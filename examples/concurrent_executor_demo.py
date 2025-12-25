#!/usr/bin/env python
"""
ConcurrentExecutor 使用示例

演示如何使用 ConcurrentExecutor 进行并发任务执行。
"""

import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.concurrent_executor import (
    ConcurrentExecutor,
    Task,
    ExecutionProgress
)


def process_data(data_id: int, duration: float = 0.5) -> dict:
    """模拟数据处理任务"""
    print(f"  开始处理数据 {data_id}...")
    time.sleep(duration)
    result = {
        "id": data_id,
        "processed": True,
        "value": data_id * 10
    }
    print(f"  完成处理数据 {data_id}")
    return result


def aggregate_results(results: list) -> dict:
    """聚合多个结果"""
    print("  聚合结果...")
    time.sleep(0.2)
    return {
        "total": len(results),
        "sum": sum(r["value"] for r in results),
        "avg": sum(r["value"] for r in results) / len(results)
    }


def progress_callback(progress: ExecutionProgress):
    """进度回调函数"""
    print(f"进度: {progress.completed}/{progress.total} 完成, "
          f"{progress.failed} 失败, "
          f"{progress.running} 运行中, "
          f"用时 {progress.elapsed_time:.2f}s")


def demo_simple_concurrent():
    """示例1: 简单并发执行"""
    print("\n=== 示例1: 简单并发执行 ===")
    
    executor = ConcurrentExecutor(max_workers=3, strategy="thread")
    
    # 创建5个任务
    tasks = [
        Task(
            id=f"task_{i}",
            func=process_data,
            args=(i, 0.5),
            metadata={"type": "data_processing"}
        )
        for i in range(5)
    ]
    
    print(f"开始执行 {len(tasks)} 个任务（最大并发数: 3）...")
    start_time = time.time()
    
    results = executor.execute_concurrent(tasks, progress_callback=progress_callback)
    
    elapsed = time.time() - start_time
    print(f"\n执行完成，用时 {elapsed:.2f}s")
    print(f"成功: {sum(1 for r in results if r.success)}")
    print(f"失败: {sum(1 for r in results if not r.success)}")


def demo_with_dependencies():
    """示例2: 带依赖关系的并发执行"""
    print("\n=== 示例2: 带依赖关系的并发执行 ===")
    
    executor = ConcurrentExecutor(max_workers=4, strategy="thread")
    
    # 创建一个依赖图:
    # task1, task2, task3 可以并发执行
    # task4 依赖 task1 和 task2
    # task5 依赖 task3
    # task6 依赖 task4 和 task5
    
    # 用于存储中间结果
    intermediate_results = {}
    
    def store_result(task_id: str, data_id: int):
        result = process_data(data_id, 0.3)
        intermediate_results[task_id] = result
        return result
    
    def combine_results(task_id: str, dep_ids: list):
        print(f"  组合结果 {dep_ids} -> {task_id}")
        time.sleep(0.2)
        results = [intermediate_results[dep_id] for dep_id in dep_ids]
        combined = {
            "id": task_id,
            "sources": dep_ids,
            "total_value": sum(r["value"] for r in results)
        }
        intermediate_results[task_id] = combined
        return combined
    
    tasks = [
        Task(id="task1", func=store_result, args=("task1", 1), dependencies=[]),
        Task(id="task2", func=store_result, args=("task2", 2), dependencies=[]),
        Task(id="task3", func=store_result, args=("task3", 3), dependencies=[]),
        Task(id="task4", func=combine_results, args=("task4", ["task1", "task2"]), dependencies=["task1", "task2"]),
        Task(id="task5", func=combine_results, args=("task5", ["task3"]), dependencies=["task3"]),
        Task(id="task6", func=combine_results, args=("task6", ["task4", "task5"]), dependencies=["task4", "task5"]),
    ]
    
    print(f"开始执行 {len(tasks)} 个任务（带依赖关系）...")
    print("依赖关系:")
    print("  task1, task2, task3 (并发)")
    print("  task4 <- task1, task2")
    print("  task5 <- task3")
    print("  task6 <- task4, task5")
    
    start_time = time.time()
    
    results = executor.execute_with_dependencies(tasks, progress_callback=progress_callback)
    
    elapsed = time.time() - start_time
    print(f"\n执行完成，用时 {elapsed:.2f}s")
    print(f"成功: {sum(1 for r in results if r.success)}")
    
    # 显示最终结果
    final_result = results[-1].result
    print(f"\n最终结果: {final_result}")


def demo_error_handling():
    """示例3: 错误处理"""
    print("\n=== 示例3: 错误处理 ===")
    
    executor = ConcurrentExecutor(max_workers=2, strategy="thread")
    
    def failing_task(task_id: str):
        print(f"  任务 {task_id} 失败")
        raise ValueError(f"任务 {task_id} 故意失败")
    
    def success_task(task_id: str):
        print(f"  任务 {task_id} 成功")
        time.sleep(0.2)
        return f"结果 {task_id}"
    
    tasks = [
        Task(id="task1", func=success_task, args=("task1",), required=True),
        Task(id="task2", func=failing_task, args=("task2",), required=True),
        Task(id="task3", func=success_task, args=("task3",), dependencies=["task1"], required=True),
        Task(id="task4", func=success_task, args=("task4",), dependencies=["task2"], required=True),
    ]
    
    print("执行任务（task2 会失败，task4 依赖 task2）...")
    
    results = executor.execute_with_dependencies(tasks)
    
    print("\n结果:")
    for result in results:
        status = "✓" if result.success else "✗"
        print(f"  {status} {result.task_id}: {result.error if result.error else 'Success'}")


def demo_progress_tracking():
    """示例4: 进度跟踪"""
    print("\n=== 示例4: 进度跟踪 ===")
    
    executor = ConcurrentExecutor(max_workers=2, strategy="thread")
    
    progress_history = []
    
    def detailed_progress_callback(progress: ExecutionProgress):
        progress_history.append({
            "completed": progress.completed,
            "total": progress.total,
            "rate": progress.completion_rate,
            "elapsed": progress.elapsed_time,
            "estimated_remaining": progress.estimated_remaining_time
        })
        
        print(f"进度: {progress.completion_rate*100:.1f}% "
              f"({progress.completed}/{progress.total}), "
              f"已用时 {progress.elapsed_time:.2f}s, "
              f"预计剩余 {progress.estimated_remaining_time:.2f}s" 
              if progress.estimated_remaining_time else "")
    
    tasks = [
        Task(id=f"task_{i}", func=process_data, args=(i, 0.3))
        for i in range(8)
    ]
    
    print(f"执行 {len(tasks)} 个任务，跟踪进度...")
    
    results = executor.execute_concurrent(tasks, progress_callback=detailed_progress_callback)
    
    print(f"\n总共收到 {len(progress_history)} 次进度更新")


if __name__ == "__main__":
    print("ConcurrentExecutor 使用示例")
    print("=" * 50)
    
    demo_simple_concurrent()
    demo_with_dependencies()
    demo_error_handling()
    demo_progress_tracking()
    
    print("\n" + "=" * 50)
    print("所有示例执行完成！")
