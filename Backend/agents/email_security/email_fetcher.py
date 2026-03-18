"""
Email Security Agent — Email Fetcher
Fetches ONLY new and unlabeled emails from the Gmail inbox (whether read or unread).
Emails that already have a security label (🟢 SAFE / 🟡 SPAM / 🔴 FRAUD / 🟠 SUSPICIOUS)
are SKIPPED to prevent re-analysis on refresh.

Race-condition protection:
  PROCESSING_LOCK is an in-memory set of message IDs currently being analyzed.
  Claim an ID before starting analysis; release after.
  This ensures duplicate Pub/Sub webhook calls never process the same email twice.
"""
import logging

logger = logging.getLogger("email_security")

# Label names applied by our agent — used to detect already-analyzed emails
SECURITY_LABEL_NAMES = {"🔴 FRAUD", "🟡 SPAM", "🟢 SAFE", "🟠 SUSPICIOUS"}

# ── In-memory processing lock ─────────────────────────────────────────────
# Simple set; safe because FastAPI runs in a single-process async event loop.
# Prevents duplicate Pub/Sub webhook calls from double-processing the same email.
PROCESSING_LOCK: set = set()


def claim_message(message_id: str) -> bool:
    """
    Atomically claim a message_id for processing.
    Returns True if successfully claimed (caller should process it).
    Returns False if already claimed by another task (caller should skip it).
    """
    if message_id in PROCESSING_LOCK:
        logger.info(f"[Lock] Email {message_id} already being processed — skipping duplicate.")
        return False
    PROCESSING_LOCK.add(message_id)
    return True


def release_message(message_id: str):
    """Release the lock for a message_id after processing is complete or failed."""
    PROCESSING_LOCK.discard(message_id)


def _get_security_label_ids(service) -> set:
    """Return the Gmail label IDs for the 4 security labels."""
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


def _is_already_labeled(service, message_id: str, security_label_ids: set) -> bool:
    """Returns True if the email already has a security label applied."""
    if not security_label_ids:
        return False
    try:
        meta = service.users().messages().get(
            userId="me", id=message_id, format="metadata", metadataHeaders=[]
        ).execute()
        existing = set(meta.get("labelIds", []))
        return bool(existing & security_label_ids)
    except Exception as e:
        logger.warning(f"[EmailFetcher] Could not check labels for {message_id}: {e}")
        return False  # Assume unlabeled on error (safer to analyze than skip)


def fetch_unanalyzed_emails(service, max_results: int = 10) -> list:
    """
    Returns inbox emails that:
      1. Have NOT been labeled by the security agent yet
      2. Are NOT currently being processed (in-memory lock)

    Flow:
      1. Query Gmail for INBOX (respects max_results count)
      2. Check existing labels — skip already-classified ones
      3. Check the in-memory lock — skip ones currently being analyzed
      4. Return fresh unlabeled emails for analysis
    """
    try:
        result = (
            service.users()
            .messages()
            .list(
                userId="me",
                labelIds=["INBOX"],
                maxResults=max_results,
            )
            .execute()
        )
        messages = result.get("messages", [])
        logger.info(f"[EmailFetcher] Found {len(messages)} inbox emails.")

        if not messages:
            return []

        security_label_ids = _get_security_label_ids(service)

        fresh = []
        for stub in messages:
            msg_id = stub["id"]

            # Skip already-labeled
            if _is_already_labeled(service, msg_id, security_label_ids):
                logger.debug(f"[EmailFetcher] Skipping already-labeled email {msg_id}")
                continue

            # Skip currently-in-processing (race condition guard)
            if msg_id in PROCESSING_LOCK:
                logger.info(f"[EmailFetcher] Skipping in-progress email {msg_id}")
                continue

            fresh.append(stub)

        logger.info(
            f"[EmailFetcher] {len(fresh)} fresh emails to analyze "
            f"({len(messages) - len(fresh)} skipped)."
        )
        return fresh

    except Exception as e:
        logger.error(f"[EmailFetcher] Failed to list inbox messages: {e}", exc_info=True)
        return []


def fetch_single_email_by_id(service, message_id: str) -> list:
    """
    Returns a single email stub by ID for webhook processing.
    Returns empty list if:
      - email already has a security label, OR
      - it is already being processed (in-memory lock guards duplicate webhook calls)
    """
    try:
        # In-memory lock check first (fast, no API call)
        if message_id in PROCESSING_LOCK:
            logger.info(f"[EmailFetcher] Webhook dup: {message_id} already locked — skipping.")
            return []

        security_label_ids = _get_security_label_ids(service)

        if _is_already_labeled(service, message_id, security_label_ids):
            logger.info(f"[EmailFetcher] Webhook email {message_id} already labeled — skipping.")
            return []

        meta = service.users().messages().get(
            userId="me", id=message_id, format="metadata", metadataHeaders=[]
        ).execute()
        return [{"id": message_id, "threadId": meta.get("threadId", "")}]

    except Exception as e:
        logger.error(f"[EmailFetcher] Failed to fetch single email {message_id}: {e}", exc_info=True)
        return []
