#!/usr/bin/env python
"""
DependencyAnalyzer 使用示例

演示如何使用 DependencyAnalyzer 分析 Pipeline 步骤的依赖关系，
识别可并发执行的步骤组，并进行拓扑排序。
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.dependency_analyzer import DependencyAnalyzer
from src.models import StepConfig


def example_linear_pipeline():
    """示例1: 线性依赖的 Pipeline"""
    print("=" * 60)
    print("示例1: 线性依赖的 Pipeline")
    print("=" * 60)
    
    steps = [
        StepConfig(
            id="extract",
            type="agent_flow",
            agent="extractor",
            flow="extract_v1",
            output_key="entities"
        ),
        StepConfig(
            id="classify",
            type="agent_flow",
            agent="classifier",
            flow="classify_v1",
            input_mapping={"data": "entities"},
            output_key="classified"
        ),
        StepConfig(
            id="summarize",
            type="agent_flow",
            agent="summarizer",
            flow="summarize_v1",
            input_mapping={"data": "classified"},
            output_key="summary"
        )
    ]
    
    analyzer = DependencyAnalyzer()
    graph = analyzer.analyze_dependencies(steps)
    
    print(f"\n步骤数量: {len(graph.nodes)}")
    print(f"依赖关系:")
    for step_id, deps in graph.edges.items():
        if deps:
            print(f"  {step_id} 依赖: {', '.join(deps)}")
        else:
            print(f"  {step_id} 无依赖")
    
    sorted_steps = analyzer.topological_sort(graph)
    print(f"\n拓扑排序结果: {' -> '.join(sorted_steps)}")
    
    groups = analyzer.find_concurrent_groups(graph)
    print(f"\n并发组 (共 {len(groups)} 组):")
    for i, group in enumerate(groups, 1):
        print(f"  组 {i}: {', '.join(group)}")


def example_diamond_pipeline():
    """示例2: 菱形依赖的 Pipeline (可并发)"""
    print("\n" + "=" * 60)
    print("示例2: 菱形依赖的 Pipeline (可并发)")
    print("=" * 60)
    
    steps = [
        StepConfig(
            id="preprocess",
            type="agent_flow",
            agent="preprocessor",
            flow="preprocess_v1",
            output_key="preprocessed"
        ),
        StepConfig(
            id="analyze_sentiment",
            type="agent_flow",
            agent="sentiment_analyzer",
            flow="analyze_v1",
            input_mapping={"text": "preprocessed"},
            output_key="sentiment"
        ),
        StepConfig(
            id="extract_keywords",
            type="agent_flow",
            agent="keyword_extractor",
            flow="extract_v1",
            input_mapping={"text": "preprocessed"},
            output_key="keywords"
        ),
        StepConfig(
            id="generate_report",
            type="agent_flow",
            agent="reporter",
            flow="report_v1",
            depends_on=["analyze_sentiment", "extract_keywords"],
            output_key="report"
        )
    ]
    
    analyzer = DependencyAnalyzer()
    graph = analyzer.analyze_dependencies(steps)
    
    print(f"\n步骤数量: {len(graph.nodes)}")
    print(f"依赖关系:")
    for step_id, deps in graph.edges.items():
        if deps:
            print(f"  {step_id} 依赖: {', '.join(deps)}")
        else:
            print(f"  {step_id} 无依赖")
    
    sorted_steps = analyzer.topological_sort(graph)
    print(f"\n拓扑排序结果: {' -> '.join(sorted_steps)}")
    
    groups = analyzer.find_concurrent_groups(graph)
    print(f"\n并发组 (共 {len(groups)} 组):")
    for i, group in enumerate(groups, 1):
        print(f"  组 {i}: {', '.join(group)}")
        if len(group) > 1:
            print(f"    ✓ 可并发执行!")


def example_explicit_concurrent_groups():
    """示例3: 使用显式并发组配置"""
    print("\n" + "=" * 60)
    print("示例3: 使用显式并发组配置")
    print("=" * 60)
    
    steps = [
        StepConfig(
            id="task1",
            type="agent_flow",
            agent="worker",
            flow="process_v1",
            concurrent_group="parallel_tasks",
            output_key="result1"
        ),
        StepConfig(
            id="task2",
            type="agent_flow",
            agent="worker",
            flow="process_v1",
            concurrent_group="parallel_tasks",
            output_key="result2"
        ),
        StepConfig(
            id="task3",
            type="agent_flow",
            agent="worker",
            flow="process_v1",
            concurrent_group="parallel_tasks",
            output_key="result3"
        ),
        StepConfig(
            id="aggregate",
            type="code_node",
            language="python",
            code="def aggregate(results): return sum(results)",
            depends_on=["task1", "task2", "task3"],
            output_key="total"
        )
    ]
    
    analyzer = DependencyAnalyzer()
    graph = analyzer.analyze_dependencies(steps)
    
    print(f"\n步骤数量: {len(graph.nodes)}")
    print(f"并发组配置:")
    for group_name, step_ids in graph.concurrent_groups.items():
        print(f"  {group_name}: {', '.join(step_ids)}")
    
    print(f"\n依赖关系:")
    for step_id, deps in graph.edges.items():
        if deps:
            print(f"  {step_id} 依赖: {', '.join(deps)}")
        else:
            print(f"  {step_id} 无依赖")
    
    groups = analyzer.find_concurrent_groups(graph)
    print(f"\n实际并发组 (共 {len(groups)} 组):")
    for i, group in enumerate(groups, 1):
        print(f"  组 {i}: {', '.join(group)}")


def example_complex_pipeline():
    """示例4: 复杂的多阶段 Pipeline"""
    print("\n" + "=" * 60)
    print("示例4: 复杂的多阶段 Pipeline")
    print("=" * 60)
    
    steps = [
        # 阶段1: 数据获取
        StepConfig(
            id="fetch_data",
            type="agent_flow",
            agent="fetcher",
            flow="fetch_v1",
            output_key="raw_data"
        ),
        
        # 阶段2: 并行处理
        StepConfig(
            id="process_text",
            type="agent_flow",
            agent="text_processor",
            flow="process_v1",
            input_mapping={"data": "raw_data"},
            concurrent_group="processing",
            output_key="processed_text"
        ),
        StepConfig(
            id="process_metadata",
            type="code_node",
            language="python",
            code="def process(data): return data['metadata']",
            input_mapping={"data": "raw_data"},
            concurrent_group="processing",
            output_key="processed_metadata"
        ),
        
        # 阶段3: 分析
        StepConfig(
            id="analyze",
            type="agent_flow",
            agent="analyzer",
            flow="analyze_v1",
            depends_on=["process_text", "process_metadata"],
            output_key="analysis"
        ),
        
        # 阶段4: 并行生成报告
        StepConfig(
            id="generate_summary",
            type="agent_flow",
            agent="summarizer",
            flow="summarize_v1",
            input_mapping={"data": "analysis"},
            concurrent_group="reporting",
            output_key="summary"
        ),
        StepConfig(
            id="generate_visualization",
            type="code_node",
            language="javascript",
            code="function visualize(data) { return createChart(data); }",
            input_mapping={"data": "analysis"},
            concurrent_group="reporting",
            output_key="chart"
        ),
        
        # 阶段5: 最终输出
        StepConfig(
            id="finalize",
            type="agent_flow",
            agent="finalizer",
            flow="finalize_v1",
            depends_on=["generate_summary", "generate_visualization"],
            output_key="final_report"
        )
    ]
    
    analyzer = DependencyAnalyzer()
    graph = analyzer.analyze_dependencies(steps)
    
    print(f"\n步骤数量: {len(graph.nodes)}")
    print(f"并发组配置:")
    for group_name, step_ids in graph.concurrent_groups.items():
        print(f"  {group_name}: {', '.join(step_ids)}")
    
    sorted_steps = analyzer.topological_sort(graph)
    print(f"\n拓扑排序结果:")
    print(f"  {' -> '.join(sorted_steps)}")
    
    groups = analyzer.find_concurrent_groups(graph)
    print(f"\n并发执行计划 (共 {len(groups)} 个阶段):")
    for i, group in enumerate(groups, 1):
        print(f"  阶段 {i}: {', '.join(group)}")
        if len(group) > 1:
            print(f"    ✓ 可并发执行 {len(group)} 个步骤!")


if __name__ == "__main__":
    example_linear_pipeline()
    example_diamond_pipeline()
    example_explicit_concurrent_groups()
    example_complex_pipeline()
    
    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)
