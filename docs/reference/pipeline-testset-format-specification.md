# Pipeline 级别测试集格式规范

## 概述

本文档定义了 Prompt Lab 项目中 Pipeline 级别测试集的完整格式规范。该格式支持复杂的多步骤 Pipeline 测试场景，包括：

- 多步骤测试数据定义
- 步骤级输入数据
- 批量测试数据
- 预期聚合结果
- 中间步骤评估
- 最终输出评估

## 设计原则

1. **向后兼容**: 支持现有的简单测试集格式
2. **渐进增强**: 可以根据需要逐步添加复杂特性
3. **清晰明确**: 字段命名清晰，结构易于理解
4. **灵活扩展**: 支持未来功能的扩展

## 格式版本

当前版本: **v2.0**

- v1.0: 简单格式（所有字段作为输入）
- v2.0: Pipeline 级别格式（支持多步骤、批量处理等）

## 核心数据结构

### TestCase 数据模型

```python
@dataclass
class TestCase:
    """Pipeline 测试用例"""
    
    # 必需字段
    id: str                                    # 测试用例唯一标识符
    
    # 可选字段
    tags: List[str]                            # 标签（用于过滤和分类）
    inputs: Dict[str, Any]                     # 全局输入（Pipeline 初始输入）
    step_inputs: Dict[str, Dict[str, Any]]     # 步骤级输入
    batch_items: Optional[List[Dict[str, Any]]] # 批量处理数据
    expected_outputs: Dict[str, Any]           # 预期输出
    expected_aggregation: Optional[Any]        # 预期聚合结果
    intermediate_expectations: Dict[str, Any]  # 中间步骤预期结果
    evaluation_config: Dict[str, Any]          # 评估配置
```

## 字段详细说明

### 1. id (必需)

测试用例的唯一标识符。

**类型**: `string`

**规则**:
- 必须唯一（在同一测试集中）
- 建议使用描述性名称
- 支持字母、数字、下划线、连字符

**示例**:
```json
"id": "test_sentiment_analysis_basic"
"id": "batch_processing_large_dataset_001"
"id": "multi_step_pipeline_with_aggregation"
```

### 2. tags (可选)

用于分类和过滤测试用例的标签列表。

**类型**: `List[string]`

**默认值**: `[]`

**用途**:
- 按功能分类（如 "sentiment", "summarization"）
- 按复杂度分类（如 "simple", "complex"）
- 按测试类型分类（如 "unit", "integration", "performance"）
- 按优先级分类（如 "critical", "optional"）

**示例**:
```json
"tags": ["sentiment", "batch", "critical"]
"tags": ["multi-step", "aggregation", "integration"]
```

### 3. inputs (可选)

Pipeline 的全局输入数据，作为第一个步骤的初始输入。

**类型**: `Dict[string, Any]`

**默认值**: `{}`

**用途**:
- 提供 Pipeline 的初始输入
- 可以被后续步骤通过 input_mapping 引用
- 支持任意 JSON 可序列化的数据类型

**示例**:
```json
"inputs": {
  "text": "This is a sample text for analysis",
  "language": "en",
  "context": {
    "domain": "customer_service",
    "priority": "high"
  }
}
```

### 4. step_inputs (可选)

为特定步骤提供额外的输入数据。

**类型**: `Dict[string, Dict[string, Any]]`

**默认值**: `{}`

**结构**: `{step_id: {input_key: input_value}}`

**用途**:
- 为不同步骤提供不同的配置参数
- 覆盖或补充全局输入
- 支持步骤级的测试数据定义

**示例**:
```json
"step_inputs": {
  "preprocess": {
    "mode": "strict",
    "remove_stopwords": true
  },
  "analyze": {
    "depth": "deep",
    "include_entities": true
  },
  "generate_report": {
    "format": "json",
    "include_metadata": true
  }
}
```

### 5. batch_items (可选)

批量处理步骤的输入数据列表。

**类型**: `List[Dict[string, Any]]`

**默认值**: `null`

**用途**:
- 为批量处理步骤提供多个输入项
- 每个项都会被独立处理
- 结果会被聚合后传递给下一步骤

**示例**:
```json
"batch_items": [
  {"text": "Great product!", "rating": 5},
  {"text": "Poor quality", "rating": 2},
  {"text": "Average experience", "rating": 3},
  {"text": "Excellent service", "rating": 5}
]
```

### 6. expected_outputs (可选)

Pipeline 最终输出的预期结果。

**类型**: `Dict[string, Any]`

**默认值**: `{}`

**用途**:
- 定义 Pipeline 最终输出的预期值
- 用于自动化评估
- 支持部分匹配（只验证指定的字段）

**示例**:
```json
"expected_outputs": {
  "sentiment": "positive",
  "confidence": 0.95,
  "summary": "Customer is satisfied with the product"
}
```

### 7. expected_aggregation (可选)

批量处理聚合步骤的预期结果。

**类型**: `Any` (通常是 `Dict` 或 `List`)

**默认值**: `null`

**用途**:
- 定义批量聚合的预期结果
- 验证聚合逻辑的正确性
- 支持复杂的聚合结果结构

**示例**:
```json
"expected_aggregation": {
  "total_items": 4,
  "positive_count": 2,
  "negative_count": 1,
  "neutral_count": 1,
  "average_rating": 3.75,
  "sentiment_distribution": {
    "positive": 0.5,
    "negative": 0.25,
    "neutral": 0.25
  }
}
```

### 8. intermediate_expectations (可选，新增)

中间步骤的预期输出，用于验证 Pipeline 中间状态。

**类型**: `Dict[string, Any]`

**默认值**: `{}`

**结构**: `{step_id: expected_output}`

**用途**:
- 验证中间步骤的输出
- 调试 Pipeline 问题
- 确保每个步骤都按预期工作

**示例**:
```json
"intermediate_expectations": {
  "preprocess": {
    "cleaned_text": "sample text analysis",
    "token_count": 3
  },
  "analyze": {
    "sentiment_score": 0.8,
    "entities": ["sample", "text"]
  }
}
```

### 9. evaluation_config (可选，新增)

评估配置，控制如何评估测试结果。

**类型**: `Dict[string, Any]`

**默认值**: `{}`

**支持的配置**:
- `evaluate_intermediate`: 是否评估中间步骤（默认 false）
- `evaluate_final`: 是否评估最终输出（默认 true）
- `evaluate_aggregation`: 是否评估聚合结果（默认 true，如果有 expected_aggregation）
- `strict_mode`: 严格模式（完全匹配）或宽松模式（部分匹配）
- `tolerance`: 数值比较的容差
- `ignore_fields`: 评估时忽略的字段列表

**示例**:
```json
"evaluation_config": {
  "evaluate_intermediate": true,
  "strict_mode": false,
  "tolerance": 0.01,
  "ignore_fields": ["timestamp", "request_id"]
}
```

## 测试集格式示例

### 示例 1: 简单格式（向后兼容）

```jsonl
{"id": "simple_1", "text": "This is a test", "expected_output": "processed"}
```

等价于:
```jsonl
{"id": "simple_1", "inputs": {"text": "This is a test"}, "expected_outputs": {"output": "processed"}}
```

### 示例 2: 多步骤 Pipeline 测试

```jsonl
{
  "id": "multi_step_sentiment_analysis",
  "tags": ["sentiment", "multi-step"],
  "inputs": {
    "text": "I love this product! It's amazing and works perfectly."
  },
  "step_inputs": {
    "preprocess": {
      "lowercase": true,
      "remove_punctuation": false
    },
    "analyze_sentiment": {
      "model": "advanced",
      "include_confidence": true
    },
    "generate_summary": {
      "max_length": 50
    }
  },
  "intermediate_expectations": {
    "preprocess": {
      "cleaned_text": "i love this product its amazing and works perfectly"
    },
    "analyze_sentiment": {
      "sentiment": "positive",
      "confidence": 0.95
    }
  },
  "expected_outputs": {
    "sentiment": "positive",
    "summary": "Customer expresses strong satisfaction"
  },
  "evaluation_config": {
    "evaluate_intermediate": true,
    "strict_mode": false
  }
}
```

### 示例 3: 批量处理测试

```jsonl
{
  "id": "batch_customer_reviews",
  "tags": ["batch", "sentiment", "aggregation"],
  "batch_items": [
    {"review": "Excellent product!", "rating": 5},
    {"review": "Not satisfied", "rating": 2},
    {"review": "Good value", "rating": 4},
    {"review": "Poor quality", "rating": 1},
    {"review": "Highly recommend", "rating": 5}
  ],
  "step_inputs": {
    "analyze_batch": {
      "batch_size": 5,
      "concurrent": true
    },
    "aggregate_results": {
      "strategy": "stats",
      "include_distribution": true
    }
  },
  "expected_aggregation": {
    "total_reviews": 5,
    "average_rating": 3.4,
    "sentiment_distribution": {
      "positive": 2,
      "negative": 2,
      "neutral": 1
    },
    "recommendation_rate": 0.4
  },
  "expected_outputs": {
    "overall_sentiment": "mixed",
    "key_insights": ["Quality concerns", "High satisfaction from some users"]
  }
}
```

### 示例 4: 复杂 Pipeline（多步骤 + 批量 + 聚合）

```jsonl
{
  "id": "complex_pipeline_full_features",
  "tags": ["complex", "multi-step", "batch", "aggregation"],
  "inputs": {
    "dataset_id": "customer_feedback_2024_q1",
    "analysis_type": "comprehensive"
  },
  "step_inputs": {
    "load_data": {
      "source": "database",
      "filters": {"date_range": "2024-01-01 to 2024-03-31"}
    },
    "preprocess_batch": {
      "normalize": true,
      "remove_duplicates": true
    },
    "analyze_sentiment": {
      "model": "doubao-pro",
      "batch_size": 10
    },
    "extract_topics": {
      "num_topics": 5,
      "method": "lda"
    },
    "aggregate_insights": {
      "strategy": "custom",
      "code": "def aggregate(items): return {'summary': analyze(items)}"
    },
    "generate_report": {
      "format": "executive_summary",
      "include_charts": true
    }
  },
  "batch_items": [
    {"feedback": "Great service", "category": "service"},
    {"feedback": "Fast delivery", "category": "logistics"},
    {"feedback": "Quality product", "category": "product"}
  ],
  "intermediate_expectations": {
    "preprocess_batch": {
      "items_processed": 3,
      "duplicates_removed": 0
    },
    "analyze_sentiment": {
      "positive_count": 3,
      "negative_count": 0
    }
  },
  "expected_aggregation": {
    "total_feedback": 3,
    "sentiment_breakdown": {
      "positive": 3,
      "negative": 0,
      "neutral": 0
    },
    "top_topics": ["service", "logistics", "product"]
  },
  "expected_outputs": {
    "overall_rating": "excellent",
    "key_strengths": ["service", "delivery", "quality"],
    "areas_for_improvement": [],
    "recommendation": "maintain_current_standards"
  },
  "evaluation_config": {
    "evaluate_intermediate": true,
    "evaluate_final": true,
    "evaluate_aggregation": true,
    "strict_mode": false,
    "tolerance": 0.05,
    "ignore_fields": ["timestamp", "processing_time"]
  }
}
```

## 格式验证规则

### 必需字段验证

1. **id**: 必须存在且非空
2. **id 唯一性**: 同一测试集中不能有重复的 id

### 类型验证

1. **tags**: 必须是字符串列表
2. **inputs**: 必须是字典
3. **step_inputs**: 必须是嵌套字典 `{step_id: {key: value}}`
4. **batch_items**: 必须是字典列表
5. **expected_outputs**: 必须是字典
6. **intermediate_expectations**: 必须是字典

### 逻辑验证

1. **batch_items 与 expected_aggregation**: 如果定义了 batch_items，建议定义 expected_aggregation
2. **step_inputs 引用**: step_inputs 中的 step_id 应该对应 Pipeline 中的实际步骤
3. **intermediate_expectations 引用**: 中的 step_id 应该对应 Pipeline 中的实际步骤

## 使用指南

### 创建简单测试用例

对于简单的单步骤测试，只需要定义 id 和基本输入：

```jsonl
{"id": "test_1", "text": "input text", "expected_output": "result"}
```

### 创建多步骤测试用例

为不同步骤提供不同的输入：

```jsonl
{
  "id": "multi_step_1",
  "inputs": {"initial_data": "..."},
  "step_inputs": {
    "step1": {"param1": "value1"},
    "step2": {"param2": "value2"}
  },
  "expected_outputs": {"final_result": "..."}
}
```

### 创建批量处理测试用例

定义批量数据和预期聚合结果：

```jsonl
{
  "id": "batch_1",
  "batch_items": [
    {"item": "A"},
    {"item": "B"}
  ],
  "expected_aggregation": {"count": 2}
}
```

### 创建完整的 Pipeline 测试用例

结合所有特性：

```jsonl
{
  "id": "full_pipeline_1",
  "inputs": {...},
  "step_inputs": {...},
  "batch_items": [...],
  "intermediate_expectations": {...},
  "expected_aggregation": {...},
  "expected_outputs": {...},
  "evaluation_config": {...}
}
```

## 最佳实践

### 1. 命名约定

- **id**: 使用描述性名称，包含测试类型和场景
  - 好: `"sentiment_analysis_positive_review"`
  - 差: `"test1"`

- **tags**: 使用一致的标签体系
  - 功能标签: `"sentiment"`, `"summarization"`, `"translation"`
  - 类型标签: `"unit"`, `"integration"`, `"performance"`
  - 优先级标签: `"critical"`, `"important"`, `"optional"`

### 2. 数据组织

- 将相关的测试用例放在同一个文件中
- 使用标签进行分类和过滤
- 为复杂场景创建单独的测试文件

### 3. 预期结果定义

- 定义明确的预期结果，避免模糊
- 使用 `evaluation_config` 控制评估严格程度
- 对于 LLM 输出，使用宽松模式和关键字段验证

### 4. 批量测试

- 批量大小应适中（建议 5-20 个项目）
- 确保批量数据具有代表性
- 定义清晰的聚合预期

### 5. 中间步骤验证

- 对关键步骤定义 intermediate_expectations
- 用于调试和确保 Pipeline 正确性
- 可以通过 evaluation_config 控制是否评估

## 文件格式

### JSONL 格式

测试集使用 JSONL (JSON Lines) 格式：

- 每行一个完整的 JSON 对象
- 每行代表一个测试用例
- 支持注释（以 `//` 开头的行会被忽略）

### 文件命名约定

```
<feature>_<type>_<version>.jsonl
```

示例:
- `sentiment_analysis_basic_v1.jsonl`
- `pipeline_multi_step_integration_v2.jsonl`
- `batch_processing_performance_v1.jsonl`

### 文件组织

```
testsets/
├── unit/
│   ├── sentiment_basic.jsonl
│   └── summarization_basic.jsonl
├── integration/
│   ├── pipeline_multi_step.jsonl
│   └── pipeline_with_batch.jsonl
└── performance/
    └── batch_large_dataset.jsonl
```

## 版本兼容性

### v1.0 格式（简单格式）

```jsonl
{"id": "test_1", "input_field": "value", "expected_output": "result"}
```

**兼容性**: 完全支持，自动转换为 v2.0 格式

### v2.0 格式（Pipeline 格式）

```jsonl
{
  "id": "test_1",
  "inputs": {"input_field": "value"},
  "expected_outputs": {"output": "result"}
}
```

**新增特性**:
- step_inputs
- batch_items
- expected_aggregation
- intermediate_expectations
- evaluation_config

## 扩展性

### 自定义字段

测试用例支持自定义字段，这些字段会被保留在 `raw_data` 中：

```jsonl
{
  "id": "test_1",
  "custom_field": "custom_value",
  "metadata": {"author": "test_team"}
}
```

### 未来扩展

预留的扩展点：

1. **性能基准**: `performance_baseline` 字段
2. **依赖关系**: `depends_on` 字段（测试用例间依赖）
3. **条件执行**: `conditions` 字段（条件执行测试）
4. **参数化测试**: `parameters` 字段（参数化测试用例）

## 参考实现

完整的实现请参考：

- `src/testset_loader.py`: TestCase 类和 TestsetLoader 类
- `examples/testsets/`: 各种格式的示例文件
- `tests/test_testset_loader.py`: 单元测试

## 相关文档

- [Batch Processing Guide](./batch-processing-config-guide.md)
- [Pipeline Configuration Guide](./pipeline-guide.md)
- [Testset Loader Quick Reference](./testset-loader-quick-reference.md)
