"""
Tests for Configuration File Read/Write API

This module tests the configuration management API endpoints:
- GET /api/v1/config/agents/{agent_id}
- PUT /api/v1/config/agents/{agent_id}
- GET /api/v1/config/pipelines/{pipeline_id}
- PUT /api/v1/config/pipelines/{pipeline_id}

Requirements: 8.4
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import yaml
import tempfile
import shutil

from src.api.app import app
from src.agent_registry_v2 import AgentRegistry, AgentMetadata

client = TestClient(app)


@pytest.fixture
def temp_agent_dir(tmp_path):
    """Create a temporary agent directory with config file."""
    agent_dir = tmp_path / "agents" / "test_agent"
    agent_dir.mkdir(parents=True)
    
    # Create agent.yaml
    config = {
        "name": "Test Agent",
        "model": "doubao-pro",
        "prompts": {
            "system": "You are a test agent",
            "user": "Process: {input}"
        },
        "temperature": 0.7
    }
    
    config_file = agent_dir / "agent.yaml"
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)
    
    return agent_dir


@pytest.fixture
def temp_pipeline_dir(tmp_path):
    """Create a temporary pipeline directory with config file."""
    pipeline_dir = tmp_path / "pipelines"
    pipeline_dir.mkdir(parents=True)
    
    # Create pipeline.yaml
    config = {
        "name": "Test Pipeline",
        "description": "A test pipeline",
        "version": "1.0.0",
        "inputs": [
            {"name": "text", "desc": "Input text", "required": True}
        ],
        "outputs": [
            {"key": "result", "label": "Result"}
        ],
        "steps": [
            {
                "id": "step1",
                "type": "agent_flow",
                "agent": "test_agent",
                "flow": "default",
                "input_mapping": {"text": "text"},
                "output_key": "result"
            }
        ]
    }
    
    config_file = pipeline_dir / "test_pipeline.yaml"
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)
    
    return pipeline_dir


class TestAgentConfigAPI:
    """Test agent configuration API endpoints."""
    
    def test_get_agent_config_not_found(self):
        """Test getting config for non-existent agent."""
        response = client.get("/api/v1/config/agents/nonexistent_agent")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"] == "NotFound"
    
    def test_get_agent_config_success(self, temp_agent_dir, monkeypatch):
        """Test successfully getting agent configuration."""
        # Mock the agent registry to return our test agent
        def mock_get_agent(self, agent_id):
            if agent_id == "test_agent":
                return AgentMetadata(
                    id="test_agent",
                    name="Test Agent",
                    category="test",
                    environment="test",
                    owner="test-team",
                    version="1.0.0",
                    location=temp_agent_dir,
                    deprecated=False,
                    tags=[],
                    status="active"
                )
            raise KeyError(f"Agent {agent_id} not found")
        
        monkeypatch.setattr(AgentRegistry, "get_agent", mock_get_agent)
        
        response = client.get("/api/v1/config/agents/test_agent")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "test_agent"
        assert "config" in data
        assert data["config"]["name"] == "Test Agent"
        assert data["config"]["model"] == "doubao-pro"
        assert "prompts" in data["config"]
        assert "file_path" in data
        assert "last_modified" in data
    
    def test_update_agent_config_not_found(self):
        """Test updating config for non-existent agent."""
        response = client.put(
            "/api/v1/config/agents/nonexistent_agent",
            json={"config": {"name": "Updated"}}
        )
        assert response.status_code == 404
    
    def test_update_agent_config_invalid_data(self, temp_agent_dir, monkeypatch):
        """Test updating agent config with invalid data."""
        # Mock the agent registry
        def mock_get_agent(self, agent_id):
            if agent_id == "test_agent":
                return AgentMetadata(
                    id="test_agent",
                    name="Test Agent",
                    category="test",
                    environment="test",
                    owner="test-team",
                    version="1.0.0",
                    location=temp_agent_dir,
                    deprecated=False,
                    tags=[],
                    status="active"
                )
            raise KeyError(f"Agent {agent_id} not found")
        
        monkeypatch.setattr(AgentRegistry, "get_agent", mock_get_agent)
        
        # Send non-dict config (Pydantic will validate and return 422)
        response = client.put(
            "/api/v1/config/agents/test_agent",
            json={"config": "not a dict"}
        )
        # Pydantic validation returns 422 for invalid request body
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_update_agent_config_success(self, temp_agent_dir, monkeypatch):
        """Test successfully updating agent configuration."""
        # Mock the agent registry
        def mock_get_agent(self, agent_id):
            if agent_id == "test_agent":
                return AgentMetadata(
                    id="test_agent",
                    name="Test Agent",
                    category="test",
                    environment="test",
                    owner="test-team",
                    version="1.0.0",
                    location=temp_agent_dir,
                    deprecated=False,
                    tags=[],
                    status="active"
                )
            raise KeyError(f"Agent {agent_id} not found")
        
        monkeypatch.setattr(AgentRegistry, "get_agent", mock_get_agent)
        
        # Update config
        new_config = {
            "name": "Updated Test Agent",
            "model": "doubao-pro-32k",
            "prompts": {
                "system": "Updated system prompt",
                "user": "Updated user prompt"
            },
            "temperature": 0.9
        }
        
        response = client.put(
            "/api/v1/config/agents/test_agent",
            json={"config": new_config}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Agent configuration updated successfully"
        assert data["data"]["id"] == "test_agent"
        
        # Verify the file was updated
        config_file = temp_agent_dir / "agent.yaml"
        with open(config_file, 'r', encoding='utf-8') as f:
            saved_config = yaml.safe_load(f)
        
        assert saved_config["name"] == "Updated Test Agent"
        assert saved_config["model"] == "doubao-pro-32k"
        assert saved_config["temperature"] == 0.9


class TestPipelineConfigAPI:
    """Test pipeline configuration API endpoints."""
    
    def test_get_pipeline_config_not_found(self):
        """Test getting config for non-existent pipeline."""
        response = client.get("/api/v1/config/pipelines/nonexistent_pipeline")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert data["detail"]["error"] == "NotFound"
    
    def test_get_pipeline_config_success(self, temp_pipeline_dir, monkeypatch):
        """Test successfully getting pipeline configuration."""
        # Mock find_pipeline_config_file to return our test file
        def mock_find_pipeline_config_file(pipeline_id):
            if pipeline_id == "test_pipeline":
                return temp_pipeline_dir / "test_pipeline.yaml"
            raise FileNotFoundError(f"Pipeline {pipeline_id} not found")
        
        import src.api.routes.config as config_module
        monkeypatch.setattr(config_module, "find_pipeline_config_file", mock_find_pipeline_config_file)
        
        response = client.get("/api/v1/config/pipelines/test_pipeline")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "test_pipeline"
        assert "config" in data
        assert data["config"]["name"] == "Test Pipeline"
        assert data["config"]["version"] == "1.0.0"
        assert len(data["config"]["steps"]) == 1
        assert "file_path" in data
        assert "last_modified" in data
    
    def test_update_pipeline_config_not_found(self):
        """Test updating config for non-existent pipeline."""
        response = client.put(
            "/api/v1/config/pipelines/nonexistent_pipeline",
            json={"config": {"name": "Updated"}}
        )
        assert response.status_code == 404
    
    def test_update_pipeline_config_invalid_data(self, temp_pipeline_dir, monkeypatch):
        """Test updating pipeline config with invalid data."""
        # Mock find_pipeline_config_file
        def mock_find_pipeline_config_file(pipeline_id):
            if pipeline_id == "test_pipeline":
                return temp_pipeline_dir / "test_pipeline.yaml"
            raise FileNotFoundError(f"Pipeline {pipeline_id} not found")
        
        import src.api.routes.config as config_module
        monkeypatch.setattr(config_module, "find_pipeline_config_file", mock_find_pipeline_config_file)
        
        # Send non-dict config (Pydantic will validate and return 422)
        response = client.put(
            "/api/v1/config/pipelines/test_pipeline",
            json={"config": "not a dict"}
        )
        # Pydantic validation returns 422 for invalid request body
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    def test_update_pipeline_config_success(self, temp_pipeline_dir, monkeypatch):
        """Test successfully updating pipeline configuration."""
        # Mock find_pipeline_config_file
        def mock_find_pipeline_config_file(pipeline_id):
            if pipeline_id == "test_pipeline":
                return temp_pipeline_dir / "test_pipeline.yaml"
            raise FileNotFoundError(f"Pipeline {pipeline_id} not found")
        
        import src.api.routes.config as config_module
        monkeypatch.setattr(config_module, "find_pipeline_config_file", mock_find_pipeline_config_file)
        
        # Update config
        new_config = {
            "name": "Updated Test Pipeline",
            "description": "Updated description",
            "version": "1.1.0",
            "inputs": [
                {"name": "text", "desc": "Updated input", "required": True}
            ],
            "outputs": [
                {"key": "result", "label": "Updated Result"}
            ],
            "steps": [
                {
                    "id": "step1",
                    "type": "agent_flow",
                    "agent": "updated_agent",
                    "flow": "default",
                    "input_mapping": {"text": "text"},
                    "output_key": "result"
                }
            ]
        }
        
        response = client.put(
            "/api/v1/config/pipelines/test_pipeline",
            json={"config": new_config}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == "Pipeline configuration updated successfully"
        assert data["data"]["id"] == "test_pipeline"
        
        # Verify the file was updated
        config_file = temp_pipeline_dir / "test_pipeline.yaml"
        with open(config_file, 'r', encoding='utf-8') as f:
            saved_config = yaml.safe_load(f)
        
        assert saved_config["name"] == "Updated Test Pipeline"
        assert saved_config["version"] == "1.1.0"
        assert saved_config["description"] == "Updated description"
        assert saved_config["steps"][0]["agent"] == "updated_agent"


class TestConfigAPIIntegration:
    """Integration tests for configuration API."""
    
    def test_read_update_read_cycle(self, temp_agent_dir, monkeypatch):
        """Test reading, updating, and reading again to verify persistence."""
        # Mock the agent registry
        def mock_get_agent(self, agent_id):
            if agent_id == "test_agent":
                return AgentMetadata(
                    id="test_agent",
                    name="Test Agent",
                    category="test",
                    environment="test",
                    owner="test-team",
                    version="1.0.0",
                    location=temp_agent_dir,
                    deprecated=False,
                    tags=[],
                    status="active"
                )
            raise KeyError(f"Agent {agent_id} not found")
        
        monkeypatch.setattr(AgentRegistry, "get_agent", mock_get_agent)
        
        # Read original config
        response1 = client.get("/api/v1/config/agents/test_agent")
        assert response1.status_code == 200
        original_config = response1.json()["config"]
        
        # Update config
        updated_config = original_config.copy()
        updated_config["temperature"] = 0.5
        updated_config["new_field"] = "new_value"
        
        response2 = client.put(
            "/api/v1/config/agents/test_agent",
            json={"config": updated_config}
        )
        assert response2.status_code == 200
        
        # Read updated config
        response3 = client.get("/api/v1/config/agents/test_agent")
        assert response3.status_code == 200
        final_config = response3.json()["config"]
        
        # Verify changes persisted
        assert final_config["temperature"] == 0.5
        assert final_config["new_field"] == "new_value"
        assert final_config["name"] == original_config["name"]
