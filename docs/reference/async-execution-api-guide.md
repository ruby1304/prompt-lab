# Async Execution API Guide

**Version:** 1.0.0  
**Status:** Implemented  
**Requirements:** 8.5

## Overview

The Async Execution API provides endpoints for executing agents and pipelines asynchronously. This allows long-running operations to be performed in the background while the client can poll for status and retrieve results when ready.

## Key Features

- **Asynchronous Execution**: Start agent/pipeline execution and get immediate response
- **Status Tracking**: Query execution status and progress at any time
- **Result Retrieval**: Get outputs when execution completes
- **Cancellation**: Cancel running executions
- **Filtering & Pagination**: List and filter executions with pagination support
- **Webhook Callbacks**: Optional webhook notifications on completion (future)

## Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ POST /executions
       ▼
┌─────────────────────────────┐
│   Execution Manager         │
│  - Task Queue               │
│  - Status Tracking          │
│  - Background Execution     │
└─────────────────────────────┘
       │
       ├─► Agent Execution
       └─► Pipeline Execution
```

## API Endpoints

### 1. Start Async Execution

**Endpoint:** `POST /api/v1/executions`

Start an asynchronous execution of an agent or pipeline.

**Request Body:**
```json
{
  "type": "agent|pipeline",
  "target_id": "agent_id or pipeline_id",
  "inputs": {
    "key": "value"
  },
  "config": {
    "flow_id": "default",
    "max_workers": 4
  },
  "callback_url": "https://example.com/webhook"
}
```

**Response (202 Accepted):**
```json
{
  "execution_id": "exec_abc123",
  "status": "pending",
  "message": "Agent execution started",
  "status_url": "/api/v1/executions/exec_abc123",
  "created_at": "2024-12-17T10:30:00Z"
}
```

**Example:**
```python
import requests

response = requests.post(
    "http://localhost:8000/api/v1/executions",
    json={
        "type": "agent",
        "target_id": "mem_l1_summarizer",
        "inputs": {
            "text": "Input text to process"
        },
        "config": {
            "flow_id": "default"
        }
    }
)

execution_id = response.json()["execution_id"]
```

### 2. Get Execution Status

**Endpoint:** `GET /api/v1/executions/{execution_id}`

Get the current status and results of an execution.

**Response (200 OK):**

**Pending/Running:**
```json
{
  "execution_id": "exec_abc123",
  "type": "agent",
  "target_id": "mem_l1_summarizer",
  "status": "running",
  "progress": {
    "current_step": 1,
    "total_steps": 3,
    "percentage": 33.3,
    "current_step_name": "processing"
  },
  "started_at": "2024-12-17T10:30:00Z"
}
```

**Completed:**
```json
{
  "execution_id": "exec_abc123",
  "type": "agent",
  "target_id": "mem_l1_summarizer",
  "status": "completed",
  "progress": {
    "current_step": 3,
    "total_steps": 3,
    "percentage": 100.0
  },
  "outputs": {
    "output": "Processed result",
    "metadata": {
      "model_used": "doubao-pro-32k",
      "tokens_used": 250
    }
  },
  "started_at": "2024-12-17T10:30:00Z",
  "completed_at": "2024-12-17T10:30:05Z"
}
```

**Failed:**
```json
{
  "execution_id": "exec_abc123",
  "type": "agent",
  "target_id": "mem_l1_summarizer",
  "status": "failed",
  "error": {
    "type": "ExecutionError",
    "message": "Agent execution failed",
    "details": {
      "agent_id": "mem_l1_summarizer"
    }
  },
  "started_at": "2024-12-17T10:30:00Z",
  "failed_at": "2024-12-17T10:30:05Z"
}
```

**Example:**
```python
import time

# Poll for completion
while True:
    response = requests.get(
        f"http://localhost:8000/api/v1/executions/{execution_id}"
    )
    status = response.json()
    
    if status["status"] in ["completed", "failed", "cancelled"]:
        break
    
    # Print progress
    if "progress" in status:
        print(f"Progress: {status['progress']['percentage']:.1f}%")
    
    time.sleep(1)

# Get results
if status["status"] == "completed":
    outputs = status["outputs"]
    print(f"Result: {outputs}")
```

### 3. List Executions

**Endpoint:** `GET /api/v1/executions`

List all executions with optional filtering and pagination.

**Query Parameters:**
- `status` (optional): Filter by status (pending, running, completed, failed, cancelled)
- `type` (optional): Filter by type (agent, pipeline)
- `target_id` (optional): Filter by target agent/pipeline ID
- `page` (optional, default=1): Page number
- `page_size` (optional, default=50): Items per page
- `sort` (optional, default=created_at): Sort field
- `order` (optional, default=desc): Sort order (asc/desc)

**Response (200 OK):**
```json
{
  "executions": [
    {
      "execution_id": "exec_abc123",
      "type": "agent",
      "target_id": "mem_l1_summarizer",
      "status": "completed",
      "started_at": "2024-12-17T10:30:00Z",
      "completed_at": "2024-12-17T10:30:05Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 100,
    "total_pages": 2,
    "has_next": true,
    "has_prev": false,
    "next_page": 2,
    "prev_page": null
  }
}
```

**Example:**
```python
# List all completed executions
response = requests.get(
    "http://localhost:8000/api/v1/executions",
    params={
        "status": "completed",
        "page": 1,
        "page_size": 20
    }
)

executions = response.json()["executions"]
for exec in executions:
    print(f"{exec['execution_id']}: {exec['status']}")
```

### 4. Cancel Execution

**Endpoint:** `POST /api/v1/executions/{execution_id}/cancel`

Cancel a running execution.

**Response (200 OK):**
```json
{
  "message": "Execution cancelled successfully",
  "data": {
    "execution_id": "exec_abc123",
    "status": "cancelled",
    "cancelled_at": "2024-12-17T10:30:05Z"
  }
}
```

**Example:**
```python
response = requests.post(
    f"http://localhost:8000/api/v1/executions/{execution_id}/cancel"
)

if response.status_code == 200:
    print("Execution cancelled")
```

## Execution Status Values

| Status | Description |
|--------|-------------|
| `pending` | Execution queued but not started |
| `running` | Execution in progress |
| `completed` | Execution finished successfully |
| `failed` | Execution failed with error |
| `cancelled` | Execution was cancelled |

## Progress Tracking

For pipeline executions, progress information is available:

```json
{
  "progress": {
    "current_step": 2,
    "total_steps": 5,
    "percentage": 40.0,
    "current_step_name": "data_processing"
  }
}
```

## Error Handling

### Common Error Responses

**404 Not Found:**
```json
{
  "detail": "Execution 'exec_abc123' not found"
}
```

**400 Bad Request:**
```json
{
  "detail": "Cannot cancel execution with status 'completed'"
}
```

**500 Internal Server Error:**
```json
{
  "error": "Internal Server Error",
  "message": "Failed to start execution: ...",
  "path": "/api/v1/executions"
}
```

## Best Practices

### 1. Polling Strategy

Use exponential backoff for polling:

```python
import time

def wait_for_execution(execution_id, max_wait=300):
    """Wait for execution with exponential backoff."""
    wait_time = 0.5
    max_wait_time = 5.0
    elapsed = 0
    
    while elapsed < max_wait:
        response = requests.get(
            f"http://localhost:8000/api/v1/executions/{execution_id}"
        )
        status = response.json()
        
        if status["status"] in ["completed", "failed", "cancelled"]:
            return status
        
        time.sleep(wait_time)
        elapsed += wait_time
        wait_time = min(wait_time * 1.5, max_wait_time)
    
    raise TimeoutError("Execution did not complete in time")
```

### 2. Error Handling

Always handle errors gracefully:

```python
try:
    response = requests.post(
        "http://localhost:8000/api/v1/executions",
        json=payload
    )
    response.raise_for_status()
    execution_id = response.json()["execution_id"]
    
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 404:
        print("Agent/Pipeline not found")
    elif e.response.status_code == 400:
        print(f"Invalid request: {e.response.json()['detail']}")
    else:
        print(f"Error: {e}")
```

### 3. Timeout Handling

Set appropriate timeouts:

```python
# For agent execution
response = requests.post(
    url,
    json=payload,
    timeout=10  # Connection timeout
)

# Wait for completion with timeout
status = wait_for_execution(execution_id, max_wait=300)
```

### 4. Cleanup

Cancel executions that are no longer needed:

```python
# Cancel if taking too long
if elapsed > max_wait:
    requests.post(
        f"http://localhost:8000/api/v1/executions/{execution_id}/cancel"
    )
```

## Use Cases

### 1. Long-Running Agent Execution

```python
# Start execution
response = requests.post(
    "http://localhost:8000/api/v1/executions",
    json={
        "type": "agent",
        "target_id": "document_analyzer",
        "inputs": {
            "document": "Very long document..."
        }
    }
)

execution_id = response.json()["execution_id"]

# Do other work while waiting
do_other_work()

# Check if complete
status = requests.get(
    f"http://localhost:8000/api/v1/executions/{execution_id}"
).json()

if status["status"] == "completed":
    result = status["outputs"]
```

### 2. Batch Processing

```python
# Start multiple executions
execution_ids = []

for item in batch_items:
    response = requests.post(
        "http://localhost:8000/api/v1/executions",
        json={
            "type": "agent",
            "target_id": "processor",
            "inputs": item
        }
    )
    execution_ids.append(response.json()["execution_id"])

# Wait for all to complete
results = []
for exec_id in execution_ids:
    status = wait_for_execution(exec_id)
    if status["status"] == "completed":
        results.append(status["outputs"])
```

### 3. Pipeline with Progress Monitoring

```python
# Start pipeline
response = requests.post(
    "http://localhost:8000/api/v1/executions",
    json={
        "type": "pipeline",
        "target_id": "data_pipeline",
        "inputs": {"data": "..."}
    }
)

execution_id = response.json()["execution_id"]

# Monitor progress
while True:
    status = requests.get(
        f"http://localhost:8000/api/v1/executions/{execution_id}"
    ).json()
    
    if status["status"] in ["completed", "failed"]:
        break
    
    if "progress" in status:
        progress = status["progress"]
        print(f"Step {progress['current_step']}/{progress['total_steps']}: "
              f"{progress['current_step_name']} ({progress['percentage']:.1f}%)")
    
    time.sleep(1)
```

## Future Enhancements

### Webhook Callbacks

In future versions, webhook callbacks will be supported:

```python
response = requests.post(
    "http://localhost:8000/api/v1/executions",
    json={
        "type": "agent",
        "target_id": "processor",
        "inputs": {...},
        "callback_url": "https://myapp.com/webhook"
    }
)

# Server will POST to callback_url when complete:
# {
#   "event": "execution.completed",
#   "execution_id": "exec_abc123",
#   "status": "completed",
#   "outputs": {...}
# }
```

### WebSocket Progress Updates

Real-time progress updates via WebSocket:

```python
import websocket

ws = websocket.WebSocket()
ws.connect(f"ws://localhost:8000/api/v1/executions/{execution_id}/progress")

while True:
    message = ws.recv()
    progress = json.loads(message)
    print(f"Progress: {progress['percentage']:.1f}%")
    
    if progress["percentage"] >= 100:
        break

ws.close()
```

## Related Documentation

- [API Design Specification](./api-design-specification.md)
- [Agent Management API](./agent-management-api.md)
- [Pipeline Management API](./pipeline-management-api.md)
- [API Setup Guide](./api-setup-guide.md)

## References

- **Requirements:** Requirement 8.5 (Async Execution and Progress Query)
- **Design Document:** `.kiro/specs/project-production-readiness/design.md`
- **Implementation:** `src/api/routes/executions.py`, `src/api/execution_manager.py`
