"""
PPT Generator Agent — FastAPI Router
POST /api/ppt-generator/generate  → JSON: session_id, outline, download_token, ...
GET  /api/ppt-generator/download/{token} → .pptx file (one-time, then cleaned up)
"""
import os
import uuid
import logging
import threading
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

logger = logging.getLogger("ppt_generator")
router = APIRouter()

# ── In-memory download store {token: {"path": str, "filename": str}} ──────────
_download_store: Dict[str, Dict[str, str]] = {}
_store_lock = threading.Lock()

# ── Request / Response models ─────────────────────────────────────────────────

class DocumentMetadata(BaseModel):
    owner: str
    email: str
    department: str
    version: str
    classification: str
    approved_by: str
    creation_date: str


class PPTGenerateRequest(BaseModel):
    raw_input: str
    user_instructions: Optional[str] = ""
    template_name: Optional[str] = "light_red"
    document_metadata: DocumentMetadata
    session_id: Optional[str] = None          # None = new session, reuse for updates


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_slide_content(slide: dict) -> str:
    """Extract paragraph-level speaker content from a slide dict."""
    parts = []
    for key in ("content", "body", "description", "text"):
        val = slide.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
        elif isinstance(val, list):
            parts.extend(str(v).strip() for v in val if str(v).strip())
    for key in ("key_points", "bullets", "points", "highlights"):
        val = slide.get(key)
        if isinstance(val, list):
            for kp in val:
                if isinstance(kp, str) and kp.strip():
                    parts.append(f"• {kp.strip()}")
                elif isinstance(kp, dict):
                    pt = kp.get("point") or kp.get("text") or kp.get("title", "")
                    if pt:
                        parts.append(f"• {pt.strip()}")
    for key in ("notes", "speaker_notes", "presenter_notes"):
        val = slide.get(key)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    return "\n".join(parts) if parts else ""


def _build_outline(slides: list) -> list:
    """Return a detailed outline (with content) from the slides list."""
    outline = []
    for i, s in enumerate(slides):
        if not isinstance(s, dict):
            continue
        outline.append({
            "index": i + 1,
            "title": s.get("title", f"Slide {i + 1}"),
            "type": s.get("type", s.get("slide_type", "content")),
            "has_chart": bool(
                s.get("chart_data") or s.get("bar_data")
                or s.get("pie_data") or s.get("line_data")
            ),
            "has_table": bool(s.get("table_data")),
            "content": _extract_slide_content(s),
        })
    return outline


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/api/ppt-generator/generate")
async def generate_presentation(request: PPTGenerateRequest):
    """
    Runs the AutoPresenter LangGraph workflow.
    • Pass session_id from a previous call to update the existing PPT.
    • Omit session_id (or pass null) to start a new session.
    Returns JSON with outline + a one-time download_token.
    """
    if not request.raw_input or not request.raw_input.strip():
        raise HTTPException(status_code=400, detail="raw_input is required.")

    meta = request.document_metadata
    missing = [k for k, v in {
        "owner": meta.owner, "email": meta.email,
        "department": meta.department, "version": meta.version,
        "classification": meta.classification, "approved_by": meta.approved_by,
    }.items() if not v]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required metadata fields: {', '.join(missing)}"
        )

    # Reuse session or start fresh
    session_id = (request.session_id or "").strip() or uuid.uuid4().hex
    is_update = bool(request.session_id and request.session_id.strip())
    logger.info(
        f"PPT Generator: session='{session_id}' update={is_update} "
        f"template='{request.template_name}'"
    )

    inputs = {
        "template_name": request.template_name,
        "document_metadata": meta.dict(),
        "raw_input": request.raw_input.strip(),
        "user_instructions": (request.user_instructions or "").strip(),
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
        # Keep existing slides so the planner's is_update_request logic fires
        # (graph will merge this with previous checkpoint on the same thread)
        "slides": [],
    }

    try:
        from agents.PPT_generator_from_JSON.graph_logic import app as ppt_app

        config = {"configurable": {"thread_id": session_id}}
        logger.info("PPT Generator: Invoking LangGraph workflow…")
        result = ppt_app.invoke(inputs, config=config)

        final_path = result.get("final_file_path", "")
        current_step = result.get("current_step", "")
        error_message = result.get("error_message", "")
        slides = result.get("slides", [])

        # ── Success ──────────────────────────────────────────────────────────
        if final_path and os.path.exists(final_path):
            token = uuid.uuid4().hex
            with _store_lock:
                _download_store[token] = {
                    "path": final_path,
                    "filename": "AutoPresenter_Output.pptx",
                }

            outline = _build_outline(slides)
            input_type = result.get("input_analysis", {}).get("input_type", "topic")
            logger.info(
                f"PPT Generator: Success — {len(slides)} slides, token={token}, input_type={input_type}"
            )
            return {
                "session_id": session_id,
                "is_update": is_update,
                "slide_count": len(slides),
                "outline": outline,
                "download_token": token,
                "generation_warning": result.get("generation_warning", ""),
                "input_type": input_type,
            }

        # ── Failure ──────────────────────────────────────────────────────────
        step_errors = {
            "input_analysis_failed": "Failed to analyse input. Check your topic or JSON.",
            "no_analytics_data":     "No suitable data found. Provide numeric JSON or a topic.",
            "planning_failed":       "Failed to create the presentation structure.",
            "validation_failed":     "Generated slides failed quality validation.",
            "visualization_build_failed": f"Failed to build charts/tables. {error_message}",
            "content_build_failed":  f"Failed to add text content. {error_message}",
        }
        user_msg = step_errors.get(
            current_step,
            f"Workflow ended at '{current_step}' without producing a file."
            + (f" Detail: {error_message}" if error_message else ""),
        )
        logger.error(
            f"PPT Generator: Workflow failed — step='{current_step}'"
        )
        raise HTTPException(status_code=500, detail=user_msg)

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"PPT Generator: Unexpected error — {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/ppt-generator/download/{token}")
async def download_presentation(token: str):
    """Serve the generated PPTX file once; removes entry from store after serving."""
    with _store_lock:
        entry = _download_store.pop(token, None)

    if not entry:
        raise HTTPException(status_code=404, detail="Download token not found or already used.")

    path = entry["path"]
    filename = entry["filename"]

    if not os.path.exists(path):
        raise HTTPException(status_code=410, detail="Generated file no longer exists on server.")

    return FileResponse(
        path=path,
        media_type=(
            "application/vnd.openxmlformats-officedocument"
            ".presentationml.presentation"
        ),
        filename=filename,
    )
