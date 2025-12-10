# 评估规则配置指南

## 概述

评估规则系统允许你为每个 Agent 配置自定义的规则，用于快速过滤明显的 bad case，减少人工评估和 LLM Judge 的工作量。

## 规则配置位置

在 Agent 配置文件 `agents/{agent_id}.yaml` 中的 `evaluation.rules` 部分：

```yaml
evaluation:
  # ... 其他配置
  rules:
    - id: "rule_unique_id"
      kind: "rule_type"
      target: "output"
      # ... 规则特定参数
      action: "mark_bad"
```

## 支持的规则类型

### 1. 长度控制规则

#### `max_tokens` - 最大 Token 数限制
```yaml
- id: "max_tokens_200"
  kind: "max_tokens"
  target: "output"
  max_tokens: 200
  action: "mark_bad"
```
**说明**：限制输出的最大 token 数量（使用简单估算）
**参数**：
- `max_tokens` (必需): 最大允许的 token 数

#### `max_chars` - 最大字符数限制
```yaml
- id: "reasonable_length"
  kind: "max_chars"
  target: "output"
  max_chars: 1000
  action: "mark_bad"
```
**说明**：限制输出的最大字符数
**参数**：
- `max_chars` (必需): 最大允许的字符数

### 2. 内容检查规则

#### `non_empty` - 非空检查
```yaml
- id: "must_not_be_empty"
  kind: "non_empty"
  target: "output"
  action: "mark_bad"
```
**说明**：确保输出不为空（去除空白字符后）
**参数**：无

#### `allowed_values` - 允许值列表
```yaml
- id: "binary_output"
  kind: "allowed_values"
  target: "output"
  allowed_values: ["0", "1"]
  trim: true
  action: "mark_bad"
```
**说明**：输出必须是指定值列表中的一个
**参数**：
- `allowed_values` (必需): 允许的值列表
- `trim` (可选): 是否先去除首尾空白，默认 true

#### `contains_any` - 包含关键词检查
```yaml
- id: "should_mention_key_concepts"
  kind: "contains_any"
  target: "output"
  keywords: ["用户", "角色", "对话", "总结"]
  ignore_case: true
  action: "mark_bad"
```
**说明**：输出必须包含至少一个指定的关键词
**参数**：
- `keywords` (必需): 关键词列表
- `ignore_case` (可选): 是否忽略大小写，默认 false

### 3. 格式检查规则

#### `regex_match` - 正则表达式匹配
```yaml
- id: "no_json_format"
  kind: "regex_match"
  target: "output"
  pattern: "^[^{]*$"
  ignore_case: false
  action: "mark_bad"
```
**说明**：输出必须匹配指定的正则表达式
**参数**：
- `pattern` (必需): 正则表达式模式
- `ignore_case` (可选): 是否忽略大小写，默认 false

#### `starts_with` - 前缀检查
```yaml
- id: "must_start_with_summary"
  kind: "starts_with"
  target: "output"
  prefix: "总结："
  ignore_case: true
  action: "mark_bad"
```
**说明**：输出必须以指定前缀开头
**参数**：
- `prefix` (必需): 必需的前缀
- `ignore_case` (可选): 是否忽略大小写，默认 false

#### `ends_with` - 后缀检查
```yaml
- id: "must_end_with_period"
  kind: "ends_with"
  target: "output"
  suffix: "。"
  ignore_case: false
  action: "mark_bad"
```
**说明**：输出必须以指定后缀结尾
**参数**：
- `suffix` (必需): 必需的后缀
- `ignore_case` (可选): 是否忽略大小写，默认 false

## 规则配置示例

### 对话总结 Agent
```yaml
evaluation:
  rules:
    # 基础长度控制
    - id: "reasonable_summary_length"
      kind: "max_tokens"
      target: "output"
      max_tokens: 300
      action: "mark_bad"
    
    - id: "not_empty"
      kind: "non_empty"
      target: "output"
      action: "mark_bad"
    
    # 内容质量检查
    - id: "must_mention_dialogue_elements"
      kind: "contains_any"
      target: "output"
      keywords: ["用户", "角色", "对话", "交流", "时间", "事件"]
      ignore_case: true
      action: "mark_bad"
```

### 分类 Agent
```yaml
evaluation:
  rules:
    - id: "valid_category_only"
      kind: "allowed_values"
      target: "output"
      allowed_values: ["positive", "negative", "neutral"]
      trim: true
      action: "mark_bad"
    
    - id: "single_word_output"
      kind: "regex_match"
      target: "output"
      pattern: "^\\w+$"
      action: "mark_bad"
```

### 二元判断 Agent
```yaml
evaluation:
  rules:
    - id: "binary_only"
      kind: "allowed_values"
      target: "output"
      allowed_values: ["0", "1", "yes", "no", "true", "false"]
      trim: true
      action: "mark_bad"
```

### 结构化输出 Agent
```yaml
evaluation:
  rules:
    - id: "must_have_structure"
      kind: "contains_any"
      target: "output"
      keywords: ["###", "**", "1.", "2.", "-"]
      ignore_case: false
      action: "mark_bad"
    
    - id: "reasonable_structured_length"
      kind: "max_chars"
      target: "output"
      max_chars: 2000
      action: "mark_bad"
```

## 使用指南

### 1. 无规则配置
如果不需要任何规则，可以完全省略 `rules` 部分：
```yaml
evaluation:
  judge_agent_id: "judge_default"
  # 没有 rules 部分
```

### 2. 规则设计原则
- **从简单开始**：先配置基础的硬性规则（非空、长度限制）
- **逐步细化**：根据实际输出质量添加内容规则
- **避免过严**：规则应该过滤明显错误，而不是替代人工判断

### 3. 规则调试
```bash
# 查看规则执行结果
python -m src.eval_rules run --agent your_agent --infile input.csv --outfile output.csv

# 查看规则统计
python -m src.eval_rules stats --infile output.csv
```

### 4. 常见规则组合

#### 最小规则集（推荐起点）
```yaml
rules:
  - id: "not_empty"
    kind: "non_empty"
    target: "output"
    action: "mark_bad"
  
  - id: "reasonable_length"
    kind: "max_chars"
    target: "output"
    max_chars: 2000
    action: "mark_bad"
```

#### 严格规则集
```yaml
rules:
  - id: "not_empty"
    kind: "non_empty"
    target: "output"
    action: "mark_bad"
  
  - id: "token_limit"
    kind: "max_tokens"
    target: "output"
    max_tokens: 200
    action: "mark_bad"
  
  - id: "must_be_relevant"
    kind: "contains_any"
    target: "output"
    keywords: ["相关", "关键词", "列表"]
    ignore_case: true
    action: "mark_bad"
```

## 扩展新规则类型

如需添加新的规则类型，请在 `src/rule_engine.py` 中的 `RULE_HANDLERS` 字典中添加处理函数：

```python
def handle_your_new_rule(rule: Dict[str, Any], value: str) -> bool:
    """返回 True 表示违反规则"""
    # 实现你的规则逻辑
    return violation_detected

RULE_HANDLERS["your_new_rule_type"] = handle_your_new_rule
```

## 注意事项

1. **规则 ID 唯一性**：同一个 Agent 内的规则 ID 必须唯一
2. **性能考虑**：规则检查在本地执行，复杂的正则表达式可能影响性能
3. **规则顺序**：规则按配置顺序执行，所有违反的规则都会被记录
4. **目标字段**：目前只支持 `target: "output"`，未来可能扩展到其他字段