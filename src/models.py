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
class OutputParserConfig:
    """Output Parser 配置"""
    type: str  # "json" | "pydantic" | "list" | "none"
    schema: Optional[Dict[str, Any]] = None  # JSON schema
    pydantic_model: Optional[str] = None  # Pydantic 模型类名
    retry_on_error: bool = True
    max_retries: int = 3
    fix_prompt: Optional[str] = None  # 修复提示词
    
    def validate(self) -> List[str]:
        """验证配置有效性"""
        errors = []
        
        # 验证 type 字段
        valid_types = ["json", "pydantic", "list", "none"]
        if not self.type:
            errors.append("Output parser type 不能为空")
        elif self.type not in valid_types:
            errors.append(f"不支持的 output parser 类型: {self.type}，支持的类型: {', '.join(valid_types)}")
        
        # 验证 JSON parser 配置
        if self.type == "json":
            if self.schema is not None and not isinstance(self.schema, dict):
                errors.append("JSON schema 必须是字典类型")
        
        # 验证 Pydantic parser 配置
        if self.type == "pydantic":
            if not self.pydantic_model:
                errors.append("Pydantic parser 必须指定 pydantic_model")
        
        # 验证重试配置
        if self.max_retries < 0:
            errors.append("max_retries 必须是非负整数")
        
        return errors
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OutputParserConfig':
        """从字典创建 OutputParserConfig 实例"""
        return cls(
            type=data.get("type", "none"),
            schema=data.get("schema"),
            pydantic_model=data.get("pydantic_model"),
            retry_on_error=data.get("retry_on_error", True),
            max_retries=data.get("max_retries", 3),
            fix_prompt=data.get("fix_prompt")
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {"type": self.type}
        
        if self.schema is not None:
            result["schema"] = self.schema
        if self.pydantic_model is not None:
            result["pydantic_model"] = self.pydantic_model
        if not self.retry_on_error:
            result["retry_on_error"] = self.retry_on_error
        if self.max_retries != 3:
            result["max_retries"] = self.max_retries
        if self.fix_prompt is not None:
            result["fix_prompt"] = self.fix_prompt
        
        return result
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'OutputParserConfig':
        """从 JSON 字符串创建 OutputParserConfig 实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


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
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'InputSpec':
        """从 JSON 字符串创建 InputSpec 实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


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
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'OutputSpec':
        """从 JSON 字符串创建 OutputSpec 实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class CodeNodeConfig:
    """代码节点配置"""
    language: str  # "javascript" or "python"
    code: Optional[str] = None  # 内联代码
    code_file: Optional[str] = None  # 外部文件路径
    timeout: int = 30
    env_vars: Dict[str, str] = field(default_factory=dict)
    
    def validate(self) -> List[str]:
        """验证代码节点配置"""
        errors = []
        
        # 验证 language 字段
        valid_languages = ["javascript", "python"]
        if not self.language:
            errors.append("代码节点的 language 字段不能为空")
        elif self.language not in valid_languages:
            errors.append(
                f"不支持的代码语言: {self.language}，"
                f"支持的语言: {', '.join(valid_languages)}"
            )
        
        # 验证必须指定 code 或 code_file 之一
        if not self.code and not self.code_file:
            errors.append("代码节点必须指定 code（内联代码）或 code_file（外部文件）之一")
        
        # 验证不能同时指定 code 和 code_file
        if self.code and self.code_file:
            errors.append("代码节点不能同时指定 code 和 code_file，请只使用其中一个")
        
        # 验证 timeout
        if self.timeout <= 0:
            errors.append("代码节点的 timeout 必须是正整数")
        
        return errors
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CodeNodeConfig':
        """从字典创建 CodeNodeConfig 实例"""
        return cls(
            language=data.get("language", ""),
            code=data.get("code"),
            code_file=data.get("code_file"),
            timeout=data.get("timeout", 30),
            env_vars=data.get("env_vars", {})
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "language": self.language,
            "timeout": self.timeout
        }
        if self.code is not None:
            result["code"] = self.code
        if self.code_file is not None:
            result["code_file"] = self.code_file
        if self.env_vars:
            result["env_vars"] = self.env_vars
        return result
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'CodeNodeConfig':
        """从 JSON 字符串创建 CodeNodeConfig 实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class StepConfig:
    """Pipeline 步骤配置（增强版，支持代码节点）"""
    id: str
    type: str = "agent_flow"  # "agent_flow", "code_node", "batch_aggregator"
    
    # Agent Flow 字段
    agent: str = ""
    flow: str = ""
    
    # Code Node 字段
    code_config: Optional[CodeNodeConfig] = None
    language: Optional[str] = None  # 向后兼容：直接在 step 中指定 language
    code: Optional[str] = None  # 向后兼容：直接在 step 中指定 code
    code_file: Optional[str] = None  # 向后兼容：直接在 step 中指定 code_file
    
    # 批量处理字段
    batch_mode: bool = False
    batch_size: int = 10
    concurrent: bool = True  # 批量处理时是否并发执行
    max_workers: int = 4  # 最大并发工作线程数
    
    # 聚合字段
    aggregation_strategy: Optional[str] = None  # "concat", "stats", "filter", "group", "summary", "custom"
    aggregation_code: Optional[str] = None
    separator: Optional[str] = None  # concat 策略的分隔符
    fields: Optional[List[str]] = None  # stats 策略的字段列表
    condition: Optional[str] = None  # filter 策略的条件表达式
    group_by: Optional[str] = None  # group 策略的分组字段
    summary_fields: Optional[List[str]] = None  # summary 策略的汇总字段
    
    # 并发控制
    concurrent_group: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    
    # 通用字段
    input_mapping: Dict[str, str] = field(default_factory=dict)
    output_key: str = ""
    model_override: Optional[str] = None
    description: str = ""
    required: bool = True  # 步骤是否必需（如果为False，失败时继续执行）
    timeout: Optional[int] = None
    
    def get_dependencies(self) -> List[str]:
        """
        获取此步骤依赖的其他步骤的output_key
        
        Returns:
            依赖的output_key列表
        """
        return list(self.input_mapping.values())
    
    def validate(self) -> List[str]:
        """验证步骤配置"""
        errors = []
        
        # 基本字段验证
        if not self.id:
            errors.append("步骤 ID 不能为空")
        elif not self.id.isidentifier():
            errors.append(f"步骤 ID '{self.id}' 不是有效的标识符")
        
        # 验证步骤类型
        valid_types = ["agent_flow", "code_node", "batch_aggregator"]
        if not self.type:
            errors.append("步骤类型不能为空")
        elif self.type not in valid_types:
            errors.append(
                f"不支持的步骤类型: {self.type}，"
                f"支持的类型: {', '.join(valid_types)}"
            )
        
        # 根据类型验证特定字段
        if self.type == "agent_flow":
            if not self.agent:
                errors.append("Agent Flow 步骤的 agent 字段不能为空")
            if not self.flow:
                errors.append("Agent Flow 步骤的 flow 字段不能为空")
        
        elif self.type == "code_node":
            # 验证代码节点配置
            if self.code_config:
                errors.extend(self.code_config.validate())
            else:
                # 向后兼容：检查直接在 step 中指定的字段
                if not self.language:
                    errors.append("代码节点必须指定 language 字段")
                elif self.language not in ["javascript", "python"]:
                    errors.append(
                        f"不支持的代码语言: {self.language}，"
                        f"支持的语言: javascript, python"
                    )
                
                if not self.code and not self.code_file:
                    errors.append("代码节点必须指定 code（内联代码）或 code_file（外部文件）之一")
                
                if self.code and self.code_file:
                    errors.append("代码节点不能同时指定 code 和 code_file")
        
        elif self.type == "batch_aggregator":
            # 验证批量聚合配置
            if not self.aggregation_strategy:
                errors.append("批量聚合步骤必须指定 aggregation_strategy")
            elif self.aggregation_strategy not in ["concat", "stats", "filter", "group", "summary", "custom"]:
                errors.append(
                    f"不支持的聚合策略: {self.aggregation_strategy}，"
                    f"支持的策略: concat, stats, filter, group, summary, custom"
                )
            
            # 验证策略特定字段
            if self.aggregation_strategy == "custom":
                # Accept either 'code', 'aggregation_code', or 'code_file'
                has_code = self.code or self.aggregation_code or self.code_file
                if not has_code:
                    errors.append("自定义聚合策略必须指定 code, aggregation_code 或 code_file")
                if not self.language:
                    errors.append("自定义聚合策略必须指定 language (python 或 javascript)")
            
            if self.aggregation_strategy == "stats" and not self.fields:
                errors.append("stats 聚合策略必须指定 fields 字段列表")
            
            if self.aggregation_strategy == "filter" and not self.condition:
                errors.append("filter 聚合策略必须指定 condition 过滤条件")
            
            if self.aggregation_strategy == "group" and not self.group_by:
                errors.append("group 聚合策略必须指定 group_by 分组字段")
            
            if self.aggregation_strategy == "summary" and not self.summary_fields:
                errors.append("summary 聚合策略必须指定 summary_fields 汇总字段列表")
        
        # 验证批量处理配置
        if self.batch_mode:
            if self.batch_size <= 0:
                errors.append("batch_size 必须是正整数")
            if self.max_workers <= 0:
                errors.append("max_workers 必须是正整数")
        
        # 验证输出键
        if not self.output_key:
            errors.append("输出键不能为空")
        elif not self.output_key.isidentifier():
            errors.append(f"输出键 '{self.output_key}' 不是有效的标识符")
        
        # 验证 input_mapping
        for param, source in self.input_mapping.items():
            if not param:
                errors.append("输入映射的键不能为空")
            if not source:
                errors.append(f"输入映射源 '{param}' 不能为空")
        
        # 验证 timeout
        if self.timeout is not None and self.timeout <= 0:
            errors.append("timeout 必须是正整数")
        
        return errors
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> StepConfig:
        """从字典创建 StepConfig 实例"""
        # 处理 code_config
        code_config = None
        if "code_config" in data and data["code_config"]:
            if isinstance(data["code_config"], dict):
                code_config = CodeNodeConfig.from_dict(data["code_config"])
            elif isinstance(data["code_config"], CodeNodeConfig):
                code_config = data["code_config"]
        
        # 创建 StepConfig 实例
        step_data = data.copy()
        if "code_config" in step_data:
            step_data["code_config"] = code_config
        
        return cls(**step_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            "id": self.id,
            "type": self.type,
            "input_mapping": self.input_mapping,
            "output_key": self.output_key,
        }
        
        # Agent Flow 字段
        if self.agent:
            result["agent"] = self.agent
        if self.flow:
            result["flow"] = self.flow
        if self.model_override:
            result["model_override"] = self.model_override
        
        # Code Node 字段
        if self.code_config:
            result["code_config"] = self.code_config.to_dict()
        elif self.type == "code_node":
            # 向后兼容：直接在 step 中的字段
            if self.language:
                result["language"] = self.language
            if self.code:
                result["code"] = self.code
            if self.code_file:
                result["code_file"] = self.code_file
        
        # 批量处理字段
        if self.batch_mode:
            result["batch_mode"] = self.batch_mode
            result["batch_size"] = self.batch_size
            if not self.concurrent:
                result["concurrent"] = self.concurrent
            if self.max_workers != 4:
                result["max_workers"] = self.max_workers
        
        # 聚合字段
        if self.aggregation_strategy:
            result["aggregation_strategy"] = self.aggregation_strategy
        if self.aggregation_code:
            result["aggregation_code"] = self.aggregation_code
        if self.separator is not None:
            result["separator"] = self.separator
        if self.fields:
            result["fields"] = self.fields
        if self.condition:
            result["condition"] = self.condition
        if self.group_by:
            result["group_by"] = self.group_by
        if self.summary_fields:
            result["summary_fields"] = self.summary_fields
        
        # 并发控制
        if self.concurrent_group:
            result["concurrent_group"] = self.concurrent_group
        if self.depends_on:
            result["depends_on"] = self.depends_on
        
        # 其他字段
        if self.description:
            result["description"] = self.description
        if not self.required:
            result["required"] = self.required
        if self.timeout is not None:
            result["timeout"] = self.timeout
        
        return result
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'StepConfig':
        """从 JSON 字符串创建 StepConfig 实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


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
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {"flow": self.flow}
        if self.model:
            result["model"] = self.model
        return result
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaselineStepConfig':
        """从字典创建 BaselineStepConfig 实例"""
        return cls(
            flow=data.get("flow", ""),
            model=data.get("model")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BaselineStepConfig':
        """从 JSON 字符串创建 BaselineStepConfig 实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


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
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "description": self.description,
            "steps": {step_id: step.to_dict() for step_id, step in self.steps.items()}
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaselineConfig':
        """从字典创建 BaselineConfig 实例"""
        steps = {}
        for step_id, step_data in data.get("steps", {}).items():
            steps[step_id] = BaselineStepConfig.from_dict(step_data)
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            steps=steps
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BaselineConfig':
        """从 JSON 字符串创建 BaselineConfig 实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


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
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {}
        if self.flow:
            result["flow"] = self.flow
        if self.model:
            result["model"] = self.model
        return result
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VariantStepOverride':
        """从字典创建 VariantStepOverride 实例"""
        return cls(
            flow=data.get("flow"),
            model=data.get("model")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'VariantStepOverride':
        """从 JSON 字符串创建 VariantStepOverride 实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


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
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "description": self.description,
            "overrides": {step_id: override.to_dict() for step_id, override in self.overrides.items()}
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VariantConfig':
        """从字典创建 VariantConfig 实例"""
        overrides = {}
        for step_id, override_data in data.get("overrides", {}).items():
            overrides[step_id] = VariantStepOverride.from_dict(override_data)
        return cls(
            description=data.get("description", ""),
            overrides=overrides
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'VariantConfig':
        """从 JSON 字符串创建 VariantConfig 实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


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
    evaluation_target: Optional[str] = None  # 新增：指定评估目标步骤（默认为最后一步）

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
        
        # 验证 evaluation_target 引用的步骤存在
        if self.evaluation_target:
            if self.evaluation_target not in step_ids:
                errors.append(f"evaluation_target '{self.evaluation_target}' 引用了不存在的步骤")
                
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
            steps.append(StepConfig.from_dict(step_data))
            
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
            variants=variants,
            evaluation_target=data.get("evaluation_target")
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
        
        # 添加 evaluation_target（如果指定）
        if self.evaluation_target:
            result["evaluation_target"] = self.evaluation_target
        
        # 处理 steps
        for step in self.steps:
            result["steps"].append(step.to_dict())
            
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
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'PipelineConfig':
        """从 JSON 字符串创建 PipelineConfig 实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class RuleConfig:
    """规则配置"""
    name: str
    type: str  # "contains", "not_contains", "regex", "length", etc.
    params: Dict[str, Any] = field(default_factory=dict)
    severity: str = "error"  # "error" | "warning"
    message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "name": self.name,
            "type": self.type,
            "params": self.params,
            "severity": self.severity,
            "message": self.message
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RuleConfig':
        """从字典创建 RuleConfig 实例"""
        return cls(
            name=data.get("name", ""),
            type=data.get("type", ""),
            params=data.get("params", {}),
            severity=data.get("severity", "error"),
            message=data.get("message", "")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'RuleConfig':
        """从 JSON 字符串创建 RuleConfig 实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class CaseFieldConfig:
    """测试用例字段配置"""
    key: str
    label: str = ""
    section: str = "context"  # "primary_input" | "context" | "meta" | "raw"
    truncate: Optional[int] = None
    as_json: bool = False
    required: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "key": self.key,
            "label": self.label,
            "section": self.section,
            "truncate": self.truncate,
            "as_json": self.as_json,
            "required": self.required
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CaseFieldConfig':
        """从字典创建 CaseFieldConfig 实例"""
        return cls(
            key=data.get("key", ""),
            label=data.get("label", ""),
            section=data.get("section", "context"),
            truncate=data.get("truncate"),
            as_json=data.get("as_json", False),
            required=data.get("required", False)
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'CaseFieldConfig':
        """从 JSON 字符串创建 CaseFieldConfig 实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class EvaluationConfig:
    """统一的评估配置，适用于 Agent 和 Pipeline"""
    
    # 规则评估
    rules: List[RuleConfig] = field(default_factory=list)
    
    # Judge 评估
    judge_enabled: bool = False
    judge_agent_id: Optional[str] = None
    judge_flow: Optional[str] = None
    judge_model: Optional[str] = None
    
    # 评分范围
    scale_min: int = 0
    scale_max: int = 10
    
    # 字段配置
    case_fields: List[CaseFieldConfig] = field(default_factory=list)
    
    # 其他配置
    temperature: float = 0.0
    preferred_judge_model: Optional[str] = None
    
    @classmethod
    def from_agent_config(cls, agent_config: 'AgentConfig') -> 'EvaluationConfig':
        """从 Agent 配置创建评估配置"""
        eval_cfg = agent_config.evaluation or {}
        
        # 解析规则配置
        rules = []
        for rule_data in eval_cfg.get("rules", []):
            if isinstance(rule_data, dict):
                rules.append(RuleConfig.from_dict(rule_data))
        
        # 解析字段配置
        case_fields = []
        for field_data in eval_cfg.get("case_fields", []):
            if isinstance(field_data, dict):
                case_fields.append(CaseFieldConfig.from_dict(field_data))
        
        # 获取评分范围
        scale = eval_cfg.get("scale", {}) or {}
        scale_min = scale.get("min", 0)
        scale_max = scale.get("max", 10)
        
        # 判断是否启用 Judge
        judge_enabled = eval_cfg.get("judge_agent_id") is not None or eval_cfg.get("judge_flow") is not None
        
        return cls(
            rules=rules,
            judge_enabled=judge_enabled,
            judge_agent_id=eval_cfg.get("judge_agent_id"),
            judge_flow=eval_cfg.get("judge_flow"),
            judge_model=eval_cfg.get("judge_model"),
            scale_min=scale_min,
            scale_max=scale_max,
            case_fields=case_fields,
            temperature=eval_cfg.get("temperature", 0.0),
            preferred_judge_model=eval_cfg.get("preferred_judge_model")
        )
    
    @classmethod
    def from_pipeline_config(cls, pipeline_config: 'PipelineConfig') -> 'EvaluationConfig':
        """从 Pipeline 配置创建评估配置"""
        # Pipeline 的评估配置通常基于最后一个步骤的 agent
        # 如果 Pipeline 配置中有评估配置，优先使用
        # 否则使用最后一个步骤的 agent 配置
        
        # 注意：这里需要导入 agent_registry，但为了避免循环导入，
        # 我们在方法内部导入
        from .agent_registry import load_agent
        
        # 尝试从最后一个步骤获取 agent 配置
        if pipeline_config.steps:
            final_step = pipeline_config.steps[-1]
            try:
                final_agent = load_agent(final_step.agent)
                return cls.from_agent_config(final_agent)
            except Exception:
                # 如果加载失败，返回默认配置
                pass
        
        # 返回默认配置
        return cls(
            rules=[],
            judge_enabled=False,
            scale_min=0,
            scale_max=10,
            case_fields=[]
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "rules": [rule.to_dict() for rule in self.rules],
            "judge_enabled": self.judge_enabled,
            "judge_agent_id": self.judge_agent_id,
            "judge_flow": self.judge_flow,
            "judge_model": self.judge_model,
            "scale_min": self.scale_min,
            "scale_max": self.scale_max,
            "case_fields": [field.to_dict() for field in self.case_fields],
            "temperature": self.temperature,
            "preferred_judge_model": self.preferred_judge_model
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EvaluationConfig':
        """从字典创建 EvaluationConfig 实例"""
        rules = [RuleConfig.from_dict(rule_data) for rule_data in data.get("rules", [])]
        case_fields = [CaseFieldConfig.from_dict(field_data) for field_data in data.get("case_fields", [])]
        return cls(
            rules=rules,
            judge_enabled=data.get("judge_enabled", False),
            judge_agent_id=data.get("judge_agent_id"),
            judge_flow=data.get("judge_flow"),
            judge_model=data.get("judge_model"),
            scale_min=data.get("scale_min", 0),
            scale_max=data.get("scale_max", 10),
            case_fields=case_fields,
            temperature=data.get("temperature", 0.0),
            preferred_judge_model=data.get("preferred_judge_model")
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> 'EvaluationConfig':
        """从 JSON 字符串创建 EvaluationConfig 实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class EvaluationResult:
    """评估结果数据结构"""
    sample_id: str
    entity_type: str  # "agent" | "pipeline"
    entity_id: str  # agent_id 或 pipeline_id
    variant: str
    overall_score: float
    must_have_pass: bool
    rule_violations: List[str] = field(default_factory=list)
    judge_feedback: str = ""
    execution_time: float = 0.0
    step_outputs: Dict[str, Any] = field(default_factory=dict)
    failed_steps: List[str] = field(default_factory=list)  # 新增：失败步骤的ID列表
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "sample_id": self.sample_id,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "variant": self.variant,
            "overall_score": self.overall_score,
            "must_have_pass": self.must_have_pass,
            "rule_violations": self.rule_violations,
            "judge_feedback": self.judge_feedback,
            "execution_time": self.execution_time,
            "step_outputs": self.step_outputs,
            "failed_steps": self.failed_steps,
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
            entity_type=data.get("entity_type", "agent"),  # 默认为 agent 以保持向后兼容
            entity_id=data.get("entity_id", ""),
            variant=data.get("variant", ""),
            overall_score=float(data.get("overall_score", 0.0)),
            must_have_pass=bool(data.get("must_have_pass", False)),
            rule_violations=data.get("rule_violations", []),
            judge_feedback=data.get("judge_feedback", ""),
            execution_time=float(data.get("execution_time", 0.0)),
            step_outputs=data.get("step_outputs", {}),
            failed_steps=data.get("failed_steps", []),
            created_at=created_at
        )
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'EvaluationResult':
        """从 JSON 字符串创建 EvaluationResult 实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


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
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'RegressionCase':
        """从 JSON 字符串创建 RegressionCase 实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


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
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ComparisonReport':
        """从 JSON 字符串创建 ComparisonReport 实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)