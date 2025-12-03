# src/run_batch.py
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List, Dict, Any

import typer
from rich.console import Console
from rich.table import Table

from .chains import run_flow

console = Console()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"


def load_test_cases(path: Path) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            cases.append(json.loads(line))
    return cases


def run(
    flow: str = typer.Option("flow_demo", help="使用的 flow 名称，对应 prompts/{flow}.yaml"),
    infile: str = typer.Option("test_cases.demo.jsonl", help="输入测试集文件，默认 data/test_cases.demo.jsonl"),
    outfile: str = typer.Option("results.demo.csv", help="输出结果文件名，默认 data/results.demo.csv"),
    limit: int = typer.Option(0, help="最多运行多少条（0=全部）"),
):
    """
    批量跑测试集：读取 JSONL -> 调用模型 -> 写入 CSV
    JSONL 每行格式：
    {"id": 1, "input": "...", "context": "", "expected": "..."}
    """
    in_path = DATA_DIR / infile
    out_path = DATA_DIR / outfile

    console.rule("[bold blue]Prompt Lab · Batch Run")
    console.print(f"[bold]Flow[/]: {flow}")
    console.print(f"[bold]Input file[/]: {in_path}")
    console.print(f"[bold]Output file[/]: {out_path}")

    cases = load_test_cases(in_path)
    if limit > 0:
        cases = cases[:limit]

    rows: List[Dict[str, Any]] = []
    for idx, case in enumerate(cases, start=1):
        _id = case.get("id", idx)
        
        # 提取所有变量，除了id和expected
        variables = {k: v for k, v in case.items() if k not in ["id", "expected"]}
        
        # 为了向后兼容，如果有input字段，显示它；否则显示前几个变量
        display_info = case.get("input", str(list(variables.keys())[:3]))
        console.print(f"[{idx}/{len(cases)}] id={_id}  variables={display_info!r}")

        output = run_flow(flow, extra_vars=variables)

        # 构建结果行，包含所有原始变量
        result_row = {"id": _id}
        result_row.update(variables)  # 添加所有变量
        result_row.update({
            "expected": case.get("expected", ""),
            "output": output,
        })
        rows.append(result_row)

    if not rows:
        console.print("[yellow]没有可写入的结果，检查你的测试集文件。[/]")
        return

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    console.print(f"[green]完成！结果已写入：[/] {out_path}")

    # 简单预览前几条
    table = Table(title="Sample Results Preview", show_lines=True)
    # 动态确定要显示的列
    preview_cols = ["id"]
    if "input" in rows[0]:
        preview_cols.append("input")
    preview_cols.extend(["expected", "output"])
    
    for col in preview_cols:
        table.add_column(col, overflow="fold")
    
    for row in rows[:3]:
        row_data = [str(row["id"])]
        if "input" in row:
            row_data.append(row["input"])
        row_data.extend([row.get("expected", ""), row["output"][:200]])
        table.add_row(*row_data)
    console.print(table)


if __name__ == "__main__":
    typer.run(run)
