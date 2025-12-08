# 项目结构指南

## 新的目录结构（2025年12月重构）

项目现在采用 **以Agent为中心** 的目录结构，将配置、提示词、测试集物理聚合：

```
prompt-lab/
├── agents/                    # Agent源码目录（进Git）
│   ├── mem0_l1_summarizer/    # 按Agent分组
│   │   ├── agent.yaml         # Agent配置
│   │   ├── prompts/           # 提示词版本
│   │   │   ├── mem0_l1_v1.yaml
│   │   │   ├── mem0_l1_v2.yaml
│   │   │   └── mem0_l1_v3.yaml
│   │   └── testsets/          # 测试集
│   │       └── mem0_l1.jsonl
│   ├── asr_cleaner/
│   │   ├── agent.yaml
│   │   ├── prompts/
│   │   └── testsets/
│   └── _template/             # 新Agent创建模板
├── prompts/                   # 全局通用提示词（可选）
└── data/                      # 运行时数据（不进Git）
    ├── runs/                  # 执行结果
    │   ├── mem0_l1_summarizer/
    │   │   ├── 2025-12-04T11-05-01_batch_mem0_l1_v1.csv
    │   │   └── 2025-12-04T11-05-29_compare_mem0_l1_v1_mem0_l1_v2.csv
    │   └── asr_cleaner/
    └── evals/                 # 评估结果
        ├── mem0_l1_summarizer/
        │   ├── rules/         # 规则评估结果
        │   ├── manual/        # 人工评审结果
        │   └── llm/           # LLM评估结果
        └── asr_cleaner/
```

## 文件命名规范

### 运行输出文件
- 单flow批量运行：`{timestamp}_batch_{flow_name}.csv`
- 多flow对比运行：`{timestamp}_compare_{flow1}_{flow2}_{...}.csv`

### 评估结果文件
- 规则评估：`{base_name}.rules.csv`
- 人工评审：`{base_name}.manual.csv`
- LLM评估：`{base_name}.judge.csv`

## 使用方式

### 1. 基本执行（自动路径）

```bash
# 单flow执行，自动使用默认测试集和输出路径
python -m src.run_eval --agent mem0_l1_summarizer --flows mem0_l1_v1

# 多flow对比，自动路径
python -m src.run_eval --agent mem0_l1_summarizer --flows mem0_l1_v1,mem0_l1_v2
```

### 2. 规则评估

```bash
# 对运行结果应用规则评估，自动输出到 evals/{agent}/rules/
python -m src.eval_rules run --agent mem0_l1_summarizer --infile 2025-12-04T11-05-29_compare_mem0_l1_v1_mem0_l1_v2.csv
```

### 3. 统计规则结果

```bash
# 统计规则评估结果
python -m src.eval_rules stats --agent mem0_l1_summarizer --infile 2025-12-04T11-05-29_compare_mem0_l1_v1_mem0_l1_v2.rules.csv
```

## 路径解析规则

### 1. Agent配置文件
- 新结构：`agents/{agent_id}/agent.yaml`
- 兼容旧结构：`agents/{agent_id}.yaml`

### 2. 提示词文件
- 优先：`agents/{agent_id}/prompts/{flow_name}.yaml`
- 兼容：`prompts/{flow_name}.yaml`

### 3. 测试集路径
- 优先：`agents/{agent_id}/testsets/{testset_file}`
- 兼容：`data/testsets/{agent_id}/{testset_file}`
- 未指定 `--infile` → 使用 agent 的 `default_testset`

### 4. 输出路径
- 未指定 `--outfile` → 自动生成到 `data/runs/{agent_id}/`
- 指定相对路径 → `data/runs/{agent_id}/{outfile}`
- 指定绝对路径 → 直接使用

### 5. 评估结果路径
- 规则评估 → `data/evals/{agent_id}/rules/`
- 人工评审 → `data/evals/{agent_id}/manual/`
- LLM评估 → `data/evals/{agent_id}/llm/`

## 新结构的优势

1. **物理聚合**：Agent的配置、提示词、测试集都在同一目录
2. **模板化创建**：使用 `agents/_template` 快速创建新Agent
3. **清晰分离**：源码（agents/）与运行时数据（data/）分离
4. **版本控制友好**：只有源码进Git，运行结果不污染仓库
5. **维护简单**：新增Agent时只需要复制一个目录
6. **向后兼容**：支持旧结构的文件查找

## 创建新Agent

```bash
# 1. 复制模板
cp -r agents/_template agents/your_new_agent

# 2. 修改配置
cd agents/your_new_agent
# 编辑 agent.yaml - 更新id、name、description等
# 编辑 prompts/your_agent_v1.yaml - 设计提示词
# 编辑 testsets/default.jsonl - 准备测试用例

# 3. 测试
python -m src agents show your_new_agent
python -m src eval --agent your_new_agent --limit 3
```

## 迁移说明

项目已从旧的分散式结构迁移到新的Agent中心式结构：
- `agents/*.yaml` → `agents/{agent_id}/agent.yaml`
- `prompts/{agent_id}_*.yaml` → `agents/{agent_id}/prompts/*.yaml`
- `data/testsets/{agent_id}/*` → `agents/{agent_id}/testsets/*`

现有脚本完全兼容新结构，并保持对旧路径的兼容性。