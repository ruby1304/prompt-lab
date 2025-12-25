# tests/test_dependency_analyzer_properties.py
"""
DependencyAnalyzer Property-Based Tests

Property-based tests for dependency analysis functionality using Hypothesis.
Tests Property 12: Dependency identification
"""

import pytest
from hypothesis import given, strategies as st, settings
from hypothesis import assume

from src.dependency_analyzer import DependencyAnalyzer, DependencyGraph
from src.models import StepConfig


# ============================================================================
# Hypothesis Strategies for generating test data
# ============================================================================

def step_id_strategy():
    """Generate valid step IDs"""
    return st.text(
        min_size=1,
        max_size=20,
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789_'
    ).filter(lambda x: x[0].isalpha())  # Must start with letter


def output_key_strategy():
    """Generate valid output keys"""
    return st.text(
        min_size=1,
        max_size=20,
        alphabet='abcdefghijklmnopqrstuvwxyz0123456789_'
    ).filter(lambda x: x[0].isalpha())


def independent_steps_strategy():
    """
    Generate a list of independent steps (no dependencies)
    
    Returns steps that have no input_mapping and no depends_on,
    meaning they have no dependencies on other steps.
    """
    return st.lists(
        st.builds(
            StepConfig,
            id=step_id_strategy(),
            type=st.just("agent_flow"),
            agent=st.text(min_size=1, max_size=10, alphabet='abcdefghijklmnopqrstuvwxyz'),
            flow=st.text(min_size=1, max_size=10, alphabet='abcdefghijklmnopqrstuvwxyz'),
            output_key=output_key_strategy(),
            input_mapping=st.just({}),  # No input mapping = no dependencies
            depends_on=st.just([]),  # No explicit dependencies
            concurrent_group=st.none(),
            required=st.booleans()
        ),
        min_size=1,
        max_size=10,
        unique_by=lambda s: s.id  # Ensure unique step IDs
    )


def steps_with_dependencies_strategy():
    """
    Generate a list of steps where some have dependencies on others
    
    Creates a mix of independent steps and dependent steps.
    """
    # First, generate some independent steps
    num_independent = st.integers(min_value=1, max_value=5)
    
    @st.composite
    def _steps_with_deps(draw):
        n_independent = draw(num_independent)
        
        # Create independent steps
        independent_steps = []
        output_keys = []
        
        for i in range(n_independent):
            step_id = f"step_{i}"
            output_key = f"output_{i}"
            
            step = StepConfig(
                id=step_id,
                type="agent_flow",
                agent=f"agent_{i}",
                flow=f"flow_{i}",
                output_key=output_key,
                input_mapping={},
                depends_on=[],
                required=True
            )
            independent_steps.append(step)
            output_keys.append(output_key)
        
        # Create some dependent steps
        n_dependent = draw(st.integers(min_value=0, max_value=5))
        dependent_steps = []
        
        for i in range(n_dependent):
            step_id = f"dep_step_{i}"
            
            # Randomly choose to depend on some of the independent steps
            num_deps = draw(st.integers(min_value=1, max_value=min(3, len(output_keys))))
            chosen_outputs = draw(st.lists(
                st.sampled_from(output_keys),
                min_size=num_deps,
                max_size=num_deps,
                unique=True
            ))
            
            # Create input mapping from chosen outputs
            input_mapping = {
                f"input_{j}": output
                for j, output in enumerate(chosen_outputs)
            }
            
            step = StepConfig(
                id=step_id,
                type="agent_flow",
                agent=f"agent_dep_{i}",
                flow=f"flow_dep_{i}",
                output_key=f"dep_output_{i}",
                input_mapping=input_mapping,
                depends_on=[],
                required=True
            )
            dependent_steps.append(step)
        
        return independent_steps + dependent_steps
    
    return _steps_with_deps()


def steps_with_explicit_depends_on_strategy():
    """
    Generate steps with explicit depends_on relationships
    """
    @st.composite
    def _steps_with_explicit_deps(draw):
        n_steps = draw(st.integers(min_value=2, max_value=8))
        
        steps = []
        step_ids = [f"step_{i}" for i in range(n_steps)]
        
        for i, step_id in enumerate(step_ids):
            # First step has no dependencies
            if i == 0:
                depends_on = []
            else:
                # Later steps can depend on earlier steps
                num_deps = draw(st.integers(min_value=0, max_value=min(2, i)))
                if num_deps > 0:
                    depends_on = draw(st.lists(
                        st.sampled_from(step_ids[:i]),
                        min_size=num_deps,
                        max_size=num_deps,
                        unique=True
                    ))
                else:
                    depends_on = []
            
            step = StepConfig(
                id=step_id,
                type="agent_flow",
                agent=f"agent_{i}",
                flow=f"flow_{i}",
                output_key=f"output_{i}",
                input_mapping={},
                depends_on=depends_on,
                required=True
            )
            steps.append(step)
        
        return steps
    
    return _steps_with_explicit_deps()


# ============================================================================
# Property-Based Tests
# ============================================================================

class TestDependencyIdentificationProperty:
    """
    Property 12: Dependency identification
    
    For any pipeline configuration, the system should correctly identify
    all steps with no dependencies.
    
    Validates: Requirements 3.3
    """
    
    def setup_method(self):
        """Setup test fixtures"""
        self.analyzer = DependencyAnalyzer()
    
    # Feature: project-production-readiness, Property 12: Dependency identification
    @settings(max_examples=100)
    @given(steps=independent_steps_strategy())
    def test_all_independent_steps_have_no_dependencies(self, steps):
        """
        Property: When all steps are independent (no input_mapping, no depends_on),
        the dependency graph should show that all steps have empty dependency lists.
        
        This tests that the system correctly identifies steps with no dependencies.
        """
        # Analyze dependencies
        graph = self.analyzer.analyze_dependencies(steps)
        
        # All steps should be in the graph
        assert len(graph.nodes) == len(steps)
        assert set(graph.nodes) == {step.id for step in steps}
        
        # All steps should have no dependencies (empty edges)
        for step in steps:
            assert step.id in graph.edges
            assert len(graph.edges[step.id]) == 0, \
                f"Step {step.id} should have no dependencies but has: {graph.edges[step.id]}"
    
    @settings(max_examples=100)
    @given(steps=steps_with_dependencies_strategy())
    def test_independent_steps_identified_correctly(self, steps):
        """
        Property: In a mix of independent and dependent steps, the system should
        correctly identify which steps have no dependencies.
        
        A step has no dependencies if:
        1. Its input_mapping doesn't reference any other step's output_key
        2. Its depends_on list is empty
        """
        # Build a map of output_key to step_id
        output_to_step = {step.output_key: step.id for step in steps if step.output_key}
        
        # Identify which steps should be independent
        expected_independent = []
        for step in steps:
            has_input_deps = any(
                source in output_to_step
                for source in step.input_mapping.values()
            )
            has_explicit_deps = len(step.depends_on) > 0
            
            if not has_input_deps and not has_explicit_deps:
                expected_independent.append(step.id)
        
        # Analyze dependencies
        graph = self.analyzer.analyze_dependencies(steps)
        
        # Check that identified independent steps match expectations
        actual_independent = [
            node for node in graph.nodes
            if len(graph.edges[node]) == 0
        ]
        
        assert set(actual_independent) == set(expected_independent), \
            f"Expected independent steps: {expected_independent}, but got: {actual_independent}"
    
    @settings(max_examples=100)
    @given(steps=steps_with_explicit_depends_on_strategy())
    def test_explicit_dependencies_identified(self, steps):
        """
        Property: When steps have explicit depends_on relationships,
        the system should correctly identify which steps have dependencies
        and which don't.
        """
        # Identify expected independent steps (no depends_on)
        expected_independent = [
            step.id for step in steps
            if len(step.depends_on) == 0
        ]
        
        # Analyze dependencies
        graph = self.analyzer.analyze_dependencies(steps)
        
        # Check independent steps
        actual_independent = [
            node for node in graph.nodes
            if len(graph.edges[node]) == 0
        ]
        
        assert set(actual_independent) == set(expected_independent), \
            f"Expected independent: {expected_independent}, got: {actual_independent}"
        
        # Check that dependent steps have the correct dependencies
        for step in steps:
            if len(step.depends_on) > 0:
                assert step.id in graph.edges
                # The step should depend on all steps in depends_on
                for dep_id in step.depends_on:
                    assert dep_id in graph.edges[step.id], \
                        f"Step {step.id} should depend on {dep_id}"
    
    @settings(max_examples=100)
    @given(
        num_steps=st.integers(min_value=1, max_value=20)
    )
    def test_all_steps_present_in_dependency_graph(self, num_steps):
        """
        Property: For any list of steps, all steps should appear in the
        dependency graph's nodes list.
        """
        # Generate steps
        steps = [
            StepConfig(
                id=f"step_{i}",
                type="agent_flow",
                agent=f"agent_{i}",
                flow=f"flow_{i}",
                output_key=f"output_{i}",
                input_mapping={},
                depends_on=[],
                required=True
            )
            for i in range(num_steps)
        ]
        
        # Analyze dependencies
        graph = self.analyzer.analyze_dependencies(steps)
        
        # All steps should be in nodes
        assert len(graph.nodes) == num_steps
        assert set(graph.nodes) == {f"step_{i}" for i in range(num_steps)}
        
        # All nodes should have an entry in edges (even if empty)
        for node in graph.nodes:
            assert node in graph.edges
    
    @settings(max_examples=100)
    @given(steps=independent_steps_strategy())
    def test_independent_steps_can_be_concurrent(self, steps):
        """
        Property: All independent steps (steps with no dependencies) should
        be identified as being able to execute concurrently.
        
        This is verified by checking that find_concurrent_groups places
        all independent steps in the same concurrent group.
        """
        # Skip if we have no steps
        assume(len(steps) > 0)
        
        # Analyze dependencies
        graph = self.analyzer.analyze_dependencies(steps)
        
        # Find concurrent groups
        concurrent_groups = self.analyzer.find_concurrent_groups(graph)
        
        # Since all steps are independent, they should all be in the first group
        assert len(concurrent_groups) >= 1
        
        # The first group should contain all steps
        first_group = concurrent_groups[0]
        assert set(first_group) == {step.id for step in steps}, \
            f"Expected all independent steps in first group, but got: {first_group}"
    
    @settings(max_examples=50)
    @given(
        num_independent=st.integers(min_value=2, max_value=10),
        num_dependent=st.integers(min_value=1, max_value=5)
    )
    def test_dependency_graph_structure_consistency(self, num_independent, num_dependent):
        """
        Property: The dependency graph structure should be consistent:
        - All nodes should have an entry in edges
        - Dependencies should only reference existing nodes
        - No self-dependencies should exist
        """
        # Create independent steps
        steps = []
        output_keys = []
        
        for i in range(num_independent):
            step = StepConfig(
                id=f"indep_{i}",
                type="agent_flow",
                agent=f"agent_{i}",
                flow=f"flow_{i}",
                output_key=f"output_{i}",
                input_mapping={},
                depends_on=[],
                required=True
            )
            steps.append(step)
            output_keys.append(f"output_{i}")
        
        # Create dependent steps that depend on independent steps
        for i in range(num_dependent):
            # Pick a random output to depend on
            dep_output = output_keys[i % len(output_keys)]
            
            step = StepConfig(
                id=f"dep_{i}",
                type="agent_flow",
                agent=f"agent_dep_{i}",
                flow=f"flow_dep_{i}",
                output_key=f"dep_output_{i}",
                input_mapping={"input": dep_output},
                depends_on=[],
                required=True
            )
            steps.append(step)
        
        # Analyze dependencies
        graph = self.analyzer.analyze_dependencies(steps)
        
        # Check consistency
        # 1. All nodes should have an entry in edges
        for node in graph.nodes:
            assert node in graph.edges, f"Node {node} missing from edges"
        
        # 2. All dependencies should reference existing nodes
        for node, deps in graph.edges.items():
            for dep in deps:
                assert dep in graph.nodes, \
                    f"Node {node} depends on {dep} which doesn't exist in nodes"
        
        # 3. No self-dependencies
        for node, deps in graph.edges.items():
            assert node not in deps, f"Node {node} has self-dependency"
    
    @settings(max_examples=50)
    @given(steps=independent_steps_strategy())
    def test_topological_sort_of_independent_steps(self, steps):
        """
        Property: For independent steps, topological sort should return
        all steps (in any order, since they're all independent).
        """
        assume(len(steps) > 0)
        
        # Analyze dependencies
        graph = self.analyzer.analyze_dependencies(steps)
        
        # Perform topological sort
        sorted_steps = self.analyzer.topological_sort(graph)
        
        # All steps should be in the result
        assert len(sorted_steps) == len(steps)
        assert set(sorted_steps) == {step.id for step in steps}
    
    @settings(max_examples=50)
    @given(
        num_steps=st.integers(min_value=2, max_value=10)
    )
    def test_linear_dependency_chain_identification(self, num_steps):
        """
        Property: In a linear dependency chain (step1 -> step2 -> step3 -> ...),
        only the first step should have no dependencies.
        """
        # Create a linear chain
        steps = []
        for i in range(num_steps):
            if i == 0:
                # First step has no dependencies
                step = StepConfig(
                    id=f"step_{i}",
                    type="agent_flow",
                    agent=f"agent_{i}",
                    flow=f"flow_{i}",
                    output_key=f"output_{i}",
                    input_mapping={},
                    depends_on=[],
                    required=True
                )
            else:
                # Each subsequent step depends on the previous one
                step = StepConfig(
                    id=f"step_{i}",
                    type="agent_flow",
                    agent=f"agent_{i}",
                    flow=f"flow_{i}",
                    output_key=f"output_{i}",
                    input_mapping={"input": f"output_{i-1}"},
                    depends_on=[],
                    required=True
                )
            steps.append(step)
        
        # Analyze dependencies
        graph = self.analyzer.analyze_dependencies(steps)
        
        # Only the first step should have no dependencies
        independent_steps = [
            node for node in graph.nodes
            if len(graph.edges[node]) == 0
        ]
        
        assert len(independent_steps) == 1, \
            f"Expected exactly 1 independent step, got {len(independent_steps)}: {independent_steps}"
        assert independent_steps[0] == "step_0", \
            f"Expected step_0 to be independent, got {independent_steps[0]}"
        
        # All other steps should have exactly one dependency
        for i in range(1, num_steps):
            step_id = f"step_{i}"
            assert len(graph.edges[step_id]) == 1, \
                f"Step {step_id} should have 1 dependency, has {len(graph.edges[step_id])}"
            assert f"step_{i-1}" in graph.edges[step_id], \
                f"Step {step_id} should depend on step_{i-1}"
