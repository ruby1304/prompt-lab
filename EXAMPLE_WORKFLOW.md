# LLM-as-Judge 评估系统完整示例

这个文档展示了如何使用 LLM-as-judge 评估系统的完整工作流程。

## 示例场景

我们有一个对话记忆总结助手，有两个版本的 prompt（v2 和 v3），想要客观地评估哪个版本表现更好。

## 步骤 1: 准备 Agent 配置

确保 `agents/mem0_l1_summarizer.yaml` 包含完整的评估配置：

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

## 步骤 2: 生成对比结果

```bash
# 运行对比测试，生成两个版本的输出结果
python -m src.run_compare compare \
  --agent mem0_l1_summarizer \
  --outfile mem0_l1.compare.csv
```

这会生成一个包含以下列的 CSV 文件：
- `id`: 测试用例 ID
- `input`, `context`, `expected`: 测试数据
- `output__mem0_l1_v2`: v2 版本的输出
- `output__mem0_l1_v3`: v3 版本的输出
- 各种 token 统计信息

## 步骤 3: 运行 LLM 评估

```bash
# 对所有结果进行评估（可能比较耗时和费用）
python -m src.eval_llm_judge \
  --agent mem0_l1_summarizer \
  --infile mem0_l1.compare.csv \
  --outfile mem0_l1.eval.full.csv

# 或者先用小样本测试
python -m src.eval_llm_judge \
  --agent mem0_l1_summarizer \
  --infile mem0_l1.compare.csv \
  --outfile mem0_l1.eval.sample.csv \
  --limit 20
```

## 步骤 4: 分析评估结果

```bash
# 运行分析脚本
python src/analyze_eval_results.py data/mem0_l1.eval.sample.csv --details
```

### 示例输出解读

```
Flow 性能对比
┏━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━┓
┃ Flow       ┃ 样本数 ┃ 平均分 ┃ 标准差 ┃ 最低分 ┃ 最高分 ┃
┡━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━┩
│ mem0_l1_v2 │      2 │   7.85 │   0.21 │    7.7 │    8.0 │
│ mem0_l1_v3 │      2 │   8.50 │   0.00 │    8.5 │    8.5 │
└────────────┴────────┴────────┴────────┴────────┴────────┘
```

**解读**: v3 版本平均分比 v2 高 0.65 分，且更稳定（标准差为 0）。

```
各维度平均得分
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ 维度         ┃ mem0_l1_v2 ┃ mem0_l1_v3 ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ accuracy     │       8.00 │       9.50 │
│ completeness │       8.00 │       9.50 │
│ conciseness  │       7.50 │       8.00 │
│ structure    │       8.00 │       8.00 │
└──────────────┴────────────┴────────────┘
```

**解读**: v3 在准确性和完整性方面显著优于 v2，这两个维度权重较高，解释了总分差异。

## 步骤 5: 深入分析（可选）

### 使用 Python 进行更详细的分析

```python
import pandas as pd
import matplotlib.pyplot as plt

# 读取评估结果
df = pd.read_csv('data/mem0_l1.eval.sample.csv')

# 1. 可视化 Flow 性能对比
flow_scores = df.groupby('flow')['overall_score'].mean()
flow_scores.plot(kind='bar', title='Flow 平均得分对比')
plt.ylabel('平均得分')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('flow_comparison.png')
plt.show()

# 2. 维度雷达图
import numpy as np

criteria_cols = [col for col in df.columns if col.endswith('__score') and col != 'overall_score']
flows = df['flow'].unique()

fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))

for flow in flows:
    flow_data = df[df['flow'] == flow]
    scores = [flow_data[col].mean() for col in criteria_cols]
    
    # 闭合雷达图
    scores += scores[:1]
    angles = np.linspace(0, 2 * np.pi, len(criteria_cols), endpoint=False).tolist()
    angles += angles[:1]
    
    ax.plot(angles, scores, 'o-', linewidth=2, label=flow)
    ax.fill(angles, scores, alpha=0.25)

ax.set_xticks(angles[:-1])
ax.set_xticklabels([col.replace('__score', '') for col in criteria_cols])
ax.set_ylim(0, 10)
ax.set_title('各维度得分雷达图', size=16)
ax.legend()
plt.tight_layout()
plt.savefig('criteria_radar.png')
plt.show()

# 3. 识别需要改进的案例
problematic_cases = df[df['overall_score'] < 8.0]
if len(problematic_cases) > 0:
    print("需要改进的案例:")
    print(problematic_cases[['id', 'flow', 'overall_score', 'overall_comment']])
```

## 步骤 6: 基于结果优化 Prompt

根据评估结果，我们发现：

1. **v3 在准确性和完整性方面更好** → 可以将 v3 的相关技巧应用到其他 prompt
2. **简洁性还有提升空间** → 可以在 prompt 中加入更明确的长度控制指令
3. **结构规范性两个版本相当** → 这部分已经比较成熟

### 优化建议

```yaml
# 在 prompts/mem0_l1_v4.yaml 中结合两个版本的优点
system: |
  你是一个专业的对话记忆总结助手。请根据以下要求总结对话：
  
  1. 完整性：确保包含所有关键时间、事件、约定信息（借鉴 v3）
  2. 准确性：准确替换用户和角色指代词，不添加原文没有的信息（借鉴 v3）
  3. 简洁性：控制输出长度，避免冗余表述，每个要点用最简洁的语言表达
  4. 结构性：按时间顺序组织，使用清晰的格式
```

## 步骤 7: 验证优化效果

```bash
# 创建新版本后，重新运行评估
python -m src.run_compare compare \
  --agent mem0_l1_summarizer \
  --flows mem0_l1_v3,mem0_l1_v4 \
  --outfile mem0_l1.v3_v4.compare.csv

python -m src.eval_llm_judge \
  --agent mem0_l1_summarizer \
  --infile mem0_l1.v3_v4.compare.csv \
  --outfile mem0_l1.v3_v4.eval.csv \
  --limit 20

python src/analyze_eval_results.py data/mem0_l1.v3_v4.eval.csv --details
```

## 成本控制建议

1. **分阶段评估**: 先用 10-20 个样本快速验证，再扩大规模
2. **重点案例**: 优先评估历史上表现差异较大的测试用例
3. **批量处理**: 一次性评估多个版本，减少重复的 context 处理
4. **缓存结果**: 保存评估结果，避免重复评估相同的输出

## 最佳实践

1. **定期校准**: 定期人工检查 Judge 模型的评估质量
2. **多维度平衡**: 不要只关注总分，要分析各维度的表现
3. **版本管理**: 为每次评估结果添加时间戳和版本标记
4. **文档记录**: 记录每次优化的依据和预期效果

通过这套完整的工作流程，你可以客观地评估和优化 Agent 的性能，实现数据驱动的 prompt 工程。