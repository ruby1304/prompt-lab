# Project Structure Migration Script

This document describes the `migrate_structure.py` script used to migrate the Prompt Lab project from its experimental structure to a production-ready structure.

## Overview

The migration script performs the following operations:

1. **Structure Detection**: Analyzes the current project structure
2. **Backup Creation**: Creates a timestamped backup of the current state
3. **Deprecated Scripts Removal**: Removes old test scripts from the root directory
4. **Documentation Consolidation**: Moves extra README files to the docs directory
5. **Directory Creation**: Creates missing directories required by the new structure
6. **Logging**: Maintains a detailed log of all operations

## Requirements Addressed

This script addresses the following requirements from the design document:

- **1.2**: Separate test content from production content
- **1.3**: Organize production agents and pipelines
- **1.4**: Consolidate documentation
- **1.5**: Clean up root directory

## Usage

### Preview Changes (Dry Run)

To preview what changes will be made without actually executing them:

```bash
python scripts/migrate_structure.py --dry-run
```

This will:
- Show all operations that would be performed
- Not modify any files or directories
- Generate a preview report

### Execute Migration

To execute the migration:

```bash
python scripts/migrate_structure.py
```

This will:
- Create a backup in `.migration_backups/`
- Execute all migration operations
- Generate a detailed report
- Save a migration log

### Create Backup Only

To create a backup without executing the migration:

```bash
python scripts/migrate_structure.py --backup-only
```

### Specify Project Root

By default, the script operates on the current directory. To specify a different project root:

```bash
python scripts/migrate_structure.py --project-root /path/to/project
```

## What Gets Changed

### Files Removed

- `run_tests.py` - Old test runner script
- `run_spec_tests.sh` - Old spec test runner script

### Files Moved

The following files are moved from the root directory to the docs directory:

- `PROJECT_STRUCTURE.md` → `docs/reference/project-structure.md`
- `QUICK_REFERENCE.md` → `docs/QUICK_REFERENCE.md`
- `REORGANIZATION_SUMMARY.md` → `docs/archive/reorganization-summary.md`
- `.project-organization-checklist.md` → `docs/archive/project-organization-checklist.md`

### Directories Created

The following directories are created if they don't exist:

- `config/` - For system configuration files
- `tests/unit/` - For unit tests
- `tests/integration/` - For integration tests
- `docs/api/` - For API documentation
- `pipelines/` - For production pipeline configurations

## Backup and Recovery

### Backup Location

Backups are stored in `.migration_backups/` with a timestamp:

```
.migration_backups/
└── backup_20231215_140522/
    ├── agents/
    ├── tests/
    ├── docs/
    ├── src/
    ├── README.md
    ├── requirements.txt
    └── migration_metadata.json
```

### Recovery

To recover from a backup:

1. Locate the backup directory in `.migration_backups/`
2. Copy the desired files/directories back to the project root
3. Or restore the entire backup:

```bash
# Example: restore from a specific backup
cp -r .migration_backups/backup_20231215_140522/* .
```

## Migration Log

The script maintains a detailed log of all operations in JSON format:

```
.migration_backups/
└── migration_log_20231215_140522.json
```

The log includes:
- Timestamp of each operation
- Operation type (move, remove, create_dir)
- Source and destination paths
- Status (success/failure)
- Additional details

## Migration Report

After migration, a comprehensive report is generated:

```
.migration_backups/
└── migration_report_20231215_140522.txt
```

The report includes:
- Current structure detection results
- List of deprecated scripts handled
- Documentation consolidation details
- Test and production content summary
- Created directories
- Backup location

## Safety Features

1. **Dry Run Mode**: Preview all changes before executing
2. **Automatic Backup**: Creates backup before any modifications
3. **Operation Logging**: Detailed log of all operations
4. **Validation**: Validates project structure before proceeding
5. **Error Handling**: Graceful error handling with detailed messages

## Testing

The migration script includes comprehensive tests:

```bash
# Run all migration script tests
python -m pytest tests/test_migrate_structure.py -v

# Run specific test
python -m pytest tests/test_migrate_structure.py::TestStructureMigrator::test_full_migration_dry_run -v
```

## Troubleshooting

### "Not a valid Prompt Lab project" Error

This error occurs when the script is run in a directory that doesn't contain a `src/` directory. Make sure you're running the script from the project root.

### Permission Errors

If you encounter permission errors, ensure you have write permissions for:
- The project root directory
- All subdirectories being modified
- The `.migration_backups/` directory

### Existing Destination Files

If a destination file already exists during documentation consolidation, the script will:
1. Create a backup of the existing file with `.backup` extension
2. Move the new file to the destination
3. Log the operation

## Post-Migration Steps

After running the migration:

1. **Verify Changes**: Review the migration report
2. **Run Tests**: Ensure all tests still pass
3. **Update Imports**: Check if any import paths need updating
4. **Update Documentation**: Review and update any documentation references
5. **Commit Changes**: Commit the migrated structure to version control

## Example Output

```
🚀 Starting project structure migration...
   Project root: /Users/user/prompt-lab
   Mode: EXECUTION

🔍 Detecting current project structure...
✅ Structure detection complete

📦 Creating backup at: .migration_backups/backup_20231215_140522
   Backing up: agents/
   Backing up: tests/
   ...
✅ Backup created successfully

🧹 Handling deprecated scripts...
   Removing: run_tests.py
   Removing: run_spec_tests.sh

📚 Consolidating documentation...
   Moving: PROJECT_STRUCTURE.md -> docs/reference/project-structure.md
   Moving: QUICK_REFERENCE.md -> docs/QUICK_REFERENCE.md
   ...

🧪 Organizing test content...
   ✅ Found 1 test agents in tests/agents/
   ℹ️  Test content is already properly organized

🏭 Verifying production content...
   ✅ Found 4 production agents
   ✅ Found 5 example agents

📁 Creating missing directories...
   Creating: config/
   Creating: tests/unit/
   Creating: tests/integration/
   Creating: docs/api/
   Creating: pipelines/

📝 Migration log saved to: .migration_backups/migration_log_20231215_140522.json

======================================================================
PROJECT STRUCTURE MIGRATION REPORT
======================================================================
...
✅ Migration completed successfully
   Backup available at: .migration_backups/backup_20231215_140522
```

## Related Documentation

- [Design Document](../.kiro/specs/project-production-readiness/design.md)
- [Requirements Document](../.kiro/specs/project-production-readiness/requirements.md)
- [Tasks Document](../.kiro/specs/project-production-readiness/tasks.md)
