"""
utils/attachment.py — Attachment download, extraction, and relevance checking.

UPDATED VERSION:
  - Sentence-aware semantic chunking
  - embed_query (ticket) vs embed_documents (chunks)
  - Batch embedding for performance
  - No unsafe hard truncation
  - Lowered default threshold (0.45)
  - Cache invalidation via Jira attachment_id (no file hashing)
"""

from __future__ import annotations

import io
import logging
import os
import re
from typing import Optional

import numpy as np
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

RELEVANCE_THRESHOLD: float = float(
    os.getenv("ATTACHMENT_RELEVANCE_THRESHOLD", "0.45")
)

CHUNK_SIZE: int = int(os.getenv("ATTACHMENT_CHUNK_SIZE", "1000"))

EMBED_MODEL: str = os.getenv("BEDROCK_EMBED_MODEL","amazon.titan-embed-text-v2:0")

# ---------------------------------------------------------------------------
# Lazy embedding client
# ---------------------------------------------------------------------------

_embeddings = None


def _get_embeddings():
    global _embeddings
    if _embeddings is None:
        from langchain_aws import BedrockEmbeddings

        region = os.getenv("AWS_DEFAULT_REGION","ap-southeast-2")

        if not EMBED_MODEL:
            raise ValueError("BEDROCK_EMBED_MODEL environment variable not set")

        _embeddings = BedrockEmbeddings(
            model_id=EMBED_MODEL,
            region_name=region,
        )
    return _embeddings


# ---------------------------------------------------------------------------
# Download
# ---------------------------------------------------------------------------

def download_attachment(url: str, email: str, token: str) -> bytes:
    response = requests.get(
        url,
        auth=HTTPBasicAuth(email, token),
        timeout=60,
    )
    response.raise_for_status()
    return response.content


# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------

def extract_pdf_text(file_bytes: bytes) -> str:
    try:
        import pdfplumber

        full_text = ""
        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page in pdf.pages:
                full_text += (page.extract_text() or "") + "\n"
        return full_text.strip()
    except Exception as exc:
        logger.warning(f"[Attach] PDF extraction failed: {exc}")
        return ""


def extract_image_text(file_bytes: bytes) -> str:
    try:
        from PIL import Image
        import pytesseract

        image = Image.open(io.BytesIO(file_bytes))
        return pytesseract.image_to_string(image)
    except Exception as exc:
        logger.warning(f"[Attach] OCR failed: {exc}")
        return ""


def extract_text_file(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="ignore")


def extract_attachment_content(
    attachment: dict,
    email: str,
    token: str,
) -> tuple[bytes, str]:

    url = attachment.get("content", "")
    mime = attachment.get("mimeType", "").lower()
    filename = attachment.get("filename", "")

    try:
        file_bytes = download_attachment(url, email, token)
    except Exception as exc:
        logger.error(f"[Attach] Download failed for '{filename}': {exc}")
        return b"", ""

    if "pdf" in mime:
        text = extract_pdf_text(file_bytes)
    elif "image" in mime:
        text = extract_image_text(file_bytes)
    elif "text" in mime or filename.endswith((".txt", ".log", ".csv", ".md")):
        text = extract_text_file(file_bytes)
    else:
        text = file_bytes.decode("utf-8", errors="ignore")

    return file_bytes, text


# ---------------------------------------------------------------------------
# Sentence-aware semantic chunking
# ---------------------------------------------------------------------------

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    """
    Sentence-aware chunking.
    Prevents cutting sentences mid-way.
    """
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    current_chunk = ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= chunk_size:
            current_chunk += sentence + " "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


# ---------------------------------------------------------------------------
# Embeddings & similarity
# ---------------------------------------------------------------------------

def cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)

    norm_a = np.linalg.norm(va)
    norm_b = np.linalg.norm(vb)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(va, vb) / (norm_a * norm_b))

# ---------------------------------------------------------------------------
# Orchestrator: process all attachments for one ticket
# ---------------------------------------------------------------------------

def process_ticket_attachments(
    attachments: list[dict],
    email: str,
    token: str,
    ticket_context: str,
    tenant_id: str,
    ticket_key: str,
) -> dict:
    """
    Process all attachments for a ticket.

    Cache invalidation: Jira assigns a globally-unique attachment_id on every
    upload. If an attachment_id is already in the DB, its analysis result is
    reused without re-downloading the file. If a user re-uploads a file, Jira
    gives it a new attachment_id, causing a cache miss and triggering
    re-analysis automatically.

    Returns:
    {
        "total": int,
        "relevant": int,
        "irrelevant": int,
        "all_relevant": bool,
        "any_relevant": bool,
        "attachment_ids": [str, ...],   # all processed attachment IDs (sorted)
        "details": [...]
    }
    """

    from utils.db import get_attachment_result, upsert_attachment

    results = []
    attachment_ids = []

    for att in attachments:
        att_id = att.get("attachment_id", "")
        filename = att.get("filename", "unknown")

        if att_id:
            attachment_ids.append(att_id)

        # --- Cache check: if this attachment_id is already in DB, reuse result ---
        cached = get_attachment_result(tenant_id, att_id) if att_id else None
        if cached:
            logger.info(f"[Attach] '{filename}' (id={att_id}) — cache hit (attachment_id already analysed).")
            results.append({
                "attachment_id": att_id,
                "filename": filename,
                "is_relevant": cached.get("is_relevant", True),
                "score": cached.get("relevance_score", 0.0),
            })
            continue

        # --- Extract ---
        file_bytes, extracted_text = extract_attachment_content(att, email, token)

        if not file_bytes:
            results.append({
                "attachment_id": att_id,
                "filename": filename,
                "is_relevant": True,  # fail-open
                "score": 0.0,
            })
            continue

        # --- Relevance Check ---
        is_relevant, score = check_attachment_relevance(
            att,
            file_bytes,
            extracted_text,
            ticket_context,
        )

        # --- Persist ---
        try:
            upsert_attachment(
                tenant_id=tenant_id,
                ticket_key=ticket_key,
                attachment_id=att_id,
                filename=filename,
                mime_type=att.get("mimeType", ""),
                relevance_score=score,
                is_relevant=is_relevant,
            )
        except Exception as exc:
            logger.error(f"[Attach] DB upsert failed for '{filename}': {exc}")

        results.append({
            "attachment_id": att_id,
            "filename": filename,
            "is_relevant": is_relevant,
            "score": score,
        })

    relevant_count = sum(1 for r in results if r["is_relevant"])
    irrelevant_count = len(results) - relevant_count

    return {
        "total": len(results),
        "relevant": relevant_count,
        "irrelevant": irrelevant_count,
        "all_relevant": irrelevant_count == 0,
        "any_relevant": relevant_count > 0,
        "attachment_ids": sorted(attachment_ids),
        "details": results,
    }


# ---------------------------------------------------------------------------
# Relevance pipeline (UPDATED)
# ---------------------------------------------------------------------------

def check_attachment_relevance(
    attachment: dict,
    file_bytes: bytes,
    extracted_text: str,
    ticket_context: str,
) -> tuple[bool, float]:

    filename = attachment.get("filename", "?")

    if not extracted_text.strip():
        logger.info(f"[Attach] '{filename}' — empty extraction.")
        return False, 0.0

    if not ticket_context.strip():
        logger.warning(f"[Attach] '{filename}' — no ticket context.")
        return True, 1.0  # fail-open

    try:
        embeddings = _get_embeddings()

        # 🔹 Embed ticket context as query
        ticket_embedding = embeddings.embed_query(ticket_context)

        # 🔹 Chunk attachment semantically
        chunks = chunk_text(extracted_text)

        if not chunks:
            return False, 0.0

        # 🔹 Batch embed attachment chunks (more efficient)
        chunk_embeddings = embeddings.embed_documents(chunks)

        max_score = 0.0

        for chunk_emb in chunk_embeddings:
            score = cosine_similarity(ticket_embedding, chunk_emb)
            if score > max_score:
                max_score = score

        is_relevant = max_score >= RELEVANCE_THRESHOLD

        logger.info(
            f"[Attach] '{filename}' — score={max_score:.4f}, "
            f"threshold={RELEVANCE_THRESHOLD}, relevant={is_relevant}"
        )

        return is_relevant, round(max_score, 4)

    except Exception as exc:
        logger.error(f"[Attach] Relevance check failed for '{filename}': {exc}")
        return True, 0.0
