# tests/test_pipeline_config.py
"""
Pipeline 配置解析器单元测试
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from src.pipeline_config import (
    PipelineValidator, validate_yaml_schema, load_pipeline_config,
    find_pipeline_config_file, list_available_pipelines, save_pipeline_config,
    validate_pipeline_config_file, get_pipeline_summary, PipelineConfigError
)
from src.models import PipelineConfig
from src.error_handler import ConfigError


class TestPipelineValidator:
    """测试 PipelineValidator 类"""
    
    def test_validator_initialization(self):
        """测试验证器初始化"""
        with patch('src.pipeline_config.list_available_agents') as mock_list_agents, \
             patch('src.pipeline_config.load_agent') as mock_load_agent:
            
            mock_list_agents.return_value = ["agent1", "agent2"]
            
            mock_agent1 = Mock()
            mock_agent1.flows = [Mock(name="flow1"), Mock(name="flow2")]
            mock_agent2 = Mock()
            mock_agent2.flows = [Mock(name="flow3")]
            
            def mock_load(agent_id):
                if agent_id == "agent1":
                    return mock_agent1
                elif agent_id == "agent2":
                    return mock_agent2
                raise ValueError(f"Agent not found: {agent_id}")
            
            mock_load_agent.side_effect = mock_load
            
            validator = PipelineValidator()
            
            assert validator.available_agents == {"agent1", "agent2"}
            assert validator.agent_flows["agent1"] == {"flow1", "flow2"}
            assert validator.agent_flows["agent2"] == {"flow3"}
    
    def test_validator_initialization_with_errors(self):
        """测试验证器初始化时处理错误"""
        with patch('src.pipeline_config.list_available_agents') as mock_list_agents, \
             patch('src.pipeline_config.load_agent') as mock_load_agent:
            
            mock_list_agents.return_value = ["agent1", "agent2"]
            
            def mock_load(agent_id):
                if agent_id == "agent1":
                    mock_agent = Mock()
                    mock_agent.flows = [Mock(name="flow1")]
                    return mock_agent
                else:
                    raise Exception("Load error")
            
            mock_load_agent.side_effect = mock_load
            
            validator = PipelineValidator()
            
            # 应该处理错误并继续
            assert "agent1" in validator.available_agents
            assert validator.agent_flows["agent1"] == {"flow1"}
            assert validator.agent_flows["agent2"] == set()  # 空集合，因为加载失败
    
    def test_validate_references_success(self, sample_pipeline_config):
        """测试成功的引用验证"""
        with patch('src.pipeline_config.list_available_agents') as mock_list_agents, \
             patch('src.pipeline_config.load_agent') as mock_load_agent:
            
            mock_list_agents.return_value = ["test_agent"]
            
            mock_agent = Mock()
            mock_agent.flows = [
                Mock(name="test_flow"),
                Mock(name="test_flow2"),
                Mock(name="baseline_flow"),
                Mock(name="baseline_flow2"),
                Mock(name="variant_flow")
            ]
            mock_load_agent.return_value = mock_agent
            
            validator = PipelineValidator()
            errors = validator.validate_references(sample_pipeline_config)
            
            assert errors == []
    
    def test_validate_references_missing_agent(self, sample_pipeline_config):
        """测试缺失 agent 的引用验证"""
        with patch('src.pipeline_config.list_available_agents') as mock_list_agents:
            mock_list_agents.return_value = []  # 没有可用的 agent
            
            validator = PipelineValidator()
            errors = validator.validate_references(sample_pipeline_config)
            
            assert len(errors) > 0
            assert any("不存在的 agent" in error for error in errors)
    
    def test_validate_references_missing_flow(self, sample_pipeline_config):
        """测试缺失 flow 的引用验证"""
        with patch('src.pipeline_config.list_available_agents') as mock_list_agents, \
             patch('src.pipeline_config.load_agent') as mock_load_agent:
            
            mock_list_agents.return_value = ["test_agent"]
            
            mock_agent = Mock()
            mock_agent.flows = [Mock(name="other_flow")]  # 不包含所需的 flows
            mock_load_agent.return_value = mock_agent
            
            validator = PipelineValidator()
            errors = validator.validate_references(sample_pipeline_config)
            
            assert len(errors) > 0
            assert any("不存在的 flow" in error for error in errors)
    
    def test_validate_references_baseline_flow_missing(self, sample_pipeline_config):
        """测试 baseline flow 缺失的验证"""
        with patch('src.pipeline_config.list_available_agents') as mock_list_agents, \
             patch('src.pipeline_config.load_agent') as mock_load_agent:
            
            mock_list_agents.return_value = ["test_agent"]
            
            mock_agent = Mock()
            mock_agent.flows = [
                Mock(name="test_flow"),
                Mock(name="test_flow2")
                # 缺少 baseline_flow 和 baseline_flow2
            ]
            mock_load_agent.return_value = mock_agent
            
            validator = PipelineValidator()
            errors = validator.validate_references(sample_pipeline_config)
            
            assert len(errors) > 0
            assert any("Baseline" in error and "不存在的 flow" in error for error in errors)
    
    def test_validate_references_variant_flow_missing(self, sample_pipeline_config):
        """测试变体 flow 缺失的验证"""
        with patch('src.pipeline_config.list_available_agents') as mock_list_agents, \
             patch('src.pipeline_config.load_agent') as mock_load_agent:
            
            mock_list_agents.return_value = ["test_agent"]
            
            mock_agent = Mock()
            mock_agent.flows = [
                Mock(name="test_flow"),
                Mock(name="test_flow2"),
                Mock(name="baseline_flow"),
                Mock(name="baseline_flow2")
                # 缺少 variant_flow
            ]
            mock_load_agent.return_value = mock_agent
            
            validator = PipelineValidator()
            errors = validator.validate_references(sample_pipeline_config)
            
            assert len(errors) > 0
            assert any("变体" in error and "不存在的 flow" in error for error in errors)
    
    def test_validate_references_testset_missing(self, sample_pipeline_config):
        """测试测试集文件缺失的验证"""
        with patch('src.pipeline_config.list_available_agents') as mock_list_agents, \
             patch('src.pipeline_config.load_agent') as mock_load_agent:
            
            mock_list_agents.return_value = ["test_agent"]
            mock_agent = Mock()
            mock_agent.flows = [
                Mock(name="test_flow"),
                Mock(name="test_flow2"),
                Mock(name="baseline_flow"),
                Mock(name="baseline_flow2"),
                Mock(name="variant_flow")
            ]
            mock_load_agent.return_value = mock_agent
            
            validator = PipelineValidator()
            
            # 模拟测试集文件不存在
            with patch.object(validator, '_resolve_testset_path') as mock_resolve:
                mock_path = Mock()
                mock_path.exists.return_value = False
                mock_resolve.return_value = mock_path
                
                errors = validator.validate_references(sample_pipeline_config)
                
                assert any("测试集文件不存在" in error for error in errors)
    
    def test_resolve_testset_path_absolute(self):
        """测试解析绝对路径的测试集文件"""
        validator = PipelineValidator()
        
        absolute_path = Path("/absolute/path/test.jsonl")
        result = validator._resolve_testset_path("pipeline_id", str(absolute_path))
        
        assert result == absolute_path
    
    def test_resolve_testset_path_relative_pipeline(self):
        """测试解析相对路径的测试集文件（pipeline 目录）"""
        validator = PipelineValidator()
        
        with patch('pathlib.Path.exists') as mock_exists:
            def exists_side_effect():
                # 模拟 pipeline 目录下的文件存在
                return True
            
            mock_exists.side_effect = exists_side_effect
            
            result = validator._resolve_testset_path("test_pipeline", "test.jsonl")
            
            expected_path = Path(__file__).resolve().parent.parent / "data" / "pipelines" / "test_pipeline" / "testsets" / "test.jsonl"
            assert result == expected_path


class TestValidateYamlSchema:
    """测试 YAML schema 验证"""
    
    def test_validate_yaml_schema_success(self):
        """测试成功的 schema 验证"""
        valid_data = {
            "id": "test_pipeline",
            "name": "测试 Pipeline",
            "description": "测试描述",
            "steps": [
                {
                    "id": "step1",
                    "agent": "test_agent",
                    "flow": "test_flow",
                    "output_key": "output1",
                    "input_mapping": {"param": "value"}
                }
            ]
        }
        
        errors = validate_yaml_schema(valid_data)
        assert errors == []
    
    def test_validate_yaml_schema_missing_required_fields(self):
        """测试缺少必需字段的验证"""
        invalid_data = {
            "name": "测试 Pipeline"
            # 缺少 id 和 steps
        }
        
        errors = validate_yaml_schema(invalid_data)
        
        assert len(errors) >= 2
        assert any("缺少必需字段: id" in error for error in errors)
        assert any("缺少必需字段: steps" in error for error in errors)
    
    def test_validate_yaml_schema_empty_required_fields(self):
        """测试必需字段为空的验证"""
        invalid_data = {
            "id": "",
            "name": "",
            "steps": []
        }
        
        errors = validate_yaml_schema(invalid_data)
        
        assert any("必需字段不能为空: id" in error for error in errors)
        assert any("必需字段不能为空: name" in error for error in errors)
    
    def test_validate_yaml_schema_wrong_field_types(self):
        """测试字段类型错误的验证"""
        invalid_data = {
            "id": 123,  # 应该是字符串
            "name": [],  # 应该是字符串
            "steps": "not_a_list"  # 应该是列表
        }
        
        errors = validate_yaml_schema(invalid_data)
        
        assert any("'id' 必须是字符串" in error for error in errors)
        assert any("'name' 必须是字符串" in error for error in errors)
        assert any("'steps' 必须是列表" in error for error in errors)
    
    def test_validate_yaml_schema_invalid_inputs(self):
        """测试无效 inputs 字段的验证"""
        invalid_data = {
            "id": "test",
            "name": "test",
            "steps": [],
            "inputs": "not_a_list"  # 应该是列表
        }
        
        errors = validate_yaml_schema(invalid_data)
        
        assert any("'inputs' 必须是列表" in error for error in errors)
    
    def test_validate_yaml_schema_invalid_input_items(self):
        """测试无效 input 项的验证"""
        invalid_data = {
            "id": "test",
            "name": "test",
            "steps": [],
            "inputs": [
                {"name": "valid_input"},
                {},  # 缺少 name 字段
                123  # 不是字符串或字典
            ]
        }
        
        errors = validate_yaml_schema(invalid_data)
        
        assert any("输入项 1 缺少 'name' 字段" in error for error in errors)
        assert any("输入项 2 必须是字符串或包含 'name' 字段的字典" in error for error in errors)
    
    def test_validate_yaml_schema_invalid_steps(self):
        """测试无效 steps 的验证"""
        invalid_data = {
            "id": "test",
            "name": "test",
            "steps": [
                {
                    "id": "step1",
                    "agent": "test_agent",
                    "flow": "test_flow",
                    "output_key": "output1"
                },
                {
                    # 缺少必需字段
                    "id": "step2"
                },
                "not_a_dict"  # 不是字典
            ]
        }
        
        errors = validate_yaml_schema(invalid_data)
        
        # Step 1 is missing agent and flow (it's agent_flow type by default)
        assert any("步骤 1" in error and ("agent" in error or "缺少必需字段" in error) for error in errors)
        assert any("步骤 2 必须是字典" in error for error in errors)
    
    def test_validate_yaml_schema_invalid_step_input_mapping(self):
        """测试无效步骤 input_mapping 的验证"""
        invalid_data = {
            "id": "test",
            "name": "test",
            "steps": [
                {
                    "id": "step1",
                    "agent": "test_agent",
                    "flow": "test_flow",
                    "output_key": "output1",
                    "input_mapping": "not_a_dict"  # 应该是字典
                }
            ]
        }
        
        errors = validate_yaml_schema(invalid_data)
        
        assert any("'input_mapping' 必须是字典" in error for error in errors)
    
    def test_validate_yaml_schema_invalid_outputs(self):
        """测试无效 outputs 的验证"""
        invalid_data = {
            "id": "test",
            "name": "test",
            "steps": [],
            "outputs": [
                {"key": "valid_output"},
                {},  # 缺少 key 字段
                123  # 不是字符串或字典
            ]
        }
        
        errors = validate_yaml_schema(invalid_data)
        
        assert any("输出项 1 缺少 'key' 字段" in error for error in errors)
        assert any("输出项 2 必须是字符串或包含 'key' 字段的字典" in error for error in errors)
    
    def test_validate_yaml_schema_invalid_baseline(self):
        """测试无效 baseline 的验证"""
        invalid_data = {
            "id": "test",
            "name": "test",
            "steps": [],
            "baseline": {
                # 缺少 name 字段
                "steps": "not_a_dict"  # 应该是字典
            }
        }
        
        errors = validate_yaml_schema(invalid_data)
        
        assert any("Baseline 缺少 'name' 字段" in error for error in errors)
        assert any("Baseline 的 'steps' 字段必须是字典" in error for error in errors)
    
    def test_validate_yaml_schema_invalid_variants(self):
        """测试无效 variants 的验证"""
        invalid_data = {
            "id": "test",
            "name": "test",
            "steps": [],
            "variants": {
                "variant1": {
                    "description": "valid variant"
                },
                "variant2": "not_a_dict",  # 应该是字典
                "variant3": {
                    "overrides": "not_a_dict"  # 应该是字典
                }
            }
        }
        
        errors = validate_yaml_schema(invalid_data)
        
        assert any("变体 'variant2' 必须是字典" in error for error in errors)
        assert any("变体 'variant3' 的 'overrides' 字段必须是字典" in error for error in errors)


class TestLoadPipelineConfig:
    """测试 load_pipeline_config 函数"""
    
    def test_load_pipeline_config_success(self, sample_pipeline_config):
        """测试成功加载 pipeline 配置"""
        config_data = sample_pipeline_config.to_dict()
        
        with patch('src.pipeline_config.find_pipeline_config_file') as mock_find, \
             patch('builtins.open', mock_open(read_data=yaml.dump(config_data))), \
             patch('src.pipeline_config.PipelineValidator') as mock_validator_class:
            
            mock_find.return_value = Path("test_pipeline.yaml")
            mock_validator = Mock()
            mock_validator.validate_references.return_value = []
            mock_validator_class.return_value = mock_validator
            
            result = load_pipeline_config("test_pipeline")
            
            assert result.id == "test_pipeline"
            assert result.name == "测试 Pipeline"
    
    def test_load_pipeline_config_yaml_error(self):
        """测试 YAML 解析错误"""
        with patch('src.pipeline_config.find_pipeline_config_file') as mock_find, \
             patch('builtins.open', mock_open(read_data="invalid: yaml: content:")):
            
            mock_find.return_value = Path("test_pipeline.yaml")
            
            with pytest.raises(ConfigError, match="YAML 解析错误"):
                load_pipeline_config("test_pipeline")
    
    def test_load_pipeline_config_file_not_found(self):
        """测试配置文件不存在"""
        with patch('src.pipeline_config.find_pipeline_config_file') as mock_find:
            mock_find.side_effect = ConfigError("文件不存在")
            
            with pytest.raises(ConfigError):
                load_pipeline_config("nonexistent_pipeline")
    
    def test_load_pipeline_config_not_dict(self):
        """测试配置文件根节点不是字典"""
        with patch('src.pipeline_config.find_pipeline_config_file') as mock_find, \
             patch('builtins.open', mock_open(read_data="- not_a_dict")):
            
            mock_find.return_value = Path("test_pipeline.yaml")
            
            with pytest.raises(ConfigError, match="配置文件根节点必须是字典"):
                load_pipeline_config("test_pipeline")
    
    def test_load_pipeline_config_schema_validation_error(self):
        """测试 schema 验证错误"""
        invalid_config = {"name": "test"}  # 缺少必需字段
        
        with patch('src.pipeline_config.find_pipeline_config_file') as mock_find, \
             patch('builtins.open', mock_open(read_data=yaml.dump(invalid_config))):
            
            mock_find.return_value = Path("test_pipeline.yaml")
            
            with pytest.raises(ConfigError, match="schema 验证失败"):
                load_pipeline_config("test_pipeline")
    
    def test_load_pipeline_config_reference_validation_error(self, sample_pipeline_config):
        """测试引用验证错误"""
        config_data = sample_pipeline_config.to_dict()
        
        with patch('src.pipeline_config.find_pipeline_config_file') as mock_find, \
             patch('builtins.open', mock_open(read_data=yaml.dump(config_data))), \
             patch('src.pipeline_config.PipelineValidator') as mock_validator_class:
            
            mock_find.return_value = Path("test_pipeline.yaml")
            mock_validator = Mock()
            mock_validator.validate_references.return_value = ["引用错误"]
            mock_validator_class.return_value = mock_validator
            
            with pytest.raises(ConfigError, match="引用验证失败"):
                load_pipeline_config("test_pipeline")


class TestFindPipelineConfigFile:
    """测试 find_pipeline_config_file 函数"""
    
    def test_find_pipeline_config_file_direct(self):
        """测试直接找到配置文件"""
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.side_effect = lambda: True  # 第一个路径存在
            
            result = find_pipeline_config_file("test_pipeline")
            
            expected_path = Path(__file__).resolve().parent.parent / "pipelines" / "test_pipeline.yaml"
            assert result == expected_path
    
    def test_find_pipeline_config_file_in_directory(self):
        """测试在目录中找到配置文件"""
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.side_effect = [False, True]  # 第二个路径存在
            
            result = find_pipeline_config_file("test_pipeline")
            
            expected_path = Path(__file__).resolve().parent.parent / "pipelines" / "test_pipeline" / "pipeline.yaml"
            assert result == expected_path
    
    def test_find_pipeline_config_file_not_found(self):
        """测试找不到配置文件"""
        with patch('pathlib.Path.exists') as mock_exists, \
             patch('src.pipeline_config.list_available_pipelines') as mock_list:
            
            mock_exists.return_value = False
            mock_list.return_value = ["other_pipeline"]
            
            with pytest.raises(ConfigError, match="找不到 pipeline"):
                find_pipeline_config_file("nonexistent_pipeline")


class TestListAvailablePipelines:
    """测试 list_available_pipelines 函数"""
    
    def test_list_available_pipelines_success(self):
        """测试成功列出可用的 pipelines"""
        with patch('pathlib.Path.exists') as mock_exists, \
             patch('pathlib.Path.glob') as mock_glob, \
             patch('pathlib.Path.iterdir') as mock_iterdir:
            
            mock_exists.return_value = True
            
            # 模拟 *.yaml 文件
            yaml_files = [Mock(stem="pipeline1"), Mock(stem="pipeline2")]
            mock_glob.return_value = yaml_files
            
            # 模拟目录结构
            dir1 = Mock()
            dir1.is_dir.return_value = True
            dir1.name = "pipeline3"
            dir1.__truediv__ = lambda self, other: Mock(exists=lambda: True)
            
            dir2 = Mock()
            dir2.is_dir.return_value = False  # 不是目录
            
            mock_iterdir.return_value = [dir1, dir2]
            
            result = list_available_pipelines()
            
            assert "pipeline1" in result
            assert "pipeline2" in result
            assert "pipeline3" in result
            assert len(result) == 3
    
    def test_list_available_pipelines_no_directory(self):
        """测试 pipelines 目录不存在"""
        with patch('pathlib.Path.exists') as mock_exists:
            mock_exists.return_value = False
            
            result = list_available_pipelines()
            
            assert result == []


class TestSavePipelineConfig:
    """测试 save_pipeline_config 函数"""
    
    def test_save_pipeline_config_success(self, sample_pipeline_config, temp_dir):
        """测试成功保存 pipeline 配置"""
        file_path = temp_dir / "test_pipeline.yaml"
        
        with patch('src.pipeline_config.PIPELINES_DIR', temp_dir):
            result = save_pipeline_config(sample_pipeline_config, file_path)
            
            assert result == file_path
            assert file_path.exists()
            
            # 验证文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            assert data["id"] == "test_pipeline"
            assert data["name"] == "测试 Pipeline"
    
    def test_save_pipeline_config_default_path(self, sample_pipeline_config, temp_dir):
        """测试使用默认路径保存配置"""
        with patch('src.pipeline_config.PIPELINES_DIR', temp_dir):
            result = save_pipeline_config(sample_pipeline_config)
            
            expected_path = temp_dir / "test_pipeline.yaml"
            assert result == expected_path
            assert expected_path.exists()
    
    def test_save_pipeline_config_validation_error(self):
        """测试保存时配置验证错误"""
        # 创建无效配置
        invalid_config = PipelineConfig(
            id="",  # 空 ID
            name="",
            description="",
            default_testset="",
            inputs=[],
            steps=[],
            outputs=[],
            baseline=None,
            variants={}
        )
        
        with pytest.raises(PipelineConfigError, match="配置验证失败"):
            save_pipeline_config(invalid_config)


class TestValidatePipelineConfigFile:
    """测试 validate_pipeline_config_file 函数"""
    
    def test_validate_pipeline_config_file_success(self, sample_pipeline_config, temp_dir):
        """测试成功验证配置文件"""
        config_file = temp_dir / "test_pipeline.yaml"
        config_data = sample_pipeline_config.to_dict()
        
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f)
        
        with patch('src.pipeline_config.PipelineValidator') as mock_validator_class:
            mock_validator = Mock()
            mock_validator.validate_references.return_value = []
            mock_validator_class.return_value = mock_validator
            
            errors = validate_pipeline_config_file(config_file)
            
            assert errors == []
    
    def test_validate_pipeline_config_file_yaml_error(self, temp_dir):
        """测试验证 YAML 错误的配置文件"""
        config_file = temp_dir / "invalid.yaml"
        config_file.write_text("invalid: yaml: content:")
        
        errors = validate_pipeline_config_file(config_file)
        
        assert len(errors) == 1
        assert "YAML 解析错误" in errors[0]
    
    def test_validate_pipeline_config_file_not_found(self):
        """测试验证不存在的配置文件"""
        nonexistent_file = Path("nonexistent.yaml")
        
        errors = validate_pipeline_config_file(nonexistent_file)
        
        assert len(errors) == 1
        assert "配置文件不存在" in errors[0]
    
    def test_validate_pipeline_config_file_not_dict(self, temp_dir):
        """测试验证根节点不是字典的配置文件"""
        config_file = temp_dir / "not_dict.yaml"
        config_file.write_text("- not_a_dict")
        
        errors = validate_pipeline_config_file(config_file)
        
        assert len(errors) == 1
        assert "配置文件根节点必须是字典" in errors[0]


class TestGetPipelineSummary:
    """测试 get_pipeline_summary 函数"""
    
    def test_get_pipeline_summary_success(self, sample_pipeline_config):
        """测试成功获取 pipeline 摘要"""
        with patch('src.pipeline_config.load_pipeline_config') as mock_load:
            mock_load.return_value = sample_pipeline_config
            
            result = get_pipeline_summary("test_pipeline")
            
            expected = "测试 Pipeline (2 步骤, 1 变体)"
            assert result == expected
    
    def test_get_pipeline_summary_load_error(self):
        """测试加载配置失败时的摘要"""
        with patch('src.pipeline_config.load_pipeline_config') as mock_load:
            mock_load.side_effect = Exception("加载失败")
            
            result = get_pipeline_summary("test_pipeline")
            
            assert result == "test_pipeline (配置加载失败)"


class TestBatchProcessingValidation:
    """测试批量处理配置验证"""
    
    def test_validate_batch_mode_with_valid_config(self):
        """测试有效的批量处理配置"""
        valid_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [
                {
                    "id": "step1",
                    "type": "agent_flow",
                    "agent": "test_agent",
                    "flow": "test_flow",
                    "batch_mode": True,
                    "batch_size": 20,
                    "concurrent": True,
                    "max_workers": 5,
                    "input_mapping": {"text": "input"},
                    "output_key": "output"
                }
            ]
        }
        
        errors = validate_yaml_schema(valid_data)
        assert errors == []
    
    def test_validate_batch_mode_with_invalid_batch_size(self):
        """测试无效的 batch_size"""
        invalid_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [
                {
                    "id": "step1",
                    "type": "agent_flow",
                    "agent": "test_agent",
                    "flow": "test_flow",
                    "batch_mode": True,
                    "batch_size": 0,  # Invalid: must be positive
                    "input_mapping": {"text": "input"},
                    "output_key": "output"
                }
            ]
        }
        
        errors = validate_yaml_schema(invalid_data)
        assert any("'batch_size' 必须是正整数" in error for error in errors)
    
    def test_validate_batch_mode_with_negative_batch_size(self):
        """测试负数的 batch_size"""
        invalid_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [
                {
                    "id": "step1",
                    "type": "agent_flow",
                    "agent": "test_agent",
                    "flow": "test_flow",
                    "batch_mode": True,
                    "batch_size": -5,  # Invalid: negative
                    "input_mapping": {"text": "input"},
                    "output_key": "output"
                }
            ]
        }
        
        errors = validate_yaml_schema(invalid_data)
        assert any("'batch_size' 必须是正整数" in error for error in errors)
    
    def test_validate_batch_mode_with_invalid_max_workers(self):
        """测试无效的 max_workers"""
        invalid_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [
                {
                    "id": "step1",
                    "type": "agent_flow",
                    "agent": "test_agent",
                    "flow": "test_flow",
                    "batch_mode": True,
                    "batch_size": 10,
                    "max_workers": 0,  # Invalid: must be positive
                    "input_mapping": {"text": "input"},
                    "output_key": "output"
                }
            ]
        }
        
        errors = validate_yaml_schema(invalid_data)
        assert any("'max_workers' 必须是正整数" in error for error in errors)
    
    def test_validate_batch_mode_with_non_integer_batch_size(self):
        """测试非整数的 batch_size"""
        invalid_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [
                {
                    "id": "step1",
                    "type": "agent_flow",
                    "agent": "test_agent",
                    "flow": "test_flow",
                    "batch_mode": True,
                    "batch_size": "10",  # Invalid: string instead of int
                    "input_mapping": {"text": "input"},
                    "output_key": "output"
                }
            ]
        }
        
        errors = validate_yaml_schema(invalid_data)
        assert any("'batch_size' 必须是整数" in error for error in errors)
    
    def test_validate_batch_mode_with_invalid_concurrent_type(self):
        """测试无效的 concurrent 类型"""
        invalid_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [
                {
                    "id": "step1",
                    "type": "agent_flow",
                    "agent": "test_agent",
                    "flow": "test_flow",
                    "batch_mode": True,
                    "batch_size": 10,
                    "concurrent": "yes",  # Invalid: string instead of bool
                    "input_mapping": {"text": "input"},
                    "output_key": "output"
                }
            ]
        }
        
        errors = validate_yaml_schema(invalid_data)
        assert any("'concurrent' 必须是布尔值" in error for error in errors)
    
    def test_validate_batch_aggregator_with_all_strategies(self):
        """测试所有聚合策略的验证"""
        strategies = ["concat", "stats", "filter", "group", "summary", "custom"]
        
        for strategy in strategies:
            valid_data = {
                "id": "test_pipeline",
                "name": "Test Pipeline",
                "steps": [
                    {
                        "id": "step1",
                        "type": "batch_aggregator",
                        "aggregation_strategy": strategy,
                        "input_mapping": {"items": "input"},
                        "output_key": "output"
                    }
                ]
            }
            
            # Add required fields for specific strategies
            if strategy == "custom":
                valid_data["steps"][0]["aggregation_code"] = "def aggregate(items): return items"
                valid_data["steps"][0]["language"] = "python"
            elif strategy == "stats":
                valid_data["steps"][0]["fields"] = ["score", "count"]
            elif strategy == "filter":
                valid_data["steps"][0]["condition"] = "item.score > 0.5"
            elif strategy == "group":
                valid_data["steps"][0]["group_by"] = "category"
            elif strategy == "summary":
                valid_data["steps"][0]["summary_fields"] = ["total_count", "average_score"]
            
            errors = validate_yaml_schema(valid_data)
            assert errors == [], f"Strategy {strategy} should be valid but got errors: {errors}"
    
    def test_validate_batch_aggregator_missing_strategy(self):
        """测试缺少聚合策略"""
        invalid_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [
                {
                    "id": "step1",
                    "type": "batch_aggregator",
                    # Missing aggregation_strategy
                    "input_mapping": {"items": "input"},
                    "output_key": "output"
                }
            ]
        }
        
        errors = validate_yaml_schema(invalid_data)
        assert any("缺少必需字段: aggregation_strategy" in error for error in errors)
    
    def test_validate_batch_aggregator_invalid_strategy(self):
        """测试无效的聚合策略"""
        invalid_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [
                {
                    "id": "step1",
                    "type": "batch_aggregator",
                    "aggregation_strategy": "invalid_strategy",
                    "input_mapping": {"items": "input"},
                    "output_key": "output"
                }
            ]
        }
        
        errors = validate_yaml_schema(invalid_data)
        assert any("不支持的聚合策略" in error for error in errors)
        assert any("concat, stats, filter, group, summary, custom" in error for error in errors)
    
    def test_validate_batch_aggregator_custom_missing_code(self):
        """测试自定义聚合策略缺少代码"""
        invalid_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [
                {
                    "id": "step1",
                    "type": "batch_aggregator",
                    "aggregation_strategy": "custom",
                    # Missing code, aggregation_code and code_file
                    "input_mapping": {"items": "input"},
                    "output_key": "output"
                }
            ]
        }
        
        errors = validate_yaml_schema(invalid_data)
        assert any("必须指定 'code', 'aggregation_code' 或 'code_file'" in error for error in errors)
    
    def test_validate_batch_aggregator_custom_missing_language(self):
        """测试自定义聚合策略缺少语言"""
        invalid_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [
                {
                    "id": "step1",
                    "type": "batch_aggregator",
                    "aggregation_strategy": "custom",
                    "aggregation_code": "def aggregate(items): return items",
                    # Missing language
                    "input_mapping": {"items": "input"},
                    "output_key": "output"
                }
            ]
        }
        
        errors = validate_yaml_schema(invalid_data)
        assert any("必须指定 'language'" in error for error in errors)
    
    def test_validate_batch_aggregator_stats_missing_fields(self):
        """测试 stats 策略缺少 fields"""
        invalid_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [
                {
                    "id": "step1",
                    "type": "batch_aggregator",
                    "aggregation_strategy": "stats",
                    # Missing fields
                    "input_mapping": {"items": "input"},
                    "output_key": "output"
                }
            ]
        }
        
        errors = validate_yaml_schema(invalid_data)
        assert any("必须指定 'fields' 字段列表" in error for error in errors)
    
    def test_validate_batch_aggregator_filter_missing_condition(self):
        """测试 filter 策略缺少 condition"""
        invalid_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [
                {
                    "id": "step1",
                    "type": "batch_aggregator",
                    "aggregation_strategy": "filter",
                    # Missing condition
                    "input_mapping": {"items": "input"},
                    "output_key": "output"
                }
            ]
        }
        
        errors = validate_yaml_schema(invalid_data)
        assert any("必须指定 'condition' 过滤条件" in error for error in errors)
    
    def test_validate_batch_aggregator_group_missing_group_by(self):
        """测试 group 策略缺少 group_by"""
        invalid_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [
                {
                    "id": "step1",
                    "type": "batch_aggregator",
                    "aggregation_strategy": "group",
                    # Missing group_by
                    "input_mapping": {"items": "input"},
                    "output_key": "output"
                }
            ]
        }
        
        errors = validate_yaml_schema(invalid_data)
        assert any("必须指定 'group_by' 分组字段" in error for error in errors)
    
    def test_validate_batch_aggregator_summary_missing_summary_fields(self):
        """测试 summary 策略缺少 summary_fields"""
        invalid_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [
                {
                    "id": "step1",
                    "type": "batch_aggregator",
                    "aggregation_strategy": "summary",
                    # Missing summary_fields
                    "input_mapping": {"items": "input"},
                    "output_key": "output"
                }
            ]
        }
        
        errors = validate_yaml_schema(invalid_data)
        assert any("必须指定 'summary_fields' 汇总字段列表" in error for error in errors)
    
    def test_validate_batch_mode_without_batch_mode_flag(self):
        """测试没有 batch_mode 标志时不验证批量字段"""
        # This should be valid - batch fields are ignored if batch_mode is False
        valid_data = {
            "id": "test_pipeline",
            "name": "Test Pipeline",
            "steps": [
                {
                    "id": "step1",
                    "type": "agent_flow",
                    "agent": "test_agent",
                    "flow": "test_flow",
                    "batch_mode": False,
                    "batch_size": -1,  # Would be invalid if batch_mode was True
                    "input_mapping": {"text": "input"},
                    "output_key": "output"
                }
            ]
        }
        
        errors = validate_yaml_schema(valid_data)
        # Should not have batch_size validation errors since batch_mode is False
        assert not any("batch_size" in error for error in errors)
