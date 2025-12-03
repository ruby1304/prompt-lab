# src/chains.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

import yaml
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableSerializable

from .config import get_openai_model_name, get_openai_temperature

ROOT_DIR = Path(__file__).resolve().parent.parent
PROMPT_DIR = ROOT_DIR / "prompts"


def load_flow_config(flow_name: str) -> Dict[str, Any]:
    """从 prompts 目录加载 YAML 配置"""
    path = PROMPT_DIR / f"{flow_name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Prompt config not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_chain(flow_cfg: Dict[str, Any]) -> RunnableSerializable:
    """根据 flow 配置构建一个 LCEL Chain"""
    system_prompt: str = flow_cfg["system_prompt"]
    user_template: str = flow_cfg["user_template"]

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", user_template),
        ]
    )

    llm = ChatOpenAI(
        model=get_openai_model_name(),
        temperature=get_openai_temperature(),
    )

    chain = prompt | llm
    return chain


def run_flow(
    flow_name: str,
    input_text: str = "",
    context: str = "",
    extra_vars: Dict[str, Any] | None = None,
) -> str:
    """
    对外暴露的核心接口：
    - flow_name: 对应 prompts/{flow_name}.yaml
    - input_text: 用户输入（可选，为了向后兼容）
    - context: 额外上下文（可选，为了向后兼容）
    - extra_vars: 变量字典，包含prompt模板需要的所有变量
    """
    flow_cfg = load_flow_config(flow_name)
    chain = build_chain(flow_cfg)

    # 如果extra_vars包含了所有需要的变量，就直接使用
    # 否则使用传统的input/context方式（向后兼容）
    if extra_vars:
        variables = extra_vars.copy()
        # 如果extra_vars中没有input和context，但函数参数有，则添加进去
        if "input" not in variables and input_text:
            variables["input"] = input_text
        if "context" not in variables and context:
            variables["context"] = context
    else:
        variables = {
            "input": input_text,
            "context": context,
        }

    # 为常见的缺失变量提供默认值
    default_values = {
        "user_name": "用户",
        "input": "",
        "context": "",
        "character_profile": "默认角色设定",
        "chat_round_30": "暂无对话记录",
        "cloth_prompt": "默认服装",
        "current_schedule_full_desc": "暂无日程安排",
        "current_schedule_time": "未知时间",
    }
    
    for key, default_value in default_values.items():
        if key not in variables:
            variables[key] = default_value

    result: BaseMessage = chain.invoke(variables)
    # ChatOpenAI 返回的是一条消息对象
    return result.content
