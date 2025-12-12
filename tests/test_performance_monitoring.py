# tests/test_performance_monitoring.py
"""
性能监控功能的单元测试

测试执行时间记录、token统计、parser统计和性能摘要生成
"""

import pytest
from datetime import datetime
from src.pipeline_runner import StepResult, PipelineResult, PipelineRunner
from src.output_parser import ParserStatistics, RetryOutputParser
from langchain_core.output_parsers import JsonOutputParser


class TestStepResult:
    """测试 StepResult 的性能监控功能"""
    
    def test_step_result_with_execution_time(self):
        """测试步骤结果包含执行时间"""
        step_result = StepResult(
            step_id="test_step",
            output_key="output",
            output_value="test output",
            execution_time=1.5,
            token_usage={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            success=True
        )
        
        assert step_result.execution_time == 1.5
        assert step_result.success is True
        
        # 验证 to_dict 包含执行时间
        result_dict = step_result.to_dict()
        assert result_dict["execution_time"] == 1.5
        assert result_dict["token_usage"]["total_tokens"] == 150
    
    def test_step_result_with_parser_stats(self):
        """测试步骤结果包含 parser 统计信息"""
        parser_stats = {
            "success_count": 1,
            "failure_count": 0,
            "total_retry_count": 2,
            "success_rate": 1.0,
            "average_retries": 2.0
        }
        
        step_result = StepResult(
            step_id="test_step",
            output_key="output",
            output_value={"result": "parsed"},
            execution_time=2.0,
            token_usage={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            parser_stats=parser_stats,
            success=True
        )
        
        assert step_result.parser_stats == parser_stats
        
        # 验证 to_dict 包含 parser 统计
        result_dict = step_result.to_dict()
        assert "parser_stats" in result_dict
        assert result_dict["parser_stats"]["success_rate"] == 1.0


class TestPipelineResult:
    """测试 PipelineResult 的性能监控功能"""
    
    def test_pipeline_result_aggregates_execution_time(self):
        """测试 Pipeline 结果聚合执行时间"""
        step1 = StepResult(
            step_id="step1",
            output_key="output1",
            output_value="output1",
            execution_time=1.0,
            token_usage={"input_tokens": 50, "output_tokens": 25, "total_tokens": 75},
            success=True
        )
        
        step2 = StepResult(
            step_id="step2",
            output_key="output2",
            output_value="output2",
            execution_time=1.5,
            token_usage={"input_tokens": 60, "output_tokens": 30, "total_tokens": 90},
            success=True
        )
        
        pipeline_result = PipelineResult(
            sample_id="test_sample",
            variant="baseline",
            step_results=[step1, step2],
            total_execution_time=2.5,
            total_token_usage={"input_tokens": 110, "output_tokens": 55, "total_tokens": 165}
        )
        
        assert pipeline_result.total_execution_time == 2.5
        assert pipeline_result.total_token_usage["total_tokens"] == 165
    
    def test_pipeline_result_aggregates_parser_stats(self):
        """测试 Pipeline 结果聚合 parser 统计"""
        parser_stats1 = {
            "success_count": 1,
            "failure_count": 0,
            "total_retry_count": 1,
            "success_rate": 1.0,
            "average_retries": 1.0
        }
        
        parser_stats2 = {
            "success_count": 1,
            "failure_count": 0,
            "total_retry_count": 2,
            "success_rate": 1.0,
            "average_retries": 2.0
        }
        
        step1 = StepResult(
            step_id="step1",
            output_key="output1",
            output_value={"result": "parsed1"},
            execution_time=1.0,
            token_usage={"input_tokens": 50, "output_tokens": 25, "total_tokens": 75},
            parser_stats=parser_stats1,
            success=True
        )
        
        step2 = StepResult(
            step_id="step2",
            output_key="output2",
            output_value={"result": "parsed2"},
            execution_time=1.5,
            token_usage={"input_tokens": 60, "output_tokens": 30, "total_tokens": 90},
            parser_stats=parser_stats2,
            success=True
        )
        
        total_parser_stats = {
            "success_count": 2,
            "failure_count": 0,
            "total_retry_count": 3,
            "success_rate": 1.0,
            "average_retries": 1.5
        }
        
        pipeline_result = PipelineResult(
            sample_id="test_sample",
            variant="baseline",
            step_results=[step1, step2],
            total_execution_time=2.5,
            total_token_usage={"input_tokens": 110, "output_tokens": 55, "total_tokens": 165},
            total_parser_stats=total_parser_stats
        )
        
        assert pipeline_result.total_parser_stats is not None
        assert pipeline_result.total_parser_stats["success_count"] == 2
        assert pipeline_result.total_parser_stats["total_retry_count"] == 3
        assert pipeline_result.total_parser_stats["average_retries"] == 1.5
    
    def test_get_performance_summary(self):
        """测试生成性能摘要"""
        step1 = StepResult(
            step_id="step1",
            output_key="output1",
            output_value="output1",
            execution_time=1.0,
            token_usage={"input_tokens": 50, "output_tokens": 25, "total_tokens": 75},
            success=True
        )
        
        step2 = StepResult(
            step_id="step2",
            output_key="output2",
            output_value="output2",
            execution_time=1.5,
            token_usage={"input_tokens": 60, "output_tokens": 30, "total_tokens": 90},
            success=True
        )
        
        pipeline_result = PipelineResult(
            sample_id="test_sample",
            variant="baseline",
            step_results=[step1, step2],
            total_execution_time=2.5,
            total_token_usage={"input_tokens": 110, "output_tokens": 55, "total_tokens": 165}
        )
        
        summary = pipeline_result.get_performance_summary(detailed=False)
        
        assert summary["sample_id"] == "test_sample"
        assert summary["variant"] == "baseline"
        assert summary["total_execution_time"] == 2.5
        assert summary["total_steps"] == 2
        assert summary["successful_steps"] == 2
        assert summary["failed_steps"] == 0
        assert summary["token_usage"]["total_tokens"] == 165
        assert summary["success"] is True
        assert "step_performance" not in summary
    
    def test_get_performance_summary_detailed(self):
        """测试生成详细性能摘要"""
        step1 = StepResult(
            step_id="step1",
            output_key="output1",
            output_value="output1",
            execution_time=1.0,
            token_usage={"input_tokens": 50, "output_tokens": 25, "total_tokens": 75},
            success=True
        )
        
        pipeline_result = PipelineResult(
            sample_id="test_sample",
            variant="baseline",
            step_results=[step1],
            total_execution_time=1.0,
            total_token_usage={"input_tokens": 50, "output_tokens": 25, "total_tokens": 75}
        )
        
        summary = pipeline_result.get_performance_summary(detailed=True)
        
        assert "step_performance" in summary
        assert len(summary["step_performance"]) == 1
        assert summary["step_performance"][0]["step_id"] == "step1"
        assert summary["step_performance"][0]["execution_time"] == 1.0


class TestParserStatistics:
    """测试 ParserStatistics 类"""
    
    def test_record_success(self):
        """测试记录成功的解析"""
        stats = ParserStatistics()
        
        stats.record_success(retry_count=0)
        assert stats.success_count == 1
        assert stats.failure_count == 0
        assert stats.total_retry_count == 0
        
        stats.record_success(retry_count=2)
        assert stats.success_count == 2
        assert stats.total_retry_count == 2
    
    def test_record_failure(self):
        """测试记录失败的解析"""
        stats = ParserStatistics()
        
        stats.record_failure(retry_count=3)
        assert stats.success_count == 0
        assert stats.failure_count == 1
        assert stats.total_retry_count == 3
    
    def test_get_success_rate(self):
        """测试计算成功率"""
        stats = ParserStatistics()
        
        # 空统计
        assert stats.get_success_rate() == 0.0
        
        # 全部成功
        stats.record_success()
        stats.record_success()
        assert stats.get_success_rate() == 1.0
        
        # 部分失败
        stats.record_failure()
        assert stats.get_success_rate() == 2/3
    
    def test_get_average_retries(self):
        """测试计算平均重试次数"""
        stats = ParserStatistics()
        
        # 空统计
        assert stats.get_average_retries() == 0.0
        
        # 有重试
        stats.record_success(retry_count=1)
        stats.record_success(retry_count=3)
        assert stats.get_average_retries() == 2.0
    
    def test_to_dict(self):
        """测试转换为字典"""
        stats = ParserStatistics()
        stats.record_success(retry_count=1)
        stats.record_success(retry_count=2)
        stats.record_failure(retry_count=3)
        
        result = stats.to_dict()
        
        assert result["success_count"] == 2
        assert result["failure_count"] == 1
        assert result["total_retry_count"] == 6
        assert result["success_rate"] == 2/3
        assert result["average_retries"] == 2.0
    
    def test_reset(self):
        """测试重置统计"""
        stats = ParserStatistics()
        stats.record_success(retry_count=1)
        stats.record_failure(retry_count=2)
        
        stats.reset()
        
        assert stats.success_count == 0
        assert stats.failure_count == 0
        assert stats.total_retry_count == 0


class TestRetryOutputParser:
    """测试 RetryOutputParser 的统计功能"""
    
    def test_parser_records_success(self):
        """测试 parser 记录成功的解析"""
        base_parser = JsonOutputParser()
        retry_parser = RetryOutputParser(parser=base_parser, max_retries=3)
        
        # 解析成功的 JSON
        result = retry_parser.parse('{"key": "value"}')
        
        assert result == {"key": "value"}
        
        stats = retry_parser.get_statistics()
        assert stats.success_count == 1
        assert stats.failure_count == 0
        assert stats.total_retry_count == 0
    
    def test_parser_records_failure(self):
        """测试 parser 记录失败的解析"""
        base_parser = JsonOutputParser()
        retry_parser = RetryOutputParser(parser=base_parser, max_retries=2)
        
        # 解析失败的 JSON
        with pytest.raises(Exception):
            retry_parser.parse('invalid json')
        
        stats = retry_parser.get_statistics()
        assert stats.success_count == 0
        assert stats.failure_count == 1
        assert stats.total_retry_count == 2  # 最大重试次数
    
    def test_parser_statistics_accumulate(self):
        """测试 parser 统计信息累积"""
        base_parser = JsonOutputParser()
        retry_parser = RetryOutputParser(parser=base_parser, max_retries=3)
        
        # 多次解析
        retry_parser.parse('{"key1": "value1"}')
        retry_parser.parse('{"key2": "value2"}')
        
        try:
            retry_parser.parse('invalid')
        except:
            pass
        
        stats = retry_parser.get_statistics()
        assert stats.success_count == 2
        assert stats.failure_count == 1
        assert stats.get_success_rate() == 2/3


class TestAggregatePerformanceSummary:
    """测试聚合性能摘要"""
    
    def test_generate_aggregate_summary_empty(self):
        """测试空结果列表的聚合摘要"""
        summary = PipelineRunner.generate_aggregate_performance_summary([])
        
        assert summary["total_samples"] == 0
        assert summary["successful_samples"] == 0
        assert summary["failed_samples"] == 0
        assert summary["total_execution_time"] == 0.0
        assert summary["success_rate"] == 0.0
    
    def test_generate_aggregate_summary_single_result(self):
        """测试单个结果的聚合摘要"""
        step1 = StepResult(
            step_id="step1",
            output_key="output1",
            output_value="output1",
            execution_time=1.0,
            token_usage={"input_tokens": 50, "output_tokens": 25, "total_tokens": 75},
            success=True
        )
        
        result = PipelineResult(
            sample_id="sample1",
            variant="baseline",
            step_results=[step1],
            total_execution_time=1.0,
            total_token_usage={"input_tokens": 50, "output_tokens": 25, "total_tokens": 75}
        )
        
        summary = PipelineRunner.generate_aggregate_performance_summary([result])
        
        assert summary["total_samples"] == 1
        assert summary["successful_samples"] == 1
        assert summary["failed_samples"] == 0
        assert summary["success_rate"] == 1.0
        assert summary["total_execution_time"] == 1.0
        assert summary["average_execution_time"] == 1.0
        assert summary["total_token_usage"]["total_tokens"] == 75
        assert summary["average_token_usage"]["total_tokens"] == 75
    
    def test_generate_aggregate_summary_multiple_results(self):
        """测试多个结果的聚合摘要"""
        result1 = PipelineResult(
            sample_id="sample1",
            variant="baseline",
            step_results=[],
            total_execution_time=1.0,
            total_token_usage={"input_tokens": 50, "output_tokens": 25, "total_tokens": 75}
        )
        
        result2 = PipelineResult(
            sample_id="sample2",
            variant="baseline",
            step_results=[],
            total_execution_time=2.0,
            total_token_usage={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
        )
        
        result3 = PipelineResult(
            sample_id="sample3",
            variant="baseline",
            step_results=[],
            total_execution_time=1.5,
            total_token_usage={"input_tokens": 75, "output_tokens": 35, "total_tokens": 110},
            error="Test error"
        )
        
        summary = PipelineRunner.generate_aggregate_performance_summary([result1, result2, result3])
        
        assert summary["total_samples"] == 3
        assert summary["successful_samples"] == 2
        assert summary["failed_samples"] == 1
        assert summary["success_rate"] == 2/3
        assert summary["total_execution_time"] == 4.5
        assert summary["average_execution_time"] == 1.5
        assert summary["total_token_usage"]["total_tokens"] == 335
        assert summary["average_token_usage"]["total_tokens"] == pytest.approx(111.67, rel=0.01)
    
    def test_generate_aggregate_summary_with_parser_stats(self):
        """测试包含 parser 统计的聚合摘要"""
        parser_stats1 = {
            "success_count": 2,
            "failure_count": 0,
            "total_retry_count": 1,
            "success_rate": 1.0,
            "average_retries": 0.5
        }
        
        parser_stats2 = {
            "success_count": 1,
            "failure_count": 1,
            "total_retry_count": 3,
            "success_rate": 0.5,
            "average_retries": 1.5
        }
        
        result1 = PipelineResult(
            sample_id="sample1",
            variant="baseline",
            step_results=[],
            total_execution_time=1.0,
            total_token_usage={"input_tokens": 50, "output_tokens": 25, "total_tokens": 75},
            total_parser_stats=parser_stats1
        )
        
        result2 = PipelineResult(
            sample_id="sample2",
            variant="baseline",
            step_results=[],
            total_execution_time=2.0,
            total_token_usage={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            total_parser_stats=parser_stats2
        )
        
        summary = PipelineRunner.generate_aggregate_performance_summary([result1, result2])
        
        assert "parser_stats" in summary
        assert summary["parser_stats"]["success_count"] == 3
        assert summary["parser_stats"]["failure_count"] == 1
        assert summary["parser_stats"]["total_retry_count"] == 4
        assert summary["parser_stats"]["success_rate"] == 0.75
        assert summary["parser_stats"]["average_retries"] == 1.0
    
    def test_generate_aggregate_summary_detailed(self):
        """测试详细的聚合摘要"""
        result1 = PipelineResult(
            sample_id="sample1",
            variant="baseline",
            step_results=[],
            total_execution_time=1.0,
            total_token_usage={"input_tokens": 50, "output_tokens": 25, "total_tokens": 75}
        )
        
        result2 = PipelineResult(
            sample_id="sample2",
            variant="baseline",
            step_results=[],
            total_execution_time=2.0,
            total_token_usage={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
        )
        
        summary = PipelineRunner.generate_aggregate_performance_summary([result1, result2], detailed=True)
        
        assert "sample_summaries" in summary
        assert len(summary["sample_summaries"]) == 2
        assert summary["sample_summaries"][0]["sample_id"] == "sample1"
        assert summary["sample_summaries"][1]["sample_id"] == "sample2"
