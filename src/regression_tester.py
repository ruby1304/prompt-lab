# src/regression_tester.py
"""
回归测试执行器

处理回归测试工作流，比较新版本与 baseline 性能，
支持 pipeline 和 agent 级别的回归测试。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .baseline_manager import BaselineManager, BaselineSnapshot
from .pipeline_eval import PipelineEvaluator, PipelineComparator
from .models import (
    PipelineConfig, EvaluationResult, ComparisonReport, RegressionCase
)
from .pipeline_config import load_pipeline_config
from .agent_registry import load_agent
from .data_manager import DataManager
from .testset_filter import TestsetFilter

logger = logging.getLogger(__name__)


@dataclass
class RegressionTestConfig:
    """回归测试配置"""
    entity_type: str  # "agent" or "pipeline"
    entity_id: str
    baseline_name: str
    variant_name: str
    testset_path: Optional[str] = None
    include_tags: List[str] = field(default_factory=list)
    exclude_tags: List[str] = field(default_factory=list)
    score_threshold: float = 0.5  # 分数下降阈值
    must_have_check: bool = True  # 是否检查 must_have 失败
    apply_rules: bool = True
    apply_judge: bool = True
    limit: int = 0  # 限制样本数量，0表示全部
    
    def validate(self) -> List[str]:
        """验证配置"""
        errors = []
        
        if self.entity_type not in ["agent", "pipeline"]:
            errors.append(f"不支持的实体类型: {self.entity_type}")
        
        if not self.entity_id:
            errors.append("实体 ID 不能为空")
        
        if not self.baseline_name:
            errors.append("Baseline 名称不能为空")
        
        if not self.variant_name:
            errors.append("变体名称不能为空")
        
        if self.score_threshold < 0:
            errors.append("分数阈值不能为负数")
        
        return errors


@dataclass
class RegressionTestResult:
    """回归测试结果"""
    config: RegressionTestConfig
    baseline_snapshot: BaselineSnapshot
    variant_results: List[EvaluationResult]
    regression_cases: List[RegressionCase] = field(default_factory=list)
    comparison_report: Optional[ComparisonReport] = None
    summary: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "config": {
                "entity_type": self.config.entity_type,
                "entity_id": self.config.entity_id,
                "baseline_name": self.config.baseline_name,
                "variant_name": self.config.variant_name,
                "testset_path": self.config.testset_path,
                "include_tags": self.config.include_tags,
                "exclude_tags": self.config.exclude_tags,
                "score_threshold": self.config.score_threshold,
                "must_have_check": self.config.must_have_check
            },
            "baseline_snapshot": self.baseline_snapshot.to_dict(),
            "variant_results": [result.to_dict() for result in self.variant_results],
            "regression_cases": [case.to_dict() for case in self.regression_cases],
            "comparison_report": self.comparison_report.to_dict() if self.comparison_report else None,
            "summary": self.summary,
            "created_at": self.created_at.isoformat()
        }


class RegressionTester:
    """回归测试执行器"""
    
    def __init__(self, baseline_manager: Optional[BaselineManager] = None,
                 data_manager: Optional[DataManager] = None):
        """
        初始化回归测试器
        
        Args:
            baseline_manager: Baseline 管理器
            data_manager: 数据管理器
        """
        self.baseline_manager = baseline_manager or BaselineManager()
        self.data_manager = data_manager or DataManager()
        self.testset_filter = TestsetFilter()
        
        # 进度回调
        self.progress_callback: Optional[callable] = None
    
    def set_progress_callback(self, callback: callable):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def run_regression_test(self, config: RegressionTestConfig) -> RegressionTestResult:
        """
        运行回归测试
        
        Args:
            config: 回归测试配置
            
        Returns:
            回归测试结果
        """
        # 验证配置
        config_errors = config.validate()
        if config_errors:
            raise ValueError(f"回归测试配置错误: {', '.join(config_errors)}")
        
        logger.info(f"开始回归测试: {config.entity_type}/{config.entity_id}")
        logger.info(f"Baseline: {config.baseline_name}")
        logger.info(f"变体: {config.variant_name}")
        
        # 加载 baseline 快照
        baseline_snapshot = self.baseline_manager.load_baseline(
            config.entity_type, config.entity_id, config.baseline_name
        )
        
        if not baseline_snapshot:
            raise ValueError(f"未找到 baseline: {config.baseline_name}")
        
        logger.info(f"已加载 baseline 快照，创建时间: {baseline_snapshot.created_at}")
        
        # 加载测试集
        testset_samples = self._load_testset(config)
        logger.info(f"已加载测试集，样本数量: {len(testset_samples)}")
        
        # 执行变体评估
        if config.entity_type == "pipeline":
            variant_results = self._run_pipeline_variant_evaluation(config, testset_samples)
        else:
            variant_results = self._run_agent_variant_evaluation(config, testset_samples)
        
        logger.info(f"变体评估完成，结果数量: {len(variant_results)}")
        
        # 检测回归案例
        regression_cases = self._detect_regressions(
            baseline_snapshot, variant_results, config
        )
        
        logger.info(f"检测到 {len(regression_cases)} 个回归案例")
        
        # 生成比较报告
        comparison_report = self._generate_comparison_report(
            baseline_snapshot, variant_results, regression_cases, config
        )
        
        # 生成摘要
        summary = self._generate_regression_summary(
            baseline_snapshot, variant_results, regression_cases, config
        )
        
        result = RegressionTestResult(
            config=config,
            baseline_snapshot=baseline_snapshot,
            variant_results=variant_results,
            regression_cases=regression_cases,
            comparison_report=comparison_report,
            summary=summary
        )
        
        logger.info("回归测试完成")
        return result
    
    def _load_testset(self, config: RegressionTestConfig) -> List[Dict[str, Any]]:
        """加载测试集"""
        # 确定测试集路径
        if config.testset_path:
            testset_path = Path(config.testset_path)
        else:
            # 使用默认测试集路径
            testset_path = self.data_manager.find_testset_file(
                config.entity_type, config.entity_id, "regression.jsonl"
            )
            
            if not testset_path:
                # 尝试使用基础测试集
                testset_path = self.data_manager.find_testset_file(
                    config.entity_type, config.entity_id, "base.jsonl"
                )
        
        if not testset_path or not testset_path.exists():
            raise FileNotFoundError(f"未找到测试集文件: {config.testset_path or 'regression.jsonl/base.jsonl'}")
        
        # 加载样本
        samples = []
        with open(testset_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    sample = json.loads(line)
                    samples.append(sample)
                except json.JSONDecodeError as e:
                    logger.warning(f"跳过无效的 JSON 行 {line_num}: {e}")
        
        # 应用标签过滤
        if config.include_tags or config.exclude_tags:
            samples = self.testset_filter.filter_by_tags(
                samples, config.include_tags, config.exclude_tags
            )
        
        # 应用样本数量限制
        if config.limit > 0:
            samples = samples[:config.limit]
        
        return samples
    
    def _run_pipeline_variant_evaluation(
        self, config: RegressionTestConfig, samples: List[Dict[str, Any]]
    ) -> List[EvaluationResult]:
        """运行 pipeline 变体评估"""
        # 加载 pipeline 配置
        pipeline_config = load_pipeline_config(config.entity_id)
        if not pipeline_config:
            raise ValueError(f"未找到 pipeline 配置: {config.entity_id}")
        
        # 创建评估器
        evaluator = PipelineEvaluator(pipeline_config)
        if self.progress_callback:
            evaluator.set_progress_callback(self.progress_callback)
        
        # 执行评估
        evaluation_result = evaluator.evaluate_pipeline(
            samples=samples,
            variant=config.variant_name,
            apply_rules=config.apply_rules,
            apply_judge=config.apply_judge,
            limit=config.limit
        )
        
        return evaluation_result.sample_results
    
    def _run_agent_variant_evaluation(
        self, config: RegressionTestConfig, samples: List[Dict[str, Any]]
    ) -> List[EvaluationResult]:
        """运行 agent 变体评估"""
        # TODO: 实现 agent 级别的回归测试
        # 这里需要集成现有的 agent 评估逻辑
        raise NotImplementedError("Agent 级别的回归测试尚未实现")
    
    def _detect_regressions(
        self,
        baseline_snapshot: BaselineSnapshot,
        variant_results: List[EvaluationResult],
        config: RegressionTestConfig
    ) -> List[RegressionCase]:
        """检测回归案例"""
        regression_cases = []
        
        # 从 baseline 快照中提取评估结果
        baseline_results = {}
        for result_data in baseline_snapshot.evaluation_results:
            sample_id = result_data.get("sample_id", "")
            if sample_id:
                baseline_results[sample_id] = EvaluationResult.from_dict(result_data)
        
        # 计算整体统计信息用于相对阈值判断
        baseline_scores = [r.overall_score for r in baseline_results.values() if r.overall_score > 0]
        variant_scores = [r.overall_score for r in variant_results if r.overall_score > 0]
        
        baseline_avg = sum(baseline_scores) / len(baseline_scores) if baseline_scores else 0.0
        variant_avg = sum(variant_scores) / len(variant_scores) if variant_scores else 0.0
        
        # 计算分数标准差用于相对阈值
        baseline_std = self._calculate_std(baseline_scores) if len(baseline_scores) > 1 else 0.0
        
        # 比较每个样本的结果
        for variant_result in variant_results:
            sample_id = variant_result.sample_id
            
            if sample_id not in baseline_results:
                continue
            
            baseline_result = baseline_results[sample_id]
            
            # 检测各种类型的回归
            regression_info = self._analyze_sample_regression(
                baseline_result, variant_result, config, baseline_avg, baseline_std
            )
            
            if regression_info["is_regression"]:
                regression_case = RegressionCase(
                    sample_id=sample_id,
                    baseline_score=baseline_result.overall_score,
                    variant_score=variant_result.overall_score,
                    score_delta=regression_info["score_delta"],
                    severity=regression_info["severity"],
                    description=regression_info["description"]
                )
                regression_cases.append(regression_case)
        
        # 应用高级回归检测算法
        regression_cases = self._apply_advanced_regression_detection(
            regression_cases, baseline_results, variant_results, config
        )
        
        # 按严重程度和分数变化排序
        regression_cases = self._prioritize_regression_cases(regression_cases)
        
        return regression_cases
    
    def _analyze_sample_regression(
        self,
        baseline_result: EvaluationResult,
        variant_result: EvaluationResult,
        config: RegressionTestConfig,
        baseline_avg: float,
        baseline_std: float
    ) -> Dict[str, Any]:
        """分析单个样本的回归情况"""
        score_delta = variant_result.overall_score - baseline_result.overall_score
        
        # 检测 must_have 回归
        must_have_regression = (
            config.must_have_check and
            baseline_result.must_have_pass and
            not variant_result.must_have_pass
        )
        
        # 检测新的规则违规
        new_violations = set(variant_result.rule_violations) - set(baseline_result.rule_violations)
        
        # 检测执行时间显著增加
        execution_time_regression = False
        if (baseline_result.execution_time > 0 and variant_result.execution_time > 0):
            time_increase_ratio = variant_result.execution_time / baseline_result.execution_time
            execution_time_regression = time_increase_ratio > 2.0  # 执行时间增加超过100%
        
        # 判断是否为回归案例
        is_regression = False
        severity = "minor"
        description_parts = []
        
        # 1. 绝对分数阈值检测
        if score_delta <= -config.score_threshold:
            is_regression = True
            if score_delta <= -2.0:
                severity = "critical"
            elif score_delta <= -1.0:
                severity = "major"
            else:
                severity = "minor"
            
            description_parts.append(f"分数下降 {abs(score_delta):.2f}")
        
        # 2. 相对分数阈值检测（基于标准差）
        elif baseline_std > 0 and score_delta <= -2 * baseline_std:
            is_regression = True
            severity = "major" if score_delta <= -3 * baseline_std else "minor"
            description_parts.append(f"分数显著下降 {abs(score_delta):.2f} (>{2 if severity == 'minor' else 3}σ)")
        
        # 3. Must-have 回归检测
        if must_have_regression:
            is_regression = True
            severity = "critical"  # must_have 失败总是严重的
            description_parts.append("Must-have 要求失败")
        
        # 4. 新规则违规检测
        if new_violations:
            is_regression = True
            if severity == "minor":
                severity = "major"
            description_parts.append(f"新增规则违规: {', '.join(new_violations)}")
        
        # 5. 执行时间回归检测
        if execution_time_regression:
            is_regression = True
            if severity == "minor":
                severity = "major"
            time_increase = variant_result.execution_time - baseline_result.execution_time
            description_parts.append(f"执行时间显著增加 {time_increase:.2f}s")
        
        # 6. 高分样本的轻微下降也要关注
        if (baseline_result.overall_score >= 8.0 and 
            score_delta <= -0.2 and 
            not is_regression):
            is_regression = True
            severity = "minor"
            description_parts.append(f"高分样本轻微下降 {abs(score_delta):.2f}")
        
        return {
            "is_regression": is_regression,
            "severity": severity,
            "score_delta": score_delta,
            "description": "; ".join(description_parts) if description_parts else "未知回归",
            "must_have_regression": must_have_regression,
            "new_violations": list(new_violations),
            "execution_time_regression": execution_time_regression
        }
    
    def _apply_advanced_regression_detection(
        self,
        regression_cases: List[RegressionCase],
        baseline_results: Dict[str, EvaluationResult],
        variant_results: List[EvaluationResult],
        config: RegressionTestConfig
    ) -> List[RegressionCase]:
        """应用高级回归检测算法"""
        
        # 1. 检测系统性回归模式
        pattern_regressions = self._detect_systematic_regression_patterns(
            baseline_results, variant_results, config
        )
        
        # 2. 检测聚类回归（相似样本的集体回归）
        cluster_regressions = self._detect_cluster_regressions(
            baseline_results, variant_results, config
        )
        
        # 3. 检测边界案例回归
        edge_case_regressions = self._detect_edge_case_regressions(
            baseline_results, variant_results, config
        )
        
        # 合并所有检测到的回归案例
        all_regressions = regression_cases + pattern_regressions + cluster_regressions + edge_case_regressions
        
        # 去重（基于 sample_id）
        seen_samples = set()
        unique_regressions = []
        
        for regression in all_regressions:
            if regression.sample_id not in seen_samples:
                unique_regressions.append(regression)
                seen_samples.add(regression.sample_id)
            else:
                # 如果已存在，选择更严重的版本
                for i, existing in enumerate(unique_regressions):
                    if existing.sample_id == regression.sample_id:
                        if self._compare_severity(regression.severity, existing.severity) > 0:
                            unique_regressions[i] = regression
                        break
        
        return unique_regressions
    
    def _detect_systematic_regression_patterns(
        self,
        baseline_results: Dict[str, EvaluationResult],
        variant_results: List[EvaluationResult],
        config: RegressionTestConfig
    ) -> List[RegressionCase]:
        """检测系统性回归模式"""
        pattern_regressions = []
        
        # 检测整体性能下降
        baseline_scores = [r.overall_score for r in baseline_results.values() if r.overall_score > 0]
        variant_scores = [r.overall_score for r in variant_results if r.overall_score > 0]
        
        if baseline_scores and variant_scores:
            baseline_avg = sum(baseline_scores) / len(baseline_scores)
            variant_avg = sum(variant_scores) / len(variant_scores)
            overall_delta = variant_avg - baseline_avg
            
            # 如果整体性能下降超过阈值，标记所有下降的样本为系统性回归
            if overall_delta <= -config.score_threshold:
                variant_map = {r.sample_id: r for r in variant_results}
                
                for sample_id, baseline_result in baseline_results.items():
                    if sample_id in variant_map:
                        variant_result = variant_map[sample_id]
                        sample_delta = variant_result.overall_score - baseline_result.overall_score
                        
                        if sample_delta < 0:  # 只标记下降的样本
                            pattern_regressions.append(RegressionCase(
                                sample_id=sample_id,
                                baseline_score=baseline_result.overall_score,
                                variant_score=variant_result.overall_score,
                                score_delta=sample_delta,
                                severity="major",
                                description=f"系统性回归 (整体下降 {abs(overall_delta):.2f})"
                            ))
        
        return pattern_regressions
    
    def _detect_cluster_regressions(
        self,
        baseline_results: Dict[str, EvaluationResult],
        variant_results: List[EvaluationResult],
        config: RegressionTestConfig
    ) -> List[RegressionCase]:
        """检测聚类回归（相似样本的集体回归）"""
        cluster_regressions = []
        
        # 简化的聚类检测：基于规则违规模式
        variant_map = {r.sample_id: r for r in variant_results}
        
        # 按规则违规类型分组
        violation_groups = {}
        for sample_id, baseline_result in baseline_results.items():
            if sample_id in variant_map:
                variant_result = variant_map[sample_id]
                
                # 检查是否有新的违规
                new_violations = set(variant_result.rule_violations) - set(baseline_result.rule_violations)
                
                if new_violations:
                    for violation in new_violations:
                        if violation not in violation_groups:
                            violation_groups[violation] = []
                        violation_groups[violation].append((sample_id, baseline_result, variant_result))
        
        # 如果某种违规影响了多个样本，标记为聚类回归
        for violation, affected_samples in violation_groups.items():
            if len(affected_samples) >= 3:  # 至少3个样本受影响
                for sample_id, baseline_result, variant_result in affected_samples:
                    score_delta = variant_result.overall_score - baseline_result.overall_score
                    
                    cluster_regressions.append(RegressionCase(
                        sample_id=sample_id,
                        baseline_score=baseline_result.overall_score,
                        variant_score=variant_result.overall_score,
                        score_delta=score_delta,
                        severity="major",
                        description=f"聚类回归: {violation} (影响 {len(affected_samples)} 个样本)"
                    ))
        
        return cluster_regressions
    
    def _detect_edge_case_regressions(
        self,
        baseline_results: Dict[str, EvaluationResult],
        variant_results: List[EvaluationResult],
        config: RegressionTestConfig
    ) -> List[RegressionCase]:
        """检测边界案例回归"""
        edge_case_regressions = []
        
        variant_map = {r.sample_id: r for r in variant_results}
        
        # 检测原本表现很好但现在失败的案例
        for sample_id, baseline_result in baseline_results.items():
            if sample_id in variant_map:
                variant_result = variant_map[sample_id]
                
                # 高分到低分的急剧下降
                if (baseline_result.overall_score >= 8.0 and 
                    variant_result.overall_score <= 5.0):
                    
                    score_delta = variant_result.overall_score - baseline_result.overall_score
                    edge_case_regressions.append(RegressionCase(
                        sample_id=sample_id,
                        baseline_score=baseline_result.overall_score,
                        variant_score=variant_result.overall_score,
                        score_delta=score_delta,
                        severity="critical",
                        description=f"边界案例回归: 高分急剧下降 ({baseline_result.overall_score:.1f} → {variant_result.overall_score:.1f})"
                    ))
                
                # 从通过到失败的 must_have 案例
                elif (baseline_result.must_have_pass and 
                      not variant_result.must_have_pass and
                      baseline_result.overall_score >= 7.0):
                    
                    score_delta = variant_result.overall_score - baseline_result.overall_score
                    edge_case_regressions.append(RegressionCase(
                        sample_id=sample_id,
                        baseline_score=baseline_result.overall_score,
                        variant_score=variant_result.overall_score,
                        score_delta=score_delta,
                        severity="critical",
                        description="边界案例回归: 高质量样本 must_have 失败"
                    ))
        
        return edge_case_regressions
    
    def _prioritize_regression_cases(self, regression_cases: List[RegressionCase]) -> List[RegressionCase]:
        """对回归案例进行优先级排序"""
        def get_priority_score(case: RegressionCase) -> Tuple[int, float, float]:
            # 严重程度权重
            severity_weights = {"critical": 0, "major": 1, "minor": 2}
            severity_score = severity_weights.get(case.severity, 3)
            
            # 分数下降程度（越大越严重）
            score_impact = abs(case.score_delta)
            
            # 基线分数（原本越好的样本回归越严重）
            baseline_impact = -case.baseline_score  # 负号使得高分排在前面
            
            return (severity_score, -score_impact, baseline_impact)
        
        return sorted(regression_cases, key=get_priority_score)
    
    def _compare_severity(self, severity1: str, severity2: str) -> int:
        """比较两个严重程度，返回 1 如果 severity1 更严重，-1 如果 severity2 更严重，0 如果相等"""
        severity_order = {"critical": 3, "major": 2, "minor": 1}
        score1 = severity_order.get(severity1, 0)
        score2 = severity_order.get(severity2, 0)
        
        if score1 > score2:
            return 1
        elif score1 < score2:
            return -1
        else:
            return 0
    
    def _calculate_std(self, values: List[float]) -> float:
        """计算标准差"""
        if len(values) <= 1:
            return 0.0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
        return variance ** 0.5
    
    def _generate_comparison_report(
        self,
        baseline_snapshot: BaselineSnapshot,
        variant_results: List[EvaluationResult],
        regression_cases: List[RegressionCase],
        config: RegressionTestConfig
    ) -> ComparisonReport:
        """生成比较报告"""
        # 计算整体统计
        total_samples = len(variant_results)
        
        # 分数统计
        variant_scores = [r.overall_score for r in variant_results if r.overall_score > 0]
        avg_variant_score = sum(variant_scores) / len(variant_scores) if variant_scores else 0.0
        
        baseline_avg_score = baseline_snapshot.performance_metrics.get("average_score", 0.0)
        score_delta = avg_variant_score - baseline_avg_score
        
        # Must-have 统计
        variant_must_have_passed = len([r for r in variant_results if r.must_have_pass])
        variant_must_have_rate = variant_must_have_passed / total_samples if total_samples > 0 else 0.0
        
        baseline_must_have_rate = baseline_snapshot.performance_metrics.get("must_have_pass_rate", 0.0)
        must_have_delta = variant_must_have_rate - baseline_must_have_rate
        
        # 规则违规统计
        variant_rule_violations = {}
        for result in variant_results:
            for violation in result.rule_violations:
                variant_rule_violations[violation] = variant_rule_violations.get(violation, 0) + 1
        
        total_variant_violations = sum(variant_rule_violations.values())
        variant_violation_rate = total_variant_violations / total_samples if total_samples > 0 else 0.0
        
        baseline_violation_rate = baseline_snapshot.performance_metrics.get("rule_violation_rate", 0.0)
        rule_violation_delta = variant_violation_rate - baseline_violation_rate
        
        # 按标签分析性能（如果有标签信息）
        tag_performance = {}
        # TODO: 实现按标签的性能分析
        
        # 选择最严重的回归案例
        worst_regressions = regression_cases[:10]  # 取前10个最严重的
        
        # 生成摘要
        summary_parts = []
        if score_delta < 0:
            summary_parts.append(f"平均分数下降 {abs(score_delta):.2f}")
        elif score_delta > 0:
            summary_parts.append(f"平均分数提升 {score_delta:.2f}")
        else:
            summary_parts.append("平均分数无变化")
        
        if must_have_delta < 0:
            summary_parts.append(f"Must-have 通过率下降 {abs(must_have_delta)*100:.1f}%")
        elif must_have_delta > 0:
            summary_parts.append(f"Must-have 通过率提升 {must_have_delta*100:.1f}%")
        
        if len(regression_cases) > 0:
            critical_count = len([c for c in regression_cases if c.severity == "critical"])
            major_count = len([c for c in regression_cases if c.severity == "major"])
            minor_count = len([c for c in regression_cases if c.severity == "minor"])
            
            summary_parts.append(f"发现 {len(regression_cases)} 个回归案例")
            if critical_count > 0:
                summary_parts.append(f"其中 {critical_count} 个严重")
            if major_count > 0:
                summary_parts.append(f"{major_count} 个重要")
            if minor_count > 0:
                summary_parts.append(f"{minor_count} 个轻微")
        else:
            summary_parts.append("未发现回归案例")
        
        summary = "；".join(summary_parts)
        
        return ComparisonReport(
            baseline_name=config.baseline_name,
            variant_name=config.variant_name,
            sample_count=total_samples,
            score_delta=score_delta,
            must_have_delta=must_have_delta,
            rule_violation_delta=rule_violation_delta,
            tag_performance=tag_performance,
            worst_regressions=worst_regressions,
            summary=summary
        )
    
    def _generate_regression_summary(
        self,
        baseline_snapshot: BaselineSnapshot,
        variant_results: List[EvaluationResult],
        regression_cases: List[RegressionCase],
        config: RegressionTestConfig
    ) -> str:
        """生成回归测试摘要"""
        summary_lines = [
            f"# 回归测试报告",
            f"",
            f"**实体**: {config.entity_type}/{config.entity_id}",
            f"**Baseline**: {config.baseline_name}",
            f"**变体**: {config.variant_name}",
            f"**测试时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**样本数量**: {len(variant_results)}",
            f"",
            f"## 整体结果"
        ]
        
        # 添加整体统计
        if len(regression_cases) == 0:
            summary_lines.extend([
                f"✅ **未发现回归问题**",
                f"",
                f"所有测试样本的性能都符合预期，没有显著的性能下降。"
            ])
        else:
            critical_count = len([c for c in regression_cases if c.severity == "critical"])
            major_count = len([c for c in regression_cases if c.severity == "major"])
            minor_count = len([c for c in regression_cases if c.severity == "minor"])
            
            summary_lines.extend([
                f"⚠️ **发现 {len(regression_cases)} 个回归案例**",
                f"",
                f"- 严重回归: {critical_count} 个",
                f"- 重要回归: {major_count} 个",
                f"- 轻微回归: {minor_count} 个",
                f""
            ])
            
            # 添加最严重的回归案例
            if critical_count > 0:
                critical_cases = [c for c in regression_cases if c.severity == "critical"][:5]
                summary_lines.extend([
                    f"### 严重回归案例",
                    f""
                ])
                
                for case in critical_cases:
                    summary_lines.extend([
                        f"**样本 {case.sample_id}**",
                        f"- 分数变化: {case.baseline_score:.2f} → {case.variant_score:.2f} ({case.score_delta:+.2f})",
                        f"- 问题描述: {case.description}",
                        f""
                    ])
        
        # 添加性能对比
        baseline_metrics = baseline_snapshot.performance_metrics
        
        variant_scores = [r.overall_score for r in variant_results if r.overall_score > 0]
        variant_avg_score = sum(variant_scores) / len(variant_scores) if variant_scores else 0.0
        
        variant_must_have_passed = len([r for r in variant_results if r.must_have_pass])
        variant_must_have_rate = variant_must_have_passed / len(variant_results) if variant_results else 0.0
        
        summary_lines.extend([
            f"## 性能对比",
            f"",
            f"| 指标 | Baseline | 变体 | 变化 |",
            f"|------|----------|------|------|",
            f"| 平均分数 | {baseline_metrics.get('average_score', 0):.2f} | {variant_avg_score:.2f} | {variant_avg_score - baseline_metrics.get('average_score', 0):+.2f} |",
            f"| Must-Have 通过率 | {baseline_metrics.get('must_have_pass_rate', 0)*100:.1f}% | {variant_must_have_rate*100:.1f}% | {(variant_must_have_rate - baseline_metrics.get('must_have_pass_rate', 0))*100:+.1f}% |",
            f""
        ])
        
        # 添加建议
        if len(regression_cases) > 0:
            summary_lines.extend([
                f"## 建议",
                f""
            ])
            
            if critical_count > 0:
                summary_lines.append(f"- 🚨 发现严重回归，建议立即修复后再发布")
            elif major_count > 0:
                summary_lines.append(f"- ⚠️ 发现重要回归，建议评估影响后决定是否发布")
            else:
                summary_lines.append(f"- ℹ️ 发现轻微回归，可考虑在后续版本中优化")
            
            summary_lines.extend([
                f"- 重点关注失败的样本，分析失败原因",
                f"- 考虑增加针对性的测试用例",
                f"- 评估是否需要调整模型参数或 prompt"
            ])
        else:
            summary_lines.extend([
                f"## 建议",
                f"",
                f"- ✅ 当前变体性能良好，可以考虑发布",
                f"- 建议继续监控生产环境的性能表现",
                f"- 可以将当前变体设置为新的 baseline"
            ])
        
        return "\n".join(summary_lines)
    
    def save_regression_test_result(
        self,
        result: RegressionTestResult,
        output_dir: Optional[Path] = None
    ) -> Dict[str, Path]:
        """
        保存回归测试结果
        
        Args:
            result: 回归测试结果
            output_dir: 输出目录（可选）
            
        Returns:
            保存的文件路径字典
        """
        if not output_dir:
            output_dir = self.data_manager.get_entity_evals_dir(
                result.config.entity_type, result.config.entity_id
            ) / "regression"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = result.created_at.strftime("%Y-%m-%dT%H-%M-%S")
        base_filename = f"{result.config.entity_id}_{result.config.variant_name}_vs_{result.config.baseline_name}_{timestamp}"
        
        saved_files = {}
        
        # 保存完整的 JSON 结果
        json_path = output_dir / f"{base_filename}.regression.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        saved_files["json"] = json_path
        
        # 保存摘要报告
        summary_path = output_dir / f"{base_filename}.summary.md"
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write(result.summary)
        saved_files["summary"] = summary_path
        
        # 保存回归案例 CSV
        if result.regression_cases:
            import csv
            csv_path = output_dir / f"{base_filename}.regressions.csv"
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = [
                    "sample_id", "baseline_score", "variant_score", 
                    "score_delta", "severity", "description"
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                
                for case in result.regression_cases:
                    writer.writerow(case.to_dict())
            
            saved_files["regressions_csv"] = csv_path
        
        logger.info(f"回归测试结果已保存到: {output_dir}")
        return saved_files


# 便捷函数
def run_pipeline_regression_test(
    pipeline_id: str,
    baseline_name: str,
    variant_name: str,
    testset_path: Optional[str] = None,
    include_tags: Optional[List[str]] = None,
    exclude_tags: Optional[List[str]] = None,
    score_threshold: float = 0.5,
    progress_callback: Optional[callable] = None
) -> RegressionTestResult:
    """运行 pipeline 回归测试的便捷函数"""
    config = RegressionTestConfig(
        entity_type="pipeline",
        entity_id=pipeline_id,
        baseline_name=baseline_name,
        variant_name=variant_name,
        testset_path=testset_path,
        include_tags=include_tags or [],
        exclude_tags=exclude_tags or [],
        score_threshold=score_threshold
    )
    
    tester = RegressionTester()
    if progress_callback:
        tester.set_progress_callback(progress_callback)
    
    return tester.run_regression_test(config)


def run_agent_regression_test(
    agent_id: str,
    baseline_name: str,
    variant_name: str,
    testset_path: Optional[str] = None,
    include_tags: Optional[List[str]] = None,
    exclude_tags: Optional[List[str]] = None,
    score_threshold: float = 0.5,
    progress_callback: Optional[callable] = None
) -> RegressionTestResult:
    """运行 agent 回归测试的便捷函数"""
    config = RegressionTestConfig(
        entity_type="agent",
        entity_id=agent_id,
        baseline_name=baseline_name,
        variant_name=variant_name,
        testset_path=testset_path,
        include_tags=include_tags or [],
        exclude_tags=exclude_tags or [],
        score_threshold=score_threshold
    )
    
    tester = RegressionTester()
    if progress_callback:
        tester.set_progress_callback(progress_callback)
    
    return tester.run_regression_test(config)


class RegressionAnalyzer:
    """回归分析器 - 提供深度分析和洞察"""
    
    def __init__(self):
        """初始化回归分析器"""
        pass
    
    def analyze_regression_patterns(
        self,
        regression_cases: List[RegressionCase],
        baseline_results: Dict[str, EvaluationResult],
        variant_results: List[EvaluationResult]
    ) -> Dict[str, Any]:
        """
        分析回归模式和趋势
        
        Args:
            regression_cases: 回归案例列表
            baseline_results: 基线结果字典
            variant_results: 变体结果列表
            
        Returns:
            回归模式分析结果
        """
        variant_map = {r.sample_id: r for r in variant_results}
        
        analysis = {
            "severity_distribution": self._analyze_severity_distribution(regression_cases),
            "score_impact_analysis": self._analyze_score_impact(regression_cases),
            "failure_pattern_analysis": self._analyze_failure_patterns(
                regression_cases, baseline_results, variant_map
            ),
            "temporal_analysis": self._analyze_temporal_patterns(regression_cases),
            "root_cause_analysis": self._analyze_root_causes(
                regression_cases, baseline_results, variant_map
            ),
            "recovery_recommendations": self._generate_recovery_recommendations(
                regression_cases, baseline_results, variant_map
            )
        }
        
        return analysis
    
    def _analyze_severity_distribution(self, regression_cases: List[RegressionCase]) -> Dict[str, Any]:
        """分析严重程度分布"""
        severity_counts = {"critical": 0, "major": 0, "minor": 0}
        severity_scores = {"critical": [], "major": [], "minor": []}
        
        for case in regression_cases:
            severity_counts[case.severity] += 1
            severity_scores[case.severity].append(abs(case.score_delta))
        
        total = len(regression_cases)
        
        return {
            "counts": severity_counts,
            "percentages": {
                severity: count / total * 100 if total > 0 else 0
                for severity, count in severity_counts.items()
            },
            "average_impact": {
                severity: sum(scores) / len(scores) if scores else 0
                for severity, scores in severity_scores.items()
            },
            "max_impact": {
                severity: max(scores) if scores else 0
                for severity, scores in severity_scores.items()
            }
        }
    
    def _analyze_score_impact(self, regression_cases: List[RegressionCase]) -> Dict[str, Any]:
        """分析分数影响"""
        score_deltas = [case.score_delta for case in regression_cases]
        
        if not score_deltas:
            return {"error": "没有回归案例"}
        
        score_deltas.sort()
        n = len(score_deltas)
        
        # 分数下降区间分析
        impact_ranges = {
            "轻微 (0-0.5)": len([d for d in score_deltas if -0.5 <= d < 0]),
            "中等 (0.5-1.0)": len([d for d in score_deltas if -1.0 <= d < -0.5]),
            "严重 (1.0-2.0)": len([d for d in score_deltas if -2.0 <= d < -1.0]),
            "极严重 (>2.0)": len([d for d in score_deltas if d < -2.0])
        }
        
        return {
            "total_cases": n,
            "average_impact": sum(score_deltas) / n,
            "median_impact": score_deltas[n // 2] if n % 2 == 1 else (score_deltas[n // 2 - 1] + score_deltas[n // 2]) / 2,
            "worst_impact": min(score_deltas),
            "impact_ranges": impact_ranges,
            "cumulative_impact": sum(abs(d) for d in score_deltas)
        }
    
    def _analyze_failure_patterns(
        self,
        regression_cases: List[RegressionCase],
        baseline_results: Dict[str, EvaluationResult],
        variant_map: Dict[str, EvaluationResult]
    ) -> Dict[str, Any]:
        """分析失败模式"""
        patterns = {
            "must_have_failures": [],
            "rule_violation_patterns": {},
            "score_drop_patterns": {},
            "execution_time_issues": []
        }
        
        for case in regression_cases:
            sample_id = case.sample_id
            
            if sample_id in baseline_results and sample_id in variant_map:
                baseline = baseline_results[sample_id]
                variant = variant_map[sample_id]
                
                # Must-have 失败分析
                if baseline.must_have_pass and not variant.must_have_pass:
                    patterns["must_have_failures"].append({
                        "sample_id": sample_id,
                        "baseline_score": baseline.overall_score,
                        "variant_score": variant.overall_score,
                        "new_violations": list(set(variant.rule_violations) - set(baseline.rule_violations))
                    })
                
                # 规则违规模式分析
                new_violations = set(variant.rule_violations) - set(baseline.rule_violations)
                for violation in new_violations:
                    if violation not in patterns["rule_violation_patterns"]:
                        patterns["rule_violation_patterns"][violation] = []
                    patterns["rule_violation_patterns"][violation].append(sample_id)
                
                # 分数下降模式分析
                score_range = self._get_score_range(baseline.overall_score)
                if score_range not in patterns["score_drop_patterns"]:
                    patterns["score_drop_patterns"][score_range] = []
                patterns["score_drop_patterns"][score_range].append({
                    "sample_id": sample_id,
                    "baseline_score": baseline.overall_score,
                    "variant_score": variant.overall_score,
                    "delta": case.score_delta
                })
                
                # 执行时间问题分析
                if (baseline.execution_time > 0 and variant.execution_time > 0 and
                    variant.execution_time > baseline.execution_time * 1.5):
                    patterns["execution_time_issues"].append({
                        "sample_id": sample_id,
                        "baseline_time": baseline.execution_time,
                        "variant_time": variant.execution_time,
                        "increase_ratio": variant.execution_time / baseline.execution_time
                    })
        
        return patterns
    
    def _analyze_temporal_patterns(self, regression_cases: List[RegressionCase]) -> Dict[str, Any]:
        """分析时间模式（如果有时间戳信息）"""
        # 这里可以分析回归案例是否有时间相关的模式
        # 目前简化实现，主要分析严重程度的分布趋势
        
        severity_timeline = []
        for i, case in enumerate(regression_cases):
            severity_timeline.append({
                "index": i,
                "severity": case.severity,
                "impact": abs(case.score_delta)
            })
        
        return {
            "severity_timeline": severity_timeline,
            "trend_analysis": self._analyze_severity_trend(severity_timeline)
        }
    
    def _analyze_severity_trend(self, timeline: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析严重程度趋势"""
        if len(timeline) < 3:
            return {"trend": "insufficient_data"}
        
        # 简单的趋势分析：看严重程度是否有聚集
        severity_weights = {"critical": 3, "major": 2, "minor": 1}
        
        first_half = timeline[:len(timeline)//2]
        second_half = timeline[len(timeline)//2:]
        
        first_avg = sum(severity_weights[item["severity"]] for item in first_half) / len(first_half)
        second_avg = sum(severity_weights[item["severity"]] for item in second_half) / len(second_half)
        
        if second_avg > first_avg * 1.2:
            trend = "worsening"
        elif second_avg < first_avg * 0.8:
            trend = "improving"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "first_half_severity": first_avg,
            "second_half_severity": second_avg
        }
    
    def _analyze_root_causes(
        self,
        regression_cases: List[RegressionCase],
        baseline_results: Dict[str, EvaluationResult],
        variant_map: Dict[str, EvaluationResult]
    ) -> Dict[str, Any]:
        """分析根本原因"""
        root_causes = {
            "prompt_related": [],
            "model_related": [],
            "logic_related": [],
            "data_related": [],
            "unknown": []
        }
        
        for case in regression_cases:
            sample_id = case.sample_id
            
            if sample_id in baseline_results and sample_id in variant_map:
                baseline = baseline_results[sample_id]
                variant = variant_map[sample_id]
                
                # 基于描述和违规类型推断根本原因
                cause_category = self._infer_root_cause(case, baseline, variant)
                root_causes[cause_category].append({
                    "sample_id": sample_id,
                    "severity": case.severity,
                    "description": case.description,
                    "evidence": self._collect_evidence(case, baseline, variant)
                })
        
        return root_causes
    
    def _infer_root_cause(
        self,
        case: RegressionCase,
        baseline: EvaluationResult,
        variant: EvaluationResult
    ) -> str:
        """推断根本原因类别"""
        description = case.description.lower()
        new_violations = set(variant.rule_violations) - set(baseline.rule_violations)
        
        # 基于规则违规类型推断
        if any("格式" in v or "结构" in v for v in new_violations):
            return "prompt_related"
        elif any("逻辑" in v or "推理" in v for v in new_violations):
            return "logic_related"
        elif any("数据" in v or "信息" in v for v in new_violations):
            return "data_related"
        elif "执行时间" in description:
            return "model_related"
        elif "must_have" in description:
            return "logic_related"
        else:
            return "unknown"
    
    def _collect_evidence(
        self,
        case: RegressionCase,
        baseline: EvaluationResult,
        variant: EvaluationResult
    ) -> Dict[str, Any]:
        """收集证据信息"""
        return {
            "score_change": case.score_delta,
            "must_have_change": baseline.must_have_pass != variant.must_have_pass,
            "new_violations": list(set(variant.rule_violations) - set(baseline.rule_violations)),
            "removed_violations": list(set(baseline.rule_violations) - set(variant.rule_violations)),
            "execution_time_change": variant.execution_time - baseline.execution_time if baseline.execution_time > 0 else 0
        }
    
    def _generate_recovery_recommendations(
        self,
        regression_cases: List[RegressionCase],
        baseline_results: Dict[str, EvaluationResult],
        variant_map: Dict[str, EvaluationResult]
    ) -> List[Dict[str, Any]]:
        """生成恢复建议"""
        recommendations = []
        
        # 分析主要问题类型
        severity_counts = {"critical": 0, "major": 0, "minor": 0}
        must_have_failures = 0
        rule_violations = {}
        
        for case in regression_cases:
            severity_counts[case.severity] += 1
            
            sample_id = case.sample_id
            if sample_id in baseline_results and sample_id in variant_map:
                baseline = baseline_results[sample_id]
                variant = variant_map[sample_id]
                
                if baseline.must_have_pass and not variant.must_have_pass:
                    must_have_failures += 1
                
                new_violations = set(variant.rule_violations) - set(baseline.rule_violations)
                for violation in new_violations:
                    rule_violations[violation] = rule_violations.get(violation, 0) + 1
        
        # 基于分析结果生成建议
        if severity_counts["critical"] > 0:
            recommendations.append({
                "priority": "high",
                "category": "immediate_action",
                "title": "立即处理严重回归",
                "description": f"发现 {severity_counts['critical']} 个严重回归案例，建议立即停止发布并修复",
                "actions": [
                    "回滚到上一个稳定版本",
                    "分析严重回归案例的共同特征",
                    "修复根本问题后重新测试"
                ]
            })
        
        if must_have_failures > 0:
            recommendations.append({
                "priority": "high",
                "category": "must_have_fixes",
                "title": "修复 Must-Have 要求失败",
                "description": f"{must_have_failures} 个样本的 must_have 要求失败",
                "actions": [
                    "检查 prompt 是否正确处理必要条件",
                    "验证模型参数设置",
                    "增加针对性的测试用例"
                ]
            })
        
        if rule_violations:
            top_violations = sorted(rule_violations.items(), key=lambda x: x[1], reverse=True)[:3]
            recommendations.append({
                "priority": "medium",
                "category": "rule_compliance",
                "title": "改善规则合规性",
                "description": f"主要违规类型: {', '.join([v[0] for v in top_violations])}",
                "actions": [
                    f"重点关注 {top_violations[0][0]} 违规 ({top_violations[0][1]} 次)",
                    "检查相关的 prompt 指令",
                    "考虑调整规则阈值或模型参数"
                ]
            })
        
        if severity_counts["minor"] > severity_counts["critical"] + severity_counts["major"]:
            recommendations.append({
                "priority": "low",
                "category": "optimization",
                "title": "性能优化建议",
                "description": "主要是轻微回归，可以通过优化改善",
                "actions": [
                    "分析轻微回归的模式",
                    "考虑 prompt 微调",
                    "增加更多训练数据"
                ]
            })
        
        return recommendations
    
    def _get_score_range(self, score: float) -> str:
        """获取分数范围标签"""
        if score >= 9.0:
            return "优秀 (9.0-10.0)"
        elif score >= 8.0:
            return "良好 (8.0-9.0)"
        elif score >= 7.0:
            return "中等 (7.0-8.0)"
        elif score >= 6.0:
            return "及格 (6.0-7.0)"
        else:
            return "不及格 (<6.0)"
    
    def generate_detailed_analysis_report(
        self,
        regression_cases: List[RegressionCase],
        baseline_results: Dict[str, EvaluationResult],
        variant_results: List[EvaluationResult],
        config: RegressionTestConfig
    ) -> str:
        """生成详细的分析报告"""
        analysis = self.analyze_regression_patterns(
            regression_cases, 
            {r.sample_id: r for r in baseline_results.values()}, 
            variant_results
        )
        
        report_lines = [
            f"# 详细回归分析报告",
            f"",
            f"**实体**: {config.entity_type}/{config.entity_id}",
            f"**Baseline**: {config.baseline_name}",
            f"**变体**: {config.variant_name}",
            f"**分析时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"## 回归严重程度分析"
        ]
        
        severity_dist = analysis["severity_distribution"]
        report_lines.extend([
            f"",
            f"| 严重程度 | 数量 | 占比 | 平均影响 | 最大影响 |",
            f"|----------|------|------|----------|----------|",
            f"| 严重 | {severity_dist['counts']['critical']} | {severity_dist['percentages']['critical']:.1f}% | {severity_dist['average_impact']['critical']:.2f} | {severity_dist['max_impact']['critical']:.2f} |",
            f"| 重要 | {severity_dist['counts']['major']} | {severity_dist['percentages']['major']:.1f}% | {severity_dist['average_impact']['major']:.2f} | {severity_dist['max_impact']['major']:.2f} |",
            f"| 轻微 | {severity_dist['counts']['minor']} | {severity_dist['percentages']['minor']:.1f}% | {severity_dist['average_impact']['minor']:.2f} | {severity_dist['max_impact']['minor']:.2f} |",
            f""
        ])
        
        # 分数影响分析
        score_impact = analysis["score_impact_analysis"]
        if "error" not in score_impact:
            report_lines.extend([
                f"## 分数影响分析",
                f"",
                f"- **总回归案例**: {score_impact['total_cases']}",
                f"- **平均影响**: {score_impact['average_impact']:.2f}",
                f"- **中位数影响**: {score_impact['median_impact']:.2f}",
                f"- **最严重影响**: {score_impact['worst_impact']:.2f}",
                f"- **累计影响**: {score_impact['cumulative_impact']:.2f}",
                f"",
                f"### 影响程度分布",
                f""
            ])
            
            for range_name, count in score_impact["impact_ranges"].items():
                percentage = count / score_impact['total_cases'] * 100 if score_impact['total_cases'] > 0 else 0
                report_lines.append(f"- {range_name}: {count} 个 ({percentage:.1f}%)")
            
            report_lines.append("")
        
        # 失败模式分析
        failure_patterns = analysis["failure_pattern_analysis"]
        
        if failure_patterns["must_have_failures"]:
            report_lines.extend([
                f"## Must-Have 失败分析",
                f"",
                f"发现 {len(failure_patterns['must_have_failures'])} 个 must_have 失败案例:",
                f""
            ])
            
            for failure in failure_patterns["must_have_failures"][:5]:  # 显示前5个
                report_lines.extend([
                    f"**样本 {failure['sample_id']}**",
                    f"- 分数变化: {failure['baseline_score']:.2f} → {failure['variant_score']:.2f}",
                    f"- 新增违规: {', '.join(failure['new_violations']) if failure['new_violations'] else '无'}",
                    f""
                ])
        
        if failure_patterns["rule_violation_patterns"]:
            report_lines.extend([
                f"## 规则违规模式分析",
                f""
            ])
            
            for violation, samples in failure_patterns["rule_violation_patterns"].items():
                report_lines.append(f"**{violation}**: 影响 {len(samples)} 个样本")
            
            report_lines.append("")
        
        # 根本原因分析
        root_causes = analysis["root_cause_analysis"]
        report_lines.extend([
            f"## 根本原因分析",
            f""
        ])
        
        for cause_type, cases in root_causes.items():
            if cases:
                cause_names = {
                    "prompt_related": "Prompt 相关",
                    "model_related": "模型相关", 
                    "logic_related": "逻辑相关",
                    "data_related": "数据相关",
                    "unknown": "未知原因"
                }
                report_lines.append(f"**{cause_names.get(cause_type, cause_type)}**: {len(cases)} 个案例")
        
        report_lines.append("")
        
        # 恢复建议
        recommendations = analysis["recovery_recommendations"]
        if recommendations:
            report_lines.extend([
                f"## 恢复建议",
                f""
            ])
            
            for rec in recommendations:
                priority_emoji = {"high": "🚨", "medium": "⚠️", "low": "ℹ️"}
                report_lines.extend([
                    f"### {priority_emoji.get(rec['priority'], '•')} {rec['title']}",
                    f"",
                    f"{rec['description']}",
                    f"",
                    f"**建议行动**:",
                    f""
                ])
                
                for action in rec["actions"]:
                    report_lines.append(f"- {action}")
                
                report_lines.append("")
        
        return "\n".join(report_lines)


# 便捷函数扩展
def analyze_regression_results(
    regression_result: RegressionTestResult
) -> Dict[str, Any]:
    """分析回归测试结果的便捷函数"""
    analyzer = RegressionAnalyzer()
    
    baseline_results = {}
    for result_data in regression_result.baseline_snapshot.evaluation_results:
        sample_id = result_data.get("sample_id", "")
        if sample_id:
            baseline_results[sample_id] = EvaluationResult.from_dict(result_data)
    
    return analyzer.analyze_regression_patterns(
        regression_result.regression_cases,
        baseline_results,
        regression_result.variant_results
    )


def generate_regression_analysis_report(
    regression_result: RegressionTestResult
) -> str:
    """生成回归分析报告的便捷函数"""
    analyzer = RegressionAnalyzer()
    
    baseline_results = {}
    for result_data in regression_result.baseline_snapshot.evaluation_results:
        sample_id = result_data.get("sample_id", "")
        if sample_id:
            baseline_results[sample_id] = EvaluationResult.from_dict(result_data)
    
    return analyzer.generate_detailed_analysis_report(
        regression_result.regression_cases,
        baseline_results,
        regression_result.variant_results,
        regression_result.config
    )