# src/unified_evaluator.py
"""
统一评估器

提供统一的评估接口，适用于 Agent 和 Pipeline 评估。
使用相同的规则引擎和 Judge 评估逻辑。
"""

from __future__ import annotations

import logging
from typing import Dict, Any, Optional, Tuple

from .models import EvaluationConfig, EvaluationResult
from .eval_rules import apply_rules_to_row
from .eval_llm_judge import judge_one, build_judge_chain, render_case_for_judge
from .agent_registry import load_agent, AgentConfig

logger = logging.getLogger(__name__)


class UnifiedEvaluator:
    """统一的评估器，处理 Agent 和 Pipeline 评估"""
    
    def __init__(self, config: EvaluationConfig):
        """
        初始化统一评估器
        
        Args:
            config: 评估配置
        """
        self.config = config
        self.judge_chain = None
        self.judge_agent = None
        
        # 如果启用了 Judge 评估，构建 Judge chain
        if config.judge_enabled and config.judge_agent_id and config.judge_flow:
            try:
                self.judge_agent = load_agent(config.judge_agent_id)
                logger.info(f"使用 Judge Agent: {config.judge_agent_id}/{config.judge_flow}")
            except Exception as e:
                logger.warning(f"加载 Judge Agent 失败: {e}")
                self.config.judge_enabled = False
    
    def evaluate_agent_output(
        self,
        agent_id: str,
        flow_name: str,
        test_case: Dict[str, Any],
        output: str,
        execution_time: float = 0.0
    ) -> EvaluationResult:
        """
        评估 Agent 输出
        
        Args:
            agent_id: Agent ID
            flow_name: Flow 名称
            test_case: 测试用例
            output: Agent 输出
            execution_time: 执行时间
            
        Returns:
            评估结果
        """
        sample_id = test_case.get("id", "unknown")
        
        # 初始化评估结果
        eval_result = EvaluationResult(
            sample_id=sample_id,
            entity_type="agent",
            entity_id=agent_id,
            variant=flow_name,
            overall_score=0.0,
            must_have_pass=True,
            execution_time=execution_time
        )
        
        # 加载 agent 配置（用于规则评估）
        try:
            agent_config = load_agent(agent_id)
        except Exception as e:
            logger.warning(f"加载 Agent 配置失败: {e}")
            eval_result.judge_feedback = f"加载 Agent 配置失败: {e}"
            return eval_result
        
        # 应用规则评估
        if self.config.rules or agent_config.evaluation.get("rules"):
            try:
                rule_result = apply_rules_to_row(
                    agent_config,
                    {"output": output},
                    "output"
                )
                eval_result.must_have_pass = bool(rule_result.get("rule_pass", 1))
                rule_violations = rule_result.get("rule_violations", "")
                if rule_violations:
                    eval_result.rule_violations = [
                        v.strip() for v in rule_violations.split(",") if v.strip()
                    ]
            except Exception as e:
                logger.warning(f"规则评估失败: {e}")
        
        # 应用 LLM Judge 评估
        if self.config.judge_enabled and self.judge_agent:
            try:
                # 构建 judge chain（如果还没有构建）
                if not self.judge_chain:
                    self.judge_chain = build_judge_chain(
                        task_agent_cfg=agent_config,
                        judge_agent_cfg=self.judge_agent,
                        judge_flow_name=self.config.judge_flow
                    )
                
                # 调用 Judge
                judge_data, token_info = judge_one(
                    task_agent_cfg=agent_config,
                    flow_name=flow_name,
                    case=test_case,
                    output=output,
                    judge_config=self.judge_chain,
                    judge_flow_name=self.config.judge_flow
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
                logger.warning(f"Judge 评估失败: {e}")
                eval_result.judge_feedback = f"Judge 评估失败: {str(e)}"
        
        return eval_result
    
    def evaluate_pipeline_output(
        self,
        pipeline_id: str,
        variant: str,
        test_case: Dict[str, Any],
        step_outputs: Dict[str, Any],
        final_output: str,
        execution_time: float = 0.0,
        evaluation_target: Optional[str] = None,
        evaluate_intermediate: bool = False,
        evaluate_aggregation: bool = False
    ) -> EvaluationResult:
        """
        评估 Pipeline 输出
        
        Args:
            pipeline_id: Pipeline ID
            variant: 变体名称
            test_case: 测试用例
            step_outputs: 所有步骤的输出
            final_output: 最终输出
            execution_time: 执行时间
            evaluation_target: 评估目标步骤ID（可选，默认使用最后一步）
            evaluate_intermediate: 是否评估中间步骤
            evaluate_aggregation: 是否评估聚合结果
            
        Returns:
            评估结果
        """
        sample_id = test_case.get("id", "unknown")
        
        # 初始化评估结果
        eval_result = EvaluationResult(
            sample_id=sample_id,
            entity_type="pipeline",
            entity_id=pipeline_id,
            variant=variant,
            overall_score=0.0,
            must_have_pass=True,
            execution_time=execution_time,
            step_outputs=step_outputs,
            failed_steps=[]
        )
        
        # 从 pipeline 配置获取评估目标步骤的 agent（用于评估）
        # 注意：这里需要导入 pipeline_config，但为了避免循环导入，
        # 我们在方法内部导入
        from .pipeline_config import load_pipeline_config
        
        try:
            pipeline_config = load_pipeline_config(pipeline_id)
            if not pipeline_config.steps:
                eval_result.judge_feedback = "Pipeline 没有步骤"
                return eval_result
            
            # 确定评估目标步骤
            target_step_id = evaluation_target or pipeline_config.evaluation_target
            if target_step_id:
                # 查找指定的步骤
                target_step = None
                for step in pipeline_config.steps:
                    if step.id == target_step_id:
                        target_step = step
                        break
                if not target_step:
                    logger.warning(f"找不到评估目标步骤: {target_step_id}，使用最后一步")
                    target_step = pipeline_config.steps[-1]
            else:
                # 使用最后一步
                target_step = pipeline_config.steps[-1]
            
            # 获取目标步骤的输出
            target_output = step_outputs.get(target_step.output_key, final_output)
            
            # 获取目标步骤的 agent 配置
            agent_config = load_agent(target_step.agent)
            
        except Exception as e:
            logger.warning(f"加载 Pipeline 或 Agent 配置失败: {e}")
            eval_result.judge_feedback = f"加载配置失败: {e}"
            return eval_result
        
        # 应用规则评估
        if self.config.rules or agent_config.evaluation.get("rules"):
            try:
                rule_result = apply_rules_to_row(
                    agent_config,
                    {"output": target_output},
                    "output"
                )
                eval_result.must_have_pass = bool(rule_result.get("rule_pass", 1))
                rule_violations = rule_result.get("rule_violations", "")
                if rule_violations:
                    eval_result.rule_violations = [
                        v.strip() for v in rule_violations.split(",") if v.strip()
                    ]
            except Exception as e:
                logger.warning(f"规则评估失败: {e}")
        
        # 评估中间步骤（如果需要）
        intermediate_results = {}
        if evaluate_intermediate:
            try:
                intermediate_results = self.evaluate_intermediate_steps(
                    pipeline_id=pipeline_id,
                    variant=variant,
                    test_case=test_case,
                    step_outputs=step_outputs
                )
                
                # 如果有中间步骤评估失败，记录到评估结果
                failed_intermediate = [
                    step_id for step_id, result in intermediate_results.items()
                    if not result['matched']
                ]
                
                if failed_intermediate:
                    eval_result.must_have_pass = False
                    failure_details = "; ".join([
                        f"{step_id}: {intermediate_results[step_id]['details']}"
                        for step_id in failed_intermediate
                    ])
                    eval_result.judge_feedback = f"中间步骤评估失败: {failure_details}"
                    logger.warning(f"中间步骤评估失败: {failure_details}")
                
            except Exception as e:
                logger.warning(f"中间步骤评估失败: {e}")
                eval_result.judge_feedback = f"中间步骤评估失败: {str(e)}"
        
        # 评估聚合结果（如果需要）
        aggregation_result = {}
        if evaluate_aggregation:
            try:
                # 查找聚合步骤的输出
                # 通常聚合步骤的输出键会包含 "aggregat" 或者是批量处理后的结果
                aggregation_output = None
                for key, value in step_outputs.items():
                    if 'aggregat' in key.lower() or 'batch' in key.lower():
                        aggregation_output = value
                        break
                
                # 如果没有找到明确的聚合输出，使用最终输出
                if aggregation_output is None:
                    aggregation_output = final_output
                
                aggregation_result = self.evaluate_aggregation_result(
                    pipeline_id=pipeline_id,
                    variant=variant,
                    test_case=test_case,
                    aggregation_output=aggregation_output
                )
                
                # 如果聚合评估失败，记录到评估结果
                if aggregation_result and not aggregation_result.get('matched', True):
                    eval_result.must_have_pass = False
                    details = aggregation_result.get('details', '未知错误')
                    if eval_result.judge_feedback:
                        eval_result.judge_feedback += f"; 聚合评估失败: {details}"
                    else:
                        eval_result.judge_feedback = f"聚合评估失败: {details}"
                    logger.warning(f"聚合评估失败: {details}")
                
            except Exception as e:
                logger.warning(f"聚合评估失败: {e}")
                if eval_result.judge_feedback:
                    eval_result.judge_feedback += f"; 聚合评估失败: {str(e)}"
                else:
                    eval_result.judge_feedback = f"聚合评估失败: {str(e)}"
        
        # 应用 LLM Judge 评估
        if self.config.judge_enabled and self.judge_agent:
            try:
                # 构建 judge chain（如果还没有构建）
                if not self.judge_chain:
                    self.judge_chain = build_judge_chain(
                        task_agent_cfg=agent_config,
                        judge_agent_cfg=self.judge_agent,
                        judge_flow_name=self.config.judge_flow
                    )
                
                # 扩展测试用例，包含中间步骤输出
                extended_case = test_case.copy()
                extended_case["step_outputs"] = step_outputs
                
                # 格式化步骤输出为可读文本
                step_outputs_text = self._format_step_outputs(step_outputs)
                extended_case["pipeline_steps"] = step_outputs_text
                
                # 添加中间步骤评估结果
                if intermediate_results:
                    extended_case["intermediate_evaluation"] = intermediate_results
                
                # 添加聚合评估结果
                if aggregation_result:
                    extended_case["aggregation_evaluation"] = aggregation_result
                
                # 调用 Judge
                judge_data, token_info = judge_one(
                    task_agent_cfg=agent_config,
                    flow_name=target_step.flow,
                    case=extended_case,
                    output=target_output,
                    judge_config=self.judge_chain,
                    judge_flow_name=self.config.judge_flow
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
                logger.warning(f"Judge 评估失败: {e}")
                eval_result.judge_feedback = f"Judge 评估失败: {str(e)}"
        
        # 将中间步骤和聚合评估结果添加到评估结果中
        if intermediate_results:
            eval_result.step_outputs['_intermediate_evaluation'] = intermediate_results
        if aggregation_result:
            eval_result.step_outputs['_aggregation_evaluation'] = aggregation_result
        
        return eval_result
    
    def evaluate_intermediate_steps(
        self,
        pipeline_id: str,
        variant: str,
        test_case: Dict[str, Any],
        step_outputs: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        评估中间步骤输出
        
        Args:
            pipeline_id: Pipeline ID
            variant: 变体名称
            test_case: 测试用例（包含 intermediate_expectations）
            step_outputs: 所有步骤的输出
            
        Returns:
            中间步骤评估结果字典 {step_id: {matched: bool, expected: Any, actual: Any, details: str}}
        """
        intermediate_expectations = test_case.get('intermediate_expectations', {})
        if not intermediate_expectations:
            return {}
        
        results = {}
        
        for step_id, expected in intermediate_expectations.items():
            actual = step_outputs.get(step_id)
            
            # 比较预期和实际输出
            matched, details = self._compare_outputs(expected, actual)
            
            results[step_id] = {
                'matched': matched,
                'expected': expected,
                'actual': actual,
                'details': details
            }
            
            logger.info(f"中间步骤 {step_id} 评估: {'通过' if matched else '失败'} - {details}")
        
        return results
    
    def evaluate_aggregation_result(
        self,
        pipeline_id: str,
        variant: str,
        test_case: Dict[str, Any],
        aggregation_output: Any
    ) -> Dict[str, Any]:
        """
        评估批量聚合结果
        
        Args:
            pipeline_id: Pipeline ID
            variant: 变体名称
            test_case: 测试用例（包含 expected_aggregation）
            aggregation_output: 实际聚合输出
            
        Returns:
            聚合评估结果 {matched: bool, expected: Any, actual: Any, details: str}
        """
        expected_aggregation = test_case.get('expected_aggregation')
        if expected_aggregation is None:
            return {}
        
        # 比较预期和实际聚合结果
        matched, details = self._compare_outputs(expected_aggregation, aggregation_output)
        
        result = {
            'matched': matched,
            'expected': expected_aggregation,
            'actual': aggregation_output,
            'details': details
        }
        
        logger.info(f"聚合结果评估: {'通过' if matched else '失败'} - {details}")
        
        return result
    
    def _compare_outputs(self, expected: Any, actual: Any) -> Tuple[bool, str]:
        """
        比较预期输出和实际输出
        
        Args:
            expected: 预期输出
            actual: 实际输出
            
        Returns:
            (是否匹配, 详细说明)
        """
        import json
        
        # 如果预期是字典，支持部分匹配和模式匹配
        if isinstance(expected, dict):
            if not isinstance(actual, dict):
                return False, f"类型不匹配: 预期字典，实际 {type(actual).__name__}"
            
            # 检查所有预期的键是否存在且值匹配
            for key, expected_value in expected.items():
                if key not in actual:
                    return False, f"缺少键: {key}"
                
                actual_value = actual[key]
                
                # 递归比较
                if isinstance(expected_value, (dict, list)):
                    matched, details = self._compare_outputs(expected_value, actual_value)
                    if not matched:
                        return False, f"键 {key} 不匹配: {details}"
                else:
                    # 支持字符串包含匹配（如果预期值以 "contains:" 开头）
                    if isinstance(expected_value, str) and expected_value.startswith("contains:"):
                        search_text = expected_value[9:].strip()
                        if search_text not in str(actual_value):
                            return False, f"键 {key} 不包含预期文本: {search_text}"
                    elif expected_value != actual_value:
                        return False, f"键 {key} 值不匹配: 预期 {expected_value}, 实际 {actual_value}"
            
            return True, "所有字段匹配"
        
        # 如果预期是列表，检查长度和元素
        elif isinstance(expected, list):
            if not isinstance(actual, list):
                return False, f"类型不匹配: 预期列表，实际 {type(actual).__name__}"
            
            if len(expected) != len(actual):
                return False, f"列表长度不匹配: 预期 {len(expected)}, 实际 {len(actual)}"
            
            for i, (exp_item, act_item) in enumerate(zip(expected, actual)):
                matched, details = self._compare_outputs(exp_item, act_item)
                if not matched:
                    return False, f"索引 {i} 不匹配: {details}"
            
            return True, "所有元素匹配"
        
        # 如果预期是字符串，支持包含匹配
        elif isinstance(expected, str):
            if expected.startswith("contains:"):
                search_text = expected[9:].strip()
                if search_text in str(actual):
                    return True, f"包含预期文本: {search_text}"
                else:
                    return False, f"不包含预期文本: {search_text}"
            elif expected.startswith("regex:"):
                import re
                pattern = expected[6:].strip()
                if re.search(pattern, str(actual)):
                    return True, f"匹配正则表达式: {pattern}"
                else:
                    return False, f"不匹配正则表达式: {pattern}"
            else:
                if expected == str(actual):
                    return True, "完全匹配"
                else:
                    return False, f"不匹配: 预期 '{expected}', 实际 '{actual}'"
        
        # 其他类型直接比较
        else:
            if expected == actual:
                return True, "完全匹配"
            else:
                return False, f"不匹配: 预期 {expected}, 实际 {actual}"
    
    def _format_step_outputs(self, step_outputs: Dict[str, Any]) -> str:
        """
        格式化步骤输出为可读文本
        
        Args:
            step_outputs: 步骤输出字典
            
        Returns:
            格式化后的文本
        """
        if not step_outputs:
            return "无中间步骤输出"
        
        lines = ["=== Pipeline 中间步骤输出 ==="]
        for key, value in step_outputs.items():
            lines.append(f"\n【{key}】")
            if isinstance(value, (dict, list)):
                import json
                lines.append(json.dumps(value, ensure_ascii=False, indent=2))
            else:
                lines.append(str(value))
        
        return "\n".join(lines)
