# Prompt Lab 项目结构

## 📁 目录结构

```
prompt-lab/
├── agents/                          # 生产和系统 Agent
│   ├── _template/                   # Agent 模板
│   ├── judge_default/               # 系统 Agent - 评估
│   ├── mem_l1_summarizer/           # 生产 Agent - 一级记忆总结
│   ├── mem0_l1_summarizer/          # 生产 Agent - 对话记忆总结
│   └── usr_profile/                 # 生产 Agent - 用户画像
│
├── data/                            # 数据目录
│   ├── agents/                      # Agent 运行数据
│   ├── baselines/                   # 基线数据
│   ├── evals/                       # 评估结果
│   ├── pipelines/                   # Pipeline 运行数据
│   ├── runs/                        # 运行记录
│   ├── testsets/                    # 测试集
│   └── archive/                     # 归档数据（历史运行结果）
│
├── docs/                            # 文档目录
│   ├── README.md                    # 文档导航
│   ├── ARCHITECTURE.md              # 系统架构
│   ├── USAGE_GUIDE.md               # 使用指南
│   ├── TROUBLESHOOTING.md           # 故障排除
│   ├── guides/                      # 使用指南
│   │   ├── agent-management.md      # Agent 管理
│   │   └── output-parser-usage.md   # Output Parser 使用
│   ├── reference/                   # 参考文档
│   │   ├── pipeline-guide.md        # Pipeline 配置
│   │   ├── eval-modes-guide.md      # 评估模式
│   │   └── ...                      # 其他参考文档
│   └── archive/                     # 归档文档（历史记录）
│
├── examples/                        # 示例和演示
│   ├── agents/                      # 示例 Agent
│   │   ├── text_cleaner/            # 文本清洗示例
│   │   ├── document_summarizer/     # 文档摘要示例
│   │   ├── intent_classifier/       # 意图识别示例
│   │   ├── entity_extractor/        # 实体提取示例
│   │   └── response_generator/      # 回复生成示例
│   ├── pipelines/                   # 示例 Pipeline
│   │   ├── document_summary.yaml    # 文档处理 Pipeline
│   │   └── customer_service_flow.yaml  # 客服流程 Pipeline
│   ├── batch_json_examples/         # 批量处理示例数据
│   └── *.py                         # 示例脚本
│
├── pipelines/                       # 生产 Pipeline 配置（当前为空）
│
├── prompts/                         # 共享 Prompt 片段（当前为空）
│
├── scripts/                         # 工具脚本
│   ├── add_agent_metadata.py        # 添加 Agent 元数据
│   ├── list_agents_by_category.py   # 列出 Agent
│   └── ...                          # 其他工具脚本
│
├── src/                             # 源代码
│   ├── agent_registry.py            # Agent 注册和加载
│   ├── agent_template_parser/       # Agent 模板解析器
│   ├── chains.py                    # Flow 执行
│   ├── cli.py                       # 命令行接口
│   ├── pipeline_config.py           # Pipeline 配置
│   ├── pipeline_runner.py           # Pipeline 运行器
│   ├── unified_evaluator.py         # 统一评估接口
│   └── ...                          # 其他源代码
│
├── templates/                       # Agent 模板（用于生成新 Agent）
│   ├── big_thing/                   # Big Thing 模板
│   ├── memory_l1/                   # 记忆 L1 模板
│   ├── usr_profile/                 # 用户画像模板
│   ├── system_prompts/              # 系统提示词模板
│   ├── user_inputs/                 # 用户输入模板
│   └── test_cases/                  # 测试用例模板
│
├── tests/                           # 测试代码
│   ├── agents/                      # 测试用 Agent
│   │   └── big_thing/               # Agent Template Parser 测试
│   ├── fixtures/                    # 测试固件
│   │   ├── agents/                  # 测试用 Agent 配置
│   │   ├── pipelines/               # 测试用 Pipeline 配置
│   │   ├── testsets/                # 测试用测试集
│   │   └── prompts/                 # 测试用 Prompt
│   └── test_*.py                    # 测试文件
│
├── .env                             # 环境变量（不提交到 Git）
├── .env.example                     # 环境变量示例
├── .gitignore                       # Git 忽略文件
├── README.md                        # 项目主文档
├── PROJECT_STRUCTURE.md             # 本文件 - 项目结构说明
└── requirements.txt                 # Python 依赖
```

---

## 📂 目录说明

### agents/
**用途**: 存放生产环境和系统 Agent

**内容**:
- `_template/`: Agent 模板，用于创建新 Agent
- `judge_default/`: 系统 Agent，用于评估其他 Agent
- `mem_l1_summarizer/`, `mem0_l1_summarizer/`, `usr_profile/`: 生产 Agent

**规则**:
- 只存放实际业务使用的 Agent
- 每个 Agent 目录包含: `agent.yaml`, `prompts/`, `testsets/`

### data/
**用途**: 存放所有运行时数据和评估结果

**子目录**:
- `agents/`: Agent 运行数据（按 agent_id 组织）
- `baselines/`: 基线数据（用于回归测试）
- `evals/`: 评估结果
- `pipelines/`: Pipeline 运行数据
- `runs/`: 运行记录
- `testsets/`: 测试集
- `archive/`: 归档数据（历史运行结果，不再使用的数据）

### docs/
**用途**: 存放所有项目文档

**组织**:
- 根目录: 核心文档（架构、使用指南、故障排除）
- `guides/`: 使用指南（Agent 管理、Output Parser 等）
- `reference/`: 参考文档（Pipeline 配置、评估模式等）
- `archive/`: 归档文档（历史记录，如重组文档）

### examples/
**用途**: 存放示例和演示代码

**内容**:
- `agents/`: 示例 Agent（用于演示 Pipeline 功能）
- `pipelines/`: 示例 Pipeline 配置
- `batch_json_examples/`: 批量处理示例数据
- `*.py`: 示例脚本

**规则**:
- 示例 Agent 不用于生产环境
- 主要用于文档和教程

### pipelines/
**用途**: 存放生产 Pipeline 配置

**状态**: 当前为空（示例 Pipeline 在 `examples/pipelines/`）

### prompts/
**用途**: 存放共享的 Prompt 片段或模板

**状态**: 当前为空（测试用 Prompt 已移到 `tests/fixtures/prompts/`）

### scripts/
**用途**: 存放工具脚本

**内容**:
- Agent 管理工具
- 数据处理工具
- 其他辅助脚本

### src/
**用途**: 存放源代码

**核心模块**:
- `agent_registry.py`: Agent 注册和加载
- `chains.py`: Flow 执行
- `cli.py`: 命令行接口
- `pipeline_config.py`: Pipeline 配置
- `pipeline_runner.py`: Pipeline 运行器
- `unified_evaluator.py`: 统一评估接口
- `agent_template_parser/`: Agent 模板解析器

### templates/
**用途**: 存放 Agent 模板（用于生成新 Agent）

**内容**:
- 各种 Agent 类型的模板
- 系统提示词、用户输入、测试用例模板

**用法**: 配合 Agent Template Parser 使用

### tests/
**用途**: 存放测试代码和测试固件

**组织**:
- `agents/`: 测试用 Agent（如 big_thing）
- `fixtures/`: 测试固件（agents, pipelines, testsets, prompts）
- `test_*.py`: 测试文件

---

## 🎯 文件组织原则

### 1. 生产 vs 示例 vs 测试
- **生产**: `agents/`, `pipelines/`
- **示例**: `examples/agents/`, `examples/pipelines/`
- **测试**: `tests/agents/`, `tests/fixtures/`

### 2. 数据组织
- 运行时数据: `data/agents/`, `data/pipelines/`
- 历史数据: `data/archive/`
- 测试数据: `tests/fixtures/`

### 3. 文档组织
- 核心文档: `docs/` 根目录
- 使用指南: `docs/guides/`
- 参考文档: `docs/reference/`
- 历史文档: `docs/archive/`

### 4. 命名规范
- 目录: 小写加下划线 `snake_case`
- 文档: 小写加连字符 `kebab-case.md`
- Python 文件: 小写加下划线 `snake_case.py`
- YAML 配置: 小写加下划线 `snake_case.yaml`

---

## 🔍 快速查找

### 我想找...
- **生产 Agent 配置** → `agents/{agent_id}/agent.yaml`
- **示例 Agent 配置** → `examples/agents/{agent_id}/agent.yaml`
- **Pipeline 配置** → `examples/pipelines/{pipeline_id}.yaml`
- **Agent 运行结果** → `data/agents/{agent_id}/runs/`
- **Pipeline 运行结果** → `data/pipelines/{pipeline_id}/runs/`
- **测试集** → `data/testsets/{agent_id}/` 或 Agent 目录下的 `testsets/`
- **文档** → `docs/README.md`
- **示例脚本** → `examples/*.py`
- **工具脚本** → `scripts/`

---

## 📝 维护建议

### 定期清理
- 定期将旧的运行结果移到 `data/archive/`
- 删除不再使用的测试数据
- 归档过时的文档到 `docs/archive/`

### 添加新内容
- **新 Agent**: 根据用途放到 `agents/` 或 `examples/agents/`
- **新 Pipeline**: 根据用途放到 `pipelines/` 或 `examples/pipelines/`
- **新文档**: 根据类型放到 `docs/` 的相应子目录
- **新脚本**: 放到 `scripts/` 或 `examples/`

### 版本控制
- 不提交 `.env` 文件
- 不提交 `data/` 目录（除了示例数据）
- 不提交 `__pycache__/` 和 `.pytest_cache/`
- 参考 `.gitignore` 文件

---

**最后更新**: 2025-12-15
