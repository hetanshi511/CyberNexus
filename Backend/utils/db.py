"""
utils/db.py — Multi-tenant PostgreSQL storage for compliance reports and attachments.

Features:
  - Schema auto-created on first import (CREATE TABLE IF NOT EXISTS + ALTER TABLE IF NOT EXISTS)
  - Row Level Security (RLS) enforced via app.current_tenant per connection
  - All writes are upserts → zero duplicates guaranteed
  - Sync SQLAlchemy engine; callers must use run_in_executor to stay non-blocking
  - Cache invalidation uses Jira attachment_id (not file content hash)
"""

import os
import json
import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from sqlalchemy import create_engine, text, cast, literal
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import SQLAlchemyError, OperationalError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Engine — lazily initialised on first use
# ---------------------------------------------------------------------------
_engine = None


def get_engine():
    """Return the SQLAlchemy engine, creating and initialising it on first call.

    Engine creation is deferred so that Railway's reference variable resolution
    (e.g. ``${{ Postgres.DATABASE_URL }}``) has time to complete before the app
    attempts a real TCP connection to the database.

    Retry logic (up to 5 attempts with exponential back-off) guards against the
    brief window where the Postgres service is still starting up.
    """
    global _engine
    if _engine is not None:
        return _engine

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not set")

    _engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args={"connect_timeout": 10},
    )

    # Attempt schema initialisation with retries so transient startup failures
    # (e.g. Postgres container not yet ready) are handled gracefully.
    _init_schema_with_retry(_engine)

    return _engine

# ---------------------------------------------------------------------------
# Schema bootstrap — runs once, idempotent
# ---------------------------------------------------------------------------
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tickets (
    tenant_id     TEXT      NOT NULL,
    ticket_key    TEXT      NOT NULL,
    project_key   TEXT      NOT NULL,
    jira_updated  TIMESTAMP,
    ticket_hash   TEXT      NOT NULL,
    last_analyzed TIMESTAMP,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (tenant_id, ticket_key)
);

-- Migration: drop attachment_combined_hash column if it exists (replaced by attachment IDs)
ALTER TABLE tickets
    DROP COLUMN IF EXISTS attachment_combined_hash;

CREATE TABLE IF NOT EXISTS ticket_reports (
    tenant_id              TEXT    NOT NULL,
    ticket_key             TEXT    NOT NULL,
    alignment_status       TEXT,
    severity               TEXT,
    completion_percentage  INTEGER,
    compliance_report      JSONB,
    analyzed_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (tenant_id, ticket_key),
    FOREIGN KEY (tenant_id, ticket_key)
        REFERENCES tickets(tenant_id, ticket_key)
        ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS attachments (
    tenant_id       TEXT      NOT NULL,
    ticket_key      TEXT      NOT NULL,
    attachment_id   TEXT      NOT NULL,
    filename        TEXT,
    mime_type       TEXT,
    relevance_score FLOAT,
    is_relevant     BOOLEAN,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (tenant_id, ticket_key, attachment_id),
    FOREIGN KEY (tenant_id, ticket_key)
        REFERENCES tickets(tenant_id, ticket_key)
        ON DELETE CASCADE
);

-- Migration: make legacy file_hash column nullable if it still exists
ALTER TABLE attachments
DROP COLUMN IF EXISTS file_hash;

CREATE INDEX IF NOT EXISTS idx_attachments_ticket
    ON attachments (tenant_id, ticket_key);

ALTER TABLE tickets         ENABLE ROW LEVEL SECURITY;
ALTER TABLE ticket_reports  ENABLE ROW LEVEL SECURITY;
ALTER TABLE attachments     ENABLE ROW LEVEL SECURITY;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'tickets' AND policyname = 'tenant_isolation_tickets'
    ) THEN
        CREATE POLICY tenant_isolation_tickets ON tickets
            USING (tenant_id = current_setting('app.current_tenant', true));
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'ticket_reports' AND policyname = 'tenant_isolation_reports'
    ) THEN
        CREATE POLICY tenant_isolation_reports ON ticket_reports
            USING (tenant_id = current_setting('app.current_tenant', true));
    END IF;
END $$;

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies
        WHERE tablename = 'attachments' AND policyname = 'tenant_isolation_attachments'
    ) THEN
        CREATE POLICY tenant_isolation_attachments ON attachments
            USING (tenant_id = current_setting('app.current_tenant', true));
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS user_oauth_tokens (
    email         TEXT PRIMARY KEY,
    access_token  TEXT NOT NULL,
    refresh_token TEXT,
    expires_at    TIMESTAMP,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def _init_schema(engine) -> None:
    """Run schema DDL once against *engine*. Safe to call repeatedly (IF NOT EXISTS guards)."""
    with engine.begin() as conn:
        conn.execute(text(_SCHEMA_SQL))
    logger.info("[DB] Schema initialised successfully")


def _init_schema_with_retry(engine, max_attempts: int = 5, base_delay: float = 2.0) -> None:
    """Call _init_schema with exponential back-off retries.

    Retries up to *max_attempts* times, doubling the wait after each failure
    (2 s → 4 s → 8 s → 16 s).  Raises the last exception if all attempts fail.
    """
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            _init_schema(engine)
            return
        except (SQLAlchemyError, OperationalError) as exc:
            last_exc = exc
            if attempt < max_attempts:
                delay = base_delay * (2 ** (attempt - 1))
                logger.warning(
                    f"[DB] Schema initialisation attempt {attempt}/{max_attempts} failed "
                    f"({exc}). Retrying in {delay:.0f}s…"
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"[DB] Schema initialisation failed after {max_attempts} attempts: {exc}"
                )
    raise last_exc


# ---------------------------------------------------------------------------
# RLS helper
# ---------------------------------------------------------------------------
def _set_tenant(conn, tenant_id: str) -> None:
    """Set the per-connection tenant for RLS enforcement."""
    conn.execute(
        text("SELECT set_config('app.current_tenant', :tid, true)"),
        {"tid": tenant_id},
    )


# ---------------------------------------------------------------------------
# Ticket functions
# ---------------------------------------------------------------------------

def get_ticket_hash(tenant_id: str, ticket_key: str) -> Optional[str]:
    """Return stored ticket_hash for (tenant_id, ticket_key), or None."""
    try:
        with get_engine().connect() as conn:
            _set_tenant(conn, tenant_id)
            row = conn.execute(
                text(
                    "SELECT ticket_hash FROM tickets "
                    "WHERE tenant_id = :tid AND ticket_key = :key"
                ),
                {"tid": tenant_id, "key": ticket_key},
            ).fetchone()
            return row[0] if row else None
    except SQLAlchemyError as exc:
        logger.error(f"[DB] get_ticket_hash({ticket_key}): {exc}")
        return None


def get_stored_attachment_ids(tenant_id: str, ticket_key: str) -> List[str]:
    """Return sorted list of attachment_ids already stored for (tenant_id, ticket_key)."""
    try:
        with get_engine().connect() as conn:
            _set_tenant(conn, tenant_id)
            rows = conn.execute(
                text(
                    "SELECT attachment_id FROM attachments "
                    "WHERE tenant_id = :tid AND ticket_key = :key"
                ),
                {"tid": tenant_id, "key": ticket_key},
            ).fetchall()
            return sorted(r[0] for r in rows)
    except SQLAlchemyError as exc:
        logger.error(f"[DB] get_stored_attachment_ids({ticket_key}): {exc}")
        return []


def load_report_from_db(tenant_id: str, ticket_key: str) -> Optional[Dict[str, Any]]:
    """Return the full dashboard_row dict stored for (tenant_id, ticket_key), or None."""
    try:
        with get_engine().connect() as conn:
            _set_tenant(conn, tenant_id)
            row = conn.execute(
                text(
                    "SELECT compliance_report FROM ticket_reports "
                    "WHERE tenant_id = :tid AND ticket_key = :key"
                ),
                {"tid": tenant_id, "key": ticket_key},
            ).fetchone()
            if row and row[0]:
                data = row[0] if isinstance(row[0], dict) else json.loads(row[0])
                return data
            return None
    except SQLAlchemyError as exc:
        logger.error(f"[DB] load_report_from_db({ticket_key}): {exc}")
        return None


def upsert_ticket(
    tenant_id: str,
    ticket_key: str,
    project_key: str,
    jira_updated,
    ticket_hash: str,
) -> None:
    """
    Insert or update the tickets row.
    ON CONFLICT → update hash and last_analyzed.
    Cache invalidation for attachments is handled via attachment_id uniqueness.
    """
    try:
        if isinstance(jira_updated, str) and jira_updated:
            try:
                jira_updated = datetime.fromisoformat(jira_updated.replace("Z", "+00:00"))
            except ValueError:
                jira_updated = None

        with get_engine().begin() as conn:
            _set_tenant(conn, tenant_id)
            conn.execute(
                text("""
                    INSERT INTO tickets
                        (tenant_id, ticket_key, project_key, jira_updated,
                         ticket_hash, last_analyzed)
                    VALUES
                        (:tid, :key, :project, :updated,
                         :hash, :analyzed)
                    ON CONFLICT (tenant_id, ticket_key)
                    DO UPDATE SET
                        jira_updated  = EXCLUDED.jira_updated,
                        ticket_hash   = EXCLUDED.ticket_hash,
                        last_analyzed = EXCLUDED.last_analyzed
                """),
                {
                    "tid": tenant_id,
                    "key": ticket_key,
                    "project": project_key,
                    "updated": jira_updated,
                    "hash": ticket_hash,
                    "analyzed": datetime.now(timezone.utc),
                },
            )
    except SQLAlchemyError as exc:
        logger.error(f"[DB] upsert_ticket({ticket_key}): {exc}")
        raise


def upsert_report(
    tenant_id: str,
    ticket_key: str,
    dashboard_row: Dict[str, Any],
) -> None:
    """
    Insert or update ticket_reports row.
    ON CONFLICT → overwrite with latest analysis.
    """
    try:
        report_json = json.dumps(dashboard_row)
        with get_engine().begin() as conn:
            _set_tenant(conn, tenant_id)
            conn.execute(
                text("""
                    INSERT INTO ticket_reports
                        (tenant_id, ticket_key, alignment_status, severity,
                         completion_percentage, compliance_report, analyzed_at)
                    VALUES
                        (:tid, :key, :alignment, :severity, :completion,
                         CAST(:report AS jsonb), :ts)
                    ON CONFLICT (tenant_id, ticket_key)
                    DO UPDATE SET
                        alignment_status      = EXCLUDED.alignment_status,
                        severity              = EXCLUDED.severity,
                        completion_percentage = EXCLUDED.completion_percentage,
                        compliance_report     = EXCLUDED.compliance_report,
                        analyzed_at           = EXCLUDED.analyzed_at
                """),
                {
                    "tid": tenant_id,
                    "key": ticket_key,
                    "alignment": dashboard_row.get("alignment_status"),
                    "severity": dashboard_row.get("priority"),
                    "completion": dashboard_row.get("completion_percentage"),
                    "report": report_json,
                    "ts": datetime.now(timezone.utc),
                },
            )
    except SQLAlchemyError as exc:
        logger.error(f"[DB] upsert_report({ticket_key}): {exc}")
        raise


# ---------------------------------------------------------------------------
# Attachment functions
# ---------------------------------------------------------------------------

def get_attachment_result(tenant_id: str, attachment_id: str) -> Optional[Dict[str, Any]]:
    """Return cached relevance result for an attachment, or None.
    A non-None return means this attachment_id was already analysed.
    """
    try:
        with get_engine().connect() as conn:
            _set_tenant(conn, tenant_id)
            row = conn.execute(
                text(
                    "SELECT relevance_score, is_relevant "
                    "FROM attachments "
                    "WHERE tenant_id = :tid AND attachment_id = :aid"
                ),
                {"tid": tenant_id, "aid": attachment_id},
            ).fetchone()
            if row:
                return {
                    "relevance_score": row[0],
                    "is_relevant": row[1],
                }
            return None
    except SQLAlchemyError as exc:
        logger.error(f"[DB] get_attachment_result({attachment_id}): {exc}")
        return None


def upsert_attachment(
    tenant_id: str,
    ticket_key: str,
    attachment_id: str,
    filename: str,
    mime_type: str,
    relevance_score: float,
    is_relevant: bool,
) -> None:
    """
    Insert or update an attachment row.
    ON CONFLICT (tenant_id, attachment_id) → update mutable fields.
    Cache invalidation is implicit: Jira assigns a new attachment_id on every
    upload, so a changed file will always produce a cache miss.
    """
    try:
        with get_engine().begin() as conn:
            _set_tenant(conn, tenant_id)
            conn.execute(
                text("""
                    INSERT INTO attachments
                        (tenant_id, ticket_key, attachment_id, filename, mime_type,
                         relevance_score, is_relevant)
                    VALUES
                        (:tid, :key, :aid, :fname, :mime,
                         :score, :relevant)
                    ON CONFLICT (tenant_id, attachment_id)
                    DO UPDATE SET
                        filename        = EXCLUDED.filename,
                        mime_type       = EXCLUDED.mime_type,
                        relevance_score = EXCLUDED.relevance_score,
                        is_relevant     = EXCLUDED.is_relevant
                """),
                {
                    "tid": tenant_id,
                    "key": ticket_key,
                    "aid": attachment_id,
                    "fname": filename,
                    "mime": mime_type,
                    "score": relevance_score,
                    "relevant": is_relevant,
                },
            )
    except SQLAlchemyError as exc:
        logger.error(f"[DB] upsert_attachment({attachment_id}): {exc}")
        raise


# ---------------------------------------------------------------------------
# Ticket hash helpers
# ---------------------------------------------------------------------------
# Bump this version whenever analysis criteria change.
# v1 = initial release
# v2 = Option C: Satisfied = is_satisfied AND alignment_status == Aligned
# v3 = Attachment relevance check added
# v4 = Cache invalidation uses attachment_id instead of file content hash
ANALYSIS_VERSION = "v4"


def compute_ticket_hash(ticket: dict, attachment_ids: Optional[List[str]] = None) -> str:
    """SHA-256 of ticket JSON + sorted attachment IDs + ANALYSIS_VERSION.

    Including attachment IDs means that when a new file is uploaded to Jira
    (new attachment_id) the hash changes and the ticket is re-analysed.
    Bumping ANALYSIS_VERSION forces full re-analysis of all cached tickets.
    """
    normalized = json.dumps(ticket, sort_keys=True, default=str)
    ids_str = "|".join(sorted(attachment_ids)) if attachment_ids else ""
    versioned = f"{ANALYSIS_VERSION}:{normalized}:{ids_str}"
    return hashlib.sha256(versioned.encode()).hexdigest()

# ---------------------------------------------------------------------------
# OAuth Token Storage (For Offline Background Refreshing, e.g. Gmail Webhooks)
# ---------------------------------------------------------------------------

def save_oauth_tokens(email: str, access_token: str, refresh_token: str = None, expires_at: datetime = None) -> bool:
    """Upsert OAuth access and refresh tokens for a given user email."""
    sql = """
        INSERT INTO user_oauth_tokens (email, access_token, refresh_token, expires_at, updated_at)
        VALUES (:email, :access, :refresh, :expires, CURRENT_TIMESTAMP)
        ON CONFLICT (email) DO UPDATE SET
            access_token = EXCLUDED.access_token,
            refresh_token = COALESCE(EXCLUDED.refresh_token, user_oauth_tokens.refresh_token),
            expires_at = EXCLUDED.expires_at,
            updated_at = CURRENT_TIMESTAMP
    """
    try:
        with get_engine().begin() as conn:
            conn.execute(
                text(sql),
                {
                    "email": email,
                    "access": access_token,
                    "refresh": refresh_token,
                    "expires": expires_at
                }
            )
        logger.info(f"[DB] Saved OAuth tokens for {email}")
        return True
    except SQLAlchemyError as exc:
        logger.error(f"[DB] Failed to save OAuth tokens for {email}: {exc}")
        return False

def get_oauth_credentials(email: str) -> Optional[Dict[str, Any]]:
    """Fetch the OAuth tokens for the given email, returning a dict if found."""
    sql = "SELECT access_token, refresh_token, expires_at FROM user_oauth_tokens WHERE email = :email"
    try:
        with get_engine().connect() as conn:
            row = conn.execute(text(sql), {"email": email}).fetchone()
            if row:
                return {
                    "access_token": row[0],
                    "refresh_token": row[1],
                    "expires_at": row[2]
                }
        return None
    except SQLAlchemyError as exc:
        logger.error(f"[DB] Failed to get OAuth tokens for {email}: {exc}")
        return None
