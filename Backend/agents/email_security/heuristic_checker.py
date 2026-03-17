"""
Email Security Agent — Heuristic Checker
Fast rule-based pre-scan that flags suspicious patterns in emails.
"""
import re
import logging

logger = logging.getLogger("email_security")

# Known bad keywords in subject/body
SUSPICIOUS_KEYWORDS = [
    "urgent", "verify", "bank", "password", "lottery", "won", "prize",
    "claim", "account suspended", "click here", "confirm your", "you have been selected",
    "update your information", "unusual login", "limited time", "act now",
    "free money", "wire transfer", "gift card", "otp", "verify now",
    "dear customer", "dear user", "security alert", "your account",
    "final notice", "you are a winner"
]

# Known safe sending domains — these won't be flagged
SAFE_DOMAINS = {"gmail.com", "google.com", "microsoft.com", "apple.com", "amazon.com"}

# Suspicious domain patterns
SUSPICIOUS_DOMAIN_PATTERNS = [
    r"\d{2,}\.\w{2,4}$",       # numeric-heavy TLDs
    r"-(secure|login|verify)\.", # hyphenated phishing subdomains
]


def heuristic_check(subject: str, body: str, sender: str) -> list:
    """
    Returns a list of string flags describing suspicious patterns.
    Empty list means nothing detected.
    """
    flags = []
    combined = (subject + " " + body).lower()

    # Keyword check
    for kw in SUSPICIOUS_KEYWORDS:
        if kw in combined:
            flags.append(f"suspicious_keyword:{kw}")
            break  # one is enough to flag it

    # Sender domain check
    if "@" not in sender:
        flags.append("invalid_sender_format")
    else:
        domain = sender.split("@")[-1].strip(">").lower()
        if domain not in SAFE_DOMAINS:
            for pattern in SUSPICIOUS_DOMAIN_PATTERNS:
                if re.search(pattern, domain):
                    flags.append(f"suspicious_domain:{domain}")
                    break

    # Misleading link text check (text != URL)
    if re.search(r"click here|click below|click the link", combined):
        flags.append("deceptive_cta")

    logger.info(f"[HeuristicChecker] Flags: {flags or ['none']}")
    return flags
