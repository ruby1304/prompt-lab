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
from .paths import (
    DATA_DIR, agent_testset_dir, agent_runs_dir, agent_evals_dir,
    default_compare_outfile, default_batch_outfile, ensure_agent_dirs,
    timestamp_str
)
from .agent_registry import load_agent, list_available_agents
from .eval_llm_judge import build_judge_chain, judge_one
from .rule_engine import apply_rules as apply_rules_engine

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


def generate_output_filename(agent_id: str, flows: List[str], with_rules: bool, with_judge: bool) -> Path:
    """生成输出文件路径"""
    ts = timestamp_str()
    
    if len(flows) == 1:
        # 单flow模式
        flow_part = flows[0]
        filename = f"{ts}_batch_{flow_part}.csv"
    else:
        # 多flow对比模式
        flows_str = "_".join(flows)
        filename = f"{ts}_compare_{flows_str}.csv"
    
    return agent_runs_dir(agent_id) / filename


def apply_rules_to_outputs(agent_cfg, rows: List[Dict[str, Any]], flow_list: List[str]) -> List[Dict[str, Any]]:
    """对输出结果应用规则评估"""
    eval_cfg = agent_cfg.evaluation or {}
    rules = eval_cfg.get("rules", []) or []
    
    if not rules:
        # 没有规则配置，添加默认通过的规则字段
        for row in rows:
            if len(flow_list) == 1:
                row["rule_pass"] = 1
                row["rule_violations"] = ""
            else:
                for flow_name in flow_list:
                    row[f"rule_pass__{flow_name}"] = 1
                    row[f"rule_violations__{flow_name}"] = ""
        return rows
    
    # 应用规则评估
    result_rows = []
    for row in rows:
        result = dict(row)
        
        if len(flow_list) == 1:
            # 单flow模式
            output_text = (row.get("output") or "").strip()
            rule_result = apply_rules_engine(rules, output_text)
            result.update(rule_result)
        else:
            # 多flow对比模式
            for flow_name in flow_list:
                output_col = f"output__{flow_name}"
                output_text = (row.get(output_col) or "").strip()
                
                # 创建临时行用于规则评估
                temp_row = {"output": output_text}
                rule_result = apply_rules_engine(rules, output_text)
                
                result[f"rule_pass__{flow_name}"] = rule_result["rule_pass"]
                result[f"rule_violations__{flow_name}"] = rule_result["rule_violations"]
        
        result_rows.append(result)
    
    return result_rows


def print_rule_stats(rows: List[Dict[str, Any]], flow_list: List[str], console: Console):
    """打印规则评估统计"""
    console.rule("[bold yellow]规则评估统计[/bold yellow]")
    
    if len(flow_list) == 1:
        # 单flow统计
        total = len(rows)
        passed = sum(1 for r in rows if r.get("rule_pass") == 1)
        failed = total - passed
        
        console.print(f"总样本: {total}, 通过: {passed} ({passed/total*100:.1f}%), 失败: {failed} ({failed/total*100:.1f}%)")
        
        if failed > 0:
            violation_counts = {}
            for r in rows:
                if r.get("rule_pass") == 0:
                    violations = r.get("rule_violations", "").split(",")
                    for v in violations:
                        if v.strip():
                            violation_counts[v.strip()] = violation_counts.get(v.strip(), 0) + 1
            
            if violation_counts:
                console.print("\n违规统计:")
                for rule_id, count in sorted(violation_counts.items(), key=lambda x: x[1], reverse=True):
                    console.print(f"  {rule_id}: {count} 次")
    else:
        # 多flow统计
        rule_table = Table(title="Rule Evaluation by Flow")
        rule_table.add_column("Flow", style="bold")
        rule_table.add_column("Total", justify="right")
        rule_table.add_column("Passed", justify="right")
        rule_table.add_column("Failed", justify="right")
        rule_table.add_column("Pass Rate", justify="right")
        
        for flow_name in flow_list:
            pass_field = f"rule_pass__{flow_name}"
            total = len(rows)
            passed = sum(1 for r in rows if r.get(pass_field) == 1)
            failed = total - passed
            pass_rate = f"{passed/total*100:.1f}%" if total > 0 else "0%"
            
            rule_table.add_row(
                flow_name,
                str(total),
                str(passed),
                str(failed),
                pass_rate
            )
        
        console.print(rule_table)


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
    rules: bool = typer.Option(
        False,
        "--rules",
        "-r",
        help="是否进行规则评估",
    ),
    judge: bool = typer.Option(
        False,
        "--judge",
        "-j",
        help="是否进行LLM judge评估（会自动启用规则评估）",
    ),
    limit: int = typer.Option(0, help="最多运行多少条（0=全部）"),
):
    """
    统一的评估执行工具：批量运行flow并可选择进行规则评估和LLM judge评估
    
    支持三种评估模式：
    1. 仅执行：不加任何评估参数
    2. 规则评估：--rules
    3. 规则+模型评估：--judge（会自动启用规则评估）
    
    支持单个flow执行或多个flow对比执行。
    """
    # 参数逻辑处理
    if judge:
        rules = True  # judge模式自动启用规则评估
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

    # 确保agent目录存在
    ensure_agent_dirs(agent_cfg.id)
    
    # 解析测试集
    if not infile:
        infile = agent_cfg.default_testset
        in_path = agent_testset_dir(agent_cfg.id) / infile
        console.print(f"[bold]Testset[/]: {infile} (使用agent默认测试集)")
    else:
        # 如果是绝对路径，直接使用；否则在testset目录下查找
        if Path(infile).is_absolute():
            in_path = Path(infile)
        else:
            in_path = agent_testset_dir(agent_cfg.id) / infile
        console.print(f"[bold]Testset[/]: {infile}")

    # 生成输出文件路径
    if not outfile:
        out_path = generate_output_filename(agent_cfg.id, flow_list, rules, judge)
        console.print(f"[bold]Output[/]: {out_path.name} (自动生成)")
    else:
        # 如果是绝对路径，直接使用；否则在runs目录下
        if Path(outfile).is_absolute():
            out_path = Path(outfile)
        else:
            out_path = agent_runs_dir(agent_cfg.id) / outfile
        console.print(f"[bold]Output[/]: {outfile}")

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
    
    # 检查是否有规则配置
    rules = agent_cfg.evaluation.get("rules", []) or [] if agent_cfg.evaluation else []
    
    # 显示评估模式
    eval_modes = []
    if rules and not judge:
        eval_modes.append("规则评估")
    if judge and rules:
        eval_modes.append("规则+模型评估")
    elif judge:
        eval_modes.append("模型评估")
    
    if eval_modes:
        console.print(f"[bold]Evaluation[/]: {' + '.join(eval_modes)}")
    else:
        console.print(f"[bold]Evaluation[/]: 仅执行（无评估）")

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

    # 规则评估阶段
    if rules:
        console.rule("[bold yellow]规则评估阶段[/bold yellow]")
        
        # 检查规则配置
        eval_cfg = agent_cfg.evaluation or {}
        rule_configs = eval_cfg.get("rules", []) or []
        
        if not rule_configs:
            console.print("[yellow]该 agent 没有配置规则，将跳过规则评估[/]")
        else:
            console.print(f"[blue]应用 {len(rule_configs)} 条规则：[/]")
            for rule in rule_configs:
                console.print(f"  - {rule.get('id', 'unknown')}: {rule.get('kind', 'unknown')}")
        
        # 应用规则评估
        rows = apply_rules_to_outputs(agent_cfg, rows, flow_list)
        
        # 显示规则统计
        if rule_configs:
            print_rule_stats(rows, flow_list, console)

    # 保存执行结果（包含规则评估结果）
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
        # 在judge评估之前显示执行结果预览
        console.rule("[bold blue]执行结果预览[/bold blue]")
        show_execution_results_preview(rows, flow_list)
        
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
            eval_out_path = agent_evals_dir(agent_cfg.id) / "llm" / f"{out_path.stem}.judge.csv"
            
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
    
    # 根据不同情况显示不同的预览内容
    if judge and eval_rows:
        # 有judge评估结果时，显示评估结果预览
        show_judge_preview(eval_rows, flow_list)
    elif rules and len(flow_list) > 1:
        # 多flow对比 + 规则评估
        show_compare_with_rules_preview(rows, flow_list, fieldnames)
    elif rules and len(flow_list) == 1:
        # 单flow + 规则评估
        show_single_with_rules_preview(rows, fieldnames)
    elif len(flow_list) > 1:
        # 多flow对比，无评估
        show_compare_preview(rows, flow_list, fieldnames)
    else:
        # 单flow，无评估
        show_single_preview(rows, fieldnames)


def show_execution_results_preview(rows: List[Dict[str, Any]], flow_list: List[str]):
    """显示执行结果完整输出"""
    if len(flow_list) == 1:
        # 单flow完整输出
        preview_table = Table(title="Execution Results", show_lines=True)
        preview_table.add_column("ID", style="bold")
        preview_table.add_column("Output", overflow="fold")
        preview_table.add_column("Tokens", justify="right")
        
        for row in rows[:3]:
            output = str(row.get("output", ""))
            tokens = str(row.get("total_tokens", ""))
            
            preview_table.add_row(
                str(row.get("id", "")),
                output,  # 显示完整输出，不截断
                tokens
            )
    else:
        # 多flow对比完整输出
        preview_table = Table(title="Execution Results", show_lines=True)
        preview_table.add_column("ID", style="bold")
        
        # 显示前两个flow的输出
        for flow in flow_list[:2]:
            preview_table.add_column(f"{flow}", overflow="fold")
        
        for row in rows[:3]:
            preview_row = [str(row.get("id", ""))]
            
            for flow in flow_list[:2]:
                output = str(row.get(f"output__{flow}", ""))
                preview_row.append(output)  # 显示完整输出，不截断
            
            preview_table.add_row(*preview_row)
    
    console.print(preview_table)


def show_judge_preview(eval_rows: List[Dict[str, Any]], flow_list: List[str]):
    """显示judge评估结果统计"""
    console.rule("[bold cyan]Judge 评估统计[/bold cyan]")
    if len(flow_list) > 1:
        show_judge_stats_by_flow(eval_rows, flow_list)
    else:
        show_judge_stats_single(eval_rows)


def show_judge_stats_by_flow(eval_rows: List[Dict[str, Any]], flow_list: List[str]):
    """显示按flow分组的judge统计"""
    stats_table = Table(title="Judge Stats by Flow")
    stats_table.add_column("Flow", style="bold")
    stats_table.add_column("样本数", justify="right")
    stats_table.add_column("平均分", justify="right")
    stats_table.add_column("分数范围", justify="center")
    stats_table.add_column("Must-Have通过率", justify="right")
    stats_table.add_column("分数分布", justify="center")
    
    for flow in flow_list:
        flow_rows = [r for r in eval_rows if r.get("flow") == flow]
        if not flow_rows:
            continue
            
        # 计算平均分
        scores = [r.get("overall_score", 0) for r in flow_rows if isinstance(r.get("overall_score"), (int, float))]
        avg_score = sum(scores) / len(scores) if scores else 0
        min_score = min(scores) if scores else 0
        max_score = max(scores) if scores else 0
        
        # 计算分数分布
        excellent = sum(1 for s in scores if s >= 8)
        good = sum(1 for s in scores if 6 <= s < 8)
        poor = sum(1 for s in scores if s < 6)
        total = len(scores)
        
        # 计算must-have通过率
        must_have_total = 0
        must_have_passed = 0
        for row in flow_rows:
            must_have_cols = [col for col in row.keys() if col.startswith("must_have_") and col.endswith("__satisfied")]
            for col in must_have_cols:
                must_have_total += 1
                if row.get(col) == True:
                    must_have_passed += 1
        
        must_have_rate = f"{must_have_passed/must_have_total*100:.1f}%" if must_have_total > 0 else "N/A"
        
        # 颜色标记
        if avg_score >= 8:
            avg_score_str = f"[green]{avg_score:.1f}[/green]"
        elif avg_score >= 6:
            avg_score_str = f"[yellow]{avg_score:.1f}[/yellow]"
        else:
            avg_score_str = f"[red]{avg_score:.1f}[/red]"
        
        # 分数分布显示
        distribution = f"优{excellent}/良{good}/差{poor}"
        
        stats_table.add_row(
            flow,
            str(total),
            avg_score_str,
            f"{min_score:.1f}-{max_score:.1f}",
            must_have_rate,
            distribution
        )
    
    console.print(stats_table)


def show_judge_stats_single(eval_rows: List[Dict[str, Any]]):
    """显示单flow的judge统计"""
    scores = [r.get("overall_score", 0) for r in eval_rows if isinstance(r.get("overall_score"), (int, float))]
    if scores:
        avg_score = sum(scores) / len(scores)
        min_score = min(scores)
        max_score = max(scores)
        
        # 计算分数分布
        excellent = sum(1 for s in scores if s >= 8)
        good = sum(1 for s in scores if 6 <= s < 8)
        poor = sum(1 for s in scores if s < 6)
        total = len(scores)
        
        # 计算Must-Have通过率
        must_have_total = 0
        must_have_passed = 0
        for row in eval_rows:
            must_have_cols = [col for col in row.keys() if col.startswith("must_have_") and col.endswith("__satisfied")]
            for col in must_have_cols:
                must_have_total += 1
                if row.get(col) == True:
                    must_have_passed += 1
        
        must_have_rate = f"{must_have_passed/must_have_total*100:.1f}%" if must_have_total > 0 else "N/A"
        
        console.print(f"[bold]总体统计[/]: 样本数 {total}, 平均分 {avg_score:.1f}, 范围 {min_score:.1f}-{max_score:.1f}")
        console.print(f"[bold]分数分布[/]: 优秀(≥8分) {excellent}个, 良好(6-8分) {good}个, 待改进(<6分) {poor}个")
        console.print(f"[bold]Must-Have通过率[/]: {must_have_rate} ({must_have_passed}/{must_have_total})")


def show_compare_with_rules_preview(rows: List[Dict[str, Any]], flow_list: List[str], fieldnames: List[str]):
    """显示多flow对比+规则评估预览"""
    preview_table = Table(title="Compare Results with Rules Preview", show_lines=True)
    preview_table.add_column("ID", style="bold")
    
    # 为每个flow添加输出和规则结果列
    for flow in flow_list[:2]:  # 只显示前两个flow
        preview_table.add_column(f"{flow}\nOutput", overflow="fold")
        preview_table.add_column(f"{flow}\nRule", justify="center")
    
    for row in rows[:3]:
        preview_row = [str(row.get("id", ""))]
        
        for flow in flow_list[:2]:
            # 输出预览
            output = str(row.get(f"output__{flow}", ""))
            output_preview = output[:60] + "..." if len(output) > 60 else output
            preview_row.append(output_preview)
            
            # 规则结果
            rule_pass = row.get(f"rule_pass__{flow}", 1)
            if rule_pass == 1:
                rule_status = "[green]✓[/green]"
            else:
                violations = row.get(f"rule_violations__{flow}", "")
                rule_status = f"[red]✗[/red]\n{violations[:20]}..."
            preview_row.append(rule_status)
        
        preview_table.add_row(*preview_row)
    
    console.print(preview_table)
    
    # 显示规则统计
    show_rules_stats_compare(rows, flow_list)


def show_rules_stats_compare(rows: List[Dict[str, Any]], flow_list: List[str]):
    """显示对比模式的规则统计"""
    stats_table = Table(title="Rules Stats by Flow")
    stats_table.add_column("Flow", style="bold")
    stats_table.add_column("Pass Rate", justify="right")
    stats_table.add_column("Failed Cases", justify="right")
    stats_table.add_column("Top Violations", overflow="fold")
    
    for flow in flow_list:
        total = len(rows)
        passed = sum(1 for r in rows if r.get(f"rule_pass__{flow}", 1) == 1)
        failed = total - passed
        pass_rate = f"{passed/total*100:.1f}%" if total > 0 else "0%"
        
        # 统计违规类型
        violation_counts = {}
        for row in rows:
            if row.get(f"rule_pass__{flow}", 1) == 0:
                violations = row.get(f"rule_violations__{flow}", "").split(",")
                for v in violations:
                    v = v.strip()
                    if v:
                        violation_counts[v] = violation_counts.get(v, 0) + 1
        
        top_violations = sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)[:2]
        violation_str = ", ".join(f"{k}({v})" for k, v in top_violations)
        
        # 颜色标记
        if passed == total:
            pass_rate_str = f"[green]{pass_rate}[/green]"
        elif failed > total * 0.5:
            pass_rate_str = f"[red]{pass_rate}[/red]"
        else:
            pass_rate_str = f"[yellow]{pass_rate}[/yellow]"
        
        stats_table.add_row(flow, pass_rate_str, str(failed), violation_str)
    
    console.print(stats_table)


def show_single_with_rules_preview(rows: List[Dict[str, Any]], fieldnames: List[str]):
    """显示单flow+规则评估预览"""
    preview_table = Table(title="Single Flow with Rules Preview", show_lines=True)
    preview_table.add_column("ID", style="bold")
    preview_table.add_column("Output", overflow="fold")
    preview_table.add_column("Rule Status", justify="center")
    preview_table.add_column("Violations", overflow="fold")
    
    for row in rows[:3]:
        output = str(row.get("output", ""))
        output_preview = output[:80] + "..." if len(output) > 80 else output
        
        rule_pass = row.get("rule_pass", 1)
        if rule_pass == 1:
            rule_status = "[green]✓ Pass[/green]"
            violations = ""
        else:
            rule_status = "[red]✗ Fail[/red]"
            violations = str(row.get("rule_violations", ""))[:40] + "..."
        
        preview_table.add_row(
            str(row.get("id", "")),
            output_preview,
            rule_status,
            violations
        )
    
    console.print(preview_table)
    
    # 显示规则统计
    total = len(rows)
    passed = sum(1 for r in rows if r.get("rule_pass", 1) == 1)
    failed = total - passed
    pass_rate = f"{passed/total*100:.1f}%" if total > 0 else "0%"
    
    if passed == total:
        status_str = f"[green]全部通过 ({pass_rate})[/green]"
    elif failed > total * 0.5:
        status_str = f"[red]大量失败 ({pass_rate} 通过)[/red]"
    else:
        status_str = f"[yellow]部分失败 ({pass_rate} 通过)[/yellow]"
    
    console.print(f"[bold]规则评估统计[/]: {status_str}, 失败 {failed} 条")


def show_compare_preview(rows: List[Dict[str, Any]], flow_list: List[str], fieldnames: List[str]):
    """显示多flow对比预览（无评估）"""
    preview_table = Table(title="Compare Results Preview", show_lines=True)
    preview_table.add_column("ID", style="bold")
    
    # 显示前两个flow的输出
    for flow in flow_list[:2]:
        preview_table.add_column(f"{flow}", overflow="fold")
    
    for row in rows[:3]:
        preview_row = [str(row.get("id", ""))]
        
        for flow in flow_list[:2]:
            output = str(row.get(f"output__{flow}", ""))
            output_preview = output[:80] + "..." if len(output) > 80 else output
            preview_row.append(output_preview)
        
        preview_table.add_row(*preview_row)
    
    console.print(preview_table)


def show_single_preview(rows: List[Dict[str, Any]], fieldnames: List[str]):
    """显示单flow预览（无评估）"""
    preview_table = Table(title="Single Flow Results Preview", show_lines=True)
    preview_table.add_column("ID", style="bold")
    preview_table.add_column("Output", overflow="fold")
    preview_table.add_column("Tokens", justify="right")
    
    for row in rows[:3]:
        output = str(row.get("output", ""))
        output_preview = output[:100] + "..." if len(output) > 100 else output
        tokens = str(row.get("total_tokens", ""))
        
        preview_table.add_row(
            str(row.get("id", "")),
            output_preview,
            tokens
        )
    
    console.print(preview_table)


def apply_rules_to_outputs(agent_cfg, rows: List[Dict[str, Any]], flow_list: List[str]) -> List[Dict[str, Any]]:
    """对输出应用规则评估"""
    from .rule_engine import apply_rules as apply_rules_engine
    
    eval_cfg = agent_cfg.evaluation or {}
    rules = eval_cfg.get("rules", []) or []
    
    if not rules:
        return rows
    
    for row in rows:
        if len(flow_list) == 1:
            # 单flow模式
            output_text = (row.get("output") or "").strip()
            rule_result = apply_rules_engine(rules, output_text)
            row.update(rule_result)
        else:
            # 多flow对比模式，为每个flow分别评估
            for flow_name in flow_list:
                output_text = (row.get(f"output__{flow_name}") or "").strip()
                rule_result = apply_rules_engine(rules, output_text)
                row[f"rule_pass__{flow_name}"] = rule_result["rule_pass"]
                row[f"rule_violations__{flow_name}"] = rule_result["rule_violations"]
    
    return rows


def print_rule_stats(rows: List[Dict[str, Any]], flow_list: List[str], console):
    """打印规则评估统计"""
    if len(flow_list) == 1:
        # 单flow统计
        total = len(rows)
        passed = sum(1 for r in rows if r.get("rule_pass", 1) == 1)
        failed = total - passed
        pass_rate = f"{passed/total*100:.1f}%" if total > 0 else "0%"
        
        if passed == total:
            status_str = f"[green]全部通过 ({pass_rate})[/green]"
        elif failed > total * 0.5:
            status_str = f"[red]大量失败 ({pass_rate} 通过)[/red]"
        else:
            status_str = f"[yellow]部分失败 ({pass_rate} 通过)[/yellow]"
        
        console.print(f"[bold]规则评估统计[/]: {status_str}, 失败 {failed} 条")
        
        # 显示违规统计
        if failed > 0:
            violation_counts = {}
            for row in rows:
                if row.get("rule_pass", 1) == 0:
                    violations = row.get("rule_violations", "").split(",")
                    for v in violations:
                        v = v.strip()
                        if v:
                            violation_counts[v] = violation_counts.get(v, 0) + 1
            
            if violation_counts:
                console.print("[bold]违规类型统计：[/]")
                for rule_id, count in sorted(violation_counts.items(), key=lambda x: x[1], reverse=True):
                    console.print(f"  {rule_id}: {count} 次")
    else:
        # 多flow对比统计
        stats_table = Table(title="Rules Stats by Flow")
        stats_table.add_column("Flow", style="bold")
        stats_table.add_column("Pass Rate", justify="right")
        stats_table.add_column("Failed", justify="right")
        stats_table.add_column("Top Violations", overflow="fold")
        
        for flow in flow_list:
            total = len(rows)
            passed = sum(1 for r in rows if r.get(f"rule_pass__{flow}", 1) == 1)
            failed = total - passed
            pass_rate = f"{passed/total*100:.1f}%" if total > 0 else "0%"
            
            # 统计违规类型
            violation_counts = {}
            for row in rows:
                if row.get(f"rule_pass__{flow}", 1) == 0:
                    violations = row.get(f"rule_violations__{flow}", "").split(",")
                    for v in violations:
                        v = v.strip()
                        if v:
                            violation_counts[v] = violation_counts.get(v, 0) + 1
            
            top_violations = sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)[:2]
            violation_str = ", ".join(f"{k}({v})" for k, v in top_violations)
            
            # 颜色标记
            if passed == total:
                pass_rate_str = f"[green]{pass_rate}[/green]"
            elif failed > total * 0.5:
                pass_rate_str = f"[red]{pass_rate}[/red]"
            else:
                pass_rate_str = f"[yellow]{pass_rate}[/yellow]"
            
            stats_table.add_row(flow, pass_rate_str, str(failed), violation_str)
        
        console.print(stats_table)


if __name__ == "__main__":
    app()