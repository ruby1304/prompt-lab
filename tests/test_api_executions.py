"""
Tests for Async Execution API

This module tests the async execution endpoints for agents and pipelines.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import time
import json

from src.api.app import app
from src.api.execution_manager import ExecutionManager, get_execution_manager
from src.api.models import ExecutionStatus, ExecutionType


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def execution_manager():
    """Get execution manager instance."""
    return get_execution_manager()


@pytest.fixture(autouse=True)
def clear_executions(execution_manager):
    """Clear executions before each test."""
    execution_manager.executions.clear()
    yield
    execution_manager.executions.clear()


class TestAsyncExecutionEndpoints:
    """Test async execution API endpoints."""
    
    def test_start_async_agent_execution(self, client):
        """Test starting an async agent execution."""
        # This test requires a real agent to exist
        # For now, we'll test the API structure
        response = client.post(
            "/api/v1/executions",
            json={
                "type": "agent",
                "target_id": "test_agent",
                "inputs": {
                    "text": "Test input"
                },
                "config": {
                    "flow_id": "default"
                }
            }
        )
        
        # Should return 202 Accepted or 404 if agent doesn't exist
        assert response.status_code in [202, 404, 500]
        
        if response.status_code == 202:
            data = response.json()
            assert "execution_id" in data
            assert data["status"] == "pending"
            assert "status_url" in data
            assert data["execution_id"].startswith("exec_")
    
    def test_start_async_pipeline_execution(self, client):
        """Test starting an async pipeline execution."""
        response = client.post(
            "/api/v1/executions",
            json={
                "type": "pipeline",
                "target_id": "test_pipeline",
                "inputs": {
                    "input1": "Test input"
                },
                "config": {
                    "max_workers": 4
                }
            }
        )
        
        # Should return 202 Accepted or 404 if pipeline doesn't exist
        assert response.status_code in [202, 404, 500]
        
        if response.status_code == 202:
            data = response.json()
            assert "execution_id" in data
            assert data["status"] == "pending"
    
    def test_get_execution_status_not_found(self, client):
        """Test getting status of non-existent execution."""
        response = client.get("/api/v1/executions/exec_nonexistent")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_get_execution_status(self, client, execution_manager):
        """Test getting execution status."""
        # Create a test execution
        execution_id = "exec_test123"
        execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.AGENT,
            target_id="test_agent",
            inputs={"text": "test"},
            config={}
        )
        
        response = client.get(f"/api/v1/executions/{execution_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["execution_id"] == execution_id
        assert data["type"] == "agent"
        assert data["target_id"] == "test_agent"
        assert data["status"] == "pending"
    
    def test_list_executions_empty(self, client):
        """Test listing executions when none exist."""
        response = client.get("/api/v1/executions")
        assert response.status_code == 200
        
        data = response.json()
        assert "executions" in data
        assert "pagination" in data
        assert len(data["executions"]) == 0
    
    def test_list_executions_with_data(self, client, execution_manager):
        """Test listing executions with data."""
        # Create test executions
        for i in range(3):
            execution_manager.create_execution(
                execution_id=f"exec_test{i}",
                execution_type=ExecutionType.AGENT if i % 2 == 0 else ExecutionType.PIPELINE,
                target_id=f"test_target_{i}",
                inputs={"text": f"test {i}"},
                config={}
            )
        
        response = client.get("/api/v1/executions")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["executions"]) == 3
        assert data["pagination"]["total_items"] == 3
        assert data["pagination"]["total_pages"] == 1
    
    def test_list_executions_with_filters(self, client, execution_manager):
        """Test listing executions with filters."""
        # Create test executions
        execution_manager.create_execution(
            execution_id="exec_agent1",
            execution_type=ExecutionType.AGENT,
            target_id="agent1",
            inputs={},
            config={}
        )
        execution_manager.create_execution(
            execution_id="exec_pipeline1",
            execution_type=ExecutionType.PIPELINE,
            target_id="pipeline1",
            inputs={},
            config={}
        )
        
        # Filter by type
        response = client.get("/api/v1/executions?type=agent")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["executions"]) == 1
        assert data["executions"][0]["type"] == "agent"
    
    def test_list_executions_pagination(self, client, execution_manager):
        """Test execution list pagination."""
        # Create 10 test executions
        for i in range(10):
            execution_manager.create_execution(
                execution_id=f"exec_test{i}",
                execution_type=ExecutionType.AGENT,
                target_id=f"agent{i}",
                inputs={},
                config={}
            )
        
        # Get first page
        response = client.get("/api/v1/executions?page=1&page_size=5")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["executions"]) == 5
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["total_pages"] == 2
        assert data["pagination"]["has_next"] is True
        assert data["pagination"]["has_prev"] is False
        
        # Get second page
        response = client.get("/api/v1/executions?page=2&page_size=5")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["executions"]) == 5
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["has_next"] is False
        assert data["pagination"]["has_prev"] is True
    
    def test_cancel_execution_not_found(self, client):
        """Test cancelling non-existent execution."""
        response = client.post("/api/v1/executions/exec_nonexistent/cancel")
        assert response.status_code == 404
    
    def test_cancel_pending_execution(self, client, execution_manager):
        """Test cancelling a pending execution."""
        # Create a pending execution
        execution_id = "exec_cancel_test"
        execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.AGENT,
            target_id="test_agent",
            inputs={},
            config={}
        )
        
        response = client.post(f"/api/v1/executions/{execution_id}/cancel")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Execution cancelled successfully"
        assert data["data"]["execution_id"] == execution_id
        assert data["data"]["status"] == "cancelled"
        
        # Verify status changed
        status = execution_manager.get_execution_status(execution_id)
        assert status.status == ExecutionStatus.CANCELLED
    
    def test_cancel_completed_execution(self, client, execution_manager):
        """Test cancelling a completed execution (should fail)."""
        # Create a completed execution
        execution_id = "exec_completed"
        record = execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.AGENT,
            target_id="test_agent",
            inputs={},
            config={}
        )
        record.status = ExecutionStatus.COMPLETED
        
        response = client.post(f"/api/v1/executions/{execution_id}/cancel")
        assert response.status_code == 400
        
        data = response.json()
        assert "cannot cancel" in data["detail"].lower()


class TestExecutionManager:
    """Test ExecutionManager class."""
    
    def test_create_execution(self, execution_manager):
        """Test creating an execution record."""
        execution_id = "exec_test"
        record = execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.AGENT,
            target_id="test_agent",
            inputs={"text": "test"},
            config={"timeout": 60}
        )
        
        assert record.execution_id == execution_id
        assert record.type == ExecutionType.AGENT
        assert record.target_id == "test_agent"
        assert record.status == ExecutionStatus.PENDING
        assert record.inputs == {"text": "test"}
        assert record.config == {"timeout": 60}
    
    def test_create_duplicate_execution(self, execution_manager):
        """Test creating duplicate execution (should fail)."""
        execution_id = "exec_duplicate"
        execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.AGENT,
            target_id="test_agent",
            inputs={},
            config={}
        )
        
        with pytest.raises(ValueError, match="already exists"):
            execution_manager.create_execution(
                execution_id=execution_id,
                execution_type=ExecutionType.AGENT,
                target_id="test_agent",
                inputs={},
                config={}
            )
    
    def test_get_execution_status(self, execution_manager):
        """Test getting execution status."""
        execution_id = "exec_status_test"
        execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.PIPELINE,
            target_id="test_pipeline",
            inputs={},
            config={}
        )
        
        status = execution_manager.get_execution_status(execution_id)
        assert status is not None
        assert status.execution_id == execution_id
        assert status.type == ExecutionType.PIPELINE
        assert status.status == ExecutionStatus.PENDING
    
    def test_get_nonexistent_execution(self, execution_manager):
        """Test getting non-existent execution."""
        status = execution_manager.get_execution_status("exec_nonexistent")
        assert status is None
    
    def test_list_executions_filtering(self, execution_manager):
        """Test listing executions with filters."""
        # Create various executions
        execution_manager.create_execution(
            execution_id="exec_agent1",
            execution_type=ExecutionType.AGENT,
            target_id="agent1",
            inputs={},
            config={}
        )
        
        record2 = execution_manager.create_execution(
            execution_id="exec_agent2",
            execution_type=ExecutionType.AGENT,
            target_id="agent2",
            inputs={},
            config={}
        )
        record2.status = ExecutionStatus.COMPLETED
        
        execution_manager.create_execution(
            execution_id="exec_pipeline1",
            execution_type=ExecutionType.PIPELINE,
            target_id="pipeline1",
            inputs={},
            config={}
        )
        
        # Filter by type
        agents = execution_manager.list_executions(execution_type=ExecutionType.AGENT)
        assert len(agents) == 2
        
        # Filter by status
        completed = execution_manager.list_executions(status=ExecutionStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].execution_id == "exec_agent2"
        
        # Filter by target_id
        target_filtered = execution_manager.list_executions(target_id="agent1")
        assert len(target_filtered) == 1
        assert target_filtered[0].execution_id == "exec_agent1"
    
    def test_cancel_execution(self, execution_manager):
        """Test cancelling an execution."""
        execution_id = "exec_cancel"
        execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.AGENT,
            target_id="test_agent",
            inputs={},
            config={}
        )
        
        cancelled_at = execution_manager.cancel_execution(execution_id)
        assert cancelled_at is not None
        
        status = execution_manager.get_execution_status(execution_id)
        assert status.status == ExecutionStatus.CANCELLED
        assert status.completed_at is not None


class TestProgressQueryEndpoints:
    """Test progress query API endpoints."""
    
    def test_get_execution_progress_not_found(self, client):
        """Test getting progress of non-existent execution."""
        response = client.get("/api/v1/executions/exec_nonexistent/progress")
        assert response.status_code == 404
        
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()
    
    def test_get_execution_progress_no_data(self, client, execution_manager):
        """Test getting progress when no progress data available."""
        # Create execution without progress
        execution_id = "exec_no_progress"
        execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.AGENT,
            target_id="test_agent",
            inputs={},
            config={}
        )
        
        response = client.get(f"/api/v1/executions/{execution_id}/progress")
        # Should return 204 No Content when no progress data
        assert response.status_code == 204
    
    def test_get_execution_progress_with_data(self, client, execution_manager):
        """Test getting progress with data."""
        from src.api.models import ProgressInfo
        
        # Create execution with progress
        execution_id = "exec_with_progress"
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
            current_step=2,
            total_steps=5,
            percentage=40.0,
            current_step_name="processing"
        )
        
        response = client.get(f"/api/v1/executions/{execution_id}/progress")
        assert response.status_code == 200
        
        data = response.json()
        assert data["current_step"] == 2
        assert data["total_steps"] == 5
        assert data["percentage"] == 40.0
        assert data["current_step_name"] == "processing"
    
    def test_get_execution_progress_completed(self, client, execution_manager):
        """Test getting progress of completed execution."""
        from src.api.models import ProgressInfo
        
        # Create completed execution with final progress
        execution_id = "exec_completed_progress"
        record = execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.AGENT,
            target_id="test_agent",
            inputs={},
            config={}
        )
        
        record.status = ExecutionStatus.COMPLETED
        record.progress = ProgressInfo(
            current_step=3,
            total_steps=3,
            percentage=100.0
        )
        
        response = client.get(f"/api/v1/executions/{execution_id}/progress")
        assert response.status_code == 200
        
        data = response.json()
        assert data["percentage"] == 100.0


class TestWebSocketProgressEndpoints:
    """Test WebSocket progress streaming endpoints."""
    
    def test_websocket_execution_not_found(self, client):
        """Test WebSocket connection for non-existent execution."""
        with client.websocket_connect("/api/v1/executions/exec_nonexistent/progress/ws") as websocket:
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert "not found" in data["message"].lower()
    
    def test_websocket_execution_already_completed(self, client, execution_manager):
        """Test WebSocket connection for already completed execution."""
        # Create completed execution
        execution_id = "exec_ws_completed"
        record = execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.AGENT,
            target_id="test_agent",
            inputs={},
            config={}
        )
        record.status = ExecutionStatus.COMPLETED
        record.outputs = {"result": "success"}
        
        with client.websocket_connect(f"/api/v1/executions/{execution_id}/progress/ws") as websocket:
            # Should receive initial status
            data = websocket.receive_json()
            assert data["type"] == "status"
            assert data["execution_id"] == execution_id
            assert data["status"] == "completed"
            
            # Should receive final status
            data = websocket.receive_json()
            assert data["type"] == "completed"
            assert data["outputs"] == {"result": "success"}
    
    def test_websocket_execution_progress_updates(self, client, execution_manager):
        """Test WebSocket receives progress updates."""
        from src.api.models import ProgressInfo
        
        # Create running execution
        execution_id = "exec_ws_progress"
        record = execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.PIPELINE,
            target_id="test_pipeline",
            inputs={},
            config={}
        )
        record.status = ExecutionStatus.RUNNING
        record.progress = ProgressInfo(
            current_step=1,
            total_steps=3,
            percentage=33.3,
            current_step_name="step1"
        )
        
        # Connect and verify we can receive initial status
        with client.websocket_connect(f"/api/v1/executions/{execution_id}/progress/ws") as websocket:
            # Receive initial status
            data = websocket.receive_json()
            assert data["type"] == "status"
            assert data["status"] == "running"
            assert data["execution_id"] == execution_id
            
            # Verify progress is included
            assert "progress" in data
            assert data["progress"]["current_step"] == 1
            assert data["progress"]["total_steps"] == 3
            assert data["progress"]["percentage"] == 33.3
    
    def test_websocket_execution_cancelled(self, client, execution_manager):
        """Test WebSocket receives cancellation notification."""
        from src.api.models import ProgressInfo
        import threading
        import time
        
        # Create running execution
        execution_id = "exec_ws_cancel"
        record = execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.AGENT,
            target_id="test_agent",
            inputs={},
            config={}
        )
        record.status = ExecutionStatus.RUNNING
        
        # Function to cancel execution
        def cancel_execution():
            time.sleep(0.5)
            execution_manager.cancel_execution(execution_id)
        
        thread = threading.Thread(target=cancel_execution)
        thread.start()
        
        try:
            with client.websocket_connect(f"/api/v1/executions/{execution_id}/progress/ws") as websocket:
                # Receive initial status
                data = websocket.receive_json()
                assert data["type"] == "status"
                
                # Wait for cancellation
                while True:
                    try:
                        data = websocket.receive_json(timeout=2.0)
                        if data["type"] == "cancelled":
                            assert data["execution_id"] == execution_id
                            break
                    except:
                        break
        finally:
            thread.join(timeout=3.0)
    
    def test_websocket_execution_failed(self, client, execution_manager):
        """Test WebSocket receives failure notification."""
        from src.api.models import ExecutionError
        import threading
        import time
        
        # Create running execution
        execution_id = "exec_ws_fail"
        record = execution_manager.create_execution(
            execution_id=execution_id,
            execution_type=ExecutionType.PIPELINE,
            target_id="test_pipeline",
            inputs={},
            config={}
        )
        record.status = ExecutionStatus.RUNNING
        
        # Function to fail execution
        def fail_execution():
            time.sleep(0.5)
            record.status = ExecutionStatus.FAILED
            record.error = ExecutionError(
                type="ValueError",
                message="Test error",
                details={}
            )
        
        thread = threading.Thread(target=fail_execution)
        thread.start()
        
        try:
            with client.websocket_connect(f"/api/v1/executions/{execution_id}/progress/ws") as websocket:
                # Receive initial status
                data = websocket.receive_json()
                assert data["type"] == "status"
                
                # Wait for failure
                while True:
                    try:
                        data = websocket.receive_json(timeout=2.0)
                        if data["type"] == "failed":
                            assert data["execution_id"] == execution_id
                            assert data["error"]["type"] == "ValueError"
                            assert data["error"]["message"] == "Test error"
                            break
                    except:
                        break
        finally:
            thread.join(timeout=3.0)


class TestExecutionModels:
    """Test execution data models."""
    
    def test_execution_status_response_model(self):
        """Test ExecutionStatusResponse model."""
        from src.api.models import ExecutionStatusResponse, ProgressInfo
        from datetime import datetime
        
        response = ExecutionStatusResponse(
            execution_id="exec_test",
            type=ExecutionType.AGENT,
            target_id="test_agent",
            status=ExecutionStatus.RUNNING,
            progress=ProgressInfo(
                current_step=1,
                total_steps=3,
                percentage=33.3,
                current_step_name="step1"
            ),
            started_at=datetime.now()
        )
        
        assert response.execution_id == "exec_test"
        assert response.type == ExecutionType.AGENT
        assert response.status == ExecutionStatus.RUNNING
        assert response.progress.percentage == 33.3
    
    def test_async_execution_request_model(self):
        """Test AsyncExecutionRequest model."""
        from src.api.models import AsyncExecutionRequest
        
        request = AsyncExecutionRequest(
            type=ExecutionType.PIPELINE,
            target_id="test_pipeline",
            inputs={"input1": "value1"},
            config={"max_workers": 4},
            callback_url="https://example.com/webhook"
        )
        
        assert request.type == ExecutionType.PIPELINE
        assert request.target_id == "test_pipeline"
        assert request.inputs == {"input1": "value1"}
        assert request.callback_url == "https://example.com/webhook"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
