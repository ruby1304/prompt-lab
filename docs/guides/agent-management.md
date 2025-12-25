# Agent 管理指南

## 📚 概述

本指南介绍如何管理和分类 Prompt Lab 中的 Agent，包括如何区分生产 Agent、示例 Agent 和测试 Agent。

---

## 🏷️ Agent 分类系统

### 分类维度

每个 Agent 有两个主要分类维度：

#### 1. Category（类别）
- **production**: 生产环境 Agent，实际业务使用
- **example**: 示例 Agent，用于演示和学习
- **test**: 测试 Agent，用于测试框架功能
- **system**: 系统 Agent，如 Judge Agent

#### 2. Environment（环境）
- **production**: 生产环境
- **staging**: 预发布环境
- **demo**: 演示环境
- **test**: 测试环境

### 元数据字段

在 `agent.yaml` 中添加以下字段：

```yaml
id: "my_agent"
name: "我的 Agent"
type: "task"

# 分类元数据（新增）
category: "production"        # 必需：类别
environment: "production"     # 必需：环境
owner: "team_name"           # 可选：负责团队
version: "1.0.0"             # 可选：版本号
tags: ["tag1", "tag2"]       # 可选：标签
deprecated: false            # 可选：是否废弃

# 特殊说明（可选）
notes: "特殊说明"
example_usage: "用于 XX Pipeline 演示"
test_purpose: "测试 XX 功能"

# 原有字段保持不变
description: |
  Agent 描述...
business_goal: |
  业务目标...
# ...
```

---

## 🛠️ 使用工具

### 1. 添加元数据到所有 Agent

#### 预览更改（推荐先执行）
```bash
python scripts/add_agent_metadata.py --dry-run
```

这会显示将要进行的更改，但不会实际修改文件。

#### 执行更新
```bash
python scripts/add_agent_metadata.py
```

这会实际修改所有 Agent 的配置文件。

#### 只更新特定 Agent
```bash
python scripts/add_agent_metadata.py --agent mem_l1_summarizer
```

### 2. 列出 Agent

#### 列出所有 Agent
```bash
python scripts/list_agents_by_category.py
```

输出示例：
```
================================================================================
生产环境 Agent (3)
================================================================================
🚀 mem_l1_summarizer              [PROD]   一级记忆总结助手
🚀 mem0_l1_summarizer             [PROD]   一级记忆总结助手
🚀 usr_profile                    [PROD]   用户画像提取专家

================================================================================
示例 Agent (5)
================================================================================
📋 text_cleaner                   [DEMO]   文本清洗助手
📋 document_summarizer            [DEMO]   文档摘要助手
📋 intent_classifier              [DEMO]   意图识别助手
📋 entity_extractor               [DEMO]   实体提取助手
📋 response_generator             [DEMO]   回复生成助手
```

#### 只列出生产 Agent
```bash
python scripts/list_agents_by_category.py --category production
```

#### 只列出示例 Agent
```bash
python scripts/list_agents_by_category.py --category example
```

#### 显示详细信息
```bash
python scripts/list_agents_by_category.py --show-details
```

输出示例：
```
🚀 mem_l1_summarizer              [PROD]   一级记忆总结助手
    v1.0.0 | Owner: memory_team | Tags: memory, conversation, summarization | Flows: 1
    📝 【生产环境】负责处理「一级记忆」层的对话总结
```

#### 按环境过滤
```bash
python scripts/list_agents_by_category.py --environment production
python scripts/list_agents_by_category.py --environment demo
```

---

## 📋 当前 Agent 清单

### 生产 Agent（3个）

#### mem_l1_summarizer
- **用途**: 一级记忆总结助手
- **业务目标**: 处理对话总结，生成4-10句的客观第三人称总结
- **状态**: ✅ 生产环境

#### mem0_l1_summarizer
- **用途**: 一级记忆总结助手（另一版本）
- **业务目标**: 与 mem_l1_summarizer 类似
- **状态**: ⚠️ 需要确认是否与 mem_l1_summarizer 重复

#### usr_profile
- **用途**: 用户画像提取专家
- **业务目标**: 从对话历史中提取十维度用户画像
- **状态**: ✅ 生产环境

### 示例 Agent（5个）

这些 Agent 用于演示 Pipeline 功能，不是实际业务使用。

#### 文档处理 Pipeline 示例
- **text_cleaner**: 文本清洗助手
- **document_summarizer**: 文档摘要助手
- **Pipeline**: `pipelines/document_summary.yaml`

#### 客服流程 Pipeline 示例
- **intent_classifier**: 意图识别助手
- **entity_extractor**: 实体提取助手
- **response_generator**: 回复生成助手
- **Pipeline**: `pipelines/customer_service_flow.yaml`

### 测试 Agent（1个）

#### big_thing
- **用途**: 测试 Agent Template Parser 功能
- **状态**: 🧪 测试用途

### 系统 Agent（1个）

#### judge_default
- **用途**: 通用评估 Agent
- **类型**: Judge Agent
- **状态**: ⚙️ 系统核心组件

---

## 🎯 最佳实践

### 1. 创建新 Agent 时

```yaml
# 生产 Agent 模板
id: "new_production_agent"
name: "新生产 Agent"
type: "task"
category: "production"
environment: "production"
owner: "your_team"
version: "1.0.0"
tags: ["your", "tags"]
deprecated: false
description: |
  【生产环境】Agent 描述...
business_goal: |
  业务目标...
```

```yaml
# 示例 Agent 模板
id: "new_example_agent"
name: "新示例 Agent"
type: "task"
category: "example"
environment: "demo"
owner: "platform_team"
version: "1.0.0"
tags: ["demo", "example"]
deprecated: false
example_usage: "用于 XX Pipeline 演示"
description: |
  【示例 Agent】用于演示 XX 功能
  Agent 描述...
```

### 2. 废弃 Agent 时

不要直接删除，而是标记为废弃：

```yaml
id: "old_agent"
name: "旧 Agent"
deprecated: true  # 标记为废弃
deprecation_reason: "已被 new_agent 替代"
replacement: "new_agent"  # 推荐的替代 Agent
```

### 3. 评估时过滤 Agent

```bash
# 只评估生产 Agent（未来功能）
python -m src eval --category production --flows v1 --judge

# 排除测试 Agent（未来功能）
python -m src eval --exclude-category test --flows v1

# 只评估特定标签的 Agent（未来功能）
python -m src eval --tags memory,conversation --flows v1
```

---

## 🔍 常见问题

### Q1: 如何判断一个 Agent 是生产还是示例？

**判断标准**：
- **生产 Agent**: 实际业务中使用，有真实的业务目标和测试集
- **示例 Agent**: 用于演示 Pipeline 功能，主要在文档和教程中使用
- **测试 Agent**: 用于测试框架功能，不涉及实际业务

**检查方法**：
1. 查看 Agent 是否在 Pipeline 中被引用
2. 查看 Agent 的 `business_goal` 是否与实际业务相关
3. 查看 Agent 的测试集是否是真实数据

### Q2: mem0_l1_summarizer 和 mem_l1_summarizer 有什么区别？

**需要确认**：
- 查看两个 Agent 的配置和提示词
- 查看它们的测试集
- 确认哪个是当前使用的版本
- 如果 mem0_l1_summarizer 是旧版本，标记为 `deprecated: true`

### Q3: 示例 Agent 需要完整的测试集吗？

**建议**：
- 保留最小化的测试集用于演示（3-5个样本）
- 不需要像生产 Agent 那样完整的测试覆盖
- 在文档中说明这些是示例，不需要完整评估

### Q4: 如何处理 big_thing Agent？

**选项**：
1. **保留**: 如果需要测试 Agent Template Parser，保留并标记为测试用途
2. **移动**: 移到 `agents/tests/` 目录
3. **删除**: 如果不再需要，可以删除

**推荐**: 保留并标记为测试用途，因为它可以作为 Agent Template Parser 的测试案例。

### Q5: 如何避免误操作生产 Agent？

**建议**：
1. 使用分类过滤，只操作特定类型的 Agent
2. 在 CI/CD 中添加检查，防止误修改生产 Agent
3. 为生产 Agent 添加额外的保护机制（如需要审批）
4. 定期备份生产 Agent 的配置

---

## 📊 统计信息

运行以下命令查看 Agent 统计：

```bash
python scripts/list_agents_by_category.py
```

输出示例：
```
================================================================================
总计: 10 个 Agent

分类统计:
  🚀 生产环境 Agent        : 3
  ⚙️ 系统 Agent           : 1
  📋 示例 Agent           : 5
  🧪 测试 Agent           : 1
```

---

## 🚀 下一步

### 立即执行
1. ✅ 阅读 `AGENT_CLASSIFICATION_REPORT.md` 了解详细分析
2. ✅ 运行 `python scripts/add_agent_metadata.py --dry-run` 预览更改
3. ✅ 确认 mem0_l1_summarizer 的状态
4. ✅ 运行 `python scripts/add_agent_metadata.py` 添加元数据
5. ✅ 运行 `python scripts/list_agents_by_category.py --show-details` 验证结果

### 短期计划
- [ ] 增强 CLI 支持分类过滤（`--category`, `--exclude-category`）
- [ ] 添加 Agent 生命周期管理（deprecated, archived）
- [ ] 为示例 Agent 添加更详细的说明文档
- [ ] 在 README.md 中添加 Agent 分类说明

### 长期计划
- [ ] 考虑是否需要物理分离目录
- [ ] 实现 Agent 依赖管理
- [ ] 添加 Agent 使用统计
- [ ] 实现 Agent 版本管理

---

## 📚 相关文档

- [AGENT_CLASSIFICATION_REPORT.md](../archive/agent-classification-report.md) - 详细的分类分析报告
- [README.md](README.md) - 项目主文档
- [ARCHITECTURE.md](../ARCHITECTURE.md) - 系统架构文档
- [USAGE_GUIDE.md](../USAGE_GUIDE.md) - 使用指南

---

**最后更新**: 2025-12-15  
**维护者**: Platform Team
