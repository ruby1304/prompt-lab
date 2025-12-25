# Testset Property Tests Quick Reference

## Overview
Property-based tests for pipeline testset parsing using Hypothesis.

## Test File
- **Location**: `tests/test_testset_properties.py`
- **Framework**: pytest + Hypothesis
- **Iterations**: 100 examples per test

## Property 27: Multi-step testset parsing

**Validates**: Requirements 5.1

**Property Statement**: For any pipeline testset with step-specific test data, the system should correctly parse and associate data with steps.

### Test Functions

#### 1. Core Parsing Test
```python
test_property_27_multi_step_testset_parsing(test_data)
```
**Verifies**:
- TestCase correctly parses `step_inputs` from dictionary
- TestCase correctly parses `intermediate_expectations` from dictionary
- All step IDs are correctly identified
- Step-specific data can be extracted for each step
- Round-trip serialization preserves data

#### 2. File Loading Test
```python
test_property_27_multi_step_testset_file_parsing(test_data_list, tmp_path)
```
**Verifies**:
- All test cases are loaded from JSONL files
- Each test case preserves its step-specific data
- Pipeline structure analysis correctly identifies all steps
- Grouping by features correctly categorizes test cases

#### 3. Data Extraction Test
```python
test_property_27_step_data_extraction_consistency(test_data, query_step_id)
```
**Verifies**:
- If a step has inputs, `extract_step_data` returns them
- If a step has expectations, `extract_step_data` returns them
- If a step doesn't exist, `extract_step_data` returns empty dict
- Extracted data structure is always consistent

#### 4. Filtering Test
```python
test_property_27_intermediate_evaluation_filtering(test_data_list)
```
**Verifies**:
- All returned test cases have `intermediate_expectations`
- All test cases with `intermediate_expectations` are returned
- The count matches the expected count

#### 5. Validation Test
```python
test_property_27_validation_accepts_valid_testcases(test_data)
```
**Verifies**:
- Well-formed `step_inputs` pass validation
- Well-formed `intermediate_expectations` pass validation
- No false positive validation errors

## Running Tests

### Run all testset property tests
```bash
pytest tests/test_testset_properties.py -v
```

### Run specific property test
```bash
pytest tests/test_testset_properties.py::test_property_27_multi_step_testset_parsing -v
```

### Run with verbose Hypothesis output
```bash
pytest tests/test_testset_properties.py -v --hypothesis-show-statistics
```

## Hypothesis Strategies

### Custom Strategies
1. **`step_id_strategy`**: Generates valid step IDs (alphanumeric, lowercase)
2. **`step_inputs_strategy`**: Generates step_inputs with 1-5 steps
3. **`intermediate_expectations_strategy`**: Generates expectations for subset of steps
4. **`testcase_with_step_data_strategy`**: Generates complete TestCase with all fields
5. **`simple_testcase_strategy`**: Generates simple test cases for batch testing
6. **`testcase_with_final_output_strategy`**: Generates test cases with expected final outputs

### Generated Data Types
- **Step IDs**: Lowercase alphanumeric strings (1-20 chars)
- **Input Values**: Strings, integers, floats, booleans
- **Number of Steps**: 1-5 steps per test case
- **Parameters per Step**: 1-5 parameters
- **Expected Outputs**: 1-5 output fields with various data types
- **Batch Sizes**: 1-10 test cases per batch

## Test Configuration

```python
@settings(max_examples=100, deadline=None)
```

- **max_examples**: 100 iterations per test
- **deadline**: None (allows complex generation)
- **suppress_health_check**: `function_scoped_fixture` for file tests

## Expected Results

All tests should pass with 100 examples each:
```
tests/test_testset_properties.py::test_property_27_multi_step_testset_parsing PASSED
tests/test_testset_properties.py::test_property_27_multi_step_testset_file_parsing PASSED
tests/test_testset_properties.py::test_property_27_step_data_extraction_consistency PASSED
tests/test_testset_properties.py::test_property_27_intermediate_evaluation_filtering PASSED
tests/test_testset_properties.py::test_property_27_validation_accepts_valid_testcases PASSED
tests/test_testset_properties.py::test_property_28_batch_test_execution PASSED
tests/test_testset_properties.py::test_property_28_batch_size_handling PASSED
tests/test_testset_properties.py::test_property_28_result_aggregation_consistency PASSED
tests/test_testset_properties.py::test_property_29_final_output_evaluation PASSED
tests/test_testset_properties.py::test_property_29_final_output_evaluation_batch PASSED
tests/test_testset_properties.py::test_property_29_final_output_field_evaluation PASSED
tests/test_testset_properties.py::test_property_29_final_output_evaluation_consistency PASSED

12 passed in ~32s
```

## Key Assertions

### Parsing Assertions
```python
assert tc.has_step_inputs() == bool(test_data.get('step_inputs'))
assert tc.has_intermediate_expectations() == bool(test_data.get('intermediate_expectations'))
```

### Data Association Assertions
```python
assert tc.step_inputs[step_id] == test_data['step_inputs'][step_id]
assert tc.get_intermediate_expectation(step_id) == test_data['intermediate_expectations'][step_id]
```

### Round-Trip Assertions
```python
serialized = tc.to_dict()
tc_roundtrip = TestCase.from_dict(serialized)
assert tc_roundtrip.step_inputs == tc.step_inputs
```

## Troubleshooting

### Test Failures
If a property test fails, Hypothesis will provide:
1. The failing example (minimal counterexample)
2. The assertion that failed
3. Steps to reproduce

### Common Issues
1. **Strategy generates invalid data**: Adjust strategy constraints
2. **Timeout**: Increase deadline or simplify generation
3. **Flaky tests**: Check for non-deterministic behavior

## Related Documentation
- [Testset Loader Guide](./testset-loader-quick-reference.md)
- [Pipeline Testset Format](./pipeline-testset-format-specification.md)
- [Property-Based Testing Guide](../../docs/guides/property-based-testing.md)

## Property 28: Batch test execution

**Validates**: Requirements 5.2

**Property Statement**: For any pipeline testset with multiple test cases, the system should execute all cases and aggregate results.

### Test Functions

#### 1. Batch Execution Test
```python
test_property_28_batch_test_execution(test_data_list, tmp_path)
```
**Verifies**:
- All test cases are loaded from the testset file
- The system can process multiple test cases in batch
- Results are collected for all test cases
- The number of results matches the number of input test cases
- Each test case maintains its unique identity through the batch process
- Aggregated statistics are computed correctly

#### 2. Batch Size Handling Test
```python
test_property_28_batch_size_handling(test_data_list, batch_size)
```
**Verifies**:
- Batch processing works with any valid batch size
- All test cases are processed regardless of batch size
- Results are complete even when batch size doesn't divide evenly
- No test cases are lost or duplicated

#### 3. Result Aggregation Test
```python
test_property_28_result_aggregation_consistency(test_data_list)
```
**Verifies**:
- Aggregation produces consistent counts
- Aggregation statistics are deterministic
- Different aggregation methods produce the same results
- Aggregation handles empty results correctly

## Property 29: Final output evaluation

**Validates**: Requirements 5.3

**Property Statement**: For any pipeline execution result, the system should support evaluating the final output against expected values.

### Test Functions

#### 1. Core Evaluation Test
```python
test_property_29_final_output_evaluation(test_data)
```
**Verifies**:
- Test cases with expected_outputs can be parsed correctly
- Expected outputs are accessible for evaluation
- The system can compare actual outputs against expected outputs
- Evaluation results indicate whether outputs match expectations
- Multiple expected output fields are all evaluated
- Overall evaluation reflects individual field results

#### 2. Batch Evaluation Test
```python
test_property_29_final_output_evaluation_batch(test_data_list, tmp_path)
```
**Verifies**:
- Multiple test cases can be evaluated in batch
- Each test case's final output is evaluated independently
- Evaluation results are aggregated correctly
- Pass/fail statistics are computed correctly
- All expected output fields are evaluated for each test case

#### 3. Field Evaluation Test
```python
test_property_29_final_output_field_evaluation(test_data, output_key)
```
**Verifies**:
- Individual output fields can be evaluated independently
- Evaluation handles missing fields correctly
- Evaluation handles type mismatches correctly
- Evaluation is deterministic
- Exact matches return True, different values return False

#### 4. Consistency Test
```python
test_property_29_final_output_evaluation_consistency(test_data)
```
**Verifies**:
- Evaluation is deterministic
- Multiple evaluations produce the same result
- Evaluation order doesn't affect results
- Overall result is consistent across multiple evaluations

## Design Document Reference

### Property 27
- **Property**: Property 27: Multi-step testset parsing
- **Requirement**: 5.1 - Pipeline 级别的测试集支持
- **Acceptance Criteria**: WHEN 定义 Pipeline 测试集时 THEN the System SHALL 支持为不同步骤定义不同的测试数据

### Property 28
- **Property**: Property 28: Batch test execution
- **Requirement**: 5.2 - Pipeline 级别的测试集支持
- **Acceptance Criteria**: WHEN 执行 Pipeline 测试时 THEN the System SHALL 支持批量执行多个测试用例并聚合结果

### Property 29
- **Property**: Property 29: Final output evaluation
- **Requirement**: 5.3 - Pipeline 级别的测试集支持
- **Acceptance Criteria**: WHEN 评估 Pipeline 时 THEN the System SHALL 支持对整个 Pipeline 的最终输出进行评估
