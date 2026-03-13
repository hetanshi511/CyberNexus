"""
Google Calendar Service
Supports two authentication modes:
  1. OAuth 2.0 user token  — recruiter authenticates via Firebase popup (preferred)
  2. Service-account JSON  — legacy fallback
"""

import os
import json
import base64
import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials as GoogleCredentials
from googleapiclient.discovery import build

from utils.db import get_oauth_credentials

logger = logging.getLogger("scheduler_agent")

# Path to the existing service-account key shipped with the project
SERVICE_ACCOUNT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),  # Backend/
    "service_account.json",
)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

SLOT_DURATION_MINUTES = 30


# ── Authentication ─────────────────────────────────────────────────────

def get_calendar_service_from_token(access_token: str):
    """
    Build a Calendar API service using the recruiter's OAuth access token
    obtained from Firebase ``signInWithPopup``.
    """
    credentials = GoogleCredentials(token=access_token)
    service = build("calendar", "v3", credentials=credentials)
    logger.info("Google Calendar service initialised (OAuth user token).")
    return service


def get_calendar_service(email_address: str = None):
    """
    Build a Calendar API service using the Offline OAuth key (if available)
    or fallback to the service-account key.
    """
    if email_address:
        db_creds = get_oauth_credentials(email_address)
        if db_creds and db_creds.get("refresh_token"):
            client_config = _get_client_config()
            creds = GoogleCredentials(
                token=db_creds["access_token"],
                refresh_token=db_creds["refresh_token"],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_config.get("client_id"),
                client_secret=client_config.get("client_secret"),
                scopes=SCOPES
            )
            logger.info(f"Google Calendar service initialised via DB refresh token for {email_address}.")
            return build("calendar", "v3", credentials=creds)

    if os.path.exists(SERVICE_ACCOUNT_FILE):
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
    else:
        sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
        if not sa_json:
            raise FileNotFoundError(
                "Service-account key not found. Set GOOGLE_SERVICE_ACCOUNT_JSON env var "
                "or place service_account.json in the Backend root."
            )
        # Try raw JSON first (if it starts with '{')
        if sa_json.startswith("{"):
            info = json.loads(sa_json)
        else:
            # Try base64-encoded
            decoded = base64.b64decode(sa_json).decode("utf-8").strip()
            info = json.loads(decoded)
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)

    service = build("calendar", "v3", credentials=creds)
    logger.info("Google Calendar service initialised (service account).")
    return service

def _get_client_config():
    """Reads the local client_secret.json needed to refresh tokens"""
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "client_secret.json")
    if not os.path.exists(path):
        return {}
    with open(path, "r") as f:
        data = json.load(f)
        web = data.get("web") or data.get("installed", {})
        return {
            "client_id": web.get("client_id"),
            "client_secret": web.get("client_secret")
        }


# ── Query busy slots ───────────────────────────────────────────────────

def get_busy_slots(
    service,
    calendar_id: str,
    date: datetime,
) -> List[datetime]:
    """
    Return start-times of every event on *date* in the given calendar.
    """
    day_start = datetime.combine(
        date.date() if isinstance(date, datetime) else date,
        datetime.min.time(),
    ).astimezone(timezone.utc).isoformat()

    day_end = datetime.combine(
        date.date() if isinstance(date, datetime) else date,
        datetime.max.time(),
    ).astimezone(timezone.utc).isoformat()

    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=day_start,
            timeMax=day_end,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = events_result.get("items", [])
    busy = []

    for event in events:
        start_str = event["start"].get("dateTime", event["start"].get("date"))
        end_str = event["end"].get("dateTime", event["end"].get("date"))
        try:
            start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00")).replace(tzinfo=None)
            end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00")).replace(tzinfo=None)
            busy.append((start_dt, end_dt))
        except (ValueError, TypeError):
            continue

    logger.info(f"Found {len(busy)} busy slot(s) on {date.date() if isinstance(date, datetime) else date}.")
    return busy


# ── Create calendar event ──────────────────────────────────────────────

def create_calendar_event(
    service,
    calendar_id: str,
    summary: str,
    description: str,
    start_dt: datetime,
    end_dt: datetime,
    meeting_link: str,
    attendees: List[dict] = None,
) -> dict:
    """
    Insert a new event into the recruiter's calendar.
    Returns a dict with ``event_id`` and ``meet_link``.

    Tries to create a real Google Meet link via conferenceData. If it
    fails (e.g. unsupported account type), falls back to a plain event.
    """
    base_event = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": "Asia/Kolkata",
        },
        "reminders": {
            "useDefault": True,
        },
    }
    
    if attendees:
        base_event["attendees"] = attendees

    # ── Attempt 1: with real Google Meet link ──────────────────────────
    try:
        event_with_meet = {
            **base_event,
            "conferenceData": {
                "createRequest": {
                    "requestId": str(uuid.uuid4()),
                    "conferenceSolutionKey": {
                        "type": "hangoutsMeet",
                    },
                },
            },
        }

        created_event = (
            service.events()
            .insert(
                calendarId=calendar_id,
                body=event_with_meet,
                conferenceDataVersion=1,
                sendUpdates="all",
            )
            .execute()
        )
        logger.info("Calendar event created WITH Google Meet link.")

    except Exception as meet_err:
        logger.warning(
            f"Could not create event with Meet link ({meet_err}). "
            f"Retrying without conferenceData..."
        )

        # ── Attempt 2: plain event without conferenceData ─────────────
        created_event = (
            service.events()
            .insert(
                calendarId=calendar_id,
                body=base_event,
                sendUpdates="all"
            )
            .execute()
        )
        logger.info("Calendar event created WITHOUT Google Meet (plain event).")

    event_id = created_event.get("id", "")

    # Extract real Meet link if it was generated
    meet_link = ""
    conference_data = created_event.get("conferenceData", {})
    entry_points = conference_data.get("entryPoints", [])
    for ep in entry_points:
        if ep.get("entryPointType") == "video":
            meet_link = ep.get("uri", "")
            break

    logger.info(f"Calendar event created: {event_id}, Meet link: {meet_link or '(fallback link used)'}")
    return {"event_id": event_id, "meet_link": meet_link}
