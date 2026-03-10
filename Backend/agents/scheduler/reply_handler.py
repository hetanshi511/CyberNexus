import logging
import re
from datetime import datetime, timedelta
from utils.calendar_service import get_calendar_service, get_busy_slots, create_calendar_event
from utils.scheduler_email_service import send_interview_email
from utils.slot_generator import find_available_slot, SLOT_DURATION_MINUTES

# ---------------------------------------------------------------------------
# Reply Handler
# Executes actions (Confirm/Reschedule/Cancel) on Google Calendar events.
# ---------------------------------------------------------------------------

logger = logging.getLogger("scheduler_agent")

def handle_reply(recruiter_email: str, invite_id: str, intent: str, preferred_time: str, candidate_email: str):
    logger.info(f"[ReplyHandler] Action: {intent} on {invite_id}")
    
    try:
        service = get_calendar_service()
        
        # Search the recruiter's calendar for the invite ID
        now = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId=recruiter_email, 
            timeMin=now,
            q=invite_id,
            singleEvents=True
        ).execute()
        
        events = events_result.get('items', [])
        if not events:
            logger.warning(f"[ReplyHandler] Cannot find future calendar event for {invite_id}.")
            return
            
        event = events[0]
        event_id = event['id']
        
        if intent == "confirm":
            desc = event.get('description', '')
            if "Status: Confirmed by candidate" not in desc:
                event['description'] = desc + "\n\nStatus: Confirmed by candidate"
                service.events().update(calendarId=recruiter_email, eventId=event_id, body=event).execute()
                logger.info(f"[ReplyHandler] Confirmed event {event_id}")
                
        elif intent == "reject":
            service.events().delete(calendarId=recruiter_email, eventId=event_id).execute()
            logger.info(f"[ReplyHandler] Canceled event {event_id}")
            
        elif intent == "reschedule":
            # Cancel the old event
            service.events().delete(calendarId=recruiter_email, eventId=event_id).execute()
            
            # Reconstruct details
            summary = event.get('summary', '') 
            role = "Candidate"
            candidate_name = "Candidate"
            
            # Pattern: Interview – Backend Engineer (John Doe) [INV-12345]
            if " – " in summary:
                parts = summary.split(" – ")
                if len(parts) > 1:
                    role_part = parts[1]
                    if " (" in role_part:
                        role = role_part.split(" (")[0]
                        candidate_name = role_part.split(" (")[1].split(")")[0]
                        
            # Clean candidate email
            clean_email = candidate_email
            email_match = re.search(r'<(.+?)>', candidate_email)
            if email_match:
                clean_email = email_match.group(1)
            
            # Find new slot (next 30 days)
            from utils.slot_generator import IST
            today = datetime.now(IST).replace(tzinfo=None)
            
            all_busy = []
            check_date = today
            for _ in range(30):
                try:
                    day_busy = get_busy_slots(service, recruiter_email, check_date)
                    all_busy.extend(day_busy)
                except Exception:
                    pass
                check_date += timedelta(days=1)
                
            slot = find_available_slot(today, all_busy)
            if not slot:
                logger.warning(f"[ReplyHandler] Could not find any auto-reschedule slot for {invite_id}.")
                return
                
            start_dt = slot
            end_dt = start_dt + timedelta(minutes=SLOT_DURATION_MINUTES)
            
            # Recover or generate meeting link
            meeting_link = ""
            conf_data = event.get("conferenceData", {})
            for ep in conf_data.get("entryPoints", []):
                if ep.get("entryPointType") == "video":
                    meeting_link = ep.get("uri", "")
                    break
                    
            if not meeting_link:
                match = re.search(r'https://meet\.jit\.si/\S+', event.get('description', ''))
                if match:
                    meeting_link = match.group(0)
            
            new_desc = (
                f"Candidate : {candidate_name}\n"
                f"Email     : {clean_email}\n"
                f"Role      : {role}\n"
                f"Meeting   : {meeting_link}\n\n"
                f"Rescheduled automatically based on candidate reply. ID: {invite_id}"
            )
            
            new_ev = create_calendar_event(
                service=service,
                calendar_id=recruiter_email,
                summary=f"Interview – {role} ({candidate_name}) [{invite_id}]",
                description=new_desc,
                start_dt=start_dt,
                end_dt=end_dt,
                meeting_link=meeting_link
            )
            
            send_interview_email(
                candidate_name=candidate_name,
                candidate_email=clean_email,
                job_role=role,
                interview_datetime=start_dt,
                meeting_link=new_ev.get('meet_link', meeting_link),
                recruiter_name=recruiter_email,
                invite_id=invite_id
            )
            logger.info(f"[ReplyHandler] Rescheduled event {invite_id} for {start_dt}")
            
    except Exception as e:
        logger.error(f"[ReplyHandler] Failed handling reply for {invite_id}: {e}", exc_info=True)
