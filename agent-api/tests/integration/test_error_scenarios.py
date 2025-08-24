#!/usr/bin/env python3
"""
Error Scenario Tests for n8n Workflow Agent System

Comprehensive tests for error handling, edge cases, and failure scenarios.
Run with: pytest test_error_scenarios.py -v
"""

import asyncio
import json
import os
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List

import httpx
import pytest
from faker import Faker
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Import modules under test
from llm_client import LLMClient, OpenRouterClient
from n8n_client import N8nClient
from langgraph_agent import WorkflowAgent, WorkflowState
from main import app, TemplateServiceClient

fake = Faker()


class TestLLMErrorScenarios:
    """Test LLM client error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_openrouter_api_key_missing(self):
        """Test OpenRouter client without API key"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenRouter API key not provided"):
                OpenRouterClient()
    
    @pytest.mark.asyncio
    async def test_openrouter_network_timeout(self):
        """Test OpenRouter client network timeout"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            # Setup timeout error
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            async_context.post.side_effect = httpx.TimeoutException("Request timeout")
            
            client = OpenRouterClient()
            
            with pytest.raises(httpx.TimeoutException):
                await client.chat_completion([{"role": "user", "content": "test"}])
    
    @pytest.mark.asyncio
    async def test_openrouter_rate_limiting(self):
        """Test OpenRouter client rate limiting"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            # Setup rate limit error
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            mock_response = Mock()
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            
            http_error = httpx.HTTPStatusError(
                "429 Too Many Requests",
                request=Mock(),
                response=mock_response
            )
            async_context.post.return_value.raise_for_status.side_effect = http_error
            
            client = OpenRouterClient()
            
            with pytest.raises(httpx.HTTPStatusError) as exc_info:
                await client.chat_completion([{"role": "user", "content": "test"}])
            
            assert "429" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_openrouter_malformed_response(self):
        """Test OpenRouter client with malformed JSON response"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            # Setup malformed response
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            mock_response = Mock()
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_response.raise_for_status.return_value = None
            async_context.post.return_value = mock_response
            
            client = OpenRouterClient()
            
            with pytest.raises(json.JSONDecodeError):
                await client.chat_completion([{"role": "user", "content": "test"}])
    
    @pytest.mark.asyncio
    async def test_openrouter_empty_choices(self):
        """Test OpenRouter client with empty choices array"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            # Setup response with empty choices
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            mock_response = Mock()
            mock_response.json.return_value = {"choices": []}
            mock_response.raise_for_status.return_value = None
            async_context.post.return_value = mock_response
            
            client = OpenRouterClient()
            
            with pytest.raises((IndexError, KeyError)):
                await client.chat_completion([{"role": "user", "content": "test"}])
    
    @pytest.mark.asyncio
    async def test_intent_extraction_invalid_json_fallback(self):
        """Test intent extraction fallback for invalid JSON"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            # Setup response with invalid JSON
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            mock_response = Mock()
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": "This is not valid JSON for intent extraction"
                    }
                }]
            }
            mock_response.raise_for_status.return_value = None
            async_context.post.return_value = mock_response
            
            client = OpenRouterClient()
            result = await client.extract_intent("Create workflow")
            
            # Should fallback to default structure
            assert "integrations" in result
            assert "trigger_type" in result
            assert "action" in result
            assert result["trigger_type"] == "manual"
            assert result["action"] == "Create workflow"
    
    @pytest.mark.asyncio
    async def test_template_scoring_invalid_score_fallback(self):
        """Test template scoring fallback for invalid score format"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            # Setup response with invalid score format
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            mock_response = Mock()
            mock_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": "This is not a valid score format"
                    }
                }]
            }
            mock_response.raise_for_status.return_value = None
            async_context.post.return_value = mock_response
            
            client = OpenRouterClient()
            score = await client.score_template_match(
                "Test request with email integration",
                "Email_Processing_Template",
                ["email", "processing"],
                "webhook"
            )
            
            # Should use keyword-based fallback
            assert isinstance(score, float)
            assert 0 <= score <= 100
            # Should get bonus points for matching "email" keyword
            assert score >= 50  # Base score + integration matches


class TestN8nErrorScenarios:
    """Test n8n client error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_n8n_connection_refused(self):
        """Test n8n client with connection refused"""
        with patch('httpx.AsyncClient') as mock_client:
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            async_context.get.side_effect = httpx.ConnectError("Connection refused")
            
            client = N8nClient("http://nonexistent-n8n:5678")
            result = await client.test_connection()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_n8n_api_authentication_error(self):
        """Test n8n client with authentication error"""
        with patch('httpx.AsyncClient') as mock_client:
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # Mock API detection success
            async_context.get.return_value = Mock(status_code=200)
            
            # Mock workflow creation with auth error
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized - Invalid credentials"
            
            http_error = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=Mock(),
                response=mock_response
            )
            async_context.post.return_value.raise_for_status.side_effect = http_error
            
            client = N8nClient("http://test-n8n:5678")
            
            with pytest.raises(Exception, match="n8n API error: 401"):
                await client.create_workflow({"name": "Test Workflow"})
    
    @pytest.mark.asyncio
    async def test_n8n_workflow_validation_error(self):
        """Test n8n client with workflow validation error"""
        with patch('httpx.AsyncClient') as mock_client:
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # Mock API detection success
            async_context.get.return_value = Mock(status_code=200)
            
            # Mock workflow creation with validation error
            mock_response = Mock()
            mock_response.status_code = 422
            mock_response.text = "Workflow validation failed: Invalid node configuration"
            
            http_error = httpx.HTTPStatusError(
                "422 Unprocessable Entity",
                request=Mock(),
                response=mock_response
            )
            async_context.post.return_value.raise_for_status.side_effect = http_error
            
            client = N8nClient("http://test-n8n:5678")
            
            with pytest.raises(Exception, match="n8n API error: 422"):
                await client.create_workflow({
                    "name": "Invalid Workflow",
                    "nodes": [{"invalid": "node"}]
                })
    
    @pytest.mark.asyncio
    async def test_n8n_server_error(self):
        """Test n8n client with server error"""
        with patch('httpx.AsyncClient') as mock_client:
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # Mock API detection success
            async_context.get.return_value = Mock(status_code=200)
            
            # Mock server error during workflow creation
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal server error"
            
            http_error = httpx.HTTPStatusError(
                "500 Internal Server Error",
                request=Mock(),
                response=mock_response
            )
            async_context.post.return_value.raise_for_status.side_effect = http_error
            
            client = N8nClient("http://test-n8n:5678")
            
            with pytest.raises(Exception, match="n8n API error: 500"):
                await client.create_workflow({"name": "Test Workflow"})
    
    @pytest.mark.asyncio
    async def test_n8n_malformed_workflow_response(self):
        """Test n8n client with malformed workflow response"""
        with patch('httpx.AsyncClient') as mock_client:
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # Mock API detection
            async_context.get.return_value = Mock(status_code=200)
            
            # Mock malformed response
            mock_response = Mock()
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_response.raise_for_status.return_value = None
            async_context.post.return_value = mock_response
            
            client = N8nClient("http://test-n8n:5678")
            
            with pytest.raises(json.JSONDecodeError):
                await client.create_workflow({"name": "Test Workflow"})
    
    @pytest.mark.asyncio
    async def test_n8n_api_path_detection_total_failure(self):
        """Test n8n client when both API paths fail"""
        with patch('httpx.AsyncClient') as mock_client:
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # Both API paths fail
            async_context.get.side_effect = [
                httpx.ConnectError("Connection failed"),  # /api/v1 fails
                httpx.ConnectError("Connection failed")   # /rest fails
            ]
            
            client = N8nClient("http://test-n8n:5678")
            api_path = await client.detect_api_path()
            
            # Should default to /api/v1
            assert api_path == "/api/v1"
            assert client.api_path == "/api/v1"


class TestTemplateServiceErrorScenarios:
    """Test template service error handling scenarios"""
    
    @pytest.mark.asyncio
    async def test_template_service_connection_error(self):
        """Test template service connection error"""
        with patch('httpx.AsyncClient') as mock_client:
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            async_context.post.side_effect = httpx.ConnectError("Connection refused")
            
            client = TemplateServiceClient("http://nonexistent-service:8000")
            
            with pytest.raises(HTTPException, match="Template service unavailable"):
                await client.search_templates("test query")
    
    @pytest.mark.asyncio
    async def test_template_service_timeout(self):
        """Test template service timeout"""
        with patch('httpx.AsyncClient') as mock_client:
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            async_context.post.side_effect = httpx.TimeoutException("Request timeout")
            
            client = TemplateServiceClient("http://slow-service:8000")
            
            with pytest.raises(HTTPException, match="Template service unavailable"):
                await client.search_templates("test query")
    
    @pytest.mark.asyncio
    async def test_template_service_malformed_response(self):
        """Test template service with malformed response"""
        with patch('httpx.AsyncClient') as mock_client:
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            mock_response = Mock()
            mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            mock_response.raise_for_status.return_value = None
            async_context.post.return_value = mock_response
            
            client = TemplateServiceClient("http://broken-service:8000")
            
            with pytest.raises(HTTPException, match="Template service unavailable"):
                await client.search_templates("test query")
    
    @pytest.mark.asyncio
    async def test_template_service_missing_fields(self):
        """Test template service response with missing required fields"""
        with patch('httpx.AsyncClient') as mock_client:
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # Response missing required fields
            mock_response = Mock()
            mock_response.json.return_value = {
                "results": [
                    {"id": "template-1"},  # Missing name, score, description
                    {"name": "Template 2", "score": 0.8}  # Missing id, description
                ]
            }
            mock_response.raise_for_status.return_value = None
            async_context.post.return_value = mock_response
            
            client = TemplateServiceClient("http://incomplete-service:8000")
            
            # Should handle missing fields gracefully
            with pytest.raises((KeyError, TypeError)):
                await client.search_templates("test query")
    
    @pytest.mark.asyncio
    async def test_template_service_server_error(self):
        """Test template service server error"""
        with patch('httpx.AsyncClient') as mock_client:
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            mock_response = Mock()
            mock_response.status_code = 500
            mock_response.text = "Internal server error"
            
            http_error = httpx.HTTPStatusError(
                "500 Internal Server Error",
                request=Mock(),
                response=mock_response
            )
            async_context.post.return_value.raise_for_status.side_effect = http_error
            
            client = TemplateServiceClient("http://error-service:8000")
            
            with pytest.raises(HTTPException, match="Template service unavailable"):
                await client.search_templates("test query")


class TestWorkflowAgentErrorScenarios:
    """Test workflow agent error handling scenarios"""
    
    @pytest.fixture
    def agent_with_mocked_clients(self):
        """Create agent with mocked clients for error testing"""
        mock_llm = Mock(spec=LLMClient)
        mock_llm.generate_text = AsyncMock()
        
        mock_n8n = Mock(spec=N8nClient)
        mock_n8n.create_workflow = AsyncMock()
        mock_n8n.base_url = "http://test-n8n:5678"
        
        agent = WorkflowAgent(mock_llm, mock_n8n)
        return agent, mock_llm, mock_n8n
    
    @pytest.mark.asyncio
    async def test_agent_intent_parsing_failure(self, agent_with_mocked_clients):
        """Test agent when intent parsing fails"""
        agent, mock_llm, mock_n8n = agent_with_mocked_clients
        
        # Make LLM fail during intent parsing
        mock_llm.generate_text.side_effect = Exception("LLM service unavailable")
        
        result = await agent.process_request("Create a test workflow")
        
        assert result["success"] is False
        assert "error" in result
        assert "LLM service unavailable" in result["error"]
        assert result["final_status"] == "error"
    
    @pytest.mark.asyncio
    async def test_agent_template_search_failure(self, agent_with_mocked_clients):
        """Test agent when template search phase fails"""
        agent, mock_llm, mock_n8n = agent_with_mocked_clients
        
        # Setup successful intent parsing
        mock_llm.generate_text.return_value = json.dumps({
            "integrations": ["slack"],
            "trigger_type": "webhook",
            "action": "send_message",
            "requirements": [],
            "complexity": "simple"
        })
        
        # Make template search fail by making _simulate_template_search raise error
        with patch.object(agent, '_simulate_template_search', side_effect=Exception("Template search failed")):
            result = await agent.process_request("Create a Slack workflow")
        
        assert result["success"] is False
        assert "Template search failed" in result["error"]
        assert result["final_status"] == "error"
    
    @pytest.mark.asyncio
    async def test_agent_template_scoring_failure(self, agent_with_mocked_clients):
        """Test agent when template scoring fails"""
        agent, mock_llm, mock_n8n = agent_with_mocked_clients
        
        # Setup successful intent parsing
        mock_llm.generate_text.side_effect = [
            json.dumps({
                "integrations": ["slack"],
                "trigger_type": "webhook", 
                "action": "send_message",
                "requirements": [],
                "complexity": "simple"
            }),
            # Then fail during scoring
            Exception("Scoring service unavailable")
        ]
        
        result = await agent.process_request("Create a Slack workflow")
        
        assert result["success"] is False
        assert "Scoring service unavailable" in result["error"]
        assert result["final_status"] == "error"
    
    @pytest.mark.asyncio
    async def test_agent_n8n_creation_failure(self, agent_with_mocked_clients):
        """Test agent when n8n workflow creation fails"""
        agent, mock_llm, mock_n8n = agent_with_mocked_clients
        
        # Setup successful processing until n8n creation
        mock_llm.generate_text.side_effect = [
            json.dumps({
                "integrations": ["slack"],
                "trigger_type": "webhook",
                "action": "send_message",
                "requirements": [],
                "complexity": "simple"
            }),
            "0.85"  # Good score
        ]
        
        # Make n8n creation fail
        mock_n8n.create_workflow.side_effect = Exception("n8n workflow creation failed")
        
        result = await agent.process_request("Create a Slack workflow")
        
        assert result["success"] is False
        assert "n8n workflow creation failed" in result["error"]
        assert result["final_status"] == "error"
    
    @pytest.mark.asyncio
    async def test_agent_response_generation_failure(self, agent_with_mocked_clients):
        """Test agent when response generation fails"""
        agent, mock_llm, mock_n8n = agent_with_mocked_clients
        
        # Setup successful processing until response generation
        mock_llm.generate_text.side_effect = [
            json.dumps({
                "integrations": ["slack"],
                "trigger_type": "webhook",
                "action": "send_message", 
                "requirements": [],
                "complexity": "simple"
            }),
            "0.85",  # Good score
            Exception("Response generation failed")  # Fail at response generation
        ]
        
        # Setup successful n8n creation
        mock_n8n.create_workflow.return_value = {
            "id": "test-workflow-123",
            "name": "Test Workflow",
            "active": False
        }
        
        result = await agent.process_request("Create a Slack workflow")
        
        assert result["success"] is False
        assert "Response generation failed" in result["error"]
        assert result["final_status"] == "error"
    
    @pytest.mark.asyncio
    async def test_agent_retry_exhaustion(self, agent_with_mocked_clients):
        """Test agent when retries are exhausted"""
        agent, mock_llm, mock_n8n = agent_with_mocked_clients
        
        # Setup successful processing until n8n creation
        mock_llm.generate_text.side_effect = [
            json.dumps({
                "integrations": ["slack"],
                "trigger_type": "webhook",
                "action": "send_message",
                "requirements": [],
                "complexity": "simple"
            }),
            "0.85"  # Good score
        ]
        
        # Make n8n creation fail consistently (more than max_retries)
        mock_n8n.create_workflow.side_effect = Exception("Persistent n8n failure")
        
        result = await agent.process_request("Create a Slack workflow")
        
        assert result["success"] is False
        assert "failed after 3 retries" in result["error"] or "Persistent n8n failure" in result["error"]
        assert result["final_status"] == "error"
        
        # Verify retry attempts
        assert mock_n8n.create_workflow.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_agent_unexpected_state_error(self, agent_with_mocked_clients):
        """Test agent with unexpected state conditions"""
        agent, mock_llm, mock_n8n = agent_with_mocked_clients
        
        # Create a state that violates expectations (e.g., no candidates after search)
        with patch.object(agent, '_search_templates') as mock_search:
            mock_search.return_value = {
                "user_query": "test",
                "intent": {"integrations": ["test"]},
                "candidates": None,  # This should cause issues
                "selected_workflow": None,
                "workflow_created": None,
                "error": None,
                "confidence_score": None,
                "retry_count": 0
            }
            
            result = await agent.process_request("Create a test workflow")
            
            # Should handle gracefully and route to appropriate error handling
            assert result["success"] is False or result["final_status"] in ["error", "manual_selection_required"]


class TestFastAPIErrorScenarios:
    """Test FastAPI endpoint error scenarios"""
    
    @pytest.fixture
    def test_client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_chat_endpoint_agent_not_initialized(self, test_client):
        """Test chat endpoint when agent is not initialized"""
        with patch('main.agent_graph', None):
            response = test_client.post("/chat", json={
                "message": "This should fail",
                "activate": False
            })
            
            assert response.status_code == 503
            data = response.json()
            assert "Agent not initialized" in data["error"]["message"]
    
    def test_dryrun_endpoint_template_service_not_initialized(self, test_client):
        """Test dryrun endpoint when template service is not initialized"""
        with patch('main.template_service_client', None):
            response = test_client.post("/dryrun", json={
                "message": "This should fail"
            })
            
            assert response.status_code == 503
            data = response.json()
            assert "Template service not available" in data["error"]["message"]
    
    def test_health_endpoint_with_service_failures(self, test_client):
        """Test health endpoint when services are failing"""
        with patch('main.check_n8n_health') as mock_n8n_health, \
             patch('main.check_template_service_health') as mock_template_health, \
             patch('main.check_openrouter_health') as mock_openrouter_health:
            
            # Make all services return failure
            mock_n8n_health.return_value = (False, None, "Connection failed")
            mock_template_health.return_value = (False, None, "Service unavailable")
            mock_openrouter_health.return_value = (False, None, "API key invalid")
            
            response = test_client.get("/health")
            
            assert response.status_code == 200  # Health endpoint always returns 200
            data = response.json()
            
            assert data["status"] == "unhealthy"
            assert len(data["services"]) == 3
            
            # All services should be marked as unhealthy
            for service in data["services"]:
                assert service["status"] == "unhealthy"
                assert service["error"] is not None
    
    def test_request_body_too_large(self, test_client):
        """Test request with extremely large body"""
        # Create a very large message (FastAPI should handle this at middleware level)
        large_message = "x" * 10000  # 10KB message, larger than our 2000 char limit
        
        response = test_client.post("/chat", json={
            "message": large_message,
            "activate": False
        })
        
        # Should get validation error for message length
        assert response.status_code == 422
    
    def test_malformed_json_request(self, test_client):
        """Test request with malformed JSON"""
        # Send malformed JSON
        response = test_client.post(
            "/chat",
            data="{invalid json}",
            headers={"Content-Type": "application/json"}
        )
        
        # Should get JSON decode error
        assert response.status_code == 422
    
    def test_unsupported_media_type(self, test_client):
        """Test request with unsupported media type"""
        # Send XML instead of JSON
        response = test_client.post(
            "/chat",
            data="<xml>test</xml>",
            headers={"Content-Type": "application/xml"}
        )
        
        # Should get unsupported media type error
        assert response.status_code == 422
    
    def test_missing_required_fields(self, test_client):
        """Test requests with missing required fields"""
        test_cases = [
            # Chat endpoint missing message
            ("/chat", {"activate": False}),
            # Dryrun endpoint missing message
            ("/dryrun", {}),
            # Chat endpoint with null message
            ("/chat", {"message": None, "activate": False}),
        ]
        
        for endpoint, payload in test_cases:
            response = test_client.post(endpoint, json=payload)
            assert response.status_code == 422
            
            data = response.json()
            assert "detail" in data  # Pydantic validation error format


if __name__ == "__main__":
    pytest.main([__file__, "-v"])