"""
n8n API Client for Local Instance
Handles workflow creation and management in local n8n
"""

import os
import json
from typing import Dict, Any, Optional, List
import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class N8nClient:
    """Client for interacting with local n8n instance"""
    
    def __init__(self, base_url: Optional[str] = None):
        # Use Docker internal network name if running in container
        self.base_url = base_url or os.getenv("N8N_URL", "http://n8n:5678")
        self.api_path = None
        self.timeout = httpx.Timeout(30.0)
    
    async def detect_api_path(self) -> str:
        """
        Auto-detect whether n8n uses /api/v1 or /rest for API endpoints
        
        Returns:
            The correct API path prefix
        """
        if self.api_path:
            return self.api_path
        
        # Try both possible API paths
        paths_to_try = ["/api/v1", "/rest"]
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for path in paths_to_try:
                try:
                    # Try to get workflows list as a test
                    response = await client.get(f"{self.base_url}{path}/workflows")
                    if response.status_code in [200, 401, 403]:  # API exists
                        self.api_path = path
                        logger.info(f"Detected n8n API path: {path}")
                        return path
                except httpx.RequestError:
                    continue
        
        # Default to /api/v1 if detection fails
        self.api_path = "/api/v1"
        logger.warning(f"Could not detect API path, defaulting to {self.api_path}")
        return self.api_path
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def create_workflow(
        self,
        workflow_json: Dict[str, Any],
        activate: bool = False
    ) -> Dict[str, Any]:
        """
        Create a new workflow in n8n
        
        Args:
            workflow_json: The workflow definition
            activate: Whether to activate the workflow immediately
        
        Returns:
            Created workflow data including ID and editor URL
        """
        api_path = await self.detect_api_path()
        
        # Ensure workflow has required fields
        if "name" not in workflow_json:
            workflow_json["name"] = "Imported Workflow"
        
        # Set active status
        workflow_json["active"] = activate
        
        # Remove any existing ID to create new workflow
        workflow_json.pop("id", None)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    f"{self.base_url}{api_path}/workflows",
                    json=workflow_json
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Add editor URL
                workflow_id = result.get("id")
                if workflow_id:
                    # Use the public URL through Caddy proxy
                    result["editorUrl"] = f"http://n8n.localhost/workflow/{workflow_id}"
                
                logger.info(f"Created workflow: {result.get('name')} (ID: {workflow_id})")
                return result
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to create workflow: {e.response.text}")
                raise Exception(f"n8n API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logger.error(f"Error creating workflow: {str(e)}")
                raise
    
    async def activate_workflow(self, workflow_id: str) -> bool:
        """
        Activate an existing workflow
        
        Args:
            workflow_id: ID of the workflow to activate
        
        Returns:
            True if activation successful
        """
        api_path = await self.detect_api_path()
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.patch(
                    f"{self.base_url}{api_path}/workflows/{workflow_id}",
                    json={"active": True}
                )
                response.raise_for_status()
                logger.info(f"Activated workflow: {workflow_id}")
                return True
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to activate workflow: {e.response.text}")
                return False
            except Exception as e:
                logger.error(f"Error activating workflow: {str(e)}")
                return False
    
    async def get_workflow(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a workflow by ID
        
        Args:
            workflow_id: ID of the workflow
        
        Returns:
            Workflow data or None if not found
        """
        api_path = await self.detect_api_path()
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}{api_path}/workflows/{workflow_id}"
                )
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    return None
                logger.error(f"Failed to get workflow: {e.response.text}")
                raise
            except Exception as e:
                logger.error(f"Error getting workflow: {str(e)}")
                raise
    
    async def list_workflows(self) -> List[Dict[str, Any]]:
        """
        List all workflows in n8n
        
        Returns:
            List of workflow summaries
        """
        api_path = await self.detect_api_path()
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.base_url}{api_path}/workflows"
                )
                response.raise_for_status()
                data = response.json()
                
                # Handle both array and object with data field
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict) and "data" in data:
                    return data["data"]
                else:
                    return []
                    
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to list workflows: {e.response.text}")
                return []
            except Exception as e:
                logger.error(f"Error listing workflows: {str(e)}")
                return []
    
    async def test_connection(self) -> bool:
        """
        Test connection to n8n instance
        
        Returns:
            True if connection successful
        """
        try:
            await self.detect_api_path()
            workflows = await self.list_workflows()
            logger.info(f"n8n connection successful. Found {len(workflows)} workflows.")
            return True
        except Exception as e:
            logger.error(f"n8n connection failed: {str(e)}")
            return False