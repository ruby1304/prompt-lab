"""
Property-Based Tests for Async Execution and Progress Query

This module tests Property 35: Async execution and progress query
For any long-running execution started asynchronously, the system should
provide queryable progress information.

Feature: project-production-readiness, Property 35: Async execution and progress query
Validates: Requirements 8.5
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from fastapi.testclient import TestClient
from pathlib import Path
import time
import asyncio
from datetime import datetime
from typing import Dict, Any

from src.api.app import create_app
from src.api.execution_manager import ExecutionManager, get_execution_manager, ExecutionRecord
from src.api.models import ExecutionStatus, ExecutionType, ProgressInfo, ExecutionError


@pytest.fixture
def test_client():
    """Create a test client."""
    app = create_app()
    return TestClient(app)


@pytest.fixture
def execution_manager():
    """Get execution manager instance."""
    manager = get_execution_manager()
    # Clear before returning
    manager.executions.clear()
    return manager


@pytest.fixture(autouse=True)
def clear_executions(execution_manager):
    """Clear executions before and after each test."""
    execution_manager.executions.clear()
    yield
    execution_manager.executions.clear()


# Custom strategies for generating execution data
import uuid

def generate_unique_execution_id():
    """Generate a unique execution ID."""
    return f"exec_{uuid.uuid4().hex[:12]}"

execution_id_strategy = st.builds(generate_unique_execution_id)

target_id_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='_'),
    min_size=1,
    max_size=50
).filter(lambda x: x[0].isalpha())

inputs_strategy = st.dictionaries(
    keys=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
    values=st.one_of(
        st.text(min_size=0, max_size=100),
        st.integers(min_value=-1000, max_value=1000),
        st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        st.booleans()
    ),
    min_size=0,
    max_size=5
)

config_strategy = st.dictionaries(
    keys=st.sampled_from(["flow_id", "model_override", "timeout", "max_workers"]),
    values=st.one_of(
        st.text(min_size=1, max_size=50),
        st.integers(min_value=1, max_value=100)
    ),
    min_size=0,
    max_size=3
)


class TestAsyncExecutionCreation:
    """Test async execution creation and initial status."""
    
    # Feature: project-production-readiness, Property 35: Async execution and progress query
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        execution_id=execution_id_strategy,
        execution_type=st.sampled_from([ExecutionType.AGENT, ExecutionType.PIPELINE]),
        target_id=target_id_strategy,
        inputs=inputs_strategy,
        config=config_strategy
    )
    def test_async_execution_creation_provides_queryable_status(
        self,
        execution_id,
        execution_type,
        target_id,
        inputs,
        config,
        execution_manager
    ):
        """
        Feature: project-production-readiness, Property 35: Async execution and progress query
        Validates: Requirements 8.5
        
        Property: For any async execution created, the system should immediately
        provide queryable status information.
        """
        # Create execution
        record = execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=execution_type,
            target_id=target_id,
            inputs=inputs,
            config=config
        )
        
        # Verify execution was created
        assert record is not None
        assert record.execution_id == execution_id
        assert record.type == execution_type
        assert record.target_id == target_id
        assert record.status == ExecutionStatus.PENDING
        
        # Query status immediately
        status = execution_manager.get_execution_status(execution_id)
        
        # Verify status is queryable
        assert status is not None, "Status should be queryable immediately after creation"
        assert status.execution_id == execution_id
        assert status.type == execution_type
        assert status.target_id == target_id
        assert status.status == ExecutionStatus.PENDING
        assert status.started_at is not None  # Should have a timestamp
    
    # Feature: project-production-readiness, Property 35: Async execution and progress query
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        execution_id=execution_id_strategy,
        execution_type=st.sampled_from([ExecutionType.AGENT, ExecutionType.PIPELINE]),
        target_id=target_id_strategy,
        inputs=inputs_strategy,
        config=config_strategy
    )
    def test_execution_status_accessible_via_api(
        self,
        execution_id,
        execution_type,
        target_id,
        inputs,
        config,
        execution_manager,
        test_client
    ):
        """
        Feature: project-production-readiness, Property 35: Async execution and progress query
        Validates: Requirements 8.5
        
        Property: For any execution, the status should be accessible via API endpoint.
        """
        # Create execution
        execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=execution_type,
            target_id=target_id,
            inputs=inputs,
            config=config
        )
        
        # Query via API
        response = test_client.get(f"/api/v1/executions/{execution_id}")
        
        # Verify API returns status
        assert response.status_code == 200, f"API should return status for execution {execution_id}"
        
        data = response.json()
        assert data["execution_id"] == execution_id
        assert data["type"] == execution_type.value
        assert data["target_id"] == target_id
        assert data["status"] == ExecutionStatus.PENDING.value


class TestProgressQueryability:
    """Test progress information queryability."""
    
    # Feature: project-production-readiness, Property 35: Async execution and progress query
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        execution_id=execution_id_strategy,
        current_step=st.integers(min_value=0, max_value=100),
        total_steps=st.integers(min_value=1, max_value=100),
        step_name=st.one_of(st.none(), st.text(min_size=1, max_size=50))
    )
    def test_progress_information_is_queryable(
        self,
        execution_id,
        current_step,
        total_steps,
        step_name,
        execution_manager
    ):
        """
        Feature: project-production-readiness, Property 35: Async execution and progress query
        Validates: Requirements 8.5
        
        Property: For any execution with progress information, the progress
        should be queryable and return accurate data.
        """
        # Ensure current_step doesn't exceed total_steps
        assume(current_step <= total_steps)
        
        # Create execution with progress
        record = execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.PIPELINE,
            target_id="test_pipeline",
            inputs={},
            config={}
        )
        
        # Set progress
        record.status = ExecutionStatus.RUNNING
        record.progress = ProgressInfo(
            current_step=current_step,
            total_steps=total_steps,
            percentage=(current_step / total_steps * 100) if total_steps > 0 else 0,
            current_step_name=step_name
        )
        
        # Query status
        status = execution_manager.get_execution_status(execution_id)
        
        # Verify progress is included
        assert status is not None
        assert status.progress is not None, "Progress should be queryable"
        assert status.progress.current_step == current_step
        assert status.progress.total_steps == total_steps
        assert abs(status.progress.percentage - (current_step / total_steps * 100)) < 0.01
        
        if step_name:
            assert status.progress.current_step_name == step_name
    
    # Feature: project-production-readiness, Property 35: Async execution and progress query
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        execution_id=execution_id_strategy,
        current_step=st.integers(min_value=0, max_value=100),
        total_steps=st.integers(min_value=1, max_value=100)
    )
    def test_progress_accessible_via_api(
        self,
        execution_id,
        current_step,
        total_steps,
        execution_manager,
        test_client
    ):
        """
        Feature: project-production-readiness, Property 35: Async execution and progress query
        Validates: Requirements 8.5
        
        Property: For any execution with progress, the progress should be
        accessible via dedicated progress API endpoint.
        """
        # Ensure current_step doesn't exceed total_steps
        assume(current_step <= total_steps)
        
        # Create execution with progress
        record = execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.PIPELINE,
            target_id="test_pipeline",
            inputs={},
            config={}
        )
        
        record.status = ExecutionStatus.RUNNING
        record.progress = ProgressInfo(
            current_step=current_step,
            total_steps=total_steps,
            percentage=(current_step / total_steps * 100) if total_steps > 0 else 0
        )
        
        # Query progress via API
        response = test_client.get(f"/api/v1/executions/{execution_id}/progress")
        
        # Verify API returns progress
        assert response.status_code == 200, "Progress endpoint should return data"
        
        data = response.json()
        assert data["current_step"] == current_step
        assert data["total_steps"] == total_steps
        assert abs(data["percentage"] - (current_step / total_steps * 100)) < 0.01
    
    # Feature: project-production-readiness, Property 35: Async execution and progress query
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        execution_id=execution_id_strategy
    )
    def test_progress_query_handles_no_progress_data(
        self,
        execution_id,
        execution_manager,
        test_client
    ):
        """
        Feature: project-production-readiness, Property 35: Async execution and progress query
        Validates: Requirements 8.5
        
        Property: For any execution without progress data, the progress query
        should handle gracefully (return 204 No Content).
        """
        # Create execution without progress
        execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.AGENT,
            target_id="test_agent",
            inputs={},
            config={}
        )
        
        # Query progress via API
        response = test_client.get(f"/api/v1/executions/{execution_id}/progress")
        
        # Should return 204 No Content when no progress data
        assert response.status_code == 204, "Should return 204 when no progress data available"


class TestExecutionStatusTransitions:
    """Test execution status transitions and queryability."""
    
    # Feature: project-production-readiness, Property 35: Async execution and progress query
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        execution_id=execution_id_strategy,
        target_id=target_id_strategy
    )
    def test_status_transitions_are_queryable(
        self,
        execution_id,
        target_id,
        execution_manager
    ):
        """
        Feature: project-production-readiness, Property 35: Async execution and progress query
        Validates: Requirements 8.5
        
        Property: For any execution, status transitions (pending -> running -> completed)
        should be queryable at each stage.
        """
        # Create execution (PENDING)
        record = execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.AGENT,
            target_id=target_id,
            inputs={},
            config={}
        )
        
        # Query PENDING status
        status1 = execution_manager.get_execution_status(execution_id)
        assert status1 is not None
        assert status1.status == ExecutionStatus.PENDING
        
        # Transition to RUNNING
        record.status = ExecutionStatus.RUNNING
        record.started_at = datetime.now()
        
        # Query RUNNING status
        status2 = execution_manager.get_execution_status(execution_id)
        assert status2 is not None
        assert status2.status == ExecutionStatus.RUNNING
        assert status2.started_at is not None
        
        # Transition to COMPLETED
        record.status = ExecutionStatus.COMPLETED
        record.completed_at = datetime.now()
        record.outputs = {"result": "success"}
        
        # Query COMPLETED status
        status3 = execution_manager.get_execution_status(execution_id)
        assert status3 is not None
        assert status3.status == ExecutionStatus.COMPLETED
        assert status3.completed_at is not None
        assert status3.outputs is not None
    
    # Feature: project-production-readiness, Property 35: Async execution and progress query
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        execution_id=execution_id_strategy,
        error_type=st.text(min_size=1, max_size=50),
        error_message=st.text(min_size=1, max_size=200)
    )
    def test_failed_execution_status_is_queryable(
        self,
        execution_id,
        error_type,
        error_message,
        execution_manager
    ):
        """
        Feature: project-production-readiness, Property 35: Async execution and progress query
        Validates: Requirements 8.5
        
        Property: For any failed execution, the error information should be
        queryable along with the status.
        """
        # Create execution
        record = execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.PIPELINE,
            target_id="test_pipeline",
            inputs={},
            config={}
        )
        
        # Transition to FAILED with error
        record.status = ExecutionStatus.FAILED
        record.failed_at = datetime.now()
        record.error = ExecutionError(
            type=error_type,
            message=error_message,
            details={"test": "data"}
        )
        
        # Query status
        status = execution_manager.get_execution_status(execution_id)
        
        # Verify error information is queryable
        assert status is not None
        assert status.status == ExecutionStatus.FAILED
        assert status.failed_at is not None
        assert status.error is not None
        assert status.error.type == error_type
        assert status.error.message == error_message
        assert status.error.details == {"test": "data"}
    
    # Feature: project-production-readiness, Property 35: Async execution and progress query
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        execution_id=execution_id_strategy
    )
    def test_cancelled_execution_status_is_queryable(
        self,
        execution_id,
        execution_manager
    ):
        """
        Feature: project-production-readiness, Property 35: Async execution and progress query
        Validates: Requirements 8.5
        
        Property: For any cancelled execution, the cancellation status should
        be queryable.
        """
        # Create execution
        execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.AGENT,
            target_id="test_agent",
            inputs={},
            config={}
        )
        
        # Cancel execution
        cancelled_at = execution_manager.cancel_execution(execution_id)
        
        # Query status
        status = execution_manager.get_execution_status(execution_id)
        
        # Verify cancellation is queryable
        assert status is not None
        assert status.status == ExecutionStatus.CANCELLED
        assert status.completed_at is not None
        assert status.completed_at == cancelled_at


class TestExecutionListing:
    """Test execution listing and filtering."""
    
    # Feature: project-production-readiness, Property 35: Async execution and progress query
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        num_executions=st.integers(min_value=1, max_value=20),
        filter_type=st.one_of(st.none(), st.sampled_from([ExecutionType.AGENT, ExecutionType.PIPELINE])),
        filter_status=st.one_of(st.none(), st.sampled_from([
            ExecutionStatus.PENDING,
            ExecutionStatus.RUNNING,
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED
        ]))
    )
    def test_executions_are_listable_and_filterable(
        self,
        num_executions,
        filter_type,
        filter_status,
        execution_manager
    ):
        """
        Feature: project-production-readiness, Property 35: Async execution and progress query
        Validates: Requirements 8.5
        
        Property: For any set of executions, they should be listable and
        filterable by type and status.
        """
        # Clear executions for this example
        execution_manager.executions.clear()
        
        # Create multiple executions with varying types and statuses
        created_executions = []
        for i in range(num_executions):
            exec_type = ExecutionType.AGENT if i % 2 == 0 else ExecutionType.PIPELINE
            record = execution_manager.create_execution(
                execution_id=f"exec_test_{uuid.uuid4().hex[:8]}_{i}",
                execution_type=exec_type,
                target_id=f"target_{i}",
                inputs={},
                config={}
            )
            
            # Set varying statuses
            if i % 4 == 0:
                record.status = ExecutionStatus.PENDING
            elif i % 4 == 1:
                record.status = ExecutionStatus.RUNNING
            elif i % 4 == 2:
                record.status = ExecutionStatus.COMPLETED
            else:
                record.status = ExecutionStatus.FAILED
            
            created_executions.append(record)
        
        # List with filters
        filtered = execution_manager.list_executions(
            execution_type=filter_type,
            status=filter_status
        )
        
        # Verify filtering works correctly
        assert isinstance(filtered, list)
        
        for execution in filtered:
            if filter_type is not None:
                assert execution.type == filter_type, \
                    f"Filtered execution should match type filter"
            
            if filter_status is not None:
                assert execution.status == filter_status, \
                    f"Filtered execution should match status filter"
    
    # Feature: project-production-readiness, Property 35: Async execution and progress query
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        num_executions=st.integers(min_value=5, max_value=20),
        page=st.integers(min_value=1, max_value=5),
        page_size=st.integers(min_value=1, max_value=10)
    )
    def test_execution_list_supports_pagination(
        self,
        num_executions,
        page,
        page_size,
        execution_manager,
        test_client
    ):
        """
        Feature: project-production-readiness, Property 35: Async execution and progress query
        Validates: Requirements 8.5
        
        Property: For any set of executions, the list API should support
        pagination and return consistent results.
        """
        # Clear executions for this example
        execution_manager.executions.clear()
        
        # Create executions
        for i in range(num_executions):
            execution_manager.create_execution(
                execution_id=f"exec_page_test_{uuid.uuid4().hex[:8]}_{i}",
                execution_type=ExecutionType.AGENT,
                target_id=f"agent_{i}",
                inputs={},
                config={}
            )
        
        # Query with pagination
        response = test_client.get(f"/api/v1/executions?page={page}&page_size={page_size}")
        
        # Verify pagination works
        assert response.status_code == 200
        
        data = response.json()
        assert "executions" in data
        assert "pagination" in data
        
        pagination = data["pagination"]
        assert pagination["page"] == page
        assert pagination["page_size"] == page_size
        assert pagination["total_items"] == num_executions
        
        # Verify page size is respected (unless on last page)
        expected_items = min(page_size, max(0, num_executions - (page - 1) * page_size))
        assert len(data["executions"]) == expected_items


class TestProgressConsistency:
    """Test progress information consistency."""
    
    # Feature: project-production-readiness, Property 35: Async execution and progress query
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        execution_id=execution_id_strategy,
        progress_updates=st.lists(
            st.tuples(
                st.integers(min_value=0, max_value=100),  # current_step
                st.integers(min_value=1, max_value=100)   # total_steps
            ),
            min_size=1,
            max_size=10
        )
    )
    def test_progress_updates_are_consistently_queryable(
        self,
        execution_id,
        progress_updates,
        execution_manager
    ):
        """
        Feature: project-production-readiness, Property 35: Async execution and progress query
        Validates: Requirements 8.5
        
        Property: For any sequence of progress updates, each update should be
        queryable and reflect the most recent state.
        """
        # Create execution
        record = execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.PIPELINE,
            target_id="test_pipeline",
            inputs={},
            config={}
        )
        
        record.status = ExecutionStatus.RUNNING
        
        # Apply progress updates and verify each is queryable
        for current, total in progress_updates:
            # Ensure current doesn't exceed total
            if current > total:
                current = total
            
            # Update progress
            record.progress = ProgressInfo(
                current_step=current,
                total_steps=total,
                percentage=(current / total * 100) if total > 0 else 0
            )
            
            # Query and verify
            status = execution_manager.get_execution_status(execution_id)
            assert status is not None
            assert status.progress is not None
            assert status.progress.current_step == current
            assert status.progress.total_steps == total
            
            # Verify percentage is calculated correctly
            expected_percentage = (current / total * 100) if total > 0 else 0
            assert abs(status.progress.percentage - expected_percentage) < 0.01
    
    # Feature: project-production-readiness, Property 35: Async execution and progress query
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        execution_id=execution_id_strategy,
        total_steps=st.integers(min_value=1, max_value=50)
    )
    def test_progress_percentage_is_accurate(
        self,
        execution_id,
        total_steps,
        execution_manager
    ):
        """
        Feature: project-production-readiness, Property 35: Async execution and progress query
        Validates: Requirements 8.5
        
        Property: For any execution progress, the percentage should accurately
        reflect the ratio of current_step to total_steps.
        """
        # Create execution
        record = execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.PIPELINE,
            target_id="test_pipeline",
            inputs={},
            config={}
        )
        
        record.status = ExecutionStatus.RUNNING
        
        # Test progress at each step
        for current_step in range(total_steps + 1):
            expected_percentage = (current_step / total_steps * 100) if total_steps > 0 else 0
            
            record.progress = ProgressInfo(
                current_step=current_step,
                total_steps=total_steps,
                percentage=expected_percentage
            )
            
            # Query and verify percentage
            status = execution_manager.get_execution_status(execution_id)
            assert status is not None
            assert status.progress is not None
            
            # Percentage should match expected value
            assert abs(status.progress.percentage - expected_percentage) < 0.01, \
                f"Percentage mismatch at step {current_step}/{total_steps}"


class TestExecutionQueryRobustness:
    """Test robustness of execution queries."""
    
    # Feature: project-production-readiness, Property 35: Async execution and progress query
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        nonexistent_id=execution_id_strategy
    )
    def test_query_nonexistent_execution_returns_none(
        self,
        nonexistent_id,
        execution_manager
    ):
        """
        Feature: project-production-readiness, Property 35: Async execution and progress query
        Validates: Requirements 8.5
        
        Property: For any non-existent execution ID, querying should return None
        or 404, not crash.
        """
        # Query non-existent execution
        status = execution_manager.get_execution_status(nonexistent_id)
        
        # Should return None gracefully
        assert status is None, "Querying non-existent execution should return None"
    
    # Feature: project-production-readiness, Property 35: Async execution and progress query
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        nonexistent_id=execution_id_strategy
    )
    def test_query_nonexistent_execution_via_api_returns_404(
        self,
        nonexistent_id,
        test_client
    ):
        """
        Feature: project-production-readiness, Property 35: Async execution and progress query
        Validates: Requirements 8.5
        
        Property: For any non-existent execution ID, the API should return 404.
        """
        # Query via API
        response = test_client.get(f"/api/v1/executions/{nonexistent_id}")
        
        # Should return 404
        assert response.status_code == 404, "API should return 404 for non-existent execution"
        
        data = response.json()
        assert "detail" in data
    
    # Feature: project-production-readiness, Property 35: Async execution and progress query
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        execution_id=execution_id_strategy
    )
    def test_concurrent_status_queries_are_consistent(
        self,
        execution_id,
        execution_manager
    ):
        """
        Feature: project-production-readiness, Property 35: Async execution and progress query
        Validates: Requirements 8.5
        
        Property: For any execution, multiple concurrent status queries should
        return consistent results.
        """
        # Create execution
        execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.AGENT,
            target_id="test_agent",
            inputs={},
            config={}
        )
        
        # Query multiple times concurrently (simulated)
        statuses = []
        for _ in range(5):
            status = execution_manager.get_execution_status(execution_id)
            statuses.append(status)
        
        # All queries should return consistent results
        assert all(s is not None for s in statuses)
        assert all(s.execution_id == execution_id for s in statuses)
        assert all(s.status == statuses[0].status for s in statuses)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
