import logging
from fastapi import APIRouter, Depends, HTTPException, Response

try:
    from supabase_auth.errors import AuthApiError
except ImportError:
    try:
        from gotrue.errors import AuthApiError
    except ImportError:
        AuthApiError = Exception

from backend.auth import current_user
from backend.config import settings
from backend.db import auth_client, service_client
from backend.mailer import extract_action_link, send_verification_email
from backend.models import LoginInput, ResendVerificationInput, SignupInput

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/login")
def login(payload: LoginInput, response: Response):
    try:
        session = auth_client().auth.sign_in_with_password({"email": str(payload.email), "password": payload.password}).session
    except AuthApiError as exc:
        raise HTTPException(status_code=401, detail="Email or password is incorrect.") from exc
    if not session:
        raise HTTPException(status_code=401, detail="Email verification is required before signing in.")
    response.set_cookie(
        "qyron_session", session.access_token, httponly=True, secure=settings().cookie_secure,
        samesite="lax", max_age=max(60, session.expires_in), path="/",
    )
    return {"ok": True}


@router.post("/signup", status_code=201)
def signup(payload: SignupInput):
    cfg = settings()
    email_str = str(payload.email).strip().lower()
    redirect_url = cfg.supabase_email_redirect_url or "http://127.0.0.1:8000/portal"

    if cfg.has_smtp:
        try:
            # Generate link via Supabase Admin API without triggering Supabase mailer
            link_res = service_client().auth.admin.generate_link({
                "type": "signup",
                "email": email_str,
                "password": payload.password,
                "options": {"redirect_to": redirect_url},
            })
            action_link = extract_action_link(link_res)
            if not action_link:
                raise HTTPException(status_code=500, detail="Could not generate email verification link from Supabase.")
            send_verification_email(email_str, action_link)
        except AuthApiError as exc:
            msg = str(exc)
            if "already registered" in msg.lower() or "already exists" in msg.lower():
                raise HTTPException(
                    status_code=409,
                    detail="An account with this email already exists. Sign in or request a new verification link.",
                ) from exc
            raise HTTPException(status_code=400, detail=f"Signup failed: {msg}") from exc
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("Failed to dispatch verification email via manual SMTP")
            raise HTTPException(
                status_code=500,
                detail=f"Account created, but sending verification email failed: {exc}. Verify SMTP_EMAIL and SMTP_APP_PASSWORD in .env.",
            ) from exc
        return {"ok": True, "message": "Verification email sent! Check your inbox (and spam folder) to verify your account, then sign in."}

    # Fallback to Supabase built-in auth mailer
    try:
        credentials = {"email": email_str, "password": payload.password}
        if redirect_url:
            credentials["options"] = {"email_redirect_to": redirect_url}
        auth_client().auth.sign_up(credentials)
    except AuthApiError as exc:
        raise HTTPException(status_code=400, detail="Account could not be created. Check the email and try again.") from exc
    return {"ok": True, "message": "Check your email to verify the account, then sign in."}


@router.post("/resend-verification")
def resend_verification(payload: ResendVerificationInput):
    cfg = settings()
    email_str = str(payload.email).strip().lower()
    redirect_url = cfg.supabase_email_redirect_url or "http://127.0.0.1:8000/portal"

    if cfg.has_smtp:
        try:
            link_res = service_client().auth.admin.generate_link({
                "type": "magiclink",
                "email": email_str,
                "options": {"redirect_to": redirect_url},
            })
            action_link = extract_action_link(link_res)
            if not action_link:
                raise HTTPException(status_code=500, detail="Could not generate email verification link.")
            send_verification_email(email_str, action_link)
        except Exception as exc:
            logger.exception("Failed to resend verification email via manual SMTP")
            raise HTTPException(
                status_code=400,
                detail=f"Could not resend verification email: {exc}. Ensure the email is registered.",
            ) from exc
        return {"ok": True, "message": "A new verification link has been sent to your email."}

    try:
        auth_client().auth.resend({
            "type": "signup",
            "email": email_str,
            "options": {"email_redirect_to": redirect_url},
        })
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not resend verification email: {exc}") from exc
    return {"ok": True, "message": "A new verification link has been sent to your email."}


@router.get("/me")
def me(user=Depends(current_user)):
    return {"id": user.id, "email": user.email, "role": user.role}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("qyron_session", path="/", httponly=True, samesite="lax", secure=settings().cookie_secure)
    return {"ok": True}
