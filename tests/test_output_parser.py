# tests/test_output_parser.py
"""
Output Parser 单元测试

测试 OutputParserFactory 和相关功能，包括：
- 创建各种类型的 parser
- JSON parser 解析成功和失败场景
- Pydantic parser 验证
- 重试机制
- 向后兼容性
"""

import pytest
from typing import Dict, Any
from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage

from src.models import OutputParserConfig
from src.output_parser import OutputParserFactory, RetryOutputParser
from langchain_core.output_parsers import (
    JsonOutputParser,
    PydanticOutputParser,
    CommaSeparatedListOutputParser,
    StrOutputParser
)


class TestOutputParserConfig:
    """测试 OutputParserConfig 数据模型"""
    
    def test_output_parser_config_creation(self):
        """测试 OutputParserConfig 创建"""
        config = OutputParserConfig(
            type="json",
            schema={"type": "object", "properties": {"score": {"type": "number"}}},
            retry_on_error=True,
            max_retries=3
        )
        
        assert config.type == "json"
        assert config.schema is not None
        assert config.retry_on_error is True
        assert config.max_retries == 3
    
    def test_output_parser_config_from_dict(self):
        """测试从字典创建 OutputParserConfig"""
        data = {
            "type": "json",
            "schema": {"type": "object"},
            "retry_on_error": True,
            "max_retries": 2
        }
        
        config = OutputParserConfig.from_dict(data)
        
        assert config.type == "json"
        assert config.schema == {"type": "object"}
        assert config.retry_on_error is True
        assert config.max_retries == 2
    
    def test_output_parser_config_to_dict(self):
        """测试 OutputParserConfig 转换为字典"""
        config = OutputParserConfig(
            type="json",
            schema={"type": "object"},
            retry_on_error=False,
            max_retries=5
        )
        
        result = config.to_dict()
        
        assert result["type"] == "json"
        assert result["schema"] == {"type": "object"}
        assert result["retry_on_error"] is False
        assert result["max_retries"] == 5
    
    def test_output_parser_config_validate_success(self):
        """测试成功的配置验证"""
        config = OutputParserConfig(
            type="json",
            schema={"type": "object"},
            retry_on_error=True,
            max_retries=3
        )
        
        errors = config.validate()
        assert errors == []
    
    def test_output_parser_config_validate_invalid_type(self):
        """测试无效的 parser 类型"""
        config = OutputParserConfig(
            type="invalid_type",
            retry_on_error=True,
            max_retries=3
        )
        
        errors = config.validate()
        assert len(errors) > 0
        assert any("不支持的 output parser 类型" in error for error in errors)
    
    def test_output_parser_config_validate_empty_type(self):
        """测试空的 parser 类型"""
        config = OutputParserConfig(
            type="",
            retry_on_error=True,
            max_retries=3
        )
        
        errors = config.validate()
        assert len(errors) > 0
        assert any("不能为空" in error for error in errors)
    
    def test_output_parser_config_validate_negative_retries(self):
        """测试负数重试次数"""
        config = OutputParserConfig(
            type="json",
            retry_on_error=True,
            max_retries=-1
        )
        
        errors = config.validate()
        assert len(errors) > 0
        assert any("max_retries 必须是非负整数" in error for error in errors)
    
    def test_output_parser_config_validate_pydantic_missing_model(self):
        """测试 Pydantic parser 缺少模型"""
        config = OutputParserConfig(
            type="pydantic",
            pydantic_model=None,
            retry_on_error=True,
            max_retries=3
        )
        
        errors = config.validate()
        assert len(errors) > 0
        assert any("必须指定 pydantic_model" in error for error in errors)


class TestOutputParserFactory:
    """测试 OutputParserFactory 工厂类"""
    
    def test_create_json_parser(self):
        """测试创建 JSON parser"""
        config = OutputParserConfig(type="json")
        parser = OutputParserFactory.create_parser(config)
        
        assert isinstance(parser, JsonOutputParser)
    
    def test_create_json_parser_with_schema(self):
        """测试创建带 schema 的 JSON parser"""
        config = OutputParserConfig(
            type="json",
            schema={"type": "object", "properties": {"score": {"type": "number"}}}
        )
        parser = OutputParserFactory.create_parser(config)
        
        assert isinstance(parser, JsonOutputParser)
    
    def test_create_list_parser(self):
        """测试创建 List parser"""
        config = OutputParserConfig(type="list")
        parser = OutputParserFactory.create_parser(config)
        
        assert isinstance(parser, CommaSeparatedListOutputParser)
    
    def test_create_none_parser(self):
        """测试创建 None parser（字符串 parser）"""
        config = OutputParserConfig(type="none")
        parser = OutputParserFactory.create_parser(config)
        
        assert isinstance(parser, StrOutputParser)
    
    def test_create_pydantic_parser_raises_not_implemented(self):
        """测试创建 Pydantic parser 抛出 NotImplementedError"""
        config = OutputParserConfig(
            type="pydantic",
            pydantic_model="SomeModel"
        )
        
        with pytest.raises(NotImplementedError) as exc_info:
            OutputParserFactory.create_parser(config)
        
        assert "Pydantic parser requires a Pydantic model class" in str(exc_info.value)
    
    def test_create_pydantic_parser_with_class(self):
        """测试使用 Pydantic 类创建 parser"""
        
        class TestModel(BaseModel):
            score: float
            comment: str
        
        parser = OutputParserFactory.create_pydantic_parser(TestModel)
        
        assert isinstance(parser, PydanticOutputParser)
    
    def test_create_parser_with_invalid_config(self):
        """测试使用无效配置创建 parser"""
        config = OutputParserConfig(type="invalid_type")
        
        with pytest.raises(ValueError) as exc_info:
            OutputParserFactory.create_parser(config)
        
        assert "Invalid OutputParserConfig" in str(exc_info.value)
    
    def test_create_retry_parser(self):
        """测试创建带重试的 parser"""
        base_parser = JsonOutputParser()
        retry_parser = OutputParserFactory.create_retry_parser(
            parser=base_parser,
            max_retries=3
        )
        
        assert isinstance(retry_parser, RetryOutputParser)
        assert retry_parser.max_retries == 3
    
    def test_create_parser_from_config_without_retry(self):
        """测试从配置创建 parser（不带重试）"""
        config = OutputParserConfig(
            type="json",
            retry_on_error=False
        )
        
        parser = OutputParserFactory.create_parser_from_config(config)
        
        assert isinstance(parser, JsonOutputParser)
        assert not isinstance(parser, RetryOutputParser)
    
    def test_create_parser_from_config_with_retry(self):
        """测试从配置创建 parser（带重试）"""
        config = OutputParserConfig(
            type="json",
            retry_on_error=True,
            max_retries=3
        )
        
        parser = OutputParserFactory.create_parser_from_config(config)
        
        assert isinstance(parser, RetryOutputParser)
        assert parser.max_retries == 3
    
    def test_create_parser_from_config_pydantic_with_class(self):
        """测试从配置创建 Pydantic parser"""
        
        class TestModel(BaseModel):
            score: float
            comment: str
        
        config = OutputParserConfig(
            type="pydantic",
            pydantic_model="TestModel",
            retry_on_error=False
        )
        
        parser = OutputParserFactory.create_parser_from_config(
            config,
            pydantic_class=TestModel
        )
        
        assert isinstance(parser, PydanticOutputParser)
    
    def test_create_parser_from_config_pydantic_without_class(self):
        """测试从配置创建 Pydantic parser 但未提供类"""
        config = OutputParserConfig(
            type="pydantic",
            pydantic_model="TestModel"
        )
        
        with pytest.raises(ValueError) as exc_info:
            OutputParserFactory.create_parser_from_config(config)
        
        assert "requires pydantic_class parameter" in str(exc_info.value)


class TestJsonParser:
    """测试 JSON Parser 功能"""
    
    def test_json_parser_parse_success(self):
        """测试 JSON parser 成功解析"""
        parser = JsonOutputParser()
        
        json_text = '{"score": 8.5, "comment": "Good work"}'
        result = parser.parse(json_text)
        
        assert isinstance(result, dict)
        assert result["score"] == 8.5
        assert result["comment"] == "Good work"
    
    def test_json_parser_parse_complex_object(self):
        """测试 JSON parser 解析复杂对象"""
        parser = JsonOutputParser()
        
        json_text = '''
        {
            "overall_score": 9.0,
            "must_have_check": [
                {"item": "requirement1", "satisfied": true},
                {"item": "requirement2", "satisfied": false}
            ],
            "overall_comment": "Mostly good"
        }
        '''
        
        result = parser.parse(json_text)
        
        assert isinstance(result, dict)
        assert result["overall_score"] == 9.0
        assert len(result["must_have_check"]) == 2
        assert result["must_have_check"][0]["satisfied"] is True
    
    def test_json_parser_handles_malformed_json(self):
        """测试 JSON parser 处理格式不完整的 JSON
        
        注意：LangChain 的 JsonOutputParser 实际上相当宽容，
        可以处理一些格式不完整的 JSON（例如缺少结束括号）。
        这是一个特性，不是 bug，因为它使用了更智能的解析策略。
        """
        parser = JsonOutputParser()
        
        # 这个 JSON 缺少结束括号，但 JsonOutputParser 可以处理
        incomplete_json = '{"score": 8.5, "comment": "Missing closing brace"'
        result = parser.parse(incomplete_json)
        
        # 验证它成功解析了
        assert isinstance(result, dict)
        assert "score" in result
        assert result["score"] == 8.5
    
    def test_json_parser_parse_from_ai_message(self):
        """测试 JSON parser 从 AIMessage 解析"""
        parser = JsonOutputParser()
        
        message = AIMessage(content='{"score": 7.5, "comment": "Acceptable"}')
        result = parser.parse(message.content)
        
        assert isinstance(result, dict)
        assert result["score"] == 7.5


class TestPydanticParser:
    """测试 Pydantic Parser 功能"""
    
    def test_pydantic_parser_parse_success(self):
        """测试 Pydantic parser 成功解析和验证"""
        
        class JudgeOutput(BaseModel):
            overall_score: float = Field(ge=0, le=10)
            overall_comment: str
        
        parser = PydanticOutputParser(pydantic_object=JudgeOutput)
        
        json_text = '{"overall_score": 8.5, "overall_comment": "Good work"}'
        result = parser.parse(json_text)
        
        assert isinstance(result, JudgeOutput)
        assert result.overall_score == 8.5
        assert result.overall_comment == "Good work"
    
    def test_pydantic_parser_validation_failure(self):
        """测试 Pydantic parser 验证失败"""
        
        class JudgeOutput(BaseModel):
            overall_score: float = Field(ge=0, le=10)
            overall_comment: str
        
        parser = PydanticOutputParser(pydantic_object=JudgeOutput)
        
        # Score out of range
        json_text = '{"overall_score": 15.0, "overall_comment": "Too high"}'
        
        with pytest.raises(Exception):
            parser.parse(json_text)
    
    def test_pydantic_parser_missing_required_field(self):
        """测试 Pydantic parser 缺少必需字段"""
        
        class JudgeOutput(BaseModel):
            overall_score: float
            overall_comment: str
        
        parser = PydanticOutputParser(pydantic_object=JudgeOutput)
        
        # Missing overall_comment
        json_text = '{"overall_score": 8.5}'
        
        with pytest.raises(Exception):
            parser.parse(json_text)


class TestRetryOutputParser:
    """测试 RetryOutputParser 重试机制"""
    
    def test_retry_parser_success_first_attempt(self):
        """测试重试 parser 第一次尝试成功"""
        base_parser = JsonOutputParser()
        retry_parser = RetryOutputParser(parser=base_parser, max_retries=3)
        
        json_text = '{"score": 8.5, "comment": "Good"}'
        result = retry_parser.parse(json_text)
        
        assert isinstance(result, dict)
        assert result["score"] == 8.5
        assert retry_parser.get_retry_count() == 0
    
    def test_retry_parser_parse_from_ai_message(self):
        """测试重试 parser 从 AIMessage 解析"""
        base_parser = JsonOutputParser()
        retry_parser = RetryOutputParser(parser=base_parser, max_retries=3)
        
        message = AIMessage(content='{"score": 7.5, "comment": "OK"}')
        result = retry_parser.parse(message)
        
        assert isinstance(result, dict)
        assert result["score"] == 7.5
    
    def test_retry_parser_with_pydantic_validation_failure(self):
        """测试重试 parser 在 Pydantic 验证失败时的行为
        
        使用 Pydantic parser 来测试重试机制，因为它有更严格的验证。
        """
        from pydantic import BaseModel, Field
        
        class StrictModel(BaseModel):
            score: float = Field(ge=0, le=10)
            comment: str
        
        base_parser = PydanticOutputParser(pydantic_object=StrictModel)
        retry_parser = RetryOutputParser(parser=base_parser, max_retries=2)
        
        # Score 超出范围，会导致验证失败
        invalid_json = '{"score": 15.0, "comment": "Out of range"}'
        
        with pytest.raises(Exception):
            retry_parser.parse(invalid_json)
        
        # 应该尝试了 max_retries 次
        assert retry_parser.get_retry_count() == 2
    
    def test_retry_parser_get_format_instructions(self):
        """测试重试 parser 获取格式说明"""
        base_parser = JsonOutputParser()
        retry_parser = RetryOutputParser(parser=base_parser, max_retries=3)
        
        instructions = retry_parser.get_format_instructions()
        
        assert isinstance(instructions, str)
        assert len(instructions) > 0
    
    def test_retry_parser_callable(self):
        """测试重试 parser 可调用"""
        base_parser = JsonOutputParser()
        retry_parser = RetryOutputParser(parser=base_parser, max_retries=3)
        
        json_text = '{"score": 9.0, "comment": "Excellent"}'
        result = retry_parser(json_text)
        
        assert isinstance(result, dict)
        assert result["score"] == 9.0


class TestListParser:
    """测试 List Parser 功能"""
    
    def test_list_parser_parse_success(self):
        """测试 List parser 成功解析"""
        parser = CommaSeparatedListOutputParser()
        
        text = "apple, banana, orange"
        result = parser.parse(text)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert "apple" in result
        assert "banana" in result
        assert "orange" in result
    
    def test_list_parser_parse_single_item(self):
        """测试 List parser 解析单个项目"""
        parser = CommaSeparatedListOutputParser()
        
        text = "single_item"
        result = parser.parse(text)
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == "single_item"


class TestBackwardCompatibility:
    """测试向后兼容性"""
    
    def test_none_parser_returns_string(self):
        """测试 None parser 返回字符串（向后兼容）"""
        config = OutputParserConfig(type="none")
        parser = OutputParserFactory.create_parser(config)
        
        text = "This is a plain text output"
        result = parser.parse(text)
        
        assert isinstance(result, str)
        assert result == text
    
    def test_str_parser_with_ai_message(self):
        """测试字符串 parser 处理 AIMessage"""
        parser = StrOutputParser()
        
        message = AIMessage(content="This is the response")
        # StrOutputParser's invoke method handles AIMessage, but parse expects string
        # Use invoke instead or pass the content directly
        result = parser.invoke(message)
        
        assert isinstance(result, str)
        assert result == "This is the response"
    
    def test_config_without_parser_type_defaults_to_none(self):
        """测试未指定 parser 类型时的默认行为"""
        # 当 type 为 "none" 时，应该返回字符串
        config = OutputParserConfig(type="none")
        parser = OutputParserFactory.create_parser(config)
        
        assert isinstance(parser, StrOutputParser)


class TestIntegrationScenarios:
    """测试集成场景"""
    
    def test_json_parser_with_retry_success(self):
        """测试带重试的 JSON parser 成功场景"""
        config = OutputParserConfig(
            type="json",
            retry_on_error=True,
            max_retries=3
        )
        
        parser = OutputParserFactory.create_parser_from_config(config)
        
        json_text = '{"score": 8.5, "feedback": "Well done"}'
        result = parser.parse(json_text)
        
        assert isinstance(result, dict)
        assert result["score"] == 8.5
        assert result["feedback"] == "Well done"
    
    def test_pydantic_parser_with_retry(self):
        """测试带重试的 Pydantic parser"""
        
        class OutputModel(BaseModel):
            score: float
            feedback: str
        
        config = OutputParserConfig(
            type="pydantic",
            pydantic_model="OutputModel",
            retry_on_error=True,
            max_retries=2
        )
        
        parser = OutputParserFactory.create_parser_from_config(
            config,
            pydantic_class=OutputModel
        )
        
        json_text = '{"score": 9.0, "feedback": "Excellent work"}'
        result = parser.parse(json_text)
        
        assert isinstance(result, OutputModel)
        assert result.score == 9.0
        assert result.feedback == "Excellent work"
    
    def test_judge_output_scenario(self):
        """测试 Judge 输出场景"""
        
        class JudgeOutput(BaseModel):
            overall_score: float = Field(ge=0, le=10)
            must_have_check: list
            overall_comment: str
        
        config = OutputParserConfig(
            type="pydantic",
            pydantic_model="JudgeOutput",
            retry_on_error=True,
            max_retries=3
        )
        
        parser = OutputParserFactory.create_parser_from_config(
            config,
            pydantic_class=JudgeOutput
        )
        
        json_text = '''
        {
            "overall_score": 8.5,
            "must_have_check": [
                {"item": "req1", "satisfied": true},
                {"item": "req2", "satisfied": true}
            ],
            "overall_comment": "Good implementation"
        }
        '''
        
        result = parser.parse(json_text)
        
        assert isinstance(result, JudgeOutput)
        assert result.overall_score == 8.5
        assert len(result.must_have_check) == 2
        assert result.overall_comment == "Good implementation"
