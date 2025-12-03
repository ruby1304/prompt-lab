# LLM-as-Judge 自动评估系统

## 🎯 系统概述

这是一个基于 LLM-as-judge 思路的自动化评估系统，可以客观地评估和对比不同 Agent flow 的性能表现。系统使用更强的模型（如 doubao-1-5-pro-32k-250115）作为评审员，根据预定义的评估维度对输出结果进行打分和点评。

## ✨ 核心特性

- **多维度评估**: 支持自定义评估维度，每个维度可设置权重和描述
- **自动化流程**: 从对比测试到评估分析的完整自动化工作流
- **详细分析**: 提供统计分析、维度对比、问题案例识别等功能
- **成本控制**: 支持样本限制、批量处理等成本控制措施
- **可视化结果**: 清晰的表格和图表展示评估结果

## 🚀 快速开始

### 1. 一键评估

```bash
# 使用快速评估脚本（推荐）
./scripts/quick_eval.sh mem0_l1_summarizer 10

# 或者手动执行步骤
python -m src.run_compare --agent mem0_l1_summarizer --outfile compare_results.csv
python -m src.eval_llm_judge --agent mem0_l1_summarizer --infile compare_results.csv --outfile eval_results.csv --limit 10
python src/analyze_eval_results.py data/eval_results.csv --details
```

### 2. 查看结果

评估完成后会生成：
- **对比结果文件**: 包含不同 flow 的输出对比
- **评估结果文件**: 包含详细的评分和点评
- **分析报告**: 统计分析和改进建议

## 📊 评估维度示例

### 对话记忆总结助手
- **信息完整性 (35%)**: 是否完整保留关键信息
- **简洁性 (25%)**: 总结是否简洁，避免冗余
- **准确性 (25%)**: 指代替换和事实是否正确
- **结构规范性 (15%)**: 输出格式是否规范

### ASR 纠错助手
- **语义忠实度 (40%)**: 是否忠实保留原意
- **清晰度 (30%)**: 纠正后是否更清晰
- **风格正确性 (30%)**: 是否保持合适的语言风格

## 📁 文件结构

```
├── src/
│   ├── eval_llm_judge.py      # 核心评估脚本
│   └── analyze_eval_results.py # 结果分析脚本
├── scripts/
│   └── quick_eval.sh          # 快速评估脚本
├── agents/
│   ├── mem0_l1_summarizer.yaml # Agent 配置（含评估维度）
│   └── asr_cleaner.yaml
├── data/
│   ├── *.compare.csv          # 对比结果文件
│   └── *.eval.csv             # 评估结果文件
├── EVAL_GUIDE.md              # 详细使用指南
├── EXAMPLE_WORKFLOW.md        # 完整示例工作流
└── README_EVAL.md             # 本文档
```

## 🔧 配置说明

### Agent 配置文件

在 `agents/{agent}.yaml` 中添加评估配置：

```yaml
evaluation:
  criteria:
    - id: "completeness"
      name: "信息完整性"
      desc: "是否完整保留了对话中的关键信息"
      weight: 0.35
    - id: "accuracy"
      name: "准确性"
      desc: "用户和角色指代替换是否准确"
      weight: 0.25
  scale:
    min: 0
    max: 10
    overall_strategy: "weighted_average"
  preferred_judge_model: "doubao-1-5-pro-32k-250115"
  temperature: 0.0
```

### 环境变量

确保 `.env` 文件包含正确的模型配置：

```env
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=your_base_url
OPENAI_MODEL_NAME=doubao-1-5-pro-32k-250115
```

## 📈 结果分析

### 性能对比示例

```
Flow 性能统计
┏━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━┓
┃ Flow       ┃ 样本数 ┃ 平均分 ┃ 标准差 ┃
┡━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━┩
│ mem0_l1_v2 │     10 │   7.85 │   0.21 │
│ mem0_l1_v3 │     10 │   8.50 │   0.15 │
└────────────┴────────┴────────┴────────┘
```

### 维度分析示例

```
各维度平均得分
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ 维度         ┃ mem0_l1_v2 ┃ mem0_l1_v3 ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ completeness │       8.00 │       9.50 │
│ accuracy     │       8.00 │       9.50 │
│ conciseness  │       7.50 │       8.00 │
│ structure    │       8.00 │       8.00 │
└──────────────┴────────────┴────────────┘
```

## 💡 最佳实践

### 1. 评估策略
- **分阶段评估**: 先用小样本验证，再扩大规模
- **重点案例**: 优先评估历史问题案例
- **定期校准**: 人工检查评估质量

### 2. 成本控制
- 使用 `--limit` 参数控制样本数量
- 批量处理多个版本
- 缓存评估结果避免重复

### 3. 结果应用
- 关注维度分析，不只看总分
- 识别问题案例进行人工复盘
- 基于评估结果迭代优化 prompt

## 🛠️ 高级功能

### 1. 自定义评估维度

```yaml
evaluation:
  criteria:
    - id: "creativity"
      name: "创新性"
      desc: "输出是否具有创新性和独特性"
      weight: 0.2
```

### 2. 多次评估取平均

```bash
for i in {1..3}; do
  python -m src.eval_llm_judge --agent mem0_l1_summarizer --infile results.csv --outfile eval_run$i.csv --limit 20
done
```

### 3. 成本效益分析

```python
# 计算性价比 = overall_score / total_tokens
df['cost_efficiency'] = df['overall_score'] / df['total_tokens']
```

## 🔍 故障排除

### 常见问题

1. **模型不存在**: 检查 agent 配置中的 `preferred_judge_model`
2. **JSON 解析错误**: Judge 模型输出格式问题，会显示原始输出
3. **文件格式错误**: 确保输入文件包含必要的列

### 调试技巧

1. 使用 `--limit` 参数测试小样本
2. 检查生成的 prompt 是否合理
3. 验证评估维度权重总和为 1.0

## 📚 相关文档

- [详细使用指南](EVAL_GUIDE.md)
- [完整示例工作流](EXAMPLE_WORKFLOW.md)
- [Agent 升级指南](AGENT_UPGRADE.md)

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个评估系统！

---

通过这套 LLM-as-judge 评估系统，你可以客观地评估和优化 Agent 性能，实现数据驱动的 prompt 工程。🎯