#!/usr/bin/env python3
"""
进度跟踪演示

演示如何使用进度跟踪功能：
1. 实时进度更新
2. 进度查询接口
3. 与 PipelineProgressTracker 集成
"""

import time
import threading
from pathlib import Path
import sys

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from concurrent_executor import ConcurrentExecutor, Task, ExecutionProgress
from progress_tracker import PipelineProgressTracker, ProgressTracker, ProgressStats


def simulate_task(task_id: str, duration: float) -> str:
    """模拟一个耗时任务"""
    time.sleep(duration)
    return f"Task {task_id} completed"


def demo_concurrent_executor_progress():
    """演示并发执行器的进度跟踪"""
    print("=" * 60)
    print("演示 1: ConcurrentExecutor 进度跟踪")
    print("=" * 60)
    
    # 创建并发执行器
    executor = ConcurrentExecutor(max_workers=3, strategy="thread")
    
    # 创建任务列表
    tasks = [
        Task(id=f"task_{i}", func=simulate_task, args=(f"task_{i}", 0.5))
        for i in range(10)
    ]
    
    # 定义进度回调函数
    def progress_callback(progress: ExecutionProgress):
        """打印进度信息"""
        print(f"\r进度: {progress.completed}/{progress.total} "
              f"({progress.completion_rate*100:.1f}%) "
              f"运行中: {progress.running}, 待处理: {progress.pending}, "
              f"失败: {progress.failed}, "
              f"已用时: {progress.elapsed_time:.1f}秒", end="")
        
        if progress.estimated_remaining_time:
            print(f", 预计剩余: {progress.estimated_remaining_time:.1f}秒", end="")
    
    print("\n开始并发执行 10 个任务（最大并发数: 3）...")
    
    # 执行任务
    results = executor.execute_concurrent(
        tasks=tasks,
        progress_callback=progress_callback
    )
    
    print("\n\n执行完成！")
    print(f"成功: {len([r for r in results if r.success])}/{len(results)}")
    print(f"失败: {len([r for r in results if not r.success])}/{len(results)}")
    
    # 查询最终进度
    final_progress = executor.get_progress()
    print(f"\n最终进度统计:")
    print(f"  总任务数: {final_progress.total}")
    print(f"  已完成: {final_progress.completed}")
    print(f"  失败: {final_progress.failed}")
    print(f"  总耗时: {final_progress.elapsed_time:.2f}秒")
    
    # 获取字典格式的进度信息（用于API）
    progress_dict = executor.get_progress_dict()
    print(f"\n进度字典（用于API）:")
    for key, value in progress_dict.items():
        print(f"  {key}: {value}")


def demo_progress_tracker_query():
    """演示进度跟踪器的查询接口"""
    print("\n\n" + "=" * 60)
    print("演示 2: ProgressTracker 查询接口")
    print("=" * 60)
    
    # 创建进度跟踪器
    tracker = ProgressTracker(
        task_name="数据处理",
        total_items=20,
        show_spinner=True,
        show_eta=True
    )
    
    # 在后台线程中查询进度
    stop_query = threading.Event()
    
    def query_progress():
        """定期查询进度"""
        while not stop_query.is_set():
            stats = tracker.get_stats()
            stats_dict = tracker.get_stats_dict()
            
            # 可以将这些信息发送到API、数据库等
            # print(f"\n[查询] 进度: {stats.progress_percentage:.1f}%, "
            #       f"当前项: {stats.current_item}")
            
            time.sleep(0.5)
    
    # 启动查询线程
    query_thread = threading.Thread(target=query_progress, daemon=True)
    query_thread.start()
    
    # 开始处理
    tracker.start()
    
    print("\n模拟处理 20 个项目...")
    for i in range(20):
        # 模拟处理
        time.sleep(0.2)
        
        # 更新进度
        tracker.update(
            current_item=f"项目_{i+1}",
            current_step=f"步骤 {(i % 3) + 1}/3",
            failed=(i % 7 == 0)  # 每7个项目失败一次
        )
    
    # 完成
    tracker.finish("处理完成！")
    
    # 停止查询线程
    stop_query.set()
    query_thread.join(timeout=1)
    
    # 获取最终统计
    final_stats = tracker.get_stats()
    print(f"\n最终统计:")
    print(f"  成功: {final_stats.success_items}/{final_stats.total_items}")
    print(f"  失败: {final_stats.failed_items}/{final_stats.total_items}")
    print(f"  成功率: {final_stats.success_items/final_stats.total_items*100:.1f}%")


def demo_pipeline_progress_tracker():
    """演示 Pipeline 进度跟踪器"""
    print("\n\n" + "=" * 60)
    print("演示 3: PipelineProgressTracker")
    print("=" * 60)
    
    # 创建 Pipeline 进度跟踪器
    tracker = PipelineProgressTracker(
        pipeline_name="示例Pipeline",
        total_samples=5,
        total_steps=3,
        variant="baseline"
    )
    
    # 添加自定义回调
    def custom_callback(stats: ProgressStats):
        """自定义进度回调"""
        # 可以在这里发送进度到外部系统
        pass
    
    tracker.add_callback(custom_callback)
    
    # 开始执行
    tracker.start()
    
    print("\n模拟执行 Pipeline（5个样本，每个3个步骤）...")
    
    for sample_idx in range(5):
        sample_id = f"sample_{sample_idx + 1}"
        
        # 执行每个步骤
        for step_idx in range(3):
            step_name = f"步骤_{step_idx + 1}"
            
            # 更新进度
            tracker.update_sample(
                sample_index=sample_idx,
                sample_id=sample_id,
                step_index=step_idx,
                step_name=step_name,
                failed=False
            )
            
            # 模拟步骤执行
            time.sleep(0.3)
        
        # 完成样本
        tracker.complete_sample(
            sample_index=sample_idx,
            sample_id=sample_id,
            failed=(sample_idx == 2)  # 第3个样本失败
        )
    
    # 完成
    tracker.finish("Pipeline 执行完成！")
    
    # 获取 Pipeline 专用统计
    pipeline_stats = tracker.get_pipeline_stats_dict()
    print(f"\nPipeline 统计信息:")
    for key, value in pipeline_stats.items():
        print(f"  {key}: {value}")


def demo_concurrent_with_dependencies():
    """演示带依赖关系的并发执行进度跟踪"""
    print("\n\n" + "=" * 60)
    print("演示 4: 带依赖关系的并发执行进度跟踪")
    print("=" * 60)
    
    # 创建并发执行器
    executor = ConcurrentExecutor(max_workers=3, strategy="thread")
    
    # 创建有依赖关系的任务
    tasks = [
        Task(id="task_1", func=simulate_task, args=("task_1", 0.5), dependencies=[]),
        Task(id="task_2", func=simulate_task, args=("task_2", 0.5), dependencies=[]),
        Task(id="task_3", func=simulate_task, args=("task_3", 0.5), dependencies=["task_1"]),
        Task(id="task_4", func=simulate_task, args=("task_4", 0.5), dependencies=["task_1", "task_2"]),
        Task(id="task_5", func=simulate_task, args=("task_5", 0.5), dependencies=["task_3", "task_4"]),
    ]
    
    # 构建依赖图
    dependency_graph = {task.id: task.dependencies for task in tasks}
    
    print("\n任务依赖关系:")
    for task_id, deps in dependency_graph.items():
        if deps:
            print(f"  {task_id} 依赖于: {', '.join(deps)}")
        else:
            print(f"  {task_id} 无依赖")
    
    # 定义进度回调
    def progress_callback(progress: ExecutionProgress):
        """打印进度信息"""
        print(f"\r进度: {progress.completed}/{progress.total} "
              f"({progress.completion_rate*100:.1f}%) "
              f"运行中: {progress.running}, 待处理: {progress.pending}", end="")
    
    print("\n\n开始执行...")
    
    # 执行任务
    results = executor.execute_with_dependencies(
        tasks=tasks,
        dependency_graph=dependency_graph,
        progress_callback=progress_callback
    )
    
    print("\n\n执行完成！")
    print(f"成功: {len([r for r in results if r.success])}/{len(results)}")
    
    # 显示执行顺序
    print("\n执行顺序:")
    for i, result in enumerate(results):
        print(f"  {i+1}. {result.task_id} - "
              f"{'成功' if result.success else '失败'} "
              f"({result.execution_time:.2f}秒)")


def main():
    """主函数"""
    print("进度跟踪功能演示")
    print("=" * 60)
    
    # 演示 1: 并发执行器进度跟踪
    demo_concurrent_executor_progress()
    
    # 演示 2: 进度跟踪器查询接口
    demo_progress_tracker_query()
    
    # 演示 3: Pipeline 进度跟踪器
    demo_pipeline_progress_tracker()
    
    # 演示 4: 带依赖关系的并发执行
    demo_concurrent_with_dependencies()
    
    print("\n\n" + "=" * 60)
    print("所有演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
