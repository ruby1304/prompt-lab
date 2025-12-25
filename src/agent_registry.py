# src/agent_registry.py
"""
Agent Registry - Backward Compatible Interface

This module provides backward compatibility with the existing agent_registry interface
while using the new AgentRegistry v2 system internally.

For new code, consider using agent_registry_v2.AgentRegistry directly.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

import yaml

from .agent_registry_v2 import AgentRegistry as AgentRegistryV2, AgentMetadata

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).resolve().parent.parent

# Agent 目录列表（按优先级排序）
AGENT_DIRS = [
    ROOT_DIR / "agents",           # 生产和系统 Agent（优先级最高）
    ROOT_DIR / "examples" / "agents",  # 示例 Agent
    ROOT_DIR / "tests" / "agents",     # 测试 Agent
]

PROMPT_DIR = ROOT_DIR / "prompts"  # 保留全局prompts目录

# Global registry instance (lazy loaded)
_registry_instance: Optional[AgentRegistryV2] = None


def _get_registry() -> AgentRegistryV2:
    """Get or create the global registry instance"""
    global _registry_instance
    if _registry_instance is None:
        try:
            _registry_instance = AgentRegistryV2()
            logger.info("Initialized AgentRegistry v2")
        except Exception as e:
            logger.warning(f"Failed to initialize AgentRegistry v2: {e}. Falling back to filesystem-only mode.")
            _registry_instance = None
    return _registry_instance


@dataclass
class AgentFlow:
    name: str          # flow 名称（如 mem0_l1_v1）
    file: str          # 对应 prompts 下的文件名（如 mem0_l1_v1.yaml）
    notes: str = ""    # 备注


@dataclass
class AgentConfig:
    id: str
    name: str
    description: str
    business_goal: str
    expectations: Dict[str, Any]
    default_testset: str
    extra_testsets: List[str]
    flows: List[AgentFlow]
    evaluation: Dict[str, Any]
    
    # 新增可选字段
    type: str = "task"           # "task" or "judge"
    model: str | None = None     # 对 judge agent 有用
    temperature: float | None = None
    baseline_flow: str | None = None  # 用于回归测试的基线 flow
    
    # 分类元数据（新增）
    category: str | None = None      # "production", "example", "test", "system"
    environment: str | None = None   # "production", "staging", "demo", "test"
    owner: str | None = None         # 负责团队
    version: str | None = None       # 版本号
    tags: List[str] | None = None    # 标签
    deprecated: bool = False         # 是否废弃

    @property
    def all_testsets(self) -> List[str]:
        if not self.default_testset:
            return self.extra_testsets or []
        return [self.default_testset] + list(self.extra_testsets or [])
    
    def validate(self) -> List[str]:
        """验证 agent 配置的有效性"""
        errors = []
        
        # 验证 baseline_flow 引用
        if self.baseline_flow:
            flow_names = {flow.name for flow in self.flows}
            if self.baseline_flow not in flow_names:
                errors.append(f"baseline_flow '{self.baseline_flow}' 不存在于 flows 列表中")
        
        return errors


def _find_agent_dir(agent_id: str) -> Optional[Path]:
    """在多个目录中查找 Agent 目录"""
    # First try to get from registry v2
    registry = _get_registry()
    if registry:
        try:
            metadata = registry.get_agent(agent_id)
            agent_dir = ROOT_DIR / metadata.location
            if agent_dir.exists() and agent_dir.is_dir():
                return agent_dir
        except KeyError:
            # Agent not in registry, fall back to filesystem search
            pass
    
    # Fall back to filesystem search
    for base_dir in AGENT_DIRS:
        if not base_dir.exists():
            continue
        
        agent_dir = base_dir / agent_id
        if agent_dir.exists() and agent_dir.is_dir():
            config_file = agent_dir / "agent.yaml"
            if config_file.exists():
                return agent_dir
    
    return None


def load_agent(agent_id: str) -> AgentConfig:
    """
    加载指定 agent 的配置（支持多目录）
    
    This function now uses AgentRegistry v2 internally for metadata lookup,
    but maintains backward compatibility with the AgentConfig interface.
    """
    # Try to get metadata from registry v2 first
    registry = _get_registry()
    agent_metadata: Optional[AgentMetadata] = None
    
    if registry:
        try:
            agent_metadata = registry.get_agent(agent_id)
            logger.debug(f"Found agent '{agent_id}' in registry v2")
        except KeyError:
            logger.debug(f"Agent '{agent_id}' not in registry v2, falling back to filesystem")
    
    # 查找 agent 目录
    agent_dir = _find_agent_dir(agent_id)
    
    if agent_dir:
        path = agent_dir / "agent.yaml"
    else:
        # 兼容旧结构：agents/{agent_id}.yaml
        old_path = AGENT_DIRS[0] / f"{agent_id}.yaml"
        if old_path.exists():
            path = old_path
        else:
            raise FileNotFoundError(
                f"Agent config not found: {agent_id}\n"
                f"Searched in: {', '.join(str(d) for d in AGENT_DIRS)}"
            )
    
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    flows = [
        AgentFlow(
            name=f["name"],
            file=f["file"],
            notes=f.get("notes", ""),
        )
        for f in cfg.get("flows", [])
    ]

    # Merge metadata from registry v2 if available
    if agent_metadata:
        # Use registry metadata for classification fields
        agent_config = AgentConfig(
            id=cfg["id"],
            name=cfg.get("name", agent_metadata.name),
            description=cfg.get("description", agent_metadata.description or ""),
            business_goal=cfg.get("business_goal", agent_metadata.business_goal or ""),
            expectations=cfg.get("expectations", {}),
            default_testset=cfg.get("default_testset", ""),
            extra_testsets=cfg.get("extra_testsets", []) or [],
            flows=flows,
            evaluation=cfg.get("evaluation", {}),
            type=cfg.get("type", "task"),
            model=cfg.get("model"),
            temperature=cfg.get("temperature"),
            baseline_flow=cfg.get("baseline_flow"),
            # Use registry v2 metadata for classification
            category=agent_metadata.category,
            environment=agent_metadata.environment,
            owner=agent_metadata.owner,
            version=agent_metadata.version,
            tags=agent_metadata.tags,
            deprecated=agent_metadata.deprecated,
        )
    else:
        # Fall back to agent.yaml only
        agent_config = AgentConfig(
            id=cfg["id"],
            name=cfg.get("name", cfg["id"]),
            description=cfg.get("description", ""),
            business_goal=cfg.get("business_goal", ""),
            expectations=cfg.get("expectations", {}),
            default_testset=cfg.get("default_testset", ""),
            extra_testsets=cfg.get("extra_testsets", []) or [],
            flows=flows,
            evaluation=cfg.get("evaluation", {}),
            type=cfg.get("type", "task"),
            model=cfg.get("model"),
            temperature=cfg.get("temperature"),
            baseline_flow=cfg.get("baseline_flow"),
            # 分类元数据
            category=cfg.get("category"),
            environment=cfg.get("environment"),
            owner=cfg.get("owner"),
            version=cfg.get("version"),
            tags=cfg.get("tags"),
            deprecated=cfg.get("deprecated", False),
        )
    
    # 验证配置
    validation_errors = agent_config.validate()
    if validation_errors:
        raise ValueError(f"Agent '{cfg['id']}' 配置验证失败:\n" + "\n".join(f"- {error}" for error in validation_errors))
    
    return agent_config


def list_available_agents(category: Optional[str] = None, include_deprecated: bool = True) -> List[str]:
    """
    列出所有可用的 agent ID（支持多目录和分类过滤）
    
    This function now uses AgentRegistry v2 internally when available,
    falling back to filesystem scanning for backward compatibility.
    """
    # Try to use registry v2 first
    registry = _get_registry()
    if registry:
        try:
            agents = registry.list_agents(
                category=category,
                include_deprecated=include_deprecated
            )
            agent_ids = [agent.id for agent in agents]
            logger.debug(f"Listed {len(agent_ids)} agents from registry v2")
            return sorted(agent_ids)
        except Exception as e:
            logger.warning(f"Failed to list agents from registry v2: {e}. Falling back to filesystem.")
    
    # Fall back to filesystem scanning
    agent_ids = set()
    
    # 遍历所有 Agent 目录
    for base_dir in AGENT_DIRS:
        if not base_dir.exists():
            continue
        
        # 新结构：{base_dir}/{agent_id}/agent.yaml
        for agent_dir in base_dir.iterdir():
            if (agent_dir.is_dir() and 
                (agent_dir / "agent.yaml").exists() and 
                not agent_dir.name.startswith("_")):  # 排除模板目录
                agent_ids.add(agent_dir.name)
    
    # 兼容旧结构：agents/{agent_id}.yaml
    old_agent_dir = AGENT_DIRS[0]
    if old_agent_dir.exists():
        for yaml_file in old_agent_dir.glob("*.yaml"):
            agent_ids.add(yaml_file.stem)
    
    # 应用过滤器
    if category or not include_deprecated:
        filtered_ids = []
        for agent_id in agent_ids:
            try:
                agent = load_agent(agent_id)
                
                # 过滤 deprecated
                if not include_deprecated and agent.deprecated:
                    continue
                
                # 过滤 category
                if category and agent.category != category:
                    continue
                
                filtered_ids.append(agent_id)
            except Exception:
                # 如果加载失败，仍然包含在列表中
                filtered_ids.append(agent_id)
        
        return sorted(filtered_ids)
    
    return sorted(agent_ids)


def find_prompt_file(agent_id: str, flow_file: str) -> Path:
    """查找prompt文件，支持新旧结构和多目录"""
    # 查找 agent 目录
    agent_dir = _find_agent_dir(agent_id)
    
    if agent_dir:
        # 在 agent 目录下查找
        agent_prompt_path = agent_dir / "prompts" / flow_file
        if agent_prompt_path.exists():
            return agent_prompt_path
    
    # 兼容全局prompts目录
    global_prompt_path = PROMPT_DIR / flow_file
    if global_prompt_path.exists():
        return global_prompt_path
    
    raise FileNotFoundError(
        f"Prompt file not found: {flow_file} for agent {agent_id}\n"
        f"Searched in agent prompts directory and global prompts directory"
    )


def find_testset_file(agent_id: str, testset_file: str) -> Path:
    """查找测试集文件，支持新旧结构和多目录"""
    from .compatibility import get_compatible_path
    
    # 使用兼容性路径解析器
    try:
        return get_compatible_path("testset", agent_id, testset_file)
    except Exception:
        # 如果兼容性解析失败，回退到原始逻辑
        # 查找 agent 目录
        agent_dir = _find_agent_dir(agent_id)
        
        if agent_dir:
            # 在 agent 目录下查找
            agent_testset_path = agent_dir / "testsets" / testset_file
            if agent_testset_path.exists():
                return agent_testset_path
        
        # 兼容data/testsets目录
        from .paths import agent_testset_dir
        old_testset_path = agent_testset_dir(agent_id) / testset_file
        if old_testset_path.exists():
            return old_testset_path
        
        raise FileNotFoundError(
            f"Testset file not found: {testset_file} for agent {agent_id}\n"
            f"Searched in agent testsets directory and data/testsets directory"
        )


def get_agent_summary(agent_id: str) -> str:
    """获取 agent 的简要信息，用于命令行帮助"""
    try:
        agent = load_agent(agent_id)
        flow_names = [f.name for f in agent.flows]
        
        # 添加分类信息
        category_icon = {
            "production": "🚀",
            "example": "📋",
            "test": "🧪",
            "system": "⚙️",
        }.get(agent.category, "")
        
        summary = f"{category_icon} {agent.name}"
        
        if agent.deprecated:
            summary += " [DEPRECATED]"
        
        summary += f" (flows: {', '.join(flow_names)})"
        
        return summary
    except Exception:
        return f"{agent_id} (配置加载失败)"


# New functions to expose registry v2 functionality

def get_registry() -> Optional[AgentRegistryV2]:
    """
    Get the global AgentRegistry v2 instance.
    
    Returns:
        AgentRegistry v2 instance, or None if not available
    """
    return _get_registry()


def reload_registry() -> None:
    """
    Reload the agent registry from the configuration file.
    
    This is useful for hot reloading when the config file changes.
    """
    registry = _get_registry()
    if registry:
        registry.reload_registry()
        logger.info("Agent registry reloaded")
    else:
        logger.warning("Registry v2 not available, cannot reload")


def search_agents(query: str, **kwargs) -> List[str]:
    """
    Search agents by text query.
    
    Args:
        query: Search query string
        **kwargs: Additional search parameters (search_fields, case_sensitive)
        
    Returns:
        List of agent IDs matching the query
    """
    registry = _get_registry()
    if registry:
        try:
            agents = registry.search_agents(query, **kwargs)
            return [agent.id for agent in agents]
        except Exception as e:
            logger.warning(f"Failed to search agents in registry v2: {e}")
    
    # Fall back to simple filtering
    all_agents = list_available_agents()
    query_lower = query.lower()
    return [aid for aid in all_agents if query_lower in aid.lower()]


def get_agents_by_tag(tag: str) -> List[str]:
    """
    Get all agents with a specific tag.
    
    Args:
        tag: The tag to filter by
        
    Returns:
        List of agent IDs with the specified tag
    """
    registry = _get_registry()
    if registry:
        try:
            agents = registry.get_agents_by_tag(tag)
            return [agent.id for agent in agents]
        except Exception as e:
            logger.warning(f"Failed to get agents by tag from registry v2: {e}")
    
    # Fall back to loading all agents and filtering
    result = []
    for agent_id in list_available_agents():
        try:
            agent = load_agent(agent_id)
            if agent.tags and tag in agent.tags:
                result.append(agent_id)
        except Exception:
            pass
    return result


def get_agents_by_owner(owner: str) -> List[str]:
    """
    Get all agents owned by a specific team/person.
    
    Args:
        owner: The owner to filter by
        
    Returns:
        List of agent IDs owned by the specified owner
    """
    registry = _get_registry()
    if registry:
        try:
            agents = registry.get_agents_by_owner(owner)
            return [agent.id for agent in agents]
        except Exception as e:
            logger.warning(f"Failed to get agents by owner from registry v2: {e}")
    
    # Fall back to loading all agents and filtering
    result = []
    for agent_id in list_available_agents():
        try:
            agent = load_agent(agent_id)
            if agent.owner == owner:
                result.append(agent_id)
        except Exception:
            pass
    return result
