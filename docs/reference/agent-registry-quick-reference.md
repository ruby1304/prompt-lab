# Agent Registry Quick Reference

## Quick Start

### 1. Register a New Agent

```yaml
# In config/agent_registry.yaml
agents:
  my_agent:
    name: "My Agent"
    category: "production"          # production|example|test|system
    environment: "staging"          # production|staging|demo|test
    owner: "my-team"
    version: "1.0.0"
    location: "agents/my_agent"
    deprecated: false
    tags: ["analysis", "document"]
    description: "Brief description"
```

### 2. Query an Agent

```python
from src.agent_registry import AgentRegistry

registry = AgentRegistry()
agent = registry.get_agent("my_agent")
print(f"{agent.name} v{agent.version}")
```

### 3. List Agents

```python
# All agents
all_agents = registry.list_agents()

# Filter by category
prod_agents = registry.list_agents(category="production")

# Filter by tags
memory_agents = registry.list_agents(tags=["memory"])
```

## Field Reference

### Required Fields

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `name` | string | "对话记忆总结助手" | Human-readable name |
| `category` | enum | "production" | production\|example\|test\|system |
| `environment` | enum | "production" | production\|staging\|demo\|test |
| `owner` | string | "memory-team" | Team or email |
| `version` | string | "1.2.0" | Semantic versioning |
| `location` | string | "agents/my_agent" | Relative path |
| `deprecated` | boolean | false | Deprecation status |

### Common Optional Fields

| Field | Type | Example | Notes |
|-------|------|---------|-------|
| `description` | string | "Processes conversations..." | 1-2 sentences |
| `tags` | array | ["memory", "summarization"] | 2-5 recommended |
| `created_at` | date | "2024-03-20" | ISO 8601 format |
| `updated_at` | date | "2025-12-10" | ISO 8601 format |

## Categories

| Category | Purpose | Icon |
|----------|---------|------|
| `production` | Live business use | ✓ |
| `example` | Demos & learning | 📚 |
| `test` | Development & testing | 🧪 |
| `system` | Platform functionality | ⚙️ |

## Standard Tags

### Functional
`evaluation`, `summarization`, `analysis`, `extraction`, `generation`, `classification`, `translation`

### Domain
`memory`, `profile`, `conversation`, `document`, `entity`, `intent`

### Technical
`llm-as-judge`, `multi-step`, `batch-processing`, `real-time`

### Quality
`high-accuracy`, `fast`, `cost-effective`

## Common Operations

### Get Agent by ID

```python
agent = registry.get_agent("mem0_l1_summarizer")
```

### List All Production Agents

```python
agents = registry.list_agents(category="production")
```

### Find Agents by Tag

```python
# Any of these tags
agents = registry.list_agents(tags=["memory"])

# All of these tags
agents = registry.list_agents(
    tags=["memory", "summarization"],
    match_all_tags=True
)
```

### Filter by Multiple Criteria

```python
agents = registry.list_agents(
    category="production",
    environment="production",
    tags=["memory"],
    include_deprecated=False
)
```

### Check if Agent Exists

```python
if registry.has_agent("my_agent"):
    print("Agent exists")
```

### Get Agent Count

```python
total = registry.count_agents()
prod_count = registry.count_agents(category="production")
```

## Validation

### Version Format

✅ Valid: `1.0.0`, `2.1.3`, `1.0.0-beta.1`  
❌ Invalid: `1.0`, `v1.0.0`, `1.0.0.0`

### Category Values

✅ Valid: `production`, `example`, `test`, `system`  
❌ Invalid: `prod`, `dev`, `staging`

### Environment Values

✅ Valid: `production`, `staging`, `demo`, `test`  
❌ Invalid: `prod`, `dev`, `local`

### Location Path

✅ Valid: `agents/my_agent`, `examples/agents/demo`  
❌ Invalid: `/agents/my_agent`, `./agents/my_agent`

## Auto-Sync

### Scan for New Agents

```bash
python scripts/sync_agent_registry.py --dry-run
```

### Apply Changes

```bash
python scripts/sync_agent_registry.py --apply
```

### Interactive Mode

```bash
python scripts/sync_agent_registry.py --interactive
```

## Hot Reload

### Enable in Config

```yaml
config:
  hot_reload:
    enabled: true
    watch_file: "config/agent_registry.yaml"
    debounce_ms: 500
```

### Use in Code

```python
registry = AgentRegistry(hot_reload=True)

def on_reload(event):
    print(f"Registry reloaded: {len(event.changes)} changes")

registry.on_reload(on_reload)
```

## Deprecation

### Mark as Deprecated

```yaml
old_agent:
  deprecated: true
  deprecation_reason: "Replaced by new_agent"
  replacement_agent: "new_agent"
  deprecation_date: "2025-12-01"
  removal_date: "2026-03-01"
```

### Find Deprecated Agents

```python
deprecated = registry.list_agents(deprecated=True)
```

## Error Handling

### Agent Not Found

```python
from src.agent_registry import AgentNotFoundError

try:
    agent = registry.get_agent("nonexistent")
except AgentNotFoundError as e:
    print(f"Agent not found: {e.agent_id}")
```

### Validation Error

```python
from src.agent_registry import ValidationError

try:
    registry = AgentRegistry()
except ValidationError as e:
    print(f"Validation failed: {e.message}")
    for error in e.errors:
        print(f"  {error.field}: {error.message}")
```

## Best Practices

### ✅ Do

- Use semantic versioning (1.2.3)
- Add 2-5 relevant tags
- Include description for all agents
- Update `updated_at` when changing
- Use standard tags from taxonomy
- Set appropriate category and environment

### ❌ Don't

- Use custom categories without definition
- Skip required fields
- Use absolute paths for location
- Forget to update version on changes
- Use too many tags (>10)
- Leave deprecated agents without replacement info

## Configuration Examples

### Minimal Agent

```yaml
my_agent:
  name: "My Agent"
  category: "test"
  environment: "test"
  owner: "dev-team"
  version: "1.0.0"
  location: "agents/my_agent"
  deprecated: false
```

### Complete Agent

```yaml
my_agent:
  name: "My Production Agent"
  category: "production"
  environment: "production"
  owner: "platform-team"
  version: "2.1.0"
  location: "agents/my_agent"
  deprecated: false
  description: "Comprehensive agent for production use"
  business_goal: "Achieve high accuracy with low latency"
  tags: ["analysis", "document", "high-accuracy"]
  created_at: "2024-01-15"
  updated_at: "2025-12-15"
  dependencies: ["judge_default"]
  maintainer: "john.doe@company.com"
  documentation_url: "https://docs.example.com/agents/my_agent"
  performance_metrics:
    avg_latency_ms: 1200
    avg_tokens: 1500
    success_rate: 0.98
```

### Deprecated Agent

```yaml
old_agent:
  name: "Old Agent"
  category: "production"
  environment: "production"
  owner: "legacy-team"
  version: "1.5.0"
  location: "agents/old_agent"
  deprecated: true
  deprecation_reason: "Replaced by new_agent with 2x performance"
  replacement_agent: "new_agent"
  deprecation_date: "2025-11-01"
  removal_date: "2026-02-01"
  tags: ["legacy"]
```

## CLI Commands

### List All Agents

```bash
python -m src.agent_registry list
```

### Get Agent Details

```bash
python -m src.agent_registry get mem0_l1_summarizer
```

### Validate Registry

```bash
python -m src.agent_registry validate
```

### Sync from Filesystem

```bash
python scripts/sync_agent_registry.py
```

## Troubleshooting

### Problem: Agent not found

**Check:**
1. Agent ID spelling
2. Agent in registry config
3. Run auto-sync

### Problem: Validation fails

**Check:**
1. Required fields present
2. Category/environment values valid
3. Version format correct
4. Location path exists

### Problem: Hot reload not working

**Check:**
1. `hot_reload.enabled: true`
2. File watcher running
3. File path correct
4. File permissions

## Resources

- [Full Guide](./agent-registry-guide.md)
- [Schema Specification](./agent-registry-schema.md)
- [API Reference](./agent-registry-api.md)
- [Migration Guide](./agent-registry-migration.md)
