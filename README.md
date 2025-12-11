# Prompt Lab

Prompt Lab 是一个面向 AI Agent 的端到端实验平台，提供 **模板化配置生成、评估、Pipeline 工作流和回归测试** 等能力，帮助团队快速搭建和迭代智能体。

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
```bash
# 运行 Pipeline 并选择变体
python -m src eval --pipeline my_pipeline --variants baseline,experiment_v1 --judge

# 回归检测（基于基线与候选变体）
python -m src regression run --pipeline my_pipeline --baseline baseline --variant experiment_v1
```
> 如需自定义 Pipeline，需要提供对应的配置文件；当前仓库仅包含 demo 运行结果，需自行补充配置。

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
