# 项目结构说明

## 概述

Prompt Lab 采用 **以Agent为中心** 的目录结构，将每个Agent的配置、提示词、测试集物理聚合在同一目录下，提供清晰的组织方式和便捷的维护体验。

## 目录结构

```
prompt-lab/
├── agents/                    # Agent源码目录（进Git）
│   ├── mem0_l1_summarizer/    # 对话记忆总结助手
│   │   ├── agent.yaml         # Agent配置文件
│   │   ├── prompts/           # 提示词版本管理
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
│       ├── agent.yaml
│       ├── prompts/
│       │   └── your_agent_v1.yaml
│       ├── testsets/
│       │   └── default.jsonl
│       └── README.md
├── prompts/                   # 全局通用提示词（可选保留）
│   ├── analysis_agent.yaml
│   └── flow_demo.yaml
├── data/                      # 运行时数据（不进Git）
│   ├── runs/                  # 执行结果
│   │   ├── mem0_l1_summarizer/
│   │   └── asr_cleaner/
│   └── evals/                 # 评估结果
│       ├── mem0_l1_summarizer/
│       │   ├── rules/
│       │   ├── manual/
│       │   └── llm/
│       └── asr_cleaner/
├── src/                       # 核心代码
├── scripts/                   # 辅助脚本
├── .gitignore                 # 版本控制配置
├── README.md                  # 项目主文档
├── DATA_STRUCTURE_GUIDE.md    # 数据结构指南
└── PROJECT_STRUCTURE.md       # 本文档
```

## 设计原则

### 1. 物理聚合
- 每个Agent的所有相关文件都在 `agents/{agent_id}/` 目录下
- 配置、提示词、测试集就近存放，便于维护
- 减少跨目录跳转，降低认知负担

### 2. 源码与运行时分离
- **源码**：`agents/` 目录，进入版本控制
- **运行时数据**：`data/` 目录，不进入版本控制
- 清晰的职责分离，避免仓库污染

### 3. 模板化创建
- `agents/_template/` 提供标准模板
- 新建Agent只需复制目录并修改配置
- 标准化的文件结构和命名规范

### 4. 向后兼容
- 支持旧结构的文件查找
- 渐进式迁移，不破坏现有工作流
- 兼容绝对路径的使用方式

## 文件查找优先级

### Agent配置
1. `agents/{agent_id}/agent.yaml` (新结构)
2. `agents/{agent_id}.yaml` (旧结构兼容)

### 提示词文件
1. `agents/{agent_id}/prompts/{flow_name}.yaml` (新结构)
2. `prompts/{flow_name}.yaml` (全局目录兼容)

### 测试集文件
1. `agents/{agent_id}/testsets/{testset_file}` (新结构)
2. `data/testsets/{agent_id}/{testset_file}` (旧结构兼容)

## 创建新Agent

### 快速开始
```bash
# 1. 复制模板
cp -r agents/_template agents/your_new_agent

# 2. 进入目录
cd agents/your_new_agent

# 3. 修改配置
# 编辑 agent.yaml - 更新id、name、description等
# 编辑 prompts/your_agent_v1.yaml - 设计提示词
# 编辑 testsets/default.jsonl - 准备测试用例

# 4. 测试Agent
python -m src agents show your_new_agent
python -m src eval --agent your_new_agent --limit 3
```

### 配置要点
1. **agent.yaml**：确保 `id` 字段与目录名一致
2. **prompts/**：文件名要与 `agent.yaml` 中的 `flows.file` 对应
3. **testsets/**：文件名要与 `agent.yaml` 中的 `default_testset` 对应

## 版本控制

### 进入Git的文件
- `agents/` 目录下的所有文件
- 项目配置和文档文件
- 源代码文件

### 不进入Git的文件
- `data/runs/` - 执行结果
- `data/evals/` - 评估结果
- `data/testsets/` - 旧结构兼容目录（已迁移）
- 临时文件和日志

## 优势总结

1. **维护简单**：相关文件聚合，新增Agent只需复制一个目录
2. **结构清晰**：按业务功能分组，而非按文件类型分组
3. **模板标准**：统一的创建流程和文件结构
4. **版本友好**：源码与运行时数据分离
5. **向后兼容**：支持旧结构，平滑迁移
6. **扩展性好**：易于添加新的Agent类型和功能

这种结构特别适合多人协作的prompt工程项目，每个人可以专注于自己负责的Agent，减少文件冲突和维护成本。