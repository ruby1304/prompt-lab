# Prompt Lab - AI Agent Development Platform

一个强大的 AI Agent 开发、评估、测试和回归分析平台。支持从模板快速生成 Agent 配置、单 Agent 评估、多步骤 Pipeline 执行、基线管理和自动化回归测试。

## 🚀 核心功能

### 🎯 Agent Template Parser (NEW!)
- **模板到配置转换**: 从文本模板自动生成符合规范的 Agent 配置
- **智能变量映射**: 自动识别和映射模板变量到配置字段
- **批量测试集生成**: 批量处理 JSON 数据生成标准测试集
- **LLM 增强优化**: 使用 LLM 自动优化和修正配置文件
- **错误处理恢复**: 智能错误检测和多级回退机制

### Agent 评估
- **单 Agent 测试**: 快速评估单个 Agent 的性能
- **多 Flow 比较**: 同时测试多个 Flow 版本
- **规则和 LLM 评估**: 结合规则引擎和 LLM Judge 的双重评估

### Pipeline 工作流
- **多步骤执行**: 将多个 Agent/Flow 串联成复杂工作流
- **数据流管理**: 自动处理步骤间的数据传递
- **变体管理**: 支持多个 Pipeline 配置变体的 A/B 测试

### 回归测试
- **基线管理**: 保存和管理稳定版本的性能基线
- **自动回归检测**: 识别性能下降和功能回退
- **详细分析报告**: 提供具体的回归案例和改进建议

### 数据组织
- **结构化存储**: 按 Agent/Pipeline 组织测试数据
- **标签过滤**: 使用标签进行精细化测试控制
- **历史追踪**: 完整的执行历史和性能趋势

## 📦 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 基本使用

#### 0. Agent Template Parser (快速创建 Agent)

```bash
# 从模板文件创建 Agent
python -m src.agent_template_parser.cli create-agent \
  --system-prompt templates/system_prompts/my_agent_system.txt \
  --user-input templates/user_inputs/my_agent_user.txt \
  --test-case templates/test_cases/my_agent_test.json \
  --agent-name my_agent

# 批量创建测试集
python -m src.agent_template_parser.cli create-testset \
  --json-files data1.json data2.json data3.json \
  --target-agent existing_agent \
  --output-filename batch_testset.jsonl

# 查看可用模板
python -m src.agent_template_parser.cli list-templates

# 验证模板文件
python -m src.agent_template_parser.cli validate-templates --agent-name my_agent
```

#### 1. Agent 评估

```bash
# 评估单个 Agent 的 Flow
python -m src eval --agent my_agent --flows flow_v1 --judge

# 比较多个 Flow
python -m src eval --agent my_agent --flows flow_v1,flow_v2 --judge --limit 50

# 使用标签过滤测试集
python -m src eval --agent my_agent --flows flow_v1 --include-tags critical,regression
```

#### 2. Pipeline 执行

```bash
# 执行 Pipeline 基线版本
python -m src eval --pipeline my_pipeline --variants baseline --judge

# 比较多个 Pipeline 变体
python -m src eval --pipeline my_pipeline --variants baseline,experimental_v1 --judge

# 使用特定测试集
python -m src eval --pipeline my_pipeline --variants baseline --testset custom_test.jsonl
```

#### 3. 基线管理

```bash
# 保存 Agent 基线
python -m src baseline save --agent my_agent --flow stable_v1 --name production_baseline

# 保存 Pipeline 基线
python -m src baseline save --pipeline my_pipeline --variant baseline --name prod_v1

# 列出所有基线
python -m src baseline list --agent my_agent

# 查看基线详情
python -m src baseline show --agent my_agent --name production_baseline
```

#### 4. 回归测试

```bash
# Agent 回归测试
python -m src eval_regression --agent my_agent --baseline production_baseline --variant new_flow_v2

# Pipeline 回归测试
python -m src eval_regression --pipeline my_pipeline --baseline prod_v1 --variant experimental_v1
```

## 🏗️ 项目结构

```
prompt-lab/
├── agents/                    # Agent 配置目录
│   └── {agent_id}/
│       ├── agent.yaml        # Agent 配置文件
│       ├── prompts/          # Prompt 文件
│       └── testsets/         # 测试集文件
├── pipelines/                # Pipeline 配置目录
│   └── {pipeline_id}.yaml   # Pipeline 配置文件
├── templates/                # 模板文件目录 (NEW!)
│   ├── system_prompts/      # 系统提示词模板
│   ├── user_inputs/         # 用户输入模板
│   └── test_cases/          # 测试用例文件
├── examples/                 # 示例文件
│   └── batch_json_examples/ # 批量处理示例
├── data/                     # 数据存储目录
│   ├── agents/              # Agent 数据
│   │   └── {agent_id}/
│   │       ├── testsets/    # 测试集
│   │       ├── runs/        # 执行结果
│   │       └── evals/       # 评估结果
│   ├── pipelines/           # Pipeline 数据
│   │   └── {pipeline_id}/
│   │       ├── testsets/
│   │       ├── runs/
│   │       └── evals/
│   └── baselines/           # 基线快照
│       ├── agents/
│       └── pipelines/
├── src/                     # 源代码
│   └── agent_template_parser/ # Agent 模板解析器 (NEW!)
├── docs/                    # 文档
│   └── reference/          # 参考文档
└── tests/                   # 测试代码
```

## 📋 配置示例

### Agent 配置 (agents/my_agent/agent.yaml)

```yaml
id: my_agent
name: 客服助手
description: 智能客服对话助手
business_goal: 准确理解用户意图并提供有用回复

flows:
  - name: customer_service_v1
    file: customer_service_v1.yaml
    notes: 基础客服流程
  - name: customer_service_v2
    file: customer_service_v2.yaml
    notes: 改进版客服流程

default_testset: customer_queries.jsonl
baseline_flow: customer_service_v1

evaluation:
  rules:
    - name: response_length
      description: 回复长度适中
    - name: politeness_check
      description: 回复礼貌友好
  judge:
    enabled: true
    model: gpt-4
    criteria:
      - 准确性：回复是否准确回答了用户问题
      - 有用性：回复是否对用户有帮助
      - 专业性：回复是否体现了专业水准
```

### Pipeline 配置 (pipelines/document_processing.yaml)

```yaml
id: document_processing
name: 文档处理 Pipeline
description: 清理文档内容并生成摘要

inputs:
  - name: raw_text
    desc: 原始文档文本
    required: true

steps:
  - id: clean
    agent: text_cleaner
    flow: clean_v1
    input_mapping:
      text: raw_text
    output_key: cleaned_text
    
  - id: summarize
    agent: summarizer
    flow: summary_v1
    input_mapping:
      text: cleaned_text
    output_key: summary

outputs:
  - key: summary
    label: 文档摘要

baseline:
  name: stable_v1
  description: 稳定版本基线
  steps:
    clean:
      flow: clean_v1
    summarize:
      flow: summary_v1

variants:
  improved_v1:
    description: 改进版本
    overrides:
      summarize:
        flow: summary_v2
        model: gpt-4
```

### 测试集格式 (testsets/example.jsonl)

```json
{"id": "test_1", "tags": ["basic", "customer_service"], "scenario": "greeting", "user_message": "你好，我需要帮助", "expected_intent": "greeting"}
{"id": "test_2", "tags": ["complex", "technical"], "scenario": "troubleshooting", "user_message": "我的账户登录不了", "expected_intent": "technical_support"}
{"id": "test_3", "tags": ["edge_case", "complaint"], "scenario": "complaint", "user_message": "你们的服务太差了", "expected_intent": "complaint"}
```

## 🔧 高级功能

### 标签过滤

使用标签进行精细化测试控制：

```bash
# 只测试关键功能
python -m src eval --agent my_agent --flows flow_v1 --include-tags critical

# 排除边界情况
python -m src eval --agent my_agent --flows flow_v1 --exclude-tags edge_case

# 组合过滤
python -m src eval --agent my_agent --flows flow_v1 --include-tags regression,important --exclude-tags slow
```

### 批量操作

```bash
# 批量比较多个 Flow
python -m src run_compare --agent my_agent --flows flow_v1,flow_v2,flow_v3

# 批量执行多个 Agent
python -m src run_batch --agents agent1,agent2 --flows latest
```

### 自定义评估

```bash
# 只使用规则评估
python -m src eval --agent my_agent --flows flow_v1 --rules-only

# 只使用 LLM 评估
python -m src eval --agent my_agent --flows flow_v1 --judge-only

# 自定义 Judge 模型
python -m src eval --agent my_agent --flows flow_v1 --judge --judge-model gpt-4-turbo
```

## 📊 结果分析

### 评估报告

系统生成详细的评估报告，包括：

- **整体指标**: 平均分、通过率、执行时间
- **规则分析**: 各项规则的通过情况
- **LLM 评估**: 详细的评分和反馈
- **标签分析**: 按标签分组的性能统计
- **案例详情**: 具体的成功和失败案例

### 回归分析

回归测试提供：

- **性能对比**: 新版本 vs 基线的详细对比
- **回归检测**: 自动识别性能下降的案例
- **严重程度分类**: Critical/Major/Minor 回归分类
- **改进建议**: 基于分析结果的具体建议

### 数据导出

```bash
# 导出评估结果为 CSV
python -m src export --agent my_agent --format csv --output results.csv

# 导出回归分析报告
python -m src export_regression --pipeline my_pipeline --baseline prod_v1 --variant test_v1 --format json
```

## 🛠️ 开发和测试

### 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行单元测试
python -m pytest tests/test_*.py -v

# 运行集成测试
python -m pytest tests/test_integration.py -v

# 生成覆盖率报告
python -m pytest tests/ --cov=src --cov-report=html
```

### 代码质量

```bash
# 代码格式化
black src/ tests/

# 代码检查
flake8 src/ tests/

# 类型检查
mypy src/
```

## 📚 详细文档

### 参考文档

#### Agent Template Parser 文档 (NEW!)
- **[Agent Template Parser README](src/agent_template_parser/README.md)** - 完整的功能介绍和 API 文档
- **[使用指南](docs/USAGE_GUIDE.md)** - 详细的使用教程和实际案例
- **[故障排除指南](docs/TROUBLESHOOTING.md)** - 常见问题和解决方案

#### 系统文档
- **[Pipeline 配置指南](docs/reference/pipeline-guide.md)** - 详细的 Pipeline 配置语法和示例
- **[回归测试指南](docs/reference/regression-testing.md)** - 回归测试工作流程和最佳实践
- **[数据结构指南](docs/reference/data-structure-guide.md)** - 数据文件格式和组织结构
- **[评估模式指南](docs/reference/eval-modes-guide.md)** - 不同评估模式的使用方法
- **[评估规则指南](docs/reference/evaluation-rules.md)** - 规则引擎的配置和使用
- **[手动评估指南](docs/reference/manual-eval-guide.md)** - 手动评估流程和工具
- **[规则快速参考](docs/reference/rules-quick-reference.md)** - 常用规则的快速参考
- **[项目结构说明](docs/reference/project-structure.md)** - 详细的项目结构说明
- **[迁移指南](docs/reference/migration-guide.md)** - 从旧版本迁移的指南

### 使用场景

#### 1. 新功能开发

```bash
# 1. 开发新的 Flow
# 编辑 agents/my_agent/prompts/new_flow.yaml

# 2. 测试新 Flow
python -m src eval --agent my_agent --flows new_flow --judge --limit 20

# 3. 与现有版本比较
python -m src eval --agent my_agent --flows current_flow,new_flow --judge

# 4. 创建新基线（如果性能更好）
python -m src baseline save --agent my_agent --flow new_flow --name improved_baseline
```

#### 2. 质量保证

```bash
# 1. 运行回归测试
python -m src eval_regression --agent my_agent --baseline production_baseline --variant candidate_flow

# 2. 检查关键功能
python -m src eval --agent my_agent --flows candidate_flow --include-tags critical,regression --judge

# 3. 生成质量报告
python -m src generate_qa_report --agent my_agent --baseline production_baseline --variant candidate_flow
```

#### 3. 性能监控

```bash
# 1. 定期性能检查
python -m src eval --agent my_agent --flows production_flow --judge --include-tags monitoring

# 2. 趋势分析
python -m src analyze_trends --agent my_agent --days 30

# 3. 性能告警
python -m src check_performance_alerts --agent my_agent --threshold 0.1
```

#### 4. A/B 测试

```bash
# 1. 设置 Pipeline 变体
# 编辑 pipelines/my_pipeline.yaml，添加新变体

# 2. 并行测试多个变体
python -m src eval --pipeline my_pipeline --variants baseline,variant_a,variant_b --judge

# 3. 分析变体性能
python -m src analyze_variants --pipeline my_pipeline --variants baseline,variant_a,variant_b
```

## 🤝 贡献指南

### 开发环境设置

```bash
# 克隆仓库
git clone <repository-url>
cd prompt-lab

# 安装开发依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 运行测试确保环境正常
python -m pytest tests/ -v
```

### 提交代码

1. 创建功能分支
2. 编写测试用例
3. 确保所有测试通过
4. 提交 Pull Request

### 代码规范

- 使用 Black 进行代码格式化
- 遵循 PEP 8 编码规范
- 为新功能编写测试
- 更新相关文档

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🆘 支持和反馈

如果您遇到问题或有改进建议，请：

1. 查看 [文档](docs/reference/) 寻找解决方案
2. 搜索现有的 Issues
3. 创建新的 Issue 描述问题
4. 联系开发团队

---

**Prompt Lab** - 让 AI Agent 开发更简单、更可靠、更高效！