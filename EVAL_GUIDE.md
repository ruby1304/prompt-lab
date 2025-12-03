# LLM-as-Judge 自动评估系统使用指南

## 概述

这个评估系统基于 LLM-as-judge 的思路，可以对 Agent 的输出结果进行自动化评估打分。系统会根据预定义的评估维度，使用更强的模型（如 doubao-1-5-pro-32k-250115）对各个 flow 的输出进行客观评分。

## 系统架构

### 1. Agent 配置文件格式

每个 agent 的配置文件（如 `agents/mem0_l1_summarizer.yaml`）需要包含完整的评估配置：

```yaml
evaluation:
  criteria:
    - id: "completeness"
      name: "信息完整性"
      desc: "是否完整保留了对话中的关键信息（时间、事件、约定等）"
      weight: 0.35
    - id: "conciseness"
      name: "简洁性"
      desc: "总结是否简洁，避免冗余信息"
      weight: 0.25
    - id: "accuracy"
      name: "准确性"
      desc: "用户和角色指代替换是否准确，事实是否正确"
      weight: 0.25
    - id: "structure"
      name: "结构规范性"
      desc: "输出格式是否符合后续处理需求"
      weight: 0.15
  scale:
    min: 0
    max: 10
    overall_strategy: "weighted_average"
  preferred_judge_model: "doubao-1-5-pro-32k-250115"
  temperature: 0.0
```

### 2. 评估脚本

使用 `src/eval_llm_judge.py` 进行自动评估：

```bash
python -m src.eval_llm_judge \
  --agent mem0_l1_summarizer \
  --infile results.compare.csv \
  --outfile mem0_l1.eval.results.csv \
  --limit 50
```

## 使用流程

### 步骤 1: 生成对比结果

首先使用现有的 compare 功能生成不同 flow 的对比结果：

```bash
python -m src.run_compare compare \
  --agent mem0_l1_summarizer \
  --outfile mem0_l1.compare.csv
```

### 步骤 2: 运行自动评估

对生成的对比结果进行 LLM 评估：

```bash
python -m src.eval_llm_judge \
  --agent mem0_l1_summarizer \
  --infile mem0_l1.compare.csv \
  --outfile mem0_l1.eval.csv \
  --limit 50  # 可选：限制评估条数，用于快速测试
```

### 步骤 3: 分析评估结果

评估结果会保存为 CSV 文件，包含以下字段：

- `id`: 测试用例 ID
- `flow`: 被评估的 flow 名称
- `overall_score`: 总体评分（加权平均）
- `overall_comment`: 总体评语
- `{criteria_id}__score`: 各维度评分
- `{criteria_id}__comment`: 各维度评语

## 评估维度说明

### 对话记忆总结助手 (mem0_l1_summarizer)

- **信息完整性 (35%)**: 是否完整保留了对话中的关键信息（时间、事件、约定等）
- **简洁性 (25%)**: 总结是否简洁，避免冗余信息
- **准确性 (25%)**: 用户和角色指代替换是否准确，事实是否正确
- **结构规范性 (15%)**: 输出格式是否符合后续处理需求

### ASR 纠错助手 (asr_cleaner)

- **语义忠实度 (40%)**: 是否忠实保留用户原本想表达的意思，不乱加、不乱删关键信息
- **清晰度 (30%)**: 纠正后的文本是否更好读，歧义更少
- **风格正确性 (30%)**: 是否在不过度书面化的前提下保留儿童口语风格

## 结果分析建议

### 1. 整体性能对比

```python
import pandas as pd

# 读取评估结果
df = pd.read_csv('data/mem0_l1.eval.csv')

# 按 flow 分组计算平均分
flow_scores = df.groupby('flow')['overall_score'].agg(['mean', 'std', 'count'])
print(flow_scores)
```

### 2. 维度分析

```python
# 分析各维度表现
criteria_cols = [col for col in df.columns if col.endswith('__score')]
for col in criteria_cols:
    criterion = col.replace('__score', '')
    print(f"\n{criterion} 维度分析:")
    print(df.groupby('flow')[col].agg(['mean', 'std']))
```

### 3. 问题案例识别

```python
# 找出评分差异较大的案例
df['score_diff'] = df.groupby('id')['overall_score'].transform(lambda x: x.max() - x.min())
problematic_cases = df[df['score_diff'] > 2.0]  # 评分差异超过2分的案例
print("需要人工复盘的案例:")
print(problematic_cases[['id', 'flow', 'overall_score', 'overall_comment']])
```

## 高级功能

### 1. 自定义评估维度

可以在 agent 配置文件中添加新的评估维度：

```yaml
evaluation:
  criteria:
    - id: "creativity"
      name: "创新性"
      desc: "输出是否具有创新性和独特性"
      weight: 0.2
```

### 2. 多次评估取平均

为了提高评估的稳定性，可以多次运行评估并取平均值：

```bash
# 运行多次评估
for i in {1..3}; do
  python -m src.eval_llm_judge \
    --agent mem0_l1_summarizer \
    --infile mem0_l1.compare.csv \
    --outfile mem0_l1.eval.run$i.csv \
    --limit 20
done
```

### 3. 成本效益分析

结合 token 统计数据，可以计算性价比指标：

```python
# 计算性价比 = overall_score / total_tokens
df['cost_efficiency'] = df['overall_score'] / df['total_tokens']
```

## 注意事项

1. **模型配置**: 确保 `preferred_judge_model` 与环境变量中的模型名称一致
2. **评估成本**: LLM 评估会产生额外的 API 调用成本，建议先用小样本测试
3. **评估一致性**: Judge 模型的输出可能存在一定随机性，重要决策建议多次评估
4. **人工验证**: 定期抽查评估结果，确保 Judge 模型的评估质量

## 故障排除

### 常见错误

1. **模型不存在**: 检查 agent 配置中的 `preferred_judge_model` 是否正确
2. **JSON 解析错误**: Judge 模型偶尔可能输出非标准 JSON，系统会报错并显示原始输出
3. **文件格式错误**: 确保输入文件包含必要的列：`id`, `input`, `context`, `expected`, `output__flow_name`

### 调试技巧

1. 使用 `--limit` 参数先测试小样本
2. 检查生成的 prompt 是否合理
3. 验证评估维度的权重是否合理（总和应为1.0）