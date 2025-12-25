# src/pipeline_config.py
"""
Pipeline YAML 配置解析器

处理 pipeline YAML 文件的加载、验证和管理，
包括 schema 验证、引用完整性检查和循环依赖检测。
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
import logging

from .models import PipelineConfig
from .agent_registry import load_agent, list_available_agents, AgentConfig
from .error_handler import create_config_error, create_data_error, handle_error

logger = logging.getLogger(__name__)

# 获取项目根目录
ROOT_DIR = Path(__file__).resolve().parent.parent

# Pipeline 目录列表（按优先级排序）
PIPELINE_DIRS = [
    ROOT_DIR / "pipelines",           # 生产 Pipeline（优先级最高）
    ROOT_DIR / "examples" / "pipelines",  # 示例 Pipeline
]

# 向后兼容
PIPELINES_DIR = PIPELINE_DIRS[0]


class PipelineConfigError(Exception):
    """Pipeline 配置错误（向后兼容）"""
    pass


class PipelineValidator:
    """Pipeline 配置验证器"""
    
    def __init__(self):
        self.available_agents: Set[str] = set()
        self.agent_flows: Dict[str, Set[str]] = {}
        self._load_agent_info()
    
    def detect_circular_dependencies(self, config: PipelineConfig) -> List[str]:
        """
        检测 Pipeline 步骤间的循环依赖
        
        Args:
            config: Pipeline 配置
        
        Returns:
            错误列表，包含循环依赖的详细信息
        """
        errors = []
        
        # 构建依赖图
        dependencies: Dict[str, Set[str]] = {}
        step_outputs: Dict[str, str] = {}
        
        for step in config.steps:
            dependencies[step.id] = set()
            step_outputs[step.output_key] = step.id
        
        # 分析输入映射中的依赖关系
        for step in config.steps:
            for param, source in step.input_mapping.items():
                # 如果源是其他步骤的输出
                if source in step_outputs:
                    source_step = step_outputs[source]
                    if source_step != step.id:  # 不能依赖自己
                        dependencies[step.id].add(source_step)
                    else:
                        errors.append(
                            f"步骤 '{step.id}' 不能依赖自己的输出\n"
                            f"  问题: input_mapping['{param}'] = '{source}'\n"
                            f"  修复建议: 请移除此自引用，或使用其他步骤的输出"
                        )
        
        # 检测循环依赖
        def find_cycle_path(node: str, visited: Set[str], rec_stack: List[str]) -> Optional[List[str]]:
            """查找循环依赖路径"""
            visited.add(node)
            rec_stack.append(node)
            
            for neighbor in dependencies.get(node, set()):
                if neighbor not in visited:
                    cycle = find_cycle_path(neighbor, visited, rec_stack)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # 找到循环，返回循环路径
                    cycle_start = rec_stack.index(neighbor)
                    return rec_stack[cycle_start:] + [neighbor]
            
            rec_stack.pop()
            return None
        
        visited: Set[str] = set()
        for step_id in dependencies:
            if step_id not in visited:
                cycle_path = find_cycle_path(step_id, visited, [])
                if cycle_path:
                    cycle_str = " -> ".join(cycle_path)
                    errors.append(
                        f"检测到循环依赖:\n"
                        f"  循环路径: {cycle_str}\n"
                        f"  修复建议: 请重新设计步骤间的数据流，打破循环依赖"
                    )
                    break  # 只报告第一个循环
        
        return errors
    
    def _load_agent_info(self):
        """加载可用的 agent 和 flow 信息"""
        try:
            self.available_agents = set(list_available_agents())
            
            for agent_id in self.available_agents:
                try:
                    agent = load_agent(agent_id)
                    self.agent_flows[agent_id] = {flow.name for flow in agent.flows}
                except Exception as e:
                    logger.warning(f"无法加载 agent {agent_id} 的配置: {e}")
                    self.agent_flows[agent_id] = set()
                    
        except Exception as e:
            logger.warning(f"加载 agent 信息时出错: {e}")
            self.available_agents = set()
            self.agent_flows = {}
    
    def validate_references(self, config: PipelineConfig) -> List[str]:
        """验证配置中的引用完整性，提供详细的错误信息和修复建议"""
        errors = []
        
        # 首先检测循环依赖
        cycle_errors = self.detect_circular_dependencies(config)
        errors.extend(cycle_errors)
        
        # 验证步骤中的 agent 和 flow 引用
        for step in config.steps:
            # 只验证 agent_flow 类型的步骤
            if step.type == "agent_flow":
                # 检查 agent 是否存在
                if step.agent not in self.available_agents:
                    available_list = ", ".join(sorted(self.available_agents)) if self.available_agents else "无"
                    errors.append(
                        f"步骤 '{step.id}' 引用了不存在的 agent: {step.agent}\n"
                        f"  可用的 agents: {available_list}\n"
                        f"  修复建议: 请检查 agent ID 的拼写，或创建新的 agent"
                    )
                    continue
                    
                # 检查 flow 是否存在
                agent_flows = self.agent_flows.get(step.agent, set())
                if step.flow not in agent_flows:
                    available_flows = ", ".join(sorted(agent_flows)) if agent_flows else "无"
                    errors.append(
                        f"步骤 '{step.id}' 引用了 agent '{step.agent}' 中不存在的 flow: {step.flow}\n"
                        f"  可用的 flows: {available_flows}\n"
                        f"  修复建议: 请检查 flow 名称的拼写，或在 agent '{step.agent}' 中创建新的 flow"
                    )
            
            elif step.type == "code_node":
                # 验证代码节点的文件引用（如果使用外部文件）
                code_file = None
                if step.code_config and step.code_config.code_file:
                    code_file = step.code_config.code_file
                elif step.code_file:
                    code_file = step.code_file
                
                if code_file:
                    # 检查文件是否存在
                    code_file_path = Path(code_file)
                    if not code_file_path.is_absolute():
                        code_file_path = ROOT_DIR / code_file
                    
                    if not code_file_path.exists():
                        errors.append(
                            f"步骤 '{step.id}' 引用的代码文件不存在: {code_file}\n"
                            f"  查找路径: {code_file_path}\n"
                            f"  修复建议: 请创建代码文件，或更新 code_file 字段"
                        )
        
        # 验证 baseline 中的 flow 引用
        if config.baseline:
            for step_id, baseline_step in config.baseline.steps.items():
                # 找到对应的 pipeline 步骤
                pipeline_step = None
                for step in config.steps:
                    if step.id == step_id:
                        pipeline_step = step
                        break
                
                if not pipeline_step:
                    step_ids = ", ".join([s.id for s in config.steps])
                    errors.append(
                        f"Baseline 引用了不存在的步骤: {step_id}\n"
                        f"  可用的步骤 IDs: {step_ids}\n"
                        f"  修复建议: 请检查步骤 ID 的拼写，或从 baseline 中移除此步骤"
                    )
                elif pipeline_step:
                    agent_flows = self.agent_flows.get(pipeline_step.agent, set())
                    if baseline_step.flow not in agent_flows:
                        available_flows = ", ".join(sorted(agent_flows)) if agent_flows else "无"
                        errors.append(
                            f"Baseline 步骤 '{step_id}' 引用了 agent '{pipeline_step.agent}' 中不存在的 flow: {baseline_step.flow}\n"
                            f"  可用的 flows: {available_flows}\n"
                            f"  修复建议: 请检查 flow 名称的拼写，或在 agent '{pipeline_step.agent}' 中创建新的 flow"
                        )
        
        # 验证变体中的 flow 引用
        for variant_name, variant in config.variants.items():
            for step_id, override in variant.overrides.items():
                # 找到对应的 pipeline 步骤
                pipeline_step = None
                for step in config.steps:
                    if step.id == step_id:
                        pipeline_step = step
                        break
                
                if not pipeline_step:
                    step_ids = ", ".join([s.id for s in config.steps])
                    errors.append(
                        f"变体 '{variant_name}' 引用了不存在的步骤: {step_id}\n"
                        f"  可用的步骤 IDs: {step_ids}\n"
                        f"  修复建议: 请检查步骤 ID 的拼写，或从变体中移除此覆盖"
                    )
                elif override.flow:
                    agent_flows = self.agent_flows.get(pipeline_step.agent, set())
                    if override.flow not in agent_flows:
                        available_flows = ", ".join(sorted(agent_flows)) if agent_flows else "无"
                        errors.append(
                            f"变体 '{variant_name}' 步骤 '{step_id}' 引用了 agent '{pipeline_step.agent}' 中不存在的 flow: {override.flow}\n"
                            f"  可用的 flows: {available_flows}\n"
                            f"  修复建议: 请检查 flow 名称的拼写，或在 agent '{pipeline_step.agent}' 中创建新的 flow"
                        )
        
        # 验证 testset 文件是否存在
        if config.default_testset:
            testset_path = self._resolve_testset_path(config.id, config.default_testset)
            if not testset_path.exists():
                # 尝试查找可能的测试集文件
                testset_dir = ROOT_DIR / "data" / "pipelines" / config.id / "testsets"
                available_testsets = []
                if testset_dir.exists():
                    available_testsets = [f.name for f in testset_dir.glob("*.jsonl")]
                
                available_list = ", ".join(available_testsets) if available_testsets else "无"
                errors.append(
                    f"默认测试集文件不存在: {config.default_testset}\n"
                    f"  查找路径: {testset_path}\n"
                    f"  可用的测试集: {available_list}\n"
                    f"  修复建议: 请创建测试集文件，或更新 default_testset 字段"
                )
        
        return errors
    
    def _resolve_testset_path(self, pipeline_id: str, testset_file: str) -> Path:
        """解析测试集文件路径"""
        # 如果是绝对路径，直接使用
        if Path(testset_file).is_absolute():
            return Path(testset_file)
        
        # 相对路径，优先在 pipeline 目录下查找
        pipeline_testset_path = ROOT_DIR / "data" / "pipelines" / pipeline_id / "testsets" / testset_file
        if pipeline_testset_path.exists():
            return pipeline_testset_path
        
        # 兼容旧的 data/testsets 目录
        old_testset_path = ROOT_DIR / "data" / "testsets" / testset_file
        if old_testset_path.exists():
            return old_testset_path
        
        # 相对于项目根目录
        return ROOT_DIR / testset_file


def validate_code_node_config(step_data: Dict[str, Any], step_index: int) -> List[str]:
    """
    验证代码节点配置的有效性
    
    Args:
        step_data: 步骤配置字典
        step_index: 步骤索引（用于错误信息）
    
    Returns:
        错误列表
    """
    errors = []
    step_id = step_data.get("id", f"步骤 {step_index}")
    
    # 检查是否有 code_config
    if "code_config" in step_data:
        code_config = step_data["code_config"]
        if not isinstance(code_config, dict):
            errors.append(f"{step_id}: code_config 必须是字典类型")
            return errors
        
        # 验证 language
        if "language" not in code_config:
            errors.append(f"{step_id}: code_config 缺少 'language' 字段")
        elif code_config["language"] not in ["javascript", "python"]:
            errors.append(
                f"{step_id}: 不支持的代码语言 '{code_config['language']}'。"
                f"支持的语言: javascript, python"
            )
        
        # 验证必须有 code 或 code_file
        has_code = "code" in code_config and code_config["code"]
        has_code_file = "code_file" in code_config and code_config["code_file"]
        
        if not has_code and not has_code_file:
            errors.append(f"{step_id}: code_config 必须指定 'code'（内联代码）或 'code_file'（外部文件）之一")
        
        if has_code and has_code_file:
            errors.append(f"{step_id}: code_config 不能同时指定 'code' 和 'code_file'")
        
        # 验证 timeout
        if "timeout" in code_config:
            timeout = code_config["timeout"]
            if not isinstance(timeout, int):
                errors.append(f"{step_id}: timeout 必须是整数")
            elif timeout <= 0:
                errors.append(f"{step_id}: timeout 必须是正整数")
        
        # 验证 env_vars
        if "env_vars" in code_config:
            env_vars = code_config["env_vars"]
            if not isinstance(env_vars, dict):
                errors.append(f"{step_id}: env_vars 必须是字典类型")
    
    else:
        # 向后兼容：检查直接在 step 中的字段
        if "language" not in step_data:
            errors.append(f"{step_id}: 代码节点必须指定 'language' 字段")
        elif step_data["language"] not in ["javascript", "python"]:
            errors.append(
                f"{step_id}: 不支持的代码语言 '{step_data['language']}'。"
                f"支持的语言: javascript, python"
            )
        
        has_code = "code" in step_data and step_data["code"]
        has_code_file = "code_file" in step_data and step_data["code_file"]
        
        if not has_code and not has_code_file:
            errors.append(f"{step_id}: 代码节点必须指定 'code'（内联代码）或 'code_file'（外部文件）之一")
        
        if has_code and has_code_file:
            errors.append(f"{step_id}: 代码节点不能同时指定 'code' 和 'code_file'")
    
    return errors


def validate_yaml_schema(data: Dict[str, Any]) -> List[str]:
    """验证 YAML 数据的基本 schema"""
    errors = []
    
    # 必需字段检查
    required_fields = ["id", "name", "steps"]
    for field in required_fields:
        if field not in data:
            errors.append(f"缺少必需字段: {field}")
        elif not data[field]:
            errors.append(f"必需字段不能为空: {field}")
    
    # 字段类型检查
    if "id" in data and not isinstance(data["id"], str):
        errors.append("字段 'id' 必须是字符串")
    
    if "name" in data and not isinstance(data["name"], str):
        errors.append("字段 'name' 必须是字符串")
    
    if "description" in data and not isinstance(data["description"], str):
        errors.append("字段 'description' 必须是字符串")
    
    if "default_testset" in data and not isinstance(data["default_testset"], str):
        errors.append("字段 'default_testset' 必须是字符串")
    
    # 验证 inputs 字段
    if "inputs" in data:
        if not isinstance(data["inputs"], list):
            errors.append("字段 'inputs' 必须是列表")
        else:
            for i, input_item in enumerate(data["inputs"]):
                if isinstance(input_item, dict):
                    if "name" not in input_item:
                        errors.append(f"输入项 {i} 缺少 'name' 字段")
                elif not isinstance(input_item, str):
                    errors.append(f"输入项 {i} 必须是字符串或包含 'name' 字段的字典")
    
    # 验证 steps 字段
    if "steps" in data:
        if not isinstance(data["steps"], list):
            errors.append("字段 'steps' 必须是列表")
        else:
            for i, step in enumerate(data["steps"]):
                if not isinstance(step, dict):
                    errors.append(f"步骤 {i} 必须是字典")
                    continue
                
                # 验证基本必需字段
                if "id" not in step:
                    errors.append(f"步骤 {i} 缺少必需字段: id")
                elif not step["id"]:
                    errors.append(f"步骤 {i} 的字段 'id' 不能为空")
                
                if "output_key" not in step:
                    errors.append(f"步骤 {i} 缺少必需字段: output_key")
                elif not step["output_key"]:
                    errors.append(f"步骤 {i} 的字段 'output_key' 不能为空")
                
                # 根据步骤类型验证
                step_type = step.get("type", "agent_flow")
                
                if step_type == "agent_flow":
                    # Agent Flow 步骤需要 agent 和 flow 字段
                    if "agent" not in step:
                        errors.append(f"步骤 {i} (agent_flow) 缺少必需字段: agent")
                    elif not step["agent"]:
                        errors.append(f"步骤 {i} 的字段 'agent' 不能为空")
                    
                    if "flow" not in step:
                        errors.append(f"步骤 {i} (agent_flow) 缺少必需字段: flow")
                    elif not step["flow"]:
                        errors.append(f"步骤 {i} 的字段 'flow' 不能为空")
                
                elif step_type == "code_node":
                    # 验证代码节点配置
                    code_errors = validate_code_node_config(step, i)
                    errors.extend(code_errors)
                
                elif step_type == "batch_aggregator":
                    # 验证批量聚合配置
                    if "aggregation_strategy" not in step:
                        errors.append(f"步骤 {i} (batch_aggregator) 缺少必需字段: aggregation_strategy")
                    elif step["aggregation_strategy"] not in ["concat", "stats", "filter", "group", "summary", "custom"]:
                        errors.append(
                            f"步骤 {i}: 不支持的聚合策略 '{step['aggregation_strategy']}'。"
                            f"支持的策略: concat, stats, filter, group, summary, custom"
                        )
                    
                    # 验证策略特定字段
                    aggregation_strategy = step.get("aggregation_strategy")
                    
                    if aggregation_strategy == "custom":
                        # Accept either 'code', 'aggregation_code', or 'code_file'
                        has_code = "code" in step or "aggregation_code" in step or "code_file" in step
                        if not has_code:
                            errors.append(f"步骤 {i}: 自定义聚合策略必须指定 'code', 'aggregation_code' 或 'code_file'")
                        if "language" not in step:
                            errors.append(f"步骤 {i}: 自定义聚合策略必须指定 'language' (python 或 javascript)")
                    
                    if aggregation_strategy == "stats" and "fields" not in step:
                        errors.append(f"步骤 {i}: stats 聚合策略必须指定 'fields' 字段列表")
                    
                    if aggregation_strategy == "filter" and "condition" not in step:
                        errors.append(f"步骤 {i}: filter 聚合策略必须指定 'condition' 过滤条件")
                    
                    if aggregation_strategy == "group" and "group_by" not in step:
                        errors.append(f"步骤 {i}: group 聚合策略必须指定 'group_by' 分组字段")
                    
                    if aggregation_strategy == "summary" and "summary_fields" not in step:
                        errors.append(f"步骤 {i}: summary 聚合策略必须指定 'summary_fields' 汇总字段列表")
                
                else:
                    errors.append(
                        f"步骤 {i}: 不支持的步骤类型 '{step_type}'。"
                        f"支持的类型: agent_flow, code_node, batch_aggregator"
                    )
                
                # 验证批量处理配置（适用于所有步骤类型）
                if step.get("batch_mode", False):
                    batch_size = step.get("batch_size", 10)
                    max_workers = step.get("max_workers", 4)
                    
                    if not isinstance(batch_size, int):
                        errors.append(f"步骤 {i}: 'batch_size' 必须是整数")
                    elif batch_size <= 0:
                        errors.append(f"步骤 {i}: 'batch_size' 必须是正整数")
                    
                    if not isinstance(max_workers, int):
                        errors.append(f"步骤 {i}: 'max_workers' 必须是整数")
                    elif max_workers <= 0:
                        errors.append(f"步骤 {i}: 'max_workers' 必须是正整数")
                    
                    if "concurrent" in step and not isinstance(step["concurrent"], bool):
                        errors.append(f"步骤 {i}: 'concurrent' 必须是布尔值")
                
                # 验证 input_mapping
                if "input_mapping" in step and not isinstance(step["input_mapping"], dict):
                    errors.append(f"步骤 {i} 的 'input_mapping' 必须是字典")
    
    # 验证 outputs 字段
    if "outputs" in data:
        if not isinstance(data["outputs"], list):
            errors.append("字段 'outputs' 必须是列表")
        else:
            for i, output_item in enumerate(data["outputs"]):
                if isinstance(output_item, dict):
                    if "key" not in output_item:
                        errors.append(f"输出项 {i} 缺少 'key' 字段")
                elif not isinstance(output_item, str):
                    errors.append(f"输出项 {i} 必须是字符串或包含 'key' 字段的字典")
    
    # 验证 baseline 字段
    if "baseline" in data:
        baseline = data["baseline"]
        if not isinstance(baseline, dict):
            errors.append("字段 'baseline' 必须是字典")
        else:
            if "name" not in baseline:
                errors.append("Baseline 缺少 'name' 字段")
            if "steps" in baseline and not isinstance(baseline["steps"], dict):
                errors.append("Baseline 的 'steps' 字段必须是字典")
    
    # 验证 variants 字段
    if "variants" in data:
        if not isinstance(data["variants"], dict):
            errors.append("字段 'variants' 必须是字典")
        else:
            for variant_name, variant in data["variants"].items():
                if not isinstance(variant, dict):
                    errors.append(f"变体 '{variant_name}' 必须是字典")
                elif "overrides" in variant and not isinstance(variant["overrides"], dict):
                    errors.append(f"变体 '{variant_name}' 的 'overrides' 字段必须是字典")
    
    return errors


def validate_output_parser_config(parser_config: Dict[str, Any], location: str) -> List[str]:
    """
    验证 output_parser 配置的有效性
    
    Args:
        parser_config: output_parser 配置字典
        location: 配置位置描述（用于错误信息）
    
    Returns:
        错误列表
    """
    errors = []
    
    # 验证 type 字段
    if "type" not in parser_config:
        errors.append(f"{location}: output_parser 缺少 'type' 字段")
        return errors
    
    parser_type = parser_config["type"]
    valid_types = ["json", "pydantic", "list", "none"]
    if parser_type not in valid_types:
        errors.append(
            f"{location}: 不支持的 output_parser 类型 '{parser_type}'。"
            f"支持的类型: {', '.join(valid_types)}"
        )
    
    # 验证 JSON parser 配置
    if parser_type == "json" and "schema" in parser_config:
        schema = parser_config["schema"]
        if not isinstance(schema, dict):
            errors.append(f"{location}: JSON schema 必须是字典类型")
        else:
            # 验证 JSON schema 的基本结构
            schema_errors = _validate_json_schema(schema, location)
            errors.extend(schema_errors)
    
    # 验证 Pydantic parser 配置
    if parser_type == "pydantic":
        if "pydantic_model" not in parser_config:
            errors.append(f"{location}: Pydantic parser 必须指定 'pydantic_model' 字段")
        elif not isinstance(parser_config["pydantic_model"], str):
            errors.append(f"{location}: 'pydantic_model' 必须是字符串")
    
    # 验证重试配置
    if "max_retries" in parser_config:
        max_retries = parser_config["max_retries"]
        if not isinstance(max_retries, int):
            errors.append(f"{location}: 'max_retries' 必须是整数")
        elif max_retries < 0:
            errors.append(f"{location}: 'max_retries' 必须是非负整数")
    
    if "retry_on_error" in parser_config:
        if not isinstance(parser_config["retry_on_error"], bool):
            errors.append(f"{location}: 'retry_on_error' 必须是布尔值")
    
    return errors


def _validate_json_schema(schema: Dict[str, Any], location: str) -> List[str]:
    """
    验证 JSON schema 的基本格式
    
    Args:
        schema: JSON schema 字典
        location: 配置位置描述
    
    Returns:
        错误列表
    """
    errors = []
    
    # 验证 type 字段
    if "type" in schema:
        schema_type = schema["type"]
        valid_schema_types = ["object", "array", "string", "number", "integer", "boolean", "null"]
        if schema_type not in valid_schema_types:
            errors.append(
                f"{location}: JSON schema 的 type '{schema_type}' 无效。"
                f"有效类型: {', '.join(valid_schema_types)}"
            )
    
    # 验证 properties 字段（对于 object 类型）
    if schema.get("type") == "object" and "properties" in schema:
        properties = schema["properties"]
        if not isinstance(properties, dict):
            errors.append(f"{location}: JSON schema 的 'properties' 必须是字典")
    
    # 验证 required 字段
    if "required" in schema:
        required = schema["required"]
        if not isinstance(required, list):
            errors.append(f"{location}: JSON schema 的 'required' 必须是列表")
        elif not all(isinstance(item, str) for item in required):
            errors.append(f"{location}: JSON schema 的 'required' 列表中的所有项必须是字符串")
    
    # 验证 items 字段（对于 array 类型）
    if schema.get("type") == "array" and "items" in schema:
        items = schema["items"]
        if not isinstance(items, dict):
            errors.append(f"{location}: JSON schema 的 'items' 必须是字典")
    
    return errors


def load_pipeline_config(pipeline_id: str) -> PipelineConfig:
    """加载指定 pipeline 的配置"""
    # 查找配置文件
    config_path = find_pipeline_config_file(pipeline_id)
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise create_config_error(
            message=f"YAML 解析错误: {e}",
            suggestion="请检查 YAML 文件的语法，确保缩进和格式正确",
            file_path=str(config_path)
        )
    except FileNotFoundError:
        available_pipelines = list_available_pipelines()
        suggestion = f"可用的 pipelines: {', '.join(available_pipelines)}" if available_pipelines else "请先创建 pipeline 配置文件"
        raise create_config_error(
            message=f"Pipeline 配置文件不存在: {config_path}",
            suggestion=suggestion,
            file_path=str(config_path)
        )
    except Exception as e:
        raise create_config_error(
            message=f"读取配置文件时出错: {e}",
            suggestion="请检查文件权限和磁盘空间",
            file_path=str(config_path)
        )
    
    if not isinstance(data, dict):
        raise create_config_error(
            message="配置文件根节点必须是字典",
            suggestion="请确保 YAML 文件的根级别是字典格式",
            file_path=str(config_path)
        )
    
    # Schema 验证
    schema_errors = validate_yaml_schema(data)
    
    # 验证 output_parser 配置（如果存在）
    if "steps" in data and isinstance(data["steps"], list):
        for i, step in enumerate(data["steps"]):
            if isinstance(step, dict) and "output_parser" in step:
                parser_errors = validate_output_parser_config(
                    step["output_parser"],
                    f"步骤 {i} (id: {step.get('id', 'unknown')})"
                )
                schema_errors.extend(parser_errors)
    
    if schema_errors:
        error_msg = "配置文件 schema 验证失败:\n" + "\n".join(f"- {error}" for error in schema_errors)
        raise create_config_error(
            message=error_msg,
            suggestion="请检查配置文件的字段名称、类型和必需字段",
            file_path=str(config_path)
        )
    
    # 创建配置对象
    try:
        config = PipelineConfig.from_dict(data)
    except Exception as e:
        raise create_config_error(
            message=f"创建配置对象时出错: {e}",
            suggestion="请检查配置文件的数据格式和字段值",
            file_path=str(config_path)
        )
    
    # 数据验证
    validation_errors = config.validate()
    if validation_errors:
        error_msg = "配置验证失败:\n" + "\n".join(f"- {error}" for error in validation_errors)
        raise create_config_error(
            message=error_msg,
            suggestion="请检查配置的逻辑一致性和数据完整性",
            file_path=str(config_path)
        )
    
    # 引用完整性验证
    validator = PipelineValidator()
    reference_errors = validator.validate_references(config)
    if reference_errors:
        error_msg = "引用验证失败:\n" + "\n".join(f"- {error}" for error in reference_errors)
        raise create_config_error(
            message=error_msg,
            suggestion="请确保引用的 agents、flows 和文件都存在",
            file_path=str(config_path)
        )
    
    return config


def find_pipeline_config_file(pipeline_id: str) -> Path:
    """查找 pipeline 配置文件（支持多目录）"""
    # 在多个目录中查找
    for base_dir in PIPELINE_DIRS:
        if not base_dir.exists():
            continue
        
        # 查找 {base_dir}/{pipeline_id}.yaml
        config_path = base_dir / f"{pipeline_id}.yaml"
        if config_path.exists():
            return config_path
        
        # 查找 {base_dir}/{pipeline_id}/pipeline.yaml
        dir_config_path = base_dir / pipeline_id / "pipeline.yaml"
        if dir_config_path.exists():
            return dir_config_path
    
    available_pipelines = list_available_pipelines()
    suggestion = f"可用的 pipelines: {', '.join(available_pipelines)}" if available_pipelines else "请先创建 pipeline 配置文件"
    raise create_config_error(
        message=f"找不到 pipeline '{pipeline_id}' 的配置文件",
        suggestion=suggestion
    )


def list_available_pipelines() -> List[str]:
    """列出所有可用的 pipeline ID（支持多目录）"""
    pipeline_ids = set()
    
    # 遍历所有 Pipeline 目录
    for base_dir in PIPELINE_DIRS:
        if not base_dir.exists():
            continue
        
        # 查找 {base_dir}/{pipeline_id}.yaml 文件
        for yaml_file in base_dir.glob("*.yaml"):
            pipeline_ids.add(yaml_file.stem)
        
        # 查找 {base_dir}/{pipeline_id}/pipeline.yaml 文件
        for pipeline_dir in base_dir.iterdir():
            if (pipeline_dir.is_dir() and 
                (pipeline_dir / "pipeline.yaml").exists()):
                pipeline_ids.add(pipeline_dir.name)
    
    return sorted(pipeline_ids)


def save_pipeline_config(config: PipelineConfig, file_path: Optional[Path] = None) -> Path:
    """保存 pipeline 配置到文件"""
    if file_path is None:
        # 确保 pipelines 目录存在
        PIPELINES_DIR.mkdir(parents=True, exist_ok=True)
        file_path = PIPELINES_DIR / f"{config.id}.yaml"
    
    # 验证配置
    validation_errors = config.validate()
    if validation_errors:
        raise PipelineConfigError(f"配置验证失败:\n" + "\n".join(f"- {error}" for error in validation_errors))
    
    # 转换为字典并保存
    data = config.to_dict()
    
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, indent=2)
    except Exception as e:
        raise PipelineConfigError(f"保存配置文件时出错: {e}")
    
    return file_path


def validate_pipeline_config_file(file_path: Path) -> List[str]:
    """
    验证 pipeline 配置文件，返回错误列表
    
    Args:
        file_path: 配置文件路径
    
    Returns:
        错误列表，每个错误包含详细的位置和修复建议
    """
    errors = []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [
            f"YAML 解析错误: {e}\n"
            f"  文件: {file_path}\n"
            f"  修复建议: 请检查 YAML 文件的语法，确保缩进和格式正确"
        ]
    except FileNotFoundError:
        return [
            f"配置文件不存在: {file_path}\n"
            f"  修复建议: 请确认文件路径正确，或创建新的配置文件"
        ]
    except Exception as e:
        return [
            f"读取配置文件时出错: {e}\n"
            f"  文件: {file_path}\n"
            f"  修复建议: 请检查文件权限和磁盘空间"
        ]
    
    if not isinstance(data, dict):
        return [
            "配置文件根节点必须是字典\n"
            f"  文件: {file_path}\n"
            f"  修复建议: 请确保 YAML 文件的根级别是字典格式（键值对）"
        ]
    
    # Schema 验证
    errors.extend(validate_yaml_schema(data))
    
    # 验证 output_parser 配置（如果存在）
    if "steps" in data and isinstance(data["steps"], list):
        for i, step in enumerate(data["steps"]):
            if isinstance(step, dict) and "output_parser" in step:
                parser_errors = validate_output_parser_config(
                    step["output_parser"],
                    f"步骤 {i} (id: {step.get('id', 'unknown')})"
                )
                errors.extend(parser_errors)
    
    # 如果 schema 验证失败，不继续后续验证
    if errors:
        return errors
    
    try:
        # 创建配置对象并验证
        config = PipelineConfig.from_dict(data)
        errors.extend(config.validate())
        
        # 引用完整性验证
        validator = PipelineValidator()
        errors.extend(validator.validate_references(config))
        
    except Exception as e:
        errors.append(
            f"配置对象创建或验证时出错: {e}\n"
            f"  文件: {file_path}\n"
            f"  修复建议: 请检查配置文件的数据格式和字段值"
        )
    
    return errors


def format_validation_errors(errors: List[str], file_path: Optional[Path] = None) -> str:
    """
    格式化验证错误为易读的字符串
    
    Args:
        errors: 错误列表
        file_path: 配置文件路径（可选）
    
    Returns:
        格式化的错误消息
    """
    if not errors:
        return "✅ 配置验证通过"
    
    lines = []
    lines.append(f"❌ 配置验证失败，发现 {len(errors)} 个错误:")
    
    if file_path:
        lines.append(f"📄 文件: {file_path}")
    
    lines.append("")
    
    for i, error in enumerate(errors, 1):
        lines.append(f"{i}. {error}")
        lines.append("")
    
    return "\n".join(lines)


def get_pipeline_summary(pipeline_id: str) -> str:
    """获取 pipeline 的简要信息，用于命令行帮助"""
    try:
        config = load_pipeline_config(pipeline_id)
        step_count = len(config.steps)
        variant_count = len(config.variants)
        return f"{config.name} ({step_count} 步骤, {variant_count} 变体)"
    except Exception:
        return f"{pipeline_id} (配置加载失败)"