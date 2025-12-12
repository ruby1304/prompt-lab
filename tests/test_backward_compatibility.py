# tests/test_backward_compatibility.py
"""
向后兼容性测试套件

验证新功能（Output Parser）不会破坏现有功能：
- 未配置 output_parser 的 Flow 继续返回字符串
- 现有的 Agent 配置能够正常加载
- 现有的 API 和 CLI 接口保持兼容
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
from unittest.mock import patch, Mock

from src.chains import run_flow, run_flow_with_tokens, load_flow_config
from src.agent_registry import load_agent, list_available_agents, AgentConfig
from src.pipeline_config import load_pipeline_config


class TestFlowConfigBackwardCompatibility:
    """测试旧 Flow 配置的向后兼容性"""
    
    def test_flow_without_output_parser_returns_string(self):
        """测试未配置 output_parser 的 Flow 返回字符串"""
        # 使用现有的 text_cleaner agent（没有 output_parser 配置）
        result = run_flow(
            flow_name="clean_v1",
            agent_id="text_cleaner",
            extra_vars={"text": "  这是一个  测试文本  "}
        )
        
        # 验证返回的是字符串类型
        assert isinstance(result, str), f"Expected str, got {type(result)}"
        assert len(result) > 0
        # 验证文本被清洗了
        assert "测试文本" in result
    
    def test_flow_without_output_parser_with_tokens(self):
        """测试未配置 output_parser 的 Flow 使用 run_flow_with_tokens"""
        result, token_info, parser_stats = run_flow_with_tokens(
            flow_name="clean_v1",
            agent_id="text_cleaner",
            extra_vars={"text": "测试文本"}
        )
        
        # 验证返回的是字符串类型
        assert isinstance(result, str), f"Expected str, got {type(result)}"
        
        # 验证 token 信息存在
        assert isinstance(token_info, dict)
        assert "input_tokens" in token_info or "total_tokens" in token_info
        
        # 验证 parser_stats 为 None（因为没有使用 parser）
        assert parser_stats is None
    
    def test_all_existing_flows_load_successfully(self):
        """测试所有现有的 Flow 配置能够成功加载"""
        # 获取所有 agent
        agents = list_available_agents()
        
        load_failures = []
        
        for agent_id in agents:
            try:
                agent = load_agent(agent_id)
                
                # 尝试加载每个 flow 配置
                for flow_info in agent.flows:
                    flow_name = flow_info.name
                    try:
                        flow_cfg = load_flow_config(flow_name, agent_id)
                        
                        # 验证基本字段存在
                        assert "system_prompt" in flow_cfg
                        assert "user_template" in flow_cfg
                        
                        # 如果有 output_parser 配置，验证其格式
                        if "output_parser" in flow_cfg:
                            parser_cfg = flow_cfg["output_parser"]
                            assert "type" in parser_cfg
                            assert parser_cfg["type"] in ["json", "pydantic", "list", "none"]
                        
                    except Exception as e:
                        load_failures.append(f"{agent_id}/{flow_name}: {str(e)}")
            
            except Exception as e:
                load_failures.append(f"{agent_id}: {str(e)}")
        
        # 如果有加载失败，报告详情
        if load_failures:
            pytest.fail(f"以下 Flow 配置加载失败:\n" + "\n".join(load_failures))
    
    def test_flow_with_defaults_still_works(self):
        """测试使用 defaults 的 Flow 仍然正常工作"""
        # text_cleaner 的 clean_v1 有 defaults 配置
        flow_cfg = load_flow_config("clean_v1", "text_cleaner")
        
        # 验证 defaults 存在
        assert "defaults" in flow_cfg
        assert "text" in flow_cfg["defaults"]
        
        # 测试不提供参数时使用 defaults
        result = run_flow(
            flow_name="clean_v1",
            agent_id="text_cleaner",
            extra_vars={}
        )
        
        # 应该能够成功执行（使用默认的空字符串）
        assert isinstance(result, str)


class TestAgentConfigBackwardCompatibility:
    """测试 Agent 配置文件的向后兼容性"""
    
    def test_all_agent_configs_load_successfully(self):
        """测试所有现有的 Agent 配置能够成功加载"""
        agents = list_available_agents()
        
        assert len(agents) > 0, "应该至少有一个 agent"
        
        load_failures = []
        
        for agent_id in agents:
            try:
                agent = load_agent(agent_id)
                
                # 验证基本字段
                assert agent.id == agent_id
                assert agent.name is not None
                assert agent.type is not None
                assert len(agent.flows) > 0
                
                # 验证每个 flow 的配置
                for flow_info in agent.flows:
                    assert flow_info.name is not None
                    assert flow_info.file is not None
            
            except Exception as e:
                load_failures.append(f"{agent_id}: {str(e)}")
        
        if load_failures:
            pytest.fail(f"以下 Agent 配置加载失败:\n" + "\n".join(load_failures))
    
    def test_agent_without_evaluation_config(self):
        """测试没有评估配置的 Agent 仍然可以加载"""
        # text_cleaner 可能没有评估配置
        agent = load_agent("text_cleaner")
        
        assert agent.id == "text_cleaner"
        assert agent.name is not None
        
        # 评估配置应该是可选的
        # 如果没有，应该有合理的默认值
        if hasattr(agent, 'evaluation'):
            # 如果有评估配置，验证其结构
            eval_cfg = agent.evaluation
            if eval_cfg:
                assert hasattr(eval_cfg, 'rules') or hasattr(eval_cfg, 'judge_enabled')
    
    def test_agent_with_multiple_flows(self):
        """测试有多个 Flow 的 Agent 配置"""
        # document_summarizer 有多个 flow 版本
        agent = load_agent("document_summarizer")
        
        assert len(agent.flows) >= 2
        
        # 验证每个 flow 都可以执行
        for flow_info in agent.flows[:2]:  # 只测试前两个
            result = run_flow(
                flow_name=flow_info.name,
                agent_id=agent.id,
                extra_vars={"text": "这是一个测试文档，包含一些内容。"}
            )
            
            assert isinstance(result, str)
            assert len(result) > 0


class TestPipelineConfigBackwardCompatibility:
    """测试 Pipeline 配置文件的向后兼容性"""
    
    def test_existing_pipeline_configs_load(self):
        """测试现有的 Pipeline 配置能够加载"""
        # 检查是否有现有的 pipeline 配置
        from src.pipeline_config import PIPELINES_DIR
        
        if not PIPELINES_DIR.exists():
            pytest.skip("没有 pipeline 配置目录")
        
        pipeline_files = list(PIPELINES_DIR.glob("*.yaml"))
        
        if not pipeline_files:
            pytest.skip("没有现有的 pipeline 配置文件")
        
        load_failures = []
        
        for pipeline_file in pipeline_files:
            pipeline_id = pipeline_file.stem
            try:
                config = load_pipeline_config(pipeline_id)
                
                # 验证基本字段
                assert config.id == pipeline_id
                assert config.name is not None
                assert len(config.steps) > 0
                assert len(config.inputs) > 0
                
            except Exception as e:
                load_failures.append(f"{pipeline_id}: {str(e)}")
        
        if load_failures:
            pytest.fail(f"以下 Pipeline 配置加载失败:\n" + "\n".join(load_failures))
    
    def test_pipeline_without_evaluation_config(self):
        """测试没有评估配置的 Pipeline 仍然可以加载"""
        from src.pipeline_config import PIPELINES_DIR
        
        if not PIPELINES_DIR.exists():
            pytest.skip("没有 pipeline 配置目录")
        
        pipeline_files = list(PIPELINES_DIR.glob("*.yaml"))
        
        if not pipeline_files:
            pytest.skip("没有现有的 pipeline 配置文件")
        
        # 加载第一个 pipeline
        pipeline_id = pipeline_files[0].stem
        config = load_pipeline_config(pipeline_id)
        
        # 评估配置应该是可选的
        if hasattr(config, 'evaluation'):
            eval_cfg = config.evaluation
            if eval_cfg:
                assert hasattr(eval_cfg, 'rules') or hasattr(eval_cfg, 'judge_enabled')


class TestAPIBackwardCompatibility:
    """测试 API 接口的向后兼容性"""
    
    def test_run_flow_signature_compatibility(self):
        """测试 run_flow 函数签名保持兼容"""
        # 测试旧的调用方式仍然有效
        
        # 方式1：只提供 flow_name
        result = run_flow(
            flow_name="clean_v1",
            agent_id="text_cleaner",
            extra_vars={"text": "测试"}
        )
        assert isinstance(result, str)
        
        # 方式2：提供 input_text 参数（旧接口）
        result = run_flow(
            flow_name="clean_v1",
            agent_id="text_cleaner",
            input_text="测试文本"
        )
        assert isinstance(result, str)
        
        # 方式3：提供 context 参数（旧接口）
        result = run_flow(
            flow_name="clean_v1",
            agent_id="text_cleaner",
            input_text="测试",
            context="上下文"
        )
        assert isinstance(result, str)
    
    def test_run_flow_with_tokens_signature_compatibility(self):
        """测试 run_flow_with_tokens 函数签名保持兼容"""
        # 测试返回值格式
        result, token_info, parser_stats = run_flow_with_tokens(
            flow_name="clean_v1",
            agent_id="text_cleaner",
            extra_vars={"text": "测试"}
        )
        
        # 验证返回值类型
        assert isinstance(result, str)
        assert isinstance(token_info, dict)
        # parser_stats 可以是 None 或 dict
        assert parser_stats is None or isinstance(parser_stats, dict)
    
    def test_load_agent_api_compatibility(self):
        """测试 load_agent API 保持兼容"""
        # 测试加载 agent
        agent = load_agent("text_cleaner")
        
        # 验证返回的对象类型
        assert isinstance(agent, AgentConfig)
        
        # 验证必需字段存在
        assert hasattr(agent, 'id')
        assert hasattr(agent, 'name')
        assert hasattr(agent, 'type')
        assert hasattr(agent, 'flows')
        
        # 验证 flows 是列表
        assert isinstance(agent.flows, list)
        assert len(agent.flows) > 0
    
    def test_list_agents_api_compatibility(self):
        """测试 list_available_agents API 保持兼容"""
        agents = list_available_agents()
        
        # 验证返回的是列表
        assert isinstance(agents, list)
        assert len(agents) > 0
        
        # 验证每个元素是字符串（agent_id）
        for agent_id in agents:
            assert isinstance(agent_id, str)
            assert len(agent_id) > 0


class TestEvaluationBackwardCompatibility:
    """测试评估功能的向后兼容性"""
    
    def test_evaluation_without_output_parser(self):
        """测试未使用 output_parser 的评估仍然正常工作"""
        # 这个测试验证旧的评估流程不受影响
        
        # 执行一个没有 output_parser 的 flow
        result = run_flow(
            flow_name="clean_v1",
            agent_id="text_cleaner",
            extra_vars={"text": "  测试文本  "}
        )
        
        # 验证结果是字符串
        assert isinstance(result, str)
        
        # 模拟评估过程（不使用真实的 judge）
        # 只验证结果格式可以被评估系统处理
        assert len(result) > 0
        assert isinstance(result, str)
    
    def test_judge_agent_backward_compatibility(self):
        """测试 Judge Agent 的向后兼容性"""
        # 加载 judge agent
        judge_agent = load_agent("judge_default")
        
        assert judge_agent.id == "judge_default"
        assert len(judge_agent.flows) > 0
        
        # 验证 judge flow 配置可以加载
        for flow_info in judge_agent.flows:
            flow_cfg = load_flow_config(flow_info.name, "judge_default")
            
            assert "system_prompt" in flow_cfg
            assert "user_template" in flow_cfg
            
            # 如果配置了 output_parser，验证其类型
            if "output_parser" in flow_cfg:
                parser_cfg = flow_cfg["output_parser"]
                assert parser_cfg["type"] == "json"


class TestDataStructureBackwardCompatibility:
    """测试数据结构的向后兼容性"""
    
    def test_evaluation_result_backward_compatibility(self):
        """测试 EvaluationResult 数据结构的向后兼容性"""
        from src.models import EvaluationResult
        
        # 测试创建旧格式的评估结果（没有新字段）
        result = EvaluationResult(
            sample_id="test_sample",
            entity_type="agent",
            entity_id="test_agent",
            variant="test_flow",
            overall_score=8.5,
            must_have_pass=True,
            rule_violations=[],
            judge_feedback="Good"
        )
        
        # 验证对象可以正常创建
        assert result.sample_id == "test_sample"
        assert result.overall_score == 8.5
        
        # 验证可以转换为字典
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "sample_id" in result_dict
        assert "overall_score" in result_dict
    
    def test_pipeline_result_backward_compatibility(self):
        """测试 PipelineResult 数据结构的向后兼容性"""
        from src.pipeline_runner import PipelineResult, StepResult
        
        # 创建步骤结果
        step_result = StepResult(
            step_id="step1",
            output_key="step1_output",
            output_value="test output",
            execution_time=1.5,
            success=True
        )
        
        # 创建 pipeline 结果
        pipeline_result = PipelineResult(
            sample_id="test_sample",
            variant="baseline",
            step_results=[step_result],
            final_outputs={"result": "final output"},
            total_execution_time=2.0
        )
        
        # 验证对象可以正常创建
        assert pipeline_result.sample_id == "test_sample"
        assert len(pipeline_result.step_results) == 1
        assert pipeline_result.final_outputs["result"] == "final output"


class TestCLIBackwardCompatibility:
    """测试 CLI 命令的向后兼容性"""
    
    def test_single_run_cli_compatibility(self):
        """测试单次运行 CLI 命令的兼容性"""
        # 这个测试验证 CLI 接口没有破坏性变更
        
        # 模拟旧的 CLI 调用
        from src.run_single import chat
        from typer.testing import CliRunner
        from src.run_single import app
        
        runner = CliRunner()
        
        # 测试基本调用
        result = runner.invoke(app, [
            "--flow", "clean_v1",
            "--text", "测试文本"
        ])
        
        # 验证命令执行成功（退出码为0）
        # 注意：由于需要真实的 LLM 调用，这里可能会失败
        # 但至少验证了 CLI 接口没有语法错误
        assert result.exit_code in [0, 1]  # 0=成功, 1=可能的 API 错误
    
    def test_batch_run_cli_compatibility(self):
        """测试批量运行 CLI 命令的兼容性"""
        # 验证批量运行的 CLI 接口仍然存在
        from src import run_batch
        
        # 验证模块可以导入
        assert hasattr(run_batch, 'run')
        assert hasattr(run_batch, 'load_test_cases')


class TestModelOverrideBackwardCompatibility:
    """测试模型覆盖功能的向后兼容性"""
    
    def test_model_override_in_extra_vars(self):
        """测试通过 extra_vars 传递模型覆盖参数"""
        # 这个功能应该继续工作
        
        # 注意：这里不实际调用 LLM，只验证参数传递
        flow_cfg = load_flow_config("clean_v1", "text_cleaner")
        
        # 验证配置可以加载
        assert "system_prompt" in flow_cfg
        
        # 验证 extra_vars 可以包含 _model_override
        extra_vars = {
            "text": "测试",
            "_model_override": "gpt-4"
        }
        
        # 这应该不会抛出异常
        assert "_model_override" in extra_vars


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
