"""
Slot Generator Utility
Generates 30-minute interview time slots within recruiter working hours.
"""

import logging
from datetime import datetime, timedelta, time as dt_time, timezone
from typing import List, Optional

# IST = UTC+5:30
IST = timezone(timedelta(hours=5, minutes=30))

logger = logging.getLogger("scheduler_agent")

# ── Configuration ──────────────────────────────────────────────────────
WORK_START = dt_time(9, 0)   # 09:00 AM
WORK_END   = dt_time(17, 0)  # 05:00 PM
SLOT_DURATION_MINUTES = 30
MAX_MEETINGS_PER_DAY  = 4


def generate_all_slots(date: datetime) -> List[datetime]:
    """
    Generate every possible 30-minute slot on *date* between WORK_START and
    WORK_END.  Returns a sorted list of ``datetime`` objects representing
    slot start times.
    """
    slots: List[datetime] = []
    current = datetime.combine(date.date() if isinstance(date, datetime) else date, WORK_START)
    end     = datetime.combine(date.date() if isinstance(date, datetime) else date, WORK_END)

    while current + timedelta(minutes=SLOT_DURATION_MINUTES) <= end:
        slots.append(current)
        current += timedelta(minutes=SLOT_DURATION_MINUTES)

    return slots


def _is_working_day(date: datetime) -> bool:
    """Monday=0 … Friday=4 are working days."""
    return date.weekday() < 5


def _next_working_day(date: datetime) -> datetime:
    """Return the next calendar date that is Mon–Fri."""
    nxt = date + timedelta(days=1)
    while not _is_working_day(nxt):
        nxt += timedelta(days=1)
    return nxt


def find_available_slot(
    start_date: datetime,
    busy_slots: List[datetime],
    daily_limit: int = MAX_MEETINGS_PER_DAY,
    max_search_days: int = 10,
) -> Optional[datetime]:
    """
    Walk forward from *start_date* and return the first free slot that
    satisfies:

    1. Not in *busy_slots* (comparison by hour + minute on the same date).
    2. The day has fewer than *daily_limit* existing meetings.
    3. Falls on a working day (Mon–Fri).

    Returns ``None`` if nothing is found within *max_search_days*.
    """
    current_date = start_date if _is_working_day(start_date) else _next_working_day(start_date)

    for _ in range(max_search_days):
        all_slots = generate_all_slots(current_date)

        # Busy slots for this specific date
        day_busy = [
            s for s in busy_slots
            if s[0].date() == current_date.date()
]

        # Already-booked count for the day
        booked_count = len(day_busy)

        if booked_count >= daily_limit:
            logger.info(
                f"Date {current_date.date()} already has {booked_count} meetings "
                f"(limit {daily_limit}). Skipping."
            )
            current_date = _next_working_day(current_date)
            continue

        # Filter out busy times (proper overlap detection) and past/too-soon slots
        # Use IST since Docker runs in UTC but working hours are IST
        now_ist = datetime.now(IST).replace(tzinfo=None)
        earliest_allowed = now_ist + timedelta(hours=1)
        free_slots = []
        for slot in all_slots:
            if slot <= earliest_allowed:
                continue
            slot_end = slot + timedelta(minutes=SLOT_DURATION_MINUTES)
            conflict = False
            for busy_start, busy_end in day_busy:
                if slot < busy_end and slot_end > busy_start:
                    conflict = True
                    break
            if not conflict:
                free_slots.append(slot)

        if free_slots:
            # Pick the first available slot (earliest in the day)
            selected = free_slots[0]
            logger.info(f"Selected slot: {selected}")
            return selected

        # All slots taken — move on
        current_date = _next_working_day(current_date)

    logger.warning(f"No available slot found within {max_search_days} days.")
    return None
