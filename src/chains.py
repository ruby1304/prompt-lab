# src/chains.py
from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, Optional, Tuple, Union

import yaml
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableSerializable
from langchain_openai import ChatOpenAI

from .config import get_openai_model_name, get_openai_temperature
from .paths import PROMPT_DIR
from .models import OutputParserConfig
from .output_parser import OutputParserFactory


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
    """根据 Prompt 构建一个 LCEL Chain，并允许配置模型参数。
    
    如果 flow_cfg 中配置了 output_parser，则构建 prompt | llm | parser chain。
    否则保持原有行为 prompt | llm（向后兼容）。
    """

    # 支持模型覆盖，优先级：model_override > flow_cfg.model > 全局默认
    model_name = model_override or flow_cfg.get("model", get_openai_model_name())
    
    llm = ChatOpenAI(
        model=model_name,
        temperature=flow_cfg.get("temperature", get_openai_temperature()),
    )

    # 检查是否配置了 output_parser
    parser_config_dict = flow_cfg.get("output_parser")
    if parser_config_dict:
        # 创建 OutputParserConfig
        parser_config = OutputParserConfig.from_dict(parser_config_dict)
        
        # 创建 parser
        parser = OutputParserFactory.create_parser_from_config(parser_config)
        
        # 构建 prompt | llm | parser chain
        return prompt | llm | parser
    else:
        # 向后兼容：未配置 parser 时返回原始 chain
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
) -> Union[str, Dict[str, Any], Any]:
    """
    对外暴露的核心接口：
    - flow_name: 对应 prompts/{flow_name}.yaml
    - input_text/context: 为了兼容旧用法，自动补充到变量表
    - extra_vars: 任意变量字典，允许多于或少于 Prompt 模板需要的变量

    提示词中的占位符（无论位于 system 还是 user）都会从同一份变量表中解析，
    缺失值依次使用 defaults 或空字符串兜底。
    
    返回值：
    - 如果配置了 output_parser，返回解析后的结构化对象（dict, list 等）
    - 如果未配置 output_parser，返回字符串（向后兼容）
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

    result = chain.invoke(resolved_vars)
    
    # 如果配置了 output_parser，result 已经是解析后的对象
    # 否则 result 是 BaseMessage，需要提取 content
    if flow_cfg.get("output_parser"):
        return result
    else:
        return result.content


def run_flow_with_tokens(
    flow_name: str,
    input_text: str = "",
    context: str = "",
    extra_vars: Dict[str, Any] | None = None,
    agent_id: str = None,
) -> Tuple[Union[str, Dict[str, Any], Any], Dict[str, int], Optional[Dict[str, Any]]]:
    """
    带token统计和parser统计的flow运行接口
    返回: (输出内容, token统计信息, parser统计信息)
    
    输出内容：
    - 如果配置了 output_parser，返回解析后的结构化对象（dict, list 等）
    - 如果未配置 output_parser，返回字符串（向后兼容）
    
    parser统计信息：
    - 如果使用了 RetryOutputParser，返回统计信息字典
    - 否则返回 None
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

    # 使用 chain.invoke 获取结果
    # 注意：当使用 output_parser 时，我们需要从 LLM 的响应中提取 token 信息
    # 但 parser 会转换输出，所以我们需要特殊处理
    
    has_parser = flow_cfg.get("output_parser") is not None
    
    if has_parser:
        # 如果有 parser，我们需要先获取 LLM 的原始响应来提取 token 信息
        # 然后再通过完整的 chain 获取解析后的结果
        
        # 构建不带 parser 的 chain 来获取 token 信息
        model_name = model_override or flow_cfg.get("model", get_openai_model_name())
        llm = ChatOpenAI(
            model=model_name,
            temperature=flow_cfg.get("temperature", get_openai_temperature()),
        )
        llm_chain = prompt | llm
        llm_result = llm_chain.invoke(resolved_vars)
        
        # 提取 token 信息
        token_info = _extract_token_info(llm_result)
        
        # 使用完整的 chain（带 parser）获取解析后的结果
        parsed_result = chain.invoke(resolved_vars)
        
        # 提取 parser 统计信息
        parser_stats = _extract_parser_stats(chain)
        
        return parsed_result, token_info, parser_stats
    else:
        # 没有 parser，使用原有逻辑
        result = chain.invoke(resolved_vars)
        token_info = _extract_token_info(result)
        return result.content, token_info, None


def _extract_token_info(result: BaseMessage) -> Dict[str, int]:
    """从 LLM 响应中提取 token 使用信息"""
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
    
    return token_info


def _extract_parser_stats(chain: RunnableSerializable) -> Optional[Dict[str, Any]]:
    """从 chain 中提取 parser 统计信息"""
    from .output_parser import RetryOutputParser
    
    # 尝试从 chain 的最后一个步骤获取 parser
    # LCEL chain 的结构是 prompt | llm | parser
    if hasattr(chain, 'last'):
        parser = chain.last
        if isinstance(parser, RetryOutputParser):
            return parser.get_statistics().to_dict()
    
    # 尝试从 chain 的 steps 属性获取
    if hasattr(chain, 'steps'):
        for step in reversed(chain.steps):
            if isinstance(step, RetryOutputParser):
                return step.get_statistics().to_dict()
    
    return None
