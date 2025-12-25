"""
Configuration File Read/Write API Routes

This module implements the Configuration Management API endpoints:
- GET /api/v1/config/agents/{agent_id} - Read agent configuration file
- PUT /api/v1/config/agents/{agent_id} - Update agent configuration file
- GET /api/v1/config/pipelines/{pipeline_id} - Read pipeline configuration file
- PUT /api/v1/config/pipelines/{pipeline_id} - Update pipeline configuration file

Requirements: 8.4
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any
from datetime import datetime
from pathlib import Path
import yaml

from ..models import ConfigResponse, ConfigUpdateRequest, MessageResponse
from ..dependencies import get_agent_registry
from ...agent_registry_v2 import AgentRegistry
from ...pipeline_config import find_pipeline_config_file

router = APIRouter(prefix="/config", tags=["Configuration"])


def find_agent_config_file(agent_id: str, registry: AgentRegistry) -> Path:
    """
    Find the agent.yaml configuration file for an agent.
    
    Args:
        agent_id: Agent identifier
        registry: AgentRegistry instance
        
    Returns:
        Path to the agent configuration file
        
    Raises:
        HTTPException: If agent not found or config file not found
    """
    try:
        # Get agent metadata from registry
        agent = registry.get_agent(agent_id)
        
        # Agent location should point to the agent directory
        agent_dir = Path(agent.location)
        if not agent_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "NotFound",
                    "message": f"Agent directory not found: {agent_dir}"
                }
            )
        
        # Look for agent.yaml in the agent directory
        config_file = agent_dir / "agent.yaml"
        if not config_file.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "NotFound",
                    "message": f"Agent configuration file not found: {config_file}"
                }
            )
        
        return config_file
        
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "NotFound",
                "message": f"Agent '{agent_id}' not found in registry"
            }
        )





@router.get("/agents/{agent_id}", response_model=ConfigResponse)
async def get_agent_config(
    agent_id: str,
    registry: AgentRegistry = Depends(get_agent_registry),
):
    """
    Read the agent.yaml configuration file for a specific agent.
    
    This endpoint returns the complete YAML configuration for an agent,
    including all prompts, model settings, and other configuration.
    
    **Example:**
    ```
    GET /api/v1/config/agents/mem_l1_summarizer
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
        },
        ...
      },
      "file_path": "agents/mem_l1_summarizer/agent.yaml",
      "last_modified": "2024-12-01T00:00:00Z"
    }
    ```
    """
    try:
        # Find agent config file
        config_file = find_agent_config_file(agent_id, registry)
        
        # Read configuration
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # Get file metadata
        stat = config_file.stat()
        last_modified = datetime.fromtimestamp(stat.st_mtime)
        
        return ConfigResponse(
            id=agent_id,
            config=config_data,
            file_path=str(config_file),
            last_modified=last_modified
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": f"Failed to read agent configuration: {str(e)}"
            }
        )


@router.put("/agents/{agent_id}", response_model=MessageResponse)
async def update_agent_config(
    agent_id: str,
    request: ConfigUpdateRequest,
    registry: AgentRegistry = Depends(get_agent_registry),
):
    """
    Update the agent.yaml configuration file for a specific agent.
    
    This endpoint writes the provided configuration to the agent's YAML file.
    The entire configuration is replaced with the new content.
    
    **Warning:** This operation overwrites the existing configuration file.
    Make sure to include all required fields in the new configuration.
    
    **Example:**
    ```
    PUT /api/v1/config/agents/mem_l1_summarizer
    {
      "config": {
        "name": "一级记忆总结",
        "model": "doubao-pro",
        "prompts": {
          "system": "Updated system prompt",
          "user": "Updated user prompt"
        },
        ...
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
    """
    try:
        # Find agent config file
        config_file = find_agent_config_file(agent_id, registry)
        
        # Validate that config is a dictionary
        if not isinstance(request.config, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "BadRequest",
                    "message": "Configuration must be a valid dictionary/object"
                }
            )
        
        # Write updated configuration
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(
                request.config,
                f,
                default_flow_style=False,
                allow_unicode=True,
                indent=2,
                sort_keys=False
            )
        
        return MessageResponse(
            message="Agent configuration updated successfully",
            data={
                "id": agent_id,
                "file_path": str(config_file)
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": f"Failed to update agent configuration: {str(e)}"
            }
        )


@router.get("/pipelines/{pipeline_id}", response_model=ConfigResponse)
async def get_pipeline_config(pipeline_id: str):
    """
    Read the pipeline configuration file for a specific pipeline.
    
    This endpoint returns the complete YAML configuration for a pipeline,
    including all steps, inputs, outputs, and other configuration.
    
    **Example:**
    ```
    GET /api/v1/config/pipelines/customer_service_flow
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
      "last_modified": "2024-12-01T00:00:00Z"
    }
    ```
    """
    try:
        # Find pipeline config file
        config_file = find_pipeline_config_file(pipeline_id)
        
        # Read configuration
        with open(config_file, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        # Get file metadata
        stat = config_file.stat()
        last_modified = datetime.fromtimestamp(stat.st_mtime)
        
        return ConfigResponse(
            id=pipeline_id,
            config=config_data,
            file_path=str(config_file),
            last_modified=last_modified
        )
        
    except (FileNotFoundError, Exception) as e:
        # Check if it's a "not found" error
        error_msg = str(e)
        if "找不到" in error_msg or "not found" in error_msg.lower() or isinstance(e, FileNotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "NotFound",
                    "message": f"Pipeline configuration file for '{pipeline_id}' not found"
                }
            )
        elif isinstance(e, HTTPException):
            # Re-raise HTTP exceptions
            raise
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "InternalServerError",
                    "message": f"Failed to read pipeline configuration: {str(e)}"
                }
            )


@router.put("/pipelines/{pipeline_id}", response_model=MessageResponse)
async def update_pipeline_config(
    pipeline_id: str,
    request: ConfigUpdateRequest,
):
    """
    Update the pipeline configuration file for a specific pipeline.
    
    This endpoint writes the provided configuration to the pipeline's YAML file.
    The entire configuration is replaced with the new content.
    
    **Warning:** This operation overwrites the existing configuration file.
    Make sure to include all required fields in the new configuration.
    
    **Example:**
    ```
    PUT /api/v1/config/pipelines/customer_service_flow
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
    """
    try:
        # Find pipeline config file
        config_file = find_pipeline_config_file(pipeline_id)
        
        # Validate that config is a dictionary
        if not isinstance(request.config, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "BadRequest",
                    "message": "Configuration must be a valid dictionary/object"
                }
            )
        
        # Write updated configuration
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(
                request.config,
                f,
                default_flow_style=False,
                allow_unicode=True,
                indent=2,
                sort_keys=False
            )
        
        return MessageResponse(
            message="Pipeline configuration updated successfully",
            data={
                "id": pipeline_id,
                "file_path": str(config_file)
            }
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except (FileNotFoundError, Exception) as e:
        # Check if it's a "not found" error
        error_msg = str(e)
        if "找不到" in error_msg or "not found" in error_msg.lower() or isinstance(e, FileNotFoundError):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "NotFound",
                    "message": f"Pipeline configuration file for '{pipeline_id}' not found"
                }
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "InternalServerError",
                    "message": f"Failed to update pipeline configuration: {str(e)}"
                }
            )
