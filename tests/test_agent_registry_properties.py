"""
Property-Based Tests for Agent Registry V2

These tests use Hypothesis to verify universal properties that should hold
across all valid executions of the Agent Registry system.

Feature: project-production-readiness
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from hypothesis import given, strategies as st, settings
from hypothesis import assume

from src.agent_registry_v2 import (
    AgentRegistry,
    AgentMetadata,
)


# Custom strategies for generating valid agent configurations
@st.composite
def agent_metadata_dict(draw):
    """Generate a valid agent metadata dictionary"""
    # Use simpler text generation to avoid slow filters
    agent_id = draw(st.text(
        min_size=3,
        max_size=20,
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789_'
    ))
    # Ensure it starts with a letter
    if not agent_id[0].isalpha():
        agent_id = 'a' + agent_id
    
    return {
        "name": draw(st.text(min_size=1, max_size=50, alphabet='abcdefghijklmnopqrstuvwxyz ABCDEFGHIJKLMNOPQRSTUVWXYZ')),
        "category": draw(st.sampled_from(["production", "example", "test", "system"])),
        "environment": draw(st.sampled_from(["production", "staging", "demo", "test"])),
        "owner": draw(st.text(min_size=1, max_size=30, alphabet='abcdefghijklmnopqrstuvwxyz-')),
        "version": draw(st.from_regex(r'\d+\.\d+\.\d+', fullmatch=True)),
        "location": f"agents/{agent_id}",
        "deprecated": draw(st.booleans()),
        "tags": draw(st.lists(st.text(min_size=1, max_size=15, alphabet='abcdefghijklmnopqrstuvwxyz'), max_size=3)),
        "description": draw(st.one_of(st.none(), st.text(min_size=0, max_size=100, alphabet='abcdefghijklmnopqrstuvwxyz '))),
    }


@st.composite
def registry_config_dict(draw):
    """Generate a valid registry configuration dictionary"""
    # Generate 1-5 agents (reduced for faster generation)
    num_agents = draw(st.integers(min_value=1, max_value=5))
    
    agents = {}
    for i in range(num_agents):
        agent_id = f"agent_{i}"
        agents[agent_id] = draw(agent_metadata_dict())
        # Ensure location matches agent_id
        agents[agent_id]["location"] = f"agents/{agent_id}"
    
    return {
        "version": "1.0",
        "agents": agents
    }


def save_registry_to_file(registry: AgentRegistry, config_path: Path) -> None:
    """
    Helper function to save the current registry state to a config file.
    
    This is needed for testing persistence since AgentRegistry doesn't have
    a built-in save method yet.
    """
    config = {
        "version": "1.0",
        "agents": {}
    }
    
    for agent_id, agent_metadata in registry._agents.items():
        config["agents"][agent_id] = agent_metadata.to_dict()
        # Remove the 'id' field from the dict since it's redundant (it's the key)
        if 'id' in config["agents"][agent_id]:
            del config["agents"][agent_id]['id']
    
    with open(config_path, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


class TestAgentRegistryProperties:
    """Property-Based Tests for Agent Registry"""
    
    # Feature: project-production-readiness, Property 1: Registry loading completeness
    @settings(max_examples=100)
    @given(config=registry_config_dict())
    def test_registry_loading_completeness(self, config):
        """
        Property 1: Registry loading completeness
        
        For any valid Agent Registry configuration file, loading the registry
        should successfully load all defined agents with complete metadata.
        
        Validates: Requirements 2.1
        """
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            config_path = Path(f.name)
        
        try:
            # Load the registry
            registry = AgentRegistry(config_path=config_path)
            
            # Property: All agents in config should be loaded
            expected_agent_ids = set(config["agents"].keys())
            loaded_agent_ids = set(registry._agents.keys())
            
            assert loaded_agent_ids == expected_agent_ids, \
                f"Not all agents loaded. Expected: {expected_agent_ids}, Got: {loaded_agent_ids}"
            
            # Property: Each loaded agent should have complete metadata
            for agent_id, agent_config in config["agents"].items():
                loaded_agent = registry.get_agent(agent_id)
                
                # Verify all required fields are present and match
                assert loaded_agent.id == agent_id
                assert loaded_agent.name == agent_config["name"]
                assert loaded_agent.category == agent_config["category"]
                assert loaded_agent.environment == agent_config["environment"]
                assert loaded_agent.owner == agent_config["owner"]
                assert loaded_agent.version == agent_config["version"]
                assert str(loaded_agent.location) == agent_config["location"]
                assert loaded_agent.deprecated == agent_config["deprecated"]
                
                # Verify optional fields
                if "tags" in agent_config:
                    assert loaded_agent.tags == agent_config["tags"]
                if "description" in agent_config and agent_config["description"] is not None:
                    assert loaded_agent.description == agent_config["description"]
            
            # Property: Agent count should match config
            assert registry.agent_count == len(config["agents"])
            
        finally:
            # Cleanup
            config_path.unlink()
    
    # Feature: project-production-readiness, Property 2: Agent registration persistence
    @settings(max_examples=100)
    @given(
        initial_config=registry_config_dict(),
        new_agent_metadata=agent_metadata_dict()
    )
    def test_agent_registration_persistence(self, initial_config, new_agent_metadata):
        """
        Property 2: Agent registration persistence
        
        For any new agent metadata, after registering the agent and reloading
        the registry, the agent should be queryable with the same metadata.
        
        Validates: Requirements 2.2
        """
        # Create a temporary config file with initial agents
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(initial_config, f)
            config_path = Path(f.name)
        
        try:
            # Load the registry
            registry = AgentRegistry(config_path=config_path)
            initial_count = registry.agent_count
            
            # Generate a unique agent ID that doesn't conflict with existing ones
            new_agent_id = "test_new_agent"
            counter = 0
            while new_agent_id in registry._agents:
                counter += 1
                new_agent_id = f"test_new_agent_{counter}"
            
            # Create agent metadata with the unique ID
            metadata = AgentMetadata.from_dict(new_agent_id, new_agent_metadata)
            metadata.id = new_agent_id  # Ensure ID matches
            
            # Register the new agent
            registry.register_agent(new_agent_id, metadata)
            
            # Verify agent is in memory
            assert new_agent_id in registry._agents
            assert registry.agent_count == initial_count + 1
            
            # Save the registry to the config file (persistence step)
            save_registry_to_file(registry, config_path)
            
            # Reload the registry from the config file
            registry.reload_registry()
            
            # Property: The registered agent should still be queryable after reload
            loaded_metadata = registry.get_agent(new_agent_id)
            
            # Verify all metadata fields match
            assert loaded_metadata.id == metadata.id
            assert loaded_metadata.name == metadata.name
            assert loaded_metadata.category == metadata.category
            assert loaded_metadata.environment == metadata.environment
            assert loaded_metadata.owner == metadata.owner
            assert loaded_metadata.version == metadata.version
            assert str(loaded_metadata.location) == str(metadata.location)
            assert loaded_metadata.deprecated == metadata.deprecated
            assert loaded_metadata.tags == metadata.tags
            
            # Verify optional fields
            # Note: Empty strings may be converted to None during serialization/deserialization
            if metadata.description is not None and metadata.description != '':
                assert loaded_metadata.description == metadata.description
            elif metadata.description == '':
                # Empty string may become None, which is acceptable
                assert loaded_metadata.description in (None, '')
            
            # Property: Agent count should include the new agent
            assert registry.agent_count == initial_count + 1
            
        finally:
            # Cleanup
            config_path.unlink()

    # Feature: project-production-readiness, Property 3: Agent query completeness
    @settings(max_examples=100)
    @given(config=registry_config_dict())
    def test_agent_query_completeness(self, config):
        """
        Property 3: Agent query completeness
        
        For any registered agent ID, querying the agent should return all
        required metadata fields (ID, name, category, description, etc.)
        
        Validates: Requirements 2.3
        """
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config, f)
            config_path = Path(f.name)
        
        try:
            # Load the registry
            registry = AgentRegistry(config_path=config_path)
            
            # Property: For each agent in the registry, querying should return complete metadata
            for agent_id in config["agents"].keys():
                # Query the agent
                agent_metadata = registry.get_agent(agent_id)
                
                # Verify agent_metadata is not None
                assert agent_metadata is not None, f"Agent {agent_id} not found in registry"
                
                # Verify all REQUIRED fields are present and not None
                assert agent_metadata.id is not None, f"Agent {agent_id} missing 'id' field"
                assert agent_metadata.id == agent_id, f"Agent ID mismatch: expected {agent_id}, got {agent_metadata.id}"
                
                assert agent_metadata.name is not None, f"Agent {agent_id} missing 'name' field"
                assert isinstance(agent_metadata.name, str), f"Agent {agent_id} 'name' is not a string"
                
                assert agent_metadata.category is not None, f"Agent {agent_id} missing 'category' field"
                assert agent_metadata.category in ["production", "example", "test", "system"], \
                    f"Agent {agent_id} has invalid category: {agent_metadata.category}"
                
                assert agent_metadata.environment is not None, f"Agent {agent_id} missing 'environment' field"
                assert agent_metadata.environment in ["production", "staging", "demo", "test"], \
                    f"Agent {agent_id} has invalid environment: {agent_metadata.environment}"
                
                assert agent_metadata.owner is not None, f"Agent {agent_id} missing 'owner' field"
                assert isinstance(agent_metadata.owner, str), f"Agent {agent_id} 'owner' is not a string"
                
                assert agent_metadata.version is not None, f"Agent {agent_id} missing 'version' field"
                assert isinstance(agent_metadata.version, str), f"Agent {agent_id} 'version' is not a string"
                
                assert agent_metadata.location is not None, f"Agent {agent_id} missing 'location' field"
                assert isinstance(agent_metadata.location, Path), f"Agent {agent_id} 'location' is not a Path"
                
                assert agent_metadata.deprecated is not None, f"Agent {agent_id} missing 'deprecated' field"
                assert isinstance(agent_metadata.deprecated, bool), f"Agent {agent_id} 'deprecated' is not a boolean"
                
                assert agent_metadata.status is not None, f"Agent {agent_id} missing 'status' field"
                assert isinstance(agent_metadata.status, str), f"Agent {agent_id} 'status' is not a string"
                
                # Verify OPTIONAL fields have correct types when present
                if agent_metadata.description is not None:
                    assert isinstance(agent_metadata.description, str), \
                        f"Agent {agent_id} 'description' is not a string"
                
                if agent_metadata.tags is not None:
                    assert isinstance(agent_metadata.tags, list), \
                        f"Agent {agent_id} 'tags' is not a list"
                    for tag in agent_metadata.tags:
                        assert isinstance(tag, str), \
                            f"Agent {agent_id} has non-string tag: {tag}"
                
                # Verify the metadata matches the original config
                original_config = config["agents"][agent_id]
                assert agent_metadata.name == original_config["name"]
                assert agent_metadata.category == original_config["category"]
                assert agent_metadata.environment == original_config["environment"]
                assert agent_metadata.owner == original_config["owner"]
                assert agent_metadata.version == original_config["version"]
                assert str(agent_metadata.location) == original_config["location"]
                assert agent_metadata.deprecated == original_config["deprecated"]
                
                # Verify optional fields match if present in config
                if "tags" in original_config:
                    assert agent_metadata.tags == original_config["tags"]
                if "description" in original_config and original_config["description"] is not None:
                    assert agent_metadata.description == original_config["description"]
            
            # Property: Querying all agents should return the same count as in config
            all_agents = registry.list_agents()
            assert len(all_agents) == len(config["agents"]), \
                f"Agent count mismatch: expected {len(config['agents'])}, got {len(all_agents)}"
            
        finally:
            # Cleanup
            config_path.unlink()

    # Feature: project-production-readiness, Property 4: Registry hot reload consistency
    @settings(max_examples=100)
    @given(
        initial_config=registry_config_dict(),
        modified_config=registry_config_dict()
    )
    def test_registry_hot_reload_consistency(self, initial_config, modified_config):
        """
        Property 4: Registry hot reload consistency
        
        For any registry configuration file, after modifying the file and
        triggering reload, the in-memory registry should reflect the changes.
        
        Validates: Requirements 2.4
        """
        # Create a temporary config file with initial configuration
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(initial_config, f)
            config_path = Path(f.name)
        
        try:
            # Load the registry with initial config
            registry = AgentRegistry(config_path=config_path, enable_hot_reload=False)
            initial_count = registry.agent_count
            initial_agent_ids = set(registry._agents.keys())
            
            # Verify initial state
            assert registry.agent_count == len(initial_config["agents"])
            for agent_id in initial_config["agents"].keys():
                assert agent_id in registry._agents
            
            # Modify the config file with new configuration
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(modified_config, f)
            
            # Trigger reload
            registry.reload_registry()
            
            # Property: After reload, registry should reflect the modified config
            modified_agent_ids = set(registry._agents.keys())
            expected_agent_ids = set(modified_config["agents"].keys())
            
            # Verify agent IDs match the modified config
            assert modified_agent_ids == expected_agent_ids, \
                f"Agent IDs don't match after reload. Expected: {expected_agent_ids}, Got: {modified_agent_ids}"
            
            # Verify agent count matches modified config
            assert registry.agent_count == len(modified_config["agents"]), \
                f"Agent count mismatch after reload. Expected: {len(modified_config['agents'])}, Got: {registry.agent_count}"
            
            # Property: Each agent in the modified config should be queryable with correct metadata
            for agent_id, agent_config in modified_config["agents"].items():
                loaded_agent = registry.get_agent(agent_id)
                
                # Verify metadata matches the modified config
                assert loaded_agent.id == agent_id
                assert loaded_agent.name == agent_config["name"]
                assert loaded_agent.category == agent_config["category"]
                assert loaded_agent.environment == agent_config["environment"]
                assert loaded_agent.owner == agent_config["owner"]
                assert loaded_agent.version == agent_config["version"]
                assert str(loaded_agent.location) == agent_config["location"]
                assert loaded_agent.deprecated == agent_config["deprecated"]
                
                # Verify optional fields
                if "tags" in agent_config:
                    assert loaded_agent.tags == agent_config["tags"]
                if "description" in agent_config and agent_config["description"] is not None:
                    assert loaded_agent.description == agent_config["description"]
            
            # Property: Agents from initial config that are not in modified config should be removed
            removed_agents = initial_agent_ids - expected_agent_ids
            for agent_id in removed_agents:
                with pytest.raises(KeyError):
                    registry.get_agent(agent_id)
            
            # Property: New agents in modified config should be accessible
            new_agents = expected_agent_ids - initial_agent_ids
            for agent_id in new_agents:
                # Should not raise KeyError
                agent = registry.get_agent(agent_id)
                assert agent is not None
                assert agent.id == agent_id
            
        finally:
            # Cleanup
            config_path.unlink()
