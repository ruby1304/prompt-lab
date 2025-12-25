# Batch Processing Configuration Guide

## Overview

This guide describes the configuration format for batch processing in Prompt Lab pipelines. Batch processing allows you to:

- Process multiple test cases in parallel
- Collect outputs from multiple executions
- Aggregate results using various strategies
- Pass aggregated results to subsequent pipeline steps

Batch processing is essential for scenarios like:
- Running an agent on multiple inputs and summarizing results
- Collecting feedback from multiple evaluations
- Aggregating statistics across test cases
- Filtering and transforming batch results

## Table of Contents

1. [Batch Step Configuration](#batch-step-configuration)
2. [Aggregation Strategies](#aggregation-strategies)
3. [Custom Aggregation Code](#custom-aggregation-code)
4. [Complete Examples](#complete-examples)
5. [Best Practices](#best-practices)

---

## Batch Step Configuration

### Basic Batch Step

A batch step processes multiple inputs and collects their outputs:

```yaml
steps:
  - id: "process_batch"
    type: "agent_flow"
    agent: "text_analyzer"
    flow: "analyze_v1"
    batch_mode: true          # Enable batch processing
    batch_size: 10            # Process 10 items per batch (optional)
    input_mapping:
      text: "input_texts"     # Source of batch items
    output_key: "batch_results"
    description: "Process multiple texts in batch"
    required: true
```

### Batch Step Fields

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `batch_mode` | boolean | Yes | `false` | Enable batch processing for this step |
| `batch_size` | integer | No | `10` | Number of items to process per batch |
| `input_mapping` | object | Yes | - | Maps input parameters to data sources |
| `output_key` | string | Yes | - | Key for storing batch results |
| `concurrent` | boolean | No | `true` | Process batch items concurrently |
| `max_workers` | integer | No | `4` | Maximum concurrent workers |
| `timeout` | integer | No | `300` | Timeout per batch item (seconds) |
| `required` | boolean | No | `true` | Whether batch must succeed |

### Batch Input Format

The input data for a batch step should be a list of items:

```json
{
  "input_texts": [
    "First text to analyze",
    "Second text to analyze",
    "Third text to analyze"
  ]
}
```

Or a list of objects:

```json
{
  "input_items": [
    {"id": "1", "text": "First text", "metadata": {}},
    {"id": "2", "text": "Second text", "metadata": {}},
    {"id": "3", "text": "Third text", "metadata": {}}
  ]
}
```

### Batch Output Format

The output of a batch step is a list of results:

```json
{
  "batch_results": [
    {"input": "First text", "output": "Analysis result 1", "success": true},
    {"input": "Second text", "output": "Analysis result 2", "success": true},
    {"input": "Third text", "output": "Analysis result 3", "success": true}
  ]
}
```

---

## Aggregation Strategies

After collecting batch results, you can aggregate them using various strategies.

### Aggregation Step Configuration

```yaml
steps:
  - id: "aggregate_results"
    type: "batch_aggregator"
    aggregation_strategy: "concat"  # Strategy type
    input_mapping:
      items: "batch_results"        # Source of items to aggregate
    output_key: "aggregated_result"
    description: "Aggregate batch results"
    required: true
```

### Built-in Aggregation Strategies

#### 1. Concat Strategy

Concatenates all outputs into a single string.

```yaml
- id: "concat_results"
  type: "batch_aggregator"
  aggregation_strategy: "concat"
  separator: "\n---\n"              # Optional separator (default: "\n")
  input_mapping:
    items: "batch_results"
  output_key: "concatenated_text"
```

**Output Example:**
```json
{
  "concatenated_text": "Result 1\n---\nResult 2\n---\nResult 3"
}
```

#### 2. Stats Strategy

Computes statistics across batch results.

```yaml
- id: "compute_stats"
  type: "batch_aggregator"
  aggregation_strategy: "stats"
  fields:                           # Fields to compute stats for
    - "score"
    - "confidence"
  input_mapping:
    items: "batch_results"
  output_key: "statistics"
```

**Output Example:**
```json
{
  "statistics": {
    "count": 100,
    "score": {
      "min": 0.2,
      "max": 0.95,
      "mean": 0.67,
      "median": 0.70,
      "std": 0.15
    },
    "confidence": {
      "min": 0.5,
      "max": 1.0,
      "mean": 0.82,
      "median": 0.85,
      "std": 0.12
    }
  }
}
```

#### 3. Filter Strategy

Filters batch results based on a condition.

```yaml
- id: "filter_results"
  type: "batch_aggregator"
  aggregation_strategy: "filter"
  condition: "item.score > 0.7"    # Filter condition
  input_mapping:
    items: "batch_results"
  output_key: "filtered_results"
```

**Supported Conditions:**
- Comparison: `item.score > 0.7`, `item.status == "success"`
- Logical: `item.score > 0.5 and item.confidence > 0.8`
- Membership: `item.category in ["A", "B"]`
- Existence: `item.error is None`, `item.result is not None`

**Output Example:**
```json
{
  "filtered_results": [
    {"score": 0.85, "text": "High quality result"},
    {"score": 0.92, "text": "Another high quality result"}
  ]
}
```

#### 4. Group Strategy

Groups batch results by a field value.

```yaml
- id: "group_results"
  type: "batch_aggregator"
  aggregation_strategy: "group"
  group_by: "category"              # Field to group by
  input_mapping:
    items: "batch_results"
  output_key: "grouped_results"
```

**Output Example:**
```json
{
  "grouped_results": {
    "category_a": [
      {"id": "1", "category": "category_a", "value": 10},
      {"id": "3", "category": "category_a", "value": 15}
    ],
    "category_b": [
      {"id": "2", "category": "category_b", "value": 20}
    ]
  }
}
```

#### 5. Summary Strategy

Creates a summary of batch results.

```yaml
- id: "summarize_results"
  type: "batch_aggregator"
  aggregation_strategy: "summary"
  summary_fields:                   # Fields to include in summary
    - "total_count"
    - "success_count"
    - "failure_count"
    - "average_score"
  input_mapping:
    items: "batch_results"
  output_key: "summary"
```

**Output Example:**
```json
{
  "summary": {
    "total_count": 100,
    "success_count": 95,
    "failure_count": 5,
    "average_score": 0.82,
    "success_rate": 0.95
  }
}
```

---

## Custom Aggregation Code

For complex aggregation logic, use custom code (Python or JavaScript).

### Python Custom Aggregation

```yaml
- id: "custom_aggregate"
  type: "batch_aggregator"
  aggregation_strategy: "custom"
  language: "python"                # Language for custom code
  code: |
    def aggregate(items):
      """
      Custom aggregation function
      
      Args:
        items: List of batch result items
        
      Returns:
        Aggregated result (any JSON-serializable type)
      """
      # Filter successful results
      successful = [item for item in items if item.get('success', False)]
      
      # Extract scores
      scores = [item.get('score', 0) for item in successful]
      
      # Compute custom metrics
      return {
        'total_items': len(items),
        'successful_items': len(successful),
        'failed_items': len(items) - len(successful),
        'average_score': sum(scores) / len(scores) if scores else 0,
        'high_score_count': len([s for s in scores if s > 0.8]),
        'low_score_count': len([s for s in scores if s < 0.5]),
        'score_distribution': {
          'high': len([s for s in scores if s > 0.8]),
          'medium': len([s for s in scores if 0.5 <= s <= 0.8]),
          'low': len([s for s in scores if s < 0.5])
        }
      }
  input_mapping:
    items: "batch_results"
  output_key: "custom_aggregation"
  timeout: 60
```

### JavaScript Custom Aggregation

```yaml
- id: "custom_aggregate_js"
  type: "batch_aggregator"
  aggregation_strategy: "custom"
  language: "javascript"
  code: |
    function aggregate(items) {
      // Filter and transform results
      const successful = items.filter(item => item.success);
      
      // Group by category
      const byCategory = successful.reduce((acc, item) => {
        const cat = item.category || 'uncategorized';
        if (!acc[cat]) acc[cat] = [];
        acc[cat].push(item);
        return acc;
      }, {});
      
      // Compute statistics per category
      const categoryStats = {};
      for (const [category, categoryItems] of Object.entries(byCategory)) {
        const scores = categoryItems.map(item => item.score || 0);
        categoryStats[category] = {
          count: categoryItems.length,
          avgScore: scores.reduce((a, b) => a + b, 0) / scores.length,
          maxScore: Math.max(...scores),
          minScore: Math.min(...scores)
        };
      }
      
      return {
        totalItems: items.length,
        successfulItems: successful.length,
        categories: Object.keys(byCategory),
        categoryStats: categoryStats
      };
    }
    
    module.exports = aggregate;
  input_mapping:
    items: "batch_results"
  output_key: "category_analysis"
  timeout: 60
```

### External Aggregation File

For reusable aggregation logic, use external files:

```yaml
- id: "aggregate_from_file"
  type: "batch_aggregator"
  aggregation_strategy: "custom"
  language: "python"
  code_file: "aggregators/custom_aggregator.py"
  input_mapping:
    items: "batch_results"
    config: "aggregation_config"
  output_key: "aggregated_data"
  timeout: 120
```

**aggregators/custom_aggregator.py:**
```python
def aggregate(items, config=None):
    """
    Reusable custom aggregation function
    
    Args:
        items: List of batch result items
        config: Optional configuration dict
        
    Returns:
        Aggregated result
    """
    config = config or {}
    threshold = config.get('threshold', 0.5)
    
    # Your custom aggregation logic here
    filtered = [item for item in items if item.get('score', 0) > threshold]
    
    return {
        'filtered_count': len(filtered),
        'threshold_used': threshold,
        'results': filtered
    }
```

### Custom Aggregation Function Signature

**Python:**
```python
def aggregate(items, **kwargs):
    """
    Args:
        items: List[Dict[str, Any]] - Batch result items
        **kwargs: Additional parameters from input_mapping
        
    Returns:
        Dict[str, Any] or List or str - Aggregated result
    """
    pass
```

**JavaScript:**
```javascript
function aggregate(items, additionalParams) {
  /**
   * @param {Array<Object>} items - Batch result items
   * @param {Object} additionalParams - Additional parameters from input_mapping
   * @returns {Object|Array|string} - Aggregated result
   */
}

module.exports = aggregate;
```

---

## Complete Examples

### Example 1: Batch Processing with Concat Aggregation

Process multiple texts and concatenate results:

```yaml
id: "batch_text_analysis"
name: "Batch Text Analysis Pipeline"

inputs:
  - name: "texts"
    desc: "List of texts to analyze"
    required: true

steps:
  # Step 1: Analyze each text
  - id: "analyze_texts"
    type: "agent_flow"
    agent: "text_analyzer"
    flow: "analyze_v1"
    batch_mode: true
    batch_size: 20
    input_mapping:
      text: "texts"
    output_key: "analysis_results"
    
  # Step 2: Concatenate all analyses
  - id: "concat_analyses"
    type: "batch_aggregator"
    aggregation_strategy: "concat"
    separator: "\n\n---\n\n"
    input_mapping:
      items: "analysis_results"
    output_key: "combined_analysis"
    
  # Step 3: Generate summary from concatenated results
  - id: "generate_summary"
    type: "agent_flow"
    agent: "summarizer"
    flow: "summarize_v1"
    input_mapping:
      text: "combined_analysis"
    output_key: "final_summary"

outputs:
  - key: "final_summary"
    label: "Final Summary"
```

### Example 2: Batch Processing with Stats Aggregation

Evaluate multiple responses and compute statistics:

```yaml
id: "batch_evaluation"
name: "Batch Response Evaluation"

inputs:
  - name: "responses"
    desc: "List of responses to evaluate"
    required: true

steps:
  # Step 1: Evaluate each response
  - id: "evaluate_responses"
    type: "agent_flow"
    agent: "evaluator"
    flow: "evaluate_v1"
    batch_mode: true
    batch_size: 50
    concurrent: true
    max_workers: 10
    input_mapping:
      response: "responses"
    output_key: "evaluations"
    
  # Step 2: Compute statistics
  - id: "compute_stats"
    type: "batch_aggregator"
    aggregation_strategy: "stats"
    fields:
      - "score"
      - "confidence"
      - "quality_rating"
    input_mapping:
      items: "evaluations"
    output_key: "evaluation_stats"
    
  # Step 3: Generate report
  - id: "generate_report"
    type: "code_node"
    language: "python"
    code: |
      def execute(stats):
        return {
          'report': f"""
          Evaluation Report
          =================
          Total Responses: {stats['count']}
          
          Score Statistics:
          - Average: {stats['score']['mean']:.2f}
          - Median: {stats['score']['median']:.2f}
          - Range: {stats['score']['min']:.2f} - {stats['score']['max']:.2f}
          
          Quality Rating:
          - Average: {stats['quality_rating']['mean']:.2f}
          - Std Dev: {stats['quality_rating']['std']:.2f}
          """
        }
    input_mapping:
      stats: "evaluation_stats"
    output_key: "evaluation_report"

outputs:
  - key: "evaluation_report"
    label: "Evaluation Report"
  - key: "evaluation_stats"
    label: "Statistics"
```

### Example 3: Multi-Stage Batch Processing

Complex pipeline with multiple batch stages:

```yaml
id: "multi_stage_batch"
name: "Multi-Stage Batch Processing"

inputs:
  - name: "documents"
    desc: "List of documents to process"
    required: true

steps:
  # Stage 1: Extract entities from each document
  - id: "extract_entities"
    type: "agent_flow"
    agent: "entity_extractor"
    flow: "extract_v1"
    batch_mode: true
    batch_size: 10
    input_mapping:
      document: "documents"
    output_key: "entity_results"
    
  # Stage 2: Filter high-confidence entities
  - id: "filter_entities"
    type: "batch_aggregator"
    aggregation_strategy: "filter"
    condition: "item.confidence > 0.8"
    input_mapping:
      items: "entity_results"
    output_key: "high_confidence_entities"
    
  # Stage 3: Group entities by type
  - id: "group_entities"
    type: "batch_aggregator"
    aggregation_strategy: "group"
    group_by: "entity_type"
    input_mapping:
      items: "high_confidence_entities"
    output_key: "grouped_entities"
    
  # Stage 4: Analyze each entity group
  - id: "analyze_groups"
    type: "agent_flow"
    agent: "group_analyzer"
    flow: "analyze_v1"
    batch_mode: true
    input_mapping:
      entity_group: "grouped_entities"
    output_key: "group_analyses"
    
  # Stage 5: Custom aggregation for final report
  - id: "create_final_report"
    type: "batch_aggregator"
    aggregation_strategy: "custom"
    language: "python"
    code: |
      def aggregate(group_analyses):
        report = {
          'total_groups': len(group_analyses),
          'groups': {}
        }
        
        for analysis in group_analyses:
          group_type = analysis.get('entity_type', 'unknown')
          report['groups'][group_type] = {
            'count': analysis.get('entity_count', 0),
            'summary': analysis.get('summary', ''),
            'key_findings': analysis.get('key_findings', [])
          }
        
        return report
    input_mapping:
      group_analyses: "group_analyses"
    output_key: "final_report"

outputs:
  - key: "final_report"
    label: "Entity Analysis Report"
```

### Example 4: Batch with Error Handling

Robust batch processing with error handling:

```yaml
id: "robust_batch_processing"
name: "Robust Batch Processing with Error Handling"

inputs:
  - name: "items"
    desc: "Items to process"
    required: true

steps:
  # Step 1: Process items (some may fail)
  - id: "process_items"
    type: "agent_flow"
    agent: "processor"
    flow: "process_v1"
    batch_mode: true
    batch_size: 10
    required: false              # Don't halt pipeline on failures
    input_mapping:
      item: "items"
    output_key: "processing_results"
    
  # Step 2: Separate successful and failed results
  - id: "separate_results"
    type: "code_node"
    language: "python"
    code: |
      def execute(results):
        successful = []
        failed = []
        
        for result in results:
          if result.get('success', False):
            successful.append(result)
          else:
            failed.append({
              'input': result.get('input'),
              'error': result.get('error', 'Unknown error')
            })
        
        return {
          'successful': successful,
          'failed': failed,
          'success_rate': len(successful) / len(results) if results else 0
        }
    input_mapping:
      results: "processing_results"
    output_key: "separated_results"
    
  # Step 3: Aggregate successful results
  - id: "aggregate_successful"
    type: "batch_aggregator"
    aggregation_strategy: "stats"
    fields: ["score", "quality"]
    input_mapping:
      items: "separated_results.successful"
    output_key: "success_stats"
    
  # Step 4: Generate error report
  - id: "generate_error_report"
    type: "code_node"
    language: "javascript"
    code: |
      function generateErrorReport(separated) {
        const { failed, success_rate } = separated;
        
        return {
          error_report: {
            total_failures: failed.length,
            success_rate: (success_rate * 100).toFixed(2) + '%',
            errors: failed.map(f => ({
              input: f.input,
              error: f.error
            }))
          }
        };
      }
      module.exports = generateErrorReport;
    input_mapping:
      separated: "separated_results"
    output_key: "error_report"

outputs:
  - key: "success_stats"
    label: "Success Statistics"
  - key: "error_report"
    label: "Error Report"
```

---

## Best Practices

### 1. Batch Size Selection

Choose appropriate batch sizes based on:

- **Small batches (5-10)**: For expensive operations (complex LLM calls)
- **Medium batches (10-50)**: For standard processing
- **Large batches (50-100+)**: For lightweight operations

```yaml
# Expensive LLM operation
- id: "complex_analysis"
  batch_mode: true
  batch_size: 5        # Small batch for expensive ops
  
# Lightweight validation
- id: "validate_format"
  batch_mode: true
  batch_size: 100      # Large batch for cheap ops
```

### 2. Concurrent Processing

Enable concurrent processing for independent operations:

```yaml
- id: "parallel_processing"
  batch_mode: true
  concurrent: true
  max_workers: 10      # Adjust based on system resources
```

### 3. Error Handling

Use `required: false` for non-critical batch steps:

```yaml
- id: "optional_enrichment"
  batch_mode: true
  required: false      # Continue pipeline even if this fails
```

### 4. Timeout Configuration

Set appropriate timeouts for batch operations:

```yaml
- id: "batch_with_timeout"
  batch_mode: true
  timeout: 300         # 5 minutes per batch item
```

### 5. Memory Management

For large batches, consider:

- Processing in smaller chunks
- Using streaming aggregation
- Cleaning up intermediate results

```yaml
# Process large dataset in chunks
- id: "chunk_processing"
  batch_mode: true
  batch_size: 20       # Process 20 at a time
  input_mapping:
    items: "large_dataset"
```

### 6. Aggregation Strategy Selection

Choose the right strategy:

- **concat**: For text summarization, report generation
- **stats**: For numerical analysis, performance metrics
- **filter**: For quality control, threshold-based selection
- **group**: For categorization, classification results
- **custom**: For complex business logic

### 7. Testing Batch Pipelines

Test with various batch sizes:

```yaml
# Test with small batch first
default_testset: "batch_test_small.jsonl"  # 10 items

# Then scale up
# default_testset: "batch_test_medium.jsonl"  # 100 items
# default_testset: "batch_test_large.jsonl"   # 1000 items
```

### 8. Monitoring and Logging

Track batch processing metrics:

```yaml
- id: "log_batch_metrics"
  type: "code_node"
  language: "python"
  code: |
    def execute(results):
      import time
      return {
        'metrics': {
          'timestamp': time.time(),
          'total_items': len(results),
          'successful': len([r for r in results if r.get('success')]),
          'failed': len([r for r in results if not r.get('success')]),
          'avg_processing_time': sum(r.get('time', 0) for r in results) / len(results)
        }
      }
  input_mapping:
    results: "batch_results"
  output_key: "batch_metrics"
```

---

## Related Documentation

- [Pipeline Configuration Guide](./pipeline-guide.md)
- [Code Node Configuration](./code-node-config-guide.md)
- [Concurrent Execution Guide](./concurrent-executor-guide.md)
- [Testing Strategy](./evaluation-rules.md)

---

## Validation and Schema

All batch processing configurations are validated against the schema defined in `src/models.py`. Common validation errors:

1. **Missing required fields**: `batch_mode` must be `true` for batch steps
2. **Invalid aggregation strategy**: Must be one of: `concat`, `stats`, `filter`, `group`, `summary`, `custom`
3. **Custom aggregation without code**: `custom` strategy requires `code` or `code_file`
4. **Invalid batch size**: Must be a positive integer
5. **Invalid timeout**: Must be a positive integer (seconds)

---

## Troubleshooting

### Issue: Batch processing is slow

**Solutions:**
- Enable concurrent processing: `concurrent: true`
- Increase `max_workers`
- Reduce `batch_size` for expensive operations
- Check for bottlenecks in aggregation code

### Issue: Out of memory errors

**Solutions:**
- Reduce `batch_size`
- Process in multiple stages
- Use streaming aggregation
- Clean up intermediate results

### Issue: Aggregation fails

**Solutions:**
- Validate input data format
- Check custom aggregation code for errors
- Add error handling in custom code
- Use `required: false` for non-critical aggregations

### Issue: Inconsistent results

**Solutions:**
- Ensure deterministic aggregation logic
- Check for race conditions in concurrent processing
- Validate input data consistency
- Add logging to track data flow

---

## Version History

- **v1.0** (2024-12): Initial batch processing configuration format
- Requirements: 4.1, 4.5
- Design: Phase 5 - Batch Aggregator

