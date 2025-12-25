# tests/test_testset_loader_pipeline.py
"""
测试 Pipeline 级别的测试集加载功能

测试新增的 Pipeline 特性:
- intermediate_expectations 字段
- evaluation_config 字段
- 步骤级数据提取
- 批量数据组织
- Pipeline 结构分析
"""

import pytest
from pathlib import Path
import tempfile
import json

from src.testset_loader import (
    TestCase,
    TestsetLoader,
    load_testset,
    validate_testset
)


class TestPipelineTestCase:
    """测试 Pipeline 级别的 TestCase 功能"""
    
    def test_from_dict_with_intermediate_expectations(self):
        """测试加载包含中间步骤预期的测试用例"""
        data = {
            'id': 'test_1',
            'inputs': {'text': 'test'},
            'intermediate_expectations': {
                'step1': {'output': 'result1'},
                'step2': {'output': 'result2'}
            }
        }
        
        tc = TestCase.from_dict(data)
        
        assert tc.id == 'test_1'
        assert tc.has_intermediate_expectations()
        assert 'step1' in tc.intermediate_expectations
        assert 'step2' in tc.intermediate_expectations
        assert tc.get_intermediate_expectation('step1') == {'output': 'result1'}
        assert tc.get_intermediate_expectation('step2') == {'output': 'result2'}
        assert tc.get_intermediate_expectation('step3') is None
    
    def test_from_dict_with_evaluation_config(self):
        """测试加载包含评估配置的测试用例"""
        data = {
            'id': 'test_1',
            'inputs': {'text': 'test'},
            'evaluation_config': {
                'evaluate_intermediate': True,
                'evaluate_final': True,
                'strict_mode': False,
                'tolerance': 0.01,
                'ignore_fields': ['timestamp', 'id']
            }
        }
        
        tc = TestCase.from_dict(data)
        
        assert tc.should_evaluate_intermediate() is True
        assert tc.should_evaluate_final() is True
        assert tc.is_strict_mode() is False
        assert tc.get_tolerance() == 0.01
        assert tc.get_ignore_fields() == ['timestamp', 'id']
    
    def test_evaluation_config_defaults(self):
        """测试评估配置的默认值"""
        data = {
            'id': 'test_1',
            'inputs': {'text': 'test'}
        }
        
        tc = TestCase.from_dict(data)
        
        assert tc.should_evaluate_intermediate() is False
        assert tc.should_evaluate_final() is True
        assert tc.is_strict_mode() is False
        assert tc.get_tolerance() == 0.0
        assert tc.get_ignore_fields() == []
    
    def test_should_evaluate_aggregation(self):
        """测试聚合评估判断"""
        # 有预期聚合结果，默认评估
        data1 = {
            'id': 'test_1',
            'expected_aggregation': {'count': 10}
        }
        tc1 = TestCase.from_dict(data1)
        assert tc1.should_evaluate_aggregation() is True
        
        # 没有预期聚合结果，不评估
        data2 = {
            'id': 'test_2'
        }
        tc2 = TestCase.from_dict(data2)
        assert tc2.should_evaluate_aggregation() is False
        
        # 有预期聚合结果，但配置为不评估
        data3 = {
            'id': 'test_3',
            'expected_aggregation': {'count': 10},
            'evaluation_config': {'evaluate_aggregation': False}
        }
        tc3 = TestCase.from_dict(data3)
        assert tc3.should_evaluate_aggregation() is False
    
    def test_get_all_step_ids(self):
        """测试获取所有步骤 ID"""
        data = {
            'id': 'test_1',
            'step_inputs': {
                'step1': {'param': 'value1'},
                'step2': {'param': 'value2'}
            },
            'intermediate_expectations': {
                'step2': {'output': 'result2'},
                'step3': {'output': 'result3'}
            }
        }
        
        tc = TestCase.from_dict(data)
        step_ids = tc.get_all_step_ids()
        
        assert len(step_ids) == 3
        assert 'step1' in step_ids
        assert 'step2' in step_ids
        assert 'step3' in step_ids
        assert step_ids == sorted(step_ids)  # 应该是排序的
    
    def test_get_batch_size(self):
        """测试获取批量数据大小"""
        # 有批量数据
        data1 = {
            'id': 'test_1',
            'batch_items': [
                {'item': 'A'},
                {'item': 'B'},
                {'item': 'C'}
            ]
        }
        tc1 = TestCase.from_dict(data1)
        assert tc1.get_batch_size() == 3
        
        # 没有批量数据
        data2 = {
            'id': 'test_2'
        }
        tc2 = TestCase.from_dict(data2)
        assert tc2.get_batch_size() == 0
    
    def test_to_dict_with_new_fields(self):
        """测试包含新字段的序列化"""
        data = {
            'id': 'test_1',
            'inputs': {'text': 'test'},
            'intermediate_expectations': {
                'step1': {'output': 'result1'}
            },
            'evaluation_config': {
                'evaluate_intermediate': True,
                'strict_mode': False
            }
        }
        
        tc = TestCase.from_dict(data)
        result = tc.to_dict()
        
        assert result['id'] == 'test_1'
        assert 'intermediate_expectations' in result
        assert result['intermediate_expectations'] == {'step1': {'output': 'result1'}}
        assert 'evaluation_config' in result
        assert result['evaluation_config']['evaluate_intermediate'] is True


class TestPipelineTestsetLoader:
    """测试 Pipeline 级别的 TestsetLoader 功能"""
    
    def test_load_multi_step_testset(self, tmp_path):
        """测试加载多步骤测试集"""
        testset_file = tmp_path / "multi_step.jsonl"
        
        test_data = [
            {
                'id': 'test_1',
                'tags': ['multi-step'],
                'inputs': {'text': 'input'},
                'step_inputs': {
                    'preprocess': {'lowercase': True},
                    'analyze': {'model': 'advanced'}
                },
                'intermediate_expectations': {
                    'preprocess': {'cleaned_text': 'input'}
                },
                'expected_outputs': {'result': 'output'}
            }
        ]
        
        with open(testset_file, 'w', encoding='utf-8') as f:
            for data in test_data:
                f.write(json.dumps(data, ensure_ascii=False) + '\n')
        
        test_cases = load_testset(testset_file)
        
        assert len(test_cases) == 1
        tc = test_cases[0]
        assert tc.has_step_inputs()
        assert tc.has_intermediate_expectations()
        assert 'preprocess' in tc.step_inputs
        assert 'analyze' in tc.step_inputs
    
    def test_get_intermediate_evaluation_test_cases(self):
        """测试获取需要中间步骤评估的测试用例"""
        test_cases = [
            TestCase.from_dict({
                'id': 'test_1',
                'intermediate_expectations': {'step1': {'output': 'result'}}
            }),
            TestCase.from_dict({
                'id': 'test_2'
            }),
            TestCase.from_dict({
                'id': 'test_3',
                'intermediate_expectations': {'step2': {'output': 'result'}}
            })
        ]
        
        result = TestsetLoader.get_intermediate_evaluation_test_cases(test_cases)
        
        assert len(result) == 2
        assert result[0].id == 'test_1'
        assert result[1].id == 'test_3'
    
    def test_extract_step_data(self):
        """测试提取步骤数据"""
        tc = TestCase.from_dict({
            'id': 'test_1',
            'step_inputs': {
                'step1': {'param1': 'value1', 'param2': 'value2'}
            },
            'intermediate_expectations': {
                'step1': {'output': 'expected_result'}
            }
        })
        
        step_data = TestsetLoader.extract_step_data(tc, 'step1')
        
        assert 'inputs' in step_data
        assert step_data['inputs'] == {'param1': 'value1', 'param2': 'value2'}
        assert 'expected' in step_data
        assert step_data['expected'] == {'output': 'expected_result'}
        
        # 不存在的步骤
        step_data_empty = TestsetLoader.extract_step_data(tc, 'step_nonexistent')
        assert step_data_empty == {}
    
    def test_organize_batch_data(self):
        """测试组织批量数据"""
        test_cases = [
            TestCase.from_dict({
                'id': 'test_1',
                'batch_items': [{'item': 'A'}, {'item': 'B'}]
            }),
            TestCase.from_dict({
                'id': 'test_2'
            }),
            TestCase.from_dict({
                'id': 'test_3',
                'batch_items': [{'item': 'C'}, {'item': 'D'}, {'item': 'E'}]
            })
        ]
        
        result = TestsetLoader.organize_batch_data(test_cases)
        
        assert result['total_test_cases'] == 2
        assert result['total_batch_items'] == 5
        assert result['average_batch_size'] == 2.5
        assert len(result['test_cases']) == 2
    
    def test_get_pipeline_structure(self):
        """测试分析 Pipeline 结构"""
        test_cases = [
            TestCase.from_dict({
                'id': 'test_1',
                'step_inputs': {
                    'step1': {'param': 'value'},
                    'step2': {'param': 'value'}
                },
                'intermediate_expectations': {
                    'step1': {'output': 'result'}
                }
            }),
            TestCase.from_dict({
                'id': 'test_2',
                'step_inputs': {
                    'step2': {'param': 'value'},
                    'step3': {'param': 'value'}
                },
                'batch_items': [{'item': 'A'}]
            })
        ]
        
        structure = TestsetLoader.get_pipeline_structure(test_cases)
        
        assert structure['total_steps'] == 3
        assert set(structure['all_step_ids']) == {'step1', 'step2', 'step3'}
        assert set(structure['steps_with_inputs']) == {'step1', 'step2', 'step3'}
        assert set(structure['steps_with_expectations']) == {'step1'}
        assert structure['has_batch_processing'] is True
        assert structure['has_intermediate_evaluation'] is True
    
    def test_group_by_pipeline_features(self):
        """测试按 Pipeline 特性分组"""
        test_cases = [
            TestCase.from_dict({
                'id': 'simple_1',
                'inputs': {'text': 'test'}
            }),
            TestCase.from_dict({
                'id': 'multi_step_1',
                'step_inputs': {'step1': {'param': 'value'}}
            }),
            TestCase.from_dict({
                'id': 'batch_1',
                'batch_items': [{'item': 'A'}]
            }),
            TestCase.from_dict({
                'id': 'intermediate_1',
                'intermediate_expectations': {'step1': {'output': 'result'}}
            }),
            TestCase.from_dict({
                'id': 'complex_1',
                'step_inputs': {'step1': {'param': 'value'}},
                'batch_items': [{'item': 'A'}],
                'intermediate_expectations': {'step1': {'output': 'result'}}
            })
        ]
        
        groups = TestsetLoader.group_by_pipeline_features(test_cases)
        
        assert len(groups['simple']) == 1
        assert groups['simple'][0].id == 'simple_1'
        
        assert len(groups['multi_step']) == 2  # multi_step_1 和 complex_1
        
        assert len(groups['batch_processing']) == 2  # batch_1 和 complex_1
        
        assert len(groups['intermediate_evaluation']) == 2  # intermediate_1 和 complex_1
        
        assert len(groups['complex']) == 1
        assert groups['complex'][0].id == 'complex_1'
    
    def test_validate_intermediate_expectations(self):
        """测试验证中间步骤预期格式"""
        # 有效的格式
        valid_tc = TestCase.from_dict({
            'id': 'test_1',
            'intermediate_expectations': {
                'step1': {'output': 'result'}
            }
        })
        errors = validate_testset([valid_tc])
        assert len(errors) == 0
        
        # 无效的格式 - intermediate_expectations 不是字典
        invalid_tc1 = TestCase.from_dict({
            'id': 'test_2',
            'intermediate_expectations': 'invalid'
        })
        errors1 = validate_testset([invalid_tc1])
        assert len(errors1) > 0
        assert 'intermediate_expectations 必须是字典' in errors1[0]
        
        # 无效的格式 - 步骤预期不是字典
        invalid_tc2 = TestCase.from_dict({
            'id': 'test_3',
            'intermediate_expectations': {
                'step1': 'invalid'
            }
        })
        errors2 = validate_testset([invalid_tc2])
        assert len(errors2) > 0
        assert 'intermediate_expectations[step1] 必须是字典' in errors2[0]
    
    def test_validate_evaluation_config(self):
        """测试验证评估配置格式"""
        # 有效的格式
        valid_tc = TestCase.from_dict({
            'id': 'test_1',
            'evaluation_config': {
                'evaluate_intermediate': True,
                'strict_mode': False
            }
        })
        errors = validate_testset([valid_tc])
        assert len(errors) == 0
        
        # 无效的格式 - evaluation_config 不是字典
        invalid_tc = TestCase.from_dict({
            'id': 'test_2',
            'evaluation_config': 'invalid'
        })
        errors = validate_testset([invalid_tc])
        assert len(errors) > 0
        assert 'evaluation_config 必须是字典' in errors[0]


class TestRealWorldPipelineExamples:
    """测试真实的 Pipeline 测试集示例"""
    
    def test_load_pipeline_multi_step_examples(self):
        """测试加载多步骤 Pipeline 示例"""
        testset_file = Path('examples/testsets/pipeline_multi_step_examples.jsonl')
        
        if not testset_file.exists():
            pytest.skip(f"测试文件不存在: {testset_file}")
        
        test_cases = load_testset(testset_file)
        
        assert len(test_cases) > 0
        
        # 检查是否有多步骤测试用例
        multi_step_cases = [tc for tc in test_cases if tc.has_step_inputs()]
        assert len(multi_step_cases) > 0
        
        # 检查是否有中间步骤评估
        intermediate_cases = TestsetLoader.get_intermediate_evaluation_test_cases(test_cases)
        assert len(intermediate_cases) > 0
    
    def test_load_pipeline_batch_aggregation_examples(self):
        """测试加载批量聚合 Pipeline 示例"""
        testset_file = Path('examples/testsets/pipeline_batch_aggregation_examples.jsonl')
        
        if not testset_file.exists():
            pytest.skip(f"测试文件不存在: {testset_file}")
        
        test_cases = load_testset(testset_file)
        
        assert len(test_cases) > 0
        
        # 检查是否有批量处理测试用例
        batch_cases = TestsetLoader.get_batch_test_cases(test_cases)
        assert len(batch_cases) > 0
        
        # 检查是否有预期聚合结果
        aggregation_cases = [tc for tc in test_cases if tc.has_expected_aggregation()]
        assert len(aggregation_cases) > 0
    
    def test_load_pipeline_intermediate_evaluation_examples(self):
        """测试加载中间步骤评估示例"""
        testset_file = Path('examples/testsets/pipeline_intermediate_evaluation_examples.jsonl')
        
        if not testset_file.exists():
            pytest.skip(f"测试文件不存在: {testset_file}")
        
        test_cases = load_testset(testset_file)
        
        assert len(test_cases) > 0
        
        # 检查是否有中间步骤评估
        intermediate_cases = TestsetLoader.get_intermediate_evaluation_test_cases(test_cases)
        assert len(intermediate_cases) > 0
        
        # 检查评估配置
        for tc in intermediate_cases:
            if tc.evaluation_config:
                # 如果有评估配置，应该包含 evaluate_intermediate
                assert isinstance(tc.evaluation_config, dict)
    
    def test_load_pipeline_complex_scenarios(self):
        """测试加载复杂场景示例"""
        testset_file = Path('examples/testsets/pipeline_complex_scenarios.jsonl')
        
        if not testset_file.exists():
            pytest.skip(f"测试文件不存在: {testset_file}")
        
        test_cases = load_testset(testset_file)
        
        assert len(test_cases) > 0
        
        # 分析 Pipeline 结构
        structure = TestsetLoader.get_pipeline_structure(test_cases)
        assert structure['total_steps'] > 0
        
        # 按特性分组
        groups = TestsetLoader.group_by_pipeline_features(test_cases)
        
        # 应该有复杂的测试用例（包含多个特性）
        if len(groups['complex']) > 0:
            complex_tc = groups['complex'][0]
            assert complex_tc.has_step_inputs()
            assert complex_tc.has_batch_data()
            assert complex_tc.has_intermediate_expectations()


class TestPipelineIntegration:
    """测试 Pipeline 集成场景"""
    
    def test_complete_pipeline_workflow(self, tmp_path):
        """测试完整的 Pipeline 工作流"""
        # 创建一个完整的 Pipeline 测试集
        testset_file = tmp_path / "complete_pipeline.jsonl"
        
        test_data = {
            'id': 'complete_pipeline_test',
            'tags': ['integration', 'complete'],
            'inputs': {
                'dataset': 'customer_reviews'
            },
            'step_inputs': {
                'load_data': {
                    'source': 'database',
                    'limit': 100
                },
                'preprocess': {
                    'lowercase': True,
                    'remove_stopwords': True
                },
                'analyze_sentiment': {
                    'model': 'advanced',
                    'batch_size': 10
                },
                'aggregate_results': {
                    'strategy': 'stats'
                }
            },
            'batch_items': [
                {'review': 'Great product!', 'rating': 5},
                {'review': 'Not satisfied', 'rating': 2},
                {'review': 'Good value', 'rating': 4}
            ],
            'intermediate_expectations': {
                'preprocess': {
                    'items_processed': 3
                },
                'analyze_sentiment': {
                    'positive_count': 2,
                    'negative_count': 1
                }
            },
            'expected_aggregation': {
                'total_reviews': 3,
                'average_rating': 3.67,
                'sentiment_distribution': {
                    'positive': 2,
                    'negative': 1
                }
            },
            'expected_outputs': {
                'overall_sentiment': 'positive',
                'recommendation': 'maintain_quality'
            },
            'evaluation_config': {
                'evaluate_intermediate': True,
                'evaluate_final': True,
                'evaluate_aggregation': True,
                'strict_mode': False,
                'tolerance': 0.1,
                'ignore_fields': ['timestamp', 'processing_time']
            }
        }
        
        with open(testset_file, 'w', encoding='utf-8') as f:
            f.write(json.dumps(test_data, ensure_ascii=False) + '\n')
        
        # 加载测试集
        test_cases = load_testset(testset_file)
        assert len(test_cases) == 1
        
        tc = test_cases[0]
        
        # 验证所有特性
        assert tc.has_step_inputs()
        assert tc.has_batch_data()
        assert tc.has_intermediate_expectations()
        assert tc.has_expected_aggregation()
        
        # 验证评估配置
        assert tc.should_evaluate_intermediate()
        assert tc.should_evaluate_final()
        assert tc.should_evaluate_aggregation()
        assert not tc.is_strict_mode()
        assert tc.get_tolerance() == 0.1
        assert 'timestamp' in tc.get_ignore_fields()
        
        # 验证步骤数据提取
        step_ids = tc.get_all_step_ids()
        assert len(step_ids) == 4
        
        for step_id in step_ids:
            step_data = TestsetLoader.extract_step_data(tc, step_id)
            if step_id in tc.step_inputs:
                assert 'inputs' in step_data
            if step_id in tc.intermediate_expectations:
                assert 'expected' in step_data
        
        # 验证批量数据
        assert tc.get_batch_size() == 3
        
        # 验证测试集有效性
        errors = validate_testset(test_cases)
        assert len(errors) == 0
