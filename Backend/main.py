from fastapi import FastAPI, HTTPException, Body, Request, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import uvicorn
import logging
import time
import re
import requests

# --- MODULAR AGENT IMPORTS ---
from agents.newsletter.agent import run_newsletter_agent
from agents.policy.agent import run_policy_agent
from agents.vendor.agent import run_vendor_agent
from agents.compliance.agent import run_compliance_agent, analyze_compliance
from agents.content_reviewer.agent import run_content_reviewer_agent
from agents.header_validator.agent import run_header_validator_agent
from agents.resume_reviewer.agent import run_resume_reviewer_agent

from routes.scheduler_routes import router as scheduler_router
from routes.gmail_webhook_routes import router as gmail_webhook_router
from routes.auth_routes import router as auth_router

from utils.firebase_auth import get_current_tenant
from utils.email_pdf import send_raw_pdf_email
from utils.playwright_pdf import generate_dashboard_pdf_playwright
from utils.google_drive import download_drive_file

from fastapi.responses import Response

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import pytz

# --- MODULAR AGENT IMPORTS ---
from services.gmail_reader import get_gmail_service

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

# --- Register Routers ---
app.include_router(scheduler_router)
app.include_router(gmail_webhook_router)
app.include_router(auth_router)

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
    agent_id: Optional[str] = "sec-1"
    linkedin_access_token: Optional[str] = None
    topic: Optional[str] = "Cyber Security news from Google, GPT, and Linux Foundation"
    policy_source: Optional[str] = None
    policy_target: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_docs: Optional[str] = None
    website_url: Optional[str] = None
    max_pages: Optional[int] = 5
    max_depth: Optional[int] = 2
    send_email_to: Optional[str] = None
    # Jira Fields
    jira_project_key: Optional[str] = None
    jira_ticket_id: Optional[str] = None
    jira_domain: Optional[str] = None
    jira_email: Optional[str] = None
    jira_token: Optional[str] = None

@app.get("/")
def read_root():
    return {"status": "Agent Backend Running", "documentation": "/docs"}

@app.post("/api/execute_agent")
async def execute_agent(
    request: AgentRequest,
    tenant_id: str = Depends(get_current_tenant),
):
    logger.info(f"Executing agent [{request.agent_id}] for tenant [{tenant_id}]")
    try:
        if request.agent_id == "compliance-bot":
            if not request.jira_domain or not request.jira_email or not request.jira_token:
                raise HTTPException(status_code=400, detail="Jira Domain, Email, and Token are required.")

            if not request.jira_project_key and not request.jira_ticket_id:
                raise HTTPException(status_code=400, detail="Either Jira Project Key or Ticket ID is required.")

            result = await run_compliance_agent(
                project_key=request.jira_project_key,
                ticket_id=request.jira_ticket_id,
                jira_domain=request.jira_domain,
                jira_email=request.jira_email,
                jira_token=request.jira_token,
                tenant_id=tenant_id,
            )
            return result

        elif request.agent_id == "sec-2":
            if not request.policy_source or not request.policy_target:
                raise HTTPException(status_code=400, detail="Both 'policy_source' and 'policy_target' are required for this agent.")
            result = await run_policy_agent(request.policy_source, request.policy_target)
            return result

        elif request.agent_id == "sec-3":
            if not request.vendor_name or not request.vendor_docs:
                raise HTTPException(status_code=400, detail="Both 'vendor_name' and 'vendor_docs' are required for this agent.")
            result = await run_vendor_agent(request.vendor_name, request.vendor_docs)
            return result
            
        elif request.agent_id == "content-reviewer":
            if not request.website_url:
                raise HTTPException(status_code=400, detail="'website_url' is required for the Content Reviewer agent.")
            result = await run_content_reviewer_agent(
                request.website_url,
                max_pages=request.max_pages,
                max_depth=request.max_depth,
                send_email_to=request.send_email_to
            )
            return result
            
        elif request.agent_id == "header-validator":
            if not request.website_url:
                raise HTTPException(status_code=400, detail="'website_url' is required for the Header Validator agent.")
            result = await run_header_validator_agent(request.website_url)
            return result

        else:
            # Default: Newsletter Agent (sec-1)
            if not request.linkedin_access_token:
                raise HTTPException(status_code=400, detail="LinkedIn Access Token is required for this agent.")
            result = await run_newsletter_agent(
                token=request.linkedin_access_token,
                topic=request.topic
            )
            return result

    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/execute_resume_reviewer")
async def execute_resume_reviewer(
    job_description: str = Form(...),
    resumes: Optional[list[UploadFile]] = File(None),
    drive_file_ids: Optional[str] = Form(None),
    drive_access_token: Optional[str] = Form(None),
):
    resumes_count = len(resumes) if resumes else 0
    logger.info(f"Executing resume_reviewer agent with {resumes_count} local resumes and Google Drive inputs")
    try:
        raw_candidates = []
        if resumes:
            for resume in resumes:
                content_bytes = await resume.read()
                raw_candidates.append({
                    "name": resume.filename,
                    "content_bytes": content_bytes,
                    "mime_type": resume.content_type
                })
            
        if drive_file_ids and drive_access_token:
            import json
            try:
                # Parse drive_file_ids if passed as a JSON string from frontend FormData
                file_ids_list = json.loads(drive_file_ids)
            except Exception:
                # Fallback if passed as a comma-separated string
                file_ids_list = [fid.strip() for fid in drive_file_ids.split(",") if fid.strip()]
                
            for file_id in file_ids_list:
                try:
                    file_bytes, file_name, mime_type = download_drive_file(
                        file_id,
                        drive_access_token
                    )
                    raw_candidates.append({
                        "name": file_name,
                        "content_bytes": file_bytes,
                        "mime_type": mime_type
                    })
                except Exception as e:
                    logger.error(f"Failed to download Google Drive file {file_id}: {e}")

        if not raw_candidates:
            return {"status": "Failed", "report": {"all_candidates": [], "shortlisted_candidates": [], "total_evaluated": 0, "total_shortlisted": 0, "error": "No resumes provided."}}

        result = await run_resume_reviewer_agent(job_description, raw_candidates)
        return result
    except Exception as e:
        logger.error(f"Resume Reviewer Agent execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class PDFGenerationRequest(BaseModel):
    to_email: str
    dashboard_route: str  # i.e., "/content-review-dashboard"
    report_data: dict

@app.post("/api/generate_and_mail_pdf")
async def generate_and_mail_pdf(request: PDFGenerationRequest):
    """
    Receives frontend state (report data), generates a perfect native PDF using Playwright,
    emails it to the user, and returns the PDF bytes for local download.
    """
    try:
        frontend_base_url = os.getenv("FRONTEND_INTERNAL_URL", "http://frontend:5000")
        full_url = f"{frontend_base_url}{request.dashboard_route}"
        
        # 1. Generate the perfect A4 PDF natively from Chromium engine
        pdf_bytes = await generate_dashboard_pdf_playwright(
            report_data=request.report_data,
            dashboard_url=full_url
        )
        
        # 2. Email it if an address is provided
        if request.to_email:
            send_raw_pdf_email(
                pdf_bytes=pdf_bytes, 
                to_email=request.to_email, 
                subject="Invinsense Dashboard Report"
            )
            
        # 3. Return a success confirmation to the frontend
        return {"status": "success", "message": "PDF generated and sent successfully."}
        
    except Exception as e:
        logger.error(f"Error handling dashboard PDF generation via Playwright: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# --- Compliance Test Endpoint (requires real JWT — tenant isolated) ---
class TestRequest(BaseModel):
    count: int = 20

@app.post("/api/compliance/test")
async def run_compliance_test(
    request: TestRequest,
    tenant_id: str = Depends(get_current_tenant),
):
    """
    Run compliance analysis against dummy Jira tickets.
    Requires valid Firebase JWT — results are stored under the authenticated tenant.
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    from test_compliance import generate_dummy_tickets

    count = max(1, min(request.count, 200))
    logger.info(f"[ComplianceTest] tenant={tenant_id}, count={count}")

    try:
        tickets = generate_dummy_tickets(count)
        fake_state = {
            "project_key": "TEST",
            "ticket_id": None,
            "jira_domain": "test.atlassian.net",
            "jira_email": "test@example.com",
            "jira_token": "dummy",
            "tickets": tickets,
            "project_report": [],
            "final_error": None,
            "tenant_id": tenant_id,
        }

        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            result_state = await loop.run_in_executor(pool, analyze_compliance, fake_state)

        report = result_state.get("project_report", [])
        satisfied = sum(1 for r in report if r.get("is_satisfied"))
        dissatisfied = len(report) - satisfied

        return {
            "status": "Test completed successfully",
            "mode": "test",
            "tenant_id": tenant_id,
            "total_tickets": len(report),
            "satisfied": satisfied,
            "dissatisfied": dissatisfied,
            "analysis_result": report,
        }

    except Exception as e:
        logger.error(f"[ComplianceTest] failed: {e}", exc_info=True)
        return {
            "status": "Test failed",
            "mode": "test",
            "tenant_id": tenant_id,
            "total_tickets": 0,
            "satisfied": 0,
            "dissatisfied": 0,
            "analysis_result": [],
            "error": str(e),
        }


# --- Scheduler Setup ---
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
}
scheduler = AsyncIOScheduler(jobstores=jobstores)

async def scheduled_agent_task(linkedin_access_token: str, topic: str):
    logger.info(f"STARTING SCHEDULED JOB for topic: {topic}")
    try:
        await run_newsletter_agent(linkedin_access_token, topic)
        logger.info("SCHEDULED JOB COMPLETED")
    except Exception as e:
        logger.error(f"Scheduled job failed: {e}", exc_info=True)

@app.on_event("startup")
def startup_event():
    import logging
    logger = logging.getLogger("api")
    logger.info("Scheduler Agent v2 running")
    scheduler.start()
    logger.info("Scheduler Started")
    
    # Run once at startup, then schedule every 24h
    register_gmail_watch()
    if not scheduler.get_job('gmail_watch_job'):
        scheduler.add_job(
            register_gmail_watch,
            IntervalTrigger(days=1),
            id='gmail_watch_job',
            name='Daily Gmail Watch Renewal',
            replace_existing=True
        )

def register_gmail_watch():
    """Register Gmail watch for Pub/Sub push notifications. Expires in 7 days."""
    try:
        from utils.db import engine
        from sqlalchemy import text
        
        with engine.connect() as conn:
            row = conn.execute(text("SELECT email FROM user_oauth_tokens ORDER BY updated_at DESC LIMIT 1")).fetchone()
            
        if not row:
            logger.warning("No OAuth token found in DB. Skipping automated watch registration.")
            return

        email = row[0]
        service = get_gmail_service(email_address=email)
        
        results = service.users().labels().list(userId='me').execute()
        labels = results.get('labels', [])
        
        target_label_id = None
        for label in labels:
            if label['name'].lower() == 'interview-replies':
                target_label_id = label['id']
                break
                
        if not target_label_id:
            logger.warning(f"Could not find label 'Interview-Replies' for {email}! Please create it.")
            return
            
        request = {
            "labelIds": [target_label_id],
            "topicName": "projects/ai-marketplace-c169b/topics/gmail-interview-replies"
        }
        res = service.users().watch(userId="me", body=request).execute()
        logger.info(f"Gmail watch registered successfully for {email}: {res}")
    except Exception as e:
        logger.error(f"Failed to register Gmail watch: {e}", exc_info=True)

@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()
    logger.info("Scheduler Shut Down")

class ScheduleRequest(BaseModel):
    linkedin_access_token: str
    topic: Optional[str] = "Cyber Security news"
    schedule_type: str  # "date", "cron", "interval"
    schedule_params: Dict[str, Any]

@app.post("/api/schedule_agent")
async def schedule_agent(request: ScheduleRequest):
    try:
        job = None
        if request.schedule_type == "date":
            run_date = request.schedule_params.get("run_date")
            trigger = DateTrigger(run_date=run_date)
        elif request.schedule_type == "cron":
            trigger = CronTrigger(**request.schedule_params)
        elif request.schedule_type == "interval":
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
