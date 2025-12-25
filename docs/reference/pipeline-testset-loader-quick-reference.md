# Pipeline 测试集加载器快速参考

## 概述

Pipeline 测试集加载器支持加载和处理复杂的 Pipeline 级别测试集，包括多步骤测试、批量处理、中间步骤评估等功能。

## 快速开始

### 基本用法

```python
from src.testset_loader import load_testset, TestsetLoader

# 加载测试集
test_cases = load_testset('path/to/testset.jsonl')

# 遍历测试用例
for tc in test_cases:
    print(f"Test ID: {tc.id}")
    print(f"Inputs: {tc.inputs}")
    print(f"Expected outputs: {tc.expected_outputs}")
```

## TestCase 类

### 核心字段

```python
@dataclass
class TestCase:
    id: str                                    # 测试用例 ID
    tags: List[str]                            # 标签
    inputs: Dict[str, Any]                     # 全局输入
    step_inputs: Dict[str, Dict[str, Any]]     # 步骤级输入
    batch_items: Optional[List[Dict[str, Any]]] # 批量数据
    expected_outputs: Dict[str, Any]           # 预期输出
    expected_aggregation: Optional[Any]        # 预期聚合结果
    intermediate_expectations: Dict[str, Any]  # 中间步骤预期
    evaluation_config: Dict[str, Any]          # 评估配置
```

### 常用方法

#### 检查方法

```python
# 检查是否有步骤级输入
tc.has_step_inputs() -> bool

# 检查是否有批量数据
tc.has_batch_data() -> bool

# 检查是否有中间步骤预期
tc.has_intermediate_expectations() -> bool

# 检查是否有预期聚合结果
tc.has_expected_aggregation() -> bool
```

#### 数据访问方法

```python
# 获取输入值
tc.get_input('key', default=None) -> Any

# 获取步骤输入
tc.get_step_input('step_id', 'key', default=None) -> Any

# 获取中间步骤预期
tc.get_intermediate_expectation('step_id') -> Optional[Dict[str, Any]]

# 获取所有步骤 ID
tc.get_all_step_ids() -> List[str]

# 获取批量数据大小
tc.get_batch_size() -> int
```

#### 评估配置方法

```python
# 是否应该评估中间步骤
tc.should_evaluate_intermediate() -> bool

# 是否应该评估最终输出
tc.should_evaluate_final() -> bool

# 是否应该评估聚合结果
tc.should_evaluate_aggregation() -> bool

# 是否使用严格模式
tc.is_strict_mode() -> bool

# 获取数值容差
tc.get_tolerance() -> float

# 获取忽略字段列表
tc.get_ignore_fields() -> List[str]
```

## TestsetLoader 类

### 加载方法

```python
# 加载测试集（返回 TestCase 对象列表）
test_cases = TestsetLoader.load_testset(file_path)

# 加载测试集（返回字典列表，向后兼容）
test_dicts = TestsetLoader.load_testset_dict(file_path)
```

### 验证方法

```python
# 验证测试集
errors = TestsetLoader.validate_testset(test_cases)
if errors:
    for error in errors:
        print(f"Error: {error}")
```

### 过滤方法

```python
# 按标签过滤
filtered = TestsetLoader.filter_by_tags(
    test_cases,
    include_tags=['integration', 'critical'],
    exclude_tags=['slow']
)

# 获取批量处理测试用例
batch_cases = TestsetLoader.get_batch_test_cases(test_cases)

# 获取包含步骤级输入的测试用例
step_input_cases = TestsetLoader.get_step_input_test_cases(test_cases)

# 获取需要中间步骤评估的测试用例
intermediate_cases = TestsetLoader.get_intermediate_evaluation_test_cases(test_cases)
```

### Pipeline 数据提取

```python
# 提取特定步骤的数据
step_data = TestsetLoader.extract_step_data(test_case, 'step_id')
# 返回: {'inputs': {...}, 'expected': {...}}

# 组织批量数据
batch_info = TestsetLoader.organize_batch_data(test_cases)
# 返回: {
#   'total_test_cases': int,
#   'total_batch_items': int,
#   'average_batch_size': float,
#   'test_cases': List[TestCase]
# }
```

### Pipeline 结构分析

```python
# 分析 Pipeline 结构
structure = TestsetLoader.get_pipeline_structure(test_cases)
# 返回: {
#   'total_steps': int,
#   'all_step_ids': List[str],
#   'steps_with_inputs': List[str],
#   'steps_with_expectations': List[str],
#   'has_batch_processing': bool,
#   'has_intermediate_evaluation': bool
# }

# 按 Pipeline 特性分组
groups = TestsetLoader.group_by_pipeline_features(test_cases)
# 返回: {
#   'simple': List[TestCase],
#   'multi_step': List[TestCase],
#   'batch_processing': List[TestCase],
#   'intermediate_evaluation': List[TestCase],
#   'complex': List[TestCase]
# }
```

## 测试集格式

### 简单格式

```jsonl
{"id": "test_1", "text": "input", "expected_output": "result"}
```

### 多步骤格式

```jsonl
{
  "id": "multi_step_1",
  "inputs": {"text": "input"},
  "step_inputs": {
    "step1": {"param1": "value1"},
    "step2": {"param2": "value2"}
  },
  "expected_outputs": {"result": "output"}
}
```

### 批量处理格式

```jsonl
{
  "id": "batch_1",
  "batch_items": [
    {"item": "A"},
    {"item": "B"}
  ],
  "expected_aggregation": {"count": 2}
}
```

### 中间步骤评估格式

```jsonl
{
  "id": "intermediate_1",
  "inputs": {"text": "input"},
  "step_inputs": {
    "preprocess": {"lowercase": true}
  },
  "intermediate_expectations": {
    "preprocess": {"cleaned_text": "input"}
  },
  "expected_outputs": {"result": "output"}
}
```

### 完整格式

```jsonl
{
  "id": "complete_1",
  "tags": ["integration", "critical"],
  "inputs": {"text": "input"},
  "step_inputs": {
    "step1": {"param": "value"}
  },
  "batch_items": [{"item": "A"}],
  "intermediate_expectations": {
    "step1": {"output": "result"}
  },
  "expected_aggregation": {"count": 1},
  "expected_outputs": {"result": "output"},
  "evaluation_config": {
    "evaluate_intermediate": true,
    "evaluate_final": true,
    "strict_mode": false,
    "tolerance": 0.01,
    "ignore_fields": ["timestamp"]
  }
}
```

## 常见用例

### 用例 1: 加载并验证测试集

```python
from src.testset_loader import load_testset, validate_testset

# 加载测试集
test_cases = load_testset('testset.jsonl')

# 验证测试集
errors = validate_testset(test_cases)
if errors:
    print("Validation errors:")
    for error in errors:
        print(f"  - {error}")
else:
    print(f"Loaded {len(test_cases)} valid test cases")
```

### 用例 2: 按标签过滤测试用例

```python
from src.testset_loader import load_testset, filter_by_tags

test_cases = load_testset('testset.jsonl')

# 只运行关键的集成测试
critical_tests = filter_by_tags(
    test_cases,
    include_tags=['integration', 'critical']
)

print(f"Running {len(critical_tests)} critical integration tests")
```

### 用例 3: 处理多步骤测试

```python
from src.testset_loader import load_testset, TestsetLoader

test_cases = load_testset('testset.jsonl')

for tc in test_cases:
    if tc.has_step_inputs():
        print(f"Test {tc.id} has {len(tc.step_inputs)} steps")
        
        for step_id in tc.get_all_step_ids():
            step_data = TestsetLoader.extract_step_data(tc, step_id)
            
            if 'inputs' in step_data:
                print(f"  Step {step_id} inputs: {step_data['inputs']}")
            
            if 'expected' in step_data:
                print(f"  Step {step_id} expected: {step_data['expected']}")
```

### 用例 4: 处理批量测试

```python
from src.testset_loader import load_testset, TestsetLoader

test_cases = load_testset('testset.jsonl')

# 获取批量处理测试用例
batch_cases = TestsetLoader.get_batch_test_cases(test_cases)

for tc in batch_cases:
    print(f"Test {tc.id}:")
    print(f"  Batch size: {tc.get_batch_size()}")
    print(f"  Has expected aggregation: {tc.has_expected_aggregation()}")
    
    if tc.has_expected_aggregation():
        print(f"  Expected aggregation: {tc.expected_aggregation}")
```

### 用例 5: 分析 Pipeline 结构

```python
from src.testset_loader import load_testset, TestsetLoader

test_cases = load_testset('testset.jsonl')

# 分析 Pipeline 结构
structure = TestsetLoader.get_pipeline_structure(test_cases)

print("Pipeline Structure:")
print(f"  Total steps: {structure['total_steps']}")
print(f"  All step IDs: {structure['all_step_ids']}")
print(f"  Steps with inputs: {structure['steps_with_inputs']}")
print(f"  Steps with expectations: {structure['steps_with_expectations']}")
print(f"  Has batch processing: {structure['has_batch_processing']}")
print(f"  Has intermediate evaluation: {structure['has_intermediate_evaluation']}")
```

### 用例 6: 按特性分组

```python
from src.testset_loader import load_testset, TestsetLoader

test_cases = load_testset('testset.jsonl')

# 按特性分组
groups = TestsetLoader.group_by_pipeline_features(test_cases)

print("Test Distribution:")
print(f"  Simple: {len(groups['simple'])}")
print(f"  Multi-step: {len(groups['multi_step'])}")
print(f"  Batch processing: {len(groups['batch_processing'])}")
print(f"  Intermediate evaluation: {len(groups['intermediate_evaluation'])}")
print(f"  Complex: {len(groups['complex'])}")

# 先运行简单测试
for tc in groups['simple']:
    print(f"Running simple test: {tc.id}")
    # ... 运行测试 ...

# 再运行复杂测试
for tc in groups['complex']:
    print(f"Running complex test: {tc.id}")
    # ... 运行测试 ...
```

### 用例 7: 使用评估配置

```python
from src.testset_loader import load_testset

test_cases = load_testset('testset.jsonl')

for tc in test_cases:
    print(f"Test {tc.id}:")
    
    # 检查评估配置
    if tc.should_evaluate_intermediate():
        print("  Will evaluate intermediate steps")
    
    if tc.should_evaluate_final():
        print("  Will evaluate final output")
    
    if tc.should_evaluate_aggregation():
        print("  Will evaluate aggregation result")
    
    # 获取评估参数
    if tc.is_strict_mode():
        print("  Using strict mode")
    else:
        print(f"  Using tolerance: {tc.get_tolerance()}")
    
    ignore_fields = tc.get_ignore_fields()
    if ignore_fields:
        print(f"  Ignoring fields: {ignore_fields}")
```

## 便捷函数

```python
from src.testset_loader import (
    load_testset,           # 加载测试集
    load_testset_dict,      # 加载测试集（字典格式）
    validate_testset,       # 验证测试集
    filter_by_tags          # 按标签过滤
)

# 使用便捷函数
test_cases = load_testset('testset.jsonl')
errors = validate_testset(test_cases)
filtered = filter_by_tags(test_cases, include_tags=['critical'])
```

## 错误处理

```python
from src.testset_loader import load_testset, validate_testset

try:
    # 加载测试集
    test_cases = load_testset('testset.jsonl')
    
    # 验证测试集
    errors = validate_testset(test_cases)
    if errors:
        print("Validation errors found:")
        for error in errors:
            print(f"  - {error}")
        # 决定是否继续
    
except FileNotFoundError as e:
    print(f"Testset file not found: {e}")
    
except ValueError as e:
    print(f"Invalid testset format: {e}")
```

## 性能提示

1. **批量加载**: 一次性加载整个测试集比多次加载单个测试用例更高效
2. **过滤优先**: 先按标签过滤，再进行复杂的处理
3. **结构分析**: 对于大型测试集，只在需要时进行结构分析
4. **缓存结果**: 如果需要多次访问相同的数据，考虑缓存结果

## 相关文档

- [Pipeline 测试集格式规范](./pipeline-testset-format-specification.md)
- [测试集加载器完整文档](./testset-loader-quick-reference.md)
- [批量处理配置指南](./batch-processing-config-guide.md)
- [Pipeline 配置指南](./pipeline-guide.md)

## 示例文件

- `examples/testsets/pipeline_multi_step_examples.jsonl`
- `examples/testsets/pipeline_batch_aggregation_examples.jsonl`
- `examples/testsets/pipeline_intermediate_evaluation_examples.jsonl`
- `examples/testsets/pipeline_complex_scenarios.jsonl`
