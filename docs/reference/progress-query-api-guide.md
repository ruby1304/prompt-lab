# Progress Query API Guide

This guide explains how to use the Progress Query API to monitor execution progress in real-time.

## Overview

The Progress Query API provides two methods for monitoring execution progress:

1. **REST API Polling** - Query progress at intervals using HTTP GET requests
2. **WebSocket Streaming** - Receive real-time progress updates via persistent connection

## Table of Contents

- [REST API Endpoints](#rest-api-endpoints)
- [WebSocket Endpoint](#websocket-endpoint)
- [Use Cases](#use-cases)
- [Best Practices](#best-practices)
- [Examples](#examples)

## REST API Endpoints

### GET /executions/{execution_id}

Get complete execution status including progress information.

**Response:**
```json
{
  "execution_id": "exec_123456",
  "type": "pipeline",
  "target_id": "customer_service_flow",
  "status": "running",
  "progress": {
    "current_step": 2,
    "total_steps": 5,
    "percentage": 40.0,
    "current_step_name": "data_processing"
  },
  "started_at": "2024-12-17T10:30:00Z"
}
```

### GET /executions/{execution_id}/progress

Get detailed progress information only.

**Response (200 OK):**
```json
{
  "current_step": 2,
  "total_steps": 5,
  "percentage": 40.0,
  "current_step_name": "data_processing"
}
```

**Response (204 No Content):**
- Returned when execution has no progress data
- Common for pending or completed executions

**Response (404 Not Found):**
- Execution doesn't exist

## WebSocket Endpoint

### WS /executions/{execution_id}/progress/ws

Establish a WebSocket connection for real-time progress streaming.

**Connection:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/v1/executions/exec_123456/progress/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Message:', data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Connection closed');
};
```

**Python:**
```python
from websocket import create_connection
import json

ws = create_connection('ws://localhost:8000/api/v1/executions/exec_123456/progress/ws')

while True:
    message = ws.recv()
    data = json.loads(message)
    print(f"Message: {data}")
    
    if data['type'] in ['completed', 'failed', 'cancelled']:
        break

ws.close()
```

### Message Types

#### 1. Status Message
Initial status when connection is established.

```json
{
  "type": "status",
  "execution_id": "exec_123456",
  "status": "running",
  "progress": {
    "current_step": 1,
    "total_steps": 5,
    "percentage": 20.0
  },
  "timestamp": "2024-12-17T10:30:00Z"
}
```

#### 2. Started Message
Execution transitioned from pending to running.

```json
{
  "type": "started",
  "execution_id": "exec_123456",
  "status": "running",
  "timestamp": "2024-12-17T10:30:01Z"
}
```

#### 3. Progress Message
Progress update during execution.

```json
{
  "type": "progress",
  "execution_id": "exec_123456",
  "status": "running",
  "progress": {
    "current_step": 3,
    "total_steps": 5,
    "percentage": 60.0,
    "current_step_name": "aggregation"
  },
  "timestamp": "2024-12-17T10:30:05Z"
}
```

#### 4. Completed Message
Execution completed successfully.

```json
{
  "type": "completed",
  "execution_id": "exec_123456",
  "status": "completed",
  "outputs": {
    "result": "Success",
    "data": {...}
  },
  "timestamp": "2024-12-17T10:30:10Z"
}
```

#### 5. Failed Message
Execution failed with error.

```json
{
  "type": "failed",
  "execution_id": "exec_123456",
  "status": "failed",
  "error": {
    "type": "ValueError",
    "message": "Invalid input parameter",
    "details": {...}
  },
  "timestamp": "2024-12-17T10:30:08Z"
}
```

#### 6. Cancelled Message
Execution was cancelled.

```json
{
  "type": "cancelled",
  "execution_id": "exec_123456",
  "status": "cancelled",
  "timestamp": "2024-12-17T10:30:06Z"
}
```

#### 7. Error Message
WebSocket error occurred.

```json
{
  "type": "error",
  "message": "Execution not found",
  "timestamp": "2024-12-17T10:30:00Z"
}
```

## Use Cases

### 1. Progress Bar in UI

**REST API Polling:**
```javascript
async function updateProgressBar(executionId) {
  const interval = setInterval(async () => {
    const response = await fetch(`/api/v1/executions/${executionId}/progress`);
    
    if (response.status === 200) {
      const progress = await response.json();
      updateUI(progress.percentage, progress.current_step_name);
    } else if (response.status === 204) {
      // No progress data yet
      updateUI(0, 'Starting...');
    }
    
    // Check if completed
    const statusResponse = await fetch(`/api/v1/executions/${executionId}`);
    const status = await statusResponse.json();
    
    if (status.status !== 'running') {
      clearInterval(interval);
      handleCompletion(status);
    }
  }, 1000); // Poll every second
}
```

**WebSocket Streaming:**
```javascript
function streamProgress(executionId) {
  const ws = new WebSocket(`ws://localhost:8000/api/v1/executions/${executionId}/progress/ws`);
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'progress') {
      updateUI(data.progress.percentage, data.progress.current_step_name);
    } else if (data.type === 'completed') {
      handleCompletion(data);
    } else if (data.type === 'failed') {
      handleError(data.error);
    }
  };
}
```

### 2. Monitoring Multiple Executions

```python
import asyncio
import websockets
import json

async def monitor_execution(execution_id):
    uri = f"ws://localhost:8000/api/v1/executions/{execution_id}/progress/ws"
    
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            
            print(f"[{execution_id}] {data['type']}: {data.get('progress', {}).get('percentage', 0)}%")
            
            if data['type'] in ['completed', 'failed', 'cancelled']:
                break

async def monitor_multiple(execution_ids):
    tasks = [monitor_execution(exec_id) for exec_id in execution_ids]
    await asyncio.gather(*tasks)

# Monitor 3 executions concurrently
asyncio.run(monitor_multiple(['exec_1', 'exec_2', 'exec_3']))
```

### 3. Command-Line Progress Display

```python
import requests
import time
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

def monitor_with_rich(execution_id):
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        
        task = progress.add_task("Executing...", total=100)
        
        while not progress.finished:
            response = requests.get(f"/api/v1/executions/{execution_id}/progress")
            
            if response.status_code == 200:
                data = response.json()
                progress.update(
                    task,
                    completed=data['percentage'],
                    description=data.get('current_step_name', 'Processing')
                )
            
            # Check status
            status_response = requests.get(f"/api/v1/executions/{execution_id}")
            status = status_response.json()
            
            if status['status'] != 'running':
                progress.update(task, completed=100)
                break
            
            time.sleep(0.5)
```

## Best Practices

### When to Use REST API Polling

✅ **Use polling when:**
- Building simple integrations
- Progress updates are not time-critical
- WebSocket support is not available
- Monitoring infrequent executions

**Recommended polling interval:** 1-2 seconds

### When to Use WebSocket Streaming

✅ **Use WebSocket when:**
- Building real-time UI dashboards
- Monitoring long-running executions
- Need instant progress updates
- Monitoring multiple executions simultaneously
- Minimizing server load

### Error Handling

**REST API:**
```python
def get_progress_safe(execution_id):
    try:
        response = requests.get(f"/api/v1/executions/{execution_id}/progress")
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 204:
            return None  # No progress data
        elif response.status_code == 404:
            raise ValueError(f"Execution {execution_id} not found")
        else:
            raise Exception(f"Unexpected status: {response.status_code}")
    except requests.RequestException as e:
        print(f"Network error: {e}")
        return None
```

**WebSocket:**
```python
from websocket import create_connection, WebSocketException

def stream_progress_safe(execution_id):
    try:
        ws = create_connection(f"ws://localhost:8000/api/v1/executions/{execution_id}/progress/ws")
        
        while True:
            try:
                message = ws.recv()
                data = json.loads(message)
                
                if data['type'] == 'error':
                    print(f"Error: {data['message']}")
                    break
                
                # Handle message...
                
                if data['type'] in ['completed', 'failed', 'cancelled']:
                    break
                    
            except WebSocketException as e:
                print(f"WebSocket error: {e}")
                break
        
        ws.close()
        
    except Exception as e:
        print(f"Connection error: {e}")
```

### Connection Management

**WebSocket Reconnection:**
```python
import time

def stream_with_reconnect(execution_id, max_retries=3):
    retries = 0
    
    while retries < max_retries:
        try:
            stream_progress_safe(execution_id)
            break  # Success
        except Exception as e:
            retries += 1
            if retries < max_retries:
                print(f"Reconnecting... (attempt {retries}/{max_retries})")
                time.sleep(2 ** retries)  # Exponential backoff
            else:
                print(f"Failed after {max_retries} attempts")
                raise
```

## Performance Considerations

### REST API Polling

**Pros:**
- Simple to implement
- Works with any HTTP client
- No persistent connections

**Cons:**
- Higher latency (polling interval)
- More server requests
- Potential for missed updates

**Optimization:**
- Use appropriate polling intervals (1-2s recommended)
- Implement exponential backoff for errors
- Stop polling when execution completes

### WebSocket Streaming

**Pros:**
- Real-time updates (500ms polling internally)
- Lower server load
- Instant notifications
- Efficient for multiple executions

**Cons:**
- Requires WebSocket support
- Persistent connection overhead
- More complex error handling

**Optimization:**
- Reuse connections when possible
- Implement reconnection logic
- Close connections promptly after completion

## Examples

See `examples/api_progress_query_demo.py` for complete working examples including:
- Basic progress querying
- WebSocket streaming
- Concurrent monitoring
- Performance comparison

## Related Documentation

- [Async Execution API Guide](./async-execution-api-guide.md)
- [API Design Specification](./api-design-specification.md)
- [Progress Tracking Guide](./progress-tracking-guide.md)

## Troubleshooting

### WebSocket Connection Fails

**Problem:** Cannot establish WebSocket connection

**Solutions:**
1. Check if API server is running
2. Verify WebSocket URL format: `ws://` not `http://`
3. Check firewall/proxy settings
4. Ensure uvicorn is running with WebSocket support

### No Progress Data (204 Response)

**Problem:** GET /progress returns 204 No Content

**Explanation:** This is normal for:
- Pending executions (not started yet)
- Completed executions (progress cleared)
- Executions without progress tracking

**Solution:** Check execution status first

### Progress Not Updating

**Problem:** Progress percentage stays at 0%

**Possible causes:**
1. Execution hasn't started yet
2. Pipeline doesn't report progress
3. Execution is stuck

**Solution:**
```python
# Check execution status
status = requests.get(f"/api/v1/executions/{execution_id}").json()
print(f"Status: {status['status']}")
print(f"Started: {status.get('started_at')}")
```

## API Reference

### Progress Info Model

```python
{
  "current_step": int,      # Current step number (0-indexed)
  "total_steps": int,       # Total number of steps
  "percentage": float,      # Completion percentage (0-100)
  "current_step_name": str  # Optional step name
}
```

### Execution Status Values

- `pending` - Queued, not started
- `running` - Currently executing
- `completed` - Finished successfully
- `failed` - Failed with error
- `cancelled` - Cancelled by user

## Support

For issues or questions:
1. Check the [API documentation](./api-design-specification.md)
2. Review [examples](../../examples/api_progress_query_demo.py)
3. Check server logs for errors
4. Verify API server is running and accessible
