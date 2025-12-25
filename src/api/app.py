"""
FastAPI Application Configuration

This module configures the main FastAPI application with:
- CORS middleware for cross-origin requests
- Request/response logging middleware
- Error handling middleware
- API versioning
- OpenAPI documentation
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
import time
import logging
from typing import Callable
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured FastAPI application instance
    """
    app = FastAPI(
        title="Prompt Lab API",
        description="""
# Prompt Lab API

REST API for Prompt Lab - A comprehensive Agent and Pipeline Management Platform.

## Features

* **Agent Management**: Register, query, and manage AI agents with metadata
* **Pipeline Management**: Create and execute multi-step agent workflows
* **Configuration Management**: Read and write agent/pipeline configurations
* **Async Execution**: Execute long-running tasks asynchronously with progress tracking
* **Real-time Progress**: WebSocket support for live execution updates

## Getting Started

1. **List Available Agents**: `GET /api/v1/agents`
2. **Get Agent Details**: `GET /api/v1/agents/{agent_id}`
3. **Execute Pipeline**: `POST /api/v1/executions`
4. **Track Progress**: `GET /api/v1/executions/{execution_id}`

## Authentication

Currently, the API does not require authentication. In production environments,
implement appropriate authentication and authorization mechanisms.

## Rate Limiting

No rate limiting is currently enforced. Consider implementing rate limiting
for production deployments.

## Support

For issues and questions, please refer to the project documentation or
contact the development team.
        """,
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={
            "name": "Prompt Lab Team",
            "email": "support@promptlab.example.com",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        openapi_tags=[
            {
                "name": "System",
                "description": "System health and information endpoints"
            },
            {
                "name": "Agents",
                "description": "Agent management operations - register, query, and update agents"
            },
            {
                "name": "Pipelines",
                "description": "Pipeline management operations - create and configure multi-step workflows"
            },
            {
                "name": "Configuration",
                "description": "Configuration file management - read and write YAML configurations"
            },
            {
                "name": "Async Execution",
                "description": "Asynchronous execution operations - start, monitor, and cancel long-running tasks"
            },
        ],
        servers=[
            {
                "url": "http://localhost:8000",
                "description": "Development server"
            },
            {
                "url": "http://localhost:8000/api/v1",
                "description": "Development server (API v1)"
            },
        ],
        responses={
            400: {
                "description": "Bad Request - Invalid input parameters",
                "content": {
                    "application/json": {
                        "example": {
                            "error": "BadRequest",
                            "message": "Invalid parameter value",
                            "path": "/api/v1/agents"
                        }
                    }
                }
            },
            404: {
                "description": "Not Found - Resource does not exist",
                "content": {
                    "application/json": {
                        "example": {
                            "error": "NotFound",
                            "message": "Agent 'unknown_agent' not found",
                            "path": "/api/v1/agents/unknown_agent"
                        }
                    }
                }
            },
            500: {
                "description": "Internal Server Error - Unexpected error occurred",
                "content": {
                    "application/json": {
                        "example": {
                            "error": "InternalServerError",
                            "message": "An unexpected error occurred",
                            "path": "/api/v1/agents"
                        }
                    }
                }
            },
        },
    )
    
    # Configure CORS
    configure_cors(app)
    
    # Configure middleware
    configure_middleware(app)
    
    # Configure error handlers
    configure_error_handlers(app)
    
    # Health check endpoint
    @app.get("/health", tags=["System"])
    async def health_check():
        """Health check endpoint to verify API is running."""
        return {
            "status": "healthy",
            "service": "prompt-lab-api",
            "version": "1.0.0"
        }
    
    @app.get("/", tags=["System"])
    async def root():
        """Root endpoint with API information."""
        return {
            "message": "Welcome to Prompt Lab API",
            "version": "1.0.0",
            "docs": "/docs",
            "health": "/health"
        }
    
    # Include API routes
    from .routes import api_router
    app.include_router(api_router)
    
    return app


def configure_cors(app: FastAPI) -> None:
    """
    Configure CORS (Cross-Origin Resource Sharing) middleware.
    
    This allows the API to be accessed from web applications running
    on different domains, which is essential for the future visualization
    interface.
    
    Args:
        app: FastAPI application instance
    """
    # Allow all origins in development
    # In production, this should be restricted to specific domains
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # TODO: Restrict in production
        allow_credentials=True,
        allow_methods=["*"],  # Allow all HTTP methods
        allow_headers=["*"],  # Allow all headers
        expose_headers=["*"],
    )
    logger.info("CORS middleware configured")


def configure_middleware(app: FastAPI) -> None:
    """
    Configure additional middleware for the application.
    
    Args:
        app: FastAPI application instance
    """
    # GZip compression for responses
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    
    # Request logging middleware
    @app.middleware("http")
    async def log_requests(request: Request, call_next: Callable):
        """Log all incoming requests and their processing time."""
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.url.path}")
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        
        # Log response
        logger.info(
            f"Response: {request.method} {request.url.path} "
            f"- Status: {response.status_code} "
            f"- Time: {process_time:.3f}s"
        )
        
        return response
    
    logger.info("Additional middleware configured")


def configure_error_handlers(app: FastAPI) -> None:
    """
    Configure global error handlers for the application.
    
    Args:
        app: FastAPI application instance
    """
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle all unhandled exceptions."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": str(exc),
                "path": request.url.path
            }
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        """Handle ValueError exceptions."""
        logger.warning(f"ValueError: {exc}")
        return JSONResponse(
            status_code=400,
            content={
                "error": "Bad Request",
                "message": str(exc),
                "path": request.url.path
            }
        )
    
    @app.exception_handler(FileNotFoundError)
    async def file_not_found_handler(request: Request, exc: FileNotFoundError):
        """Handle FileNotFoundError exceptions."""
        logger.warning(f"FileNotFoundError: {exc}")
        return JSONResponse(
            status_code=404,
            content={
                "error": "Not Found",
                "message": str(exc),
                "path": request.url.path
            }
        )
    
    logger.info("Error handlers configured")


# Create the application instance
app = create_app()
