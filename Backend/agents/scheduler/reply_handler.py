import logging
import re
from datetime import datetime, timedelta

from utils.calendar_service import get_calendar_service, create_calendar_event
from utils.scheduler_email_service import send_interview_email
from utils.slot_generator import find_available_slot, SLOT_DURATION_MINUTES

logger = logging.getLogger("scheduler_agent")


def handle_reply(recruiter_email, invite_id, intent, preferred_time, candidate_email):

    logger.info(f"[ReplyHandler] Action: {intent} on {invite_id}")

    try:
        service = get_calendar_service(recruiter_email)

        # ── Locate event by invite ID ──────────────────────────────
        now = (datetime.utcnow() - timedelta(hours=6)).isoformat() + "Z"

        events = (
            service.events()
            .list(
                calendarId=recruiter_email,
                timeMin=now,
                singleEvents=True,
                q=invite_id,
            )
            .execute()
            .get("items", [])
        )

        event = None
        for ev in events:
            if invite_id in ev.get("summary", ""):
                event = ev
                break

        if not event:
            logger.warning(f"[ReplyHandler] Event not found for {invite_id}")
            return

        event_id = event["id"]

        # ── Confirm interview ─────────────────────────────────────
        if intent == "confirm":

            desc = event.get("description", "")
            if "Status: Confirmed by candidate" not in desc:
                event["description"] = desc + "\n\nStatus: Confirmed by candidate"

                service.events().update(
                    calendarId=recruiter_email,
                    eventId=event_id,
                    body=event,
                ).execute()

                logger.info(f"[ReplyHandler] Interview confirmed: {invite_id}")

            return

        # ── Reject interview ──────────────────────────────────────
        if intent == "reject":

            service.events().delete(
                calendarId=recruiter_email,
                eventId=event_id
            ).execute()

            logger.info(f"[ReplyHandler] Interview cancelled: {invite_id}")
            return

        # ── Reschedule interview ──────────────────────────────────
        if intent == "reschedule":

            logger.info(f"[ReplyHandler] Processing reschedule for {invite_id}")

            old_start = datetime.fromisoformat(
                event["start"]["dateTime"].replace("Z", "+00:00")
            ).replace(tzinfo=None)

            old_end = datetime.fromisoformat(
                event["end"]["dateTime"].replace("Z", "+00:00")
            ).replace(tzinfo=None)

            # Candidate name + role
            summary = event.get("summary", "")
            role = "Candidate"
            candidate_name = "Candidate"

            if " – " in summary:
                role = summary.split(" – ")[1].split(" (")[0]
                candidate_name = summary.split("(")[1].split(")")[0]

            # Clean email
            clean_email = candidate_email
            m = re.search(r"<(.+?)>", candidate_email)
            if m:
                clean_email = m.group(1)

            # ── Collect Recruiter Busy Slots (14 days) ───────────
            from utils.calendar_service import get_busy_slots
            from utils.slot_generator import IST

            busy_slots = []
            today = datetime.now(IST).replace(tzinfo=None)

            for i in range(14):
                date_to_check = today + timedelta(days=i)
                try:
                    busy_slots.extend(get_busy_slots(service, recruiter_email, date_to_check))
                except Exception:
                    pass

            # Block the previous event
            busy_slots.append((old_start, old_end))

            # ── Determine new slot ───────────────────────────────
            candidate_slot = None

            if preferred_time:
                try:
                    candidate_slot = datetime.fromisoformat(preferred_time)
                except Exception:
                    pass

            def is_slot_free(start, end, busy):
                for b_start, b_end in busy:
                    if start < b_end and end > b_start:
                        return False
                return True

            slot = None
            if candidate_slot:
                end_candidate = candidate_slot + timedelta(minutes=SLOT_DURATION_MINUTES)
                if is_slot_free(candidate_slot, end_candidate, busy_slots):
                    slot = candidate_slot
                    logger.info(f"[ReplyHandler] Candidate requested slot {slot} is free")
                else:
                    logger.info("[ReplyHandler] Candidate slot busy → searching next free")
            
            if not slot:
                search_start = candidate_slot if candidate_slot else today
                slot = find_available_slot(search_start, busy_slots)
                logger.info(f"[ReplyHandler] Auto slot selected {slot}")

            if not slot:
                logger.warning(f"[ReplyHandler] Could not find any auto-reschedule slot for {invite_id}")
                return

            start_dt = slot
            end_dt = start_dt + timedelta(minutes=SLOT_DURATION_MINUTES)

            # Recover meeting link
            meeting_link = ""
            conf = event.get("conferenceData", {})

            for ep in conf.get("entryPoints", []):
                if ep.get("entryPointType") == "video":
                    meeting_link = ep.get("uri", "")

            # ── Create new event first ───────────────────────────
            new_event = create_calendar_event(
                service=service,
                calendar_id=recruiter_email,
                summary=f"Interview – {role} ({candidate_name}) [{invite_id}]",
                description=f"Rescheduled interview for {candidate_name}",
                start_dt=start_dt,
                end_dt=end_dt,
                meeting_link=meeting_link,
            )

            logger.info(f"[ReplyHandler] New event created {new_event['event_id']}")

            # ── Delete old event ─────────────────────────────────
            service.events().delete(
                calendarId=recruiter_email,
                eventId=event_id
            ).execute()

            logger.info(f"[ReplyHandler] Old event removed")

            # ── Send updated email ───────────────────────────────
            send_interview_email(
                candidate_name=candidate_name,
                candidate_email=clean_email,
                job_role=role,
                interview_datetime=start_dt,
                meeting_link=new_event.get("meet_link", meeting_link),
                recruiter_name=recruiter_name,
                recruiter_email=recruiter_email,
                invite_id=invite_id,
            )

            logger.info(f"[ReplyHandler] Reschedule completed")

    except Exception as e:
        logger.error(
            f"[ReplyHandler] Failed handling {invite_id}: {e}",
            exc_info=True,
        )



# import logging
# import re
# from datetime import datetime, timedelta
# from utils.calendar_service import get_calendar_service, get_busy_slots, create_calendar_event
# from utils.scheduler_email_service import send_interview_email
# from utils.slot_generator import find_available_slot, SLOT_DURATION_MINUTES

# # ---------------------------------------------------------------------------
# # Reply Handler
# # Executes actions (Confirm/Reschedule/Cancel) on Google Calendar events.
# # ---------------------------------------------------------------------------

# logger = logging.getLogger("scheduler_agent")

# def handle_reply(recruiter_email: str, invite_id: str, intent: str, preferred_time: str, candidate_email: str):
#     logger.info(f"[ReplyHandler] Action: {intent} on {invite_id}")
    
#     try:
#         service = get_calendar_service(recruiter_email)
        
#         # Search the recruiter's calendar for the invite ID starting 6 hours ago
#         now = (datetime.utcnow() - timedelta(hours=6)).isoformat() + 'Z'
#         events_result = service.events().list(
#             calendarId=recruiter_email, 
#             timeMin=now,
#             q=invite_id,
#             singleEvents=True
#         ).execute()
        
#         events = events_result.get('items', [])
        
#         event = None
#         for ev in events:
#             if invite_id in ev.get("summary", ""):
#                 event = ev
#                 break
                
#         if not event:
#             logger.warning(f"[ReplyHandler] Cannot find calendar event for {invite_id}.")
#             return
            
#         event_id = event['id']
        
#         if intent == "confirm":
#             desc = event.get('description', '')
#             if "Status: Confirmed by candidate" not in desc:
#                 event['description'] = desc + "\n\nStatus: Confirmed by candidate"
#                 service.events().update(calendarId=recruiter_email, eventId=event_id, body=event).execute()
#                 logger.info(f"[ReplyHandler] Confirmed event {event_id}")
                
#         elif intent == "reject":
#             service.events().delete(calendarId=recruiter_email, eventId=event_id).execute()
#             logger.info(f"[ReplyHandler] Canceled event {event_id}")
            
#         elif intent == "reschedule":
#             logger.info(f"[ReplyHandler] Processing reschedule request for {invite_id}")
            
#             # Get old event timing
#             old_start = datetime.fromisoformat(event["start"]["dateTime"].replace("Z",""))
#             old_end = datetime.fromisoformat(event["end"]["dateTime"].replace("Z",""))
            
#             logger.info(f"[ReplyHandler] Old interview slot: {old_start} → {old_end}")
            
#             # Reconstruct details
#             summary = event.get('summary', '') 
#             role = "Candidate"
#             candidate_name = "Candidate"
            
#             # Pattern: Interview – Backend Engineer (John Doe) [INV-12345]
#             if " – " in summary:
#                 parts = summary.split(" – ")
#                 if len(parts) > 1:
#                     role_part = parts[1]
#                     if " (" in role_part:
#                         role = role_part.split(" (")[0]
#                         candidate_name = role_part.split(" (")[1].split(")")[0]
                        
#             # Clean candidate email
#             clean_email = candidate_email
#             email_match = re.search(r'<(.+?)>', candidate_email)
#             if email_match:
#                 clean_email = email_match.group(1)
            
#             # Collect busy slots for next 30 days
#             from utils.slot_generator import IST
#             today = datetime.now(IST).replace(tzinfo=None)
            
#             all_busy = []
#             check_date = today
            
#             for _ in range(30):
#                 try:
#                     day_busy = get_busy_slots(service, recruiter_email, check_date)
#                     all_busy.extend(day_busy)
#                 except Exception:
#                     pass
#                 check_date += timedelta(days=1)
                
#             # Add old slot to busy list so it won't be selected again
#             all_busy.append((old_start, old_end))
            
#             # If candidate suggested time
#             slot = None
#             if preferred_time:
#                 try:
#                     pref_dt = datetime.fromisoformat(preferred_time)
#                     logger.info(f"[ReplyHandler] Candidate preferred time: {pref_dt}")
                    
#                     # Check if preferred slot conflicts
#                     conflict = False
#                     for busy_start, busy_end in all_busy:
#                         if busy_start <= pref_dt < busy_end:
#                             conflict = True
#                             break
                            
#                     if not conflict:
#                         slot = pref_dt
#                         logger.info(f"[ReplyHandler] Using candidate preferred slot: {slot}")
                        
#                 except Exception:
#                     logger.warning(f"[ReplyHandler] Could not parse preferred_time: {preferred_time}")
                    
#             # If preferred time not usable, auto-find slot
#             if not slot:
#                 slot = find_available_slot(today, all_busy)
#                 logger.info(f"[ReplyHandler] Auto-selected new slot: {slot}")
                
#             if not slot:
#                 logger.warning(f"[ReplyHandler] Could not find any auto-reschedule slot for {invite_id}.")
#                 return
                
#             start_dt = slot
#             end_dt = start_dt + timedelta(minutes=SLOT_DURATION_MINUTES)
            
#             logger.info(f"[ReplyHandler] Creating rescheduled event at {start_dt}")
            
#             # Recover or generate meeting link
#             meeting_link = ""
#             conf_data = event.get("conferenceData", {})
#             for ep in conf_data.get("entryPoints", []):
#                 if ep.get("entryPointType") == "video":
#                     meeting_link = ep.get("uri", "")
#                     break
                    
#             if not meeting_link:
#                 match = re.search(r'https://meet\.jit\.si/\S+', event.get('description', ''))
#                 if match:
#                     meeting_link = match.group(0)
            
#             new_desc = (
#                 f"Candidate : {candidate_name}\n"
#                 f"Email     : {clean_email}\n"
#                 f"Role      : {role}\n"
#                 f"Meeting   : {meeting_link}\n\n"
#                 f"Rescheduled automatically based on candidate reply. ID: {invite_id}"
#             )
            
#             # Create new event FIRST
#             new_ev = create_calendar_event(
#                 service=service,
#                 calendar_id=recruiter_email,
#                 summary=f"Interview – {role} ({candidate_name}) [{invite_id}]",
#                 description=new_desc,
#                 start_dt=start_dt,
#                 end_dt=end_dt,
#                 meeting_link=meeting_link
#             )
            
#             logger.info(f"[ReplyHandler] New calendar event created for {invite_id}")
            
#             # Delete old event AFTER new one created
#             service.events().delete(
#                 calendarId=recruiter_email,
#                 eventId=event_id
#             ).execute()
            
#             logger.info(f"[ReplyHandler] Old calendar event deleted for {invite_id}")
            
#             # Send updated interview email
#             send_interview_email(
#                 candidate_name=candidate_name,
#                 candidate_email=clean_email,
#                 job_role=role,
#                 interview_datetime=start_dt,
#                 meeting_link=new_ev.get('meet_link', meeting_link),
#                 recruiter_name=recruiter_email,
#                 invite_id=invite_id
#             )
#             logger.info(f"[ReplyHandler] Reschedule email sent for {invite_id}")
            
#     except Exception as e:
#         logger.error(f"[ReplyHandler] Failed handling reply for {invite_id}: {e}", exc_info=True)
