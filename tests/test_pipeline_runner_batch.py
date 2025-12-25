"""
Tests for batch processing in PipelineRunner

Requirements: 4.2, 4.4
"""
import pytest
from pathlib import Path
from src.pipeline_runner import PipelineRunner, PipelineResult
from src.models import PipelineConfig, StepConfig


class TestBatchAggregatorSteps:
    """Tests for batch_aggregator step execution"""
    
    def test_batch_aggregator_concat(self):
        """Test batch aggregator with concat strategy"""
        config = PipelineConfig(
            id="test_batch_concat",
            name="Test Batch Concat",
            description="Test concat aggregation",
            inputs=[],
            steps=[
                StepConfig(
                    id="concat_items",
                    type="batch_aggregator",
                    aggregation_strategy="concat",
                    separator=", ",
                    input_mapping={"items": "test_items"},
                    output_key="concatenated"
                )
            ],
            outputs=[{"key": "concatenated", "label": "Concatenated"}]
        )
        
        runner = PipelineRunner(config, enable_concurrent=False)
        runner.context["test_items"] = ["apple", "banana", "cherry"]
        
        step = config.steps[0]
        result = runner.execute_step(step)
        
        assert result.success
        assert result.output_value == "apple, banana, cherry"
        assert result.step_id == "concat_items"
    
    def test_batch_aggregator_stats(self):
        """Test batch aggregator with stats strategy"""
        config = PipelineConfig(
            id="test_batch_stats",
            name="Test Batch Stats",
            description="Test stats aggregation",
            inputs=[],
            steps=[
                StepConfig(
                    id="compute_stats",
                    type="batch_aggregator",
                    aggregation_strategy="stats",
                    fields=["score", "count"],
                    input_mapping={"items": "test_data"},
                    output_key="statistics"
                )
            ],
            outputs=[{"key": "statistics", "label": "Statistics"}]
        )
        
        runner = PipelineRunner(config, enable_concurrent=False)
        runner.context["test_data"] = [
            {"score": 10, "count": 5},
            {"score": 20, "count": 10},
            {"score": 30, "count": 15}
        ]
        
        step = config.steps[0]
        result = runner.execute_step(step)
        
        assert result.success
        assert "fields" in result.output_value
        assert "score" in result.output_value["fields"]
        assert result.output_value["fields"]["score"]["mean"] == 20.0
        assert result.output_value["fields"]["count"]["sum"] == 30
    
    def test_batch_aggregator_custom_python(self):
        """Test batch aggregator with custom Python code"""
        config = PipelineConfig(
            id="test_custom_python",
            name="Test Custom Python",
            description="Test custom Python aggregation",
            inputs=[],
            steps=[
                StepConfig(
                    id="custom_agg",
                    type="batch_aggregator",
                    aggregation_strategy="custom",
                    language="python",
                    aggregation_code="""
def aggregate(items):
    return {
        "total": len(items),
        "sum": sum(items),
        "average": sum(items) / len(items) if items else 0
    }
""",
                    input_mapping={"items": "numbers"},
                    output_key="result"
                )
            ],
            outputs=[{"key": "result", "label": "Result"}]
        )
        
        runner = PipelineRunner(config, enable_concurrent=False)
        runner.context["numbers"] = [10, 20, 30, 40, 50]
        
        step = config.steps[0]
        result = runner.execute_step(step)
        
        assert result.success
        assert result.output_value["total"] == 5
        assert result.output_value["sum"] == 150
        assert result.output_value["average"] == 30.0
    
    def test_batch_aggregator_empty_items(self):
        """Test batch aggregator with empty items list"""
        config = PipelineConfig(
            id="test_empty_items",
            name="Test Empty Items",
            description="Test empty items",
            inputs=[],
            steps=[
                StepConfig(
                    id="concat_empty",
                    type="batch_aggregator",
                    aggregation_strategy="concat",
                    separator=", ",
                    input_mapping={"items": "empty_items"},
                    output_key="result"
                )
            ],
            outputs=[{"key": "result", "label": "Result"}]
        )
        
        runner = PipelineRunner(config, enable_concurrent=False)
        runner.context["empty_items"] = []
        
        step = config.steps[0]
        result = runner.execute_step(step)
        
        assert result.success
        assert result.output_value == []


class TestBatchModeSteps:
    """Tests for batch_mode agent_flow steps"""
    
    def test_batch_mode_identification(self):
        """Test that batch_mode is correctly identified"""
        config = PipelineConfig(
            id="test_batch_mode",
            name="Test Batch Mode",
            description="Test batch mode",
            inputs=[],
            steps=[
                StepConfig(
                    id="batch_step",
                    type="agent_flow",
                    agent="test_agent",
                    flow="test_flow",
                    batch_mode=True,
                    batch_size=10,
                    concurrent=True,
                    max_workers=4,
                    input_mapping={"text": "input_texts"},
                    output_key="results"
                )
            ],
            outputs=[{"key": "results", "label": "Results"}]
        )
        
        step = config.steps[0]
        assert step.batch_mode == True
        assert step.batch_size == 10
        assert step.concurrent == True
        assert step.max_workers == 4


class TestBatchDataCollection:
    """Tests for batch data collection from inputs"""
    
    def test_collect_batch_data_from_list_input(self):
        """Test collecting batch data from list input"""
        config = PipelineConfig(
            id="test_collect_batch",
            name="Test Collect Batch",
            description="Test batch data collection",
            inputs=[],
            steps=[
                StepConfig(
                    id="aggregate",
                    type="batch_aggregator",
                    aggregation_strategy="concat",
                    separator=" | ",
                    input_mapping={"items": "reviews"},
                    output_key="all_reviews"
                )
            ],
            outputs=[{"key": "all_reviews", "label": "All Reviews"}]
        )
        
        runner = PipelineRunner(config, enable_concurrent=False)
        
        # Simulate batch data from previous step
        runner.context["reviews"] = [
            "Great product!",
            "Not bad",
            "Excellent service"
        ]
        
        step = config.steps[0]
        result = runner.execute_step(step)
        
        assert result.success
        assert "Great product!" in result.output_value
        assert "Not bad" in result.output_value
        assert "Excellent service" in result.output_value


class TestBatchResultPassing:
    """Tests for passing aggregated results to subsequent steps"""
    
    def test_aggregation_result_passed_to_next_step(self):
        """Test that aggregated results are passed to subsequent steps"""
        config = PipelineConfig(
            id="test_result_passing",
            name="Test Result Passing",
            description="Test result passing",
            inputs=[],
            steps=[
                # Step 1: Aggregate items
                StepConfig(
                    id="aggregate_items",
                    type="batch_aggregator",
                    aggregation_strategy="concat",
                    separator="\n",
                    input_mapping={"items": "input_items"},
                    output_key="aggregated_text"
                ),
                # Step 2: Use aggregated result (code node for testing)
                StepConfig(
                    id="process_aggregated",
                    type="code_node",
                    language="python",
                    code="""
def transform(inputs):
    text = inputs.get('text', '')
    lines = text.split('\\n')
    return {
        "line_count": len(lines),
        "total_length": len(text),
        "lines": lines
    }
""",
                    input_mapping={"text": "aggregated_text"},
                    output_key="processed_result"
                )
            ],
            outputs=[{"key": "processed_result", "label": "Processed Result"}]
        )
        
        runner = PipelineRunner(config, enable_concurrent=False)
        
        # Set up initial data
        runner.context["input_items"] = ["Line 1", "Line 2", "Line 3"]
        
        # Execute first step (aggregation)
        step1 = config.steps[0]
        result1 = runner.execute_step(step1)
        assert result1.success
        
        # Add result to context (simulating pipeline execution)
        runner.context[result1.output_key] = result1.output_value
        
        # Execute second step (processing)
        step2 = config.steps[1]
        result2 = runner.execute_step(step2)
        assert result2.success
        
        # The code node returns the output directly
        output = result2.output_value
        assert output["line_count"] == 3
        assert output["lines"] == ["Line 1", "Line 2", "Line 3"]


class TestBatchProcessingIntegration:
    """Integration tests for complete batch processing workflows"""
    
    def test_multi_stage_batch_processing(self):
        """Test multi-stage batch processing with aggregation"""
        config = PipelineConfig(
            id="test_multi_stage",
            name="Test Multi-Stage Batch",
            description="Test multi-stage batch processing",
            inputs=[],
            steps=[
                # Stage 1: Aggregate raw data
                StepConfig(
                    id="aggregate_raw",
                    type="batch_aggregator",
                    aggregation_strategy="stats",
                    fields=["value"],
                    input_mapping={"items": "raw_data"},
                    output_key="raw_stats"
                ),
                # Stage 2: Process stats with code node
                StepConfig(
                    id="process_stats",
                    type="code_node",
                    language="python",
                    code="""
def transform(inputs):
    stats = inputs.get("stats", {})
    fields = stats.get("fields", {})
    value_stats = fields.get("value", {})
    
    return {
        "summary": f"Processed {stats['total_items']} items",
        "average": value_stats.get("mean", 0),
        "range": value_stats.get("max", 0) - value_stats.get("min", 0)
    }
""",
                    input_mapping={"stats": "raw_stats"},
                    output_key="summary"
                )
            ],
            outputs=[{"key": "summary", "label": "Summary"}]
        )
        
        runner = PipelineRunner(config, enable_concurrent=False)
        
        # Set up test data
        runner.context["raw_data"] = [
            {"value": 10},
            {"value": 20},
            {"value": 30},
            {"value": 40},
            {"value": 50}
        ]
        
        # Execute stage 1
        step1 = config.steps[0]
        result1 = runner.execute_step(step1)
        assert result1.success
        runner.context[result1.output_key] = result1.output_value
        
        # Execute stage 2
        step2 = config.steps[1]
        result2 = runner.execute_step(step2)
        assert result2.success
        assert "Processed 5 items" in result2.output_value["summary"]
        assert result2.output_value["average"] == 30.0
        assert result2.output_value["range"] == 40


class TestBatchErrorHandling:
    """Tests for error handling in batch processing"""
    
    def test_batch_aggregator_missing_items(self):
        """Test batch aggregator when items are missing from context"""
        config = PipelineConfig(
            id="test_missing_items",
            name="Test Missing Items",
            description="Test missing items",
            inputs=[],
            steps=[
                StepConfig(
                    id="aggregate",
                    type="batch_aggregator",
                    aggregation_strategy="concat",
                    input_mapping={"items": "nonexistent_items"},
                    output_key="result"
                )
            ],
            outputs=[{"key": "result", "label": "Result"}]
        )
        
        runner = PipelineRunner(config, enable_concurrent=False)
        # Don't set nonexistent_items in context
        
        step = config.steps[0]
        result = runner.execute_step(step)
        
        # Should handle gracefully with empty list
        assert result.success
        assert result.output_value == []
    
    def test_batch_aggregator_invalid_strategy(self):
        """Test batch aggregator with invalid strategy"""
        # Invalid strategy should be caught during config validation
        from src.error_handler import ConfigurationError
        
        with pytest.raises(ConfigurationError) as exc_info:
            config = PipelineConfig(
                id="test_invalid_strategy",
                name="Test Invalid Strategy",
                description="Test invalid strategy",
                inputs=[],
                steps=[
                    StepConfig(
                        id="aggregate",
                        type="batch_aggregator",
                        aggregation_strategy="invalid_strategy",
                        input_mapping={"items": "test_items"},
                        output_key="result"
                    )
                ],
                outputs=[{"key": "result", "label": "Result"}]
            )
            
            runner = PipelineRunner(config, enable_concurrent=False)
        
        # Verify the error message
        assert "invalid_strategy" in str(exc_info.value).lower() or "不支持的聚合策略" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
