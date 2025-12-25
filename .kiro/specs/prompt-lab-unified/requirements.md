# Prompt Lab v0.8 统一需求文档

## Introduction

Prompt Lab 是一个用于 LLM Agent 开发、测试和评估的平台。本文档整合了项目从实验阶段向生产就绪阶段转型的所有需求，涵盖以下核心功能模块：

1. **项目基础设施** - 项目结构、配置管理
2. **Agent Registry** - Agent 统一注册和管理
3. **Agent 模板解析** - 从模板创建 Agent
4. **Pipeline 系统** - 多步骤工作流执行
5. **Code Node** - 代码节点执行引擎
6. **并发执行** - 并发执行和性能优化
7. **批量处理** - 批量聚合和后处理
8. **评估系统** - 统一评估和回归测试
9. **API Layer** - REST API 接口
10. **测试集系统** - Pipeline 级别测试集

## Glossary

- **Agent**: 具有明确业务目标的 LLM 任务单元
- **Flow**: Agent 的一个具体实现版本（prompt + 配置）
- **Pipeline**: 多个 Agent/Flow 的串联组合工作流
- **Code Node**: Pipeline 中的代码处理节点
- **Agent Registry**: Agent 统一注册和管理机制
- **Testset**: 测试数据集，JSONL 格式
- **Judge**: 使用 LLM 进行评估的 Agent
- **Baseline**: 基准版本，用于回归测试对比

## Requirements

### Module 1: 项目基础设施

**User Story:** 作为开发者，我希望项目结构清晰整洁，配置管理规范化。

#### Acceptance Criteria

1.1 WHEN 查看项目根目录 THEN the System SHALL 只包含必要的配置文件和单一的 README.md
1.2 WHEN 查看项目目录结构 THEN the System SHALL 将测试内容与生产内容分离
1.3 WHEN 查看项目配置 THEN the System SHALL 使用 pyproject.toml 进行现代化配置
1.4 WHEN 查看文档 THEN the System SHALL 将所有文档集中在 docs/ 目录下

### Module 2: Agent Registry 系统

**User Story:** 作为开发者，我希望有统一的地方管理所有 Agent 的元数据。

#### Acceptance Criteria

2.1 WHEN 系统启动时 THEN the System SHALL 从 Agent Registry 配置文件加载所有 Agent 元数据
2.2 WHEN 添加新 Agent 时 THEN the System SHALL 支持通过配置文件注册新 Agent
2.3 WHEN 查询 Agent 信息时 THEN the System SHALL 返回 Agent 的完整元数据
2.4 WHEN Agent Registry 配置更新时 THEN the System SHALL 自动热重载
2.5 WHEN Agent 目录变化时 THEN the System SHALL 提供同步工具脚本

### Module 3: Agent 模板解析

**User Story:** 作为开发者，我希望能从模板文件快速创建 Agent 配置。

#### Acceptance Criteria

3.1 WHEN 提供系统提示词模板时 THEN the System SHALL 解析并提取变量占位符
3.2 WHEN 提供用户输入模板时 THEN the System SHALL 解析并映射到配置字段
3.3 WHEN 提供测试用例 JSON 时 THEN the System SHALL 解析并生成测试集
3.4 WHEN 解析完成时 THEN the System SHALL 生成符合规范的 agent.yaml 配置
3.5 WHEN 配置格式有误时 THEN the System SHALL 使用 LLM 辅助修正

### Module 4: Pipeline 系统

**User Story:** 作为开发者，我希望能定义和执行多步骤的 Agent 工作流。

#### Acceptance Criteria

4.1 WHEN 定义 Pipeline 时 THEN the System SHALL 支持 YAML 格式的配置文件
4.2 WHEN 执行 Pipeline 时 THEN the System SHALL 按依赖顺序执行各步骤
4.3 WHEN 步骤间传递数据时 THEN the System SHALL 支持输入输出映射
4.4 WHEN 步骤执行失败时 THEN the System SHALL 根据配置决定是否继续
4.5 WHEN 配置 Pipeline 时 THEN the System SHALL 支持 baseline 和 variants 对比

### Module 5: Code Node 执行引擎

**User Story:** 作为开发者，我希望在 Pipeline 中使用代码节点进行数据转换。

#### Acceptance Criteria

5.1 WHEN 定义代码节点时 THEN the System SHALL 支持内联代码和外部文件引用
5.2 WHEN 执行 JavaScript 代码时 THEN the System SHALL 使用 Node.js 运行时
5.3 WHEN 执行 Python 代码时 THEN the System SHALL 使用 Python 解释器
5.4 WHEN 代码执行时 THEN the System SHALL 正确传递输入数据
5.5 WHEN 代码执行完成时 THEN the System SHALL 捕获输出和错误信息
5.6 WHEN 代码执行超时时 THEN the System SHALL 终止执行并返回超时错误
5.7 WHEN 代码执行失败时 THEN the System SHALL 提供详细的错误堆栈

### Module 6: 并发执行

**User Story:** 作为开发者，我希望系统能并发执行独立的步骤以提高性能。

#### Acceptance Criteria

6.1 WHEN 分析 Pipeline 步骤时 THEN the System SHALL 识别无依赖关系的步骤
6.2 WHEN 执行 Pipeline 时 THEN the System SHALL 并发执行独立步骤
6.3 WHEN 配置并发时 THEN the System SHALL 支持设置最大并发数
6.4 WHEN 并发执行时 THEN the System SHALL 正确处理错误和异常
6.5 WHEN 并发执行完成时 THEN the System SHALL 按原始顺序返回结果
6.6 WHEN 监控执行时 THEN the System SHALL 提供实时进度反馈

### Module 7: 批量处理

**User Story:** 作为开发者，我希望能批量处理多个测试用例并聚合结果。

#### Acceptance Criteria

7.1 WHEN 定义批量步骤时 THEN the System SHALL 支持 batch_mode 配置
7.2 WHEN 执行批量步骤时 THEN the System SHALL 收集所有输出结果
7.3 WHEN 聚合结果时 THEN the System SHALL 支持多种聚合策略（concat, stats, filter, custom）
7.4 WHEN 聚合完成时 THEN the System SHALL 将结果传递给后续步骤
7.5 WHEN 使用自定义聚合时 THEN the System SHALL 支持代码节点聚合

### Module 8: 评估系统

**User Story:** 作为开发者，我希望有统一的评估机制来验证 Agent 和 Pipeline 的输出质量。

#### Acceptance Criteria

8.1 WHEN 评估 Agent 输出时 THEN the System SHALL 支持规则评估和 LLM Judge 评估
8.2 WHEN 评估 Pipeline 输出时 THEN the System SHALL 支持最终输出和中间步骤评估
8.3 WHEN 配置评估时 THEN the System SHALL 支持统一的评估配置格式
8.4 WHEN 进行回归测试时 THEN the System SHALL 对比新版本与 baseline 的性能
8.5 WHEN 检测到回归时 THEN the System SHALL 提供详细的回归分析报告

### Module 9: API Layer

**User Story:** 作为开发者，我希望通过 REST API 访问系统的所有核心功能。

#### Acceptance Criteria

9.1 WHEN 访问 API 时 THEN the System SHALL 提供 Agent 管理接口
9.2 WHEN 访问 API 时 THEN the System SHALL 提供 Pipeline 管理接口
9.3 WHEN 访问 API 时 THEN the System SHALL 提供配置文件读写接口
9.4 WHEN 执行长时间任务时 THEN the System SHALL 支持异步执行和进度查询
9.5 WHEN 访问 API 文档时 THEN the System SHALL 提供 OpenAPI/Swagger 文档

### Module 10: 测试集系统

**User Story:** 作为开发者，我希望测试集能支持复杂 Pipeline 的评估需求。

#### Acceptance Criteria

10.1 WHEN 定义 Pipeline 测试集时 THEN the System SHALL 支持多步骤测试数据
10.2 WHEN 执行 Pipeline 测试时 THEN the System SHALL 支持批量执行和结果聚合
10.3 WHEN 评估 Pipeline 时 THEN the System SHALL 支持最终输出和中间步骤评估
10.4 WHEN 定义测试集时 THEN the System SHALL 支持预期聚合结果验证
10.5 WHEN 过滤测试集时 THEN the System SHALL 支持基于标签的过滤
