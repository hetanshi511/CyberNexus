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
    logger.info("Starting Gmail Watch Registration for all users...")
    
    # Get all authenticated emails from DB
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT email FROM user_oauth_tokens")).fetchall()
        
    if not rows:
        logger.error("No OAuth tokens found in DB. Did you complete the consent screen?")
        sys.exit(1)
        
    success_count = 0
    fail_count = 0

    for row in rows:
        email = row[0]
        logger.info(f"--------------------------------------------------")
        logger.info(f"Processing {email}...")
        
        try:
            service = get_gmail_service(email_address=email)
            
            # 1. Resolve Label ID for Interview-Replies
            logger.info("Fetching all labels to resolve 'Interview-Replies'...")
            results = service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            target_label_id = None
            for label in labels:
                if label['name'].lower() == 'interview-replies' or label['name'] == 'Interview-Replies':
                    target_label_id = label['id']
                    break
                    
            if not target_label_id:
                logger.warning(f"Could not find label 'Interview-Replies' for {email}! Please create it first. Skipping this account...")
                fail_count += 1
                continue
                
            logger.info(f"Resolved 'Interview-Replies' to ID: {target_label_id}")
            
            # 2. Register Watch for BOTH Security (INBOX) and Scheduler (Interview-Replies)
            request = {
                "labelIds": ["INBOX", target_label_id],
                "topicName": "projects/ai-marketplace-c169b/topics/gmail-interview-replies"
            }
            
            logger.info(f"Sending watch request for {email} to {request['topicName']}...")
            res = service.users().watch(userId="me", body=request).execute()
            
            logger.info(f"✅ GMAIL WATCH REGISTERED SUCCESSFULLY FOR {email}: {res}")
            success_count += 1
            
        except Exception as e:
            logger.error(f"❌ Failed to register watch for {email}: {e}", exc_info=True)
            fail_count += 1
            # Continue to the next email instead of exiting
            continue

    logger.info(f"--------------------------------------------------")
    logger.info(f"Registration Complete! Success: {success_count}, Failed: {fail_count}")

if __name__ == '__main__':
    register_watch()
