#!/usr/bin/env python3
"""
n8n Agent API - Main FastAPI Application

A FastAPI application that provides an intelligent agent interface for n8n workflow automation.
Uses LangGraph for conversation processing and OpenRouter for LLM inference.
"""

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional

import httpx
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from langgraph_agent import create_workflow_agent
from llm_client import LLMClient
from n8n_client import N8nClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("agent_api.log")
    ]
)
logger = logging.getLogger(__name__)

# Global clients - initialized on startup
n8n_client: Optional[N8nClient] = None
llm_client: Optional[LLMClient] = None
template_service_client: Optional[httpx.AsyncClient] = None
agent_graph = None

# Configuration
TEMPLATE_SERVICE_URL = os.getenv("TEMPLATES_SERVICE_URL", "http://localhost:8000")
REQUEST_TIMEOUT = 30.0


# Pydantic Models for Request/Response Validation

class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., min_length=1, max_length=2000, description="User message")
    activate: bool = Field(default=False, description="Whether to activate/import the workflow")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Create a workflow that sends daily email reports",
                "activate": False
            }
        }


class ChatResponse(BaseModel):
    """Response model for chat endpoint"""
    workflow_id: Optional[str] = Field(None, description="Generated workflow ID")
    editor_url: Optional[str] = Field(None, description="n8n editor URL")
    active: bool = Field(False, description="Whether workflow was activated")
    message: str = Field(..., description="Agent response message")
    request_id: str = Field(..., description="Unique request identifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "workflow_id": "wf_123456",
                "editor_url": "http://localhost:5678/workflow/123456",
                "active": False,
                "message": "I've found a suitable email automation template. Would you like me to import and customize it?",
                "request_id": "req_abc123"
            }
        }


class DryRunRequest(BaseModel):
    """Request model for dry run endpoint"""
    message: str = Field(..., min_length=1, max_length=2000, description="User message describing desired workflow")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "I need a workflow to process customer feedback forms"
            }
        }


class TemplateMatch(BaseModel):
    """Template match result model"""
    id: str = Field(..., description="Template ID")
    name: str = Field(..., description="Template name")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score (0-1)")
    description: str = Field(..., description="Template description")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "template_123",
                "name": "Customer Feedback Processor",
                "score": 0.85,
                "description": "Processes customer feedback forms from various sources"
            }
        }


class DryRunResponse(BaseModel):
    """Response model for dry run endpoint"""
    templates: List[TemplateMatch] = Field(..., description="List of matching templates")
    request_id: str = Field(..., description="Unique request identifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "templates": [
                    {
                        "id": "template_123",
                        "name": "Customer Feedback Processor",
                        "score": 0.85,
                        "description": "Processes customer feedback forms from various sources"
                    }
                ],
                "request_id": "req_xyz789"
            }
        }


class ServiceStatus(BaseModel):
    """Service status model"""
    name: str = Field(..., description="Service name")
    status: str = Field(..., description="Service status")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if unhealthy")


class HealthResponse(BaseModel):
    """Response model for health endpoint"""
    status: str = Field(..., description="Overall health status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Health check timestamp")
    services: List[ServiceStatus] = Field(..., description="Individual service statuses")
    request_id: str = Field(..., description="Unique request identifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2024-01-15T10:30:00Z",
                "services": [
                    {"name": "n8n", "status": "healthy", "response_time_ms": 45.2},
                    {"name": "template_service", "status": "healthy", "response_time_ms": 23.1},
                    {"name": "openrouter", "status": "healthy", "response_time_ms": 156.3}
                ],
                "request_id": "req_health_123"
            }
        }


class APIInfo(BaseModel):
    """API information model"""
    name: str = Field(..., description="API name")
    version: str = Field(..., description="API version")
    description: str = Field(..., description="API description")
    endpoints: List[str] = Field(..., description="Available endpoints")
    docs_url: str = Field(..., description="Documentation URL")


# OpenAI-compatible API Models

class OpenAIMessage(BaseModel):
    """OpenAI chat message format"""
    role: str = Field(..., description="Message role: system, user, or assistant")
    content: str = Field(..., description="Message content")

class OpenAIChatRequest(BaseModel):
    """OpenAI chat completions request format"""
    model: str = Field(default="n8n-workflow-assistant", description="Model name")
    messages: List[OpenAIMessage] = Field(..., description="Chat messages")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperature for randomness")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens in response")
    stream: bool = Field(default=False, description="Stream response")
    
    class Config:
        json_schema_extra = {
            "example": {
                "model": "n8n-workflow-assistant",
                "messages": [
                    {"role": "user", "content": "Create a workflow that sends Slack notifications when new emails arrive"}
                ],
                "temperature": 0.7,
                "stream": False
            }
        }

class OpenAIChoice(BaseModel):
    """OpenAI choice format"""
    index: int = Field(..., description="Choice index")
    message: OpenAIMessage = Field(..., description="Response message")
    finish_reason: str = Field(..., description="Reason for completion")

class OpenAIUsage(BaseModel):
    """OpenAI usage statistics"""
    prompt_tokens: int = Field(..., description="Tokens in prompt")
    completion_tokens: int = Field(..., description="Tokens in completion")
    total_tokens: int = Field(..., description="Total tokens used")

class OpenAIChatResponse(BaseModel):
    """OpenAI chat completions response format"""
    id: str = Field(..., description="Response ID")
    object: str = Field(default="chat.completion", description="Object type")
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Model used")
    choices: List[OpenAIChoice] = Field(..., description="Response choices")
    usage: OpenAIUsage = Field(..., description="Token usage")

class OpenAIModel(BaseModel):
    """OpenAI model format"""
    id: str = Field(..., description="Model ID")
    object: str = Field(default="model", description="Object type")
    created: int = Field(..., description="Creation timestamp")
    owned_by: str = Field(default="n8n-agent-api", description="Owner")

class OpenAIModelsResponse(BaseModel):
    """OpenAI models list response"""
    object: str = Field(default="list", description="Object type")
    data: List[OpenAIModel] = Field(..., description="Available models")


# Template Service Client

class TemplateServiceClient:
    """Client for interacting with the template service"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        # Don't create a persistent client - create fresh ones for each request
    
    async def search_templates(self, query: str) -> List[TemplateMatch]:
        """Search for templates matching the query"""
        try:
            # Configure httpx to prefer IPv4 and handle host.docker.internal properly
            limits = httpx.Limits(max_keepalive_connections=0, max_connections=5)
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT, 
                limits=limits,
                verify=False  # Disable SSL verification for local connections
            ) as client:
                response = await client.get(
                    f"{self.base_url}/search",
                    params={"q": query}
                )
                response.raise_for_status()
                data = response.json()
                
                # Take only the first 5 results
                results = data[:5] if isinstance(data, list) else []
                
                return [
                    TemplateMatch(
                        id=item["id"],
                        name=item["name"],
                        score=item.get("score", 0.0),
                        description=item.get("description", item.get("name", ""))
                    )
                    for item in results
                ]
        except Exception as e:
            logger.error(f"Template search failed: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"Template service unavailable: {str(e)}"
            )
    
    async def fetch_template(self, template_id: str) -> Dict:
        """Fetch a specific template by ID"""
        try:
            limits = httpx.Limits(max_keepalive_connections=0, max_connections=5)
            async with httpx.AsyncClient(
                timeout=REQUEST_TIMEOUT, 
                limits=limits,
                verify=False
            ) as client:
                # The template_id should be the filename (without .json extension)
                response = await client.get(f"{self.base_url}/api/workflows/{template_id}")
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Template fetch failed for {template_id}: {str(e)}")
            raise HTTPException(
                status_code=503,
                detail=f"Could not fetch template: {str(e)}"
            )
    
    async def health_check(self) -> bool:
        """Check if template service is healthy"""
        try:
            limits = httpx.Limits(max_keepalive_connections=0, max_connections=5)
            async with httpx.AsyncClient(
                timeout=5.0, 
                limits=limits,
                verify=False
            ) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False
    
    async def close(self):
        """Close the HTTP client - no longer needed since we use context managers"""
        pass


# Application Lifecycle Management

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    global n8n_client, llm_client, template_service_client, agent_graph
    
    logger.info("🚀 Starting n8n Agent API...")
    
    # Initialize clients
    try:
        logger.info("Initializing clients...")
        
        # Initialize n8n client
        n8n_client = N8nClient()
        
        # Initialize LLM client
        llm_client = LLMClient()
        
        # Initialize template service client
        template_service_client = TemplateServiceClient(TEMPLATE_SERVICE_URL)
        
        # Create agent
        agent_graph = create_workflow_agent(llm_client, n8n_client)
        
        logger.info("✅ All clients initialized successfully")
        
        # Verify service connectivity
        await verify_services_startup()
        
        logger.info("🎯 n8n Agent API is ready!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}")
        raise
    
    yield
    
    # Cleanup
    logger.info("🧹 Shutting down n8n Agent API...")
    try:
        if template_service_client:
            await template_service_client.close()
        logger.info("✅ Cleanup completed")
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")


async def verify_services_startup():
    """Verify all services are available on startup"""
    services_to_check = [
        ("n8n", check_n8n_health),
        ("template_service", check_template_service_health),
        ("openrouter", check_openrouter_health)
    ]
    
    for service_name, health_check in services_to_check:
        try:
            is_healthy = await health_check()
            if is_healthy:
                logger.info(f"✅ {service_name} is healthy")
            else:
                logger.warning(f"⚠️  {service_name} is not responding")
        except Exception as e:
            logger.warning(f"⚠️  Failed to check {service_name}: {str(e)}")


# FastAPI Application Setup

app = FastAPI(
    title="n8n Agent API",
    version="1.0.0",
    description="Intelligent agent interface for n8n workflow automation using LangGraph and OpenRouter",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# Middleware for request tracking and logging

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and add request ID"""
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    
    start_time = datetime.utcnow()
    logger.info(f"🌐 [{request_id}] {request.method} {request.url.path}")
    
    response = await call_next(request)
    
    duration = (datetime.utcnow() - start_time).total_seconds() * 1000
    logger.info(f"✅ [{request_id}] Response: {response.status_code} ({duration:.1f}ms)")
    
    return response


# Static Files Configuration - Removed (using Open WebUI instead)


# Health Check Functions

async def check_n8n_health() -> tuple[bool, Optional[float], Optional[str]]:
    """Check n8n service health"""
    try:
        if not n8n_client:
            return False, None, "n8n client not initialized"
        
        start_time = datetime.utcnow()
        workflows = await n8n_client.list_workflows()
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return True, duration, None
    except Exception as e:
        return False, None, str(e)


async def check_template_service_health() -> tuple[bool, Optional[float], Optional[str]]:
    """Check template service health"""
    try:
        if not template_service_client:
            return False, None, "Template service client not initialized"
        
        start_time = datetime.utcnow()
        is_healthy = await template_service_client.health_check()
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        if is_healthy:
            return True, duration, None
        else:
            return False, duration, "Service not responding"
    except Exception as e:
        return False, None, str(e)


async def check_openrouter_health() -> tuple[bool, Optional[float], Optional[str]]:
    """Check OpenRouter API health"""
    try:
        if not llm_client:
            return False, None, "LLM client not initialized"
        
        start_time = datetime.utcnow()
        # Simple health check - try to get models list
        models = await llm_client.list_models()
        duration = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        return len(models) > 0, duration, None
    except Exception as e:
        return False, None, str(e)


# API Endpoints



@app.get("/", response_model=APIInfo)
async def root(request: Request) -> APIInfo:
    """API welcome and documentation"""
    return APIInfo(
        name="n8n Agent API",
        version="1.0.0",
        description="Intelligent agent interface for n8n workflow automation",
        endpoints=["/chat", "/dryrun", "/health", "/v1/models", "/v1/chat/completions", "/docs"],
        docs_url="http://localhost:8001/docs"
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, chat_request: ChatRequest) -> ChatResponse:
    """
    Process a chat message through the LangGraph agent
    
    - **message**: The user's message describing their workflow needs
    - **activate**: Whether to actually import/activate the workflow (default: false)
    """
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4())[:8])
    
    logger.info(f"💬 [{request_id}] Chat request: '{chat_request.message[:100]}{'...' if len(chat_request.message) > 100 else ''}', activate={chat_request.activate}")
    
    try:
        if not agent_graph:
            raise HTTPException(status_code=503, detail="Agent not initialized")
        
        # Process through agent
        result = await agent_graph.process_request(chat_request.message)
        
        # Extract workflow details if created
        workflow_created = result.get("workflow_created")
        workflow_id = workflow_created.get("id") if workflow_created else None
        editor_url = workflow_created.get("url") if workflow_created else None
        is_active = workflow_created.get("active", False) if workflow_created else False
        
        response = ChatResponse(
            workflow_id=workflow_id,
            editor_url=editor_url,
            active=is_active,
            message=result.get("user_response", "I encountered an issue processing your request."),
            request_id=request_id
        )
        
        logger.info(f"💬 [{request_id}] Chat response: workflow_id={response.workflow_id}, active={response.active}")
        return response
        
    except Exception as e:
        logger.error(f"❌ [{request_id}] Chat error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat request: {str(e)}"
        )


@app.post("/dryrun", response_model=DryRunResponse)
async def dryrun(request: Request, dryrun_request: DryRunRequest) -> DryRunResponse:
    """
    Search for templates without importing them (dry run)
    
    - **message**: Description of the desired workflow functionality
    """
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4())[:8])
    
    logger.info(f"🔍 [{request_id}] Dry run request: '{dryrun_request.message[:100]}{'...' if len(dryrun_request.message) > 100 else ''}'")
    
    try:
        if not template_service_client:
            raise HTTPException(status_code=503, detail="Template service not available")
        
        # Search for matching templates
        templates = await template_service_client.search_templates(dryrun_request.message)
        
        response = DryRunResponse(
            templates=templates,
            request_id=request_id
        )
        
        logger.info(f"🔍 [{request_id}] Dry run response: {len(templates)} templates found")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [{request_id}] Dry run error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to perform dry run: {str(e)}"
        )


@app.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    """
    Check the health of all connected services
    
    Returns the status of n8n, template service, and OpenRouter API
    """
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4())[:8])
    
    logger.info(f"🔍 [{request_id}] Health check requested")
    
    # Check all services concurrently
    health_checks = [
        ("n8n", check_n8n_health()),
        ("template_service", check_template_service_health()),
        ("openrouter", check_openrouter_health())
    ]
    
    services = []
    overall_healthy = True
    
    for service_name, health_check in health_checks:
        try:
            is_healthy, response_time, error = await health_check
            
            services.append(ServiceStatus(
                name=service_name,
                status="healthy" if is_healthy else "unhealthy",
                response_time_ms=response_time,
                error=error
            ))
            
            if not is_healthy:
                overall_healthy = False
                
        except Exception as e:
            services.append(ServiceStatus(
                name=service_name,
                status="unhealthy",
                response_time_ms=None,
                error=str(e)
            ))
            overall_healthy = False
    
    response = HealthResponse(
        status="healthy" if overall_healthy else "unhealthy",
        services=services,
        request_id=request_id
    )
    
    logger.info(f"🔍 [{request_id}] Health check: {response.status}")
    return response


# OpenAI-compatible API Endpoints

@app.get("/v1/models", response_model=OpenAIModelsResponse)
async def list_models(request: Request) -> OpenAIModelsResponse:
    """
    List available models (OpenAI-compatible)
    
    Returns a list of available models for the n8n workflow assistant
    """
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4())[:8])
    
    logger.info(f"🔍 [{request_id}] Models list requested")
    
    # Return our available model
    models = [
        OpenAIModel(
            id="n8n-workflow-assistant",
            created=int(datetime.utcnow().timestamp()),
            owned_by="n8n-agent-api"
        )
    ]
    
    return OpenAIModelsResponse(data=models)


@app.post("/v1/chat/completions", response_model=OpenAIChatResponse)
async def chat_completions(request: Request, openai_request: OpenAIChatRequest) -> OpenAIChatResponse:
    """
    Create chat completions (OpenAI-compatible)
    
    Process chat messages through the n8n workflow agent using OpenAI format
    """
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4())[:8])
    
    # Extract the user message from the OpenAI format
    user_message = ""
    for message in openai_request.messages:
        if message.role == "user":
            user_message = message.content
            break
    
    logger.info(f"🤖 [{request_id}] OpenAI chat request: '{user_message[:100]}{'...' if len(user_message) > 100 else ''}', model={openai_request.model}")
    
    try:
        if not agent_graph:
            raise HTTPException(status_code=503, detail="Agent not initialized")
        
        # Process through agent
        result = await agent_graph.process_request(user_message)
        
        # Get agent response
        agent_response = result.get("user_response", "I encountered an issue processing your request.")
        
        # Add workflow information to response if available
        workflow_created = result.get("workflow_created")
        if workflow_created:
            workflow_info = f"\n\n🔗 **Workflow Created:**\n- ID: {workflow_created.get('id')}\n- URL: {workflow_created.get('url')}\n- Active: {workflow_created.get('active', False)}"
            agent_response += workflow_info
        
        # Create OpenAI-compatible response
        response_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
        created_timestamp = int(datetime.utcnow().timestamp())
        
        # Estimate token usage (rough approximation)
        prompt_tokens = len(user_message.split()) * 1.3  # Rough token estimation
        completion_tokens = len(agent_response.split()) * 1.3
        total_tokens = int(prompt_tokens + completion_tokens)
        
        openai_response = OpenAIChatResponse(
            id=response_id,
            created=created_timestamp,
            model=openai_request.model,
            choices=[
                OpenAIChoice(
                    index=0,
                    message=OpenAIMessage(
                        role="assistant",
                        content=agent_response
                    ),
                    finish_reason="stop"
                )
            ],
            usage=OpenAIUsage(
                prompt_tokens=int(prompt_tokens),
                completion_tokens=int(completion_tokens),
                total_tokens=total_tokens
            )
        )
        
        logger.info(f"🤖 [{request_id}] OpenAI chat response: {total_tokens} tokens")
        return openai_response
        
    except Exception as e:
        logger.error(f"❌ [{request_id}] OpenAI chat error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat request: {str(e)}"
        )


# Error Handlers

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with request ID"""
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4())[:8])
    
    logger.error(f"❌ [{request_id}] HTTP {exc.status_code}: {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.detail,
                "status_code": exc.status_code,
                "request_id": request_id
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with request ID"""
    request_id = getattr(request.state, 'request_id', str(uuid.uuid4())[:8])
    
    logger.error(f"❌ [{request_id}] Unexpected error: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "An unexpected error occurred",
                "status_code": 500,
                "request_id": request_id
            }
        }
    )


# Development Server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )