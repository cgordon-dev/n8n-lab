# n8n Workflow Agent System - Comprehensive Testing Guide

## Overview

This document provides a complete guide to the test suite for the n8n workflow agent system. The testing framework is designed to ensure reliability, maintainability, and proper functionality across all components.

## Test Architecture

### Test Categories

1. **Unit Tests** (`test_unit.py`) - Test individual components in isolation
2. **FastAPI Endpoint Tests** (`test_fastapi_endpoints.py`) - Test all HTTP endpoints  
3. **Mock Tests** (`test_mocks.py`) - Test external service mocking functionality
4. **Error Scenario Tests** (`test_error_scenarios.py`) - Test error handling and edge cases
5. **Integration Tests** (`test_integration.py`) - Test component interactions
6. **Complete Integration Tests** (`test_complete_integration.py`) - End-to-end workflows

### Test Framework Features

- **Async/Await Support**: Full async testing with pytest-asyncio
- **Service Mocking**: Comprehensive mocking for external services
- **Error Recovery**: Tests for retry logic and failure scenarios  
- **Performance**: Tests designed to run efficiently with proper cleanup
- **Markers**: Organized test execution with pytest markers

## Test Files Overview

### `test_unit.py` - Unit Tests
Tests individual components without external dependencies:
- LLM client functionality (OpenRouter integration)
- n8n client API interactions
- LangGraph agent components
- Data models and utility functions

**Key Test Classes:**
- `TestLLMClient` - OpenRouter API wrapper tests
- `TestN8nClient` - n8n API client tests  
- `TestLangGraphAgent` - Workflow agent logic tests
- `TestDataGenerators` - Test data creation utilities

### `test_fastapi_endpoints.py` - FastAPI Endpoint Tests
Comprehensive tests for all HTTP endpoints:
- Request/response validation
- Error handling and status codes
- Middleware functionality (CORS, GZip, logging)
- Authentication and authorization
- Template service client integration

**Key Test Classes:**
- `TestFastAPIEndpoints` - Main endpoint testing
- `TestTemplateServiceClient` - Template service integration

### `test_mocks.py` - Mock Tests
Tests the mocking functionality for external services:
- LLM service mocking (OpenRouter)
- n8n API mocking
- Template service mocking
- Workflow agent with mocked dependencies

**Key Test Classes:**
- `TestLLMClientMocking` - LLM service mock tests
- `TestN8nClientMocking` - n8n service mock tests
- `TestTemplateServiceMocking` - Template service mock tests
- `TestWorkflowAgentMocking` - Agent with mocked services

### `test_error_scenarios.py` - Error Scenario Tests
Tests error handling and edge cases:
- Network failures and timeouts
- Invalid responses and malformed data
- Service unavailability
- Authentication/authorization failures
- Rate limiting and quota errors

**Key Test Classes:**
- `TestLLMErrorScenarios` - LLM service error handling
- `TestN8nErrorScenarios` - n8n service error handling
- `TestTemplateServiceErrorScenarios` - Template service errors
- `TestWorkflowAgentErrorScenarios` - Agent error handling
- `TestFastAPIErrorScenarios` - API endpoint error handling

### `test_integration.py` - Integration Tests
Tests interactions between components:
- Service integration workflows
- Cross-component communication
- Real API interactions (with service mocking)
- Multi-step workflows

**Key Test Classes:**
- `TestTemplateServiceIntegration` - Template service workflows
- `TestN8nIntegration` - n8n integration workflows
- `TestLLMIntegration` - LLM service integration
- `TestFastAPIEndpoints` - API endpoint integration
- `TestEndToEndWorkflows` - Complete workflow tests

### `test_complete_integration.py` - Complete Integration Tests
End-to-end system tests:
- Full workflow creation scenarios
- Multi-service coordination
- Error recovery and resilience
- Performance and reliability testing

**Key Test Classes:**
- `TestCompleteWorkflowIntegration` - Full workflow scenarios
- `TestFastAPICompleteIntegration` - Complete API workflows
- `TestCompleteSystemResilience` - System recovery testing

## Running Tests

### Test Runner Script
Use the `run_tests.py` script for comprehensive test execution:

```bash
# Run all tests
python run_tests.py

# Run specific test categories  
python run_tests.py unit
python run_tests.py fastapi
python run_tests.py mocks
python run_tests.py errors
python run_tests.py integration
python run_tests.py complete

# Check service health
python run_tests.py check
```

### Direct pytest Execution
Run tests directly with pytest:

```bash
# Run all tests
pytest -v

# Run by category
pytest -m unit -v
pytest -m fastapi -v
pytest -m integration -v
pytest -m complete -v

# Run specific test files
pytest test_unit.py -v
pytest test_fastapi_endpoints.py -v

# Run with coverage
pytest --cov=. --cov-report=html -v
```

### Test Markers
Available pytest markers for targeted test execution:

- `unit` - Unit tests with no external dependencies
- `integration` - Integration tests with mocked services
- `fastapi` - FastAPI endpoint specific tests
- `mocks` - Mock functionality tests
- `errors` - Error scenario and edge case tests
- `complete` - Complete end-to-end integration tests
- `slow` - Tests that take longer to execute
- `openrouter` - Tests requiring OpenRouter API
- `n8n` - Tests requiring n8n service
- `template_service` - Tests requiring template service

## Test Configuration

### Environment Setup
Tests use environment variables for configuration:

```bash
# Required for LLM tests (can be mock value for testing)
export OPENROUTER_API_KEY="test-key-for-testing"

# Optional service URLs (defaults to localhost)
export N8N_URL="http://localhost:5678"
export TEMPLATE_SERVICE_URL="http://localhost:8000"
```

### pytest Configuration
Configuration in `pytest.ini`:
- Async mode enabled
- Comprehensive logging
- Test discovery patterns
- Marker definitions
- Timeout settings

## Mocking Strategy

### Service Mocking
All external services are properly mocked:

**LLM Service (OpenRouter)**:
- HTTP requests/responses mocked
- Various response scenarios (success, failure, malformed)
- Rate limiting and authentication errors
- Retry logic and timeout handling

**n8n Service**:
- API endpoint mocking
- Workflow creation/management
- Connection and authentication errors
- Version compatibility testing

**Template Service**:
- Search and retrieval operations
- Health check functionality
- Error scenarios and fallbacks
- Performance simulation

### Mock Data
Realistic test data generated using:
- Faker library for dynamic test data
- Predefined scenarios for consistency
- Edge cases and boundary conditions
- Performance testing datasets

## Error Testing

### Error Categories Covered

**Network Errors**:
- Connection refused/timeout
- DNS resolution failures  
- SSL/TLS certificate issues
- Intermittent connectivity

**API Errors**:
- HTTP status codes (4xx, 5xx)
- Authentication failures
- Rate limiting
- Invalid request/response formats

**Service Errors**:
- Service unavailability
- Partial service failures
- Malformed responses
- Version incompatibilities

**Application Errors**:
- Invalid input validation
- Business logic errors
- State management issues
- Resource exhaustion

### Recovery Testing
Tests verify system recovery from:
- Transient failures with retry logic
- Service restoration after outages
- Graceful degradation scenarios
- Circuit breaker functionality

## Performance Testing

### Performance Considerations
Tests are designed for:
- Fast execution (< 5 minutes for full suite)
- Parallel execution where possible
- Efficient resource usage
- Proper cleanup and teardown

### Timeout Management
- Individual test timeouts (30 seconds default)
- Suite-level timeout (5 minutes)
- Service call timeouts (configurable)
- Async operation timeouts

## Continuous Integration

### CI/CD Integration
Test suite designed for:
- Automated CI/CD pipelines
- Docker container testing
- Multi-environment testing
- Parallel test execution

### Quality Gates
Tests enforce quality standards:
- Code coverage thresholds
- Performance benchmarks
- Error rate limits
- Security scanning

## Best Practices

### Writing Tests
Follow these guidelines:
- Use descriptive test names
- Include docstrings explaining test purpose
- Mock external dependencies
- Test both success and failure paths
- Use appropriate assertions
- Clean up resources properly

### Test Organization
- Group related tests in classes
- Use fixtures for common setup
- Parameterize tests for multiple scenarios  
- Separate unit and integration tests
- Include performance considerations

### Debugging Tests
For test debugging:
- Use verbose output (`-v` flag)
- Enable detailed logging
- Run specific tests in isolation
- Use debugger integration
- Check mock configurations

## Troubleshooting

### Common Issues

**Import Errors**:
- Ensure all dependencies installed
- Check Python path configuration
- Verify module structure

**Async Issues**:  
- Use proper async/await patterns
- Configure asyncio mode correctly
- Handle async fixtures properly

**Mock Issues**:
- Verify mock setup and teardown
- Check mock call expectations  
- Ensure proper patching scope

**Service Issues**:
- Check service availability
- Verify configuration settings
- Review network connectivity

### Getting Help
- Check test output logs
- Review pytest documentation
- Examine mock configurations
- Verify service connections
- Use debugging tools

## Metrics and Reporting

### Test Coverage
- Aim for >80% code coverage
- Focus on critical path coverage
- Include error path testing
- Document coverage gaps

### Test Reports
- HTML coverage reports
- JUnit XML for CI integration
- Performance metrics
- Error rate tracking

### Quality Metrics
- Test execution time
- Success/failure rates  
- Code complexity metrics
- Maintainability indices

## Conclusion

This comprehensive test suite ensures the n8n workflow agent system is reliable, maintainable, and performs well under various conditions. The tests cover all major components, error scenarios, and integration points, providing confidence in system behavior and facilitating ongoing development.