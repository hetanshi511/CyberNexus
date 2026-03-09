import json
import traceback
from typing import TypedDict, List
from langgraph.graph import StateGraph, END

from utils.llm import get_llm
from utils.attachment import extract_pdf_text

class ResumeReviewerState(TypedDict):
    job_description: str
    raw_candidates: List[dict] # [{"name": str, "content_bytes": bytes, "mime_type": str}]
    parsed_candidates: List[dict] # [{"name": str, "text": str}]
    formatted_candidates: List[dict] # [{"name": str, "formatted_text": str}]
    evaluated_candidates: List[dict] # [{"name": str, "email": str, "score": int, "summary": str}]
    final_report: dict
    final_status: str

def get_candidate_details(state: ResumeReviewerState):
    print("--- RESUME REVIEWER: GET CANDIDATE DETAILS ---")
    raw_candidates = state.get("raw_candidates", [])
    parsed_candidates = []
    
    for cand in raw_candidates:
        name = cand.get("name", "Unknown")
        content_bytes = cand.get("content_bytes", b"")
        mime_type = cand.get("mime_type", "").lower()
        
        text = ""
        try:
            if "pdf" in mime_type or name.lower().endswith(".pdf"):
                text = extract_pdf_text(content_bytes)
            else:
                text = content_bytes.decode("utf-8", errors="ignore")
        except Exception as e:
            print(f"Error parsing resume {name}: {e}")
            
        parsed_candidates.append({
            "name": name,
            "text": text
        })
        
    return {"parsed_candidates": parsed_candidates}

def json_to_string(state: ResumeReviewerState):
    print("--- RESUME REVIEWER: JSON TO STRING ---")
    parsed_candidates = state.get("parsed_candidates", [])
    formatted_candidates = []
    
    for cand in parsed_candidates:
        name = cand["name"]
        text = cand["text"]
        # Convert structured/parsed details to string format.
        # Since we just extracted text, we just package it neatly.
        formatted_text = f"Candidate Name: {name}\n\nResume Content:\n{text}"
        formatted_candidates.append({
            "name": name,
            "formatted_text": formatted_text
        })
        
    return {"formatted_candidates": formatted_candidates}

def assign_scores_for_candidate(state: ResumeReviewerState):
    print("--- RESUME REVIEWER: ASSIGN SCORES ---")
    job_description = state.get("job_description", "")
    formatted_candidates = state.get("formatted_candidates", [])
    evaluated_candidates = []
    llm = get_llm()
    
    for cand in formatted_candidates:
        name = cand["name"]
        content = cand["formatted_text"]
        
        prompt = f"""You are an expert AI Resume Reviewer.
Evaluate the following candidate resume against the provided job description.
Assign a score from 0 to 10 strictly based on parsed data (no assumptions).
Extract the candidate's Email ID from the resume content. If not found, output "N/A".
Provide a 2-line summary of key strengths and weaknesses relative to the job description.

Job Description:
{job_description}

Candidate Resume:
{content}

You MUST output your response in STRICT JSON format matching this schema exactly. Do not include markdown formatting outside the JSON object:
{{
    "email": "candidate@example.com",
    "score": 8,
    "summary": "Strengths: ... Weaknesses: ..."
}}
"""
        try:
            response = llm.invoke(prompt)
            output = response.content if hasattr(response, 'content') else str(response)
            
            # Clean up potential markdown formatting
            output_cleaned = output.strip()
            if output_cleaned.startswith("```json"):
                output_cleaned = output_cleaned.replace("```json", "", 1)
            if output_cleaned.startswith("```"):
                output_cleaned = output_cleaned.replace("```", "", 1)
            if output_cleaned.endswith("```"):
                output_cleaned = output_cleaned[::-1].replace("```", "", 1)[::-1]
            output_cleaned = output_cleaned.strip()

            parsed_json = json.loads(output_cleaned)
            score = parsed_json.get("score", 0)
            if isinstance(score, str):
                try:
                    score = int(score)
                except ValueError:
                    score = 0
                    
            evaluated_candidates.append({
                "name": name,
                "email": parsed_json.get("email", "N/A"),
                "score": score,
                "summary": parsed_json.get("summary", "No summary provided.")
            })
            print(f"Evaluated {name} - Score: {score}")
        except Exception as e:
            print(f"Error evaluating candidate {name}: {e}")
            traceback.print_exc()
            evaluated_candidates.append({
                "name": name,
                "email": "Error",
                "score": 0,
                "summary": f"Failed to evaluate candidate due to an error: {str(e)}"
            })
            
    return {"evaluated_candidates": evaluated_candidates}

def report_node(state: ResumeReviewerState):
    print("--- RESUME REVIEWER: REPORT ---")
    evaluated_candidates = state.get("evaluated_candidates", [])
    
    # Sort candidates by score descending
    evaluated_candidates = sorted(evaluated_candidates, key=lambda x: x["score"], reverse=True)
    
    # Shortlist those with score >= 8
    shortlisted = [c for c in evaluated_candidates if c["score"] >= 8]
    
    final_report = {
        "all_candidates": evaluated_candidates,
        "shortlisted_candidates": shortlisted,
        "total_evaluated": len(evaluated_candidates),
        "total_shortlisted": len(shortlisted)
    }
    
    return {"final_report": final_report, "final_status": "Success"}

# Workflow
workflow = StateGraph(ResumeReviewerState)
workflow.add_node("get_candidate_details", get_candidate_details)
workflow.add_node("json_to_string", json_to_string)
workflow.add_node("assign_scores_for_candidate", assign_scores_for_candidate)
workflow.add_node("report_node", report_node)

workflow.set_entry_point("get_candidate_details")
workflow.add_edge("get_candidate_details", "json_to_string")
workflow.add_edge("json_to_string", "assign_scores_for_candidate")
workflow.add_edge("assign_scores_for_candidate", "report_node")
workflow.add_edge("report_node", END)

app = workflow.compile()

async def run_resume_reviewer_agent(job_description: str, raw_candidates: List[dict]):
    state = {
        "job_description": job_description,
        "raw_candidates": raw_candidates,
        "parsed_candidates": [],
        "formatted_candidates": [],
        "evaluated_candidates": [],
        "final_report": {},
        "final_status": ""
    }
    
    try:
        result = await app.ainvoke(state)
        return {
            "status": result["final_status"],
            "report": result["final_report"]
        }
    except Exception as e:
        print(f"Resume Reviewer Agent failed: {e}")
        traceback.print_exc()
        return {
            "status": "Failed",
            "report": f"Agent encountered an error: {str(e)}"
        }
