"""
Email Security Agent — Email Fetcher
Fetches ONLY new, unread, and unlabeled emails from the Gmail inbox.
Emails that already have a security label (🟢 SAFE / 🟡 SPAM / 🔴 FRAUD / 🟠 SUSPICIOUS)
are SKIPPED to prevent re-analysis on refresh.
"""
import logging

logger = logging.getLogger("email_security")

# Label names applied by our agent — used to detect already-analyzed emails
SECURITY_LABEL_NAMES = {"🔴 FRAUD", "🟡 SPAM", "🟢 SAFE", "🟠 SUSPICIOUS"}


def _get_security_label_ids(service) -> set:
    """Return the Gmail label IDs for the 4 security labels (cached per call)."""
    try:
        all_labels = service.users().labels().list(userId="me").execute().get("labels", [])
        return {
            lbl["id"]
            for lbl in all_labels
            if lbl.get("name") in SECURITY_LABEL_NAMES
        }
    except Exception as e:
        logger.warning(f"[EmailFetcher] Could not fetch label list: {e}")
        return set()


def fetch_unanalyzed_emails(service, max_results: int = 20) -> list:
    """
    Returns unread inbox emails that have NOT already been labeled by the security agent.
    
    Flow:
      1. Query Gmail for UNREAD INBOX emails (respects max_results)
      2. Get the IDs of our 4 custom security labels from Gmail
      3. Skip any email that already carries one of those labels
      4. Return only fresh, unlabeled emails for analysis
    """
    try:
        # Step 1: Fetch unread inbox messages (no bulk scanning of all mail)
        result = (
            service.users()
            .messages()
            .list(
                userId="me",
                labelIds=["INBOX", "UNREAD"],
                maxResults=max_results,
            )
            .execute()
        )
        messages = result.get("messages", [])
        logger.info(f"[EmailFetcher] Found {len(messages)} unread inbox emails.")

        if not messages:
            return []

        # Step 2: Get our security label IDs (could be empty if none created yet)
        security_label_ids = _get_security_label_ids(service)

        if not security_label_ids:
            # No labels exist yet → all emails are fresh
            return messages

        # Step 3: Filter out already-labeled emails
        fresh = []
        for stub in messages:
            try:
                # Fetch just the metadata to check labels (no need to fetch full content)
                meta = service.users().messages().get(
                    userId="me", id=stub["id"], format="metadata",
                    metadataHeaders=[]
                ).execute()
                existing_labels = set(meta.get("labelIds", []))
                if existing_labels & security_label_ids:
                    logger.debug(
                        f"[EmailFetcher] Skipping already-analyzed email {stub['id']}"
                    )
                    continue
                fresh.append(stub)
            except Exception as e:
                logger.warning(f"[EmailFetcher] Could not check labels for {stub['id']}: {e}")
                fresh.append(stub)  # Include on error to avoid silently skipping

        logger.info(
            f"[EmailFetcher] {len(fresh)} fresh emails to analyze "
            f"({len(messages) - len(fresh)} already labeled, skipped)."
        )
        return fresh

    except Exception as e:
        logger.error(f"[EmailFetcher] Failed to list inbox messages: {e}", exc_info=True)
        return []


def fetch_single_email_by_id(service, message_id: str) -> list:
    """
    Returns a single email stub by message ID, or empty list if already labeled.
    Used by the real-time webhook to process exactly the newly arrived email.
    """
    try:
        security_label_ids = _get_security_label_ids(service)
        meta = service.users().messages().get(
            userId="me", id=message_id, format="metadata", metadataHeaders=[]
        ).execute()
        existing_labels = set(meta.get("labelIds", []))

        if existing_labels & security_label_ids:
            logger.info(f"[EmailFetcher] Webhook email {message_id} already labeled — skipping.")
            return []

        return [{"id": message_id, "threadId": meta.get("threadId", "")}]

    except Exception as e:
        logger.error(f"[EmailFetcher] Failed to fetch single email {message_id}: {e}", exc_info=True)
        return []
