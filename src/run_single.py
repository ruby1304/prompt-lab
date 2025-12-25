# src/run_single.py
from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

import json

from .chains import run_flow_with_tokens

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def chat(
    flow: str = typer.Option("flow_demo", help="使用的 flow 名称，对应 prompts/{flow}.yaml"),
    text: str = typer.Option("", "--text", "-t", help="用户输入文本（可留空）"),
    context: str = typer.Option("", "--context", "-c", help="上下文（可选）"),
    variables: str = typer.Option(
        "{}",
        "--vars",
        "-v",
        help="额外变量的 JSON 字符串，例如 '{\"name\": \"张三\"}'",
    ),
):
    """单次对话验证：改 Prompt 时快速观察行为"""
    console.rule("[bold blue]Prompt Lab · Single Run")
    console.print(f"[bold]Flow[/]: {flow}")
    if text:
        console.print(f"[bold]Input[/]: {text}")
    if context:
        console.print(f"[bold]Context[/]: {context}")

    try:
        extra_vars = json.loads(variables)
        if not isinstance(extra_vars, dict):
            raise ValueError("vars 需要是 JSON 对象")
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"无法解析 vars：{exc}")
    except ValueError as exc:  # 保持提示友好
        raise typer.BadParameter(str(exc))

    output, token_info, _parser_stats = run_flow_with_tokens(flow, text, context, extra_vars=extra_vars)

    console.print(
        Panel.fit(
            output,
            title="模型回答",
            border_style="green",
        )
    )
    
    # 显示token使用信息
    if token_info:
        console.print(f"\n[bold cyan]Token 使用情况:[/]")
        console.print(f"  输入 Tokens: {token_info.get('input_tokens', 0):,}")
        console.print(f"  输出 Tokens: {token_info.get('output_tokens', 0):,}")
        console.print(f"  总 Tokens: {token_info.get('total_tokens', 0):,}")


def main():
    """python -m src.run_single 的入口"""
    app()


if __name__ == "__main__":
    main()
