import json
import logging
from utils.llm import get_llm
from langchain_core.messages import HumanMessage

logger = logging.getLogger("scheduler_agent")

def choose_best_slot_with_llm(candidate_pref: str, available_slots: list) -> str:
    """
    Given a candidate's preferred time and a list of strictly valid available slots,
    uses the LLM to reason and return the absolute best slot.
    """
    
    if not available_slots:
        return ""
        
    slots_str = json.dumps(available_slots, indent=2)

    prompt = f"""
You are an interview scheduling assistant.

Candidate preferred time:
{candidate_pref}

Available slots for recruiter (MUST strictly pick from these exact options):
{slots_str}

Choose the BEST slot for the interview.

Rules:
1. If candidate preference matches an available slot exactly, choose it.
2. Otherwise choose the closest available slot after the preference.
3. If no preference was given, choose the earliest available slot.
4. NEVER invent or hallucinate times not listed in available_slots. You MUST return an exact match from the array.

Return ONLY valid JSON in this exact format:
{{
"selected_slot": "ISO datetime exactly matching one from available slots"
}}
"""

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
        selected = data.get("selected_slot", "")
        
        # Fallback validation just in case
        if selected not in available_slots:
            logger.warning(f"[SlotReasoner] LLM returned invalid slot {selected}, falling back to earliest.")
            return available_slots[0]
            
        return selected
        
    except Exception as e:
        logger.error(f"[SlotReasoner] LLM slot selection failed: {e}", exc_info=True)
        # Safe fallback: Earliest available
        return available_slots[0] if available_slots else ""
