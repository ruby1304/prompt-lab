# Pipeline 评估指南

本指南介绍如何使用增强的 Pipeline 评估功能，包括最终输出评估、中间步骤评估和批量聚合结果评估。

## 概述

Pipeline 评估系统现在支持三种评估模式：

1. **最终输出评估** - 评估 Pipeline 的最终输出结果
2. **中间步骤评估** - 评估 Pipeline 中间步骤的输出
3. **批量聚合结果评估** - 评估批量处理后的聚合结果

## 最终输出评估

最终输出评估是默认的评估模式，评估 Pipeline 的最终输出结果。

### 配置示例

```yaml
# pipeline.yaml
id: my_pipeline
name: My Pipeline
steps:
  - id: step1
    agent: processor
    flow: process_v1
    output_key: processed_data
  
  - id: step2
    agent: summarizer
    flow: summarize_v1
    output_key: final_summary

evaluation_target: step2  # 指定评估目标步骤（可选，默认最后一步）
```

### 测试用例示例

```jsonl
{
  "id": "test_1",
  "inputs": {"text": "Input text"},
  "expected_outputs": {
    "final_summary": "Expected summary text"
  }
}
```

## 中间步骤评估

中间步骤评估允许你验证 Pipeline 中间步骤的输出是否符合预期。

### 测试用例格式

在测试用例中添加 `intermediate_expectations` 字段：

```jsonl
{
  "id": "test_1",
  "inputs": {"text": "Input text"},
  "intermediate_expectations": {
    "step1": {
      "status": "success",
      "count": 5
    },
    "step2": {
      "result": "contains:processed"
    }
  },
  "expected_outputs": {
    "final_summary": "Expected summary"
  }
}
```

### 支持的匹配模式

#### 1. 完全匹配

```json
{
  "intermediate_expectations": {
    "step1": {
      "status": "success",
      "count": 5
    }
  }
}
```

实际输出必须包含所有指定的字段，且值完全匹配。

#### 2. 包含匹配

使用 `contains:` 前缀进行文本包含匹配：

```json
{
  "intermediate_expectations": {
    "step1": {
      "message": "contains:success"
    }
  }
}
```

实际输出的 `message` 字段只需包含 "success" 文本即可。

#### 3. 正则表达式匹配

使用 `regex:` 前缀进行正则表达式匹配：

```json
{
  "intermediate_expectations": {
    "step1": {
      "phone": "regex:\\d{3}-\\d{4}"
    }
  }
}
```

#### 4. 部分匹配

实际输出可以包含比预期更多的字段：

```json
// 预期
{
  "intermediate_expectations": {
    "step1": {"status": "success"}
  }
}

// 实际输出（匹配成功）
{
  "step1": {
    "status": "success",
    "timestamp": "2024-01-01",
    "extra_field": "value"
  }
}
```

### 使用示例

```python
from src.unified_evaluator import UnifiedEvaluator
from src.models import EvaluationConfig

# 创建评估器
config = EvaluationConfig(
    judge_enabled=False,
    rules=[]
)
evaluator = UnifiedEvaluator(config)

# 测试用例
test_case = {
    'id': 'test_1',
    'intermediate_expectations': {
        'step1': {'status': 'success'},
        'step2': {'count': 5}
    }
}

# 步骤输出
step_outputs = {
    'step1': {'status': 'success'},
    'step2': {'count': 5},
    'step3': {'final': 'output'}
}

# 执行中间步骤评估
results = evaluator.evaluate_intermediate_steps(
    pipeline_id='my_pipeline',
    variant='v1',
    test_case=test_case,
    step_outputs=step_outputs
)

# 检查结果
for step_id, result in results.items():
    if result['matched']:
        print(f"✓ {step_id}: {result['details']}")
    else:
        print(f"✗ {step_id}: {result['details']}")
```

## 批量聚合结果评估

批量聚合结果评估用于验证批量处理后的聚合结果。

### 测试用例格式

在测试用例中添加 `expected_aggregation` 字段：

```jsonl
{
  "id": "test_1",
  "inputs": {"text": "Input text"},
  "batch_items": [
    {"text": "Item 1"},
    {"text": "Item 2"},
    {"text": "Item 3"}
  ],
  "expected_aggregation": {
    "total_count": 3,
    "success_count": 3,
    "summary": "contains:successful"
  }
}
```

### 聚合结果匹配

聚合结果支持与中间步骤评估相同的匹配模式：

- 完全匹配
- 包含匹配 (`contains:`)
- 正则表达式匹配 (`regex:`)
- 部分匹配

### 使用示例

```python
from src.unified_evaluator import UnifiedEvaluator
from src.models import EvaluationConfig

# 创建评估器
config = EvaluationConfig(
    judge_enabled=False,
    rules=[]
)
evaluator = UnifiedEvaluator(config)

# 测试用例
test_case = {
    'id': 'test_1',
    'expected_aggregation': {
        'total': 10,
        'success_rate': 0.8
    }
}

# 聚合输出
aggregation_output = {
    'total': 10,
    'success_rate': 0.8,
    'details': 'Additional info'
}

# 执行聚合评估
result = evaluator.evaluate_aggregation_result(
    pipeline_id='my_pipeline',
    variant='v1',
    test_case=test_case,
    aggregation_output=aggregation_output
)

# 检查结果
if result['matched']:
    print(f"✓ 聚合评估通过: {result['details']}")
else:
    print(f"✗ 聚合评估失败: {result['details']}")
```

## 完整的 Pipeline 评估

使用 `evaluate_pipeline_output` 方法进行完整的 Pipeline 评估：

```python
from src.unified_evaluator import UnifiedEvaluator
from src.models import EvaluationConfig

# 创建评估器
config = EvaluationConfig(
    judge_enabled=True,
    judge_agent_id='judge_default',
    judge_flow='judge_v1',
    rules=[]
)
evaluator = UnifiedEvaluator(config)

# 测试用例
test_case = {
    'id': 'test_1',
    'inputs': {'text': 'Input text'},
    'intermediate_expectations': {
        'step1': {'status': 'success'}
    },
    'expected_aggregation': {
        'total': 10
    },
    'expected_outputs': {
        'final_output': 'Expected result'
    }
}

# 步骤输出
step_outputs = {
    'step1': {'status': 'success'},
    'aggregated_result': {'total': 10},
    'final_output': 'Actual result'
}

# 执行完整评估
result = evaluator.evaluate_pipeline_output(
    pipeline_id='my_pipeline',
    variant='v1',
    test_case=test_case,
    step_outputs=step_outputs,
    final_output='Actual result',
    execution_time=1.5,
    evaluation_target='final_output',
    evaluate_intermediate=True,  # 启用中间步骤评估
    evaluate_aggregation=True    # 启用聚合评估
)

# 检查评估结果
print(f"Sample ID: {result.sample_id}")
print(f"Overall Score: {result.overall_score}")
print(f"Must-Have Pass: {result.must_have_pass}")
print(f"Judge Feedback: {result.judge_feedback}")

# 检查中间步骤评估结果
if '_intermediate_evaluation' in result.step_outputs:
    intermediate_eval = result.step_outputs['_intermediate_evaluation']
    for step_id, eval_result in intermediate_eval.items():
        print(f"  {step_id}: {'✓' if eval_result['matched'] else '✗'}")

# 检查聚合评估结果
if '_aggregation_evaluation' in result.step_outputs:
    aggregation_eval = result.step_outputs['_aggregation_evaluation']
    print(f"Aggregation: {'✓' if aggregation_eval['matched'] else '✗'}")
```

## 使用 PipelineEvaluator

`PipelineEvaluator` 类会自动检测测试用例中的 `intermediate_expectations` 和 `expected_aggregation` 字段，并启用相应的评估：

```python
from src.pipeline_eval import PipelineEvaluator
from src.pipeline_config import load_pipeline_config

# 加载 Pipeline 配置
pipeline_config = load_pipeline_config('my_pipeline')

# 创建评估器
evaluator = PipelineEvaluator(pipeline_config)

# 测试样本
samples = [
    {
        'id': 'test_1',
        'inputs': {'text': 'Input 1'},
        'intermediate_expectations': {
            'step1': {'status': 'success'}
        },
        'expected_aggregation': {
            'total': 10
        }
    },
    {
        'id': 'test_2',
        'inputs': {'text': 'Input 2'},
        'intermediate_expectations': {
            'step1': {'status': 'success'}
        }
    }
]

# 执行评估
result = evaluator.evaluate_pipeline(
    samples=samples,
    variant='v1',
    apply_rules=True,
    apply_judge=True
)

# 查看结果
print(f"Total Samples: {result.overall_stats['total_samples']}")
print(f"Success Rate: {result.overall_stats['success_rate']:.2%}")
print(f"Average Score: {result.overall_stats['average_score']:.2f}")
```

## 评估结果结构

评估结果包含以下信息：

```python
{
    'sample_id': 'test_1',
    'entity_type': 'pipeline',
    'entity_id': 'my_pipeline',
    'variant': 'v1',
    'overall_score': 8.5,
    'must_have_pass': True,
    'judge_feedback': 'Good output',
    'execution_time': 1.5,
    'step_outputs': {
        'step1': {...},
        'step2': {...},
        '_intermediate_evaluation': {
            'step1': {
                'matched': True,
                'expected': {...},
                'actual': {...},
                'details': '所有字段匹配'
            }
        },
        '_aggregation_evaluation': {
            'matched': True,
            'expected': {...},
            'actual': {...},
            'details': '所有字段匹配'
        }
    },
    'failed_steps': []
}
```

## 最佳实践

### 1. 渐进式评估

从简单的最终输出评估开始，逐步添加中间步骤和聚合评估：

```jsonl
// 第一阶段：只评估最终输出
{"id": "test_1", "inputs": {...}, "expected_outputs": {...}}

// 第二阶段：添加关键中间步骤评估
{"id": "test_1", "inputs": {...}, "intermediate_expectations": {"key_step": {...}}, "expected_outputs": {...}}

// 第三阶段：添加聚合评估
{"id": "test_1", "inputs": {...}, "intermediate_expectations": {...}, "expected_aggregation": {...}, "expected_outputs": {...}}
```

### 2. 使用包含匹配减少脆性

对于可能变化的输出，使用 `contains:` 匹配而不是完全匹配：

```json
{
  "intermediate_expectations": {
    "step1": {
      "message": "contains:success"  // 而不是完全匹配
    }
  }
}
```

### 3. 只验证关键字段

不需要验证所有字段，只验证对业务逻辑重要的字段：

```json
{
  "intermediate_expectations": {
    "step1": {
      "status": "success",
      "count": 5
      // 不验证 timestamp, id 等非关键字段
    }
  }
}
```

### 4. 组合使用规则和 Judge

结合使用规则评估和 LLM Judge 评估：

- 规则评估：验证结构化数据（状态、计数等）
- Judge 评估：验证文本质量和语义

```python
config = EvaluationConfig(
    judge_enabled=True,
    judge_agent_id='judge_default',
    judge_flow='judge_v1',
    rules=[
        RuleConfig(
            name='status_check',
            type='contains',
            field='output',
            value='success'
        )
    ]
)
```

## 故障排查

### 中间步骤评估失败

如果中间步骤评估失败，检查：

1. 步骤 ID 是否正确（与 Pipeline 配置中的 `output_key` 匹配）
2. 预期字段是否存在于实际输出中
3. 数据类型是否匹配

### 聚合评估找不到输出

聚合评估会自动查找包含 "aggregat" 或 "batch" 的输出键。如果找不到，会使用最终输出。

确保聚合步骤的 `output_key` 包含这些关键词：

```yaml
steps:
  - id: aggregate
    type: batch_aggregator
    output_key: aggregated_result  # 包含 "aggregat"
```

## 相关文档

- [Pipeline 测试集格式规范](pipeline-testset-format-specification.md)
- [批量处理配置指南](batch-processing-config-guide.md)
- [统一评估器 API](../ARCHITECTURE.md#unified-evaluator)
