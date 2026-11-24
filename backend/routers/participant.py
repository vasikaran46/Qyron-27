from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from backend.auth import Principal, current_user
from backend.db import service_client
from backend.models import PaymentReferenceInput, TeamRegistration

try:
    from zoneinfo import ZoneInfo
    IST = ZoneInfo("Asia/Kolkata")
except Exception:
    IST = timezone(timedelta(hours=5, minutes=30), name="IST")

router = APIRouter(prefix="/api/participant", tags=["participant"])
REGISTRATION_CUTOFF = datetime(2027, 1, 20, 23, 59, 59, tzinfo=IST)
SUBMISSION_CUTOFF = datetime(2027, 1, 25, 23, 59, 59, tzinfo=IST)
SHORTLIST_FEE_CUTOFF = datetime(2027, 2, 7, 23, 59, 59, tzinfo=IST)
ALLOWED_TYPES = {
    ".pdf": ("application/pdf", b"%PDF-"),
    ".ppt": ("application/vnd.ms-powerpoint", bytes.fromhex("D0CF11E0A1B11AE1")),
    ".pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", b"PK\x03\x04"),
}


def _single(table: str, **filters):
    query = service_client().table(table).select("*")
    for key, value in filters.items():
        query = query.eq(key, value)
    return query.maybe_single().execute().data


@router.get("/dashboard")
def dashboard(user: Principal = Depends(current_user)):
    client = service_client()
    teams = client.table("teams").select("*").eq("team_lead_user_id", user.id).order("created_at", desc=True).limit(1).execute().data or []
    if not teams and user.email:
        memberships = client.table("team_members").select("team_id").eq("email", user.email.lower()).limit(1).execute().data or []
        if memberships:
            teams = client.table("teams").select("*").eq("id", memberships[0]["team_id"]).limit(1).execute().data or []
    if not teams:
        return {"team": None}
    team = teams[0]
    members = client.table("team_members").select("id,full_name,email,student_id,is_team_lead").eq("team_id", team["id"]).order("created_at").execute().data or []
    payments = client.table("payments").select("id,stage,amount_inr,status,payment_reference,member_id,created_at").eq("team_id", team["id"]).order("created_at").execute().data or []
    member_map = {member["id"]: member for member in members}
    for payment in payments:
        owner = member_map.get(payment.get("member_id"))
        payment["member_name"] = owner["full_name"] if owner else None
        payment["member_email"] = owner["email"] if owner else None
    submissions = client.table("submissions").select("original_filename,size_bytes,submitted_at").eq("team_id", team["id"]).limit(1).execute().data or []
    decision = _single("shortlist_decisions", team_id=team["id"])
    if datetime.now(IST) < datetime(2027, 2, 1, 18, 0, tzinfo=IST):
        decision = None
    if not decision or not decision.get("selected"):
        payments = [payment for payment in payments if payment["stage"] == "registration"]
    return {"team": team, "members": members, "payments": payments, "submission": submissions[0] if submissions else None, "shortlist": decision, "viewer_email": user.email, "is_team_lead": team["team_lead_user_id"] == user.id}


@router.post("/teams/{team_id}/payments/{payment_id}/reference")
def submit_payment_reference(team_id: str, payment_id: str, payload: PaymentReferenceInput, user: Principal = Depends(current_user)):
    client = service_client()
    team = _single("teams", id=team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found.")
    payment = _single("payments", id=payment_id, team_id=team_id)
    if not payment or payment["status"] not in {"pending", "rejected"}:
        raise HTTPException(status_code=409, detail="This payment is not accepting a reference.")
    if payment["stage"] == "shortlisted" and datetime.now(IST) > SHORTLIST_FEE_CUTOFF:
        raise HTTPException(status_code=410, detail="The shortlisted fee deadline has passed.")
    if payment["stage"] == "registration":
        if team["team_lead_user_id"] != user.id:
            raise HTTPException(status_code=403, detail="Only the team lead can submit the team payment reference.")
    else:
        member = _single("team_members", id=payment["member_id"], team_id=team_id)
        if not member or member["email"].lower() != user.email.lower():
            raise HTTPException(status_code=403, detail="This shortlisted fee belongs to another team member.")
    result = client.table("payments").update({
        "status": "submitted", "payment_reference": payload.payment_reference.strip(), "reviewer_note": "", "reviewed_by": None, "reviewed_at": None,
    }).eq("id", payment_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Payment record not found.")
    return {"payment": result.data[0], "message": "Payment reference submitted for organizer review."}


@router.post("/teams", status_code=201)
def register_team(payload: TeamRegistration, user: Principal = Depends(current_user)):
    if user.role != "participant":
        raise HTTPException(status_code=403, detail="Only participant accounts can register a team.")
    if datetime.now(IST) > REGISTRATION_CUTOFF:
        raise HTTPException(status_code=410, detail="Team registration is closed.")
    if not payload.members or payload.members[0].email.lower() != user.email.lower():
        raise HTTPException(status_code=422, detail="The first roster member must match the signed-in team lead.")
    try:
        result = service_client().rpc("register_complete_team", {
            "p_name": payload.name,
            "p_college": payload.college,
            "p_team_lead_user_id": user.id,
            "p_members": [member.model_dump(mode="json") for member in payload.members],
        }).execute()
    except Exception as exc:
        message = str(exc)
        if "duplicate key" in message.lower():
            raise HTTPException(status_code=409, detail="A roster email is already registered on another team.") from exc
        if "registration is closed" in message.lower():
            raise HTTPException(status_code=410, detail="Team registration is closed.") from exc
        raise HTTPException(status_code=400, detail="The team could not be registered. Check the roster and try again.") from exc
    return {"team_id": result.data, "registration_status": "pending_payment"}


@router.post("/teams/{team_id}/submission")
async def submit_proposal(
    team_id: str,
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    abstract: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    user: Principal = Depends(current_user)
):
    team = _single("teams", id=team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found for this account.")
    if team["team_lead_user_id"] != user.id and not _single("team_members", team_id=team_id, email=user.email.lower()):
        raise HTTPException(status_code=403, detail="Only registered team members can upload this proposal.")
    if datetime.now(IST) > SUBMISSION_CUTOFF:
        raise HTTPException(status_code=410, detail="The proposal upload deadline has passed.")
    extension = Path(file.filename or "").suffix.lower()
    if extension not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Upload a PPT, PPTX, or PDF file.")
    content = await file.read(10 * 1024 * 1024 + 1)
    if not content or len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="The maximum proposal size is 10 MB.")
    content_type, signature = ALLOWED_TYPES[extension]
    if not content.startswith(signature):
        raise HTTPException(status_code=415, detail="The file contents do not match the selected file type.")
    client = service_client()
    old = _single("submissions", team_id=team_id)
    path = f"{team_id}/{uuid4().hex}{extension}"

    # Upload to Google Drive if configured
    drive_url = None
    try:
        from backend.services.gdrive import gdrive_service
        if gdrive_service.is_configured():
            d_ok, d_res, _ = gdrive_service.upload_file(
                file_bytes=content,
                filename=f"{team_id}_{Path(file.filename or 'proposal').name}",
                mime_type=content_type
            )
            if d_ok:
                drive_url = d_res
    except Exception:
        pass

    try:
        client.storage.from_("qyron-submissions").upload(path, content, {"content-type": content_type, "upsert": "false"})
        saved = client.table("submissions").upsert({
            "team_id": team_id, "storage_path": drive_url or path, "original_filename": Path(file.filename or "proposal").name,
            "content_type": content_type, "size_bytes": len(content), "submitted_at": datetime.now(IST).isoformat(),
        }, on_conflict="team_id").execute()
        client.table("teams").update({"registration_status": "submission_received", "updated_at": datetime.now(IST).isoformat()}).eq("id", team_id).execute()
        
        # Also sync proposal fields to registrations if matching
        try:
            update_data = {"status": "submission_received", "idea_ppt_filename": Path(file.filename or "proposal").name}
            if title: update_data["idea_title"] = title
            if abstract: update_data["idea_summary"] = abstract
            if description: update_data["idea_description"] = description
            if drive_url: update_data["idea_ppt_path"] = drive_url
            client.table("registrations").update(update_data).eq("leader_email", user.email.lower()).execute()
        except Exception:
            pass
    except Exception as exc:
        try:
            client.storage.from_("qyron-submissions").remove([path])
        except Exception:
            pass
        raise HTTPException(status_code=502, detail="Proposal upload did not complete. Please try again.") from exc
    if old and old.get("storage_path") != path:
        try:
            client.storage.from_("qyron-submissions").remove([old["storage_path"]])
        except Exception:
            pass
    return {"submission": saved.data[0] if saved.data else {"team_id": team_id, "submitted_at": datetime.now(IST).isoformat()}, "message": "Proposal uploaded successfully.", "drive_url": drive_url}
