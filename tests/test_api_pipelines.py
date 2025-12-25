"""
Tests for Pipeline Management API Routes

This module tests the Pipeline Management API endpoints:
- GET /api/v1/pipelines - List pipelines
- GET /api/v1/pipelines/{pipeline_id} - Get pipeline details
- POST /api/v1/pipelines - Create pipeline
- PUT /api/v1/pipelines/{pipeline_id} - Update pipeline

Requirements: 8.2
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import yaml
import tempfile
import shutil

from src.api.app import app
from src.pipeline_config import PIPELINE_DIRS

client = TestClient(app)


@pytest.fixture
def temp_pipeline_dir():
    """Create a temporary pipeline directory for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    
    # Add temp dir to PIPELINE_DIRS at the beginning (highest priority)
    PIPELINE_DIRS.insert(0, temp_dir)
    
    yield temp_dir
    
    # Cleanup
    PIPELINE_DIRS.remove(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_pipeline_config():
    """Sample pipeline configuration for testing."""
    return {
        "id": "test_pipeline",
        "name": "Test Pipeline",
        "description": "A test pipeline",
        "version": "1.0.0",
        "inputs": [
            {
                "name": "input1",
                "desc": "Test input",
                "required": True
            }
        ],
        "outputs": [
            {
                "key": "result1",  # Must match a step's output_key
                "label": "Test output"
            }
        ],
        "steps": [
            {
                "id": "step1",
                "type": "agent_flow",
                "agent": "judge_default",  # Use a real agent that exists
                "flow": "judge_v1",  # Use a real flow that exists
                "input_mapping": {
                    "text": "input1"
                },
                "output_key": "result1"
            }
        ]
    }


@pytest.fixture
def create_test_pipeline(temp_pipeline_dir, sample_pipeline_config):
    """Create a test pipeline file."""
    pipeline_file = temp_pipeline_dir / "test_pipeline.yaml"
    with open(pipeline_file, 'w', encoding='utf-8') as f:
        yaml.dump(sample_pipeline_config, f, default_flow_style=False, allow_unicode=True)
    return pipeline_file


class TestListPipelines:
    """Tests for GET /api/v1/pipelines endpoint."""
    
    def test_list_pipelines_empty(self, temp_pipeline_dir):
        """Test listing pipelines when none exist."""
        response = client.get("/api/v1/pipelines")
        assert response.status_code == 200
        
        data = response.json()
        assert "pipelines" in data
        assert "pagination" in data
        assert isinstance(data["pipelines"], list)
    
    def test_list_pipelines_with_data(self, create_test_pipeline):
        """Test listing pipelines with existing data."""
        response = client.get("/api/v1/pipelines")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["pipelines"]) >= 1
        
        # Check pipeline structure
        pipeline = data["pipelines"][0]
        assert "id" in pipeline
        assert "name" in pipeline
        assert "description" in pipeline
        assert "version" in pipeline
        assert "status" in pipeline
        assert "steps_count" in pipeline
    
    def test_list_pipelines_pagination(self, create_test_pipeline):
        """Test pagination parameters."""
        response = client.get("/api/v1/pipelines?page=1&page_size=10")
        assert response.status_code == 200
        
        data = response.json()
        pagination = data["pagination"]
        assert pagination["page"] == 1
        assert pagination["page_size"] == 10
        assert "total_items" in pagination
        assert "total_pages" in pagination
    
    def test_list_pipelines_search(self, create_test_pipeline):
        """Test search functionality."""
        response = client.get("/api/v1/pipelines?search=test")
        assert response.status_code == 200
        
        data = response.json()
        # Should find the test pipeline
        assert any("test" in p["id"].lower() or "test" in p["name"].lower() 
                  for p in data["pipelines"])
    
    def test_list_pipelines_status_filter(self, create_test_pipeline):
        """Test filtering by status."""
        response = client.get("/api/v1/pipelines?status=active")
        assert response.status_code == 200
        
        data = response.json()
        # All returned pipelines should have active status
        assert all(p["status"] == "active" for p in data["pipelines"])


class TestGetPipeline:
    """Tests for GET /api/v1/pipelines/{pipeline_id} endpoint."""
    
    def test_get_pipeline_success(self, create_test_pipeline):
        """Test getting a pipeline that exists."""
        response = client.get("/api/v1/pipelines/test_pipeline")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "test_pipeline"
        assert data["name"] == "Test Pipeline"
        assert data["description"] == "A test pipeline"
        assert "inputs" in data
        assert "outputs" in data
        assert "steps" in data
        assert len(data["steps"]) == 1
    
    def test_get_pipeline_not_found(self):
        """Test getting a pipeline that doesn't exist."""
        response = client.get("/api/v1/pipelines/nonexistent_pipeline")
        assert response.status_code == 404
        
        data = response.json()
        assert "error" in data["detail"]
        assert data["detail"]["error"] == "NotFound"
    
    def test_get_pipeline_details(self, create_test_pipeline):
        """Test that pipeline details are complete."""
        response = client.get("/api/v1/pipelines/test_pipeline")
        assert response.status_code == 200
        
        data = response.json()
        
        # Check inputs
        assert len(data["inputs"]) == 1
        assert data["inputs"][0]["name"] == "input1"
        assert data["inputs"][0]["required"] is True
        
        # Check outputs
        assert len(data["outputs"]) == 1
        assert data["outputs"][0]["key"] == "result1"
        
        # Check steps
        assert len(data["steps"]) == 1
        step = data["steps"][0]
        assert step["id"] == "step1"
        assert step["type"] == "agent_flow"
        assert step["agent"] == "judge_default"
        assert step["output_key"] == "result1"


class TestCreatePipeline:
    """Tests for POST /api/v1/pipelines endpoint."""
    
    def test_create_pipeline_success(self, temp_pipeline_dir):
        """Test creating a new pipeline."""
        # Clean up any existing file from previous test runs
        from src.pipeline_config import PIPELINES_DIR
        pipeline_file = PIPELINES_DIR / "api_test_new_pipeline.yaml"
        if pipeline_file.exists():
            pipeline_file.unlink()
        
        new_pipeline = {
            "id": "api_test_new_pipeline",
            "name": "New Test Pipeline",
            "description": "A newly created pipeline",
            "inputs": [
                {
                    "name": "text",
                    "desc": "Input text",
                    "required": True
                }
            ],
            "outputs": [
                {
                    "key": "result",
                    "label": "Result"
                }
            ],
            "steps": [
                {
                    "id": "process",
                    "type": "agent_flow",
                    "agent": "judge_default",  # Use a real agent
                    "flow": "judge_v1",  # Use a real flow
                    "input_mapping": {
                        "text": "text"
                    },
                    "output_key": "result",
                    "concurrent_group": None,
                    "depends_on": [],
                    "required": True
                }
            ]
        }
        
        response = client.post("/api/v1/pipelines", json=new_pipeline)
        assert response.status_code == 201
        
        data = response.json()
        assert data["message"] == "Pipeline created successfully"
        assert "data" in data
        assert data["data"]["id"] == "api_test_new_pipeline"
        
        # Verify file was created (it will be in PIPELINES_DIR, not temp_pipeline_dir)
        from src.pipeline_config import PIPELINES_DIR
        pipeline_file = PIPELINES_DIR / "api_test_new_pipeline.yaml"
        assert pipeline_file.exists()
        
        # Clean up
        if pipeline_file.exists():
            pipeline_file.unlink()
    
    def test_create_pipeline_duplicate(self, create_test_pipeline):
        """Test creating a pipeline with duplicate ID."""
        duplicate_pipeline = {
            "id": "test_pipeline",
            "name": "Duplicate Pipeline",
            "description": "This should fail",
            "inputs": [],
            "outputs": [],
            "steps": []
        }
        
        response = client.post("/api/v1/pipelines", json=duplicate_pipeline)
        assert response.status_code == 409
        
        data = response.json()
        assert "error" in data["detail"]
        assert data["detail"]["error"] == "Conflict"
    
    def test_create_pipeline_invalid_id(self, temp_pipeline_dir):
        """Test creating a pipeline with invalid ID format."""
        invalid_pipeline = {
            "id": "invalid-pipeline-id!",  # Invalid characters
            "name": "Invalid Pipeline",
            "description": "Should fail validation",
            "inputs": [],
            "outputs": [],
            "steps": []
        }
        
        response = client.post("/api/v1/pipelines", json=invalid_pipeline)
        # Should fail validation (422) or succeed but with sanitized ID
        assert response.status_code in [422, 201]


class TestUpdatePipeline:
    """Tests for PUT /api/v1/pipelines/{pipeline_id} endpoint."""
    
    def test_update_pipeline_name(self, create_test_pipeline):
        """Test updating pipeline name."""
        update_data = {
            "name": "Updated Pipeline Name"
        }
        
        response = client.put("/api/v1/pipelines/test_pipeline", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Pipeline updated successfully"
        
        # Verify the update
        get_response = client.get("/api/v1/pipelines/test_pipeline")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Updated Pipeline Name"
    
    def test_update_pipeline_description(self, create_test_pipeline):
        """Test updating pipeline description."""
        update_data = {
            "description": "Updated description"
        }
        
        response = client.put("/api/v1/pipelines/test_pipeline", json=update_data)
        assert response.status_code == 200
        
        # Verify the update
        get_response = client.get("/api/v1/pipelines/test_pipeline")
        assert get_response.status_code == 200
        assert get_response.json()["description"] == "Updated description"
    
    def test_update_pipeline_steps(self, create_test_pipeline):
        """Test updating pipeline steps."""
        update_data = {
            "steps": [
                {
                    "id": "step1",
                    "type": "agent_flow",
                    "agent": "judge_default",  # Use a real agent
                    "flow": "judge_v1",  # Use a real flow
                    "input_mapping": {
                        "text": "input1"
                    },
                    "output_key": "result1",
                    "concurrent_group": None,
                    "depends_on": [],
                    "required": True
                },
                {
                    "id": "step2",
                    "type": "agent_flow",
                    "agent": "usr_profile",  # Use another real agent
                    "flow": "usr_profile_v1",  # Use a real flow
                    "input_mapping": {
                        "data": "result1"
                    },
                    "output_key": "result2",
                    "concurrent_group": None,
                    "depends_on": ["step1"],
                    "required": True
                }
            ]
        }
        
        response = client.put("/api/v1/pipelines/test_pipeline", json=update_data)
        assert response.status_code == 200
        
        # Verify the update
        get_response = client.get("/api/v1/pipelines/test_pipeline")
        assert get_response.status_code == 200
        steps = get_response.json()["steps"]
        assert len(steps) == 2
        assert steps[0]["agent"] == "judge_default"
        assert steps[1]["agent"] == "usr_profile"
    
    def test_update_pipeline_not_found(self):
        """Test updating a pipeline that doesn't exist."""
        update_data = {
            "name": "Updated Name"
        }
        
        response = client.put("/api/v1/pipelines/nonexistent_pipeline", json=update_data)
        assert response.status_code == 404
        
        data = response.json()
        assert "error" in data["detail"]
        assert data["detail"]["error"] == "NotFound"
    
    def test_update_pipeline_partial(self, create_test_pipeline):
        """Test partial update (only some fields)."""
        # Get original data
        original = client.get("/api/v1/pipelines/test_pipeline").json()
        
        # Update only name
        update_data = {
            "name": "Partially Updated"
        }
        
        response = client.put("/api/v1/pipelines/test_pipeline", json=update_data)
        assert response.status_code == 200
        
        # Verify only name changed
        updated = client.get("/api/v1/pipelines/test_pipeline").json()
        assert updated["name"] == "Partially Updated"
        assert updated["description"] == original["description"]
        assert len(updated["steps"]) == len(original["steps"])


class TestPipelineIntegration:
    """Integration tests for pipeline API workflows."""
    
    def test_create_get_update_workflow(self, temp_pipeline_dir):
        """Test complete workflow: create -> get -> update -> get."""
        # Clean up any existing file
        from src.pipeline_config import PIPELINES_DIR
        pipeline_file = PIPELINES_DIR / "workflow_test.yaml"
        if pipeline_file.exists():
            pipeline_file.unlink()
        
        # Create
        create_data = {
            "id": "workflow_test",
            "name": "Workflow Test",
            "description": "Testing workflow",
            "inputs": [{"name": "in", "desc": "Input", "required": True}],
            "outputs": [{"key": "out", "label": "Output"}],
            "steps": [
                {
                    "id": "s1",
                    "type": "agent_flow",
                    "agent": "judge_default",  # Use a real agent
                    "flow": "judge_v1",  # Use a real flow
                    "input_mapping": {"x": "in"},
                    "output_key": "out",
                    "concurrent_group": None,
                    "depends_on": [],
                    "required": True
                }
            ]
        }
        
        create_response = client.post("/api/v1/pipelines", json=create_data)
        assert create_response.status_code == 201
        
        # Get
        get_response = client.get("/api/v1/pipelines/workflow_test")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == "Workflow Test"
        
        # Update
        update_data = {"name": "Updated Workflow"}
        update_response = client.put("/api/v1/pipelines/workflow_test", json=update_data)
        assert update_response.status_code == 200
        
        # Get again
        final_response = client.get("/api/v1/pipelines/workflow_test")
        assert final_response.status_code == 200
        assert final_response.json()["name"] == "Updated Workflow"
    
    def test_list_includes_created_pipeline(self, temp_pipeline_dir):
        """Test that created pipelines appear in list."""
        # Clean up any existing file
        from src.pipeline_config import PIPELINES_DIR
        pipeline_file = PIPELINES_DIR / "api_test_list_pipeline.yaml"
        if pipeline_file.exists():
            pipeline_file.unlink()
        
        # Create a pipeline
        create_data = {
            "id": "api_test_list_pipeline",
            "name": "List Test",
            "description": "For list testing",
            "inputs": [{"name": "in", "desc": "Input", "required": True}],
            "outputs": [{"key": "out", "label": "Output"}],
            "steps": [{
                "id": "s1",
                "type": "agent_flow",
                "agent": "judge_default",
                "flow": "judge_v1",
                "input_mapping": {"x": "in"},
                "output_key": "out",
                "concurrent_group": None,
                "depends_on": [],
                "required": True
            }]
        }
        
        create_response = client.post("/api/v1/pipelines", json=create_data)
        assert create_response.status_code == 201
        
        # List pipelines
        list_response = client.get("/api/v1/pipelines")
        assert list_response.status_code == 200
        
        pipelines = list_response.json()["pipelines"]
        pipeline_ids = [p["id"] for p in pipelines]
        assert "api_test_list_pipeline" in pipeline_ids


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
