# Tests Directory

This directory contains all test files for the Prompt Lab project.

## Test Structure

```
tests/
├── conftest.py              # Pytest configuration and shared fixtures
├── fixtures/                # Test data and fixtures
│   ├── agents/             # Test agent configurations
│   ├── pipelines/          # Test pipeline configurations
│   └── testsets/           # Test datasets
├── output/                  # Test output files (gitignored)
├── .cache/                  # Test cache (gitignored)
└── test_*.py               # Test files
```

## Running Tests

### Quick Start

1. **Configure test environment:**
   ```bash
   cp .env.example .env.test
   # Edit .env.test with your Doubao Pro API credentials
   ```

2. **Validate configuration:**
   ```bash
   python scripts/validate_test_env.py
   ```

3. **Run tests:**
   ```bash
   # All tests
   pytest tests/ -v
   
   # Unit tests only (fast, no API calls)
   pytest tests/ -m "not integration" -v
   
   # Integration tests only (requires API)
   pytest tests/ -m integration -v
   ```

## Test Categories

### Unit Tests
- Test individual components in isolation
- No external dependencies (LLM, database, etc.)
- Fast execution
- Run with: `pytest -m "not integration"`

### Integration Tests
- Test complete workflows with real LLM API calls
- Require Doubao Pro API configuration
- Slower execution
- Marked with `@pytest.mark.integration`
- Run with: `pytest -m integration`

### Property-Based Tests
- Use Hypothesis for property-based testing
- Generate random test cases
- Minimum 100 iterations per property
- Test universal properties across all inputs

## Environment Configuration

### Required Variables (for integration tests)

```bash
OPENAI_API_KEY=your_doubao_api_key
OPENAI_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
OPENAI_MODEL_NAME=doubao-1-5-pro-32k-250115
```

### Optional Variables

```bash
OPENAI_TEMPERATURE=0.3
OPENAI_MAX_TOKENS=2000
TEST_TIMEOUT=60
TEST_MAX_RETRIES=3
LOG_LEVEL=INFO
```

See [Test Environment Setup Guide](../docs/guides/test-environment-setup.md) for detailed configuration instructions.

## Test Markers

Tests use pytest markers to control execution:

- `@pytest.mark.integration` - Requires real LLM API calls
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.unit` - Pure unit tests

Examples:

```python
@pytest.mark.integration
def test_pipeline_with_real_llm():
    """This test calls the real Doubao Pro API"""
    pass

@pytest.mark.unit
def test_data_model_validation():
    """This test only validates data models"""
    pass
```

## Writing Tests

### Unit Test Example

```python
import pytest
from src.models import PipelineConfig

@pytest.mark.unit
def test_pipeline_config_validation():
    """Test pipeline configuration validation"""
    config = PipelineConfig(
        id="test",
        name="Test Pipeline",
        steps=[]
    )
    assert config.id == "test"
    assert config.name == "Test Pipeline"
```

### Integration Test Example

```python
import pytest
import os

@pytest.mark.integration
class TestPipelineIntegration:
    """Integration tests for pipeline execution"""
    
    def test_env_variables_loaded(self):
        """Verify environment is configured"""
        api_key = os.getenv("OPENAI_API_KEY")
        assert api_key is not None, "OPENAI_API_KEY not set"
    
    def test_pipeline_execution(self):
        """Test complete pipeline execution with real LLM"""
        # Test implementation using real Doubao Pro API
        pass
```

### Property-Based Test Example

```python
import pytest
from hypothesis import given, strategies as st

# Feature: project-production-readiness, Property 1: Registry loading completeness
@given(
    agent_id=st.text(min_size=1, max_size=50),
    agent_name=st.text(min_size=1, max_size=100)
)
def test_agent_registration_property(agent_id, agent_name):
    """Test agent registration with random inputs"""
    # Property test implementation
    pass
```

## Test Fixtures

Common fixtures are defined in `conftest.py`:

- `temp_dir` - Temporary directory for test files
- `sample_pipeline_config` - Example pipeline configuration
- `sample_testset` - Example test dataset
- `mock_agent` - Mocked agent for unit tests
- `mock_load_agent` - Mocked agent loader
- `mock_run_flow_with_tokens` - Mocked flow execution

Usage:

```python
def test_with_fixture(temp_dir, sample_pipeline_config):
    """Test using fixtures"""
    # temp_dir and sample_pipeline_config are automatically provided
    pass
```

## Coverage Reports

Generate coverage reports:

```bash
# Terminal report
pytest --cov=src --cov-report=term-missing

# HTML report
pytest --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

## Continuous Integration

Tests run automatically on:
- Pull requests
- Pushes to main branch

CI configuration:
- Unit tests: Always run
- Integration tests: Run on main branch only
- Coverage threshold: 80%

## Troubleshooting

### Tests Fail with "OPENAI_API_KEY not set"

**Solution:** Configure `.env.test` file with your API credentials.

```bash
python scripts/validate_test_env.py
```

### Tests Timeout

**Solution:** Increase timeout in `.env.test`:

```bash
TEST_TIMEOUT=120
```

### Import Errors

**Solution:** Install the package in development mode:

```bash
pip install -e ".[test]"
```

### Hypothesis Finds Counterexample

**Solution:** This is expected! Property-based tests are designed to find edge cases. Review the counterexample and either:
1. Fix the code to handle the edge case
2. Update the test to exclude invalid inputs
3. Update the specification if needed

## Best Practices

1. **Write unit tests first** - Fast feedback loop
2. **Mark integration tests** - Use `@pytest.mark.integration`
3. **Use fixtures** - Avoid code duplication
4. **Test edge cases** - Use property-based testing
5. **Keep tests isolated** - No shared state between tests
6. **Use descriptive names** - Test names should explain what they test
7. **Validate environment** - Run validation script before testing

## Resources

- [Test Environment Setup Guide](../docs/guides/test-environment-setup.md)
- [pytest Documentation](https://docs.pytest.org/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Project Architecture](../docs/ARCHITECTURE.md)

## Support

For issues or questions:
1. Check the [Test Environment Setup Guide](../docs/guides/test-environment-setup.md)
2. Run validation: `python scripts/validate_test_env.py`
3. Review test logs: `tests/test_run.log`
4. Open an issue with error details
