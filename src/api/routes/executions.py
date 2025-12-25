"""
Async Execution API Routes

This module implements asynchronous execution endpoints for agents and pipelines.
It provides:
- POST /executions - Start async execution
- GET /executions/{execution_id} - Get execution status
- GET /executions - List executions
- POST /executions/{execution_id}/cancel - Cancel execution

Requirements: 8.5
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, WebSocket, WebSocketDisconnect
from typing import Optional, List
import uuid
from datetime import datetime
import logging
import asyncio
import json

from ..models import (
    AsyncExecutionRequest,
    AsyncExecutionResponse,
    ExecutionStatusResponse,
    ExecutionListResponse,
    ExecutionListItem,
    ExecutionStatus,
    ExecutionType,
    MessageResponse,
    PaginationInfo,
    ProgressInfo
)
from ..dependencies import get_execution_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/executions", tags=["Async Execution"])


@router.post("", response_model=AsyncExecutionResponse, status_code=202)
async def start_async_execution(
    request: AsyncExecutionRequest,
    background_tasks: BackgroundTasks
):
    """
    Start an asynchronous execution (agent or pipeline).
    
    The execution runs in the background and returns immediately with an execution ID.
    Use the execution ID to query status and retrieve results.
    
    **Request Body:**
    - `type`: Execution type ("agent" or "pipeline")
    - `target_id`: Agent ID or Pipeline ID
    - `inputs`: Input parameters for the execution
    - `config`: Optional configuration overrides
    - `callback_url`: Optional webhook URL for completion notification
    
    **Returns:**
    - `execution_id`: Unique identifier for this execution
    - `status`: Initial status ("pending")
    - `status_url`: URL to query execution status
    - `created_at`: Timestamp when execution was created
    
    **Example:**
    ```json
    {
      "type": "pipeline",
      "target_id": "customer_service_flow",
      "inputs": {
        "customer_query": "How do I reset my password?"
      },
      "config": {
        "max_workers": 4
      }
    }
    ```
    """
    try:
        # Generate unique execution ID
        execution_id = f"exec_{uuid.uuid4().hex[:12]}"
        
        # Get execution manager
        execution_manager = get_execution_manager()
        
        # Create execution record
        execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=request.type,
            target_id=request.target_id,
            inputs=request.inputs,
            config=request.config,
            callback_url=request.callback_url
        )
        
        # Schedule background execution
        if request.type == ExecutionType.AGENT:
            background_tasks.add_task(
                execution_manager.execute_agent_async,
                execution_id=execution_id,
                agent_id=request.target_id,
                inputs=request.inputs,
                config=request.config
            )
        elif request.type == ExecutionType.PIPELINE:
            background_tasks.add_task(
                execution_manager.execute_pipeline_async,
                execution_id=execution_id,
                pipeline_id=request.target_id,
                inputs=request.inputs,
                config=request.config
            )
        
        logger.info(f"Started async execution: {execution_id} (type={request.type}, target={request.target_id})")
        
        return AsyncExecutionResponse(
            execution_id=execution_id,
            status=ExecutionStatus.PENDING,
            message=f"{request.type.value.capitalize()} execution started",
            status_url=f"/api/v1/executions/{execution_id}",
            created_at=datetime.now()
        )
        
    except ValueError as e:
        logger.error(f"Validation error in async execution: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except FileNotFoundError as e:
        logger.error(f"Resource not found: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error starting async execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to start execution: {str(e)}")


@router.get("/{execution_id}", response_model=ExecutionStatusResponse)
async def get_execution_status(execution_id: str):
    """
    Get the status and results of an execution.
    
    **Path Parameters:**
    - `execution_id`: Unique execution identifier
    
    **Returns:**
    - Execution status, progress, outputs, and error information (if any)
    
    **Status Values:**
    - `pending`: Execution queued but not started
    - `running`: Execution in progress
    - `completed`: Execution finished successfully
    - `failed`: Execution failed with error
    - `cancelled`: Execution was cancelled
    
    **Example Response (Running):**
    ```json
    {
      "execution_id": "exec_123456",
      "type": "pipeline",
      "target_id": "customer_service_flow",
      "status": "running",
      "progress": {
        "current_step": 1,
        "total_steps": 3,
        "percentage": 33.3,
        "current_step_name": "classify"
      },
      "started_at": "2024-12-17T10:30:00Z"
    }
    ```
    
    **Example Response (Completed):**
    ```json
    {
      "execution_id": "exec_123456",
      "type": "pipeline",
      "target_id": "customer_service_flow",
      "status": "completed",
      "progress": {
        "current_step": 3,
        "total_steps": 3,
        "percentage": 100.0
      },
      "outputs": {
        "response": "To reset your password..."
      },
      "started_at": "2024-12-17T10:30:00Z",
      "completed_at": "2024-12-17T10:30:05Z"
    }
    ```
    """
    try:
        execution_manager = get_execution_manager()
        status = execution_manager.get_execution_status(execution_id)
        
        if status is None:
            raise HTTPException(
                status_code=404,
                detail=f"Execution '{execution_id}' not found"
            )
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get execution status: {str(e)}")


@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    status: Optional[ExecutionStatus] = Query(None, description="Filter by status"),
    type: Optional[ExecutionType] = Query(None, description="Filter by type"),
    target_id: Optional[str] = Query(None, description="Filter by target ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    sort: str = Query("created_at", description="Sort field"),
    order: str = Query("desc", description="Sort order (asc/desc)")
):
    """
    List all executions with optional filtering and pagination.
    
    **Query Parameters:**
    - `status`: Filter by execution status
    - `type`: Filter by execution type (agent/pipeline)
    - `target_id`: Filter by target agent/pipeline ID
    - `page`: Page number (default: 1)
    - `page_size`: Items per page (default: 50, max: 100)
    - `sort`: Sort field (default: created_at)
    - `order`: Sort order - asc or desc (default: desc)
    
    **Returns:**
    - List of executions with pagination information
    
    **Example:**
    ```
    GET /api/v1/executions?status=completed&type=pipeline&page=1&page_size=20
    ```
    """
    try:
        execution_manager = get_execution_manager()
        
        # Get filtered executions
        executions = execution_manager.list_executions(
            status=status,
            execution_type=type,
            target_id=target_id,
            sort_by=sort,
            sort_order=order
        )
        
        # Apply pagination
        total_items = len(executions)
        total_pages = (total_items + page_size - 1) // page_size
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        paginated_executions = executions[start_idx:end_idx]
        
        # Convert to list items
        execution_items = [
            ExecutionListItem(
                execution_id=exec.execution_id,
                type=exec.type,
                target_id=exec.target_id,
                status=exec.status,
                started_at=exec.started_at or exec.created_at,
                completed_at=exec.completed_at
            )
            for exec in paginated_executions
        ]
        
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
        
        return ExecutionListResponse(
            executions=execution_items,
            pagination=pagination
        )
        
    except Exception as e:
        logger.error(f"Error listing executions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list executions: {str(e)}")


@router.get("/{execution_id}/progress", response_model=ProgressInfo)
async def get_execution_progress(execution_id: str):
    """
    Get detailed progress information for a running execution.
    
    This endpoint provides real-time progress updates for long-running executions,
    including current step information and completion percentage.
    
    **Path Parameters:**
    - `execution_id`: Unique execution identifier
    
    **Returns:**
    - Detailed progress information including:
      - `current_step`: Current step number (0-indexed)
      - `total_steps`: Total number of steps
      - `percentage`: Completion percentage (0-100)
      - `current_step_name`: Name of the current step (if available)
    
    **Status Codes:**
    - `200`: Progress information retrieved successfully
    - `404`: Execution not found
    - `204`: No progress information available (execution pending or completed)
    
    **Example Response:**
    ```json
    {
      "current_step": 2,
      "total_steps": 5,
      "percentage": 40.0,
      "current_step_name": "data_processing"
    }
    ```
    
    **Use Cases:**
    - Polling for progress updates in UI
    - Monitoring long-running pipeline executions
    - Displaying progress bars and status indicators
    
    **Note:**
    - For real-time updates, consider using the WebSocket endpoint instead
    - Progress information is only available for running executions
    - Returns 204 No Content if execution has no progress data
    """
    try:
        execution_manager = get_execution_manager()
        
        # Get execution status
        status = execution_manager.get_execution_status(execution_id)
        if status is None:
            raise HTTPException(
                status_code=404,
                detail=f"Execution '{execution_id}' not found"
            )
        
        # Check if progress information is available
        if status.progress is None:
            # Return 204 No Content if no progress data
            from fastapi.responses import Response
            return Response(status_code=204)
        
        return status.progress
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting execution progress: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get execution progress: {str(e)}")


@router.post("/{execution_id}/cancel", response_model=MessageResponse)
async def cancel_execution(execution_id: str):
    """
    Cancel a running execution.
    
    **Path Parameters:**
    - `execution_id`: Unique execution identifier
    
    **Returns:**
    - Confirmation message with cancellation timestamp
    
    **Note:**
    - Only executions with status "pending" or "running" can be cancelled
    - Completed or failed executions cannot be cancelled
    
    **Example Response:**
    ```json
    {
      "message": "Execution cancelled successfully",
      "data": {
        "execution_id": "exec_123456",
        "status": "cancelled",
        "cancelled_at": "2024-12-17T10:30:05Z"
      }
    }
    ```
    """
    try:
        execution_manager = get_execution_manager()
        
        # Check if execution exists
        status = execution_manager.get_execution_status(execution_id)
        if status is None:
            raise HTTPException(
                status_code=404,
                detail=f"Execution '{execution_id}' not found"
            )
        
        # Check if execution can be cancelled
        if status.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel execution with status '{status.status.value}'"
            )
        
        # Cancel execution
        cancelled_at = execution_manager.cancel_execution(execution_id)
        
        logger.info(f"Cancelled execution: {execution_id}")
        
        return MessageResponse(
            message="Execution cancelled successfully",
            data={
                "execution_id": execution_id,
                "status": "cancelled",
                "cancelled_at": cancelled_at.isoformat()
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling execution: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cancel execution: {str(e)}")


@router.websocket("/{execution_id}/progress/ws")
async def websocket_execution_progress(websocket: WebSocket, execution_id: str):
    """
    WebSocket endpoint for real-time execution progress updates.
    
    This endpoint provides a persistent connection for streaming progress updates
    as the execution progresses. The client receives JSON messages with progress
    information whenever the execution state changes.
    
    **Path Parameters:**
    - `execution_id`: Unique execution identifier
    
    **Connection:**
    ```javascript
    const ws = new WebSocket('ws://localhost:8000/api/v1/executions/exec_123456/progress/ws');
    
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('Progress:', data);
    };
    ```
    
    **Message Format:**
    ```json
    {
      "type": "progress",
      "execution_id": "exec_123456",
      "status": "running",
      "progress": {
        "current_step": 2,
        "total_steps": 5,
        "percentage": 40.0,
        "current_step_name": "data_processing"
      },
      "timestamp": "2024-12-17T10:30:05Z"
    }
    ```
    
    **Message Types:**
    - `progress`: Progress update during execution
    - `completed`: Execution completed successfully
    - `failed`: Execution failed with error
    - `cancelled`: Execution was cancelled
    - `error`: WebSocket error occurred
    
    **Completion Message:**
    ```json
    {
      "type": "completed",
      "execution_id": "exec_123456",
      "status": "completed",
      "outputs": {...},
      "timestamp": "2024-12-17T10:30:10Z"
    }
    ```
    
    **Error Message:**
    ```json
    {
      "type": "failed",
      "execution_id": "exec_123456",
      "status": "failed",
      "error": {
        "type": "ValueError",
        "message": "Invalid input"
      },
      "timestamp": "2024-12-17T10:30:10Z"
    }
    ```
    
    **Connection Lifecycle:**
    1. Client connects to WebSocket
    2. Server sends initial status message
    3. Server sends progress updates as execution progresses
    4. Server sends final status message (completed/failed/cancelled)
    5. Connection closes automatically after completion
    
    **Polling Interval:**
    - Progress updates are sent every 500ms while execution is running
    - No updates are sent if progress hasn't changed
    - Connection closes after execution completes or fails
    
    **Error Handling:**
    - If execution doesn't exist, connection closes with error message
    - If execution is already completed, sends final status and closes
    - Network errors automatically close the connection
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established for execution: {execution_id}")
    
    try:
        execution_manager = get_execution_manager()
        
        # Check if execution exists
        status = execution_manager.get_execution_status(execution_id)
        if status is None:
            await websocket.send_json({
                "type": "error",
                "message": f"Execution '{execution_id}' not found",
                "timestamp": datetime.now().isoformat()
            })
            await websocket.close(code=1008, reason="Execution not found")
            return
        
        # Send initial status
        await websocket.send_json({
            "type": "status",
            "execution_id": execution_id,
            "status": status.status.value,
            "progress": status.progress.dict() if status.progress else None,
            "timestamp": datetime.now().isoformat()
        })
        
        # If execution is already completed, send final status and close
        if status.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
            await websocket.send_json({
                "type": status.status.value,
                "execution_id": execution_id,
                "status": status.status.value,
                "outputs": status.outputs,
                "error": status.error.dict() if status.error else None,
                "timestamp": datetime.now().isoformat()
            })
            await websocket.close(code=1000, reason="Execution already completed")
            return
        
        # Poll for progress updates
        last_progress = None
        last_status = status.status
        
        while True:
            # Get current status
            current_status = execution_manager.get_execution_status(execution_id)
            
            if current_status is None:
                # Execution was deleted
                await websocket.send_json({
                    "type": "error",
                    "message": "Execution no longer exists",
                    "timestamp": datetime.now().isoformat()
                })
                break
            
            # Check if status changed
            if current_status.status != last_status:
                last_status = current_status.status
                
                # Send status change message
                if current_status.status == ExecutionStatus.RUNNING:
                    await websocket.send_json({
                        "type": "started",
                        "execution_id": execution_id,
                        "status": "running",
                        "timestamp": datetime.now().isoformat()
                    })
                elif current_status.status == ExecutionStatus.COMPLETED:
                    await websocket.send_json({
                        "type": "completed",
                        "execution_id": execution_id,
                        "status": "completed",
                        "outputs": current_status.outputs,
                        "timestamp": datetime.now().isoformat()
                    })
                    break
                elif current_status.status == ExecutionStatus.FAILED:
                    await websocket.send_json({
                        "type": "failed",
                        "execution_id": execution_id,
                        "status": "failed",
                        "error": current_status.error.dict() if current_status.error else None,
                        "timestamp": datetime.now().isoformat()
                    })
                    break
                elif current_status.status == ExecutionStatus.CANCELLED:
                    await websocket.send_json({
                        "type": "cancelled",
                        "execution_id": execution_id,
                        "status": "cancelled",
                        "timestamp": datetime.now().isoformat()
                    })
                    break
            
            # Check if progress changed
            if current_status.progress != last_progress:
                last_progress = current_status.progress
                
                # Send progress update
                if current_status.progress:
                    await websocket.send_json({
                        "type": "progress",
                        "execution_id": execution_id,
                        "status": current_status.status.value,
                        "progress": current_status.progress.dict(),
                        "timestamp": datetime.now().isoformat()
                    })
            
            # Wait before next poll
            await asyncio.sleep(0.5)
        
        # Close connection
        await websocket.close(code=1000, reason="Execution completed")
        logger.info(f"WebSocket connection closed for execution: {execution_id}")
        
    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {execution_id}")
    except Exception as e:
        logger.error(f"WebSocket error for execution {execution_id}: {e}", exc_info=True)
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            })
            await websocket.close(code=1011, reason="Internal error")
        except:
            pass
