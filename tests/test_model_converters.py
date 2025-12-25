# tests/test_model_converters.py
"""
Tests for model converters

Tests conversion between dataclass models and Pydantic models.
"""

import pytest

from src.models import (
    InputSpec as DataclassInputSpec,
    OutputSpec as DataclassOutputSpec,
    StepConfig as DataclassStepConfig,
    PipelineConfig as DataclassPipelineConfig,
)

from src.api.models import (
    InputSpec as PydanticInputSpec,
    OutputSpec as PydanticOutputSpec,
    StepConfig as PydanticStepConfig,
    PipelineConfigResponse,
    StepType,
)

from src.model_converters import (
    dataclass_input_spec_to_pydantic,
    pydantic_input_spec_to_dataclass,
    dataclass_output_spec_to_pydantic,
    pydantic_output_spec_to_dataclass,
    dataclass_step_config_to_pydantic,
    pydantic_step_config_to_dataclass,
    dataclass_pipeline_config_to_pydantic,
    pydantic_pipeline_config_to_dataclass,
)


class TestInputSpecConversion:
    """Test InputSpec conversion between dataclass and Pydantic."""
    
    def test_dataclass_to_pydantic(self):
        """Test converting dataclass InputSpec to Pydantic."""
        dc_spec = DataclassInputSpec(
            name="test_input",
            desc="Test description",
            required=True
        )
        
        pyd_spec = dataclass_input_spec_to_pydantic(dc_spec)
        
        assert isinstance(pyd_spec, PydanticInputSpec)
        assert pyd_spec.name == dc_spec.name
        assert pyd_spec.desc == dc_spec.desc
        assert pyd_spec.required == dc_spec.required
    
    def test_pydantic_to_dataclass(self):
        """Test converting Pydantic InputSpec to dataclass."""
        pyd_spec = PydanticInputSpec(
            name="test_input",
            desc="Test description",
            required=False
        )
        
        dc_spec = pydantic_input_spec_to_dataclass(pyd_spec)
        
        assert isinstance(dc_spec, DataclassInputSpec)
        assert dc_spec.name == pyd_spec.name
        assert dc_spec.desc == pyd_spec.desc
        assert dc_spec.required == pyd_spec.required
    
    def test_round_trip_conversion(self):
        """Test round-trip conversion preserves data."""
        original = DataclassInputSpec(
            name="round_trip",
            desc="Round trip test",
            required=True
        )
        
        pydantic = dataclass_input_spec_to_pydantic(original)
        back_to_dataclass = pydantic_input_spec_to_dataclass(pydantic)
        
        assert back_to_dataclass.name == original.name
        assert back_to_dataclass.desc == original.desc
        assert back_to_dataclass.required == original.required


class TestOutputSpecConversion:
    """Test OutputSpec conversion between dataclass and Pydantic."""
    
    def test_dataclass_to_pydantic(self):
        """Test converting dataclass OutputSpec to Pydantic."""
        dc_spec = DataclassOutputSpec(
            key="test_output",
            label="Test Label"
        )
        
        pyd_spec = dataclass_output_spec_to_pydantic(dc_spec)
        
        assert isinstance(pyd_spec, PydanticOutputSpec)
        assert pyd_spec.key == dc_spec.key
        assert pyd_spec.label == dc_spec.label
    
    def test_pydantic_to_dataclass(self):
        """Test converting Pydantic OutputSpec to dataclass."""
        pyd_spec = PydanticOutputSpec(
            key="test_output",
            label="Test Label"
        )
        
        dc_spec = pydantic_output_spec_to_dataclass(pyd_spec)
        
        assert isinstance(dc_spec, DataclassOutputSpec)
        assert dc_spec.key == pyd_spec.key
        assert dc_spec.label == pyd_spec.label


class TestStepConfigConversion:
    """Test StepConfig conversion between dataclass and Pydantic."""
    
    def test_agent_flow_step_dataclass_to_pydantic(self):
        """Test converting agent flow step from dataclass to Pydantic."""
        dc_step = DataclassStepConfig(
            id="step1",
            type="agent_flow",
            agent="test_agent",
            flow="test_flow",
            input_mapping={"input": "source"},
            output_key="result",
            required=True
        )
        
        pyd_step = dataclass_step_config_to_pydantic(dc_step)
        
        assert isinstance(pyd_step, PydanticStepConfig)
        assert pyd_step.id == dc_step.id
        assert pyd_step.type == StepType.AGENT_FLOW
        assert pyd_step.agent == dc_step.agent
        assert pyd_step.flow == dc_step.flow
        assert pyd_step.input_mapping == dc_step.input_mapping
        assert pyd_step.output_key == dc_step.output_key
    
    def test_code_node_step_dataclass_to_pydantic(self):
        """Test converting code node step from dataclass to Pydantic."""
        dc_step = DataclassStepConfig(
            id="step2",
            type="code_node",
            input_mapping={"x": "input"},
            output_key="result"
        )
        
        pyd_step = dataclass_step_config_to_pydantic(dc_step)
        
        assert pyd_step.type == StepType.CODE_NODE
    
    def test_pydantic_to_dataclass(self):
        """Test converting Pydantic StepConfig to dataclass."""
        pyd_step = PydanticStepConfig(
            id="step1",
            type=StepType.AGENT_FLOW,
            agent="test_agent",
            flow="test_flow",
            input_mapping={"input": "source"},
            output_key="result"
        )
        
        dc_step = pydantic_step_config_to_dataclass(pyd_step)
        
        assert isinstance(dc_step, DataclassStepConfig)
        assert dc_step.id == pyd_step.id
        assert dc_step.type == "agent_flow"
        assert dc_step.agent == pyd_step.agent
        assert dc_step.flow == pyd_step.flow


class TestPipelineConfigConversion:
    """Test PipelineConfig conversion between dataclass and Pydantic."""
    
    def test_dataclass_to_pydantic(self):
        """Test converting dataclass PipelineConfig to Pydantic."""
        dc_pipeline = DataclassPipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            description="A test pipeline",
            inputs=[DataclassInputSpec(name="input1")],
            outputs=[DataclassOutputSpec(key="output1")],
            steps=[
                DataclassStepConfig(
                    id="step1",
                    type="agent_flow",
                    agent="agent1",
                    flow="flow1",
                    input_mapping={"x": "input1"},
                    output_key="output1"
                )
            ]
        )
        
        pyd_pipeline = dataclass_pipeline_config_to_pydantic(dc_pipeline)
        
        assert isinstance(pyd_pipeline, PipelineConfigResponse)
        assert pyd_pipeline.id == dc_pipeline.id
        assert pyd_pipeline.name == dc_pipeline.name
        assert pyd_pipeline.description == dc_pipeline.description
        assert len(pyd_pipeline.inputs) == 1
        assert len(pyd_pipeline.outputs) == 1
        assert len(pyd_pipeline.steps) == 1
    
    def test_pydantic_to_dataclass(self):
        """Test converting Pydantic PipelineConfigResponse to dataclass."""
        pyd_pipeline = PipelineConfigResponse(
            id="test_pipeline",
            name="Test Pipeline",
            description="A test pipeline",
            version="1.0.0",
            status="active",
            inputs=[PydanticInputSpec(name="input1")],
            outputs=[PydanticOutputSpec(key="output1")],
            steps=[
                PydanticStepConfig(
                    id="step1",
                    type=StepType.AGENT_FLOW,
                    agent="agent1",
                    flow="flow1",
                    input_mapping={"x": "input1"},
                    output_key="output1"
                )
            ]
        )
        
        dc_pipeline = pydantic_pipeline_config_to_dataclass(pyd_pipeline)
        
        assert isinstance(dc_pipeline, DataclassPipelineConfig)
        assert dc_pipeline.id == pyd_pipeline.id
        assert dc_pipeline.name == pyd_pipeline.name
        assert dc_pipeline.description == pyd_pipeline.description
        assert len(dc_pipeline.inputs) == 1
        assert len(dc_pipeline.outputs) == 1
        assert len(dc_pipeline.steps) == 1
    
    def test_complex_pipeline_round_trip(self):
        """Test round-trip conversion of complex pipeline."""
        original = DataclassPipelineConfig(
            id="complex_pipeline",
            name="Complex Pipeline",
            description="A complex test pipeline",
            inputs=[
                DataclassInputSpec(name="input1", desc="First input", required=True),
                DataclassInputSpec(name="input2", desc="Second input", required=False)
            ],
            outputs=[
                DataclassOutputSpec(key="output1", label="First output"),
                DataclassOutputSpec(key="output2", label="Second output")
            ],
            steps=[
                DataclassStepConfig(
                    id="step1",
                    type="agent_flow",
                    agent="agent1",
                    flow="flow1",
                    input_mapping={"x": "input1"},
                    output_key="intermediate"
                ),
                DataclassStepConfig(
                    id="step2",
                    type="agent_flow",
                    agent="agent2",
                    flow="flow2",
                    input_mapping={"y": "intermediate", "z": "input2"},
                    output_key="output1"
                )
            ]
        )
        
        pydantic = dataclass_pipeline_config_to_pydantic(original)
        back_to_dataclass = pydantic_pipeline_config_to_dataclass(pydantic)
        
        assert back_to_dataclass.id == original.id
        assert back_to_dataclass.name == original.name
        assert len(back_to_dataclass.inputs) == 2
        assert len(back_to_dataclass.outputs) == 2
        assert len(back_to_dataclass.steps) == 2
        assert back_to_dataclass.steps[0].id == "step1"
        assert back_to_dataclass.steps[1].id == "step2"
