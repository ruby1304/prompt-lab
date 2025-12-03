#!/usr/bin/env python3
"""
演示完整的人工评估工作流程
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

ROOT_DIR = Path(__file__).resolve().parent.parent
console = Console()

app = typer.Typer()


def run_command(cmd: list[str], description: str):
    """运行命令并显示结果"""
    console.print(f"\n[bold blue]步骤：{description}[/]")
    console.print(f"[dim]命令：{' '.join(cmd)}[/]")
    
    try:
        result = subprocess.run(cmd, cwd=ROOT_DIR, capture_output=True, text=True)
        if result.returncode == 0:
            console.print("[green]✓ 成功[/]")
            if result.stdout.strip():
                console.print(result.stdout)
        else:
            console.print(f"[red]✗ 失败 (退出码: {result.returncode})[/]")
            if result.stderr.strip():
                console.print(f"[red]错误：{result.stderr}[/]")
            return False
    except Exception as e:
        console.print(f"[red]✗ 执行失败：{e}[/]")
        return False
    
    return True


@app.command()
def demo(
    agent: str = typer.Option("mem0_l1_summarizer", help="要演示的 agent"),
    skip_compare: bool = typer.Option(False, help="跳过 compare 步骤（如果已有结果）"),
):
    """演示完整的人工评估流程"""
    console.rule("[bold]Manual Evaluation Demo")
    console.print(f"[bold]Agent[/]: {agent}")
    
    # 文件名
    compare_file = f"{agent}.compare.20251203_170456.csv"  # 使用现有文件
    rules_file = f"{agent}.compare.rules.csv"
    review_file = f"{agent}.manual_review.csv"
    
    steps = []
    
    # 步骤1：生成对比结果（可选）
    if not skip_compare:
        steps.append((
            [sys.executable, "-m", "src.run_compare", "compare", "--agent", agent, "--outfile", compare_file],
            f"生成 {agent} 的对比结果"
        ))
    
    # 步骤2：应用规则评估
    steps.append((
        [sys.executable, "-m", "src.eval_rules", "run", "--agent", agent, "--infile", compare_file, "--outfile", rules_file],
        "应用规则评估，过滤明显的 bad case"
    ))
    
    # 步骤3：生成人工评审表
    steps.append((
        [sys.executable, "-m", "src.prepare_manual_review", "--infile", rules_file, "--outfile", review_file],
        "生成人工评审表"
    ))
    
    # 步骤4：显示规则统计
    steps.append((
        [sys.executable, "-m", "src.eval_rules", "stats", "--infile", rules_file],
        "显示规则评估统计"
    ))
    
    # 执行所有步骤
    for i, (cmd, desc) in enumerate(steps, 1):
        console.print(f"\n[bold cyan]== 步骤 {i}/{len(steps)} ==[/]")
        if not run_command(cmd, desc):
            console.print(f"[red]步骤 {i} 失败，停止执行[/]")
            raise typer.Exit(1)
    
    # 完成提示
    console.rule("[bold green]Demo 完成")
    console.print(f"""
[bold]下一步操作：[/]

1. 用 Excel/Numbers 打开：[cyan]data/{review_file}[/]
   - 查看 rule_pass=1 的样本（通过规则检查的）
   - 在 human_score 列填写 0-10 分
   - 在 human_label 列填写 good/bad/edge
   - 在 human_comment 列添加简短备注

2. 打分完成后，运行汇总：
   [cyan]python -m src.summarize_manual_review summary --infile {review_file}[/]

3. 可选：导出特定条件的数据：
   [cyan]python -m src.summarize_manual_review export_filtered --infile {review_file} --labels good,bad[/]

[bold yellow]提示：[/]
- 规则层已经过滤了明显的问题（超长、空输出等）
- 你只需要关注通过规则的样本进行人工判断
- 这样可以大大减少人工工作量和 LLM token 消耗
""")


@app.command()
def summary_demo(
    review_file: str = typer.Option("mem0_l1_summarizer.manual_review.csv", help="人工评审文件"),
):
    """演示汇总人工评审结果"""
    console.rule("[bold]Manual Review Summary Demo")
    
    cmd = [sys.executable, "-m", "src.summarize_manual_review", "summary", "--infile", review_file]
    run_command(cmd, f"汇总 {review_file} 的评审结果")


if __name__ == "__main__":
    app()