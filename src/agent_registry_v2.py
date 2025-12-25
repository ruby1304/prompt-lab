"""
Agent Registry V2 - Unified Agent Registration and Management System

This module provides a centralized registry for managing all agents in the Prompt Lab system.
It supports:
- Loading agent metadata from a central configuration file
- Querying agents by ID, category, environment, and tags
- Filtering and searching agents
- Hot reloading of registry configuration
- Backward compatibility with existing agent_registry.py

For detailed documentation, see: docs/reference/agent-registry-guide.md
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Callable

import yaml
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

logger = logging.getLogger(__name__)

# Default paths
ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY_PATH = ROOT_DIR / "config" / "agent_registry.yaml"


@dataclass
class AgentMetadata:
    """
    Agent metadata from the registry.
    
    This class represents the metadata for a single agent as defined in the
    agent_registry.yaml configuration file.
    """
    id: str
    name: str
    category: str  # "production", "example", "test", "system"
    environment: str  # "production", "staging", "demo", "test"
    owner: str
    version: str
    location: Path
    deprecated: bool
    
    # Optional fields
    description: Optional[str] = None
    business_goal: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    maintainer: Optional[str] = None
    documentation_url: Optional[str] = None
    
    # Deprecation fields
    deprecation_reason: Optional[str] = None
    replacement_agent: Optional[str] = None
    deprecation_date: Optional[str] = None
    removal_date: Optional[str] = None
    
    # Status and metrics
    status: str = "active"  # "active", "deprecated", "experimental", "archived"
    performance_metrics: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """Ensure location is a Path object"""
        if isinstance(self.location, str):
            self.location = Path(self.location)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        data = {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "environment": self.environment,
            "owner": self.owner,
            "version": self.version,
            "location": str(self.location),
            "deprecated": self.deprecated,
            "status": self.status,
        }
        
        # Add optional fields if present
        if self.description:
            data["description"] = self.description
        if self.business_goal:
            data["business_goal"] = self.business_goal
        if self.tags:
            data["tags"] = self.tags
        if self.created_at:
            data["created_at"] = self.created_at
        if self.updated_at:
            data["updated_at"] = self.updated_at
        if self.dependencies:
            data["dependencies"] = self.dependencies
        if self.maintainer:
            data["maintainer"] = self.maintainer
        if self.documentation_url:
            data["documentation_url"] = self.documentation_url
        if self.deprecation_reason:
            data["deprecation_reason"] = self.deprecation_reason
        if self.replacement_agent:
            data["replacement_agent"] = self.replacement_agent
        if self.deprecation_date:
            data["deprecation_date"] = self.deprecation_date
        if self.removal_date:
            data["removal_date"] = self.removal_date
        if self.performance_metrics:
            data["performance_metrics"] = self.performance_metrics
        
        return data
    
    @classmethod
    def from_dict(cls, agent_id: str, data: Dict[str, Any]) -> AgentMetadata:
        """Create AgentMetadata from dictionary"""
        return cls(
            id=agent_id,
            name=data["name"],
            category=data["category"],
            environment=data["environment"],
            owner=data["owner"],
            version=data["version"],
            location=Path(data["location"]),
            deprecated=data.get("deprecated", False),
            description=data.get("description"),
            business_goal=data.get("business_goal"),
            tags=data.get("tags", []),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            dependencies=data.get("dependencies", []),
            maintainer=data.get("maintainer"),
            documentation_url=data.get("documentation_url"),
            deprecation_reason=data.get("deprecation_reason"),
            replacement_agent=data.get("replacement_agent"),
            deprecation_date=data.get("deprecation_date"),
            removal_date=data.get("removal_date"),
            status=data.get("status", "active"),
            performance_metrics=data.get("performance_metrics"),
        )
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AgentMetadata':
        """Create AgentMetadata from JSON string"""
        import json
        data = json.loads(json_str)
        agent_id = data.pop("id")  # Extract id from data
        return cls.from_dict(agent_id, data)


@dataclass
class SyncResult:
    """Result of syncing registry with filesystem"""
    added: List[str] = field(default_factory=list)
    updated: List[str] = field(default_factory=list)
    removed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    
    @property
    def has_changes(self) -> bool:
        """Check if there are any changes"""
        return bool(self.added or self.updated or self.removed)
    
    @property
    def has_errors(self) -> bool:
        """Check if there are any errors"""
        return bool(self.errors)
    
    def summary(self) -> str:
        """Get a summary of the sync result"""
        lines = []
        if self.added:
            lines.append(f"Added: {len(self.added)} agents")
        if self.updated:
            lines.append(f"Updated: {len(self.updated)} agents")
        if self.removed:
            lines.append(f"Removed: {len(self.removed)} agents")
        if self.errors:
            lines.append(f"Errors: {len(self.errors)}")
        
        return ", ".join(lines) if lines else "No changes"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "added": self.added,
            "updated": self.updated,
            "removed": self.removed,
            "errors": self.errors
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SyncResult':
        """Create SyncResult from dictionary"""
        return cls(
            added=data.get("added", []),
            updated=data.get("updated", []),
            removed=data.get("removed", []),
            errors=data.get("errors", [])
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'SyncResult':
        """Create SyncResult from JSON string"""
        import json
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class ReloadEvent:
    """Event data for registry reload notifications"""
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ReloadEvent':
        """Create ReloadEvent from dictionary"""
        from datetime import datetime
        timestamp = datetime.fromisoformat(data["timestamp"])
        return cls(timestamp=timestamp)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ReloadEvent':
        """Create ReloadEvent from JSON string"""
        import json
        data = json.loads(json_str)
        return cls.from_dict(data)
    success: bool
    error: Optional[str] = None
    agents_count: int = 0
    previous_count: int = 0
    
    def __str__(self) -> str:
        if self.success:
            return (
                f"Registry reloaded successfully at {self.timestamp.isoformat()}: "
                f"{self.agents_count} agents (was {self.previous_count})"
            )
        else:
            return (
                f"Registry reload failed at {self.timestamp.isoformat()}: "
                f"{self.error}"
            )


class RegistryFileHandler(FileSystemEventHandler):
    """File system event handler for registry config file changes"""
    
    def __init__(self, registry: 'AgentRegistry', config_path: Path):
        """
        Initialize the file handler.
        
        Args:
            registry: The AgentRegistry instance to reload
            config_path: Path to the config file to watch
        """
        self.registry = registry
        self.config_path = config_path.resolve()
        self._last_reload_time = 0.0
        self._reload_debounce = 1.0  # Debounce reload for 1 second
        
    def on_modified(self, event):
        """Handle file modification events"""
        if event.is_directory:
            return
        
        # Check if the modified file is our config file
        event_path = Path(event.src_path).resolve()
        if event_path != self.config_path:
            return
        
        # Debounce: ignore if we just reloaded recently
        current_time = time.time()
        if current_time - self._last_reload_time < self._reload_debounce:
            return
        
        self._last_reload_time = current_time
        
        # Trigger reload
        logger.info(f"Config file modified: {self.config_path}")
        self.registry._trigger_reload()


class AgentRegistry:
    """
    Unified Agent Registry for managing all agents in the system.
    
    This class provides:
    - Loading agent metadata from config/agent_registry.yaml
    - Querying agents by ID, category, environment, and tags
    - Filtering and searching capabilities
    - Hot reloading support
    - Filesystem synchronization
    
    Example:
        >>> registry = AgentRegistry()
        >>> agent = registry.get_agent("mem0_l1_summarizer")
        >>> agents = registry.list_agents(category="production")
    """
    
    def __init__(self, config_path: Optional[Path] = None, enable_hot_reload: bool = False):
        """
        Initialize the Agent Registry.
        
        Args:
            config_path: Path to agent_registry.yaml. If None, uses default path.
            enable_hot_reload: Whether to enable automatic hot reloading when config changes
        """
        self.config_path = config_path or DEFAULT_REGISTRY_PATH
        self._agents: Dict[str, AgentMetadata] = {}
        self._registry_config: Dict[str, Any] = {}
        self._last_loaded: Optional[datetime] = None
        
        # Hot reload support
        self._hot_reload_enabled = enable_hot_reload
        self._file_observer: Optional[Observer] = None
        self._reload_callbacks: List[Callable[[ReloadEvent], None]] = []
        self._reload_lock = threading.Lock()
        
        # Load registry on initialization
        if self.config_path.exists():
            self.load_registry()
        else:
            logger.warning(f"Registry config not found at {self.config_path}")
        
        # Start hot reload if enabled
        if self._hot_reload_enabled:
            self.start_hot_reload()
    
    def load_registry(self) -> Dict[str, AgentMetadata]:
        """
        Load the agent registry from the configuration file.
        
        Returns:
            Dictionary mapping agent IDs to AgentMetadata
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
            ValueError: If config file has invalid structure
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Registry config not found: {self.config_path}")
        
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            # Validate config structure
            if not isinstance(config, dict):
                raise ValueError("Registry config must be a dictionary")
            
            if "agents" not in config:
                raise ValueError("Registry config must contain 'agents' key")
            
            # Store registry config
            self._registry_config = config
            
            # Parse agents
            agents_data = config["agents"]
            if not isinstance(agents_data, dict):
                raise ValueError("'agents' must be a dictionary")
            
            # Load each agent
            self._agents = {}
            for agent_id, agent_data in agents_data.items():
                try:
                    metadata = AgentMetadata.from_dict(agent_id, agent_data)
                    self._agents[agent_id] = metadata
                except Exception as e:
                    logger.error(f"Failed to load agent '{agent_id}': {e}")
                    raise ValueError(f"Invalid agent metadata for '{agent_id}': {e}")
            
            self._last_loaded = datetime.now()
            logger.info(f"Loaded {len(self._agents)} agents from registry")
            
            return self._agents
            
        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Invalid YAML in registry config: {e}")
    
    def reload_registry(self) -> None:
        """
        Reload the registry from the configuration file.
        
        This is useful for hot reloading when the config file changes.
        """
        logger.info("Reloading agent registry...")
        self.load_registry()
    
    def get_agent(self, agent_id: str) -> AgentMetadata:
        """
        Get agent metadata by ID.
        
        Args:
            agent_id: The agent ID
            
        Returns:
            AgentMetadata for the requested agent
            
        Raises:
            KeyError: If agent not found
        """
        if agent_id not in self._agents:
            available = ", ".join(sorted(self._agents.keys()))
            raise KeyError(
                f"Agent '{agent_id}' not found in registry. "
                f"Available agents: {available}"
            )
        
        return self._agents[agent_id]
    
    def list_agents(
        self,
        category: Optional[str] = None,
        environment: Optional[str] = None,
        tags: Optional[List[str]] = None,
        include_deprecated: bool = True,
        status: Optional[str] = None,
    ) -> List[AgentMetadata]:
        """
        List agents with optional filtering.
        
        Args:
            category: Filter by category ("production", "example", "test", "system")
            environment: Filter by environment ("production", "staging", "demo", "test")
            tags: Filter by tags (agent must have ALL specified tags)
            include_deprecated: Whether to include deprecated agents
            status: Filter by status ("active", "deprecated", "experimental", "archived")
            
        Returns:
            List of AgentMetadata matching the filters
        """
        results = []
        
        for agent in self._agents.values():
            # Filter by deprecated
            if not include_deprecated and agent.deprecated:
                continue
            
            # Filter by category
            if category and agent.category != category:
                continue
            
            # Filter by environment
            if environment and agent.environment != environment:
                continue
            
            # Filter by status
            if status and agent.status != status:
                continue
            
            # Filter by tags (agent must have ALL specified tags)
            if tags:
                agent_tags = set(agent.tags)
                required_tags = set(tags)
                if not required_tags.issubset(agent_tags):
                    continue
            
            results.append(agent)
        
        # Sort by name
        results.sort(key=lambda a: a.name)
        
        return results
    
    def search_agents(
        self,
        query: str,
        search_fields: Optional[List[str]] = None,
        case_sensitive: bool = False,
    ) -> List[AgentMetadata]:
        """
        Search agents by text query.
        
        Args:
            query: Search query string
            search_fields: Fields to search in. Defaults to ["id", "name", "description"]
            case_sensitive: Whether search is case-sensitive
            
        Returns:
            List of AgentMetadata matching the query
        """
        if not query:
            return list(self._agents.values())
        
        if search_fields is None:
            search_fields = ["id", "name", "description", "tags"]
        
        # Prepare query
        search_query = query if case_sensitive else query.lower()
        
        results = []
        for agent in self._agents.values():
            # Check each search field
            for field in search_fields:
                value = getattr(agent, field, None)
                if value is None:
                    continue
                
                # Handle different field types
                if isinstance(value, list):
                    # For lists (like tags), check if any item matches
                    search_values = value if case_sensitive else [str(v).lower() for v in value]
                    if any(search_query in str(v) for v in search_values):
                        results.append(agent)
                        break
                else:
                    # For strings, check if query is in value
                    search_value = str(value) if case_sensitive else str(value).lower()
                    if search_query in search_value:
                        results.append(agent)
                        break
        
        return results
    
    def get_agents_by_tag(self, tag: str) -> List[AgentMetadata]:
        """
        Get all agents with a specific tag.
        
        Args:
            tag: The tag to filter by
            
        Returns:
            List of AgentMetadata with the specified tag
        """
        return [agent for agent in self._agents.values() if tag in agent.tags]
    
    def get_agents_by_owner(self, owner: str) -> List[AgentMetadata]:
        """
        Get all agents owned by a specific team/person.
        
        Args:
            owner: The owner to filter by
            
        Returns:
            List of AgentMetadata owned by the specified owner
        """
        return [agent for agent in self._agents.values() if agent.owner == owner]
    
    def register_agent(self, agent_id: str, metadata: AgentMetadata) -> None:
        """
        Register a new agent in the registry.
        
        Note: This only updates the in-memory registry. To persist changes,
        you need to write the registry back to the config file.
        
        Args:
            agent_id: The agent ID
            metadata: The agent metadata
            
        Raises:
            ValueError: If agent_id doesn't match metadata.id
        """
        if agent_id != metadata.id:
            raise ValueError(
                f"Agent ID mismatch: {agent_id} != {metadata.id}"
            )
        
        self._agents[agent_id] = metadata
        logger.info(f"Registered agent: {agent_id}")
    
    def update_agent(self, agent_id: str, metadata: AgentMetadata) -> None:
        """
        Update an existing agent's metadata.
        
        Note: This only updates the in-memory registry. To persist changes,
        you need to write the registry back to the config file.
        
        Args:
            agent_id: The agent ID
            metadata: The updated agent metadata
            
        Raises:
            KeyError: If agent not found
            ValueError: If agent_id doesn't match metadata.id
        """
        if agent_id not in self._agents:
            raise KeyError(f"Agent '{agent_id}' not found in registry")
        
        if agent_id != metadata.id:
            raise ValueError(
                f"Agent ID mismatch: {agent_id} != {metadata.id}"
            )
        
        self._agents[agent_id] = metadata
        logger.info(f"Updated agent: {agent_id}")
    
    def remove_agent(self, agent_id: str) -> None:
        """
        Remove an agent from the registry.
        
        Note: This only updates the in-memory registry. To persist changes,
        you need to write the registry back to the config file.
        
        Args:
            agent_id: The agent ID
            
        Raises:
            KeyError: If agent not found
        """
        if agent_id not in self._agents:
            raise KeyError(f"Agent '{agent_id}' not found in registry")
        
        del self._agents[agent_id]
        logger.info(f"Removed agent: {agent_id}")
    
    def sync_from_filesystem(
        self,
        scan_directories: Optional[List[Path]] = None,
        exclude_patterns: Optional[List[str]] = None,
        auto_register: bool = False,
    ) -> SyncResult:
        """
        Sync the registry with the filesystem.
        
        This scans the specified directories for agent.yaml files and compares
        them with the registry. It can detect:
        - New agents in filesystem not in registry
        - Agents in registry but not in filesystem
        - Agents with mismatched locations
        
        Args:
            scan_directories: Directories to scan. If None, uses config.
            exclude_patterns: Patterns to exclude (e.g., "_template", ".*")
            auto_register: Whether to automatically register new agents
            
        Returns:
            SyncResult with details of changes and errors
        """
        result = SyncResult()
        
        # Get scan directories from config if not provided
        if scan_directories is None:
            config = self._registry_config.get("config", {})
            auto_sync = config.get("auto_sync", {})
            scan_dirs = auto_sync.get("scan_directories", ["agents/"])
            scan_directories = [ROOT_DIR / d for d in scan_dirs]
        
        # Get exclude patterns from config if not provided
        if exclude_patterns is None:
            config = self._registry_config.get("config", {})
            auto_sync = config.get("auto_sync", {})
            exclude_patterns = auto_sync.get("exclude_patterns", ["_template", ".*"])
        
        # Find all agent directories in filesystem
        filesystem_agents: Dict[str, Path] = {}
        
        for scan_dir in scan_directories:
            if not scan_dir.exists():
                logger.warning(f"Scan directory not found: {scan_dir}")
                continue
            
            for agent_dir in scan_dir.iterdir():
                if not agent_dir.is_dir():
                    continue
                
                # Check exclude patterns
                if any(agent_dir.name.startswith(pattern.rstrip("*")) 
                       for pattern in exclude_patterns):
                    continue
                
                # Check if agent.yaml exists
                config_file = agent_dir / "agent.yaml"
                if config_file.exists():
                    agent_id = agent_dir.name
                    filesystem_agents[agent_id] = agent_dir
        
        # Compare with registry
        registry_ids = set(self._agents.keys())
        filesystem_ids = set(filesystem_agents.keys())
        
        # Find new agents (in filesystem but not in registry)
        new_agents = filesystem_ids - registry_ids
        for agent_id in new_agents:
            result.added.append(agent_id)
            if auto_register:
                # TODO: Implement auto-registration
                # This would require loading the agent.yaml and creating metadata
                logger.info(f"Would auto-register: {agent_id}")
        
        # Find removed agents (in registry but not in filesystem)
        removed_agents = registry_ids - filesystem_ids
        for agent_id in removed_agents:
            result.removed.append(agent_id)
        
        # Find agents with mismatched locations
        for agent_id in registry_ids & filesystem_ids:
            registry_location = self._agents[agent_id].location
            filesystem_location = filesystem_agents[agent_id]
            
            # Normalize paths for comparison
            registry_path = (ROOT_DIR / registry_location).resolve()
            filesystem_path = filesystem_location.resolve()
            
            if registry_path != filesystem_path:
                result.updated.append(agent_id)
                logger.warning(
                    f"Location mismatch for {agent_id}: "
                    f"registry={registry_location}, filesystem={filesystem_location}"
                )
        
        logger.info(f"Sync complete: {result.summary()}")
        return result
    
    @property
    def agent_count(self) -> int:
        """Get the total number of agents in the registry"""
        return len(self._agents)
    
    @property
    def categories(self) -> Set[str]:
        """Get all unique categories in the registry"""
        return {agent.category for agent in self._agents.values()}
    
    @property
    def environments(self) -> Set[str]:
        """Get all unique environments in the registry"""
        return {agent.environment for agent in self._agents.values()}
    
    @property
    def all_tags(self) -> Set[str]:
        """Get all unique tags in the registry"""
        tags = set()
        for agent in self._agents.values():
            tags.update(agent.tags)
        return tags
    
    def start_hot_reload(self) -> None:
        """
        Start watching the config file for changes and auto-reload.
        
        This starts a background file watcher that monitors the registry config file.
        When the file is modified, the registry will automatically reload.
        
        Raises:
            RuntimeError: If hot reload is already running
        """
        if self._file_observer is not None:
            raise RuntimeError("Hot reload is already running")
        
        if not self.config_path.exists():
            logger.warning(
                f"Cannot start hot reload: config file not found at {self.config_path}"
            )
            return
        
        # Create file handler
        handler = RegistryFileHandler(self, self.config_path)
        
        # Create and start observer
        self._file_observer = Observer()
        watch_dir = self.config_path.parent
        self._file_observer.schedule(handler, str(watch_dir), recursive=False)
        self._file_observer.start()
        
        self._hot_reload_enabled = True
        logger.info(f"Hot reload started for {self.config_path}")
    
    def stop_hot_reload(self) -> None:
        """
        Stop the hot reload file watcher.
        
        This stops the background file watcher and cleans up resources.
        """
        if self._file_observer is None:
            return
        
        self._file_observer.stop()
        self._file_observer.join(timeout=5.0)
        self._file_observer = None
        self._hot_reload_enabled = False
        
        logger.info("Hot reload stopped")
    
    def add_reload_callback(self, callback: Callable[[ReloadEvent], None]) -> None:
        """
        Add a callback to be notified when the registry reloads.
        
        The callback will be called with a ReloadEvent object containing
        information about the reload operation.
        
        Args:
            callback: Function to call on reload. Takes a ReloadEvent parameter.
            
        Example:
            >>> def on_reload(event: ReloadEvent):
            ...     print(f"Registry reloaded: {event}")
            >>> registry.add_reload_callback(on_reload)
        """
        self._reload_callbacks.append(callback)
    
    def remove_reload_callback(self, callback: Callable[[ReloadEvent], None]) -> None:
        """
        Remove a previously added reload callback.
        
        Args:
            callback: The callback function to remove
        """
        if callback in self._reload_callbacks:
            self._reload_callbacks.remove(callback)
    
    def _trigger_reload(self) -> None:
        """
        Internal method to trigger a reload and notify callbacks.
        
        This is called by the file watcher when the config file changes.
        """
        with self._reload_lock:
            previous_count = self.agent_count
            
            try:
                # Attempt to reload
                self.reload_registry()
                
                # Create success event
                event = ReloadEvent(
                    timestamp=datetime.now(),
                    success=True,
                    agents_count=self.agent_count,
                    previous_count=previous_count,
                )
                
                logger.info(str(event))
                
            except Exception as e:
                # Create error event
                event = ReloadEvent(
                    timestamp=datetime.now(),
                    success=False,
                    error=str(e),
                    agents_count=self.agent_count,
                    previous_count=previous_count,
                )
                
                logger.error(str(event))
            
            # Notify all callbacks
            for callback in self._reload_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    logger.error(f"Error in reload callback: {e}")
    
    def __del__(self):
        """Cleanup: stop hot reload on deletion"""
        if self._file_observer is not None:
            try:
                self.stop_hot_reload()
            except Exception:
                pass
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.
        
        Returns:
            Dictionary with statistics about the registry
        """
        stats = {
            "total_agents": self.agent_count,
            "by_category": {},
            "by_environment": {},
            "by_status": {},
            "deprecated_count": 0,
            "last_loaded": self._last_loaded.isoformat() if self._last_loaded else None,
            "hot_reload_enabled": self._hot_reload_enabled,
        }
        
        # Count by category
        for category in self.categories:
            stats["by_category"][category] = len(
                [a for a in self._agents.values() if a.category == category]
            )
        
        # Count by environment
        for environment in self.environments:
            stats["by_environment"][environment] = len(
                [a for a in self._agents.values() if a.environment == environment]
            )
        
        # Count by status
        for agent in self._agents.values():
            status = agent.status
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        
        # Count deprecated
        stats["deprecated_count"] = len(
            [a for a in self._agents.values() if a.deprecated]
        )
        
        return stats


# Convenience function for backward compatibility
def get_registry(config_path: Optional[Path] = None) -> AgentRegistry:
    """
    Get or create a singleton AgentRegistry instance.
    
    Args:
        config_path: Path to agent_registry.yaml. If None, uses default path.
        
    Returns:
        AgentRegistry instance
    """
    if not hasattr(get_registry, "_instance"):
        get_registry._instance = AgentRegistry(config_path)
    return get_registry._instance
