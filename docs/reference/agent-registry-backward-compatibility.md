# Agent Registry Backward Compatibility Guide

## Overview

The `src/agent_registry.py` module has been updated to integrate with the new AgentRegistry v2 system while maintaining full backward compatibility with existing code. This guide explains the changes and how to use the new features.

## What Changed

### Internal Implementation

The `agent_registry.py` module now uses `agent_registry_v2.AgentRegistry` internally for:
- Loading agent metadata from the central registry configuration
- Querying and filtering agents
- Searching agents by various criteria

### Backward Compatibility

All existing functions maintain their original signatures and behavior:
- `load_agent(agent_id: str) -> AgentConfig`
- `list_available_agents(category: Optional[str] = None, include_deprecated: bool = True) -> List[str]`
- `find_prompt_file(agent_id: str, flow_file: str) -> Path`
- `find_testset_file(agent_id: str, testset_file: str) -> Path`
- `get_agent_summary(agent_id: str) -> str`

### New Features

New functions have been added to expose AgentRegistry v2 functionality:

```python
# Get the global registry instance
registry = get_registry()

# Reload the registry
reload_registry()

# Search agents by text query
results = search_agents("memory", case_sensitive=False)

# Get agents by tag
memory_agents = get_agents_by_tag("memory")

# Get agents by owner
team_agents = get_agents_by_owner("memory-team")
```

## How It Works

### Metadata Priority

When loading an agent, the system uses the following priority for metadata:

1. **AgentRegistry v2**: If the agent is registered in `config/agent_registry.yaml`, metadata from the registry is used for classification fields (category, environment, owner, version, tags, deprecated)
2. **agent.yaml**: Agent-specific configuration (flows, testsets, evaluation) is always loaded from the agent's `agent.yaml` file
3. **Fallback**: If the agent is not in the registry, all metadata is loaded from `agent.yaml`

### Example

```python
from src.agent_registry import load_agent

# Load agent - uses registry v2 for metadata
agent = load_agent("mem0_l1_summarizer")

# Registry v2 provides:
print(agent.category)      # "production"
print(agent.environment)   # "production"
print(agent.owner)         # "memory-team"
print(agent.version)       # "1.2.0"

# agent.yaml provides:
print(agent.flows)         # [AgentFlow(...), ...]
print(agent.default_testset)  # "mem0_l1.jsonl"
```

## CLI Enhancements

The `python -m src.run_agents` CLI has been enhanced with new commands and options:

### List Command (Enhanced)

```bash
# List all agents
python -m src.run_agents list

# Filter by category
python -m src.run_agents list --category production

# Filter by environment
python -m src.run_agents list --environment production

# Filter by tag
python -m src.run_agents list --tag memory

# Filter by owner
python -m src.run_agents list --owner memory-team

# Exclude deprecated agents
python -m src.run_agents list --no-deprecated
```

### Search Command (New)

```bash
# Search agents by text
python -m src.run_agents search "记忆"

# Case-sensitive search
python -m src.run_agents search "Memory" --case-sensitive
```

### Info Command (New)

```bash
# Show registry statistics
python -m src.run_agents info
```

### Reload Command (New)

```bash
# Reload the registry
python -m src.run_agents reload
```

## Migration Guide

### For Existing Code

No changes required! All existing code continues to work:

```python
# This still works exactly as before
from src.agent_registry import load_agent, list_available_agents

agents = list_available_agents()
agent = load_agent("mem0_l1_summarizer")
```

### For New Code

Consider using the new features:

```python
from src.agent_registry import (
    load_agent,
    list_available_agents,
    search_agents,
    get_agents_by_tag,
    get_registry,
)

# Use enhanced filtering
production_agents = list_available_agents(category="production")

# Use search
results = search_agents("memory")

# Use tag filtering
memory_agents = get_agents_by_tag("memory")

# Access registry v2 directly for advanced features
registry = get_registry()
if registry:
    agents = registry.list_agents(
        category="production",
        environment="production",
        tags=["memory"],
    )
```

## Fallback Behavior

If the AgentRegistry v2 system is not available (e.g., config file missing), the system automatically falls back to filesystem-only mode:

- `load_agent()` loads from agent.yaml files
- `list_available_agents()` scans the filesystem
- New functions return empty results or use simple filtering

This ensures the system continues to work even without the registry configuration.

## Benefits

### For Developers

1. **Centralized Metadata**: Agent classification metadata is managed in one place
2. **Enhanced Filtering**: More powerful filtering and search capabilities
3. **Better Organization**: Clear separation between production, example, and test agents
4. **Hot Reload**: Registry can be reloaded without restarting the application

### For Operations

1. **Easy Management**: Update agent metadata without modifying agent.yaml files
2. **Consistency**: Ensure consistent categorization across all agents
3. **Visibility**: Better overview of all agents in the system
4. **Deprecation**: Easy marking and filtering of deprecated agents

## See Also

- [Agent Registry v2 Guide](./agent-registry-guide.md)
- [Agent Registry Schema](./agent-registry-schema.md)
- [Agent Registry Sync Guide](./agent-registry-sync-guide.md)
