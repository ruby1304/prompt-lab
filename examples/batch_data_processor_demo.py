"""
Batch Data Processor Demo

Demonstrates the BatchProcessor class for handling batch operations in pipelines.
Shows batch size control, concurrent processing, and result aggregation.

Requirements: 4.2
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.batch_aggregator import BatchProcessor, BatchProcessingResult


def demo_basic_batch_processing():
    """Demo: Basic batch processing with simple function"""
    print("=" * 60)
    print("Demo 1: Basic Batch Processing")
    print("=" * 60)
    
    processor = BatchProcessor(max_workers=4)
    
    # Sample data: list of numbers
    items = list(range(1, 21))  # 1 to 20
    print(f"\nProcessing {len(items)} items: {items}")
    
    # Simple processing function
    def square(x):
        return x ** 2
    
    # Process in batches
    results = processor.process_in_batches(
        items,
        square,
        batch_size=5,
        concurrent=False
    )
    
    print(f"\nResults: {results}")
    print(f"Total items processed: {len(results)}")


def demo_concurrent_batch_processing():
    """Demo: Concurrent batch processing for better performance"""
    print("\n" + "=" * 60)
    print("Demo 2: Concurrent Batch Processing")
    print("=" * 60)
    
    processor = BatchProcessor(max_workers=4)
    
    # Sample data: list of dictionaries
    items = [
        {"id": i, "value": i * 10}
        for i in range(1, 31)
    ]
    print(f"\nProcessing {len(items)} items concurrently...")
    
    # Processing function that extracts and transforms data
    def extract_and_double(item):
        return {
            "id": item["id"],
            "original": item["value"],
            "doubled": item["value"] * 2
        }
    
    # Process concurrently
    results = processor.process_in_batches(
        items,
        extract_and_double,
        batch_size=10,
        concurrent=True
    )
    
    print(f"\nFirst 5 results:")
    for result in results[:5]:
        print(f"  {result}")
    print(f"... and {len(results) - 5} more")


def demo_batch_processing_with_errors():
    """Demo: Batch processing with error handling"""
    print("\n" + "=" * 60)
    print("Demo 3: Batch Processing with Error Handling")
    print("=" * 60)
    
    processor = BatchProcessor(max_workers=2)
    
    # Sample data with some problematic values
    items = [10, 5, 0, 8, 2, 0, 15, 3]  # 0 will cause division errors
    print(f"\nProcessing items: {items}")
    print("Note: Division by zero will be handled gracefully")
    
    # Function that may fail for some items
    def divide_100_by(x):
        return 100 / x
    
    # Process with error handling
    results = processor.process_in_batches(
        items,
        divide_100_by,
        batch_size=3,
        concurrent=False
    )
    
    print(f"\nResults:")
    for i, (item, result) in enumerate(zip(items, results)):
        if result is None:
            print(f"  Item {i} ({item}): FAILED (division by zero)")
        else:
            print(f"  Item {i} ({item}): {result:.2f}")


def demo_detailed_batch_processing():
    """Demo: Detailed batch processing with comprehensive results"""
    print("\n" + "=" * 60)
    print("Demo 4: Detailed Batch Processing")
    print("=" * 60)
    
    processor = BatchProcessor(max_workers=4)
    
    # Sample data
    items = [
        {"name": "Alice", "score": 85},
        {"name": "Bob", "score": 92},
        {"name": "Charlie", "score": 78},
        {"name": "David", "score": 88},
        {"name": "Eve", "score": 95}
    ]
    print(f"\nProcessing {len(items)} student records...")
    
    # Processing function
    def calculate_grade(student):
        score = student["score"]
        if score >= 90:
            grade = "A"
        elif score >= 80:
            grade = "B"
        elif score >= 70:
            grade = "C"
        else:
            grade = "F"
        
        return {
            "name": student["name"],
            "score": score,
            "grade": grade
        }
    
    # Process with detailed results
    result = processor.process_in_batches_detailed(
        items,
        calculate_grade,
        batch_size=2,
        concurrent=True
    )
    
    print(f"\nProcessing Summary:")
    print(f"  Success: {result.success}")
    print(f"  Total items: {result.total_items}")
    print(f"  Batch count: {result.batch_count}")
    print(f"  Failed items: {len(result.failed_items)}")
    print(f"  Execution time: {result.execution_time:.4f}s")
    
    print(f"\nGrade Results:")
    for student_result in result.results:
        print(f"  {student_result['name']}: {student_result['score']} -> {student_result['grade']}")


def demo_batch_size_comparison():
    """Demo: Compare different batch sizes"""
    print("\n" + "=" * 60)
    print("Demo 5: Batch Size Comparison")
    print("=" * 60)
    
    processor = BatchProcessor(max_workers=4)
    
    # Large dataset
    items = list(range(1, 101))  # 1 to 100
    
    def simple_transform(x):
        return x * 2
    
    # Test different batch sizes
    batch_sizes = [5, 10, 25, 50]
    
    print(f"\nProcessing {len(items)} items with different batch sizes:")
    
    for batch_size in batch_sizes:
        result = processor.process_in_batches_detailed(
            items,
            simple_transform,
            batch_size=batch_size,
            concurrent=True
        )
        
        print(f"\n  Batch size {batch_size}:")
        print(f"    Batches created: {result.batch_count}")
        print(f"    Execution time: {result.execution_time:.4f}s")
        print(f"    Items per batch: {len(items) // result.batch_count}")


def demo_real_world_scenario():
    """Demo: Real-world scenario - processing API responses"""
    print("\n" + "=" * 60)
    print("Demo 6: Real-World Scenario - Processing API Responses")
    print("=" * 60)
    
    processor = BatchProcessor(max_workers=4)
    
    # Simulated API responses
    api_responses = [
        {"user_id": 1, "status": "success", "data": {"views": 150, "likes": 45}},
        {"user_id": 2, "status": "success", "data": {"views": 230, "likes": 67}},
        {"user_id": 3, "status": "error", "error": "User not found"},
        {"user_id": 4, "status": "success", "data": {"views": 89, "likes": 23}},
        {"user_id": 5, "status": "success", "data": {"views": 310, "likes": 92}},
        {"user_id": 6, "status": "error", "error": "Rate limit exceeded"},
        {"user_id": 7, "status": "success", "data": {"views": 175, "likes": 51}},
        {"user_id": 8, "status": "success", "data": {"views": 420, "likes": 128}},
    ]
    
    print(f"\nProcessing {len(api_responses)} API responses...")
    
    # Processing function to extract and normalize data
    def process_api_response(response):
        if response["status"] == "error":
            # Return None for failed responses
            raise ValueError(f"API error: {response.get('error', 'Unknown error')}")
        
        data = response["data"]
        return {
            "user_id": response["user_id"],
            "views": data["views"],
            "likes": data["likes"],
            "engagement_rate": (data["likes"] / data["views"]) * 100 if data["views"] > 0 else 0
        }
    
    # Process responses
    results = processor.process_in_batches(
        api_responses,
        process_api_response,
        batch_size=3,
        concurrent=True
    )
    
    # Analyze results
    successful_results = [r for r in results if r is not None]
    failed_count = len([r for r in results if r is None])
    
    print(f"\nProcessing Results:")
    print(f"  Successful: {len(successful_results)}")
    print(f"  Failed: {failed_count}")
    
    print(f"\nSuccessful Results:")
    for result in successful_results:
        print(f"  User {result['user_id']}: "
              f"{result['views']} views, {result['likes']} likes "
              f"({result['engagement_rate']:.2f}% engagement)")
    
    # Calculate aggregate statistics
    if successful_results:
        avg_views = sum(r["views"] for r in successful_results) / len(successful_results)
        avg_likes = sum(r["likes"] for r in successful_results) / len(successful_results)
        avg_engagement = sum(r["engagement_rate"] for r in successful_results) / len(successful_results)
        
        print(f"\nAggregate Statistics:")
        print(f"  Average views: {avg_views:.2f}")
        print(f"  Average likes: {avg_likes:.2f}")
        print(f"  Average engagement rate: {avg_engagement:.2f}%")


def main():
    """Run all demos"""
    print("\n" + "=" * 60)
    print("BATCH DATA PROCESSOR DEMO")
    print("=" * 60)
    print("\nThis demo showcases the BatchProcessor class capabilities:")
    print("- Batch size control")
    print("- Concurrent vs sequential processing")
    print("- Error handling for individual items")
    print("- Detailed processing results")
    print("- Real-world scenarios")
    
    demo_basic_batch_processing()
    demo_concurrent_batch_processing()
    demo_batch_processing_with_errors()
    demo_detailed_batch_processing()
    demo_batch_size_comparison()
    demo_real_world_scenario()
    
    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
