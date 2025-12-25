"""
Execution Manager

This module manages asynchronous execution of agents and pipelines.
It provides:
- Task queue management
- Background task execution
- Execution status tracking
- Result storage

Requirements: 8.5
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
import threading
from enum import Enum

from .models import (
    ExecutionStatus,
    ExecutionType,
    ExecutionStatusResponse,
    ProgressInfo,
    ExecutionError
)
from ..pipeline_runner import PipelineRunner
from ..pipeline_config import PipelineConfig
from ..agent_registry import load_agent
from ..chains import run_flow_with_tokens

logger = logging.getLogger(__name__)


@dataclass
class ExecutionRecord:
    """Record of an execution."""
    execution_id: str
    type: ExecutionType
    target_id: str
    status: ExecutionStatus
    inputs: Dict[str, Any]
    config: Dict[str, Any]
    callback_url: Optional[str] = None
    outputs: Optional[Dict[str, Any]] = None
    error: Optional[ExecutionError] = None
    progress: Optional[ProgressInfo] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_status_response(self) -> ExecutionStatusResponse:
        """Convert to API response model."""
        return ExecutionStatusResponse(
            execution_id=self.execution_id,
            type=self.type,
            target_id=self.target_id,
            status=self.status,
            progress=self.progress,
            outputs=self.outputs,
            error=self.error,
            started_at=self.started_at or self.created_at,
            completed_at=self.completed_at,
            failed_at=self.failed_at
        )


class ExecutionManager:
    """
    Manages asynchronous execution of agents and pipelines.
    
    This class provides:
    - Execution record management
    - Background task execution
    - Status tracking and querying
    - Result storage
    """
    
    def __init__(self):
        """Initialize the execution manager."""
        self.executions: Dict[str, ExecutionRecord] = {}
        self.lock = threading.Lock()
        logger.info("ExecutionManager initialized")
    
    def create_execution(
        self,
        execution_id: str,
        execution_type: ExecutionType,
        target_id: str,
        inputs: Dict[str, Any],
        config: Dict[str, Any],
        callback_url: Optional[str] = None
    ) -> ExecutionRecord:
        """
        Create a new execution record.
        
        Args:
            execution_id: Unique execution identifier
            execution_type: Type of execution (agent or pipeline)
            target_id: Agent ID or Pipeline ID
            inputs: Input parameters
            config: Configuration overrides
            callback_url: Optional webhook URL
            
        Returns:
            ExecutionRecord: Created execution record
        """
        with self.lock:
            if execution_id in self.executions:
                raise ValueError(f"Execution '{execution_id}' already exists")
            
            record = ExecutionRecord(
                execution_id=execution_id,
                type=execution_type,
                target_id=target_id,
                status=ExecutionStatus.PENDING,
                inputs=inputs,
                config=config,
                callback_url=callback_url
            )
            
            self.executions[execution_id] = record
            logger.info(f"Created execution record: {execution_id}")
            return record
    
    def get_execution_status(self, execution_id: str) -> Optional[ExecutionStatusResponse]:
        """
        Get execution status.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            ExecutionStatusResponse or None if not found
        """
        with self.lock:
            record = self.executions.get(execution_id)
            if record is None:
                return None
            return record.to_status_response()
    
    def list_executions(
        self,
        status: Optional[ExecutionStatus] = None,
        execution_type: Optional[ExecutionType] = None,
        target_id: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> List[ExecutionRecord]:
        """
        List executions with optional filtering.
        
        Args:
            status: Filter by status
            execution_type: Filter by type
            target_id: Filter by target ID
            sort_by: Sort field
            sort_order: Sort order (asc/desc)
            
        Returns:
            List of execution records
        """
        with self.lock:
            executions = list(self.executions.values())
        
        # Apply filters
        if status is not None:
            executions = [e for e in executions if e.status == status]
        if execution_type is not None:
            executions = [e for e in executions if e.type == execution_type]
        if target_id is not None:
            executions = [e for e in executions if e.target_id == target_id]
        
        # Sort
        reverse = sort_order.lower() == "desc"
        if sort_by == "created_at":
            executions.sort(key=lambda e: e.created_at, reverse=reverse)
        elif sort_by == "started_at":
            executions.sort(key=lambda e: e.started_at or e.created_at, reverse=reverse)
        elif sort_by == "completed_at":
            executions.sort(key=lambda e: e.completed_at or datetime.max, reverse=reverse)
        
        return executions
    
    def cancel_execution(self, execution_id: str) -> datetime:
        """
        Cancel an execution.
        
        Args:
            execution_id: Execution identifier
            
        Returns:
            Cancellation timestamp
            
        Raises:
            ValueError: If execution not found or cannot be cancelled
        """
        with self.lock:
            record = self.executions.get(execution_id)
            if record is None:
                raise ValueError(f"Execution '{execution_id}' not found")
            
            if record.status not in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING]:
                raise ValueError(f"Cannot cancel execution with status '{record.status.value}'")
            
            record.status = ExecutionStatus.CANCELLED
            record.completed_at = datetime.now()
            
            logger.info(f"Cancelled execution: {execution_id}")
            return record.completed_at
    
    async def execute_agent_async(
        self,
        execution_id: str,
        agent_id: str,
        inputs: Dict[str, Any],
        config: Dict[str, Any]
    ):
        """
        Execute an agent asynchronously.
        
        Args:
            execution_id: Execution identifier
            agent_id: Agent identifier
            inputs: Input parameters
            config: Configuration overrides
        """
        try:
            # Update status to running
            with self.lock:
                record = self.executions.get(execution_id)
                if record is None:
                    logger.error(f"Execution record not found: {execution_id}")
                    return
                
                if record.status == ExecutionStatus.CANCELLED:
                    logger.info(f"Execution cancelled before start: {execution_id}")
                    return
                
                record.status = ExecutionStatus.RUNNING
                record.started_at = datetime.now()
                record.progress = ProgressInfo(
                    current_step=0,
                    total_steps=1,
                    percentage=0.0
                )
            
            logger.info(f"Starting agent execution: {execution_id} (agent={agent_id})")
            
            # Extract flow_id from config or use default
            flow_id = config.get("flow_id", "default")
            model_override = config.get("model_override")
            
            # Execute agent in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._execute_agent_sync,
                agent_id,
                flow_id,
                inputs,
                model_override
            )
            
            # Check if cancelled during execution
            with self.lock:
                record = self.executions.get(execution_id)
                if record and record.status == ExecutionStatus.CANCELLED:
                    logger.info(f"Execution cancelled during execution: {execution_id}")
                    return
            
            # Update status to completed
            with self.lock:
                record = self.executions.get(execution_id)
                if record:
                    record.status = ExecutionStatus.COMPLETED
                    record.outputs = result
                    record.completed_at = datetime.now()
                    record.progress = ProgressInfo(
                        current_step=1,
                        total_steps=1,
                        percentage=100.0
                    )
            
            logger.info(f"Agent execution completed: {execution_id}")
            
            # Send callback if configured
            if record and record.callback_url:
                await self._send_callback(record)
                
        except Exception as e:
            logger.error(f"Agent execution failed: {execution_id} - {e}", exc_info=True)
            
            # Update status to failed
            with self.lock:
                record = self.executions.get(execution_id)
                if record:
                    record.status = ExecutionStatus.FAILED
                    record.failed_at = datetime.now()
                    record.error = ExecutionError(
                        type=type(e).__name__,
                        message=str(e),
                        details={"agent_id": agent_id}
                    )
            
            # Send callback if configured
            if record and record.callback_url:
                await self._send_callback(record)
    
    def _execute_agent_sync(
        self,
        agent_id: str,
        flow_id: str,
        inputs: Dict[str, Any],
        model_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute agent synchronously (runs in thread pool).
        
        Args:
            agent_id: Agent identifier
            flow_id: Flow identifier
            inputs: Input parameters
            model_override: Optional model override
            
        Returns:
            Execution outputs
        """
        # Load agent configuration
        agent = load_agent(agent_id)
        
        # Find the flow
        flow = None
        for f in agent.flows:
            if f.name == flow_id:
                flow = f
                break
        
        if flow is None:
            raise ValueError(f"Flow '{flow_id}' not found in agent '{agent_id}'")
        
        # Prepare input text
        input_text = inputs.get("text", "")
        if not input_text and "input" in inputs:
            input_text = inputs["input"]
        
        # Execute flow
        output, token_usage, parser_stats = run_flow_with_tokens(
            flow_name=flow.name,
            input_text=input_text,
            agent_id=agent_id,
            model_override=model_override,
            **inputs
        )
        
        return {
            "output": output,
            "metadata": {
                "model_used": model_override or flow.model or "unknown",
                "tokens_used": token_usage.get("total_tokens") if token_usage else None,
                "parser_stats": parser_stats
            }
        }
    
    async def execute_pipeline_async(
        self,
        execution_id: str,
        pipeline_id: str,
        inputs: Dict[str, Any],
        config: Dict[str, Any]
    ):
        """
        Execute a pipeline asynchronously.
        
        Args:
            execution_id: Execution identifier
            pipeline_id: Pipeline identifier
            inputs: Input parameters
            config: Configuration overrides
        """
        try:
            # Update status to running
            with self.lock:
                record = self.executions.get(execution_id)
                if record is None:
                    logger.error(f"Execution record not found: {execution_id}")
                    return
                
                if record.status == ExecutionStatus.CANCELLED:
                    logger.info(f"Execution cancelled before start: {execution_id}")
                    return
                
                record.status = ExecutionStatus.RUNNING
                record.started_at = datetime.now()
            
            logger.info(f"Starting pipeline execution: {execution_id} (pipeline={pipeline_id})")
            
            # Load pipeline configuration
            pipeline_path = Path(f"pipelines/{pipeline_id}.yaml")
            if not pipeline_path.exists():
                raise FileNotFoundError(f"Pipeline '{pipeline_id}' not found")
            
            pipeline_config = PipelineConfig.from_yaml(pipeline_path)
            
            # Create progress callback
            def progress_callback(current: int, total: int, step_name: Optional[str] = None):
                with self.lock:
                    record = self.executions.get(execution_id)
                    if record:
                        record.progress = ProgressInfo(
                            current_step=current,
                            total_steps=total,
                            percentage=(current / total * 100) if total > 0 else 0,
                            current_step_name=step_name
                        )
            
            # Execute pipeline in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                self._execute_pipeline_sync,
                pipeline_config,
                inputs,
                config,
                progress_callback
            )
            
            # Check if cancelled during execution
            with self.lock:
                record = self.executions.get(execution_id)
                if record and record.status == ExecutionStatus.CANCELLED:
                    logger.info(f"Execution cancelled during execution: {execution_id}")
                    return
            
            # Update status to completed
            with self.lock:
                record = self.executions.get(execution_id)
                if record:
                    record.status = ExecutionStatus.COMPLETED
                    record.outputs = result.get("outputs")
                    record.completed_at = datetime.now()
                    if record.progress:
                        record.progress.percentage = 100.0
            
            logger.info(f"Pipeline execution completed: {execution_id}")
            
            # Send callback if configured
            if record and record.callback_url:
                await self._send_callback(record)
                
        except Exception as e:
            logger.error(f"Pipeline execution failed: {execution_id} - {e}", exc_info=True)
            
            # Update status to failed
            with self.lock:
                record = self.executions.get(execution_id)
                if record:
                    record.status = ExecutionStatus.FAILED
                    record.failed_at = datetime.now()
                    record.error = ExecutionError(
                        type=type(e).__name__,
                        message=str(e),
                        details={"pipeline_id": pipeline_id}
                    )
            
            # Send callback if configured
            if record and record.callback_url:
                await self._send_callback(record)
    
    def _execute_pipeline_sync(
        self,
        pipeline_config: PipelineConfig,
        inputs: Dict[str, Any],
        config: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Execute pipeline synchronously (runs in thread pool).
        
        Args:
            pipeline_config: Pipeline configuration
            inputs: Input parameters
            config: Configuration overrides
            progress_callback: Progress callback function
            
        Returns:
            Execution outputs
        """
        # Create pipeline runner
        runner = PipelineRunner(pipeline_config)
        
        # Set progress callback
        if progress_callback:
            runner.set_progress_callback(progress_callback)
        
        # Create sample with inputs
        sample = {"inputs": inputs}
        
        # Execute pipeline
        result = runner.execute_sample(
            sample=sample,
            variant="baseline",
            progress_tracker=None,
            sample_index=0
        )
        
        return {
            "outputs": result.outputs,
            "step_results": [
                {
                    "step_id": step_result.step_id,
                    "status": "completed" if step_result.success else "failed",
                    "output": step_result.output,
                    "execution_time_ms": step_result.execution_time * 1000
                }
                for step_result in result.step_results
            ],
            "metadata": {
                "total_execution_time_ms": result.total_time * 1000,
                "steps_executed": len([s for s in result.step_results if s.success]),
                "steps_failed": len([s for s in result.step_results if not s.success])
            }
        }
    
    async def _send_callback(self, record: ExecutionRecord):
        """
        Send webhook callback for execution completion.
        
        Args:
            record: Execution record
        """
        if not record.callback_url:
            return
        
        try:
            import aiohttp
            
            payload = {
                "event": f"execution.{record.status.value}",
                "execution_id": record.execution_id,
                "status": record.status.value,
                "outputs": record.outputs,
                "error": record.error.dict() if record.error else None,
                "timestamp": datetime.now().isoformat()
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(record.callback_url, json=payload) as response:
                    if response.status == 200:
                        logger.info(f"Callback sent successfully: {record.execution_id}")
                    else:
                        logger.warning(f"Callback failed with status {response.status}: {record.execution_id}")
                        
        except Exception as e:
            logger.error(f"Failed to send callback: {e}", exc_info=True)


# Global execution manager instance
_execution_manager: Optional[ExecutionManager] = None


def get_execution_manager() -> ExecutionManager:
    """Get or create the global execution manager instance."""
    global _execution_manager
    if _execution_manager is None:
        _execution_manager = ExecutionManager()
    return _execution_manager
