#!/usr/bin/env python3
"""
规则评估脚本：对输出应用预定义规则，快速过滤 bad case
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Any, List

import typer
from rich.console import Console
from rich.table import Table

from .agent_registry import load_agent
from .rule_engine import apply_rules as apply_rules_engine, get_supported_rule_types, validate_rule

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

app = typer.Typer()
console = Console()


def apply_rules_to_row(agent_cfg, row: Dict[str, Any], output_field: str = "output") -> Dict[str, Any]:
    """对单行数据应用规则"""
    eval_cfg = agent_cfg.evaluation or {}
    rules = eval_cfg.get("rules", []) or []
    
    output_text = (row.get(output_field) or "").strip()
    
    # 使用规则引擎处理
    rule_result = apply_rules_engine(rules, output_text)
    
    # 返回带规则结果的行
    result = dict(row)
    result.update(rule_result)
    return result


@app.command()
def run(
    agent: str = typer.Option(..., help="agent id"),
    infile: str = typer.Option(..., help="输入结果文件，如 mem0_l1.compare.csv"),
    outfile: str = typer.Option("with_rules.csv", help="输出带规则结果的文件"),
    mode: str = typer.Option("compare", help="处理模式：compare（对比结果）或 manual（人工评审表）"),
):
    """对结果文件应用规则评估"""
    try:
        agent_cfg = load_agent(agent)
    except FileNotFoundError:
        console.print(f"[red]Agent 不存在: {agent}[/]")
        raise typer.Exit(1)
    
    in_path = DATA_DIR / infile
    out_path = DATA_DIR / outfile

    console.print(f"[bold]Agent[/]: {agent_cfg.id} - {agent_cfg.name}")
    console.print(f"[bold]Input[/]: {in_path}")
    console.print(f"[bold]Output[/]: {out_path}")
    console.print(f"[bold]Mode[/]: {mode}")

    if not in_path.exists():
        console.print(f"[red]输入文件不存在: {in_path}[/]")
        raise typer.Exit(1)

    # 检查规则配置
    rules = agent_cfg.evaluation.get("rules", []) or []
    if not rules:
        console.print("[yellow]该 agent 没有配置规则，将直接复制文件[/]")
    else:
        console.print(f"[blue]发现 {len(rules)} 条规则：[/]")
        for rule in rules:
            console.print(f"  - {rule.get('id', 'unknown')}: {rule.get('kind', 'unknown')}")

    # 读取数据
    with open(in_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        console.print("[yellow]没有数据可评估[/]")
        raise typer.Exit()

    # 根据模式处理数据
    if mode == "compare":
        # 处理 compare 结果：需要为每个 output__ 列分别评估
        flow_cols = [c for c in rows[0].keys() if c.startswith("output__")]
        if not flow_cols:
            console.print("[red]找不到 output__ 开头的列，这不是 compare 结果文件[/]")
            raise typer.Exit(1)
        
        console.print(f"[blue]发现 {len(flow_cols)} 个 flow 输出列[/]")
        
        # 为每个 flow 添加规则评估结果
        out_rows = []
        for row in rows:
            result = dict(row)
            
            # 为每个 flow 评估规则
            for flow_col in flow_cols:
                flow_name = flow_col.replace("output__", "")
                
                if rules:
                    # 创建临时行用于规则评估
                    temp_row = {"output": row.get(flow_col, "")}
                    rule_result = apply_rules_to_row(agent_cfg, temp_row)
                    
                    result[f"rule_pass__{flow_name}"] = rule_result["rule_pass"]
                    result[f"rule_violations__{flow_name}"] = rule_result["rule_violations"]
                else:
                    result[f"rule_pass__{flow_name}"] = 1
                    result[f"rule_violations__{flow_name}"] = ""
            
            out_rows.append(result)
        
        # 添加新的字段名
        new_fields = []
        for flow_col in flow_cols:
            flow_name = flow_col.replace("output__", "")
            new_fields.extend([f"rule_pass__{flow_name}", f"rule_violations__{flow_name}"])
        
        fieldnames = list(rows[0].keys()) + new_fields
        
    else:
        # 处理 manual 模式：直接对 output 列评估
        out_rows = []
        for row in rows:
            if rules:
                out_rows.append(apply_rules_to_row(agent_cfg, row))
            else:
                result = dict(row)
                result["rule_pass"] = 1
                result["rule_violations"] = ""
                out_rows.append(result)
        
        fieldnames = list(rows[0].keys()) + ["rule_pass", "rule_violations"]

    # 写入结果
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    # 统计结果
    if rules:
        if mode == "compare":
            # 统计每个 flow 的规则通过情况
            flow_stats = {}
            for flow_col in flow_cols:
                flow_name = flow_col.replace("output__", "")
                pass_field = f"rule_pass__{flow_name}"
                violation_field = f"rule_violations__{flow_name}"
                
                total = len(out_rows)
                passed = sum(1 for r in out_rows if r.get(pass_field) == 1)
                failed = total - passed
                
                flow_stats[flow_name] = {"total": total, "passed": passed, "failed": failed}
                
                # 统计违规类型
                violation_counts = {}
                for r in out_rows:
                    if r.get(pass_field) == 0:
                        violations = r.get(violation_field, "").split(",")
                        for v in violations:
                            if v.strip():
                                violation_counts[v.strip()] = violation_counts.get(v.strip(), 0) + 1
                
                flow_stats[flow_name]["violations"] = violation_counts
            
            console.print(f"[green]规则评估完成[/]")
            for flow_name, stats in flow_stats.items():
                console.print(f"\n[bold]{flow_name}[/]:")
                console.print(f"  总样本: {stats['total']}, 通过: {stats['passed']} ({stats['passed']/stats['total']*100:.1f}%), 失败: {stats['failed']} ({stats['failed']/stats['total']*100:.1f}%)")
                
                if stats["violations"]:
                    console.print("  违规统计:")
                    for rule_id, count in sorted(stats["violations"].items(), key=lambda x: x[1], reverse=True):
                        console.print(f"    {rule_id}: {count} 次")
        else:
            # manual 模式的统计
            total = len(out_rows)
            passed = sum(1 for r in out_rows if r["rule_pass"] == 1)
            failed = total - passed
            
            console.print(f"[green]规则评估完成[/]")
            console.print(f"总样本: {total}, 通过: {passed} ({passed/total*100:.1f}%), 失败: {failed} ({failed/total*100:.1f}%)")
            
            if failed > 0:
                violation_counts = {}
                for r in out_rows:
                    if r["rule_pass"] == 0:
                        violations = r["rule_violations"].split(",")
                        for v in violations:
                            if v.strip():
                                violation_counts[v.strip()] = violation_counts.get(v.strip(), 0) + 1
                
                console.print("\n[bold]违规统计：[/]")
                for rule_id, count in sorted(violation_counts.items(), key=lambda x: x[1], reverse=True):
                    console.print(f"  {rule_id}: {count} 次")
    else:
        console.print(f"[green]文件已复制，共 {len(out_rows)} 条记录[/]")


@app.command()
def stats(
    infile: str = typer.Option(..., help="带规则结果的文件，如 mem0_l1.with_rules.csv"),
):
    """统计规则评估结果"""
    in_path = DATA_DIR / infile
    
    if not in_path.exists():
        console.print(f"[red]文件不存在: {in_path}[/]")
        raise typer.Exit(1)

    with open(in_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        console.print("[yellow]没有数据可统计[/]")
        raise typer.Exit()

    # 检查是否有规则结果列
    has_rule_results = "rule_pass" in rows[0] or any(col.startswith("rule_pass__") for col in rows[0].keys())
    if not has_rule_results:
        console.print("[red]文件中没有规则结果，请先运行 eval_rules run[/]")
        raise typer.Exit(1)

    # 检查是否是 compare 模式的结果（有 rule_pass__flow_name 列）
    compare_mode = any(col.startswith("rule_pass__") for col in rows[0].keys())
    
    if compare_mode:
        # Compare 模式：统计每个 flow 的规则结果
        flow_cols = [col for col in rows[0].keys() if col.startswith("rule_pass__")]
        flow_stats = {}
        overall_stats = {"total": 0, "passed": 0, "failed": 0, "violations": {}}
        
        for flow_col in flow_cols:
            flow_name = flow_col.replace("rule_pass__", "")
            violation_col = f"rule_violations__{flow_name}"
            
            flow_stats[flow_name] = {"total": 0, "passed": 0, "failed": 0, "violations": {}}
            
            for row in rows:
                rule_pass = int(row.get(flow_col, 1))
                violations = row.get(violation_col, "").strip()
                
                flow_stats[flow_name]["total"] += 1
                overall_stats["total"] += 1
                
                if rule_pass:
                    flow_stats[flow_name]["passed"] += 1
                    overall_stats["passed"] += 1
                else:
                    flow_stats[flow_name]["failed"] += 1
                    overall_stats["failed"] += 1
                    
                    # 统计违规类型
                    if violations:
                        for v in violations.split(","):
                            v = v.strip()
                            if v:
                                flow_stats[flow_name]["violations"][v] = flow_stats[flow_name]["violations"].get(v, 0) + 1
                                overall_stats["violations"][v] = overall_stats["violations"].get(v, 0) + 1
    else:
        # Manual 模式：按 flow 列统计
        flow_stats = {}
        overall_stats = {"total": 0, "passed": 0, "failed": 0, "violations": {}}
        
        for row in rows:
            flow = row.get("flow", "unknown")
            rule_pass = int(row.get("rule_pass", 1))
            violations = row.get("rule_violations", "").strip()
            
            # 初始化 flow 统计
            if flow not in flow_stats:
                flow_stats[flow] = {"total": 0, "passed": 0, "failed": 0, "violations": {}}
            
            # 更新统计
            flow_stats[flow]["total"] += 1
            overall_stats["total"] += 1
            
            if rule_pass:
                flow_stats[flow]["passed"] += 1
                overall_stats["passed"] += 1
            else:
                flow_stats[flow]["failed"] += 1
                overall_stats["failed"] += 1
                
                # 统计违规类型
                if violations:
                    for v in violations.split(","):
                        v = v.strip()
                        if v:
                            flow_stats[flow]["violations"][v] = flow_stats[flow]["violations"].get(v, 0) + 1
                            overall_stats["violations"][v] = overall_stats["violations"].get(v, 0) + 1

    # 显示结果
    if len(flow_stats) > 1:
        # 按 flow 显示
        table = Table(title="Rule Evaluation Stats by Flow", show_lines=True)
        table.add_column("Flow", style="bold")
        table.add_column("Total", justify="right")
        table.add_column("Passed", justify="right")
        table.add_column("Failed", justify="right")
        table.add_column("Pass Rate", justify="right")
        table.add_column("Top Violations", overflow="fold")
        
        for flow, stats in sorted(flow_stats.items()):
            pass_rate = f"{stats['passed']/stats['total']*100:.1f}%" if stats['total'] > 0 else "0%"
            
            # 取前3个最常见的违规
            top_violations = sorted(stats["violations"].items(), key=lambda x: x[1], reverse=True)[:3]
            violation_str = ", ".join(f"{k}({v})" for k, v in top_violations)
            
            table.add_row(
                flow,
                str(stats["total"]),
                str(stats["passed"]),
                str(stats["failed"]),
                pass_rate,
                violation_str
            )
        
        console.print(table)
    
    # 整体统计
    console.print(f"\n[bold]整体统计：[/]")
    console.print(f"总样本: {overall_stats['total']}")
    console.print(f"通过: {overall_stats['passed']} ({overall_stats['passed']/overall_stats['total']*100:.1f}%)")
    console.print(f"失败: {overall_stats['failed']} ({overall_stats['failed']/overall_stats['total']*100:.1f}%)")
    
    if overall_stats["violations"]:
        console.print(f"\n[bold]违规类型统计：[/]")
        for rule_id, count in sorted(overall_stats["violations"].items(), key=lambda x: x[1], reverse=True):
            pct = count / overall_stats["total"] * 100
            console.print(f"  {rule_id}: {count} 次 ({pct:.1f}%)")


@app.command()
def list_rules():
    """列出所有支持的规则类型"""
    from .rule_engine import get_rule_info
    
    rule_info = get_rule_info()
    
    console.print("[bold]支持的规则类型：[/]\n")
    
    for rule_type, info in rule_info.items():
        console.print(f"[bold cyan]{rule_type}[/]: {info['description']}")
        
        if info['required_params']:
            console.print(f"  [yellow]必需参数[/]: {', '.join(info['required_params'])}")
        
        if info['optional_params']:
            console.print(f"  [green]可选参数[/]: {', '.join(info['optional_params'])}")
        
        console.print("  [dim]示例配置[/]:")
        example = info['example']
        for key, value in example.items():
            if isinstance(value, list):
                value_str = f"[{', '.join(map(str, value))}]"
            else:
                value_str = str(value)
            console.print(f"    {key}: {value_str}")
        
        console.print()


@app.command()
def validate(
    agent: str = typer.Option(..., help="要验证规则的 agent id"),
):
    """验证 agent 的规则配置"""
    try:
        agent_cfg = load_agent(agent)
    except FileNotFoundError:
        console.print(f"[red]Agent 不存在: {agent}[/]")
        raise typer.Exit(1)
    
    rules = agent_cfg.evaluation.get("rules", []) or []
    
    if not rules:
        console.print(f"[yellow]Agent {agent} 没有配置规则[/]")
        return
    
    console.print(f"[bold]验证 Agent {agent} 的规则配置：[/]\n")
    
    all_valid = True
    for i, rule in enumerate(rules, 1):
        rule_id = rule.get("id", f"rule_{i}")
        console.print(f"[bold]规则 {i}: {rule_id}[/]")
        
        errors = validate_rule(rule)
        if errors:
            all_valid = False
            for error in errors:
                console.print(f"  [red]✗ {error}[/]")
        else:
            console.print(f"  [green]✓ 配置正确[/]")
        
        console.print()
    
    if all_valid:
        console.print("[green]所有规则配置都正确！[/]")
    else:
        console.print("[red]发现规则配置错误，请修复后重试[/]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()