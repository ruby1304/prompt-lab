# src/run_eval.py
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table

from .chains import run_flow_with_tokens
from .paths import DATA_DIR
from .agent_registry import load_agent, list_available_agents
from .eval_llm_judge import build_judge_chain, judge_one

app = typer.Typer()
console = Console()


def load_test_cases(path: Path) -> List[Dict[str, Any]]:
    """加载测试用例"""
    cases: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    return cases


def generate_output_filename(agent_id: str, flows: List[str], with_judge: bool) -> str:
    """生成输出文件名"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if len(flows) == 1:
        flow_part = flows[0]
    else:
        flow_part = "compare"
    
    suffix = "eval" if with_judge else "results"
    return f"{agent_id}_{flow_part}.{suffix}.{timestamp}.csv"


@app.callback(invoke_without_command=True)
def run_eval(
    agent: str = typer.Option(..., help="agent id，对应 agents/{agent}.yaml"),
    flows: str = typer.Option(
        "",
        "--flows",
        "-f", 
        help="用逗号分隔的flow名称；为空则使用agent的所有flows",
    ),
    infile: str = typer.Option(
        "",
        "--infile",
        "-i",
        help="输入测试集文件；为空则使用agent的default_testset",
    ),
    outfile: str = typer.Option(
        "",
        "--outfile", 
        "-o",
        help="输出文件名；为空则自动生成",
    ),
    judge: bool = typer.Option(
        False,
        "--judge",
        "-j",
        help="是否在执行完成后立即进行judge评估",
    ),
    limit: int = typer.Option(0, help="最多运行多少条（0=全部）"),
):
    """
    统一的评估执行工具：批量运行flow并可选择立即进行judge评估
    
    支持单个flow执行或多个flow对比执行，可选择是否立即进行LLM judge评估。
    """
    # 加载agent配置
    try:
        agent_cfg = load_agent(agent)
        console.rule(f"[bold blue]Eval Runner · Agent {agent_cfg.id}[/bold blue]")
        console.print(f"[bold]Agent[/]: {agent_cfg.name}")
        console.print(f"[dim]{agent_cfg.description}[/]")
    except FileNotFoundError as e:
        console.print(f"[red]错误：{e}[/]")
        available_agents = list_available_agents()
        if available_agents:
            console.print(f"[yellow]可用的 agents：{', '.join(available_agents)}[/]")
        raise typer.Exit(1)

    # 解析flows
    flow_list = []
    if flows:
        flow_list = [x.strip() for x in flows.split(",") if x.strip()]
        console.print(f"[bold]Flows[/]: {', '.join(flow_list)} (手动指定)")
    else:
        flow_list = [f.name for f in agent_cfg.flows]
        console.print(f"[bold]Flows[/]: {', '.join(flow_list)} (使用agent全部flows)")

    if not flow_list:
        console.print("[red]错误：没有可执行的flow。[/]")
        raise typer.Exit(1)

    # 解析测试集
    if not infile:
        infile = agent_cfg.default_testset
        console.print(f"[bold]Testset[/]: {infile} (使用agent默认测试集)")
    else:
        console.print(f"[bold]Testset[/]: {infile}")

    # 生成输出文件名
    if not outfile:
        outfile = generate_output_filename(agent_cfg.id, flow_list, judge)
        console.print(f"[bold]Output[/]: {outfile} (自动生成)")
    else:
        console.print(f"[bold]Output[/]: {outfile}")

    in_path = DATA_DIR / infile
    out_path = DATA_DIR / outfile

    # 检查输入文件
    if not in_path.exists():
        console.print(f"[red]错误：测试文件不存在：[/] {in_path}")
        console.print(f"[yellow]提示：agent '{agent_cfg.id}' 的可用测试集：{', '.join(agent_cfg.all_testsets)}[/]")
        raise typer.Exit(1)

    # 加载测试用例
    cases = load_test_cases(in_path)
    if limit > 0:
        cases = cases[:limit]

    if not cases:
        console.print("[yellow]没有测试用例可执行。[/]")
        raise typer.Exit()

    console.print(f"[bold]Cases[/]: {len(cases)} 条")
    if judge:
        console.print(f"[bold]Judge[/]: 启用 (将在执行完成后自动评估)")

    # 执行阶段
    console.rule("[bold green]执行阶段[/bold green]")
    
    rows: List[Dict[str, Any]] = []
    flow_token_stats = {flow: {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0} for flow in flow_list}
    
    for idx, case in enumerate(cases, start=1):
        _id = case.get("id", idx)
        variables = {k: v for k, v in case.items() if k != "id"}

        console.print(f"\n[{idx}/{len(cases)}] id={_id}")

        row: Dict[str, Any] = {"id": _id, **variables}

        # 执行每个flow
        for flow_name in flow_list:
            console.print(f"  -> Running flow: [cyan]{flow_name}[/cyan]")
            output, token_info = run_flow_with_tokens(flow_name, extra_vars=variables)
            
            # 保存结果
            if len(flow_list) == 1:
                # 单flow模式，直接用output列名
                row["output"] = output
                row["input_tokens"] = token_info.get("input_tokens", 0)
                row["output_tokens"] = token_info.get("output_tokens", 0)
                row["total_tokens"] = token_info.get("total_tokens", 0)
            else:
                # 多flow对比模式，用带前缀的列名
                row[f"output__{flow_name}"] = output
                row[f"input_tokens__{flow_name}"] = token_info.get("input_tokens", 0)
                row[f"output_tokens__{flow_name}"] = token_info.get("output_tokens", 0)
                row[f"total_tokens__{flow_name}"] = token_info.get("total_tokens", 0)
            
            # 累计统计
            for key in flow_token_stats[flow_name]:
                flow_token_stats[flow_name][key] += token_info.get(key, 0)
            
            # 显示预览
            output_preview = output[:150] + "..." if len(output) > 150 else output
            console.print(f"     Output: {output_preview}")
            console.print(f"     Tokens: {token_info.get('total_tokens', 0)}")

        rows.append(row)

    # 保存执行结果
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    console.print(f"[green]执行完成！结果已写入：[/] {out_path}")

    # 显示token统计
    console.rule("[bold cyan]Token 统计[/bold cyan]")
    if len(flow_list) == 1:
        # 单flow统计
        stats = flow_token_stats[flow_list[0]]
        avg_input = stats["input_tokens"] / len(rows) if rows else 0
        avg_output = stats["output_tokens"] / len(rows) if rows else 0
        avg_total = stats["total_tokens"] / len(rows) if rows else 0
        
        console.print(f"总输入 tokens: {stats['input_tokens']:,} (平均: {avg_input:.1f})")
        console.print(f"总输出 tokens: {stats['output_tokens']:,} (平均: {avg_output:.1f})")
        console.print(f"总计 tokens: {stats['total_tokens']:,} (平均: {avg_total:.1f})")
    else:
        # 多flow对比统计
        token_table = Table(title="Token Usage Comparison")
        token_table.add_column("Flow", style="bold")
        token_table.add_column("平均输入", justify="right")
        token_table.add_column("平均输出", justify="right") 
        token_table.add_column("平均总计", justify="right")
        
        for flow_name in flow_list:
            stats = flow_token_stats[flow_name]
            avg_input = stats["input_tokens"] / len(rows) if rows else 0
            avg_output = stats["output_tokens"] / len(rows) if rows else 0
            avg_total = stats["total_tokens"] / len(rows) if rows else 0
            token_table.add_row(
                flow_name,
                f"{avg_input:.1f}",
                f"{avg_output:.1f}",
                f"{avg_total:.1f}"
            )
        console.print(token_table)

    # Judge评估阶段
    if judge:
        console.rule("[bold magenta]Judge 评估阶段[/bold magenta]")
        
        # 获取judge配置
        eval_cfg = agent_cfg.evaluation or {}
        judge_agent_id = eval_cfg.get("judge_agent_id", "judge_default")
        judge_flow = eval_cfg.get("judge_flow", "judge_v1")
        
        try:
            judge_agent_cfg = load_agent(judge_agent_id)
            console.print(f"[bold]Judge Agent[/]: {judge_agent_cfg.name} ({judge_agent_id})")
            console.print(f"[bold]Judge Flow[/]: {judge_flow}")
        except FileNotFoundError:
            console.print(f"[red]Judge Agent 不存在: {judge_agent_id}[/red]")
            console.print("[yellow]跳过judge评估，仅保存执行结果。[/]")
            return

        # 构建judge chain
        judge_chain = build_judge_chain(
            task_agent_cfg=agent_cfg,
            judge_agent_cfg=judge_agent_cfg,
            judge_flow_name=judge_flow,
        )

        # 执行judge评估
        eval_rows: List[Dict[str, Any]] = []
        judge_total_tokens = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
        
        # 确定要评估的输出列
        if len(flow_list) == 1:
            output_cols = ["output"]
            flow_names = flow_list
        else:
            output_cols = [f"output__{flow}" for flow in flow_list]
            flow_names = flow_list

        for idx, row in enumerate(rows, start=1):
            console.print(f"[{idx}/{len(rows)}] Judge评估 id={row.get('id')}")
            
            case_base = {
                "id": row.get("id"),
                "input": row.get("input", ""),
                "context": row.get("context", ""),
                "expected": row.get("expected", ""),
            }
            
            for col, flow_name in zip(output_cols, flow_names):
                output = row.get(col, "")
                if not output:
                    continue
                
                console.print(f"  -> judging flow: [cyan]{flow_name}[/cyan]")
                judge_data, token_info = judge_one(
                    task_agent_cfg=agent_cfg,
                    flow_name=flow_name,
                    case=case_base,
                    output=output,
                    judge_chain=judge_chain,
                )
                
                # 累计token统计
                for key in judge_total_tokens:
                    judge_total_tokens[key] += token_info.get(key, 0)
                
                console.print(f"    score: {judge_data.get('overall_score')}, tokens: {token_info.get('total_tokens', 0)}")
                
                # 构建评估结果行
                flat: Dict[str, Any] = {
                    "id": case_base["id"],
                    "flow": flow_name,
                    "overall_score": judge_data.get("overall_score"),
                    "overall_comment": judge_data.get("overall_comment", ""),
                    "judge_input_tokens": token_info.get("input_tokens", 0),
                    "judge_output_tokens": token_info.get("output_tokens", 0),
                    "judge_total_tokens": token_info.get("total_tokens", 0),
                }
                
                # 展开详细评估结果
                for idx_check, check in enumerate(judge_data.get("must_have_check", [])):
                    flat[f"must_have_{idx_check+1}__satisfied"] = check.get("satisfied")
                    flat[f"must_have_{idx_check+1}__score"] = check.get("score")
                    flat[f"must_have_{idx_check+1}__comment"] = check.get("comment", "")
                
                for idx_check, check in enumerate(judge_data.get("nice_to_have_check", [])):
                    flat[f"nice_to_have_{idx_check+1}__satisfied"] = check.get("satisfied")
                    flat[f"nice_to_have_{idx_check+1}__score"] = check.get("score")
                    flat[f"nice_to_have_{idx_check+1}__comment"] = check.get("comment", "")
                
                # summary_quality_check 检查结果展开（如果存在）
                for idx_check, check in enumerate(judge_data.get("summary_quality_check", [])):
                    aspect = check.get("aspect", f"quality_{idx_check+1}")
                    flat[f"quality__{aspect}__satisfied"] = check.get("satisfied")
                    flat[f"quality__{aspect}__score"] = check.get("score")
                    flat[f"quality__{aspect}__comment"] = check.get("comment", "")
                
                eval_rows.append(flat)

        if eval_rows:
            # 保存judge结果到新文件
            eval_outfile = outfile.replace(".csv", ".judge.csv")
            eval_out_path = DATA_DIR / eval_outfile
            
            eval_fieldnames = sorted(eval_rows[0].keys(), key=lambda x: (x not in ["id", "flow"], x))
            with open(eval_out_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=eval_fieldnames)
                writer.writeheader()
                writer.writerows(eval_rows)
            
            console.print(f"[green]Judge评估完成！结果已写入：[/] {eval_out_path}")
            
            # 显示judge token统计
            console.print(f"\n[bold]Judge Token 统计：[/]")
            console.print(f"  输入 tokens: {judge_total_tokens['input_tokens']:,}")
            console.print(f"  输出 tokens: {judge_total_tokens['output_tokens']:,}")
            console.print(f"  总计 tokens: {judge_total_tokens['total_tokens']:,}")

    # 最终预览
    console.rule("[bold blue]结果预览[/bold blue]")
    preview_table = Table(title="Results Preview", show_lines=True)
    
    if len(flow_list) == 1:
        preview_cols = ["id", "input", "expected", "output", "total_tokens"]
    else:
        output_cols = [col for col in fieldnames if col.startswith("output__")]
        preview_cols = ["id"] + output_cols[:2]  # 只显示前两个flow的输出
    
    # 只显示存在的列
    preview_cols = [col for col in preview_cols if col in fieldnames]
    
    for col in preview_cols:
        preview_table.add_column(col, overflow="fold")
    
    for row in rows[:3]:
        preview_row = []
        for col in preview_cols:
            value = str(row.get(col, ""))
            if col.startswith("output"):
                value = value[:100] + "..." if len(value) > 100 else value
            preview_row.append(value)
        preview_table.add_row(*preview_row)
    
    console.print(preview_table)


if __name__ == "__main__":
    app()