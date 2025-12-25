# tests/test_pipeline_runner_code_nodes.py
"""
PipelineRunner 代码节点集成测试

测试 PipelineRunner 与 CodeExecutor 的集成，验证代码节点的执行功能。
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.pipeline_runner import PipelineRunner, StepResult, PipelineResult
from src.models import PipelineConfig, StepConfig, CodeNodeConfig, InputSpec, OutputSpec
from src.code_executor import CodeExecutor, ExecutionResult as CodeExecutionResult
from src.error_handler import ExecutionError


@pytest.fixture
def simple_code_node_config():
    """创建简单的代码节点配置"""
    return CodeNodeConfig(
        language="python",
        code="""
def transform(inputs):
    return {"result": inputs.get("value", 0) * 2}
""",
        timeout=10
    )


@pytest.fixture
def pipeline_with_code_node(simple_code_node_config):
    """创建包含代码节点的 Pipeline 配置"""
    return PipelineConfig(
        id="test_code_pipeline",
        name="测试代码节点 Pipeline",
        description="包含代码节点的测试 Pipeline",
        default_testset="test.jsonl",
        inputs=[
            InputSpec(name="input_value", desc="输入值")
        ],
        steps=[
            StepConfig(
                id="code_step",
                type="code_node",
                code_config=simple_code_node_config,
                input_mapping={"value": "input_value"},
                output_key="code_output",
                required=True
            )
        ],
        outputs=[
            OutputSpec(key="code_output", label="代码输出")
        ],
        baseline=None,
        variants={}
    )


@pytest.fixture
def pipeline_with_agent_and_code():
    """创建包含 Agent 和代码节点的混合 Pipeline"""
    return PipelineConfig(
        id="test_mixed_pipeline",
        name="混合 Pipeline",
        description="包含 Agent 和代码节点的 Pipeline",
        default_testset="test.jsonl",
        inputs=[
            InputSpec(name="text", desc="输入文本")
        ],
        steps=[
            # Agent 步骤
            StepConfig(
                id="agent_step",
                type="agent_flow",
                agent="test_agent",
                flow="test_flow",
                input_mapping={"input": "text"},
                output_key="agent_output",
                required=True
            ),
            # 代码节点步骤
            StepConfig(
                id="transform_step",
                type="code_node",
                code_config=CodeNodeConfig(
                    language="python",
                    code="""
def transform(inputs):
    text = inputs.get("text", "")
    return {"transformed": text.upper()}
""",
                    timeout=10
                ),
                input_mapping={"text": "agent_output"},
                output_key="final_output",
                required=True
            )
        ],
        outputs=[
            OutputSpec(key="final_output", label="最终输出")
        ],
        baseline=None,
        variants={}
    )


class TestPipelineRunnerCodeNodes:
    """测试 PipelineRunner 的代码节点功能"""
    
    def test_code_executor_initialization(self, pipeline_with_code_node):
        """测试 PipelineRunner 初始化时创建 CodeExecutor"""
        runner = PipelineRunner(pipeline_with_code_node)
        
        assert hasattr(runner, 'code_executor')
        assert isinstance(runner.code_executor, CodeExecutor)
        assert runner.code_executor.default_timeout == 30
    
    def test_execute_simple_code_node(self, pipeline_with_code_node):
        """测试执行简单的代码节点"""
        runner = PipelineRunner(pipeline_with_code_node)
        
        # 准备测试样本
        sample = {
            "id": "test_sample",
            "input_value": 5
        }
        
        # 执行 Pipeline
        result = runner.execute_sample(sample, variant="baseline")
        
        # 验证结果
        assert result.sample_id == "test_sample"
        assert result.error is None
        assert len(result.step_results) == 1
        
        step_result = result.step_results[0]
        assert step_result.step_id == "code_step"
        assert step_result.success is True
        assert step_result.output_value == {"result": 10}
        assert step_result.token_usage == {}  # 代码节点不使用 token
    
    def test_execute_javascript_code_node(self):
        """测试执行 JavaScript 代码节点"""
        config = PipelineConfig(
            id="test_js_pipeline",
            name="JavaScript Pipeline",
            description="测试 JavaScript 代码节点",
            default_testset="test.jsonl",
            inputs=[InputSpec(name="numbers", desc="数字列表")],
            steps=[
                StepConfig(
                    id="js_step",
                    type="code_node",
                    code_config=CodeNodeConfig(
                        language="javascript",
                        code="""
function transform(inputs) {
    const numbers = inputs.numbers || [];
    return { sum: numbers.reduce((a, b) => a + b, 0) };
}
module.exports = transform;
""",
                        timeout=10
                    ),
                    input_mapping={"numbers": "numbers"},
                    output_key="js_output",
                    required=True
                )
            ],
            outputs=[OutputSpec(key="js_output", label="JS 输出")],
            baseline=None,
            variants={}
        )
        
        runner = PipelineRunner(config)
        sample = {
            "id": "test_js",
            "numbers": [1, 2, 3, 4, 5]
        }
        
        result = runner.execute_sample(sample, variant="baseline")
        
        assert result.error is None
        assert result.step_results[0].output_value == {"sum": 15}
    
    def test_code_node_with_backward_compatibility(self):
        """测试代码节点的向后兼容性（直接在 step 中指定字段）"""
        config = PipelineConfig(
            id="test_compat_pipeline",
            name="向后兼容 Pipeline",
            description="测试向后兼容的代码节点配置",
            default_testset="test.jsonl",
            inputs=[InputSpec(name="value", desc="值")],
            steps=[
                StepConfig(
                    id="compat_step",
                    type="code_node",
                    language="python",  # 直接指定
                    code="def transform(inputs): return {'doubled': inputs['value'] * 2}",  # 直接指定
                    timeout=10,
                    input_mapping={"value": "value"},
                    output_key="output",
                    required=True
                )
            ],
            outputs=[OutputSpec(key="output", label="输出")],
            baseline=None,
            variants={}
        )
        
        runner = PipelineRunner(config)
        sample = {"id": "test", "value": 7}
        
        result = runner.execute_sample(sample, variant="baseline")
        
        assert result.error is None
        assert result.step_results[0].output_value == {"doubled": 14}
    
    def test_code_node_timeout_handling(self):
        """测试代码节点超时处理"""
        config = PipelineConfig(
            id="test_timeout_pipeline",
            name="超时测试 Pipeline",
            description="测试代码节点超时",
            default_testset="test.jsonl",
            inputs=[InputSpec(name="value", desc="值")],
            steps=[
                StepConfig(
                    id="timeout_step",
                    type="code_node",
                    code_config=CodeNodeConfig(
                        language="python",
                        code="""
import time
def transform(inputs):
    time.sleep(5)  # 睡眠 5 秒
    return {"result": "done"}
""",
                        timeout=1  # 超时设置为 1 秒
                    ),
                    input_mapping={"value": "value"},
                    output_key="output",
                    required=True
                )
            ],
            outputs=[OutputSpec(key="output", label="输出")],
            baseline=None,
            variants={}
        )
        
        runner = PipelineRunner(config)
        sample = {"id": "test", "value": 1}
        
        result = runner.execute_sample(sample, variant="baseline")
        
        # 应该失败，因为超时
        assert result.error is not None
        assert "超时" in result.error or "timeout" in result.error.lower()
        assert result.step_results[0].success is False
    
    def test_code_node_error_handling(self):
        """测试代码节点错误处理"""
        config = PipelineConfig(
            id="test_error_pipeline",
            name="错误测试 Pipeline",
            description="测试代码节点错误处理",
            default_testset="test.jsonl",
            inputs=[InputSpec(name="value", desc="值")],
            steps=[
                StepConfig(
                    id="error_step",
                    type="code_node",
                    code_config=CodeNodeConfig(
                        language="python",
                        code="""
def transform(inputs):
    raise ValueError("测试错误")
""",
                        timeout=10
                    ),
                    input_mapping={"value": "value"},
                    output_key="output",
                    required=True
                )
            ],
            outputs=[OutputSpec(key="output", label="输出")],
            baseline=None,
            variants={}
        )
        
        runner = PipelineRunner(config)
        sample = {"id": "test", "value": 1}
        
        result = runner.execute_sample(sample, variant="baseline")
        
        # 应该失败
        assert result.error is not None
        assert result.step_results[0].success is False
        assert result.step_results[0].error is not None
    
    def test_optional_code_node_failure(self):
        """测试可选代码节点失败时继续执行"""
        config = PipelineConfig(
            id="test_optional_pipeline",
            name="可选步骤 Pipeline",
            description="测试可选代码节点",
            default_testset="test.jsonl",
            inputs=[InputSpec(name="value", desc="值")],
            steps=[
                StepConfig(
                    id="optional_step",
                    type="code_node",
                    code_config=CodeNodeConfig(
                        language="python",
                        code="def transform(inputs): raise ValueError('error')",
                        timeout=10
                    ),
                    input_mapping={"value": "value"},
                    output_key="optional_output",
                    required=False  # 可选步骤
                ),
                StepConfig(
                    id="next_step",
                    type="code_node",
                    code_config=CodeNodeConfig(
                        language="python",
                        code="def transform(inputs): return {'result': 'success'}",
                        timeout=10
                    ),
                    input_mapping={"value": "value"},
                    output_key="final_output",
                    required=True
                )
            ],
            outputs=[OutputSpec(key="final_output", label="最终输出")],
            baseline=None,
            variants={}
        )
        
        runner = PipelineRunner(config)
        sample = {"id": "test", "value": 1}
        
        result = runner.execute_sample(sample, variant="baseline")
        
        # Pipeline 应该成功完成
        assert result.error is None
        assert len(result.step_results) == 2
        
        # 第一个步骤失败
        assert result.step_results[0].success is False
        
        # 第二个步骤成功
        assert result.step_results[1].success is True
        assert result.step_results[1].output_value == {"result": "success"}
    
    @patch('src.pipeline_runner.run_flow_with_tokens')
    @patch('src.pipeline_runner.load_agent')
    def test_mixed_pipeline_agent_and_code(self, mock_load_agent, mock_run_flow, 
                                          pipeline_with_agent_and_code):
        """测试混合 Pipeline（Agent + 代码节点）"""
        # Mock agent with proper flow structure
        mock_flow = Mock()
        mock_flow.name = "test_flow"
        mock_agent = Mock()
        mock_agent.flows = [mock_flow]
        mock_load_agent.return_value = mock_agent
        
        # Mock agent 输出
        mock_run_flow.return_value = (
            "agent output text",
            {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            None
        )
        
        runner = PipelineRunner(pipeline_with_agent_and_code)
        sample = {
            "id": "test_mixed",
            "text": "hello world"
        }
        
        result = runner.execute_sample(sample, variant="baseline")
        
        # 验证结果
        assert result.error is None
        assert len(result.step_results) == 2
        
        # Agent 步骤
        assert result.step_results[0].step_id == "agent_step"
        assert result.step_results[0].success is True
        assert result.step_results[0].output_value == "agent output text"
        
        # 代码节点步骤
        assert result.step_results[1].step_id == "transform_step"
        assert result.step_results[1].success is True
        assert result.step_results[1].output_value == {"transformed": "AGENT OUTPUT TEXT"}
    
    def test_code_node_data_passing(self):
        """测试代码节点之间的数据传递"""
        config = PipelineConfig(
            id="test_data_passing",
            name="数据传递测试",
            description="测试代码节点之间的数据传递",
            default_testset="test.jsonl",
            inputs=[InputSpec(name="value", desc="值")],
            steps=[
                StepConfig(
                    id="step1",
                    type="code_node",
                    code_config=CodeNodeConfig(
                        language="python",
                        code="def transform(inputs): return {'result': inputs['value'] * 2}",
                        timeout=10
                    ),
                    input_mapping={"value": "value"},
                    output_key="step1_output",
                    required=True
                ),
                StepConfig(
                    id="step2",
                    type="code_node",
                    code_config=CodeNodeConfig(
                        language="python",
                        code="def transform(inputs): return {'final': inputs['data']['result'] + 10}",
                        timeout=10
                    ),
                    input_mapping={"data": "step1_output"},  # 传递整个输出对象
                    output_key="step2_output",
                    required=True
                )
            ],
            outputs=[OutputSpec(key="step2_output", label="最终输出")],
            baseline=None,
            variants={}
        )
        
        runner = PipelineRunner(config)
        sample = {"id": "test", "value": 5}
        
        result = runner.execute_sample(sample, variant="baseline")
        
        # 验证数据传递
        assert result.error is None
        assert result.step_results[0].output_value == {"result": 10}
        assert result.step_results[1].output_value == {"final": 20}
    
    def test_code_node_invalid_config(self):
        """测试无效的代码节点配置"""
        from src.error_handler import ConfigurationError
        
        config = PipelineConfig(
            id="test_invalid",
            name="无效配置测试",
            description="测试无效的代码节点配置",
            default_testset="test.jsonl",
            inputs=[InputSpec(name="value", desc="值")],
            steps=[
                StepConfig(
                    id="invalid_step",
                    type="code_node",
                    code_config=CodeNodeConfig(
                        language="invalid_language",  # 无效语言
                        code="some code",
                        timeout=10
                    ),
                    input_mapping={"value": "value"},
                    output_key="output",
                    required=True
                )
            ],
            outputs=[OutputSpec(key="output", label="输出")],
            baseline=None,
            variants={}
        )
        
        # 应该在初始化时就抛出配置错误
        with pytest.raises(ConfigurationError):
            runner = PipelineRunner(config)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
