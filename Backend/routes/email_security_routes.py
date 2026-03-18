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


# ── Webhook Notification ──────────────────────────────────────────────────

@router.post("/api/gmail-security-webhook")
async def gmail_security_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Pub/Sub push endpoint for real-time email arrival.
    We just use this as a wake-up signal to trigger a normal scan of unanalyzed emails.
    The lock in email_fetcher.py prevents duplicate tags from being assigned if multiple
    webhooks fire closely together.
    """
    try:
        body = await request.json()
        message = body.get("message", {})
        data_encoded = message.get("data", "")
        if not data_encoded:
            return {"status": "no_data"}

        data = json.loads(base64.b64decode(data_encoded).decode("utf-8"))
        email_address = data.get("emailAddress", "")

        if not email_address:
            return {"status": "no_email_address"}

        logger.info(f"[Webhook] Security notification for {email_address} — triggering background scan.")

        # Run analysis in the background
        background_tasks.add_task(
            _scan_inbox_background, email_address
        )
        return {"status": "accepted"}

    except Exception as e:
        logger.error(f"[Webhook] Error: {e}", exc_info=True)
        return {"status": "error"}


async def _scan_inbox_background(email_address: str):
    """Wake-up scan for webhook."""
    try:
        service = get_gmail_service(email_address)
        
        # Will naturally skip already-labeled & locked emails!
        results = await run_email_security_scan(service, max_results=5)
        
        if results:
            logger.info(f"[Webhook] Processed {len(results)} new emails for {email_address}")
            
    except PermissionError as e:
        logger.warning(f"[Webhook] No OAuth token for {email_address}: {e}")
    except Exception as e:
        logger.error(f"[Webhook] Background scan failed for {email_address}: {e}", exc_info=True)


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
