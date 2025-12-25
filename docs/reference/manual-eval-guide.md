# 人工评估系统使用指南

## 概述

这套系统实现了分层评估架构，用"规则 + 人工"替代昂贵的 LLM 评估：

1. **规则层**：快速过滤明显的 bad case（零 token 成本）
2. **人工层**：对通过规则的样本进行精细打分
3. **Judge 层**（可选）：对争议样本使用 LLM 进行二次判断

## 快速开始

### 1. 查看可用的规则类型

```bash
# 列出所有支持的规则类型
python -m src.eval_rules list-rules

# 查看规则配置示例
python scripts/rule_helper.py examples

# 交互式生成规则配置
python scripts/rule_helper.py generate
```

### 2. 配置规则（可选）

在 `agents/{agent_id}.yaml` 中添加规则：

```yaml
evaluation:
  # ... 其他配置
  rules:
    - id: "not_empty"
      kind: "non_empty"
      target: "output"
      action: "mark_bad"
    
    - id: "reasonable_length"
      kind: "max_chars"
      target: "output"
      max_chars: 1000
      action: "mark_bad"
```

### 3. 验证规则配置

```bash
# 验证 agent 的规则配置
python -m src.eval_rules validate --agent your_agent_id
```

### 4. 完整工作流程

```bash
# 步骤1：生成模型输出对比（如果还没有）
python -m src.run_compare compare --agent mem0_l1_summarizer --outfile mem0_l1.compare.csv

# 步骤2：应用规则评估，过滤明显问题
python -m src.eval_rules run --agent mem0_l1_summarizer --infile mem0_l1.compare.csv --outfile mem0_l1.compare.rules.csv --mode compare

# 步骤3：生成人工评审表
python -m src.prepare_manual_review --infile mem0_l1.compare.rules.csv --outfile mem0_l1.manual_review.csv

# 步骤4：查看规则评估统计
python -m src.eval_rules stats --infile mem0_l1.compare.rules.csv
```

### 2. 人工打分

用 Excel/Numbers 打开 `data/mem0_l1.manual_review.csv`：

- **human_score**: 填写 0-10 分
- **human_label**: 填写 good/bad/edge
- **human_comment**: 简短备注

建议优先关注 `rule_pass=1` 的样本（已通过规则检查）。

### 3. 汇总结果

```bash
# 查看汇总统计
python -m src.summarize_manual_review summary --infile mem0_l1.manual_review.csv

# 导出特定条件的数据
python -m src.summarize_manual_review export_filtered --infile mem0_l1.manual_review.csv --labels good,bad --min_score 7
```

## 规则配置

### 无规则配置
如果不需要规则，可以完全省略 `rules` 部分：
```yaml
evaluation:
  judge_agent_id: "judge_default"
  # 没有 rules 部分，系统会跳过规则检查
```

### 基础规则配置
```yaml
evaluation:
  # ... 其他配置
  rules:
    - id: "not_empty"
      kind: "non_empty"
      target: "output"
      action: "mark_bad"
    
    - id: "reasonable_length"
      kind: "max_chars"
      target: "output"
      max_chars: 1000
      action: "mark_bad"
```

### 查看所有支持的规则类型
```bash
python -m src.eval_rules list-rules
```

详细的规则类型说明请参考 [EVALUATION_RULES.md](evaluation-rules.md)

## 使用场景

### 场景1：规则-only 模式
适合大规模筛查，快速发现 prompt 设计问题：

```bash
python -m src.eval_rules run --agent your_agent --infile results.csv --outfile with_rules.csv
python -m src.eval_rules stats --infile with_rules.csv
```

### 场景2：规则 + 人工模式
适合关键 agent 的精细调参：

```bash
# 完整流程如上所示
# 重点关注通过规则的样本进行人工评估
```

### 场景3：规则 + 人工 + 少量 Judge
对争议样本使用 LLM 进行二次判断：

```bash
# 先完成人工评估
# 然后导出争议样本
python -m src.summarize_manual_review export_filtered --infile manual_review.csv --labels edge --outfile edge_cases.csv

# 对争议样本使用传统 LLM judge（需要转换格式）
```

## 优势

1. **成本控制**：规则层零 token 成本，大幅减少 LLM 调用
2. **效率提升**：人工只需关注通过规则的"合格"样本
3. **质量保证**：人工判断比 LLM judge 更准确，特别是对业务逻辑的理解
4. **灵活配置**：规则可以根据不同 agent 的特点灵活调整
5. **可追溯性**：每个评估决策都有明确的规则或人工依据

## 最佳实践

1. **规则设计**：
   - 从宽松开始，逐步收紧
   - 优先过滤明显的硬伤（空输出、超长、格式错误）
   - 根据业务需求添加内容质量规则

2. **人工评估**：
   - 建立清晰的评分标准
   - 多人评估时保持标准一致性
   - 记录典型 case 作为参考

3. **迭代优化**：
   - 根据人工评估结果调整规则
   - 定期回顾和更新评估标准
   - 积累评估经验，逐步自动化更多判断

## 演示脚本

```bash
# 运行完整演示
python scripts/demo_manual_eval.py demo --agent mem0_l1_summarizer

# 生成示例打分（仅用于演示）
python scripts/demo_fill_scores.py --infile manual_review.csv --outfile manual_review.demo.csv

# 查看汇总结果
python scripts/demo_manual_eval.py summary_demo --review_file manual_review.demo.csv
```

这套系统让你能够以最小的成本获得最高质量的评估结果，特别适合需要精细调优的生产环境。