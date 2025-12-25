"""
API Data Models

This module defines Pydantic models for API request/response validation.
These models ensure type safety and automatic validation of API inputs/outputs.

All models follow the API design specification in:
docs/reference/api-design-specification.md
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List, Literal
from datetime import datetime
from enum import Enum


# ============================================================================
# System Models
# ============================================================================

class HealthStatus(str, Enum):
    """Health check status values."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class HealthResponse(BaseModel):
    """Health check response model."""
    status: HealthStatus
    service: str
    version: str
    timestamp: Optional[datetime] = None


class ErrorDetails(BaseModel):
    """Error details for validation errors."""
    field: Optional[str] = None
    message: str
    validation_errors: Optional[List[Dict[str, str]]] = None


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str
    message: str
    path: str
    details: Optional[ErrorDetails] = None
    timestamp: Optional[datetime] = None
    request_id: Optional[str] = None


class MessageResponse(BaseModel):
    """Generic message response model."""
    message: str
    data: Optional[Dict[str, Any]] = None


class PaginationInfo(BaseModel):
    """Pagination information for list responses."""
    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, le=100, description="Items per page")
    total_items: int = Field(ge=0, description="Total number of items")
    total_pages: int = Field(ge=0, description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_prev: bool = Field(description="Whether there is a previous page")
    next_page: Optional[int] = Field(None, description="Next page number")
    prev_page: Optional[int] = Field(None, description="Previous page number")


# ============================================================================
# Agent Models
# ============================================================================

class AgentCategory(str, Enum):
    """Agent category values."""
    PRODUCTION = "production"
    EXAMPLE = "example"
    TEST = "test"
    SYSTEM = "system"


class AgentEnvironment(str, Enum):
    """Agent environment values."""
    PRODUCTION = "production"
    STAGING = "staging"
    DEMO = "demo"
    TEST = "test"


class AgentStatus(str, Enum):
    """Agent status values."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"
    ARCHIVED = "archived"


class PerformanceMetrics(BaseModel):
    """Agent performance metrics."""
    avg_latency_ms: Optional[float] = None
    success_rate: Optional[float] = Field(None, ge=0.0, le=1.0)
    total_executions: Optional[int] = None
    last_execution: Optional[datetime] = None


class AgentMetadataResponse(BaseModel):
    """Agent metadata response model."""
    id: str
    name: str
    category: AgentCategory
    environment: AgentEnvironment
    owner: str
    version: str
    status: AgentStatus
    tags: List[str] = Field(default_factory=list)
    deprecated: bool = False
    location: str
    description: Optional[str] = None
    business_goal: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    maintainer: Optional[str] = None
    documentation_url: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list)
    performance_metrics: Optional[PerformanceMetrics] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "mem_l1_summarizer",
                "name": "一级记忆总结",
                "category": "production",
                "environment": "production",
                "owner": "memory-team",
                "version": "1.2.0",
                "status": "active",
                "tags": ["memory", "summarization"],
                "deprecated": False,
                "location": "agents/mem_l1_summarizer"
            }
        }


class AgentListResponse(BaseModel):
    """Response model for listing agents."""
    agents: List[AgentMetadataResponse]
    pagination: PaginationInfo


class AgentCreateRequest(BaseModel):
    """Request model for creating an agent."""
    id: str = Field(..., pattern=r'^[a-zA-Z][a-zA-Z0-9_]*$')
    name: str
    category: AgentCategory
    environment: AgentEnvironment
    owner: str
    version: str
    location: str
    description: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class AgentUpdateRequest(BaseModel):
    """Request model for updating an agent."""
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    status: Optional[AgentStatus] = None


class AgentFlowInfo(BaseModel):
    """Agent flow information."""
    id: str
    name: str
    version: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None


class AgentFlowsResponse(BaseModel):
    """Response model for listing agent flows."""
    agent_id: str
    flows: List[AgentFlowInfo]


class AgentExecutionRequest(BaseModel):
    """Request model for executing an agent flow."""
    inputs: Dict[str, Any] = Field(..., description="Input parameters for the agent")
    model_override: Optional[str] = Field(None, description="Override the default model")
    timeout: Optional[int] = Field(None, ge=1, description="Execution timeout in seconds")


class ExecutionMetadata(BaseModel):
    """Execution metadata."""
    execution_time_ms: float
    model_used: str
    tokens_used: Optional[int] = None


class AgentExecutionResponse(BaseModel):
    """Response model for agent execution."""
    execution_id: str
    agent_id: str
    flow_id: str
    status: Literal["completed", "failed"]
    output: Dict[str, Any]
    metadata: ExecutionMetadata
    started_at: datetime
    completed_at: datetime


# ============================================================================
# Pipeline Models
# ============================================================================

class PipelineStatus(str, Enum):
    """Pipeline status values."""
    ACTIVE = "active"
    DRAFT = "draft"
    ARCHIVED = "archived"


class InputSpec(BaseModel):
    """Pipeline input specification."""
    name: str
    desc: str = ""
    required: bool = True


class OutputSpec(BaseModel):
    """Pipeline output specification."""
    key: str
    label: str = ""


class StepType(str, Enum):
    """Pipeline step type."""
    AGENT_FLOW = "agent_flow"
    CODE_NODE = "code_node"
    BATCH_AGGREGATOR = "batch_aggregator"


class StepConfig(BaseModel):
    """Pipeline step configuration."""
    id: str
    type: StepType
    agent: Optional[str] = None
    flow: Optional[str] = None
    input_mapping: Dict[str, str] = Field(default_factory=dict)
    output_key: str
    concurrent_group: Optional[str] = None
    depends_on: List[str] = Field(default_factory=list)
    required: bool = True


class PipelineConfigResponse(BaseModel):
    """Pipeline configuration response."""
    id: str
    name: str
    description: str = ""
    version: str
    status: PipelineStatus
    inputs: List[InputSpec]
    outputs: List[OutputSpec]
    steps: List[StepConfig]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PipelineListItem(BaseModel):
    """Pipeline list item."""
    id: str
    name: str
    description: str = ""
    version: str
    status: PipelineStatus
    steps_count: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class PipelineListResponse(BaseModel):
    """Response model for listing pipelines."""
    pipelines: List[PipelineListItem]
    pagination: PaginationInfo


class PipelineCreateRequest(BaseModel):
    """Request model for creating a pipeline."""
    id: str = Field(..., pattern=r'^[a-zA-Z][a-zA-Z0-9_]*$')
    name: str
    description: str = ""
    inputs: List[InputSpec]
    outputs: List[OutputSpec]
    steps: List[StepConfig]


class PipelineUpdateRequest(BaseModel):
    """Request model for updating a pipeline."""
    name: Optional[str] = None
    description: Optional[str] = None
    steps: Optional[List[StepConfig]] = None


class PipelineExecutionRequest(BaseModel):
    """Request model for executing a pipeline."""
    inputs: Dict[str, Any]
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class StepResult(BaseModel):
    """Pipeline step execution result."""
    step_id: str
    status: Literal["completed", "failed", "skipped"]
    output: Optional[Dict[str, Any]] = None
    execution_time_ms: float


class PipelineExecutionResponse(BaseModel):
    """Response model for pipeline execution."""
    execution_id: str
    pipeline_id: str
    status: Literal["completed", "failed", "running"]
    outputs: Optional[Dict[str, Any]] = None
    step_results: List[StepResult]
    metadata: Dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime] = None


# ============================================================================
# Async Execution Models
# ============================================================================

class ExecutionType(str, Enum):
    """Execution type."""
    AGENT = "agent"
    PIPELINE = "pipeline"


class ExecutionStatus(str, Enum):
    """Execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProgressInfo(BaseModel):
    """Execution progress information."""
    current_step: int
    total_steps: int
    percentage: float = Field(ge=0.0, le=100.0)
    current_step_name: Optional[str] = None


class AsyncExecutionRequest(BaseModel):
    """Request model for async execution."""
    type: ExecutionType
    target_id: str
    inputs: Dict[str, Any]
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    callback_url: Optional[str] = None


class AsyncExecutionResponse(BaseModel):
    """Response model for async execution start."""
    execution_id: str
    status: ExecutionStatus
    message: str
    status_url: str
    created_at: datetime


class ExecutionError(BaseModel):
    """Execution error details."""
    type: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ExecutionStatusResponse(BaseModel):
    """Response model for execution status."""
    execution_id: str
    type: ExecutionType
    target_id: str
    status: ExecutionStatus
    progress: Optional[ProgressInfo] = None
    outputs: Optional[Dict[str, Any]] = None
    error: Optional[ExecutionError] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None


class ExecutionListItem(BaseModel):
    """Execution list item."""
    execution_id: str
    type: ExecutionType
    target_id: str
    status: ExecutionStatus
    started_at: datetime
    completed_at: Optional[datetime] = None


class ExecutionListResponse(BaseModel):
    """Response model for listing executions."""
    executions: List[ExecutionListItem]
    pagination: PaginationInfo


# ============================================================================
# Batch Processing Models
# ============================================================================

class TestCase(BaseModel):
    """Batch test case."""
    id: str
    inputs: Dict[str, Any]


class BatchExecutionRequest(BaseModel):
    """Request model for batch execution."""
    target_type: ExecutionType
    target_id: str
    flow_id: Optional[str] = None
    test_cases: List[TestCase]
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class BatchProgressInfo(BaseModel):
    """Batch execution progress."""
    completed: int
    total: int
    percentage: float = Field(ge=0.0, le=100.0)


class BatchTestResult(BaseModel):
    """Batch test result."""
    test_id: str
    status: Literal["completed", "failed"]
    output: Optional[Dict[str, Any]] = None


class BatchStatusResponse(BaseModel):
    """Response model for batch status."""
    batch_id: str
    status: ExecutionStatus
    progress: BatchProgressInfo
    results: List[BatchTestResult]
    started_at: datetime
    completed_at: Optional[datetime] = None


# ============================================================================
# Configuration Models
# ============================================================================

class ConfigResponse(BaseModel):
    """Configuration file response."""
    id: str
    config: Dict[str, Any]
    file_path: str
    last_modified: datetime


class ConfigUpdateRequest(BaseModel):
    """Configuration update request."""
    config: Dict[str, Any]


class ConfigValidationRequest(BaseModel):
    """Configuration validation request."""
    type: Literal["agent", "pipeline"]
    config: Dict[str, Any]


class ValidationError(BaseModel):
    """Validation error detail."""
    field: str
    message: str


class ConfigValidationResponse(BaseModel):
    """Configuration validation response."""
    valid: bool
    message: Optional[str] = None
    errors: Optional[List[ValidationError]] = None
