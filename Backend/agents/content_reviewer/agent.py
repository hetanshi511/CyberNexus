from typing import TypedDict, List
from langgraph.graph import StateGraph, END
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
import traceback
import json
import re

from utils.llm import get_llm

class ContentReviewerState(TypedDict):
    website_url: str
    max_pages: int
    max_depth: int
    send_email_to: str
    visited_urls: List[str]
    urls_to_visit: List[dict]  # list of dicts: {"url": str, "depth": int}
    crawled_content: List[dict] # list of dicts: {"url": str, "content": str, "analysis": dict}
    final_report: dict
    final_status: str

def fetch_and_extract_text(url: str):
    """Fetches HTML and extracts visible text."""
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script, style, and hidden elements to keep only visible text
        for tag in soup(['script', 'style', 'noscript', 'meta', 'head', 'title', 'header', 'footer']):
            tag.decompose()
        
        text = soup.get_text(separator=' ', strip=True)
        
        # Extract internal links
        links = []
        base_url = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Resolve relative URLs
            full_url = urljoin(base_url, href)
            # Filter internal links
            if full_url.startswith(base_url):
                # Optionally filter out login/admin/logout
                lower_url = full_url.lower()
                if not any(stop_word in lower_url for stop_word in ['/login', '/admin', '/logout', '/wp-admin']):
                    # Remove fragments/anchors
                    full_url = full_url.split('#')[0]
                    links.append(full_url)
                    
        return text, list(set(links))
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None, []

def crawler_node(state: ContentReviewerState):
    """Crawls URLs up to a limit or depth limit."""
    print("--- CONTENT REVIEWER AGENT: CRAWLER ---")
    
    urls_to_visit = list(state.get("urls_to_visit", []))
    visited_urls = list(state.get("visited_urls", []))
    crawled_content = list(state.get("crawled_content", []))
    
    MAX_PAGES = state.get("max_pages", 5)
    MAX_DEPTH = state.get("max_depth", 2)
    
    # Initialize from start if empty
    if not urls_to_visit and not visited_urls:
        urls_to_visit.append({"url": state["website_url"], "depth": 0})
        
    while urls_to_visit and len(visited_urls) < MAX_PAGES:
        current = urls_to_visit.pop(0)
        url = current["url"]
        depth = current["depth"]
        
        if url in visited_urls:
            continue
            
        print(f"Crawling (Depth {depth}): {url}")
        visited_urls.append(url)
        text, links = fetch_and_extract_text(url)
        
        if text:
            # truncate text to avoid astronomical contexts
            crawled_content.append({"url": url, "content": text[:8000]})
            
        if depth < MAX_DEPTH:
            for link in links:
                if link not in visited_urls and not any(u["url"] == link for u in urls_to_visit):
                    urls_to_visit.append({"url": link, "depth": depth + 1})
                    
    return {
        "visited_urls": visited_urls,
        "urls_to_visit": urls_to_visit,
        "crawled_content": crawled_content
    }

def analyze_node(state: ContentReviewerState):
    """Analyzes the content using GenAI for typos, grammar, etc."""
    print("--- CONTENT REVIEWER AGENT: ANALYZE ---")
    llm = get_llm()
    crawled_content = list(state.get("crawled_content", []))
    
    for page in crawled_content:
        if "analysis" in page:
            continue # already analyzed
            
        prompt = f"""You are an expert Content Reviewer and Copywriter.
        A user has submitted website content to be analyzed for typos, spelling mistakes, grammatical issues, and punctuation errors.
        
        Website URL: {page['url']}
        Content:
        {page['content']}
        
        INSTRUCTIONS:
        1. Review the content for any textual errors (grammar, punctuation, typos, spelling).
        2. Identify each error. Provide the original text, the suggested correction, and a brief explanation.
        3. You MUST output your response in STRICT JSON format matching this schema exactly. Do not include markdown formatting like ```json or anything outside the JSON object:
        
        {{
            "url": "{page['url']}",
            "error_count": 0,
            "errors": [
                {{
                    "type": "typo|grammar|punctuation|spelling",
                    "original_text": "...",
                    "suggested_correction": "...",
                    "explanation": "..."
                }}
            ]
        }}
        
        4. If absolutely NO errors are found, return the JSON structure with "error_count": 0 and an empty list for "errors".
        """
        
        try:
            response = llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Clean up potential markdown formatting around JSON
            content_cleaned = content.strip()
            if content_cleaned.startswith("```json"):
                content_cleaned = content_cleaned.replace("```json", "", 1)
            if content_cleaned.startswith("```"):
                content_cleaned = content_cleaned.replace("```", "", 1)
            if content_cleaned.endswith("```"):
                content_cleaned = content_cleaned[::-1].replace("```", "", 1)[::-1]
            content_cleaned = content_cleaned.strip()

            parsed_json = json.loads(content_cleaned)
            page["analysis"] = parsed_json
            print(f"Analysis completed for {page['url']} ({parsed_json.get('error_count', 0)} errors)")
        except Exception as e:
            print(f"Error during LLM analysis or JSON parsing of {page['url']}: {e}")
            print(f"Raw Output: {content if 'content' in locals() else 'None'}")
            page["analysis"] = {
                "url": page['url'],
                "error_count": 1,
                "errors": [{
                    "type": "system",
                    "original_text": "N/A",
                    "suggested_correction": "N/A",
                    "explanation": "Failed to analyze this page due to an LLM or parsing error."
                }]
            }
            
    return {"crawled_content": crawled_content}

def report_node(state: ContentReviewerState):
    """Aggregates all analysis into a final JSON report."""
    print("--- CONTENT REVIEWER AGENT: REPORT ---")
    crawled_content = list(state.get("crawled_content", []))
    
    if not crawled_content:
        return {
            "final_report": {
                "summary": {
                    "total_pages": 0,
                    "total_errors": 0,
                    "status": "Failed"
                },
                "pages": [],
                "message": "Could not fetch or extract content from the provided URL."
            },
            "final_status": "Failed"
        }
        
    total_errors = 0
    pages_report = []
    
    for page in crawled_content:
        analysis = page.get("analysis", {})
        count = analysis.get("error_count", 0)
        total_errors += count
        pages_report.append(analysis)
        
    final_report = {
        "summary": {
            "total_pages": len(pages_report),
            "total_errors": total_errors,
            "status": "Success" if total_errors == 0 else "Issues Found",
            "message": f"Crawled {len(pages_report)} pages." if len(pages_report) < state.get("max_pages", 5) else ""
        },
        "pages": pages_report
    }
    
    return {
        "final_report": final_report,
        "final_status": "Completed"
    }

# Workflow
workflow = StateGraph(ContentReviewerState)
workflow.add_node("crawler", crawler_node)
workflow.add_node("analyze", analyze_node)
workflow.add_node("report", report_node)

workflow.set_entry_point("crawler")
workflow.add_edge("crawler", "analyze")
workflow.add_edge("analyze", "report")
workflow.add_edge("report", END)

app = workflow.compile()

async def run_content_reviewer_agent(website_url: str, max_pages: int = 5, max_depth: int = 2, send_email_to: str = None):
    state = {
        "website_url": website_url,
        "max_pages": max_pages,
        "max_depth": max_depth,
        "send_email_to": send_email_to or "",
        "visited_urls": [],
        "urls_to_visit": [],
        "crawled_content": [],
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
        print(f"Content Reviewer Agent failed: {e}")
        traceback.print_exc()
        return {
            "status": "Failed",
            "report": f"Agent encountered an error: {str(e)}"
        }
