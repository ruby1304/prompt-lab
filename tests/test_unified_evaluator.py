# tests/test_unified_evaluator.py
"""
统一评估接口的单元测试

测试 EvaluationConfig 和 UnifiedEvaluator 的功能。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.models import (
    EvaluationConfig, EvaluationResult, RuleConfig, CaseFieldConfig,
    PipelineConfig, StepConfig, InputSpec, OutputSpec
)
from src.unified_evaluator import UnifiedEvaluator
from src.agent_registry import AgentConfig, AgentFlow


class TestEvaluationConfig:
    """测试 EvaluationConfig 类"""
    
    def test_from_agent_config_basic(self):
        """测试从 Agent 配置创建评估配置（基本情况）"""
        # 创建一个简单的 agent 配置
        agent_config = AgentConfig(
            id="test_agent",
            name="Test Agent",
            description="Test description",
            business_goal="Test goal",
            expectations={},
            default_testset="test.jsonl",
            extra_testsets=[],
            flows=[],
            evaluation={
                "judge_agent_id": "judge_default",
                "judge_flow": "judge_v1",
                "scale": {"min": 0, "max": 10},
                "temperature": 0.0
            }
        )
        
        # 从 agent 配置创建评估配置
        eval_config = EvaluationConfig.from_agent_config(agent_config)
        
        # 验证基本字段
        assert eval_config.judge_enabled is True
        assert eval_config.judge_agent_id == "judge_default"
        assert eval_config.judge_flow == "judge_v1"
        assert eval_config.scale_min == 0
        assert eval_config.scale_max == 10
        assert eval_config.temperature == 0.0
    
    def test_from_agent_config_with_rules(self):
        """测试从 Agent 配置创建评估配置（包含规则）"""
        agent_config = AgentConfig(
            id="test_agent",
            name="Test Agent",
            description="Test description",
            business_goal="Test goal",
            expectations={},
            default_testset="test.jsonl",
            extra_testsets=[],
            flows=[],
            evaluation={
                "rules": [
                    {
                        "name": "length_check",
                        "type": "length",
                        "params": {"min": 10, "max": 100},
                        "severity": "error",
                        "message": "Output length must be between 10 and 100"
                    }
                ]
            }
        )
        
        eval_config = EvaluationConfig.from_agent_config(agent_config)
        
        # 验证规则配置
        assert len(eval_config.rules) == 1
        assert eval_config.rules[0].name == "length_check"
        assert eval_config.rules[0].type == "length"
        assert eval_config.rules[0].params == {"min": 10, "max": 100}
    
    def test_from_agent_config_with_case_fields(self):
        """测试从 Agent 配置创建评估配置（包含字段配置）"""
        agent_config = AgentConfig(
            id="test_agent",
            name="Test Agent",
            description="Test description",
            business_goal="Test goal",
            expectations={},
            default_testset="test.jsonl",
            extra_testsets=[],
            flows=[],
            evaluation={
                "case_fields": [
                    {
                        "key": "input",
                        "label": "输入",
                        "section": "primary_input",
                        "required": True
                    },
                    {
                        "key": "context",
                        "label": "上下文",
                        "section": "context",
                        "truncate": 500
                    }
                ]
            }
        )
        
        eval_config = EvaluationConfig.from_agent_config(agent_config)
        
        # 验证字段配置
        assert len(eval_config.case_fields) == 2
        assert eval_config.case_fields[0].key == "input"
        assert eval_config.case_fields[0].section == "primary_input"
        assert eval_config.case_fields[0].required is True
        assert eval_config.case_fields[1].key == "context"
        assert eval_config.case_fields[1].truncate == 500
    
    def test_from_agent_config_no_judge(self):
        """测试从 Agent 配置创建评估配置（不启用 Judge）"""
        agent_config = AgentConfig(
            id="test_agent",
            name="Test Agent",
            description="Test description",
            business_goal="Test goal",
            expectations={},
            default_testset="test.jsonl",
            extra_testsets=[],
            flows=[],
            evaluation={}
        )
        
        eval_config = EvaluationConfig.from_agent_config(agent_config)
        
        # 验证 Judge 未启用
        assert eval_config.judge_enabled is False
        assert eval_config.judge_agent_id is None
        assert eval_config.judge_flow is None
    
    @patch('src.agent_registry.load_agent')
    def test_from_pipeline_config(self, mock_load_agent):
        """测试从 Pipeline 配置创建评估配置"""
        # 创建一个模拟的 agent 配置
        mock_agent = AgentConfig(
            id="final_agent",
            name="Final Agent",
            description="Final agent description",
            business_goal="Final goal",
            expectations={},
            default_testset="test.jsonl",
            extra_testsets=[],
            flows=[],
            evaluation={
                "judge_agent_id": "judge_default",
                "judge_flow": "judge_v1",
                "scale": {"min": 0, "max": 10}
            }
        )
        mock_load_agent.return_value = mock_agent
        
        # 创建一个 pipeline 配置
        pipeline_config = PipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            description="Test pipeline",
            inputs=[InputSpec(name="input")],
            steps=[
                StepConfig(
                    id="step1",
                    agent="agent1",
                    flow="flow1",
                    input_mapping={"text": "input"},
                    output_key="output1"
                ),
                StepConfig(
                    id="step2",
                    agent="final_agent",
                    flow="flow2",
                    input_mapping={"text": "output1"},
                    output_key="output2"
                )
            ],
            outputs=[OutputSpec(key="output2")]
        )
        
        # 从 pipeline 配置创建评估配置
        eval_config = EvaluationConfig.from_pipeline_config(pipeline_config)
        
        # 验证使用了最后一个步骤的 agent 配置
        assert eval_config.judge_enabled is True
        assert eval_config.judge_agent_id == "judge_default"
        assert eval_config.judge_flow == "judge_v1"
        mock_load_agent.assert_called_once_with("final_agent")
    
    def test_from_pipeline_config_no_steps(self):
        """测试从 Pipeline 配置创建评估配置（没有步骤）"""
        pipeline_config = PipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            description="Test pipeline",
            inputs=[],
            steps=[],
            outputs=[]
        )
        
        # 从 pipeline 配置创建评估配置
        eval_config = EvaluationConfig.from_pipeline_config(pipeline_config)
        
        # 验证返回默认配置
        assert eval_config.judge_enabled is False
        assert eval_config.scale_min == 0
        assert eval_config.scale_max == 10


class TestUnifiedEvaluator:
    """测试 UnifiedEvaluator 类"""
    
    @patch('src.unified_evaluator.load_agent')
    def test_init_with_judge_enabled(self, mock_load_agent):
        """测试初始化统一评估器（启用 Judge）"""
        # 创建一个模拟的 judge agent
        mock_judge = AgentConfig(
            id="judge_default",
            name="Judge Agent",
            description="Judge description",
            business_goal="Judge goal",
            expectations={},
            default_testset="test.jsonl",
            extra_testsets=[],
            flows=[],
            evaluation={}
        )
        mock_load_agent.return_value = mock_judge
        
        # 创建评估配置
        eval_config = EvaluationConfig(
            judge_enabled=True,
            judge_agent_id="judge_default",
            judge_flow="judge_v1"
        )
        
        # 初始化评估器
        evaluator = UnifiedEvaluator(eval_config)
        
        # 验证 judge agent 被加载
        assert evaluator.judge_agent is not None
        mock_load_agent.assert_called_once_with("judge_default")
    
    def test_init_without_judge(self):
        """测试初始化统一评估器（不启用 Judge）"""
        eval_config = EvaluationConfig(
            judge_enabled=False
        )
        
        evaluator = UnifiedEvaluator(eval_config)
        
        # 验证 judge agent 未加载
        assert evaluator.judge_agent is None
        assert evaluator.judge_chain is None
    
    @patch('src.unified_evaluator.load_agent')
    @patch('src.unified_evaluator.apply_rules_to_row')
    def test_evaluate_agent_output_with_rules(self, mock_apply_rules, mock_load_agent):
        """测试评估 Agent 输出（使用规则）"""
        # 创建模拟的 agent 配置
        mock_agent = AgentConfig(
            id="test_agent",
            name="Test Agent",
            description="Test description",
            business_goal="Test goal",
            expectations={},
            default_testset="test.jsonl",
            extra_testsets=[],
            flows=[],
            evaluation={
                "rules": [{"name": "test_rule", "type": "contains", "params": {}}]
            }
        )
        mock_load_agent.return_value = mock_agent
        
        # 模拟规则评估结果
        mock_apply_rules.return_value = {
            "rule_pass": 1,
            "rule_violations": ""
        }
        
        # 创建评估配置
        eval_config = EvaluationConfig(
            rules=[RuleConfig(name="test_rule", type="contains")],
            judge_enabled=False
        )
        
        # 初始化评估器
        evaluator = UnifiedEvaluator(eval_config)
        
        # 评估输出
        result = evaluator.evaluate_agent_output(
            agent_id="test_agent",
            flow_name="test_flow",
            test_case={"id": "test_1", "input": "test input"},
            output="test output"
        )
        
        # 验证结果
        assert result.sample_id == "test_1"
        assert result.entity_type == "agent"
        assert result.entity_id == "test_agent"
        assert result.variant == "test_flow"
        assert result.must_have_pass is True
        assert len(result.rule_violations) == 0
        
        # 验证规则评估被调用
        mock_apply_rules.assert_called_once()
    
    @patch('src.unified_evaluator.load_agent')
    @patch('src.unified_evaluator.apply_rules_to_row')
    def test_evaluate_agent_output_with_rule_violations(self, mock_apply_rules, mock_load_agent):
        """测试评估 Agent 输出（有规则违规）"""
        mock_agent = AgentConfig(
            id="test_agent",
            name="Test Agent",
            description="Test description",
            business_goal="Test goal",
            expectations={},
            default_testset="test.jsonl",
            extra_testsets=[],
            flows=[],
            evaluation={"rules": []}
        )
        mock_load_agent.return_value = mock_agent
        
        # 模拟规则评估结果（有违规）
        mock_apply_rules.return_value = {
            "rule_pass": 0,
            "rule_violations": "rule1, rule2"
        }
        
        eval_config = EvaluationConfig(
            rules=[RuleConfig(name="test_rule", type="contains")],
            judge_enabled=False
        )
        
        evaluator = UnifiedEvaluator(eval_config)
        
        result = evaluator.evaluate_agent_output(
            agent_id="test_agent",
            flow_name="test_flow",
            test_case={"id": "test_1"},
            output="test output"
        )
        
        # 验证规则违规被记录
        assert result.must_have_pass is False
        assert len(result.rule_violations) == 2
        assert "rule1" in result.rule_violations
        assert "rule2" in result.rule_violations
    
    @patch('src.agent_registry.load_agent')
    @patch('src.pipeline_config.load_pipeline_config')
    @patch('src.unified_evaluator.apply_rules_to_row')
    def test_evaluate_pipeline_output(self, mock_apply_rules, mock_load_pipeline, mock_load_agent):
        """测试评估 Pipeline 输出"""
        # 创建模拟的 agent 配置
        mock_agent = AgentConfig(
            id="final_agent",
            name="Final Agent",
            description="Final description",
            business_goal="Final goal",
            expectations={},
            default_testset="test.jsonl",
            extra_testsets=[],
            flows=[],
            evaluation={"rules": []}
        )
        mock_load_agent.return_value = mock_agent
        
        # 创建模拟的 pipeline 配置
        mock_pipeline = PipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            description="Test pipeline",
            inputs=[InputSpec(name="input")],
            steps=[
                StepConfig(
                    id="step1",
                    agent="final_agent",
                    flow="flow1",
                    input_mapping={"text": "input"},
                    output_key="output1"
                )
            ],
            outputs=[OutputSpec(key="output1")]
        )
        mock_load_pipeline.return_value = mock_pipeline
        
        # 模拟规则评估结果
        mock_apply_rules.return_value = {
            "rule_pass": 1,
            "rule_violations": ""
        }
        
        # 创建评估配置
        eval_config = EvaluationConfig(
            rules=[RuleConfig(name="test_rule", type="contains")],
            judge_enabled=False
        )
        
        # 初始化评估器
        evaluator = UnifiedEvaluator(eval_config)
        
        # 评估 pipeline 输出
        result = evaluator.evaluate_pipeline_output(
            pipeline_id="test_pipeline",
            variant="baseline",
            test_case={"id": "test_1", "input": "test input"},
            step_outputs={"output1": "step 1 output"},
            final_output="final output"
        )
        
        # 验证结果
        assert result.sample_id == "test_1"
        assert result.entity_type == "pipeline"
        assert result.entity_id == "test_pipeline"
        assert result.variant == "baseline"
        assert result.must_have_pass is True
        assert result.step_outputs == {"output1": "step 1 output"}
    
    @patch('src.pipeline_config.load_pipeline_config')
    def test_evaluate_pipeline_output_no_steps(self, mock_load_pipeline):
        """测试评估 Pipeline 输出（没有步骤）"""
        # 创建模拟的 pipeline 配置（没有步骤）
        mock_pipeline = PipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            description="Test pipeline",
            inputs=[],
            steps=[],
            outputs=[]
        )
        mock_load_pipeline.return_value = mock_pipeline
        
        eval_config = EvaluationConfig(judge_enabled=False)
        evaluator = UnifiedEvaluator(eval_config)
        
        result = evaluator.evaluate_pipeline_output(
            pipeline_id="test_pipeline",
            variant="baseline",
            test_case={"id": "test_1"},
            step_outputs={},
            final_output=""
        )
        
        # 验证返回错误结果
        assert result.sample_id == "test_1"
        assert result.entity_type == "pipeline"
        assert "没有步骤" in result.judge_feedback


class TestEvaluationResultFormat:
    """测试评估结果格式一致性"""
    
    def test_agent_result_format(self):
        """测试 Agent 评估结果格式"""
        result = EvaluationResult(
            sample_id="test_1",
            entity_type="agent",
            entity_id="test_agent",
            variant="test_flow",
            overall_score=8.5,
            must_have_pass=True,
            rule_violations=[],
            judge_feedback="Good output"
        )
        
        # 转换为字典
        result_dict = result.to_dict()
        
        # 验证字段存在
        assert "sample_id" in result_dict
        assert "entity_type" in result_dict
        assert "entity_id" in result_dict
        assert "variant" in result_dict
        assert "overall_score" in result_dict
        assert "must_have_pass" in result_dict
        assert "step_outputs" in result_dict
        
        # 验证值
        assert result_dict["entity_type"] == "agent"
        assert result_dict["entity_id"] == "test_agent"
    
    def test_pipeline_result_format(self):
        """测试 Pipeline 评估结果格式"""
        result = EvaluationResult(
            sample_id="test_1",
            entity_type="pipeline",
            entity_id="test_pipeline",
            variant="baseline",
            overall_score=7.5,
            must_have_pass=True,
            step_outputs={"step1": "output1", "step2": "output2"}
        )
        
        # 转换为字典
        result_dict = result.to_dict()
        
        # 验证字段存在
        assert "entity_type" in result_dict
        assert "entity_id" in result_dict
        assert "step_outputs" in result_dict
        
        # 验证值
        assert result_dict["entity_type"] == "pipeline"
        assert result_dict["entity_id"] == "test_pipeline"
        assert len(result_dict["step_outputs"]) == 2
    
    def test_result_format_consistency(self):
        """测试 Agent 和 Pipeline 结果格式一致性"""
        agent_result = EvaluationResult(
            sample_id="test_1",
            entity_type="agent",
            entity_id="test_agent",
            variant="test_flow",
            overall_score=8.0,
            must_have_pass=True
        )
        
        pipeline_result = EvaluationResult(
            sample_id="test_1",
            entity_type="pipeline",
            entity_id="test_pipeline",
            variant="baseline",
            overall_score=8.0,
            must_have_pass=True
        )
        
        # 转换为字典
        agent_dict = agent_result.to_dict()
        pipeline_dict = pipeline_result.to_dict()
        
        # 验证两者有相同的字段集合
        assert set(agent_dict.keys()) == set(pipeline_dict.keys())
    
    def test_result_from_dict_backward_compatibility(self):
        """测试从字典创建结果（向后兼容）"""
        # 旧格式的字典（没有 entity_type 和 entity_id）
        old_dict = {
            "sample_id": "test_1",
            "variant": "test_flow",
            "overall_score": 8.0,
            "must_have_pass": True,
            "rule_violations": [],
            "judge_feedback": "Good",
            "execution_time": 1.5,
            "step_outputs": {}
        }
        
        # 从字典创建结果
        result = EvaluationResult.from_dict(old_dict)
        
        # 验证默认值
        assert result.entity_type == "agent"  # 默认为 agent
        assert result.entity_id == ""
        assert result.sample_id == "test_1"
        assert result.overall_score == 8.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
