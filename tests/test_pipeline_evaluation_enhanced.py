# tests/test_pipeline_evaluation_enhanced.py
"""
测试增强的 Pipeline 评估功能

测试中间步骤评估、聚合结果评估和最终输出评估
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.unified_evaluator import UnifiedEvaluator
from src.models import EvaluationConfig, EvaluationResult


class TestIntermediateStepEvaluation:
    """测试中间步骤评估功能"""
    
    def test_evaluate_intermediate_steps_exact_match(self):
        """测试中间步骤评估 - 完全匹配"""
        config = EvaluationConfig(
            judge_enabled=False,
            rules=[]
        )
        evaluator = UnifiedEvaluator(config)
        
        test_case = {
            'id': 'test_1',
            'intermediate_expectations': {
                'step1': {'status': 'success', 'count': 5},
                'step2': {'result': 'processed'}
            }
        }
        
        step_outputs = {
            'step1': {'status': 'success', 'count': 5},
            'step2': {'result': 'processed'},
            'step3': {'final': 'output'}
        }
        
        results = evaluator.evaluate_intermediate_steps(
            pipeline_id='test_pipeline',
            variant='v1',
            test_case=test_case,
            step_outputs=step_outputs
        )
        
        assert len(results) == 2
        assert results['step1']['matched'] is True
        assert results['step2']['matched'] is True
        assert '所有字段匹配' in results['step1']['details']
    
    def test_evaluate_intermediate_steps_mismatch(self):
        """测试中间步骤评估 - 不匹配"""
        config = EvaluationConfig(
            judge_enabled=False,
            rules=[]
        )
        evaluator = UnifiedEvaluator(config)
        
        test_case = {
            'id': 'test_1',
            'intermediate_expectations': {
                'step1': {'status': 'success', 'count': 5},
                'step2': {'result': 'processed'}
            }
        }
        
        step_outputs = {
            'step1': {'status': 'failed', 'count': 3},  # 不匹配
            'step2': {'result': 'processed'},
            'step3': {'final': 'output'}
        }
        
        results = evaluator.evaluate_intermediate_steps(
            pipeline_id='test_pipeline',
            variant='v1',
            test_case=test_case,
            step_outputs=step_outputs
        )
        
        assert len(results) == 2
        assert results['step1']['matched'] is False
        assert results['step2']['matched'] is True
        assert '不匹配' in results['step1']['details']
    
    def test_evaluate_intermediate_steps_contains_match(self):
        """测试中间步骤评估 - 包含匹配"""
        config = EvaluationConfig(
            judge_enabled=False,
            rules=[]
        )
        evaluator = UnifiedEvaluator(config)
        
        test_case = {
            'id': 'test_1',
            'intermediate_expectations': {
                'step1': {'message': 'contains:success'},
                'step2': 'contains:processed successfully'
            }
        }
        
        step_outputs = {
            'step1': {'message': 'The operation was a success!'},
            'step2': 'Data was processed successfully with no errors',
            'step3': {'final': 'output'}
        }
        
        results = evaluator.evaluate_intermediate_steps(
            pipeline_id='test_pipeline',
            variant='v1',
            test_case=test_case,
            step_outputs=step_outputs
        )
        
        assert len(results) == 2
        assert results['step1']['matched'] is True
        assert results['step2']['matched'] is True
    
    def test_evaluate_intermediate_steps_missing_step(self):
        """测试中间步骤评估 - 缺少步骤输出"""
        config = EvaluationConfig(
            judge_enabled=False,
            rules=[]
        )
        evaluator = UnifiedEvaluator(config)
        
        test_case = {
            'id': 'test_1',
            'intermediate_expectations': {
                'step1': {'status': 'success'},
                'step2': {'result': 'processed'}
            }
        }
        
        step_outputs = {
            'step1': {'status': 'success'},
            # step2 缺失
            'step3': {'final': 'output'}
        }
        
        results = evaluator.evaluate_intermediate_steps(
            pipeline_id='test_pipeline',
            variant='v1',
            test_case=test_case,
            step_outputs=step_outputs
        )
        
        assert len(results) == 2
        assert results['step1']['matched'] is True
        assert results['step2']['matched'] is False
        assert results['step2']['actual'] is None


class TestAggregationEvaluation:
    """测试聚合结果评估功能"""
    
    def test_evaluate_aggregation_result_exact_match(self):
        """测试聚合结果评估 - 完全匹配"""
        config = EvaluationConfig(
            judge_enabled=False,
            rules=[]
        )
        evaluator = UnifiedEvaluator(config)
        
        test_case = {
            'id': 'test_1',
            'expected_aggregation': {
                'total_count': 10,
                'success_rate': 0.8
            }
        }
        
        aggregation_output = {
            'total_count': 10,
            'success_rate': 0.8
        }
        
        result = evaluator.evaluate_aggregation_result(
            pipeline_id='test_pipeline',
            variant='v1',
            test_case=test_case,
            aggregation_output=aggregation_output
        )
        
        assert result['matched'] is True
        assert '所有字段匹配' in result['details']
    
    def test_evaluate_aggregation_result_mismatch(self):
        """测试聚合结果评估 - 不匹配"""
        config = EvaluationConfig(
            judge_enabled=False,
            rules=[]
        )
        evaluator = UnifiedEvaluator(config)
        
        test_case = {
            'id': 'test_1',
            'expected_aggregation': {
                'total_count': 10,
                'success_rate': 0.8
            }
        }
        
        aggregation_output = {
            'total_count': 8,  # 不匹配
            'success_rate': 0.7  # 不匹配
        }
        
        result = evaluator.evaluate_aggregation_result(
            pipeline_id='test_pipeline',
            variant='v1',
            test_case=test_case,
            aggregation_output=aggregation_output
        )
        
        assert result['matched'] is False
        assert '不匹配' in result['details']
    
    def test_evaluate_aggregation_result_list(self):
        """测试聚合结果评估 - 列表类型"""
        config = EvaluationConfig(
            judge_enabled=False,
            rules=[]
        )
        evaluator = UnifiedEvaluator(config)
        
        test_case = {
            'id': 'test_1',
            'expected_aggregation': [
                {'id': 1, 'status': 'success'},
                {'id': 2, 'status': 'success'}
            ]
        }
        
        aggregation_output = [
            {'id': 1, 'status': 'success'},
            {'id': 2, 'status': 'success'}
        ]
        
        result = evaluator.evaluate_aggregation_result(
            pipeline_id='test_pipeline',
            variant='v1',
            test_case=test_case,
            aggregation_output=aggregation_output
        )
        
        assert result['matched'] is True
    
    def test_evaluate_aggregation_result_no_expectation(self):
        """测试聚合结果评估 - 没有预期结果"""
        config = EvaluationConfig(
            judge_enabled=False,
            rules=[]
        )
        evaluator = UnifiedEvaluator(config)
        
        test_case = {
            'id': 'test_1'
            # 没有 expected_aggregation
        }
        
        aggregation_output = {'total': 10}
        
        result = evaluator.evaluate_aggregation_result(
            pipeline_id='test_pipeline',
            variant='v1',
            test_case=test_case,
            aggregation_output=aggregation_output
        )
        
        assert result == {}


class TestCompareOutputs:
    """测试输出比较功能"""
    
    def test_compare_outputs_dict_exact_match(self):
        """测试字典完全匹配"""
        config = EvaluationConfig(judge_enabled=False, rules=[])
        evaluator = UnifiedEvaluator(config)
        
        expected = {'a': 1, 'b': 'test', 'c': [1, 2, 3]}
        actual = {'a': 1, 'b': 'test', 'c': [1, 2, 3]}
        
        matched, details = evaluator._compare_outputs(expected, actual)
        
        assert matched is True
        assert '所有字段匹配' in details
    
    def test_compare_outputs_dict_partial_match(self):
        """测试字典部分匹配（实际包含更多字段）"""
        config = EvaluationConfig(judge_enabled=False, rules=[])
        evaluator = UnifiedEvaluator(config)
        
        expected = {'a': 1, 'b': 'test'}
        actual = {'a': 1, 'b': 'test', 'c': 'extra'}
        
        matched, details = evaluator._compare_outputs(expected, actual)
        
        assert matched is True  # 只要预期的字段都匹配即可
    
    def test_compare_outputs_dict_missing_key(self):
        """测试字典缺少键"""
        config = EvaluationConfig(judge_enabled=False, rules=[])
        evaluator = UnifiedEvaluator(config)
        
        expected = {'a': 1, 'b': 'test', 'c': 'value'}
        actual = {'a': 1, 'b': 'test'}
        
        matched, details = evaluator._compare_outputs(expected, actual)
        
        assert matched is False
        assert '缺少键' in details
    
    def test_compare_outputs_string_contains(self):
        """测试字符串包含匹配"""
        config = EvaluationConfig(judge_enabled=False, rules=[])
        evaluator = UnifiedEvaluator(config)
        
        expected = 'contains:success'
        actual = 'The operation was a success!'
        
        matched, details = evaluator._compare_outputs(expected, actual)
        
        assert matched is True
        assert '包含预期文本' in details
    
    def test_compare_outputs_string_regex(self):
        """测试正则表达式匹配"""
        config = EvaluationConfig(judge_enabled=False, rules=[])
        evaluator = UnifiedEvaluator(config)
        
        expected = r'regex:\d{3}-\d{4}'
        actual = 'Phone: 123-4567'
        
        matched, details = evaluator._compare_outputs(expected, actual)
        
        assert matched is True
        assert '匹配正则表达式' in details
    
    def test_compare_outputs_list_exact_match(self):
        """测试列表完全匹配"""
        config = EvaluationConfig(judge_enabled=False, rules=[])
        evaluator = UnifiedEvaluator(config)
        
        expected = [1, 2, 3, 4, 5]
        actual = [1, 2, 3, 4, 5]
        
        matched, details = evaluator._compare_outputs(expected, actual)
        
        assert matched is True
        assert '所有元素匹配' in details
    
    def test_compare_outputs_list_length_mismatch(self):
        """测试列表长度不匹配"""
        config = EvaluationConfig(judge_enabled=False, rules=[])
        evaluator = UnifiedEvaluator(config)
        
        expected = [1, 2, 3]
        actual = [1, 2, 3, 4, 5]
        
        matched, details = evaluator._compare_outputs(expected, actual)
        
        assert matched is False
        assert '列表长度不匹配' in details
    
    def test_compare_outputs_nested_structure(self):
        """测试嵌套结构匹配"""
        config = EvaluationConfig(judge_enabled=False, rules=[])
        evaluator = UnifiedEvaluator(config)
        
        expected = {
            'user': {
                'name': 'John',
                'age': 30,
                'tags': ['admin', 'user']
            },
            'status': 'active'
        }
        
        actual = {
            'user': {
                'name': 'John',
                'age': 30,
                'tags': ['admin', 'user']
            },
            'status': 'active'
        }
        
        matched, details = evaluator._compare_outputs(expected, actual)
        
        assert matched is True


class TestPipelineEvaluationIntegration:
    """测试 Pipeline 评估集成"""
    
    def test_evaluate_intermediate_steps_integration(self):
        """测试中间步骤评估集成"""
        config = EvaluationConfig(
            judge_enabled=False,
            rules=[]
        )
        evaluator = UnifiedEvaluator(config)
        
        # 测试用例
        test_case = {
            'id': 'test_1',
            'inputs': {'text': 'test input'},
            'intermediate_expectations': {
                'output1': {'status': 'success'},
                'output2': {'count': 5}
            }
        }
        
        step_outputs = {
            'output1': {'status': 'success'},
            'output2': {'count': 5, 'extra': 'data'},
            'output3': {'result': 'final output'}
        }
        
        # 执行中间步骤评估
        results = evaluator.evaluate_intermediate_steps(
            pipeline_id='test_pipeline',
            variant='v1',
            test_case=test_case,
            step_outputs=step_outputs
        )
        
        assert len(results) == 2
        assert results['output1']['matched'] is True
        assert results['output2']['matched'] is True
    
    def test_evaluate_aggregation_integration(self):
        """测试聚合评估集成"""
        config = EvaluationConfig(
            judge_enabled=False,
            rules=[]
        )
        evaluator = UnifiedEvaluator(config)
        
        # 测试用例
        test_case = {
            'id': 'test_1',
            'inputs': {'text': 'test input'},
            'expected_aggregation': {
                'total': 10,
                'success_count': 8,
                'summary': 'contains:successful'
            }
        }
        
        aggregation_output = {
            'total': 10,
            'success_count': 8,
            'summary': 'The operation was successful with 8 out of 10 items processed'
        }
        
        # 执行聚合评估
        result = evaluator.evaluate_aggregation_result(
            pipeline_id='test_pipeline',
            variant='v1',
            test_case=test_case,
            aggregation_output=aggregation_output
        )
        
        assert result['matched'] is True
        assert result['expected'] == test_case['expected_aggregation']
        assert result['actual'] == aggregation_output


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
