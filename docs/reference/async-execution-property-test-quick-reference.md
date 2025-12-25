# Async Execution Property Tests - Quick Reference

## Overview
Property-based tests for async execution and progress query functionality (Property 35, Requirements 8.5).

## Test File
- **Location**: `tests/test_async_execution_properties.py`
- **Framework**: Hypothesis (property-based testing)
- **Test Count**: 15 tests across 5 classes

## Running Tests

```bash
# Run all async execution property tests
pytest tests/test_async_execution_properties.py -v

# Run specific test class
pytest tests/test_async_execution_properties.py::TestProgressQueryability -v

# Run with coverage
pytest tests/test_async_execution_properties.py --cov=src.api.execution_manager
```

## Test Classes

### TestAsyncExecutionCreation
Tests execution creation and immediate queryability.

**Key Properties**:
- Executions are immediately queryable after creation
- Status is accessible via API

### TestProgressQueryability
Tests progress information accessibility.

**Key Properties**:
- Progress data is queryable when available
- Progress accessible via dedicated API endpoint
- Graceful handling when no progress data exists

### TestExecutionStatusTransitions
Tests status lifecycle and transitions.

**Key Properties**:
- All status transitions are queryable
- Failed executions include error information
- Cancelled executions are properly tracked

### TestExecutionListing
Tests execution listing and filtering.

**Key Properties**:
- Executions can be listed and filtered
- Pagination works correctly

### TestProgressConsistency
Tests progress information accuracy.

**Key Properties**:
- Progress updates are consistently queryable
- Percentage calculations are accurate

### TestExecutionQueryRobustness
Tests error handling and edge cases.

**Key Properties**:
- Non-existent executions handled gracefully
- Concurrent queries return consistent results

## Property 35 Validation

**Property Statement**: For any long-running execution started asynchronously, the system should provide queryable progress information.

**Validated Aspects**:
1. ✅ Immediate queryability after creation
2. ✅ Progress information accessibility
3. ✅ Status transition tracking
4. ✅ Error information availability
5. ✅ Execution listing and filtering
6. ✅ Progress calculation accuracy
7. ✅ Graceful error handling
8. ✅ Concurrent query consistency

## Key Test Patterns

### Unique ID Generation
```python
def generate_unique_execution_id():
    return f"exec_{uuid.uuid4().hex[:12]}"

execution_id_strategy = st.builds(generate_unique_execution_id)
```

### Execution Manager Clearing
```python
# Clear executions for this example
execution_manager.executions.clear()
```

### Progress Validation
```python
# Verify progress is queryable
status = execution_manager.get_execution_status(execution_id)
assert status.progress is not None
assert status.progress.current_step == current_step
assert status.progress.total_steps == total_steps
```

## API Endpoints Tested

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/v1/executions` | POST | Create async execution |
| `/api/v1/executions` | GET | List executions |
| `/api/v1/executions/{id}` | GET | Get execution status |
| `/api/v1/executions/{id}/progress` | GET | Get execution progress |
| `/api/v1/executions/{id}/cancel` | POST | Cancel execution |

## Common Test Scenarios

### Testing Execution Creation
```python
@given(
    execution_id=execution_id_strategy,
    execution_type=st.sampled_from([ExecutionType.AGENT, ExecutionType.PIPELINE]),
    target_id=target_id_strategy,
    inputs=inputs_strategy,
    config=config_strategy
)
def test_execution_creation(execution_id, execution_type, target_id, inputs, config):
    record = execution_manager.create_execution(
        execution_id=execution_id,
        execution_type=execution_type,
        target_id=target_id,
        inputs=inputs,
        config=config
    )
    
    status = execution_manager.get_execution_status(execution_id)
    assert status is not None
    assert status.status == ExecutionStatus.PENDING
```

### Testing Progress Updates
```python
@given(
    execution_id=execution_id_strategy,
    current_step=st.integers(min_value=0, max_value=100),
    total_steps=st.integers(min_value=1, max_value=100)
)
def test_progress_updates(execution_id, current_step, total_steps):
    assume(current_step <= total_steps)
    
    record = execution_manager.create_execution(...)
    record.status = ExecutionStatus.RUNNING
    record.progress = ProgressInfo(
        current_step=current_step,
        total_steps=total_steps,
        percentage=(current_step / total_steps * 100)
    )
    
    status = execution_manager.get_execution_status(execution_id)
    assert status.progress.current_step == current_step
```

### Testing API Endpoints
```python
def test_api_endpoint(test_client, execution_manager):
    execution_manager.create_execution(...)
    
    response = test_client.get(f"/api/v1/executions/{execution_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["execution_id"] == execution_id
```

## Hypothesis Configuration

```python
@settings(
    max_examples=100,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture]
)
```

## Troubleshooting

### Issue: Execution ID Collisions
**Symptom**: `ValueError: Execution 'exec_xxx' already exists`

**Solution**: Use UUID-based unique ID generation:
```python
execution_id = f"exec_{uuid.uuid4().hex[:12]}"
```

### Issue: State Persistence Across Examples
**Symptom**: Tests fail due to leftover executions from previous examples

**Solution**: Clear execution manager at start of test:
```python
execution_manager.executions.clear()
```

### Issue: Pagination Count Mismatch
**Symptom**: `assert pagination["total_items"] == num_executions` fails

**Solution**: Ensure execution manager is cleared before creating test executions

## Related Documentation

- [Async Execution API Guide](./async-execution-api-guide.md)
- [Progress Query API Guide](./progress-query-api-guide.md)
- [API Design Specification](./api-design-specification.md)
- [Model Serialization Guide](./model-serialization-guide.md)

## Requirements Coverage

**Requirement 8.5**: Async execution and progress query
- ✅ Create async executions
- ✅ Query execution status
- ✅ Query execution progress
- ✅ List executions with filtering
- ✅ Cancel executions
- ✅ Handle errors gracefully

## Test Metrics

- **Total Tests**: 15
- **Property Tests**: 15
- **Example Count**: 50-100 per test
- **Total Examples**: ~1,000+
- **Execution Time**: ~5 seconds
- **Pass Rate**: 100%

## Best Practices

1. **Use Unique IDs**: Always generate unique execution IDs using UUID
2. **Clear State**: Clear execution manager state between examples
3. **Test All States**: Test pending, running, completed, failed, and cancelled states
4. **Verify API**: Test both direct calls and API endpoints
5. **Check Edge Cases**: Test non-existent executions and missing data
6. **Validate Progress**: Ensure progress percentages are accurate
7. **Test Concurrency**: Verify concurrent queries return consistent results

## Example Test Run

```bash
$ pytest tests/test_async_execution_properties.py -v

tests/test_async_execution_properties.py::TestAsyncExecutionCreation::test_async_execution_creation_provides_queryable_status PASSED
tests/test_async_execution_properties.py::TestAsyncExecutionCreation::test_execution_status_accessible_via_api PASSED
tests/test_async_execution_properties.py::TestProgressQueryability::test_progress_information_is_queryable PASSED
tests/test_async_execution_properties.py::TestProgressQueryability::test_progress_accessible_via_api PASSED
tests/test_async_execution_properties.py::TestProgressQueryability::test_progress_query_handles_no_progress_data PASSED
tests/test_async_execution_properties.py::TestExecutionStatusTransitions::test_status_transitions_are_queryable PASSED
tests/test_async_execution_properties.py::TestExecutionStatusTransitions::test_failed_execution_status_is_queryable PASSED
tests/test_async_execution_properties.py::TestExecutionStatusTransitions::test_cancelled_execution_status_is_queryable PASSED
tests/test_async_execution_properties.py::TestExecutionListing::test_executions_are_listable_and_filterable PASSED
tests/test_async_execution_properties.py::TestExecutionListing::test_execution_list_supports_pagination PASSED
tests/test_async_execution_properties.py::TestProgressConsistency::test_progress_updates_are_consistently_queryable PASSED
tests/test_async_execution_properties.py::TestProgressConsistency::test_progress_percentage_is_accurate PASSED
tests/test_async_execution_properties.py::TestExecutionQueryRobustness::test_query_nonexistent_execution_returns_none PASSED
tests/test_async_execution_properties.py::TestExecutionQueryRobustness::test_query_nonexistent_execution_via_api_returns_404 PASSED
tests/test_async_execution_properties.py::TestExecutionQueryRobustness::test_concurrent_status_queries_are_consistent PASSED

========================================= 15 passed in 4.86s =========================================
```
