# Prompt Lab API Design Specification

**Version:** 1.0.0  
**Status:** Draft  
**Last Updated:** 2024-12-17

## Overview

This document defines the complete RESTful API specification for the Prompt Lab platform. The API provides programmatic access to all core functionality including agent management, pipeline execution, configuration management, and asynchronous task execution.

## Design Principles

1. **RESTful Architecture**: Follow REST principles with resource-based URLs
2. **Consistent Naming**: Use kebab-case for URLs, snake_case for JSON fields
3. **Versioning**: API versioned via URL path (`/api/v1/`)
4. **Standard HTTP Methods**: GET (read), POST (create), PUT (update), DELETE (remove)
5. **Standard Status Codes**: Use appropriate HTTP status codes
6. **Pagination**: Support pagination for list endpoints
7. **Filtering**: Support filtering and sorting for list endpoints
8. **Error Handling**: Consistent error response format
9. **Documentation**: Auto-generated OpenAPI/Swagger documentation

## Base URL

```
Development: http://localhost:8000/api/v1
Production: https://api.promptlab.example.com/api/v1
```

## Authentication

**Phase 1 (Current)**: No authentication (development only)  
**Phase 2 (Future)**: API key authentication via `X-API-Key` header  
**Phase 3 (Future)**: OAuth 2.0 / JWT tokens

## Common Headers

### Request Headers
```
Content-Type: application/json
Accept: application/json
X-API-Key: <api-key>  (future)
```

### Response Headers
```
Content-Type: application/json
X-Process-Time: <seconds>
X-Request-ID: <uuid>
```


## HTTP Status Codes

### Success Codes
- `200 OK`: Request successful, response body contains data
- `201 Created`: Resource created successfully
- `202 Accepted`: Request accepted for async processing
- `204 No Content`: Request successful, no response body

### Client Error Codes
- `400 Bad Request`: Invalid request format or parameters
- `401 Unauthorized`: Authentication required or failed
- `403 Forbidden`: Authenticated but not authorized
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict (e.g., duplicate ID)
- `422 Unprocessable Entity`: Validation error

### Server Error Codes
- `500 Internal Server Error`: Unexpected server error
- `502 Bad Gateway`: Upstream service error
- `503 Service Unavailable`: Service temporarily unavailable
- `504 Gateway Timeout`: Upstream service timeout

## Error Response Format

All error responses follow this consistent format:

```json
{
  "error": "ErrorType",
  "message": "Human-readable error description",
  "details": {
    "field": "error details",
    "validation_errors": []
  },
  "path": "/api/v1/resource",
  "timestamp": "2024-12-17T10:30:00Z",
  "request_id": "uuid"
}
```

### Error Examples

**Validation Error (422)**
```json
{
  "error": "ValidationError",
  "message": "Request validation failed",
  "details": {
    "validation_errors": [
      {
        "field": "agent_id",
        "message": "Agent ID is required"
      },
      {
        "field": "flow_id",
        "message": "Flow ID must be a valid identifier"
      }
    ]
  },
  "path": "/api/v1/agents",
  "timestamp": "2024-12-17T10:30:00Z"
}
```

**Not Found Error (404)**
```json
{
  "error": "NotFound",
  "message": "Agent 'unknown_agent' not found",
  "path": "/api/v1/agents/unknown_agent",
  "timestamp": "2024-12-17T10:30:00Z"
}
```


## API Endpoints

### System Endpoints

#### Health Check
```
GET /health
```

Check API health status.

**Response (200)**
```json
{
  "status": "healthy",
  "service": "prompt-lab-api",
  "version": "1.0.0",
  "timestamp": "2024-12-17T10:30:00Z"
}
```

#### API Information
```
GET /
GET /api/v1
```

Get API version and available endpoints.

**Response (200)**
```json
{
  "message": "Prompt Lab API v1",
  "version": "1.0.0",
  "documentation": "/docs",
  "endpoints": {
    "agents": "/api/v1/agents",
    "pipelines": "/api/v1/pipelines",
    "executions": "/api/v1/executions",
    "config": "/api/v1/config"
  }
}
```

---

### Agent Management Endpoints

#### List Agents
```
GET /api/v1/agents
```

List all registered agents with optional filtering.

**Query Parameters**
- `category` (string, optional): Filter by category (production, example, test, system)
- `environment` (string, optional): Filter by environment (production, staging, demo, test)
- `tags` (string, optional): Comma-separated tags to filter by
- `status` (string, optional): Filter by status (active, deprecated, experimental, archived)
- `page` (integer, optional, default=1): Page number
- `page_size` (integer, optional, default=50): Items per page
- `sort` (string, optional, default=id): Sort field (id, name, created_at, updated_at)
- `order` (string, optional, default=asc): Sort order (asc, desc)

**Response (200)**
```json
{
  "agents": [
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
      "description": "Summarizes L1 memory entries",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-12-01T00:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 10,
    "total_pages": 1
  }
}
```


#### Get Agent Details
```
GET /api/v1/agents/{agent_id}
```

Get detailed information about a specific agent.

**Path Parameters**
- `agent_id` (string, required): Agent identifier

**Response (200)**
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
  "description": "Summarizes L1 memory entries",
  "business_goal": "Improve memory retrieval efficiency",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-12-01T00:00:00Z",
  "maintainer": "john@example.com",
  "documentation_url": "https://docs.example.com/agents/mem_l1",
  "dependencies": ["tokenizer", "embeddings"],
  "performance_metrics": {
    "avg_latency_ms": 150,
    "success_rate": 0.98
  }
}
```

**Response (404)** - Agent not found

#### Register Agent
```
POST /api/v1/agents
```

Register a new agent in the registry.

**Request Body**
```json
{
  "id": "new_agent",
  "name": "New Agent",
  "category": "production",
  "environment": "staging",
  "owner": "team-name",
  "version": "1.0.0",
  "location": "agents/new_agent",
  "description": "Agent description",
  "tags": ["tag1", "tag2"]
}
```

**Response (201)**
```json
{
  "id": "new_agent",
  "name": "New Agent",
  "message": "Agent registered successfully",
  "created_at": "2024-12-17T10:30:00Z"
}
```

**Response (409)** - Agent ID already exists

#### Update Agent
```
PUT /api/v1/agents/{agent_id}
```

Update agent metadata.

**Path Parameters**
- `agent_id` (string, required): Agent identifier

**Request Body** (partial update supported)
```json
{
  "name": "Updated Name",
  "version": "1.3.0",
  "description": "Updated description",
  "tags": ["new-tag"]
}
```

**Response (200)**
```json
{
  "id": "mem_l1_summarizer",
  "message": "Agent updated successfully",
  "updated_at": "2024-12-17T10:30:00Z"
}
```

#### Delete Agent
```
DELETE /api/v1/agents/{agent_id}
```

Remove an agent from the registry (soft delete - marks as archived).

**Path Parameters**
- `agent_id` (string, required): Agent identifier

**Response (204)** - No content


#### List Agent Flows
```
GET /api/v1/agents/{agent_id}/flows
```

List all flows for a specific agent.

**Path Parameters**
- `agent_id` (string, required): Agent identifier

**Response (200)**
```json
{
  "agent_id": "mem_l1_summarizer",
  "flows": [
    {
      "id": "default",
      "name": "Default Flow",
      "version": "1.0",
      "description": "Standard summarization flow",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### Execute Agent Flow
```
POST /api/v1/agents/{agent_id}/flows/{flow_id}/execute
```

Execute a specific agent flow (synchronous).

**Path Parameters**
- `agent_id` (string, required): Agent identifier
- `flow_id` (string, required): Flow identifier

**Request Body**
```json
{
  "inputs": {
    "text": "Input text to process",
    "param1": "value1"
  },
  "model_override": "doubao-pro-32k",
  "timeout": 60
}
```

**Response (200)**
```json
{
  "execution_id": "exec_123456",
  "agent_id": "mem_l1_summarizer",
  "flow_id": "default",
  "status": "completed",
  "output": {
    "summary": "Generated summary",
    "key_points": ["point1", "point2"]
  },
  "metadata": {
    "execution_time_ms": 1500,
    "model_used": "doubao-pro-32k",
    "tokens_used": 250
  },
  "started_at": "2024-12-17T10:30:00Z",
  "completed_at": "2024-12-17T10:30:01.5Z"
}
```

**Response (400)** - Invalid inputs
**Response (404)** - Agent or flow not found
**Response (500)** - Execution error

---

### Pipeline Management Endpoints

#### List Pipelines
```
GET /api/v1/pipelines
```

List all configured pipelines.

**Query Parameters**
- `category` (string, optional): Filter by category
- `status` (string, optional): Filter by status (active, draft, archived)
- `page` (integer, optional, default=1): Page number
- `page_size` (integer, optional, default=50): Items per page

**Response (200)**
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
    "page_size": 50,
    "total_items": 5,
    "total_pages": 1
  }
}
```


#### Get Pipeline Details
```
GET /api/v1/pipelines/{pipeline_id}
```

Get detailed pipeline configuration.

**Path Parameters**
- `pipeline_id` (string, required): Pipeline identifier

**Response (200)**
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
    },
    {
      "id": "process",
      "type": "agent_flow",
      "agent": "response_generator",
      "flow": "default",
      "input_mapping": {
        "intent": "intent",
        "query": "customer_query"
      },
      "output_key": "response"
    }
  ],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-12-01T00:00:00Z"
}
```

#### Create Pipeline
```
POST /api/v1/pipelines
```

Create a new pipeline configuration.

**Request Body**
```json
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

**Response (201)**
```json
{
  "id": "new_pipeline",
  "message": "Pipeline created successfully",
  "created_at": "2024-12-17T10:30:00Z"
}
```

#### Update Pipeline
```
PUT /api/v1/pipelines/{pipeline_id}
```

Update pipeline configuration.

**Path Parameters**
- `pipeline_id` (string, required): Pipeline identifier

**Request Body** (partial update supported)
```json
{
  "name": "Updated Pipeline Name",
  "description": "Updated description",
  "steps": [...]
}
```

**Response (200)**
```json
{
  "id": "customer_service_flow",
  "message": "Pipeline updated successfully",
  "updated_at": "2024-12-17T10:30:00Z"
}
```

#### Delete Pipeline
```
DELETE /api/v1/pipelines/{pipeline_id}
```

Delete a pipeline configuration.

**Path Parameters**
- `pipeline_id` (string, required): Pipeline identifier

**Response (204)** - No content


#### Execute Pipeline (Synchronous)
```
POST /api/v1/pipelines/{pipeline_id}/execute
```

Execute a pipeline synchronously (blocks until completion).

**Path Parameters**
- `pipeline_id` (string, required): Pipeline identifier

**Request Body**
```json
{
  "inputs": {
    "customer_query": "How do I reset my password?"
  },
  "config": {
    "max_workers": 4,
    "timeout": 300
  }
}
```

**Response (200)**
```json
{
  "execution_id": "exec_789012",
  "pipeline_id": "customer_service_flow",
  "status": "completed",
  "outputs": {
    "response": "To reset your password, please..."
  },
  "step_results": [
    {
      "step_id": "classify",
      "status": "completed",
      "output": {"intent": "password_reset"},
      "execution_time_ms": 500
    },
    {
      "step_id": "process",
      "status": "completed",
      "output": {"response": "To reset your password..."},
      "execution_time_ms": 1200
    }
  ],
  "metadata": {
    "total_execution_time_ms": 1700,
    "steps_executed": 2,
    "steps_failed": 0
  },
  "started_at": "2024-12-17T10:30:00Z",
  "completed_at": "2024-12-17T10:30:01.7Z"
}
```

**Response (400)** - Invalid inputs
**Response (404)** - Pipeline not found
**Response (500)** - Execution error

---

### Asynchronous Execution Endpoints

#### Start Async Execution
```
POST /api/v1/executions
```

Start an asynchronous execution (agent or pipeline).

**Request Body**
```json
{
  "type": "pipeline",
  "target_id": "customer_service_flow",
  "inputs": {
    "customer_query": "How do I reset my password?"
  },
  "config": {
    "max_workers": 4,
    "timeout": 300
  },
  "callback_url": "https://example.com/webhook"
}
```

**Response (202)**
```json
{
  "execution_id": "exec_345678",
  "status": "pending",
  "message": "Execution started",
  "status_url": "/api/v1/executions/exec_345678",
  "created_at": "2024-12-17T10:30:00Z"
}
```

#### Get Execution Status
```
GET /api/v1/executions/{execution_id}
```

Get the status and results of an execution.

**Path Parameters**
- `execution_id` (string, required): Execution identifier

**Response (200)** - Completed
```json
{
  "execution_id": "exec_345678",
  "type": "pipeline",
  "target_id": "customer_service_flow",
  "status": "completed",
  "progress": {
    "current_step": 2,
    "total_steps": 2,
    "percentage": 100
  },
  "outputs": {
    "response": "To reset your password..."
  },
  "metadata": {
    "total_execution_time_ms": 1700
  },
  "started_at": "2024-12-17T10:30:00Z",
  "completed_at": "2024-12-17T10:30:01.7Z"
}
```

**Response (200)** - In Progress
```json
{
  "execution_id": "exec_345678",
  "status": "running",
  "progress": {
    "current_step": 1,
    "total_steps": 2,
    "percentage": 50,
    "current_step_name": "classify"
  },
  "started_at": "2024-12-17T10:30:00Z"
}
```

**Response (200)** - Failed
```json
{
  "execution_id": "exec_345678",
  "status": "failed",
  "error": {
    "type": "ExecutionError",
    "message": "Step 'classify' failed",
    "details": {
      "step_id": "classify",
      "error_message": "Agent timeout"
    }
  },
  "started_at": "2024-12-17T10:30:00Z",
  "failed_at": "2024-12-17T10:30:05Z"
}
```


#### List Executions
```
GET /api/v1/executions
```

List all executions with filtering.

**Query Parameters**
- `status` (string, optional): Filter by status (pending, running, completed, failed)
- `type` (string, optional): Filter by type (agent, pipeline)
- `target_id` (string, optional): Filter by target agent/pipeline ID
- `page` (integer, optional, default=1): Page number
- `page_size` (integer, optional, default=50): Items per page
- `sort` (string, optional, default=created_at): Sort field
- `order` (string, optional, default=desc): Sort order

**Response (200)**
```json
{
  "executions": [
    {
      "execution_id": "exec_345678",
      "type": "pipeline",
      "target_id": "customer_service_flow",
      "status": "completed",
      "started_at": "2024-12-17T10:30:00Z",
      "completed_at": "2024-12-17T10:30:01.7Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 100,
    "total_pages": 2
  }
}
```

#### Cancel Execution
```
POST /api/v1/executions/{execution_id}/cancel
```

Cancel a running execution.

**Path Parameters**
- `execution_id` (string, required): Execution identifier

**Response (200)**
```json
{
  "execution_id": "exec_345678",
  "status": "cancelled",
  "message": "Execution cancelled successfully",
  "cancelled_at": "2024-12-17T10:30:05Z"
}
```

#### Get Execution Progress (WebSocket)
```
WS /api/v1/executions/{execution_id}/progress
```

Real-time progress updates via WebSocket.

**WebSocket Messages**
```json
{
  "type": "progress",
  "execution_id": "exec_345678",
  "progress": {
    "current_step": 1,
    "total_steps": 2,
    "percentage": 50,
    "current_step_name": "classify"
  },
  "timestamp": "2024-12-17T10:30:00.5Z"
}
```

---

### Configuration Management Endpoints

#### Get Agent Configuration
```
GET /api/v1/config/agents/{agent_id}
```

Read agent configuration file (agent.yaml).

**Path Parameters**
- `agent_id` (string, required): Agent identifier

**Response (200)**
```json
{
  "agent_id": "mem_l1_summarizer",
  "config": {
    "name": "一级记忆总结",
    "version": "1.2.0",
    "flows": {
      "default": {
        "system_prompt": "...",
        "user_input": "...",
        "model": "doubao-pro-32k"
      }
    }
  },
  "file_path": "agents/mem_l1_summarizer/agent.yaml",
  "last_modified": "2024-12-01T00:00:00Z"
}
```

#### Update Agent Configuration
```
PUT /api/v1/config/agents/{agent_id}
```

Update agent configuration file.

**Path Parameters**
- `agent_id` (string, required): Agent identifier

**Request Body**
```json
{
  "config": {
    "name": "Updated Name",
    "flows": {
      "default": {
        "system_prompt": "Updated prompt"
      }
    }
  }
}
```

**Response (200)**
```json
{
  "agent_id": "mem_l1_summarizer",
  "message": "Configuration updated successfully",
  "updated_at": "2024-12-17T10:30:00Z"
}
```


#### Get Pipeline Configuration
```
GET /api/v1/config/pipelines/{pipeline_id}
```

Read pipeline configuration file (pipeline.yaml).

**Path Parameters**
- `pipeline_id` (string, required): Pipeline identifier

**Response (200)**
```json
{
  "pipeline_id": "customer_service_flow",
  "config": {
    "name": "Customer Service Pipeline",
    "inputs": [...],
    "outputs": [...],
    "steps": [...]
  },
  "file_path": "pipelines/customer_service_flow.yaml",
  "last_modified": "2024-12-01T00:00:00Z"
}
```

#### Update Pipeline Configuration
```
PUT /api/v1/config/pipelines/{pipeline_id}
```

Update pipeline configuration file.

**Path Parameters**
- `pipeline_id` (string, required): Pipeline identifier

**Request Body**
```json
{
  "config": {
    "name": "Updated Pipeline Name",
    "steps": [...]
  }
}
```

**Response (200)**
```json
{
  "pipeline_id": "customer_service_flow",
  "message": "Configuration updated successfully",
  "updated_at": "2024-12-17T10:30:00Z"
}
```

#### Validate Configuration
```
POST /api/v1/config/validate
```

Validate a configuration without saving.

**Request Body**
```json
{
  "type": "pipeline",
  "config": {
    "id": "test_pipeline",
    "steps": [...]
  }
}
```

**Response (200)** - Valid
```json
{
  "valid": true,
  "message": "Configuration is valid"
}
```

**Response (422)** - Invalid
```json
{
  "valid": false,
  "errors": [
    {
      "field": "steps[0].agent",
      "message": "Agent 'unknown_agent' not found"
    }
  ]
}
```

---

### Batch Processing Endpoints

#### Execute Batch Tests
```
POST /api/v1/batch/execute
```

Execute a batch of test cases.

**Request Body**
```json
{
  "target_type": "agent",
  "target_id": "mem_l1_summarizer",
  "flow_id": "default",
  "test_cases": [
    {
      "id": "test_1",
      "inputs": {"text": "Test input 1"}
    },
    {
      "id": "test_2",
      "inputs": {"text": "Test input 2"}
    }
  ],
  "config": {
    "concurrent": true,
    "max_workers": 4
  }
}
```

**Response (202)**
```json
{
  "batch_id": "batch_123456",
  "status": "pending",
  "total_tests": 2,
  "status_url": "/api/v1/batch/batch_123456",
  "created_at": "2024-12-17T10:30:00Z"
}
```

#### Get Batch Status
```
GET /api/v1/batch/{batch_id}
```

Get batch execution status and results.

**Path Parameters**
- `batch_id` (string, required): Batch identifier

**Response (200)**
```json
{
  "batch_id": "batch_123456",
  "status": "completed",
  "progress": {
    "completed": 2,
    "total": 2,
    "percentage": 100
  },
  "results": [
    {
      "test_id": "test_1",
      "status": "completed",
      "output": {"summary": "..."}
    },
    {
      "test_id": "test_2",
      "status": "completed",
      "output": {"summary": "..."}
    }
  ],
  "started_at": "2024-12-17T10:30:00Z",
  "completed_at": "2024-12-17T10:30:05Z"
}
```


---

## Request/Response Models

### Agent Models

#### AgentMetadata
```json
{
  "id": "string",
  "name": "string",
  "category": "production|example|test|system",
  "environment": "production|staging|demo|test",
  "owner": "string",
  "version": "string",
  "status": "active|deprecated|experimental|archived",
  "tags": ["string"],
  "deprecated": "boolean",
  "location": "string",
  "description": "string",
  "business_goal": "string",
  "created_at": "datetime",
  "updated_at": "datetime",
  "maintainer": "string",
  "documentation_url": "string",
  "dependencies": ["string"],
  "performance_metrics": {
    "avg_latency_ms": "number",
    "success_rate": "number"
  }
}
```

#### AgentExecutionRequest
```json
{
  "inputs": {
    "key": "value"
  },
  "model_override": "string",
  "timeout": "integer"
}
```

#### AgentExecutionResponse
```json
{
  "execution_id": "string",
  "agent_id": "string",
  "flow_id": "string",
  "status": "completed|failed",
  "output": {},
  "metadata": {
    "execution_time_ms": "number",
    "model_used": "string",
    "tokens_used": "number"
  },
  "started_at": "datetime",
  "completed_at": "datetime"
}
```

### Pipeline Models

#### PipelineConfig
```json
{
  "id": "string",
  "name": "string",
  "description": "string",
  "version": "string",
  "status": "active|draft|archived",
  "inputs": [
    {
      "name": "string",
      "desc": "string",
      "required": "boolean"
    }
  ],
  "outputs": [
    {
      "key": "string",
      "label": "string"
    }
  ],
  "steps": [
    {
      "id": "string",
      "type": "agent_flow|code_node|batch_aggregator",
      "agent": "string",
      "flow": "string",
      "input_mapping": {},
      "output_key": "string",
      "concurrent_group": "string",
      "depends_on": ["string"],
      "required": "boolean"
    }
  ],
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

#### PipelineExecutionRequest
```json
{
  "inputs": {},
  "config": {
    "max_workers": "integer",
    "timeout": "integer"
  }
}
```

#### PipelineExecutionResponse
```json
{
  "execution_id": "string",
  "pipeline_id": "string",
  "status": "completed|failed|running",
  "outputs": {},
  "step_results": [
    {
      "step_id": "string",
      "status": "completed|failed|skipped",
      "output": {},
      "execution_time_ms": "number"
    }
  ],
  "metadata": {
    "total_execution_time_ms": "number",
    "steps_executed": "integer",
    "steps_failed": "integer"
  },
  "started_at": "datetime",
  "completed_at": "datetime"
}
```

### Execution Models

#### AsyncExecutionRequest
```json
{
  "type": "agent|pipeline",
  "target_id": "string",
  "inputs": {},
  "config": {},
  "callback_url": "string"
}
```

#### ExecutionStatus
```json
{
  "execution_id": "string",
  "type": "agent|pipeline",
  "target_id": "string",
  "status": "pending|running|completed|failed|cancelled",
  "progress": {
    "current_step": "integer",
    "total_steps": "integer",
    "percentage": "number",
    "current_step_name": "string"
  },
  "outputs": {},
  "error": {
    "type": "string",
    "message": "string",
    "details": {}
  },
  "started_at": "datetime",
  "completed_at": "datetime"
}
```

### Batch Models

#### BatchExecutionRequest
```json
{
  "target_type": "agent|pipeline",
  "target_id": "string",
  "flow_id": "string",
  "test_cases": [
    {
      "id": "string",
      "inputs": {}
    }
  ],
  "config": {
    "concurrent": "boolean",
    "max_workers": "integer"
  }
}
```

#### BatchStatus
```json
{
  "batch_id": "string",
  "status": "pending|running|completed|failed",
  "progress": {
    "completed": "integer",
    "total": "integer",
    "percentage": "number"
  },
  "results": [
    {
      "test_id": "string",
      "status": "completed|failed",
      "output": {}
    }
  ],
  "started_at": "datetime",
  "completed_at": "datetime"
}
```


---

## Pagination

All list endpoints support pagination with consistent parameters and response format.

### Pagination Parameters
- `page` (integer, default=1): Page number (1-indexed)
- `page_size` (integer, default=50, max=100): Items per page

### Pagination Response
```json
{
  "items": [...],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 150,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false,
    "next_page": 2,
    "prev_page": null
  }
}
```

---

## Filtering and Sorting

### Filtering
List endpoints support filtering via query parameters:
- Field-specific filters: `?category=production&status=active`
- Multiple values: `?tags=memory,summarization` (comma-separated)
- Date ranges: `?created_after=2024-01-01&created_before=2024-12-31`

### Sorting
- `sort` parameter: Field name to sort by
- `order` parameter: `asc` (ascending) or `desc` (descending)
- Example: `?sort=created_at&order=desc`

---

## Rate Limiting

**Phase 1 (Current)**: No rate limiting  
**Phase 2 (Future)**: Rate limiting with headers

### Rate Limit Headers (Future)
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640000000
```

### Rate Limit Error (429)
```json
{
  "error": "RateLimitExceeded",
  "message": "Rate limit exceeded. Try again in 60 seconds.",
  "retry_after": 60
}
```

---

## Webhooks (Future)

For async executions, clients can provide a `callback_url` to receive completion notifications.

### Webhook Payload
```json
{
  "event": "execution.completed",
  "execution_id": "exec_345678",
  "status": "completed",
  "outputs": {},
  "timestamp": "2024-12-17T10:30:01.7Z"
}
```

### Webhook Events
- `execution.started`: Execution started
- `execution.completed`: Execution completed successfully
- `execution.failed`: Execution failed
- `execution.cancelled`: Execution cancelled

---

## API Versioning Strategy

### Current Version
- **v1**: Current stable version
- Base path: `/api/v1/`

### Version Deprecation
- Versions supported for minimum 12 months after deprecation announcement
- Deprecation warnings in response headers:
  ```
  X-API-Deprecated: true
  X-API-Deprecation-Date: 2025-01-01
  X-API-Sunset-Date: 2026-01-01
  ```

### Version Migration
- New versions introduced as `/api/v2/`, etc.
- Breaking changes only in new major versions
- Non-breaking changes added to current version

---

## Security Considerations

### Input Validation
- All inputs validated against schemas
- SQL injection prevention (not applicable - no SQL)
- YAML injection prevention in config parsing
- Path traversal prevention in file operations

### Code Execution Security
- Code nodes execute in isolated processes
- Timeout enforcement
- Resource limits (CPU, memory)
- No access to sensitive system resources

### Configuration Security
- Sensitive data stored in environment variables
- Configuration files validated before saving
- Access control for configuration endpoints (future)

### CORS Configuration
- Development: Allow all origins
- Production: Whitelist specific domains
- Credentials support for authenticated requests

---

## OpenAPI/Swagger Documentation

### Auto-Generated Documentation
- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`

### Documentation Features
- Interactive API testing
- Request/response examples
- Schema validation
- Authentication testing (future)

---

## Implementation Notes

### Technology Stack
- **Framework**: FastAPI 0.104+
- **Server**: Uvicorn
- **Validation**: Pydantic v2
- **Async**: asyncio, aiofiles
- **WebSocket**: FastAPI WebSocket support

### Performance Considerations
- Response compression (GZip)
- Connection pooling for database (future)
- Caching for frequently accessed data (future)
- Async I/O for file operations

### Monitoring and Logging
- Request/response logging
- Execution time tracking (X-Process-Time header)
- Error tracking and reporting
- Performance metrics collection (future)

---

## Testing Strategy

### Unit Tests
- Test each endpoint independently
- Mock external dependencies
- Validate request/response schemas

### Integration Tests
- Test complete workflows
- Use real agent/pipeline execution
- Validate error handling

### API Contract Tests
- Validate OpenAPI schema
- Ensure backward compatibility
- Test all documented examples

---

## Future Enhancements

### Short-term (Phase 2)
- [ ] Authentication (API keys)
- [ ] Rate limiting
- [ ] WebSocket real-time updates
- [ ] Batch operations optimization

### Medium-term (Phase 3)
- [ ] OAuth 2.0 / JWT authentication
- [ ] Role-based access control (RBAC)
- [ ] API usage analytics
- [ ] GraphQL endpoint (alternative to REST)

### Long-term (Phase 4)
- [ ] Multi-tenancy support
- [ ] API gateway integration
- [ ] Service mesh compatibility
- [ ] gRPC support for high-performance scenarios

---

## References

- **Requirements**: Requirement 8.2 (API Layer)
- **Design Document**: `.kiro/specs/project-production-readiness/design.md`
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **OpenAPI Specification**: https://swagger.io/specification/
- **REST API Best Practices**: https://restfulapi.net/

---

## Changelog

### Version 1.0.0 (2024-12-17)
- Initial API design specification
- Defined all core endpoints
- Established request/response models
- Documented error handling
- Defined pagination and filtering standards

