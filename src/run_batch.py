# src/run_batch.py
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
    default_batch_outfile, ensure_agent_dirs
)
from .agent_registry import load_agent, list_available_agents

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


def run(
    flow: str = typer.Option("", help="使用的 flow 名称；如未指定且提供了 agent，则用 agent 的第一个 flow"),
    infile: str = typer.Option("", help="输入测试集文件；如未指定且提供了 agent，则用 agent 的 default_testset"),
    outfile: str = typer.Option("results.demo.csv", help="输出结果文件名，默认 data/results.demo.csv"),
    agent: str = typer.Option("", help="agent id，对应 agents/{agent}.yaml"),
    limit: int = typer.Option(0, help="最多运行多少条（0=全部）"),
):
    """
    批量跑测试集：读取 JSONL -> 调用模型 -> 写入 CSV

    JSONL 每行是一个变量字典，可以包含除 `id/expected` 外任意字段。
    模板未用到的字段会被忽略，缺失字段将按 Prompt 配置的 defaults 或空字符串兜底。
    """
    # 处理 agent 配置
    agent_cfg = None
    if agent:
        try:
            agent_cfg = load_agent(agent)
            ensure_agent_dirs(agent_cfg.id)
            console.rule("[bold blue]Prompt Lab · Batch Run")
            console.print(f"[bold]Agent[/]: {agent_cfg.id} - {agent_cfg.name}")
            console.print(f"[dim]{agent_cfg.description}[/]")
        except FileNotFoundError as e:
            console.print(f"[red]错误：{e}[/]")
            available_agents = list_available_agents()
            if available_agents:
                console.print(f"[yellow]可用的 agents：{', '.join(available_agents)}[/]")
            raise typer.Exit(1)
    else:
        console.rule("[bold blue]Prompt Lab · Batch Run")

    # 解析 flow
    if not flow:
        if agent_cfg and agent_cfg.flows:
            flow = agent_cfg.flows[0].name
            console.print(f"[bold]Flow[/]: {flow} (使用 agent 默认 flow)")
        else:
            console.print("[red]错误：必须指定 --flow，或者使用 --agent 且保证 agent 配置中有 flows。[/]")
            raise typer.Exit(1)
    else:
        console.print(f"[bold]Flow[/]: {flow}")

    # 解析 infile
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

    # 解析输出路径
    if agent_cfg and outfile == "results.demo.csv":
        # 使用默认路径
        out_path = default_batch_outfile(agent_cfg.id, flow)
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
    total_tokens = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    
    for idx, case in enumerate(cases, start=1):
        _id = case.get("id", idx)

        # 提取所有变量，除了id和expected
        variables = {k: v for k, v in case.items() if k not in ["id", "expected"]}

        # 为了向后兼容，如果有input字段，显示它；否则显示前几个变量
        display_info = case.get("input") or ",".join(list(variables.keys())[:3]) or "<空>"
        console.print(f"[{idx}/{len(cases)}] id={_id}  variables={display_info!r}")

        agent_id = agent_cfg.id if agent_cfg else None
        output, token_info = run_flow_with_tokens(flow, extra_vars=variables, agent_id=agent_id)
        
        # 累计token统计
        for key in total_tokens:
            total_tokens[key] += token_info.get(key, 0)

        # 构建结果行，包含所有原始变量和token信息
        result_row = {"id": _id}
        result_row.update(variables)  # 添加所有变量
        result_row.update({
            "expected": case.get("expected", ""),
            "output": output,
            "input_tokens": token_info.get("input_tokens", 0),
            "output_tokens": token_info.get("output_tokens", 0),
            "total_tokens": token_info.get("total_tokens", 0),
        })
        rows.append(result_row)

    if not rows:
        console.print("[yellow]没有可写入的结果，检查你的测试集文件。[/]")
        return

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    console.print(f"[green]完成！结果已写入：[/] {out_path}")

    # 显示token统计信息
    console.rule("[bold cyan]Token 统计")
    avg_input_tokens = total_tokens["input_tokens"] / len(rows) if rows else 0
    avg_output_tokens = total_tokens["output_tokens"] / len(rows) if rows else 0
    avg_total_tokens = total_tokens["total_tokens"] / len(rows) if rows else 0
    
    token_table = Table(title="Token Usage Summary")
    token_table.add_column("指标", style="bold")
    token_table.add_column("总计", justify="right")
    token_table.add_column("平均每个case", justify="right")
    
    token_table.add_row("输入 Tokens", f"{total_tokens['input_tokens']:,}", f"{avg_input_tokens:.1f}")
    token_table.add_row("输出 Tokens", f"{total_tokens['output_tokens']:,}", f"{avg_output_tokens:.1f}")
    token_table.add_row("总 Tokens", f"{total_tokens['total_tokens']:,}", f"{avg_total_tokens:.1f}")
    
    console.print(token_table)

    # 简单预览前几条
    table = Table(title="Sample Results Preview", show_lines=True)
    # 动态确定要显示的列
    preview_cols = ["id"]
    if "input" in rows[0]:
        preview_cols.append("input")
    preview_cols.extend(["expected", "output", "total_tokens"])

    for col in preview_cols:
        table.add_column(col, overflow="fold")

    for row in rows[:3]:
        row_data = [str(row["id"])]
        if "input" in row:
            row_data.append(row["input"])
        row_data.extend([
            row.get("expected", ""), 
            row["output"][:200], 
            str(row.get("total_tokens", 0))
        ])
        table.add_row(*row_data)
    console.print(table)


if __name__ == "__main__":
    typer.run(run)
