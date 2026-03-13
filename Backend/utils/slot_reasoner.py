import json
from utils.llm import get_llm
from langchain_core.messages import HumanMessage


def choose_best_slot_with_llm(candidate_pref, available_slots):

    prompt = f"""
You are an interview scheduling assistant.

Candidate preferred time:
{candidate_pref}

Available slots:
{available_slots}

Rules:
1. If candidate preferred time exists in available_slots, choose it.
2. Otherwise choose the closest slot AFTER the preferred time.
3. Never choose a slot earlier than the preferred time.
4. Only choose from available_slots.

Return JSON:

{{
"selected_slot": "slot from available_slots"
}}
"""

    llm = get_llm()

    result = llm.invoke([HumanMessage(content=prompt)])

    content = result.content

    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()

    return json.loads(content)["selected_slot"]