"""
QYRON'27 — Google Drive Upload Verification Tool
Tests if presentation files can be uploaded directly to the destination Google Drive
using either:
  1. Google Apps Script Webhook (GOOGLE_DRIVE_WEBHOOK_URL)
  2. Google Service Account (service_account.json or GOOGLE_SERVICE_ACCOUNT_JSON)
  3. Google OAuth2 Refresh Token

Usage:
    .\\venv\\Scripts\\python tools\\test_gdrive_upload.py
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

from backend.services.gdrive import gdrive_service


def test():
    print("=" * 65)
    print(" QYRON'27 — GOOGLE DRIVE INTEGRATION TEST")
    print("=" * 65)

    webhook_url = os.getenv("GOOGLE_DRIVE_WEBHOOK_URL", "").strip() or gdrive_service.webhook_url
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip() or gdrive_service.folder_id
    sa_path = PROJECT_ROOT / "service_account.json"

    print(f"[*] Target Folder ID : {folder_id or '(Default / Root)'}")

    if webhook_url:
        print(f"[+] Found GOOGLE_DRIVE_WEBHOOK_URL: {webhook_url[:40]}...")
    elif sa_path.exists():
        print(f"[+] Found 'service_account.json' in project root!")
    elif gdrive_service.sa_json_raw:
        print("[+] Found GOOGLE_SERVICE_ACCOUNT_JSON in .env")
    elif gdrive_service.refresh_token:
        print("[+] Found OAuth2 Refresh Token credentials")
    else:
        print("\n[!] WARNING: No Google Drive credentials found in .env or project root.")
        print("    To upload files directly to your personal Google Drive:")
        print("    1. Open and follow instructions in 'google_apps_script.js'")
        print("    2. Add GOOGLE_DRIVE_WEBHOOK_URL=https://script.google.com/macros/s/.../exec to .env")
        print("    3. Or add 'service_account.json' to the project root directory.\n")
        return

    print("\n[*] Uploading test presentation file to Google Drive...")
    test_content = b"QYRON'27 Quantum Innovation Hackathon - Test Presentation File for Google Drive Verification"
    filename = "QYRON27_Drive_Verification_Test.txt"

    success, result_or_err, file_id = gdrive_service.upload_file(
        file_bytes=test_content,
        filename=filename,
        mime_type="text/plain"
    )

    if success:
        print("\n" + "=" * 65)
        print(" [SUCCESS] File successfully uploaded to your Google Drive!")
        print("=" * 65)
        print(f" View URL: {result_or_err}")
        print(f" File ID:  {file_id}")
        print("\n All participant PPT & PDF submissions will now be uploaded automatically here.")
    else:
        print("\n" + "=" * 65)
        print(" [ERROR] Google Drive Upload Failed")
        print("=" * 65)
        print(f" Error: {result_or_err}\n")
        print(" Tips:")
        print(" - For Apps Script: ensure 'Who has access' was set to 'Anyone' during deployment.")
        print(" - For Service Account: ensure your Google Drive folder is shared with the service account email.")


if __name__ == "__main__":
    test()
