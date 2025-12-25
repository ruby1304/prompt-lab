# Prompt Lab v0.8 统一设计文档

## Overview

本设计文档整合了 Prompt Lab 项目的所有核心功能模块的技术方案。

## Architecture

### 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                         │
│  REST API / OpenAPI / WebSocket                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      配置管理层                                   │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐     │
│  │Agent Registry│    │Pipeline Config│   │Testset Manager│     │
│  │              │    │              │    │              │     │
│  │- 统一注册    │    │- 代码节点    │    │- 批量测试    │     │
│  │- 元数据管理  │    │- 并发配置    │    │- 多阶段测试  │     │
│  │- 热重载      │    │- 批量处理    │    │- 聚合评估    │     │
│  └──────────────┘    └──────────────┘    └──────────────┘     │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      执行引擎层                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Pipeline Runner                                        │    │
│  │  - 依赖分析 (DependencyAnalyzer)                        │    │
│  │  - 并发调度 (ConcurrentExecutor)                        │    │
│  │  - 代码节点执行 (CodeExecutor)                          │    │
│  │  - 批量聚合 (BatchAggregator)                           │    │
│  └────────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Evaluation Engine                                      │    │
│  │  - 规则评估 (RuleEngine)                                │    │
│  │  - LLM Judge 评估                                       │    │
│  │  - 回归测试 (RegressionTester)                          │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### 项目目录结构

```
prompt-lab/
├── README.md                     # 主文档
├── pyproject.toml                # 项目配置
├── requirements.txt              # Python 依赖
│
├── agents/                       # 生产 Agent
│   ├── _template/                # Agent 模板
│   ├── judge_default/            # 系统 Judge Agent
│   └── [其他生产 Agent]
│
├── pipelines/                    # Pipeline 配置
│
├── config/                       # 配置文件
│   ├── agent_registry.yaml       # Agent Registry
│   └── schemas/                  # JSON Schema
│
├── data/                         # 运行时数据
│   ├── agents/                   # Agent 数据
│   ├── pipelines/                # Pipeline 数据
│   └── baselines/                # 基线数据
│
├── docs/                         # 文档
│   ├── README.md                 # 文档导航
│   ├── guides/                   # 使用指南
│   ├── reference/                # 参考文档
│   └── archive/                  # 归档文档
│
├── examples/                     # 示例
│
├── src/                          # 源代码
│   ├── agent_registry.py         # Agent Registry
│   ├── agent_registry_v2.py      # Agent Registry v2
│   ├── pipeline_runner.py        # Pipeline 执行器
│   ├── pipeline_config.py        # Pipeline 配置
│   ├── code_executor.py          # 代码节点执行器
│   ├── concurrent_executor.py    # 并发执行器
│   ├── dependency_analyzer.py    # 依赖分析器
│   ├── batch_aggregator.py       # 批量聚合器
│   ├── unified_evaluator.py      # 统一评估器
│   ├── regression_tester.py      # 回归测试器
│   ├── baseline_manager.py       # 基线管理器
│   ├── testset_loader.py         # 测试集加载器
│   ├── output_parser.py          # 输出解析器
│   ├── progress_tracker.py       # 进度跟踪器
│   ├── api/                      # API 层
│   └── agent_template_parser/    # 模板解析器
│
├── scripts/                      # 工具脚本
│
└── tests/                        # 测试代码
```

## Components and Interfaces

### 1. Agent Registry System

```python
class AgentRegistry:
    def load_registry(self) -> Dict[str, AgentMetadata]
    def reload_registry(self) -> None  # 热重载
    def get_agent(self, agent_id: str) -> AgentMetadata
    def list_agents(self, category=None, tags=None) -> List[AgentMetadata]
    def register_agent(self, agent_id: str, metadata: AgentMetadata) -> None
    def sync_from_filesystem(self) -> SyncResult
```

### 2. Pipeline Runner

```python
class PipelineRunner:
    def execute(self, pipeline_config: PipelineConfig, inputs: Dict) -> PipelineResult
    def execute_step(self, step: StepConfig, context: Dict) -> StepResult
```

### 3. Code Executor

```python
class CodeExecutor:
    def execute_javascript(self, code: str, inputs: Dict, timeout: int) -> ExecutionResult
    def execute_python(self, code: str, inputs: Dict, timeout: int) -> ExecutionResult
```

### 4. Concurrent Executor

```python
class ConcurrentExecutor:
    def execute_concurrent(self, tasks: List[Task], max_workers: int) -> List[TaskResult]

class DependencyAnalyzer:
    def analyze_dependencies(self, steps: List[StepConfig]) -> DependencyGraph
    def find_concurrent_groups(self, graph: DependencyGraph) -> List[List[str]]
```

### 5. Batch Aggregator

```python
class BatchAggregator:
    def aggregate_concat(self, items: List[Any], separator: str) -> str
    def aggregate_stats(self, items: List[Any], fields: List[str]) -> Dict
    def aggregate_filter(self, items: List[Any], condition: Callable) -> List[Any]
    def aggregate_custom(self, items: List[Any], code: str) -> Any
```

### 6. Unified Evaluator

```python
class UnifiedEvaluator:
    def evaluate_agent_output(self, output: str, expected: str, config: EvaluationConfig) -> EvaluationResult
    def evaluate_pipeline_output(self, result: PipelineResult, config: EvaluationConfig) -> EvaluationResult
```

### 7. API Layer

```
GET  /agents                    # 列出 Agent
GET  /agents/{id}               # 获取 Agent 详情
POST /agents                    # 注册 Agent
PUT  /agents/{id}               # 更新 Agent

GET  /pipelines                 # 列出 Pipeline
GET  /pipelines/{id}            # 获取 Pipeline 详情
POST /pipelines                 # 创建 Pipeline
PUT  /pipelines/{id}            # 更新 Pipeline

GET  /config/agents/{id}        # 读取 Agent 配置
PUT  /config/agents/{id}        # 更新 Agent 配置
GET  /config/pipelines/{id}     # 读取 Pipeline 配置
PUT  /config/pipelines/{id}     # 更新 Pipeline 配置

POST /execute/agent             # 异步执行 Agent
POST /execute/pipeline          # 异步执行 Pipeline
GET  /tasks/{task_id}           # 查询任务状态
GET  /tasks/{task_id}/progress  # 查询执行进度
```

## Data Models

### Core Models

```python
@dataclass
class AgentMetadata:
    id: str
    name: str
    category: str
    environment: str
    owner: str
    version: str
    tags: List[str]
    deprecated: bool
    location: Path

@dataclass
class PipelineConfig:
    id: str
    name: str
    steps: List[StepConfig]
    inputs: List[str]
    outputs: List[str]
    baseline: Optional[str]
    variants: List[str]

@dataclass
class StepConfig:
    id: str
    type: str  # "agent_flow", "code_node", "batch_aggregator"
    agent: Optional[str]
    flow: Optional[str]
    code_config: Optional[CodeNodeConfig]
    batch_mode: bool
    aggregation_strategy: Optional[str]
    concurrent_group: Optional[str]
    depends_on: List[str]
    input_mapping: Dict[str, str]
    output_key: str

@dataclass
class CodeNodeConfig:
    language: str  # "javascript" or "python"
    code: Optional[str]
    code_file: Optional[Path]
    timeout: int

@dataclass
class EvaluationConfig:
    rules: List[str]
    judge_enabled: bool
    judge_agent_id: str
    judge_flow: str
    scale_min: float
    scale_max: float
```

## Correctness Properties

### Agent Registry Properties (P1-P4)
- P1: Registry loading completeness
- P2: Agent registration persistence
- P3: Agent query completeness
- P4: Registry hot reload consistency

### Code Node Properties (P5-P11)
- P5: Code node configuration parsing
- P6: JavaScript execution correctness
- P7: Python execution correctness
- P8: Code node input passing
- P9: Code node output capture
- P10: Code node timeout enforcement
- P11: Code node error reporting

### Concurrent Execution Properties (P12-P21)
- P12: Dependency identification
- P13: Concurrent execution of independent steps
- P14: Concurrent group parsing
- P15: Concurrent synchronization
- P16: Concurrent error handling
- P17: Concurrent test execution
- P18: Max concurrency enforcement
- P19: Concurrent error isolation
- P20: Result order preservation
- P21: Progress feedback availability

### Batch Processing Properties (P22-P26)
- P22: Batch step configuration parsing
- P23: Batch output collection
- P24: Batch aggregation correctness
- P25: Aggregation result passing
- P26: Aggregation strategy parsing

### Pipeline Testset Properties (P27-P31)
- P27: Multi-step testset parsing
- P28: Batch test execution
- P29: Final output evaluation
- P30: Intermediate step evaluation
- P31: Expected aggregation validation

### API Layer Properties (P32-P35)
- P32: Core function API availability
- P33: Data model JSON serialization
- P34: Configuration API read-write
- P35: Async execution and progress query

## Error Handling

- 配置文件错误：提供详细的错误信息和行号
- 代码执行错误：捕获完整的堆栈跟踪
- 超时错误：强制终止进程，返回超时错误
- 并发错误：错误隔离，不影响其他任务
- API 错误：统一的错误响应格式

## Testing Strategy

### 测试类型
1. **单元测试**: 测试独立组件的功能
2. **Property 测试**: 使用 Hypothesis 进行属性测试
3. **集成测试**: 测试完整的工作流，使用真实的豆包 Pro 模型

### 测试配置
- Property 测试至少 100 次迭代
- 集成测试使用真实的 Doubao Pro 模型
- 测试覆盖率目标 85%+
