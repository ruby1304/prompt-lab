# src/concurrent_executor.py
"""
并发执行器 - 支持多任务并发执行

提供线程池和进程池管理，支持任务队列、结果收集和进度跟踪。
用于提高 Pipeline 和测试执行的性能。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable, Set
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, Future, as_completed
from collections import defaultdict, deque
import time
import threading
from enum import Enum


class ExecutionStrategy(Enum):
    """执行策略"""
    THREAD = "thread"  # 线程池
    PROCESS = "process"  # 进程池


@dataclass
class ErrorSummary:
    """
    错误汇总信息
    
    Attributes:
        total_errors: 总错误数
        failed_tasks: 失败的任务列表
        skipped_tasks: 跳过的任务列表
        error_types: 错误类型统计
        critical_errors: 关键错误（必需任务失败）
    """
    total_errors: int = 0
    failed_tasks: List[str] = field(default_factory=list)
    skipped_tasks: List[str] = field(default_factory=list)
    error_types: Dict[str, int] = field(default_factory=dict)
    critical_errors: List[str] = field(default_factory=list)
    
    def add_error(self, task_id: str, error_type: str, is_critical: bool = False) -> None:
        """添加错误记录"""
        self.total_errors += 1
        self.failed_tasks.append(task_id)
        
        if error_type not in self.error_types:
            self.error_types[error_type] = 0
        self.error_types[error_type] += 1
        
        if is_critical:
            self.critical_errors.append(task_id)
    
    def add_skipped(self, task_id: str) -> None:
        """添加跳过的任务"""
        self.skipped_tasks.append(task_id)
    
    def has_critical_errors(self) -> bool:
        """是否有关键错误"""
        return len(self.critical_errors) > 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_errors": self.total_errors,
            "failed_tasks": self.failed_tasks,
            "skipped_tasks": self.skipped_tasks,
            "error_types": self.error_types,
            "critical_errors": self.critical_errors,
            "has_critical_errors": self.has_critical_errors()
        }


@dataclass
class ExecutionSummary:
    """
    执行汇总信息
    
    包含进度信息和错误汇总，提供完整的执行状态视图。
    
    Attributes:
        progress: 执行进度
        errors: 错误汇总
        results: 任务结果列表
    """
    progress: ExecutionProgress
    errors: ErrorSummary
    results: List[TaskResult] = field(default_factory=list)
    
    def is_successful(self) -> bool:
        """执行是否成功（没有关键错误）"""
        return not self.errors.has_critical_errors()
    
    def get_failed_results(self) -> List[TaskResult]:
        """获取所有失败的任务结果"""
        return [r for r in self.results if not r.success and not r.skipped]
    
    def get_skipped_results(self) -> List[TaskResult]:
        """获取所有跳过的任务结果"""
        return [r for r in self.results if r.skipped]
    
    def get_successful_results(self) -> List[TaskResult]:
        """获取所有成功的任务结果"""
        return [r for r in self.results if r.success]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "progress": {
                "total": self.progress.total,
                "completed": self.progress.completed,
                "failed": self.progress.failed,
                "skipped": self.progress.skipped,
                "success_rate": self.progress.success_rate,
                "elapsed_time": self.progress.elapsed_time
            },
            "errors": self.errors.to_dict(),
            "is_successful": self.is_successful(),
            "failed_count": len(self.get_failed_results()),
            "skipped_count": len(self.get_skipped_results()),
            "successful_count": len(self.get_successful_results())
        }


@dataclass
class Task:
    """
    任务定义
    
    Attributes:
        id: 任务唯一标识
        func: 要执行的函数
        args: 位置参数
        kwargs: 关键字参数
        dependencies: 依赖的任务ID列表
        required: 是否必需（失败时是否继续）
        metadata: 任务元数据
    """
    id: str
    func: Callable
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    required: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskResult:
    """
    任务执行结果
    
    Attributes:
        task_id: 任务ID
        success: 是否成功
        result: 执行结果
        error: 错误信息
        execution_time: 执行时间（秒）
        metadata: 结果元数据
        skipped: 是否被跳过（因为依赖失败）
        error_type: 错误类型（如果失败）
    """
    task_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    skipped: bool = False
    error_type: Optional[str] = None


@dataclass
class ExecutionProgress:
    """
    执行进度信息
    
    Attributes:
        total: 总任务数
        completed: 已完成任务数
        failed: 失败任务数
        running: 正在运行的任务数
        pending: 待执行任务数
        skipped: 跳过的任务数
        start_time: 开始时间
        current_time: 当前时间
    """
    total: int
    completed: int
    failed: int
    running: int
    pending: int
    skipped: int = 0
    start_time: float = 0.0
    current_time: float = 0.0
    
    @property
    def elapsed_time(self) -> float:
        """已用时间（秒）"""
        return self.current_time - self.start_time
    
    @property
    def completion_rate(self) -> float:
        """完成率（0-1）"""
        if self.total == 0:
            return 1.0
        return self.completed / self.total
    
    @property
    def estimated_remaining_time(self) -> Optional[float]:
        """预计剩余时间（秒）"""
        if self.completed == 0:
            return None
        avg_time_per_task = self.elapsed_time / self.completed
        return avg_time_per_task * (self.total - self.completed)
    
    @property
    def success_rate(self) -> float:
        """成功率（0-1）"""
        if self.completed == 0:
            return 0.0
        successful = self.completed - self.failed
        return successful / self.completed


class ConcurrentExecutor:
    """
    并发执行器
    
    支持线程池和进程池两种执行策略，提供任务队列管理、
    结果收集和进度跟踪功能。
    """
    
    def __init__(
        self, 
        max_workers: int = 4, 
        strategy: str = "thread"
    ):
        """
        初始化并发执行器
        
        Args:
            max_workers: 最大并发工作线程/进程数
            strategy: 执行策略，"thread" 或 "process"
            
        Raises:
            ValueError: 如果 strategy 不是 "thread" 或 "process"
        """
        if strategy not in ["thread", "process"]:
            raise ValueError(f"不支持的执行策略: {strategy}，必须是 'thread' 或 'process'")
        
        self.max_workers = max_workers
        self.strategy = ExecutionStrategy(strategy)
        
        # 进度跟踪
        self._lock = threading.Lock()
        self._progress = ExecutionProgress(
            total=0,
            completed=0,
            failed=0,
            running=0,
            pending=0,
            skipped=0,
            start_time=0.0,
            current_time=0.0
        )
        
        # 错误跟踪
        self._error_summary = ErrorSummary()
    
    def execute_concurrent(
        self,
        tasks: List[Task],
        progress_callback: Optional[Callable[[ExecutionProgress], None]] = None
    ) -> List[TaskResult]:
        """
        并发执行任务列表（无依赖关系）
        
        所有任务将尽可能并发执行，受 max_workers 限制。
        
        Args:
            tasks: 任务列表
            progress_callback: 进度回调函数，接收 ExecutionProgress 对象
            
        Returns:
            List[TaskResult]: 任务结果列表，顺序与输入任务列表一致
        """
        if not tasks:
            return []
        
        # 初始化进度和错误跟踪
        with self._lock:
            self._progress = ExecutionProgress(
                total=len(tasks),
                completed=0,
                failed=0,
                running=0,
                pending=len(tasks),
                skipped=0,
                start_time=time.time(),
                current_time=time.time()
            )
            self._error_summary = ErrorSummary()
        
        # 创建执行器
        executor_class = ThreadPoolExecutor if self.strategy == ExecutionStrategy.THREAD else ProcessPoolExecutor
        
        # 任务ID到索引的映射（用于保持顺序）
        task_id_to_index = {task.id: i for i, task in enumerate(tasks)}
        results = [None] * len(tasks)
        
        with executor_class(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_task: Dict[Future, Task] = {}
            
            for task in tasks:
                future = executor.submit(self._execute_task, task)
                future_to_task[future] = task
            
            # 更新进度
            with self._lock:
                self._progress.running = len(future_to_task)
                self._progress.pending = 0
                self._progress.current_time = time.time()
            
            if progress_callback:
                progress_callback(self._get_progress_snapshot())
            
            # 收集结果
            for future in as_completed(future_to_task):
                task = future_to_task[future]
                task_result = future.result()
                
                # 将结果放到正确的位置
                index = task_id_to_index[task.id]
                results[index] = task_result
                
                # 更新进度和错误跟踪
                with self._lock:
                    self._progress.completed += 1
                    self._progress.running -= 1
                    if not task_result.success:
                        self._progress.failed += 1
                        # 记录错误
                        error_type = task_result.error_type or "UnknownError"
                        self._error_summary.add_error(
                            task.id, 
                            error_type, 
                            is_critical=task.required
                        )
                    self._progress.current_time = time.time()
                
                if progress_callback:
                    progress_callback(self._get_progress_snapshot())
        
        return results
    
    def execute_with_dependencies(
        self,
        tasks: List[Task],
        dependency_graph: Optional[Dict[str, List[str]]] = None,
        progress_callback: Optional[Callable[[ExecutionProgress], None]] = None
    ) -> List[TaskResult]:
        """
        根据依赖关系并发执行任务
        
        任务将按照依赖关系分批执行，同一批次内的任务并发执行。
        
        Args:
            tasks: 任务列表
            dependency_graph: 依赖图，格式为 {task_id: [dependency_task_ids]}
                            如果为 None，将从 Task.dependencies 构建
            progress_callback: 进度回调函数
            
        Returns:
            List[TaskResult]: 任务结果列表，顺序与输入任务列表一致
            
        Raises:
            ValueError: 如果检测到循环依赖或依赖的任务不存在
        """
        if not tasks:
            return []
        
        # 构建依赖图
        if dependency_graph is None:
            dependency_graph = {task.id: task.dependencies for task in tasks}
        
        # 验证依赖图
        task_ids = {task.id for task in tasks}
        for task_id, deps in dependency_graph.items():
            for dep in deps:
                if dep not in task_ids:
                    raise ValueError(f"任务 {task_id} 依赖的任务 {dep} 不存在")
        
        # 检测循环依赖
        self._detect_cycles(dependency_graph, task_ids)
        
        # 初始化进度和错误跟踪
        with self._lock:
            self._progress = ExecutionProgress(
                total=len(tasks),
                completed=0,
                failed=0,
                running=0,
                pending=len(tasks),
                skipped=0,
                start_time=time.time(),
                current_time=time.time()
            )
            self._error_summary = ErrorSummary()
        
        # 任务ID到任务对象的映射
        task_map = {task.id: task for task in tasks}
        
        # 任务ID到索引的映射（用于保持顺序）
        task_id_to_index = {task.id: i for i, task in enumerate(tasks)}
        results = [None] * len(tasks)
        
        # 已完成的任务ID集合
        completed_tasks: Set[str] = set()
        failed_tasks: Set[str] = set()
        
        # 创建执行器
        executor_class = ThreadPoolExecutor if self.strategy == ExecutionStrategy.THREAD else ProcessPoolExecutor
        
        with executor_class(max_workers=self.max_workers) as executor:
            # 待执行的任务队列
            remaining_tasks = set(task_ids)
            
            while remaining_tasks:
                # 找出所有依赖已满足的任务
                ready_tasks = []
                skipped_tasks = []
                
                for task_id in remaining_tasks:
                    deps = dependency_graph.get(task_id, [])
                    # 检查所有依赖是否已完成
                    if all(dep in completed_tasks for dep in deps):
                        # 检查是否有必需的依赖失败了
                        required_deps_failed = any(
                            dep in failed_tasks and task_map[dep].required
                            for dep in deps
                        )
                        if not required_deps_failed:
                            ready_tasks.append(task_map[task_id])
                        else:
                            # 跳过这个任务（因为必需的依赖失败了）
                            skipped_tasks.append(task_id)
                
                # 处理跳过的任务
                for task_id in skipped_tasks:
                    task = task_map[task_id]
                    task_result = TaskResult(
                        task_id=task_id,
                        success=False,
                        error="必需的依赖任务失败",
                        execution_time=0.0,
                        skipped=True,
                        error_type="DependencyFailure"
                    )
                    index = task_id_to_index[task_id]
                    results[index] = task_result
                    remaining_tasks.remove(task_id)
                    failed_tasks.add(task_id)
                    completed_tasks.add(task_id)  # 标记为已完成（虽然失败了）
                    
                    with self._lock:
                        self._progress.completed += 1
                        self._progress.failed += 1
                        self._progress.skipped += 1
                        self._progress.pending -= 1
                        self._progress.current_time = time.time()
                        # 记录跳过的任务
                        self._error_summary.add_skipped(task_id)
                        # 如果是必需任务，也记录为关键错误
                        if task.required:
                            self._error_summary.add_error(
                                task_id,
                                "DependencyFailure",
                                is_critical=True
                            )
                    
                    if progress_callback:
                        progress_callback(self._get_progress_snapshot())
                
                # 如果有跳过的任务，继续下一轮循环
                if skipped_tasks:
                    continue
                
                if not ready_tasks:
                    if remaining_tasks:
                        # 如果还有任务但没有就绪的任务，说明存在问题
                        raise ValueError(f"无法执行剩余任务，可能存在循环依赖或所有依赖都失败了: {remaining_tasks}")
                    break
                
                # 并发执行就绪的任务
                future_to_task: Dict[Future, Task] = {}
                
                for task in ready_tasks:
                    future = executor.submit(self._execute_task, task)
                    future_to_task[future] = task
                    remaining_tasks.remove(task.id)
                
                # 更新进度
                with self._lock:
                    self._progress.running = len(future_to_task)
                    self._progress.pending = len(remaining_tasks)
                    self._progress.current_time = time.time()
                
                if progress_callback:
                    progress_callback(self._get_progress_snapshot())
                
                # 等待当前批次完成
                for future in as_completed(future_to_task):
                    task = future_to_task[future]
                    task_result = future.result()
                    
                    # 将结果放到正确的位置
                    index = task_id_to_index[task.id]
                    results[index] = task_result
                    
                    # 更新完成状态
                    completed_tasks.add(task.id)  # 无论成功失败都标记为已完成
                    if not task_result.success:
                        failed_tasks.add(task.id)
                    
                    # 更新进度和错误跟踪
                    with self._lock:
                        self._progress.completed += 1
                        self._progress.running -= 1
                        if not task_result.success:
                            self._progress.failed += 1
                            # 记录错误
                            error_type = task_result.error_type or "UnknownError"
                            self._error_summary.add_error(
                                task.id,
                                error_type,
                                is_critical=task.required
                            )
                        self._progress.current_time = time.time()
                    
                    if progress_callback:
                        progress_callback(self._get_progress_snapshot())
        
        return results
    
    def get_progress(self) -> ExecutionProgress:
        """
        获取当前执行进度（线程安全）
        
        Returns:
            ExecutionProgress: 进度信息快照
        """
        return self._get_progress_snapshot()
    
    def get_progress_dict(self) -> Dict[str, Any]:
        """
        获取当前执行进度的字典表示（用于API等场景）
        
        Returns:
            Dict[str, Any]: 进度信息字典
        """
        progress = self._get_progress_snapshot()
        return {
            "total": progress.total,
            "completed": progress.completed,
            "failed": progress.failed,
            "running": progress.running,
            "pending": progress.pending,
            "skipped": progress.skipped,
            "elapsed_time": progress.elapsed_time,
            "completion_rate": progress.completion_rate,
            "success_rate": progress.success_rate,
            "estimated_remaining_time": progress.estimated_remaining_time
        }
    
    def get_error_summary(self) -> ErrorSummary:
        """
        获取错误汇总信息（线程安全）
        
        Returns:
            ErrorSummary: 错误汇总信息快照
        """
        with self._lock:
            return ErrorSummary(
                total_errors=self._error_summary.total_errors,
                failed_tasks=self._error_summary.failed_tasks.copy(),
                skipped_tasks=self._error_summary.skipped_tasks.copy(),
                error_types=self._error_summary.error_types.copy(),
                critical_errors=self._error_summary.critical_errors.copy()
            )
    
    def get_execution_summary(self, results: List[TaskResult]) -> ExecutionSummary:
        """
        获取完整的执行汇总信息
        
        Args:
            results: 任务结果列表
            
        Returns:
            ExecutionSummary: 执行汇总信息
        """
        progress = self._get_progress_snapshot()
        errors = self.get_error_summary()
        
        return ExecutionSummary(
            progress=progress,
            errors=errors,
            results=results
        )
    
    def _execute_task(self, task: Task) -> TaskResult:
        """
        执行单个任务
        
        Args:
            task: 任务对象
            
        Returns:
            TaskResult: 任务执行结果
        """
        start_time = time.time()
        
        try:
            result = task.func(*task.args, **task.kwargs)
            execution_time = time.time() - start_time
            
            return TaskResult(
                task_id=task.id,
                success=True,
                result=result,
                execution_time=execution_time,
                metadata=task.metadata.copy(),
                skipped=False,
                error_type=None
            )
        
        except Exception as e:
            execution_time = time.time() - start_time
            
            # 获取异常类型
            error_type = type(e).__name__
            
            return TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
                execution_time=execution_time,
                metadata=task.metadata.copy(),
                skipped=False,
                error_type=error_type
            )
    
    def _get_progress_snapshot(self) -> ExecutionProgress:
        """获取进度信息的线程安全快照"""
        with self._lock:
            return ExecutionProgress(
                total=self._progress.total,
                completed=self._progress.completed,
                failed=self._progress.failed,
                running=self._progress.running,
                pending=self._progress.pending,
                skipped=self._progress.skipped,
                start_time=self._progress.start_time,
                current_time=time.time()
            )
    
    def _detect_cycles(
        self, 
        dependency_graph: Dict[str, List[str]], 
        task_ids: Set[str]
    ) -> None:
        """
        检测依赖图中的循环依赖
        
        Args:
            dependency_graph: 依赖图
            task_ids: 所有任务ID集合
            
        Raises:
            ValueError: 如果检测到循环依赖
        """
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        
        def dfs(node: str, path: List[str]) -> Optional[List[str]]:
            """DFS 检测循环，返回循环路径"""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for dep in dependency_graph.get(node, []):
                if dep not in visited:
                    cycle_path = dfs(dep, path.copy())
                    if cycle_path:
                        return cycle_path
                elif dep in rec_stack:
                    # 找到循环
                    cycle_start = path.index(dep)
                    return path[cycle_start:] + [dep]
            
            rec_stack.remove(node)
            return None
        
        for node in task_ids:
            if node not in visited:
                cycle_path = dfs(node, [])
                if cycle_path:
                    cycle_str = " -> ".join(cycle_path)
                    raise ValueError(f"检测到循环依赖: {cycle_str}")
