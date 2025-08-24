"""
OpenRouter LLM Client Wrapper
Handles all LLM interactions through OpenRouter API
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
try:
    from .validation_rules import IntentValidator
except ImportError:
    from validation_rules import IntentValidator

logger = logging.getLogger(__name__)


class LLMClient:
    """Main LLM client interface that wraps OpenRouter client"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.openrouter = OpenRouterClient(api_key)
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """Generate text using the LLM"""
        messages = [{"role": "user", "content": prompt}]
        response = await self.openrouter.chat_completion(messages, **kwargs)
        return response["choices"][0]["message"]["content"]
    
    async def list_models(self) -> List[str]:
        """List available models"""
        # Mock implementation for testing
        return ["openai/gpt-3.5-turbo", "openai/gpt-4", "anthropic/claude-2"]


class OpenRouterClient:
    """Client for interacting with OpenRouter API"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key not provided")
        
        self.base_url = "https://openrouter.ai/api/v1"
        self.default_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-3.5-turbo")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:8001",  # Required by OpenRouter
            "X-Title": "n8n Workflow Agent"  # Optional, for OpenRouter dashboard
        }
        
        # Initialize validation framework
        self.validator = IntentValidator()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Send a chat completion request to OpenRouter
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (defaults to configured model)
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            stream: Whether to stream the response
        
        Returns:
            Response from OpenRouter API
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": model or self.default_model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "stream": stream
                    },
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                logger.error(f"OpenRouter API error: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Error calling OpenRouter: {str(e)}")
                raise
    
    async def extract_intent(self, user_message: str) -> Dict[str, Any]:
        """
        Extract workflow intent from user message
        
        Args:
            user_message: Natural language request from user
        
        Returns:
            Extracted intent with integrations, trigger type, and description
        """
        system_prompt = """You are an expert n8n workflow automation assistant specializing in intent extraction.

INTEGRATION DETECTION RULES (CRITICAL - ALWAYS FOLLOW):
- If user mentions "webhook" → ALWAYS include "Webhook" in integrations
- If user mentions "form" or "submission" → ALWAYS include "Form" in integrations
- If user mentions "schedule", "daily", "weekly" → ALWAYS include "Schedule" in integrations
- Use GENERIC service names: "Email" not "Gmail", "Database" not "MySQL", "Storage" not "Dropbox"
- Common n8n integrations: Slack, Discord, Email, Webhook, Form, Schedule, Database, HTTP Request, Sheets, Airtable

TRIGGER TYPE DECISION RULES (Choose ONE):
- webhook: External system calls your workflow (webhooks, form submissions, API calls, "when X happens", incoming data)
- schedule: Time-based activation (daily, weekly, hourly, cron, "every day", automated timing)
- manual: User manually starts workflow ("I want to run", "let me trigger", "start manually")
- triggered: Activated by another workflow or internal service ("after another workflow", "chain workflows")

EXAMPLES FOR REFERENCE:
✓ "Create webhook for Slack" → integrations: ["Webhook", "Slack"], trigger: "webhook"
✓ "Schedule daily reports to sheets" → integrations: ["Schedule", "Sheets"], trigger: "schedule"
✓ "Email notifications for forms" → integrations: ["Email", "Form"], trigger: "webhook"
✓ "Manual data processing to database" → integrations: ["Database"], trigger: "manual"
✓ "When form submitted, send to Airtable" → integrations: ["Form", "Airtable"], trigger: "webhook"

CRITICAL: For simple requests, be extra thorough in detecting ALL integrations and the correct trigger type.

Respond in JSON format:
{
    "integrations": ["service1", "service2"],
    "trigger_type": "webhook|schedule|manual|triggered",
    "action": "brief description of what the workflow should do",
    "requirements": ["requirement1", "requirement2"]
}"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        response = await self.chat_completion(
            messages=messages,
            temperature=0.1,  # Very low temperature for consistent structured output
            max_tokens=400  # Reduced for more focused responses
        )
        
        try:
            # Extract JSON from response
            content = response["choices"][0]["message"]["content"]
            # Try to parse JSON, handling potential markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            return json.loads(content.strip())
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Failed to parse intent: {e}")
            # Fallback to basic extraction
            return {
                "integrations": [],
                "trigger_type": "manual",
                "action": user_message,
                "requirements": []
            }
    
    async def extract_intent_with_validation(self, user_message: str) -> Tuple[Dict[str, Any], float, List[str]]:
        """
        Enhanced intent extraction with multi-pass validation and correction
        
        Args:
            user_message: Natural language request from user
            
        Returns:
            Tuple of (validated_intent, confidence_score, corrections_applied)
        """
        logger.info(f"Starting enhanced intent extraction for: '{user_message[:100]}...'")
        
        # Pass 1: Main extraction using improved prompt
        intent = await self.extract_intent(user_message)
        
        # Pass 2: Validation and correction
        validated_intent, corrections = self.validator.validate_and_correct_intent(intent, user_message)
        
        # Pass 3: Confidence scoring
        confidence_score = self.validator.calculate_confidence_score(validated_intent, user_message)
        
        logger.info(f"Enhanced extraction complete. Confidence: {confidence_score:.2f}, Corrections: {len(corrections)}")
        
        return validated_intent, confidence_score, corrections
    
    async def score_template_match(
        self,
        user_request: str,
        template_name: str,
        template_integrations: List[str],
        template_trigger: str
    ) -> float:
        """
        Score how well a template matches the user's request
        
        Args:
            user_request: Original user message
            template_name: Name of the workflow template
            template_integrations: List of integrations in the template
            template_trigger: Trigger type of the template
        
        Returns:
            Score between 0 and 100
        """
        prompt = f"""Score how well this workflow template matches the user's request.

User Request: {user_request}

Template Details:
- Name: {template_name}
- Integrations: {', '.join(template_integrations)}
- Trigger Type: {template_trigger}

Provide a score from 0-100 and brief reasoning.
Response format: {{"score": 85, "reasoning": "..."}}"""
        
        messages = [
            {"role": "system", "content": "You are an expert at matching workflow templates to user requirements."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.chat_completion(
            messages=messages,
            temperature=0.3,
            max_tokens=200
        )
        
        try:
            content = response["choices"][0]["message"]["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            result = json.loads(content.strip())
            return float(result.get("score", 50))
        except Exception as e:
            logger.error(f"Failed to parse score: {e}")
            # Fallback to keyword matching
            score = 50  # Base score
            request_lower = user_request.lower()
            
            # Check integrations
            for integration in template_integrations:
                if integration.lower() in request_lower:
                    score += 15
            
            # Check trigger type
            if template_trigger.lower() in request_lower:
                score += 10
            
            # Check name similarity
            name_words = set(template_name.lower().split('_'))
            request_words = set(request_lower.split())
            common_words = name_words.intersection(request_words)
            score += len(common_words) * 5
            
            return min(score, 100)
    
    async def generate_response(
        self,
        success: bool,
        workflow_name: Optional[str] = None,
        workflow_id: Optional[str] = None,
        error_message: Optional[str] = None,
        candidates: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate a natural language response for the user
        
        Args:
            success: Whether the operation was successful
            workflow_name: Name of the imported workflow
            workflow_id: ID of the imported workflow
            error_message: Error message if operation failed
            candidates: List of candidate workflows for dry run
        
        Returns:
            Natural language response
        """
        if success and workflow_name:
            prompt = f"""Generate a friendly response for successfully importing a workflow.
            Workflow: {workflow_name}
            ID: {workflow_id}
            
            Keep it brief and helpful. Mention what the workflow does and any setup needed."""
        elif candidates:
            prompt = f"""Generate a response showing the top matching workflows.
            Candidates: {json.dumps(candidates, indent=2)}
            
            Explain briefly what each does and why they might be relevant."""
        else:
            prompt = f"""Generate a helpful error message.
            Error: {error_message}
            
            Provide guidance on how to fix the issue or alternative actions."""
        
        messages = [
            {"role": "system", "content": "You are a helpful workflow automation assistant."},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.chat_completion(
            messages=messages,
            temperature=0.7,
            max_tokens=300
        )
        
        return response["choices"][0]["message"]["content"]