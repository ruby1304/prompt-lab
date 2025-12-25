# 进度跟踪指南

本指南介绍如何使用 Prompt Lab 的进度跟踪功能，包括实时进度更新、进度查询接口和与 PipelineProgressTracker 的集成。

## 目录

- [概述](#概述)
- [核心组件](#核心组件)
- [基本用法](#基本用法)
- [高级功能](#高级功能)
- [API 参考](#api-参考)
- [最佳实践](#最佳实践)

## 概述

进度跟踪系统提供以下功能：

1. **实时进度更新**: 在任务执行过程中实时更新进度信息
2. **进度查询接口**: 支持线程安全的进度查询，可用于 API、监控等场景
3. **Pipeline 集成**: 与 PipelineProgressTracker 深度集成，支持复杂的 Pipeline 执行场景
4. **并发执行支持**: 与 ConcurrentExecutor 集成，支持并发任务的进度跟踪

## 核心组件

### ProgressStats

进度统计信息数据类，包含：

- `total_items`: 总项目数
- `completed_items`: 已完成项目数
- `failed_items`: 失败项目数
- `success_items`: 成功项目数（计算属性）
- `progress_percentage`: 完成百分比（计算属性）
- `elapsed_time`: 已用时间（计算属性）
- `estimated_remaining_time`: 预估剩余时间（计算属性）
- `estimated_completion_time`: 预估完成时间（计算属性）

### ProgressTracker

通用进度跟踪器，支持：

- 实时进度显示（使用 Rich 库）
- 进度回调机制
- 线程安全的进度查询
- 自动计算预估时间

### PipelineProgressTracker

Pipeline 专用进度跟踪器，继承自 ProgressTracker，额外支持：

- 样本级别的进度跟踪
- 步骤级别的进度跟踪
- Pipeline 特定的统计信息

### ExecutionProgress

并发执行进度信息，包含：

- `total`: 总任务数
- `completed`: 已完成任务数
- `failed`: 失败任务数
- `running`: 正在运行的任务数
- `pending`: 待执行任务数
- `completion_rate`: 完成率
- `estimated_remaining_time`: 预估剩余时间

## 基本用法

### 1. 使用 ProgressTracker

```python
from src.progress_tracker import ProgressTracker

# 创建进度跟踪器
tracker = ProgressTracker(
    task_name="数据处理",
    total_items=100,
    show_spinner=True,
    show_eta=True
)

# 开始跟踪
tracker.start()

# 处理项目
for i in range(100):
    # 执行任务
    process_item(i)
    
    # 更新进度
    tracker.update(
        current_item=f"项目_{i+1}",
        current_step="处理中",
        increment=1,
        failed=(i % 10 == 0)  # 示例：每10个失败一次
    )

# 完成跟踪
tracker.finish("处理完成！")
```

### 2. 使用 PipelineProgressTracker

```python
from src.progress_tracker import PipelineProgressTracker

# 创建 Pipeline 进度跟踪器
tracker = PipelineProgressTracker(
    pipeline_name="示例Pipeline",
    total_samples=10,
    total_steps=3,
    variant="baseline"
)

# 开始跟踪
tracker.start()

# 处理每个样本
for sample_idx in range(10):
    sample_id = f"sample_{sample_idx + 1}"
    
    # 执行每个步骤
    for step_idx in range(3):
        step_name = f"步骤_{step_idx + 1}"
        
        # 更新进度
        tracker.update_sample(
            sample_index=sample_idx,
            sample_id=sample_id,
            step_index=step_idx,
            step_name=step_name
        )
        
        # 执行步骤
        execute_step(sample_id, step_name)
    
    # 完成样本
    tracker.complete_sample(
        sample_index=sample_idx,
        sample_id=sample_id,
        failed=False
    )

# 完成跟踪
tracker.finish("Pipeline 执行完成！")
```

### 3. 使用 ConcurrentExecutor 的进度跟踪

```python
from src.concurrent_executor import ConcurrentExecutor, Task

# 创建并发执行器
executor = ConcurrentExecutor(max_workers=4, strategy="thread")

# 定义进度回调
def progress_callback(progress):
    print(f"进度: {progress.completed}/{progress.total} "
          f"({progress.completion_rate*100:.1f}%)")

# 创建任务
tasks = [
    Task(id=f"task_{i}", func=process_data, args=(i,))
    for i in range(100)
]

# 执行任务（带进度跟踪）
results = executor.execute_concurrent(
    tasks=tasks,
    progress_callback=progress_callback
)
```

## 高级功能

### 1. 进度查询接口

进度跟踪器支持线程安全的进度查询，可用于 API、监控等场景：

```python
import threading
import time

# 创建进度跟踪器
tracker = ProgressTracker(task_name="长时间任务", total_items=1000)
tracker.start()

# 在后台线程中查询进度
def query_progress():
    while True:
        # 获取进度统计
        stats = tracker.get_stats()
        print(f"当前进度: {stats.progress_percentage:.1f}%")
        
        # 获取字典格式（用于 API）
        stats_dict = tracker.get_stats_dict()
        # 可以将 stats_dict 发送到 API、数据库等
        
        time.sleep(1)

# 启动查询线程
query_thread = threading.Thread(target=query_progress, daemon=True)
query_thread.start()

# 执行任务
for i in range(1000):
    process_item(i)
    tracker.update(increment=1)

tracker.finish()
```

### 2. 进度回调机制

可以添加多个回调函数，在进度更新时自动调用：

```python
# 创建进度跟踪器
tracker = ProgressTracker(task_name="任务", total_items=100)

# 添加回调函数
def log_progress(stats):
    """记录进度到日志"""
    logger.info(f"进度: {stats.progress_percentage:.1f}%")

def send_to_api(stats):
    """发送进度到 API"""
    api_client.update_progress(stats.to_dict())

tracker.add_callback(log_progress)
tracker.add_callback(send_to_api)

# 开始执行
tracker.start()

# 每次更新都会触发回调
for i in range(100):
    tracker.update(increment=1)

tracker.finish()
```

### 3. 与 Pipeline 并发执行集成

PipelineRunner 自动集成了进度跟踪和并发执行：

```python
from src.pipeline_runner import PipelineRunner
from src.pipeline_config import load_pipeline_config

# 加载 Pipeline 配置
config = load_pipeline_config("pipeline.yaml")

# 创建 Pipeline 执行器（启用并发）
runner = PipelineRunner(
    config=config,
    enable_concurrent=True,
    max_workers=4
)

# 执行 Pipeline（自动显示进度）
results = runner.execute(
    samples=test_samples,
    variant="baseline",
    use_progress_tracker=True  # 启用进度跟踪
)
```

在并发执行时，进度跟踪器会显示：
- 当前执行的批次
- 并发执行的任务数
- 整体进度百分比
- 预估剩余时间

### 4. 自定义进度显示

可以自定义进度显示的组件：

```python
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn

# 创建自定义进度显示
progress = Progress(
    SpinnerColumn(),
    TextColumn("[bold blue]{task.description}"),
    BarColumn(),
    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    TextColumn("({task.completed}/{task.total})"),
    TextColumn("[cyan]{task.fields[custom_info]}"),  # 自定义字段
)

# 使用自定义进度
tracker = ProgressTracker(
    task_name="自定义任务",
    total_items=100
)
tracker.progress = progress
tracker.start()

# 更新时可以传递自定义信息
for i in range(100):
    tracker.update(
        increment=1,
        custom_info=f"处理项目 {i+1}"
    )

tracker.finish()
```

## API 参考

### ProgressTracker

#### 构造函数

```python
ProgressTracker(
    task_name: str,
    total_items: int,
    console: Optional[Console] = None,
    show_spinner: bool = True,
    show_eta: bool = True
)
```

#### 主要方法

- `start()`: 开始进度跟踪
- `update(completed=None, current_item="", current_step="", increment=1, failed=False)`: 更新进度
- `finish(success_message="")`: 完成进度跟踪
- `get_stats() -> ProgressStats`: 获取进度统计（线程安全）
- `get_stats_dict() -> Dict[str, Any]`: 获取进度统计字典
- `add_callback(callback: Callable[[ProgressStats], None])`: 添加进度回调

### PipelineProgressTracker

继承自 ProgressTracker，额外方法：

- `update_sample(sample_index, sample_id, step_index=0, step_name="", failed=False)`: 更新样本进度
- `complete_sample(sample_index, sample_id, failed=False)`: 完成样本处理
- `get_pipeline_stats_dict() -> Dict[str, Any]`: 获取 Pipeline 统计信息字典

### ConcurrentExecutor

#### 进度相关方法

- `get_progress() -> ExecutionProgress`: 获取当前执行进度（线程安全）
- `get_progress_dict() -> Dict[str, Any]`: 获取进度字典
- `execute_concurrent(tasks, progress_callback=None)`: 并发执行任务（带进度回调）
- `execute_with_dependencies(tasks, dependency_graph=None, progress_callback=None)`: 带依赖关系的并发执行（带进度回调）

## 最佳实践

### 1. 选择合适的进度跟踪器

- **简单任务**: 使用 `ProgressTracker`
- **Pipeline 执行**: 使用 `PipelineProgressTracker`
- **并发执行**: 使用 `ConcurrentExecutor` 的进度回调

### 2. 线程安全

所有进度查询方法都是线程安全的，可以在多线程环境中安全使用：

```python
# 在主线程中更新进度
tracker.update(increment=1)

# 在其他线程中查询进度
stats = tracker.get_stats()  # 线程安全
```

### 3. 进度回调的性能考虑

进度回调会在每次更新时调用，应避免在回调中执行耗时操作：

```python
# ❌ 不好的做法
def slow_callback(stats):
    time.sleep(1)  # 会严重影响性能
    send_to_api(stats)

# ✅ 好的做法
def fast_callback(stats):
    # 使用异步或队列
    queue.put(stats)
```

### 4. 预估时间的准确性

预估时间基于已完成任务的平均时间，在以下情况下更准确：

- 任务执行时间相对均匀
- 已完成足够多的任务（至少 10%）
- 没有长时间的初始化开销

### 5. 与日志系统集成

```python
import logging

logger = logging.getLogger(__name__)

# 创建进度跟踪器
tracker = ProgressTracker(task_name="任务", total_items=100)

# 添加日志回调
def log_progress(stats):
    if stats.completed_items % 10 == 0:  # 每10个记录一次
        logger.info(
            f"进度: {stats.progress_percentage:.1f}%, "
            f"已用时: {stats.elapsed_time.total_seconds():.1f}秒"
        )

tracker.add_callback(log_progress)
```

### 6. 错误处理

进度跟踪器会自动处理回调中的异常，不会影响主流程：

```python
def risky_callback(stats):
    # 即使这里抛出异常，也不会影响进度跟踪
    raise Exception("回调失败")

tracker.add_callback(risky_callback)
tracker.update(increment=1)  # 继续正常工作
```

## 示例

完整的示例代码请参考：

- `examples/progress_tracking_demo.py`: 进度跟踪功能演示
- `examples/concurrent_executor_demo.py`: 并发执行器演示
- `tests/test_progress_tracking.py`: 单元测试示例

## 相关文档

- [并发执行器指南](concurrent-executor-guide.md)
- [Pipeline 执行指南](pipeline-guide.md)
- [性能优化指南](../guides/performance-optimization.md)
