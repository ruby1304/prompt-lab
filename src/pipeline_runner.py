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

from .models import PipelineConfig, StepConfig, VariantConfig, EvaluationResult
from .chains import run_flow_with_tokens
from .agent_registry import load_agent
from .progress_tracker import PipelineProgressTracker
from .checkpoint_manager import CheckpointManager, ResumableExecutor
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
    
    def __init__(self, config: PipelineConfig):
        """
        初始化 Pipeline 执行器
        
        Args:
            config: Pipeline 配置对象
        """
        self.config = config
        self.context: Dict[str, Any] = {}
        self.progress_callback: Optional[callable] = None
        self.error_handler = ErrorHandler()
        
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
            
        except Exception as e:
            result.error = str(e)
            result.total_execution_time = time.time() - start_time
            logger.error(f"样本 {sample_id} 执行失败: {e}")
        
        return result
    
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
            
            # 获取实际使用的 flow 和 model
            flow_name, model_override = self._resolve_step_config(step, variant_config)
            
            logger.debug(f"执行步骤 '{step.id}': agent={step.agent}, flow={flow_name}")
            
            # 执行 Agent/Flow
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