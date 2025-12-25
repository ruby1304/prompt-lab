# API Unit Tests - Quick Reference

## Overview

Comprehensive unit tests for all API endpoints covering request validation, error handling, and edge cases.

## Test Files

### Main Test Files
- `tests/test_api_comprehensive.py` - Cross-cutting concerns and edge cases (54 tests)
- `tests/test_api_agents.py` - Agent management endpoints (14 tests)
- `tests/test_api_pipelines.py` - Pipeline management endpoints (18 tests)
- `tests/test_api_config.py` - Configuration endpoints (11 tests)
- `tests/test_api_executions.py` - Async execution endpoints (28 tests)

**Total: 125 API tests**

## Running Tests

### Run All API Tests
```bash
pytest tests/test_api_*.py -v
```

### Run Specific Test File
```bash
pytest tests/test_api_comprehensive.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_api_comprehensive.py::TestRequestValidation -v
```

### Run Specific Test
```bash
pytest tests/test_api_comprehensive.py::TestRequestValidation::test_invalid_json_body -v
```

### Run with Coverage
```bash
pytest tests/test_api_*.py --cov=src/api --cov-report=html
```

## Test Categories

### 1. System Endpoints
Tests for health check, root, and documentation endpoints.

```python
# Example
def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

### 2. Request Validation
Tests for input validation and error handling.

```python
# Example
def test_invalid_json_body(client):
    response = client.post(
        "/api/v1/agents",
        data="not valid json",
        headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
```

### 3. Error Handling
Tests for various HTTP error codes and error response formats.

```python
# Example
def test_404_not_found_agent(client):
    response = client.get("/api/v1/agents/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"]["error"] == "NotFound"
```

### 4. Response Formats
Tests for consistent response structure across endpoints.

```python
# Example
def test_agent_list_response_format(client):
    response = client.get("/api/v1/agents")
    data = response.json()
    assert "agents" in data
    assert "pagination" in data
```

### 5. Pagination
Tests for pagination behavior and edge cases.

```python
# Example
def test_custom_page_size(client):
    response = client.get("/api/v1/agents?page_size=5")
    pagination = response.json()["pagination"]
    assert pagination["page_size"] == 5
```

### 6. Filtering and Search
Tests for filtering and search functionality.

```python
# Example
def test_agent_category_filter(client):
    response = client.get("/api/v1/agents?category=production")
    for agent in response.json()["agents"]:
        assert agent["category"] == "production"
```

### 7. Edge Cases
Tests for boundary conditions and unusual inputs.

```python
# Example
def test_unicode_characters(client):
    response = client.post(
        "/api/v1/agents",
        json={
            "id": "test_unicode",
            "name": "测试 Agent 🚀",
            # ... other fields
        }
    )
    assert response.status_code in [201, 409]
```

### 8. Concurrency
Tests for concurrent request handling.

```python
# Example
def test_concurrent_reads(client):
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(lambda: client.get("/api/v1/agents")) 
                   for _ in range(10)]
        results = [f.result() for f in futures]
    assert all(r.status_code == 200 for r in results)
```

## Test Fixtures

### Client Fixture
```python
@pytest.fixture
def client():
    """Create a test client."""
    app = create_app()
    return TestClient(app)
```

### Test Registry Fixture
```python
@pytest.fixture
def test_registry_config():
    """Create a temporary registry config for testing."""
    config = {
        "version": "1.0",
        "agents": {
            "test_agent": {
                "name": "Test Agent",
                # ... other fields
            }
        }
    }
    # Create temp file and return path
```

## Common Test Patterns

### Testing Success Response
```python
response = client.get("/api/v1/agents")
assert response.status_code == 200
data = response.json()
assert "agents" in data
```

### Testing Error Response
```python
response = client.get("/api/v1/agents/nonexistent")
assert response.status_code == 404
data = response.json()
assert "detail" in data
assert data["detail"]["error"] == "NotFound"
```

### Testing Validation Error
```python
response = client.post("/api/v1/agents", json={"id": "test"})
assert response.status_code == 422
data = response.json()
assert "detail" in data
```

### Testing Pagination
```python
response = client.get("/api/v1/agents?page=1&page_size=10")
assert response.status_code == 200
pagination = response.json()["pagination"]
assert pagination["page"] == 1
assert pagination["page_size"] == 10
```

### Testing Filtering
```python
response = client.get("/api/v1/agents?category=production")
assert response.status_code == 200
for agent in response.json()["agents"]:
    assert agent["category"] == "production"
```

## Test Coverage

### Endpoints Covered
- ✅ System endpoints (health, root, docs)
- ✅ Agent management (list, get, create, update)
- ✅ Pipeline management (list, get, create, update)
- ✅ Configuration (read, write)
- ✅ Async execution (start, status, cancel)
- ✅ Progress query (get, WebSocket)

### Validation Covered
- ✅ Invalid JSON
- ✅ Missing required fields
- ✅ Invalid data types
- ✅ Invalid enum values
- ✅ Invalid ID formats
- ✅ Invalid pagination parameters

### Error Codes Covered
- ✅ 200 OK
- ✅ 201 Created
- ✅ 204 No Content
- ✅ 400 Bad Request
- ✅ 404 Not Found
- ✅ 409 Conflict
- ✅ 422 Validation Error
- ✅ 500 Internal Server Error

### Edge Cases Covered
- ✅ Empty strings
- ✅ Very long strings (10,000+ chars)
- ✅ Special characters
- ✅ Unicode characters
- ✅ Null values
- ✅ Deeply nested JSON
- ✅ Concurrent requests

## Best Practices

### 1. Test Isolation
Each test should be independent and not rely on other tests.

```python
# Good
def test_create_agent(client):
    response = client.post("/api/v1/agents", json={...})
    assert response.status_code == 201

# Bad - relies on previous test
def test_get_agent(client):
    # Assumes agent was created in previous test
    response = client.get("/api/v1/agents/test_agent")
```

### 2. Clear Test Names
Use descriptive names that explain what is being tested.

```python
# Good
def test_create_agent_with_missing_required_fields_returns_422():
    ...

# Bad
def test_agent():
    ...
```

### 3. Arrange-Act-Assert
Structure tests with clear setup, execution, and verification.

```python
def test_example(client):
    # Arrange
    agent_data = {"id": "test", ...}
    
    # Act
    response = client.post("/api/v1/agents", json=agent_data)
    
    # Assert
    assert response.status_code == 201
```

### 4. Test Both Success and Failure
Test both happy paths and error cases.

```python
def test_get_existing_agent(client):
    # Test success case
    ...

def test_get_nonexistent_agent(client):
    # Test error case
    ...
```

### 5. Use Fixtures for Reusable Setup
Create fixtures for common test setup.

```python
@pytest.fixture
def sample_agent():
    return {
        "id": "test_agent",
        "name": "Test Agent",
        # ... other fields
    }

def test_create_agent(client, sample_agent):
    response = client.post("/api/v1/agents", json=sample_agent)
    assert response.status_code == 201
```

## Troubleshooting

### Test Fails with 500 Error
Check the application logs for the actual error:
```python
response = client.get("/api/v1/agents")
if response.status_code == 500:
    print(response.json())  # See error details
```

### Test Fails with 422 Validation Error
Check which field failed validation:
```python
response = client.post("/api/v1/agents", json={...})
if response.status_code == 422:
    print(response.json()["detail"])  # See validation errors
```

### Test Hangs or Times Out
Check for blocking operations or infinite loops in the code being tested.

### Fixture Not Found
Ensure the fixture is defined in the same file or in `conftest.py`.

## Related Documentation

- [API Design Specification](./api-design-specification.md)
- [API Setup Guide](./api-setup-guide.md)
- [API Routes Implementation Guide](./api-routes-implementation-guide.md)
- [Model Serialization Guide](./model-serialization-guide.md)

## Requirements Validated

- ✅ **Requirement 8.2**: Core function API availability
- ✅ **Requirement 8.4**: Configuration API read-write

## Summary

The API unit tests provide comprehensive coverage of:
- All API endpoints
- Request validation
- Error handling
- Response formats
- Edge cases
- Concurrency

**Total: 125 tests, all passing**
