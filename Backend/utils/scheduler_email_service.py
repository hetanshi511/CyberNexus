"""
Scheduler Email Service
Sends interview-confirmation emails to candidates via SMTP.
"""

import os
import smtplib
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("scheduler_agent")


def send_interview_email(
    candidate_name: str,
    candidate_email: str,
    job_role: str,
    interview_datetime: datetime,
    meeting_link: str,
    recruiter_name: str,
    invite_id: str = None
) -> bool:
    """
    Send an interview-confirmation email to the candidate.

    Returns ``True`` on success, ``False`` otherwise.
    Uses the same SMTP env-vars as the rest of the platform
    (``SMTP_SERVER``, ``SMTP_PORT``, ``SMTP_USERNAME``, ``SMTP_PASSWORD``).
    """
    smtp_server = os.environ.get("SMTP_SERVER")
    smtp_port   = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user   = os.environ.get("SMTP_USERNAME")
    smtp_pass   = os.environ.get("SMTP_PASSWORD")

    if not smtp_server:
        logger.warning("SMTP not configured — skipping interview email.")
        return False

    if invite_id:
        subject = f"Interview Scheduled – {job_role} [{invite_id}]"
    else:
        subject = f"Interview Scheduled – {job_role}"

    formatted_date = interview_datetime.strftime("%A, %B %d, %Y")
    formatted_time = interview_datetime.strftime("%I:%M %p")

    body = (
        f"Dear {candidate_name},\n\n"
        f"We are pleased to inform you that your interview for the position of "
        f"**{job_role}** has been scheduled.\n\n"
        f"📅  Date : {formatted_date}\n"
        f"🕐  Time : {formatted_time}\n"
        f"🔗  Meeting Link : {meeting_link}\n\n"
        f"Recruiter: {recruiter_name}\n\n"
        f"Please join the meeting link at the scheduled time. If you have any "
        f"questions, feel free to reach out.\n\n"
        f"Best regards,\n"
        f"{recruiter_name}\n"
        f"Invinsense AI Marketplace"
    )

    try:
        msg = MIMEMultipart()
        msg["From"]    = smtp_user or "noreply@invinsense.local"
        msg["To"]      = candidate_email
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
        server.starttls()
        if smtp_user and smtp_pass:
            server.login(smtp_user, smtp_pass)

        server.send_message(msg)
        server.quit()

        logger.info(f"Interview email sent to {candidate_email}.")
        return True

    except OSError as e:
        logger.error(f"[SchedulerEmail] Network error (Errno 101 / Timeout) when connecting to {smtp_server}:{smtp_port}")
        logger.error(f"NOTE: Your deployment environment (e.g. Railway or local Docker) may be blocking outbound SMTP connections on port {smtp_port}. Please check platform firewall rules.")
        return False
    except Exception as e:
        logger.error(f"Failed to send interview email to {candidate_email}: {e}")
        return False
