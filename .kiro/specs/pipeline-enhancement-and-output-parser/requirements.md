# Requirements Document

## Introduction

本规范定义了 Prompt Lab 的两个关键增强功能：

1. **Pipeline 功能完善与示例补充**：补充可执行的 Pipeline 配置示例，完善文档和快速开始指南，使用户能够快速上手 Pipeline 功能。

2. **Output Parser 实现**：引入 LangChain 的 Output Parser 机制，提升结构化输出的可靠性，特别是改进 Judge Agent 的 JSON 输出解析。

这两个功能的设计遵循以下核心原则：
- **基于 LangChain 架构**：充分利用 LangChain 的设计模式和最佳实践
- **保持架构一致性**：Agent 和 Pipeline 的评估机制保持统一
- **快速配置与迭代**：支持便捷的导入、配置、调用、评估、比较、迭代流程
- **向后兼容**：不破坏现有功能，平滑升级

## Glossary

- **Agent**：具有明确业务目标的任务单元，包含配置、提示词版本和评估标准
- **Flow**：Agent 的一个具体实现版本，是可执行的 LangChain Chain
- **Pipeline**：多个 Agent/Flow 的串联组合，形成多步骤业务流程
- **Output Parser**：LangChain 的输出解析器，用于将 LLM 输出转换为结构化数据
- **Baseline**：用于回归测试的基准配置
- **Variant**：Pipeline 或 Agent 的变体配置，用于 A/B 测试

## Requirements

### Requirement 1: Pipeline 示例配置补充

**User Story:** 作为新用户，我希望能够通过完整的 Pipeline 示例快速理解和上手 Pipeline 功能，这样我就可以快速构建自己的多步骤工作流。

#### Acceptance Criteria

1. WHEN 项目初始化 THEN 系统 SHALL 在 `pipelines/` 目录下提供至少 2 个完整的示例配置
2. WHEN 用户查看简单示例 THEN 系统 SHALL 提供一个两步骤的文档处理 Pipeline（清洗 → 总结）
3. WHEN 用户查看复杂示例 THEN 系统 SHALL 提供一个多步骤的客服流程 Pipeline（意图识别 → 实体提取 → 回复生成）
4. WHEN 示例配置引用 Agent THEN 所有引用的 Agent 和 Flow SHALL 在项目中存在或提供创建指南
5. WHEN 示例配置包含测试集 THEN 测试集 SHALL 包含至少 5 个有代表性的测试用例

### Requirement 2: Pipeline 快速开始文档

**User Story:** 作为开发者，我希望有清晰的 Pipeline 快速开始指南，这样我就可以在 5 分钟内运行第一个 Pipeline 并看到结果。

#### Acceptance Criteria

1. WHEN 用户阅读 README THEN 系统 SHALL 在"快速开始"章节包含 Pipeline 运行示例
2. WHEN 用户执行快速开始命令 THEN 系统 SHALL 提供完整的命令行示例和预期输出
3. WHEN 用户需要创建新 Pipeline THEN 文档 SHALL 提供从零开始的创建步骤
4. WHEN 用户需要理解配置 THEN 文档 SHALL 提供配置字段的详细说明和最佳实践
5. WHEN 用户遇到问题 THEN 文档 SHALL 提供常见问题和故障排除指南

### Requirement 3: Pipeline 示例演示脚本

**User Story:** 作为开发者，我希望有 Python 脚本演示如何通过 API 使用 Pipeline，这样我就可以将 Pipeline 集成到自己的应用中。

#### Acceptance Criteria

1. WHEN 项目提供示例脚本 THEN 系统 SHALL 在 `examples/` 目录下包含 `pipeline_demo.py`
2. WHEN 脚本演示基本用法 THEN 系统 SHALL 展示如何加载、执行、评估 Pipeline
3. WHEN 脚本演示高级用法 THEN 系统 SHALL 展示如何对比变体、保存基线、运行回归测试
4. WHEN 脚本包含注释 THEN 注释 SHALL 清晰解释每个步骤的目的和参数
5. WHEN 用户运行脚本 THEN 脚本 SHALL 提供详细的输出和结果说明

### Requirement 4: Output Parser 基础架构

**User Story:** 作为系统架构师，我希望引入 LangChain 的 Output Parser 机制，这样系统就能可靠地处理结构化输出。

#### Acceptance Criteria

1. WHEN Flow 配置支持 output_parser THEN 系统 SHALL 允许指定 parser 类型（json, pydantic, list, custom）
2. WHEN 使用 JSON parser THEN 系统 SHALL 自动解析 LLM 输出为 JSON 对象
3. WHEN 使用 Pydantic parser THEN 系统 SHALL 根据 schema 验证和解析输出
4. WHEN 解析失败 THEN 系统 SHALL 支持自动重试机制（可配置重试次数）
5. WHEN 解析成功 THEN 系统 SHALL 返回结构化的 Python 对象而非字符串

### Requirement 5: Flow 配置中的 Output Parser 支持

**User Story:** 作为 Prompt 工程师，我希望在 Flow 配置中声明 output parser，这样系统就能自动处理输出格式转换。

#### Acceptance Criteria

1. WHEN 编辑 Flow YAML THEN 系统 SHALL 支持 `output_parser` 配置节
2. WHEN 配置 JSON parser THEN 系统 SHALL 支持指定 JSON schema 进行验证
3. WHEN 配置 Pydantic parser THEN 系统 SHALL 支持引用 Python 类定义
4. WHEN 配置重试策略 THEN 系统 SHALL 支持 `retry_on_error` 和 `max_retries` 参数
5. WHEN 未配置 parser THEN 系统 SHALL 默认返回原始字符串（向后兼容）

### Requirement 6: Judge Agent 的 Output Parser 集成

**User Story:** 作为评估系统用户，我希望 Judge Agent 的 JSON 输出能够自动解析和验证，这样评估结果就更可靠。

#### Acceptance Criteria

1. WHEN Judge Agent 执行评估 THEN 系统 SHALL 自动使用 JSON Output Parser
2. WHEN Judge 输出格式错误 THEN 系统 SHALL 自动重试最多 3 次
3. WHEN 重试仍失败 THEN 系统 SHALL 记录错误并提供降级处理（使用默认分数）
4. WHEN 解析成功 THEN 系统 SHALL 验证必需字段（overall_score, must_have_check, overall_comment）
5. WHEN 字段缺失或类型错误 THEN 系统 SHALL 提供清晰的错误信息和建议

### Requirement 7: 统一的评估接口

**User Story:** 作为开发者，我希望 Agent 评估和 Pipeline 评估使用统一的接口和配置方式，这样我就可以用相同的方式处理两种场景。

#### Acceptance Criteria

1. WHEN 执行评估 THEN Agent 和 Pipeline SHALL 使用相同的评估配置结构
2. WHEN 配置规则评估 THEN Agent 和 Pipeline SHALL 支持相同的规则类型和参数
3. WHEN 配置 Judge 评估 THEN Agent 和 Pipeline SHALL 使用相同的 Judge Agent 和配置
4. WHEN 查看评估结果 THEN Agent 和 Pipeline SHALL 使用相同的结果格式和字段
5. WHEN 导出评估报告 THEN Agent 和 Pipeline SHALL 支持相同的导出格式（CSV, JSON）

### Requirement 8: Pipeline 评估的特殊处理

**User Story:** 作为 Pipeline 用户，我希望 Pipeline 评估能够处理多步骤输出，这样我就可以评估整个工作流的质量。

#### Acceptance Criteria

1. WHEN 评估 Pipeline THEN 系统 SHALL 收集所有步骤的中间输出
2. WHEN 配置 Pipeline 评估 THEN 系统 SHALL 允许指定评估哪个步骤的输出（默认最后一步）
3. WHEN 执行 Judge 评估 THEN 系统 SHALL 将中间步骤输出作为上下文传递给 Judge
4. WHEN 查看评估结果 THEN 系统 SHALL 显示每个步骤的执行状态和输出
5. WHEN 步骤失败 THEN 系统 SHALL 记录失败原因并跳过后续步骤的评估

### Requirement 9: 快速配置与迭代工作流

**User Story:** 作为 Prompt 工程师，我希望能够快速创建、配置、测试、迭代 Agent 和 Pipeline，这样我就可以高效地优化提示词。

#### Acceptance Criteria

1. WHEN 创建新 Agent THEN 系统 SHALL 提供模板复制命令（基于 `agents/_template/`）
2. WHEN 创建新 Pipeline THEN 系统 SHALL 提供配置生成工具或模板
3. WHEN 修改配置后 THEN 系统 SHALL 支持快速运行单个测试用例验证
4. WHEN 对比版本 THEN 系统 SHALL 支持一键对比多个 Flow 或 Pipeline 变体
5. WHEN 迭代优化 THEN 系统 SHALL 支持保存当前最佳版本为 baseline

### Requirement 10: LangChain 架构优势利用

**User Story:** 作为系统架构师，我希望充分利用 LangChain 的架构优势，这样系统就能更容易扩展和维护。

#### Acceptance Criteria

1. WHEN 实现 Output Parser THEN 系统 SHALL 使用 LangChain 的标准 Output Parser 接口
2. WHEN 构建 Chain THEN 系统 SHALL 使用 LCEL（LangChain Expression Language）语法
3. WHEN 处理错误 THEN 系统 SHALL 利用 LangChain 的错误处理和重试机制
4. WHEN 扩展功能 THEN 系统 SHALL 遵循 LangChain 的组件化设计模式
5. WHEN 集成新功能 THEN 系统 SHALL 优先使用 LangChain 生态中的现有组件

### Requirement 11: 配置验证与错误提示

**User Story:** 作为用户，我希望在配置错误时能够得到清晰的错误提示，这样我就可以快速定位和修复问题。

#### Acceptance Criteria

1. WHEN 加载配置文件 THEN 系统 SHALL 验证 YAML 语法和必需字段
2. WHEN 引用不存在的 Agent/Flow THEN 系统 SHALL 提供可用选项列表
3. WHEN 配置 output_parser THEN 系统 SHALL 验证 schema 格式和类型定义
4. WHEN 配置 Pipeline 步骤 THEN 系统 SHALL 检测循环依赖和无效的数据流
5. WHEN 验证失败 THEN 系统 SHALL 提供具体的错误位置、原因和修复建议

### Requirement 12: 性能与可观测性

**User Story:** 作为系统运维人员，我希望能够监控 Pipeline 执行过程和性能，这样我就可以优化系统配置。

#### Acceptance Criteria

1. WHEN 执行 Pipeline THEN 系统 SHALL 记录每个步骤的执行时间
2. WHEN 使用 Output Parser THEN 系统 SHALL 记录解析成功率和重试次数
3. WHEN 调用 LLM THEN 系统 SHALL 记录 token 使用量（输入、输出、总计）
4. WHEN 执行完成 THEN 系统 SHALL 提供性能摘要（总时间、token 消耗、成功率）
5. WHEN 启用调试模式 THEN 系统 SHALL 输出详细的执行日志和中间结果

### Requirement 13: 文档完整性和架构整理

**User Story:** 作为用户，我希望有完整且结构清晰的文档，包括系统架构和开发路线图，这样我就可以充分理解和利用系统能力。

#### Acceptance Criteria

1. WHEN 查看 README THEN 系统 SHALL 包含完整的文档导航和链接
2. WHEN 查看 README THEN 系统 SHALL 包含"系统架构"章节，说明核心组件和数据流
3. WHEN 查看 README THEN 系统 SHALL 包含"开发路线图"章节，列出已完成、进行中和计划中的功能
4. WHEN 实现 Output Parser THEN 系统 SHALL 提供使用指南和配置示例
5. WHEN 更新评估机制 THEN 文档 SHALL 说明 Agent 和 Pipeline 评估的异同
6. WHEN 提供 API THEN 文档 SHALL 包含完整的 Python API 使用示例
7. WHEN 添加新配置选项 THEN 文档 SHALL 更新配置参考和字段说明
8. WHEN 创建新文档 THEN 文档 SHALL 在 README 中有链接和简要说明

### Requirement 14: 向后兼容性

**User Story:** 作为现有用户，我希望新功能不会破坏现有的工作流，这样我就可以平滑升级。

#### Acceptance Criteria

1. WHEN 引入 Output Parser THEN 未配置 parser 的 Flow SHALL 继续返回字符串
2. WHEN 更新评估接口 THEN 现有的评估命令和脚本 SHALL 继续工作
3. WHEN 添加新配置字段 THEN 所有字段 SHALL 是可选的且有合理默认值
4. WHEN 修改内部实现 THEN 外部 API 和 CLI 接口 SHALL 保持不变
5. WHEN 升级系统 THEN 现有的配置文件和数据 SHALL 无需修改即可使用

### Requirement 15: 测试覆盖

**User Story:** 作为开发者，我希望新功能有完整的测试覆盖，这样我就可以确保系统的稳定性。

#### Acceptance Criteria

1. WHEN 实现 Output Parser THEN 系统 SHALL 包含单元测试覆盖所有 parser 类型
2. WHEN 实现 Pipeline 示例 THEN 系统 SHALL 包含集成测试验证示例可运行
3. WHEN 实现评估接口 THEN 系统 SHALL 包含测试验证 Agent 和 Pipeline 评估一致性
4. WHEN 实现错误处理 THEN 系统 SHALL 包含测试覆盖各种错误场景
5. WHEN 运行测试套件 THEN 所有测试 SHALL 通过且覆盖率 SHALL 达到 85% 以上

### Requirement 16: 真实 LLM 调用测试

**User Story:** 作为质量保障工程师，我希望所有测试都使用真实的 doubao-1-5-pro-32k-250115 模型进行调用，这样我就可以验证系统在实际生产环境下的表现。

#### Acceptance Criteria

1. WHEN 运行任何测试 THEN 系统 SHALL 使用 .env 中配置的真实 API Key 和 doubao-1-5-pro-32k-250115 模型
2. WHEN 测试 Output Parser THEN 系统 SHALL 真实调用 doubao-1-5-pro-32k-250115 模型并解析返回结果
3. WHEN 测试 Pipeline 示例 THEN 系统 SHALL 使用 doubao-1-5-pro-32k-250115 模型完整执行所有步骤并验证输出
4. WHEN 测试 Judge Agent THEN 系统 SHALL 使用 doubao-1-5-pro-32k-250115 模型真实调用 Judge 并验证评分结果
5. WHEN 测试 Agent 执行 THEN 系统 SHALL 使用 doubao-1-5-pro-32k-250115 模型进行真实调用而非 Mock
6. WHEN API 调用失败 THEN 测试 SHALL 提供清晰的错误信息和调试建议
7. WHEN 配置测试环境 THEN 系统 SHALL 禁止使用 Mock 或假数据替代真实模型调用
8. WHEN 执行集成测试 THEN 系统 SHALL 验证 doubao-1-5-pro-32k-250115 模型的响应质量和格式
