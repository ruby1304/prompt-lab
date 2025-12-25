# Pipeline 评估快速参考

## 评估模式

| 模式 | 用途 | 测试用例字段 |
|------|------|-------------|
| 最终输出评估 | 评估 Pipeline 最终输出 | `expected_outputs` |
| 中间步骤评估 | 评估中间步骤输出 | `intermediate_expectations` |
| 聚合结果评估 | 评估批量聚合结果 | `expected_aggregation` |

## 测试用例格式

### 基本格式

```jsonl
{
  "id": "test_1",
  "inputs": {"text": "Input"},
  "expected_outputs": {"output": "Expected"}
}
```

### 中间步骤评估

```jsonl
{
  "id": "test_1",
  "inputs": {"text": "Input"},
  "intermediate_expectations": {
    "step1": {"status": "success"},
    "step2": {"count": 5}
  },
  "expected_outputs": {"output": "Expected"}
}
```

### 聚合评估

```jsonl
{
  "id": "test_1",
  "inputs": {"text": "Input"},
  "batch_items": [{"text": "Item 1"}, {"text": "Item 2"}],
  "expected_aggregation": {"total": 2, "success_count": 2},
  "expected_outputs": {"output": "Expected"}
}
```

## 匹配模式

| 模式 | 语法 | 示例 |
|------|------|------|
| 完全匹配 | 直接值 | `{"status": "success"}` |
| 包含匹配 | `contains:text` | `{"message": "contains:success"}` |
| 正则匹配 | `regex:pattern` | `{"phone": "regex:\\d{3}-\\d{4}"}` |
| 部分匹配 | 子集 | 实际可包含更多字段 |

## API 使用

### 评估中间步骤

```python
from src.unified_evaluator import UnifiedEvaluator
from src.models import EvaluationConfig

config = EvaluationConfig(judge_enabled=False, rules=[])
evaluator = UnifiedEvaluator(config)

results = evaluator.evaluate_intermediate_steps(
    pipeline_id='my_pipeline',
    variant='v1',
    test_case={'intermediate_expectations': {...}},
    step_outputs={...}
)
```

### 评估聚合结果

```python
result = evaluator.evaluate_aggregation_result(
    pipeline_id='my_pipeline',
    variant='v1',
    test_case={'expected_aggregation': {...}},
    aggregation_output={...}
)
```

### 完整 Pipeline 评估

```python
result = evaluator.evaluate_pipeline_output(
    pipeline_id='my_pipeline',
    variant='v1',
    test_case={...},
    step_outputs={...},
    final_output='...',
    evaluate_intermediate=True,
    evaluate_aggregation=True
)
```

### 使用 PipelineEvaluator

```python
from src.pipeline_eval import PipelineEvaluator
from src.pipeline_config import load_pipeline_config

pipeline_config = load_pipeline_config('my_pipeline')
evaluator = PipelineEvaluator(pipeline_config)

result = evaluator.evaluate_pipeline(
    samples=[...],
    variant='v1',
    apply_rules=True,
    apply_judge=True
)
```

## 评估结果

```python
{
    'sample_id': 'test_1',
    'overall_score': 8.5,
    'must_have_pass': True,
    'judge_feedback': '...',
    'step_outputs': {
        '_intermediate_evaluation': {
            'step1': {
                'matched': True,
                'expected': {...},
                'actual': {...},
                'details': '...'
            }
        },
        '_aggregation_evaluation': {
            'matched': True,
            'expected': {...},
            'actual': {...},
            'details': '...'
        }
    }
}
```

## 常用命令

### 运行评估

```bash
# 使用 Python API
python -c "
from src.pipeline_eval import PipelineEvaluator
from src.pipeline_config import load_pipeline_config
from src.testset_loader import TestsetLoader

config = load_pipeline_config('my_pipeline')
evaluator = PipelineEvaluator(config)
samples = TestsetLoader.load_from_file('testset.jsonl')
result = evaluator.evaluate_pipeline(samples, 'v1')
print(result.overall_stats)
"
```

### 查看评估结果

```bash
# 查看评估结果文件
cat data/pipelines/my_pipeline/evals/my_pipeline_v1_*.eval.csv
```

## 配置选项

### Pipeline 配置

```yaml
# pipeline.yaml
id: my_pipeline
name: My Pipeline
steps: [...]
evaluation_target: step2  # 指定评估目标步骤
```

### 评估配置

```python
EvaluationConfig(
    judge_enabled=True,
    judge_agent_id='judge_default',
    judge_flow='judge_v1',
    rules=[...]
)
```

## 最佳实践

1. **渐进式评估** - 从简单到复杂
2. **使用包含匹配** - 减少测试脆性
3. **只验证关键字段** - 避免过度验证
4. **组合规则和 Judge** - 结构化 + 语义评估

## 相关文档

- [Pipeline 评估指南](pipeline-evaluation-guide.md)
- [Pipeline 测试集格式](pipeline-testset-format-specification.md)
- [批量处理配置](batch-processing-config-guide.md)
