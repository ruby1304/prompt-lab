# 并发错误处理指南

本指南介绍 ConcurrentExecutor 的错误处理功能，包括错误隔离、错误收集、可选步骤处理和结果顺序保持。

## 目录

- [概述](#概述)
- [核心功能](#核心功能)
- [错误隔离](#错误隔离)
- [错误收集](#错误收集)
- [可选步骤处理](#可选步骤处理)
- [结果顺序保持](#结果顺序保持)
- [API 参考](#api-参考)
- [最佳实践](#最佳实践)

## 概述

ConcurrentExecutor 提供了强大的错误处理机制，确保在并发执行中：

1. **错误隔离**: 一个任务的失败不会影响其他独立任务的执行
2. **错误收集**: 系统收集所有错误并提供详细的错误报告
3. **可选步骤处理**: 区分必需任务和可选任务，灵活处理依赖关系
4. **结果顺序保持**: 无论任务何时完成，结果都按输入顺序返回

## 核心功能

### 1. 错误隔离

错误隔离确保一个任务的失败不会影响其他独立任务的执行。

```python
from src.concurrent_executor import ConcurrentExecutor, Task

executor = ConcurrentExecutor(max_workers=4)

tasks = [
    Task(id="task1", func=success_func, args=(1,)),
    Task(id="task2", func=failing_func),  # 这个会失败
    Task(id="task3", func=success_func, args=(3,)),
]

results = executor.execute_concurrent(tasks)

# task1 和 task3 成功执行，不受 task2 失败的影响
assert results[0].success is True
assert results[1].success is False
assert results[2].success is True
```

### 2. 错误收集

系统自动收集所有错误信息，包括：

- 失败的任务列表
- 错误类型统计
- 关键错误（必需任务失败）
- 跳过的任务

```python
results = executor.execute_concurrent(tasks)

# 获取错误汇总
error_summary = executor.get_error_summary()

print(f"总错误数: {error_summary.total_errors}")
print(f"失败任务: {error_summary.failed_tasks}")
print(f"错误类型: {error_summary.error_types}")
print(f"关键错误: {error_summary.critical_errors}")
print(f"跳过任务: {error_summary.skipped_tasks}")
```

### 3. 可选步骤处理

通过 `required` 参数区分必需任务和可选任务：

- **必需任务** (`required=True`): 失败会阻止依赖任务执行
- **可选任务** (`required=False`): 失败不会阻止依赖任务执行

```python
tasks = [
    # 可选任务失败，依赖任务继续执行
    Task(id="optional", func=failing_func, required=False),
    Task(id="dependent1", func=success_func, args=(1,), 
         dependencies=["optional"]),
    
    # 必需任务失败，依赖任务被跳过
    Task(id="required", func=failing_func, required=True),
    Task(id="dependent2", func=success_func, args=(2,), 
         dependencies=["required"]),
]

results = executor.execute_with_dependencies(tasks)

# dependent1 继续执行（因为 optional 是可选的）
assert results[1].success is True

# dependent2 被跳过（因为 required 是必需的且失败了）
assert results[3].skipped is True
```

### 4. 结果顺序保持

无论任务何时完成，结果都按输入顺序返回：

```python
tasks = [
    Task(id="slow", func=slow_func, args=(0.3,)),    # 最慢
    Task(id="fast", func=fast_func, args=(0.1,)),    # 最快
    Task(id="medium", func=medium_func, args=(0.2,)), # 中等
]

results = executor.execute_concurrent(tasks)

# 结果顺序与输入一致，不受完成时间影响
assert results[0].task_id == "slow"
assert results[1].task_id == "fast"
assert results[2].task_id == "medium"
```

## 错误隔离

### 工作原理

每个任务在独立的执行上下文中运行：

1. 任务提交到线程池/进程池
2. 每个任务独立执行，捕获自己的异常
3. 失败的任务不会影响其他任务的执行
4. 所有任务的结果（成功或失败）都会被收集

### 示例：混合成功和失败

```python
def process_item(item_id: int) -> dict:
    if item_id % 3 == 0:
        raise ValueError(f"Item {item_id} is invalid")
    return {"id": item_id, "processed": True}

executor = ConcurrentExecutor(max_workers=4)

tasks = [
    Task(id=f"item_{i}", func=process_item, args=(i,))
    for i in range(10)
]

results = executor.execute_concurrent(tasks)

# 统计成功和失败
successful = [r for r in results if r.success]
failed = [r for r in results if not r.success]

print(f"成功: {len(successful)}, 失败: {len(failed)}")
# 输出: 成功: 7, 失败: 3
```

### 依赖执行中的错误隔离

在依赖执行中，错误隔离体现在：

- 独立分支的失败不会影响其他分支
- 可选任务的失败不会阻止依赖任务

```python
# 创建有多个分支的依赖图
tasks = [
    Task(id="root", func=success_func, args=(0,)),
    
    # 三个独立分支
    Task(id="branch1", func=failing_func, dependencies=["root"], required=False),
    Task(id="branch2", func=success_func, args=(2,), dependencies=["root"]),
    Task(id="branch3", func=success_func, args=(3,), dependencies=["root"]),
    
    # 合并节点
    Task(id="merge", func=aggregate_func, 
         dependencies=["branch1", "branch2", "branch3"]),
]

results = executor.execute_with_dependencies(tasks)

# branch1 失败不影响 branch2 和 branch3
assert results[1].success is False  # branch1 失败
assert results[2].success is True   # branch2 成功
assert results[3].success is True   # branch3 成功
assert results[4].success is True   # merge 继续执行
```

## 错误收集

### ErrorSummary 类

`ErrorSummary` 提供完整的错误信息：

```python
@dataclass
class ErrorSummary:
    total_errors: int              # 总错误数
    failed_tasks: List[str]        # 失败的任务ID列表
    skipped_tasks: List[str]       # 跳过的任务ID列表
    error_types: Dict[str, int]    # 错误类型统计
    critical_errors: List[str]     # 关键错误（必需任务失败）
```

### 获取错误汇总

```python
# 执行任务
results = executor.execute_concurrent(tasks)

# 获取错误汇总
error_summary = executor.get_error_summary()

# 检查是否有关键错误
if error_summary.has_critical_errors():
    print("警告：有关键任务失败！")
    print(f"关键错误: {error_summary.critical_errors}")

# 查看错误类型分布
for error_type, count in error_summary.error_types.items():
    print(f"{error_type}: {count} 次")
```

### ExecutionSummary 类

`ExecutionSummary` 提供完整的执行状态：

```python
# 获取执行汇总
summary = executor.get_execution_summary(results)

# 进度信息
print(f"总任务: {summary.progress.total}")
print(f"完成: {summary.progress.completed}")
print(f"失败: {summary.progress.failed}")
print(f"跳过: {summary.progress.skipped}")
print(f"成功率: {summary.progress.success_rate:.1%}")

# 错误信息
print(f"总错误: {summary.errors.total_errors}")
print(f"关键错误: {summary.errors.has_critical_errors()}")

# 结果分类
successful = summary.get_successful_results()
failed = summary.get_failed_results()
skipped = summary.get_skipped_results()

# 整体状态
if summary.is_successful():
    print("执行成功！")
else:
    print("执行失败，有关键错误")
```

### 转换为字典

方便序列化和API返回：

```python
# 错误汇总转字典
error_dict = error_summary.to_dict()
# {
#     "total_errors": 3,
#     "failed_tasks": ["task1", "task2", "task3"],
#     "skipped_tasks": ["task4"],
#     "error_types": {"ValueError": 2, "TypeError": 1},
#     "critical_errors": ["task1"],
#     "has_critical_errors": True
# }

# 执行汇总转字典
summary_dict = summary.to_dict()
# {
#     "progress": {...},
#     "errors": {...},
#     "is_successful": False,
#     "failed_count": 3,
#     "skipped_count": 1,
#     "successful_count": 5
# }
```

## 可选步骤处理

### 必需 vs 可选任务

```python
# 必需任务（默认）
required_task = Task(
    id="critical_step",
    func=validate_data,
    required=True  # 默认值
)

# 可选任务
optional_task = Task(
    id="optional_step",
    func=send_notification,
    required=False
)
```

### 依赖处理规则

1. **必需任务失败**:
   - 所有依赖该任务的后续任务被跳过
   - 被跳过的任务标记为 `skipped=True`
   - 错误信息为 "必需的依赖任务失败"

2. **可选任务失败**:
   - 依赖该任务的后续任务继续执行
   - 不影响执行流程

### 混合依赖示例

```python
tasks = [
    # 必需任务
    Task(id="load_data", func=load_data, required=True),
    
    # 可选任务（依赖必需任务）
    Task(id="cache_data", func=cache_data, 
         dependencies=["load_data"], required=False),
    
    # 必需任务（依赖必需任务）
    Task(id="validate", func=validate, 
         dependencies=["load_data"], required=True),
    
    # 必需任务（依赖混合）
    Task(id="process", func=process, 
         dependencies=["validate", "cache_data"], required=True),
]

results = executor.execute_with_dependencies(tasks)

# 如果 load_data 失败：
# - cache_data 被跳过
# - validate 被跳过
# - process 被跳过

# 如果 cache_data 失败（可选）：
# - validate 继续执行
# - process 继续执行（只要 validate 成功）
```

### 跳过任务的识别

```python
for result in results:
    if result.skipped:
        print(f"{result.task_id} 被跳过: {result.error}")
        # 输出: task_name 被跳过: 必需的依赖任务失败

# 或使用错误汇总
error_summary = executor.get_error_summary()
print(f"跳过的任务: {error_summary.skipped_tasks}")
```

## 结果顺序保持

### 为什么重要

在并发执行中，任务完成的顺序是不确定的，但结果顺序必须与输入一致：

- 便于结果处理和验证
- 保持数据关联性
- 简化错误定位

### 实现机制

```python
# 内部使用任务ID到索引的映射
task_id_to_index = {task.id: i for i, task in enumerate(tasks)}
results = [None] * len(tasks)

# 任务完成时，放到正确的位置
for future in as_completed(future_to_task):
    task = future_to_task[future]
    task_result = future.result()
    
    index = task_id_to_index[task.id]
    results[index] = task_result
```

### 验证顺序

```python
tasks = [
    Task(id=f"task_{i}", func=process_func, args=(i,))
    for i in range(10)
]

results = executor.execute_concurrent(tasks)

# 验证顺序
for i, result in enumerate(results):
    assert result.task_id == f"task_{i}"
```

### 混合成功和失败

即使有失败，顺序也保持：

```python
tasks = [
    Task(id="task_0", func=success_func),
    Task(id="task_1", func=failing_func),
    Task(id="task_2", func=success_func),
    Task(id="task_3", func=failing_func),
]

results = executor.execute_concurrent(tasks)

# 结果顺序与输入一致
assert results[0].task_id == "task_0"
assert results[1].task_id == "task_1"
assert results[2].task_id == "task_2"
assert results[3].task_id == "task_3"

# 成功/失败状态正确
assert results[0].success is True
assert results[1].success is False
assert results[2].success is True
assert results[3].success is False
```

## API 参考

### TaskResult

```python
@dataclass
class TaskResult:
    task_id: str              # 任务ID
    success: bool             # 是否成功
    result: Any               # 执行结果
    error: Optional[str]      # 错误信息
    execution_time: float     # 执行时间（秒）
    metadata: Dict[str, Any]  # 任务元数据
    skipped: bool             # 是否被跳过
    error_type: Optional[str] # 错误类型
```

### ErrorSummary

```python
@dataclass
class ErrorSummary:
    total_errors: int
    failed_tasks: List[str]
    skipped_tasks: List[str]
    error_types: Dict[str, int]
    critical_errors: List[str]
    
    def add_error(task_id: str, error_type: str, is_critical: bool) -> None
    def add_skipped(task_id: str) -> None
    def has_critical_errors() -> bool
    def to_dict() -> Dict[str, Any]
```

### ExecutionProgress

```python
@dataclass
class ExecutionProgress:
    total: int
    completed: int
    failed: int
    running: int
    pending: int
    skipped: int
    start_time: float
    current_time: float
    
    @property
    def success_rate() -> float  # 成功率（0-1）
```

### ExecutionSummary

```python
@dataclass
class ExecutionSummary:
    progress: ExecutionProgress
    errors: ErrorSummary
    results: List[TaskResult]
    
    def is_successful() -> bool
    def get_failed_results() -> List[TaskResult]
    def get_skipped_results() -> List[TaskResult]
    def get_successful_results() -> List[TaskResult]
    def to_dict() -> Dict[str, Any]
```

### ConcurrentExecutor 方法

```python
# 获取错误汇总
def get_error_summary() -> ErrorSummary

# 获取执行汇总
def get_execution_summary(results: List[TaskResult]) -> ExecutionSummary

# 获取进度（包含成功率）
def get_progress() -> ExecutionProgress

# 获取进度字典（包含跳过计数）
def get_progress_dict() -> Dict[str, Any]
```

## 最佳实践

### 1. 合理设置 required 标志

```python
# 关键步骤设为必需
Task(id="load_config", func=load_config, required=True)

# 非关键步骤设为可选
Task(id="send_metrics", func=send_metrics, required=False)
Task(id="log_to_external", func=log_external, required=False)
```

### 2. 使用进度回调监控执行

```python
def progress_callback(progress: ExecutionProgress):
    print(f"进度: {progress.completed}/{progress.total}")
    print(f"成功率: {progress.success_rate:.1%}")
    print(f"失败: {progress.failed}, 跳过: {progress.skipped}")
    
    # 如果失败率过高，可以考虑提前告警
    if progress.completed > 10 and progress.success_rate < 0.5:
        logger.warning("成功率低于50%，请检查！")

results = executor.execute_concurrent(tasks, progress_callback=progress_callback)
```

### 3. 检查执行结果

```python
results = executor.execute_concurrent(tasks)
summary = executor.get_execution_summary(results)

# 检查是否有关键错误
if not summary.is_successful():
    logger.error(f"执行失败，关键错误: {summary.errors.critical_errors}")
    # 采取补救措施
    handle_critical_errors(summary.errors)

# 记录错误统计
for error_type, count in summary.errors.error_types.items():
    metrics.record(f"error.{error_type}", count)
```

### 4. 处理跳过的任务

```python
skipped = summary.get_skipped_results()

if skipped:
    logger.warning(f"有 {len(skipped)} 个任务被跳过")
    
    # 记录跳过的任务
    for result in skipped:
        logger.info(f"跳过任务: {result.task_id}, 原因: {result.error}")
    
    # 可能需要手动处理这些任务
    if should_retry_skipped():
        retry_tasks(skipped)
```

### 5. 错误恢复策略

```python
def execute_with_retry(tasks, max_retries=3):
    """带重试的执行"""
    executor = ConcurrentExecutor()
    
    for attempt in range(max_retries):
        results = executor.execute_concurrent(tasks)
        summary = executor.get_execution_summary(results)
        
        if summary.is_successful():
            return results
        
        # 只重试失败的任务
        failed_results = summary.get_failed_results()
        tasks = [
            task for task in tasks 
            if task.id in [r.task_id for r in failed_results]
        ]
        
        logger.info(f"重试第 {attempt + 1} 次，剩余 {len(tasks)} 个任务")
    
    raise Exception("达到最大重试次数")
```

### 6. 日志和监控

```python
# 记录详细的错误信息
for result in results:
    if not result.success:
        logger.error(
            f"任务失败: {result.task_id}",
            extra={
                "error_type": result.error_type,
                "error_message": result.error,
                "execution_time": result.execution_time,
                "skipped": result.skipped
            }
        )

# 记录汇总指标
error_summary = executor.get_error_summary()
metrics.gauge("tasks.total_errors", error_summary.total_errors)
metrics.gauge("tasks.critical_errors", len(error_summary.critical_errors))
metrics.gauge("tasks.skipped", len(error_summary.skipped_tasks))
```

## 相关文档

- [并发执行器指南](concurrent-executor-guide.md)
- [依赖分析器指南](dependency-analyzer-guide.md)
- [进度跟踪指南](progress-tracking-guide.md)

## 示例代码

完整的示例代码请参考：

- `examples/concurrent_error_handling_demo.py` - 错误处理演示
- `tests/test_concurrent_error_handling.py` - 错误处理测试
