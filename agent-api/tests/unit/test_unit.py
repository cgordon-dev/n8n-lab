#!/usr/bin/env python3
"""
Unit Tests for n8n Workflow Agent System

Tests individual components with mocked external services.
Run with: pytest test_unit.py -m unit
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

# Import modules under test
from llm_client import LLMClient, OpenRouterClient
from n8n_client import N8nClient
from langgraph_agent import WorkflowAgent, WorkflowState, create_workflow_agent

fake = Faker()


class TestLLMClient:
    """Unit tests for LLM Client components"""
    
    @pytest.fixture
    def mock_openrouter_client(self):
        """Mock OpenRouter client for testing"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key-12345'}):
            client = OpenRouterClient()
            return client
    
    @pytest.mark.unit
    def test_openrouter_client_init_with_api_key(self):
        """Test OpenRouter client initialization with API key"""
        with patch.dict(os.environ, {'OPENROUTER_API_KEY': 'test-key'}):
            client = OpenRouterClient()
            assert client.api_key == 'test-key'
            assert client.base_url == "https://openrouter.ai/api/v1"
            assert client.default_model == "openai/gpt-3.5-turbo"
    
    @pytest.mark.unit
    def test_openrouter_client_init_without_api_key(self):
        """Test OpenRouter client fails without API key"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="OpenRouter API key not provided"):
                OpenRouterClient()
    
    @pytest.mark.unit
    async def test_chat_completion_success(self, mock_openrouter_client):
        """Test successful chat completion"""
        mock_response = {
            "choices": [{
                "message": {
                    "content": "Test response from OpenRouter"
                }
            }],
            "usage": {"total_tokens": 50}
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value.json.return_value = mock_response
            mock_client.return_value.__aenter__.return_value.post.return_value.raise_for_status.return_value = None
            
            messages = [{"role": "user", "content": "Hello"}]
            result = await mock_openrouter_client.chat_completion(messages)
            
            assert result == mock_response
            assert result["choices"][0]["message"]["content"] == "Test response from OpenRouter"
    
    @pytest.mark.unit
    async def test_chat_completion_http_error(self, mock_openrouter_client):
        """Test chat completion HTTP error handling"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            
            http_error = httpx.HTTPStatusError(
                "401 Unauthorized", 
                request=Mock(), 
                response=mock_response
            )
            mock_client.return_value.__aenter__.return_value.post.return_value.raise_for_status.side_effect = http_error
            
            messages = [{"role": "user", "content": "Hello"}]
            
            with pytest.raises(httpx.HTTPStatusError):
                await mock_openrouter_client.chat_completion(messages)
    
    @pytest.mark.unit
    async def test_extract_intent_valid_json(self, mock_openrouter_client):
        """Test intent extraction with valid JSON response"""
        mock_intent = {
            "integrations": ["slack", "gmail"],
            "trigger_type": "webhook",
            "action": "send notification",
            "requirements": ["real-time"]
        }
        
        mock_response = {
            "choices": [{
                "message": {
                    "content": json.dumps(mock_intent)
                }
            }]
        }
        
        with patch.object(mock_openrouter_client, 'chat_completion', return_value=mock_response):
            user_message = "Send Slack notification when new email arrives"
            result = await mock_openrouter_client.extract_intent(user_message)
            
            assert result == mock_intent
            assert result["integrations"] == ["slack", "gmail"]
            assert result["trigger_type"] == "webhook"
    
    @pytest.mark.unit
    async def test_extract_intent_invalid_json(self, mock_openrouter_client):
        """Test intent extraction with invalid JSON fallback"""
        mock_response = {
            "choices": [{
                "message": {
                    "content": "This is not valid JSON"
                }
            }]
        }
        
        with patch.object(mock_openrouter_client, 'chat_completion', return_value=mock_response):
            user_message = "Create workflow"
            result = await mock_openrouter_client.extract_intent(user_message)
            
            # Should fallback to default structure
            assert "integrations" in result
            assert "trigger_type" in result
            assert "action" in result
            assert result["trigger_type"] == "manual"
            assert result["action"] == user_message
    
    @pytest.mark.unit
    async def test_extract_intent_with_code_block(self, mock_openrouter_client):
        """Test intent extraction with JSON in code block"""
        mock_intent = {
            "integrations": ["discord"],
            "trigger_type": "schedule",
            "action": "post message",
            "requirements": []
        }
        
        mock_response = {
            "choices": [{
                "message": {
                    "content": f"```json\n{json.dumps(mock_intent)}\n```"
                }
            }]
        }
        
        with patch.object(mock_openrouter_client, 'chat_completion', return_value=mock_response):
            user_message = "Schedule Discord messages"
            result = await mock_openrouter_client.extract_intent(user_message)
            
            assert result == mock_intent
    
    @pytest.mark.unit
    async def test_score_template_match_success(self, mock_openrouter_client):
        """Test template scoring with valid response"""
        mock_response = {
            "choices": [{
                "message": {
                    "content": '{"score": 85, "reasoning": "Good match"}'
                }
            }]
        }
        
        with patch.object(mock_openrouter_client, 'chat_completion', return_value=mock_response):
            score = await mock_openrouter_client.score_template_match(
                "Send email notifications",
                "Email Alert System",
                ["email", "smtp"],
                "webhook"
            )
            
            assert score == 85.0
    
    @pytest.mark.unit
    async def test_score_template_match_fallback(self, mock_openrouter_client):
        """Test template scoring with fallback logic"""
        mock_response = {
            "choices": [{
                "message": {
                    "content": "Invalid JSON response"
                }
            }]
        }
        
        with patch.object(mock_openrouter_client, 'chat_completion', return_value=mock_response):
            score = await mock_openrouter_client.score_template_match(
                "Send slack notifications via email",
                "Email_Slack_Integration",
                ["email", "slack"],
                "webhook"
            )
            
            # Should use keyword-based fallback
            assert isinstance(score, float)
            assert 0 <= score <= 100
            # Should get bonus points for matching integrations
            assert score > 50  # Base score + integration matches


class TestN8nClient:
    """Unit tests for n8n Client"""
    
    @pytest.fixture
    def n8n_client(self):
        """Create n8n client instance for testing"""
        return N8nClient(base_url="http://test-n8n:5678")
    
    @pytest.mark.unit
    def test_n8n_client_init(self, n8n_client):
        """Test n8n client initialization"""
        assert n8n_client.base_url == "http://test-n8n:5678"
        assert n8n_client.api_path is None
        assert n8n_client.timeout.read == 30.0
    
    @pytest.mark.unit
    async def test_detect_api_path_v1(self, n8n_client):
        """Test API path detection for /api/v1"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            api_path = await n8n_client.detect_api_path()
            
            assert api_path == "/api/v1"
            assert n8n_client.api_path == "/api/v1"
    
    @pytest.mark.unit
    async def test_detect_api_path_rest(self, n8n_client):
        """Test API path detection for /rest"""
        with patch('httpx.AsyncClient') as mock_client:
            # First call to /api/v1 fails, second call to /rest succeeds
            mock_client.return_value.__aenter__.return_value.get.side_effect = [
                httpx.RequestError("Connection failed"),
                Mock(status_code=200)
            ]
            
            api_path = await n8n_client.detect_api_path()
            
            assert api_path == "/rest"
            assert n8n_client.api_path == "/rest"
    
    @pytest.mark.unit
    async def test_detect_api_path_fallback(self, n8n_client):
        """Test API path detection fallback"""
        with patch('httpx.AsyncClient') as mock_client:
            # Both API paths fail
            mock_client.return_value.__aenter__.return_value.get.side_effect = [
                httpx.RequestError("Connection failed"),
                httpx.RequestError("Connection failed")
            ]
            
            api_path = await n8n_client.detect_api_path()
            
            assert api_path == "/api/v1"  # Default fallback
            assert n8n_client.api_path == "/api/v1"
    
    @pytest.mark.unit
    async def test_create_workflow_success(self, n8n_client):
        """Test successful workflow creation"""
        workflow_json = {
            "name": "Test Workflow",
            "nodes": [{"id": "trigger", "type": "manualTrigger"}],
            "connections": {}
        }
        
        mock_response_data = {
            "id": "12345",
            "name": "Test Workflow",
            "active": False,
            "nodes": workflow_json["nodes"],
            "connections": workflow_json["connections"]
        }
        
        with patch.object(n8n_client, 'detect_api_path', return_value="/api/v1"), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await n8n_client.create_workflow(workflow_json, activate=False)
            
            assert result["id"] == "12345"
            assert result["name"] == "Test Workflow"
            assert result["active"] is False
            assert "editorUrl" in result
            assert result["editorUrl"] == "http://n8n.localhost/workflow/12345"
    
    @pytest.mark.unit
    async def test_create_workflow_with_activation(self, n8n_client):
        """Test workflow creation with activation"""
        workflow_json = {"name": "Test Active Workflow"}
        
        mock_response_data = {
            "id": "67890",
            "name": "Test Active Workflow",
            "active": True
        }
        
        with patch.object(n8n_client, 'detect_api_path', return_value="/api/v1"), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_response = Mock()
            mock_response.json.return_value = mock_response_data
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            result = await n8n_client.create_workflow(workflow_json, activate=True)
            
            assert result["active"] is True
    
    @pytest.mark.unit
    async def test_create_workflow_http_error(self, n8n_client):
        """Test workflow creation HTTP error handling"""
        workflow_json = {"name": "Test Workflow"}
        
        with patch.object(n8n_client, 'detect_api_path', return_value="/api/v1"), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_response = Mock()
            mock_response.status_code = 400
            mock_response.text = "Bad request"
            
            http_error = httpx.HTTPStatusError(
                "400 Bad Request", 
                request=Mock(), 
                response=mock_response
            )
            mock_client.return_value.__aenter__.return_value.post.return_value.raise_for_status.side_effect = http_error
            
            with pytest.raises(Exception, match="n8n API error: 400"):
                await n8n_client.create_workflow(workflow_json)
    
    @pytest.mark.unit
    async def test_activate_workflow_success(self, n8n_client):
        """Test successful workflow activation"""
        with patch.object(n8n_client, 'detect_api_path', return_value="/api/v1"), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.patch.return_value = mock_response
            
            result = await n8n_client.activate_workflow("12345")
            
            assert result is True
    
    @pytest.mark.unit
    async def test_activate_workflow_failure(self, n8n_client):
        """Test workflow activation failure"""
        with patch.object(n8n_client, 'detect_api_path', return_value="/api/v1"), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.text = "Workflow not found"
            
            http_error = httpx.HTTPStatusError(
                "404 Not Found", 
                request=Mock(), 
                response=mock_response
            )
            mock_client.return_value.__aenter__.return_value.patch.return_value.raise_for_status.side_effect = http_error
            
            result = await n8n_client.activate_workflow("nonexistent")
            
            assert result is False
    
    @pytest.mark.unit
    async def test_list_workflows_array_response(self, n8n_client):
        """Test listing workflows with array response"""
        mock_workflows = [
            {"id": "1", "name": "Workflow 1", "active": True},
            {"id": "2", "name": "Workflow 2", "active": False}
        ]
        
        with patch.object(n8n_client, 'detect_api_path', return_value="/api/v1"), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_response = Mock()
            mock_response.json.return_value = mock_workflows
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await n8n_client.list_workflows()
            
            assert result == mock_workflows
            assert len(result) == 2
    
    @pytest.mark.unit
    async def test_list_workflows_object_response(self, n8n_client):
        """Test listing workflows with object response containing data field"""
        mock_workflows = [
            {"id": "1", "name": "Workflow 1", "active": True},
            {"id": "2", "name": "Workflow 2", "active": False}
        ]
        
        with patch.object(n8n_client, 'detect_api_path', return_value="/rest"), \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_response = Mock()
            mock_response.json.return_value = {"data": mock_workflows}
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await n8n_client.list_workflows()
            
            assert result == mock_workflows
            assert len(result) == 2
    
    @pytest.mark.unit
    async def test_test_connection_success(self, n8n_client):
        """Test successful connection test"""
        with patch.object(n8n_client, 'detect_api_path', return_value="/api/v1"), \
             patch.object(n8n_client, 'list_workflows', return_value=[]):
            
            result = await n8n_client.test_connection()
            
            assert result is True
    
    @pytest.mark.unit
    async def test_test_connection_failure(self, n8n_client):
        """Test connection test failure"""
        with patch.object(n8n_client, 'detect_api_path', side_effect=Exception("Connection failed")):
            
            result = await n8n_client.test_connection()
            
            assert result is False


class TestLangGraphAgent:
    """Unit tests for LangGraph Agent components"""
    
    @pytest.fixture
    def mock_llm_client(self):
        """Mock LLM client"""
        mock = Mock(spec=LLMClient)
        mock.generate_text = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_n8n_client(self):
        """Mock n8n client"""
        mock = Mock(spec=N8nClient)
        mock.create_workflow = AsyncMock()
        mock.base_url = "http://test-n8n:5678"
        return mock
    
    @pytest.fixture
    def workflow_agent(self, mock_llm_client, mock_n8n_client):
        """Create workflow agent with mocked clients"""
        return WorkflowAgent(mock_llm_client, mock_n8n_client)
    
    @pytest.mark.unit
    def test_workflow_agent_initialization(self, workflow_agent, mock_llm_client, mock_n8n_client):
        """Test workflow agent initialization"""
        assert workflow_agent.llm_client == mock_llm_client
        assert workflow_agent.n8n_client == mock_n8n_client
        assert workflow_agent.max_retries == 3
        assert workflow_agent.confidence_threshold == 0.7
        assert workflow_agent.graph is not None
    
    @pytest.mark.unit
    async def test_parse_intent_success(self, workflow_agent):
        """Test successful intent parsing"""
        mock_intent = {
            "integrations": ["slack"],
            "trigger_type": "webhook",
            "action": "send_message",
            "requirements": [],
            "complexity": "simple"
        }
        
        workflow_agent.llm_client.generate_text.return_value = json.dumps(mock_intent)
        
        state = WorkflowState(
            user_query="Send Slack message when webhook triggered",
            intent=None,
            candidates=None,
            selected_workflow=None,
            workflow_created=None,
            error=None,
            confidence_score=None,
            retry_count=0
        )
        
        result = await workflow_agent._parse_intent(state)
        
        assert result["intent"] == mock_intent
        assert result["error"] is None
    
    @pytest.mark.unit
    async def test_parse_intent_json_error(self, workflow_agent):
        """Test intent parsing with JSON error"""
        workflow_agent.llm_client.generate_text.return_value = "Invalid JSON response"
        
        state = WorkflowState(
            user_query="Test query",
            intent=None,
            candidates=None,
            selected_workflow=None,
            workflow_created=None,
            error=None,
            confidence_score=None,
            retry_count=0
        )
        
        result = await workflow_agent._parse_intent(state)
        
        assert result["intent"] is None
        assert "Failed to parse intent" in result["error"]
    
    @pytest.mark.unit
    async def test_search_templates_success(self, workflow_agent):
        """Test successful template search"""
        mock_intent = {
            "integrations": ["slack", "webhook"],
            "trigger_type": "webhook",
            "action": "send_message",
            "requirements": []
        }
        
        state = WorkflowState(
            user_query="Test query",
            intent=mock_intent,
            candidates=None,
            selected_workflow=None,
            workflow_created=None,
            error=None,
            confidence_score=None,
            retry_count=0
        )
        
        result = await workflow_agent._search_templates(state)
        
        assert result["candidates"] is not None
        assert len(result["candidates"]) > 0
        assert result["error"] is None
    
    @pytest.mark.unit
    async def test_score_candidates_success(self, workflow_agent):
        """Test successful candidate scoring"""
        mock_candidates = [
            {
                "id": "template1",
                "name": "Slack Webhook",
                "description": "Send Slack messages via webhook",
                "integrations": ["slack", "webhook"],
                "category": "messaging"
            },
            {
                "id": "template2", 
                "name": "Email Alert",
                "description": "Send email alerts",
                "integrations": ["email"],
                "category": "notifications"
            }
        ]
        
        mock_intent = {
            "integrations": ["slack"],
            "trigger_type": "webhook",
            "action": "send_message"
        }
        
        # Mock LLM to return different scores
        workflow_agent.llm_client.generate_text.side_effect = ["0.85", "0.45"]
        
        state = WorkflowState(
            user_query="Test query",
            intent=mock_intent,
            candidates=mock_candidates,
            selected_workflow=None,
            workflow_created=None,
            error=None,
            confidence_score=None,
            retry_count=0
        )
        
        result = await workflow_agent._score_candidates(state)
        
        assert result["candidates"] is not None
        assert len(result["candidates"]) == 2
        assert result["candidates"][0]["score"] == 0.85  # Should be sorted by score
        assert result["candidates"][1]["score"] == 0.45
        assert result["confidence_score"] == 0.85
        assert result["error"] is None
    
    @pytest.mark.unit
    async def test_select_best_candidate(self, workflow_agent):
        """Test selecting the best candidate"""
        mock_candidates = [
            {
                "id": "template1",
                "name": "Best Template",
                "description": "The best matching template",
                "score": 0.95
            },
            {
                "id": "template2",
                "name": "Second Template", 
                "description": "Second best template",
                "score": 0.75
            }
        ]
        
        state = WorkflowState(
            user_query="Test query",
            intent=None,
            candidates=mock_candidates,
            selected_workflow=None,
            workflow_created=None,
            error=None,
            confidence_score=None,
            retry_count=0
        )
        
        result = await workflow_agent._select_best(state)
        
        assert result["selected_workflow"] is not None
        assert result["selected_workflow"]["id"] == "template1"
        assert result["selected_workflow"]["name"] == "Best Template"
        assert result["selected_workflow"]["score"] == 0.95
        assert result["error"] is None
    
    @pytest.mark.unit
    async def test_conditional_routing_functions(self, workflow_agent):
        """Test conditional routing logic"""
        # Test intent routing
        assert workflow_agent._should_continue_after_intent({"error": "test error"}) == "error"
        assert workflow_agent._should_continue_after_intent({"intent": {"test": "data"}}) == "search"
        assert workflow_agent._should_continue_after_intent({}) == "error"
        
        # Test search routing
        assert workflow_agent._should_continue_after_search({"error": "test error"}) == "error"
        assert workflow_agent._should_continue_after_search({"candidates": []}) == "no_results"
        assert workflow_agent._should_continue_after_search({"candidates": [{"id": "test"}]}) == "score"
        
        # Test scoring routing
        assert workflow_agent._should_continue_after_scoring({"error": "test error"}) == "error"
        assert workflow_agent._should_continue_after_scoring({"confidence_score": 0.5}) == "low_confidence"
        assert workflow_agent._should_continue_after_scoring({"confidence_score": 0.8}) == "select"
    
    @pytest.mark.unit
    async def test_generate_response_success(self, workflow_agent):
        """Test successful response generation"""
        workflow_agent.llm_client.generate_text.return_value = "Your workflow has been successfully created!"
        
        mock_workflow_created = {
            "id": "12345",
            "name": "Test Workflow",
            "url": "http://test-n8n:5678/workflow/12345",
            "active": False
        }
        
        mock_selected_workflow = {
            "score": 0.85
        }
        
        state = WorkflowState(
            user_query="Create test workflow",
            intent=None,
            candidates=None,
            selected_workflow=mock_selected_workflow,
            workflow_created=mock_workflow_created,
            error=None,
            confidence_score=None,
            retry_count=0
        )
        
        result = await workflow_agent._generate_response(state)
        
        assert result["user_response"] == "Your workflow has been successfully created!"
        assert result["error"] is None
    
    @pytest.mark.unit
    async def test_handle_error(self, workflow_agent):
        """Test error handling"""
        state = WorkflowState(
            user_query="Test query",
            intent=None,
            candidates=None,
            selected_workflow=None,
            workflow_created=None,
            error="Test error occurred",
            confidence_score=None,
            retry_count=0
        )
        
        result = await workflow_agent._handle_error(state)
        
        assert "Test error occurred" in result["user_response"]
        assert result["final_status"] == "error"
    
    @pytest.mark.unit
    async def test_manual_fallback_with_candidates(self, workflow_agent):
        """Test manual fallback with candidate options"""
        mock_candidates = [
            {"name": "Option 1", "score": 0.6},
            {"name": "Option 2", "score": 0.55}
        ]
        
        state = WorkflowState(
            user_query="Test query",
            intent=None,
            candidates=mock_candidates,
            selected_workflow=None,
            workflow_created=None,
            error=None,
            confidence_score=0.6,
            retry_count=0
        )
        
        result = await workflow_agent._manual_fallback(state)
        
        assert "Option 1" in result["user_response"]
        assert "Option 2" in result["user_response"]
        assert result["final_status"] == "manual_selection_required"
    
    @pytest.mark.unit
    async def test_manual_fallback_no_candidates(self, workflow_agent):
        """Test manual fallback with no candidates"""
        state = WorkflowState(
            user_query="Test query",
            intent=None,
            candidates=[],
            selected_workflow=None,
            workflow_created=None,
            error=None,
            confidence_score=None,
            retry_count=0
        )
        
        result = await workflow_agent._manual_fallback(state)
        
        assert "couldn't find any existing workflow templates" in result["user_response"]
        assert result["final_status"] == "manual_selection_required"


class TestUtilityFunctions:
    """Test utility functions and helpers"""
    
    @pytest.mark.unit
    def test_create_workflow_agent_factory(self):
        """Test workflow agent factory function"""
        mock_llm = Mock()
        mock_n8n = Mock()
        
        agent = create_workflow_agent(mock_llm, mock_n8n)
        
        assert isinstance(agent, WorkflowAgent)
        assert agent.llm_client == mock_llm
        assert agent.n8n_client == mock_n8n
    
    @pytest.mark.unit
    def test_workflow_state_type_dict(self):
        """Test WorkflowState TypedDict structure"""
        state = WorkflowState(
            user_query="test",
            intent=None,
            candidates=None,
            selected_workflow=None,
            workflow_created=None,
            error=None,
            confidence_score=None,
            retry_count=0
        )
        
        assert state["user_query"] == "test"
        assert state["retry_count"] == 0
        assert state["error"] is None


# Test data generators using Faker
class TestDataGenerators:
    """Generate test data for consistent testing"""
    
    @pytest.fixture
    def sample_workflow_json(self):
        """Generate sample workflow JSON"""
        return {
            "id": fake.uuid4(),
            "name": fake.catch_phrase(),
            "nodes": [
                {
                    "id": "trigger",
                    "type": "n8n-nodes-base.manualTrigger",
                    "typeVersion": 1,
                    "position": [240, 300]
                },
                {
                    "id": "http_request",
                    "type": "n8n-nodes-base.httpRequest",
                    "typeVersion": 1,
                    "position": [460, 300],
                    "parameters": {
                        "url": fake.url(),
                        "method": "POST"
                    }
                }
            ],
            "connections": {
                "trigger": {
                    "main": [[{"node": "http_request", "type": "main", "index": 0}]]
                }
            },
            "active": False,
            "settings": {},
            "staticData": None
        }
    
    @pytest.fixture
    def sample_template_candidates(self):
        """Generate sample template candidates"""
        return [
            {
                "id": fake.uuid4(),
                "name": f"{fake.word().title()} {fake.word().title()} Integration",
                "description": fake.text(max_nb_chars=100),
                "integrations": [fake.word(), fake.word()],
                "category": fake.random_element(["productivity", "notifications", "data", "automation"]),
                "complexity": fake.random_element(["simple", "medium", "complex"]),
                "score": fake.random.uniform(0.3, 0.9)
            }
            for _ in range(fake.random_int(2, 5))
        ]
    
    @pytest.fixture 
    def sample_user_queries(self):
        """Generate sample user queries for testing"""
        return [
            "Send a Slack notification when I receive an important email",
            "Create a workflow that backs up files to Google Drive every day",
            "Automatically post new blog articles to Twitter and LinkedIn", 
            "Set up monitoring alerts when my website goes down",
            "Process incoming webhook data and save it to a database",
            "Generate daily reports from sales data and email them to the team"
        ]


if __name__ == "__main__":
    # Run unit tests only
    pytest.main([__file__, "-m", "unit", "-v"])