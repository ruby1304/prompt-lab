# tests/test_integration_batch_pipeline.py
"""
批量 Pipeline 集成测试（真实 LLM 调用）

这些测试使用真实的 doubao-pro 模型进行调用，
验证批量处理的完整流程：Agent1 → 聚合 → Agent2

重要：
- ⚠️ 必须使用 .env 中配置的真实 API Key
- ⚠️ 必须使用 doubao-pro 模型
- ⚠️ 禁止使用 Mock 或假数据
- 验证批量处理流程的正确性
- 验证聚合功能的正确性
- 验证结果传递的正确性

Requirements:
- 4.2: 批量处理步骤收集前序步骤的所有输出结果
- 4.3: 使用代码节点对批量结果进行聚合和转换
- 4.4: 将聚合结果作为单个输入传递给后续 Agent
"""

import pytest
import os
import time
import json
from pathlib import Path
from dotenv import load_dotenv

from src.pipeline_config import load_pipeline_config
from src.pipeline_runner import PipelineRunner
from src.models import PipelineConfig, StepConfig, OutputSpec


# 加载环境变量
load_dotenv()


@pytest.mark.integration
class TestBatchPipelineIntegration:
    """批量 Pipeline 集成测试"""
    
    def test_env_variables_loaded(self):
        """测试环境变量已正确加载"""
        api_key = os.getenv("OPENAI_API_KEY")
        assert api_key is not None, "OPENAI_API_KEY 未设置，请检查 .env 文件"
        assert len(api_key) > 0, "OPENAI_API_KEY 为空"
        
        print(f"\n✓ 环境变量加载成功")
        print(f"  - API Key: {'*' * 20}{api_key[-8:]}")
    
    def test_batch_processing_agent_to_aggregation(self):
        """
        测试批量处理：Agent → 聚合（真实 LLM 调用）
        
        Requirements: 4.2 - 批量处理步骤收集前序步骤的所有输出结果
        
        验证：
        1. Agent 批量处理多个输入
        2. 聚合步骤收集所有输出
        3. 聚合结果正确
        """
        # 创建 Pipeline 配置：批量处理 → 聚合
        config = PipelineConfig(
            id="batch_to_aggregation_test",
            name="批量处理到聚合测试",
            description="测试 Agent 批量处理和聚合",
            steps=[
                # Step 1: 批量处理多个文本（使用真实 Agent）
                StepConfig(
                    id="batch_summarize",
                    type="agent_flow",
                    agent="mem0_l1_summarizer",
                    flow="mem0_l1_v1",
                    batch_mode=True,
                    batch_size=10,
                    concurrent=True,
                    max_workers=3,
                    input_mapping={"text": "reviews"},
                    output_key="summaries",
                    description="批量总结评论",
                    required=True
                ),
                # Step 2: 聚合所有总结
                StepConfig(
                    id="aggregate_summaries",
                    type="batch_aggregator",
                    aggregation_strategy="concat",
                    separator="\n\n",
                    input_mapping={"items": "summaries"},
                    output_key="all_summaries",
                    description="聚合所有总结",
                    required=True
                )
            ],
            outputs=[
                OutputSpec(key="all_summaries", label="所有总结")
            ]
        )
        
        # 准备测试样本（多个评论）
        test_sample = {
            "id": "batch_agg_test_1",
            "reviews": [
                "这个产品质量很好，物流也很快，非常满意！",
                "价格有点贵，但是功能确实强大，值得购买。",
                "客服态度很好，解决问题很及时，赞一个！"
            ]
        }
        
        print(f"\n测试批量处理 → 聚合...")
        print(f"  - 输入评论数: {len(test_sample['reviews'])}")
        
        # 执行 Pipeline
        runner = PipelineRunner(config, enable_concurrent=True, max_workers=3)
        result = runner.execute_sample(test_sample)
        
        # 验证执行成功
        assert result is not None, "执行结果不应为空"
        assert result.error is None, f"执行失败: {result.error}"
        assert len(result.step_results) == 2, "应该有 2 个步骤结果"
        
        # 验证批量处理步骤
        batch_result = next(r for r in result.step_results if r.step_id == "batch_summarize")
        assert batch_result.success, f"批量处理失败: {batch_result.error}"
        assert batch_result.output_value is not None, "批量处理输出为空"
        
        # 验证批量输出是列表
        summaries = batch_result.output_value
        assert isinstance(summaries, list), f"批量输出应该是列表，实际是: {type(summaries)}"
        assert len(summaries) == len(test_sample['reviews']), \
            f"批量输出数量({len(summaries)})应该等于输入数量({len(test_sample['reviews'])})"
        
        # 验证每个总结都不为空
        for i, summary in enumerate(summaries):
            assert summary is not None, f"总结 {i} 为空"
            assert len(str(summary)) > 0, f"总结 {i} 内容为空"
        
        # 验证聚合步骤
        agg_result = next(r for r in result.step_results if r.step_id == "aggregate_summaries")
        assert agg_result.success, f"聚合失败: {agg_result.error}"
        assert agg_result.output_value is not None, "聚合输出为空"
        
        # 验证聚合结果
        all_summaries = agg_result.output_value
        assert isinstance(all_summaries, str), f"聚合输出应该是字符串，实际是: {type(all_summaries)}"
        assert len(all_summaries) > 0, "聚合输出内容为空"
        
        # 验证聚合结果包含分隔符
        assert "\n\n" in all_summaries, "聚合结果应该包含分隔符"
        
        print(f"\n✓ 批量处理 → 聚合测试通过")
        print(f"  - 批量处理输出数: {len(summaries)}")
        print(f"  - 聚合结果长度: {len(all_summaries)}")
        print(f"  - 批量处理时间: {batch_result.execution_time:.2f}秒")
        print(f"  - 聚合时间: {agg_result.execution_time:.2f}秒")

    
    def test_batch_processing_with_custom_aggregation(self):
        """
        测试批量处理：Agent → 自定义聚合（真实 LLM 调用）
        
        Requirements: 4.3 - 使用代码节点对批量结果进行聚合和转换
        
        验证：
        1. Agent 批量处理多个输入
        2. 自定义代码聚合结果
        3. 聚合逻辑正确执行
        """
        # 创建 Pipeline 配置：批量处理 → 自定义聚合
        config = PipelineConfig(
            id="batch_custom_agg_test",
            name="批量处理自定义聚合测试",
            description="测试批量处理和自定义聚合",
            steps=[
                # Step 1: 批量处理多个文本
                StepConfig(
                    id="batch_process",
                    type="agent_flow",
                    agent="mem0_l1_summarizer",
                    flow="mem0_l1_v1",
                    batch_mode=True,
                    batch_size=10,
                    concurrent=True,
                    max_workers=3,
                    input_mapping={"text": "texts"},
                    output_key="processed_texts",
                    description="批量处理文本",
                    required=True
                ),
                # Step 2: 自定义聚合
                StepConfig(
                    id="custom_aggregate",
                    type="batch_aggregator",
                    aggregation_strategy="custom",
                    language="python",
                    aggregation_code="""
def aggregate(items):
    # 统计信息
    total = len(items)
    total_length = sum(len(str(item)) for item in items)
    avg_length = total_length / total if total > 0 else 0
    
    # 拼接所有内容
    combined = " | ".join(str(item) for item in items)
    
    return {
        "total_items": total,
        "total_length": total_length,
        "average_length": avg_length,
        "combined_text": combined
    }
""",
                    input_mapping={"items": "processed_texts"},
                    output_key="aggregated_result",
                    description="自定义聚合",
                    required=True
                )
            ],
            outputs=[
                OutputSpec(key="aggregated_result", label="聚合结果")
            ]
        )
        
        # 准备测试样本
        test_sample = {
            "id": "custom_agg_test_1",
            "texts": [
                "人工智能正在改变世界。",
                "机器学习是人工智能的核心技术。",
                "深度学习推动了AI的快速发展。"
            ]
        }
        
        print(f"\n测试批量处理 → 自定义聚合...")
        print(f"  - 输入文本数: {len(test_sample['texts'])}")
        
        # 执行 Pipeline
        runner = PipelineRunner(config, enable_concurrent=True, max_workers=3)
        result = runner.execute_sample(test_sample)
        
        # 验证执行成功
        assert result is not None, "执行结果不应为空"
        assert result.error is None, f"执行失败: {result.error}"
        assert len(result.step_results) == 2, "应该有 2 个步骤结果"
        
        # 验证批量处理步骤
        batch_result = next(r for r in result.step_results if r.step_id == "batch_process")
        assert batch_result.success, f"批量处理失败: {batch_result.error}"
        
        # 验证自定义聚合步骤
        agg_result = next(r for r in result.step_results if r.step_id == "custom_aggregate")
        assert agg_result.success, f"自定义聚合失败: {agg_result.error}"
        assert agg_result.output_value is not None, "聚合输出为空"
        
        # 验证聚合结果结构
        agg_output = agg_result.output_value
        assert isinstance(agg_output, dict), f"聚合输出应该是字典，实际是: {type(agg_output)}"
        assert "total_items" in agg_output, "聚合结果缺少 total_items"
        assert "total_length" in agg_output, "聚合结果缺少 total_length"
        assert "average_length" in agg_output, "聚合结果缺少 average_length"
        assert "combined_text" in agg_output, "聚合结果缺少 combined_text"
        
        # 验证聚合结果值
        assert agg_output["total_items"] == len(test_sample['texts']), \
            f"total_items 应该是 {len(test_sample['texts'])}，实际是 {agg_output['total_items']}"
        assert agg_output["total_length"] > 0, "total_length 应该大于 0"
        assert agg_output["average_length"] > 0, "average_length 应该大于 0"
        assert len(agg_output["combined_text"]) > 0, "combined_text 不应为空"
        assert " | " in agg_output["combined_text"], "combined_text 应该包含分隔符"
        
        print(f"\n✓ 批量处理 → 自定义聚合测试通过")
        print(f"  - 总项目数: {agg_output['total_items']}")
        print(f"  - 总长度: {agg_output['total_length']}")
        print(f"  - 平均长度: {agg_output['average_length']:.2f}")
        print(f"  - 组合文本长度: {len(agg_output['combined_text'])}")

    
    def test_agent_to_aggregation_to_agent(self):
        """
        测试完整批量流程：Agent1 → 聚合 → Agent2（真实 LLM 调用）
        
        Requirements: 
        - 4.2: 批量处理步骤收集前序步骤的所有输出结果
        - 4.3: 使用代码节点对批量结果进行聚合和转换
        - 4.4: 将聚合结果作为单个输入传递给后续 Agent
        
        验证：
        1. Agent1 批量处理多个输入
        2. 聚合步骤收集所有输出并聚合
        3. Agent2 接收聚合结果作为输入
        4. 整个流程成功执行
        """
        # 创建 Pipeline 配置：Agent1 → 聚合 → Agent2
        config = PipelineConfig(
            id="agent_agg_agent_test",
            name="Agent → 聚合 → Agent 测试",
            description="测试完整的批量处理流程",
            steps=[
                # Step 1: Agent1 批量处理多个评论
                StepConfig(
                    id="analyze_reviews",
                    type="agent_flow",
                    agent="mem0_l1_summarizer",
                    flow="mem0_l1_v1",
                    batch_mode=True,
                    batch_size=10,
                    concurrent=True,
                    max_workers=3,
                    input_mapping={"text": "customer_reviews"},
                    output_key="review_analyses",
                    description="分析每条评论",
                    required=True
                ),
                # Step 2: 聚合所有分析结果
                StepConfig(
                    id="aggregate_analyses",
                    type="batch_aggregator",
                    aggregation_strategy="custom",
                    language="python",
                    aggregation_code="""
def aggregate(items):
    # 统计分析
    total = len(items)
    
    # 拼接所有分析
    all_analyses = []
    for i, item in enumerate(items, 1):
        all_analyses.append(f"评论{i}: {item}")
    
    combined = "\\n\\n".join(all_analyses)
    
    # 生成摘要
    summary = f"共分析了 {total} 条评论。以下是详细分析：\\n\\n{combined}"
    
    return summary
""",
                    input_mapping={"items": "review_analyses"},
                    output_key="analysis_summary",
                    description="聚合所有分析",
                    required=True
                ),
                # Step 3: Agent2 基于聚合结果生成最终报告
                StepConfig(
                    id="generate_report",
                    type="agent_flow",
                    agent="mem0_l1_summarizer",
                    flow="mem0_l1_v1",
                    input_mapping={"text": "analysis_summary"},
                    output_key="final_report",
                    description="生成最终报告",
                    required=True
                )
            ],
            outputs=[
                OutputSpec(key="final_report", label="最终报告")
            ]
        )
        
        # 准备测试样本
        test_sample = {
            "id": "full_flow_test_1",
            "customer_reviews": [
                "产品质量非常好，超出预期！",
                "物流速度很快，包装也很仔细。",
                "客服态度很好，解答问题很耐心。",
                "性价比很高，值得推荐！"
            ]
        }
        
        print(f"\n测试完整批量流程：Agent1 → 聚合 → Agent2...")
        print(f"  - 输入评论数: {len(test_sample['customer_reviews'])}")
        
        # 执行 Pipeline
        runner = PipelineRunner(config, enable_concurrent=True, max_workers=3)
        start_time = time.time()
        result = runner.execute_sample(test_sample)
        execution_time = time.time() - start_time
        
        # 验证执行成功
        assert result is not None, "执行结果不应为空"
        assert result.error is None, f"执行失败: {result.error}"
        assert len(result.step_results) == 3, "应该有 3 个步骤结果"
        
        # 验证 Step 1: Agent1 批量处理
        step1_result = next(r for r in result.step_results if r.step_id == "analyze_reviews")
        assert step1_result.success, f"Agent1 批量处理失败: {step1_result.error}"
        assert step1_result.output_value is not None, "Agent1 输出为空"
        
        # 验证批量输出是列表
        analyses = step1_result.output_value
        assert isinstance(analyses, list), f"批量输出应该是列表，实际是: {type(analyses)}"
        assert len(analyses) == len(test_sample['customer_reviews']), \
            f"批量输出数量({len(analyses)})应该等于输入数量({len(test_sample['customer_reviews'])})"
        
        # 验证每个分析都不为空
        for i, analysis in enumerate(analyses):
            assert analysis is not None, f"分析 {i} 为空"
            assert len(str(analysis)) > 0, f"分析 {i} 内容为空"
        
        print(f"  ✓ Step 1 (Agent1 批量处理): 成功")
        print(f"    - 输出数量: {len(analyses)}")
        print(f"    - 执行时间: {step1_result.execution_time:.2f}秒")
        
        # 验证 Step 2: 聚合
        step2_result = next(r for r in result.step_results if r.step_id == "aggregate_analyses")
        assert step2_result.success, f"聚合失败: {step2_result.error}"
        assert step2_result.output_value is not None, "聚合输出为空"
        
        # 验证聚合结果是字符串
        summary = step2_result.output_value
        assert isinstance(summary, str), f"聚合输出应该是字符串，实际是: {type(summary)}"
        assert len(summary) > 0, "聚合输出内容为空"
        
        # 验证聚合结果包含预期内容
        assert "共分析了" in summary, "聚合结果应该包含统计信息"
        assert str(len(test_sample['customer_reviews'])) in summary, "聚合结果应该包含评论数量"
        
        print(f"  ✓ Step 2 (聚合): 成功")
        print(f"    - 聚合结果长度: {len(summary)}")
        print(f"    - 执行时间: {step2_result.execution_time:.2f}秒")
        
        # 验证 Step 3: Agent2 生成报告
        step3_result = next(r for r in result.step_results if r.step_id == "generate_report")
        assert step3_result.success, f"Agent2 生成报告失败: {step3_result.error}"
        assert step3_result.output_value is not None, "Agent2 输出为空"
        
        # 验证最终报告
        final_report = step3_result.output_value
        assert isinstance(final_report, str), f"最终报告应该是字符串，实际是: {type(final_report)}"
        assert len(final_report) > 0, "最终报告内容为空"
        
        print(f"  ✓ Step 3 (Agent2 生成报告): 成功")
        print(f"    - 报告长度: {len(final_report)}")
        print(f"    - 执行时间: {step3_result.execution_time:.2f}秒")
        
        # 验证输出
        step_outputs = result.get_step_outputs_dict()
        assert "review_analyses" in step_outputs, "缺少 review_analyses 输出"
        assert "analysis_summary" in step_outputs, "缺少 analysis_summary 输出"
        assert "final_report" in step_outputs, "缺少 final_report 输出"
        
        print(f"\n✓ 完整批量流程测试通过")
        print(f"  - 总执行时间: {execution_time:.2f}秒")
        print(f"  - Step 1 (批量处理): {step1_result.execution_time:.2f}秒")
        print(f"  - Step 2 (聚合): {step2_result.execution_time:.2f}秒")
        print(f"  - Step 3 (生成报告): {step3_result.execution_time:.2f}秒")
        print(f"  - 批量输出数: {len(analyses)}")
        print(f"  - 聚合结果长度: {len(summary)}")
        print(f"  - 最终报告长度: {len(final_report)}")

    
    def test_batch_processing_with_stats_aggregation(self):
        """
        测试批量处理：Agent → 统计聚合 → Agent（真实 LLM 调用）
        
        Requirements: 4.2, 4.3, 4.4
        
        验证：
        1. Agent 批量处理多个输入
        2. 统计聚合收集数值信息
        3. Agent 基于统计信息生成报告
        """
        # 创建 Pipeline 配置：Agent1 → 统计聚合 → Agent2
        config = PipelineConfig(
            id="batch_stats_test",
            name="批量统计聚合测试",
            description="测试批量处理和统计聚合",
            steps=[
                # Step 1: 批量处理（模拟生成带数值的结果）
                StepConfig(
                    id="process_items",
                    type="code_node",
                    language="python",
                    code="""
def transform(inputs):
    items = inputs.get('items', [])
    results = []
    for i, item in enumerate(items):
        results.append({
            'id': i + 1,
            'text': item,
            'score': (i + 1) * 10,
            'length': len(item)
        })
    return results
""",
                    input_mapping={"items": "input_items"},
                    output_key="processed_items",
                    description="处理项目",
                    required=True
                ),
                # Step 2: 统计聚合
                StepConfig(
                    id="compute_stats",
                    type="batch_aggregator",
                    aggregation_strategy="stats",
                    fields=["score", "length"],
                    input_mapping={"items": "processed_items"},
                    output_key="statistics",
                    description="计算统计信息",
                    required=True
                ),
                # Step 3: 基于统计信息生成报告
                StepConfig(
                    id="generate_stats_report",
                    type="code_node",
                    language="python",
                    code="""
def transform(inputs):
    stats = inputs.get('stats', {})
    fields = stats.get('fields', {})
    
    score_stats = fields.get('score', {})
    length_stats = fields.get('length', {})
    
    report = f\"\"\"统计报告：
总项目数: {stats.get('total_items', 0)}

分数统计:
- 平均值: {score_stats.get('mean', 0):.2f}
- 最小值: {score_stats.get('min', 0)}
- 最大值: {score_stats.get('max', 0)}
- 总和: {score_stats.get('sum', 0)}

长度统计:
- 平均值: {length_stats.get('mean', 0):.2f}
- 最小值: {length_stats.get('min', 0)}
- 最大值: {length_stats.get('max', 0)}
- 总和: {length_stats.get('sum', 0)}
\"\"\"
    return report
""",
                    input_mapping={"stats": "statistics"},
                    output_key="stats_report",
                    description="生成统计报告",
                    required=True
                )
            ],
            outputs=[
                OutputSpec(key="stats_report", label="统计报告")
            ]
        )
        
        # 准备测试样本
        test_sample = {
            "id": "stats_test_1",
            "input_items": [
                "第一个项目",
                "第二个项目内容更长一些",
                "第三个项目",
                "第四个项目的内容",
                "第五个项目"
            ]
        }
        
        print(f"\n测试批量处理 → 统计聚合 → 报告生成...")
        print(f"  - 输入项目数: {len(test_sample['input_items'])}")
        
        # 执行 Pipeline
        runner = PipelineRunner(config, enable_concurrent=False)
        result = runner.execute_sample(test_sample)
        
        # 验证执行成功
        assert result is not None, "执行结果不应为空"
        assert result.error is None, f"执行失败: {result.error}"
        assert len(result.step_results) == 3, "应该有 3 个步骤结果"
        
        # 验证所有步骤成功
        for step_result in result.step_results:
            assert step_result.success, f"步骤 {step_result.step_id} 失败: {step_result.error}"
        
        # 验证统计聚合结果
        stats_result = next(r for r in result.step_results if r.step_id == "compute_stats")
        stats = stats_result.output_value
        assert isinstance(stats, dict), "统计结果应该是字典"
        assert "fields" in stats, "统计结果缺少 fields"
        assert "score" in stats["fields"], "统计结果缺少 score 字段"
        assert "length" in stats["fields"], "统计结果缺少 length 字段"
        
        # 验证统计值
        score_stats = stats["fields"]["score"]
        assert score_stats["mean"] == 30.0, f"平均分数应该是 30.0，实际是 {score_stats['mean']}"
        assert score_stats["min"] == 10, f"最小分数应该是 10，实际是 {score_stats['min']}"
        assert score_stats["max"] == 50, f"最大分数应该是 50，实际是 {score_stats['max']}"
        assert score_stats["sum"] == 150, f"总分数应该是 150，实际是 {score_stats['sum']}"
        
        # 验证报告生成
        report_result = next(r for r in result.step_results if r.step_id == "generate_stats_report")
        report = report_result.output_value
        assert isinstance(report, str), "报告应该是字符串"
        assert "统计报告" in report, "报告应该包含标题"
        assert "总项目数: 5" in report, "报告应该包含项目数"
        assert "平均值: 30.00" in report, "报告应该包含平均分数"
        
        print(f"\n✓ 批量统计聚合测试通过")
        print(f"  - 总项目数: {stats['total_items']}")
        print(f"  - 平均分数: {score_stats['mean']:.2f}")
        print(f"  - 分数范围: {score_stats['min']} - {score_stats['max']}")
        print(f"  - 报告长度: {len(report)}")

    
    def test_batch_processing_error_handling(self):
        """
        测试批量处理的错误处理（真实 LLM 调用）
        
        Requirements: 4.2, 4.3, 4.4
        
        验证：
        1. 批量处理中部分失败不影响其他项
        2. 聚合步骤正确处理部分失败的情况
        3. 可选步骤失败不影响整体流程
        """
        # 创建 Pipeline 配置：包含可选的批量步骤
        config = PipelineConfig(
            id="batch_error_test",
            name="批量错误处理测试",
            description="测试批量处理的错误处理",
            steps=[
                # Step 1: 批量处理（正常步骤）
                StepConfig(
                    id="batch_process_normal",
                    type="agent_flow",
                    agent="mem0_l1_summarizer",
                    flow="mem0_l1_v1",
                    batch_mode=True,
                    batch_size=10,
                    concurrent=True,
                    max_workers=2,
                    input_mapping={"text": "texts"},
                    output_key="processed_texts",
                    description="批量处理文本",
                    required=True
                ),
                # Step 2: 聚合（正常步骤）
                StepConfig(
                    id="aggregate_normal",
                    type="batch_aggregator",
                    aggregation_strategy="concat",
                    separator=" | ",
                    input_mapping={"items": "processed_texts"},
                    output_key="aggregated",
                    description="聚合结果",
                    required=True
                ),
                # Step 3: 可选的代码节点（会失败）
                StepConfig(
                    id="optional_code_node",
                    type="code_node",
                    language="python",
                    code="""
def transform(inputs):
    # 故意引发错误
    raise ValueError("Intentional error for testing")
""",
                    input_mapping={"data": "aggregated"},
                    output_key="optional_results",
                    description="可选的代码节点（会失败）",
                    required=False  # 可选步骤
                ),
                # Step 4: 最终处理（依赖正常步骤）
                StepConfig(
                    id="final_process",
                    type="code_node",
                    language="python",
                    code="""
def transform(inputs):
    aggregated = inputs.get('aggregated', '')
    return {
        'status': 'success',
        'length': len(aggregated),
        'content': aggregated[:100] + '...' if len(aggregated) > 100 else aggregated
    }
""",
                    input_mapping={"aggregated": "aggregated"},
                    output_key="final_result",
                    description="最终处理",
                    required=True
                )
            ],
            outputs=[
                OutputSpec(key="final_result", label="最终结果")
            ]
        )
        
        # 准备测试样本
        test_sample = {
            "id": "error_test_1",
            "texts": [
                "人工智能技术发展迅速。",
                "机器学习应用广泛。",
                "深度学习效果显著。"
            ]
        }
        
        print(f"\n测试批量处理错误处理...")
        print(f"  - 输入文本数: {len(test_sample['texts'])}")
        
        # 执行 Pipeline
        runner = PipelineRunner(config, enable_concurrent=True, max_workers=2)
        result = runner.execute_sample(test_sample)
        
        # 验证执行结果
        assert result is not None, "执行结果不应为空"
        assert len(result.step_results) == 4, "应该有 4 个步骤结果"
        
        # 验证 Step 1 成功
        step1_result = next(r for r in result.step_results if r.step_id == "batch_process_normal")
        assert step1_result.success, f"Step 1 应该成功: {step1_result.error}"
        
        # 验证 Step 2 成功
        step2_result = next(r for r in result.step_results if r.step_id == "aggregate_normal")
        assert step2_result.success, f"Step 2 应该成功: {step2_result.error}"
        
        # 验证 Step 3 失败（可选步骤）
        step3_result = next(r for r in result.step_results if r.step_id == "optional_code_node")
        assert not step3_result.success, "Step 3 应该失败（故意引发错误）"
        assert step3_result.error is not None, "Step 3 应该有错误信息"
        assert "Intentional error" in step3_result.error, "错误信息应该包含预期的错误文本"
        
        # 验证 Step 4 成功（不受 Step 3 失败影响）
        step4_result = next(r for r in result.step_results if r.step_id == "final_process")
        assert step4_result.success, f"Step 4 应该成功（Step 3 是可选的）: {step4_result.error}"
        
        # 验证整个 Pipeline 成功（因为失败的是可选步骤）
        assert result.error is None, f"Pipeline 应该成功（失败的是可选步骤）: {result.error}"
        
        # 验证最终结果
        final_result = step4_result.output_value
        assert isinstance(final_result, dict), "最终结果应该是字典"
        assert final_result["status"] == "success", "状态应该是 success"
        assert final_result["length"] > 0, "长度应该大于 0"
        
        print(f"\n✓ 批量处理错误处理测试通过")
        print(f"  - Step 1 (批量处理): 成功")
        print(f"  - Step 2 (聚合): 成功")
        print(f"  - Step 3 (可选代码节点): 失败（预期）")
        print(f"  - Step 4 (最终处理): 成功")
        print(f"  - Pipeline 整体: 成功（可选步骤失败不影响整体）")
        print(f"  - 最终结果长度: {final_result['length']}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
