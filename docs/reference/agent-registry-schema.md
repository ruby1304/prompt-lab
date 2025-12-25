# Agent Registry Schema Specification

## Version 1.0

This document provides the formal schema specification for the Agent Registry configuration format.

## Root Schema

```yaml
version: string (required)
registry: RegistryMetadata (required)
agents: map<string, AgentMetadata> (required)
categories: map<string, CategoryDefinition> (optional)
environments: map<string, EnvironmentDefinition> (optional)
tag_taxonomy: TagTaxonomy (optional)
config: RegistryConfig (optional)
```

## RegistryMetadata

Metadata about the registry itself.

```yaml
name: string (required)
  # Human-readable name of the registry
  # Example: "Prompt Lab Agent Registry"

description: string (optional)
  # Brief description of the registry's purpose
  # Example: "Central registry for all production, example, and system agents"

last_updated: string (optional)
  # ISO 8601 date of last update
  # Format: YYYY-MM-DD
  # Example: "2025-12-15"

maintainer: string (optional)
  # Team or person maintaining the registry
  # Example: "platform-team"
```

## AgentMetadata

Complete metadata for a single agent.

### Required Fields

```yaml
name: string (required)
  # Human-readable agent name
  # Can be in any language
  # Example: "对话记忆总结助手"
  # Constraints:
  #   - Length: 1-200 characters
  #   - Must not be empty

category: string (required)
  # Agent category
  # Must be one of: "production", "example", "test", "system"
  # Example: "production"

environment: string (required)
  # Deployment environment
  # Must be one of: "production", "staging", "demo", "test"
  # Example: "production"

owner: string (required)
  # Team or person responsible for the agent
  # Example: "memory-team" or "john.doe@company.com"
  # Constraints:
  #   - Length: 1-100 characters

version: string (required)
  # Semantic version
  # Format: MAJOR.MINOR.PATCH
  # Example: "1.2.0"
  # Constraints:
  #   - Must match regex: ^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$
  #   - Examples: "1.0.0", "2.1.3", "1.0.0-beta.1"

location: string (required)
  # Relative path to agent directory from project root
  # Example: "agents/mem0_l1_summarizer"
  # Constraints:
  #   - Must be a valid relative path
  #   - Directory must exist
  #   - Must contain agent.yaml file

deprecated: boolean (required)
  # Whether the agent is deprecated
  # Example: false
  # Default: false
```

### Optional Fields

```yaml
description: string (optional)
  # Brief description of agent purpose
  # Example: "Processes conversation history to extract key information"
  # Constraints:
  #   - Length: 1-500 characters
  #   - Should be 1-2 sentences

business_goal: string (optional)
  # Business objective or value proposition
  # Example: "Generate high-quality summaries while conserving tokens"
  # Constraints:
  #   - Length: 1-1000 characters

tags: array<string> (optional)
  # Classification tags
  # Example: ["memory", "summarization", "conversation"]
  # Constraints:
  #   - Each tag: 1-50 characters
  #   - Recommended: 2-5 tags
  #   - Should use tags from tag_taxonomy

created_at: string (optional)
  # Creation date
  # Format: ISO 8601 (YYYY-MM-DD)
  # Example: "2024-03-20"

updated_at: string (optional)
  # Last update date
  # Format: ISO 8601 (YYYY-MM-DD)
  # Example: "2025-12-10"

dependencies: array<string> (optional)
  # Required agents or services
  # Example: ["judge_default", "entity_extractor"]
  # Each item is an agent ID

maintainer: string (optional)
  # Current maintainer (can differ from owner)
  # Example: "jane.smith@company.com"

documentation_url: string (optional)
  # Link to detailed documentation
  # Example: "https://docs.example.com/agents/mem0"
  # Must be a valid URL

deprecation_reason: string (optional)
  # Reason for deprecation (required if deprecated=true)
  # Example: "Replaced by mem0_l2_summarizer with better performance"

replacement_agent: string (optional)
  # ID of replacement agent (if deprecated)
  # Example: "mem0_l2_summarizer"

deprecation_date: string (optional)
  # Date when agent was deprecated
  # Format: ISO 8601 (YYYY-MM-DD)

removal_date: string (optional)
  # Planned removal date
  # Format: ISO 8601 (YYYY-MM-DD)

status: string (optional)
  # Current status
  # Values: "active", "deprecated", "experimental", "archived"
  # Default: "active"

performance_metrics: PerformanceMetrics (optional)
  # Performance characteristics
  # See PerformanceMetrics schema below
```

## CategoryDefinition

Definition of an agent category.

```yaml
description: string (required)
  # Description of the category's purpose
  # Example: "Production-ready agents used in live business scenarios"

color: string (optional)
  # Hex color code for UI display
  # Example: "#28a745"
  # Format: #RRGGBB

icon: string (optional)
  # Icon or emoji for UI display
  # Example: "✓" or "🚀"
```

## EnvironmentDefinition

Definition of a deployment environment.

```yaml
description: string (required)
  # Description of the environment
  # Example: "Live production environment"

requires_approval: boolean (optional)
  # Whether deployments require approval
  # Example: true
  # Default: false

approval_process: string (optional)
  # Description of approval process
  # Example: "Requires sign-off from tech lead and product manager"
```

## TagTaxonomy

Organized collection of standard tags.

```yaml
functional: array<string> (optional)
  # Tags describing agent functionality
  # Example: ["evaluation", "summarization", "analysis"]

domain: array<string> (optional)
  # Tags describing business domain
  # Example: ["memory", "profile", "conversation"]

technical: array<string> (optional)
  # Tags describing technical characteristics
  # Example: ["llm-as-judge", "multi-step", "batch-processing"]

quality: array<string> (optional)
  # Tags describing quality attributes
  # Example: ["high-accuracy", "fast", "cost-effective"]

custom: map<string, array<string>> (optional)
  # Custom tag categories
  # Example:
  #   custom:
  #     industry: ["healthcare", "finance", "retail"]
```

## RegistryConfig

Configuration for registry behavior.

```yaml
auto_sync: AutoSyncConfig (optional)
hot_reload: HotReloadConfig (optional)
validation: ValidationConfig (optional)
discovery: DiscoveryConfig (optional)
```

### AutoSyncConfig

```yaml
enabled: boolean (required)
  # Whether auto-sync is enabled
  # Default: true

scan_directories: array<string> (required)
  # Directories to scan for agents
  # Example: ["agents/", "examples/agents/"]

exclude_patterns: array<string> (optional)
  # Glob patterns to exclude
  # Example: ["_template", ".*", "__pycache__"]

auto_register: boolean (optional)
  # Automatically register new agents
  # Default: false

conflict_resolution: string (optional)
  # How to handle conflicts
  # Values: "manual", "filesystem", "registry"
  # Default: "manual"
```

### HotReloadConfig

```yaml
enabled: boolean (required)
  # Whether hot reload is enabled
  # Default: true

watch_file: string (required)
  # File to watch for changes
  # Example: "config/agent_registry.yaml"

debounce_ms: integer (optional)
  # Debounce delay in milliseconds
  # Default: 500
  # Range: 100-5000
```

### ValidationConfig

```yaml
strict_mode: boolean (optional)
  # Whether to enforce strict validation
  # Default: true

required_fields: array<string> (required)
  # Fields that must be present
  # Example: ["name", "category", "environment", "owner", "version", "location"]

warn_on_missing_optional: array<string> (optional)
  # Optional fields to warn about if missing
  # Example: ["description", "tags", "created_at"]

validate_location: boolean (optional)
  # Whether to validate location paths exist
  # Default: true

validate_dependencies: boolean (optional)
  # Whether to validate dependency references
  # Default: true

allow_custom_categories: boolean (optional)
  # Whether to allow categories not in definitions
  # Default: false

allow_custom_environments: boolean (optional)
  # Whether to allow environments not in definitions
  # Default: false
```

### DiscoveryConfig

```yaml
enable_fuzzy_search: boolean (optional)
  # Enable fuzzy matching in searches
  # Default: true

enable_tag_filtering: boolean (optional)
  # Enable filtering by tags
  # Default: true

enable_category_filtering: boolean (optional)
  # Enable filtering by category
  # Default: true

default_sort: string (optional)
  # Default sort field
  # Values: "name", "updated_at", "version", "category"
  # Default: "name"

case_sensitive_search: boolean (optional)
  # Whether searches are case-sensitive
  # Default: false
```

## PerformanceMetrics

Optional performance characteristics of an agent.

```yaml
avg_latency_ms: integer (optional)
  # Average latency in milliseconds
  # Example: 1500

avg_tokens: integer (optional)
  # Average token usage
  # Example: 2000

success_rate: float (optional)
  # Success rate (0.0 to 1.0)
  # Example: 0.95

cost_per_call: float (optional)
  # Average cost per call in USD
  # Example: 0.05

throughput_per_hour: integer (optional)
  # Maximum throughput per hour
  # Example: 1000
```

## Validation Rules

### Version Format

Versions must follow semantic versioning:

```regex
^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$
```

Valid examples:
- `1.0.0`
- `2.1.3`
- `1.0.0-beta.1`
- `3.2.1-rc.2`

Invalid examples:
- `1.0` (missing patch)
- `v1.0.0` (no 'v' prefix)
- `1.0.0.0` (too many parts)

### Category Values

Must be one of:
- `production`
- `example`
- `test`
- `system`

### Environment Values

Must be one of:
- `production`
- `staging`
- `demo`
- `test`

### Status Values

Must be one of:
- `active`
- `deprecated`
- `experimental`
- `archived`

### Date Format

All dates must be in ISO 8601 format:

```regex
^\d{4}-\d{2}-\d{2}$
```

Example: `2025-12-15`

### Location Path

- Must be a relative path
- Must not start with `/` or `./`
- Must use forward slashes `/`
- Must point to existing directory (if validation enabled)
- Directory must contain `agent.yaml` file

Valid examples:
- `agents/mem0_l1_summarizer`
- `examples/agents/document_summarizer`

Invalid examples:
- `/agents/mem0_l1_summarizer` (absolute path)
- `./agents/mem0_l1_summarizer` (starts with ./)
- `agents\mem0_l1_summarizer` (backslashes)

## Complete Example

```yaml
version: "1.0"

registry:
  name: "Prompt Lab Agent Registry"
  description: "Central registry for all agents"
  last_updated: "2025-12-15"
  maintainer: "platform-team"

agents:
  mem0_l1_summarizer:
    # Required fields
    name: "对话记忆总结助手"
    category: "production"
    environment: "production"
    owner: "memory-team"
    version: "1.3.0"
    location: "agents/mem0_l1_summarizer"
    deprecated: false
    
    # Optional fields
    description: "Processes conversation history to extract key information"
    business_goal: "Generate high-quality summaries while conserving tokens"
    tags: ["memory", "summarization", "conversation"]
    created_at: "2024-03-20"
    updated_at: "2025-12-10"
    dependencies: ["judge_default"]
    maintainer: "john.doe@company.com"
    documentation_url: "https://docs.example.com/agents/mem0"
    status: "active"
    
    performance_metrics:
      avg_latency_ms: 1500
      avg_tokens: 2000
      success_rate: 0.95
      cost_per_call: 0.05

categories:
  production:
    description: "Production-ready agents"
    color: "#28a745"
    icon: "✓"

environments:
  production:
    description: "Live production environment"
    requires_approval: true
    approval_process: "Requires tech lead and PM sign-off"

tag_taxonomy:
  functional:
    - "evaluation"
    - "summarization"
  domain:
    - "memory"
    - "conversation"

config:
  auto_sync:
    enabled: true
    scan_directories: ["agents/"]
    exclude_patterns: ["_template"]
  
  hot_reload:
    enabled: true
    watch_file: "config/agent_registry.yaml"
    debounce_ms: 500
  
  validation:
    strict_mode: true
    required_fields: ["name", "category", "environment", "owner", "version", "location"]
  
  discovery:
    enable_fuzzy_search: true
    default_sort: "name"
```

## JSON Schema

For programmatic validation, a JSON Schema is available at:
`config/schemas/agent_registry.schema.json`

This can be used with YAML validators that support JSON Schema.

## Changelog

### Version 1.0 (2025-12-15)
- Initial schema specification
- Defined required and optional fields
- Established validation rules
- Added performance metrics support
