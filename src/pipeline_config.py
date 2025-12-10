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
PIPELINES_DIR = ROOT_DIR / "pipelines"


class PipelineConfigError(Exception):
    """Pipeline 配置错误（向后兼容）"""
    pass


class PipelineValidator:
    """Pipeline 配置验证器"""
    
    def __init__(self):
        self.available_agents: Set[str] = set()
        self.agent_flows: Dict[str, Set[str]] = {}
        self._load_agent_info()
    
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
        """验证配置中的引用完整性"""
        errors = []
        
        # 验证步骤中的 agent 和 flow 引用
        for step in config.steps:
            # 检查 agent 是否存在
            if step.agent not in self.available_agents:
                errors.append(f"步骤 '{step.id}' 引用了不存在的 agent: {step.agent}")
                continue
                
            # 检查 flow 是否存在
            agent_flows = self.agent_flows.get(step.agent, set())
            if step.flow not in agent_flows:
                errors.append(f"步骤 '{step.id}' 引用了 agent '{step.agent}' 中不存在的 flow: {step.flow}")
        
        # 验证 baseline 中的 flow 引用
        if config.baseline:
            for step_id, baseline_step in config.baseline.steps.items():
                # 找到对应的 pipeline 步骤
                pipeline_step = None
                for step in config.steps:
                    if step.id == step_id:
                        pipeline_step = step
                        break
                
                if pipeline_step:
                    agent_flows = self.agent_flows.get(pipeline_step.agent, set())
                    if baseline_step.flow not in agent_flows:
                        errors.append(f"Baseline 步骤 '{step_id}' 引用了 agent '{pipeline_step.agent}' 中不存在的 flow: {baseline_step.flow}")
        
        # 验证变体中的 flow 引用
        for variant_name, variant in config.variants.items():
            for step_id, override in variant.overrides.items():
                if override.flow:
                    # 找到对应的 pipeline 步骤
                    pipeline_step = None
                    for step in config.steps:
                        if step.id == step_id:
                            pipeline_step = step
                            break
                    
                    if pipeline_step:
                        agent_flows = self.agent_flows.get(pipeline_step.agent, set())
                        if override.flow not in agent_flows:
                            errors.append(f"变体 '{variant_name}' 步骤 '{step_id}' 引用了 agent '{pipeline_step.agent}' 中不存在的 flow: {override.flow}")
        
        # 验证 testset 文件是否存在
        if config.default_testset:
            testset_path = self._resolve_testset_path(config.id, config.default_testset)
            if not testset_path.exists():
                errors.append(f"默认测试集文件不存在: {config.default_testset}")
        
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
            step_required_fields = ["id", "agent", "flow", "output_key"]
            for i, step in enumerate(data["steps"]):
                if not isinstance(step, dict):
                    errors.append(f"步骤 {i} 必须是字典")
                    continue
                
                for field in step_required_fields:
                    if field not in step:
                        errors.append(f"步骤 {i} 缺少必需字段: {field}")
                    elif not step[field]:
                        errors.append(f"步骤 {i} 的字段 '{field}' 不能为空")
                
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
    """查找 pipeline 配置文件"""
    # 优先查找 pipelines/{pipeline_id}.yaml
    config_path = PIPELINES_DIR / f"{pipeline_id}.yaml"
    if config_path.exists():
        return config_path
    
    # 查找 pipelines/{pipeline_id}/pipeline.yaml
    dir_config_path = PIPELINES_DIR / pipeline_id / "pipeline.yaml"
    if dir_config_path.exists():
        return dir_config_path
    
    available_pipelines = list_available_pipelines()
    suggestion = f"可用的 pipelines: {', '.join(available_pipelines)}" if available_pipelines else "请先创建 pipeline 配置文件"
    raise create_config_error(
        message=f"找不到 pipeline '{pipeline_id}' 的配置文件",
        suggestion=suggestion
    )


def list_available_pipelines() -> List[str]:
    """列出所有可用的 pipeline ID"""
    if not PIPELINES_DIR.exists():
        return []
    
    pipeline_ids = []
    
    # 查找 pipelines/{pipeline_id}.yaml 文件
    for yaml_file in PIPELINES_DIR.glob("*.yaml"):
        pipeline_ids.append(yaml_file.stem)
    
    # 查找 pipelines/{pipeline_id}/pipeline.yaml 文件
    for pipeline_dir in PIPELINES_DIR.iterdir():
        if (pipeline_dir.is_dir() and 
            (pipeline_dir / "pipeline.yaml").exists() and 
            pipeline_dir.name not in pipeline_ids):
            pipeline_ids.append(pipeline_dir.name)
    
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
    """验证 pipeline 配置文件，返回错误列表"""
    errors = []
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        return [f"YAML 解析错误: {e}"]
    except FileNotFoundError:
        return [f"配置文件不存在: {file_path}"]
    except Exception as e:
        return [f"读取配置文件时出错: {e}"]
    
    if not isinstance(data, dict):
        return ["配置文件根节点必须是字典"]
    
    # Schema 验证
    errors.extend(validate_yaml_schema(data))
    
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
        errors.append(f"配置对象创建或验证时出错: {e}")
    
    return errors


def get_pipeline_summary(pipeline_id: str) -> str:
    """获取 pipeline 的简要信息，用于命令行帮助"""
    try:
        config = load_pipeline_config(pipeline_id)
        step_count = len(config.steps)
        variant_count = len(config.variants)
        return f"{config.name} ({step_count} 步骤, {variant_count} 变体)"
    except Exception:
        return f"{pipeline_id} (配置加载失败)"