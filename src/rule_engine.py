#!/usr/bin/env python3
"""
规则引擎：处理各种评估规则的核心逻辑
"""
from __future__ import annotations

import re
from typing import Dict, Any, List, Callable


def approx_token_count(text: str) -> int:
    """简单估算 token 数量"""
    if not text:
        return 0
    # 粗略估算：中文每字 1 token，英文按空格分词
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
    other_chars = len(text) - chinese_chars - english_words
    return chinese_chars + english_words + max(0, other_chars // 4)


# 规则处理函数：返回 True 表示违反规则
def handle_max_tokens(rule: Dict[str, Any], value: str) -> bool:
    """处理最大 token 数规则"""
    max_tokens = rule.get("max_tokens", 0)
    return approx_token_count(value) > max_tokens


def handle_max_chars(rule: Dict[str, Any], value: str) -> bool:
    """处理最大字符数规则"""
    max_chars = rule.get("max_chars", 0)
    return len(value) > max_chars


def handle_non_empty(rule: Dict[str, Any], value: str) -> bool:
    """处理非空规则"""
    return not value.strip()


def handle_allowed_values(rule: Dict[str, Any], value: str) -> bool:
    """处理允许值列表规则"""
    allowed = rule.get("allowed_values", [])
    if rule.get("trim", True):
        check_value = value.strip()
    else:
        check_value = value
    return check_value not in allowed


def handle_contains_any(rule: Dict[str, Any], value: str) -> bool:
    """处理包含关键词规则"""
    keywords = rule.get("keywords", [])
    ignore_case = rule.get("ignore_case", False)
    check_text = value.lower() if ignore_case else value
    
    found = any(
        (kw.lower() if ignore_case else kw) in check_text 
        for kw in keywords
    )
    return not found


def handle_regex_match(rule: Dict[str, Any], value: str) -> bool:
    """处理正则匹配规则"""
    pattern = rule.get("pattern", "")
    flags = 0
    if rule.get("ignore_case", False):
        flags |= re.IGNORECASE
    
    try:
        return not re.search(pattern, value, flags)
    except re.error:
        # 正则表达式错误时，认为违反规则
        return True


def handle_starts_with(rule: Dict[str, Any], value: str) -> bool:
    """处理前缀检查规则"""
    prefix = rule.get("prefix", "")
    ignore_case = rule.get("ignore_case", False)
    
    check_value = value.lower() if ignore_case else value
    check_prefix = prefix.lower() if ignore_case else prefix
    
    return not check_value.startswith(check_prefix)


def handle_ends_with(rule: Dict[str, Any], value: str) -> bool:
    """处理后缀检查规则"""
    suffix = rule.get("suffix", "")
    ignore_case = rule.get("ignore_case", False)
    
    check_value = value.lower() if ignore_case else value
    check_suffix = suffix.lower() if ignore_case else suffix
    
    return not check_value.endswith(check_suffix)


# 规则处理器映射表
RULE_HANDLERS: Dict[str, Callable[[Dict[str, Any], str], bool]] = {
    "max_tokens": handle_max_tokens,
    "max_chars": handle_max_chars,
    "non_empty": handle_non_empty,
    "allowed_values": handle_allowed_values,
    "contains_any": handle_contains_any,
    "regex_match": handle_regex_match,
    "starts_with": handle_starts_with,
    "ends_with": handle_ends_with,
}


def get_supported_rule_types() -> List[str]:
    """获取支持的规则类型列表"""
    return list(RULE_HANDLERS.keys())


def validate_rule(rule: Dict[str, Any]) -> List[str]:
    """验证规则配置，返回错误信息列表"""
    errors = []
    
    # 检查必需字段
    if not rule.get("id"):
        errors.append("规则缺少 'id' 字段")
    
    if not rule.get("kind"):
        errors.append("规则缺少 'kind' 字段")
    
    if not rule.get("target"):
        errors.append("规则缺少 'target' 字段")
    
    # 检查规则类型是否支持
    kind = rule.get("kind")
    if kind and kind not in RULE_HANDLERS:
        errors.append(f"不支持的规则类型: {kind}")
    
    # 检查特定规则的参数
    if kind == "max_tokens" and not isinstance(rule.get("max_tokens"), int):
        errors.append("max_tokens 规则缺少有效的 'max_tokens' 参数")
    
    if kind == "max_chars" and not isinstance(rule.get("max_chars"), int):
        errors.append("max_chars 规则缺少有效的 'max_chars' 参数")
    
    if kind == "allowed_values" and not isinstance(rule.get("allowed_values"), list):
        errors.append("allowed_values 规则缺少有效的 'allowed_values' 参数")
    
    if kind == "contains_any" and not isinstance(rule.get("keywords"), list):
        errors.append("contains_any 规则缺少有效的 'keywords' 参数")
    
    if kind == "regex_match" and not rule.get("pattern"):
        errors.append("regex_match 规则缺少 'pattern' 参数")
    
    if kind == "starts_with" and not rule.get("prefix"):
        errors.append("starts_with 规则缺少 'prefix' 参数")
    
    if kind == "ends_with" and not rule.get("suffix"):
        errors.append("ends_with 规则缺少 'suffix' 参数")
    
    return errors


def apply_rule(rule: Dict[str, Any], value: str) -> bool:
    """
    应用单个规则到值上
    
    Args:
        rule: 规则配置字典
        value: 要检查的值
    
    Returns:
        bool: True 表示违反规则，False 表示通过规则
    """
    kind = rule.get("kind")
    if kind not in RULE_HANDLERS:
        # 未知规则类型，认为违反规则
        return True
    
    handler = RULE_HANDLERS[kind]
    try:
        return handler(rule, value)
    except Exception:
        # 规则执行出错，认为违反规则
        return True


def apply_rules(rules: List[Dict[str, Any]], value: str) -> Dict[str, Any]:
    """
    应用规则列表到值上
    
    Args:
        rules: 规则配置列表
        value: 要检查的值
    
    Returns:
        dict: 包含 rule_pass 和 rule_violations 的结果
    """
    violations = []
    
    for rule in rules:
        if apply_rule(rule, value):
            violations.append(rule.get("id", "unknown"))
    
    return {
        "rule_pass": 0 if violations else 1,
        "rule_violations": ",".join(violations)
    }


def get_rule_info() -> Dict[str, Dict[str, Any]]:
    """获取所有规则类型的信息"""
    return {
        "max_tokens": {
            "description": "限制最大 token 数量",
            "required_params": ["max_tokens"],
            "optional_params": [],
            "example": {
                "id": "max_tokens_200",
                "kind": "max_tokens",
                "target": "output",
                "max_tokens": 200,
                "action": "mark_bad"
            }
        },
        "max_chars": {
            "description": "限制最大字符数",
            "required_params": ["max_chars"],
            "optional_params": [],
            "example": {
                "id": "reasonable_length",
                "kind": "max_chars",
                "target": "output",
                "max_chars": 1000,
                "action": "mark_bad"
            }
        },
        "non_empty": {
            "description": "确保输出不为空",
            "required_params": [],
            "optional_params": [],
            "example": {
                "id": "must_not_be_empty",
                "kind": "non_empty",
                "target": "output",
                "action": "mark_bad"
            }
        },
        "allowed_values": {
            "description": "输出必须是指定值之一",
            "required_params": ["allowed_values"],
            "optional_params": ["trim"],
            "example": {
                "id": "binary_output",
                "kind": "allowed_values",
                "target": "output",
                "allowed_values": ["0", "1"],
                "trim": True,
                "action": "mark_bad"
            }
        },
        "contains_any": {
            "description": "输出必须包含至少一个关键词",
            "required_params": ["keywords"],
            "optional_params": ["ignore_case"],
            "example": {
                "id": "should_mention_key_concepts",
                "kind": "contains_any",
                "target": "output",
                "keywords": ["用户", "角色", "对话"],
                "ignore_case": True,
                "action": "mark_bad"
            }
        },
        "regex_match": {
            "description": "输出必须匹配正则表达式",
            "required_params": ["pattern"],
            "optional_params": ["ignore_case"],
            "example": {
                "id": "no_json_format",
                "kind": "regex_match",
                "target": "output",
                "pattern": "^[^{]*$",
                "ignore_case": False,
                "action": "mark_bad"
            }
        },
        "starts_with": {
            "description": "输出必须以指定前缀开头",
            "required_params": ["prefix"],
            "optional_params": ["ignore_case"],
            "example": {
                "id": "must_start_with_summary",
                "kind": "starts_with",
                "target": "output",
                "prefix": "总结：",
                "ignore_case": True,
                "action": "mark_bad"
            }
        },
        "ends_with": {
            "description": "输出必须以指定后缀结尾",
            "required_params": ["suffix"],
            "optional_params": ["ignore_case"],
            "example": {
                "id": "must_end_with_period",
                "kind": "ends_with",
                "target": "output",
                "suffix": "。",
                "ignore_case": False,
                "action": "mark_bad"
            }
        }
    }