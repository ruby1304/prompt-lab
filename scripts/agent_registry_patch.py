#!/usr/bin/env python3
"""
更新 agent_registry.py 以支持多目录加载

使用方法：
    python scripts/agent_registry_patch.py --dry-run  # 预览更改
    python scripts/agent_registry_patch.py            # 实际执行
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
registry_path = project_root / "src" / "agent_registry.py"


def get_updated_content() -> str:
    """返回更新后的 agent_registry.py 内容"""
    return '''# src/agent_registry.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Any, Optional

import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent

# Agent 目录列表（按优先级排序）
AGENT_DIRS = [
    ROOT_DIR / "agents",           # 生产和系统 Agent（优先级最高）
    ROOT_DIR / "examples" / "agents",  # 示例 Agent
    ROOT_DIR / "tests" / "agents",     # 测试 Agent
]

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
    """加载指定 agent 的配置（支持多目录）"""
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
                f"Agent config not found: {agent_id}\\n"
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
        raise ValueError(f"Agent '{cfg['id']}' 配置验证失败:\\n" + "\\n".join(f"- {error}" for error in validation_errors))
    
    return agent_config


def list_available_agents(category: Optional[str] = None, include_deprecated: bool = True) -> List[str]:
    """列出所有可用的 agent ID（支持多目录和分类过滤）"""
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
        f"Prompt file not found: {flow_file} for agent {agent_id}\\n"
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
            f"Testset file not found: {testset_file} for agent {agent_id}\\n"
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
'''


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="更新 agent_registry.py 以支持多目录加载")
    parser.add_argument("--dry-run", action="store_true", help="预览更改，不实际修改文件")
    args = parser.parse_args()
    
    if not registry_path.exists():
        print(f"❌ 文件不存在: {registry_path}")
        return 1
    
    print(f"{'='*80}")
    print(f"更新 agent_registry.py")
    print(f"{'='*80}")
    print(f"文件: {registry_path}")
    print(f"模式: {'预览模式' if args.dry_run else '执行模式'}")
    print(f"{'='*80}\n")
    
    if args.dry_run:
        print("📝 将进行以下更改:\n")
        print("1. 添加 AGENT_DIRS 列表，支持多目录加载")
        print("   - agents/ (生产和系统 Agent)")
        print("   - examples/agents/ (示例 Agent)")
        print("   - tests/agents/ (测试 Agent)")
        print()
        print("2. 添加 _find_agent_dir() 函数，在多个目录中查找 Agent")
        print()
        print("3. 更新 load_agent() 函数，支持多目录加载")
        print()
        print("4. 更新 list_available_agents() 函数，支持分类过滤")
        print("   - 新增 category 参数")
        print("   - 新增 include_deprecated 参数")
        print()
        print("5. 更新 AgentConfig 数据类，添加分类元数据字段")
        print("   - category: 分类")
        print("   - environment: 环境")
        print("   - owner: 负责团队")
        print("   - version: 版本号")
        print("   - tags: 标签")
        print("   - deprecated: 是否废弃")
        print()
        print("6. 更新 find_prompt_file() 和 find_testset_file()，支持多目录")
        print()
        print("7. 更新 get_agent_summary()，显示分类图标")
        print()
        print(f"\n💡 要实际执行，请运行: python {__file__}")
    else:
        # 备份原文件
        backup_path = registry_path.with_suffix(".py.backup")
        import shutil
        shutil.copy2(registry_path, backup_path)
        print(f"✅ 已备份原文件: {backup_path}")
        
        # 写入新内容
        new_content = get_updated_content()
        registry_path.write_text(new_content, encoding='utf-8')
        print(f"✅ 已更新: {registry_path}")
        
        print(f"\n⚠️  重要提示:")
        print(f"   1. 请检查更新后的文件是否正确")
        print(f"   2. 运行测试: pytest tests/")
        print(f"   3. 如果有问题，可以从备份恢复: cp {backup_path} {registry_path}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
