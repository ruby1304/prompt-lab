# API Setup Guide

This guide covers the initial setup and configuration of the Prompt Lab API layer.

## Overview

The API layer provides a REST interface to the Prompt Lab platform, built with FastAPI. This initial setup (Task 70) establishes the foundation for future API endpoints.

## Architecture

### Components

1. **FastAPI Application** (`src/api/app.py`)
   - Main application configuration
   - CORS middleware setup
   - Request logging middleware
   - Error handling middleware
   - Health check endpoints

2. **Configuration** (`src/api/config.py`)
   - Environment-based configuration
   - Server settings (host, port, workers)
   - CORS settings
   - Logging configuration

3. **Dependencies** (`src/api/dependencies.py`)
   - Dependency injection for FastAPI
   - Singleton instances (Agent Registry, etc.)
   - Path resolution utilities

4. **Data Models** (`src/api/models.py`)
   - Pydantic models for request/response validation
   - Standard error response models
   - Health check models

5. **Server** (`src/api/server.py`)
   - Uvicorn server startup script
   - Development and production modes

## Installation

### Dependencies

The following packages are required:

```bash
pip install fastapi>=0.104.0
pip install uvicorn[standard]>=0.24.0
pip install pydantic-settings>=2.0.0
pip install httpx>=0.25.0
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

## Running the API

### Development Mode

For development with auto-reload:

```bash
python -m src.api.server
```

Or programmatically:

```python
from src.api.server import start_server
start_server(reload=True, log_level="DEBUG")
```

### Production Mode

For production with multiple workers:

```bash
uvicorn src.api.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker (Future)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Configuration

### Environment Variables

Configure the API using environment variables with the `API_` prefix:

```bash
# Server
export API_HOST=0.0.0.0
export API_PORT=8080
export API_RELOAD=true
export API_WORKERS=4

# CORS
export API_CORS_ORIGINS='["http://localhost:3000"]'

# Logging
export API_LOG_LEVEL=INFO
```

### Configuration File

Create a `.env` file:

```env
API_HOST=0.0.0.0
API_PORT=8080
API_RELOAD=false
API_WORKERS=4
API_LOG_LEVEL=INFO
API_CORS_ORIGINS=["*"]
```

## Middleware

### CORS Middleware

Enables cross-origin requests for web applications:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Production Note**: Restrict `allow_origins` to specific domains in production.

### Request Logging Middleware

Logs all requests with timing information:

```
INFO:src.api.app:Request: GET /health
INFO:src.api.app:Response: GET /health - Status: 200 - Time: 0.001s
```

### GZip Middleware

Compresses responses larger than 1000 bytes for better performance.

### Error Handling

Global error handlers provide consistent error responses:

```json
{
  "error": "Error Type",
  "message": "Detailed error message",
  "path": "/api/endpoint"
}
```

## Available Endpoints

### System Endpoints

#### Health Check
```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "service": "prompt-lab-api",
  "version": "1.0.0"
}
```

#### Root
```
GET /
```

Response:
```json
{
  "message": "Welcome to Prompt Lab API",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/health"
}
```

### Documentation Endpoints

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## Testing

### Manual Testing

Use the demo script:

```bash
# Start the server
python -m src.api.server

# In another terminal, run the demo
python examples/api_demo.py
```

### Using curl

```bash
# Health check
curl http://localhost:8000/health

# Root endpoint
curl http://localhost:8000/

# OpenAPI schema
curl http://localhost:8000/openapi.json
```

### Using Python requests

```python
import requests

response = requests.get("http://localhost:8000/health")
print(response.json())
```

## Directory Structure

```
src/api/
├── __init__.py          # Package initialization
├── app.py               # FastAPI application
├── config.py            # Configuration management
├── dependencies.py      # Dependency injection
├── models.py            # Pydantic models
├── server.py            # Server startup
└── README.md            # API documentation

examples/
└── api_demo.py          # API demo script

docs/reference/
└── api-setup-guide.md   # This file
```

## Next Steps

Future tasks will add:

1. **Agent Management API** (Task 72)
   - List agents
   - Get agent details
   - Register/update agents

2. **Pipeline Management API** (Task 73)
   - List pipelines
   - Get pipeline details
   - Create/update pipelines

3. **Configuration API** (Task 74)
   - Read/write agent configs
   - Read/write pipeline configs

4. **Execution API** (Task 75-76)
   - Async agent execution
   - Async pipeline execution
   - Progress tracking

5. **Authentication** (Future)
   - JWT-based authentication
   - API key authentication

6. **Rate Limiting** (Future)
   - Request rate limiting
   - Per-user quotas

## Troubleshooting

### Port Already in Use

If port 8000 is already in use:

```bash
# Use a different port
python -c "from src.api.server import start_server; start_server(port=8080)"
```

### Import Errors

Ensure you're running from the project root:

```bash
# Check current directory
pwd

# Should be in prompt-lab directory
# If not, cd to the correct directory
```

### CORS Issues

If you encounter CORS errors in the browser:

1. Check `API_CORS_ORIGINS` configuration
2. Ensure your frontend URL is in the allowed origins list
3. For development, `["*"]` allows all origins

## Requirements Satisfied

This implementation satisfies **Requirement 8.2**:
- ✅ FastAPI framework selected and configured
- ✅ `src/api/` directory structure created
- ✅ Basic FastAPI application configured
- ✅ CORS middleware configured
- ✅ Request logging middleware configured
- ✅ Error handling middleware configured
- ✅ Health check endpoints implemented
- ✅ OpenAPI documentation auto-generated

## Related Documentation

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Uvicorn Documentation](https://www.uvicorn.org/)
- [CORS Middleware](https://fastapi.tiangolo.com/tutorial/cors/)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
