#!/usr/bin/env python3
"""
简单的 Big Thing Agent 导入示例
演示如何在项目中导入和使用 big_thing agent
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def main():
    """演示如何导入 big_thing agent"""
    
    print("=== Big Thing Agent 导入示例 ===\n")
    
    # 方法1: 导入 agent_registry 模块
    print("方法1: 使用 agent_registry 模块")
    try:
        from src.agent_registry import load_agent, list_available_agents
        
        # 列出所有可用的 agents
        agents = list_available_agents()
        print(f"   可用的 agents: {agents}")
        
        # 检查 big_thing 是否在列表中
        if 'big_thing' in agents:
            print("   ✅ big_thing agent 已成功导入到项目中")
        else:
            print("   ❌ big_thing agent 未找到")
            return
        
        # 加载 big_thing agent 配置
        agent = load_agent('big_thing')
        print(f"   📝 Agent ID: {agent.id}")
        print(f"   📝 Agent 名称: {agent.name}")
        print(f"   📝 描述: {agent.description}")
        print(f"   📝 业务目标: {agent.business_goal}")
        print(f"   📝 默认测试集: {agent.default_testset}")
        print(f"   📝 可用 flows: {[f.name for f in agent.flows]}")
        
        # 显示 flow 详细信息
        for flow in agent.flows:
            print(f"      - Flow: {flow.name}")
            print(f"        文件: {flow.file}")
            print(f"        备注: {flow.notes}")
        
    except ImportError as e:
        print(f"   ❌ 导入失败: {e}")
        return
    except Exception as e:
        print(f"   ❌ 加载失败: {e}")
        return
    
    print()
    
    # 方法2: 验证文件结构
    print("方法2: 验证 agent 文件结构")
    agent_dir = project_root / "agents" / "big_thing"
    
    if agent_dir.exists():
        print(f"   ✅ Agent 目录存在: {agent_dir}")
        
        # 检查必要文件
        required_files = [
            "agent.yaml",
            "prompts/big_thing_v1.yaml",
            "testsets/big_thing_test.jsonl"
        ]
        
        for file_path in required_files:
            full_path = agent_dir / file_path
            if full_path.exists():
                print(f"   ✅ {file_path} 存在")
            else:
                print(f"   ❌ {file_path} 缺失")
    else:
        print(f"   ❌ Agent 目录不存在: {agent_dir}")
    
    print()
    
    # 方法3: 显示使用示例
    print("方法3: 在其他脚本中使用 big_thing agent 的示例代码")
    print("""
    # 在你的 Python 脚本中添加以下代码:
    
    from src.agent_registry import load_agent
    from src.chains import run_flow_with_tokens
    
    # 加载 big_thing agent
    agent = load_agent('big_thing')
    
    # 准备输入数据
    conversation_data = "你的对话历史数据..."
    
    # 使用 agent 处理数据
    result, token_usage = run_flow_with_tokens(
        flow_name=agent.flows[0].name,  # 使用第一个 flow
        input_text=conversation_data,
        agent_id=agent.id
    )
    
    print(f"提取的重大事件: {result}")
    print(f"Token 使用情况: {token_usage}")
    """)
    
    print("\n=== 导入验证完成 ===")

if __name__ == "__main__":
    main()