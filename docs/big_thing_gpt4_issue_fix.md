# Big Thing Agent GPT-4 调用问题修复报告

## 问题描述

在导入 `big_thing` agent 的过程中，发现系统会意外调用 `gpt-4` 模型，而不是使用项目配置的默认模型。

## 问题根源分析

通过代码审查，发现了以下几个硬编码 `gpt-4` 模型的位置：

### 1. `src/agent_template_parser/error_handler.py` (第394行)

**问题代码：**
```python
'flows': {
    'default': {
        'prompt': f'{agent_name}_v1',
        'model': 'gpt-4'  # 硬编码了 gpt-4
    }
},
```

**修复方案：**
```python
'flows': {
    'default': {
        'prompt': f'{agent_name}_v1'
        # 不指定model，使用系统默认配置
    }
},
```

### 2. `src/agent_template_parser/llm_enhancer.py` (第20行)

**问题代码：**
```python
def __init__(self, model_name: str = "gpt-4", temperature: float = 0.1, max_retries: int = 3, fallback_enabled: bool = True):
```

**修复方案：**
```python
def __init__(self, model_name: str = None, temperature: float = 0.1, max_retries: int = 3, fallback_enabled: bool = True):
```

并在 LLM 实例创建时添加默认配置支持：
```python
# 如果没有指定模型，使用项目默认配置
from ..config import get_openai_model_name
model_name = self.model_name or get_openai_model_name()
```

## 修复效果

### 修复前
- Agent 模板解析器在错误恢复时会硬编码使用 `gpt-4`
- LLM 增强器默认使用 `gpt-4` 模型
- 生成的 agent 配置可能包含 `gpt-4` 模型配置

### 修复后
- 所有组件都使用项目的默认模型配置 (`src/config.py` 中的 `get_openai_model_name()`)
- 默认模型为 `gpt-4.1-mini`（更经济的选择）
- 可以通过环境变量 `OPENAI_MODEL_NAME` 自定义默认模型

## 项目默认模型配置

项目的默认模型配置位于 `src/config.py`：

```python
def get_openai_model_name() -> str:
    return os.getenv("OPENAI_MODEL_NAME", "gpt-4.1-mini")
```

### 自定义默认模型

可以通过以下方式自定义默认模型：

1. **环境变量方式：**
   ```bash
   export OPENAI_MODEL_NAME="gpt-4o-mini"
   ```

2. **`.env` 文件方式：**
   ```
   OPENAI_MODEL_NAME=gpt-4o-mini
   ```

## 验证修复

### 1. 重新创建 big_thing agent
```bash
rm -rf agents/big_thing
python -m src.agent_template_parser.cli create-agent big_thing
```

### 2. 检查生成的配置
生成的 `agents/big_thing/agent.yaml` 不再包含硬编码的 `gpt-4` 配置。

### 3. 验证 agent 加载
```python
from src.agent_registry import load_agent
agent = load_agent('big_thing')
print(f"Agent loaded: {agent.name}")
```

## 影响范围

这个修复影响以下组件：

1. **Agent 模板解析器** - 错误恢复机制不再硬编码 gpt-4
2. **LLM 增强器** - 使用项目默认模型配置
3. **所有新创建的 agents** - 将使用项目默认模型而不是 gpt-4

## 建议

1. **成本控制：** 建议在 `.env` 文件中设置 `OPENAI_MODEL_NAME=gpt-4o-mini` 以降低 API 调用成本
2. **性能需求：** 如果需要更高性能，可以设置为 `gpt-4` 或 `gpt-4-turbo`
3. **测试环境：** 在测试环境中使用更便宜的模型，生产环境使用高性能模型

## 相关文件

- `src/agent_template_parser/error_handler.py` - 错误恢复机制
- `src/agent_template_parser/llm_enhancer.py` - LLM 增强器
- `src/config.py` - 项目配置
- `agents/big_thing/` - 修复后的 big_thing agent

## 总结

通过这次修复，消除了项目中硬编码 `gpt-4` 模型的问题，使所有组件都统一使用项目的默认模型配置。这不仅提高了配置的一致性，也为成本控制和模型选择提供了更好的灵活性。