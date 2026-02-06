from typing import TypedDict
from langgraph.graph import StateGraph, END
from utils.llm import get_llm

class PolicyState(TypedDict):
    policy_source: str
    policy_target: str
    conflict_report: str
    final_status: str

def analyze_conflict(state: PolicyState):
    print("--- POLICY AGENT: ANALYZING ---")
    llm = get_llm()
    
    source = state["policy_source"]
    target = state["policy_target"]
    
    prompt = f"""You are a Senior Compliance Officer.
    Compare the following two policy documents.
    
    SOURCE POLICY:
    {source}
    
    TARGET STANDARD:
    {target}
    
    Output a structured report:
    1. Executive Summary
    2. Key Conflicts (cite specific sections)
    3. Recommended Changes
    """
    
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, 'content') else str(response)
    
    return {
        "conflict_report": content,
        "final_status": "Completed"
    }

# Workflow
workflow = StateGraph(PolicyState)
workflow.add_node("analyze", analyze_conflict)
workflow.set_entry_point("analyze")
workflow.add_edge("analyze", END)

app = workflow.compile()

async def run_policy_agent(source: str, target: str):
    state = {
        "policy_source": source,
        "policy_target": target,
        "conflict_report": "",
        "final_status": ""
    }
    result = await app.ainvoke(state)
    return {
        "status": result["final_status"],
        "report": result["conflict_report"]
    }
