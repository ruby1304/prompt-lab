# Agent Template Parser

Agent Template Parser 是一个强大的工具，用于从文本模板文件自动生成符合项目规范的 agent 配置，并支持批量处理 JSON 数据生成测试集。

详细的使用说明请参考：[Agent Template Parser 指南](../../docs/reference/agent-template-parser-guide.md)

## 快速开始

### 从模板创建 Agent

```bash
python -m src.agent_template_parser.cli create-agent \
  --system-prompt templates/system_prompts/my_agent_system.txt \
  --user-input templates/user_inputs/my_agent_user.txt \
  --test-case templates/test_cases/my_agent_test.json \
  --agent-name my_agent
```

### 批量创建测试集

```bash
python -m src.agent_template_parser.cli create-testset \
  --json-files data1.json data2.json data3.json \
  --target-agent existing_agent \
  --output-filename batch_testset.jsonl
```

## 相关文档

- [Agent Template Parser 完整指南](../../docs/reference/agent-template-parser-guide.md)
- [模板目录使用指南](../../docs/reference/templates-guide.md)
- [Agent 模板使用指南](../../docs/agent-template-guide.md)
- [使用指南](../../docs/USAGE_GUIDE.md)
