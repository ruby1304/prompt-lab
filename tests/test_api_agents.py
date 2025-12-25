"""
Tests for Agent Management API Routes

This module tests the agent management API endpoints:
- GET /api/v1/agents - List agents
- GET /api/v1/agents/{agent_id} - Get agent details
- POST /api/v1/agents - Create agent
- PUT /api/v1/agents/{agent_id} - Update agent
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import yaml

from src.api.app import create_app
from src.agent_registry_v2 import AgentRegistry


@pytest.fixture
def test_registry_config():
    """Create a temporary registry config for testing."""
    config = {
        "version": "1.0",
        "agents": {
            "test_agent_1": {
                "name": "Test Agent 1",
                "category": "test",
                "environment": "test",
                "owner": "test-team",
                "version": "1.0.0",
                "location": "agents/test_agent_1",
                "deprecated": False,
                "status": "active",
                "tags": ["test", "example"],
                "description": "A test agent"
            },
            "test_agent_2": {
                "name": "Test Agent 2",
                "category": "production",
                "environment": "production",
                "owner": "prod-team",
                "version": "2.0.0",
                "location": "agents/test_agent_2",
                "deprecated": False,
                "status": "active",
                "tags": ["production"],
                "description": "A production agent"
            }
        }
    }
    
    # Create temporary config file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        config_path = Path(f.name)
    
    yield config_path
    
    # Cleanup
    config_path.unlink()


@pytest.fixture
def test_registry_instance(test_registry_config):
    """Create a single registry instance for the test."""
    return AgentRegistry(test_registry_config, enable_hot_reload=False)


@pytest.fixture
def app_with_test_registry(test_registry_instance):
    """Create an app with a test registry."""
    # Override the get_agent_registry dependency
    from src.api.dependencies import get_agent_registry
    
    def override_get_agent_registry():
        return test_registry_instance
    
    app = create_app()
    app.dependency_overrides[get_agent_registry] = override_get_agent_registry
    
    return app


@pytest.fixture
def client(app_with_test_registry):
    """Create a test client."""
    from starlette.testclient import TestClient as StarletteTestClient
    return StarletteTestClient(app_with_test_registry)


class TestListAgents:
    """Tests for GET /api/v1/agents endpoint."""
    
    def test_list_all_agents(self, client):
        """Test listing all agents."""
        response = client.get("/api/v1/agents")
        assert response.status_code == 200
        
        data = response.json()
        assert "agents" in data
        assert "pagination" in data
        assert len(data["agents"]) == 2
        
        # Check pagination
        pagination = data["pagination"]
        assert pagination["page"] == 1
        assert pagination["total_items"] == 2
        assert pagination["has_next"] is False
        assert pagination["has_prev"] is False
    
    def test_list_agents_with_pagination(self, client):
        """Test listing agents with pagination."""
        response = client.get("/api/v1/agents?page=1&page_size=1")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["agents"]) == 1
        
        pagination = data["pagination"]
        assert pagination["page"] == 1
        assert pagination["page_size"] == 1
        assert pagination["total_items"] == 2
        assert pagination["total_pages"] == 2
        assert pagination["has_next"] is True
        assert pagination["has_prev"] is False
    
    def test_filter_by_category(self, client):
        """Test filtering agents by category."""
        response = client.get("/api/v1/agents?category=production")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["agents"]) == 1
        assert data["agents"][0]["id"] == "test_agent_2"
        assert data["agents"][0]["category"] == "production"
    
    def test_filter_by_tags(self, client):
        """Test filtering agents by tags."""
        response = client.get("/api/v1/agents?tags=test")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["agents"]) == 1
        assert data["agents"][0]["id"] == "test_agent_1"
        assert "test" in data["agents"][0]["tags"]
    
    def test_search_agents(self, client):
        """Test searching agents."""
        response = client.get("/api/v1/agents?search=production")
        assert response.status_code == 200
        
        data = response.json()
        # Should find test_agent_2 (has "production" in description or category)
        assert len(data["agents"]) >= 1


class TestGetAgent:
    """Tests for GET /api/v1/agents/{agent_id} endpoint."""
    
    def test_get_existing_agent(self, client):
        """Test getting an existing agent."""
        response = client.get("/api/v1/agents/test_agent_1")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "test_agent_1"
        assert data["name"] == "Test Agent 1"
        assert data["category"] == "test"
        assert data["version"] == "1.0.0"
        assert data["description"] == "A test agent"
        assert "test" in data["tags"]
    
    def test_get_nonexistent_agent(self, client):
        """Test getting a non-existent agent."""
        response = client.get("/api/v1/agents/nonexistent_agent")
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"]["error"] == "NotFound"
        assert "nonexistent_agent" in data["detail"]["message"]


class TestCreateAgent:
    """Tests for POST /api/v1/agents endpoint."""
    
    def test_create_new_agent(self, client):
        """Test creating a new agent."""
        new_agent = {
            "id": "new_test_agent",
            "name": "New Test Agent",
            "category": "test",
            "environment": "test",
            "owner": "test-team",
            "version": "1.0.0",
            "location": "agents/new_test_agent",
            "description": "A newly created agent",
            "tags": ["new", "test"]
        }
        
        response = client.post("/api/v1/agents", json=new_agent)
        assert response.status_code == 201
        
        data = response.json()
        assert data["id"] == "new_test_agent"
        assert data["name"] == "New Test Agent"
        assert data["status"] == "active"
        assert data["deprecated"] is False
    
    def test_create_duplicate_agent(self, client):
        """Test creating an agent that already exists."""
        duplicate_agent = {
            "id": "test_agent_1",  # Already exists
            "name": "Duplicate Agent",
            "category": "test",
            "environment": "test",
            "owner": "test-team",
            "version": "1.0.0",
            "location": "agents/duplicate"
        }
        
        response = client.post("/api/v1/agents", json=duplicate_agent)
        assert response.status_code == 409
        
        data = response.json()
        assert data["detail"]["error"] == "Conflict"
        assert "test_agent_1" in data["detail"]["message"]


class TestUpdateAgent:
    """Tests for PUT /api/v1/agents/{agent_id} endpoint."""
    
    def test_update_existing_agent(self, client):
        """Test updating an existing agent."""
        update_data = {
            "version": "1.1.0",
            "description": "Updated description",
            "tags": ["test", "updated"]
        }
        
        response = client.put("/api/v1/agents/test_agent_1", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == "test_agent_1"
        assert data["version"] == "1.1.0"
        assert data["description"] == "Updated description"
        assert "updated" in data["tags"]
    
    def test_update_nonexistent_agent(self, client):
        """Test updating a non-existent agent."""
        update_data = {
            "version": "2.0.0"
        }
        
        response = client.put("/api/v1/agents/nonexistent_agent", json=update_data)
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"]["error"] == "NotFound"
    
    def test_partial_update(self, client):
        """Test partial update (only some fields)."""
        update_data = {
            "version": "1.2.0"
        }
        
        response = client.put("/api/v1/agents/test_agent_1", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["version"] == "1.2.0"
        # Other fields should remain unchanged
        assert data["name"] == "Test Agent 1"
        assert data["owner"] == "test-team"


class TestAgentAPIIntegration:
    """Integration tests for agent API."""
    
    def test_create_and_list_agent(self, client):
        """Test creating an agent and then listing it."""
        # Create agent
        new_agent = {
            "id": "integration_test_agent",
            "name": "Integration Test Agent",
            "category": "test",
            "environment": "test",
            "owner": "test-team",
            "version": "1.0.0",
            "location": "agents/integration_test"
        }
        
        create_response = client.post("/api/v1/agents", json=new_agent)
        assert create_response.status_code == 201
        
        # List agents and verify the new one is included
        list_response = client.get("/api/v1/agents")
        assert list_response.status_code == 200
        
        data = list_response.json()
        agent_ids = [agent["id"] for agent in data["agents"]]
        assert "integration_test_agent" in agent_ids
    
    def test_update_existing_agent_from_registry(self, client):
        """Test updating an agent that exists in the registry."""
        # Update an existing agent from the test registry
        update_data = {
            "version": "2.0.0",
            "description": "Updated via API"
        }
        
        update_response = client.put("/api/v1/agents/test_agent_1", json=update_data)
        assert update_response.status_code == 200
        
        # Retrieve and verify
        get_response = client.get("/api/v1/agents/test_agent_1")
        assert get_response.status_code == 200
        
        data = get_response.json()
        assert data["version"] == "2.0.0"
        assert data["description"] == "Updated via API"
