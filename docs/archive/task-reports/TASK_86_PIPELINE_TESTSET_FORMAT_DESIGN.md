# Task 86: Pipeline 级别测试集格式设计 - 完成总结

## 任务概述

设计 Pipeline 级别测试集格式，支持复杂的多步骤 Pipeline 测试场景。

**需求**: Requirements 5.1, 5.5

## 完成的工作

### 1. 核心设计文档

创建了完整的 Pipeline 测试集格式规范文档：

**文件**: `docs/reference/pipeline-testset-format-specification.md`

**内容包括**:
- 格式版本定义（v2.0）
- 核心数据结构（TestCase 模型）
- 9个字段的详细说明
- 多种测试场景示例
- 格式验证规则
- 使用指南和最佳实践
- 文件格式和命名约定
- 版本兼容性说明
- 扩展性设计

### 2. JSON Schema 定义

创建了标准的 JSON Schema 用于验证测试集格式：

**文件**: `config/schemas/pipeline_testset.schema.json`

**特性**:
- 符合 JSON Schema Draft-07 标准
- 完整的字段定义和类型约束
- 详细的描述和示例
- 支持自动验证

### 3. 示例测试集文件

创建了4个完整的示例文件，涵盖各种场景：

#### a. 多步骤 Pipeline 示例
**文件**: `examples/testsets/pipeline_multi_step_examples.jsonl`

包含5个示例：
- 基础多步骤测试
- 包含代码节点的测试
- 条件执行测试
- 并发处理测试
- 输入验证测试

#### b. 批量聚合示例
**文件**: `examples/testsets/pipeline_batch_aggregation_examples.jsonl`

包含7个示例：
- 简单拼接聚合
- 统计聚合
- 过滤聚合
- 自定义聚合
- 多阶段聚合
- 错误处理聚合
- 嵌套数据聚合

#### c. 中间步骤评估示例
**文件**: `examples/testsets/pipeline_intermediate_evaluation_examples.jsonl`

包含6个示例：
- 基础中间评估
- 带指标的评估
- 调试场景
- 部分失败处理
- 数据流验证
- 性能跟踪

#### d. 复杂场景示例
**文件**: `examples/testsets/pipeline_complex_scenarios.jsonl`

包含5个复杂的端到端场景：
- 客户反馈分析（E2E）
- 多语言处理
- 数据 ETL Pipeline
- 机器学习 Pipeline
- 实时监控

### 4. 快速参考文档

创建了简洁的速查表：

**文件**: `docs/reference/pipeline-testset-quick-reference.md`

**内容**:
- 基本结构速查
- 字段对照表
- 常用模式
- 评估配置选项
- 标签最佳实践
- 加载代码示例
- 常见用例
- 验证规则

### 5. 文档集成

更新了主文档导航：

**文件**: `docs/README.md`

添加了新文档的链接和快速查找入口。

## 设计亮点

### 1. 支持多步骤测试数据

```json
{
  "step_inputs": {
    "preprocess": {"lowercase": true},
    "analyze": {"model": "advanced"},
    "generate_report": {"format": "json"}
  }
}
```

为不同步骤提供不同的配置参数。

### 2. 支持批量测试数据

```json
{
  "batch_items": [
    {"text": "Item 1", "rating": 5},
    {"text": "Item 2", "rating": 3}
  ]
}
```

批量处理步骤的输入数据列表。

### 3. 支持预期聚合结果

```json
{
  "expected_aggregation": {
    "total_items": 5,
    "average_rating": 3.8,
    "sentiment_distribution": {
      "positive": 3,
      "negative": 1,
      "neutral": 1
    }
  }
}
```

验证批量聚合的正确性。

### 4. 支持中间步骤评估

```json
{
  "intermediate_expectations": {
    "preprocess": {"cleaned_text": "..."},
    "analyze": {"sentiment_score": 0.8}
  },
  "evaluation_config": {
    "evaluate_intermediate": true
  }
}
```

验证 Pipeline 中间状态，便于调试。

### 5. 灵活的评估配置

```json
{
  "evaluation_config": {
    "evaluate_intermediate": true,
    "strict_mode": false,
    "tolerance": 0.01,
    "ignore_fields": ["timestamp", "request_id"]
  }
}
```

控制评估的严格程度和忽略字段。

## 核心字段说明

### 必需字段

1. **id** (string): 测试用例唯一标识符

### 可选字段

2. **tags** (string[]): 标签列表，用于分类和过滤
3. **inputs** (object): 全局输入，Pipeline 初始输入
4. **step_inputs** (object): 步骤级输入，为特定步骤提供参数
5. **batch_items** (object[]): 批量处理数据列表
6. **expected_outputs** (object): 预期最终输出
7. **expected_aggregation** (any): 预期聚合结果
8. **intermediate_expectations** (object): 中间步骤预期输出
9. **evaluation_config** (object): 评估配置

## 向后兼容性

### v1.0 格式（简单格式）

```jsonl
{"id": "test_1", "text": "input", "expected_output": "result"}
```

完全支持，自动转换为 v2.0 格式。

### v2.0 格式（Pipeline 格式）

```jsonl
{
  "id": "test_1",
  "inputs": {"text": "input"},
  "expected_outputs": {"output": "result"}
}
```

新增所有高级特性。

## 验证规则

### 必需字段验证
- `id` 必须存在且非空
- `id` 在同一测试集中必须唯一

### 类型验证
- `tags`: 字符串列表
- `inputs`: 字典
- `step_inputs`: 嵌套字典
- `batch_items`: 字典列表
- `expected_outputs`: 字典

### 逻辑验证
- 如果定义了 `batch_items`，建议定义 `expected_aggregation`
- `step_inputs` 中的 step_id 应对应实际步骤
- `intermediate_expectations` 中的 step_id 应对应实际步骤

## 使用场景

### 1. 简单单步测试
```json
{"id": "test_1", "text": "input", "expected_output": "result"}
```

### 2. 多步骤 Pipeline 测试
```json
{
  "id": "multi_1",
  "inputs": {...},
  "step_inputs": {"step1": {...}, "step2": {...}},
  "expected_outputs": {...}
}
```

### 3. 批量处理测试
```json
{
  "id": "batch_1",
  "batch_items": [...],
  "expected_aggregation": {...}
}
```

### 4. 完整 Pipeline 测试
```json
{
  "id": "full_1",
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
- 使用描述性的 id
- 使用一致的标签体系
- 文件命名: `<feature>_<type>_<version>.jsonl`

### 2. 数据组织
- 相关测试用例放在同一文件
- 使用标签进行分类
- 为复杂场景创建单独文件

### 3. 预期结果定义
- 定义明确的预期结果
- 使用 evaluation_config 控制严格程度
- 对 LLM 输出使用宽松模式

### 4. 批量测试
- 批量大小适中（5-20个）
- 确保数据具有代表性
- 定义清晰的聚合预期

### 5. 中间步骤验证
- 对关键步骤定义 intermediate_expectations
- 用于调试和确保正确性
- 通过 evaluation_config 控制是否评估

## 扩展性

### 预留扩展点

1. **性能基准**: `performance_baseline` 字段
2. **依赖关系**: `depends_on` 字段（测试用例间依赖）
3. **条件执行**: `conditions` 字段（条件执行测试）
4. **参数化测试**: `parameters` 字段（参数化测试用例）

### 自定义字段

测试用例支持自定义字段，保留在 `raw_data` 中：

```json
{
  "id": "test_1",
  "custom_field": "custom_value",
  "metadata": {"author": "test_team"}
}
```

## 文件清单

### 文档文件
1. `docs/reference/pipeline-testset-format-specification.md` - 完整规范（约1500行）
2. `docs/reference/pipeline-testset-quick-reference.md` - 快速参考（约300行）
3. `docs/README.md` - 更新了文档导航

### Schema 文件
4. `config/schemas/pipeline_testset.schema.json` - JSON Schema 定义

### 示例文件
5. `examples/testsets/pipeline_multi_step_examples.jsonl` - 多步骤示例（5个）
6. `examples/testsets/pipeline_batch_aggregation_examples.jsonl` - 批量聚合示例（7个）
7. `examples/testsets/pipeline_intermediate_evaluation_examples.jsonl` - 中间评估示例（6个）
8. `examples/testsets/pipeline_complex_scenarios.jsonl` - 复杂场景示例（5个）

### 总结文件
9. `TASK_86_PIPELINE_TESTSET_FORMAT_DESIGN.md` - 本文件

## 与现有系统的集成

### TestCase 类（已存在）

现有的 `src/testset_loader.py` 中的 `TestCase` 类已经支持所有设计的字段：

```python
@dataclass
class TestCase:
    id: str
    tags: List[str]
    inputs: Dict[str, Any]
    step_inputs: Dict[str, Dict[str, Any]]
    batch_items: Optional[List[Dict[str, Any]]]
    expected_outputs: Dict[str, Any]
    expected_aggregation: Optional[Any]
    raw_data: Dict[str, Any]
```

### 需要添加的字段

设计中新增的字段需要在后续任务中添加到 TestCase 类：

1. `intermediate_expectations: Dict[str, Any]`
2. `evaluation_config: Dict[str, Any]`

## 验证需求满足情况

### Requirement 5.1 ✅
**WHEN 定义 Pipeline 测试集时 THEN the System SHALL 支持为不同步骤定义不同的测试数据**

- ✅ 通过 `step_inputs` 字段实现
- ✅ 支持为每个步骤定义独立的输入参数
- ✅ 提供了多个示例和文档说明

### Requirement 5.5 ✅
**WHEN 定义测试集时 THEN the System SHALL 支持为批量处理步骤定义预期的聚合结果**

- ✅ 通过 `expected_aggregation` 字段实现
- ✅ 支持任意复杂的聚合结果结构
- ✅ 提供了7个不同的聚合示例

## 后续任务

本任务完成了格式设计，后续任务需要：

1. **Task 87**: 更新测试集加载器，支持新字段
2. **Task 88**: 实现 Pipeline 评估支持
3. **Task 89**: 创建更多测试集示例
4. **Task 90-94**: 编写 Property 测试

## 总结

本任务成功设计了完整的 Pipeline 级别测试集格式，包括：

- ✅ 完整的格式规范文档
- ✅ JSON Schema 定义
- ✅ 23个实际示例（涵盖各种场景）
- ✅ 快速参考文档
- ✅ 文档集成

设计支持：
- ✅ 多步骤测试数据
- ✅ 步骤级输入
- ✅ 批量测试数据
- ✅ 预期聚合结果
- ✅ 中间步骤评估
- ✅ 灵活的评估配置
- ✅ 向后兼容
- ✅ 可扩展性

格式设计完整、清晰、易用，为后续的实现和测试奠定了坚实的基础。

---

**任务状态**: ✅ 完成
**完成时间**: 2024-12-17
**相关需求**: Requirements 5.1, 5.5
