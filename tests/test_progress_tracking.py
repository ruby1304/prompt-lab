#!/usr/bin/env python3
"""
进度跟踪功能测试

测试进度跟踪的核心功能：
1. 实时进度更新
2. 进度查询接口
3. 与 PipelineProgressTracker 集成
"""

import pytest
import time
import threading
from datetime import datetime, timedelta

from src.progress_tracker import (
    ProgressStats, ProgressTracker, PipelineProgressTracker,
    EvaluationProgressTracker
)
from src.concurrent_executor import (
    ConcurrentExecutor, Task, ExecutionProgress
)


class TestProgressStats:
    """测试 ProgressStats 类"""
    
    def test_progress_stats_creation(self):
        """测试创建进度统计"""
        stats = ProgressStats(total_items=10)
        
        assert stats.total_items == 10
        assert stats.completed_items == 0
        assert stats.failed_items == 0
        assert stats.success_items == 0
        assert stats.progress_percentage == 0.0
    
    def test_progress_stats_success_items(self):
        """测试成功项目数计算"""
        stats = ProgressStats(total_items=10, completed_items=8, failed_items=2)
        
        assert stats.success_items == 6  # 8 - 2
    
    def test_progress_stats_percentage(self):
        """测试进度百分比计算"""
        stats = ProgressStats(total_items=10, completed_items=5)
        
        assert stats.progress_percentage == 50.0
    
    def test_progress_stats_elapsed_time(self):
        """测试已用时间计算"""
        start_time = datetime.now() - timedelta(seconds=5)
        stats = ProgressStats(total_items=10, start_time=start_time)
        
        elapsed = stats.elapsed_time
        assert elapsed.total_seconds() >= 5.0
        assert elapsed.total_seconds() < 6.0  # 允许一些误差
    
    def test_progress_stats_estimated_remaining_time(self):
        """测试预估剩余时间计算"""
        start_time = datetime.now() - timedelta(seconds=10)
        stats = ProgressStats(
            total_items=10,
            completed_items=5,
            start_time=start_time
        )
        
        remaining = stats.estimated_remaining_time
        assert remaining is not None
        # 已完成5个用了10秒，剩余5个预计也需要10秒
        assert 9.0 <= remaining.total_seconds() <= 11.0
    
    def test_progress_stats_no_completed_items(self):
        """测试没有完成项目时的预估时间"""
        stats = ProgressStats(total_items=10, completed_items=0)
        
        assert stats.estimated_remaining_time is None
        assert stats.estimated_completion_time is None


class TestProgressTracker:
    """测试 ProgressTracker 类"""
    
    def test_progress_tracker_creation(self):
        """测试创建进度跟踪器"""
        tracker = ProgressTracker(
            task_name="测试任务",
            total_items=10
        )
        
        assert tracker.task_name == "测试任务"
        assert tracker.stats.total_items == 10
    
    def test_progress_tracker_update(self):
        """测试更新进度"""
        tracker = ProgressTracker(task_name="测试", total_items=10)
        tracker.start()
        
        # 更新进度
        tracker.update(
            current_item="项目1",
            current_step="步骤1",
            increment=1
        )
        
        stats = tracker.get_stats()
        assert stats.completed_items == 1
        assert stats.current_item == "项目1"
        assert stats.current_step == "步骤1"
        
        tracker.finish()
    
    def test_progress_tracker_get_stats(self):
        """测试获取统计信息"""
        tracker = ProgressTracker(task_name="测试", total_items=10)
        tracker.start()
        
        tracker.update(completed=5, failed=True)
        
        stats = tracker.get_stats()
        assert stats.completed_items == 5
        assert stats.failed_items == 1
        assert stats.success_items == 4
        
        tracker.finish()
    
    def test_progress_tracker_get_stats_dict(self):
        """测试获取统计信息字典"""
        tracker = ProgressTracker(task_name="测试", total_items=10)
        tracker.start()
        
        tracker.update(completed=5, current_item="项目5")
        
        stats_dict = tracker.get_stats_dict()
        assert stats_dict["total_items"] == 10
        assert stats_dict["completed_items"] == 5
        assert stats_dict["progress_percentage"] == 50.0
        assert stats_dict["current_item"] == "项目5"
        assert "elapsed_time" in stats_dict
        
        tracker.finish()
    
    def test_progress_tracker_callback(self):
        """测试进度回调"""
        tracker = ProgressTracker(task_name="测试", total_items=10)
        
        callback_called = []
        
        def callback(stats):
            callback_called.append(stats.completed_items)
        
        tracker.add_callback(callback)
        tracker.start()
        
        # 更新进度
        tracker.update(increment=1)
        tracker.update(increment=1)
        
        assert len(callback_called) == 2
        assert callback_called == [1, 2]
        
        tracker.finish()
    
    def test_progress_tracker_thread_safety(self):
        """测试线程安全性"""
        tracker = ProgressTracker(task_name="测试", total_items=100)
        tracker.start()
        
        def update_progress():
            for _ in range(10):
                tracker.update(increment=1)
                time.sleep(0.001)
        
        # 创建多个线程同时更新进度
        threads = [threading.Thread(target=update_progress) for _ in range(10)]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # 验证最终计数正确
        stats = tracker.get_stats()
        assert stats.completed_items == 100
        
        tracker.finish()


class TestPipelineProgressTracker:
    """测试 PipelineProgressTracker 类"""
    
    def test_pipeline_progress_tracker_creation(self):
        """测试创建 Pipeline 进度跟踪器"""
        tracker = PipelineProgressTracker(
            pipeline_name="测试Pipeline",
            total_samples=5,
            total_steps=3,
            variant="baseline"
        )
        
        assert tracker.pipeline_name == "测试Pipeline"
        assert tracker.total_steps == 3
        assert tracker.variant == "baseline"
        assert tracker.stats.total_items == 5
    
    def test_pipeline_progress_tracker_update_sample(self):
        """测试更新样本进度"""
        tracker = PipelineProgressTracker(
            pipeline_name="测试",
            total_samples=5,
            total_steps=3
        )
        tracker.start()
        
        # 更新样本进度
        tracker.update_sample(
            sample_index=0,
            sample_id="sample_1",
            step_index=1,
            step_name="步骤2"
        )
        
        stats = tracker.get_stats()
        assert "sample_1" in stats.current_item
        assert "步骤2" in stats.current_step
        
        tracker.finish()
    
    def test_pipeline_progress_tracker_complete_sample(self):
        """测试完成样本"""
        tracker = PipelineProgressTracker(
            pipeline_name="测试",
            total_samples=5,
            total_steps=3
        )
        tracker.start()
        
        # 完成第一个样本
        tracker.complete_sample(
            sample_index=0,
            sample_id="sample_1",
            failed=False
        )
        
        stats = tracker.get_stats()
        assert stats.completed_items == 1
        assert stats.failed_items == 0
        
        # 完成第二个样本（失败）
        tracker.complete_sample(
            sample_index=1,
            sample_id="sample_2",
            failed=True
        )
        
        stats = tracker.get_stats()
        assert stats.completed_items == 2
        assert stats.failed_items == 1
        
        tracker.finish()
    
    def test_pipeline_progress_tracker_get_pipeline_stats_dict(self):
        """测试获取 Pipeline 统计信息字典"""
        tracker = PipelineProgressTracker(
            pipeline_name="测试Pipeline",
            total_samples=5,
            total_steps=3,
            variant="variant_1"
        )
        tracker.start()
        
        tracker.update_sample(0, "sample_1", 1, "步骤2")
        
        stats_dict = tracker.get_pipeline_stats_dict()
        assert stats_dict["pipeline_name"] == "测试Pipeline"
        assert stats_dict["variant"] == "variant_1"
        assert stats_dict["total_steps"] == 3
        assert stats_dict["current_sample_step"] == 1
        
        tracker.finish()


class TestConcurrentExecutorProgress:
    """测试 ConcurrentExecutor 的进度跟踪"""
    
    def test_concurrent_executor_progress_callback(self):
        """测试并发执行器的进度回调"""
        executor = ConcurrentExecutor(max_workers=2, strategy="thread")
        
        progress_updates = []
        
        def progress_callback(progress: ExecutionProgress):
            progress_updates.append({
                "completed": progress.completed,
                "total": progress.total,
                "running": progress.running
            })
        
        # 创建简单任务
        def simple_task(x):
            time.sleep(0.1)
            return x * 2
        
        tasks = [
            Task(id=f"task_{i}", func=simple_task, args=(i,))
            for i in range(5)
        ]
        
        # 执行任务
        results = executor.execute_concurrent(
            tasks=tasks,
            progress_callback=progress_callback
        )
        
        # 验证结果
        assert len(results) == 5
        assert all(r.success for r in results)
        
        # 验证进度回调被调用
        assert len(progress_updates) > 0
        
        # 验证最后一次更新显示所有任务完成
        final_update = progress_updates[-1]
        assert final_update["completed"] == 5
        assert final_update["total"] == 5
    
    def test_concurrent_executor_get_progress(self):
        """测试获取并发执行器进度"""
        executor = ConcurrentExecutor(max_workers=2, strategy="thread")
        
        # 创建任务
        def slow_task():
            time.sleep(0.5)
            return "done"
        
        tasks = [
            Task(id=f"task_{i}", func=slow_task)
            for i in range(4)
        ]
        
        # 在后台线程中执行任务
        results = []
        
        def execute_tasks():
            results.extend(executor.execute_concurrent(tasks=tasks))
        
        thread = threading.Thread(target=execute_tasks)
        thread.start()
        
        # 等待一小段时间，让任务开始执行
        time.sleep(0.1)
        
        # 查询进度
        progress = executor.get_progress()
        assert progress.total == 4
        assert progress.completed < 4  # 应该还没全部完成
        
        # 等待完成
        thread.join()
        
        # 再次查询进度
        final_progress = executor.get_progress()
        assert final_progress.completed == 4
    
    def test_concurrent_executor_get_progress_dict(self):
        """测试获取并发执行器进度字典"""
        executor = ConcurrentExecutor(max_workers=2, strategy="thread")
        
        def simple_task():
            return "done"
        
        tasks = [Task(id=f"task_{i}", func=simple_task) for i in range(3)]
        
        # 执行任务
        executor.execute_concurrent(tasks=tasks)
        
        # 获取进度字典
        progress_dict = executor.get_progress_dict()
        
        assert progress_dict["total"] == 3
        assert progress_dict["completed"] == 3
        assert progress_dict["completion_rate"] == 1.0
        assert "elapsed_time" in progress_dict
    
    def test_concurrent_executor_progress_with_dependencies(self):
        """测试带依赖关系的并发执行进度"""
        executor = ConcurrentExecutor(max_workers=2, strategy="thread")
        
        progress_updates = []
        
        def progress_callback(progress: ExecutionProgress):
            progress_updates.append(progress.completed)
        
        def simple_task(x):
            time.sleep(0.05)
            return x
        
        # 创建有依赖关系的任务
        tasks = [
            Task(id="task_1", func=simple_task, args=(1,), dependencies=[]),
            Task(id="task_2", func=simple_task, args=(2,), dependencies=[]),
            Task(id="task_3", func=simple_task, args=(3,), dependencies=["task_1"]),
            Task(id="task_4", func=simple_task, args=(4,), dependencies=["task_1", "task_2"]),
        ]
        
        # 执行任务
        results = executor.execute_with_dependencies(
            tasks=tasks,
            progress_callback=progress_callback
        )
        
        # 验证结果
        assert len(results) == 4
        assert all(r.success for r in results)
        
        # 验证进度更新
        assert len(progress_updates) > 0
        assert progress_updates[-1] == 4  # 最后应该完成4个任务


class TestProgressTrackingIntegration:
    """测试进度跟踪的集成场景"""
    
    def test_progress_tracking_with_concurrent_execution(self):
        """测试进度跟踪与并发执行的集成"""
        # 创建进度跟踪器
        tracker = ProgressTracker(task_name="并发任务", total_items=10)
        
        # 创建并发执行器
        executor = ConcurrentExecutor(max_workers=3, strategy="thread")
        
        # 定义进度回调，将并发执行进度同步到跟踪器
        def sync_progress(exec_progress: ExecutionProgress):
            tracker.update(
                completed=exec_progress.completed,
                current_item=f"任务 {exec_progress.completed}/{exec_progress.total}",
                current_step=f"运行中: {exec_progress.running}"
            )
        
        # 创建任务
        def simple_task(x):
            time.sleep(0.05)
            return x * 2
        
        tasks = [
            Task(id=f"task_{i}", func=simple_task, args=(i,))
            for i in range(10)
        ]
        
        # 开始跟踪
        tracker.start()
        
        # 执行任务
        results = executor.execute_concurrent(
            tasks=tasks,
            progress_callback=sync_progress
        )
        
        # 完成跟踪
        tracker.finish()
        
        # 验证
        assert len(results) == 10
        stats = tracker.get_stats()
        assert stats.completed_items == 10
    
    def test_multiple_progress_trackers(self):
        """测试多个进度跟踪器同时工作"""
        tracker1 = ProgressTracker(task_name="任务1", total_items=5)
        tracker2 = ProgressTracker(task_name="任务2", total_items=10)
        
        tracker1.start()
        tracker2.start()
        
        # 更新两个跟踪器
        for i in range(5):
            tracker1.update(increment=1)
            time.sleep(0.01)
        
        for i in range(10):
            tracker2.update(increment=1)
            time.sleep(0.01)
        
        # 验证两个跟踪器独立工作
        stats1 = tracker1.get_stats()
        stats2 = tracker2.get_stats()
        
        assert stats1.completed_items == 5
        assert stats2.completed_items == 10
        
        tracker1.finish()
        tracker2.finish()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
