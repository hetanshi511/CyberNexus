from typing import TypedDict, List
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langgraph.graph import StateGraph, END
from langchain_community.tools.tavily_search import TavilySearchResults
import json
import os
import requests
import logging
from utils.llm import get_llm

logger = logging.getLogger(__name__)

class AgentState(TypedDict):
    messages: List[BaseMessage]
    linkedin_access_token: str
    news_results: str
    newsletter_draft: str
    final_status: str

def search_news(state: AgentState):
    print("--- SEARCHING NEWS ---")
    if not os.environ.get("TAVILY_API_KEY"):
        return {
            "news_results": "Error: TAVILY_API_KEY missing.",
            "messages": [AIMessage(content="Error: TAVILY_API_KEY missing.")]
        }

    messages = state.get("messages", [])
    query = messages[-1].content if messages else "Cyber security news"
    
    tavily = TavilySearchResults(max_results=5)
    try:
        results = tavily.invoke(query)
        formatted_results = json.dumps(results, indent=2)
    except Exception as e:
        formatted_results = f"Error during search: {str(e)}"
        
    return {
        "news_results": formatted_results,
        "messages": [AIMessage(content=f"Found news:\n{formatted_results}")]
    }

def generate_newsletter(state: AgentState):
    print("--- GENERATING NEWSLETTER ---")
    llm = get_llm()
    news = state["news_results"]
    
    prompt = f"""You are a professional Cyber Security Analyst. 
    Based on these news results, create an engaging and formal LinkedIn newsletter post.
    
    IMPORTANT INSTRUCTIONS:
    1. The output MUST NOT be in JSON format. It must be formatted as a formal, professional plain-text post.
    2. The entire output MUST be under 2500 characters.
    3. Focus on the top 3-4 most critical updates only.
    4. Provide an engaging title and introduction.
    5. For each update, provide a concise description using bullet points AND include the original source URL link so readers can access the full article.
    6. Include relevant professional hashtags at the end.
    
    News Data:
    {news}
    
    Output strictly the newsletter content text."""
    
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, 'content') else str(response)
    
    return {
        "newsletter_draft": content,
        "messages": [AIMessage(content=content)]
    }

def post_to_linkedin(state: AgentState):
    print("--- POSTING TO LINKEDIN ---")
    access_token = state["linkedin_access_token"]
    content = state["newsletter_draft"]
    
    if not access_token:
        return {"final_status": "Skipped LinkedIn post (Token missing)."}
    
    try:
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        # Get URN
        profile_url = "https://api.linkedin.com/v2/userinfo"
        resp = requests.get(profile_url, headers=headers)
        if resp.status_code == 200:
             urn = f"urn:li:person:{resp.json()['sub']}"
        else:
             me_url = "https://api.linkedin.com/v2/me"
             me_resp = requests.get(me_url, headers=headers)
             me_resp.raise_for_status()
             urn = f"urn:li:person:{me_resp.json()['id']}"
        
        # Post
        post_url = "https://api.linkedin.com/v2/ugcPosts"
        post_data = {
            "author": urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": content},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }
        
        post_resp = requests.post(post_url, headers=headers, json=post_data)
        if post_resp.status_code in [200, 201]:
            status = "Success: Posted to LinkedIn!"
        else:
            status = f"Failed: {post_resp.text}"

    except Exception as e:
        status = f"Error: {str(e)}"
    
    return {"final_status": status}

# Workflow
workflow = StateGraph(AgentState)
workflow.add_node("search", search_news)
workflow.add_node("generate", generate_newsletter)
workflow.add_node("publish", post_to_linkedin)
workflow.set_entry_point("search")
workflow.add_edge("search", "generate")
workflow.add_edge("generate", "publish")
workflow.add_edge("publish", END)

app = workflow.compile()

async def run_newsletter_agent(token: str, topic: str):
    state = {
        "messages": [HumanMessage(content=topic)],
        "linkedin_access_token": token,
        "news_results": "",
        "newsletter_draft": "",
        "final_status": ""
    }
    result = await app.ainvoke(state)
    return {
        "status": result["final_status"],
        "newsletter": result["newsletter_draft"]
    }
