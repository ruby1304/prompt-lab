# tests/test_pipeline_evaluation.py
"""
Pipeline 评估功能单元测试

测试 Pipeline 步骤输出收集、评估目标步骤、中间输出传递给 Judge、步骤失败处理等功能。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.models import (
    PipelineConfig, StepConfig, InputSpec, OutputSpec, 
    EvaluationResult, EvaluationConfig
)
from src.pipeline_runner import PipelineRunner, PipelineResult, StepResult
from src.unified_evaluator import UnifiedEvaluator


class TestStepOutputCollection:
    """测试步骤输出收集功能"""
    
    def test_step_result_has_success_flag(self):
        """测试 StepResult 包含 success 标志"""
        step_result = StepResult(
            step_id="test_step",
            output_key="test_output",
            output_value="test value",
            execution_time=1.0,
            success=True
        )
        
        assert step_result.success is True
        assert step_result.error is None
    
    def test_step_result_failure_flag(self):
        """测试 StepResult 失败标志"""
        step_result = StepResult(
            step_id="test_step",
            output_key="test_output",
            output_value="",
            execution_time=1.0,
            success=False,
            error="Test error"
        )
        
        assert step_result.success is False
        assert step_result.error == "Test error"
    
    def test_pipeline_result_get_step_outputs_dict(self):
        """测试 PipelineResult.get_step_outputs_dict() 方法"""
        step_results = [
            StepResult(
                step_id="step1",
                output_key="output1",
                output_value="value1",
                execution_time=1.0,
                success=True
            ),
            StepResult(
                step_id="step2",
                output_key="output2",
                output_value="value2",
                execution_time=1.0,
                success=True
            ),
            StepResult(
                step_id="step3",
                output_key="output3",
                output_value="",
                execution_time=1.0,
                success=False,
                error="Failed"
            )
        ]
        
        pipeline_result = PipelineResult(
            sample_id="test_sample",
            variant="baseline",
            step_results=step_results
        )
        
        outputs_dict = pipeline_result.get_step_outputs_dict()
        
        # 只包含成功的步骤输出
        assert len(outputs_dict) == 2
        assert outputs_dict["output1"] == "value1"
        assert outputs_dict["output2"] == "value2"
        assert "output3" not in outputs_dict
    
    def test_pipeline_result_get_failed_steps(self):
        """测试 PipelineResult.get_failed_steps() 方法"""
        step_results = [
            StepResult(
                step_id="step1",
                output_key="output1",
                output_value="value1",
                execution_time=1.0,
                success=True
            ),
            StepResult(
                step_id="step2",
                output_key="output2",
                output_value="",
                execution_time=1.0,
                success=False,
                error="Error 1"
            ),
            StepResult(
                step_id="step3",
                output_key="output3",
                output_value="",
                execution_time=1.0,
                success=False,
                error="Error 2"
            )
        ]
        
        pipeline_result = PipelineResult(
            sample_id="test_sample",
            variant="baseline",
            step_results=step_results
        )
        
        failed_steps = pipeline_result.get_failed_steps()
        
        assert len(failed_steps) == 2
        assert failed_steps[0].step_id == "step2"
        assert failed_steps[1].step_id == "step3"
    
    def test_step_result_to_dict_includes_success(self):
        """测试 StepResult.to_dict() 包含 success 字段"""
        step_result = StepResult(
            step_id="test_step",
            output_key="test_output",
            output_value="test value",
            execution_time=1.0,
            success=True
        )
        
        result_dict = step_result.to_dict()
        
        assert "success" in result_dict
        assert result_dict["success"] is True


class TestEvaluationTargetStep:
    """测试指定评估目标步骤功能"""
    
    def test_pipeline_config_has_evaluation_target(self):
        """测试 PipelineConfig 包含 evaluation_target 字段"""
        config = PipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            steps=[
                StepConfig(
                    id="step1",
                    agent="agent1",
                    flow="flow1",
                    output_key="output1"
                ),
                StepConfig(
                    id="step2",
                    agent="agent2",
                    flow="flow2",
                    output_key="output2"
                )
            ],
            outputs=[OutputSpec(key="output2")],
            evaluation_target="step1"
        )
        
        assert config.evaluation_target == "step1"
    
    def test_pipeline_config_validation_invalid_evaluation_target(self):
        """测试 PipelineConfig 验证无效的 evaluation_target"""
        config = PipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            steps=[
                StepConfig(
                    id="step1",
                    agent="agent1",
                    flow="flow1",
                    output_key="output1"
                )
            ],
            outputs=[OutputSpec(key="output1")],
            evaluation_target="nonexistent_step"
        )
        
        errors = config.validate()
        
        assert any("evaluation_target" in error for error in errors)
    
    def test_pipeline_result_get_evaluation_target_output_default(self):
        """测试获取评估目标输出（默认最后一步）"""
        step_results = [
            StepResult(
                step_id="step1",
                output_key="output1",
                output_value="value1",
                execution_time=1.0,
                success=True
            ),
            StepResult(
                step_id="step2",
                output_key="output2",
                output_value="value2",
                execution_time=1.0,
                success=True
            )
        ]
        
        pipeline_result = PipelineResult(
            sample_id="test_sample",
            variant="baseline",
            step_results=step_results
        )
        
        step_id, output = pipeline_result.get_evaluation_target_output()
        
        assert step_id == "step2"
        assert output == "value2"
    
    def test_pipeline_result_get_evaluation_target_output_specified(self):
        """测试获取评估目标输出（指定步骤）"""
        step_results = [
            StepResult(
                step_id="step1",
                output_key="output1",
                output_value="value1",
                execution_time=1.0,
                success=True
            ),
            StepResult(
                step_id="step2",
                output_key="output2",
                output_value="value2",
                execution_time=1.0,
                success=True
            )
        ]
        
        pipeline_result = PipelineResult(
            sample_id="test_sample",
            variant="baseline",
            step_results=step_results
        )
        
        step_id, output = pipeline_result.get_evaluation_target_output("step1")
        
        assert step_id == "step1"
        assert output == "value1"
    
    def test_pipeline_result_get_evaluation_target_output_failed_step(self):
        """测试获取评估目标输出（步骤失败）"""
        step_results = [
            StepResult(
                step_id="step1",
                output_key="output1",
                output_value="",
                execution_time=1.0,
                success=False,
                error="Failed"
            )
        ]
        
        pipeline_result = PipelineResult(
            sample_id="test_sample",
            variant="baseline",
            step_results=step_results
        )
        
        step_id, output = pipeline_result.get_evaluation_target_output("step1")
        
        assert step_id == "step1"
        assert output == ""


class TestIntermediateOutputsToJudge:
    """测试中间步骤输出传递给 Judge 功能"""
    
    def test_unified_evaluator_formats_step_outputs(self):
        """测试 UnifiedEvaluator 格式化步骤输出"""
        eval_config = EvaluationConfig(
            judge_enabled=False
        )
        evaluator = UnifiedEvaluator(eval_config)
        
        step_outputs = {
            "output1": "value1",
            "output2": {"key": "value"},
            "output3": ["item1", "item2"]
        }
        
        formatted = evaluator._format_step_outputs(step_outputs)
        
        assert "=== Pipeline 中间步骤输出 ===" in formatted
        assert "【output1】" in formatted
        assert "value1" in formatted
        assert "【output2】" in formatted
        assert "【output3】" in formatted
    
    def test_unified_evaluator_formats_empty_step_outputs(self):
        """测试 UnifiedEvaluator 格式化空步骤输出"""
        eval_config = EvaluationConfig(
            judge_enabled=False
        )
        evaluator = UnifiedEvaluator(eval_config)
        
        formatted = evaluator._format_step_outputs({})
        
        assert formatted == "无中间步骤输出"
    
    @patch('src.pipeline_config.load_pipeline_config')
    @patch('src.unified_evaluator.load_agent')
    @patch('src.unified_evaluator.judge_one')
    @patch('src.unified_evaluator.build_judge_chain')
    def test_evaluate_pipeline_output_passes_step_outputs_to_judge(
        self, mock_build_chain, mock_judge_one, mock_load_agent, mock_load_pipeline
    ):
        """测试评估 Pipeline 输出时将步骤输出传递给 Judge"""
        # Mock pipeline config
        mock_pipeline = Mock()
        mock_pipeline.steps = [
            Mock(id="step1", agent="agent1", flow="flow1", output_key="output1"),
            Mock(id="step2", agent="agent2", flow="flow2", output_key="output2")
        ]
        mock_pipeline.evaluation_target = None
        mock_load_pipeline.return_value = mock_pipeline
        
        # Mock agent config
        mock_agent = Mock()
        mock_agent.evaluation = {}
        mock_load_agent.return_value = mock_agent
        
        # Mock judge
        mock_build_chain.return_value = {"flow_cfg": {}, "model_name": "test"}
        mock_judge_one.return_value = (
            {
                "overall_score": 8.0,
                "must_have_check": [],
                "overall_comment": "Good"
            },
            {"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
        )
        
        # Create evaluator
        eval_config = EvaluationConfig(
            judge_enabled=True,
            judge_agent_id="judge_default",
            judge_flow="judge_v1"
        )
        evaluator = UnifiedEvaluator(eval_config)
        evaluator.judge_agent = mock_agent
        
        # Evaluate
        step_outputs = {"output1": "value1", "output2": "value2"}
        result = evaluator.evaluate_pipeline_output(
            pipeline_id="test_pipeline",
            variant="baseline",
            test_case={"id": "test"},
            step_outputs=step_outputs,
            final_output="final value"
        )
        
        # Verify judge was called with extended case including step_outputs
        assert mock_judge_one.called
        call_args = mock_judge_one.call_args
        extended_case = call_args[1]["case"]
        
        assert "step_outputs" in extended_case
        assert extended_case["step_outputs"] == step_outputs
        assert "pipeline_steps" in extended_case


class TestStepFailureHandling:
    """测试步骤失败处理功能"""
    
    def test_step_config_has_required_field(self):
        """测试 StepConfig 包含 required 字段"""
        step = StepConfig(
            id="test_step",
            agent="test_agent",
            flow="test_flow",
            output_key="test_output",
            required=False
        )
        
        assert step.required is False
    
    def test_step_config_get_dependencies(self):
        """测试 StepConfig.get_dependencies() 方法"""
        step = StepConfig(
            id="test_step",
            agent="test_agent",
            flow="test_flow",
            input_mapping={
                "param1": "output1",
                "param2": "output2"
            },
            output_key="test_output"
        )
        
        dependencies = step.get_dependencies()
        
        assert len(dependencies) == 2
        assert "output1" in dependencies
        assert "output2" in dependencies
    
    def test_evaluation_result_has_failed_steps_field(self):
        """测试 EvaluationResult 包含 failed_steps 字段"""
        result = EvaluationResult(
            sample_id="test",
            entity_type="pipeline",
            entity_id="test_pipeline",
            variant="baseline",
            overall_score=5.0,
            must_have_pass=True,
            failed_steps=["step2", "step3"]
        )
        
        assert len(result.failed_steps) == 2
        assert "step2" in result.failed_steps
        assert "step3" in result.failed_steps
    
    def test_evaluation_result_to_dict_includes_failed_steps(self):
        """测试 EvaluationResult.to_dict() 包含 failed_steps"""
        result = EvaluationResult(
            sample_id="test",
            entity_type="pipeline",
            entity_id="test_pipeline",
            variant="baseline",
            overall_score=5.0,
            must_have_pass=True,
            failed_steps=["step2"]
        )
        
        result_dict = result.to_dict()
        
        assert "failed_steps" in result_dict
        assert result_dict["failed_steps"] == ["step2"]
    
    def test_evaluation_result_from_dict_includes_failed_steps(self):
        """测试 EvaluationResult.from_dict() 包含 failed_steps"""
        data = {
            "sample_id": "test",
            "entity_type": "pipeline",
            "entity_id": "test_pipeline",
            "variant": "baseline",
            "overall_score": 5.0,
            "must_have_pass": True,
            "failed_steps": ["step2", "step3"]
        }
        
        result = EvaluationResult.from_dict(data)
        
        assert len(result.failed_steps) == 2
        assert "step2" in result.failed_steps
        assert "step3" in result.failed_steps
    
    @patch('src.pipeline_runner.run_flow_with_tokens')
    @patch('src.pipeline_runner.load_agent')
    def test_pipeline_runner_skips_dependent_steps_on_failure(
        self, mock_load_agent, mock_run_flow
    ):
        """测试 Pipeline 执行器在步骤失败时跳过依赖步骤"""
        # Mock agent with properly named flows
        def create_mock_agent(agent_id):
            mock_agent = Mock()
            flow1 = Mock()
            flow1.name = "flow1"
            flow2 = Mock()
            flow2.name = "flow2"
            flow3 = Mock()
            flow3.name = "flow3"
            mock_agent.flows = [flow1, flow2, flow3]
            return mock_agent
        
        mock_load_agent.side_effect = create_mock_agent
        
        # Mock flow execution - step1 succeeds, step2 fails
        def mock_run_side_effect(*args, **kwargs):
            flow_name = kwargs.get("flow_name", "")
            if flow_name == "flow1":
                return "output1", {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20}, None
            elif flow_name == "flow2":
                raise Exception("Step 2 failed")
            else:
                return "output3", {"input_tokens": 10, "output_tokens": 10, "total_tokens": 20}, None
        
        mock_run_flow.side_effect = mock_run_side_effect
        
        # Create pipeline config
        config = PipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            steps=[
                StepConfig(
                    id="step1",
                    agent="agent1",
                    flow="flow1",
                    input_mapping={},
                    output_key="output1",
                    required=False
                ),
                StepConfig(
                    id="step2",
                    agent="agent2",
                    flow="flow2",
                    input_mapping={},
                    output_key="output2",
                    required=False
                ),
                StepConfig(
                    id="step3",
                    agent="agent3",
                    flow="flow3",
                    input_mapping={"input": "output2"},  # Depends on step2
                    output_key="output3"
                )
            ],
            outputs=[OutputSpec(key="output3")]
        )
        
        runner = PipelineRunner(config)
        
        # Execute sample
        sample = {"id": "test_sample"}
        result = runner.execute_sample(sample, "baseline")
        
        # Verify results
        assert len(result.step_results) == 3
        
        # Step 1 should succeed
        assert result.step_results[0].success is True
        assert result.step_results[0].output_value == "output1"
        
        # Step 2 should fail
        assert result.step_results[1].success is False
        assert "failed" in result.step_results[1].error.lower()
        
        # Step 3 should be skipped due to dependency on step2
        assert result.step_results[2].success is False
        assert "依赖" in result.step_results[2].error or "跳过" in result.step_results[2].error


class TestPipelineEvaluationIntegration:
    """测试 Pipeline 评估集成功能"""
    
    @patch('src.pipeline_config.load_pipeline_config')
    @patch('src.unified_evaluator.load_agent')
    def test_evaluate_pipeline_with_evaluation_target(
        self, mock_load_agent, mock_load_pipeline
    ):
        """测试使用指定评估目标评估 Pipeline"""
        # Mock pipeline config
        mock_pipeline = Mock()
        mock_pipeline.steps = [
            Mock(id="step1", agent="agent1", flow="flow1", output_key="output1"),
            Mock(id="step2", agent="agent2", flow="flow2", output_key="output2")
        ]
        mock_pipeline.evaluation_target = "step1"
        mock_load_pipeline.return_value = mock_pipeline
        
        # Mock agent config
        mock_agent = Mock()
        mock_agent.evaluation = {}
        mock_load_agent.return_value = mock_agent
        
        # Create evaluator
        eval_config = EvaluationConfig(
            judge_enabled=False
        )
        evaluator = UnifiedEvaluator(eval_config)
        
        # Evaluate
        step_outputs = {"output1": "value1", "output2": "value2"}
        result = evaluator.evaluate_pipeline_output(
            pipeline_id="test_pipeline",
            variant="baseline",
            test_case={"id": "test"},
            step_outputs=step_outputs,
            final_output="value2"
        )
        
        # Verify result
        assert result.entity_type == "pipeline"
        assert result.entity_id == "test_pipeline"
        assert result.step_outputs == step_outputs
    
    @patch('src.pipeline_config.load_pipeline_config')
    @patch('src.unified_evaluator.load_agent')
    def test_evaluate_pipeline_with_failed_steps(
        self, mock_load_agent, mock_load_pipeline
    ):
        """测试评估包含失败步骤的 Pipeline"""
        # Mock pipeline config
        mock_pipeline = Mock()
        mock_pipeline.steps = [
            Mock(id="step1", agent="agent1", flow="flow1", output_key="output1")
        ]
        mock_pipeline.evaluation_target = None
        mock_load_pipeline.return_value = mock_pipeline
        
        # Mock agent config
        mock_agent = Mock()
        mock_agent.evaluation = {}
        mock_load_agent.return_value = mock_agent
        
        # Create evaluator
        eval_config = EvaluationConfig(
            judge_enabled=False
        )
        evaluator = UnifiedEvaluator(eval_config)
        
        # Evaluate with empty step outputs (simulating failure)
        result = evaluator.evaluate_pipeline_output(
            pipeline_id="test_pipeline",
            variant="baseline",
            test_case={"id": "test"},
            step_outputs={},
            final_output=""
        )
        
        # Verify result
        assert result.entity_type == "pipeline"
        assert result.step_outputs == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
