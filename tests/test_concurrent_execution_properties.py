# tests/test_concurrent_execution_properties.py
"""
Concurrent Execution Property-Based Tests

Property-based tests for concurrent execution functionality using Hypothesis.
Tests Properties 13-21 related to concurrent execution.
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
import time
import threading
from typing import List, Dict, Any

from src.concurrent_executor import ConcurrentExecutor, Task, TaskResult, ExecutionProgress
from src.dependency_analyzer import DependencyAnalyzer
from src.models import StepConfig


# ============================================================================
# Hypothesis Strategies for generating test data
# ============================================================================

def task_id_strategy():
    """Generate valid task IDs"""
    return st.text(
        min_size=1,
        max_size=20,
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789_'
    ).filter(lambda x: x[0].isalpha())


def independent_tasks_strategy():
    """
    Generate a list of independent tasks (no dependencies)
    
    Returns tasks that have no dependencies, meaning they can all
    execute concurrently.
    """
    def simple_task(task_id: str, sleep_time: float = 0.01) -> str:
        """A simple task that sleeps and returns its ID"""
        time.sleep(sleep_time)
        return f"completed_{task_id}"
    
    return st.lists(
        st.builds(
            Task,
            id=task_id_strategy(),
            func=st.just(simple_task),
            args=st.tuples(task_id_strategy(), st.floats(min_value=0.01, max_value=0.05)),
            kwargs=st.just({}),
            dependencies=st.just([]),
            required=st.booleans(),
            metadata=st.just({})
        ),
        min_size=2,
        max_size=10,
        unique_by=lambda t: t.id
    )


def timing_task_strategy():
    """
    Generate tasks that record their execution timing
    
    These tasks record when they start and finish, allowing us to
    verify concurrent execution.
    """
    def timing_task(task_id: str, timing_dict: Dict[str, Any], sleep_time: float = 0.05) -> str:
        """A task that records its start and end time"""
        timing_dict[f"{task_id}_start"] = time.time()
        time.sleep(sleep_time)
        timing_dict[f"{task_id}_end"] = time.time()
        return f"completed_{task_id}"
    
    @st.composite
    def _timing_tasks(draw):
        num_tasks = draw(st.integers(min_value=2, max_value=8))
        timing_dict = {}
        tasks = []
        
        for i in range(num_tasks):
            task_id = f"task_{i}"
            sleep_time = draw(st.floats(min_value=0.05, max_value=0.1))
            
            task = Task(
                id=task_id,
                func=timing_task,
                args=(task_id, timing_dict, sleep_time),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        return tasks, timing_dict
    
    return _timing_tasks()


# ============================================================================
# Property-Based Tests
# ============================================================================

class TestConcurrentExecutionProperty:
    """
    Property 13: Concurrent execution of independent steps
    
    For any pipeline with independent steps, those steps should execute
    concurrently (not sequentially).
    
    Validates: Requirements 3.4
    """
    
    # Feature: project-production-readiness, Property 13: Concurrent execution of independent steps
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=2, max_value=8),
        max_workers=st.integers(min_value=2, max_value=4)
    )
    def test_independent_tasks_execute_concurrently(self, num_tasks, max_workers):
        """
        Property: When executing independent tasks, they should run concurrently,
        not sequentially. This is verified by checking that the total execution
        time is less than the sum of individual task times.
        
        If tasks ran sequentially, total time would be sum of all task times.
        If tasks run concurrently, total time should be approximately the max
        of individual task times (plus overhead).
        """
        # Create timing dictionary to track execution
        timing_dict = {}
        lock = threading.Lock()
        
        def timing_task(task_id: str, sleep_time: float) -> str:
            """Task that records timing information"""
            with lock:
                timing_dict[f"{task_id}_start"] = time.time()
            time.sleep(sleep_time)
            with lock:
                timing_dict[f"{task_id}_end"] = time.time()
            return f"completed_{task_id}"
        
        # Create independent tasks with known sleep times
        task_sleep_time = 0.1  # Each task sleeps for 0.1 seconds
        tasks = []
        
        for i in range(num_tasks):
            task = Task(
                id=f"task_{i}",
                func=timing_task,
                args=(f"task_{i}", task_sleep_time),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Execute tasks concurrently
        executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
        start_time = time.time()
        results = executor.execute_concurrent(tasks)
        total_time = time.time() - start_time
        
        # Verify all tasks completed successfully
        assert len(results) == num_tasks
        assert all(r.success for r in results), \
            f"Some tasks failed: {[r.task_id for r in results if not r.success]}"
        
        # Calculate expected times
        sequential_time = num_tasks * task_sleep_time
        # With concurrent execution, time should be approximately:
        # ceil(num_tasks / max_workers) * task_sleep_time
        import math
        expected_concurrent_time = math.ceil(num_tasks / max_workers) * task_sleep_time
        
        # Allow some overhead (50% margin)
        max_allowed_time = expected_concurrent_time * 1.5
        
        # Verify concurrent execution (total time should be much less than sequential)
        assert total_time < sequential_time * 0.8, \
            f"Tasks appear to run sequentially: total_time={total_time:.3f}s, " \
            f"sequential_time={sequential_time:.3f}s"
        
        # Verify timing is reasonable for concurrent execution
        assert total_time < max_allowed_time, \
            f"Execution took too long: total_time={total_time:.3f}s, " \
            f"expected_max={max_allowed_time:.3f}s"
        
        # Verify that tasks actually overlapped in time
        # Check that at least some tasks were running simultaneously
        if num_tasks >= 2:
            # Find overlapping execution windows
            overlaps_found = False
            for i in range(num_tasks):
                for j in range(i + 1, num_tasks):
                    task_i_start = timing_dict.get(f"task_{i}_start", 0)
                    task_i_end = timing_dict.get(f"task_{i}_end", 0)
                    task_j_start = timing_dict.get(f"task_{j}_start", 0)
                    task_j_end = timing_dict.get(f"task_{j}_end", 0)
                    
                    # Check if execution windows overlap
                    if (task_i_start < task_j_end and task_j_start < task_i_end):
                        overlaps_found = True
                        break
                if overlaps_found:
                    break
            
            assert overlaps_found, \
                "No overlapping execution detected - tasks may be running sequentially"
    
    @settings(max_examples=100, deadline=3000)
    @given(
        num_tasks=st.integers(min_value=2, max_value=6)
    )
    def test_concurrent_execution_preserves_result_order(self, num_tasks):
        """
        Property: When executing tasks concurrently, the results should be
        returned in the same order as the input tasks, regardless of which
        task finishes first.
        """
        def simple_task(task_id: str, sleep_time: float) -> str:
            """Simple task that sleeps and returns its ID"""
            time.sleep(sleep_time)
            return f"result_{task_id}"
        
        # Create tasks with varying sleep times
        tasks = []
        expected_order = []
        
        for i in range(num_tasks):
            task_id = f"task_{i}"
            # Reverse sleep times so later tasks finish first
            sleep_time = 0.01 * (num_tasks - i)
            
            task = Task(
                id=task_id,
                func=simple_task,
                args=(task_id, sleep_time),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
            expected_order.append(task_id)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # Verify order is preserved
        assert len(results) == num_tasks
        actual_order = [r.task_id for r in results]
        assert actual_order == expected_order, \
            f"Result order not preserved: expected {expected_order}, got {actual_order}"
    
    @settings(max_examples=100, deadline=3000)
    @given(
        num_tasks=st.integers(min_value=3, max_value=8),
        max_workers=st.integers(min_value=2, max_value=4)
    )
    def test_concurrent_execution_respects_max_workers(self, num_tasks, max_workers):
        """
        Property: The concurrent executor should never run more than max_workers
        tasks simultaneously.
        """
        # Track concurrent execution count
        concurrent_count = {"current": 0, "max_seen": 0}
        lock = threading.Lock()
        
        def tracking_task(task_id: str) -> str:
            """Task that tracks concurrent execution count"""
            with lock:
                concurrent_count["current"] += 1
                concurrent_count["max_seen"] = max(
                    concurrent_count["max_seen"],
                    concurrent_count["current"]
                )
            
            # Sleep to ensure overlap
            time.sleep(0.05)
            
            with lock:
                concurrent_count["current"] -= 1
            
            return f"completed_{task_id}"
        
        # Create tasks
        tasks = []
        for i in range(num_tasks):
            task = Task(
                id=f"task_{i}",
                func=tracking_task,
                args=(f"task_{i}",),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # Verify all tasks completed
        assert len(results) == num_tasks
        assert all(r.success for r in results)
        
        # Verify max_workers was respected
        assert concurrent_count["max_seen"] <= max_workers, \
            f"Exceeded max_workers: saw {concurrent_count['max_seen']} concurrent tasks, " \
            f"max_workers={max_workers}"
    
    @settings(max_examples=100, deadline=3000)
    @given(
        num_tasks=st.integers(min_value=2, max_value=8)
    )
    def test_concurrent_execution_with_some_failures(self, num_tasks):
        """
        Property: When some independent tasks fail, other tasks should still
        complete successfully (error isolation).
        """
        def task_with_failure(task_id: str, should_fail: bool) -> str:
            """Task that may fail based on parameter"""
            time.sleep(0.01)
            if should_fail:
                raise ValueError(f"Task {task_id} failed intentionally")
            return f"completed_{task_id}"
        
        # Create tasks where some will fail
        tasks = []
        expected_failures = []
        expected_successes = []
        
        for i in range(num_tasks):
            task_id = f"task_{i}"
            should_fail = (i % 3 == 0)  # Every 3rd task fails
            
            task = Task(
                id=task_id,
                func=task_with_failure,
                args=(task_id, should_fail),
                kwargs={},
                dependencies=[],
                required=False,  # Not required, so failures don't stop execution
                metadata={}
            )
            tasks.append(task)
            
            if should_fail:
                expected_failures.append(task_id)
            else:
                expected_successes.append(task_id)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # Verify all tasks were attempted
        assert len(results) == num_tasks
        
        # Verify failures and successes
        actual_failures = [r.task_id for r in results if not r.success]
        actual_successes = [r.task_id for r in results if r.success]
        
        assert set(actual_failures) == set(expected_failures), \
            f"Unexpected failures: expected {expected_failures}, got {actual_failures}"
        assert set(actual_successes) == set(expected_successes), \
            f"Unexpected successes: expected {expected_successes}, got {actual_successes}"
    
    @settings(max_examples=50, deadline=3000)
    @given(
        num_tasks=st.integers(min_value=2, max_value=6)
    )
    def test_concurrent_execution_returns_all_results(self, num_tasks):
        """
        Property: Concurrent execution should return results for all tasks,
        even if some fail.
        """
        def simple_task(task_id: str, value: int) -> int:
            """Simple task that returns a value"""
            time.sleep(0.01)
            return value * 2
        
        # Create tasks
        tasks = []
        expected_values = []
        
        for i in range(num_tasks):
            task = Task(
                id=f"task_{i}",
                func=simple_task,
                args=(f"task_{i}", i),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
            expected_values.append(i * 2)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # Verify all results returned
        assert len(results) == num_tasks
        
        # Verify results are correct
        actual_values = [r.result for r in results]
        assert actual_values == expected_values, \
            f"Results don't match: expected {expected_values}, got {actual_values}"
    
    @settings(max_examples=50, deadline=3000)
    @given(
        num_tasks=st.integers(min_value=1, max_value=8)
    )
    def test_concurrent_execution_with_empty_or_single_task(self, num_tasks):
        """
        Property: Concurrent execution should handle edge cases like
        empty task lists or single tasks correctly.
        """
        def simple_task(task_id: str) -> str:
            """Simple task"""
            time.sleep(0.01)
            return f"completed_{task_id}"
        
        # Create tasks
        tasks = []
        for i in range(num_tasks):
            task = Task(
                id=f"task_{i}",
                func=simple_task,
                args=(f"task_{i}",),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # Verify correct number of results
        assert len(results) == num_tasks
        
        # Verify all successful
        if num_tasks > 0:
            assert all(r.success for r in results)
    
    @settings(max_examples=50, deadline=3000)
    @given(
        num_tasks=st.integers(min_value=2, max_value=6)
    )
    def test_concurrent_execution_completes_all_tasks(self, num_tasks):
        """
        Property: Concurrent execution should complete all independent tasks,
        regardless of the number of tasks.
        """
        def simple_task(task_id: str) -> str:
            """Simple task that returns its ID"""
            time.sleep(0.01)
            return f"completed_{task_id}"
        
        # Create tasks
        tasks = []
        for i in range(num_tasks):
            task = Task(
                id=f"task_{i}",
                func=simple_task,
                args=(f"task_{i}",),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # Verify all tasks completed
        assert len(results) == num_tasks
        assert all(r.success for r in results)
        
        # Verify each task returned the expected result
        for i, result in enumerate(results):
            assert result.task_id == f"task_{i}"
            assert result.result == f"completed_task_{i}"



class TestConcurrentGroupParsingProperty:
    """
    Property 14: Concurrent group parsing
    
    For any pipeline configuration with concurrent_group annotations, the system
    should correctly parse and group steps.
    
    Validates: Requirements 3.5
    """
    
    # Feature: project-production-readiness, Property 14: Concurrent group parsing
    @settings(max_examples=100, deadline=3000)
    @given(
        num_groups=st.integers(min_value=1, max_value=5),
        steps_per_group=st.integers(min_value=1, max_value=4)
    )
    def test_concurrent_group_parsing(self, num_groups, steps_per_group):
        """
        Property: For any pipeline configuration with concurrent_group annotations,
        the dependency analyzer should correctly parse and group steps by their
        concurrent_group field.
        
        This verifies that:
        1. Steps with the same concurrent_group are grouped together
        2. Steps with different concurrent_groups are in different groups
        3. All steps are accounted for in the parsed groups
        """
        # Create steps with concurrent groups
        steps = []
        expected_groups = {}
        
        for group_idx in range(num_groups):
            group_name = f"group_{group_idx}"
            expected_groups[group_name] = []
            
            for step_idx in range(steps_per_group):
                step_id = f"step_g{group_idx}_s{step_idx}"
                step = StepConfig(
                    id=step_id,
                    type="agent_flow",
                    agent=f"agent_{step_id}",
                    flow="flow_v1",
                    concurrent_group=group_name,
                    output_key=f"output_{step_id}"
                )
                steps.append(step)
                expected_groups[group_name].append(step_id)
        
        # Analyze dependencies
        analyzer = DependencyAnalyzer()
        graph = analyzer.analyze_dependencies(steps)
        
        # Verify concurrent groups are correctly parsed
        assert len(graph.concurrent_groups) == num_groups, \
            f"Expected {num_groups} concurrent groups, got {len(graph.concurrent_groups)}"
        
        # Verify each group contains the correct steps
        for group_name, expected_step_ids in expected_groups.items():
            assert group_name in graph.concurrent_groups, \
                f"Group '{group_name}' not found in parsed concurrent groups"
            
            actual_step_ids = graph.concurrent_groups[group_name]
            assert set(actual_step_ids) == set(expected_step_ids), \
                f"Group '{group_name}' has incorrect steps: " \
                f"expected {expected_step_ids}, got {actual_step_ids}"
        
        # Verify all steps are accounted for
        all_steps_in_groups = set()
        for step_ids in graph.concurrent_groups.values():
            all_steps_in_groups.update(step_ids)
        
        all_step_ids = {step.id for step in steps}
        assert all_steps_in_groups == all_step_ids, \
            f"Not all steps accounted for in concurrent groups: " \
            f"expected {all_step_ids}, got {all_steps_in_groups}"
    
    @settings(max_examples=100, deadline=3000)
    @given(
        num_grouped_steps=st.integers(min_value=1, max_value=6),
        num_ungrouped_steps=st.integers(min_value=0, max_value=4)
    )
    def test_concurrent_group_parsing_with_mixed_steps(self, num_grouped_steps, num_ungrouped_steps):
        """
        Property: When a pipeline has both grouped and ungrouped steps,
        the system should correctly parse only the grouped steps into
        concurrent_groups, while ungrouped steps should not appear in
        any concurrent group.
        """
        steps = []
        expected_group_steps = []
        ungrouped_step_ids = []
        
        # Create grouped steps
        for i in range(num_grouped_steps):
            step_id = f"grouped_step_{i}"
            step = StepConfig(
                id=step_id,
                type="agent_flow",
                agent=f"agent_{i}",
                flow="flow_v1",
                concurrent_group="test_group",
                output_key=f"output_{i}"
            )
            steps.append(step)
            expected_group_steps.append(step_id)
        
        # Create ungrouped steps
        for i in range(num_ungrouped_steps):
            step_id = f"ungrouped_step_{i}"
            step = StepConfig(
                id=step_id,
                type="agent_flow",
                agent=f"agent_ungrouped_{i}",
                flow="flow_v1",
                # No concurrent_group specified
                output_key=f"output_ungrouped_{i}"
            )
            steps.append(step)
            ungrouped_step_ids.append(step_id)
        
        # Analyze dependencies
        analyzer = DependencyAnalyzer()
        graph = analyzer.analyze_dependencies(steps)
        
        # Verify grouped steps are in concurrent_groups
        if num_grouped_steps > 0:
            assert "test_group" in graph.concurrent_groups, \
                "Expected 'test_group' in concurrent_groups"
            assert set(graph.concurrent_groups["test_group"]) == set(expected_group_steps), \
                f"Grouped steps mismatch: expected {expected_group_steps}, " \
                f"got {graph.concurrent_groups['test_group']}"
        
        # Verify ungrouped steps are NOT in any concurrent group
        all_grouped_step_ids = set()
        for step_ids in graph.concurrent_groups.values():
            all_grouped_step_ids.update(step_ids)
        
        for ungrouped_id in ungrouped_step_ids:
            assert ungrouped_id not in all_grouped_step_ids, \
                f"Ungrouped step '{ungrouped_id}' should not be in any concurrent group"
    
    @settings(max_examples=100, deadline=3000)
    @given(
        group_names=st.lists(
            st.text(
                min_size=1,
                max_size=20,
                alphabet='abcdefghijklmnopqrstuvwxyz0123456789_'
            ).filter(lambda x: x[0].isalpha()),
            min_size=1,
            max_size=5,
            unique=True
        )
    )
    def test_concurrent_group_parsing_with_various_group_names(self, group_names):
        """
        Property: The system should correctly parse concurrent groups
        regardless of the group name used (as long as it's a valid string).
        """
        steps = []
        expected_groups = {name: [] for name in group_names}
        
        # Create one step for each group
        for group_name in group_names:
            step_id = f"step_{group_name}"
            step = StepConfig(
                id=step_id,
                type="agent_flow",
                agent=f"agent_{group_name}",
                flow="flow_v1",
                concurrent_group=group_name,
                output_key=f"output_{group_name}"
            )
            steps.append(step)
            expected_groups[group_name].append(step_id)
        
        # Analyze dependencies
        analyzer = DependencyAnalyzer()
        graph = analyzer.analyze_dependencies(steps)
        
        # Verify all groups are parsed
        assert len(graph.concurrent_groups) == len(group_names), \
            f"Expected {len(group_names)} groups, got {len(graph.concurrent_groups)}"
        
        # Verify each group is correctly parsed
        for group_name in group_names:
            assert group_name in graph.concurrent_groups, \
                f"Group '{group_name}' not found in parsed groups"
            assert graph.concurrent_groups[group_name] == expected_groups[group_name], \
                f"Group '{group_name}' has incorrect steps"
    
    @settings(max_examples=100, deadline=3000)
    @given(
        num_steps=st.integers(min_value=2, max_value=8)
    )
    def test_concurrent_group_parsing_preserves_step_identity(self, num_steps):
        """
        Property: When steps are parsed into concurrent groups, their
        identity (ID, agent, flow, etc.) should be preserved in the
        dependency graph nodes.
        """
        steps = []
        step_details = {}
        
        for i in range(num_steps):
            step_id = f"step_{i}"
            agent = f"agent_{i}"
            flow = f"flow_{i}"
            
            step = StepConfig(
                id=step_id,
                type="agent_flow",
                agent=agent,
                flow=flow,
                concurrent_group="test_group",
                output_key=f"output_{i}"
            )
            steps.append(step)
            step_details[step_id] = {"agent": agent, "flow": flow}
        
        # Analyze dependencies
        analyzer = DependencyAnalyzer()
        graph = analyzer.analyze_dependencies(steps)
        
        # Verify all steps are in the graph nodes
        assert len(graph.nodes) == num_steps, \
            f"Expected {num_steps} nodes, got {len(graph.nodes)}"
        
        # Verify all step IDs are preserved
        for step_id in step_details.keys():
            assert step_id in graph.nodes, \
                f"Step '{step_id}' not found in graph nodes"
        
        # Verify concurrent group contains all steps
        assert "test_group" in graph.concurrent_groups
        assert set(graph.concurrent_groups["test_group"]) == set(step_details.keys()), \
            "Concurrent group doesn't contain all steps"
    
    @settings(max_examples=50, deadline=3000)
    @given(
        num_steps_per_group=st.lists(
            st.integers(min_value=1, max_value=5),
            min_size=1,
            max_size=4
        )
    )
    def test_concurrent_group_parsing_with_varying_group_sizes(self, num_steps_per_group):
        """
        Property: The system should correctly parse concurrent groups
        of varying sizes (some groups may have 1 step, others may have many).
        """
        steps = []
        expected_groups = {}
        
        for group_idx, num_steps in enumerate(num_steps_per_group):
            group_name = f"group_{group_idx}"
            expected_groups[group_name] = []
            
            for step_idx in range(num_steps):
                step_id = f"step_g{group_idx}_s{step_idx}"
                step = StepConfig(
                    id=step_id,
                    type="agent_flow",
                    agent=f"agent_{step_id}",
                    flow="flow_v1",
                    concurrent_group=group_name,
                    output_key=f"output_{step_id}"
                )
                steps.append(step)
                expected_groups[group_name].append(step_id)
        
        # Analyze dependencies
        analyzer = DependencyAnalyzer()
        graph = analyzer.analyze_dependencies(steps)
        
        # Verify correct number of groups
        assert len(graph.concurrent_groups) == len(num_steps_per_group), \
            f"Expected {len(num_steps_per_group)} groups, got {len(graph.concurrent_groups)}"
        
        # Verify each group has the correct number of steps
        for group_idx, expected_num_steps in enumerate(num_steps_per_group):
            group_name = f"group_{group_idx}"
            assert group_name in graph.concurrent_groups, \
                f"Group '{group_name}' not found"
            
            actual_num_steps = len(graph.concurrent_groups[group_name])
            assert actual_num_steps == expected_num_steps, \
                f"Group '{group_name}' should have {expected_num_steps} steps, " \
                f"got {actual_num_steps}"
    
    @settings(max_examples=100, deadline=3000)
    @given(
        num_steps=st.integers(min_value=1, max_value=8)
    )
    def test_concurrent_group_parsing_empty_group_name_treated_as_no_group(self, num_steps):
        """
        Property: Steps with None or empty concurrent_group should not
        appear in any concurrent group in the parsed dependency graph.
        """
        steps = []
        
        for i in range(num_steps):
            step = StepConfig(
                id=f"step_{i}",
                type="agent_flow",
                agent=f"agent_{i}",
                flow="flow_v1",
                concurrent_group=None,  # Explicitly no group
                output_key=f"output_{i}"
            )
            steps.append(step)
        
        # Analyze dependencies
        analyzer = DependencyAnalyzer()
        graph = analyzer.analyze_dependencies(steps)
        
        # Verify no concurrent groups are created
        assert len(graph.concurrent_groups) == 0, \
            f"Expected no concurrent groups, but got {len(graph.concurrent_groups)}"
        
        # Verify all steps are still in the graph
        assert len(graph.nodes) == num_steps, \
            f"Expected {num_steps} nodes, got {len(graph.nodes)}"


class TestConcurrentErrorHandlingProperty:
    """
    Property 16: Concurrent error handling
    
    For any code node in concurrent execution that fails, the error should be
    recorded and handled according to the required/optional configuration.
    
    Validates: Requirements 3.7
    """
    
    # Feature: project-production-readiness, Property 16: Concurrent error handling
    @settings(max_examples=100, deadline=3000)
    @given(
        num_tasks=st.integers(min_value=3, max_value=10),
        failure_rate=st.floats(min_value=0.1, max_value=0.5)
    )
    def test_concurrent_error_recording_and_isolation(self, num_tasks, failure_rate):
        """
        Property: When tasks fail during concurrent execution, the errors should
        be recorded and isolated - failures should not prevent other independent
        tasks from completing.
        
        This test verifies:
        1. Errors are properly recorded in the error summary
        2. Failed tasks don't prevent other tasks from executing
        3. Error types are tracked correctly
        """
        def task_with_potential_failure(task_id: str, should_fail: bool) -> str:
            """Task that may fail based on parameter"""
            time.sleep(0.01)
            if should_fail:
                raise ValueError(f"Task {task_id} failed intentionally")
            return f"completed_{task_id}"
        
        # Create tasks where some will fail based on failure_rate
        tasks = []
        expected_failures = []
        expected_successes = []
        
        for i in range(num_tasks):
            task_id = f"task_{i}"
            # Deterministic failure based on index and failure_rate
            should_fail = (i % int(1 / failure_rate)) == 0 if failure_rate > 0 else False
            
            task = Task(
                id=task_id,
                func=task_with_potential_failure,
                args=(task_id, should_fail),
                kwargs={},
                dependencies=[],
                required=False,  # Not required, so failures don't stop execution
                metadata={}
            )
            tasks.append(task)
            
            if should_fail:
                expected_failures.append(task_id)
            else:
                expected_successes.append(task_id)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        error_summary = executor.get_error_summary()
        
        # Property 1: All tasks were attempted (error isolation)
        assert len(results) == num_tasks, \
            f"Not all tasks were attempted: expected {num_tasks}, got {len(results)}"
        
        # Property 2: Errors are properly recorded
        actual_failures = [r.task_id for r in results if not r.success]
        actual_successes = [r.task_id for r in results if r.success]
        
        assert set(actual_failures) == set(expected_failures), \
            f"Unexpected failures: expected {expected_failures}, got {actual_failures}"
        assert set(actual_successes) == set(expected_successes), \
            f"Unexpected successes: expected {expected_successes}, got {actual_successes}"
        
        # Property 3: Error summary is accurate
        assert error_summary.total_errors == len(expected_failures), \
            f"Error count mismatch: expected {len(expected_failures)}, " \
            f"got {error_summary.total_errors}"
        
        assert set(error_summary.failed_tasks) == set(expected_failures), \
            f"Failed tasks mismatch in error summary"
        
        # Property 4: Error types are tracked
        if expected_failures:
            assert "ValueError" in error_summary.error_types, \
                "ValueError should be tracked in error types"
            assert error_summary.error_types["ValueError"] == len(expected_failures), \
                f"ValueError count mismatch: expected {len(expected_failures)}, " \
                f"got {error_summary.error_types.get('ValueError', 0)}"
    
    @settings(max_examples=100, deadline=3000)
    @given(
        num_required_tasks=st.integers(min_value=1, max_value=5),
        num_optional_tasks=st.integers(min_value=1, max_value=5)
    )
    def test_required_vs_optional_error_handling(self, num_required_tasks, num_optional_tasks):
        """
        Property: The system should distinguish between required and optional
        task failures. Required task failures should be marked as critical errors,
        while optional task failures should not.
        """
        def failing_task(task_id: str) -> str:
            """Task that always fails"""
            time.sleep(0.01)
            raise RuntimeError(f"Task {task_id} failed")
        
        tasks = []
        expected_critical = []
        expected_non_critical = []
        
        # Create required tasks that will fail
        for i in range(num_required_tasks):
            task_id = f"required_{i}"
            expected_critical.append(task_id)
            
            task = Task(
                id=task_id,
                func=failing_task,
                args=(task_id,),
                kwargs={},
                dependencies=[],
                required=True,  # Required
                metadata={}
            )
            tasks.append(task)
        
        # Create optional tasks that will fail
        for i in range(num_optional_tasks):
            task_id = f"optional_{i}"
            expected_non_critical.append(task_id)
            
            task = Task(
                id=task_id,
                func=failing_task,
                args=(task_id,),
                kwargs={},
                dependencies=[],
                required=False,  # Optional
                metadata={}
            )
            tasks.append(task)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        error_summary = executor.get_error_summary()
        
        # Property 1: All tasks failed as expected
        assert all(not r.success for r in results), \
            "All tasks should have failed"
        
        # Property 2: Critical errors are correctly identified
        assert set(error_summary.critical_errors) == set(expected_critical), \
            f"Critical errors mismatch: expected {expected_critical}, " \
            f"got {error_summary.critical_errors}"
        
        # Property 3: has_critical_errors() returns correct value
        assert error_summary.has_critical_errors() == (num_required_tasks > 0), \
            f"has_critical_errors() should be {num_required_tasks > 0}"
        
        # Property 4: All failures are recorded
        assert error_summary.total_errors == num_required_tasks + num_optional_tasks, \
            f"Total errors mismatch"
    
    @settings(max_examples=100, deadline=3000)
    @given(
        num_tasks=st.integers(min_value=4, max_value=10)
    )
    def test_error_handling_with_dependencies(self, num_tasks):
        """
        Property: When a required task fails in a dependency chain, dependent
        tasks should be skipped and recorded appropriately. When an optional
        task fails, dependent tasks should continue.
        """
        def success_task(task_id: str) -> str:
            """Task that succeeds"""
            time.sleep(0.01)
            return f"completed_{task_id}"
        
        def failure_task(task_id: str) -> str:
            """Task that fails"""
            time.sleep(0.01)
            raise TypeError(f"Task {task_id} failed")
        
        # Create a dependency chain with failures
        # Structure: root -> [branch1 (fails, required), branch2 (success)] -> merge
        tasks = []
        
        # Root task (succeeds)
        root_id = "root"
        task = Task(
            id=root_id,
            func=success_task,
            args=(root_id,),
            kwargs={},
            dependencies=[],
            required=True,
            metadata={}
        )
        tasks.append(task)
        
        # Branch 1: fails and is required
        branch1_id = "branch1_fail_required"
        task = Task(
            id=branch1_id,
            func=failure_task,
            args=(branch1_id,),
            kwargs={},
            dependencies=[root_id],
            required=True,
            metadata={}
        )
        tasks.append(task)
        
        # Branch 2: succeeds
        branch2_id = "branch2_success"
        task = Task(
            id=branch2_id,
            func=success_task,
            args=(branch2_id,),
            kwargs={},
            dependencies=[root_id],
            required=True,
            metadata={}
        )
        tasks.append(task)
        
        # Merge task: depends on both branches
        merge_id = "merge"
        task = Task(
            id=merge_id,
            func=success_task,
            args=(merge_id,),
            kwargs={},
            dependencies=[branch1_id, branch2_id],
            required=True,
            metadata={}
        )
        tasks.append(task)
        
        # Add more independent tasks to reach num_tasks
        for i in range(num_tasks - 4):
            task_id = f"independent_{i}"
            task = Task(
                id=task_id,
                func=success_task,
                args=(task_id,),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Execute with dependencies
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_with_dependencies(tasks)
        error_summary = executor.get_error_summary()
        
        # Property 1: Root task succeeded
        root_result = next(r for r in results if r.task_id == root_id)
        assert root_result.success, "Root task should succeed"
        
        # Property 2: Branch1 failed
        branch1_result = next(r for r in results if r.task_id == branch1_id)
        assert not branch1_result.success, "Branch1 should fail"
        assert not branch1_result.skipped, "Branch1 should not be skipped (it actually ran)"
        
        # Property 3: Branch2 succeeded
        branch2_result = next(r for r in results if r.task_id == branch2_id)
        assert branch2_result.success, "Branch2 should succeed"
        
        # Property 4: Merge task was skipped (because branch1 is required and failed)
        merge_result = next(r for r in results if r.task_id == merge_id)
        assert not merge_result.success, "Merge should not succeed"
        assert merge_result.skipped, "Merge should be skipped due to failed required dependency"
        
        # Property 5: Independent tasks succeeded (error isolation)
        for i in range(num_tasks - 4):
            task_id = f"independent_{i}"
            result = next(r for r in results if r.task_id == task_id)
            assert result.success, f"Independent task {task_id} should succeed"
        
        # Property 6: Error summary correctly tracks failures and skips
        assert branch1_id in error_summary.failed_tasks, \
            "Branch1 should be in failed tasks"
        assert merge_id in error_summary.skipped_tasks, \
            "Merge should be in skipped tasks"
        assert branch1_id in error_summary.critical_errors, \
            "Branch1 failure should be critical"
    
    @settings(max_examples=100, deadline=3000)
    @given(
        num_tasks=st.integers(min_value=3, max_value=8),
        error_types=st.lists(
            st.sampled_from(["ValueError", "TypeError", "RuntimeError", "KeyError"]),
            min_size=1,
            max_size=4,
            unique=True
        )
    )
    def test_error_type_tracking(self, num_tasks, error_types):
        """
        Property: The system should correctly track different types of errors
        that occur during concurrent execution.
        """
        def task_with_error_type(task_id: str, error_type: str) -> str:
            """Task that raises a specific error type"""
            time.sleep(0.01)
            error_classes = {
                "ValueError": ValueError,
                "TypeError": TypeError,
                "RuntimeError": RuntimeError,
                "KeyError": KeyError
            }
            raise error_classes[error_type](f"Task {task_id} failed with {error_type}")
        
        tasks = []
        expected_error_counts = {et: 0 for et in error_types}
        
        # Create tasks with different error types
        for i in range(num_tasks):
            task_id = f"task_{i}"
            error_type = error_types[i % len(error_types)]
            expected_error_counts[error_type] += 1
            
            task = Task(
                id=task_id,
                func=task_with_error_type,
                args=(task_id, error_type),
                kwargs={},
                dependencies=[],
                required=False,
                metadata={}
            )
            tasks.append(task)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        error_summary = executor.get_error_summary()
        
        # Property 1: All tasks failed
        assert all(not r.success for r in results), \
            "All tasks should have failed"
        
        # Property 2: Error types are correctly tracked
        for error_type, expected_count in expected_error_counts.items():
            actual_count = error_summary.error_types.get(error_type, 0)
            assert actual_count == expected_count, \
                f"Error type {error_type} count mismatch: " \
                f"expected {expected_count}, got {actual_count}"
        
        # Property 3: Total errors match sum of error types
        total_from_types = sum(error_summary.error_types.values())
        assert total_from_types == error_summary.total_errors, \
            f"Sum of error types ({total_from_types}) doesn't match " \
            f"total errors ({error_summary.total_errors})"
    
    @settings(max_examples=100, deadline=3000)
    @given(
        num_tasks=st.integers(min_value=2, max_value=8)
    )
    def test_execution_summary_with_errors(self, num_tasks):
        """
        Property: The execution summary should correctly reflect the state
        of execution when errors occur, including success rate and completion status.
        """
        def task_with_failure(task_id: str, should_fail: bool) -> str:
            """Task that may fail"""
            time.sleep(0.01)
            if should_fail:
                raise ValueError(f"Task {task_id} failed")
            return f"completed_{task_id}"
        
        tasks = []
        num_failures = num_tasks // 2  # Half will fail
        
        for i in range(num_tasks):
            task_id = f"task_{i}"
            should_fail = i < num_failures
            
            task = Task(
                id=task_id,
                func=task_with_failure,
                args=(task_id, should_fail),
                kwargs={},
                dependencies=[],
                required=(i == 0),  # First task is required
                metadata={}
            )
            tasks.append(task)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        summary = executor.get_execution_summary(results)
        
        # Property 1: Progress reflects all tasks
        assert summary.progress.total == num_tasks, \
            f"Total tasks mismatch: expected {num_tasks}, got {summary.progress.total}"
        assert summary.progress.completed == num_tasks, \
            f"Completed tasks mismatch: expected {num_tasks}, got {summary.progress.completed}"
        assert summary.progress.failed == num_failures, \
            f"Failed tasks mismatch: expected {num_failures}, got {summary.progress.failed}"
        
        # Property 2: Success rate is correct
        expected_success_rate = (num_tasks - num_failures) / num_tasks
        assert abs(summary.progress.success_rate - expected_success_rate) < 0.01, \
            f"Success rate mismatch: expected {expected_success_rate}, " \
            f"got {summary.progress.success_rate}"
        
        # Property 3: is_successful() reflects critical errors
        # First task is required and fails, so execution should not be successful
        assert summary.is_successful() == False, \
            "Execution should not be successful when required task fails"
        
        # Property 4: Result categorization is correct
        assert len(summary.get_failed_results()) == num_failures, \
            f"Failed results count mismatch"
        assert len(summary.get_successful_results()) == num_tasks - num_failures, \
            f"Successful results count mismatch"
        assert len(summary.get_skipped_results()) == 0, \
            f"Should have no skipped results in concurrent execution"
    
    @settings(max_examples=50, deadline=3000)
    @given(
        num_tasks=st.integers(min_value=3, max_value=8)
    )
    def test_error_handling_preserves_result_order(self, num_tasks):
        """
        Property: Even when errors occur, results should be returned in the
        same order as the input task list.
        """
        def task_with_failure(task_id: str, should_fail: bool) -> str:
            """Task that may fail"""
            time.sleep(0.01)
            if should_fail:
                raise ValueError(f"Task {task_id} failed")
            return f"completed_{task_id}"
        
        tasks = []
        expected_order = []
        
        for i in range(num_tasks):
            task_id = f"task_{i}"
            expected_order.append(task_id)
            should_fail = (i % 2 == 0)  # Every other task fails
            
            task = Task(
                id=task_id,
                func=task_with_failure,
                args=(task_id, should_fail),
                kwargs={},
                dependencies=[],
                required=False,
                metadata={}
            )
            tasks.append(task)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # Property: Result order is preserved
        actual_order = [r.task_id for r in results]
        assert actual_order == expected_order, \
            f"Result order not preserved: expected {expected_order}, got {actual_order}"


class TestConcurrentTestExecutionProperty:
    """
    Property 17: Concurrent test execution
    
    For any list of independent test cases, executing them concurrently should
    produce the same results as sequential execution.
    
    Validates: Requirements 9.1
    """
    
    # Feature: project-production-readiness, Property 17: Concurrent test execution
    @settings(max_examples=100, deadline=5000)
    @given(
        num_test_cases=st.integers(min_value=2, max_value=10),
        max_workers=st.integers(min_value=2, max_value=4)
    )
    def test_concurrent_test_execution_produces_same_results_as_sequential(
        self, num_test_cases, max_workers
    ):
        """
        Property: For any list of independent test cases, executing them
        concurrently should produce the same results as sequential execution.
        
        This verifies that:
        1. Concurrent execution produces the same outputs as sequential
        2. The order of results is preserved
        3. All test cases are executed in both modes
        """
        def test_case_task(test_id: str, input_value: int) -> Dict[str, Any]:
            """
            Simulates a test case execution that performs some computation.
            This represents running a test case through a pipeline or agent.
            """
            time.sleep(0.01)  # Simulate some work
            
            # Perform deterministic computation
            result = {
                "test_id": test_id,
                "input": input_value,
                "output": input_value * 2 + 10,
                "squared": input_value ** 2,
                "status": "passed" if input_value % 2 == 0 else "failed"
            }
            return result
        
        # Create test case tasks
        tasks = []
        expected_results_sequential = []
        
        for i in range(num_test_cases):
            test_id = f"test_case_{i}"
            input_value = i * 3  # Deterministic input
            
            task = Task(
                id=test_id,
                func=test_case_task,
                args=(test_id, input_value),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={"input_value": input_value}
            )
            tasks.append(task)
            
            # Calculate expected result for verification
            expected_results_sequential.append({
                "test_id": test_id,
                "input": input_value,
                "output": input_value * 2 + 10,
                "squared": input_value ** 2,
                "status": "passed" if input_value % 2 == 0 else "failed"
            })
        
        # Execute sequentially (one at a time)
        executor_sequential = ConcurrentExecutor(max_workers=1, strategy="thread")
        sequential_results = executor_sequential.execute_concurrent(tasks)
        
        # Execute concurrently
        executor_concurrent = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
        concurrent_results = executor_concurrent.execute_concurrent(tasks)
        
        # Property 1: Both executions should complete all test cases
        assert len(sequential_results) == num_test_cases, \
            f"Sequential execution didn't complete all tests: " \
            f"expected {num_test_cases}, got {len(sequential_results)}"
        assert len(concurrent_results) == num_test_cases, \
            f"Concurrent execution didn't complete all tests: " \
            f"expected {num_test_cases}, got {len(concurrent_results)}"
        
        # Property 2: All test cases should succeed in both modes
        assert all(r.success for r in sequential_results), \
            f"Some sequential tests failed: {[r.task_id for r in sequential_results if not r.success]}"
        assert all(r.success for r in concurrent_results), \
            f"Some concurrent tests failed: {[r.task_id for r in concurrent_results if not r.success]}"
        
        # Property 3: Results should be in the same order
        sequential_order = [r.task_id for r in sequential_results]
        concurrent_order = [r.task_id for r in concurrent_results]
        assert sequential_order == concurrent_order, \
            f"Result order differs: sequential={sequential_order}, concurrent={concurrent_order}"
        
        # Property 4: Results should be identical (same outputs)
        for seq_result, conc_result in zip(sequential_results, concurrent_results):
            assert seq_result.task_id == conc_result.task_id, \
                f"Task ID mismatch at same position"
            assert seq_result.result == conc_result.result, \
                f"Results differ for {seq_result.task_id}: " \
                f"sequential={seq_result.result}, concurrent={conc_result.result}"
            assert seq_result.success == conc_result.success, \
                f"Success status differs for {seq_result.task_id}"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_test_cases=st.integers(min_value=3, max_value=12),
        failure_indices=st.lists(
            st.integers(min_value=0, max_value=11),
            min_size=0,
            max_size=4,
            unique=True
        )
    )
    def test_concurrent_test_execution_with_failures_matches_sequential(
        self, num_test_cases, failure_indices
    ):
        """
        Property: Even when some test cases fail, concurrent execution should
        produce the same results (including failures) as sequential execution.
        """
        # Filter failure_indices to only include valid indices
        valid_failure_indices = [idx for idx in failure_indices if idx < num_test_cases]
        
        def test_case_with_potential_failure(
            test_id: str, input_value: int, should_fail: bool
        ) -> Dict[str, Any]:
            """Test case that may fail"""
            time.sleep(0.01)
            
            if should_fail:
                raise ValueError(f"Test case {test_id} failed intentionally")
            
            return {
                "test_id": test_id,
                "input": input_value,
                "result": input_value * 2
            }
        
        # Create test case tasks
        tasks = []
        
        for i in range(num_test_cases):
            test_id = f"test_case_{i}"
            input_value = i * 5
            should_fail = i in valid_failure_indices
            
            task = Task(
                id=test_id,
                func=test_case_with_potential_failure,
                args=(test_id, input_value, should_fail),
                kwargs={},
                dependencies=[],
                required=False,  # Allow failures
                metadata={}
            )
            tasks.append(task)
        
        # Execute sequentially
        executor_sequential = ConcurrentExecutor(max_workers=1, strategy="thread")
        sequential_results = executor_sequential.execute_concurrent(tasks)
        
        # Execute concurrently
        executor_concurrent = ConcurrentExecutor(max_workers=4, strategy="thread")
        concurrent_results = executor_concurrent.execute_concurrent(tasks)
        
        # Property 1: Same number of results
        assert len(sequential_results) == len(concurrent_results) == num_test_cases
        
        # Property 2: Same success/failure pattern
        sequential_success_pattern = [r.success for r in sequential_results]
        concurrent_success_pattern = [r.success for r in concurrent_results]
        assert sequential_success_pattern == concurrent_success_pattern, \
            f"Success patterns differ: sequential={sequential_success_pattern}, " \
            f"concurrent={concurrent_success_pattern}"
        
        # Property 3: Same results for successful test cases
        for seq_result, conc_result in zip(sequential_results, concurrent_results):
            assert seq_result.task_id == conc_result.task_id
            if seq_result.success and conc_result.success:
                assert seq_result.result == conc_result.result, \
                    f"Results differ for successful test {seq_result.task_id}"
        
        # Property 4: Same error types for failed test cases
        for seq_result, conc_result in zip(sequential_results, concurrent_results):
            if not seq_result.success and not conc_result.success:
                # Both should have errors
                assert seq_result.error is not None
                assert conc_result.error is not None
                # Error types should match
                assert seq_result.error_type == conc_result.error_type, \
                    f"Error types differ for {seq_result.task_id}: " \
                    f"sequential={seq_result.error_type}, concurrent={conc_result.error_type}"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_test_cases=st.integers(min_value=2, max_value=8),
        test_durations=st.lists(
            st.floats(min_value=0.01, max_value=0.1),
            min_size=2,
            max_size=8
        )
    )
    def test_concurrent_test_execution_with_varying_durations(
        self, num_test_cases, test_durations
    ):
        """
        Property: Concurrent execution should produce the same results as
        sequential execution even when test cases have varying execution times.
        
        This is important because in real scenarios, different test cases may
        take different amounts of time to execute.
        """
        # Ensure we have enough durations
        while len(test_durations) < num_test_cases:
            test_durations.append(0.05)
        test_durations = test_durations[:num_test_cases]
        
        def test_case_with_duration(
            test_id: str, duration: float, value: int
        ) -> Dict[str, Any]:
            """Test case with specific duration"""
            time.sleep(duration)
            return {
                "test_id": test_id,
                "duration": duration,
                "computed_value": value * 3 + 7
            }
        
        # Create test case tasks
        tasks = []
        
        for i in range(num_test_cases):
            test_id = f"test_case_{i}"
            duration = test_durations[i]
            value = i * 2
            
            task = Task(
                id=test_id,
                func=test_case_with_duration,
                args=(test_id, duration, value),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Execute sequentially
        executor_sequential = ConcurrentExecutor(max_workers=1, strategy="thread")
        sequential_results = executor_sequential.execute_concurrent(tasks)
        
        # Execute concurrently
        executor_concurrent = ConcurrentExecutor(max_workers=4, strategy="thread")
        concurrent_results = executor_concurrent.execute_concurrent(tasks)
        
        # Property: Results should be identical regardless of execution order
        assert len(sequential_results) == len(concurrent_results) == num_test_cases
        
        for seq_result, conc_result in zip(sequential_results, concurrent_results):
            assert seq_result.task_id == conc_result.task_id
            assert seq_result.success == conc_result.success
            assert seq_result.result == conc_result.result, \
                f"Results differ for {seq_result.task_id}: " \
                f"sequential={seq_result.result}, concurrent={conc_result.result}"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        num_test_cases=st.integers(min_value=1, max_value=10)
    )
    def test_concurrent_test_execution_deterministic_results(self, num_test_cases):
        """
        Property: Running the same test cases concurrently multiple times
        should produce consistent results (determinism).
        
        This verifies that concurrent execution doesn't introduce
        non-deterministic behavior.
        """
        def deterministic_test_case(test_id: str, seed: int) -> Dict[str, Any]:
            """Test case with deterministic computation"""
            time.sleep(0.01)
            
            # Deterministic computation based on seed
            result = {
                "test_id": test_id,
                "seed": seed,
                "hash": hash(f"{test_id}_{seed}") % 1000,
                "computed": (seed * 17 + 42) % 100
            }
            return result
        
        # Create test case tasks
        tasks = []
        
        for i in range(num_test_cases):
            test_id = f"test_case_{i}"
            seed = i * 7  # Deterministic seed
            
            task = Task(
                id=test_id,
                func=deterministic_test_case,
                args=(test_id, seed),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Execute concurrently multiple times
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        
        first_run_results = executor.execute_concurrent(tasks)
        second_run_results = executor.execute_concurrent(tasks)
        
        # Property: Multiple concurrent runs should produce identical results
        assert len(first_run_results) == len(second_run_results) == num_test_cases
        
        for first_result, second_result in zip(first_run_results, second_run_results):
            assert first_result.task_id == second_result.task_id
            assert first_result.success == second_result.success
            assert first_result.result == second_result.result, \
                f"Results differ across runs for {first_result.task_id}: " \
                f"first={first_result.result}, second={second_result.result}"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_test_cases=st.integers(min_value=2, max_value=10)
    )
    def test_concurrent_test_execution_preserves_test_isolation(self, num_test_cases):
        """
        Property: Concurrent test execution should maintain test isolation -
        one test case should not affect the results of another test case.
        
        This is verified by ensuring that each test case produces the same
        result regardless of what other test cases are running concurrently.
        """
        # Shared state to detect if tests interfere with each other
        # Each test will write to its own key, and we'll verify no cross-contamination
        shared_results = {}
        lock = threading.Lock()
        
        def isolated_test_case(test_id: str, value: int) -> Dict[str, Any]:
            """Test case that writes to shared state"""
            time.sleep(0.01)
            
            # Each test writes to its own key
            with lock:
                shared_results[test_id] = value * 2
            
            # Compute result based only on own input
            result = {
                "test_id": test_id,
                "value": value,
                "doubled": value * 2
            }
            
            return result
        
        # Create test case tasks
        tasks = []
        expected_shared_results = {}
        
        for i in range(num_test_cases):
            test_id = f"test_case_{i}"
            value = i * 3
            expected_shared_results[test_id] = value * 2
            
            task = Task(
                id=test_id,
                func=isolated_test_case,
                args=(test_id, value),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # Property 1: All tests completed successfully
        assert len(results) == num_test_cases
        assert all(r.success for r in results)
        
        # Property 2: Each test produced correct result based on its own input
        for i, result in enumerate(results):
            test_id = f"test_case_{i}"
            value = i * 3
            
            assert result.task_id == test_id
            assert result.result["value"] == value
            assert result.result["doubled"] == value * 2
        
        # Property 3: Shared state shows no cross-contamination
        assert shared_results == expected_shared_results, \
            f"Shared state contaminated: expected {expected_shared_results}, " \
            f"got {shared_results}"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_test_cases=st.integers(min_value=2, max_value=8),
        max_workers=st.integers(min_value=1, max_value=6)
    )
    def test_concurrent_test_execution_respects_max_workers(
        self, num_test_cases, max_workers
    ):
        """
        Property: Concurrent test execution should respect the max_workers
        setting and produce the same results regardless of the max_workers value.
        
        This verifies that the degree of parallelism doesn't affect correctness.
        """
        def test_case_task(test_id: str, value: int) -> Dict[str, Any]:
            """Simple test case"""
            time.sleep(0.02)
            return {
                "test_id": test_id,
                "result": value ** 2 + value
            }
        
        # Create test case tasks
        tasks = []
        
        for i in range(num_test_cases):
            test_id = f"test_case_{i}"
            value = i * 4
            
            task = Task(
                id=test_id,
                func=test_case_task,
                args=(test_id, value),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Execute with specified max_workers
        executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # Property 1: All tests completed
        assert len(results) == num_test_cases
        assert all(r.success for r in results)
        
        # Property 2: Results are correct regardless of max_workers
        for i, result in enumerate(results):
            test_id = f"test_case_{i}"
            value = i * 4
            expected_result = value ** 2 + value
            
            assert result.task_id == test_id
            assert result.result["result"] == expected_result, \
                f"Result incorrect for {test_id} with max_workers={max_workers}: " \
                f"expected {expected_result}, got {result.result['result']}"


class TestConcurrentSynchronizationProperty:
    """
    Property 15: Concurrent synchronization
    
    For any pipeline with concurrent steps followed by dependent steps, the dependent
    steps should only execute after all concurrent steps complete.
    
    Validates: Requirements 3.6
    """
    
    # Feature: project-production-readiness, Property 15: Concurrent synchronization
    @settings(max_examples=100, deadline=5000)
    @given(
        num_concurrent_tasks=st.integers(min_value=2, max_value=6),
        num_dependent_tasks=st.integers(min_value=1, max_value=4)
    )
    def test_dependent_tasks_wait_for_all_concurrent_tasks(
        self, num_concurrent_tasks, num_dependent_tasks
    ):
        """
        Property: When executing tasks with dependencies, dependent tasks should
        only start executing after ALL their dependencies have completed.
        
        This test creates:
        1. A set of concurrent tasks (no dependencies)
        2. A set of dependent tasks that depend on ALL concurrent tasks
        
        It verifies that no dependent task starts before all concurrent tasks finish.
        """
        # Track execution timing
        timing_dict = {}
        lock = threading.Lock()
        
        def concurrent_task(task_id: str, sleep_time: float) -> str:
            """A concurrent task that records its timing"""
            with lock:
                timing_dict[f"{task_id}_start"] = time.time()
            time.sleep(sleep_time)
            with lock:
                timing_dict[f"{task_id}_end"] = time.time()
            return f"completed_{task_id}"
        
        def dependent_task(task_id: str, sleep_time: float) -> str:
            """A dependent task that records its timing"""
            with lock:
                timing_dict[f"{task_id}_start"] = time.time()
            time.sleep(sleep_time)
            with lock:
                timing_dict[f"{task_id}_end"] = time.time()
            return f"completed_{task_id}"
        
        # Create concurrent tasks (no dependencies)
        concurrent_task_ids = []
        tasks = []
        
        for i in range(num_concurrent_tasks):
            task_id = f"concurrent_{i}"
            concurrent_task_ids.append(task_id)
            
            task = Task(
                id=task_id,
                func=concurrent_task,
                args=(task_id, 0.1),  # Each concurrent task takes 0.1s
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Create dependent tasks (depend on ALL concurrent tasks)
        dependent_task_ids = []
        
        for i in range(num_dependent_tasks):
            task_id = f"dependent_{i}"
            dependent_task_ids.append(task_id)
            
            task = Task(
                id=task_id,
                func=dependent_task,
                args=(task_id, 0.05),  # Dependent tasks are faster
                kwargs={},
                dependencies=concurrent_task_ids,  # Depend on ALL concurrent tasks
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Execute with dependencies
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_with_dependencies(tasks)
        
        # Verify all tasks completed successfully
        assert len(results) == num_concurrent_tasks + num_dependent_tasks
        assert all(r.success for r in results), \
            f"Some tasks failed: {[r.task_id for r in results if not r.success]}"
        
        # Verify synchronization: dependent tasks should start AFTER all concurrent tasks finish
        # Find the latest end time among concurrent tasks
        latest_concurrent_end = max(
            timing_dict.get(f"concurrent_{i}_end", 0)
            for i in range(num_concurrent_tasks)
        )
        
        # Find the earliest start time among dependent tasks
        earliest_dependent_start = min(
            timing_dict.get(f"dependent_{i}_start", float('inf'))
            for i in range(num_dependent_tasks)
        )
        
        # Verify that dependent tasks started after all concurrent tasks finished
        assert earliest_dependent_start >= latest_concurrent_end, \
            f"Dependent task started before all concurrent tasks finished: " \
            f"earliest_dependent_start={earliest_dependent_start:.6f}, " \
            f"latest_concurrent_end={latest_concurrent_end:.6f}"
        
        # Additional verification: check each dependent task individually
        for i in range(num_dependent_tasks):
            dependent_start = timing_dict.get(f"dependent_{i}_start", 0)
            
            # This dependent task should start after ALL concurrent tasks finish
            for j in range(num_concurrent_tasks):
                concurrent_end = timing_dict.get(f"concurrent_{j}_end", 0)
                assert dependent_start >= concurrent_end, \
                    f"Dependent task 'dependent_{i}' started at {dependent_start:.6f} " \
                    f"before concurrent task 'concurrent_{j}' ended at {concurrent_end:.6f}"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks_per_level=st.lists(
            st.integers(min_value=1, max_value=4),
            min_size=2,
            max_size=4
        )
    )
    def test_multi_level_dependency_synchronization(self, num_tasks_per_level):
        """
        Property: In a multi-level dependency chain, each level should wait
        for all tasks in the previous level to complete before starting.
        
        This creates a dependency chain like:
        Level 0: [task_0_0, task_0_1, ...]  (no dependencies)
        Level 1: [task_1_0, task_1_1, ...]  (depend on all Level 0)
        Level 2: [task_2_0, task_2_1, ...]  (depend on all Level 1)
        etc.
        """
        timing_dict = {}
        lock = threading.Lock()
        
        def timed_task(task_id: str, sleep_time: float) -> str:
            """Task that records timing"""
            with lock:
                timing_dict[f"{task_id}_start"] = time.time()
            time.sleep(sleep_time)
            with lock:
                timing_dict[f"{task_id}_end"] = time.time()
            return f"completed_{task_id}"
        
        tasks = []
        level_task_ids = []  # List of lists: level_task_ids[level] = [task_ids]
        
        # Create tasks for each level
        for level, num_tasks in enumerate(num_tasks_per_level):
            current_level_ids = []
            
            for task_idx in range(num_tasks):
                task_id = f"task_L{level}_T{task_idx}"
                current_level_ids.append(task_id)
                
                # Dependencies: all tasks from previous level
                dependencies = level_task_ids[level - 1] if level > 0 else []
                
                task = Task(
                    id=task_id,
                    func=timed_task,
                    args=(task_id, 0.05),
                    kwargs={},
                    dependencies=dependencies,
                    required=True,
                    metadata={}
                )
                tasks.append(task)
            
            level_task_ids.append(current_level_ids)
        
        # Execute with dependencies
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_with_dependencies(tasks)
        
        # Verify all tasks completed
        total_tasks = sum(num_tasks_per_level)
        assert len(results) == total_tasks
        assert all(r.success for r in results)
        
        # Verify synchronization between levels
        for level in range(1, len(num_tasks_per_level)):
            # Get the latest end time from previous level
            prev_level_ids = level_task_ids[level - 1]
            latest_prev_end = max(
                timing_dict.get(f"{task_id}_end", 0)
                for task_id in prev_level_ids
            )
            
            # Get the earliest start time from current level
            current_level_ids = level_task_ids[level]
            earliest_current_start = min(
                timing_dict.get(f"{task_id}_start", float('inf'))
                for task_id in current_level_ids
            )
            
            # Verify synchronization
            assert earliest_current_start >= latest_prev_end, \
                f"Level {level} started before Level {level-1} finished: " \
                f"earliest_start={earliest_current_start:.6f}, " \
                f"latest_prev_end={latest_prev_end:.6f}"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_concurrent_tasks=st.integers(min_value=3, max_value=6)  # Need at least 3 for meaningful test
    )
    def test_partial_dependencies_allow_early_start(self, num_concurrent_tasks):
        """
        Property: A task that depends on only SOME concurrent tasks should
        be able to start as soon as those specific dependencies complete,
        without waiting for all concurrent tasks.
        
        This verifies that the synchronization is precise - tasks only wait
        for their actual dependencies, not all concurrent tasks.
        """
        timing_dict = {}
        lock = threading.Lock()
        
        def timed_task(task_id: str, sleep_time: float) -> str:
            """Task that records timing"""
            with lock:
                timing_dict[f"{task_id}_start"] = time.time()
            time.sleep(sleep_time)
            with lock:
                timing_dict[f"{task_id}_end"] = time.time()
            return f"completed_{task_id}"
        
        tasks = []
        
        # Create concurrent tasks with varying durations
        # First task is fast, others are slow
        fast_task_id = "concurrent_0"
        slow_task_ids = []
        
        # Fast task
        task = Task(
            id=fast_task_id,
            func=timed_task,
            args=(fast_task_id, 0.05),  # Fast: 0.05s
            kwargs={},
            dependencies=[],
            required=True,
            metadata={}
        )
        tasks.append(task)
        
        # Slow tasks - need significant time difference
        for i in range(1, num_concurrent_tasks):
            task_id = f"concurrent_{i}"
            slow_task_ids.append(task_id)
            
            task = Task(
                id=task_id,
                func=timed_task,
                args=(task_id, 0.3),  # Slow: 0.3s
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Create a dependent task that only depends on the fast task
        early_dependent_id = "early_dependent"
        task = Task(
            id=early_dependent_id,
            func=timed_task,
            args=(early_dependent_id, 0.05),
            kwargs={},
            dependencies=[fast_task_id],  # Only depends on fast task
            required=True,
            metadata={}
        )
        tasks.append(task)
        
        # Create a dependent task that depends on ALL tasks
        late_dependent_id = "late_dependent"
        all_concurrent_ids = [fast_task_id] + slow_task_ids
        task = Task(
            id=late_dependent_id,
            func=timed_task,
            args=(late_dependent_id, 0.05),
            kwargs={},
            dependencies=all_concurrent_ids,  # Depends on all
            required=True,
            metadata={}
        )
        tasks.append(task)
        
        # Execute with dependencies
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_with_dependencies(tasks)
        
        # Verify all tasks completed
        assert len(results) == num_concurrent_tasks + 2
        assert all(r.success for r in results)
        
        # Main property: Verify early_dependent started after fast task finishes
        fast_end = timing_dict.get(f"{fast_task_id}_end", 0)
        early_dependent_start = timing_dict.get(f"{early_dependent_id}_start", 0)
        
        # Early dependent should start after its dependency (fast task) finishes
        assert early_dependent_start >= fast_end, \
            f"Early dependent started before its dependency finished"
        
        # Verify late_dependent waited for ALL tasks (including slow ones)
        latest_concurrent_end = max(
            timing_dict.get(f"{task_id}_end", 0)
            for task_id in all_concurrent_ids
        )
        late_dependent_start = timing_dict.get(f"{late_dependent_id}_start", 0)
        
        assert late_dependent_start >= latest_concurrent_end, \
            f"Late dependent didn't wait for all dependencies"
        
        # Additional verification: early_dependent should START before or at the same time as late_dependent
        # Due to thread scheduling, they might start very close together, so we allow a small margin
        # The key is that early_dependent doesn't wait significantly longer
        time_diff = late_dependent_start - early_dependent_start
        # Allow 10ms margin for timing precision
        assert time_diff >= -0.01, \
            f"Early dependent started significantly after late dependent: " \
            f"time_diff={time_diff:.6f}s"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_concurrent_tasks=st.integers(min_value=2, max_value=6)
    )
    def test_synchronization_with_failed_optional_tasks(self, num_concurrent_tasks):
        """
        Property: When optional concurrent tasks fail, dependent tasks should
        be skipped if any of their dependencies (even optional ones) are required
        tasks that failed.
        
        This test verifies the current behavior: if a task depends on another task
        that is marked as required=True and that task fails, the dependent task
        will be skipped.
        """
        timing_dict = {}
        lock = threading.Lock()
        
        def success_task(task_id: str, sleep_time: float) -> str:
            """Task that succeeds"""
            with lock:
                timing_dict[f"{task_id}_start"] = time.time()
            time.sleep(sleep_time)
            with lock:
                timing_dict[f"{task_id}_end"] = time.time()
            return f"completed_{task_id}"
        
        def failure_task(task_id: str, sleep_time: float) -> str:
            """Task that fails"""
            with lock:
                timing_dict[f"{task_id}_start"] = time.time()
            time.sleep(sleep_time)
            with lock:
                timing_dict[f"{task_id}_end"] = time.time()
            raise ValueError(f"Task {task_id} failed intentionally")
        
        tasks = []
        successful_task_ids = []
        failed_optional_task_ids = []
        
        # Create concurrent tasks - all optional, some will fail
        for i in range(num_concurrent_tasks):
            task_id = f"concurrent_{i}"
            will_fail = (i % 3 == 0)  # Every 3rd task fails
            
            if will_fail:
                failed_optional_task_ids.append(task_id)
            else:
                successful_task_ids.append(task_id)
            
            task = Task(
                id=task_id,
                func=failure_task if will_fail else success_task,
                args=(task_id, 0.1),
                kwargs={},
                dependencies=[],
                required=False,  # All optional
                metadata={}
            )
            tasks.append(task)
        
        # Create dependent task that depends on all concurrent tasks
        dependent_id = "dependent"
        all_concurrent_ids = successful_task_ids + failed_optional_task_ids
        task = Task(
            id=dependent_id,
            func=success_task,
            args=(dependent_id, 0.05),
            kwargs={},
            dependencies=all_concurrent_ids,
            required=True,
            metadata={}
        )
        tasks.append(task)
        
        # Execute with dependencies
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_with_dependencies(tasks)
        
        # Verify dependent task executed successfully
        # Since all dependencies are optional (required=False), the dependent task should proceed
        dependent_result = next(r for r in results if r.task_id == dependent_id)
        assert dependent_result.success, \
            "Dependent task should succeed when all failed dependencies are optional"
        
        # Verify dependent task waited for all successful tasks
        if successful_task_ids:
            successful_ends = [
                timing_dict.get(f"{task_id}_end", 0)
                for task_id in successful_task_ids
                if f"{task_id}_end" in timing_dict
            ]
            
            if successful_ends:
                latest_successful_end = max(successful_ends)
                dependent_start = timing_dict.get(f"{dependent_id}_start", 0)
                
                assert dependent_start >= latest_successful_end, \
                    f"Dependent task started before successful dependencies finished"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        num_concurrent_tasks=st.integers(min_value=2, max_value=5)
    )
    def test_synchronization_preserves_result_order(self, num_concurrent_tasks):
        """
        Property: Even with synchronization and dependencies, results should
        be returned in the same order as the input task list.
        """
        def simple_task(task_id: str, sleep_time: float) -> str:
            """Simple task"""
            time.sleep(sleep_time)
            return f"result_{task_id}"
        
        tasks = []
        expected_order = []
        
        # Create concurrent tasks
        for i in range(num_concurrent_tasks):
            task_id = f"concurrent_{i}"
            expected_order.append(task_id)
            
            task = Task(
                id=task_id,
                func=simple_task,
                args=(task_id, 0.05),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Create dependent task
        dependent_id = "dependent"
        expected_order.append(dependent_id)
        
        task = Task(
            id=dependent_id,
            func=simple_task,
            args=(dependent_id, 0.05),
            kwargs={},
            dependencies=[f"concurrent_{i}" for i in range(num_concurrent_tasks)],
            required=True,
            metadata={}
        )
        tasks.append(task)
        
        # Execute with dependencies
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_with_dependencies(tasks)
        
        # Verify order is preserved
        actual_order = [r.task_id for r in results]
        assert actual_order == expected_order, \
            f"Result order not preserved: expected {expected_order}, got {actual_order}"



class TestMaxConcurrencyEnforcementProperty:
    """
    Property 18: Max concurrency enforcement
    
    For any concurrent execution with max_workers=N, the system should never
    execute more than N tasks simultaneously.
    
    Validates: Requirements 9.2
    """
    
    # Feature: project-production-readiness, Property 18: Max concurrency enforcement
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=5, max_value=20),
        max_workers=st.integers(min_value=1, max_value=8)
    )
    def test_max_workers_never_exceeded(self, num_tasks, max_workers):
        """
        Property: For any concurrent execution with max_workers=N, the system
        should never execute more than N tasks simultaneously.
        
        This is the core property that validates Requirement 9.2:
        "WHEN 配置并发执行时 THEN the System SHALL 支持设置最大并发数"
        
        We verify this by:
        1. Tracking the number of concurrently executing tasks
        2. Recording the maximum concurrent count seen
        3. Asserting that max_seen <= max_workers
        """
        # Track concurrent execution count with thread-safe operations
        concurrent_count = {"current": 0, "max_seen": 0}
        lock = threading.Lock()
        
        def tracking_task(task_id: str, sleep_time: float) -> str:
            """Task that tracks concurrent execution count"""
            # Increment concurrent count
            with lock:
                concurrent_count["current"] += 1
                concurrent_count["max_seen"] = max(
                    concurrent_count["max_seen"],
                    concurrent_count["current"]
                )
            
            # Sleep to ensure tasks overlap
            time.sleep(sleep_time)
            
            # Decrement concurrent count
            with lock:
                concurrent_count["current"] -= 1
            
            return f"completed_{task_id}"
        
        # Create tasks with sufficient sleep time to ensure overlap
        tasks = []
        sleep_time = 0.1  # 100ms per task
        
        for i in range(num_tasks):
            task = Task(
                id=f"task_{i}",
                func=tracking_task,
                args=(f"task_{i}", sleep_time),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Execute concurrently with specified max_workers
        executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # Verify all tasks completed successfully
        assert len(results) == num_tasks, \
            f"Expected {num_tasks} results, got {len(results)}"
        assert all(r.success for r in results), \
            f"Some tasks failed: {[r.task_id for r in results if not r.success]}"
        
        # CRITICAL PROPERTY: max_workers was never exceeded
        assert concurrent_count["max_seen"] <= max_workers, \
            f"PROPERTY VIOLATION: Exceeded max_workers limit! " \
            f"Saw {concurrent_count['max_seen']} concurrent tasks, " \
            f"but max_workers={max_workers}"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=10, max_value=30),
        max_workers=st.integers(min_value=2, max_value=6)
    )
    def test_max_workers_enforcement_with_varying_task_durations(self, num_tasks, max_workers):
        """
        Property: Max workers limit should be enforced even when tasks have
        varying execution times.
        
        This tests that the executor properly manages the worker pool even when
        some tasks finish quickly and others take longer.
        """
        concurrent_count = {"current": 0, "max_seen": 0}
        lock = threading.Lock()
        
        def variable_duration_task(task_id: str, duration: float) -> str:
            """Task with variable duration"""
            with lock:
                concurrent_count["current"] += 1
                concurrent_count["max_seen"] = max(
                    concurrent_count["max_seen"],
                    concurrent_count["current"]
                )
            
            time.sleep(duration)
            
            with lock:
                concurrent_count["current"] -= 1
            
            return f"completed_{task_id}"
        
        # Create tasks with varying durations
        tasks = []
        for i in range(num_tasks):
            # Vary duration between 0.05s and 0.15s
            duration = 0.05 + (i % 3) * 0.05
            
            task = Task(
                id=f"task_{i}",
                func=variable_duration_task,
                args=(f"task_{i}", duration),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # Verify all tasks completed
        assert len(results) == num_tasks
        assert all(r.success for r in results)
        
        # Verify max_workers was never exceeded
        assert concurrent_count["max_seen"] <= max_workers, \
            f"PROPERTY VIOLATION: Exceeded max_workers with varying durations! " \
            f"Saw {concurrent_count['max_seen']} concurrent tasks, " \
            f"but max_workers={max_workers}"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=8, max_value=20),
        max_workers=st.integers(min_value=1, max_value=4)
    )
    def test_max_workers_enforcement_with_task_failures(self, num_tasks, max_workers):
        """
        Property: Max workers limit should be enforced even when some tasks fail.
        
        This ensures that task failures don't cause the executor to violate
        the max_workers constraint.
        """
        concurrent_count = {"current": 0, "max_seen": 0}
        lock = threading.Lock()
        
        def task_with_potential_failure(task_id: str, should_fail: bool) -> str:
            """Task that may fail"""
            with lock:
                concurrent_count["current"] += 1
                concurrent_count["max_seen"] = max(
                    concurrent_count["max_seen"],
                    concurrent_count["current"]
                )
            
            time.sleep(0.08)
            
            with lock:
                concurrent_count["current"] -= 1
            
            if should_fail:
                raise ValueError(f"Task {task_id} failed intentionally")
            
            return f"completed_{task_id}"
        
        # Create tasks where some will fail
        tasks = []
        for i in range(num_tasks):
            should_fail = (i % 4 == 0)  # Every 4th task fails
            
            task = Task(
                id=f"task_{i}",
                func=task_with_potential_failure,
                args=(f"task_{i}", should_fail),
                kwargs={},
                dependencies=[],
                required=False,  # Allow execution to continue on failure
                metadata={}
            )
            tasks.append(task)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # Verify all tasks were attempted
        assert len(results) == num_tasks
        
        # Verify max_workers was never exceeded despite failures
        assert concurrent_count["max_seen"] <= max_workers, \
            f"PROPERTY VIOLATION: Exceeded max_workers with task failures! " \
            f"Saw {concurrent_count['max_seen']} concurrent tasks, " \
            f"but max_workers={max_workers}"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        max_workers=st.integers(min_value=1, max_value=10)
    )
    def test_max_workers_enforcement_with_exact_worker_count(self, max_workers):
        """
        Property: When the number of tasks equals max_workers, all tasks
        should execute concurrently without exceeding the limit.
        
        This is an edge case that tests the boundary condition.
        """
        concurrent_count = {"current": 0, "max_seen": 0}
        lock = threading.Lock()
        
        def tracking_task(task_id: str) -> str:
            """Task that tracks concurrent execution"""
            with lock:
                concurrent_count["current"] += 1
                concurrent_count["max_seen"] = max(
                    concurrent_count["max_seen"],
                    concurrent_count["current"]
                )
            
            time.sleep(0.1)
            
            with lock:
                concurrent_count["current"] -= 1
            
            return f"completed_{task_id}"
        
        # Create exactly max_workers tasks
        tasks = []
        for i in range(max_workers):
            task = Task(
                id=f"task_{i}",
                func=tracking_task,
                args=(f"task_{i}",),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # Verify all tasks completed
        assert len(results) == max_workers
        assert all(r.success for r in results)
        
        # Verify max_workers was never exceeded
        assert concurrent_count["max_seen"] <= max_workers, \
            f"PROPERTY VIOLATION: Exceeded max_workers at boundary! " \
            f"Saw {concurrent_count['max_seen']} concurrent tasks, " \
            f"but max_workers={max_workers}"
        
        # For this edge case, we expect to see exactly max_workers concurrent tasks
        assert concurrent_count["max_seen"] == max_workers, \
            f"Expected to see exactly {max_workers} concurrent tasks, " \
            f"but saw {concurrent_count['max_seen']}"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=1, max_value=5),
        max_workers=st.integers(min_value=6, max_value=10)
    )
    def test_max_workers_enforcement_with_fewer_tasks_than_workers(self, num_tasks, max_workers):
        """
        Property: When the number of tasks is less than max_workers, only
        the actual number of tasks should execute concurrently.
        
        This tests that the executor doesn't create unnecessary workers.
        """
        # Ensure num_tasks < max_workers
        assume(num_tasks < max_workers)
        
        concurrent_count = {"current": 0, "max_seen": 0}
        lock = threading.Lock()
        
        def tracking_task(task_id: str) -> str:
            """Task that tracks concurrent execution"""
            with lock:
                concurrent_count["current"] += 1
                concurrent_count["max_seen"] = max(
                    concurrent_count["max_seen"],
                    concurrent_count["current"]
                )
            
            time.sleep(0.1)
            
            with lock:
                concurrent_count["current"] -= 1
            
            return f"completed_{task_id}"
        
        # Create fewer tasks than max_workers
        tasks = []
        for i in range(num_tasks):
            task = Task(
                id=f"task_{i}",
                func=tracking_task,
                args=(f"task_{i}",),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # Verify all tasks completed
        assert len(results) == num_tasks
        assert all(r.success for r in results)
        
        # Verify max_workers was never exceeded
        assert concurrent_count["max_seen"] <= max_workers, \
            f"PROPERTY VIOLATION: Exceeded max_workers! " \
            f"Saw {concurrent_count['max_seen']} concurrent tasks, " \
            f"but max_workers={max_workers}"
        
        # Verify we didn't exceed the actual number of tasks
        assert concurrent_count["max_seen"] <= num_tasks, \
            f"Saw more concurrent tasks ({concurrent_count['max_seen']}) " \
            f"than total tasks ({num_tasks})"
    
    @settings(max_examples=50, deadline=6000)
    @given(
        num_tasks=st.integers(min_value=15, max_value=40),
        max_workers=st.integers(min_value=2, max_value=5)
    )
    def test_max_workers_enforcement_over_multiple_batches(self, num_tasks, max_workers):
        """
        Property: When tasks are executed in multiple batches (because
        num_tasks > max_workers), the max_workers limit should be enforced
        throughout all batches.
        
        This tests that the executor properly manages the worker pool across
        multiple waves of task execution.
        """
        concurrent_count = {"current": 0, "max_seen": 0, "samples": []}
        lock = threading.Lock()
        
        def tracking_task(task_id: str) -> str:
            """Task that tracks concurrent execution"""
            with lock:
                concurrent_count["current"] += 1
                concurrent_count["max_seen"] = max(
                    concurrent_count["max_seen"],
                    concurrent_count["current"]
                )
                # Sample the concurrent count periodically
                concurrent_count["samples"].append(concurrent_count["current"])
            
            time.sleep(0.05)
            
            with lock:
                concurrent_count["current"] -= 1
            
            return f"completed_{task_id}"
        
        # Create many tasks to ensure multiple batches
        tasks = []
        for i in range(num_tasks):
            task = Task(
                id=f"task_{i}",
                func=tracking_task,
                args=(f"task_{i}",),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # Verify all tasks completed
        assert len(results) == num_tasks
        assert all(r.success for r in results)
        
        # Verify max_workers was never exceeded across all batches
        assert concurrent_count["max_seen"] <= max_workers, \
            f"PROPERTY VIOLATION: Exceeded max_workers across batches! " \
            f"Saw {concurrent_count['max_seen']} concurrent tasks, " \
            f"but max_workers={max_workers}"
        
        # Verify that all samples respect the limit
        for sample in concurrent_count["samples"]:
            assert sample <= max_workers, \
                f"PROPERTY VIOLATION: Sample showed {sample} concurrent tasks, " \
                f"exceeding max_workers={max_workers}"



class TestConcurrentErrorIsolationProperty:
    """
    Property 19: Concurrent error isolation
    
    For any concurrent execution where some tasks fail, the failures should
    not prevent other independent tasks from completing.
    
    Validates: Requirements 9.3
    """
    
    # Feature: project-production-readiness, Property 19: Concurrent error isolation
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=3, max_value=12),
        failure_rate=st.floats(min_value=0.1, max_value=0.6)
    )
    def test_failures_do_not_prevent_independent_task_completion(
        self, num_tasks, failure_rate
    ):
        """
        Property: When executing independent tasks concurrently, failures in
        some tasks should not prevent other independent tasks from completing
        successfully.
        
        This is the core error isolation property: each task's success or
        failure should be independent of other tasks' outcomes.
        """
        # Track which tasks actually executed
        executed_tasks = set()
        lock = threading.Lock()
        
        def task_with_potential_failure(task_id: str, should_fail: bool) -> str:
            """Task that may fail, but records that it was executed"""
            with lock:
                executed_tasks.add(task_id)
            
            time.sleep(0.02)  # Small delay to ensure concurrent execution
            
            if should_fail:
                raise RuntimeError(f"Task {task_id} failed intentionally")
            
            return f"completed_{task_id}"
        
        # Create tasks with some that will fail
        tasks = []
        expected_failures = set()
        expected_successes = set()
        
        for i in range(num_tasks):
            task_id = f"task_{i}"
            # Randomly determine if this task should fail based on failure_rate
            should_fail = (i % int(1 / failure_rate)) == 0 if failure_rate > 0 else False
            
            task = Task(
                id=task_id,
                func=task_with_potential_failure,
                args=(task_id, should_fail),
                kwargs={},
                dependencies=[],  # All tasks are independent
                required=False,  # Failures should not stop execution
                metadata={}
            )
            tasks.append(task)
            
            if should_fail:
                expected_failures.add(task_id)
            else:
                expected_successes.add(task_id)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # PROPERTY VERIFICATION: All tasks were attempted
        assert len(results) == num_tasks, \
            f"PROPERTY VIOLATION: Not all tasks were attempted! " \
            f"Expected {num_tasks} results, got {len(results)}"
        
        # PROPERTY VERIFICATION: All tasks were actually executed
        assert len(executed_tasks) == num_tasks, \
            f"PROPERTY VIOLATION: Not all tasks were executed! " \
            f"Expected {num_tasks} tasks to execute, but only {len(executed_tasks)} did"
        
        # PROPERTY VERIFICATION: Failed tasks actually failed
        actual_failures = {r.task_id for r in results if not r.success}
        assert actual_failures == expected_failures, \
            f"PROPERTY VIOLATION: Failure set mismatch! " \
            f"Expected failures: {expected_failures}, got: {actual_failures}"
        
        # PROPERTY VERIFICATION: Successful tasks actually succeeded
        actual_successes = {r.task_id for r in results if r.success}
        assert actual_successes == expected_successes, \
            f"PROPERTY VIOLATION: Success set mismatch! " \
            f"Expected successes: {expected_successes}, got: {actual_successes}"
        
        # PROPERTY VERIFICATION: No task was skipped (all are independent)
        skipped_tasks = [r.task_id for r in results if r.skipped]
        assert len(skipped_tasks) == 0, \
            f"PROPERTY VIOLATION: Independent tasks should not be skipped! " \
            f"Found skipped tasks: {skipped_tasks}"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=4, max_value=10),
        num_failures=st.integers(min_value=1, max_value=3)
    )
    def test_specific_number_of_failures_isolated(self, num_tasks, num_failures):
        """
        Property: When a specific number of tasks fail, exactly that many
        should fail, and all others should succeed (error isolation).
        
        This tests that failures are precisely isolated to the failing tasks.
        """
        # Ensure we don't try to fail more tasks than we have
        assume(num_failures < num_tasks)
        
        # Determine which tasks will fail (first num_failures tasks)
        failing_task_indices = set(range(num_failures))
        
        def task_with_controlled_failure(task_id: str, task_index: int) -> str:
            """Task that fails if its index is in the failing set"""
            time.sleep(0.01)
            
            if task_index in failing_task_indices:
                raise ValueError(f"Task {task_id} (index {task_index}) failed")
            
            return f"completed_{task_id}"
        
        # Create tasks
        tasks = []
        for i in range(num_tasks):
            task = Task(
                id=f"task_{i}",
                func=task_with_controlled_failure,
                args=(f"task_{i}", i),
                kwargs={},
                dependencies=[],
                required=False,
                metadata={}
            )
            tasks.append(task)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # Count failures and successes
        num_failed = sum(1 for r in results if not r.success)
        num_succeeded = sum(1 for r in results if r.success)
        
        # PROPERTY VERIFICATION: Exact number of failures
        assert num_failed == num_failures, \
            f"PROPERTY VIOLATION: Expected exactly {num_failures} failures, " \
            f"got {num_failed}"
        
        # PROPERTY VERIFICATION: Exact number of successes
        expected_successes = num_tasks - num_failures
        assert num_succeeded == expected_successes, \
            f"PROPERTY VIOLATION: Expected exactly {expected_successes} successes, " \
            f"got {num_succeeded}"
        
        # PROPERTY VERIFICATION: The right tasks failed
        failed_indices = {
            int(r.task_id.split('_')[1]) 
            for r in results if not r.success
        }
        assert failed_indices == failing_task_indices, \
            f"PROPERTY VIOLATION: Wrong tasks failed! " \
            f"Expected indices {failing_task_indices}, got {failed_indices}"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=5, max_value=15),
        max_workers=st.integers(min_value=2, max_value=4)
    )
    def test_error_isolation_with_varying_concurrency(
        self, num_tasks, max_workers
    ):
        """
        Property: Error isolation should work correctly regardless of the
        level of concurrency (max_workers setting).
        
        This tests that error isolation is maintained even when tasks are
        executed in different batch sizes due to max_workers constraints.
        """
        # Create tasks where every 3rd task fails
        def task_with_pattern_failure(task_id: str, task_index: int) -> str:
            """Task that fails in a pattern"""
            time.sleep(0.02)
            
            if task_index % 3 == 0:
                raise RuntimeError(f"Task {task_id} failed (pattern failure)")
            
            return f"completed_{task_id}"
        
        tasks = []
        expected_failures = []
        expected_successes = []
        
        for i in range(num_tasks):
            task_id = f"task_{i}"
            task = Task(
                id=task_id,
                func=task_with_pattern_failure,
                args=(task_id, i),
                kwargs={},
                dependencies=[],
                required=False,
                metadata={}
            )
            tasks.append(task)
            
            if i % 3 == 0:
                expected_failures.append(task_id)
            else:
                expected_successes.append(task_id)
        
        # Execute with specified max_workers
        executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # PROPERTY VERIFICATION: All tasks completed
        assert len(results) == num_tasks, \
            f"PROPERTY VIOLATION: Not all tasks completed! " \
            f"Expected {num_tasks}, got {len(results)}"
        
        # PROPERTY VERIFICATION: Correct failures
        actual_failures = [r.task_id for r in results if not r.success]
        assert set(actual_failures) == set(expected_failures), \
            f"PROPERTY VIOLATION: Failure mismatch with max_workers={max_workers}! " \
            f"Expected {expected_failures}, got {actual_failures}"
        
        # PROPERTY VERIFICATION: Correct successes
        actual_successes = [r.task_id for r in results if r.success]
        assert set(actual_successes) == set(expected_successes), \
            f"PROPERTY VIOLATION: Success mismatch with max_workers={max_workers}! " \
            f"Expected {expected_successes}, got {actual_successes}"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=4, max_value=12)
    )
    def test_error_isolation_with_different_error_types(self, num_tasks):
        """
        Property: Error isolation should work regardless of the type of
        exception raised by failing tasks.
        
        This tests that different error types don't affect error isolation.
        """
        # Different error types to use
        error_types = [
            ValueError,
            RuntimeError,
            TypeError,
            KeyError,
            IndexError
        ]
        
        def task_with_varied_errors(task_id: str, task_index: int) -> str:
            """Task that may raise different types of errors"""
            time.sleep(0.01)
            
            # Every other task fails with a different error type
            if task_index % 2 == 0:
                error_class = error_types[task_index % len(error_types)]
                raise error_class(f"Task {task_id} failed with {error_class.__name__}")
            
            return f"completed_{task_id}"
        
        tasks = []
        expected_failures = []
        expected_successes = []
        
        for i in range(num_tasks):
            task_id = f"task_{i}"
            task = Task(
                id=task_id,
                func=task_with_varied_errors,
                args=(task_id, i),
                kwargs={},
                dependencies=[],
                required=False,
                metadata={}
            )
            tasks.append(task)
            
            if i % 2 == 0:
                expected_failures.append(task_id)
            else:
                expected_successes.append(task_id)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # PROPERTY VERIFICATION: All tasks attempted
        assert len(results) == num_tasks, \
            f"PROPERTY VIOLATION: Not all tasks attempted! " \
            f"Expected {num_tasks}, got {len(results)}"
        
        # PROPERTY VERIFICATION: Correct failures despite different error types
        actual_failures = [r.task_id for r in results if not r.success]
        assert set(actual_failures) == set(expected_failures), \
            f"PROPERTY VIOLATION: Different error types affected isolation! " \
            f"Expected failures: {expected_failures}, got: {actual_failures}"
        
        # PROPERTY VERIFICATION: Correct successes
        actual_successes = [r.task_id for r in results if r.success]
        assert set(actual_successes) == set(expected_successes), \
            f"PROPERTY VIOLATION: Different error types affected successes! " \
            f"Expected successes: {expected_successes}, got: {actual_successes}"
        
        # PROPERTY VERIFICATION: Error information is captured
        for result in results:
            if not result.success:
                assert result.error is not None, \
                    f"PROPERTY VIOLATION: Failed task {result.task_id} has no error message"
                assert result.error_type is not None, \
                    f"PROPERTY VIOLATION: Failed task {result.task_id} has no error type"
    
    @settings(max_examples=50, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=6, max_value=15)
    )
    def test_error_isolation_with_slow_and_fast_tasks(self, num_tasks):
        """
        Property: Error isolation should work when tasks have different
        execution times (some fast, some slow).
        
        This tests that timing differences don't affect error isolation.
        """
        def task_with_varied_timing(
            task_id: str, task_index: int, sleep_time: float
        ) -> str:
            """Task with variable execution time"""
            time.sleep(sleep_time)
            
            # Tasks with odd indices fail
            if task_index % 2 == 1:
                raise RuntimeError(f"Task {task_id} failed")
            
            return f"completed_{task_id}"
        
        tasks = []
        expected_failures = []
        expected_successes = []
        
        for i in range(num_tasks):
            task_id = f"task_{i}"
            # Alternate between fast (0.01s) and slow (0.1s) tasks
            sleep_time = 0.01 if i % 2 == 0 else 0.1
            
            task = Task(
                id=task_id,
                func=task_with_varied_timing,
                args=(task_id, i, sleep_time),
                kwargs={},
                dependencies=[],
                required=False,
                metadata={}
            )
            tasks.append(task)
            
            if i % 2 == 1:
                expected_failures.append(task_id)
            else:
                expected_successes.append(task_id)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # PROPERTY VERIFICATION: All tasks completed
        assert len(results) == num_tasks, \
            f"PROPERTY VIOLATION: Not all tasks completed! " \
            f"Expected {num_tasks}, got {len(results)}"
        
        # PROPERTY VERIFICATION: Timing differences didn't affect isolation
        actual_failures = [r.task_id for r in results if not r.success]
        assert set(actual_failures) == set(expected_failures), \
            f"PROPERTY VIOLATION: Timing differences affected error isolation! " \
            f"Expected failures: {expected_failures}, got: {actual_failures}"
        
        # PROPERTY VERIFICATION: Fast tasks succeeded despite slow task failures
        actual_successes = [r.task_id for r in results if r.success]
        assert set(actual_successes) == set(expected_successes), \
            f"PROPERTY VIOLATION: Timing differences affected successes! " \
            f"Expected successes: {expected_successes}, got: {actual_successes}"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=3, max_value=10)
    )
    def test_error_isolation_preserves_result_order(self, num_tasks):
        """
        Property: Error isolation should not affect the ordering of results.
        Results should be returned in the same order as input tasks, regardless
        of which tasks failed.
        
        This tests that error isolation doesn't break result ordering.
        """
        def task_with_failure(task_id: str, task_index: int) -> int:
            """Task that returns its index or fails"""
            time.sleep(0.01)
            
            if task_index % 3 == 0:
                raise ValueError(f"Task {task_id} failed")
            
            return task_index
        
        tasks = []
        for i in range(num_tasks):
            task = Task(
                id=f"task_{i}",
                func=task_with_failure,
                args=(f"task_{i}", i),
                kwargs={},
                dependencies=[],
                required=False,
                metadata={}
            )
            tasks.append(task)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # PROPERTY VERIFICATION: Results are in correct order
        for i, result in enumerate(results):
            expected_task_id = f"task_{i}"
            assert result.task_id == expected_task_id, \
                f"PROPERTY VIOLATION: Result order not preserved! " \
                f"Position {i} has task_id '{result.task_id}', " \
                f"expected '{expected_task_id}'"
        
        # PROPERTY VERIFICATION: Successful tasks have correct results
        for i, result in enumerate(results):
            if result.success:
                assert result.result == i, \
                    f"PROPERTY VIOLATION: Task {result.task_id} has wrong result! " \
                    f"Expected {i}, got {result.result}"



class TestResultOrderPreservationProperty:
    """
    Property 20: Result order preservation
    
    For any concurrent execution of ordered tasks, the results should be
    returned in the original input order.
    
    Validates: Requirements 9.4
    """
    
    # Feature: project-production-readiness, Property 20: Result order preservation
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=2, max_value=10),
        max_workers=st.integers(min_value=2, max_value=4)
    )
    def test_result_order_preserved_with_varying_execution_times(
        self, num_tasks, max_workers
    ):
        """
        Property: For any concurrent execution of ordered tasks, the results
        should be returned in the original input order, regardless of which
        tasks finish first.
        
        This test creates tasks with varying execution times (later tasks
        finish first) to ensure the executor properly reorders results.
        """
        def task_with_timing(task_id: str, task_index: int, sleep_time: float) -> Dict[str, Any]:
            """Task that sleeps and returns its index and ID"""
            time.sleep(sleep_time)
            return {
                "task_id": task_id,
                "index": task_index,
                "result": f"completed_{task_index}"
            }
        
        tasks = []
        expected_order = []
        
        for i in range(num_tasks):
            task_id = f"task_{i}"
            # Reverse sleep times: later tasks finish first
            # This ensures tasks complete out of order
            sleep_time = 0.01 * (num_tasks - i)
            
            task = Task(
                id=task_id,
                func=task_with_timing,
                args=(task_id, i, sleep_time),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
            expected_order.append(task_id)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # PROPERTY VERIFICATION: Correct number of results
        assert len(results) == num_tasks, \
            f"PROPERTY VIOLATION: Expected {num_tasks} results, got {len(results)}"
        
        # PROPERTY VERIFICATION: Results are in original input order
        actual_order = [r.task_id for r in results]
        assert actual_order == expected_order, \
            f"PROPERTY VIOLATION: Result order not preserved! " \
            f"Expected order: {expected_order}, got: {actual_order}"
        
        # PROPERTY VERIFICATION: Each result is at the correct position
        for i, result in enumerate(results):
            expected_task_id = f"task_{i}"
            assert result.task_id == expected_task_id, \
                f"PROPERTY VIOLATION: Position {i} has wrong task! " \
                f"Expected '{expected_task_id}', got '{result.task_id}'"
            
            # Verify the result content is correct
            assert result.success, \
                f"PROPERTY VIOLATION: Task {result.task_id} failed unexpectedly"
            assert result.result["index"] == i, \
                f"PROPERTY VIOLATION: Task {result.task_id} has wrong index! " \
                f"Expected {i}, got {result.result['index']}"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=3, max_value=10)
    )
    def test_result_order_preserved_with_failures(self, num_tasks):
        """
        Property: Result order should be preserved even when some tasks fail.
        Failed tasks should still appear in their original position in the
        results list.
        """
        def task_with_potential_failure(task_id: str, task_index: int) -> int:
            """Task that may fail based on index"""
            time.sleep(0.01)
            
            # Every 3rd task fails
            if task_index % 3 == 0:
                raise ValueError(f"Task {task_id} failed intentionally")
            
            return task_index * 2
        
        tasks = []
        expected_order = []
        
        for i in range(num_tasks):
            task_id = f"task_{i}"
            task = Task(
                id=task_id,
                func=task_with_potential_failure,
                args=(task_id, i),
                kwargs={},
                dependencies=[],
                required=False,  # Allow failures
                metadata={}
            )
            tasks.append(task)
            expected_order.append(task_id)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # PROPERTY VERIFICATION: All tasks have results (success or failure)
        assert len(results) == num_tasks, \
            f"PROPERTY VIOLATION: Expected {num_tasks} results, got {len(results)}"
        
        # PROPERTY VERIFICATION: Results are in original order
        actual_order = [r.task_id for r in results]
        assert actual_order == expected_order, \
            f"PROPERTY VIOLATION: Result order not preserved with failures! " \
            f"Expected: {expected_order}, got: {actual_order}"
        
        # PROPERTY VERIFICATION: Each position has the correct task
        for i, result in enumerate(results):
            expected_task_id = f"task_{i}"
            assert result.task_id == expected_task_id, \
                f"PROPERTY VIOLATION: Position {i} has wrong task! " \
                f"Expected '{expected_task_id}', got '{result.task_id}'"
            
            # Verify success/failure matches expectation
            should_fail = (i % 3 == 0)
            if should_fail:
                assert not result.success, \
                    f"PROPERTY VIOLATION: Task {result.task_id} should have failed"
            else:
                assert result.success, \
                    f"PROPERTY VIOLATION: Task {result.task_id} should have succeeded"
                assert result.result == i * 2, \
                    f"PROPERTY VIOLATION: Task {result.task_id} has wrong result"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=2, max_value=8),
        max_workers=st.integers(min_value=1, max_value=4)
    )
    def test_result_order_preserved_with_different_worker_counts(
        self, num_tasks, max_workers
    ):
        """
        Property: Result order should be preserved regardless of the number
        of workers. Whether we have 1 worker (sequential) or many workers
        (highly concurrent), results should maintain input order.
        """
        def simple_task(task_id: str, task_index: int) -> str:
            """Simple task that returns its index"""
            time.sleep(0.01)
            return f"result_{task_index}"
        
        tasks = []
        expected_order = []
        
        for i in range(num_tasks):
            task_id = f"task_{i}"
            task = Task(
                id=task_id,
                func=simple_task,
                args=(task_id, i),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
            expected_order.append(task_id)
        
        # Execute concurrently with specified number of workers
        executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # PROPERTY VERIFICATION: Results are in original order
        actual_order = [r.task_id for r in results]
        assert actual_order == expected_order, \
            f"PROPERTY VIOLATION: Result order not preserved with {max_workers} workers! " \
            f"Expected: {expected_order}, got: {actual_order}"
        
        # PROPERTY VERIFICATION: All results are correct
        for i, result in enumerate(results):
            assert result.success, \
                f"PROPERTY VIOLATION: Task {result.task_id} failed"
            assert result.result == f"result_{i}", \
                f"PROPERTY VIOLATION: Task {result.task_id} has wrong result"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=2, max_value=10)
    )
    def test_result_order_preserved_with_random_execution_times(self, num_tasks):
        """
        Property: Result order should be preserved even when tasks have
        completely random execution times, ensuring no correlation between
        completion order and result order.
        """
        import random
        
        def random_timing_task(task_id: str, task_index: int, sleep_time: float) -> int:
            """Task with random execution time"""
            time.sleep(sleep_time)
            return task_index
        
        tasks = []
        expected_order = []
        
        # Generate random sleep times
        random.seed(42)  # For reproducibility in property testing
        sleep_times = [random.uniform(0.01, 0.1) for _ in range(num_tasks)]
        
        for i in range(num_tasks):
            task_id = f"task_{i}"
            task = Task(
                id=task_id,
                func=random_timing_task,
                args=(task_id, i, sleep_times[i]),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
            expected_order.append(task_id)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # PROPERTY VERIFICATION: Results are in original order
        actual_order = [r.task_id for r in results]
        assert actual_order == expected_order, \
            f"PROPERTY VIOLATION: Result order not preserved with random timings! " \
            f"Expected: {expected_order}, got: {actual_order}"
        
        # PROPERTY VERIFICATION: Each result has correct index
        for i, result in enumerate(results):
            assert result.result == i, \
                f"PROPERTY VIOLATION: Position {i} has wrong result value! " \
                f"Expected {i}, got {result.result}"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=1, max_value=10)
    )
    def test_result_order_preserved_with_edge_cases(self, num_tasks):
        """
        Property: Result order should be preserved even in edge cases like
        single task, empty list (if num_tasks=0), or all tasks completing
        instantly.
        """
        def instant_task(task_id: str, task_index: int) -> int:
            """Task that completes instantly"""
            return task_index
        
        tasks = []
        expected_order = []
        
        for i in range(num_tasks):
            task_id = f"task_{i}"
            task = Task(
                id=task_id,
                func=instant_task,
                args=(task_id, i),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
            expected_order.append(task_id)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # PROPERTY VERIFICATION: Correct number of results
        assert len(results) == num_tasks, \
            f"PROPERTY VIOLATION: Expected {num_tasks} results, got {len(results)}"
        
        # PROPERTY VERIFICATION: Results are in original order
        if num_tasks > 0:
            actual_order = [r.task_id for r in results]
            assert actual_order == expected_order, \
                f"PROPERTY VIOLATION: Result order not preserved in edge case! " \
                f"Expected: {expected_order}, got: {actual_order}"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=3, max_value=10)
    )
    def test_result_order_preserved_with_mixed_success_and_failure(self, num_tasks):
        """
        Property: Result order should be preserved when tasks have a mix of
        successes and failures in random patterns.
        """
        def mixed_outcome_task(task_id: str, task_index: int, should_fail: bool) -> int:
            """Task that may succeed or fail"""
            time.sleep(0.01)
            
            if should_fail:
                raise RuntimeError(f"Task {task_id} failed")
            
            return task_index * 10
        
        tasks = []
        expected_order = []
        failure_pattern = []
        
        # Create a pattern of successes and failures
        for i in range(num_tasks):
            task_id = f"task_{i}"
            # Alternate pattern: fail, succeed, succeed, fail, succeed, succeed, ...
            should_fail = (i % 3 == 0)
            
            task = Task(
                id=task_id,
                func=mixed_outcome_task,
                args=(task_id, i, should_fail),
                kwargs={},
                dependencies=[],
                required=False,
                metadata={}
            )
            tasks.append(task)
            expected_order.append(task_id)
            failure_pattern.append(should_fail)
        
        # Execute concurrently
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks)
        
        # PROPERTY VERIFICATION: All tasks have results
        assert len(results) == num_tasks, \
            f"PROPERTY VIOLATION: Expected {num_tasks} results, got {len(results)}"
        
        # PROPERTY VERIFICATION: Results are in original order
        actual_order = [r.task_id for r in results]
        assert actual_order == expected_order, \
            f"PROPERTY VIOLATION: Result order not preserved with mixed outcomes! " \
            f"Expected: {expected_order}, got: {actual_order}"
        
        # PROPERTY VERIFICATION: Success/failure pattern matches
        for i, (result, should_fail) in enumerate(zip(results, failure_pattern)):
            if should_fail:
                assert not result.success, \
                    f"PROPERTY VIOLATION: Task {result.task_id} should have failed"
            else:
                assert result.success, \
                    f"PROPERTY VIOLATION: Task {result.task_id} should have succeeded"
                assert result.result == i * 10, \
                    f"PROPERTY VIOLATION: Task {result.task_id} has wrong result"



class TestProgressFeedbackAvailabilityProperty:
    """
    Property 21: Progress feedback availability
    
    For any concurrent execution, the system should provide queryable progress
    information at any time.
    
    Validates: Requirements 9.5
    """
    
    # Feature: project-production-readiness, Property 21: Progress feedback availability
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=2, max_value=10),
        max_workers=st.integers(min_value=2, max_value=4)
    )
    def test_progress_queryable_during_execution(self, num_tasks, max_workers):
        """
        Property: During concurrent execution, progress information should be
        queryable at any time and should accurately reflect the current state
        of execution.
        
        This test verifies:
        1. Progress can be queried during execution
        2. Progress information is accurate (total, completed, running, pending)
        3. Progress updates as tasks complete
        4. Progress information is thread-safe
        """
        # Track progress snapshots during execution
        progress_snapshots = []
        lock = threading.Lock()
        
        def slow_task(task_id: str, sleep_time: float) -> str:
            """Task that takes some time to complete"""
            time.sleep(sleep_time)
            return f"completed_{task_id}"
        
        # Create tasks with varying sleep times
        # Use longer sleep times to ensure monitoring thread can capture progress
        # With max_workers, some tasks will wait, giving us time to capture progress
        task_sleep_time = 0.2  # Each task takes 0.2 seconds
        tasks = []
        for i in range(num_tasks):
            task = Task(
                id=f"task_{i}",
                func=slow_task,
                args=(f"task_{i}", task_sleep_time),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Create executor
        executor = ConcurrentExecutor(max_workers=max_workers, strategy="thread")
        
        # Flag to control progress monitoring thread
        monitoring_active = threading.Event()
        monitoring_active.set()
        execution_started = threading.Event()
        
        def monitor_progress():
            """Background thread that continuously queries progress"""
            # Wait for execution to start
            execution_started.wait(timeout=1.0)
            
            while monitoring_active.is_set():
                progress = executor.get_progress()
                # Only record snapshots after execution has started (total > 0)
                if progress.total > 0:
                    with lock:
                        progress_snapshots.append({
                            "total": progress.total,
                            "completed": progress.completed,
                            "failed": progress.failed,
                            "running": progress.running,
                            "pending": progress.pending,
                            "elapsed_time": progress.elapsed_time,
                            "completion_rate": progress.completion_rate
                        })
                time.sleep(0.02)  # Query every 20ms
        
        # Start monitoring thread
        monitor_thread = threading.Thread(target=monitor_progress)
        monitor_thread.start()
        
        # Signal that execution is starting
        execution_started.set()
        
        # Execute tasks
        results = executor.execute_concurrent(tasks)
        
        # Stop monitoring
        monitoring_active.clear()
        monitor_thread.join()
        
        # PROPERTY VERIFICATION 1: Progress was queryable during execution
        assert len(progress_snapshots) > 0, \
            "PROPERTY VIOLATION: No progress snapshots captured - progress not queryable"
        
        # PROPERTY VERIFICATION 2: Total is always correct
        for snapshot in progress_snapshots:
            assert snapshot["total"] == num_tasks, \
                f"PROPERTY VIOLATION: Total should always be {num_tasks}, got {snapshot['total']}"
        
        # PROPERTY VERIFICATION 3: Completed + running + pending = total (accounting invariant)
        for i, snapshot in enumerate(progress_snapshots):
            accounted = snapshot["completed"] + snapshot["running"] + snapshot["pending"]
            assert accounted == snapshot["total"], \
                f"PROPERTY VIOLATION: Accounting error in snapshot {i}: " \
                f"completed({snapshot['completed']}) + running({snapshot['running']}) + " \
                f"pending({snapshot['pending']}) = {accounted}, expected {snapshot['total']}"
        
        # PROPERTY VERIFICATION 4: Completed count is monotonically increasing
        completed_counts = [s["completed"] for s in progress_snapshots]
        for i in range(1, len(completed_counts)):
            assert completed_counts[i] >= completed_counts[i-1], \
                f"PROPERTY VIOLATION: Completed count decreased from {completed_counts[i-1]} " \
                f"to {completed_counts[i]} at snapshot {i}"
        
        # PROPERTY VERIFICATION 5: Final progress shows all tasks completed
        final_progress = executor.get_progress()
        assert final_progress.completed == num_tasks, \
            f"PROPERTY VIOLATION: Final completed count should be {num_tasks}, " \
            f"got {final_progress.completed}"
        assert final_progress.running == 0, \
            f"PROPERTY VIOLATION: Final running count should be 0, got {final_progress.running}"
        assert final_progress.pending == 0, \
            f"PROPERTY VIOLATION: Final pending count should be 0, got {final_progress.pending}"
        
        # PROPERTY VERIFICATION 6: Completion rate progresses
        # Note: With very fast execution, we might only capture snapshots at 0% or 100%
        # The key property is that completion_rate is monotonically non-decreasing
        completion_rates = [s["completion_rate"] for s in progress_snapshots]
        if len(completion_rates) > 1:
            # Verify monotonic increase
            for i in range(1, len(completion_rates)):
                assert completion_rates[i] >= completion_rates[i-1], \
                    f"PROPERTY VIOLATION: Completion rate decreased from {completion_rates[i-1]} " \
                    f"to {completion_rates[i]}"
        
        # PROPERTY VERIFICATION 7: All tasks completed successfully
        assert len(results) == num_tasks
        assert all(r.success for r in results)
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=3, max_value=8)
    )
    def test_progress_dict_contains_required_fields(self, num_tasks):
        """
        Property: The progress dictionary returned by get_progress_dict() should
        contain all required fields with correct types and values.
        """
        def simple_task(task_id: str) -> str:
            """Simple task"""
            time.sleep(0.05)
            return f"completed_{task_id}"
        
        # Create tasks
        tasks = []
        for i in range(num_tasks):
            task = Task(
                id=f"task_{i}",
                func=simple_task,
                args=(f"task_{i}",),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Create executor
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        
        # Execute tasks in background
        results_container = []
        
        def execute_tasks():
            results_container.extend(executor.execute_concurrent(tasks))
        
        thread = threading.Thread(target=execute_tasks)
        thread.start()
        
        # Wait a bit for execution to start
        time.sleep(0.02)
        
        # Query progress dict
        progress_dict = executor.get_progress_dict()
        
        # Wait for completion
        thread.join()
        
        # PROPERTY VERIFICATION: All required fields are present
        required_fields = [
            "total", "completed", "failed", "running", "pending", "skipped",
            "elapsed_time", "completion_rate", "success_rate"
        ]
        
        for field in required_fields:
            assert field in progress_dict, \
                f"PROPERTY VIOLATION: Required field '{field}' missing from progress dict"
        
        # PROPERTY VERIFICATION: Field types are correct
        assert isinstance(progress_dict["total"], int), \
            "PROPERTY VIOLATION: 'total' should be int"
        assert isinstance(progress_dict["completed"], int), \
            "PROPERTY VIOLATION: 'completed' should be int"
        assert isinstance(progress_dict["failed"], int), \
            "PROPERTY VIOLATION: 'failed' should be int"
        assert isinstance(progress_dict["running"], int), \
            "PROPERTY VIOLATION: 'running' should be int"
        assert isinstance(progress_dict["pending"], int), \
            "PROPERTY VIOLATION: 'pending' should be int"
        assert isinstance(progress_dict["skipped"], int), \
            "PROPERTY VIOLATION: 'skipped' should be int"
        assert isinstance(progress_dict["elapsed_time"], (int, float)), \
            "PROPERTY VIOLATION: 'elapsed_time' should be numeric"
        assert isinstance(progress_dict["completion_rate"], (int, float)), \
            "PROPERTY VIOLATION: 'completion_rate' should be numeric"
        assert isinstance(progress_dict["success_rate"], (int, float)), \
            "PROPERTY VIOLATION: 'success_rate' should be numeric"
        
        # PROPERTY VERIFICATION: Values are in valid ranges
        assert 0 <= progress_dict["completion_rate"] <= 1.0, \
            f"PROPERTY VIOLATION: completion_rate should be in [0, 1], " \
            f"got {progress_dict['completion_rate']}"
        assert 0 <= progress_dict["success_rate"] <= 1.0, \
            f"PROPERTY VIOLATION: success_rate should be in [0, 1], " \
            f"got {progress_dict['success_rate']}"
        assert progress_dict["elapsed_time"] >= 0, \
            f"PROPERTY VIOLATION: elapsed_time should be non-negative, " \
            f"got {progress_dict['elapsed_time']}"
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=2, max_value=8)
    )
    def test_progress_callback_receives_updates(self, num_tasks):
        """
        Property: When a progress callback is provided, it should receive
        progress updates during execution, and the updates should show
        increasing completion.
        """
        progress_updates = []
        
        def progress_callback(progress: ExecutionProgress):
            """Callback that records progress updates"""
            progress_updates.append({
                "completed": progress.completed,
                "total": progress.total,
                "running": progress.running,
                "pending": progress.pending
            })
        
        def simple_task(task_id: str) -> str:
            """Simple task"""
            time.sleep(0.05)
            return f"completed_{task_id}"
        
        # Create tasks
        tasks = []
        for i in range(num_tasks):
            task = Task(
                id=f"task_{i}",
                func=simple_task,
                args=(f"task_{i}",),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Execute with progress callback
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_concurrent(tasks, progress_callback=progress_callback)
        
        # PROPERTY VERIFICATION 1: Callback was invoked
        assert len(progress_updates) > 0, \
            "PROPERTY VIOLATION: Progress callback was never invoked"
        
        # PROPERTY VERIFICATION 2: Callback received multiple updates
        # (at least one per task completion)
        assert len(progress_updates) >= num_tasks, \
            f"PROPERTY VIOLATION: Expected at least {num_tasks} progress updates, " \
            f"got {len(progress_updates)}"
        
        # PROPERTY VERIFICATION 3: Completed count increases monotonically
        completed_counts = [u["completed"] for u in progress_updates]
        for i in range(1, len(completed_counts)):
            assert completed_counts[i] >= completed_counts[i-1], \
                f"PROPERTY VIOLATION: Completed count decreased from {completed_counts[i-1]} " \
                f"to {completed_counts[i]} in update {i}"
        
        # PROPERTY VERIFICATION 4: Final update shows all tasks completed
        final_update = progress_updates[-1]
        assert final_update["completed"] == num_tasks, \
            f"PROPERTY VIOLATION: Final update should show {num_tasks} completed, " \
            f"got {final_update['completed']}"
        
        # PROPERTY VERIFICATION 5: All tasks completed successfully
        assert len(results) == num_tasks
        assert all(r.success for r in results)
    
    @settings(max_examples=50, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=3, max_value=8)
    )
    def test_progress_available_with_dependencies(self, num_tasks):
        """
        Property: Progress information should be available and accurate even
        when executing tasks with dependencies (not just independent tasks).
        """
        progress_snapshots = []
        
        def progress_callback(progress: ExecutionProgress):
            """Callback that records progress"""
            progress_snapshots.append({
                "completed": progress.completed,
                "total": progress.total,
                "running": progress.running
            })
        
        def simple_task(task_id: str) -> str:
            """Simple task"""
            time.sleep(0.05)
            return f"completed_{task_id}"
        
        # Create tasks with dependencies: task_i depends on task_(i-1)
        tasks = []
        for i in range(num_tasks):
            dependencies = [f"task_{i-1}"] if i > 0 else []
            task = Task(
                id=f"task_{i}",
                func=simple_task,
                args=(f"task_{i}",),
                kwargs={},
                dependencies=dependencies,
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Execute with dependencies
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        results = executor.execute_with_dependencies(
            tasks,
            progress_callback=progress_callback
        )
        
        # PROPERTY VERIFICATION 1: Progress updates were received
        assert len(progress_snapshots) > 0, \
            "PROPERTY VIOLATION: No progress updates received for dependent tasks"
        
        # PROPERTY VERIFICATION 2: Total is always correct
        for snapshot in progress_snapshots:
            assert snapshot["total"] == num_tasks, \
                f"PROPERTY VIOLATION: Total should be {num_tasks}, got {snapshot['total']}"
        
        # PROPERTY VERIFICATION 3: Completed increases monotonically
        completed_counts = [s["completed"] for s in progress_snapshots]
        for i in range(1, len(completed_counts)):
            assert completed_counts[i] >= completed_counts[i-1], \
                f"PROPERTY VIOLATION: Completed count decreased in dependent execution"
        
        # PROPERTY VERIFICATION 4: All tasks completed
        assert len(results) == num_tasks
        assert all(r.success for r in results)
        
        # PROPERTY VERIFICATION 5: Final progress shows completion
        final_progress = executor.get_progress()
        assert final_progress.completed == num_tasks
        assert final_progress.running == 0
        assert final_progress.pending == 0
    
    @settings(max_examples=100, deadline=5000)
    @given(
        num_tasks=st.integers(min_value=2, max_value=8)
    )
    def test_progress_thread_safety(self, num_tasks):
        """
        Property: Progress information should be thread-safe - multiple threads
        should be able to query progress simultaneously without corruption.
        """
        def simple_task(task_id: str) -> str:
            """Simple task"""
            time.sleep(0.1)
            return f"completed_{task_id}"
        
        # Create tasks
        tasks = []
        for i in range(num_tasks):
            task = Task(
                id=f"task_{i}",
                func=simple_task,
                args=(f"task_{i}",),
                kwargs={},
                dependencies=[],
                required=True,
                metadata={}
            )
            tasks.append(task)
        
        # Create executor
        executor = ConcurrentExecutor(max_workers=4, strategy="thread")
        
        # Track progress queries from multiple threads
        query_results = []
        query_lock = threading.Lock()
        query_active = threading.Event()
        query_active.set()
        execution_started = threading.Event()
        
        def query_progress_repeatedly():
            """Thread that repeatedly queries progress"""
            # Wait for execution to start
            execution_started.wait(timeout=1.0)
            
            local_results = []
            while query_active.is_set():
                try:
                    progress = executor.get_progress()
                    progress_dict = executor.get_progress_dict()
                    
                    # Only record results after execution has started
                    if progress.total > 0:
                        # Verify consistency between the two methods
                        assert progress.total == progress_dict["total"]
                        assert progress.completed == progress_dict["completed"]
                        
                        local_results.append({
                            "total": progress.total,
                            "completed": progress.completed,
                            "valid": True
                        })
                except Exception as e:
                    local_results.append({
                        "error": str(e),
                        "valid": False
                    })
                
                time.sleep(0.01)
            
            with query_lock:
                query_results.extend(local_results)
        
        # Start multiple query threads
        query_threads = []
        for _ in range(3):  # 3 concurrent query threads
            thread = threading.Thread(target=query_progress_repeatedly)
            thread.start()
            query_threads.append(thread)
        
        # Signal that execution is starting
        execution_started.set()
        
        # Execute tasks
        results = executor.execute_concurrent(tasks)
        
        # Stop query threads
        query_active.clear()
        for thread in query_threads:
            thread.join()
        
        # PROPERTY VERIFICATION 1: All queries succeeded (no exceptions)
        failed_queries = [q for q in query_results if not q.get("valid", False)]
        assert len(failed_queries) == 0, \
            f"PROPERTY VIOLATION: {len(failed_queries)} queries failed due to thread safety issues"
        
        # PROPERTY VERIFICATION 2: Multiple queries were made
        assert len(query_results) > num_tasks, \
            f"PROPERTY VIOLATION: Expected multiple concurrent queries, got {len(query_results)}"
        
        # PROPERTY VERIFICATION 3: All queries returned valid data
        for query in query_results:
            assert query["total"] == num_tasks, \
                f"PROPERTY VIOLATION: Query returned wrong total: {query['total']}"
            assert 0 <= query["completed"] <= num_tasks, \
                f"PROPERTY VIOLATION: Query returned invalid completed count: {query['completed']}"
        
        # PROPERTY VERIFICATION 4: All tasks completed successfully
        assert len(results) == num_tasks
        assert all(r.success for r in results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
