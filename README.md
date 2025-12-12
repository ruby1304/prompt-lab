# Prompt Lab

Prompt Lab 是一个面向 AI Agent 的端到端实验平台，提供 **模板化配置生成、评估、Pipeline 工作流和回归测试** 等能力，帮助团队快速搭建和迭代智能体。

## 核心概念

基于 LangChain 构建，Prompt Lab 定义了三个核心抽象层次：

### 🤖 Agent（智能体）
**定义**：一个具有明确业务目标的任务单元，包含完整的配置、提示词版本和评估标准。

**核心特征**：
- **业务导向**：有明确的 `business_goal` 和 `expectations`（must_have/nice_to_have）
- **版本管理**：包含多个 `flows`（提示词版本），支持迭代和对比
- **自包含**：在 `agents/{agent_id}/` 目录下聚合所有相关资源（配置、提示词、测试集）
- **可评估**：配置了评估标准（规则评估 + LLM Judge）

**类型**：
- **Task Agent**：执行具体任务（如对话总结、文本清洗）
- **Judge Agent**：评估其他 Agent 的输出质量

### 🌊 Flow（提示词版本/执行流）
**定义**：Agent 的一个具体实现版本，是一个可执行的 LangChain Chain，包含 system prompt + user template + LLM 配置。

**本质**：
- **在 LangChain 层面**：`ChatPromptTemplate | ChatOpenAI` 的 LCEL Chain
- **在业务层面**：Agent 的一个提示词版本，用于迭代优化和 A/B 测试

**用途**：
- 同一个 Agent 的不同优化版本（v1, v2, v3）
- 不同的提示词策略（详细版、简化版、优化版）
- A/B 测试和性能对比

### 🔗 Pipeline（工作流）
**定义**：多个 Agent/Flow 的串联组合，形成多步骤的复杂业务流程，支持数据在步骤间传递。

**核心特征**：
- **多步骤**：由多个 `steps` 组成，每个 step 调用一个 Agent 的特定 Flow
- **数据流**：通过 `input_mapping` 定义步骤间的数据传递
- **变体管理**：支持 `baseline` 和 `variants`，用于对比不同的 Flow 组合
- **依赖管理**：自动检测循环依赖，确保步骤执行顺序合理

**关系图**：
```
Agent（业务单元）
  ├── Flow v1（提示词版本1）→ LangChain Chain
  ├── Flow v2（提示词版本2）→ LangChain Chain
  └── Flow v3（提示词版本3）→ LangChain Chain

Pipeline（工作流编排）
  ├── Step 1: Agent A + Flow v1
  ├── Step 2: Agent B + Flow v2
  └── Step 3: Agent C + Flow v1
```

**类比理解**：
- **Agent** = 一个微服务（有明确的职责和接口）
- **Flow** = 微服务的一个版本/实现（v1, v2, v3）
- **Pipeline** = 微服务编排（Service Orchestration）

## 核心能力
- **Agent Template Parser**：从系统提示词、用户输入模板和测试用例生成规范的 Agent 配置和 Prompt 文件，支持 CLI 与 Python API，并提供 LLM 自动优化能力。
- **Agent 评估**：通过命令行快速执行单个 Flow 或多版本 Flow 对比，内置规则评估与 LLM Judge 双通道评分。
- **Pipeline 运行**：串联多个 Agent/Flow 构建多步工作流，支持对 Pipeline 变体进行对比与回归检测。
- **基线与回归**：为 Agent 或 Pipeline 保存性能基线，比较候选版本并生成回归报告。
- **数据与标签管理**：按 Agent/Pipeline 组织测试集、运行结果和评估数据，支持标签过滤、批量导入与结果导出。

## 项目结构
```
prompt-lab/
├── agents/                  # 现有 Agent 配置与 Prompt 模板
├── data/                    # 评估与运行生成的数据（含 demo pipeline 运行结果）
├── docs/                    # 详细指南与参考资料
├── examples/                # 示例数据与脚本
├── prompts/                 # 共享 Prompt 片段或模板
├── src/                     # CLI、评估管线与模板解析核心代码
├── templates/               # 系统提示词、用户输入与测试用例模板
└── tests/                   # 自动化测试
```

## 快速开始
### 1. 环境准备
```bash
python --version  # Python >= 3.8
pip install -r requirements.txt
# 可选：启用 LLM 增强功能
export OPENAI_API_KEY="your-key"
```

### 2. 查看 CLI 入口
项目使用 Typer 构建命令行，入口为 `python -m src`：
```bash
python -m src --help
python -m src eval --help
```

### 3. 评估 Agent Flow
```bash
# 运行单个 Flow，并启用规则+Judge 评估
python -m src eval --agent my_agent --flows flow_v1 --judge

# 对比多个 Flow
python -m src eval --agent my_agent --flows flow_v1,flow_v2 --judge --limit 50

# 使用标签过滤测试集
python -m src eval --agent my_agent --flows flow_v1 --include-tags critical,regression
```

### 4. Pipeline 工作流

#### 4.1 运行示例 Pipeline
项目提供了两个完整的 Pipeline 示例，可以直接运行：

```bash
# 运行文档摘要 Pipeline（简单示例：清洗 → 总结）
python -m src eval --pipeline document_summary --variants baseline --limit 3

# 运行客服流程 Pipeline（复杂示例：意图识别 → 实体提取 → 回复生成）
python -m src eval --pipeline customer_service_flow --variants baseline --limit 3

# 对比不同变体
python -m src eval --pipeline document_summary --variants baseline,improved_v1 --judge

# 使用标签过滤测试集
python -m src eval --pipeline customer_service_flow --variants baseline --include-tags refund,complaint
```

**预期输出示例**：
```
🔄 Loading pipeline: document_summary
✅ Loaded 2 steps: clean → summarize
📊 Running 3 test cases with variant: baseline
  ✓ Test 1/3: Cleaned and summarized successfully
  ✓ Test 2/3: Cleaned and summarized successfully
  ✓ Test 3/3: Cleaned and summarized successfully
📈 Results saved to: data/pipelines/document_summary/runs/
```

#### 4.2 创建自定义 Pipeline

**步骤 1：创建 Pipeline 配置文件**
```bash
# 在 pipelines/ 目录下创建 YAML 配置
touch pipelines/my_pipeline.yaml
```

**步骤 2：编辑配置文件**
```yaml
# pipelines/my_pipeline.yaml
id: "my_pipeline"
name: "我的 Pipeline"
description: "Pipeline 描述"
default_testset: "my_testset.jsonl"

inputs:
  - name: "input_text"
    desc: "输入文本"
    required: true

steps:
  - id: "step1"
    agent: "text_cleaner"
    flow: "clean_v1"
    input_mapping:
      text: "input_text"
    output_key: "cleaned_text"
    
  - id: "step2"
    agent: "document_summarizer"
    flow: "summary_v1"
    input_mapping:
      text: "cleaned_text"
    output_key: "summary"

outputs:
  - key: "summary"
    label: "最终摘要"

baseline:
  name: "baseline"
  steps:
    step1:
      flow: "clean_v1"
    step2:
      flow: "summary_v1"
```

**步骤 3：创建测试集**
```bash
# 创建测试集目录
mkdir -p data/pipelines/my_pipeline/testsets

# 创建测试集文件（JSONL 格式）
cat > data/pipelines/my_pipeline/testsets/my_testset.jsonl << EOF
{"id": 1, "input_text": "这是第一个测试文档...", "expected_summary": "预期摘要", "tags": ["test"]}
{"id": 2, "input_text": "这是第二个测试文档...", "expected_summary": "预期摘要", "tags": ["test"]}
EOF
```

**步骤 4：验证并运行**
```bash
# 验证配置
python -m src eval --pipeline my_pipeline --variants baseline --limit 1

# 完整运行
python -m src eval --pipeline my_pipeline --variants baseline --judge
```

#### 4.3 Pipeline 回归测试
```bash
# 保存基线
python -m src baseline save --pipeline my_pipeline --variant baseline --name production

# 运行回归检测
python -m src regression run --pipeline my_pipeline --baseline baseline --variant experiment_v1

# 查看回归报告
python -m src regression report --pipeline my_pipeline
```

> 💡 **提示**：更多 Pipeline 配置选项和最佳实践，请参考 [Pipeline 配置指南](docs/reference/pipeline-guide.md)

### 5. 基线管理
```bash
# 保存 Agent 基线
python -m src baseline save --agent my_agent --flow stable_v1 --name production

# 查看/列出基线
python -m src baseline list --agent my_agent
python -m src baseline show --agent my_agent --name production
```

### 6. Agent Template Parser 快速用法
- **CLI 生成配置**
  ```bash
  python -m src.agent_template_parser.cli create-agent \
    --system-prompt templates/system_prompts/my_agent_system.txt \
    --user-input templates/user_inputs/my_agent_user.txt \
    --test-case templates/test_cases/my_agent_test.json \
    --agent-name my_agent
  
  python -m src.agent_template_parser.cli create-testset \
    --json-files data/*.json \
    --target-agent my_agent \
    --output-filename batch_testset.jsonl
  ```
- **Python API 示例**
  ```python
  from src.agent_template_parser import TemplateManager, TemplateParser, AgentConfigGenerator

  tm = TemplateManager()
  parser = TemplateParser()
  generator = AgentConfigGenerator()

  system_prompt = Path("templates/system_prompts/demo_system.txt").read_text()
  user_input = Path("templates/user_inputs/demo_user.txt").read_text()
  test_case = Path("templates/test_cases/demo_test.json").read_text()

  parsed = parser.create_parsed_template(
      parser.parse_system_prompt(system_prompt),
      parser.parse_user_input(user_input),
      parser.parse_test_case(test_case),
  )
  agent_cfg = generator.generate_agent_yaml(parsed, "demo_agent")
  prompt_cfg = generator.generate_prompt_yaml(parsed, "demo_agent", system_prompt, user_input)
  generator.save_config_files(agent_cfg, prompt_cfg, "demo_agent")
  ```

### 7. 数据与测试集
- 测试集使用 JSONL 格式，支持自定义 `tags`，文件通常放在 `agents/<agent_id>/testsets/`。
- 运行与评估结果分别存储在 `data/agents/<agent_id>/runs|evals` 下；Pipeline 运行结果位于 `data/pipelines/<pipeline_id>/runs/`。
- 可用 `python -m src export` 系列命令导出 CSV/JSON 报告。

## 典型场景
- **新 Flow 开发**：编辑 `agents/<agent>/prompts/*.yaml` → `python -m src eval --agent <agent> --flows new_flow --judge` → 与现有 Flow 对比 → 覆盖基线。
- **Pipeline 迭代**：准备 Pipeline 配置 → `python -m src eval --pipeline <id> --variants baseline,candidate --judge` → 回归检测 → 更新基线。
- **批量测试集生成**：整理 JSON 数据 → `create-testset` 生成标准化测试集 → 标签化后用于评估或回归。

## 故障排除速查
- **模块导入/依赖问题**：确保在项目根目录执行并安装依赖，可必要时设置 `PYTHONPATH=$(pwd)`。
- **模板解析失败**：检查文件编码为 UTF-8、JSON 语法合法，并确认变量格式符合模板约定（如 `${sys.user_input}`）。
- **批量处理/文件路径错误**：确认目标 Agent 目录存在且具备写权限；使用绝对路径或从项目根目录运行命令。
- **LLM 增强异常**：检查网络、API Key，或添加 `--no-llm-enhancement` 禁用增强。

## 开发与测试
```bash
# 运行核心测试（示例）
python -m pytest tests/test_cli.py -k create_agent_from_templates_success -v

# 代码格式与质量（可选）
black src/ tests/
flake8 src/ tests/
mypy src/
```

欢迎在 `issues` 中反馈问题或提交 PR 改进平台体验。

## 系统架构

### 核心组件

Prompt Lab 基于 LangChain 构建，采用分层架构设计：

```
┌─────────────────────────────────────────────────────────────┐
│                     配置层 (Configuration)                   │
│  Agent Config ──→ Flow Config ──→ Pipeline Config           │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     执行层 (Execution)                       │
│  ┌──────────────────────────────────────────────────┐      │
│  │  Flow Executor (chains.py)                       │      │
│  │  ChatPromptTemplate → ChatOpenAI → OutputParser  │      │
│  └──────────────────────────────────────────────────┘      │
│  ┌──────────────────────────────────────────────────┐      │
│  │  Pipeline Runner (pipeline_runner.py)            │      │
│  │  步骤编排 → 数据传递 → 错误处理                   │      │
│  └──────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                     评估层 (Evaluation)                      │
│  统一评估接口 → 规则引擎 + Judge Agent                       │
└─────────────────────────────────────────────────────────────┘
```

**核心组件说明**：

1. **Agent**：业务任务单元，包含配置、提示词版本和评估标准
2. **Flow**：可执行的 LangChain Chain，是 Agent 的具体实现版本
3. **Pipeline**：多步骤工作流，串联多个 Agent/Flow
4. **Output Parser**：结构化输出解析器，确保 LLM 输出格式可靠
5. **Unified Evaluator**：统一评估接口，支持规则评估和 Judge 评估

### 数据流

```
测试集 (JSONL) → Pipeline/Agent → LLM 调用 → Output Parser → 评估 → 结果报告
```

### 与 LangChain 生态的关系

Prompt Lab 充分利用 LangChain 的核心能力：

| LangChain 概念 | Prompt Lab 实现 | 状态 |
|---------------|----------------|------|
| **Chain** | Flow | ✅ 已实现 |
| **SequentialChain** | Pipeline | ✅ 已实现 |
| **Prompt Template** | Flow YAML | ✅ 已实现 |
| **Output Parser** | Output Parser 配置 | ✅ 已实现 |
| **LLM** | ChatOpenAI | ✅ 已实现 |
| **Memory** | - | 📋 计划中 |
| **Tools** | - | 📋 计划中 |
| **Retriever** | - | 📋 计划中 |
| **Router** | - | 📋 计划中 |
| **Autonomous Agents** | - | 📋 计划中 |

详细的架构分析和缺失维度评估，请参考 [架构分析文档](docs/ARCHITECTURE_ANALYSIS.md)。

## 开发路线图

### ✅ 已完成功能

**核心功能**：
- ✅ Agent 配置管理和版本控制
- ✅ Flow 执行和对比
- ✅ Pipeline 多步骤工作流
- ✅ 规则评估和 LLM Judge 评估
- ✅ 基线管理和回归测试
- ✅ Agent Template Parser（模板解析和配置生成）

**最新增强**（v1.1）：
- ✅ **Output Parser**：支持 JSON、Pydantic、List 等结构化输出解析
- ✅ **统一评估接口**：Agent 和 Pipeline 使用相同的评估机制
- ✅ **Pipeline 示例**：提供完整的文档处理和客服流程示例
- ✅ **性能监控**：执行时间、Token 使用量、解析成功率统计
- ✅ **错误处理增强**：Output Parser 自动重试和降级处理
- ✅ **配置验证**：循环依赖检测、引用完整性检查

### 🔄 进行中功能

- 🔄 **文档完善**：系统架构文档、Output Parser 使用指南
- 🔄 **测试覆盖**：集成测试、向后兼容性测试

### 📋 短期规划（1-2 个月）

1. **Memory 系统**：支持多轮对话和 Pipeline 状态管理
   - ConversationBufferMemory
   - ConversationSummaryMemory
   - Pipeline 步骤间记忆传递

2. **Streaming 输出**：支持流式输出和实时反馈
   - 流式 LLM 调用
   - 实时进度显示
   - 中间结果预览

3. **并行执行**：Pipeline 步骤的并行执行优化
   - 独立步骤并行化
   - 依赖分析和调度
   - 性能提升

### 📋 中期规划（3-6 个月）

4. **Tools 集成**：支持函数调用和外部系统集成
   - Function Calling
   - API 集成
   - 数据库查询
   - 文件操作

5. **Retriever**：支持 RAG（检索增强生成）
   - 向量数据库集成
   - 文档检索
   - 上下文压缩
   - 混合检索

6. **Router**：支持条件分支和动态路由
   - LLM Router
   - 条件分支
   - 动态步骤选择

### 📋 长期规划（6-12 个月）

7. **Autonomous Agents**：实现真正的自主决策 Agent
   - ReAct 模式
   - Plan-and-Execute
   - 自主工具选择

8. **可视化编辑器**：Pipeline 的图形化配置界面
   - 拖拽式 Pipeline 构建
   - 实时预览
   - 可视化调试

9. **分布式执行**：支持分布式 Pipeline 执行
   - 任务队列
   - 分布式调度
   - 结果聚合

详细的功能规划和优先级分析，请参考 [架构分析文档](docs/ARCHITECTURE_ANALYSIS.md)。

## 文档导航

### 📚 核心文档
- [使用指南](docs/USAGE_GUIDE.md) - 详细的功能使用说明
- [系统架构](docs/ARCHITECTURE.md) - 完整的系统架构说明和组件详解
- [架构分析](docs/ARCHITECTURE_ANALYSIS.md) - 与 LangChain 生态对比和演进规划
- [故障排除](docs/TROUBLESHOOTING.md) - 常见问题和解决方案

### 📖 参考文档
- [Pipeline 配置指南](docs/reference/pipeline-guide.md) - Pipeline 配置语法和最佳实践
- [Output Parser 快速指南](OUTPUT_PARSER_USAGE.md) - Output Parser 快速开始
- [Output Parser 详细指南](docs/reference/output-parser-guide.md) - Output Parser 完整使用文档
- [评估模式指南](docs/reference/eval-modes-guide.md) - 评估系统详解
- [回归测试指南](docs/reference/regression-testing.md) - 基线管理和回归测试
- [数据结构指南](docs/reference/data-structure-guide.md) - 数据格式和组织
- [评估规则参考](docs/reference/evaluation-rules.md) - 规则评估配置
- [手动评估指南](docs/reference/manual-eval-guide.md) - 手动评估流程
- [项目结构说明](docs/reference/project-structure.md) - 目录结构详解
- [迁移指南](docs/reference/migration-guide.md) - 版本升级指南

### 🔧 开发文档
- [Agent Template Parser](src/agent_template_parser/README.md) - 模板解析器使用
- [Big Thing Agent 指南](docs/big_thing_agent_guide.md) - Big Thing Agent 使用示例
