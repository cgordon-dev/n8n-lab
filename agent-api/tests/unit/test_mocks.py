#!/usr/bin/env python3
"""
Mock Tests for External Service Dependencies

Tests mocking functionality for LLM, n8n, and template services.
Run with: pytest test_mocks.py -v
"""

import asyncio
import json
import os
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List

import httpx
import pytest
from faker import Faker

# Import modules under test
from llm_client import LLMClient, OpenRouterClient
from n8n_client import N8nClient
from langgraph_agent import WorkflowAgent, create_workflow_agent
from main import TemplateServiceClient

fake = Faker()


class TestLLMClientMocking:
    """Test LLM client with comprehensive mocking"""
    
    @pytest.fixture
    def mock_openrouter_responses(self):
        """Fixture providing various mock OpenRouter responses"""
        return {
            "chat_completion": {
                "choices": [{
                    "message": {
                        "content": "This is a mocked chat completion response"
                    }
                }],
                "usage": {"total_tokens": 50}
            },
            "intent_extraction": {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "integrations": ["slack", "webhook"],
                            "trigger_type": "webhook",
                            "action": "send notification",
                            "requirements": ["real-time"]
                        })
                    }
                }]
            },
            "template_scoring": {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "score": 88,
                            "reasoning": "Excellent match for requirements"
                        })
                    }
                }]
            },
            "response_generation": {
                "choices": [{
                    "message": {
                        "content": "I've successfully created your workflow! You can now customize it in the n8n editor."
                    }
                }]
            }
        }
    
    @pytest.mark.asyncio
    async def test_llm_client_with_mock_responses(self, mock_openrouter_responses):
        """Test LLM client with various mocked responses"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key-mock'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            # Setup mock HTTP client
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # Test chat completion
            mock_response = Mock()
            mock_response.json.return_value = mock_openrouter_responses["chat_completion"]
            mock_response.raise_for_status.return_value = None
            async_context.post.return_value = mock_response
            
            client = LLMClient()
            result = await client.generate_text("Hello, this is a test message")
            
            assert "mocked chat completion response" in result
            
            # Verify HTTP call was made correctly
            async_context.post.assert_called_once()
            call_args = async_context.post.call_args
            assert "https://openrouter.ai/api/v1/chat/completions" in str(call_args)
    
    @pytest.mark.asyncio
    async def test_openrouter_intent_extraction_mock(self, mock_openrouter_responses):
        """Test intent extraction with mocked OpenRouter response"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key-mock'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            # Setup mock
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            mock_response = Mock()
            mock_response.json.return_value = mock_openrouter_responses["intent_extraction"]
            mock_response.raise_for_status.return_value = None
            async_context.post.return_value = mock_response
            
            client = OpenRouterClient()
            result = await client.extract_intent("Send Slack notifications via webhook")
            
            assert result["integrations"] == ["slack", "webhook"]
            assert result["trigger_type"] == "webhook"
            assert result["action"] == "send notification"
            assert "real-time" in result["requirements"]
    
    @pytest.mark.asyncio
    async def test_openrouter_template_scoring_mock(self, mock_openrouter_responses):
        """Test template scoring with mocked response"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key-mock'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            # Setup mock
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            mock_response = Mock()
            mock_response.json.return_value = mock_openrouter_responses["template_scoring"]
            mock_response.raise_for_status.return_value = None
            async_context.post.return_value = mock_response
            
            client = OpenRouterClient()
            score = await client.score_template_match(
                "Send notifications to Slack",
                "Slack Notification System",
                ["slack", "notifications"],
                "webhook"
            )
            
            assert score == 88.0
    
    @pytest.mark.asyncio
    async def test_openrouter_error_handling_mock(self):
        """Test OpenRouter error handling with mocked errors"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key-mock'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            # Setup mock to raise HTTP error
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            
            http_error = httpx.HTTPStatusError(
                "401 Unauthorized",
                request=Mock(),
                response=mock_response
            )
            async_context.post.return_value.raise_for_status.side_effect = http_error
            
            client = OpenRouterClient()
            
            with pytest.raises(httpx.HTTPStatusError):
                await client.chat_completion([{"role": "user", "content": "test"}])
    
    @pytest.mark.asyncio
    async def test_openrouter_retry_logic_mock(self):
        """Test OpenRouter retry logic with mocked failures and success"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key-mock'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            # Setup mock to fail twice, then succeed
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # First two calls fail, third succeeds
            failure_response = Mock()
            failure_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "500 Internal Server Error",
                request=Mock(),
                response=Mock(status_code=500, text="Server error")
            )
            
            success_response = Mock()
            success_response.json.return_value = {
                "choices": [{"message": {"content": "Success after retries"}}]
            }
            success_response.raise_for_status.return_value = None
            
            async_context.post.side_effect = [failure_response, failure_response, success_response]
            
            client = OpenRouterClient()
            result = await client.chat_completion([{"role": "user", "content": "test retry"}])
            
            assert result["choices"][0]["message"]["content"] == "Success after retries"
            assert async_context.post.call_count == 3  # Should have retried twice


class TestN8nClientMocking:
    """Test n8n client with comprehensive mocking"""
    
    @pytest.fixture
    def mock_n8n_responses(self):
        """Fixture providing various mock n8n responses"""
        return {
            "workflow_creation": {
                "id": "mock-workflow-123",
                "name": "Mock Test Workflow",
                "active": False,
                "nodes": [
                    {
                        "id": "trigger",
                        "type": "n8n-nodes-base.webhook",
                        "position": [240, 300]
                    },
                    {
                        "id": "action",
                        "type": "n8n-nodes-base.slack",
                        "position": [460, 300]
                    }
                ],
                "connections": {
                    "trigger": {
                        "main": [[{"node": "action", "type": "main", "index": 0}]]
                    }
                }
            },
            "workflow_list": [
                {"id": "1", "name": "Mock Workflow 1", "active": True},
                {"id": "2", "name": "Mock Workflow 2", "active": False},
                {"id": "3", "name": "Mock Workflow 3", "active": True}
            ],
            "workflow_detail": {
                "id": "detail-workflow-456",
                "name": "Detailed Mock Workflow",
                "active": True,
                "nodes": [],
                "connections": {}
            }
        }
    
    @pytest.mark.asyncio
    async def test_n8n_client_workflow_creation_mock(self, mock_n8n_responses):
        """Test n8n workflow creation with mocked response"""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock HTTP client
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # Mock API path detection
            api_detect_response = Mock()
            api_detect_response.status_code = 200
            async_context.get.return_value = api_detect_response
            
            # Mock workflow creation
            create_response = Mock()
            create_response.json.return_value = mock_n8n_responses["workflow_creation"]
            create_response.raise_for_status.return_value = None
            async_context.post.return_value = create_response
            
            client = N8nClient("http://mock-n8n:5678")
            
            test_workflow = {
                "name": "Test Workflow",
                "nodes": [{"id": "test", "type": "test-node"}],
                "connections": {}
            }
            
            result = await client.create_workflow(test_workflow, activate=False)
            
            assert result["id"] == "mock-workflow-123"
            assert result["name"] == "Mock Test Workflow"
            assert result["active"] is False
            assert "editorUrl" in result
            assert len(result["nodes"]) == 2
    
    @pytest.mark.asyncio
    async def test_n8n_client_list_workflows_mock(self, mock_n8n_responses):
        """Test n8n workflow listing with mocked response"""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock HTTP client
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # Mock API path detection and list workflows
            async_context.get.side_effect = [
                Mock(status_code=200),  # API detection
                Mock(
                    json=lambda: mock_n8n_responses["workflow_list"],
                    raise_for_status=lambda: None
                )  # List workflows
            ]
            
            client = N8nClient("http://mock-n8n:5678")
            result = await client.list_workflows()
            
            assert len(result) == 3
            assert result[0]["name"] == "Mock Workflow 1"
            assert result[1]["active"] is False
            assert result[2]["id"] == "3"
    
    @pytest.mark.asyncio
    async def test_n8n_client_api_path_detection_mock(self):
        """Test n8n API path detection with mocked responses"""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock HTTP client
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # Test /api/v1 path detection
            async_context.get.return_value = Mock(status_code=200)
            
            client = N8nClient("http://mock-n8n:5678")
            api_path = await client.detect_api_path()
            
            assert api_path == "/api/v1"
            assert client.api_path == "/api/v1"
            
            # Test /rest path fallback
            client.api_path = None  # Reset
            async_context.get.side_effect = [
                httpx.RequestError("Connection failed"),  # /api/v1 fails
                Mock(status_code=200)  # /rest succeeds
            ]
            
            api_path = await client.detect_api_path()
            
            assert api_path == "/rest"
            assert client.api_path == "/rest"
    
    @pytest.mark.asyncio
    async def test_n8n_client_error_handling_mock(self):
        """Test n8n client error handling with mocked errors"""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock HTTP client
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # Mock API detection success
            async_context.get.return_value = Mock(status_code=200)
            
            # Mock workflow creation failure
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = "Bad request - invalid workflow"
            
            http_error = httpx.HTTPStatusError(
                "400 Bad Request",
                request=Mock(),
                response=mock_response
            )
            async_context.post.return_value.raise_for_status.side_effect = http_error
            
            client = N8nClient("http://mock-n8n:5678")
            
            with pytest.raises(Exception, match="n8n API error: 400"):
                await client.create_workflow({"name": "Invalid Workflow"})
    
    @pytest.mark.asyncio
    async def test_n8n_client_activation_mock(self):
        """Test n8n workflow activation with mocked response"""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock HTTP client
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # Mock API detection and activation
            async_context.get.return_value = Mock(status_code=200)
            
            activation_response = Mock()
            activation_response.raise_for_status.return_value = None
            async_context.patch.return_value = activation_response
            
            client = N8nClient("http://mock-n8n:5678")
            result = await client.activate_workflow("test-workflow-123")
            
            assert result is True
            
            # Verify patch request was made
            async_context.patch.assert_called_once()
            call_args = async_context.patch.call_args
            assert "test-workflow-123" in str(call_args[0][0])
    
    @pytest.mark.asyncio
    async def test_n8n_client_connection_test_mock(self):
        """Test n8n connection test with mocked response"""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock HTTP client
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # Mock successful connection test
            async_context.get.side_effect = [
                Mock(status_code=200),  # API detection
                Mock(
                    json=lambda: [],
                    raise_for_status=lambda: None
                )  # List workflows
            ]
            
            client = N8nClient("http://mock-n8n:5678")
            result = await client.test_connection()
            
            assert result is True
            
            # Test connection failure
            client.api_path = None  # Reset
            async_context.get.side_effect = Exception("Connection failed")
            
            result = await client.test_connection()
            assert result is False


class TestTemplateServiceMocking:
    """Test template service client with comprehensive mocking"""
    
    @pytest.fixture
    def mock_template_responses(self):
        """Fixture providing various mock template service responses"""
        return {
            "search_results": {
                "results": [
                    {
                        "id": "template-001",
                        "name": "Slack Webhook Integration",
                        "score": 0.95,
                        "description": "Send Slack messages via webhooks"
                    },
                    {
                        "id": "template-002",
                        "name": "Email Automation",
                        "score": 0.82,
                        "description": "Automated email processing and responses"
                    },
                    {
                        "id": "template-003",
                        "name": "Discord Notifications",
                        "score": 0.76,
                        "description": "Send notifications to Discord channels"
                    }
                ]
            },
            "template_detail": {
                "id": "template-001",
                "name": "Slack Webhook Integration",
                "version": "1.2.0",
                "workflow": {
                    "nodes": [
                        {
                            "id": "webhook-trigger",
                            "type": "n8n-nodes-base.webhook",
                            "parameters": {"path": "slack-webhook"}
                        },
                        {
                            "id": "slack-sender",
                            "type": "n8n-nodes-base.slack",
                            "parameters": {"channel": "#general"}
                        }
                    ],
                    "connections": {
                        "webhook-trigger": {
                            "main": [[{"node": "slack-sender", "type": "main", "index": 0}]]
                        }
                    }
                },
                "metadata": {
                    "category": "messaging",
                    "tags": ["slack", "webhook", "notifications"]
                }
            },
            "empty_results": {
                "results": []
            }
        }
    
    @pytest.mark.asyncio
    async def test_template_service_search_mock(self, mock_template_responses):
        """Test template service search with mocked response"""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock HTTP client
            mock_response = Mock()
            mock_response.json.return_value = mock_template_responses["search_results"]
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            client = TemplateServiceClient("http://mock-template-service:8000")
            results = await client.search_templates("slack webhook integration")
            
            assert len(results) == 3
            assert results[0].id == "template-001"
            assert results[0].name == "Slack Webhook Integration"
            assert results[0].score == 0.95
            assert results[1].score == 0.82
            assert results[2].score == 0.76
    
    @pytest.mark.asyncio
    async def test_template_service_fetch_mock(self, mock_template_responses):
        """Test template service fetch with mocked response"""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock HTTP client
            mock_response = Mock()
            mock_response.json.return_value = mock_template_responses["template_detail"]
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            client = TemplateServiceClient("http://mock-template-service:8000")
            result = await client.fetch_template("template-001")
            
            assert result["id"] == "template-001"
            assert result["name"] == "Slack Webhook Integration"
            assert result["version"] == "1.2.0"
            assert "workflow" in result
            assert len(result["workflow"]["nodes"]) == 2
            assert "metadata" in result
    
    @pytest.mark.asyncio
    async def test_template_service_empty_results_mock(self, mock_template_responses):
        """Test template service with no results"""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock HTTP client for empty results
            mock_response = Mock()
            mock_response.json.return_value = mock_template_responses["empty_results"]
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            client = TemplateServiceClient("http://mock-template-service:8000")
            results = await client.search_templates("nonexistent template type")
            
            assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_template_service_error_mock(self):
        """Test template service error handling"""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock HTTP client to raise error
            http_error = httpx.HTTPStatusError(
                "503 Service Unavailable",
                request=Mock(),
                response=Mock(status_code=503, text="Template service down")
            )
            mock_client.return_value.__aenter__.return_value.post.return_value.raise_for_status.side_effect = http_error
            
            client = TemplateServiceClient("http://mock-template-service:8000")
            
            with pytest.raises(Exception, match="Template service unavailable"):
                await client.search_templates("test query")
    
    @pytest.mark.asyncio
    async def test_template_service_health_check_mock(self):
        """Test template service health check with mocked response"""
        with patch('httpx.AsyncClient') as mock_client:
            # Setup mock HTTP client for successful health check
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            client = TemplateServiceClient("http://mock-template-service:8000")
            result = await client.health_check()
            
            assert result is True
            
            # Test health check failure
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.ConnectError("Connection failed")
            
            result = await client.health_check()
            assert result is False


class TestWorkflowAgentMocking:
    """Test workflow agent with comprehensive service mocking"""
    
    @pytest.fixture
    def fully_mocked_agent(self):
        """Create workflow agent with fully mocked dependencies"""
        # Mock LLM client
        mock_llm = Mock(spec=LLMClient)
        mock_llm.generate_text = AsyncMock()
        
        # Mock n8n client
        mock_n8n = Mock(spec=N8nClient)
        mock_n8n.create_workflow = AsyncMock()
        mock_n8n.base_url = "http://mock-n8n:5678"
        
        agent = WorkflowAgent(mock_llm, mock_n8n)
        
        return agent, mock_llm, mock_n8n
    
    @pytest.mark.asyncio
    async def test_workflow_agent_complete_flow_mock(self, fully_mocked_agent):
        """Test complete workflow agent flow with all services mocked"""
        agent, mock_llm, mock_n8n = fully_mocked_agent
        
        # Setup mock responses in sequence
        mock_llm.generate_text.side_effect = [
            # 1. Intent parsing
            json.dumps({
                "integrations": ["slack", "webhook"],
                "trigger_type": "webhook",
                "action": "send_message",
                "requirements": [],
                "complexity": "simple"
            }),
            # 2. Template scoring (first template)
            "0.92",
            # 3. Template scoring (second template)
            "0.75",
            # 4. Response generation
            "I've successfully created your Slack webhook notification workflow!"
        ]
        
        # Setup n8n workflow creation mock
        mock_n8n.create_workflow.return_value = {
            "id": "mock-workflow-789",
            "name": "Mock Created Workflow",
            "active": False
        }
        
        # Execute agent workflow
        result = await agent.process_request(
            "Create a workflow that sends Slack notifications when webhook is triggered"
        )
        
        # Verify results
        assert result["success"] is True
        assert result["workflow_created"] is not None
        assert result["workflow_created"]["id"] == "mock-workflow-789"
        assert result["confidence_score"] == 0.92
        assert "successfully created" in result["user_response"].lower()
        
        # Verify mock calls
        assert mock_llm.generate_text.call_count == 4
        mock_n8n.create_workflow.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_workflow_agent_error_handling_mock(self, fully_mocked_agent):
        """Test workflow agent error handling with mocked failures"""
        agent, mock_llm, mock_n8n = fully_mocked_agent
        
        # Setup mock to fail at intent parsing
        mock_llm.generate_text.side_effect = Exception("LLM service unavailable")
        
        # Execute agent workflow
        result = await agent.process_request("This should fail during intent parsing")
        
        # Verify error handling
        assert result["success"] is False
        assert "error" in result
        assert "LLM service unavailable" in result["error"]
        assert result["final_status"] == "error"
    
    @pytest.mark.asyncio
    async def test_workflow_agent_low_confidence_mock(self, fully_mocked_agent):
        """Test workflow agent low confidence scenario with mocked responses"""
        agent, mock_llm, mock_n8n = fully_mocked_agent
        
        # Setup mock responses for low confidence scenario
        mock_llm.generate_text.side_effect = [
            # Intent parsing
            json.dumps({
                "integrations": ["custom_api"],
                "trigger_type": "complex_schedule",
                "action": "data_processing",
                "requirements": ["high_throughput"],
                "complexity": "complex"
            }),
            # Low scoring for templates
            "0.45",
            "0.38"
        ]
        
        # Execute agent workflow
        result = await agent.process_request(
            "Create a complex data processing pipeline with custom APIs"
        )
        
        # Verify fallback behavior
        assert result["success"] is True  # Fallback is still successful
        assert result["final_status"] == "manual_selection_required"
        assert "several workflow templates" in result["user_response"]
        assert result["confidence_score"] == 0.45  # Best score from low options
    
    @pytest.mark.asyncio
    async def test_workflow_agent_retry_logic_mock(self, fully_mocked_agent):
        """Test workflow agent retry logic with mocked failures"""
        agent, mock_llm, mock_n8n = fully_mocked_agent
        
        # Setup successful intent parsing
        mock_llm.generate_text.side_effect = [
            json.dumps({
                "integrations": ["email"],
                "trigger_type": "schedule",
                "action": "send_report",
                "requirements": [],
                "complexity": "simple"
            }),
            "0.85"  # Good score
        ]
        
        # Setup n8n to fail twice, then succeed
        mock_n8n.create_workflow.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            {
                "id": "retry-success-workflow",
                "name": "Retry Success Workflow",
                "active": False
            }
        ]
        
        # Add response generation
        mock_llm.generate_text.side_effect.append("Workflow created after retries!")
        
        # Execute agent workflow
        result = await agent.process_request("Send daily email reports")
        
        # Verify retry worked
        assert result["success"] is True
        assert result["workflow_created"]["id"] == "retry-success-workflow"
        assert mock_n8n.create_workflow.call_count == 3  # Should have retried twice


if __name__ == "__main__":
    pytest.main([__file__, "-v"])