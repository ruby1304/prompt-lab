# Task 87: 更新测试集加载器 - 完成总结

## 任务概述

更新 `src/testset_loader.py` 以支持 Pipeline 级别的测试集，包括：
- Pipeline 测试集解析
- 步骤级数据提取
- 批量数据组织
- 中间步骤评估支持
- 评估配置支持

**需求**: Requirements 5.1

## 实现内容

### 1. 新增字段支持

#### TestCase 数据模型增强

在 `TestCase` 类中新增了两个重要字段：

```python
@dataclass
class TestCase:
    # ... 现有字段 ...
    
    # 中间步骤预期结果（可选，用于验证中间步骤）
    intermediate_expectations: Dict[str, Any] = field(default_factory=dict)
    
    # 评估配置（可选，控制评估行为）
    evaluation_config: Dict[str, Any] = field(default_factory=dict)
```

这两个字段支持：
- **intermediate_expectations**: 定义 Pipeline 中间步骤的预期输出，用于验证每个步骤是否正确执行
- **evaluation_config**: 控制评估行为，包括是否评估中间步骤、严格模式、容差等

### 2. 新增辅助方法

#### TestCase 类新增方法

```python
# 中间步骤相关
def has_intermediate_expectations(self) -> bool
def get_intermediate_expectation(self, step_id: str) -> Optional[Dict[str, Any]]

# 评估配置相关
def should_evaluate_intermediate(self) -> bool
def should_evaluate_final(self) -> bool
def should_evaluate_aggregation(self) -> bool
def is_strict_mode(self) -> bool
def get_tolerance(self) -> float
def get_ignore_fields(self) -> List[str]

# Pipeline 结构相关
def get_all_step_ids(self) -> List[str]
def get_batch_size(self) -> int
```

#### TestsetLoader 类新增方法

```python
# 过滤和查询
@staticmethod
def get_intermediate_evaluation_test_cases(test_cases: List[TestCase]) -> List[TestCase]

# 数据提取和组织
@staticmethod
def extract_step_data(test_case: TestCase, step_id: str) -> Dict[str, Any]

@staticmethod
def organize_batch_data(test_cases: List[TestCase]) -> Dict[str, Any]

# Pipeline 结构分析
@staticmethod
def get_pipeline_structure(test_cases: List[TestCase]) -> Dict[str, Any]

@staticmethod
def group_by_pipeline_features(test_cases: List[TestCase]) -> Dict[str, List[TestCase]]
```

### 3. 增强的验证功能

更新了 `validate_testset` 方法，新增对以下内容的验证：

- **intermediate_expectations 格式验证**: 确保是字典类型，且每个步骤的预期也是字典
- **evaluation_config 格式验证**: 确保是字典类型

### 4. 完整的测试覆盖

创建了 `tests/test_testset_loader_pipeline.py`，包含 20 个测试用例：

#### TestPipelineTestCase (7 个测试)
- ✅ 测试加载包含中间步骤预期的测试用例
- ✅ 测试加载包含评估配置的测试用例
- ✅ 测试评估配置的默认值
- ✅ 测试聚合评估判断逻辑
- ✅ 测试获取所有步骤 ID
- ✅ 测试获取批量数据大小
- ✅ 测试包含新字段的序列化

#### TestPipelineTestsetLoader (8 个测试)
- ✅ 测试加载多步骤测试集
- ✅ 测试获取需要中间步骤评估的测试用例
- ✅ 测试提取步骤数据
- ✅ 测试组织批量数据
- ✅ 测试分析 Pipeline 结构
- ✅ 测试按 Pipeline 特性分组
- ✅ 测试验证中间步骤预期格式
- ✅ 测试验证评估配置格式

#### TestRealWorldPipelineExamples (4 个测试)
- ✅ 测试加载多步骤 Pipeline 示例
- ✅ 测试加载批量聚合 Pipeline 示例
- ✅ 测试加载中间步骤评估示例
- ✅ 测试加载复杂场景示例

#### TestPipelineIntegration (1 个测试)
- ✅ 测试完整的 Pipeline 工作流

## 功能特性

### 1. Pipeline 测试集解析

支持解析包含以下字段的 Pipeline 测试集：

```jsonl
{
  "id": "test_1",
  "inputs": {"text": "input"},
  "step_inputs": {
    "step1": {"param": "value1"},
    "step2": {"param": "value2"}
  },
  "intermediate_expectations": {
    "step1": {"output": "result1"}
  },
  "evaluation_config": {
    "evaluate_intermediate": true,
    "strict_mode": false,
    "tolerance": 0.01
  },
  "expected_outputs": {"result": "output"}
}
```

### 2. 步骤级数据提取

使用 `extract_step_data` 方法可以提取特定步骤的所有相关数据：

```python
step_data = TestsetLoader.extract_step_data(test_case, 'step1')
# 返回: {
#   'inputs': {...},      # 步骤输入
#   'expected': {...}     # 步骤预期输出
# }
```

### 3. 批量数据组织

使用 `organize_batch_data` 方法可以组织和分析批量测试数据：

```python
batch_info = TestsetLoader.organize_batch_data(test_cases)
# 返回: {
#   'total_test_cases': 5,
#   'total_batch_items': 50,
#   'average_batch_size': 10.0,
#   'test_cases': [...]
# }
```

### 4. Pipeline 结构分析

使用 `get_pipeline_structure` 方法可以分析测试集中的 Pipeline 结构：

```python
structure = TestsetLoader.get_pipeline_structure(test_cases)
# 返回: {
#   'total_steps': 5,
#   'all_step_ids': ['step1', 'step2', ...],
#   'steps_with_inputs': ['step1', 'step2'],
#   'steps_with_expectations': ['step1'],
#   'has_batch_processing': True,
#   'has_intermediate_evaluation': True
# }
```

### 5. 按特性分组

使用 `group_by_pipeline_features` 方法可以按 Pipeline 特性对测试用例分组：

```python
groups = TestsetLoader.group_by_pipeline_features(test_cases)
# 返回: {
#   'simple': [...],                    # 简单测试用例
#   'multi_step': [...],                # 多步骤测试用例
#   'batch_processing': [...],          # 批量处理测试用例
#   'intermediate_evaluation': [...],   # 中间步骤评估测试用例
#   'complex': [...]                    # 复杂测试用例（包含多个特性）
# }
```

## 测试结果

### 所有测试通过

```bash
$ python -m pytest tests/test_testset_loader.py tests/test_testset_loader_pipeline.py -v

================================ test session starts ================================
collected 51 items

tests/test_testset_loader.py::TestTestCase::test_from_dict_simple PASSED      [  1%]
tests/test_testset_loader.py::TestTestCase::test_from_dict_explicit_inputs PASSED [  3%]
# ... (省略中间输出) ...
tests/test_testset_loader_pipeline.py::TestPipelineIntegration::test_complete_pipeline_workflow PASSED [100%]

================================ 51 passed in 0.56s =================================
```

- ✅ 原有 31 个测试全部通过（向后兼容）
- ✅ 新增 20 个 Pipeline 测试全部通过
- ✅ 总计 51 个测试，100% 通过率

## 向后兼容性

所有更改都保持了向后兼容性：

1. **现有字段**: 所有现有字段和方法保持不变
2. **新字段可选**: 新增的 `intermediate_expectations` 和 `evaluation_config` 字段都是可选的
3. **默认行为**: 如果不提供新字段，系统行为与之前完全一致
4. **现有测试**: 所有 31 个现有测试继续通过

## 使用示例

### 示例 1: 加载多步骤测试集

```python
from src.testset_loader import load_testset, TestsetLoader

# 加载测试集
test_cases = load_testset('examples/testsets/pipeline_multi_step_examples.jsonl')

# 获取需要中间步骤评估的测试用例
intermediate_cases = TestsetLoader.get_intermediate_evaluation_test_cases(test_cases)

for tc in intermediate_cases:
    print(f"Test: {tc.id}")
    print(f"  Should evaluate intermediate: {tc.should_evaluate_intermediate()}")
    print(f"  Steps with expectations: {list(tc.intermediate_expectations.keys())}")
```

### 示例 2: 提取步骤数据

```python
from src.testset_loader import load_testset, TestsetLoader

test_cases = load_testset('testset.jsonl')
tc = test_cases[0]

# 提取特定步骤的数据
step_data = TestsetLoader.extract_step_data(tc, 'preprocess')

if 'inputs' in step_data:
    print(f"Step inputs: {step_data['inputs']}")

if 'expected' in step_data:
    print(f"Expected output: {step_data['expected']}")
```

### 示例 3: 分析 Pipeline 结构

```python
from src.testset_loader import load_testset, TestsetLoader

test_cases = load_testset('testset.jsonl')

# 分析 Pipeline 结构
structure = TestsetLoader.get_pipeline_structure(test_cases)

print(f"Total steps: {structure['total_steps']}")
print(f"All step IDs: {structure['all_step_ids']}")
print(f"Has batch processing: {structure['has_batch_processing']}")
print(f"Has intermediate evaluation: {structure['has_intermediate_evaluation']}")
```

### 示例 4: 按特性分组

```python
from src.testset_loader import load_testset, TestsetLoader

test_cases = load_testset('testset.jsonl')

# 按特性分组
groups = TestsetLoader.group_by_pipeline_features(test_cases)

print(f"Simple tests: {len(groups['simple'])}")
print(f"Multi-step tests: {len(groups['multi_step'])}")
print(f"Batch processing tests: {len(groups['batch_processing'])}")
print(f"Complex tests: {len(groups['complex'])}")
```

## 相关文件

### 修改的文件
- `src/testset_loader.py`: 更新 TestCase 和 TestsetLoader 类

### 新增的文件
- `tests/test_testset_loader_pipeline.py`: Pipeline 级别测试集的测试

### 相关文档
- `docs/reference/pipeline-testset-format-specification.md`: Pipeline 测试集格式规范
- `docs/reference/testset-loader-quick-reference.md`: 测试集加载器快速参考

### 示例文件
- `examples/testsets/pipeline_multi_step_examples.jsonl`: 多步骤示例
- `examples/testsets/pipeline_batch_aggregation_examples.jsonl`: 批量聚合示例
- `examples/testsets/pipeline_intermediate_evaluation_examples.jsonl`: 中间步骤评估示例
- `examples/testsets/pipeline_complex_scenarios.jsonl`: 复杂场景示例

## 下一步

Task 87 已完成。根据任务列表，下一个任务是：

- **Task 88**: 实现 Pipeline 评估支持
  - 实现最终输出评估
  - 实现中间步骤评估
  - 实现批量聚合结果评估
  - 集成到 unified_evaluator

测试集加载器现在已经完全支持 Pipeline 级别的测试集格式，可以为后续的 Pipeline 评估功能提供完整的数据支持。

## 总结

Task 87 成功完成，实现了以下目标：

✅ **Pipeline 测试集解析**: 支持解析包含多步骤、批量处理、中间步骤评估等复杂特性的测试集
✅ **步骤级数据提取**: 提供便捷的方法提取特定步骤的输入和预期输出
✅ **批量数据组织**: 提供批量数据的组织和统计功能
✅ **Pipeline 结构分析**: 提供 Pipeline 结构的分析和分组功能
✅ **完整的测试覆盖**: 20 个新测试 + 31 个现有测试，100% 通过率
✅ **向后兼容**: 所有现有功能保持不变，新功能完全可选

测试集加载器现在已经为 Phase 7 的 Pipeline 测试集架构升级提供了坚实的基础。
