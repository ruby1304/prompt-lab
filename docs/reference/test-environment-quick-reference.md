# Test Environment Quick Reference

Quick reference for configuring and validating the test environment.

## Setup (3 Steps)

```bash
# 1. Create test environment file
cp .env.example .env.test

# 2. Edit with your credentials
# Edit .env.test: Set OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL_NAME

# 3. Validate
python scripts/validate_test_env.py
```

## Required Environment Variables

```bash
OPENAI_API_KEY=your_doubao_api_key
OPENAI_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
OPENAI_MODEL_NAME=doubao-1-5-pro-32k-250115
```

## Running Tests

```bash
# All tests
pytest tests/ -v

# Unit tests only (fast, no API)
pytest -m "not integration" -v

# Integration tests only (requires API)
pytest -m integration -v

# Specific test file
pytest tests/test_integration_pipeline.py -v

# With coverage
pytest --cov=src --cov-report=term-missing
```

## Validation Commands

```bash
# Full validation (includes API test)
python scripts/validate_test_env.py

# Skip API connection test
python scripts/validate_test_env.py --skip-api-test

# Use custom env file
python scripts/validate_test_env.py --env-file .env.production
```

## Test Markers

```bash
# Run only integration tests
pytest -m integration

# Skip integration tests
pytest -m "not integration"

# Run only slow tests
pytest -m slow

# Skip slow tests
pytest -m "not slow"

# Run only unit tests
pytest -m unit
```

## Common Issues

### Missing API Key
```bash
# Error: OPENAI_API_KEY is not configured
# Fix: Edit .env.test and set your API key
```

### API Connection Failed
```bash
# Error: API connection failed
# Fix: Verify credentials and endpoint
python scripts/validate_test_env.py
```

### Import Errors
```bash
# Error: ModuleNotFoundError
# Fix: Install in development mode
pip install -e ".[test]"
```

## Environment File Priority

1. `.env.test` (highest - for testing)
2. `.env` (fallback - for development)
3. System environment variables (lowest)

## Test Categories

| Category | Marker | API Required | Speed |
|----------|--------|--------------|-------|
| Unit | `@pytest.mark.unit` | No | Fast |
| Integration | `@pytest.mark.integration` | Yes | Slow |
| Property | Hypothesis | Varies | Medium |

## Validation Output

✓ = Success  
✗ = Error  
⚠ = Warning  
ℹ = Info

## Quick Troubleshooting

| Issue | Command | Fix |
|-------|---------|-----|
| Config invalid | `python scripts/validate_test_env.py` | Check output |
| Tests fail | `pytest -v` | Check logs |
| Import error | `pip install -e ".[test]"` | Reinstall |
| API timeout | Edit `.env.test` | Increase `TEST_TIMEOUT` |

## Files

- `.env.test` - Test environment configuration
- `.env.example` - Template for environment files
- `tests/conftest.py` - Pytest configuration
- `scripts/validate_test_env.py` - Validation script
- `docs/guides/test-environment-setup.md` - Full guide

## See Also

- [Test Environment Setup Guide](../guides/test-environment-setup.md) - Detailed guide
- [Tests README](../../tests/README.md) - Test directory overview
- [Architecture](../ARCHITECTURE.md) - System architecture
