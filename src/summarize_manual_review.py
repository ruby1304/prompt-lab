#!/usr/bin/env python3
"""
汇总人工评审结果，生成统计报告
"""
from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, List

import typer
from rich.console import Console
from rich.table import Table

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

app = typer.Typer()
console = Console()


@app.command()
def summary(
    infile: str = typer.Option(..., help="人工打分后的文件，如 mem0_l1.manual_review.csv"),
):
    """汇总人工评审结果"""
    in_path = DATA_DIR / infile
    console.print(f"[bold]Input[/]: {in_path}")

    if not in_path.exists():
        console.print(f"[red]文件不存在：{in_path}[/]")
        raise typer.Exit(1)

    with open(in_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        console.print("[yellow]没有数据可汇总[/]")
        raise typer.Exit()

    # 统计数据结构
    stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "n": 0,
        "score_sum": 0.0,
        "score_n": 0,
        "label_count": defaultdict(int),
        "scores": [],
    })

    # 处理每一行
    for r in rows:
        flow = r.get("flow", "unknown")
        label = (r.get("human_label") or "").strip() or "unlabeled"
        
        # 处理分数
        try:
            score = float(r["human_score"]) if r.get("human_score", "").strip() else None
        except (ValueError, TypeError):
            score = None

        s = stats[flow]
        s["n"] += 1
        s["label_count"][label] += 1
        
        if score is not None:
            s["score_sum"] += score
            s["score_n"] += 1
            s["scores"].append(score)

    # 生成汇总表
    table = Table(title="Manual Eval Summary", show_lines=True)
    table.add_column("Flow", style="bold")
    table.add_column("Cases", justify="right")
    table.add_column("Avg Score", justify="right")
    table.add_column("Score Range", justify="right")
    table.add_column("Labels", overflow="fold")

    for flow, s in sorted(stats.items()):
        # 平均分
        if s["score_n"] > 0:
            avg_score = f"{s['score_sum'] / s['score_n']:.2f}"
            min_score = min(s["scores"])
            max_score = max(s["scores"])
            score_range = f"{min_score:.1f}-{max_score:.1f}" if min_score != max_score else f"{min_score:.1f}"
        else:
            avg_score = "-"
            score_range = "-"
        
        # 标签分布
        label_str = ", ".join(f"{k}:{v}" for k, v in sorted(s["label_count"].items()))
        
        table.add_row(
            flow,
            str(s["n"]),
            avg_score,
            score_range,
            label_str
        )

    console.print(table)

    # 详细统计
    console.print("\n[bold]详细统计：[/]")
    total_cases = sum(s["n"] for s in stats.values())
    total_scored = sum(s["score_n"] for s in stats.values())
    
    console.print(f"总样本数：{total_cases}")
    console.print(f"已打分样本：{total_scored} ({total_scored/total_cases*100:.1f}%)")
    
    if total_scored > 0:
        all_scores = []
        for s in stats.values():
            all_scores.extend(s["scores"])
        overall_avg = sum(all_scores) / len(all_scores)
        console.print(f"整体平均分：{overall_avg:.2f}")

    # 标签汇总
    all_labels = defaultdict(int)
    for s in stats.values():
        for label, count in s["label_count"].items():
            all_labels[label] += count
    
    if all_labels:
        console.print(f"\n[bold]标签分布：[/]")
        for label, count in sorted(all_labels.items(), key=lambda x: x[1], reverse=True):
            pct = count / total_cases * 100
            console.print(f"  {label}: {count} ({pct:.1f}%)")


@app.command()
def export_filtered(
    infile: str = typer.Option(..., help="人工打分后的文件"),
    outfile: str = typer.Option("filtered_review.csv", help="输出过滤后的文件"),
    min_score: float = typer.Option(None, help="最低分数过滤"),
    max_score: float = typer.Option(None, help="最高分数过滤"),
    labels: str = typer.Option(None, help="标签过滤，逗号分隔，如 'good,edge'"),
    flows: str = typer.Option(None, help="flow 过滤，逗号分隔"),
):
    """导出过滤后的评审数据"""
    in_path = DATA_DIR / infile
    out_path = DATA_DIR / outfile

    with open(in_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        console.print("[yellow]没有数据可过滤[/]")
        raise typer.Exit()

    # 解析过滤条件
    label_filter = set(labels.split(",")) if labels else None
    flow_filter = set(flows.split(",")) if flows else None

    filtered_rows = []
    for r in rows:
        # 分数过滤
        if min_score is not None or max_score is not None:
            try:
                score = float(r.get("human_score", ""))
                if min_score is not None and score < min_score:
                    continue
                if max_score is not None and score > max_score:
                    continue
            except (ValueError, TypeError):
                continue  # 跳过无效分数

        # 标签过滤
        if label_filter:
            label = (r.get("human_label", "") or "").strip()
            if label not in label_filter:
                continue

        # flow 过滤
        if flow_filter:
            flow = r.get("flow", "")
            if flow not in flow_filter:
                continue

        filtered_rows.append(r)

    # 写入过滤结果
    if filtered_rows:
        with open(out_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(filtered_rows)
        
        console.print(f"[green]已导出 {len(filtered_rows)} 条过滤结果到：[/] {out_path}")
    else:
        console.print("[yellow]没有符合条件的数据[/]")


if __name__ == "__main__":
    app()