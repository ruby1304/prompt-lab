# 进度跟踪快速参考

## 快速开始

### 基本用法

```python
from src.progress_tracker import ProgressTracker

# 创建并使用进度跟踪器
with ProgressTracker("任务名称", total_items=100) as tracker:
    for i in range(100):
        # 执行任务
        process_item(i)
        # 更新进度
        tracker.update(increment=1)
```

### Pipeline 进度跟踪

```python
from src.progress_tracker import PipelineProgressTracker

tracker = PipelineProgressTracker(
    pipeline_name="我的Pipeline",
    total_samples=10,
    total_steps=3
)

tracker.start()
for i in range(10):
    for j in range(3):
        tracker.update_sample(i, f"sample_{i}", j, f"步骤{j}")
        execute_step()
    tracker.complete_sample(i, f"sample_{i}")
tracker.finish()
```

### 并发执行进度跟踪

```python
from src.concurrent_executor import ConcurrentExecutor, Task

executor = ConcurrentExecutor(max_workers=4)

def progress_callback(progress):
    print(f"{progress.completed}/{progress.total} ({progress.completion_rate*100:.1f}%)")

results = executor.execute_concurrent(
    tasks=[Task(id=f"t{i}", func=work, args=(i,)) for i in range(100)],
    progress_callback=progress_callback
)
```

## API 参考

### ProgressTracker

| 方法 | 说明 |
|------|------|
| `start()` | 开始进度跟踪 |
| `update(increment=1, current_item="", current_step="", failed=False)` | 更新进度 |
| `finish(message="")` | 完成进度跟踪 |
| `get_stats()` | 获取进度统计（线程安全） |
| `get_stats_dict()` | 获取进度字典（用于API） |
| `add_callback(func)` | 添加进度回调 |

### PipelineProgressTracker

继承 ProgressTracker，额外方法：

| 方法 | 说明 |
|------|------|
| `update_sample(index, id, step_index, step_name)` | 更新样本进度 |
| `complete_sample(index, id, failed=False)` | 完成样本 |
| `get_pipeline_stats_dict()` | 获取Pipeline统计 |

### ConcurrentExecutor

| 方法 | 说明 |
|------|------|
| `get_progress()` | 获取执行进度 |
| `get_progress_dict()` | 获取进度字典 |
| `execute_concurrent(tasks, progress_callback)` | 并发执行（带回调） |
| `execute_with_dependencies(tasks, graph, progress_callback)` | 依赖执行（带回调） |

## 进度信息结构

### ProgressStats

```python
{
    "total_items": 100,           # 总项目数
    "completed_items": 50,        # 已完成
    "failed_items": 5,            # 失败
    "success_items": 45,          # 成功
    "progress_percentage": 50.0,  # 百分比
    "elapsed_time": 30.5,         # 已用时间（秒）
    "estimated_remaining_time": 30.5,  # 预估剩余（秒）
    "estimated_completion_time": "2025-12-16T14:35:58",  # 预估完成时间
    "current_item": "项目50",     # 当前项目
    "current_step": "步骤2"       # 当前步骤
}
```

### ExecutionProgress

```python
{
    "total": 100,                 # 总任务数
    "completed": 50,              # 已完成
    "failed": 5,                  # 失败
    "running": 4,                 # 运行中
    "pending": 46,                # 待处理
    "elapsed_time": 30.5,         # 已用时间
    "completion_rate": 0.5,       # 完成率
    "estimated_remaining_time": 30.5  # 预估剩余
}
```

## 常见模式

### 1. 添加进度回调

```python
tracker = ProgressTracker("任务", 100)

def log_progress(stats):
    logger.info(f"进度: {stats.progress_percentage:.1f}%")

tracker.add_callback(log_progress)
```

### 2. 后台查询进度

```python
import threading

def query_progress():
    while not done:
        stats = tracker.get_stats_dict()
        send_to_api(stats)
        time.sleep(1)

thread = threading.Thread(target=query_progress, daemon=True)
thread.start()
```

### 3. 集成到 Pipeline

```python
runner = PipelineRunner(config, enable_concurrent=True)
results = runner.execute(
    samples=samples,
    use_progress_tracker=True  # 自动显示进度
)
```

### 4. 自定义进度显示

```python
from rich.progress import Progress, SpinnerColumn, BarColumn

progress = Progress(
    SpinnerColumn(),
    BarColumn(),
    TextColumn("{task.percentage:>3.0f}%")
)

tracker = ProgressTracker("任务", 100)
tracker.progress = progress
```

## 最佳实践

### ✅ 推荐做法

```python
# 使用上下文管理器
with ProgressTracker("任务", 100) as tracker:
    for i in range(100):
        tracker.update(increment=1)

# 线程安全查询
stats = tracker.get_stats()  # 总是线程安全

# 轻量级回调
def fast_callback(stats):
    queue.put(stats)  # 使用队列异步处理
```

### ❌ 避免做法

```python
# 不要在回调中执行耗时操作
def slow_callback(stats):
    time.sleep(1)  # ❌ 会严重影响性能
    send_to_api(stats)

# 不要直接修改 stats
stats = tracker.get_stats()
stats.completed_items = 100  # ❌ 不会生效（是副本）
```

## 故障排查

### 问题：进度不更新

```python
# 确保调用了 start()
tracker.start()  # ✅ 必须调用

# 确保调用了 update()
tracker.update(increment=1)  # ✅ 更新进度
```

### 问题：预估时间不准确

```python
# 需要完成足够多的任务
if stats.completed_items < 10:
    # 预估时间可能不准确
    pass
```

### 问题：回调不执行

```python
# 确保添加了回调
tracker.add_callback(my_callback)  # ✅

# 确保回调函数签名正确
def my_callback(stats: ProgressStats):  # ✅
    pass
```

## 示例代码

完整示例：`examples/progress_tracking_demo.py`

```bash
python examples/progress_tracking_demo.py
```

## 相关文档

- [详细指南](progress-tracking-guide.md)
- [并发执行器](concurrent-executor-guide.md)
- [Pipeline 指南](pipeline-guide.md)
