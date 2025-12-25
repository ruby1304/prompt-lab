#!/usr/bin/env python
"""
验证 Agent 迁移状态

此脚本验证：
1. 生产 Agent 在 agents/ 目录
2. 示例 Agent 在 examples/agents/ 目录
3. 测试 Agent 在 tests/agents/ 目录
4. 所有 Agent 都可以正确加载
5. Agent Registry 正确解析所有目录
"""

import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.agent_registry import list_available_agents, load_agent, _find_agent_dir

# 定义预期的 Agent 分布
EXPECTED_PRODUCTION_AGENTS = {
    '_template',  # 模板
    'judge_default',  # 系统 Agent
    'mem_l1_summarizer',  # 生产 Agent
    'mem0_l1_summarizer',  # 生产 Agent
    'usr_profile',  # 生产 Agent
}

EXPECTED_EXAMPLE_AGENTS = {
    'document_summarizer',
    'entity_extractor',
    'intent_classifier',
    'response_generator',
    'text_cleaner',
}

EXPECTED_TEST_AGENTS = {
    'big_thing',
}


def verify_directory_structure():
    """验证目录结构"""
    print("=" * 60)
    print("验证目录结构")
    print("=" * 60)
    
    agents_dir = ROOT_DIR / "agents"
    examples_agents_dir = ROOT_DIR / "examples" / "agents"
    tests_agents_dir = ROOT_DIR / "tests" / "agents"
    
    # 检查生产 Agent 目录
    print("\n1. 生产 Agent 目录 (agents/):")
    if agents_dir.exists():
        actual_agents = {d.name for d in agents_dir.iterdir() if d.is_dir()}
        print(f"   预期: {sorted(EXPECTED_PRODUCTION_AGENTS)}")
        print(f"   实际: {sorted(actual_agents)}")
        
        if actual_agents == EXPECTED_PRODUCTION_AGENTS:
            print("   ✓ 生产 Agent 目录正确")
        else:
            extra = actual_agents - EXPECTED_PRODUCTION_AGENTS
            missing = EXPECTED_PRODUCTION_AGENTS - actual_agents
            if extra:
                print(f"   ✗ 多余的 Agent: {extra}")
            if missing:
                print(f"   ✗ 缺失的 Agent: {missing}")
            return False
    else:
        print("   ✗ agents/ 目录不存在")
        return False
    
    # 检查示例 Agent 目录
    print("\n2. 示例 Agent 目录 (examples/agents/):")
    if examples_agents_dir.exists():
        actual_examples = {d.name for d in examples_agents_dir.iterdir() if d.is_dir()}
        print(f"   预期: {sorted(EXPECTED_EXAMPLE_AGENTS)}")
        print(f"   实际: {sorted(actual_examples)}")
        
        if actual_examples == EXPECTED_EXAMPLE_AGENTS:
            print("   ✓ 示例 Agent 目录正确")
        else:
            extra = actual_examples - EXPECTED_EXAMPLE_AGENTS
            missing = EXPECTED_EXAMPLE_AGENTS - actual_examples
            if extra:
                print(f"   ✗ 多余的 Agent: {extra}")
            if missing:
                print(f"   ✗ 缺失的 Agent: {missing}")
            return False
    else:
        print("   ✗ examples/agents/ 目录不存在")
        return False
    
    # 检查测试 Agent 目录
    print("\n3. 测试 Agent 目录 (tests/agents/):")
    if tests_agents_dir.exists():
        actual_tests = {d.name for d in tests_agents_dir.iterdir() if d.is_dir()}
        print(f"   预期: {sorted(EXPECTED_TEST_AGENTS)}")
        print(f"   实际: {sorted(actual_tests)}")
        
        if actual_tests == EXPECTED_TEST_AGENTS:
            print("   ✓ 测试 Agent 目录正确")
        else:
            extra = actual_tests - EXPECTED_TEST_AGENTS
            missing = EXPECTED_TEST_AGENTS - actual_tests
            if extra:
                print(f"   ✗ 多余的 Agent: {extra}")
            if missing:
                print(f"   ✗ 缺失的 Agent: {missing}")
            return False
    else:
        print("   ✗ tests/agents/ 目录不存在")
        return False
    
    return True


def verify_agent_registry():
    """验证 Agent Registry"""
    print("\n" + "=" * 60)
    print("验证 Agent Registry")
    print("=" * 60)
    
    # 列出所有可用的 Agent
    all_agents = set(list_available_agents())
    expected_all = EXPECTED_PRODUCTION_AGENTS | EXPECTED_EXAMPLE_AGENTS | EXPECTED_TEST_AGENTS
    # 排除模板
    expected_all = expected_all - {'_template'}
    
    print(f"\n所有可用 Agent: {sorted(all_agents)}")
    print(f"预期 Agent: {sorted(expected_all)}")
    
    if all_agents == expected_all:
        print("✓ Agent Registry 正确列出所有 Agent")
    else:
        extra = all_agents - expected_all
        missing = expected_all - all_agents
        if extra:
            print(f"✗ 多余的 Agent: {extra}")
        if missing:
            print(f"✗ 缺失的 Agent: {missing}")
        return False
    
    return True


def verify_agent_loading():
    """验证 Agent 加载"""
    print("\n" + "=" * 60)
    print("验证 Agent 加载")
    print("=" * 60)
    
    all_agents = list_available_agents()
    failed = []
    
    for agent_id in all_agents:
        try:
            agent = load_agent(agent_id)
            agent_dir = _find_agent_dir(agent_id)
            
            # 确定 Agent 类型
            if agent_dir and 'examples/agents' in str(agent_dir):
                agent_type = "示例"
            elif agent_dir and 'tests/agents' in str(agent_dir):
                agent_type = "测试"
            else:
                agent_type = "生产"
            
            print(f"✓ {agent_id:25s} [{agent_type}] - {agent.name} ({len(agent.flows)} flows)")
        except Exception as e:
            print(f"✗ {agent_id:25s} - 加载失败: {str(e)[:50]}")
            failed.append(agent_id)
    
    if failed:
        print(f"\n✗ {len(failed)} 个 Agent 加载失败")
        return False
    else:
        print(f"\n✓ 所有 {len(all_agents)} 个 Agent 加载成功")
        return True


def verify_agent_paths():
    """验证 Agent 路径解析"""
    print("\n" + "=" * 60)
    print("验证 Agent 路径解析")
    print("=" * 60)
    
    test_cases = [
        ('judge_default', 'agents/judge_default'),
        ('mem_l1_summarizer', 'agents/mem_l1_summarizer'),
        ('document_summarizer', 'examples/agents/document_summarizer'),
        ('big_thing', 'tests/agents/big_thing'),
    ]
    
    all_passed = True
    for agent_id, expected_path_suffix in test_cases:
        agent_dir = _find_agent_dir(agent_id)
        if agent_dir and expected_path_suffix in str(agent_dir):
            print(f"✓ {agent_id:25s} -> {agent_dir}")
        else:
            print(f"✗ {agent_id:25s} -> {agent_dir} (预期包含: {expected_path_suffix})")
            all_passed = False
    
    return all_passed


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("Agent 迁移验证脚本")
    print("=" * 60)
    
    results = []
    
    # 运行所有验证
    results.append(("目录结构", verify_directory_structure()))
    results.append(("Agent Registry", verify_agent_registry()))
    results.append(("Agent 加载", verify_agent_loading()))
    results.append(("路径解析", verify_agent_paths()))
    
    # 总结
    print("\n" + "=" * 60)
    print("验证总结")
    print("=" * 60)
    
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{name:20s}: {status}")
    
    all_passed = all(passed for _, passed in results)
    
    if all_passed:
        print("\n" + "=" * 60)
        print("✓ 所有验证通过！Agent 迁移完成。")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("✗ 部分验证失败，请检查上述错误。")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
