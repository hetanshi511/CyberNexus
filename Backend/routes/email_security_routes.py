"""
Email Security Agent — FastAPI Router
GET  /api/email-security/scan          — Manual scan (N newest unread+unlabeled emails)
POST /api/gmail-security-webhook       — Pub/Sub push: analyze the single newly arrived email
GET  /api/auth/gmail/connect           — Returns the Google OAuth consent URL
GET  /api/auth/gmail/connected/:email  — Checks if a user has OAuth tokens stored
"""
import asyncio
import base64
import json
import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Query

from agents.email_security.agent import run_email_security_scan, run_single_email_scan
from services.gmail_reader import get_gmail_service
from routes.auth_routes import get_google_oauth_url

logger = logging.getLogger("email_security")

router = APIRouter()


# ── Manual Scan ─────────────────────────────────────────────────────────────

@router.get("/api/email-security/scan")
async def scan_inbox(
    email: str = Query(..., description="Gmail address to scan"),
    max_results: int = Query(10, ge=1, le=50, description="Max NEW emails to analyze"),
):
    """
    Triggers security analysis on NEW (UNREAD + unlabeled) emails only.
    Already-classified emails are skipped automatically.
    """
    logger.info(f"[Route] Manual scan requested for {email} (max={max_results})")
    try:
        service = get_gmail_service(email)
        results = await run_email_security_scan(service, max_results=max_results)
        return {
            "status": "completed",
            "email": email,
            "scanned": len(results),
            "results": results,
        }
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"[Route] Scan failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ── Real-time Webhook ────────────────────────────────────────────────────────

@router.post("/api/gmail-security-webhook")
async def gmail_security_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Pub/Sub push endpoint for real-time email arrival.
    Processes ONLY the single newly arrived email identified in the notification.
    Returns 200 immediately; analysis runs in the background.
    """
    try:
        body = await request.json()
        message = body.get("message", {})
        data_encoded = message.get("data", "")
        if not data_encoded:
            return {"status": "no_data"}

        data = json.loads(base64.b64decode(data_encoded).decode("utf-8"))
        email_address = data.get("emailAddress", "")
        history_id = data.get("historyId")

        if not email_address:
            return {"status": "no_email_address"}

        logger.info(f"[Webhook] Security notification for {email_address} (historyId={history_id})")

        # Run analysis in the background so Pub/Sub doesn't timeout waiting
        background_tasks.add_task(
            _analyze_new_email_background, email_address, history_id
        )
        return {"status": "accepted"}

    except PermissionError as e:
        logger.warning(f"[Webhook] No OAuth token: {e}")
        return {"status": "no_token"}
    except Exception as e:
        logger.error(f"[Webhook] Security webhook error: {e}", exc_info=True)
        return {"status": "error"}


async def _analyze_new_email_background(email_address: str, history_id: str):
    """
    Background task: use Gmail history API to find the exact new message ID,
    then run a single-email security scan on it.
    """
    try:
        service = get_gmail_service(email_address)

        # Use historyId to find the specific new message(s) since the last known state
        history_result = service.users().history().list(
            userId="me",
            startHistoryId=history_id,
            historyTypes=["messageAdded"],
            labelId="INBOX",
        ).execute()

        history_records = history_result.get("history", [])
        new_message_ids = []
        for record in history_records:
            for added in record.get("messagesAdded", []):
                new_message_ids.append(added["message"]["id"])

        if not new_message_ids:
            logger.info(f"[Webhook] No new inbox messages found for historyId={history_id}")
            return

        # Analyze each newly arrived email (usually just 1)
        for msg_id in new_message_ids:
            logger.info(f"[Webhook] Analyzing new email {msg_id} for {email_address}")
            results = await run_single_email_scan(service, msg_id)
            if results:
                r = results[0]
                logger.info(
                    f"[Webhook] Done: {msg_id} classified as {r.get('classification')} "
                    f"(trust={r.get('trust_level')})"
                )

    except Exception as e:
        logger.error(f"[Webhook] Background analysis failed for {email_address}: {e}", exc_info=True)


# ── Gmail OAuth Connect helpers ──────────────────────────────────────────────

@router.get("/api/auth/gmail/connect")
async def get_gmail_connect_url():
    """Returns the Google OAuth consent URL for Gmail access."""
    return await get_google_oauth_url()


@router.get("/api/auth/gmail/connected")
async def check_gmail_connected(email: str = Query(...)):
    """Check if a user already has valid OAuth tokens stored for their Gmail."""
    from utils.db import get_oauth_credentials
    creds = get_oauth_credentials(email)
    has_token = bool(creds and creds.get("refresh_token"))
    return {"email": email, "connected": has_token}
