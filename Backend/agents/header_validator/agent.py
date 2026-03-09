import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

# Import our new modular tools
from agents.header_validator.tools.dns_lookup import resolve_domain
from agents.header_validator.tools.header_fetcher import fetch_headers
from agents.header_validator.tools.cookie_analyzer import analyze_cookies
from agents.header_validator.tools.csp_analyzer import analyze_csp, validate_hsts
from agents.header_validator.tools.scoring_engine import calculate_security_score
from agents.header_validator.services.report_generator import generate_llm_report

logger = logging.getLogger("header_validator_agent")

async def run_header_validator_agent(url: str):
    """
    Agentic workflow to fetch, deeply validate, and AI-reason about web security headers.
    """
    logger.info(f"Starting Agentic Header Validator for URL: {url}")

    try:
        # Step 1. Asynchronous DNS Lookup w/ SSRF verification
        parsed = urlparse(url)
        hostname = parsed.hostname or url
        ip_address = await resolve_domain(hostname)
        
        # Step 2. Asynchronous HTTP Header Fetching
        raw_headers, status_code, normalized_url, http_version = await fetch_headers(url)
        
        # Explicit normalization to ensure all operations are case-insensitive
        headers_normalized = {k.lower(): v for k, v in raw_headers.items()}

        # Step 3. Security Header Validations
        security_headers_def = {
            "content-security-policy": {"name": "Content-Security-Policy", "warning": "CSP prevents XSS and data injections. Highly critical to implement.", "category": "Critical"},
            "strict-transport-security": {"name": "Strict-Transport-Security", "warning": "HSTS enforces HTTPS connections. Its absence leaves you vulnerable to downgrade attacks.", "category": "Critical"},
            "x-frame-options": {"name": "X-Frame-Options", "warning": "Prevents clickjacking attacks by blocking unauthorized framing.", "category": "Critical"},
            "x-content-type-options": {"name": "X-Content-Type-Options", "warning": "Stops browsers from MIME-sniffing away from the declared content-type.", "category": "Critical"},
            "referrer-policy": {"name": "Referrer-Policy", "warning": "Controls how much domain information is leaked when users navigate away.", "category": "Recommended"},
            "permissions-policy": {"name": "Permissions-Policy", "warning": "Controls which browser features and APIs are enabled on your site.", "category": "Recommended"},
            "x-xss-protection": {"name": "X-XSS-Protection", "warning": "Legacy header. Modern browsers ignore it.", "category": "Optional", "optional": True},
            "expect-ct": {"name": "Expect-CT", "warning": "Allows applications to opt in to Certificate Transparency verification.", "category": "Optional", "optional": True},
            "clear-site-data": {"name": "Clear-Site-Data", "warning": "Clears browsing data (cookies, storage, cache) associated with the requesting website.", "category": "Optional", "optional": True}
        }
        
        upcoming_headers_def = {
            "cross-origin-embedder-policy": {"name": "Cross-Origin-Embedder-Policy", "description": "Prevents assets being loaded without explicit CORS or CORP grants."},
            "cross-origin-opener-policy": {"name": "Cross-Origin-Opener-Policy", "description": "Opt-in to Cross-Origin Isolation in the browser."},
            "cross-origin-resource-policy": {"name": "Cross-Origin-Resource-Policy", "description": "Specifies who can load the resource."}
        }

        missing_headers = []
        present_security_headers = []
        upcoming_headers = []

        # Analyze Core Security Headers
        for key, info in security_headers_def.items():
            if key in headers_normalized:
                # Value verification for Content-Type-Options
                if key == "x-content-type-options" and headers_normalized[key].lower() != "nosniff":
                    if not info.get("optional", False):
                        missing_headers.append({
                            "name": info["name"],
                            "description": f"X-Content-Type-Options is present but misconfigured (Value: {headers_normalized[key]}. Expected: nosniff).",
                            "category": info["category"]
                        })
                # Check for CSP Report-Only fallback
                elif key == "content-security-policy" and "content-security-policy-report-only" in headers_normalized:
                    present_security_headers.append({
                        "name": info["name"] + " (Report-Only)",
                        "value": headers_normalized["content-security-policy-report-only"],
                        "category": info["category"]
                    })
                else:
                    present_security_headers.append({
                        "name": info["name"],
                        "value": headers_normalized[key],
                        "category": info["category"]
                    })
            # Handle the edge case where actual CSP is missing, but Report-Only is present
            elif key == "content-security-policy" and "content-security-policy-report-only" in headers_normalized:
                 present_security_headers.append({
                    "name": info["name"] + " (Report-Only)",
                    "value": headers_normalized["content-security-policy-report-only"],
                    "category": info["category"]
                 })
            else:
                 if not info.get("optional", False):
                    missing_headers.append({
                        "name": info["name"],
                        "description": info["warning"],
                        "category": info["category"]
                    })

        # Process upcoming headers UI presentation
        for key, info in upcoming_headers_def.items():
            if key in headers_normalized:
                 upcoming_headers.append({"name": info["name"], "value": headers_normalized[key], "present": True, "description": info["description"]})
            else:
                 upcoming_headers.append({"name": info["name"], "present": False, "description": info["description"]})

        # Formatted lists for the frontend UI Raw view
        formatted_raw_headers = [{"name": "HTTP Status", "value": str(status_code)}]
        for k, v in raw_headers.items():
            formatted_raw_headers.append({"name": k, "value": v})

        # Step 4. Deep Introspective Analytis (Cookies, CSP, HSTS constraints)
        cookie_issues = analyze_cookies(headers_normalized)
        
        # Pull standard CSP, or fallback to Report-Only CSP
        csp_flags = []
        if 'content-security-policy' in headers_normalized:
            csp_flags = analyze_csp(headers_normalized['content-security-policy'], is_report_only=False)
        elif 'content-security-policy-report-only' in headers_normalized:
            csp_flags = analyze_csp(headers_normalized['content-security-policy-report-only'], is_report_only=True)
            csp_flags.insert(0, "[Report-Only] CSP is deployed in report-only mode and not actively enforced.")
            
        csp_issues = csp_flags
        hsts_issues = validate_hsts(headers_normalized.get('strict-transport-security', ''))
        
        security_issues = []
        if cookie_issues: security_issues.append({"category": "Cookies", "issues": cookie_issues})
        if csp_issues: security_issues.append({"category": "Content Security Policy", "issues": csp_issues})
        if hsts_issues: security_issues.append({"category": "Strict Transport Security", "issues": hsts_issues})
        
        # Redirect Security
        if url != normalized_url:
            if url.startswith("http://") and normalized_url.startswith("https://"):
                 pass # Good, HTTP to HTTPS
            else:
                 security_issues.append({"category": "Redirect Security", "issues": [f"Site redirects from {url} to {normalized_url} unexpectedly."]})
        
        # TLS / Protocol Versions
        if http_version in ["HTTP/1.0", "HTTP/1.1"]:
            alt_svc = raw_headers.get('alt-svc', '')
            if 'h2' in alt_svc or 'h3' in alt_svc:
                security_issues.append({"category": "TLS / Protocol Security (Info)", "issues": [f"HTTP/1.1 initial response detected but HTTP/2 or HTTP/3 upgrade is supported via Alt-Svc."] })
            else:
                security_issues.append({"category": "TLS / Protocol Security", "issues": [f"Legacy protocol detected ({http_version}). Upgrade to HTTP/2 or HTTP/3 for multiplexed secure connections."] })
        
        # Server Exposure detection
        server_header = headers_normalized.get("server", "")
        if "/" in server_header:
             security_issues.append({"category": "Server Exposure (Low Risk)", "issues": [f"Server version disclosure detected: {server_header}"]})
        if 'x-powered-by' in headers_normalized:
             security_issues.append({"category": "Server Exposure (Low Risk)", "issues": [f"Backend technology disclosed: {headers_normalized['x-powered-by']}"]})

        # Step 5. Automated Security Mathematical Scoring
        score, grade = calculate_security_score(missing_headers, cookie_issues, csp_issues, hsts_issues)
        
        report_time = datetime.now(timezone.utc).strftime("%d %b %Y %H:%M:%S UTC")

        # Step 6. Agentic LLM Evaluation 
        llm_analysis_text = await generate_llm_report(normalized_url, score, missing_headers, security_issues, raw_headers)

        # Assemble Payload matching previous schema format but expanded
        report = {
            "site": normalized_url,
            "ip_address": ip_address,
            "report_time": report_time,
            "status_code": status_code,
            "security_score": score,
            "grade": grade,
            "present_security_headers": present_security_headers,
            "missing_headers": missing_headers,
            "raw_headers": formatted_raw_headers,
            "upcoming_headers": upcoming_headers,
            "security_issues": security_issues,
            "llm_analysis": llm_analysis_text
        }

        logger.info(f"Agentic Validation complete for {normalized_url} (Score: {score})")
        return {
            "status": "Header validation completed successfully",
            "report": report
        }

    except ValueError as e:
        logger.warning(f"Validation aborted for {url}: {e}")
        return {
            "status": "Failed to analyze site",
            "error": str(e)
        }
    except Exception as e:
        logger.error(f"Unexpected error in Agentic Header Validator: {e}", exc_info=True)
        return {
            "status": "Failed to analyze site",
            "error": f"Internal Agent Error: {e}"
        }
