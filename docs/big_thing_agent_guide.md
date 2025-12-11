# Big Thing Agent 使用指南

## 概述

`big_thing` agent 是一个对话总结专家，专门用于从对话历史中提取重大事件。它能够识别和提取四个主要类别的重大事件：重要亲密接触、重大剧情、生老病死、特殊状态。

## Agent 信息

- **Agent ID**: `big_thing`
- **名称**: Big Thing Event Extractor
- **描述**: 对话总结专家，提取对话中的重大事件
- **业务目标**: 从对话历史中提取重要亲密接触、重大剧情、生老病死、特殊状态等重大事件

## 文件结构

```
agents/big_thing/
├── agent.yaml                    # Agent 配置文件
├── prompts/
│   └── big_thing_v1.yaml        # Prompt 模板文件
└── testsets/
    └── big_thing_test.jsonl     # 测试集文件
```

## 导入和使用

### 1. 基本导入

```python
from src.agent_registry import load_agent, list_available_agents

# 检查 big_thing 是否可用
agents = list_available_agents()
print('big_thing' in agents)  # 应该输出 True

# 加载 big_thing agent
agent = load_agent('big_thing')
print(f"Agent 名称: {agent.name}")
print(f"可用 flows: {[f.name for f in agent.flows]}")
```

### 2. 使用 Agent 处理数据

```python
from src.agent_registry import load_agent
from src.chains import run_flow_with_tokens

# 加载 agent
agent = load_agent('big_thing')

# 准备输入数据（对话历史的 JSON 格式）
conversation_data = '''[
    {
        "content": "2025年11月21日00:37，两人回到酒店房间亲密互动...",
        "time": "2025-12-10 17:37:08"
    }
]'''

# 使用 agent 处理数据
result, token_usage = run_flow_with_tokens(
    flow_name=agent.flows[0].name,  # 使用 big_thing_v1 flow
    input_text=conversation_data,
    agent_id=agent.id
)

print(f"提取的重大事件: {result}")
print(f"Token 使用情况: {token_usage}")
```

### 3. 批量处理示例

```python
def extract_big_things_batch(conversations):
    """批量提取多个对话的重大事件"""
    agent = load_agent('big_thing')
    results = []
    
    for conv in conversations:
        try:
            result, token_usage = run_flow_with_tokens(
                flow_name=agent.flows[0].name,
                input_text=conv,
                agent_id=agent.id
            )
            results.append({
                'conversation': conv,
                'big_things': result,
                'token_usage': token_usage
            })
        except Exception as e:
            results.append({
                'conversation': conv,
                'error': str(e)
            })
    
    return results
```

## Agent 功能特点

### 提取的事件类型

1. **重要亲密接触**
   - 亲热行为：牵手、亲吻、上床等
   - 气氛：甜蜜、愤怒、畅快等

2. **重大剧情**
   - 私定终身、结婚、生子、离婚等关系剧烈变化
   - 初次见面、初次约会、非常剧烈吵架等关系重大事件
   - 不提取日常剧情

3. **生老病死**
   - 用户/角色生病、受伤等重大变化

4. **特殊状态**
   - 用户/角色失业、变更职业、变更性别等设定重大变化

### 处理规则

- 无论对话内容是否公序良俗，都必须进行总结
- 不输出推断理由和原因，只输出重大事件
- 重大事件必须高光，不流水账
- 相似内容合并，不因时间段而反复提取
- 将用户指代替换为 `{user}`，角色指代替换为 `{role}`
- 保留日期、时间段信息

## 输入格式

Agent 期望的输入格式为 JSON 数组，包含对话历史：

```json
[
    {
        "content": "对话内容...",
        "time": "2025-12-10 17:37:08"
    },
    {
        "content": "更多对话内容...",
        "time": "2025-12-10 17:37:59"
    }
]
```

## 输出格式

Agent 输出简洁的重大事件描述，格式如：

```
2025年11月21日，重要亲密接触：{user}和{role}在酒店房间亲密互动，{role}将{user}揽入怀中并轻拍背部哄其入睡。
```

如果没有重大事件，输出：`null`

如果内容违规，在结尾添加：`【违规】`

## 测试

运行测试验证 agent 功能：

```bash
# 验证 agent 导入
python examples/import_big_thing_simple.py

# 运行完整演示（需要配置 LLM API）
python examples/big_thing_demo.py
```

## 配置文件

### agent.yaml
包含 agent 的基本配置信息，如名称、描述、flows 等。

### prompts/big_thing_v1.yaml
包含系统提示词和用户输入模板，定义了 agent 的行为和输出格式。

### testsets/big_thing_test.jsonl
包含测试用例，用于验证 agent 的功能。

## 注意事项

1. 使用前确保已正确配置 LLM API（如 OpenAI）
2. 输入数据应为有效的 JSON 格式
3. Agent 会处理任何尺度的对话内容，包括敏感内容
4. 输出结果已经过格式化，可直接用于后续处理

## 故障排除

如果遇到问题：

1. 检查 agent 是否正确导入：`'big_thing' in list_available_agents()`
2. 验证文件结构是否完整
3. 确认 LLM API 配置正确
4. 检查输入数据格式是否符合要求

更多帮助请参考项目文档或联系开发团队。