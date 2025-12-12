# Output Parser 详细使用指南

## 目录

1. [概述](#概述)
2. [核心概念](#核心概念)
3. [配置方式](#配置方式)
4. [Parser 类型详解](#parser-类型详解)
5. [重试机制](#重试机制)
6. [错误处理](#错误处理)
7. [最佳实践](#最佳实践)
8. [高级用法](#高级用法)
9. [故障排除](#故障排除)

## 概述

Output Parser 是 Prompt Lab 基于 LangChain 实现的结构化输出解析功能。它能够将 LLM 的文本输出自动转换为结构化数据（如 JSON 对象、列表等），提高输出的可靠性和可用性。

### 为什么需要 Output Parser？

**问题**：
- LLM 输出是文本，需要手动解析
- 输出格式不稳定，容易出错
- 需要编写大量解析和验证代码

**解决方案**：
- 自动解析文本为结构化数据
- 自动验证输出格式
- 解析失败时自动重试
- 提供降级处理机制

### 主要特性

✅ **多种 Parser 类型**：JSON、Pydantic、List、None
✅ **自动重试**：解析失败时自动重试，提高成功率
✅ **降级处理**：重试失败后返回包含错误信息的降级结果
✅ **向后兼容**：未配置 Parser 时保持原有行为
✅ **性能监控**：记录解析成功率、重试次数等指标

## 核心概念

### Parser 工作流程

```
LLM 输出 (文本)
    ↓
Parser 尝试解析
    ↓
成功？ ──Yes──→ 返回结构化对象
    ↓
   No
    ↓
启用重试？ ──No──→ 抛出异常
    ↓
   Yes
    ↓
重新调用 LLM（带修复提示）
    ↓
解析成功？ ──Yes──→ 返回结构化对象
    ↓
   No
    ↓
达到最大重试次数？ ──Yes──→ 返回降级结果
    ↓
   No
    ↓
继续重试...
```

### Chain 结构

**不使用 Parser**：
```python
chain = prompt | llm
# 返回: str
```

**使用 Parser**：
```python
chain = prompt | llm | parser
# 返回: dict / list / Pydantic 对象
```

**使用 Retry Parser**：
```python
chain = prompt | llm | retry_parser
# 返回: dict / list / Pydantic 对象（带重试）
```

## 配置方式

### 在 Flow 配置中添加 Output Parser

Output Parser 在 Flow 配置文件中定义：

```yaml
# agents/{agent_id}/prompts/{flow_name}.yaml
name: "my_flow"
description: "Flow 描述"

system_prompt: |
  你的系统提示词...

user_template: |
  你的用户模板...

# Output Parser 配置
output_parser:
  type: "json"              # Parser 类型
  schema:                   # JSON schema（可选）
    type: "object"
    properties:
      field1: {type: "string"}
      field2: {type: "number"}
    required: ["field1"]
  retry_on_error: true      # 启用重试
  max_retries: 3            # 最大重试次数
  fix_prompt: |             # 修复提示（可选）
    上一次输出格式不正确，请严格按照 JSON 格式输出。
```

### 配置字段说明

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `type` | string | 是 | - | Parser 类型：`json`, `pydantic`, `list`, `none` |
| `schema` | dict | 否 | None | JSON schema，用于验证 JSON 输出 |
| `pydantic_model` | string | 否 | None | Pydantic 模型类名（需要在代码中定义） |
| `retry_on_error` | boolean | 否 | true | 解析失败时是否重试 |
| `max_retries` | int | 否 | 3 | 最大重试次数 |
| `fix_prompt` | string | 否 | None | 重试时使用的修复提示 |

## Parser 类型详解

### 1. JSON Parser

**用途**：将 JSON 字符串解析为 Python 字典

**配置示例**：
```yaml
output_parser:
  type: "json"
  schema:
    type: "object"
    properties:
      summary: {type: "string"}
      keywords: {type: "array", items: {type: "string"}}
      score: {type: "number", minimum: 0, maximum: 10}
    required: ["summary", "score"]
  retry_on_error: true
  max_retries: 3
```

**Prompt 建议**：
```yaml
system_prompt: |
  你是一个助手，请以 JSON 格式输出结果。
  只输出 JSON，不要有其他文字。
  
  输出格式：
  {
    "summary": "摘要文本",
    "keywords": ["关键词1", "关键词2"],
    "score": 8.5
  }
```

**使用示例**：
```python
result = run_flow(
    flow_name="my_json_flow",
    agent_id="my_agent",
    extra_vars={'text': '输入文本'}
)
# result: {'summary': '...', 'keywords': [...], 'score': 8.5}
```

**适用场景**：
- 结构化输出（摘要、分类结果、评分）
- 多字段返回
- 需要验证输出格式

### 2. Pydantic Parser

**用途**：使用 Pydantic 模型进行严格的类型验证

**配置示例**：
```yaml
output_parser:
  type: "pydantic"
  pydantic_model: "MyOutputModel"
  retry_on_error: true
  max_retries: 3
```

**模型定义**：
```python
from pydantic import BaseModel, Field
from typing import List

class MyOutputModel(BaseModel):
    summary: str = Field(description="文本摘要")
    keywords: List[str] = Field(description="关键词列表")
    score: float = Field(ge=0, le=10, description="评分")
```

**使用示例**：
```python
result = run_flow(
    flow_name="my_pydantic_flow",
    agent_id="my_agent",
    extra_vars={'text': '输入文本'}
)
# result: MyOutputModel(summary='...', keywords=[...], score=8.5)
```

**适用场景**：
- 需要严格类型检查
- 复杂的嵌套结构
- 需要数据验证逻辑

### 3. List Parser

**用途**：解析逗号分隔的列表

**配置示例**：
```yaml
output_parser:
  type: "list"
  retry_on_error: false
```

**Prompt 建议**：
```yaml
system_prompt: |
  你是一个助手，请用逗号分隔的列表格式输出。
  只输出列表项，用逗号分隔，不要有其他文字。

user_template: |
  列出 5 种{category}
```

**使用示例**：
```python
result = run_flow(
    flow_name="my_list_flow",
    agent_id="my_agent",
    extra_vars={'category': '编程语言'}
)
# result: ['Python', 'Java', 'C++', 'JavaScript', 'Go']
```

**适用场景**：
- 关键词提取
- 标签生成
- 简单列表输出

### 4. None（默认）

**用途**：不使用 Parser，返回原始字符串

**配置示例**：
```yaml
output_parser:
  type: "none"
```

或者不配置 `output_parser` 字段（向后兼容）。

**使用示例**：
```python
result = run_flow(
    flow_name="my_text_flow",
    agent_id="my_agent",
    extra_vars={'text': '输入文本'}
)
# result: "这是 LLM 的原始文本输出..."
```

**适用场景**：
- 自由文本生成
- 不需要结构化输出
- 保持向后兼容

## 重试机制

### 工作原理

当 Parser 解析失败时，系统会：

1. **检查是否启用重试**：`retry_on_error: true`
2. **检查重试次数**：是否达到 `max_retries`
3. **重新调用 LLM**：使用修复提示
4. **再次尝试解析**：解析新的输出
5. **重复步骤 2-4**：直到成功或达到最大重试次数

### 配置重试

```yaml
output_parser:
  type: "json"
  retry_on_error: true      # 启用重试
  max_retries: 3            # 最多重试 3 次
  fix_prompt: |             # 自定义修复提示
    上一次输出格式不正确。
    请严格按照 JSON 格式输出，不要有其他文字。
    确保所有必需字段都存在。
```

### 重试策略建议

| 场景 | 建议重试次数 | 说明 |
|------|-------------|------|
| 简单 JSON | 1-2 次 | 格式简单，通常一次就能成功 |
| 复杂 JSON | 2-3 次 | 字段较多，可能需要多次尝试 |
| Pydantic | 2-3 次 | 有验证逻辑，可能需要调整 |
| List | 0-1 次 | 格式简单，不需要太多重试 |

### 性能影响

- **无重试**：最快，但可能失败
- **1-2 次重试**：平衡性能和可靠性
- **3+ 次重试**：最可靠，但增加延迟和成本

**建议**：
- 开发阶段：使用 2-3 次重试，确保可靠性
- 生产环境：优化 Prompt 减少失败率，使用 1-2 次重试

## 错误处理

### 解析失败的处理

**情况 1：未启用重试**
```python
try:
    result = run_flow(...)
except OutputParserException as e:
    # 处理解析错误
    print(f"解析失败: {e}")
    # 使用默认值或降级处理
    result = {"error": str(e)}
```

**情况 2：启用重试但仍失败**
```python
# 系统会自动返回降级结果
result = run_flow(...)
# result: {
#     "error": "解析失败",
#     "raw_output": "LLM 的原始输出...",
#     "retry_count": 3
# }
```

### 降级处理

当所有重试都失败时，系统返回降级结果：

```python
{
    "error": "Output parsing failed after 3 retries",
    "raw_output": "LLM 的原始输出（前 500 字符）",
    "retry_count": 3,
    "parse_error": True
}
```

### 日志记录

系统会自动记录解析失败和重试信息：

```
WARNING: Output parsing failed: Expecting ',' delimiter: line 5 column 10
INFO: Retrying output parsing (attempt 1/3)
INFO: Retrying output parsing (attempt 2/3)
ERROR: Output parsing failed after 3 retries
```

## 最佳实践

### 1. Prompt 设计

**✅ 好的 Prompt**：
```yaml
system_prompt: |
  你是一个助手，请以 JSON 格式输出结果。
  
  输出格式要求：
  1. 只输出 JSON，不要有其他文字
  2. 确保 JSON 格式正确（括号匹配、逗号正确）
  3. 必须包含以下字段：summary, score
  
  示例输出：
  {"summary": "这是摘要", "score": 8.5}
```

**❌ 不好的 Prompt**：
```yaml
system_prompt: |
  你是一个助手，请输出结果。
```

### 2. Schema 设计

**✅ 好的 Schema**：
```yaml
schema:
  type: "object"
  properties:
    summary: {type: "string", minLength: 10}
    score: {type: "number", minimum: 0, maximum: 10}
  required: ["summary", "score"]
```

**❌ 不好的 Schema**：
```yaml
schema:
  type: "object"
  properties:
    field1: {type: "string"}
    field2: {type: "string"}
    field3: {type: "string"}
    # 太多字段，容易出错
```

### 3. 重试配置

**✅ 合理的重试配置**：
```yaml
output_parser:
  type: "json"
  retry_on_error: true
  max_retries: 2
  fix_prompt: "请严格按照 JSON 格式输出。"
```

**❌ 不合理的重试配置**：
```yaml
output_parser:
  type: "json"
  retry_on_error: true
  max_retries: 10  # 太多重试，浪费资源
```

### 4. 错误处理

**✅ 完善的错误处理**：
```python
try:
    result = run_flow(...)
    if isinstance(result, dict) and result.get("parse_error"):
        # 降级处理
        logger.warning(f"解析失败，使用降级结果: {result}")
        result = handle_fallback(result)
except Exception as e:
    logger.error(f"执行失败: {e}")
    result = None
```

**❌ 缺少错误处理**：
```python
result = run_flow(...)
# 假设总是成功，没有错误处理
```

### 5. 性能优化

**优化 Prompt 减少失败率**：
- 在 Prompt 中提供输出示例
- 明确说明格式要求
- 使用较低的 temperature（如 0.3）

**监控解析成功率**：
```python
# 使用性能监控功能
from src.pipeline_runner import PipelineRunner

runner = PipelineRunner(pipeline_config)
result = runner.run(test_case, variant="baseline")

# 查看解析统计
print(f"解析成功率: {result.parse_success_rate}")
print(f"平均重试次数: {result.avg_retry_count}")
```

## 高级用法

### 1. 自定义 Parser

```python
from langchain.output_parsers import BaseOutputParser

class CustomOutputParser(BaseOutputParser):
    def parse(self, text: str) -> dict:
        # 自定义解析逻辑
        lines = text.strip().split('\n')
        return {
            'line_count': len(lines),
            'content': lines
        }

# 在 OutputParserFactory 中注册
# （需要修改 src/output_parser.py）
```

### 2. 条件性使用 Parser

```python
def run_with_conditional_parser(flow_name, agent_id, use_parser=True):
    if use_parser:
        # 使用配置的 Parser
        result = run_flow(flow_name, agent_id, ...)
    else:
        # 临时禁用 Parser
        # （需要在代码中实现此功能）
        result = run_flow_without_parser(flow_name, agent_id, ...)
    return result
```

### 3. Parser 链式组合

```python
# 先解析 JSON，再提取特定字段
chain = prompt | llm | json_parser | field_extractor
```

## 故障排除

### 问题 1：解析总是失败

**症状**：即使重试多次，解析仍然失败

**可能原因**：
1. Prompt 不够明确
2. LLM 输出包含额外文字
3. JSON 格式错误

**解决方案**：
```yaml
# 1. 改进 Prompt
system_prompt: |
  你是一个助手，请以 JSON 格式输出结果。
  
  重要：
  - 只输出 JSON，不要有任何其他文字
  - 不要输出 "```json" 或 "```"
  - 确保 JSON 格式正确
  
  输出示例：
  {"field1": "value1", "field2": 123}

# 2. 降低 temperature
temperature: 0.3

# 3. 增加重试次数
output_parser:
  retry_on_error: true
  max_retries: 3
```

### 问题 2：返回类型不对

**症状**：期望返回 dict，但返回了 str

**可能原因**：
1. 没有配置 output_parser
2. 配置格式错误
3. Parser 类型设置错误

**解决方案**：
```python
# 1. 检查配置
from src.config import load_flow_config

flow_cfg = load_flow_config("my_agent", "my_flow")
print(flow_cfg.get("output_parser"))  # 应该有值

# 2. 验证配置
from src.output_parser import OutputParserConfig

parser_cfg = OutputParserConfig(**flow_cfg["output_parser"])
parser_cfg.validate()  # 检查配置是否有效
```

### 问题 3：性能下降

**症状**：使用 Parser 后执行时间明显增加

**可能原因**：
1. 重试次数过多
2. 解析失败率高
3. 使用了复杂的 Pydantic 模型

**解决方案**：
```yaml
# 1. 减少重试次数
output_parser:
  max_retries: 1  # 从 3 减少到 1

# 2. 优化 Prompt 提高成功率
system_prompt: |
  # 更明确的指令...

# 3. 使用更简单的 Parser
output_parser:
  type: "json"  # 而不是 pydantic
```

### 问题 4：Judge Agent 评分不稳定

**症状**：Judge Agent 的评分结果不一致

**可能原因**：
1. Judge 输出格式不稳定
2. 没有使用 Output Parser
3. temperature 设置过高

**解决方案**：
```yaml
# agents/judge_default/prompts/judge_v2.yaml
name: "judge_v2"

system_prompt: |
  你是评估助手，请严格按照 JSON 格式输出。
  只输出 JSON，不要有其他文字。

temperature: 0.3  # 降低 temperature

output_parser:
  type: "json"
  schema:
    type: "object"
    properties:
      overall_score: {type: "number"}
      must_have_check: {type: "array"}
      overall_comment: {type: "string"}
    required: ["overall_score", "must_have_check", "overall_comment"]
  retry_on_error: true
  max_retries: 3
```

## 相关文档

- [系统架构文档](../ARCHITECTURE.md) - 了解 Output Parser 在系统中的位置
- [Pipeline 配置指南](pipeline-guide.md) - Pipeline 中使用 Output Parser
- [评估模式指南](eval-modes-guide.md) - Judge Agent 使用 Output Parser
- [OUTPUT_PARSER_USAGE.md](../../OUTPUT_PARSER_USAGE.md) - 快速开始指南

## 示例代码

完整的示例代码请参考：
- `examples/pipeline_demo.py` - Pipeline 中使用 Output Parser
- `tests/test_output_parser.py` - Output Parser 单元测试
- `tests/test_integration_judge.py` - Judge Agent 集成测试
