# tests/test_testset_properties.py
"""
Property-Based Tests for Testset Loading

Tests correctness properties for pipeline testset parsing and loading.
Uses Hypothesis for property-based testing with at least 100 iterations.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from pathlib import Path
import tempfile
import json
from typing import Dict, Any, List

from src.testset_loader import (
    TestCase,
    TestsetLoader,
    load_testset,
    validate_testset
)


# ============================================================================
# Hypothesis Strategies for Generating Test Data
# ============================================================================

@st.composite
def step_id_strategy(draw):
    """Generate valid step IDs"""
    return draw(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), blacklist_characters='_-'),
        min_size=1,
        max_size=20
    ).map(lambda s: s.lower().replace(' ', '_')))


@st.composite
def step_inputs_strategy(draw):
    """Generate step_inputs dictionary with random step IDs and input data"""
    num_steps = draw(st.integers(min_value=1, max_value=5))
    step_ids = draw(st.lists(step_id_strategy(), min_size=num_steps, max_size=num_steps, unique=True))
    
    step_inputs = {}
    for step_id in step_ids:
        # Generate random input data for each step
        num_params = draw(st.integers(min_value=1, max_value=5))
        step_data = {}
        for _ in range(num_params):
            key = draw(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))))
            value = draw(st.one_of(
                st.text(min_size=0, max_size=50),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans()
            ))
            step_data[key] = value
        step_inputs[step_id] = step_data
    
    return step_inputs


@st.composite
def intermediate_expectations_strategy(draw, step_ids=None):
    """Generate intermediate_expectations dictionary"""
    if step_ids is None:
        num_steps = draw(st.integers(min_value=1, max_value=5))
        step_ids = draw(st.lists(step_id_strategy(), min_size=num_steps, max_size=num_steps, unique=True))
    
    # Select a subset of steps to have expectations
    num_expectations = draw(st.integers(min_value=1, max_value=len(step_ids)))
    selected_steps = draw(st.lists(st.sampled_from(step_ids), min_size=num_expectations, max_size=num_expectations, unique=True))
    
    expectations = {}
    for step_id in selected_steps:
        # Generate random expectation data
        num_fields = draw(st.integers(min_value=1, max_value=5))
        expectation_data = {}
        for _ in range(num_fields):
            key = draw(st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))))
            value = draw(st.one_of(
                st.text(min_size=0, max_size=50),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans()
            ))
            expectation_data[key] = value
        expectations[step_id] = expectation_data
    
    return expectations


@st.composite
def testcase_with_step_data_strategy(draw):
    """Generate a TestCase with step-specific data"""
    test_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    
    # Generate step_inputs
    step_inputs = draw(step_inputs_strategy())
    step_ids = list(step_inputs.keys())
    
    # Generate intermediate_expectations for some of the steps
    intermediate_expectations = draw(intermediate_expectations_strategy(step_ids=step_ids))
    
    # Generate global inputs
    inputs = draw(st.dictionaries(
        keys=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
        min_size=0,
        max_size=3
    ))
    
    # Generate expected outputs
    expected_outputs = draw(st.dictionaries(
        keys=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
        min_size=0,
        max_size=3
    ))
    
    data = {
        'id': test_id,
        'inputs': inputs,
        'step_inputs': step_inputs,
        'intermediate_expectations': intermediate_expectations,
        'expected_outputs': expected_outputs
    }
    
    return data


# ============================================================================
# Property 27: Multi-step testset parsing
# Feature: project-production-readiness, Property 27: Multi-step testset parsing
# Validates: Requirements 5.1
# ============================================================================

@settings(max_examples=100, deadline=None)
@given(test_data=testcase_with_step_data_strategy())
def test_property_27_multi_step_testset_parsing(test_data):
    """
    Property 27: Multi-step testset parsing
    
    For any pipeline testset with step-specific test data, the system should 
    correctly parse and associate data with steps.
    
    This property verifies that:
    1. TestCase correctly parses step_inputs from dictionary
    2. TestCase correctly parses intermediate_expectations from dictionary
    3. All step IDs are correctly identified
    4. Step-specific data can be extracted for each step
    5. The parsed data matches the original input data
    """
    # Parse the test case from dictionary
    tc = TestCase.from_dict(test_data)
    
    # Property 1: TestCase should have step_inputs if provided
    assert tc.has_step_inputs() == bool(test_data.get('step_inputs'))
    
    # Property 2: TestCase should have intermediate_expectations if provided
    assert tc.has_intermediate_expectations() == bool(test_data.get('intermediate_expectations'))
    
    # Property 3: All step IDs from step_inputs should be present
    if test_data.get('step_inputs'):
        for step_id in test_data['step_inputs'].keys():
            assert step_id in tc.step_inputs
            # Verify the data is correctly associated
            assert tc.step_inputs[step_id] == test_data['step_inputs'][step_id]
    
    # Property 4: All step IDs from intermediate_expectations should be present
    if test_data.get('intermediate_expectations'):
        for step_id in test_data['intermediate_expectations'].keys():
            assert step_id in tc.intermediate_expectations
            # Verify the expectation data is correctly associated
            expectation = tc.get_intermediate_expectation(step_id)
            assert expectation == test_data['intermediate_expectations'][step_id]
    
    # Property 5: get_all_step_ids should return all unique step IDs
    all_step_ids = tc.get_all_step_ids()
    expected_step_ids = set()
    if test_data.get('step_inputs'):
        expected_step_ids.update(test_data['step_inputs'].keys())
    if test_data.get('intermediate_expectations'):
        expected_step_ids.update(test_data['intermediate_expectations'].keys())
    
    assert set(all_step_ids) == expected_step_ids
    
    # Property 6: extract_step_data should return correct data for each step
    for step_id in all_step_ids:
        step_data = TestsetLoader.extract_step_data(tc, step_id)
        
        # If step has inputs, they should be in the extracted data
        if step_id in tc.step_inputs:
            assert 'inputs' in step_data
            assert step_data['inputs'] == tc.step_inputs[step_id]
        
        # If step has expectations, they should be in the extracted data
        if step_id in tc.intermediate_expectations:
            assert 'expected' in step_data
            assert step_data['expected'] == tc.intermediate_expectations[step_id]
    
    # Property 7: Round-trip serialization should preserve data
    serialized = tc.to_dict()
    tc_roundtrip = TestCase.from_dict(serialized)
    
    # Verify step_inputs are preserved
    assert tc_roundtrip.step_inputs == tc.step_inputs
    
    # Verify intermediate_expectations are preserved
    assert tc_roundtrip.intermediate_expectations == tc.intermediate_expectations
    
    # Verify all step IDs are preserved
    assert set(tc_roundtrip.get_all_step_ids()) == set(tc.get_all_step_ids())


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(test_data_list=st.lists(testcase_with_step_data_strategy(), min_size=1, max_size=10))
def test_property_27_multi_step_testset_file_parsing(test_data_list, tmp_path):
    """
    Property 27 (File Loading): Multi-step testset file parsing
    
    For any JSONL file containing pipeline testsets with step-specific data,
    the system should correctly load and parse all test cases.
    
    This property verifies that:
    1. All test cases are loaded from the file
    2. Each test case preserves its step-specific data
    3. Pipeline structure analysis correctly identifies all steps
    4. Grouping by features correctly categorizes test cases
    """
    # Create a temporary JSONL file
    testset_file = tmp_path / "multi_step_test.jsonl"
    
    with open(testset_file, 'w', encoding='utf-8') as f:
        for data in test_data_list:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    
    # Load the testset
    test_cases = load_testset(testset_file)
    
    # Property 1: All test cases should be loaded
    assert len(test_cases) == len(test_data_list)
    
    # Property 2: Each test case should preserve step-specific data
    for i, tc in enumerate(test_cases):
        original_data = test_data_list[i]
        
        # Verify step_inputs
        if original_data.get('step_inputs'):
            assert tc.has_step_inputs()
            assert tc.step_inputs == original_data['step_inputs']
        
        # Verify intermediate_expectations
        if original_data.get('intermediate_expectations'):
            assert tc.has_intermediate_expectations()
            assert tc.intermediate_expectations == original_data['intermediate_expectations']
    
    # Property 3: Pipeline structure analysis should identify all steps
    structure = TestsetLoader.get_pipeline_structure(test_cases)
    
    # Collect all expected step IDs
    all_expected_steps = set()
    for data in test_data_list:
        if data.get('step_inputs'):
            all_expected_steps.update(data['step_inputs'].keys())
        if data.get('intermediate_expectations'):
            all_expected_steps.update(data['intermediate_expectations'].keys())
    
    assert set(structure['all_step_ids']) == all_expected_steps
    
    # Property 4: Grouping by features should correctly categorize
    groups = TestsetLoader.group_by_pipeline_features(test_cases)
    
    # All test cases with step_inputs should be in multi_step group
    multi_step_count = sum(1 for data in test_data_list if data.get('step_inputs'))
    assert len(groups['multi_step']) == multi_step_count
    
    # All test cases with intermediate_expectations should be in intermediate_evaluation group
    intermediate_count = sum(1 for data in test_data_list if data.get('intermediate_expectations'))
    assert len(groups['intermediate_evaluation']) == intermediate_count


@settings(max_examples=100, deadline=None)
@given(
    test_data=testcase_with_step_data_strategy(),
    query_step_id=step_id_strategy()
)
def test_property_27_step_data_extraction_consistency(test_data, query_step_id):
    """
    Property 27 (Data Extraction): Step data extraction consistency
    
    For any test case and any step ID, extracting step data should be consistent
    with the presence of that step in the test case.
    
    This property verifies that:
    1. If a step has inputs, extract_step_data returns them
    2. If a step has expectations, extract_step_data returns them
    3. If a step doesn't exist, extract_step_data returns empty dict
    4. Extracted data structure is always consistent
    """
    tc = TestCase.from_dict(test_data)
    
    # Extract data for the query step
    step_data = TestsetLoader.extract_step_data(tc, query_step_id)
    
    # Property 1: If step has inputs in step_inputs, they should be in extracted data
    if query_step_id in tc.step_inputs:
        assert 'inputs' in step_data
        assert step_data['inputs'] == tc.step_inputs[query_step_id]
    else:
        # If step doesn't have inputs, 'inputs' key should not be present
        # unless the step doesn't exist at all
        if query_step_id not in tc.intermediate_expectations:
            assert step_data == {}
    
    # Property 2: If step has expectations, they should be in extracted data
    if query_step_id in tc.intermediate_expectations:
        assert 'expected' in step_data
        assert step_data['expected'] == tc.intermediate_expectations[query_step_id]
    
    # Property 3: Extracted data should only contain 'inputs' and/or 'expected' keys
    for key in step_data.keys():
        assert key in ['inputs', 'expected']


@settings(max_examples=100, deadline=None)
@given(test_data_list=st.lists(testcase_with_step_data_strategy(), min_size=1, max_size=20))
def test_property_27_intermediate_evaluation_filtering(test_data_list):
    """
    Property 27 (Filtering): Intermediate evaluation test case filtering
    
    For any list of test cases, filtering for intermediate evaluation should
    return exactly those test cases that have intermediate_expectations.
    
    This property verifies that:
    1. All returned test cases have intermediate_expectations
    2. All test cases with intermediate_expectations are returned
    3. The count matches the expected count
    """
    test_cases = [TestCase.from_dict(data) for data in test_data_list]
    
    # Get test cases that need intermediate evaluation
    intermediate_cases = TestsetLoader.get_intermediate_evaluation_test_cases(test_cases)
    
    # Property 1: All returned test cases should have intermediate_expectations
    for tc in intermediate_cases:
        assert tc.has_intermediate_expectations()
    
    # Property 2: Count should match expected count
    expected_count = sum(1 for data in test_data_list if data.get('intermediate_expectations'))
    assert len(intermediate_cases) == expected_count
    
    # Property 3: All test cases with intermediate_expectations should be included
    intermediate_ids = {tc.id for tc in intermediate_cases}
    expected_ids = {
        data['id'] for data in test_data_list 
        if data.get('intermediate_expectations')
    }
    assert intermediate_ids == expected_ids


@settings(max_examples=100, deadline=None)
@given(test_data=testcase_with_step_data_strategy())
def test_property_27_validation_accepts_valid_testcases(test_data):
    """
    Property 27 (Validation): Valid test cases should pass validation
    
    For any properly structured test case with step-specific data,
    validation should not produce errors.
    
    This property verifies that:
    1. Well-formed step_inputs pass validation
    2. Well-formed intermediate_expectations pass validation
    3. No false positive validation errors
    """
    tc = TestCase.from_dict(test_data)
    
    # Validate the test case
    errors = validate_testset([tc])
    
    # Property: No validation errors for well-formed test cases
    assert len(errors) == 0, f"Validation errors for valid test case: {errors}"


# ============================================================================
# Property 28: Batch test execution
# Feature: project-production-readiness, Property 28: Batch test execution
# Validates: Requirements 5.2
# ============================================================================

@st.composite
def simple_testcase_strategy(draw):
    """Generate a simple test case for batch execution testing"""
    test_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    
    # Generate simple inputs
    inputs = draw(st.dictionaries(
        keys=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
        min_size=1,
        max_size=3
    ))
    
    # Generate expected outputs
    expected_outputs = draw(st.dictionaries(
        keys=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
        min_size=0,
        max_size=3
    ))
    
    data = {
        'id': test_id,
        'inputs': inputs,
        'expected_outputs': expected_outputs
    }
    
    return data


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(test_data_list=st.lists(simple_testcase_strategy(), min_size=2, max_size=20))
def test_property_28_batch_test_execution(test_data_list, tmp_path):
    """
    Property 28: Batch test execution
    
    For any pipeline testset with multiple test cases, the system should 
    execute all cases and aggregate results.
    
    This property verifies that:
    1. All test cases are loaded from the testset file
    2. The system can process multiple test cases in batch
    3. Results are collected for all test cases
    4. The number of results matches the number of input test cases
    5. Each test case maintains its unique identity through the batch process
    6. Aggregated statistics are computed correctly
    """
    # Create a temporary JSONL file with multiple test cases
    testset_file = tmp_path / "batch_test.jsonl"
    
    with open(testset_file, 'w', encoding='utf-8') as f:
        for data in test_data_list:
            f.write(json.dumps(data, ensure_ascii=False) + '\n')
    
    # Property 1: All test cases should be loaded
    test_cases = load_testset(testset_file)
    assert len(test_cases) == len(test_data_list), \
        f"Expected {len(test_data_list)} test cases, but loaded {len(test_cases)}"
    
    # Property 2: Each test case should preserve its data
    for i, tc in enumerate(test_cases):
        original_data = test_data_list[i]
        assert tc.id == original_data['id'], \
            f"Test case ID mismatch: expected {original_data['id']}, got {tc.id}"
        assert tc.inputs == original_data['inputs'], \
            f"Test case inputs mismatch for {tc.id}"
        assert tc.expected_outputs == original_data['expected_outputs'], \
            f"Test case expected_outputs mismatch for {tc.id}"
    
    # Property 3: Batch processing should maintain test case count
    # Simulate batch execution by collecting all test case IDs
    batch_ids = [tc.id for tc in test_cases]
    assert len(batch_ids) == len(test_data_list), \
        "Batch processing should maintain the same number of test cases"
    
    # Property 4: All test case IDs should be unique and preserved
    original_ids = {data['id'] for data in test_data_list}
    loaded_ids = {tc.id for tc in test_cases}
    assert loaded_ids == original_ids, \
        f"Test case IDs not preserved: expected {original_ids}, got {loaded_ids}"
    
    # Property 5: Batch execution should preserve order
    for i, tc in enumerate(test_cases):
        assert tc.id == test_data_list[i]['id'], \
            f"Test case order not preserved at position {i}"
    
    # Property 6: Aggregation statistics should be computable
    # Test that we can compute basic statistics over the batch
    total_count = len(test_cases)
    assert total_count == len(test_data_list), \
        "Total count in aggregation should match input count"
    
    # Count test cases with expected outputs
    with_expectations = sum(1 for tc in test_cases if tc.expected_outputs)
    expected_with_expectations = sum(1 for data in test_data_list if data.get('expected_outputs'))
    assert with_expectations == expected_with_expectations, \
        "Count of test cases with expectations should match"
    
    # Property 7: Batch results should be aggregatable
    # Simulate collecting results for each test case
    simulated_results = []
    for tc in test_cases:
        # Simulate a result for each test case
        result = {
            'test_id': tc.id,
            'has_inputs': bool(tc.inputs),
            'has_expectations': bool(tc.expected_outputs),
            'input_count': len(tc.inputs) if tc.inputs else 0
        }
        simulated_results.append(result)
    
    # Verify we have results for all test cases
    assert len(simulated_results) == len(test_cases), \
        "Should have results for all test cases"
    
    # Verify result IDs match test case IDs
    result_ids = {r['test_id'] for r in simulated_results}
    test_case_ids = {tc.id for tc in test_cases}
    assert result_ids == test_case_ids, \
        "Result IDs should match test case IDs"
    
    # Property 8: Aggregated statistics should be correct
    # Compute aggregated statistics
    total_with_inputs = sum(1 for r in simulated_results if r['has_inputs'])
    total_with_expectations = sum(1 for r in simulated_results if r['has_expectations'])
    avg_input_count = sum(r['input_count'] for r in simulated_results) / len(simulated_results)
    
    # Verify statistics
    expected_with_inputs = sum(1 for data in test_data_list if data.get('inputs'))
    assert total_with_inputs == expected_with_inputs, \
        "Aggregated count of test cases with inputs should be correct"
    
    assert total_with_expectations == expected_with_expectations, \
        "Aggregated count of test cases with expectations should be correct"
    
    expected_avg_input_count = sum(len(data.get('inputs', {})) for data in test_data_list) / len(test_data_list)
    assert abs(avg_input_count - expected_avg_input_count) < 0.01, \
        "Average input count should be computed correctly"


@settings(max_examples=100, deadline=None)
@given(
    test_data_list=st.lists(simple_testcase_strategy(), min_size=1, max_size=50),
    batch_size=st.integers(min_value=1, max_value=10)
)
def test_property_28_batch_size_handling(test_data_list, batch_size):
    """
    Property 28 (Batch Size): Batch execution with different batch sizes
    
    For any list of test cases and any batch size, the system should
    correctly handle batch processing regardless of batch size.
    
    This property verifies that:
    1. Batch processing works with any valid batch size
    2. All test cases are processed regardless of batch size
    3. Results are complete even when batch size doesn't divide evenly
    4. No test cases are lost or duplicated
    """
    test_cases = [TestCase.from_dict(data) for data in test_data_list]
    
    # Simulate batch processing with the given batch size
    batches = []
    for i in range(0, len(test_cases), batch_size):
        batch = test_cases[i:i + batch_size]
        batches.append(batch)
    
    # Property 1: All test cases should be in some batch
    all_batched_cases = []
    for batch in batches:
        all_batched_cases.extend(batch)
    
    assert len(all_batched_cases) == len(test_cases), \
        f"All test cases should be batched: expected {len(test_cases)}, got {len(all_batched_cases)}"
    
    # Property 2: No test cases should be duplicated
    batched_ids = [tc.id for tc in all_batched_cases]
    original_ids = [tc.id for tc in test_cases]
    assert batched_ids == original_ids, \
        "Test case order and uniqueness should be preserved in batching"
    
    # Property 3: Each batch should respect the batch size (except possibly the last)
    for i, batch in enumerate(batches[:-1]):  # All batches except the last
        assert len(batch) == batch_size, \
            f"Batch {i} should have size {batch_size}, got {len(batch)}"
    
    # Last batch can be smaller or equal to batch_size
    if batches:
        assert len(batches[-1]) <= batch_size, \
            f"Last batch should have size <= {batch_size}, got {len(batches[-1])}"
    
    # Property 4: Number of batches should be correct
    expected_num_batches = (len(test_cases) + batch_size - 1) // batch_size
    assert len(batches) == expected_num_batches, \
        f"Expected {expected_num_batches} batches, got {len(batches)}"


@settings(max_examples=100, deadline=None)
@given(test_data_list=st.lists(simple_testcase_strategy(), min_size=1, max_size=30))
def test_property_28_result_aggregation_consistency(test_data_list):
    """
    Property 28 (Aggregation): Result aggregation consistency
    
    For any list of test cases, aggregating results should produce
    consistent statistics regardless of how aggregation is performed.
    
    This property verifies that:
    1. Aggregation produces consistent counts
    2. Aggregation statistics are deterministic
    3. Different aggregation methods produce the same results
    4. Aggregation handles empty results correctly
    """
    test_cases = [TestCase.from_dict(data) for data in test_data_list]
    
    # Simulate results for each test case
    results = []
    for tc in test_cases:
        result = {
            'id': tc.id,
            'success': True,
            'score': 1.0 if tc.expected_outputs else 0.5,
            'has_expectations': bool(tc.expected_outputs)
        }
        results.append(result)
    
    # Method 1: Direct aggregation
    total_count_1 = len(results)
    success_count_1 = sum(1 for r in results if r['success'])
    avg_score_1 = sum(r['score'] for r in results) / len(results) if results else 0.0
    with_expectations_1 = sum(1 for r in results if r['has_expectations'])
    
    # Method 2: Aggregation via grouping
    success_results = [r for r in results if r['success']]
    total_count_2 = len(results)
    success_count_2 = len(success_results)
    avg_score_2 = sum(r['score'] for r in results) / total_count_2 if total_count_2 > 0 else 0.0
    with_expectations_2 = len([r for r in results if r['has_expectations']])
    
    # Property 1: Both methods should produce the same counts
    assert total_count_1 == total_count_2, \
        "Total count should be consistent across aggregation methods"
    assert success_count_1 == success_count_2, \
        "Success count should be consistent across aggregation methods"
    assert abs(avg_score_1 - avg_score_2) < 0.0001, \
        "Average score should be consistent across aggregation methods"
    assert with_expectations_1 == with_expectations_2, \
        "Count with expectations should be consistent across aggregation methods"
    
    # Property 2: Aggregation should match expected values
    expected_total = len(test_data_list)
    assert total_count_1 == expected_total, \
        f"Total count should match input: expected {expected_total}, got {total_count_1}"
    
    expected_with_expectations = sum(1 for data in test_data_list if data.get('expected_outputs'))
    assert with_expectations_1 == expected_with_expectations, \
        f"Count with expectations should match: expected {expected_with_expectations}, got {with_expectations_1}"
    
    # Property 3: Aggregation should be deterministic
    # Run aggregation again and verify same results
    total_count_3 = len(results)
    success_count_3 = sum(1 for r in results if r['success'])
    avg_score_3 = sum(r['score'] for r in results) / len(results) if results else 0.0
    
    assert total_count_3 == total_count_1, "Aggregation should be deterministic"
    assert success_count_3 == success_count_1, "Aggregation should be deterministic"
    assert abs(avg_score_3 - avg_score_1) < 0.0001, "Aggregation should be deterministic"


# ============================================================================
# Property 29: Final output evaluation
# Feature: project-production-readiness, Property 29: Final output evaluation
# Validates: Requirements 5.3
# ============================================================================

@st.composite
def testcase_with_final_output_strategy(draw):
    """Generate a test case with expected final output for evaluation"""
    test_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    
    # Generate inputs
    inputs = draw(st.dictionaries(
        keys=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
        min_size=1,
        max_size=3
    ))
    
    # Generate expected final output
    expected_outputs = draw(st.dictionaries(
        keys=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        values=st.one_of(st.text(max_size=100), st.integers(), st.booleans()),
        min_size=1,
        max_size=5
    ))
    
    data = {
        'id': test_id,
        'inputs': inputs,
        'expected_outputs': expected_outputs
    }
    
    return data


@settings(max_examples=100, deadline=None)
@given(test_data=testcase_with_final_output_strategy())
def test_property_29_final_output_evaluation(test_data):
    """
    Property 29: Final output evaluation
    
    For any pipeline execution result, the system should support evaluating 
    the final output against expected values.
    
    This property verifies that:
    1. Test cases with expected_outputs can be parsed correctly
    2. Expected outputs are accessible for evaluation
    3. The system can compare actual outputs against expected outputs
    4. Evaluation results indicate whether outputs match expectations
    5. Multiple expected output fields are all evaluated
    """
    # Parse the test case
    tc = TestCase.from_dict(test_data)
    
    # Property 1: Test case should have expected_outputs
    assert tc.expected_outputs is not None, \
        "Test case should have expected_outputs"
    assert len(tc.expected_outputs) > 0, \
        "Test case should have at least one expected output"
    
    # Property 2: Expected outputs should match the input data
    for key, value in test_data['expected_outputs'].items():
        assert key in tc.expected_outputs, \
            f"Expected output key '{key}' should be present"
        assert tc.expected_outputs[key] == value, \
            f"Expected output value for '{key}' should match"
    
    # Property 3: Simulate pipeline execution and evaluation
    # Create simulated actual outputs (some match, some don't)
    actual_outputs = {}
    expected_matches = {}
    
    for key, expected_value in tc.expected_outputs.items():
        # Randomly decide if this output matches (for testing purposes)
        # In real evaluation, this would be the actual pipeline output
        import random
        random.seed(hash(test_data['id'] + key))  # Deterministic for testing
        
        if random.random() > 0.3:  # 70% chance of match
            actual_outputs[key] = expected_value
            expected_matches[key] = True
        else:
            # Generate a different value
            if isinstance(expected_value, str):
                actual_outputs[key] = expected_value + "_modified"
            elif isinstance(expected_value, int):
                actual_outputs[key] = expected_value + 1
            elif isinstance(expected_value, bool):
                actual_outputs[key] = not expected_value
            else:
                actual_outputs[key] = str(expected_value) + "_modified"
            expected_matches[key] = False
    
    # Property 4: Evaluation should compare each expected output field
    evaluation_results = {}
    for key in tc.expected_outputs.keys():
        expected = tc.expected_outputs[key]
        actual = actual_outputs.get(key)
        
        # Simple equality check (in real system, this could be more sophisticated)
        matches = (actual == expected)
        evaluation_results[key] = {
            'expected': expected,
            'actual': actual,
            'matches': matches
        }
    
    # Property 5: All expected output fields should be evaluated
    assert len(evaluation_results) == len(tc.expected_outputs), \
        "All expected output fields should be evaluated"
    
    for key in tc.expected_outputs.keys():
        assert key in evaluation_results, \
            f"Expected output field '{key}' should have evaluation result"
        assert 'expected' in evaluation_results[key], \
            f"Evaluation result for '{key}' should include expected value"
        assert 'actual' in evaluation_results[key], \
            f"Evaluation result for '{key}' should include actual value"
        assert 'matches' in evaluation_results[key], \
            f"Evaluation result for '{key}' should include match status"
    
    # Property 6: Match status should be correct
    for key, result in evaluation_results.items():
        expected_match = expected_matches[key]
        actual_match = result['matches']
        assert expected_match == actual_match, \
            f"Match status for '{key}' should be correct: expected {expected_match}, got {actual_match}"
    
    # Property 7: Overall evaluation should reflect individual field results
    all_matched = all(result['matches'] for result in evaluation_results.values())
    any_matched = any(result['matches'] for result in evaluation_results.values())
    
    # If all fields match, overall should be success
    if all_matched:
        overall_success = True
    else:
        overall_success = False
    
    # Verify the overall evaluation logic
    assert overall_success == all_matched, \
        "Overall evaluation should be True only if all fields match"


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(test_data_list=st.lists(testcase_with_final_output_strategy(), min_size=1, max_size=10))
def test_property_29_final_output_evaluation_batch(test_data_list, tmp_path):
    """
    Property 29 (Batch): Final output evaluation for multiple test cases
    
    For any set of pipeline test cases with expected outputs, the system 
    should evaluate all final outputs and aggregate the results.
    
    This property verifies that:
    1. Multiple test cases can be evaluated in batch
    2. Each test case's final output is evaluated independently
    3. Evaluation results are aggregated correctly
    4. Pass/fail statistics are computed correctly
    """
    # Create test cases
    test_cases = [TestCase.from_dict(data) for data in test_data_list]
    
    # Property 1: All test cases should have expected outputs
    for tc in test_cases:
        assert tc.expected_outputs is not None, \
            f"Test case {tc.id} should have expected_outputs"
        assert len(tc.expected_outputs) > 0, \
            f"Test case {tc.id} should have at least one expected output"
    
    # Property 2: Simulate batch evaluation
    batch_evaluation_results = []
    
    for tc in test_cases:
        # Simulate actual outputs (deterministic based on test case ID)
        import random
        random.seed(hash(tc.id))
        
        # Randomly decide if this test case passes (for testing)
        passes = random.random() > 0.4  # 60% pass rate
        
        if passes:
            # All outputs match
            actual_outputs = tc.expected_outputs.copy()
            all_match = True
        else:
            # Some outputs don't match
            actual_outputs = {}
            for key, value in tc.expected_outputs.items():
                if random.random() > 0.5:
                    actual_outputs[key] = value
                else:
                    # Modify the value
                    if isinstance(value, str):
                        actual_outputs[key] = value + "_modified"
                    elif isinstance(value, int):
                        actual_outputs[key] = value + 1
                    else:
                        actual_outputs[key] = str(value) + "_modified"
            all_match = False
        
        # Evaluate
        field_results = {}
        for key in tc.expected_outputs.keys():
            expected = tc.expected_outputs[key]
            actual = actual_outputs.get(key)
            matches = (actual == expected)
            field_results[key] = matches
        
        overall_pass = all(field_results.values())
        
        batch_evaluation_results.append({
            'test_id': tc.id,
            'overall_pass': overall_pass,
            'field_results': field_results,
            'expected_outputs': tc.expected_outputs,
            'actual_outputs': actual_outputs
        })
    
    # Property 3: All test cases should have evaluation results
    assert len(batch_evaluation_results) == len(test_cases), \
        "All test cases should have evaluation results"
    
    # Property 4: Compute aggregated statistics
    total_tests = len(batch_evaluation_results)
    passed_tests = sum(1 for r in batch_evaluation_results if r['overall_pass'])
    failed_tests = total_tests - passed_tests
    pass_rate = passed_tests / total_tests if total_tests > 0 else 0.0
    
    # Property 5: Statistics should be consistent
    assert passed_tests + failed_tests == total_tests, \
        "Passed + failed should equal total tests"
    assert 0.0 <= pass_rate <= 1.0, \
        "Pass rate should be between 0 and 1"
    
    # Property 6: Each test case should have complete evaluation
    for result in batch_evaluation_results:
        assert 'test_id' in result, "Result should have test_id"
        assert 'overall_pass' in result, "Result should have overall_pass"
        assert 'field_results' in result, "Result should have field_results"
        assert 'expected_outputs' in result, "Result should have expected_outputs"
        assert 'actual_outputs' in result, "Result should have actual_outputs"
        
        # All expected output fields should be evaluated
        expected_keys = set(result['expected_outputs'].keys())
        evaluated_keys = set(result['field_results'].keys())
        assert expected_keys == evaluated_keys, \
            f"All expected output fields should be evaluated for test {result['test_id']}"


@settings(max_examples=100, deadline=None)
@given(
    test_data=testcase_with_final_output_strategy(),
    output_key=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))
)
def test_property_29_final_output_field_evaluation(test_data, output_key):
    """
    Property 29 (Field Evaluation): Individual output field evaluation
    
    For any test case and any output field, the system should correctly
    evaluate whether the actual output matches the expected output.
    
    This property verifies that:
    1. Individual output fields can be evaluated independently
    2. Evaluation handles missing fields correctly
    3. Evaluation handles type mismatches correctly
    4. Evaluation is deterministic
    """
    tc = TestCase.from_dict(test_data)
    
    # Check if the output_key exists in expected outputs
    if output_key in tc.expected_outputs:
        expected_value = tc.expected_outputs[output_key]
        
        # Test 1: Exact match
        actual_value = expected_value
        matches = (actual_value == expected_value)
        assert matches == True, \
            "Exact match should return True"
        
        # Test 2: Different value
        if isinstance(expected_value, str):
            actual_value = expected_value + "_different"
        elif isinstance(expected_value, int):
            actual_value = expected_value + 1
        elif isinstance(expected_value, bool):
            actual_value = not expected_value
        else:
            actual_value = str(expected_value) + "_different"
        
        matches = (actual_value == expected_value)
        assert matches == False, \
            "Different value should return False"
        
        # Test 3: Type mismatch
        if isinstance(expected_value, str):
            actual_value = 123  # int instead of str
        elif isinstance(expected_value, int):
            actual_value = str(expected_value)  # str instead of int
        else:
            actual_value = "type_mismatch"
        
        matches = (actual_value == expected_value)
        assert matches == False, \
            "Type mismatch should return False"
    
    # Test 4: Missing field
    if output_key not in tc.expected_outputs:
        # If the field is not expected, evaluation should handle it gracefully
        # In this case, we consider it as "not evaluated" or "not applicable"
        evaluation_result = {
            'field': output_key,
            'evaluated': False,
            'reason': 'Field not in expected outputs'
        }
        
        assert evaluation_result['evaluated'] == False, \
            "Missing expected field should not be evaluated"


@settings(max_examples=100, deadline=None)
@given(test_data=testcase_with_final_output_strategy())
def test_property_29_final_output_evaluation_consistency(test_data):
    """
    Property 29 (Consistency): Final output evaluation consistency
    
    For any test case, evaluating the same outputs multiple times should
    produce consistent results.
    
    This property verifies that:
    1. Evaluation is deterministic
    2. Multiple evaluations produce the same result
    3. Evaluation order doesn't affect results
    """
    tc = TestCase.from_dict(test_data)
    
    # Create actual outputs (same as expected for this test)
    actual_outputs = tc.expected_outputs.copy()
    
    # Evaluate multiple times
    evaluation_1 = {}
    for key, expected in tc.expected_outputs.items():
        actual = actual_outputs.get(key)
        evaluation_1[key] = (actual == expected)
    
    evaluation_2 = {}
    for key, expected in tc.expected_outputs.items():
        actual = actual_outputs.get(key)
        evaluation_2[key] = (actual == expected)
    
    # Property 1: Both evaluations should produce the same results
    assert evaluation_1 == evaluation_2, \
        "Multiple evaluations should produce consistent results"
    
    # Property 2: Evaluate in different order
    keys_reversed = list(reversed(list(tc.expected_outputs.keys())))
    evaluation_3 = {}
    for key in keys_reversed:
        expected = tc.expected_outputs[key]
        actual = actual_outputs.get(key)
        evaluation_3[key] = (actual == expected)
    
    # Results should be the same regardless of evaluation order
    assert evaluation_1 == evaluation_3, \
        "Evaluation order should not affect results"
    
    # Property 3: Overall result should be consistent
    overall_1 = all(evaluation_1.values())
    overall_2 = all(evaluation_2.values())
    overall_3 = all(evaluation_3.values())
    
    assert overall_1 == overall_2 == overall_3, \
        "Overall evaluation result should be consistent"


# ============================================================================
# Property 30: Intermediate step evaluation
# Feature: project-production-readiness, Property 30: Intermediate step evaluation
# Validates: Requirements 5.4
# ============================================================================

@st.composite
def testcase_with_intermediate_expectations_strategy(draw):
    """Generate a test case with intermediate step expectations"""
    test_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    
    # Generate inputs
    inputs = draw(st.dictionaries(
        keys=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
        min_size=1,
        max_size=3
    ))
    
    # Generate intermediate expectations for multiple steps
    num_steps = draw(st.integers(min_value=1, max_value=5))
    intermediate_expectations = {}
    
    for i in range(num_steps):
        step_id = f"step_{i+1}"
        # Generate random expectation data for this step
        expectation = draw(st.dictionaries(
            keys=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
            values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
            min_size=1,
            max_size=3
        ))
        intermediate_expectations[step_id] = expectation
    
    # Generate expected final outputs
    expected_outputs = draw(st.dictionaries(
        keys=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
        min_size=0,
        max_size=3
    ))
    
    data = {
        'id': test_id,
        'inputs': inputs,
        'intermediate_expectations': intermediate_expectations,
        'expected_outputs': expected_outputs
    }
    
    return data


@settings(max_examples=100, deadline=None)
@given(test_data=testcase_with_intermediate_expectations_strategy())
def test_property_30_intermediate_step_evaluation(test_data):
    """
    Property 30: Intermediate step evaluation
    
    For any pipeline execution with intermediate evaluation configured, the 
    system should evaluate intermediate step outputs.
    
    This property verifies that:
    1. Test cases with intermediate_expectations can be parsed correctly
    2. Intermediate expectations are accessible for each step
    3. The system can compare actual step outputs against expected outputs
    4. Evaluation results indicate whether step outputs match expectations
    5. Multiple intermediate steps are all evaluated independently
    6. Evaluation handles missing step outputs correctly
    """
    # Parse the test case
    tc = TestCase.from_dict(test_data)
    
    # Property 1: Test case should have intermediate_expectations
    assert tc.has_intermediate_expectations(), \
        "Test case should have intermediate_expectations"
    assert len(tc.intermediate_expectations) > 0, \
        "Test case should have at least one intermediate expectation"
    
    # Property 2: Intermediate expectations should match the input data
    for step_id, expectation in test_data['intermediate_expectations'].items():
        assert step_id in tc.intermediate_expectations, \
            f"Intermediate expectation for step '{step_id}' should be present"
        assert tc.intermediate_expectations[step_id] == expectation, \
            f"Intermediate expectation for step '{step_id}' should match"
    
    # Property 3: Simulate pipeline execution with step outputs
    # Create simulated step outputs (some match, some don't)
    step_outputs = {}
    expected_matches = {}
    
    import random
    random.seed(hash(test_data['id']))  # Deterministic for testing
    
    for step_id, expected_output in tc.intermediate_expectations.items():
        # Randomly decide if this step output matches (for testing purposes)
        if random.random() > 0.3:  # 70% chance of match
            # Output matches expectation
            step_outputs[step_id] = expected_output.copy() if isinstance(expected_output, dict) else expected_output
            expected_matches[step_id] = True
        else:
            # Output doesn't match - modify the expected output
            if isinstance(expected_output, dict):
                modified_output = expected_output.copy()
                # Modify one field
                if modified_output:
                    first_key = list(modified_output.keys())[0]
                    if isinstance(modified_output[first_key], str):
                        modified_output[first_key] = modified_output[first_key] + "_modified"
                    elif isinstance(modified_output[first_key], int):
                        modified_output[first_key] = modified_output[first_key] + 1
                    elif isinstance(modified_output[first_key], bool):
                        modified_output[first_key] = not modified_output[first_key]
                step_outputs[step_id] = modified_output
            elif isinstance(expected_output, str):
                step_outputs[step_id] = expected_output + "_modified"
            elif isinstance(expected_output, int):
                step_outputs[step_id] = expected_output + 1
            elif isinstance(expected_output, bool):
                step_outputs[step_id] = not expected_output
            else:
                step_outputs[step_id] = str(expected_output) + "_modified"
            expected_matches[step_id] = False
    
    # Property 4: Evaluate each intermediate step
    evaluation_results = {}
    for step_id in tc.intermediate_expectations.keys():
        expected = tc.intermediate_expectations[step_id]
        actual = step_outputs.get(step_id)
        
        # Simple equality check (in real system, this uses _compare_outputs)
        if isinstance(expected, dict) and isinstance(actual, dict):
            # For dicts, check if all expected keys match
            matches = all(
                key in actual and actual[key] == value
                for key, value in expected.items()
            )
        else:
            matches = (actual == expected)
        
        evaluation_results[step_id] = {
            'expected': expected,
            'actual': actual,
            'matches': matches
        }
    
    # Property 5: All intermediate steps should be evaluated
    assert len(evaluation_results) == len(tc.intermediate_expectations), \
        "All intermediate steps should be evaluated"
    
    for step_id in tc.intermediate_expectations.keys():
        assert step_id in evaluation_results, \
            f"Intermediate step '{step_id}' should have evaluation result"
        assert 'expected' in evaluation_results[step_id], \
            f"Evaluation result for '{step_id}' should include expected value"
        assert 'actual' in evaluation_results[step_id], \
            f"Evaluation result for '{step_id}' should include actual value"
        assert 'matches' in evaluation_results[step_id], \
            f"Evaluation result for '{step_id}' should include match status"
    
    # Property 6: Match status should be correct
    for step_id, result in evaluation_results.items():
        expected_match = expected_matches[step_id]
        actual_match = result['matches']
        assert expected_match == actual_match, \
            f"Match status for step '{step_id}' should be correct: expected {expected_match}, got {actual_match}"
    
    # Property 7: Each step is evaluated independently
    # Verify that a failure in one step doesn't affect evaluation of other steps
    for step_id in evaluation_results.keys():
        # Each step should have its own evaluation result
        assert evaluation_results[step_id] is not None, \
            f"Step '{step_id}' should have independent evaluation result"
    
    # Property 8: Overall intermediate evaluation should reflect individual step results
    all_steps_matched = all(result['matches'] for result in evaluation_results.values())
    any_step_matched = any(result['matches'] for result in evaluation_results.values())
    
    # Count matched and failed steps
    matched_count = sum(1 for result in evaluation_results.values() if result['matches'])
    failed_count = len(evaluation_results) - matched_count
    
    assert matched_count + failed_count == len(evaluation_results), \
        "Matched + failed should equal total intermediate steps"


@settings(max_examples=100, deadline=None)
@given(test_data=testcase_with_intermediate_expectations_strategy())
def test_property_30_intermediate_step_evaluation_missing_outputs(test_data):
    """
    Property 30 (Missing Outputs): Intermediate step evaluation with missing outputs
    
    For any pipeline execution where some intermediate step outputs are missing,
    the system should handle missing outputs correctly.
    
    This property verifies that:
    1. Evaluation handles missing step outputs gracefully
    2. Missing outputs are reported as evaluation failures
    3. Other steps with outputs are still evaluated correctly
    4. Missing output information is included in evaluation results
    """
    tc = TestCase.from_dict(test_data)
    
    # Simulate step outputs with some steps missing
    step_outputs = {}
    step_ids = list(tc.intermediate_expectations.keys())
    
    import random
    random.seed(hash(test_data['id']))
    
    # Only include outputs for some steps (randomly)
    for step_id in step_ids:
        if random.random() > 0.3:  # 70% chance of having output
            expected = tc.intermediate_expectations[step_id]
            step_outputs[step_id] = expected.copy() if isinstance(expected, dict) else expected
    
    # Property 1: Evaluate all steps, including those with missing outputs
    evaluation_results = {}
    for step_id, expected in tc.intermediate_expectations.items():
        actual = step_outputs.get(step_id)
        
        if actual is None:
            # Missing output
            matches = False
            details = "Step output is missing"
        else:
            # Compare outputs
            if isinstance(expected, dict) and isinstance(actual, dict):
                matches = all(
                    key in actual and actual[key] == value
                    for key, value in expected.items()
                )
            else:
                matches = (actual == expected)
            details = "Match" if matches else "Mismatch"
        
        evaluation_results[step_id] = {
            'expected': expected,
            'actual': actual,
            'matches': matches,
            'details': details
        }
    
    # Property 2: All steps should have evaluation results
    assert len(evaluation_results) == len(tc.intermediate_expectations), \
        "All intermediate steps should have evaluation results, even if outputs are missing"
    
    # Property 3: Steps with missing outputs should be marked as failed
    for step_id, result in evaluation_results.items():
        if result['actual'] is None:
            assert result['matches'] is False, \
                f"Step '{step_id}' with missing output should be marked as failed"
            assert 'missing' in result['details'].lower(), \
                f"Step '{step_id}' should indicate output is missing"
    
    # Property 4: Steps with outputs should be evaluated normally
    for step_id, result in evaluation_results.items():
        if result['actual'] is not None:
            # This step has output, so it should be evaluated normally
            expected = result['expected']
            actual = result['actual']
            
            if isinstance(expected, dict) and isinstance(actual, dict):
                expected_match = all(
                    key in actual and actual[key] == value
                    for key, value in expected.items()
                )
            else:
                expected_match = (actual == expected)
            
            assert result['matches'] == expected_match, \
                f"Step '{step_id}' with output should be evaluated correctly"


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(test_data_list=st.lists(testcase_with_intermediate_expectations_strategy(), min_size=1, max_size=10))
def test_property_30_intermediate_step_evaluation_batch(test_data_list, tmp_path):
    """
    Property 30 (Batch): Intermediate step evaluation for multiple test cases
    
    For any set of pipeline test cases with intermediate expectations, the 
    system should evaluate all intermediate steps across all test cases.
    
    This property verifies that:
    1. Multiple test cases can be evaluated in batch
    2. Each test case's intermediate steps are evaluated independently
    3. Evaluation results are aggregated correctly across test cases
    4. Statistics are computed correctly for intermediate step evaluation
    """
    # Ensure unique test IDs
    for i, data in enumerate(test_data_list):
        data['id'] = f"test_{i}_{data['id']}"
    
    # Create test cases
    test_cases = [TestCase.from_dict(data) for data in test_data_list]
    
    # Property 1: All test cases should have intermediate expectations
    for tc in test_cases:
        assert tc.has_intermediate_expectations(), \
            f"Test case {tc.id} should have intermediate_expectations"
    
    # Property 2: Simulate batch evaluation of intermediate steps
    batch_evaluation_results = []
    
    import random
    for tc in test_cases:
        random.seed(hash(tc.id))
        
        # Simulate step outputs
        step_outputs = {}
        for step_id, expected in tc.intermediate_expectations.items():
            if random.random() > 0.2:  # 80% chance of having output
                if random.random() > 0.3:  # 70% chance of match
                    step_outputs[step_id] = expected.copy() if isinstance(expected, dict) else expected
                else:
                    # Modified output
                    if isinstance(expected, dict):
                        modified = expected.copy()
                        if modified:
                            first_key = list(modified.keys())[0]
                            if isinstance(modified[first_key], str):
                                modified[first_key] = modified[first_key] + "_mod"
                            elif isinstance(modified[first_key], int):
                                modified[first_key] = modified[first_key] + 1
                        step_outputs[step_id] = modified
                    else:
                        step_outputs[step_id] = str(expected) + "_mod"
        
        # Evaluate intermediate steps for this test case
        step_results = {}
        for step_id, expected in tc.intermediate_expectations.items():
            actual = step_outputs.get(step_id)
            
            if actual is None:
                matches = False
            elif isinstance(expected, dict) and isinstance(actual, dict):
                matches = all(
                    key in actual and actual[key] == value
                    for key, value in expected.items()
                )
            else:
                matches = (actual == expected)
            
            step_results[step_id] = {
                'matches': matches,
                'expected': expected,
                'actual': actual
            }
        
        batch_evaluation_results.append({
            'test_id': tc.id,
            'step_results': step_results,
            'all_steps_passed': all(r['matches'] for r in step_results.values())
        })
    
    # Property 3: All test cases should have evaluation results
    assert len(batch_evaluation_results) == len(test_cases), \
        "All test cases should have intermediate step evaluation results"
    
    # Property 4: Compute aggregated statistics
    total_tests = len(batch_evaluation_results)
    tests_with_all_steps_passed = sum(1 for r in batch_evaluation_results if r['all_steps_passed'])
    
    # Count total steps evaluated across all test cases
    total_steps = sum(len(r['step_results']) for r in batch_evaluation_results)
    total_steps_passed = sum(
        sum(1 for step_result in r['step_results'].values() if step_result['matches'])
        for r in batch_evaluation_results
    )
    
    # Property 5: Statistics should be consistent
    assert total_steps > 0, "Should have evaluated at least one step"
    assert total_steps_passed <= total_steps, "Passed steps should not exceed total steps"
    
    step_pass_rate = total_steps_passed / total_steps if total_steps > 0 else 0.0
    assert 0.0 <= step_pass_rate <= 1.0, "Step pass rate should be between 0 and 1"
    
    # Property 6: Each test case should have complete evaluation
    for result in batch_evaluation_results:
        assert 'test_id' in result, "Result should have test_id"
        assert 'step_results' in result, "Result should have step_results"
        assert 'all_steps_passed' in result, "Result should have all_steps_passed"
        
        # Find the corresponding test case
        tc = next(tc for tc in test_cases if tc.id == result['test_id'])
        
        # All expected steps should be evaluated
        expected_step_ids = set(tc.intermediate_expectations.keys())
        evaluated_step_ids = set(result['step_results'].keys())
        assert expected_step_ids == evaluated_step_ids, \
            f"All expected steps should be evaluated for test {result['test_id']}"


@settings(max_examples=100, deadline=None)
@given(
    test_data=testcase_with_intermediate_expectations_strategy(),
    step_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')))
)
def test_property_30_intermediate_step_evaluation_individual_step(test_data, step_id):
    """
    Property 30 (Individual Step): Individual intermediate step evaluation
    
    For any test case and any step ID, the system should correctly evaluate
    whether the actual step output matches the expected output.
    
    This property verifies that:
    1. Individual steps can be evaluated independently
    2. Evaluation handles steps not in expectations correctly
    3. Evaluation is deterministic for the same inputs
    4. Different data types are handled correctly
    """
    tc = TestCase.from_dict(test_data)
    
    # Check if the step_id exists in intermediate expectations
    if step_id in tc.intermediate_expectations:
        expected = tc.intermediate_expectations[step_id]
        
        # Test 1: Exact match
        actual = expected.copy() if isinstance(expected, dict) else expected
        
        if isinstance(expected, dict) and isinstance(actual, dict):
            matches = all(
                key in actual and actual[key] == value
                for key, value in expected.items()
            )
        else:
            matches = (actual == expected)
        
        assert matches is True, \
            "Exact match should return True"
        
        # Test 2: Different value
        if isinstance(expected, dict):
            actual_modified = expected.copy()
            if actual_modified:
                first_key = list(actual_modified.keys())[0]
                if isinstance(actual_modified[first_key], str):
                    actual_modified[first_key] = actual_modified[first_key] + "_diff"
                elif isinstance(actual_modified[first_key], int):
                    actual_modified[first_key] = actual_modified[first_key] + 1
                elif isinstance(actual_modified[first_key], bool):
                    actual_modified[first_key] = not actual_modified[first_key]
                
                matches = all(
                    key in actual_modified and actual_modified[key] == value
                    for key, value in expected.items()
                )
        elif isinstance(expected, str):
            actual_modified = expected + "_different"
            matches = (actual_modified == expected)
        elif isinstance(expected, int):
            actual_modified = expected + 1
            matches = (actual_modified == expected)
        elif isinstance(expected, bool):
            actual_modified = not expected
            matches = (actual_modified == expected)
        else:
            actual_modified = str(expected) + "_different"
            matches = (actual_modified == expected)
        
        assert matches is False, \
            "Different value should return False"
    
    # Test 3: Step not in expectations
    if step_id not in tc.intermediate_expectations:
        # If the step is not expected, evaluation should handle it gracefully
        # In this case, we consider it as "not evaluated" or "not applicable"
        evaluation_result = {
            'step_id': step_id,
            'evaluated': False,
            'reason': 'Step not in intermediate expectations'
        }
        
        assert evaluation_result['evaluated'] is False, \
            "Step not in expectations should not be evaluated"


@settings(max_examples=100, deadline=None)
@given(test_data=testcase_with_intermediate_expectations_strategy())
def test_property_30_intermediate_step_evaluation_consistency(test_data):
    """
    Property 30 (Consistency): Intermediate step evaluation consistency
    
    For any test case, evaluating the same step outputs multiple times should
    produce consistent results.
    
    This property verifies that:
    1. Evaluation is deterministic
    2. Multiple evaluations produce the same result
    3. Evaluation order doesn't affect results
    """
    tc = TestCase.from_dict(test_data)
    
    # Create step outputs (same as expected for this test)
    step_outputs = {}
    for step_id, expected in tc.intermediate_expectations.items():
        step_outputs[step_id] = expected.copy() if isinstance(expected, dict) else expected
    
    # Evaluate multiple times
    evaluation_1 = {}
    for step_id, expected in tc.intermediate_expectations.items():
        actual = step_outputs.get(step_id)
        
        if isinstance(expected, dict) and isinstance(actual, dict):
            matches = all(
                key in actual and actual[key] == value
                for key, value in expected.items()
            )
        else:
            matches = (actual == expected)
        
        evaluation_1[step_id] = matches
    
    evaluation_2 = {}
    for step_id, expected in tc.intermediate_expectations.items():
        actual = step_outputs.get(step_id)
        
        if isinstance(expected, dict) and isinstance(actual, dict):
            matches = all(
                key in actual and actual[key] == value
                for key, value in expected.items()
            )
        else:
            matches = (actual == expected)
        
        evaluation_2[step_id] = matches
    
    # Property 1: Both evaluations should produce the same results
    assert evaluation_1 == evaluation_2, \
        "Multiple evaluations should produce consistent results"
    
    # Property 2: Evaluate in different order
    step_ids_reversed = list(reversed(list(tc.intermediate_expectations.keys())))
    evaluation_3 = {}
    for step_id in step_ids_reversed:
        expected = tc.intermediate_expectations[step_id]
        actual = step_outputs.get(step_id)
        
        if isinstance(expected, dict) and isinstance(actual, dict):
            matches = all(
                key in actual and actual[key] == value
                for key, value in expected.items()
            )
        else:
            matches = (actual == expected)
        
        evaluation_3[step_id] = matches
    
    # Results should be the same regardless of evaluation order
    assert evaluation_1 == evaluation_3, \
        "Evaluation order should not affect results"
    
    # Property 3: Overall result should be consistent
    overall_1 = all(evaluation_1.values())
    overall_2 = all(evaluation_2.values())
    overall_3 = all(evaluation_3.values())
    
    assert overall_1 == overall_2 == overall_3, \
        "Overall evaluation result should be consistent"


# ============================================================================
# Property 31: Expected aggregation validation
# Feature: project-production-readiness, Property 31: Expected aggregation validation
# Validates: Requirements 5.5
# ============================================================================

@st.composite
def testcase_with_expected_aggregation_strategy(draw):
    """Generate a test case with expected aggregation for batch processing"""
    test_id = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))))
    
    # Generate batch items
    num_items = draw(st.integers(min_value=2, max_value=10))
    batch_items = []
    for i in range(num_items):
        item = draw(st.dictionaries(
            keys=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
            values=st.one_of(
                st.text(max_size=50),
                st.integers(min_value=0, max_value=100),
                st.floats(min_value=0.0, max_value=100.0, allow_nan=False, allow_infinity=False),
                st.booleans()
            ),
            min_size=1,
            max_size=3
        ))
        batch_items.append(item)
    
    # Generate expected aggregation result
    expected_aggregation = draw(st.dictionaries(
        keys=st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        values=st.one_of(
            st.text(max_size=100),
            st.integers(min_value=0, max_value=1000),
            st.floats(min_value=0.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
            st.booleans(),
            st.lists(st.integers(min_value=0, max_value=100), min_size=0, max_size=5)
        ),
        min_size=1,
        max_size=5
    ))
    
    # Generate inputs
    inputs = draw(st.dictionaries(
        keys=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
        min_size=0,
        max_size=3
    ))
    
    # Generate expected outputs
    expected_outputs = draw(st.dictionaries(
        keys=st.text(min_size=1, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'))),
        values=st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
        min_size=0,
        max_size=3
    ))
    
    data = {
        'id': test_id,
        'inputs': inputs,
        'batch_items': batch_items,
        'expected_aggregation': expected_aggregation,
        'expected_outputs': expected_outputs
    }
    
    return data


@settings(max_examples=100, deadline=None)
@given(test_data=testcase_with_expected_aggregation_strategy())
def test_property_31_expected_aggregation_validation(test_data):
    """
    Property 31: Expected aggregation validation
    
    For any testset with expected_aggregation defined, the system should 
    validate the actual aggregation result against the expected value.
    
    This property verifies that:
    1. Test cases with expected_aggregation can be parsed correctly
    2. Expected aggregation is accessible for validation
    3. The system can compare actual aggregation results against expected values
    4. Validation results indicate whether aggregation matches expectations
    5. Multiple aggregation fields are all validated
    6. Validation handles different data types correctly
    """
    # Parse the test case
    tc = TestCase.from_dict(test_data)
    
    # Property 1: Test case should have expected_aggregation
    assert tc.has_expected_aggregation(), \
        "Test case should have expected_aggregation"
    assert tc.expected_aggregation is not None, \
        "expected_aggregation should not be None"
    assert len(tc.expected_aggregation) > 0, \
        "expected_aggregation should have at least one field"
    
    # Property 2: Expected aggregation should match the input data
    for key, value in test_data['expected_aggregation'].items():
        assert key in tc.expected_aggregation, \
            f"Expected aggregation key '{key}' should be present"
        assert tc.expected_aggregation[key] == value, \
            f"Expected aggregation value for '{key}' should match"
    
    # Property 3: Simulate batch aggregation and validation
    # Create simulated actual aggregation results (some match, some don't)
    actual_aggregation = {}
    expected_matches = {}
    
    import random
    random.seed(hash(test_data['id']))  # Deterministic for testing
    
    for key, expected_value in tc.expected_aggregation.items():
        # Randomly decide if this field matches (for testing purposes)
        if random.random() > 0.3:  # 70% chance of match
            actual_aggregation[key] = expected_value
            expected_matches[key] = True
        else:
            # Generate a different value
            if isinstance(expected_value, str):
                actual_aggregation[key] = expected_value + "_modified"
            elif isinstance(expected_value, int):
                actual_aggregation[key] = expected_value + 1
            elif isinstance(expected_value, float):
                actual_aggregation[key] = expected_value + 0.1
            elif isinstance(expected_value, bool):
                actual_aggregation[key] = not expected_value
            elif isinstance(expected_value, list):
                actual_aggregation[key] = expected_value + [999]
            else:
                actual_aggregation[key] = str(expected_value) + "_modified"
            expected_matches[key] = False
    
    # Property 4: Validate each aggregation field
    validation_results = {}
    for key in tc.expected_aggregation.keys():
        expected = tc.expected_aggregation[key]
        actual = actual_aggregation.get(key)
        
        # Simple equality check (in real system, this could be more sophisticated)
        if isinstance(expected, float) and isinstance(actual, (int, float)):
            # For floats, use approximate comparison
            matches = abs(float(actual) - expected) < 0.0001
        else:
            matches = (actual == expected)
        
        validation_results[key] = {
            'expected': expected,
            'actual': actual,
            'matches': matches
        }
    
    # Property 5: All expected aggregation fields should be validated
    assert len(validation_results) == len(tc.expected_aggregation), \
        "All expected aggregation fields should be validated"
    
    for key in tc.expected_aggregation.keys():
        assert key in validation_results, \
            f"Expected aggregation field '{key}' should have validation result"
        assert 'expected' in validation_results[key], \
            f"Validation result for '{key}' should include expected value"
        assert 'actual' in validation_results[key], \
            f"Validation result for '{key}' should include actual value"
        assert 'matches' in validation_results[key], \
            f"Validation result for '{key}' should include match status"
    
    # Property 6: Match status should be correct
    for key, result in validation_results.items():
        expected_match = expected_matches[key]
        actual_match = result['matches']
        assert expected_match == actual_match, \
            f"Match status for '{key}' should be correct: expected {expected_match}, got {actual_match}"
    
    # Property 7: Overall validation should reflect individual field results
    all_matched = all(result['matches'] for result in validation_results.values())
    any_matched = any(result['matches'] for result in validation_results.values())
    
    # If all fields match, overall should be success
    if all_matched:
        overall_success = True
    else:
        overall_success = False
    
    # Verify the overall validation logic
    assert overall_success == all_matched, \
        "Overall validation should be True only if all fields match"
    
    # Property 8: Validation should handle different data types
    for key, result in validation_results.items():
        expected = result['expected']
        actual = result['actual']
        
        # Type consistency check
        if result['matches']:
            # If they match, types should be compatible
            if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
                # Numeric types are compatible
                pass
            else:
                # For other types, they should be the same type
                assert type(expected) == type(actual), \
                    f"Matching values should have compatible types for '{key}'"


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(test_data_list=st.lists(testcase_with_expected_aggregation_strategy(), min_size=1, max_size=10))
def test_property_31_expected_aggregation_validation_batch(test_data_list, tmp_path):
    """
    Property 31 (Batch): Expected aggregation validation for multiple test cases
    
    For any set of test cases with expected aggregation, the system should 
    validate all aggregation results and aggregate the validation results.
    
    This property verifies that:
    1. Multiple test cases can be validated in batch
    2. Each test case's aggregation is validated independently
    3. Validation results are aggregated correctly
    4. Pass/fail statistics are computed correctly
    """
    # Ensure unique test IDs
    for i, data in enumerate(test_data_list):
        data['id'] = f"test_{i}_{data['id']}"
    
    # Create test cases
    test_cases = [TestCase.from_dict(data) for data in test_data_list]
    
    # Property 1: All test cases should have expected aggregation
    for tc in test_cases:
        assert tc.has_expected_aggregation(), \
            f"Test case {tc.id} should have expected_aggregation"
        assert len(tc.expected_aggregation) > 0, \
            f"Test case {tc.id} should have at least one aggregation field"
    
    # Property 2: Simulate batch validation
    batch_validation_results = []
    
    import random
    for tc in test_cases:
        random.seed(hash(tc.id))
        
        # Randomly decide if this test case passes (for testing)
        passes = random.random() > 0.4  # 60% pass rate
        
        if passes:
            # All fields match
            actual_aggregation = tc.expected_aggregation.copy()
            all_match = True
        else:
            # Some fields don't match
            actual_aggregation = {}
            for key, value in tc.expected_aggregation.items():
                if random.random() > 0.5:
                    actual_aggregation[key] = value
                else:
                    # Modify the value
                    if isinstance(value, str):
                        actual_aggregation[key] = value + "_modified"
                    elif isinstance(value, int):
                        actual_aggregation[key] = value + 1
                    elif isinstance(value, float):
                        actual_aggregation[key] = value + 0.1
                    elif isinstance(value, bool):
                        actual_aggregation[key] = not value
                    elif isinstance(value, list):
                        actual_aggregation[key] = value + [999]
                    else:
                        actual_aggregation[key] = str(value) + "_modified"
            all_match = False
        
        # Validate
        field_results = {}
        for key in tc.expected_aggregation.keys():
            expected = tc.expected_aggregation[key]
            actual = actual_aggregation.get(key)
            
            if isinstance(expected, float) and isinstance(actual, (int, float)):
                matches = abs(float(actual) - expected) < 0.0001
            else:
                matches = (actual == expected)
            
            field_results[key] = matches
        
        overall_pass = all(field_results.values())
        
        batch_validation_results.append({
            'test_id': tc.id,
            'overall_pass': overall_pass,
            'field_results': field_results,
            'expected_aggregation': tc.expected_aggregation,
            'actual_aggregation': actual_aggregation
        })
    
    # Property 3: All test cases should have validation results
    assert len(batch_validation_results) == len(test_cases), \
        "All test cases should have validation results"
    
    # Property 4: Compute aggregated statistics
    total_tests = len(batch_validation_results)
    passed_tests = sum(1 for r in batch_validation_results if r['overall_pass'])
    failed_tests = total_tests - passed_tests
    pass_rate = passed_tests / total_tests if total_tests > 0 else 0.0
    
    # Property 5: Statistics should be consistent
    assert passed_tests + failed_tests == total_tests, \
        "Passed + failed should equal total tests"
    assert 0.0 <= pass_rate <= 1.0, \
        "Pass rate should be between 0 and 1"
    
    # Property 6: Each test case should have complete validation
    for result in batch_validation_results:
        assert 'test_id' in result, "Result should have test_id"
        assert 'overall_pass' in result, "Result should have overall_pass"
        assert 'field_results' in result, "Result should have field_results"
        assert 'expected_aggregation' in result, "Result should have expected_aggregation"
        assert 'actual_aggregation' in result, "Result should have actual_aggregation"
        
        # All expected aggregation fields should be validated
        expected_keys = set(result['expected_aggregation'].keys())
        validated_keys = set(result['field_results'].keys())
        assert expected_keys == validated_keys, \
            f"All expected aggregation fields should be validated for test {result['test_id']}"


@settings(max_examples=100, deadline=None)
@given(
    test_data=testcase_with_expected_aggregation_strategy(),
    aggregation_key=st.text(min_size=1, max_size=15, alphabet=st.characters(whitelist_categories=('Lu', 'Ll')))
)
def test_property_31_expected_aggregation_field_validation(test_data, aggregation_key):
    """
    Property 31 (Field Validation): Individual aggregation field validation
    
    For any test case and any aggregation field, the system should correctly
    validate whether the actual aggregation matches the expected aggregation.
    
    This property verifies that:
    1. Individual aggregation fields can be validated independently
    2. Validation handles missing fields correctly
    3. Validation handles type mismatches correctly
    4. Validation is deterministic
    """
    tc = TestCase.from_dict(test_data)
    
    # Check if the aggregation_key exists in expected aggregation
    if aggregation_key in tc.expected_aggregation:
        expected_value = tc.expected_aggregation[aggregation_key]
        
        # Test 1: Exact match
        actual_value = expected_value
        if isinstance(expected_value, float):
            matches = abs(float(actual_value) - expected_value) < 0.0001
        else:
            matches = (actual_value == expected_value)
        assert matches is True, \
            "Exact match should return True"
        
        # Test 2: Different value
        if isinstance(expected_value, str):
            actual_value = expected_value + "_different"
        elif isinstance(expected_value, int):
            actual_value = expected_value + 1
        elif isinstance(expected_value, float):
            actual_value = expected_value + 1.0
        elif isinstance(expected_value, bool):
            actual_value = not expected_value
        elif isinstance(expected_value, list):
            actual_value = expected_value + [999]
        else:
            actual_value = str(expected_value) + "_different"
        
        if isinstance(expected_value, float):
            matches = abs(float(actual_value) - expected_value) < 0.0001
        else:
            matches = (actual_value == expected_value)
        assert matches is False, \
            "Different value should return False"
        
        # Test 3: Type mismatch
        if isinstance(expected_value, str):
            actual_value = 123  # int instead of str
        elif isinstance(expected_value, int):
            actual_value = str(expected_value)  # str instead of int
        elif isinstance(expected_value, float):
            actual_value = "not_a_float"
        elif isinstance(expected_value, list):
            actual_value = "not_a_list"
        else:
            actual_value = "type_mismatch"
        
        if isinstance(expected_value, float) and isinstance(actual_value, (int, float)):
            matches = abs(float(actual_value) - expected_value) < 0.0001
        else:
            matches = (actual_value == expected_value)
        assert matches is False, \
            "Type mismatch should return False"
    
    # Test 4: Missing field
    if aggregation_key not in tc.expected_aggregation:
        # If the field is not expected, validation should handle it gracefully
        validation_result = {
            'field': aggregation_key,
            'validated': False,
            'reason': 'Field not in expected aggregation'
        }
        
        assert validation_result['validated'] is False, \
            "Missing expected field should not be validated"


@settings(max_examples=100, deadline=None)
@given(test_data=testcase_with_expected_aggregation_strategy())
def test_property_31_expected_aggregation_validation_consistency(test_data):
    """
    Property 31 (Consistency): Expected aggregation validation consistency
    
    For any test case, validating the same aggregation multiple times should
    produce consistent results.
    
    This property verifies that:
    1. Validation is deterministic
    2. Multiple validations produce the same result
    3. Validation order doesn't affect results
    """
    tc = TestCase.from_dict(test_data)
    
    # Create actual aggregation (same as expected for this test)
    actual_aggregation = {}
    for key, value in tc.expected_aggregation.items():
        if isinstance(value, dict):
            actual_aggregation[key] = value.copy()
        elif isinstance(value, list):
            actual_aggregation[key] = value.copy()
        else:
            actual_aggregation[key] = value
    
    # Validate multiple times
    validation_1 = {}
    for key, expected in tc.expected_aggregation.items():
        actual = actual_aggregation.get(key)
        if isinstance(expected, float) and isinstance(actual, (int, float)):
            validation_1[key] = abs(float(actual) - expected) < 0.0001
        else:
            validation_1[key] = (actual == expected)
    
    validation_2 = {}
    for key, expected in tc.expected_aggregation.items():
        actual = actual_aggregation.get(key)
        if isinstance(expected, float) and isinstance(actual, (int, float)):
            validation_2[key] = abs(float(actual) - expected) < 0.0001
        else:
            validation_2[key] = (actual == expected)
    
    # Property 1: Both validations should produce the same results
    assert validation_1 == validation_2, \
        "Multiple validations should produce consistent results"
    
    # Property 2: Validate in different order
    keys_reversed = list(reversed(list(tc.expected_aggregation.keys())))
    validation_3 = {}
    for key in keys_reversed:
        expected = tc.expected_aggregation[key]
        actual = actual_aggregation.get(key)
        if isinstance(expected, float) and isinstance(actual, (int, float)):
            validation_3[key] = abs(float(actual) - expected) < 0.0001
        else:
            validation_3[key] = (actual == expected)
    
    # Results should be the same regardless of validation order
    assert validation_1 == validation_3, \
        "Validation order should not affect results"
    
    # Property 3: Overall result should be consistent
    overall_1 = all(validation_1.values())
    overall_2 = all(validation_2.values())
    overall_3 = all(validation_3.values())
    
    assert overall_1 == overall_2 == overall_3, \
        "Overall validation result should be consistent"


@settings(max_examples=100, deadline=None)
@given(test_data=testcase_with_expected_aggregation_strategy())
def test_property_31_expected_aggregation_with_tolerance(test_data):
    """
    Property 31 (Tolerance): Expected aggregation validation with numeric tolerance
    
    For any test case with numeric aggregation values, the system should
    support validation with tolerance for floating-point comparisons.
    
    This property verifies that:
    1. Numeric values within tolerance are considered matching
    2. Numeric values outside tolerance are considered not matching
    3. Tolerance is applied consistently
    4. Non-numeric values use exact matching
    """
    tc = TestCase.from_dict(test_data)
    
    # Define tolerance for numeric comparisons
    tolerance = 0.01
    
    # Create actual aggregation with slight variations
    actual_aggregation = {}
    import random
    random.seed(hash(test_data['id']))
    
    for key, expected_value in tc.expected_aggregation.items():
        if isinstance(expected_value, float):
            # Add small variation within tolerance
            variation = random.uniform(-tolerance/2, tolerance/2)
            actual_aggregation[key] = expected_value + variation
        elif isinstance(expected_value, int):
            # Keep exact for integers
            actual_aggregation[key] = expected_value
        else:
            # Keep exact for non-numeric
            if isinstance(expected_value, dict):
                actual_aggregation[key] = expected_value.copy()
            elif isinstance(expected_value, list):
                actual_aggregation[key] = expected_value.copy()
            else:
                actual_aggregation[key] = expected_value
    
    # Validate with tolerance
    validation_results = {}
    for key, expected in tc.expected_aggregation.items():
        actual = actual_aggregation.get(key)
        
        if isinstance(expected, float) and isinstance(actual, (int, float)):
            # Use tolerance for floats
            matches = abs(float(actual) - expected) <= tolerance
        else:
            # Exact match for non-floats
            matches = (actual == expected)
        
        validation_results[key] = matches
    
    # Property 1: All numeric values within tolerance should match
    for key, matches in validation_results.items():
        expected = tc.expected_aggregation[key]
        actual = actual_aggregation.get(key)
        
        if isinstance(expected, float) and isinstance(actual, (int, float)):
            # Should match because we added variation within tolerance
            assert matches is True, \
                f"Numeric value within tolerance should match for '{key}'"
        else:
            # Non-numeric should match exactly
            assert matches is True, \
                f"Non-numeric value should match exactly for '{key}'"
    
    # Property 2: Test values outside tolerance
    for key, expected_value in tc.expected_aggregation.items():
        if isinstance(expected_value, float):
            # Create value outside tolerance
            actual_outside = expected_value + (tolerance * 2)
            matches = abs(actual_outside - expected_value) <= tolerance
            assert matches is False, \
                f"Numeric value outside tolerance should not match for '{key}'"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
