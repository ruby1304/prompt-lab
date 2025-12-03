# src/__main__.py
from .run_batch import run
import typer

if __name__ == "__main__":
    typer.run(run)