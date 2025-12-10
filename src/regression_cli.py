# src/regression_cli.py
"""
回归测试 CLI 接口模块

实现 eval_regression 命令，支持 agent 和 pipeline 模式的回归测试，
提供详细的中文进度提示和结果摘要。
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from .regression_tester import RegressionTester, RegressionTestResult, RegressionTestConfig
from .agent_registry import load_agent, list_available_agents
from .pipeline_config import load_pipeline_config, list_available_pipelines
from .baseline_manager import load_agent_baseline, load_pipeline_baseline
from .data_manager import get_agent_runs_dir, get_pipeline_runs_dir
from .testset_filter import filter_samples_by_tags
from .run_eval import load_test_cases

app = typer.Typer(help="回归测试工具")
console = Console()


@app.command("run")
def run_regression_test(
    agent: str = typer.Option("", help="Agent ID（与 --pipeline 二选一）"),
    pipeline: str = typer.Option("", help="Pipeline ID（与 --agent 二选一）"),
    baseline: str = typer.Option(..., help="基准 baseline 名称"),
    variant: str = typer.Option(..., help="要测试的变体名称"),
    testset: str = typer.Option("", help="测试集文件（可选，使用默认测试集）"),
    limit: int = typer.Option(0, help="限制测试样本数量（0=全部）"),
    include_tags: str = typer.Option("", help="只包含指定标签的样本，多个标签用逗号分隔"),
    exclude_tags: str = typer.Option("", help="排除指定标签的样本，多个标签用逗号分隔"),
    threshold: float = typer.Option(0.1, help="回归检测阈值（分数下降超过此值视为回归）"),
    output: str = typer.Option("", help="输出报告文件路径（可选）"),
):
    """
    执行回归测试
    
    比较指定变体与 baseline 的性能，检测潜在的回归问题。
    支持 Agent 和 Pipeline 两种模式。
    """
    # 参数验证
    if not agent and not pipeline:
        console.print("[red]错误：必须指定 --agent 或 --pipeline 参数[/]")
        raise typer.Exit(1)
    
    if agent and pipeline:
        console.print("[red]错误：不能同时指定 --agent 和 --pipeline 参数[/]")
        raise typer.Exit(1)
    
    # 显示回归测试开始信息
    console.rule("[bold blue]回归测试开始[/bold blue]")
    
    try:
        if agent:
            # Agent 回归测试
            console.print(f"[bold]模式[/]: Agent 回归测试")
            console.print(f"[bold]Agent[/]: {agent}")
            
            # 验证 agent 存在
            try:
                agent_cfg = load_agent(agent)
                console.print(f"[bold]Agent 名称[/]: {agent_cfg.name}")
            except FileNotFoundError:
                console.print(f"[red]错误：Agent '{agent}' 不存在[/]")
                available = list_available_agents()
                if available:
                    console.print(f"[yellow]可用的 agents：{', '.join(available)}[/]")
                raise typer.Exit(1)
            
            # 加载 baseline
            baseline_snapshot = load_agent_baseline(agent, baseline)
            if not baseline_snapshot:
                console.print(f"[red]错误：Baseline '{baseline}' 不存在[/]")
                raise typer.Exit(1)
            
            entity_type = "agent"
            entity_id = agent
            entity_config = agent_cfg
            
        else:
            # Pipeline 回归测试
            console.print(f"[bold]模式[/]: Pipeline 回归测试")
            console.print(f"[bold]Pipeline[/]: {pipeline}")
            
            # 验证 pipeline 存在
            try:
                pipeline_cfg = load_pipeline_config(pipeline)
                console.print(f"[bold]Pipeline 名称[/]: {pipeline_cfg.name}")
            except Exception as e:
                console.print(f"[red]错误：Pipeline '{pipeline}' 不存在或配置错误: {e}[/]")
                available = list_available_pipelines()
                if available:
                    console.print(f"[yellow]可用的 pipelines：{', '.join(available)}[/]")
                raise typer.Exit(1)
            
            # 加载 baseline
            baseline_snapshot = load_pipeline_baseline(pipeline, baseline)
            if not baseline_snapshot:
                console.print(f"[red]错误：Baseline '{baseline}' 不存在[/]")
                raise typer.Exit(1)
            
            entity_type = "pipeline"
            entity_id = pipeline
            entity_config = pipeline_cfg
        
        console.print(f"[bold]基准 Baseline[/]: {baseline}")
        console.print(f"[bold]测试变体[/]: {variant}")
        console.print(f"[bold]回归阈值[/]: {threshold}")
        
        # 显示 baseline 信息
        console.print(f"\n[bold cyan]基准信息[/]:")
        console.print(f"创建时间: {baseline_snapshot.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"描述: {baseline_snapshot.description or '无'}")
        
        if baseline_snapshot.performance_metrics:
            console.print("性能指标:")
            for key, value in baseline_snapshot.performance_metrics.items():
                console.print(f"  {key}: {value}")
        
        # 准备测试集
        console.rule("[bold green]准备测试数据[/bold green]")
        
        if testset:
            # 使用指定测试集
            testset_path = Path(testset)
            if not testset_path.exists():
                console.print(f"[red]错误：测试集文件不存在: {testset}[/]")
                raise typer.Exit(1)
            console.print(f"[bold]测试集[/]: {testset}")
        else:
            # 使用默认测试集
            if entity_type == "agent":
                testset_file = entity_config.default_testset
            else:
                testset_file = entity_config.default_testset
            
            console.print(f"[bold]测试集[/]: {testset_file} (默认)")
            
            # 查找测试集文件
            if entity_type == "agent":
                from .data_manager import get_agent_testsets_dir
                testset_dir = get_agent_testsets_dir(entity_id)
            else:
                from .data_manager import get_pipeline_testsets_dir
                testset_dir = get_pipeline_testsets_dir(entity_id)
            
            testset_path = testset_dir / testset_file
            if not testset_path.exists():
                # 尝试在项目根目录查找
                root_path = Path(testset_file)
                if root_path.exists():
                    testset_path = root_path
                else:
                    console.print(f"[red]错误：测试集文件不存在: {testset_file}[/]")
                    raise typer.Exit(1)
        
        # 加载测试用例
        cases = load_test_cases(testset_path)
        console.print(f"加载测试样本: {len(cases)} 条")
        
        # 应用标签过滤
        include_tags_list = [tag.strip() for tag in include_tags.split(",") if tag.strip()] if include_tags else None
        exclude_tags_list = [tag.strip() for tag in exclude_tags.split(",") if tag.strip()] if exclude_tags else None
        
        if include_tags_list or exclude_tags_list:
            console.print(f"[bold cyan]应用标签过滤[/]")
            if include_tags_list:
                console.print(f"包含标签: {', '.join(include_tags_list)}")
            if exclude_tags_list:
                console.print(f"排除标签: {', '.join(exclude_tags_list)}")
            
            original_count = len(cases)
            cases = filter_samples_by_tags(cases, include_tags_list, exclude_tags_list, show_stats=True)
            
            if len(cases) == 0:
                console.print("[red]错误：过滤后没有剩余样本，请检查标签过滤条件[/]")
                raise typer.Exit(1)
            
            console.print(f"过滤前样本数: {original_count}, 过滤后样本数: {len(cases)}")
        
        if limit > 0:
            cases = cases[:limit]
            console.print(f"限制样本数量: {len(cases)} 条")
        
        if not cases:
            console.print("[yellow]没有测试用例可执行。[/]")
            raise typer.Exit()
        
        # 执行回归测试
        console.rule("[bold green]执行回归测试[/bold green]")
        
        # 创建回归测试配置
        config = RegressionTestConfig(
            entity_type=entity_type,
            entity_id=entity_id,
            baseline_name=baseline,
            variant_name=variant,
            testset_path=str(testset_path),
            include_tags=include_tags_list or [],
            exclude_tags=exclude_tags_list or [],
            score_threshold=threshold,
            must_have_check=True,
            apply_rules=True,
            apply_judge=True,
            limit=limit
        )
        
        # 创建回归测试器
        tester = RegressionTester()
        
        # 设置进度回调
        def progress_callback(current: int, total: int, message: str):
            console.print(f"[{current+1}/{total}] {message}")
        
        tester.set_progress_callback(progress_callback)
        
        # 执行回归测试
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("正在执行回归测试...", total=len(cases))
            
            def update_progress(current: int, total: int, message: str):
                progress.update(task, completed=current, description=f"正在处理: {message}")
            
            regression_result = tester.run_regression_test(config)
        
        # 显示回归测试结果
        console.rule("[bold blue]回归测试结果[/bold blue]")
        
        show_regression_results(regression_result, threshold)
        
        # 保存报告
        if output:
            save_regression_report(regression_result, Path(output))
            console.print(f"\n[green]回归测试报告已保存至: {output}[/]")
        else:
            # 自动生成报告文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if entity_type == "agent":
                runs_dir = get_agent_runs_dir(entity_id)
            else:
                runs_dir = get_pipeline_runs_dir(entity_id)
            
            report_path = runs_dir / f"regression_{baseline}_vs_{variant}_{timestamp}.json"
            save_regression_report(regression_result, report_path)
            console.print(f"\n[green]回归测试报告已保存至: {report_path}[/]")
        
    except Exception as e:
        console.print(f"[red]回归测试失败: {e}[/]")
        raise typer.Exit(1)


def show_regression_results(result: RegressionTestResult, threshold: float):
    """显示回归测试结果摘要"""
    console.print(f"[bold]测试完成时间[/]: {result.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    console.print(f"[bold]测试样本数量[/]: {len(result.variant_results)}")
    console.print(f"[bold]回归检测阈值[/]: {threshold}")
    
    # 显示基准信息
    console.print(f"[bold]基准 Baseline[/]: {result.config.baseline_name}")
    console.print(f"[bold]测试变体[/]: {result.config.variant_name}")
    
    # 整体性能对比（如果有比较报告）
    if result.comparison_report:
        console.print(f"\n[bold cyan]整体性能对比[/]:")
        performance_table = Table()
        performance_table.add_column("指标", style="bold")
        performance_table.add_column("基准值", justify="right")
        performance_table.add_column("当前值", justify="right")
        performance_table.add_column("变化", justify="right")
        performance_table.add_column("状态", justify="center")
        
        # 从比较报告中提取性能指标
        baseline_metrics = result.baseline_snapshot.performance_metrics or {}
        
        # 计算当前变体的平均性能
        if result.variant_results:
            avg_score = sum(r.overall_score for r in result.variant_results) / len(result.variant_results)
            must_have_pass_rate = sum(1 for r in result.variant_results if r.must_have_pass) / len(result.variant_results) * 100
            
            # 显示平均分对比
            baseline_avg = baseline_metrics.get("avg_score", 0)
            score_delta = avg_score - baseline_avg
            
            # 状态标记
            if abs(score_delta) < threshold:
                status = "[green]正常[/green]"
            elif score_delta < -threshold:
                status = "[red]回归[/red]"
            else:
                status = "[blue]改进[/blue]"
            
            performance_table.add_row(
                "平均分",
                f"{baseline_avg:.3f}",
                f"{avg_score:.3f}",
                f"{score_delta:+.3f}",
                status
            )
            
            # 显示 Must-Have 通过率对比
            baseline_must_have = baseline_metrics.get("must_have_pass_rate", 0)
            must_have_delta = must_have_pass_rate - baseline_must_have
            
            if abs(must_have_delta) < 5:  # 5% 阈值
                must_have_status = "[green]正常[/green]"
            elif must_have_delta < -5:
                must_have_status = "[red]回归[/red]"
            else:
                must_have_status = "[blue]改进[/blue]"
            
            performance_table.add_row(
                "Must-Have通过率",
                f"{baseline_must_have:.1f}%",
                f"{must_have_pass_rate:.1f}%",
                f"{must_have_delta:+.1f}%",
                must_have_status
            )
        
        console.print(performance_table)
    
    # 回归案例统计
    if result.regression_cases:
        console.print(f"\n[bold red]发现回归案例: {len(result.regression_cases)} 个[/bold red]")
        
        # 显示最严重的回归案例
        worst_cases = sorted(result.regression_cases, key=lambda x: x.score_delta)[:5]
        
        regression_table = Table(title="最严重的回归案例（前5个）")
        regression_table.add_column("样本ID", style="bold")
        regression_table.add_column("基准分数", justify="right")
        regression_table.add_column("当前分数", justify="right")
        regression_table.add_column("分数下降", justify="right", style="red")
        regression_table.add_column("问题类型", overflow="fold")
        
        for case in worst_cases:
            regression_table.add_row(
                case.sample_id,
                f"{case.baseline_score:.2f}",
                f"{case.current_score:.2f}",
                f"{case.score_delta:.2f}",
                case.issue_type or "性能下降"
            )
        
        console.print(regression_table)
        
        # 回归类型统计
        issue_types = {}
        for case in result.regression_cases:
            issue_type = case.issue_type or "性能下降"
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
        
        if issue_types:
            console.print(f"\n[bold]回归类型分布[/]:")
            for issue_type, count in sorted(issue_types.items(), key=lambda x: x[1], reverse=True):
                console.print(f"  {issue_type}: {count} 个案例")
    else:
        console.print(f"\n[bold green]✓ 未发现回归案例[/bold green]")
    
    # 显示摘要
    if result.summary:
        console.print(f"\n[bold cyan]测试摘要[/]:")
        console.print(result.summary)
    
    # 总结和建议
    console.print(f"\n[bold cyan]建议[/]:")
    if result.regression_cases:
        console.print(f"[red]⚠️  检测到 {len(result.regression_cases)} 个回归案例，建议进一步分析[/]")
        console.print(f"[yellow]💡 建议检查变体 '{result.config.variant_name}' 的配置和实现[/]")
        console.print(f"[yellow]💡 重点关注分数下降超过 {threshold} 的案例[/]")
    else:
        console.print(f"[green]✅ 变体 '{result.config.variant_name}' 性能正常，可以考虑部署[/]")


def save_regression_report(result: RegressionTestResult, output_path: Path):
    """保存回归测试报告到文件"""
    # 使用 RegressionTestResult 的 to_dict 方法
    report_data = result.to_dict()
    
    # 添加一些额外的摘要信息
    report_data["summary_stats"] = {
        "total_regressions": len(result.regression_cases),
        "worst_regression": min([c.score_delta for c in result.regression_cases]) if result.regression_cases else 0,
        "total_samples": len(result.variant_results),
        "avg_score": sum(r.overall_score for r in result.variant_results) / len(result.variant_results) if result.variant_results else 0,
        "must_have_pass_rate": sum(1 for r in result.variant_results if r.must_have_pass) / len(result.variant_results) * 100 if result.variant_results else 0
    }
    
    # 确保输出目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 保存 JSON 报告
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    app()