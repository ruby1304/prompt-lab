# tests/test_concurrent_executor_basic.py
"""
基础测试 - ConcurrentExecutor 核心功能

测试并发执行器的基本功能，包括任务执行、结果收集和进度跟踪。
"""

import pytest
import time
from src.concurrent_executor import (
    ConcurrentExecutor,
    Task,
    TaskResult,
    ExecutionProgress,
    ExecutionStrategy
)


def simple_task(x: int) -> int:
    """简单的测试任务"""
    return x * 2


def slow_task(duration: float) -> str:
    """慢速任务，用于测试并发"""
    time.sleep(duration)
    return f"slept for {duration}s"


def failing_task() -> None:
    """会失败的任务"""
    raise ValueError("This task always fails")


class TestConcurrentExecutorBasic:
    """ConcurrentExecutor 基础功能测试"""
    
    def test_initialization_thread_strategy(self):
        """测试使用线程策略初始化"""
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        assert executor.max_workers == 4
        assert executor.strategy == ExecutionStrategy.THREAD
    
    def test_initialization_process_strategy(self):
        """测试使用进程策略初始化"""
        executor = ConcurrentExecutor(max_workers=2, strategy="process")
        assert executor.max_workers == 2
        assert executor.strategy == ExecutionStrategy.PROCESS
    
    def test_initialization_invalid_strategy(self):
        """测试无效的执行策略"""
        with pytest.raises(ValueError, match="不支持的执行策略"):
            ConcurrentExecutor(strategy="invalid")
    
    def test_execute_concurrent_empty_list(self):
        """测试执行空任务列表"""
        executor = ConcurrentExecutor()
        results = executor.execute_concurrent([])
        assert results == []
    
    def test_execute_concurrent_single_task(self):
        """测试执行单个任务"""
        executor = ConcurrentExecutor()
        
        task = Task(
            id="task1",
            func=simple_task,
            args=(5,)
        )
        
        results = executor.execute_concurrent([task])
        
        assert len(results) == 1
        assert results[0].task_id == "task1"
        assert results[0].success is True
        assert results[0].result == 10
        assert results[0].error is None
    
    def test_execute_concurrent_multiple_tasks(self):
        """测试并发执行多个任务"""
        executor = ConcurrentExecutor(max_workers=4)
        
        tasks = [
            Task(id=f"task{i}", func=simple_task, args=(i,))
            for i in range(5)
        ]
        
        results = executor.execute_concurrent(tasks)
        
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result.task_id == f"task{i}"
            assert result.success is True
            assert result.result == i * 2
    
    def test_execute_concurrent_preserves_order(self):
        """测试结果顺序与输入顺序一致"""
        executor = ConcurrentExecutor(max_workers=4)
        
        # 创建不同执行时间的任务
        tasks = [
            Task(id="fast", func=simple_task, args=(1,)),
            Task(id="slow", func=slow_task, args=(0.1,)),
            Task(id="medium", func=simple_task, args=(2,))
        ]
        
        results = executor.execute_concurrent(tasks)
        
        assert len(results) == 3
        assert results[0].task_id == "fast"
        assert results[1].task_id == "slow"
        assert results[2].task_id == "medium"
    
    def test_execute_concurrent_with_failure(self):
        """测试处理失败的任务"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="success", func=simple_task, args=(5,)),
            Task(id="failure", func=failing_task),
            Task(id="success2", func=simple_task, args=(10,))
        ]
        
        results = executor.execute_concurrent(tasks)
        
        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False
        assert "This task always fails" in results[1].error
        assert results[2].success is True
    
    def test_execute_concurrent_with_progress_callback(self):
        """测试进度回调"""
        executor = ConcurrentExecutor(max_workers=2)
        
        progress_updates = []
        
        def progress_callback(progress: ExecutionProgress):
            progress_updates.append({
                'completed': progress.completed,
                'total': progress.total,
                'failed': progress.failed
            })
        
        tasks = [
            Task(id=f"task{i}", func=simple_task, args=(i,))
            for i in range(3)
        ]
        
        results = executor.execute_concurrent(tasks, progress_callback=progress_callback)
        
        assert len(results) == 3
        assert len(progress_updates) > 0
        # 最后一次更新应该显示所有任务完成
        assert progress_updates[-1]['completed'] == 3
        assert progress_updates[-1]['total'] == 3
    
    def test_task_metadata_preserved(self):
        """测试任务元数据被保留"""
        executor = ConcurrentExecutor()
        
        task = Task(
            id="task1",
            func=simple_task,
            args=(5,),
            metadata={"key": "value", "number": 42}
        )
        
        results = executor.execute_concurrent([task])
        
        assert results[0].metadata == {"key": "value", "number": 42}
    
    def test_execution_time_recorded(self):
        """测试执行时间被记录"""
        executor = ConcurrentExecutor()
        
        task = Task(
            id="slow_task",
            func=slow_task,
            args=(0.1,)
        )
        
        results = executor.execute_concurrent([task])
        
        assert results[0].execution_time >= 0.1
        assert results[0].execution_time < 0.5  # 应该不会太慢
    
    def test_get_progress(self):
        """测试获取进度信息"""
        executor = ConcurrentExecutor()
        
        # 初始进度
        progress = executor.get_progress()
        assert progress.total == 0
        assert progress.completed == 0
    
    def test_max_workers_limit(self):
        """测试最大并发数限制"""
        executor = ConcurrentExecutor(max_workers=2)
        
        # 创建4个慢速任务
        tasks = [
            Task(id=f"task{i}", func=slow_task, args=(0.2,))
            for i in range(4)
        ]
        
        start_time = time.time()
        results = executor.execute_concurrent(tasks)
        elapsed_time = time.time() - start_time
        
        # 如果真的并发，4个任务应该在约0.4秒内完成（2批，每批0.2秒）
        # 如果串行，需要0.8秒
        assert len(results) == 4
        assert all(r.success for r in results)
        # 应该比串行快，但比完全并发慢
        assert 0.3 < elapsed_time < 0.6


class TestConcurrentExecutorWithDependencies:
    """ConcurrentExecutor 依赖执行测试"""
    
    def test_execute_with_dependencies_empty_list(self):
        """测试执行空任务列表"""
        executor = ConcurrentExecutor()
        results = executor.execute_with_dependencies([])
        assert results == []
    
    def test_execute_with_dependencies_no_deps(self):
        """测试无依赖的任务"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="task1", func=simple_task, args=(1,)),
            Task(id="task2", func=simple_task, args=(2,)),
            Task(id="task3", func=simple_task, args=(3,))
        ]
        
        results = executor.execute_with_dependencies(tasks)
        
        assert len(results) == 3
        assert all(r.success for r in results)
    
    def test_execute_with_dependencies_linear_chain(self):
        """测试线性依赖链"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="task1", func=simple_task, args=(1,), dependencies=[]),
            Task(id="task2", func=simple_task, args=(2,), dependencies=["task1"]),
            Task(id="task3", func=simple_task, args=(3,), dependencies=["task2"])
        ]
        
        results = executor.execute_with_dependencies(tasks)
        
        assert len(results) == 3
        assert all(r.success for r in results)
        assert results[0].task_id == "task1"
        assert results[1].task_id == "task2"
        assert results[2].task_id == "task3"
    
    def test_execute_with_dependencies_parallel_branches(self):
        """测试并行分支"""
        executor = ConcurrentExecutor(max_workers=4)
        
        tasks = [
            Task(id="root", func=simple_task, args=(0,), dependencies=[]),
            Task(id="branch1", func=simple_task, args=(1,), dependencies=["root"]),
            Task(id="branch2", func=simple_task, args=(2,), dependencies=["root"]),
            Task(id="merge", func=simple_task, args=(3,), dependencies=["branch1", "branch2"])
        ]
        
        results = executor.execute_with_dependencies(tasks)
        
        assert len(results) == 4
        assert all(r.success for r in results)
    
    def test_execute_with_dependencies_from_graph(self):
        """测试使用显式依赖图"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="task1", func=simple_task, args=(1,)),
            Task(id="task2", func=simple_task, args=(2,)),
            Task(id="task3", func=simple_task, args=(3,))
        ]
        
        dependency_graph = {
            "task1": [],
            "task2": ["task1"],
            "task3": ["task1", "task2"]
        }
        
        results = executor.execute_with_dependencies(tasks, dependency_graph)
        
        assert len(results) == 3
        assert all(r.success for r in results)
    
    def test_execute_with_dependencies_cycle_detection(self):
        """测试循环依赖检测"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="task1", func=simple_task, args=(1,), dependencies=["task2"]),
            Task(id="task2", func=simple_task, args=(2,), dependencies=["task1"])
        ]
        
        with pytest.raises(ValueError, match="检测到循环依赖"):
            executor.execute_with_dependencies(tasks)
    
    def test_execute_with_dependencies_missing_dependency(self):
        """测试缺失的依赖"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="task1", func=simple_task, args=(1,), dependencies=["nonexistent"])
        ]
        
        with pytest.raises(ValueError, match="依赖的任务.*不存在"):
            executor.execute_with_dependencies(tasks)
    
    def test_execute_with_dependencies_required_failure(self):
        """测试必需依赖失败时跳过后续任务"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="task1", func=failing_task, required=True),
            Task(id="task2", func=simple_task, args=(2,), dependencies=["task1"], required=True)
        ]
        
        results = executor.execute_with_dependencies(tasks)
        
        assert len(results) == 2
        assert results[0].success is False
        assert results[1].success is False
        assert "必需的依赖任务失败" in results[1].error
    
    def test_execute_with_dependencies_optional_failure(self):
        """测试可选依赖失败时继续执行"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="task1", func=failing_task, required=False),
            Task(id="task2", func=simple_task, args=(2,), dependencies=["task1"], required=True)
        ]
        
        results = executor.execute_with_dependencies(tasks)
        
        assert len(results) == 2
        assert results[0].success is False
        assert results[1].success is True  # 应该继续执行


class TestExecutionProgress:
    """ExecutionProgress 测试"""
    
    def test_progress_properties(self):
        """测试进度属性计算"""
        progress = ExecutionProgress(
            total=10,
            completed=5,
            failed=1,
            running=2,
            pending=3,
            start_time=100.0,
            current_time=110.0
        )
        
        assert progress.elapsed_time == 10.0
        assert progress.completion_rate == 0.5
        assert progress.estimated_remaining_time == 10.0  # 5 tasks * 2s/task
    
    def test_progress_completion_rate_zero_total(self):
        """测试总数为0时的完成率"""
        progress = ExecutionProgress(
            total=0,
            completed=0,
            failed=0,
            running=0,
            pending=0,
            start_time=100.0,
            current_time=100.0
        )
        
        assert progress.completion_rate == 1.0
    
    def test_progress_estimated_time_no_completed(self):
        """测试没有完成任务时的预计时间"""
        progress = ExecutionProgress(
            total=10,
            completed=0,
            failed=0,
            running=5,
            pending=5,
            start_time=100.0,
            current_time=100.0
        )
        
        assert progress.estimated_remaining_time is None
