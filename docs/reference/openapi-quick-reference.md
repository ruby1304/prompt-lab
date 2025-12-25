# OpenAPI Documentation Quick Reference

## Access Points

| Interface | URL | Purpose |
|-----------|-----|---------|
| **Swagger UI** | http://localhost:8000/docs | Interactive API testing |
| **ReDoc** | http://localhost:8000/redoc | Clean documentation view |
| **OpenAPI JSON** | http://localhost:8000/openapi.json | Raw specification |

## Quick Start

### 1. View Documentation
```bash
# Start the API server
python -m src.api.server

# Open in browser
open http://localhost:8000/docs
```

### 2. Test an Endpoint
1. Go to http://localhost:8000/docs
2. Click on any endpoint
3. Click "Try it out"
4. Fill in parameters
5. Click "Execute"

### 3. Download Specification
```bash
curl http://localhost:8000/openapi.json > openapi.json
```

## API Endpoints Overview

### System
- `GET /health` - Health check
- `GET /` - API information

### Agents
- `GET /api/v1/agents` - List agents
- `GET /api/v1/agents/{agent_id}` - Get agent details
- `POST /api/v1/agents` - Register agent
- `PUT /api/v1/agents/{agent_id}` - Update agent

### Pipelines
- `GET /api/v1/pipelines` - List pipelines
- `GET /api/v1/pipelines/{pipeline_id}` - Get pipeline details
- `POST /api/v1/pipelines` - Create pipeline
- `PUT /api/v1/pipelines/{pipeline_id}` - Update pipeline

### Configuration
- `GET /api/v1/config/agents/{agent_id}` - Read agent config
- `PUT /api/v1/config/agents/{agent_id}` - Update agent config
- `GET /api/v1/config/pipelines/{pipeline_id}` - Read pipeline config
- `PUT /api/v1/config/pipelines/{pipeline_id}` - Update pipeline config

### Async Execution
- `POST /api/v1/executions` - Start execution
- `GET /api/v1/executions/{execution_id}` - Get status
- `GET /api/v1/executions` - List executions
- `GET /api/v1/executions/{execution_id}/progress` - Get progress
- `POST /api/v1/executions/{execution_id}/cancel` - Cancel execution
- `WS /api/v1/executions/{execution_id}/progress/ws` - Progress stream

## Common Examples

### List Agents
```bash
curl http://localhost:8000/api/v1/agents?page=1&page_size=20
```

### Get Agent Details
```bash
curl http://localhost:8000/api/v1/agents/mem_l1_summarizer
```

### Execute Pipeline
```bash
curl -X POST http://localhost:8000/api/v1/executions \
  -H "Content-Type: application/json" \
  -d '{
    "type": "pipeline",
    "target_id": "customer_service_flow",
    "inputs": {
      "customer_query": "How do I reset my password?"
    }
  }'
```

### Check Execution Status
```bash
curl http://localhost:8000/api/v1/executions/exec_123456
```

## Response Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created |
| 202 | Accepted | Async operation started |
| 204 | No Content | Success, no data |
| 400 | Bad Request | Invalid input |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource exists |
| 500 | Server Error | Internal error |

## Error Response Format

```json
{
  "error": "ErrorType",
  "message": "Human-readable message",
  "path": "/api/v1/endpoint"
}
```

## Pagination

All list endpoints support pagination:

```bash
GET /api/v1/agents?page=1&page_size=50
```

Response includes pagination info:
```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 150,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

## Filtering

### Agents
```bash
# By category
GET /api/v1/agents?category=production

# By environment
GET /api/v1/agents?environment=production

# By status
GET /api/v1/agents?status=active

# By tags
GET /api/v1/agents?tags=memory,summarization

# Search
GET /api/v1/agents?search=summarizer
```

### Pipelines
```bash
# By status
GET /api/v1/pipelines?status=active

# Search
GET /api/v1/pipelines?search=customer
```

### Executions
```bash
# By status
GET /api/v1/executions?status=completed

# By type
GET /api/v1/executions?type=pipeline

# By target
GET /api/v1/executions?target_id=customer_service_flow
```

## WebSocket Connection

```javascript
const ws = new WebSocket(
  'ws://localhost:8000/api/v1/executions/exec_123456/progress/ws'
);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data.progress);
};
```

## Import to Tools

### Postman
1. Import → Link
2. Enter: `http://localhost:8000/openapi.json`
3. Click Import

### Insomnia
1. Create → Import From → URL
2. Enter: `http://localhost:8000/openapi.json`
3. Click Fetch and Import

## Generate Client SDK

```bash
# Download spec
curl http://localhost:8000/openapi.json > openapi.json

# Generate Python client
openapi-generator-cli generate \
  -i openapi.json \
  -g python \
  -o ./client-python

# Generate TypeScript client
openapi-generator-cli generate \
  -i openapi.json \
  -g typescript-axios \
  -o ./client-typescript
```

## Documentation Features

### Swagger UI Features
- ✅ Interactive testing
- ✅ Request/response examples
- ✅ Schema validation
- ✅ Authentication support
- ✅ Try it out functionality

### ReDoc Features
- ✅ Clean layout
- ✅ Full-text search
- ✅ Deep linking
- ✅ Print-friendly
- ✅ Code samples

## Customization

### Add Model Examples
```python
class MyModel(BaseModel):
    field: str
    
    class Config:
        json_schema_extra = {
            "example": {"field": "value"}
        }
```

### Add Endpoint Description
```python
@router.get("/endpoint")
async def my_endpoint():
    """
    Detailed description here.
    
    **Example:**
    ```
    GET /api/v1/endpoint
    ```
    """
    pass
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Docs not loading | Check server is running on port 8000 |
| Missing endpoints | Verify routes are registered in app |
| Outdated examples | Clear browser cache and reload |
| WebSocket fails | Check execution_id is valid |

## Related Documentation

- [OpenAPI Documentation Guide](./openapi-documentation-guide.md) - Full guide
- [API Design Specification](./api-design-specification.md) - API design
- [API Setup Guide](./api-setup-guide.md) - Setup instructions
- [Async Execution Guide](./async-execution-api-guide.md) - Async operations

## Support

For issues or questions:
- Review the full [OpenAPI Documentation Guide](./openapi-documentation-guide.md)
- Check the [API Design Specification](./api-design-specification.md)
- Contact the development team
