# src/run_compare.py
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List

import typer
from rich.console import Console
from rich.table import Table

from .chains import run_flow_with_tokens
from .paths import (
    DATA_DIR, agent_testset_dir, agent_runs_dir, 
    default_compare_outfile, ensure_agent_dirs
)
from .agent_registry import load_agent, list_available_agents

app = typer.Typer()
console = Console()


def load_test_cases(path: Path) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    return cases





@app.callback(invoke_without_command=True)
def compare(
    flows: str = typer.Option(
        "",
        "--flows",
        "-f",
        help="用逗号分隔的多个 flow 名称；如未指定且使用 agent，则默认使用 agent 配置中的全部 flows",
    ),
    infile: str = typer.Option(
        "",
        "--infile",
        "-i", 
        help="输入测试集文件；如未指定且提供了 agent，则用 agent.default_testset",
    ),
    outfile: str = typer.Option(
        "results.compare.csv",
        "--outfile",
        "-o",
        help="输出结果文件名，默认 results.compare.csv",
    ),
    agent: str = typer.Option(
        "",
        help="agent id，对应 agents/{agent}.yaml",
    ),
    limit: int = typer.Option(0, help="最多运行多少条（0=全部）"),
):
    """用同一批测试样本，对比多个 flow 的输出。

    JSONL 每行可以包含任意变量；脚本会把除 id 以外的字段整体传入多个 flow。
    """
    # 处理 agent 配置
    agent_cfg = None
    if agent:
        try:
            agent_cfg = load_agent(agent)
            console.rule("[bold blue]Prompt Lab · Multi-Flow Compare")
            console.print(f"[bold]Agent[/]: {agent_cfg.id} - {agent_cfg.name}")
            console.print(f"[dim]{agent_cfg.description}[/]")
        except FileNotFoundError as e:
            console.print(f"[red]错误：{e}[/]")
            available_agents = list_available_agents()
            if available_agents:
                console.print(f"[yellow]可用的 agents：{', '.join(available_agents)}[/]")
            raise typer.Exit(1)
    else:
        console.rule("[bold blue]Prompt Lab · Multi-Flow Compare")

    # 确保agent目录存在
    if agent_cfg:
        ensure_agent_dirs(agent_cfg.id)
    
    # 解析 testset
    if not infile:
        if agent_cfg:
            infile = agent_cfg.default_testset
            in_path = agent_testset_dir(agent_cfg.id) / infile
            console.print(f"[bold]Testset[/]: {infile} (使用 agent 默认测试集)")
        else:
            console.print("[red]错误：必须指定 --infile，或者使用 --agent。[/]")
            raise typer.Exit(1)
    else:
        if agent_cfg and not Path(infile).is_absolute():
            in_path = agent_testset_dir(agent_cfg.id) / infile
        else:
            in_path = DATA_DIR / infile
        console.print(f"[bold]Testset[/]: {infile}")

    # 解析 flows
    flow_list = []
    if flows:
        flow_list = [x.strip() for x in flows.split(",") if x.strip()]
        console.print(f"[bold]Flows[/]: {', '.join(flow_list)} (手动指定)")
    elif agent_cfg:
        flow_list = [f.name for f in agent_cfg.flows]
        console.print(f"[bold]Flows[/]: {', '.join(flow_list)} (使用 agent 全部 flows)")

    if len(flow_list) < 2:
        console.print("[red]错误：对比至少需要两个 flow。[/]")
        if agent_cfg:
            console.print(f"[yellow]agent '{agent_cfg.id}' 的可用 flows：{[f.name for f in agent_cfg.flows]}[/]")
        raise typer.Exit(1)

    # 解析输出路径
    if agent_cfg and outfile == "results.compare.csv":
        # 使用默认路径
        out_path = default_compare_outfile(agent_cfg.id, flow_list)
        console.print(f"[bold]Output[/]: {out_path.name} (自动生成)")
    elif agent_cfg and not Path(outfile).is_absolute():
        out_path = agent_runs_dir(agent_cfg.id) / outfile
        console.print(f"[bold]Output[/]: {outfile}")
    else:
        out_path = DATA_DIR / outfile
        console.print(f"[bold]Output[/]: {outfile}")
    
    console.print(f"[bold]Input file[/]: {in_path}")
    console.print(f"[bold]Output file[/]: {out_path}")
    
    # 检查输入文件是否存在
    if not in_path.exists():
        console.print(f"[red]错误：测试文件不存在：[/] {in_path}")
        if agent_cfg:
            console.print(f"[yellow]提示：agent '{agent_cfg.id}' 的可用测试集：{', '.join(agent_cfg.all_testsets)}[/]")
        raise typer.Exit(1)

    cases = load_test_cases(in_path)
    if limit > 0:
        cases = cases[:limit]

    rows: List[Dict[str, Any]] = []
    flow_token_stats = {flow: {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0} for flow in flow_list}
    
    for idx, case in enumerate(cases, start=1):
        _id = case.get("id", idx)
        variables = {k: v for k, v in case.items() if k != "id"}

        console.print(f"\n[{idx}/{len(cases)}] id={_id}")

        row: Dict[str, Any] = {"id": _id, **variables}

        # 依次跑每个 flow
        for flow_name in flow_list:
            console.print(f"  -> Running flow: [cyan]{flow_name}[/cyan]")
            agent_id = agent_cfg.id if agent_cfg else None
            output, token_info, _parser_stats = run_flow_with_tokens(flow_name, extra_vars=variables, agent_id=agent_id)
            
            # 保存输出和token信息
            col_name = f"output__{flow_name}"
            row[col_name] = output
            row[f"input_tokens__{flow_name}"] = token_info.get("input_tokens", 0)
            row[f"output_tokens__{flow_name}"] = token_info.get("output_tokens", 0)
            row[f"total_tokens__{flow_name}"] = token_info.get("total_tokens", 0)
            
            # 累计统计
            for key in flow_token_stats[flow_name]:
                flow_token_stats[flow_name][key] += token_info.get(key, 0)
            
            # 打印输出结果的前200个字符和token信息
            output_preview = output[:200] + "..." if len(output) > 200 else output
            console.print(f"     Output: {output_preview}")
            console.print(f"     Tokens: {token_info.get('total_tokens', 0)} (in: {token_info.get('input_tokens', 0)}, out: {token_info.get('output_tokens', 0)})")

        rows.append(row)

    if not rows:
        console.print("[yellow]没有可写入的结果，检查你的测试集文件。[/]")
        return

    # 写 CSV
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    console.print(f"[green]完成！结果已写入：[/] {out_path}")

    # 显示各flow的token统计对比
    console.rule("[bold cyan]Token 统计对比")
    token_compare_table = Table(title="Token Usage Comparison")
    token_compare_table.add_column("Flow", style="bold")
    token_compare_table.add_column("平均输入 Tokens", justify="right")
    token_compare_table.add_column("平均输出 Tokens", justify="right")
    token_compare_table.add_column("平均总 Tokens", justify="right")
    
    for flow_name in flow_list:
        stats = flow_token_stats[flow_name]
        avg_input = stats["input_tokens"] / len(rows) if rows else 0
        avg_output = stats["output_tokens"] / len(rows) if rows else 0
        avg_total = stats["total_tokens"] / len(rows) if rows else 0
        token_compare_table.add_row(
            flow_name,
            f"{avg_input:.1f}",
            f"{avg_output:.1f}",
            f"{avg_total:.1f}"
        )
    
    console.print(token_compare_table)

    # 预览前几条 - 显示 id 和完整输出内容
    table = Table(title="Compare Results Preview", show_lines=True)
    
    # 找出输出列
    output_cols = [col for col in fieldnames if col.startswith("output__")]
    preview_cols = ["id"] + output_cols
    
    for col in preview_cols:
        table.add_column(col, overflow="fold")
    
    for row in rows[:3]:
        preview_row = []
        for col in preview_cols:
            value = row.get(col, "")
            # 完整显示输出内容，不截断
            preview_row.append(str(value))
        table.add_row(*preview_row)
    
    console.print(table)


if __name__ == "__main__":
    app()
