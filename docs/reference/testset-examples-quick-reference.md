# 测试集示例快速参考

## 快速选择指南

### 我想测试...

| 测试场景 | 推荐文件 | 用例数 |
|---------|---------|--------|
| 情感分析 | `simple_sentiment_analysis.jsonl` | 10 |
| 文本摘要 | `simple_summarization.jsonl` | 5 |
| 批量评论分析 | `simple_batch_reviews.jsonl` | 6 |
| 文本处理流程 | `simple_text_processing_pipeline.jsonl` | 10 |
| 复杂场景 | `pipeline_complex_scenarios.jsonl` | 5 |

## 按特性选择

### 简单测试（单步骤）

```bash
examples/testsets/simple_sentiment_analysis.jsonl
examples/testsets/simple_summarization.jsonl
```

**特点**:
- 单一输入输出
- 适合 Agent 单元测试
- 快速验证基础功能

### 批量处理测试

```bash
examples/testsets/simple_batch_reviews.jsonl
examples/testsets/batch_processing_demo.jsonl
examples/testsets/pipeline_batch_aggregation_examples.jsonl
```

**特点**:
- 批量数据处理
- 聚合策略（concat, stats, filter, custom）
- 并发执行

### 多阶段评估测试

```bash
examples/testsets/simple_text_processing_pipeline.jsonl
examples/testsets/pipeline_multi_step_examples.jsonl
examples/testsets/pipeline_intermediate_evaluation_examples.jsonl
```

**特点**:
- 中间步骤验证
- 数据流跟踪
- 调试友好

## 快速命令

### 运行简单测试

```bash
# 情感分析
python -m src.run_eval \
  --agent sentiment_analyzer \
  --testset examples/testsets/simple_sentiment_analysis.jsonl

# 文本摘要
python -m src.run_eval \
  --agent summarizer \
  --testset examples/testsets/simple_summarization.jsonl
```

### 运行批量测试

```bash
# 批量评论分析
python -m src.run_eval \
  --pipeline review_analysis \
  --testset examples/testsets/simple_batch_reviews.jsonl
```

### 运行多阶段测试

```bash
# 文本处理 Pipeline
python -m src.run_eval \
  --pipeline text_processing \
  --testset examples/testsets/simple_text_processing_pipeline.jsonl \
  --evaluate-intermediate
```

### 使用标签过滤

```bash
# 只运行关键测试
python -m src.run_eval \
  --agent my_agent \
  --testset examples/testsets/simple_sentiment_analysis.jsonl \
  --tags critical

# 运行特定类型
python -m src.run_eval \
  --agent my_agent \
  --testset examples/testsets/simple_batch_reviews.jsonl \
  --tags batch,positive
```

## 测试集特性对照

| 文件 | 简单 | 批量 | 多步骤 | 中间验证 | 聚合 | 并发 |
|------|:----:|:----:|:------:|:--------:|:----:|:----:|
| `simple_sentiment_analysis.jsonl` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `simple_summarization.jsonl` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `simple_batch_reviews.jsonl` | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ |
| `simple_text_processing_pipeline.jsonl` | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| `batch_processing_demo.jsonl` | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| `pipeline_multi_step_examples.jsonl` | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| `pipeline_batch_aggregation_examples.jsonl` | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| `pipeline_intermediate_evaluation_examples.jsonl` | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| `pipeline_complex_scenarios.jsonl` | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |

## 示例代码片段

### 加载测试集

```python
from src.testset_loader import TestsetLoader

loader = TestsetLoader()
testcases = loader.load_testset("examples/testsets/simple_sentiment_analysis.jsonl")
```

### 按标签过滤

```python
# 只加载关键测试
critical_tests = loader.load_testset(
    "examples/testsets/simple_sentiment_analysis.jsonl",
    tags=["critical"]
)
```

### 运行测试

```python
from src.pipeline_runner import PipelineRunner

runner = PipelineRunner(pipeline_config)
results = runner.run_batch(testcases)
```

### 评估结果

```python
from src.unified_evaluator import UnifiedEvaluator

evaluator = UnifiedEvaluator()
evaluation = evaluator.evaluate_batch(results, testcases)
print(f"Pass rate: {evaluation['pass_rate']}")
```

## 常见标签

### 功能标签
- `sentiment` - 情感分析
- `summarization` - 文本摘要
- `translation` - 翻译
- `extraction` - 信息提取

### 类型标签
- `simple` - 简单测试
- `batch` - 批量处理
- `multi-step` - 多步骤
- `integration` - 集成测试

### 优先级标签
- `critical` - 关键测试
- `important` - 重要测试
- `optional` - 可选测试

### 场景标签
- `edge` - 边界情况
- `error` - 错误处理
- `performance` - 性能测试

## 创建自己的测试集

### 1. 从模板开始

```jsonl
{"id": "test_1", "inputs": {"text": "test"}, "expected_outputs": {"result": "expected"}}
```

### 2. 添加标签和配置

```jsonl
{
  "id": "test_1",
  "tags": ["critical", "basic"],
  "inputs": {"text": "test"},
  "expected_outputs": {"result": "expected"},
  "evaluation_config": {"strict_mode": false}
}
```

### 3. 添加批量处理

```jsonl
{
  "id": "batch_test",
  "batch_items": [{"item": 1}, {"item": 2}],
  "expected_aggregation": {"count": 2}
}
```

### 4. 添加中间验证

```jsonl
{
  "id": "multi_step_test",
  "inputs": {"data": "input"},
  "intermediate_expectations": {
    "step1": {"output": "intermediate"}
  },
  "expected_outputs": {"result": "final"},
  "evaluation_config": {"evaluate_intermediate": true}
}
```

## 相关文档

- [Testset Creation Guide](../guides/testset-creation-guide.md) - 完整创建指南
- [Pipeline Testset Format Specification](./pipeline-testset-format-specification.md) - 格式规范
- [Testset Loader Quick Reference](./testset-loader-quick-reference.md) - 加载器参考
- [Batch Processing Guide](./batch-processing-config-guide.md) - 批量处理指南
- [Pipeline Evaluation Guide](./pipeline-evaluation-guide.md) - 评估指南

## 故障排查

### 问题: 测试加载失败

```bash
# 验证 JSON 格式
python -c "import json; [json.loads(line) for line in open('testset.jsonl')]"
```

### 问题: 所有测试都失败

检查评估配置：
```jsonl
{
  "evaluation_config": {
    "strict_mode": false,
    "tolerance": 0.05,
    "ignore_fields": ["timestamp"]
  }
}
```

### 问题: 批量处理不工作

确保 Pipeline 配置支持批量处理：
```yaml
steps:
  - id: process
    batch_mode: true
    batch_size: 10
```

---

**最后更新**: 2024-01-17
**版本**: 1.0.0
