# Batch Processing Quick Reference

Quick reference for batch processing and aggregation in Prompt Lab pipelines.

## Batch Step Configuration

### Minimal Batch Step

```yaml
- id: "process_batch"
  type: "agent_flow"
  agent: "my_agent"
  flow: "my_flow"
  batch_mode: true
  input_mapping:
    text: "input_texts"
  output_key: "batch_results"
```

### Full Batch Step Options

```yaml
- id: "process_batch"
  type: "agent_flow"
  agent: "my_agent"
  flow: "my_flow"
  batch_mode: true              # Required: Enable batch mode
  batch_size: 20                # Optional: Items per batch (default: 10)
  concurrent: true              # Optional: Enable concurrency (default: true)
  max_workers: 5                # Optional: Max concurrent workers (default: 4)
  timeout: 120                  # Optional: Timeout per item in seconds
  required: true                # Optional: Must succeed (default: true)
  input_mapping:
    text: "input_texts"
  output_key: "batch_results"
  description: "Process items in batch"
```

## Aggregation Strategies

### 1. Concat - Concatenate Results

```yaml
- id: "concat_results"
  type: "batch_aggregator"
  aggregation_strategy: "concat"
  separator: "\n---\n"          # Optional: Default is "\n"
  input_mapping:
    items: "batch_results"
  output_key: "concatenated"
```

**Output:** Single string with all results concatenated

### 2. Stats - Compute Statistics

```yaml
- id: "compute_stats"
  type: "batch_aggregator"
  aggregation_strategy: "stats"
  fields:                       # Required: Fields to analyze
    - "score"
    - "confidence"
  input_mapping:
    items: "batch_results"
  output_key: "statistics"
```

**Output:** Statistics object with min, max, mean, median, std for each field

### 3. Filter - Filter Results

```yaml
- id: "filter_results"
  type: "batch_aggregator"
  aggregation_strategy: "filter"
  condition: "item.score > 0.7" # Required: Filter condition
  input_mapping:
    items: "batch_results"
  output_key: "filtered"
```

**Output:** Array of items matching the condition

### 4. Group - Group by Field

```yaml
- id: "group_results"
  type: "batch_aggregator"
  aggregation_strategy: "group"
  group_by: "category"          # Required: Field to group by
  input_mapping:
    items: "batch_results"
  output_key: "grouped"
```

**Output:** Object with groups as keys, arrays of items as values

### 5. Summary - Create Summary

```yaml
- id: "summarize"
  type: "batch_aggregator"
  aggregation_strategy: "summary"
  summary_fields:               # Required: Fields to include
    - "total_count"
    - "success_count"
    - "failure_count"
    - "average_score"
  input_mapping:
    items: "batch_results"
  output_key: "summary"
```

**Output:** Summary object with requested fields

### 6. Custom - Custom Code

#### Python Custom Aggregation

```yaml
- id: "custom_agg"
  type: "batch_aggregator"
  aggregation_strategy: "custom"
  language: "python"
  code: |
    def aggregate(items):
      # Your custom logic here
      return {
        'count': len(items),
        'processed': [item['result'] for item in items]
      }
  input_mapping:
    items: "batch_results"
  output_key: "custom_result"
  timeout: 60
```

#### JavaScript Custom Aggregation

```yaml
- id: "custom_agg"
  type: "batch_aggregator"
  aggregation_strategy: "custom"
  language: "javascript"
  code: |
    function aggregate(items) {
      // Your custom logic here
      return {
        count: items.length,
        processed: items.map(item => item.result)
      };
    }
    module.exports = aggregate;
  input_mapping:
    items: "batch_results"
  output_key: "custom_result"
  timeout: 60
```

#### External File

```yaml
- id: "custom_agg"
  type: "batch_aggregator"
  aggregation_strategy: "custom"
  language: "python"
  code_file: "aggregators/my_aggregator.py"
  input_mapping:
    items: "batch_results"
    config: "agg_config"
  output_key: "custom_result"
```

## Common Patterns

### Pattern 1: Batch → Aggregate → Agent

```yaml
steps:
  # Step 1: Process batch
  - id: "process_items"
    type: "agent_flow"
    agent: "processor"
    flow: "process_v1"
    batch_mode: true
    input_mapping:
      item: "input_items"
    output_key: "processed_items"
  
  # Step 2: Aggregate results
  - id: "aggregate"
    type: "batch_aggregator"
    aggregation_strategy: "concat"
    input_mapping:
      items: "processed_items"
    output_key: "aggregated"
  
  # Step 3: Summarize with agent
  - id: "summarize"
    type: "agent_flow"
    agent: "summarizer"
    flow: "summarize_v1"
    input_mapping:
      text: "aggregated"
    output_key: "summary"
```

### Pattern 2: Batch → Filter → Stats

```yaml
steps:
  # Step 1: Process batch
  - id: "evaluate"
    type: "agent_flow"
    agent: "evaluator"
    flow: "eval_v1"
    batch_mode: true
    input_mapping:
      text: "texts"
    output_key: "evaluations"
  
  # Step 2: Filter high quality
  - id: "filter_quality"
    type: "batch_aggregator"
    aggregation_strategy: "filter"
    condition: "item.quality_score > 0.8"
    input_mapping:
      items: "evaluations"
    output_key: "high_quality"
  
  # Step 3: Compute statistics
  - id: "compute_stats"
    type: "batch_aggregator"
    aggregation_strategy: "stats"
    fields: ["quality_score", "relevance"]
    input_mapping:
      items: "high_quality"
    output_key: "quality_stats"
```

### Pattern 3: Batch → Group → Batch Each Group

```yaml
steps:
  # Step 1: Classify items
  - id: "classify"
    type: "agent_flow"
    agent: "classifier"
    flow: "classify_v1"
    batch_mode: true
    input_mapping:
      item: "items"
    output_key: "classified"
  
  # Step 2: Group by category
  - id: "group_by_category"
    type: "batch_aggregator"
    aggregation_strategy: "group"
    group_by: "category"
    input_mapping:
      items: "classified"
    output_key: "grouped"
  
  # Step 3: Analyze each group
  - id: "analyze_groups"
    type: "agent_flow"
    agent: "analyzer"
    flow: "analyze_v1"
    batch_mode: true
    input_mapping:
      group: "grouped"
    output_key: "group_analyses"
```

## Filter Condition Syntax

### Comparison Operators

```yaml
condition: "item.score > 0.7"           # Greater than
condition: "item.score >= 0.7"          # Greater than or equal
condition: "item.score < 0.3"           # Less than
condition: "item.score <= 0.3"          # Less than or equal
condition: "item.status == 'success'"   # Equal
condition: "item.status != 'failed'"    # Not equal
```

### Logical Operators

```yaml
condition: "item.score > 0.7 and item.confidence > 0.8"
condition: "item.status == 'success' or item.retry_count < 3"
condition: "not item.error"
```

### Membership

```yaml
condition: "item.category in ['A', 'B', 'C']"
condition: "item.tag not in ['spam', 'invalid']"
```

### Existence

```yaml
condition: "item.error is None"
condition: "item.result is not None"
```

## Performance Tips

### Batch Size Guidelines

| Operation Type | Recommended Batch Size |
|---------------|------------------------|
| Expensive LLM calls | 5-10 |
| Standard processing | 10-50 |
| Lightweight operations | 50-100+ |

### Concurrency Settings

```yaml
# For I/O-bound operations (API calls)
concurrent: true
max_workers: 10

# For CPU-bound operations
concurrent: true
max_workers: 4  # Match CPU cores

# For rate-limited APIs
concurrent: true
max_workers: 2
batch_size: 5
```

### Timeout Configuration

```yaml
# Quick operations
timeout: 30

# Standard LLM calls
timeout: 60

# Complex processing
timeout: 120

# Long-running analysis
timeout: 300
```

## Error Handling

### Optional Batch Steps

```yaml
- id: "optional_enrichment"
  type: "agent_flow"
  agent: "enricher"
  flow: "enrich_v1"
  batch_mode: true
  required: false  # Continue even if this fails
  input_mapping:
    item: "items"
  output_key: "enriched"
```

### Handling Partial Failures

```yaml
steps:
  # Step 1: Process (some may fail)
  - id: "process"
    type: "agent_flow"
    agent: "processor"
    flow: "process_v1"
    batch_mode: true
    required: false
    input_mapping:
      item: "items"
    output_key: "results"
  
  # Step 2: Separate success/failure
  - id: "separate"
    type: "code_node"
    language: "python"
    code: |
      def execute(results):
        successful = [r for r in results if r.get('success')]
        failed = [r for r in results if not r.get('success')]
        return {
          'successful': successful,
          'failed': failed,
          'success_rate': len(successful) / len(results)
        }
    input_mapping:
      results: "results"
    output_key: "separated"
  
  # Step 3: Process only successful
  - id: "aggregate_success"
    type: "batch_aggregator"
    aggregation_strategy: "stats"
    fields: ["score"]
    input_mapping:
      items: "separated.successful"
    output_key: "success_stats"
```

## Validation

### Required Fields

- `id`: Unique step identifier
- `type`: Must be "batch_aggregator" for aggregation steps
- `aggregation_strategy`: One of: concat, stats, filter, group, summary, custom
- `input_mapping`: Must include source of items
- `output_key`: Where to store results

### Strategy-Specific Requirements

| Strategy | Required Fields |
|----------|----------------|
| concat | separator (optional) |
| stats | fields (array) |
| filter | condition (string) |
| group | group_by (string) |
| summary | summary_fields (array) |
| custom | language, code or code_file |

## Examples

See complete examples in:
- `examples/pipelines/batch_processing_demo.yaml`
- `docs/reference/batch-processing-config-guide.md`

## Related Documentation

- [Batch Processing Configuration Guide](./batch-processing-config-guide.md)
- [Pipeline Configuration Guide](./pipeline-guide.md)
- [Code Node Configuration](./code-node-config-guide.md)
- [Concurrent Execution Guide](./concurrent-executor-guide.md)

## Requirements

- Requirements: 4.1, 4.5
- Design: Phase 5 - Batch Aggregator
- Schema: `config/schemas/batch_processing.schema.json`
