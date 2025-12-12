# Prompt Lab 系统架构文档

## 概述

Prompt Lab 是一个基于 LangChain 构建的 AI Agent 实验平台，提供从配置、执行到评估的完整工作流。本文档详细说明系统的架构设计、核心组件、数据流和扩展机制。

## 架构概览

### 分层架构

Prompt Lab 采用三层架构设计：

```
┌─────────────────────────────────────────────────────────────────┐
│                      配置层 (Configuration Layer)                │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │ Agent Config │    │ Flow Config  │    │Pipeline Config│     │
│  │              │    │              │    │              │     │
│  │ - ID         │    │ - Prompts    │    │ - Steps      │     │
│  │ - Flows      │    │ - Model      │    │ - Inputs     │     │
│  │ - Evaluation │    │ - Parser     │    │ - Outputs    │     │
│  │ - Testsets   │    │ - Defaults   │    │ - Variants   │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      执行层 (Execution Layer)                    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Flow Executor (chains.py)                             │    │
│  │  ┌──────────────────────────────────────────────┐     │    │
│  │  │  ChatPromptTemplate                           │     │    │
│  │  │         ↓                                     │     │    │
│  │  │  ChatOpenAI (LLM)                            │     │    │
│  │  │         ↓                                     │     │    │
│  │  │  Output Parser (JSON/Pydantic/List)          │     │    │
│  │  │         ↓                                     │     │    │
│  │  │  Retry Logic (OutputFixingParser)            │     │    │
│  │  └──────────────────────────────────────────────┘     │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Pipeline Runner (pipeline_runner.py)                  │    │
│  │  - 步骤编排和依赖管理                                   │    │
│  │  - 数据传递和映射                                       │    │
│  │  - 错误处理和降级                                       │    │
│  │  - 性能监控和统计                                       │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      评估层 (Evaluation Layer)                   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  统一评估接口 (Unified Evaluation Interface)            │    │
│  │  ┌──────────────┐      ┌──────────────┐              │    │
│  │  │ Agent Eval   │      │ Pipeline Eval│              │    │
│  │  │              │      │              │              │    │
│  │  │ - Rules      │      │ - Rules      │              │    │
│  │  │ - Judge      │      │ - Judge      │              │    │
│  │  │ - Metrics    │      │ - Metrics    │              │    │
│  │  └──────────────┘      └──────────────┘              │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  规则引擎 (Rule Engine)                                 │    │
│  │  - Length Check                                         │    │
│  │  - Contains/Not Contains                                │    │
│  │  - Regex Match                                          │    │
│  │  - Custom Rules                                         │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Judge Agent                                            │    │
│  │  - LLM-based Evaluation                                 │    │
│  │  - Structured Output (JSON)                             │    │
│  │  - Must-have/Nice-to-have Checks                        │    │
│  └────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## 核心组件

### 1. Agent（智能体）

**定义**：具有明确业务目标的任务单元。

**组成**：
- **配置文件** (`agent.yaml`)：定义 Agent 的元数据、Flows、评估标准
- **Flows**：多个提示词版本，用于迭代优化
- **测试集**：JSONL 格式的测试用例
- **评估配置**：规则和 Judge 配置

**目录结构**：
```
agents/
└── my_agent/
    ├── agent.yaml           # Agent 配置
    ├── prompts/             # Flow 配置
    │   ├── flow_v1.yaml
    │   └── flow_v2.yaml
    └── testsets/            # 测试集
        └── default.jsonl
```

**配置示例**：
```yaml
id: "my_agent"
name: "我的 Agent"
business_goal: "处理用户输入并生成结构化输出"

flows:
  - name: "flow_v1"
    file: "flow_v1.yaml"
  - name: "flow_v2"
    file: "flow_v2.yaml"

evaluation:
  rules:
    - type: "length"
      field: "output"
      min: 10
      max: 500
  judge:
    enabled: true
    agent: "judge_default"
    flow: "judge_v2"

case_fields:
  - name: "input_text"
    required: true
  - name: "context"
    required: false
```

### 2. Flow（执行流）

**定义**：Agent 的一个具体实现版本，是可执行的 LangChain Chain。

**本质**：
- **LangChain 层面**：`ChatPromptTemplate | ChatOpenAI | OutputParser`
- **业务层面**：Agent 的一个提示词版本

**配置示例**：
```yaml
name: "flow_v1"
description: "基础版本"

system_prompt: |
  你是一个助手，请处理用户输入。

user_template: |
  输入：{input_text}
  上下文：{context}

defaults:
  context: ""

# Output Parser 配置（可选）
output_parser:
  type: "json"
  schema:
    type: "object"
    properties:
      result: {type: "string"}
      confidence: {type: "number"}
    required: ["result"]
  retry_on_error: true
  max_retries: 3
```

**执行流程**：
```
1. 加载 Flow 配置
2. 构建 ChatPromptTemplate
3. 创建 ChatOpenAI 实例
4. 如果配置了 Output Parser，创建 Parser
5. 组装 LCEL Chain: prompt | llm | parser
6. 执行 Chain
7. 返回结果（字符串或结构化对象）
```

### 3. Pipeline（工作流）

**定义**：多个 Agent/Flow 的串联组合，形成多步骤业务流程。

**核心特性**：
- **步骤编排**：定义执行顺序和依赖关系
- **数据传递**：通过 `input_mapping` 定义数据流
- **变体管理**：支持 baseline 和多个 variants
- **依赖检测**：自动检测循环依赖

**配置示例**：
```yaml
id: "document_summary"
name: "文档摘要 Pipeline"

inputs:
  - name: "raw_text"
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
  steps:
    clean:
      flow: "clean_v1"
    summarize:
      flow: "summary_v1"

variants:
  improved_v1:
    overrides:
      summarize:
        flow: "summary_v2"
```

**执行流程**：
```
1. 加载 Pipeline 配置
2. 验证配置（循环依赖、引用完整性）
3. 加载测试集
4. 对于每个测试用例：
   a. 初始化上下文（包含测试用例数据）
   b. 按顺序执行每个步骤：
      - 根据 input_mapping 准备输入
      - 调用对应的 Agent/Flow
      - 将输出存储到上下文
   c. 收集所有步骤的输出
   d. 执行评估（如果配置）
5. 生成执行报告
```

### 4. Output Parser（输出解析器）

**定义**：将 LLM 的文本输出转换为结构化数据。

**支持的类型**：
- **JSON Parser**：解析为 Python 字典
- **Pydantic Parser**：解析为 Pydantic 模型（带验证）
- **List Parser**：解析逗号分隔的列表
- **None**：不解析，返回原始字符串（默认）

**工作原理**：
```
LLM 输出 (字符串)
    ↓
Parser 尝试解析
    ↓
成功？ ──Yes──→ 返回结构化对象
    ↓
   No
    ↓
启用重试？ ──No──→ 抛出异常或返回降级结果
    ↓
   Yes
    ↓
使用 OutputFixingParser 修复
    ↓
重新调用 LLM（带修复提示）
    ↓
解析成功？ ──Yes──→ 返回结构化对象
    ↓
   No
    ↓
达到最大重试次数？ ──Yes──→ 返回降级结果
    ↓
   No
    ↓
继续重试...
```

**实现细节**：
```python
# src/output_parser.py
class OutputParserFactory:
    @staticmethod
    def create_parser(config: OutputParserConfig) -> BaseOutputParser:
        if config.type == "json":
            return JsonOutputParser()
        elif config.type == "pydantic":
            return PydanticOutputParser(pydantic_object=config.pydantic_model)
        elif config.type == "list":
            return CommaSeparatedListOutputParser()
        else:
            return StrOutputParser()
    
    @staticmethod
    def create_retry_parser(parser, max_retries=3):
        return OutputFixingParser.from_llm(
            parser=parser,
            llm=ChatOpenAI(...),
            max_retries=max_retries
        )
```

### 5. 统一评估接口

**定义**：Agent 和 Pipeline 使用相同的评估机制。

**评估方式**：
1. **规则评估**：基于规则引擎的自动化检查
2. **Judge 评估**：使用 LLM 进行质量评估

**统一配置**：
```python
@dataclass
class EvaluationConfig:
    rules: List[RuleConfig]
    judge_enabled: bool
    judge_agent_id: Optional[str]
    judge_flow: Optional[str]
    scale_min: int
    scale_max: int
    
    @classmethod
    def from_agent_config(cls, agent: AgentConfig):
        # 从 Agent 配置创建
        pass
    
    @classmethod
    def from_pipeline_config(cls, pipeline: PipelineConfig):
        # 从 Pipeline 配置创建
        pass
```

**评估流程**：
```
输出结果
    ↓
规则评估
    ├─ Length Check
    ├─ Contains Check
    ├─ Regex Match
    └─ Custom Rules
    ↓
Judge 评估（如果启用）
    ├─ 调用 Judge Agent
    ├─ 使用 Output Parser 解析 Judge 输出
    └─ 提取评分和反馈
    ↓
生成评估结果
    ├─ overall_score
    ├─ must_have_pass
    ├─ rule_violations
    └─ judge_feedback
```

## 数据流

### Agent 执行数据流

```
测试集 (JSONL)
    ↓
加载测试用例
    ↓
对于每个测试用例：
    ├─ 填充 Prompt 模板
    ├─ 调用 LLM
    ├─ Output Parser 解析
    ├─ 规则评估
    ├─ Judge 评估
    └─ 保存结果
    ↓
生成评估报告 (CSV/JSON)
```

### Pipeline 执行数据流

```
测试集 (JSONL)
    ↓
加载测试用例
    ↓
对于每个测试用例：
    ├─ 初始化上下文
    ├─ 步骤 1：
    │   ├─ 映射输入
    │   ├─ 调用 Agent/Flow
    │   ├─ Output Parser 解析
    │   └─ 存储输出到上下文
    ├─ 步骤 2：
    │   ├─ 映射输入（可引用步骤 1 输出）
    │   ├─ 调用 Agent/Flow
    │   ├─ Output Parser 解析
    │   └─ 存储输出到上下文
    ├─ ...
    ├─ 步骤 N：
    │   └─ 同上
    ├─ 收集所有步骤输出
    ├─ 规则评估
    ├─ Judge 评估（传递所有步骤输出作为上下文）
    └─ 保存结果
    ↓
生成评估报告 (CSV/JSON)
```

## 与 LangChain 的关系

### LangChain 组件映射

| Prompt Lab 组件 | LangChain 组件 | 说明 |
|----------------|---------------|------|
| Flow | Chain (LCEL) | 单个可执行的 Chain |
| Pipeline | SequentialChain | 多步骤串联 |
| Flow Config | ChatPromptTemplate | 提示词模板 |
| Output Parser Config | OutputParser | 输出解析器 |
| Agent Execution | Chain.invoke() | 执行 Chain |

### LCEL 表达式

Prompt Lab 使用 LangChain Expression Language (LCEL) 构建 Chain：

```python
# 基础 Chain（无 Output Parser）
chain = prompt | llm

# 带 Output Parser 的 Chain
chain = prompt | llm | parser

# 带重试的 Chain
chain = prompt | llm | retry_parser
```

### 扩展 LangChain

Prompt Lab 在 LangChain 基础上增加了：
1. **配置化**：通过 YAML 配置 Chain，无需编写代码
2. **版本管理**：支持多个 Flow 版本和对比
3. **评估体系**：内置规则评估和 Judge 评估
4. **Pipeline 编排**：多步骤工作流和变体管理
5. **回归测试**：基线管理和自动化回归检测

## 错误处理

### Output Parser 错误处理

```python
try:
    # 尝试解析
    result = parser.parse(llm_output)
except OutputParserException as e:
    if retry_enabled and retry_count < max_retries:
        # 使用 OutputFixingParser 重试
        fixing_parser = OutputFixingParser.from_llm(
            parser=parser,
            llm=llm
        )
        result = fixing_parser.parse(llm_output)
    else:
        # 降级处理
        result = create_fallback_result(llm_output, error=e)
```

### Pipeline 错误处理

```python
for step in pipeline.steps:
    try:
        # 执行步骤
        output = execute_step(step, context)
        context[step.output_key] = output
    except Exception as e:
        # 记录错误
        log_step_error(step, e)
        
        # 决定是否继续
        if step.required:
            # 关键步骤失败，停止执行
            raise PipelineExecutionError(f"Step {step.id} failed")
        else:
            # 可选步骤失败，继续执行
            context[step.output_key] = None
            continue
```

## 性能监控

### 监控指标

1. **执行时间**：
   - 每个步骤的执行时间
   - 总执行时间
   - LLM 调用时间

2. **Token 使用量**：
   - 输入 tokens
   - 输出 tokens
   - 总 tokens
   - 成本估算

3. **Output Parser 统计**：
   - 解析成功次数
   - 解析失败次数
   - 重试次数
   - 成功率

4. **评估指标**：
   - 规则通过率
   - Judge 平均分
   - Must-have 通过率

### 性能优化建议

1. **减少 LLM 调用**：
   - 优化 Prompt 减少解析失败
   - 合理设置重试次数
   - 使用缓存避免重复调用

2. **并行执行**（未来）：
   - 识别独立步骤
   - 并行执行无依赖步骤
   - 异步 LLM 调用

3. **模型选择**：
   - 简单任务使用小模型
   - 复杂任务使用大模型
   - 根据成本和性能权衡

## 扩展机制

### 添加新的 Output Parser 类型

```python
# 1. 创建自定义 Parser
class CustomOutputParser(BaseOutputParser):
    def parse(self, text: str) -> Any:
        # 自定义解析逻辑
        pass

# 2. 在 OutputParserFactory 中注册
class OutputParserFactory:
    @staticmethod
    def create_parser(config: OutputParserConfig):
        if config.type == "custom":
            return CustomOutputParser()
        # ...
```

### 添加新的评估规则

```python
# 1. 在 RuleEngine 中添加规则类型
class RuleEngine:
    def evaluate_custom_rule(self, output, rule_config):
        # 自定义规则逻辑
        pass
    
    def evaluate(self, output, rules):
        for rule in rules:
            if rule.type == "custom":
                self.evaluate_custom_rule(output, rule)
            # ...
```

### 添加新的 Pipeline 步骤类型

```python
# 1. 定义新的步骤类型
class CustomStepExecutor:
    def execute(self, step_config, context):
        # 自定义步骤执行逻辑
        pass

# 2. 在 PipelineRunner 中注册
class PipelineRunner:
    def execute_step(self, step, context):
        if step.type == "custom":
            executor = CustomStepExecutor()
            return executor.execute(step, context)
        # ...
```

## 安全考虑

### API Key 安全

- 使用 `.env` 文件存储敏感信息
- 不要将 API Key 硬编码
- 不要提交 `.env` 到版本控制

### 输入验证

- 验证所有用户输入
- 防止 YAML 注入
- 限制文件大小和复杂度

### 输出安全

- 不在日志中输出敏感信息
- 对 LLM 输出进行清理
- 防止 Prompt 注入攻击

## 最佳实践

### Agent 设计

1. **单一职责**：每个 Agent 只做一件事
2. **清晰的输入输出**：明确定义 case_fields
3. **完善的测试集**：覆盖各种场景
4. **合理的评估标准**：规则 + Judge 结合

### Flow 设计

1. **清晰的 Prompt**：明确说明任务和输出格式
2. **合理的默认值**：为可选字段提供默认值
3. **Output Parser 配置**：结构化输出使用 Parser
4. **版本管理**：保留历史版本，便于回滚

### Pipeline 设计

1. **步骤粒度**：每个步骤有明确的职责
2. **数据流清晰**：input_mapping 明确定义
3. **错误处理**：区分关键步骤和可选步骤
4. **变体管理**：baseline 稳定，variants 实验

## 相关文档

- [架构分析文档](ARCHITECTURE_ANALYSIS.md) - 与 LangChain 生态的对比
- [Pipeline 配置指南](reference/pipeline-guide.md) - Pipeline 详细配置
- [Output Parser 使用指南](../OUTPUT_PARSER_USAGE.md) - Output Parser 配置和使用
- [评估模式指南](reference/eval-modes-guide.md) - 评估系统详解
