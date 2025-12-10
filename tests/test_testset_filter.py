# tests/test_testset_filter.py
"""
TestsetFilter 单元测试
"""

import pytest
from unittest.mock import patch, Mock

from src.testset_filter import TestsetFilter, filter_samples_by_tags


class TestTestsetFilter:
    """测试 TestsetFilter 类"""
    
    def test_filter_initialization(self):
        """测试过滤器初始化"""
        filter_obj = TestsetFilter()
        
        assert filter_obj.filtered_count == 0
        assert filter_obj.total_count == 0
    
    def test_filter_by_tags_no_filters(self, sample_testset):
        """测试无过滤条件时返回原样本"""
        filter_obj = TestsetFilter()
        
        result = filter_obj.filter_by_tags(sample_testset)
        
        assert result == sample_testset
        assert filter_obj.total_count == 0  # 没有设置过滤条件时不更新计数
    
    def test_filter_by_tags_include_single(self, sample_testset):
        """测试包含单个标签的过滤"""
        filter_obj = TestsetFilter()
        
        result = filter_obj.filter_by_tags(sample_testset, include_tags=["test"])
        
        assert len(result) == 2  # sample1 和 sample2 包含 "test" 标签
        assert result[0]["id"] == "sample1"
        assert result[1]["id"] == "sample2"
        assert filter_obj.total_count == 3
        assert filter_obj.filtered_count == 2
    
    def test_filter_by_tags_include_multiple(self, sample_testset):
        """测试包含多个标签的过滤"""
        filter_obj = TestsetFilter()
        
        result = filter_obj.filter_by_tags(sample_testset, include_tags=["test", "regression"])
        
        assert len(result) == 3  # 所有样本都包含至少一个指定标签
        assert filter_obj.filtered_count == 3
    
    def test_filter_by_tags_exclude_single(self, sample_testset):
        """测试排除单个标签的过滤"""
        filter_obj = TestsetFilter()
        
        result = filter_obj.filter_by_tags(sample_testset, exclude_tags=["regression"])
        
        assert len(result) == 2  # 排除包含 "regression" 的 sample3
        assert result[0]["id"] == "sample1"
        assert result[1]["id"] == "sample2"
        assert filter_obj.filtered_count == 2
    
    def test_filter_by_tags_exclude_multiple(self, sample_testset):
        """测试排除多个标签的过滤"""
        filter_obj = TestsetFilter()
        
        result = filter_obj.filter_by_tags(sample_testset, exclude_tags=["edge_case", "regression"])
        
        assert len(result) == 1  # 只有 sample1 不包含排除的标签
        assert result[0]["id"] == "sample1"
        assert filter_obj.filtered_count == 1
    
    def test_filter_by_tags_include_and_exclude(self, sample_testset):
        """测试同时使用包含和排除过滤"""
        filter_obj = TestsetFilter()
        
        result = filter_obj.filter_by_tags(
            sample_testset, 
            include_tags=["test"], 
            exclude_tags=["edge_case"]
        )
        
        assert len(result) == 1  # 只有 sample1 包含 "test" 且不包含 "edge_case"
        assert result[0]["id"] == "sample1"
        assert filter_obj.filtered_count == 1
    
    def test_filter_by_tags_no_matches(self, sample_testset):
        """测试没有匹配样本的情况"""
        filter_obj = TestsetFilter()
        
        result = filter_obj.filter_by_tags(sample_testset, include_tags=["nonexistent"])
        
        assert len(result) == 0
        assert filter_obj.filtered_count == 0
    
    def test_filter_by_tags_samples_without_tags(self):
        """测试处理没有标签的样本"""
        samples = [
            {"id": "sample1", "text": "无标签样本1"},
            {"id": "sample2", "tags": [], "text": "空标签样本"},
            {"id": "sample3", "tags": ["test"], "text": "有标签样本"}
        ]
        
        filter_obj = TestsetFilter()
        result = filter_obj.filter_by_tags(samples, include_tags=["test"])
        
        assert len(result) == 1
        assert result[0]["id"] == "sample3"
    
    def test_filter_by_scenario(self, sample_testset):
        """测试按场景过滤"""
        filter_obj = TestsetFilter()
        
        result = filter_obj.filter_by_scenario(sample_testset, ["normal"])
        
        assert len(result) == 2  # sample1 和 sample3 的场景是 "normal"
        assert result[0]["id"] == "sample1"
        assert result[1]["id"] == "sample3"
    
    def test_filter_by_scenario_multiple(self, sample_testset):
        """测试按多个场景过滤"""
        filter_obj = TestsetFilter()
        
        result = filter_obj.filter_by_scenario(sample_testset, ["normal", "edge"])
        
        assert len(result) == 3  # 所有样本
    
    def test_filter_by_scenario_no_scenarios(self, sample_testset):
        """测试无场景过滤条件"""
        filter_obj = TestsetFilter()
        
        result = filter_obj.filter_by_scenario(sample_testset, [])
        
        assert result == sample_testset
    
    def test_filter_by_scenario_missing_field(self):
        """测试处理缺少场景字段的样本"""
        samples = [
            {"id": "sample1", "text": "无场景字段"},
            {"id": "sample2", "scenario": "normal", "text": "有场景字段"}
        ]
        
        filter_obj = TestsetFilter()
        result = filter_obj.filter_by_scenario(samples, ["normal"])
        
        assert len(result) == 1
        assert result[0]["id"] == "sample2"
    
    def test_filter_by_priority(self, sample_testset):
        """测试按优先级过滤"""
        filter_obj = TestsetFilter()
        
        result = filter_obj.filter_by_priority(sample_testset, ["high"])
        
        assert len(result) == 2  # sample1 和 sample3 的优先级是 "high"
        assert result[0]["id"] == "sample1"
        assert result[1]["id"] == "sample3"
    
    def test_filter_by_priority_multiple(self, sample_testset):
        """测试按多个优先级过滤"""
        filter_obj = TestsetFilter()
        
        result = filter_obj.filter_by_priority(sample_testset, ["high", "medium"])
        
        assert len(result) == 3  # 所有样本
    
    def test_filter_by_priority_no_priorities(self, sample_testset):
        """测试无优先级过滤条件"""
        filter_obj = TestsetFilter()
        
        result = filter_obj.filter_by_priority(sample_testset, [])
        
        assert result == sample_testset
    
    def test_get_tag_statistics(self, sample_testset):
        """测试获取标签统计"""
        filter_obj = TestsetFilter()
        
        stats = filter_obj.get_tag_statistics(sample_testset)
        
        expected_stats = {
            "test": 2,
            "basic": 1,
            "edge_case": 1,
            "regression": 1
        }
        assert stats == expected_stats
    
    def test_get_tag_statistics_empty(self):
        """测试空样本的标签统计"""
        filter_obj = TestsetFilter()
        
        stats = filter_obj.get_tag_statistics([])
        
        assert stats == {}
    
    def test_get_tag_statistics_no_tags(self):
        """测试无标签样本的统计"""
        samples = [
            {"id": "sample1", "text": "无标签"},
            {"id": "sample2", "tags": [], "text": "空标签"}
        ]
        
        filter_obj = TestsetFilter()
        stats = filter_obj.get_tag_statistics(samples)
        
        assert stats == {}
    
    def test_get_scenario_statistics(self, sample_testset):
        """测试获取场景统计"""
        filter_obj = TestsetFilter()
        
        stats = filter_obj.get_scenario_statistics(sample_testset)
        
        expected_stats = {
            "normal": 2,
            "edge": 1
        }
        assert stats == expected_stats
    
    def test_get_scenario_statistics_missing_field(self):
        """测试缺少场景字段的统计"""
        samples = [
            {"id": "sample1", "text": "无场景字段"},
            {"id": "sample2", "scenario": "normal", "text": "有场景字段"}
        ]
        
        filter_obj = TestsetFilter()
        stats = filter_obj.get_scenario_statistics(samples)
        
        expected_stats = {
            "未指定": 1,
            "normal": 1
        }
        assert stats == expected_stats
    
    @patch('src.testset_filter.console')
    def test_print_filter_summary(self, mock_console, sample_testset):
        """测试打印过滤摘要"""
        filter_obj = TestsetFilter()
        filter_obj.filter_by_tags(sample_testset, include_tags=["test"])
        
        filter_obj.print_filter_summary(include_tags=["test"])
        
        # 验证 console.print 被调用
        assert mock_console.print.call_count >= 4  # 至少4次打印调用
    
    @patch('src.testset_filter.console')
    def test_print_filter_summary_no_data(self, mock_console):
        """测试无数据时的过滤摘要"""
        filter_obj = TestsetFilter()
        
        filter_obj.print_filter_summary()
        
        # 无数据时不应该打印
        mock_console.print.assert_not_called()
    
    @patch('src.testset_filter.console')
    def test_print_tag_statistics(self, mock_console, sample_testset):
        """测试打印标签统计"""
        filter_obj = TestsetFilter()
        
        filter_obj.print_tag_statistics(sample_testset)
        
        # 验证 console.print 被调用
        assert mock_console.print.call_count >= 5  # 标题 + 4个标签
    
    @patch('src.testset_filter.console')
    def test_print_tag_statistics_no_tags(self, mock_console):
        """测试无标签时的统计打印"""
        samples = [{"id": "sample1", "text": "无标签"}]
        filter_obj = TestsetFilter()
        
        filter_obj.print_tag_statistics(samples)
        
        # 应该打印"没有找到任何标签"
        mock_console.print.assert_called()


class TestFilterSamplesByTags:
    """测试便捷函数 filter_samples_by_tags"""
    
    @patch('src.testset_filter.TestsetFilter')
    def test_filter_samples_by_tags_basic(self, mock_filter_class, sample_testset):
        """测试基本的标签过滤功能"""
        mock_filter = Mock()
        mock_filter.filter_by_tags.return_value = [sample_testset[0]]
        mock_filter_class.return_value = mock_filter
        
        result = filter_samples_by_tags(
            sample_testset, 
            include_tags=["test"], 
            show_stats=False
        )
        
        mock_filter.filter_by_tags.assert_called_once_with(
            sample_testset, ["test"], None
        )
        assert result == [sample_testset[0]]
    
    @patch('src.testset_filter.TestsetFilter')
    def test_filter_samples_by_tags_with_stats(self, mock_filter_class, sample_testset):
        """测试带统计信息的标签过滤"""
        mock_filter = Mock()
        mock_filter.filter_by_tags.return_value = sample_testset
        mock_filter_class.return_value = mock_filter
        
        result = filter_samples_by_tags(
            sample_testset, 
            include_tags=["test"], 
            show_stats=True
        )
        
        # 验证统计方法被调用
        mock_filter.print_filter_summary.assert_called_once_with(["test"], None)
        mock_filter.print_tag_statistics.assert_called_once_with(sample_testset)
    
    @patch('src.testset_filter.TestsetFilter')
    def test_filter_samples_by_tags_no_results_no_stats(self, mock_filter_class, sample_testset):
        """测试无结果时不显示标签统计"""
        mock_filter = Mock()
        mock_filter.filter_by_tags.return_value = []
        mock_filter_class.return_value = mock_filter
        
        result = filter_samples_by_tags(
            sample_testset, 
            include_tags=["nonexistent"], 
            show_stats=True
        )
        
        # 验证过滤摘要被调用，但标签统计不被调用（因为结果为空）
        mock_filter.print_filter_summary.assert_called_once()
        mock_filter.print_tag_statistics.assert_not_called()
        assert result == []


class TestEdgeCases:
    """测试边界情况"""
    
    def test_filter_empty_samples(self):
        """测试过滤空样本列表"""
        filter_obj = TestsetFilter()
        
        result = filter_obj.filter_by_tags([], include_tags=["test"])
        
        assert result == []
        assert filter_obj.total_count == 0
        assert filter_obj.filtered_count == 0
    
    def test_filter_samples_with_none_tags(self):
        """测试处理 tags 为 None 的样本"""
        samples = [
            {"id": "sample1", "tags": None, "text": "标签为None"},
            {"id": "sample2", "tags": ["test"], "text": "正常标签"}
        ]
        
        filter_obj = TestsetFilter()
        result = filter_obj.filter_by_tags(samples, include_tags=["test"])
        
        assert len(result) == 1
        assert result[0]["id"] == "sample2"
    
    def test_filter_samples_with_non_list_tags(self):
        """测试处理 tags 不是列表的样本"""
        samples = [
            {"id": "sample1", "tags": "test", "text": "标签为字符串"},
            {"id": "sample2", "tags": ["test"], "text": "正常标签"}
        ]
        
        filter_obj = TestsetFilter()
        
        # 这种情况下应该优雅处理，不抛出异常
        try:
            result = filter_obj.filter_by_tags(samples, include_tags=["test"])
            # 只有正常格式的样本应该被匹配
            assert len(result) <= 1
        except (TypeError, AttributeError):
            # 如果抛出异常也是可以接受的，因为数据格式不正确
            pass
    
    def test_filter_by_scenario_empty_string(self):
        """测试场景为空字符串的情况"""
        samples = [
            {"id": "sample1", "scenario": "", "text": "空场景"},
            {"id": "sample2", "scenario": "normal", "text": "正常场景"}
        ]
        
        filter_obj = TestsetFilter()
        result = filter_obj.filter_by_scenario(samples, [""])
        
        assert len(result) == 1
        assert result[0]["id"] == "sample1"
    
    def test_case_sensitive_tags(self):
        """测试标签的大小写敏感性"""
        samples = [
            {"id": "sample1", "tags": ["Test"], "text": "大写标签"},
            {"id": "sample2", "tags": ["test"], "text": "小写标签"}
        ]
        
        filter_obj = TestsetFilter()
        result = filter_obj.filter_by_tags(samples, include_tags=["test"])
        
        # 应该只匹配小写的标签
        assert len(result) == 1
        assert result[0]["id"] == "sample2"