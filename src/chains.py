# src/chains.py
from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Tuple

import yaml
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from langchain_openai import ChatOpenAI

from .config import get_openai_model_name, get_openai_temperature
from .paths import PROMPT_DIR


def load_flow_config(flow_name: str, agent_id: str = None) -> Dict[str, Any]:
    """加载 YAML 配置，支持新旧结构"""
    if agent_id:
        # 如果提供了agent_id，使用新的查找逻辑
        from .agent_registry import find_prompt_file
        try:
            path = find_prompt_file(agent_id, f"{flow_name}.yaml")
        except FileNotFoundError:
            # 如果在agent目录找不到，尝试全局目录
            path = PROMPT_DIR / f"{flow_name}.yaml"
    else:
        # 兼容旧的直接调用方式
        path = PROMPT_DIR / f"{flow_name}.yaml"
    
    if not path.exists():
        raise FileNotFoundError(f"Prompt config not found: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_prompt(flow_cfg: Mapping[str, Any]) -> ChatPromptTemplate:
    """根据 flow 配置构建 Prompt 对象。"""

    system_prompt: str = flow_cfg["system_prompt"]
    user_template: str = flow_cfg["user_template"]

    return ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", user_template),
        ]
    )


def build_chain(prompt: ChatPromptTemplate, flow_cfg: Mapping[str, Any], model_override: str = None) -> RunnableSerializable:
    """根据 Prompt 构建一个 LCEL Chain，并允许配置模型参数。"""

    # 支持模型覆盖，优先级：model_override > flow_cfg.model > 全局默认
    model_name = model_override or flow_cfg.get("model", get_openai_model_name())
    
    llm = ChatOpenAI(
        model=model_name,
        temperature=flow_cfg.get("temperature", get_openai_temperature()),
    )

    return prompt | llm


def _merge_variables(
    required_vars: Iterable[str],
    provided_vars: Mapping[str, Any],
    fallback: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """确保每个必需变量都有值，并应用兜底逻辑。

    优先级：用户传入 > prompt 配置 defaults > 全局默认空字符串。
    """

    fallback = fallback or {}
    merged: Dict[str, Any] = {}
    for key in required_vars:
        if key in provided_vars:
            merged[key] = provided_vars[key]
        elif key in fallback:
            merged[key] = fallback[key]
        else:
            merged[key] = ""
    return merged


def run_flow(
    flow_name: str,
    input_text: str = "",
    context: str = "",
    extra_vars: Dict[str, Any] | None = None,
    agent_id: str = None,
) -> str:
    """
    对外暴露的核心接口：
    - flow_name: 对应 prompts/{flow_name}.yaml
    - input_text/context: 为了兼容旧用法，自动补充到变量表
    - extra_vars: 任意变量字典，允许多于或少于 Prompt 模板需要的变量

    提示词中的占位符（无论位于 system 还是 user）都会从同一份变量表中解析，
    缺失值依次使用 defaults 或空字符串兜底。
    """

    flow_cfg = load_flow_config(flow_name, agent_id)
    prompt = build_prompt(flow_cfg)
    
    # 检查是否有模型覆盖
    model_override = None
    if extra_vars and "_model_override" in extra_vars:
        model_override = extra_vars.pop("_model_override")
    
    chain = build_chain(prompt, flow_cfg, model_override)

    provided_vars: Dict[str, Any] = {}
    if extra_vars:
        provided_vars.update(extra_vars)
    if input_text:
        provided_vars.setdefault("input", input_text)
    if context:
        provided_vars.setdefault("context", context)

    required_vars = prompt.input_variables
    resolved_vars = _merge_variables(
        required_vars,
        provided_vars,
        fallback=flow_cfg.get("defaults", {}),
    )

    result: BaseMessage = chain.invoke(resolved_vars)
    return result.content


def run_flow_with_tokens(
    flow_name: str,
    input_text: str = "",
    context: str = "",
    extra_vars: Dict[str, Any] | None = None,
    agent_id: str = None,
) -> Tuple[str, Dict[str, int]]:
    """
    带token统计的flow运行接口
    返回: (输出内容, token统计信息)
    """
    
    flow_cfg = load_flow_config(flow_name, agent_id)
    prompt = build_prompt(flow_cfg)
    
    # 检查是否有模型覆盖
    model_override = None
    if extra_vars and "_model_override" in extra_vars:
        model_override = extra_vars.pop("_model_override")
    
    # 支持模型覆盖
    model_name = model_override or flow_cfg.get("model", get_openai_model_name())
    
    llm = ChatOpenAI(
        model=model_name,
        temperature=flow_cfg.get("temperature", get_openai_temperature()),
    )
    
    chain = prompt | llm

    provided_vars: Dict[str, Any] = {}
    if extra_vars:
        provided_vars.update(extra_vars)
    if input_text:
        provided_vars.setdefault("input", input_text)
    if context:
        provided_vars.setdefault("context", context)

    required_vars = prompt.input_variables
    resolved_vars = _merge_variables(
        required_vars,
        provided_vars,
        fallback=flow_cfg.get("defaults", {}),
    )

    # 使用with_config来获取token使用信息
    result = chain.invoke(resolved_vars)
    
    # 从result中提取token信息
    token_info = {}
    if hasattr(result, 'usage_metadata') and result.usage_metadata:
        usage = result.usage_metadata
        token_info = {
            'input_tokens': usage.get('input_tokens', 0),
            'output_tokens': usage.get('output_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0)
        }
    else:
        # 如果没有usage_metadata，尝试从response_metadata获取
        if hasattr(result, 'response_metadata') and result.response_metadata:
            usage = result.response_metadata.get('token_usage', {})
            token_info = {
                'input_tokens': usage.get('prompt_tokens', 0),
                'output_tokens': usage.get('completion_tokens', 0),
                'total_tokens': usage.get('total_tokens', 0)
            }
    
    return result.content, token_info
