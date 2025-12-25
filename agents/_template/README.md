# Agent 模板

这是一个 Agent 模板，用于快速创建新的 Agent。

详细的使用说明请参考：[Agent 模板使用指南](../../docs/agent-template-guide.md)

## 快速开始

```bash
# 复制模板
cp -r agents/_template agents/your_new_agent_id

# 修改配置
vim agents/your_new_agent_id/agent.yaml
vim agents/your_new_agent_id/prompts/your_agent_v1.yaml

# 测试 Agent
python -m src eval --agent your_new_agent_id --limit 3
```

## 相关文档

- [Agent 模板使用指南](../../docs/agent-template-guide.md)
- [Agent 管理指南](../../docs/guides/agent-management.md)
- [使用指南](../../docs/USAGE_GUIDE.md)
