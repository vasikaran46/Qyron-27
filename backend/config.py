import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_anon_key = os.getenv("SUPABASE_PUBLISHABLE_KEY", os.getenv("SUPABASE_ANON_KEY", ""))
    supabase_service_role_key = os.getenv("SUPABASE_SECRET_KEY", os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
    supabase_email_redirect_url = os.getenv("SUPABASE_EMAIL_REDIRECT_URL", "")
    cookie_secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    allowed_origins = [origin.strip() for origin in os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:8000,http://localhost:8000").split(",") if origin.strip()]

    # Manual SMTP Settings
    smtp_email = os.getenv("SMTP_EMAIL", "").strip()
    smtp_app_password = os.getenv("SMTP_APP_PASSWORD", "").strip()
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_use_tls = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
    smtp_use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
    smtp_from_name = os.getenv("SMTP_FROM_NAME", "QYRON'27 Organizers").strip()

    # Google Drive Direct Storage Settings
    google_drive_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "").strip()
    google_drive_payment_folder_id = (
        os.getenv("GOOGLE_DRIVE_PAYMENT_FOLDER_ID", "").strip()
        or os.getenv("GOOGLE_DRIVE_TRANSACTION_FOLDER_ID", "").strip()
        or os.getenv("GDRIVE_PAYMENT_FOLDER_ID", "").strip()
        or os.getenv("GDRIVE_TRANSACTION_FOLDER_ID", "").strip()
    )
    google_drive_webhook_url = os.getenv("GOOGLE_DRIVE_WEBHOOK_URL", "").strip() or os.getenv("GOOGLE_DRIVE_SCRIPT_URL", "").strip()
    google_service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    google_service_account_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "").strip()

    # UPI QR Payment Settings
    upi_id = os.getenv("UPI_ID", "karanvasi80@okhdfcbank").strip()
    upi_payee_name = os.getenv("UPI_PAYEE_NAME", "Vasikaran A").strip()
    upi_amount = int(os.getenv("UPI_AMOUNT", "150"))
    upi_qr_image = os.getenv("UPI_QR_IMAGE", "/assets/upi-qr-scanner.jpg").strip()

    @property
    def has_smtp(self) -> bool:
        return bool(self.smtp_email and self.smtp_app_password)

    @property
    def has_gdrive(self) -> bool:
        return bool(self.google_drive_webhook_url or self.google_service_account_json or self.google_service_account_file)


@lru_cache
def settings() -> Settings:
    return Settings()
