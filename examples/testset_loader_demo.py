#!/usr/bin/env python
"""
Testset Loader Demo

Demonstrates how to use the testset loader to load and work with
batch processing testsets.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.testset_loader import (
    TestsetLoader, load_testset, validate_testset, filter_by_tags
)


def main():
    print("=" * 70)
    print("Testset Loader Demo")
    print("=" * 70)
    print()
    
    # Example 1: Load a simple testset
    print("Example 1: Loading Pipeline Testset Formats")
    print("-" * 70)
    
    testset_path = Path("examples/testsets/pipeline_testset_formats.jsonl")
    if testset_path.exists():
        test_cases = load_testset(testset_path)
        print(f"Loaded {len(test_cases)} test cases")
        
        for tc in test_cases:
            print(f"\n  Test ID: {tc.id}")
            print(f"  Tags: {tc.tags}")
            print(f"  Has batch data: {tc.has_batch_data()}")
            print(f"  Has step inputs: {tc.has_step_inputs()}")
            
            if tc.has_batch_data():
                print(f"  Batch items count: {len(tc.batch_items)}")
            
            if tc.has_step_inputs():
                print(f"  Step inputs: {list(tc.step_inputs.keys())}")
    else:
        print(f"  Testset file not found: {testset_path}")
    
    print()
    
    # Example 2: Load batch processing testset
    print("Example 2: Loading Batch Processing Advanced Testset")
    print("-" * 70)
    
    batch_testset_path = Path("examples/testsets/batch_processing_advanced.jsonl")
    if batch_testset_path.exists():
        batch_cases = load_testset(batch_testset_path)
        print(f"Loaded {len(batch_cases)} batch test cases")
        
        for tc in batch_cases:
            print(f"\n  Test ID: {tc.id}")
            print(f"  Tags: {tc.tags}")
            
            if tc.has_batch_data():
                print(f"  Batch items: {len(tc.batch_items)}")
                print(f"  First item: {tc.batch_items[0]}")
            
            if tc.has_expected_aggregation():
                print(f"  Expected aggregation: {tc.expected_aggregation}")
    else:
        print(f"  Testset file not found: {batch_testset_path}")
    
    print()
    
    # Example 3: Validate testset
    print("Example 3: Validating Testset")
    print("-" * 70)
    
    if testset_path.exists():
        test_cases = load_testset(testset_path)
        errors = validate_testset(test_cases)
        
        if errors:
            print("  Validation errors found:")
            for error in errors:
                print(f"    - {error}")
        else:
            print("  ✓ Testset is valid!")
    
    print()
    
    # Example 4: Filter by tags
    print("Example 4: Filtering by Tags")
    print("-" * 70)
    
    if testset_path.exists():
        test_cases = load_testset(testset_path)
        
        # Filter for batch tests
        batch_tests = filter_by_tags(test_cases, include_tags=["batch"])
        print(f"  Batch tests: {len(batch_tests)}")
        for tc in batch_tests:
            print(f"    - {tc.id}")
        
        # Filter for simple tests
        simple_tests = filter_by_tags(test_cases, include_tags=["simple"])
        print(f"\n  Simple tests: {len(simple_tests)}")
        for tc in simple_tests:
            print(f"    - {tc.id}")
        
        # Exclude complex tests
        non_complex = filter_by_tags(test_cases, exclude_tags=["complex"])
        print(f"\n  Non-complex tests: {len(non_complex)}")
        for tc in non_complex:
            print(f"    - {tc.id}")
    
    print()
    
    # Example 5: Get specific test case types
    print("Example 5: Getting Specific Test Case Types")
    print("-" * 70)
    
    if batch_testset_path.exists():
        test_cases = load_testset(batch_testset_path)
        
        # Get batch test cases
        batch_cases = TestsetLoader.get_batch_test_cases(test_cases)
        print(f"  Test cases with batch data: {len(batch_cases)}")
        for tc in batch_cases:
            print(f"    - {tc.id}: {len(tc.batch_items)} items")
        
        # Get step input test cases
        step_cases = TestsetLoader.get_step_input_test_cases(test_cases)
        print(f"\n  Test cases with step inputs: {len(step_cases)}")
        for tc in step_cases:
            print(f"    - {tc.id}: steps {list(tc.step_inputs.keys())}")
    
    print()
    
    # Example 6: Accessing test case data
    print("Example 6: Accessing Test Case Data")
    print("-" * 70)
    
    if testset_path.exists():
        test_cases = load_testset(testset_path)
        
        if test_cases:
            tc = test_cases[0]
            print(f"  Test case: {tc.id}")
            print(f"  Description: {tc.get_input('description', 'N/A')}")
            
            # Get global inputs
            print(f"\n  Global inputs:")
            for key, value in tc.inputs.items():
                print(f"    {key}: {value}")
            
            # Get step-specific inputs
            if tc.has_step_inputs():
                print(f"\n  Step-specific inputs:")
                for step_id, step_input in tc.step_inputs.items():
                    print(f"    {step_id}:")
                    for key, value in step_input.items():
                        print(f"      {key}: {value}")
            
            # Get expected outputs
            if tc.expected_outputs:
                print(f"\n  Expected outputs:")
                for key, value in tc.expected_outputs.items():
                    print(f"    {key}: {value}")
    
    print()
    print("=" * 70)
    print("Demo Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
