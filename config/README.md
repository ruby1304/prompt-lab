# Configuration Directory

This directory contains system-wide configuration files for the Prompt Lab platform.

## Files

### agent_registry.yaml

The central Agent Registry configuration file. This file serves as the single source of truth for all agent metadata, including:

- Agent names and descriptions
- Categories and environments
- Version information
- Tags and classifications
- Ownership and maintenance info
- Deprecation status

**Documentation**: See [Agent Registry Guide](../docs/reference/agent-registry-guide.md)

**Schema**: See [schemas/agent_registry.schema.json](schemas/agent_registry.schema.json)

### schemas/

JSON Schema files for validating configuration formats.

#### agent_registry.schema.json

JSON Schema for validating `agent_registry.yaml` files. Can be used with YAML validators that support JSON Schema.

**Usage**:
```bash
# Using a YAML validator with JSON Schema support
yaml-validator --schema config/schemas/agent_registry.schema.json config/agent_registry.yaml
```

## Configuration Management

### Editing Configuration

1. **Manual Editing**: Edit `agent_registry.yaml` directly
   - Use a YAML-aware editor for syntax highlighting
   - Validate against schema before committing
   - Follow the field specifications in the documentation

2. **Auto-Sync Tool**: Use the sync tool to detect filesystem changes
   ```bash
   python scripts/sync_agent_registry.py --dry-run
   python scripts/sync_agent_registry.py --apply
   ```

3. **Programmatic Updates**: Use the AgentRegistry API
   ```python
   from src.agent_registry import AgentRegistry
   
   registry = AgentRegistry()
   registry.register_agent("new_agent", metadata)
   registry.save()
   ```

### Validation

Before committing changes, validate the configuration:

```bash
# Validate syntax and schema
python -m src.agent_registry validate

# Check for common issues
python scripts/sync_agent_registry.py --verify
```

### Version Control

- Always commit configuration changes with descriptive messages
- Use pull requests for production agent changes
- Tag releases when making significant registry updates
- Keep backup copies before major changes

## Best Practices

### DO

✅ Use semantic versioning for agent versions  
✅ Add descriptive tags from the standard taxonomy  
✅ Include creation and update dates  
✅ Document deprecation reasons and replacements  
✅ Validate configuration before committing  
✅ Use consistent naming conventions  

### DON'T

❌ Skip required fields  
❌ Use custom categories without defining them  
❌ Forget to update `updated_at` when changing agents  
❌ Leave deprecated agents without replacement info  
❌ Use absolute paths for agent locations  
❌ Commit invalid YAML syntax  

## Hot Reload

The Agent Registry supports hot reloading. When `agent_registry.yaml` is modified, the system can automatically reload the configuration without restart.

**Enable hot reload**:
```yaml
config:
  hot_reload:
    enabled: true
    watch_file: "config/agent_registry.yaml"
    debounce_ms: 500
```

**Note**: Hot reload is useful in development but should be used carefully in production.

## Security

### Sensitive Information

⚠️ **Do not store sensitive information in configuration files**

- API keys → Use environment variables
- Passwords → Use secrets management
- Tokens → Use secure credential storage

### Access Control

- Restrict write access to configuration files
- Use code review for production changes
- Audit configuration changes
- Implement approval workflows for critical agents

## Backup and Recovery

### Backup Strategy

1. **Version Control**: Git provides automatic backup
2. **Pre-Migration Backups**: Created automatically by migration scripts
3. **Manual Backups**: Copy before major changes

```bash
# Create manual backup
cp config/agent_registry.yaml config/agent_registry.yaml.backup.$(date +%Y%m%d)
```

### Recovery

```bash
# Restore from backup
cp config/agent_registry.yaml.backup.20251215 config/agent_registry.yaml

# Restore from git
git checkout HEAD -- config/agent_registry.yaml
```

## Migration

When migrating from older systems or restructuring:

1. Create backup of current configuration
2. Run migration script with `--dry-run` first
3. Review proposed changes
4. Apply migration
5. Validate new configuration
6. Test agent discovery and loading

See [Migration Guide](../docs/reference/agent-registry-migration.md) for details.

## Troubleshooting

### Configuration Won't Load

**Check**:
- YAML syntax is valid
- Required fields are present
- Field values match allowed enums
- File permissions are correct

**Validate**:
```bash
python -m src.agent_registry validate
```

### Auto-Sync Not Working

**Check**:
- `auto_sync.enabled: true` in config
- Scan directories are correct
- Agent directories contain `agent.yaml`
- No permission issues

**Debug**:
```bash
python scripts/sync_agent_registry.py --verbose --dry-run
```

### Hot Reload Not Triggering

**Check**:
- `hot_reload.enabled: true` in config
- File watcher is running
- File path is correct
- No file system issues

## Resources

- [Agent Registry Guide](../docs/reference/agent-registry-guide.md) - Complete guide
- [Schema Specification](../docs/reference/agent-registry-schema.md) - Field specifications
- [Quick Reference](../docs/reference/agent-registry-quick-reference.md) - Quick lookup
- [API Reference](../docs/reference/agent-registry-api.md) - Programming interface

## Support

For questions or issues:
1. Check the documentation links above
2. Review examples in `agent_registry.yaml`
3. Run validation tools
4. Contact the platform team
