"""
Agent Management API Routes

This module implements the Agent Management API endpoints:
- GET /api/v1/agents - List all agents with filtering and pagination
- GET /api/v1/agents/{agent_id} - Get agent details
- POST /api/v1/agents - Register a new agent
- PUT /api/v1/agents/{agent_id} - Update agent metadata

Requirements: 8.2
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from ..models import (
    AgentMetadataResponse,
    AgentListResponse,
    AgentCreateRequest,
    AgentUpdateRequest,
    AgentCategory,
    AgentEnvironment,
    AgentStatus,
    PaginationInfo,
    MessageResponse,
)
from ..dependencies import get_agent_registry
from ...agent_registry_v2 import AgentRegistry, AgentMetadata

router = APIRouter(prefix="/agents", tags=["Agents"])


def paginate(items: List, page: int, page_size: int) -> tuple[List, PaginationInfo]:
    """
    Paginate a list of items.
    
    Args:
        items: List of items to paginate
        page: Current page number (1-indexed)
        page_size: Number of items per page
        
    Returns:
        Tuple of (paginated_items, pagination_info)
    """
    total_items = len(items)
    total_pages = (total_items + page_size - 1) // page_size if total_items > 0 else 0
    
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    
    paginated_items = items[start_idx:end_idx]
    
    pagination = PaginationInfo(
        page=page,
        page_size=page_size,
        total_items=total_items,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
        next_page=page + 1 if page < total_pages else None,
        prev_page=page - 1 if page > 1 else None
    )
    
    return paginated_items, pagination


def agent_metadata_to_response(metadata: AgentMetadata) -> AgentMetadataResponse:
    """
    Convert AgentMetadata to AgentMetadataResponse.
    
    Args:
        metadata: AgentMetadata instance
        
    Returns:
        AgentMetadataResponse instance
    """
    return AgentMetadataResponse(
        id=metadata.id,
        name=metadata.name,
        category=AgentCategory(metadata.category),
        environment=AgentEnvironment(metadata.environment),
        owner=metadata.owner,
        version=metadata.version,
        status=AgentStatus(metadata.status),
        tags=metadata.tags,
        deprecated=metadata.deprecated,
        location=str(metadata.location),
        description=metadata.description,
        business_goal=metadata.business_goal,
        created_at=datetime.fromisoformat(metadata.created_at) if metadata.created_at else None,
        updated_at=datetime.fromisoformat(metadata.updated_at) if metadata.updated_at else None,
        maintainer=metadata.maintainer,
        documentation_url=metadata.documentation_url,
        dependencies=metadata.dependencies,
        performance_metrics=metadata.performance_metrics,
    )


@router.get("/", response_model=AgentListResponse)
async def list_agents(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    category: Optional[AgentCategory] = Query(None, description="Filter by category"),
    environment: Optional[AgentEnvironment] = Query(None, description="Filter by environment"),
    status: Optional[AgentStatus] = Query(None, description="Filter by status"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    include_deprecated: bool = Query(True, description="Include deprecated agents"),
    search: Optional[str] = Query(None, description="Search query"),
    registry: AgentRegistry = Depends(get_agent_registry),
):
    """
    List all agents with filtering and pagination.
    
    This endpoint returns a paginated list of agents with optional filtering by:
    - Category (production, example, test, system)
    - Environment (production, staging, demo, test)
    - Status (active, deprecated, experimental, archived)
    - Tags (comma-separated list)
    - Search query (searches in id, name, description, tags)
    
    **Example:**
    ```
    GET /api/v1/agents?category=production&page=1&page_size=20
    ```
    
    **Response:**
    ```json
    {
      "agents": [...],
      "pagination": {
        "page": 1,
        "page_size": 20,
        "total_items": 45,
        "total_pages": 3,
        "has_next": true,
        "has_prev": false
      }
    }
    ```
    """
    try:
        # Parse tags if provided
        tag_list = None
        if tags:
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        
        # Get filtered agents
        if search:
            # Use search if query provided
            agents = registry.search_agents(query=search, case_sensitive=False)
            
            # Apply additional filters
            if category:
                agents = [a for a in agents if a.category == category.value]
            if environment:
                agents = [a for a in agents if a.environment == environment.value]
            if status:
                agents = [a for a in agents if a.status == status.value]
            if not include_deprecated:
                agents = [a for a in agents if not a.deprecated]
            if tag_list:
                agents = [a for a in agents if all(tag in a.tags for tag in tag_list)]
        else:
            # Use list_agents with filters
            agents = registry.list_agents(
                category=category.value if category else None,
                environment=environment.value if environment else None,
                tags=tag_list,
                include_deprecated=include_deprecated,
                status=status.value if status else None,
            )
        
        # Paginate results
        paginated_agents, pagination = paginate(agents, page, page_size)
        
        # Convert to response models
        agent_responses = [
            agent_metadata_to_response(agent) for agent in paginated_agents
        ]
        
        return AgentListResponse(
            agents=agent_responses,
            pagination=pagination
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": f"Failed to list agents: {str(e)}"
            }
        )


@router.get("/{agent_id}", response_model=AgentMetadataResponse)
async def get_agent(
    agent_id: str,
    registry: AgentRegistry = Depends(get_agent_registry),
):
    """
    Get detailed information about a specific agent.
    
    This endpoint returns complete metadata for a single agent including:
    - Basic information (id, name, version)
    - Classification (category, environment, status)
    - Ownership and maintenance info
    - Tags and dependencies
    - Performance metrics (if available)
    
    **Example:**
    ```
    GET /api/v1/agents/mem_l1_summarizer
    ```
    
    **Response:**
    ```json
    {
      "id": "mem_l1_summarizer",
      "name": "一级记忆总结",
      "category": "production",
      "environment": "production",
      "owner": "memory-team",
      "version": "1.2.0",
      "status": "active",
      "tags": ["memory", "summarization"],
      "deprecated": false,
      "location": "agents/mem_l1_summarizer",
      "description": "Summarizes L1 memory entries"
    }
    ```
    """
    try:
        # Get agent from registry
        agent = registry.get_agent(agent_id)
        
        # Convert to response model
        return agent_metadata_to_response(agent)
        
    except KeyError:
        # Agent not found
        available_agents = ", ".join(sorted(registry._agents.keys())[:10])
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "NotFound",
                "message": f"Agent '{agent_id}' not found",
                "available_agents": available_agents + ("..." if len(registry._agents) > 10 else "")
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": f"Failed to get agent: {str(e)}"
            }
        )


@router.post("/", response_model=AgentMetadataResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    request: AgentCreateRequest,
    registry: AgentRegistry = Depends(get_agent_registry),
):
    """
    Register a new agent in the registry.
    
    This endpoint creates a new agent entry in the registry. The agent must have:
    - A unique ID (alphanumeric with underscores)
    - A name and version
    - Category and environment classification
    - Owner information
    - Location path
    
    **Note:** This only updates the in-memory registry. To persist changes,
    the registry configuration file must be written back to disk.
    
    **Example:**
    ```
    POST /api/v1/agents
    {
      "id": "new_agent",
      "name": "New Agent",
      "category": "production",
      "environment": "staging",
      "owner": "my-team",
      "version": "1.0.0",
      "location": "agents/new_agent",
      "description": "A new agent",
      "tags": ["new", "experimental"]
    }
    ```
    
    **Response:**
    ```json
    {
      "id": "new_agent",
      "name": "New Agent",
      ...
    }
    ```
    """
    try:
        # Check if agent already exists
        try:
            existing = registry.get_agent(request.id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "Conflict",
                    "message": f"Agent '{request.id}' already exists",
                    "existing_agent": {
                        "id": existing.id,
                        "name": existing.name,
                        "version": existing.version
                    }
                }
            )
        except KeyError:
            # Agent doesn't exist, good to proceed
            pass
        
        # Create agent metadata
        metadata = AgentMetadata(
            id=request.id,
            name=request.name,
            category=request.category.value,
            environment=request.environment.value,
            owner=request.owner,
            version=request.version,
            location=Path(request.location),
            deprecated=False,
            description=request.description,
            tags=request.tags,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            status="active",
        )
        
        # Register agent
        registry.register_agent(request.id, metadata)
        
        # Convert to response model
        return agent_metadata_to_response(metadata)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": f"Failed to create agent: {str(e)}"
            }
        )


@router.put("/{agent_id}", response_model=AgentMetadataResponse)
async def update_agent(
    agent_id: str,
    request: AgentUpdateRequest,
    registry: AgentRegistry = Depends(get_agent_registry),
):
    """
    Update an existing agent's metadata.
    
    This endpoint updates the metadata for an existing agent. You can update:
    - Name
    - Version
    - Description
    - Tags
    - Status
    
    Fields not provided in the request will remain unchanged.
    
    **Note:** This only updates the in-memory registry. To persist changes,
    the registry configuration file must be written back to disk.
    
    **Example:**
    ```
    PUT /api/v1/agents/mem_l1_summarizer
    {
      "version": "1.3.0",
      "description": "Updated description",
      "tags": ["memory", "summarization", "v1.3"]
    }
    ```
    
    **Response:**
    ```json
    {
      "id": "mem_l1_summarizer",
      "name": "一级记忆总结",
      "version": "1.3.0",
      "description": "Updated description",
      ...
    }
    ```
    """
    try:
        # Get existing agent
        try:
            existing = registry.get_agent(agent_id)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "NotFound",
                    "message": f"Agent '{agent_id}' not found"
                }
            )
        
        # Update fields if provided
        if request.name is not None:
            existing.name = request.name
        if request.version is not None:
            existing.version = request.version
        if request.description is not None:
            existing.description = request.description
        if request.tags is not None:
            existing.tags = request.tags
        if request.status is not None:
            existing.status = request.status.value
        
        # Update timestamp
        existing.updated_at = datetime.now().isoformat()
        
        # Update in registry
        registry.update_agent(agent_id, existing)
        
        # Convert to response model
        return agent_metadata_to_response(existing)
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": f"Failed to update agent: {str(e)}"
            }
        )
