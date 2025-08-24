#!/usr/bin/env python3
"""
Complete Integration Tests for n8n Workflow Agent System

End-to-end integration tests that validate the complete flow from user request
to workflow creation, including all service interactions.
Run with: pytest test_complete_integration.py -v --asyncio-mode=auto
"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from typing import Dict, Any, List

import httpx
import pytest
from faker import Faker
from fastapi.testclient import TestClient

# Import the complete system
from main import app
from llm_client import LLMClient, OpenRouterClient
from n8n_client import N8nClient
from langgraph_agent import WorkflowAgent, create_workflow_agent
from main import TemplateServiceClient, TemplateMatch

fake = Faker()


class TestCompleteWorkflowIntegration:
    """Complete end-to-end integration tests"""
    
    @pytest.fixture
    def integration_test_data(self):
        """Comprehensive test data for integration scenarios"""
        return {
            "user_requests": [
                "Create a workflow that sends Slack notifications when webhook is triggered",
                "Set up automated email reports sent daily at 9 AM",
                "Build a Discord bot that responds to mentions with custom messages",
                "Process customer feedback forms and save to database",
                "Monitor website uptime and alert team via multiple channels"
            ],
            "expected_intents": [
                {
                    "integrations": ["slack", "webhook"],
                    "trigger_type": "webhook",
                    "action": "send_notification",
                    "requirements": ["real-time"],
                    "complexity": "simple"
                },
                {
                    "integrations": ["email", "schedule"],
                    "trigger_type": "schedule",
                    "action": "send_report",
                    "requirements": ["daily", "9am"],
                    "complexity": "medium"
                },
                {
                    "integrations": ["discord", "bot"],
                    "trigger_type": "mention",
                    "action": "respond_message",
                    "requirements": ["custom_responses"],
                    "complexity": "medium"
                },
                {
                    "integrations": ["form", "database"],
                    "trigger_type": "form_submission",
                    "action": "save_data",
                    "requirements": ["data_validation"],
                    "complexity": "medium"
                },
                {
                    "integrations": ["monitoring", "alert", "multi_channel"],
                    "trigger_type": "schedule",
                    "action": "check_uptime_alert",
                    "requirements": ["multi_channel", "monitoring"],
                    "complexity": "complex"
                }
            ],
            "mock_templates": [
                {
                    "id": "slack-webhook-001",
                    "name": "Slack Webhook Notifier",
                    "score": 0.95,
                    "description": "Send Slack notifications via webhook triggers",
                    "workflow": {
                        "nodes": [
                            {
                                "id": "webhook-trigger",
                                "type": "n8n-nodes-base.webhook",
                                "parameters": {"path": "slack-notification"}
                            },
                            {
                                "id": "slack-message",
                                "type": "n8n-nodes-base.slack",
                                "parameters": {"channel": "#alerts"}
                            }
                        ],
                        "connections": {
                            "webhook-trigger": {
                                "main": [[{"node": "slack-message", "type": "main", "index": 0}]]
                            }
                        }
                    }
                },
                {
                    "id": "email-scheduler-002",
                    "name": "Daily Email Reports",
                    "score": 0.88,
                    "description": "Automated daily email report generation",
                    "workflow": {
                        "nodes": [
                            {
                                "id": "schedule-trigger",
                                "type": "n8n-nodes-base.cron",
                                "parameters": {"cronExpression": "0 9 * * *"}
                            },
                            {
                                "id": "email-sender",
                                "type": "n8n-nodes-base.emailSend",
                                "parameters": {"subject": "Daily Report"}
                            }
                        ],
                        "connections": {
                            "schedule-trigger": {
                                "main": [[{"node": "email-sender", "type": "main", "index": 0}]]
                            }
                        }
                    }
                },
                {
                    "id": "discord-bot-003", 
                    "name": "Discord Mention Bot",
                    "score": 0.82,
                    "description": "Discord bot with custom message responses",
                    "workflow": {
                        "nodes": [
                            {
                                "id": "discord-trigger",
                                "type": "n8n-nodes-base.discordTrigger",
                                "parameters": {"events": ["mention"]}
                            },
                            {
                                "id": "discord-response",
                                "type": "n8n-nodes-base.discord",
                                "parameters": {"operation": "sendMessage"}
                            }
                        ],
                        "connections": {
                            "discord-trigger": {
                                "main": [[{"node": "discord-response", "type": "main", "index": 0}]]
                            }
                        }
                    }
                }
            ],
            "expected_n8n_responses": [
                {
                    "id": "workflow-integration-001",
                    "name": "Slack Webhook Notifier",
                    "active": False,
                    "editorUrl": "http://n8n.localhost/workflow/workflow-integration-001"
                },
                {
                    "id": "workflow-integration-002",
                    "name": "Daily Email Reports",
                    "active": False,
                    "editorUrl": "http://n8n.localhost/workflow/workflow-integration-002"
                },
                {
                    "id": "workflow-integration-003",
                    "name": "Discord Mention Bot",
                    "active": False,
                    "editorUrl": "http://n8n.localhost/workflow/workflow-integration-003"
                }
            ]
        }
    
    @pytest.mark.asyncio
    async def test_complete_slack_workflow_creation(self, integration_test_data):
        """Test complete workflow creation for Slack notification scenario"""
        test_case_index = 0  # Slack webhook scenario
        
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-integration-key'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            # Setup comprehensive mock responses
            mock_responses = []
            
            # 1. Intent extraction response
            intent_response = Mock()
            intent_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps(integration_test_data["expected_intents"][test_case_index])
                    }
                }]
            }
            intent_response.raise_for_status.return_value = None
            mock_responses.append(intent_response)
            
            # 2. Template scoring responses (assume 2 templates to score)
            for score in ["0.95", "0.72"]:
                score_response = Mock()
                score_response.json.return_value = {
                    "choices": [{"message": {"content": score}}]
                }
                score_response.raise_for_status.return_value = None
                mock_responses.append(score_response)
            
            # 3. n8n API path detection
            n8n_detect_response = Mock()
            n8n_detect_response.status_code = 200
            mock_responses.append(n8n_detect_response)
            
            # 4. n8n workflow creation
            n8n_create_response = Mock()
            n8n_create_response.json.return_value = integration_test_data["expected_n8n_responses"][test_case_index]
            n8n_create_response.raise_for_status.return_value = None
            mock_responses.append(n8n_create_response)
            
            # 5. Response generation
            response_gen = Mock()
            response_gen.json.return_value = {
                "choices": [{
                    "message": {
                        "content": "Perfect! I've created your Slack webhook notification workflow. "
                                 "It's ready for you to review and customize in the n8n editor."
                    }
                }]
            }
            response_gen.raise_for_status.return_value = None
            mock_responses.append(response_gen)
            
            # Configure HTTP client mock
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # POST requests (LLM calls, n8n workflow creation)
            async_context.post.side_effect = [intent_response, score_response, score_response, n8n_create_response, response_gen]
            
            # GET requests (n8n API detection)
            async_context.get.return_value = n8n_detect_response
            
            # Create components
            llm_client = LLMClient()
            n8n_client = N8nClient("http://localhost:5678")
            agent = create_workflow_agent(llm_client, n8n_client)
            
            # Execute complete workflow
            result = await agent.process_request(integration_test_data["user_requests"][test_case_index])
            
            # Comprehensive verification
            assert result["success"] is True
            assert result["workflow_created"] is not None
            assert result["workflow_created"]["id"] == "workflow-integration-001"
            assert result["workflow_created"]["name"] == "Slack Webhook Notifier"
            assert result["confidence_score"] == 0.95
            assert "Perfect! I've created your Slack webhook" in result["user_response"]
            assert result["final_status"] == "completed"
            
            # Verify all service calls were made
            assert async_context.post.call_count == 5  # Intent + 2 scores + n8n creation + response
            assert async_context.get.call_count == 1   # API detection
    
    @pytest.mark.asyncio
    async def test_complete_email_workflow_creation(self, integration_test_data):
        """Test complete workflow creation for email report scenario"""
        test_case_index = 1  # Email reports scenario
        
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-integration-key'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            # Setup mock responses for email scenario
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # Intent extraction
            intent_response = Mock()
            intent_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps(integration_test_data["expected_intents"][test_case_index])
                    }
                }]
            }
            intent_response.raise_for_status.return_value = None
            
            # Template scoring
            score_response = Mock()
            score_response.json.return_value = {
                "choices": [{"message": {"content": "0.88"}}]
            }
            score_response.raise_for_status.return_value = None
            
            # n8n responses
            n8n_detect_response = Mock(status_code=200)
            n8n_create_response = Mock()
            n8n_create_response.json.return_value = integration_test_data["expected_n8n_responses"][test_case_index]
            n8n_create_response.raise_for_status.return_value = None
            
            # Response generation
            response_gen = Mock()
            response_gen.json.return_value = {
                "choices": [{
                    "message": {
                        "content": "Excellent! Your daily email report workflow is now set up. "
                                 "It will automatically send reports every day at 9 AM."
                    }
                }]
            }
            response_gen.raise_for_status.return_value = None
            
            # Configure mocks
            async_context.post.side_effect = [intent_response, score_response, n8n_create_response, response_gen]
            async_context.get.return_value = n8n_detect_response
            
            # Create and execute
            llm_client = LLMClient()
            n8n_client = N8nClient("http://localhost:5678")
            agent = create_workflow_agent(llm_client, n8n_client)
            
            result = await agent.process_request(integration_test_data["user_requests"][test_case_index])
            
            # Verify email-specific results
            assert result["success"] is True
            assert result["workflow_created"]["id"] == "workflow-integration-002"
            assert result["workflow_created"]["name"] == "Daily Email Reports"
            assert result["confidence_score"] == 0.88
            assert "daily email report" in result["user_response"].lower()
            assert "9 AM" in result["user_response"] or "9am" in result["user_response"].lower()
    
    @pytest.mark.asyncio
    async def test_complete_workflow_with_low_confidence_fallback(self, integration_test_data):
        """Test complete workflow that falls back to manual selection due to low confidence"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-integration-key'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # Intent extraction for complex scenario
            intent_response = Mock()
            intent_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps({
                            "integrations": ["custom_api", "complex_processing"],
                            "trigger_type": "complex_event",
                            "action": "multi_step_processing",
                            "requirements": ["high_complexity", "custom_logic"],
                            "complexity": "complex"
                        })
                    }
                }]
            }
            intent_response.raise_for_status.return_value = None
            
            # Low confidence scores for all templates
            low_score_responses = []
            for score in ["0.45", "0.38", "0.42"]:
                score_response = Mock()
                score_response.json.return_value = {
                    "choices": [{"message": {"content": score}}]
                }
                score_response.raise_for_status.return_value = None
                low_score_responses.append(score_response)
            
            # Configure mocks
            async_context.post.side_effect = [intent_response] + low_score_responses
            
            # Create and execute
            llm_client = LLMClient()
            n8n_client = N8nClient("http://localhost:5678")
            agent = create_workflow_agent(llm_client, n8n_client)
            
            result = await agent.process_request(
                "Create a highly complex workflow with custom API integrations and multi-step data processing"
            )
            
            # Verify fallback behavior
            assert result["success"] is True  # Fallback is still a valid outcome
            assert result["final_status"] == "manual_selection_required"
            assert result["confidence_score"] == 0.45  # Best of the low scores
            assert "several workflow templates" in result["user_response"]
            assert "help to choose" in result["user_response"] or "manual" in result["user_response"]
    
    @pytest.mark.asyncio
    async def test_complete_workflow_with_error_recovery(self, integration_test_data):
        """Test complete workflow with error recovery scenarios"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-integration-key'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # Successful intent extraction
            intent_response = Mock()
            intent_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps(integration_test_data["expected_intents"][0])  # Slack scenario
                    }
                }]
            }
            intent_response.raise_for_status.return_value = None
            
            # Successful scoring
            score_response = Mock()
            score_response.json.return_value = {
                "choices": [{"message": {"content": "0.92"}}]
            }
            score_response.raise_for_status.return_value = None
            
            # n8n API detection succeeds
            n8n_detect_response = Mock(status_code=200)
            
            # n8n workflow creation fails with server error
            n8n_error_response = Mock()
            n8n_error_response.status_code = 500
            n8n_error_response.text = "Internal server error"
            n8n_http_error = httpx.HTTPStatusError(
                "500 Internal Server Error",
                request=Mock(),
                response=n8n_error_response
            )
            n8n_error_response.raise_for_status.side_effect = n8n_http_error
            
            # Configure mocks
            async_context.post.side_effect = [intent_response, score_response, n8n_error_response]
            async_context.get.return_value = n8n_detect_response
            
            # Create and execute
            llm_client = LLMClient()
            n8n_client = N8nClient("http://localhost:5678")
            agent = create_workflow_agent(llm_client, n8n_client)
            
            result = await agent.process_request(integration_test_data["user_requests"][0])
            
            # Verify error handling
            assert result["success"] is False
            assert result["final_status"] == "error"
            assert "error" in result
            assert "500" in result["error"] or "server error" in result["error"].lower()
            assert "encountered an issue" in result["user_response"].lower()
    
    @pytest.mark.asyncio
    async def test_complete_workflow_with_retry_success(self, integration_test_data):
        """Test complete workflow with successful retry after initial failure"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-integration-key'}), \
             patch('httpx.AsyncClient') as mock_client:
            
            async_context = MagicMock()
            mock_client.return_value.__aenter__.return_value = async_context
            
            # Successful intent and scoring
            intent_response = Mock()
            intent_response.json.return_value = {
                "choices": [{
                    "message": {
                        "content": json.dumps(integration_test_data["expected_intents"][0])
                    }
                }]
            }
            intent_response.raise_for_status.return_value = None
            
            score_response = Mock()
            score_response.json.return_value = {
                "choices": [{"message": {"content": "0.91"}}]
            }
            score_response.raise_for_status.return_value = None
            
            # n8n API detection
            n8n_detect_response = Mock(status_code=200)
            
            # n8n workflow creation: first fails, second succeeds
            n8n_failure_response = Mock()
            n8n_failure_response.status_code = 503
            n8n_failure_response.text = "Service temporarily unavailable"
            n8n_failure_error = httpx.HTTPStatusError(
                "503 Service Unavailable",
                request=Mock(),
                response=n8n_failure_response
            )
            n8n_failure_response.raise_for_status.side_effect = n8n_failure_error
            
            n8n_success_response = Mock()
            n8n_success_response.json.return_value = {
                "id": "retry-success-workflow-123",
                "name": "Retry Success Workflow",
                "active": False,
                "editorUrl": "http://n8n.localhost/workflow/retry-success-workflow-123"
            }
            n8n_success_response.raise_for_status.return_value = None
            
            # Response generation
            response_gen = Mock()
            response_gen.json.return_value = {
                "choices": [{
                    "message": {
                        "content": "Great! After a brief delay, your workflow has been successfully created."
                    }
                }]
            }
            response_gen.raise_for_status.return_value = None
            
            # Configure mocks (failure then success)
            async_context.post.side_effect = [
                intent_response, score_response, n8n_failure_response, n8n_success_response, response_gen
            ]
            async_context.get.return_value = n8n_detect_response
            
            # Create and execute
            llm_client = LLMClient()
            n8n_client = N8nClient("http://localhost:5678")
            agent = create_workflow_agent(llm_client, n8n_client)
            
            result = await agent.process_request(integration_test_data["user_requests"][0])
            
            # Verify successful retry
            assert result["success"] is True
            assert result["workflow_created"]["id"] == "retry-success-workflow-123"
            assert result["final_status"] == "completed"
            assert "successfully created" in result["user_response"].lower()
            
            # Verify retry occurred (should have 2 n8n creation attempts)
            post_calls = [call for call in async_context.post.call_args_list]
            n8n_creation_calls = [call for call in post_calls if "workflows" in str(call)]
            assert len(n8n_creation_calls) >= 2  # At least one retry


class TestFastAPICompleteIntegration:
    """Complete FastAPI endpoint integration tests"""
    
    @pytest.fixture
    def test_client(self):
        """Create test client"""
        return TestClient(app)
    
    @pytest.fixture
    def full_system_mocks(self):
        """Setup complete system mocks for FastAPI testing"""
        with patch('main.n8n_client') as mock_n8n, \
             patch('main.llm_client') as mock_llm, \
             patch('main.template_service_client') as mock_template, \
             patch('main.agent_graph') as mock_agent:
            
            # Setup comprehensive mocks
            mock_n8n.list_workflows = AsyncMock(return_value=[
                {"id": "existing-1", "name": "Existing Workflow 1", "active": True},
                {"id": "existing-2", "name": "Existing Workflow 2", "active": False}
            ])
            
            mock_llm.list_models = AsyncMock(return_value=[
                "openai/gpt-3.5-turbo", "openai/gpt-4", "anthropic/claude-2"
            ])
            
            mock_template.health_check = AsyncMock(return_value=True)
            mock_template.search_templates = AsyncMock(return_value=[
                TemplateMatch(
                    id="integration-template-001",
                    name="Complete Integration Template",
                    score=0.94,
                    description="Template for complete integration testing"
                )
            ])
            
            mock_agent.process_request = AsyncMock(return_value={
                "success": True,
                "user_response": "Integration test: Workflow created successfully with all services coordinated!",
                "workflow_created": {
                    "id": "fastapi-integration-workflow-456",
                    "url": "http://localhost:5678/workflow/fastapi-integration-workflow-456",
                    "active": False
                },
                "confidence_score": 0.94,
                "final_status": "completed"
            })
            
            yield {
                "n8n": mock_n8n,
                "llm": mock_llm,
                "template": mock_template,
                "agent": mock_agent
            }
    
    def test_complete_chat_workflow_via_api(self, test_client, full_system_mocks):
        """Test complete chat workflow through FastAPI endpoint"""
        request_data = {
            "message": "Create a comprehensive integration test workflow with multiple services",
            "activate": False
        }
        
        response = test_client.post("/chat", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "workflow_id" in data
        assert "editor_url" in data
        assert "active" in data
        assert "message" in data
        assert "request_id" in data
        
        # Verify response content
        assert data["workflow_id"] == "fastapi-integration-workflow-456"
        assert data["active"] is False
        assert "Integration test" in data["message"]
        assert "successfully" in data["message"].lower()
        
        # Verify agent was called with correct message
        full_system_mocks["agent"].process_request.assert_called_once_with(request_data["message"])
    
    def test_complete_dryrun_workflow_via_api(self, test_client, full_system_mocks):
        """Test complete dry run workflow through FastAPI endpoint"""
        request_data = {
            "message": "Find templates for integration testing workflows"
        }
        
        response = test_client.post("/dryrun", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "templates" in data
        assert "request_id" in data
        
        # Verify template data
        assert len(data["templates"]) == 1
        template = data["templates"][0]
        assert template["id"] == "integration-template-001"
        assert template["name"] == "Complete Integration Template"
        assert template["score"] == 0.94
        assert "integration testing" in template["description"].lower()
        
        # Verify template service was called
        full_system_mocks["template"].search_templates.assert_called_once_with(request_data["message"])
    
    def test_complete_health_check_via_api(self, test_client, full_system_mocks):
        """Test complete health check through FastAPI endpoint"""
        response = test_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
        assert "request_id" in data
        
        # Verify overall health
        assert data["status"] == "healthy"
        
        # Verify individual services
        assert len(data["services"]) == 3
        service_names = [service["name"] for service in data["services"]]
        assert "n8n" in service_names
        assert "template_service" in service_names
        assert "openrouter" in service_names
        
        # All services should be healthy
        for service in data["services"]:
            assert service["status"] == "healthy"
            assert "response_time_ms" in service
            assert service["error"] is None
        
        # Verify service health checks were called
        full_system_mocks["n8n"].list_workflows.assert_called_once()
        full_system_mocks["llm"].list_models.assert_called_once()
        full_system_mocks["template"].health_check.assert_called_once()
    
    def test_complete_error_handling_via_api(self, test_client, full_system_mocks):
        """Test complete error handling through FastAPI endpoints"""
        # Make agent fail
        full_system_mocks["agent"].process_request.side_effect = Exception("Integration test error")
        
        request_data = {
            "message": "This should cause an error for testing",
            "activate": False
        }
        
        response = test_client.post("/chat", json=request_data)
        
        assert response.status_code == 500
        data = response.json()
        
        # Verify error response structure
        assert "error" in data
        assert "message" in data["error"]
        assert "status_code" in data["error"]
        assert "request_id" in data["error"]
        
        # Verify error content
        assert data["error"]["status_code"] == 500
        assert "Failed to process chat request" in data["error"]["message"]
        
        # Verify agent was still called (error occurred during processing)
        full_system_mocks["agent"].process_request.assert_called_once_with(request_data["message"])
    
    def test_complete_validation_via_api(self, test_client, full_system_mocks):
        """Test complete input validation through FastAPI endpoints"""
        # Test various invalid inputs
        invalid_requests = [
            # Empty message
            {"message": "", "activate": False},
            # Message too long
            {"message": "x" * 2001, "activate": False},
            # Missing message
            {"activate": False},
            # Invalid data types
            {"message": None, "activate": "not_boolean"}
        ]
        
        for invalid_request in invalid_requests:
            response = test_client.post("/chat", json=invalid_request)
            assert response.status_code == 422  # Validation error
            
            data = response.json()
            assert "detail" in data  # Pydantic validation error format
        
        # Verify agent was never called for invalid requests
        full_system_mocks["agent"].process_request.assert_not_called()


class TestCompleteSystemResilience:
    """Test complete system resilience and recovery"""
    
    @pytest.mark.asyncio
    async def test_complete_system_with_partial_service_failures(self):
        """Test complete system behavior with partial service failures"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-resilience-key'}):
            
            # Create real components
            llm_client = LLMClient()
            n8n_client = N8nClient("http://localhost:5678")
            agent = create_workflow_agent(llm_client, n8n_client)
            
            # Mock individual service failures
            with patch.object(llm_client.openrouter, 'chat_completion') as mock_llm_call, \
                 patch.object(n8n_client, 'create_workflow') as mock_n8n_call:
                
                # LLM works for intent parsing, fails for scoring
                mock_llm_call.side_effect = [
                    # Successful intent extraction
                    {
                        "choices": [{
                            "message": {
                                "content": json.dumps({
                                    "integrations": ["slack"],
                                    "trigger_type": "webhook",
                                    "action": "send_message",
                                    "requirements": [],
                                    "complexity": "simple"
                                })
                            }
                        }]
                    },
                    # Fail during template scoring
                    Exception("LLM service temporarily unavailable")
                ]
                
                # Execute and verify graceful degradation
                result = await agent.process_request("Create Slack notification workflow")
                
                # Should handle LLM failure gracefully
                assert result["success"] is False
                assert result["final_status"] == "error"
                assert "temporarily unavailable" in result["error"]
    
    @pytest.mark.asyncio
    async def test_complete_system_recovery_after_failure(self):
        """Test complete system recovery after transient failures"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-recovery-key'}):
            
            # Create components
            llm_client = LLMClient()
            n8n_client = N8nClient("http://localhost:5678")
            agent = create_workflow_agent(llm_client, n8n_client)
            
            # Mock transient failures followed by success
            with patch.object(llm_client.openrouter, 'chat_completion') as mock_llm, \
                 patch.object(n8n_client, 'create_workflow') as mock_n8n:
                
                # LLM calls succeed
                mock_llm.side_effect = [
                    # Intent extraction
                    {
                        "choices": [{
                            "message": {
                                "content": json.dumps({
                                    "integrations": ["email"],
                                    "trigger_type": "schedule",
                                    "action": "send_report",
                                    "requirements": [],
                                    "complexity": "simple"
                                })
                            }
                        }]
                    },
                    # Template scoring
                    {"choices": [{"message": {"content": "0.87"}}]},
                    # Response generation
                    {
                        "choices": [{
                            "message": {
                                "content": "Your email workflow has been created successfully after recovery!"
                            }
                        }]
                    }
                ]
                
                # n8n fails twice, then succeeds (testing retry logic)
                mock_n8n.side_effect = [
                    Exception("First failure - network timeout"),
                    Exception("Second failure - server busy"),
                    {
                        "id": "recovery-workflow-789",
                        "name": "Recovery Test Workflow",
                        "active": False,
                        "editorUrl": "http://n8n.localhost/workflow/recovery-workflow-789"
                    }
                ]
                
                # Execute request
                result = await agent.process_request("Set up daily email reports")
                
                # Should eventually succeed after retries
                assert result["success"] is True
                assert result["workflow_created"]["id"] == "recovery-workflow-789"
                assert "successfully after recovery" in result["user_response"]
                assert result["final_status"] == "completed"
                
                # Verify retry attempts were made
                assert mock_n8n.call_count == 3  # 2 failures + 1 success


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])