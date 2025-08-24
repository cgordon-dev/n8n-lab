# Testing Setup - Quick Start Guide

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run All Tests
```bash
python run_tests.py
```

### 3. Run Specific Test Categories
```bash
# Unit tests only (fastest)
python run_tests.py unit

# FastAPI endpoint tests
python run_tests.py fastapi

# Integration tests
python run_tests.py integration

# Complete end-to-end tests
python run_tests.py complete
```

## Test Files Created

1. **`test_fastapi_endpoints.py`** - Comprehensive FastAPI endpoint tests
   - All HTTP endpoints (/chat, /dryrun, /health, /)
   - Request/response validation
   - Error handling and middleware
   - Template service integration

2. **`test_mocks.py`** - External service mocking tests
   - LLM client mocking (OpenRouter)
   - n8n client mocking  
   - Template service mocking
   - Workflow agent with mocked dependencies

3. **`test_error_scenarios.py`** - Error handling and edge cases
   - Network failures and timeouts
   - Invalid responses and authentication errors
   - Service unavailability scenarios
   - FastAPI error handling

4. **`test_complete_integration.py`** - End-to-end integration tests
   - Complete workflow creation scenarios
   - Multi-service coordination
   - Error recovery and resilience testing
   - System recovery after failures

## Key Features

✅ **Proper Async/Await Patterns**: All tests use correct asyncio patterns with pytest-asyncio  
✅ **Comprehensive Mocking**: External services mocked to run without dependencies  
✅ **Error Scenarios**: Extensive error handling and edge case testing  
✅ **Integration Testing**: Complete workflow validation from request to n8n creation  
✅ **Performance Focused**: Tests designed to run efficiently with proper cleanup  

## Test Categories

- **Unit Tests** (`-m unit`): Individual component testing
- **FastAPI Tests** (`-m fastapi`): HTTP endpoint testing  
- **Mock Tests** (`-m mocks`): Service mocking validation
- **Error Tests** (`-m errors`): Error handling and edge cases
- **Integration Tests** (`-m integration`): Component interaction testing
- **Complete Tests** (`-m complete`): End-to-end system testing

## Running Tests

### Using Test Runner (Recommended)
```bash
# All tests with service health checks
python run_tests.py

# Specific categories
python run_tests.py unit
python run_tests.py fastapi  
python run_tests.py mocks
python run_tests.py errors
python run_tests.py integration
python run_tests.py complete

# Check service health only
python run_tests.py check
```

### Using pytest Directly
```bash
# All tests
pytest -v

# By marker
pytest -m unit -v
pytest -m fastapi -v
pytest -m integration -v

# Specific files
pytest test_fastapi_endpoints.py -v
pytest test_complete_integration.py -v

# With coverage
pytest --cov=. --cov-report=html -v
```

## Test Environment

### Required Environment Variables
```bash
# Mock API key for testing (not a real key)
export OPENROUTER_API_KEY="test-key-for-testing"
```

### Optional Service URLs
```bash
export N8N_URL="http://localhost:5678"
export TEMPLATE_SERVICE_URL="http://localhost:8000"  
export AGENT_API_URL="http://localhost:8001"
```

## What Tests Cover

### FastAPI Endpoints
- ✅ `/` root endpoint with API information
- ✅ `/chat` endpoint with workflow creation
- ✅ `/dryrun` endpoint for template search
- ✅ `/health` endpoint with service status
- ✅ Request validation and error handling
- ✅ Middleware (CORS, GZip, logging)

### LLM Client  
- ✅ OpenRouter API integration
- ✅ Intent extraction from user messages
- ✅ Template scoring and ranking
- ✅ Response generation
- ✅ Error handling and retry logic

### n8n Client
- ✅ Workflow creation and management
- ✅ API path detection (/api/v1 vs /rest)
- ✅ Workflow activation and status
- ✅ Connection testing and health checks

### LangGraph Agent
- ✅ Complete workflow state machine
- ✅ Multi-step processing pipeline
- ✅ Template search and selection
- ✅ Conditional routing and decision logic
- ✅ Error recovery and retry mechanisms

### Error Scenarios
- ✅ Network failures and timeouts
- ✅ Invalid API responses
- ✅ Authentication and authorization errors
- ✅ Service unavailability
- ✅ Malformed data handling

### Integration Testing  
- ✅ Complete request-to-workflow flows
- ✅ Multi-service coordination
- ✅ Error recovery and fallback behavior
- ✅ System resilience testing

## Test Results

When you run the tests, you'll see comprehensive output including:

```
📋 Test Execution Plan:
  1. Unit Tests (no external dependencies)
  2. FastAPI Endpoint Tests (with mocking)
  3. Mock Tests (testing mock functionality)
  4. Error Scenario Tests (error handling)  
  5. Integration Tests (with service mocking)
  6. Complete Integration Tests (end-to-end)

📊 Test Results Summary:
==========================================
Unit Tests:              ✅ PASSED
FastAPI Endpoint Tests:  ✅ PASSED
Mock Tests:              ✅ PASSED
Error Scenario Tests:    ✅ PASSED
Integration Tests:       ✅ PASSED
Complete Integration:    ✅ PASSED

🎉 All test suites passed!
```

## Troubleshooting

### Common Issues

**Import errors**: Make sure all dependencies are installed
```bash
pip install -r requirements.txt
```

**Async issues**: Tests use pytest-asyncio, ensure it's installed
```bash
pip install pytest-asyncio
```

**Mock issues**: Check that mocks are properly configured in test setup

**Environment issues**: Set required environment variables
```bash
export OPENROUTER_API_KEY="test-key-for-testing"
```

### Getting Detailed Output
```bash
# Verbose output with all details
python run_tests.py unit -v

# Run with pytest directly for more control
pytest test_fastapi_endpoints.py -v -s --tb=long
```

## Next Steps

1. **Run the tests**: `python run_tests.py`
2. **Check coverage**: `pytest --cov=. --cov-report=html`
3. **Review results**: Open `htmlcov/index.html` for coverage report
4. **Add more tests**: Extend existing test files as needed

The test suite is designed to run without requiring external services, using comprehensive mocking to simulate all external dependencies. This ensures tests are fast, reliable, and can run in any environment.