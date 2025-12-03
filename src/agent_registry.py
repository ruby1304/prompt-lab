# src/agent_registry.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
AGENT_DIR = ROOT_DIR / "agents"


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

    @property
    def all_testsets(self) -> List[str]:
        if not self.default_testset:
            return self.extra_testsets or []
        return [self.default_testset] + list(self.extra_testsets or [])


def load_agent(agent_id: str) -> AgentConfig:
    """加载指定 agent 的配置"""
    path = AGENT_DIR / f"{agent_id}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Agent config not found: {path}")
    
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

    return AgentConfig(
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
    )


def list_available_agents() -> List[str]:
    """列出所有可用的 agent ID"""
    if not AGENT_DIR.exists():
        return []
    
    agent_ids = []
    for yaml_file in AGENT_DIR.glob("*.yaml"):
        agent_ids.append(yaml_file.stem)
    
    return sorted(agent_ids)


def get_agent_summary(agent_id: str) -> str:
    """获取 agent 的简要信息，用于命令行帮助"""
    try:
        agent = load_agent(agent_id)
        flow_names = [f.name for f in agent.flows]
        return f"{agent.name} (flows: {', '.join(flow_names)})"
    except Exception:
        return f"{agent_id} (配置加载失败)"