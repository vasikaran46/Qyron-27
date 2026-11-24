from dataclasses import dataclass
from typing import Literal

from fastapi import Cookie, Depends, HTTPException
from backend.db import auth_client, service_client


@dataclass
class Principal:
    id: str
    email: str
    role: Literal["participant", "reviewer", "admin"]


def current_user(qyron_session: str | None = Cookie(default=None)) -> Principal:
    if not qyron_session:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    try:
        verified = auth_client().auth.get_user(qyron_session)
        user = verified.user
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Your session expired. Please sign in again.") from exc
    if not user:
        raise HTTPException(status_code=401, detail="Please sign in to continue.")
    if not getattr(user, "email_confirmed_at", None):
        raise HTTPException(status_code=403, detail="Verify your email before using the participant portal.")
    profile = service_client().table("profiles").select("role").eq("id", user.id).maybe_single().execute().data
    role = profile.get("role", "participant") if profile else "participant"
    return Principal(id=user.id, email=user.email or "", role=role)


def admin_user(user: Principal = Depends(current_user)) -> Principal:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required.")
    return user


def reviewer_user(user: Principal = Depends(current_user)) -> Principal:
    if user.role not in {"admin", "reviewer"}:
        raise HTTPException(status_code=403, detail="Reviewer access is required.")
    return user
