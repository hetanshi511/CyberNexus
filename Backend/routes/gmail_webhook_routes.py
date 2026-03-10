import base64
import json
import logging
from fastapi import APIRouter, Request, BackgroundTasks
from services.gmail_reader import process_new_emails

# ---------------------------------------------------------------------------
# Gmail Webhook Route
# Receives push notifications from Google Pub/Sub when candidate replies.
# ---------------------------------------------------------------------------

logger = logging.getLogger("api")
router = APIRouter()

@router.post("/api/gmail-webhook")
async def gmail_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Endpoint for Google Pub/Sub Push Notification.
    """
    logger.info("[GmailWebhook] Received push notification.")
    try:
        data = await request.json()
        message = data.get("message", {})
        encoded_data = message.get("data")
        
        if encoded_data:
            # Decode the base64 Pub/Sub payload
            decoded_data = base64.b64decode(encoded_data).decode('utf-8')
            payload = json.loads(decoded_data)
            
            history_id = payload.get("historyId")
            email_address = payload.get("emailAddress")
            
            if history_id and email_address:
                logger.info(f"[GmailWebhook] Triggering background sync for {email_address}, historyId: {history_id}")
                background_tasks.add_task(process_new_emails, email_address, history_id)
            else:
                logger.warning("[GmailWebhook] Missing historyId or emailAddress in payload.")
        else:
            logger.warning("[GmailWebhook] No encoded data in Pub/Sub message.")
            
        return {"status": "received"}
    except Exception as e:
        logger.error(f"[GmailWebhook] Error processing webhook: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}
