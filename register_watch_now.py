import sys
import os
import logging
sys.path.append(os.path.abspath('/app/Backend'))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from services.gmail_reader import get_gmail_service
from utils.db import engine
from sqlalchemy import text

def register_watch():
    logger.info("Starting Gmail Watch Registration...")
    
    # Get the authenticated email from DB
    with engine.connect() as conn:
        row = conn.execute(text("SELECT email FROM user_oauth_tokens ORDER BY updated_at DESC LIMIT 1")).fetchone()
        
    if not row:
        logger.error("No OAuth token found in DB. Did you complete the consent screen?")
        sys.exit(1)
        
    email = row[0]
    logger.info(f"Authenticating as {email} using Offline OAuth Token...")
    
    try:
        service = get_gmail_service(email_address=email)
        
        request = {
            "labelIds": ["Interview-Replies"],
            "topicName": "projects/ai-marketplace-c169b/topics/gmail-interview-replies"
        }
        
        logger.info(f"Sending watch request for {email} to {request['topicName']}...")
        res = service.users().watch(userId="me", body=request).execute()
        
        logger.info(f"✅ GMAIL WATCH REGISTERED SUCCESSFULLY: {res}")
        
    except Exception as e:
        logger.error(f"❌ Failed to register watch: {e}", exc_info=True)
        sys.exit(1)

if __name__ == '__main__':
    register_watch()
