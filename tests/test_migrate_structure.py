"""
Tests for the project structure migration script.

This test suite verifies the migration script's functionality including:
- Structure detection
- Backup creation
- File moving and reorganization
- Directory creation
"""

import pytest
import json
from pathlib import Path
from datetime import datetime
import sys

# Add scripts directory to path to import the migration script
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from migrate_structure import StructureMigrator


class TestStructureMigrator:
    """Test suite for StructureMigrator class."""
    
    @pytest.fixture
    def mock_project_root(self, temp_dir):
        """Create a mock project structure for testing."""
        project_root = temp_dir / "test_project"
        project_root.mkdir()
        
        # Create basic directory structure
        (project_root / "src").mkdir()
        (project_root / "agents").mkdir()
        (project_root / "tests").mkdir()
        (project_root / "docs").mkdir()
        (project_root / "examples").mkdir()
        (project_root / "data").mkdir()
        (project_root / "scripts").mkdir()
        (project_root / "templates").mkdir()
        
        # Create some files
        (project_root / "README.md").write_text("# Main README")
        (project_root / "requirements.txt").write_text("langchain>=0.3.0")
        (project_root / ".gitignore").write_text("__pycache__/")
        
        # Create deprecated scripts
        (project_root / "run_tests.py").write_text("# Old test script")
        (project_root / "run_spec_tests.sh").write_text("#!/bin/bash\n# Old spec test script")
        
        # Create extra README files
        (project_root / "PROJECT_STRUCTURE.md").write_text("# Project Structure")
        (project_root / "QUICK_REFERENCE.md").write_text("# Quick Reference")
        (project_root / "REORGANIZATION_SUMMARY.md").write_text("# Reorganization Summary")
        (project_root / ".project-organization-checklist.md").write_text("# Checklist")
        
        # Create some test agents
        test_agent_dir = project_root / "tests" / "agents" / "test_agent"
        test_agent_dir.mkdir(parents=True)
        (test_agent_dir / "agent.yaml").write_text("id: test_agent")
        
        # Create some production agents
        prod_agent_dir = project_root / "agents" / "prod_agent"
        prod_agent_dir.mkdir(parents=True)
        (prod_agent_dir / "agent.yaml").write_text("id: prod_agent")
        
        return project_root
    
    def test_detect_current_structure(self, mock_project_root):
        """Test structure detection functionality."""
        migrator = StructureMigrator(mock_project_root, dry_run=True)
        detection = migrator.detect_current_structure()
        
        # Verify basic structure detection
        assert detection["has_root_readme"] is True
        assert detection["has_agents_dir"] is True
        assert detection["has_tests_dir"] is True
        assert detection["has_docs_dir"] is True
        assert detection["has_src_dir"] is True
        
        # Verify deprecated scripts detection
        assert "run_tests.py" in detection["deprecated_scripts"]
        assert "run_spec_tests.sh" in detection["deprecated_scripts"]
        
        # Verify extra README files detection
        assert "PROJECT_STRUCTURE.md" in detection["extra_readme_files"]
        assert "QUICK_REFERENCE.md" in detection["extra_readme_files"]
    
    def test_create_backup(self, mock_project_root):
        """Test backup creation functionality."""
        migrator = StructureMigrator(mock_project_root, dry_run=False)
        backup_dir = migrator.create_backup()
        
        # Verify backup directory was created
        assert backup_dir.exists()
        assert backup_dir.is_dir()
        
        # Verify backup contains expected directories
        assert (backup_dir / "src").exists()
        assert (backup_dir / "agents").exists()
        assert (backup_dir / "tests").exists()
        
        # Verify backup contains expected files
        assert (backup_dir / "README.md").exists()
        assert (backup_dir / "requirements.txt").exists()
        assert (backup_dir / "run_tests.py").exists()
        
        # Verify metadata file was created
        metadata_file = backup_dir / "migration_metadata.json"
        assert metadata_file.exists()
        
        with open(metadata_file) as f:
            metadata = json.load(f)
            assert "timestamp" in metadata
            assert "project_root" in metadata
            assert metadata["migration_version"] == "1.0"
    
    def test_move_deprecated_scripts_dry_run(self, mock_project_root):
        """Test deprecated scripts handling in dry run mode."""
        migrator = StructureMigrator(mock_project_root, dry_run=True)
        actions = migrator.move_deprecated_scripts()
        
        # Verify actions were planned
        assert len(actions) == 2
        assert ("run_tests.py", "remove") in actions
        assert ("run_spec_tests.sh", "remove") in actions
        
        # Verify files still exist (dry run)
        assert (mock_project_root / "run_tests.py").exists()
        assert (mock_project_root / "run_spec_tests.sh").exists()
    
    def test_move_deprecated_scripts_execution(self, mock_project_root):
        """Test deprecated scripts handling in execution mode."""
        migrator = StructureMigrator(mock_project_root, dry_run=False)
        
        # Create backup first
        migrator.create_backup()
        
        # Execute script removal
        actions = migrator.move_deprecated_scripts()
        
        # Verify actions were executed
        assert len(actions) == 2
        
        # Verify files were removed
        assert not (mock_project_root / "run_tests.py").exists()
        assert not (mock_project_root / "run_spec_tests.sh").exists()
    
    def test_consolidate_documentation_dry_run(self, mock_project_root):
        """Test documentation consolidation in dry run mode."""
        migrator = StructureMigrator(mock_project_root, dry_run=True)
        moves = migrator.consolidate_documentation()
        
        # Verify moves were planned
        assert len(moves) > 0
        
        # Check specific moves
        move_dict = dict(moves)
        assert "PROJECT_STRUCTURE.md" in move_dict
        assert "QUICK_REFERENCE.md" in move_dict
        
        # Verify files still exist in original location (dry run)
        assert (mock_project_root / "PROJECT_STRUCTURE.md").exists()
        assert (mock_project_root / "QUICK_REFERENCE.md").exists()
    
    def test_consolidate_documentation_execution(self, mock_project_root):
        """Test documentation consolidation in execution mode."""
        migrator = StructureMigrator(mock_project_root, dry_run=False)
        
        # Create backup first
        migrator.create_backup()
        
        # Execute documentation consolidation
        moves = migrator.consolidate_documentation()
        
        # Verify moves were executed
        assert len(moves) > 0
        
        # Verify files were moved
        assert not (mock_project_root / "PROJECT_STRUCTURE.md").exists()
        assert (mock_project_root / "docs" / "reference" / "project-structure.md").exists()
        
        assert not (mock_project_root / "QUICK_REFERENCE.md").exists()
        assert (mock_project_root / "docs" / "QUICK_REFERENCE.md").exists()
    
    def test_organize_test_content(self, mock_project_root):
        """Test test content organization."""
        migrator = StructureMigrator(mock_project_root, dry_run=True)
        result = migrator.organize_test_content()
        
        # Verify test agents were detected
        assert "test_agents" in result
        assert len(result["test_agents"]) > 0
    
    def test_verify_production_content(self, mock_project_root):
        """Test production content verification."""
        migrator = StructureMigrator(mock_project_root, dry_run=True)
        result = migrator.verify_production_content()
        
        # Verify production agents were detected
        assert "production_agents" in result
        assert len(result["production_agents"]) > 0
        assert "prod_agent" in result["production_agents"]
    
    def test_create_missing_directories_dry_run(self, mock_project_root):
        """Test missing directory creation in dry run mode."""
        migrator = StructureMigrator(mock_project_root, dry_run=True)
        created = migrator.create_missing_directories()
        
        # Verify directories would be created
        assert "config" in created
        assert "tests/unit" in created
        assert "tests/integration" in created
        assert "docs/api" in created
        assert "pipelines" in created
        
        # Verify directories don't exist yet (dry run)
        assert not (mock_project_root / "config").exists()
        assert not (mock_project_root / "pipelines").exists()
    
    def test_create_missing_directories_execution(self, mock_project_root):
        """Test missing directory creation in execution mode."""
        migrator = StructureMigrator(mock_project_root, dry_run=False)
        created = migrator.create_missing_directories()
        
        # Verify directories were created
        assert len(created) > 0
        
        # Verify directories exist
        assert (mock_project_root / "config").exists()
        assert (mock_project_root / "tests" / "unit").exists()
        assert (mock_project_root / "tests" / "integration").exists()
        assert (mock_project_root / "docs" / "api").exists()
        assert (mock_project_root / "pipelines").exists()
    
    def test_log_operation(self, mock_project_root):
        """Test operation logging."""
        migrator = StructureMigrator(mock_project_root, dry_run=False)
        
        # Log some operations
        migrator.log_operation("move", "/src/file.py", "/dest/file.py", "success")
        migrator.log_operation("remove", "/old/file.py", "", "success")
        migrator.log_operation("create_dir", "", "/new/dir", "success")
        
        # Verify log entries
        assert len(migrator.migration_log) == 3
        assert migrator.migration_log[0]["operation"] == "move"
        assert migrator.migration_log[1]["operation"] == "remove"
        assert migrator.migration_log[2]["operation"] == "create_dir"
    
    def test_generate_migration_report(self, mock_project_root):
        """Test migration report generation."""
        migrator = StructureMigrator(mock_project_root, dry_run=True)
        
        # Run detection
        detection = migrator.detect_current_structure()
        deprecated_actions = [("run_tests.py", "remove")]
        doc_moves = [("PROJECT_STRUCTURE.md", "docs/reference/project-structure.md")]
        test_content = {"test_agents": ["test_agent"], "test_pipelines": []}
        prod_content = {"production_agents": ["prod_agent"], "example_agents": [], "pipelines": []}
        created_dirs = ["config", "pipelines"]
        
        # Generate report
        report = migrator.generate_migration_report(
            detection, deprecated_actions, doc_moves,
            test_content, prod_content, created_dirs
        )
        
        # Verify report content
        assert "PROJECT STRUCTURE MIGRATION REPORT" in report
        assert "CURRENT STRUCTURE DETECTION" in report
        assert "DEPRECATED SCRIPTS" in report
        assert "DOCUMENTATION CONSOLIDATION" in report
        assert "TEST CONTENT" in report
        assert "PRODUCTION CONTENT" in report
        assert "CREATED DIRECTORIES" in report
        assert "DRY RUN COMPLETE" in report
    
    def test_full_migration_dry_run(self, mock_project_root):
        """Test complete migration in dry run mode."""
        migrator = StructureMigrator(mock_project_root, dry_run=True)
        success = migrator.run_migration()
        
        # Verify migration completed successfully
        assert success is True
        
        # Verify no actual changes were made
        assert (mock_project_root / "run_tests.py").exists()
        assert (mock_project_root / "PROJECT_STRUCTURE.md").exists()
        assert not (mock_project_root / "config").exists()
    
    def test_full_migration_execution(self, mock_project_root):
        """Test complete migration in execution mode."""
        migrator = StructureMigrator(mock_project_root, dry_run=False)
        success = migrator.run_migration()
        
        # Verify migration completed successfully
        assert success is True
        
        # Verify backup was created
        assert migrator.backup_dir is not None
        assert migrator.backup_dir.exists()
        
        # Verify deprecated scripts were removed
        assert not (mock_project_root / "run_tests.py").exists()
        assert not (mock_project_root / "run_spec_tests.sh").exists()
        
        # Verify documentation was moved
        assert not (mock_project_root / "PROJECT_STRUCTURE.md").exists()
        assert (mock_project_root / "docs" / "reference" / "project-structure.md").exists()
        
        # Verify directories were created
        assert (mock_project_root / "config").exists()
        assert (mock_project_root / "pipelines").exists()
        
        # Verify migration log was saved
        log_files = list((mock_project_root / ".migration_backups").glob("migration_log_*.json"))
        assert len(log_files) > 0
        
        # Verify report was saved
        report_files = list((mock_project_root / ".migration_backups").glob("migration_report_*.txt"))
        assert len(report_files) > 0
    
    def test_backup_existing_destination(self, mock_project_root):
        """Test handling of existing destination files during consolidation."""
        migrator = StructureMigrator(mock_project_root, dry_run=False)
        
        # Create backup first
        migrator.create_backup()
        
        # Create a file at the destination
        dest_dir = mock_project_root / "docs" / "reference"
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / "project-structure.md"
        dest_file.write_text("# Existing content")
        
        # Execute documentation consolidation
        moves = migrator.consolidate_documentation()
        
        # Verify backup of existing file was created
        backup_file = dest_dir / "project-structure.md.backup"
        assert backup_file.exists()
        assert backup_file.read_text() == "# Existing content"
        
        # Verify new file was moved
        assert dest_file.exists()
        assert dest_file.read_text() == "# Project Structure"


class TestMigrationScriptIntegration:
    """Integration tests for the migration script."""
    
    def test_script_help(self):
        """Test that the script help works."""
        import subprocess
        result = subprocess.run(
            ["python", "scripts/migrate_structure.py", "--help"],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 0
        assert "Migrate Prompt Lab project structure" in result.stdout
        assert "--dry-run" in result.stdout
        assert "--backup-only" in result.stdout
    
    def test_script_validation(self, temp_dir):
        """Test that the script validates project root."""
        import subprocess
        
        # Create an invalid project directory (no src/)
        invalid_dir = temp_dir / "invalid_project"
        invalid_dir.mkdir()
        
        result = subprocess.run(
            ["python", "scripts/migrate_structure.py", "--project-root", str(invalid_dir)],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1
        # Error message goes to stdout, not stderr
        assert "Not a valid Prompt Lab project" in result.stdout
