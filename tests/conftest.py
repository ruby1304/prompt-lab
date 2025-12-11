# tests/conftest.py
"""
pytest 配置和共享 fixtures
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, MagicMock

from src.models import PipelineConfig, StepConfig, BaselineConfig, VariantConfig, VariantStepOverride, BaselineStepConfig
from src.agent_registry import AgentConfig, AgentFlow


@pytest.fixture(autouse=True)
def _set_default_model_env(monkeypatch):
    """确保测试运行时不会依赖写死的模型名称。"""
    monkeypatch.setenv("OPENAI_MODEL_NAME", "test-model")


@pytest.fixture
def temp_dir():
    """创建临时目录"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_pipeline_config():
    """创建示例 pipeline 配置"""
    return PipelineConfig(
        id="test_pipeline",
        name="测试 Pipeline",
        description="用于测试的 Pipeline 配置",
        default_testset="test.jsonl",
        inputs=[{"name": "input_text", "desc": "输入文本"}],
        steps=[
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="test_agent",
                flow="test_flow",
                input_mapping={"text": "input_text"},
                output_key="step1_output"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="test_agent",
                flow="test_flow2",
                input_mapping={"text": "step1_output"},
                output_key="step2_output"
            )
        ],
        outputs=[{"key": "step2_output", "label": "最终输出"}],
        baseline=BaselineConfig(
            name="baseline_v1",
            description="基线配置",
            steps={
                "step1": BaselineStepConfig(flow="baseline_flow"),
                "step2": BaselineStepConfig(flow="baseline_flow2")
            }
        ),
        variants={
            "variant1": VariantConfig(
                description="变体1",
                overrides={
                    "step1": VariantStepOverride(flow="variant_flow")
                }
            )
        }
    )


@pytest.fixture
def sample_testset():
    """创建示例测试集"""
    return [
        {
            "id": "sample1",
            "tags": ["test", "basic"],
            "scenario": "normal",
            "priority": "high",
            "input_text": "这是测试输入1"
        },
        {
            "id": "sample2",
            "tags": ["test", "edge_case"],
            "scenario": "edge",
            "priority": "medium",
            "input_text": "这是测试输入2"
        },
        {
            "id": "sample3",
            "tags": ["regression"],
            "scenario": "normal",
            "priority": "high",
            "input_text": "这是回归测试输入"
        }
    ]


@pytest.fixture
def mock_agent():
    """创建模拟的 agent"""
    agent = Mock(spec=AgentConfig)
    agent.id = "test_agent"
    agent.name = "测试 Agent"
    
    # Create mock flows with proper name attributes
    flows = []
    flow_names = ["test_flow", "test_flow2", "baseline_flow", "baseline_flow2", "variant_flow", "baseline_flow1", "variant_flow1"]
    for flow_name in flow_names:
        flow = Mock(spec=AgentFlow)
        flow.name = flow_name
        flows.append(flow)
    
    agent.flows = flows
    return agent


@pytest.fixture
def mock_load_agent(monkeypatch, mock_agent):
    """模拟 load_agent 函数"""
    def _load_agent(agent_id: str):
        if agent_id == "test_agent":
            return mock_agent
        raise ValueError(f"Agent not found: {agent_id}")
    
    # Patch in multiple locations where load_agent might be imported
    monkeypatch.setattr("src.agent_registry.load_agent", _load_agent)
    monkeypatch.setattr("src.pipeline_runner.load_agent", _load_agent)
    return _load_agent


@pytest.fixture
def mock_run_flow_with_tokens(monkeypatch):
    """模拟 run_flow_with_tokens 函数"""
    def _run_flow(flow_name: str, extra_vars: Dict[str, Any], agent_id: str):
        # 模拟不同 flow 的输出
        outputs = {
            "test_flow": f"输出来自 {flow_name}，输入: {extra_vars.get('text', '')}",
            "test_flow2": f"最终输出来自 {flow_name}，输入: {extra_vars.get('text', '')}",
            "baseline_flow": f"基线输出来自 {flow_name}",
            "baseline_flow2": f"基线最终输出来自 {flow_name}",
            "baseline_flow1": f"基线输出来自 {flow_name}",
            "variant_flow": f"变体输出来自 {flow_name}",
            "variant_flow1": f"变体输出来自 {flow_name}"
        }
        
        token_usage = {
            "input_tokens": 100,
            "output_tokens": 50,
            "total_tokens": 150
        }
        
        return outputs.get(flow_name, f"默认输出来自 {flow_name}"), token_usage
    
    # Patch in multiple locations where run_flow_with_tokens might be imported
    monkeypatch.setattr("src.chains.run_flow_with_tokens", _run_flow)
    monkeypatch.setattr("src.pipeline_runner.run_flow_with_tokens", _run_flow)
    return _run_flow


@pytest.fixture
def mock_data_manager(temp_dir):
    """创建模拟的数据管理器"""
    from src.data_manager import DataManager
    
    data_manager = DataManager(base_dir=temp_dir)
    data_manager.initialize_data_structure()
    return data_manager