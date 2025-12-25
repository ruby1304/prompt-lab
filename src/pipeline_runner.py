# src/pipeline_runner.py
"""
Pipeline 执行引擎

实现 PipelineRunner 类处理多步骤执行流程，
包括步骤间的数据传递、上下文管理和进度跟踪。
"""

from __future__ import annotations

import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from .models import PipelineConfig, StepConfig, VariantConfig, EvaluationResult, CodeNodeConfig
from .chains import run_flow_with_tokens
from .agent_registry import load_agent
from .progress_tracker import PipelineProgressTracker
from .checkpoint_manager import CheckpointManager, ResumableExecutor
from .code_executor import CodeExecutor, ExecutionResult as CodeExecutionResult
from .dependency_analyzer import DependencyAnalyzer, DependencyGraph
from .concurrent_executor import ConcurrentExecutor, Task, TaskResult
from .batch_aggregator import BatchAggregator, AggregationResult
from .error_handler import (
    ErrorHandler, create_config_error, create_execution_error, 
    create_data_error, handle_error
)

logger = logging.getLogger(__name__)


@dataclass
class StepResult:
    """单个步骤的执行结果"""
    step_id: str
    output_key: str
    output_value: Any
    execution_time: float
    token_usage: Dict[str, int] = field(default_factory=dict)
    parser_stats: Optional[Dict[str, Any]] = None  # 新增：Output Parser 统计信息
    error: Optional[str] = None
    success: bool = True  # 新增：明确标记步骤是否成功
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "step_id": self.step_id,
            "output_key": self.output_key,
            "output_value": self.output_value,
            "execution_time": self.execution_time,
            "token_usage": self.token_usage,
            "error": self.error,
            "success": self.success
        }
        if self.parser_stats:
            result["parser_stats"] = self.parser_stats
        return result


@dataclass
class PipelineResult:
    """Pipeline 执行结果"""
    sample_id: str
    variant: str
    step_results: List[StepResult] = field(default_factory=list)
    total_execution_time: float = 0.0
    total_token_usage: Dict[str, int] = field(default_factory=dict)
    total_parser_stats: Optional[Dict[str, Any]] = None  # 新增：聚合的 Parser 统计信息
    final_outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def get_step_outputs_dict(self) -> Dict[str, Any]:
        """
        获取所有步骤的输出字典
        
        Returns:
            {output_key: output_value} 格式的字典
        """
        return {
            step.output_key: step.output_value 
            for step in self.step_results 
            if step.success
        }
    
    def get_failed_steps(self) -> List[StepResult]:
        """
        获取所有失败的步骤
        
        Returns:
            失败步骤的列表
        """
        return [step for step in self.step_results if not step.success]
    
    def get_evaluation_target_output(self, target_step_id: Optional[str] = None) -> Tuple[str, Any]:
        """
        获取评估目标步骤的输出
        
        Args:
            target_step_id: 目标步骤ID，如果为None则使用最后一个成功的步骤
            
        Returns:
            (step_id, output_value) 元组
        """
        if target_step_id:
            # 查找指定的步骤
            for step in self.step_results:
                if step.step_id == target_step_id and step.success:
                    return step.step_id, step.output_value
            # 如果找不到或步骤失败，返回空
            return target_step_id, ""
        else:
            # 使用最后一个成功的步骤
            for step in reversed(self.step_results):
                if step.success:
                    return step.step_id, step.output_value
            # 如果没有成功的步骤，返回空
            return "", ""
    
    def get_performance_summary(self, detailed: bool = False) -> Dict[str, Any]:
        """
        生成性能摘要
        
        Args:
            detailed: 是否包含详细信息（每个步骤的性能）
            
        Returns:
            性能摘要字典
        """
        summary = {
            "sample_id": self.sample_id,
            "variant": self.variant,
            "total_execution_time": self.total_execution_time,
            "total_steps": len(self.step_results),
            "successful_steps": len([s for s in self.step_results if s.success]),
            "failed_steps": len([s for s in self.step_results if not s.success]),
            "token_usage": self.total_token_usage,
            "success": self.error is None
        }
        
        # 添加 parser 统计信息
        if self.total_parser_stats:
            summary["parser_stats"] = self.total_parser_stats
        
        # 添加详细的步骤性能信息
        if detailed:
            summary["step_performance"] = [
                {
                    "step_id": step.step_id,
                    "execution_time": step.execution_time,
                    "token_usage": step.token_usage,
                    "parser_stats": step.parser_stats,
                    "success": step.success
                }
                for step in self.step_results
            ]
        
        return summary
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "sample_id": self.sample_id,
            "variant": self.variant,
            "step_results": [step.to_dict() for step in self.step_results],
            "total_execution_time": self.total_execution_time,
            "total_token_usage": self.total_token_usage,
            "final_outputs": self.final_outputs,
            "error": self.error,
            "created_at": self.created_at.isoformat()
        }
        if self.total_parser_stats:
            result["total_parser_stats"] = self.total_parser_stats
        return result


class PipelineExecutionError(Exception):
    """Pipeline 执行错误（向后兼容）"""
    pass


class PipelineRunner:
    """Pipeline 执行器"""
    
    def __init__(self, config: PipelineConfig, enable_concurrent: bool = True, max_workers: int = 4):
        """
        初始化 Pipeline 执行器
        
        Args:
            config: Pipeline 配置对象
            enable_concurrent: 是否启用并发执行（默认True）
            max_workers: 最大并发工作线程数（默认4）
        """
        self.config = config
        self.context: Dict[str, Any] = {}
        self.progress_callback: Optional[callable] = None
        self.error_handler = ErrorHandler()
        self.code_executor = CodeExecutor(default_timeout=30)  # 初始化代码执行器
        self.batch_aggregator = BatchAggregator()  # 初始化批量聚合器
        
        # 并发执行相关
        self.enable_concurrent = enable_concurrent
        self.max_workers = max_workers
        self.dependency_analyzer = DependencyAnalyzer()
        self.concurrent_executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
        
        # 验证配置
        validation_errors = config.validate()
        if validation_errors:
            error_msg = "Pipeline 配置验证失败:\n" + "\n".join(f"- {error}" for error in validation_errors)
            raise create_config_error(
                message=error_msg,
                suggestion="请检查 Pipeline 配置文件的格式和必需字段"
            )
    
    def set_progress_callback(self, callback: callable):
        """设置进度回调函数"""
        self.progress_callback = callback
    
    def execute(self, samples: List[Dict[str, Any]], variant: str = "baseline", 
                use_progress_tracker: bool = True, 
                enable_checkpoint: bool = False,
                auto_resume: bool = True,
                max_retries: int = 3) -> List[PipelineResult]:
        """
        执行完整的 Pipeline 流程
        
        Args:
            samples: 测试样本列表
            variant: 变体名称，默认为 "baseline"
            use_progress_tracker: 是否使用进度跟踪器
            enable_checkpoint: 是否启用断点续传
            auto_resume: 是否自动恢复
            max_retries: 最大重试次数
            
        Returns:
            Pipeline 执行结果列表
        """
        if not samples:
            logger.warning("没有提供测试样本")
            return []
        
        logger.info(f"开始执行 Pipeline: {self.config.name}")
        logger.info(f"变体: {variant}")
        logger.info(f"样本数量: {len(samples)}")
        
        # 如果启用断点续传，使用可恢复执行器
        if enable_checkpoint:
            checkpoint_manager = CheckpointManager(self.config.id, variant)
            resumable_executor = ResumableExecutor(self, checkpoint_manager)
            return resumable_executor.execute_with_resume(
                samples=samples,
                variant=variant,
                auto_resume=auto_resume,
                max_retries=max_retries
            )
        
        # 常规执行流程
        results = []
        total_samples = len(samples)
        
        # 创建进度跟踪器
        progress_tracker = None
        if use_progress_tracker:
            progress_tracker = PipelineProgressTracker(
                pipeline_name=self.config.name,
                total_samples=total_samples,
                total_steps=len(self.config.steps),
                variant=variant
            )
            progress_tracker.start()
        
        try:
            for i, sample in enumerate(samples):
                sample_id = sample.get("id", f"sample_{i}")
                
                # 更新进度（开始处理样本）
                if progress_tracker:
                    progress_tracker.update_sample(i, sample_id, 0, "开始处理")
                elif self.progress_callback:
                    self.progress_callback(i, total_samples, f"正在处理样本: {sample_id}")
                
                try:
                    result = self.execute_sample(sample, variant, progress_tracker, i)
                    results.append(result)
                    logger.debug(f"样本 {sample_id} 执行完成")
                    
                    # 更新进度（样本完成）
                    if progress_tracker:
                        progress_tracker.complete_sample(i, sample_id, failed=bool(result.error))
                    
                except Exception as e:
                    # 使用错误处理器处理异常
                    error_info = self.error_handler.handle_error(
                        error=e,
                        context={"sample_id": sample_id, "sample_index": i},
                        reraise=False
                    )
                    
                    error_msg = f"样本 {sample_id} 执行失败: {error_info.message}"
                    logger.error(error_msg)
                    
                    # 创建错误结果
                    error_result = PipelineResult(
                        sample_id=sample_id,
                        variant=variant,
                        error=error_msg
                    )
                    results.append(error_result)
                    
                    # 更新进度（样本失败）
                    if progress_tracker:
                        progress_tracker.complete_sample(i, sample_id, failed=True)
            
            # 完成进度跟踪
            if progress_tracker:
                success_count = len([r for r in results if not r.error])
                progress_tracker.finish(f"Pipeline 执行完成！成功处理 {success_count}/{total_samples} 个样本")
            elif self.progress_callback:
                self.progress_callback(total_samples, total_samples, "Pipeline 执行完成")
            
            # 生成并记录性能摘要
            perf_summary = self.generate_aggregate_performance_summary(results, detailed=False)
            logger.info(f"Pipeline 执行完成，成功处理 {perf_summary['successful_samples']}/{perf_summary['total_samples']} 个样本")
            logger.info(f"总执行时间: {perf_summary['total_execution_time']:.2f}秒, 平均: {perf_summary['average_execution_time']:.2f}秒/样本")
            logger.info(f"总 token 使用: {perf_summary['total_token_usage']['total_tokens']}, 平均: {perf_summary['average_token_usage']['total_tokens']:.0f}/样本")
            
            # 在调试模式下输出详细信息
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("详细性能摘要:")
                logger.debug(f"  - 输入 tokens: {perf_summary['total_token_usage']['input_tokens']}")
                logger.debug(f"  - 输出 tokens: {perf_summary['total_token_usage']['output_tokens']}")
                if perf_summary.get('parser_stats'):
                    logger.debug(f"  - Parser 成功率: {perf_summary['parser_stats']['success_rate']:.2%}")
                    logger.debug(f"  - Parser 平均重试: {perf_summary['parser_stats']['average_retries']:.2f}")
            
        except Exception as e:
            if progress_tracker:
                progress_tracker.finish("Pipeline 执行过程中出现错误")
            raise
        
        return results
    
    def execute_sample(self, sample: Dict[str, Any], variant: str = "baseline", 
                      progress_tracker: Optional[PipelineProgressTracker] = None,
                      sample_index: int = 0) -> PipelineResult:
        """
        执行单个样本的 Pipeline 流程
        
        Args:
            sample: 测试样本数据
            variant: 变体名称
            progress_tracker: 进度跟踪器
            sample_index: 样本索引
            
        Returns:
            Pipeline 执行结果
        """
        sample_id = sample.get("id", "unknown")
        start_time = time.time()
        
        # 初始化执行上下文
        self.context = {
            "sample": sample,
            "variant": variant,
            "testset_fields": sample.copy()
        }
        
        result = PipelineResult(
            sample_id=sample_id,
            variant=variant
        )
        
        try:
            # 获取变体配置
            variant_config = self._get_variant_config(variant)
            
            # 根据是否启用并发执行选择不同的执行策略
            if self.enable_concurrent:
                # 使用并发执行调度
                result = self._execute_sample_concurrent(
                    sample=sample,
                    sample_id=sample_id,
                    variant=variant,
                    variant_config=variant_config,
                    progress_tracker=progress_tracker,
                    sample_index=sample_index,
                    start_time=start_time
                )
            else:
                # 使用顺序执行（原有逻辑）
                result = self._execute_sample_sequential(
                    sample=sample,
                    sample_id=sample_id,
                    variant=variant,
                    variant_config=variant_config,
                    progress_tracker=progress_tracker,
                    sample_index=sample_index,
                    start_time=start_time
                )
            
        except Exception as e:
            result.error = str(e)
            result.total_execution_time = time.time() - start_time
            logger.error(f"样本 {sample_id} 执行失败: {e}")
        
        return result
    
    def _execute_sample_sequential(
        self,
        sample: Dict[str, Any],
        sample_id: str,
        variant: str,
        variant_config: Optional[VariantConfig],
        progress_tracker: Optional[PipelineProgressTracker],
        sample_index: int,
        start_time: float
    ) -> PipelineResult:
        """
        顺序执行样本的 Pipeline 流程（原有逻辑）
        
        Args:
            sample: 测试样本数据
            sample_id: 样本ID
            variant: 变体名称
            variant_config: 变体配置
            progress_tracker: 进度跟踪器
            sample_index: 样本索引
            start_time: 开始时间
            
        Returns:
            Pipeline 执行结果
        """
        result = PipelineResult(
            sample_id=sample_id,
            variant=variant
        )
        
        # 执行每个步骤
        failed_outputs = set()  # 跟踪失败步骤的输出
        
        for step_index, step in enumerate(self.config.steps):
            # 更新进度（开始执行步骤）
            if progress_tracker:
                progress_tracker.update_sample(sample_index, sample_id, step_index, step.id)
            
            # 检查此步骤是否依赖失败的步骤
            dependencies = step.get_dependencies()
            has_failed_dependency = any(dep in failed_outputs for dep in dependencies)
            
            if has_failed_dependency:
                # 跳过此步骤，因为它依赖的步骤失败了
                logger.warning(f"跳过步骤 '{step.id}'，因为它依赖的步骤失败了")
                skipped_result = StepResult(
                    step_id=step.id,
                    output_key=step.output_key,
                    output_value="",
                    execution_time=0.0,
                    error="依赖的步骤失败，跳过执行",
                    success=False
                )
                result.step_results.append(skipped_result)
                failed_outputs.add(step.output_key)
                continue
            
            # 执行步骤
            step_result = self.execute_step(step, variant_config)
            result.step_results.append(step_result)
            
            # 如果步骤执行失败
            if not step_result.success:
                failed_outputs.add(step_result.output_key)
                
                # 如果是必需步骤，停止整个 Pipeline
                if step.required:
                    raise create_execution_error(
                        message=f"必需步骤 '{step.id}' 执行失败: {step_result.error}",
                        suggestion="请检查步骤配置和输入数据",
                        step_id=step.id,
                        sample_id=sample_id
                    )
                else:
                    # 可选步骤失败，记录警告但继续执行
                    logger.warning(f"可选步骤 '{step.id}' 执行失败: {step_result.error}")
            else:
                # 将步骤输出添加到上下文
                self.context[step_result.output_key] = step_result.output_value
        
        # 收集最终输出
        result.final_outputs = self._collect_final_outputs()
        
        # 计算总执行时间、token使用量和parser统计
        result.total_execution_time = time.time() - start_time
        result.total_token_usage = self._calculate_total_token_usage(result.step_results)
        result.total_parser_stats = self._aggregate_parser_stats(result.step_results)
        
        return result
    
    def _execute_sample_concurrent(
        self,
        sample: Dict[str, Any],
        sample_id: str,
        variant: str,
        variant_config: Optional[VariantConfig],
        progress_tracker: Optional[PipelineProgressTracker],
        sample_index: int,
        start_time: float
    ) -> PipelineResult:
        """
        并发执行样本的 Pipeline 流程
        
        实现依赖关系分析、并发组调度、同步点等待和最大并发数控制
        
        Args:
            sample: 测试样本数据
            sample_id: 样本ID
            variant: 变体名称
            variant_config: 变体配置
            progress_tracker: 进度跟踪器
            sample_index: 样本索引
            start_time: 开始时间
            
        Returns:
            Pipeline 执行结果
        """
        result = PipelineResult(
            sample_id=sample_id,
            variant=variant
        )
        
        try:
            # 1. 分析依赖关系
            logger.debug(f"分析 Pipeline 步骤依赖关系")
            dependency_graph = self.dependency_analyzer.analyze_dependencies(self.config.steps)
            
            # 2. 识别并发组
            logger.debug(f"识别可并发执行的步骤组")
            concurrent_groups = self.dependency_analyzer.find_concurrent_groups(dependency_graph)
            
            logger.info(f"Pipeline 将分 {len(concurrent_groups)} 个批次执行")
            for i, group in enumerate(concurrent_groups):
                logger.debug(f"  批次 {i+1}: {', '.join(group)} ({len(group)} 个步骤)")
            
            # 创建步骤ID到步骤对象的映射
            step_map = {step.id: step for step in self.config.steps}
            
            # 跟踪已完成和失败的步骤
            completed_steps: Dict[str, StepResult] = {}
            failed_outputs = set()
            
            # 3. 按批次执行并发组（实现同步点等待）
            for group_index, group_step_ids in enumerate(concurrent_groups):
                logger.debug(f"开始执行批次 {group_index + 1}/{len(concurrent_groups)}")
                
                # 创建当前批次的任务列表
                tasks = []
                skipped_steps = []
                
                for step_id in group_step_ids:
                    step = step_map[step_id]
                    
                    # 检查依赖是否满足
                    dependencies = step.depends_on
                    # 也检查 input_mapping 中的依赖
                    for source in step.input_mapping.values():
                        # 找到产生这个输出的步骤
                        for other_step in self.config.steps:
                            if other_step.output_key == source and other_step.id not in dependencies:
                                dependencies.append(other_step.id)
                    
                    # 检查是否有必需的依赖失败了
                    has_failed_dependency = False
                    for dep_id in dependencies:
                        if dep_id in completed_steps:
                            dep_result = completed_steps[dep_id]
                            if not dep_result.success and step_map[dep_id].required:
                                has_failed_dependency = True
                                break
                    
                    if has_failed_dependency:
                        # 跳过此步骤
                        logger.warning(f"跳过步骤 '{step.id}'，因为必需的依赖步骤失败了")
                        skipped_result = StepResult(
                            step_id=step.id,
                            output_key=step.output_key,
                            output_value="",
                            execution_time=0.0,
                            error="必需的依赖步骤失败，跳过执行",
                            success=False
                        )
                        completed_steps[step.id] = skipped_result
                        failed_outputs.add(step.output_key)
                        skipped_steps.append(step.id)
                        continue
                    
                    # 创建任务
                    task = Task(
                        id=step.id,
                        func=self._execute_step_wrapper,
                        args=(step, variant_config),
                        kwargs={},
                        dependencies=[],  # 同一批次内的任务没有依赖关系
                        required=step.required,
                        metadata={"step": step}
                    )
                    tasks.append(task)
                
                # 如果当前批次没有任务（都被跳过了），继续下一批次
                if not tasks:
                    logger.debug(f"批次 {group_index + 1} 的所有步骤都被跳过")
                    continue
                
                # 4. 并发执行当前批次的任务（实现最大并发数控制）
                logger.debug(f"并发执行批次 {group_index + 1} 的 {len(tasks)} 个任务（最大并发数: {self.max_workers}）")
                
                # 创建进度回调函数，将并发执行进度传递给 PipelineProgressTracker
                def concurrent_progress_callback(exec_progress):
                    """并发执行进度回调"""
                    if progress_tracker:
                        # 计算当前样本的整体进度
                        # 已完成的批次数 + 当前批次的进度
                        completed_batches = group_index
                        current_batch_progress = exec_progress.completion_rate
                        
                        # 计算总体步骤进度（近似）
                        total_batches = len(concurrent_groups)
                        overall_progress = (completed_batches + current_batch_progress) / total_batches
                        
                        # 更新进度跟踪器
                        # 使用当前批次中正在执行的任务作为当前步骤
                        current_step_name = f"批次 {group_index + 1}/{total_batches}"
                        if exec_progress.running > 0:
                            current_step_name += f" (并发执行 {exec_progress.running} 个任务)"
                        
                        progress_tracker.update_sample(
                            sample_index=sample_index,
                            sample_id=sample_id,
                            step_index=int(overall_progress * len(self.config.steps)),
                            step_name=current_step_name,
                            failed=False
                        )
                
                # 使用 ConcurrentExecutor 执行任务
                task_results = self.concurrent_executor.execute_concurrent(
                    tasks=tasks,
                    progress_callback=concurrent_progress_callback
                )
                
                # 处理任务结果
                for task_result in task_results:
                    step_id = task_result.task_id
                    step = step_map[step_id]
                    
                    if task_result.success:
                        # 任务成功，提取 StepResult
                        step_result = task_result.result
                        completed_steps[step_id] = step_result
                        
                        # 将步骤输出添加到上下文
                        self.context[step_result.output_key] = step_result.output_value
                        
                        logger.debug(f"步骤 '{step_id}' 执行成功")
                    else:
                        # 任务失败
                        logger.warning(f"步骤 '{step_id}' 执行失败: {task_result.error}")
                        
                        # 检查是否是 StepResult（execute_step 返回的）
                        if isinstance(task_result.result, StepResult):
                            step_result = task_result.result
                        else:
                            step_result = StepResult(
                                step_id=step_id,
                                output_key=step.output_key,
                                output_value="",
                                execution_time=task_result.execution_time,
                                error=task_result.error,
                                success=False
                            )
                        
                        completed_steps[step_id] = step_result
                        failed_outputs.add(step.output_key)
                        
                        # 如果是必需步骤，停止整个 Pipeline
                        if step.required:
                            # 先收集已完成的步骤结果
                            for s in self.config.steps:
                                if s.id in completed_steps:
                                    result.step_results.append(completed_steps[s.id])
                            
                            raise create_execution_error(
                                message=f"必需步骤 '{step_id}' 执行失败: {step_result.error}",
                                suggestion="请检查步骤配置和输入数据",
                                step_id=step_id,
                                sample_id=sample_id
                            )
                
                logger.debug(f"批次 {group_index + 1} 执行完成")
            
            # 按原始步骤顺序收集结果
            for step in self.config.steps:
                if step.id in completed_steps:
                    result.step_results.append(completed_steps[step.id])
            
            # 检查是否有必需步骤失败
            for step_result in result.step_results:
                step = step_map[step_result.step_id]
                if not step_result.success and step.required:
                    raise create_execution_error(
                        message=f"必需步骤 '{step_result.step_id}' 执行失败: {step_result.error}",
                        suggestion="请检查步骤配置和输入数据",
                        step_id=step_result.step_id,
                        sample_id=sample_id
                    )
            
            # 收集最终输出
            result.final_outputs = self._collect_final_outputs()
            
            # 计算总执行时间、token使用量和parser统计
            result.total_execution_time = time.time() - start_time
            result.total_token_usage = self._calculate_total_token_usage(result.step_results)
            result.total_parser_stats = self._aggregate_parser_stats(result.step_results)
            
            logger.info(f"样本 {sample_id} 并发执行完成，总耗时 {result.total_execution_time:.2f}秒")
            
        except Exception as e:
            result.error = str(e)
            result.total_execution_time = time.time() - start_time
            logger.error(f"样本 {sample_id} 并发执行失败: {e}")
        
        return result
    
    def _execute_step_wrapper(self, step: StepConfig, variant_config: Optional[VariantConfig]) -> StepResult:
        """
        步骤执行包装器，用于并发执行
        
        这个方法会被 ConcurrentExecutor 调用，需要返回 StepResult
        
        Args:
            step: 步骤配置
            variant_config: 变体配置
            
        Returns:
            StepResult: 步骤执行结果
        """
        return self.execute_step(step, variant_config)
    
    def execute_step(self, step: StepConfig, variant_config: Optional[VariantConfig] = None) -> StepResult:
        """
        执行单个步骤
        
        Args:
            step: 步骤配置
            variant_config: 变体配置（可选）
            
        Returns:
            步骤执行结果
        """
        step_start_time = time.time()
        
        try:
            # 解析输入映射
            step_inputs = self._resolve_input_mapping(step.input_mapping)
            
            # 根据步骤类型执行不同的逻辑
            if step.type == "code_node":
                # 执行代码节点
                logger.debug(f"执行代码节点步骤 '{step.id}'")
                output_content, execution_time = self._execute_code_node(
                    step=step,
                    inputs=step_inputs,
                    start_time=step_start_time
                )
                
                return StepResult(
                    step_id=step.id,
                    output_key=step.output_key,
                    output_value=output_content,
                    execution_time=execution_time,
                    token_usage={},  # 代码节点不使用 token
                    parser_stats=None,
                    success=True
                )
            
            elif step.type == "batch_aggregator":
                # 执行批量聚合步骤
                logger.debug(f"执行批量聚合步骤 '{step.id}'")
                output_content, execution_time = self._execute_batch_aggregator(
                    step=step,
                    inputs=step_inputs,
                    start_time=step_start_time
                )
                
                return StepResult(
                    step_id=step.id,
                    output_key=step.output_key,
                    output_value=output_content,
                    execution_time=execution_time,
                    token_usage={},  # 批量聚合不使用 token
                    parser_stats=None,
                    success=True
                )
            
            elif step.type == "agent_flow":
                # 检查是否是批量模式
                if step.batch_mode:
                    # 执行批量 Agent/Flow
                    logger.debug(f"执行批量 Agent/Flow 步骤 '{step.id}'")
                    output_content, token_usage, parser_stats, execution_time = self._execute_batch_agent_flow(
                        step=step,
                        inputs=step_inputs,
                        variant_config=variant_config,
                        start_time=step_start_time
                    )
                    
                    return StepResult(
                        step_id=step.id,
                        output_key=step.output_key,
                        output_value=output_content,
                        execution_time=execution_time,
                        token_usage=token_usage,
                        parser_stats=parser_stats,
                        success=True
                    )
                else:
                    # 执行单个 Agent/Flow
                    flow_name, model_override = self._resolve_step_config(step, variant_config)
                    
                    logger.debug(f"执行步骤 '{step.id}': agent={step.agent}, flow={flow_name}")
                    
                    output_content, token_usage, parser_stats = self._execute_agent_flow(
                        agent_id=step.agent,
                        flow_name=flow_name,
                        inputs=step_inputs,
                        model_override=model_override
                    )
                    
                    execution_time = time.time() - step_start_time
                    
                    return StepResult(
                        step_id=step.id,
                        output_key=step.output_key,
                        output_value=output_content,
                        execution_time=execution_time,
                        token_usage=token_usage,
                        parser_stats=parser_stats,
                        success=True
                    )
            
            else:
                # 不支持的步骤类型
                raise create_config_error(
                    message=f"不支持的步骤类型: {step.type}",
                    suggestion="支持的步骤类型: agent_flow, code_node, batch_aggregator"
                )
            
        except Exception as e:
            execution_time = time.time() - step_start_time
            error_msg = f"步骤执行失败: {str(e)}"
            
            return StepResult(
                step_id=step.id,
                output_key=step.output_key,
                output_value="",
                execution_time=execution_time,
                error=error_msg,
                success=False
            )
    
    def _get_variant_config(self, variant: str) -> Optional[VariantConfig]:
        """获取变体配置"""
        if variant == "baseline":
            return None
        
        if variant not in self.config.variants:
            raise create_config_error(
                message=f"未找到变体配置: {variant}",
                suggestion=f"请检查 Pipeline 配置中是否定义了变体 '{variant}'"
            )
        
        return self.config.variants[variant]
    
    def _resolve_input_mapping(self, input_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        解析输入映射，将映射源转换为实际值
        
        Args:
            input_mapping: 输入映射配置 {参数名: 映射源}
            
        Returns:
            解析后的输入参数字典
        """
        resolved_inputs = {}
        
        for param_name, source in input_mapping.items():
            if source in self.context:
                # 从上下文中获取值（包括前序步骤输出和testset字段）
                resolved_inputs[param_name] = self.context[source]
            elif source in self.context.get("testset_fields", {}):
                # 从testset字段中获取值
                resolved_inputs[param_name] = self.context["testset_fields"][source]
            else:
                # 如果找不到映射源，使用空字符串作为默认值
                logger.warning(f"输入映射源 '{source}' 未找到，使用空字符串作为默认值")
                resolved_inputs[param_name] = ""
        
        return resolved_inputs
    
    def _resolve_step_config(self, step: StepConfig, variant_config: Optional[VariantConfig]) -> Tuple[str, Optional[str]]:
        """
        解析步骤配置，考虑变体覆盖
        
        Args:
            step: 原始步骤配置
            variant_config: 变体配置
            
        Returns:
            (flow_name, model_override) 元组
        """
        flow_name = step.flow
        model_override = step.model_override
        
        # 应用变体覆盖
        if variant_config and step.id in variant_config.overrides:
            override = variant_config.overrides[step.id]
            if override.flow:
                flow_name = override.flow
            if override.model:
                model_override = override.model
        
        # 应用 baseline 配置
        if variant_config is None and self.config.baseline and step.id in self.config.baseline.steps:
            baseline_step = self.config.baseline.steps[step.id]
            flow_name = baseline_step.flow
            if baseline_step.model:
                model_override = baseline_step.model
        
        return flow_name, model_override
    
    def _execute_agent_flow(self, agent_id: str, flow_name: str, inputs: Dict[str, Any], model_override: Optional[str] = None) -> Tuple[str, Dict[str, int], Optional[Dict[str, Any]]]:
        """
        执行 Agent/Flow 组合
        
        Args:
            agent_id: Agent ID
            flow_name: Flow 名称
            inputs: 输入参数
            model_override: 模型覆盖（可选）
            
        Returns:
            (输出内容, token使用统计, parser统计) 元组
        """
        try:
            # 验证 agent 存在
            agent = load_agent(agent_id)
            
            # 验证 flow 存在
            flow_exists = any(flow.name == flow_name for flow in agent.flows)
            if not flow_exists:
                available_flows = [f.name for f in agent.flows]
                raise create_config_error(
                    message=f"Agent '{agent_id}' 中不存在 flow '{flow_name}'",
                    suggestion=f"可用的 flows: {', '.join(available_flows)}"
                )
            
            # 准备额外变量，包含模型覆盖
            extra_vars = inputs.copy()
            if model_override:
                # 注意：模型覆盖需要在 chains.py 中支持
                extra_vars["_model_override"] = model_override
            
            # 执行 flow
            output_content, token_usage, parser_stats = run_flow_with_tokens(
                flow_name=flow_name,
                extra_vars=extra_vars,
                agent_id=agent_id
            )
            
            return output_content, token_usage, parser_stats
            
        except Exception as e:
            raise create_execution_error(
                message=f"执行 Agent/Flow 失败: {str(e)}",
                suggestion="请检查 Agent 配置、Flow 定义和网络连接"
            ) from e
    
    def _execute_code_node(self, step: StepConfig, inputs: Dict[str, Any], start_time: float) -> Tuple[Any, float]:
        """
        执行代码节点
        
        Args:
            step: 步骤配置
            inputs: 输入数据
            start_time: 步骤开始时间
            
        Returns:
            (输出内容, 执行时间) 元组
            
        Raises:
            Exception: 如果代码执行失败
        """
        try:
            # 获取代码节点配置
            code_config = step.code_config
            
            # 向后兼容：如果没有 code_config，从 step 直接字段构建
            if not code_config:
                code_config = CodeNodeConfig(
                    language=step.language or "python",
                    code=step.code,
                    code_file=step.code_file,
                    timeout=step.timeout or 30,
                    env_vars={}
                )
            
            # 验证配置
            validation_errors = code_config.validate()
            if validation_errors:
                raise create_config_error(
                    message=f"代码节点配置无效: {', '.join(validation_errors)}",
                    suggestion="请检查代码节点的 language、code 或 code_file 配置"
                )
            
            # 执行代码
            if code_config.code_file:
                # 从文件执行
                code_file_path = Path(code_config.code_file)
                logger.debug(f"从文件执行代码: {code_file_path}")
                
                result = self.code_executor.execute_from_file(
                    file_path=code_file_path,
                    language=code_config.language,
                    inputs=inputs,
                    timeout=code_config.timeout
                )
            else:
                # 执行内联代码
                logger.debug(f"执行内联 {code_config.language} 代码")
                
                result = self.code_executor.execute(
                    code=code_config.code,
                    language=code_config.language,
                    inputs=inputs,
                    timeout=code_config.timeout
                )
            
            # 检查执行结果
            if not result.success:
                error_details = []
                error_details.append(f"错误: {result.error}")
                
                if result.stderr:
                    error_details.append(f"标准错误: {result.stderr}")
                
                if result.stack_trace:
                    error_details.append(f"堆栈跟踪:\n{result.stack_trace}")
                
                if result.timeout:
                    error_details.append(f"执行超时 ({code_config.timeout}秒)")
                
                raise create_execution_error(
                    message=f"代码节点执行失败:\n" + "\n".join(error_details),
                    suggestion="请检查代码逻辑、输入数据格式和超时设置",
                    step_id=step.id
                )
            
            execution_time = time.time() - start_time
            logger.debug(f"代码节点执行成功，耗时 {execution_time:.2f}秒")
            
            return result.output, execution_time
            
        except Exception as e:
            # 如果是我们自己抛出的错误，直接传递
            if isinstance(e, type(create_execution_error("", ""))):
                raise
            
            # 其他异常，包装后抛出
            raise create_execution_error(
                message=f"代码节点执行过程中出现异常: {str(e)}",
                suggestion="请检查代码节点配置和代码逻辑",
                step_id=step.id
            ) from e
    
    def _execute_batch_aggregator(self, step: StepConfig, inputs: Dict[str, Any], start_time: float) -> Tuple[Any, float]:
        """
        执行批量聚合步骤
        
        Args:
            step: 步骤配置
            inputs: 输入数据（应包含要聚合的items）
            start_time: 步骤开始时间
            
        Returns:
            (聚合结果, 执行时间) 元组
            
        Raises:
            Exception: 如果聚合失败
        """
        try:
            # 获取要聚合的items
            items = inputs.get("items", [])
            
            if not items:
                logger.warning(f"批量聚合步骤 '{step.id}' 没有收到任何items")
                return [], time.time() - start_time
            
            # 确保items是列表
            if not isinstance(items, list):
                items = [items]
            
            logger.info(f"批量聚合步骤 '{step.id}': 聚合 {len(items)} 个items，策略={step.aggregation_strategy}")
            
            # 准备聚合参数
            kwargs = {}
            
            if step.aggregation_strategy == "concat":
                kwargs["separator"] = step.separator or "\n"
            elif step.aggregation_strategy == "stats":
                kwargs["fields"] = step.fields or []
            elif step.aggregation_strategy == "filter":
                kwargs["condition"] = step.condition
            elif step.aggregation_strategy == "group":
                kwargs["group_by"] = step.group_by
            elif step.aggregation_strategy == "summary":
                kwargs["summary_fields"] = step.summary_fields or []
            elif step.aggregation_strategy == "custom":
                # 自定义聚合使用代码
                code = step.aggregation_code or step.code
                if not code and step.code_file:
                    # 从文件读取代码
                    from pathlib import Path
                    code_file_path = Path(step.code_file)
                    if code_file_path.exists():
                        code = code_file_path.read_text()
                    else:
                        raise create_config_error(
                            message=f"代码文件不存在: {step.code_file}",
                            suggestion="请检查 code_file 路径是否正确"
                        )
                
                kwargs["code"] = code
                kwargs["language"] = step.language or "python"
                kwargs["timeout"] = step.timeout or 30
            
            # 执行聚合
            result = self.batch_aggregator.aggregate(
                items=items,
                strategy=step.aggregation_strategy,
                **kwargs
            )
            
            # 检查聚合结果
            if not result.success:
                raise create_execution_error(
                    message=f"批量聚合失败: {result.error}",
                    suggestion="请检查聚合策略配置和输入数据格式",
                    step_id=step.id
                )
            
            execution_time = time.time() - start_time
            logger.info(f"批量聚合步骤 '{step.id}' 完成，耗时 {execution_time:.2f}秒")
            
            return result.result, execution_time
            
        except Exception as e:
            # 如果是我们自己抛出的错误，直接传递
            if isinstance(e, type(create_execution_error("", ""))):
                raise
            
            # 其他异常，包装后抛出
            raise create_execution_error(
                message=f"批量聚合步骤执行过程中出现异常: {str(e)}",
                suggestion="请检查聚合配置和输入数据",
                step_id=step.id
            ) from e
    
    def _execute_batch_agent_flow(
        self, 
        step: StepConfig, 
        inputs: Dict[str, Any], 
        variant_config: Optional[VariantConfig],
        start_time: float
    ) -> Tuple[List[Any], Dict[str, int], Optional[Dict[str, Any]], float]:
        """
        执行批量 Agent/Flow 步骤
        
        Args:
            step: 步骤配置
            inputs: 输入数据
            variant_config: 变体配置
            start_time: 步骤开始时间
            
        Returns:
            (批量输出列表, 总token使用量, 聚合parser统计, 执行时间) 元组
            
        Raises:
            Exception: 如果批量执行失败
        """
        try:
            # 解析步骤配置
            flow_name, model_override = self._resolve_step_config(step, variant_config)
            
            # 获取批量数据
            # 批量数据应该是一个列表，每个元素是一个输入字典
            batch_data = []
            
            # 检查inputs中是否有列表类型的数据
            for param_name, value in inputs.items():
                if isinstance(value, list):
                    # 找到列表数据，为每个元素创建输入字典
                    for item in value:
                        item_inputs = {}
                        # 将当前item作为该参数的值
                        item_inputs[param_name] = item
                        # 添加其他非列表参数
                        for other_param, other_value in inputs.items():
                            if other_param != param_name and not isinstance(other_value, list):
                                item_inputs[other_param] = other_value
                        batch_data.append(item_inputs)
                    break
            
            # 如果没有找到列表数据，将整个inputs作为单个批次项
            if not batch_data:
                batch_data = [inputs]
            
            logger.info(f"批量执行步骤 '{step.id}': {len(batch_data)} 个items, batch_size={step.batch_size}, concurrent={step.concurrent}")
            
            # 分批处理
            batch_size = step.batch_size or 10
            all_results = []
            total_token_usage = {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0}
            all_parser_stats = []
            
            # 将数据分成批次
            batches = [batch_data[i:i + batch_size] for i in range(0, len(batch_data), batch_size)]
            
            logger.info(f"将 {len(batch_data)} 个items分成 {len(batches)} 个批次")
            
            for batch_index, batch in enumerate(batches):
                logger.debug(f"处理批次 {batch_index + 1}/{len(batches)}, 包含 {len(batch)} 个items")
                
                if step.concurrent:
                    # 并发执行批次
                    batch_results = self._execute_batch_concurrent(
                        agent_id=step.agent,
                        flow_name=flow_name,
                        batch_items=batch,
                        model_override=model_override,
                        max_workers=step.max_workers or 4
                    )
                else:
                    # 顺序执行批次
                    batch_results = self._execute_batch_sequential(
                        agent_id=step.agent,
                        flow_name=flow_name,
                        batch_items=batch,
                        model_override=model_override
                    )
                
                # 收集结果
                for result in batch_results:
                    all_results.append(result["output"])
                    
                    # 累加token使用量
                    if "token_usage" in result:
                        for key in total_token_usage:
                            total_token_usage[key] += result["token_usage"].get(key, 0)
                    
                    # 收集parser统计
                    if "parser_stats" in result and result["parser_stats"]:
                        all_parser_stats.append(result["parser_stats"])
            
            # 聚合parser统计
            aggregated_parser_stats = None
            if all_parser_stats:
                aggregated_parser_stats = {
                    "success_count": sum(s.get("success_count", 0) for s in all_parser_stats),
                    "failure_count": sum(s.get("failure_count", 0) for s in all_parser_stats),
                    "total_retry_count": sum(s.get("total_retry_count", 0) for s in all_parser_stats)
                }
                total_attempts = aggregated_parser_stats["success_count"] + aggregated_parser_stats["failure_count"]
                if total_attempts > 0:
                    aggregated_parser_stats["success_rate"] = aggregated_parser_stats["success_count"] / total_attempts
                    aggregated_parser_stats["average_retries"] = aggregated_parser_stats["total_retry_count"] / total_attempts
            
            execution_time = time.time() - start_time
            logger.info(f"批量执行步骤 '{step.id}' 完成，处理了 {len(all_results)} 个items，耗时 {execution_time:.2f}秒")
            
            return all_results, total_token_usage, aggregated_parser_stats, execution_time
            
        except Exception as e:
            # 如果是我们自己抛出的错误，直接传递
            if isinstance(e, type(create_execution_error("", ""))):
                raise
            
            # 其他异常，包装后抛出
            raise create_execution_error(
                message=f"批量执行步骤过程中出现异常: {str(e)}",
                suggestion="请检查批量配置和输入数据",
                step_id=step.id
            ) from e
    
    def _execute_batch_concurrent(
        self,
        agent_id: str,
        flow_name: str,
        batch_items: List[Dict[str, Any]],
        model_override: Optional[str],
        max_workers: int
    ) -> List[Dict[str, Any]]:
        """
        并发执行批量items
        
        Args:
            agent_id: Agent ID
            flow_name: Flow 名称
            batch_items: 批量输入数据列表
            model_override: 模型覆盖
            max_workers: 最大并发数
            
        Returns:
            批量结果列表
        """
        # 创建任务列表
        tasks = []
        for i, item_inputs in enumerate(batch_items):
            task = Task(
                id=f"batch_item_{i}",
                func=self._execute_agent_flow_wrapper,
                args=(agent_id, flow_name, item_inputs, model_override),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={"item_index": i}
            )
            tasks.append(task)
        
        # 使用并发执行器执行
        task_results = self.concurrent_executor.execute_concurrent(
            tasks=tasks,
            progress_callback=None
        )
        
        # 收集结果
        results = []
        for task_result in task_results:
            if task_result.success:
                output_content, token_usage, parser_stats = task_result.result
                results.append({
                    "output": output_content,
                    "token_usage": token_usage,
                    "parser_stats": parser_stats
                })
            else:
                # 批量执行中的单个item失败，记录错误但继续
                logger.warning(f"批量item {task_result.task_id} 执行失败: {task_result.error}")
                results.append({
                    "output": "",
                    "token_usage": {},
                    "parser_stats": None,
                    "error": task_result.error
                })
        
        return results
    
    def _execute_batch_sequential(
        self,
        agent_id: str,
        flow_name: str,
        batch_items: List[Dict[str, Any]],
        model_override: Optional[str]
    ) -> List[Dict[str, Any]]:
        """
        顺序执行批量items
        
        Args:
            agent_id: Agent ID
            flow_name: Flow 名称
            batch_items: 批量输入数据列表
            model_override: 模型覆盖
            
        Returns:
            批量结果列表
        """
        results = []
        for i, item_inputs in enumerate(batch_items):
            try:
                output_content, token_usage, parser_stats = self._execute_agent_flow(
                    agent_id=agent_id,
                    flow_name=flow_name,
                    inputs=item_inputs,
                    model_override=model_override
                )
                results.append({
                    "output": output_content,
                    "token_usage": token_usage,
                    "parser_stats": parser_stats
                })
            except Exception as e:
                # 批量执行中的单个item失败，记录错误但继续
                logger.warning(f"批量item {i} 执行失败: {str(e)}")
                results.append({
                    "output": "",
                    "token_usage": {},
                    "parser_stats": None,
                    "error": str(e)
                })
        
        return results
    
    def _execute_agent_flow_wrapper(
        self,
        agent_id: str,
        flow_name: str,
        inputs: Dict[str, Any],
        model_override: Optional[str]
    ) -> Tuple[str, Dict[str, int], Optional[Dict[str, Any]]]:
        """
        Agent/Flow 执行包装器，用于并发执行
        
        Args:
            agent_id: Agent ID
            flow_name: Flow 名称
            inputs: 输入参数
            model_override: 模型覆盖
            
        Returns:
            (输出内容, token使用统计, parser统计) 元组
        """
        return self._execute_agent_flow(agent_id, flow_name, inputs, model_override)
    
    def _collect_final_outputs(self) -> Dict[str, Any]:
        """收集最终输出"""
        final_outputs = {}
        
        for output_spec in self.config.outputs:
            if output_spec.key in self.context:
                final_outputs[output_spec.key] = self.context[output_spec.key]
            else:
                logger.warning(f"输出键 '{output_spec.key}' 在上下文中未找到")
                final_outputs[output_spec.key] = ""
        
        return final_outputs
    
    def _calculate_total_token_usage(self, step_results: List[StepResult]) -> Dict[str, int]:
        """计算总token使用量"""
        total_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0
        }
        
        for step_result in step_results:
            if step_result.token_usage:
                for key in total_usage:
                    total_usage[key] += step_result.token_usage.get(key, 0)
        
        return total_usage
    
    def _aggregate_parser_stats(self, step_results: List[StepResult]) -> Optional[Dict[str, Any]]:
        """聚合所有步骤的 Parser 统计信息"""
        total_stats = {
            "success_count": 0,
            "failure_count": 0,
            "total_retry_count": 0,
            "success_rate": 0.0,
            "average_retries": 0.0
        }
        
        has_stats = False
        
        for step_result in step_results:
            if step_result.parser_stats:
                has_stats = True
                total_stats["success_count"] += step_result.parser_stats.get("success_count", 0)
                total_stats["failure_count"] += step_result.parser_stats.get("failure_count", 0)
                total_stats["total_retry_count"] += step_result.parser_stats.get("total_retry_count", 0)
        
        if not has_stats:
            return None
        
        # 计算聚合的成功率和平均重试次数
        total_attempts = total_stats["success_count"] + total_stats["failure_count"]
        if total_attempts > 0:
            total_stats["success_rate"] = total_stats["success_count"] / total_attempts
            total_stats["average_retries"] = total_stats["total_retry_count"] / total_attempts
        
        return total_stats
    
    def validate_pipeline(self) -> List[str]:
        """
        验证 Pipeline 配置的有效性
        
        Returns:
            错误列表，空列表表示验证通过
        """
        errors = []
        
        try:
            # 基本配置验证
            errors.extend(self.config.validate())
            
            # 验证每个步骤的 agent 和 flow 是否存在
            for step in self.config.steps:
                try:
                    agent = load_agent(step.agent)
                    flow_exists = any(flow.name == step.flow for flow in agent.flows)
                    if not flow_exists:
                        errors.append(f"步骤 '{step.id}' 引用的 flow '{step.flow}' 在 agent '{step.agent}' 中不存在")
                except Exception as e:
                    errors.append(f"步骤 '{step.id}' 引用的 agent '{step.agent}' 加载失败: {str(e)}")
            
            # 验证 baseline 配置
            if self.config.baseline:
                for step_id, baseline_step in self.config.baseline.steps.items():
                    # 找到对应的 pipeline 步骤
                    pipeline_step = None
                    for step in self.config.steps:
                        if step.id == step_id:
                            pipeline_step = step
                            break
                    
                    if pipeline_step:
                        try:
                            agent = load_agent(pipeline_step.agent)
                            flow_exists = any(flow.name == baseline_step.flow for flow in agent.flows)
                            if not flow_exists:
                                errors.append(f"Baseline 步骤 '{step_id}' 引用的 flow '{baseline_step.flow}' 在 agent '{pipeline_step.agent}' 中不存在")
                        except Exception as e:
                            errors.append(f"Baseline 步骤 '{step_id}' 验证失败: {str(e)}")
            
            # 验证变体配置
            for variant_name, variant in self.config.variants.items():
                for step_id, override in variant.overrides.items():
                    if override.flow:
                        # 找到对应的 pipeline 步骤
                        pipeline_step = None
                        for step in self.config.steps:
                            if step.id == step_id:
                                pipeline_step = step
                                break
                        
                        if pipeline_step:
                            try:
                                agent = load_agent(pipeline_step.agent)
                                flow_exists = any(flow.name == override.flow for flow in agent.flows)
                                if not flow_exists:
                                    errors.append(f"变体 '{variant_name}' 步骤 '{step_id}' 引用的 flow '{override.flow}' 在 agent '{pipeline_step.agent}' 中不存在")
                            except Exception as e:
                                errors.append(f"变体 '{variant_name}' 步骤 '{step_id}' 验证失败: {str(e)}")
            
        except Exception as e:
            errors.append(f"Pipeline 验证过程中出现异常: {str(e)}")
        
        return errors


    @staticmethod
    def generate_aggregate_performance_summary(
        results: List[PipelineResult],
        detailed: bool = False
    ) -> Dict[str, Any]:
        """
        生成多个结果的聚合性能摘要
        
        Args:
            results: Pipeline 执行结果列表
            detailed: 是否包含详细信息
            
        Returns:
            聚合性能摘要字典
        """
        if not results:
            return {
                "total_samples": 0,
                "successful_samples": 0,
                "failed_samples": 0,
                "total_execution_time": 0.0,
                "average_execution_time": 0.0,
                "total_token_usage": {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
                "success_rate": 0.0
            }
        
        total_samples = len(results)
        successful_samples = len([r for r in results if not r.error])
        failed_samples = total_samples - successful_samples
        
        total_execution_time = sum(r.total_execution_time for r in results)
        average_execution_time = total_execution_time / total_samples if total_samples > 0 else 0.0
        
        # 聚合 token 使用量
        total_token_usage = {
            "input_tokens": sum(r.total_token_usage.get("input_tokens", 0) for r in results),
            "output_tokens": sum(r.total_token_usage.get("output_tokens", 0) for r in results),
            "total_tokens": sum(r.total_token_usage.get("total_tokens", 0) for r in results)
        }
        
        # 聚合 parser 统计
        total_parser_stats = None
        parser_results = [r for r in results if r.total_parser_stats]
        if parser_results:
            total_parser_stats = {
                "success_count": sum(r.total_parser_stats.get("success_count", 0) for r in parser_results),
                "failure_count": sum(r.total_parser_stats.get("failure_count", 0) for r in parser_results),
                "total_retry_count": sum(r.total_parser_stats.get("total_retry_count", 0) for r in parser_results)
            }
            total_attempts = total_parser_stats["success_count"] + total_parser_stats["failure_count"]
            if total_attempts > 0:
                total_parser_stats["success_rate"] = total_parser_stats["success_count"] / total_attempts
                total_parser_stats["average_retries"] = total_parser_stats["total_retry_count"] / total_attempts
            else:
                total_parser_stats["success_rate"] = 0.0
                total_parser_stats["average_retries"] = 0.0
        
        summary = {
            "total_samples": total_samples,
            "successful_samples": successful_samples,
            "failed_samples": failed_samples,
            "success_rate": successful_samples / total_samples if total_samples > 0 else 0.0,
            "total_execution_time": total_execution_time,
            "average_execution_time": average_execution_time,
            "total_token_usage": total_token_usage,
            "average_token_usage": {
                "input_tokens": total_token_usage["input_tokens"] / total_samples if total_samples > 0 else 0,
                "output_tokens": total_token_usage["output_tokens"] / total_samples if total_samples > 0 else 0,
                "total_tokens": total_token_usage["total_tokens"] / total_samples if total_samples > 0 else 0
            }
        }
        
        if total_parser_stats:
            summary["parser_stats"] = total_parser_stats
        
        if detailed:
            summary["sample_summaries"] = [r.get_performance_summary(detailed=False) for r in results]
        
        return summary


def create_progress_printer(pipeline_name: str) -> callable:
    """创建进度打印回调函数"""
    def print_progress(current: int, total: int, message: str = ""):
        percentage = (current / total) * 100 if total > 0 else 0
        end = "\n" if current == total else ""
        print(
            f"\r正在执行 Pipeline: {pipeline_name} [{current}/{total}] {percentage:.1f}% {message}",
            end=end,
            flush=True,
        )

    return print_progress