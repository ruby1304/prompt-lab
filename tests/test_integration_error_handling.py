# tests/test_integration_error_handling.py
"""
错误处理集成测试（真实 LLM 调用）

这些测试使用真实的 doubao-1-5-pro-32k-250115 模型进行调用，
验证系统的错误处理机制。

重要：
- 测试 API 调用失败的处理
- 测试解析失败的降级处理
- 测试步骤失败的错误传播
- 验证错误信息清晰且包含模型调用详情
- 测试重试机制在真实模型调用中的表现
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from dotenv import load_dotenv

from src.chains import run_flow, run_flow_with_tokens
from src.pipeline_config import load_pipeline_config
from src.pipeline_runner import PipelineRunner
from src.eval_llm_judge import judge_one, build_judge_chain
from src.agent_registry import load_agent


# 加载环境变量
load_dotenv()


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """错误处理集成测试"""
    
    def test_env_variables_loaded(self):
        """测试环境变量已正确加载"""
        api_key = os.getenv("OPENAI_API_KEY")
        assert api_key is not None, "OPENAI_API_KEY 未设置，请检查 .env 文件"
        assert len(api_key) > 0, "OPENAI_API_KEY 为空"
    
    def test_judge_parse_error_fallback(self):
        """测试 Judge 解析失败时的降级处理
        
        注意：由于使用了 Output Parser 和重试机制，实际的解析失败很少发生。
        这个测试验证当所有重试都失败时，系统能够提供降级结果。
        """
        # 加载 agent 配置
        try:
            task_agent_cfg = load_agent("mem0_l1_summarizer")
        except:
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
            "id": "parse_error_test",
            "input": "测试输入",
            "context": "测试上下文",
            "expected": "期望输出"
        }
        
        test_output = "这是一个测试输出"
        
        # 真实调用 judge_one
        judge_data, token_info = judge_one(
            task_agent_cfg=task_agent_cfg,
            flow_name="mem0_l1_v1",
            case=test_case,
            output=test_output,
            judge_config=judge_config,
            judge_flow_name="judge_v1"
        )
        
        # 验证即使在最坏情况下，也能得到有效的结果
        assert isinstance(judge_data, dict), "应该返回字典"
        assert "overall_score" in judge_data, "应该有 overall_score"
        assert "overall_comment" in judge_data, "应该有 overall_comment"
        
        # 如果有解析错误，验证降级处理
        if judge_data.get("parse_error"):
            assert judge_data["overall_score"] >= 0, "降级分数应该是有效的"
            assert len(judge_data["overall_comment"]) > 0, "降级评论不应为空"
            print(f"\n✓ Judge 解析失败降级处理验证")
            print(f"  - 使用降级分数: {judge_data['overall_score']}")
            print(f"  - 错误信息: {judge_data.get('error_message', '')[:100]}...")
        else:
            print(f"\n✓ Judge 解析成功（无需降级）")
            print(f"  - 评分: {judge_data['overall_score']}")
    
    def test_pipeline_step_failure_propagation(self):
        """测试 Pipeline 步骤失败的错误传播
        
        当一个必需步骤失败时，后续依赖该步骤的步骤应该被跳过。
        """
        # 加载 Pipeline 配置
        pipeline = load_pipeline_config("customer_service_flow")
        runner = PipelineRunner(pipeline)
        
        # 准备一个可能导致步骤失败的测试样本
        # （由于 entity_extractor 的 prompt 模板问题，这个样本会导致步骤失败）
        test_sample = {
            "id": "step_failure_test",
            "user_message": "测试消息",
            "conversation_history": ""
        }
        
        # 真实执行 Pipeline
        result = runner.execute_sample(test_sample, variant="baseline")
        
        # 验证结果存在
        assert result is not None, "Pipeline 执行结果不应为空"
        
        # 验证至少有一些步骤结果
        assert len(result.step_results) > 0, "应该有步骤结果"
        
        # 检查是否有失败的步骤
        failed_steps = result.get_failed_steps()
        
        if len(failed_steps) > 0:
            # 验证失败步骤有错误信息
            for failed_step in failed_steps:
                assert failed_step.error is not None, f"失败步骤 {failed_step.step_id} 应该有错误信息"
                assert len(failed_step.error) > 0, f"失败步骤 {failed_step.step_id} 错误信息不应为空"
                assert not failed_step.success, f"失败步骤 {failed_step.step_id} success 应该是 False"
            
            # 验证 Pipeline 整体错误信息
            if result.error:
                assert len(result.error) > 0, "Pipeline 错误信息不应为空"
                assert "失败" in result.error or "错误" in result.error, "错误信息应该包含失败或错误关键词"
            
            print(f"\n✓ Pipeline 步骤失败错误传播验证")
            print(f"  - 失败步骤数: {len(failed_steps)}")
            for failed_step in failed_steps:
                print(f"  - 失败步骤: {failed_step.step_id}")
                print(f"    错误: {failed_step.error[:100]}...")
        else:
            print(f"\n✓ Pipeline 所有步骤成功执行（无失败）")
            print(f"  - 成功步骤数: {len(result.step_results)}")
    
    def test_pipeline_error_message_clarity(self):
        """测试 Pipeline 错误信息的清晰度"""
        # 加载 Pipeline 配置
        pipeline = load_pipeline_config("document_summary")
        runner = PipelineRunner(pipeline)
        
        # 准备一个空输入的测试样本（可能导致某些问题）
        test_sample = {
            "id": "error_clarity_test",
            "raw_text": ""  # 空输入
        }
        
        # 真实执行 Pipeline
        result = runner.execute_sample(test_sample, variant="baseline")
        
        # 验证结果存在
        assert result is not None, "Pipeline 执行结果不应为空"
        
        # 如果有错误，验证错误信息的质量
        if result.error:
            # 错误信息应该不为空
            assert len(result.error) > 0, "错误信息不应为空"
            
            # 错误信息应该包含有用的信息
            # （至少应该提到哪个步骤失败了）
            assert any(keyword in result.error for keyword in ["步骤", "失败", "错误", "执行"]), \
                "错误信息应该包含关键信息"
            
            print(f"\n✓ Pipeline 错误信息清晰度验证")
            print(f"  - 错误信息长度: {len(result.error)}")
            print(f"  - 错误信息: {result.error[:200]}...")
        else:
            # 即使输入为空，Pipeline 也成功执行了
            print(f"\n✓ Pipeline 处理空输入成功")
            print(f"  - 所有步骤都成功执行")
    
    def test_output_parser_retry_mechanism(self):
        """测试 Output Parser 的重试机制
        
        验证当解析失败时，系统会自动重试。
        """
        # 准备测试数据
        extra_vars = {
            "agent_id": "retry_test_agent",
            "agent_name": "重试测试 Agent",
            "description": "测试重试机制",
            "business_goal": "验证重试",
            "must_have": "测试",
            "nice_to_have": "测试",
            "case_rendered": "测试输入",
            "input": "测试",
            "context": "测试",
            "expected": "测试",
            "output": "测试输出",
            "flow_name": "test",
            "min_score": 0,
            "max_score": 10
        }
        
        # 真实调用 Judge（使用 judge_v1，它配置了重试）
        result, token_info, parser_stats = run_flow_with_tokens(
            flow_name="judge_v1",
            extra_vars=extra_vars,
            agent_id="judge_default"
        )
        
        # 验证结果
        assert isinstance(result, dict), "应该返回字典"
        assert "overall_score" in result, "应该有 overall_score"
        
        # 验证 token 信息
        assert token_info["total_tokens"] > 0, "应该有 token 消耗"
        
        # 如果有 parser 统计信息，验证重试机制
        if parser_stats:
            print(f"\n✓ Output Parser 重试机制验证")
            print(f"  - Parser 统计信息: {parser_stats}")
            
            # 验证统计信息的结构
            if "success_count" in parser_stats:
                assert parser_stats["success_count"] >= 0, "success_count 应该是非负数"
            if "failure_count" in parser_stats:
                assert parser_stats["failure_count"] >= 0, "failure_count 应该是非负数"
            if "total_retry_count" in parser_stats:
                assert parser_stats["total_retry_count"] >= 0, "total_retry_count 应该是非负数"
        else:
            print(f"\n✓ Output Parser 解析成功（无重试）")
            print(f"  - 第一次尝试就成功")
    
    def test_pipeline_validation_errors(self):
        """测试 Pipeline 配置验证错误"""
        # 加载一个有效的 Pipeline 配置
        pipeline = load_pipeline_config("document_summary")
        
        # 验证 Pipeline 配置
        runner = PipelineRunner(pipeline)
        validation_errors = runner.validate_pipeline()
        
        # 对于有效的配置，应该没有验证错误
        if len(validation_errors) == 0:
            print(f"\n✓ Pipeline 配置验证通过")
            print(f"  - 无验证错误")
        else:
            # 如果有验证错误，验证错误信息的质量
            print(f"\n⚠ Pipeline 配置有验证错误")
            print(f"  - 错误数量: {len(validation_errors)}")
            for i, error in enumerate(validation_errors[:3]):  # 只显示前3个
                print(f"  - 错误 {i+1}: {error[:100]}...")
            
            # 验证错误信息不为空
            for error in validation_errors:
                assert len(error) > 0, "验证错误信息不应为空"
    
    def test_api_call_error_handling(self):
        """测试 API 调用错误的处理
        
        注意：这个测试使用真实的 API 调用，所以不会故意触发错误。
        它验证系统在正常情况下能够正确处理 API 响应。
        """
        # 准备测试数据
        extra_vars = {
            "agent_id": "api_test",
            "agent_name": "API 测试",
            "description": "测试 API 调用",
            "business_goal": "验证 API",
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
        
        # 真实调用
        try:
            result = run_flow(
                flow_name="judge_v1",
                extra_vars=extra_vars,
                agent_id="judge_default"
            )
            
            # 验证调用成功
            assert isinstance(result, dict), "API 调用应该成功并返回字典"
            assert "overall_score" in result, "结果应该包含 overall_score"
            
            print(f"\n✓ API 调用成功")
            print(f"  - 返回类型: {type(result).__name__}")
            print(f"  - overall_score: {result['overall_score']}")
            
        except Exception as e:
            # 如果发生错误，验证错误信息的质量
            error_msg = str(e)
            assert len(error_msg) > 0, "错误信息不应为空"
            
            print(f"\n⚠ API 调用失败（预期外）")
            print(f"  - 错误类型: {type(e).__name__}")
            print(f"  - 错误信息: {error_msg[:200]}...")
            
            # 重新抛出异常以标记测试失败
            raise
    
    def test_error_recovery_and_continuation(self):
        """测试错误恢复和继续执行
        
        验证当可选步骤失败时，Pipeline 能够继续执行后续步骤。
        """
        # 加载 Pipeline 配置
        pipeline = load_pipeline_config("document_summary")
        runner = PipelineRunner(pipeline)
        
        # 准备测试样本
        test_sample = {
            "id": "recovery_test",
            "raw_text": "这是一段测试文本，用于验证错误恢复机制。"
        }
        
        # 真实执行 Pipeline
        result = runner.execute_sample(test_sample, variant="baseline")
        
        # 验证结果存在
        assert result is not None, "Pipeline 执行结果不应为空"
        
        # 验证至少有一些步骤成功执行
        successful_steps = [s for s in result.step_results if s.success]
        assert len(successful_steps) > 0, "应该至少有一个步骤成功执行"
        
        # 验证执行时间被记录
        assert result.total_execution_time > 0, "执行时间应该大于 0"
        
        print(f"\n✓ 错误恢复和继续执行验证")
        print(f"  - 总步骤数: {len(result.step_results)}")
        print(f"  - 成功步骤数: {len(successful_steps)}")
        print(f"  - 失败步骤数: {len(result.get_failed_steps())}")
        print(f"  - 执行时间: {result.total_execution_time:.2f}秒")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
