# 规则系统快速参考

## 🎯 核心概念

规则系统让你为每个 Agent 配置自定义规则，用于快速过滤明显的 bad case，减少人工评估工作量。

## 📋 快速命令

```bash
# 查看所有支持的规则类型
python -m src.eval_rules list-rules

# 查看规则配置示例
python scripts/rule_helper.py examples

# 验证 agent 规则配置
python -m src.eval_rules validate --agent your_agent

# 应用规则评估
python -m src.eval_rules run --agent your_agent --infile input.csv --outfile output.csv

# 查看规则统计
python -m src.eval_rules stats --infile output.csv
```

## 🔧 配置位置

在 `agents/{agent_id}.yaml` 文件中：

```yaml
evaluation:
  # ... 其他配置
  rules:  # 可选，不需要规则时可以完全删除这部分
    - id: "rule_unique_id"
      kind: "rule_type"
      target: "output"
      # ... 规则参数
      action: "mark_bad"
```

## 📚 支持的规则类型

| 规则类型 | 用途 | 示例 |
|----------|------|------|
| `non_empty` | 确保输出不为空 | 基础检查 |
| `max_chars` | 限制最大字符数 | 长度控制 |
| `max_tokens` | 限制最大 token 数 | 长度控制 |
| `allowed_values` | 限制输出值范围 | 分类/二元判断 |
| `contains_any` | 必须包含关键词 | 内容质量 |
| `regex_match` | 正则表达式匹配 | 格式检查 |
| `starts_with` | 前缀检查 | 格式要求 |
| `ends_with` | 后缀检查 | 格式要求 |

## 🚀 常用配置模板

### 最小规则集（推荐起点）
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

### 对话总结 Agent
```yaml
rules:
  - id: "summary_length"
    kind: "max_tokens"
    target: "output"
    max_tokens: 300
    action: "mark_bad"
  
  - id: "must_mention_dialogue"
    kind: "contains_any"
    target: "output"
    keywords: ["用户", "角色", "对话", "交流"]
    ignore_case: true
    action: "mark_bad"
```

### 分类 Agent
```yaml
rules:
  - id: "valid_category_only"
    kind: "allowed_values"
    target: "output"
    allowed_values: ["positive", "negative", "neutral"]
    trim: true
    action: "mark_bad"
```

### 二元判断 Agent
```yaml
rules:
  - id: "binary_only"
    kind: "allowed_values"
    target: "output"
    allowed_values: ["0", "1", "yes", "no"]
    trim: true
    action: "mark_bad"
```

## 💡 最佳实践

1. **从简单开始**：先配置基础规则（非空、长度），再根据需要添加
2. **避免过严**：规则应该过滤明显错误，不要替代人工判断
3. **测试验证**：使用 `validate` 命令检查配置正确性
4. **查看统计**：通过 `stats` 命令了解规则效果
5. **无规则也OK**：不需要规则时可以完全省略 `rules` 部分

## 📖 详细文档

- [EVALUATION_RULES.md](EVALUATION_RULES.md) - 完整的规则类型说明
- [MANUAL_EVAL_GUIDE.md](MANUAL_EVAL_GUIDE.md) - 完整的评估系统指南