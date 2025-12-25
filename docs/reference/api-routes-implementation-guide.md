# API Routes Implementation Guide

This guide provides implementation details for all API routes defined in the API Design Specification.

## Route Organization

Routes are organized into separate modules by resource type:

```
src/api/routes/
├── __init__.py          # Router aggregation
├── system.py            # System endpoints (health, info)
├── agents.py            # Agent management endpoints
├── pipelines.py         # Pipeline management endpoints
├── executions.py        # Async execution endpoints
├── batch.py             # Batch processing endpoints
└── config.py            # Configuration management endpoints
```

## Implementation Pattern

Each route module follows this pattern:

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from ..models import *
from ..dependencies import get_agent_registry, get_pipeline_runner

router = APIRouter(prefix="/resource", tags=["Resource"])

@router.get("/")
async def list_resources(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    # ... other query params
):
    """List all resources with pagination."""
    # Implementation
    pass

@router.get("/{resource_id}")
async def get_resource(resource_id: str):
    """Get a specific resource."""
    # Implementation
    pass

@router.post("/")
async def create_resource(request: ResourceCreateRequest):
    """Create a new resource."""
    # Implementation
    pass

@router.put("/{resource_id}")
async def update_resource(resource_id: str, request: ResourceUpdateRequest):
    """Update a resource."""
    # Implementation
    pass

@router.delete("/{resource_id}")
async def delete_resource(resource_id: str):
    """Delete a resource."""
    # Implementation
    pass
```

## Dependency Injection

Common dependencies are defined in `src/api/dependencies.py`:

```python
from src.agent_registry_v2 import AgentRegistry
from src.pipeline_runner import PipelineRunner
from src.concurrent_executor import ConcurrentExecutor

def get_agent_registry() -> AgentRegistry:
    """Get the agent registry instance."""
    # Return singleton or create new instance
    pass

def get_pipeline_runner() -> PipelineRunner:
    """Get the pipeline runner instance."""
    pass

def get_concurrent_executor() -> ConcurrentExecutor:
    """Get the concurrent executor instance."""
    pass
```

## Error Handling

Use FastAPI's HTTPException for standard errors:

```python
from fastapi import HTTPException, status

# Not Found
raise HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={
        "error": "NotFound",
        "message": f"Agent '{agent_id}' not found"
    }
)

# Validation Error
raise HTTPException(
    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    detail={
        "error": "ValidationError",
        "message": "Invalid configuration",
        "details": {"validation_errors": errors}
    }
)

# Conflict
raise HTTPException(
    status_code=status.HTTP_409_CONFLICT,
    detail={
        "error": "Conflict",
        "message": f"Agent '{agent_id}' already exists"
    }
)
```

## Pagination Helper

Create a pagination helper function:

```python
from typing import List, TypeVar, Generic
from ..models import PaginationInfo

T = TypeVar('T')

def paginate(
    items: List[T],
    page: int,
    page_size: int
) -> tuple[List[T], PaginationInfo]:
    """Paginate a list of items."""
    total_items = len(items)
    total_pages = (total_items + page_size - 1) // page_size
    
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
```

## Async Execution Management

For async executions, use a task manager:

```python
import asyncio
from typing import Dict
from uuid import uuid4

class ExecutionManager:
    """Manage async executions."""
    
    def __init__(self):
        self.executions: Dict[str, asyncio.Task] = {}
        self.results: Dict[str, Any] = {}
    
    def start_execution(self, coro) -> str:
        """Start an async execution."""
        execution_id = f"exec_{uuid4().hex[:12]}"
        task = asyncio.create_task(coro)
        self.executions[execution_id] = task
        return execution_id
    
    def get_status(self, execution_id: str) -> dict:
        """Get execution status."""
        if execution_id not in self.executions:
            raise ValueError(f"Execution {execution_id} not found")
        
        task = self.executions[execution_id]
        
        if task.done():
            if task.exception():
                return {"status": "failed", "error": str(task.exception())}
            else:
                return {"status": "completed", "result": task.result()}
        else:
            return {"status": "running"}
    
    def cancel_execution(self, execution_id: str):
        """Cancel an execution."""
        if execution_id in self.executions:
            self.executions[execution_id].cancel()
```

## WebSocket Support

For real-time progress updates:

```python
from fastapi import WebSocket, WebSocketDisconnect

@router.websocket("/{execution_id}/progress")
async def execution_progress(
    websocket: WebSocket,
    execution_id: str
):
    """WebSocket endpoint for real-time progress updates."""
    await websocket.accept()
    
    try:
        while True:
            # Get current progress
            progress = get_execution_progress(execution_id)
            
            # Send progress update
            await websocket.send_json({
                "type": "progress",
                "execution_id": execution_id,
                "progress": progress,
                "timestamp": datetime.now().isoformat()
            })
            
            # Check if completed
            if progress["status"] in ["completed", "failed", "cancelled"]:
                break
            
            # Wait before next update
            await asyncio.sleep(1)
    
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
```

## Testing Routes

Use FastAPI's TestClient for testing:

```python
from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)

def test_list_agents():
    response = client.get("/api/v1/agents")
    assert response.status_code == 200
    data = response.json()
    assert "agents" in data
    assert "pagination" in data

def test_get_agent():
    response = client.get("/api/v1/agents/mem_l1_summarizer")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "mem_l1_summarizer"

def test_agent_not_found():
    response = client.get("/api/v1/agents/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "NotFound"
```

## Next Steps

1. Implement system routes (Task 72 - partial)
2. Implement agent management routes (Task 72)
3. Implement pipeline management routes (Task 73)
4. Implement configuration routes (Task 74)
5. Implement async execution routes (Task 75)
6. Implement progress tracking routes (Task 76)
7. Add comprehensive tests for all routes

## References

- API Design Specification: `docs/reference/api-design-specification.md`
- FastAPI Documentation: https://fastapi.tiangolo.com/
- Pydantic Models: `src/api/models.py`
