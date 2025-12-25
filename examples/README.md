# Prompt Lab 示例

本目录包含 Prompt Lab 的示例 Agent 和 Pipeline，用于演示和学习。

详细的使用说明请参考：[示例指南](../docs/examples-guide.md)

## 📁 目录结构

```
examples/
├── agents/                      # 示例 Agent
├── pipelines/                   # 示例 Pipeline
└── scripts/                     # 示例脚本
```

## 快速开始

### 运行示例 Pipeline

```bash
# 文档处理 Pipeline
python -m src eval --pipeline document_summary --variants baseline --limit 3

# 客服流程 Pipeline
python -m src eval --pipeline customer_service_flow --variants baseline --limit 3
```

### 基于示例创建自己的 Agent

```bash
# 复制示例 Agent
cp -r examples/agents/text_cleaner agents/my_agent

# 修改配置
vim agents/my_agent/agent.yaml

# 运行评估
python -m src eval --agent my_agent
```

## 相关文档

- [示例完整指南](../docs/examples-guide.md)
- [Agent 管理指南](../docs/guides/agent-management.md)
- [Pipeline 配置指南](../docs/reference/pipeline-guide.md)
- [使用指南](../docs/USAGE_GUIDE.md)
