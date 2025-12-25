# Pipeline 测试集创建指南

## 概述

本指南提供了创建 Pipeline 级别测试集的完整说明，包括最佳实践、示例和常见模式。无论您是创建简单的单步骤测试还是复杂的多阶段批量处理测试，本指南都能帮助您快速上手。

## 目录

1. [快速开始](#快速开始)
2. [测试集类型](#测试集类型)
3. [创建简单测试集](#创建简单测试集)
4. [创建批量处理测试集](#创建批量处理测试集)
5. [创建多阶段评估测试集](#创建多阶段评估测试集)
6. [最佳实践](#最佳实践)
7. [常见模式](#常见模式)
8. [故障排查](#故障排查)

## 快速开始

### 最简单的测试用例

创建一个 JSONL 文件（例如 `my_testset.jsonl`），每行一个测试用例：

```jsonl
{"id": "test_1", "inputs": {"text": "Hello world"}, "expected_outputs": {"result": "processed"}}
```

### 运行测试

```bash
# 使用 CLI
python -m src.run_eval --agent my_agent --testset my_testset.jsonl

# 使用 Python API
from src.testset_loader import TestsetLoader
from src.pipeline_runner import PipelineRunner

loader = TestsetLoader()
testcases = loader.load_testset("my_testset.jsonl")
runner = PipelineRunner(pipeline_config)
results = runner.run_batch(testcases)
```

## 测试集类型

### 1. 简单测试集

**用途**: 单步骤 Agent 或简单 Pipeline 测试

**特点**:
- 单一输入
- 单一输出
- 无中间步骤验证

**示例**:
```jsonl
{"id": "sentiment_positive", "inputs": {"text": "I love this!"}, "expected_outputs": {"sentiment": "positive"}}
{"id": "sentiment_negative", "inputs": {"text": "This is terrible"}, "expected_outputs": {"sentiment": "negative"}}
```

### 2. 多步骤测试集

**用途**: 复杂 Pipeline，需要验证中间步骤

**特点**:
- 多个步骤
- 步骤级输入
- 中间结果验证

**示例**:
```jsonl
{
  "id": "multi_step_1",
  "inputs": {"text": "Raw input"},
  "step_inputs": {
    "preprocess": {"mode": "strict"},
    "analyze": {"depth": "deep"}
  },
  "intermediate_expectations": {
    "preprocess": {"cleaned": "raw input"}
  },
  "expected_outputs": {"result": "final"}
}
```

### 3. 批量处理测试集

**用途**: 测试批量数据处理和聚合

**特点**:
- 多个输入项
- 批量处理
- 聚合结果验证

**示例**:
```jsonl
{
  "id": "batch_1",
  "batch_items": [
    {"text": "Item 1"},
    {"text": "Item 2"}
  ],
  "expected_aggregation": {"count": 2},
  "expected_outputs": {"summary": "processed"}
}
```

## 创建简单测试集

### 步骤 1: 确定测试目标

明确您要测试什么：
- 功能正确性？
- 边界情况？
- 错误处理？
- 性能基准？

### 步骤 2: 准备测试数据

收集或创建测试输入：
- 典型案例
- 边界案例
- 错误案例

### 步骤 3: 定义预期输出

为每个输入定义预期结果：
- 精确匹配（严格模式）
- 部分匹配（宽松模式）
- 关键字段验证

### 步骤 4: 创建 JSONL 文件

```jsonl
{"id": "test_typical", "inputs": {"text": "Normal input"}, "expected_outputs": {"result": "expected"}}
{"id": "test_edge_empty", "inputs": {"text": ""}, "expected_outputs": {"error": "empty_input"}}
{"id": "test_edge_long", "inputs": {"text": "Very long text..."}, "expected_outputs": {"result": "truncated"}}
```

### 完整示例: 情感分析测试集

创建文件 `examples/testsets/simple_sentiment_analysis.jsonl`:

```jsonl
{"id": "positive_basic", "tags": ["sentiment", "positive"], "inputs": {"text": "I love this product!"}, "expected_outputs": {"sentiment": "positive", "confidence": 0.9}}
{"id": "negative_basic", "tags": ["sentiment", "negative"], "inputs": {"text": "This is terrible"}, "expected_outputs": {"sentiment": "negative", "confidence": 0.85}}
{"id": "neutral_basic", "tags": ["sentiment", "neutral"], "inputs": {"text": "It's okay"}, "expected_outputs": {"sentiment": "neutral", "confidence": 0.6}}
{"id": "positive_strong", "tags": ["sentiment", "positive", "strong"], "inputs": {"text": "Absolutely amazing! Best purchase ever!"}, "expected_outputs": {"sentiment": "positive", "confidence": 0.95}}
{"id": "negative_strong", "tags": ["sentiment", "negative", "strong"], "inputs": {"text": "Worst experience ever. Complete waste of money."}, "expected_outputs": {"sentiment": "negative", "confidence": 0.95}}
{"id": "mixed_sentiment", "tags": ["sentiment", "mixed"], "inputs": {"text": "Good quality but too expensive"}, "expected_outputs": {"sentiment": "mixed"}}
{"id": "edge_empty", "tags": ["edge", "error"], "inputs": {"text": ""}, "expected_outputs": {"error": "empty_input"}}
{"id": "edge_very_short", "tags": ["edge"], "inputs": {"text": "OK"}, "expected_outputs": {"sentiment": "neutral"}}
```

## 创建批量处理测试集

### 何时使用批量处理测试

- 测试批量数据处理功能
- 验证聚合逻辑
- 测试并发处理
- 性能测试

### 批量测试集结构

```jsonl
{
  "id": "unique_id",
  "tags": ["batch", "aggregation"],
  "batch_items": [
    {"item_data": "..."},
    {"item_data": "..."}
  ],
  "step_inputs": {
    "process_batch": {"batch_size": 10},
    "aggregate": {"strategy": "stats"}
  },
  "expected_aggregation": {
    "total": 2,
    "summary": "..."
  },
  "expected_outputs": {
    "final_result": "..."
  }
}
```

### 聚合策略

#### 1. Concat (拼接)

将所有结果拼接成一个字符串：

```jsonl
{
  "id": "batch_concat",
  "batch_items": [
    {"text": "First"},
    {"text": "Second"},
    {"text": "Third"}
  ],
  "step_inputs": {
    "aggregate": {
      "strategy": "concat",
      "separator": " | "
    }
  },
  "expected_aggregation": {
    "concatenated": "First | Second | Third"
  }
}
```

#### 2. Stats (统计)

计算统计信息：

```jsonl
{
  "id": "batch_stats",
  "batch_items": [
    {"score": 8.5},
    {"score": 7.2},
    {"score": 9.1}
  ],
  "step_inputs": {
    "aggregate": {
      "strategy": "stats",
      "fields": ["score"]
    }
  },
  "expected_aggregation": {
    "count": 3,
    "average": 8.27,
    "max": 9.1,
    "min": 7.2
  },
  "evaluation_config": {
    "tolerance": 0.01
  }
}
```

#### 3. Filter (过滤)

根据条件过滤结果：

```jsonl
{
  "id": "batch_filter",
  "batch_items": [
    {"rating": 5, "verified": true},
    {"rating": 2, "verified": false},
    {"rating": 4, "verified": true}
  ],
  "step_inputs": {
    "aggregate": {
      "strategy": "filter",
      "condition": "verified == true and rating >= 4"
    }
  },
  "expected_aggregation": {
    "filtered_count": 2
  }
}
```

#### 4. Custom (自定义)

使用自定义代码聚合：

```jsonl
{
  "id": "batch_custom",
  "batch_items": [
    {"product": "A", "sales": 100},
    {"product": "B", "sales": 150}
  ],
  "step_inputs": {
    "aggregate": {
      "strategy": "custom",
      "code": "def aggregate(items): return {'total_sales': sum(i['sales'] for i in items), 'best_product': max(items, key=lambda x: x['sales'])['product']}"
    }
  },
  "expected_aggregation": {
    "total_sales": 250,
    "best_product": "B"
  }
}
```

### 完整示例: 客户评论批量分析

创建文件 `examples/testsets/simple_batch_reviews.jsonl`:

```jsonl
{
  "id": "batch_reviews_basic",
  "tags": ["batch", "reviews", "sentiment"],
  "batch_items": [
    {"review": "Excellent product!", "rating": 5},
    {"review": "Not satisfied", "rating": 2},
    {"review": "Good value", "rating": 4},
    {"review": "Poor quality", "rating": 1},
    {"review": "Highly recommend", "rating": 5}
  ],
  "step_inputs": {
    "analyze_sentiment": {
      "batch_size": 5,
      "concurrent": true
    },
    "aggregate_results": {
      "strategy": "stats",
      "fields": ["rating"]
    }
  },
  "expected_aggregation": {
    "total_reviews": 5,
    "average_rating": 3.4,
    "positive_count": 2,
    "negative_count": 2,
    "neutral_count": 1
  },
  "expected_outputs": {
    "overall_sentiment": "mixed",
    "recommendation": "improve_quality"
  },
  "evaluation_config": {
    "tolerance": 0.1,
    "strict_mode": false
  }
}
```

## 创建多阶段评估测试集

### 何时使用多阶段评估

- 调试复杂 Pipeline
- 验证数据流转
- 确保每个步骤正确
- 性能分析

### 多阶段测试集结构

```jsonl
{
  "id": "unique_id",
  "tags": ["multi-stage", "evaluation"],
  "inputs": {"initial": "data"},
  "step_inputs": {
    "step1": {"param": "value"},
    "step2": {"param": "value"}
  },
  "intermediate_expectations": {
    "step1": {"output": "expected"},
    "step2": {"output": "expected"}
  },
  "expected_outputs": {"final": "result"},
  "evaluation_config": {
    "evaluate_intermediate": true
  }
}
```

### 中间步骤验证

#### 验证数据转换

```jsonl
{
  "id": "data_transform",
  "inputs": {"text": "Hello World"},
  "step_inputs": {
    "lowercase": {},
    "remove_spaces": {},
    "reverse": {}
  },
  "intermediate_expectations": {
    "lowercase": {"text": "hello world"},
    "remove_spaces": {"text": "helloworld"},
    "reverse": {"text": "dlrowolleh"}
  },
  "expected_outputs": {"text": "dlrowolleh"}
}
```

#### 验证数据流

```jsonl
{
  "id": "data_flow",
  "inputs": {"users": [{"id": 1, "name": "Alice"}]},
  "step_inputs": {
    "extract_ids": {},
    "fetch_details": {},
    "enrich_data": {}
  },
  "intermediate_expectations": {
    "extract_ids": {"ids": [1]},
    "fetch_details": {"details": [{"id": 1, "email": "alice@example.com"}]},
    "enrich_data": {"enriched": [{"id": 1, "name": "Alice", "email": "alice@example.com"}]}
  },
  "expected_outputs": {"count": 1}
}
```

### 完整示例: 文本处理 Pipeline

创建文件 `examples/testsets/simple_text_processing_pipeline.jsonl`:

```jsonl
{
  "id": "text_processing_complete",
  "tags": ["multi-stage", "text-processing", "nlp"],
  "inputs": {
    "text": "This is a Sample Text for Processing! It has multiple sentences."
  },
  "step_inputs": {
    "normalize": {
      "lowercase": true,
      "remove_punctuation": true
    },
    "tokenize": {
      "method": "word"
    },
    "remove_stopwords": {
      "language": "en"
    },
    "stem": {
      "algorithm": "porter"
    },
    "count_tokens": {}
  },
  "intermediate_expectations": {
    "normalize": {
      "text": "this is a sample text for processing it has multiple sentences"
    },
    "tokenize": {
      "tokens": ["this", "is", "a", "sample", "text", "for", "processing", "it", "has", "multiple", "sentences"],
      "count": 11
    },
    "remove_stopwords": {
      "tokens": ["sample", "text", "processing", "multiple", "sentences"],
      "count": 5
    },
    "stem": {
      "tokens": ["sampl", "text", "process", "multipl", "sentenc"],
      "count": 5
    }
  },
  "expected_outputs": {
    "final_tokens": ["sampl", "text", "process", "multipl", "sentenc"],
    "token_count": 5,
    "unique_tokens": 5
  },
  "evaluation_config": {
    "evaluate_intermediate": true,
    "strict_mode": false
  }
}
```

## 最佳实践

### 1. 命名约定

#### 测试用例 ID

使用描述性名称：

```
✅ 好的命名:
- "sentiment_positive_basic"
- "batch_reviews_large_dataset"
- "multi_step_with_error_handling"

❌ 不好的命名:
- "test1"
- "t"
- "abc123"
```

#### 标签使用

使用一致的标签体系：

```jsonl
{
  "tags": [
    "sentiment",        // 功能
    "batch",           // 类型
    "integration",     // 测试级别
    "critical"         // 优先级
  ]
}
```

### 2. 数据质量

#### 使用真实数据

```jsonl
✅ 好的数据:
{"text": "I love this product! It works great and exceeded my expectations."}

❌ 不好的数据:
{"text": "test test test"}
```

#### 覆盖边界情况

```jsonl
{"id": "edge_empty", "inputs": {"text": ""}}
{"id": "edge_very_long", "inputs": {"text": "Very long text..." * 1000}}
{"id": "edge_special_chars", "inputs": {"text": "!@#$%^&*()"}}
{"id": "edge_unicode", "inputs": {"text": "你好世界 🌍"}}
```

### 3. 预期结果定义

#### 使用宽松模式处理 LLM 输出

```jsonl
{
  "expected_outputs": {
    "sentiment": "positive",
    "summary": "customer satisfaction"
  },
  "evaluation_config": {
    "strict_mode": false,
    "ignore_fields": ["timestamp", "request_id"]
  }
}
```

#### 使用容差处理数值

```jsonl
{
  "expected_outputs": {
    "confidence": 0.85
  },
  "evaluation_config": {
    "tolerance": 0.05
  }
}
```

### 4. 文件组织

```
testsets/
├── unit/
│   ├── sentiment_basic.jsonl          # 基础功能测试
│   └── summarization_basic.jsonl
├── integration/
│   ├── pipeline_multi_step.jsonl      # 集成测试
│   └── pipeline_with_batch.jsonl
├── performance/
│   └── batch_large_dataset.jsonl      # 性能测试
└── regression/
    └── bug_fixes.jsonl                # 回归测试
```

### 5. 版本控制

在文件名中包含版本：

```
sentiment_analysis_v1.jsonl
sentiment_analysis_v2.jsonl
```

或在测试用例中添加版本标签：

```jsonl
{"id": "test_1", "tags": ["v2", "updated"], ...}
```

## 常见模式

### 模式 1: 参数化测试

测试不同参数组合：

```jsonl
{"id": "param_1", "inputs": {"text": "test", "mode": "strict"}, "expected_outputs": {"result": "A"}}
{"id": "param_2", "inputs": {"text": "test", "mode": "lenient"}, "expected_outputs": {"result": "B"}}
{"id": "param_3", "inputs": {"text": "test", "mode": "auto"}, "expected_outputs": {"result": "C"}}
```

### 模式 2: 错误处理测试

```jsonl
{"id": "error_empty", "inputs": {"text": ""}, "expected_outputs": {"error": "empty_input", "status": "failed"}}
{"id": "error_invalid", "inputs": {"text": null}, "expected_outputs": {"error": "invalid_input", "status": "failed"}}
{"id": "error_timeout", "inputs": {"text": "very long..."}, "step_inputs": {"process": {"timeout": 1}}, "expected_outputs": {"error": "timeout", "status": "failed"}}
```

### 模式 3: 性能基准

```jsonl
{
  "id": "perf_small",
  "tags": ["performance", "baseline"],
  "batch_items": [{"text": "item"} for i in range(10)],
  "expected_outputs": {"processing_time_ms": 1000},
  "evaluation_config": {"ignore_fields": ["processing_time_ms"]}
}
```

### 模式 4: A/B 测试

```jsonl
{"id": "ab_model_a", "tags": ["ab-test", "model-a"], "inputs": {"text": "test"}, "step_inputs": {"analyze": {"model": "model_a"}}, "expected_outputs": {"result": "..."}}
{"id": "ab_model_b", "tags": ["ab-test", "model-b"], "inputs": {"text": "test"}, "step_inputs": {"analyze": {"model": "model_b"}}, "expected_outputs": {"result": "..."}}
```

### 模式 5: 回归测试

```jsonl
{
  "id": "regression_bug_123",
  "tags": ["regression", "bug-fix", "issue-123"],
  "inputs": {"text": "specific input that caused bug"},
  "expected_outputs": {"result": "correct output after fix"},
  "evaluation_config": {"strict_mode": true}
}
```

## 故障排查

### 问题 1: 测试用例加载失败

**症状**: `JSONDecodeError` 或 `Invalid format`

**解决方案**:
1. 检查 JSON 格式是否正确
2. 确保每行是完整的 JSON 对象
3. 检查是否有多余的逗号或括号

```bash
# 验证 JSON 格式
python -c "import json; [json.loads(line) for line in open('testset.jsonl')]"
```

### 问题 2: 评估失败

**症状**: 所有测试都失败，但输出看起来正确

**解决方案**:
1. 使用宽松模式: `"strict_mode": false`
2. 添加容差: `"tolerance": 0.1`
3. 忽略不重要的字段: `"ignore_fields": ["timestamp"]`

### 问题 3: 批量处理不工作

**症状**: `batch_items` 没有被处理

**解决方案**:
1. 确保 Pipeline 配置支持批量处理
2. 检查 `batch_mode: true` 是否设置
3. 验证聚合步骤配置

### 问题 4: 中间步骤验证失败

**症状**: 中间步骤输出与预期不符

**解决方案**:
1. 启用详细日志: `"evaluate_intermediate": true`
2. 检查步骤 ID 是否匹配 Pipeline 配置
3. 使用宽松模式进行初步验证

### 问题 5: 性能问题

**症状**: 测试运行很慢

**解决方案**:
1. 启用并发处理: `"concurrent": true`
2. 调整批量大小: `"batch_size": 10`
3. 使用标签过滤运行部分测试

```bash
# 只运行特定标签的测试
python -m src.run_eval --agent my_agent --testset testset.jsonl --tags critical
```

## 示例文件参考

### 简单测试集示例

- `examples/testsets/simple_sentiment_analysis.jsonl`
- `examples/testsets/simple_summarization.jsonl`
- `examples/testsets/simple_translation.jsonl`

### 批量处理示例

- `examples/testsets/simple_batch_reviews.jsonl`
- `examples/testsets/batch_processing_demo.jsonl`
- `examples/testsets/pipeline_batch_aggregation_examples.jsonl`

### 多阶段评估示例

- `examples/testsets/simple_text_processing_pipeline.jsonl`
- `examples/testsets/pipeline_multi_step_examples.jsonl`
- `examples/testsets/pipeline_intermediate_evaluation_examples.jsonl`

### 复杂场景示例

- `examples/testsets/pipeline_complex_scenarios.jsonl`

## 下一步

1. 阅读 [Pipeline Testset Format Specification](../reference/pipeline-testset-format-specification.md)
2. 查看 [Testset Loader Quick Reference](../reference/testset-loader-quick-reference.md)
3. 探索 [Batch Processing Guide](../reference/batch-processing-config-guide.md)
4. 学习 [Pipeline Evaluation Guide](../reference/pipeline-evaluation-guide.md)

## 获取帮助

如果您遇到问题或有疑问：

1. 查看 [故障排查](#故障排查) 部分
2. 参考示例文件
3. 查看相关文档
4. 联系开发团队

---

**最后更新**: 2024-01-17
**版本**: 1.0.0
