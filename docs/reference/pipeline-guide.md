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

## 相关文档

- [回归测试指南](regression-testing.md)
- [数据结构指南](data-structure-guide.md)
- [评估模式指南](../EVAL_MODES_GUIDE.md)