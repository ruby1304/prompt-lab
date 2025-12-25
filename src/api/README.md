# Prompt Lab API

REST API layer for the Prompt Lab platform, providing programmatic access to core functionality.

## Overview

The API is built with FastAPI and provides endpoints for:
- Agent management and execution
- Pipeline configuration and execution
- Configuration file management
- Asynchronous task execution and progress tracking

## Quick Start

### Installation

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Running the Server

#### Development Mode (with auto-reload)

```bash
python -m src.api.server
```

Or with auto-reload enabled:

```python
from src.api.server import start_server
start_server(reload=True)
```

#### Production Mode

```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Accessing the API

Once the server is running:

- **API Base URL**: http://localhost:8000
- **Interactive Documentation (Swagger UI)**: http://localhost:8000/docs
- **Alternative Documentation (ReDoc)**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json
- **Health Check**: http://localhost:8000/health

## Configuration

The API can be configured via environment variables with the `API_` prefix:

```bash
# Server settings
export API_HOST=0.0.0.0
export API_PORT=8080
export API_RELOAD=true
export API_WORKERS=4

# CORS settings
export API_CORS_ORIGINS='["http://localhost:3000", "https://app.example.com"]'

# Logging
export API_LOG_LEVEL=DEBUG
```

Or create a `.env` file:

```env
API_HOST=0.0.0.0
API_PORT=8080
API_RELOAD=false
API_WORKERS=4
API_LOG_LEVEL=INFO
```

## Architecture

### Directory Structure

```
src/api/
├── __init__.py          # Package initialization
├── app.py               # FastAPI application setup
├── config.py            # Configuration management
├── dependencies.py      # Dependency injection
├── models.py            # Pydantic models for API
├── server.py            # Server startup script
└── README.md            # This file
```

### Middleware

The API includes the following middleware:

1. **CORS Middleware**: Enables cross-origin requests for web applications
2. **GZip Middleware**: Compresses responses for better performance
3. **Request Logging Middleware**: Logs all requests with timing information
4. **Error Handling Middleware**: Provides consistent error responses

### Error Handling

The API provides consistent error responses:

```json
{
  "error": "Error Type",
  "message": "Detailed error message",
  "path": "/api/endpoint",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Development

### Adding New Endpoints

Future endpoints will be organized in separate router modules:

```python
# src/api/routes/agents.py
from fastapi import APIRouter

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.get("/")
async def list_agents():
    return {"agents": []}
```

Then include in the main app:

```python
# src/api/app.py
from .routes import agents

app.include_router(agents.router, prefix="/api/v1")
```

### Testing

API tests will be added in future tasks using FastAPI's TestClient:

```python
from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

## API Documentation

### Complete API Specification

See the complete API design specification:
- **[API Design Specification](../../docs/reference/api-design-specification.md)** - Complete RESTful API specification with all endpoints, request/response models, and error handling

### Implementation Guides

- **[API Routes Implementation Guide](../../docs/reference/api-routes-implementation-guide.md)** - Detailed guide for implementing API routes
- **[API Models](./models.py)** - Pydantic models for request/response validation

## API Endpoints Overview

### System Endpoints
- `GET /health` - Health check
- `GET /` - API information

### Agent Management (Task 72)
- `GET /api/v1/agents` - List agents
- `GET /api/v1/agents/{agent_id}` - Get agent details
- `POST /api/v1/agents` - Register agent
- `PUT /api/v1/agents/{agent_id}` - Update agent
- `DELETE /api/v1/agents/{agent_id}` - Delete agent
- `POST /api/v1/agents/{agent_id}/flows/{flow_id}/execute` - Execute agent flow

### Pipeline Management (Task 73)
- `GET /api/v1/pipelines` - List pipelines
- `GET /api/v1/pipelines/{pipeline_id}` - Get pipeline details
- `POST /api/v1/pipelines` - Create pipeline
- `PUT /api/v1/pipelines/{pipeline_id}` - Update pipeline
- `DELETE /api/v1/pipelines/{pipeline_id}` - Delete pipeline
- `POST /api/v1/pipelines/{pipeline_id}/execute` - Execute pipeline

### Configuration Management (Task 74)
- `GET /api/v1/config/agents/{agent_id}` - Get agent config
- `PUT /api/v1/config/agents/{agent_id}` - Update agent config
- `GET /api/v1/config/pipelines/{pipeline_id}` - Get pipeline config
- `PUT /api/v1/config/pipelines/{pipeline_id}` - Update pipeline config
- `POST /api/v1/config/validate` - Validate configuration

### Async Execution (Task 75)
- `POST /api/v1/executions` - Start async execution
- `GET /api/v1/executions/{execution_id}` - Get execution status
- `GET /api/v1/executions` - List executions
- `POST /api/v1/executions/{execution_id}/cancel` - Cancel execution

### Progress Tracking (Task 76)
- `WS /api/v1/executions/{execution_id}/progress` - Real-time progress (WebSocket)

### Batch Processing
- `POST /api/v1/batch/execute` - Execute batch tests
- `GET /api/v1/batch/{batch_id}` - Get batch status

## Future Enhancements

The following features are planned for future implementation:

- [ ] Agent management endpoints (Task 72)
- [ ] Pipeline management endpoints (Task 73)
- [ ] Configuration file API (Task 74)
- [ ] Asynchronous execution API (Task 75)
- [ ] Progress tracking API (Task 76)
- [ ] Authentication and authorization
- [ ] Rate limiting
- [ ] WebSocket support for real-time updates
- [ ] API versioning strategy

## Requirements

This implementation satisfies **Requirement 8.2** from the design document:
- FastAPI framework selected and configured
- CORS middleware enabled for cross-origin requests
- Request logging and error handling middleware
- OpenAPI documentation auto-generation
- Modular structure for future endpoint additions
- Complete API specification documented
- Request/response models defined with Pydantic

## Related Documentation

- [API Design Specification](../../docs/reference/api-design-specification.md)
- [API Routes Implementation Guide](../../docs/reference/api-routes-implementation-guide.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
