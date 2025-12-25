#!/usr/bin/env python3
"""
Agent Registry Sync Tool

This script synchronizes the Agent Registry configuration with the filesystem.
It scans agent directories, detects new/removed/changed agents, and can
automatically update the registry configuration.

Usage:
    # Scan and report differences (dry-run)
    python scripts/sync_agent_registry.py --dry-run
    
    # Scan and auto-update registry
    python scripts/sync_agent_registry.py --auto-update
    
    # Scan specific directories
    python scripts/sync_agent_registry.py --scan-dirs agents/ examples/agents/
    
    # Generate new registry from scratch
    python scripts/sync_agent_registry.py --generate-new

Requirements: 2.5
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

import yaml

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agent_registry_v2 import AgentMetadata, AgentRegistry, SyncResult

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentScanner:
    """Scans filesystem for agent directories and extracts metadata"""
    
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
    
    def scan_directory(
        self,
        scan_dir: Path,
        exclude_patterns: Optional[List[str]] = None
    ) -> Dict[str, Path]:
        """
        Scan a directory for agent subdirectories.
        
        Args:
            scan_dir: Directory to scan
            exclude_patterns: Patterns to exclude (e.g., "_template", ".*")
            
        Returns:
            Dictionary mapping agent_id to agent directory path
        """
        if exclude_patterns is None:
            exclude_patterns = ["_template", ".*", "__pycache__"]
        
        agents = {}
        
        if not scan_dir.exists():
            logger.warning(f"Scan directory not found: {scan_dir}")
            return agents
        
        for agent_dir in scan_dir.iterdir():
            if not agent_dir.is_dir():
                continue
            
            # Check exclude patterns
            agent_name = agent_dir.name
            if any(
                agent_name.startswith(pattern.rstrip("*"))
                for pattern in exclude_patterns
            ):
                logger.debug(f"Excluding {agent_name} (matches exclude pattern)")
                continue
            
            # Check if agent.yaml exists
            config_file = agent_dir / "agent.yaml"
            if not config_file.exists():
                logger.debug(f"Skipping {agent_name} (no agent.yaml)")
                continue
            
            agents[agent_name] = agent_dir
        
        return agents
    
    def load_agent_config(self, agent_dir: Path) -> Optional[Dict]:
        """Load agent.yaml configuration"""
        config_file = agent_dir / "agent.yaml"
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load {config_file}: {e}")
            return None
    
    def infer_metadata_from_config(
        self,
        agent_id: str,
        agent_dir: Path,
        config: Dict
    ) -> AgentMetadata:
        """
        Infer agent metadata from agent.yaml configuration.
        
        Args:
            agent_id: Agent ID
            agent_dir: Agent directory path
            config: Loaded agent.yaml configuration
            
        Returns:
            AgentMetadata with inferred values
        """
        # Get relative path from project root
        try:
            location = agent_dir.relative_to(self.root_dir)
        except ValueError:
            location = agent_dir
        
        # Infer category based on location
        category = "production"  # Default
        if "examples" in str(location):
            category = "example"
        elif "tests" in str(location):
            category = "test"
        elif agent_id in ["judge_default"]:
            category = "system"
        
        # Infer environment
        environment = "production" if category == "production" else "demo"
        if category == "test":
            environment = "test"
        
        # Extract metadata from config
        name = config.get("name", agent_id)
        description = config.get("description", "")
        business_goal = config.get("business_goal")
        
        # Extract tags from config or infer
        tags = []
        if "tags" in config:
            tags = config["tags"]
        else:
            # Infer tags from description or type
            agent_type = config.get("type", "")
            if "summariz" in description.lower() or "总结" in description:
                tags.append("summarization")
            if "memory" in description.lower() or "记忆" in description:
                tags.append("memory")
            if "profile" in description.lower() or "画像" in description:
                tags.append("profile")
            if "judge" in agent_id or "evaluat" in description.lower():
                tags.append("evaluation")
        
        # Get version from config or default
        version = config.get("version", "1.0.0")
        
        # Get owner from config or infer
        owner = config.get("owner", "platform-team")
        
        # Check if deprecated
        deprecated = config.get("deprecated", False)
        
        return AgentMetadata(
            id=agent_id,
            name=name,
            category=category,
            environment=environment,
            owner=owner,
            version=version,
            location=location,
            deprecated=deprecated,
            description=description,
            business_goal=business_goal,
            tags=tags,
            created_at=datetime.now().strftime("%Y-%m-%d"),
            updated_at=datetime.now().strftime("%Y-%m-%d"),
            status="active" if not deprecated else "deprecated"
        )



class RegistrySyncer:
    """Synchronizes Agent Registry with filesystem"""
    
    def __init__(self, registry_path: Path, root_dir: Path):
        self.registry_path = registry_path
        self.root_dir = root_dir
        self.scanner = AgentScanner(root_dir)
    
    def load_registry_config(self) -> Dict:
        """Load the registry configuration file"""
        if not self.registry_path.exists():
            logger.warning(f"Registry config not found: {self.registry_path}")
            return self._create_empty_registry()
        
        try:
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load registry config: {e}")
            raise
    
    def _create_empty_registry(self) -> Dict:
        """Create an empty registry structure"""
        return {
            "version": "1.0",
            "registry": {
                "name": "Prompt Lab Agent Registry",
                "description": "Central registry for all agents",
                "last_updated": datetime.now().strftime("%Y-%m-%d"),
                "maintainer": "platform-team"
            },
            "agents": {},
            "config": {
                "auto_sync": {
                    "enabled": True,
                    "scan_directories": ["agents/", "examples/agents/"],
                    "exclude_patterns": ["_template", ".*", "__pycache__"]
                }
            }
        }
    
    def save_registry_config(self, config: Dict) -> None:
        """Save the registry configuration file"""
        # Update last_updated timestamp
        if "registry" in config:
            config["registry"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
        
        # Ensure parent directory exists
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(self.registry_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    config,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                    indent=2
                )
            logger.info(f"Saved registry config to {self.registry_path}")
        except Exception as e:
            logger.error(f"Failed to save registry config: {e}")
            raise
    
    def scan_filesystem(
        self,
        scan_directories: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> Dict[str, Tuple[Path, Dict]]:
        """
        Scan filesystem for all agents.
        
        Returns:
            Dictionary mapping agent_id to (agent_dir, agent_config)
        """
        if scan_directories is None:
            # Get from registry config
            config = self.load_registry_config()
            auto_sync = config.get("config", {}).get("auto_sync", {})
            scan_directories = auto_sync.get("scan_directories", ["agents/"])
        
        if exclude_patterns is None:
            # Get from registry config
            config = self.load_registry_config()
            auto_sync = config.get("config", {}).get("auto_sync", {})
            exclude_patterns = auto_sync.get(
                "exclude_patterns",
                ["_template", ".*", "__pycache__"]
            )
        
        filesystem_agents = {}
        
        for scan_dir_str in scan_directories:
            scan_dir = self.root_dir / scan_dir_str
            agents = self.scanner.scan_directory(scan_dir, exclude_patterns)
            
            for agent_id, agent_dir in agents.items():
                # Load agent config
                agent_config = self.scanner.load_agent_config(agent_dir)
                if agent_config:
                    filesystem_agents[agent_id] = (agent_dir, agent_config)
        
        return filesystem_agents
    
    def compare_with_registry(
        self,
        filesystem_agents: Dict[str, Tuple[Path, Dict]]
    ) -> Tuple[Set[str], Set[str], Set[str], Dict[str, str]]:
        """
        Compare filesystem agents with registry.
        
        Returns:
            Tuple of (new_agents, removed_agents, updated_agents, conflicts)
        """
        registry_config = self.load_registry_config()
        registry_agents = registry_config.get("agents", {})
        
        filesystem_ids = set(filesystem_agents.keys())
        registry_ids = set(registry_agents.keys())
        
        # Find differences
        new_agents = filesystem_ids - registry_ids
        removed_agents = registry_ids - filesystem_ids
        updated_agents = set()
        conflicts = {}
        
        # Check for location mismatches
        for agent_id in filesystem_ids & registry_ids:
            agent_dir, _ = filesystem_agents[agent_id]
            registry_location = Path(registry_agents[agent_id]["location"])
            
            # Normalize paths
            try:
                fs_location = agent_dir.relative_to(self.root_dir)
            except ValueError:
                fs_location = agent_dir
            
            if fs_location != registry_location:
                updated_agents.add(agent_id)
                conflicts[agent_id] = (
                    f"Location mismatch: registry={registry_location}, "
                    f"filesystem={fs_location}"
                )
        
        return new_agents, removed_agents, updated_agents, conflicts
    
    def sync(
        self,
        auto_add: bool = False,
        auto_remove: bool = False,
        auto_update: bool = False,
        dry_run: bool = True
    ) -> SyncResult:
        """
        Synchronize registry with filesystem.
        
        Args:
            auto_add: Automatically add new agents
            auto_remove: Automatically remove missing agents
            auto_update: Automatically update changed agents
            dry_run: If True, don't actually modify the registry
            
        Returns:
            SyncResult with details of changes
        """
        result = SyncResult()
        
        # Scan filesystem
        logger.info("Scanning filesystem for agents...")
        filesystem_agents = self.scan_filesystem()
        logger.info(f"Found {len(filesystem_agents)} agents in filesystem")
        
        # Compare with registry
        logger.info("Comparing with registry...")
        new_agents, removed_agents, updated_agents, conflicts = \
            self.compare_with_registry(filesystem_agents)
        
        # Load registry config
        registry_config = self.load_registry_config()
        agents_config = registry_config.get("agents", {})
        
        # Handle new agents
        if new_agents:
            logger.info(f"Found {len(new_agents)} new agents")
            for agent_id in sorted(new_agents):
                agent_dir, agent_config = filesystem_agents[agent_id]
                
                if auto_add:
                    # Infer metadata and add to registry
                    metadata = self.scanner.infer_metadata_from_config(
                        agent_id, agent_dir, agent_config
                    )
                    agents_config[agent_id] = metadata.to_dict()
                    result.added.append(agent_id)
                    logger.info(f"  + Added: {agent_id}")
                else:
                    result.added.append(agent_id)
                    logger.info(f"  + New: {agent_id} (not added, use --auto-add)")
        
        # Handle removed agents
        if removed_agents:
            logger.info(f"Found {len(removed_agents)} removed agents")
            for agent_id in sorted(removed_agents):
                if auto_remove:
                    del agents_config[agent_id]
                    result.removed.append(agent_id)
                    logger.info(f"  - Removed: {agent_id}")
                else:
                    result.removed.append(agent_id)
                    logger.info(
                        f"  - Missing: {agent_id} (not removed, use --auto-remove)"
                    )
        
        # Handle updated agents
        if updated_agents:
            logger.info(f"Found {len(updated_agents)} agents with conflicts")
            for agent_id in sorted(updated_agents):
                conflict_msg = conflicts.get(agent_id, "Unknown conflict")
                
                if auto_update:
                    agent_dir, agent_config = filesystem_agents[agent_id]
                    # Update location
                    try:
                        location = agent_dir.relative_to(self.root_dir)
                    except ValueError:
                        location = agent_dir
                    agents_config[agent_id]["location"] = str(location)
                    result.updated.append(agent_id)
                    logger.info(f"  ~ Updated: {agent_id}")
                else:
                    result.updated.append(agent_id)
                    result.errors.append(f"{agent_id}: {conflict_msg}")
                    logger.warning(
                        f"  ~ Conflict: {agent_id} - {conflict_msg} "
                        f"(not updated, use --auto-update)"
                    )
        
        # Save if not dry-run and changes were made
        if not dry_run and (result.added or result.removed or result.updated):
            registry_config["agents"] = agents_config
            self.save_registry_config(registry_config)
            logger.info("Registry configuration updated")
        elif dry_run:
            logger.info("Dry-run mode: no changes were saved")
        
        return result
    
    def generate_new_registry(self) -> Dict:
        """
        Generate a new registry configuration from filesystem.
        
        Returns:
            Complete registry configuration dictionary
        """
        logger.info("Generating new registry from filesystem...")
        
        # Scan filesystem
        filesystem_agents = self.scan_filesystem()
        logger.info(f"Found {len(filesystem_agents)} agents")
        
        # Create registry structure
        registry_config = self._create_empty_registry()
        agents_config = {}
        
        # Add all agents
        for agent_id in sorted(filesystem_agents.keys()):
            agent_dir, agent_config = filesystem_agents[agent_id]
            
            # Infer metadata
            metadata = self.scanner.infer_metadata_from_config(
                agent_id, agent_dir, agent_config
            )
            agents_config[agent_id] = metadata.to_dict()
            logger.info(f"  + {agent_id}")
        
        registry_config["agents"] = agents_config
        
        return registry_config


def print_summary(result: SyncResult) -> None:
    """Print a summary of sync results"""
    print("\n" + "=" * 70)
    print("SYNC SUMMARY")
    print("=" * 70)
    
    if result.added:
        print(f"\n✅ Added ({len(result.added)}):")
        for agent_id in sorted(result.added):
            print(f"   + {agent_id}")
    
    if result.removed:
        print(f"\n❌ Removed ({len(result.removed)}):")
        for agent_id in sorted(result.removed):
            print(f"   - {agent_id}")
    
    if result.updated:
        print(f"\n🔄 Updated ({len(result.updated)}):")
        for agent_id in sorted(result.updated):
            print(f"   ~ {agent_id}")
    
    if result.errors:
        print(f"\n⚠️  Errors ({len(result.errors)}):")
        for error in result.errors:
            print(f"   ! {error}")
    
    if not result.has_changes and not result.has_errors:
        print("\n✨ No changes detected - registry is in sync!")
    
    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description="Synchronize Agent Registry with filesystem",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan and report differences (dry-run)
  python scripts/sync_agent_registry.py --dry-run
  
  # Auto-add new agents
  python scripts/sync_agent_registry.py --auto-add
  
  # Full auto-sync (add, remove, update)
  python scripts/sync_agent_registry.py --auto-update
  
  # Generate new registry from scratch
  python scripts/sync_agent_registry.py --generate-new
        """
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without modifying the registry"
    )
    parser.add_argument(
        "--auto-add",
        action="store_true",
        help="Automatically add new agents found in filesystem"
    )
    parser.add_argument(
        "--auto-remove",
        action="store_true",
        help="Automatically remove agents not found in filesystem"
    )
    parser.add_argument(
        "--auto-update",
        action="store_true",
        help="Automatically update agents with conflicts (implies --auto-add and --auto-remove)"
    )
    parser.add_argument(
        "--generate-new",
        action="store_true",
        help="Generate a new registry from scratch (overwrites existing)"
    )
    parser.add_argument(
        "--registry-path",
        type=Path,
        default=project_root / "config" / "agent_registry.yaml",
        help="Path to agent_registry.yaml (default: config/agent_registry.yaml)"
    )
    parser.add_argument(
        "--scan-dirs",
        nargs="+",
        help="Directories to scan (default: from registry config)"
    )
    parser.add_argument(
        "--exclude",
        nargs="+",
        help="Patterns to exclude (default: from registry config)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create syncer
    syncer = RegistrySyncer(args.registry_path, project_root)
    
    try:
        if args.generate_new:
            # Generate new registry
            logger.info("Generating new registry configuration...")
            registry_config = syncer.generate_new_registry()
            
            if args.dry_run:
                print("\n" + "=" * 70)
                print("GENERATED REGISTRY (DRY-RUN)")
                print("=" * 70)
                print(yaml.dump(registry_config, allow_unicode=True, sort_keys=False))
                print("\nTo save this registry, run without --dry-run")
            else:
                syncer.save_registry_config(registry_config)
                print(f"\n✅ New registry generated and saved to {args.registry_path}")
        
        else:
            # Sync with filesystem
            auto_update = args.auto_update
            auto_add = args.auto_add or auto_update
            auto_remove = args.auto_remove or auto_update
            
            result = syncer.sync(
                auto_add=auto_add,
                auto_remove=auto_remove,
                auto_update=auto_update,
                dry_run=args.dry_run
            )
            
            # Print summary
            print_summary(result)
            
            if args.dry_run and result.has_changes:
                print("\n💡 To apply these changes, run without --dry-run")
                print("   Or use --auto-update to automatically sync everything")
        
        return 0
    
    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=args.verbose)
        return 1


if __name__ == "__main__":
    sys.exit(main())
