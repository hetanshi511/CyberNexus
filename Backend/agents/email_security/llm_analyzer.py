"""
Email Security Agent — LLM Analyzer
Uses LLM to classify emails as SAFE / SPAM / FRAUD based on combined signals.
"""
import json
import logging
from utils.llm import get_llm
from langchain_core.messages import HumanMessage

logger = logging.getLogger("email_security")


def analyze_email_with_llm(
    subject: str,
    sender: str,
    body: str,
    attachment_results: list,
    link_results: list,
) -> dict:
    """
    Returns: { classification: SAFE|SPAM|FRAUD, confidence: high|medium|low, reason: str }
    """
    att_summary = _summarize_vt(attachment_results, "attachment")
    link_summary = _summarize_vt(link_results, "link")

    prompt = f"""You are an email cybersecurity analyst.

Analyze this email and classify it strictly as SAFE, SPAM, or FRAUD.

Email Details:
- Sender: {sender}
- Subject: {subject}
- Body (first 1000 chars): {body[:1000]}

VirusTotal Attachment Scan: {att_summary}
VirusTotal Link Scan: {link_summary}

Instructions:
- FRAUD: if VirusTotal reports malicious, or body contains phishing/impersonation/credential harvesting
- SPAM: if body contains commercial promotions, prizes, unsolicited offers
- SAFE: if email appears legitimate

Return ONLY valid JSON, no explanation:
{{
  "classification": "SAFE" | "SPAM" | "FRAUD",
  "confidence": "high" | "medium" | "low",
  "reason": "brief one-line explanation"
}}"""

    try:
        llm = get_llm()
        result = llm.invoke([HumanMessage(content=prompt)])
        content = result.content.strip()

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        data = json.loads(content)
        classification = data.get("classification", "SAFE").upper()
        if classification not in {"SAFE", "SPAM", "FRAUD"}:
            classification = "SAFE"

        return {
            "classification": classification,
            "confidence": data.get("confidence", "low"),
            "reason": data.get("reason", "")
        }

    except Exception as e:
        logger.error(f"[LLMAnalyzer] Analysis failed: {e}", exc_info=True)
        return {"classification": "SAFE", "confidence": "low", "reason": f"LLM error: {e}"}


def _summarize_vt(results: list, kind: str) -> str:
    if not results:
        return f"No {kind}s found."
    total_mal = sum(r.get("malicious", 0) for r in results)
    total_sus = sum(r.get("suspicious", 0) for r in results)
    return f"{len(results)} {kind}(s) scanned — {total_mal} malicious, {total_sus} suspicious"
