import base64
import logging

# ---------------------------------------------------------------------------
# Email Parser Utility
# Extracts plain text from Gmail API message payloads safely.
# ---------------------------------------------------------------------------

logger = logging.getLogger("scheduler_agent")

def extract_email_body(message: dict) -> str:
    """Extract plain text body from Gmail message payload."""
    try:
        payload = message.get('payload', {})
        text = _get_text_from_payload(payload)
        return text.strip()
    except Exception as e:
        logger.error(f"[EmailParser] Error parsing email: {e}")
        return ""

def _get_text_from_payload(payload: dict) -> str:
    """Recursive helper for extracting text/plain."""
    mime_type = payload.get('mimeType')
    body_data = payload.get('body', {}).get('data')
    
    if mime_type == 'text/plain' and body_data:
        return base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
        
    text_content = ""
    parts = payload.get('parts', [])
    for part in parts:
        p_mime = part.get('mimeType')
        if p_mime == 'text/plain':
            data = part.get('body', {}).get('data')
            if data:
                text_content += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        elif p_mime in ['multipart/alternative', 'multipart/mixed']:
            text_content += _get_text_from_payload(part)
            
    return text_content
