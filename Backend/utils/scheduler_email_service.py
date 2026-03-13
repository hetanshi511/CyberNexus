"""
Scheduler Email Service
Sends interview-confirmation emails to candidates via SMTP.
"""

import os
import json
import base64
import uuid
import logging
from datetime import datetime, timedelta
from email.message import EmailMessage

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from utils.db import get_oauth_credentials

logger = logging.getLogger("scheduler_agent")


def send_interview_email(
    candidate_name: str,
    candidate_email: str,
    job_role: str,
    interview_datetime: datetime,
    meeting_link: str,
    recruiter_name: str,
    recruiter_email: str,
    invite_id: str = None
) -> bool:
    """
    Send an interview-confirmation email to the candidate via Gmail API.
    Returns ``True`` on success, ``False`` otherwise.
    """
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
        msg = EmailMessage()
        msg.set_content(body)
        msg["To"] = candidate_email
        msg["From"] = f"{recruiter_name} <{recruiter_email}>"
        msg["Subject"] = subject
        
        db_creds = get_oauth_credentials(recruiter_email)
        if not db_creds or not db_creds.get("refresh_token"):
            logger.error(f"No OAuth tokens found for {recruiter_email} to send email.")
            return False
            
        # Get client_secret.json config
        client_id = client_secret = None
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "client_secret.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
                web = data.get("web") or data.get("installed", {})
                client_id = web.get("client_id")
                client_secret = web.get("client_secret")

        creds = Credentials(
            token=db_creds["access_token"],
            refresh_token=db_creds["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/gmail.modify"]
        )
        
        # Build ICS content
        dt_start = interview_datetime.strftime("%Y%m%dT%H%M%S")
        end_time = interview_datetime + timedelta(minutes=30)
        dt_end = end_time.strftime("%Y%m%dT%H%M%S")
        dt_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        uid = f"{uuid.uuid4().hex}@invinsense.marketplace"

        ics_content = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "PRODID:-//Invinsense AI Marketplace//Scheduler Agent//EN\r\n"
            "METHOD:REQUEST\r\n"
            "BEGIN:VEVENT\r\n"
            f"UID:{uid}\r\n"
            f"DTSTAMP:{dt_stamp}\r\n"
            f"DTSTART;TZID=Asia/Kolkata:{dt_start}\r\n"
            f"DTEND;TZID=Asia/Kolkata:{dt_end}\r\n"
            f"SUMMARY:{subject}\r\n"
            f"DESCRIPTION:Meeting Link: {meeting_link}\\n{body.replace(chr(10), '\\n')}\r\n"
            f"ORGANIZER;CN=\"{recruiter_name}\":mailto:{recruiter_email}\r\n"
            f"ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:{candidate_email}\r\n"
            "STATUS:CONFIRMED\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR"
        )
        msg.add_attachment(ics_content.encode("utf-8"), maintype="text", subtype="calendar", filename="invite.ics", params={"method": "REQUEST"})

        service = build('gmail', 'v1', credentials=creds)
        encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        
        service.users().messages().send(
            userId="me", 
            body={'raw': encoded_message}
        ).execute()

        logger.info(f"Interview email sent to {candidate_email} via Gmail API.")
        return True

    except Exception as e:
        logger.error(f"Failed to send interview email to {candidate_email}: {e}")
        return False

def send_reschedule_email(
    candidate_name: str,
    candidate_email: str,
    job_role: str,
    interview_datetime: datetime,
    meeting_link: str,
    recruiter_name: str,
    recruiter_email: str,
    invite_id: str = None
) -> bool:
    """
    Send an interview-reschedule reply email to the candidate via Gmail API.
    Returns ``True`` on success, ``False`` otherwise.
    """
    if invite_id:
        subject = f"Re: Interview Scheduled – {job_role} [{invite_id}]"
    else:
        subject = f"Re: Interview Scheduled – {job_role}"

    formatted_date = interview_datetime.strftime("%A, %B %d, %Y")
    formatted_time = interview_datetime.strftime("%I:%M %p")

    body = (
        f"Hi {candidate_name},\n\n"
        f"Thank you for reaching out. We have successfully rescheduled your interview for the position of "
        f"**{job_role}**.\n\n"
        f"Here are your new details:\n"
        f"📅  Date : {formatted_date}\n"
        f"🕐  Time : {formatted_time}\n"
        f"🔗  Meeting Link : {meeting_link}\n\n"
        f"Recruiter: {recruiter_name}\n\n"
        f"Please check your Google Calendar to see the updated event and accept the invitation. "
        f"Let me know if you have any questions.\n\n"
        f"Best regards,\n"
        f"{recruiter_name}\n"
        f"Invinsense AI Marketplace"
    )

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["To"] = candidate_email
        msg["From"] = f"{recruiter_name} <{recruiter_email}>"
        msg["Subject"] = subject
        
        db_creds = get_oauth_credentials(recruiter_email)
        if not db_creds or not db_creds.get("refresh_token"):
            logger.error(f"No OAuth tokens found for {recruiter_email} to send email.")
            return False
            
        client_id = client_secret = None
        path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "client_secret.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
                web = data.get("web") or data.get("installed", {})
                client_id = web.get("client_id")
                client_secret = web.get("client_secret")

        creds = Credentials(
            token=db_creds["access_token"],
            refresh_token=db_creds["refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/gmail.modify"]
        )
        
        # Build ICS content
        dt_start = interview_datetime.strftime("%Y%m%dT%H%M%S")
        end_time = interview_datetime + timedelta(minutes=30)
        dt_end = end_time.strftime("%Y%m%dT%H%M%S")
        dt_stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        uid = f"{uuid.uuid4().hex}@invinsense.marketplace"

        ics_content = (
            "BEGIN:VCALENDAR\r\n"
            "VERSION:2.0\r\n"
            "PRODID:-//Invinsense AI Marketplace//Scheduler Agent//EN\r\n"
            "METHOD:REQUEST\r\n"
            "BEGIN:VEVENT\r\n"
            f"UID:{uid}\r\n"
            f"DTSTAMP:{dt_stamp}\r\n"
            f"DTSTART;TZID=Asia/Kolkata:{dt_start}\r\n"
            f"DTEND;TZID=Asia/Kolkata:{dt_end}\r\n"
            f"SUMMARY:{subject}\r\n"
            f"DESCRIPTION:Meeting Link: {meeting_link}\\n{body.replace(chr(10), '\\n')}\r\n"
            f"ORGANIZER;CN=\"{recruiter_name}\":mailto:{recruiter_email}\r\n"
            f"ATTENDEE;ROLE=REQ-PARTICIPANT;PARTSTAT=NEEDS-ACTION;RSVP=TRUE:mailto:{candidate_email}\r\n"
            "STATUS:CONFIRMED\r\n"
            "END:VEVENT\r\n"
            "END:VCALENDAR"
        )
        msg.add_attachment(ics_content.encode("utf-8"), maintype="text", subtype="calendar", filename="invite.ics", params={"method": "REQUEST"})

        service = build('gmail', 'v1', credentials=creds)
        encoded_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        
        service.users().messages().send(
            userId="me", 
            body={'raw': encoded_message}
        ).execute()

        logger.info(f"Reschedule email sent to {candidate_email} via Gmail API.")
        return True

    except Exception as e:
        logger.error(f"Failed to send reschedule email to {candidate_email}: {e}")
        return False
