"""
Property-Based Tests for Configuration API Read-Write

This module tests Property 34: Configuration API read-write
For any configuration file, the system should support reading and writing
through API endpoints with round-trip consistency.

Feature: project-production-readiness, Property 34: Configuration API read-write
Validates: Requirements 8.4
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck, assume
from fastapi.testclient import TestClient
from pathlib import Path
import yaml
import tempfile
import shutil

from src.api.app import create_app
from src.agent_registry_v2 import AgentRegistry, AgentMetadata


# Custom strategies for generating valid configuration data
# Use printable ASCII to avoid YAML encoding issues
yaml_safe_text = st.text(
    alphabet=st.characters(
        whitelist_categories=('Lu', 'Ll', 'Nd', 'P'),
        blacklist_characters='\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f'
                             '\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
                             '\x7f\x80\x81\x82\x83\x84\x85\x86\x87\x88\x89\x8a\x8b\x8c\x8d\x8e\x8f'
                             '\x90\x91\x92\x93\x94\x95\x96\x97\x98\x99\x9a\x9b\x9c\x9d\x9e\x9f'
    ),
    min_size=1
)

@st.composite
def agent_config_strategy(draw):
    """Strategy for generating valid agent configurations."""
    config = {
        "name": draw(yaml_safe_text.filter(lambda x: len(x) <= 100)),
        "model": draw(st.sampled_from([
            "doubao-pro", "doubao-pro-32k", "gpt-4", "gpt-3.5-turbo"
        ])),
        "temperature": draw(st.floats(min_value=0.0, max_value=2.0, allow_nan=False, allow_infinity=False)),
    }
    
    # Add prompts
    config["prompts"] = {
        "system": draw(yaml_safe_text.filter(lambda x: len(x) <= 500)),
        "user": draw(yaml_safe_text.filter(lambda x: len(x) <= 500))
    }
    
    # Optionally add other fields
    if draw(st.booleans()):
        config["max_tokens"] = draw(st.integers(min_value=1, max_value=4096))
    
    if draw(st.booleans()):
        config["top_p"] = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    
    if draw(st.booleans()):
        config["description"] = draw(yaml_safe_text.filter(lambda x: len(x) <= 200))
    
    return config


@st.composite
def pipeline_config_strategy(draw):
    """Strategy for generating valid pipeline configurations."""
    num_steps = draw(st.integers(min_value=1, max_value=5))
    
    config = {
        "name": draw(yaml_safe_text.filter(lambda x: len(x) <= 100)),
        "description": draw(yaml_safe_text.filter(lambda x: len(x) <= 200)),
        "version": draw(st.text(min_size=1, max_size=20, alphabet=st.characters(
            whitelist_categories=('Nd',), blacklist_characters=''
        )).map(lambda x: f"1.{x}.0" if x else "1.0.0")),
        "inputs": [
            {
                "name": draw(yaml_safe_text.filter(lambda x: len(x) <= 50)),
                "desc": draw(yaml_safe_text.filter(lambda x: len(x) <= 100)),
                "required": draw(st.booleans())
            }
        ],
        "outputs": [
            {
                "key": draw(yaml_safe_text.filter(lambda x: len(x) <= 50)),
                "label": draw(yaml_safe_text.filter(lambda x: len(x) <= 100))
            }
        ],
        "steps": []
    }
    
    # Generate steps
    for i in range(num_steps):
        step = {
            "id": f"step{i+1}",
            "type": draw(st.sampled_from(["agent_flow", "code_node"])),
            "input_mapping": {
                draw(yaml_safe_text.filter(lambda x: len(x) <= 20)): draw(yaml_safe_text.filter(lambda x: len(x) <= 20))
            },
            "output_key": draw(yaml_safe_text.filter(lambda x: len(x) <= 50))
        }
        
        if step["type"] == "agent_flow":
            step["agent"] = draw(yaml_safe_text.filter(lambda x: len(x) <= 50))
            step["flow"] = draw(yaml_safe_text.filter(lambda x: len(x) <= 50))
        elif step["type"] == "code_node":
            step["language"] = draw(st.sampled_from(["javascript", "python"]))
            step["code"] = draw(yaml_safe_text.filter(lambda x: len(x) <= 200))
        
        config["steps"].append(step)
    
    return config


@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace with agent and pipeline directories."""
    agents_dir = tmp_path / "agents"
    pipelines_dir = tmp_path / "pipelines"
    agents_dir.mkdir()
    pipelines_dir.mkdir()
    
    return {
        "root": tmp_path,
        "agents": agents_dir,
        "pipelines": pipelines_dir
    }


@pytest.fixture
def test_client():
    """Create a test client."""
    app = create_app()
    return TestClient(app)


def create_test_agent(workspace, agent_id, config):
    """Helper to create a test agent with configuration."""
    agent_dir = workspace["agents"] / agent_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    config_file = agent_dir / "agent.yaml"
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)
    
    return agent_dir


def create_test_pipeline(workspace, pipeline_id, config):
    """Helper to create a test pipeline with configuration."""
    config_file = workspace["pipelines"] / f"{pipeline_id}.yaml"
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)
    
    return config_file


class TestAgentConfigRoundTrip:
    """Test agent configuration read-write round-trip."""
    
    # Feature: project-production-readiness, Property 34: Configuration API read-write
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        agent_id=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='_'),
            min_size=1,
            max_size=50
        ).filter(lambda x: x[0].isalpha()),
        original_config=agent_config_strategy(),
        updated_config=agent_config_strategy()
    )
    def test_agent_config_read_write_round_trip(self, agent_id, original_config, updated_config, temp_workspace, test_client, monkeypatch):
        """
        Feature: project-production-readiness, Property 34: Configuration API read-write
        Validates: Requirements 8.4
        
        Property: For any agent configuration, reading it via API, updating it,
        and reading it again should produce the updated configuration.
        
        This tests the complete round-trip: read -> update -> read
        """
        # Create test agent with original config
        agent_dir = create_test_agent(temp_workspace, agent_id, original_config)
        
        # Mock the agent registry to return our test agent
        def mock_get_agent(self, aid):
            if aid == agent_id:
                return AgentMetadata(
                    id=agent_id,
                    name=original_config.get("name", "Test Agent"),
                    category="test",
                    environment="test",
                    owner="test-team",
                    version="1.0.0",
                    location=agent_dir,
                    deprecated=False,
                    tags=[],
                    status="active"
                )
            raise KeyError(f"Agent {aid} not found")
        
        monkeypatch.setattr(AgentRegistry, "get_agent", mock_get_agent)
        
        # Step 1: Read original configuration via API
        response1 = test_client.get(f"/api/v1/config/agents/{agent_id}")
        assert response1.status_code == 200, f"Failed to read agent config: {response1.json()}"
        
        read_config_1 = response1.json()["config"]
        
        # Verify original config was read correctly
        assert read_config_1["name"] == original_config["name"]
        assert read_config_1["model"] == original_config["model"]
        
        # Step 2: Update configuration via API
        response2 = test_client.put(
            f"/api/v1/config/agents/{agent_id}",
            json={"config": updated_config}
        )
        assert response2.status_code == 200, f"Failed to update agent config: {response2.json()}"
        
        # Step 3: Read updated configuration via API
        response3 = test_client.get(f"/api/v1/config/agents/{agent_id}")
        assert response3.status_code == 200, f"Failed to read updated agent config: {response3.json()}"
        
        read_config_2 = response3.json()["config"]
        
        # Verify updated config was persisted correctly
        assert read_config_2["name"] == updated_config["name"], \
            f"Name mismatch: expected {updated_config['name']}, got {read_config_2['name']}"
        assert read_config_2["model"] == updated_config["model"], \
            f"Model mismatch: expected {updated_config['model']}, got {read_config_2['model']}"
        assert abs(read_config_2["temperature"] - updated_config["temperature"]) < 0.0001, \
            f"Temperature mismatch: expected {updated_config['temperature']}, got {read_config_2['temperature']}"
        
        # Verify prompts
        assert read_config_2["prompts"]["system"] == updated_config["prompts"]["system"]
        assert read_config_2["prompts"]["user"] == updated_config["prompts"]["user"]
        
        # Verify optional fields if present
        if "max_tokens" in updated_config:
            assert read_config_2.get("max_tokens") == updated_config["max_tokens"]
        
        if "top_p" in updated_config:
            assert abs(read_config_2.get("top_p", 0) - updated_config["top_p"]) < 0.0001
    
    # Feature: project-production-readiness, Property 34: Configuration API read-write
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        agent_id=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='_'),
            min_size=1,
            max_size=50
        ).filter(lambda x: x[0].isalpha()),
        config=agent_config_strategy()
    )
    def test_agent_config_preserves_all_fields(self, agent_id, config, temp_workspace, test_client, monkeypatch):
        """
        Feature: project-production-readiness, Property 34: Configuration API read-write
        Validates: Requirements 8.4
        
        Property: For any agent configuration with arbitrary fields,
        reading and writing via API should preserve all fields.
        """
        # Add some custom fields to test preservation
        config["custom_field_1"] = "custom_value_1"
        config["custom_field_2"] = {"nested": "value"}
        config["custom_list"] = ["item1", "item2", "item3"]
        
        # Create test agent
        agent_dir = create_test_agent(temp_workspace, agent_id, config)
        
        # Mock the agent registry
        def mock_get_agent(self, aid):
            if aid == agent_id:
                return AgentMetadata(
                    id=agent_id,
                    name=config.get("name", "Test Agent"),
                    category="test",
                    environment="test",
                    owner="test-team",
                    version="1.0.0",
                    location=agent_dir,
                    deprecated=False,
                    tags=[],
                    status="active"
                )
            raise KeyError(f"Agent {aid} not found")
        
        monkeypatch.setattr(AgentRegistry, "get_agent", mock_get_agent)
        
        # Read configuration
        response1 = test_client.get(f"/api/v1/config/agents/{agent_id}")
        assert response1.status_code == 200
        read_config = response1.json()["config"]
        
        # Verify all fields are preserved
        assert read_config["custom_field_1"] == "custom_value_1"
        assert read_config["custom_field_2"] == {"nested": "value"}
        assert read_config["custom_list"] == ["item1", "item2", "item3"]
        
        # Update with modified custom fields
        read_config["custom_field_1"] = "modified_value"
        read_config["new_field"] = "new_value"
        
        response2 = test_client.put(
            f"/api/v1/config/agents/{agent_id}",
            json={"config": read_config}
        )
        assert response2.status_code == 200
        
        # Read again and verify changes
        response3 = test_client.get(f"/api/v1/config/agents/{agent_id}")
        assert response3.status_code == 200
        final_config = response3.json()["config"]
        
        assert final_config["custom_field_1"] == "modified_value"
        assert final_config["new_field"] == "new_value"
        assert final_config["custom_field_2"] == {"nested": "value"}


class TestPipelineConfigRoundTrip:
    """Test pipeline configuration read-write round-trip."""
    
    # Feature: project-production-readiness, Property 34: Configuration API read-write
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        pipeline_id=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='_'),
            min_size=1,
            max_size=50
        ).filter(lambda x: x[0].isalpha()),
        original_config=pipeline_config_strategy(),
        updated_config=pipeline_config_strategy()
    )
    def test_pipeline_config_read_write_round_trip(self, pipeline_id, original_config, updated_config, temp_workspace, test_client, monkeypatch):
        """
        Feature: project-production-readiness, Property 34: Configuration API read-write
        Validates: Requirements 8.4
        
        Property: For any pipeline configuration, reading it via API, updating it,
        and reading it again should produce the updated configuration.
        
        This tests the complete round-trip: read -> update -> read
        """
        # Create test pipeline with original config
        config_file = create_test_pipeline(temp_workspace, pipeline_id, original_config)
        
        # Mock find_pipeline_config_file to return our test file
        def mock_find_pipeline_config_file(pid):
            if pid == pipeline_id:
                return config_file
            raise FileNotFoundError(f"Pipeline {pid} not found")
        
        import src.api.routes.config as config_module
        monkeypatch.setattr(config_module, "find_pipeline_config_file", mock_find_pipeline_config_file)
        
        # Step 1: Read original configuration via API
        response1 = test_client.get(f"/api/v1/config/pipelines/{pipeline_id}")
        assert response1.status_code == 200, f"Failed to read pipeline config: {response1.json()}"
        
        read_config_1 = response1.json()["config"]
        
        # Verify original config was read correctly
        assert read_config_1["name"] == original_config["name"]
        assert read_config_1["version"] == original_config["version"]
        assert len(read_config_1["steps"]) == len(original_config["steps"])
        
        # Step 2: Update configuration via API
        response2 = test_client.put(
            f"/api/v1/config/pipelines/{pipeline_id}",
            json={"config": updated_config}
        )
        assert response2.status_code == 200, f"Failed to update pipeline config: {response2.json()}"
        
        # Step 3: Read updated configuration via API
        response3 = test_client.get(f"/api/v1/config/pipelines/{pipeline_id}")
        assert response3.status_code == 200, f"Failed to read updated pipeline config: {response3.json()}"
        
        read_config_2 = response3.json()["config"]
        
        # Verify updated config was persisted correctly
        assert read_config_2["name"] == updated_config["name"], \
            f"Name mismatch: expected {updated_config['name']}, got {read_config_2['name']}"
        assert read_config_2["version"] == updated_config["version"], \
            f"Version mismatch: expected {updated_config['version']}, got {read_config_2['version']}"
        assert read_config_2["description"] == updated_config["description"]
        
        # Verify steps
        assert len(read_config_2["steps"]) == len(updated_config["steps"])
        for i, step in enumerate(updated_config["steps"]):
            assert read_config_2["steps"][i]["id"] == step["id"]
            assert read_config_2["steps"][i]["type"] == step["type"]
    
    # Feature: project-production-readiness, Property 34: Configuration API read-write
    @settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        pipeline_id=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='_'),
            min_size=1,
            max_size=50
        ).filter(lambda x: x[0].isalpha()),
        config=pipeline_config_strategy()
    )
    def test_pipeline_config_preserves_step_details(self, pipeline_id, config, temp_workspace, test_client, monkeypatch):
        """
        Feature: project-production-readiness, Property 34: Configuration API read-write
        Validates: Requirements 8.4
        
        Property: For any pipeline configuration with complex step configurations,
        reading and writing via API should preserve all step details.
        """
        # Create test pipeline
        config_file = create_test_pipeline(temp_workspace, pipeline_id, config)
        
        # Mock find_pipeline_config_file
        def mock_find_pipeline_config_file(pid):
            if pid == pipeline_id:
                return config_file
            raise FileNotFoundError(f"Pipeline {pid} not found")
        
        import src.api.routes.config as config_module
        monkeypatch.setattr(config_module, "find_pipeline_config_file", mock_find_pipeline_config_file)
        
        # Read configuration
        response1 = test_client.get(f"/api/v1/config/pipelines/{pipeline_id}")
        assert response1.status_code == 200
        read_config = response1.json()["config"]
        
        # Verify all step details are preserved
        for i, original_step in enumerate(config["steps"]):
            read_step = read_config["steps"][i]
            assert read_step["id"] == original_step["id"]
            assert read_step["type"] == original_step["type"]
            assert read_step["input_mapping"] == original_step["input_mapping"]
            assert read_step["output_key"] == original_step["output_key"]
            
            if original_step["type"] == "agent_flow":
                assert read_step["agent"] == original_step["agent"]
                assert read_step["flow"] == original_step["flow"]
            elif original_step["type"] == "code_node":
                assert read_step["language"] == original_step["language"]
                assert read_step["code"] == original_step["code"]
        
        # Modify a step and update
        read_config["steps"][0]["output_key"] = "modified_output"
        if read_config["steps"][0]["type"] == "agent_flow":
            read_config["steps"][0]["agent"] = "modified_agent"
        
        response2 = test_client.put(
            f"/api/v1/config/pipelines/{pipeline_id}",
            json={"config": read_config}
        )
        assert response2.status_code == 200
        
        # Read again and verify changes
        response3 = test_client.get(f"/api/v1/config/pipelines/{pipeline_id}")
        assert response3.status_code == 200
        final_config = response3.json()["config"]
        
        assert final_config["steps"][0]["output_key"] == "modified_output"
        if final_config["steps"][0]["type"] == "agent_flow":
            assert final_config["steps"][0]["agent"] == "modified_agent"


class TestConfigAPIConsistency:
    """Test consistency properties of configuration API."""
    
    # Feature: project-production-readiness, Property 34: Configuration API read-write
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        agent_id=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='_'),
            min_size=1,
            max_size=50
        ).filter(lambda x: x[0].isalpha()),
        config=agent_config_strategy()
    )
    def test_multiple_reads_return_same_config(self, agent_id, config, temp_workspace, test_client, monkeypatch):
        """
        Feature: project-production-readiness, Property 34: Configuration API read-write
        Validates: Requirements 8.4
        
        Property: Multiple reads of the same configuration without updates
        should return identical results.
        """
        # Create test agent
        agent_dir = create_test_agent(temp_workspace, agent_id, config)
        
        # Mock the agent registry
        def mock_get_agent(self, aid):
            if aid == agent_id:
                return AgentMetadata(
                    id=agent_id,
                    name=config.get("name", "Test Agent"),
                    category="test",
                    environment="test",
                    owner="test-team",
                    version="1.0.0",
                    location=agent_dir,
                    deprecated=False,
                    tags=[],
                    status="active"
                )
            raise KeyError(f"Agent {aid} not found")
        
        monkeypatch.setattr(AgentRegistry, "get_agent", mock_get_agent)
        
        # Read configuration multiple times
        configs = []
        for _ in range(3):
            response = test_client.get(f"/api/v1/config/agents/{agent_id}")
            assert response.status_code == 200
            configs.append(response.json()["config"])
        
        # All reads should return identical configurations
        assert configs[0] == configs[1]
        assert configs[1] == configs[2]
    
    # Feature: project-production-readiness, Property 34: Configuration API read-write
    @settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        agent_id=st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='_'),
            min_size=1,
            max_size=50
        ).filter(lambda x: x[0].isalpha()),
        config=agent_config_strategy()
    )
    def test_read_after_write_is_idempotent(self, agent_id, config, temp_workspace, test_client, monkeypatch):
        """
        Feature: project-production-readiness, Property 34: Configuration API read-write
        Validates: Requirements 8.4
        
        Property: Writing a configuration and immediately reading it back
        should return the exact configuration that was written.
        """
        # Create test agent with initial config
        agent_dir = create_test_agent(temp_workspace, agent_id, {"name": "Initial"})
        
        # Mock the agent registry
        def mock_get_agent(self, aid):
            if aid == agent_id:
                return AgentMetadata(
                    id=agent_id,
                    name="Test Agent",
                    category="test",
                    environment="test",
                    owner="test-team",
                    version="1.0.0",
                    location=agent_dir,
                    deprecated=False,
                    tags=[],
                    status="active"
                )
            raise KeyError(f"Agent {aid} not found")
        
        monkeypatch.setattr(AgentRegistry, "get_agent", mock_get_agent)
        
        # Write configuration
        response1 = test_client.put(
            f"/api/v1/config/agents/{agent_id}",
            json={"config": config}
        )
        assert response1.status_code == 200
        
        # Read configuration immediately
        response2 = test_client.get(f"/api/v1/config/agents/{agent_id}")
        assert response2.status_code == 200
        read_config = response2.json()["config"]
        
        # Verify exact match
        assert read_config["name"] == config["name"]
        assert read_config["model"] == config["model"]
        assert abs(read_config["temperature"] - config["temperature"]) < 0.0001
        assert read_config["prompts"] == config["prompts"]
        
        # Verify optional fields
        for key in ["max_tokens", "top_p", "description"]:
            if key in config:
                if isinstance(config[key], float):
                    assert abs(read_config.get(key, 0) - config[key]) < 0.0001
                else:
                    assert read_config.get(key) == config[key]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
