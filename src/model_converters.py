# src/model_converters.py
"""
Model Converters

Utility functions to convert between dataclass models (src/models.py) 
and Pydantic models (src/api/models.py).

This module provides bidirectional conversion to support:
- API request/response validation (Pydantic)
- Internal business logic (dataclasses)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

# Import dataclass models
from src.models import (
    InputSpec as DataclassInputSpec,
    OutputSpec as DataclassOutputSpec,
    StepConfig as DataclassStepConfig,
    PipelineConfig as DataclassPipelineConfig,
    CodeNodeConfig as DataclassCodeNodeConfig,
    EvaluationResult as DataclassEvaluationResult,
    RegressionCase as DataclassRegressionCase,
    ComparisonReport as DataclassComparisonReport,
)

# Import Pydantic models
from src.api.models import (
    InputSpec as PydanticInputSpec,
    OutputSpec as PydanticOutputSpec,
    StepConfig as PydanticStepConfig,
    PipelineConfigResponse,
    StepType,
    PipelineStatus,
)


# ============================================================================
# Pipeline Models Conversion
# ============================================================================

def dataclass_input_spec_to_pydantic(dc: DataclassInputSpec) -> PydanticInputSpec:
    """Convert dataclass InputSpec to Pydantic InputSpec."""
    return PydanticInputSpec(
        name=dc.name,
        desc=dc.desc,
        required=dc.required
    )


def pydantic_input_spec_to_dataclass(pyd: PydanticInputSpec) -> DataclassInputSpec:
    """Convert Pydantic InputSpec to dataclass InputSpec."""
    return DataclassInputSpec(
        name=pyd.name,
        desc=pyd.desc,
        required=pyd.required
    )


def dataclass_output_spec_to_pydantic(dc: DataclassOutputSpec) -> PydanticOutputSpec:
    """Convert dataclass OutputSpec to Pydantic OutputSpec."""
    return PydanticOutputSpec(
        key=dc.key,
        label=dc.label
    )


def pydantic_output_spec_to_dataclass(pyd: PydanticOutputSpec) -> DataclassOutputSpec:
    """Convert Pydantic OutputSpec to dataclass OutputSpec."""
    return DataclassOutputSpec(
        key=pyd.key,
        label=pyd.label
    )


def dataclass_step_config_to_pydantic(dc: DataclassStepConfig) -> PydanticStepConfig:
    """Convert dataclass StepConfig to Pydantic StepConfig."""
    # Map type string to StepType enum
    step_type_map = {
        "agent_flow": StepType.AGENT_FLOW,
        "code_node": StepType.CODE_NODE,
        "batch_aggregator": StepType.BATCH_AGGREGATOR,
    }
    
    return PydanticStepConfig(
        id=dc.id,
        type=step_type_map.get(dc.type, StepType.AGENT_FLOW),
        agent=dc.agent if dc.agent else None,
        flow=dc.flow if dc.flow else None,
        input_mapping=dc.input_mapping,
        output_key=dc.output_key,
        concurrent_group=dc.concurrent_group,
        depends_on=dc.depends_on,
        required=dc.required
    )


def pydantic_step_config_to_dataclass(pyd: PydanticStepConfig) -> DataclassStepConfig:
    """Convert Pydantic StepConfig to dataclass StepConfig."""
    return DataclassStepConfig(
        id=pyd.id,
        type=pyd.type.value,  # Convert enum to string
        agent=pyd.agent or "",
        flow=pyd.flow or "",
        input_mapping=pyd.input_mapping,
        output_key=pyd.output_key,
        concurrent_group=pyd.concurrent_group,
        depends_on=pyd.depends_on,
        required=pyd.required
    )


def dataclass_pipeline_config_to_pydantic(dc: DataclassPipelineConfig) -> PipelineConfigResponse:
    """Convert dataclass PipelineConfig to Pydantic PipelineConfigResponse."""
    return PipelineConfigResponse(
        id=dc.id,
        name=dc.name,
        description=dc.description,
        version="1.0.0",  # Default version if not specified
        status=PipelineStatus.ACTIVE,  # Default status
        inputs=[dataclass_input_spec_to_pydantic(inp) for inp in dc.inputs],
        outputs=[dataclass_output_spec_to_pydantic(out) for out in dc.outputs],
        steps=[dataclass_step_config_to_pydantic(step) for step in dc.steps],
        created_at=None,
        updated_at=None
    )


def pydantic_pipeline_config_to_dataclass(pyd: PipelineConfigResponse) -> DataclassPipelineConfig:
    """Convert Pydantic PipelineConfigResponse to dataclass PipelineConfig."""
    return DataclassPipelineConfig(
        id=pyd.id,
        name=pyd.name,
        description=pyd.description,
        default_testset="",
        inputs=[pydantic_input_spec_to_dataclass(inp) for inp in pyd.inputs],
        outputs=[pydantic_output_spec_to_dataclass(out) for out in pyd.outputs],
        steps=[pydantic_step_config_to_dataclass(step) for step in pyd.steps],
        baseline=None,
        variants={},
        evaluation_target=None
    )


# ============================================================================
# Generic Conversion Helpers
# ============================================================================

def dataclass_to_pydantic_dict(dataclass_instance) -> Dict[str, Any]:
    """
    Convert any dataclass instance to a dictionary suitable for Pydantic model creation.
    
    This is a generic helper that uses the to_dict() method if available,
    or falls back to dataclasses.asdict().
    """
    if hasattr(dataclass_instance, 'to_dict'):
        return dataclass_instance.to_dict()
    else:
        from dataclasses import asdict
        return asdict(dataclass_instance)


def pydantic_to_dataclass_dict(pydantic_instance) -> Dict[str, Any]:
    """
    Convert any Pydantic model instance to a dictionary suitable for dataclass creation.
    
    Uses Pydantic's model_dump() method (or dict() for older versions).
    """
    if hasattr(pydantic_instance, 'model_dump'):
        return pydantic_instance.model_dump()
    elif hasattr(pydantic_instance, 'dict'):
        return pydantic_instance.dict()
    else:
        raise ValueError(f"Cannot convert {type(pydantic_instance)} to dict")


# ============================================================================
# Batch Conversion Utilities
# ============================================================================

def convert_dataclass_list_to_pydantic(
    dataclass_list: List[Any],
    converter_func
) -> List[Any]:
    """Convert a list of dataclass instances to Pydantic models."""
    return [converter_func(item) for item in dataclass_list]


def convert_pydantic_list_to_dataclass(
    pydantic_list: List[Any],
    converter_func
) -> List[Any]:
    """Convert a list of Pydantic models to dataclass instances."""
    return [converter_func(item) for item in pydantic_list]
