# Code Node Configuration Format - Design Summary

## Overview

This document summarizes the Code Node configuration format design completed for Task 18 of the Project Production Readiness specification.

## Deliverables

### 1. Configuration Documentation

**File**: `docs/reference/code-node-config-guide.md`

Complete configuration guide covering:
- Basic and advanced configuration structures
- Field definitions and requirements
- Language-specific requirements (JavaScript and Python)
- Input mapping and data flow
- Timeout and error handling
- Environment variables
- Complete working examples
- Best practices and migration guide

### 2. JSON Schema

**File**: `config/schemas/code_node.schema.json`

JSON Schema for validation including:
- Required and optional field definitions
- Field type constraints and patterns
- Language-specific requirements
- Validation rules (e.g., either `code` or `code_file` required)
- Example configurations
- Detailed descriptions for all fields

### 3. Quick Reference Guide

**File**: `docs/reference/code-node-quick-reference.md`

Quick reference guide with:
- Minimal configuration examples
- Field reference table
- Language requirements summary
- Common patterns (filtering, transformation, aggregation, validation)
- Error handling examples
- Best practices checklist
- Common validation errors and fixes

### 4. Example Code Nodes

**Files**:
- `examples/code_nodes/transform.js` - JavaScript transformation example
- `examples/code_nodes/aggregate.py` - Python aggregation example
- `examples/code_nodes/README.md` - Examples documentation

Demonstrates:
- External file reference pattern
- Input validation
- Error handling
- Documentation standards
- Testing approach

### 5. Example Pipeline

**File**: `examples/pipelines/code_node_demo.yaml`

Complete pipeline demonstrating:
- Inline code (Python and JavaScript)
- External file references
- Input mapping from various sources
- Mixing code nodes with agent steps
- Optional vs required steps
- Timeout configuration
- Environment variables

### 6. Documentation Integration

**Updated**: `docs/README.md`

Added code node documentation to:
- Pipeline-related documentation section
- Quick find section for easy navigation

## Configuration Format Summary

### Required Fields

```yaml
id: string              # Unique step identifier
type: "code_node"       # Step type
language: string        # "javascript" or "python"
output_key: string      # Output storage key
```

### Code Source (One Required)

```yaml
code: string           # Inline code (multiline)
# OR
code_file: string      # External file path
```

### Optional Fields

```yaml
input_mapping: dict    # Parameter to source mapping
timeout: integer       # Seconds (default: 30)
description: string    # Human-readable description
required: boolean      # Halt on failure (default: true)
env_vars: dict        # Environment variables
```

## Language Requirements

### JavaScript
- **Runtime**: Node.js
- **Export**: `module.exports = function`
- **Input**: Single object parameter
- **Output**: Value or Promise

### Python
- **Runtime**: Python 3.x
- **Function**: `def execute(...)`
- **Input**: Keyword arguments
- **Output**: JSON-serializable value

## Key Design Decisions

### 1. Dual Code Source Options

**Decision**: Support both inline code and external file references

**Rationale**:
- Inline code: Quick prototyping, simple transformations
- External files: Complex logic, reusability, version control

**Validation**: Exactly one must be specified (enforced by schema)

### 2. Language-Specific Conventions

**Decision**: Use standard conventions for each language

**Rationale**:
- JavaScript: `module.exports` is Node.js standard
- Python: `execute` function is clear and conventional
- Reduces learning curve for developers

### 3. Timeout Control

**Decision**: Default 30 seconds, configurable per node

**Rationale**:
- Prevents hanging pipelines
- Allows flexibility for long-running operations
- Reasonable default for most transformations

### 4. Optional Steps

**Decision**: Support `required: false` for non-critical steps

**Rationale**:
- Enables graceful degradation
- Useful for enrichment/validation steps
- Maintains pipeline flow even with failures

### 5. Environment Variables

**Decision**: Support per-node environment variables

**Rationale**:
- Enables API key injection
- Supports configuration without code changes
- Maintains security best practices

## Validation Rules

The configuration format includes comprehensive validation:

1. **Required Fields**: `id`, `type`, `language`, `output_key`
2. **Code Source**: Either `code` or `code_file` (not both)
3. **Language**: Must be `"javascript"` or `"python"`
4. **ID Format**: Valid identifier (alphanumeric + underscore)
5. **Timeout**: Positive integer (1-3600 seconds)
6. **Input Mapping**: All sources must exist in pipeline

## Error Handling

The design includes comprehensive error handling:

1. **Syntax Errors**: Captured with line numbers
2. **Runtime Errors**: Full stack trace provided
3. **Timeout Errors**: Execution time reported
4. **Output Errors**: JSON serialization failures (Python)

Error response format:
```json
{
  "success": false,
  "error": "Error message",
  "error_type": "SyntaxError|RuntimeError|TimeoutError|OutputError",
  "stderr": "Standard error output",
  "execution_time": 1.23,
  "stack_trace": "Full stack trace..."
}
```

## Integration Points

### Pipeline Configuration

Code nodes integrate seamlessly with existing pipeline configuration:
- Same `input_mapping` format as agent steps
- Same `output_key` mechanism for data flow
- Compatible with dependency analysis
- Works with concurrent execution

### Data Flow

Code nodes participate in pipeline data flow:
- Can reference pipeline inputs
- Can reference previous step outputs
- Output becomes available to subsequent steps
- Supports complex data transformations

## Use Cases

### 1. Data Preprocessing
Clean and normalize data before agent processing

### 2. Data Transformation
Transform agent outputs into required formats

### 3. Aggregation
Combine multiple results into summaries

### 4. Validation
Validate data structure and content

### 5. Enrichment
Add metadata or external data

### 6. Filtering
Remove unwanted items based on criteria

## Testing Strategy

### Unit Testing
- Test code node parsing and validation
- Test input mapping resolution
- Test timeout enforcement
- Test error handling

### Integration Testing
- Test code execution (JavaScript and Python)
- Test data flow through pipelines
- Test error propagation
- Test with real LLM agents

### Property-Based Testing
- Property 5: Configuration parsing correctness
- Property 6: JavaScript execution correctness
- Property 7: Python execution correctness
- Property 8-11: Input/output/timeout/error handling

## Security Considerations

### Risks
- Arbitrary code execution
- File system access
- Network access
- Resource consumption

### Mitigations
1. **Timeout Control**: Forced termination
2. **Environment Isolation**: Separate process execution
3. **Input Validation**: Strict schema validation
4. **Code Review**: Production code must be reviewed
5. **Resource Limits**: Future: CPU/memory limits

## Future Enhancements

### Short Term
1. Resource limits (CPU, memory)
2. Sandboxed execution environment
3. More language support (Ruby, Go)
4. Code caching for performance

### Long Term
1. Visual code editor in UI
2. Code versioning and rollback
3. Shared code library
4. Performance profiling

## Requirements Validation

This design satisfies the following requirements:

### Requirement 3.1
✅ "WHEN defining Pipeline steps THEN the System SHALL support defining code node (Code Node) type steps"

- Complete YAML configuration format defined
- JSON schema for validation
- Documentation and examples provided

### Requirement 10.1
✅ "WHEN defining code nodes THEN the System SHALL support inline code and external file references"

- Both `code` and `code_file` fields supported
- Validation ensures exactly one is specified
- Examples demonstrate both approaches

## Conclusion

The Code Node configuration format design is complete and ready for implementation. All deliverables have been created:

1. ✅ Comprehensive configuration guide
2. ✅ JSON schema for validation
3. ✅ Quick reference guide
4. ✅ Working examples (JavaScript and Python)
5. ✅ Example pipeline
6. ✅ Documentation integration

The design provides a flexible, secure, and developer-friendly way to integrate custom code into pipelines while maintaining consistency with existing pipeline configuration patterns.

## Next Steps

1. Implement `CodeNodeConfig` data model in `src/models.py`
2. Update pipeline configuration parser to support code nodes
3. Implement `CodeExecutor` class for JavaScript and Python execution
4. Add validation logic to pipeline validator
5. Write unit tests and property-based tests
6. Update pipeline runner to execute code nodes

---

**Task Status**: ✅ Complete
**Requirements Covered**: 3.1, 10.1
**Date**: 2025-12-15
