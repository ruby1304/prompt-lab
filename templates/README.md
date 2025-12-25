# Templates 目录

本目录包含 Agent Template Parser 系统的输入模板文件。

详细的使用说明请参考：[Templates 目录使用指南](../docs/reference/templates-guide.md)

## 推荐结构

```
templates/
├── my_agent/
│   ├── system_prompt    # 系统提示词模板
│   ├── user_input      # 用户输入模板
│   └── case           # 测试用例 JSON
└── ...
```

## 快速开始

### 创建新模板

```bash
# 创建 agent 文件夹
mkdir templates/my_agent

# 添加模板文件
touch templates/my_agent/system_prompt
touch templates/my_agent/user_input
touch templates/my_agent/case

# 从模板创建 agent
python -m src.agent_template_parser.cli create-agent my_agent
```

## 相关文档

- [Templates 目录完整指南](../docs/reference/templates-guide.md)
- [Agent Template Parser 指南](../docs/reference/agent-template-parser-guide.md)
- [Agent 模板使用指南](../docs/agent-template-guide.md)
