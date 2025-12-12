#!/usr/bin/env python3
"""
Pipeline 演示脚本

演示如何使用 Prompt Lab 的 Pipeline 功能：
1. 加载 Pipeline 配置
2. 执行 Pipeline
3. 评估 Pipeline 输出
4. 对比不同变体
5. 保存和加载基线

使用方法：
    python examples/pipeline_demo.py
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
import json

# 添加项目根目录到 Python 路径
sys.path.append(str(Path(__file__).parent.parent))

from src.pipeline_config import load_pipeline_config, list_available_pipelines
from src.pipeline_runner import PipelineRunner, PipelineResult
from src.baseline_manager import save_pipeline_baseline, load_pipeline_baseline
from src.data_manager import DataManager


def print_section(title: str):
    """打印章节标题"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def demo_list_pipelines():
    """演示：列出可用的 Pipeline"""
    print_section("1. 列出可用的 Pipeline")
    
    try:
        pipelines = list_available_pipelines()
        
        if pipelines:
            print(f"✅ 找到 {len(pipelines)} 个 Pipeline:\n")
            for pipeline_id in pipelines:
                print(f"  - {pipeline_id}")
        else:
            print("⚠️  未找到任何 Pipeline 配置")
            print("💡 提示：在 pipelines/ 目录下创建 YAML 配置文件")
            
    except Exception as e:
        print(f"❌ 列出 Pipeline 时出错: {e}")


def demo_load_pipeline(pipeline_id: str = "document_summary"):
    """演示：加载 Pipeline 配置"""
    print_section(f"2. 加载 Pipeline 配置: {pipeline_id}")
    
    try:
        # 加载配置
        config = load_pipeline_config(pipeline_id)
        
        print(f"✅ 成功加载 Pipeline: {config.name}")
        print(f"   描述: {config.description}")
        print(f"   步骤数量: {len(config.steps)}")
        print(f"\n📋 Pipeline 步骤:")
        
        for i, step in enumerate(config.steps, 1):
            print(f"   {i}. {step.id}")
            print(f"      - Agent: {step.agent}")
            print(f"      - Flow: {step.flow}")
            print(f"      - 输出键: {step.output_key}")
            
        # 显示变体信息
        if config.variants:
            print(f"\n🔀 可用变体:")
            for variant_name, variant in config.variants.items():
                print(f"   - {variant_name}: {variant.description}")
                
        return config
        
    except Exception as e:
        print(f"❌ 加载 Pipeline 配置时出错: {e}")
        return None


def demo_load_testset(pipeline_id: str = "document_summary") -> List[Dict[str, Any]]:
    """演示：加载测试集"""
    print_section(f"3. 加载测试集: {pipeline_id}")
    
    try:
        # 使用 DataManager 加载测试集
        data_manager = DataManager()
        testset_path = Path(f"data/pipelines/{pipeline_id}/testsets")
        
        # 查找测试集文件
        testset_files = list(testset_path.glob("*.jsonl"))
        
        if not testset_files:
            print(f"⚠️  未找到测试集文件: {testset_path}")
            return []
            
        # 加载第一个测试集
        testset_file = testset_files[0]
        print(f"📂 加载测试集: {testset_file.name}")
        
        test_cases = []
        with open(testset_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    test_cases.append(json.loads(line))
                    
        print(f"✅ 加载了 {len(test_cases)} 个测试用例")
        
        # 显示第一个测试用例
        if test_cases:
            print(f"\n📝 示例测试用例:")
            first_case = test_cases[0]
            for key, value in first_case.items():
                if key != "tags":
                    value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                    print(f"   {key}: {value_str}")
                    
        return test_cases
        
    except Exception as e:
        print(f"❌ 加载测试集时出错: {e}")
        return []


def demo_run_pipeline(config, test_case: Dict[str, Any], variant: str = "baseline"):
    """演示：执行 Pipeline"""
    print_section(f"4. 执行 Pipeline (变体: {variant})")
    
    try:
        # 创建 Pipeline 执行器
        runner = PipelineRunner(config)
        
        print(f"🚀 开始执行 Pipeline...")
        print(f"   Pipeline: {config.name}")
        print(f"   变体: {variant}")
        print(f"   测试用例 ID: {test_case.get('id', 'N/A')}")
        
        # 执行 Pipeline（使用 execute_sample 方法执行单个样本）
        result = runner.execute_sample(
            sample=test_case,
            variant=variant
        )
        
        # 显示执行结果
        print(f"\n✅ Pipeline 执行完成!")
        print(f"   总执行时间: {result.total_execution_time:.2f} 秒")
        
        if result.total_token_usage:
            print(f"   Token 使用量:")
            print(f"      - 输入: {result.total_token_usage.get('input_tokens', 0)}")
            print(f"      - 输出: {result.total_token_usage.get('output_tokens', 0)}")
            print(f"      - 总计: {result.total_token_usage.get('total_tokens', 0)}")
            
        # 显示每个步骤的结果
        print(f"\n📊 步骤执行结果:")
        for step_result in result.step_results:
            status = "✓" if not step_result.error else "✗"
            print(f"   {status} {step_result.step_id}")
            print(f"      输出键: {step_result.output_key}")
            
            # 显示输出值（截断长文本）
            output_str = str(step_result.output_value)
            if len(output_str) > 100:
                output_str = output_str[:100] + "..."
            print(f"      输出值: {output_str}")
            print(f"      执行时间: {step_result.execution_time:.2f} 秒")
            
            if step_result.error:
                print(f"      ❌ 错误: {step_result.error}")
                
        # 显示最终输出
        print(f"\n🎯 最终输出:")
        for key, value in result.final_outputs.items():
            value_str = str(value)
            if len(value_str) > 200:
                value_str = value_str[:200] + "..."
            print(f"   {key}: {value_str}")
            
        return result
        
    except Exception as e:
        print(f"❌ 执行 Pipeline 时出错: {e}")
        import traceback
        traceback.print_exc()
        return None


def demo_compare_variants(config, test_case: Dict[str, Any]):
    """演示：对比不同变体"""
    print_section("5. 对比不同变体")
    
    # 获取所有变体（包括 baseline）
    variants = ["baseline"]
    if config.variants:
        variants.extend(config.variants.keys())
        
    print(f"🔀 对比 {len(variants)} 个变体: {', '.join(variants)}")
    
    results = {}
    
    for variant in variants:
        print(f"\n--- 执行变体: {variant} ---")
        
        try:
            runner = PipelineRunner(config)
            result = runner.execute_sample(
                sample=test_case,
                variant=variant
            )
            
            results[variant] = result
            
            print(f"✅ {variant} 执行完成")
            print(f"   执行时间: {result.total_execution_time:.2f} 秒")
            print(f"   Token 总计: {result.total_token_usage.get('total_tokens', 0)}")
            
        except Exception as e:
            print(f"❌ {variant} 执行失败: {e}")
            
    # 对比结果
    if len(results) > 1:
        print(f"\n📊 变体对比:")
        print(f"{'变体':<20} {'执行时间':<15} {'Token 使用':<15}")
        print("-" * 50)
        
        for variant, result in results.items():
            exec_time = f"{result.total_execution_time:.2f}s"
            tokens = result.total_token_usage.get('total_tokens', 0)
            print(f"{variant:<20} {exec_time:<15} {tokens:<15}")
            
    return results


def demo_save_baseline(config, result: PipelineResult):
    """演示：保存基线"""
    print_section("6. 保存基线")
    
    try:
        baseline_name = "demo_baseline"
        
        print(f"💾 保存基线: {baseline_name}")
        print(f"   Pipeline: {config.id}")
        print(f"   变体: {result.variant}")
        
        # 计算性能指标
        performance_metrics = {
            "avg_execution_time": result.total_execution_time,
            "total_tokens": result.total_token_usage.get('total_tokens', 0),
            "success_rate": 1.0 if not result.error else 0.0
        }
        
        # 保存基线
        # 注意：save_pipeline_baseline 需要 evaluation_results，这里我们简化处理
        # 在实际使用中，应该先运行评估再保存基线
        save_pipeline_baseline(
            pipeline_id=config.id,
            baseline_name=baseline_name,
            description=f"演示脚本创建的基线 (变体: {result.variant})",
            performance_metrics=performance_metrics,
            evaluation_results=None  # 简化处理，实际应该包含评估结果
        )
        
        print(f"✅ 基线保存成功!")
        print(f"   基线名称: {baseline_name}")
        print(f"   保存位置: data/baselines/pipelines/{config.id}/{baseline_name}.json")
        print(f"   性能指标: {performance_metrics}")
        
    except Exception as e:
        print(f"❌ 保存基线时出错: {e}")


def demo_load_baseline(pipeline_id: str, baseline_name: str = "demo_baseline"):
    """演示：加载基线"""
    print_section("7. 加载基线")
    
    try:
        print(f"📂 加载基线: {baseline_name}")
        print(f"   Pipeline: {pipeline_id}")
        
        # 加载基线
        baseline = load_pipeline_baseline(pipeline_id, baseline_name)
        
        if baseline:
            print(f"✅ 基线加载成功!")
            print(f"   基线名称: {baseline.baseline_name}")
            print(f"   描述: {baseline.description}")
            print(f"   创建时间: {baseline.created_at}")
            print(f"   评估结果数量: {len(baseline.evaluation_results)}")
            print(f"   性能指标: {baseline.performance_metrics}")
            
            return baseline
        else:
            print(f"⚠️  未找到基线: {baseline_name}")
            return None
            
    except Exception as e:
        print(f"❌ 加载基线时出错: {e}")
        return None


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  🚀 Pipeline 演示脚本")
    print("=" * 60)
    
    # 1. 列出可用的 Pipeline
    demo_list_pipelines()
    
    # 2. 加载 Pipeline 配置
    pipeline_id = "document_summary"
    config = demo_load_pipeline(pipeline_id)
    
    if not config:
        print("\n❌ 无法加载 Pipeline 配置，演示终止")
        return
        
    # 3. 加载测试集
    test_cases = demo_load_testset(pipeline_id)
    
    if not test_cases:
        print("\n⚠️  未找到测试用例，使用示例数据")
        # 创建示例测试用例
        test_cases = [{
            "id": "demo_001",
            "raw_text": "这是一个演示文档。它包含一些示例文本，用于测试 Pipeline 的功能。",
            "tags": ["demo"]
        }]
        
    # 使用第一个测试用例
    test_case = test_cases[0]
    
    # 4. 执行 Pipeline
    result = demo_run_pipeline(config, test_case, variant="baseline")
    
    if not result:
        print("\n❌ Pipeline 执行失败，演示终止")
        return
        
    # 5. 对比不同变体（如果有）
    if config.variants:
        demo_compare_variants(config, test_case)
    else:
        print("\n💡 提示：此 Pipeline 没有配置变体，跳过变体对比")
        
    # 6. 保存基线
    demo_save_baseline(config, result)
    
    # 7. 加载基线
    demo_load_baseline(pipeline_id, "demo_baseline")
    
    # 完成
    print_section("演示完成")
    print("✅ 所有演示步骤已完成!")
    print("\n💡 下一步:")
    print("   1. 查看 pipelines/ 目录下的配置文件")
    print("   2. 创建自己的 Pipeline 配置")
    print("   3. 使用 CLI 运行 Pipeline:")
    print("      python -m src eval --pipeline <pipeline_id> --variants baseline --judge")
    print("   4. 查看文档: docs/reference/pipeline-guide.md")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  演示被用户中断")
    except Exception as e:
        print(f"\n\n❌ 演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
