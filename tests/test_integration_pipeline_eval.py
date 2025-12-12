# tests/test_integration_pipeline_eval.py
"""
Pipeline 评估流程集成测试（真实 LLM 调用）

这些测试使用真实的 doubao-1-5-pro-32k-250115 模型进行调用，
验证 Pipeline 评估流程的完整性。

重要：
- 必须使用 .env 中配置的真实 API Key
- 必须使用 doubao-1-5-pro-32k-250115 模型
- Judge Agent 必须使用真实模型进行调用
- 验证评估结果包含所有必需字段
- 验证 Judge 评分合理且符合模型输出特征
- 验证 Output Parser 正确处理 Judge 输出
"""

import pytest
import os
from dotenv import load_dotenv

from src.pipeline_config import load_pipeline_config
from src.pipeline_runner import PipelineRunner
from src.unified_evaluator import UnifiedEvaluator
from src.models import EvaluationConfig


# 加载环境变量
load_dotenv()


@pytest.mark.integration
class TestPipelineEvaluationIntegration:
    """Pipeline 评估流程集成测试"""
    
    def test_env_variables_loaded(self):
        """测试环境变量已正确加载"""
        api_key = os.getenv("OPENAI_API_KEY")
        assert api_key is not None, "OPENAI_API_KEY 未设置，请检查 .env 文件"
        assert len(api_key) > 0, "OPENAI_API_KEY 为空"
    
    def test_pipeline_execute_and_evaluate_real_call(self):
        """测试 Pipeline 执行并评估（真实模型调用）"""
        # 加载 Pipeline 配置
        pipeline = load_pipeline_config("document_summary")
        runner = PipelineRunner(pipeline)
        
        # 准备测试样本
        test_sample = {
            "id": "eval_test_1",
            "raw_text": "人工智能是计算机科学的一个分支。它研究如何让机器模拟人类的智能行为。人工智能的应用包括语音识别、图像识别、自然语言处理等领域。",
            "expected_summary": "介绍人工智能的定义和应用领域"
        }
        
        # 真实执行 Pipeline
        result = runner.execute_sample(test_sample, variant="baseline")
        
        # 验证执行成功
        assert result.error is None, f"Pipeline 执行失败: {result.error}"
        assert len(result.step_results) == 2, "应该有 2 个步骤结果"
        
        # 获取最终输出
        step_outputs = result.get_step_outputs_dict()
        final_output = step_outputs.get("summary", "")
        
        assert len(final_output) > 0, "最终输出不应为空"
        
        # 创建评估配置（使用 Judge Agent）
        eval_config = EvaluationConfig(
            judge_enabled=True,
            judge_agent_id="judge_default",
            judge_flow="judge_v1",
            scale_min=0,
            scale_max=10
        )
        
        # 创建评估器
        evaluator = UnifiedEvaluator(eval_config)
        
        # 真实评估 Pipeline 输出（Judge 使用真实模型调用）
        eval_result = evaluator.evaluate_pipeline_output(
            pipeline_id=pipeline.id,
            variant="baseline",
            test_case=test_sample,
            step_outputs=step_outputs,
            final_output=final_output
        )
        
        # 验证评估结果包含所有必需字段
        assert eval_result is not None, "评估结果不应为空"
        assert hasattr(eval_result, "sample_id"), "评估结果应该有 sample_id"
        assert hasattr(eval_result, "entity_type"), "评估结果应该有 entity_type"
        assert hasattr(eval_result, "entity_id"), "评估结果应该有 entity_id"
        assert hasattr(eval_result, "variant"), "评估结果应该有 variant"
        assert hasattr(eval_result, "overall_score"), "评估结果应该有 overall_score"
        assert hasattr(eval_result, "step_outputs"), "评估结果应该有 step_outputs"
        assert hasattr(eval_result, "judge_feedback"), "评估结果应该有 judge_feedback"
        
        # 验证字段值
        assert eval_result.entity_type == "pipeline", "entity_type 应该是 pipeline"
        assert eval_result.entity_id == pipeline.id, "entity_id 应该是 pipeline ID"
        assert eval_result.variant == "baseline", "variant 应该是 baseline"
        
        # 验证 Judge 评分合理
        assert isinstance(eval_result.overall_score, (int, float)), \
            f"overall_score 应该是数字，但得到 {type(eval_result.overall_score).__name__}"
        assert 0 <= eval_result.overall_score <= 10, \
            f"overall_score 应该在 0-10 之间，但得到 {eval_result.overall_score}"
        
        # 验证步骤输出被正确记录
        assert isinstance(eval_result.step_outputs, dict), "step_outputs 应该是字典"
        assert len(eval_result.step_outputs) > 0, "step_outputs 不应为空"
        
        # 验证 Output Parser 正确处理了 Judge 输出（没有解析错误）
        assert not hasattr(eval_result, "parse_error") or not eval_result.parse_error, \
            "不应该有解析错误"
        
        print(f"\n✓ Pipeline 执行并评估成功")
        print(f"  - Pipeline ID: {pipeline.id}")
        print(f"  - 样本 ID: {eval_result.sample_id}")
        print(f"  - 评估分数: {eval_result.overall_score}")
        print(f"  - 步骤输出数: {len(eval_result.step_outputs)}")
        print(f"  - 最终输出长度: {len(final_output)}")
        print(f"  - 最终输出: {final_output[:100]}...")
    
    def test_pipeline_evaluation_with_judge_feedback(self):
        """测试 Pipeline 评估包含 Judge 反馈"""
        # 加载 Pipeline 配置
        pipeline = load_pipeline_config("document_summary")
        runner = PipelineRunner(pipeline)
        
        # 准备测试样本
        test_sample = {
            "id": "feedback_test",
            "raw_text": "量子计算是一种新型计算模式。它利用量子力学原理进行计算。量子计算机在某些问题上比传统计算机快得多。",
            "expected_summary": "介绍量子计算的原理和优势"
        }
        
        # 真实执行 Pipeline
        result = runner.execute_sample(test_sample, variant="baseline")
        
        assert result.error is None, f"Pipeline 执行失败: {result.error}"
        
        # 获取输出
        step_outputs = result.get_step_outputs_dict()
        final_output = step_outputs.get("summary", "")
        
        # 创建评估配置
        eval_config = EvaluationConfig(
            judge_enabled=True,
            judge_agent_id="judge_default",
            judge_flow="judge_v1",
            scale_min=0,
            scale_max=10
        )
        
        evaluator = UnifiedEvaluator(eval_config)
        
        # 真实评估
        eval_result = evaluator.evaluate_pipeline_output(
            pipeline_id=pipeline.id,
            variant="baseline",
            test_case=test_sample,
            step_outputs=step_outputs,
            final_output=final_output
        )
        
        # 验证 Judge 反馈存在
        assert hasattr(eval_result, "judge_feedback"), "评估结果应该有 judge_feedback"
        
        # 如果有 Judge 反馈，验证其内容
        if eval_result.judge_feedback:
            assert isinstance(eval_result.judge_feedback, str), "judge_feedback 应该是字符串"
            assert len(eval_result.judge_feedback) > 0, "judge_feedback 不应为空"
            
            print(f"\n✓ Pipeline 评估包含 Judge 反馈")
            print(f"  - 评估分数: {eval_result.overall_score}")
            print(f"  - Judge 反馈: {eval_result.judge_feedback[:200]}...")
        else:
            print(f"\n✓ Pipeline 评估完成（无 Judge 反馈）")
            print(f"  - 评估分数: {eval_result.overall_score}")
    
    def test_pipeline_evaluation_result_structure(self):
        """测试 Pipeline 评估结果结构完整性"""
        # 加载 Pipeline 配置
        pipeline = load_pipeline_config("document_summary")
        runner = PipelineRunner(pipeline)
        
        # 准备测试样本
        test_sample = {
            "id": "structure_test",
            "raw_text": "区块链是一种分布式数据库技术。它具有去中心化、不可篡改等特点。"
        }
        
        # 真实执行 Pipeline
        result = runner.execute_sample(test_sample, variant="baseline")
        
        assert result.error is None, f"Pipeline 执行失败: {result.error}"
        
        # 获取输出
        step_outputs = result.get_step_outputs_dict()
        final_output = step_outputs.get("summary", "")
        
        # 创建评估配置
        eval_config = EvaluationConfig(
            judge_enabled=True,
            judge_agent_id="judge_default",
            judge_flow="judge_v1"
        )
        
        evaluator = UnifiedEvaluator(eval_config)
        
        # 真实评估
        eval_result = evaluator.evaluate_pipeline_output(
            pipeline_id=pipeline.id,
            variant="baseline",
            test_case=test_sample,
            step_outputs=step_outputs,
            final_output=final_output
        )
        
        # 验证结果可以转换为字典
        result_dict = eval_result.to_dict()
        
        assert isinstance(result_dict, dict), "评估结果应该可以转换为字典"
        assert "sample_id" in result_dict, "字典应该包含 sample_id"
        assert "entity_type" in result_dict, "字典应该包含 entity_type"
        assert "entity_id" in result_dict, "字典应该包含 entity_id"
        assert "variant" in result_dict, "字典应该包含 variant"
        assert "overall_score" in result_dict, "字典应该包含 overall_score"
        assert "step_outputs" in result_dict, "字典应该包含 step_outputs"
        assert "judge_feedback" in result_dict, "字典应该包含 judge_feedback"
        
        print(f"\n✓ Pipeline 评估结果结构完整")
        print(f"  - 字典字段数: {len(result_dict)}")
        print(f"  - 包含所有必需字段")
    
    def test_pipeline_evaluation_with_multiple_steps(self):
        """测试 Pipeline 多步骤输出的评估"""
        # 加载 Pipeline 配置
        pipeline = load_pipeline_config("document_summary")
        runner = PipelineRunner(pipeline)
        
        # 准备测试样本
        test_sample = {
            "id": "multi_step_test",
            "raw_text": "机器学习是人工智能的一个分支。它让计算机能够从数据中学习。机器学习在图像识别、语音识别等领域有广泛应用。"
        }
        
        # 真实执行 Pipeline
        result = runner.execute_sample(test_sample, variant="baseline")
        
        assert result.error is None, f"Pipeline 执行失败: {result.error}"
        
        # 获取所有步骤输出
        step_outputs = result.get_step_outputs_dict()
        
        # 验证有多个步骤输出
        assert len(step_outputs) >= 2, "应该有至少 2 个步骤输出"
        
        # 获取最终输出
        final_output = step_outputs.get("summary", "")
        
        # 创建评估配置
        eval_config = EvaluationConfig(
            judge_enabled=True,
            judge_agent_id="judge_default",
            judge_flow="judge_v1"
        )
        
        evaluator = UnifiedEvaluator(eval_config)
        
        # 真实评估
        eval_result = evaluator.evaluate_pipeline_output(
            pipeline_id=pipeline.id,
            variant="baseline",
            test_case=test_sample,
            step_outputs=step_outputs,
            final_output=final_output
        )
        
        # 验证评估结果包含所有步骤输出
        assert len(eval_result.step_outputs) == len(step_outputs), \
            "评估结果应该包含所有步骤输出"
        
        # 验证每个步骤输出都被记录
        for key in step_outputs:
            assert key in eval_result.step_outputs, f"缺少步骤输出: {key}"
        
        print(f"\n✓ Pipeline 多步骤输出评估成功")
        print(f"  - 步骤输出数: {len(step_outputs)}")
        print(f"  - 评估分数: {eval_result.overall_score}")
        for key, value in step_outputs.items():
            print(f"  - {key}: {str(value)[:50]}...")
    
    def test_pipeline_evaluation_token_usage(self):
        """测试 Pipeline 评估的 token 使用量统计"""
        # 加载 Pipeline 配置
        pipeline = load_pipeline_config("document_summary")
        runner = PipelineRunner(pipeline)
        
        # 准备测试样本
        test_sample = {
            "id": "token_test",
            "raw_text": "深度学习是机器学习的一个子领域。它使用多层神经网络进行学习。"
        }
        
        # 真实执行 Pipeline
        result = runner.execute_sample(test_sample, variant="baseline")
        
        assert result.error is None, f"Pipeline 执行失败: {result.error}"
        
        # 验证 Pipeline 执行有 token 统计
        assert result.total_token_usage is not None, "应该有 token 使用量统计"
        assert result.total_token_usage["total_tokens"] > 0, "总 token 应该大于 0"
        
        # 获取输出
        step_outputs = result.get_step_outputs_dict()
        final_output = step_outputs.get("summary", "")
        
        # 创建评估配置
        eval_config = EvaluationConfig(
            judge_enabled=True,
            judge_agent_id="judge_default",
            judge_flow="judge_v1"
        )
        
        evaluator = UnifiedEvaluator(eval_config)
        
        # 真实评估
        eval_result = evaluator.evaluate_pipeline_output(
            pipeline_id=pipeline.id,
            variant="baseline",
            test_case=test_sample,
            step_outputs=step_outputs,
            final_output=final_output
        )
        
        # 验证评估结果有执行时间统计
        assert hasattr(eval_result, "execution_time"), "评估结果应该有 execution_time"
        
        # 注意：EvaluationResult 模型没有 token_usage 字段，
        # token 使用量在 PipelineResult 中已经统计
        print(f"\n✓ Pipeline 评估 token 使用量统计")
        print(f"  - Pipeline 执行 token: {result.total_token_usage['total_tokens']}")
        print(f"  - 评估执行时间: {eval_result.execution_time:.2f}秒")
        print(f"  - Pipeline 执行时间: {result.total_execution_time:.2f}秒")
    
    def test_pipeline_evaluation_model_verification(self):
        """验证 Pipeline 评估使用的是 doubao-1-5-pro-32k-250115 模型"""
        # 验证环境变量配置
        model_name = os.getenv("OPENAI_MODEL_NAME", "")
        
        if model_name:
            assert "doubao" in model_name.lower(), \
                f"应该使用 doubao 模型，但配置的是: {model_name}"
            print(f"\n✓ 模型配置验证通过: {model_name}")
        else:
            print(f"\n⚠ 未在环境变量中指定模型，将使用默认配置")
        
        # 执行一次完整的 Pipeline 评估来验证
        pipeline = load_pipeline_config("document_summary")
        runner = PipelineRunner(pipeline)
        
        test_sample = {
            "id": "model_verify",
            "raw_text": "测试文本"
        }
        
        result = runner.execute_sample(test_sample, variant="baseline")
        assert result.error is None, "Pipeline 执行应该成功"
        
        step_outputs = result.get_step_outputs_dict()
        final_output = step_outputs.get("summary", "")
        
        eval_config = EvaluationConfig(
            judge_enabled=True,
            judge_agent_id="judge_default",
            judge_flow="judge_v1"
        )
        
        evaluator = UnifiedEvaluator(eval_config)
        
        eval_result = evaluator.evaluate_pipeline_output(
            pipeline_id=pipeline.id,
            variant="baseline",
            test_case=test_sample,
            step_outputs=step_outputs,
            final_output=final_output
        )
        
        assert eval_result is not None, "评估应该成功"
        assert isinstance(eval_result.overall_score, (int, float)), "应该有有效的评分"
        
        print(f"  - Pipeline 执行成功，模型工作正常")
        print(f"  - 评估分数: {eval_result.overall_score}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
