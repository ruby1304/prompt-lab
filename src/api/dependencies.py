"""
FastAPI Dependencies

This module provides dependency injection functions for FastAPI endpoints.
Dependencies handle common tasks like:
- Loading configuration
- Initializing services
- Authentication (future)
- Rate limiting (future)
"""

from functools import lru_cache
from pathlib import Path
from typing import Optional
import os

from ..agent_registry_v2 import AgentRegistry
from ..pipeline_config import PipelineConfig
from .execution_manager import ExecutionManager, get_execution_manager as _get_execution_manager


@lru_cache()
def get_agent_registry() -> AgentRegistry:
    """
    Get the Agent Registry instance (singleton).
    
    This dependency provides access to the Agent Registry for API endpoints.
    The registry is cached to avoid reloading on every request.
    
    Returns:
        AgentRegistry: The agent registry instance
    """
    config_path = Path("config/agent_registry.yaml")
    if not config_path.exists():
        # Try alternative location
        config_path = Path(__file__).parent.parent.parent / "config" / "agent_registry.yaml"
    
    return AgentRegistry(config_path, enable_hot_reload=False)


def get_workspace_root() -> Path:
    """
    Get the workspace root directory.
    
    Returns:
        Path: The workspace root directory
    """
    # Try to get from environment variable
    workspace = os.getenv("PROMPT_LAB_WORKSPACE")
    if workspace:
        return Path(workspace)
    
    # Default to current directory
    return Path.cwd()


def get_agents_dir() -> Path:
    """
    Get the agents directory.
    
    Returns:
        Path: The agents directory path
    """
    return get_workspace_root() / "agents"


def get_pipelines_dir() -> Path:
    """
    Get the pipelines directory.
    
    Returns:
        Path: The pipelines directory path
    """
    return get_workspace_root() / "pipelines"


def get_data_dir() -> Path:
    """
    Get the data directory.
    
    Returns:
        Path: The data directory path
    """
    return get_workspace_root() / "data"


def get_config_dir() -> Path:
    """
    Get the config directory.
    
    Returns:
        Path: The config directory path
    """
    return get_workspace_root() / "config"


def get_execution_manager() -> ExecutionManager:
    """
    Get the Execution Manager instance (singleton).
    
    This dependency provides access to the Execution Manager for async execution.
    The manager handles background task execution and status tracking.
    
    Returns:
        ExecutionManager: The execution manager instance
    """
    return _get_execution_manager()
