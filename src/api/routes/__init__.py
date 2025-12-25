"""
API Routes

This module aggregates all API route modules and provides a single router
to be included in the main FastAPI application.
"""

from fastapi import APIRouter
from . import agents, pipelines, config, executions

# Create main API router
api_router = APIRouter(prefix="/api/v1")

# Include route modules
api_router.include_router(agents.router)
api_router.include_router(pipelines.router)
api_router.include_router(config.router)
api_router.include_router(executions.router)

__all__ = ["api_router"]
