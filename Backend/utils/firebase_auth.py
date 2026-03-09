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
import logging
from functools import lru_cache

import firebase_admin
from firebase_admin import credentials, auth as firebase_auth
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Firebase Admin SDK — initialised once
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_firebase_app() -> firebase_admin.App:
    """Initialise Firebase Admin SDK exactly once (thread-safe via lru_cache)."""
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "service_account.json")
    if not os.path.exists(cred_path):
        raise RuntimeError(
            f"Firebase service account file not found at '{cred_path}'. "
            "Download it from Firebase Console → Project Settings → Service Accounts."
        )
    cred = credentials.Certificate(cred_path)
    app = firebase_admin.initialize_app(cred)
    logger.info(f"[FirebaseAuth] Initialised using credentials from '{cred_path}'")
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
