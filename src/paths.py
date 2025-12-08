# src/paths.py
"""集中维护项目中的路径常量，避免在脚本里硬编码。"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
PROMPT_DIR = ROOT_DIR / "prompts"


def agent_testset_dir(agent_id: str) -> Path:
    """获取agent的测试集目录（兼容旧结构）"""
    return DATA_DIR / "testsets" / agent_id


def agent_source_testset_dir(agent_id: str) -> Path:
    """获取agent源码目录下的测试集目录（新结构）"""
    return ROOT_DIR / "agents" / agent_id / "testsets"


def agent_runs_dir(agent_id: str) -> Path:
    """获取agent的运行输出目录"""
    return DATA_DIR / "runs" / agent_id


def agent_evals_dir(agent_id: str) -> Path:
    """获取agent的评估结果目录"""
    return DATA_DIR / "evals" / agent_id


def timestamp_str() -> str:
    """生成时间戳字符串"""
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


def default_compare_outfile(agent_id: str, flows: list[str]) -> Path:
    """生成默认的compare输出文件路径"""
    ts = timestamp_str()
    flows_str = "_".join(flows)
    filename = f"{ts}_compare_{flows_str}.csv"
    return agent_runs_dir(agent_id) / filename


def default_batch_outfile(agent_id: str, flow_name: str) -> Path:
    """生成默认的batch输出文件路径"""
    ts = timestamp_str()
    filename = f"{ts}_batch_{flow_name}.csv"
    return agent_runs_dir(agent_id) / filename


def default_rules_outfile(agent_id: str, base_name: str) -> Path:
    """生成默认的规则评估输出文件路径"""
    # base_name 是原始文件名，不带目录
    return agent_evals_dir(agent_id) / "rules" / f"{base_name}.rules.csv"


def default_manual_review_outfile(agent_id: str, base_name: str) -> Path:
    """生成默认的人工评审输出文件路径"""
    return agent_evals_dir(agent_id) / "manual" / f"{base_name}.manual.csv"


def default_llm_eval_outfile(agent_id: str, base_name: str) -> Path:
    """生成默认的LLM评估输出文件路径"""
    return agent_evals_dir(agent_id) / "llm" / f"{base_name}.judge.csv"


def ensure_agent_dirs(agent_id: str) -> None:
    """确保agent的所有目录都存在"""
    agent_testset_dir(agent_id).mkdir(parents=True, exist_ok=True)
    agent_runs_dir(agent_id).mkdir(parents=True, exist_ok=True)
    (agent_evals_dir(agent_id) / "rules").mkdir(parents=True, exist_ok=True)
    (agent_evals_dir(agent_id) / "manual").mkdir(parents=True, exist_ok=True)
    (agent_evals_dir(agent_id) / "llm").mkdir(parents=True, exist_ok=True)
