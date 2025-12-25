"""
Tests for Agent Registry Sync Tool

This module tests the sync_agent_registry.py script functionality.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch
import yaml

# Import the sync script modules
import sys
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.sync_agent_registry import (
    AgentScanner,
    RegistrySyncer,
)
from src.agent_registry_v2 import AgentMetadata


@pytest.fixture
def temp_project_dir():
    """Create a temporary project directory structure"""
    temp_dir = Path(tempfile.mkdtemp())
    
    # Create directory structure
    agents_dir = temp_dir / "agents"
    agents_dir.mkdir()
    
    examples_dir = temp_dir / "examples" / "agents"
    examples_dir.mkdir(parents=True)
    
    config_dir = temp_dir / "config"
    config_dir.mkdir()
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_agent_config():
    """Sample agent.yaml configuration"""
    return {
        "id": "test_agent",
        "name": "Test Agent",
        "type": "task",
        "description": "A test agent for testing",
        "business_goal": "Test business goal",
        "flows": [
            {"name": "test_v1", "file": "test_v1.yaml"}
        ]
    }


def create_agent_directory(base_dir: Path, agent_id: str, config: dict):
    """Helper to create an agent directory with config"""
    agent_dir = base_dir / agent_id
    agent_dir.mkdir(parents=True, exist_ok=True)
    
    # Create agent.yaml
    config_file = agent_dir / "agent.yaml"
    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)
    
    return agent_dir


class TestAgentScanner:
    """Tests for AgentScanner class"""
    
    def test_scan_directory_finds_agents(self, temp_project_dir, sample_agent_config):
        """Test that scanner finds agent directories"""
        agents_dir = temp_project_dir / "agents"
        
        # Create test agents
        create_agent_directory(agents_dir, "agent1", sample_agent_config)
        create_agent_directory(agents_dir, "agent2", sample_agent_config)
        
        # Scan
        scanner = AgentScanner(temp_project_dir)
        agents = scanner.scan_directory(agents_dir)
        
        assert len(agents) == 2
        assert "agent1" in agents
        assert "agent2" in agents
    
    def test_scan_directory_excludes_patterns(self, temp_project_dir, sample_agent_config):
        """Test that scanner excludes specified patterns"""
        agents_dir = temp_project_dir / "agents"
        
        # Create agents with different patterns
        create_agent_directory(agents_dir, "agent1", sample_agent_config)
        create_agent_directory(agents_dir, "_template", sample_agent_config)
        create_agent_directory(agents_dir, ".hidden", sample_agent_config)
        
        # Scan with default exclusions
        scanner = AgentScanner(temp_project_dir)
        agents = scanner.scan_directory(agents_dir)
        
        assert len(agents) == 1
        assert "agent1" in agents
        assert "_template" not in agents
        assert ".hidden" not in agents
    
    def test_scan_directory_requires_agent_yaml(self, temp_project_dir):
        """Test that scanner only includes directories with agent.yaml"""
        agents_dir = temp_project_dir / "agents"
        
        # Create directory without agent.yaml
        no_config_dir = agents_dir / "no_config"
        no_config_dir.mkdir()
        
        # Create directory with agent.yaml
        with_config_dir = agents_dir / "with_config"
        with_config_dir.mkdir()
        (with_config_dir / "agent.yaml").write_text("id: test")
        
        # Scan
        scanner = AgentScanner(temp_project_dir)
        agents = scanner.scan_directory(agents_dir)
        
        assert len(agents) == 1
        assert "with_config" in agents
        assert "no_config" not in agents
    
    def test_load_agent_config(self, temp_project_dir, sample_agent_config):
        """Test loading agent configuration"""
        agents_dir = temp_project_dir / "agents"
        agent_dir = create_agent_directory(agents_dir, "test_agent", sample_agent_config)
        
        scanner = AgentScanner(temp_project_dir)
        config = scanner.load_agent_config(agent_dir)
        
        assert config is not None
        assert config["id"] == "test_agent"
        assert config["name"] == "Test Agent"
    
    def test_infer_metadata_from_config(self, temp_project_dir, sample_agent_config):
        """Test inferring metadata from agent config"""
        agents_dir = temp_project_dir / "agents"
        agent_dir = create_agent_directory(agents_dir, "test_agent", sample_agent_config)
        
        scanner = AgentScanner(temp_project_dir)
        metadata = scanner.infer_metadata_from_config(
            "test_agent",
            agent_dir,
            sample_agent_config
        )
        
        assert isinstance(metadata, AgentMetadata)
        assert metadata.id == "test_agent"
        assert metadata.name == "Test Agent"
        assert metadata.category == "production"
        assert metadata.environment == "production"
        assert metadata.location == Path("agents/test_agent")
    
    def test_infer_metadata_category_from_location(self, temp_project_dir, sample_agent_config):
        """Test that category is inferred from location"""
        scanner = AgentScanner(temp_project_dir)
        
        # Test example agent
        examples_dir = temp_project_dir / "examples" / "agents"
        example_dir = create_agent_directory(examples_dir, "example_agent", sample_agent_config)
        metadata = scanner.infer_metadata_from_config(
            "example_agent",
            example_dir,
            sample_agent_config
        )
        assert metadata.category == "example"
        assert metadata.environment == "demo"
        
        # Test system agent
        agents_dir = temp_project_dir / "agents"
        judge_config = {**sample_agent_config, "id": "judge_default"}
        judge_dir = create_agent_directory(agents_dir, "judge_default", judge_config)
        metadata = scanner.infer_metadata_from_config(
            "judge_default",
            judge_dir,
            judge_config
        )
        assert metadata.category == "system"


class TestRegistrySyncer:
    """Tests for RegistrySyncer class"""
    
    def test_create_empty_registry(self, temp_project_dir):
        """Test creating an empty registry structure"""
        registry_path = temp_project_dir / "config" / "agent_registry.yaml"
        syncer = RegistrySyncer(registry_path, temp_project_dir)
        
        registry = syncer._create_empty_registry()
        
        assert "version" in registry
        assert "registry" in registry
        assert "agents" in registry
        assert "config" in registry
        assert registry["agents"] == {}
    
    def test_scan_filesystem(self, temp_project_dir, sample_agent_config):
        """Test scanning filesystem for agents"""
        # Create test agents
        agents_dir = temp_project_dir / "agents"
        create_agent_directory(agents_dir, "agent1", sample_agent_config)
        create_agent_directory(agents_dir, "agent2", sample_agent_config)
        
        # Create registry config
        registry_path = temp_project_dir / "config" / "agent_registry.yaml"
        registry_config = {
            "version": "1.0",
            "agents": {},
            "config": {
                "auto_sync": {
                    "scan_directories": ["agents/"],
                    "exclude_patterns": ["_template", ".*"]
                }
            }
        }
        with open(registry_path, 'w') as f:
            yaml.dump(registry_config, f)
        
        syncer = RegistrySyncer(registry_path, temp_project_dir)
        filesystem_agents = syncer.scan_filesystem()
        
        assert len(filesystem_agents) == 2
        assert "agent1" in filesystem_agents
        assert "agent2" in filesystem_agents
    
    def test_compare_with_registry_detects_new_agents(
        self, temp_project_dir, sample_agent_config
    ):
        """Test detecting new agents not in registry"""
        # Create filesystem agents
        agents_dir = temp_project_dir / "agents"
        agent1_dir = create_agent_directory(agents_dir, "agent1", sample_agent_config)
        agent2_dir = create_agent_directory(agents_dir, "agent2", sample_agent_config)
        
        # Create registry with only agent1
        registry_path = temp_project_dir / "config" / "agent_registry.yaml"
        registry_config = {
            "version": "1.0",
            "agents": {
                "agent1": {
                    "name": "Agent 1",
                    "location": "agents/agent1",
                    "category": "production",
                    "environment": "production",
                    "owner": "test",
                    "version": "1.0.0",
                    "deprecated": False
                }
            }
        }
        with open(registry_path, 'w') as f:
            yaml.dump(registry_config, f)
        
        syncer = RegistrySyncer(registry_path, temp_project_dir)
        filesystem_agents = {
            "agent1": (agent1_dir, sample_agent_config),
            "agent2": (agent2_dir, sample_agent_config)
        }
        
        new, removed, updated, conflicts = syncer.compare_with_registry(filesystem_agents)
        
        assert "agent2" in new
        assert len(removed) == 0
        assert len(updated) == 0
    
    def test_compare_with_registry_detects_removed_agents(
        self, temp_project_dir, sample_agent_config
    ):
        """Test detecting agents removed from filesystem"""
        # Create filesystem with only agent1
        agents_dir = temp_project_dir / "agents"
        agent1_dir = create_agent_directory(agents_dir, "agent1", sample_agent_config)
        
        # Create registry with agent1 and agent2
        registry_path = temp_project_dir / "config" / "agent_registry.yaml"
        registry_config = {
            "version": "1.0",
            "agents": {
                "agent1": {
                    "name": "Agent 1",
                    "location": "agents/agent1",
                    "category": "production",
                    "environment": "production",
                    "owner": "test",
                    "version": "1.0.0",
                    "deprecated": False
                },
                "agent2": {
                    "name": "Agent 2",
                    "location": "agents/agent2",
                    "category": "production",
                    "environment": "production",
                    "owner": "test",
                    "version": "1.0.0",
                    "deprecated": False
                }
            }
        }
        with open(registry_path, 'w') as f:
            yaml.dump(registry_config, f)
        
        syncer = RegistrySyncer(registry_path, temp_project_dir)
        filesystem_agents = {
            "agent1": (agent1_dir, sample_agent_config)
        }
        
        new, removed, updated, conflicts = syncer.compare_with_registry(filesystem_agents)
        
        assert len(new) == 0
        assert "agent2" in removed
        assert len(updated) == 0
    
    def test_compare_with_registry_detects_location_mismatch(
        self, temp_project_dir, sample_agent_config
    ):
        """Test detecting agents with mismatched locations"""
        # Create filesystem agent
        agents_dir = temp_project_dir / "agents"
        agent1_dir = create_agent_directory(agents_dir, "agent1", sample_agent_config)
        
        # Create registry with wrong location
        registry_path = temp_project_dir / "config" / "agent_registry.yaml"
        registry_config = {
            "version": "1.0",
            "agents": {
                "agent1": {
                    "name": "Agent 1",
                    "location": "wrong/path/agent1",  # Wrong location
                    "category": "production",
                    "environment": "production",
                    "owner": "test",
                    "version": "1.0.0",
                    "deprecated": False
                }
            }
        }
        with open(registry_path, 'w') as f:
            yaml.dump(registry_config, f)
        
        syncer = RegistrySyncer(registry_path, temp_project_dir)
        filesystem_agents = {
            "agent1": (agent1_dir, sample_agent_config)
        }
        
        new, removed, updated, conflicts = syncer.compare_with_registry(filesystem_agents)
        
        assert len(new) == 0
        assert len(removed) == 0
        assert "agent1" in updated
        assert "agent1" in conflicts
        assert "Location mismatch" in conflicts["agent1"]
    
    def test_sync_dry_run_does_not_modify_registry(
        self, temp_project_dir, sample_agent_config
    ):
        """Test that dry-run mode doesn't modify the registry"""
        # Create filesystem agent
        agents_dir = temp_project_dir / "agents"
        create_agent_directory(agents_dir, "new_agent", sample_agent_config)
        
        # Create empty registry
        registry_path = temp_project_dir / "config" / "agent_registry.yaml"
        registry_config = {
            "version": "1.0",
            "agents": {},
            "config": {
                "auto_sync": {
                    "scan_directories": ["agents/"],
                    "exclude_patterns": ["_template"]
                }
            }
        }
        with open(registry_path, 'w') as f:
            yaml.dump(registry_config, f)
        
        # Get original content
        original_content = registry_path.read_text()
        
        # Sync in dry-run mode
        syncer = RegistrySyncer(registry_path, temp_project_dir)
        result = syncer.sync(auto_add=True, dry_run=True)
        
        # Verify no changes
        assert registry_path.read_text() == original_content
        assert "new_agent" in result.added
    
    def test_sync_auto_add_adds_new_agents(
        self, temp_project_dir, sample_agent_config
    ):
        """Test that auto-add mode adds new agents to registry"""
        # Create filesystem agent
        agents_dir = temp_project_dir / "agents"
        create_agent_directory(agents_dir, "new_agent", sample_agent_config)
        
        # Create empty registry
        registry_path = temp_project_dir / "config" / "agent_registry.yaml"
        registry_config = {
            "version": "1.0",
            "agents": {},
            "config": {
                "auto_sync": {
                    "scan_directories": ["agents/"],
                    "exclude_patterns": ["_template"]
                }
            }
        }
        with open(registry_path, 'w') as f:
            yaml.dump(registry_config, f)
        
        # Sync with auto-add
        syncer = RegistrySyncer(registry_path, temp_project_dir)
        result = syncer.sync(auto_add=True, dry_run=False)
        
        # Verify agent was added
        assert "new_agent" in result.added
        
        # Load registry and verify
        with open(registry_path, 'r') as f:
            updated_config = yaml.safe_load(f)
        
        assert "new_agent" in updated_config["agents"]
        assert updated_config["agents"]["new_agent"]["name"] == "Test Agent"
    
    def test_generate_new_registry(self, temp_project_dir, sample_agent_config):
        """Test generating a new registry from scratch"""
        # Create filesystem agents
        agents_dir = temp_project_dir / "agents"
        create_agent_directory(agents_dir, "agent1", sample_agent_config)
        create_agent_directory(agents_dir, "agent2", sample_agent_config)
        
        # Create syncer (no existing registry)
        registry_path = temp_project_dir / "config" / "agent_registry.yaml"
        syncer = RegistrySyncer(registry_path, temp_project_dir)
        
        # Generate new registry
        registry_config = syncer.generate_new_registry()
        
        # Verify structure
        assert "version" in registry_config
        assert "registry" in registry_config
        assert "agents" in registry_config
        assert len(registry_config["agents"]) == 2
        assert "agent1" in registry_config["agents"]
        assert "agent2" in registry_config["agents"]


class TestIntegration:
    """Integration tests for the sync tool"""
    
    def test_full_sync_workflow(self, temp_project_dir, sample_agent_config):
        """Test a complete sync workflow"""
        # Setup: Create agents and initial registry
        agents_dir = temp_project_dir / "agents"
        create_agent_directory(agents_dir, "agent1", sample_agent_config)
        
        registry_path = temp_project_dir / "config" / "agent_registry.yaml"
        registry_config = {
            "version": "1.0",
            "agents": {
                "agent1": {
                    "name": "Agent 1",
                    "location": "agents/agent1",
                    "category": "production",
                    "environment": "production",
                    "owner": "test",
                    "version": "1.0.0",
                    "deprecated": False
                }
            },
            "config": {
                "auto_sync": {
                    "scan_directories": ["agents/"],
                    "exclude_patterns": ["_template"]
                }
            }
        }
        with open(registry_path, 'w') as f:
            yaml.dump(registry_config, f)
        
        # Step 1: Add a new agent
        create_agent_directory(agents_dir, "agent2", sample_agent_config)
        
        syncer = RegistrySyncer(registry_path, temp_project_dir)
        result = syncer.sync(auto_add=True, dry_run=False)
        
        assert "agent2" in result.added
        
        # Step 2: Remove an agent
        shutil.rmtree(agents_dir / "agent1")
        
        result = syncer.sync(auto_remove=True, dry_run=False)
        
        assert "agent1" in result.removed
        
        # Verify final state
        with open(registry_path, 'r') as f:
            final_config = yaml.safe_load(f)
        
        assert "agent1" not in final_config["agents"]
        assert "agent2" in final_config["agents"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
