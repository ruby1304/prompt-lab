#!/usr/bin/env python
"""
Testset Pipeline Integration Example

Demonstrates how the testset loader integrates with pipeline execution.
This is a conceptual example showing the intended usage pattern.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.testset_loader import load_testset, TestCase


def simulate_pipeline_execution(test_case: TestCase, pipeline_config: dict):
    """
    Simulates how a pipeline would use the TestCase data.
    
    This is a conceptual example - actual implementation would be in
    the PipelineRunner class.
    """
    print(f"\n{'='*70}")
    print(f"Executing Pipeline for Test Case: {test_case.id}")
    print(f"{'='*70}")
    
    # 1. Get global inputs
    print("\n1. Global Inputs:")
    for key, value in test_case.inputs.items():
        print(f"   {key}: {value}")
    
    # 2. Execute pipeline steps
    print("\n2. Executing Pipeline Steps:")
    
    for step in pipeline_config.get("steps", []):
        step_id = step["id"]
        print(f"\n   Step: {step_id}")
        
        # Get step-specific inputs if available
        if test_case.has_step_inputs() and step_id in test_case.step_inputs:
            print(f"   Step-specific inputs:")
            for key, value in test_case.step_inputs[step_id].items():
                print(f"     {key}: {value}")
        
        # Check if this is a batch processing step
        if step.get("batch_mode") and test_case.has_batch_data():
            print(f"   Batch processing: {len(test_case.batch_items)} items")
            for i, item in enumerate(test_case.batch_items[:3]):  # Show first 3
                print(f"     Item {i+1}: {item}")
            if len(test_case.batch_items) > 3:
                print(f"     ... and {len(test_case.batch_items) - 3} more items")
    
    # 3. Validate expected outputs
    print("\n3. Expected Outputs:")
    if test_case.expected_outputs:
        for key, value in test_case.expected_outputs.items():
            print(f"   {key}: {value}")
    else:
        print("   (No expected outputs specified)")
    
    # 4. Validate expected aggregation
    if test_case.has_expected_aggregation():
        print("\n4. Expected Aggregation:")
        print(f"   {test_case.expected_aggregation}")
    
    print(f"\n{'='*70}\n")


def main():
    print("=" * 70)
    print("Testset Pipeline Integration Example")
    print("=" * 70)
    
    # Load testset
    testset_path = Path("examples/testsets/pipeline_testset_formats.jsonl")
    
    if not testset_path.exists():
        print(f"Testset file not found: {testset_path}")
        return
    
    test_cases = load_testset(testset_path)
    print(f"\nLoaded {len(test_cases)} test cases\n")
    
    # Example pipeline configuration
    pipeline_config = {
        "id": "example_pipeline",
        "name": "Example Pipeline",
        "steps": [
            {
                "id": "preprocess",
                "type": "code_node",
                "language": "python"
            },
            {
                "id": "analyze",
                "type": "agent_flow",
                "agent": "analyzer",
                "batch_mode": True
            },
            {
                "id": "aggregate",
                "type": "batch_aggregator",
                "aggregation_strategy": "custom"
            }
        ]
    }
    
    # Simulate pipeline execution for each test case
    for test_case in test_cases:
        simulate_pipeline_execution(test_case, pipeline_config)
    
    print("\n" + "=" * 70)
    print("Integration Example Complete!")
    print("=" * 70)
    print("\nKey Integration Points:")
    print("1. TestCase.inputs → Pipeline global inputs")
    print("2. TestCase.step_inputs → Step-specific configuration")
    print("3. TestCase.batch_items → Batch processing data")
    print("4. TestCase.expected_outputs → Output validation")
    print("5. TestCase.expected_aggregation → Aggregation validation")
    print("=" * 70)


if __name__ == "__main__":
    main()
