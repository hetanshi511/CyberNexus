"""
Email Security Agent — LangGraph Orchestrator
Full pipeline: fetch → parse → heuristic → scan_attachments → scan_links
             → llm_analyze → decide → action
"""

import logging
from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, END

from agents.email_security.email_fetcher import (
    fetch_unanalyzed_emails, 
    fetch_single_email_by_id,
    claim_message,
    release_message
)
from agents.email_security.email_parser import parse_email_full, extract_links
from agents.email_security.heuristic_checker import heuristic_check, analyze_sender_trust
from agents.email_security.virustotal_scanner import scan_attachment, scan_url
from agents.email_security.llm_analyzer import analyze_email_with_llm
from agents.email_security.action_taker import take_action

logger = logging.getLogger("email_security")

# ── State ──────────────────────────────────────────────────────────────────

class EmailSecurityState(TypedDict):
    service: object           # Gmail API service (not serialised)
    email_id: str
    subject: str
    sender: str
    body: str
    headers: list             # Raw headers for SPF/DKIM
    was_unread: bool          # Original read state
    attachments: List[dict]   # [{ filename, data_bytes, size }]
    links: List[str]
    heuristic_flags: List[str]
    trust_score: dict         # domain trust analysis
    attachment_results: List[dict]
    link_results: List[dict]
    llm_classification: str
    llm_confidence: str
    llm_reason: str
    classification: str       # SAFE | SPAM | SUSPICIOUS | FRAUD (final)
    action_taken: str
    error: Optional[str]


# ── Nodes ──────────────────────────────────────────────────────────────────

def node_parse(state: EmailSecurityState) -> dict:
    logger.info(f"[Agent] Parsing email {state['email_id']}")
    parsed = parse_email_full(state["service"], state["email_id"])
    links = extract_links(parsed["body"])
    return {
        "subject": parsed["subject"],
        "sender": parsed["sender"],
        "body": parsed["body"],
        "headers": parsed.get("headers", []),
        "was_unread": parsed.get("was_unread", False),
        "attachments": parsed["attachments"],
        "links": links,
    }


def node_heuristic(state: EmailSecurityState) -> dict:
    # 1. Content Flags
    flags = heuristic_check(state["subject"], state["body"], state["sender"])
    # 2. Domain Trust (SPF/DKIM/Spoofing)
    trust = analyze_sender_trust(state["sender"], state.get("headers", []))
    
    return {"heuristic_flags": flags, "trust_score": trust}


def node_scan_attachments(state: EmailSecurityState) -> dict:
    results = []
    for att in state.get("attachments", []):
        r = scan_attachment(att["filename"], att["data_bytes"], att["size"])
        results.append(r)
        logger.info(f"[Agent] Attachment {att['filename']}: {r}")
    return {"attachment_results": results}


def node_scan_links(state: EmailSecurityState) -> dict:
    results = []
    links = state.get("links", [])
    for url in links[:5]:
        r = scan_url(url)
        results.append(r)
        logger.info(f"[Agent] Link {url}: {r}")
    return {"link_results": results}


def node_llm_analyze(state: EmailSecurityState) -> dict:
    result = analyze_email_with_llm(
        subject=state["subject"],
        sender=state["sender"],
        body=state["body"],
        attachment_results=state.get("attachment_results", []),
        link_results=state.get("link_results", []),
    )
    return {
        "llm_classification": result["classification"],
        "llm_confidence": result["confidence"],
        "llm_reason": result["reason"],
    }


def node_decide(state: EmailSecurityState) -> dict:
    """
    Final decision combining VirusTotal, Sender Trust, and LLM result.
    Priority:
      1. VirusTotal malicious → FRAUD
      2. Sender spoofed → FRAUD
      3. HIGH_TRUST domain + SPF/DKIM pass → SAFE override (if suspicous content → SUSPICIOUS)
      4. MEDIUM_TRUST → defer to LLM
      5. LOW_TRUST + Heuristics → SPAM
      6. LLM result fallback
    """
    att_results = state.get("attachment_results", [])
    link_results = state.get("link_results", [])
    trust_info = state.get("trust_score", {})
    trust_lvl = trust_info.get("trust_level", "LOW_TRUST")
    has_heuristics = len(state.get("heuristic_flags", [])) > 0
    llm = state.get("llm_classification", "SAFE")

    # 1. Hard Rule: VirusTotal malicious = FRAUD
    if any(r.get("malicious", 0) > 0 for r in att_results + link_results):
        classification = "FRAUD"
        
    # 2. Hard Rule: Spoofed Domain = FRAUD
    elif trust_info.get("is_spoofed"):
        classification = "FRAUD"
        
    # 3. Trusted Sender Override (HIGH_TRUST)
    elif trust_lvl == "HIGH_TRUST":
        # Never mark trusted domains as spam. If LLM or heuristics flagged it => SUSPICIOUS
        if has_heuristics or llm in ["SPAM", "FRAUD"]:
            classification = "SUSPICIOUS"
        else:
            classification = "SAFE"
            
    # 4. Medium Trust (Trusted domain, but missing SPF/DKIM)
    elif trust_lvl == "MEDIUM_TRUST":
        classification = llm  # Trust LLM more here
        
    # 5. Low Trust + Suspicious Content = SPAM automatically
    elif has_heuristics and llm != "FRAUD":
        classification = "SPAM"
        
    # 6. Fallback to LLM
    else:
        classification = llm

    logger.info(f"[Agent] Final classification for {state['email_id']}: {classification} (Trust: {trust_lvl}, LLM: {llm})")
    return {"classification": classification}


def node_action(state: EmailSecurityState) -> dict:
    # Pass was_unread state to action taker
    result = take_action(
        state["service"], 
        state["email_id"], 
        state["classification"], 
        was_unread=state.get("was_unread", False)
    )
    return {"action_taken": result}


# ── Build Graph ────────────────────────────────────────────────────────────

_workflow = StateGraph(EmailSecurityState)

_workflow.add_node("parse", node_parse)
_workflow.add_node("heuristic", node_heuristic)
_workflow.add_node("scan_attachments", node_scan_attachments)
_workflow.add_node("scan_links", node_scan_links)
_workflow.add_node("llm_analyze", node_llm_analyze)
_workflow.add_node("decide", node_decide)
_workflow.add_node("action", node_action)

_workflow.set_entry_point("parse")
_workflow.add_edge("parse", "heuristic")
_workflow.add_edge("heuristic", "scan_attachments")
_workflow.add_edge("scan_attachments", "scan_links")
_workflow.add_edge("scan_links", "llm_analyze")
_workflow.add_edge("llm_analyze", "decide")
_workflow.add_edge("decide", "action")
_workflow.add_edge("action", END)

_app = _workflow.compile()


# ── Public API ─────────────────────────────────────────────────────────────

async def run_email_security_scan(service, max_results: int = 20) -> list:
    """
    Manual scan: fetches up to max_results UNREAD + unlabeled emails and analyzes them.
    Already-labeled emails are skipped to prevent re-analysis on refresh.
    Returns a list of scan results.
    """
    emails = fetch_unanalyzed_emails(service, max_results=max_results)
    if not emails:
        logger.info("[Agent] No new unanalyzed emails to process.")
        return []

    return await _process_email_stubs(service, emails)


async def run_single_email_scan(service, message_id: str) -> list:
    """
    Real-time webhook path: analyzes exactly one newly arrived email by ID.
    Skips if the email already has a security label.
    Returns a list with 0 or 1 result.
    """
    stubs = fetch_single_email_by_id(service, message_id)
    if not stubs:
        return []
    return await _process_email_stubs(service, stubs)


async def _process_email_stubs(service, stubs: list) -> list:
    """Shared internal runner: processes a list of email stubs through the LangGraph pipeline."""
    results = []
    for stub in stubs:
        msg_id = stub["id"]
        
        # 1) Atomically claim this email to prevent duplicate processing by webhook races
        if not claim_message(msg_id):
            continue
            
        try:
            initial_state: EmailSecurityState = {
                "service": service,
                "email_id": msg_id,
                "subject": "",
                "sender": "",
                "body": "",
                "headers": [],
                "was_unread": False,
                "attachments": [],
                "links": [],
                "heuristic_flags": [],
                "trust_score": {},
                "attachment_results": [],
                "link_results": [],
                "llm_classification": "SAFE",
                "llm_confidence": "low",
                "llm_reason": "",
                "classification": "SAFE",
                "action_taken": "",
                "error": None,
            }
            final = await _app.ainvoke(initial_state)
            results.append({
                "email_id": msg_id,
                "subject": final.get("subject", ""),
                "sender": final.get("sender", ""),
                "classification": final.get("classification", "SAFE"),
                "confidence": final.get("llm_confidence", "low"),
                "reason": final.get("llm_reason", ""),
                "heuristic_flags": final.get("heuristic_flags", []),
                "action_taken": final.get("action_taken", ""),
                "trust_level": final.get("trust_score", {}).get("trust_level", "UNKNOWN"),
            })
        except Exception as e:
            logger.error(f"[Agent] Failed to process email {msg_id}: {e}", exc_info=True)
            results.append({"email_id": msg_id, "error": str(e)})
        finally:
            # 2) Release the lock when done
            release_message(msg_id)

    return results
