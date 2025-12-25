# tests/test_dependency_analyzer.py
"""
DependencyAnalyzer 单元测试

测试依赖分析器的核心功能：
- 依赖图构建
- 拓扑排序
- 并发组识别
- 循环依赖检测
"""

import pytest
from src.dependency_analyzer import DependencyAnalyzer, DependencyGraph
from src.models import StepConfig


class TestDependencyAnalyzer:
    """DependencyAnalyzer 单元测试"""
    
    def setup_method(self):
        """测试前准备"""
        self.analyzer = DependencyAnalyzer()
    
    def test_analyze_simple_linear_dependencies(self):
        """测试简单的线性依赖关系"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                input_mapping={"input": "output1"},
                output_key="output2"
            ),
            StepConfig(
                id="step3",
                type="agent_flow",
                agent="agent3",
                flow="flow3",
                input_mapping={"input": "output2"},
                output_key="output3"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        
        assert len(graph.nodes) == 3
        assert "step1" in graph.nodes
        assert "step2" in graph.nodes
        assert "step3" in graph.nodes
        
        # step2 依赖 step1
        assert "step1" in graph.edges["step2"]
        # step3 依赖 step2
        assert "step2" in graph.edges["step3"]
        # step1 没有依赖
        assert len(graph.edges["step1"]) == 0
    
    def test_analyze_independent_steps(self):
        """测试独立步骤（无依赖）"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                output_key="output2"
            ),
            StepConfig(
                id="step3",
                type="agent_flow",
                agent="agent3",
                flow="flow3",
                output_key="output3"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        
        assert len(graph.nodes) == 3
        # 所有步骤都没有依赖
        assert len(graph.edges["step1"]) == 0
        assert len(graph.edges["step2"]) == 0
        assert len(graph.edges["step3"]) == 0
    
    def test_analyze_explicit_depends_on(self):
        """测试显式的 depends_on 依赖"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                output_key="output2"
            ),
            StepConfig(
                id="step3",
                type="agent_flow",
                agent="agent3",
                flow="flow3",
                depends_on=["step1", "step2"],
                output_key="output3"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        
        # step3 依赖 step1 和 step2
        assert "step1" in graph.edges["step3"]
        assert "step2" in graph.edges["step3"]
    
    def test_analyze_concurrent_groups(self):
        """测试并发组配置"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                concurrent_group="group_a",
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                concurrent_group="group_a",
                output_key="output2"
            ),
            StepConfig(
                id="step3",
                type="agent_flow",
                agent="agent3",
                flow="flow3",
                concurrent_group="group_b",
                output_key="output3"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        
        assert "group_a" in graph.concurrent_groups
        assert "group_b" in graph.concurrent_groups
        assert set(graph.concurrent_groups["group_a"]) == {"step1", "step2"}
        assert graph.concurrent_groups["group_b"] == ["step3"]
    
    def test_detect_cycle_simple(self):
        """测试检测简单的循环依赖"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                input_mapping={"input": "output2"},
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                input_mapping={"input": "output1"},
                output_key="output2"
            )
        ]
        
        with pytest.raises(ValueError, match="循环依赖"):
            self.analyzer.analyze_dependencies(steps)
    
    def test_detect_cycle_complex(self):
        """测试检测复杂的循环依赖"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                input_mapping={"input": "output1"},
                output_key="output2"
            ),
            StepConfig(
                id="step3",
                type="agent_flow",
                agent="agent3",
                flow="flow3",
                input_mapping={"input": "output2"},
                output_key="output3"
            ),
            StepConfig(
                id="step4",
                type="agent_flow",
                agent="agent4",
                flow="flow4",
                input_mapping={"input": "output3"},
                depends_on=["step2"],  # 创建循环：step4 -> step2 -> step3 -> step4
                output_key="output4"
            )
        ]
        
        # 这个配置实际上没有循环，让我修正
        steps[1].input_mapping = {"input": "output4"}  # step2 依赖 step4，形成循环
        
        with pytest.raises(ValueError, match="循环依赖"):
            self.analyzer.analyze_dependencies(steps)
    
    def test_topological_sort_linear(self):
        """测试线性依赖的拓扑排序"""
        steps = [
            StepConfig(
                id="step3",
                type="agent_flow",
                agent="agent3",
                flow="flow3",
                input_mapping={"input": "output2"},
                output_key="output3"
            ),
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                input_mapping={"input": "output1"},
                output_key="output2"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        sorted_steps = self.analyzer.topological_sort(graph)
        
        # step1 应该在 step2 之前
        assert sorted_steps.index("step1") < sorted_steps.index("step2")
        # step2 应该在 step3 之前
        assert sorted_steps.index("step2") < sorted_steps.index("step3")
    
    def test_topological_sort_independent(self):
        """测试独立步骤的拓扑排序"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                output_key="output2"
            ),
            StepConfig(
                id="step3",
                type="agent_flow",
                agent="agent3",
                flow="flow3",
                output_key="output3"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        sorted_steps = self.analyzer.topological_sort(graph)
        
        # 所有步骤都应该在结果中
        assert len(sorted_steps) == 3
        assert set(sorted_steps) == {"step1", "step2", "step3"}
    
    def test_topological_sort_diamond(self):
        """测试菱形依赖的拓扑排序"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                input_mapping={"input": "output1"},
                output_key="output2"
            ),
            StepConfig(
                id="step3",
                type="agent_flow",
                agent="agent3",
                flow="flow3",
                input_mapping={"input": "output1"},
                output_key="output3"
            ),
            StepConfig(
                id="step4",
                type="agent_flow",
                agent="agent4",
                flow="flow4",
                depends_on=["step2", "step3"],
                output_key="output4"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        sorted_steps = self.analyzer.topological_sort(graph)
        
        # step1 应该在所有其他步骤之前
        assert sorted_steps.index("step1") < sorted_steps.index("step2")
        assert sorted_steps.index("step1") < sorted_steps.index("step3")
        assert sorted_steps.index("step1") < sorted_steps.index("step4")
        
        # step2 和 step3 应该在 step4 之前
        assert sorted_steps.index("step2") < sorted_steps.index("step4")
        assert sorted_steps.index("step3") < sorted_steps.index("step4")
    
    def test_find_concurrent_groups_independent(self):
        """测试独立步骤的并发组识别"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                output_key="output2"
            ),
            StepConfig(
                id="step3",
                type="agent_flow",
                agent="agent3",
                flow="flow3",
                output_key="output3"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        groups = self.analyzer.find_concurrent_groups(graph)
        
        # 所有独立步骤应该在同一个并发组
        assert len(groups) == 1
        assert set(groups[0]) == {"step1", "step2", "step3"}
    
    def test_find_concurrent_groups_linear(self):
        """测试线性依赖的并发组识别"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                input_mapping={"input": "output1"},
                output_key="output2"
            ),
            StepConfig(
                id="step3",
                type="agent_flow",
                agent="agent3",
                flow="flow3",
                input_mapping={"input": "output2"},
                output_key="output3"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        groups = self.analyzer.find_concurrent_groups(graph)
        
        # 线性依赖应该分成3个组
        assert len(groups) == 3
        assert groups[0] == ["step1"]
        assert groups[1] == ["step2"]
        assert groups[2] == ["step3"]
    
    def test_find_concurrent_groups_diamond(self):
        """测试菱形依赖的并发组识别"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                input_mapping={"input": "output1"},
                output_key="output2"
            ),
            StepConfig(
                id="step3",
                type="agent_flow",
                agent="agent3",
                flow="flow3",
                input_mapping={"input": "output1"},
                output_key="output3"
            ),
            StepConfig(
                id="step4",
                type="agent_flow",
                agent="agent4",
                flow="flow4",
                depends_on=["step2", "step3"],
                output_key="output4"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        groups = self.analyzer.find_concurrent_groups(graph)
        
        # 应该分成3个组
        assert len(groups) == 3
        assert groups[0] == ["step1"]
        # step2 和 step3 可以并发
        assert set(groups[1]) == {"step2", "step3"}
        assert groups[2] == ["step4"]
    
    def test_find_concurrent_groups_with_explicit_groups(self):
        """测试使用显式并发组配置"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                concurrent_group="group_a",
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                concurrent_group="group_a",
                output_key="output2"
            ),
            StepConfig(
                id="step3",
                type="agent_flow",
                agent="agent3",
                flow="flow3",
                depends_on=["step1", "step2"],
                output_key="output3"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        groups = self.analyzer.find_concurrent_groups(graph)
        
        # 应该识别出显式的并发组
        assert len(groups) >= 1
        # 第一个组应该包含 step1 和 step2
        assert set(groups[0]) == {"step1", "step2"}
    
    def test_find_concurrent_groups_invalid_explicit_group(self):
        """测试显式并发组中存在依赖关系的情况"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                concurrent_group="group_a",
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                concurrent_group="group_a",
                input_mapping={"input": "output1"},  # step2 依赖 step1
                output_key="output2"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        groups = self.analyzer.find_concurrent_groups(graph)
        
        # 由于存在依赖，应该被拆分成多个组
        assert len(groups) == 2
        assert groups[0] == ["step1"]
        assert groups[1] == ["step2"]
    
    def test_empty_steps(self):
        """测试空步骤列表"""
        steps = []
        
        graph = self.analyzer.analyze_dependencies(steps)
        
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0
        assert len(graph.concurrent_groups) == 0
    
    def test_single_step(self):
        """测试单个步骤"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                output_key="output1"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        sorted_steps = self.analyzer.topological_sort(graph)
        groups = self.analyzer.find_concurrent_groups(graph)
        
        assert len(graph.nodes) == 1
        assert sorted_steps == ["step1"]
        assert groups == [["step1"]]
    
    def test_self_dependency_ignored(self):
        """测试自依赖被忽略"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                output_key="output1",
                input_mapping={"input": "output1"}  # 自依赖
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        
        # 自依赖应该被忽略
        assert len(graph.edges["step1"]) == 0
    
    def test_multiple_dependencies_same_step(self):
        """测试一个步骤依赖多个其他步骤"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                output_key="output2"
            ),
            StepConfig(
                id="step3",
                type="agent_flow",
                agent="agent3",
                flow="flow3",
                output_key="output3"
            ),
            StepConfig(
                id="step4",
                type="agent_flow",
                agent="agent4",
                flow="flow4",
                input_mapping={
                    "input1": "output1",
                    "input2": "output2",
                    "input3": "output3"
                },
                output_key="output4"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        
        # step4 应该依赖 step1, step2, step3
        assert set(graph.edges["step4"]) == {"step1", "step2", "step3"}
    
    def test_mixed_input_mapping_and_depends_on(self):
        """测试混合使用 input_mapping 和 depends_on"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                output_key="output2"
            ),
            StepConfig(
                id="step3",
                type="agent_flow",
                agent="agent3",
                flow="flow3",
                input_mapping={"input": "output1"},
                depends_on=["step2"],
                output_key="output3"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        
        # step3 应该同时依赖 step1 和 step2
        assert set(graph.edges["step3"]) == {"step1", "step2"}
    
    def test_duplicate_dependencies_removed(self):
        """测试重复依赖被去重"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                input_mapping={"input": "output1"},
                depends_on=["step1"],  # 重复依赖
                output_key="output2"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        
        # step2 对 step1 的依赖应该只出现一次
        assert graph.edges["step2"].count("step1") == 1
    
    def test_nonexistent_dependency_ignored(self):
        """测试不存在的依赖被忽略"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                input_mapping={"input": "nonexistent_output"},
                output_key="output1"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        
        # 不存在的依赖应该被忽略
        assert len(graph.edges["step1"]) == 0
    
    def test_complex_concurrent_groups_with_dependencies(self):
        """测试复杂的并发组配置（包含依赖关系）"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                concurrent_group="group_a",
                input_mapping={"input": "output1"},
                output_key="output2"
            ),
            StepConfig(
                id="step3",
                type="agent_flow",
                agent="agent3",
                flow="flow3",
                concurrent_group="group_a",
                input_mapping={"input": "output1"},
                output_key="output3"
            ),
            StepConfig(
                id="step4",
                type="agent_flow",
                agent="agent4",
                flow="flow4",
                depends_on=["step2", "step3"],
                output_key="output4"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        groups = self.analyzer.find_concurrent_groups(graph)
        
        # 应该有3个组
        assert len(groups) == 3
        # 第一组是 step1
        assert groups[0] == ["step1"]
        # 第二组是 step2 和 step3（它们在同一个并发组且都依赖 step1）
        assert set(groups[1]) == {"step2", "step3"}
        # 第三组是 step4
        assert groups[2] == ["step4"]
    
    def test_topological_sort_with_cycle_raises_error(self):
        """测试拓扑排序遇到循环依赖时抛出错误"""
        # 创建一个有循环的图
        graph = DependencyGraph(
            nodes=["step1", "step2"],
            edges={
                "step1": ["step2"],
                "step2": ["step1"]
            },
            concurrent_groups={}
        )
        
        with pytest.raises(ValueError, match="循环依赖"):
            self.analyzer.topological_sort(graph)
    
    def test_three_way_cycle_detection(self):
        """测试三步循环依赖检测"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                input_mapping={"input": "output3"},
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                input_mapping={"input": "output1"},
                output_key="output2"
            ),
            StepConfig(
                id="step3",
                type="agent_flow",
                agent="agent3",
                flow="flow3",
                input_mapping={"input": "output2"},
                output_key="output3"
            )
        ]
        
        with pytest.raises(ValueError, match="循环依赖"):
            self.analyzer.analyze_dependencies(steps)
    
    def test_concurrent_groups_with_partial_overlap(self):
        """测试并发组部分重叠的情况"""
        steps = [
            StepConfig(
                id="step1",
                type="agent_flow",
                agent="agent1",
                flow="flow1",
                concurrent_group="group_a",
                output_key="output1"
            ),
            StepConfig(
                id="step2",
                type="agent_flow",
                agent="agent2",
                flow="flow2",
                concurrent_group="group_a",
                output_key="output2"
            ),
            StepConfig(
                id="step3",
                type="agent_flow",
                agent="agent3",
                flow="flow3",
                concurrent_group="group_b",
                output_key="output3"
            ),
            StepConfig(
                id="step4",
                type="agent_flow",
                agent="agent4",
                flow="flow4",
                concurrent_group="group_b",
                depends_on=["step1"],
                output_key="output4"
            )
        ]
        
        graph = self.analyzer.analyze_dependencies(steps)
        groups = self.analyzer.find_concurrent_groups(graph)
        
        # 验证并发组被正确识别
        assert "group_a" in graph.concurrent_groups
        assert "group_b" in graph.concurrent_groups
        assert set(graph.concurrent_groups["group_a"]) == {"step1", "step2"}
        assert set(graph.concurrent_groups["group_b"]) == {"step3", "step4"}
    
    def test_large_dependency_chain(self):
        """测试大型依赖链"""
        # 创建一个10步的线性依赖链
        steps = []
        for i in range(1, 11):
            step = StepConfig(
                id=f"step{i}",
                type="agent_flow",
                agent=f"agent{i}",
                flow=f"flow{i}",
                output_key=f"output{i}"
            )
            if i > 1:
                step.input_mapping = {"input": f"output{i-1}"}
            steps.append(step)
        
        graph = self.analyzer.analyze_dependencies(steps)
        sorted_steps = self.analyzer.topological_sort(graph)
        groups = self.analyzer.find_concurrent_groups(graph)
        
        # 验证拓扑排序正确
        assert sorted_steps == [f"step{i}" for i in range(1, 11)]
        
        # 验证每个步骤都在单独的并发组中
        assert len(groups) == 10
        for i, group in enumerate(groups, 1):
            assert group == [f"step{i}"]
    
    def test_wide_dependency_tree(self):
        """测试宽依赖树（一个步骤依赖多个独立步骤）"""
        # 创建5个独立步骤，然后一个步骤依赖所有这些步骤
        steps = []
        for i in range(1, 6):
            steps.append(StepConfig(
                id=f"step{i}",
                type="agent_flow",
                agent=f"agent{i}",
                flow=f"flow{i}",
                output_key=f"output{i}"
            ))
        
        # 添加依赖所有前面步骤的步骤
        steps.append(StepConfig(
            id="step_final",
            type="agent_flow",
            agent="agent_final",
            flow="flow_final",
            depends_on=[f"step{i}" for i in range(1, 6)],
            output_key="output_final"
        ))
        
        graph = self.analyzer.analyze_dependencies(steps)
        groups = self.analyzer.find_concurrent_groups(graph)
        
        # 应该有2个并发组
        assert len(groups) == 2
        # 第一组包含所有独立步骤
        assert set(groups[0]) == {f"step{i}" for i in range(1, 6)}
        # 第二组只包含最终步骤
        assert groups[1] == ["step_final"]
