#!/usr/bin/env python
"""
并发错误处理演示

展示如何使用 ConcurrentExecutor 的错误处理功能：
- 错误隔离
- 错误收集
- 可选步骤处理
- 结果顺序保持
"""

import time
from src.concurrent_executor import (
    ConcurrentExecutor,
    Task,
    ExecutionProgress
)


def process_data(data_id: int) -> dict:
    """处理数据的任务"""
    time.sleep(0.1)  # 模拟处理时间
    return {
        "id": data_id,
        "processed": True,
        "result": data_id * 2
    }


def validate_data(data_id: int) -> bool:
    """验证数据的任务（可能失败）"""
    time.sleep(0.05)
    # 模拟某些数据验证失败
    if data_id % 3 == 0:
        raise ValueError(f"数据 {data_id} 验证失败")
    return True


def aggregate_results(results: list) -> dict:
    """聚合结果的任务"""
    time.sleep(0.1)
    return {
        "total": len(results),
        "sum": sum(r["result"] for r in results if isinstance(r, dict))
    }


def progress_callback(progress: ExecutionProgress):
    """进度回调函数"""
    print(f"进度: {progress.completed}/{progress.total} "
          f"(成功率: {progress.success_rate:.1%}, "
          f"失败: {progress.failed}, "
          f"跳过: {progress.skipped})")


def demo_error_isolation():
    """演示错误隔离"""
    print("\n=== 演示 1: 错误隔离 ===")
    print("即使某些任务失败，其他任务仍会继续执行\n")
    
    executor = ConcurrentExecutor(max_workers=4)
    
    # 创建一些任务，其中一些会失败
    tasks = [
        Task(id=f"validate_{i}", func=validate_data, args=(i,))
        for i in range(10)
    ]
    
    results = executor.execute_concurrent(tasks, progress_callback=progress_callback)
    
    # 显示结果
    print("\n结果:")
    for result in results:
        status = "✓ 成功" if result.success else f"✗ 失败: {result.error}"
        print(f"  {result.task_id}: {status}")
    
    # 显示错误汇总
    error_summary = executor.get_error_summary()
    print(f"\n错误汇总:")
    print(f"  总错误数: {error_summary.total_errors}")
    print(f"  失败任务: {', '.join(error_summary.failed_tasks)}")
    print(f"  错误类型: {error_summary.error_types}")


def demo_error_collection():
    """演示错误收集"""
    print("\n=== 演示 2: 错误收集 ===")
    print("系统会收集所有错误并提供详细的错误报告\n")
    
    executor = ConcurrentExecutor(max_workers=4)
    
    # 创建混合任务
    tasks = []
    for i in range(8):
        if i % 2 == 0:
            tasks.append(Task(
                id=f"process_{i}",
                func=process_data,
                args=(i,),
                required=True
            ))
        else:
            tasks.append(Task(
                id=f"validate_{i}",
                func=validate_data,
                args=(i,),
                required=False  # 可选任务
            ))
    
    results = executor.execute_concurrent(tasks, progress_callback=progress_callback)
    
    # 获取执行汇总
    summary = executor.get_execution_summary(results)
    
    print("\n执行汇总:")
    print(f"  总任务数: {summary.progress.total}")
    print(f"  成功: {len(summary.get_successful_results())}")
    print(f"  失败: {len(summary.get_failed_results())}")
    print(f"  跳过: {len(summary.get_skipped_results())}")
    print(f"  成功率: {summary.progress.success_rate:.1%}")
    print(f"  有关键错误: {summary.errors.has_critical_errors()}")
    
    # 显示错误详情
    if summary.errors.total_errors > 0:
        print(f"\n错误详情:")
        for error_type, count in summary.errors.error_types.items():
            print(f"  {error_type}: {count} 次")


def demo_optional_step_handling():
    """演示可选步骤处理"""
    print("\n=== 演示 3: 可选步骤处理 ===")
    print("可选任务失败不会阻止依赖任务，必需任务失败会阻止依赖任务\n")
    
    executor = ConcurrentExecutor(max_workers=4)
    
    # 创建依赖任务
    tasks = [
        # 第一组：可选任务失败
        Task(id="optional_validate", func=validate_data, args=(3,), required=False),
        Task(id="process_after_optional", func=process_data, args=(1,), 
             dependencies=["optional_validate"]),
        
        # 第二组：必需任务失败
        Task(id="required_validate", func=validate_data, args=(6,), required=True),
        Task(id="process_after_required", func=process_data, args=(2,), 
             dependencies=["required_validate"]),
    ]
    
    results = executor.execute_with_dependencies(tasks, progress_callback=progress_callback)
    
    print("\n结果:")
    for i, result in enumerate(results):
        task = tasks[i]
        if result.success:
            status = "✓ 成功"
        elif result.skipped:
            status = "⊘ 跳过（依赖失败）"
        else:
            status = f"✗ 失败: {result.error}"
        
        required_str = "必需" if task.required else "可选"
        print(f"  {result.task_id} ({required_str}): {status}")


def demo_result_order_preservation():
    """演示结果顺序保持"""
    print("\n=== 演示 4: 结果顺序保持 ===")
    print("无论任务何时完成，结果都按输入顺序返回\n")
    
    executor = ConcurrentExecutor(max_workers=4)
    
    # 创建不同执行时间的任务
    def slow_task(task_id: int, duration: float):
        time.sleep(duration)
        return f"Task {task_id} completed"
    
    tasks = [
        Task(id="task_0", func=slow_task, args=(0, 0.3)),  # 慢
        Task(id="task_1", func=slow_task, args=(1, 0.1)),  # 快
        Task(id="task_2", func=validate_data, args=(3,)),  # 失败
        Task(id="task_3", func=slow_task, args=(3, 0.2)),  # 中等
        Task(id="task_4", func=slow_task, args=(4, 0.05)), # 最快
    ]
    
    print("任务执行顺序（按完成时间）: task_4 -> task_1 -> task_3 -> task_0")
    print("但结果顺序应该是: task_0 -> task_1 -> task_2 -> task_3 -> task_4\n")
    
    results = executor.execute_concurrent(tasks, progress_callback=progress_callback)
    
    print("\n结果顺序:")
    for i, result in enumerate(results):
        status = "✓" if result.success else "✗"
        print(f"  位置 {i}: {result.task_id} {status}")


def demo_complex_error_scenario():
    """演示复杂错误场景"""
    print("\n=== 演示 5: 复杂错误场景 ===")
    print("展示级联失败和部分分支失败的处理\n")
    
    executor = ConcurrentExecutor(max_workers=4)
    
    # 创建复杂的依赖图
    # root -> branch1 (fails, required) -> merge
    #      -> branch2 (success) -> merge
    #      -> branch3 (fails, optional) -> merge
    tasks = [
        Task(id="root", func=process_data, args=(0,), dependencies=[]),
        
        Task(id="branch1", func=validate_data, args=(3,), 
             dependencies=["root"], required=True),
        Task(id="branch2", func=process_data, args=(2,), 
             dependencies=["root"]),
        Task(id="branch3", func=validate_data, args=(6,), 
             dependencies=["root"], required=False),
        
        Task(id="merge", func=aggregate_results, args=([],), 
             dependencies=["branch1", "branch2", "branch3"]),
    ]
    
    results = executor.execute_with_dependencies(tasks, progress_callback=progress_callback)
    
    print("\n执行结果:")
    for i, result in enumerate(results):
        task = tasks[i]
        if result.success:
            status = "✓ 成功"
        elif result.skipped:
            status = "⊘ 跳过"
        else:
            status = f"✗ 失败"
        
        required_str = "必需" if task.required else "可选"
        deps = f" (依赖: {', '.join(task.dependencies)})" if task.dependencies else ""
        print(f"  {result.task_id} ({required_str}){deps}: {status}")
    
    # 显示错误汇总
    error_summary = executor.get_error_summary()
    print(f"\n错误汇总:")
    print(f"  失败任务: {', '.join(error_summary.failed_tasks)}")
    print(f"  跳过任务: {', '.join(error_summary.skipped_tasks)}")
    print(f"  关键错误: {', '.join(error_summary.critical_errors)}")


def main():
    """运行所有演示"""
    print("=" * 60)
    print("并发错误处理演示")
    print("=" * 60)
    
    demo_error_isolation()
    demo_error_collection()
    demo_optional_step_handling()
    demo_result_order_preservation()
    demo_complex_error_scenario()
    
    print("\n" + "=" * 60)
    print("演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
