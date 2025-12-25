# Agent 重组快速开始指南

## 🎯 目标

将示例 Agent 和测试 Agent 从 `agents/` 目录分离出来，使目录结构更清晰。

---

## 📋 3 步完成重组

### 步骤 1: 预览重组

```bash
python scripts/reorganize_agents.py --dry-run
```

这会显示将要移动的文件，但不会实际修改。

**预期输出**：
```
================================================================================
Agent 目录重组工具
================================================================================
模式: 预览模式（不会修改文件）
================================================================================

================================================================================
步骤 1: 移动 Agent
================================================================================

📦 将移动: agents/text_cleaner -> examples/agents/text_cleaner
📦 将移动: agents/document_summarizer -> examples/agents/document_summarizer
📦 将移动: agents/intent_classifier -> examples/agents/intent_classifier
📦 将移动: agents/entity_extractor -> examples/agents/entity_extractor
📦 将移动: agents/response_generator -> examples/agents/response_generator
📦 将移动: agents/big_thing -> tests/agents/big_thing

================================================================================
步骤 2: 移动 Pipeline
================================================================================

📄 将移动: pipelines/document_summary.yaml -> examples/pipelines/document_summary.yaml
📄 将移动: pipelines/customer_service_flow.yaml -> examples/pipelines/customer_service_flow.yaml

================================================================================
步骤 3: 创建示例说明文档
================================================================================

📝 将创建: examples/README.md
```

### 步骤 2: 执行重组

```bash
python scripts/reorganize_agents.py
```

这会实际移动文件。

**预期输出**：
```
✅ 已移动: text_cleaner -> examples/agents/text_cleaner
✅ 已移动: document_summarizer -> examples/agents/document_summarizer
✅ 已移动: intent_classifier -> examples/agents/intent_classifier
✅ 已移动: entity_extractor -> examples/agents/entity_extractor
✅ 已移动: response_generator -> examples/agents/response_generator
✅ 已移动: big_thing -> tests/agents/big_thing
✅ 已移动: document_summary.yaml -> examples/pipelines/document_summary.yaml
✅ 已移动: customer_service_flow.yaml -> examples/pipelines/customer_service_flow.yaml
✅ 已创建: examples/README.md

================================================================================
总结:
================================================================================
✅ 成功: 9
⚠️  跳过: 0
❌ 失败: 0

✅ 重组完成！

⚠️  重要提示:
   1. 需要手动更新 src/agent_registry.py 以支持多目录加载
   2. 运行测试确保一切正常: pytest tests/
   3. 更新文档中的路径引用
   4. 提交更改: git add . && git commit -m 'Reorganize agents'
```

### 步骤 3: 更新 agent_registry.py

```bash
# 预览更改
python scripts/agent_registry_patch.py --dry-run

# 执行更新
python scripts/agent_registry_patch.py
```

这会更新 `src/agent_registry.py` 以支持从多个目录加载 Agent。

**预期输出**：
```
================================================================================
更新 agent_registry.py
================================================================================
文件: src/agent_registry.py
模式: 执行模式
================================================================================

✅ 已备份原文件: src/agent_registry.py.backup
✅ 已更新: src/agent_registry.py

⚠️  重要提示:
   1. 请检查更新后的文件是否正确
   2. 运行测试: pytest tests/
   3. 如果有问题，可以从备份恢复: cp src/agent_registry.py.backup src/agent_registry.py
```

---

## ✅ 验证

### 1. 检查目录结构

```bash
# 查看 agents/ 目录（应该只有生产和系统 Agent）
ls -la agents/

# 查看 examples/agents/ 目录（应该有示例 Agent）
ls -la examples/agents/

# 查看 tests/agents/ 目录（应该有测试 Agent）
ls -la tests/agents/
```

**预期结果**：
```
agents/
├── _template/
├── judge_default/
├── mem_l1_summarizer/
├── mem0_l1_summarizer/
└── usr_profile/

examples/agents/
├── text_cleaner/
├── document_summarizer/
├── intent_classifier/
├── entity_extractor/
└── response_generator/

tests/agents/
└── big_thing/
```

### 2. 测试 Agent 加载

```bash
# 列出所有 Agent（应该能看到所有 Agent，包括示例和测试）
python scripts/list_agents_by_category.py
```

**预期输出**：
```
================================================================================
生产环境 Agent (3)
================================================================================
🚀 mem_l1_summarizer              [PROD]   一级记忆总结助手
🚀 mem0_l1_summarizer             [PROD]   一级记忆总结助手
🚀 usr_profile                    [PROD]   用户画像提取专家

================================================================================
系统 Agent (1)
================================================================================
⚙️ judge_default                  [PROD]   通用评估 Agent

================================================================================
示例 Agent (5)
================================================================================
📋 text_cleaner                   [DEMO]   文本清洗助手
📋 document_summarizer            [DEMO]   文档摘要助手
📋 intent_classifier              [DEMO]   意图识别助手
📋 entity_extractor               [DEMO]   实体提取助手
📋 response_generator             [DEMO]   回复生成助手

================================================================================
测试 Agent (1)
================================================================================
🧪 big_thing                      [TEST]   Big Thing
```

### 3. 测试示例 Pipeline

```bash
# 测试文档处理 Pipeline
python -m src eval --pipeline document_summary --variants baseline --limit 1

# 测试客服流程 Pipeline
python -m src eval --pipeline customer_service_flow --variants baseline --limit 1
```

如果能正常运行，说明重组成功！

### 4. 运行测试套件

```bash
pytest tests/ -v
```

确保所有测试通过。

---

## 🔄 回滚（如果需要）

如果重组后出现问题，可以回滚：

```bash
# 恢复 agent_registry.py
cp src/agent_registry.py.backup src/agent_registry.py

# 移回 Agent（手动）
mv examples/agents/* agents/
mv tests/agents/* agents/

# 移回 Pipeline（手动）
mv examples/pipelines/* pipelines/
```

或者使用 Git 回滚：

```bash
git checkout -- src/agent_registry.py
git clean -fd  # 删除新创建的目录
```

---

## 📊 重组前后对比

### 重组前
```
agents/
├── _template/
├── big_thing/              # 测试 Agent
├── document_summarizer/    # 示例 Agent
├── entity_extractor/       # 示例 Agent
├── intent_classifier/      # 示例 Agent
├── judge_default/          # 系统 Agent
├── mem_l1_summarizer/      # 生产 Agent
├── mem0_l1_summarizer/     # 生产 Agent
├── response_generator/     # 示例 Agent
├── text_cleaner/           # 示例 Agent
└── usr_profile/            # 生产 Agent

pipelines/
├── document_summary.yaml
└── customer_service_flow.yaml
```

### 重组后
```
agents/                     # 只有生产和系统 Agent
├── _template/
├── judge_default/
├── mem_l1_summarizer/
├── mem0_l1_summarizer/
└── usr_profile/

examples/
├── agents/                 # 示例 Agent
│   ├── text_cleaner/
│   ├── document_summarizer/
│   ├── intent_classifier/
│   ├── entity_extractor/
│   └── response_generator/
├── pipelines/              # 示例 Pipeline
│   ├── document_summary.yaml
│   └── customer_service_flow.yaml
└── README.md

tests/
└── agents/                 # 测试 Agent
    └── big_thing/
```

---

## 🎉 完成！

重组完成后，你的项目结构会更清晰：

✅ **生产 Agent** 在 `agents/` 目录  
✅ **示例 Agent** 在 `examples/agents/` 目录  
✅ **测试 Agent** 在 `tests/agents/` 目录  
✅ **示例 Pipeline** 在 `examples/pipelines/` 目录  

现在可以：
- 清楚地区分生产和示例 Agent
- 避免误操作生产 Agent
- 更好地组织和管理 Agent

---

## 📚 相关文档

- [AGENT_REORGANIZATION_PLAN.md](agent-reorganization-plan.md) - 详细的重组方案
- [AGENT_CLASSIFICATION_REPORT.md](agent-classification-report.md) - Agent 分类分析
- [AGENT_MANAGEMENT_GUIDE.md](../guides/agent-management.md) - Agent 管理指南

---

**创建时间**: 2025-12-15  
**预计时间**: 5-10 分钟
