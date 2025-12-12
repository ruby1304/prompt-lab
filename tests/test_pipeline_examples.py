"""
集成测试：Pipeline 示例可执行性

测试 document_summary 和 customer_service_flow Pipeline 的加载和执行。
使用真实的 LLM 调用验证 Pipeline 功能。
"""

import pytest
import json
from pathlib import Path
from dotenv import load_dotenv

from src.pipeline_config import load_pipeline_config
from src.pipeline_runner import PipelineRunner


# 加载环境变量
load_dotenv()


class TestDocumentSummaryPipeline:
    """测试 document_summary Pipeline"""
    
    def test_pipeline_can_load(self):
        """测试 Pipeline 配置能够成功加载"""
        config = load_pipeline_config("document_summary")
        
        assert config.id == "document_summary"
        assert config.name == "文档摘要 Pipeline"
        assert len(config.steps) == 2
        assert config.steps[0].id == "clean"
        assert config.steps[1].id == "summarize"
        assert len(config.variants) == 1
        assert "improved_v1" in config.variants
    
    def test_pipeline_validation_passes(self):
        """测试 Pipeline 配置验证通过"""
        config = load_pipeline_config("document_summary")
        runner = PipelineRunner(config)
        
        errors = runner.validate_pipeline()
        assert len(errors) == 0, f"Validation errors: {errors}"
    
    def test_testset_exists_and_valid(self):
        """测试测试集文件存在且格式正确"""
        testset_path = Path("data/pipelines/document_summary/testsets/documents.jsonl")
        assert testset_path.exists(), f"Testset file not found: {testset_path}"
        
        # 读取并验证测试集格式
        samples = []
        with open(testset_path, "r", encoding="utf-8") as f:
            for line in f:
                sample = json.loads(line.strip())
                samples.append(sample)
                
                # 验证必需字段
                assert "id" in sample
                assert "raw_text" in sample
                assert "tags" in sample
        
        # 验证至少有 5 个测试用例
        assert len(samples) >= 5, f"Expected at least 5 test cases, got {len(samples)}"
    
    @pytest.mark.integration
    def test_pipeline_execution_with_real_llm(self):
        """测试 Pipeline 使用真实 LLM 执行（集成测试）"""
        config = load_pipeline_config("document_summary")
        runner = PipelineRunner(config)
        
        # 使用第一个测试样本
        testset_path = Path("data/pipelines/document_summary/testsets/documents.jsonl")
        with open(testset_path, "r", encoding="utf-8") as f:
            sample = json.loads(f.readline().strip())
        
        # 执行 Pipeline
        result = runner.execute_sample(sample, variant="baseline")
        
        # 验证执行结果
        assert str(result.sample_id) == str(sample["id"])
        assert result.variant == "baseline"
        assert result.error is None, f"Execution error: {result.error}"
        
        # 验证步骤结果
        assert len(result.step_results) == 2
        
        # 验证第一步（clean）
        clean_result = result.step_results[0]
        assert clean_result.step_id == "clean"
        assert clean_result.output_key == "cleaned_text"
        assert clean_result.output_value is not None
        assert len(clean_result.output_value) > 0
        assert clean_result.error is None
        
        # 验证第二步（summarize）
        summary_result = result.step_results[1]
        assert summary_result.step_id == "summarize"
        assert summary_result.output_key == "summary"
        assert summary_result.output_value is not None
        assert len(summary_result.output_value) > 0
        assert summary_result.error is None
        
        # 验证最终输出
        assert "summary" in result.final_outputs
        assert len(result.final_outputs["summary"]) > 0
        
        # 验证性能指标
        assert result.total_execution_time > 0
        assert result.total_token_usage["total_tokens"] > 0
    
    @pytest.mark.integration
    def test_pipeline_variant_execution(self):
        """测试 Pipeline 变体执行"""
        config = load_pipeline_config("document_summary")
        runner = PipelineRunner(config)
        
        # 使用第一个测试样本
        testset_path = Path("data/pipelines/document_summary/testsets/documents.jsonl")
        with open(testset_path, "r", encoding="utf-8") as f:
            sample = json.loads(f.readline().strip())
        
        # 执行变体
        result = runner.execute_sample(sample, variant="improved_v1")
        
        # 验证执行结果
        assert result.variant == "improved_v1"
        assert result.error is None
        assert len(result.step_results) == 2
        assert "summary" in result.final_outputs


class TestCustomerServiceFlowPipeline:
    """测试 customer_service_flow Pipeline"""
    
    def test_pipeline_can_load(self):
        """测试 Pipeline 配置能够成功加载"""
        config = load_pipeline_config("customer_service_flow")
        
        assert config.id == "customer_service_flow"
        assert config.name == "客服处理流程"
        assert len(config.steps) == 3
        assert config.steps[0].id == "intent_detection"
        assert config.steps[1].id == "entity_extraction"
        assert config.steps[2].id == "response_generation"
        assert len(config.variants) == 1
    
    def test_pipeline_validation_passes(self):
        """测试 Pipeline 配置验证通过"""
        config = load_pipeline_config("customer_service_flow")
        runner = PipelineRunner(config)
        
        errors = runner.validate_pipeline()
        assert len(errors) == 0, f"Validation errors: {errors}"
    
    def test_testset_exists_and_valid(self):
        """测试测试集文件存在且格式正确"""
        testset_path = Path("data/pipelines/customer_service_flow/testsets/customer_requests.jsonl")
        assert testset_path.exists(), f"Testset file not found: {testset_path}"
        
        # 读取并验证测试集格式
        samples = []
        with open(testset_path, "r", encoding="utf-8") as f:
            for line in f:
                sample = json.loads(line.strip())
                samples.append(sample)
                
                # 验证必需字段
                assert "id" in sample
                assert "user_message" in sample
                assert "tags" in sample
        
        # 验证至少有 5 个测试用例
        assert len(samples) >= 5, f"Expected at least 5 test cases, got {len(samples)}"
    
    @pytest.mark.integration
    def test_pipeline_execution_with_real_llm(self):
        """测试 Pipeline 使用真实 LLM 执行（集成测试）"""
        config = load_pipeline_config("customer_service_flow")
        runner = PipelineRunner(config)
        
        # 使用第一个测试样本
        testset_path = Path("data/pipelines/customer_service_flow/testsets/customer_requests.jsonl")
        with open(testset_path, "r", encoding="utf-8") as f:
            sample = json.loads(f.readline().strip())
        
        # 执行 Pipeline
        result = runner.execute_sample(sample, variant="baseline")
        
        # 验证执行结果
        assert str(result.sample_id) == str(sample["id"])
        assert result.variant == "baseline"
        assert result.error is None, f"Execution error: {result.error}"
        
        # 验证步骤结果
        assert len(result.step_results) == 3
        
        # 验证第一步（intent_detection）
        intent_result = result.step_results[0]
        assert intent_result.step_id == "intent_detection"
        assert intent_result.output_key == "intent"
        assert intent_result.output_value is not None
        assert len(intent_result.output_value) > 0
        assert intent_result.error is None
        
        # 验证第二步（entity_extraction）
        entity_result = result.step_results[1]
        assert entity_result.step_id == "entity_extraction"
        assert entity_result.output_key == "entities"
        assert entity_result.output_value is not None
        assert entity_result.error is None
        
        # 验证第三步（response_generation）
        response_result = result.step_results[2]
        assert response_result.step_id == "response_generation"
        assert response_result.output_key == "response"
        assert response_result.output_value is not None
        assert len(response_result.output_value) > 0
        assert response_result.error is None
        
        # 验证最终输出
        assert "intent" in result.final_outputs
        assert "entities" in result.final_outputs
        assert "response" in result.final_outputs
        assert len(result.final_outputs["response"]) > 0
        
        # 验证性能指标
        assert result.total_execution_time > 0
        assert result.total_token_usage["total_tokens"] > 0
    
    @pytest.mark.integration
    def test_pipeline_with_conversation_history(self):
        """测试 Pipeline 处理带对话历史的请求"""
        config = load_pipeline_config("customer_service_flow")
        runner = PipelineRunner(config)
        
        # 使用带对话历史的测试样本
        testset_path = Path("data/pipelines/customer_service_flow/testsets/customer_requests.jsonl")
        with open(testset_path, "r", encoding="utf-8") as f:
            for line in f:
                sample = json.loads(line.strip())
                if sample.get("conversation_history"):
                    break
        
        # 执行 Pipeline
        result = runner.execute_sample(sample, variant="baseline")
        
        # 验证执行结果
        assert result.error is None
        assert len(result.step_results) == 3
        assert "response" in result.final_outputs


class TestPipelineOutputFormat:
    """测试 Pipeline 输出格式"""
    
    @pytest.mark.integration
    def test_output_format_consistency(self):
        """测试输出格式的一致性"""
        # 测试 document_summary
        config1 = load_pipeline_config("document_summary")
        runner1 = PipelineRunner(config1)
        
        testset_path1 = Path("data/pipelines/document_summary/testsets/documents.jsonl")
        with open(testset_path1, "r", encoding="utf-8") as f:
            sample1 = json.loads(f.readline().strip())
        
        result1 = runner1.execute_sample(sample1, variant="baseline")
        
        # 验证结果可以转换为字典
        result_dict1 = result1.to_dict()
        assert isinstance(result_dict1, dict)
        assert "sample_id" in result_dict1
        assert "variant" in result_dict1
        assert "step_results" in result_dict1
        assert "final_outputs" in result_dict1
        assert "total_execution_time" in result_dict1
        assert "total_token_usage" in result_dict1
        
        # 测试 customer_service_flow
        config2 = load_pipeline_config("customer_service_flow")
        runner2 = PipelineRunner(config2)
        
        testset_path2 = Path("data/pipelines/customer_service_flow/testsets/customer_requests.jsonl")
        with open(testset_path2, "r", encoding="utf-8") as f:
            sample2 = json.loads(f.readline().strip())
        
        result2 = runner2.execute_sample(sample2, variant="baseline")
        
        # 验证结果格式一致
        result_dict2 = result2.to_dict()
        assert set(result_dict1.keys()) == set(result_dict2.keys())
