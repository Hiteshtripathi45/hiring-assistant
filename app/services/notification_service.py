import os
import smtplib
import uuid
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

from ics import Calendar, Event

from app.core.config import settings

INVITES_DIR = "generated_invites"
os.makedirs(INVITES_DIR, exist_ok=True)


def generate_interview_invite(
    candidate_name: str,
    job_title: str,
    start_time: datetime | None = None,
    duration_minutes: int = 45,
) -> str:
    """Generate a real .ics calendar invite file for an interview slot.
    Returns the filesystem path to the generated file."""
    start_time = start_time or (datetime.utcnow() + timedelta(days=2))

    cal = Calendar()
    event = Event()
    event.name = f"Interview: {candidate_name} — {job_title}"
    event.begin = start_time
    event.duration = timedelta(minutes=duration_minutes)
    event.description = (
        f"Automatically scheduled interview for {candidate_name} "
        f"for the {job_title} role, based on AI Hiring Assistant ranking + QA review."
    )
    cal.events.add(event)

    filename = f"{INVITES_DIR}/{candidate_name.replace(' ', '_')}_{uuid.uuid4().hex[:6]}.ics"
    with open(filename, "w") as f:
        f.writelines(cal.serialize_iter())

    return filename


def send_interview_email(
    to_email: str | None,
    candidate_name: str,
    job_title: str,
    ics_path: str,
) -> dict:
    """Send (or dry-run) the interview invitation email with the .ics attached.

    Returns a dict describing what happened, so the API can report it
    honestly rather than silently pretending an email went out.
    """
    subject = f"Interview invitation — {job_title}"
    body = (
        f"Hi {candidate_name},\n\n"
        f"You've been shortlisted for the {job_title} role. "
        f"Please find a proposed interview slot attached as a calendar invite.\n\n"
        f"Best,\nHiring Team"
    )

    smtp_host = settings.SMTP_HOST
    smtp_user = settings.SMTP_USER
    smtp_password = settings.SMTP_PASSWORD

    if not to_email or not smtp_host or not smtp_user or not smtp_password:

        return {
            "status": "dry_run",
            "to": to_email or "(no email on file)",
            "subject": subject,
            "ics_file": ics_path,
            "note": "SMTP not configured or candidate has no email — logged instead of sent.",
        }

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with open(ics_path, "rb") as f:
        part = MIMEBase("text", "calendar", method="REQUEST")
        part.set_payload(f.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(ics_path)}")
        msg.attach(part)

    try:
        with smtplib.SMTP(smtp_host, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_email, msg.as_string())
        return {"status": "sent", "to": to_email, "subject": subject, "ics_file": ics_path}
    except Exception as e:
        return {"status": "failed", "to": to_email, "error": str(e), "ics_file": ics_path}
