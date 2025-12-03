# Prompt Lab

一个用于快速迭代与验证 Prompt 的实验项目，提供单条验证、批量跑数和多模型对比，同时内置自动评估的分析 Agent。支持 Agent 抽象层管理，让业务需求、测试集和提示词版本统一管理。所有命令均默认使用中文输出。

## 核心概念

### Agent 抽象层 🆕
- **Agent**: 一个业务角色/任务，如 `mem0_l1_summarizer`（对话记忆总结助手）
- **Flow**: Agent 的某个提示词版本/实现版本，如 `mem0_l1_v1`, `mem0_l1_v2`
- **TestSet**: 为 Agent 准备的测试集，如 `mem0_l1.jsonl`

Agent 配置统一管理：
- 业务需求和期望标准
- 评估标准和权重
- 该用哪批测试集
- 当前维护哪些提示词版本

这样避免以后搞不清哪个 flow 在服务谁，哪个测试集对应什么业务场景。

## 目录结构

```
prompt-lab/
├── agents/                    # 🆕 Agent 配置文件
│   └── mem0_l1_summarizer.yaml
├── prompts/                   # Prompt Flow 配置（YAML）
│   ├── mem0_l1_v1.yaml
│   ├── mem0_l1_v2.yaml
│   └── mem0_l1_v3.yaml
├── data/                      # 测试数据和结果
│   ├── mem0_l1.jsonl
│   └── mem0_l1_test01.csv
└── src/                       # 核心脚本与工具
    ├── agent_registry.py      # 🆕 Agent 注册管理
    ├── run_agents.py          # 🆕 Agent 管理命令
    ├── chains.py              # 加载 Prompt Flow 并执行模型调用
    ├── run_single.py          # 单样本验证
    ├── run_batch.py           # 批量跑测试集（支持 Agent）
    ├── run_compare.py         # 多 Flow 对比（支持 Agent）
    └── run_analysis.py        # 自动评估模型输出
```

## 环境准备

1. 创建 `.env` 并写入你的 OpenAI Key：

   ```bash
   cp .env.example .env
   # 编辑 .env，填入 OPENAI_API_KEY、OPENAI_MODEL_NAME 等
   ```

2. 安装依赖：

   ```bash
   pip install -r requirements.txt
   ```

## 使用指南

### 🆕 Agent 管理

#### 查看所有 Agents
```bash
python -m src agents list
```

#### 查看特定 Agent 详情
```bash
python -m src agents show mem0_l1_summarizer
```

#### 使用 Agent 批量运行（推荐）
```bash
# 使用默认配置（默认 flow + 默认测试集）
python -m src batch --agent mem0_l1_summarizer

# 指定特定 flow
python -m src batch --agent mem0_l1_summarizer --flow mem0_l1_v2

# 指定特定测试集
python -m src batch --agent mem0_l1_summarizer --infile mem0_l1_test01.csv
```

#### 使用 Agent 对比所有版本
```bash
# 对比 agent 的所有 flows
python -m src compare --agent mem0_l1_summarizer

# 对比指定的 flows
python -m src compare --agent mem0_l1_summarizer --flows mem0_l1_v2,mem0_l1_v3
```

### 传统方式（仍然支持）

#### 1）单条验证
```bash
python -m src.run_single --flow flow_demo --text "你好" --context "可选上下文" --vars '{"user_name": "小明"}'
```

#### 2）批量跑测试集
```bash
python -m src batch --flow flow_demo --infile test_cases.demo.jsonl --outfile results.demo.csv
```

#### 3）多 Flow 对比
```bash
python -m src compare --flows mem0_l1_v1,mem0_l1_v2 --infile mem0_l1.jsonl --outfile results.compare.csv
```

#### 4）自动评估（分析 Agent）
```bash
python -m src.run_analysis --infile results.demo.csv --output-column output --flow analysis_agent
```

## 配置文件

### 🆕 Agent 配置

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
  preferred_judge_model: "gpt-4o-mini"
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

## Agent 系统的优势

1. **业务导向**：每个 Agent 对应一个明确的业务角色和任务
2. **统一管理**：业务需求、测试集、提示词版本都在一个配置文件里
3. **标准化评估**：预定义评估标准和权重，便于自动化评估
4. **版本追踪**：清楚知道每个 flow 的作用和改进方向
5. **简化使用**：一个命令就能跑完整的测试流程

## 变量处理规则

- 模板中未使用的变量可以出现在数据集中，会被自动忽略
- 若数据集中缺少某个变量，优先使用 `defaults`，否则自动用空字符串兜底
- 系统提示词与用户模板共享同一套变量解析逻辑

