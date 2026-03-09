import httpx
from urllib.parse import urlparse
import logging

logger = logging.getLogger("header_validator.header_fetcher")

async def fetch_headers(url: str) -> tuple[dict, int, str]:
    """
    Fetches headers asynchronously from the given URL.
    Returns: (raw_headers_dict, status_code, normalized_url)
    """
    if not url.startswith('http'):
        url = 'https://' + url
        
    try:
        # Provide a realistic user-agent to bypass basic bot-blocking middleware that trips up scanners
        custom_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        async with httpx.AsyncClient(timeout=15, verify=False, follow_redirects=True) as client:
            response = await client.get(url, headers=custom_headers)
            
            raw_headers = {k.lower(): v for k, v in response.headers.items()}
            http_version = response.http_version
            return raw_headers, response.status_code, url, http_version
            
    except httpx.RequestError as e:
        logger.error(f"HTTPX Request Error connecting to {url}: {e}")
        raise ValueError(f"Failed to connect to {url}: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching {url}: {e}")
        raise ValueError(f"Unexpected HTTP error: {e}")
