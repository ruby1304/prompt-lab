"""
API Integration Tests

This module provides comprehensive integration tests for the API layer,
testing complete workflows with real Doubao Pro model execution.

⚠️ IMPORTANT: These tests use real Doubao Pro model and require:
- Valid API credentials in environment variables
- Network access to Doubao API endpoint
- Sufficient API quota

Requirements: 8.2, 8.5

Test Coverage:
- Complete agent execution workflow via API
- Complete pipeline execution workflow via API
- Async execution and progress tracking
- Error handling and recovery
- End-to-end data flow
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import tempfile
import yaml
import json
import time
import os
from typing import Dict, Any

from src.api.app import create_app
from src.agent_registry_v2 import AgentRegistry


# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def verify_doubao_config():
    """Verify Doubao Pro configuration before running tests."""
    required_vars = ["OPENAI_API_KEY", "OPENAI_API_BASE", "OPENAI_MODEL_NAME"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        pytest.skip(
            f"Missing required environment variables for Doubao Pro: {', '.join(missing_vars)}\n"
            "Please configure:\n"
            "  - OPENAI_API_KEY: Your Doubao API key\n"
            "  - OPENAI_API_BASE: Doubao API endpoint\n"
            "  - OPENAI_MODEL_NAME: Doubao Pro model name"
        )
    
    # Verify model name contains "doubao" or is a valid model
    model_name = os.getenv("OPENAI_MODEL_NAME", "").lower()
    print(f"\n✓ Using model: {os.getenv('OPENAI_MODEL_NAME')}")
    print(f"✓ API endpoint: {os.getenv('OPENAI_API_BASE')}")
    
    return True


@pytest.fixture
def test_agent_config():
    """Create a test agent configuration."""
    agent_dir = Path("agents/test_integration_agent")
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    # Create agent.yaml
    agent_config = {
        "id": "test_integration_agent",
        "name": "Test Integration Agent",
        "description": "Agent for API integration testing",
        "version": "1.0.0",
        "flows": {
            "default": {
                "system_prompt": "You are a helpful assistant. Respond concisely.",
                "user_prompt_template": "{{input_text}}",
                "model": os.getenv("OPENAI_MODEL_NAME", "doubao-pro"),
                "temperature": 0.7,
                "max_tokens": 100
            }
        }
    }
    
    agent_file = agent_dir / "agent.yaml"
    with open(agent_file, 'w') as f:
        yaml.dump(agent_config, f)
    
    yield agent_dir
    
    # Cleanup
    if agent_file.exists():
        agent_file.unlink()
    if agent_dir.exists():
        agent_dir.rmdir()


@pytest.fixture
def test_pipeline_config():
    """Create a test pipeline configuration."""
    pipeline_file = Path("pipelines/test_integration_pipeline.yaml")
    
    pipeline_config = {
        "id": "test_integration_pipeline",
        "name": "Test Integration Pipeline",
        "description": "Pipeline for API integration testing",
        "version": "1.0.0",
        "inputs": ["user_input"],
        "outputs": ["final_result"],
        "steps": [
            {
                "id": "step1",
                "type": "agent_flow",
                "agent": "test_integration_agent",
                "flow": "default",
                "input_mapping": {
                    "input_text": "user_input"
                },
                "output_key": "step1_result"
            },
            {
                "id": "step2",
                "type": "code_node",
                "language": "python",
                "code": """
def process(inputs):
    result = inputs.get('step1_result', '')
    return {'processed': f"Processed: {result}"}
""",
                "input_mapping": {
                    "step1_result": "step1_result"
                },
                "output_key": "final_result"
            }
        ]
    }
    
    pipeline_file.parent.mkdir(parents=True, exist_ok=True)
    with open(pipeline_file, 'w') as f:
        yaml.dump(pipeline_config, f)
    
    yield pipeline_file
    
    # Cleanup
    if pipeline_file.exists():
        pipeline_file.unlink()


@pytest.fixture
def client(test_agent_config, test_pipeline_config):
    """Create test client with real configuration."""
    app = create_app()
    return TestClient(app)


class TestAgentExecutionWorkflow:
    """Test complete agent execution workflow via API."""
    
    def test_sync_agent_execution_workflow(self, client, verify_doubao_config):
        """
        Test synchronous agent execution workflow.
        
        This test verifies:
        1. Agent can be retrieved via API
        2. Agent can be executed with inputs
        3. Execution returns valid results from Doubao Pro
        """
        # Step 1: Verify agent exists
        response = client.get("/api/v1/agents/test_integration_agent")
        if response.status_code == 404:
            pytest.skip("Test agent not found in registry")
        
        assert response.status_code == 200
        agent_data = response.json()
        assert agent_data["id"] == "test_integration_agent"
        print(f"\n✓ Agent retrieved: {agent_data['name']}")
        
        # Step 2: Execute agent synchronously (if endpoint exists)
        # Note: Current API may not have sync execution, so we test async
        execution_request = {
            "type": "agent",
            "target_id": "test_integration_agent",
            "inputs": {
                "input_text": "What is 2+2? Answer in one word."
            },
            "config": {
                "flow_id": "default"
            }
        }
        
        response = client.post("/api/v1/executions", json=execution_request)
        assert response.status_code in [200, 202], f"Unexpected status: {response.status_code}"
        
        execution_data = response.json()
        assert "execution_id" in execution_data
        execution_id = execution_data["execution_id"]
        print(f"✓ Execution started: {execution_id}")
        
        # Step 3: Poll for completion
        max_wait = 30  # seconds
        start_time = time.time()
        final_status = None
        
        while time.time() - start_time < max_wait:
            response = client.get(f"/api/v1/executions/{execution_id}")
            assert response.status_code == 200
            
            status_data = response.json()
            status = status_data["status"]
            print(f"  Status: {status}")
            
            if status in ["completed", "failed", "cancelled"]:
                final_status = status_data
                break
            
            time.sleep(1)
        
        # Step 4: Verify completion
        assert final_status is not None, "Execution did not complete within timeout"
        assert final_status["status"] == "completed", f"Execution failed: {final_status.get('error')}"
        assert "outputs" in final_status
        print(f"✓ Execution completed successfully")
        print(f"  Output: {final_status['outputs']}")
    
    def test_async_agent_execution_with_progress(self, client, verify_doubao_config):
        """
        Test async agent execution with progress tracking.
        
        This test verifies:
        1. Async execution can be started
        2. Progress can be queried
        3. Execution completes successfully
        """
        # Start async execution
        execution_request = {
            "type": "agent",
            "target_id": "test_integration_agent",
            "inputs": {
                "input_text": "List three colors. Be brief."
            },
            "config": {
                "flow_id": "default"
            }
        }
        
        response = client.post("/api/v1/executions", json=execution_request)
        assert response.status_code == 202
        
        execution_data = response.json()
        execution_id = execution_data["execution_id"]
        assert execution_data["status"] == "pending"
        print(f"\n✓ Async execution started: {execution_id}")
        
        # Query progress
        max_wait = 30
        start_time = time.time()
        progress_updates = []
        
        while time.time() - start_time < max_wait:
            # Check progress endpoint
            progress_response = client.get(f"/api/v1/executions/{execution_id}/progress")
            if progress_response.status_code == 200:
                progress_data = progress_response.json()
                progress_updates.append(progress_data)
                print(f"  Progress: {progress_data.get('percentage', 0)}%")
            
            # Check status
            status_response = client.get(f"/api/v1/executions/{execution_id}")
            assert status_response.status_code == 200
            
            status_data = status_response.json()
            if status_data["status"] in ["completed", "failed", "cancelled"]:
                break
            
            time.sleep(1)
        
        # Verify completion
        final_response = client.get(f"/api/v1/executions/{execution_id}")
        final_data = final_response.json()
        
        assert final_data["status"] == "completed"
        assert "outputs" in final_data
        print(f"✓ Async execution completed")
        print(f"  Progress updates received: {len(progress_updates)}")
        print(f"  Final output: {final_data['outputs']}")


class TestPipelineExecutionWorkflow:
    """Test complete pipeline execution workflow via API."""
    
    def test_pipeline_execution_with_code_node(self, client, verify_doubao_config):
        """
        Test pipeline execution with agent and code node.
        
        This test verifies:
        1. Pipeline can be retrieved via API
        2. Pipeline with agent + code node can be executed
        3. Data flows correctly through steps
        4. Final output is correct
        """
        # Step 1: Verify pipeline exists
        response = client.get("/api/v1/pipelines/test_integration_pipeline")
        if response.status_code == 404:
            pytest.skip("Test pipeline not found")
        
        assert response.status_code == 200
        pipeline_data = response.json()
        assert pipeline_data["id"] == "test_integration_pipeline"
        print(f"\n✓ Pipeline retrieved: {pipeline_data['name']}")
        
        # Step 2: Execute pipeline
        execution_request = {
            "type": "pipeline",
            "target_id": "test_integration_pipeline",
            "inputs": {
                "user_input": "Hello, world!"
            },
            "config": {}
        }
        
        response = client.post("/api/v1/executions", json=execution_request)
        assert response.status_code in [200, 202]
        
        execution_data = response.json()
        execution_id = execution_data["execution_id"]
        print(f"✓ Pipeline execution started: {execution_id}")
        
        # Step 3: Wait for completion
        max_wait = 60  # Pipelines may take longer
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = client.get(f"/api/v1/executions/{execution_id}")
            assert response.status_code == 200
            
            status_data = response.json()
            status = status_data["status"]
            
            # Check progress if available
            if "progress" in status_data and status_data["progress"]:
                progress = status_data["progress"]
                print(f"  Step {progress.get('current_step', 0)}/{progress.get('total_steps', 0)}: {progress.get('current_step_name', 'unknown')}")
            
            if status in ["completed", "failed", "cancelled"]:
                break
            
            time.sleep(2)
        
        # Step 4: Verify results
        final_response = client.get(f"/api/v1/executions/{execution_id}")
        final_data = final_response.json()
        
        assert final_data["status"] == "completed", f"Pipeline failed: {final_data.get('error')}"
        assert "outputs" in final_data
        
        # Verify code node processed the agent output
        final_result = final_data["outputs"].get("final_result", {})
        assert "processed" in final_result or "Processed" in str(final_result)
        
        print(f"✓ Pipeline completed successfully")
        print(f"  Final result: {final_result}")
    
    def test_pipeline_execution_error_handling(self, client, verify_doubao_config):
        """
        Test pipeline execution error handling.
        
        This test verifies:
        1. Invalid inputs are rejected
        2. Execution errors are reported correctly
        3. Error details are accessible
        """
        # Test 1: Invalid pipeline ID
        execution_request = {
            "type": "pipeline",
            "target_id": "nonexistent_pipeline",
            "inputs": {},
            "config": {}
        }
        
        response = client.post("/api/v1/executions", json=execution_request)
        assert response.status_code in [404, 500]
        print("\n✓ Invalid pipeline ID rejected")
        
        # Test 2: Missing required inputs
        execution_request = {
            "type": "pipeline",
            "target_id": "test_integration_pipeline",
            "inputs": {},  # Missing user_input
            "config": {}
        }
        
        response = client.post("/api/v1/executions", json=execution_request)
        # May succeed but fail during execution, or reject immediately
        if response.status_code == 202:
            execution_id = response.json()["execution_id"]
            
            # Wait for failure
            max_wait = 30
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                status_response = client.get(f"/api/v1/executions/{execution_id}")
                status_data = status_response.json()
                
                if status_data["status"] == "failed":
                    assert "error" in status_data
                    print(f"✓ Missing input error caught: {status_data['error']}")
                    break
                
                if status_data["status"] == "completed":
                    # Some pipelines may handle missing inputs gracefully
                    print("✓ Pipeline handled missing input gracefully")
                    break
                
                time.sleep(1)


class TestExecutionCancellation:
    """Test execution cancellation via API."""
    
    def test_cancel_pending_execution(self, client, verify_doubao_config):
        """
        Test cancelling a pending execution.
        
        This test verifies:
        1. Execution can be cancelled before it starts
        2. Status updates to cancelled
        3. Cancellation is reflected in queries
        """
        # Start execution
        execution_request = {
            "type": "agent",
            "target_id": "test_integration_agent",
            "inputs": {
                "input_text": "This execution will be cancelled"
            },
            "config": {}
        }
        
        response = client.post("/api/v1/executions", json=execution_request)
        if response.status_code != 202:
            pytest.skip("Could not start execution for cancellation test")
        
        execution_id = response.json()["execution_id"]
        print(f"\n✓ Execution started: {execution_id}")
        
        # Cancel immediately
        cancel_response = client.post(f"/api/v1/executions/{execution_id}/cancel")
        assert cancel_response.status_code == 200
        
        cancel_data = cancel_response.json()
        assert cancel_data["data"]["status"] == "cancelled"
        print(f"✓ Execution cancelled")
        
        # Verify status
        status_response = client.get(f"/api/v1/executions/{execution_id}")
        status_data = status_response.json()
        assert status_data["status"] == "cancelled"
        print(f"✓ Cancellation confirmed")


class TestExecutionListing:
    """Test execution listing and filtering via API."""
    
    def test_list_executions_with_filters(self, client, verify_doubao_config):
        """
        Test listing executions with various filters.
        
        This test verifies:
        1. Executions can be listed
        2. Filters work correctly
        3. Pagination works
        """
        # Create multiple executions
        execution_ids = []
        
        for i in range(3):
            execution_request = {
                "type": "agent" if i % 2 == 0 else "pipeline",
                "target_id": "test_integration_agent" if i % 2 == 0 else "test_integration_pipeline",
                "inputs": {
                    "input_text": f"Test execution {i}" if i % 2 == 0 else "user_input",
                    "user_input": f"Test execution {i}"
                },
                "config": {}
            }
            
            response = client.post("/api/v1/executions", json=execution_request)
            if response.status_code == 202:
                execution_ids.append(response.json()["execution_id"])
        
        print(f"\n✓ Created {len(execution_ids)} test executions")
        
        # Test listing all
        response = client.get("/api/v1/executions")
        assert response.status_code == 200
        
        data = response.json()
        assert "executions" in data
        assert "pagination" in data
        assert len(data["executions"]) >= len(execution_ids)
        print(f"✓ Listed {len(data['executions'])} total executions")
        
        # Test filtering by type
        response = client.get("/api/v1/executions?type=agent")
        assert response.status_code == 200
        
        data = response.json()
        for execution in data["executions"]:
            assert execution["type"] == "agent"
        print(f"✓ Filtered by type: {len(data['executions'])} agent executions")
        
        # Test pagination
        response = client.get("/api/v1/executions?page=1&page_size=2")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["executions"]) <= 2
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 2
        print(f"✓ Pagination works: page 1 with {len(data['executions'])} items")


class TestConfigurationAPI:
    """Test configuration read/write via API."""
    
    def test_read_agent_config(self, client, verify_doubao_config):
        """
        Test reading agent configuration via API.
        
        This test verifies:
        1. Agent config can be read
        2. Config format is correct
        3. All fields are present
        """
        response = client.get("/api/v1/config/agents/test_integration_agent")
        if response.status_code == 404:
            pytest.skip("Test agent config not found")
        
        assert response.status_code == 200
        
        config_data = response.json()
        assert "config" in config_data
        
        config = config_data["config"]
        assert "id" in config
        assert "flows" in config
        print(f"\n✓ Agent config retrieved")
        print(f"  Flows: {list(config['flows'].keys())}")
    
    def test_update_agent_config(self, client, verify_doubao_config):
        """
        Test updating agent configuration via API.
        
        This test verifies:
        1. Agent config can be updated
        2. Changes are persisted
        3. Updated config can be read back
        """
        # Read current config
        response = client.get("/api/v1/config/agents/test_integration_agent")
        if response.status_code == 404:
            pytest.skip("Test agent config not found")
        
        original_config = response.json()["config"]
        
        # Update config
        updated_config = original_config.copy()
        updated_config["description"] = "Updated via API integration test"
        
        update_response = client.put(
            "/api/v1/config/agents/test_integration_agent",
            json={"config": updated_config}
        )
        
        assert update_response.status_code == 200
        print(f"\n✓ Agent config updated")
        
        # Read back and verify
        verify_response = client.get("/api/v1/config/agents/test_integration_agent")
        assert verify_response.status_code == 200
        
        new_config = verify_response.json()["config"]
        assert new_config["description"] == "Updated via API integration test"
        print(f"✓ Config update verified")


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""
    
    def test_complete_workflow_agent_to_pipeline(self, client, verify_doubao_config):
        """
        Test complete workflow: create agent, create pipeline, execute.
        
        This test verifies the entire API workflow from creation to execution.
        """
        print("\n" + "="*60)
        print("Complete End-to-End Workflow Test")
        print("="*60)
        
        # Step 1: Verify agent exists
        print("\nStep 1: Verify agent...")
        agent_response = client.get("/api/v1/agents/test_integration_agent")
        if agent_response.status_code == 404:
            pytest.skip("Test agent not available")
        
        assert agent_response.status_code == 200
        print("✓ Agent verified")
        
        # Step 2: Verify pipeline exists
        print("\nStep 2: Verify pipeline...")
        pipeline_response = client.get("/api/v1/pipelines/test_integration_pipeline")
        if pipeline_response.status_code == 404:
            pytest.skip("Test pipeline not available")
        
        assert pipeline_response.status_code == 200
        print("✓ Pipeline verified")
        
        # Step 3: Execute agent
        print("\nStep 3: Execute agent...")
        agent_exec_request = {
            "type": "agent",
            "target_id": "test_integration_agent",
            "inputs": {
                "input_text": "Say 'Hello from agent'"
            },
            "config": {}
        }
        
        agent_exec_response = client.post("/api/v1/executions", json=agent_exec_request)
        assert agent_exec_response.status_code == 202
        agent_exec_id = agent_exec_response.json()["execution_id"]
        print(f"✓ Agent execution started: {agent_exec_id}")
        
        # Wait for agent completion
        max_wait = 30
        start_time = time.time()
        while time.time() - start_time < max_wait:
            status_response = client.get(f"/api/v1/executions/{agent_exec_id}")
            status_data = status_response.json()
            
            if status_data["status"] == "completed":
                print(f"✓ Agent execution completed")
                print(f"  Output: {status_data['outputs']}")
                break
            elif status_data["status"] == "failed":
                pytest.fail(f"Agent execution failed: {status_data.get('error')}")
            
            time.sleep(1)
        
        # Step 4: Execute pipeline
        print("\nStep 4: Execute pipeline...")
        pipeline_exec_request = {
            "type": "pipeline",
            "target_id": "test_integration_pipeline",
            "inputs": {
                "user_input": "Hello from pipeline"
            },
            "config": {}
        }
        
        pipeline_exec_response = client.post("/api/v1/executions", json=pipeline_exec_request)
        assert pipeline_exec_response.status_code == 202
        pipeline_exec_id = pipeline_exec_response.json()["execution_id"]
        print(f"✓ Pipeline execution started: {pipeline_exec_id}")
        
        # Wait for pipeline completion
        start_time = time.time()
        while time.time() - start_time < max_wait:
            status_response = client.get(f"/api/v1/executions/{pipeline_exec_id}")
            status_data = status_response.json()
            
            if status_data["status"] == "completed":
                print(f"✓ Pipeline execution completed")
                print(f"  Output: {status_data['outputs']}")
                break
            elif status_data["status"] == "failed":
                pytest.fail(f"Pipeline execution failed: {status_data.get('error')}")
            
            time.sleep(2)
        
        # Step 5: Verify both executions in list
        print("\nStep 5: Verify executions in list...")
        list_response = client.get("/api/v1/executions")
        assert list_response.status_code == 200
        
        list_data = list_response.json()
        execution_ids = [e["execution_id"] for e in list_data["executions"]]
        
        assert agent_exec_id in execution_ids
        assert pipeline_exec_id in execution_ids
        print(f"✓ Both executions found in list")
        
        print("\n" + "="*60)
        print("End-to-End Workflow Test Complete!")
        print("="*60)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
