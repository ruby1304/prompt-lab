# ConcurrentExecutor 使用指南

## 概述

`ConcurrentExecutor` 是一个强大的并发任务执行器，支持线程池和进程池两种执行策略。它提供了任务队列管理、结果收集、进度跟踪和依赖关系处理等功能。

## 核心特性

- **多种执行策略**: 支持线程池 (thread) 和进程池 (process) 两种执行模式
- **任务队列管理**: 自动管理任务队列，控制最大并发数
- **结果收集**: 保持结果顺序与输入任务顺序一致
- **进度跟踪**: 实时跟踪执行进度，支持进度回调
- **依赖关系处理**: 自动分析任务依赖，按依赖关系分批并发执行
- **错误处理**: 支持必需/可选任务，灵活处理失败情况
- **循环依赖检测**: 自动检测并报告循环依赖

## 快速开始

### 基本用法

```python
from src.concurrent_executor import ConcurrentExecutor, Task

# 创建执行器
executor = ConcurrentExecutor(max_workers=4, strategy="thread")

# 定义任务
def process_data(x):
    return x * 2

# 创建任务列表
tasks = [
    Task(id=f"task_{i}", func=process_data, args=(i,))
    for i in range(10)
]

# 并发执行
results = executor.execute_concurrent(tasks)

# 处理结果
for result in results:
    if result.success:
        print(f"{result.task_id}: {result.result}")
    else:
        print(f"{result.task_id} 失败: {result.error}")
```

### 带依赖关系的执行

```python
# 创建带依赖关系的任务
tasks = [
    Task(id="task1", func=func1, dependencies=[]),
    Task(id="task2", func=func2, dependencies=[]),
    Task(id="task3", func=func3, dependencies=["task1", "task2"]),
]

# 执行（自动处理依赖关系）
results = executor.execute_with_dependencies(tasks)
```

### 进度跟踪

```python
def progress_callback(progress):
    print(f"进度: {progress.completion_rate*100:.1f}% "
          f"({progress.completed}/{progress.total})")

results = executor.execute_concurrent(tasks, progress_callback=progress_callback)
```

## 数据模型

### Task

任务定义，包含以下字段：

- `id` (str): 任务唯一标识
- `func` (Callable): 要执行的函数
- `args` (tuple): 位置参数
- `kwargs` (dict): 关键字参数
- `dependencies` (List[str]): 依赖的任务ID列表
- `required` (bool): 是否必需（失败时是否继续）
- `metadata` (dict): 任务元数据

### TaskResult

任务执行结果，包含以下字段：

- `task_id` (str): 任务ID
- `success` (bool): 是否成功
- `result` (Any): 执行结果
- `error` (str): 错误信息
- `execution_time` (float): 执行时间（秒）
- `metadata` (dict): 结果元数据

### ExecutionProgress

执行进度信息，包含以下字段：

- `total` (int): 总任务数
- `completed` (int): 已完成任务数
- `failed` (int): 失败任务数
- `running` (int): 正在运行的任务数
- `pending` (int): 待执行任务数
- `start_time` (float): 开始时间
- `current_time` (float): 当前时间

属性：
- `elapsed_time`: 已用时间（秒）
- `completion_rate`: 完成率（0-1）
- `estimated_remaining_time`: 预计剩余时间（秒）

## API 参考

### ConcurrentExecutor

#### `__init__(max_workers: int = 4, strategy: str = "thread")`

初始化并发执行器。

**参数:**
- `max_workers`: 最大并发工作线程/进程数
- `strategy`: 执行策略，"thread" 或 "process"

**异常:**
- `ValueError`: 如果 strategy 不是 "thread" 或 "process"

#### `execute_concurrent(tasks: List[Task], progress_callback: Optional[Callable] = None) -> List[TaskResult]`

并发执行任务列表（无依赖关系）。

**参数:**
- `tasks`: 任务列表
- `progress_callback`: 进度回调函数，接收 ExecutionProgress 对象

**返回:**
- `List[TaskResult]`: 任务结果列表，顺序与输入任务列表一致

#### `execute_with_dependencies(tasks: List[Task], dependency_graph: Optional[Dict[str, List[str]]] = None, progress_callback: Optional[Callable] = None) -> List[TaskResult]`

根据依赖关系并发执行任务。

**参数:**
- `tasks`: 任务列表
- `dependency_graph`: 依赖图，格式为 {task_id: [dependency_task_ids]}。如果为 None，将从 Task.dependencies 构建
- `progress_callback`: 进度回调函数

**返回:**
- `List[TaskResult]`: 任务结果列表，顺序与输入任务列表一致

**异常:**
- `ValueError`: 如果检测到循环依赖或依赖的任务不存在

#### `get_progress() -> ExecutionProgress`

获取当前执行进度。

**返回:**
- `ExecutionProgress`: 进度信息快照

## 使用场景

### 1. 批量数据处理

```python
# 并发处理大量数据
tasks = [
    Task(id=f"process_{i}", func=process_item, args=(item,))
    for i, item in enumerate(data_items)
]

results = executor.execute_concurrent(tasks)
```

### 2. Pipeline 步骤并发执行

```python
# Pipeline 中的独立步骤可以并发执行
tasks = [
    Task(id="step1", func=run_agent, args=("agent1", input1)),
    Task(id="step2", func=run_agent, args=("agent2", input2)),
    Task(id="step3", func=run_agent, args=("agent3", input3)),
]

results = executor.execute_concurrent(tasks)
```

### 3. 复杂依赖关系处理

```python
# 自动处理复杂的依赖关系
tasks = [
    Task(id="fetch_data", func=fetch_data),
    Task(id="process_a", func=process_a, dependencies=["fetch_data"]),
    Task(id="process_b", func=process_b, dependencies=["fetch_data"]),
    Task(id="merge", func=merge_results, dependencies=["process_a", "process_b"]),
]

results = executor.execute_with_dependencies(tasks)
```

### 4. 测试用例并发执行

```python
# 并发执行多个测试用例
tasks = [
    Task(id=f"test_{i}", func=run_test, args=(test_case,))
    for i, test_case in enumerate(test_cases)
]

results = executor.execute_concurrent(tasks)
```

## 最佳实践

### 1. 选择合适的执行策略

- **线程池 (thread)**: 适用于 I/O 密集型任务（网络请求、文件读写、LLM API 调用）
- **进程池 (process)**: 适用于 CPU 密集型任务（数据处理、计算）

### 2. 设置合理的并发数

```python
import os

# 根据 CPU 核心数设置
max_workers = os.cpu_count()

# 或根据任务类型设置
max_workers = 10  # I/O 密集型可以设置更高
```

### 3. 使用进度回调监控执行

```python
def progress_callback(progress):
    if progress.completed % 10 == 0:  # 每10个任务打印一次
        print(f"进度: {progress.completion_rate*100:.1f}%")

results = executor.execute_concurrent(tasks, progress_callback=progress_callback)
```

### 4. 处理任务失败

```python
# 标记可选任务
tasks = [
    Task(id="critical", func=critical_func, required=True),
    Task(id="optional", func=optional_func, required=False),
]

results = executor.execute_with_dependencies(tasks)

# 检查结果
for result in results:
    if not result.success:
        print(f"任务 {result.task_id} 失败: {result.error}")
```

### 5. 使用元数据传递上下文

```python
tasks = [
    Task(
        id=f"task_{i}",
        func=process_data,
        args=(data,),
        metadata={"source": "api", "priority": "high"}
    )
    for i, data in enumerate(data_items)
]

results = executor.execute_concurrent(tasks)

# 访问元数据
for result in results:
    print(f"任务 {result.task_id} (优先级: {result.metadata['priority']})")
```

## 性能考虑

### 并发性能提升

使用 `ConcurrentExecutor` 可以显著提升性能：

- **无依赖任务**: 理论加速比 = min(任务数, max_workers)
- **有依赖任务**: 加速比取决于依赖图的结构

### 示例性能对比

```python
# 串行执行: 10个任务 × 1秒 = 10秒
# 并发执行 (max_workers=4): 约 3秒 (10/4 ≈ 2.5批次)
```

## 注意事项

1. **线程安全**: 确保传递给任务的函数是线程安全的
2. **进程序列化**: 使用进程池时，函数和参数必须可序列化
3. **资源限制**: 注意系统资源限制（文件描述符、内存等）
4. **错误处理**: 任务函数中的异常会被捕获并记录在 TaskResult 中
5. **循环依赖**: 系统会自动检测并报告循环依赖

## 示例代码

完整的示例代码请参考 `examples/concurrent_executor_demo.py`。

## 相关文档

- [DependencyAnalyzer 使用指南](./dependency-analyzer-guide.md)
- [Pipeline 并发执行](./pipeline-guide.md#并发执行)
- [性能优化指南](../guides/performance-optimization.md)
