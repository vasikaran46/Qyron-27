"""
QYRON'27 — SMTP Email Diagnostics & Verification Tool
Tests Gmail SMTP credentials and outbound dispatch.

Usage:
  python tools/test_smtp.py
  python tools/test_smtp.py --to recipient@example.com
"""

import sys
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.config import settings

def main():
    print("=" * 65)
    print(" QYRON'27 — SMTP CONFIGURATION & DISPATCH DIAGNOSTICS")
    print("=" * 65)

    cfg = settings()

    if not cfg.smtp_email or not cfg.smtp_app_password:
        print("[!] SMTP credentials NOT configured in .env")
        print("\nTo enable automated transactional emails:")
        print("  1. In Google Account: Enable 2-Step Verification")
        print("  2. Visit: https://myaccount.google.com/apppasswords")
        print("  3. Create an App Password (name it 'QYRON 27')")
        print("  4. Add to .env:")
        print("     SMTP_EMAIL=your-email@gmail.com")
        print("     SMTP_APP_PASSWORD=your-16-char-app-password")
        print("     SMTP_HOST=smtp.gmail.com")
        print("     SMTP_PORT=587")
        print("     SMTP_FROM_NAME=QYRON'27 Organizers")
        sys.exit(1)

    print(f"[*] Target Host  : {cfg.smtp_host}:{cfg.smtp_port}")
    print(f"[*] Sender Email : {cfg.smtp_email}")
    print(f"[*] Sender Name  : {cfg.smtp_from_name}")
    print(f"[*] TLS Active   : {cfg.smtp_use_tls}")

    password_clean = cfg.smtp_app_password.replace(" ", "")

    print("\n[*] Establishing connection to mail server...")
    try:
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=15) as server:
            server.ehlo()
            if cfg.smtp_use_tls or cfg.smtp_port == 587:
                print("[*] Initiating STARTTLS encryption...")
                server.starttls()
                server.ehlo()

            print("[*] Authenticating with application credentials...")
            server.login(cfg.smtp_email, password_clean)
            print("[+] SUCCESS: SMTP Authentication successful!")

            target_to = None
            if "--to" in sys.argv:
                idx = sys.argv.index("--to")
                if idx + 1 < len(sys.argv):
                    target_to = sys.argv[idx + 1]

            if target_to:
                print(f"[*] Dispatching test message to: {target_to}")
                msg = MIMEMultipart()
                msg["Subject"] = "QYRON'27 — SMTP Diagnostics Test Dispatch"
                msg["From"] = formataddr((cfg.smtp_from_name, cfg.smtp_email))
                msg["To"] = target_to
                body = "This is a verification test email confirming your QYRON'27 SMTP configuration is operational."
                msg.attach(MIMEText(body, "plain", "utf-8"))
                server.sendmail(cfg.smtp_email, target_to, msg.as_string())
                print(f"[+] Test message dispatched successfully to {target_to}!")

    except smtplib.SMTPAuthenticationError as auth_err:
        print("\n[ERROR] SMTP Authentication Failed!")
        print(f" Details: {auth_err}")
        print(" Hint: Ensure you are using a 16-character Google 'App Password', NOT your standard Gmail account password.")
        print(" Generate one at: https://myaccount.google.com/apppasswords")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] SMTP Connection Failed: {e}")
        sys.exit(1)

    print("\n" + "=" * 65)
    print(" ALL SMTP CHECKS VERIFIED SUCCESSFULLY!")
    print("=" * 65)

if __name__ == "__main__":
    main()
