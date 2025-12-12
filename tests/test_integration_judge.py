# tests/test_integration_judge.py
"""
Judge Agent 集成测试（真实 LLM 调用）

这些测试使用真实的 doubao-1-5-pro-32k-250115 模型进行调用，
验证 Judge Agent 与 Output Parser 的集成是否正常工作。

重要：
- 必须使用 .env 中配置的真实 API Key
- 必须使用 doubao-1-5-pro-32k-250115 模型
- 禁止使用 Mock 或假数据
- 验证真实模型的响应质量和格式
"""

import pytest
import os
from dotenv import load_dotenv

from src.chains import run_flow, run_flow_with_tokens
from src.eval_llm_judge import judge_one, build_judge_chain
from src.agent_registry import load_agent


# 加载环境变量
load_dotenv()


@pytest.mark.integration
class TestJudgeAgentIntegration:
    """Judge Agent 集成测试"""
    
    def test_env_variables_loaded(self):
        """测试环境变量已正确加载"""
        api_key = os.getenv("OPENAI_API_KEY")
        assert api_key is not None, "OPENAI_API_KEY 未设置，请检查 .env 文件"
        assert len(api_key) > 0, "OPENAI_API_KEY 为空"
        
        # 验证模型名称
        model_name = os.getenv("OPENAI_MODEL_NAME", "")
        assert "doubao" in model_name.lower() or model_name == "", \
            f"期望使用 doubao 模型，但配置的是: {model_name}"
    
    def test_judge_v1_with_output_parser_real_call(self):
        """测试 judge_v1 使用 Output Parser（真实模型调用）"""
        # 准备测试数据
        extra_vars = {
            "agent_id": "test_agent",
            "agent_name": "测试 Agent",
            "description": "这是一个测试 Agent",
            "business_goal": "测试业务目标",
            "must_have": "必须包含关键信息",
            "nice_to_have": "最好简洁明了",
            "case_rendered": "输入: 测试输入\n上下文: 测试上下文",
            "input": "测试输入",
            "context": "测试上下文",
            "expected": "期望输出",
            "output": "这是一个测试输出，包含了关键信息，表达简洁明了。",
            "flow_name": "test_flow",
            "min_score": 0,
            "max_score": 10
        }
        
        # 真实调用 Judge Agent
        result = run_flow(
            flow_name="judge_v1",
            extra_vars=extra_vars,
            agent_id="judge_default"
        )
        
        # 验证返回的是结构化对象（dict），不是字符串
        assert isinstance(result, dict), \
            f"期望返回 dict，但得到 {type(result).__name__}"
        
        # 验证必需字段存在
        assert "overall_score" in result, "缺少 overall_score 字段"
        assert "must_have_check" in result, "缺少 must_have_check 字段"
        assert "overall_comment" in result, "缺少 overall_comment 字段"
        
        # 验证字段类型
        assert isinstance(result["overall_score"], (int, float)), \
            f"overall_score 应该是数字，但得到 {type(result['overall_score']).__name__}"
        assert isinstance(result["must_have_check"], list), \
            f"must_have_check 应该是列表，但得到 {type(result['must_have_check']).__name__}"
        assert isinstance(result["overall_comment"], str), \
            f"overall_comment 应该是字符串，但得到 {type(result['overall_comment']).__name__}"
        
        # 验证分数在合理范围内
        assert 0 <= result["overall_score"] <= 10, \
            f"overall_score 应该在 0-10 之间，但得到 {result['overall_score']}"
        
        # 验证 overall_comment 不为空
        assert len(result["overall_comment"]) > 0, "overall_comment 不应为空"
        
        print(f"\n✓ Judge v1 真实调用成功")
        print(f"  - 返回类型: {type(result).__name__}")
        print(f"  - overall_score: {result['overall_score']}")
        print(f"  - must_have_check 数量: {len(result['must_have_check'])}")
        print(f"  - overall_comment: {result['overall_comment'][:100]}...")
    
    def test_judge_v2_with_output_parser_real_call(self):
        """测试 judge_v2 使用 Output Parser（真实模型调用）"""
        # 准备测试数据
        extra_vars = {
            "agent_id": "test_agent",
            "agent_name": "对话总结 Agent",
            "description": "总结对话内容",
            "business_goal": "准确提取对话中的关键信息",
            "must_have": "包含时间、地点、人物信息",
            "nice_to_have": "总结简洁",
            "case_rendered": "对话内容: 小明和小红在2024年1月1日在公园讨论了项目计划",
            "input": "对话内容",
            "context": "项目讨论",
            "expected": "总结",
            "output": "2024年1月1日，小明和小红在公园讨论了项目计划。",
            "flow_name": "test_flow",
            "min_score": 0,
            "max_score": 10
        }
        
        # 真实调用 Judge Agent v2
        result = run_flow(
            flow_name="judge_v2",
            extra_vars=extra_vars,
            agent_id="judge_default"
        )
        
        # 验证返回的是结构化对象
        assert isinstance(result, dict), \
            f"期望返回 dict，但得到 {type(result).__name__}"
        
        # 验证必需字段存在
        assert "overall_score" in result, "缺少 overall_score 字段"
        assert "must_have_check" in result, "缺少 must_have_check 字段"
        assert "overall_comment" in result, "缺少 overall_comment 字段"
        
        # judge_v2 特有的字段
        assert "summary_quality_check" in result, "缺少 summary_quality_check 字段"
        assert isinstance(result["summary_quality_check"], list), \
            "summary_quality_check 应该是列表"
        
        # 验证分数在合理范围内
        assert 0 <= result["overall_score"] <= 10, \
            f"overall_score 应该在 0-10 之间，但得到 {result['overall_score']}"
        
        print(f"\n✓ Judge v2 真实调用成功")
        print(f"  - 返回类型: {type(result).__name__}")
        print(f"  - overall_score: {result['overall_score']}")
        print(f"  - summary_quality_check 数量: {len(result['summary_quality_check'])}")
        print(f"  - overall_comment: {result['overall_comment'][:100]}...")
    
    def test_judge_with_tokens_real_call(self):
        """测试 Judge 使用 run_flow_with_tokens（真实模型调用）"""
        extra_vars = {
            "agent_id": "test_agent",
            "agent_name": "测试 Agent",
            "description": "测试描述",
            "business_goal": "测试目标",
            "must_have": "必须包含测试信息",
            "nice_to_have": "简洁",
            "case_rendered": "测试输入",
            "input": "测试",
            "context": "上下文",
            "expected": "期望",
            "output": "这是测试输出，包含了测试信息。",
            "flow_name": "test_flow",
            "min_score": 0,
            "max_score": 10
        }
        
        # 真实调用并获取 token 信息
        result, token_info, parser_stats = run_flow_with_tokens(
            flow_name="judge_v1",
            extra_vars=extra_vars,
            agent_id="judge_default"
        )
        
        # 验证结果
        assert isinstance(result, dict), "期望返回 dict"
        assert "overall_score" in result, "缺少 overall_score 字段"
        
        # 验证 token 信息
        assert isinstance(token_info, dict), "token_info 应该是 dict"
        assert "input_tokens" in token_info, "缺少 input_tokens"
        assert "output_tokens" in token_info, "缺少 output_tokens"
        assert "total_tokens" in token_info, "缺少 total_tokens"
        
        # 验证 token 数量合理（真实调用应该有 token 消耗）
        assert token_info["input_tokens"] > 0, "input_tokens 应该大于 0"
        assert token_info["output_tokens"] > 0, "output_tokens 应该大于 0"
        assert token_info["total_tokens"] > 0, "total_tokens 应该大于 0"
        
        print(f"\n✓ Judge with tokens 真实调用成功")
        print(f"  - input_tokens: {token_info['input_tokens']}")
        print(f"  - output_tokens: {token_info['output_tokens']}")
        print(f"  - total_tokens: {token_info['total_tokens']}")
        if parser_stats:
            print(f"  - parser_stats: {parser_stats}")
    
    def test_judge_one_function_real_call(self):
        """测试 judge_one 函数（真实模型调用）"""
        # 加载测试 agent（使用现有的 mem0_l1_summarizer）
        try:
            task_agent_cfg = load_agent("mem0_l1_summarizer")
        except:
            # 如果 mem0_l1_summarizer 不存在，跳过测试
            pytest.skip("mem0_l1_summarizer agent 不存在")
        
        judge_agent_cfg = load_agent("judge_default")
        
        # 构建 judge 配置
        judge_config = build_judge_chain(
            task_agent_cfg=task_agent_cfg,
            judge_agent_cfg=judge_agent_cfg,
            judge_flow_name="judge_v1"
        )
        
        # 准备测试用例
        test_case = {
            "id": "test_1",
            "input": "这是一段测试对话内容",
            "context": "测试上下文",
            "expected": "期望的总结"
        }
        
        test_output = "这是一个测试输出，总结了对话的关键信息。"
        
        # 真实调用 judge_one
        judge_data, token_info = judge_one(
            task_agent_cfg=task_agent_cfg,
            flow_name="mem0_l1_v1",
            case=test_case,
            output=test_output,
            judge_config=judge_config,
            judge_flow_name="judge_v1"
        )
        
        # 验证结果
        assert isinstance(judge_data, dict), "judge_data 应该是 dict"
        assert "overall_score" in judge_data, "缺少 overall_score"
        assert "must_have_check" in judge_data, "缺少 must_have_check"
        assert "overall_comment" in judge_data, "缺少 overall_comment"
        
        # 验证 token 信息
        assert isinstance(token_info, dict), "token_info 应该是 dict"
        assert token_info["total_tokens"] > 0, "应该有 token 消耗"
        
        # 验证没有解析错误
        assert not judge_data.get("parse_error", False), \
            f"不应该有解析错误: {judge_data.get('error_message', '')}"
        
        print(f"\n✓ judge_one 函数真实调用成功")
        print(f"  - overall_score: {judge_data['overall_score']}")
        print(f"  - must_have_check 数量: {len(judge_data['must_have_check'])}")
        print(f"  - total_tokens: {token_info['total_tokens']}")
    
    def test_judge_response_quality(self):
        """测试 Judge 响应质量和格式"""
        extra_vars = {
            "agent_id": "quality_test_agent",
            "agent_name": "质量测试 Agent",
            "description": "测试 Agent 的响应质量",
            "business_goal": "确保输出包含所有必需信息并且格式正确",
            "must_have": "1. 包含用户名称\n2. 包含时间信息\n3. 包含操作描述",
            "nice_to_have": "1. 语言简洁\n2. 格式清晰",
            "case_rendered": "用户: 张三\n时间: 2024-01-15\n操作: 提交了项目报告",
            "input": "用户操作记录",
            "context": "项目管理系统",
            "expected": "完整的操作记录",
            "output": "张三在2024年1月15日提交了项目报告。报告内容完整，格式规范。",
            "flow_name": "test_flow",
            "min_score": 0,
            "max_score": 10
        }
        
        # 真实调用
        result = run_flow(
            flow_name="judge_v1",
            extra_vars=extra_vars,
            agent_id="judge_default"
        )
        
        # 验证响应质量
        assert isinstance(result, dict), "应该返回字典"
        
        # 验证 must_have_check 的结构
        assert isinstance(result["must_have_check"], list), "must_have_check 应该是列表"
        if len(result["must_have_check"]) > 0:
            first_check = result["must_have_check"][0]
            assert "item" in first_check, "must_have_check 项应该包含 item 字段"
            assert "satisfied" in first_check, "must_have_check 项应该包含 satisfied 字段"
            assert isinstance(first_check["satisfied"], bool), "satisfied 应该是布尔值"
        
        # 验证 nice_to_have_check 的结构（如果存在）
        if "nice_to_have_check" in result:
            assert isinstance(result["nice_to_have_check"], list), \
                "nice_to_have_check 应该是列表"
        
        # 验证 derived_criteria（如果存在）
        if "derived_criteria" in result:
            assert isinstance(result["derived_criteria"], list), \
                "derived_criteria 应该是列表"
            if len(result["derived_criteria"]) > 0:
                first_criteria = result["derived_criteria"][0]
                assert "name" in first_criteria, "derived_criteria 应该包含 name"
                assert "from" in first_criteria, "derived_criteria 应该包含 from"
        
        # 验证 overall_comment 有实质内容
        assert len(result["overall_comment"]) > 20, \
            "overall_comment 应该有足够的内容（至少20个字符）"
        
        print(f"\n✓ Judge 响应质量验证通过")
        print(f"  - overall_score: {result['overall_score']}")
        print(f"  - must_have_check 数量: {len(result['must_have_check'])}")
        print(f"  - overall_comment 长度: {len(result['overall_comment'])}")
        if "derived_criteria" in result:
            print(f"  - derived_criteria 数量: {len(result['derived_criteria'])}")
    
    def test_judge_model_verification(self):
        """验证使用的是 doubao-1-5-pro-32k-250115 模型"""
        # 这个测试主要是确认配置正确
        model_name = os.getenv("OPENAI_MODEL_NAME", "")
        
        # 如果环境变量中指定了模型，验证它
        if model_name:
            assert "doubao" in model_name.lower(), \
                f"应该使用 doubao 模型，但配置的是: {model_name}"
            print(f"\n✓ 模型配置验证通过: {model_name}")
        else:
            print(f"\n⚠ 未在环境变量中指定模型，将使用默认配置")
        
        # 执行一次真实调用来验证
        extra_vars = {
            "agent_id": "model_test",
            "agent_name": "模型测试",
            "description": "验证模型",
            "business_goal": "测试",
            "must_have": "测试",
            "nice_to_have": "测试",
            "case_rendered": "测试",
            "input": "测试",
            "context": "测试",
            "expected": "测试",
            "output": "测试输出",
            "flow_name": "test",
            "min_score": 0,
            "max_score": 10
        }
        
        # 真实调用应该成功
        result = run_flow(
            flow_name="judge_v1",
            extra_vars=extra_vars,
            agent_id="judge_default"
        )
        
        assert isinstance(result, dict), "真实调用应该成功并返回字典"
        print(f"  - 真实调用成功，模型工作正常")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
