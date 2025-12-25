#!/usr/bin/env python
"""
生成并发执行性能报告

运行完整的性能测试套件并生成详细的性能报告，包括：
- 线程池规模优化建议
- 内存使用分析
- 吞吐量分析
- 最优配置推荐

Usage:
    python scripts/generate_performance_report.py [--output OUTPUT_DIR]
"""

import argparse
import json
import time
import os
import psutil
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, field, asdict
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.concurrent_executor import ConcurrentExecutor, Task


@dataclass
class PerformanceMetrics:
    """性能指标"""
    execution_time: float
    speedup: float
    throughput: float
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
    system_info: Dict[str, Any]
    metrics: List[Dict[str, Any]]
    summary: Dict[str, Any]
    recommendations: List[str]
    optimization_tips: List[str]


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_memory = 0
        self.peak_memory = 0
        self.start_cpu = 0
    
    def start(self):
        """开始监控"""
        self.start_memory = self.process.memory_info().rss / 1024 / 1024
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


def run_scaling_test(task_count: int = 20, task_duration: float = 0.1) -> List[PerformanceMetrics]:
    """运行规模测试"""
    print("\n" + "="*80)
    print("运行线程池规模测试...")
    print("="*80)
    
    worker_configs = [1, 2, 4, 8, 16]
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
            task_count=task_count,
            metadata={"test_type": "scaling"}
        )
        
        results.append(metrics)
        
        print(f"Workers: {max_workers:2d} | "
              f"Time: {execution_time:6.3f}s | "
              f"Speedup: {speedup:5.2f}x | "
              f"Throughput: {throughput:6.2f} tasks/s")
    
    return results


def run_memory_test(max_workers: int = 4) -> List[PerformanceMetrics]:
    """运行内存测试"""
    print("\n" + "="*80)
    print("运行内存使用测试...")
    print("="*80)
    
    task_counts = [10, 50, 100, 200]
    results = []
    
    for task_count in task_counts:
        monitor = PerformanceMonitor()
        monitor.start()
        
        tasks = [
            Task(
                id=f"task_{i}",
                func=dummy_task,
                kwargs={"duration": 0.05}
            )
            for i in range(task_count)
        ]
        
        executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
        
        def progress_callback(progress):
            monitor.update_peak()
        
        start_time = time.time()
        task_results = executor.execute_concurrent(tasks, progress_callback=progress_callback)
        execution_time = time.time() - start_time
        
        metrics_data = monitor.get_metrics()
        
        sequential_time = task_count * 0.05
        speedup = sequential_time / execution_time if execution_time > 0 else 0
        throughput = task_count / execution_time if execution_time > 0 else 0
        memory_per_task = (metrics_data["memory_peak_mb"] * 1024) / task_count if task_count > 0 else 0
        
        metrics = PerformanceMetrics(
            execution_time=execution_time,
            speedup=speedup,
            throughput=throughput,
            memory_usage_mb=metrics_data["memory_usage_mb"],
            memory_peak_mb=metrics_data["memory_peak_mb"],
            cpu_percent=metrics_data["cpu_percent"],
            strategy="thread",
            max_workers=max_workers,
            task_count=task_count,
            metadata={
                "test_type": "memory",
                "memory_per_task_kb": memory_per_task
            }
        )
        
        results.append(metrics)
        
        print(f"Tasks: {task_count:3d} | "
              f"Time: {execution_time:6.3f}s | "
              f"Peak Memory: {metrics_data['memory_peak_mb']:6.2f} MB | "
              f"Per Task: {memory_per_task:6.2f} KB")
    
    return results


def run_optimal_worker_test(task_count: int = 40, task_duration: float = 0.1) -> List[PerformanceMetrics]:
    """运行最优worker数量测试"""
    print("\n" + "="*80)
    print("运行最优Worker数量测试...")
    print("="*80)
    
    cpu_count = os.cpu_count() or 4
    print(f"系统CPU核心数: {cpu_count}")
    
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
        throughput = task_count / execution_time if execution_time > 0 else 0
        efficiency = speedup / max_workers if max_workers > 0 else 0
        
        metrics = PerformanceMetrics(
            execution_time=execution_time,
            speedup=speedup,
            throughput=throughput,
            memory_usage_mb=metrics_data["memory_usage_mb"],
            memory_peak_mb=metrics_data["memory_peak_mb"],
            cpu_percent=metrics_data["cpu_percent"],
            strategy="thread",
            max_workers=max_workers,
            task_count=task_count,
            metadata={
                "test_type": "optimal_worker",
                "efficiency": efficiency,
                "cpu_ratio": max_workers / cpu_count
            }
        )
        
        results.append(metrics)
        
        print(f"Workers: {max_workers:2d} ({max_workers/cpu_count:.1f}x CPU) | "
              f"Speedup: {speedup:5.2f}x | "
              f"Efficiency: {efficiency:5.2%}")
    
    return results


def generate_recommendations(all_metrics: List[PerformanceMetrics]) -> tuple[List[str], List[str]]:
    """生成推荐和优化建议"""
    recommendations = []
    optimization_tips = []
    
    cpu_count = os.cpu_count() or 4
    
    # 分析规模测试结果
    scaling_metrics = [m for m in all_metrics if m.metadata.get("test_type") == "scaling"]
    if scaling_metrics:
        best_speedup = max(m.speedup for m in scaling_metrics)
        best_config = max(scaling_metrics, key=lambda m: m.speedup)
        
        recommendations.append(
            f"最佳性能配置: {best_config.max_workers} workers，"
            f"加速比 {best_speedup:.2f}x"
        )
        
        if best_speedup < 2.0:
            optimization_tips.append("加速比较低，考虑增加max_workers或检查任务是否适合并发")
    
    # 分析内存测试结果
    memory_metrics = [m for m in all_metrics if m.metadata.get("test_type") == "memory"]
    if memory_metrics:
        max_memory = max(m.memory_peak_mb for m in memory_metrics)
        
        if max_memory > 100:
            optimization_tips.append(
                f"峰值内存使用较高 ({max_memory:.2f} MB)，"
                "考虑减少并发数或优化任务内存使用"
            )
        
        # 计算内存增长率
        if len(memory_metrics) >= 2:
            first = memory_metrics[0]
            last = memory_metrics[-1]
            memory_growth = (last.memory_peak_mb - first.memory_peak_mb) / (last.task_count - first.task_count)
            
            if memory_growth > 0.5:
                optimization_tips.append(
                    f"内存增长率较高 ({memory_growth:.4f} MB/task)，"
                    "考虑优化任务内存使用"
                )
    
    # 分析最优worker测试结果
    optimal_metrics = [m for m in all_metrics if m.metadata.get("test_type") == "optimal_worker"]
    if optimal_metrics:
        best_efficiency = max(m.metadata.get("efficiency", 0) for m in optimal_metrics)
        best_efficiency_config = max(optimal_metrics, key=lambda m: m.metadata.get("efficiency", 0))
        
        recommendations.append(
            f"最高效率配置: {best_efficiency_config.max_workers} workers，"
            f"效率 {best_efficiency:.2%}"
        )
    
    # 通用推荐
    recommendations.append(
        f"对于IO密集型任务，推荐max_workers设置为CPU核心数的1-2倍 ({cpu_count}-{cpu_count*2})"
    )
    recommendations.append(
        "对于CPU密集型任务，推荐max_workers设置为CPU核心数"
    )
    
    # 优化建议
    optimization_tips.append("使用线程池策略处理IO密集型任务")
    optimization_tips.append("复用ConcurrentExecutor实例以减少初始化开销")
    optimization_tips.append("合理设置批量大小以平衡吞吐量和内存使用")
    optimization_tips.append("监控实际工作负载并根据需要调整max_workers")
    
    return recommendations, optimization_tips


def generate_report(output_dir: Path):
    """生成完整的性能报告"""
    print("\n" + "="*80)
    print("并发执行性能测试报告生成器")
    print("="*80)
    
    # 收集系统信息
    system_info = {
        "cpu_count": os.cpu_count() or 4,
        "total_memory_gb": psutil.virtual_memory().total / (1024**3),
        "available_memory_gb": psutil.virtual_memory().available / (1024**3),
        "platform": sys.platform,
        "python_version": sys.version
    }
    
    print(f"\n系统信息:")
    print(f"  CPU核心数: {system_info['cpu_count']}")
    print(f"  总内存: {system_info['total_memory_gb']:.2f} GB")
    print(f"  可用内存: {system_info['available_memory_gb']:.2f} GB")
    
    # 运行所有测试
    all_metrics = []
    
    # 1. 规模测试
    all_metrics.extend(run_scaling_test())
    
    # 2. 内存测试
    all_metrics.extend(run_memory_test())
    
    # 3. 最优worker测试
    all_metrics.extend(run_optimal_worker_test())
    
    # 生成摘要
    summary = {
        "total_tests": len(all_metrics),
        "average_speedup": sum(m.speedup for m in all_metrics) / len(all_metrics),
        "best_speedup": max(m.speedup for m in all_metrics),
        "average_throughput": sum(m.throughput for m in all_metrics) / len(all_metrics),
        "max_throughput": max(m.throughput for m in all_metrics),
        "total_memory_peak_mb": max(m.memory_peak_mb for m in all_metrics),
        "average_memory_peak_mb": sum(m.memory_peak_mb for m in all_metrics) / len(all_metrics)
    }
    
    # 生成推荐
    recommendations, optimization_tips = generate_recommendations(all_metrics)
    
    # 创建报告
    report = PerformanceReport(
        test_name="Concurrent Executor Performance Test",
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        system_info=system_info,
        metrics=[asdict(m) for m in all_metrics],
        summary=summary,
        recommendations=recommendations,
        optimization_tips=optimization_tips
    )
    
    # 保存报告
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / f"performance_report_{time.strftime('%Y%m%d_%H%M%S')}.json"
    
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False)
    
    # 打印摘要
    print("\n" + "="*80)
    print("性能测试摘要")
    print("="*80)
    print(f"总测试数: {summary['total_tests']}")
    print(f"平均加速比: {summary['average_speedup']:.2f}x")
    print(f"最佳加速比: {summary['best_speedup']:.2f}x")
    print(f"平均吞吐量: {summary['average_throughput']:.2f} tasks/s")
    print(f"最大吞吐量: {summary['max_throughput']:.2f} tasks/s")
    print(f"峰值内存: {summary['total_memory_peak_mb']:.2f} MB")
    print(f"平均峰值内存: {summary['average_memory_peak_mb']:.2f} MB")
    
    print("\n推荐配置:")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")
    
    print("\n优化建议:")
    for i, tip in enumerate(optimization_tips, 1):
        print(f"  {i}. {tip}")
    
    print(f"\n完整报告已保存到: {report_path}")
    print("="*80)
    
    return report


def main():
    parser = argparse.ArgumentParser(description="生成并发执行性能报告")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/performance_reports"),
        help="输出目录 (默认: data/performance_reports)"
    )
    
    args = parser.parse_args()
    
    try:
        report = generate_report(args.output)
        print("\n✓ 性能报告生成成功!")
        return 0
    except Exception as e:
        print(f"\n✗ 性能报告生成失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
