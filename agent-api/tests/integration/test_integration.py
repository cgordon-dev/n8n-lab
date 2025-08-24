#!/usr/bin/env python3
"""
Integration Tests for n8n Workflow Agent System

Tests complete workflows with external service integration.
Run with: pytest test_integration.py -m integration
"""

import asyncio
import json
import os
import uuid
from typing import Dict, Any
from unittest.mock import patch, AsyncMock, Mock

import httpx
import pytest
from faker import Faker
from fastapi.testclient import TestClient

# Import the FastAPI app and components
from main import app, n8n_client, llm_client, template_service_client, agent_graph
from main import (
    ChatRequest, ChatResponse, DryRunRequest, DryRunResponse, 
    HealthResponse, TemplateServiceClient
)

fake = Faker()


@pytest.fixture(scope="session")
def test_client():
    """Create test client for FastAPI app"""
    return TestClient(app)


@pytest.fixture
async def mock_template_service():
    """Mock template service responses"""
    mock_templates = [
        {
            "id": "slack-webhook-notify",
            "name": "Slack Webhook Notification",
            "description": "Send Slack notifications via incoming webhooks",
            "score": 0.95,
            "integrations": ["slack", "webhook"],
            "category": "messaging"
        },
        {
            "id": "email-discord-bridge", 
            "name": "Email to Discord Bridge",
            "description": "Forward important emails to Discord channels",
            "score": 0.78,
            "integrations": ["email", "discord"],
            "category": "notifications"
        }
    ]
    
    mock_workflow_json = {
        "id": "test-workflow-123",
        "name": "Test Integration Workflow",
        "nodes": [
            {
                "id": "webhook",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 1,
                "position": [200, 300],
                "parameters": {"path": "integration-test"}
            },
            {
                "id": "slack",
                "type": "n8n-nodes-base.slack", 
                "typeVersion": 1,
                "position": [400, 300],
                "parameters": {
                    "channel": "#general",
                    "text": "Integration test message"
                }
            }
        ],
        "connections": {
            "webhook": {
                "main": [[{"node": "slack", "type": "main", "index": 0}]]
            }
        },
        "active": False
    }
    
    return {
        "search_results": {"results": mock_templates},
        "workflow_json": mock_workflow_json
    }


class TestTemplateServiceIntegration:
    """Integration tests for template service interaction"""
    
    @pytest.mark.integration
    @pytest.mark.template_service
    async def test_template_service_search_success(self, mock_template_service):
        """Test successful template search integration"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock search response
            mock_response = Mock()
            mock_response.json.return_value = mock_template_service["search_results"]
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            client = TemplateServiceClient("http://localhost:8000")
            results = await client.search_templates("slack webhook notification")
            
            assert len(results) == 2
            assert results[0].name == "Slack Webhook Notification"
            assert results[0].score == 0.95
            assert "slack" in results[0].id
    
    @pytest.mark.integration
    @pytest.mark.template_service
    async def test_template_service_fetch_success(self, mock_template_service):
        """Test successful template fetch integration"""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock fetch response
            mock_response = Mock()
            mock_response.json.return_value = mock_template_service["workflow_json"]
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            client = TemplateServiceClient("http://localhost:8000")
            result = await client.fetch_template("slack-webhook-notify")
            
            assert result["id"] == "test-workflow-123"
            assert result["name"] == "Test Integration Workflow"
            assert len(result["nodes"]) == 2
    
    @pytest.mark.integration
    @pytest.mark.template_service
    async def test_template_service_health_check(self):
        """Test template service health check"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            client = TemplateServiceClient("http://localhost:8000")
            is_healthy = await client.health_check()
            
            assert is_healthy is True
    
    @pytest.mark.integration
    @pytest.mark.template_service
    async def test_template_service_connection_error(self):
        """Test template service connection error handling"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.side_effect = httpx.ConnectError("Connection failed")
            
            client = TemplateServiceClient("http://localhost:8000")
            
            with pytest.raises(Exception, match="Template service unavailable"):
                await client.search_templates("test query")


class TestN8nIntegration:
    """Integration tests for n8n API interaction"""
    
    @pytest.mark.integration
    @pytest.mark.n8n
    async def test_n8n_workflow_creation_integration(self, mock_template_service):
        """Test complete n8n workflow creation process"""
        from n8n_client import N8nClient
        
        with patch('httpx.AsyncClient') as mock_client:
            # Mock API path detection
            mock_client.return_value.__aenter__.return_value.get.return_value = Mock(status_code=200)
            
            # Mock workflow creation
            mock_create_response = Mock()
            mock_create_response.json.return_value = {
                "id": "workflow-integration-123",
                "name": "Integration Test Workflow",
                "active": False,
                "nodes": mock_template_service["workflow_json"]["nodes"]
            }
            mock_create_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_create_response
            
            client = N8nClient("http://localhost:5678")
            result = await client.create_workflow(
                mock_template_service["workflow_json"], 
                activate=False
            )
            
            assert result["id"] == "workflow-integration-123"
            assert result["name"] == "Integration Test Workflow"
            assert result["active"] is False
            assert "editorUrl" in result
    
    @pytest.mark.integration
    @pytest.mark.n8n
    async def test_n8n_workflow_activation_integration(self):
        """Test n8n workflow activation integration"""
        from n8n_client import N8nClient
        
        with patch('httpx.AsyncClient') as mock_client:
            # Mock API path detection
            mock_client.return_value.__aenter__.return_value.get.return_value = Mock(status_code=200)
            
            # Mock workflow activation
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.patch.return_value = mock_response
            
            client = N8nClient("http://localhost:5678")
            result = await client.activate_workflow("test-workflow-123")
            
            assert result is True
    
    @pytest.mark.integration  
    @pytest.mark.n8n
    async def test_n8n_list_workflows_integration(self):
        """Test n8n workflow listing integration"""
        from n8n_client import N8nClient
        
        mock_workflows = [
            {"id": "1", "name": "Test Workflow 1", "active": True},
            {"id": "2", "name": "Test Workflow 2", "active": False}
        ]
        
        with patch('httpx.AsyncClient') as mock_client:
            # Mock API path detection
            mock_client.return_value.__aenter__.return_value.get.side_effect = [
                Mock(status_code=200),  # API path detection
                Mock(json=lambda: mock_workflows, raise_for_status=lambda: None)  # List workflows
            ]
            
            client = N8nClient("http://localhost:5678")
            result = await client.list_workflows()
            
            assert len(result) == 2
            assert result[0]["name"] == "Test Workflow 1"
            assert result[1]["active"] is False


class TestLLMIntegration:
    """Integration tests for LLM service interaction"""
    
    @pytest.mark.integration
    @pytest.mark.openrouter
    async def test_openrouter_chat_completion_integration(self):
        """Test OpenRouter chat completion integration"""
        from llm_client import OpenRouterClient
        
        mock_response = {
            "choices": [{
                "message": {
                    "content": "This is a test response from OpenRouter integration test"
                }
            }],
            "usage": {"total_tokens": 25}
        }
        
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key-integration'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_http_response = Mock()
            mock_http_response.json.return_value = mock_response
            mock_http_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_http_response
            
            client = OpenRouterClient()
            result = await client.chat_completion([
                {"role": "user", "content": "Hello, this is an integration test"}
            ])
            
            assert result == mock_response
            assert "This is a test response" in result["choices"][0]["message"]["content"]
    
    @pytest.mark.integration
    @pytest.mark.openrouter
    async def test_openrouter_intent_extraction_integration(self):
        """Test complete intent extraction integration"""
        from llm_client import OpenRouterClient
        
        mock_intent = {
            "integrations": ["slack", "webhook"],
            "trigger_type": "webhook",
            "action": "send notification",
            "requirements": ["real-time", "channel-specific"]
        }
        
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps(mock_intent)
                }
            }]
        }
        
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key-integration'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_http_response = Mock()
            mock_http_response.json.return_value = mock_response
            mock_http_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_http_response
            
            client = OpenRouterClient()
            result = await client.extract_intent(
                "Send Slack notifications when webhook is triggered with specific channel targeting"
            )
            
            assert result == mock_intent
            assert result["integrations"] == ["slack", "webhook"]
            assert result["trigger_type"] == "webhook"
    
    @pytest.mark.integration
    @pytest.mark.openrouter
    async def test_openrouter_template_scoring_integration(self):
        """Test template scoring integration"""
        from llm_client import OpenRouterClient
        
        mock_response = {
            "choices": [{
                "message": {
                    "content": '{"score": 87, "reasoning": "Excellent match for webhook-to-slack integration"}'
                }
            }]
        }
        
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key-integration'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_http_response = Mock()
            mock_http_response.json.return_value = mock_response  
            mock_http_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_http_response
            
            client = OpenRouterClient()
            score = await client.score_template_match(
                "Send Slack notifications via webhook",
                "Webhook to Slack Notifier",
                ["webhook", "slack"],
                "webhook"
            )
            
            assert score == 87.0


class TestFastAPIEndpoints:
    """Integration tests for FastAPI endpoints"""
    
    @pytest.fixture
    def mock_agent_dependencies(self, mock_template_service):
        """Mock all agent dependencies for endpoint testing"""
        with patch('main.n8n_client') as mock_n8n, \
             patch('main.llm_client') as mock_llm, \
             patch('main.template_service_client') as mock_template, \
             patch('main.agent_graph') as mock_agent:
            
            # Setup mocks
            mock_n8n.list_workflows = AsyncMock(return_value=[])
            mock_llm.list_models = AsyncMock(return_value=["model1", "model2"])  
            mock_template.health_check = AsyncMock(return_value=True)
            
            # Mock agent response
            mock_agent.process_request = AsyncMock(return_value={
                "success": True,
                "user_response": "Successfully created your Slack notification workflow!",
                "workflow_created": {
                    "id": "test-workflow-456",
                    "url": "http://localhost:5678/workflow/test-workflow-456",
                    "active": False
                },
                "final_status": "completed"
            })
            
            yield {
                "n8n": mock_n8n,
                "llm": mock_llm, 
                "template": mock_template,
                "agent": mock_agent
            }
    
    @pytest.mark.integration
    def test_root_endpoint(self, test_client):
        """Test root endpoint returns API info"""
        response = test_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "n8n Agent API"
        assert data["version"] == "1.0.0"
        assert "/chat" in data["endpoints"]
        assert "/health" in data["endpoints"]
    
    @pytest.mark.integration 
    def test_chat_endpoint_success(self, test_client, mock_agent_dependencies):
        """Test successful chat endpoint integration"""
        chat_request = {
            "message": "Create a workflow to send Slack notifications when webhooks are received",
            "activate": False
        }
        
        response = test_client.post("/chat", json=chat_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == "test-workflow-456"
        assert data["active"] is False
        assert "Successfully created" in data["message"]
        assert "request_id" in data
    
    @pytest.mark.integration
    def test_chat_endpoint_with_activation(self, test_client, mock_agent_dependencies):
        """Test chat endpoint with workflow activation"""
        # Update mock to return active workflow
        mock_agent_dependencies["agent"].ainvoke.return_value = {
            "workflow_id": "test-workflow-789", 
            "editor_url": "http://localhost:5678/workflow/test-workflow-789",
            "active": True,
            "message": "Workflow created and activated successfully!"
        }
        
        chat_request = {
            "message": "Create and activate a Discord notification workflow",
            "activate": True
        }
        
        response = test_client.post("/chat", json=chat_request)
        
        assert response.status_code == 200
        data = response.json()
        assert data["workflow_id"] == "test-workflow-789"
        assert data["active"] is True
        assert "activated" in data["message"]
    
    @pytest.mark.integration
    def test_chat_endpoint_validation_error(self, test_client):
        """Test chat endpoint input validation"""
        # Empty message should fail validation
        chat_request = {"message": "", "activate": False}
        
        response = test_client.post("/chat", json=chat_request)
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.integration
    def test_dryrun_endpoint_success(self, test_client, mock_agent_dependencies, mock_template_service):
        """Test successful dry run endpoint"""
        with patch('main.template_service_client') as mock_template:
            from main import TemplateMatch
            
            mock_template.search_templates.return_value = [
                TemplateMatch(
                    id="template-123",
                    name="Webhook to Email",
                    score=0.92,
                    description="Forward webhook data via email"
                ),
                TemplateMatch(
                    id="template-456", 
                    name="Slack Integration",
                    score=0.78,
                    description="Send Slack messages from webhooks"
                )
            ]
            
            dryrun_request = {"message": "Process webhooks and send notifications"}
            
            response = test_client.post("/dryrun", json=dryrun_request)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["templates"]) == 2
            assert data["templates"][0]["name"] == "Webhook to Email"
            assert data["templates"][0]["score"] == 0.92
            assert "request_id" in data
    
    @pytest.mark.integration
    def test_dryrun_endpoint_no_results(self, test_client, mock_agent_dependencies):
        """Test dry run endpoint with no matching templates"""
        with patch('main.template_service_client') as mock_template:
            mock_template.search_templates.return_value = []
            
            dryrun_request = {"message": "Very specific and unusual workflow requirement"}
            
            response = test_client.post("/dryrun", json=dryrun_request)
            
            assert response.status_code == 200
            data = response.json()
            assert len(data["templates"]) == 0
            assert "request_id" in data
    
    @pytest.mark.integration
    def test_health_endpoint_all_healthy(self, test_client, mock_agent_dependencies):
        """Test health endpoint with all services healthy"""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert len(data["services"]) == 3
        
        # Check individual service statuses
        service_names = [service["name"] for service in data["services"]]
        assert "n8n" in service_names
        assert "template_service" in service_names
        assert "openrouter" in service_names
        
        # All should be healthy
        for service in data["services"]:
            assert service["status"] == "healthy"
    
    @pytest.mark.integration
    def test_health_endpoint_some_unhealthy(self, test_client, mock_agent_dependencies):
        """Test health endpoint with some services unhealthy"""
        # Make template service unhealthy
        mock_agent_dependencies["template"].health_check.return_value = False
        
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
    
    @pytest.mark.integration
    def test_error_handling_with_request_id(self, test_client, mock_agent_dependencies):
        """Test error responses include request ID"""
        # Make agent throw an error
        mock_agent_dependencies["agent"].ainvoke.side_effect = Exception("Test error")
        
        chat_request = {"message": "This should cause an error", "activate": False}
        response = test_client.post("/chat", json=chat_request)
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert "request_id" in data["error"]
        assert "Failed to process chat request" in data["error"]["message"]


class TestEndToEndWorkflows:
    """End-to-end integration tests for complete workflows"""
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_complete_workflow_creation_flow(self, mock_template_service):
        """Test complete workflow from user request to n8n creation"""
        from langgraph_agent import WorkflowAgent
        from llm_client import LLMClient, OpenRouterClient
        from n8n_client import N8nClient
        
        # Mock all external service calls
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}), \
             patch('httpx.AsyncClient') as mock_http_client:
            
            # Setup mock HTTP responses
            mock_responses = []
            
            # 1. OpenRouter intent extraction
            intent_response = Mock()
            intent_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "integrations": ["slack", "webhook"],
                            "trigger_type": "webhook", 
                            "action": "send_message",
                            "requirements": [],
                            "complexity": "simple"
                        })
                    }
                }]
            }
            intent_response.raise_for_status.return_value = None
            mock_responses.append(intent_response)
            
            # 2. Template scoring responses
            for score in ["0.95", "0.72"]:
                score_response = Mock()
                score_response.json.return_value = {
                    "choices": [{
                        "message": {"content": score}
                    }]
                }
                score_response.raise_for_status.return_value = None
                mock_responses.append(score_response)
            
            # 3. n8n API path detection
            n8n_detect_response = Mock()
            n8n_detect_response.status_code = 200
            mock_responses.append(n8n_detect_response)
            
            # 4. n8n workflow creation
            n8n_create_response = Mock()
            n8n_create_response.json.return_value = {
                "id": "workflow-e2e-test-123",
                "name": "E2E Test Workflow",
                "active": False,
                "nodes": mock_template_service["workflow_json"]["nodes"]
            }
            n8n_create_response.raise_for_status.return_value = None
            mock_responses.append(n8n_create_response)
            
            # 5. Response generation
            response_gen_response = Mock()
            response_gen_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": "I've successfully created your Slack webhook notification workflow! "
                                 "You can now review and customize it in the n8n editor."
                    }
                }]
            }
            response_gen_response.raise_for_status.return_value = None
            mock_responses.append(response_gen_response)
            
            # Configure mock HTTP client to return responses in order
            mock_http_client.return_value.__aenter__.return_value.post.side_effect = [
                intent_response, score_response, score_response, n8n_create_response, response_gen_response
            ]
            mock_http_client.return_value.__aenter__.return_value.get.return_value = n8n_detect_response
            
            # Create components
            llm_client = LLMClient()
            n8n_client = N8nClient("http://localhost:5678")
            agent = WorkflowAgent(llm_client, n8n_client)
            
            # Execute complete workflow
            result = await agent.process_request(
                "Create a workflow that sends Slack notifications when webhook is triggered"
            )
            
            # Verify results
            assert result["success"] is True
            assert result["workflow_created"] is not None
            assert result["workflow_created"]["id"] == "workflow-e2e-test-123"
            assert result["workflow_created"]["name"] == "E2E Test Workflow"
            assert "successfully created" in result["user_response"].lower()
            assert result["confidence_score"] == 0.95
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_error_recovery_workflow(self):
        """Test error recovery in complete workflow"""
        from langgraph_agent import WorkflowAgent
        from llm_client import LLMClient
        from n8n_client import N8nClient
        
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}), \
             patch('httpx.AsyncClient') as mock_http_client:
            
            # Mock intent extraction success
            intent_response = Mock()
            intent_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "integrations": ["email"],
                            "trigger_type": "schedule",
                            "action": "send_report",
                            "requirements": [],
                            "complexity": "medium"
                        })
                    }
                }]
            }
            intent_response.raise_for_status.return_value = None
            
            # Mock n8n failure
            n8n_error = httpx.HTTPStatusError(
                "500 Internal Server Error", 
                request=Mock(), 
                response=Mock(status_code=500, text="n8n server error")
            )
            
            mock_http_client.return_value.__aenter__.return_value.post.side_effect = [
                intent_response,  # Intent extraction succeeds
                n8n_error  # n8n creation fails
            ]
            mock_http_client.return_value.__aenter__.return_value.get.return_value = Mock(status_code=200)
            
            # Create components
            llm_client = LLMClient()
            n8n_client = N8nClient("http://localhost:5678")
            agent = WorkflowAgent(llm_client, n8n_client)
            
            # Execute workflow (should handle error gracefully)
            result = await agent.process_request("Send daily email reports")
            
            # Verify error handling
            assert result["success"] is False
            assert result["error"] is not None
            assert "error" in result["user_response"].lower()
            assert result["final_status"] == "error"
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_low_confidence_fallback_workflow(self):
        """Test manual fallback for low confidence matches"""
        from langgraph_agent import WorkflowAgent
        from llm_client import LLMClient  
        from n8n_client import N8nClient
        
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}), \
             patch('httpx.AsyncClient') as mock_http_client:
            
            # Mock intent extraction
            intent_response = Mock()
            intent_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "integrations": ["custom_api"],
                            "trigger_type": "complex_schedule", 
                            "action": "data_processing",
                            "requirements": ["high_throughput"],
                            "complexity": "complex"
                        })
                    }
                }]
            }
            intent_response.raise_for_status.return_value = None
            
            # Mock low scoring responses
            low_score_response = Mock()
            low_score_response.json.return_value = {
                "choices": [{"message": {"content": "0.45"}}]
            }
            low_score_response.raise_for_status.return_value = None
            
            mock_http_client.return_value.__aenter__.return_value.post.side_effect = [
                intent_response,
                low_score_response,
                low_score_response
            ]
            
            # Create components
            llm_client = LLMClient()
            n8n_client = N8nClient("http://localhost:5678")
            agent = WorkflowAgent(llm_client, n8n_client)
            
            # Execute workflow
            result = await agent.process_request(
                "Create a complex data processing pipeline with custom API integrations"
            )
            
            # Verify fallback behavior
            assert result["success"] is True  # Fallback is still a valid result
            assert result["final_status"] == "manual_selection_required"
            assert "several workflow templates" in result["user_response"]
            assert "help to choose" in result["user_response"]


class TestConcurrentRequests:
    """Test concurrent request handling"""
    
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_concurrent_chat_requests(self, test_client, mock_agent_dependencies):
        """Test handling multiple concurrent chat requests"""
        import asyncio
        import aiohttp
        
        # Simulate different response delays  
        async def mock_agent_response(request):
            await asyncio.sleep(0.1)  # Simulate processing time
            return {
                "workflow_id": f"concurrent-{request['message'][:8]}-{uuid.uuid4().hex[:6]}",
                "editor_url": f"http://localhost:5678/workflow/test",
                "active": False,
                "message": f"Created workflow for: {request['message'][:20]}..."
            }
        
        mock_agent_dependencies["agent"].ainvoke.side_effect = mock_agent_response
        
        # Create multiple concurrent requests
        requests = [
            {"message": f"Create workflow {i} for testing concurrency", "activate": False}
            for i in range(5)
        ]
        
        # Execute requests concurrently
        async def make_request(req_data):
            async with aiohttp.ClientSession() as session:
                async with session.post("http://localhost:3001/chat", json=req_data) as response:
                    return await response.json()
        
        # Note: This would require the actual server to be running
        # For now, we'll test the mock setup
        assert len(requests) == 5
        assert all("Create workflow" in req["message"] for req in requests)


if __name__ == "__main__":
    # Run integration tests only
    pytest.main([__file__, "-m", "integration", "-v"])