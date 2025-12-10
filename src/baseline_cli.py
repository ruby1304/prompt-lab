# src/baseline_cli.py
"""
Baseline 管理 CLI 命令模块

提供 baseline save/load/list/compare 子命令，
支持 agent 和 pipeline 的 baseline 管理。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .baseline_manager import (
    save_agent_baseline, save_pipeline_baseline,
    load_agent_baseline, load_pipeline_baseline,
    list_agent_baselines, list_pipeline_baselines,
    BaselineSnapshot
)
from .agent_registry import load_agent, list_available_agents
from .pipeline_config import load_pipeline_config, list_available_pipelines

app = typer.Typer(help="Baseline 管理工具")
console = Console()


@app.command("save")
def save_baseline(
    agent: str = typer.Option("", help="Agent ID（与 --pipeline 二选一）"),
    pipeline: str = typer.Option("", help="Pipeline ID（与 --agent 二选一）"),
    variant: str = typer.Option("baseline", help="要保存的变体名称"),
    name: str = typer.Option(..., help="Baseline 名称"),
    description: str = typer.Option("", help="Baseline 描述"),
    run_file: str = typer.Option("", help="运行结果文件路径（可选）"),
):
    """
    保存 baseline 快照
    
    将指定的 agent 或 pipeline 变体保存为 baseline，
    用于后续的回归测试和性能比较。
    """
    # 参数验证
    if not agent and not pipeline:
        console.print("[red]错误：必须指定 --agent 或 --pipeline 参数[/]")
        raise typer.Exit(1)
    
    if agent and pipeline:
        console.print("[red]错误：不能同时指定 --agent 和 --pipeline 参数[/]")
        raise typer.Exit(1)
    
    try:
        if agent:
            # Agent baseline
            console.rule(f"[bold blue]保存 Agent Baseline[/bold blue]")
            
            # 验证 agent 存在
            try:
                agent_cfg = load_agent(agent)
                console.print(f"[bold]Agent[/]: {agent_cfg.name} ({agent})")
            except FileNotFoundError:
                console.print(f"[red]错误：Agent '{agent}' 不存在[/]")
                available = list_available_agents()
                if available:
                    console.print(f"[yellow]可用的 agents：{', '.join(available)}[/]")
                raise typer.Exit(1)
            
            # 保存 agent baseline
            baseline = save_agent_baseline(
                agent_id=agent,
                variant=variant,
                baseline_name=name,
                description=description,
                run_file_path=run_file if run_file else None
            )
            
        else:
            # Pipeline baseline
            console.rule(f"[bold blue]保存 Pipeline Baseline[/bold blue]")
            
            # 验证 pipeline 存在
            try:
                pipeline_cfg = load_pipeline_config(pipeline)
                console.print(f"[bold]Pipeline[/]: {pipeline_cfg.name} ({pipeline})")
            except Exception as e:
                console.print(f"[red]错误：Pipeline '{pipeline}' 不存在或配置错误: {e}[/]")
                available = list_available_pipelines()
                if available:
                    console.print(f"[yellow]可用的 pipelines：{', '.join(available)}[/]")
                raise typer.Exit(1) 
           
            # 保存 pipeline baseline
            baseline = save_pipeline_baseline(
                pipeline_id=pipeline,
                variant=variant,
                baseline_name=name,
                description=description,
                run_file_path=run_file if run_file else None
            )
        
        # 显示保存结果
        console.print(f"[green]✓ Baseline '{name}' 保存成功！[/]")
        console.print(f"[bold]变体[/]: {variant}")
        console.print(f"[bold]描述[/]: {description or '无'}")
        console.print(f"[bold]创建时间[/]: {baseline.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if baseline.performance_metrics:
            console.print(f"[bold]性能指标[/]:")
            for key, value in baseline.performance_metrics.items():
                console.print(f"  {key}: {value}")
        
    except Exception as e:
        console.print(f"[red]保存 baseline 失败: {e}[/]")
        raise typer.Exit(1)


@app.command("list")
def list_baselines(
    agent: str = typer.Option("", help="Agent ID（与 --pipeline 二选一）"),
    pipeline: str = typer.Option("", help="Pipeline ID（与 --agent 二选一）"),
):
    """
    列出所有 baseline
    
    显示指定 agent 或 pipeline 的所有已保存的 baseline。
    """
    # 参数验证
    if not agent and not pipeline:
        console.print("[red]错误：必须指定 --agent 或 --pipeline 参数[/]")
        raise typer.Exit(1)
    
    if agent and pipeline:
        console.print("[red]错误：不能同时指定 --agent 和 --pipeline 参数[/]")
        raise typer.Exit(1)
    
    try:
        if agent:
            # 列出 agent baselines
            console.rule(f"[bold blue]Agent '{agent}' 的 Baselines[/bold blue]")
            baselines = list_agent_baselines(agent)
            entity_type = "Agent"
        else:
            # 列出 pipeline baselines
            console.rule(f"[bold blue]Pipeline '{pipeline}' 的 Baselines[/bold blue]")
            baselines = list_pipeline_baselines(pipeline)
            entity_type = "Pipeline"
        
        if not baselines:
            console.print(f"[yellow]没有找到任何 baseline[/]")
            console.print(f"[dim]使用以下命令创建 baseline：[/]")
            if agent:
                console.print(f"[dim]  python -m src baseline save --agent {agent} --name <baseline_name>[/]")
            else:
                console.print(f"[dim]  python -m src baseline save --pipeline {pipeline} --name <baseline_name>[/]")
            return
        
        # 创建表格显示
        table = Table(title=f"{entity_type} Baselines")
        table.add_column("名称", style="bold")
        table.add_column("变体", style="cyan")
        table.add_column("描述", overflow="fold")
        table.add_column("创建时间", style="dim")
        table.add_column("性能指标", overflow="fold")
        
        for baseline_info in baselines:
            name = baseline_info.get("name", "")
            variant = baseline_info.get("variant", "")
            description = baseline_info.get("description", "")
            created_at = baseline_info.get("created_at", "")
            
            # 格式化创建时间
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    created_str = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    created_str = created_at
            else:
                created_str = "未知"
            
            # 格式化性能指标
            metrics = baseline_info.get("performance_metrics", {})
            if metrics:
                metrics_str = ", ".join(f"{k}: {v}" for k, v in metrics.items())
                if len(metrics_str) > 50:
                    metrics_str = metrics_str[:47] + "..."
            else:
                metrics_str = "无"
            
            table.add_row(name, variant, description, created_str, metrics_str)
        
        console.print(table)
        console.print(f"\n[bold]总计[/]: {len(baselines)} 个 baseline")
        
    except Exception as e:
        console.print(f"[red]列出 baseline 失败: {e}[/]")
        raise typer.Exit(1)


@app.command("load")
def load_baseline(
    agent: str = typer.Option("", help="Agent ID（与 --pipeline 二选一）"),
    pipeline: str = typer.Option("", help="Pipeline ID（与 --agent 二选一）"),
    name: str = typer.Option(..., help="要加载的 baseline 名称"),
):
    """
    加载并显示 baseline 详情
    
    显示指定 baseline 的详细信息，包括配置、性能指标等。
    """
    # 参数验证
    if not agent and not pipeline:
        console.print("[red]错误：必须指定 --agent 或 --pipeline 参数[/]")
        raise typer.Exit(1)
    
    if agent and pipeline:
        console.print("[red]错误：不能同时指定 --agent 和 --pipeline 参数[/]")
        raise typer.Exit(1)
    
    try:
        if agent:
            # 加载 agent baseline
            console.rule(f"[bold blue]Agent Baseline: {name}[/bold blue]")
            baseline = load_agent_baseline(agent, name)
            entity_type = "Agent"
            entity_id = agent
        else:
            # 加载 pipeline baseline
            console.rule(f"[bold blue]Pipeline Baseline: {name}[/bold blue]")
            baseline = load_pipeline_baseline(pipeline, name)
            entity_type = "Pipeline"
            entity_id = pipeline
        
        if not baseline:
            console.print(f"[red]Baseline '{name}' 不存在[/]")
            # 显示可用的 baselines
            if agent:
                available = list_agent_baselines(agent)
            else:
                available = list_pipeline_baselines(pipeline)
            
            if available:
                names = [b.get("name", "") for b in available]
                console.print(f"[yellow]可用的 baselines：{', '.join(names)}[/]")
            raise typer.Exit(1)
        
        # 显示 baseline 详情
        console.print(f"[bold]{entity_type} ID[/]: {entity_id}")
        console.print(f"[bold]Baseline 名称[/]: {baseline.baseline_name}")
        console.print(f"[bold]变体[/]: {baseline.variant}")
        console.print(f"[bold]描述[/]: {baseline.description or '无'}")
        console.print(f"[bold]创建时间[/]: {baseline.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 显示配置信息
        if baseline.config_snapshot:
            console.print(f"\n[bold cyan]配置快照[/]:")
            config_panel = Panel(
                json.dumps(baseline.config_snapshot, indent=2, ensure_ascii=False),
                title="Configuration",
                expand=False
            )
            console.print(config_panel)
        
        # 显示性能指标
        if baseline.performance_metrics:
            console.print(f"\n[bold cyan]性能指标[/]:")
            metrics_table = Table()
            metrics_table.add_column("指标", style="bold")
            metrics_table.add_column("值", justify="right")
            
            for key, value in baseline.performance_metrics.items():
                metrics_table.add_row(key, str(value))
            
            console.print(metrics_table)
        
        # 显示运行数据
        if baseline.run_data:
            console.print(f"\n[bold cyan]运行数据[/]:")
            console.print(f"样本数量: {len(baseline.run_data)}")
            
            if baseline.run_data:
                # 显示前几个样本作为预览
                preview_table = Table(title="样本预览（前3个）")
                
                # 动态添加列
                first_sample = baseline.run_data[0]
                for key in list(first_sample.keys())[:5]:  # 只显示前5列
                    preview_table.add_column(key, overflow="fold")
                
                for sample in baseline.run_data[:3]:
                    row_data = []
                    for key in list(first_sample.keys())[:5]:
                        value = str(sample.get(key, ""))
                        if len(value) > 30:
                            value = value[:27] + "..."
                        row_data.append(value)
                    preview_table.add_row(*row_data)
                
                console.print(preview_table)
        
    except Exception as e:
        console.print(f"[red]加载 baseline 失败: {e}[/]")
        raise typer.Exit(1)


@app.command("compare")
def compare_baselines(
    agent: str = typer.Option("", help="Agent ID（与 --pipeline 二选一）"),
    pipeline: str = typer.Option("", help="Pipeline ID（与 --agent 二选一）"),
    baseline: str = typer.Option(..., help="基准 baseline 名称"),
    variant: str = typer.Option(..., help="要比较的变体名称"),
):
    """
    比较 baseline 和变体性能
    
    对比指定 baseline 和变体的性能差异，
    生成详细的比较报告。
    """
    # 参数验证
    if not agent and not pipeline:
        console.print("[red]错误：必须指定 --agent 或 --pipeline 参数[/]")
        raise typer.Exit(1)
    
    if agent and pipeline:
        console.print("[red]错误：不能同时指定 --agent 和 --pipeline 参数[/]")
        raise typer.Exit(1)
    
    try:
        if agent:
            console.rule(f"[bold blue]Agent Baseline 比较[/bold blue]")
            baseline_snapshot = load_agent_baseline(agent, baseline)
            entity_type = "Agent"
            entity_id = agent
        else:
            console.rule(f"[bold blue]Pipeline Baseline 比较[/bold blue]")
            baseline_snapshot = load_pipeline_baseline(pipeline, baseline)
            entity_type = "Pipeline"
            entity_id = pipeline
        
        if not baseline_snapshot:
            console.print(f"[red]Baseline '{baseline}' 不存在[/]")
            raise typer.Exit(1)
        
        console.print(f"[bold]{entity_type}[/]: {entity_id}")
        console.print(f"[bold]基准 Baseline[/]: {baseline}")
        console.print(f"[bold]比较变体[/]: {variant}")
        
        # 显示基准性能
        console.print(f"\n[bold cyan]基准性能 ({baseline})[/]:")
        if baseline_snapshot.performance_metrics:
            baseline_table = Table()
            baseline_table.add_column("指标", style="bold")
            baseline_table.add_column("值", justify="right")
            
            for key, value in baseline_snapshot.performance_metrics.items():
                baseline_table.add_row(key, str(value))
            
            console.print(baseline_table)
        else:
            console.print("[yellow]无性能指标数据[/]")
        
        # 注意：实际的变体比较需要运行新的评估
        # 这里只是显示框架，实际实现需要集成评估系统
        console.print(f"\n[bold yellow]注意[/]: 要进行完整的性能比较，请先运行变体评估：")
        if agent:
            console.print(f"[dim]  python -m src eval --agent {agent} --flows <flows> --judge[/]")
        else:
            console.print(f"[dim]  python -m src eval --pipeline {pipeline} --variants {variant} --judge[/]")
        
        console.print(f"[dim]然后使用回归测试命令进行详细比较：[/]")
        if agent:
            console.print(f"[dim]  python -m src regression --agent {agent} --baseline {baseline} --variant {variant}[/]")
        else:
            console.print(f"[dim]  python -m src regression --pipeline {pipeline} --baseline {baseline} --variant {variant}[/]")
        
    except Exception as e:
        console.print(f"[red]比较 baseline 失败: {e}[/]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()