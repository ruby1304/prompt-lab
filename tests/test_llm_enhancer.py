"""测试LLM增强处理器模块"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
import yaml
from src.agent_template_parser.llm_enhancer import LLMEnhancer, LLMEnhancementError


class TestLLMEnhancer:
    """测试LLMEnhancer类"""
    
    @pytest.fixture
    def enhancer(self):
        """创建LLMEnhancer实例"""
        return LLMEnhancer(model_name="gpt-4", temperature=0.1)
    
    @pytest.fixture
    def sample_config(self):
        """示例配置"""
        return {
            "name": "test_agent",
            "flows": {
                "default": {
                    "prompt": "test_prompt_v1"
                }
            },
            "evaluation": {
                "case_fields": ["input", "output"]
            }
        }
    
    @pytest.fixture
    def sample_errors(self):
        """示例错误列表"""
        return [
            "Missing required field: description",
            "Invalid flow configuration",
            "Incorrect YAML syntax"
        ]
    
    def test_init(self, enhancer):
        """测试初始化"""
        assert enhancer.model_name == "gpt-4"
        assert enhancer.temperature == 0.1
        assert enhancer.max_retries == 3
        assert enhancer.fallback_enabled is True
        assert enhancer._llm is None
    
    def test_init_with_custom_params(self):
        """测试使用自定义参数初始化"""
        enhancer = LLMEnhancer(
            model_name="gpt-3.5-turbo",
            temperature=0.5,
            max_retries=5,
            fallback_enabled=False
        )
        assert enhancer.model_name == "gpt-3.5-turbo"
        assert enhancer.temperature == 0.5
        assert enhancer.max_retries == 5
        assert enhancer.fallback_enabled is False
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch('src.agent_template_parser.llm_enhancer.ChatOpenAI')
    def test_llm_property_lazy_loading(self, mock_chat_openai, enhancer):
        """测试LLM属性的懒加载"""
        mock_llm_instance = Mock()
        mock_chat_openai.return_value = mock_llm_instance
        
        # 第一次访问应该创建实例
        llm = enhancer.llm
        assert llm == mock_llm_instance
        mock_chat_openai.assert_called_once_with(
            model="gpt-4",
            temperature=0.1,
            openai_api_key="test-key"
        )
        
        # 第二次访问应该返回同一个实例
        llm2 = enhancer.llm
        assert llm2 == mock_llm_instance
        assert mock_chat_openai.call_count == 1
    
    def test_llm_property_no_api_key(self, enhancer):
        """测试没有API密钥时的错误处理"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(LLMEnhancementError, match="OPENAI_API_KEY environment variable is required"):
                _ = enhancer.llm
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch('src.agent_template_parser.llm_enhancer.ChatOpenAI')
    def test_fix_config_format_success(self, mock_chat_openai, enhancer, sample_config, sample_errors):
        """测试成功修正配置格式"""
        # 模拟LLM响应
        mock_response = Mock()
        mock_response.content = """```yaml
name: test_agent
description: Test agent description
flows:
  default:
    prompt: test_prompt_v1
evaluation:
  case_fields: ["input", "output"]
```"""
        
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm
        
        # 调用方法
        result = enhancer.fix_config_format(sample_config, sample_errors)
        
        # 验证结果
        assert isinstance(result, dict)
        assert result["name"] == "test_agent"
        assert "description" in result
        assert result["description"] == "Test agent description"
        
        # 验证LLM调用
        mock_llm.invoke.assert_called_once()
        call_args = mock_llm.invoke.call_args[0][0]
        assert len(call_args) == 2  # SystemMessage and HumanMessage
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch('src.agent_template_parser.llm_enhancer.ChatOpenAI')
    def test_fix_config_format_llm_error_with_fallback(self, mock_chat_openai, enhancer, sample_config, sample_errors):
        """测试LLM调用失败但回退成功的情况"""
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("API call failed")
        mock_chat_openai.return_value = mock_llm
        
        # 应该使用回退机制，不抛出异常
        result = enhancer.fix_config_format(sample_config, sample_errors)
        
        # 验证回退结果
        assert isinstance(result, dict)
        assert "description" in result  # 回退应该添加缺失的description字段
        assert result["name"] == sample_config["name"]
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch('src.agent_template_parser.llm_enhancer.ChatOpenAI')
    def test_fix_config_format_llm_error_no_fallback(self, mock_chat_openai, sample_config, sample_errors):
        """测试禁用回退时LLM调用失败的错误处理"""
        enhancer = LLMEnhancer(fallback_enabled=False)
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("API call failed")
        mock_chat_openai.return_value = mock_llm
        
        with pytest.raises(LLMEnhancementError, match="Failed to fix config format"):
            enhancer.fix_config_format(sample_config, sample_errors)
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch('src.agent_template_parser.llm_enhancer.ChatOpenAI')
    def test_optimize_config_success(self, mock_chat_openai, enhancer, sample_config):
        """测试成功优化配置"""
        mock_response = Mock()
        mock_response.content = """```yaml
name: test_agent
description: Optimized test agent
flows:
  default:
    prompt: test_prompt_v1
    timeout: 30
evaluation:
  case_fields: ["input", "output"]
  metrics: ["accuracy", "relevance"]
```"""
        
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm
        
        result = enhancer.optimize_config(sample_config)
        
        assert isinstance(result, dict)
        assert result["name"] == "test_agent"
        assert "description" in result
        assert "timeout" in result["flows"]["default"]
        assert "metrics" in result["evaluation"]
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch('src.agent_template_parser.llm_enhancer.ChatOpenAI')
    def test_generate_improvement_suggestions_success(self, mock_chat_openai, enhancer, sample_config):
        """测试成功生成改进建议"""
        mock_response = Mock()
        mock_response.content = """- 添加agent描述字段以提高可读性
- 为flows配置添加超时设置
- 增加更多评估指标
- 考虑添加错误处理配置"""
        
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm
        
        result = enhancer.generate_improvement_suggestions(sample_config)
        
        assert isinstance(result, list)
        assert len(result) == 4
        assert "添加agent描述字段以提高可读性" in result
        assert "为flows配置添加超时设置" in result
    
    def test_parse_llm_response_with_yaml_block(self, enhancer):
        """测试解析包含YAML代码块的响应"""
        response = """这是修正后的配置：

```yaml
name: test_agent
description: Test description
```

配置已经修正完成。"""
        
        result = enhancer._parse_llm_response(response)
        
        assert isinstance(result, dict)
        assert result["name"] == "test_agent"
        assert result["description"] == "Test description"
    
    def test_parse_llm_response_without_yaml_block(self, enhancer):
        """测试解析不包含YAML代码块的响应"""
        response = """name: test_agent
description: Test description"""
        
        result = enhancer._parse_llm_response(response)
        
        assert isinstance(result, dict)
        assert result["name"] == "test_agent"
        assert result["description"] == "Test description"
    
    def test_parse_llm_response_invalid_yaml(self, enhancer):
        """测试解析无效YAML的错误处理"""
        response = """```yaml
name: test_agent
  invalid: yaml: syntax
```"""
        
        with pytest.raises(LLMEnhancementError, match="Failed to parse LLM response"):
            enhancer._parse_llm_response(response)
    
    def test_parse_suggestions_response_with_dashes(self, enhancer):
        """测试解析带破折号的建议响应"""
        response = """- 第一个建议
- 第二个建议
- 第三个建议"""
        
        result = enhancer._parse_suggestions_response(response)
        
        assert isinstance(result, list)
        assert len(result) == 3
        assert result[0] == "第一个建议"
        assert result[1] == "第二个建议"
        assert result[2] == "第三个建议"
    
    def test_parse_suggestions_response_mixed_format(self, enhancer):
        """测试解析混合格式的建议响应"""
        response = """- 第一个建议
第二个建议（没有破折号）
- 第三个建议
# 这是注释，应该被忽略
第四个建议"""
        
        result = enhancer._parse_suggestions_response(response)
        
        assert isinstance(result, list)
        assert len(result) == 4
        assert "第一个建议" in result
        assert "第二个建议（没有破折号）" in result
        assert "第三个建议" in result
        assert "第四个建议" in result
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_is_available_with_api_key(self, enhancer):
        """测试有API密钥时的可用性检查"""
        assert enhancer.is_available() is True
    
    @patch.dict(os.environ, {}, clear=True)
    def test_is_available_without_api_key(self, enhancer):
        """测试没有API密钥时的可用性检查"""
        assert enhancer.is_available() is False
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": ""})
    def test_is_available_with_empty_api_key(self, enhancer):
        """测试空API密钥时的可用性检查"""
        assert enhancer.is_available() is False
    
    def test_get_fix_format_system_prompt(self, enhancer):
        """测试获取格式修正系统提示词"""
        prompt = enhancer._get_fix_format_system_prompt()
        
        assert isinstance(prompt, str)
        assert "修正YAML配置格式" in prompt
        assert "```yaml" in prompt
    
    def test_get_fix_format_user_prompt(self, enhancer, sample_config, sample_errors):
        """测试获取格式修正用户提示词"""
        prompt = enhancer._get_fix_format_user_prompt(sample_config, sample_errors)
        
        assert isinstance(prompt, str)
        assert "检测到的错误" in prompt
        assert "当前配置" in prompt
        for error in sample_errors:
            assert error in prompt
    
    def test_get_optimize_config_system_prompt(self, enhancer):
        """测试获取配置优化系统提示词"""
        prompt = enhancer._get_optimize_config_system_prompt()
        
        assert isinstance(prompt, str)
        assert "优化agent配置" in prompt
        assert "最佳实践" in prompt
    
    def test_get_suggestions_system_prompt(self, enhancer):
        """测试获取建议生成系统提示词"""
        prompt = enhancer._get_suggestions_system_prompt()
        
        assert isinstance(prompt, str)
        assert "分析agent配置" in prompt
        assert "改进建议" in prompt
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch('src.agent_template_parser.llm_enhancer.ChatOpenAI')
    def test_execute_with_fallback_success_on_first_try(self, mock_chat_openai, enhancer, sample_config):
        """测试第一次尝试就成功的情况"""
        mock_response = Mock()
        mock_response.content = "name: test_agent\ndescription: Test"
        
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        mock_chat_openai.return_value = mock_llm
        
        def mock_llm_func(config):
            return enhancer._fix_config_format_with_llm(config, [])
        
        result = enhancer._execute_with_fallback(
            mock_llm_func,
            sample_config,
            fallback_func=None,
            operation_name="test"
        )
        
        assert isinstance(result, dict)
        assert mock_llm.invoke.call_count == 1
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch('src.agent_template_parser.llm_enhancer.ChatOpenAI')
    def test_execute_with_fallback_retry_then_success(self, mock_chat_openai, enhancer, sample_config):
        """测试重试后成功的情况"""
        mock_response = Mock()
        mock_response.content = "name: test_agent\ndescription: Test"
        
        mock_llm = Mock()
        # 前两次调用失败，第三次成功
        mock_llm.invoke.side_effect = [
            Exception("First failure"),
            Exception("Second failure"),
            mock_response
        ]
        mock_chat_openai.return_value = mock_llm
        
        def mock_llm_func(config):
            return enhancer._fix_config_format_with_llm(config, [])
        
        result = enhancer._execute_with_fallback(
            mock_llm_func,
            sample_config,
            fallback_func=None,
            operation_name="test"
        )
        
        assert isinstance(result, dict)
        assert mock_llm.invoke.call_count == 3
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch('src.agent_template_parser.llm_enhancer.ChatOpenAI')
    def test_execute_with_fallback_llm_fails_fallback_succeeds(self, mock_chat_openai, enhancer, sample_config):
        """测试LLM失败但回退成功的情况"""
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("LLM failure")
        mock_chat_openai.return_value = mock_llm
        
        def mock_llm_func(config):
            return enhancer._fix_config_format_with_llm(config, [])
        
        def mock_fallback_func(config):
            return {"name": "fallback_result"}
        
        result = enhancer._execute_with_fallback(
            mock_llm_func,
            sample_config,
            fallback_func=mock_fallback_func,
            operation_name="test"
        )
        
        assert result == {"name": "fallback_result"}
        assert mock_llm.invoke.call_count == 3  # max_retries
    
    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch('src.agent_template_parser.llm_enhancer.ChatOpenAI')
    def test_execute_with_fallback_both_fail(self, mock_chat_openai, enhancer, sample_config):
        """测试LLM和回退都失败的情况"""
        mock_llm = Mock()
        mock_llm.invoke.side_effect = Exception("LLM failure")
        mock_chat_openai.return_value = mock_llm
        
        def mock_llm_func(config):
            return enhancer._fix_config_format_with_llm(config, [])
        
        def mock_fallback_func(config):
            raise Exception("Fallback failure")
        
        with pytest.raises(LLMEnhancementError, match="Failed to test with LLM.*and fallback also failed"):
            enhancer._execute_with_fallback(
                mock_llm_func,
                sample_config,
                fallback_func=mock_fallback_func,
                operation_name="test"
            )
    
    def test_execute_with_fallback_disabled(self, enhancer, sample_config):
        """测试禁用回退机制的情况"""
        enhancer.fallback_enabled = False
        
        def mock_llm_func(config):
            raise Exception("LLM failure")
        
        def mock_fallback_func(config):
            return {"name": "fallback_result"}
        
        with pytest.raises(LLMEnhancementError, match="Failed to test: LLM failure"):
            enhancer._execute_with_fallback(
                mock_llm_func,
                sample_config,
                fallback_func=mock_fallback_func,
                operation_name="test"
            )
    
    def test_fix_config_format_fallback(self, enhancer, sample_config):
        """测试配置格式修正的回退实现"""
        errors = [
            "Missing required field: description",
            "Missing evaluation configuration",
            "Missing flows configuration"
        ]
        
        result = enhancer._fix_config_format_fallback(sample_config, errors)
        
        assert isinstance(result, dict)
        assert "description" in result
        assert "evaluation" in result
        assert "flows" in result
        assert result["name"] == sample_config["name"]
    
    def test_optimize_config_fallback(self, enhancer, sample_config):
        """测试配置优化的回退实现"""
        result = enhancer._optimize_config_fallback(sample_config)
        
        assert isinstance(result, dict)
        assert "description" in result
        assert result["flows"]["default"]["timeout"] == 30
    
    def test_generate_suggestions_fallback(self, enhancer, sample_config):
        """测试生成建议的回退实现"""
        result = enhancer._generate_suggestions_fallback(sample_config)
        
        assert isinstance(result, list)
        assert len(result) > 0
        assert any("description" in suggestion for suggestion in result)
    
    def test_generate_suggestions_fallback_complete_config(self, enhancer):
        """测试对完整配置生成建议的回退实现"""
        complete_config = {
            "name": "complete_agent",
            "description": "A complete agent",
            "flows": {
                "default": {
                    "prompt": "test_prompt_v1",
                    "timeout": 30
                }
            },
            "evaluation": {
                "case_fields": ["input", "output"],
                "metrics": ["accuracy"]
            }
        }
        
        result = enhancer._generate_suggestions_fallback(complete_config)
        
        assert isinstance(result, list)
        assert len(result) > 0


class TestLLMEnhancementError:
    """测试LLMEnhancementError异常类"""
    
    def test_exception_creation(self):
        """测试异常创建"""
        error = LLMEnhancementError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)


@pytest.mark.integration
class TestLLMEnhancerIntegration:
    """LLM增强处理器集成测试"""
    
    @pytest.fixture
    def enhancer(self):
        """创建LLMEnhancer实例"""
        return LLMEnhancer()
    
    @pytest.fixture
    def sample_config(self):
        """示例配置"""
        return {
            "name": "integration_test_agent",
            "flows": {
                "default": {
                    "prompt": "test_prompt_v1"
                }
            }
        }
    
    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="需要OPENAI_API_KEY环境变量")
    def test_real_llm_fix_config_format(self, enhancer, sample_config):
        """测试真实LLM调用修正配置格式（需要API密钥）"""
        errors = ["Missing description field", "Missing evaluation configuration"]
        
        try:
            result = enhancer.fix_config_format(sample_config, errors)
            
            # 验证结果是字典
            assert isinstance(result, dict)
            assert "name" in result
            
            # 验证修正效果（LLM应该添加缺失的字段）
            # 注意：由于LLM响应的不确定性，这里只做基本验证
            print(f"Fixed config: {result}")
            
        except LLMEnhancementError as e:
            pytest.skip(f"LLM调用失败: {e}")
    
    @pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="需要OPENAI_API_KEY环境变量")
    def test_real_llm_generate_suggestions(self, enhancer, sample_config):
        """测试真实LLM调用生成建议（需要API密钥）"""
        try:
            suggestions = enhancer.generate_improvement_suggestions(sample_config)
            
            # 验证结果是列表
            assert isinstance(suggestions, list)
            assert len(suggestions) > 0
            
            # 验证建议内容
            print(f"Generated suggestions: {suggestions}")
            
        except LLMEnhancementError as e:
            pytest.skip(f"LLM调用失败: {e}")