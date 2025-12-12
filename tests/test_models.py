# tests/test_models.py
"""
数据模型单元测试
"""

import pytest
from datetime import datetime
from typing import Dict, Any

from src.models import (
    PipelineConfig, StepConfig, BaselineConfig, VariantConfig, 
    VariantStepOverride, BaselineStepConfig, InputSpec, OutputSpec,
    EvaluationResult, ComparisonReport, RegressionCase
)


class TestInputSpec:
    """测试 InputSpec 类"""
    
    def test_input_spec_creation(self):
        """测试 InputSpec 创建"""
        spec = InputSpec(name="input_text", desc="输入文本描述")
        
        assert spec.name == "input_text"
        assert spec.desc == "输入文本描述"
    
    def test_input_spec_from_dict(self):
        """测试从字典创建 InputSpec"""
        data = {"name": "input_text", "desc": "输入文本描述"}
        spec = InputSpec.from_dict(data)
        
        assert spec.name == "input_text"
        assert spec.desc == "输入文本描述"
    
    def test_input_spec_from_string(self):
        """测试从字符串创建 InputSpec"""
        spec = InputSpec.from_dict("input_text")
        
        assert spec.name == "input_text"
        assert spec.desc == ""
    
    def test_input_spec_to_dict(self):
        """测试 InputSpec 转换为字典"""
        spec = InputSpec(name="input_text", desc="输入文本描述")
        result = spec.to_dict()
        
        assert result == {"name": "input_text", "desc": "输入文本描述", "required": True}


class TestOutputSpec:
    """测试 OutputSpec 类"""
    
    def test_output_spec_creation(self):
        """测试 OutputSpec 创建"""
        spec = OutputSpec(key="output_key", label="输出标签")
        
        assert spec.key == "output_key"
        assert spec.label == "输出标签"
    
    def test_output_spec_from_dict(self):
        """测试从字典创建 OutputSpec"""
        data = {"key": "output_key", "label": "输出标签"}
        spec = OutputSpec.from_dict(data)
        
        assert spec.key == "output_key"
        assert spec.label == "输出标签"
    
    def test_output_spec_from_string(self):
        """测试从字符串创建 OutputSpec"""
        spec = OutputSpec.from_dict("output_key")
        
        assert spec.key == "output_key"
        assert spec.label == ""
    
    def test_output_spec_to_dict(self):
        """测试 OutputSpec 转换为字典"""
        spec = OutputSpec(key="output_key", label="输出标签")
        result = spec.to_dict()
        
        assert result == {"key": "output_key", "label": "输出标签"}


class TestStepConfig:
    """测试 StepConfig 类"""
    
    def test_step_config_creation(self):
        """测试 StepConfig 创建"""
        step = StepConfig(
            id="step1",
            type="agent_flow",
            agent="test_agent",
            flow="test_flow",
            input_mapping={"param": "value"},
            output_key="step1_output",
            model_override="gpt-4"
        )
        
        assert step.id == "step1"
        assert step.type == "agent_flow"
        assert step.agent == "test_agent"
        assert step.flow == "test_flow"
        assert step.input_mapping == {"param": "value"}
        assert step.output_key == "step1_output"
        assert step.model_override == "gpt-4"
    
    def test_step_config_from_dict(self):
        """测试从字典创建 StepConfig"""
        data = {
            "id": "step1",
            "type": "agent_flow",
            "agent": "test_agent",
            "flow": "test_flow",
            "input_mapping": {"param": "value"},
            "output_key": "step1_output",
            "model_override": "gpt-4"
        }
        
        step = StepConfig.from_dict(data)
        
        assert step.id == "step1"
        assert step.type == "agent_flow"
        assert step.agent == "test_agent"
        assert step.flow == "test_flow"
        assert step.input_mapping == {"param": "value"}
        assert step.output_key == "step1_output"
        assert step.model_override == "gpt-4"
    
    def test_step_config_from_dict_minimal(self):
        """测试从最小字典创建 StepConfig"""
        data = {
            "id": "step1",
            "agent": "test_agent",
            "flow": "test_flow",
            "output_key": "step1_output"
        }
        
        step = StepConfig.from_dict(data)
        
        assert step.id == "step1"
        assert step.type == "agent_flow"  # 默认值
        assert step.agent == "test_agent"
        assert step.flow == "test_flow"
        assert step.input_mapping == {}  # 默认值
        assert step.output_key == "step1_output"
        assert step.model_override is None  # 默认值
    
    def test_step_config_to_dict(self):
        """测试 StepConfig 转换为字典"""
        step = StepConfig(
            id="step1",
            type="agent_flow",
            agent="test_agent",
            flow="test_flow",
            input_mapping={"param": "value"},
            output_key="step1_output",
            model_override="gpt-4"
        )
        
        result = step.to_dict()
        
        expected = {
            "id": "step1",
            "type": "agent_flow",
            "agent": "test_agent",
            "flow": "test_flow",
            "input_mapping": {"param": "value"},
            "output_key": "step1_output",
            "model_override": "gpt-4"
        }
        
        assert result == expected
    
    def test_step_config_validate_success(self):
        """测试成功的 StepConfig 验证"""
        step = StepConfig(
            id="step1",
            type="agent_flow",
            agent="test_agent",
            flow="test_flow",
            input_mapping={"param": "value"},
            output_key="step1_output"
        )
        
        errors = step.validate()
        assert errors == []
    
    def test_step_config_validate_missing_fields(self):
        """测试缺少字段的 StepConfig 验证"""
        step = StepConfig(
            id="",  # 空 ID
            type="agent_flow",
            agent="",  # 空 agent
            flow="test_flow",
            input_mapping={},
            output_key=""  # 空 output_key
        )
        
        errors = step.validate()
        
        assert len(errors) >= 3
        assert any("步骤 ID 不能为空" in error for error in errors)
        assert any("Agent ID 不能为空" in error for error in errors)
        assert any("输出键不能为空" in error for error in errors)
    
    def test_step_config_validate_invalid_input_mapping(self):
        """测试无效输入映射的验证"""
        step = StepConfig(
            id="step1",
            type="agent_flow",
            agent="test_agent",
            flow="test_flow",
            input_mapping={"": "value"},  # 空键
            output_key="step1_output"
        )
        
        errors = step.validate()
        
        assert any("输入映射的键不能为空" in error for error in errors)


class TestBaselineStepConfig:
    """测试 BaselineStepConfig 类"""
    
    def test_baseline_step_config_creation(self):
        """测试 BaselineStepConfig 创建"""
        step = BaselineStepConfig(flow="baseline_flow", model="gpt-4")
        
        assert step.flow == "baseline_flow"
        assert step.model == "gpt-4"
    
    def test_baseline_step_config_validate_success(self):
        """测试成功的 BaselineStepConfig 验证"""
        step = BaselineStepConfig(flow="baseline_flow", model="gpt-4")
        errors = step.validate()
        
        assert errors == []
    
    def test_baseline_step_config_validate_missing_flow(self):
        """测试缺少 flow 的验证"""
        step = BaselineStepConfig(flow="", model="gpt-4")
        errors = step.validate()
        
        assert len(errors) > 0
        assert any("缺少 flow 配置" in error for error in errors)


class TestVariantStepOverride:
    """测试 VariantStepOverride 类"""
    
    def test_variant_step_override_creation(self):
        """测试 VariantStepOverride 创建"""
        override = VariantStepOverride(flow="override_flow", model="gpt-4")
        
        assert override.flow == "override_flow"
        assert override.model == "gpt-4"
    
    def test_variant_step_override_validate_success(self):
        """测试成功的 VariantStepOverride 验证"""
        override = VariantStepOverride(flow="override_flow", model="gpt-4")
        errors = override.validate()
        
        assert errors == []
    
    def test_variant_step_override_validate_empty(self):
        """测试空覆盖的验证"""
        override = VariantStepOverride()
        errors = override.validate()
        
        assert len(errors) > 0
        assert any("必须指定 flow 或 model" in error for error in errors)


class TestBaselineConfig:
    """测试 BaselineConfig 类"""
    
    def test_baseline_config_creation(self):
        """测试 BaselineConfig 创建"""
        baseline = BaselineConfig(
            name="baseline_v1",
            description="基线配置",
            steps={
                "step1": BaselineStepConfig(flow="baseline_flow1"),
                "step2": BaselineStepConfig(flow="baseline_flow2", model="gpt-4")
            }
        )
        
        assert baseline.name == "baseline_v1"
        assert baseline.description == "基线配置"
        assert len(baseline.steps) == 2
        assert baseline.steps["step1"].flow == "baseline_flow1"
        assert baseline.steps["step2"].model == "gpt-4"
    
    def test_baseline_config_from_dict(self):
        """测试从字典创建 BaselineConfig"""
        data = {
            "name": "baseline_v1",
            "description": "基线配置",
            "steps": {
                "step1": {"flow": "baseline_flow1"},
                "step2": {"flow": "baseline_flow2", "model": "gpt-4"}
            }
        }
        
        baseline = BaselineConfig.from_dict(data)
        
        assert baseline.name == "baseline_v1"
        assert baseline.description == "基线配置"
        assert len(baseline.steps) == 2
        assert baseline.steps["step1"].flow == "baseline_flow1"
        assert baseline.steps["step2"].model == "gpt-4"
    
    def test_baseline_config_to_dict(self):
        """测试 BaselineConfig 转换为字典"""
        baseline = BaselineConfig(
            name="baseline_v1",
            description="基线配置",
            steps={
                "step1": BaselineStepConfig(flow="baseline_flow1"),
                "step2": BaselineStepConfig(flow="baseline_flow2", model="gpt-4")
            }
        )
        
        result = baseline.to_dict()
        
        expected = {
            "name": "baseline_v1",
            "description": "基线配置",
            "steps": {
                "step1": {"flow": "baseline_flow1", "model": None},
                "step2": {"flow": "baseline_flow2", "model": "gpt-4"}
            }
        }
        
        assert result == expected


class TestVariantConfig:
    """测试 VariantConfig 类"""
    
    def test_variant_config_creation(self):
        """测试 VariantConfig 创建"""
        variant = VariantConfig(
            description="变体配置",
            overrides={
                "step1": VariantStepOverride(flow="variant_flow1"),
                "step2": VariantStepOverride(flow="variant_flow2", model="gpt-4")
            }
        )
        
        assert variant.description == "变体配置"
        assert len(variant.overrides) == 2
        assert variant.overrides["step1"].flow == "variant_flow1"
        assert variant.overrides["step2"].model == "gpt-4"
    
    def test_variant_config_from_dict(self):
        """测试从字典创建 VariantConfig"""
        data = {
            "description": "变体配置",
            "overrides": {
                "step1": {"flow": "variant_flow1"},
                "step2": {"flow": "variant_flow2", "model": "gpt-4"}
            }
        }
        
        variant = VariantConfig.from_dict(data)
        
        assert variant.description == "变体配置"
        assert len(variant.overrides) == 2
        assert variant.overrides["step1"].flow == "variant_flow1"
        assert variant.overrides["step2"].model == "gpt-4"
    
    def test_variant_config_to_dict(self):
        """测试 VariantConfig 转换为字典"""
        variant = VariantConfig(
            description="变体配置",
            overrides={
                "step1": VariantStepOverride(flow="variant_flow1"),
                "step2": VariantStepOverride(flow="variant_flow2", model="gpt-4")
            }
        )
        
        result = variant.to_dict()
        
        expected = {
            "description": "变体配置",
            "overrides": {
                "step1": {"flow": "variant_flow1", "model": None},
                "step2": {"flow": "variant_flow2", "model": "gpt-4"}
            }
        }
        
        assert result == expected


class TestPipelineConfig:
    """测试 PipelineConfig 类"""
    
    def test_pipeline_config_creation(self, sample_pipeline_config):
        """测试 PipelineConfig 创建"""
        config = sample_pipeline_config
        
        assert config.id == "test_pipeline"
        assert config.name == "测试 Pipeline"
        assert config.description == "用于测试的 Pipeline 配置"
        assert config.default_testset == "test.jsonl"
        assert len(config.inputs) == 1
        assert len(config.steps) == 2
        assert len(config.outputs) == 1
        assert config.baseline is not None
        assert len(config.variants) == 1
    
    def test_pipeline_config_from_dict(self):
        """测试从字典创建 PipelineConfig"""
        data = {
            "id": "test_pipeline",
            "name": "测试 Pipeline",
            "description": "用于测试的 Pipeline 配置",
            "default_testset": "test.jsonl",
            "inputs": [{"name": "input_text", "desc": "输入文本"}],
            "steps": [
                {
                    "id": "step1",
                    "agent": "test_agent",
                    "flow": "test_flow",
                    "input_mapping": {"text": "input_text"},
                    "output_key": "step1_output"
                }
            ],
            "outputs": [{"key": "step1_output", "label": "输出"}],
            "baseline": {
                "name": "baseline_v1",
                "description": "基线配置",
                "steps": {
                    "step1": {"flow": "baseline_flow"}
                }
            },
            "variants": {
                "variant1": {
                    "description": "变体1",
                    "overrides": {
                        "step1": {"flow": "variant_flow"}
                    }
                }
            }
        }
        
        config = PipelineConfig.from_dict(data)
        
        assert config.id == "test_pipeline"
        assert config.name == "测试 Pipeline"
        assert len(config.steps) == 1
        assert config.baseline.name == "baseline_v1"
        assert "variant1" in config.variants
    
    def test_pipeline_config_to_dict(self, sample_pipeline_config):
        """测试 PipelineConfig 转换为字典"""
        result = sample_pipeline_config.to_dict()
        
        assert result["id"] == "test_pipeline"
        assert result["name"] == "测试 Pipeline"
        assert len(result["steps"]) == 2
        assert result["baseline"]["name"] == "baseline_v1"
        assert "variant1" in result["variants"]
    
    def test_pipeline_config_validate_success(self, sample_pipeline_config):
        """测试成功的 PipelineConfig 验证"""
        errors = sample_pipeline_config.validate()
        assert errors == []
    
    def test_pipeline_config_validate_missing_fields(self):
        """测试缺少字段的 PipelineConfig 验证"""
        config = PipelineConfig(
            id="",  # 空 ID
            name="",  # 空名称
            description="",
            default_testset="",
            inputs=[],
            steps=[],  # 空步骤列表
            outputs=[],
            baseline=None,
            variants={}
        )
        
        errors = config.validate()
        
        assert len(errors) >= 3
        assert any("Pipeline ID 不能为空" in error for error in errors)
        assert any("Pipeline 名称不能为空" in error for error in errors)
        assert any("Pipeline 必须包含至少一个步骤" in error for error in errors)
    
    def test_pipeline_config_validate_duplicate_step_ids(self):
        """测试重复步骤 ID 的验证"""
        config = PipelineConfig(
            id="test_pipeline",
            name="测试 Pipeline",
            description="",
            default_testset="",
            inputs=[],
            steps=[
                StepConfig(
                    id="step1",
                    type="agent_flow",
                    agent="test_agent",
                    flow="test_flow",
                    input_mapping={},
                    output_key="output1"
                ),
                StepConfig(
                    id="step1",  # 重复 ID
                    type="agent_flow",
                    agent="test_agent",
                    flow="test_flow2",
                    input_mapping={},
                    output_key="output2"
                )
            ],
            outputs=[],
            baseline=None,
            variants={}
        )
        
        errors = config.validate()
        
        assert any("重复的步骤 ID" in error for error in errors)
    
    def test_pipeline_config_validate_duplicate_output_keys(self):
        """测试重复输出键的验证"""
        config = PipelineConfig(
            id="test_pipeline",
            name="测试 Pipeline",
            description="",
            default_testset="",
            inputs=[],
            steps=[
                StepConfig(
                    id="step1",
                    type="agent_flow",
                    agent="test_agent",
                    flow="test_flow",
                    input_mapping={},
                    output_key="same_output"
                ),
                StepConfig(
                    id="step2",
                    type="agent_flow",
                    agent="test_agent",
                    flow="test_flow2",
                    input_mapping={},
                    output_key="same_output"  # 重复输出键
                )
            ],
            outputs=[],
            baseline=None,
            variants={}
        )
        
        errors = config.validate()
        
        assert any("重复的输出键" in error for error in errors)
    
    def test_pipeline_config_validate_circular_dependency(self):
        """测试循环依赖的验证"""
        config = PipelineConfig(
            id="test_pipeline",
            name="测试 Pipeline",
            description="",
            default_testset="",
            inputs=[],
            steps=[
                StepConfig(
                    id="step1",
                    type="agent_flow",
                    agent="test_agent",
                    flow="test_flow",
                    input_mapping={"input": "step2_output"},  # 依赖 step2
                    output_key="step1_output"
                ),
                StepConfig(
                    id="step2",
                    type="agent_flow",
                    agent="test_agent",
                    flow="test_flow2",
                    input_mapping={"input": "step1_output"},  # 依赖 step1，形成循环
                    output_key="step2_output"
                )
            ],
            outputs=[],
            baseline=None,
            variants={}
        )
        
        errors = config.validate()
        
        assert any("循环依赖" in error for error in errors)


class TestEvaluationResult:
    """测试 EvaluationResult 类"""
    
    def test_evaluation_result_creation(self):
        """测试 EvaluationResult 创建"""
        result = EvaluationResult(
            sample_id="sample1",
            entity_type="agent",
            entity_id="test_agent",
            variant="baseline",
            overall_score=8.5,
            must_have_pass=True,
            rule_violations=["violation1"],
            judge_feedback="良好",
            execution_time=1.5,
            step_outputs={"step1": "output1"}
        )
        
        assert result.sample_id == "sample1"
        assert result.entity_type == "agent"
        assert result.entity_id == "test_agent"
        assert result.variant == "baseline"
        assert result.overall_score == 8.5
        assert result.must_have_pass is True
        assert result.rule_violations == ["violation1"]
        assert result.judge_feedback == "良好"
        assert result.execution_time == 1.5
        assert result.step_outputs == {"step1": "output1"}
        assert isinstance(result.created_at, datetime)
    
    def test_evaluation_result_to_dict(self):
        """测试 EvaluationResult 转换为字典"""
        result = EvaluationResult(
            sample_id="sample1",
            entity_type="pipeline",
            entity_id="test_pipeline",
            variant="baseline",
            overall_score=8.5,
            must_have_pass=True,
            rule_violations=["violation1"],
            judge_feedback="良好",
            execution_time=1.5
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["sample_id"] == "sample1"
        assert result_dict["entity_type"] == "pipeline"
        assert result_dict["entity_id"] == "test_pipeline"
        assert result_dict["variant"] == "baseline"
        assert result_dict["overall_score"] == 8.5
        assert result_dict["must_have_pass"] is True
        assert result_dict["rule_violations"] == ["violation1"]
        assert result_dict["judge_feedback"] == "良好"
        assert result_dict["execution_time"] == 1.5
        assert "created_at" in result_dict
    
    def test_evaluation_result_from_dict(self):
        """测试从字典创建 EvaluationResult"""
        data = {
            "sample_id": "sample1",
            "variant": "baseline",
            "overall_score": 8.5,
            "must_have_pass": True,
            "rule_violations": ["violation1"],
            "judge_feedback": "良好",
            "execution_time": 1.5,
            "created_at": "2025-01-01T10:00:00"
        }
        
        result = EvaluationResult.from_dict(data)
        
        assert result.sample_id == "sample1"
        assert result.variant == "baseline"
        assert result.overall_score == 8.5
        assert result.must_have_pass is True
        assert result.rule_violations == ["violation1"]
        assert result.judge_feedback == "良好"
        assert result.execution_time == 1.5


class TestRegressionCase:
    """测试 RegressionCase 类"""
    
    def test_regression_case_creation(self):
        """测试 RegressionCase 创建"""
        case = RegressionCase(
            sample_id="sample1",
            baseline_score=8.0,
            variant_score=6.5,
            score_delta=-1.5,
            severity="high",
            baseline_must_have_pass=True,
            variant_must_have_pass=False,
            new_rule_violations=["new_violation"],
            description="性能显著下降"
        )
        
        assert case.sample_id == "sample1"
        assert case.baseline_score == 8.0
        assert case.variant_score == 6.5
        assert case.score_delta == -1.5
        assert case.severity == "high"
        assert case.baseline_must_have_pass is True
        assert case.variant_must_have_pass is False
        assert case.new_rule_violations == ["new_violation"]
        assert case.description == "性能显著下降"
    
    def test_regression_case_to_dict(self):
        """测试 RegressionCase 转换为字典"""
        case = RegressionCase(
            sample_id="sample1",
            baseline_score=8.0,
            variant_score=6.5,
            score_delta=-1.5,
            severity="high"
        )
        
        result = case.to_dict()
        
        assert result["sample_id"] == "sample1"
        assert result["baseline_score"] == 8.0
        assert result["variant_score"] == 6.5
        assert result["score_delta"] == -1.5
        assert result["severity"] == "high"


class TestComparisonReport:
    """测试 ComparisonReport 类"""
    
    def test_comparison_report_creation(self):
        """测试 ComparisonReport 创建"""
        regression_case = RegressionCase(
            sample_id="sample1",
            baseline_score=8.0,
            variant_score=6.5,
            score_delta=-1.5,
            severity="high"
        )
        
        report = ComparisonReport(
            baseline_name="baseline_v1",
            variant_name="variant_v1",
            sample_count=100,
            score_delta=-0.5,
            must_have_delta=-0.1,
            rule_violation_delta=0.05,
            tag_performance={"test": -0.3, "regression": -0.8},
            worst_regressions=[regression_case],
            summary="整体性能下降"
        )
        
        assert report.baseline_name == "baseline_v1"
        assert report.variant_name == "variant_v1"
        assert report.sample_count == 100
        assert report.score_delta == -0.5
        assert report.must_have_delta == -0.1
        assert report.rule_violation_delta == 0.05
        assert report.tag_performance == {"test": -0.3, "regression": -0.8}
        assert len(report.worst_regressions) == 1
        assert report.summary == "整体性能下降"
        assert isinstance(report.created_at, datetime)
    
    def test_comparison_report_to_dict(self):
        """测试 ComparisonReport 转换为字典"""
        regression_case = RegressionCase(
            sample_id="sample1",
            baseline_score=8.0,
            variant_score=6.5,
            score_delta=-1.5,
            severity="high"
        )
        
        report = ComparisonReport(
            baseline_name="baseline_v1",
            variant_name="variant_v1",
            sample_count=100,
            score_delta=-0.5,
            worst_regressions=[regression_case]
        )
        
        result = report.to_dict()
        
        assert result["baseline_name"] == "baseline_v1"
        assert result["variant_name"] == "variant_v1"
        assert result["sample_count"] == 100
        assert result["score_delta"] == -0.5
        assert len(result["worst_regressions"]) == 1
        assert "created_at" in result