#!/usr/bin/env python3
"""
生成人工评审表，将 compare 结果展开成方便人工打分的格式
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Dict, Any

import typer
from rich.console import Console
from rich.table import Table

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

app = typer.Typer()
console = Console()


@app.command()
def make(
    infile: str = typer.Option(..., help="compare 结果文件，如 mem0_l1.compare.csv"),
    outfile: str = typer.Option("manual_review.csv", help="输出供人工打分的文件"),
    truncate: int = typer.Option(300, help="输出预览的最大字符数，避免一行太长"),
):
    """生成人工评审表"""
    in_path = DATA_DIR / infile
    out_path = DATA_DIR / outfile

    console.print(f"[bold]Input[/]: {in_path}")
    console.print(f"[bold]Output[/]: {out_path}")

    if not in_path.exists():
        console.print(f"[red]文件不存在：{in_path}[/]")
        raise typer.Exit(1)

    with open(in_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        console.print("[yellow]没有数据可处理[/]")
        raise typer.Exit()

    # 找到所有 output__ 开头的列
    flow_cols = [c for c in rows[0].keys() if c.startswith("output__")]
    if not flow_cols:
        console.print("[red]找不到 output__ 开头的列，这是 compare 结果吗？[/]")
        raise typer.Exit(1)

    console.print(f"[blue]发现 {len(flow_cols)} 个 flow：{', '.join(flow_cols)}[/]")

    review_rows: List[Dict[str, Any]] = []
    for row in rows:
        # 基础信息
        base_info = {
            "id": row.get("id", ""),
            "input": (row.get("input", "") or "")[:truncate],
            "context": (row.get("context", "") or "")[:truncate],
            "expected": (row.get("expected", "") or "")[:truncate],
        }
        
        # 为每个 flow 创建一行
        for col in flow_cols:
            flow_name = col.replace("output__", "")
            output = row.get(col, "") or ""
            
            review_rows.append({
                **base_info,
                "flow": flow_name,
                "output": output,
                "human_score": "",      # 人工填写 0-10
                "human_label": "",      # 比如 good/bad/edge
                "human_comment": "",    # 简短说明
            })

    # 写入 CSV
    fieldnames = ["id", "flow", "input", "context", "expected", "output",
                  "human_score", "human_label", "human_comment"]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(review_rows)

    console.print(f"[green]已生成人工评审表：[/] {out_path}")
    console.print(f"[blue]共 {len(review_rows)} 条记录待评审[/]")

    # 简单预览
    table = Table(title="Manual Review Preview", show_lines=True)
    for col in ["id", "flow", "input", "expected", "output"]:
        table.add_column(col, overflow="fold", max_width=30)
    
    for r in review_rows[:5]:
        table.add_row(
            str(r["id"]),
            r["flow"],
            r["input"][:50] + ("..." if len(r["input"]) > 50 else ""),
            r["expected"][:50] + ("..." if len(r["expected"]) > 50 else ""),
            r["output"][:100] + ("..." if len(r["output"]) > 100 else "")
        )
    console.print(table)
    
    if len(review_rows) > 5:
        console.print(f"[dim]... 还有 {len(review_rows) - 5} 条记录[/]")


if __name__ == "__main__":
    app()