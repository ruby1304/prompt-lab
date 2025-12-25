# Pipeline 测试集示例

本目录包含各种 Pipeline 测试集示例，展示了不同的测试场景和最佳实践。

## 📁 文件组织

### 简单测试集 (Simple Testsets)

适合单步骤 Agent 或简单 Pipeline 测试：

- **`simple_sentiment_analysis.jsonl`** - 情感分析测试
  - 基础正面/负面/中性情感
  - 强烈情感表达
  - 混合情感
  - 边界情况（空文本、表情符号、讽刺）

- **`simple_summarization.jsonl`** - 文本摘要测试
  - 短文本摘要
  - 中等长度文本
  - 技术文档摘要
  - 新闻摘要
  - 带要点的摘要

### 批量处理测试集 (Batch Processing Testsets)

展示批量数据处理和聚合功能：

- **`simple_batch_reviews.jsonl`** - 客户评论批量分析
  - 基础批量处理
  - 全部正面评论
  - 过滤验证评论
  - 按类别分组
  - 自定义聚合逻辑
  - 大数据集性能测试

- **`batch_processing_demo.jsonl`** - 批量处理演示
  - 基础批量配置
  - 不同聚合策略示例

- **`batch_processing_advanced.jsonl`** - 高级批量处理
  - 复杂聚合场景
  - 嵌套数据处理
  - 错误处理

- **`pipeline_batch_aggregation_examples.jsonl`** - Pipeline 批量聚合
  - Concat 聚合
  - Stats 聚合
  - Filter 聚合
  - Custom 聚合
  - 多阶段聚合
  - 嵌套聚合

### 多阶段评估测试集 (Multi-Stage Evaluation Testsets)

展示中间步骤验证和复杂数据流：

- **`simple_text_processing_pipeline.jsonl`** - 文本处理 Pipeline
  - 完整的文本处理流程
  - 短文本处理
  - 数字提取
  - 多语言处理
  - 验证和错误处理
  - 数据流验证
  - 条件执行
  - 并行步骤
  - 性能跟踪

- **`pipeline_multi_step_examples.jsonl`** - 多步骤 Pipeline
  - 基础多步骤
  - 代码节点集成
  - 条件执行
  - 并行处理
  - 验证流程

- **`pipeline_intermediate_evaluation_examples.jsonl`** - 中间步骤评估
  - 基础中间评估
  - 带指标的评估
  - 调试场景
  - 部分失败处理
  - 数据流跟踪
  - 性能跟踪

### 复杂场景测试集 (Complex Scenarios)

展示真实世界的复杂用例：

- **`pipeline_complex_scenarios.jsonl`** - 复杂 Pipeline 场景
  - 端到端客户反馈分析
  - 多语言处理和翻译
  - ETL 数据管道
  - 机器学习 Pipeline
  - 实时监控

- **`pipeline_testset_formats.jsonl`** - 测试集格式示例
  - 各种格式的完整示例

## 🚀 快速开始

### 1. 运行简单测试

```bash
# 情感分析测试
python -m src.run_eval \
  --agent sentiment_analyzer \
  --testset examples/testsets/simple_sentiment_analysis.jsonl

# 文本摘要测试
python -m src.run_eval \
  --agent summarizer \
  --testset examples/testsets/simple_summarization.jsonl
```

### 2. 运行批量处理测试

```bash
# 批量评论分析
python -m src.run_eval \
  --pipeline review_analysis_pipeline \
  --testset examples/testsets/simple_batch_reviews.jsonl
```

### 3. 运行多阶段评估测试

```bash
# 文本处理 Pipeline
python -m src.run_eval \
  --pipeline text_processing_pipeline \
  --testset examples/testsets/simple_text_processing_pipeline.jsonl \
  --evaluate-intermediate
```

### 4. 使用标签过滤

```bash
# 只运行关键测试
python -m src.run_eval \
  --agent my_agent \
  --testset examples/testsets/simple_sentiment_analysis.jsonl \
  --tags critical

# 运行特定类型的测试
python -m src.run_eval \
  --agent my_agent \
  --testset examples/testsets/simple_batch_reviews.jsonl \
  --tags batch,positive
```

## 📖 使用指南

### 选择合适的测试集类型

| 测试场景 | 推荐文件 | 特点 |
|---------|---------|------|
| 单步骤 Agent 测试 | `simple_*.jsonl` | 简单输入输出 |
| 批量数据处理 | `simple_batch_*.jsonl` | 批量处理和聚合 |
| 复杂 Pipeline | `simple_text_processing_pipeline.jsonl` | 多步骤验证 |
| 高级场景 | `pipeline_complex_scenarios.jsonl` | 真实世界用例 |

### 创建自己的测试集

1. **从简单开始**
   ```jsonl
   {"id": "test_1", "inputs": {"text": "test"}, "expected_outputs": {"result": "expected"}}
   ```

2. **添加标签和配置**
   ```jsonl
   {
     "id": "test_1",
     "tags": ["critical", "basic"],
     "inputs": {"text": "test"},
     "expected_outputs": {"result": "expected"},
     "evaluation_config": {"strict_mode": false}
   }
   ```

3. **添加批量处理**
   ```jsonl
   {
     "id": "batch_test",
     "batch_items": [{"item": 1}, {"item": 2}],
     "expected_aggregation": {"count": 2}
   }
   ```

4. **添加中间步骤验证**
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

## 🎯 测试集特性对照表

| 文件 | 简单 | 批量 | 多步骤 | 中间验证 | 聚合 | 并发 |
|------|------|------|--------|----------|------|------|
| `simple_sentiment_analysis.jsonl` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `simple_summarization.jsonl` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `simple_batch_reviews.jsonl` | ❌ | ✅ | ❌ | ❌ | ✅ | ✅ |
| `simple_text_processing_pipeline.jsonl` | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| `batch_processing_demo.jsonl` | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| `pipeline_multi_step_examples.jsonl` | ❌ | ❌ | ✅ | ✅ | ❌ | ✅ |
| `pipeline_batch_aggregation_examples.jsonl` | ❌ | ✅ | ✅ | ❌ | ✅ | ❌ |
| `pipeline_intermediate_evaluation_examples.jsonl` | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| `pipeline_complex_scenarios.jsonl` | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ |

## 📚 相关文档

### 指南
- [Testset Creation Guide](../../docs/guides/testset-creation-guide.md) - 完整的测试集创建指南
- [Batch Processing Guide](../../docs/reference/batch-processing-config-guide.md) - 批量处理配置
- [Pipeline Evaluation Guide](../../docs/reference/pipeline-evaluation-guide.md) - Pipeline 评估

### 参考
- [Pipeline Testset Format Specification](../../docs/reference/pipeline-testset-format-specification.md) - 格式规范
- [Testset Loader Quick Reference](../../docs/reference/testset-loader-quick-reference.md) - 快速参考
- [Batch Testset Format Guide](../../docs/reference/batch-testset-format-guide.md) - 批量测试集格式

## 💡 最佳实践

### 1. 命名约定
- 使用描述性的测试 ID: `sentiment_positive_basic` 而不是 `test1`
- 使用一致的标签: `["sentiment", "positive", "critical"]`

### 2. 数据质量
- 使用真实的测试数据
- 覆盖边界情况
- 包含错误场景

### 3. 评估配置
- 对 LLM 输出使用宽松模式: `"strict_mode": false`
- 为数值添加容差: `"tolerance": 0.05`
- 忽略不重要的字段: `"ignore_fields": ["timestamp"]`

### 4. 文件组织
```
testsets/
├── unit/           # 单元测试
├── integration/    # 集成测试
├── performance/    # 性能测试
└── regression/     # 回归测试
```

## 🔍 示例代码

### Python API 使用

```python
from src.testset_loader import TestsetLoader
from src.pipeline_runner import PipelineRunner
from src.unified_evaluator import UnifiedEvaluator

# 加载测试集
loader = TestsetLoader()
testcases = loader.load_testset("examples/testsets/simple_sentiment_analysis.jsonl")

# 运行测试
runner = PipelineRunner(pipeline_config)
results = runner.run_batch(testcases)

# 评估结果
evaluator = UnifiedEvaluator()
evaluation = evaluator.evaluate_batch(results, testcases)

print(f"Pass rate: {evaluation['pass_rate']}")
```

### 过滤测试用例

```python
# 按标签过滤
critical_tests = loader.load_testset(
    "examples/testsets/simple_sentiment_analysis.jsonl",
    tags=["critical"]
)

# 按 ID 过滤
specific_tests = loader.load_testset(
    "examples/testsets/simple_sentiment_analysis.jsonl",
    test_ids=["positive_basic", "negative_basic"]
)
```

## 🐛 故障排查

### 问题: 测试加载失败
```bash
# 验证 JSON 格式
python -c "import json; [json.loads(line) for line in open('testset.jsonl')]"
```

### 问题: 所有测试都失败
- 检查 `evaluation_config` 设置
- 使用 `"strict_mode": false`
- 添加 `"tolerance"` 和 `"ignore_fields"`

### 问题: 批量处理不工作
- 确保 Pipeline 配置支持批量处理
- 检查 `batch_mode: true` 设置
- 验证聚合步骤配置

## 📞 获取帮助

如果您遇到问题：

1. 查看 [Testset Creation Guide](../../docs/guides/testset-creation-guide.md)
2. 参考示例文件
3. 查看相关文档
4. 联系开发团队

---

**最后更新**: 2024-01-17
**版本**: 1.0.0
