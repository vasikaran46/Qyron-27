import json
import logging
import os
import random
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import quote_plus

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, JSONResponse

from backend.config import settings

logger = logging.getLogger("qyron.registration")

router = APIRouter(tags=["registration_wizard"])

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
try:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    DATA_DIR = Path("/tmp/data")
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
REG_STORE_FILE = DATA_DIR / "registrations.json"

UPLOAD_PPT_DIR = ROOT / "uploads" / "ppt"
try:
    UPLOAD_PPT_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    UPLOAD_PPT_DIR = Path("/tmp/uploads/ppt")
    try:
        UPLOAD_PPT_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

UPLOAD_PAYMENT_DIR = ROOT / "uploads" / "payments"
try:
    UPLOAD_PAYMENT_DIR.mkdir(parents=True, exist_ok=True)
except OSError:
    UPLOAD_PAYMENT_DIR = Path("/tmp/uploads/payments")
    try:
        UPLOAD_PAYMENT_DIR.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass


def _load_registrations() -> list[dict]:
    if not REG_STORE_FILE.exists():
        return []
    try:
        with open(REG_STORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Could not read local registrations file: %s", e)
        return []


def _save_registrations(records: list[dict]) -> None:
    try:
        with open(REG_STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error("Could not write to registrations file: %s", e)


def _find_registration_by_team_name(clean_name: str) -> Optional[dict]:
    records = _load_registrations()
    lower_name = clean_name.strip().lower()
    for r in records:
        if r.get("team_name", "").strip().lower() == lower_name:
            return r
    return None


def _find_registration_by_code(team_code: str) -> Optional[dict]:
    records = _load_registrations()
    code = team_code.strip().upper()
    for r in records:
        if r.get("team_code", "").strip().upper() == code:
            return r
    return None


@router.get("/api/check-team-name")
def api_check_team_name(name: str = Query("", description="Team name to verify")):
    clean_name = name.strip()
    if not clean_name:
        return {"available": False, "message": "Team name cannot be empty."}

    # Check local store first
    existing = _find_registration_by_team_name(clean_name)
    if existing:
        return {
            "available": False,
            "message": f"Team name '{clean_name}' is already taken (team names are unique & case-insensitive).",
            "existing_name": existing.get("team_name")
        }

    # Also check Supabase if configured
    try:
        from backend.db import service_client
        sb = service_client()
        # Check teams table
        sb_team = sb.table("teams").select("name").ilike("name", clean_name).limit(1).execute().data
        if sb_team:
            return {
                "available": False,
                "message": f"Team name '{clean_name}' is already reserved in QYRON central registry.",
                "existing_name": sb_team[0].get("name")
            }
    except Exception:
        pass

    return {
        "available": True,
        "message": f"Team name '{clean_name}' is available."
    }


@router.post("/api/register")
async def api_submit_registration(request: Request):
    """
    Validates team data, project proposal, presentation upload,
    and generates a ₹150 payment order.
    Enforces team size of 2 to 4 members.
    """
    content_type = request.headers.get("content-type", "")
    data: Dict[str, Any] = {}
    idea_ppt_file: Optional[UploadFile] = None

    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        for k, v in form.items():
            if k == "idea_ppt" and isinstance(v, UploadFile):
                idea_ppt_file = v
            else:
                data[k] = v
        
        # Parse members JSON if sent as string
        if isinstance(data.get("members"), str):
            try:
                data["members"] = json.loads(data["members"])
            except Exception:
                data["members"] = []
    else:
        try:
            data = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid request payload.")

    team_name = str(data.get("team_name", "")).strip()
    college_name = str(data.get("college_name", "")).strip()
    track = str(data.get("track", "")).strip()

    leader_name = str(data.get("leader_name", "")).strip()
    leader_email = str(data.get("leader_email", "")).strip().lower()
    leader_phone = str(data.get("leader_phone", "")).strip()
    leader_college = str(data.get("leader_college", "")).strip() or college_name
    leader_degree = str(data.get("leader_degree", "")).strip()
    leader_department = str(data.get("leader_department", "")).strip() or "General"
    leader_year = str(data.get("leader_year", "")).strip() or "3rd Year"
    leader_gender = str(data.get("leader_gender", "")).strip()

    idea_title = str(data.get("idea_title", "")).strip()
    idea_description = str(data.get("idea_description", "")).strip()
    idea_summary = str(data.get("idea_summary", "")).strip()

    members_list = data.get("members", [])
    if isinstance(members_list, str):
        try:
            members_list = json.loads(members_list)
        except Exception:
            members_list = []

    # Essential field checks
    if not (team_name and college_name and track and leader_name and leader_email and leader_phone and leader_degree and leader_gender):
        return JSONResponse(
            status_code=422,
            content={"success": False, "message": "Please fill in Team Name, College Name, Track, Leader Degree, Gender, and contact credentials."}
        )

    # Check case-insensitive unique team name
    if _find_registration_by_team_name(team_name):
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": f"Team name '{team_name}' is already taken (team names are unique & case-insensitive). Please choose a different team name."
            }
        )

    # Idea Submission fields (now submitted via Participant Portal after login)
    if not idea_title:
        idea_title = "Pending Portal Submission"
    if not idea_summary:
        idea_summary = "To be submitted by team in Participant Portal."
    if not idea_description:
        idea_description = "To be submitted by team in Participant Portal."

    # Validate team size (min 2, max 4 total members)
    total_team_size = 1 + len(members_list)
    if total_team_size < 2 or total_team_size > 4:
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "message": f"Team size must be between 2 and 4 members (Leader + 1 to 3 members). Current total: {total_team_size}."
            }
        )

    # Validate crew members and check email uniqueness
    all_emails = [leader_email]
    cleaned_members = []
    for idx, m in enumerate(members_list, start=2):
        if not isinstance(m, dict):
            continue
        m_name = str(m.get("name", "")).strip()
        m_email = str(m.get("email", "")).strip().lower()
        m_phone = str(m.get("phone", "")).strip()
        m_gender = str(m.get("gender", "")).strip()
        m_degree = str(m.get("degree", "")).strip()
        m_dept = str(m.get("department", "")).strip() or "General"
        m_year = str(m.get("year", "3rd Year")).strip()

        if not (m_name and m_email and m_phone):
            return JSONResponse(
                status_code=422,
                content={"success": False, "message": f"Please provide Full Name, Email, and Mobile Number for Crew Member #{idx}."}
            )
        if m_email in all_emails:
            return JSONResponse(
                status_code=422,
                content={"success": False, "message": f"Duplicate email address '{m_email}' found in roster. Every member must have a distinct email."}
            )
        all_emails.append(m_email)

        if not m_gender:
            return JSONResponse(
                status_code=422,
                content={"success": False, "message": f"Please select Gender for Crew Member #{idx}."}
            )
        if not m_degree:
            return JSONResponse(
                status_code=422,
                content={"success": False, "message": f"Please select Degree for Crew Member #{idx}."}
            )

        cleaned_members.append({
            "id": idx,
            "name": m_name,
            "email": m_email,
            "phone": m_phone,
            "college": college_name,
            "degree": m_degree,
            "department": m_dept,
            "year": m_year,
            "gender": m_gender,
        })

    # Generate unique team identification code: QYRON-27-XXX-XXXX
    records = _load_registrations()
    seq_num = len(records) + 101
    random_suffix = uuid.uuid4().hex[:4].upper()
    team_code = f"QYRON-27-{seq_num:03d}-{random_suffix}"

    # Handle presentation file upload
    ppt_filename = None
    ppt_disk_path = None
    ppt_drive_url = None
    ppt_drive_file_id = None
    if idea_ppt_file and idea_ppt_file.filename:
        filename = idea_ppt_file.filename
        ext = Path(filename).suffix.lower()
        if ext not in [".ppt", ".pptx", ".pdf"]:
            return JSONResponse(
                status_code=422,
                content={"success": False, "message": "Presentation slides must be in .pptx, .ppt, or .pdf format."}
            )
        file_bytes = await idea_ppt_file.read()
        if len(file_bytes) > 10 * 1024 * 1024:
            return JSONResponse(
                status_code=422,
                content={"success": False, "message": "Presentation file size exceeds maximum limit of 10MB."}
            )
        # Check if Google Drive direct upload is configured
        ppt_drive_url = None
        ppt_drive_file_id = None
        try:
            from backend.services.gdrive import gdrive_service
            if gdrive_service.is_configured():
                logger.info("Uploading presentation to Google Drive for team %s...", team_code)
                drive_success, drive_res, drive_id = gdrive_service.upload_file(
                    file_bytes=file_bytes,
                    filename=f"{team_code}_{filename}",
                    mime_type=None
                )
                if drive_success:
                    ppt_drive_url = drive_res
                    ppt_drive_file_id = drive_id
                    logger.info("Google Drive upload SUCCESS for %s: %s", team_code, drive_res)
                else:
                    logger.warning("Google Drive upload returned error: %s", drive_res)
        except Exception as g_err:
            logger.warning("Google Drive upload error: %s", g_err)

        safe_name = re.sub(r"[^a-zA-Z0-9_\.-]", "_", filename)
        saved_filename = f"{team_code}_{safe_name}"
        save_path = UPLOAD_PPT_DIR / saved_filename
        try:
            with open(save_path, "wb") as f:
                f.write(file_bytes)
            ppt_filename = filename
            ppt_disk_path = ppt_drive_url or f"/uploads/ppt/{saved_filename}"
        except Exception as err:
            logger.warning("Could not write upload file locally: %s", err)
            ppt_filename = filename
            ppt_disk_path = ppt_drive_url or f"/uploads/ppt/{saved_filename}"

    # Payment order (₹150 team registration fee via UPI QR)
    cfg = settings()
    amount_inr = cfg.upi_amount or 150
    amount_paise = amount_inr * 100
    order_id = f"order_qyron_{int(datetime.now(timezone.utc).timestamp())}_{uuid.uuid4().hex[:6]}"
    
    # Generate portal login credentials for team lead
    random_pin = random.randint(1000, 9999)
    portal_password = f"Qyron@{random_pin}"

    order_data = {
        "mode": "upi_qr",
        "order_id": order_id,
        "amount": amount_paise,
        "amount_inr": amount_inr,
        "currency": "INR",
        "upi_id": cfg.upi_id,
        "upi_payee_name": cfg.upi_payee_name,
        "upi_qr_image": cfg.upi_qr_image,
        "upi_deep_link": f"upi://pay?pa={cfg.upi_id}&pn={quote_plus(cfg.upi_payee_name)}&am={amount_inr}&cu=INR&tn={quote_plus('QYRON27 ' + team_code)}",
        "name": "QYRON'27",
        "description": f"Team Registration Fee (₹150) - {team_code}",
        "notes": {
            "team_code": team_code,
            "team_name": team_name,
            "leader_email": leader_email,
            "leader_phone": leader_phone
        }
    }

    # Save registration entry
    reg_record = {
        "team_code": team_code,
        "team_name": team_name,
        "college_name": college_name,
        "track": track,
        "idea_title": idea_title,
        "idea_summary": idea_summary,
        "idea_description": idea_description,
        "idea_ppt_filename": ppt_filename,
        "idea_ppt_path": ppt_disk_path,
        "idea_ppt_url": ppt_drive_url or ppt_disk_path,
        "idea_ppt_drive_url": ppt_drive_url,
        "idea_ppt_drive_id": ppt_drive_file_id,
        "portal_username": leader_email,
        "portal_password": portal_password,
        "proposal_submitted": bool(ppt_filename),
        "leader_name": leader_name,
        "leader_email": leader_email,
        "leader_phone": leader_phone,
        "leader_college": leader_college,
        "leader_degree": leader_degree,
        "leader_department": leader_department,
        "leader_year": leader_year,
        "leader_gender": leader_gender,
        "member_count": total_team_size,
        "members": cleaned_members,
        "amount_paid": amount_inr,
        "payment_status": "pending",
        "razorpay_order_id": order_id,
        "razorpay_payment_id": None,
        "status": "submitted",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    records.append(reg_record)
    _save_registrations(records)

    # Check if UTR number was submitted directly in this request (Atomic registration)
    utr_number = str(data.get("utr_number") or "").strip()
    payment_screenshot_file = None
    if "multipart/form-data" in content_type:
        payment_screenshot_file = form.get("payment_screenshot")

    if utr_number:
        # Atomic registration: team info + UPI payment recorded together
        screenshot_url = None
        if payment_screenshot_file and isinstance(payment_screenshot_file, UploadFile) and payment_screenshot_file.filename:
            s_ext = Path(payment_screenshot_file.filename).suffix.lower() or ".jpg"
            try:
                s_bytes = await payment_screenshot_file.read()
                from backend.services.gdrive import gdrive_service
                if gdrive_service.is_configured():
                    d_ok, d_res, _ = gdrive_service.upload_payment_screenshot(
                        file_bytes=s_bytes,
                        filename=f"{team_code}_payment_screenshot{s_ext}",
                        mime_type=payment_screenshot_file.content_type
                    )
                    if d_ok:
                        screenshot_url = d_res
            except Exception as g_err:
                logger.warning("Google Drive screenshot upload error in atomic register: %s", g_err)

        reg_record["utr_number"] = utr_number
        reg_record["razorpay_payment_id"] = utr_number
        reg_record["payment_reference"] = utr_number
        reg_record["payment_status"] = "pending_verification"
        reg_record["payment_method"] = "upi_qr"
        if screenshot_url:
            reg_record["payment_screenshot_url"] = screenshot_url
        reg_record["payment_timestamp"] = datetime.now(timezone.utc).isoformat()
        reg_record["status"] = "pending_verification"
        _save_registrations(records)

        # Sync to Supabase
        try:
            from backend.db import service_client
            sb = service_client()
            sb.table("registrations").upsert({
                "team_code": team_code,
                "team_name": team_name,
                "college_name": college_name,
                "track": track,
                "idea_title": idea_title,
                "idea_summary": idea_summary,
                "idea_description": idea_description,
                "idea_ppt_filename": ppt_filename,
                "idea_ppt_path": ppt_disk_path,
                "leader_name": leader_name,
                "leader_email": leader_email,
                "leader_phone": leader_phone,
                "leader_college": leader_college,
                "leader_department": leader_department,
                "leader_year": leader_year,
                "leader_gender": leader_gender,
                "member_count": total_team_size,
                "members_data": json.dumps(cleaned_members),
                "amount_paid": amount_inr,
                "payment_status": "pending_verification",
                "razorpay_order_id": order_id,
                "razorpay_payment_id": utr_number,
                "payment_timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "pending_verification"
            }).execute()
        except Exception as sb_err:
            logger.debug("Supabase atomic register upsert skipped: %s", sb_err)

        # Provision Supabase Auth User
        try:
            from backend.db import service_client
            sb = service_client()
            try:
                sb.auth.admin.create_user({
                    "email": leader_email,
                    "password": portal_password,
                    "email_confirm": True,
                    "user_metadata": {
                        "full_name": leader_name,
                        "team_name": team_name,
                        "team_code": team_code,
                        "role": "participant"
                    }
                })
            except Exception:
                try:
                    users = sb.auth.admin.list_users()
                    matched = [u for u in users if u.email.lower() == leader_email.lower()]
                    if matched:
                        sb.auth.admin.update_user_by_id(matched[0].id, {"password": portal_password, "email_confirm": True})
                except Exception:
                    pass
        except Exception as sb_err:
            logger.debug("Supabase auth note in atomic register: %s", sb_err)

        # Dispatch Email 1 with credentials immediately
        portal_url = "https://qyron27.vercel.app/login" if "vercel.app" in str(request.base_url) else "http://127.0.0.1:8000/login"
        try:
            cfg = settings()
            if cfg.has_smtp:
                from backend.mailer import send_registration_confirmation
                send_registration_confirmation(
                    to_email=leader_email,
                    team_code=team_code,
                    team_name=team_name,
                    track=track,
                    utr_number=utr_number,
                    leader_name=leader_name,
                    username=leader_email,
                    password=portal_password,
                    portal_url=portal_url,
                    college_name=college_name
                )
        except Exception as email_err:
            logger.warning("SMTP confirmation email error in atomic register: %s", email_err)

        return {
            "success": True,
            "message": "Registration successful! Your portal login credentials have been dispatched to your email.",
            "team_code": team_code,
            "username": leader_email,
            "password": portal_password,
            "portal_url": portal_url,
            "payment_status": "pending_verification",
            "redirect_url": f"/confirmation?team_code={team_code}"
        }

    # Also sync to Supabase if available
    try:
        from backend.db import service_client
        sb = service_client()
        sb.table("registrations").upsert({
            "team_code": team_code,
            "team_name": team_name,
            "college_name": college_name,
            "track": track,
            "idea_title": idea_title,
            "idea_summary": idea_summary,
            "idea_description": idea_description,
            "idea_ppt_filename": ppt_filename,
            "idea_ppt_path": ppt_disk_path,
            "leader_name": leader_name,
            "leader_email": leader_email,
            "leader_phone": leader_phone,
            "leader_college": leader_college,
            "leader_department": leader_department,
            "leader_year": leader_year,
            "leader_gender": leader_gender,
            "member_count": total_team_size,
            "members_data": json.dumps(cleaned_members),
            "amount_paid": amount_inr,
            "payment_status": "pending",
            "razorpay_order_id": order_id,
            "status": "submitted"
        }).execute()
    except Exception as sb_err:
        logger.debug("Supabase sync skipped: %s", sb_err)

    return {
        "success": True,
        "team_code": team_code,
        "order": order_data
    }


@router.post("/api/payment/verify")
async def api_verify_payment(request: Request):
    content_type = request.headers.get("content-type", "")
    screenshot_file = None
    data: Dict[str, Any] = {}
    if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
        form = await request.form()
        team_code = str(form.get("team_code", "")).strip()
        utr_number = str(form.get("utr_number", form.get("razorpay_payment_id", ""))).strip()
        order_id = str(form.get("order_id", form.get("razorpay_order_id", ""))).strip()
        screenshot_file = form.get("payment_screenshot")
        for k, v in form.items():
            if k != "payment_screenshot":
                data[k] = v
    else:
        try:
            data = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid payload format.")
        team_code = data.get("team_code")
        utr_number = str(data.get("utr_number") or data.get("razorpay_payment_id") or "").strip()
        order_id = data.get("order_id") or data.get("razorpay_order_id")

    payment_id = utr_number or f"UPI_UTR_{uuid.uuid4().hex[:8].upper()}"

    if not team_code:
        raise HTTPException(status_code=422, detail="Team code is required.")

    records = _load_registrations()
    reg = None
    for r in records:
        if r.get("team_code", "").strip().upper() == team_code.strip().upper():
            reg = r
            break

    # 1. Fallback: Query Supabase
    if not reg:
        try:
            from backend.db import service_client
            sb = service_client()
            res = sb.table("registrations").select("*").eq("team_code", team_code.strip().upper()).limit(1).execute().data
            if res:
                reg = res[0]
                if isinstance(reg.get("members_data"), str):
                    try:
                        reg["members"] = json.loads(reg["members_data"])
                    except Exception:
                        reg["members"] = []
                records.append(reg)
        except Exception as sb_err:
            logger.debug("Supabase lookup note in verify_payment: %s", sb_err)

    # 2. Fallback: Reconstruct from incoming form data if present (prevents Vercel serverless cross-instance 404)
    if not reg:
        leader_email = str(data.get("leader_email") or "").strip().lower()
        if leader_email or team_code:
            portal_pw = f"Qyron@{random.randint(1000, 9999)}"
            members_raw = data.get("members", [])
            if isinstance(members_raw, str):
                try:
                    members_raw = json.loads(members_raw)
                except Exception:
                    members_raw = []
            reg = {
                "team_code": team_code,
                "team_name": str(data.get("team_name") or f"Team-{team_code[-4:]}").strip(),
                "college_name": str(data.get("college_name") or "Collegiate Team").strip(),
                "track": str(data.get("track") or "Quantum Computing").strip(),
                "leader_name": str(data.get("leader_name") or "Team Leader").strip(),
                "leader_email": leader_email or "participant@qyron.org",
                "leader_phone": str(data.get("leader_phone") or "").strip(),
                "leader_degree": str(data.get("leader_degree") or "B.Sc").strip(),
                "leader_department": str(data.get("leader_department") or "Department of Mathematics").strip(),
                "leader_year": str(data.get("leader_year") or "3rd Year").strip(),
                "leader_gender": str(data.get("leader_gender") or "Other").strip(),
                "members": members_raw,
                "member_count": 1 + len(members_raw),
                "portal_username": leader_email or "participant@qyron.org",
                "portal_password": portal_pw,
                "amount_paid": 150,
                "payment_status": "pending_verification",
                "status": "pending_verification",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            records.append(reg)

    if not reg:
        return JSONResponse(status_code=404, content={"success": False, "message": "Registration record not found."})

    # Upload payment screenshot to Google Drive & local storage if provided
    screenshot_url = None
    if screenshot_file and isinstance(screenshot_file, UploadFile) and screenshot_file.filename:
        s_filename = screenshot_file.filename
        s_ext = Path(s_filename).suffix.lower() or ".jpg"
        s_bytes = await screenshot_file.read()
        
        # 1. Google Drive direct upload
        try:
            from backend.services.gdrive import gdrive_service
            if gdrive_service.is_configured():
                d_ok, d_res, _ = gdrive_service.upload_payment_screenshot(
                    file_bytes=s_bytes,
                    filename=f"{team_code}_payment_screenshot{s_ext}",
                    mime_type=screenshot_file.content_type
                )
                if d_ok:
                    screenshot_url = d_res
                    logger.info("Google Drive payment screenshot upload SUCCESS for %s: %s", team_code, d_res)
        except Exception as g_err:
            logger.warning("Google Drive screenshot upload error: %s", g_err)

        # 2. Local fallback storage
        s_safe_name = f"{team_code}_payment_screenshot{s_ext}"
        s_local_path = UPLOAD_PAYMENT_DIR / s_safe_name
        try:
            with open(s_local_path, "wb") as sf:
                sf.write(s_bytes)
            if not screenshot_url:
                screenshot_url = f"/uploads/payments/{s_safe_name}"
        except Exception:
            pass

    reg["payment_status"] = "pending_verification"
    reg["payment_method"] = "upi_qr"
    reg["utr_number"] = utr_number or payment_id
    reg["razorpay_payment_id"] = payment_id
    reg["payment_reference"] = utr_number or payment_id
    if screenshot_url:
        reg["payment_screenshot_url"] = screenshot_url
    reg["payment_timestamp"] = datetime.now(timezone.utc).isoformat()
    reg["status"] = "pending_verification"

    # Generate portal login credentials and provision active access immediately
    leader_email = reg.get("leader_email")
    leader_name = reg.get("leader_name")
    team_name = reg.get("team_name")
    track = reg.get("track")
    college_name = reg.get("college_name") or ""
    username = leader_email
    password = reg.get("portal_password") or f"Qyron@{random.randint(1000, 9999)}"
    reg["portal_username"] = username
    reg["portal_password"] = password

    _save_registrations(records)

    # Provision user immediately in Supabase Auth
    try:
        from backend.db import service_client
        sb = service_client()
        try:
            sb.auth.admin.create_user({
                "email": username,
                "password": password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": leader_name,
                    "team_name": team_name,
                    "team_code": team_code,
                    "role": "participant"
                }
            })
            logger.info("Created Supabase Auth user upon registration: %s", username)
        except Exception:
            try:
                users = sb.auth.admin.list_users()
                matched = [u for u in users if u.email.lower() == username.lower()]
                if matched:
                    sb.auth.admin.update_user_by_id(matched[0].id, {"password": password, "email_confirm": True})
                    logger.info("Updated existing Supabase Auth user password: %s", username)
            except Exception:
                pass

        try:
            sb.table("registrations").update({
                "payment_status": reg.get("payment_status", "pending_verification"),
                "razorpay_payment_id": payment_id,
                "payment_timestamp": datetime.now(timezone.utc).isoformat()
            }).eq("team_code", team_code).execute()
        except Exception:
            pass
    except Exception as sb_err:
        logger.warning("Supabase auth note: %s", sb_err)

    # Send confirmation email with portal login credentials immediately
    portal_url = "http://127.0.0.1:8000/login"
    try:
        cfg = settings()
        if cfg.has_smtp:
            from backend.mailer import send_registration_confirmation
            send_registration_confirmation(
                to_email=leader_email,
                team_code=team_code,
                team_name=team_name,
                track=track,
                utr_number=reg.get("utr_number", payment_id),
                leader_name=leader_name,
                username=username,
                password=password,
                portal_url=portal_url,
                college_name=college_name
            )
    except Exception as email_err:
        logger.warning("SMTP confirmation email error: %s", email_err)

    return {
        "success": True,
        "message": "Registration successful! Your portal login credentials have been dispatched to your email.",
        "team_code": team_code,
        "username": username,
        "password": password,
        "portal_url": portal_url,
        "payment_status": reg.get("payment_status", "pending_verification"),
        "redirect_url": f"/confirmation?team_code={team_code}"
    }


@router.post("/api/admin/registrations/{team_code}/verify-payment")
async def api_admin_verify_payment(team_code: str):
    """
    Called by organizers from Admin Panel to verify UPI payment receipt.
    Activates participant portal account and dispatches Email 2 with login credentials.
    """
    records = _load_registrations()
    reg = None
    for r in records:
        if r.get("team_code", "").strip().upper() == team_code.strip().upper():
            reg = r
            break

    if not reg:
        try:
            from backend.db import service_client
            sb = service_client()
            res = sb.table("registrations").select("*").eq("team_code", team_code.strip().upper()).limit(1).execute().data
            if res:
                reg = res[0]
                records.append(reg)
        except Exception:
            pass

    if not reg:
        return JSONResponse(status_code=404, content={"success": False, "message": "Registration record not found."})

    leader_email = reg.get("leader_email")
    leader_name = reg.get("leader_name")
    team_name = reg.get("team_name")
    track = reg.get("track")
    college_name = reg.get("college_name") or ""
    utr_number = reg.get("utr_number") or reg.get("razorpay_payment_id") or "Verified"
    username = leader_email
    password = reg.get("portal_password") or f"Qyron@{random.randint(1000, 9999)}"
    reg["portal_password"] = password
    reg["payment_status"] = "paid"
    reg["status"] = "payment_verified"
    reg["payment_verified_at"] = datetime.now(timezone.utc).isoformat()
    _save_registrations(records)

    # Provision active participant in Supabase Auth
    try:
        from backend.db import service_client
        sb = service_client()
        try:
            sb.auth.admin.create_user({
                "email": username,
                "password": password,
                "email_confirm": True,
                "user_metadata": {
                    "full_name": leader_name,
                    "team_name": team_name,
                    "team_code": team_code,
                    "role": "participant"
                }
            })
            logger.info("Admin activated Supabase Auth user: %s", username)
        except Exception:
            try:
                users = sb.auth.admin.list_users()
                matched = [u for u in users if u.email.lower() == username.lower()]
                if matched:
                    sb.auth.admin.update_user_by_id(matched[0].id, {"password": password, "email_confirm": True})
            except Exception:
                pass

        try:
            sb.table("registrations").update({
                "payment_status": "paid",
                "payment_verified_at": datetime.now(timezone.utc).isoformat()
            }).eq("team_code", team_code).execute()
        except Exception:
            pass
    except Exception as sb_err:
        logger.warning("Supabase sync note on admin verify: %s", sb_err)

    # Dispatch Email 2: Payment Verified & Portal Access Activated
    portal_url = "http://127.0.0.1:8000/login"
    try:
        from backend.mailer import send_payment_verified_email
        send_payment_verified_email(
            to_email=leader_email,
            team_code=team_code,
            team_name=team_name,
            track=track,
            utr_number=utr_number,
            leader_name=leader_name,
            username=username,
            password=password,
            portal_url=portal_url,
            college_name=college_name
        )
    except Exception as email_err:
        logger.warning("Error dispatching payment verified email: %s", email_err)

    return {
        "success": True,
        "message": f"Payment for team {team_code} verified! Portal credentials email dispatched to {leader_email}.",
        "team_code": team_code,
        "payment_status": "paid",
        "username": username
    }


@router.post("/api/admin/registrations/{team_code}/reject-payment")
async def api_admin_reject_payment(team_code: str):
    """
    Called by organizers from Admin Panel to flag false / invalid UTR.
    """
    records = _load_registrations()
    reg = None
    for r in records:
        if r.get("team_code", "").strip().upper() == team_code.strip().upper():
            reg = r
            break
    if not reg:
        try:
            from backend.db import service_client
            sb = service_client()
            res = sb.table("registrations").select("*").eq("team_code", team_code.strip().upper()).limit(1).execute().data
            if res:
                reg = res[0]
                records.append(reg)
        except Exception:
            pass
    if not reg:
        return JSONResponse(status_code=404, content={"success": False, "message": "Registration record not found."})

    reg["payment_status"] = "rejected"
    reg["status"] = "payment_rejected"
    _save_registrations(records)
    return {
        "success": True,
        "message": f"Payment for team {team_code} marked as REJECTED.",
        "team_code": team_code,
        "payment_status": "rejected"
    }


@router.post("/api/portal/submit-proposal")
async def api_portal_submit_proposal(request: Request):
    """
    Submits proposal details (Title, Abstract, Description, PPT/PDF) from the portal.
    Uploads presentation file directly to Google Drive.
    """
    form = await request.form()
    team_code = str(form.get("team_code", "")).strip()
    leader_email = str(form.get("email", "")).strip().lower()
    idea_title = str(form.get("idea_title", "")).strip()
    idea_summary = str(form.get("idea_summary", "")).strip()
    idea_description = str(form.get("idea_description", "")).strip()
    ppt_file = form.get("idea_ppt")

    if not idea_title:
        return JSONResponse(status_code=422, content={"success": False, "message": "Idea Title is required."})
    if not idea_summary:
        return JSONResponse(status_code=422, content={"success": False, "message": "Abstract / Executive Summary is required."})
    if not idea_description:
        return JSONResponse(status_code=422, content={"success": False, "message": "Technical Description is required."})

    records = _load_registrations()
    reg = None
    for r in records:
        if (team_code and r.get("team_code") == team_code) or (leader_email and r.get("leader_email", "").lower() == leader_email):
            reg = r
            break

    if not reg:
        return JSONResponse(status_code=404, content={"success": False, "message": "Team registration record not found."})

    effective_team_code = reg.get("team_code")
    ppt_drive_url = None
    ppt_filename = reg.get("idea_ppt_filename")
    ppt_disk_path = reg.get("idea_ppt_path")

    if ppt_file and isinstance(ppt_file, UploadFile) and ppt_file.filename:
        filename = ppt_file.filename
        ext = Path(filename).suffix.lower()
        if ext not in [".ppt", ".pptx", ".pdf"]:
            return JSONResponse(status_code=422, content={"success": False, "message": "Presentation must be in .pptx, .ppt, or .pdf format."})
        file_bytes = await ppt_file.read()
        if len(file_bytes) > 10 * 1024 * 1024:
            return JSONResponse(status_code=422, content={"success": False, "message": "Presentation file size exceeds 10MB limit."})

        # Upload directly to Google Drive
        try:
            from backend.services.gdrive import gdrive_service
            if gdrive_service.is_configured():
                d_ok, d_res, d_id = gdrive_service.upload_file(
                    file_bytes=file_bytes,
                    filename=f"{effective_team_code}_{filename}",
                    mime_type=None
                )
                if d_ok:
                    ppt_drive_url = d_res
                    logger.info("Google Drive upload successful for proposal %s: %s", effective_team_code, d_res)
        except Exception as d_err:
            logger.warning("Google Drive upload error during portal submission: %s", d_err)

        safe_name = re.sub(r"[^a-zA-Z0-9_\.-]", "_", filename)
        saved_filename = f"{effective_team_code}_{safe_name}"
        save_path = UPLOAD_PPT_DIR / saved_filename
        try:
            with open(save_path, "wb") as f:
                f.write(file_bytes)
            ppt_filename = filename
            ppt_disk_path = ppt_drive_url or f"/uploads/ppt/{saved_filename}"
        except Exception:
            ppt_filename = filename
            ppt_disk_path = ppt_drive_url or f"/uploads/ppt/{saved_filename}"

    reg["idea_title"] = idea_title
    reg["idea_summary"] = idea_summary
    reg["idea_description"] = idea_description
    reg["idea_ppt_filename"] = ppt_filename
    reg["idea_ppt_path"] = ppt_disk_path
    reg["idea_ppt_drive_url"] = ppt_drive_url or reg.get("idea_ppt_drive_url")
    reg["idea_ppt_url"] = ppt_drive_url or ppt_disk_path
    reg["proposal_submitted"] = True
    reg["proposal_submitted_at"] = datetime.now(timezone.utc).isoformat()
    reg["status"] = "submission_received"
    _save_registrations(records)

    # Sync to Supabase registrations table if present
    try:
        from backend.db import service_client
        sb = service_client()
        sb.table("registrations").update({
            "idea_title": idea_title,
            "idea_summary": idea_summary,
            "idea_description": idea_description,
            "idea_ppt_filename": ppt_filename,
            "idea_ppt_path": ppt_disk_path,
            "status": "submission_received"
        }).eq("team_code", effective_team_code).execute()
    except Exception:
        pass

    return {
        "success": True,
        "message": "Project presentation slides and details successfully submitted!",
        "team_code": effective_team_code,
        "drive_url": ppt_drive_url,
        "ppt_filename": ppt_filename
    }


@router.get("/api/registration/{team_code}")
def api_get_registration(team_code: str):
    reg = _find_registration_by_code(team_code)
    if not reg:
        # Check Supabase
        try:
            from backend.db import service_client
            sb = service_client()
            res = sb.table("registrations").select("*").eq("team_code", team_code.strip().upper()).limit(1).execute().data
            if res:
                reg = res[0]
                if isinstance(reg.get("members_data"), str):
                    try:
                        reg["members"] = json.loads(reg["members_data"])
                    except Exception:
                        reg["members"] = []
        except Exception:
            pass

    if not reg:
        raise HTTPException(status_code=404, detail="Registration record not found.")

    return {"success": True, "registration": reg}


@router.get("/api/admin/registrations")
def api_get_all_registrations():
    """Lists all team registrations, UTR payment verification references, and proposal uploads."""
    records = _load_registrations()
    return {"success": True, "count": len(records), "registrations": records}


@router.get("/download/idea-template")
async def download_idea_template():
    """Serves the standardized QYRON'27 Presentation Template."""
    ppt_path = ROOT / "assets" / "qyron-proposal-outline.pptx"
    if not ppt_path.exists():
        raise HTTPException(status_code=404, detail="Template file not found.")

    return FileResponse(
        path=str(ppt_path),
        filename="qyron-proposal-outline.pptx",
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation"
    )
