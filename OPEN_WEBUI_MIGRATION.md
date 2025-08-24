# Open WebUI Migration Guide

This guide helps you migrate from the legacy custom chat interface to the new Open WebUI integration.

## What Changed

### 🆕 New Features
- **Professional Chat Interface**: Modern, feature-rich UI with conversation history
- **Self-hosted Privacy**: All data stored locally, no external requests
- **Advanced Features**: Model switching, conversation management, file uploads
- **Better UX**: Improved user experience with established chat interface patterns

### 🚫 Removed Features
- **Custom Chat Interface**: The `/ui` endpoint and static files have been removed
- **Direct HTML Access**: No longer serving custom HTML/CSS/JS files

### 🔄 Preserved Features
- **All Agent API Functionality**: Existing `/chat`, `/dryrun`, and `/health` endpoints remain
- **n8n Integration**: Full workflow creation and management capabilities
- **Template Search**: All template discovery features still available

## Migration Steps

### 1. Update Your Environment

No environment variable changes are needed! The existing `OPENROUTER_API_KEY` is reused.

### 2. Rebuild and Start Services

```bash
# Stop current services
docker compose down

# Rebuild and start with new Open WebUI service
docker compose up -d --build

# Check all services are healthy
docker compose ps
```

### 3. Access the New Interface

- **Primary URL**: http://chat.n8n.localhost (via Caddy proxy)
- **Direct URL**: http://localhost:3000

### 4. First-Time Setup

1. Visit the Open WebUI interface
2. Create your admin account (first user becomes administrator)
3. The `n8n-workflow-assistant` model should be automatically available

### 5. Test the Integration

```bash
# Test the integration endpoints
python test_openai_integration.py

# Check health of all services
curl http://localhost:8001/health
```

## API Endpoint Changes

### ✅ Still Available (Unchanged)
- `GET /` - API information
- `POST /chat` - Direct agent chat
- `POST /dryrun` - Template search
- `GET /health` - Health check
- `GET /docs` - API documentation

### 🆕 New OpenAI-Compatible Endpoints
- `GET /v1/models` - List available models
- `POST /v1/chat/completions` - OpenAI-compatible chat

### ❌ Removed Endpoints
- `GET /ui` - No longer available (use Open WebUI instead)

## Troubleshooting

### Open WebUI Not Loading
1. Check the container is running: `docker compose ps`
2. Check logs: `docker compose logs openwebui`
3. Verify port 3000 is available
4. Try direct access: http://localhost:3000

### Model Not Available in Open WebUI
1. Check agent-api is healthy: `curl http://localhost:8001/health`
2. Test models endpoint: `curl http://localhost:8001/v1/models`
3. Check Open WebUI logs for connection errors

### Chat Not Working
1. Verify OpenRouter API key is set correctly in `.env`
2. Test direct agent endpoint: `curl -X POST http://localhost:8001/chat -H "Content-Type: application/json" -d '{"message": "test"}'`
3. Check agent-api logs: `docker compose logs agent-api`

### Caddy Routing Issues
1. Ensure Caddy is running: `docker compose ps caddy`
2. Check Caddy configuration: `docker compose logs caddy`
3. Verify `/etc/hosts` has `127.0.0.1 chat.n8n.localhost` entry

## Benefits of Open WebUI

### 🎨 Better User Experience
- Professional, modern chat interface
- Conversation history and management
- Real-time typing indicators
- File upload support
- Dark/light theme toggle

### 🔒 Enhanced Privacy
- All data stored locally in Docker volumes
- No external requests to third-party services
- Local conversation history and user management
- Self-hosted with full control

### 🚀 Improved Performance
- Optimized chat interface built for AI interactions
- Better handling of long conversations
- Responsive design for mobile and desktop
- Faster loading and smoother UX

### 🛠 Advanced Features
- Model switching (for future multi-model support)
- Conversation export/import
- User management and permissions
- Plugin system for extensions

## Need Help?

- Check the main documentation: `CLAUDE.md`
- Review API documentation: `API_GUIDE.md`
- Run integration tests: `python test_openai_integration.py`
- Check service health: `curl http://localhost:8001/health`