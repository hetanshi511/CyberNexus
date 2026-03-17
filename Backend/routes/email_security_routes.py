"""
Email Security Agent — FastAPI Router
GET /api/email-security/scan  — trigger a manual scan
POST /api/gmail-security-webhook — Pub/Sub push endpoint (real-time)
"""
import base64
import json
import logging
from fastapi import APIRouter, HTTPException, Request, Query

from agents.email_security.agent import run_email_security_scan
from services.gmail_reader import get_gmail_service

logger = logging.getLogger("email_security")

router = APIRouter()


@router.get("/api/email-security/scan")
async def scan_inbox(
    email: str = Query(..., description="Recruiter/user Gmail to scan"),
    max_results: int = Query(20, ge=1, le=50, description="Max emails to scan"),
):
    """
    Triggers a full security analysis of the user's Gmail inbox.
    Requires the user to have completed the OAuth flow via /api/auth/google/url first.
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


@router.post("/api/gmail-security-webhook")
async def gmail_security_webhook(request: Request):
    """
    Pub/Sub push endpoint for real-time email arrival notification.
    When a new email arrives, triggers a 1-email scan automatically.
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

        logger.info(f"[Webhook] Security notification for {email_address}")

        service = get_gmail_service(email_address)
        # Only scan 5 latest on webhook push to be fast
        results = await run_email_security_scan(service, max_results=5)

        return {"status": "processed", "emails_scanned": len(results)}

    except PermissionError as e:
        logger.warning(f"[Webhook] No OAuth token: {e}")
        return {"status": "no_token"}
    except Exception as e:
        logger.error(f"[Webhook] Security webhook error: {e}", exc_info=True)
        return {"status": "error"}
