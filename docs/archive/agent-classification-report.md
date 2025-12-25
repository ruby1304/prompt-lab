# Agent 分类分析报告

## 📊 当前 Agent 清单

### 1. 业务实际使用的 Agent（Production Agents）

这些 Agent 是你实际业务中需要评估、测试和使用的：

#### 1.1 对话记忆相关
- **mem_l1_summarizer** - 一级记忆总结助手
  - 用途：处理对话总结，生成4-10句的客观第三人称总结
  - 业务目标：为二级、三级记忆和用户画像提供基础
  - 状态：✅ 业务核心 Agent

- **mem0_l1_summarizer** - 另一个一级记忆总结版本
  - 用途：可能是 mem_l1_summarizer 的变体或旧版本
  - 状态：⚠️ 需要确认是否还在使用

#### 1.2 用户画像相关
- **usr_profile** - 用户画像提取专家
  - 用途：从对话历史中提取十维度用户画像
  - 业务目标：为个性化服务提供数据支持
  - 状态：✅ 业务核心 Agent

### 2. 示例/演示用的 Agent（Demo/Example Agents）

这些 Agent 是为了演示 Pipeline 功能而创建的示例：

#### 2.1 文档处理 Pipeline 示例
- **text_cleaner** - 文本清洗助手
  - 用途：清洗和规范化文本内容
  - 使用场景：`pipelines/document_summary.yaml` 中的第一步
  - 状态：📋 示例 Agent（用于演示 Pipeline）

- **document_summarizer** - 文档摘要助手
  - 用途：生成文档的简洁摘要
  - 使用场景：`pipelines/document_summary.yaml` 中的第二步
  - 状态：📋 示例 Agent（用于演示 Pipeline）

#### 2.2 客服流程 Pipeline 示例
- **intent_classifier** - 意图识别助手
  - 用途：识别用户消息的意图
  - 使用场景：`pipelines/customer_service_flow.yaml` 中的第一步
  - 状态：📋 示例 Agent（用于演示 Pipeline）

- **entity_extractor** - 实体提取助手
  - 用途：从用户消息中提取关键实体
  - 使用场景：`pipelines/customer_service_flow.yaml` 中的第二步
  - 状态：📋 示例 Agent（用于演示 Pipeline）

- **response_generator** - 回复生成助手
  - 用途：生成客服回复
  - 使用场景：`pipelines/customer_service_flow.yaml` 中的第三步
  - 状态：📋 示例 Agent（用于演示 Pipeline）

### 3. 测试/模板用的 Agent（Test/Template Agents）

#### 3.1 测试用
- **big_thing** - 自动生成的测试 Agent
  - 用途：测试 Agent Template Parser 功能
  - 状态：🧪 测试 Agent

#### 3.2 模板
- **_template** - Agent 模板目录
  - 用途：作为创建新 Agent 的模板
  - 状态：📝 模板

### 4. 系统 Agent（System Agents）

- **judge_default** - 通用评估 Agent
  - 用途：对其他 Agent 的输出进行自动打分和评估
  - 类型：Judge Agent（不是 Task Agent）
  - 状态：✅ 系统核心组件

---

## 🎯 重组建议

### 方案 1：按用途分类（推荐）

```
agents/
├── _template/              # 模板
├── _system/                # 系统 Agent
│   └── judge_default/
├── production/             # 生产环境 Agent
│   ├── mem_l1_summarizer/
│   ├── mem0_l1_summarizer/
│   └── usr_profile/
├── examples/               # 示例 Agent
│   ├── text_cleaner/
│   ├── document_summarizer/
│   ├── intent_classifier/
│   ├── entity_extractor/
│   └── response_generator/
└── tests/                  # 测试 Agent
    └── big_thing/
```

**优点**：
- ✅ 清晰区分生产和示例
- ✅ 避免误操作生产 Agent
- ✅ 便于管理和维护

**缺点**：
- ⚠️ 需要修改代码中的 Agent 加载逻辑
- ⚠️ 需要更新所有 Pipeline 配置

### 方案 2：使用标签/元数据标记（推荐）

在每个 Agent 的 `agent.yaml` 中添加 `category` 字段：

```yaml
# 生产 Agent
id: "mem_l1_summarizer"
name: "一级记忆总结助手"
category: "production"  # 新增字段
environment: "production"  # 新增字段
...

# 示例 Agent
id: "text_cleaner"
name: "文本清洗助手"
category: "example"  # 新增字段
environment: "demo"  # 新增字段
...

# 测试 Agent
id: "big_thing"
name: "Big Thing"
category: "test"  # 新增字段
environment: "test"  # 新增字段
...
```

**优点**：
- ✅ 不需要移动文件
- ✅ 不需要修改代码逻辑
- ✅ 可以通过 CLI 过滤显示
- ✅ 向后兼容

**缺点**：
- ⚠️ 需要手动给每个 Agent 添加标签

### 方案 3：使用命名前缀（最简单）

```
agents/
├── _template/              # 模板（已有前缀）
├── prod_mem_l1_summarizer/     # 生产：prod_ 前缀
├── prod_mem0_l1_summarizer/
├── prod_usr_profile/
├── demo_text_cleaner/          # 示例：demo_ 前缀
├── demo_document_summarizer/
├── demo_intent_classifier/
├── demo_entity_extractor/
├── demo_response_generator/
├── test_big_thing/             # 测试：test_ 前缀
└── judge_default/              # 系统：无前缀或 sys_ 前缀
```

**优点**：
- ✅ 一眼就能看出 Agent 类型
- ✅ 不需要修改代码逻辑
- ✅ 文件系统自动排序

**缺点**：
- ⚠️ 需要重命名目录和更新所有引用
- ⚠️ 破坏现有的命名约定

---

## 💡 推荐方案：方案 2（标签/元数据）

### 理由：
1. **最小侵入性**：不需要移动文件或重命名
2. **向后兼容**：旧代码仍然可以正常工作
3. **灵活性高**：可以添加更多元数据（owner, version, tags 等）
4. **易于实现**：只需要修改 YAML 配置文件

### 实施步骤：

#### 步骤 1：定义标准元数据字段

在 `agent.yaml` 中添加以下字段：

```yaml
# 必需字段
category: "production" | "example" | "test" | "system" | "template"
environment: "production" | "staging" | "demo" | "test"

# 可选字段
owner: "team_name"  # 负责团队
version: "1.0.0"    # 版本号
tags: ["memory", "conversation"]  # 标签
deprecated: false   # 是否已废弃
```

#### 步骤 2：更新所有 Agent 配置

为每个 Agent 添加分类信息（见下面的具体配置）

#### 步骤 3：增强 CLI 支持

```bash
# 列出所有生产 Agent
python -m src agent list --category production

# 列出所有示例 Agent
python -m src agent list --category example

# 只评估生产 Agent
python -m src eval --category production --flows v1 --judge

# 排除测试 Agent
python -m src eval --exclude-category test --flows v1
```

#### 步骤 4：更新文档

在 README.md 中添加 Agent 分类说明

---

## 📝 具体配置建议

### 生产 Agent 配置

```yaml
# agents/mem_l1_summarizer/agent.yaml
id: "mem_l1_summarizer"
name: "一级记忆总结助手"
type: "task"
category: "production"
environment: "production"
owner: "memory_team"
version: "1.0.0"
tags: ["memory", "conversation", "summarization"]
deprecated: false
# ... 其他配置保持不变
```

```yaml
# agents/usr_profile/agent.yaml
id: "usr_profile"
name: "用户画像提取专家"
type: "task"
category: "production"
environment: "production"
owner: "profile_team"
version: "1.0.0"
tags: ["profile", "user_analysis"]
deprecated: false
# ... 其他配置保持不变
```

### 示例 Agent 配置

```yaml
# agents/text_cleaner/agent.yaml
id: "text_cleaner"
name: "文本清洗助手"
type: "task"
category: "example"
environment: "demo"
owner: "platform_team"
version: "1.0.0"
tags: ["demo", "text_processing"]
deprecated: false
description: |
  【示例 Agent】用于演示 Pipeline 功能
  负责清洗和规范化文本内容
# ... 其他配置保持不变
```

### 测试 Agent 配置

```yaml
# agents/big_thing/agent.yaml
id: "big_thing"
name: "Big Thing"
type: "task"
category: "test"
environment: "test"
owner: "platform_team"
version: "1.0.0"
tags: ["test", "template_parser"]
deprecated: false
description: |
  【测试 Agent】用于测试 Agent Template Parser 功能
  自动生成的测试 Agent
# ... 其他配置保持不变
```

### 系统 Agent 配置

```yaml
# agents/judge_default/agent.yaml
id: "judge_default"
name: "通用评估 Agent"
type: "judge"
category: "system"
environment: "production"
owner: "platform_team"
version: "2.0.0"
tags: ["system", "evaluation", "judge"]
deprecated: false
# ... 其他配置保持不变
```

---

## 🔍 需要确认的问题

### 1. mem0_l1_summarizer vs mem_l1_summarizer
- ❓ 这两个 Agent 的区别是什么？
- ❓ mem0_l1_summarizer 是旧版本吗？
- ❓ 是否需要保留两个版本？

**建议**：
- 如果 mem0_l1_summarizer 是旧版本，标记为 `deprecated: true`
- 如果两者都在使用，添加清晰的说明区分用途

### 2. 示例 Agent 的测试集
- ❓ 示例 Agent 是否需要完整的测试集？
- ❓ 是否需要为示例 Agent 运行评估？

**建议**：
- 保留最小化的测试集用于演示
- 在文档中说明这些是示例，不需要完整评估

### 3. big_thing Agent
- ❓ 这个 Agent 是否还需要？
- ❓ 是否可以移到 tests/ 目录？

**建议**：
- 如果只用于测试，考虑移到 `agents/tests/` 或直接删除
- 如果需要保留，确保标记为测试用途

---

## 📋 实施清单

### 立即执行（高优先级）
- [ ] 为所有 Agent 添加 `category` 和 `environment` 字段
- [ ] 在 Agent 描述中明确标注【生产】【示例】【测试】
- [ ] 更新 README.md，添加 Agent 分类说明
- [ ] 确认 mem0_l1_summarizer 的状态

### 短期执行（中优先级）
- [ ] 增强 CLI 支持分类过滤
- [ ] 添加 Agent 列表命令（按分类显示）
- [ ] 更新文档，说明如何创建不同类型的 Agent
- [ ] 为示例 Agent 添加更详细的说明文档

### 长期执行（低优先级）
- [ ] 考虑是否需要物理分离目录
- [ ] 添加 Agent 生命周期管理（deprecated, archived）
- [ ] 实现 Agent 依赖管理
- [ ] 添加 Agent 使用统计

---

## 🎯 总结

**当前状态**：
- 生产 Agent：2-3 个（mem_l1_summarizer, usr_profile, mem0_l1_summarizer?）
- 示例 Agent：5 个（text_cleaner, document_summarizer, intent_classifier, entity_extractor, response_generator）
- 测试 Agent：1 个（big_thing）
- 系统 Agent：1 个（judge_default）

**推荐方案**：
使用元数据标签（category, environment）来分类，不移动文件，保持向后兼容。

**下一步行动**：
1. 确认 mem0_l1_summarizer 的状态
2. 为所有 Agent 添加分类元数据
3. 更新文档说明
4. 增强 CLI 支持

---

**生成时间**: 2025-12-15  
**分析者**: Kiro AI Assistant
