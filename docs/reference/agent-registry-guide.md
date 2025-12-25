# Agent Registry Configuration Guide

## Overview

The Agent Registry is a centralized system for managing, discovering, and organizing all agents in the Prompt Lab platform. It provides:

- **Unified Metadata Management**: Single source of truth for agent information
- **Categorization & Tagging**: Flexible classification system for agent discovery
- **Hot Reload**: Automatic updates when configuration changes
- **Auto-Sync**: Automatic detection of new agents from filesystem
- **Version Control**: Track agent versions and deprecation status

## Configuration File

The Agent Registry configuration is stored in `config/agent_registry.yaml`.

### File Structure

```yaml
version: "1.0"
registry: {...}      # Registry metadata
agents: {...}        # Agent definitions
categories: {...}    # Category definitions
environments: {...}  # Environment definitions
tag_taxonomy: {...}  # Standard tags
config: {...}        # Registry settings
```

## Agent Metadata Fields

### Required Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `name` | string | Human-readable agent name | "对话记忆总结助手" |
| `category` | string | Agent category (see Categories) | "production" |
| `environment` | string | Deployment environment | "production" |
| `owner` | string | Team or person responsible | "memory-team" |
| `version` | string | Semantic version | "1.2.0" |
| `location` | string | Path to agent directory | "agents/mem0_l1_summarizer" |
| `deprecated` | boolean | Whether agent is deprecated | false |

### Optional Fields

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `description` | string | Brief description of agent purpose | "Processes conversation history..." |
| `business_goal` | string | Business objective | "Generate high-quality summaries..." |
| `tags` | array | Classification tags | ["memory", "summarization"] |
| `created_at` | string | Creation date (ISO 8601) | "2024-03-20" |
| `updated_at` | string | Last update date (ISO 8601) | "2025-12-10" |
| `dependencies` | array | Required agents or services | ["judge_default"] |
| `maintainer` | string | Current maintainer | "john.doe@company.com" |
| `documentation_url` | string | Link to detailed docs | "https://docs.example.com/agents/mem0" |

## Categories

Agents are classified into four main categories:

### Production
- **Purpose**: Production-ready agents used in live business scenarios
- **Requirements**: 
  - Comprehensive testing
  - Documentation
  - Approval process
- **Color**: Green (#28a745)
- **Icon**: ✓

### Example
- **Purpose**: Example agents for demonstration and learning
- **Requirements**: 
  - Clear documentation
  - Working test cases
- **Color**: Blue (#17a2b8)
- **Icon**: 📚

### Test
- **Purpose**: Test agents for development and validation
- **Requirements**: 
  - Located in `tests/` directory
  - Part of test suite
- **Color**: Yellow (#ffc107)
- **Icon**: 🧪

### System
- **Purpose**: Core platform functionality (judges, utilities)
- **Requirements**: 
  - High reliability
  - Backward compatibility
- **Color**: Purple (#6f42c1)
- **Icon**: ⚙️

## Environments

Agents can be deployed to different environments:

| Environment | Description | Requires Approval |
|-------------|-------------|-------------------|
| `production` | Live production environment | Yes |
| `staging` | Pre-production testing | Yes |
| `demo` | Feature demonstrations | No |
| `test` | Development and testing | No |

## Tag Taxonomy

Tags provide flexible classification beyond categories. Use standard tags from the taxonomy:

### Functional Tags
Describe what the agent does:
- `evaluation` - Evaluates outputs
- `summarization` - Summarizes content
- `analysis` - Analyzes data
- `extraction` - Extracts information
- `generation` - Generates content
- `classification` - Classifies inputs
- `translation` - Translates content

### Domain Tags
Describe the business domain:
- `memory` - Memory/conversation management
- `profile` - User/character profiling
- `conversation` - Conversation processing
- `document` - Document processing
- `entity` - Entity recognition
- `intent` - Intent classification

### Technical Tags
Describe technical characteristics:
- `llm-as-judge` - Uses LLM for evaluation
- `multi-step` - Multi-step processing
- `batch-processing` - Batch operations
- `real-time` - Real-time processing

### Quality Tags
Describe quality attributes:
- `high-accuracy` - High accuracy requirements
- `fast` - Optimized for speed
- `cost-effective` - Optimized for cost

## Adding a New Agent

### Step 1: Create Agent Directory

```bash
mkdir -p agents/my_new_agent/prompts
mkdir -p agents/my_new_agent/testsets
```

### Step 2: Create Agent Configuration

Create `agents/my_new_agent/agent.yaml`:

```yaml
id: "my_new_agent"
name: "My New Agent"
type: "task"
description: "Agent description"
# ... other agent-specific config
```

### Step 3: Register in Agent Registry

Add to `config/agent_registry.yaml`:

```yaml
agents:
  my_new_agent:
    name: "My New Agent"
    category: "production"
    environment: "staging"
    owner: "my-team"
    version: "1.0.0"
    tags: ["analysis", "document"]
    deprecated: false
    location: "agents/my_new_agent"
    description: "Detailed description of what this agent does"
    created_at: "2025-12-15"
    updated_at: "2025-12-15"
```

### Step 4: Verify Registration

```bash
# Using the sync tool (when implemented)
python scripts/sync_agent_registry.py --verify

# Or manually check
python -c "from src.agent_registry import AgentRegistry; \
           registry = AgentRegistry(); \
           print(registry.get_agent('my_new_agent'))"
```

## Auto-Sync Feature

The registry can automatically detect new agents from the filesystem:

```yaml
config:
  auto_sync:
    enabled: true
    scan_directories:
      - "agents/"
      - "examples/agents/"
    exclude_patterns:
      - "_template"
      - ".*"
      - "__pycache__"
```

### How Auto-Sync Works

1. Scans configured directories for agent.yaml files
2. Extracts metadata from agent.yaml
3. Compares with registry configuration
4. Reports new, updated, or removed agents
5. Optionally updates registry configuration

### Running Auto-Sync

```bash
# Dry run - show what would change
python scripts/sync_agent_registry.py --dry-run

# Apply changes
python scripts/sync_agent_registry.py --apply

# Interactive mode
python scripts/sync_agent_registry.py --interactive
```

## Hot Reload

The registry supports hot reloading when the configuration file changes. This allows you to update agent metadata without restarting your application.

### Enabling Hot Reload

```python
from src.agent_registry_v2 import AgentRegistry

# Enable hot reload on initialization
registry = AgentRegistry(enable_hot_reload=True)

# Or start it manually later
registry = AgentRegistry()
registry.start_hot_reload()
```

### How Hot Reload Works

1. **File Watcher**: Monitors `config/agent_registry.yaml` for changes
2. **Debounce**: Waits 1 second to avoid multiple reloads from rapid edits
3. **Reload**: Attempts to reload the configuration file
4. **Validation**: Validates the new configuration
5. **Update**: Updates the in-memory registry if validation succeeds
6. **Notification**: Calls all registered callbacks with reload event

### Reload Events

When the registry reloads, it creates a `ReloadEvent` with the following information:

```python
@dataclass
class ReloadEvent:
    timestamp: datetime      # When the reload occurred
    success: bool           # Whether reload succeeded
    error: Optional[str]    # Error message if failed
    agents_count: int       # Number of agents after reload
    previous_count: int     # Number of agents before reload
```

### Using Reload Callbacks

Register callbacks to be notified when the registry reloads:

```python
from src.agent_registry_v2 import AgentRegistry, ReloadEvent

registry = AgentRegistry(enable_hot_reload=True)

def on_reload(event: ReloadEvent):
    if event.success:
        print(f"✅ Registry reloaded: {event.agents_count} agents")
        if event.agents_count != event.previous_count:
            print(f"   Agent count changed: {event.previous_count} → {event.agents_count}")
    else:
        print(f"❌ Reload failed: {event.error}")

# Add callback
registry.add_reload_callback(on_reload)

# Remove callback when no longer needed
registry.remove_reload_callback(on_reload)
```

### Multiple Callbacks

You can register multiple callbacks for different purposes:

```python
def log_reload(event: ReloadEvent):
    """Log reload events"""
    logger.info(f"Registry reload: {event}")

def update_cache(event: ReloadEvent):
    """Update application cache"""
    if event.success:
        cache.invalidate('agents')

def notify_users(event: ReloadEvent):
    """Notify connected users"""
    if event.success:
        websocket.broadcast({'type': 'registry_updated'})

registry.add_reload_callback(log_reload)
registry.add_reload_callback(update_cache)
registry.add_reload_callback(notify_users)
```

### Error Handling

If the reload fails (e.g., invalid YAML, missing required fields), the registry:

1. Keeps the previous valid configuration
2. Logs the error
3. Calls callbacks with `success=False` and error details
4. Continues watching for future changes

```python
def on_reload(event: ReloadEvent):
    if not event.success:
        # Handle reload error
        logger.error(f"Registry reload failed: {event.error}")
        # Send alert to monitoring system
        alert_system.send_alert(
            severity='warning',
            message=f"Agent registry reload failed: {event.error}"
        )
```

### Stopping Hot Reload

Stop the file watcher when shutting down:

```python
# Stop hot reload
registry.stop_hot_reload()

# Hot reload is automatically stopped when registry is deleted
del registry
```

### Demo Script

Run the hot reload demo to see it in action:

```bash
python examples/hot_reload_demo.py
```

Then, in another terminal, modify `config/agent_registry.yaml` to see automatic reloading.

### Thread Safety

The hot reload mechanism is thread-safe:

- Uses a lock to prevent concurrent reloads
- Callbacks are executed sequentially
- Registry queries during reload return consistent data

### Performance Considerations

- **File Watching**: Minimal CPU overhead (uses OS-level file events)
- **Debouncing**: Prevents excessive reloads during rapid edits
- **Reload Time**: Typically < 100ms for normal-sized registries
- **Memory**: No memory leaks from file watching

### Best Practices

1. **Enable in Development**: Use hot reload during development for faster iteration
2. **Optional in Production**: Consider disabling in production if registry rarely changes
3. **Monitor Callbacks**: Keep callbacks lightweight to avoid blocking
4. **Handle Errors**: Always handle reload failures gracefully
5. **Clean Shutdown**: Stop hot reload before application exit

## Querying the Registry

### Get Single Agent

```python
from src.agent_registry import AgentRegistry

registry = AgentRegistry()
agent = registry.get_agent("mem0_l1_summarizer")

print(f"Name: {agent.name}")
print(f"Version: {agent.version}")
print(f"Tags: {agent.tags}")
```

### List All Agents

```python
agents = registry.list_agents()
for agent in agents:
    print(f"{agent.id}: {agent.name} (v{agent.version})")
```

### Filter by Category

```python
production_agents = registry.list_agents(category="production")
system_agents = registry.list_agents(category="system")
```

### Filter by Environment

```python
prod_agents = registry.list_agents(environment="production")
test_agents = registry.list_agents(environment="test")
```

### Filter by Tags

```python
# Agents with any of these tags
memory_agents = registry.list_agents(tags=["memory"])

# Agents with all of these tags
summarizers = registry.list_agents(
    tags=["summarization", "memory"],
    match_all_tags=True
)
```

### Complex Queries

```python
# Production memory agents
agents = registry.list_agents(
    category="production",
    tags=["memory"],
    environment="production"
)

# Non-deprecated evaluation agents
agents = registry.list_agents(
    tags=["evaluation"],
    include_deprecated=False
)
```

## Validation

The registry validates all agent metadata:

```yaml
config:
  validation:
    strict_mode: true
    required_fields:
      - "name"
      - "category"
      - "environment"
      - "owner"
      - "version"
      - "location"
    warn_on_missing_optional:
      - "description"
      - "tags"
```

### Validation Rules

1. **Required Fields**: Must be present and non-empty
2. **Category**: Must be one of: production, example, test, system
3. **Environment**: Must be one of: production, staging, demo, test
4. **Version**: Must follow semantic versioning (e.g., "1.2.3")
5. **Location**: Must be a valid directory path
6. **Tags**: Should use standard tags from taxonomy (warning if not)

### Validation Errors

```python
from src.agent_registry import AgentRegistry, ValidationError

try:
    registry = AgentRegistry()
except ValidationError as e:
    print(f"Validation failed: {e.message}")
    for error in e.errors:
        print(f"  - {error.field}: {error.message}")
```

## Best Practices

### Naming Conventions

- **Agent IDs**: Use snake_case (e.g., `mem0_l1_summarizer`)
- **Names**: Use descriptive names in native language
- **Versions**: Follow semantic versioning (MAJOR.MINOR.PATCH)

### Metadata Guidelines

1. **Description**: 1-2 sentences explaining the agent's purpose
2. **Business Goal**: Explain the business value (for production agents)
3. **Tags**: Use 2-5 relevant tags from the taxonomy
4. **Owner**: Use team name or email address
5. **Dates**: Use ISO 8601 format (YYYY-MM-DD)

### Version Management

- **MAJOR**: Breaking changes to agent interface
- **MINOR**: New features, backward compatible
- **PATCH**: Bug fixes, no interface changes

### Deprecation Process

1. Set `deprecated: true` in registry
2. Add `deprecation_reason` field
3. Specify `replacement_agent` if available
4. Set `deprecation_date` and `removal_date`
5. Update documentation

Example:

```yaml
old_agent:
  name: "Old Agent"
  deprecated: true
  deprecation_reason: "Replaced by new_agent with better performance"
  replacement_agent: "new_agent"
  deprecation_date: "2025-12-01"
  removal_date: "2026-03-01"
```

## Troubleshooting

### Agent Not Found

**Problem**: `registry.get_agent()` raises `AgentNotFoundError`

**Solutions**:
1. Check agent ID spelling
2. Verify agent is in registry configuration
3. Run auto-sync to detect new agents
4. Check if agent is in excluded directory

### Validation Errors

**Problem**: Registry fails to load due to validation errors

**Solutions**:
1. Check required fields are present
2. Verify category and environment values
3. Validate version format
4. Check location path exists

### Hot Reload Not Working

**Problem**: Changes to registry file not reflected

**Solutions**:
1. Verify `hot_reload.enabled: true`
2. Check file watcher is running
3. Verify file path is correct
4. Check file permissions

### Auto-Sync Conflicts

**Problem**: Auto-sync reports conflicts between filesystem and registry

**Solutions**:
1. Review conflict report
2. Manually resolve conflicts in registry file
3. Use `--force` flag to overwrite (with caution)
4. Use `--interactive` mode for guided resolution

## API Reference

See the [Agent Registry API Reference](./agent-registry-api.md) for detailed API documentation.

## Examples

See the [Agent Registry Examples](../../examples/agent_registry_examples.py) for code examples.

## Migration Guide

If you're migrating from the old agent system, see the [Agent Registry Migration Guide](./agent-registry-migration.md).

## Backward Compatibility

The agent registry system is fully backward compatible with existing code. See the [Backward Compatibility Guide](./agent-registry-backward-compatibility.md) for details on how the new system integrates with existing code.
