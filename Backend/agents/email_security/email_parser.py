"""
Email Security Agent — Email Parser
Extracts subject, sender, headers, body, read state, and attachment bytes.
"""
import base64
import re
import logging

logger = logging.getLogger("email_security")

# Image extensions that are skipped for attachment scanning
SKIP_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".bmp", ".webp"}


def parse_email_full(service, msg_id: str) -> dict:
    """
    Fetches and parses a Gmail message.
    Returns:
        {
            subject, sender, body (plain text),
            headers: raw header list (for SPF/DKIM analysis),
            was_unread: bool (original read state BEFORE we touch it),
            attachments: [{ filename, data_bytes, size }],
        }
    """
    try:
        msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
        payload = msg.get("payload", {})
        headers = payload.get("headers", [])
        label_ids = msg.get("labelIds", [])

        # Capture the original unread state BEFORE any modification
        was_unread = "UNREAD" in label_ids

        subject = _header(headers, "Subject")
        sender = _header(headers, "From")
        body = _extract_body(payload)
        attachments = _extract_attachments(service, msg_id, payload)

        return {
            "subject": subject,
            "sender": sender,
            "body": body,
            "headers": headers,
            "was_unread": was_unread,
            "attachments": attachments,
        }
    except Exception as e:
        logger.error(f"[EmailParser] Failed to parse {msg_id}: {e}", exc_info=True)
        return {"subject": "", "sender": "", "body": "", "headers": [], "was_unread": False, "attachments": []}


def extract_links(text: str) -> list:
    """Extract all http/https URLs from text."""
    return list(set(re.findall(r"https?://[^\s\"'>]+", text)))


# ── Internals ──────────────────────────────────────────────────────────────

def _header(headers: list, name: str) -> str:
    return next((h["value"] for h in headers if h["name"].lower() == name.lower()), "")


def _extract_body(payload: dict) -> str:
    """Recursively extract plain text body."""
    mime = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if mime == "text/plain" and body_data:
        return base64.urlsafe_b64decode(body_data + "==").decode("utf-8", errors="replace")

    for part in payload.get("parts", []):
        text = _extract_body(part)
        if text:
            return text

    return ""


def _extract_attachments(service, msg_id: str, payload: dict) -> list:
    """Extract attachments from message parts. Skips images."""
    attachments = []
    for part in payload.get("parts", []):
        filename = part.get("filename", "")
        if not filename:
            continue

        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext in SKIP_EXTENSIONS:
            logger.info(f"[EmailParser] Skipping image attachment: {filename}")
            continue

        att_id = part.get("body", {}).get("attachmentId")
        size = part.get("body", {}).get("size", 0)

        if att_id:
            try:
                att = service.users().messages().attachments().get(
                    userId="me", messageId=msg_id, id=att_id
                ).execute()
                data = base64.urlsafe_b64decode(att.get("data", "") + "==")
                attachments.append({"filename": filename, "data_bytes": data, "size": size})
            except Exception as e:
                logger.warning(f"[EmailParser] Could not fetch attachment {filename}: {e}")

    return attachments
