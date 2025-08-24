"""
LangGraph state machine for n8n workflow automation agent.
Handles the complete workflow from user query to n8n workflow creation.
"""

import json
import logging
from typing import Dict, List, Optional, TypedDict, Any
from typing_extensions import Annotated

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from llm_client import LLMClient
from n8n_client import N8nClient

# Configure logging
logger = logging.getLogger(__name__)

class WorkflowState(TypedDict):
    """State definition for the workflow automation agent."""
    user_query: str
    intent: Optional[Dict[str, Any]]
    candidates: Optional[List[Dict[str, Any]]]
    selected_workflow: Optional[Dict[str, Any]]
    workflow_created: Optional[Dict[str, Any]]
    error: Optional[str]
    confidence_score: Optional[float]
    retry_count: int


class WorkflowAgent:
    """LangGraph-based workflow automation agent for n8n."""
    
    def __init__(self, llm_client: LLMClient, n8n_client: N8nClient):
        self.llm_client = llm_client
        self.n8n_client = n8n_client
        self.graph = self._build_graph()
        self.max_retries = 3
        self.confidence_threshold = 0.7
        
    def _build_graph(self) -> StateGraph:
        """Construct the LangGraph state machine."""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("parse_intent", self._parse_intent)
        workflow.add_node("search_templates", self._search_templates)
        workflow.add_node("score_candidates", self._score_candidates)
        workflow.add_node("select_best", self._select_best)
        workflow.add_node("fetch_template", self._fetch_template)
        workflow.add_node("import_to_n8n", self._import_to_n8n)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("handle_error", self._handle_error)
        workflow.add_node("manual_fallback", self._manual_fallback)
        
        # Set entry point
        workflow.set_entry_point("parse_intent")
        
        # Define edges and conditional routing
        workflow.add_conditional_edges(
            "parse_intent",
            self._should_continue_after_intent,
            {
                "search": "search_templates",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "search_templates",
            self._should_continue_after_search,
            {
                "score": "score_candidates",
                "no_results": "manual_fallback",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "score_candidates",
            self._should_continue_after_scoring,
            {
                "select": "select_best",
                "low_confidence": "manual_fallback",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "select_best",
            self._should_continue_after_selection,
            {
                "fetch": "fetch_template",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "fetch_template",
            self._should_continue_after_fetch,
            {
                "import": "import_to_n8n",
                "retry": "fetch_template",
                "error": "handle_error"
            }
        )
        
        workflow.add_conditional_edges(
            "import_to_n8n",
            self._should_continue_after_import,
            {
                "success": "generate_response",
                "retry": "import_to_n8n",
                "error": "handle_error"
            }
        )
        
        # Terminal nodes
        workflow.add_edge("generate_response", END)
        workflow.add_edge("handle_error", END)
        workflow.add_edge("manual_fallback", END)
        
        return workflow.compile()
    
    async def _parse_intent(self, state: WorkflowState) -> WorkflowState:
        """Parse user intent using LLM."""
        try:
            logger.info(f"Parsing intent for query: {state['user_query'][:100]}...")
            
            intent_prompt = f"""
            Parse the following user request to extract workflow automation intent:
            
            User Query: {state['user_query']}
            
            Extract and return a JSON object with:
            - integrations: List of mentioned services/platforms (e.g., ["gmail", "slack"])
            - trigger_type: Type of trigger (webhook, schedule, manual, email, etc.)
            - action: Main action to perform (send_email, create_task, post_message, etc.)
            - requirements: Specific requirements or conditions
            - complexity: "simple", "medium", or "complex"
            
            Return only valid JSON.
            """
            
            response = await self.llm_client.generate_text(intent_prompt)
            intent = json.loads(response.strip())
            
            logger.info(f"Extracted intent: {intent}")
            
            return {
                **state,
                "intent": intent,
                "error": None
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse intent JSON: {e}")
            return {
                **state,
                "error": f"Failed to parse intent: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error parsing intent: {e}")
            return {
                **state,
                "error": f"Intent parsing error: {str(e)}"
            }
    
    async def _search_templates(self, state: WorkflowState) -> WorkflowState:
        """Search for workflow templates based on intent."""
        try:
            intent = state["intent"]
            if not intent:
                return {**state, "error": "No intent available for search"}
            
            logger.info(f"Searching templates for intent: {intent}")
            
            # Build search query from intent
            integrations = intent.get("integrations", [])
            trigger_type = intent.get("trigger_type", "")
            action = intent.get("action", "")
            
            search_query = f"{' '.join(integrations)} {trigger_type} {action}".strip()
            
            # TODO: Replace with actual template service call
            # For now, simulate template search
            candidates = await self._simulate_template_search(search_query, intent)
            
            logger.info(f"Found {len(candidates)} candidate templates")
            
            return {
                **state,
                "candidates": candidates,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error searching templates: {e}")
            return {
                **state,
                "error": f"Template search error: {str(e)}"
            }
    
    async def _score_candidates(self, state: WorkflowState) -> WorkflowState:
        """Score workflow candidates using LLM."""
        try:
            candidates = state["candidates"]
            intent = state["intent"]
            
            if not candidates or not intent:
                return {**state, "error": "Missing candidates or intent for scoring"}
            
            logger.info(f"Scoring {len(candidates)} candidates")
            
            scored_candidates = []
            for candidate in candidates:
                score_prompt = f"""
                Rate how well this workflow template matches the user's requirements on a scale of 0.0 to 1.0:
                
                User Intent:
                - Integrations: {intent.get('integrations', [])}
                - Trigger Type: {intent.get('trigger_type', '')}
                - Action: {intent.get('action', '')}
                - Requirements: {intent.get('requirements', '')}
                
                Workflow Template:
                - Name: {candidate.get('name', '')}
                - Description: {candidate.get('description', '')}
                - Integrations: {candidate.get('integrations', [])}
                - Category: {candidate.get('category', '')}
                
                Return only a decimal number between 0.0 and 1.0.
                """
                
                try:
                    score_response = await self.llm_client.generate_text(score_prompt)
                    score = float(score_response.strip())
                    score = max(0.0, min(1.0, score))  # Clamp to valid range
                    
                    scored_candidate = {**candidate, "score": score}
                    scored_candidates.append(scored_candidate)
                    
                    logger.debug(f"Scored '{candidate.get('name', 'Unknown')}': {score}")
                    
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse score for {candidate.get('name', 'Unknown')}: {e}")
                    scored_candidates.append({**candidate, "score": 0.0})
            
            # Sort by score descending
            scored_candidates.sort(key=lambda x: x["score"], reverse=True)
            
            # Calculate overall confidence
            best_score = scored_candidates[0]["score"] if scored_candidates else 0.0
            
            logger.info(f"Best candidate score: {best_score}")
            
            return {
                **state,
                "candidates": scored_candidates,
                "confidence_score": best_score,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error scoring candidates: {e}")
            return {
                **state,
                "error": f"Candidate scoring error: {str(e)}"
            }
    
    async def _select_best(self, state: WorkflowState) -> WorkflowState:
        """Select the best workflow candidate."""
        try:
            candidates = state["candidates"]
            if not candidates:
                return {**state, "error": "No candidates available for selection"}
            
            best_candidate = candidates[0]  # Already sorted by score
            
            logger.info(f"Selected workflow: {best_candidate.get('name', 'Unknown')} "
                       f"(score: {best_candidate.get('score', 0.0)})")
            
            return {
                **state,
                "selected_workflow": {
                    "id": best_candidate.get("id"),
                    "name": best_candidate.get("name"),
                    "description": best_candidate.get("description"),
                    "score": best_candidate.get("score"),
                    "json_data": None  # Will be fetched in next step
                },
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error selecting best candidate: {e}")
            return {
                **state,
                "error": f"Candidate selection error: {str(e)}"
            }
    
    async def _fetch_template(self, state: WorkflowState) -> WorkflowState:
        """Fetch the full template JSON."""
        try:
            selected = state["selected_workflow"]
            if not selected or not selected.get("id"):
                return {**state, "error": "No selected workflow to fetch"}
            
            template_id = selected["id"]
            logger.info(f"Fetching template data for ID: {template_id}")
            
            # TODO: Replace with actual template service call
            # For now, simulate template fetch
            template_json = await self._simulate_template_fetch(template_id)
            
            return {
                **state,
                "selected_workflow": {
                    **selected,
                    "json_data": template_json
                },
                "retry_count": 0,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error fetching template: {e}")
            retry_count = state.get("retry_count", 0)
            
            if retry_count < self.max_retries:
                logger.info(f"Retrying template fetch (attempt {retry_count + 1})")
                return {
                    **state,
                    "retry_count": retry_count + 1,
                    "error": None
                }
            else:
                return {
                    **state,
                    "error": f"Template fetch failed after {self.max_retries} retries: {str(e)}"
                }
    
    async def _import_to_n8n(self, state: WorkflowState) -> WorkflowState:
        """Import the workflow to n8n."""
        try:
            selected = state["selected_workflow"]
            if not selected or not selected.get("json_data"):
                return {**state, "error": "No workflow data to import"}
            
            logger.info(f"Importing workflow to n8n: {selected.get('name', 'Unknown')}")
            
            workflow_data = selected["json_data"]
            
            # Import to n8n
            result = await self.n8n_client.create_workflow(
                name=selected.get("name", "Imported Workflow"),
                workflow_json=workflow_data,
                active=False  # Start inactive for safety
            )
            
            logger.info(f"Successfully created n8n workflow: {result.get('id')}")
            
            return {
                **state,
                "workflow_created": {
                    "id": result.get("id"),
                    "name": result.get("name"),
                    "url": f"{self.n8n_client.base_url}/workflow/{result.get('id')}",
                    "active": result.get("active", False)
                },
                "retry_count": 0,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error importing to n8n: {e}")
            retry_count = state.get("retry_count", 0)
            
            if retry_count < self.max_retries:
                logger.info(f"Retrying n8n import (attempt {retry_count + 1})")
                return {
                    **state,
                    "retry_count": retry_count + 1,
                    "error": None
                }
            else:
                return {
                    **state,
                    "error": f"n8n import failed after {self.max_retries} retries: {str(e)}"
                }
    
    async def _generate_response(self, state: WorkflowState) -> WorkflowState:
        """Generate user-friendly response."""
        try:
            workflow_created = state["workflow_created"]
            selected_workflow = state["selected_workflow"]
            
            if not workflow_created:
                return {**state, "error": "No workflow created to generate response for"}
            
            response_prompt = f"""
            Generate a friendly, informative response for a user whose workflow automation request has been successfully processed.
            
            Original Request: {state['user_query']}
            
            Workflow Created:
            - Name: {workflow_created.get('name')}
            - ID: {workflow_created.get('id')}
            - URL: {workflow_created.get('url')}
            - Active: {workflow_created.get('active')}
            - Match Score: {selected_workflow.get('score', 0.0):.1%}
            
            Include:
            1. Confirmation that the workflow was created
            2. Brief explanation of what it does
            3. Next steps for the user (review, customize, activate)
            4. The workflow URL for easy access
            
            Keep it conversational and helpful.
            """
            
            response = await self.llm_client.generate_text(response_prompt)
            
            logger.info("Generated user response successfully")
            
            return {
                **state,
                "user_response": response.strip(),
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                **state,
                "error": f"Response generation error: {str(e)}"
            }
    
    async def _handle_error(self, state: WorkflowState) -> WorkflowState:
        """Handle errors and generate appropriate response."""
        error = state.get("error", "Unknown error occurred")
        logger.error(f"Handling error: {error}")
        
        return {
            **state,
            "user_response": f"I encountered an issue while processing your request: {error}. "
                           f"Please try rephrasing your request or contact support for assistance.",
            "final_status": "error"
        }
    
    async def _manual_fallback(self, state: WorkflowState) -> WorkflowState:
        """Handle cases requiring manual intervention."""
        candidates = state.get("candidates", [])
        confidence = state.get("confidence_score", 0.0)
        
        logger.info(f"Falling back to manual selection (confidence: {confidence})")
        
        if candidates:
            # Provide options for manual selection
            options = []
            for i, candidate in enumerate(candidates[:5]):  # Top 5 options
                options.append(f"{i+1}. {candidate.get('name', 'Unknown')} "
                             f"(Score: {candidate.get('score', 0.0):.1%})")
            
            response = f"""
            I found several workflow templates that might match your request, but I need your help to choose the best one:
            
            {chr(10).join(options)}
            
            Please let me know which option you'd like to use, or provide more specific requirements.
            
            Original request: {state['user_query']}
            """
        else:
            response = f"""
            I couldn't find any existing workflow templates that match your request well enough.
            
            Your request: {state['user_query']}
            
            Would you like me to:
            1. Try searching with different keywords
            2. Help you create a custom workflow from scratch
            3. Suggest alternative approaches
            """
        
        return {
            **state,
            "user_response": response.strip(),
            "final_status": "manual_selection_required"
        }
    
    # Conditional edge functions
    def _should_continue_after_intent(self, state: WorkflowState) -> str:
        """Determine next step after intent parsing."""
        if state.get("error"):
            return "error"
        if state.get("intent"):
            return "search"
        return "error"
    
    def _should_continue_after_search(self, state: WorkflowState) -> str:
        """Determine next step after template search."""
        if state.get("error"):
            return "error"
        candidates = state.get("candidates", [])
        if not candidates:
            return "no_results"
        return "score"
    
    def _should_continue_after_scoring(self, state: WorkflowState) -> str:
        """Determine next step after candidate scoring."""
        if state.get("error"):
            return "error"
        confidence = state.get("confidence_score", 0.0)
        if confidence < self.confidence_threshold:
            return "low_confidence"
        return "select"
    
    def _should_continue_after_selection(self, state: WorkflowState) -> str:
        """Determine next step after workflow selection."""
        if state.get("error"):
            return "error"
        if state.get("selected_workflow"):
            return "fetch"
        return "error"
    
    def _should_continue_after_fetch(self, state: WorkflowState) -> str:
        """Determine next step after template fetch."""
        if state.get("error") and state.get("retry_count", 0) >= self.max_retries:
            return "error"
        if state.get("error"):
            return "retry"
        if state.get("selected_workflow", {}).get("json_data"):
            return "import"
        return "error"
    
    def _should_continue_after_import(self, state: WorkflowState) -> str:
        """Determine next step after n8n import."""
        if state.get("error") and state.get("retry_count", 0) >= self.max_retries:
            return "error"
        if state.get("error"):
            return "retry"
        if state.get("workflow_created"):
            return "success"
        return "error"
    
    # Simulation methods (replace with actual API calls)
    async def _simulate_template_search(self, query: str, intent: Dict) -> List[Dict]:
        """Simulate template search (replace with actual template service)."""
        # Mock templates based on common integrations
        mock_templates = [
            {
                "id": "gmail-slack-notify",
                "name": "Gmail to Slack Notification",
                "description": "Send Slack notifications for important emails",
                "integrations": ["gmail", "slack"],
                "category": "productivity",
                "complexity": "simple"
            },
            {
                "id": "webhook-discord-alert",
                "name": "Webhook to Discord Alert",
                "description": "Post Discord alerts from webhook triggers",
                "integrations": ["webhook", "discord"],
                "category": "alerts",
                "complexity": "simple"
            },
            {
                "id": "schedule-backup-gdrive",
                "name": "Scheduled Google Drive Backup",
                "description": "Automatically backup files to Google Drive on schedule",
                "integrations": ["schedule", "gdrive", "filesystem"],
                "category": "backup",
                "complexity": "medium"
            }
        ]
        
        # Simple matching based on integrations mentioned
        intent_integrations = set(intent.get("integrations", []))
        relevant_templates = []
        
        for template in mock_templates:
            template_integrations = set(template["integrations"])
            if intent_integrations.intersection(template_integrations):
                relevant_templates.append(template)
        
        # Return all templates if no specific matches
        return relevant_templates if relevant_templates else mock_templates[:2]
    
    async def _simulate_template_fetch(self, template_id: str) -> Dict:
        """Simulate template fetch (replace with actual template service)."""
        # Mock workflow JSON structure
        mock_workflow = {
            "id": template_id,
            "name": "Mock Workflow",
            "nodes": [
                {
                    "id": "trigger",
                    "type": "n8n-nodes-base.manualTrigger",
                    "typeVersion": 1,
                    "position": [240, 300]
                },
                {
                    "id": "action",
                    "type": "n8n-nodes-base.httpRequest",
                    "typeVersion": 1,
                    "position": [460, 300],
                    "parameters": {
                        "url": "https://api.example.com",
                        "method": "GET"
                    }
                }
            ],
            "connections": {
                "trigger": {
                    "main": [
                        [
                            {
                                "node": "action",
                                "type": "main",
                                "index": 0
                            }
                        ]
                    ]
                }
            }
        }
        
        return mock_workflow
    
    async def process_request(self, user_query: str) -> Dict[str, Any]:
        """Process a user request through the complete workflow."""
        initial_state: WorkflowState = {
            "user_query": user_query,
            "intent": None,
            "candidates": None,
            "selected_workflow": None,
            "workflow_created": None,
            "error": None,
            "confidence_score": None,
            "retry_count": 0
        }
        
        try:
            logger.info(f"Processing request: {user_query[:100]}...")
            
            # Run the workflow
            final_state = await self.graph.ainvoke(initial_state)
            
            # Extract key results
            result = {
                "success": final_state.get("error") is None,
                "user_response": final_state.get("user_response", "No response generated"),
                "workflow_created": final_state.get("workflow_created"),
                "confidence_score": final_state.get("confidence_score"),
                "error": final_state.get("error"),
                "final_status": final_state.get("final_status", "completed")
            }
            
            logger.info(f"Request processing completed. Success: {result['success']}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            return {
                "success": False,
                "user_response": f"I encountered an unexpected error: {str(e)}",
                "error": str(e),
                "final_status": "error"
            }


def create_workflow_agent(llm_client: LLMClient, n8n_client: N8nClient) -> WorkflowAgent:
    """Factory function to create a configured workflow agent."""
    return WorkflowAgent(llm_client, n8n_client)