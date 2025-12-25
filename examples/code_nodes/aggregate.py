"""
Example Python code node for data aggregation

This module demonstrates how to write a Python code node
that can be referenced from a pipeline configuration.
"""

import json
from typing import List, Dict, Any, Optional
from datetime import datetime


def execute(items: List[Dict[str, Any]], strategy: str = "concat") -> Dict[str, Any]:
    """
    Aggregate items using the specified strategy
    
    Args:
        items: List of items to aggregate
        strategy: Aggregation strategy ("concat", "stats", "summary")
    
    Returns:
        Aggregated result with metadata
    
    Raises:
        ValueError: If items is not a list or strategy is invalid
    """
    # Validate inputs
    if not isinstance(items, list):
        raise ValueError('items must be a list')
    
    valid_strategies = ["concat", "stats", "summary"]
    if strategy not in valid_strategies:
        raise ValueError(f'strategy must be one of {valid_strategies}')
    
    # Apply aggregation strategy
    if strategy == "concat":
        result = _aggregate_concat(items)
    elif strategy == "stats":
        result = _aggregate_stats(items)
    else:  # summary
        result = _aggregate_summary(items)
    
    # Add metadata
    result['metadata'] = {
        'strategy': strategy,
        'item_count': len(items),
        'aggregated_at': datetime.utcnow().isoformat(),
        'version': '1.0.0'
    }
    
    return result


def _aggregate_concat(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Concatenate all items into a single structure"""
    return {
        'type': 'concat',
        'items': items,
        'total': len(items)
    }


def _aggregate_stats(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate statistics from items"""
    if not items:
        return {
            'type': 'stats',
            'count': 0,
            'scores': {}
        }
    
    # Extract scores if available
    scores = [item.get('score', 0) for item in items if 'score' in item]
    
    stats = {
        'type': 'stats',
        'count': len(items),
        'scores': {}
    }
    
    if scores:
        stats['scores'] = {
            'min': min(scores),
            'max': max(scores),
            'avg': sum(scores) / len(scores),
            'total': sum(scores)
        }
    
    # Count by category if available
    categories = {}
    for item in items:
        category = item.get('category', 'unknown')
        categories[category] = categories.get(category, 0) + 1
    
    if categories:
        stats['categories'] = categories
    
    return stats


def _aggregate_summary(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Create a summary of items"""
    if not items:
        return {
            'type': 'summary',
            'summary': 'No items to summarize'
        }
    
    # Extract key information
    ids = [item.get('id') for item in items if 'id' in item]
    scores = [item.get('score') for item in items if 'score' in item]
    
    summary_parts = []
    
    if ids:
        summary_parts.append(f"Processed {len(ids)} items")
    
    if scores:
        avg_score = sum(scores) / len(scores)
        summary_parts.append(f"Average score: {avg_score:.2f}")
        summary_parts.append(f"Score range: {min(scores):.2f} - {max(scores):.2f}")
    
    return {
        'type': 'summary',
        'summary': '. '.join(summary_parts) if summary_parts else 'No data available',
        'item_ids': ids[:10],  # First 10 IDs
        'total_items': len(items)
    }


if __name__ == '__main__':
    # Test the aggregation function
    test_items = [
        {'id': 1, 'score': 85, 'category': 'high'},
        {'id': 2, 'score': 45, 'category': 'low'},
        {'id': 3, 'score': 92, 'category': 'high'},
        {'id': 4, 'score': 67, 'category': 'medium'}
    ]
    
    print("Testing concat strategy:")
    result = execute(test_items, "concat")
    print(json.dumps(result, indent=2))
    
    print("\nTesting stats strategy:")
    result = execute(test_items, "stats")
    print(json.dumps(result, indent=2))
    
    print("\nTesting summary strategy:")
    result = execute(test_items, "summary")
    print(json.dumps(result, indent=2))
