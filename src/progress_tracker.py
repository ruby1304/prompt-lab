# src/progress_tracker.py
"""
执行进度跟踪和显示模块

提供进度条显示、预估完成时间计算和中文进度消息功能。
支持不同类型的执行任务，包括 Pipeline 执行、评估和比较等。
"""

from __future__ import annotations

import time
import threading
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from rich.console import Console
from rich.progress import Progress, TaskID, BarColumn, TextColumn, TimeRemainingColumn, SpinnerColumn
from rich.live import Live
from rich.table import Table


@dataclass
class ProgressStats:
    """进度统计信息"""
    total_items: int
    completed_items: int = 0
    failed_items: int = 0
    start_time: datetime = field(default_factory=datetime.now)
    current_item: str = ""
    current_step: str = ""
    
    @property
    def success_items(self) -> int:
        """成功完成的项目数"""
        return self.completed_items - self.failed_items
    
    @property
    def progress_percentage(self) -> float:
        """完成百分比"""
        return (self.completed_items / self.total_items * 100) if self.total_items > 0 else 0
    
    @property
    def elapsed_time(self) -> timedelta:
        """已用时间"""
        return datetime.now() - self.start_time
    
    @property
    def estimated_remaining_time(self) -> Optional[timedelta]:
        """预估剩余时间"""
        if self.completed_items == 0:
            return None
        
        elapsed_seconds = self.elapsed_time.total_seconds()
        avg_time_per_item = elapsed_seconds / self.completed_items
        remaining_items = self.total_items - self.completed_items
        
        return timedelta(seconds=avg_time_per_item * remaining_items)
    
    @property
    def estimated_completion_time(self) -> Optional[datetime]:
        """预估完成时间"""
        remaining = self.estimated_remaining_time
        if remaining is None:
            return None
        return datetime.now() + remaining


class ProgressTracker:
    """进度跟踪器"""
    
    def __init__(self, 
                 task_name: str,
                 total_items: int,
                 console: Optional[Console] = None,
                 show_spinner: bool = True,
                 show_eta: bool = True):
        """
        初始化进度跟踪器
        
        Args:
            task_name: 任务名称
            total_items: 总项目数
            console: Rich Console 实例
            show_spinner: 是否显示旋转器
            show_eta: 是否显示预估完成时间
        """
        self.task_name = task_name
        self.console = console or Console()
        self.show_spinner = show_spinner
        self.show_eta = show_eta
        
        self.stats = ProgressStats(total_items=total_items)
        self.progress: Optional[Progress] = None
        self.task_id: Optional[TaskID] = None
        self.live: Optional[Live] = None
        self._lock = threading.Lock()
        self._callbacks: list[Callable[[ProgressStats], None]] = []
        
        # 创建进度条组件
        columns = []
        if show_spinner:
            columns.append(SpinnerColumn())
        columns.extend([
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
        ])
        if show_eta:
            columns.append(TimeRemainingColumn())
        
        self.progress = Progress(*columns, console=self.console)
    
    def add_callback(self, callback: Callable[[ProgressStats], None]):
        """添加进度更新回调函数"""
        self._callbacks.append(callback)
    
    def get_stats(self) -> ProgressStats:
        """
        获取当前进度统计信息（线程安全）
        
        Returns:
            ProgressStats: 进度统计信息的副本
        """
        with self._lock:
            # 返回一个副本，避免外部修改
            return ProgressStats(
                total_items=self.stats.total_items,
                completed_items=self.stats.completed_items,
                failed_items=self.stats.failed_items,
                start_time=self.stats.start_time,
                current_item=self.stats.current_item,
                current_step=self.stats.current_step
            )
    
    def get_stats_dict(self) -> Dict[str, Any]:
        """
        获取当前进度统计信息的字典表示（用于API等场景）
        
        Returns:
            Dict[str, Any]: 进度统计信息字典
        """
        stats = self.get_stats()
        result = {
            "total_items": stats.total_items,
            "completed_items": stats.completed_items,
            "failed_items": stats.failed_items,
            "success_items": stats.success_items,
            "progress_percentage": stats.progress_percentage,
            "elapsed_time": stats.elapsed_time.total_seconds(),
            "current_item": stats.current_item,
            "current_step": stats.current_step
        }
        
        # 添加预估时间（如果可用）
        if stats.estimated_remaining_time:
            result["estimated_remaining_time"] = stats.estimated_remaining_time.total_seconds()
        if stats.estimated_completion_time:
            result["estimated_completion_time"] = stats.estimated_completion_time.isoformat()
        
        return result
    
    def start(self):
        """开始进度跟踪"""
        if self.progress is None:
            return
        
        self.progress.start()
        self.task_id = self.progress.add_task(
            description=f"正在执行 {self.task_name}",
            total=self.stats.total_items
        )
        
        # 显示初始状态
        self._update_display()
    
    def update(self, 
               completed: Optional[int] = None,
               current_item: str = "",
               current_step: str = "",
               increment: int = 1,
               failed: bool = False):
        """
        更新进度
        
        Args:
            completed: 已完成项目数（绝对值）
            current_item: 当前处理的项目名称
            current_step: 当前执行的步骤
            increment: 增量（当completed为None时使用）
            failed: 当前项目是否失败
        """
        with self._lock:
            if completed is not None:
                self.stats.completed_items = completed
            else:
                self.stats.completed_items += increment
            
            if failed:
                self.stats.failed_items += 1
            
            if current_item:
                self.stats.current_item = current_item
            
            if current_step:
                self.stats.current_step = current_step
            
            self._update_display()
            
            # 调用回调函数
            for callback in self._callbacks:
                try:
                    callback(self.stats)
                except Exception as e:
                    # 忽略回调函数中的错误，避免影响主流程
                    pass
    
    def _update_display(self):
        """更新显示"""
        if self.progress is None or self.task_id is None:
            return
        
        # 构建描述信息
        description_parts = [f"正在执行 {self.task_name}"]
        
        if self.stats.current_item:
            description_parts.append(f"当前: {self.stats.current_item}")
        
        if self.stats.current_step:
            description_parts.append(f"步骤: {self.stats.current_step}")
        
        description = " | ".join(description_parts)
        
        # 更新进度条
        self.progress.update(
            self.task_id,
            completed=self.stats.completed_items,
            description=description
        )
    
    def finish(self, success_message: str = ""):
        """完成进度跟踪"""
        if self.progress is None:
            return
        
        # 确保进度条显示100%
        if self.task_id is not None:
            self.progress.update(self.task_id, completed=self.stats.total_items)
        
        self.progress.stop()
        
        # 显示完成统计
        self._show_completion_stats(success_message)
    
    def _show_completion_stats(self, success_message: str):
        """显示完成统计信息"""
        elapsed = self.stats.elapsed_time
        success_count = self.stats.success_items
        failed_count = self.stats.failed_items
        total_count = self.stats.total_items
        
        # 创建统计表格
        stats_table = Table(title=f"{self.task_name} 执行统计", show_header=False)
        stats_table.add_column("项目", style="bold")
        stats_table.add_column("数值", justify="right")
        
        stats_table.add_row("总项目数", str(total_count))
        stats_table.add_row("成功完成", f"[green]{success_count}[/green]")
        if failed_count > 0:
            stats_table.add_row("执行失败", f"[red]{failed_count}[/red]")
        stats_table.add_row("成功率", f"{success_count/total_count*100:.1f}%" if total_count > 0 else "0%")
        stats_table.add_row("总用时", self._format_duration(elapsed))
        
        if total_count > 0:
            avg_time = elapsed.total_seconds() / total_count
            stats_table.add_row("平均用时", f"{avg_time:.1f}秒/项")
        
        self.console.print(stats_table)
        
        if success_message:
            self.console.print(f"[green]{success_message}[/green]")
    
    def _format_duration(self, duration: timedelta) -> str:
        """格式化时间间隔"""
        total_seconds = int(duration.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}小时{minutes}分{seconds}秒"
        elif minutes > 0:
            return f"{minutes}分{seconds}秒"
        else:
            return f"{seconds}秒"
    
    def __enter__(self):
        """上下文管理器入口"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        if exc_type is None:
            self.finish("执行完成！")
        else:
            self.finish("执行过程中出现错误")


class PipelineProgressTracker(ProgressTracker):
    """Pipeline 专用进度跟踪器"""
    
    def __init__(self, 
                 pipeline_name: str,
                 total_samples: int,
                 total_steps: int,
                 variant: str = "baseline",
                 console: Optional[Console] = None):
        """
        初始化 Pipeline 进度跟踪器
        
        Args:
            pipeline_name: Pipeline 名称
            total_samples: 总样本数
            total_steps: 每个样本的步骤数
            variant: 变体名称
            console: Rich Console 实例
        """
        task_name = f"Pipeline {pipeline_name} ({variant})"
        super().__init__(task_name, total_samples, console)
        
        self.pipeline_name = pipeline_name
        self.total_steps = total_steps
        self.variant = variant
        self.current_sample_step = 0
    
    def update_sample(self, 
                     sample_index: int,
                     sample_id: str,
                     step_index: int = 0,
                     step_name: str = "",
                     failed: bool = False):
        """
        更新样本处理进度
        
        Args:
            sample_index: 当前样本索引（从0开始）
            sample_id: 样本ID
            step_index: 当前步骤索引（从0开始）
            step_name: 步骤名称
            failed: 是否失败
        """
        self.current_sample_step = step_index
        
        # 构建当前项目描述
        current_item = f"样本 {sample_id} ({sample_index + 1}/{self.stats.total_items})"
        
        # 构建当前步骤描述
        if step_name:
            current_step = f"{step_name} ({step_index + 1}/{self.total_steps})"
        else:
            current_step = f"步骤 {step_index + 1}/{self.total_steps}"
        
        # 如果是样本的最后一个步骤，则认为样本完成
        completed = sample_index + (1 if step_index == self.total_steps - 1 else 0)
        
        self.update(
            completed=completed,
            current_item=current_item,
            current_step=current_step,
            failed=failed
        )
    
    def complete_sample(self, sample_index: int, sample_id: str, failed: bool = False):
        """
        完成样本处理
        
        Args:
            sample_index: 样本索引
            sample_id: 样本ID
            failed: 是否失败
        """
        current_item = f"样本 {sample_id} ({sample_index + 1}/{self.stats.total_items})"
        current_step = "完成" if not failed else "失败"
        
        self.update(
            completed=sample_index + 1,
            current_item=current_item,
            current_step=current_step,
            failed=failed
        )
    
    def get_pipeline_stats_dict(self) -> Dict[str, Any]:
        """
        获取 Pipeline 专用的进度统计信息字典
        
        Returns:
            Dict[str, Any]: Pipeline 进度统计信息字典
        """
        base_stats = self.get_stats_dict()
        base_stats.update({
            "pipeline_name": self.pipeline_name,
            "variant": self.variant,
            "total_steps": self.total_steps,
            "current_sample_step": self.current_sample_step
        })
        return base_stats


class EvaluationProgressTracker(ProgressTracker):
    """评估专用进度跟踪器"""
    
    def __init__(self,
                 eval_type: str,  # "rules", "judge", "compare"
                 total_items: int,
                 entity_name: str = "",
                 console: Optional[Console] = None):
        """
        初始化评估进度跟踪器
        
        Args:
            eval_type: 评估类型
            total_items: 总项目数
            entity_name: 实体名称（agent或pipeline）
            console: Rich Console 实例
        """
        eval_type_names = {
            "rules": "规则评估",
            "judge": "LLM评估", 
            "compare": "对比评估",
            "regression": "回归测试"
        }
        
        task_name = eval_type_names.get(eval_type, eval_type)
        if entity_name:
            task_name = f"{entity_name} {task_name}"
        
        super().__init__(task_name, total_items, console)
        self.eval_type = eval_type
        self.entity_name = entity_name


def create_simple_progress_callback(task_name: str, console: Optional[Console] = None) -> Callable:
    """
    创建简单的进度回调函数，用于与现有代码集成
    
    Args:
        task_name: 任务名称
        console: Rich Console 实例
        
    Returns:
        进度回调函数
    """
    console = console or Console()
    start_time = time.time()
    
    def progress_callback(current: int, total: int, message: str = ""):
        """进度回调函数"""
        if total == 0:
            return
        
        percentage = (current / total) * 100
        elapsed = time.time() - start_time
        
        # 计算预估剩余时间
        if current > 0:
            avg_time = elapsed / current
            remaining_time = avg_time * (total - current)
            eta_str = f"预计剩余: {remaining_time:.0f}秒"
        else:
            eta_str = "预计剩余: 计算中..."
        
        # 构建进度信息
        progress_info = f"[{current}/{total}] {percentage:.1f}%"
        if message:
            progress_info += f" | {message}"
        progress_info += f" | {eta_str}"
        
        # 使用 \r 实现同行更新
        console.print(f"\r正在执行 {task_name}: {progress_info}", end="")
        
        # 完成时换行
        if current == total:
            elapsed_str = f"{elapsed:.1f}秒"
            console.print(f"\n[green]{task_name} 执行完成！用时: {elapsed_str}[/green]")
    
    return progress_callback


def create_pipeline_progress_callback(pipeline_name: str, 
                                    variant: str = "baseline",
                                    console: Optional[Console] = None) -> Callable:
    """
    创建 Pipeline 专用的进度回调函数
    
    Args:
        pipeline_name: Pipeline 名称
        variant: 变体名称
        console: Rich Console 实例
        
    Returns:
        进度回调函数
    """
    console = console or Console()
    start_time = time.time()
    
    def progress_callback(current: int, total: int, message: str = ""):
        """Pipeline 进度回调函数"""
        if total == 0:
            return
        
        percentage = (current / total) * 100
        elapsed = time.time() - start_time
        
        # 计算预估剩余时间
        if current > 0:
            avg_time = elapsed / current
            remaining_time = avg_time * (total - current)
            eta_str = f"预计剩余: {remaining_time:.0f}秒"
        else:
            eta_str = "预计剩余: 计算中..."
        
        # 构建进度信息
        progress_info = f"[{current}/{total}] {percentage:.1f}%"
        if message:
            progress_info += f" | {message}"
        progress_info += f" | {eta_str}"
        
        # 使用 \r 实现同行更新
        console.print(f"\r正在执行 Pipeline {pipeline_name} ({variant}): {progress_info}", end="")
        
        # 完成时换行
        if current == total:
            elapsed_str = f"{elapsed:.1f}秒"
            console.print(f"\n[green]Pipeline {pipeline_name} ({variant}) 执行完成！用时: {elapsed_str}[/green]")
    
    return progress_callback


# 向后兼容的函数
def create_progress_printer(pipeline_name: str) -> Callable:
    """
    创建进度打印回调函数（向后兼容）
    
    Args:
        pipeline_name: Pipeline 名称
        
    Returns:
        进度回调函数
    """
    return create_pipeline_progress_callback(pipeline_name)