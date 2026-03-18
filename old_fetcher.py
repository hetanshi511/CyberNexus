"""
Email Security Agent — Email Fetcher
Fetches unread emails from Gmail inbox using the Gmail API.
"""
import logging
logger = logging.getLogger("email_security")


def fetch_unread_emails(service, max_results: int = 20) -> list:
    """
    Returns a list of message stub dicts from Gmail inbox.
    Each stub contains only 'id' and 'threadId' — full parsing done separately.
    """
    try:
        result = (
            service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX"], maxResults=max_results)
            .execute()
        )
        messages = result.get("messages", [])
        logger.info(f"[EmailFetcher] Found {len(messages)} emails in inbox.")
        return messages
    except Exception as e:
        logger.error(f"[EmailFetcher] Failed to list inbox messages: {e}", exc_info=True)
        return []
