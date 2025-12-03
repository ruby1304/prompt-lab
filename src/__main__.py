# src/__main__.py
import typer
from .run_batch import run as batch_run
from .run_compare import app as compare_app
from .run_agents import app as agents_app
from .run_eval import app as eval_app

app = typer.Typer()

# 添加子命令
app.command("batch")(batch_run)
app.add_typer(compare_app, name="compare")
app.add_typer(agents_app, name="agents")
app.add_typer(eval_app, name="eval")

if __name__ == "__main__":
    app()