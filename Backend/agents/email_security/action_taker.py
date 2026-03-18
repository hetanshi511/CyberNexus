"""
Email Security Agent — Action Taker
Applies Gmail labels, moves to Spam (FRAUD/SPAM), and correctly 
preserves the original read/unread state of each email.
"""
import logging
from googleapiclient.errors import HttpError

logger = logging.getLogger("email_security")

LABEL_FRAUD = "🔴 FRAUD"
LABEL_SPAM_CUSTOM = "🟡 SPAM"
LABEL_SAFE = "🟢 SAFE"
LABEL_SUSPICIOUS = "🟠 SUSPICIOUS"


def _get_or_create_label(service, label_name: str) -> str:
    """Returns the labelId for a label, creating it if it doesn't exist."""
    try:
        labels = service.users().labels().list(userId="me").execute().get("labels", [])
        for lbl in labels:
            if lbl["name"] == label_name:
                return lbl["id"]

        new_label = service.users().labels().create(
            userId="me",
            body={"name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
        ).execute()
        logger.info(f"[ActionTaker] Created label '{label_name}' → id={new_label['id']}")
        return new_label["id"]
    except HttpError as e:
        logger.warning(f"[ActionTaker] Could not get/create label '{label_name}': {e}")
        return None


def take_action(service, msg_id: str, classification: str, was_unread: bool = False) -> str:
    """
    Applies Gmail actions based on classification.

    Read/Unread policy (Problem 2 fix):
      - If the email WAS already read (was_unread=False) → keep it read (don't touch UNREAD label)
      - If the email WAS unread (was_unread=True) → restore UNREAD after labelling
      - FRAUD/SPAM → always restore UNREAD so user notices the threat

    Classification actions:
      - FRAUD   → move to Spam + 🔴 FRAUD label + always UNREAD
      - SPAM    → move to Spam + 🟡 SPAM label + always UNREAD
      - SUSPICIOUS → stay in inbox + 🟠 SUSPICIOUS label + restore original state
      - SAFE    → stay in inbox + 🟢 SAFE label + restore original state
    """
    actions = []
    add_labels = []
    remove_labels = []

    try:
        if classification == "FRAUD":
            label_id = _get_or_create_label(service, LABEL_FRAUD)
            if label_id:
                add_labels.append(label_id)
            add_labels.append("SPAM")
            remove_labels.append("INBOX")
            # Always mark unread for FRAUD so user sees it
            add_labels.append("UNREAD")
            actions.append("moved to Spam + labeled 🔴 FRAUD + marked unread")

        elif classification == "SPAM":
            label_id = _get_or_create_label(service, LABEL_SPAM_CUSTOM)
            if label_id:
                add_labels.append(label_id)
            add_labels.append("SPAM")
            remove_labels.append("INBOX")
            # Always mark unread for SPAM
            add_labels.append("UNREAD")
            actions.append("moved to Spam + labeled 🟡 SPAM + marked unread")

        elif classification == "SUSPICIOUS":
            # Trusted sender but suspicious content — don't move to Spam
            label_id = _get_or_create_label(service, LABEL_SUSPICIOUS)
            if label_id:
                add_labels.append(label_id)
            # Restore original read state
            if was_unread:
                add_labels.append("UNREAD")
            else:
                remove_labels.append("UNREAD")
            actions.append("labeled 🟠 SUSPICIOUS + read state preserved")

        else:  # SAFE
            label_id = _get_or_create_label(service, LABEL_SAFE)
            if label_id:
                add_labels.append(label_id)
            # Restore original read state — if it was read before, keep it read
            if was_unread:
                add_labels.append("UNREAD")
            else:
                remove_labels.append("UNREAD")
            actions.append("labeled 🟢 SAFE + read state preserved")

        service.users().messages().modify(
            userId="me",
            id=msg_id,
            body={"addLabelIds": add_labels, "removeLabelIds": remove_labels}
        ).execute()

        action_str = " | ".join(actions)
        logger.info(f"[ActionTaker] msg={msg_id} was_unread={was_unread} → {action_str}")
        return action_str

    except Exception as e:
        logger.error(f"[ActionTaker] Failed to act on {msg_id}: {e}", exc_info=True)
        return f"error: {e}"
