"""
Unit tests for BatchAggregator

Tests the basic aggregation functionality including:
- Concat aggregation
- Stats aggregation
- Filter aggregation
- Error handling
- Batch processing
"""

import pytest
from src.batch_aggregator import BatchAggregator, AggregationResult, BatchProcessor, BatchProcessingResult


class TestBatchAggregatorConcat:
    """Tests for concat aggregation strategy"""
    
    def test_concat_simple_strings(self):
        """Test concatenating simple strings"""
        aggregator = BatchAggregator()
        items = ["hello", "world", "test"]
        
        result = aggregator.aggregate_concat(items, separator=" ")
        
        assert result == "hello world test"
    
    def test_concat_with_newline_separator(self):
        """Test concatenating with default newline separator"""
        aggregator = BatchAggregator()
        items = ["line1", "line2", "line3"]
        
        result = aggregator.aggregate_concat(items)
        
        assert result == "line1\nline2\nline3"
    
    def test_concat_dict_items_with_text_field(self):
        """Test concatenating dict items with 'text' field"""
        aggregator = BatchAggregator()
        items = [
            {"text": "first", "other": "data"},
            {"text": "second", "other": "data"},
            {"text": "third", "other": "data"}
        ]
        
        result = aggregator.aggregate_concat(items, separator=", ")
        
        assert result == "first, second, third"
    
    def test_concat_dict_items_with_output_field(self):
        """Test concatenating dict items with 'output' field"""
        aggregator = BatchAggregator()
        items = [
            {"output": "result1"},
            {"output": "result2"},
            {"output": "result3"}
        ]
        
        result = aggregator.aggregate_concat(items, separator=" | ")
        
        assert result == "result1 | result2 | result3"
    
    def test_concat_dict_items_with_result_field(self):
        """Test concatenating dict items with 'result' field"""
        aggregator = BatchAggregator()
        items = [
            {"result": "A"},
            {"result": "B"},
            {"result": "C"}
        ]
        
        result = aggregator.aggregate_concat(items, separator="-")
        
        assert result == "A-B-C"
    
    def test_concat_mixed_types(self):
        """Test concatenating mixed types"""
        aggregator = BatchAggregator()
        items = ["string", 123, {"text": "dict"}, 45.6]
        
        result = aggregator.aggregate_concat(items, separator=", ")
        
        assert "string" in result
        assert "123" in result
        assert "dict" in result
        assert "45.6" in result
    
    def test_concat_empty_list(self):
        """Test concatenating empty list"""
        aggregator = BatchAggregator()
        items = []
        
        result = aggregator.aggregate_concat(items)
        
        assert result == ""


class TestBatchAggregatorStats:
    """Tests for stats aggregation strategy"""
    
    def test_stats_single_field(self):
        """Test calculating statistics for a single field"""
        aggregator = BatchAggregator()
        items = [
            {"score": 85},
            {"score": 90},
            {"score": 78},
            {"score": 92}
        ]
        
        result = aggregator.aggregate_stats(items, fields=["score"])
        
        assert result["total_items"] == 4
        assert result["fields"]["score"]["count"] == 4
        assert result["fields"]["score"]["sum"] == 345
        assert result["fields"]["score"]["mean"] == 86.25
        assert result["fields"]["score"]["min"] == 78
        assert result["fields"]["score"]["max"] == 92
        assert "median" in result["fields"]["score"]
        assert "stdev" in result["fields"]["score"]
    
    def test_stats_multiple_fields(self):
        """Test calculating statistics for multiple fields"""
        aggregator = BatchAggregator()
        items = [
            {"score": 85, "time": 1.2},
            {"score": 90, "time": 1.5},
            {"score": 78, "time": 1.1}
        ]
        
        result = aggregator.aggregate_stats(items, fields=["score", "time"])
        
        assert result["total_items"] == 3
        assert "score" in result["fields"]
        assert "time" in result["fields"]
        assert result["fields"]["score"]["count"] == 3
        assert result["fields"]["time"]["count"] == 3
        assert result["fields"]["score"]["mean"] == pytest.approx(84.33, rel=0.01)
        assert result["fields"]["time"]["mean"] == pytest.approx(1.27, rel=0.01)
    
    def test_stats_missing_field(self):
        """Test statistics when field is missing from some items"""
        aggregator = BatchAggregator()
        items = [
            {"score": 85, "time": 1.2},
            {"score": 90},  # missing 'time'
            {"time": 1.5}   # missing 'score'
        ]
        
        result = aggregator.aggregate_stats(items, fields=["score", "time"])
        
        assert result["fields"]["score"]["count"] == 2
        assert result["fields"]["time"]["count"] == 2
    
    def test_stats_non_numeric_values(self):
        """Test statistics with non-numeric values"""
        aggregator = BatchAggregator()
        items = [
            {"score": 85, "name": "test1"},
            {"score": 90, "name": "test2"},
            {"score": "invalid", "name": "test3"}
        ]
        
        result = aggregator.aggregate_stats(items, fields=["score", "name"])
        
        # Only numeric scores should be counted
        assert result["fields"]["score"]["count"] == 2
        # Name field should have error
        assert "error" in result["fields"]["name"]
    
    def test_stats_no_fields_specified(self):
        """Test statistics with no fields specified"""
        aggregator = BatchAggregator()
        items = [{"score": 85}, {"score": 90}]
        
        with pytest.raises(ValueError, match="No fields specified"):
            aggregator.aggregate_stats(items, fields=[])
    
    def test_stats_single_value(self):
        """Test statistics with single value (no stdev)"""
        aggregator = BatchAggregator()
        items = [{"score": 85}]
        
        result = aggregator.aggregate_stats(items, fields=["score"])
        
        assert result["fields"]["score"]["count"] == 1
        assert result["fields"]["score"]["mean"] == 85
        # Should not have stdev with single value
        assert "stdev" not in result["fields"]["score"]


class TestBatchAggregatorFilter:
    """Tests for filter aggregation strategy"""
    
    def test_filter_with_simple_condition(self):
        """Test filtering with a simple condition"""
        aggregator = BatchAggregator()
        items = [
            {"score": 85, "passed": True},
            {"score": 45, "passed": False},
            {"score": 90, "passed": True},
            {"score": 60, "passed": False}
        ]
        
        result = aggregator.aggregate_filter(
            items,
            condition=lambda x: x.get("passed", False)
        )
        
        assert len(result) == 2
        assert all(item["passed"] for item in result)
    
    def test_filter_with_numeric_condition(self):
        """Test filtering with numeric condition"""
        aggregator = BatchAggregator()
        items = [
            {"score": 85},
            {"score": 45},
            {"score": 90},
            {"score": 60}
        ]
        
        result = aggregator.aggregate_filter(
            items,
            condition=lambda x: x.get("score", 0) >= 70
        )
        
        assert len(result) == 2
        assert all(item["score"] >= 70 for item in result)
    
    def test_filter_no_matches(self):
        """Test filtering when no items match"""
        aggregator = BatchAggregator()
        items = [
            {"score": 45},
            {"score": 50},
            {"score": 60}
        ]
        
        result = aggregator.aggregate_filter(
            items,
            condition=lambda x: x.get("score", 0) >= 100
        )
        
        assert len(result) == 0
    
    def test_filter_all_match(self):
        """Test filtering when all items match"""
        aggregator = BatchAggregator()
        items = [
            {"score": 85},
            {"score": 90},
            {"score": 95}
        ]
        
        result = aggregator.aggregate_filter(
            items,
            condition=lambda x: x.get("score", 0) >= 70
        )
        
        assert len(result) == 3
    
    def test_filter_no_condition(self):
        """Test filtering with no condition returns all items"""
        aggregator = BatchAggregator()
        items = [{"a": 1}, {"b": 2}, {"c": 3}]
        
        result = aggregator.aggregate_filter(items, condition=None)
        
        assert len(result) == 3
        assert result == items
    
    def test_filter_invalid_condition(self):
        """Test filtering with invalid condition"""
        aggregator = BatchAggregator()
        items = [{"a": 1}]
        
        with pytest.raises(ValueError, match="Condition must be a callable"):
            aggregator.aggregate_filter(items, condition="not a function")


class TestBatchAggregatorAggregate:
    """Tests for the main aggregate method"""
    
    def test_aggregate_concat_strategy(self):
        """Test aggregate method with concat strategy"""
        aggregator = BatchAggregator()
        items = ["a", "b", "c"]
        
        result = aggregator.aggregate(items, strategy="concat", separator=",")
        
        assert result.success
        assert result.result == "a,b,c"
        assert result.strategy == "concat"
        assert result.item_count == 3
    
    def test_aggregate_stats_strategy(self):
        """Test aggregate method with stats strategy"""
        aggregator = BatchAggregator()
        items = [{"score": 85}, {"score": 90}]
        
        result = aggregator.aggregate(items, strategy="stats", fields=["score"])
        
        assert result.success
        assert result.strategy == "stats"
        assert result.item_count == 2
        assert "score" in result.result["fields"]
    
    def test_aggregate_filter_strategy(self):
        """Test aggregate method with filter strategy"""
        aggregator = BatchAggregator()
        items = [{"x": 1}, {"x": 5}, {"x": 10}]
        
        result = aggregator.aggregate(
            items,
            strategy="filter",
            condition=lambda x: x.get("x", 0) > 3
        )
        
        assert result.success
        assert result.strategy == "filter"
        assert len(result.result) == 2
    
    def test_aggregate_empty_items(self):
        """Test aggregate with empty items list"""
        aggregator = BatchAggregator()
        items = []
        
        result = aggregator.aggregate(items, strategy="concat")
        
        assert result.success
        assert result.result is None
        assert result.item_count == 0
    
    def test_aggregate_unsupported_strategy(self):
        """Test aggregate with unsupported strategy"""
        aggregator = BatchAggregator()
        items = [{"a": 1}]
        
        result = aggregator.aggregate(items, strategy="invalid_strategy")
        
        assert not result.success
        assert result.error is not None
        assert "Unsupported aggregation strategy" in result.error
    



class TestBatchAggregatorCustom:
    """Tests for custom aggregation strategy"""
    
    def test_custom_aggregation_python_simple(self):
        """Test custom aggregation with simple Python code"""
        aggregator = BatchAggregator()
        items = [{"score": 85}, {"score": 90}, {"score": 78}]
        
        code = """
def aggregate(items):
    scores = [item["score"] for item in items]
    return {"average": sum(scores) / len(scores), "count": len(scores)}
"""
        
        result = aggregator.aggregate_custom(items, code, language="python")
        
        assert result["average"] == pytest.approx(84.33, rel=0.01)
        assert result["count"] == 3
    
    def test_custom_aggregation_python_filter_and_sum(self):
        """Test custom aggregation with filtering and summing"""
        aggregator = BatchAggregator()
        items = [
            {"score": 85, "passed": True},
            {"score": 45, "passed": False},
            {"score": 90, "passed": True},
            {"score": 60, "passed": False}
        ]
        
        code = """
def aggregate(items):
    passed_items = [item for item in items if item.get("passed", False)]
    total_score = sum(item["score"] for item in passed_items)
    return {"passed_count": len(passed_items), "total_score": total_score}
"""
        
        result = aggregator.aggregate_custom(items, code, language="python")
        
        assert result["passed_count"] == 2
        assert result["total_score"] == 175
    
    def test_custom_aggregation_javascript_simple(self):
        """Test custom aggregation with simple JavaScript code"""
        aggregator = BatchAggregator()
        items = [{"value": 10}, {"value": 20}, {"value": 30}]
        
        code = """
function aggregate(items) {
    const sum = items.reduce((acc, item) => acc + item.value, 0);
    return {sum: sum, count: items.length};
}

module.exports = aggregate;
"""
        
        result = aggregator.aggregate_custom(items, code, language="javascript")
        
        assert result["sum"] == 60
        assert result["count"] == 3
    
    def test_custom_aggregation_javascript_complex(self):
        """Test custom aggregation with complex JavaScript logic"""
        aggregator = BatchAggregator()
        items = [
            {"name": "Alice", "score": 85},
            {"name": "Bob", "score": 90},
            {"name": "Charlie", "score": 78}
        ]
        
        code = """
function aggregate(items) {
    const scores = items.map(item => item.score);
    const avg = scores.reduce((a, b) => a + b, 0) / scores.length;
    const max = Math.max(...scores);
    const min = Math.min(...scores);
    
    return {
        average: avg,
        max: max,
        min: min,
        names: items.map(item => item.name)
    };
}

module.exports = aggregate;
"""
        
        result = aggregator.aggregate_custom(items, code, language="javascript")
        
        assert result["average"] == pytest.approx(84.33, rel=0.01)
        assert result["max"] == 90
        assert result["min"] == 78
        assert result["names"] == ["Alice", "Bob", "Charlie"]
    
    def test_custom_aggregation_empty_code(self):
        """Test custom aggregation with empty code"""
        aggregator = BatchAggregator()
        items = [{"a": 1}]
        
        with pytest.raises(ValueError, match="code cannot be empty"):
            aggregator.aggregate_custom(items, "", language="python")
    
    def test_custom_aggregation_unsupported_language(self):
        """Test custom aggregation with unsupported language"""
        aggregator = BatchAggregator()
        items = [{"a": 1}]
        
        with pytest.raises(ValueError, match="Unsupported language"):
            aggregator.aggregate_custom(items, "code", language="ruby")
    
    def test_custom_aggregation_python_syntax_error(self):
        """Test custom aggregation with Python syntax error"""
        aggregator = BatchAggregator()
        items = [{"a": 1}]
        
        code = """
def aggregate(items):
    return items[  # Syntax error: unclosed bracket
"""
        
        with pytest.raises(RuntimeError, match="execution failed"):
            aggregator.aggregate_custom(items, code, language="python")
    
    def test_custom_aggregation_python_runtime_error(self):
        """Test custom aggregation with Python runtime error"""
        aggregator = BatchAggregator()
        items = [{"a": 1}]
        
        code = """
def aggregate(items):
    return items[100]  # IndexError
"""
        
        with pytest.raises(RuntimeError, match="execution failed"):
            aggregator.aggregate_custom(items, code, language="python")
    
    def test_custom_aggregation_javascript_syntax_error(self):
        """Test custom aggregation with JavaScript syntax error"""
        aggregator = BatchAggregator()
        items = [{"a": 1}]
        
        code = """
function aggregate(inputs) {
    return inputs.items[  // Syntax error
}
module.exports = aggregate;
"""
        
        with pytest.raises(RuntimeError, match="execution failed"):
            aggregator.aggregate_custom(items, code, language="javascript")
    
    def test_custom_aggregation_with_timeout(self):
        """Test custom aggregation with custom timeout"""
        aggregator = BatchAggregator()
        items = [{"a": 1}]
        
        code = """
def aggregate(items):
    return {"result": "quick"}
"""
        
        result = aggregator.aggregate_custom(items, code, language="python", timeout=5)
        
        assert result["result"] == "quick"
    
    def test_custom_aggregation_via_aggregate_method(self):
        """Test custom aggregation through the main aggregate method"""
        aggregator = BatchAggregator()
        items = [{"x": 1}, {"x": 2}, {"x": 3}]
        
        code = """
def aggregate(items):
    return {"sum": sum(item["x"] for item in items)}
"""
        
        result = aggregator.aggregate(
            items,
            strategy="custom",
            code=code,
            language="python"
        )
        
        assert result.success
        assert result.result["sum"] == 6
        assert result.strategy == "custom"
        assert result.item_count == 3


class TestAggregationResult:
    """Tests for AggregationResult dataclass"""
    
    def test_aggregation_result_to_dict(self):
        """Test converting AggregationResult to dict"""
        result = AggregationResult(
            success=True,
            result="test result",
            strategy="concat",
            item_count=5
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["result"] == "test result"
        assert result_dict["strategy"] == "concat"
        assert result_dict["item_count"] == 5
        assert result_dict["error"] is None
    
    def test_aggregation_result_with_error(self):
        """Test AggregationResult with error"""
        result = AggregationResult(
            success=False,
            result=None,
            error="Something went wrong",
            strategy="stats",
            item_count=3
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is False
        assert result_dict["error"] == "Something went wrong"


class TestBatchProcessor:
    """Tests for BatchProcessor class"""
    
    def test_batch_processor_initialization(self):
        """Test BatchProcessor initialization"""
        processor = BatchProcessor(max_workers=8)
        
        assert processor.max_workers == 8
    
    def test_batch_processor_default_max_workers(self):
        """Test BatchProcessor with default max_workers"""
        processor = BatchProcessor()
        
        assert processor.max_workers == 4
    
    def test_process_in_batches_simple(self):
        """Test processing items in batches with simple function"""
        from src.batch_aggregator import BatchProcessor
        
        processor = BatchProcessor()
        items = [1, 2, 3, 4, 5]
        
        def double(x):
            return x * 2
        
        results = processor.process_in_batches(items, double, batch_size=2, concurrent=False)
        
        assert results == [2, 4, 6, 8, 10]
    
    def test_process_in_batches_with_batch_size(self):
        """Test batch size control"""
        from src.batch_aggregator import BatchProcessor
        
        processor = BatchProcessor()
        items = list(range(10))
        
        def identity(x):
            return x
        
        results = processor.process_in_batches(items, identity, batch_size=3, concurrent=False)
        
        assert results == items
        assert len(results) == 10
    
    def test_process_in_batches_concurrent(self):
        """Test concurrent batch processing"""
        from src.batch_aggregator import BatchProcessor
        
        processor = BatchProcessor(max_workers=2)
        items = [1, 2, 3, 4, 5, 6]
        
        def square(x):
            return x ** 2
        
        results = processor.process_in_batches(items, square, batch_size=2, concurrent=True)
        
        assert results == [1, 4, 9, 16, 25, 36]
    
    def test_process_in_batches_sequential(self):
        """Test sequential batch processing"""
        from src.batch_aggregator import BatchProcessor
        
        processor = BatchProcessor()
        items = [1, 2, 3, 4, 5]
        
        def triple(x):
            return x * 3
        
        results = processor.process_in_batches(items, triple, batch_size=2, concurrent=False)
        
        assert results == [3, 6, 9, 12, 15]
    
    def test_process_in_batches_empty_list(self):
        """Test processing empty list"""
        from src.batch_aggregator import BatchProcessor
        
        processor = BatchProcessor()
        items = []
        
        def identity(x):
            return x
        
        results = processor.process_in_batches(items, identity, batch_size=10)
        
        assert results == []
    
    def test_process_in_batches_invalid_batch_size(self):
        """Test with invalid batch size"""
        from src.batch_aggregator import BatchProcessor
        
        processor = BatchProcessor()
        items = [1, 2, 3]
        
        def identity(x):
            return x
        
        with pytest.raises(ValueError, match="batch_size must be at least 1"):
            processor.process_in_batches(items, identity, batch_size=0)
    
    def test_process_in_batches_with_errors(self):
        """Test batch processing with some items failing"""
        from src.batch_aggregator import BatchProcessor
        
        processor = BatchProcessor()
        items = [1, 2, 0, 4, 5]  # 0 will cause division error
        
        def divide_10_by(x):
            return 10 / x
        
        results = processor.process_in_batches(items, divide_10_by, batch_size=2, concurrent=False)
        
        # Failed item should be None
        assert results[0] == 10.0
        assert results[1] == 5.0
        assert results[2] is None  # Division by zero
        assert results[3] == 2.5
        assert results[4] == 2.0
    
    def test_process_in_batches_dict_items(self):
        """Test processing dictionary items"""
        from src.batch_aggregator import BatchProcessor
        
        processor = BatchProcessor()
        items = [
            {"name": "Alice", "score": 85},
            {"name": "Bob", "score": 90},
            {"name": "Charlie", "score": 78}
        ]
        
        def extract_score(item):
            return item["score"]
        
        results = processor.process_in_batches(items, extract_score, batch_size=2, concurrent=False)
        
        assert results == [85, 90, 78]
    
    def test_process_in_batches_detailed_success(self):
        """Test detailed batch processing with success"""
        from src.batch_aggregator import BatchProcessor
        
        processor = BatchProcessor()
        items = [1, 2, 3, 4, 5]
        
        def double(x):
            return x * 2
        
        result = processor.process_in_batches_detailed(items, double, batch_size=2, concurrent=False)
        
        assert result.success is True
        assert result.results == [2, 4, 6, 8, 10]
        assert result.total_items == 5
        assert result.batch_count == 3  # 5 items / 2 per batch = 3 batches
        assert result.failed_items == []
        assert result.execution_time > 0
        assert result.error is None
    
    def test_process_in_batches_detailed_with_failures(self):
        """Test detailed batch processing with some failures"""
        from src.batch_aggregator import BatchProcessor
        
        processor = BatchProcessor()
        items = [1, 2, 0, 4]  # 0 will cause error
        
        def divide_10_by(x):
            return 10 / x
        
        result = processor.process_in_batches_detailed(items, divide_10_by, batch_size=2, concurrent=False)
        
        assert result.success is True
        assert result.total_items == 4
        assert result.batch_count == 2
        assert 2 in result.failed_items  # Index 2 (value 0) should fail
        assert result.results[2] is None
    
    def test_process_in_batches_detailed_empty_list(self):
        """Test detailed processing with empty list"""
        from src.batch_aggregator import BatchProcessor
        
        processor = BatchProcessor()
        items = []
        
        def identity(x):
            return x
        
        result = processor.process_in_batches_detailed(items, identity, batch_size=10)
        
        assert result.success is True
        assert result.results == []
        assert result.total_items == 0
        assert result.batch_count == 0
    
    def test_process_in_batches_detailed_invalid_batch_size(self):
        """Test detailed processing with invalid batch size"""
        from src.batch_aggregator import BatchProcessor
        
        processor = BatchProcessor()
        items = [1, 2, 3]
        
        def identity(x):
            return x
        
        result = processor.process_in_batches_detailed(items, identity, batch_size=-1)
        
        assert result.success is False
        assert result.error is not None
        assert "batch_size must be at least 1" in result.error
    
    def test_batch_processing_result_to_dict(self):
        """Test BatchProcessingResult to_dict method"""
        from src.batch_aggregator import BatchProcessingResult
        
        result = BatchProcessingResult(
            success=True,
            results=[1, 2, 3],
            total_items=3,
            batch_count=2,
            failed_items=[],
            execution_time=1.5
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["success"] is True
        assert result_dict["results"] == [1, 2, 3]
        assert result_dict["total_items"] == 3
        assert result_dict["batch_count"] == 2
        assert result_dict["failed_items"] == []
        assert result_dict["execution_time"] == 1.5
        assert result_dict["error"] is None
    
    def test_create_batches(self):
        """Test internal _create_batches method"""
        from src.batch_aggregator import BatchProcessor
        
        processor = BatchProcessor()
        items = [1, 2, 3, 4, 5, 6, 7]
        
        batches = processor._create_batches(items, batch_size=3)
        
        assert len(batches) == 3
        assert batches[0] == [1, 2, 3]
        assert batches[1] == [4, 5, 6]
        assert batches[2] == [7]
    
    def test_process_single_batch(self):
        """Test internal _process_single_batch method"""
        from src.batch_aggregator import BatchProcessor
        
        processor = BatchProcessor()
        batch = [1, 2, 3]
        
        def double(x):
            return x * 2
        
        results = processor._process_single_batch(batch, double)
        
        assert results == [2, 4, 6]
    
    def test_process_single_batch_with_error(self):
        """Test _process_single_batch with error handling"""
        from src.batch_aggregator import BatchProcessor
        
        processor = BatchProcessor()
        batch = [1, 0, 3]  # 0 will cause error
        
        def divide_10_by(x):
            return 10 / x
        
        results = processor._process_single_batch(batch, divide_10_by)
        
        assert results[0] == 10.0
        assert results[1] is None  # Failed item
        assert results[2] == pytest.approx(3.33, rel=0.01)
    
    def test_process_in_batches_large_dataset(self):
        """Test batch processing with larger dataset"""
        from src.batch_aggregator import BatchProcessor
        
        processor = BatchProcessor(max_workers=4)
        items = list(range(100))
        
        def add_one(x):
            return x + 1
        
        results = processor.process_in_batches(items, add_one, batch_size=10, concurrent=True)
        
        assert len(results) == 100
        assert results == list(range(1, 101))
    
    def test_process_in_batches_not_callable(self):
        """Test with non-callable processor"""
        from src.batch_aggregator import BatchProcessor
        
        processor = BatchProcessor()
        items = [1, 2, 3]
        
        with pytest.raises(ValueError, match="processor must be a callable"):
            processor.process_in_batches(items, "not a function", batch_size=2)
