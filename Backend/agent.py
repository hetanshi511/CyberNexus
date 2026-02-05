import os
import json
import logging
import boto3
import requests 
from typing import TypedDict, Annotated, List, Dict, Optional, Any
from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_aws import ChatBedrockConverse
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.language_models.llms import LLM 
from langchain_core.callbacks.manager import CallbackManagerForLLMRun 

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- State Definition (MOVED TO TOP) ---
class AgentState(TypedDict):
    messages: List[BaseMessage]
    linkedin_access_token: str
    news_results: str
    newsletter_draft: str
    final_status: str

# --- Custom LLM for Bedrock Bearer Token Support ---
class CustomBedrockLLM(LLM):
    api_key: str
    model_id: str
    region: str
    
    @property
    def _llm_type(self) -> str:
        return "custom_bedrock"

    def _call(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        url = f"https://bedrock-runtime.{self.region}.amazonaws.com/model/{self.model_id}/invoke"
        
        # Amazon Nova / Converse API Payload Structure
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ],
            "inferenceConfig": {
                "temperature": 0.5
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            # Parse Nova response
            result = response.json()
            # Nova response path: output -> message -> content -> [0] -> text
            output_text = result.get("output", {}).get("message", {}).get("content", [])[0].get("text", "")
            return output_text
            
        except Exception as e:
            return f"Error executing Bedrock model with Token: {str(e)}"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {"model_id": self.model_id}

# --- INITIALIZE BEDROCK WITH ERROR HANDLING ---
def get_bedrock_client():
    """Initialize Bedrock client with proper error handling."""
    try:
        region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        client = boto3.client(
            service_name="bedrock-runtime",
            region_name=region
        )
        logger.info(f"Bedrock client initialized for region: {region}")
        return client

    except Exception as e:
        logger.error(f"Failed to initialize Bedrock client: {e}")
        raise

def get_llm():
    """Initialize LLM with proper error handling."""
    
    # 1. Check for Bearer Token (User's .env)
    bearer_token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
    if bearer_token:
        logger.info("Using Custom Bedrock Bearer Token logic.")
        try:
            return CustomBedrockLLM(
                api_key=bearer_token,
                model_id=os.environ.get("BEDROCK_MODEL", "amazon.nova-pro-v1:0"),
                region=os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
            )
        except Exception as e:
            logger.error(f"Failed to initialize Custom Token LLM: {e}")
            raise

    # 2. Fallback to Standard Boto3 (User's snippet)
    try:
        logger.info("Using Standard Boto3 credentials.")
        client = get_bedrock_client()
        # Fallback to a default if BEDROCK_MODEL is not set, or ensure .env has it. 
        # User snippet used BEDROCK_MODEL. My .env used BEDROCK_MODEL_ID. 
        # I will use os.getenv("BEDROCK_MODEL", os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")) to be safe.
        model_id = os.getenv("BEDROCK_MODEL", os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0"))
        
        llm = ChatBedrockConverse(
            client=client,
            model=model_id,
            temperature=0.3,
            max_tokens=8000  
        )
        logger.info("LLM initialized successfully")
        return llm

    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}")
        raise

# Initialize global LLM instance to fail fast if config is wrong
try:
    llm_instance = get_llm()
except Exception:
    llm_instance = None # Handle gracefully in nodes


# --- NODE FUNCTIONS ---
# These MUST be defined BEFORE the graph construction at the bottom.

def search_news(state: AgentState):
    print("--- SEARCHING NEWS ---")
    
    # Validation: Ensure Key is present
    if not os.environ.get("TAVILY_API_KEY"):
        logger.error("TAVILY_API_KEY not found in environment")
        return {
            "news_results": "Error: TAVILY_API_KEY is missing from environment variables. Please check your .env file.",
            "messages": [AIMessage(content="Error: TAVILY_API_KEY is missing.")]
        }

    messages = state.get("messages", [])
    query = messages[-1].content if messages else ""
    
    if not query or len(messages) <= 1: 
        query = "Recent cyber security news Google GPT Linux Foundation"
    
    # Initialize Tavily (automatically reads TAVILY_API_KEY from env)
    tavily = TavilySearchResults(max_results=5)
    try:
        results = tavily.invoke(query)
        formatted_results = json.dumps(results, indent=2)
    except Exception as e:
        logger.error(f"Tavily Search failed: {e}")
        formatted_results = f"Error during search: {str(e)}"
        
    return {
        "news_results": formatted_results,
        "messages": [AIMessage(content=f"Found the following news:\n{formatted_results}")]
    }

def generate_newsletter(state: AgentState):
    print("--- GENERATING NEWSLETTER ---")
    # Use the globally initialized LLM or re-initialize
    local_llm = llm_instance if llm_instance else get_llm()
    
    news = state["news_results"]
    
    prompt = f"""You are a professional Cyber Security Analyst. 
    Based on the following news search results, create a concise, 
    engaging LinkedIn newsletter post. 
    
    Focus on the top 5 most important updates. 
    Include a catchy title.
    Use emojis where appropriate.
    Keep it professional but engaging.
    
    News Data:
    {news}
    
    Output strictly the newsletter content."""
    
    response = local_llm.invoke(prompt)
    
    # Handle response type (String for CustomLLM, Message for ChatBedrock)
    content = response.content if hasattr(response, 'content') else str(response)
    
    return {
        "newsletter_draft": content,
        "messages": [AIMessage(content=content)]
    }

def post_to_linkedin(state: AgentState):
    print("--- POSTING TO LINKEDIN (OFFICIAL API) ---")
    access_token = state["linkedin_access_token"]
    content = state["newsletter_draft"]
    
    if not access_token:
        # Access token input is mandatory in UI, but safe check here.
        logger.warning("No access token provided to post_to_linkedin node.")
        return {"final_status": "Skipped LinkedIn post (Access Token missing). Generated content provided."}
    
    try:
        # 1. Get User URN (Person ID)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0"
        }
        
        logger.info("Fetching LinkedIn Profile URN...")
        profile_url = "https://api.linkedin.com/v2/userinfo"
        profile_response = requests.get(profile_url, headers=headers)
        
        if profile_response.status_code == 200:
             urn = f"urn:li:person:{profile_response.json()['sub']}"
        else:
             # Fallback to 'me' endpoint
             logger.info("v2/userinfo failed, trying v2/me...")
             me_url = "https://api.linkedin.com/v2/me"
             me_response = requests.get(me_url, headers=headers)
             me_response.raise_for_status()
             urn = f"urn:li:person:{me_response.json()['id']}"
        
        logger.info(f"Resolved LinkedIn User URN: {urn}")
        
        # 2. Create UGC Post (Official Endpoint)
        post_url = "https://api.linkedin.com/v2/ugcPosts"
        
        post_data = {
            "author": urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {
                        "text": content
                    },
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
            }
        }
        
        logger.info("Sending Post Request to LinkedIn...")
        response = requests.post(post_url, headers=headers, json=post_data)
        
        if response.status_code in [200, 201]:
            logger.info("Successfully posted to LinkedIn via Official API")
            status = "Newsletter generated and POSTED to LinkedIn successfully! (Official API)"
        else:
            logger.error(f"LinkedIn API Error: {response.text}")
            status = f"Post Failed. LinkedIn API Status: {response.status_code} - {response.text}"

    except Exception as e:
        logger.error(f"Failed to post to LinkedIn: {e}", exc_info=True)
        status = f"Newsletter generated but failed to post to LinkedIn. Error: {str(e)}"
    
    return {"final_status": status}


# --- GRAPH CONSTRUCTION ---
# This MUST be defined AFTER the function definitions above.
workflow = StateGraph(AgentState)

workflow.add_node("search", search_news)
workflow.add_node("generate", generate_newsletter)
workflow.add_node("publish", post_to_linkedin)

workflow.set_entry_point("search")
workflow.add_edge("search", "generate")
workflow.add_edge("generate", "publish")
workflow.add_edge("publish", END)

app = workflow.compile()

async def run_agent(linkedin_access_token: str, topic: str):
    initial_state = {
        "messages": [HumanMessage(content=topic)],
        "linkedin_access_token": linkedin_access_token,
        "news_results": "",
        "newsletter_draft": "",
        "final_status": ""
    }
    
    final_state = await app.ainvoke(initial_state)
    return {
        "status": final_state["final_status"],
        "newsletter": final_state["newsletter_draft"]
    }
