import json
from utils.llm import get_llm
from langchain_core.messages import HumanMessage


def choose_best_slot_with_llm(candidate_pref, available_slots):

    prompt = f"""
You are an interview scheduling assistant.

Candidate preferred time:
{candidate_pref}

Available slots for recruiter:
{available_slots}

Choose the BEST slot.

Rules:
1. If candidate preference matches available slot, choose it.
2. Otherwise choose the closest available slot after the preference.
3. If no preference, choose the earliest slot.

Return JSON:

{{
"selected_slot": "ISO datetime from available slots"
}}
"""

    llm = get_llm()

    result = llm.invoke([HumanMessage(content=prompt)])

    content = result.content

    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()

    return json.loads(content)["selected_slot"]