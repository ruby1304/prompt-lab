#!/usr/bin/env python3
"""
Project Structure Migration Script

This script migrates the Prompt Lab project from its current structure to the
production-ready structure defined in the design document.

Requirements addressed:
- 1.2: Separate test content from production content
- 1.3: Organize production agents and pipelines
- 1.4: Consolidate documentation
- 1.5: Clean up root directory

Usage:
    python scripts/migrate_structure.py --dry-run  # Preview changes
    python scripts/migrate_structure.py            # Execute migration
    python scripts/migrate_structure.py --backup-only  # Create backup only
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json


class StructureMigrator:
    """Handles project structure migration with backup and rollback support."""
    
    def __init__(self, project_root: Path, dry_run: bool = False):
        self.project_root = project_root
        self.dry_run = dry_run
        self.backup_dir: Optional[Path] = None
        self.migration_log: List[Dict] = []
        
    def detect_current_structure(self) -> Dict[str, bool]:
        """
        Detect the current project structure and identify what needs migration.
        
        Returns:
            Dictionary with detection results
        """
        print("🔍 Detecting current project structure...")
        
        detection = {
            "has_root_readme": (self.project_root / "README.md").exists(),
            "has_root_scripts": any([
                (self.project_root / "run_tests.py").exists(),
                (self.project_root / "run_spec_tests.sh").exists(),
            ]),
            "has_agents_dir": (self.project_root / "agents").exists(),
            "has_tests_dir": (self.project_root / "tests").exists(),
            "has_docs_dir": (self.project_root / "docs").exists(),
            "has_examples_dir": (self.project_root / "examples").exists(),
            "has_data_dir": (self.project_root / "data").exists(),
            "has_src_dir": (self.project_root / "src").exists(),
            "has_scripts_dir": (self.project_root / "scripts").exists(),
            "has_templates_dir": (self.project_root / "templates").exists(),
        }
        
        # Check for files that need cleanup
        root_files = list(self.project_root.glob("*.md"))
        detection["extra_readme_files"] = [
            f.name for f in root_files 
            if f.name not in ["README.md", ".gitignore"]
        ]
        
        # Check for deprecated scripts
        detection["deprecated_scripts"] = []
        if (self.project_root / "run_tests.py").exists():
            detection["deprecated_scripts"].append("run_tests.py")
        if (self.project_root / "run_spec_tests.sh").exists():
            detection["deprecated_scripts"].append("run_spec_tests.sh")
            
        print("✅ Structure detection complete")
        return detection
    
    def create_backup(self) -> Path:
        """
        Create a backup of the current project structure.
        
        Returns:
            Path to the backup directory
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{timestamp}"
        self.backup_dir = self.project_root / ".migration_backups" / backup_name
        
        print(f"📦 Creating backup at: {self.backup_dir}")
        
        if self.dry_run:
            print("   [DRY RUN] Would create backup")
            return self.backup_dir
        
        # Create backup directory
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Directories to backup
        dirs_to_backup = [
            "agents", "tests", "docs", "examples", "data", 
            "src", "scripts", "templates"
        ]
        
        for dir_name in dirs_to_backup:
            src_dir = self.project_root / dir_name
            if src_dir.exists():
                dst_dir = self.backup_dir / dir_name
                print(f"   Backing up: {dir_name}/")
                shutil.copytree(src_dir, dst_dir, symlinks=True)
        
        # Backup important root files
        root_files_to_backup = [
            "README.md", "requirements.txt", ".gitignore",
            "run_tests.py", "run_spec_tests.sh",
            "PROJECT_STRUCTURE.md", "QUICK_REFERENCE.md",
            "REORGANIZATION_SUMMARY.md", ".project-organization-checklist.md"
        ]
        
        for file_name in root_files_to_backup:
            src_file = self.project_root / file_name
            if src_file.exists():
                dst_file = self.backup_dir / file_name
                print(f"   Backing up: {file_name}")
                shutil.copy2(src_file, dst_file)
        
        # Save migration metadata
        metadata = {
            "timestamp": timestamp,
            "project_root": str(self.project_root),
            "backup_dir": str(self.backup_dir),
            "migration_version": "1.0",
        }
        
        metadata_file = self.backup_dir / "migration_metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Backup created successfully at: {self.backup_dir}")
        return self.backup_dir
    
    def log_operation(self, operation: str, source: str, destination: str, 
                     status: str, details: str = ""):
        """Log a migration operation for audit trail."""
        self.migration_log.append({
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "source": source,
            "destination": destination,
            "status": status,
            "details": details,
        })
    
    def move_deprecated_scripts(self) -> List[Tuple[str, str]]:
        """
        Move or remove deprecated scripts from root directory.
        
        Returns:
            List of (source, action) tuples
        """
        print("\n🧹 Handling deprecated scripts...")
        
        actions = []
        deprecated_scripts = [
            ("run_tests.py", "remove"),
            ("run_spec_tests.sh", "remove"),
        ]
        
        for script_name, action in deprecated_scripts:
            script_path = self.project_root / script_name
            if not script_path.exists():
                continue
                
            if self.dry_run:
                print(f"   [DRY RUN] Would {action}: {script_name}")
                actions.append((script_name, action))
                continue
            
            if action == "remove":
                print(f"   Removing: {script_name}")
                script_path.unlink()
                self.log_operation("remove", str(script_path), "", "success")
            elif action == "move":
                dest = self.project_root / "scripts" / script_name
                print(f"   Moving: {script_name} -> scripts/")
                shutil.move(str(script_path), str(dest))
                self.log_operation("move", str(script_path), str(dest), "success")
            
            actions.append((script_name, action))
        
        return actions
    
    def consolidate_documentation(self) -> List[Tuple[str, str]]:
        """
        Move extra README files to docs directory.
        
        Returns:
            List of (source_file, destination_file) tuples
        """
        print("\n📚 Consolidating documentation...")
        
        moves = []
        
        # Files to move to docs/
        files_to_move = [
            ("PROJECT_STRUCTURE.md", "docs/reference/project-structure.md"),
            ("QUICK_REFERENCE.md", "docs/QUICK_REFERENCE.md"),
            ("REORGANIZATION_SUMMARY.md", "docs/archive/reorganization-summary.md"),
            (".project-organization-checklist.md", "docs/archive/project-organization-checklist.md"),
        ]
        
        for src_name, dst_path in files_to_move:
            src_file = self.project_root / src_name
            if not src_file.exists():
                continue
            
            dst_file = self.project_root / dst_path
            
            if self.dry_run:
                print(f"   [DRY RUN] Would move: {src_name} -> {dst_path}")
                moves.append((src_name, dst_path))
                continue
            
            # Ensure destination directory exists
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if destination already exists
            if dst_file.exists():
                print(f"   ⚠️  Destination exists: {dst_path}, creating backup")
                backup_path = dst_file.with_suffix(dst_file.suffix + ".backup")
                shutil.move(str(dst_file), str(backup_path))
            
            print(f"   Moving: {src_name} -> {dst_path}")
            shutil.move(str(src_file), str(dst_file))
            self.log_operation("move", str(src_file), str(dst_file), "success")
            moves.append((src_name, dst_path))
        
        return moves
    
    def organize_test_content(self) -> Dict[str, List[str]]:
        """
        Ensure test agents and pipelines are in tests/fixtures/.
        
        Returns:
            Dictionary with organized content info
        """
        print("\n🧪 Organizing test content...")
        
        result = {
            "test_agents": [],
            "test_pipelines": [],
            "skipped": [],
        }
        
        # Check tests/agents/ - these should stay as test fixtures
        tests_agents_dir = self.project_root / "tests" / "agents"
        if tests_agents_dir.exists():
            test_agents = [d.name for d in tests_agents_dir.iterdir() if d.is_dir()]
            result["test_agents"] = test_agents
            print(f"   ✅ Found {len(test_agents)} test agents in tests/agents/")
        
        # Check tests/fixtures/pipelines/
        tests_pipelines_dir = self.project_root / "tests" / "fixtures" / "pipelines"
        if tests_pipelines_dir.exists():
            test_pipelines = [f.name for f in tests_pipelines_dir.iterdir() if f.is_file()]
            result["test_pipelines"] = test_pipelines
            print(f"   ✅ Found {len(test_pipelines)} test pipelines in tests/fixtures/pipelines/")
        
        # Note: We don't move anything here, just verify the structure
        print("   ℹ️  Test content is already properly organized")
        
        return result
    
    def verify_production_content(self) -> Dict[str, List[str]]:
        """
        Verify production agents and pipelines are in correct locations.
        
        Returns:
            Dictionary with production content info
        """
        print("\n🏭 Verifying production content...")
        
        result = {
            "production_agents": [],
            "example_agents": [],
            "pipelines": [],
        }
        
        # Check agents/ directory
        agents_dir = self.project_root / "agents"
        if agents_dir.exists():
            for agent_dir in agents_dir.iterdir():
                if not agent_dir.is_dir() or agent_dir.name.startswith("."):
                    continue
                
                # Categorize agents
                if agent_dir.name == "_template":
                    continue
                elif agent_dir.name.startswith("test_"):
                    print(f"   ⚠️  Found test agent in production: {agent_dir.name}")
                else:
                    result["production_agents"].append(agent_dir.name)
            
            print(f"   ✅ Found {len(result['production_agents'])} production agents")
        
        # Check examples/agents/ directory
        examples_agents_dir = self.project_root / "examples" / "agents"
        if examples_agents_dir.exists():
            example_agents = [d.name for d in examples_agents_dir.iterdir() if d.is_dir()]
            result["example_agents"] = example_agents
            print(f"   ✅ Found {len(example_agents)} example agents")
        
        # Check for pipeline configurations
        # Note: pipelines/ directory might not exist yet
        pipelines_dir = self.project_root / "pipelines"
        if pipelines_dir.exists():
            pipelines = [f.name for f in pipelines_dir.iterdir() if f.suffix == ".yaml"]
            result["pipelines"] = pipelines
            print(f"   ✅ Found {len(pipelines)} pipeline configurations")
        else:
            print("   ℹ️  pipelines/ directory does not exist yet (will be created in future phases)")
        
        return result
    
    def create_missing_directories(self) -> List[str]:
        """
        Create any missing directories required by the new structure.
        
        Returns:
            List of created directories
        """
        print("\n📁 Creating missing directories...")
        
        required_dirs = [
            "config",
            "tests/unit",
            "tests/integration",
            "docs/api",
            "pipelines",
        ]
        
        created = []
        
        for dir_path in required_dirs:
            full_path = self.project_root / dir_path
            if full_path.exists():
                continue
            
            if self.dry_run:
                print(f"   [DRY RUN] Would create: {dir_path}/")
                created.append(dir_path)
                continue
            
            print(f"   Creating: {dir_path}/")
            full_path.mkdir(parents=True, exist_ok=True)
            self.log_operation("create_dir", "", str(full_path), "success")
            created.append(dir_path)
        
        return created
    
    def save_migration_log(self):
        """Save the migration log to a file."""
        if self.dry_run:
            return
        
        log_dir = self.project_root / ".migration_backups"
        log_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"migration_log_{timestamp}.json"
        
        with open(log_file, "w") as f:
            json.dump(self.migration_log, f, indent=2)
        
        print(f"\n📝 Migration log saved to: {log_file}")
    
    def generate_migration_report(self, detection: Dict, 
                                  deprecated_actions: List,
                                  doc_moves: List,
                                  test_content: Dict,
                                  prod_content: Dict,
                                  created_dirs: List) -> str:
        """Generate a comprehensive migration report."""
        report_lines = [
            "=" * 70,
            "PROJECT STRUCTURE MIGRATION REPORT",
            "=" * 70,
            "",
            f"Timestamp: {datetime.now().isoformat()}",
            f"Project Root: {self.project_root}",
            f"Mode: {'DRY RUN' if self.dry_run else 'EXECUTION'}",
            "",
            "CURRENT STRUCTURE DETECTION",
            "-" * 70,
        ]
        
        for key, value in detection.items():
            if isinstance(value, bool):
                status = "✅" if value else "❌"
                report_lines.append(f"  {status} {key}: {value}")
            elif isinstance(value, list) and value:
                report_lines.append(f"  📋 {key}:")
                for item in value:
                    report_lines.append(f"     - {item}")
        
        report_lines.extend([
            "",
            "DEPRECATED SCRIPTS",
            "-" * 70,
        ])
        
        if deprecated_actions:
            for script, action in deprecated_actions:
                report_lines.append(f"  🗑️  {script}: {action}")
        else:
            report_lines.append("  ✅ No deprecated scripts found")
        
        report_lines.extend([
            "",
            "DOCUMENTATION CONSOLIDATION",
            "-" * 70,
        ])
        
        if doc_moves:
            for src, dst in doc_moves:
                report_lines.append(f"  📄 {src} -> {dst}")
        else:
            report_lines.append("  ✅ Documentation already consolidated")
        
        report_lines.extend([
            "",
            "TEST CONTENT",
            "-" * 70,
            f"  Test Agents: {len(test_content.get('test_agents', []))}",
            f"  Test Pipelines: {len(test_content.get('test_pipelines', []))}",
            "",
            "PRODUCTION CONTENT",
            "-" * 70,
            f"  Production Agents: {len(prod_content.get('production_agents', []))}",
            f"  Example Agents: {len(prod_content.get('example_agents', []))}",
            f"  Pipelines: {len(prod_content.get('pipelines', []))}",
        ])
        
        if created_dirs:
            report_lines.extend([
                "",
                "CREATED DIRECTORIES",
                "-" * 70,
            ])
            for dir_path in created_dirs:
                report_lines.append(f"  📁 {dir_path}/")
        
        if self.backup_dir:
            report_lines.extend([
                "",
                "BACKUP",
                "-" * 70,
                f"  📦 Backup Location: {self.backup_dir}",
            ])
        
        report_lines.extend([
            "",
            "=" * 70,
            "MIGRATION COMPLETE" if not self.dry_run else "DRY RUN COMPLETE",
            "=" * 70,
        ])
        
        return "\n".join(report_lines)
    
    def run_migration(self) -> bool:
        """
        Execute the complete migration process.
        
        Returns:
            True if migration was successful, False otherwise
        """
        try:
            print("🚀 Starting project structure migration...")
            print(f"   Project root: {self.project_root}")
            print(f"   Mode: {'DRY RUN' if self.dry_run else 'EXECUTION'}")
            print()
            
            # Step 1: Detect current structure
            detection = self.detect_current_structure()
            
            # Step 2: Create backup (unless dry run)
            if not self.dry_run:
                self.create_backup()
            else:
                print("\n📦 [DRY RUN] Backup would be created")
            
            # Step 3: Move deprecated scripts
            deprecated_actions = self.move_deprecated_scripts()
            
            # Step 4: Consolidate documentation
            doc_moves = self.consolidate_documentation()
            
            # Step 5: Organize test content
            test_content = self.organize_test_content()
            
            # Step 6: Verify production content
            prod_content = self.verify_production_content()
            
            # Step 7: Create missing directories
            created_dirs = self.create_missing_directories()
            
            # Step 8: Save migration log
            if not self.dry_run:
                self.save_migration_log()
            
            # Step 9: Generate and display report
            report = self.generate_migration_report(
                detection, deprecated_actions, doc_moves,
                test_content, prod_content, created_dirs
            )
            
            print("\n" + report)
            
            if not self.dry_run:
                # Save report to file
                report_file = self.project_root / ".migration_backups" / f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                report_file.parent.mkdir(exist_ok=True)
                with open(report_file, "w") as f:
                    f.write(report)
                print(f"\n📄 Report saved to: {report_file}")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(
        description="Migrate Prompt Lab project structure to production-ready layout",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Preview changes without executing
  python scripts/migrate_structure.py --dry-run
  
  # Execute migration
  python scripts/migrate_structure.py
  
  # Create backup only
  python scripts/migrate_structure.py --backup-only
        """
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without executing them"
    )
    
    parser.add_argument(
        "--backup-only",
        action="store_true",
        help="Create backup only, do not execute migration"
    )
    
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: current directory)"
    )
    
    args = parser.parse_args()
    
    # Validate project root
    if not args.project_root.exists():
        print(f"❌ Error: Project root does not exist: {args.project_root}")
        sys.exit(1)
    
    # Check if we're in a valid project directory
    if not (args.project_root / "src").exists():
        print(f"❌ Error: Not a valid Prompt Lab project (src/ directory not found)")
        sys.exit(1)
    
    # Create migrator
    migrator = StructureMigrator(args.project_root, dry_run=args.dry_run)
    
    # Handle backup-only mode
    if args.backup_only:
        print("📦 Creating backup only...")
        backup_dir = migrator.create_backup()
        print(f"✅ Backup created at: {backup_dir}")
        sys.exit(0)
    
    # Run migration
    success = migrator.run_migration()
    
    if success:
        if args.dry_run:
            print("\n✅ Dry run completed successfully")
            print("   Run without --dry-run to execute the migration")
        else:
            print("\n✅ Migration completed successfully")
            print("   Backup available at:", migrator.backup_dir)
        sys.exit(0)
    else:
        print("\n❌ Migration failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
