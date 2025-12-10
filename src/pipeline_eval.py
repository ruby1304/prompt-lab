# src/pipeline_eval.py
"""
Pipeline 评估和比较系统

实现 PipelineEvaluator 类处理 pipeline 级别的评估，
支持多变体比较和集成现有的规则评估和 LLM judge 逻辑。
"""

from __future__ import annotations

import csv
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .models import (
    PipelineConfig, EvaluationResult, ComparisonReport, RegressionCase
)
from .pipeline_runner import PipelineRunner, PipelineResult
from .agent_registry import load_agent
from .eval_rules import apply_rules_to_row
from .eval_llm_judge import judge_one, build_judge_chain
from .data_manager import get_pipeline_evals_dir, get_pipeline_runs_dir
from .paths import ensure_pipeline_dirs

logger = logging.getLogger(__name__)


@dataclass
class PipelineEvaluationResult:
    """Pipeline 评估结果"""
    pipeline_id: str
    variant: str
    sample_results: List[EvaluationResult] = field(default_factory=list)
    overall_stats: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "pipeline_id": self.pipeline_id,
            "variant": self.variant,
            "sample_results": [result.to_dict() for result in self.sample_results],
            "overall_stats": self.overall_stats,
            "execution_time": self.execution_time,
            "created_at": self.created_at.isoformat()
        }


class PipelineEvaluator:
    """Pipeline 评估器"""
    
    def __init__(self, pipeline_config: PipelineConfig):
        """
        初始化 Pipeline 评估器
        
        Args:
            pipeline_config: Pipeline 配置对象
        """
        self.config = pipeline_config
        self.runner = PipelineRunner(pipeline_config)
        
        # 确保数据目录存在
        ensure_pipeline_dirs(pipeline_config.id)
        
        # 进度回调
        self.progress_callback: Optional[callable] = None
    
    def set_progress_callback(self, callback: callable):
        """设置进度回调函数"""
        self.progress_callback = callback
        self.runner.set_progress_callback(callback)
    
    def evaluate_pipeline(
        self,
        samples: List[Dict[str, Any]],
        variant: str = "baseline",
        apply_rules: bool = True,
        apply_judge: bool = True,
        judge_agent_id: Optional[str] = None,
        judge_flow: Optional[str] = None,
        limit: int = 0
    ) -> PipelineEvaluationResult:
        """
        评估单个 pipeline 变体
        
        Args:
            samples: 测试样本列表
            variant: 变体名称
            apply_rules: 是否应用规则评估
            apply_judge: 是否应用 LLM judge 评估
            judge_agent_id: Judge agent ID（可选）
            judge_flow: Judge flow 名称（可选）
            limit: 限制评估样本数量（0表示全部）
            
        Returns:
            Pipeline 评估结果
        """
        start_time = time.time()
        
        if limit > 0:
            samples = samples[:limit]
        
        logger.info(f"开始评估 Pipeline: {self.config.name}")
        logger.info(f"变体: {variant}")
        logger.info(f"样本数量: {len(samples)}")
        logger.info(f"规则评估: {'启用' if apply_rules else '禁用'}")
        logger.info(f"Judge 评估: {'启用' if apply_judge else '禁用'}")
        
        # 执行 pipeline
        pipeline_results = self.runner.execute(samples, variant)
        
        # 准备评估结果
        evaluation_results = []
        
        # 获取最终步骤的 agent 配置（用于规则和 judge 评估）
        final_step = self.config.steps[-1] if self.config.steps else None
        final_agent = None
        judge_chain = None
        
        if final_step and (apply_rules or apply_judge):
            try:
                final_agent = load_agent(final_step.agent)
                
                # 构建 judge chain（如果需要）
                if apply_judge:
                    eval_cfg = final_agent.evaluation or {}
                    judge_agent_id = judge_agent_id or eval_cfg.get("judge_agent_id", "judge_default")
                    judge_flow = judge_flow or eval_cfg.get("judge_flow", "judge_v1")
                    
                    try:
                        judge_agent = load_agent(judge_agent_id)
                        judge_chain = build_judge_chain(final_agent, judge_agent, judge_flow)
                        logger.info(f"使用 Judge: {judge_agent_id}/{judge_flow}")
                    except Exception as e:
                        logger.warning(f"构建 Judge chain 失败: {e}")
                        apply_judge = False
                        
            except Exception as e:
                logger.warning(f"加载最终步骤 agent 失败: {e}")
                apply_rules = False
                apply_judge = False
        
        # 处理每个样本的评估
        for i, (sample, pipeline_result) in enumerate(zip(samples, pipeline_results)):
            sample_id = sample.get("id", f"sample_{i}")
            
            if self.progress_callback:
                self.progress_callback(i, len(samples), f"正在评估样本: {sample_id}")
            
            # 如果 pipeline 执行失败，创建失败的评估结果
            if pipeline_result.error:
                eval_result = EvaluationResult(
                    sample_id=sample_id,
                    variant=variant,
                    overall_score=0.0,
                    must_have_pass=False,
                    judge_feedback=f"Pipeline 执行失败: {pipeline_result.error}"
                )
                evaluation_results.append(eval_result)
                continue
            
            # 获取最终输出
            final_output = ""
            if pipeline_result.final_outputs:
                # 使用第一个输出作为评估对象
                final_output = str(list(pipeline_result.final_outputs.values())[0])
            
            # 初始化评估结果
            eval_result = EvaluationResult(
                sample_id=sample_id,
                variant=variant,
                overall_score=0.0,
                must_have_pass=True,
                execution_time=pipeline_result.total_execution_time,
                step_outputs=pipeline_result.final_outputs
            )
            
            # 应用规则评估
            if apply_rules and final_agent:
                try:
                    rule_result = apply_rules_to_row(
                        final_agent, 
                        {"output": final_output}, 
                        "output"
                    )
                    eval_result.must_have_pass = bool(rule_result.get("rule_pass", 1))
                    rule_violations = rule_result.get("rule_violations", "")
                    if rule_violations:
                        eval_result.rule_violations = [v.strip() for v in rule_violations.split(",") if v.strip()]
                except Exception as e:
                    logger.warning(f"样本 {sample_id} 规则评估失败: {e}")
            
            # 应用 LLM judge 评估
            if apply_judge and judge_chain and final_agent:
                try:
                    judge_data, token_info = judge_one(
                        task_agent_cfg=final_agent,
                        flow_name=final_step.flow,
                        case=sample,
                        output=final_output,
                        judge_chain=judge_chain
                    )
                    
                    eval_result.overall_score = float(judge_data.get("overall_score", 0.0))
                    eval_result.judge_feedback = judge_data.get("overall_comment", "")
                    
                    # 检查 must_have 要求
                    must_have_checks = judge_data.get("must_have_check", [])
                    if must_have_checks:
                        eval_result.must_have_pass = all(
                            check.get("satisfied", False) for check in must_have_checks
                        )
                    
                except Exception as e:
                    logger.warning(f"样本 {sample_id} Judge 评估失败: {e}")
                    eval_result.judge_feedback = f"Judge 评估失败: {str(e)}"
            
            evaluation_results.append(eval_result)
        
        # 计算整体统计
        overall_stats = self._calculate_overall_stats(evaluation_results)
        
        execution_time = time.time() - start_time
        
        result = PipelineEvaluationResult(
            pipeline_id=self.config.id,
            variant=variant,
            sample_results=evaluation_results,
            overall_stats=overall_stats,
            execution_time=execution_time
        )
        
        logger.info(f"Pipeline 评估完成，耗时 {execution_time:.2f} 秒")
        logger.info(f"整体统计: {overall_stats}")
        
        return result
    
    def _calculate_overall_stats(self, results: List[EvaluationResult]) -> Dict[str, Any]:
        """计算整体统计信息"""
        if not results:
            return {}
        
        total_samples = len(results)
        successful_samples = len([r for r in results if not r.judge_feedback.startswith("Pipeline 执行失败")])
        
        # 分数统计
        scores = [r.overall_score for r in results if r.overall_score > 0]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        
        # Must-have 通过率
        must_have_passed = len([r for r in results if r.must_have_pass])
        must_have_pass_rate = must_have_passed / total_samples if total_samples > 0 else 0.0
        
        # 规则违规统计
        rule_violations = {}
        for result in results:
            for violation in result.rule_violations:
                rule_violations[violation] = rule_violations.get(violation, 0) + 1
        
        # 执行时间统计
        execution_times = [r.execution_time for r in results if r.execution_time > 0]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0.0
        
        return {
            "total_samples": total_samples,
            "successful_samples": successful_samples,
            "success_rate": successful_samples / total_samples if total_samples > 0 else 0.0,
            "average_score": avg_score,
            "must_have_pass_rate": must_have_pass_rate,
            "rule_violations": rule_violations,
            "average_execution_time": avg_execution_time
        }
    
    def save_evaluation_results(
        self,
        results: PipelineEvaluationResult,
        filename: Optional[str] = None
    ) -> Path:
        """
        保存评估结果到文件
        
        Args:
            results: 评估结果
            filename: 文件名（可选，自动生成）
            
        Returns:
            保存的文件路径
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            filename = f"{self.config.id}_{results.variant}_{timestamp}.eval.csv"
        
        evals_dir = get_pipeline_evals_dir(self.config.id)
        file_path = evals_dir / filename
        
        # 准备 CSV 数据
        csv_rows = []
        for result in results.sample_results:
            row = {
                "id": result.sample_id,
                "variant": result.variant,
                "overall_score": result.overall_score,
                "must_have_pass": int(result.must_have_pass),
                "rule_violations": ",".join(result.rule_violations),
                "judge_feedback": result.judge_feedback,
                "execution_time": result.execution_time
            }
            
            # 添加步骤输出
            for key, value in result.step_outputs.items():
                row[f"output__{key}"] = str(value)
            
            csv_rows.append(row)
        
        # 写入 CSV 文件
        if csv_rows:
            fieldnames = list(csv_rows[0].keys())
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_rows)
        
        logger.info(f"评估结果已保存到: {file_path}")
        return file_path


@dataclass
class VariantComparisonResult:
    """变体比较结果"""
    baseline_variant: str
    comparison_variant: str
    sample_comparisons: List[Dict[str, Any]] = field(default_factory=list)
    overall_comparison: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "baseline_variant": self.baseline_variant,
            "comparison_variant": self.comparison_variant,
            "sample_comparisons": self.sample_comparisons,
            "overall_comparison": self.overall_comparison,
            "created_at": self.created_at.isoformat()
        }


class PipelineComparator:
    """Pipeline 比较器"""
    
    def __init__(self, pipeline_config: PipelineConfig):
        """
        初始化 Pipeline 比较器
        
        Args:
            pipeline_config: Pipeline 配置对象
        """
        self.config = pipeline_config
        self.evaluator = PipelineEvaluator(pipeline_config)
        self.progress_callback: Optional[callable] = None
    
    def set_progress_callback(self, callback: callable):
        """设置进度回调函数"""
        self.progress_callback = callback
        self.evaluator.set_progress_callback(callback)
    
    def compare_variants(
        self,
        samples: List[Dict[str, Any]],
        variants: List[str],
        apply_rules: bool = True,
        apply_judge: bool = True,
        parallel: bool = True,
        max_workers: int = 2,
        limit: int = 0
    ) -> Dict[str, PipelineEvaluationResult]:
        """
        比较多个 pipeline 变体
        
        Args:
            samples: 测试样本列表
            variants: 变体名称列表
            apply_rules: 是否应用规则评估
            apply_judge: 是否应用 LLM judge 评估
            parallel: 是否并行执行
            max_workers: 最大并行工作线程数
            limit: 限制评估样本数量（0表示全部）
            
        Returns:
            变体评估结果字典
        """
        logger.info(f"开始比较 Pipeline 变体: {variants}")
        
        results = {}
        
        if parallel and len(variants) > 1:
            # 并行执行
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_variant = {
                    executor.submit(
                        self.evaluator.evaluate_pipeline,
                        samples, variant, apply_rules, apply_judge, None, None, limit
                    ): variant
                    for variant in variants
                }
                
                for future in as_completed(future_to_variant):
                    variant = future_to_variant[future]
                    try:
                        result = future.result()
                        results[variant] = result
                        logger.info(f"变体 {variant} 评估完成")
                    except Exception as e:
                        logger.error(f"变体 {variant} 评估失败: {e}")
        else:
            # 串行执行
            for variant in variants:
                try:
                    result = self.evaluator.evaluate_pipeline(
                        samples, variant, apply_rules, apply_judge, None, None, limit
                    )
                    results[variant] = result
                    logger.info(f"变体 {variant} 评估完成")
                except Exception as e:
                    logger.error(f"变体 {variant} 评估失败: {e}")
        
        return results
    
    def save_comparison_results(
        self,
        results: Dict[str, PipelineEvaluationResult],
        filename: Optional[str] = None
    ) -> Path:
        """
        保存比较结果到文件
        
        Args:
            results: 变体评估结果字典
            filename: 文件名（可选，自动生成）
            
        Returns:
            保存的文件路径
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            variant_names = "_".join(sorted(results.keys()))
            filename = f"{self.config.id}_compare_{variant_names}_{timestamp}.csv"
        
        runs_dir = get_pipeline_runs_dir(self.config.id)
        file_path = runs_dir / filename
        
        # 准备比较数据
        if not results:
            logger.warning("没有评估结果可保存")
            return file_path
        
        # 获取所有样本ID
        all_sample_ids = set()
        for result in results.values():
            for sample_result in result.sample_results:
                all_sample_ids.add(sample_result.sample_id)
        
        # 构建比较表格
        csv_rows = []
        for sample_id in sorted(all_sample_ids):
            row = {"id": sample_id}
            
            # 为每个变体添加列
            for variant in sorted(results.keys()):
                result = results[variant]
                sample_result = None
                
                # 查找对应的样本结果
                for sr in result.sample_results:
                    if sr.sample_id == sample_id:
                        sample_result = sr
                        break
                
                if sample_result:
                    row[f"score__{variant}"] = sample_result.overall_score
                    row[f"must_have__{variant}"] = int(sample_result.must_have_pass)
                    row[f"rule_violations__{variant}"] = ",".join(sample_result.rule_violations)
                    row[f"judge_feedback__{variant}"] = sample_result.judge_feedback
                    
                    # 添加步骤输出
                    for key, value in sample_result.step_outputs.items():
                        row[f"output__{variant}__{key}"] = str(value)
                else:
                    row[f"score__{variant}"] = 0.0
                    row[f"must_have__{variant}"] = 0
                    row[f"rule_violations__{variant}"] = ""
                    row[f"judge_feedback__{variant}"] = "未找到结果"
            
            csv_rows.append(row)
        
        # 写入 CSV 文件
        if csv_rows:
            fieldnames = list(csv_rows[0].keys())
            with open(file_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(csv_rows)
        
        logger.info(f"比较结果已保存到: {file_path}")
        return file_path
    
    def analyze_variant_differences(
        self,
        baseline_result: PipelineEvaluationResult,
        comparison_result: PipelineEvaluationResult
    ) -> VariantComparisonResult:
        """
        分析两个变体之间的差异
        
        Args:
            baseline_result: 基线变体评估结果
            comparison_result: 比较变体评估结果
            
        Returns:
            变体比较结果
        """
        logger.info(f"分析变体差异: {baseline_result.variant} vs {comparison_result.variant}")
        
        # 创建样本ID到结果的映射
        baseline_map = {r.sample_id: r for r in baseline_result.sample_results}
        comparison_map = {r.sample_id: r for r in comparison_result.sample_results}
        
        # 获取共同的样本ID
        common_sample_ids = set(baseline_map.keys()) & set(comparison_map.keys())
        
        sample_comparisons = []
        score_deltas = []
        must_have_changes = []
        
        for sample_id in sorted(common_sample_ids):
            baseline_sample = baseline_map[sample_id]
            comparison_sample = comparison_map[sample_id]
            
            score_delta = comparison_sample.overall_score - baseline_sample.overall_score
            score_deltas.append(score_delta)
            
            must_have_change = int(comparison_sample.must_have_pass) - int(baseline_sample.must_have_pass)
            must_have_changes.append(must_have_change)
            
            sample_comparison = {
                "sample_id": sample_id,
                "baseline_score": baseline_sample.overall_score,
                "comparison_score": comparison_sample.overall_score,
                "score_delta": score_delta,
                "baseline_must_have": baseline_sample.must_have_pass,
                "comparison_must_have": comparison_sample.must_have_pass,
                "must_have_change": must_have_change,
                "baseline_violations": baseline_sample.rule_violations,
                "comparison_violations": comparison_sample.rule_violations,
                "baseline_feedback": baseline_sample.judge_feedback,
                "comparison_feedback": comparison_sample.judge_feedback
            }
            sample_comparisons.append(sample_comparison)
        
        # 计算整体比较统计
        overall_comparison = {
            "total_samples": len(common_sample_ids),
            "average_score_delta": sum(score_deltas) / len(score_deltas) if score_deltas else 0.0,
            "score_improvement_count": len([d for d in score_deltas if d > 0]),
            "score_degradation_count": len([d for d in score_deltas if d < 0]),
            "score_unchanged_count": len([d for d in score_deltas if d == 0]),
            "must_have_improvement_count": len([c for c in must_have_changes if c > 0]),
            "must_have_degradation_count": len([c for c in must_have_changes if c < 0]),
            "must_have_unchanged_count": len([c for c in must_have_changes if c == 0]),
            "baseline_stats": baseline_result.overall_stats,
            "comparison_stats": comparison_result.overall_stats
        }
        
        # 找出最大的改进和退化案例
        if sample_comparisons:
            best_improvement = max(sample_comparisons, key=lambda x: x["score_delta"])
            worst_degradation = min(sample_comparisons, key=lambda x: x["score_delta"])
            
            overall_comparison["best_improvement"] = best_improvement
            overall_comparison["worst_degradation"] = worst_degradation
        
        return VariantComparisonResult(
            baseline_variant=baseline_result.variant,
            comparison_variant=comparison_result.variant,
            sample_comparisons=sample_comparisons,
            overall_comparison=overall_comparison
        )
    
    def generate_comparison_summary(
        self,
        comparison_result: VariantComparisonResult
    ) -> str:
        """
        生成比较结果的中文摘要
        
        Args:
            comparison_result: 变体比较结果
            
        Returns:
            中文摘要文本
        """
        stats = comparison_result.overall_comparison
        baseline = comparison_result.baseline_variant
        comparison = comparison_result.comparison_variant
        
        summary_lines = [
            f"# Pipeline 变体比较报告",
            f"",
            f"**基线变体**: {baseline}",
            f"**比较变体**: {comparison}",
            f"**比较时间**: {comparison_result.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"## 整体统计",
            f"- 总样本数: {stats['total_samples']}",
            f"- 平均分数变化: {stats['average_score_delta']:.3f}",
            f"- 分数提升样本: {stats['score_improvement_count']} ({stats['score_improvement_count']/stats['total_samples']*100:.1f}%)",
            f"- 分数下降样本: {stats['score_degradation_count']} ({stats['score_degradation_count']/stats['total_samples']*100:.1f}%)",
            f"- 分数不变样本: {stats['score_unchanged_count']} ({stats['score_unchanged_count']/stats['total_samples']*100:.1f}%)",
            f"",
            f"## Must-Have 要求变化",
            f"- 改进样本: {stats['must_have_improvement_count']}",
            f"- 退化样本: {stats['must_have_degradation_count']}",
            f"- 不变样本: {stats['must_have_unchanged_count']}",
            f""
        ]
        
        # 添加最佳改进和最差退化案例
        if "best_improvement" in stats and stats["best_improvement"]["score_delta"] > 0:
            best = stats["best_improvement"]
            summary_lines.extend([
                f"## 最佳改进案例",
                f"- 样本ID: {best['sample_id']}",
                f"- 分数变化: {best['baseline_score']:.2f} → {best['comparison_score']:.2f} (+{best['score_delta']:.2f})",
                f"- Must-Have: {'通过' if best['baseline_must_have'] else '失败'} → {'通过' if best['comparison_must_have'] else '失败'}",
                f""
            ])
        
        if "worst_degradation" in stats and stats["worst_degradation"]["score_delta"] < 0:
            worst = stats["worst_degradation"]
            summary_lines.extend([
                f"## 最严重退化案例",
                f"- 样本ID: {worst['sample_id']}",
                f"- 分数变化: {worst['baseline_score']:.2f} → {worst['comparison_score']:.2f} ({worst['score_delta']:.2f})",
                f"- Must-Have: {'通过' if worst['baseline_must_have'] else '失败'} → {'通过' if worst['comparison_must_have'] else '失败'}",
                f""
            ])
        
        # 添加基线和比较变体的整体统计
        baseline_stats = stats.get("baseline_stats", {})
        comparison_stats = stats.get("comparison_stats", {})
        
        if baseline_stats and comparison_stats:
            summary_lines.extend([
                f"## 变体整体性能对比",
                f"",
                f"### {baseline} (基线)",
                f"- 平均分数: {baseline_stats.get('average_score', 0):.2f}",
                f"- Must-Have 通过率: {baseline_stats.get('must_have_pass_rate', 0)*100:.1f}%",
                f"- 成功率: {baseline_stats.get('success_rate', 0)*100:.1f}%",
                f"",
                f"### {comparison} (比较)",
                f"- 平均分数: {comparison_stats.get('average_score', 0):.2f}",
                f"- Must-Have 通过率: {comparison_stats.get('must_have_pass_rate', 0)*100:.1f}%",
                f"- 成功率: {comparison_stats.get('success_rate', 0)*100:.1f}%",
                f""
            ])
        
        return "\n".join(summary_lines)


class ComparisonEngine:
    """比较结果分析引擎"""
    
    def __init__(self):
        """初始化比较引擎"""
        pass
    
    def analyze_score_distribution(
        self,
        results: List[EvaluationResult]
    ) -> Dict[str, Any]:
        """
        分析分数分布
        
        Args:
            results: 评估结果列表
            
        Returns:
            分数分布统计
        """
        scores = [r.overall_score for r in results if r.overall_score > 0]
        
        if not scores:
            return {"error": "没有有效分数数据"}
        
        scores.sort()
        n = len(scores)
        
        return {
            "count": n,
            "min": min(scores),
            "max": max(scores),
            "mean": sum(scores) / n,
            "median": scores[n // 2] if n % 2 == 1 else (scores[n // 2 - 1] + scores[n // 2]) / 2,
            "q1": scores[n // 4],
            "q3": scores[3 * n // 4],
            "std": self._calculate_std(scores),
            "score_ranges": self._analyze_score_ranges(scores)
        }
    
    def analyze_must_have_performance(
        self,
        results: List[EvaluationResult]
    ) -> Dict[str, Any]:
        """
        分析 must_have 要求通过情况
        
        Args:
            results: 评估结果列表
            
        Returns:
            Must-have 性能统计
        """
        total = len(results)
        passed = len([r for r in results if r.must_have_pass])
        failed = total - passed
        
        # 分析失败原因（规则违规）
        failure_reasons = {}
        for result in results:
            if not result.must_have_pass:
                for violation in result.rule_violations:
                    failure_reasons[violation] = failure_reasons.get(violation, 0) + 1
        
        return {
            "total_samples": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0.0,
            "failure_reasons": failure_reasons
        }
    
    def analyze_tag_performance(
        self,
        samples: List[Dict[str, Any]],
        results: List[EvaluationResult]
    ) -> Dict[str, Dict[str, Any]]:
        """
        按标签分析性能
        
        Args:
            samples: 原始样本数据
            results: 评估结果列表
            
        Returns:
            按标签分组的性能统计
        """
        # 创建样本ID到标签的映射
        sample_tags = {}
        for sample in samples:
            sample_id = sample.get("id", "")
            tags = sample.get("tags", [])
            if isinstance(tags, str):
                tags = [tags]
            sample_tags[sample_id] = tags
        
        # 按标签分组结果
        tag_results = {}
        for result in results:
            tags = sample_tags.get(result.sample_id, [])
            for tag in tags:
                if tag not in tag_results:
                    tag_results[tag] = []
                tag_results[tag].append(result)
        
        # 分析每个标签的性能
        tag_performance = {}
        for tag, tag_result_list in tag_results.items():
            tag_performance[tag] = {
                "sample_count": len(tag_result_list),
                "score_distribution": self.analyze_score_distribution(tag_result_list),
                "must_have_performance": self.analyze_must_have_performance(tag_result_list)
            }
        
        return tag_performance
    
    def detect_performance_regressions(
        self,
        baseline_results: List[EvaluationResult],
        comparison_results: List[EvaluationResult],
        score_threshold: float = 0.5,
        must_have_threshold: bool = True
    ) -> List[RegressionCase]:
        """
        检测性能回归案例
        
        Args:
            baseline_results: 基线评估结果
            comparison_results: 比较评估结果
            score_threshold: 分数下降阈值
            must_have_threshold: 是否检测 must_have 失败
            
        Returns:
            回归案例列表
        """
        # 创建样本ID到结果的映射
        baseline_map = {r.sample_id: r for r in baseline_results}
        comparison_map = {r.sample_id: r for r in comparison_results}
        
        regressions = []
        
        for sample_id in baseline_map:
            if sample_id not in comparison_map:
                continue
            
            baseline = baseline_map[sample_id]
            comparison = comparison_map[sample_id]
            
            score_delta = comparison.overall_score - baseline.overall_score
            
            # 检测分数回归
            if score_delta <= -score_threshold:
                severity = self._classify_regression_severity(score_delta)
                description = f"分数从 {baseline.overall_score:.2f} 下降到 {comparison.overall_score:.2f}"
                
                regressions.append(RegressionCase(
                    sample_id=sample_id,
                    baseline_score=baseline.overall_score,
                    variant_score=comparison.overall_score,
                    score_delta=score_delta,
                    severity=severity,
                    description=description
                ))
            
            # 检测 must_have 回归
            if must_have_threshold and baseline.must_have_pass and not comparison.must_have_pass:
                description = f"Must-have 要求从通过变为失败"
                if comparison.rule_violations:
                    description += f"，违规: {', '.join(comparison.rule_violations)}"
                
                regressions.append(RegressionCase(
                    sample_id=sample_id,
                    baseline_score=baseline.overall_score,
                    variant_score=comparison.overall_score,
                    score_delta=score_delta,
                    severity="critical",
                    description=description
                ))
        
        # 按严重程度和分数变化排序
        regressions.sort(key=lambda x: (
            {"critical": 0, "major": 1, "minor": 2}[x.severity],
            x.score_delta
        ))
        
        return regressions
    
    def generate_comprehensive_report(
        self,
        pipeline_id: str,
        baseline_results: PipelineEvaluationResult,
        comparison_results: List[PipelineEvaluationResult],
        samples: List[Dict[str, Any]]
    ) -> str:
        """
        生成综合比较报告
        
        Args:
            pipeline_id: Pipeline ID
            baseline_results: 基线评估结果
            comparison_results: 比较评估结果列表
            samples: 原始样本数据
            
        Returns:
            中文综合报告
        """
        report_lines = [
            f"# Pipeline 综合评估报告",
            f"",
            f"**Pipeline ID**: {pipeline_id}",
            f"**基线变体**: {baseline_results.variant}",
            f"**比较变体**: {', '.join([r.variant for r in comparison_results])}",
            f"**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**样本总数**: {len(samples)}",
            f"",
            f"## 基线性能概览",
            f""
        ]
        
        # 基线性能分析
        baseline_score_dist = self.analyze_score_distribution(baseline_results.sample_results)
        baseline_must_have = self.analyze_must_have_performance(baseline_results.sample_results)
        
        report_lines.extend([
            f"### 分数分布",
            f"- 平均分: {baseline_score_dist.get('mean', 0):.2f}",
            f"- 中位数: {baseline_score_dist.get('median', 0):.2f}",
            f"- 分数范围: {baseline_score_dist.get('min', 0):.2f} - {baseline_score_dist.get('max', 0):.2f}",
            f"",
            f"### Must-Have 要求",
            f"- 通过率: {baseline_must_have.get('pass_rate', 0)*100:.1f}%",
            f"- 通过样本: {baseline_must_have.get('passed', 0)}/{baseline_must_have.get('total_samples', 0)}",
            f""
        ])
        
        # 变体比较分析
        for comparison_result in comparison_results:
            report_lines.extend([
                f"## 变体比较: {comparison_result.variant}",
                f""
            ])
            
            # 检测回归
            regressions = self.detect_performance_regressions(
                baseline_results.sample_results,
                comparison_result.sample_results
            )
            
            if regressions:
                critical_regressions = [r for r in regressions if r.severity == "critical"]
                major_regressions = [r for r in regressions if r.severity == "major"]
                minor_regressions = [r for r in regressions if r.severity == "minor"]
                
                report_lines.extend([
                    f"### 回归检测结果",
                    f"- 严重回归: {len(critical_regressions)} 个",
                    f"- 重要回归: {len(major_regressions)} 个",
                    f"- 轻微回归: {len(minor_regressions)} 个",
                    f""
                ])
                
                # 列出前5个最严重的回归
                if regressions:
                    report_lines.extend([
                        f"### 最严重的回归案例 (前5个)",
                        f""
                    ])
                    
                    for i, regression in enumerate(regressions[:5], 1):
                        report_lines.extend([
                            f"{i}. **样本 {regression.sample_id}** ({regression.severity})",
                            f"   - 分数变化: {regression.baseline_score:.2f} → {regression.variant_score:.2f} ({regression.score_delta:.2f})",
                            f"   - 描述: {regression.description}",
                            f""
                        ])
            else:
                report_lines.extend([
                    f"### 回归检测结果",
                    f"✅ 未检测到显著回归",
                    f""
                ])
            
            # 性能对比
            comparison_score_dist = self.analyze_score_distribution(comparison_result.sample_results)
            comparison_must_have = self.analyze_must_have_performance(comparison_result.sample_results)
            
            score_improvement = comparison_score_dist.get('mean', 0) - baseline_score_dist.get('mean', 0)
            must_have_improvement = comparison_must_have.get('pass_rate', 0) - baseline_must_have.get('pass_rate', 0)
            
            report_lines.extend([
                f"### 性能对比",
                f"- 平均分变化: {score_improvement:+.3f}",
                f"- Must-Have 通过率变化: {must_have_improvement*100:+.1f}%",
                f"- 当前平均分: {comparison_score_dist.get('mean', 0):.2f}",
                f"- 当前 Must-Have 通过率: {comparison_must_have.get('pass_rate', 0)*100:.1f}%",
                f""
            ])
        
        # 标签性能分析
        tag_performance = self.analyze_tag_performance(samples, baseline_results.sample_results)
        if tag_performance:
            report_lines.extend([
                f"## 按标签性能分析 (基于基线)",
                f""
            ])
            
            for tag, perf in tag_performance.items():
                score_dist = perf["score_distribution"]
                must_have_perf = perf["must_have_performance"]
                
                report_lines.extend([
                    f"### 标签: {tag}",
                    f"- 样本数: {perf['sample_count']}",
                    f"- 平均分: {score_dist.get('mean', 0):.2f}",
                    f"- Must-Have 通过率: {must_have_perf.get('pass_rate', 0)*100:.1f}%",
                    f""
                ])
        
        # 总结和建议
        report_lines.extend([
            f"## 总结和建议",
            f""
        ])
        
        # 基于分析结果生成建议
        total_regressions = sum(len(self.detect_performance_regressions(
            baseline_results.sample_results, comp.sample_results
        )) for comp in comparison_results)
        
        if total_regressions == 0:
            report_lines.append("✅ 所有变体都没有显著回归，可以考虑部署。")
        elif total_regressions <= 5:
            report_lines.append("⚠️ 检测到少量回归案例，建议仔细审查后决定是否部署。")
        else:
            report_lines.append("❌ 检测到较多回归案例，建议进一步优化后再考虑部署。")
        
        return "\n".join(report_lines)
    
    def _calculate_std(self, scores: List[float]) -> float:
        """计算标准差"""
        if len(scores) <= 1:
            return 0.0
        
        mean = sum(scores) / len(scores)
        variance = sum((x - mean) ** 2 for x in scores) / (len(scores) - 1)
        return variance ** 0.5
    
    def _analyze_score_ranges(self, scores: List[float]) -> Dict[str, int]:
        """分析分数范围分布"""
        ranges = {
            "0-2": 0, "2-4": 0, "4-6": 0, "6-8": 0, "8-10": 0
        }
        
        for score in scores:
            if score < 2:
                ranges["0-2"] += 1
            elif score < 4:
                ranges["2-4"] += 1
            elif score < 6:
                ranges["4-6"] += 1
            elif score < 8:
                ranges["6-8"] += 1
            else:
                ranges["8-10"] += 1
        
        return ranges
    
    def _classify_regression_severity(self, score_delta: float) -> str:
        """分类回归严重程度"""
        if score_delta <= -2.0:
            return "critical"
        elif score_delta <= -1.0:
            return "major"
        else:
            return "minor"


def create_pipeline_progress_printer(pipeline_name: str) -> callable:
    """创建 Pipeline 进度打印回调函数"""
    def print_progress(current: int, total: int, message: str = ""):
        percentage = (current / total) * 100 if total > 0 else 0
        print(f"\r正在评估 Pipeline: {pipeline_name} [{current}/{total}] {percentage:.1f}% {message}", end="", flush=True)
        if current == total:
            print()  # 完成时换行
    
    return print_progress