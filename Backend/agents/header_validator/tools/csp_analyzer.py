def analyze_csp(csp: str, is_report_only: bool = False) -> list[str]:
    """
    Analyzes Content-Security-Policy for unsafe practices.
    Returns a list of identified issues.
    """
    issues = []
    
    if not csp:
        return issues
        
    csp_lower = csp.lower()
    prefix = "[Report-Only] " if is_report_only else ""

    if "unsafe-inline" in csp_lower:
        issues.append(f"{prefix}CSP permits 'unsafe-inline' which drastically reduces XSS protection.")

    if "unsafe-eval" in csp_lower:
        issues.append(f"{prefix}CSP permits 'unsafe-eval' which allows potentially dangerous code execution.")

    if "*" in csp_lower:
        issues.append(f"{prefix}CSP contains a wildcard (*) source, trusting excessively broad origins.")
        
    if "data:" in csp_lower:
        issues.append(f"{prefix}CSP permits 'data:' URIs which can be used to bypass XSS protections.")

    return issues

def validate_hsts(hsts: str) -> list[str]:
    """
    Analyzes Strict-Transport-Security policy values.
    Returns a list of identified issues.
    """
    issues = []
    if not hsts:
        return issues
        
    hsts_lower = hsts.lower()
    
    if "max-age" not in hsts_lower:
        issues.append("HSTS is missing the required 'max-age' directive.")
        return issues
        
    try:
        max_age_str = hsts_lower.split("max-age=")[1].split(";")[0].strip()
        max_age_val = int(max_age_str)
        
        # 31536000 seconds = 1 year
        if max_age_val < 31536000:
            issues.append(f"HSTS max-age is {max_age_val}, which is shorter than the recommended 31536000 (1 year).")
    except Exception:
        issues.append("HSTS max-age directive is malformed.")
        
    if "includesubdomains" not in hsts_lower:
        issues.append("[Recommendation] Consider adding 'includeSubDomains' to enforce HTTPS across all subdomains.")
        
    return issues
