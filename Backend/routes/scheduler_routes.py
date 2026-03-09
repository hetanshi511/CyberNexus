"""
Scheduler Agent — FastAPI Router
Provides the POST /api/scheduler-agent endpoint.
"""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from agents.scheduler.agent import run_scheduler_agent

logger = logging.getLogger("scheduler_agent")

router = APIRouter()


class SchedulerRequest(BaseModel):
    candidate_name: str
    candidate_email: str
    job_role: str
    recruiter_name: str
    recruiter_email: str
    calendar_access_token: Optional[str] = None  # OAuth token from frontend


@router.post("/api/scheduler-agent")
async def schedule_interview(request: SchedulerRequest):
    """
    Schedule an interview between a candidate and a recruiter.

    The endpoint invokes the Scheduler Agent which:
    1. Validates input
    2. Finds an available calendar slot
    3. Generates a meeting link
    4. Creates a calendar event
    5. Sends a confirmation email to the candidate
    """
    logger.info(
        f"Scheduler Agent invoked — candidate={request.candidate_name}, "
        f"role={request.job_role}, recruiter={request.recruiter_name}, "
        f"oauth={'yes' if request.calendar_access_token else 'no'}"
    )

    try:
        result = await run_scheduler_agent(request.model_dump())

        if result.get("status") == "Failed":
            raise HTTPException(status_code=422, detail=result.get("error", "Unknown error"))

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Scheduler Agent endpoint error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
