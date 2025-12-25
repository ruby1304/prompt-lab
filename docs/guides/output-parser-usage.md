# Output Parser 使用指南

## 概述

Output Parser 功能已成功实现，支持将 LLM 的文本输出自动解析为结构化数据（JSON、列表等）。

## 功能特性

✅ **已实现的功能：**
1. JSON Output Parser - 将 JSON 字符串解析为 Python 字典
2. List Output Parser - 将逗号分隔的列表解析为 Python 列表
3. 向后兼容 - 未配置 parser 时保持原有字符串返回行为
4. Token 统计 - 支持在使用 parser 时正确统计 token 使用量
5. 配置验证 - 自动验证 parser 配置的有效性

✅ **重试机制：**
- 已实现自定义 RetryOutputParser，避免了 LangChain OutputFixingParser 的兼容性问题
- 支持配置重试次数（max_retries）
- 自动记录重试次数和失败原因

## 使用方法

### 1. 在 Flow 配置中添加 Output Parser

在 `agents/{agent_id}/prompts/{flow_name}.yaml` 文件中添加 `output_parser` 配置：

#### JSON Parser 示例

```yaml
name: "my_json_flow"
description: "返回 JSON 格式的 Flow"

system_prompt: |
  你是一个有帮助的助手。请严格按照 JSON 格式输出。
  只输出 JSON，不要有其他文字。

user_template: |
  请用 JSON 格式介绍{topic}，包含 name, type, description 三个字段

model: doubao-1-5-pro-32k-250115
temperature: 0.3

# Output Parser 配置
output_parser:
  type: "json"              # 解析器类型
  retry_on_error: true      # 是否启用重试
  max_retries: 3            # 最大重试次数（当 retry_on_error 为 true 时）
```

#### List Parser 示例

```yaml
name: "my_list_flow"
description: "返回列表格式的 Flow"

system_prompt: |
  你是一个有帮助的助手。请用逗号分隔的列表格式输出。

user_template: |
  列出 5 种{category}，用逗号分隔

model: doubao-1-5-pro-32k-250115
temperature: 0.3

output_parser:
  type: "list"
  retry_on_error: false
```

### 2. 在代码中使用

```python
from src.chains import run_flow, run_flow_with_tokens

# 使用 JSON Parser
result = run_flow(
    flow_name="my_json_flow",
    agent_id="my_agent",
    extra_vars={'topic': 'Python编程语言'}
)
# result 是一个 dict: {'name': 'Python', 'type': '...', 'description': '...'}

# 使用 List Parser
result = run_flow(
    flow_name="my_list_flow",
    agent_id="my_agent",
    extra_vars={'category': '编程语言'}
)
# result 是一个 list: ['Python', 'Java', 'C++', ...]

# 使用 Token 统计
result, token_info = run_flow_with_tokens(
    flow_name="my_json_flow",
    agent_id="my_agent",
    extra_vars={'topic': 'Python编程语言'}
)
# result: 解析后的数据
# token_info: {'input_tokens': 29, 'output_tokens': 44, 'total_tokens': 73}
```

### 3. 向后兼容

如果不配置 `output_parser`，行为与之前完全一致：

```yaml
name: "my_old_flow"
system_prompt: "你是一个有帮助的助手。"
user_template: "请介绍{topic}"
model: doubao-1-5-pro-32k-250115
# 没有 output_parser 配置
```

```python
result = run_flow(flow_name="my_old_flow", extra_vars={'topic': 'Python'})
# result 是一个 str: "Python是一种..."
```

## 配置选项

### OutputParserConfig 字段说明

| 字段 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `type` | string | 是 | - | 解析器类型：`json`, `pydantic`, `list`, `none` |
| `schema` | dict | 否 | None | JSON schema（用于 JSON parser） |
| `pydantic_model` | string | 否 | None | Pydantic 模型类名（用于 Pydantic parser） |
| `retry_on_error` | boolean | 否 | true | 是否在解析失败时重试 |
| `max_retries` | int | 否 | 3 | 最大重试次数 |
| `fix_prompt` | string | 否 | None | 修复提示词（用于重试） |

### 支持的 Parser 类型

1. **json** - 解析 JSON 字符串为 Python 字典
2. **list** - 解析逗号分隔的列表为 Python 列表
3. **pydantic** - 使用 Pydantic 模型验证和解析（需要提供模型类）
4. **none** - 返回原始字符串（等同于不配置 parser）

## 测试验证

已通过真实 LLM 调用测试（使用 doubao-1-5-pro-32k-250115 模型）：

✅ 测试 1: 向后兼容 - 未配置 parser 时返回字符串
✅ 测试 2: JSON Parser - 成功解析 JSON 输出为字典
✅ 测试 3: List Parser - 成功解析列表输出
✅ 测试 4: Token 统计 - 正常记录 token 使用量
✅ 测试 5: 组合功能 - JSON Parser + Token 统计正常工作

## 最佳实践

1. **明确的 Prompt 指令**：在 system_prompt 中明确要求 LLM 输出特定格式
2. **简洁的输出**：要求 LLM "只输出 JSON/列表，不要有其他文字"
3. **启用重试**：建议设置 `retry_on_error: true` 和 `max_retries: 3` 以提高可靠性
4. **错误处理**：在代码中添加 try-catch 处理解析失败的情况
5. **监控重试**：使用日志监控解析失败和重试情况

## 示例：Judge Agent 配置

```yaml
# agents/judge_default/prompts/judge_v2.yaml
name: "judge_v2"
description: "带 Output Parser 的 Judge"

system_prompt: |
  你是评估助手。请严格按照 JSON 格式输出评估结果。
  只输出 JSON，不要有其他文字。

user_template: |
  评估以下输出...

output_parser:
  type: "json"
  retry_on_error: true
  max_retries: 3
```

## 故障排除

### 问题：解析失败

**原因**：LLM 输出的格式不符合预期

**解决方案**：
1. 在 prompt 中更明确地要求输出格式
2. 降低 temperature 提高输出稳定性
3. 在代码中添加错误处理

### 问题：返回类型不对

**原因**：可能没有正确配置 output_parser

**解决方案**：
1. 检查 YAML 配置中是否有 `output_parser` 节
2. 验证 `type` 字段是否正确
3. 使用 `OutputParserConfig.validate()` 验证配置

## 下一步

根据 tasks.md，接下来的任务包括：
- 为 Judge Agent 配置 JSON Output Parser
- 创建 Pipeline 示例配置
- 实现统一评估接口
- 添加性能监控

---

**实现状态**: ✅ 完成
**测试状态**: ✅ 通过真实 LLM 调用测试
**文档状态**: ✅ 已更新
