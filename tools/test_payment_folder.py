import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.services.gdrive import GoogleDriveService
from backend.config import settings

def test_payment_folder_config():
    service = GoogleDriveService()
    service.folder_id = ""
    service.payment_folder_id = ""
    
    # 1. Fallback to main folder when payment folder is empty
    with patch.dict(os.environ, {"GOOGLE_DRIVE_FOLDER_ID": "main_folder_123", "GOOGLE_DRIVE_PAYMENT_FOLDER_ID": ""}):
        folder = service.get_payment_folder_id()
        assert folder == "main_folder_123", f"Expected main_folder_123, got {folder}"
        print("[OK] Fallback to main folder works when payment folder is not set.")

    # 2. Dedicated GOOGLE_DRIVE_PAYMENT_FOLDER_ID
    with patch.dict(os.environ, {"GOOGLE_DRIVE_FOLDER_ID": "main_folder_123", "GOOGLE_DRIVE_PAYMENT_FOLDER_ID": "payment_folder_456"}):
        folder = service.get_payment_folder_id()
        assert folder == "payment_folder_456", f"Expected payment_folder_456, got {folder}"
        print("[OK] GOOGLE_DRIVE_PAYMENT_FOLDER_ID correctly picked up.")

    # 3. Dedicated GOOGLE_DRIVE_TRANSACTION_FOLDER_ID alias
    with patch.dict(os.environ, {"GOOGLE_DRIVE_FOLDER_ID": "main_folder_123", "GOOGLE_DRIVE_PAYMENT_FOLDER_ID": "", "GOOGLE_DRIVE_TRANSACTION_FOLDER_ID": "txn_folder_789"}):
        folder = service.get_payment_folder_id()
        assert folder == "txn_folder_789", f"Expected txn_folder_789, got {folder}"
        print("[OK] GOOGLE_DRIVE_TRANSACTION_FOLDER_ID alias correctly picked up.")

    # 4. Verify upload_payment_screenshot calls upload_file with target folder
    with patch.dict(os.environ, {"GOOGLE_DRIVE_PAYMENT_FOLDER_ID": "payment_folder_456"}):
        with patch.object(service, "upload_file", return_value=(True, "http://drive.url", "file_123")) as mock_upload:
            res = service.upload_payment_screenshot(b"dummy bytes", "test_screenshot.jpg", "image/jpeg")
            mock_upload.assert_called_once_with(
                file_bytes=b"dummy bytes",
                filename="test_screenshot.jpg",
                mime_type="image/jpeg",
                folder_id="payment_folder_456"
            )
            print("[OK] upload_payment_screenshot correctly targets payment folder ID.")

if __name__ == "__main__":
    test_payment_folder_config()
    print("\nALL PAYMENT FOLDER INTEGRATION TESTS PASSED!")
