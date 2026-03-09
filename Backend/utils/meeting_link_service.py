"""
Meeting Link Service
Generates unique, real video-meeting URLs using Jitsi Meet.
Jitsi is free, open-source, and requires no API keys or accounts.
"""

import uuid
import logging

logger = logging.getLogger("scheduler_agent")


def generate_meeting_link() -> str:
    """
    Generate a unique, **working** meeting link via Jitsi Meet.

    Format: https://meet.jit.si/invinsense-interview-<uuid-short>
    Anyone with this link can join immediately — no login required.
    """
    room_id = uuid.uuid4().hex[:12]
    link = f"https://meet.jit.si/invinsense-interview-{room_id}"
    logger.info(f"Generated meeting link: {link}")
    return link
