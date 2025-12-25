"""
Batch Aggregator

Provides aggregation capabilities for batch processing in pipelines.
Supports multiple aggregation strategies:
- concat: Concatenate items with a separator
- stats: Calculate statistics on specified fields
- filter: Filter items based on a condition
- custom: Execute custom aggregation code

Requirements: 4.3, 4.5
"""

from __future__ import annotations

import json
import logging
import statistics
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field

# Configure logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


@dataclass
class AggregationResult:
    """
    Result of batch aggregation operation.
    
    Attributes:
        success: Whether aggregation completed successfully
        result: The aggregated result
        error: Error message if aggregation failed
        strategy: The aggregation strategy used
        item_count: Number of items aggregated
    """
    success: bool
    result: Any
    error: Optional[str] = None
    strategy: Optional[str] = None
    item_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "strategy": self.strategy,
            "item_count": self.item_count
        }


class BatchAggregator:
    """
    Batch aggregator for processing and combining multiple items.
    
    Supports multiple aggregation strategies:
    - concat: Concatenate items into a single string
    - stats: Calculate statistics on numeric fields
    - filter: Filter items based on conditions
    - custom: Execute custom aggregation code
    """
    
    def __init__(self):
        """Initialize the batch aggregator"""
        logger.info("Initializing BatchAggregator")
    
    def aggregate(
        self,
        items: List[Any],
        strategy: str,
        **kwargs
    ) -> AggregationResult:
        """
        Aggregate items using the specified strategy.
        
        Args:
            items: List of items to aggregate
            strategy: Aggregation strategy ("concat", "stats", "filter", "custom")
            **kwargs: Strategy-specific parameters
            
        Returns:
            AggregationResult with the aggregated result
        """
        if not items:
            logger.warning("Empty items list provided for aggregation")
            return AggregationResult(
                success=True,
                result=None,
                strategy=strategy,
                item_count=0
            )
        
        try:
            if strategy == "concat":
                result = self.aggregate_concat(
                    items,
                    separator=kwargs.get("separator", "\n")
                )
            elif strategy == "stats":
                result = self.aggregate_stats(
                    items,
                    fields=kwargs.get("fields", [])
                )
            elif strategy == "filter":
                result = self.aggregate_filter(
                    items,
                    condition=kwargs.get("condition")
                )
            elif strategy == "custom":
                result = self.aggregate_custom(
                    items,
                    code=kwargs.get("code", ""),
                    language=kwargs.get("language", "python"),
                    timeout=kwargs.get("timeout", 30)
                )
            else:
                raise ValueError(f"Unsupported aggregation strategy: {strategy}")
            
            return AggregationResult(
                success=True,
                result=result,
                strategy=strategy,
                item_count=len(items)
            )
            
        except Exception as e:
            logger.error(f"Aggregation failed with strategy '{strategy}': {str(e)}")
            return AggregationResult(
                success=False,
                result=None,
                error=str(e),
                strategy=strategy,
                item_count=len(items)
            )
    
    def aggregate_concat(
        self,
        items: List[Any],
        separator: str = "\n"
    ) -> str:
        """
        Concatenate items into a single string.
        
        Args:
            items: List of items to concatenate
            separator: String to use between items (default: newline)
            
        Returns:
            Concatenated string
            
        Example:
            >>> aggregator = BatchAggregator()
            >>> items = ["hello", "world", "test"]
            >>> result = aggregator.aggregate_concat(items, separator=" ")
            >>> print(result)
            "hello world test"
        """
        logger.info(f"Concatenating {len(items)} items with separator: {repr(separator)}")
        
        # Convert items to strings
        str_items = []
        for item in items:
            if isinstance(item, str):
                str_items.append(item)
            elif isinstance(item, dict):
                # For dict items, try to extract a text field or convert to JSON
                if "text" in item:
                    str_items.append(str(item["text"]))
                elif "output" in item:
                    str_items.append(str(item["output"]))
                elif "result" in item:
                    str_items.append(str(item["result"]))
                else:
                    str_items.append(json.dumps(item, ensure_ascii=False))
            else:
                str_items.append(str(item))
        
        result = separator.join(str_items)
        logger.info(f"Concatenation complete, result length: {len(result)} characters")
        return result
    
    def aggregate_stats(
        self,
        items: List[Any],
        fields: List[str]
    ) -> Dict[str, Any]:
        """
        Calculate statistics on specified fields.
        
        Args:
            items: List of items (typically dicts) to analyze
            fields: List of field names to calculate statistics for
            
        Returns:
            Dictionary with statistics for each field
            
        Example:
            >>> aggregator = BatchAggregator()
            >>> items = [
            ...     {"score": 85, "time": 1.2},
            ...     {"score": 90, "time": 1.5},
            ...     {"score": 78, "time": 1.1}
            ... ]
            >>> result = aggregator.aggregate_stats(items, fields=["score", "time"])
            >>> print(result["score"]["mean"])
            84.33
        """
        logger.info(f"Calculating statistics for {len(items)} items on fields: {fields}")
        
        if not fields:
            raise ValueError("No fields specified for stats aggregation")
        
        stats_result = {
            "total_items": len(items),
            "fields": {}
        }
        
        for field in fields:
            # Extract values for this field
            values = []
            for item in items:
                if isinstance(item, dict) and field in item:
                    value = item[field]
                    # Only include numeric values
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        values.append(value)
            
            if not values:
                logger.warning(f"No numeric values found for field '{field}'")
                stats_result["fields"][field] = {
                    "count": 0,
                    "error": "No numeric values found"
                }
                continue
            
            # Calculate statistics
            field_stats = {
                "count": len(values),
                "sum": sum(values),
                "mean": statistics.mean(values),
                "min": min(values),
                "max": max(values)
            }
            
            # Add median and stdev if we have enough values
            if len(values) >= 2:
                field_stats["median"] = statistics.median(values)
                field_stats["stdev"] = statistics.stdev(values)
            
            stats_result["fields"][field] = field_stats
            logger.info(f"Statistics for '{field}': mean={field_stats['mean']:.2f}, "
                       f"min={field_stats['min']}, max={field_stats['max']}")
        
        return stats_result
    
    def aggregate_filter(
        self,
        items: List[Any],
        condition: Optional[Callable] = None
    ) -> List[Any]:
        """
        Filter items based on a condition.
        
        Args:
            items: List of items to filter
            condition: Callable that returns True for items to keep
            
        Returns:
            Filtered list of items
            
        Example:
            >>> aggregator = BatchAggregator()
            >>> items = [
            ...     {"score": 85, "passed": True},
            ...     {"score": 45, "passed": False},
            ...     {"score": 90, "passed": True}
            ... ]
            >>> result = aggregator.aggregate_filter(
            ...     items,
            ...     condition=lambda x: x.get("passed", False)
            ... )
            >>> len(result)
            2
        """
        logger.info(f"Filtering {len(items)} items")
        
        if condition is None:
            logger.warning("No condition provided for filter aggregation, returning all items")
            return items
        
        if not callable(condition):
            raise ValueError("Condition must be a callable function")
        
        filtered_items = [item for item in items if condition(item)]
        logger.info(f"Filter complete: {len(filtered_items)} items passed the condition")
        
        return filtered_items
    
    def aggregate_custom(
        self,
        items: List[Any],
        code: str,
        language: str = "python",
        timeout: int = 30
    ) -> Any:
        """
        Execute custom aggregation code using CodeExecutor.
        
        The custom code should define a function that takes the items list
        and returns the aggregated result. Supported function names:
        - Python: aggregate(), transform(), process_data(), main()
        - JavaScript: module.exports, exports, aggregate(), transform(), process_data(), main()
        
        Args:
            items: List of items to aggregate
            code: Custom aggregation code
            language: Programming language ("python" or "javascript")
            timeout: Timeout in seconds for code execution (default: 30)
            
        Returns:
            Result of custom aggregation
            
        Raises:
            ValueError: If code is empty or language is unsupported
            RuntimeError: If code execution fails
            
        Example:
            >>> aggregator = BatchAggregator()
            >>> items = [{"score": 85}, {"score": 90}, {"score": 78}]
            >>> code = '''
            ... def aggregate(items):
            ...     scores = [item["score"] for item in items]
            ...     return {"average": sum(scores) / len(scores)}
            ... '''
            >>> result = aggregator.aggregate_custom(items, code, language="python")
            >>> print(result)
            {"average": 84.33}
        """
        logger.info(f"Executing custom aggregation with {language} code (timeout: {timeout}s)")
        
        if not code or not code.strip():
            raise ValueError("Custom aggregation code cannot be empty")
        
        if language.lower() not in ("python", "py", "javascript", "js", "node"):
            raise ValueError(
                f"Unsupported language: {language}. "
                "Supported languages: python, javascript"
            )
        
        # Import CodeExecutor here to avoid circular imports
        try:
            from src.code_executor import CodeExecutor
        except ImportError:
            from code_executor import CodeExecutor
        
        try:
            # Create CodeExecutor instance
            executor = CodeExecutor(default_timeout=timeout)
            
            # Prepare inputs for the code
            # Pass items directly for aggregate functions, wrapped for others
            inputs = {"items": items}
            
            # Execute the custom code
            logger.debug(f"Executing custom aggregation code with {len(items)} items")
            result = executor.execute(code, language, inputs, timeout)
            
            if not result.success:
                error_msg = f"Custom aggregation code execution failed: {result.error}"
                if result.stack_trace:
                    error_msg += f"\n\nStack trace:\n{result.stack_trace}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            
            logger.info(f"Custom aggregation completed successfully in {result.execution_time:.2f}s")
            return result.output
            
        except (ValueError, RuntimeError):
            # Re-raise validation and execution errors
            raise
        except Exception as e:
            logger.error(f"Unexpected error during custom aggregation: {e}", exc_info=True)
            raise RuntimeError(f"Unexpected error during custom aggregation: {str(e)}")


@dataclass
class BatchProcessingResult:
    """
    Result of batch processing operation.
    
    Attributes:
        success: Whether batch processing completed successfully
        results: List of processed results (one per item)
        total_items: Total number of items processed
        batch_count: Number of batches processed
        failed_items: List of indices of items that failed
        execution_time: Total execution time in seconds
        error: Error message if processing failed
    """
    success: bool
    results: List[Any]
    total_items: int
    batch_count: int
    failed_items: List[int] = field(default_factory=list)
    execution_time: float = 0.0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "success": self.success,
            "results": self.results,
            "total_items": self.total_items,
            "batch_count": self.batch_count,
            "failed_items": self.failed_items,
            "execution_time": self.execution_time,
            "error": self.error
        }


class BatchProcessor:
    """
    Batch processor for handling batch operations in pipelines.
    
    Supports:
    - Batch size control
    - Concurrent batch processing
    - Result aggregation
    - Error handling for individual items
    
    Requirements: 4.2
    """
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize the batch processor
        
        Args:
            max_workers: Maximum number of concurrent workers for batch processing
        """
        self.max_workers = max_workers
        logger.info(f"Initializing BatchProcessor with max_workers={max_workers}")
    
    def process_in_batches(
        self,
        items: List[Any],
        processor: Callable,
        batch_size: int = 10,
        concurrent: bool = True
    ) -> List[Any]:
        """
        Process items in batches.
        
        This method divides the input items into batches and processes them
        either sequentially or concurrently based on the concurrent flag.
        
        Args:
            items: List of items to process
            processor: Function to process each item. Should accept a single item
                      and return the processed result. Can raise exceptions for
                      individual item failures.
            batch_size: Number of items per batch (default: 10)
            concurrent: Whether to process batches concurrently (default: True)
            
        Returns:
            List[Any]: List of processed results, one per input item.
                      Failed items will have None as their result.
            
        Raises:
            ValueError: If batch_size is less than 1 or items is empty
            
        Example:
            >>> processor = BatchProcessor()
            >>> items = [1, 2, 3, 4, 5]
            >>> def double(x): return x * 2
            >>> results = processor.process_in_batches(items, double, batch_size=2)
            >>> print(results)
            [2, 4, 6, 8, 10]
        """
        import time
        
        start_time = time.time()
        
        # Validation
        if not items:
            logger.warning("Empty items list provided for batch processing")
            return []
        
        if batch_size < 1:
            raise ValueError(f"batch_size must be at least 1, got {batch_size}")
        
        if not callable(processor):
            raise ValueError("processor must be a callable function")
        
        logger.info(
            f"Processing {len(items)} items in batches of {batch_size}, "
            f"concurrent={concurrent}"
        )
        
        # Divide items into batches
        batches = self._create_batches(items, batch_size)
        logger.info(f"Created {len(batches)} batches")
        
        # Process batches
        if concurrent and len(batches) > 1:
            results = self._process_batches_concurrent(batches, processor)
        else:
            results = self._process_batches_sequential(batches, processor)
        
        execution_time = time.time() - start_time
        logger.info(
            f"Batch processing complete: {len(results)} results in "
            f"{execution_time:.2f}s"
        )
        
        return results
    
    def process_in_batches_detailed(
        self,
        items: List[Any],
        processor: Callable,
        batch_size: int = 10,
        concurrent: bool = True
    ) -> BatchProcessingResult:
        """
        Process items in batches with detailed result information.
        
        This method provides more detailed information about the batch processing
        operation, including failed items and execution time.
        
        Args:
            items: List of items to process
            processor: Function to process each item
            batch_size: Number of items per batch (default: 10)
            concurrent: Whether to process batches concurrently (default: True)
            
        Returns:
            BatchProcessingResult: Detailed result object with success status,
                                  results, and error information
            
        Example:
            >>> processor = BatchProcessor()
            >>> items = [1, 2, 3, 4, 5]
            >>> def double(x): return x * 2
            >>> result = processor.process_in_batches_detailed(items, double)
            >>> print(result.success)
            True
            >>> print(result.total_items)
            5
        """
        import time
        
        start_time = time.time()
        
        try:
            # Validation
            if not items:
                return BatchProcessingResult(
                    success=True,
                    results=[],
                    total_items=0,
                    batch_count=0,
                    execution_time=0.0
                )
            
            if batch_size < 1:
                raise ValueError(f"batch_size must be at least 1, got {batch_size}")
            
            # Process items
            results = self.process_in_batches(items, processor, batch_size, concurrent)
            
            # Identify failed items (None results)
            failed_items = [i for i, result in enumerate(results) if result is None]
            
            execution_time = time.time() - start_time
            batch_count = (len(items) + batch_size - 1) // batch_size
            
            return BatchProcessingResult(
                success=True,
                results=results,
                total_items=len(items),
                batch_count=batch_count,
                failed_items=failed_items,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Batch processing failed: {e}", exc_info=True)
            
            return BatchProcessingResult(
                success=False,
                results=[],
                total_items=len(items) if items else 0,
                batch_count=0,
                execution_time=execution_time,
                error=str(e)
            )
    
    def _create_batches(
        self,
        items: List[Any],
        batch_size: int
    ) -> List[List[Any]]:
        """
        Divide items into batches.
        
        Args:
            items: List of items to batch
            batch_size: Size of each batch
            
        Returns:
            List of batches, where each batch is a list of items
        """
        batches = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batches.append(batch)
        return batches
    
    def _process_batches_sequential(
        self,
        batches: List[List[Any]],
        processor: Callable
    ) -> List[Any]:
        """
        Process batches sequentially.
        
        Args:
            batches: List of batches to process
            processor: Function to process each item
            
        Returns:
            List of processed results
        """
        logger.info(f"Processing {len(batches)} batches sequentially")
        
        all_results = []
        for batch_idx, batch in enumerate(batches):
            logger.debug(f"Processing batch {batch_idx + 1}/{len(batches)}")
            batch_results = self._process_single_batch(batch, processor)
            all_results.extend(batch_results)
        
        return all_results
    
    def _process_batches_concurrent(
        self,
        batches: List[List[Any]],
        processor: Callable
    ) -> List[Any]:
        """
        Process batches concurrently using thread pool.
        
        Args:
            batches: List of batches to process
            processor: Function to process each item
            
        Returns:
            List of processed results in original order
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        logger.info(
            f"Processing {len(batches)} batches concurrently "
            f"with max_workers={self.max_workers}"
        )
        
        # Use thread pool for concurrent processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batches
            future_to_batch_idx = {}
            for batch_idx, batch in enumerate(batches):
                future = executor.submit(self._process_single_batch, batch, processor)
                future_to_batch_idx[future] = batch_idx
            
            # Collect results in order
            batch_results = [None] * len(batches)
            for future in as_completed(future_to_batch_idx):
                batch_idx = future_to_batch_idx[future]
                try:
                    result = future.result()
                    batch_results[batch_idx] = result
                    logger.debug(f"Batch {batch_idx + 1}/{len(batches)} completed")
                except Exception as e:
                    logger.error(
                        f"Batch {batch_idx + 1} failed: {e}",
                        exc_info=True
                    )
                    # Return None for failed items in this batch
                    batch_results[batch_idx] = [None] * len(batches[batch_idx])
        
        # Flatten results
        all_results = []
        for batch_result in batch_results:
            if batch_result is not None:
                all_results.extend(batch_result)
        
        return all_results
    
    def _process_single_batch(
        self,
        batch: List[Any],
        processor: Callable
    ) -> List[Any]:
        """
        Process a single batch of items.
        
        Args:
            batch: List of items in this batch
            processor: Function to process each item
            
        Returns:
            List of processed results for this batch
        """
        results = []
        for item in batch:
            try:
                result = processor(item)
                results.append(result)
            except Exception as e:
                logger.warning(f"Failed to process item: {e}")
                # Append None for failed items
                results.append(None)
        return results
