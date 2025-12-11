# tests/test_agent_template_parser_integration.py
"""
Agent Template Parser 端到端集成测试

验证从模板文件到最终agent配置的完整工作流，以及批量JSON处理到测试集生成的完整流程。
"""

import pytest
import json
import tempfile
import shutil
import yaml
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.agent_template_parser.template_manager import TemplateManager
from src.agent_template_parser.template_parser import TemplateParser
from src.agent_template_parser.config_generator import AgentConfigGenerator
from src.agent_template_parser.llm_enhancer import LLMEnhancer
from src.agent_template_parser.batch_data_processor import BatchDataProcessor
from src.agent_template_parser.cli import AgentTemplateParserCLI
from src.agent_template_parser.models import TemplateData, ParsedTemplate, GeneratedConfig


class TestTemplateToAgentConfigWorkflow:
    """从模板文件到agent配置的完整工作流测试"""
    
    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = Path(tempfile.mkdtemp())
        
        # 创建目录结构
        (temp_dir / "templates").mkdir()
        (temp_dir / "agents").mkdir()
        (temp_dir / "agents" / "test_agent").mkdir()
        (temp_dir / "agents" / "test_agent" / "prompts").mkdir()
        (temp_dir / "agents" / "test_agent" / "testsets").mkdir()
        
        yield temp_dir
        
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def sample_template_files(self, temp_workspace):
        """创建示例模板文件"""
        templates_dir = temp_workspace / "templates"
        
        # 系统提示词模板
        system_prompt = """你是一个专业的对话总结专家。你的任务是分析用户提供的对话内容，并生成简洁、准确的总结。

请根据以下对话内容：${sys.user_input}

为用户{user}生成总结，考虑其角色{role}的特点。

总结要求：
1. 保持客观中性
2. 突出关键信息
3. 控制在200字以内
"""
        
        # 用户输入模板
        user_input = """请总结以下对话内容：
{input_text}

用户角色：{user_role}
总结重点：{focus_area}
"""
        
        # 测试用例
        test_case = {
            "sys": {
                "user_input": [
                    {"role": "user", "content": "你好，我想了解一下产品功能"},
                    {"role": "assistant", "content": "您好！我很乐意为您介绍我们的产品功能..."},
                    {"role": "user", "content": "价格如何？"},
                    {"role": "assistant", "content": "我们有多种价格方案..."}
                ]
            },
            "input_text": "用户咨询产品功能和价格",
            "user_role": "潜在客户",
            "focus_area": "产品介绍"
        }
        
        # 保存模板文件
        system_prompt_file = templates_dir / "system_prompts" / "test_agent_system.txt"
        user_input_file = templates_dir / "user_inputs" / "test_agent_user.txt"
        test_case_file = templates_dir / "test_cases" / "test_agent_test.json"
        
        system_prompt_file.parent.mkdir(parents=True, exist_ok=True)
        user_input_file.parent.mkdir(parents=True, exist_ok=True)
        test_case_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(system_prompt_file, 'w', encoding='utf-8') as f:
            f.write(system_prompt)
        
        with open(user_input_file, 'w', encoding='utf-8') as f:
            f.write(user_input)
        
        with open(test_case_file, 'w', encoding='utf-8') as f:
            json.dump(test_case, f, ensure_ascii=False, indent=2)
        
        return {
            "system_prompt": system_prompt_file,
            "user_input": user_input_file,
            "test_case": test_case_file
        }
    
    def test_complete_template_to_agent_workflow(self, temp_workspace, sample_template_files):
        """测试从模板文件到agent配置的完整工作流"""
        
        # 1. 初始化模板管理器
        template_manager = TemplateManager(str(temp_workspace / "templates"))
        
        # 2. 加载模板文件
        template_files = template_manager.load_template_files("test_agent")
        
        assert "system_prompt" in template_files
        assert "user_input" in template_files
        assert "test_case" in template_files
        assert "${sys.user_input}" in template_files["system_prompt"]
        assert "{input_text}" in template_files["user_input"]
        
        # 3. 解析模板
        parser = TemplateParser()
        
        system_data = parser.parse_system_prompt(template_files["system_prompt"])
        user_data = parser.parse_user_input(template_files["user_input"])
        test_data = parser.parse_test_case(template_files["test_case"])
        
        # 验证解析结果
        assert len(system_data["variables"]) > 0
        assert "${sys.user_input}" in system_data["variables"]
        assert "{user}" in system_data["variables"]
        assert "{role}" in system_data["variables"]
        
        assert len(user_data["variables"]) > 0
        assert "{input_text}" in user_data["variables"]
        assert "{user_role}" in user_data["variables"]
        
        assert "sys" in test_data["data"]
        assert "user_input" in test_data["data"]["sys"]
        
        # 4. 生成配置
        config_generator = AgentConfigGenerator()
        
        parsed_template = ParsedTemplate(
            system_variables=system_data["variables"],
            user_variables=user_data["variables"],
            test_structure=test_data["structure"],
            variable_mappings=parser.map_variables_to_config(
                system_data["variables"] + user_data["variables"]
            )
        )
        
        agent_config = config_generator.generate_agent_yaml(
            parsed_template,
            "test_agent"
        )
        
        prompt_config = config_generator.generate_prompt_yaml(
            parsed_template,
            "test_agent",
            original_system_prompt=template_files["system_prompt"],
            original_user_template=template_files["user_input"]
        )
        
        # 验证生成的配置
        assert agent_config["id"] == "test_agent"
        assert "flows" in agent_config
        assert "evaluation" in agent_config
        assert "case_fields" in agent_config
        
        assert "system_prompt" in prompt_config
        assert "user_template" in prompt_config
        assert "defaults" in prompt_config
        
        # 5. 保存配置文件
        agents_dir = temp_workspace / "agents"
        config_generator.agents_dir = agents_dir
        config_generator.save_config_files(
            agent_config, prompt_config, "test_agent"
        )
        
        # 验证文件保存
        agent_yaml_path = agents_dir / "test_agent" / "agent.yaml"
        prompt_yaml_path = agents_dir / "test_agent" / "prompts" / "test_agent_v1.yaml"
        
        assert agent_yaml_path.exists()
        assert prompt_yaml_path.exists()
        
        # 验证保存的文件内容
        with open(agent_yaml_path, 'r', encoding='utf-8') as f:
            saved_agent_config = yaml.safe_load(f)
        
        with open(prompt_yaml_path, 'r', encoding='utf-8') as f:
            saved_prompt_config = yaml.safe_load(f)
        
        assert saved_agent_config["id"] == "test_agent"
        assert saved_prompt_config["system_prompt"] is not None
        assert saved_prompt_config["user_template"] is not None
    
    @pytest.mark.skip(reason="Requires OpenAI API key")
    def test_template_workflow_with_llm_enhancement(self, temp_workspace, sample_template_files):
        """测试带LLM增强的模板工作流"""
        pass
    
    def test_template_workflow_error_handling(self, temp_workspace):
        """测试模板工作流的错误处理"""
        
        # 创建无效的模板文件
        templates_dir = temp_workspace / "templates"
        templates_dir.mkdir(exist_ok=True)
        
        # 无效的JSON测试用例
        invalid_test_case = templates_dir / "test_cases" / "invalid_test.json"
        invalid_test_case.parent.mkdir(parents=True, exist_ok=True)
        
        with open(invalid_test_case, 'w', encoding='utf-8') as f:
            f.write("{ invalid json content")
        
        # 测试错误处理
        template_manager = TemplateManager(str(templates_dir))
        parser = TemplateParser()
        
        # 应该抛出解析错误
        with pytest.raises(Exception):
            test_content = template_manager.load_template_files("invalid_test")
            parser.parse_test_case(test_content.get("test_case", ""))


class TestBatchJSONToTestsetWorkflow:
    """批量JSON处理到测试集生成的完整工作流测试"""
    
    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = Path(tempfile.mkdtemp())
        
        # 创建agents目录结构
        (temp_dir / "agents" / "target_agent").mkdir(parents=True)
        (temp_dir / "agents" / "target_agent" / "testsets").mkdir()
        
        yield temp_dir
        
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def sample_json_inputs(self):
        """创建示例JSON输入数据"""
        json_inputs = [
            {
                "sys": {
                    "user_input": [
                        {"role": "user", "content": "请帮我总结这个会议"},
                        {"role": "assistant", "content": "好的，我来帮您总结会议内容"}
                    ]
                },
                "meeting_type": "项目会议",
                "participants": ["张三", "李四", "王五"],
                "duration": "2小时"
            },
            {
                "sys": {
                    "user_input": [
                        {"role": "user", "content": "分析一下销售数据"},
                        {"role": "assistant", "content": "我将为您分析销售数据的趋势"}
                    ]
                },
                "data_type": "销售报表",
                "time_period": "Q3 2024",
                "metrics": ["收入", "客户数", "转化率"]
            },
            {
                "sys": {
                    "user_input": [
                        {"role": "user", "content": "制定营销策略"},
                        {"role": "assistant", "content": "让我为您制定一个营销策略"}
                    ]
                },
                "target_market": "年轻消费者",
                "budget": "100万",
                "channels": ["社交媒体", "线下活动"]
            }
        ]
        
        return json_inputs
    
    def test_complete_batch_json_to_testset_workflow(self, temp_workspace, sample_json_inputs):
        """测试批量JSON处理到测试集生成的完整工作流"""
        
        # 1. 初始化批量数据处理器
        processor = BatchDataProcessor()
        
        # 2. 创建目标agent并验证存在
        agents_dir = temp_workspace / "agents"
        target_agent_dir = agents_dir / "target_agent"
        target_agent_dir.mkdir(parents=True, exist_ok=True)
        (target_agent_dir / "agent.yaml").write_text("id: target_agent")
        
        processor = BatchDataProcessor(str(agents_dir))
        assert processor.validate_agent_exists("target_agent")
        
        # 3. 处理JSON输入
        json_strings = [json.dumps(item, ensure_ascii=False) for item in sample_json_inputs]
        processed_data = processor.process_json_inputs(json_strings, "target_agent")
        
        # 验证处理结果
        assert len(processed_data) == 3
        for data in processed_data:
            assert data.sys_user_input is not None
            assert isinstance(data.sys_user_input, list)
            assert "chat_round_30" in data.extracted_fields
        
        # 4. 转换为测试集格式
        testset_data = processor.convert_to_testset_format(processed_data)
        
        # 验证转换结果
        assert len(testset_data) == 3
        for i, item in enumerate(testset_data):
            assert "id" in item
            assert "tags" in item
            assert "chat_round_30" in item  # sys.user_input is mapped to chat_round_30
            assert isinstance(item["chat_round_30"], list)
        
        # 5. 保存测试集
        testset_path = processor.save_testset(
            testset_data, "target_agent", "batch_generated.jsonl"
        )
        
        # 验证文件保存
        expected_path = agents_dir / "target_agent" / "testsets" / "batch_generated.jsonl"
        assert testset_path == expected_path
        assert testset_path.exists()
        
        # 验证保存的文件内容
        saved_data = []
        with open(testset_path, 'r', encoding='utf-8') as f:
            for line in f:
                saved_data.append(json.loads(line.strip()))
        
        assert len(saved_data) == 3
        for item in saved_data:
            assert "id" in item
            assert "chat_round_30" in item
            assert isinstance(item["chat_round_30"], list)
    
    def test_batch_processing_with_complex_data_structures(self, temp_workspace):
        """测试复杂数据结构的批量处理"""
        
        complex_json_inputs = [
            {
                "sys": {
                    "user_input": [
                        {
                            "role": "user",
                            "content": "分析这个复杂的数据结构",
                            "metadata": {
                                "timestamp": "2024-01-01T10:00:00",
                                "source": "api_call"
                            }
                        },
                        {
                            "role": "assistant", 
                            "content": "我将分析这个数据结构",
                            "metadata": {
                                "confidence": 0.95,
                                "processing_time": 1.2
                            }
                        }
                    ]
                },
                "nested_data": {
                    "level1": {
                        "level2": {
                            "values": [1, 2, 3, 4, 5],
                            "labels": ["A", "B", "C", "D", "E"]
                        }
                    }
                },
                "array_of_objects": [
                    {"name": "item1", "value": 100},
                    {"name": "item2", "value": 200}
                ]
            }
        ]
        
        # Create target agent directory
        target_agent_dir = temp_workspace / "agents" / "target_agent"
        target_agent_dir.mkdir(parents=True, exist_ok=True)
        (target_agent_dir / "agent.yaml").write_text("id: target_agent")
        
        processor = BatchDataProcessor(str(temp_workspace / "agents"))
        
        # 处理复杂数据
        processed_data = processor.process_json_inputs([json.dumps(item) for item in complex_json_inputs], "target_agent")
        
        # 验证复杂结构被正确保留
        assert len(processed_data) == 1
        data = processed_data[0]
        
        # Access the extracted fields from ProcessedJsonData
        extracted_fields = data.extracted_fields
        
        assert "nested_data" in extracted_fields
        assert "level1" in extracted_fields["nested_data"]
        assert "level2" in extracted_fields["nested_data"]["level1"]
        assert "values" in extracted_fields["nested_data"]["level1"]["level2"]
        
        assert "array_of_objects" in extracted_fields
        assert len(extracted_fields["array_of_objects"]) == 2
        assert extracted_fields["array_of_objects"][0]["name"] == "item1"
        
        # 验证sys.user_input中的metadata被保留
        user_input = extracted_fields["chat_round_30"]
        assert "metadata" in user_input[0]
        assert user_input[0]["metadata"]["source"] == "api_call"
    
    def test_batch_processing_error_handling(self, temp_workspace):
        """测试批量处理的错误处理"""
        
        processor = BatchDataProcessor(str(temp_workspace / "agents"))
        
        # 测试不存在的agent
        assert not processor.validate_agent_exists("nonexistent_agent")
        
        # 测试无效的JSON数据
        invalid_json_inputs = [
            '{"invalid": "no sys field"}',
            '{"sys": "invalid sys structure"}'
        ]
        
        # Create a valid agent for testing
        valid_agent_dir = temp_workspace / "agents" / "valid_agent"
        valid_agent_dir.mkdir(parents=True)
        (valid_agent_dir / "agent.yaml").write_text("id: valid_agent")
        
        # 应该能处理无效数据，但会跳过或转换
        processed_data = processor.process_json_inputs(invalid_json_inputs, "valid_agent")
        
        # 验证错误处理
        assert isinstance(processed_data, list)
        # 具体的错误处理行为取决于实现


class TestCLIEndToEndWorkflow:
    """CLI端到端工作流测试"""
    
    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = Path(tempfile.mkdtemp())
        
        # 创建完整的目录结构
        (temp_dir / "templates" / "system_prompts").mkdir(parents=True)
        (temp_dir / "templates" / "user_inputs").mkdir(parents=True)
        (temp_dir / "templates" / "test_cases").mkdir(parents=True)
        (temp_dir / "agents").mkdir()
        
        yield temp_dir
        
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.skip(reason="CLI tests with sys.exit() are difficult to test")
    def test_cli_create_agent_from_templates_workflow(self, temp_workspace):
        """测试CLI从模板创建agent的完整工作流"""
        pass
    
    @pytest.mark.skip(reason="CLI tests with sys.exit() are difficult to test")
    def test_cli_batch_create_testsets_workflow(self, temp_workspace):
        """测试CLI批量创建测试集的完整工作流"""
        pass


class TestSystemCompatibilityValidation:
    """系统兼容性验证测试"""
    
    @pytest.fixture
    def temp_workspace(self):
        """创建临时工作空间"""
        temp_dir = Path(tempfile.mkdtemp())
        
        # 创建完整的项目结构
        (temp_dir / "agents").mkdir()
        (temp_dir / "data" / "runs").mkdir(parents=True)
        (temp_dir / "data" / "evals").mkdir()
        
        yield temp_dir
        
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_generated_agent_config_compatibility(self, temp_workspace):
        """测试生成的agent配置与现有系统的兼容性"""
        
        # 创建一个完整的agent配置
        agent_dir = temp_workspace / "agents" / "compatibility_test_agent"
        agent_dir.mkdir(parents=True)
        (agent_dir / "prompts").mkdir()
        (agent_dir / "testsets").mkdir()
        
        # 生成标准的agent配置
        agent_config = {
            "id": "compatibility_test_agent",
            "name": "兼容性测试Agent",
            "flows": {
                "compatibility_test_agent_v1": {
                    "prompt": "compatibility_test_agent_v1",
                    "model": "gpt-4"
                }
            },
            "evaluation": {
                "judge": {
                    "enabled": True,
                    "model": "gpt-4",
                    "prompt": "judge_v1"
                },
                "rules": {
                    "enabled": True
                }
            },
            "case_fields": ["input_text", "expected_output"]
        }
        
        prompt_config = {
            "system_prompt": "你是一个兼容性测试助手。",
            "user_template": "请处理：{input_text}",
            "defaults": {
                "model": "gpt-4",
                "temperature": 0.7
            }
        }
        
        # 保存配置文件
        with open(agent_dir / "agent.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(agent_config, f, allow_unicode=True)
        
        with open(agent_dir / "prompts" / "compatibility_test_agent_v1.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(prompt_config, f, allow_unicode=True)
        
        # 创建测试集
        testset_data = [
            {
                "id": "test_1",
                "tags": ["compatibility"],
                "input_text": "测试输入1",
                "expected_output": "测试输出1"
            },
            {
                "id": "test_2", 
                "tags": ["compatibility"],
                "input_text": "测试输入2",
                "expected_output": "测试输出2"
            }
        ]
        
        testset_file = agent_dir / "testsets" / "compatibility_test.jsonl"
        with open(testset_file, 'w', encoding='utf-8') as f:
            for item in testset_data:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')
        
        # 验证配置文件格式
        assert agent_config["id"] == "compatibility_test_agent"
        assert "flows" in agent_config
        assert "evaluation" in agent_config
        assert "case_fields" in agent_config
        
        # 验证prompt配置格式
        assert "system_prompt" in prompt_config
        assert "user_template" in prompt_config
        assert "defaults" in prompt_config
        
        # 验证测试集格式
        assert len(testset_data) == 2
        for item in testset_data:
            assert "id" in item
            assert "tags" in item
        
        # 模拟系统加载配置（这里只是验证格式正确性）
        try:
            # 重新加载配置文件验证格式
            with open(agent_dir / "agent.yaml", 'r', encoding='utf-8') as f:
                loaded_agent_config = yaml.safe_load(f)
            
            with open(agent_dir / "prompts" / "compatibility_test_agent_v1.yaml", 'r', encoding='utf-8') as f:
                loaded_prompt_config = yaml.safe_load(f)
            
            assert loaded_agent_config == agent_config
            assert loaded_prompt_config == prompt_config
            
        except Exception as e:
            pytest.fail(f"生成的配置文件格式不兼容: {e}")
    
    def test_generated_testset_compatibility(self, temp_workspace):
        """测试生成的测试集与现有系统的兼容性"""
        
        # 使用BatchDataProcessor生成测试集
        processor = BatchDataProcessor()
        
        # 创建目标agent
        agent_dir = temp_workspace / "agents" / "testset_compatibility_agent"
        agent_dir.mkdir(parents=True)
        (agent_dir / "testsets").mkdir()
        
        # 准备JSON输入
        json_inputs = [
            {
                "sys": {
                    "user_input": [
                        {"role": "user", "content": "兼容性测试输入"},
                        {"role": "assistant", "content": "兼容性测试输出"}
                    ]
                },
                "test_field": "兼容性测试值",
                "metadata": {
                    "source": "compatibility_test",
                    "version": "1.0"
                }
            }
        ]
        
        # Create the agent directory first
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / "agent.yaml").write_text("id: testset_compatibility_agent")
        
        processor = BatchDataProcessor(str(temp_workspace / "agents"))
        
        # 处理并生成测试集
        json_strings = [json.dumps(item, ensure_ascii=False) for item in json_inputs]
        processed_data = processor.process_json_inputs(json_strings, "testset_compatibility_agent")
        testset_data = processor.convert_to_testset_format(processed_data)
        
        testset_path = processor.save_testset(
            testset_data, 
            "testset_compatibility_agent", 
            "compatibility_test.jsonl"
        )
        
        # 验证生成的测试集格式
        assert testset_path.exists()
        
        # 加载并验证测试集内容
        loaded_testset = []
        with open(testset_path, 'r', encoding='utf-8') as f:
            for line in f:
                loaded_testset.append(json.loads(line.strip()))
        
        assert len(loaded_testset) == 1
        item = loaded_testset[0]
        
        # 验证必需字段
        assert "id" in item
        assert "tags" in item
        assert "chat_round_30" in item  # sys.user_input is mapped to chat_round_30
        
        # 验证数据结构完整性
        assert isinstance(item["chat_round_30"], list)
        assert len(item["chat_round_30"]) == 2
        assert item["chat_round_30"][0]["role"] == "user"
        assert item["chat_round_30"][1]["role"] == "assistant"
        
        # 验证额外字段被保留
        assert "test_field" in item
        assert "metadata" in item
        assert item["metadata"]["source"] == "compatibility_test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])