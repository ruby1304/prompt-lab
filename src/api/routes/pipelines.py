"""
Pipeline Management API Routes

This module implements the Pipeline Management API endpoints:
- GET /api/v1/pipelines - List all pipelines with filtering and pagination
- GET /api/v1/pipelines/{pipeline_id} - Get pipeline details
- POST /api/v1/pipelines - Create a new pipeline
- PUT /api/v1/pipelines/{pipeline_id} - Update pipeline configuration

Requirements: 8.2
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional
from datetime import datetime
from pathlib import Path
import yaml

from ..models import (
    PipelineConfigResponse,
    PipelineListResponse,
    PipelineListItem,
    PipelineCreateRequest,
    PipelineUpdateRequest,
    PipelineStatus,
    PaginationInfo,
    MessageResponse,
    InputSpec,
    OutputSpec,
    StepConfig,
    StepType,
)
from ...pipeline_config import (
    load_pipeline_config,
    list_available_pipelines,
    save_pipeline_config,
    PIPELINE_DIRS,
)
from ...models import PipelineConfig as InternalPipelineConfig

router = APIRouter(prefix="/pipelines", tags=["Pipelines"])


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


def find_pipeline_file(pipeline_id: str) -> Optional[Path]:
    """
    Find the configuration file for a pipeline.
    
    Args:
        pipeline_id: Pipeline identifier
        
    Returns:
        Path to the pipeline configuration file, or None if not found
    """
    for base_dir in PIPELINE_DIRS:
        if not base_dir.exists():
            continue
        
        # Check for {base_dir}/{pipeline_id}.yaml
        yaml_file = base_dir / f"{pipeline_id}.yaml"
        if yaml_file.exists():
            return yaml_file
        
        # Check for {base_dir}/{pipeline_id}/pipeline.yaml
        pipeline_dir = base_dir / pipeline_id
        if pipeline_dir.is_dir():
            pipeline_yaml = pipeline_dir / "pipeline.yaml"
            if pipeline_yaml.exists():
                return pipeline_yaml
    
    return None


def get_pipeline_metadata(pipeline_id: str, config_path: Path) -> dict:
    """
    Get metadata for a pipeline from its configuration file.
    
    Args:
        pipeline_id: Pipeline identifier
        config_path: Path to the configuration file
        
    Returns:
        Dictionary with pipeline metadata
    """
    try:
        stat = config_path.stat()
        created_at = datetime.fromtimestamp(stat.st_ctime)
        updated_at = datetime.fromtimestamp(stat.st_mtime)
        
        # Load config to get details
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return {
            "id": pipeline_id,
            "name": data.get("name", pipeline_id),
            "description": data.get("description", ""),
            "version": data.get("version", "1.0.0"),
            "status": PipelineStatus.ACTIVE,  # Default status
            "steps_count": len(data.get("steps", [])),
            "created_at": created_at,
            "updated_at": updated_at,
        }
    except Exception as e:
        # Return minimal metadata if we can't read the file
        return {
            "id": pipeline_id,
            "name": pipeline_id,
            "description": "",
            "version": "1.0.0",
            "status": PipelineStatus.ACTIVE,
            "steps_count": 0,
            "created_at": None,
            "updated_at": None,
        }


def internal_to_api_step(step) -> StepConfig:
    """
    Convert internal StepConfig to API StepConfig.
    
    Args:
        step: Internal StepConfig instance
        
    Returns:
        API StepConfig instance
    """
    # Determine step type
    if hasattr(step, 'type') and step.type:
        step_type = StepType(step.type)
    elif step.agent:
        step_type = StepType.AGENT_FLOW
    else:
        step_type = StepType.CODE_NODE
    
    return StepConfig(
        id=step.id,
        type=step_type,
        agent=step.agent if hasattr(step, 'agent') else None,
        flow=step.flow if hasattr(step, 'flow') else None,
        input_mapping=step.input_mapping,
        output_key=step.output_key,
        concurrent_group=step.concurrent_group if hasattr(step, 'concurrent_group') else None,
        depends_on=step.depends_on if hasattr(step, 'depends_on') else [],
        required=step.required if hasattr(step, 'required') else True,
    )


def internal_to_api_config(config: InternalPipelineConfig) -> PipelineConfigResponse:
    """
    Convert internal PipelineConfig to API PipelineConfigResponse.
    
    Args:
        config: Internal PipelineConfig instance
        
    Returns:
        API PipelineConfigResponse instance
    """
    # Get file metadata
    config_path = find_pipeline_file(config.id)
    created_at = None
    updated_at = None
    version = "1.0.0"  # Default version
    
    if config_path:
        stat = config_path.stat()
        created_at = datetime.fromtimestamp(stat.st_ctime)
        updated_at = datetime.fromtimestamp(stat.st_mtime)
        
        # Try to read version from file
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                version = data.get('version', '1.0.0')
        except:
            pass
    
    # Convert inputs
    api_inputs = [
        InputSpec(
            name=inp.name,
            desc=inp.desc,
            required=inp.required
        )
        for inp in config.inputs
    ]
    
    # Convert outputs
    api_outputs = [
        OutputSpec(
            key=out.key,
            label=out.label
        )
        for out in config.outputs
    ]
    
    # Convert steps
    api_steps = [internal_to_api_step(step) for step in config.steps]
    
    return PipelineConfigResponse(
        id=config.id,
        name=config.name,
        description=config.description,
        version=version,
        status=PipelineStatus.ACTIVE,  # Default status
        inputs=api_inputs,
        outputs=api_outputs,
        steps=api_steps,
        created_at=created_at,
        updated_at=updated_at,
    )


@router.get("/", response_model=PipelineListResponse)
async def list_pipelines(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    status: Optional[PipelineStatus] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search query"),
):
    """
    List all configured pipelines with filtering and pagination.
    
    This endpoint returns a paginated list of pipelines with optional filtering by:
    - Status (active, draft, archived)
    - Search query (searches in id, name, description)
    
    **Example:**
    ```
    GET /api/v1/pipelines?status=active&page=1&page_size=20
    ```
    
    **Response:**
    ```json
    {
      "pipelines": [
        {
          "id": "customer_service_flow",
          "name": "Customer Service Pipeline",
          "description": "Multi-step customer service processing",
          "version": "1.0.0",
          "status": "active",
          "steps_count": 5,
          "created_at": "2024-01-01T00:00:00Z",
          "updated_at": "2024-12-01T00:00:00Z"
        }
      ],
      "pagination": {
        "page": 1,
        "page_size": 20,
        "total_items": 5,
        "total_pages": 1
      }
    }
    ```
    """
    try:
        # Get all available pipelines
        pipeline_ids = list_available_pipelines()
        
        # Build pipeline list with metadata
        pipelines = []
        for pipeline_id in pipeline_ids:
            config_path = find_pipeline_file(pipeline_id)
            if config_path:
                metadata = get_pipeline_metadata(pipeline_id, config_path)
                
                # Apply status filter
                if status and metadata["status"] != status:
                    continue
                
                # Apply search filter
                if search:
                    search_lower = search.lower()
                    if not (
                        search_lower in metadata["id"].lower() or
                        search_lower in metadata["name"].lower() or
                        search_lower in metadata["description"].lower()
                    ):
                        continue
                
                pipelines.append(PipelineListItem(**metadata))
        
        # Sort by ID
        pipelines.sort(key=lambda p: p.id)
        
        # Paginate results
        paginated_pipelines, pagination = paginate(pipelines, page, page_size)
        
        return PipelineListResponse(
            pipelines=paginated_pipelines,
            pagination=pagination
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": f"Failed to list pipelines: {str(e)}"
            }
        )


@router.get("/{pipeline_id}", response_model=PipelineConfigResponse)
async def get_pipeline(pipeline_id: str):
    """
    Get detailed configuration for a specific pipeline.
    
    This endpoint returns complete configuration for a single pipeline including:
    - Basic information (id, name, version, description)
    - Input and output specifications
    - Step configurations with dependencies
    - Timestamps
    
    **Example:**
    ```
    GET /api/v1/pipelines/customer_service_flow
    ```
    
    **Response:**
    ```json
    {
      "id": "customer_service_flow",
      "name": "Customer Service Pipeline",
      "description": "Multi-step customer service processing",
      "version": "1.0.0",
      "status": "active",
      "inputs": [
        {
          "name": "customer_query",
          "desc": "Customer question or request",
          "required": true
        }
      ],
      "outputs": [
        {
          "key": "response",
          "label": "Final Response"
        }
      ],
      "steps": [
        {
          "id": "classify",
          "type": "agent_flow",
          "agent": "intent_classifier",
          "flow": "default",
          "input_mapping": {
            "text": "customer_query"
          },
          "output_key": "intent"
        }
      ],
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-12-01T00:00:00Z"
    }
    ```
    """
    try:
        # Load pipeline configuration
        config = load_pipeline_config(pipeline_id)
        
        # Convert to API response model
        return internal_to_api_config(config)
        
    except (FileNotFoundError, Exception) as e:
        # Check if it's a "not found" error
        error_msg = str(e)
        if "找不到" in error_msg or "not found" in error_msg.lower() or isinstance(e, FileNotFoundError):
            # Pipeline not found
            available_pipelines = ", ".join(sorted(list_available_pipelines())[:10])
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "NotFound",
                    "message": f"Pipeline '{pipeline_id}' not found",
                    "available_pipelines": available_pipelines + ("..." if len(list_available_pipelines()) > 10 else "")
                }
            )
        else:
            # Other errors
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "InternalServerError",
                    "message": f"Failed to get pipeline: {str(e)}"
                }
            )


@router.post("/", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_pipeline(request: PipelineCreateRequest):
    """
    Create a new pipeline configuration.
    
    This endpoint creates a new pipeline configuration file. The pipeline must have:
    - A unique ID (alphanumeric with underscores)
    - A name and description
    - Input and output specifications
    - At least one step
    
    **Note:** This creates a new YAML configuration file in the pipelines directory.
    
    **Example:**
    ```
    POST /api/v1/pipelines
    {
      "id": "new_pipeline",
      "name": "New Pipeline",
      "description": "Pipeline description",
      "inputs": [
        {
          "name": "input1",
          "desc": "Input description",
          "required": true
        }
      ],
      "outputs": [
        {
          "key": "output1",
          "label": "Output Label"
        }
      ],
      "steps": [
        {
          "id": "step1",
          "type": "agent_flow",
          "agent": "agent1",
          "flow": "default",
          "input_mapping": {
            "text": "input1"
          },
          "output_key": "result1"
        }
      ]
    }
    ```
    
    **Response:**
    ```json
    {
      "message": "Pipeline created successfully",
      "data": {
        "id": "new_pipeline",
        "file_path": "pipelines/new_pipeline.yaml"
      }
    }
    ```
    """
    try:
        # Check if pipeline already exists
        if find_pipeline_file(request.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "error": "Conflict",
                    "message": f"Pipeline '{request.id}' already exists"
                }
            )
        
        # Convert API request to internal config
        from ...models import InputSpec as InternalInputSpec
        from ...models import OutputSpec as InternalOutputSpec
        from ...models import StepConfig as InternalStepConfig
        
        internal_inputs = [
            InternalInputSpec(
                name=inp.name,
                desc=inp.desc,
                required=inp.required
            )
            for inp in request.inputs
        ]
        
        internal_outputs = [
            InternalOutputSpec(
                key=out.key,
                label=out.label
            )
            for out in request.outputs
        ]
        
        internal_steps = []
        for step in request.steps:
            internal_step = InternalStepConfig(
                id=step.id,
                type=step.type.value,
                agent=step.agent,
                flow=step.flow,
                input_mapping=step.input_mapping,
                output_key=step.output_key,
                concurrent_group=step.concurrent_group,
                depends_on=step.depends_on,
                required=step.required,
            )
            internal_steps.append(internal_step)
        
        # Create internal config
        config = InternalPipelineConfig(
            id=request.id,
            name=request.name,
            description=request.description,
            inputs=internal_inputs,
            outputs=internal_outputs,
            steps=internal_steps,
        )
        
        # Save configuration
        file_path = save_pipeline_config(config)
        
        # Add version to the YAML file manually
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            data['version'] = '1.0.0'
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)
        except:
            pass  # If we can't add version, that's okay
        
        return MessageResponse(
            message="Pipeline created successfully",
            data={
                "id": request.id,
                "file_path": str(file_path)
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
                "message": f"Failed to create pipeline: {str(e)}"
            }
        )


@router.put("/{pipeline_id}", response_model=MessageResponse)
async def update_pipeline(
    pipeline_id: str,
    request: PipelineUpdateRequest,
):
    """
    Update an existing pipeline's configuration.
    
    This endpoint updates the configuration for an existing pipeline. You can update:
    - Name
    - Description
    - Steps
    
    Fields not provided in the request will remain unchanged.
    
    **Note:** This updates the YAML configuration file on disk.
    
    **Example:**
    ```
    PUT /api/v1/pipelines/customer_service_flow
    {
      "name": "Updated Pipeline Name",
      "description": "Updated description",
      "steps": [...]
    }
    ```
    
    **Response:**
    ```json
    {
      "message": "Pipeline updated successfully",
      "data": {
        "id": "customer_service_flow",
        "file_path": "pipelines/customer_service_flow.yaml"
      }
    }
    ```
    """
    try:
        # Load existing pipeline
        try:
            config = load_pipeline_config(pipeline_id)
        except Exception as e:
            # Check if it's a "not found" error
            error_msg = str(e)
            if "找不到" in error_msg or "not found" in error_msg.lower() or isinstance(e, FileNotFoundError):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail={
                        "error": "NotFound",
                        "message": f"Pipeline '{pipeline_id}' not found"
                    }
                )
            else:
                raise
        
        # Update fields if provided
        if request.name is not None:
            config.name = request.name
        if request.description is not None:
            config.description = request.description
        if request.steps is not None:
            # Convert API steps to internal steps
            from ...models import StepConfig as InternalStepConfig
            
            internal_steps = []
            for step in request.steps:
                internal_step = InternalStepConfig(
                    id=step.id,
                    type=step.type.value,
                    agent=step.agent,
                    flow=step.flow,
                    input_mapping=step.input_mapping,
                    output_key=step.output_key,
                    concurrent_group=step.concurrent_group,
                    depends_on=step.depends_on,
                    required=step.required,
                )
                internal_steps.append(internal_step)
            
            config.steps = internal_steps
        
        # Find the existing file path
        existing_file_path = find_pipeline_file(pipeline_id)
        if not existing_file_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "NotFound",
                    "message": f"Pipeline configuration file for '{pipeline_id}' not found"
                }
            )
        
        # Save updated configuration to the same file
        file_path = save_pipeline_config(config, existing_file_path)
        
        return MessageResponse(
            message="Pipeline updated successfully",
            data={
                "id": pipeline_id,
                "file_path": str(file_path)
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
                "message": f"Failed to update pipeline: {str(e)}"
            }
        )
