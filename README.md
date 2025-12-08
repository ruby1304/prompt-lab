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
├── agents/                    # Agent 配置和资源（按Agent分组）
│   ├── mem0_l1_summarizer/    # 对话记忆总结助手
│   │   ├── agent.yaml         # Agent配置
│   │   ├── prompts/           # 提示词版本
│   │   │   ├── mem0_l1_v1.yaml
│   │   │   ├── mem0_l1_v2.yaml
│   │   │   └── mem0_l1_v3.yaml
│   │   └── testsets/          # 测试集
│   │       └── mem0_l1.jsonl
│   ├── asr_cleaner/           # ASR纠错助手
│   │   ├── agent.yaml
│   │   ├── prompts/
│   │   └── testsets/
│   ├── judge_default/         # 通用评估Agent
│   │   ├── agent.yaml
│   │   └── prompts/
│   │       ├── judge_v1.yaml
│   │       └── judge_v2.yaml
│   └── _template/             # 新Agent创建模板
├── prompts/                   # 全局通用提示词（可选）
│   ├── analysis_agent.yaml
│   └── flow_demo.yaml
├── data/                      # 运行时数据（不进Git）
│   ├── runs/                  # 执行结果
│   │   ├── mem0_l1_summarizer/
│   │   └── asr_cleaner/
│   └── evals/                 # 评估结果
│       ├── mem0_l1_summarizer/
│       └── asr_cleaner/
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

#### 创建新 Agent
```bash
# 1. 复制模板
cp -r agents/_template agents/your_new_agent

# 2. 编辑配置
cd agents/your_new_agent
# 修改 agent.yaml 中的 id、name、description 等
# 修改 prompts/your_agent_v1.yaml 中的提示词
# 修改 testsets/default.jsonl 中的测试用例

# 3. 测试新 Agent
python -m src agents show your_new_agent
python -m src eval --agent your_new_agent --limit 3
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

基于更强模型（如 doubao-1-5-pro-32k-250115）作为评审员，**根据每个Agent的业务目标和约束自动生成评估标准**进行打分：

```bash
# 自动评估（分析 Agent）
python -m src.eval_llm_judge --agent mem0_l1_summarizer --infile results.csv --outfile eval_results.csv --limit 20

# 分析评估结果
python src/analyze_eval_results.py data/eval_results.csv --details
```

**评估特点**：
- **动态评估维度**：不依赖固定的评估维度，而是从Agent的`business_goal`、`must_have`、`nice_to_have`中自动抽取评价要点
- **业务导向**：评估标准完全基于具体的业务需求，更贴近实际应用场景
- **灵活输入格式**：通过`case_fields`配置支持复杂的测试用例结构

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

在 `agents/{agent_id}/agent.yaml` 中定义业务 Agent：

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
  judge_agent_id: "judge_default"
  judge_flow: "judge_v2"
  scale:
    min: 0
    max: 10
  preferred_judge_model: "doubao-1-5-pro-32k-250115"
  temperature: 0.0
  
  # 可选：规则评估配置
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
  
  # 可选：自定义测试用例字段配置
  case_fields:
    - key: "chat_round_30"
      label: "对话历史"
      section: "primary_input"
      required: true
    - key: "character_profile"
      label: "角色画像"
      section: "context"
      required: true
      truncate: 4000
```

### Prompt Flow 配置

在 `agents/{agent_id}/prompts/*.yaml` 中定义具体的提示词：

```yaml
name: "my_flow"
description: "描述" 
system_prompt: "系统提示词..."
user_template: "用户模板，使用 {变量名} 占位"
defaults:
  某变量: "兜底值"
```

## 🎨 评估系统工作原理

### 动态评估维度生成

系统不使用固定的评估维度，而是根据每个Agent的配置自动生成评估标准：

**输入**：
- `business_goal`: 业务目标描述
- `must_have`: 硬性约束条件
- `nice_to_have`: 加分项条件

**输出**：
- Judge模型自动推导出适合该Agent的评估要点
- 基于业务约束进行must_have/nice_to_have检查
- 生成针对性的评分和评语

### 评估结果示例

```json
{
  "derived_criteria": [
    {
      "name": "关键信息提取完整性",
      "from": "must_have",
      "importance": "high"
    }
  ],
  "must_have_check": [
    {
      "item": "不遗漏关键的时间和事件信息",
      "satisfied": true,
      "score": 9,
      "comment": "准确提取了所有时间节点和重要事件"
    }
  ],
  "overall_score": 8,
  "overall_comment": "总结质量良好，信息完整且表达简洁"
}
```

## 💡 最佳实践

### 评估策略
- **分阶段评估**: 先用小样本验证，再扩大规模
- **重点案例**: 优先评估历史问题案例
- **业务对齐**: 确保Agent的`must_have`和`nice_to_have`准确反映业务需求

### 成本控制
- 使用 `--limit` 参数控制样本数量
- 先用规则过滤明显问题，减少Judge调用
- 批量处理多个版本

### 结果应用
- 重点关注`must_have_check`的满足情况
- 分析`derived_criteria`了解Judge的评估逻辑
- 基于业务约束检查结果优化prompt

## 🔧 变量处理规则

- 模板中未使用的变量可以出现在数据集中，会被自动忽略
- 若数据集中缺少某个变量，优先使用 `defaults`，否则自动用空字符串兜底
- 系统提示词与用户模板共享同一套变量解析逻辑

## 🏆 Agent 系统的优势

1. **业务导向**：每个 Agent 对应一个明确的业务角色和任务
2. **统一管理**：业务需求、测试集、提示词版本都在一个目录里
3. **标准化评估**：预定义评估标准和权重，便于自动化评估
4. **版本追踪**：清楚知道每个 flow 的作用和改进方向
5. **简化使用**：一个命令就能跑完整的测试流程
6. **模板化创建**：使用 `agents/_template` 快速创建新Agent
7. **物理聚合**：相关文件都在同一目录下，便于维护

## 📚 详细文档

- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) - 项目结构详细说明
- [DATA_STRUCTURE_GUIDE.md](DATA_STRUCTURE_GUIDE.md) - 数据目录结构指南
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