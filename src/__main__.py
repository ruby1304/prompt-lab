# src/__main__.py
import typer
from rich.console import Console
from .run_batch import run as batch_run
from .run_compare import app as compare_app
from .run_agents import app as agents_app
from .run_eval import app as eval_app
from .baseline_cli import app as baseline_app
from .regression_cli import app as regression_app
from .compatibility import ensure_compatibility

console = Console()
app = typer.Typer()

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    check_compatibility: bool = typer.Option(
        False, 
        "--check-compatibility", 
        help="检查系统兼容性"
    ),
    version: bool = typer.Option(
        False, 
        "--version", 
        help="显示版本信息"
    )
):
    """
    Prompt Lab - 智能提示工程平台
    
    支持单 Agent/Flow 评估和多步骤 Pipeline 工作流程。
    新旧系统可以并存使用，提供平滑的迁移路径。
    """
    if version:
        console.print("[bold blue]Prompt Lab v2.0[/] - Pipeline 增强版")
        console.print("支持 Agent/Flow 评估和 Pipeline 工作流程")
        return
    
    if check_compatibility:
        console.rule("[bold blue]系统兼容性检查[/]")
        compat_result = ensure_compatibility()
        if compat_result["compatible"]:
            console.print("[green]✓ 系统兼容性正常[/]")
        else:
            console.print("[red]✗ 发现兼容性问题，请查看上述详情[/]")
        return
    
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())

# 添加子命令
app.command("batch")(batch_run)
app.add_typer(compare_app, name="compare")
app.add_typer(agents_app, name="agents")
app.add_typer(eval_app, name="eval")
app.add_typer(baseline_app, name="baseline")
app.add_typer(regression_app, name="regression")

if __name__ == "__main__":
    app()