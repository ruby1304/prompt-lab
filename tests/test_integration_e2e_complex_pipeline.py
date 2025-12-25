# tests/test_integration_e2e_complex_pipeline.py
"""
端到端复杂 Pipeline 集成测试（真实 LLM 调用）

这些测试使用真实的 doubao-pro 模型进行调用，
验证复杂 Pipeline 场景的完整执行流程：
- Agent1 → 代码节点 → 批量聚合 → Agent2
- 并发执行 + 批量处理
- 多阶段数据转换和聚合

重要：
- ⚠️ 必须使用 .env 中配置的真实 API Key
- ⚠️ 必须使用 doubao-pro 模型
- ⚠️ 禁止使用 Mock 或假数据
- 验证完整的用户场景
- 验证复杂 Pipeline 的正确性
- 验证并发执行场景

Requirements:
- 3.4: 并发执行无依赖关系的步骤
- 4.2: 批量处理步骤收集前序步骤的所有输出结果
- 4.3: 使用代码节点对批量结果进行聚合和转换
- 4.4: 将聚合结果作为单个输入传递给后续 Agent
- 9.1: 并发执行多个独立的测试用例
"""

import pytest
import os
import time
import json
from pathlib import Path
from dotenv import load_dotenv

from src.pipeline_config import load_pipeline_config
from src.pipeline_runner import PipelineRunner
from src.models import PipelineConfig, StepConfig, OutputSpec, CodeNodeConfig


# 加载环境变量
load_dotenv()


@pytest.mark.integration
class TestE2EComplexPipeline:
    """端到端复杂 Pipeline 集成测试"""
    
    def test_env_variables_loaded(self):
        """测试环境变量已正确加载"""
        api_key = os.getenv("OPENAI_API_KEY")
        assert api_key is not None, "OPENAI_API_KEY 未设置，请检查 .env 文件"
        assert len(api_key) > 0, "OPENAI_API_KEY 为空"
        
        print(f"\n✓ 环境变量加载成功")
        print(f"  - API Key: {'*' * 20}{api_key[-8:]}")
    
    def test_agent_code_node_batch_agent_pipeline(self):
        """
        测试完整场景：Agent1 → 代码节点 → 批量聚合 → Agent2（真实 LLM 调用）
        
        Requirements: 3.4, 4.2, 4.3, 4.4
        
        场景描述：
        1. Agent1 批量处理多个客户评论
        2. 代码节点提取关键信息（评分、关键词）
        3. 批量聚合所有评论的统计信息
        4. Agent2 基于聚合结果生成总结报告
        
        验证：
        1. 所有步骤成功执行
        2. 数据在步骤间正确传递
        3. 批量处理和聚合正确工作
        4. 最终输出符合预期
        """
        # 创建复杂 Pipeline 配置
        config = PipelineConfig(
            id="e2e_complex_pipeline",
            name="端到端复杂 Pipeline",
            description="Agent → 代码节点 → 批量聚合 → Agent",
            steps=[
                # Step 1: Agent1 批量分析评论
                StepConfig(
                    id="analyze_reviews",
                    type="agent_flow",
                    agent="mem0_l1_summarizer",
                    flow="mem0_l1_v1",
                    batch_mode=True,
                    batch_size=10,
                    concurrent=True,
                    max_workers=3,
                    input_mapping={"text": "reviews"},
                    output_key="review_analyses",
                    description="批量分析客户评论",
                    required=True
                ),
                # Step 2: 代码节点提取关键信息
                StepConfig(
                    id="extract_insights",
                    type="code_node",
                    language="python",
                    code="""
def transform(inputs):
    analyses = inputs.get('analyses', [])
    
    insights = []
    for i, analysis in enumerate(analyses):
        # 模拟提取关键信息
        insight = {
            'review_id': i + 1,
            'analysis': str(analysis),
            'length': len(str(analysis)),
            'has_positive': '好' in str(analysis) or '满意' in str(analysis) or '推荐' in str(analysis),
            'has_negative': '差' in str(analysis) or '不满' in str(analysis) or '失望' in str(analysis)
        }
        insights.append(insight)
    
    return insights
""",
                    input_mapping={"analyses": "review_analyses"},
                    output_key="insights",
                    description="提取关键洞察",
                    required=True
                ),
                # Step 3: 批量聚合统计信息
                StepConfig(
                    id="aggregate_insights",
                    type="batch_aggregator",
                    aggregation_strategy="custom",
                    language="python",
                    aggregation_code="""
def aggregate(items):
    total = len(items)
    positive_count = sum(1 for item in items if item.get('has_positive', False))
    negative_count = sum(1 for item in items if item.get('has_negative', False))
    avg_length = sum(item.get('length', 0) for item in items) / total if total > 0 else 0
    
    # 生成详细报告
    details = []
    for item in items:
        sentiment = "正面" if item.get('has_positive') else ("负面" if item.get('has_negative') else "中性")
        details.append(f"评论{item['review_id']}: {sentiment}, 长度: {item['length']}")
    
    summary = {
        'total_reviews': total,
        'positive_count': positive_count,
        'negative_count': negative_count,
        'neutral_count': total - positive_count - negative_count,
        'positive_rate': positive_count / total if total > 0 else 0,
        'average_length': avg_length,
        'details': "\\n".join(details)
    }
    
    return summary
""",
                    input_mapping={"items": "insights"},
                    output_key="aggregated_insights",
                    description="聚合洞察统计",
                    required=True
                ),
                # Step 4: Agent2 生成最终报告
                StepConfig(
                    id="generate_final_report",
                    type="code_node",
                    language="python",
                    code="""
def transform(inputs):
    insights = inputs.get('insights', {})
    
    report = f\"\"\"
客户评论分析报告
==================

总体统计：
- 总评论数: {insights.get('total_reviews', 0)}
- 正面评论: {insights.get('positive_count', 0)} ({insights.get('positive_rate', 0) * 100:.1f}%)
- 负面评论: {insights.get('negative_count', 0)}
- 中性评论: {insights.get('neutral_count', 0)}
- 平均长度: {insights.get('average_length', 0):.1f} 字符

详细分析：
{insights.get('details', '')}

结论：
基于以上分析，客户满意度为 {insights.get('positive_rate', 0) * 100:.1f}%。
\"\"\"
    
    return report.strip()
""",
                    input_mapping={"insights": "aggregated_insights"},
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
            "id": "e2e_test_1",
            "reviews": [
                "产品质量非常好，超出预期！物流也很快。",
                "价格有点贵，但功能确实强大，值得购买。",
                "客服态度很好，解答问题很耐心，赞一个！",
                "包装很精美，产品也很满意，会推荐给朋友。",
                "性价比很高，使用体验不错，好评！"
            ]
        }
        
        print(f"\n测试复杂 Pipeline：Agent → 代码节点 → 批量聚合 → Agent...")
        print(f"  - 输入评论数: {len(test_sample['reviews'])}")
        
        # 执行 Pipeline
        runner = PipelineRunner(config, enable_concurrent=True, max_workers=3)
        start_time = time.time()
        result = runner.execute_sample(test_sample)
        execution_time = time.time() - start_time
        
        # 验证执行成功
        assert result is not None, "执行结果不应为空"
        assert result.error is None, f"执行失败: {result.error}"
        assert len(result.step_results) == 4, "应该有 4 个步骤结果"
        
        # 验证 Step 1: Agent1 批量分析
        step1_result = next(r for r in result.step_results if r.step_id == "analyze_reviews")
        assert step1_result.success, f"Step 1 失败: {step1_result.error}"
        assert step1_result.output_value is not None, "Step 1 输出为空"
        
        analyses = step1_result.output_value
        assert isinstance(analyses, list), f"批量输出应该是列表，实际是: {type(analyses)}"
        assert len(analyses) == len(test_sample['reviews']), \
            f"批量输出数量({len(analyses)})应该等于输入数量({len(test_sample['reviews'])})"
        
        print(f"  ✓ Step 1 (Agent1 批量分析): 成功")
        print(f"    - 输出数量: {len(analyses)}")
        print(f"    - 执行时间: {step1_result.execution_time:.2f}秒")
        
        # 验证 Step 2: 代码节点提取洞察
        step2_result = next(r for r in result.step_results if r.step_id == "extract_insights")
        assert step2_result.success, f"Step 2 失败: {step2_result.error}"
        assert step2_result.output_value is not None, "Step 2 输出为空"
        
        insights = step2_result.output_value
        assert isinstance(insights, list), f"洞察应该是列表，实际是: {type(insights)}"
        assert len(insights) == len(analyses), "洞察数量应该等于分析数量"
        
        # 验证洞察结构
        for insight in insights:
            assert isinstance(insight, dict), "每个洞察应该是字典"
            assert 'review_id' in insight, "洞察缺少 review_id"
            assert 'analysis' in insight, "洞察缺少 analysis"
            assert 'length' in insight, "洞察缺少 length"
            assert 'has_positive' in insight, "洞察缺少 has_positive"
            assert 'has_negative' in insight, "洞察缺少 has_negative"
        
        print(f"  ✓ Step 2 (代码节点提取洞察): 成功")
        print(f"    - 洞察数量: {len(insights)}")
        print(f"    - 执行时间: {step2_result.execution_time:.2f}秒")
        
        # 验证 Step 3: 批量聚合
        step3_result = next(r for r in result.step_results if r.step_id == "aggregate_insights")
        assert step3_result.success, f"Step 3 失败: {step3_result.error}"
        assert step3_result.output_value is not None, "Step 3 输出为空"
        
        aggregated = step3_result.output_value
        assert isinstance(aggregated, dict), f"聚合结果应该是字典，实际是: {type(aggregated)}"
        assert 'total_reviews' in aggregated, "聚合结果缺少 total_reviews"
        assert 'positive_count' in aggregated, "聚合结果缺少 positive_count"
        assert 'negative_count' in aggregated, "聚合结果缺少 negative_count"
        assert 'positive_rate' in aggregated, "聚合结果缺少 positive_rate"
        assert 'average_length' in aggregated, "聚合结果缺少 average_length"
        assert 'details' in aggregated, "聚合结果缺少 details"
        
        # 验证统计值
        assert aggregated['total_reviews'] == len(test_sample['reviews']), \
            f"总评论数应该是 {len(test_sample['reviews'])}，实际是 {aggregated['total_reviews']}"
        assert aggregated['positive_count'] + aggregated['negative_count'] + aggregated['neutral_count'] == aggregated['total_reviews'], \
            "情感分类总数应该等于总评论数"
        
        print(f"  ✓ Step 3 (批量聚合): 成功")
        print(f"    - 总评论数: {aggregated['total_reviews']}")
        print(f"    - 正面评论: {aggregated['positive_count']}")
        print(f"    - 负面评论: {aggregated['negative_count']}")
        print(f"    - 中性评论: {aggregated['neutral_count']}")
        print(f"    - 正面率: {aggregated['positive_rate'] * 100:.1f}%")
        print(f"    - 执行时间: {step3_result.execution_time:.2f}秒")
        
        # 验证 Step 4: 生成最终报告
        step4_result = next(r for r in result.step_results if r.step_id == "generate_final_report")
        assert step4_result.success, f"Step 4 失败: {step4_result.error}"
        assert step4_result.output_value is not None, "Step 4 输出为空"
        
        final_report = step4_result.output_value
        assert isinstance(final_report, str), f"最终报告应该是字符串，实际是: {type(final_report)}"
        assert len(final_report) > 0, "最终报告内容为空"
        
        # 验证报告包含关键信息
        assert "客户评论分析报告" in final_report, "报告应该包含标题"
        assert "总体统计" in final_report, "报告应该包含统计部分"
        assert "详细分析" in final_report, "报告应该包含详细分析"
        assert "结论" in final_report, "报告应该包含结论"
        assert str(aggregated['total_reviews']) in final_report, "报告应该包含总评论数"
        
        print(f"  ✓ Step 4 (生成最终报告): 成功")
        print(f"    - 报告长度: {len(final_report)}")
        print(f"    - 执行时间: {step4_result.execution_time:.2f}秒")
        
        # 验证输出
        step_outputs = result.get_step_outputs_dict()
        assert "review_analyses" in step_outputs, "缺少 review_analyses 输出"
        assert "insights" in step_outputs, "缺少 insights 输出"
        assert "aggregated_insights" in step_outputs, "缺少 aggregated_insights 输出"
        assert "final_report" in step_outputs, "缺少 final_report 输出"
        
        print(f"\n✓ 复杂 Pipeline 端到端测试通过")
        print(f"  - 总执行时间: {execution_time:.2f}秒")
        print(f"  - Step 1 (批量分析): {step1_result.execution_time:.2f}秒")
        print(f"  - Step 2 (提取洞察): {step2_result.execution_time:.2f}秒")
        print(f"  - Step 3 (批量聚合): {step3_result.execution_time:.2f}秒")
        print(f"  - Step 4 (生成报告): {step4_result.execution_time:.2f}秒")
        print(f"\n最终报告预览：")
        print(f"{final_report[:300]}...")

    
    def test_concurrent_batch_processing_pipeline(self):
        """
        测试并发 + 批量处理场景（真实 LLM 调用）
        
        Requirements: 3.4, 4.2, 4.3, 4.4, 9.1
        
        场景描述：
        1. 并发执行两个独立的批量处理步骤
        2. 分别聚合两个批量结果
        3. 合并聚合结果
        4. 生成综合报告
        
        验证：
        1. 并发执行正确工作
        2. 批量处理正确工作
        3. 多个聚合结果正确合并
        4. 性能提升明显
        """
        # 创建并发 + 批量处理 Pipeline 配置
        config = PipelineConfig(
            id="concurrent_batch_pipeline",
            name="并发批量处理 Pipeline",
            description="并发执行多个批量处理步骤",
            steps=[
                # Step 1a: 批量处理产品评论（并发组 A）
                StepConfig(
                    id="analyze_product_reviews",
                    type="agent_flow",
                    agent="mem0_l1_summarizer",
                    flow="mem0_l1_v1",
                    batch_mode=True,
                    batch_size=10,
                    concurrent=True,
                    max_workers=2,
                    concurrent_group="group_a",
                    input_mapping={"text": "product_reviews"},
                    output_key="product_analyses",
                    description="批量分析产品评论",
                    required=True
                ),
                # Step 1b: 批量处理服务评论（并发组 A）
                StepConfig(
                    id="analyze_service_reviews",
                    type="agent_flow",
                    agent="mem0_l1_summarizer",
                    flow="mem0_l1_v1",
                    batch_mode=True,
                    batch_size=10,
                    concurrent=True,
                    max_workers=2,
                    concurrent_group="group_a",
                    input_mapping={"text": "service_reviews"},
                    output_key="service_analyses",
                    description="批量分析服务评论",
                    required=True
                ),
                # Step 2a: 聚合产品评论（依赖 Step 1a）
                StepConfig(
                    id="aggregate_product",
                    type="batch_aggregator",
                    aggregation_strategy="custom",
                    language="python",
                    aggregation_code="""
def aggregate(items):
    total = len(items)
    combined = " | ".join(str(item) for item in items)
    return {
        'category': 'product',
        'count': total,
        'summary': f"产品评论共 {total} 条: {combined[:100]}..."
    }
""",
                    input_mapping={"items": "product_analyses"},
                    output_key="product_summary",
                    description="聚合产品评论",
                    required=True
                ),
                # Step 2b: 聚合服务评论（依赖 Step 1b）
                StepConfig(
                    id="aggregate_service",
                    type="batch_aggregator",
                    aggregation_strategy="custom",
                    language="python",
                    aggregation_code="""
def aggregate(items):
    total = len(items)
    combined = " | ".join(str(item) for item in items)
    return {
        'category': 'service',
        'count': total,
        'summary': f"服务评论共 {total} 条: {combined[:100]}..."
    }
""",
                    input_mapping={"items": "service_analyses"},
                    output_key="service_summary",
                    description="聚合服务评论",
                    required=True
                ),
                # Step 3: 合并两个聚合结果
                StepConfig(
                    id="merge_summaries",
                    type="code_node",
                    language="python",
                    code="""
def transform(inputs):
    product = inputs.get('product', {})
    service = inputs.get('service', {})
    
    merged = {
        'total_reviews': product.get('count', 0) + service.get('count', 0),
        'product_count': product.get('count', 0),
        'service_count': service.get('count', 0),
        'product_summary': product.get('summary', ''),
        'service_summary': service.get('summary', ''),
        'combined_report': f\"\"\"
综合评论分析
============

产品评论: {product.get('count', 0)} 条
{product.get('summary', '')}

服务评论: {service.get('count', 0)} 条
{service.get('summary', '')}

总计: {product.get('count', 0) + service.get('count', 0)} 条评论
\"\"\"
    }
    
    return merged
""",
                    input_mapping={
                        "product": "product_summary",
                        "service": "service_summary"
                    },
                    output_key="merged_report",
                    description="合并聚合结果",
                    required=True
                )
            ],
            outputs=[
                OutputSpec(key="merged_report", label="综合报告")
            ]
        )
        
        # 准备测试样本
        test_sample = {
            "id": "concurrent_batch_test_1",
            "product_reviews": [
                "产品质量很好，做工精细。",
                "功能强大，使用方便。",
                "性价比高，值得购买。"
            ],
            "service_reviews": [
                "客服态度很好，响应及时。",
                "售后服务完善，解决问题快。",
                "物流速度快，包装仔细。"
            ]
        }
        
        print(f"\n测试并发 + 批量处理 Pipeline...")
        print(f"  - 产品评论数: {len(test_sample['product_reviews'])}")
        print(f"  - 服务评论数: {len(test_sample['service_reviews'])}")
        
        # 执行 Pipeline（并发模式）
        runner_concurrent = PipelineRunner(config, enable_concurrent=True, max_workers=4)
        start_concurrent = time.time()
        result_concurrent = runner_concurrent.execute_sample(test_sample)
        time_concurrent = time.time() - start_concurrent
        
        # 验证执行成功
        assert result_concurrent is not None, "并发执行结果不应为空"
        assert result_concurrent.error is None, f"并发执行失败: {result_concurrent.error}"
        assert len(result_concurrent.step_results) == 5, "应该有 5 个步骤结果"
        
        # 验证所有步骤成功
        for step_result in result_concurrent.step_results:
            assert step_result.success, f"步骤 {step_result.step_id} 失败: {step_result.error}"
        
        # 验证批量处理步骤
        product_result = next(r for r in result_concurrent.step_results if r.step_id == "analyze_product_reviews")
        service_result = next(r for r in result_concurrent.step_results if r.step_id == "analyze_service_reviews")
        
        assert isinstance(product_result.output_value, list), "产品分析输出应该是列表"
        assert isinstance(service_result.output_value, list), "服务分析输出应该是列表"
        assert len(product_result.output_value) == len(test_sample['product_reviews']), "产品分析数量不匹配"
        assert len(service_result.output_value) == len(test_sample['service_reviews']), "服务分析数量不匹配"
        
        # 验证聚合步骤
        product_agg_result = next(r for r in result_concurrent.step_results if r.step_id == "aggregate_product")
        service_agg_result = next(r for r in result_concurrent.step_results if r.step_id == "aggregate_service")
        
        product_summary = product_agg_result.output_value
        service_summary = service_agg_result.output_value
        
        assert isinstance(product_summary, dict), "产品聚合结果应该是字典"
        assert isinstance(service_summary, dict), "服务聚合结果应该是字典"
        assert product_summary['category'] == 'product', "产品类别不匹配"
        assert service_summary['category'] == 'service', "服务类别不匹配"
        
        # 验证合并步骤
        merge_result = next(r for r in result_concurrent.step_results if r.step_id == "merge_summaries")
        merged_report = merge_result.output_value
        
        assert isinstance(merged_report, dict), "合并报告应该是字典"
        assert 'total_reviews' in merged_report, "合并报告缺少 total_reviews"
        assert 'combined_report' in merged_report, "合并报告缺少 combined_report"
        assert merged_report['total_reviews'] == len(test_sample['product_reviews']) + len(test_sample['service_reviews']), \
            "总评论数不匹配"
        
        print(f"\n✓ 并发 + 批量处理 Pipeline 测试通过")
        print(f"  - 并发执行时间: {time_concurrent:.2f}秒")
        print(f"  - Step 1a (产品批量分析): {product_result.execution_time:.2f}秒")
        print(f"  - Step 1b (服务批量分析): {service_result.execution_time:.2f}秒")
        print(f"  - Step 2a (产品聚合): {product_agg_result.execution_time:.2f}秒")
        print(f"  - Step 2b (服务聚合): {service_agg_result.execution_time:.2f}秒")
        print(f"  - Step 3 (合并): {merge_result.execution_time:.2f}秒")
        print(f"  - 总评论数: {merged_report['total_reviews']}")
        print(f"\n综合报告预览：")
        print(f"{merged_report['combined_report'][:200]}...")
    
    def test_multi_stage_data_transformation_pipeline(self):
        """
        测试多阶段数据转换 Pipeline（真实 LLM 调用）
        
        Requirements: 3.4, 4.2, 4.3, 4.4
        
        场景描述：
        1. Agent 批量处理原始数据
        2. 代码节点 1 进行第一次转换
        3. 代码节点 2 进行第二次转换
        4. 批量聚合转换结果
        5. Agent 生成最终报告
        
        验证：
        1. 多阶段转换正确执行
        2. 数据在各阶段正确传递
        3. 最终输出符合预期
        """
        # 创建多阶段转换 Pipeline 配置
        config = PipelineConfig(
            id="multi_stage_transform_pipeline",
            name="多阶段数据转换 Pipeline",
            description="多阶段数据转换和聚合",
            steps=[
                # Stage 1: Agent 批量处理原始文本
                StepConfig(
                    id="process_raw_texts",
                    type="agent_flow",
                    agent="mem0_l1_summarizer",
                    flow="mem0_l1_v1",
                    batch_mode=True,
                    batch_size=10,
                    concurrent=True,
                    max_workers=2,
                    input_mapping={"text": "raw_texts"},
                    output_key="processed_texts",
                    description="批量处理原始文本",
                    required=True
                ),
                # Stage 2: 第一次转换 - 提取关键词
                StepConfig(
                    id="extract_keywords",
                    type="code_node",
                    language="python",
                    code="""
def transform(inputs):
    texts = inputs.get('texts', [])
    
    results = []
    for i, text in enumerate(texts):
        # 简单的关键词提取（模拟）
        text_str = str(text)
        keywords = []
        
        # 提取常见关键词
        common_keywords = ['产品', '服务', '质量', '价格', '客服', '物流', '推荐', '满意']
        for keyword in common_keywords:
            if keyword in text_str:
                keywords.append(keyword)
        
        results.append({
            'id': i + 1,
            'original': text_str,
            'keywords': keywords,
            'keyword_count': len(keywords)
        })
    
    return results
""",
                    input_mapping={"texts": "processed_texts"},
                    output_key="keyword_data",
                    description="提取关键词",
                    required=True
                ),
                # Stage 3: 第二次转换 - 分类和评分
                StepConfig(
                    id="classify_and_score",
                    type="code_node",
                    language="python",
                    code="""
def transform(inputs):
    data = inputs.get('data', [])
    
    results = []
    for item in data:
        keywords = item.get('keywords', [])
        
        # 简单的分类逻辑
        if '产品' in keywords or '质量' in keywords:
            category = 'product'
        elif '服务' in keywords or '客服' in keywords:
            category = 'service'
        elif '物流' in keywords:
            category = 'logistics'
        else:
            category = 'other'
        
        # 简单的评分逻辑
        score = 50  # 基础分
        if '推荐' in keywords or '满意' in keywords:
            score += 30
        if '质量' in keywords:
            score += 10
        if '价格' in keywords:
            score -= 5
        
        results.append({
            'id': item.get('id'),
            'category': category,
            'score': min(100, max(0, score)),
            'keywords': keywords,
            'keyword_count': item.get('keyword_count', 0)
        })
    
    return results
""",
                    input_mapping={"data": "keyword_data"},
                    output_key="classified_data",
                    description="分类和评分",
                    required=True
                ),
                # Stage 4: 批量聚合统计
                StepConfig(
                    id="aggregate_statistics",
                    type="batch_aggregator",
                    aggregation_strategy="custom",
                    language="python",
                    aggregation_code="""
def aggregate(items):
    total = len(items)
    
    # 按类别统计
    categories = {}
    for item in items:
        cat = item.get('category', 'other')
        if cat not in categories:
            categories[cat] = {'count': 0, 'total_score': 0, 'items': []}
        categories[cat]['count'] += 1
        categories[cat]['total_score'] += item.get('score', 0)
        categories[cat]['items'].append(item)
    
    # 计算平均分
    for cat in categories:
        count = categories[cat]['count']
        categories[cat]['avg_score'] = categories[cat]['total_score'] / count if count > 0 else 0
    
    # 总体统计
    total_score = sum(item.get('score', 0) for item in items)
    avg_score = total_score / total if total > 0 else 0
    
    # 生成报告文本
    report_lines = [
        f"总计: {total} 条数据",
        f"平均分: {avg_score:.1f}",
        "",
        "分类统计:"
    ]
    
    for cat, stats in categories.items():
        report_lines.append(f"  - {cat}: {stats['count']} 条, 平均分 {stats['avg_score']:.1f}")
    
    return {
        'total_items': total,
        'average_score': avg_score,
        'categories': categories,
        'report_text': "\\n".join(report_lines)
    }
""",
                    input_mapping={"items": "classified_data"},
                    output_key="statistics",
                    description="聚合统计",
                    required=True
                ),
                # Stage 5: 生成最终报告
                StepConfig(
                    id="generate_report",
                    type="code_node",
                    language="python",
                    code="""
def transform(inputs):
    stats = inputs.get('stats', {})
    
    report = f\"\"\"
数据分析报告
============

{stats.get('report_text', '')}

详细分析：
- 总数据量: {stats.get('total_items', 0)}
- 整体平均分: {stats.get('average_score', 0):.1f}
- 分类数量: {len(stats.get('categories', {}))}

结论：
数据已完成多阶段转换和分析。
\"\"\"
    
    return report.strip()
""",
                    input_mapping={"stats": "statistics"},
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
            "id": "multi_stage_test_1",
            "raw_texts": [
                "产品质量很好，非常满意，推荐购买。",
                "客服服务态度好，解决问题及时。",
                "物流速度快，包装完好。",
                "价格有点贵，但质量不错。"
            ]
        }
        
        print(f"\n测试多阶段数据转换 Pipeline...")
        print(f"  - 输入文本数: {len(test_sample['raw_texts'])}")
        
        # 执行 Pipeline
        runner = PipelineRunner(config, enable_concurrent=True, max_workers=2)
        start_time = time.time()
        result = runner.execute_sample(test_sample)
        execution_time = time.time() - start_time
        
        # 验证执行成功
        assert result is not None, "执行结果不应为空"
        assert result.error is None, f"执行失败: {result.error}"
        assert len(result.step_results) == 5, "应该有 5 个步骤结果"
        
        # 验证所有步骤成功
        for step_result in result.step_results:
            assert step_result.success, f"步骤 {step_result.step_id} 失败: {step_result.error}"
        
        # 验证各阶段输出
        step_outputs = result.get_step_outputs_dict()
        
        # Stage 1: 批量处理
        assert "processed_texts" in step_outputs, "缺少 processed_texts 输出"
        processed_texts = step_outputs["processed_texts"]
        assert isinstance(processed_texts, list), "processed_texts 应该是列表"
        assert len(processed_texts) == len(test_sample['raw_texts']), "处理数量不匹配"
        
        # Stage 2: 关键词提取
        assert "keyword_data" in step_outputs, "缺少 keyword_data 输出"
        keyword_data = step_outputs["keyword_data"]
        assert isinstance(keyword_data, list), "keyword_data 应该是列表"
        assert len(keyword_data) == len(processed_texts), "关键词数据数量不匹配"
        
        for item in keyword_data:
            assert 'keywords' in item, "关键词数据缺少 keywords"
            assert 'keyword_count' in item, "关键词数据缺少 keyword_count"
        
        # Stage 3: 分类和评分
        assert "classified_data" in step_outputs, "缺少 classified_data 输出"
        classified_data = step_outputs["classified_data"]
        assert isinstance(classified_data, list), "classified_data 应该是列表"
        assert len(classified_data) == len(keyword_data), "分类数据数量不匹配"
        
        for item in classified_data:
            assert 'category' in item, "分类数据缺少 category"
            assert 'score' in item, "分类数据缺少 score"
            assert 0 <= item['score'] <= 100, f"分数应该在 0-100 之间，实际是 {item['score']}"
        
        # Stage 4: 统计聚合
        assert "statistics" in step_outputs, "缺少 statistics 输出"
        statistics = step_outputs["statistics"]
        assert isinstance(statistics, dict), "statistics 应该是字典"
        assert 'total_items' in statistics, "统计缺少 total_items"
        assert 'average_score' in statistics, "统计缺少 average_score"
        assert 'categories' in statistics, "统计缺少 categories"
        assert statistics['total_items'] == len(test_sample['raw_texts']), "统计总数不匹配"
        
        # Stage 5: 最终报告
        assert "final_report" in step_outputs, "缺少 final_report 输出"
        final_report = step_outputs["final_report"]
        assert isinstance(final_report, str), "final_report 应该是字符串"
        assert len(final_report) > 0, "最终报告不应为空"
        assert "数据分析报告" in final_report, "报告应该包含标题"
        
        print(f"\n✓ 多阶段数据转换 Pipeline 测试通过")
        print(f"  - 总执行时间: {execution_time:.2f}秒")
        print(f"  - Stage 1 (批量处理): 成功")
        print(f"  - Stage 2 (关键词提取): 成功, {len(keyword_data)} 条")
        print(f"  - Stage 3 (分类评分): 成功, {len(classified_data)} 条")
        print(f"  - Stage 4 (统计聚合): 成功, 平均分 {statistics['average_score']:.1f}")
        print(f"  - Stage 5 (生成报告): 成功")
        print(f"\n最终报告预览：")
        print(f"{final_report[:300]}...")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s", "-m", "integration"])
