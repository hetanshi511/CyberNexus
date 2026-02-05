from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import uvicorn
import logging
import time
from agent import run_agent

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("api")

app = FastAPI(title="Cyber Security Agent API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    logger.info(f"Incoming Request: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"Request Completed: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")
        return response
    except Exception as e:
        logger.error(f"Request Failed: {request.method} {request.url.path} - Error: {e}")
        raise

class AgentRequest(BaseModel):
    linkedin_access_token: str
    topic: Optional[str] = "Cyber Security news from Google, GPT, and Linux Foundation"

@app.get("/")
def read_root():
    return {"status": "Agent Backend Running", "documentation": "/docs"}

@app.post("/api/execute_agent")
async def execute_agent(request: AgentRequest):
    logger.info(f"Executing agent for topic: {request.topic}")
    try:
        result = await run_agent(
            linkedin_access_token=request.linkedin_access_token,
            topic=request.topic
        )
        return result
    except Exception as e:
        logger.error(f"Agent execution failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
