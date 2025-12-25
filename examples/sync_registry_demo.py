#!/usr/bin/env python3
"""
Agent Registry Sync Tool Demo

This script demonstrates how to use the Agent Registry sync functionality
programmatically.

Usage:
    python examples/sync_registry_demo.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.sync_agent_registry import RegistrySyncer, print_summary


def main():
    """Demonstrate Agent Registry sync functionality"""
    
    print("=" * 70)
    print("Agent Registry Sync Tool Demo")
    print("=" * 70)
    print()
    
    # Initialize syncer
    registry_path = project_root / "config" / "agent_registry.yaml"
    syncer = RegistrySyncer(registry_path, project_root)
    
    print("1. Scanning filesystem for agents...")
    print("-" * 70)
    
    # Scan filesystem
    filesystem_agents = syncer.scan_filesystem()
    print(f"Found {len(filesystem_agents)} agents in filesystem:")
    for agent_id in sorted(filesystem_agents.keys()):
        agent_dir, _ = filesystem_agents[agent_id]
        print(f"  - {agent_id} ({agent_dir.relative_to(project_root)})")
    print()
    
    print("2. Comparing with registry...")
    print("-" * 70)
    
    # Compare with registry
    new_agents, removed_agents, updated_agents, conflicts = \
        syncer.compare_with_registry(filesystem_agents)
    
    if new_agents:
        print(f"New agents ({len(new_agents)}):")
        for agent_id in sorted(new_agents):
            print(f"  + {agent_id}")
    
    if removed_agents:
        print(f"Removed agents ({len(removed_agents)}):")
        for agent_id in sorted(removed_agents):
            print(f"  - {agent_id}")
    
    if updated_agents:
        print(f"Updated agents ({len(updated_agents)}):")
        for agent_id in sorted(updated_agents):
            print(f"  ~ {agent_id}: {conflicts.get(agent_id, 'Unknown')}")
    
    if not new_agents and not removed_agents and not updated_agents:
        print("✨ Registry is in sync with filesystem!")
    
    print()
    
    print("3. Performing dry-run sync...")
    print("-" * 70)
    
    # Perform dry-run sync
    result = syncer.sync(
        auto_add=True,
        auto_remove=False,
        auto_update=True,
        dry_run=True
    )
    
    # Print summary
    print_summary(result)
    
    print()
    print("Demo complete!")
    print()
    print("To actually apply changes, run:")
    print("  python scripts/sync_agent_registry.py --auto-update")
    print()


if __name__ == "__main__":
    main()
