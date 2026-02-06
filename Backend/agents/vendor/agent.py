from typing import TypedDict
from langgraph.graph import StateGraph, END
from utils.llm import get_llm

class VendorState(TypedDict):
    vendor_name: str
    vendor_docs: str
    risk_report: str
    final_status: str

def assess_vendor_risk(state: VendorState):
    print("--- VENDOR AGENT: ASSESSING ---")
    llm = get_llm()
    
    vendor = state["vendor_name"]
    docs = state["vendor_docs"]
    
    prompt = f"""You are a Compliance Documentation Reviewer.
    Review the following vendor description against standard industry frameworks (like ISO 27001).
    Context: This is a hypothetical review for a compliance dashboard.
    
    VENDOR: {vendor}
    DOCUMENTATION:
    {docs}
    
    INSTRUCTIONS:
    1. Compare the documentation against standard security best practices.
    2. List missing standard controls (e.g. Encryption types, Certifications).
    3. Provide a professional compliance summary.
    
    OUTPUT FORMAT (Strict Markdown):

    ### 📋 Compliance Review Summary
    
    | Category | Status |
    | :--- | :--- |
    | **Compliance Level** | **[Low / Medium / High]** |
    | **Vendor** | {vendor} |
    
    #### 🛡️ Executive Summary
    [Brief summary of compliance alignment.]

    #### 🔍 Missing Controls (Gaps)
    [List missing standard controls based on the text provided]
    *   ❌ **[Control Name]**: [Explanation]

    #### 💡 Recommendations
    [Professional steps to align with standards]
    1.  **[Step]**: [Details]
    """
    
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, 'content') else str(response)
    
    return {
        "risk_report": content,
        "final_status": "Completed"
    }

# Workflow
workflow = StateGraph(VendorState)
workflow.add_node("assess", assess_vendor_risk)
workflow.set_entry_point("assess")
workflow.add_edge("assess", END)

app = workflow.compile()

async def run_vendor_agent(name: str, docs: str):
    state = {
        "vendor_name": name,
        "vendor_docs": docs,
        "risk_report": "",
        "final_status": ""
    }
    result = await app.ainvoke(state)
    return {
        "status": result["final_status"],
        "report": result["risk_report"]
    }
