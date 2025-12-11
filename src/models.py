# src/models.py
"""
Pipeline Regression System 核心数据模型

定义了 Pipeline、Step、Baseline、Variant 等核心数据结构，
支持 YAML 配置的序列化/反序列化和数据验证。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import yaml
import json
from datetime import datetime


@dataclass
class InputSpec:
    """Pipeline 输入字段规范"""
    name: str
    desc: str = ""
    required: bool = True
    
    def validate(self) -> List[str]:
        """验证输入规范"""
        errors = []
        if not self.name:
            errors.append("输入字段名称不能为空")
        if not self.name.isidentifier():
            errors.append(f"输入字段名称 '{self.name}' 不是有效的标识符")
        return errors
    
    @classmethod
    def from_dict(cls, data: Union[str, Dict[str, Any]]) -> InputSpec:
        """从字典或字符串创建 InputSpec 实例"""
        if isinstance(data, str):
            return cls(name=data)
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "desc": self.desc,
            "required": self.required
        }


@dataclass
class OutputSpec:
    """Pipeline 输出字段规范"""
    key: str
    label: str = ""
    
    def validate(self) -> List[str]:
        """验证输出规范"""
        errors = []
        if not self.key:
            errors.append("输出字段键不能为空")
        if not self.key.isidentifier():
            errors.append(f"输出字段键 '{self.key}' 不是有效的标识符")
        return errors
    
    @classmethod
    def from_dict(cls, data: Union[str, Dict[str, Any]]) -> OutputSpec:
        """从字典或字符串创建 OutputSpec 实例"""
        if isinstance(data, str):
            return cls(key=data)
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "key": self.key,
            "label": self.label
        }


@dataclass
class StepConfig:
    """Pipeline 步骤配置"""
    id: str
    type: str = "agent_flow"  # 目前只支持 agent_flow，未来可扩展
    agent: str = ""
    flow: str = ""
    input_mapping: Dict[str, str] = field(default_factory=dict)
    output_key: str = ""
    model_override: Optional[str] = None
    description: str = ""
    
    def validate(self) -> List[str]:
        """验证步骤配置"""
        errors = []
        
        if not self.id:
            errors.append("步骤 ID 不能为空")
        elif not self.id.isidentifier():
            errors.append(f"步骤 ID '{self.id}' 不是有效的标识符")
            
        if self.type != "agent_flow":
            errors.append(f"不支持的步骤类型: {self.type}")
            
        if not self.agent:
            errors.append("Agent ID 不能为空")
            
        if not self.flow:
            errors.append("Flow 名称不能为空")
            
        if not self.output_key:
            errors.append("输出键不能为空")
        elif not self.output_key.isidentifier():
            errors.append(f"输出键 '{self.output_key}' 不是有效的标识符")
            
        # 验证 input_mapping 的值格式
        for param, source in self.input_mapping.items():
            if not param:
                errors.append("输入映射的键不能为空")
            if not source:
                errors.append(f"输入映射源 '{param}' 不能为空")
                
        return errors
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StepConfig:
        """从字典创建 StepConfig 实例"""
        return cls(**data)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "id": self.id,
            "type": self.type,
            "agent": self.agent,
            "flow": self.flow,
            "input_mapping": self.input_mapping,
            "output_key": self.output_key
        }
        if self.model_override:
            result["model_override"] = self.model_override
        if self.description:
            result["description"] = self.description
        return result


@dataclass
class BaselineStepConfig:
    """Baseline 步骤配置"""
    flow: str
    model: Optional[str] = None
    
    def validate(self) -> List[str]:
        """验证 baseline 步骤配置"""
        errors = []
        if not self.flow:
            errors.append("Baseline 步骤缺少 flow 配置")
        return errors


@dataclass
class BaselineConfig:
    """Baseline 配置"""
    name: str
    description: str = ""
    steps: Dict[str, BaselineStepConfig] = field(default_factory=dict)
    
    def validate(self, pipeline_steps: List[StepConfig]) -> List[str]:
        """验证 baseline 配置"""
        errors = []
        
        if not self.name:
            errors.append("Baseline 名称不能为空")
            
        # 验证 baseline 步骤引用的有效性
        pipeline_step_ids = {step.id for step in pipeline_steps}
        for step_id, step_config in self.steps.items():
            if step_id not in pipeline_step_ids:
                errors.append(f"Baseline 引用了不存在的步骤: {step_id}")
            else:
                errors.extend(step_config.validate())
                
        return errors


@dataclass
class VariantStepOverride:
    """变体步骤覆盖配置"""
    flow: Optional[str] = None
    model: Optional[str] = None
    
    def validate(self) -> List[str]:
        """验证变体步骤覆盖配置"""
        errors = []
        if not self.flow and not self.model:
            errors.append("变体步骤覆盖必须指定 flow 或 model 中的至少一个")
        return errors


@dataclass
class VariantConfig:
    """变体配置"""
    description: str = ""
    overrides: Dict[str, VariantStepOverride] = field(default_factory=dict)
    
    def validate(self, pipeline_steps: List[StepConfig]) -> List[str]:
        """验证变体配置"""
        errors = []
        
        # 验证变体覆盖引用的有效性
        pipeline_step_ids = {step.id for step in pipeline_steps}
        for step_id, override in self.overrides.items():
            if step_id not in pipeline_step_ids:
                errors.append(f"变体覆盖引用了不存在的步骤: {step_id}")
            else:
                errors.extend(override.validate())
                
        return errors


@dataclass
class PipelineConfig:
    """Pipeline 配置"""
    id: str
    name: str
    description: str = ""
    default_testset: str = ""
    inputs: List[InputSpec] = field(default_factory=list)
    steps: List[StepConfig] = field(default_factory=list)
    outputs: List[OutputSpec] = field(default_factory=list)
    baseline: Optional[BaselineConfig] = None
    variants: Dict[str, VariantConfig] = field(default_factory=dict)

    def __post_init__(self):
        """标准化配置字段，确保都为模型实例。"""
        self.inputs = [
            input_spec if isinstance(input_spec, InputSpec)
            else InputSpec.from_dict(input_spec)
            for input_spec in self.inputs
        ]

        self.outputs = [
            output_spec if isinstance(output_spec, OutputSpec)
            else OutputSpec.from_dict(output_spec)
            for output_spec in self.outputs
        ]

        self.steps = [
            step if isinstance(step, StepConfig)
            else StepConfig(**step)
            for step in self.steps
        ]

        self.variants = {
            name: variant if isinstance(variant, VariantConfig) else VariantConfig(**variant)
            for name, variant in self.variants.items()
        }
    
    def validate(self) -> List[str]:
        """验证 pipeline 配置"""
        errors = []
        
        # 基本字段验证
        if not self.id:
            errors.append("Pipeline ID 不能为空")
        elif not self.id.isidentifier():
            errors.append(f"Pipeline ID '{self.id}' 不是有效的标识符")
            
        if not self.name:
            errors.append("Pipeline 名称不能为空")
            
        if not self.steps:
            errors.append("Pipeline 必须包含至少一个步骤")
            
        # 验证输入规范
        for input_spec in self.inputs:
            errors.extend(input_spec.validate())
            
        # 验证步骤配置
        step_ids = set()
        for step in self.steps:
            if step.id in step_ids:
                errors.append(f"重复的步骤 ID: {step.id}")
            step_ids.add(step.id)
            errors.extend(step.validate())
            
        # 验证输出规范
        for output_spec in self.outputs:
            errors.extend(output_spec.validate())
            
        # 验证输出引用的步骤存在
        for output_spec in self.outputs:
            if output_spec.key not in {step.output_key for step in self.steps}:
                errors.append(f"输出 '{output_spec.key}' 引用了不存在的步骤输出")
                
        # 验证 baseline 配置
        if self.baseline:
            errors.extend(self.baseline.validate(self.steps))
            
        # 验证变体配置
        for variant_name, variant in self.variants.items():
            if not variant_name:
                errors.append("变体名称不能为空")
            else:
                errors.extend(variant.validate(self.steps))
                
        # 验证步骤间的依赖关系
        errors.extend(self._validate_step_dependencies())
        
        return errors
    
    def _validate_step_dependencies(self) -> List[str]:
        """验证步骤间的依赖关系，检测循环依赖"""
        errors = []
        
        # 构建依赖图
        dependencies = {}
        step_outputs = {}
        
        for step in self.steps:
            dependencies[step.id] = set()
            step_outputs[step.output_key] = step.id
            
        # 分析输入映射中的依赖关系
        for step in self.steps:
            for param, source in step.input_mapping.items():
                # 如果源是其他步骤的输出
                if source in step_outputs:
                    source_step = step_outputs[source]
                    if source_step != step.id:  # 不能依赖自己
                        dependencies[step.id].add(source_step)
                        
        # 检测循环依赖
        def has_cycle(node, visited, rec_stack):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in dependencies.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor, visited, rec_stack):
                        return True
                elif neighbor in rec_stack:
                    return True
                    
            rec_stack.remove(node)
            return False
            
        visited = set()
        for step_id in dependencies:
            if step_id not in visited:
                if has_cycle(step_id, visited, set()):
                    errors.append(f"检测到循环依赖，涉及步骤: {step_id}")
                    break
                    
        return errors
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> PipelineConfig:
        """从字典创建 PipelineConfig 实例"""
        # 处理 inputs
        inputs = []
        for input_data in data.get("inputs", []):
            if isinstance(input_data, dict):
                inputs.append(InputSpec(**input_data))
            else:
                inputs.append(InputSpec(name=str(input_data)))
                
        # 处理 steps
        steps = []
        for step_data in data.get("steps", []):
            steps.append(StepConfig(**step_data))
            
        # 处理 outputs
        outputs = []
        for output_data in data.get("outputs", []):
            if isinstance(output_data, dict):
                outputs.append(OutputSpec(**output_data))
            else:
                outputs.append(OutputSpec(key=str(output_data)))
                
        # 处理 baseline
        baseline = None
        if "baseline" in data:
            baseline_data = data["baseline"]
            baseline_steps = {}
            for step_id, step_config in baseline_data.get("steps", {}).items():
                baseline_steps[step_id] = BaselineStepConfig(**step_config)
            baseline = BaselineConfig(
                name=baseline_data.get("name", ""),
                description=baseline_data.get("description", ""),
                steps=baseline_steps
            )
            
        # 处理 variants
        variants = {}
        for variant_name, variant_data in data.get("variants", {}).items():
            variant_overrides = {}
            for step_id, override_data in variant_data.get("overrides", {}).items():
                variant_overrides[step_id] = VariantStepOverride(**override_data)
            variants[variant_name] = VariantConfig(
                description=variant_data.get("description", ""),
                overrides=variant_overrides
            )
            
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            default_testset=data.get("default_testset", ""),
            inputs=inputs,
            steps=steps,
            outputs=outputs,
            baseline=baseline,
            variants=variants
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "default_testset": self.default_testset,
            "inputs": [{"name": inp.name, "desc": inp.desc, "required": inp.required} for inp in self.inputs],
            "steps": [],
            "outputs": [{"key": out.key, "label": out.label} for out in self.outputs],
        }
        
        # 处理 steps
        for step in self.steps:
            step_dict = {
                "id": step.id,
                "type": step.type,
                "agent": step.agent,
                "flow": step.flow,
                "input_mapping": step.input_mapping,
                "output_key": step.output_key,
            }
            if step.model_override:
                step_dict["model_override"] = step.model_override
            if step.description:
                step_dict["description"] = step.description
            result["steps"].append(step_dict)
            
        # 处理 baseline
        if self.baseline:
            baseline_dict = {
                "name": self.baseline.name,
                "description": self.baseline.description,
                "steps": {}
            }
            for step_id, step_config in self.baseline.steps.items():
                step_dict = {"flow": step_config.flow}
                if step_config.model:
                    step_dict["model"] = step_config.model
                baseline_dict["steps"][step_id] = step_dict
            result["baseline"] = baseline_dict
            
        # 处理 variants
        if self.variants:
            variants_dict = {}
            for variant_name, variant in self.variants.items():
                variant_dict = {
                    "description": variant.description,
                    "overrides": {}
                }
                for step_id, override in variant.overrides.items():
                    override_dict = {}
                    if override.flow:
                        override_dict["flow"] = override.flow
                    if override.model:
                        override_dict["model"] = override.model
                    variant_dict["overrides"][step_id] = override_dict
                variants_dict[variant_name] = variant_dict
            result["variants"] = variants_dict
            
        return result


@dataclass
class EvaluationResult:
    """评估结果数据结构"""
    sample_id: str
    variant: str
    overall_score: float
    must_have_pass: bool
    rule_violations: List[str] = field(default_factory=list)
    judge_feedback: str = ""
    execution_time: float = 0.0
    step_outputs: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "sample_id": self.sample_id,
            "variant": self.variant,
            "overall_score": self.overall_score,
            "must_have_pass": self.must_have_pass,
            "rule_violations": self.rule_violations,
            "judge_feedback": self.judge_feedback,
            "execution_time": self.execution_time,
            "step_outputs": self.step_outputs,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EvaluationResult:
        """从字典创建 EvaluationResult 实例"""
        created_at = datetime.now()
        if "created_at" in data:
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass
                
        return cls(
            sample_id=data.get("sample_id", ""),
            variant=data.get("variant", ""),
            overall_score=float(data.get("overall_score", 0.0)),
            must_have_pass=bool(data.get("must_have_pass", False)),
            rule_violations=data.get("rule_violations", []),
            judge_feedback=data.get("judge_feedback", ""),
            execution_time=float(data.get("execution_time", 0.0)),
            step_outputs=data.get("step_outputs", {}),
            created_at=created_at
        )


@dataclass
class RegressionCase:
    """回归案例数据结构"""
    sample_id: str
    baseline_score: float
    variant_score: float
    score_delta: float
    severity: str  # "critical", "major", "minor"
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "sample_id": self.sample_id,
            "baseline_score": self.baseline_score,
            "variant_score": self.variant_score,
            "score_delta": self.score_delta,
            "severity": self.severity,
            "description": self.description
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RegressionCase:
        """从字典创建 RegressionCase 实例"""
        return cls(
            sample_id=data.get("sample_id", ""),
            baseline_score=float(data.get("baseline_score", 0.0)),
            variant_score=float(data.get("variant_score", 0.0)),
            score_delta=float(data.get("score_delta", 0.0)),
            severity=data.get("severity", "minor"),
            description=data.get("description", "")
        )


@dataclass
class ComparisonReport:
    """比较报告数据结构"""
    baseline_name: str
    variant_name: str
    sample_count: int
    score_delta: float
    must_have_delta: float
    rule_violation_delta: float
    tag_performance: Dict[str, float] = field(default_factory=dict)
    worst_regressions: List[RegressionCase] = field(default_factory=list)
    summary: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "baseline_name": self.baseline_name,
            "variant_name": self.variant_name,
            "sample_count": self.sample_count,
            "score_delta": self.score_delta,
            "must_have_delta": self.must_have_delta,
            "rule_violation_delta": self.rule_violation_delta,
            "tag_performance": self.tag_performance,
            "worst_regressions": [case.to_dict() for case in self.worst_regressions],
            "summary": self.summary,
            "created_at": self.created_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ComparisonReport:
        """从字典创建 ComparisonReport 实例"""
        created_at = datetime.now()
        if "created_at" in data:
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass
                
        worst_regressions = []
        for case_data in data.get("worst_regressions", []):
            worst_regressions.append(RegressionCase.from_dict(case_data))
            
        return cls(
            baseline_name=data.get("baseline_name", ""),
            variant_name=data.get("variant_name", ""),
            sample_count=int(data.get("sample_count", 0)),
            score_delta=float(data.get("score_delta", 0.0)),
            must_have_delta=float(data.get("must_have_delta", 0.0)),
            rule_violation_delta=float(data.get("rule_violation_delta", 0.0)),
            tag_performance=data.get("tag_performance", {}),
            worst_regressions=worst_regressions,
            summary=data.get("summary", ""),
            created_at=created_at
        )