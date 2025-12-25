# Prompt Lab 快速参考

## 🚀 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，添加 OPENAI_API_KEY

# 3. 运行示例 Pipeline
python -m src eval --pipeline document_summary --variants baseline --limit 3

# 4. 评估 Agent
python -m src eval --agent mem_l1_summarizer --flows flow_v1 --judge
```

---

## 📁 项目结构速查

```
prompt-lab/
├── agents/          # 生产 Agent
├── examples/        # 示例 Agent 和 Pipeline
├── tests/           # 测试代码和固件
├── data/            # 运行数据
├── docs/            # 文档
├── src/             # 源代码
└── scripts/         # 工具脚本
```

详细说明: [docs/reference/project-structure.md](docs/reference/project-structure.md)

---

## 📚 文档速查

| 文档 | 用途 |
|------|------|
| [README.md](README.md) | 项目主文档 |
| [docs/README.md](docs/README.md) | 文档导航索引 |
| [docs/reference/project-structure.md](docs/reference/project-structure.md) | 项目结构说明 |
| [docs/USAGE_GUIDE.md](docs/USAGE_GUIDE.md) | 详细使用指南 |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | 系统架构 |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | 故障排除 |

---

## 🔧 常用命令

### Agent 评估
```bash
# 评估单个 Flow
python -m src eval --agent <agent_id> --flows <flow_name> --judge

# 对比多个 Flow
python -m src eval --agent <agent_id> --flows flow1,flow2 --judge

# 使用标签过滤
python -m src eval --agent <agent_id> --flows <flow_name> --include-tags tag1,tag2
```

### Pipeline 运行
```bash
# 运行 Pipeline
python -m src eval --pipeline <pipeline_id> --variants baseline --limit 10

# 对比变体
python -m src eval --pipeline <pipeline_id> --variants baseline,variant1 --judge
```

### 基线管理
```bash
# 保存基线
python -m src baseline save --agent <agent_id> --flow <flow_name> --name production

# 查看基线
python -m src baseline list --agent <agent_id>
python -m src baseline show --agent <agent_id> --name production
```

### Agent 管理
```bash
# 列出所有 Agent
python scripts/list_agents_by_category.py

# 列出生产 Agent
python scripts/list_agents_by_category.py --category production

# 显示详细信息
python scripts/list_agents_by_category.py --show-details
```

---

## 📖 核心概念

### Agent
业务任务单元，包含配置、提示词版本和评估标准
- 位置: `agents/{agent_id}/`
- 配置: `agent.yaml`
- 提示词: `prompts/{flow_name}.yaml`
- 测试集: `testsets/{testset_name}.jsonl`

### Flow
Agent 的一个具体实现版本，是可执行的 LangChain Chain
- 本质: `ChatPromptTemplate | ChatOpenAI`
- 用途: 版本迭代、A/B 测试

### Pipeline
多个 Agent/Flow 的串联组合，形成多步骤工作流
- 位置: `pipelines/{pipeline_id}.yaml` 或 `examples/pipelines/`
- 配置: 定义 steps、input_mapping、variants

---

## 🎯 常见任务

### 创建新 Agent
```bash
# 使用 Agent Template Parser
python -m src.agent_template_parser.cli create-agent \
  --system-prompt templates/system_prompts/my_agent_system.txt \
  --user-input templates/user_inputs/my_agent_user.txt \
  --test-case templates/test_cases/my_agent_test.json \
  --agent-name my_agent
```

### 创建新 Pipeline
1. 创建配置文件: `pipelines/my_pipeline.yaml`
2. 定义 steps 和 input_mapping
3. 创建测试集: `data/pipelines/my_pipeline/testsets/`
4. 运行测试: `python -m src eval --pipeline my_pipeline --variants baseline`

详细说明: [docs/reference/pipeline-guide.md](docs/reference/pipeline-guide.md)

### 配置 Output Parser
在 Flow 配置中添加:
```yaml
output_parser:
  type: "json"              # json, list, pydantic
  retry_on_error: true
  max_retries: 3
```

详细说明: [docs/guides/output-parser-usage.md](docs/guides/output-parser-usage.md)

---

## 🔍 查找内容

### 我想找...
- **生产 Agent** → `agents/{agent_id}/`
- **示例 Agent** → `examples/agents/{agent_id}/`
- **Pipeline 配置** → `examples/pipelines/{pipeline_id}.yaml`
- **运行结果** → `data/agents/{agent_id}/runs/` 或 `data/pipelines/{pipeline_id}/runs/`
- **测试集** → `data/testsets/` 或 Agent/Pipeline 目录下的 `testsets/`
- **文档** → `docs/README.md`
- **示例脚本** → `examples/*.py`

---

## 🐛 故障排除

### 常见问题
1. **模块导入错误** → 确保在项目根目录运行，设置 `PYTHONPATH=$(pwd)`
2. **Agent 找不到** → 检查 Agent ID 是否正确，查看 `agents/` 或 `examples/agents/`
3. **Pipeline 执行失败** → 检查 Agent 引用、input_mapping 配置
4. **LLM 调用失败** → 检查 API Key、网络连接

详细说明: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

---

## 📊 项目状态

### 生产 Agent
- `mem_l1_summarizer` - 一级记忆总结
- `mem0_l1_summarizer` - 对话记忆总结
- `usr_profile` - 用户画像提取
- `judge_default` - 评估 Agent（系统）

### 示例 Agent
- `text_cleaner` - 文本清洗
- `document_summarizer` - 文档摘要
- `intent_classifier` - 意图识别
- `entity_extractor` - 实体提取
- `response_generator` - 回复生成

### 示例 Pipeline
- `document_summary` - 文档处理流程
- `customer_service_flow` - 客服流程

---

## 🔗 相关链接

- [完整文档](docs/README.md)
- [项目结构](docs/reference/project-structure.md)
- [整理总结](REORGANIZATION_SUMMARY.md)
- [GitHub Issues](https://github.com/your-repo/issues)

---

**最后更新**: 2025-12-15
