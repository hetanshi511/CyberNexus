import json
import logging
from utils.llm import get_llm
from langchain_core.messages import HumanMessage

# ---------------------------------------------------------------------------
# Reply Analyzer
# Uses LLM to determine the candidate's intent from their email reply.
# ---------------------------------------------------------------------------

from datetime import datetime

logger = logging.getLogger("scheduler_agent")

def analyze_reply(email_text: str) -> dict:
    from utils.slot_generator import IST
    now = datetime.now(IST).strftime("%A, %Y-%m-%d %H:%M:%S IST")
    prompt = f"""You are an AI interview scheduling assistant.
The current date and time is: {now}

Candidate email:
{email_text}

Determine candidate intent.

Return ONLY valid JSON in this exact format, with no explanation:
{{
"intent": "confirm" | "reschedule" | "reject",
"preferred_time": "Extract any requested new time and MUST convert it into a strict ISO 8601 format string (e.g. 2026-03-14T15:00:00). If no time is suggested, leave as empty string"
}}"""

    try:
        llm = get_llm()
        result = llm.invoke([HumanMessage(content=prompt)])
        content = result.content
        
        # Clean JSON markdown if present
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        data = json.loads(content)
        intent = data.get("intent", "").lower()
        if intent not in ["confirm", "reschedule", "reject"]:
            intent = "confirm"
            
        return {
            "intent": intent,
            "preferred_time": data.get("preferred_time", "")
        }
    except Exception as e:
        logger.error(f"[ReplyAnalyzer] Failed to analyze reply: {e}", exc_info=True)
        return {"intent": "confirm", "preferred_time": ""}
