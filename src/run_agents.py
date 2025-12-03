# src/run_agents.py
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .agent_registry import load_agent, list_available_agents

app = typer.Typer()
console = Console()


@app.command("list")
def list_agents():
    """列出所有可用的 agents"""
    console.rule("[bold blue]Available Agents")
    
    agent_ids = list_available_agents()
    if not agent_ids:
        console.print("[yellow]没有找到任何 agent 配置文件[/]")
        console.print("[dim]请在 agents/ 目录下创建 .yaml 配置文件[/]")
        return

    table = Table(title="Agent Registry", show_header=True, header_style="bold magenta")
    table.add_column("Agent ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("Flows", style="yellow")
    table.add_column("Default Testset", style="blue")

    for agent_id in agent_ids:
        try:
            agent = load_agent(agent_id)
            flow_names = [f.name for f in agent.flows]
            table.add_row(
                agent.id,
                agent.name,
                ", ".join(flow_names),
                agent.default_testset
            )
        except Exception as e:
            table.add_row(
                agent_id,
                "[red]配置错误[/red]",
                f"[red]{str(e)}[/red]",
                "-"
            )

    console.print(table)


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


if __name__ == "__main__":
    app()