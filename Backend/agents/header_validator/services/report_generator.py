from langchain_core.prompts import PromptTemplate
from utils.llm import get_llm
import logging

logger = logging.getLogger("header_validator.report_generator")

async def generate_llm_report(site: str, score: int, missing_headers: list, security_issues: list, raw_headers: dict) -> str:
    """
    Sends the parsed issues to an LLM to generate human-readable security recommendations.
    Uses unified utils.llm module.
    """
    try:
        llm = get_llm()
        
        prompt_template = PromptTemplate(
            input_variables=["site", "score", "missing_headers", "security_issues", "headers"],
            template="""You are an expert web security auditor reviewing {site}.
The automated scanner awarded a security score of {score}/100 based on the following findings:

Missing Headers: {missing_headers}
Detailed Misconfigurations & Cookies: {security_issues}

Raw HTTP Headers Available:
{headers}

Please generate a professional security report strictly using the following 5 structured markdown sections to avoid redundancy:

## 1️⃣ Missing Security Headers
## 2️⃣ Misconfigured Headers
## 3️⃣ Cookie Security Issues
## 4️⃣ CSP Policy Weakness
## 5️⃣ Server Exposure

Focus solely on explaining the exact risks tied to the provided flaws and outline brief mitigations for each. 
If a section has no issues (e.g. Server Exposure is clear), just write "No issues detected." under it. 

CRITICAL INSTRUCTIONS:
- DO NOT wrap your response in JSON formatting.
- DO NOT output a JSON object or array.
- Output ONLY raw, neatly formatted Markdown text.
- Do not include any introductory sentences.
"""
        )
        
        chain = prompt_template | llm
        
        response = await chain.ainvoke({
            "site": site,
            "score": score,
            "missing_headers": str([h['name'] for h in missing_headers]),
            "security_issues": str(security_issues),
            "headers": str(raw_headers)
        })
        
        return response.content if hasattr(response, 'content') else str(response)
        
    except Exception as e:
        logger.error(f"Failed to generate LLM report: {e}")
        return f"Automated LLM Analysis failed to generate a report. Cause: {e}"
