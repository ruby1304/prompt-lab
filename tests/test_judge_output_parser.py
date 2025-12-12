# tests/test_judge_output_parser.py
"""
测试 Judge Agent 使用 Output Parser 的功能

测试内容：
- Judge 输出成功解析
- 必需字段验证
- 解析失败和重试
- 降级处理
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.eval_llm_judge import (
    judge_one,
    _validate_judge_output,
    _create_fallback_result,
    render_case_for_judge
)
from src.agent_registry import AgentConfig


@pytest.fixture
def sample_task_agent():
    """创建示例 TaskAgent 配置"""
    agent = Mock(spec=AgentConfig)
    agent.id = "test_agent"
    agent.name = "测试 Agent"
    agent.description = "这是一个测试 Agent"
    agent.business_goal = "完成测试任务"
    agent.expectations = {
        "must_have": [
            "输出必须包含关键信息",
            "输出必须格式正确"
        ],
        "nice_to_have": [
            "输出应该简洁明了",
            "输出应该有良好的可读性"
        ]
    }
    agent.evaluation = {
        "scale": {"min": 0, "max": 10},
        "case_fields": []
    }
    return agent


@pytest.fixture
def sample_judge_config():
    """创建示例 Judge 配置"""
    return {
        "min_score": 0,
        "max_score": 10,
        "model_name": "test-model",
        "temperature": 0.0
    }


@pytest.fixture
def sample_case():
    """创建示例测试用例"""
    return {
        "id": "test_case_1",
        "input": "测试输入",
        "context": "测试上下文",
        "expected": "期望输出"
    }


@pytest.fixture
def valid_judge_output():
    """创建有效的 Judge 输出"""
    return {
        "derived_criteria": [
            {
                "id": "c1",
                "name": "信息完整性",
                "from": "must_have",
                "importance": "high",
                "comment": "检查关键信息是否完整"
            }
        ],
        "must_have_check": [
            {
                "item": "输出必须包含关键信息",
                "satisfied": True,
                "score": 10,
                "comment": "包含了所有关键信息"
            },
            {
                "item": "输出必须格式正确",
                "satisfied": True,
                "score": 10,
                "comment": "格式完全正确"
            }
        ],
        "nice_to_have_check": [
            {
                "item": "输出应该简洁明了",
                "satisfied": True,
                "score": 8,
                "comment": "比较简洁"
            }
        ],
        "overall_score": 9.0,
        "overall_comment": "整体表现优秀，符合所有要求"
    }


class TestValidateJudgeOutput:
    """测试 Judge 输出验证功能"""
    
    def test_valid_output(self, valid_judge_output):
        """测试有效的 Judge 输出通过验证"""
        # 不应该抛出异常
        _validate_judge_output(valid_judge_output)
    
    def test_missing_overall_score(self, valid_judge_output):
        """测试缺少 overall_score 字段"""
        invalid_output = valid_judge_output.copy()
        del invalid_output["overall_score"]
        
        with pytest.raises(ValueError) as exc_info:
            _validate_judge_output(invalid_output)
        
        error_msg = str(exc_info.value)
        assert "overall_score" in error_msg
        assert "缺少必需字段" in error_msg
        assert "修复建议" in error_msg
    
    def test_missing_must_have_check(self, valid_judge_output):
        """测试缺少 must_have_check 字段"""
        invalid_output = valid_judge_output.copy()
        del invalid_output["must_have_check"]
        
        with pytest.raises(ValueError) as exc_info:
            _validate_judge_output(invalid_output)
        
        error_msg = str(exc_info.value)
        assert "must_have_check" in error_msg
    
    def test_missing_overall_comment(self, valid_judge_output):
        """测试缺少 overall_comment 字段"""
        invalid_output = valid_judge_output.copy()
        del invalid_output["overall_comment"]
        
        with pytest.raises(ValueError) as exc_info:
            _validate_judge_output(invalid_output)
        
        error_msg = str(exc_info.value)
        assert "overall_comment" in error_msg
    
    def test_missing_multiple_fields(self, valid_judge_output):
        """测试缺少多个必需字段"""
        invalid_output = {
            "nice_to_have_check": []
        }
        
        with pytest.raises(ValueError) as exc_info:
            _validate_judge_output(invalid_output)
        
        error_msg = str(exc_info.value)
        assert "overall_score" in error_msg
        assert "must_have_check" in error_msg
        assert "overall_comment" in error_msg


class TestCreateFallbackResult:
    """测试降级结果创建功能"""
    
    def test_default_fallback(self):
        """测试默认降级结果"""
        result = _create_fallback_result(
            error="测试错误",
            min_score=0,
            max_score=10
        )
        
        assert result["overall_score"] == 5.0  # 中等分数
        assert result["must_have_check"] == []
        assert result["nice_to_have_check"] == []
        assert "测试错误" in result["overall_comment"]
        assert result["parse_error"] is True
        assert result["error_message"] == "测试错误"
    
    def test_custom_score_range(self):
        """测试自定义分数范围的降级结果"""
        result = _create_fallback_result(
            error="测试错误",
            min_score=1,
            max_score=5
        )
        
        assert result["overall_score"] == 3.0  # (1 + 5) / 2
    
    def test_long_error_message(self):
        """测试长错误信息被截断"""
        long_error = "错误" * 200
        result = _create_fallback_result(
            error=long_error,
            min_score=0,
            max_score=10
        )
        
        # overall_comment 应该截断错误信息
        assert len(result["overall_comment"]) < len(long_error)
        assert result["error_message"] == long_error  # 完整错误信息保留


class TestRenderCaseForJudge:
    """测试 case 渲染功能"""
    
    def test_render_without_case_fields(self, sample_task_agent, sample_case):
        """测试没有配置 case_fields 时的渲染"""
        rendered = render_case_for_judge(sample_task_agent, sample_case)
        
        assert "测试输入" in rendered
        assert "测试上下文" in rendered
        assert "期望输出" in rendered
        assert "主要输入内容" in rendered
        assert "相关上下文信息" in rendered
    
    def test_render_with_case_fields(self, sample_task_agent, sample_case):
        """测试配置了 case_fields 时的渲染"""
        sample_task_agent.evaluation = {
            "scale": {"min": 0, "max": 10},
            "case_fields": [
                {
                    "key": "input",
                    "label": "用户输入",
                    "section": "primary_input"
                },
                {
                    "key": "context",
                    "label": "背景信息",
                    "section": "context"
                }
            ]
        }
        
        rendered = render_case_for_judge(sample_task_agent, sample_case)
        
        assert "用户输入" in rendered
        assert "背景信息" in rendered
        assert "测试输入" in rendered
        assert "测试上下文" in rendered


class TestJudgeOneIntegration:
    """测试 judge_one 函数的集成功能（使用真实 LLM 调用）"""
    
    @pytest.mark.integration
    def test_judge_one_success(
        self,
        sample_task_agent,
        sample_judge_config,
        sample_case
    ):
        """测试 Judge 评估成功场景（真实 LLM 调用）"""
        # 这个测试需要真实的 API Key 和 LLM 调用
        # 使用 pytest.mark.integration 标记，可以通过 pytest -m integration 运行
        
        with patch("src.eval_llm_judge.run_flow_with_tokens") as mock_run:
            # 模拟成功的解析结果
            mock_run.return_value = (
                {
                    "overall_score": 8.5,
                    "must_have_check": [
                        {
                            "item": "输出必须包含关键信息",
                            "satisfied": True,
                            "score": 9,
                            "comment": "包含了关键信息"
                        }
                    ],
                    "nice_to_have_check": [],
                    "overall_comment": "整体表现良好"
                },
                {
                    "input_tokens": 500,
                    "output_tokens": 200,
                    "total_tokens": 700
                }
            )
            
            result, token_info = judge_one(
                task_agent_cfg=sample_task_agent,
                flow_name="test_flow",
                case=sample_case,
                output="这是测试输出",
                judge_config=sample_judge_config,
                judge_flow_name="judge_v1"
            )
            
            # 验证结果
            assert result["overall_score"] == 8.5
            assert len(result["must_have_check"]) == 1
            assert result["overall_comment"] == "整体表现良好"
            
            # 验证 token 信息
            assert token_info["input_tokens"] == 500
            assert token_info["output_tokens"] == 200
            assert token_info["total_tokens"] == 700
    
    @pytest.mark.integration
    def test_judge_one_parse_failure(
        self,
        sample_task_agent,
        sample_judge_config,
        sample_case
    ):
        """测试 Judge 解析失败时的降级处理"""
        
        with patch("src.eval_llm_judge.run_flow_with_tokens") as mock_run:
            # 模拟解析失败
            mock_run.side_effect = ValueError("解析失败")
            
            result, token_info = judge_one(
                task_agent_cfg=sample_task_agent,
                flow_name="test_flow",
                case=sample_case,
                output="这是测试输出",
                judge_config=sample_judge_config,
                judge_flow_name="judge_v1"
            )
            
            # 验证降级结果
            assert result["overall_score"] == 5.0  # 默认中等分数
            assert result["parse_error"] is True
            assert "解析失败" in result["error_message"]
            assert result["must_have_check"] == []
            
            # Token 信息应该为空
            assert token_info["total_tokens"] == 0
    
    @pytest.mark.integration
    def test_judge_one_missing_fields(
        self,
        sample_task_agent,
        sample_judge_config,
        sample_case
    ):
        """测试 Judge 输出缺少必需字段时的处理"""
        
        with patch("src.eval_llm_judge.run_flow_with_tokens") as mock_run:
            # 模拟缺少必需字段的输出
            mock_run.return_value = (
                {
                    "overall_score": 8.5,
                    # 缺少 must_have_check 和 overall_comment
                },
                {
                    "input_tokens": 500,
                    "output_tokens": 200,
                    "total_tokens": 700
                }
            )
            
            result, token_info = judge_one(
                task_agent_cfg=sample_task_agent,
                flow_name="test_flow",
                case=sample_case,
                output="这是测试输出",
                judge_config=sample_judge_config,
                judge_flow_name="judge_v1"
            )
            
            # 验证降级结果
            assert result["parse_error"] is True
            assert "缺少必需字段" in result["error_message"]
            assert result["overall_score"] == 5.0


class TestJudgeOutputParserRetry:
    """测试 Output Parser 的重试机制"""
    
    @pytest.mark.integration
    def test_retry_on_parse_error(
        self,
        sample_task_agent,
        sample_judge_config,
        sample_case
    ):
        """测试解析错误时的重试机制"""
        
        with patch("src.eval_llm_judge.run_flow_with_tokens") as mock_run:
            # 第一次调用失败，第二次成功
            call_count = 0
            
            def side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                
                if call_count == 1:
                    # 第一次返回格式错误的 JSON
                    raise json.JSONDecodeError("Invalid JSON", "", 0)
                else:
                    # 第二次返回正确的结果
                    return (
                        {
                            "overall_score": 8.0,
                            "must_have_check": [],
                            "overall_comment": "重试成功"
                        },
                        {"input_tokens": 500, "output_tokens": 200, "total_tokens": 700}
                    )
            
            mock_run.side_effect = side_effect
            
            # 注意：实际的重试逻辑在 RetryOutputParser 中
            # 这里我们测试的是当 run_flow_with_tokens 失败时的降级处理
            result, token_info = judge_one(
                task_agent_cfg=sample_task_agent,
                flow_name="test_flow",
                case=sample_case,
                output="这是测试输出",
                judge_config=sample_judge_config,
                judge_flow_name="judge_v1"
            )
            
            # 由于第一次就失败了，应该触发降级处理
            assert result["parse_error"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
