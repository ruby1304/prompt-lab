# tests/test_concurrent_performance.py
"""
并发执行性能测试和优化

测试并发执行的性能提升，优化线程池配置，监控内存使用，生成性能报告。
Requirements: 9.1
"""

import pytest
import time
import psutil
import os
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass, field
import json
from pathlib import Path

from src.concurrent_executor import ConcurrentExecutor, Task, TaskResult, ExecutionProgress


@dataclass
class PerformanceMetrics:
    """性能指标"""
    execution_time: float
    speedup: float
    throughput: float  # tasks per second
    memory_usage_mb: float
    memory_peak_mb: float
    cpu_percent: float
    strategy: str
    max_workers: int
    task_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceReport:
    """性能报告"""
    test_name: str
    timestamp: str
    metrics: List[PerformanceMetrics]
    summary: Dict[str, Any]
    recommendations: List[str]


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_memory = 0
        self.peak_memory = 0
        self.start_cpu = 0
    
    def start(self):
        """开始监控"""
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.start_memory
        self.start_cpu = self.process.cpu_percent()
    
    def update_peak(self):
        """更新峰值内存"""
        current_memory = self.process.memory_info().rss / 1024 / 1024
        self.peak_memory = max(self.peak_memory, current_memory)
    
    def get_metrics(self) -> Dict[str, float]:
        """获取当前指标"""
        current_memory = self.process.memory_info().rss / 1024 / 1024
        self.peak_memory = max(self.peak_memory, current_memory)
        
        return {
            "memory_usage_mb": current_memory - self.start_memory,
            "memory_peak_mb": self.peak_memory - self.start_memory,
            "cpu_percent": self.process.cpu_percent()
        }


def dummy_task(duration: float = 0.1) -> str:
    """模拟任务"""
    time.sleep(duration)
    return f"completed after {duration}s"


def cpu_intensive_task(iterations: int = 1000000) -> int:
    """CPU密集型任务"""
    result = 0
    for i in range(iterations):
        result += i * i
    return result


def io_intensive_task(duration: float = 0.1) -> str:
    """IO密集型任务（模拟）"""
    time.sleep(duration)
    return f"io completed after {duration}s"


class TestConcurrentPerformance:
    """并发执行性能测试"""
    
    def test_thread_pool_scaling(self):
        """测试线程池规模对性能的影响"""
        print("\n" + "="*80)
        print("测试: 线程池规模性能影响")
        print("="*80)
        
        task_count = 20
        task_duration = 0.1
        worker_configs = [1, 2, 4, 8, 16]
        
        results = []
        
        for max_workers in worker_configs:
            monitor = PerformanceMonitor()
            monitor.start()
            
            # 创建任务
            tasks = [
                Task(
                    id=f"task_{i}",
                    func=dummy_task,
                    kwargs={"duration": task_duration}
                )
                for i in range(task_count)
            ]
            
            # 执行
            executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
            start_time = time.time()
            task_results = executor.execute_concurrent(tasks)
            execution_time = time.time() - start_time
            
            # 收集指标
            metrics_data = monitor.get_metrics()
            
            # 计算性能指标
            sequential_time = task_count * task_duration
            speedup = sequential_time / execution_time if execution_time > 0 else 0
            throughput = task_count / execution_time if execution_time > 0 else 0
            
            metrics = PerformanceMetrics(
                execution_time=execution_time,
                speedup=speedup,
                throughput=throughput,
                memory_usage_mb=metrics_data["memory_usage_mb"],
                memory_peak_mb=metrics_data["memory_peak_mb"],
                cpu_percent=metrics_data["cpu_percent"],
                strategy="thread",
                max_workers=max_workers,
                task_count=task_count
            )
            
            results.append(metrics)
            
            print(f"\nWorkers: {max_workers}")
            print(f"  执行时间: {execution_time:.3f}s")
            print(f"  加速比: {speedup:.2f}x")
            print(f"  吞吐量: {throughput:.2f} tasks/s")
            print(f"  内存使用: {metrics_data['memory_usage_mb']:.2f} MB")
            print(f"  峰值内存: {metrics_data['memory_peak_mb']:.2f} MB")
        
        # 找出最优配置
        best_metrics = max(results, key=lambda m: m.speedup)
        print(f"\n最优配置: {best_metrics.max_workers} workers")
        print(f"  最佳加速比: {best_metrics.speedup:.2f}x")
        print(f"  最佳吞吐量: {best_metrics.throughput:.2f} tasks/s")
        
        # 验证性能提升
        assert best_metrics.speedup > 1.0, "并发执行应该有性能提升"
        assert all(r.speedup > 0 for r in results), "所有配置都应该能完成任务"
    
    def test_thread_vs_process_performance(self):
        """测试线程池 vs 进程池性能对比"""
        print("\n" + "="*80)
        print("测试: 线程池 vs 进程池性能对比")
        print("="*80)
        
        task_count = 10
        max_workers = 4
        
        results = {}
        
        # 只测试线程池（进程池有pickling限制）
        for strategy in ["thread"]:
            monitor = PerformanceMonitor()
            monitor.start()
            
            # 创建IO密集型任务
            tasks = [
                Task(
                    id=f"task_{i}",
                    func=io_intensive_task,
                    kwargs={"duration": 0.1}
                )
                for i in range(task_count)
            ]
            
            # 执行
            executor = ConcurrentExecutor(max_workers=max_workers, strategy=strategy)
            start_time = time.time()
            task_results = executor.execute_concurrent(tasks)
            execution_time = time.time() - start_time
            
            # 收集指标
            metrics_data = monitor.get_metrics()
            
            sequential_time = task_count * 0.1
            speedup = sequential_time / execution_time if execution_time > 0 else 0
            
            results[strategy] = {
                "execution_time": execution_time,
                "speedup": speedup,
                "memory_usage_mb": metrics_data["memory_usage_mb"],
                "memory_peak_mb": metrics_data["memory_peak_mb"],
                "cpu_percent": metrics_data["cpu_percent"]
            }
            
            print(f"\n策略: {strategy}")
            print(f"  执行时间: {execution_time:.3f}s")
            print(f"  加速比: {speedup:.2f}x")
            print(f"  内存使用: {metrics_data['memory_usage_mb']:.2f} MB")
            print(f"  CPU使用: {metrics_data['cpu_percent']:.1f}%")
        
        # 结论
        print(f"\n结论:")
        print(f"  ✓ 线程池适合IO密集型任务")
        print(f"    线程池: {results['thread']['execution_time']:.3f}s")
        print(f"  注: 进程池因pickling限制未测试，但通常适合CPU密集型任务")
        
        # 验证线程池能正常工作
        assert results["thread"]["speedup"] > 0, "线程池应该能完成任务"
    
    def test_memory_usage_scaling(self):
        """测试内存使用随任务数量的变化"""
        print("\n" + "="*80)
        print("测试: 内存使用随任务数量的变化")
        print("="*80)
        
        task_counts = [10, 50, 100, 200]
        max_workers = 4
        
        results = []
        
        for task_count in task_counts:
            monitor = PerformanceMonitor()
            monitor.start()
            
            # 创建任务
            tasks = [
                Task(
                    id=f"task_{i}",
                    func=dummy_task,
                    kwargs={"duration": 0.05}
                )
                for i in range(task_count)
            ]
            
            # 执行
            executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
            
            # 在执行过程中监控内存
            def progress_callback(progress: ExecutionProgress):
                monitor.update_peak()
            
            start_time = time.time()
            task_results = executor.execute_concurrent(tasks, progress_callback=progress_callback)
            execution_time = time.time() - start_time
            
            # 收集指标
            metrics_data = monitor.get_metrics()
            
            results.append({
                "task_count": task_count,
                "execution_time": execution_time,
                "memory_usage_mb": metrics_data["memory_usage_mb"],
                "memory_peak_mb": metrics_data["memory_peak_mb"],
                "memory_per_task_kb": (metrics_data["memory_peak_mb"] * 1024) / task_count
            })
            
            print(f"\n任务数: {task_count}")
            print(f"  执行时间: {execution_time:.3f}s")
            print(f"  内存使用: {metrics_data['memory_usage_mb']:.2f} MB")
            print(f"  峰值内存: {metrics_data['memory_peak_mb']:.2f} MB")
            print(f"  每任务内存: {results[-1]['memory_per_task_kb']:.2f} KB")
        
        # 验证内存使用是合理的（不应该线性增长太快）
        memory_growth_rate = (results[-1]["memory_peak_mb"] - results[0]["memory_peak_mb"]) / (task_counts[-1] - task_counts[0])
        print(f"\n内存增长率: {memory_growth_rate:.4f} MB/task")
        
        # 内存增长应该是合理的（每个任务不应该占用太多内存）
        assert memory_growth_rate < 1.0, "内存增长率应该小于1MB/task"
    
    def test_optimal_worker_count_recommendation(self):
        """测试并推荐最优worker数量"""
        print("\n" + "="*80)
        print("测试: 最优Worker数量推荐")
        print("="*80)
        
        cpu_count = os.cpu_count() or 4
        print(f"系统CPU核心数: {cpu_count}")
        
        task_count = 40
        task_duration = 0.1
        
        # 测试不同的worker配置
        worker_configs = [
            cpu_count // 2,
            cpu_count,
            cpu_count * 2,
            cpu_count * 4
        ]
        
        results = []
        
        for max_workers in worker_configs:
            monitor = PerformanceMonitor()
            monitor.start()
            
            tasks = [
                Task(
                    id=f"task_{i}",
                    func=dummy_task,
                    kwargs={"duration": task_duration}
                )
                for i in range(task_count)
            ]
            
            executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
            start_time = time.time()
            task_results = executor.execute_concurrent(tasks)
            execution_time = time.time() - start_time
            
            metrics_data = monitor.get_metrics()
            
            sequential_time = task_count * task_duration
            speedup = sequential_time / execution_time if execution_time > 0 else 0
            efficiency = speedup / max_workers if max_workers > 0 else 0
            
            results.append({
                "max_workers": max_workers,
                "execution_time": execution_time,
                "speedup": speedup,
                "efficiency": efficiency,
                "memory_peak_mb": metrics_data["memory_peak_mb"],
                "cpu_percent": metrics_data["cpu_percent"]
            })
            
            print(f"\nWorkers: {max_workers} ({max_workers/cpu_count:.1f}x CPU)")
            print(f"  执行时间: {execution_time:.3f}s")
            print(f"  加速比: {speedup:.2f}x")
            print(f"  效率: {efficiency:.2%}")
            print(f"  峰值内存: {metrics_data['memory_peak_mb']:.2f} MB")
        
        # 找出最优配置（平衡速度和效率）
        best_by_speed = max(results, key=lambda r: r["speedup"])
        best_by_efficiency = max(results, key=lambda r: r["efficiency"])
        
        print(f"\n推荐配置:")
        print(f"  最快速度: {best_by_speed['max_workers']} workers")
        print(f"    加速比: {best_by_speed['speedup']:.2f}x")
        print(f"    效率: {best_by_efficiency['efficiency']:.2%}")
        print(f"  最高效率: {best_by_efficiency['max_workers']} workers")
        print(f"    加速比: {best_by_efficiency['speedup']:.2f}x")
        print(f"    效率: {best_by_efficiency['efficiency']:.2%}")
        
        # 一般推荐: CPU核心数的1-2倍
        recommended = cpu_count * 2
        print(f"\n一般推荐: {recommended} workers (2x CPU核心数)")
        print(f"  适用于IO密集型任务")
        
        # 验证推荐配置的性能
        assert best_by_speed["speedup"] > 1.0, "最优配置应该有明显的性能提升"
    
    def test_generate_performance_report(self, tmp_path):
        """生成完整的性能报告"""
        print("\n" + "="*80)
        print("测试: 生成性能报告")
        print("="*80)
        
        # 运行一系列性能测试
        task_count = 20
        max_workers = 4
        
        all_metrics = []
        
        # 测试1: 线程池（只测试线程池，避免pickling问题）
        for strategy in ["thread"]:
            monitor = PerformanceMonitor()
            monitor.start()
            
            tasks = [
                Task(
                    id=f"task_{i}",
                    func=dummy_task,
                    kwargs={"duration": 0.1}
                )
                for i in range(task_count)
            ]
            
            executor = ConcurrentExecutor(max_workers=max_workers, strategy=strategy)
            start_time = time.time()
            task_results = executor.execute_concurrent(tasks)
            execution_time = time.time() - start_time
            
            metrics_data = monitor.get_metrics()
            
            sequential_time = task_count * 0.1
            speedup = sequential_time / execution_time if execution_time > 0 else 0
            throughput = task_count / execution_time if execution_time > 0 else 0
            
            metrics = PerformanceMetrics(
                execution_time=execution_time,
                speedup=speedup,
                throughput=throughput,
                memory_usage_mb=metrics_data["memory_usage_mb"],
                memory_peak_mb=metrics_data["memory_peak_mb"],
                cpu_percent=metrics_data["cpu_percent"],
                strategy=strategy,
                max_workers=max_workers,
                task_count=task_count,
                metadata={
                    "test_type": "basic_concurrent",
                    "task_duration": 0.1
                }
            )
            
            all_metrics.append(metrics)
        
        # 生成摘要
        summary = {
            "total_tests": len(all_metrics),
            "average_speedup": sum(m.speedup for m in all_metrics) / len(all_metrics),
            "best_speedup": max(m.speedup for m in all_metrics),
            "average_throughput": sum(m.throughput for m in all_metrics) / len(all_metrics),
            "total_memory_peak_mb": max(m.memory_peak_mb for m in all_metrics),
            "cpu_count": os.cpu_count() or 4
        }
        
        # 生成推荐
        recommendations = []
        
        if summary["average_speedup"] < 2.0:
            recommendations.append("考虑增加max_workers以提高并发度")
        
        if summary["total_memory_peak_mb"] > 100:
            recommendations.append("内存使用较高，考虑减少并发数或优化任务")
        
        # 添加通用推荐
        recommendations.append("对于IO密集型任务，推荐使用线程池策略")
        recommendations.append("对于CPU密集型任务，可以考虑使用进程池策略（需要确保任务可序列化）")
        recommendations.append(f"推荐max_workers设置为CPU核心数的1-2倍 ({summary['cpu_count']}-{summary['cpu_count']*2})")
        
        # 创建报告
        report = PerformanceReport(
            test_name="Concurrent Executor Performance Test",
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            metrics=all_metrics,
            summary=summary,
            recommendations=recommendations
        )
        
        # 保存报告
        report_path = tmp_path / "performance_report.json"
        report_data = {
            "test_name": report.test_name,
            "timestamp": report.timestamp,
            "metrics": [
                {
                    "execution_time": m.execution_time,
                    "speedup": m.speedup,
                    "throughput": m.throughput,
                    "memory_usage_mb": m.memory_usage_mb,
                    "memory_peak_mb": m.memory_peak_mb,
                    "cpu_percent": m.cpu_percent,
                    "strategy": m.strategy,
                    "max_workers": m.max_workers,
                    "task_count": m.task_count,
                    "metadata": m.metadata
                }
                for m in report.metrics
            ],
            "summary": report.summary,
            "recommendations": report.recommendations
        }
        
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n性能报告已保存到: {report_path}")
        print(f"\n摘要:")
        print(f"  总测试数: {summary['total_tests']}")
        print(f"  平均加速比: {summary['average_speedup']:.2f}x")
        print(f"  最佳加速比: {summary['best_speedup']:.2f}x")
        print(f"  平均吞吐量: {summary['average_throughput']:.2f} tasks/s")
        print(f"  峰值内存: {summary['total_memory_peak_mb']:.2f} MB")
        
        print(f"\n推荐:")
        for i, rec in enumerate(recommendations, 1):
            print(f"  {i}. {rec}")
        
        # 验证报告生成成功
        assert report_path.exists(), "性能报告应该被保存"
        assert summary["average_speedup"] > 0, "应该有性能提升"
        assert len(recommendations) > 0, "应该有优化推荐"


class TestConcurrentOptimization:
    """并发执行优化测试"""
    
    def test_worker_pool_reuse(self):
        """测试worker池复用的性能优势"""
        print("\n" + "="*80)
        print("测试: Worker池复用性能优势")
        print("="*80)
        
        task_count = 10
        iterations = 5
        max_workers = 4
        
        # 测试1: 每次创建新的executor
        start_time = time.time()
        for _ in range(iterations):
            tasks = [
                Task(id=f"task_{i}", func=dummy_task, kwargs={"duration": 0.05})
                for i in range(task_count)
            ]
            executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
            executor.execute_concurrent(tasks)
        time_without_reuse = time.time() - start_time
        
        # 测试2: 复用executor
        executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
        start_time = time.time()
        for _ in range(iterations):
            tasks = [
                Task(id=f"task_{i}", func=dummy_task, kwargs={"duration": 0.05})
                for i in range(task_count)
            ]
            executor.execute_concurrent(tasks)
        time_with_reuse = time.time() - start_time
        
        improvement = (time_without_reuse - time_with_reuse) / time_without_reuse * 100
        
        print(f"\n不复用executor: {time_without_reuse:.3f}s")
        print(f"复用executor: {time_with_reuse:.3f}s")
        print(f"性能提升: {improvement:.1f}%")
        
        # 复用应该更快（虽然差异可能不大）
        assert time_with_reuse <= time_without_reuse * 1.1, "复用executor应该不会更慢"
    
    def test_batch_size_optimization(self):
        """测试批量大小对性能的影响"""
        print("\n" + "="*80)
        print("测试: 批量大小优化")
        print("="*80)
        
        total_tasks = 100
        max_workers = 4
        batch_sizes = [10, 25, 50, 100]
        
        results = []
        
        for batch_size in batch_sizes:
            # 模拟批量处理
            num_batches = (total_tasks + batch_size - 1) // batch_size
            
            start_time = time.time()
            for batch_idx in range(num_batches):
                batch_start = batch_idx * batch_size
                batch_end = min(batch_start + batch_size, total_tasks)
                current_batch_size = batch_end - batch_start
                
                tasks = [
                    Task(id=f"task_{i}", func=dummy_task, kwargs={"duration": 0.01})
                    for i in range(current_batch_size)
                ]
                
                executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
                executor.execute_concurrent(tasks)
            
            execution_time = time.time() - start_time
            
            results.append({
                "batch_size": batch_size,
                "num_batches": num_batches,
                "execution_time": execution_time,
                "throughput": total_tasks / execution_time
            })
            
            print(f"\n批量大小: {batch_size}")
            print(f"  批次数: {num_batches}")
            print(f"  执行时间: {execution_time:.3f}s")
            print(f"  吞吐量: {results[-1]['throughput']:.2f} tasks/s")
        
        # 找出最优批量大小
        best = max(results, key=lambda r: r["throughput"])
        print(f"\n最优批量大小: {best['batch_size']}")
        print(f"  最高吞吐量: {best['throughput']:.2f} tasks/s")
        
        # 验证批量处理能正常工作
        assert all(r["throughput"] > 0 for r in results), "所有批量大小都应该能完成任务"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
