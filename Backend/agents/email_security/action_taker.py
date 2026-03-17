"""
Email Security Agent — Action Taker
Applies Gmail labels, moves to spam, and marks emails unread based on classification.
"""
import os
import logging
from googleapiclient.errors import HttpError

logger = logging.getLogger("email_security")

# Custom Gmail label names for the dashboard user can see
LABEL_FRAUD = "🔴 FRAUD"
LABEL_SPAM_CUSTOM = "🟡 SPAM"
LABEL_SAFE = "🟢 SAFE"


def _get_or_create_label(service, label_name: str) -> str:
    """Returns the labelId for a label, creating it if it doesn't exist."""
    try:
        labels = service.users().labels().list(userId="me").execute().get("labels", [])
        for lbl in labels:
            if lbl["name"] == label_name:
                return lbl["id"]

        # Create the label
        new_label = service.users().labels().create(
            userId="me",
            body={"name": label_name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
        ).execute()
        logger.info(f"[ActionTaker] Created label '{label_name}' with id {new_label['id']}")
        return new_label["id"]
    except HttpError as e:
        logger.warning(f"[ActionTaker] Could not get/create label '{label_name}': {e}")
        return None


def take_action(service, msg_id: str, classification: str) -> str:
    """
    Applies Gmail actions based on classification:
     - FRAUD / SPAM → move to Spam folder + apply custom label
     - SAFE → apply safe label only, leave in inbox
     - All → mark as UNREAD so user sees it
    Returns description of actions taken.
    """
    actions = []

    try:
        add_labels = []
        remove_labels = []

        if classification == "FRAUD":
            label_id = _get_or_create_label(service, LABEL_FRAUD)
            if label_id:
                add_labels.append(label_id)
            add_labels.append("SPAM")
            remove_labels.append("INBOX")
            actions.append("moved to Spam + labeled 🔴 FRAUD")

        elif classification == "SPAM":
            label_id = _get_or_create_label(service, LABEL_SPAM_CUSTOM)
            if label_id:
                add_labels.append(label_id)
            add_labels.append("SPAM")
            remove_labels.append("INBOX")
            actions.append("moved to Spam + labeled 🟡 SPAM")

        else:
            # SAFE — just label it
            label_id = _get_or_create_label(service, LABEL_SAFE)
            if label_id:
                add_labels.append(label_id)
            actions.append("labeled 🟢 SAFE")

        # Always mark as UNREAD so user notices it
        add_labels.append("UNREAD")

        service.users().messages().modify(
            userId="me",
            id=msg_id,
            body={"addLabelIds": add_labels, "removeLabelIds": remove_labels}
        ).execute()

        action_str = " + ".join(actions) + " + marked unread"
        logger.info(f"[ActionTaker] msg={msg_id} → {action_str}")
        return action_str

    except Exception as e:
        logger.error(f"[ActionTaker] Failed to act on {msg_id}: {e}", exc_info=True)
        return f"error: {e}"
