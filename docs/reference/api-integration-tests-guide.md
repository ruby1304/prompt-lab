# API Integration Tests Guide

## Overview

The API integration tests (`tests/test_api_integration.py`) provide comprehensive end-to-end testing of the Prompt Lab API layer using real Doubao Pro model execution. These tests verify complete workflows including agent execution, pipeline execution, async operations, and progress tracking.

**Requirements Validated:** 8.2, 8.5

## Prerequisites

### Required Environment Variables

The integration tests require valid Doubao Pro API credentials:

```bash
# Required environment variables
export OPENAI_API_KEY="your-doubao-api-key"
export OPENAI_API_BASE="https://ark.cn-beijing.volces.com/api/v3"
export OPENAI_MODEL_NAME="doubao-pro-32k"  # or your specific model
```

### Configuration File

Alternatively, create a `.env` file in the project root:

```env
OPENAI_API_KEY=your-doubao-api-key
OPENAI_API_BASE=https://ark.cn-beijing.volces.com/api/v3
OPENAI_MODEL_NAME=doubao-pro-32k
```

### Verification

Before running tests, verify your configuration:

```bash
# Check environment variables
echo $OPENAI_API_KEY
echo $OPENAI_API_BASE
echo $OPENAI_MODEL_NAME

# Test API connection
python -c "import os; from openai import OpenAI; client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), base_url=os.getenv('OPENAI_API_BASE')); print('✓ API connection successful')"
```

## Running Integration Tests

### Run All Integration Tests

```bash
# Run all integration tests
pytest tests/test_api_integration.py -v -m integration

# Run with detailed output
pytest tests/test_api_integration.py -v -m integration -s

# Run with coverage
pytest tests/test_api_integration.py -v -m integration --cov=src.api
```

### Run Specific Test Classes

```bash
# Test agent execution workflow
pytest tests/test_api_integration.py::TestAgentExecutionWorkflow -v -m integration

# Test pipeline execution workflow
pytest tests/test_api_integration.py::TestPipelineExecutionWorkflow -v -m integration

# Test end-to-end workflow
pytest tests/test_api_integration.py::TestEndToEndWorkflow -v -m integration
```

### Run Specific Tests

```bash
# Test sync agent execution
pytest tests/test_api_integration.py::TestAgentExecutionWorkflow::test_sync_agent_execution_workflow -v -m integration

# Test async execution with progress
pytest tests/test_api_integration.py::TestAgentExecutionWorkflow::test_async_agent_execution_with_progress -v -m integration

# Test complete workflow
pytest tests/test_api_integration.py::TestEndToEndWorkflow::test_complete_workflow_agent_to_pipeline -v -m integration
```

## Test Coverage

### 1. Agent Execution Workflow (`TestAgentExecutionWorkflow`)

Tests complete agent execution via API:

- **test_sync_agent_execution_workflow**: Tests synchronous agent execution
  - Retrieves agent via API
  - Executes agent with inputs
  - Polls for completion
  - Verifies results from Doubao Pro

- **test_async_agent_execution_with_progress**: Tests async execution with progress tracking
  - Starts async execution
  - Queries progress endpoint
  - Tracks progress updates
  - Verifies completion

### 2. Pipeline Execution Workflow (`TestPipelineExecutionWorkflow`)

Tests complete pipeline execution via API:

- **test_pipeline_execution_with_code_node**: Tests pipeline with agent + code node
  - Retrieves pipeline via API
  - Executes pipeline with multiple steps
  - Tracks progress through steps
  - Verifies data flow and final output

- **test_pipeline_execution_error_handling**: Tests error handling
  - Tests invalid pipeline ID rejection
  - Tests missing input handling
  - Verifies error reporting

### 3. Execution Cancellation (`TestExecutionCancellation`)

Tests execution cancellation:

- **test_cancel_pending_execution**: Tests cancelling pending execution
  - Starts execution
  - Cancels immediately
  - Verifies cancellation status

### 4. Execution Listing (`TestExecutionListing`)

Tests execution listing and filtering:

- **test_list_executions_with_filters**: Tests listing with filters
  - Creates multiple executions
  - Lists all executions
  - Filters by type
  - Tests pagination

### 5. Configuration API (`TestConfigurationAPI`)

Tests configuration read/write:

- **test_read_agent_config**: Tests reading agent configuration
  - Reads config via API
  - Verifies format and fields

- **test_update_agent_config**: Tests updating agent configuration
  - Updates config via API
  - Verifies persistence
  - Reads back to confirm

### 6. End-to-End Workflow (`TestEndToEndWorkflow`)

Tests complete workflow:

- **test_complete_workflow_agent_to_pipeline**: Tests entire API workflow
  - Verifies agent exists
  - Verifies pipeline exists
  - Executes agent
  - Executes pipeline
  - Verifies both in execution list

## Test Fixtures

### verify_doubao_config

Module-scoped fixture that verifies Doubao Pro configuration before running tests. Skips all tests if configuration is missing.

### test_agent_config

Creates a temporary test agent configuration:
- Agent ID: `test_integration_agent`
- Single flow: `default`
- Uses configured Doubao Pro model
- Cleaned up after tests

### test_pipeline_config

Creates a temporary test pipeline configuration:
- Pipeline ID: `test_integration_pipeline`
- Two steps: agent + code node
- Tests data flow between steps
- Cleaned up after tests

### client

Creates FastAPI TestClient with real configuration for API testing.

## Expected Behavior

### Successful Test Run

When all tests pass, you should see:

```
tests/test_api_integration.py::TestAgentExecutionWorkflow::test_sync_agent_execution_workflow PASSED
✓ Agent retrieved: Test Integration Agent
✓ Execution started: exec_abc123
  Status: pending
  Status: running
  Status: completed
✓ Execution completed successfully
  Output: {'result': 'Four'}

tests/test_api_integration.py::TestPipelineExecutionWorkflow::test_pipeline_execution_with_code_node PASSED
✓ Pipeline retrieved: Test Integration Pipeline
✓ Pipeline execution started: exec_xyz789
  Step 1/2: step1
  Step 2/2: step2
✓ Pipeline completed successfully
  Final result: {'processed': 'Processed: ...'}

...

============================== 9 passed in 45.23s ==============================
```

### Skipped Tests

When Doubao configuration is missing:

```
tests/test_api_integration.py::TestAgentExecutionWorkflow::test_sync_agent_execution_workflow SKIPPED
(Missing required environment variables for Doubao Pro: OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_MODEL_NAME
Please configure:
  - OPENAI_API_KEY: Your Doubao API key
  - OPENAI_API_BASE: Doubao API endpoint
  - OPENAI_MODEL_NAME: Doubao Pro model name)

============================== 9 skipped in 1.86s ==============================
```

## Troubleshooting

### Tests Skip Due to Missing Configuration

**Problem**: All tests are skipped with message about missing environment variables.

**Solution**:
1. Set required environment variables
2. Verify variables are set: `env | grep OPENAI`
3. Restart terminal/IDE to pick up new variables

### API Connection Errors

**Problem**: Tests fail with connection errors.

**Solution**:
1. Verify API endpoint is accessible
2. Check firewall/proxy settings
3. Verify API key is valid
4. Test connection manually:
   ```bash
   curl -H "Authorization: Bearer $OPENAI_API_KEY" $OPENAI_API_BASE/models
   ```

### Execution Timeouts

**Problem**: Tests timeout waiting for execution completion.

**Solution**:
1. Increase timeout values in test code
2. Check Doubao API quota/rate limits
3. Verify model name is correct
4. Check for API service issues

### Agent/Pipeline Not Found

**Problem**: Tests skip with "Test agent not found" or "Test pipeline not found".

**Solution**:
1. Verify test fixtures are creating configurations correctly
2. Check file permissions in `agents/` and `pipelines/` directories
3. Verify agent registry is loading correctly

### Execution Fails

**Problem**: Execution starts but fails during processing.

**Solution**:
1. Check execution error details in test output
2. Verify agent configuration is valid
3. Check input format matches agent expectations
4. Review Doubao API error messages

## Performance Considerations

### Test Duration

Integration tests use real API calls and may take time:
- Single agent execution: ~5-10 seconds
- Pipeline execution: ~15-30 seconds
- Complete test suite: ~1-2 minutes

### API Quota

Each test run consumes API quota:
- ~10-15 API calls per full test run
- Consider running selectively during development
- Use CI/CD for full test runs

### Parallel Execution

Integration tests should NOT be run in parallel:
- Tests may interfere with shared resources
- Use `-n 1` or avoid `-n` flag with pytest-xdist

## Best Practices

### Development Workflow

1. **Unit tests first**: Run unit tests before integration tests
2. **Selective testing**: Run specific test classes during development
3. **Full suite in CI**: Run complete suite in CI/CD pipeline
4. **Monitor quota**: Track API usage to avoid quota exhaustion

### Test Maintenance

1. **Keep tests independent**: Each test should be self-contained
2. **Clean up resources**: Use fixtures for setup/teardown
3. **Handle flakiness**: Add retries for network-related failures
4. **Update timeouts**: Adjust timeouts based on actual API performance

### Debugging

1. **Use -s flag**: See print statements during test execution
2. **Use -vv flag**: Get more detailed output
3. **Use --tb=long**: Get full tracebacks on failures
4. **Add logging**: Enable debug logging for detailed information

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: API Integration Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run integration tests
      env:
        OPENAI_API_KEY: ${{ secrets.DOUBAO_API_KEY }}
        OPENAI_API_BASE: ${{ secrets.DOUBAO_API_BASE }}
        OPENAI_MODEL_NAME: ${{ secrets.DOUBAO_MODEL_NAME }}
      run: |
        pytest tests/test_api_integration.py -v -m integration --cov=src.api
    
    - name: Upload coverage
      uses: codecov/codecov-action@v2
```

### Environment Secrets

Store credentials as secrets in your CI/CD platform:
- `DOUBAO_API_KEY`: Your Doubao API key
- `DOUBAO_API_BASE`: Doubao API endpoint URL
- `DOUBAO_MODEL_NAME`: Doubao Pro model name

## Related Documentation

- [API Setup Guide](api-setup-guide.md) - API server setup and configuration
- [API Design Specification](api-design-specification.md) - API endpoint specifications
- [Async Execution API Guide](async-execution-api-guide.md) - Async execution details
- [Progress Query API Guide](progress-query-api-guide.md) - Progress tracking details

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review related documentation
3. Check test output for specific error messages
4. Verify Doubao API status and quota
