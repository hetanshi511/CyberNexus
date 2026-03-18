import os
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from utils.db import save_oauth_tokens

logger = logging.getLogger("auth")

router = APIRouter()

# In-memory store for PKCE code_verifier during the OAuth flow
oauth_states = {}

# Setup Google OAuth Flow
try:
    from google_auth_oauthlib.flow import Flow
    # Update SCOPES as necessary. Ensure you have Gmail Modify and Calendar Events
    SCOPES = [
        "https://www.googleapis.com/auth/calendar",
        "https://www.googleapis.com/auth/gmail.modify",
        "openid", 
        "https://www.googleapis.com/auth/userinfo.email"
    ]
except ImportError:
    Flow = None


def get_google_flow():
    """Retrieve Google OAuth Flow helper using client_secret.json"""
    client_secrets_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "client_secret.json")
    if not os.path.exists(client_secrets_file):
        raise HTTPException(
            status_code=500, 
            detail="client_secret.json missing. You must download it from GCP and place it in the Backend folder."
        )
        
    return Flow.from_client_secrets_file(
        client_secrets_file,
        scopes=SCOPES,
        redirect_uri=os.getenv("OAUTH_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
    )


@router.get("/api/auth/google/url")
async def get_google_oauth_url():
    """
    Returns the frontend-clickable URL to prompt Google 'Offline' consent.
    This guarantees a refresh_token is returned.
    """
    if not Flow:
        raise HTTPException(status_code=500, detail="google-auth-oauthlib not installed.")
        
    flow = get_google_flow()
    
    # access_type="offline" is literally the magic string to get the refresh token.
    # prompt="consent" forces Google to ask the user, ensuring a refresh token is always granted.
    authorization_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true"
    )
    
    if hasattr(flow, "code_verifier"):
        oauth_states[state] = getattr(flow, "code_verifier")
    
    return {"url": authorization_url}


@router.get("/api/auth/google/callback")
async def google_oauth_callback(code: str = Query(None), state: str = Query(None), error: str = Query(None)):
    """
    Handles the redirect back from Google.
    Exchanges the 'code' for access & refresh tokens and stores them in DB.
    """
    if error:
        logger.error(f"[OAuth] Google Auth Error: {error}")
        return {"status": "error", "error": error}
        
    if not code:
        raise HTTPException(status_code=400, detail="No authorization code received.")
        
    try:
        flow = get_google_flow()
        
        if state and state in oauth_states:
            flow.code_verifier = oauth_states.pop(state)
            
        # Google often adds default scopes (like profile) or reorders them.
        # This tells the library not to crash if the returned scopes mismatch the requested string exactly.
        os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get the email of the person who just authenticated
        from googleapiclient.discovery import build
        service = build("oauth2", "v2", credentials=credentials)
        user_info = service.userinfo().get().execute()
        email = user_info.get("email")
        
        if not email:
            raise Exception("Failed to retrieve user email from Google.")
            
        # Extract tokens
        access_token = credentials.token
        refresh_token = credentials.refresh_token # Will be None if not requested properly
        expiry = credentials.expiry  # datetime object
        
        # Store in DB securely
        saved = save_oauth_tokens(
            email=email,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expiry
        )
        
        if not saved:
            raise Exception("Failed to save tokens to database.")
            
        logger.info(f"[OAuth] Successfully fetched and saved tokens for {email}. Refresh Token Present: {bool(refresh_token)}")
        
        # Redirect to the frontend dashboard with a success flag
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
        return RedirectResponse(
            url=f"{frontend_url}/email-security-dashboard?connected=true",
            status_code=302
        )
        
    except Exception as e:
        logger.error(f"[OAuth] Token exchange failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
