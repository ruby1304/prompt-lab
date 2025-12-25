# Templates 目录使用指南

本指南说明如何使用 `templates/` 目录组织和管理 Agent 模板文件。

## 推荐结构（新）

推荐使用 agent 专用文件夹和标准化文件名来组织模板：

```
templates/
├── my_agent/
│   ├── system_prompt    # 系统提示词模板（无扩展名）
│   ├── user_input      # 用户输入模板（无扩展名）
│   └── case           # 测试用例 JSON（无扩展名）
├── another_agent/
│   ├── system_prompt
│   ├── user_input
│   └── case
└── ...
```

### 新结构的优势
- **简化 CLI**：只需 `python -m src.agent_template_parser.cli create-agent <agent_name>` 即可创建 agent
- **更好的组织**：一个 agent 的所有文件都组织在一起
- **更清晰的命名**：标准文件名消除混淆
- **更易管理**：以完整单元的形式添加、删除或修改 agent 模板

## 传统结构（仍然支持）

原始的基于文件的结构继续支持向后兼容：

```
templates/
├── system_prompts/
│   ├── my_agent_system.txt
│   └── another_agent_system.txt
├── user_inputs/
│   ├── my_agent_user.txt
│   └── another_agent_user.txt
└── test_cases/
    ├── my_agent_test.json
    └── another_agent_test.json
```

## 使用方法

### 使用新文件夹结构（推荐）

1. 创建以 agent 命名的文件夹：`templates/{agent_name}/`
2. 添加三个标准名称的文件：
   - `system_prompt` - 包含系统提示词模板
   - `user_input` - 包含用户输入模板
   - `case` - 包含测试用例 JSON
3. 运行：`python -m src.agent_template_parser.cli create-agent {agent_name}`

### 使用传统结构

将模板文件放在相应的子目录中：
- 系统提示词模板：`system_prompts/{agent_name}_system.txt`
- 用户输入模板：`user_inputs/{agent_name}_user.txt`
- 测试用例文件：`test_cases/{agent_name}_test.json`

然后使用带文件路径的完整命令。

## 迁移指南

### 从传统结构转换到新结构

1. **创建 agent 文件夹**：`mkdir templates/{agent_name}`
2. **移动并重命名文件**：
   ```bash
   # 移动系统提示词
   mv system_prompts/{agent_name}_system.txt templates/{agent_name}/system_prompt
   
   # 移动用户输入
   mv user_inputs/{agent_name}_user.txt templates/{agent_name}/user_input
   
   # 移动测试用例
   mv test_cases/{agent_name}_test.json templates/{agent_name}/case
   ```
3. **测试迁移**：`python -m src.agent_template_parser.cli create-agent {agent_name}`

### 自动转换

使用内置转换工具进行更简单的迁移：

```bash
# 列出所有模板及其结构
python -m src.agent_template_parser.cli convert-templates --list

# 转换特定 agent
python -m src.agent_template_parser.cli convert-templates my_agent

# 预览将要转换的内容（试运行）
python -m src.agent_template_parser.cli convert-templates my_agent --dry-run

# 一次转换所有传统模板
python -m src.agent_template_parser.cli convert-templates --dry-run
python -m src.agent_template_parser.cli convert-templates
```

### 渐进式迁移

你可以一次迁移一个 agent。系统将：
1. 首先查找新文件夹结构
2. 如果未找到文件夹，则回退到传统结构
3. 如果两者都存在，则优先使用新结构

### 验证工具

验证模板结构是否正确：

```bash
# 验证特定 agent 的模板
python -m src.agent_template_parser.cli validate-templates --agent-name my_agent

# 使用独立验证脚本
python scripts/convert_templates.py validate my_agent
python scripts/convert_templates.py list
```

## 最佳实践

### 文件内容指南
- **system_prompt**：为 AI agent 编写清晰、具体的指令
- **user_input**：提供带有占位符的模板，如 `{variable_name}`
- **case**：包含具有预期输入/输出的真实测试场景

### 组织技巧
- 使用反映其用途的描述性 agent 名称
- 使用一致的命名对相关 agent 进行分组（例如，`customer_service_v1`、`customer_service_v2`）
- 保持模板专注于单一、明确定义的任务
- 在注释中记录任何特殊要求或依赖关系

### 模板验证
- 确保所有三个文件都存在且非空
- 在部署前测试模板
- 在模板中使用一致的格式和样式

## 故障排除

### 常见问题
- **缺少文件**：确保所有三个文件（`system_prompt`、`user_input`、`case`）都存在
- **空文件**：所有模板文件必须包含内容
- **错误位置**：agent 文件夹必须直接位于 `templates/` 下
- **文件扩展名**：新结构不使用文件扩展名

### 获取帮助
如果遇到问题，CLI 将提供有用的错误消息，显示：
- 预期的文件夹结构
- 缺少的文件
- 建议的修复方法

## 相关文档

- [Agent Template Parser 指南](agent-template-parser-guide.md)
- [Agent 模板使用指南](../agent-template-guide.md)
- [使用指南](../USAGE_GUIDE.md)
