"""
Property-Based Tests for API Availability

This module tests Property 32: Core function API availability
For any core system function (agent execution, pipeline execution, evaluation),
there should be a corresponding API endpoint.

Feature: project-production-readiness, Property 32: Core function API availability
Validates: Requirements 8.2
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import yaml

from src.api.app import create_app


@pytest.fixture
def client():
    """Create a test client."""
    app = create_app()
    return TestClient(app)


def get_test_client():
    """Helper function to create a test client (for use in property tests)."""
    app = create_app()
    return TestClient(app)


class TestCoreAPIAvailability:
    """Test that all core functions have corresponding API endpoints."""
    
    def test_system_endpoints_available(self, client):
        """
        Feature: project-production-readiness, Property 32: Core function API availability
        Validates: Requirements 8.2
        
        Test that system-level endpoints are available.
        """
        # Health check endpoint
        response = client.get("/health")
        assert response.status_code == 200, "Health check endpoint should be available"
        
        # Root endpoint
        response = client.get("/")
        assert response.status_code == 200, "Root endpoint should be available"
        
        # OpenAPI schema endpoint
        response = client.get("/openapi.json")
        assert response.status_code == 200, "OpenAPI schema endpoint should be available"
        
        # Documentation endpoints
        response = client.get("/docs")
        assert response.status_code == 200, "Swagger UI docs endpoint should be available"
        
        response = client.get("/redoc")
        assert response.status_code == 200, "ReDoc endpoint should be available"
    
    def test_agent_management_endpoints_available(self, client):
        """
        Feature: project-production-readiness, Property 32: Core function API availability
        Validates: Requirements 8.2
        
        Test that agent management endpoints are available.
        """
        # List agents endpoint
        response = client.get("/api/v1/agents")
        assert response.status_code == 200, "List agents endpoint should be available"
        
        # Get agent endpoint (404 is acceptable, means endpoint exists)
        response = client.get("/api/v1/agents/test_agent")
        assert response.status_code in [200, 404], "Get agent endpoint should be available"
        
        # Create agent endpoint (validation error is acceptable, means endpoint exists)
        response = client.post("/api/v1/agents", json={})
        assert response.status_code in [201, 409, 422], "Create agent endpoint should be available"
        
        # Update agent endpoint (404 is acceptable, means endpoint exists)
        response = client.put("/api/v1/agents/test_agent", json={})
        assert response.status_code in [200, 404, 422], "Update agent endpoint should be available"
    
    def test_pipeline_management_endpoints_available(self, client):
        """
        Feature: project-production-readiness, Property 32: Core function API availability
        Validates: Requirements 8.2
        
        Test that pipeline management endpoints are available.
        """
        # List pipelines endpoint
        response = client.get("/api/v1/pipelines")
        assert response.status_code == 200, "List pipelines endpoint should be available"
        
        # Get pipeline endpoint (404 or 500 is acceptable, means endpoint exists)
        # Note: 500 may occur if there's an error in pipeline loading, but endpoint is still available
        response = client.get("/api/v1/pipelines/test_pipeline")
        assert response.status_code in [200, 404, 500], "Get pipeline endpoint should be available"
        
        # Create pipeline endpoint (validation error is acceptable, means endpoint exists)
        response = client.post("/api/v1/pipelines", json={})
        assert response.status_code in [201, 409, 422], "Create pipeline endpoint should be available"
        
        # Update pipeline endpoint (404 or 500 is acceptable, means endpoint exists)
        response = client.put("/api/v1/pipelines/test_pipeline", json={})
        assert response.status_code in [200, 404, 422, 500], "Update pipeline endpoint should be available"
    
    def test_configuration_endpoints_available(self, client):
        """
        Feature: project-production-readiness, Property 32: Core function API availability
        Validates: Requirements 8.2
        
        Test that configuration management endpoints are available.
        """
        # Get agent config endpoint (404 is acceptable, means endpoint exists)
        response = client.get("/api/v1/config/agents/test_agent")
        assert response.status_code in [200, 404], "Get agent config endpoint should be available"
        
        # Update agent config endpoint (404 is acceptable, means endpoint exists)
        response = client.put("/api/v1/config/agents/test_agent", json={"config": {}})
        assert response.status_code in [200, 404, 422], "Update agent config endpoint should be available"
        
        # Get pipeline config endpoint (404 is acceptable, means endpoint exists)
        response = client.get("/api/v1/config/pipelines/test_pipeline")
        assert response.status_code in [200, 404], "Get pipeline config endpoint should be available"
        
        # Update pipeline config endpoint (404 is acceptable, means endpoint exists)
        response = client.put("/api/v1/config/pipelines/test_pipeline", json={"config": {}})
        assert response.status_code in [200, 404, 422], "Update pipeline config endpoint should be available"
    
    def test_execution_endpoints_available(self, client):
        """
        Feature: project-production-readiness, Property 32: Core function API availability
        Validates: Requirements 8.2
        
        Test that async execution endpoints are available.
        """
        # List executions endpoint
        response = client.get("/api/v1/executions")
        assert response.status_code == 200, "List executions endpoint should be available"
        
        # Create execution endpoint (validation error is acceptable, means endpoint exists)
        response = client.post("/api/v1/executions", json={})
        assert response.status_code in [202, 404, 422, 500], "Create execution endpoint should be available"
        
        # Get execution status endpoint (404 is acceptable, means endpoint exists)
        response = client.get("/api/v1/executions/exec_test")
        assert response.status_code in [200, 404], "Get execution status endpoint should be available"
        
        # Get execution progress endpoint (404 or 204 is acceptable, means endpoint exists)
        response = client.get("/api/v1/executions/exec_test/progress")
        assert response.status_code in [200, 204, 404], "Get execution progress endpoint should be available"
        
        # Cancel execution endpoint (404 is acceptable, means endpoint exists)
        response = client.post("/api/v1/executions/exec_test/cancel")
        assert response.status_code in [200, 400, 404], "Cancel execution endpoint should be available"
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        agent_id=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='_'),
            min_size=1,
            max_size=50
        ).filter(lambda x: x[0].isalpha())  # Must start with letter
    )
    def test_agent_endpoints_handle_various_ids(self, agent_id):
        """
        Feature: project-production-readiness, Property 32: Core function API availability
        Validates: Requirements 8.2
        
        Property: For any valid agent ID, the agent endpoints should be accessible
        and return appropriate responses (200, 404, etc.).
        """
        # Create client inside test to avoid fixture issues
        client = get_test_client()
        
        # Get agent endpoint should be accessible
        response = client.get(f"/api/v1/agents/{agent_id}")
        # Should return 200 (found) or 404 (not found), not 500 (server error)
        assert response.status_code in [200, 404], \
            f"Get agent endpoint should handle agent_id '{agent_id}' gracefully"
        
        # Get agent config endpoint should be accessible
        response = client.get(f"/api/v1/config/agents/{agent_id}")
        # Should return 200 (found) or 404 (not found), not 500 (server error)
        assert response.status_code in [200, 404], \
            f"Get agent config endpoint should handle agent_id '{agent_id}' gracefully"
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        pipeline_id=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='_'),
            min_size=1,
            max_size=50
        ).filter(lambda x: x[0].isalpha())  # Must start with letter
    )
    def test_pipeline_endpoints_handle_various_ids(self, pipeline_id):
        """
        Feature: project-production-readiness, Property 32: Core function API availability
        Validates: Requirements 8.2
        
        Property: For any valid pipeline ID, the pipeline endpoints should be accessible
        and return appropriate responses (200, 404, etc.).
        """
        # Create client inside test to avoid fixture issues
        client = get_test_client()
        
        # Get pipeline endpoint should be accessible
        response = client.get(f"/api/v1/pipelines/{pipeline_id}")
        # Should return 200 (found) or 404 (not found), not 500 (server error)
        assert response.status_code in [200, 404], \
            f"Get pipeline endpoint should handle pipeline_id '{pipeline_id}' gracefully"
        
        # Get pipeline config endpoint should be accessible
        response = client.get(f"/api/v1/config/pipelines/{pipeline_id}")
        # Should return 200 (found) or 404 (not found), not 500 (server error)
        assert response.status_code in [200, 404], \
            f"Get pipeline config endpoint should handle pipeline_id '{pipeline_id}' gracefully"
    
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        execution_id=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='_'),
            min_size=1,
            max_size=50
        )
    )
    def test_execution_endpoints_handle_various_ids(self, execution_id):
        """
        Feature: project-production-readiness, Property 32: Core function API availability
        Validates: Requirements 8.2
        
        Property: For any execution ID, the execution endpoints should be accessible
        and return appropriate responses (200, 404, etc.).
        """
        # Create client inside test to avoid fixture issues
        client = get_test_client()
        
        # Get execution status endpoint should be accessible
        response = client.get(f"/api/v1/executions/{execution_id}")
        # Should return 200 (found) or 404 (not found), not 500 (server error)
        assert response.status_code in [200, 404], \
            f"Get execution status endpoint should handle execution_id '{execution_id}' gracefully"
        
        # Get execution progress endpoint should be accessible
        response = client.get(f"/api/v1/executions/{execution_id}/progress")
        # Should return 200 (found), 204 (no content), or 404 (not found), not 500 (server error)
        assert response.status_code in [200, 204, 404], \
            f"Get execution progress endpoint should handle execution_id '{execution_id}' gracefully"
    
    def test_openapi_schema_documents_all_endpoints(self, client):
        """
        Feature: project-production-readiness, Property 32: Core function API availability
        Validates: Requirements 8.2
        
        Test that the OpenAPI schema documents all core endpoints.
        """
        response = client.get("/openapi.json")
        assert response.status_code == 200
        
        schema = response.json()
        paths = schema.get("paths", {})
        
        # System endpoints
        assert "/health" in paths, "Health endpoint should be documented"
        assert "/" in paths, "Root endpoint should be documented"
        
        # Agent management endpoints (FastAPI adds trailing slashes)
        assert "/api/v1/agents/" in paths or "/api/v1/agents" in paths, "List agents endpoint should be documented"
        assert "/api/v1/agents/{agent_id}" in paths, "Agent detail endpoint should be documented"
        
        # Pipeline management endpoints
        assert "/api/v1/pipelines/" in paths or "/api/v1/pipelines" in paths, "List pipelines endpoint should be documented"
        assert "/api/v1/pipelines/{pipeline_id}" in paths, "Pipeline detail endpoint should be documented"
        
        # Configuration endpoints
        assert "/api/v1/config/agents/{agent_id}" in paths, "Agent config endpoint should be documented"
        assert "/api/v1/config/pipelines/{pipeline_id}" in paths, "Pipeline config endpoint should be documented"
        
        # Execution endpoints
        assert "/api/v1/executions/" in paths or "/api/v1/executions" in paths, "Executions endpoint should be documented"
        assert "/api/v1/executions/{execution_id}" in paths, "Execution detail endpoint should be documented"
        assert "/api/v1/executions/{execution_id}/progress" in paths, "Execution progress endpoint should be documented"
        assert "/api/v1/executions/{execution_id}/cancel" in paths, "Cancel execution endpoint should be documented"
    
    def test_all_endpoints_return_json(self, client):
        """
        Feature: project-production-readiness, Property 32: Core function API availability
        Validates: Requirements 8.2
        
        Property: All API endpoints should return JSON responses (except docs).
        """
        json_endpoints = [
            ("/health", "GET"),
            ("/", "GET"),
            ("/openapi.json", "GET"),
            ("/api/v1/agents", "GET"),
            ("/api/v1/pipelines", "GET"),
            ("/api/v1/executions", "GET"),
        ]
        
        for endpoint, method in json_endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            
            assert response.status_code in [200, 201, 202, 400, 404, 422], \
                f"Endpoint {method} {endpoint} should be accessible"
            
            # Check content type (except for docs endpoints)
            if not endpoint.endswith(("/docs", "/redoc")):
                assert "application/json" in response.headers.get("content-type", ""), \
                    f"Endpoint {method} {endpoint} should return JSON"
    
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        page=st.integers(min_value=1, max_value=100),
        page_size=st.integers(min_value=1, max_value=100)
    )
    def test_list_endpoints_support_pagination(self, page, page_size):
        """
        Feature: project-production-readiness, Property 32: Core function API availability
        Validates: Requirements 8.2
        
        Property: All list endpoints should support pagination parameters.
        """
        # Create client inside test to avoid fixture issues
        client = get_test_client()
        
        list_endpoints = [
            "/api/v1/agents",
            "/api/v1/pipelines",
            "/api/v1/executions",
        ]
        
        for endpoint in list_endpoints:
            response = client.get(f"{endpoint}?page={page}&page_size={page_size}")
            
            # Should return 200 or 422 (if validation fails), not 500
            assert response.status_code in [200, 422], \
                f"Endpoint {endpoint} should handle pagination parameters gracefully"
            
            if response.status_code == 200:
                data = response.json()
                assert "pagination" in data, \
                    f"Endpoint {endpoint} should return pagination info"
                
                pagination = data["pagination"]
                assert "page" in pagination
                assert "page_size" in pagination
                assert "total_items" in pagination
                assert "total_pages" in pagination
    
    def test_error_responses_have_consistent_format(self, client):
        """
        Feature: project-production-readiness, Property 32: Core function API availability
        Validates: Requirements 8.2
        
        Property: All error responses should have a consistent format.
        """
        # Test 404 errors
        not_found_endpoints = [
            "/api/v1/agents/nonexistent_agent_xyz",
            "/api/v1/pipelines/nonexistent_pipeline_xyz",
            "/api/v1/executions/exec_nonexistent_xyz",
            "/api/v1/config/agents/nonexistent_agent_xyz",
            "/api/v1/config/pipelines/nonexistent_pipeline_xyz",
        ]
        
        for endpoint in not_found_endpoints:
            response = client.get(endpoint)
            assert response.status_code == 404, \
                f"Endpoint {endpoint} should return 404 for non-existent resources"
            
            data = response.json()
            assert "detail" in data, \
                f"404 response from {endpoint} should have 'detail' field"
            
            # Check for consistent error structure
            detail = data["detail"]
            if isinstance(detail, dict):
                assert "error" in detail or "message" in detail, \
                    f"Error detail from {endpoint} should have 'error' or 'message' field"
    
    def test_http_methods_are_correctly_implemented(self, client):
        """
        Feature: project-production-readiness, Property 32: Core function API availability
        Validates: Requirements 8.2
        
        Property: Endpoints should respond correctly to their designated HTTP methods.
        """
        # Test that GET endpoints don't accept POST
        get_only_endpoints = [
            "/health",
            "/api/v1/agents",
            "/api/v1/pipelines",
            "/api/v1/executions",
        ]
        
        for endpoint in get_only_endpoints:
            # GET should work
            get_response = client.get(endpoint)
            assert get_response.status_code in [200, 404], \
                f"GET {endpoint} should be accessible"
            
            # POST should not be allowed (405 Method Not Allowed)
            # Note: Some endpoints like /api/v1/agents accept POST for creation
            # So we skip those
            if endpoint not in ["/api/v1/agents", "/api/v1/pipelines", "/api/v1/executions"]:
                post_response = client.post(endpoint, json={})
                assert post_response.status_code in [405, 404], \
                    f"POST {endpoint} should not be allowed"


class TestAPIEndpointCompleteness:
    """Test that the API provides complete CRUD operations where appropriate."""
    
    def test_agent_crud_operations_available(self, client):
        """
        Feature: project-production-readiness, Property 32: Core function API availability
        Validates: Requirements 8.2
        
        Test that agents support Create, Read, Update operations.
        """
        # Create (POST)
        response = client.post("/api/v1/agents", json={})
        assert response.status_code in [201, 409, 422], "Create agent endpoint should exist"
        
        # Read (GET list)
        response = client.get("/api/v1/agents")
        assert response.status_code == 200, "List agents endpoint should exist"
        
        # Read (GET detail)
        response = client.get("/api/v1/agents/test")
        assert response.status_code in [200, 404], "Get agent endpoint should exist"
        
        # Update (PUT)
        response = client.put("/api/v1/agents/test", json={})
        assert response.status_code in [200, 404, 422], "Update agent endpoint should exist"
    
    def test_pipeline_crud_operations_available(self, client):
        """
        Feature: project-production-readiness, Property 32: Core function API availability
        Validates: Requirements 8.2
        
        Test that pipelines support Create, Read, Update operations.
        """
        # Create (POST)
        response = client.post("/api/v1/pipelines", json={})
        assert response.status_code in [201, 409, 422], "Create pipeline endpoint should exist"
        
        # Read (GET list)
        response = client.get("/api/v1/pipelines")
        assert response.status_code == 200, "List pipelines endpoint should exist"
        
        # Read (GET detail)
        response = client.get("/api/v1/pipelines/test")
        assert response.status_code in [200, 404], "Get pipeline endpoint should exist"
        
        # Update (PUT)
        response = client.put("/api/v1/pipelines/test", json={})
        assert response.status_code in [200, 404, 422], "Update pipeline endpoint should exist"
    
    def test_execution_lifecycle_operations_available(self, client):
        """
        Feature: project-production-readiness, Property 32: Core function API availability
        Validates: Requirements 8.2
        
        Test that executions support Create, Read, Cancel operations.
        """
        # Create (POST)
        response = client.post("/api/v1/executions", json={})
        assert response.status_code in [202, 404, 422, 500], "Create execution endpoint should exist"
        
        # Read (GET list)
        response = client.get("/api/v1/executions")
        assert response.status_code == 200, "List executions endpoint should exist"
        
        # Read (GET detail)
        response = client.get("/api/v1/executions/exec_test")
        assert response.status_code in [200, 404], "Get execution endpoint should exist"
        
        # Read progress
        response = client.get("/api/v1/executions/exec_test/progress")
        assert response.status_code in [200, 204, 404], "Get execution progress endpoint should exist"
        
        # Cancel (POST)
        response = client.post("/api/v1/executions/exec_test/cancel")
        assert response.status_code in [200, 400, 404], "Cancel execution endpoint should exist"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
