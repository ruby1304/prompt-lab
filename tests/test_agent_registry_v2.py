"""
Unit tests for Agent Registry V2

Tests the core functionality of the unified agent registry system.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from datetime import datetime

from src.agent_registry_v2 import (
    AgentRegistry,
    AgentMetadata,
    SyncResult,
    ReloadEvent,
)


class TestAgentMetadata:
    """Test AgentMetadata class"""
    
    def test_agent_metadata_creation(self):
        """Test creating AgentMetadata"""
        metadata = AgentMetadata(
            id="test_agent",
            name="Test Agent",
            category="test",
            environment="test",
            owner="test-team",
            version="1.0.0",
            location=Path("agents/test_agent"),
            deprecated=False,
        )
        
        assert metadata.id == "test_agent"
        assert metadata.name == "Test Agent"
        assert metadata.category == "test"
        assert metadata.environment == "test"
        assert metadata.owner == "test-team"
        assert metadata.version == "1.0.0"
        assert metadata.location == Path("agents/test_agent")
        assert metadata.deprecated is False
        assert metadata.status == "active"
    
    def test_agent_metadata_with_optional_fields(self):
        """Test AgentMetadata with optional fields"""
        metadata = AgentMetadata(
            id="test_agent",
            name="Test Agent",
            category="production",
            environment="production",
            owner="test-team",
            version="1.0.0",
            location=Path("agents/test_agent"),
            deprecated=False,
            description="Test description",
            tags=["test", "example"],
            business_goal="Test goal",
        )
        
        assert metadata.description == "Test description"
        assert metadata.tags == ["test", "example"]
        assert metadata.business_goal == "Test goal"
    
    def test_agent_metadata_to_dict(self):
        """Test converting AgentMetadata to dictionary"""
        metadata = AgentMetadata(
            id="test_agent",
            name="Test Agent",
            category="test",
            environment="test",
            owner="test-team",
            version="1.0.0",
            location=Path("agents/test_agent"),
            deprecated=False,
            tags=["test"],
        )
        
        result = metadata.to_dict()
        
        assert result["id"] == "test_agent"
        assert result["name"] == "Test Agent"
        assert result["category"] == "test"
        assert result["tags"] == ["test"]
        assert result["location"] == "agents/test_agent"
    
    def test_agent_metadata_from_dict(self):
        """Test creating AgentMetadata from dictionary"""
        data = {
            "name": "Test Agent",
            "category": "test",
            "environment": "test",
            "owner": "test-team",
            "version": "1.0.0",
            "location": "agents/test_agent",
            "deprecated": False,
            "tags": ["test"],
        }
        
        metadata = AgentMetadata.from_dict("test_agent", data)
        
        assert metadata.id == "test_agent"
        assert metadata.name == "Test Agent"
        assert metadata.tags == ["test"]


class TestSyncResult:
    """Test SyncResult class"""
    
    def test_sync_result_empty(self):
        """Test empty SyncResult"""
        result = SyncResult()
        
        assert not result.has_changes
        assert not result.has_errors
        assert result.summary() == "No changes"
    
    def test_sync_result_with_changes(self):
        """Test SyncResult with changes"""
        result = SyncResult(
            added=["agent1", "agent2"],
            updated=["agent3"],
            removed=["agent4"],
        )
        
        assert result.has_changes
        assert not result.has_errors
        assert "Added: 2 agents" in result.summary()
        assert "Updated: 1 agents" in result.summary()
        assert "Removed: 1 agents" in result.summary()
    
    def test_sync_result_with_errors(self):
        """Test SyncResult with errors"""
        result = SyncResult(
            errors=["Error 1", "Error 2"],
        )
        
        assert not result.has_changes
        assert result.has_errors
        assert "Errors: 2" in result.summary()


class TestAgentRegistry:
    """Test AgentRegistry class"""
    
    @pytest.fixture
    def temp_registry_config(self, tmp_path):
        """Create a temporary registry config file"""
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
                    "tags": ["test", "example"],
                },
                "test_agent_2": {
                    "name": "Test Agent 2",
                    "category": "production",
                    "environment": "production",
                    "owner": "prod-team",
                    "version": "2.0.0",
                    "location": "agents/test_agent_2",
                    "deprecated": False,
                    "tags": ["production"],
                },
                "deprecated_agent": {
                    "name": "Deprecated Agent",
                    "category": "test",
                    "environment": "test",
                    "owner": "test-team",
                    "version": "0.1.0",
                    "location": "agents/deprecated_agent",
                    "deprecated": True,
                    "tags": ["deprecated"],
                },
            },
        }
        
        config_path = tmp_path / "agent_registry.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)
        
        return config_path
    
    def test_registry_initialization(self, temp_registry_config):
        """Test initializing AgentRegistry"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        assert registry.agent_count == 3
        assert "test_agent_1" in registry._agents
        assert "test_agent_2" in registry._agents
        assert "deprecated_agent" in registry._agents
    
    def test_load_registry(self, temp_registry_config):
        """Test loading registry from config file"""
        registry = AgentRegistry(config_path=temp_registry_config)
        agents = registry.load_registry()
        
        assert len(agents) == 3
        assert "test_agent_1" in agents
        assert agents["test_agent_1"].name == "Test Agent 1"
    
    def test_load_registry_file_not_found(self, tmp_path):
        """Test loading registry with non-existent file"""
        config_path = tmp_path / "nonexistent.yaml"
        
        with pytest.raises(FileNotFoundError):
            registry = AgentRegistry(config_path=config_path)
            registry.load_registry()
    
    def test_load_registry_invalid_yaml(self, tmp_path):
        """Test loading registry with invalid YAML"""
        config_path = tmp_path / "invalid.yaml"
        with open(config_path, "w") as f:
            f.write("invalid: yaml: content:")
        
        with pytest.raises(yaml.YAMLError):
            registry = AgentRegistry(config_path=config_path)
    
    def test_load_registry_missing_agents_key(self, tmp_path):
        """Test loading registry without 'agents' key"""
        config_path = tmp_path / "no_agents.yaml"
        with open(config_path, "w") as f:
            yaml.dump({"version": "1.0"}, f)
        
        with pytest.raises(ValueError, match="must contain 'agents' key"):
            registry = AgentRegistry(config_path=config_path)
    
    def test_get_agent(self, temp_registry_config):
        """Test getting agent by ID"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        agent = registry.get_agent("test_agent_1")
        
        assert agent.id == "test_agent_1"
        assert agent.name == "Test Agent 1"
        assert agent.category == "test"
    
    def test_get_agent_not_found(self, temp_registry_config):
        """Test getting non-existent agent"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        with pytest.raises(KeyError, match="not found in registry"):
            registry.get_agent("nonexistent_agent")
    
    def test_list_agents_no_filter(self, temp_registry_config):
        """Test listing all agents"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        agents = registry.list_agents()
        
        assert len(agents) == 3
    
    def test_list_agents_filter_by_category(self, temp_registry_config):
        """Test listing agents filtered by category"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        agents = registry.list_agents(category="production")
        
        assert len(agents) == 1
        assert agents[0].id == "test_agent_2"
    
    def test_list_agents_filter_by_environment(self, temp_registry_config):
        """Test listing agents filtered by environment"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        agents = registry.list_agents(environment="production")
        
        assert len(agents) == 1
        assert agents[0].id == "test_agent_2"
    
    def test_list_agents_exclude_deprecated(self, temp_registry_config):
        """Test listing agents excluding deprecated"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        agents = registry.list_agents(include_deprecated=False)
        
        assert len(agents) == 2
        assert all(not agent.deprecated for agent in agents)
    
    def test_list_agents_filter_by_tags(self, temp_registry_config):
        """Test listing agents filtered by tags"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        agents = registry.list_agents(tags=["test"])
        
        assert len(agents) == 1
        assert agents[0].id == "test_agent_1"
    
    def test_list_agents_multiple_filters(self, temp_registry_config):
        """Test listing agents with multiple filters"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        agents = registry.list_agents(
            category="test",
            include_deprecated=False,
        )
        
        assert len(agents) == 1
        assert agents[0].id == "test_agent_1"
    
    def test_search_agents_by_name(self, temp_registry_config):
        """Test searching agents by name"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        agents = registry.search_agents("Agent 1")
        
        assert len(agents) == 1
        assert agents[0].id == "test_agent_1"
    
    def test_search_agents_by_id(self, temp_registry_config):
        """Test searching agents by ID"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        agents = registry.search_agents("test_agent_2")
        
        assert len(agents) == 1
        assert agents[0].id == "test_agent_2"
    
    def test_search_agents_by_tag(self, temp_registry_config):
        """Test searching agents by tag"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        agents = registry.search_agents("production")
        
        assert len(agents) == 1
        assert agents[0].id == "test_agent_2"
    
    def test_search_agents_case_insensitive(self, temp_registry_config):
        """Test case-insensitive search"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        agents = registry.search_agents("AGENT 1", case_sensitive=False)
        
        assert len(agents) == 1
        assert agents[0].id == "test_agent_1"
    
    def test_get_agents_by_tag(self, temp_registry_config):
        """Test getting agents by specific tag"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        agents = registry.get_agents_by_tag("test")
        
        assert len(agents) == 1
        assert agents[0].id == "test_agent_1"
    
    def test_get_agents_by_owner(self, temp_registry_config):
        """Test getting agents by owner"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        agents = registry.get_agents_by_owner("test-team")
        
        assert len(agents) == 2
    
    def test_register_agent(self, temp_registry_config):
        """Test registering a new agent"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        new_agent = AgentMetadata(
            id="new_agent",
            name="New Agent",
            category="test",
            environment="test",
            owner="test-team",
            version="1.0.0",
            location=Path("agents/new_agent"),
            deprecated=False,
        )
        
        registry.register_agent("new_agent", new_agent)
        
        assert registry.agent_count == 4
        assert registry.get_agent("new_agent").name == "New Agent"
    
    def test_register_agent_id_mismatch(self, temp_registry_config):
        """Test registering agent with mismatched ID"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        new_agent = AgentMetadata(
            id="new_agent",
            name="New Agent",
            category="test",
            environment="test",
            owner="test-team",
            version="1.0.0",
            location=Path("agents/new_agent"),
            deprecated=False,
        )
        
        with pytest.raises(ValueError, match="Agent ID mismatch"):
            registry.register_agent("different_id", new_agent)
    
    def test_update_agent(self, temp_registry_config):
        """Test updating an existing agent"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        agent = registry.get_agent("test_agent_1")
        agent.name = "Updated Name"
        
        registry.update_agent("test_agent_1", agent)
        
        updated_agent = registry.get_agent("test_agent_1")
        assert updated_agent.name == "Updated Name"
    
    def test_update_agent_not_found(self, temp_registry_config):
        """Test updating non-existent agent"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        new_agent = AgentMetadata(
            id="nonexistent",
            name="New Agent",
            category="test",
            environment="test",
            owner="test-team",
            version="1.0.0",
            location=Path("agents/nonexistent"),
            deprecated=False,
        )
        
        with pytest.raises(KeyError, match="not found in registry"):
            registry.update_agent("nonexistent", new_agent)
    
    def test_remove_agent(self, temp_registry_config):
        """Test removing an agent"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        registry.remove_agent("test_agent_1")
        
        assert registry.agent_count == 2
        with pytest.raises(KeyError):
            registry.get_agent("test_agent_1")
    
    def test_remove_agent_not_found(self, temp_registry_config):
        """Test removing non-existent agent"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        with pytest.raises(KeyError, match="not found in registry"):
            registry.remove_agent("nonexistent")
    
    def test_reload_registry(self, temp_registry_config):
        """Test reloading registry"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        initial_count = registry.agent_count
        
        # Modify the config file
        with open(temp_registry_config, "r") as f:
            config = yaml.safe_load(f)
        
        config["agents"]["new_agent"] = {
            "name": "New Agent",
            "category": "test",
            "environment": "test",
            "owner": "test-team",
            "version": "1.0.0",
            "location": "agents/new_agent",
            "deprecated": False,
        }
        
        with open(temp_registry_config, "w") as f:
            yaml.dump(config, f)
        
        # Reload
        registry.reload_registry()
        
        assert registry.agent_count == initial_count + 1
        assert "new_agent" in registry._agents
    
    def test_registry_properties(self, temp_registry_config):
        """Test registry properties"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        assert registry.agent_count == 3
        assert "test" in registry.categories
        assert "production" in registry.categories
        assert "test" in registry.environments
        assert "production" in registry.environments
        assert "test" in registry.all_tags
        assert "production" in registry.all_tags
    
    def test_get_statistics(self, temp_registry_config):
        """Test getting registry statistics"""
        registry = AgentRegistry(config_path=temp_registry_config)
        
        stats = registry.get_statistics()
        
        assert stats["total_agents"] == 3
        assert stats["by_category"]["test"] == 2
        assert stats["by_category"]["production"] == 1
        assert stats["deprecated_count"] == 1
        assert stats["last_loaded"] is not None
        assert "hot_reload_enabled" in stats


class TestHotReload:
    """Test hot reload functionality"""
    
    @pytest.fixture
    def temp_registry_config(self, tmp_path):
        """Create a temporary registry config file"""
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
                    "tags": ["test"],
                },
            },
        }
        
        config_path = tmp_path / "agent_registry.yaml"
        with open(config_path, "w") as f:
            yaml.dump(config, f)
        
        return config_path
    
    def test_start_hot_reload(self, temp_registry_config):
        """Test starting hot reload"""
        registry = AgentRegistry(config_path=temp_registry_config, enable_hot_reload=False)
        
        assert not registry._hot_reload_enabled
        assert registry._file_observer is None
        
        registry.start_hot_reload()
        
        assert registry._hot_reload_enabled
        assert registry._file_observer is not None
        
        # Cleanup
        registry.stop_hot_reload()
    
    def test_stop_hot_reload(self, temp_registry_config):
        """Test stopping hot reload"""
        registry = AgentRegistry(config_path=temp_registry_config, enable_hot_reload=True)
        
        assert registry._hot_reload_enabled
        assert registry._file_observer is not None
        
        registry.stop_hot_reload()
        
        assert not registry._hot_reload_enabled
        assert registry._file_observer is None
    
    def test_hot_reload_on_file_change(self, temp_registry_config):
        """Test automatic reload when config file changes"""
        import time
        
        registry = AgentRegistry(config_path=temp_registry_config, enable_hot_reload=True)
        
        initial_count = registry.agent_count
        assert initial_count == 1
        
        # Modify the config file
        with open(temp_registry_config, "r") as f:
            config = yaml.safe_load(f)
        
        config["agents"]["new_agent"] = {
            "name": "New Agent",
            "category": "test",
            "environment": "test",
            "owner": "test-team",
            "version": "1.0.0",
            "location": "agents/new_agent",
            "deprecated": False,
        }
        
        with open(temp_registry_config, "w") as f:
            yaml.dump(config, f)
        
        # Wait for file watcher to detect change and reload
        time.sleep(2)
        
        # Check that registry was reloaded
        assert registry.agent_count == 2
        assert "new_agent" in registry._agents
        
        # Cleanup
        registry.stop_hot_reload()
    
    def test_reload_callback(self, temp_registry_config):
        """Test reload callback notification"""
        import time
        from src.agent_registry_v2 import ReloadEvent
        
        registry = AgentRegistry(config_path=temp_registry_config, enable_hot_reload=True)
        
        # Track callback invocations
        callback_events = []
        
        def on_reload(event: ReloadEvent):
            callback_events.append(event)
        
        registry.add_reload_callback(on_reload)
        
        # Modify the config file
        with open(temp_registry_config, "r") as f:
            config = yaml.safe_load(f)
        
        config["agents"]["new_agent"] = {
            "name": "New Agent",
            "category": "test",
            "environment": "test",
            "owner": "test-team",
            "version": "1.0.0",
            "location": "agents/new_agent",
            "deprecated": False,
        }
        
        with open(temp_registry_config, "w") as f:
            yaml.dump(config, f)
        
        # Wait for reload
        time.sleep(2)
        
        # Check that callback was invoked
        assert len(callback_events) > 0
        event = callback_events[0]
        assert event.success
        assert event.agents_count == 2
        assert event.previous_count == 1
        
        # Cleanup
        registry.stop_hot_reload()
    
    def test_reload_callback_on_error(self, temp_registry_config):
        """Test reload callback on error"""
        import time
        from src.agent_registry_v2 import ReloadEvent
        
        registry = AgentRegistry(config_path=temp_registry_config, enable_hot_reload=True)
        
        # Track callback invocations
        callback_events = []
        
        def on_reload(event: ReloadEvent):
            callback_events.append(event)
        
        registry.add_reload_callback(on_reload)
        
        # Write invalid YAML to config file
        with open(temp_registry_config, "w") as f:
            f.write("invalid: yaml: content:")
        
        # Wait for reload attempt
        time.sleep(2)
        
        # Check that callback was invoked with error
        assert len(callback_events) > 0
        event = callback_events[0]
        assert not event.success
        assert event.error is not None
        
        # Cleanup
        registry.stop_hot_reload()
    
    def test_remove_reload_callback(self, temp_registry_config):
        """Test removing reload callback"""
        registry = AgentRegistry(config_path=temp_registry_config, enable_hot_reload=False)
        
        callback_count = [0]
        
        def on_reload(event):
            callback_count[0] += 1
        
        registry.add_reload_callback(on_reload)
        assert len(registry._reload_callbacks) == 1
        
        registry.remove_reload_callback(on_reload)
        assert len(registry._reload_callbacks) == 0
    
    def test_multiple_reload_callbacks(self, temp_registry_config):
        """Test multiple reload callbacks"""
        import time
        
        registry = AgentRegistry(config_path=temp_registry_config, enable_hot_reload=True)
        
        callback1_events = []
        callback2_events = []
        
        def callback1(event):
            callback1_events.append(event)
        
        def callback2(event):
            callback2_events.append(event)
        
        registry.add_reload_callback(callback1)
        registry.add_reload_callback(callback2)
        
        # Modify the config file
        with open(temp_registry_config, "r") as f:
            config = yaml.safe_load(f)
        
        config["agents"]["new_agent"] = {
            "name": "New Agent",
            "category": "test",
            "environment": "test",
            "owner": "test-team",
            "version": "1.0.0",
            "location": "agents/new_agent",
            "deprecated": False,
        }
        
        with open(temp_registry_config, "w") as f:
            yaml.dump(config, f)
        
        # Wait for reload
        time.sleep(2)
        
        # Check that both callbacks were invoked
        assert len(callback1_events) > 0
        assert len(callback2_events) > 0
        
        # Cleanup
        registry.stop_hot_reload()
    
    def test_hot_reload_enabled_on_init(self, temp_registry_config):
        """Test hot reload enabled on initialization"""
        registry = AgentRegistry(config_path=temp_registry_config, enable_hot_reload=True)
        
        assert registry._hot_reload_enabled
        assert registry._file_observer is not None
        
        stats = registry.get_statistics()
        assert stats["hot_reload_enabled"] is True
        
        # Cleanup
        registry.stop_hot_reload()
    
    def test_start_hot_reload_already_running(self, temp_registry_config):
        """Test starting hot reload when already running"""
        registry = AgentRegistry(config_path=temp_registry_config, enable_hot_reload=True)
        
        with pytest.raises(RuntimeError, match="already running"):
            registry.start_hot_reload()
        
        # Cleanup
        registry.stop_hot_reload()
    
    def test_stop_hot_reload_not_running(self, temp_registry_config):
        """Test stopping hot reload when not running"""
        registry = AgentRegistry(config_path=temp_registry_config, enable_hot_reload=False)
        
        # Should not raise an error
        registry.stop_hot_reload()
        
        assert not registry._hot_reload_enabled
        assert registry._file_observer is None
