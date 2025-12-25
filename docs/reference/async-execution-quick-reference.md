# Async Execution API - Quick Reference

**Version:** 1.0.0  
**Base URL:** `http://localhost:8000/api/v1`

## Quick Start

```python
import requests
import time

# 1. Start execution
response = requests.post(
    "http://localhost:8000/api/v1/executions",
    json={
        "type": "agent",
        "target_id": "mem_l1_summarizer",
        "inputs": {"text": "Input text"}
    }
)
execution_id = response.json()["execution_id"]

# 2. Poll for completion
while True:
    status = requests.get(
        f"http://localhost:8000/api/v1/executions/{execution_id}"
    ).json()
    
    if status["status"] in ["completed", "failed", "cancelled"]:
        break
    
    time.sleep(1)

# 3. Get results
if status["status"] == "completed":
    outputs = status["outputs"]
```

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/executions` | Start async execution |
| GET | `/executions/{id}` | Get execution status |
| GET | `/executions` | List executions |
| POST | `/executions/{id}/cancel` | Cancel execution |

## Request Examples

### Start Agent Execution
```bash
curl -X POST http://localhost:8000/api/v1/executions \
  -H "Content-Type: application/json" \
  -d '{
    "type": "agent",
    "target_id": "mem_l1_summarizer",
    "inputs": {"text": "Test input"},
    "config": {"flow_id": "default"}
  }'
```

### Start Pipeline Execution
```bash
curl -X POST http://localhost:8000/api/v1/executions \
  -H "Content-Type: application/json" \
  -d '{
    "type": "pipeline",
    "target_id": "customer_service_flow",
    "inputs": {"customer_query": "How do I reset my password?"},
    "config": {"max_workers": 4}
  }'
```

### Get Status
```bash
curl http://localhost:8000/api/v1/executions/exec_abc123
```

### List Executions
```bash
# All executions
curl http://localhost:8000/api/v1/executions

# Filter by status
curl http://localhost:8000/api/v1/executions?status=completed

# Filter by type
curl http://localhost:8000/api/v1/executions?type=pipeline

# Pagination
curl http://localhost:8000/api/v1/executions?page=1&page_size=20
```

### Cancel Execution
```bash
curl -X POST http://localhost:8000/api/v1/executions/exec_abc123/cancel
```

## Status Values

| Status | Description |
|--------|-------------|
| `pending` | Queued, not started |
| `running` | In progress |
| `completed` | Finished successfully |
| `failed` | Failed with error |
| `cancelled` | Cancelled by user |

## Response Formats

### Start Execution (202)
```json
{
  "execution_id": "exec_abc123",
  "status": "pending",
  "message": "Agent execution started",
  "status_url": "/api/v1/executions/exec_abc123",
  "created_at": "2024-12-17T10:30:00Z"
}
```

### Get Status - Running (200)
```json
{
  "execution_id": "exec_abc123",
  "type": "pipeline",
  "target_id": "customer_service_flow",
  "status": "running",
  "progress": {
    "current_step": 2,
    "total_steps": 5,
    "percentage": 40.0,
    "current_step_name": "processing"
  },
  "started_at": "2024-12-17T10:30:00Z"
}
```

### Get Status - Completed (200)
```json
{
  "execution_id": "exec_abc123",
  "type": "agent",
  "target_id": "mem_l1_summarizer",
  "status": "completed",
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

### Get Status - Failed (200)
```json
{
  "execution_id": "exec_abc123",
  "status": "failed",
  "error": {
    "type": "ExecutionError",
    "message": "Agent execution failed",
    "details": {"agent_id": "mem_l1_summarizer"}
  },
  "started_at": "2024-12-17T10:30:00Z",
  "failed_at": "2024-12-17T10:30:05Z"
}
```

### List Executions (200)
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
    "has_prev": false
  }
}
```

## Python Helper Functions

```python
import requests
import time

BASE_URL = "http://localhost:8000/api/v1"

def start_execution(type, target_id, inputs, config=None):
    """Start async execution."""
    response = requests.post(
        f"{BASE_URL}/executions",
        json={
            "type": type,
            "target_id": target_id,
            "inputs": inputs,
            "config": config or {}
        }
    )
    response.raise_for_status()
    return response.json()["execution_id"]

def get_status(execution_id):
    """Get execution status."""
    response = requests.get(f"{BASE_URL}/executions/{execution_id}")
    response.raise_for_status()
    return response.json()

def wait_for_completion(execution_id, poll_interval=1.0, timeout=300):
    """Wait for execution to complete."""
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        status = get_status(execution_id)
        
        if status["status"] in ["completed", "failed", "cancelled"]:
            return status
        
        time.sleep(poll_interval)
    
    raise TimeoutError("Execution did not complete in time")

def cancel_execution(execution_id):
    """Cancel execution."""
    response = requests.post(f"{BASE_URL}/executions/{execution_id}/cancel")
    response.raise_for_status()
    return response.json()
```

## Common Patterns

### Wait with Progress
```python
execution_id = start_execution("pipeline", "my_pipeline", inputs)

while True:
    status = get_status(execution_id)
    
    if status["status"] in ["completed", "failed", "cancelled"]:
        break
    
    if "progress" in status:
        p = status["progress"]
        print(f"{p['percentage']:.1f}% - {p['current_step_name']}")
    
    time.sleep(1)
```

### Batch Processing
```python
# Start multiple executions
execution_ids = []
for item in batch_items:
    exec_id = start_execution("agent", "processor", item)
    execution_ids.append(exec_id)

# Wait for all
results = []
for exec_id in execution_ids:
    status = wait_for_completion(exec_id)
    if status["status"] == "completed":
        results.append(status["outputs"])
```

### Error Handling
```python
try:
    execution_id = start_execution("agent", "my_agent", inputs)
    status = wait_for_completion(execution_id, timeout=60)
    
    if status["status"] == "completed":
        return status["outputs"]
    elif status["status"] == "failed":
        error = status["error"]
        print(f"Error: {error['message']}")
        
except TimeoutError:
    print("Execution timed out, cancelling...")
    cancel_execution(execution_id)
except requests.exceptions.HTTPError as e:
    print(f"API error: {e}")
```

## Error Codes

| Code | Description |
|------|-------------|
| 202 | Execution started |
| 200 | Success |
| 400 | Bad request (invalid input) |
| 404 | Execution not found |
| 500 | Server error |

## See Also

- [Async Execution API Guide](./async-execution-api-guide.md) - Complete documentation
- [API Design Specification](./api-design-specification.md) - Full API spec
- [API Setup Guide](./api-setup-guide.md) - Setup instructions
