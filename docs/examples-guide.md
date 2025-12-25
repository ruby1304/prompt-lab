# Prompt Lab 示例指南

本指南介绍 `examples/` 目录中的示例 Agent 和 Pipeline，用于演示和学习。

## 📁 目录结构

```
examples/
├── agents/                      # 示例 Agent
│   ├── text_cleaner/           # 文本清洗示例
│   ├── document_summarizer/    # 文档摘要示例
│   ├── intent_classifier/      # 意图识别示例
│   ├── entity_extractor/       # 实体提取示例
│   └── response_generator/     # 回复生成示例
│
├── pipelines/                   # 示例 Pipeline
│   ├── document_summary.yaml   # 文档处理 Pipeline
│   └── customer_service_flow.yaml  # 客服流程 Pipeline
│
└── scripts/                     # 示例脚本
```

## 🎯 示例说明

### 1. 文档处理 Pipeline

**Pipeline**: `examples/pipelines/document_summary.yaml`

**流程**:
```
原始文档 → text_cleaner (清洗) → document_summarizer (摘要) → 最终摘要
```

**运行方法**:
```bash
python -m src eval --pipeline document_summary --variants baseline --limit 3
```

### 2. 客服流程 Pipeline

**Pipeline**: `examples/pipelines/customer_service_flow.yaml`

**流程**:
```
用户消息 → intent_classifier (意图识别) 
         → entity_extractor (实体提取)
         → response_generator (生成回复)
         → 客服回复
```

**运行方法**:
```bash
python -m src eval --pipeline customer_service_flow --variants baseline --limit 3
```

## 📚 学习资源

### Agent 开发
- 查看示例 Agent 的配置文件 (`agent.yaml`)
- 查看提示词配置 (`prompts/*.yaml`)
- 查看测试集格式 (`testsets/*.jsonl`)

### Pipeline 开发
- 查看 Pipeline 配置语法
- 学习步骤编排和数据流
- 了解变体管理

## 🔧 自定义示例

你可以基于这些示例创建自己的 Agent 和 Pipeline：

```bash
# 复制示例 Agent
cp -r examples/agents/text_cleaner agents/my_agent

# 修改配置
vim agents/my_agent/agent.yaml
vim agents/my_agent/prompts/my_flow.yaml

# 运行评估
python -m src eval --agent my_agent --flows my_flow
```

## ⚠️ 注意事项

1. **这些是示例，不是生产 Agent**
   - 示例 Agent 的配置可能不完整
   - 测试集数据是模拟的
   - 不要用于生产环境

2. **修改示例不会影响生产**
   - 示例 Agent 与生产 Agent 完全分离
   - 可以自由修改和实验

3. **保持示例简单**
   - 示例应该易于理解
   - 专注于演示核心功能
   - 避免过度复杂化

## 📖 相关文档

- [Agent 管理指南](guides/agent-management.md)
- [Pipeline 配置指南](reference/pipeline-guide.md)
- [使用指南](USAGE_GUIDE.md)

---

**最后更新**: 2025-12-15
