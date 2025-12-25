# API Integration Tests - Quick Reference

## Setup

```bash
# Set environment variables
export OPENAI_API_KEY="your-doubao-api-key"
export OPENAI_API_BASE="https://ark.cn-beijing.volces.com/api/v3"
export OPENAI_MODEL_NAME="doubao-pro-32k"
```

## Run Tests

```bash
# All integration tests
pytest tests/test_api_integration.py -v -m integration

# Specific test class
pytest tests/test_api_integration.py::TestAgentExecutionWorkflow -v -m integration

# Specific test
pytest tests/test_api_integration.py::TestAgentExecutionWorkflow::test_sync_agent_execution_workflow -v -m integration

# With output
pytest tests/test_api_integration.py -v -m integration -s

# With coverage
pytest tests/test_api_integration.py -v -m integration --cov=src.api
```

## Test Classes

| Class | Tests | Description |
|-------|-------|-------------|
| `TestAgentExecutionWorkflow` | 2 | Agent execution via API |
| `TestPipelineExecutionWorkflow` | 2 | Pipeline execution via API |
| `TestExecutionCancellation` | 1 | Execution cancellation |
| `TestExecutionListing` | 1 | Execution listing/filtering |
| `TestConfigurationAPI` | 2 | Config read/write |
| `TestEndToEndWorkflow` | 1 | Complete workflow |

## Key Tests

### Agent Execution
```bash
# Sync execution
pytest tests/test_api_integration.py::TestAgentExecutionWorkflow::test_sync_agent_execution_workflow -v -m integration

# Async with progress
pytest tests/test_api_integration.py::TestAgentExecutionWorkflow::test_async_agent_execution_with_progress -v -m integration
```

### Pipeline Execution
```bash
# With code node
pytest tests/test_api_integration.py::TestPipelineExecutionWorkflow::test_pipeline_execution_with_code_node -v -m integration

# Error handling
pytest tests/test_api_integration.py::TestPipelineExecutionWorkflow::test_pipeline_execution_error_handling -v -m integration
```

### End-to-End
```bash
# Complete workflow
pytest tests/test_api_integration.py::TestEndToEndWorkflow::test_complete_workflow_agent_to_pipeline -v -m integration
```

## Verification

```bash
# Check environment
env | grep OPENAI

# Test API connection
python -c "import os; from openai import OpenAI; client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'), base_url=os.getenv('OPENAI_API_BASE')); print('✓ Connected')"

# Verify test discovery
pytest tests/test_api_integration.py --collect-only -m integration
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Tests skipped | Set environment variables |
| Connection error | Check API endpoint and key |
| Timeout | Increase timeout or check API quota |
| Agent not found | Verify test fixtures |

## Expected Duration

- Single agent test: ~5-10 seconds
- Pipeline test: ~15-30 seconds
- Full suite: ~1-2 minutes

## Requirements

- **Python**: 3.12+
- **Doubao Pro**: Valid API credentials
- **Network**: Access to Doubao API endpoint
- **Quota**: Sufficient API quota

## Related Commands

```bash
# Run all API tests (unit + integration)
pytest tests/test_api_*.py -v

# Run only unit tests
pytest tests/test_api_*.py -v -m "not integration"

# Run with specific marker
pytest -v -m integration

# Generate coverage report
pytest tests/test_api_integration.py -v -m integration --cov=src.api --cov-report=html
```

## CI/CD Integration

```yaml
# GitHub Actions
- name: Run integration tests
  env:
    OPENAI_API_KEY: ${{ secrets.DOUBAO_API_KEY }}
    OPENAI_API_BASE: ${{ secrets.DOUBAO_API_BASE }}
    OPENAI_MODEL_NAME: ${{ secrets.DOUBAO_MODEL_NAME }}
  run: pytest tests/test_api_integration.py -v -m integration
```

## Documentation

- Full Guide: [api-integration-tests-guide.md](api-integration-tests-guide.md)
- API Setup: [api-setup-guide.md](api-setup-guide.md)
- API Design: [api-design-specification.md](api-design-specification.md)
