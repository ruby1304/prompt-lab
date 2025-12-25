# tests/test_task_38_verification.py
"""
Task 38 验证测试 - 更新 PipelineRunner 支持并发

验证 PipelineRunner 已经正确集成：
1. DependencyAnalyzer - 依赖关系分析
2. ConcurrentExecutor - 并发执行
3. 并发步骤执行 - 实现并发调度
4. 向后兼容 - 保持原有功能正常工作

Requirements: 3.4, 3.6
"""

import pytest
import time
from unittest.mock import Mock, patch
from src.pipeline_runner import PipelineRunner
from src.models import PipelineConfig, StepConfig, OutputSpec
from src.dependency_analyzer import DependencyAnalyzer
from src.concurrent_executor import ConcurrentExecutor


class TestTask38Verification:
    """Task 38 验证测试"""
    
    def test_dependency_analyzer_integrated(self):
        """验证 DependencyAnalyzer 已集成"""
        config = PipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            steps=[
                StepConfig(
                    id="step1",
                    type="agent_flow",
                    agent="test_agent",
                    flow="test_flow",
                    output_key="output1"
                )
            ],
            outputs=[OutputSpec(key="output1")]
        )
        
        runner = PipelineRunner(config)
        
        # 验证 DependencyAnalyzer 已初始化
        assert hasattr(runner, 'dependency_analyzer')
        assert isinstance(runner.dependency_analyzer, DependencyAnalyzer)
    
    def test_concurrent_executor_integrated(self):
        """验证 ConcurrentExecutor 已集成"""
        config = PipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            steps=[
                StepConfig(
                    id="step1",
                    type="agent_flow",
                    agent="test_agent",
                    flow="test_flow",
                    output_key="output1"
                )
            ],
            outputs=[OutputSpec(key="output1")]
        )
        
        runner = PipelineRunner(config)
        
        # 验证 ConcurrentExecutor 已初始化
        assert hasattr(runner, 'concurrent_executor')
        assert isinstance(runner.concurrent_executor, ConcurrentExecutor)
        
        # 验证 max_workers 配置传递正确
        assert runner.concurrent_executor.max_workers == runner.max_workers
    
    def test_concurrent_execution_configurable(self):
        """验证并发执行可配置"""
        config = PipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            steps=[
                StepConfig(
                    id="step1",
                    type="agent_flow",
                    agent="test_agent",
                    flow="test_flow",
                    output_key="output1"
                )
            ],
            outputs=[OutputSpec(key="output1")]
        )
        
        # 测试默认启用并发
        runner1 = PipelineRunner(config)
        assert runner1.enable_concurrent is True
        
        # 测试可以禁用并发
        runner2 = PipelineRunner(config, enable_concurrent=False)
        assert runner2.enable_concurrent is False
        
        # 测试可以配置 max_workers
        runner3 = PipelineRunner(config, max_workers=8)
        assert runner3.max_workers == 8
    
    @patch('src.pipeline_runner.load_agent')
    @patch('src.pipeline_runner.run_flow_with_tokens')
    def test_concurrent_step_execution_implemented(self, mock_run_flow, mock_load_agent):
        """验证并发步骤执行已实现 (Requirement 3.4)"""
        # 模拟 agent 和 flow
        mock_flow1 = Mock()
        mock_flow1.name = "flow1"
        mock_flow2 = Mock()
        mock_flow2.name = "flow2"
        
        mock_agent = Mock()
        mock_agent.flows = [mock_flow1, mock_flow2]
        mock_load_agent.return_value = mock_agent
        
        # 记录执行时间
        execution_times = []
        
        def mock_flow_execution(*args, **kwargs):
            start = time.time()
            time.sleep(0.1)  # 模拟执行时间
            execution_times.append(start)
            return "output", {"total_tokens": 100}, None
        
        mock_run_flow.side_effect = mock_flow_execution
        
        # 创建有两个独立步骤的 Pipeline
        config = PipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            steps=[
                StepConfig(
                    id="step1",
                    type="agent_flow",
                    agent="test_agent",
                    flow="flow1",
                    input_mapping={"input": "text"},
                    output_key="output1"
                ),
                StepConfig(
                    id="step2",
                    type="agent_flow",
                    agent="test_agent",
                    flow="flow2",
                    input_mapping={"input": "text"},
                    output_key="output2"
                )
            ],
            outputs=[OutputSpec(key="output1"), OutputSpec(key="output2")]
        )
        
        runner = PipelineRunner(config, enable_concurrent=True, max_workers=2)
        
        sample = {"id": "test_sample", "text": "test input"}
        result = runner.execute_sample(sample)
        
        # 验证两个步骤都执行了
        assert len(result.step_results) == 2
        assert all(step.success for step in result.step_results)
        
        # 验证并发执行（两个步骤的开始时间应该很接近）
        assert len(execution_times) == 2
        time_diff = abs(execution_times[1] - execution_times[0])
        assert time_diff < 0.05, f"独立步骤应该并发执行，但时间差为 {time_diff}秒"
    
    @patch('src.pipeline_runner.load_agent')
    @patch('src.pipeline_runner.run_flow_with_tokens')
    def test_synchronization_point_implemented(self, mock_run_flow, mock_load_agent):
        """验证同步点等待已实现 (Requirement 3.6)"""
        # 模拟 agent 和 flow
        mock_flow1 = Mock()
        mock_flow1.name = "flow1"
        mock_flow2 = Mock()
        mock_flow2.name = "flow2"
        mock_flow3 = Mock()
        mock_flow3.name = "flow3"
        
        mock_agent = Mock()
        mock_agent.flows = [mock_flow1, mock_flow2, mock_flow3]
        mock_load_agent.return_value = mock_agent
        
        # 记录执行时间和顺序
        execution_log = []
        
        def mock_flow_execution(*args, **kwargs):
            flow_name = kwargs.get('flow_name', 'unknown')
            timestamp = time.time()
            execution_log.append((flow_name, timestamp))
            time.sleep(0.1)
            return f"output_{flow_name}", {"total_tokens": 100}, None
        
        mock_run_flow.side_effect = mock_flow_execution
        
        # 创建 Pipeline: step1 和 step2 并发，step3 依赖它们（同步点）
        config = PipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            steps=[
                StepConfig(
                    id="step1",
                    type="agent_flow",
                    agent="test_agent",
                    flow="flow1",
                    input_mapping={"input": "text"},
                    output_key="output1"
                ),
                StepConfig(
                    id="step2",
                    type="agent_flow",
                    agent="test_agent",
                    flow="flow2",
                    input_mapping={"input": "text"},
                    output_key="output2"
                ),
                StepConfig(
                    id="step3",
                    type="agent_flow",
                    agent="test_agent",
                    flow="flow3",
                    input_mapping={"input1": "output1", "input2": "output2"},
                    depends_on=["step1", "step2"],  # 显式依赖 - 同步点
                    output_key="output3"
                )
            ],
            outputs=[OutputSpec(key="output3")]
        )
        
        runner = PipelineRunner(config, enable_concurrent=True, max_workers=2)
        
        sample = {"id": "test_sample", "text": "test input"}
        result = runner.execute_sample(sample)
        
        # 验证所有步骤都执行了
        assert len(result.step_results) == 3
        assert all(step.success for step in result.step_results)
        
        # 验证执行顺序：flow1 和 flow2 应该并发，flow3 应该在它们之后（同步点）
        assert len(execution_log) == 3
        
        flow1_time = next(t for name, t in execution_log if name == "flow1")
        flow2_time = next(t for name, t in execution_log if name == "flow2")
        flow3_time = next(t for name, t in execution_log if name == "flow3")
        
        # flow1 和 flow2 应该几乎同时开始（并发执行）
        assert abs(flow1_time - flow2_time) < 0.05, "flow1 和 flow2 应该并发执行"
        
        # flow3 应该在 flow1 和 flow2 之后开始（同步点等待）
        assert flow3_time > flow1_time + 0.08, "flow3 应该在 flow1 完成后执行（同步点）"
        assert flow3_time > flow2_time + 0.08, "flow3 应该在 flow2 完成后执行（同步点）"
    
    @patch('src.pipeline_runner.load_agent')
    @patch('src.pipeline_runner.run_flow_with_tokens')
    def test_backward_compatibility_maintained(self, mock_run_flow, mock_load_agent):
        """验证向后兼容性已保持"""
        # 模拟 agent 和 flow
        mock_flow1 = Mock()
        mock_flow1.name = "flow1"
        mock_flow2 = Mock()
        mock_flow2.name = "flow2"
        
        mock_agent = Mock()
        mock_agent.flows = [mock_flow1, mock_flow2]
        mock_load_agent.return_value = mock_agent
        
        mock_run_flow.return_value = ("output", {"total_tokens": 100}, None)
        
        config = PipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            steps=[
                StepConfig(
                    id="step1",
                    type="agent_flow",
                    agent="test_agent",
                    flow="flow1",
                    input_mapping={"input": "text"},
                    output_key="output1"
                ),
                StepConfig(
                    id="step2",
                    type="agent_flow",
                    agent="test_agent",
                    flow="flow2",
                    input_mapping={"input": "output1"},
                    output_key="output2"
                )
            ],
            outputs=[OutputSpec(key="output2")]
        )
        
        # 测试顺序执行模式（向后兼容）
        runner = PipelineRunner(config, enable_concurrent=False)
        
        sample = {"id": "test_sample", "text": "test input"}
        result = runner.execute_sample(sample)
        
        # 验证顺序执行成功
        assert len(result.step_results) == 2
        assert all(step.success for step in result.step_results)
        assert result.error is None
        
        # 验证数据传递正确
        assert result.step_results[0].output_key == "output1"
        assert result.step_results[1].output_key == "output2"
    
    def test_execute_sample_concurrent_method_exists(self):
        """验证 _execute_sample_concurrent 方法存在"""
        config = PipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            steps=[
                StepConfig(
                    id="step1",
                    type="agent_flow",
                    agent="test_agent",
                    flow="test_flow",
                    output_key="output1"
                )
            ],
            outputs=[OutputSpec(key="output1")]
        )
        
        runner = PipelineRunner(config)
        
        # 验证并发执行方法存在
        assert hasattr(runner, '_execute_sample_concurrent')
        assert callable(runner._execute_sample_concurrent)
    
    def test_execute_sample_sequential_method_exists(self):
        """验证 _execute_sample_sequential 方法存在（向后兼容）"""
        config = PipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            steps=[
                StepConfig(
                    id="step1",
                    type="agent_flow",
                    agent="test_agent",
                    flow="test_flow",
                    output_key="output1"
                )
            ],
            outputs=[OutputSpec(key="output1")]
        )
        
        runner = PipelineRunner(config)
        
        # 验证顺序执行方法存在
        assert hasattr(runner, '_execute_sample_sequential')
        assert callable(runner._execute_sample_sequential)
    
    @patch('src.pipeline_runner.load_agent')
    @patch('src.pipeline_runner.run_flow_with_tokens')
    def test_execute_sample_routes_correctly(self, mock_run_flow, mock_load_agent):
        """验证 execute_sample 正确路由到并发或顺序执行"""
        # 模拟 agent 和 flow
        mock_flow = Mock()
        mock_flow.name = "test_flow"
        
        mock_agent = Mock()
        mock_agent.flows = [mock_flow]
        mock_load_agent.return_value = mock_agent
        
        mock_run_flow.return_value = ("output", {"total_tokens": 100}, None)
        
        config = PipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            steps=[
                StepConfig(
                    id="step1",
                    type="agent_flow",
                    agent="test_agent",
                    flow="test_flow",
                    input_mapping={"input": "text"},
                    output_key="output1"
                )
            ],
            outputs=[OutputSpec(key="output1")]
        )
        
        # 测试并发模式
        runner_concurrent = PipelineRunner(config, enable_concurrent=True)
        sample = {"id": "test_sample", "text": "test input"}
        result_concurrent = runner_concurrent.execute_sample(sample)
        assert result_concurrent.error is None
        
        # 测试顺序模式
        runner_sequential = PipelineRunner(config, enable_concurrent=False)
        result_sequential = runner_sequential.execute_sample(sample)
        assert result_sequential.error is None
        
        # 两种模式都应该产生相同的结果
        assert len(result_concurrent.step_results) == len(result_sequential.step_results)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
