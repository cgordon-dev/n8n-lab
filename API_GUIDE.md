# n8n Agent API - Complete Guide

This guide provides comprehensive documentation for the n8n Agent API, an intelligent workflow automation service that uses LangGraph and OpenRouter to create n8n workflows from natural language descriptions.

## Overview

The Agent API provides three main endpoints that enable natural language interaction with n8n workflows:

- **Chat Endpoint**: Creates and optionally activates workflows based on natural language descriptions
- **Dry Run Endpoint**: Searches for existing workflow templates without creating new workflows
- **Health Endpoint**: Monitors the status of all connected services

## Base URL

When running locally with Docker Compose:
```
http://localhost:8001
```

## Authentication

Currently, no authentication is required for local development. The service uses the `OPENROUTER_API_KEY` environment variable for LLM access.

## Endpoints

### GET /

Returns basic API information and version details.

**Response**:
```json
{
  "name": "n8n Agent API",
  "version": "1.0.0",
  "description": "Intelligent n8n workflow agent powered by LangGraph and OpenRouter",
  "docs_url": "/docs",
  "health_check_url": "/health"
}
```

**Example**:
```bash
curl http://localhost:8001/
```

### POST /chat

Process a natural language request to create an n8n workflow. The agent analyzes the request, searches for suitable templates, and can optionally create and activate the workflow in n8n.

**Request Body**:
```json
{
  "message": "string (required, 1-2000 characters)",
  "activate": "boolean (optional, default: false)"
}
```

**Response**:
```json
{
  "workflow_id": "string or null",
  "editor_url": "string or null", 
  "active": "boolean",
  "message": "string",
  "request_id": "string"
}
```

**Field Descriptions**:
- `message`: Natural language description of the desired workflow
- `activate`: Whether to activate the workflow in n8n after creation
- `workflow_id`: The ID of the created workflow (if successful)
- `editor_url`: Direct link to edit the workflow in n8n
- `active`: Whether the workflow was activated
- `message`: Agent's response explaining what was done
- `request_id`: Unique identifier for tracking the request

**Examples**:

1. **Create a workflow (preview mode)**:
```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a workflow that sends daily email reports from a Google Sheet",
    "activate": false
  }'
```

Response:
```json
{
  "workflow_id": "workflow_123abc",
  "editor_url": "http://n8n.localhost/workflow/workflow_123abc",
  "active": false,
  "message": "I've created a workflow that reads data from a Google Sheet and sends daily email reports. The workflow includes a cron trigger set for daily execution, a Google Sheets node to fetch data, and an email node to send the report. You can review and customize it in the n8n editor.",
  "request_id": "req_456def"
}
```

2. **Create and activate a workflow**:
```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Set up a webhook that saves form submissions to Airtable",
    "activate": true
  }'
```

Response:
```json
{
  "workflow_id": "workflow_789ghi",
  "editor_url": "http://n8n.localhost/workflow/workflow_789ghi",
  "active": true,
  "message": "I've created and activated a webhook workflow that saves form submissions to Airtable. The webhook URL is available in the workflow editor. When data is sent to this webhook, it will automatically be saved to your Airtable base.",
  "request_id": "req_101112"
}
```

3. **Complex workflow request**:
```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create an e-commerce order processing workflow: when a new order comes via webhook, send confirmation email, create Trello card, and notify Slack channel",
    "activate": false
  }'
```

### POST /dryrun

Search for existing workflow templates that match your requirements without creating a new workflow. This is useful for exploring available templates before committing to a specific approach.

**Request Body**:
```json
{
  "message": "string (required, 1-2000 characters)"
}
```

**Response**:
```json
{
  "templates": [
    {
      "id": "string",
      "name": "string", 
      "score": "number (0-1)",
      "description": "string"
    }
  ],
  "request_id": "string"
}
```

**Field Descriptions**:
- `message`: Natural language description of desired workflow functionality
- `templates`: Array of matching templates ordered by relevance score
- `id`: Template identifier
- `name`: Template name
- `score`: Relevance score from 0.0 to 1.0 (higher is more relevant)
- `description`: Description of what the template does
- `request_id`: Unique identifier for tracking the request

**Examples**:

1. **Search for email automation templates**:
```bash
curl -X POST http://localhost:8001/dryrun \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need to send automated emails based on calendar events"
  }'
```

Response:
```json
{
  "templates": [
    {
      "id": "template_email_calendar_01",
      "name": "Google Calendar Email Reminder",
      "score": 0.92,
      "description": "Automatically sends email reminders based on Google Calendar events"
    },
    {
      "id": "template_email_scheduler_02", 
      "name": "Scheduled Email Campaigns",
      "score": 0.75,
      "description": "Send scheduled email campaigns with calendar-based triggers"
    },
    {
      "id": "template_outlook_sync_03",
      "name": "Outlook Calendar to Email",
      "score": 0.68,
      "description": "Sync Outlook calendar events and send email notifications"
    }
  ],
  "request_id": "req_dryrun_001"
}
```

2. **Search for data processing templates**:
```bash
curl -X POST http://localhost:8001/dryrun \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Process CSV files and update database records"
  }'
```

### GET /health

Check the health status of the Agent API and all connected services. This endpoint monitors connectivity to n8n, the template service, and the OpenRouter API.

**Response**:
```json
{
  "status": "string (healthy|degraded|unhealthy)",
  "timestamp": "string (ISO 8601 datetime)",
  "services": [
    {
      "name": "string",
      "status": "string (healthy|unhealthy)",
      "response_time_ms": "number or null",
      "error": "string or null"
    }
  ],
  "request_id": "string"
}
```

**Field Descriptions**:
- `status`: Overall system health status
- `timestamp`: When the health check was performed
- `services`: Individual service health statuses
- `name`: Service name (n8n, template_service, openrouter)
- `status`: Individual service status
- `response_time_ms`: Response time in milliseconds (if healthy)
- `error`: Error message (if unhealthy)
- `request_id`: Unique identifier for the health check

**Example**:
```bash
curl http://localhost:8001/health
```

**Healthy Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45.123Z",
  "services": [
    {
      "name": "n8n",
      "status": "healthy",
      "response_time_ms": 45.2,
      "error": null
    },
    {
      "name": "template_service", 
      "status": "healthy",
      "response_time_ms": 23.1,
      "error": null
    },
    {
      "name": "openrouter",
      "status": "healthy", 
      "response_time_ms": 156.8,
      "error": null
    }
  ],
  "request_id": "req_health_001"
}
```

**Degraded Response** (some services unhealthy):
```json
{
  "status": "degraded",
  "timestamp": "2024-01-15T10:35:22.456Z", 
  "services": [
    {
      "name": "n8n",
      "status": "healthy",
      "response_time_ms": 52.3,
      "error": null
    },
    {
      "name": "template_service",
      "status": "unhealthy", 
      "response_time_ms": null,
      "error": "Connection timeout after 30 seconds"
    },
    {
      "name": "openrouter",
      "status": "healthy",
      "response_time_ms": 203.4,
      "error": null
    }
  ],
  "request_id": "req_health_002"
}
```

## Error Handling

All endpoints return appropriate HTTP status codes and include error details in the response body when applicable.

### Common HTTP Status Codes

- `200 OK`: Request successful
- `400 Bad Request`: Invalid request format or parameters
- `422 Unprocessable Entity`: Valid request format but invalid data
- `500 Internal Server Error`: Server-side error
- `503 Service Unavailable`: Required services (n8n, OpenRouter) are unavailable

### Error Response Format

```json
{
  "detail": "string or object describing the error",
  "request_id": "string (when available)"
}
```

**Examples**:

1. **Invalid request body**:
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "message"],
      "msg": "Field required",
      "input": {}
    }
  ]
}
```

2. **Service unavailable**:
```json
{
  "detail": "OpenRouter API is currently unavailable. Please try again later.",
  "request_id": "req_error_001"
}
```

3. **Message too long**:
```json
{
  "detail": [
    {
      "type": "string_too_long",
      "loc": ["body", "message"], 
      "msg": "String should have at most 2000 characters",
      "input": "very long message...",
      "ctx": {"max_length": 2000}
    }
  ]
}
```

## Rate Limiting

Currently, no rate limiting is implemented for local development. In production, consider implementing rate limiting to manage OpenRouter API costs and prevent abuse.

## Usage Examples

### Natural Language Workflow Creation Scenarios

1. **Email Automation**:
```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "When someone fills out my contact form, send me an email and add them to my Mailchimp list",
    "activate": true
  }'
```

2. **Data Synchronization**:
```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Sync new Shopify orders with my Airtable database every hour",
    "activate": false
  }'
```

3. **Social Media Automation**:
```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Post my new blog articles to Twitter and LinkedIn automatically",
    "activate": false
  }'
```

4. **Monitoring and Alerts**:
```bash
curl -X POST http://localhost:8001/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Monitor my website for downtime and send Slack notifications if it goes offline",
    "activate": true
  }'
```

### Template Discovery Scenarios

1. **Explore CRM Integration Options**:
```bash
curl -X POST http://localhost:8001/dryrun \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Connect my CRM with other business tools"
  }'
```

2. **Find File Processing Templates**:
```bash
curl -X POST http://localhost:8001/dryrun \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Process uploaded files and extract data"
  }'
```

3. **Discover Notification Workflows**:
```bash
curl -X POST http://localhost:8001/dryrun \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Send notifications when specific events happen"
  }'
```

## Integration with Frontend Applications

### JavaScript/TypeScript Example

```typescript
interface ChatRequest {
  message: string;
  activate?: boolean;
}

interface ChatResponse {
  workflow_id: string | null;
  editor_url: string | null;
  active: boolean;
  message: string;
  request_id: string;
}

async function createWorkflow(message: string, activate = false): Promise<ChatResponse> {
  const response = await fetch('http://localhost:8001/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ message, activate }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

// Usage
try {
  const result = await createWorkflow(
    "Create a workflow that backs up my database daily",
    false
  );
  console.log('Workflow created:', result.workflow_id);
  console.log('Edit in n8n:', result.editor_url);
} catch (error) {
  console.error('Failed to create workflow:', error);
}
```

### Python Example

```python
import requests
import json
from typing import Dict, Any, Optional

class N8nAgentClient:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
    
    def create_workflow(self, message: str, activate: bool = False) -> Dict[str, Any]:
        """Create a new workflow using natural language description."""
        response = requests.post(
            f"{self.base_url}/chat",
            json={"message": message, "activate": activate},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    
    def search_templates(self, message: str) -> Dict[str, Any]:
        """Search for workflow templates without creating them."""
        response = requests.post(
            f"{self.base_url}/dryrun",
            json={"message": message},
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health of all connected services."""
        response = requests.get(f"{self.base_url}/health")
        response.raise_for_status()
        return response.json()

# Usage
client = N8nAgentClient()

try:
    # Create a workflow
    result = client.create_workflow(
        "Set up a workflow that processes customer support tickets from email",
        activate=False
    )
    print(f"Created workflow: {result['workflow_id']}")
    
    # Search for templates
    templates = client.search_templates(
        "I need to integrate with Slack and send notifications"
    )
    print(f"Found {len(templates['templates'])} matching templates")
    
    # Health check
    health = client.health_check()
    print(f"System status: {health['status']}")
    
except requests.exceptions.RequestException as e:
    print(f"API request failed: {e}")
```

## Testing the API

The Agent API includes a comprehensive test suite. To run tests:

```bash
cd agent-api
python run_tests.py
```

Available test categories:
- `unit`: Fast unit tests for individual components
- `fastapi`: API endpoint tests
- `integration`: Service integration tests  
- `complete`: Full end-to-end tests

## Troubleshooting

### Common Issues

1. **OpenRouter API Key Missing**:
   - Ensure `OPENROUTER_API_KEY` is set in your environment variables
   - Check that the API key is valid and has sufficient credits

2. **n8n Connection Issues**:
   - Verify n8n is running and accessible
   - Check Docker network connectivity between services

3. **Template Service Unavailable**:
   - Ensure the workflow template API is running on port 8000
   - Check the `TEMPLATES_SERVICE_URL` environment variable

4. **Slow Response Times**:
   - OpenRouter API calls can take 2-10 seconds depending on model and load
   - Consider using the `/dryrun` endpoint for faster template searches

### Monitoring and Logs

- Agent API logs are written to `agent-api/agent_api.log`
- Use the `/health` endpoint for continuous monitoring
- Monitor OpenRouter usage and costs through the OpenRouter dashboard

## Future Enhancements

Planned features for future releases:
- Authentication and authorization
- Rate limiting and usage quotas  
- Webhook support for workflow status updates
- Batch workflow creation
- Advanced template filtering and search
- Custom LLM model selection
- Workflow versioning and rollback
- Integration with n8n Cloud instances