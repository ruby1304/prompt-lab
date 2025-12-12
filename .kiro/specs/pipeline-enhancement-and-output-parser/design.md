# Design Document

## Overview

本设计文档描述了 Prompt Lab 的两个关键增强功能的技术实现方案：

1. **Pipeline 功能完善与示例补充**：通过提供完整的示例配置、文档和演示脚本，降低 Pipeline 功能的学习曲线，使用户能够快速上手多步骤工作流。

2. **Output Parser 实现**：引入 LangChain 的 Output Parser 机制，提升结构化输出的可靠性，特别是改进 Judge Agent 的 JSON 输出解析，减少评估失败率。

### 设计目标

- **快速上手**：用户能在 5 分钟内运行第一个 Pipeline
- **架构统一**：Agent 和 Pipeline 使用相同的评估接口和配置方式
- **可靠输出**：通过 Output Parser 确保结构化输出的正确性
- **LangChain 原生**：充分利用 LangChain 的设计模式和组件
- **向后兼容**：不破坏现有功能，平滑升级

## Architecture

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                     Prompt Lab 架构                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌──────────────┐                    │
│  │   Agent      │      │   Pipeline   │                    │
│  │  (业务单元)   │      │  (工作流)     │                    │
│  └──────┬───────┘      └──────┬───────┘                    │
│         │                     │                             │
│         ├─ Flow v1            ├─ Step 1: Agent A + Flow v1 │
│         ├─ Flow v2            ├─ Step 2: Agent B + Flow v2 │
│         └─ Flow v3            └─ Step 3: Agent C + Flow v1 │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                    执行层 (Execution Layer)                  │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Flow Executor (chains.py)                         │    │
│  │  ┌──────────────────────────────────────────┐     │    │
│  │  │  ChatPromptTemplate                       │     │    │
│  │  │         ↓                                 │     │    │
│  │  │  ChatOpenAI (LLM)                        │     │    │
│  │  │         ↓                                 │     │    │
│  │  │  Output Parser (NEW!)  ←─────────────┐  │     │    │
│  │  │    - JSON Parser                      │  │     │    │
│  │  │    - Pydantic Parser                  │  │     │    │
│  │  │    - Retry Logic                      │  │     │    │
│  │  └──────────────────────────────────────────┘     │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  Pipeline Runner (pipeline_runner.py)              │    │
│  │  - 步骤编排                                         │    │
│  │  - 数据传递                                         │    │
│  │  - 错误处理                                         │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                    评估层 (Evaluation Layer)                │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  统一评估接口 (Unified Evaluation Interface)        │    │
│  │  ┌──────────────┐      ┌──────────────┐           │    │
│  │  │ Agent Eval   │      │ Pipeline Eval│           │    │
│  │  │              │      │              │           │    │
│  │  │ - Rules      │      │ - Rules      │           │    │
│  │  │ - Judge      │      │ - Judge      │           │    │
│  │  │ - Metrics    │      │ - Metrics    │           │    │
│  │  └──────────────┘      └──────────────┘           │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```


## Components and Interfaces

### 1. Output Parser 组件

#### 1.1 OutputParserConfig (新增数据模型)

```python
@dataclass
class OutputParserConfig:
    """Output Parser 配置"""
    type: str  # "json" | "pydantic" | "list" | "none"
    schema: Optional[Dict[str, Any]] = None  # JSON schema
    pydantic_model: Optional[str] = None  # Pydantic 模型类名
    retry_on_error: bool = True
    max_retries: int = 3
    fix_prompt: Optional[str] = None  # 修复提示词
```

#### 1.2 OutputParserFactory (新增工厂类)

```python
class OutputParserFactory:
    """Output Parser 工厂，根据配置创建相应的 parser"""
    
    @staticmethod
    def create_parser(config: OutputParserConfig) -> BaseOutputParser:
        """
        根据配置创建 Output Parser
        
        支持的类型：
        - json: JsonOutputParser (LangChain)
        - pydantic: PydanticOutputParser (LangChain)
        - list: CommaSeparatedListOutputParser (LangChain)
        - none: StrOutputParser (默认)
        """
        pass
    
    @staticmethod
    def create_retry_parser(
        parser: BaseOutputParser,
        max_retries: int = 3
    ) -> OutputFixingParser:
        """创建带重试的 parser"""
        pass
```

#### 1.3 chains.py 增强

```python
def build_chain_with_parser(
    prompt: ChatPromptTemplate,
    flow_cfg: Mapping[str, Any],
    model_override: str = None
) -> RunnableSerializable:
    """
    构建带 Output Parser 的 Chain
    
    Chain 结构：
    prompt | llm | output_parser
    
    如果配置了 retry，则：
    prompt | llm | retry_parser
    """
    llm = ChatOpenAI(...)
    
    # 检查是否配置了 output_parser
    parser_config = flow_cfg.get("output_parser")
    if parser_config:
        parser = OutputParserFactory.create_parser(parser_config)
        if parser_config.get("retry_on_error"):
            parser = OutputParserFactory.create_retry_parser(
                parser, 
                max_retries=parser_config.get("max_retries", 3)
            )
        return prompt | llm | parser
    else:
        # 向后兼容：返回字符串
        return prompt | llm
```

### 2. Pipeline 示例配置

#### 2.1 简单示例：文档处理 Pipeline

```yaml
# pipelines/document_summary.yaml
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

#### 2.2 复杂示例：客服流程 Pipeline

```yaml
# pipelines/customer_service_flow.yaml
id: "customer_service_flow"
name: "客服处理流程"
description: "自动化客服请求处理"

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
```

### 3. 统一评估接口

#### 3.1 EvaluationConfig (统一配置)

```python
@dataclass
class EvaluationConfig:
    """统一的评估配置，适用于 Agent 和 Pipeline"""
    
    # 规则评估
    rules: List[RuleConfig] = field(default_factory=list)
    
    # Judge 评估
    judge_enabled: bool = False
    judge_agent_id: Optional[str] = None
    judge_flow: Optional[str] = None
    judge_model: Optional[str] = None
    
    # 评分范围
    scale_min: int = 0
    scale_max: int = 10
    
    # 字段配置
    case_fields: List[CaseFieldConfig] = field(default_factory=list)
    
    @classmethod
    def from_agent_config(cls, agent: AgentConfig) -> 'EvaluationConfig':
        """从 Agent 配置创建评估配置"""
        pass
    
    @classmethod
    def from_pipeline_config(cls, pipeline: PipelineConfig) -> 'EvaluationConfig':
        """从 Pipeline 配置创建评估配置"""
        pass
```

#### 3.2 UnifiedEvaluator (统一评估器)

```python
class UnifiedEvaluator:
    """统一的评估器，处理 Agent 和 Pipeline 评估"""
    
    def __init__(self, config: EvaluationConfig):
        self.config = config
        self.rule_engine = RuleEngine(config.rules)
        if config.judge_enabled:
            self.judge = JudgeEvaluator(
                agent_id=config.judge_agent_id,
                flow=config.judge_flow,
                model=config.judge_model
            )
    
    def evaluate_agent_output(
        self,
        agent_id: str,
        flow_name: str,
        test_case: Dict[str, Any],
        output: str
    ) -> EvaluationResult:
        """评估 Agent 输出"""
        pass
    
    def evaluate_pipeline_output(
        self,
        pipeline_id: str,
        variant: str,
        test_case: Dict[str, Any],
        step_outputs: Dict[str, Any],
        final_output: str
    ) -> EvaluationResult:
        """评估 Pipeline 输出"""
        pass
```


## Data Models

### 1. Flow 配置扩展

```yaml
# agents/{agent_id}/prompts/{flow_name}.yaml
name: "flow_name"
description: "Flow 描述"

system_prompt: |
  你的系统提示词...

user_template: |
  你的用户模板...

defaults:
  field1: "default_value"

# 新增：Output Parser 配置
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

### 2. Judge Flow 配置示例

```yaml
# agents/judge_default/prompts/judge_v2.yaml
name: "judge_v2"
description: "带 Output Parser 的 Judge"

system_prompt: |
  你是评估助手，输出 JSON 格式...

user_template: |
  评估以下输出...

# 配置 JSON Output Parser
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
      overall_comment:
        type: "string"
    required: ["overall_score", "must_have_check", "overall_comment"]
  retry_on_error: true
  max_retries: 3
  fix_prompt: |
    上一次输出格式不正确，请严格按照 JSON schema 输出。
```

### 3. Pipeline 测试集格式

```jsonl
{"id": 1, "raw_text": "这是一篇很长的文档...", "expected_summary": "简短摘要", "tags": ["happy_path"]}
{"id": 2, "raw_text": "包含特殊字符的文档...", "expected_summary": "处理特殊字符", "tags": ["edge_case"]}
{"id": 3, "user_message": "我要退款", "conversation_history": [...], "tags": ["customer_service", "refund"]}
```

### 4. 评估结果格式（统一）

```python
@dataclass
class EvaluationResult:
    """统一的评估结果格式"""
    sample_id: str
    entity_type: str  # "agent" | "pipeline"
    entity_id: str  # agent_id 或 pipeline_id
    variant: str  # flow_name 或 variant_name
    
    # 输出
    output: str  # 最终输出
    step_outputs: Dict[str, Any] = field(default_factory=dict)  # Pipeline 专用
    
    # 评估结果
    overall_score: float
    must_have_pass: bool
    rule_violations: List[str] = field(default_factory=list)
    judge_feedback: str = ""
    
    # 元数据
    execution_time: float = 0.0
    token_usage: Dict[str, int] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
```

## Error Handling

### 1. Output Parser 错误处理

```python
class OutputParserErrorHandler:
    """Output Parser 错误处理器"""
    
    def handle_parse_error(
        self,
        error: Exception,
        raw_output: str,
        parser: BaseOutputParser,
        retry_count: int
    ) -> Optional[Any]:
        """
        处理解析错误
        
        策略：
        1. 如果是 JSON 格式错误，尝试修复常见问题
        2. 如果是字段缺失，使用默认值填充
        3. 如果重试次数未达上限，重新调用 LLM
        4. 如果所有尝试失败，返回降级结果
        """
        if retry_count < max_retries:
            # 使用 OutputFixingParser 重试
            fixing_parser = OutputFixingParser.from_llm(
                parser=parser,
                llm=ChatOpenAI(...)
            )
            return fixing_parser.parse(raw_output)
        else:
            # 降级处理
            return self._create_fallback_result(raw_output)
    
    def _create_fallback_result(self, raw_output: str) -> Dict[str, Any]:
        """创建降级结果"""
        return {
            "overall_score": 5.0,  # 中等分数
            "must_have_check": [],
            "overall_comment": f"解析失败，原始输出：{raw_output[:100]}...",
            "parse_error": True
        }
```

### 2. Pipeline 执行错误处理

```python
class PipelineErrorHandler:
    """Pipeline 执行错误处理器"""
    
    def handle_step_error(
        self,
        step: StepConfig,
        error: Exception,
        context: Dict[str, Any]
    ) -> StepResult:
        """
        处理步骤执行错误
        
        策略：
        1. 记录错误详情
        2. 标记步骤失败
        3. 决定是否继续执行后续步骤
        """
        logger.error(f"步骤 {step.id} 执行失败: {error}")
        
        return StepResult(
            step_id=step.id,
            success=False,
            output=None,
            error=str(error),
            execution_time=0.0
        )
    
    def should_continue(
        self,
        failed_step: StepConfig,
        pipeline: PipelineConfig
    ) -> bool:
        """判断是否应该继续执行"""
        # 如果是关键步骤，停止执行
        # 如果是可选步骤，继续执行
        return not failed_step.required
```

## Testing Strategy

### 1. 单元测试

#### 1.1 Output Parser 测试

```python
# tests/test_output_parser.py

def test_json_parser_success():
    """测试 JSON parser 成功解析"""
    parser = JsonOutputParser()
    output = '{"score": 8, "comment": "Good"}'
    result = parser.parse(output)
    assert result["score"] == 8
    assert result["comment"] == "Good"

def test_json_parser_with_retry():
    """测试 JSON parser 重试机制"""
    parser = create_retry_parser(JsonOutputParser(), max_retries=3)
    # 模拟格式错误的输出
    output = '{"score": 8, "comment": "Good"'  # 缺少右括号
    result = parser.parse(output)
    # 应该通过重试修复
    assert "score" in result

def test_pydantic_parser():
    """测试 Pydantic parser"""
    class JudgeOutput(BaseModel):
        overall_score: float
        must_have_check: List[Dict[str, Any]]
        overall_comment: str
    
    parser = PydanticOutputParser(pydantic_object=JudgeOutput)
    output = '{"overall_score": 8.5, "must_have_check": [], "overall_comment": "Good"}'
    result = parser.parse(output)
    assert isinstance(result, JudgeOutput)
    assert result.overall_score == 8.5
```

#### 1.2 统一评估接口测试

```python
# tests/test_unified_evaluator.py

def test_agent_evaluation():
    """测试 Agent 评估"""
    config = EvaluationConfig.from_agent_config(agent)
    evaluator = UnifiedEvaluator(config)
    
    result = evaluator.evaluate_agent_output(
        agent_id="test_agent",
        flow_name="test_flow",
        test_case={"input": "test"},
        output="test output"
    )
    
    assert result.entity_type == "agent"
    assert result.overall_score >= 0

def test_pipeline_evaluation():
    """测试 Pipeline 评估"""
    config = EvaluationConfig.from_pipeline_config(pipeline)
    evaluator = UnifiedEvaluator(config)
    
    result = evaluator.evaluate_pipeline_output(
        pipeline_id="test_pipeline",
        variant="baseline",
        test_case={"input": "test"},
        step_outputs={"step1": "output1", "step2": "output2"},
        final_output="final output"
    )
    
    assert result.entity_type == "pipeline"
    assert len(result.step_outputs) == 2
```

### 2. 集成测试（真实 LLM 调用）

```python
# tests/test_integration_real_llm.py

@pytest.mark.integration
def test_judge_with_output_parser():
    """测试 Judge Agent 使用 Output Parser（真实调用）"""
    # 使用 .env 中的真实 API Key
    load_dotenv()
    
    # 执行真实的 Judge 评估
    result = run_flow(
        flow_name="judge_v2",
        agent_id="judge_default",
        extra_vars={
            "agent_id": "test_agent",
            "output": "测试输出",
            # ... 其他参数
        }
    )
    
    # 验证返回的是结构化对象，不是字符串
    assert isinstance(result, dict)
    assert "overall_score" in result
    assert isinstance(result["overall_score"], (int, float))

@pytest.mark.integration
def test_pipeline_execution():
    """测试 Pipeline 完整执行（真实调用）"""
    load_dotenv()
    
    pipeline = load_pipeline_config("document_summary")
    runner = PipelineRunner(pipeline)
    
    test_case = {"raw_text": "这是一篇测试文档..."}
    result = runner.run(test_case, variant="baseline")
    
    # 验证所有步骤都执行成功
    assert result.success
    assert "cleaned_text" in result.step_outputs
    assert "summary" in result.step_outputs
```

### 3. 端到端测试

```python
# tests/test_e2e_pipeline.py

@pytest.mark.e2e
def test_pipeline_with_evaluation():
    """端到端测试：Pipeline 执行 + 评估"""
    # 1. 加载 Pipeline
    pipeline = load_pipeline_config("customer_service_flow")
    
    # 2. 执行 Pipeline
    runner = PipelineRunner(pipeline)
    test_case = {
        "user_message": "我要退款",
        "conversation_history": []
    }
    result = runner.run(test_case, variant="baseline")
    
    # 3. 评估结果
    evaluator = UnifiedEvaluator(
        EvaluationConfig.from_pipeline_config(pipeline)
    )
    eval_result = evaluator.evaluate_pipeline_output(
        pipeline_id=pipeline.id,
        variant="baseline",
        test_case=test_case,
        step_outputs=result.step_outputs,
        final_output=result.final_output
    )
    
    # 4. 验证评估结果
    assert eval_result.overall_score > 0
    assert eval_result.must_have_pass is not None
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Output Parser 类型正确性
*For any* Flow 配置了 output_parser，当执行该 Flow 时，返回的类型应该与配置的 parser 类型匹配（JSON parser 返回 dict，Pydantic parser 返回 Pydantic 对象，未配置返回 str）
**Validates: Requirements 4.5, 5.5**

### Property 2: JSON 解析幂等性
*For any* 有效的 JSON 字符串，使用 JSON Output Parser 解析后再序列化，应该得到等价的 JSON 对象
**Validates: Requirements 4.2**

### Property 3: Pydantic 验证严格性
*For any* 配置了 Pydantic parser 的 Flow，当 LLM 输出不符合 schema 时，parser 应该抛出验证错误或触发重试
**Validates: Requirements 4.3, 5.2**

### Property 4: 重试次数限制
*For any* 配置了 `max_retries=N` 的 parser，当解析持续失败时，系统应该最多重试 N 次，然后返回降级结果
**Validates: Requirements 4.4, 5.4, 6.2**

### Property 5: Judge 输出必需字段完整性
*For any* Judge Agent 的输出，解析后的结果应该包含 `overall_score`, `must_have_check`, `overall_comment` 这三个必需字段
**Validates: Requirements 6.4**

### Property 6: 评估配置结构一致性
*For any* Agent 或 Pipeline 配置，通过 `EvaluationConfig.from_agent_config()` 或 `EvaluationConfig.from_pipeline_config()` 创建的评估配置应该具有相同的字段结构
**Validates: Requirements 7.1**

### Property 7: 规则评估一致性
*For any* 相同的规则配置和输出，在 Agent 评估和 Pipeline 评估中应该产生相同的规则违规结果
**Validates: Requirements 7.2**

### Property 8: Pipeline 步骤输出完整性
*For any* 成功执行的 Pipeline，评估结果应该包含所有步骤的输出，且步骤数量应该等于 Pipeline 配置中的步骤数量
**Validates: Requirements 8.1, 8.4**

### Property 9: Pipeline 步骤失败传播
*For any* Pipeline 执行，如果某个步骤失败，后续依赖该步骤输出的步骤应该被跳过，且失败原因应该被记录
**Validates: Requirements 8.5**

### Property 10: 配置引用完整性
*For any* Pipeline 配置，所有引用的 Agent 和 Flow 应该在系统中存在，否则配置验证应该失败并提供可用选项列表
**Validates: Requirements 1.4, 11.2**

### Property 11: 循环依赖检测
*For any* Pipeline 配置，如果步骤间存在循环依赖（A 依赖 B，B 依赖 A），配置验证应该检测出来并拒绝加载
**Validates: Requirements 11.4**

### Property 12: 向后兼容性保证
*For any* 未配置 output_parser 的旧 Flow 配置，执行后应该返回字符串类型的输出，行为与引入 Output Parser 之前完全一致
**Validates: Requirements 14.1, 14.5**

### Property 13: 性能监控数据完整性
*For any* Pipeline 执行，性能摘要应该包含总执行时间、每个步骤的执行时间、token 使用量（输入、输出、总计）
**Validates: Requirements 12.1, 12.3, 12.4**

### Property 14: 示例配置可执行性
*For any* 提供的示例 Pipeline 配置，应该能够成功加载、验证并执行（使用示例测试集）
**Validates: Requirements 1.1, 1.2, 1.3**

### Property 15: 错误信息有用性
*For any* 配置验证失败或执行错误，错误信息应该包含：错误位置、具体原因、修复建议（至少包含其中两项）
**Validates: Requirements 6.5, 11.5**


## Implementation Plan

### Phase 1: Output Parser 基础设施（优先级最高）

#### 1.1 创建 Output Parser 数据模型和工厂类
- 在 `src/models.py` 中添加 `OutputParserConfig`
- 创建 `src/output_parser.py` 包含 `OutputParserFactory`
- 实现 JSON, Pydantic, List parser 的创建逻辑
- 实现重试机制（使用 LangChain 的 `OutputFixingParser`）

#### 1.2 增强 chains.py 支持 Output Parser
- 修改 `build_chain()` 函数支持 output_parser 配置
- 修改 `run_flow()` 和 `run_flow_with_tokens()` 返回结构化对象
- 确保向后兼容（未配置 parser 时返回字符串）

#### 1.3 更新 Judge Agent 配置
- 为 `judge_v1.yaml` 和 `judge_v2.yaml` 添加 output_parser 配置
- 定义 Judge 输出的 JSON schema
- 配置重试策略（max_retries=3）

#### 1.4 单元测试
- 测试 OutputParserFactory 创建各种 parser
- 测试 JSON parser 解析成功和失败场景
- 测试 Pydantic parser 验证
- 测试重试机制
- 测试向后兼容性

### Phase 2: Pipeline 示例和文档

#### 2.1 创建 Pipeline 示例配置
- 创建 `pipelines/document_summary.yaml`（简单示例）
- 创建 `pipelines/customer_service_flow.yaml`（复杂示例）
- 为每个示例创建对应的测试集（至少 5 个用例）

#### 2.2 创建或复用示例所需的 Agent
- 如果需要，创建 `text_cleaner`, `summarizer` 等 Agent
- 或者使用现有的 Agent（如 `mem0_l1_summarizer`）
- 确保所有引用的 Agent 和 Flow 都存在

#### 2.3 更新文档
- 在 README.md 的"快速开始"章节添加 Pipeline 示例
- 更新 `docs/reference/pipeline-guide.md` 添加详细说明
- 创建 `examples/pipeline_demo.py` 演示脚本

#### 2.4 集成测试
- 测试示例 Pipeline 能够成功加载
- 测试示例 Pipeline 能够成功执行（真实 LLM 调用）
- 验证输出格式和内容

### Phase 3: 统一评估接口

#### 3.1 创建统一评估配置
- 在 `src/models.py` 中添加 `EvaluationConfig`
- 实现 `from_agent_config()` 和 `from_pipeline_config()` 方法
- 确保两种配置能够转换为统一格式

#### 3.2 实现统一评估器
- 创建 `src/unified_evaluator.py`
- 实现 `UnifiedEvaluator` 类
- 实现 `evaluate_agent_output()` 和 `evaluate_pipeline_output()` 方法
- 确保两种评估使用相同的规则引擎和 Judge

#### 3.3 更新现有评估代码
- 重构 `src/eval_llm_judge.py` 使用新的 Output Parser
- 重构 `src/pipeline_eval.py` 使用统一评估接口
- 确保向后兼容

#### 3.4 单元测试
- 测试 EvaluationConfig 的创建和转换
- 测试 UnifiedEvaluator 的 Agent 评估
- 测试 UnifiedEvaluator 的 Pipeline 评估
- 测试评估结果格式一致性

### Phase 4: 错误处理和监控

#### 4.1 实现错误处理器
- 创建 `src/output_parser_error_handler.py`
- 实现解析错误的降级处理
- 创建 `src/pipeline_error_handler.py`
- 实现步骤失败的错误处理

#### 4.2 添加性能监控
- 在 Pipeline 执行中记录每个步骤的执行时间
- 记录 Output Parser 的解析成功率和重试次数
- 记录 token 使用量
- 生成性能摘要

#### 4.3 改进错误信息
- 为配置验证错误提供详细的错误位置和修复建议
- 为执行错误提供上下文信息和调试建议
- 为 API 调用失败提供清晰的错误信息

#### 4.4 单元测试
- 测试各种错误场景的处理
- 测试降级处理的正确性
- 测试性能监控数据的完整性

### Phase 5: 集成测试和文档完善

#### 5.1 端到端集成测试
- 测试 Pipeline 完整执行流程（真实 LLM 调用）
- 测试 Judge Agent 使用 Output Parser（真实调用）
- 测试 Pipeline 评估流程
- 测试错误处理和降级

#### 5.2 性能测试
- 测试大规模测试集的处理
- 测试 Pipeline 的执行效率
- 测试 Output Parser 的性能影响

#### 5.3 文档完善
- 完善 README.md 的所有相关章节
- 更新所有相关的参考文档
- 添加 API 文档和使用示例
- 更新故障排除指南

#### 5.4 向后兼容性测试
- 运行现有的所有测试，确保通过
- 测试旧的配置文件能够正常工作
- 测试旧的 API 调用能够正常工作

## Migration Guide

### 为现有 Flow 添加 Output Parser

```yaml
# 在现有的 Flow 配置中添加 output_parser 节
output_parser:
  type: "json"
  schema:
    type: "object"
    properties:
      # 定义你的输出结构
      result: {type: "string"}
  retry_on_error: true
  max_retries: 3
```

### 从旧的评估代码迁移到统一接口

```python
# 旧代码
from src.eval_llm_judge import evaluate_with_judge

result = evaluate_with_judge(agent_id, flow_name, test_case, output)

# 新代码
from src.unified_evaluator import UnifiedEvaluator, EvaluationConfig
from src.agent_registry import load_agent

agent = load_agent(agent_id)
config = EvaluationConfig.from_agent_config(agent)
evaluator = UnifiedEvaluator(config)

result = evaluator.evaluate_agent_output(
    agent_id=agent_id,
    flow_name=flow_name,
    test_case=test_case,
    output=output
)
```

### 创建新的 Pipeline

1. 复制示例配置：
```bash
cp pipelines/document_summary.yaml pipelines/my_pipeline.yaml
```

2. 修改配置：
- 更新 id, name, description
- 定义 inputs 和 outputs
- 配置 steps（agent, flow, input_mapping）
- 定义 baseline 和 variants

3. 创建测试集：
```bash
mkdir -p data/pipelines/my_pipeline/testsets
# 创建 testset.jsonl
```

4. 测试运行：
```bash
python -m src eval --pipeline my_pipeline --variants baseline --limit 3
```

## Performance Considerations

### Output Parser 性能影响

- **JSON Parser**: 几乎无性能影响（纯 Python JSON 解析）
- **Pydantic Parser**: 轻微性能影响（需要验证）
- **Retry Parser**: 显著性能影响（需要额外的 LLM 调用）

**优化建议**：
- 优先使用 JSON Parser（最快）
- 只在需要严格验证时使用 Pydantic Parser
- 合理设置 max_retries（建议 2-3 次）
- 优化 prompt 减少解析失败率

### Pipeline 执行性能

- **串行执行**: 当前实现，步骤按顺序执行
- **并行执行**: 未来优化，独立步骤可以并行

**优化建议**：
- 减少不必要的步骤
- 优化每个步骤的 prompt 和模型选择
- 使用缓存避免重复计算
- 考虑异步执行（未来）

## Security Considerations

### API Key 安全

- 使用 `.env` 文件存储 API Key
- 不要将 API Key 硬编码在代码中
- 不要将 `.env` 文件提交到版本控制

### 输入验证

- 验证所有用户输入（配置文件、测试集）
- 防止 YAML 注入攻击
- 限制文件大小和复杂度

### 输出安全

- 不要在日志中输出敏感信息
- 对 LLM 输出进行适当的清理
- 防止 prompt 注入攻击

## Future Enhancements

### 短期（1-2 个月）

1. **Memory 系统**: 支持多轮对话和状态管理
2. **Streaming 输出**: 支持流式输出和实时反馈
3. **并行执行**: Pipeline 步骤的并行执行

### 中期（3-6 个月）

4. **Tools 集成**: 支持函数调用和外部系统集成
5. **Retriever**: 支持 RAG（检索增强生成）
6. **Router**: 支持条件分支和动态路由

### 长期（6-12 个月）

7. **Autonomous Agents**: 实现真正的自主决策 Agent
8. **可视化编辑器**: Pipeline 的图形化配置界面
9. **分布式执行**: 支持分布式 Pipeline 执行

## References

- [LangChain Output Parsers](https://python.langchain.com/docs/modules/model_io/output_parsers/)
- [LangChain Expression Language (LCEL)](https://python.langchain.com/docs/expression_language/)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [JSON Schema](https://json-schema.org/)
