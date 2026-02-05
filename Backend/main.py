from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import uvicorn
import logging
import time
from agent import run_agent
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import pytz

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("api")

app = FastAPI(title="Cyber Security Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"Incoming Request: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"Request Completed: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")
        return response
    except Exception as e:
        logger.error(f"Request Failed: {request.method} {request.url.path} - Error: {e}")
        raise

class AgentRequest(BaseModel):
    linkedin_access_token: str
    topic: Optional[str] = "Cyber Security news from Google, GPT, and Linux Foundation"

@app.get("/")
def read_root():
    return {"status": "Agent Backend Running", "documentation": "/docs"}

@app.post("/api/execute_agent")
async def execute_agent(request: AgentRequest):
    logger.info(f"Executing agent for topic: {request.topic}")
    try:
        result = await run_agent(
            linkedin_access_token=request.linkedin_access_token,
            topic=request.topic
        )
        return result
    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Scheduler Setup ---
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
}
scheduler = AsyncIOScheduler(jobstores=jobstores)

async def scheduled_agent_task(linkedin_access_token: str, topic: str):
    logger.info(f"STARTING SCHEDULED JOB for topic: {topic}")
    try:
        await run_agent(linkedin_access_token, topic)
        logger.info("SCHEDULED JOB COMPLETED")
    except Exception as e:
        logger.error(f"Scheduled job failed: {e}", exc_info=True)

@app.on_event("startup")
def start_scheduler():
    scheduler.start()
    logger.info("Scheduler Started")

@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler Shut Down")

class ScheduleRequest(BaseModel):
    linkedin_access_token: str
    topic: Optional[str] = "Cyber Security news"
    schedule_type: str  # "date", "cron", "interval"
    schedule_params: Dict[str, Any] # e.g., {"run_date": "2024-02-10 15:30:00"} or {"minutes": 5}

@app.post("/api/schedule_agent")
async def schedule_agent(request: ScheduleRequest):
    try:
        job = None
        # Convert timezone-naive strings to aware if needed, or rely on APScheduler
        
        if request.schedule_type == "date":
            # Expects "run_date" in ISO format string or similar
            run_date = request.schedule_params.get("run_date")
            trigger = DateTrigger(run_date=run_date)
            
        elif request.schedule_type == "cron":
            # Expects standard cron params: minute, hour, day, month, day_of_week
            trigger = CronTrigger(**request.schedule_params)
            
        elif request.schedule_type == "interval":
            # Expects minutes, hours, etc.
            trigger = IntervalTrigger(**request.schedule_params)
            
        else:
            raise HTTPException(status_code=400, detail="Invalid schedule_type")

        job = scheduler.add_job(
            scheduled_agent_task,
            trigger=trigger,
            args=[request.linkedin_access_token, request.topic],
            name=f"Agent Run: {request.topic}"
        )
        
        return {
            "status": "Scheduled", 
            "job_id": job.id, 
            "run_time": str(job.next_run_time)
        }
        
    except Exception as e:
        logger.error(f"Scheduling failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/jobs")
def get_jobs():
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time
        })
    return jobs

@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    try:
        scheduler.remove_job(job_id)
        return {"status": "Job removed"}
    except Exception:
        raise HTTPException(status_code=404, detail="Job not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
