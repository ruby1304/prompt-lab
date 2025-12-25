#!/usr/bin/env python
"""
Pipeline 测试集加载器演示

演示如何使用更新后的测试集加载器处理 Pipeline 级别的测试集。
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.testset_loader import (
    load_testset,
    TestsetLoader,
    validate_testset,
    filter_by_tags
)


def demo_basic_loading():
    """演示基本的测试集加载"""
    print("=" * 80)
    print("演示 1: 基本的测试集加载")
    print("=" * 80)
    
    testset_file = Path('examples/testsets/pipeline_multi_step_examples.jsonl')
    
    if not testset_file.exists():
        print(f"测试集文件不存在: {testset_file}")
        return
    
    # 加载测试集
    test_cases = load_testset(testset_file)
    print(f"\n✓ 成功加载 {len(test_cases)} 个测试用例")
    
    # 显示第一个测试用例的信息
    if test_cases:
        tc = test_cases[0]
        print(f"\n第一个测试用例:")
        print(f"  ID: {tc.id}")
        print(f"  Tags: {tc.tags}")
        print(f"  Has step inputs: {tc.has_step_inputs()}")
        print(f"  Has intermediate expectations: {tc.has_intermediate_expectations()}")
        print(f"  Has batch data: {tc.has_batch_data()}")


def demo_step_data_extraction():
    """演示步骤级数据提取"""
    print("\n" + "=" * 80)
    print("演示 2: 步骤级数据提取")
    print("=" * 80)
    
    testset_file = Path('examples/testsets/pipeline_multi_step_examples.jsonl')
    
    if not testset_file.exists():
        print(f"测试集文件不存在: {testset_file}")
        return
    
    test_cases = load_testset(testset_file)
    
    # 找到第一个有步骤输入的测试用例
    for tc in test_cases:
        if tc.has_step_inputs():
            print(f"\n测试用例: {tc.id}")
            print(f"涉及的步骤: {tc.get_all_step_ids()}")
            
            # 提取每个步骤的数据
            for step_id in tc.get_all_step_ids():
                step_data = TestsetLoader.extract_step_data(tc, step_id)
                
                print(f"\n  步骤 '{step_id}':")
                if 'inputs' in step_data:
                    print(f"    输入: {step_data['inputs']}")
                if 'expected' in step_data:
                    print(f"    预期输出: {step_data['expected']}")
            
            break  # 只演示第一个


def demo_batch_data_organization():
    """演示批量数据组织"""
    print("\n" + "=" * 80)
    print("演示 3: 批量数据组织")
    print("=" * 80)
    
    testset_file = Path('examples/testsets/pipeline_batch_aggregation_examples.jsonl')
    
    if not testset_file.exists():
        print(f"测试集文件不存在: {testset_file}")
        return
    
    test_cases = load_testset(testset_file)
    
    # 组织批量数据
    batch_info = TestsetLoader.organize_batch_data(test_cases)
    
    print(f"\n批量数据统计:")
    print(f"  批量测试用例数: {batch_info['total_test_cases']}")
    print(f"  总批量项数: {batch_info['total_batch_items']}")
    print(f"  平均批量大小: {batch_info['average_batch_size']:.2f}")
    
    # 显示第一个批量测试用例
    if batch_info['test_cases']:
        tc = batch_info['test_cases'][0]
        print(f"\n第一个批量测试用例: {tc.id}")
        print(f"  批量大小: {tc.get_batch_size()}")
        print(f"  有预期聚合结果: {tc.has_expected_aggregation()}")
        if tc.has_expected_aggregation():
            print(f"  预期聚合结果: {tc.expected_aggregation}")


def demo_pipeline_structure_analysis():
    """演示 Pipeline 结构分析"""
    print("\n" + "=" * 80)
    print("演示 4: Pipeline 结构分析")
    print("=" * 80)
    
    testset_file = Path('examples/testsets/pipeline_complex_scenarios.jsonl')
    
    if not testset_file.exists():
        print(f"测试集文件不存在: {testset_file}")
        return
    
    test_cases = load_testset(testset_file)
    
    # 分析 Pipeline 结构
    structure = TestsetLoader.get_pipeline_structure(test_cases)
    
    print(f"\nPipeline 结构分析:")
    print(f"  总步骤数: {structure['total_steps']}")
    print(f"  所有步骤 ID: {structure['all_step_ids'][:5]}...")  # 只显示前5个
    print(f"  有输入的步骤: {len(structure['steps_with_inputs'])}")
    print(f"  有预期的步骤: {len(structure['steps_with_expectations'])}")
    print(f"  包含批量处理: {structure['has_batch_processing']}")
    print(f"  包含中间步骤评估: {structure['has_intermediate_evaluation']}")


def demo_feature_grouping():
    """演示按特性分组"""
    print("\n" + "=" * 80)
    print("演示 5: 按 Pipeline 特性分组")
    print("=" * 80)
    
    testset_file = Path('examples/testsets/pipeline_complex_scenarios.jsonl')
    
    if not testset_file.exists():
        print(f"测试集文件不存在: {testset_file}")
        return
    
    test_cases = load_testset(testset_file)
    
    # 按特性分组
    groups = TestsetLoader.group_by_pipeline_features(test_cases)
    
    print(f"\n测试用例分布:")
    print(f"  简单测试: {len(groups['simple'])}")
    print(f"  多步骤测试: {len(groups['multi_step'])}")
    print(f"  批量处理测试: {len(groups['batch_processing'])}")
    print(f"  中间步骤评估测试: {len(groups['intermediate_evaluation'])}")
    print(f"  复杂测试: {len(groups['complex'])}")
    
    # 显示复杂测试用例的详细信息
    if groups['complex']:
        print(f"\n复杂测试用例示例:")
        for tc in groups['complex'][:2]:  # 只显示前2个
            print(f"\n  {tc.id}:")
            print(f"    步骤数: {len(tc.get_all_step_ids())}")
            print(f"    批量大小: {tc.get_batch_size()}")
            print(f"    中间步骤预期数: {len(tc.intermediate_expectations)}")


def demo_evaluation_config():
    """演示评估配置"""
    print("\n" + "=" * 80)
    print("演示 6: 评估配置")
    print("=" * 80)
    
    testset_file = Path('examples/testsets/pipeline_intermediate_evaluation_examples.jsonl')
    
    if not testset_file.exists():
        print(f"测试集文件不存在: {testset_file}")
        return
    
    test_cases = load_testset(testset_file)
    
    # 找到有评估配置的测试用例
    for tc in test_cases:
        if tc.evaluation_config:
            print(f"\n测试用例: {tc.id}")
            print(f"  评估配置:")
            print(f"    评估中间步骤: {tc.should_evaluate_intermediate()}")
            print(f"    评估最终输出: {tc.should_evaluate_final()}")
            print(f"    评估聚合结果: {tc.should_evaluate_aggregation()}")
            print(f"    严格模式: {tc.is_strict_mode()}")
            print(f"    容差: {tc.get_tolerance()}")
            
            ignore_fields = tc.get_ignore_fields()
            if ignore_fields:
                print(f"    忽略字段: {ignore_fields}")
            
            break  # 只演示第一个


def demo_filtering():
    """演示过滤功能"""
    print("\n" + "=" * 80)
    print("演示 7: 过滤功能")
    print("=" * 80)
    
    testset_file = Path('examples/testsets/pipeline_multi_step_examples.jsonl')
    
    if not testset_file.exists():
        print(f"测试集文件不存在: {testset_file}")
        return
    
    test_cases = load_testset(testset_file)
    
    print(f"\n总测试用例数: {len(test_cases)}")
    
    # 按标签过滤
    multi_step_cases = filter_by_tags(test_cases, include_tags=['multi-step'])
    print(f"多步骤测试用例: {len(multi_step_cases)}")
    
    # 获取特定类型的测试用例
    step_input_cases = TestsetLoader.get_step_input_test_cases(test_cases)
    print(f"有步骤输入的测试用例: {len(step_input_cases)}")
    
    intermediate_cases = TestsetLoader.get_intermediate_evaluation_test_cases(test_cases)
    print(f"需要中间步骤评估的测试用例: {len(intermediate_cases)}")
    
    batch_cases = TestsetLoader.get_batch_test_cases(test_cases)
    print(f"批量处理测试用例: {len(batch_cases)}")


def demo_validation():
    """演示验证功能"""
    print("\n" + "=" * 80)
    print("演示 8: 验证功能")
    print("=" * 80)
    
    testset_file = Path('examples/testsets/pipeline_multi_step_examples.jsonl')
    
    if not testset_file.exists():
        print(f"测试集文件不存在: {testset_file}")
        return
    
    test_cases = load_testset(testset_file)
    
    # 验证测试集
    errors = validate_testset(test_cases)
    
    if errors:
        print(f"\n✗ 发现 {len(errors)} 个验证错误:")
        for error in errors:
            print(f"  - {error}")
    else:
        print(f"\n✓ 测试集验证通过，所有 {len(test_cases)} 个测试用例都有效")


def main():
    """运行所有演示"""
    print("\n" + "=" * 80)
    print("Pipeline 测试集加载器功能演示")
    print("=" * 80)
    
    demo_basic_loading()
    demo_step_data_extraction()
    demo_batch_data_organization()
    demo_pipeline_structure_analysis()
    demo_feature_grouping()
    demo_evaluation_config()
    demo_filtering()
    demo_validation()
    
    print("\n" + "=" * 80)
    print("演示完成!")
    print("=" * 80)


if __name__ == '__main__':
    main()
