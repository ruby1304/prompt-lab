"""
Integration tests for agent_registry.py backward compatibility with agent_registry_v2.py

This test suite verifies that the updated agent_registry.py correctly integrates
with agent_registry_v2.py while maintaining backward compatibility.
"""

import pytest
from pathlib import Path

from src.agent_registry import (
    load_agent,
    list_available_agents,
    get_registry,
    reload_registry,
    search_agents,
    get_agents_by_tag,
    get_agents_by_owner,
    AgentConfig,
)
from src.agent_registry_v2 import AgentRegistry


class TestAgentRegistryIntegration:
    """Test integration between agent_registry.py and agent_registry_v2.py"""
    
    def test_get_registry_returns_v2_instance(self):
        """Test that get_registry returns an AgentRegistry v2 instance"""
        registry = get_registry()
        assert registry is not None
        assert isinstance(registry, AgentRegistry)
    
    def test_load_agent_returns_agent_config(self):
        """Test that load_agent returns AgentConfig with v2 metadata"""
        agent = load_agent("mem0_l1_summarizer")
        
        assert isinstance(agent, AgentConfig)
        assert agent.id == "mem0_l1_summarizer"
        assert agent.name is not None
        assert agent.category is not None
        assert agent.environment is not None
        assert len(agent.flows) > 0
    
    def test_list_available_agents_uses_v2(self):
        """Test that list_available_agents uses v2 registry"""
        agents = list_available_agents()
        
        assert isinstance(agents, list)
        assert len(agents) > 0
        assert all(isinstance(agent_id, str) for agent_id in agents)
    
    def test_list_available_agents_with_filters(self):
        """Test that filtering works with v2 registry"""
        # Filter by category
        production_agents = list_available_agents(category="production")
        assert isinstance(production_agents, list)
        
        # Verify all returned agents are production
        for agent_id in production_agents:
            agent = load_agent(agent_id)
            assert agent.category == "production"
    
    def test_search_agents_integration(self):
        """Test that search_agents works with v2 registry"""
        results = search_agents("记忆")
        
        assert isinstance(results, list)
        # Should find at least the memory agents
        assert len(results) >= 1
    
    def test_get_agents_by_tag_integration(self):
        """Test that get_agents_by_tag works with v2 registry"""
        # Get agents with 'memory' tag
        memory_agents = get_agents_by_tag("memory")
        
        assert isinstance(memory_agents, list)
        # Verify all returned agents have the tag
        for agent_id in memory_agents:
            agent = load_agent(agent_id)
            assert "memory" in (agent.tags or [])
    
    def test_get_agents_by_owner_integration(self):
        """Test that get_agents_by_owner works with v2 registry"""
        # Get agents by owner
        agents = get_agents_by_owner("memory-team")
        
        assert isinstance(agents, list)
        # Verify all returned agents have the correct owner
        for agent_id in agents:
            agent = load_agent(agent_id)
            assert agent.owner == "memory-team"
    
    def test_reload_registry_integration(self):
        """Test that reload_registry works"""
        # Get initial count
        initial_agents = list_available_agents()
        initial_count = len(initial_agents)
        
        # Reload registry
        reload_registry()
        
        # Get count after reload
        reloaded_agents = list_available_agents()
        reloaded_count = len(reloaded_agents)
        
        # Should have same count (no changes to config)
        assert reloaded_count == initial_count
    
    def test_backward_compatibility_with_existing_code(self):
        """Test that existing code patterns still work"""
        # Pattern 1: List and load
        agent_ids = list_available_agents()
        assert len(agent_ids) > 0
        
        first_agent = load_agent(agent_ids[0])
        assert isinstance(first_agent, AgentConfig)
        
        # Pattern 2: Filter by category
        production = list_available_agents(category="production")
        assert isinstance(production, list)
        
        # Pattern 3: Load specific agent
        agent = load_agent("mem0_l1_summarizer")
        assert agent.id == "mem0_l1_summarizer"
        assert len(agent.flows) > 0
    
    def test_agent_config_has_v2_metadata(self):
        """Test that AgentConfig includes metadata from v2 registry"""
        agent = load_agent("mem0_l1_summarizer")
        
        # Check that v2 metadata is present
        assert agent.category is not None
        assert agent.environment is not None
        assert agent.owner is not None
        assert agent.version is not None
        
        # Verify it matches v2 registry
        registry = get_registry()
        if registry:
            v2_metadata = registry.get_agent("mem0_l1_summarizer")
            assert agent.category == v2_metadata.category
            assert agent.environment == v2_metadata.environment
            assert agent.owner == v2_metadata.owner
            assert agent.version == v2_metadata.version
    
    def test_fallback_when_agent_not_in_registry(self):
        """Test that system falls back to filesystem when agent not in v2 registry"""
        # This test assumes there might be agents in filesystem not in registry
        # The system should still be able to load them
        all_agents = list_available_agents()
        
        # Try to load each agent - should not fail
        for agent_id in all_agents:
            agent = load_agent(agent_id)
            assert isinstance(agent, AgentConfig)
            assert agent.id == agent_id


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
