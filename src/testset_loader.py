# src/testset_loader.py
"""
Testset Loader - 支持批量处理和 Pipeline 级别的测试集加载

支持的测试集格式:
1. 简单格式: 每行一个 JSON 对象，包含测试用例的输入和预期输出
2. 批量格式: 支持 batch_items 字段，用于批量处理步骤
3. 步骤级格式: 支持 step_inputs 字段，为不同步骤提供不同的输入数据
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class TestCase:
    """测试用例数据结构"""
    id: str
    tags: List[str] = field(default_factory=list)
    
    # 全局输入（用于 Pipeline 的初始输入）
    inputs: Dict[str, Any] = field(default_factory=dict)
    
    # 步骤级输入（可选，为特定步骤提供输入）
    step_inputs: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # 批量处理数据（可选，用于批量处理步骤）
    batch_items: Optional[List[Dict[str, Any]]] = None
    
    # 预期输出
    expected_outputs: Dict[str, Any] = field(default_factory=dict)
    
    # 预期聚合结果（可选，用于批量聚合步骤）
    expected_aggregation: Optional[Any] = None
    
    # 中间步骤预期结果（可选，用于验证中间步骤）
    intermediate_expectations: Dict[str, Any] = field(default_factory=dict)
    
    # 评估配置（可选，控制评估行为）
    evaluation_config: Dict[str, Any] = field(default_factory=dict)
    
    # 原始数据（保留所有字段）
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """后处理：从 raw_data 中提取未明确指定的字段到 inputs"""
        if self.raw_data:
            # 保留的特殊字段
            reserved_fields = {
                'id', 'tags', 'inputs', 'step_inputs', 'batch_items',
                'expected_outputs', 'expected_aggregation',
                'intermediate_expectations', 'evaluation_config'
            }
            
            # 将未保留的字段添加到 inputs
            for key, value in self.raw_data.items():
                if key not in reserved_fields and key not in self.inputs:
                    self.inputs[key] = value
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TestCase:
        """从字典创建 TestCase 实例"""
        # 提取标准字段
        test_id = data.get('id', '')
        tags = data.get('tags', [])
        
        # 确保 tags 是列表
        if isinstance(tags, str):
            tags = [tags]
        elif not isinstance(tags, list):
            tags = []
        
        # 提取输入字段
        inputs = data.get('inputs', {})
        step_inputs = data.get('step_inputs', {})
        batch_items = data.get('batch_items')
        
        # 提取预期输出
        expected_outputs = data.get('expected_outputs', {})
        expected_aggregation = data.get('expected_aggregation')
        
        # 提取中间步骤预期和评估配置
        intermediate_expectations = data.get('intermediate_expectations', {})
        evaluation_config = data.get('evaluation_config', {})
        
        return cls(
            id=test_id,
            tags=tags,
            inputs=inputs,
            step_inputs=step_inputs,
            batch_items=batch_items,
            expected_outputs=expected_outputs,
            expected_aggregation=expected_aggregation,
            intermediate_expectations=intermediate_expectations,
            evaluation_config=evaluation_config,
            raw_data=data
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = {
            'id': self.id,
            'tags': self.tags,
        }
        
        # 添加输入字段
        if self.inputs:
            result['inputs'] = self.inputs
        
        if self.step_inputs:
            result['step_inputs'] = self.step_inputs
        
        if self.batch_items is not None:
            result['batch_items'] = self.batch_items
        
        # 添加预期输出
        if self.expected_outputs:
            result['expected_outputs'] = self.expected_outputs
        
        if self.expected_aggregation is not None:
            result['expected_aggregation'] = self.expected_aggregation
        
        # 添加中间步骤预期和评估配置
        if self.intermediate_expectations:
            result['intermediate_expectations'] = self.intermediate_expectations
        
        if self.evaluation_config:
            result['evaluation_config'] = self.evaluation_config
        
        # 添加原始数据中的其他字段
        for key, value in self.raw_data.items():
            if key not in result:
                result[key] = value
        
        return result
    
    def get_input(self, key: str, default: Any = None) -> Any:
        """获取输入值（优先从 inputs 中获取，然后从 raw_data 中获取）"""
        if key in self.inputs:
            return self.inputs[key]
        return self.raw_data.get(key, default)
    
    def get_step_input(self, step_id: str, key: str, default: Any = None) -> Any:
        """获取特定步骤的输入值"""
        if step_id in self.step_inputs:
            return self.step_inputs[step_id].get(key, default)
        return default
    
    def has_batch_data(self) -> bool:
        """检查是否包含批量处理数据"""
        return self.batch_items is not None and len(self.batch_items) > 0
    
    def has_step_inputs(self) -> bool:
        """检查是否包含步骤级输入"""
        return bool(self.step_inputs)
    
    def has_expected_aggregation(self) -> bool:
        """检查是否包含预期聚合结果"""
        return self.expected_aggregation is not None
    
    def has_intermediate_expectations(self) -> bool:
        """检查是否包含中间步骤预期结果"""
        return bool(self.intermediate_expectations)
    
    def get_intermediate_expectation(self, step_id: str) -> Optional[Dict[str, Any]]:
        """获取特定步骤的预期结果"""
        return self.intermediate_expectations.get(step_id)
    
    def should_evaluate_intermediate(self) -> bool:
        """检查是否应该评估中间步骤"""
        return self.evaluation_config.get('evaluate_intermediate', False)
    
    def should_evaluate_final(self) -> bool:
        """检查是否应该评估最终输出"""
        return self.evaluation_config.get('evaluate_final', True)
    
    def should_evaluate_aggregation(self) -> bool:
        """检查是否应该评估聚合结果"""
        # 如果有预期聚合结果，默认评估
        if self.has_expected_aggregation():
            return self.evaluation_config.get('evaluate_aggregation', True)
        return False
    
    def is_strict_mode(self) -> bool:
        """检查是否使用严格模式评估"""
        return self.evaluation_config.get('strict_mode', False)
    
    def get_tolerance(self) -> float:
        """获取数值比较的容差"""
        return self.evaluation_config.get('tolerance', 0.0)
    
    def get_ignore_fields(self) -> List[str]:
        """获取评估时应忽略的字段列表"""
        ignore_fields = self.evaluation_config.get('ignore_fields', [])
        if isinstance(ignore_fields, list):
            return ignore_fields
        return []
    
    def get_all_step_ids(self) -> List[str]:
        """获取所有涉及的步骤 ID（从 step_inputs 和 intermediate_expectations）"""
        step_ids = set()
        step_ids.update(self.step_inputs.keys())
        step_ids.update(self.intermediate_expectations.keys())
        return sorted(list(step_ids))
    
    def get_batch_size(self) -> int:
        """获取批量数据的大小"""
        if self.has_batch_data():
            return len(self.batch_items)
        return 0


class TestsetLoader:
    """测试集加载器"""
    
    @staticmethod
    def load_testset(file_path: Path) -> List[TestCase]:
        """
        从 JSONL 文件加载测试集
        
        Args:
            file_path: 测试集文件路径
            
        Returns:
            测试用例列表
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误
        """
        if not file_path.exists():
            raise FileNotFoundError(f"测试集文件不存在: {file_path}")
        
        test_cases = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                    test_case = TestCase.from_dict(data)
                    test_cases.append(test_case)
                except json.JSONDecodeError as e:
                    raise ValueError(
                        f"测试集文件第 {line_num} 行 JSON 解析错误: {e}"
                    )
                except Exception as e:
                    raise ValueError(
                        f"测试集文件第 {line_num} 行处理错误: {e}"
                    )
        
        if not test_cases:
            raise ValueError(f"测试集文件为空: {file_path}")
        
        return test_cases
    
    @staticmethod
    def load_testset_dict(file_path: Path) -> List[Dict[str, Any]]:
        """
        从 JSONL 文件加载测试集（返回字典格式，用于向后兼容）
        
        Args:
            file_path: 测试集文件路径
            
        Returns:
            测试用例字典列表
        """
        test_cases = TestsetLoader.load_testset(file_path)
        return [tc.to_dict() for tc in test_cases]
    
    @staticmethod
    def validate_testset(test_cases: List[TestCase]) -> List[str]:
        """
        验证测试集的有效性
        
        Args:
            test_cases: 测试用例列表
            
        Returns:
            错误信息列表（如果为空则验证通过）
        """
        errors = []
        
        # 检查测试用例 ID 唯一性
        ids = [tc.id for tc in test_cases]
        duplicate_ids = [id for id in ids if ids.count(id) > 1]
        if duplicate_ids:
            errors.append(f"重复的测试用例 ID: {set(duplicate_ids)}")
        
        # 检查每个测试用例
        for i, tc in enumerate(test_cases):
            if not tc.id:
                errors.append(f"测试用例 #{i+1} 缺少 ID")
            
            # 检查批量数据格式
            if tc.has_batch_data():
                if not isinstance(tc.batch_items, list):
                    errors.append(
                        f"测试用例 {tc.id}: batch_items 必须是列表"
                    )
                elif not all(isinstance(item, dict) for item in tc.batch_items):
                    errors.append(
                        f"测试用例 {tc.id}: batch_items 中的每个元素必须是字典"
                    )
            
            # 检查步骤输入格式
            if tc.has_step_inputs():
                if not isinstance(tc.step_inputs, dict):
                    errors.append(
                        f"测试用例 {tc.id}: step_inputs 必须是字典"
                    )
                else:
                    for step_id, step_input in tc.step_inputs.items():
                        if not isinstance(step_input, dict):
                            errors.append(
                                f"测试用例 {tc.id}: step_inputs[{step_id}] 必须是字典"
                            )
            
            # 检查中间步骤预期格式
            if tc.has_intermediate_expectations():
                if not isinstance(tc.intermediate_expectations, dict):
                    errors.append(
                        f"测试用例 {tc.id}: intermediate_expectations 必须是字典"
                    )
                else:
                    for step_id, expectation in tc.intermediate_expectations.items():
                        if not isinstance(expectation, dict):
                            errors.append(
                                f"测试用例 {tc.id}: intermediate_expectations[{step_id}] 必须是字典"
                            )
            
            # 检查评估配置格式
            if tc.evaluation_config:
                if not isinstance(tc.evaluation_config, dict):
                    errors.append(
                        f"测试用例 {tc.id}: evaluation_config 必须是字典"
                    )
        
        return errors
    
    @staticmethod
    def filter_by_tags(test_cases: List[TestCase], 
                      include_tags: Optional[List[str]] = None,
                      exclude_tags: Optional[List[str]] = None) -> List[TestCase]:
        """
        根据标签过滤测试用例
        
        Args:
            test_cases: 测试用例列表
            include_tags: 包含的标签（任意匹配）
            exclude_tags: 排除的标签（任意匹配）
            
        Returns:
            过滤后的测试用例列表
        """
        filtered = test_cases
        
        if include_tags:
            filtered = [
                tc for tc in filtered
                if any(tag in tc.tags for tag in include_tags)
            ]
        
        if exclude_tags:
            filtered = [
                tc for tc in filtered
                if not any(tag in tc.tags for tag in exclude_tags)
            ]
        
        return filtered
    
    @staticmethod
    def get_batch_test_cases(test_cases: List[TestCase]) -> List[TestCase]:
        """获取包含批量数据的测试用例"""
        return [tc for tc in test_cases if tc.has_batch_data()]
    
    @staticmethod
    def get_step_input_test_cases(test_cases: List[TestCase]) -> List[TestCase]:
        """获取包含步骤级输入的测试用例"""
        return [tc for tc in test_cases if tc.has_step_inputs()]
    
    @staticmethod
    def get_intermediate_evaluation_test_cases(test_cases: List[TestCase]) -> List[TestCase]:
        """获取需要中间步骤评估的测试用例"""
        return [tc for tc in test_cases if tc.has_intermediate_expectations()]
    
    @staticmethod
    def extract_step_data(test_case: TestCase, step_id: str) -> Dict[str, Any]:
        """
        提取特定步骤的所有相关数据
        
        Args:
            test_case: 测试用例
            step_id: 步骤 ID
            
        Returns:
            包含步骤输入和预期输出的字典
        """
        result = {}
        
        # 添加步骤级输入
        if step_id in test_case.step_inputs:
            result['inputs'] = test_case.step_inputs[step_id]
        
        # 添加中间步骤预期
        if step_id in test_case.intermediate_expectations:
            result['expected'] = test_case.intermediate_expectations[step_id]
        
        return result
    
    @staticmethod
    def organize_batch_data(test_cases: List[TestCase]) -> Dict[str, Any]:
        """
        组织批量测试数据
        
        Args:
            test_cases: 测试用例列表
            
        Returns:
            组织后的批量数据，包含统计信息
        """
        batch_test_cases = TestsetLoader.get_batch_test_cases(test_cases)
        
        total_items = sum(tc.get_batch_size() for tc in batch_test_cases)
        
        return {
            'total_test_cases': len(batch_test_cases),
            'total_batch_items': total_items,
            'test_cases': batch_test_cases,
            'average_batch_size': total_items / len(batch_test_cases) if batch_test_cases else 0
        }
    
    @staticmethod
    def get_pipeline_structure(test_cases: List[TestCase]) -> Dict[str, Any]:
        """
        分析测试集中的 Pipeline 结构
        
        Args:
            test_cases: 测试用例列表
            
        Returns:
            Pipeline 结构信息
        """
        all_step_ids = set()
        step_with_inputs = set()
        step_with_expectations = set()
        
        for tc in test_cases:
            all_step_ids.update(tc.get_all_step_ids())
            step_with_inputs.update(tc.step_inputs.keys())
            step_with_expectations.update(tc.intermediate_expectations.keys())
        
        return {
            'total_steps': len(all_step_ids),
            'all_step_ids': sorted(list(all_step_ids)),
            'steps_with_inputs': sorted(list(step_with_inputs)),
            'steps_with_expectations': sorted(list(step_with_expectations)),
            'has_batch_processing': any(tc.has_batch_data() for tc in test_cases),
            'has_intermediate_evaluation': any(tc.has_intermediate_expectations() for tc in test_cases)
        }
    
    @staticmethod
    def group_by_pipeline_features(test_cases: List[TestCase]) -> Dict[str, List[TestCase]]:
        """
        根据 Pipeline 特性对测试用例分组
        
        Args:
            test_cases: 测试用例列表
            
        Returns:
            分组后的测试用例
        """
        return {
            'simple': [tc for tc in test_cases 
                      if not tc.has_step_inputs() 
                      and not tc.has_batch_data() 
                      and not tc.has_intermediate_expectations()],
            'multi_step': [tc for tc in test_cases if tc.has_step_inputs()],
            'batch_processing': [tc for tc in test_cases if tc.has_batch_data()],
            'intermediate_evaluation': [tc for tc in test_cases if tc.has_intermediate_expectations()],
            'complex': [tc for tc in test_cases 
                       if tc.has_step_inputs() 
                       and tc.has_batch_data() 
                       and tc.has_intermediate_expectations()]
        }


# 便捷函数
def load_testset(file_path: Path) -> List[TestCase]:
    """加载测试集"""
    return TestsetLoader.load_testset(file_path)


def load_testset_dict(file_path: Path) -> List[Dict[str, Any]]:
    """加载测试集（字典格式）"""
    return TestsetLoader.load_testset_dict(file_path)


def validate_testset(test_cases: List[TestCase]) -> List[str]:
    """验证测试集"""
    return TestsetLoader.validate_testset(test_cases)


def filter_by_tags(test_cases: List[TestCase],
                  include_tags: Optional[List[str]] = None,
                  exclude_tags: Optional[List[str]] = None) -> List[TestCase]:
    """根据标签过滤测试用例"""
    return TestsetLoader.filter_by_tags(test_cases, include_tags, exclude_tags)
