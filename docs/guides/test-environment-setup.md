# Test Environment Setup Guide

This guide explains how to configure the test environment for running integration tests with Doubao Pro API.

## Overview

The Prompt Lab project uses a dual testing strategy:

1. **Unit Tests**: Test individual components in isolation (no LLM calls required)
2. **Integration Tests**: Test complete workflows with real LLM API calls (requires Doubao Pro configuration)

## Quick Start

### 1. Create Test Environment File

Copy the example environment file:

```bash
cp .env.example .env.test
```

### 2. Configure Doubao Pro API

Edit `.env.test` and set your Doubao Pro credentials:

```bash
# Required: Doubao Pro API Configuration
OPENAI_API_KEY=your_actual_api_key_here
OPENAI_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
OPENAI_MODEL_NAME=doubao-1-5-pro-32k-250115

# Optional: Model parameters
OPENAI_TEMPERATURE=0.3
OPENAI_MAX_TOKENS=2000
```

### 3. Validate Configuration

Run the validation script to verify your setup:

```bash
python scripts/validate_test_env.py
```

This will check:
- ✓ Environment file exists
- ✓ Required variables are set
- ✓ API credentials are valid
- ✓ API connection works
- ✓ Test directories exist

### 4. Run Tests

Once validated, you can run tests:

```bash
# Run all tests (unit + integration)
pytest tests/ -v

# Run only unit tests (no LLM calls)
pytest tests/ -m "not integration" -v

# Run only integration tests (requires API)
pytest tests/ -m integration -v

# Run specific test file
pytest tests/test_integration_pipeline.py -v
```

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your Doubao Pro API key | `6ec0505d-6342-4ad1-b4f9-229ee32fbf4c` |
| `OPENAI_BASE_URL` | Doubao API endpoint | `https://ark.cn-beijing.volces.com/api/v3` |
| `OPENAI_MODEL_NAME` | Doubao Pro model name | `doubao-1-5-pro-32k-250115` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_TEMPERATURE` | Model temperature | `0.3` |
| `OPENAI_MAX_TOKENS` | Maximum tokens per request | `2000` |
| `TEST_TIMEOUT` | Test timeout in seconds | `60` |
| `TEST_MAX_RETRIES` | Maximum retry attempts | `3` |
| `TEST_CONCURRENT_WORKERS` | Concurrent test workers | `2` |
| `LOG_LEVEL` | Logging level | `INFO` |

### Test-Specific Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `TEST_DATA_DIR` | Test fixtures directory | `tests/fixtures` |
| `TEST_OUTPUT_DIR` | Test output directory | `tests/output` |
| `TEST_DB_PATH` | Test database path | `tests/fixtures/test.db` |
| `TEST_CACHE_DIR` | Test cache directory | `tests/.cache` |
| `ENABLE_PROPERTY_TESTS` | Enable property-based tests | `true` |
| `ENABLE_INTEGRATION_TESTS` | Enable integration tests | `true` |
| `ENABLE_PERFORMANCE_TESTS` | Enable performance tests | `false` |

## Environment File Priority

The test environment loads configuration in this order:

1. `.env.test` (highest priority - used for testing)
2. `.env` (fallback - used for development)
3. System environment variables (lowest priority)

This allows you to:
- Keep production credentials in `.env`
- Use separate test credentials in `.env.test`
- Override any setting via system environment variables

## Test Markers

Tests are marked with pytest markers to control execution:

### `@pytest.mark.integration`

Marks tests that require real LLM API calls:

```python
@pytest.mark.integration
def test_pipeline_with_real_llm():
    """This test calls the real Doubao Pro API"""
    # Test implementation
```

Run only integration tests:
```bash
pytest -m integration
```

Skip integration tests:
```bash
pytest -m "not integration"
```

### `@pytest.mark.slow`

Marks tests that take a long time to run:

```python
@pytest.mark.slow
def test_large_batch_processing():
    """This test processes many items"""
    # Test implementation
```

Skip slow tests:
```bash
pytest -m "not slow"
```

### `@pytest.mark.unit`

Marks pure unit tests (no external dependencies):

```python
@pytest.mark.unit
def test_data_model_validation():
    """This test only validates data models"""
    # Test implementation
```

Run only unit tests:
```bash
pytest -m unit
```

## Validation Script Usage

The validation script provides detailed feedback on your configuration:

### Basic Usage

```bash
python scripts/validate_test_env.py
```

### Custom Environment File

```bash
python scripts/validate_test_env.py --env-file .env.production
```

### Skip API Connection Test

```bash
python scripts/validate_test_env.py --skip-api-test
```

### Example Output

```
============================================================
Test Environment Validation
============================================================

✓ Environment file found: .env.test
✓ Loaded environment variables from .env.test

Checking required environment variables:
✓ OPENAI_API_KEY = 6ec0505d...bf4c
✓ OPENAI_BASE_URL = https://ark.cn-beijing.volces.com/api/v3
✓ OPENAI_MODEL_NAME = doubao-1-5-pro-32k-250115

Optional configuration:
  OPENAI_TEMPERATURE = 0.3
  OPENAI_MAX_TOKENS = 2000
  TEST_TIMEOUT = 60
  TEST_MAX_RETRIES = 3
  LOG_LEVEL = INFO

Validating configuration values:
✓ API key format looks valid
✓ Model name 'doubao-1-5-pro-32k-250115' looks valid
✓ API endpoint 'https://ark.cn-beijing.volces.com/api/v3' is a Doubao endpoint

ℹ Testing API connection...
ℹ Sending test request to API...
✓ API connection successful! Response: Hello

Checking test directories:
✓ Directory exists: tests/fixtures
✓ Directory exists: tests/output
✓ Directory exists: tests/.cache

============================================================
Validation Summary
============================================================

✓ All validation checks passed!

ℹ You can now run integration tests with:
  pytest tests/ -m integration
  pytest tests/ -v
```

## Troubleshooting

### Missing API Key

**Error:**
```
✗ OPENAI_API_KEY is not configured
```

**Solution:**
1. Open `.env.test`
2. Replace `your_doubao_api_key_here` with your actual API key
3. Run validation again

### API Connection Failed

**Error:**
```
✗ API connection failed: Authentication error
```

**Solution:**
1. Verify your API key is correct
2. Check that the API endpoint is accessible
3. Ensure your API key has proper permissions
4. Try the connection test manually:
   ```python
   from langchain_openai import ChatOpenAI
   llm = ChatOpenAI(
       model="doubao-1-5-pro-32k-250115",
       openai_api_key="your_key",
       openai_api_base="https://ark.cn-beijing.volces.com/api/v3"
   )
   response = llm.invoke("Hello")
   print(response.content)
   ```

### Wrong Model Name

**Warning:**
```
⚠ Model name 'gpt-4' does not contain 'doubao'
```

**Solution:**
1. Update `OPENAI_MODEL_NAME` in `.env.test`
2. Use a Doubao Pro model: `doubao-1-5-pro-32k-250115`
3. Run validation again

### Test Directories Missing

**Warning:**
```
⚠ Directory not found: tests/fixtures
```

**Solution:**
The validation script will automatically create missing directories. If you see this warning, the directories will be created for you.

## Best Practices

### 1. Separate Test and Production Credentials

Always use separate API keys for testing and production:

- `.env` → Production credentials
- `.env.test` → Test credentials

### 2. Use Lower Rate Limits for Tests

Configure test-specific rate limits to avoid exhausting your API quota:

```bash
TEST_MAX_RETRIES=2
TEST_CONCURRENT_WORKERS=2
```

### 3. Run Unit Tests First

Before running integration tests, ensure unit tests pass:

```bash
# Fast: Run unit tests only
pytest -m "not integration" -v

# Slow: Run integration tests
pytest -m integration -v
```

### 4. Use Test Markers Consistently

Mark all tests that make LLM calls:

```python
@pytest.mark.integration
def test_with_llm():
    # This test requires API access
    pass
```

### 5. Validate Before CI/CD

Always validate your test environment before pushing:

```bash
python scripts/validate_test_env.py
pytest -m "not integration" -v  # Quick check
```

## CI/CD Configuration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        pip install -e ".[test]"
    
    - name: Create test environment
      run: |
        echo "OPENAI_API_KEY=${{ secrets.DOUBAO_API_KEY }}" >> .env.test
        echo "OPENAI_BASE_URL=${{ secrets.DOUBAO_API_BASE }}" >> .env.test
        echo "OPENAI_MODEL_NAME=doubao-1-5-pro-32k-250115" >> .env.test
    
    - name: Validate test environment
      run: |
        python scripts/validate_test_env.py --skip-api-test
    
    - name: Run unit tests
      run: |
        pytest -m "not integration" -v --cov=src
    
    - name: Run integration tests
      if: github.event_name == 'push' && github.ref == 'refs/heads/main'
      run: |
        pytest -m integration -v
```

## Security Notes

### 1. Never Commit API Keys

Add to `.gitignore`:
```
.env
.env.test
.env.local
.env.*.local
```

### 2. Use Environment Variables in CI

Store API keys as secrets in your CI/CD platform:
- GitHub Actions: Repository Secrets
- GitLab CI: CI/CD Variables
- Jenkins: Credentials

### 3. Rotate Keys Regularly

Change your API keys periodically and update `.env.test`.

### 4. Limit Key Permissions

Use API keys with minimal required permissions for testing.

## Additional Resources

- [Doubao API Documentation](https://www.volcengine.com/docs/82379)
- [pytest Documentation](https://docs.pytest.org/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [LangChain OpenAI Integration](https://python.langchain.com/docs/integrations/llms/openai)

## Support

If you encounter issues:

1. Run the validation script: `python scripts/validate_test_env.py`
2. Check the troubleshooting section above
3. Review test logs: `tests/test_run.log`
4. Open an issue with validation output and error messages
