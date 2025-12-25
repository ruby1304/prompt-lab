# tests/test_concurrent_error_handling.py
"""
并发错误处理测试

测试并发执行器的错误隔离、错误收集、可选步骤处理和结果顺序保持功能。
"""

import pytest
import time
from src.concurrent_executor import (
    ConcurrentExecutor,
    Task,
    TaskResult,
    ErrorSummary,
    ExecutionSummary,
    ExecutionProgress
)


def success_task(x: int) -> int:
    """成功的任务"""
    return x * 2


def failing_task(error_msg: str = "Task failed") -> None:
    """失败的任务"""
    raise ValueError(error_msg)


def type_error_task() -> None:
    """抛出 TypeError 的任务"""
    raise TypeError("Type error occurred")


def runtime_error_task() -> None:
    """抛出 RuntimeError 的任务"""
    raise RuntimeError("Runtime error occurred")


class TestErrorIsolation:
    """测试错误隔离 - 确保一个任务的错误不影响其他任务"""
    
    def test_error_isolation_in_concurrent_execution(self):
        """测试并发执行中的错误隔离"""
        executor = ConcurrentExecutor(max_workers=4)
        
        tasks = [
            Task(id="task1", func=success_task, args=(1,)),
            Task(id="task2", func=failing_task, args=("Error in task2",)),
            Task(id="task3", func=success_task, args=(3,)),
            Task(id="task4", func=failing_task, args=("Error in task4",)),
            Task(id="task5", func=success_task, args=(5,))
        ]
        
        results = executor.execute_concurrent(tasks)
        
        # 验证所有任务都执行了
        assert len(results) == 5
        
        # 验证成功的任务不受失败任务影响
        assert results[0].success is True
        assert results[0].result == 2
        
        assert results[1].success is False
        assert "Error in task2" in results[1].error
        
        assert results[2].success is True
        assert results[2].result == 6
        
        assert results[3].success is False
        assert "Error in task4" in results[3].error
        
        assert results[4].success is True
        assert results[4].result == 10
    
    def test_error_isolation_with_dependencies(self):
        """测试依赖执行中的错误隔离"""
        executor = ConcurrentExecutor(max_workers=4)
        
        # 创建一个有分支的依赖图
        # root -> branch1 (fails) -> merge1
        #      -> branch2 (success) -> merge2
        tasks = [
            Task(id="root", func=success_task, args=(1,), dependencies=[]),
            Task(id="branch1", func=failing_task, args=("Branch1 failed",), dependencies=["root"], required=False),
            Task(id="branch2", func=success_task, args=(2,), dependencies=["root"]),
            Task(id="merge1", func=success_task, args=(3,), dependencies=["branch1"]),
            Task(id="merge2", func=success_task, args=(4,), dependencies=["branch2"])
        ]
        
        results = executor.execute_with_dependencies(tasks)
        
        # root 应该成功
        assert results[0].success is True
        
        # branch1 失败但不影响 branch2
        assert results[1].success is False
        assert results[2].success is True
        
        # merge1 应该继续执行（因为 branch1 是可选的）
        assert results[3].success is True
        
        # merge2 应该成功
        assert results[4].success is True


class TestErrorCollection:
    """测试错误收集 - 确保所有错误被正确收集和报告"""
    
    def test_error_summary_collection(self):
        """测试错误汇总收集"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="success1", func=success_task, args=(1,)),
            Task(id="fail1", func=failing_task, args=("Error 1",), required=True),
            Task(id="fail2", func=type_error_task, required=False),
            Task(id="success2", func=success_task, args=(2,)),
            Task(id="fail3", func=runtime_error_task, required=True)
        ]
        
        results = executor.execute_concurrent(tasks)
        error_summary = executor.get_error_summary()
        
        # 验证错误统计
        assert error_summary.total_errors == 3
        assert len(error_summary.failed_tasks) == 3
        assert "fail1" in error_summary.failed_tasks
        assert "fail2" in error_summary.failed_tasks
        assert "fail3" in error_summary.failed_tasks
        
        # 验证错误类型统计
        assert "ValueError" in error_summary.error_types
        assert "TypeError" in error_summary.error_types
        assert "RuntimeError" in error_summary.error_types
        
        # 验证关键错误（必需任务失败）
        assert len(error_summary.critical_errors) == 2
        assert "fail1" in error_summary.critical_errors
        assert "fail3" in error_summary.critical_errors
        assert "fail2" not in error_summary.critical_errors  # 可选任务
    
    def test_error_types_tracking(self):
        """测试错误类型跟踪"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="value_error1", func=failing_task, args=("Error 1",)),
            Task(id="value_error2", func=failing_task, args=("Error 2",)),
            Task(id="type_error", func=type_error_task),
            Task(id="runtime_error", func=runtime_error_task)
        ]
        
        results = executor.execute_concurrent(tasks)
        error_summary = executor.get_error_summary()
        
        # 验证错误类型计数
        assert error_summary.error_types["ValueError"] == 2
        assert error_summary.error_types["TypeError"] == 1
        assert error_summary.error_types["RuntimeError"] == 1
    
    def test_execution_summary(self):
        """测试完整的执行汇总"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="success1", func=success_task, args=(1,)),
            Task(id="fail1", func=failing_task, required=True),
            Task(id="success2", func=success_task, args=(2,))
        ]
        
        results = executor.execute_concurrent(tasks)
        summary = executor.get_execution_summary(results)
        
        # 验证进度信息
        assert summary.progress.total == 3
        assert summary.progress.completed == 3
        assert summary.progress.failed == 1
        
        # 验证错误信息
        assert summary.errors.total_errors == 1
        assert summary.errors.has_critical_errors() is True
        
        # 验证结果分类
        assert len(summary.get_successful_results()) == 2
        assert len(summary.get_failed_results()) == 1
        assert len(summary.get_skipped_results()) == 0
        
        # 验证整体成功状态
        assert summary.is_successful() is False  # 有关键错误


class TestOptionalStepHandling:
    """测试可选步骤处理 - 确保可选和必需步骤被正确处理"""
    
    def test_required_task_failure_blocks_dependents(self):
        """测试必需任务失败阻止依赖任务"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="required_fail", func=failing_task, required=True),
            Task(id="dependent", func=success_task, args=(1,), dependencies=["required_fail"])
        ]
        
        results = executor.execute_with_dependencies(tasks)
        
        # 必需任务失败
        assert results[0].success is False
        # 验证任务本身是必需的（通过 task 对象）
        assert tasks[0].required is True
        
        # 依赖任务应该被跳过
        assert results[1].success is False
        assert results[1].skipped is True
        assert "必需的依赖任务失败" in results[1].error
    
    def test_optional_task_failure_allows_dependents(self):
        """测试可选任务失败允许依赖任务继续"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="optional_fail", func=failing_task, required=False),
            Task(id="dependent", func=success_task, args=(1,), dependencies=["optional_fail"])
        ]
        
        results = executor.execute_with_dependencies(tasks)
        
        # 可选任务失败
        assert results[0].success is False
        # 验证任务本身是可选的（通过 task 对象）
        assert tasks[0].required is False
        
        # 依赖任务应该继续执行
        assert results[1].success is True
        assert results[1].skipped is False
        assert results[1].result == 2
    
    def test_mixed_required_optional_dependencies(self):
        """测试混合必需和可选依赖"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="required_success", func=success_task, args=(1,), required=True),
            Task(id="optional_fail", func=failing_task, required=False),
            Task(id="dependent", func=success_task, args=(2,), 
                 dependencies=["required_success", "optional_fail"])
        ]
        
        results = executor.execute_with_dependencies(tasks)
        
        # 必需任务成功
        assert results[0].success is True
        
        # 可选任务失败
        assert results[1].success is False
        
        # 依赖任务应该继续（因为必需依赖成功，可选依赖失败不影响）
        assert results[2].success is True
        assert results[2].result == 4
    
    def test_skipped_tasks_tracking(self):
        """测试跳过任务的跟踪"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="required_fail", func=failing_task, required=True),
            Task(id="dependent1", func=success_task, args=(1,), dependencies=["required_fail"]),
            Task(id="dependent2", func=success_task, args=(2,), dependencies=["required_fail"])
        ]
        
        results = executor.execute_with_dependencies(tasks)
        error_summary = executor.get_error_summary()
        
        # 验证跳过的任务被记录
        assert len(error_summary.skipped_tasks) == 2
        assert "dependent1" in error_summary.skipped_tasks
        assert "dependent2" in error_summary.skipped_tasks
        
        # 验证进度中的跳过计数
        progress = executor.get_progress()
        assert progress.skipped == 2


class TestResultOrderPreservation:
    """测试结果顺序保持 - 确保结果顺序与输入一致"""
    
    def test_result_order_with_mixed_success_failure(self):
        """测试混合成功和失败时的结果顺序"""
        executor = ConcurrentExecutor(max_workers=4)
        
        tasks = [
            Task(id="task0", func=success_task, args=(0,)),
            Task(id="task1", func=failing_task),
            Task(id="task2", func=success_task, args=(2,)),
            Task(id="task3", func=failing_task),
            Task(id="task4", func=success_task, args=(4,))
        ]
        
        results = executor.execute_concurrent(tasks)
        
        # 验证结果顺序
        assert len(results) == 5
        assert results[0].task_id == "task0"
        assert results[1].task_id == "task1"
        assert results[2].task_id == "task2"
        assert results[3].task_id == "task3"
        assert results[4].task_id == "task4"
        
        # 验证结果正确性
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True
        assert results[3].success is False
        assert results[4].success is True
    
    def test_result_order_with_dependencies_and_failures(self):
        """测试依赖执行中有失败时的结果顺序"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="task0", func=success_task, args=(0,), dependencies=[]),
            Task(id="task1", func=failing_task, dependencies=["task0"], required=True),
            Task(id="task2", func=success_task, args=(2,), dependencies=["task0"]),
            Task(id="task3", func=success_task, args=(3,), dependencies=["task1"]),  # 会被跳过
            Task(id="task4", func=success_task, args=(4,), dependencies=["task2"])
        ]
        
        results = executor.execute_with_dependencies(tasks)
        
        # 验证结果顺序与输入一致
        assert len(results) == 5
        assert results[0].task_id == "task0"
        assert results[1].task_id == "task1"
        assert results[2].task_id == "task2"
        assert results[3].task_id == "task3"
        assert results[4].task_id == "task4"
        
        # 验证执行结果
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True
        assert results[3].success is False  # 跳过
        assert results[3].skipped is True
        assert results[4].success is True
    
    def test_result_order_with_all_failures(self):
        """测试所有任务失败时的结果顺序"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id=f"task{i}", func=failing_task, args=(f"Error {i}",))
            for i in range(5)
        ]
        
        results = executor.execute_concurrent(tasks)
        
        # 验证结果顺序
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result.task_id == f"task{i}"
            assert result.success is False
            assert f"Error {i}" in result.error


class TestErrorReporting:
    """测试错误报告功能"""
    
    def test_error_summary_to_dict(self):
        """测试错误汇总转换为字典"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="success", func=success_task, args=(1,)),
            Task(id="fail", func=failing_task, required=True)
        ]
        
        results = executor.execute_concurrent(tasks)
        error_summary = executor.get_error_summary()
        error_dict = error_summary.to_dict()
        
        # 验证字典结构
        assert "total_errors" in error_dict
        assert "failed_tasks" in error_dict
        assert "skipped_tasks" in error_dict
        assert "error_types" in error_dict
        assert "critical_errors" in error_dict
        assert "has_critical_errors" in error_dict
        
        # 验证值
        assert error_dict["total_errors"] == 1
        assert "fail" in error_dict["failed_tasks"]
        assert error_dict["has_critical_errors"] is True
    
    def test_execution_summary_to_dict(self):
        """测试执行汇总转换为字典"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="success", func=success_task, args=(1,)),
            Task(id="fail", func=failing_task, required=True)
        ]
        
        results = executor.execute_concurrent(tasks)
        summary = executor.get_execution_summary(results)
        summary_dict = summary.to_dict()
        
        # 验证字典结构
        assert "progress" in summary_dict
        assert "errors" in summary_dict
        assert "is_successful" in summary_dict
        assert "failed_count" in summary_dict
        assert "skipped_count" in summary_dict
        assert "successful_count" in summary_dict
        
        # 验证值
        assert summary_dict["progress"]["total"] == 2
        assert summary_dict["progress"]["completed"] == 2
        assert summary_dict["progress"]["failed"] == 1
        assert summary_dict["failed_count"] == 1
        assert summary_dict["successful_count"] == 1
        assert summary_dict["is_successful"] is False
    
    def test_progress_success_rate(self):
        """测试进度中的成功率计算"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="success1", func=success_task, args=(1,)),
            Task(id="fail1", func=failing_task),
            Task(id="success2", func=success_task, args=(2,)),
            Task(id="success3", func=success_task, args=(3,))
        ]
        
        results = executor.execute_concurrent(tasks)
        progress = executor.get_progress()
        
        # 4个任务，3个成功，成功率应该是 0.75
        assert progress.success_rate == 0.75
    
    def test_progress_dict_includes_skipped(self):
        """测试进度字典包含跳过计数"""
        executor = ConcurrentExecutor()
        
        tasks = [
            Task(id="required_fail", func=failing_task, required=True),
            Task(id="dependent", func=success_task, args=(1,), dependencies=["required_fail"])
        ]
        
        results = executor.execute_with_dependencies(tasks)
        progress_dict = executor.get_progress_dict()
        
        # 验证跳过计数在字典中
        assert "skipped" in progress_dict
        assert progress_dict["skipped"] == 1
        assert "success_rate" in progress_dict


class TestComplexErrorScenarios:
    """测试复杂的错误场景"""
    
    def test_cascading_failures(self):
        """测试级联失败"""
        executor = ConcurrentExecutor()
        
        # 创建一个链式依赖，第一个失败导致后续都被跳过
        tasks = [
            Task(id="task1", func=failing_task, required=True),
            Task(id="task2", func=success_task, args=(2,), dependencies=["task1"]),
            Task(id="task3", func=success_task, args=(3,), dependencies=["task2"]),
            Task(id="task4", func=success_task, args=(4,), dependencies=["task3"])
        ]
        
        results = executor.execute_with_dependencies(tasks)
        error_summary = executor.get_error_summary()
        
        # 第一个任务失败
        assert results[0].success is False
        
        # 后续任务都被跳过
        assert all(r.skipped for r in results[1:])
        
        # 验证跳过计数
        assert len(error_summary.skipped_tasks) == 3
    
    def test_partial_branch_failure(self):
        """测试部分分支失败"""
        executor = ConcurrentExecutor(max_workers=4)
        
        # 创建一个有多个分支的依赖图
        # root -> branch1 (fails, required) -> merge
        #      -> branch2 (success) -> merge
        #      -> branch3 (success) -> merge
        tasks = [
            Task(id="root", func=success_task, args=(0,), dependencies=[]),
            Task(id="branch1", func=failing_task, dependencies=["root"], required=True),
            Task(id="branch2", func=success_task, args=(2,), dependencies=["root"]),
            Task(id="branch3", func=success_task, args=(3,), dependencies=["root"]),
            Task(id="merge", func=success_task, args=(4,), 
                 dependencies=["branch1", "branch2", "branch3"])
        ]
        
        results = executor.execute_with_dependencies(tasks)
        
        # root 成功
        assert results[0].success is True
        
        # branch1 失败，branch2 和 branch3 成功
        assert results[1].success is False
        assert results[2].success is True
        assert results[3].success is True
        
        # merge 被跳过（因为 branch1 是必需的且失败了）
        assert results[4].skipped is True
    
    def test_error_isolation_with_high_concurrency(self):
        """测试高并发下的错误隔离"""
        executor = ConcurrentExecutor(max_workers=8)
        
        # 创建大量任务，其中一半会失败
        tasks = []
        for i in range(20):
            if i % 2 == 0:
                tasks.append(Task(id=f"task{i}", func=success_task, args=(i,)))
            else:
                tasks.append(Task(id=f"task{i}", func=failing_task, args=(f"Error {i}",)))
        
        results = executor.execute_concurrent(tasks)
        
        # 验证所有任务都执行了
        assert len(results) == 20
        
        # 验证成功和失败的任务数量
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        assert len(successful) == 10
        assert len(failed) == 10
        
        # 验证结果顺序
        for i, result in enumerate(results):
            assert result.task_id == f"task{i}"

