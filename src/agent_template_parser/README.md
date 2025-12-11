# Agent Template Parser

Agent Template Parser 是一个强大的工具，用于从文本模板文件自动生成符合项目规范的 agent 配置，并支持批量处理 JSON 数据生成测试集。

## 功能特性

### 🎯 核心功能

1. **模板到 Agent 配置转换**
   - 从系统提示词模板、用户输入模板和测试用例自动生成 agent.yaml 和 prompt.yaml
   - 智能变量提取和映射
   - 支持 LLM 增强的配置优化

2. **批量测试集生成**
   - 批量处理 JSON 输入文件
   - 自动转换为项目标准的 JSONL 测试集格式
   - 支持复杂嵌套数据结构

3. **错误处理和恢复**
   - 智能错误检测和修复建议
   - 多级回退机制
   - 详细的错误报告

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 基本使用

#### 1. 从模板创建 Agent

```bash
python -m src.agent_template_parser.cli create-agent \
  --system-prompt templates/system_prompts/my_agent_system.txt \
  --user-input templates/user_inputs/my_agent_user.txt \
  --test-case templates/test_cases/my_agent_test.json \
  --agent-name my_agent
```

#### 2. 批量创建测试集

```bash
python -m src.agent_template_parser.cli create-testset \
  --json-files data1.json data2.json data3.json \
  --target-agent existing_agent \
  --output-filename batch_testset.jsonl
```

#### 3. 查看可用模板

```bash
python -m src.agent_template_parser.cli list-templates
```

#### 4. 验证模板文件

```bash
python -m src.agent_template_parser.cli validate-templates --agent-name my_agent
```

## 详细使用指南

### 模板文件格式

#### 系统提示词模板 (system_prompt.txt)

```text
你是一个专业的对话总结专家。你的任务是分析用户提供的对话内容，并生成简洁、准确的总结。

请根据以下对话内容：${sys.user_input}

为用户{user}生成总结，考虑其角色{role}的特点。

总结要求：
1. 保持客观中性
2. 突出关键信息
3. 控制在200字以内
```

**支持的变量格式：**
- `${sys.user_input}` - 系统变量，映射到对话历史
- `{user}` - 用户占位符，运行时替换
- `{role}` - 角色占位符，运行时替换
- `${input}`, `${query}`, `${context}` - 其他系统变量

#### 用户输入模板 (user_input.txt)

```text
请总结以下对话内容：
{input_text}

用户角色：{user_role}
总结重点：{focus_area}
```

#### 测试用例文件 (test_case.json)

```json
{
  "sys": {
    "user_input": [
      {"role": "user", "content": "你好，我想了解一下产品功能"},
      {"role": "assistant", "content": "您好！我很乐意为您介绍我们的产品功能..."},
      {"role": "user", "content": "价格如何？"},
      {"role": "assistant", "content": "我们有多种价格方案..."}
    ]
  },
  "input_text": "用户咨询产品功能和价格",
  "user_role": "潜在客户",
  "focus_area": "产品介绍"
}
```

### 批量 JSON 处理

#### 输入 JSON 格式

```json
{
  "sys": {
    "user_input": [
      {"role": "user", "content": "请帮我分析这个数据"},
      {"role": "assistant", "content": "我来为您分析数据"}
    ]
  },
  "data_type": "销售报表",
  "time_period": "Q3 2024",
  "metrics": ["收入", "客户数", "转化率"]
}
```

#### 生成的测试集格式

```jsonl
{"id": 1, "chat_round_30": [{"role": "user", "content": "请帮我分析这个数据"}, {"role": "assistant", "content": "我来为您分析数据"}], "data_type": "销售报表", "time_period": "Q3 2024", "metrics": ["收入", "客户数", "转化率"], "tags": []}
```

## API 使用

### Python API

```python
from src.agent_template_parser import (
    TemplateManager,
    TemplateParser,
    AgentConfigGenerator,
    BatchDataProcessor
)

# 1. 模板管理
template_manager = TemplateManager("templates")
template_manager.create_directory_structure()

# 2. 解析模板
parser = TemplateParser()
system_data = parser.parse_system_prompt(system_prompt_content)
user_data = parser.parse_user_input(user_input_content)
test_data = parser.parse_test_case(test_case_content)

# 3. 生成配置
config_generator = AgentConfigGenerator()
parsed_template = parser.create_parsed_template(system_data, user_data, test_data)
agent_config = config_generator.generate_agent_yaml(parsed_template, "my_agent")
prompt_config = config_generator.generate_prompt_yaml(parsed_template, "my_agent")

# 4. 保存配置
config_generator.save_config_files(agent_config, prompt_config, "my_agent")

# 5. 批量处理
processor = BatchDataProcessor()
json_inputs = ['{"sys": {"user_input": [...]}, "field": "value"}']
processed_data = processor.process_json_inputs(json_inputs, "target_agent")
testset_data = processor.convert_to_testset_format(processed_data)
processor.save_testset(testset_data, "target_agent", "output.jsonl")
```

## 配置选项

### 环境变量

- `OPENAI_API_KEY` - OpenAI API 密钥（用于 LLM 增强功能）

### 配置文件

可以通过修改各组件的初始化参数来自定义行为：

```python
# 自定义模板目录
template_manager = TemplateManager("custom_templates")

# 自定义 agents 目录
config_generator = AgentConfigGenerator("custom_agents")

# 自定义批量处理器
processor = BatchDataProcessor("custom_agents")

# 自定义 LLM 增强器
llm_enhancer = LLMEnhancer(
    model_name="gpt-4",
    max_retries=3,
    fallback_enabled=True
)
```

## 故障排除

### 常见问题

#### 1. 模板解析失败

**问题：** `TemplateParsingError: System prompt parsing failed`

**解决方案：**
- 检查模板文件编码是否为 UTF-8
- 确保变量格式正确（`${variable}` 或 `{variable}`）
- 验证 JSON 测试用例格式是否有效

#### 2. 配置生成错误

**问题：** `ConfigGenerationError: Agent configuration generation failed`

**解决方案：**
- 确保所有必需的模板文件都存在
- 检查 agent 名称是否符合命名规范
- 验证模板中的变量是否被正确识别

#### 3. LLM 增强失败

**问题：** `LLMEnhancementError: OPENAI_API_KEY environment variable is required`

**解决方案：**
- 设置 `OPENAI_API_KEY` 环境变量
- 或使用 `--no-llm-enhancement` 参数禁用 LLM 增强

#### 4. 批量处理错误

**问题：** `BatchProcessingError: Target agent does not exist`

**解决方案：**
- 确保目标 agent 存在于 agents 目录中
- 检查 agent.yaml 文件是否存在且格式正确
- 验证 JSON 输入文件格式是否有效

### 调试技巧

#### 1. 启用详细日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### 2. 验证模板文件

```bash
python -m src.agent_template_parser.cli validate-templates --agent-name your_agent
```

#### 3. 检查生成的配置

生成的配置文件位于：
- `agents/{agent_name}/agent.yaml`
- `agents/{agent_name}/prompts/{agent_name}_v1.yaml`

#### 4. 测试单个 JSON 文件

```bash
python -m src.agent_template_parser.cli create-testset \
  --json-files single_file.json \
  --target-agent test_agent \
  --output-filename debug.jsonl
```

## 最佳实践

### 1. 模板设计

- **保持简洁：** 模板应该清晰、简洁，避免过于复杂的逻辑
- **变量命名：** 使用有意义的变量名，如 `{user_role}` 而不是 `{ur}`
- **测试用例：** 提供真实、完整的测试用例数据

### 2. 批量处理

- **数据验证：** 处理前验证 JSON 数据格式
- **分批处理：** 对于大量数据，考虑分批处理以避免内存问题
- **错误处理：** 实现适当的错误处理和重试机制

### 3. 配置管理

- **版本控制：** 将模板文件纳入版本控制
- **命名规范：** 使用一致的 agent 命名规范
- **文档记录：** 为每个 agent 维护详细的文档

### 4. 性能优化

- **缓存：** 对于重复的模板解析，考虑使用缓存
- **并行处理：** 对于大量 JSON 文件，可以考虑并行处理
- **资源管理：** 合理管理 LLM API 调用频率

## 扩展开发

### 添加新的变量映射

```python
# 在 template_parser.py 中添加新的映射规则
VARIABLE_MAPPINGS = {
    "${sys.user_input}": "chat_round_30",
    "${custom_field}": "custom_mapping",
    # 添加新的映射...
}
```

### 自定义错误处理

```python
from src.agent_template_parser.error_handler import ErrorRecovery

class CustomErrorRecovery(ErrorRecovery):
    def handle_custom_error(self, error, context):
        # 自定义错误处理逻辑
        pass
```

### 扩展配置生成器

```python
from src.agent_template_parser.config_generator import AgentConfigGenerator

class CustomConfigGenerator(AgentConfigGenerator):
    def generate_custom_config(self, parsed_data, agent_name):
        # 自定义配置生成逻辑
        pass
```

## 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

### 开发环境设置

```bash
# 克隆项目
git clone <repository-url>
cd prompt-lab

# 安装依赖
pip install -r requirements.txt

# 运行测试
python -m pytest tests/test_agent_template_parser* -v

# 运行集成测试
python -m pytest tests/test_agent_template_parser_integration.py -v
```

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。

## 更新日志

### v1.0.0 (2024-12-03)

- ✨ 初始版本发布
- 🎯 支持从模板文件生成 agent 配置
- 📊 支持批量 JSON 处理生成测试集
- 🔧 集成 LLM 增强功能
- 🛠️ 完整的错误处理和恢复机制
- 📚 全面的文档和示例
- ✅ 完整的测试覆盖

## 支持

如果您遇到问题或有建议，请：

1. 查看本文档的故障排除部分
2. 搜索现有的 Issues
3. 创建新的 Issue 并提供详细信息

---

**Happy Coding! 🚀**