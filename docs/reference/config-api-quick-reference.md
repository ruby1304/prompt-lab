# Configuration API Quick Reference

Quick reference guide for the Configuration File Read/Write API endpoints.

## Overview

The Configuration API provides programmatic access to agent and pipeline YAML configuration files through REST endpoints.

## Base URL

```
http://localhost:8000/api/v1/config
```

## Endpoints

### Agent Configuration

#### Read Agent Configuration

```http
GET /config/agents/{agent_id}
```

**Response:**
```json
{
  "id": "mem_l1_summarizer",
  "config": {
    "name": "一级记忆总结",
    "model": "doubao-pro",
    "prompts": {
      "system": "...",
      "user": "..."
    }
  },
  "file_path": "agents/mem_l1_summarizer/agent.yaml",
  "last_modified": "2024-12-17T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Configuration retrieved successfully
- `404 Not Found` - Agent not found
- `500 Internal Server Error` - Server error

#### Update Agent Configuration

```http
PUT /config/agents/{agent_id}
```

**Request Body:**
```json
{
  "config": {
    "name": "一级记忆总结",
    "model": "doubao-pro-32k",
    "prompts": {
      "system": "Updated system prompt",
      "user": "Updated user prompt"
    },
    "temperature": 0.9
  }
}
```

**Response:**
```json
{
  "message": "Agent configuration updated successfully",
  "data": {
    "id": "mem_l1_summarizer",
    "file_path": "agents/mem_l1_summarizer/agent.yaml"
  }
}
```

**Status Codes:**
- `200 OK` - Configuration updated successfully
- `400 Bad Request` - Invalid configuration data
- `404 Not Found` - Agent not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

### Pipeline Configuration

#### Read Pipeline Configuration

```http
GET /config/pipelines/{pipeline_id}
```

**Response:**
```json
{
  "id": "customer_service_flow",
  "config": {
    "name": "Customer Service Pipeline",
    "description": "Multi-step customer service processing",
    "version": "1.0.0",
    "inputs": [...],
    "outputs": [...],
    "steps": [...]
  },
  "file_path": "pipelines/customer_service_flow.yaml",
  "last_modified": "2024-12-17T10:30:00Z"
}
```

**Status Codes:**
- `200 OK` - Configuration retrieved successfully
- `404 Not Found` - Pipeline not found
- `500 Internal Server Error` - Server error

#### Update Pipeline Configuration

```http
PUT /config/pipelines/{pipeline_id}
```

**Request Body:**
```json
{
  "config": {
    "name": "Customer Service Pipeline",
    "description": "Updated description",
    "version": "1.1.0",
    "inputs": [...],
    "outputs": [...],
    "steps": [...]
  }
}
```

**Response:**
```json
{
  "message": "Pipeline configuration updated successfully",
  "data": {
    "id": "customer_service_flow",
    "file_path": "pipelines/customer_service_flow.yaml"
  }
}
```

**Status Codes:**
- `200 OK` - Configuration updated successfully
- `400 Bad Request` - Invalid configuration data
- `404 Not Found` - Pipeline not found
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

## Usage Examples

### cURL Examples

#### Read Agent Config
```bash
curl -X GET "http://localhost:8000/api/v1/config/agents/mem_l1_summarizer"
```

#### Update Agent Config
```bash
curl -X PUT "http://localhost:8000/api/v1/config/agents/mem_l1_summarizer" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "name": "一级记忆总结",
      "model": "doubao-pro-32k",
      "temperature": 0.9
    }
  }'
```

#### Read Pipeline Config
```bash
curl -X GET "http://localhost:8000/api/v1/config/pipelines/customer_service_flow"
```

#### Update Pipeline Config
```bash
curl -X PUT "http://localhost:8000/api/v1/config/pipelines/customer_service_flow" \
  -H "Content-Type: application/json" \
  -d @pipeline_config.json
```

### Python Examples

```python
import requests

BASE_URL = "http://localhost:8000/api/v1"

# Read agent configuration
response = requests.get(f"{BASE_URL}/config/agents/mem_l1_summarizer")
config = response.json()

# Update agent configuration
new_config = config['config'].copy()
new_config['temperature'] = 0.8

response = requests.put(
    f"{BASE_URL}/config/agents/mem_l1_summarizer",
    json={"config": new_config}
)
print(response.json()['message'])
```

### JavaScript Examples

```javascript
const BASE_URL = 'http://localhost:8000/api/v1';

// Read agent configuration
const response = await fetch(`${BASE_URL}/config/agents/mem_l1_summarizer`);
const data = await response.json();

// Update agent configuration
const newConfig = { ...data.config, temperature: 0.8 };

const updateResponse = await fetch(
  `${BASE_URL}/config/agents/mem_l1_summarizer`,
  {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ config: newConfig })
  }
);
const result = await updateResponse.json();
console.log(result.message);
```

## Important Notes

### Configuration Updates
- ⚠️ **Updates overwrite the entire configuration file**
- Always read the current configuration first
- Modify only the fields you want to change
- Include all required fields in the update

### File Locations
- Agent configs: `agents/{agent_id}/agent.yaml`
- Pipeline configs: `pipelines/{pipeline_id}.yaml` or `pipelines/{pipeline_id}/pipeline.yaml`

### YAML Formatting
- Unicode characters are preserved
- 2-space indentation
- Human-readable formatting
- Key order is preserved

### Error Handling
Always check response status codes:
- `2xx` - Success
- `4xx` - Client error (check your request)
- `5xx` - Server error (check server logs)

## Security Considerations

⚠️ **Current Implementation:**
- No authentication required
- Direct file system access
- No configuration validation
- No backup/versioning

🔒 **Production Recommendations:**
1. Add authentication middleware
2. Implement role-based access control
3. Validate configuration before writing
4. Implement backup/versioning
5. Add audit logging
6. Consider partial updates (PATCH)

## Related Documentation

- [API Design Specification](./api-design-specification.md)
- [API Setup Guide](./api-setup-guide.md)
- [Agent Registry Guide](./agent-registry-guide.md)
- [Pipeline Guide](./pipeline-guide.md)

## Demo Script

Run the demo script to see the API in action:

```bash
python examples/api_config_demo.py
```

## Testing

Run the test suite:

```bash
pytest tests/test_api_config.py -v
```

## Support

For issues or questions:
1. Check the API documentation at `/docs`
2. Review the test suite for examples
3. Check server logs for error details
