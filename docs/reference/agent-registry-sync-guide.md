# Agent Registry Sync Tool Guide

## Overview

The Agent Registry Sync Tool (`scripts/sync_agent_registry.py`) is a command-line utility that synchronizes the Agent Registry configuration file with the filesystem. It helps maintain consistency between the registry and actual agent directories.

## Features

- **Filesystem Scanning**: Automatically scans configured directories for agent folders
- **Conflict Detection**: Identifies new, removed, and mismatched agents
- **Auto-Sync**: Can automatically add, remove, or update agents in the registry
- **Dry-Run Mode**: Preview changes before applying them
- **Registry Generation**: Generate a complete registry from scratch
- **Flexible Configuration**: Customize scan directories and exclusion patterns

## Usage

### Basic Commands

#### Preview Changes (Dry-Run)

Scan the filesystem and report differences without modifying the registry:

```bash
python scripts/sync_agent_registry.py --dry-run
```

#### Auto-Add New Agents

Automatically add newly discovered agents to the registry:

```bash
python scripts/sync_agent_registry.py --auto-add
```

#### Auto-Remove Missing Agents

Automatically remove agents that no longer exist in the filesystem:

```bash
python scripts/sync_agent_registry.py --auto-remove
```

#### Full Auto-Sync

Automatically add, remove, and update agents (recommended for regular maintenance):

```bash
python scripts/sync_agent_registry.py --auto-update
```

#### Generate New Registry

Generate a complete registry configuration from scratch:

```bash
python scripts/sync_agent_registry.py --generate-new
```

### Advanced Options

#### Custom Registry Path

Specify a custom path to the registry configuration:

```bash
python scripts/sync_agent_registry.py --registry-path /path/to/registry.yaml
```

#### Custom Scan Directories

Override the default scan directories:

```bash
python scripts/sync_agent_registry.py --scan-dirs agents/ examples/agents/ tests/agents/
```

#### Custom Exclusion Patterns

Override the default exclusion patterns:

```bash
python scripts/sync_agent_registry.py --exclude _template .* __pycache__
```

#### Verbose Output

Enable detailed logging for debugging:

```bash
python scripts/sync_agent_registry.py --verbose --dry-run
```

## How It Works

### 1. Filesystem Scanning

The tool scans configured directories (default: `agents/` and `examples/agents/`) for subdirectories containing an `agent.yaml` file.

**Exclusion Rules:**
- Directories starting with `_` (e.g., `_template`)
- Hidden directories starting with `.`
- `__pycache__` directories

### 2. Metadata Inference

For each discovered agent, the tool infers metadata from:
- The `agent.yaml` configuration file
- The agent's location in the filesystem
- Naming conventions (e.g., `judge_default` → system agent)

**Category Inference:**
- `agents/` → `production`
- `examples/agents/` → `example`
- `tests/agents/` → `test`
- Special names (e.g., `judge_default`) → `system`

### 3. Comparison

The tool compares filesystem agents with registry entries to detect:
- **New Agents**: Present in filesystem but not in registry
- **Removed Agents**: Present in registry but not in filesystem
- **Location Mismatches**: Agent exists in both but with different paths

### 4. Synchronization

Based on the command-line flags, the tool can:
- Add new agents to the registry
- Remove missing agents from the registry
- Update agent locations to match the filesystem
- Generate a complete new registry

## Configuration

The sync tool reads configuration from the registry file itself:

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

## Output Format

### Dry-Run Output

```
======================================================================
SYNC SUMMARY
======================================================================

✅ Added (2):
   + new_agent_1
   + new_agent_2

❌ Removed (1):
   - old_agent

🔄 Updated (1):
   ~ moved_agent

⚠️  Errors (1):
   ! conflict_agent: Location mismatch: registry=old/path, filesystem=new/path

======================================================================

💡 To apply these changes, run without --dry-run
   Or use --auto-update to automatically sync everything
```

### Success Output

```
2025-12-15 15:33:26,648 - INFO - Scanning filesystem for agents...
2025-12-15 15:33:26,697 - INFO - Found 9 agents in filesystem
2025-12-15 15:33:26,697 - INFO - Comparing with registry...
2025-12-15 15:33:26,726 - INFO - Found 2 new agents
2025-12-15 15:33:26,726 - INFO -   + Added: new_agent_1
2025-12-15 15:33:26,726 - INFO -   + Added: new_agent_2
2025-12-15 15:33:26,727 - INFO - Registry configuration updated

✅ New registry generated and saved to config/agent_registry.yaml
```

## Best Practices

### Regular Maintenance

Run the sync tool regularly to keep the registry up-to-date:

```bash
# Weekly maintenance
python scripts/sync_agent_registry.py --auto-update
```

### Before Committing Changes

Always run a dry-run before committing registry changes:

```bash
# Check for issues
python scripts/sync_agent_registry.py --dry-run

# If everything looks good, apply changes
python scripts/sync_agent_registry.py --auto-update
```

### After Adding New Agents

After creating a new agent directory, sync the registry:

```bash
python scripts/sync_agent_registry.py --auto-add
```

### Conflict Resolution

When conflicts are detected:

1. Review the conflict details in the output
2. Manually verify the correct location
3. Use `--auto-update` to apply the filesystem location
4. Or manually edit the registry if the filesystem is wrong

## Integration with CI/CD

### Pre-Commit Hook

Add a check to ensure the registry is in sync:

```bash
#!/bin/bash
# .git/hooks/pre-commit

python scripts/sync_agent_registry.py --dry-run
if [ $? -ne 0 ]; then
    echo "❌ Agent registry is out of sync!"
    echo "Run: python scripts/sync_agent_registry.py --auto-update"
    exit 1
fi
```

### GitHub Actions

```yaml
name: Check Agent Registry

on: [push, pull_request]

jobs:
  check-registry:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Check registry sync
        run: |
          python scripts/sync_agent_registry.py --dry-run
          if [ $? -ne 0 ]; then
            echo "Registry is out of sync"
            exit 1
          fi
```

## Troubleshooting

### Issue: "Registry config not found"

**Solution**: Create an initial registry:

```bash
python scripts/sync_agent_registry.py --generate-new
```

### Issue: "Failed to load agent config"

**Cause**: Invalid YAML in `agent.yaml`

**Solution**: Validate the YAML syntax:

```bash
python -c "import yaml; yaml.safe_load(open('agents/your_agent/agent.yaml'))"
```

### Issue: Location mismatches not auto-updating

**Cause**: Using `--auto-add` instead of `--auto-update`

**Solution**: Use `--auto-update` which includes location updates:

```bash
python scripts/sync_agent_registry.py --auto-update
```

## API Reference

### AgentScanner

Scans filesystem for agent directories.

**Methods:**
- `scan_directory(scan_dir, exclude_patterns)`: Scan a directory for agents
- `load_agent_config(agent_dir)`: Load agent.yaml configuration
- `infer_metadata_from_config(agent_id, agent_dir, config)`: Infer metadata

### RegistrySyncer

Synchronizes registry with filesystem.

**Methods:**
- `scan_filesystem(scan_directories, exclude_patterns)`: Scan all configured directories
- `compare_with_registry(filesystem_agents)`: Compare with current registry
- `sync(auto_add, auto_remove, auto_update, dry_run)`: Perform synchronization
- `generate_new_registry()`: Generate new registry from scratch

## Related Documentation

- [Agent Registry Guide](agent-registry-guide.md)
- [Agent Registry Schema](agent-registry-schema.md)
- [Agent Registry Quick Reference](agent-registry-quick-reference.md)
- [Hot Reload Implementation](hot-reload-implementation.md)

## Requirements

This tool implements **Requirement 2.5** from the project requirements:
- Filesystem scanning
- Automatic registry generation
- Conflict detection and resolution
