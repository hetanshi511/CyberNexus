import re

def analyze_cookies(raw_headers: dict) -> list[str]:
    """
    Analyzes `set-cookie` headers for robust security implementations by isolating individual cookies.
    Returns a list of identified issues.
    """
    issues = []
    
    cookies_raw = raw_headers.get("set-cookie")
    if not cookies_raw:
        return issues

    # httpx and requests combine multiple Set-Cookie headers using commas, 
    # but actual cookie expiration dates also contain commas (e.g. Expires=Wed, 21 Oct).
    # A safe heuristic to split distinct cookies is replacing ', ' with a newline iff 
    # the next character isn't part of a date string, but for simplicity, we split by standard comma 
    # patterns that delineate key=value pairs.
    
    # Split heuristic targeting the start of a new cookie key=value pair
    cookie_list = re.split(r', (?=[a-zA-Z0-9_\-]+?=)', cookies_raw)
    
    for cookie in cookie_list:
        c_lower = cookie.lower()
        cookie_name = cookie.split('=')[0] if '=' in cookie else "Unknown"
        
        if "secure" not in c_lower:
            issues.append(f"[High] Cookie '{cookie_name}' is missing Secure flag, susceptible to interception over HTTP.")

        if "samesite" not in c_lower:
            issues.append(f"[Medium] Cookie '{cookie_name}' is missing SameSite attribute, vulnerable to CSRF.")
            
        if "httponly" not in c_lower:
            issues.append(f"[Low] Cookie '{cookie_name}' is missing HttpOnly flag. (Recommended, not mandatory)")

    return issues
