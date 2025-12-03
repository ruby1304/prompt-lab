# src/run_analysis.py
from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List

import typer
from rich.console import Console
from rich.table import Table

from .chains import run_flow
from .paths import DATA_DIR

app = typer.Typer()
console = Console()


def _load_rows(path: Path, limit: int) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if limit > 0:
        rows = rows[:limit]
    return rows


@app.callback(invoke_without_command=True)
def analyze(
    infile: str = typer.Option(
        "results.demo.csv",
        "--infile",
        "-i",
        help="待评估的 CSV 文件，默认读取 data/results.demo.csv",
    ),
    output_column: str = typer.Option(
        "output",
        "--output-column",
        "-o",
        help="需要评估的模型输出列名，例如 output 或 output__flow",
    ),
    flow: str = typer.Option(
        "analysis_agent",
        "--flow",
        "-f",
        help="评估所用的分析 Agent 配置名，对应 prompts/{flow}.yaml",
    ),
    outfile: str = typer.Option(
        "",
        "--outfile",
        "-O",
        help="评估结果输出文件名，留空则自动在原文件名后添加 .analysis.csv",
    ),
    limit: int = typer.Option(0, help="最多处理多少条（0=全部）"),
):
    """自动评估模型输出，给出通过/不通过与简短理由。"""

    in_path = DATA_DIR / infile
    if not in_path.exists():
        raise typer.BadParameter(f"输入文件不存在：{in_path}")

    out_path = DATA_DIR / (outfile or f"{in_path.stem}.analysis.csv")

    console.rule("[bold blue]Prompt Lab · Auto Analysis")
    console.print(f"[bold]Input file[/]: {in_path}")
    console.print(f"[bold]Output column[/]: {output_column}")
    console.print(f"[bold]Result file[/]: {out_path}")

    rows = _load_rows(in_path, limit)
    if not rows:
        console.print("[yellow]文件为空，无法执行评估。[/]")
        raise typer.Exit(1)

    result_rows: List[Dict[str, str]] = []

    for idx, row in enumerate(rows, start=1):
        if output_column not in row:
            raise typer.BadParameter(f"列 {output_column} 不存在，请检查输入文件")

        console.print(f"[{idx}/{len(rows)}] 评估样本 id={row.get('id', idx)}")

        variables = {
            "case_id": row.get("id", idx),
            "input": row.get("input", ""),
            "context": row.get("context", ""),
            "expected": row.get("expected", ""),
            "model_output": row[output_column],
            "criteria": row.get("criteria", ""),
        }

        analysis = run_flow(flow, extra_vars=variables)
        result_row = dict(row)
        result_row[f"analysis__{output_column}"] = analysis
        result_rows.append(result_row)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=result_rows[0].keys())
        writer.writeheader()
        writer.writerows(result_rows)

    console.print(f"[green]完成！评估结果已写入：[/] {out_path}")

    table = Table(title="Analysis Preview", show_lines=True)
    preview_cols = ["id", output_column, f"analysis__{output_column}"]
    for col in preview_cols:
        if col in result_rows[0]:
            table.add_column(col, overflow="fold")

    for row in result_rows[:3]:
        table.add_row(*[str(row.get(col, ""))[:200] for col in preview_cols])

    console.print(table)


if __name__ == "__main__":
    app()
