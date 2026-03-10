import logging
import re
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

from utils.email_parser import extract_email_body
from agents.scheduler.reply_analyzer import analyze_reply
from agents.scheduler.reply_handler import handle_reply

# ---------------------------------------------------------------------------
# Gmail Reader Service
# Fetches unread replies from Gmail and triggers analysis/handling.
# ---------------------------------------------------------------------------

logger = logging.getLogger("scheduler_agent")

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def get_gmail_service():
    """Build a Gmail API service using the service-account key."""
    sa_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "service_account.json")
    
    if os.path.exists(sa_path):
        creds = service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)
    else:
        # Fallback to env var (Railway deployment)
        sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
        if not sa_json:
            raise FileNotFoundError("Service-account key not found.")
        
        import json
        import base64
        if sa_json.startswith("{"):
            info = json.loads(sa_json)
        else:
            info = json.loads(base64.b64decode(sa_json).decode("utf-8").strip())
            
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        
    return build('gmail', 'v1', credentials=creds)

def process_new_emails(email_address: str, history_id: str):
    """
    Fetch unread emails with the Interview-Replies label and process them.
    Notice that we use 'me' as userId, relying on domain-wide delegation
    or direct service account inbox if using a centralized webhook.
    """
    try:
        service = get_gmail_service()
        
        # Searching unread replies
        logger.info(f"[GmailReader] Fetching unread Interview-Replies for {email_address}...")
        results = service.users().messages().list(userId='me', q='is:unread label:Interview-Replies').execute()
        messages = results.get('messages', [])
        
        if not messages:
            logger.info(f"[GmailReader] No new messages found for {email_address}.")
            return
            
        for msg in messages:
            msg_id = msg['id']
            message_data = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            
            headers = message_data.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), "")
            sender = next((h['value'] for h in headers if h['name'] == 'From'), "")
            
            body = extract_email_body(message_data)
            
            # Analyze reply intent using LLM
            analysis = analyze_reply(body)
            intent = analysis.get("intent")
            preferred_time = analysis.get("preferred_time")
            
            # Identify Interview ID
            match = re.search(r'INV-\d+', subject) or re.search(r'INV-\d+', body)
            invite_id = match.group(0) if match else None
            
            logger.info(f"[GmailReader] Reply from {sender}. Intent: {intent}, ID: {invite_id}")
            
            if invite_id and intent:
                handle_reply(email_address, invite_id, intent, preferred_time, sender)
            else:
                logger.warning(f"[GmailReader] Could not identify invite ID or intent for msg {msg_id}")
            
            # Mark Email as Processed (Remove UNREAD label)
            service.users().messages().modify(
                userId='me', 
                id=msg_id, 
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            logger.info(f"[GmailReader] Marked msg {msg_id} as processed.")
            
    except Exception as e:
        logger.error(f"[GmailReader] Failed to process emails for {email_address}: {e}", exc_info=True)
