from typing import TypedDict, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage
from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
import os
import boto3
import requests
import logging

logger = logging.getLogger(__name__)

# --- SHARED CUSTOM LLM ---
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
            
            result = response.json()
            output_text = result.get("output", {}).get("message", {}).get("content", [])[0].get("text", "")
            return output_text
            
        except Exception as e:
            return f"Error executing Bedrock model: {str(e)}"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {"model_id": self.model_id}

# --- SHARED LLM FACTORY ---
global_llm_instance = None

def get_bedrock_client():
    try:
        region = os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        return boto3.client(service_name="bedrock-runtime", region_name=region)
    except Exception as e:
        logger.error(f"Failed to initialize Bedrock client: {e}")
        return None

def get_llm():
    global global_llm_instance
    if global_llm_instance:
        return global_llm_instance
        
    bearer_token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
    
    if bearer_token:
        # 1. Custom Bearer Token
        return CustomBedrockLLM(
            api_key=bearer_token,
            model_id=os.environ.get("BEDROCK_MODEL", "amazon.nova-pro-v1:0"),
            region=os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
        )
    else:
        # 2. Standard Boto3 (Fallback)
        from langchain_aws import ChatBedrockConverse
        client = get_bedrock_client()
        if not client:
             raise Exception("Failed to get bedrock client")
             
        model_id = os.getenv("BEDROCK_MODEL", os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0"))
        return ChatBedrockConverse(
            client=client,
            model=model_id,
            temperature=0.3,
            max_tokens=8000
        )

# Initialize once
try:
    global_llm_instance = get_llm()
except Exception:
    pass
