# src/agent_registry.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
AGENT_DIR = ROOT_DIR / "agents"
PROMPT_DIR = ROOT_DIR / "prompts"  # 保留全局prompts目录


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


def load_agent(agent_id: str) -> AgentConfig:
    """加载指定 agent 的配置"""
    # 优先尝试新结构：agents/{agent_id}/agent.yaml
    new_path = AGENT_DIR / agent_id / "agent.yaml"
    # 兼容旧结构：agents/{agent_id}.yaml
    old_path = AGENT_DIR / f"{agent_id}.yaml"
    
    if new_path.exists():
        path = new_path
    elif old_path.exists():
        path = old_path
    else:
        raise FileNotFoundError(f"Agent config not found: {new_path} or {old_path}")
    
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
    )
    
    # 验证配置
    validation_errors = agent_config.validate()
    if validation_errors:
        raise ValueError(f"Agent '{cfg['id']}' 配置验证失败:\n" + "\n".join(f"- {error}" for error in validation_errors))
    
    return agent_config


def list_available_agents() -> List[str]:
    """列出所有可用的 agent ID"""
    if not AGENT_DIR.exists():
        return []
    
    agent_ids = []
    
    # 新结构：agents/{agent_id}/agent.yaml
    for agent_dir in AGENT_DIR.iterdir():
        if (agent_dir.is_dir() and 
            (agent_dir / "agent.yaml").exists() and 
            not agent_dir.name.startswith("_")):  # 排除模板目录
            agent_ids.append(agent_dir.name)
    
    # 兼容旧结构：agents/{agent_id}.yaml
    for yaml_file in AGENT_DIR.glob("*.yaml"):
        if yaml_file.stem not in agent_ids:  # 避免重复
            agent_ids.append(yaml_file.stem)
    
    return sorted(agent_ids)


def find_prompt_file(agent_id: str, flow_file: str) -> Path:
    """查找prompt文件，支持新旧结构"""
    # 优先在agent目录下查找
    agent_prompt_path = AGENT_DIR / agent_id / "prompts" / flow_file
    if agent_prompt_path.exists():
        return agent_prompt_path
    
    # 兼容全局prompts目录
    global_prompt_path = PROMPT_DIR / flow_file
    if global_prompt_path.exists():
        return global_prompt_path
    
    raise FileNotFoundError(f"Prompt file not found: {flow_file} (searched in {agent_prompt_path} and {global_prompt_path})")


def find_testset_file(agent_id: str, testset_file: str) -> Path:
    """查找测试集文件，支持新旧结构"""
    from .compatibility import get_compatible_path
    
    # 使用兼容性路径解析器
    try:
        return get_compatible_path("testset", agent_id, testset_file)
    except Exception:
        # 如果兼容性解析失败，回退到原始逻辑
        # 优先在agent目录下查找
        agent_testset_path = AGENT_DIR / agent_id / "testsets" / testset_file
        if agent_testset_path.exists():
            return agent_testset_path
        
        # 兼容data/testsets目录
        from .paths import agent_testset_dir
        old_testset_path = agent_testset_dir(agent_id) / testset_file
        if old_testset_path.exists():
            return old_testset_path
        
        raise FileNotFoundError(f"Testset file not found: {testset_file} (searched in {agent_testset_path} and {old_testset_path})")


def get_agent_summary(agent_id: str) -> str:
    """获取 agent 的简要信息，用于命令行帮助"""
    try:
        agent = load_agent(agent_id)
        flow_names = [f.name for f in agent.flows]
        return f"{agent.name} (flows: {', '.join(flow_names)})"
    except Exception:
        return f"{agent_id} (配置加载失败)"