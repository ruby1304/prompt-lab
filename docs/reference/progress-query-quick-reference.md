# Progress Query API - Quick Reference

Quick reference for monitoring execution progress using REST API and WebSocket.

## REST API Endpoints

### Get Execution Status (with Progress)
```bash
GET /api/v1/executions/{execution_id}
```

**Response:**
```json
{
  "execution_id": "exec_123456",
  "status": "running",
  "progress": {
    "current_step": 2,
    "total_steps": 5,
    "percentage": 40.0,
    "current_step_name": "processing"
  }
}
```

### Get Progress Only
```bash
GET /api/v1/executions/{execution_id}/progress
```

**Response (200):**
```json
{
  "current_step": 2,
  "total_steps": 5,
  "percentage": 40.0,
  "current_step_name": "processing"
}
```

**Response (204):** No progress data available

## WebSocket Endpoint

### Connect
```bash
WS /api/v1/executions/{execution_id}/progress/ws
```

### Message Types

| Type | Description | When Sent |
|------|-------------|-----------|
| `status` | Initial status | On connection |
| `started` | Execution started | Status → running |
| `progress` | Progress update | Progress changed |
| `completed` | Success | Execution done |
| `failed` | Error occurred | Execution failed |
| `cancelled` | User cancelled | Execution cancelled |
| `error` | WebSocket error | Connection issue |

## Quick Examples

### Python - REST Polling
```python
import requests
import time

execution_id = "exec_123456"

while True:
    response = requests.get(f"/api/v1/executions/{execution_id}/progress")
    
    if response.status_code == 200:
        progress = response.json()
        print(f"Progress: {progress['percentage']:.1f}%")
    
    # Check if done
    status = requests.get(f"/api/v1/executions/{execution_id}").json()
    if status['status'] != 'running':
        break
    
    time.sleep(1)
```

### Python - WebSocket
```python
from websocket import create_connection
import json

ws = create_connection(f"ws://localhost:8000/api/v1/executions/{execution_id}/progress/ws")

while True:
    message = ws.recv()
    data = json.loads(message)
    
    if data['type'] == 'progress':
        print(f"Progress: {data['progress']['percentage']:.1f}%")
    elif data['type'] in ['completed', 'failed', 'cancelled']:
        print(f"Done: {data['type']}")
        break

ws.close()
```

### JavaScript - WebSocket
```javascript
const ws = new WebSocket(`ws://localhost:8000/api/v1/executions/${executionId}/progress/ws`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'progress') {
    updateProgressBar(data.progress.percentage);
  } else if (data.type === 'completed') {
    showSuccess(data.outputs);
  } else if (data.type === 'failed') {
    showError(data.error);
  }
};
```

### cURL - REST
```bash
# Get progress
curl http://localhost:8000/api/v1/executions/exec_123456/progress

# Get full status
curl http://localhost:8000/api/v1/executions/exec_123456
```

## Status Values

| Status | Description |
|--------|-------------|
| `pending` | Queued, not started |
| `running` | Currently executing |
| `completed` | Finished successfully |
| `failed` | Failed with error |
| `cancelled` | Cancelled by user |

## Progress Fields

| Field | Type | Description |
|-------|------|-------------|
| `current_step` | int | Current step (0-indexed) |
| `total_steps` | int | Total number of steps |
| `percentage` | float | Completion % (0-100) |
| `current_step_name` | string | Optional step name |

## When to Use What

### Use REST Polling When:
- ✅ Simple integration needed
- ✅ Updates not time-critical
- ✅ WebSocket not available
- ✅ Infrequent monitoring

**Recommended interval:** 1-2 seconds

### Use WebSocket When:
- ✅ Real-time UI needed
- ✅ Long-running executions
- ✅ Multiple executions
- ✅ Instant updates required
- ✅ Minimize server load

## Common Patterns

### Progress Bar
```python
from rich.progress import Progress

with Progress() as progress:
    task = progress.add_task("Executing...", total=100)
    
    ws = create_connection(f"ws://localhost:8000/api/v1/executions/{exec_id}/progress/ws")
    
    while True:
        data = json.loads(ws.recv())
        
        if data['type'] == 'progress':
            progress.update(task, completed=data['progress']['percentage'])
        elif data['type'] in ['completed', 'failed']:
            break
    
    ws.close()
```

### Monitor Multiple
```python
import asyncio
import websockets

async def monitor(exec_id):
    uri = f"ws://localhost:8000/api/v1/executions/{exec_id}/progress/ws"
    async with websockets.connect(uri) as ws:
        while True:
            data = json.loads(await ws.recv())
            print(f"[{exec_id}] {data['type']}")
            if data['type'] in ['completed', 'failed', 'cancelled']:
                break

# Monitor 3 executions
await asyncio.gather(
    monitor('exec_1'),
    monitor('exec_2'),
    monitor('exec_3')
)
```

### Error Handling
```python
def get_progress_safe(exec_id):
    try:
        response = requests.get(f"/api/v1/executions/{exec_id}/progress")
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 204:
            return None  # No progress yet
        elif response.status_code == 404:
            raise ValueError("Execution not found")
    except requests.RequestException as e:
        print(f"Network error: {e}")
        return None
```

## Troubleshooting

### 204 No Content
**Cause:** No progress data available
**Solution:** Normal for pending/completed executions

### WebSocket Closes Immediately
**Cause:** Execution already completed
**Solution:** Check execution status first

### No Progress Updates
**Cause:** Pipeline doesn't report progress
**Solution:** Verify pipeline has progress tracking

## See Also

- [Full Progress Query Guide](./progress-query-api-guide.md)
- [Async Execution API](./async-execution-api-guide.md)
- [Examples](../../examples/api_progress_query_demo.py)
