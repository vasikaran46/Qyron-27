from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone

from backend.auth import Principal, admin_user, reviewer_user
from backend.db import service_client
from backend.models import PaymentReviewInput, ReviewInput, ShortlistInput

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard")
def admin_dashboard(user: Principal = Depends(reviewer_user)):
    client = service_client()
    teams = client.table("teams").select("*").order("created_at", desc=True).limit(100).execute().data or []
    if not teams:
        return {"teams": [], "shortlisted_count": 0, "shortlist_limit": 30}
    team_ids = [team["id"] for team in teams]
    members = client.table("team_members").select("id,team_id,full_name,email,student_id,is_team_lead").in_("team_id", team_ids).order("created_at").execute().data or []
    reviews = client.table("team_reviews").select("*").in_("team_id", team_ids).execute().data or []
    reviews.sort(key=lambda item: item["reviewer_id"] != user.id)
    payments = client.table("payments").select("id,team_id,member_id,stage,amount_inr,status,payment_reference,reviewer_note").in_("team_id", team_ids).execute().data or []
    submissions = client.table("submissions").select("team_id,original_filename,size_bytes,submitted_at").in_("team_id", team_ids).execute().data or []
    decisions = client.table("shortlist_decisions").select("team_id,selected,score,reviewer_notes,decided_at").in_("team_id", team_ids).execute().data or []
    member_map = _group(members, "team_id")
    review_map = _group(reviews, "team_id")
    payment_map = _group(payments, "team_id")
    submission_map = {row["team_id"]: row for row in submissions}
    decision_map = {row["team_id"]: row for row in decisions}
    result = []
    for team in teams:
        tid = team["id"]
        result.append({**team, "members": member_map.get(tid, []), "reviews": review_map.get(tid, []), "payments": payment_map.get(tid, []), "submission": submission_map.get(tid), "shortlist": decision_map.get(tid)})
    return {"teams": result, "shortlisted_count": sum(1 for item in result if item["shortlist"] and item["shortlist"]["selected"]), "shortlist_limit": 30}


def _group(rows, key):
    grouped = {}
    for row in rows:
        grouped.setdefault(row[key], []).append(row)
    return grouped


@router.put("/teams/{team_id}/review")
def save_review(team_id: str, payload: ReviewInput, user: Principal = Depends(reviewer_user)):
    client = service_client()
    try:
        result = client.table("team_reviews").upsert({
            "team_id": team_id, "reviewer_id": user.id,
            "math_rigor": payload.math_rigor, "originality": payload.originality,
            "impact": payload.impact, "feasibility": payload.feasibility,
            "presentation": payload.presentation, "total_score": payload.total_score,
            "notes": payload.notes,
        }, on_conflict="team_id,reviewer_id").execute()
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Team not found or review could not be saved.") from exc
    if not result.data:
        raise HTTPException(status_code=404, detail="Team not found or review could not be saved.")
    service_client().table("teams").update({"registration_status": "under_review"}).eq("id", team_id).eq("registration_status", "submission_received").execute()
    return result.data[0]


@router.get("/teams/{team_id}/submission-link")
def submission_link(team_id: str, user: Principal = Depends(reviewer_user)):
    submission = service_client().table("submissions").select("storage_path,original_filename").eq("team_id", team_id).maybe_single().execute().data
    if not submission:
        raise HTTPException(status_code=404, detail="No proposal is attached to this team.")
    path = submission.get("storage_path", "")
    if path.startswith("http://") or path.startswith("https://"):
        return {"url": path, "expires_in": 3600}
    try:
        result = service_client().storage.from_("qyron-submissions").create_signed_url(submission["storage_path"], 120, {"download": submission["original_filename"]})
    except Exception as exc:
        raise HTTPException(status_code=502, detail="The private proposal link could not be created.") from exc
    signed_url = result.get("signedURL") or result.get("signedUrl") or result.get("signed_url")
    if not signed_url:
        raise HTTPException(status_code=502, detail="The private proposal link could not be created.")
    return {"url": signed_url, "expires_in": 120}


@router.put("/teams/{team_id}/shortlist")
def set_shortlist(team_id: str, payload: ShortlistInput, user: Principal = Depends(admin_user)):
    try:
        response = service_client().rpc("set_team_shortlist", {
            "p_team_id": team_id, "p_selected": payload.selected,
            "p_decided_by": user.id,
        }).execute()
    except Exception as exc:
        detail = str(exc).lower()
        if "shortlist limit" in detail:
            raise HTTPException(status_code=409, detail="The 30-team shortlist is full.") from exc
        raise HTTPException(status_code=400, detail="Shortlist decision could not be saved.") from exc
    return {"team_id": team_id, "selected": payload.selected, "shortlisted_count": response.data}


@router.patch("/payments/{payment_id}")
def review_payment(payment_id: str, payload: PaymentReviewInput, user: Principal = Depends(admin_user)):
    client = service_client()
    payment = client.table("payments").select("team_id,stage").eq("id", payment_id).maybe_single().execute().data
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found.")
    result = client.table("payments").update({
        "status": payload.status,
        "reviewed_by": user.id,
        "reviewed_at": datetime.now(timezone.utc).isoformat(),
        "reviewer_note": payload.note,
    }).eq("id", payment_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Payment record not found.")
    if payment["stage"] == "registration" and payload.status == "verified":
        client.table("teams").update({"registration_status": "registration_complete"}).eq("id", payment["team_id"]).eq("registration_status", "pending_payment").execute()
    return result.data[0]
