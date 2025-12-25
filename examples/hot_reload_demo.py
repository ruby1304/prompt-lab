#!/usr/bin/env python3
"""
Hot Reload Demo

This script demonstrates the hot reload functionality of the Agent Registry.
It watches the registry config file and automatically reloads when changes are detected.

Usage:
    python examples/hot_reload_demo.py

Then, in another terminal, modify the config/agent_registry.yaml file to see
the registry automatically reload.
"""

import time
import logging
from pathlib import Path

from src.agent_registry_v2 import AgentRegistry, ReloadEvent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def on_reload(event: ReloadEvent):
    """Callback function called when registry reloads"""
    if event.success:
        logger.info(f"✅ Registry reloaded successfully!")
        logger.info(f"   Agents: {event.previous_count} → {event.agents_count}")
        logger.info(f"   Time: {event.timestamp.strftime('%H:%M:%S')}")
    else:
        logger.error(f"❌ Registry reload failed!")
        logger.error(f"   Error: {event.error}")
        logger.error(f"   Time: {event.timestamp.strftime('%H:%M:%S')}")


def main():
    """Main function"""
    logger.info("Starting Hot Reload Demo")
    logger.info("=" * 60)
    
    # Create registry with hot reload enabled
    registry = AgentRegistry(enable_hot_reload=True)
    
    # Add reload callback
    registry.add_reload_callback(on_reload)
    
    logger.info(f"Registry loaded with {registry.agent_count} agents")
    logger.info(f"Config file: {registry.config_path}")
    logger.info("")
    logger.info("Hot reload is now active!")
    logger.info("Modify the config file to see automatic reload in action.")
    logger.info("Press Ctrl+C to exit.")
    logger.info("=" * 60)
    
    try:
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\nShutting down...")
        registry.stop_hot_reload()
        logger.info("Hot reload stopped. Goodbye!")


if __name__ == "__main__":
    main()
