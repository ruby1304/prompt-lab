"""
API Layer for Prompt Lab

This module provides a REST API interface for the Prompt Lab platform,
enabling programmatic access to core functionality including:
- Agent management and execution
- Pipeline configuration and execution
- Configuration file management
- Asynchronous task execution and progress tracking

The API is built with FastAPI and follows RESTful principles.
"""

from .app import app, create_app

__all__ = ["app", "create_app"]
