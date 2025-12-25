# Design Document

## Overview

本设计文档定义了 Prompt Lab 项目从实验阶段向生产就绪阶段转型的完整技术方案。项目将进行全面重构,包括:

1. **项目结构重组**: 清理根目录,分离测试与生产内容,优化文档结构
2. **Agent Registry 系统**: 建立统一的 Agent 注册和管理机制
3. **复杂 Pipeline 支持**: 实现代码节点、并发执行和批量聚合功能
4. **测试集架构升级**: 支持 Pipeline 级别的复杂测试场景
5. **API 层设计**: 为可视化界面做准备,提供完整的 REST API
6. **性能优化**: 实现并发执行,提升测试速度

本设计遵循以下原则:
- **向后兼容**: 保持现有功能的兼容性
- **渐进式重构**: 分阶段实施,降低风险
- **可扩展性**: 为未来功能预留扩展空间
- **生产就绪**: 确保系统稳定性和可维护性

## Architecture

### 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                      API 层 (Future)                             │
│  REST API / GraphQL API / WebSocket                             │
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
│  │  Pipeline Runner (Enhanced)                            │    │
│  │  - 依赖分析                                             │    │
│  │  - 并发调度                                             │    │
│  │  - 代码节点执行                                         │    │
│  │  - 批量聚合                                             │    │
│  └────────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Code Node Executor                                     │    │
│  │  - JavaScript 执行 (Node.js)                           │    │
│  │  - Python 执行 (subprocess)                            │    │
│  │  - 超时控制                                             │    │
│  │  - 错误捕获                                             │    │
│  └────────────────────────────────────────────────────────┘    │
│  ┌────────────────────────────────────────────────────────┐    │
│  │  Concurrent Executor                                    │    │
│  │  - 任务队列                                             │    │
│  │  - 线程池/进程池                                        │    │
│  │  - 进度跟踪                                             │    │
│  │  - 结果聚合                                             │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```


### 项目目录结构 (重构后)

```
prompt-lab/
├── .env                          # 环境变量
├── .gitignore                    # Git 忽略文件
├── README.md                     # 唯一的主文档
├── requirements.txt              # Python 依赖
├── pyproject.toml                # 项目配置 (新增)
│
├── agents/                       # 生产 Agent
│   ├── _template/                # Agent 模板
│   ├── judge_default/            # 系统 Agent
│   ├── mem_l1_summarizer/        # 生产 Agent
│   └── usr_profile/              # 生产 Agent
│
├── pipelines/                    # 生产 Pipeline
│   ├── _template/                # Pipeline 模板 (新增)
│   └── (生产 Pipeline 配置)
│
├── data/                         # 运行时数据
│   ├── agents/                   # Agent 数据
│   ├── pipelines/                # Pipeline 数据
│   └── baselines/                # 基线数据
│
├── docs/                         # 所有文档
│   ├── README.md                 # 文档导航
│   ├── architecture.md           # 架构文档
│   ├── api/                      # API 文档 (新增)
│   ├── guides/                   # 使用指南
│   └── reference/                # 参考文档
│
├── examples/                     # 示例
│   ├── agents/                   # 示例 Agent
│   ├── pipelines/                # 示例 Pipeline
│   └── scripts/                  # 示例脚本
│
├── src/                          # 源代码
│   ├── __main__.py               # CLI 入口
│   ├── agent_registry.py         # Agent 注册 (增强)
│   ├── pipeline_runner.py        # Pipeline 执行 (增强)
│   ├── code_executor.py          # 代码节点执行器 (新增)
│   ├── concurrent_executor.py    # 并发执行器 (新增)
│   ├── batch_aggregator.py       # 批量聚合器 (新增)
│   ├── api/                      # API 层 (新增)
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── models.py
│   └── ...
│
├── tests/                        # 测试代码
│   ├── unit/                     # 单元测试 (新增)
│   ├── integration/              # 集成测试 (新增)
│   ├── fixtures/                 # 测试固件
│   │   ├── agents/               # 测试 Agent
│   │   ├── pipelines/            # 测试 Pipeline
│   │   └── testsets/             # 测试数据
│   └── conftest.py               # pytest 配置
│
├── scripts/                      # 工具脚本
│   ├── sync_agent_registry.py    # 同步 Agent Registry (新增)
│   ├── migrate_structure.py      # 结构迁移脚本 (新增)
│   └── cleanup_deprecated.py     # 清理过时文件 (新增)
│
└── config/                       # 配置文件 (新增)
    ├── agent_registry.yaml       # Agent Registry 配置
    └── system_config.yaml        # 系统配置
```

### 关键变更说明

1. **根目录清理**: 只保留必要的配置文件和主 README
2. **测试内容分离**: 所有测试相关内容移到 tests 目录
3. **文档集中管理**: 所有文档移到 docs 目录
4. **配置文件集中**: 新增 config 目录存放系统配置
5. **API 层预留**: 在 src 下预留 api 目录


## Components and Interfaces

### 1. Agent Registry System

#### 1.1 Agent Registry 配置文件

```yaml
# config/agent_registry.yaml
version: "1.0"
agents:
  mem_l1_summarizer:
    name: "一级记忆总结"
    category: "production"
    environment: "production"
    owner: "memory-team"
    version: "1.2.0"
    tags: ["memory", "summarization"]
    deprecated: false
    location: "agents/mem_l1_summarizer"
    
  judge_default:
    name: "默认评估 Agent"
    category: "system"
    environment: "production"
    owner: "platform-team"
    version: "2.0.0"
    tags: ["evaluation", "judge"]
    deprecated: false
    location: "agents/judge_default"
```

#### 1.2 Agent Registry 接口

```python
class AgentRegistry:
    """Agent 统一注册和管理"""
    
    def __init__(self, config_path: Path):
        """从配置文件初始化"""
        pass
    
    def load_registry(self) -> Dict[str, AgentMetadata]:
        """加载 Agent Registry"""
        pass
    
    def reload_registry(self) -> None:
        """重新加载 Registry (热重载)"""
        pass
    
    def get_agent(self, agent_id: str) -> AgentMetadata:
        """获取 Agent 元数据"""
        pass
    
    def list_agents(
        self, 
        category: Optional[str] = None,
        environment: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> List[AgentMetadata]:
        """列出 Agent (支持过滤)"""
        pass
    
    def register_agent(self, agent_id: str, metadata: AgentMetadata) -> None:
        """注册新 Agent"""
        pass
    
    def update_agent(self, agent_id: str, metadata: AgentMetadata) -> None:
        """更新 Agent 元数据"""
        pass
    
    def sync_from_filesystem(self) -> SyncResult:
        """从文件系统同步 Agent"""
        pass
```


### 2. Code Node Executor

#### 2.1 代码节点配置

```yaml
# Pipeline 配置中的代码节点示例
steps:
  - id: "transform"
    type: "code_node"
    language: "javascript"  # 或 "python"
    code: |
      // 内联代码
      function transform(inputs) {
        return inputs.map(item => ({
          ...item,
          processed: true
        }));
      }
      module.exports = transform;
    input_mapping:
      inputs: "previous_step_output"
    output_key: "transformed_data"
    timeout: 30  # 秒
    
  - id: "aggregate"
    type: "code_node"
    language: "python"
    code_file: "scripts/aggregate.py"  # 外部文件
    input_mapping:
      data: "transformed_data"
    output_key: "aggregated_result"
    timeout: 60
```

#### 2.2 Code Executor 接口

```python
class CodeExecutor:
    """代码节点执行器"""
    
    def execute_javascript(
        self, 
        code: str, 
        inputs: Dict[str, Any],
        timeout: int = 30
    ) -> ExecutionResult:
        """执行 JavaScript 代码"""
        pass
    
    def execute_python(
        self, 
        code: str, 
        inputs: Dict[str, Any],
        timeout: int = 30
    ) -> ExecutionResult:
        """执行 Python 代码"""
        pass
    
    def execute_from_file(
        self,
        file_path: Path,
        language: str,
        inputs: Dict[str, Any],
        timeout: int = 30
    ) -> ExecutionResult:
        """从文件执行代码"""
        pass

@dataclass
class ExecutionResult:
    """代码执行结果"""
    success: bool
    output: Any
    error: Optional[str]
    stderr: Optional[str]
    execution_time: float
    timeout: bool
```


### 3. Concurrent Executor

#### 3.1 并发执行配置

```yaml
# Pipeline 配置中的并发执行示例
steps:
  - id: "step1"
    type: "agent_flow"
    agent: "agent1"
    flow: "flow1"
    concurrent_group: "group_a"  # 并发组
    
  - id: "step2"
    type: "agent_flow"
    agent: "agent2"
    flow: "flow2"
    concurrent_group: "group_a"  # 同一并发组
    
  - id: "step3"
    type: "agent_flow"
    agent: "agent3"
    flow: "flow3"
    depends_on: ["step1", "step2"]  # 等待 group_a 完成

# 系统配置
concurrent_execution:
  enabled: true
  max_workers: 4  # 最大并发数
  strategy: "thread"  # "thread" 或 "process"
```

#### 3.2 Concurrent Executor 接口

```python
class ConcurrentExecutor:
    """并发执行器"""
    
    def __init__(self, max_workers: int = 4, strategy: str = "thread"):
        """初始化并发执行器"""
        pass
    
    def execute_concurrent(
        self,
        tasks: List[Task],
        progress_callback: Optional[Callable] = None
    ) -> List[TaskResult]:
        """并发执行任务列表"""
        pass
    
    def execute_with_dependencies(
        self,
        tasks: List[Task],
        dependency_graph: Dict[str, List[str]]
    ) -> List[TaskResult]:
        """根据依赖关系并发执行"""
        pass

class DependencyAnalyzer:
    """依赖分析器"""
    
    def analyze_dependencies(
        self, 
        steps: List[StepConfig]
    ) -> DependencyGraph:
        """分析步骤依赖关系"""
        pass
    
    def find_concurrent_groups(
        self, 
        dependency_graph: DependencyGraph
    ) -> List[List[str]]:
        """找出可以并发执行的步骤组"""
        pass
    
    def topological_sort(
        self, 
        dependency_graph: DependencyGraph
    ) -> List[str]:
        """拓扑排序"""
        pass
```


### 4. Batch Aggregator

#### 4.1 批量处理配置

```yaml
# Pipeline 配置中的批量处理示例
steps:
  - id: "process_batch"
    type: "agent_flow"
    agent: "processor"
    flow: "process_v1"
    batch_mode: true  # 批量模式
    batch_size: 10    # 每批处理10个
    input_mapping:
      text: "input_text"
    output_key: "processed_items"
    
  - id: "aggregate"
    type: "batch_aggregator"
    aggregation_strategy: "custom"  # "concat", "stats", "filter", "custom"
    code: |
      def aggregate(items):
        # 自定义聚合逻辑
        return {
          "total": len(items),
          "results": [item["result"] for item in items],
          "summary": summarize(items)
        }
    input_mapping:
      items: "processed_items"
    output_key: "aggregated_result"
    
  - id: "final_agent"
    type: "agent_flow"
    agent: "summarizer"
    flow: "summarize_v1"
    input_mapping:
      data: "aggregated_result"
    output_key: "final_output"
```

#### 4.2 Batch Aggregator 接口

```python
class BatchAggregator:
    """批量聚合器"""
    
    def aggregate_concat(
        self, 
        items: List[Any],
        separator: str = "\n"
    ) -> str:
        """拼接聚合"""
        pass
    
    def aggregate_stats(
        self, 
        items: List[Any],
        fields: List[str]
    ) -> Dict[str, Any]:
        """统计聚合"""
        pass
    
    def aggregate_filter(
        self, 
        items: List[Any],
        condition: Callable
    ) -> List[Any]:
        """过滤聚合"""
        pass
    
    def aggregate_custom(
        self, 
        items: List[Any],
        code: str,
        language: str = "python"
    ) -> Any:
        """自定义聚合"""
        pass

class BatchProcessor:
    """批量处理器"""
    
    def process_in_batches(
        self,
        items: List[Any],
        processor: Callable,
        batch_size: int = 10,
        concurrent: bool = True
    ) -> List[Any]:
        """批量处理"""
        pass
```


## Data Models

### Agent Registry Models

```python
@dataclass
class AgentMetadata:
    """Agent 元数据"""
    id: str
    name: str
    category: str  # "production", "example", "test", "system"
    environment: str  # "production", "staging", "demo", "test"
    owner: str
    version: str
    tags: List[str]
    deprecated: bool
    location: Path
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class SyncResult:
    """同步结果"""
    added: List[str]
    updated: List[str]
    removed: List[str]
    errors: List[str]
```

### Pipeline Models (Enhanced)

```python
@dataclass
class CodeNodeConfig:
    """代码节点配置"""
    language: str  # "javascript" or "python"
    code: Optional[str] = None  # 内联代码
    code_file: Optional[Path] = None  # 外部文件
    timeout: int = 30
    env_vars: Dict[str, str] = field(default_factory=dict)

@dataclass
class StepConfig:
    """步骤配置 (增强)"""
    id: str
    type: str  # "agent_flow", "code_node", "batch_aggregator"
    
    # Agent Flow 字段
    agent: Optional[str] = None
    flow: Optional[str] = None
    
    # Code Node 字段
    code_config: Optional[CodeNodeConfig] = None
    
    # 批量处理字段
    batch_mode: bool = False
    batch_size: int = 10
    
    # 聚合字段
    aggregation_strategy: Optional[str] = None  # "concat", "stats", "filter", "custom"
    aggregation_code: Optional[str] = None
    
    # 并发控制
    concurrent_group: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    
    # 通用字段
    input_mapping: Dict[str, str] = field(default_factory=dict)
    output_key: str = ""
    required: bool = True
    timeout: Optional[int] = None

@dataclass
class DependencyGraph:
    """依赖图"""
    nodes: List[str]
    edges: Dict[str, List[str]]  # node_id -> [dependent_node_ids]
    concurrent_groups: Dict[str, List[str]]  # group_name -> [node_ids]
```

### Testset Models (Enhanced)

```python
@dataclass
class PipelineTestCase:
    """Pipeline 测试用例 (增强)"""
    id: str
    tags: List[str]
    
    # 全局输入
    inputs: Dict[str, Any]
    
    # 步骤级输入 (可选)
    step_inputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # 预期输出
    expected_outputs: Dict[str, Any] = field(default_factory=dict)
    
    # 批量处理相关
    batch_items: Optional[List[Dict[str, Any]]] = None
    expected_aggregation: Optional[Any] = None
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Agent Registry Properties

Property 1: Registry loading completeness
*For any* valid Agent Registry configuration file, loading the registry should successfully load all defined agents with complete metadata
**Validates: Requirements 2.1**

Property 2: Agent registration persistence
*For any* new agent metadata, after registering the agent and reloading the registry, the agent should be queryable with the same metadata
**Validates: Requirements 2.2**

Property 3: Agent query completeness
*For any* registered agent ID, querying the agent should return all required metadata fields (ID, name, category, description, etc.)
**Validates: Requirements 2.3**

Property 4: Registry hot reload consistency
*For any* registry configuration file, after modifying the file and triggering reload, the in-memory registry should reflect the changes
**Validates: Requirements 2.4**

### Code Node Properties

Property 5: Code node configuration parsing
*For any* pipeline configuration containing code nodes (inline or file-based), the system should successfully parse the configuration
**Validates: Requirements 3.1**

Property 6: JavaScript execution correctness
*For any* valid JavaScript code and input data, executing the code node should return the expected output or error
**Validates: Requirements 3.2**

Property 7: Python execution correctness
*For any* valid Python code and input data, executing the code node should return the expected output or error
**Validates: Requirements 3.2**

Property 8: Code node input passing
*For any* code node with input mapping, the input data should be correctly passed to the code as parameters
**Validates: Requirements 10.4**

Property 9: Code node output capture
*For any* code node execution, both stdout output and stderr errors should be captured and returned
**Validates: Requirements 10.5**

Property 10: Code node timeout enforcement
*For any* code node with timeout configuration, if execution exceeds the timeout, the system should terminate execution and return a timeout error
**Validates: Requirements 10.6**

Property 11: Code node error reporting
*For any* failed code node execution, the system should provide detailed error information including stack trace
**Validates: Requirements 10.7**

### Concurrent Execution Properties

Property 12: Dependency identification
*For any* pipeline configuration, the system should correctly identify all steps with no dependencies
**Validates: Requirements 3.3**

Property 13: Concurrent execution of independent steps
*For any* pipeline with independent steps, those steps should execute concurrently (not sequentially)
**Validates: Requirements 3.4**

Property 14: Concurrent group parsing
*For any* pipeline configuration with concurrent_group annotations, the system should correctly parse and group steps
**Validates: Requirements 3.5**

Property 15: Concurrent synchronization
*For any* pipeline with concurrent steps followed by dependent steps, the dependent steps should only execute after all concurrent steps complete
**Validates: Requirements 3.6**

Property 16: Concurrent error handling
*For any* code node in concurrent execution that fails, the error should be recorded and handled according to the required/optional configuration
**Validates: Requirements 3.7**

Property 17: Concurrent test execution
*For any* list of independent test cases, executing them concurrently should produce the same results as sequential execution
**Validates: Requirements 9.1**

Property 18: Max concurrency enforcement
*For any* concurrent execution with max_workers=N, the system should never execute more than N tasks simultaneously
**Validates: Requirements 9.2**

Property 19: Concurrent error isolation
*For any* concurrent execution where some tasks fail, the failures should not prevent other independent tasks from completing
**Validates: Requirements 9.3**

Property 20: Result order preservation
*For any* concurrent execution of ordered tasks, the results should be returned in the original input order
**Validates: Requirements 9.4**

Property 21: Progress feedback availability
*For any* concurrent execution, the system should provide queryable progress information at any time
**Validates: Requirements 9.5**


### Batch Processing Properties

Property 22: Batch step configuration parsing
*For any* pipeline configuration with batch_mode steps, the system should correctly parse the batch configuration
**Validates: Requirements 4.1**

Property 23: Batch output collection
*For any* batch processing step, the system should collect all outputs from the batch execution
**Validates: Requirements 4.2**

Property 24: Batch aggregation correctness
*For any* batch aggregation with a defined strategy, the aggregated result should match the expected output format
**Validates: Requirements 4.3**

Property 25: Aggregation result passing
*For any* batch aggregation step followed by an agent step, the aggregated result should be correctly passed as input
**Validates: Requirements 4.4**

Property 26: Aggregation strategy parsing
*For any* batch aggregation configuration with a strategy (concat, stats, filter, custom), the system should correctly parse and apply the strategy
**Validates: Requirements 4.5**

### Pipeline Testset Properties

Property 27: Multi-step testset parsing
*For any* pipeline testset with step-specific test data, the system should correctly parse and associate data with steps
**Validates: Requirements 5.1**

Property 28: Batch test execution
*For any* pipeline testset with multiple test cases, the system should execute all cases and aggregate results
**Validates: Requirements 5.2**

Property 29: Final output evaluation
*For any* pipeline execution result, the system should support evaluating the final output against expected values
**Validates: Requirements 5.3**

Property 30: Intermediate step evaluation
*For any* pipeline execution with intermediate evaluation configured, the system should evaluate intermediate step outputs
**Validates: Requirements 5.4**

Property 31: Expected aggregation validation
*For any* testset with expected_aggregation defined, the system should validate the actual aggregation result against the expected value
**Validates: Requirements 5.5**

### API Layer Properties

Property 32: Core function API availability
*For any* core system function (agent execution, pipeline execution, evaluation), there should be a corresponding API endpoint
**Validates: Requirements 8.2**

Property 33: Data model JSON serialization
*For any* data model instance, serializing to JSON and deserializing back should produce an equivalent object
**Validates: Requirements 8.3**

Property 34: Configuration API read-write
*For any* configuration file, the system should support reading and writing through API endpoints
**Validates: Requirements 8.4**

Property 35: Async execution and progress query
*For any* long-running execution started asynchronously, the system should provide queryable progress information
**Validates: Requirements 8.5**


## Error Handling

### 1. Agent Registry Errors

- **配置文件错误**: YAML 解析失败、缺少必需字段
  - 处理: 提供详细的错误信息和行号,建议修复方案
  
- **Agent 不存在**: 查询不存在的 Agent
  - 处理: 返回明确的错误信息,列出可用的 Agent
  
- **同步冲突**: 文件系统与 Registry 不一致
  - 处理: 提供冲突报告,支持手动解决或自动合并

### 2. Code Node Errors

- **语法错误**: JavaScript/Python 代码语法错误
  - 处理: 捕获并返回详细的语法错误信息和行号
  
- **运行时错误**: 代码执行过程中的异常
  - 处理: 捕获完整的堆栈跟踪,提供上下文信息
  
- **超时错误**: 代码执行超过配置的超时时间
  - 处理: 强制终止进程,返回超时错误和已执行时间
  
- **资源错误**: 内存不足、文件不存在等
  - 处理: 捕获系统级错误,提供资源使用情况

### 3. Concurrent Execution Errors

- **依赖循环**: Pipeline 步骤存在循环依赖
  - 处理: 在执行前检测,提供循环路径信息
  
- **部分失败**: 并发执行中部分任务失败
  - 处理: 收集所有错误,根据 required 配置决定是否继续
  
- **资源竞争**: 并发任务访问共享资源冲突
  - 处理: 使用锁机制,提供重试机制

### 4. Batch Processing Errors

- **聚合失败**: 批量聚合代码执行失败
  - 处理: 返回详细错误信息,保留原始批量数据
  
- **数据不一致**: 批量数据格式不统一
  - 处理: 验证数据格式,提供格式转换建议

### 5. Error Recovery Strategies

- **自动重试**: 对于临时性错误(网络超时、API 限流)
- **降级处理**: 对于非关键步骤,使用默认值继续执行
- **检查点恢复**: 对于长时间运行的 Pipeline,支持从失败点恢复
- **错误聚合**: 收集所有错误,生成详细的错误报告


## Testing Strategy

### Unit Testing

本项目将使用 pytest 作为测试框架,采用双重测试策略:

**单元测试覆盖范围**:
- Agent Registry 的加载、查询、注册、同步功能
- Code Executor 的 JavaScript/Python 执行功能
- Dependency Analyzer 的依赖分析和拓扑排序
- Batch Aggregator 的各种聚合策略
- 配置文件解析和验证
- 数据模型的序列化和反序列化

**测试组织**:
```
tests/
├── unit/
│   ├── test_agent_registry.py
│   ├── test_code_executor.py
│   ├── test_concurrent_executor.py
│   ├── test_batch_aggregator.py
│   └── test_dependency_analyzer.py
├── integration/
│   ├── test_pipeline_with_code_nodes.py
│   ├── test_concurrent_pipeline.py
│   └── test_batch_pipeline.py
└── fixtures/
    ├── agents/
    ├── pipelines/
    └── testsets/
```

**⚠️ 重要: LLM 模型使用规范**:
- **单元测试**: 不涉及 LLM 调用的纯逻辑测试可以使用 mock
- **集成测试**: 所有涉及 Agent/Flow 执行的测试必须使用真实的豆包 (Doubao) Pro 模型
- **Property-Based 测试**: 如果测试涉及 LLM 调用，必须使用真实的 Doubao Pro 模型
- 测试配置应从环境变量读取，不硬编码模型名称
- 使用 `@pytest.mark.integration` 标记需要真实 LLM 调用的测试

### Property-Based Testing

本项目将使用 **Hypothesis** (Python 的 property-based testing 库) 进行属性测试。

**配置要求**:
- 每个 property-based test 至少运行 100 次迭代
- 每个测试必须标注对应的设计文档中的 Property 编号
- 使用格式: `# Feature: project-production-readiness, Property X: [property description]`
- **⚠️ 如果测试涉及 LLM 调用，必须使用真实的豆包 (Doubao) Pro 模型，不使用 mock**

**Property 测试覆盖**:

1. **Agent Registry Properties** (Property 1-4):
   - 生成随机的 Agent 配置,测试加载和查询
   - 生成随机的注册操作,测试持久化
   - 测试热重载的一致性

2. **Code Node Properties** (Property 5-11):
   - 生成随机的有效 JavaScript/Python 代码
   - 生成随机的输入数据
   - 测试超时机制(使用长时间运行的代码)
   - 测试错误捕获(使用会失败的代码)

3. **Concurrent Execution Properties** (Property 12-21):
   - 生成随机的 Pipeline 配置(有/无依赖)
   - 测试并发执行的正确性
   - 测试结果顺序保持
   - 测试最大并发数限制

4. **Batch Processing Properties** (Property 22-26):
   - 生成随机的批量数据
   - 测试各种聚合策略
   - 测试数据传递的正确性

5. **Pipeline Testset Properties** (Property 27-31):
   - 生成随机的测试集配置
   - 测试多阶段测试的正确性

6. **API Layer Properties** (Property 32-35):
   - 测试所有数据模型的序列化round-trip
   - 测试配置文件的读写round-trip

**测试示例**:

```python
from hypothesis import given, strategies as st
import pytest
import os

# Feature: project-production-readiness, Property 2: Agent registration persistence
@given(
    agent_id=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='_')),
    agent_name=st.text(min_size=1, max_size=100),
    category=st.sampled_from(['production', 'example', 'test', 'system'])
)
def test_agent_registration_persistence(agent_id, agent_name, category):
    """测试 Agent 注册后的持久化 (不涉及 LLM 调用)"""
    registry = AgentRegistry()
    
    # 创建随机 Agent 元数据
    metadata = AgentMetadata(
        id=agent_id,
        name=agent_name,
        category=category,
        environment='test',
        owner='test-team',
        version='1.0.0',
        tags=[],
        deprecated=False,
        location=Path(f'agents/{agent_id}')
    )
    
    # 注册 Agent
    registry.register_agent(agent_id, metadata)
    
    # 重新加载 Registry
    registry.reload_registry()
    
    # 查询 Agent
    loaded_metadata = registry.get_agent(agent_id)
    
    # 验证元数据一致
    assert loaded_metadata.id == metadata.id
    assert loaded_metadata.name == metadata.name
    assert loaded_metadata.category == metadata.category

# Feature: project-production-readiness, Property 33: Data model JSON serialization
@given(
    agent_metadata=st.builds(
        AgentMetadata,
        id=st.text(min_size=1),
        name=st.text(min_size=1),
        category=st.sampled_from(['production', 'example', 'test', 'system']),
        environment=st.sampled_from(['production', 'staging', 'demo', 'test']),
        owner=st.text(min_size=1),
        version=st.text(min_size=1),
        tags=st.lists(st.text()),
        deprecated=st.booleans(),
        location=st.builds(Path, st.text())
    )
)
def test_agent_metadata_json_round_trip(agent_metadata):
    """测试 AgentMetadata 的 JSON 序列化 round-trip (不涉及 LLM 调用)"""
    # 序列化
    json_str = agent_metadata.to_json()
    
    # 反序列化
    loaded_metadata = AgentMetadata.from_json(json_str)
    
    # 验证等价性
    assert loaded_metadata == agent_metadata

# Feature: project-production-readiness, Property 6: JavaScript execution correctness
@pytest.mark.integration  # 标记为集成测试
@given(
    input_data=st.dictionaries(
        keys=st.text(min_size=1, max_size=20),
        values=st.one_of(st.integers(), st.text(), st.floats(allow_nan=False))
    )
)
def test_javascript_code_execution_with_llm_agent(input_data):
    """
    测试包含 LLM Agent 调用的 JavaScript 代码节点执行
    ⚠️ 此测试使用真实的豆包 (Doubao) Pro 模型
    """
    # 确保使用 Doubao Pro 模型
    assert os.getenv('OPENAI_MODEL_NAME'), "必须配置 OPENAI_MODEL_NAME 环境变量"
    
    # 创建包含 LLM Agent 和代码节点的 Pipeline
    pipeline_config = create_test_pipeline_with_code_node(input_data)
    
    # 执行 Pipeline (会调用真实的 Doubao Pro 模型)
    result = execute_pipeline(pipeline_config)
    
    # 验证结果
    assert result.success
    assert result.code_node_output is not None
```

### Integration Testing

**集成测试场景**:
1. 完整的 Pipeline 执行(包含代码节点、并发步骤、批量处理)
2. Agent Registry 与文件系统的同步
3. API 端点的端到端测试
4. 并发执行的性能测试

**测试数据**:
- 使用 fixtures 目录下的测试 Agent 和 Pipeline
- 使用小规模数据集确保测试速度

**⚠️ 重要: LLM 模型配置**:
- **所有涉及 LLM 调用的测试必须使用真实的豆包 (Doubao) Pro 模型**
- 不使用 mock 或模拟的 LLM 响应
- 从环境配置中读取 Doubao Pro 的配置信息
- 测试前确保环境变量正确配置:
  - `OPENAI_API_KEY` 或对应的 Doubao API Key
  - `OPENAI_API_BASE` 指向 Doubao API 端点
  - `OPENAI_MODEL_NAME` 设置为 Doubao Pro 模型名称
- 集成测试应标记为 `@pytest.mark.integration`，需要真实 API 调用
- 单元测试中不涉及 LLM 的部分可以使用 mock


## Implementation Phases

### Phase 1: 项目结构重组 (Week 1)

**目标**: 清理项目结构,分离测试与生产内容

**任务**:
1. 创建迁移脚本,自动重组目录结构
2. 移动测试内容到 tests 目录
3. 整合文档到 docs 目录
4. 清理根目录,只保留主 README
5. 更新所有导入路径和引用
6. 运行现有测试确保兼容性

**验收标准**:
- 所有现有测试通过
- 项目结构符合设计文档
- 文档链接全部更新

### Phase 2: Agent Registry 系统 (Week 2)

**目标**: 实现统一的 Agent 注册和管理机制

**任务**:
1. 设计并实现 Agent Registry 配置格式
2. 实现 AgentRegistry 类
3. 实现热重载机制
4. 实现同步工具脚本
5. 更新现有代码使用新的 Registry
6. 编写单元测试和 property 测试

**验收标准**:
- Agent Registry 所有功能正常工作
- 所有 property 测试通过
- 文档完整

### Phase 3: Code Node Executor (Week 3)

**目标**: 实现代码节点执行功能

**任务**:
1. 实现 CodeExecutor 类
2. 实现 JavaScript 执行(Node.js)
3. 实现 Python 执行(subprocess)
4. 实现超时控制和错误捕获
5. 更新 Pipeline 配置解析
6. 更新 PipelineRunner 支持代码节点
7. 编写单元测试和 property 测试

**验收标准**:
- 代码节点可以正确执行 JS 和 Python 代码
- 超时和错误处理正常工作
- 所有 property 测试通过

### Phase 4: Concurrent Executor (Week 4)

**目标**: 实现并发执行功能

**任务**:
1. 实现 DependencyAnalyzer 类
2. 实现 ConcurrentExecutor 类
3. 更新 PipelineRunner 支持并发执行
4. 实现进度跟踪
5. 实现并发测试执行
6. 编写单元测试和 property 测试
7. 性能测试和优化

**验收标准**:
- 独立步骤可以并发执行
- 依赖关系正确处理
- 性能提升明显(至少2x)
- 所有 property 测试通过

### Phase 5: Batch Aggregator (Week 5)

**目标**: 实现批量处理和聚合功能

**任务**:
1. 实现 BatchAggregator 类
2. 实现各种聚合策略
3. 更新 Pipeline 配置支持批量处理
4. 更新 PipelineRunner 支持批量步骤
5. 更新测试集格式
6. 编写单元测试和 property 测试

**验收标准**:
- 批量处理和聚合功能正常工作
- 支持自定义聚合代码
- 所有 property 测试通过

### Phase 6: API Layer (Week 6)

**目标**: 实现 REST API 层

**任务**:
1. 选择 API 框架(FastAPI 推荐)
2. 设计 API 接口
3. 实现核心 API 端点
4. 实现异步执行和进度查询
5. 实现配置文件读写 API
6. 编写 API 文档(OpenAPI/Swagger)
7. 编写集成测试

**验收标准**:
- 所有核心功能可通过 API 调用
- API 文档完整
- 集成测试通过

### Phase 7: 测试和文档 (Week 7)

**目标**: 完善测试覆盖和文档

**任务**:
1. 补充缺失的单元测试
2. 补充缺失的 property 测试
3. 编写集成测试 (使用真实的豆包 Pro 模型)
4. 配置测试环境的 Doubao Pro 模型连接
5. 更新所有文档
6. 编写迁移指南
7. 编写最佳实践指南

**验收标准**:
- 测试覆盖率 > 80%
- 所有 property 测试通过
- 所有集成测试使用真实的 Doubao Pro 模型并通过
- 文档完整且准确

**⚠️ 测试环境配置要求**:
- 配置 `.env` 文件包含 Doubao Pro 的 API 配置
- 确保测试环境可以访问 Doubao API 端点
- 集成测试前验证 API 连接正常

## Migration Strategy

### 向后兼容性

**保持兼容的功能**:
- 现有的 Agent 配置格式
- 现有的 Pipeline 配置格式(扩展,不破坏)
- 现有的测试集格式
- 现有的 CLI 命令

**新增的功能**:
- Agent Registry 配置(可选,不影响现有功能)
- 代码节点(新的步骤类型)
- 并发执行(自动优化,不需要配置)
- 批量处理(新的步骤类型)

### 迁移步骤

1. **Phase 1 迁移**: 运行迁移脚本自动重组目录
2. **Phase 2 迁移**: 可选地创建 Agent Registry 配置
3. **Phase 3-5**: 无需迁移,新功能向后兼容
4. **Phase 6**: API 层是新增功能,不影响现有使用方式

### 回滚计划

- 每个 Phase 完成后打 Git tag
- 保留迁移前的备份
- 提供回滚脚本

## Performance Considerations

### 并发执行性能

**预期提升**:
- 对于包含 N 个独立步骤的 Pipeline: 理论加速比 N
- 对于批量测试: 理论加速比 = min(测试数量, max_workers)

**实际测试**:
- 10个独立测试用例,max_workers=4: 预期加速 3-4x
- 包含3个独立步骤的 Pipeline: 预期加速 2-3x

### 代码节点性能

**开销**:
- JavaScript 执行: 进程启动开销 ~50-100ms
- Python 执行: 进程启动开销 ~100-200ms

**优化策略**:
- 对于频繁调用的代码节点,考虑使用进程池
- 对于简单转换,优先使用内置聚合策略

### 内存使用

**批量处理**:
- 批量大小应根据可用内存调整
- 默认 batch_size=10,适合大多数场景
- 对于大数据量,建议使用流式处理(未来功能)

## Security Considerations

### 代码执行安全

**风险**:
- 代码节点可以执行任意代码
- 可能访问文件系统、网络等资源

**缓解措施**:
1. **沙箱执行**: 使用受限的执行环境
2. **资源限制**: 限制 CPU、内存、文件访问
3. **超时控制**: 强制超时终止
4. **代码审查**: 生产环境的代码节点需要审查
5. **权限控制**: API 层实现权限控制

### 配置文件安全

**风险**:
- 配置文件可能包含敏感信息
- YAML 解析可能存在注入风险

**缓解措施**:
1. **配置验证**: 严格验证配置格式
2. **敏感信息**: 使用环境变量存储敏感信息
3. **访问控制**: 限制配置文件的读写权限

## Future Enhancements

### 短期 (3-6 months)

1. **流式处理**: 支持大数据量的流式批量处理
2. **分布式执行**: 支持跨机器的分布式 Pipeline 执行
3. **可视化界面**: Web UI 用于管理和监控
4. **更多代码语言**: 支持 Ruby、Go 等其他语言

### 长期 (6-12 months)

1. **智能调度**: 基于历史数据的智能任务调度
2. **自动优化**: 自动分析和优化 Pipeline 性能
3. **云原生**: 支持 Kubernetes 部署
4. **实时协作**: 多用户实时协作编辑 Pipeline

