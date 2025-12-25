# tests/test_model_serialization.py
"""
Tests for data model serialization

Tests to_dict, from_dict, to_json, and from_json methods for all data models.
"""

import pytest
import json
from datetime import datetime

from src.models import (
    OutputParserConfig,
    InputSpec,
    OutputSpec,
    CodeNodeConfig,
    StepConfig,
    BaselineStepConfig,
    BaselineConfig,
    VariantStepOverride,
    VariantConfig,
    PipelineConfig,
    RuleConfig,
    CaseFieldConfig,
    EvaluationConfig,
    EvaluationResult,
    RegressionCase,
    ComparisonReport,
)


class TestOutputParserConfigSerialization:
    """Test OutputParserConfig serialization."""
    
    def test_to_dict(self):
        """Test to_dict method."""
        config = OutputParserConfig(
            type="json",
            schema={"type": "object"},
            retry_on_error=True,
            max_retries=3
        )
        result = config.to_dict()
        
        assert result["type"] == "json"
        assert result["schema"] == {"type": "object"}
    
    def test_from_dict(self):
        """Test from_dict method."""
        data = {
            "type": "json",
            "schema": {"type": "object"},
            "retry_on_error": True,
            "max_retries": 3
        }
        config = OutputParserConfig.from_dict(data)
        
        assert config.type == "json"
        assert config.schema == {"type": "object"}
        assert config.retry_on_error is True
        assert config.max_retries == 3
    
    def test_json_round_trip(self):
        """Test JSON serialization round trip."""
        config = OutputParserConfig(
            type="pydantic",
            pydantic_model="MyModel",
            retry_on_error=False,
            max_retries=5
        )
        
        json_str = config.to_json()
        loaded_config = OutputParserConfig.from_json(json_str)
        
        assert loaded_config.type == config.type
        assert loaded_config.pydantic_model == config.pydantic_model
        assert loaded_config.retry_on_error == config.retry_on_error
        assert loaded_config.max_retries == config.max_retries


class TestInputSpecSerialization:
    """Test InputSpec serialization."""
    
    def test_to_dict(self):
        """Test to_dict method."""
        spec = InputSpec(name="input1", desc="Test input", required=True)
        result = spec.to_dict()
        
        assert result["name"] == "input1"
        assert result["desc"] == "Test input"
        assert result["required"] is True
    
    def test_json_round_trip(self):
        """Test JSON serialization round trip."""
        spec = InputSpec(name="input2", desc="Another input", required=False)
        
        json_str = spec.to_json()
        loaded_spec = InputSpec.from_json(json_str)
        
        assert loaded_spec.name == spec.name
        assert loaded_spec.desc == spec.desc
        assert loaded_spec.required == spec.required


class TestOutputSpecSerialization:
    """Test OutputSpec serialization."""
    
    def test_to_dict(self):
        """Test to_dict method."""
        spec = OutputSpec(key="output1", label="Test output")
        result = spec.to_dict()
        
        assert result["key"] == "output1"
        assert result["label"] == "Test output"
    
    def test_json_round_trip(self):
        """Test JSON serialization round trip."""
        spec = OutputSpec(key="output2", label="Another output")
        
        json_str = spec.to_json()
        loaded_spec = OutputSpec.from_json(json_str)
        
        assert loaded_spec.key == spec.key
        assert loaded_spec.label == spec.label


class TestCodeNodeConfigSerialization:
    """Test CodeNodeConfig serialization."""
    
    def test_to_dict(self):
        """Test to_dict method."""
        config = CodeNodeConfig(
            language="python",
            code="print('hello')",
            timeout=30,
            env_vars={"KEY": "value"}
        )
        result = config.to_dict()
        
        assert result["language"] == "python"
        assert result["code"] == "print('hello')"
        assert result["timeout"] == 30
        assert result["env_vars"] == {"KEY": "value"}
    
    def test_json_round_trip(self):
        """Test JSON serialization round trip."""
        config = CodeNodeConfig(
            language="javascript",
            code_file="script.js",
            timeout=60
        )
        
        json_str = config.to_json()
        loaded_config = CodeNodeConfig.from_json(json_str)
        
        assert loaded_config.language == config.language
        assert loaded_config.code_file == config.code_file
        assert loaded_config.timeout == config.timeout


class TestStepConfigSerialization:
    """Test StepConfig serialization."""
    
    def test_agent_flow_step_json_round_trip(self):
        """Test JSON round trip for agent flow step."""
        step = StepConfig(
            id="step1",
            type="agent_flow",
            agent="test_agent",
            flow="test_flow",
            input_mapping={"input": "source"},
            output_key="result"
        )
        
        json_str = step.to_json()
        loaded_step = StepConfig.from_json(json_str)
        
        assert loaded_step.id == step.id
        assert loaded_step.type == step.type
        assert loaded_step.agent == step.agent
        assert loaded_step.flow == step.flow
        assert loaded_step.input_mapping == step.input_mapping
        assert loaded_step.output_key == step.output_key
    
    def test_code_node_step_json_round_trip(self):
        """Test JSON round trip for code node step."""
        step = StepConfig(
            id="step2",
            type="code_node",
            language="python",
            code="return x * 2",
            input_mapping={"x": "input"},
            output_key="doubled"
        )
        
        json_str = step.to_json()
        loaded_step = StepConfig.from_json(json_str)
        
        assert loaded_step.id == step.id
        assert loaded_step.type == step.type
        assert loaded_step.language == step.language
        assert loaded_step.code == step.code


class TestBaselineConfigSerialization:
    """Test BaselineConfig serialization."""
    
    def test_json_round_trip(self):
        """Test JSON round trip."""
        baseline = BaselineConfig(
            name="baseline_v1",
            description="Test baseline",
            steps={
                "step1": BaselineStepConfig(flow="flow1", model="model1"),
                "step2": BaselineStepConfig(flow="flow2")
            }
        )
        
        json_str = baseline.to_json()
        loaded_baseline = BaselineConfig.from_json(json_str)
        
        assert loaded_baseline.name == baseline.name
        assert loaded_baseline.description == baseline.description
        assert len(loaded_baseline.steps) == 2
        assert loaded_baseline.steps["step1"].flow == "flow1"
        assert loaded_baseline.steps["step1"].model == "model1"


class TestVariantConfigSerialization:
    """Test VariantConfig serialization."""
    
    def test_json_round_trip(self):
        """Test JSON round trip."""
        variant = VariantConfig(
            description="Test variant",
            overrides={
                "step1": VariantStepOverride(flow="new_flow"),
                "step2": VariantStepOverride(model="new_model")
            }
        )
        
        json_str = variant.to_json()
        loaded_variant = VariantConfig.from_json(json_str)
        
        assert loaded_variant.description == variant.description
        assert len(loaded_variant.overrides) == 2
        assert loaded_variant.overrides["step1"].flow == "new_flow"
        assert loaded_variant.overrides["step2"].model == "new_model"


class TestPipelineConfigSerialization:
    """Test PipelineConfig serialization."""
    
    def test_json_round_trip(self):
        """Test JSON round trip."""
        pipeline = PipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            description="A test pipeline",
            inputs=[InputSpec(name="input1")],
            outputs=[OutputSpec(key="output1")],
            steps=[
                StepConfig(
                    id="step1",
                    type="agent_flow",
                    agent="agent1",
                    flow="flow1",
                    input_mapping={"x": "input1"},
                    output_key="output1"
                )
            ]
        )
        
        json_str = pipeline.to_json()
        loaded_pipeline = PipelineConfig.from_json(json_str)
        
        assert loaded_pipeline.id == pipeline.id
        assert loaded_pipeline.name == pipeline.name
        assert loaded_pipeline.description == pipeline.description
        assert len(loaded_pipeline.inputs) == 1
        assert len(loaded_pipeline.outputs) == 1
        assert len(loaded_pipeline.steps) == 1


class TestRuleConfigSerialization:
    """Test RuleConfig serialization."""
    
    def test_json_round_trip(self):
        """Test JSON round trip."""
        rule = RuleConfig(
            name="test_rule",
            type="contains",
            params={"text": "hello"},
            severity="error",
            message="Must contain hello"
        )
        
        json_str = rule.to_json()
        loaded_rule = RuleConfig.from_json(json_str)
        
        assert loaded_rule.name == rule.name
        assert loaded_rule.type == rule.type
        assert loaded_rule.params == rule.params
        assert loaded_rule.severity == rule.severity
        assert loaded_rule.message == rule.message


class TestCaseFieldConfigSerialization:
    """Test CaseFieldConfig serialization."""
    
    def test_json_round_trip(self):
        """Test JSON round trip."""
        field = CaseFieldConfig(
            key="field1",
            label="Field 1",
            section="context",
            truncate=100,
            as_json=True,
            required=True
        )
        
        json_str = field.to_json()
        loaded_field = CaseFieldConfig.from_json(json_str)
        
        assert loaded_field.key == field.key
        assert loaded_field.label == field.label
        assert loaded_field.section == field.section
        assert loaded_field.truncate == field.truncate
        assert loaded_field.as_json == field.as_json
        assert loaded_field.required == field.required


class TestEvaluationConfigSerialization:
    """Test EvaluationConfig serialization."""
    
    def test_json_round_trip(self):
        """Test JSON round trip."""
        config = EvaluationConfig(
            rules=[RuleConfig(name="rule1", type="contains", params={})],
            judge_enabled=True,
            judge_agent_id="judge1",
            scale_min=0,
            scale_max=10,
            case_fields=[CaseFieldConfig(key="field1")]
        )
        
        json_str = config.to_json()
        loaded_config = EvaluationConfig.from_json(json_str)
        
        assert len(loaded_config.rules) == 1
        assert loaded_config.judge_enabled == config.judge_enabled
        assert loaded_config.judge_agent_id == config.judge_agent_id
        assert loaded_config.scale_min == config.scale_min
        assert loaded_config.scale_max == config.scale_max
        assert len(loaded_config.case_fields) == 1


class TestEvaluationResultSerialization:
    """Test EvaluationResult serialization."""
    
    def test_json_round_trip(self):
        """Test JSON round trip."""
        result = EvaluationResult(
            sample_id="sample1",
            entity_type="agent",
            entity_id="agent1",
            variant="v1",
            overall_score=8.5,
            must_have_pass=True,
            rule_violations=["violation1"],
            judge_feedback="Good",
            execution_time=1.5
        )
        
        json_str = result.to_json()
        loaded_result = EvaluationResult.from_json(json_str)
        
        assert loaded_result.sample_id == result.sample_id
        assert loaded_result.entity_type == result.entity_type
        assert loaded_result.entity_id == result.entity_id
        assert loaded_result.variant == result.variant
        assert loaded_result.overall_score == result.overall_score
        assert loaded_result.must_have_pass == result.must_have_pass


class TestRegressionCaseSerialization:
    """Test RegressionCase serialization."""
    
    def test_json_round_trip(self):
        """Test JSON round trip."""
        case = RegressionCase(
            sample_id="sample1",
            baseline_score=8.0,
            variant_score=7.0,
            score_delta=-1.0,
            severity="major",
            description="Performance degradation"
        )
        
        json_str = case.to_json()
        loaded_case = RegressionCase.from_json(json_str)
        
        assert loaded_case.sample_id == case.sample_id
        assert loaded_case.baseline_score == case.baseline_score
        assert loaded_case.variant_score == case.variant_score
        assert loaded_case.score_delta == case.score_delta
        assert loaded_case.severity == case.severity


class TestComparisonReportSerialization:
    """Test ComparisonReport serialization."""
    
    def test_json_round_trip(self):
        """Test JSON round trip."""
        report = ComparisonReport(
            baseline_name="baseline",
            variant_name="variant",
            sample_count=10,
            score_delta=-0.5,
            must_have_delta=0.0,
            rule_violation_delta=1.0,
            tag_performance={"tag1": 0.8},
            worst_regressions=[
                RegressionCase(
                    sample_id="sample1",
                    baseline_score=8.0,
                    variant_score=7.0,
                    score_delta=-1.0,
                    severity="major"
                )
            ],
            summary="Overall performance decreased"
        )
        
        json_str = report.to_json()
        loaded_report = ComparisonReport.from_json(json_str)
        
        assert loaded_report.baseline_name == report.baseline_name
        assert loaded_report.variant_name == report.variant_name
        assert loaded_report.sample_count == report.sample_count
        assert loaded_report.score_delta == report.score_delta
        assert len(loaded_report.worst_regressions) == 1
