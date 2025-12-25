# Pipeline 配置指南

本文档详细说明了 Pipeline 配置的语法、结构和最佳实践。

## 概述

Pipeline 是一个多步骤的工作流，允许将多个 Agent/Flow 组合串联起来，形成复杂的业务流程。每个 Pipeline 通过 YAML 配置文件定义，支持变体管理和基线比较。

## 配置文件结构

### 基本结构

```yaml
id: "pipeline_id"
name: "Pipeline 显示名称"
description: "Pipeline 用途和工作流描述"
default_testset: "relative/path/to/testset.jsonl"

inputs:
  - name: "input_field_name"
    desc: "字段描述"
    required: true

steps:
  - id: "step_identifier"
    type: "agent_flow"
    agent: "agent_id"
    flow: "flow_name"
    input_mapping:
      flow_param: "testset_field_or_previous_output"
    output_key: "step_output_identifier"
    model_override: "optional_model_name"

outputs:
  - key: "output_identifier"
    label: "人类可读标签"

baseline:
  name: "baseline_name"
  description: "基线配置描述"
  steps:
    step_id:
      flow: "baseline_flow_name"
      model: "optional_model_override"

variants:
  variant_name:
    description: "变体描述"
    overrides:
      step_id:
        flow: "alternative_flow_name"
        model: "alternative_model_name"
```

## 字段详解

### 必需字段

- **id**: Pipeline 的唯一标识符，必须是有效的 Python 标识符
- **name**: Pipeline 的显示名称，用于日志和报告
- **steps**: 步骤列表，至少包含一个步骤

### 可选字段

- **description**: Pipeline 的详细描述
- **default_testset**: 默认测试集文件路径（相对于 pipeline 数据目录）
- **inputs**: 输入字段规范列表
- **outputs**: 输出字段规范列表
- **baseline**: 基线配置
- **variants**: 变体配置字典

### 步骤配置

每个步骤必须包含：

- **id**: 步骤唯一标识符
- **agent**: 要使用的 Agent ID
- **flow**: 要使用的 Flow 名称
- **output_key**: 步骤输出的键名

可选字段：

- **type**: 步骤类型，目前只支持 "agent_flow"
- **input_mapping**: 输入参数映射
- **model_override**: 模型覆盖
- **description**: 步骤描述

### 输入映射

输入映射定义了如何将数据传递给步骤：

```yaml
input_mapping:
  # 从测试集字段映射
  text: "input_text"
  
  # 从前序步骤输出映射
  context: "step1_output"
  
  # 混合映射
  prompt: "user_query"
  history: "previous_step_result"
```

### 基线和变体

基线定义了 Pipeline 的标准配置：

```yaml
baseline:
  name: "production_baseline"
  description: "生产环境基线配置"
  steps:
    step1:
      flow: "stable_flow_v1"
    step2:
      flow: "stable_flow_v2"
      model: "gpt-4"
```

变体允许覆盖特定步骤的配置：

```yaml
variants:
  experimental_v1:
    description: "实验性变体，使用新的 prompt"
    overrides:
      step1:
        flow: "experimental_flow_v1"
      step2:
        model: "gpt-4-turbo"
```

## 配置示例

### 简单的两步骤 Pipeline

```yaml
id: "document_summary"
name: "文档摘要 Pipeline"
description: "清理文档内容并生成摘要"
default_testset: "documents.jsonl"

inputs:
  - name: "raw_text"
    desc: "原始文档文本"
    required: true

steps:
  - id: "clean"
    agent: "text_cleaner"
    flow: "clean_v1"
    input_mapping:
      text: "raw_text"
    output_key: "cleaned_text"
    
  - id: "summarize"
    agent: "summarizer"
    flow: "summary_v1"
    input_mapping:
      text: "cleaned_text"
    output_key: "summary"

outputs:
  - key: "summary"
    label: "文档摘要"

baseline:
  name: "stable_v1"
  description: "稳定版本基线"
  steps:
    clean:
      flow: "clean_v1"
    summarize:
      flow: "summary_v1"

variants:
  improved_v1:
    description: "改进版本，使用更好的摘要算法"
    overrides:
      summarize:
        flow: "summary_v2"
```

### 复杂的多步骤 Pipeline

```yaml
id: "customer_service_flow"
name: "客服处理流程"
description: "自动化客服请求处理，包括意图识别、信息提取和回复生成"

inputs:
  - name: "user_message"
    desc: "用户消息"
  - name: "conversation_history"
    desc: "对话历史"

steps:
  - id: "intent_detection"
    agent: "intent_classifier"
    flow: "classify_v1"
    input_mapping:
      message: "user_message"
      history: "conversation_history"
    output_key: "intent"
    
  - id: "entity_extraction"
    agent: "entity_extractor"
    flow: "extract_v1"
    input_mapping:
      message: "user_message"
      intent: "intent"
    output_key: "entities"
    
  - id: "response_generation"
    agent: "response_generator"
    flow: "generate_v1"
    input_mapping:
      intent: "intent"
      entities: "entities"
      history: "conversation_history"
    output_key: "response"

outputs:
  - key: "intent"
    label: "识别的意图"
  - key: "entities"
    label: "提取的实体"
  - key: "response"
    label: "生成的回复"

baseline:
  name: "production_v1"
  steps:
    intent_detection:
      flow: "classify_v1"
    entity_extraction:
      flow: "extract_v1"
    response_generation:
      flow: "generate_v1"

variants:
  enhanced_intent:
    description: "增强意图识别"
    overrides:
      intent_detection:
        flow: "classify_v2"
        
  better_responses:
    description: "改进回复生成"
    overrides:
      response_generation:
        flow: "generate_v2"
        model: "gpt-4"
```

## 最佳实践

### 1. 命名规范

- Pipeline ID 使用下划线分隔的小写字母
- 步骤 ID 使用描述性名称
- 输出键使用清晰的名称

### 2. 步骤设计

- 每个步骤应该有单一职责
- 步骤间的数据传递要明确
- 避免过长的 Pipeline，考虑拆分

### 3. 变体管理

- 基线应该是稳定、经过验证的配置
- 变体用于实验和 A/B 测试
- 为每个变体提供清晰的描述

### 4. 测试集设计

- 为 Pipeline 创建专门的测试集
- 包含各种场景和边界情况
- 使用标签组织不同类型的测试

### 5. 文档维护

- 及时更新配置文档
- 记录重要的配置变更
- 为复杂的 Pipeline 提供流程图

## 常见问题

### Q: 如何处理步骤间的复杂数据传递？

A: 使用 `input_mapping` 明确定义数据流，确保每个步骤的输入来源清晰。对于复杂的数据转换，考虑添加专门的数据处理步骤。

### Q: 什么时候应该创建新的变体？

A: 当需要测试不同的 flow、model 或参数组合时。变体适用于 A/B 测试、实验性功能和渐进式改进。

### Q: 如何优化 Pipeline 的执行性能？

A: 
- 减少不必要的步骤
- 优化每个步骤的执行时间
- 考虑并行执行（未来功能）
- 使用合适的模型和参数

### Q: 如何调试 Pipeline 执行问题？

A: 
- 检查日志输出
- 验证输入映射是否正确
- 确认 Agent 和 Flow 配置
- 使用小规模测试集进行调试

## Output Parser 配置

### 概述

Output Parser 是 LangChain 的核心功能，用于将 LLM 的文本输出转换为结构化数据（如 JSON、Pydantic 对象）。在 Pipeline 中，可以为每个步骤的 Flow 配置 Output Parser，确保输出格式的可靠性。

### 配置方式

Output Parser 在 Flow 配置文件中定义（`agents/{agent_id}/prompts/{flow_name}.yaml`）：

```yaml
# agents/my_agent/prompts/my_flow_v1.yaml
name: "my_flow_v1"
description: "带 Output Parser 的 Flow"

system_prompt: |
  你是一个助手，请以 JSON 格式输出结果。

user_template: |
  处理以下内容：{text}

# Output Parser 配置
output_parser:
  type: "json"  # 支持: json, pydantic, list, none
  schema:
    type: "object"
    properties:
      result: {type: "string"}
      confidence: {type: "number"}
    required: ["result"]
  retry_on_error: true
  max_retries: 3
```

### 支持的 Parser 类型

#### 1. JSON Parser

最常用的类型，将 LLM 输出解析为 Python 字典：

```yaml
output_parser:
  type: "json"
  schema:
    type: "object"
    properties:
      summary: {type: "string"}
      keywords: {type: "array", items: {type: "string"}}
      score: {type: "number", minimum: 0, maximum: 10}
    required: ["summary", "score"]
  retry_on_error: true
  max_retries: 3
```

**使用场景**：
- 结构化输出（摘要、分类结果、评分）
- 多字段返回
- 需要验证输出格式

#### 2. Pydantic Parser

使用 Pydantic 模型进行严格的类型验证：

```yaml
output_parser:
  type: "pydantic"
  pydantic_model: "MyOutputModel"  # 需要在代码中定义
  retry_on_error: true
  max_retries: 3
```

**使用场景**：
- 需要严格类型检查
- 复杂的嵌套结构
- 需要数据验证逻辑

#### 3. List Parser

解析逗号分隔的列表：

```yaml
output_parser:
  type: "list"
```

**使用场景**：
- 关键词提取
- 标签生成
- 简单列表输出

#### 4. None（默认）

不使用 Parser，返回原始字符串：

```yaml
output_parser:
  type: "none"
```

或者不配置 `output_parser` 字段（向后兼容）。

### 错误处理和重试

当 LLM 输出格式不符合预期时，Output Parser 可以自动重试：

```yaml
output_parser:
  type: "json"
  schema: {...}
  retry_on_error: true  # 启用重试
  max_retries: 3        # 最多重试 3 次
  fix_prompt: |         # 可选：自定义修复提示
    上一次输出格式不正确，请严格按照 JSON schema 输出。
```

**重试机制**：
1. 第一次解析失败时，使用 LangChain 的 `OutputFixingParser` 尝试修复
2. 如果修复失败，重新调用 LLM（最多 `max_retries` 次）
3. 如果所有重试都失败，返回降级结果（包含错误信息）

### 最佳实践

1. **在 Prompt 中明确输出格式**：
   ```yaml
   system_prompt: |
     请以 JSON 格式输出，包含以下字段：
     - summary: 摘要文本
     - score: 0-10 的评分
   ```

2. **使用合理的 Schema**：
   - 只定义必需的字段
   - 使用清晰的字段名
   - 提供字段描述和约束

3. **设置合理的重试次数**：
   - 简单格式：1-2 次
   - 复杂格式：2-3 次
   - 避免过多重试（增加成本和延迟）

4. **测试 Parser 配置**：
   ```bash
   # 使用小规模测试集验证
   python -m src eval --agent my_agent --flows my_flow_v1 --limit 3
   ```

### 示例：Judge Agent 的 Output Parser

Judge Agent 是 Output Parser 的典型应用场景：

```yaml
# agents/judge_default/prompts/judge_v2.yaml
name: "judge_v2"
description: "带 Output Parser 的 Judge"

system_prompt: |
  你是评估助手，请以 JSON 格式输出评估结果。

user_template: |
  评估以下输出...

output_parser:
  type: "json"
  schema:
    type: "object"
    properties:
      overall_score:
        type: "number"
        minimum: 0
        maximum: 10
      must_have_check:
        type: "array"
        items:
          type: "object"
          properties:
            item: {type: "string"}
            satisfied: {type: "boolean"}
            comment: {type: "string"}
      nice_to_have_check:
        type: "array"
        items:
          type: "object"
          properties:
            item: {type: "string"}
            satisfied: {type: "boolean"}
            comment: {type: "string"}
      overall_comment:
        type: "string"
    required: ["overall_score", "must_have_check", "overall_comment"]
  retry_on_error: true
  max_retries: 3
```

## 评估配置

### Pipeline 评估概述

Pipeline 评估与 Agent 评估使用统一的接口，支持规则评估和 Judge 评估两种方式。

### 评估配置方式

#### 1. 在 Pipeline 配置中定义评估

```yaml
# pipelines/my_pipeline.yaml
id: "my_pipeline"
name: "我的 Pipeline"

# ... steps 配置 ...

# 评估配置
evaluation:
  # 规则评估
  rules:
    - type: "length"
      field: "summary"
      min: 10
      max: 500
      
    - type: "contains"
      field: "summary"
      patterns: ["关键词1", "关键词2"]
      
    - type: "not_contains"
      field: "summary"
      patterns: ["禁用词"]
  
  # Judge 评估
  judge:
    enabled: true
    agent: "judge_default"
    flow: "judge_v2"
    model: "gpt-4"  # 可选：覆盖默认模型
    
  # 评分范围
  scale:
    min: 0
    max: 10
```

#### 2. 使用 Agent 的评估配置

如果 Pipeline 的最后一个步骤是某个 Agent，可以复用该 Agent 的评估配置：

```yaml
# agents/my_agent/agent.yaml
id: "my_agent"
name: "我的 Agent"

# 评估配置
evaluation:
  rules:
    - type: "length"
      field: "output"
      min: 10
  judge:
    enabled: true
    agent: "judge_default"
    flow: "judge_v2"
```

### 评估目标步骤

默认情况下，Pipeline 评估使用最后一个步骤的输出。可以通过 `evaluation_target` 指定其他步骤：

```yaml
# pipelines/my_pipeline.yaml
evaluation:
  target_step: "step2"  # 评估 step2 的输出，而非最后一步
  rules: [...]
  judge: {...}
```

### 中间步骤输出传递

在 Judge 评估时，所有步骤的输出都会作为上下文传递给 Judge：

```yaml
# Judge 会收到以下上下文
{
  "final_output": "最后一步的输出",
  "step_outputs": {
    "step1": "步骤1的输出",
    "step2": "步骤2的输出",
    "step3": "步骤3的输出"
  },
  "test_case": {...}
}
```

### 评估结果格式

Pipeline 评估结果包含所有步骤的信息：

```json
{
  "sample_id": "test_001",
  "entity_type": "pipeline",
  "entity_id": "my_pipeline",
  "variant": "baseline",
  "output": "最终输出",
  "step_outputs": {
    "step1": "步骤1输出",
    "step2": "步骤2输出"
  },
  "overall_score": 8.5,
  "must_have_pass": true,
  "rule_violations": [],
  "judge_feedback": "评估反馈",
  "execution_time": 2.5,
  "token_usage": {
    "input_tokens": 150,
    "output_tokens": 80,
    "total_tokens": 230
  }
}
```

### 评估命令

```bash
# 运行 Pipeline 并评估
python -m src eval --pipeline my_pipeline --variants baseline --judge

# 只使用规则评估
python -m src eval --pipeline my_pipeline --variants baseline --rules-only

# 对比多个变体
python -m src eval --pipeline my_pipeline --variants baseline,experiment_v1 --judge

# 导出评估结果
python -m src export --pipeline my_pipeline --format csv
```

## 常见问题（更新）

### Q: Output Parser 解析失败怎么办？

A: 
1. **检查 Prompt**：确保 Prompt 中明确说明了输出格式
2. **查看原始输出**：检查 LLM 的原始输出，找出格式问题
3. **调整 Schema**：简化 Schema，只保留必需字段
4. **增加重试次数**：设置 `max_retries: 3`
5. **使用降级处理**：系统会自动返回包含错误信息的降级结果

### Q: 如何调试 Output Parser 问题？

A:
```bash
# 启用详细日志
export LOG_LEVEL=DEBUG
python -m src eval --agent my_agent --flows my_flow --limit 1

# 查看原始输出和解析结果
# 日志会显示：
# - LLM 原始输出
# - Parser 尝试解析
# - 解析错误信息
# - 重试过程
```

### Q: Pipeline 评估和 Agent 评估有什么区别？

A:
- **相同点**：使用相同的规则引擎和 Judge Agent
- **不同点**：
  - Pipeline 评估包含所有步骤的输出
  - Pipeline 可以指定评估目标步骤
  - Pipeline 的 Judge 会收到中间步骤的上下文

### Q: 如何为 Pipeline 的不同步骤配置不同的 Output Parser？

A: 在每个步骤引用的 Flow 配置中分别定义 Output Parser：

```yaml
# agents/agent_a/prompts/flow_v1.yaml
output_parser:
  type: "json"
  schema: {...}

# agents/agent_b/prompts/flow_v1.yaml
output_parser:
  type: "list"
```

### Q: Output Parser 会影响性能吗？

A:
- **JSON Parser**：几乎无影响（纯 Python 解析）
- **Pydantic Parser**：轻微影响（需要验证）
- **重试机制**：显著影响（需要额外的 LLM 调用）

建议：
- 优化 Prompt 减少解析失败率
- 合理设置重试次数（2-3 次）
- 使用性能监控查看解析成功率

## 相关文档

- [回归测试指南](regression-testing.md)
- [数据结构指南](data-structure-guide.md)
- [评估模式指南](eval-modes-guide.md)
- [Output Parser 使用指南](output-parser-guide.md)