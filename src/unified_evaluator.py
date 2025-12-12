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
        evaluation_target: Optional[str] = None
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
        
        return eval_result
    
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
