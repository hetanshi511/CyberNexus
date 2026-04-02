"""
============================================================
  Invinsense Agent Test API — Postman-Ready FastAPI Server
============================================================
Separate REST endpoint per agent.
Every response follows this schema:
    {
        "status":  "success" | "error",
        "message": "<human readable description>",
        "result":  { ... agent-specific payload ... }
    }

Run:
    cd Backend
    uvicorn api_test_server:app --reload --port 8080

Swagger UI:
    http://localhost:8080/docs

Postman base URL: http://localhost:8080
============================================================
"""

import os
import sys
import logging
from typing import Optional, List, Any, Dict

# ── stdlib path fix so we can import from the Backend package ─────────────────
sys.path.insert(0, os.path.dirname(__file__))

# ── Load .env so LLM keys and other env vars are available ───────────────────
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
    else:
        _env_up = os.path.join(os.path.dirname(__file__), "..", ".env")
        if os.path.exists(_env_up):
            load_dotenv(_env_up)
except ImportError:
    pass  # python-dotenv not installed — rely on OS environment

import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("agent_test_api")


# ---------------------------------------------------------------------------
# App Setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Invinsense Agent Test API",
    description=(
        "One endpoint per agent — designed for direct Postman testing.\n\n"
        "All responses share a unified schema: `{status, message, result}`."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Unified response helpers
# ---------------------------------------------------------------------------
def ok(message: str, result: Any) -> dict:
    return {"status": "success", "message": message, "result": result}


def err(message: str, detail: Any = None) -> dict:
    return {
        "status": "error",
        "message": message,
        "result": {"error_detail": str(detail) if detail else None},
    }


# ===========================================================================
# 0. Health Check
# ===========================================================================
@app.get("/", tags=["Health"])
def health():
    """Health check — confirm the API is running."""
    return ok("Invinsense Agent Test API is running.", {"docs": "/docs"})


# ===========================================================================
# 1. Newsletter Agent
# POST /agents/newsletter
# ===========================================================================
class NewsletterRequest(BaseModel):
    topic: str = Field(
        default="Latest Cyber Security news",
        description="Topic / query for the Tavily web search.",
        example="Latest AI and Cyber Security threats 2025",
    )
    linkedin_access_token: Optional[str] = Field(
        default=None,
        description="Your LinkedIn OAuth2 Bearer token. Leave empty to skip posting.",
        example="AQX...",
    )


@app.post("/agents/newsletter", tags=["Newsletter Agent"])
async def run_newsletter(payload: NewsletterRequest):
    """
    **Newsletter Agent** — Searches the web for the given topic and drafts a
    LinkedIn cybersecurity newsletter. Optionally posts it to LinkedIn.

    - `topic` — what to write the newsletter about
    - `linkedin_access_token` — omit or pass `null` to skip LinkedIn posting
    """
    try:
        from agents.newsletter.agent import run_newsletter_agent

        result = await run_newsletter_agent(
            token=payload.linkedin_access_token or "",
            topic=payload.topic,
        )
        return ok("Newsletter generated successfully.", result)
    except Exception as e:
        logger.error("Newsletter Agent error: %s", e, exc_info=True)
        return err("Newsletter Agent failed.", e)


# ===========================================================================
# 2. Content Reviewer Agent
# POST /agents/content-reviewer
# ===========================================================================
class ContentReviewerRequest(BaseModel):
    website_url: str = Field(
        ...,
        description="Public website URL to crawl and review for content errors.",
        example="https://example.com",
    )
    max_pages: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of pages to crawl.",
        example=5,
    )
    max_depth: int = Field(
        default=2,
        ge=1,
        le=5,
        description="Maximum crawl depth from the root URL.",
        example=2,
    )
    send_email_to: Optional[str] = Field(
        default=None,
        description="Optional email address to receive the report. Leave null to skip.",
        example="reviewer@yourcompany.com",
    )


@app.post("/agents/content-reviewer", tags=["Content Reviewer Agent"])
async def run_content_reviewer(payload: ContentReviewerRequest):
    """
    **Content Reviewer Agent** — Crawls the given website, extracts visible
    text page by page, and uses an LLM to identify typos, grammar errors,
    punctuation mistakes, and spelling issues.
    """
    try:
        from agents.content_reviewer.agent import run_content_reviewer_agent

        result = await run_content_reviewer_agent(
            website_url=payload.website_url,
            max_pages=payload.max_pages,
            max_depth=payload.max_depth,
            send_email_to=payload.send_email_to,
        )
        return ok("Content review completed.", result)
    except Exception as e:
        logger.error("Content Reviewer Agent error: %s", e, exc_info=True)
        return err("Content Reviewer Agent failed.", e)


# ===========================================================================
# 3. Header Validator Agent
# POST /agents/header-validator
# ===========================================================================
class HeaderValidatorRequest(BaseModel):
    url: str = Field(
        ...,
        description="Full URL of the website to analyze for HTTP security headers.",
        example="https://example.com",
    )


@app.post("/agents/header-validator", tags=["Header Validator Agent"])
async def run_header_validator(payload: HeaderValidatorRequest):
    """
    **Header Validator Agent** — Fetches HTTP response headers from the target URL
    and performs deep security analysis:
    - Missing / misconfigured security headers (CSP, HSTS, X-Frame-Options, etc.)
    - Cookie security flags
    - TLS / protocol version checks
    - Server information disclosure
    - AI-generated executive summary & remediation advice
    - Numeric security score + grade (A–F)
    """
    try:
        from agents.header_validator.agent import run_header_validator_agent

        result = await run_header_validator_agent(payload.url)
        return ok("Header validation completed.", result)
    except Exception as e:
        logger.error("Header Validator Agent error: %s", e, exc_info=True)
        return err("Header Validator Agent failed.", e)


# ===========================================================================
# 4. Resume Reviewer Agent  (multipart/form-data — file upload)
# POST /agents/resume-reviewer
# ===========================================================================
@app.post("/agents/resume-reviewer", tags=["Resume Reviewer Agent"])
async def run_resume_reviewer(
    job_description: str = Form(
        ...,
        description="Full text of the job description used to evaluate each resume.",
    ),
    resumes: Optional[List[UploadFile]] = File(
        default=None,
        description="One or more resume PDF or text files to evaluate.",
    ),
):
    """
    **Resume Reviewer Agent** — Accepts a job description and one or more resume
    files (PDF/TXT). For each resume the agent:
    1. Extracts the candidate's text
    2. Scores them 0–10 against the job description
    3. Extracts the candidate email
    4. Writes a 2-line strengths / weaknesses summary

    Returns a ranked report with a shortlist of candidates scoring ≥ 8.

    > **Postman tip:** Use `form-data` body type. Add `job_description` (Text)
    > and one or more `resumes` fields (File).
    """
    try:
        from agents.resume_reviewer.agent import run_resume_reviewer_agent

        raw_candidates = []
        if resumes:
            for resume in resumes:
                content_bytes = await resume.read()
                raw_candidates.append(
                    {
                        "name": resume.filename,
                        "content_bytes": content_bytes,
                        "mime_type": resume.content_type or "application/octet-stream",
                    }
                )

        if not raw_candidates:
            raise HTTPException(
                status_code=400,
                detail="Please upload at least one resume file.",
            )

        result = await run_resume_reviewer_agent(job_description, raw_candidates)
        return ok(
            f"Evaluated {result.get('report', {}).get('total_evaluated', 0)} resume(s).",
            result,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Resume Reviewer Agent error: %s", e, exc_info=True)
        return err("Resume Reviewer Agent failed.", e)


# ===========================================================================
# 5. PPT Generator Agent (from JSON / Topic)
# POST /agents/ppt-generator
# ===========================================================================
class PPTDocumentMetadata(BaseModel):
    owner: str = Field(default="John Doe", example="John Doe")
    email: str = Field(default="john@company.com", example="john@company.com")
    department: str = Field(default="Engineering", example="Engineering")
    version: str = Field(default="1.0", example="1.0")
    classification: str = Field(default="Internal", example="Internal")
    approved_by: str = Field(default="Jane Smith", example="Jane Smith")
    creation_date: str = Field(default="2025-04-02", example="2025-04-02")


class PPTGeneratorRequest(BaseModel):
    raw_input: str = Field(
        ...,
        description=(
            "Either a plain topic string (e.g. 'Quantum Computing') "
            "or a JSON blob describing slide content."
        ),
        example="Zero Trust Security Architecture — best practices and implementation roadmap",
    )
    user_instructions: Optional[str] = Field(
        default="",
        description="Optional extra instructions for the planner (style, focus, etc.).",
        example="Keep it executive-level, 8 slides max, use a formal tone.",
    )
    template_name: Optional[str] = Field(
        default="light_red",
        description="Presentation template name.",
        example="light_red",
    )
    session_id: Optional[str] = Field(
        default=None,
        description=(
            "Omit (or pass null) for a NEW presentation. "
            "Re-use a previous session_id to UPDATE/refine an existing deck."
        ),
        example=None,
    )
    document_metadata: PPTDocumentMetadata = Field(
        default_factory=PPTDocumentMetadata
    )


@app.post("/agents/ppt-generator", tags=["PPT Generator Agent"])
async def run_ppt_generator(payload: PPTGeneratorRequest):
    """
    **PPT Generator Agent** — Generates a complete PowerPoint presentation from:
    - A plain topic string (agent researches & writes content), or
    - A structured JSON blob (agent converts it into rich slides with charts & tables)

    Returns a `download_token` — use `/agents/ppt-generator/download/{token}`
    to retrieve the `.pptx` file.
    """
    import uuid

    try:
        from agents.PPT_generator_from_JSON.graph_logic import app as ppt_app

        session_id = (payload.session_id or "").strip() or uuid.uuid4().hex
        is_update = bool(payload.session_id and payload.session_id.strip())

        inputs = {
            "template_name": payload.template_name,
            "document_metadata": payload.document_metadata.dict(),
            "raw_input": payload.raw_input.strip(),
            "user_instructions": (payload.user_instructions or "").strip(),
            "topic": "",
            "source_json": "",
            "user_query": "",
            "input_analysis": {},
            "visualization_preference": {},
            "current_step": "start",
            "temp_pptx_path": "",
            "final_file_path": "",
            "error_message": "",
            "search_results": "",
            "generation_warning": "",
            "slides": [],
        }

        config = {"configurable": {"thread_id": session_id}}
        result = ppt_app.invoke(inputs, config=config)

        final_path = result.get("final_file_path", "")
        slides = result.get("slides", [])

        if final_path and os.path.exists(final_path):
            token = uuid.uuid4().hex
            app.state.download_store[token] = {
                "path": final_path,
                "filename": "Agent_Presentation.pptx",
            }
            return ok(
                f"Presentation generated with {len(slides)} slides.",
                {
                    "session_id": session_id,
                    "is_update": is_update,
                    "slide_count": len(slides),
                    "download_token": token,
                    "download_url": f"/agents/ppt-generator/download/{token}",
                    "generation_warning": result.get("generation_warning", ""),
                    "input_type": result.get("input_analysis", {}).get("input_type", "topic"),
                },
            )

        return err(
            "PPT generation workflow completed but no file was produced.",
            result.get("error_message") or result.get("current_step"),
        )

    except Exception as e:
        logger.error("PPT Generator Agent error: %s", e, exc_info=True)
        return err("PPT Generator Agent failed.", e)


@app.on_event("startup")
async def _startup():
    app.state.download_store = {}


@app.get("/agents/ppt-generator/download/{token}", tags=["PPT Generator Agent"])
async def download_ppt(token: str):
    """
    **Download PPT** — Serve the generated `.pptx` file using the one-time
    `download_token` returned by `POST /agents/ppt-generator`.
    """
    store = getattr(app.state, "download_store", {})
    entry = store.pop(token, None)
    if not entry:
        raise HTTPException(
            status_code=404,
            detail="Token not found or already used.",
        )
    if not os.path.exists(entry["path"]):
        raise HTTPException(status_code=410, detail="File no longer exists on server.")

    return FileResponse(
        path=entry["path"],
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".presentationml.presentation"
        ),
        filename=entry["filename"],
    )


# ===========================================================================
# Entry point
# ===========================================================================
if __name__ == "__main__":
    uvicorn.run(
        "api_test_server:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info",
    )
