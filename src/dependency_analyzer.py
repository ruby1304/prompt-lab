# src/dependency_analyzer.py
"""
依赖分析器 - 分析 Pipeline 步骤间的依赖关系

提供依赖图构建、拓扑排序和并发组识别功能，
用于支持 Pipeline 的并发执行优化。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional
from collections import defaultdict, deque

from src.models import StepConfig


@dataclass
class DependencyGraph:
    """依赖图数据结构"""
    nodes: List[str]  # 所有节点（步骤ID）
    edges: Dict[str, List[str]]  # node_id -> [dependent_node_ids] 依赖关系
    concurrent_groups: Dict[str, List[str]]  # group_name -> [node_ids] 并发组


class DependencyAnalyzer:
    """
    依赖分析器
    
    分析 Pipeline 步骤间的依赖关系，支持：
    1. 构建依赖图
    2. 拓扑排序
    3. 识别可并发执行的步骤组
    4. 检测循环依赖
    """
    
    def analyze_dependencies(self, steps: List[StepConfig]) -> DependencyGraph:
        """
        分析步骤依赖关系，构建依赖图
        
        Args:
            steps: Pipeline 步骤配置列表
            
        Returns:
            DependencyGraph: 依赖图对象
            
        Raises:
            ValueError: 如果检测到循环依赖
        """
        # 构建节点列表
        nodes = [step.id for step in steps]
        
        # 构建输出键到步骤ID的映射
        output_to_step: Dict[str, str] = {}
        for step in steps:
            if step.output_key:
                output_to_step[step.output_key] = step.id
        
        # 构建依赖边
        edges: Dict[str, List[str]] = defaultdict(list)
        
        for step in steps:
            # 从 input_mapping 中提取依赖
            for param, source in step.input_mapping.items():
                # 如果源是其他步骤的输出
                if source in output_to_step:
                    source_step = output_to_step[source]
                    # 不能依赖自己
                    if source_step != step.id:
                        edges[step.id].append(source_step)
            
            # 从 depends_on 中提取显式依赖
            for dep_step_id in step.depends_on:
                if dep_step_id in nodes and dep_step_id != step.id:
                    if dep_step_id not in edges[step.id]:
                        edges[step.id].append(dep_step_id)
        
        # 确保所有节点都在 edges 中（即使没有依赖）
        for node in nodes:
            if node not in edges:
                edges[node] = []
        
        # 提取并发组
        concurrent_groups: Dict[str, List[str]] = defaultdict(list)
        for step in steps:
            if step.concurrent_group:
                concurrent_groups[step.concurrent_group].append(step.id)
        
        # 创建依赖图
        dependency_graph = DependencyGraph(
            nodes=nodes,
            edges=dict(edges),
            concurrent_groups=dict(concurrent_groups)
        )
        
        # 检测循环依赖
        self._detect_cycles(dependency_graph)
        
        return dependency_graph
    
    def find_concurrent_groups(self, dependency_graph: DependencyGraph) -> List[List[str]]:
        """
        找出可以并发执行的步骤组
        
        基于依赖关系和拓扑排序，将步骤分组为可以并发执行的批次。
        同一批次内的步骤互不依赖，可以并发执行。
        
        Args:
            dependency_graph: 依赖图
            
        Returns:
            List[List[str]]: 并发组列表，每个组包含可以并发执行的步骤ID
        """
        # 如果配置中已经定义了并发组，需要将它们整合到自动分组中
        if dependency_graph.concurrent_groups:
            # 首先进行自动分组
            auto_groups = self._auto_group_by_dependencies(dependency_graph)
            
            # 然后尝试合并显式定义的并发组
            result_groups = []
            processed_steps = set()
            
            for auto_group in auto_groups:
                # 检查这个自动组中是否有显式并发组的步骤
                explicit_groups_in_auto = {}
                ungrouped_steps = []
                
                for step_id in auto_group:
                    found_in_explicit = False
                    for group_name, explicit_steps in dependency_graph.concurrent_groups.items():
                        if step_id in explicit_steps:
                            if group_name not in explicit_groups_in_auto:
                                explicit_groups_in_auto[group_name] = []
                            explicit_groups_in_auto[group_name].append(step_id)
                            found_in_explicit = True
                            break
                    
                    if not found_in_explicit:
                        ungrouped_steps.append(step_id)
                
                # 添加显式并发组（如果它们的所有成员都在这个自动组中）
                for group_name, explicit_steps in dependency_graph.concurrent_groups.items():
                    if group_name in explicit_groups_in_auto:
                        full_group = dependency_graph.concurrent_groups[group_name]
                        # 检查是否所有成员都在当前自动组中
                        if all(s in auto_group for s in full_group):
                            # 验证它们确实可以并发
                            if self._can_execute_concurrently(full_group, dependency_graph):
                                result_groups.append(full_group)
                                processed_steps.update(full_group)
                            else:
                                # 如果不能并发，按依赖关系拆分
                                split_groups = self._split_by_dependencies(full_group, dependency_graph)
                                result_groups.extend(split_groups)
                                processed_steps.update(full_group)
                
                # 添加未分组的步骤
                for step_id in auto_group:
                    if step_id not in processed_steps:
                        result_groups.append([step_id])
                        processed_steps.add(step_id)
            
            return result_groups
        
        # 如果没有定义并发组，基于依赖关系自动分组
        return self._auto_group_by_dependencies(dependency_graph)
    
    def topological_sort(self, dependency_graph: DependencyGraph) -> List[str]:
        """
        对依赖图进行拓扑排序
        
        使用 Kahn 算法进行拓扑排序，返回一个执行顺序，
        保证每个步骤在其依赖步骤之后执行。
        
        Args:
            dependency_graph: 依赖图
            
        Returns:
            List[str]: 拓扑排序后的步骤ID列表
            
        Raises:
            ValueError: 如果存在循环依赖
        """
        # 计算每个节点的入度
        in_degree: Dict[str, int] = {node: 0 for node in dependency_graph.nodes}
        
        for node, dependencies in dependency_graph.edges.items():
            for dep in dependencies:
                in_degree[node] += 1
        
        # 找出所有入度为0的节点（没有依赖的节点）
        queue = deque([node for node in dependency_graph.nodes if in_degree[node] == 0])
        
        result = []
        
        while queue:
            # 取出一个入度为0的节点
            node = queue.popleft()
            result.append(node)
            
            # 找出所有依赖当前节点的节点
            for other_node, dependencies in dependency_graph.edges.items():
                if node in dependencies:
                    in_degree[other_node] -= 1
                    if in_degree[other_node] == 0:
                        queue.append(other_node)
        
        # 如果结果长度不等于节点数，说明存在循环依赖
        if len(result) != len(dependency_graph.nodes):
            raise ValueError("检测到循环依赖，无法进行拓扑排序")
        
        return result
    
    def _detect_cycles(self, dependency_graph: DependencyGraph) -> None:
        """
        检测依赖图中的循环依赖
        
        使用深度优先搜索（DFS）检测循环。
        
        Args:
            dependency_graph: 依赖图
            
        Raises:
            ValueError: 如果检测到循环依赖
        """
        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        
        def dfs(node: str, path: List[str]) -> Optional[List[str]]:
            """DFS 检测循环，返回循环路径"""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for dep in dependency_graph.edges.get(node, []):
                if dep not in visited:
                    cycle_path = dfs(dep, path.copy())
                    if cycle_path:
                        return cycle_path
                elif dep in rec_stack:
                    # 找到循环
                    cycle_start = path.index(dep)
                    return path[cycle_start:] + [dep]
            
            rec_stack.remove(node)
            return None
        
        for node in dependency_graph.nodes:
            if node not in visited:
                cycle_path = dfs(node, [])
                if cycle_path:
                    cycle_str = " -> ".join(cycle_path)
                    raise ValueError(f"检测到循环依赖: {cycle_str}")
    
    def _can_execute_concurrently(
        self, 
        step_ids: List[str], 
        dependency_graph: DependencyGraph
    ) -> bool:
        """
        检查一组步骤是否可以并发执行（互不依赖）
        
        Args:
            step_ids: 步骤ID列表
            dependency_graph: 依赖图
            
        Returns:
            bool: 如果步骤间互不依赖，返回 True
        """
        step_set = set(step_ids)
        
        for step_id in step_ids:
            dependencies = dependency_graph.edges.get(step_id, [])
            # 检查是否依赖组内其他步骤
            for dep in dependencies:
                if dep in step_set:
                    return False
        
        return True
    
    def _split_by_dependencies(
        self, 
        step_ids: List[str], 
        dependency_graph: DependencyGraph
    ) -> List[List[str]]:
        """
        根据依赖关系拆分步骤组
        
        Args:
            step_ids: 步骤ID列表
            dependency_graph: 依赖图
            
        Returns:
            List[List[str]]: 拆分后的步骤组列表
        """
        # 创建子图
        sub_graph = DependencyGraph(
            nodes=step_ids,
            edges={
                node: [dep for dep in dependency_graph.edges.get(node, []) if dep in step_ids]
                for node in step_ids
            },
            concurrent_groups={}
        )
        
        # 对子图进行自动分组
        return self._auto_group_by_dependencies(sub_graph)
    
    def _auto_group_by_dependencies(
        self, 
        dependency_graph: DependencyGraph
    ) -> List[List[str]]:
        """
        基于依赖关系自动分组
        
        使用层级分组：同一层级的步骤可以并发执行
        
        Args:
            dependency_graph: 依赖图
            
        Returns:
            List[List[str]]: 并发组列表
        """
        # 计算每个节点的入度
        in_degree: Dict[str, int] = {node: 0 for node in dependency_graph.nodes}
        
        for node, dependencies in dependency_graph.edges.items():
            for dep in dependencies:
                in_degree[node] += 1
        
        groups: List[List[str]] = []
        remaining = set(dependency_graph.nodes)
        
        while remaining:
            # 找出当前所有入度为0的节点（可以并发执行）
            current_group = [
                node for node in remaining 
                if in_degree[node] == 0
            ]
            
            if not current_group:
                # 如果没有入度为0的节点但还有剩余节点，说明有循环依赖
                # 这种情况应该在 _detect_cycles 中被捕获
                raise ValueError("内部错误：检测到循环依赖")
            
            groups.append(current_group)
            
            # 移除当前组的节点，更新入度
            for node in current_group:
                remaining.remove(node)
                
                # 更新依赖当前节点的其他节点的入度
                for other_node in remaining:
                    if node in dependency_graph.edges.get(other_node, []):
                        in_degree[other_node] -= 1
        
        return groups
