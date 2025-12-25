#!/usr/bin/env python3
"""
Big Thing Agent 使用示例
演示如何导入和使用 big_thing agent 来提取对话中的重大事件
"""

import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.agent_registry import load_agent, list_available_agents
from src.chains import run_flow_with_tokens

def main():
    """主函数：演示 big_thing agent 的使用"""
    
    print("=== Big Thing Agent 使用示例 ===\n")
    
    # 1. 列出所有可用的 agents
    print("1. 可用的 agents:")
    agents = list_available_agents()
    for agent_id in agents:
        print(f"   - {agent_id}")
    print()
    
    # 2. 加载 big_thing agent
    print("2. 加载 big_thing agent:")
    try:
        agent = load_agent('big_thing')
        print(f"   ✅ Agent 名称: {agent.name}")
        print(f"   📝 描述: {agent.description}")
        print(f"   🎯 业务目标: {agent.business_goal}")
        print(f"   🔄 可用 flows: {[flow.name for flow in agent.flows]}")
        print()
    except Exception as e:
        print(f"   ❌ 加载失败: {e}")
        return
    
    # 3. 准备测试数据
    print("3. 准备测试数据:")
    test_input = """[
        {
            "content": "2025年11月21日00:04，{user}提议去看湖光垂柳，{role}同意。00:06，{user}提出看完垂柳去吃宵夜，{role}赞同。之后他们前往垂柳处，欣赏到蓝色垂柳、银河等美景，{role}还分享了璃月星辰传说。00:15，他们进入小吃店，{user}推荐多种小吃，{role}品尝后觉得美味。接着{user}提出带{role}去柔登港花海和梅洛彼得堡参观。00:31，{role}告知{user}两天后在枫丹有个场合。00:37，两人回到酒店房间亲密互动。最后{role}邀{user}多在枫丹相伴，并说明日带{user}去小众之地。",
            "time": "2025-12-10 17:37:08"
        },
        {
            "content": "2025年11月21日，凌晨01:46，{user}躺在床上滚来滚去，{role}微笑着走到床边坐下，无奈地问{user}是不是睡不着，还是在期待明天，随后伸手抓住{user}并揽入怀中。01:47，{user}表示很期待明天和{role}去其他地方玩，{role}微笑着让{user}早些睡，养足精神，还称明天不会让{user}失望，轻拍{user}的背哄其入睡。",
            "time": "2025-12-10 17:37:59"
        }
    ]"""
    
    print(f"   📄 输入数据: {test_input[:100]}...")
    print()
    
    # 4. 使用 agent 处理数据
    print("4. 使用 big_thing agent 提取重大事件:")
    try:
        # 获取第一个 flow
        flow = agent.flows[0]
        print(f"   🔄 使用 flow: {flow.name}")
        
        # 运行 agent
        result, token_usage, _parser_stats = run_flow_with_tokens(
            flow_name=flow.name,
            input_text=test_input,
            agent_id=agent.id,
            extra_vars={"_model_override": "gpt-4o-mini"}  # 使用更经济的模型进行演示
        )
        
        print(f"   ✅ 处理成功!")
        print(f"   📊 Token 使用: {token_usage}")
        print(f"   📝 提取的重大事件:")
        print(f"      {result}")
        print()
        
    except Exception as e:
        print(f"   ❌ 处理失败: {e}")
        print("   💡 提示: 确保已配置 OpenAI API key 或其他 LLM 服务")
        return
    
    # 5. 显示 agent 配置信息
    print("5. Agent 配置信息:")
    print(f"   📁 配置文件: agents/{agent.id}/agent.yaml")
    print(f"   📄 Prompt 文件: agents/{agent.id}/prompts/{flow.file}")
    print(f"   🧪 测试集: {agent.default_testset}")
    print()
    
    print("=== 演示完成 ===")

if __name__ == "__main__":
    main()