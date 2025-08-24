# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a local n8n development lab that provides a complete workflow automation environment using Docker Compose. It includes:
- n8n Community Edition (workflow automation tool)
- PostgreSQL database for n8n persistence
- pgAdmin for database management
- Caddy reverse proxy for routing
- **Agent API service** - Intelligent n8n workflow agent powered by LangGraph and OpenRouter
- **Open WebUI** - Self-hosted chat interface for interacting with the n8n workflow agent
- A curated collection of n8n workflow templates and documentation system

## Architecture

### Core Services (Docker Compose)
- **n8n**: Main workflow automation engine (port 5678, accessible via http://n8n.localhost)
- **postgres**: PostgreSQL 16 database for n8n data persistence
- **pgadmin**: Database administration interface
- **caddy**: Reverse proxy handling routing and domain mapping
- **agent-api**: FastAPI service providing intelligent workflow agent capabilities (port 8001)
- **openwebui**: Self-hosted chat interface (port 3000, accessible via http://chat.n8n.localhost or http://localhost:3000)

### Workflow Management System
Located in `n8n-workflows/` directory:
- Python API server (`api_server.py`) for workflow template search and management
- Node.js implementation (`src/server.js`) as an alternative
- SQLite database (`database/workflows.db`) for workflow indexing
- Over 700 pre-built workflow templates in `workflows/` directory

### Intelligent Agent System
Located in `agent-api/` directory:
- **LangGraph Agent** (`langgraph_agent.py`): State machine for workflow automation using LangGraph
- **LLM Client** (`llm_client.py`): OpenRouter integration for AI inference
- **n8n Client** (`n8n_client.py`): Direct integration with n8n API for workflow management
- **FastAPI Server** (`main.py`): RESTful API endpoints for agent interactions

## Common Development Commands

### Docker Operations
```bash
# Start all services
docker compose up -d

# Stop all services
docker compose down

# View logs
docker compose logs -f [service-name]

# Rebuild services
docker compose build --no-cache
```

### Workflow Management (in n8n-workflows/)
```bash
# Python implementation
python api_server.py              # Start the Python API server

# Node.js implementation
npm install                        # Install dependencies
npm run init                       # Initialize database
npm run index                      # Index workflow files
npm start                          # Start Node.js server
npm run dev                        # Start with nodemon for development
```

### Database Operations
```bash
# Initialize workflow database
cd n8n-workflows
python create_categories.py       # Create category mappings
python import_workflows.py        # Import workflow templates to database
```

### Agent API Development (in agent-api/)
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export OPENROUTER_API_KEY="your_api_key_here"

# Start the agent API service (development)
python main.py

# Run comprehensive tests
python run_tests.py

# Run specific test categories
python run_tests.py unit          # Unit tests only
python run_tests.py fastapi       # FastAPI endpoint tests
python run_tests.py integration   # Integration tests
python run_tests.py complete      # Complete end-to-end tests
```

## Key Directories and Files

### Configuration
- `.env`: Main environment variables (includes OPENROUTER_API_KEY for agent API)
- `config/database/.env`: PostgreSQL-specific configuration
- `config/n8n/.env`: n8n-specific configuration
- `config/reverse-proxy/Caddyfile`: Caddy routing configuration
- `agent-api/requirements.txt`: Python dependencies for agent service
- `agent-api/pytest.ini`: Testing configuration

### Workflow System
- `n8n-workflows/workflows/`: JSON workflow template files organized by service/integration
- `n8n-workflows/Documentation/`: Detailed documentation for workflow categories
- `n8n-workflows/static/`: Web interface files for workflow browser
- `n8n-workflows/context/`: Category definitions and search mappings

### Agent API System
- `agent-api/main.py`: FastAPI application with chat, dryrun, and health endpoints
- `agent-api/langgraph_agent.py`: LangGraph state machine for workflow automation
- `agent-api/llm_client.py`: OpenRouter client wrapper for LLM interactions
- `agent-api/n8n_client.py`: n8n API client with auto-detection capabilities
- `agent-api/test_*.py`: Comprehensive test suite with unit, integration, and E2E tests

### MCP Server Definitions
- `mcp/`: Model Context Protocol server configurations for various tools

## API Endpoints

### Workflow Template API (when running api_server.py or Node.js server)
- `GET /api/workflows`: List all workflows with optional filtering
- `GET /api/workflow/:id`: Get specific workflow JSON
- `GET /api/categories`: List all workflow categories
- `GET /api/search?q=<query>`: Search workflows by keyword
- `GET /api/stats`: Get statistics about workflow collection

### Agent API (Port 8001 - Intelligent Workflow Agent)
- `GET /`: API information and documentation
- `POST /chat`: Process natural language requests and create workflows
  - **Request**: `{"message": "Create a workflow...", "activate": false}`
  - **Response**: Workflow creation with agent guidance
- `POST /dryrun`: Search for workflow templates without importing
  - **Request**: `{"message": "I need a workflow to..."}`
  - **Response**: List of matching templates with relevance scores
- `GET /health`: Health check for all connected services
  - **Response**: Status of n8n, template service, and OpenRouter API

### OpenAI-Compatible API Endpoints (for Open WebUI Integration)
- `GET /v1/models`: List available models (OpenAI-compatible)
- `POST /v1/chat/completions`: Chat completions endpoint (OpenAI-compatible)
  - **Request**: OpenAI chat format with messages array
  - **Response**: OpenAI-compatible chat completion response

### Open WebUI Interface
- **URL**: http://chat.n8n.localhost or http://localhost:3000
- **Features**: Modern chat interface with conversation history, model selection, and file uploads
- **Integration**: Connects to agent-api via OpenAI-compatible endpoints
- **Data Storage**: All conversations and data stored locally in Docker volume

See `API_GUIDE.md` for detailed API documentation with examples.

## Workflow File Structure

Each workflow JSON file contains:
- `name`: Workflow name following pattern `[ID]_[Service]_[Action]_[TriggerType]`
- `nodes`: Array of operation nodes
- `connections`: Node connection mappings
- `trigger`: How the workflow is initiated (Triggered, Scheduled, Webhook, etc.)
- `settings`: Workflow configuration

## Development Guidelines

### Working with Workflows
- Workflow files are named with pattern: `[ID]_[Service]_[Action]_[TriggerType].json`
- Common trigger types: Triggered, Scheduled, Webhook, Manual
- Categories are auto-detected from service names in filenames

### Adding New Workflows
1. Place JSON file in appropriate service directory under `workflows/`
2. Follow naming convention
3. Run indexing: `python import_workflows.py` or `npm run index`

### Environment Variables
Key variables to configure:
- `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`: Database credentials
- `N8N_CONTAINER_NAME`: n8n container identifier
- `PGADMIN_DEFAULT_EMAIL`, `PGADMIN_DEFAULT_PASSWORD`: pgAdmin access
- `OPENROUTER_API_KEY`: Required for agent API LLM functionality
- `N8N_URL`: n8n instance URL for agent API (defaults to http://n8n:5678)
- `TEMPLATES_SERVICE_URL`: Template service URL for agent API (defaults to http://host.docker.internal:8000)

## Common Issues and Solutions

### n8n Not Accessible
- Check if all services are running: `docker compose ps`
- Verify Caddy is routing correctly to http://n8n.localhost
- Ensure port 80 is available for Caddy

### Database Connection Issues
- Wait for PostgreSQL health check to pass before n8n starts
- Check credentials match between `.env` files and docker-compose.yml

### Workflow Import Failures
- Ensure workflow JSON is valid n8n format
- Check for required fields: name, nodes, connections
- Verify n8n version compatibility

### Agent API Issues
- **Missing OpenRouter API Key**: Set `OPENROUTER_API_KEY` environment variable
- **Agent API Not Responding**: Check service is running on port 8001: `curl http://localhost:8001/health`
- **LLM Request Failures**: Verify OpenRouter API key is valid and has sufficient credits
- **Template Service Connection**: Ensure workflow template API is running on port 8000
- **n8n Connection**: Verify n8n is accessible from agent-api container via internal Docker network

## Testing Workflows
1. Access n8n UI at http://n8n.localhost
2. Import workflow via UI or API
3. Configure required credentials for external services
4. Test execution with manual trigger or configured trigger type

## Testing Agent API
1. **Health Check**: `curl http://localhost:8001/health`
2. **Natural Language Workflow Creation**: 
   ```bash
   curl -X POST http://localhost:8001/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Create a workflow that sends daily email reports", "activate": false}'
   ```
3. **Template Search (Dry Run)**:
   ```bash
   curl -X POST http://localhost:8001/dryrun \
     -H "Content-Type: application/json" \
     -d '{"message": "I need a workflow to process customer feedback"}'
   ```
4. **OpenAI-Compatible Endpoints**:
   ```bash
   # List available models
   curl http://localhost:8001/v1/models
   
   # Chat completion
   curl -X POST http://localhost:8001/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model": "n8n-workflow-assistant", "messages": [{"role": "user", "content": "Help me create a workflow"}]}'
   ```
5. **Run Agent API Test Suite**: `cd agent-api && python run_tests.py`
6. **Test Open WebUI Integration**: `python test_openai_integration.py`

## Testing Open WebUI
1. **Access Interface**: Visit http://chat.n8n.localhost or http://localhost:3000
2. **First-time Setup**: Create an admin account when prompted
3. **Model Selection**: The n8n-workflow-assistant model should be available
4. **Test Chat**: Send a message like "Help me create a workflow to automate email notifications"

## Security Considerations
- API keys and credentials should be stored in environment files, not in code
- The `client_secret_*.json` file appears to be OAuth credentials - handle with care
- n8n credentials are managed separately within n8n, not in workflow files
- **OpenRouter API Key**: Store `OPENROUTER_API_KEY` securely in `.env` file, never in code
- Agent API communicates with external LLM service - monitor usage and costs
- **Open WebUI**: All conversations and data stored locally in Docker volume for privacy
- **First Admin Account**: The first user to access Open WebUI becomes the administrator
- All API communications should use HTTPS in production environments
- Open WebUI provides local data storage with no external requests for enhanced security