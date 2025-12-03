# src/run_single.py
from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

from .chains import run_flow

app = typer.Typer()
console = Console()


@app.callback(invoke_without_command=True)
def chat(
    flow: str = typer.Option("flow_demo", help="使用的 flow 名称，对应 prompts/{flow}.yaml"),
    text: str = typer.Option(..., "--text", "-t", help="用户输入文本"),
    context: str = typer.Option("", "--context", "-c", help="上下文（可选）"),
):
    """单次对话验证：改 Prompt 时快速观察行为"""
    console.rule("[bold blue]Prompt Lab · Single Run")
    console.print(f"[bold]Flow[/]: {flow}")
    console.print(f"[bold]Input[/]: {text}")
    if context:
        console.print(f"[bold]Context[/]: {context}")

    output = run_flow(flow, text, context)

    console.print(
        Panel.fit(
            output,
            title="模型回答",
            border_style="green",
        )
    )


def main():
    """python -m src.run_single 的入口"""
    app()


if __name__ == "__main__":
    main()
