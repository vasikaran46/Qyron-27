"""
QYRON'27 — Google Drive Integration Service
Uploads participant presentation files (.pptx, .ppt, .pdf) directly
to the organizer's Google Drive and returns shareable Google Drive URLs
for permanent storage and evaluation.

Supported Authentication Methods in .env:
1. Google Apps Script Webhook (Zero-Cloud / No GCP Restrictions, recommended for personal Gmail):
   - GOOGLE_DRIVE_WEBHOOK_URL=https://script.google.com/macros/s/.../exec
   - GOOGLE_DRIVE_FOLDER_ID (Optional: target folder ID inside your Google Drive)

2. Google Cloud Service Account:
   - Drop 'service_account.json' into the project root directory
   - OR set GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account",...} in .env
   - GOOGLE_DRIVE_FOLDER_ID (Destination Google Drive Folder ID)

3. OAuth2 Refresh Token:
   - GOOGLE_DRIVE_CLIENT_ID
   - GOOGLE_DRIVE_CLIENT_SECRET
   - GOOGLE_DRIVE_REFRESH_TOKEN
   - GOOGLE_DRIVE_FOLDER_ID
"""

import os
import time
import json
import base64
import logging
from pathlib import Path
from typing import Optional, Tuple

import httpx

try:
    import jwt
except ImportError:
    jwt = None

logger = logging.getLogger("qyron.gdrive")

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,webViewLink,webContentLink"
GOOGLE_DRIVE_PERMISSIONS_URL = "https://www.googleapis.com/drive/v3/files/{file_id}/permissions"

MIME_MAP = {
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pdf": "application/pdf"
}


class GoogleDriveService:
    def __init__(self):
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()
        self.webhook_url = os.getenv("GOOGLE_DRIVE_WEBHOOK_URL", "").strip() or os.getenv("GOOGLE_DRIVE_SCRIPT_URL", "").strip()
        self.sa_json_raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
        self.sa_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()
        self.access_token = os.getenv("GOOGLE_DRIVE_ACCESS_TOKEN", "").strip() or os.getenv("GOOGLE_DRIVE_API_KEY", "").strip()
        self.client_id = os.getenv("GOOGLE_DRIVE_CLIENT_ID", "").strip()
        self.client_secret = os.getenv("GOOGLE_DRIVE_CLIENT_SECRET", "").strip()
        self.refresh_token = os.getenv("GOOGLE_DRIVE_REFRESH_TOKEN", "").strip()

        # Check for service_account.json in project root automatically
        auto_sa_path = self.project_root / "service_account.json"
        if not self.sa_file and auto_sa_path.exists():
            self.sa_file = str(auto_sa_path)

    def is_configured(self) -> bool:
        """Returns True if any valid Google Drive authentication method is provided."""
        webhook = os.getenv("GOOGLE_DRIVE_WEBHOOK_URL", "").strip() or self.webhook_url
        sa_raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip() or self.sa_json_raw
        sa_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip() or self.sa_file
        auto_sa = (self.project_root / "service_account.json").exists()
        refresh = os.getenv("GOOGLE_DRIVE_REFRESH_TOKEN", "").strip() or self.refresh_token
        client_id = os.getenv("GOOGLE_DRIVE_CLIENT_ID", "").strip() or self.client_id
        return bool(webhook or sa_raw or sa_file or auto_sa or (refresh and client_id))

    def _get_access_token_from_service_account(self, sa_data: dict) -> Optional[str]:
        """Exchanges a Google Service Account JWT for a short-lived Bearer access token."""
        if not jwt:
            logger.error("PyJWT is required for Service Account authentication.")
            return None
        try:
            client_email = sa_data.get("client_email")
            private_key = sa_data.get("private_key")
            if not (client_email and private_key):
                logger.error("Service Account JSON missing 'client_email' or 'private_key'")
                return None

            now = int(time.time())
            payload = {
                "iss": client_email,
                "scope": "https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/drive",
                "aud": GOOGLE_TOKEN_URL,
                "exp": now + 3600,
                "iat": now,
            }

            signed_jwt = jwt.encode(payload, private_key, algorithm="RS256")
            with httpx.Client(timeout=15) as client:
                res = client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                        "assertion": signed_jwt,
                    }
                )
            if res.status_code == 200:
                token = res.json().get("access_token")
                logger.info("Authenticated via Google Service Account (%s)", client_email)
                return token
            else:
                logger.error("Failed to obtain Google access token: %s", res.text)
                return None
        except Exception as e:
            logger.error("Error creating Google JWT / access token: %s", e)
            return None

    def _get_access_token_from_refresh_token(self) -> Optional[str]:
        """Refreshes an OAuth2 access token using client credentials and refresh token."""
        client_id = os.getenv("GOOGLE_DRIVE_CLIENT_ID", "").strip() or self.client_id
        client_secret = os.getenv("GOOGLE_DRIVE_CLIENT_SECRET", "").strip() or self.client_secret
        refresh_token = os.getenv("GOOGLE_DRIVE_REFRESH_TOKEN", "").strip() or self.refresh_token

        if not (client_id and client_secret and refresh_token):
            return None

        try:
            with httpx.Client(timeout=15) as client:
                res = client.post(
                    GOOGLE_TOKEN_URL,
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    }
                )
            if res.status_code == 200:
                return res.json().get("access_token")
            logger.error("Failed to refresh OAuth token: %s", res.text)
            return None
        except Exception as e:
            logger.error("Exception refreshing OAuth token: %s", e)
            return None

    def get_token(self) -> Tuple[Optional[str], Optional[str]]:
        """Resolves a valid Bearer access token from configured credentials."""
        # 1. Check Service Account JSON file in root or specified path
        sa_file_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip() or self.sa_file
        if not sa_file_path:
            auto_path = self.project_root / "service_account.json"
            if auto_path.exists():
                sa_file_path = str(auto_path)

        if sa_file_path and Path(sa_file_path).exists():
            try:
                with open(sa_file_path, "r", encoding="utf-8") as f:
                    sa_data = json.load(f)
                token = self._get_access_token_from_service_account(sa_data)
                if token:
                    return token, None
            except Exception as e:
                logger.error("Could not parse Service Account JSON file: %s", e)

        # 2. Check Service Account JSON string in .env
        sa_json_raw = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip() or self.sa_json_raw
        if sa_json_raw:
            try:
                sa_data = json.loads(sa_json_raw)
                token = self._get_access_token_from_service_account(sa_data)
                if token:
                    return token, None
            except Exception as e:
                logger.error("Could not parse GOOGLE_SERVICE_ACCOUNT_JSON: %s", e)

        # 3. Check OAuth2 Refresh Token
        token = self._get_access_token_from_refresh_token()
        if token:
            return token, None

        return None, "No Google Drive credentials configured"

    def _upload_via_apps_script(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: str,
        folder_id: Optional[str]
    ) -> Tuple[bool, str, Optional[str]]:
        """Uploads file through a deployed Google Apps Script Webhook."""
        webhook_url = os.getenv("GOOGLE_DRIVE_WEBHOOK_URL", "").strip() or os.getenv("GOOGLE_DRIVE_SCRIPT_URL", "").strip() or self.webhook_url
        if not webhook_url:
            return False, "Google Apps Script Webhook URL not set in GOOGLE_DRIVE_WEBHOOK_URL", None

        try:
            b64_str = base64.b64encode(file_bytes).decode("utf-8")
            target_folder = folder_id or os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip() or self.folder_id
            payload = {
                "filename": filename,
                "mimeType": mime_type,
                "base64": b64_str,
                "folderId": target_folder
            }
            with httpx.Client(timeout=45.0, follow_redirects=True) as client:
                res = client.post(webhook_url, json=payload)

            content_type = res.headers.get("content-type", "")
            if "text/html" in content_type or res.text.strip().startswith("<!DOCTYPE html>"):
                return False, (
                    "Apps Script returned a Google login page instead of JSON. "
                    "In Apps Script: Click Deploy -> Manage deployments -> Edit -> Ensure 'Who has access' is set to 'Anyone' (not 'Only myself')."
                ), None

            try:
                data = res.json()
            except Exception:
                return False, f"Apps Script returned non-JSON response ({res.status_code}): {res.text[:200]}", None

            if data.get("success") and data.get("url"):
                return True, data.get("url"), data.get("id")
            elif data.get("url"):
                return True, data.get("url"), data.get("id")
            elif data.get("error"):
                return False, f"Apps Script reported error: {data.get('error')}", None

            return False, f"Apps Script unexpected response: {res.text[:200]}", None
        except Exception as e:
            return False, f"Apps Script upload failed: {e}", None

    def upload_file(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: Optional[str] = None,
        folder_id: Optional[str] = None
    ) -> Tuple[bool, str, Optional[str]]:
        """
        Uploads a presentation file to the designated Google Drive folder.
        Sets permission to public-readable ('Anyone with link can view').
        Returns (success, message_or_url, file_id).
        """
        if not mime_type:
            ext = Path(filename).suffix.lower()
            mime_type = MIME_MAP.get(ext, "application/octet-stream")

        target_folder = folder_id or os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip() or self.folder_id
        active_webhook = os.getenv("GOOGLE_DRIVE_WEBHOOK_URL", "").strip() or os.getenv("GOOGLE_DRIVE_SCRIPT_URL", "").strip() or self.webhook_url

        # 1. Option: Apps Script Webhook (Zero Cloud Configuration)
        if active_webhook:
            logger.info("Uploading '%s' to Google Drive via Apps Script Webhook...", filename)
            return self._upload_via_apps_script(file_bytes, filename, mime_type, target_folder)

        # 2. Option: Google Cloud REST API (Service Account or OAuth)
        token, token_err = self.get_token()
        if not token:
            logger.warning("Google Drive upload aborted: %s", token_err)
            return False, token_err or "Google Drive credentials not configured", None

        metadata = {
            "name": filename,
            "mimeType": mime_type,
        }
        if target_folder:
            metadata["parents"] = [target_folder]

        headers = {
            "Authorization": f"Bearer {token}"
        }

        files = {
            "data": ("metadata", json.dumps(metadata), "application/json; charset=UTF-8"),
            "file": (filename, file_bytes, mime_type)
        }

        try:
            with httpx.Client(timeout=60.0, follow_redirects=True) as client:
                upload_res = client.post(
                    GOOGLE_DRIVE_UPLOAD_URL,
                    headers=headers,
                    files=files
                )

                if upload_res.status_code not in (200, 201):
                    err_text = upload_res.text
                    logger.error("Google Drive upload failed (%s): %s", upload_res.status_code, err_text)
                    return False, f"Google Drive API error: {err_text}", None

                data = upload_res.json()
                file_id = data.get("id")
                if not file_id:
                    return False, "No file ID returned by Google Drive", None

                # Attempt to set public read permission so jury can open it
                try:
                    client.post(
                        GOOGLE_DRIVE_PERMISSIONS_URL.format(file_id=file_id),
                        headers=headers,
                        json={"role": "reader", "type": "anyone"}
                    )
                except Exception as perm_err:
                    logger.warning("Could not set public permission on Drive file %s: %s", file_id, perm_err)

                view_url = data.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
                logger.info("File successfully uploaded to Google Drive: %s", view_url)
                return True, view_url, file_id

        except Exception as e:
            logger.error("Exception during Google Drive upload: %s", e)
            return False, str(e), None


# Singleton instance
gdrive_service = GoogleDriveService()
