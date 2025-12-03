from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, Any, List

import typer
from rich.console import Console
from rich.table import Table

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from .agent_registry import load_agent
from .config import get_openai_model_name
from .chains import load_flow_config

console = Console()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"




# 移除 criteria 相关的构建函数，改为基于业务目标的评估


def render_case_for_judge(task_agent_cfg, case: Dict[str, Any]) -> str:
    """
    根据 TaskAgent 的 case_fields 配置，将任意结构的 case 渲染成 judge 可以理解的文本
    """
    eval_cfg = task_agent_cfg.evaluation or {}
    field_cfgs = eval_cfg.get("case_fields", [])
    
    # 如果没有配置 case_fields，回退到传统的 input/context 模式
    if not field_cfgs:
        return f"""=== 主要输入内容 ===
【输入】
{case.get('input', '')}

=== 相关上下文信息 ===
【上下文】
{case.get('context', '')}

=== 元信息 / 期望说明 ===
【期望说明】
{case.get('expected', '')}"""
    
    sections = {
        "primary_input": [],
        "context": [],
        "meta": [],
        "raw": [],
    }
    
    # 先映射显式字段
    for fc in field_cfgs:
        key = fc.get("key")
        label = fc.get("label", key)
        section = fc.get("section", "context")
        truncate = fc.get("truncate")
        as_json = fc.get("as_json", False)
        
        if key == "*":
            # raw JSON 模式
            value = json.dumps(case, ensure_ascii=False, indent=2)
        else:
            value = case.get(key, "")
        
        if not value and fc.get("required"):
            # 必填缺失，可以选择：直接报错 / 在文本里说明缺失
            value = "[MISSING]"
        
        if truncate and isinstance(value, str) and len(value) > truncate:
            value = value[:truncate] + "\n...[TRUNCATED]"
        
        if as_json and not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False, indent=2)
        
        sections.setdefault(section, []).append(f"【{label}】\n{value}\n")
    
    # 组装成一个大文本
    parts = []
    
    if sections["primary_input"]:
        parts.append("=== 主要输入内容 ===")
        parts.extend(sections["primary_input"])
    
    if sections["context"]:
        parts.append("=== 相关上下文信息 ===")
        parts.extend(sections["context"])
    
    if sections["meta"]:
        parts.append("=== 元信息 / 期望说明 ===")
        parts.extend(sections["meta"])
    
    if sections["raw"]:
        parts.append("=== 原始样本 JSON（如有需要可参考） ===")
        parts.extend(sections["raw"])
    
    return "\n".join(parts)


def build_judge_chain(task_agent_cfg, judge_agent_cfg, judge_flow_name: str):
    """构建 Judge Chain，使用 JudgeAgent 的 prompt 和 TaskAgent 的业务目标"""
    
    # 1. 读取 judge 的提示词
    flow_cfg = load_flow_config(judge_flow_name)
    system_prompt = flow_cfg["system_prompt"]
    user_template = flow_cfg["user_template"]
    
    # 2. 从 TaskAgent evaluation 里拿 scale
    eval_cfg = task_agent_cfg.evaluation or {}
    scale = eval_cfg.get("scale", {}) or {}
    min_score = scale.get("min", 0)
    max_score = scale.get("max", 10)
    
    # 3. 用 min_score/max_score 格式化 system_prompt
    system_prompt = system_prompt.format(
        min_score=min_score,
        max_score=max_score,
    )
    
    # 4. 组装 ChatPromptTemplate
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("user", user_template),
        ]
    )
    
    # 5. Judge 用自己的模型配置
    eval_model_name = eval_cfg.get("preferred_judge_model")
    model_name = judge_agent_cfg.model or eval_model_name or get_openai_model_name()
    temperature = judge_agent_cfg.temperature if judge_agent_cfg.temperature is not None else eval_cfg.get("temperature", 0.0)
    
    llm = ChatOpenAI(model=model_name, temperature=temperature)
    
    return prompt | llm


def judge_one(
    task_agent_cfg,
    flow_name: str,
    case: Dict[str, Any],
    output: str,
    judge_chain,
) -> tuple[Dict[str, Any], Dict[str, int]]:
    """对单个 (case, flow) 调用一次 Judge 模型，返回评估结果和token统计"""
    
    expectations = task_agent_cfg.expectations or {}
    must_have = "\n".join(expectations.get("must_have", []))
    nice_to_have = "\n".join(expectations.get("nice_to_have", []))
    
    # 使用新的 case 渲染功能
    case_rendered = render_case_for_judge(task_agent_cfg, case)
    
    variables = {
        "agent_id": task_agent_cfg.id,
        "agent_name": task_agent_cfg.name,
        "description": task_agent_cfg.description,
        "business_goal": task_agent_cfg.business_goal,
        "must_have": must_have,
        "nice_to_have": nice_to_have,
        "case_rendered": case_rendered,
        # 保留传统字段以兼容旧的 judge 提示词
        "input": case.get("input", ""),
        "context": case.get("context", ""),
        "expected": case.get("expected", ""),
        "output": output,
        "flow_name": flow_name,
    }
    
    resp = judge_chain.invoke(variables)
    content = resp.content
    
    # 提取token统计信息
    token_info = {}
    if hasattr(resp, 'usage_metadata') and resp.usage_metadata:
        usage = resp.usage_metadata
        token_info = {
            'input_tokens': usage.get('input_tokens', 0),
            'output_tokens': usage.get('output_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0)
        }
    elif hasattr(resp, 'response_metadata') and resp.response_metadata:
        usage = resp.response_metadata.get('token_usage', {})
        token_info = {
            'input_tokens': usage.get('prompt_tokens', 0),
            'output_tokens': usage.get('completion_tokens', 0),
            'total_tokens': usage.get('total_tokens', 0)
        }
    
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # 模型偶尔可能输出非纯 JSON，这里可以再简单兜一层，但先保持简单：
        raise ValueError(f"Judge 输出非 JSON：{content}")
    
    return data, token_info


def eval_file(
    agent: str = typer.Option(..., help="agent id，对应 agents/{agent}.yaml"),
    infile: str = typer.Option(
        ...,
        help="待评估的结果文件，一般是 results.compare.csv 或某个 run_batch 结果",
    ),
    outfile: str = typer.Option(
        "eval_results.csv",
        help="评估输出文件，默认 data/eval_results.csv",
    ),
    flows: str = typer.Option(
        "",
        help="可选：只评估这些 flow（逗号分隔），如: asr_clean_v1,asr_clean_v2；为空则自动从列名推断",
    ),
    limit: int = typer.Option(0, help="最多评估多少条（0=全部）"),
):
    """
    对已有结果文件做 LLM 自动评估。
    要求 infile 至少包含列：
    - id, input, context, expected
    - output__flow_name1, output__flow_name2, ...
    """
    # 加载 TaskAgent 和 JudgeAgent
    task_agent_cfg = load_agent(agent)
    console.rule(f"[bold blue]Eval · Agent {task_agent_cfg.id}[/bold blue]")
    
    # 获取 Judge 配置
    eval_cfg = task_agent_cfg.evaluation or {}
    judge_agent_id = eval_cfg.get("judge_agent_id", "judge_default")
    judge_flow = eval_cfg.get("judge_flow", "judge_v1")
    
    try:
        judge_agent_cfg = load_agent(judge_agent_id)
    except FileNotFoundError:
        console.print(f"[red]Judge Agent 不存在: {judge_agent_id}[/red]")
        raise typer.Exit(1)
    
    console.print(f"[bold]Judge Agent[/]: {judge_agent_cfg.name} ({judge_agent_id})")
    console.print(f"[bold]Judge Flow[/]: {judge_flow}")
    
    in_path = DATA_DIR / infile
    out_path = DATA_DIR / outfile
    
    console.print(f"[bold]Input file[/]: {in_path}")
    console.print(f"[bold]Output file[/]: {out_path}")
    
    # 读取结果文件
    with open(in_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    if limit > 0:
        rows = rows[:limit]
    
    if not rows:
        console.print("[yellow]没有数据可评估。[/]")
        raise typer.Exit()
    
    # 确定要评估的 flow 列
    all_cols = rows[0].keys()
    flow_cols = [c for c in all_cols if c.startswith("output__")]
    
    if flows:
        specified = [x.strip() for x in flows.split(",") if x.strip()]
        flow_cols = [f"output__{name}" for name in specified if f"output__{name}" in flow_cols]
    
    if not flow_cols:
        console.print("[red]未找到要评估的 flow 输出列，请检查文件或 --flows 参数。[/red]")
        raise typer.Exit()
    
    console.print(f"[bold]Flows to evaluate[/]: {', '.join(flow_cols)}")
    
    # 构建 Judge Chain
    judge_chain = build_judge_chain(
        task_agent_cfg=task_agent_cfg,
        judge_agent_cfg=judge_agent_cfg,
        judge_flow_name=judge_flow,
    )
    
    # 输出字段：id / flow / overall_score / overall_comment / each criteria score/comment
    eval_rows: List[Dict[str, Any]] = []
    total_tokens = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
    
    for idx, row in enumerate(rows, start=1):
        console.print(f"[{idx}/{len(rows)}] id={row.get('id')}")
        
        case_base = {
            "id": row.get("id"),
            "input": row.get("input", ""),
            "context": row.get("context", ""),
            "expected": row.get("expected", ""),
        }
        
        for col in flow_cols:
            flow_name = col.replace("output__", "")
            output = row.get(col, "")
            
            if not output:
                continue
            
            console.print(f"  -> judging flow: [cyan]{flow_name}[/cyan]")
            judge_data, token_info = judge_one(
                task_agent_cfg=task_agent_cfg,
                flow_name=flow_name,
                case=case_base,
                output=output,
                judge_chain=judge_chain,
            )
            
            # 累计token统计
            for key in total_tokens:
                total_tokens[key] += token_info.get(key, 0)
            
            console.print(f"    tokens: {token_info.get('input_tokens', 0)} input + {token_info.get('output_tokens', 0)} output = {token_info.get('total_tokens', 0)} total")
            
            # 展平 JSON 方便 CSV 存储
            flat: Dict[str, Any] = {
                "id": case_base["id"],
                "flow": flow_name,
                "overall_score": judge_data.get("overall_score"),
                "overall_comment": judge_data.get("overall_comment", ""),
                "judge_input_tokens": token_info.get("input_tokens", 0),
                "judge_output_tokens": token_info.get("output_tokens", 0),
                "judge_total_tokens": token_info.get("total_tokens", 0),
            }
            
            # must_have 检查结果展开
            for idx, check in enumerate(judge_data.get("must_have_check", [])):
                flat[f"must_have_{idx+1}__satisfied"] = check.get("satisfied")
                flat[f"must_have_{idx+1}__score"] = check.get("score")
                flat[f"must_have_{idx+1}__comment"] = check.get("comment", "")
            
            # nice_to_have 检查结果展开
            for idx, check in enumerate(judge_data.get("nice_to_have_check", [])):
                flat[f"nice_to_have_{idx+1}__satisfied"] = check.get("satisfied")
                flat[f"nice_to_have_{idx+1}__score"] = check.get("score")
                flat[f"nice_to_have_{idx+1}__comment"] = check.get("comment", "")
            
            # summary_quality_check 检查结果展开（如果存在）
            for idx, check in enumerate(judge_data.get("summary_quality_check", [])):
                aspect = check.get("aspect", f"quality_{idx+1}")
                flat[f"quality__{aspect}__satisfied"] = check.get("satisfied")
                flat[f"quality__{aspect}__score"] = check.get("score")
                flat[f"quality__{aspect}__comment"] = check.get("comment", "")
            
            # derived_criteria 展开（用于分析评估模型的推理过程）
            for idx, criteria in enumerate(judge_data.get("derived_criteria", [])):
                flat[f"derived_criteria_{idx+1}__name"] = criteria.get("name", "")
                flat[f"derived_criteria_{idx+1}__from"] = criteria.get("from", "")
                flat[f"derived_criteria_{idx+1}__importance"] = criteria.get("importance", "")
            
            eval_rows.append(flat)
    
    if not eval_rows:
        console.print("[yellow]没有任何评估结果生成。[/]")
        raise typer.Exit()
    
    # 写 CSV
    fieldnames = sorted(eval_rows[0].keys(), key=lambda x: (x not in ["id", "flow"], x))
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(eval_rows)
    
    console.print(f"[green]评估完成，结果已写入：[/] {out_path}")
    
    # 显示token统计汇总
    console.print(f"\n[bold]Token 使用统计：[/]")
    console.print(f"  输入 tokens: {total_tokens['input_tokens']:,}")
    console.print(f"  输出 tokens: {total_tokens['output_tokens']:,}")
    console.print(f"  总计 tokens: {total_tokens['total_tokens']:,}")
    
    # 简单预览
    table = Table(title="Eval Results Preview", show_lines=True)
    preview_cols = [c for c in fieldnames if c in ["id", "flow", "overall_score", "overall_comment", "judge_total_tokens"]]
    for col in preview_cols:
        table.add_column(col, overflow="fold")
    for r in eval_rows[:5]:
        table.add_row(*(str(r.get(c, "")) for c in preview_cols))
    console.print(table)


def main():
    typer.run(eval_file)

if __name__ == "__main__":
    main()