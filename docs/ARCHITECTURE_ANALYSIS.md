# Prompt Lab 架构分析：与 LangChain 生态的对比

## 当前架构映射

### 已实现的 LangChain 概念

| LangChain 概念 | Prompt Lab 实现 | 说明 |
|---------------|----------------|------|
| **Chain** | Flow | 单个可执行的 Prompt + LLM 组合 |
| **SequentialChain** | Pipeline | 多步骤串联执行 |
| **Prompt Template** | Flow YAML (system_prompt + user_template) | 提示词模板 |
| **LLM** | ChatOpenAI | 底层模型调用 |
| **Output Parser** | ✅ 已实现 | 结构化输出解析（JSON/Pydantic/List） |

---

## 🔍 缺失的关键维度

### 1. **Memory（记忆系统）** ⭐⭐⭐⭐⭐

**LangChain 中的 Memory**：
- `ConversationBufferMemory`：保存完整对话历史
- `ConversationSummaryMemory`：总结式记忆
- `ConversationBufferWindowMemory`：滑动窗口记忆
- `VectorStoreRetrieverMemory`：基于向量检索的记忆

**当前状态**：
- ❌ 没有内置的 Memory 管理机制
- ✅ 测试集中有 `chat_round_30` 字段（对话历史），但是**静态的**
- ❌ Pipeline 步骤间只传递单次输出，没有累积记忆

**影响**：
- 无法处理多轮对话场景
- Pipeline 中的步骤无法"记住"之前的交互
- 无法实现对话式 Agent

**建议**：
```yaml
# 在 Agent 配置中增加 memory 配置
memory:
  type: "buffer"  # buffer | summary | window | vector
  max_tokens: 2000
  summary_agent: "summarizer"  # 用于 summary 类型
  
# 在 Pipeline 中增加 memory 配置
pipeline:
  memory:
    enabled: true
    scope: "pipeline"  # pipeline | step
    persist: true
```

---

### 2. **Tools（工具调用）** ⭐⭐⭐⭐⭐

**LangChain 中的 Tools**：
- 函数调用（Function Calling）
- 外部 API 集成
- 数据库查询
- 文件操作
- 计算器、搜索引擎等

**当前状态**：
- ❌ 完全缺失 Tool 支持
- ✅ Agent 只能做纯文本生成任务
- ❌ 无法调用外部系统或执行动作

**影响**：
- Agent 能力受限于纯文本处理
- 无法实现 ReAct、Function Calling 等高级模式
- 无法与外部系统集成

**建议**：
```yaml
# 在 Agent 配置中增加 tools 配置
tools:
  - name: "search"
    type: "api"
    endpoint: "https://api.search.com"
    description: "搜索互联网信息"
  
  - name: "calculator"
    type: "function"
    function: "math.eval"
    description: "执行数学计算"

# 在 Flow 中启用 tool 使用
flows:
  - name: "agent_v1"
    file: "agent_v1.yaml"
    tools_enabled: true
    max_tool_calls: 5
```

---

### 3. **Retriever（检索增强）** ⭐⭐⭐⭐

**LangChain 中的 Retriever**：
- `VectorStoreRetriever`：向量数据库检索
- `ContextualCompressionRetriever`：上下文压缩
- `MultiQueryRetriever`：多查询检索
- `EnsembleRetriever`：混合检索

**当前状态**：
- ❌ 没有 RAG（检索增强生成）支持
- ✅ 可以通过 `context` 字段手动传入上下文，但是**静态的**
- ❌ 无法动态检索知识库

**影响**：
- 无法实现 RAG 应用
- 知识必须硬编码在 prompt 中
- 无法处理大规模知识库

**建议**：
```yaml
# 在 Agent 配置中增加 retriever 配置
retriever:
  type: "vector"  # vector | keyword | hybrid
  vector_store: "pinecone"
  index_name: "knowledge_base"
  top_k: 5
  score_threshold: 0.7

# 在 Flow 中自动注入检索结果
flows:
  - name: "rag_v1"
    file: "rag_v1.yaml"
    retriever_enabled: true
    retrieval_field: "retrieved_context"  # 注入到哪个变量
```

---

### 4. **Output Parser（输出解析器）** ✅ 已实现

**LangChain 中的 Output Parser**：
- `PydanticOutputParser`：解析为 Pydantic 模型
- `StructuredOutputParser`：结构化输出
- `JsonOutputParser`：JSON 解析
- `CommaSeparatedListOutputParser`：列表解析

**当前状态**：
- ✅ 支持 JSON、Pydantic、List 等多种 Parser 类型
- ✅ Judge Agent 使用 JSON Output Parser 自动解析
- ✅ 自动验证和错误恢复（重试机制）
- ✅ 向后兼容（未配置时返回字符串）

**已实现功能**：
- 在 Flow 配置中声明 output_parser
- 自动解析 LLM 输出为结构化数据
- 解析失败时自动重试（可配置）
- 降级处理机制
- 性能监控（解析成功率、重试次数）

**配置示例**：
```yaml
# 在 Flow 配置中增加 output_parser
output_parser:
  type: "json"  # json | pydantic | list | none
  schema:
    type: "object"
    properties:
      summary: {type: "string"}
      score: {type: "number"}
    required: ["summary", "score"]
  retry_on_error: true
  max_retries: 3
```

**参考文档**：
- [Output Parser 使用指南](guides/output-parser-usage.md)
- [Output Parser 详细指南](reference/output-parser-guide.md)

---

### 5. **Callbacks（回调系统）** ⭐⭐⭐

**LangChain 中的 Callbacks**：
- `StreamingStdOutCallbackHandler`：流式输出
- `LangChainTracer`：追踪和调试
- `WandbCallbackHandler`：集成 W&B
- 自定义回调

**当前状态**：
- ❌ 没有回调机制
- ✅ 有基本的日志记录
- ❌ 无法实时监控执行过程

**影响**：
- 无法流式输出
- 调试困难
- 无法集成监控工具

**建议**：
```yaml
# 在全局配置中增加 callbacks
callbacks:
  - type: "logging"
    level: "INFO"
  
  - type: "streaming"
    enabled: true
  
  - type: "tracing"
    backend: "langsmith"
    project: "prompt-lab"
```

---

### 6. **Router/Conditional Logic（路由/条件逻辑）** ⭐⭐⭐

**LangChain 中的 Router**：
- `LLMRouterChain`：基于 LLM 的路由
- `MultiPromptChain`：多提示词路由
- `ConditionalChain`：条件分支

**当前状态**：
- ❌ Pipeline 只支持线性执行
- ❌ 无法根据条件选择不同的分支
- ❌ 无法实现复杂的决策树

**影响**：
- Pipeline 灵活性受限
- 无法实现条件分支逻辑
- 无法根据中间结果动态调整流程

**建议**：
```yaml
# 在 Pipeline 中增加条件步骤
steps:
  - id: "classify"
    agent: "classifier"
    flow: "classify_v1"
    output_key: "category"
  
  - id: "route"
    type: "router"
    condition: "category"
    branches:
      "urgent":
        next_step: "urgent_handler"
      "normal":
        next_step: "normal_handler"
      "default":
        next_step: "fallback_handler"
```

---

### 7. **Agents（自主决策 Agent）** ⭐⭐⭐⭐

**LangChain 中的 Agents**：
- `ReAct Agent`：推理-行动循环
- `OpenAI Functions Agent`：函数调用
- `Conversational Agent`：对话式 Agent
- `Plan-and-Execute Agent`：规划-执行模式

**当前状态**：
- ❌ 当前的 "Agent" 只是配置单元，不是自主决策的 Agent
- ❌ 没有 ReAct 循环
- ❌ 没有自主工具选择和调用

**影响**：
- 无法实现真正的自主 Agent
- 无法处理需要多步推理的复杂任务
- 能力受限于单次 LLM 调用

**建议**：
```yaml
# 增加 autonomous_agent 类型
type: "autonomous_agent"  # 区别于 task agent
agent_type: "react"  # react | function_calling | plan_execute
max_iterations: 10
tools:
  - search
  - calculator
  - database_query
```

---

### 8. **Document Loaders & Text Splitters（文档加载与分割）** ⭐⭐

**LangChain 中的功能**：
- 各种文档加载器（PDF, Word, HTML, etc.）
- 文本分割策略（按字符、按 token、递归分割）

**当前状态**：
- ❌ 没有文档处理能力
- ✅ 测试集是 JSONL 格式，结构化的
- ❌ 无法处理长文档

**影响**：
- 无法处理文档类任务
- 无法实现文档问答
- 长文本处理困难

---

## 📊 优先级矩阵

| 维度 | 重要性 | 实现难度 | 状态 | 建议优先级 |
|-----|-------|---------|------|----------|
| **Output Parser** | ⭐⭐⭐⭐ | 低 | ✅ 已完成 | - |
| **Memory** | ⭐⭐⭐⭐⭐ | 中 | 📋 计划中 | 🔥 P0 |
| **Tools** | ⭐⭐⭐⭐⭐ | 高 | 📋 计划中 | 🔥 P1 |
| **Retriever** | ⭐⭐⭐⭐ | 中 | 📋 计划中 | 🔥 P1 |
| **Router** | ⭐⭐⭐ | 中 | 📋 计划中 | P2 |
| **Callbacks** | ⭐⭐⭐ | 低 | 📋 计划中 | P2 |
| **Autonomous Agents** | ⭐⭐⭐⭐ | 高 | 📋 计划中 | P3 |
| **Document Loaders** | ⭐⭐ | 低 | 📋 计划中 | P3 |

---

## 🎯 建议的迭代路线

### Phase 1: 基础增强 ✅ 已完成
1. ✅ **Output Parser**：让 Judge Agent 和结构化输出更可靠
   - 支持 JSON、Pydantic、List 等多种 Parser
   - 自动重试和降级处理
   - 统一评估接口
   - 性能监控

### Phase 2: 状态管理（1-2周）
2. **Memory**：支持多轮对话和 Pipeline 记忆

### Phase 3: 能力扩展（2-3周）
3. **Tools**：支持函数调用和外部集成
4. **Retriever**：支持 RAG 应用

### Phase 4: 高级特性（3-4周）
5. **Router**：支持条件分支和动态路由
6. **Callbacks**：改进监控和调试体验

### Phase 5: 自主智能（长期）
7. **Autonomous Agents**：实现真正的自主决策 Agent
8. **Document Loaders**：完善文档处理能力

---

## 💡 关键洞察

1. **当前架构的优势**：
   - 清晰的业务抽象（Agent/Flow/Pipeline）
   - 完善的评估和回归测试体系
   - 良好的版本管理和对比能力

2. **当前架构的局限**：
   - 主要支持**单次文本生成**任务
   - 缺少**状态管理**（Memory）
   - 缺少**外部交互**（Tools, Retriever）
   - 缺少**动态决策**（Router, Autonomous Agents）

3. **演进方向**：
   - 从"提示词实验平台"→"全功能 Agent 开发平台"
   - 从"静态配置"→"动态决策"
   - 从"单次调用"→"多轮交互"

---

## 🔗 参考资源

- [LangChain Conceptual Guide](https://python.langchain.com/docs/concepts)
- [LangChain Expression Language (LCEL)](https://python.langchain.com/docs/expression_language/)
- [LangChain Agents](https://python.langchain.com/docs/modules/agents/)
