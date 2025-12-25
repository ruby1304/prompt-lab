# tests/test_pipeline_concurrent_scheduling.py
"""
测试 Pipeline 并发执行调度功能

验证 PipelineRunner 的并发执行调度实现，包括：
- 依赖关系分析
- 并发组调度
- 同步点等待
- 最大并发数控制
"""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from src.pipeline_runner import PipelineRunner, PipelineResult, StepResult
from src.models import PipelineConfig, StepConfig, OutputSpec


class TestPipelineConcurrentScheduling:
    """测试 Pipeline 并发执行调度"""
    
    def test_concurrent_execution_enabled_by_default(self):
        """测试并发执行默认启用"""
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
        assert runner.enable_concurrent is True
        assert runner.max_workers == 4
    
    def test_concurrent_execution_can_be_disabled(self):
        """测试可以禁用并发执行"""
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
        
        runner = PipelineRunner(config, enable_concurrent=False)
        assert runner.enable_concurrent is False
    
    def test_max_workers_configurable(self):
        """测试最大并发数可配置"""
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
        
        runner = PipelineRunner(config, max_workers=8)
        assert runner.max_workers == 8
        assert runner.concurrent_executor.max_workers == 8
    
    @patch('src.pipeline_runner.load_agent')
    @patch('src.pipeline_runner.run_flow_with_tokens')
    def test_independent_steps_execute_concurrently(self, mock_run_flow, mock_load_agent):
        """测试独立步骤并发执行"""
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
        assert time_diff < 0.05, f"步骤应该并发执行，但时间差为 {time_diff}秒"
    
    @patch('src.pipeline_runner.load_agent')
    @patch('src.pipeline_runner.run_flow_with_tokens')
    def test_dependent_steps_execute_sequentially(self, mock_run_flow, mock_load_agent):
        """测试有依赖关系的步骤顺序执行"""
        # 模拟 agent 和 flow
        mock_flow1 = Mock()
        mock_flow1.name = "flow1"
        mock_flow2 = Mock()
        mock_flow2.name = "flow2"
        
        mock_agent = Mock()
        mock_agent.flows = [mock_flow1, mock_flow2]
        mock_load_agent.return_value = mock_agent
        
        # 记录执行顺序
        execution_order = []
        
        def mock_flow_execution(*args, **kwargs):
            flow_name = kwargs.get('flow_name', 'unknown')
            execution_order.append(flow_name)
            time.sleep(0.05)
            return f"output_{flow_name}", {"total_tokens": 100}, None
        
        mock_run_flow.side_effect = mock_flow_execution
        
        # 创建有依赖关系的 Pipeline
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
                    input_mapping={"input": "output1"},  # 依赖 step1
                    output_key="output2"
                )
            ],
            outputs=[OutputSpec(key="output2")]
        )
        
        runner = PipelineRunner(config, enable_concurrent=True)
        
        sample = {"id": "test_sample", "text": "test input"}
        result = runner.execute_sample(sample)
        
        # 验证执行顺序
        assert execution_order == ["flow1", "flow2"], "依赖步骤应该按顺序执行"
        assert len(result.step_results) == 2
        assert all(step.success for step in result.step_results)
    
    @patch('src.pipeline_runner.load_agent')
    @patch('src.pipeline_runner.run_flow_with_tokens')
    def test_concurrent_groups_with_synchronization(self, mock_run_flow, mock_load_agent):
        """测试并发组和同步点"""
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
        
        # 创建 Pipeline: step1 和 step2 并发，step3 依赖它们
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
                    depends_on=["step1", "step2"],  # 显式依赖
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
        
        # 验证执行顺序：flow1 和 flow2 应该并发，flow3 应该在它们之后
        assert len(execution_log) == 3
        
        flow1_time = next(t for name, t in execution_log if name == "flow1")
        flow2_time = next(t for name, t in execution_log if name == "flow2")
        flow3_time = next(t for name, t in execution_log if name == "flow3")
        
        # flow1 和 flow2 应该几乎同时开始
        assert abs(flow1_time - flow2_time) < 0.05, "flow1 和 flow2 应该并发执行"
        
        # flow3 应该在 flow1 和 flow2 之后开始
        assert flow3_time > flow1_time + 0.08, "flow3 应该在 flow1 完成后执行"
        assert flow3_time > flow2_time + 0.08, "flow3 应该在 flow2 完成后执行"
    
    @patch('src.pipeline_runner.load_agent')
    @patch('src.pipeline_runner.run_flow_with_tokens')
    def test_max_concurrency_control(self, mock_run_flow, mock_load_agent):
        """测试最大并发数控制"""
        # 模拟 agent 和 flow
        mock_flows = []
        for i in range(1, 5):
            mock_flow = Mock()
            mock_flow.name = f"flow{i}"
            mock_flows.append(mock_flow)
        
        mock_agent = Mock()
        mock_agent.flows = mock_flows
        mock_load_agent.return_value = mock_agent
        
        # 记录同时执行的任务数
        concurrent_count = []
        current_count = 0
        lock = __import__('threading').Lock()
        
        def mock_flow_execution(*args, **kwargs):
            nonlocal current_count
            with lock:
                current_count += 1
                concurrent_count.append(current_count)
            
            time.sleep(0.1)
            
            with lock:
                current_count -= 1
            
            flow_name = kwargs.get('flow_name', 'unknown')
            return f"output_{flow_name}", {"total_tokens": 100}, None
        
        mock_run_flow.side_effect = mock_flow_execution
        
        # 创建有4个独立步骤的 Pipeline
        config = PipelineConfig(
            id="test_pipeline",
            name="Test Pipeline",
            steps=[
                StepConfig(
                    id=f"step{i}",
                    type="agent_flow",
                    agent="test_agent",
                    flow=f"flow{i}",
                    input_mapping={"input": "text"},
                    output_key=f"output{i}"
                )
                for i in range(1, 5)
            ],
            outputs=[OutputSpec(key="output1")]
        )
        
        # 设置最大并发数为2
        runner = PipelineRunner(config, enable_concurrent=True, max_workers=2)
        
        sample = {"id": "test_sample", "text": "test input"}
        result = runner.execute_sample(sample)
        
        # 验证所有步骤都执行了
        assert len(result.step_results) == 4
        assert all(step.success for step in result.step_results)
        
        # 验证最大并发数不超过2
        max_concurrent = max(concurrent_count)
        assert max_concurrent <= 2, f"最大并发数应该不超过2，但实际为 {max_concurrent}"
    
    @patch('src.pipeline_runner.load_agent')
    @patch('src.pipeline_runner.run_flow_with_tokens')
    def test_failed_required_step_stops_dependents(self, mock_run_flow, mock_load_agent):
        """测试必需步骤失败时停止依赖步骤"""
        # 模拟 agent 和 flow
        mock_flow1 = Mock()
        mock_flow1.name = "flow1"
        mock_flow2 = Mock()
        mock_flow2.name = "flow2"
        
        mock_agent = Mock()
        mock_agent.flows = [mock_flow1, mock_flow2]
        mock_load_agent.return_value = mock_agent
        
        # step1 失败，step2 依赖 step1
        def mock_flow_execution(*args, **kwargs):
            flow_name = kwargs.get('flow_name', 'unknown')
            if flow_name == "flow1":
                raise Exception("Step 1 failed")
            return f"output_{flow_name}", {"total_tokens": 100}, None
        
        mock_run_flow.side_effect = mock_flow_execution
        
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
                    output_key="output1",
                    required=True
                ),
                StepConfig(
                    id="step2",
                    type="agent_flow",
                    agent="test_agent",
                    flow="flow2",
                    input_mapping={"input": "output1"},
                    output_key="output2",
                    required=True  # 也设置为必需，这样当它被跳过时会失败
                )
            ],
            outputs=[OutputSpec(key="output2")]
        )
        
        runner = PipelineRunner(config, enable_concurrent=True)
        
        sample = {"id": "test_sample", "text": "test input"}
        result = runner.execute_sample(sample)
        
        # 验证 step1 失败
        assert not result.step_results[0].success
        
        # 验证 step2 被跳过
        assert not result.step_results[1].success
        assert "依赖" in result.step_results[1].error
        
        # 验证整个 pipeline 失败（因为 step1 是必需的且失败了）
        assert result.error is not None
        assert "必需步骤" in result.error
    
    @patch('src.pipeline_runner.load_agent')
    @patch('src.pipeline_runner.run_flow_with_tokens')
    def test_failed_optional_step_continues_execution(self, mock_run_flow, mock_load_agent):
        """测试可选步骤失败时继续执行"""
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
        
        # step1 失败但是可选的，step2 和 step3 独立
        def mock_flow_execution(*args, **kwargs):
            flow_name = kwargs.get('flow_name', 'unknown')
            if flow_name == "flow1":
                raise Exception("Step 1 failed")
            return f"output_{flow_name}", {"total_tokens": 100}, None
        
        mock_run_flow.side_effect = mock_flow_execution
        
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
                    output_key="output1",
                    required=False  # 可选步骤
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
                    input_mapping={"input": "text"},
                    output_key="output3"
                )
            ],
            outputs=[OutputSpec(key="output2"), OutputSpec(key="output3")]
        )
        
        runner = PipelineRunner(config, enable_concurrent=True)
        
        sample = {"id": "test_sample", "text": "test input"}
        result = runner.execute_sample(sample)
        
        # 验证 step1 失败
        assert not result.step_results[0].success
        
        # 验证 step2 和 step3 成功执行
        assert result.step_results[1].success
        assert result.step_results[2].success
        
        # 验证整个 pipeline 成功（因为 step1 是可选的）
        assert result.error is None
    
    @patch('src.pipeline_runner.load_agent')
    @patch('src.pipeline_runner.run_flow_with_tokens')
    def test_sequential_mode_still_works(self, mock_run_flow, mock_load_agent):
        """测试顺序执行模式仍然正常工作"""
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
        
        # 禁用并发执行
        runner = PipelineRunner(config, enable_concurrent=False)
        
        sample = {"id": "test_sample", "text": "test input"}
        result = runner.execute_sample(sample)
        
        # 验证顺序执行成功
        assert len(result.step_results) == 2
        assert all(step.success for step in result.step_results)
        assert result.error is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
