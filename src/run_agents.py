# src/run_agents.py
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .agent_registry import (
    load_agent, 
    list_available_agents,
    get_registry,
    reload_registry,
    search_agents,
    get_agents_by_tag,
    get_agents_by_owner,
)

app = typer.Typer()
console = Console()


@app.command("list")
def list_agents(
    category: str = typer.Option(None, "--category", "-c", help="Filter by category (production, example, test, system)"),
    environment: str = typer.Option(None, "--environment", "-e", help="Filter by environment (production, staging, demo, test)"),
    tag: str = typer.Option(None, "--tag", "-t", help="Filter by tag"),
    owner: str = typer.Option(None, "--owner", "-o", help="Filter by owner"),
    include_deprecated: bool = typer.Option(True, "--include-deprecated/--no-deprecated", help="Include deprecated agents"),
):
    """列出所有可用的 agents (支持过滤)"""
    console.rule("[bold blue]Available Agents")
    
    # Apply filters
    if tag:
        agent_ids = get_agents_by_tag(tag)
    elif owner:
        agent_ids = get_agents_by_owner(owner)
    else:
        agent_ids = list_available_agents(category=category, include_deprecated=include_deprecated)
    
    if not agent_ids:
        console.print("[yellow]没有找到任何 agent 配置文件[/]")
        console.print("[dim]请在 agents/ 目录下创建 .yaml 配置文件[/]")
        return

    table = Table(title="Agent Registry", show_header=True, header_style="bold magenta")
    table.add_column("Agent ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("Category", style="blue")
    table.add_column("Environment", style="yellow")
    table.add_column("Flows", style="yellow")
    table.add_column("Status", style="magenta")

    for agent_id in agent_ids:
        try:
            agent = load_agent(agent_id)
            flow_names = [f.name for f in agent.flows]
            
            # Apply environment filter if specified
            if environment and agent.environment != environment:
                continue
            
            status = "DEPRECATED" if agent.deprecated else "Active"
            status_style = "[red]" if agent.deprecated else "[green]"
            
            table.add_row(
                agent.id,
                agent.name,
                agent.category or "-",
                agent.environment or "-",
                ", ".join(flow_names),
                f"{status_style}{status}[/]"
            )
        except Exception as e:
            table.add_row(
                agent_id,
                "[red]配置错误[/red]",
                "-",
                "-",
                f"[red]{str(e)}[/red]",
                "[red]Error[/]"
            )

    console.print(table)
    
    # Show registry info
    registry = get_registry()
    if registry:
        console.print(f"\n[dim]Using AgentRegistry v2 with {len(agent_ids)} agents[/]")


@app.command("show")
def show_agent(
    agent_id: str = typer.Argument(..., help="要查看的 agent ID")
):
    """显示指定 agent 的详细信息"""
    try:
        agent = load_agent(agent_id)
    except FileNotFoundError:
        console.print(f"[red]错误：找不到 agent '{agent_id}'[/]")
        available_agents = list_available_agents()
        if available_agents:
            console.print(f"[yellow]可用的 agents：{', '.join(available_agents)}[/]")
        raise typer.Exit(1)

    console.rule(f"[bold blue]Agent: {agent.name}")
    
    # 基本信息
    basic_info = f"""[bold]ID:[/] {agent.id}
[bold]Name:[/] {agent.name}

[bold]Description:[/]
{agent.description}

[bold]Business Goal:[/]
{agent.business_goal}"""
    
    console.print(Panel(basic_info, title="基本信息", border_style="blue"))

    # 期望和要求
    expectations_text = ""
    if agent.expectations.get("must_have"):
        expectations_text += "[bold]Must Have:[/]\n"
        for item in agent.expectations["must_have"]:
            expectations_text += f"  • {item}\n"
    
    if agent.expectations.get("nice_to_have"):
        expectations_text += "\n[bold]Nice to Have:[/]\n"
        for item in agent.expectations["nice_to_have"]:
            expectations_text += f"  • {item}\n"
    
    if expectations_text:
        console.print(Panel(expectations_text.strip(), title="期望和要求", border_style="green"))

    # Flows 信息
    flows_table = Table(title="Available Flows", show_header=True)
    flows_table.add_column("Flow Name", style="cyan")
    flows_table.add_column("File", style="yellow")
    flows_table.add_column("Notes", style="dim")

    for flow in agent.flows:
        flows_table.add_row(flow.name, flow.file, flow.notes)

    console.print(flows_table)

    # 测试集信息
    testsets_text = f"[bold]Default:[/] {agent.default_testset}\n"
    if agent.extra_testsets:
        testsets_text += f"[bold]Extra:[/] {', '.join(agent.extra_testsets)}"
    
    console.print(Panel(testsets_text, title="测试集", border_style="yellow"))

    # 评估标准
    if agent.evaluation.get("criteria"):
        eval_table = Table(title="Evaluation Criteria", show_header=True)
        eval_table.add_column("ID", style="cyan")
        eval_table.add_column("Description", style="white")
        eval_table.add_column("Weight", style="yellow", justify="right")

        for criterion in agent.evaluation["criteria"]:
            eval_table.add_row(
                criterion["id"],
                criterion["desc"],
                f"{criterion['weight']:.2f}"
            )

        console.print(eval_table)
        
        if agent.evaluation.get("preferred_judge_model"):
            console.print(f"[dim]Preferred Judge Model: {agent.evaluation['preferred_judge_model']}[/]")

    # 使用示例
    usage_examples = f"""[bold]批量运行（使用默认配置）:[/]
python -m src.run_batch run --agent {agent.id}

[bold]批量运行（指定 flow）:[/]
python -m src.run_batch run --agent {agent.id} --flow {agent.flows[0].name if agent.flows else 'FLOW_NAME'}

[bold]对比所有 flows:[/]
python -m src.run_compare compare --agent {agent.id}

[bold]对比指定 flows:[/]
python -m src.run_compare compare --agent {agent.id} --flows {','.join([f.name for f in agent.flows[:2]])}"""

    console.print(Panel(usage_examples, title="使用示例", border_style="magenta"))


@app.command("search")
def search_agents_cmd(
    query: str = typer.Argument(..., help="Search query"),
    case_sensitive: bool = typer.Option(False, "--case-sensitive", "-s", help="Case-sensitive search"),
):
    """搜索 agents"""
    console.rule(f"[bold blue]Search Results for: {query}")
    
    agent_ids = search_agents(query, case_sensitive=case_sensitive)
    
    if not agent_ids:
        console.print(f"[yellow]No agents found matching '{query}'[/]")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Agent ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("Description", style="white")
    
    for agent_id in agent_ids:
        try:
            agent = load_agent(agent_id)
            table.add_row(
                agent.id,
                agent.name,
                agent.description[:80] + "..." if len(agent.description) > 80 else agent.description
            )
        except Exception as e:
            table.add_row(
                agent_id,
                "[red]Error[/red]",
                f"[red]{str(e)}[/red]"
            )
    
    console.print(table)
    console.print(f"\n[dim]Found {len(agent_ids)} agents[/]")


@app.command("reload")
def reload_registry_cmd():
    """重新加载 agent registry"""
    console.print("[yellow]Reloading agent registry...[/]")
    
    try:
        reload_registry()
        console.print("[green]✓ Registry reloaded successfully[/]")
        
        # Show updated count
        agent_ids = list_available_agents()
        console.print(f"[dim]Loaded {len(agent_ids)} agents[/]")
    except Exception as e:
        console.print(f"[red]✗ Failed to reload registry: {e}[/]")
        raise typer.Exit(1)


@app.command("info")
def registry_info():
    """显示 registry 信息"""
    console.rule("[bold blue]Agent Registry Information")
    
    registry = get_registry()
    
    if not registry:
        console.print("[yellow]AgentRegistry v2 not available[/]")
        console.print("[dim]Using filesystem-only mode[/]")
        return
    
    # Get statistics
    all_agents = list_available_agents(include_deprecated=True)
    active_agents = list_available_agents(include_deprecated=False)
    
    # Count by category
    categories = {}
    environments = {}
    for agent_id in all_agents:
        try:
            agent = load_agent(agent_id)
            cat = agent.category or "unknown"
            env = agent.environment or "unknown"
            categories[cat] = categories.get(cat, 0) + 1
            environments[env] = environments.get(env, 0) + 1
        except Exception:
            pass
    
    # Display info
    info_text = f"""[bold]Registry Path:[/] {registry.config_path}
[bold]Total Agents:[/] {len(all_agents)}
[bold]Active Agents:[/] {len(active_agents)}
[bold]Deprecated Agents:[/] {len(all_agents) - len(active_agents)}

[bold]By Category:[/]
"""
    for cat, count in sorted(categories.items()):
        info_text += f"  • {cat}: {count}\n"
    
    info_text += "\n[bold]By Environment:[/]\n"
    for env, count in sorted(environments.items()):
        info_text += f"  • {env}: {count}\n"
    
    console.print(Panel(info_text.strip(), title="Registry Statistics", border_style="blue"))
    
    # Hot reload status
    if registry._hot_reload_enabled:
        console.print("[green]✓ Hot reload enabled[/]")
    else:
        console.print("[dim]Hot reload disabled[/]")


if __name__ == "__main__":
    app()