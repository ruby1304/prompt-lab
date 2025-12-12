# tests/test_config_validation.py
"""
配置验证单元测试

测试 Pipeline 配置验证功能，包括：
- Output Parser 配置验证
- JSON Schema 验证
- 循环依赖检测
- 错误信息完整性
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.pipeline_config import (
    validate_output_parser_config,
    _validate_json_schema,
    PipelineValidator,
    format_validation_errors
)
from src.models import PipelineConfig, StepConfig, InputSpec, OutputSpec


class TestValidateOutputParserConfig:
    """测试 Output Parser 配置验证"""
    
    def test_validate_json_parser_success(self):
        """测试有效的 JSON parser 配置"""
        config = {
            "type": "json",
            "schema": {
                "type": "object",
                "properties": {
                    "score": {"type": "number"},
                    "comment": {"type": "string"}
                },
                "required": ["score"]
            },
            "retry_on_error": True,
            "max_retries": 3
        }
        
        errors = validate_output_parser_config(config, "测试位置")
        assert errors == []
    
    def test_validate_pydantic_parser_success(self):
        """测试有效的 Pydantic parser 配置"""
        config = {
            "type": "pydantic",
            "pydantic_model": "MyModel",
            "retry_on_error": True,
            "max_retries": 2
        }
        
        errors = validate_output_parser_config(config, "测试位置")
        assert errors == []
    
    def test_validate_list_parser_success(self):
        """测试有效的 list parser 配置"""
        config = {
            "type": "list",
            "retry_on_error": False
        }
        
        errors = validate_output_parser_config(config, "测试位置")
        assert errors == []
    
    def test_validate_none_parser_success(self):
        """测试有效的 none parser 配置"""
        config = {
            "type": "none"
        }
        
        errors = validate_output_parser_config(config, "测试位置")
        assert errors == []
    
    def test_validate_missing_type(self):
        """测试缺少 type 字段"""
        config = {
            "retry_on_error": True
        }
        
        errors = validate_output_parser_config(config, "步骤 1")
        assert len(errors) == 1
        assert "缺少 'type' 字段" in errors[0]
        assert "步骤 1" in errors[0]
    
    def test_validate_invalid_type(self):
        """测试无效的 parser 类型"""
        config = {
            "type": "invalid_type"
        }
        
        errors = validate_output_parser_config(config, "步骤 2")
        assert len(errors) == 1
        assert "不支持的 output_parser 类型" in errors[0]
        assert "invalid_type" in errors[0]
        assert "json, pydantic, list, none" in errors[0]
    
    def test_validate_json_schema_not_dict(self):
        """测试 JSON schema 不是字典"""
        config = {
            "type": "json",
            "schema": "not_a_dict"
        }
        
        errors = validate_output_parser_config(config, "步骤 3")
        assert len(errors) == 1
        assert "JSON schema 必须是字典类型" in errors[0]
    
    def test_validate_pydantic_missing_model(self):
        """测试 Pydantic parser 缺少 pydantic_model"""
        config = {
            "type": "pydantic"
        }
        
        errors = validate_output_parser_config(config, "步骤 4")
        assert len(errors) == 1
        assert "必须指定 'pydantic_model'" in errors[0]
    
    def test_validate_pydantic_model_not_string(self):
        """测试 pydantic_model 不是字符串"""
        config = {
            "type": "pydantic",
            "pydantic_model": 123
        }
        
        errors = validate_output_parser_config(config, "步骤 5")
        assert len(errors) == 1
        assert "'pydantic_model' 必须是字符串" in errors[0]
    
    def test_validate_max_retries_not_int(self):
        """测试 max_retries 不是整数"""
        config = {
            "type": "json",
            "max_retries": "three"
        }
        
        errors = validate_output_parser_config(config, "步骤 6")
        assert len(errors) == 1
        assert "'max_retries' 必须是整数" in errors[0]
    
    def test_validate_max_retries_negative(self):
        """测试 max_retries 是负数"""
        config = {
            "type": "json",
            "max_retries": -1
        }
        
        errors = validate_output_parser_config(config, "步骤 7")
        assert len(errors) == 1
        assert "'max_retries' 必须是非负整数" in errors[0]
    
    def test_validate_retry_on_error_not_bool(self):
        """测试 retry_on_error 不是布尔值"""
        config = {
            "type": "json",
            "retry_on_error": "yes"
        }
        
        errors = validate_output_parser_config(config, "步骤 8")
        assert len(errors) == 1
        assert "'retry_on_error' 必须是布尔值" in errors[0]


class TestValidateJsonSchema:
    """测试 JSON Schema 验证"""
    
    def test_validate_json_schema_object_success(self):
        """测试有效的 object schema"""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["name"]
        }
        
        errors = _validate_json_schema(schema, "测试位置")
        assert errors == []
    
    def test_validate_json_schema_array_success(self):
        """测试有效的 array schema"""
        schema = {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
        
        errors = _validate_json_schema(schema, "测试位置")
        assert errors == []
    
    def test_validate_json_schema_invalid_type(self):
        """测试无效的 schema type"""
        schema = {
            "type": "invalid_type"
        }
        
        errors = _validate_json_schema(schema, "步骤 1")
        assert len(errors) == 1
        assert "type 'invalid_type' 无效" in errors[0]
        assert "object, array, string, number" in errors[0]
    
    def test_validate_json_schema_properties_not_dict(self):
        """测试 properties 不是字典"""
        schema = {
            "type": "object",
            "properties": "not_a_dict"
        }
        
        errors = _validate_json_schema(schema, "步骤 2")
        assert len(errors) == 1
        assert "'properties' 必须是字典" in errors[0]
    
    def test_validate_json_schema_required_not_list(self):
        """测试 required 不是列表"""
        schema = {
            "type": "object",
            "required": "not_a_list"
        }
        
        errors = _validate_json_schema(schema, "步骤 3")
        assert len(errors) == 1
        assert "'required' 必须是列表" in errors[0]
    
    def test_validate_json_schema_required_items_not_strings(self):
        """测试 required 列表项不是字符串"""
        schema = {
            "type": "object",
            "required": ["valid", 123, "another"]
        }
        
        errors = _validate_json_schema(schema, "步骤 4")
        assert len(errors) == 1
        assert "'required' 列表中的所有项必须是字符串" in errors[0]
    
    def test_validate_json_schema_items_not_dict(self):
        """测试 array 的 items 不是字典"""
        schema = {
            "type": "array",
            "items": "not_a_dict"
        }
        
        errors = _validate_json_schema(schema, "步骤 5")
        assert len(errors) == 1
        assert "'items' 必须是字典" in errors[0]


class TestCircularDependencyDetection:
    """测试循环依赖检测"""
    
    def test_no_circular_dependency(self):
        """测试没有循环依赖的配置"""
        config = PipelineConfig(
            id="test",
            name="Test",
            steps=[
                StepConfig(
                    id="step1",
                    agent="agent1",
                    flow="flow1",
                    output_key="output1",
                    input_mapping={}
                ),
                StepConfig(
                    id="step2",
                    agent="agent2",
                    flow="flow2",
                    output_key="output2",
                    input_mapping={"input": "output1"}
                ),
                StepConfig(
                    id="step3",
                    agent="agent3",
                    flow="flow3",
                    output_key="output3",
                    input_mapping={"input": "output2"}
                )
            ]
        )
        
        with patch('src.pipeline_config.list_available_agents') as mock_list_agents, \
             patch('src.pipeline_config.load_agent') as mock_load_agent:
            
            mock_list_agents.return_value = ["agent1", "agent2", "agent3"]
            mock_agent = Mock()
            mock_agent.flows = [Mock(name="flow1"), Mock(name="flow2"), Mock(name="flow3")]
            mock_load_agent.return_value = mock_agent
            
            validator = PipelineValidator()
            errors = validator.detect_circular_dependencies(config)
            
            assert errors == []
    
    def test_simple_circular_dependency(self):
        """测试简单的循环依赖 (A -> B -> A)"""
        config = PipelineConfig(
            id="test",
            name="Test",
            steps=[
                StepConfig(
                    id="step1",
                    agent="agent1",
                    flow="flow1",
                    output_key="output1",
                    input_mapping={"input": "output2"}  # 依赖 step2
                ),
                StepConfig(
                    id="step2",
                    agent="agent2",
                    flow="flow2",
                    output_key="output2",
                    input_mapping={"input": "output1"}  # 依赖 step1
                )
            ]
        )
        
        with patch('src.pipeline_config.list_available_agents') as mock_list_agents, \
             patch('src.pipeline_config.load_agent') as mock_load_agent:
            
            mock_list_agents.return_value = ["agent1", "agent2"]
            mock_agent = Mock()
            mock_agent.flows = [Mock(name="flow1"), Mock(name="flow2")]
            mock_load_agent.return_value = mock_agent
            
            validator = PipelineValidator()
            errors = validator.detect_circular_dependencies(config)
            
            assert len(errors) == 1
            assert "检测到循环依赖" in errors[0]
            assert "循环路径" in errors[0]
    
    def test_complex_circular_dependency(self):
        """测试复杂的循环依赖 (A -> B -> C -> A)"""
        config = PipelineConfig(
            id="test",
            name="Test",
            steps=[
                StepConfig(
                    id="step1",
                    agent="agent1",
                    flow="flow1",
                    output_key="output1",
                    input_mapping={"input": "output3"}  # 依赖 step3
                ),
                StepConfig(
                    id="step2",
                    agent="agent2",
                    flow="flow2",
                    output_key="output2",
                    input_mapping={"input": "output1"}  # 依赖 step1
                ),
                StepConfig(
                    id="step3",
                    agent="agent3",
                    flow="flow3",
                    output_key="output3",
                    input_mapping={"input": "output2"}  # 依赖 step2
                )
            ]
        )
        
        with patch('src.pipeline_config.list_available_agents') as mock_list_agents, \
             patch('src.pipeline_config.load_agent') as mock_load_agent:
            
            mock_list_agents.return_value = ["agent1", "agent2", "agent3"]
            mock_agent = Mock()
            mock_agent.flows = [Mock(name="flow1"), Mock(name="flow2"), Mock(name="flow3")]
            mock_load_agent.return_value = mock_agent
            
            validator = PipelineValidator()
            errors = validator.detect_circular_dependencies(config)
            
            assert len(errors) == 1
            assert "检测到循环依赖" in errors[0]
            assert "循环路径" in errors[0]
    
    def test_self_dependency(self):
        """测试自依赖"""
        config = PipelineConfig(
            id="test",
            name="Test",
            steps=[
                StepConfig(
                    id="step1",
                    agent="agent1",
                    flow="flow1",
                    output_key="output1",
                    input_mapping={"input": "output1"}  # 依赖自己
                )
            ]
        )
        
        with patch('src.pipeline_config.list_available_agents') as mock_list_agents, \
             patch('src.pipeline_config.load_agent') as mock_load_agent:
            
            mock_list_agents.return_value = ["agent1"]
            mock_agent = Mock()
            mock_agent.flows = [Mock(name="flow1")]
            mock_load_agent.return_value = mock_agent
            
            validator = PipelineValidator()
            errors = validator.detect_circular_dependencies(config)
            
            assert len(errors) == 1
            assert "不能依赖自己的输出" in errors[0]
            assert "step1" in errors[0]


class TestErrorMessageQuality:
    """测试错误信息的完整性和有用性"""
    
    def test_missing_agent_error_includes_available_options(self):
        """测试缺失 agent 的错误信息包含可用选项"""
        config = PipelineConfig(
            id="test",
            name="Test",
            steps=[
                StepConfig(
                    id="step1",
                    agent="nonexistent_agent",
                    flow="flow1",
                    output_key="output1",
                    input_mapping={}
                )
            ]
        )
        
        with patch('src.pipeline_config.list_available_agents') as mock_list_agents:
            mock_list_agents.return_value = ["agent1", "agent2", "agent3"]
            
            validator = PipelineValidator()
            errors = validator.validate_references(config)
            
            assert len(errors) > 0
            error_msg = errors[0]
            assert "不存在的 agent" in error_msg
            assert "可用的 agents" in error_msg
            assert "agent1" in error_msg
            assert "agent2" in error_msg
            assert "agent3" in error_msg
            assert "修复建议" in error_msg
    
    def test_missing_flow_error_includes_available_options(self):
        """测试缺失 flow 的错误信息包含可用选项"""
        config = PipelineConfig(
            id="test",
            name="Test",
            steps=[
                StepConfig(
                    id="step1",
                    agent="agent1",
                    flow="nonexistent_flow",
                    output_key="output1",
                    input_mapping={}
                )
            ]
        )
        
        with patch('src.pipeline_config.list_available_agents') as mock_list_agents, \
             patch('src.pipeline_config.load_agent') as mock_load_agent:
            
            mock_list_agents.return_value = ["agent1"]
            mock_agent = Mock()
            # Create mock flows with name attribute as string
            flow1 = Mock()
            flow1.name = "flow1"
            flow2 = Mock()
            flow2.name = "flow2"
            mock_agent.flows = [flow1, flow2]
            mock_load_agent.return_value = mock_agent
            
            validator = PipelineValidator()
            errors = validator.validate_references(config)
            
            assert len(errors) > 0
            # Find the error about missing flow (skip circular dependency errors)
            flow_errors = [e for e in errors if "不存在的 flow" in e]
            assert len(flow_errors) > 0
            error_msg = flow_errors[0]
            assert "可用的 flows" in error_msg
            assert "flow1" in error_msg
            assert "flow2" in error_msg
            assert "修复建议" in error_msg
    
    def test_missing_testset_error_includes_available_options(self):
        """测试缺失测试集的错误信息包含可用选项"""
        config = PipelineConfig(
            id="test_pipeline",
            name="Test",
            default_testset="nonexistent.jsonl",
            steps=[
                StepConfig(
                    id="step1",
                    agent="agent1",
                    flow="flow1",
                    output_key="output1",
                    input_mapping={}
                )
            ]
        )
        
        with patch('src.pipeline_config.list_available_agents') as mock_list_agents, \
             patch('src.pipeline_config.load_agent') as mock_load_agent:
            
            mock_list_agents.return_value = ["agent1"]
            mock_agent = Mock()
            # Create mock flow with name attribute as string
            flow1 = Mock()
            flow1.name = "flow1"
            mock_agent.flows = [flow1]
            mock_load_agent.return_value = mock_agent
            
            validator = PipelineValidator()
            
            # 模拟测试集目录和文件
            with patch.object(validator, '_resolve_testset_path') as mock_resolve, \
                 patch('pathlib.Path.exists') as mock_exists, \
                 patch('pathlib.Path.glob') as mock_glob:
                
                mock_path = Mock()
                mock_path.exists.return_value = False
                mock_resolve.return_value = mock_path
                
                mock_exists.return_value = True
                # Create mock files with name attribute
                file1 = Mock()
                file1.name = "test1.jsonl"
                file2 = Mock()
                file2.name = "test2.jsonl"
                mock_glob.return_value = [file1, file2]
                
                errors = validator.validate_references(config)
                
                assert len(errors) > 0
                # Find the testset error (skip other errors)
                testset_errors = [e for e in errors if "测试集文件不存在" in e]
                assert len(testset_errors) > 0
                error_msg = testset_errors[0]
                assert "可用的测试集" in error_msg
                assert "修复建议" in error_msg
    
    def test_circular_dependency_error_shows_path(self):
        """测试循环依赖错误显示循环路径"""
        config = PipelineConfig(
            id="test",
            name="Test",
            steps=[
                StepConfig(
                    id="step1",
                    agent="agent1",
                    flow="flow1",
                    output_key="output1",
                    input_mapping={"input": "output2"}
                ),
                StepConfig(
                    id="step2",
                    agent="agent2",
                    flow="flow2",
                    output_key="output2",
                    input_mapping={"input": "output1"}
                )
            ]
        )
        
        with patch('src.pipeline_config.list_available_agents') as mock_list_agents, \
             patch('src.pipeline_config.load_agent') as mock_load_agent:
            
            mock_list_agents.return_value = ["agent1", "agent2"]
            mock_agent = Mock()
            mock_agent.flows = [Mock(name="flow1"), Mock(name="flow2")]
            mock_load_agent.return_value = mock_agent
            
            validator = PipelineValidator()
            errors = validator.detect_circular_dependencies(config)
            
            assert len(errors) > 0
            error_msg = errors[0]
            assert "检测到循环依赖" in error_msg
            assert "循环路径" in error_msg
            assert "->" in error_msg  # 路径分隔符
            assert "修复建议" in error_msg


class TestFormatValidationErrors:
    """测试错误格式化函数"""
    
    def test_format_no_errors(self):
        """测试没有错误时的格式化"""
        result = format_validation_errors([])
        assert "✅" in result
        assert "验证通过" in result
    
    def test_format_single_error(self):
        """测试单个错误的格式化"""
        errors = ["配置错误: 缺少必需字段"]
        result = format_validation_errors(errors)
        
        assert "❌" in result
        assert "1 个错误" in result
        assert "配置错误: 缺少必需字段" in result
    
    def test_format_multiple_errors(self):
        """测试多个错误的格式化"""
        errors = [
            "错误 1: 缺少字段",
            "错误 2: 类型不匹配",
            "错误 3: 引用无效"
        ]
        result = format_validation_errors(errors)
        
        assert "❌" in result
        assert "3 个错误" in result
        assert "错误 1" in result
        assert "错误 2" in result
        assert "错误 3" in result
    
    def test_format_with_file_path(self):
        """测试包含文件路径的格式化"""
        errors = ["配置错误"]
        file_path = Path("/path/to/config.yaml")
        result = format_validation_errors(errors, file_path)
        
        assert "📄" in result
        assert str(file_path) in result
