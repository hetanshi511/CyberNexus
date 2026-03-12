import logging
import re
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import os
import json
import base64

from utils.email_parser import extract_email_body
from utils.db import get_oauth_credentials
from agents.scheduler.reply_analyzer import analyze_reply
from agents.scheduler.reply_handler import handle_reply

# ---------------------------------------------------------------------------
# Gmail Reader Service
# Fetches unread replies from Gmail and triggers analysis/handling.
# ---------------------------------------------------------------------------

logger = logging.getLogger("scheduler_agent")

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

def get_gmail_service(email_address: str = None):
    """Build a Gmail API service using the service-account key or OAuth tokens."""
    # 1. Attempt using Offline Access OAuth Token if email is provided
    if email_address:
        db_creds = get_oauth_credentials(email_address)
        if db_creds and db_creds.get("refresh_token"):
            client_config = _get_client_config()
            creds = Credentials(
                token=db_creds["access_token"],
                refresh_token=db_creds["refresh_token"],
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_config.get("client_id"),
                client_secret=client_config.get("client_secret"),
                scopes=SCOPES
            )
            logger.info(f"[GmailReader] Using OAuth refresh token for {email_address}")
            return build('gmail', 'v1', credentials=creds)

    # 2. Fallback to Service Account
    sa_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "service_account.json")
    
    if os.path.exists(sa_path):
        creds = service_account.Credentials.from_service_account_file(sa_path, scopes=SCOPES)
    else:
        # Fallback to env var (Railway deployment)
        sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
        if not sa_json:
            raise FileNotFoundError("Service-account key not found.")
        
        if sa_json.startswith("{"):
            info = json.loads(sa_json)
        else:
            info = json.loads(base64.b64decode(sa_json).decode("utf-8").strip())
            
        creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        
    logger.info("[GmailReader] Using Service Account credentials mapped to me")
    return build('gmail', 'v1', credentials=creds)


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


def process_new_emails(email_address: str, history_id: str):
    """
    Fetch unread emails with the Interview-Replies label and process them.
    Notice that we use 'me' as userId, relying on domain-wide delegation
    or direct service account inbox if using a centralized webhook.
    """
    try:
        service = get_gmail_service(email_address)
        
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
