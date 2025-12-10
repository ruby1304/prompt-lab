# tests/test_pipeline_runner.py
"""
PipelineRunner 单元测试
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.pipeline_runner import (
    PipelineRunner, StepResult, PipelineResult, 
    PipelineExecutionError, create_progress_printer
)
from src.models import PipelineConfig, StepConfig
from src.error_handler import ConfigError, ExecutionError


class TestStepResult:
    """测试 StepResult 类"""
    
    def test_step_result_creation(self):
        """测试 StepResult 创建"""
        result = StepResult(
            step_id="test_step",
            output_key="output",
            output_value="test output",
            execution_time=1.5,
            token_usage={"input_tokens": 100, "output_tokens": 50}
        )
        
        assert result.step_id == "test_step"
        assert result.output_key == "output"
        assert result.output_value == "test output"
        assert result.execution_time == 1.5
        assert result.token_usage["input_tokens"] == 100
        assert result.error is None
    
    def test_step_result_to_dict(self):
        """测试 StepResult 转换为字典"""
        result = StepResult(
            step_id="test_step",
            output_key="output",
            output_value="test output",
            execution_time=1.5,
            error="test error"
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["step_id"] == "test_step"
        assert result_dict["output_key"] == "output"
        assert result_dict["output_value"] == "test output"
        assert result_dict["execution_time"] == 1.5
        assert result_dict["error"] == "test error"


class TestPipelineResult:
    """测试 PipelineResult 类"""
    
    def test_pipeline_result_creation(self):
        """测试 PipelineResult 创建"""
        result = PipelineResult(
            sample_id="sample1",
            variant="baseline"
        )
        
        assert result.sample_id == "sample1"
        assert result.variant == "baseline"
        assert result.step_results == []
        assert result.total_execution_time == 0.0
        assert result.error is None
        assert isinstance(result.created_at, datetime)
    
    def test_pipeline_result_to_dict(self):
        """测试 PipelineResult 转换为字典"""
        step_result = StepResult(
            step_id="step1",
            output_key="output",
            output_value="test",
            execution_time=1.0
        )
        
        result = PipelineResult(
            sample_id="sample1",
            variant="baseline",
            step_results=[step_result],
            total_execution_time=2.0,
            error="test error"
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["sample_id"] == "sample1"
        assert result_dict["variant"] == "baseline"
        assert len(result_dict["step_results"]) == 1
        assert result_dict["total_execution_time"] == 2.0
        assert result_dict["error"] == "test error"
        assert "created_at" in result_dict


class TestPipelineRunner:
    """测试 PipelineRunner 类"""
    
    def test_pipeline_runner_initialization(self, sample_pipeline_config):
        """测试 PipelineRunner 初始化"""
        runner = PipelineRunner(sample_pipeline_config)
        
        assert runner.config == sample_pipeline_config
        assert runner.context == {}
        assert runner.progress_callback is None
    
    def test_pipeline_runner_invalid_config(self):
        """测试无效配置的处理"""
        # 创建无效配置（缺少必需字段）
        invalid_config = PipelineConfig(
            id="",  # 空 ID
            name="",  # 空名称
            description="",
            default_testset="",
            inputs=[],
            steps=[],  # 空步骤列表
            outputs=[],
            baseline=None,
            variants={}
        )
        
        with pytest.raises(ConfigError):
            PipelineRunner(invalid_config)
    
    def test_set_progress_callback(self, sample_pipeline_config):
        """测试设置进度回调"""
        runner = PipelineRunner(sample_pipeline_config)
        callback = Mock()
        
        runner.set_progress_callback(callback)
        assert runner.progress_callback == callback
    
    def test_execute_empty_samples(self, sample_pipeline_config):
        """测试执行空样本列表"""
        runner = PipelineRunner(sample_pipeline_config)
        results = runner.execute([])
        
        assert results == []
    
    def test_execute_single_sample(self, sample_pipeline_config, sample_testset, 
                                  mock_load_agent, mock_run_flow_with_tokens):
        """测试执行单个样本"""
        runner = PipelineRunner(sample_pipeline_config)
        
        results = runner.execute([sample_testset[0]], use_progress_tracker=False)
        
        assert len(results) == 1
        result = results[0]
        assert result.sample_id == "sample1"
        assert result.variant == "baseline"
        assert len(result.step_results) == 2
        assert result.error is None
        assert result.total_execution_time > 0
    
    def test_execute_multiple_samples(self, sample_pipeline_config, sample_testset,
                                    mock_load_agent, mock_run_flow_with_tokens):
        """测试执行多个样本"""
        runner = PipelineRunner(sample_pipeline_config)
        
        results = runner.execute(sample_testset, use_progress_tracker=False)
        
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.sample_id == sample_testset[i]["id"]
            assert result.variant == "baseline"
            assert len(result.step_results) == 2
    
    def test_execute_with_variant(self, sample_pipeline_config, sample_testset,
                                mock_load_agent, mock_run_flow_with_tokens):
        """测试执行指定变体"""
        runner = PipelineRunner(sample_pipeline_config)
        
        results = runner.execute([sample_testset[0]], variant="variant1", 
                               use_progress_tracker=False)
        
        assert len(results) == 1
        result = results[0]
        assert result.variant == "variant1"
        # 验证第一个步骤使用了变体的 flow
        assert "variant_flow" in result.step_results[0].output_value
    
    def test_execute_with_progress_callback(self, sample_pipeline_config, sample_testset,
                                          mock_load_agent, mock_run_flow_with_tokens):
        """测试带进度回调的执行"""
        runner = PipelineRunner(sample_pipeline_config)
        progress_calls = []
        
        def progress_callback(current, total, message):
            progress_calls.append((current, total, message))
        
        runner.set_progress_callback(progress_callback)
        runner.execute([sample_testset[0]], use_progress_tracker=False)
        
        # 验证进度回调被调用
        assert len(progress_calls) >= 2  # 至少开始和结束
        assert progress_calls[-1][0] == progress_calls[-1][1]  # 最后一次调用表示完成
    
    def test_execute_sample_success(self, sample_pipeline_config, sample_testset,
                                   mock_load_agent, mock_run_flow_with_tokens):
        """测试成功执行单个样本"""
        runner = PipelineRunner(sample_pipeline_config)
        
        result = runner.execute_sample(sample_testset[0])
        
        assert result.sample_id == "sample1"
        assert result.variant == "baseline"
        assert len(result.step_results) == 2
        assert result.error is None
        assert result.total_execution_time > 0
        assert "step1_output" in result.final_outputs
        assert "step2_output" in result.final_outputs
    
    def test_execute_sample_with_variant(self, sample_pipeline_config, sample_testset,
                                       mock_load_agent, mock_run_flow_with_tokens):
        """测试执行样本时使用变体"""
        runner = PipelineRunner(sample_pipeline_config)
        
        result = runner.execute_sample(sample_testset[0], variant="variant1")
        
        assert result.variant == "variant1"
        # 验证第一个步骤使用了变体配置
        assert "variant_flow" in result.step_results[0].output_value
    
    def test_execute_step_success(self, sample_pipeline_config, mock_load_agent, 
                                mock_run_flow_with_tokens):
        """测试成功执行单个步骤"""
        runner = PipelineRunner(sample_pipeline_config)
        runner.context = {
            "sample": {"id": "test", "input_text": "test input"},
            "testset_fields": {"input_text": "test input"}
        }
        
        step = sample_pipeline_config.steps[0]
        result = runner.execute_step(step)
        
        assert result.step_id == "step1"
        assert result.output_key == "step1_output"
        assert result.error is None
        assert result.execution_time > 0
        assert "test_flow" in result.output_value
    
    def test_execute_step_with_missing_input(self, sample_pipeline_config, 
                                           mock_load_agent, mock_run_flow_with_tokens):
        """测试步骤执行时输入映射缺失"""
        runner = PipelineRunner(sample_pipeline_config)
        runner.context = {
            "sample": {"id": "test"},
            "testset_fields": {}  # 缺少 input_text
        }
        
        step = sample_pipeline_config.steps[0]
        result = runner.execute_step(step)
        
        # 应该使用空字符串作为默认值，不应该失败
        assert result.error is None
        assert result.output_value is not None
    
    def test_resolve_input_mapping(self, sample_pipeline_config):
        """测试输入映射解析"""
        runner = PipelineRunner(sample_pipeline_config)
        runner.context = {
            "testset_fields": {"input_text": "原始输入"},
            "step1_output": "步骤1输出"
        }
        
        # 测试从 testset 字段映射
        mapping1 = {"text": "input_text"}
        resolved1 = runner._resolve_input_mapping(mapping1)
        assert resolved1["text"] == "原始输入"
        
        # 测试从步骤输出映射
        mapping2 = {"text": "step1_output"}
        resolved2 = runner._resolve_input_mapping(mapping2)
        assert resolved2["text"] == "步骤1输出"
        
        # 测试缺失的映射源
        mapping3 = {"text": "nonexistent"}
        resolved3 = runner._resolve_input_mapping(mapping3)
        assert resolved3["text"] == ""
    
    def test_resolve_step_config_baseline(self, sample_pipeline_config):
        """测试解析步骤配置（基线）"""
        runner = PipelineRunner(sample_pipeline_config)
        
        step = sample_pipeline_config.steps[0]
        flow_name, model_override = runner._resolve_step_config(step, None)
        
        # 应该使用 baseline 配置
        assert flow_name == "baseline_flow"
        assert model_override is None
    
    def test_resolve_step_config_variant(self, sample_pipeline_config):
        """测试解析步骤配置（变体）"""
        runner = PipelineRunner(sample_pipeline_config)
        
        variant_config = sample_pipeline_config.variants["variant1"]
        step = sample_pipeline_config.steps[0]
        flow_name, model_override = runner._resolve_step_config(step, variant_config)
        
        # 应该使用变体覆盖
        assert flow_name == "variant_flow"
        assert model_override is None
    
    def test_get_variant_config_baseline(self, sample_pipeline_config):
        """测试获取基线变体配置"""
        runner = PipelineRunner(sample_pipeline_config)
        
        config = runner._get_variant_config("baseline")
        assert config is None
    
    def test_get_variant_config_existing(self, sample_pipeline_config):
        """测试获取存在的变体配置"""
        runner = PipelineRunner(sample_pipeline_config)
        
        config = runner._get_variant_config("variant1")
        assert config is not None
        assert config.description == "变体1"
    
    def test_get_variant_config_nonexistent(self, sample_pipeline_config):
        """测试获取不存在的变体配置"""
        runner = PipelineRunner(sample_pipeline_config)
        
        with pytest.raises(ConfigError):
            runner._get_variant_config("nonexistent")
    
    def test_collect_final_outputs(self, sample_pipeline_config):
        """测试收集最终输出"""
        runner = PipelineRunner(sample_pipeline_config)
        runner.context = {
            "step1_output": "步骤1输出",
            "step2_output": "步骤2输出"
        }
        
        outputs = runner._collect_final_outputs()
        
        assert "step2_output" in outputs
        assert outputs["step2_output"] == "步骤2输出"
    
    def test_calculate_total_token_usage(self, sample_pipeline_config):
        """测试计算总token使用量"""
        runner = PipelineRunner(sample_pipeline_config)
        
        step_results = [
            StepResult(
                step_id="step1",
                output_key="output1",
                output_value="test",
                execution_time=1.0,
                token_usage={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150}
            ),
            StepResult(
                step_id="step2",
                output_key="output2",
                output_value="test",
                execution_time=1.0,
                token_usage={"input_tokens": 80, "output_tokens": 40, "total_tokens": 120}
            )
        ]
        
        total_usage = runner._calculate_total_token_usage(step_results)
        
        assert total_usage["input_tokens"] == 180
        assert total_usage["output_tokens"] == 90
        assert total_usage["total_tokens"] == 270
    
    def test_validate_pipeline_success(self, sample_pipeline_config, mock_load_agent):
        """测试成功的 pipeline 验证"""
        runner = PipelineRunner(sample_pipeline_config)
        
        errors = runner.validate_pipeline()
        
        assert errors == []
    
    def test_validate_pipeline_missing_agent(self, sample_pipeline_config, monkeypatch):
        """测试验证缺失的 agent"""
        def mock_load_agent(agent_id):
            raise ValueError(f"Agent not found: {agent_id}")
        
        monkeypatch.setattr("src.agent_registry.load_agent", mock_load_agent)
        
        runner = PipelineRunner(sample_pipeline_config)
        errors = runner.validate_pipeline()
        
        assert len(errors) > 0
        assert any("agent" in error.lower() for error in errors)
    
    def test_execute_with_step_failure(self, sample_pipeline_config, sample_testset,
                                     mock_load_agent, monkeypatch):
        """测试步骤执行失败的处理"""
        def failing_run_flow(*args, **kwargs):
            raise Exception("模拟执行失败")
        
        monkeypatch.setattr("src.chains.run_flow_with_tokens", failing_run_flow)
        
        runner = PipelineRunner(sample_pipeline_config)
        results = runner.execute([sample_testset[0]], use_progress_tracker=False)
        
        assert len(results) == 1
        result = results[0]
        assert result.error is not None
        assert "执行失败" in result.error


class TestProgressPrinter:
    """测试进度打印器"""
    
    def test_create_progress_printer(self):
        """测试创建进度打印器"""
        printer = create_progress_printer("test_pipeline")
        
        assert callable(printer)
    
    @patch('builtins.print')
    def test_progress_printer_output(self, mock_print):
        """测试进度打印器输出"""
        printer = create_progress_printer("test_pipeline")
        
        # 测试中间进度
        printer(5, 10, "处理中")
        mock_print.assert_called_with(
            "\r正在执行 Pipeline: test_pipeline [5/10] 50.0% 处理中",
            end="", flush=True
        )
        
        # 测试完成进度
        printer(10, 10, "完成")
        # 完成时应该有换行
        assert mock_print.call_count == 2