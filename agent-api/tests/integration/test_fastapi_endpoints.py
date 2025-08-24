#!/usr/bin/env python3
"""
FastAPI Endpoint Tests for n8n Workflow Agent System

Comprehensive tests for all FastAPI endpoints with proper async/await patterns.
Run with: pytest test_fastapi_endpoints.py -v
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from typing import Dict, Any, List

import httpx
import pytest
from faker import Faker
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Import the FastAPI app and components
from main import (
    app, ChatRequest, ChatResponse, DryRunRequest, DryRunResponse,
    HealthResponse, TemplateServiceClient, ServiceStatus, APIInfo,
    TemplateMatch
)

fake = Faker()


class TestFastAPIEndpoints:
    """Comprehensive tests for FastAPI endpoints"""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for FastAPI app"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_dependencies(self):
        """Mock all external dependencies"""
        with patch('main.n8n_client') as mock_n8n, \
             patch('main.llm_client') as mock_llm, \
             patch('main.template_service_client') as mock_template, \
             patch('main.agent_graph') as mock_agent:
            
            # Setup n8n client mock
            mock_n8n.list_workflows = AsyncMock(return_value=[
                {"id": "1", "name": "Test Workflow 1", "active": True},
                {"id": "2", "name": "Test Workflow 2", "active": False}
            ])
            mock_n8n.create_workflow = AsyncMock(return_value={
                "id": "new-workflow-123",
                "name": "New Test Workflow",
                "active": False,
                "editorUrl": "http://n8n.localhost/workflow/new-workflow-123"
            })
            
            # Setup LLM client mock
            mock_llm.list_models = AsyncMock(return_value=[
                "openai/gpt-3.5-turbo",
                "openai/gpt-4", 
                "anthropic/claude-2"
            ])
            mock_llm.generate_text = AsyncMock(return_value="Mock LLM response")
            
            # Setup template service mock
            mock_template.health_check = AsyncMock(return_value=True)
            mock_template.search_templates = AsyncMock(return_value=[
                TemplateMatch(
                    id="template-123",
                    name="Test Template",
                    score=0.85,
                    description="A test template for testing"
                )
            ])
            
            # Setup agent mock
            mock_agent.process_request = AsyncMock(return_value={
                "success": True,
                "user_response": "Successfully created your workflow!",
                "workflow_created": {
                    "id": "agent-workflow-456",
                    "url": "http://localhost:5678/workflow/agent-workflow-456",
                    "active": False
                },
                "confidence_score": 0.92,
                "final_status": "completed"
            })
            
            yield {
                "n8n": mock_n8n,
                "llm": mock_llm,
                "template": mock_template,
                "agent": mock_agent
            }

    @pytest.mark.asyncio
    async def test_root_endpoint(self, test_client, mock_dependencies):
        """Test root endpoint returns correct API information"""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "n8n Agent API"
        assert data["version"] == "1.0.0"
        assert "description" in data
        assert isinstance(data["endpoints"], list)
        assert "/chat" in data["endpoints"]
        assert "/dryrun" in data["endpoints"]
        assert "/health" in data["endpoints"]
        assert "docs_url" in data
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_success(self, test_client, mock_dependencies):
        """Test successful chat endpoint request"""
        chat_request = {
            "message": "Create a workflow to send Slack notifications",
            "activate": False
        }
        
        response = test_client.post("/chat", json=chat_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "workflow_id" in data
        assert "editor_url" in data  
        assert "active" in data
        assert "message" in data
        assert "request_id" in data
        
        assert data["workflow_id"] == "agent-workflow-456"
        assert data["active"] is False
        assert "Successfully created" in data["message"]
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_with_activation(self, test_client, mock_dependencies):
        """Test chat endpoint with workflow activation"""
        # Update mock to return activated workflow
        mock_dependencies["agent"].process_request.return_value = {
            "success": True,
            "user_response": "Workflow created and activated!",
            "workflow_created": {
                "id": "activated-workflow-789",
                "url": "http://localhost:5678/workflow/activated-workflow-789",
                "active": True
            },
            "final_status": "completed"
        }
        
        chat_request = {
            "message": "Create and activate a Discord notification workflow",
            "activate": True
        }
        
        response = test_client.post("/chat", json=chat_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["workflow_id"] == "activated-workflow-789"
        assert data["active"] is True
        assert "activated" in data["message"]
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_validation_errors(self, test_client, mock_dependencies):
        """Test chat endpoint validation errors"""
        test_cases = [
            # Empty message
            {"message": "", "activate": False},
            # Message too long
            {"message": "x" * 2001, "activate": False},
            # Missing message
            {"activate": False},
            # Invalid data types
            {"message": 123, "activate": "not_boolean"}
        ]
        
        for invalid_request in test_cases:
            response = test_client.post("/chat", json=invalid_request)
            assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_chat_endpoint_agent_error(self, test_client, mock_dependencies):
        """Test chat endpoint when agent throws error"""
        mock_dependencies["agent"].process_request.side_effect = Exception("Agent processing error")
        
        chat_request = {
            "message": "This will cause an error",
            "activate": False
        }
        
        response = test_client.post("/chat", json=chat_request)
        
        assert response.status_code == 500
        data = response.json()
        
        assert "error" in data
        assert "Failed to process chat request" in data["error"]["message"]
        assert "request_id" in data["error"]
    
    @pytest.mark.asyncio
    async def test_dryrun_endpoint_success(self, test_client, mock_dependencies):
        """Test successful dry run endpoint"""
        dryrun_request = {
            "message": "I need a workflow to process customer feedback forms"
        }
        
        response = test_client.post("/dryrun", json=dryrun_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "templates" in data
        assert "request_id" in data
        assert isinstance(data["templates"], list)
        
        if data["templates"]:
            template = data["templates"][0]
            assert "id" in template
            assert "name" in template
            assert "score" in template
            assert "description" in template
    
    @pytest.mark.asyncio
    async def test_dryrun_endpoint_no_results(self, test_client, mock_dependencies):
        """Test dry run endpoint with no matching templates"""
        mock_dependencies["template"].search_templates.return_value = []
        
        dryrun_request = {
            "message": "Very specific and unusual workflow requirement"
        }
        
        response = test_client.post("/dryrun", json=dryrun_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "templates" in data
        assert len(data["templates"]) == 0
        assert "request_id" in data
    
    @pytest.mark.asyncio 
    async def test_dryrun_endpoint_validation_errors(self, test_client, mock_dependencies):
        """Test dry run endpoint validation errors"""
        test_cases = [
            # Empty message
            {"message": ""},
            # Message too long
            {"message": "x" * 2001},
            # Missing message
            {},
            # Invalid data type
            {"message": 123}
        ]
        
        for invalid_request in test_cases:
            response = test_client.post("/dryrun", json=invalid_request)
            assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_dryrun_endpoint_template_service_error(self, test_client, mock_dependencies):
        """Test dry run endpoint when template service fails"""
        mock_dependencies["template"].search_templates.side_effect = Exception("Template service error")
        
        dryrun_request = {
            "message": "This will cause template service error"
        }
        
        response = test_client.post("/dryrun", json=dryrun_request)
        
        assert response.status_code == 500
        data = response.json()
        
        assert "error" in data
        assert "Failed to perform dry run" in data["error"]["message"]
    
    @pytest.mark.asyncio
    async def test_health_endpoint_all_healthy(self, test_client, mock_dependencies):
        """Test health endpoint with all services healthy"""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "services" in data
        assert "request_id" in data
        
        assert len(data["services"]) == 3
        
        service_names = [service["name"] for service in data["services"]]
        assert "n8n" in service_names
        assert "template_service" in service_names
        assert "openrouter" in service_names
        
        # All should be healthy in this test
        for service in data["services"]:
            assert service["status"] == "healthy"
            assert "response_time_ms" in service
    
    @pytest.mark.asyncio
    async def test_health_endpoint_some_unhealthy(self, test_client, mock_dependencies):
        """Test health endpoint with some services unhealthy"""
        # Make template service unhealthy
        mock_dependencies["template"].health_check.return_value = False
        
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "unhealthy"  # Overall status should be unhealthy
        
        # Find template service status
        template_service = next(
            service for service in data["services"] 
            if service["name"] == "template_service"
        )
        assert template_service["status"] == "unhealthy"
    
    @pytest.mark.asyncio
    async def test_health_endpoint_service_errors(self, test_client, mock_dependencies):
        """Test health endpoint when services throw errors"""
        # Make n8n client throw error
        mock_dependencies["n8n"].list_workflows.side_effect = Exception("n8n connection error")
        
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "unhealthy"
        
        # Find n8n service status
        n8n_service = next(
            service for service in data["services"]
            if service["name"] == "n8n"
        )
        assert n8n_service["status"] == "unhealthy"
        assert "error" in n8n_service
        assert "n8n connection error" in n8n_service["error"]
    
    @pytest.mark.asyncio
    async def test_request_id_middleware(self, test_client, mock_dependencies):
        """Test that request ID is added to all responses"""
        endpoints_to_test = [
            ("/", "GET", None),
            ("/health", "GET", None),
            ("/chat", "POST", {"message": "test", "activate": False}),
            ("/dryrun", "POST", {"message": "test"})
        ]
        
        for endpoint, method, payload in endpoints_to_test:
            if method == "GET":
                response = test_client.get(endpoint)
            else:
                response = test_client.post(endpoint, json=payload)
            
            # All responses should have request_id (except validation errors)
            if response.status_code != 422:
                data = response.json()
                if "request_id" not in data:
                    # Check if it's in error object
                    if "error" in data:
                        assert "request_id" in data["error"]
                    else:
                        assert "request_id" in data
    
    @pytest.mark.asyncio
    async def test_cors_middleware(self, test_client, mock_dependencies):
        """Test CORS middleware allows cross-origin requests"""
        # Test preflight request
        response = test_client.options(
            "/chat",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        # Should allow CORS
        assert response.status_code in [200, 204]
    
    @pytest.mark.asyncio
    async def test_gzip_compression(self, test_client, mock_dependencies):
        """Test GZip compression middleware"""
        # Create a request that should trigger compression
        large_message = "x" * 1500  # Larger than minimum_size=1000
        
        response = test_client.post(
            "/chat",
            json={"message": large_message, "activate": False},
            headers={"Accept-Encoding": "gzip"}
        )
        
        assert response.status_code == 200
        # Response should be compressed if large enough
        # (TestClient might not actually compress, but middleware should be active)
    
    @pytest.mark.asyncio
    async def test_error_handler_http_exception(self, test_client, mock_dependencies):
        """Test HTTP exception handler"""
        # Trigger a 503 by making template service unavailable
        with patch('main.template_service_client', None):
            response = test_client.post("/dryrun", json={"message": "test"})
            
            assert response.status_code == 503
            data = response.json()
            
            assert "error" in data
            assert data["error"]["status_code"] == 503
            assert "request_id" in data["error"]
    
    @pytest.mark.asyncio
    async def test_error_handler_general_exception(self, test_client, mock_dependencies):
        """Test general exception handler"""
        # Force agent to throw unexpected error
        mock_dependencies["agent"].process_request.side_effect = ValueError("Unexpected error")
        
        response = test_client.post("/chat", json={"message": "test", "activate": False})
        
        assert response.status_code == 500
        data = response.json()
        
        assert "error" in data
        assert data["error"]["status_code"] == 500
        assert "An unexpected error occurred" in data["error"]["message"]
        assert "request_id" in data["error"]


class TestTemplateServiceClient:
    """Tests for TemplateServiceClient class"""
    
    @pytest.mark.asyncio
    async def test_search_templates_success(self):
        """Test successful template search"""
        mock_response_data = {
            "results": [
                {
                    "id": "template-1",
                    "name": "Email Automation", 
                    "score": 0.95,
                    "description": "Automated email processing"
                },
                {
                    "id": "template-2",
                    "name": "Slack Integration",
                    "score": 0.78,
                    "description": "Send Slack notifications"
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            client = TemplateServiceClient("http://localhost:8000")
            results = await client.search_templates("email automation")
            
            assert len(results) == 2
            assert results[0].id == "template-1"
            assert results[0].name == "Email Automation"
            assert results[0].score == 0.95
            assert results[1].id == "template-2"
    
    @pytest.mark.asyncio
    async def test_search_templates_empty_results(self):
        """Test template search with no results"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = {"results": []}
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            client = TemplateServiceClient("http://localhost:8000")
            results = await client.search_templates("nonexistent template")
            
            assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_search_templates_http_error(self):
        """Test template search HTTP error handling"""
        with patch('httpx.AsyncClient') as mock_client:
            http_error = httpx.HTTPStatusError(
                "503 Service Unavailable",
                request=Mock(),
                response=Mock(status_code=503, text="Service unavailable")
            )
            mock_client.return_value.__aenter__.return_value.post.return_value.raise_for_status.side_effect = http_error
            
            client = TemplateServiceClient("http://localhost:8000")
            
            with pytest.raises(Exception, match="Template service unavailable"):
                await client.search_templates("test query")
    
    @pytest.mark.asyncio
    async def test_fetch_template_success(self):
        """Test successful template fetch"""
        mock_template_data = {
            "id": "template-123",
            "name": "Test Template",
            "workflow": {
                "nodes": [],
                "connections": {}
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.json.return_value = mock_template_data
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            client = TemplateServiceClient("http://localhost:8000")
            result = await client.fetch_template("template-123")
            
            assert result["id"] == "template-123"
            assert result["name"] == "Test Template"
            assert "workflow" in result
    
    @pytest.mark.asyncio
    async def test_fetch_template_not_found(self):
        """Test template fetch with 404 error"""
        with patch('httpx.AsyncClient') as mock_client:
            http_error = httpx.HTTPStatusError(
                "404 Not Found",
                request=Mock(),
                response=Mock(status_code=404, text="Template not found")
            )
            mock_client.return_value.__aenter__.return_value.get.return_value.raise_for_status.side_effect = http_error
            
            client = TemplateServiceClient("http://localhost:8000")
            
            with pytest.raises(Exception, match="Could not fetch template"):
                await client.fetch_template("nonexistent-template")
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            client = TemplateServiceClient("http://localhost:8000")
            result = await client.health_check()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.ConnectError("Connection failed")
            
            client = TemplateServiceClient("http://localhost:8000")
            result = await client.health_check()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test client cleanup"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_aclose = AsyncMock()
            mock_client.return_value.aclose = mock_aclose
            
            client = TemplateServiceClient("http://localhost:8000")
            await client.close()
            
            mock_aclose.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])