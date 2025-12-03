# src/run_compare.py
from __future__ import annotations

import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
import typer
from rich.console import Console
from rich.table import Table

from .chains import run_flow

app = typer.Typer()
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





@app.callback(invoke_without_command=True)
def compare(
    flows: str = typer.Option(
        ...,
        "--flows",
        "-f",
        help="用逗号分隔的多个 flow 名称，例如：mem0_l1_v1,mem0_l1_v2",
    ),
    infile: str = typer.Option(
        ...,
        "--infile",
        "-i", 
        help="输入测试集文件，例如：mem0_l1.jsonl 或 test_cases.demo.jsonl",
    ),
    outfile: str = typer.Option(
        "results.compare.csv",
        "--outfile",
        "-o",
        help="输出结果文件名，默认 results.compare.csv",
    ),
    limit: int = typer.Option(0, help="最多运行多少条（0=全部）"),
):
    """用同一批测试样本，对比多个 flow 的输出。
    
    JSONL 每行格式：{"id": 1, "input": "...", "context": "", "expected": "..."}
    """
    flow_list = [x.strip() for x in flows.split(",") if x.strip()]
    if len(flow_list) < 2:
        raise typer.BadParameter("至少需要提供两个 flow 名称进行对比。")

    in_path = DATA_DIR / infile
    out_path = DATA_DIR / outfile
    
    # 检查输入文件是否存在
    if not in_path.exists():
        console.print(f"[red]错误：测试文件不存在：[/] {in_path}")
        console.print(f"[yellow]提示：请检查文件路径是否正确[/]")
        raise typer.Exit(1)

    console.rule("[bold blue]Prompt Lab · Multi-Flow Compare")
    console.print(f"[bold]Flows[/]: {', '.join(flow_list)}")
    console.print(f"[bold]Input file[/]: {in_path}")
    console.print(f"[bold]Output file[/]: {out_path}")

    cases = load_test_cases(in_path)
    if limit > 0:
        cases = cases[:limit]

    rows: List[Dict[str, Any]] = []
    
    for idx, case in enumerate(cases, start=1):
        _id = case.get("id", idx)
        input_text = case["input"]
        context = case.get("context", "")
        
        console.print(f"\n[{idx}/{len(cases)}] id={_id}  input={input_text!r}")
        
        row: Dict[str, Any] = {
            "id": _id,
            "input": input_text,
            "context": context,
            "expected": case.get("expected", ""),
        }
        
        # 依次跑每个 flow
        for flow_name in flow_list:
            console.print(f"  -> Running flow: [cyan]{flow_name}[/cyan]")
            output = run_flow(flow_name, input_text, context)
            col_name = f"output__{flow_name}"
            row[col_name] = output
            
        rows.append(row)

    if not rows:
        console.print("[yellow]没有可写入的结果，检查你的测试集文件。[/]")
        return

    # 写 CSV
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    console.print(f"[green]完成！结果已写入：[/] {out_path}")

    # 预览前几条
    table = Table(title="Compare Results Preview", show_lines=True)
    for col in fieldnames[:6]:  # 前几列固定 + 一两个输出列
        table.add_column(col, overflow="fold")
    
    for row in rows[:3]:
        preview_row = []
        for col in fieldnames[:6]:
            value = row.get(col, "")
            if isinstance(value, str) and len(value) > 200:
                value = value[:200] + "..."
            preview_row.append(str(value))
        table.add_row(*preview_row)
    
    console.print(table)


if __name__ == "__main__":
    app()