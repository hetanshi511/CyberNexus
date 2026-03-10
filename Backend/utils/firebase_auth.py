"""
utils/firebase_auth.py — FastAPI dependency for Firebase JWT verification.

Usage in any endpoint:
    from utils.firebase_auth import get_current_tenant
    ...
    async def my_endpoint(tenant_id: str = Depends(get_current_tenant)):
        ...

The tenant_id is the Firebase UID — never trusted from the client, always
derived from the cryptographically verified ID token.
"""

import os
import json
import base64
import logging
import tempfile
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Firebase Admin SDK — initialised once
# ---------------------------------------------------------------------------

def _load_service_account_info():
    """Load service account credentials from file or environment variable."""
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "service_account.json")

    # Option 1: File exists on disk (local dev / Docker)
    if os.path.exists(cred_path):
        with open(cred_path) as f:
            return json.load(f), cred_path

    # Option 2: JSON stored in env var (Railway / cloud deployments)
    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if sa_json:
        logger.info(f"[FirebaseAuth] Env var found, length={len(sa_json)}, starts with: {sa_json[:20]}...")

        # Try raw JSON first (if it starts with '{')
        if sa_json.startswith("{"):
            info = json.loads(sa_json)
            return info, "GOOGLE_SERVICE_ACCOUNT_JSON env var (raw JSON)"

        # Try base64–encoded
        try:
            decoded = base64.b64decode(sa_json).decode("utf-8").strip()
            logger.info(f"[FirebaseAuth] Base64 decoded, length={len(decoded)}, starts with: {decoded[:20]}...")
            info = json.loads(decoded)
            return info, "GOOGLE_SERVICE_ACCOUNT_JSON env var (base64)"
        except Exception as e:
            logger.error(f"[FirebaseAuth] Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: {e}")
            raise RuntimeError(
                f"GOOGLE_SERVICE_ACCOUNT_JSON env var is set but could not be parsed. "
                f"Value length={len(sa_json)}, first chars='{sa_json[:30]}'. Error: {e}"
            )

    raise RuntimeError(
        "Firebase service account not found. Either:\n"
        "  1. Place 'service_account.json' in the Backend root, OR\n"
        "  2. Set GOOGLE_SERVICE_ACCOUNT_JSON env var with the JSON content (raw or base64-encoded)"
    )


@lru_cache(maxsize=1)
def _get_firebase_app() -> firebase_admin.App:
    """Initialise Firebase Admin SDK exactly once (thread-safe via lru_cache)."""
    info, source = _load_service_account_info()
    cred = credentials.Certificate(info)
    app = firebase_admin.initialize_app(cred)
    logger.info(f"[FirebaseAuth] Initialised using credentials from '{source}'")
    return app


# Eagerly initialise so startup errors surface immediately
try:
    _get_firebase_app()
except Exception as exc:
    logger.warning(f"[FirebaseAuth] Deferred init — will fail on first request: {exc}")


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_current_tenant(request: Request) -> str:
    """
    FastAPI dependency. Reads the Bearer token from the Authorization header,
    verifies it with Firebase, and returns the Firebase UID as tenant_id.

    Raises HTTP 401 on missing, malformed, expired, or revoked tokens.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected: Bearer <idToken>",
        )

    id_token = auth_header.split("Bearer ", 1)[1].strip()
    if not id_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Empty ID token in Authorization header.",
        )

    try:
        # Ensure SDK is initialised
        _get_firebase_app()
        decoded = firebase_auth.verify_id_token(id_token, check_revoked=True)
        tenant_id: str = decoded["uid"]
        logger.debug(f"[FirebaseAuth] Verified token for tenant: {tenant_id}")
        return tenant_id

    except firebase_auth.RevokedIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token has been revoked. Please sign in again.",
        )
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Firebase ID token has expired. Please sign in again.",
        )
    except firebase_auth.InvalidIdTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Firebase ID token: {exc}",
        )
    except Exception as exc:
        logger.error(f"[FirebaseAuth] Unexpected error verifying token: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not verify authentication token.",
        )
