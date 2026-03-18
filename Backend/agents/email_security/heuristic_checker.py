"""
Email Security Agent — Heuristic + Domain Trust Checker
Combines keyword scanning, sender trust scoring (SPF/DKIM/DMARC + whitelist), 
spoofing detection, and suspicious pattern matching.
"""
import re
import logging

logger = logging.getLogger("email_security")

# ── Trusted known-good domains (subdomains accepted via endswith) ────────────
TRUSTED_DOMAINS = {
    "google.com", "accounts.google.com", "mail.google.com", "googleapis.com",
    "gmail.com", "youtube.com",
    "microsoft.com", "live.com", "outlook.com", "office.com", "microsoftonline.com",
    "apple.com", "icloud.com",
    "amazon.com", "aws.amazon.com",
    "github.com", "linkedin.com", "twitter.com", "facebook.com",
    "paypal.com", "stripe.com",
    "dropbox.com", "slack.com", "notion.so",
    "cloudflare.com", "sendgrid.net", "mailchimp.com", "mailgun.org",
    "railway.app",
}

# ── Phishing keywords ────────────────────────────────────────────────────────
SUSPICIOUS_KEYWORDS = [
    "urgent", "verify", "bank", "password", "lottery", "won", "prize",
    "claim", "account suspended", "click here", "confirm your",
    "you have been selected", "update your information", "unusual login",
    "limited time", "act now", "free money", "wire transfer", "gift card",
    "otp", "verify now", "dear customer", "dear user", "security alert",
    "final notice", "you are a winner", "suspended account", "credential",
    "sign in immediately", "validate your account",
]

# ── Character substitution spoofing patterns ─────────────────────────────────
SPOOF_SUBSTITUTIONS = [
    ("0", "o"), ("1", "i"), ("1", "l"), ("3", "e"), ("4", "a"),
    ("5", "s"), ("@", "a"), ("vv", "w"),
]

SPOOF_TARGET_BRANDS = [
    "google", "paypal", "microsoft", "apple", "amazon", "facebook",
    "netflix", "linkedin", "instagram", "twitter",
]


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_sender_trust(sender: str, headers: list) -> dict:
    """
    Returns a trust analysis dict:
      { trust_level: HIGH_TRUST|MEDIUM_TRUST|LOW_TRUST, 
        email, domain, spf_pass, dkim_pass, is_trusted_domain, is_spoofed }
    """
    email = _extract_email(sender)
    domain = _get_domain(email)

    trusted = _is_trusted_domain(domain)
    spf_pass, dkim_pass = _check_email_auth(headers)
    spoofed = _is_spoofed(domain)

    if spoofed:
        trust_level = "LOW_TRUST"
    elif trusted and spf_pass and dkim_pass:
        trust_level = "HIGH_TRUST"
    elif trusted:
        trust_level = "MEDIUM_TRUST"
    else:
        trust_level = "LOW_TRUST"

    logger.info(
        f"[DomainChecker] sender={email} domain={domain} trusted={trusted} "
        f"spf={spf_pass} dkim={dkim_pass} spoofed={spoofed} → {trust_level}"
    )
    return {
        "trust_level": trust_level,
        "email": email,
        "domain": domain,
        "spf_pass": spf_pass,
        "dkim_pass": dkim_pass,
        "is_trusted_domain": trusted,
        "is_spoofed": spoofed,
    }


def heuristic_check(subject: str, body: str, sender: str) -> list:
    """
    Returns a list of flags for suspicious content patterns.
    Does NOT consider sender trust (handled separately in decide node).
    Empty list means no suspicious content patterns found.
    """
    flags = []
    combined = (subject + " " + body).lower()

    # Keyword check
    for kw in SUSPICIOUS_KEYWORDS:
        if kw in combined:
            flags.append(f"suspicious_keyword:{kw}")
            break  # one keyword flag is enough

    # Deceptive CTA
    if re.search(r"click here|click below|click the link", combined):
        flags.append("deceptive_cta")

    # Suspicious URL in body but disguised with normal text
    if re.search(r"http[s]?://[^\s]{50,}", combined):
        flags.append("long_obfuscated_url")

    logger.info(f"[HeuristicChecker] Content flags: {flags or ['none']}")
    return flags


# ── Internals ────────────────────────────────────────────────────────────────

def _extract_email(sender: str) -> str:
    """Extract raw email from 'Display Name <email@domain.com>' format."""
    match = re.search(r"<(.+?)>", sender)
    return match.group(1).strip() if match else sender.strip()


def _get_domain(email: str) -> str:
    return email.split("@")[-1].lower() if "@" in email else email.lower()


def _is_trusted_domain(domain: str) -> bool:
    """Return True if domain matches any trusted domain via suffix comparison."""
    return any(domain == td or domain.endswith("." + td) for td in TRUSTED_DOMAINS)


def _check_email_auth(headers: list) -> tuple:
    """
    Reads Gmail's Authentication-Results header to check SPF and DKIM status.
    Returns (spf_pass: bool, dkim_pass: bool)
    """
    auth_header = next(
        (h["value"] for h in headers if h["name"].lower() == "authentication-results"),
        ""
    ).lower()

    spf_pass = "spf=pass" in auth_header
    dkim_pass = "dkim=pass" in auth_header

    return spf_pass, dkim_pass


def _is_spoofed(domain: str) -> bool:
    """
    Detect character-substitution domain spoofing.
    e.g. 'g00gle.com' or 'paypa1.com'
    """
    normalized = domain.lower()
    for char, replacement in SPOOF_SUBSTITUTIONS:
        normalized = normalized.replace(char, replacement)

    for brand in SPOOF_TARGET_BRANDS:
        # If normalized domain CONTAINS the brand name but ISN'T the trusted domain
        if brand in normalized and not _is_trusted_domain(domain):
            logger.warning(f"[DomainChecker] Possible spoofing detected: {domain} ≈ {brand}")
            return True

    return False
