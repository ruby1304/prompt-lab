# tests/test_concurrent_executor_unit.py
"""
并发执行器单元测试 - Task 41

专注测试 ConcurrentExecutor 的核心功能：
- 任务队列管理
- 并发执行机制
- 最大并发数控制
- 结果收集功能

Requirements: 9.1, 9.2
"""

import pytest
import time
import threading
from typing import List
from src.concurrent_executor import (
    ConcurrentExecutor,
    Task,
    TaskResult,
    ExecutionProgress,
    ExecutionStrategy
)


# ============================================================================
# 测试辅助函数
# ============================================================================

def simple_task(x: int) -> int:
    """简单的计算任务"""
    return x * 2


def slow_task(duration: float, value: int) -> int:
    """慢速任务，用于测试并发"""
    time.sleep(duration)
    return value


def failing_task(msg: str = "Task failed") -> None:
    """会失败的任务"""
    raise ValueError(msg)


def task_with_side_effect(counter: List[int], value: int) -> int:
    """有副作用的任务，用于验证执行"""
    counter.append(value)
    return value


# ============================================================================
# 1. 任务队列测试
# ============================================================================

class TestTaskQueue:
    """测试任务队列管理功能"""
    
    def test_empty_task_queue(self):
        """测试空任务队列"""
        executor = ConcurrentExecutor(max_workers=4)
        results = executor.execute_concurrent([])
        
        assert results == []
        assert len(results) == 0
    
    def test_single_task_in_queue(self):
        """测试单个任务入队和执行"""
        executor = ConcurrentExecutor(max_workers=4)
        
        task = Task(id="single_task", func=simple_task, args=(5,))
        results = executor.execute_concurrent([task])
        
        assert len(results) == 1
        assert results[0].task_id == "single_task"
        assert results[0].success is True
        assert results[0].result == 10
    
    def test_multiple_tasks_queued(self):
        """测试多个任务入队"""
        executor = ConcurrentExecutor(max_workers=4)
        
        tasks = [
            Task(id=f"task_{i}", func=simple_task, args=(i,))
            for i in range(10)
        ]
        
        results = executor.execute_concurrent(tasks)
        
        # 验证所有任务都被执行
        assert len(results) == 10
        
        # 验证每个任务的结果
        for i, result in enumerate(results):
            assert result.task_id == f"task_{i}"
            assert result.success is True
            assert result.result == i * 2
    
    def test_task_queue_with_mixed_types(self):
        """测试队列中混合不同类型的任务"""
        executor = ConcurrentExecutor(max_workers=4)
        
        tasks = [
            Task(id="fast", func=simple_task, args=(1,)),
            Task(id="slow", func=slow_task, args=(0.1, 2)),
            Task(id="fail", func=failing_task, args=("Expected failure",)),
            Task(id="fast2", func=simple_task, args=(3,))
        ]
        
        results = executor.execute_concurrent(tasks)
        
        assert len(results) == 4
        assert results[0].success is True
        assert results[1].success is True
        assert results[2].success is False
        assert results[3].success is True
    
    def test_task_queue_preserves_order(self):
        """测试任务队列保持输入顺序"""
        executor = ConcurrentExecutor(max_workers=4)
        
        # 创建不同执行时间的任务，验证结果顺序不受执行时间影响
        tasks = [
            Task(id="task_0", func=slow_task, args=(0.2, 0)),
            Task(id="task_1", func=simple_task, args=(1,)),
            Task(id="task_2", func=slow_task, args=(0.1, 2)),
            Task(id="task_3", func=simple_task, args=(3,)),
            Task(id="task_4", func=slow_task, args=(0.15, 4))
        ]
        
        results = executor.execute_concurrent(tasks)
        
        # 验证结果顺序与输入顺序一致
        assert len(results) == 5
        for i in range(5):
            assert results[i].task_id == f"task_{i}"
    
    def test_large_task_queue(self):
        """测试大量任务入队"""
        executor = ConcurrentExecutor(max_workers=8)
        
        # 创建100个任务
        tasks = [
            Task(id=f"task_{i}", func=simple_task, args=(i,))
            for i in range(100)
        ]
        
        results = executor.execute_concurrent(tasks)
        
        assert len(results) == 100
        
        # 验证所有任务都成功执行
        assert all(r.success for r in results)
        
        # 验证结果正确性
        for i, result in enumerate(results):
            assert result.result == i * 2


# ============================================================================
# 2. 并发执行测试
# ============================================================================

class TestConcurrentExecution:
    """测试并发执行机制"""
    
    def test_concurrent_execution_faster_than_sequential(self):
        """测试并发执行比串行执行快"""
        executor = ConcurrentExecutor(max_workers=4)
        
        # 创建4个各需要0.2秒的任务
        tasks = [
            Task(id=f"task_{i}", func=slow_task, args=(0.2, i))
            for i in range(4)
        ]
        
        start_time = time.time()
        results = executor.execute_concurrent(tasks)
        elapsed_time = time.time() - start_time
        
        # 如果并发执行，应该在约0.2秒内完成
        # 如果串行执行，需要0.8秒
        assert len(results) == 4
        assert all(r.success for r in results)
        assert elapsed_time < 0.5  # 应该远小于串行的0.8秒
    
    def test_concurrent_execution_with_thread_strategy(self):
        """测试使用线程策略的并发执行"""
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        
        tasks = [
            Task(id=f"task_{i}", func=simple_task, args=(i,))
            for i in range(10)
        ]
        
        results = executor.execute_concurrent(tasks)
        
        assert len(results) == 10
        assert all(r.success for r in results)
        assert executor.strategy == ExecutionStrategy.THREAD
    
    def test_concurrent_execution_with_process_strategy(self):
        """测试使用进程策略的并发执行"""
        # Note: Process strategy requires picklable functions and data
        # Using simple functions without closures or complex objects
        executor = ConcurrentExecutor(max_workers=2, strategy="process")
        
        # Use simple tasks that can be pickled
        tasks = [
            Task(id=f"task_{i}", func=simple_task, args=(i,))
            for i in range(5)
        ]
        
        try:
            results = executor.execute_concurrent(tasks)
            
            assert len(results) == 5
            assert all(r.success for r in results)
            assert executor.strategy == ExecutionStrategy.PROCESS
        except (TypeError, AttributeError) as e:
            # Process strategy may fail with pickling issues on some systems
            # This is a known limitation of multiprocessing
            if "pickle" in str(e).lower():
                pytest.skip(f"Process strategy not supported on this system: {e}")
            else:
                raise
    
    def test_concurrent_execution_independence(self):
        """测试并发任务的独立性"""
        executor = ConcurrentExecutor(max_workers=4)
        
        # 使用共享列表验证任务确实并发执行
        execution_times = []
        lock = threading.Lock()
        
        def record_time_task(task_id: int) -> int:
            with lock:
                execution_times.append((task_id, time.time()))
            time.sleep(0.1)
            return task_id
        
        tasks = [
            Task(id=f"task_{i}", func=record_time_task, args=(i,))
            for i in range(4)
        ]
        
        start_time = time.time()
        results = executor.execute_concurrent(tasks)
        
        # 验证所有任务都执行了
        assert len(results) == 4
        assert all(r.success for r in results)
        
        # 验证任务是并发开始的（时间差应该很小）
        if len(execution_times) >= 2:
            time_diffs = [execution_times[i+1][1] - execution_times[i][1] 
                         for i in range(len(execution_times)-1)]
            # 并发执行时，任务开始时间应该非常接近
            assert all(diff < 0.2 for diff in time_diffs)
    
    def test_concurrent_execution_with_failures(self):
        """测试并发执行中的失败处理"""
        executor = ConcurrentExecutor(max_workers=4)
        
        tasks = [
            Task(id="success_1", func=simple_task, args=(1,)),
            Task(id="failure_1", func=failing_task, args=("Error 1",)),
            Task(id="success_2", func=simple_task, args=(2,)),
            Task(id="failure_2", func=failing_task, args=("Error 2",)),
            Task(id="success_3", func=simple_task, args=(3,))
        ]
        
        results = executor.execute_concurrent(tasks)
        
        # 验证所有任务都执行了（失败不影响其他任务）
        assert len(results) == 5
        
        # 验证成功和失败的任务
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True
        assert results[3].success is False
        assert results[4].success is True
    
    def test_concurrent_execution_with_dependencies(self):
        """测试带依赖关系的并发执行"""
        executor = ConcurrentExecutor(max_workers=4)
        
        # 创建一个简单的依赖图
        # task1 和 task2 可以并发
        # task3 依赖 task1 和 task2
        tasks = [
            Task(id="task1", func=slow_task, args=(0.1, 1), dependencies=[]),
            Task(id="task2", func=slow_task, args=(0.1, 2), dependencies=[]),
            Task(id="task3", func=simple_task, args=(3,), dependencies=["task1", "task2"])
        ]
        
        start_time = time.time()
        results = executor.execute_with_dependencies(tasks)
        elapsed_time = time.time() - start_time
        
        # task1 和 task2 应该并发执行（约0.1秒）
        # task3 等待后执行（几乎立即）
        # 总时间应该约0.1秒，而不是0.2秒
        assert len(results) == 3
        assert all(r.success for r in results)
        assert elapsed_time < 0.3  # 应该远小于串行的0.2秒


# ============================================================================
# 3. 最大并发数测试
# ============================================================================

class TestMaxConcurrency:
    """测试最大并发数控制"""
    
    def test_max_workers_limit_enforced(self):
        """测试最大并发数限制被强制执行"""
        executor = ConcurrentExecutor(max_workers=2)
        
        # 创建4个各需要0.2秒的任务
        tasks = [
            Task(id=f"task_{i}", func=slow_task, args=(0.2, i))
            for i in range(4)
        ]
        
        start_time = time.time()
        results = executor.execute_concurrent(tasks)
        elapsed_time = time.time() - start_time
        
        # 最多2个并发，4个任务需要2批
        # 应该需要约0.4秒（2批 × 0.2秒）
        assert len(results) == 4
        assert all(r.success for r in results)
        assert 0.35 < elapsed_time < 0.6  # 允许一些误差
    
    def test_max_workers_one(self):
        """测试最大并发数为1（串行执行）"""
        executor = ConcurrentExecutor(max_workers=1)
        
        tasks = [
            Task(id=f"task_{i}", func=slow_task, args=(0.1, i))
            for i in range(3)
        ]
        
        start_time = time.time()
        results = executor.execute_concurrent(tasks)
        elapsed_time = time.time() - start_time
        
        # 串行执行，应该需要约0.3秒
        assert len(results) == 3
        assert all(r.success for r in results)
        assert elapsed_time >= 0.25  # 至少0.3秒
    
    def test_max_workers_exceeds_task_count(self):
        """测试最大并发数超过任务数"""
        executor = ConcurrentExecutor(max_workers=10)
        
        # 只有3个任务
        tasks = [
            Task(id=f"task_{i}", func=slow_task, args=(0.1, i))
            for i in range(3)
        ]
        
        start_time = time.time()
        results = executor.execute_concurrent(tasks)
        elapsed_time = time.time() - start_time
        
        # 所有任务应该同时执行
        assert len(results) == 3
        assert all(r.success for r in results)
        assert elapsed_time < 0.25  # 应该约0.1秒
    
    def test_max_workers_configuration(self):
        """测试不同的最大并发数配置"""
        test_cases = [
            (1, 4, 0.35),   # 1个worker，4个任务，约0.4秒
            (2, 4, 0.18),   # 2个worker，4个任务，约0.2秒
            (4, 4, 0.08),   # 4个worker，4个任务，约0.1秒
        ]
        
        for max_workers, task_count, expected_min_time in test_cases:
            executor = ConcurrentExecutor(max_workers=max_workers)
            
            tasks = [
                Task(id=f"task_{i}", func=slow_task, args=(0.1, i))
                for i in range(task_count)
            ]
            
            start_time = time.time()
            results = executor.execute_concurrent(tasks)
            elapsed_time = time.time() - start_time
            
            assert len(results) == task_count
            assert all(r.success for r in results)
            # 验证执行时间符合预期
            assert elapsed_time >= expected_min_time
    
    def test_max_workers_with_mixed_duration_tasks(self):
        """测试不同执行时间的任务与最大并发数"""
        executor = ConcurrentExecutor(max_workers=2)
        
        # 创建不同执行时间的任务
        tasks = [
            Task(id="fast_1", func=slow_task, args=(0.05, 1)),
            Task(id="slow_1", func=slow_task, args=(0.2, 2)),
            Task(id="fast_2", func=slow_task, args=(0.05, 3)),
            Task(id="slow_2", func=slow_task, args=(0.2, 4))
        ]
        
        start_time = time.time()
        results = executor.execute_concurrent(tasks)
        elapsed_time = time.time() - start_time
        
        assert len(results) == 4
        assert all(r.success for r in results)
        # 应该比所有任务串行执行快
        assert elapsed_time < 0.5  # 串行需要0.5秒
    
    def test_max_workers_thread_safety(self):
        """测试最大并发数的线程安全性"""
        executor = ConcurrentExecutor(max_workers=3)
        
        # 创建大量任务
        tasks = [
            Task(id=f"task_{i}", func=simple_task, args=(i,))
            for i in range(50)
        ]
        
        results = executor.execute_concurrent(tasks)
        
        # 验证所有任务都成功执行
        assert len(results) == 50
        assert all(r.success for r in results)
        
        # 验证结果正确性
        for i, result in enumerate(results):
            assert result.result == i * 2


# ============================================================================
# 4. 结果收集测试
# ============================================================================

class TestResultCollection:
    """测试结果收集功能"""
    
    def test_result_collection_basic(self):
        """测试基本的结果收集"""
        executor = ConcurrentExecutor(max_workers=4)
        
        tasks = [
            Task(id=f"task_{i}", func=simple_task, args=(i,))
            for i in range(5)
        ]
        
        results = executor.execute_concurrent(tasks)
        
        # 验证收集到所有结果
        assert len(results) == 5
        
        # 验证每个结果的完整性
        for i, result in enumerate(results):
            assert isinstance(result, TaskResult)
            assert result.task_id == f"task_{i}"
            assert result.success is True
            assert result.result == i * 2
            assert result.error is None
            assert result.execution_time >= 0  # Very fast tasks may have 0.0
    
    def test_result_collection_preserves_order(self):
        """测试结果收集保持顺序"""
        executor = ConcurrentExecutor(max_workers=4)
        
        # 创建不同执行时间的任务
        tasks = [
            Task(id="slow", func=slow_task, args=(0.2, 1)),
            Task(id="fast", func=simple_task, args=(2,)),
            Task(id="medium", func=slow_task, args=(0.1, 3)),
            Task(id="instant", func=simple_task, args=(4,))
        ]
        
        results = executor.execute_concurrent(tasks)
        
        # 验证结果顺序与输入顺序一致
        assert len(results) == 4
        assert results[0].task_id == "slow"
        assert results[1].task_id == "fast"
        assert results[2].task_id == "medium"
        assert results[3].task_id == "instant"
    
    def test_result_collection_with_failures(self):
        """测试收集包含失败的结果"""
        executor = ConcurrentExecutor(max_workers=4)
        
        tasks = [
            Task(id="success_1", func=simple_task, args=(1,)),
            Task(id="failure_1", func=failing_task, args=("Error 1",)),
            Task(id="success_2", func=simple_task, args=(2,)),
            Task(id="failure_2", func=failing_task, args=("Error 2",))
        ]
        
        results = executor.execute_concurrent(tasks)
        
        # 验证所有结果都被收集
        assert len(results) == 4
        
        # 验证成功的结果
        assert results[0].success is True
        assert results[0].result == 2
        assert results[0].error is None
        
        # 验证失败的结果
        assert results[1].success is False
        assert results[1].result is None
        assert "Error 1" in results[1].error
        
        assert results[2].success is True
        assert results[3].success is False
    
    def test_result_collection_includes_metadata(self):
        """测试结果收集包含元数据"""
        executor = ConcurrentExecutor(max_workers=4)
        
        tasks = [
            Task(
                id=f"task_{i}",
                func=simple_task,
                args=(i,),
                metadata={"priority": i, "category": "test"}
            )
            for i in range(3)
        ]
        
        results = executor.execute_concurrent(tasks)
        
        # 验证元数据被保留
        for i, result in enumerate(results):
            assert result.metadata["priority"] == i
            assert result.metadata["category"] == "test"
    
    def test_result_collection_includes_execution_time(self):
        """测试结果收集包含执行时间"""
        executor = ConcurrentExecutor(max_workers=4)
        
        tasks = [
            Task(id="fast", func=simple_task, args=(1,)),
            Task(id="slow", func=slow_task, args=(0.2, 2))
        ]
        
        results = executor.execute_concurrent(tasks)
        
        # 验证执行时间被记录
        assert results[0].execution_time > 0
        assert results[0].execution_time < 0.1  # 快速任务
        
        assert results[1].execution_time >= 0.2  # 慢速任务
        assert results[1].execution_time < 0.5
    
    def test_result_collection_with_error_types(self):
        """测试结果收集包含错误类型"""
        executor = ConcurrentExecutor(max_workers=4)
        
        def type_error_task():
            raise TypeError("Type error")
        
        def runtime_error_task():
            raise RuntimeError("Runtime error")
        
        tasks = [
            Task(id="value_error", func=failing_task, args=("Value error",)),
            Task(id="type_error", func=type_error_task),
            Task(id="runtime_error", func=runtime_error_task)
        ]
        
        results = executor.execute_concurrent(tasks)
        
        # 验证错误类型被记录
        assert results[0].error_type == "ValueError"
        assert results[1].error_type == "TypeError"
        assert results[2].error_type == "RuntimeError"
    
    def test_result_collection_large_scale(self):
        """测试大规模结果收集"""
        executor = ConcurrentExecutor(max_workers=8)
        
        # 创建100个任务
        tasks = [
            Task(id=f"task_{i}", func=simple_task, args=(i,))
            for i in range(100)
        ]
        
        results = executor.execute_concurrent(tasks)
        
        # 验证所有结果都被收集
        assert len(results) == 100
        
        # 验证结果顺序和正确性
        for i, result in enumerate(results):
            assert result.task_id == f"task_{i}"
            assert result.success is True
            assert result.result == i * 2
    
    def test_result_collection_with_dependencies(self):
        """测试依赖执行的结果收集"""
        executor = ConcurrentExecutor(max_workers=4)
        
        tasks = [
            Task(id="task1", func=simple_task, args=(1,), dependencies=[]),
            Task(id="task2", func=simple_task, args=(2,), dependencies=["task1"]),
            Task(id="task3", func=simple_task, args=(3,), dependencies=["task1", "task2"])
        ]
        
        results = executor.execute_with_dependencies(tasks)
        
        # 验证所有结果都被收集
        assert len(results) == 3
        
        # 验证结果顺序
        assert results[0].task_id == "task1"
        assert results[1].task_id == "task2"
        assert results[2].task_id == "task3"
        
        # 验证所有任务都成功
        assert all(r.success for r in results)
    
    def test_result_collection_completeness(self):
        """测试结果收集的完整性"""
        executor = ConcurrentExecutor(max_workers=4)
        
        task = Task(
            id="complete_task",
            func=simple_task,
            args=(5,),
            metadata={"test": "data"}
        )
        
        results = executor.execute_concurrent([task])
        result = results[0]
        
        # 验证结果包含所有必要字段
        assert hasattr(result, 'task_id')
        assert hasattr(result, 'success')
        assert hasattr(result, 'result')
        assert hasattr(result, 'error')
        assert hasattr(result, 'execution_time')
        assert hasattr(result, 'metadata')
        assert hasattr(result, 'skipped')
        assert hasattr(result, 'error_type')
        
        # 验证字段值
        assert result.task_id == "complete_task"
        assert result.success is True
        assert result.result == 10
        assert result.error is None
        assert result.execution_time >= 0  # Very fast tasks may have 0.0
        assert result.metadata == {"test": "data"}
        assert result.skipped is False
        assert result.error_type is None


# ============================================================================
# 集成测试
# ============================================================================

class TestConcurrentExecutorIntegration:
    """并发执行器集成测试"""
    
    def test_full_workflow(self):
        """测试完整的工作流程"""
        executor = ConcurrentExecutor(max_workers=4)
        
        # 创建一个复杂的任务集
        tasks = [
            Task(id="task_1", func=simple_task, args=(1,)),
            Task(id="task_2", func=slow_task, args=(0.1, 2)),
            Task(id="task_3", func=simple_task, args=(3,)),
            Task(id="task_4", func=failing_task, args=("Expected error",)),
            Task(id="task_5", func=simple_task, args=(5,))
        ]
        
        # 执行任务
        results = executor.execute_concurrent(tasks)
        
        # 验证结果
        assert len(results) == 5
        assert results[0].success is True
        assert results[1].success is True
        assert results[2].success is True
        assert results[3].success is False
        assert results[4].success is True
        
        # 验证进度
        progress = executor.get_progress()
        assert progress.total == 5
        assert progress.completed == 5
        assert progress.failed == 1
        
        # 验证错误汇总
        error_summary = executor.get_error_summary()
        assert error_summary.total_errors == 1
        assert "task_4" in error_summary.failed_tasks
    
    def test_concurrent_and_sequential_comparison(self):
        """测试并发和串行执行的对比"""
        # 串行执行
        sequential_executor = ConcurrentExecutor(max_workers=1)
        tasks_seq = [
            Task(id=f"seq_task_{i}", func=slow_task, args=(0.1, i))
            for i in range(4)
        ]
        
        start_seq = time.time()
        results_seq = sequential_executor.execute_concurrent(tasks_seq)
        time_seq = time.time() - start_seq
        
        # 并发执行
        concurrent_executor = ConcurrentExecutor(max_workers=4)
        tasks_con = [
            Task(id=f"con_task_{i}", func=slow_task, args=(0.1, i))
            for i in range(4)
        ]
        
        start_con = time.time()
        results_con = concurrent_executor.execute_concurrent(tasks_con)
        time_con = time.time() - start_con
        
        # 验证结果一致
        assert len(results_seq) == len(results_con) == 4
        assert all(r.success for r in results_seq)
        assert all(r.success for r in results_con)
        
        # 验证并发更快
        assert time_con < time_seq
        assert time_seq >= 0.35  # 串行至少0.4秒
        assert time_con < 0.25   # 并发应该约0.1秒


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
