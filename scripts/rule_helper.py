#!/usr/bin/env python3
"""
规则配置助手：帮助快速生成和验证规则配置
"""
from __future__ import annotations

import sys
from pathlib import Path

import typer
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

# 添加 src 到路径
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.rule_engine import get_rule_info, get_supported_rule_types

app = typer.Typer()
console = Console()


@app.command()
def list_types():
    """列出所有支持的规则类型"""
    rule_info = get_rule_info()
    
    table = Table(title="支持的规则类型", show_lines=True)
    table.add_column("类型", style="bold cyan")
    table.add_column("描述", overflow="fold")
    table.add_column("必需参数", style="yellow")
    table.add_column("可选参数", style="green")
    
    for rule_type, info in rule_info.items():
        required = ", ".join(info['required_params']) if info['required_params'] else "-"
        optional = ", ".join(info['optional_params']) if info['optional_params'] else "-"
        
        table.add_row(
            rule_type,
            info['description'],
            required,
            optional
        )
    
    console.print(table)


@app.command()
def generate():
    """交互式生成规则配置"""
    console.print("[bold]规则配置生成器[/]\n")
    
    rules = []
    rule_types = get_supported_rule_types()
    
    while True:
        console.print(f"[bold]当前已配置 {len(rules)} 条规则[/]")
        
        if not Confirm.ask("是否添加新规则？"):
            break
        
        # 选择规则类型
        console.print("\n[bold]选择规则类型：[/]")
        for i, rule_type in enumerate(rule_types, 1):
            console.print(f"  {i}. {rule_type}")
        
        while True:
            try:
                choice = int(Prompt.ask("请输入数字")) - 1
                if 0 <= choice < len(rule_types):
                    selected_type = rule_types[choice]
                    break
                else:
                    console.print("[red]无效选择，请重试[/]")
            except ValueError:
                console.print("[red]请输入有效数字[/]")
        
        # 生成规则配置
        rule = generate_rule_config(selected_type)
        if rule:
            rules.append(rule)
            console.print(f"[green]已添加规则: {rule['id']}[/]\n")
    
    if rules:
        console.print("\n[bold]生成的规则配置：[/]")
        console.print("```yaml")
        console.print("evaluation:")
        console.print("  # ... 其他配置")
        console.print("  rules:")
        
        for rule in rules:
            console.print(f"    - id: \"{rule['id']}\"")
            console.print(f"      kind: \"{rule['kind']}\"")
            console.print(f"      target: \"{rule['target']}\"")
            
            for key, value in rule.items():
                if key not in ['id', 'kind', 'target', 'action']:
                    if isinstance(value, list):
                        console.print(f"      {key}: {value}")
                    elif isinstance(value, str):
                        console.print(f"      {key}: \"{value}\"")
                    else:
                        console.print(f"      {key}: {value}")
            
            console.print(f"      action: \"{rule['action']}\"")
            console.print()
        
        console.print("```")
    else:
        console.print("[yellow]没有生成任何规则[/]")


def generate_rule_config(rule_type: str) -> dict:
    """为指定类型生成规则配置"""
    rule_info = get_rule_info()
    info = rule_info.get(rule_type)
    
    if not info:
        console.print(f"[red]未知规则类型: {rule_type}[/]")
        return {}
    
    console.print(f"\n[bold]配置 {rule_type} 规则[/]")
    console.print(f"描述: {info['description']}")
    
    rule = {
        "kind": rule_type,
        "target": "output",
        "action": "mark_bad"
    }
    
    # 规则 ID
    rule_id = Prompt.ask("规则 ID", default=f"{rule_type}_rule")
    rule["id"] = rule_id
    
    # 必需参数
    for param in info['required_params']:
        if param == "max_tokens":
            value = int(Prompt.ask("最大 token 数", default="200"))
            rule[param] = value
        elif param == "max_chars":
            value = int(Prompt.ask("最大字符数", default="1000"))
            rule[param] = value
        elif param == "allowed_values":
            values_str = Prompt.ask("允许的值（逗号分隔）", default="0,1")
            rule[param] = [v.strip() for v in values_str.split(",")]
        elif param == "keywords":
            keywords_str = Prompt.ask("关键词（逗号分隔）", default="用户,角色,对话")
            rule[param] = [k.strip() for k in keywords_str.split(",")]
        elif param == "pattern":
            pattern = Prompt.ask("正则表达式", default="^[^{]*$")
            rule[param] = pattern
        elif param == "prefix":
            prefix = Prompt.ask("必需前缀", default="总结：")
            rule[param] = prefix
        elif param == "suffix":
            suffix = Prompt.ask("必需后缀", default="。")
            rule[param] = suffix
    
    # 可选参数
    for param in info['optional_params']:
        if param == "trim":
            rule[param] = Confirm.ask("是否去除首尾空白？", default=True)
        elif param == "ignore_case":
            rule[param] = Confirm.ask("是否忽略大小写？", default=True)
    
    return rule


@app.command()
def examples():
    """显示常用规则配置示例"""
    console.print("[bold]常用规则配置示例[/]\n")
    
    examples = {
        "最小规则集（推荐起点）": [
            {
                "id": "not_empty",
                "kind": "non_empty",
                "target": "output",
                "action": "mark_bad"
            },
            {
                "id": "reasonable_length",
                "kind": "max_chars",
                "target": "output",
                "max_chars": 2000,
                "action": "mark_bad"
            }
        ],
        "对话总结 Agent": [
            {
                "id": "summary_length",
                "kind": "max_tokens",
                "target": "output",
                "max_tokens": 300,
                "action": "mark_bad"
            },
            {
                "id": "not_empty",
                "kind": "non_empty",
                "target": "output",
                "action": "mark_bad"
            },
            {
                "id": "must_mention_dialogue",
                "kind": "contains_any",
                "target": "output",
                "keywords": ["用户", "角色", "对话", "交流"],
                "ignore_case": True,
                "action": "mark_bad"
            }
        ],
        "分类 Agent": [
            {
                "id": "valid_category_only",
                "kind": "allowed_values",
                "target": "output",
                "allowed_values": ["positive", "negative", "neutral"],
                "trim": True,
                "action": "mark_bad"
            }
        ],
        "二元判断 Agent": [
            {
                "id": "binary_only",
                "kind": "allowed_values",
                "target": "output",
                "allowed_values": ["0", "1", "yes", "no"],
                "trim": True,
                "action": "mark_bad"
            }
        ]
    }
    
    for category, rules in examples.items():
        console.print(f"[bold cyan]{category}[/]:")
        console.print("```yaml")
        console.print("rules:")
        
        for rule in rules:
            console.print(f"  - id: \"{rule['id']}\"")
            console.print(f"    kind: \"{rule['kind']}\"")
            console.print(f"    target: \"{rule['target']}\"")
            
            for key, value in rule.items():
                if key not in ['id', 'kind', 'target', 'action']:
                    if isinstance(value, list):
                        console.print(f"    {key}: {value}")
                    elif isinstance(value, str):
                        console.print(f"    {key}: \"{value}\"")
                    else:
                        console.print(f"    {key}: {value}")
            
            console.print(f"    action: \"{rule['action']}\"")
        
        console.print("```\n")


if __name__ == "__main__":
    app()