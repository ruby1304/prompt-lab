# Prompt Lab

一个用于快速迭代与验证 Prompt 的实验项目，提供单条验证、批量跑数和多模型对比，同时内置自动评估的分析 Agent。支持 Agent 抽象层管理，让业务需求、测试集和提示词版本统一管理。所有命令均默认使用中文输出。

## 🎯 核心概念

### Agent 抽象层
- **Agent**: 一个业务角色/任务，如 `mem0_l1_summarizer`（对话记忆总结助手）
- **Flow**: Agent 的某个提示词版本/实现版本，如 `mem0_l1_v1`, `mem0_l1_v2`
- **TestSet**: 为 Agent 准备的测试集，如 `mem0_l1.jsonl`

Agent 配置统一管理：
- 业务需求和期望标准
- 评估标准和权重
- 该用哪批测试集
- 当前维护哪些提示词版本

## 📁 目录结构

```
prompt-lab/
├── agents/                    # Agent 配置文件
│   ├── mem0_l1_summarizer.yaml
│   └── asr_cleaner.yaml
├── prompts/                   # Prompt Flow 配置（YAML）
│   ├── mem0_l1_v1.yaml
│   ├── mem0_l1_v2.yaml
│   └── mem0_l1_v3.yaml
├── data/                      # 测试数据和结果
│   ├── mem0_l1.jsonl
│   └── *.eval.csv
├── scripts/                   # 辅助脚本
│   └── quick_eval.sh
└── src/                       # 核心脚本与工具
    ├── agent_registry.py      # Agent 注册管理
    ├── run_agents.py          # Agent 管理命令
    ├── chains.py              # 加载 Prompt Flow 并执行模型调用
    ├── run_single.py          # 单样本验证
    ├── run_batch.py           # 批量跑测试集
    ├── run_compare.py         # 多 Flow 对比
    ├── eval_llm_judge.py      # LLM-as-Judge 自动评估
    ├── eval_rules.py          # 规则评估系统
    └── run_eval.py            # 统一评估命令
```

## 🚀 环境准备

1. 创建 `.env` 并写入你的 OpenAI Key：

   ```bash
   cp .env.example .env
   # 编辑 .env，填入 OPENAI_API_KEY、OPENAI_MODEL_NAME 等
   ```

2. 安装依赖：

   ```bash
   pip install -r requirements.txt
   ```

## 📖 使用指南

### Agent 管理

#### 查看所有 Agents
```bash
python -m src agents list
```

#### 查看特定 Agent 详情
```bash
python -m src agents show mem0_l1_summarizer
```

### 统一评估命令（推荐）

新的 `eval` 命令整合了执行和评估功能，提供一站式解决方案：

```bash
# 单个 flow 执行（带 judge 评估）
python -m src eval --agent mem0_l1_summarizer --flows mem0_l1_v3 --judge --limit 10

# 多个 flow 对比执行（带 judge 评估）
python -m src eval --agent mem0_l1_summarizer --flows mem0_l1_v2,mem0_l1_v3 --judge --limit 10

# 使用 agent 的所有 flows
python -m src eval --agent mem0_l1_summarizer --judge --limit 10
```

### 快速评估脚本

```bash
# 一键完整评估流程
./scripts/quick_eval.sh mem0_l1_summarizer 10
```

### 传统方式（仍然支持）

#### 单条验证
```bash
python -m src.run_single --flow flow_demo --text "你好" --context "可选上下文" --vars '{"user_name": "小明"}'
```

#### 批量跑测试集
```bash
python -m src batch --agent mem0_l1_summarizer
python -m src batch --flow flow_demo --infile test_cases.demo.jsonl --outfile results.demo.csv
```

#### 多 Flow 对比
```bash
python -m src compare --agent mem0_l1_summarizer
python -m src compare --flows mem0_l1_v1,mem0_l1_v2 --infile mem0_l1.jsonl --outfile results.compare.csv
```

## 🎯 评估系统

### LLM-as-Judge 自动评估

基于更强模型（如 doubao-1-5-pro-32k-250115）作为评审员，根据预定义的评估维度进行打分：

```bash
# 自动评估（分析 Agent）
python -m src.eval_llm_judge --agent mem0_l1_summarizer --infile results.csv --outfile eval_results.csv --limit 20

# 分析评估结果
python src/analyze_eval_results.py data/eval_results.csv --details
```

### 规则评估系统

用规则快速过滤明显的 bad case，减少人工评估工作量：

```bash
# 查看支持的规则类型
python -m src.eval_rules list-rules

# 应用规则评估
python -m src.eval_rules run --agent mem0_l1_summarizer --infile input.csv --outfile output.csv

# 查看规则统计
python -m src.eval_rules stats --infile output.csv
```

### 人工评估工作流

```bash
# 1. 生成人工评审表
python -m src.prepare_manual_review --infile results.csv --outfile manual_review.csv

# 2. 用 Excel 打开进行人工打分
# 3. 汇总结果
python -m src.summarize_manual_review summary --infile manual_review.csv
```

## ⚙️ 配置文件

### Agent 配置

在 `agents/*.yaml` 中定义业务 Agent：

```yaml
id: "mem0_l1_summarizer"
name: "对话记忆总结助手"
description: |
  负责处理用户与角色之间的对话历史总结：
  - 提取对话中的关键信息和重要事件
  - 保持用户画像和角色画像的更新

business_goal: |
  在节约 tokens 的前提下，生成高质量的对话总结

expectations:
  must_have:
    - 不遗漏关键的时间和事件信息
    - 准确替换用户和角色的指代词
  nice_to_have:
    - 能识别用户的情绪变化和重要约定

default_testset: "mem0_l1.jsonl"
extra_testsets:
  - "mem0_l1_test01.csv"

flows:
  - name: "mem0_l1_v1"
    file: "mem0_l1_v1.yaml"
    notes: "详细版本，包含完整的工作流程"
  - name: "mem0_l1_v2"
    file: "mem0_l1_v2.yaml"
    notes: "简化版本，专注于对话内容总结"

evaluation:
  criteria:
    - id: "completeness"
      desc: "是否完整保留了对话中的关键信息"
      weight: 0.35
    - id: "conciseness"
      desc: "总结是否简洁，避免冗余信息"
      weight: 0.25
  preferred_judge_model: "doubao-1-5-pro-32k-250115"
  
  # 可选：规则评估配置
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

### Prompt Flow 配置

在 `prompts/*.yaml` 中定义具体的提示词：

```yaml
name: "my_flow"
description: "描述" 
system_prompt: "系统提示词..."
user_template: "用户模板，使用 {变量名} 占位"
defaults:
  某变量: "兜底值"
```

## 🎨 评估维度示例

### 对话记忆总结助手
- **信息完整性 (35%)**: 是否完整保留关键信息
- **简洁性 (25%)**: 总结是否简洁，避免冗余
- **准确性 (25%)**: 指代替换和事实是否正确
- **结构规范性 (15%)**: 输出格式是否规范

### ASR 纠错助手
- **语义忠实度 (40%)**: 是否忠实保留原意
- **清晰度 (30%)**: 纠正后是否更清晰
- **风格正确性 (30%)**: 是否保持合适的语言风格

## 💡 最佳实践

### 评估策略
- **分阶段评估**: 先用小样本验证，再扩大规模
- **重点案例**: 优先评估历史问题案例
- **定期校准**: 人工检查评估质量

### 成本控制
- 使用 `--limit` 参数控制样本数量
- 批量处理多个版本
- 缓存评估结果避免重复

### 结果应用
- 关注维度分析，不只看总分
- 识别问题案例进行人工复盘
- 基于评估结果迭代优化 prompt

## 🔧 变量处理规则

- 模板中未使用的变量可以出现在数据集中，会被自动忽略
- 若数据集中缺少某个变量，优先使用 `defaults`，否则自动用空字符串兜底
- 系统提示词与用户模板共享同一套变量解析逻辑

## 🏆 Agent 系统的优势

1. **业务导向**：每个 Agent 对应一个明确的业务角色和任务
2. **统一管理**：业务需求、测试集、提示词版本都在一个配置文件里
3. **标准化评估**：预定义评估标准和权重，便于自动化评估
4. **版本追踪**：清楚知道每个 flow 的作用和改进方向
5. **简化使用**：一个命令就能跑完整的测试流程

## 📚 详细文档

- [EVALUATION_RULES.md](EVALUATION_RULES.md) - 完整的规则类型说明
- [RULES_QUICK_REFERENCE.md](RULES_QUICK_REFERENCE.md) - 规则系统快速参考
- [MANUAL_EVAL_GUIDE.md](MANUAL_EVAL_GUIDE.md) - 人工评估系统详细指南

## 🔍 故障排除

### 常见问题

1. **模型不存在**: 检查 agent 配置中的 `preferred_judge_model`
2. **JSON 解析错误**: Judge 模型输出格式问题，会显示原始输出
3. **文件格式错误**: 确保输入文件包含必要的列

### 调试技巧

1. 使用 `--limit` 参数测试小样本
2. 检查生成的 prompt 是否合理
3. 验证评估维度权重总和为 1.0

---

通过这套 Prompt Lab 系统，你可以实现数据驱动的 prompt 工程，客观地评估和优化 Agent 性能。🎯