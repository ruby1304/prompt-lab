# Scripts Directory

This directory contains utility scripts for managing and maintaining the Prompt Lab project.

## Available Scripts

### Agent Registry Management

#### `sync_agent_registry.py`
Synchronizes the Agent Registry configuration with the filesystem.

**Purpose**: Maintain consistency between the registry and actual agent directories.

**Usage**:
```bash
# Preview changes
python scripts/sync_agent_registry.py --dry-run

# Auto-add new agents
python scripts/sync_agent_registry.py --auto-add

# Full auto-sync
python scripts/sync_agent_registry.py --auto-update

# Generate new registry
python scripts/sync_agent_registry.py --generate-new
```

**Documentation**: [Agent Registry Sync Guide](../docs/reference/agent-registry-sync-guide.md)

**Requirements**: Implements Requirement 2.5 (filesystem scanning, auto-generation, conflict detection)

---

### Project Structure Management

#### `migrate_structure.py`
Migrates the project from experimental to production-ready structure.

**Purpose**: Reorganize project directories and consolidate documentation.

**Usage**:
```bash
# Preview changes
python scripts/migrate_structure.py --dry-run

# Execute migration
python scripts/migrate_structure.py
```

**Documentation**: [README_MIGRATION.md](README_MIGRATION.md)

---

### Agent Management

#### `add_agent_metadata.py`
Adds classification metadata to agent configurations.

**Purpose**: Bulk update agent.yaml files with category and environment metadata.

**Usage**:
```bash
# Preview changes
python scripts/add_agent_metadata.py --dry-run

# Update all agents
python scripts/add_agent_metadata.py

# Update specific agent
python scripts/add_agent_metadata.py --agent mem0_l1_summarizer
```

#### `list_agents_by_category.py`
Lists all agents grouped by category.

**Purpose**: Quick overview of agent organization.

**Usage**:
```bash
python scripts/list_agents_by_category.py
```

#### `reorganize_agents.py`
Reorganizes agents into category-based directories.

**Purpose**: Move agents to appropriate category folders.

**Usage**:
```bash
python scripts/reorganize_agents.py --dry-run
python scripts/reorganize_agents.py
```

---

### Configuration Management

#### `migrate_config.py`
Migrates configuration files to new formats.

**Purpose**: Update configuration files during version upgrades.

**Usage**:
```bash
python scripts/migrate_config.py
```

#### `convert_templates.py`
Converts legacy template formats to new structure.

**Purpose**: Migrate old template files to the new agent template format.

**Usage**:
```bash
python scripts/convert_templates.py
```

---

### Data Management

#### `migrate_data.py`
Migrates data files to new directory structure.

**Purpose**: Reorganize data files according to new structure.

**Usage**:
```bash
python scripts/migrate_data.py --dry-run
python scripts/migrate_data.py
```

---

### Evaluation Helpers

#### `demo_fill_scores.py`
Fills in demo scores for evaluation testing.

**Purpose**: Generate sample evaluation data for testing.

**Usage**:
```bash
python scripts/demo_fill_scores.py
```

#### `demo_manual_eval.py`
Demonstrates manual evaluation workflow.

**Purpose**: Show how to perform manual evaluation.

**Usage**:
```bash
python scripts/demo_manual_eval.py
```

#### `rule_helper.py`
Helper utilities for evaluation rules.

**Purpose**: Assist in creating and testing evaluation rules.

**Usage**:
```bash
python scripts/rule_helper.py
```

---

### Documentation Management

#### `fix_doc_links.py`
Fixes broken links in documentation files.

**Purpose**: Update documentation links after restructuring.

**Usage**:
```bash
# Check for broken links
python scripts/fix_doc_links.py --check

# Fix broken links
python scripts/fix_doc_links.py --fix
```

#### `validate_docs.py`
Validates documentation structure and links.

**Purpose**: Ensure documentation is complete and consistent.

**Usage**:
```bash
python scripts/validate_docs.py
```

---

### Testing and Verification

#### `test_backward_compatibility.py`
Tests backward compatibility after changes.

**Purpose**: Ensure changes don't break existing functionality.

**Usage**:
```bash
python scripts/test_backward_compatibility.py
```

#### `verify_agent_migration.py`
Verifies agent migration was successful.

**Purpose**: Check that all agents were migrated correctly.

**Usage**:
```bash
python scripts/verify_agent_migration.py
```

#### `verify_migration.py`
Verifies overall project migration.

**Purpose**: Comprehensive verification of project structure migration.

**Usage**:
```bash
python scripts/verify_migration.py
```

---

### Shell Scripts

#### `quick_eval.sh`
Quick evaluation script for testing.

**Purpose**: Run quick evaluation tests.

**Usage**:
```bash
bash scripts/quick_eval.sh
```

#### `run_eval_demo.sh`
Runs evaluation demo.

**Purpose**: Demonstrate evaluation workflow.

**Usage**:
```bash
bash scripts/run_eval_demo.sh
```

---

## Script Categories

### 🔧 Maintenance Scripts
- `sync_agent_registry.py` - Keep registry in sync
- `migrate_structure.py` - Project restructuring
- `fix_doc_links.py` - Documentation maintenance

### 📦 Agent Management
- `add_agent_metadata.py` - Bulk metadata updates
- `list_agents_by_category.py` - Agent organization
- `reorganize_agents.py` - Agent restructuring

### 🔄 Migration Scripts
- `migrate_config.py` - Configuration migration
- `migrate_data.py` - Data migration
- `convert_templates.py` - Template conversion

### ✅ Verification Scripts
- `test_backward_compatibility.py` - Compatibility testing
- `verify_agent_migration.py` - Agent verification
- `verify_migration.py` - Overall verification
- `validate_docs.py` - Documentation validation

### 🧪 Demo/Helper Scripts
- `demo_fill_scores.py` - Demo data generation
- `demo_manual_eval.py` - Evaluation demo
- `rule_helper.py` - Rule utilities

---

## Best Practices

### Before Running Scripts

1. **Always use dry-run first**: Most scripts support `--dry-run` to preview changes
2. **Backup important data**: Scripts may create backups, but manual backups are recommended
3. **Read the documentation**: Check script-specific docs before running
4. **Test in development**: Run scripts in a test environment first

### After Running Scripts

1. **Verify changes**: Use verification scripts to check results
2. **Run tests**: Execute test suite to ensure nothing broke
3. **Update documentation**: Document any manual changes made
4. **Commit changes**: Use meaningful commit messages

### Common Patterns

```bash
# Standard workflow for migration scripts
python scripts/script_name.py --dry-run  # Preview
python scripts/script_name.py            # Execute
python scripts/verify_migration.py       # Verify

# Standard workflow for agent scripts
python scripts/script_name.py --dry-run  # Preview
python scripts/script_name.py            # Execute
python scripts/list_agents_by_category.py # Check results
```

---

## Development

### Adding New Scripts

When adding a new script:

1. **Follow naming conventions**: Use descriptive snake_case names
2. **Add shebang**: Start with `#!/usr/bin/env python3`
3. **Include docstring**: Document purpose and usage
4. **Support dry-run**: Add `--dry-run` flag when applicable
5. **Add to this README**: Document the new script
6. **Write tests**: Add tests in `tests/` directory
7. **Make executable**: `chmod +x scripts/your_script.py`

### Script Template

```python
#!/usr/bin/env python3
"""
Script Name

Brief description of what the script does.

Usage:
    python scripts/script_name.py --dry-run
    python scripts/script_name.py
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def main():
    parser = argparse.ArgumentParser(description="Script description")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes")
    args = parser.parse_args()
    
    # Script logic here
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

---

## Related Documentation

- [Agent Registry Guide](../docs/reference/agent-registry-guide.md)
- [Agent Registry Sync Guide](../docs/reference/agent-registry-sync-guide.md)
- [Project Structure](../docs/reference/project-structure.md)
- [Migration Guide](../docs/reference/migration-guide.md)

---

**Last Updated**: 2025-12-15
