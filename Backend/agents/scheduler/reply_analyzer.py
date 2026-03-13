import json
import logging
from utils.llm import get_llm
from langchain_core.messages import HumanMessage

# ---------------------------------------------------------------------------
# Reply Analyzer
# Uses LLM to determine the candidate's intent from their email reply.
# ---------------------------------------------------------------------------

logger = logging.getLogger("scheduler_agent")

def analyze_reply(email_text: str) -> dict:
    prompt = f"""You are an AI interview scheduling assistant.

Candidate email:
{email_text}

Determine candidate intent.

Return ONLY valid JSON in this exact format, with no explanation:
{{
"intent": "confirm" | "reschedule" | "reject",
"preferred_time": "Extract the exact datetime requested by the candidate. If the candidate says 'tomorrow at 4 PM', convert it to ISO format. Leave empty string if no specific time is requested."
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
