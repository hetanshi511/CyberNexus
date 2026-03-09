from typing import List, Dict, Any, Optional
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatResult, ChatGeneration
import os
import requests
import logging
import re

logger = logging.getLogger(__name__)


# -------------------- CUSTOM BEDROCK CHAT MODEL --------------------

class CustomBedrockLLM(BaseChatModel):
    api_key: str
    model_id: str
    region: str
    temperature: float = 0.3

    @property
    def _llm_type(self) -> str:
        return "custom_bedrock_chat"

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[Any] = None,
        **kwargs: Any,
    ) -> ChatResult:

        # Combine system + user messages properly
        combined_prompt = ""
        for m in messages:
            role = m.type.upper()
            combined_prompt += f"{role}: {m.content}\n\n"

        # 🔥 Strict JSON enforcement
        strict_prompt = (
            "You MUST return ONLY valid JSON. "
            "Do NOT include explanation, markdown, or extra text.\n\n"
            + combined_prompt
        )

        url = f"https://bedrock-runtime.{self.region}.amazonaws.com/model/{self.model_id}/invoke"

        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": strict_prompt}]
                }
            ],
            "inferenceConfig": {
                "temperature": self.temperature,
                "maxTokens": 4000
            }
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=60)
            response.raise_for_status()

            result = response.json()

            output_text = (
                result.get("output", {})
                .get("message", {})
                .get("content", [{}])[0]
                .get("text", "")
            )

            # Extract first JSON object safely
            match = re.search(r"\{.*\}", output_text, re.DOTALL)
            final_text = match.group(0) if match else output_text

        except Exception as e:
            logger.error(f"Bedrock call failed: {e}")
            final_text = (
                '{"alignment_status":"Error",'
                '"severity":"Low",'
                '"completion_percentage":0,'
                '"compliance_gaps":["Bedrock error"],'
                '"recommended_actions":["Retry"],'
                '"compliance_checklist":[]}'
            )

        message = AIMessage(content=final_text)
        generation = ChatGeneration(message=message)
        return ChatResult(generations=[generation])

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        return {"model_id": self.model_id}


# -------------------- GET LLM FUNCTION --------------------

def get_llm(temperature: float = 0.3):
    bearer_token = os.environ.get("AWS_BEARER_TOKEN_BEDROCK")

    if bearer_token:
        # 1️⃣ Custom Bearer Token Mode
        return CustomBedrockLLM(
            api_key=bearer_token,
            model_id=os.environ.get("BEDROCK_MODEL", "amazon.nova-pro-v1:0"),
            region=os.environ.get("AWS_DEFAULT_REGION", "us-east-1"),
            temperature=temperature
        )
    else:
        # 2️⃣ Standard AWS Bedrock via boto3
        from langchain_aws import ChatBedrockConverse
        from utils.aws import get_bedrock_client  # adjust if needed

        client = get_bedrock_client()
        if not client:
            raise Exception("Failed to get bedrock client")

        model_id = os.getenv(
            "BEDROCK_MODEL",
            os.getenv("BEDROCK_MODEL_ID", "amazon.nova-pro-v1:0")
        )

        return ChatBedrockConverse(
            client=client,
            model=model_id,
            temperature=temperature,
            max_tokens=4000
        )