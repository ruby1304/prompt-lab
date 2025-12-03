#!/usr/bin/env python3
"""
评估结果分析脚本
用于分析 LLM-as-judge 评估结果，提供统计信息和洞察
"""

import pandas as pd
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

def analyze_results(
    eval_file: str = typer.Argument(..., help="评估结果 CSV 文件路径"),
    show_details: bool = typer.Option(False, "--details", help="显示详细的案例分析")
):
    """分析评估结果文件"""
    
    # 读取数据
    try:
        df = pd.read_csv(eval_file)
    except FileNotFoundError:
        console.print(f"[red]文件不存在: {eval_file}[/red]")
        raise typer.Exit(1)
    
    console.rule(f"[bold blue]评估结果分析 - {Path(eval_file).name}[/bold blue]")
    
    # 1. 基本统计信息
    console.print("\n[bold]1. 基本统计信息[/bold]")
    
    basic_stats = Table(title="数据概览")
    basic_stats.add_column("指标", style="cyan")
    basic_stats.add_column("数值", style="green")
    
    basic_stats.add_row("总评估次数", str(len(df)))
    basic_stats.add_row("测试用例数", str(df['id'].nunique()))
    basic_stats.add_row("Flow 数量", str(df['flow'].nunique()))
    basic_stats.add_row("平均总分", f"{df['overall_score'].mean():.2f}")
    basic_stats.add_row("总分标准差", f"{df['overall_score'].std():.2f}")
    
    console.print(basic_stats)
    
    # 2. Flow 对比分析
    console.print("\n[bold]2. Flow 性能对比[/bold]")
    
    flow_stats = df.groupby('flow')['overall_score'].agg(['count', 'mean', 'std', 'min', 'max']).round(2)
    
    flow_table = Table(title="Flow 性能统计")
    flow_table.add_column("Flow", style="cyan")
    flow_table.add_column("样本数", justify="right")
    flow_table.add_column("平均分", justify="right", style="green")
    flow_table.add_column("标准差", justify="right")
    flow_table.add_column("最低分", justify="right", style="red")
    flow_table.add_column("最高分", justify="right", style="blue")
    
    for flow, stats in flow_stats.iterrows():
        flow_table.add_row(
            flow,
            str(int(stats['count'])),
            f"{stats['mean']:.2f}",
            f"{stats['std']:.2f}",
            f"{stats['min']:.1f}",
            f"{stats['max']:.1f}"
        )
    
    console.print(flow_table)
    
    # 3. 维度分析
    console.print("\n[bold]3. 评估维度分析[/bold]")
    
    # 找出所有评分维度
    score_cols = [col for col in df.columns if col.endswith('__score') and col != 'overall_score']
    
    if score_cols:
        criteria_table = Table(title="各维度平均得分")
        criteria_table.add_column("维度", style="cyan")
        for flow in df['flow'].unique():
            criteria_table.add_column(f"{flow}", justify="right")
        
        for col in score_cols:
            criterion = col.replace('__score', '')
            row = [criterion]
            for flow in df['flow'].unique():
                flow_data = df[df['flow'] == flow][col]
                if len(flow_data) > 0:
                    row.append(f"{flow_data.mean():.2f}")
                else:
                    row.append("N/A")
            criteria_table.add_row(*row)
        
        console.print(criteria_table)
    
    # 4. 问题案例识别
    console.print("\n[bold]4. 问题案例识别[/bold]")
    
    # 计算同一测试用例不同 flow 的评分差异
    if df['id'].nunique() > 1 and df['flow'].nunique() > 1:
        score_diff = df.groupby('id')['overall_score'].agg(['min', 'max'])
        score_diff['diff'] = score_diff['max'] - score_diff['min']
        
        # 找出评分差异较大的案例
        problematic_threshold = 1.5
        problematic_cases = score_diff[score_diff['diff'] > problematic_threshold]
        
        if len(problematic_cases) > 0:
            console.print(f"[yellow]发现 {len(problematic_cases)} 个评分差异较大的案例（差异 > {problematic_threshold}）:[/yellow]")
            
            problem_table = Table()
            problem_table.add_column("案例ID", style="cyan")
            problem_table.add_column("最低分", justify="right", style="red")
            problem_table.add_column("最高分", justify="right", style="green")
            problem_table.add_column("差异", justify="right", style="yellow")
            
            for case_id, stats in problematic_cases.iterrows():
                problem_table.add_row(
                    str(case_id),
                    f"{stats['min']:.1f}",
                    f"{stats['max']:.1f}",
                    f"{stats['diff']:.1f}"
                )
            
            console.print(problem_table)
        else:
            console.print("[green]✓ 未发现评分差异过大的案例[/green]")
    
    # 5. 详细案例分析（可选）
    if show_details:
        console.print("\n[bold]5. 详细案例分析[/bold]")
        
        # 显示最高分和最低分的案例
        best_case = df.loc[df['overall_score'].idxmax()]
        worst_case = df.loc[df['overall_score'].idxmin()]
        
        console.print(Panel(
            f"[green]最高分案例[/green]\n"
            f"ID: {best_case['id']}, Flow: {best_case['flow']}\n"
            f"总分: {best_case['overall_score']:.1f}\n"
            f"评语: {best_case.get('overall_comment', 'N/A')}",
            title="最佳表现"
        ))
        
        console.print(Panel(
            f"[red]最低分案例[/red]\n"
            f"ID: {worst_case['id']}, Flow: {worst_case['flow']}\n"
            f"总分: {worst_case['overall_score']:.1f}\n"
            f"评语: {worst_case.get('overall_comment', 'N/A')}",
            title="待改进案例"
        ))
    
    # 6. 改进建议
    console.print("\n[bold]6. 改进建议[/bold]")
    
    suggestions = []
    
    # 基于 flow 性能差异给出建议
    if len(flow_stats) > 1:
        best_flow = flow_stats['mean'].idxmax()
        worst_flow = flow_stats['mean'].idxmin()
        performance_gap = flow_stats.loc[best_flow, 'mean'] - flow_stats.loc[worst_flow, 'mean']
        
        if performance_gap > 0.5:
            suggestions.append(f"• {best_flow} 比 {worst_flow} 平均高 {performance_gap:.1f} 分，建议重点优化 {worst_flow}")
    
    # 基于维度分析给出建议
    if score_cols:
        for col in score_cols:
            criterion = col.replace('__score', '')
            avg_score = df[col].mean()
            if avg_score < 7.0:
                suggestions.append(f"• {criterion} 维度平均分较低（{avg_score:.1f}），需要重点关注")
    
    if suggestions:
        for suggestion in suggestions:
            console.print(suggestion)
    else:
        console.print("[green]✓ 整体表现良好，继续保持！[/green]")

if __name__ == "__main__":
    typer.run(analyze_results)