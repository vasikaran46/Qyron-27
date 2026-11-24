"""
SMTP Email Service for QYRON'27
Two-Phase Registration & Payment Email Workflow:
1. send_registration_pending_email: Dispatched immediately upon squad registration with UPI UTR.
   Notifies the team lead that registration & UTR reference are logged and currently under committee verification.
2. send_payment_verified_email: Dispatched when an organizer marks the payment as VERIFIED in the Admin Panel.
   Delivers the participant portal login credentials (username and temporary password) so the squad can log in
   and submit their Proposal Dossier (Title, Abstract, Architecture) and Presentation Slide Deck (.pptx / .pdf).

Uses Gmail SMTP with App Password authentication.
"""

import os
import smtplib
import ssl
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Any

from backend.config import settings

logger = logging.getLogger(__name__)

DEFAULT_PORTAL_URL = "http://127.0.0.1:8000/login"


def _build_registration_confirmed_html(
    leader_name: str,
    team_code: str,
    team_name: str,
    track: str,
    utr_number: str,
    username: str,
    password: str,
    portal_url: str = DEFAULT_PORTAL_URL,
    college_name: str = ""
) -> str:
    """Builds HTML email sent immediately upon registration, delivering portal credentials and proposal instructions."""
    return f"""\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #222; line-height: 1.7; margin: 0; padding: 0; background: #f4f4f4; }}
  .container {{ max-width: 640px; margin: 30px auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  .college-header {{ background: #ffffff; padding: 24px 30px; text-align: center; border-bottom: 3px solid #2e7d32; }}
  .college-header table {{ width: 100%; border-collapse: collapse; }}
  .college-header td {{ vertical-align: middle; }}
  .college-header .college-text {{ text-align: center; }}
  .college-header .college-text h2 {{ margin: 0; font-size: 22px; color: #2e7d32; font-weight: 800; letter-spacing: 1px; }}
  .college-header .college-text h3 {{ margin: 2px 0 0; font-size: 16px; color: #2e7d32; font-weight: 700; }}
  .college-header .college-text .subtitle {{ margin: 3px 0 0; font-size: 12px; color: #555; font-style: italic; }}
  .college-header .college-text .affiliation {{ margin: 3px 0 0; font-size: 11px; color: #777; }}
  .college-header .dept-badge {{ display: inline-block; background: #e8f5e9; color: #1b5e20; font-weight: 700; font-size: 12px; padding: 4px 12px; border-radius: 12px; margin-top: 6px; letter-spacing: 0.5px; }}
  .body-content {{ padding: 30px 40px; }}
  .body-content p {{ margin: 10px 0; }}
  .details-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
  .details-table td {{ padding: 10px 14px; border-bottom: 1px solid #e0e0e0; }}
  .details-table td:first-child {{ font-weight: 600; color: #455a64; width: 42%; }}
  .details-table td:last-child {{ color: #1a237e; font-weight: 500; }}
  .credentials-box {{ background: linear-gradient(135deg, #09120c, #132418); color: #ffffff; border: 2px solid #00e5ff; border-radius: 8px; padding: 22px 24px; margin: 24px 0; box-shadow: 0 4px 16px rgba(0, 229, 255, 0.15); }}
  .credentials-box h4 {{ margin: 0 0 10px; color: #00e5ff; font-size: 16px; letter-spacing: 1px; }}
  .cred-table {{ width: 100%; border-collapse: collapse; margin: 10px 0 16px; }}
  .cred-table td {{ padding: 8px 6px; color: #e0e0e0; font-size: 14px; border-bottom: 1px solid rgba(255,255,255,0.1); }}
  .cred-table td:first-child {{ width: 35%; color: #81c784; font-weight: 600; }}
  .cred-val {{ font-family: 'Space Mono', Consolas, monospace; background: rgba(0,0,0,0.4); padding: 4px 10px; border-radius: 4px; color: #ffffff; font-weight: 700; letter-spacing: 0.5px; border: 1px solid rgba(0,229,255,0.3); }}
  .btn-portal {{ display: inline-block; background: #00e5ff; color: #050706 !important; padding: 12px 28px; font-weight: 800; font-size: 13px; letter-spacing: 1px; text-decoration: none; border-radius: 4px; text-transform: uppercase; margin-top: 8px; }}
  .status-box {{ background: #fffbeb; border: 1.5px solid #f59e0b; border-left: 5px solid #d97706; padding: 16px 20px; margin: 22px 0; border-radius: 4px; }}
  .status-box h4 {{ margin: 0 0 6px; color: #92400e; font-size: 14.5px; }}
  .status-box p {{ margin: 0; font-size: 13px; color: #78350f; line-height: 1.6; }}
  .info-box {{ background: #e8f5e9; border-left: 4px solid #43a047; padding: 16px 20px; margin: 20px 0; border-radius: 4px; }}
  .info-box ol {{ margin: 8px 0 0 18px; padding: 0; }}
  .info-box li {{ margin: 6px 0; font-size: 13px; color: #2e7d32; }}
  .event-box {{ background: #e3f2fd; border-left: 4px solid #1e88e5; padding: 16px 20px; margin: 20px 0; border-radius: 4px; }}
  .event-box ul {{ margin: 8px 0 0 18px; padding: 0; list-style: disc; }}
  .event-box li {{ margin: 4px 0; font-size: 13px; color: #1565c0; }}
  .footer {{ background: #263238; color: #b0bec5; text-align: center; padding: 22px 40px; font-size: 12px; }}
  .footer strong {{ color: #ffffff; }}
  .tagline {{ color: #00838f; font-style: italic; margin-top: 10px; }}
</style>
</head>
<body>
<div class="container">
  <!-- College Letterhead Header -->
  <div class="college-header">
    <table role="presentation">
      <tr>
        <td class="college-text">
          <h2>PATRICIAN</h2>
          <h3>COLLEGE OF ARTS AND SCIENCE</h3>
          <p class="subtitle">An Institute of the Brothers of St. Patrick</p>
          <p class="affiliation">Affiliated to the University of Madras | Accredited 'A+' Grade By NAAC</p>
          <span class="dept-badge">DEPARTMENT OF MATHEMATICS</span>
        </td>
      </tr>
    </table>
  </div>

  <div class="body-content">
    <p>Dear <strong>{leader_name}</strong>,</p>
    <p>Greetings from the <strong>Department of Mathematics, Patrician College of Arts and Science!</strong></p>
    <p>Thank you for submitting your squad registration for <strong>QYRON'27 — 24-Hour National Quantum Computing &amp; Mathematical Innovation Hackathon</strong>.</p>
    <p>Your team details and UPI payment transaction reference have been successfully recorded in our registration registry. Your participant portal account has been activated immediately so you can begin drafting your proposal.</p>

    <!-- Registration Details Table -->
    <h3 style="color: #1a237e; border-bottom: 2px solid #e0e0e0; padding-bottom: 6px; margin-top: 24px;">Registration Application Dossier</h3>
    <table class="details-table">
      <tr><td>Event</td><td><strong>QYRON'27 Hackathon</strong></td></tr>
      <tr><td>Registration ID</td><td><strong style="color:#00838f; font-size:15px;">{team_code}</strong></td></tr>
      <tr><td>Team Callsign</td><td><strong>{team_name}</strong></td></tr>
      <tr><td>Institution</td><td>{college_name or 'Patrician College / Collegiate Partner'}</td></tr>
      <tr><td>Operational Track</td><td><strong>{track}</strong></td></tr>
      <tr><td>Initial Entry Fee</td><td>&#8377;150 per Squad</td></tr>
      <tr><td>Submitted UPI UTR / Ref</td><td><code style="font-family:monospace; background:#f1f5f9; padding:2px 6px; border-radius:3px; color:#0f172a; font-weight:700;">{utr_number}</code></td></tr>
      <tr><td>Registration Status</td><td><span style="color: #2e7d32; font-weight: 700;">&#9989; Registered &amp; Credentials Dispatched</span></td></tr>
    </table>

    <!-- PORTAL LOGIN CREDENTIALS BOX -->
    <div class="credentials-box">
      <h4>&#128273; YOUR PARTICIPANT PORTAL CREDENTIALS</h4>
      <p style="margin: 0 0 10px; font-size: 13px; color: #b0bec5;">Log in right away to submit your proposal abstract, technical architecture, and upload your presentation slide deck:</p>
      <table class="cred-table" role="presentation">
        <tr>
          <td>Portal Login URL:</td>
          <td><a href="{portal_url}" style="color:#00e5ff; text-decoration:underline;">{portal_url}</a></td>
        </tr>
        <tr>
          <td>Username (Email):</td>
          <td><span class="cred-val">{username}</span></td>
        </tr>
        <tr>
          <td>Portal Password:</td>
          <td><span class="cred-val">{password}</span></td>
        </tr>
      </table>
      <div style="text-align: center; margin-top: 14px;">
        <a class="btn-portal" href="{portal_url}" target="_blank" rel="noopener noreferrer">LOGIN TO PORTAL &amp; SUBMIT PROPOSAL &#10148;</a>
      </div>
    </div>

    <!-- PAYMENT VERIFICATION NOTICE -->
    <div class="status-box">
      <h4>&#9888; UPI Payment Verification Note</h4>
      <p>
        Your submitted 12-digit UPI reference number (<strong>{utr_number}</strong>) for &#8377;150 is currently being cross-checked against official college bank accounts by our organizing committee.
        <br><br>
        <strong>Note:</strong> You do NOT need to wait for payment verification to submit your proposal! Log in to the portal right away using the credentials above and submit your proposal title, abstract, and presentation slide deck.
        Once your transfer is confirmed by our accounts team, you will receive an official <strong>Payment Verified Email</strong>.
      </p>
    </div>

    <!-- PROPOSAL SUBMISSION NEXT STEPS -->
    <div class="info-box">
      <strong>Action Required: Submit Your Proposal Dossier in Portal</strong>
      <ol>
        <li>Click the button above or visit <a href="{portal_url}" style="color:#2e7d32; font-weight:bold;">{portal_url}</a> and log in.</li>
        <li>Enter your <strong>Proposal / Project Title</strong>, <strong>Executive Abstract</strong>, and <strong>Technical Architecture &amp; Methodology</strong>.</li>
        <li>Upload your team's official <strong>Presentation Slide Deck (.pptx, .ppt, or .pdf)</strong>.</li>
        <li>Your presentation file is automatically stored securely in Google Drive for our academic jury review.</li>
        <li><strong>Proposal Deadline:</strong> Ensure your dossier is submitted in the portal by <strong>25 January 2027 · 11:59 PM IST</strong>.</li>
      </ol>
    </div>

    <!-- EVENT TIMELINE -->
    <div class="event-box">
      <strong>Important Hackathon Dates &amp; Milestones</strong>
      <ul>
        <li><strong>Proposal Submission Deadline:</strong> 25 January 2027 (in Participant Portal)</li>
        <li><strong>Announcement of Top 30 Shortlisted Finalists:</strong> 28 January 2027</li>
        <li><strong>Grand 24-Hour On-Campus Hackathon:</strong> 12–13 February 2027</li>
        <li><strong>Finalist Round Fee:</strong> &#8377;350 per member (applicable only to shortlisted teams)</li>
        <li><strong>Venue:</strong> Patrician College of Arts and Science, Adyar, Chennai &ndash; 600 020</li>
      </ul>
    </div>

    <p>Please preserve this email for your records. If you have any questions regarding your registration, please reply to this email quoting your Registration ID: <strong>{team_code}</strong>.</p>

    <p style="margin-top: 24px;">
      Warm Regards,<br>
      <strong>Organising Committee &mdash; QYRON'27</strong><br>
      Department of Mathematics<br>
      Patrician College of Arts and Science<br>
      Canal Bank Road, Gandhi Nagar, Adyar, Chennai &ndash; 600 020
    </p>
    <p class="tagline"><em>Quantum Coherence. Mathematical Precision.</em></p>
  </div>
  <div class="footer">
    <p><strong>QYRON'27</strong> &mdash; Department of Mathematics, Patrician College of Arts and Science</p>
    <p>This automated notification was delivered regarding Registration ID: {team_code}.</p>
  </div>
</div>
</body>
</html>"""


def _build_verified_html(
    leader_name: str,
    team_code: str,
    team_name: str,
    track: str,
    utr_number: str,
    username: str,
    password: str,
    portal_url: str = DEFAULT_PORTAL_URL,
    college_name: str = ""
) -> str:
    """Builds the HTML email body after the payment has been manually verified by the admin."""
    return f"""\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; color: #222; line-height: 1.7; margin: 0; padding: 0; background: #f4f4f4; }}
  .container {{ max-width: 640px; margin: 30px auto; background: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
  .college-header {{ background: #ffffff; padding: 24px 30px; text-align: center; border-bottom: 3px solid #2e7d32; }}
  .college-header table {{ width: 100%; border-collapse: collapse; }}
  .college-header td {{ vertical-align: middle; }}
  .college-header .college-text {{ text-align: center; }}
  .college-header .college-text h2 {{ margin: 0; font-size: 22px; color: #2e7d32; font-weight: 800; letter-spacing: 1px; }}
  .college-header .college-text h3 {{ margin: 2px 0 0; font-size: 16px; color: #2e7d32; font-weight: 700; }}
  .college-header .college-text .subtitle {{ margin: 3px 0 0; font-size: 12px; color: #555; font-style: italic; }}
  .college-header .college-text .affiliation {{ margin: 3px 0 0; font-size: 11px; color: #777; }}
  .college-header .dept-badge {{ display: inline-block; background: #e8f5e9; color: #1b5e20; font-weight: 700; font-size: 12px; padding: 4px 12px; border-radius: 12px; margin-top: 6px; letter-spacing: 0.5px; }}
  .body-content {{ padding: 30px 40px; }}
  .body-content p {{ margin: 10px 0; }}
  .details-table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
  .details-table td {{ padding: 10px 14px; border-bottom: 1px solid #e0e0e0; }}
  .details-table td:first-child {{ font-weight: 600; color: #455a64; width: 42%; }}
  .details-table td:last-child {{ color: #1a237e; font-weight: 500; }}
  .credentials-box {{ background: linear-gradient(135deg, #09120c, #132418); color: #ffffff; border: 2px solid #00e5ff; border-radius: 8px; padding: 22px 24px; margin: 24px 0; box-shadow: 0 4px 16px rgba(0, 229, 255, 0.15); }}
  .credentials-box h4 {{ margin: 0 0 12px; color: #00e5ff; font-size: 16px; letter-spacing: 1px; }}
  .cred-table {{ width: 100%; border-collapse: collapse; margin: 10px 0 16px; }}
  .cred-table td {{ padding: 8px 6px; color: #e0e0e0; font-size: 14px; border-bottom: 1px solid rgba(255,255,255,0.1); }}
  .cred-table td:first-child {{ width: 35%; color: #81c784; font-weight: 600; }}
  .cred-val {{ font-family: 'Space Mono', Consolas, monospace; background: rgba(0,0,0,0.4); padding: 4px 10px; border-radius: 4px; color: #ffffff; font-weight: 700; letter-spacing: 0.5px; border: 1px solid rgba(0,229,255,0.3); }}
  .btn-portal {{ display: inline-block; background: #00e5ff; color: #050706 !important; padding: 12px 28px; font-weight: 800; font-size: 13px; letter-spacing: 1px; text-decoration: none; border-radius: 4px; text-transform: uppercase; margin-top: 8px; }}
  .info-box {{ background: #e8f5e9; border-left: 4px solid #43a047; padding: 16px 20px; margin: 20px 0; border-radius: 4px; }}
  .info-box ol {{ margin: 8px 0 0 18px; padding: 0; }}
  .info-box li {{ margin: 6px 0; font-size: 13px; color: #2e7d32; }}
  .event-box {{ background: #e3f2fd; border-left: 4px solid #1e88e5; padding: 16px 20px; margin: 20px 0; border-radius: 4px; }}
  .event-box ul {{ margin: 8px 0 0 18px; padding: 0; list-style: disc; }}
  .event-box li {{ margin: 4px 0; font-size: 13px; color: #1565c0; }}
  .footer {{ background: #263238; color: #b0bec5; text-align: center; padding: 22px 40px; font-size: 12px; }}
  .footer strong {{ color: #ffffff; }}
  .tagline {{ color: #00838f; font-style: italic; margin-top: 10px; }}
</style>
</head>
<body>
<div class="container">
  <!-- College Letterhead Header -->
  <div class="college-header">
    <table role="presentation">
      <tr>
        <td class="college-text">
          <h2>PATRICIAN</h2>
          <h3>COLLEGE OF ARTS AND SCIENCE</h3>
          <p class="subtitle">An Institute of the Brothers of St. Patrick</p>
          <p class="affiliation">Affiliated to the University of Madras | Accredited 'A+' Grade By NAAC</p>
          <span class="dept-badge">DEPARTMENT OF MATHEMATICS</span>
        </td>
      </tr>
    </table>
  </div>

  <div class="body-content">
    <p>Dear <strong>{leader_name}</strong>,</p>
    <p>Greetings from the <strong>Department of Mathematics, Patrician College of Arts and Science!</strong></p>
    <p>We are pleased to inform you that your registration payment of <strong>&#8377;150</strong> (UTR: <strong>{utr_number}</strong>) has been <strong>successfully verified and approved</strong> by the organizing directorate!</p>
    <p>Your squad is officially active and provisioned with full access to the Participant Portal.</p>

    <!-- Registration Details Table -->
    <h3 style="color: #1a237e; border-bottom: 2px solid #e0e0e0; padding-bottom: 6px; margin-top: 24px;">Verified Registration Manifest</h3>
    <table class="details-table">
      <tr><td>Event</td><td><strong>QYRON'27 Hackathon</strong></td></tr>
      <tr><td>Registration ID</td><td><strong style="color:#00838f; font-size:15px;">{team_code}</strong></td></tr>
      <tr><td>Team Callsign</td><td><strong>{team_name}</strong></td></tr>
      <tr><td>Institution</td><td>{college_name or 'Patrician College / Collegiate Partner'}</td></tr>
      <tr><td>Operational Track</td><td><strong>{track}</strong></td></tr>
      <tr><td>Registration Fee</td><td>&#8377;150 per Squad (&#9989; Verified)</td></tr>
      <tr><td>Verified UTR Ref</td><td><code style="font-family:monospace; background:#f1f5f9; padding:2px 6px; border-radius:3px; color:#0f172a; font-weight:700;">{utr_number}</code></td></tr>
      <tr><td>Account Status</td><td><span style="color: #2e7d32; font-weight: 700;">&#9989; Active &amp; Credentials Dispatched</span></td></tr>
    </table>

    <!-- PORTAL LOGIN CREDENTIALS BOX -->
    <div class="credentials-box">
      <h4>&#128273; YOUR PARTICIPANT PORTAL CREDENTIALS</h4>
      <p style="margin: 0 0 10px; font-size: 13px; color: #b0bec5;">Sign in to your team portal to submit your proposal abstract, technical architecture, and slide deck:</p>
      <table class="cred-table" role="presentation">
        <tr>
          <td>Portal Login URL:</td>
          <td><a href="{portal_url}" style="color:#00e5ff; text-decoration:underline;">{portal_url}</a></td>
        </tr>
        <tr>
          <td>Username (Email):</td>
          <td><span class="cred-val">{username}</span></td>
        </tr>
        <tr>
          <td>Portal Password:</td>
          <td><span class="cred-val">{password}</span></td>
        </tr>
      </table>
      <div style="text-align: center; margin-top: 14px;">
        <a class="btn-portal" href="{portal_url}" target="_blank" rel="noopener noreferrer">LOGIN TO PORTAL &amp; SUBMIT PROPOSAL &#10148;</a>
      </div>
    </div>

    <!-- NEXT STEPS: PROPOSAL SUBMISSION INSTRUCTIONS -->
    <div class="info-box">
      <strong>Action Required: Submit Your Proposal Dossier in Portal</strong>
      <ol>
        <li>Click the button above or visit <a href="{portal_url}" style="color:#2e7d32; font-weight:bold;">{portal_url}</a> and log in.</li>
        <li>Enter your <strong>Proposal / Project Title</strong>, <strong>Executive Abstract</strong>, and <strong>Technical Architecture &amp; Methodology</strong>.</li>
        <li>Upload your team's official <strong>Presentation Slide Deck (.pptx, .ppt, or .pdf)</strong>.</li>
        <li>Your presentation file will be automatically stored securely in Google Drive for our academic jury review.</li>
        <li><strong>Proposal Deadline:</strong> Ensure your dossier is submitted in the portal by <strong>25 January 2027 · 11:59 PM IST</strong>.</li>
      </ol>
    </div>

    <!-- EVENT TIMELINE & SHORTLISTING -->
    <div class="event-box">
      <strong>Key Dates &amp; Finalist Information</strong>
      <ul>
        <li><strong>Proposal Submission Deadline:</strong> 25 January 2027 (11:59 PM IST)</li>
        <li><strong>Announcement of Top 30 Shortlisted Finalists:</strong> 28 January 2027</li>
        <li><strong>Grand 24-Hour Final Hackathon:</strong> 12–13 February 2027 (On-Campus)</li>
        <li><strong>Finalist Participation Fee:</strong> &#8377;350 per member (applicable only to shortlisted teams)</li>
        <li><strong>Venue:</strong> Patrician College of Arts and Science, Adyar, Chennai &ndash; 600 020</li>
      </ul>
    </div>

    <p>Please keep these credentials safe. Your Registration ID (<strong>{team_code}</strong>) will be required during check-in and throughout the hackathon.</p>
    <p>We look forward to reviewing your mathematical and quantum innovation proposals!</p>

    <p style="margin-top: 24px;">
      Warm Regards,<br>
      <strong>Organising Committee &mdash; QYRON'27</strong><br>
      Department of Mathematics<br>
      Patrician College of Arts and Science<br>
      Canal Bank Road, Gandhi Nagar, Adyar, Chennai &ndash; 600 020
    </p>
    <p class="tagline"><em>Quantum Coherence. Mathematical Precision.</em></p>
  </div>
  <div class="footer">
    <p><strong>QYRON'27</strong> &mdash; Department of Mathematics, Patrician College of Arts and Science</p>
    <p>This confirmation was dispatched to {username}. Please keep your credentials secure.</p>
  </div>
</div>
</body>
</html>"""


def _build_pending_html(
    leader_name: str,
    team_code: str,
    team_name: str,
    track: str,
    utr_number: str,
    college_name: str = ""
) -> str:
    """Builds HTML acknowledging registration and stating payment is under verification."""
    return _build_registration_confirmed_html(
        leader_name=leader_name,
        team_code=team_code,
        team_name=team_name,
        track=track,
        utr_number=utr_number,
        username=leader_name,
        password="(Available on confirmation screen & in portal)",
        portal_url=DEFAULT_PORTAL_URL,
        college_name=college_name
    )


def send_registration_pending_email(
    to_email: str,
    team_code: str,
    team_name: str,
    track: str,
    utr_number: str = "Submitted via UPI",
    leader_name: str = "Participant",
    college_name: str = ""
) -> bool:
    """
    Sends Email 1: Acknowledges squad registration & logs payment UTR under pending verification.
    """
    cfg = settings()
    if not cfg.has_smtp:
        logger.warning("SMTP not configured — skipping pending registration email for %s", team_code)
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"QYRON'27 — Registration Received & Payment Under Verification | {team_code}"
        from_name = cfg.smtp_from_name or "QYRON'27 Organizers"
        msg["From"] = formataddr((from_name, cfg.smtp_email))
        msg["To"] = to_email

        plain_text = f"""Dear {leader_name},

Greetings from the Department of Mathematics, Patrician College of Arts and Science!

Thank you for registering your team for QYRON'27 — 24-Hour National Quantum Computing & Mathematical Innovation Hackathon.

REGISTRATION APPLICATION DETAILS:
- Event: QYRON'27 Hackathon
- Registration ID: {team_code}
- Team Name: {team_name}
- Track: {track}
- Entry Fee: Rs. 150 per Squad
- Submitted UPI UTR / Ref: {utr_number}
- Status: Pending Committee Verification

Your payment reference ({utr_number}) is currently being verified against our official college bank records.
Once verified by our organizing committee, you will receive an official Payment Verified email containing your Portal Login Credentials (Username & Password) to submit your Proposal Presentation (.pptx/.pdf).

Key Dates:
- Proposal Submission Deadline: 25 January 2027
- Shortlist Announcement: 28 January 2027
- On-Campus Finale: 12-13 February 2027

Best Regards,
Department of Mathematics, Patrician College of Arts and Science
"""
        html_text = _build_pending_html(leader_name, team_code, team_name, track, utr_number, college_name)

        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_text, "html", "utf-8"))

        password_clean = cfg.smtp_app_password.replace(" ", "")
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=15) as server:
            server.ehlo()
            if cfg.smtp_use_tls or cfg.smtp_port == 587:
                server.starttls()
                server.ehlo()
            server.login(cfg.smtp_email, password_clean)
            server.sendmail(cfg.smtp_email, to_email, msg.as_string())

        logger.info("Registration pending verification email sent to %s for squad %s", to_email, team_code)
        return True

    except Exception as e:
        logger.error("Failed to send pending verification email to %s: %s", to_email, e)
        return False


def send_registration_confirmation(
    to_email: str,
    team_code: str,
    team_name: str,
    track: str,
    utr_number: str = "Submitted via UPI",
    leader_name: str = "Participant",
    username: str = "",
    password: str = "",
    portal_url: str = "",
    college_name: str = ""
) -> bool:
    """
    Sends Email 1: Dispatched immediately upon registration.
    Delivers team registration confirmation, UTR receipt acknowledgement, and active portal login credentials.
    """
    cfg = settings()
    if not cfg.has_smtp:
        logger.warning("SMTP not configured — skipping registration confirmation email for %s", team_code)
        return False

    login_user = username or to_email
    target_portal_url = portal_url or cfg.supabase_email_redirect_url or DEFAULT_PORTAL_URL
    if "/login" not in target_portal_url and not target_portal_url.endswith(".html"):
        target_portal_url = target_portal_url.rstrip("/") + "/login"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"QYRON'27 — Registration Confirmed & Portal Credentials | {team_code}"
        from_name = cfg.smtp_from_name or "QYRON'27 Organizers"
        msg["From"] = formataddr((from_name, cfg.smtp_email))
        msg["To"] = to_email

        plain_text = f"""Dear {leader_name},

Greetings from the Department of Mathematics, Patrician College of Arts and Science!

Thank you for registering your team for QYRON'27 — 24-Hour National Quantum Computing & Mathematical Innovation Hackathon.

REGISTRATION APPLICATION DETAILS:
- Event: QYRON'27 Hackathon
- Registration ID: {team_code}
- Team Name: {team_name}
- Track: {track}
- Initial Entry Fee: Rs. 150 per Squad
- Submitted UPI UTR / Ref: {utr_number}
- Registration Status: Registered & Credentials Dispatched

YOUR PARTICIPANT PORTAL CREDENTIALS:
- Portal Login URL: {target_portal_url}
- Username: {login_user}
- Password: {password}

NEXT STEPS:
1. Log in to {target_portal_url}
2. Enter your Idea Title, Abstract, and Technical Architecture.
3. Upload your official Presentation Slide Deck (.pptx, .ppt, or .pdf).
4. Proposal Submission Deadline: 25 January 2027 (11:59 PM IST).

Note on Payment: Your submitted 12-digit UPI reference ({utr_number}) is currently being cross-verified against official college bank accounts. You do NOT need to wait for payment verification to submit your proposal — you may log in and begin right away! Once verified, an official Payment Verified email will be dispatched.

Best Regards,
Organising Committee — QYRON'27
Department of Mathematics, Patrician College of Arts and Science
"""
        html_text = _build_registration_confirmed_html(
            leader_name, team_code, team_name, track, utr_number, login_user, password, target_portal_url, college_name
        )

        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_text, "html", "utf-8"))

        password_clean = cfg.smtp_app_password.replace(" ", "")
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=15) as server:
            server.ehlo()
            if cfg.smtp_use_tls or cfg.smtp_port == 587:
                server.starttls()
                server.ehlo()
            server.login(cfg.smtp_email, password_clean)
            server.sendmail(cfg.smtp_email, to_email, msg.as_string())

        logger.info("Registration confirmation & credentials email sent to %s for squad %s", to_email, team_code)
        return True

    except Exception as e:
        logger.error("Failed to send registration confirmation email to %s: %s", to_email, e)
        return False


def send_payment_verified_email(
    to_email: str,
    team_code: str,
    team_name: str,
    track: str,
    utr_number: str = "Verified",
    leader_name: str = "Participant",
    username: str = "",
    password: str = "",
    portal_url: str = "",
    college_name: str = ""
) -> bool:
    """
    Sends Email 2: Triggered by organizer in Admin Panel when payment is confirmed against bank statements.
    Confirms payment verification and reminds squad of the proposal deadline.
    """
    cfg = settings()
    if not cfg.has_smtp:
        logger.warning("SMTP not configured — skipping payment verified email for %s", team_code)
        return False

    login_user = username or to_email
    target_portal_url = portal_url or cfg.supabase_email_redirect_url or DEFAULT_PORTAL_URL
    if "/login" not in target_portal_url and not target_portal_url.endswith(".html"):
        target_portal_url = target_portal_url.rstrip("/") + "/login"

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Payment Verified & Registration Approved — QYRON'27 | {team_code}"
        from_name = cfg.smtp_from_name or "QYRON'27 Organizers"
        msg["From"] = formataddr((from_name, cfg.smtp_email))
        msg["To"] = to_email

        plain_text = f"""Dear {leader_name},

Greetings from the Department of Mathematics, Patrician College of Arts and Science!

We are pleased to inform you that your registration payment of Rs. 150 (UTR: {utr_number}) for Team {team_name} has been VERIFIED & APPROVED by the organizing committee!

YOUR VERIFIED REGISTRATION DETAILS:
- Event: QYRON'27 Hackathon
- Registration ID: {team_code}
- Team Name: {team_name}
- Track: {track}
- Payment Status: Verified & Approved (Rs. 150 Paid)

YOUR PARTICIPANT PORTAL ACCESS:
- Portal Login URL: {target_portal_url}
- Username: {login_user}

Please ensure your Idea Title, Abstract, and Presentation Slide Deck (.pptx / .pdf) are submitted in the portal before 25 January 2027 (11:59 PM IST).

Best Regards,
Organising Committee — QYRON'27
Department of Mathematics, Patrician College of Arts and Science
"""
        html_text = _build_verified_html(
            leader_name, team_code, team_name, track, utr_number, login_user, password, target_portal_url, college_name
        )

        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_text, "html", "utf-8"))

        password_clean = cfg.smtp_app_password.replace(" ", "")
        with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=15) as server:
            server.ehlo()
            if cfg.smtp_use_tls or cfg.smtp_port == 587:
                server.starttls()
                server.ehlo()
            server.login(cfg.smtp_email, password_clean)
            server.sendmail(cfg.smtp_email, to_email, msg.as_string())

        logger.info("Payment verified email sent to %s for squad %s", to_email, team_code)
        return True

    except Exception as e:
        logger.error("Failed to send payment verified email to %s: %s", to_email, e)
        return False


def extract_action_link(response: Any) -> str | None:
    """Extract action_link from Supabase Admin generate_link response across SDK versions."""
    if hasattr(response, "properties"):
        props = response.properties
        if hasattr(props, "action_link"):
            return getattr(props, "action_link")
        if isinstance(props, dict) and "action_link" in props:
            return props["action_link"]

    if hasattr(response, "action_link"):
        return getattr(response, "action_link")

    if isinstance(response, dict):
        if "action_link" in response:
            return response["action_link"]
        if "properties" in response and isinstance(response["properties"], dict):
            return response["properties"].get("action_link")

    return None


def render_verification_email(action_link: str, to_email: str) -> tuple[str, str]:
    """Compatibility helper for verification email."""
    text_body = f"Verify your QYRON'27 account by opening: {action_link}"
    html_body = f"<p>Verify your QYRON'27 account: <a href='{action_link}'>{action_link}</a></p>"
    return html_body, text_body


def send_verification_email(to_email: str, action_link: str) -> None:
    """Send verification email for Supabase Auth."""
    cfg = settings()
    if not cfg.has_smtp:
        return
    html, text = render_verification_email(action_link, to_email)
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Verify your account for QYRON'27"
    msg["From"] = formataddr((cfg.smtp_from_name or "QYRON'27 Organizers", cfg.smtp_email))
    msg["To"] = to_email
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    password_clean = cfg.smtp_app_password.replace(" ", "")
    with smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=15) as server:
        server.ehlo()
        if cfg.smtp_use_tls or cfg.smtp_port == 587:
            server.starttls()
            server.ehlo()
        server.login(cfg.smtp_email, password_clean)
        server.sendmail(cfg.smtp_email, to_email, msg.as_string())
