"""
Email Security Agent — LangGraph Orchestrator
Full pipeline: fetch → parse → heuristic → scan_attachments → scan_links
             → llm_analyze → decide → action
"""

import logging
from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, END

from agents.email_security.email_fetcher import fetch_unread_emails
from agents.email_security.email_parser import parse_email_full, extract_links
from agents.email_security.heuristic_checker import heuristic_check
from agents.email_security.virustotal_scanner import scan_attachment, scan_url
from agents.email_security.llm_analyzer import analyze_email_with_llm
from agents.email_security.action_taker import take_action

logger = logging.getLogger("email_security")


# ── State ──────────────────────────────────────────────────────────────────

class EmailSecurityState(TypedDict):
    service: object           # Gmail API service (not serialised — in-memory only)
    email_id: str
    subject: str
    sender: str
    body: str
    attachments: List[dict]   # [{ filename, data_bytes, size }]
    links: List[str]
    heuristic_flags: List[str]
    attachment_results: List[dict]
    link_results: List[dict]
    llm_classification: str
    llm_confidence: str
    llm_reason: str
    classification: str       # SAFE | SPAM | FRAUD (final)
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
        "attachments": parsed["attachments"],
        "links": links,
    }


def node_heuristic(state: EmailSecurityState) -> dict:
    flags = heuristic_check(state["subject"], state["body"], state["sender"])
    return {"heuristic_flags": flags}


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
    # Limit to first 5 links to avoid excessive API calls
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
    Final decision combining VirusTotal hard signals + LLM result + heuristics.
    Priority: VT malicious > LLM FRAUD > heuristics > LLM SPAM > SAFE
    """
    att_results = state.get("attachment_results", [])
    link_results = state.get("link_results", [])

    # Hard rule: any VirusTotal malicious → FRAUD immediately
    if any(r.get("malicious", 0) > 0 for r in att_results + link_results):
        classification = "FRAUD"
    elif state.get("llm_classification") == "FRAUD":
        classification = "FRAUD"
    elif state.get("heuristic_flags"):
        # Upgrade to SPAM if heuristics found something
        classification = "SPAM" if state.get("llm_classification") == "SAFE" else state.get("llm_classification", "SPAM")
    else:
        classification = state.get("llm_classification", "SAFE")

    logger.info(f"[Agent] Final classification for {state['email_id']}: {classification}")
    return {"classification": classification}


def node_action(state: EmailSecurityState) -> dict:
    result = take_action(state["service"], state["email_id"], state["classification"])
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
    Runs the full security scan on unread inbox emails.
    Returns a list of scan results per email.
    """
    emails = fetch_unread_emails(service, max_results=max_results)
    results = []

    for stub in emails:
        msg_id = stub["id"]
        try:
            initial_state: EmailSecurityState = {
                "service": service,
                "email_id": msg_id,
                "subject": "",
                "sender": "",
                "body": "",
                "attachments": [],
                "links": [],
                "heuristic_flags": [],
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
            })
        except Exception as e:
            logger.error(f"[Agent] Failed to process email {msg_id}: {e}", exc_info=True)
            results.append({"email_id": msg_id, "error": str(e)})

    return results
