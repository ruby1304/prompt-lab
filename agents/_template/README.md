# Agent模板使用说明

这是一个Agent模板，用于快速创建新的Agent。

## 使用步骤

1. **复制模板**：
   ```bash
   cp -r agents/_template agents/your_new_agent_id
   cd agents/your_new_agent_id
   ```

2. **修改配置**：
   - 编辑 `agent.yaml`，更新所有的 `your_agent_id` 和相关配置
   - 根据实际需求调整 `business_goal`、`expectations` 等字段

3. **创建提示词**：
   - 编辑 `prompts/your_agent_v1.yaml`
   - 根据任务需求设计 `system_prompt` 和 `user_template`
   - 设置合适的 `defaults` 值

4. **准备测试集**：
   - 编辑 `testsets/default.jsonl`
   - 添加真实的测试用例
   - 确保字段名与prompt模板中的变量对应

5. **测试Agent**：
   ```bash
   # 查看agent信息
   python -m src agents show your_new_agent_id
   
   # 运行测试
   python -m src eval --agent your_new_agent_id --limit 3
   ```

## 注意事项

- Agent ID必须唯一，不能与现有agent重复
- 提示词文件名要与agent.yaml中的flows配置对应
- 测试集字段要与case_fields配置匹配
- 建议先用小样本测试，确认无误后再扩大规模