"""
Batch Aggregator Demo

Demonstrates the usage of BatchAggregator for different aggregation strategies.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from batch_aggregator import BatchAggregator


def demo_concat_aggregation():
    """Demonstrate concat aggregation"""
    print("=" * 60)
    print("Demo: Concat Aggregation")
    print("=" * 60)
    
    aggregator = BatchAggregator()
    
    # Example 1: Simple strings
    items = ["Hello", "World", "from", "BatchAggregator"]
    result = aggregator.aggregate_concat(items, separator=" ")
    print(f"\nSimple strings: {result}")
    
    # Example 2: Dict items with text field
    items = [
        {"text": "First result", "score": 85},
        {"text": "Second result", "score": 90},
        {"text": "Third result", "score": 78}
    ]
    result = aggregator.aggregate_concat(items, separator="\n---\n")
    print(f"\nDict items with text field:\n{result}")
    
    # Example 3: Using aggregate method
    items = ["Line 1", "Line 2", "Line 3"]
    result = aggregator.aggregate(items, strategy="concat", separator="\n")
    print(f"\nUsing aggregate method:")
    print(f"Success: {result.success}")
    print(f"Result:\n{result.result}")
    print(f"Item count: {result.item_count}")


def demo_stats_aggregation():
    """Demonstrate stats aggregation"""
    print("\n" + "=" * 60)
    print("Demo: Stats Aggregation")
    print("=" * 60)
    
    aggregator = BatchAggregator()
    
    # Example: Calculate statistics on test scores
    items = [
        {"student": "Alice", "score": 85, "time": 1.2},
        {"student": "Bob", "score": 90, "time": 1.5},
        {"student": "Charlie", "score": 78, "time": 1.1},
        {"student": "David", "score": 92, "time": 1.3},
        {"student": "Eve", "score": 88, "time": 1.4}
    ]
    
    result = aggregator.aggregate_stats(items, fields=["score", "time"])
    
    print(f"\nTotal items: {result['total_items']}")
    print("\nScore statistics:")
    score_stats = result["fields"]["score"]
    print(f"  Count: {score_stats['count']}")
    print(f"  Mean: {score_stats['mean']:.2f}")
    print(f"  Min: {score_stats['min']}")
    print(f"  Max: {score_stats['max']}")
    print(f"  Median: {score_stats['median']:.2f}")
    print(f"  Stdev: {score_stats['stdev']:.2f}")
    
    print("\nTime statistics:")
    time_stats = result["fields"]["time"]
    print(f"  Count: {time_stats['count']}")
    print(f"  Mean: {time_stats['mean']:.2f}")
    print(f"  Min: {time_stats['min']}")
    print(f"  Max: {time_stats['max']}")


def demo_filter_aggregation():
    """Demonstrate filter aggregation"""
    print("\n" + "=" * 60)
    print("Demo: Filter Aggregation")
    print("=" * 60)
    
    aggregator = BatchAggregator()
    
    # Example: Filter test results
    items = [
        {"student": "Alice", "score": 85, "passed": True},
        {"student": "Bob", "score": 45, "passed": False},
        {"student": "Charlie", "score": 90, "passed": True},
        {"student": "David", "score": 60, "passed": False},
        {"student": "Eve", "score": 88, "passed": True}
    ]
    
    # Filter 1: Get only passed students
    passed_students = aggregator.aggregate_filter(
        items,
        condition=lambda x: x.get("passed", False)
    )
    print(f"\nPassed students ({len(passed_students)}):")
    for student in passed_students:
        print(f"  - {student['student']}: {student['score']}")
    
    # Filter 2: Get high scorers (>= 85)
    high_scorers = aggregator.aggregate_filter(
        items,
        condition=lambda x: x.get("score", 0) >= 85
    )
    print(f"\nHigh scorers (>= 85) ({len(high_scorers)}):")
    for student in high_scorers:
        print(f"  - {student['student']}: {student['score']}")


def demo_custom_aggregation():
    """Demonstrate custom aggregation with code execution"""
    print("\n" + "=" * 60)
    print("Demo: Custom Aggregation")
    print("=" * 60)
    
    aggregator = BatchAggregator()
    
    # Example 1: Python custom aggregation
    items = [
        {"score": 85, "passed": True},
        {"score": 45, "passed": False},
        {"score": 90, "passed": True},
        {"score": 60, "passed": False}
    ]
    
    python_code = """
def aggregate(items):
    passed = [item for item in items if item.get("passed", False)]
    failed = [item for item in items if not item.get("passed", False)]
    
    return {
        "total": len(items),
        "passed_count": len(passed),
        "failed_count": len(failed),
        "pass_rate": len(passed) / len(items) * 100 if items else 0,
        "avg_passed_score": sum(item["score"] for item in passed) / len(passed) if passed else 0,
        "avg_failed_score": sum(item["score"] for item in failed) / len(failed) if failed else 0
    }
"""
    
    result = aggregator.aggregate_custom(items, python_code, language="python")
    print(f"\nPython custom aggregation:")
    print(f"  Total: {result['total']}")
    print(f"  Passed: {result['passed_count']}")
    print(f"  Failed: {result['failed_count']}")
    print(f"  Pass rate: {result['pass_rate']:.1f}%")
    print(f"  Avg passed score: {result['avg_passed_score']:.2f}")
    print(f"  Avg failed score: {result['avg_failed_score']:.2f}")
    
    # Example 2: JavaScript custom aggregation
    items = [
        {"name": "Product A", "sales": 100, "revenue": 1000},
        {"name": "Product B", "sales": 150, "revenue": 2250},
        {"name": "Product C", "sales": 80, "revenue": 960}
    ]
    
    js_code = """
function aggregate(items) {
    const totalSales = items.reduce((sum, item) => sum + item.sales, 0);
    const totalRevenue = items.reduce((sum, item) => sum + item.revenue, 0);
    const avgPrice = totalRevenue / totalSales;
    
    const topProduct = items.reduce((max, item) => 
        item.revenue > max.revenue ? item : max
    );
    
    return {
        total_sales: totalSales,
        total_revenue: totalRevenue,
        average_price: avgPrice,
        top_product: topProduct.name,
        top_product_revenue: topProduct.revenue
    };
}

module.exports = aggregate;
"""
    
    result = aggregator.aggregate_custom(items, js_code, language="javascript")
    print(f"\nJavaScript custom aggregation:")
    print(f"  Total sales: {result['total_sales']}")
    print(f"  Total revenue: ${result['total_revenue']}")
    print(f"  Average price: ${result['average_price']:.2f}")
    print(f"  Top product: {result['top_product']} (${result['top_product_revenue']})")


def demo_aggregate_method():
    """Demonstrate using the main aggregate method"""
    print("\n" + "=" * 60)
    print("Demo: Using Aggregate Method")
    print("=" * 60)
    
    aggregator = BatchAggregator()
    
    items = [
        {"text": "Result A", "score": 85, "passed": True},
        {"text": "Result B", "score": 45, "passed": False},
        {"text": "Result C", "score": 90, "passed": True}
    ]
    
    # Strategy 1: Concat
    result = aggregator.aggregate(items, strategy="concat", separator=" | ")
    print(f"\nConcat strategy:")
    print(f"  Success: {result.success}")
    print(f"  Result: {result.result}")
    
    # Strategy 2: Stats
    result = aggregator.aggregate(items, strategy="stats", fields=["score"])
    print(f"\nStats strategy:")
    print(f"  Success: {result.success}")
    print(f"  Mean score: {result.result['fields']['score']['mean']:.2f}")
    
    # Strategy 3: Filter
    result = aggregator.aggregate(
        items,
        strategy="filter",
        condition=lambda x: x.get("passed", False)
    )
    print(f"\nFilter strategy:")
    print(f"  Success: {result.success}")
    print(f"  Filtered count: {len(result.result)}")
    
    # Strategy 4: Custom (via aggregate method)
    code = """
def aggregate(items):
    return {
        "count": len(items),
        "avg_score": sum(item["score"] for item in items) / len(items)
    }
"""
    result = aggregator.aggregate(items, strategy="custom", code=code, language="python")
    print(f"\nCustom strategy:")
    print(f"  Success: {result.success}")
    print(f"  Count: {result.result['count']}")
    print(f"  Avg score: {result.result['avg_score']:.2f}")
    
    # Strategy 5: Unsupported (error handling)
    result = aggregator.aggregate(items, strategy="invalid")
    print(f"\nInvalid strategy:")
    print(f"  Success: {result.success}")
    print(f"  Error: {result.error}")


def main():
    """Run all demos"""
    print("\n" + "=" * 60)
    print("BATCH AGGREGATOR DEMONSTRATION")
    print("=" * 60)
    
    demo_concat_aggregation()
    demo_stats_aggregation()
    demo_filter_aggregation()
    demo_custom_aggregation()
    demo_aggregate_method()
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
