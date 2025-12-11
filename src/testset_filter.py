# src/testset_filter.py
"""
测试集过滤器模块

提供基于标签、场景等维度的测试样本过滤功能。
"""

from typing import Any, Dict, List, Optional, Set
from rich.console import Console

console = Console()


class TestsetFilter:
    """测试集过滤器类，支持多种过滤维度"""
    
    def __init__(self):
        self.filtered_count = 0
        self.total_count = 0
    
    def filter_by_tags(
        self, 
        samples: List[Dict[str, Any]], 
        include_tags: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        根据标签过滤测试样本
        
        Args:
            samples: 测试样本列表
            include_tags: 包含的标签列表，样本必须包含其中至少一个标签
            exclude_tags: 排除的标签列表，样本不能包含其中任何一个标签
            
        Returns:
            过滤后的样本列表
        """
        if not include_tags and not exclude_tags:
            return samples
        
        self.total_count = len(samples)
        filtered_samples = []
        
        include_set = set(include_tags) if include_tags else None
        exclude_set = set(exclude_tags) if exclude_tags else None

        for sample in samples:
            raw_tags = sample.get("tags") or []
            sample_tags = set(raw_tags)
            
            # 应用 include 过滤
            if include_set and not sample_tags.intersection(include_set):
                continue
                
            # 应用 exclude 过滤
            if exclude_set and sample_tags.intersection(exclude_set):
                continue
                
            filtered_samples.append(sample)
        
        self.filtered_count = len(filtered_samples)
        return filtered_samples
    
    def filter_by_scenario(
        self, 
        samples: List[Dict[str, Any]], 
        scenarios: List[str]
    ) -> List[Dict[str, Any]]:
        """
        根据场景过滤测试样本
        
        Args:
            samples: 测试样本列表
            scenarios: 场景列表
            
        Returns:
            过滤后的样本列表
        """
        if not scenarios:
            return samples
            
        scenario_set = set(scenarios)
        filtered_samples = []
        
        for sample in samples:
            sample_scenario = sample.get("scenario", "")
            if sample_scenario in scenario_set:
                filtered_samples.append(sample)
        
        return filtered_samples
    
    def filter_by_priority(
        self, 
        samples: List[Dict[str, Any]], 
        priorities: List[str]
    ) -> List[Dict[str, Any]]:
        """
        根据优先级过滤测试样本
        
        Args:
            samples: 测试样本列表
            priorities: 优先级列表，如 ["high", "medium"]
            
        Returns:
            过滤后的样本列表
        """
        if not priorities:
            return samples
            
        priority_set = set(priorities)
        filtered_samples = []
        
        for sample in samples:
            sample_priority = sample.get("priority", "")
            if sample_priority in priority_set:
                filtered_samples.append(sample)
        
        return filtered_samples
    
    def get_tag_statistics(self, samples: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        获取样本的标签统计信息
        
        Args:
            samples: 测试样本列表
            
        Returns:
            标签统计字典，键为标签名，值为出现次数
        """
        tag_counts = {}
        
        for sample in samples:
            tags = sample.get("tags", [])
            for tag in tags:
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        
        return tag_counts
    
    def get_scenario_statistics(self, samples: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        获取样本的场景统计信息
        
        Args:
            samples: 测试样本列表
            
        Returns:
            场景统计字典，键为场景名，值为出现次数
        """
        scenario_counts = {}
        
        for sample in samples:
            scenario = sample.get("scenario", "未指定")
            scenario_counts[scenario] = scenario_counts.get(scenario, 0) + 1
        
        return scenario_counts
    
    def print_filter_summary(
        self, 
        include_tags: Optional[List[str]] = None,
        exclude_tags: Optional[List[str]] = None
    ) -> None:
        """
        打印过滤结果摘要
        
        Args:
            include_tags: 包含的标签列表
            exclude_tags: 排除的标签列表
        """
        if self.total_count == 0:
            return
            
        console.print(f"[bold cyan]过滤结果摘要[/]")
        console.print(f"总样本数: {self.total_count}")
        console.print(f"过滤后样本数: {self.filtered_count}")
        console.print(f"过滤比例: {self.filtered_count/self.total_count:.1%}")
        
        if include_tags:
            console.print(f"包含标签: {', '.join(include_tags)}")
        if exclude_tags:
            console.print(f"排除标签: {', '.join(exclude_tags)}")
    
    def print_tag_statistics(self, samples: List[Dict[str, Any]]) -> None:
        """
        打印标签统计信息
        
        Args:
            samples: 测试样本列表
        """
        tag_stats = self.get_tag_statistics(samples)
        
        if not tag_stats:
            console.print("[yellow]没有找到任何标签[/]")
            return
            
        console.print(f"[bold cyan]标签分布统计[/]")
        for tag, count in sorted(tag_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = count / len(samples) * 100
            console.print(f"  {tag}: {count} ({percentage:.1f}%)")


def filter_samples_by_tags(
    samples: List[Dict[str, Any]], 
    include_tags: Optional[List[str]] = None,
    exclude_tags: Optional[List[str]] = None,
    show_stats: bool = True
) -> List[Dict[str, Any]]:
    """
    便捷函数：根据标签过滤样本
    
    Args:
        samples: 测试样本列表
        include_tags: 包含的标签列表
        exclude_tags: 排除的标签列表
        show_stats: 是否显示统计信息
        
    Returns:
        过滤后的样本列表
    """
    filter_obj = TestsetFilter()
    filtered_samples = filter_obj.filter_by_tags(samples, include_tags, exclude_tags)
    
    if show_stats:
        filter_obj.print_filter_summary(include_tags, exclude_tags)
        if filtered_samples:
            filter_obj.print_tag_statistics(filtered_samples)
    
    return filtered_samples