#!/usr/bin/env python3
"""
演示脚本：自动填写一些示例分数，模拟人工打分过程
"""
from __future__ import annotations

import csv
from pathlib import Path
import random

import typer
from rich.console import Console

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"

app = typer.Typer()
console = Console()


@app.command()
def fill_demo_scores(
    infile: str = typer.Option("mem0_l1_summarizer.manual_review.csv", help="人工评审文件"),
    outfile: str = typer.Option("mem0_l1_summarizer.manual_review.demo.csv", help="填写示例分数后的文件"),
):
    """填写一些示例分数，模拟人工打分"""
    in_path = DATA_DIR / infile
    out_path = DATA_DIR / outfile
    
    if not in_path.exists():
        console.print(f"[red]文件不存在: {in_path}[/]")
        raise typer.Exit(1)
    
    with open(in_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if not rows:
        console.print("[yellow]没有数据可处理[/]")
        raise typer.Exit()
    
    # 模拟人工打分逻辑
    demo_scores = []
    for row in rows:
        flow = row["flow"]
        output = row["output"]
        
        # 简单的评分逻辑（仅用于演示）
        if not output.strip():
            score = 0
            label = "bad"
            comment = "输出为空"
        elif len(output) < 50:
            score = random.randint(2, 4)
            label = "bad"
            comment = "输出过短"
        elif "用户画像" in output and len(output.split("用户画像")[1].strip()) < 10:
            score = random.randint(4, 6)
            label = "edge"
            comment = "用户画像部分不完整"
        elif flow == "mem0_l1_v1" and "###" in output:
            score = random.randint(7, 9)
            label = "good"
            comment = "结构清晰，内容完整"
        elif flow == "mem0_l1_v2":
            score = random.randint(6, 8)
            label = "good"
            comment = "简洁有效"
        elif flow == "mem0_l1_v3":
            score = random.randint(5, 7)
            label = "edge"
            comment = "内容合理但可能过于简化"
        else:
            score = random.randint(5, 8)
            label = "good"
            comment = "基本符合要求"
        
        row["human_score"] = str(score)
        row["human_label"] = label
        row["human_comment"] = comment
        demo_scores.append(row)
    
    # 写入结果
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerows(demo_scores)
    
    console.print(f"[green]已生成示例打分文件：[/] {out_path}")
    console.print(f"[blue]共填写 {len(demo_scores)} 条评分[/]")
    
    # 显示评分分布
    score_dist = {}
    label_dist = {}
    for row in demo_scores:
        score = row["human_score"]
        label = row["human_label"]
        score_dist[score] = score_dist.get(score, 0) + 1
        label_dist[label] = label_dist.get(label, 0) + 1
    
    console.print("\n[bold]评分分布：[/]")
    for score in sorted(score_dist.keys()):
        console.print(f"  {score} 分: {score_dist[score]} 条")
    
    console.print("\n[bold]标签分布：[/]")
    for label, count in sorted(label_dist.items()):
        console.print(f"  {label}: {count} 条")


if __name__ == "__main__":
    app()