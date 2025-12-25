# Requirements Document

## Introduction

本需求文档定义了 Prompt Lab 项目从实验阶段向生产就绪阶段转型的完整需求。项目当前存在测试内容与生产内容混杂、缺乏统一的 Agent 管理机制、复杂 Pipeline 支持不足等问题。本次重构旨在建立清晰的项目结构、统一的管理机制，并支持复杂的生产场景（如 Agent 链式调用、代码节点、并发执行等）。

## Glossary

- **System**: Prompt Lab 平台
- **Agent**: 具有明确业务目标的任务单元
- **Flow**: Agent 的一个具体实现版本
- **Pipeline**: 多个 Agent/Flow 的串联组合工作流
- **Code Node**: Pipeline 中的代码处理节点，用于数据转换和预处理
- **Agent Registry**: Agent 统一注册和管理机制
- **Production Content**: 实际业务使用的 Agent、Pipeline 和配置
- **Test Content**: 用于测试和开发的 Agent、Pipeline 和固件
- **Concurrent Execution**: 并发执行多个独立的 Pipeline 步骤
- **Batch Processing**: 批量处理多个测试用例
- **Testset**: 测试数据集，JSONL 格式
- **Visualization Interface**: 可视化管理界面

## Requirements

### Requirement 1: 项目结构清理和优化

**User Story:** 作为开发者，我希望项目结构清晰整洁，测试内容与生产内容分离，以便快速定位和维护代码。

#### Acceptance Criteria

1. WHEN 查看项目根目录 THEN the System SHALL 只包含必要的配置文件和单一的 README.md 文档
2. WHEN 查看项目目录结构 THEN the System SHALL 将所有测试脚本、测试 Agent、测试 Pipeline 统一放置在 tests 目录下
3. WHEN 查看项目目录结构 THEN the System SHALL 将所有生产 Agent 放置在 agents 目录下，所有生产 Pipeline 放置在 pipelines 目录下
4. WHEN 查看项目文档 THEN the System SHALL 将所有非主文档的 README 文件移动到 docs 目录下
5. WHEN 查看项目根目录 THEN the System SHALL 移除所有过时的测试运行脚本（如 run_tests.py, run_spec_tests.sh）

### Requirement 2: Agent 统一注册和管理机制

**User Story:** 作为开发者，我希望有一个统一的地方管理所有 Agent 的名称和元数据，以便快速调整和维护大量 Agent。

#### Acceptance Criteria

1. WHEN 系统启动时 THEN the System SHALL 从统一的 Agent Registry 配置文件加载所有 Agent 的元数据
2. WHEN 添加新 Agent 时 THEN the System SHALL 支持通过更新 Agent Registry 配置文件来注册新 Agent
3. WHEN 查询 Agent 信息时 THEN the System SHALL 从 Agent Registry 返回 Agent 的 ID、名称、分类、描述等元数据
4. WHEN Agent Registry 配置文件更新时 THEN the System SHALL 自动重新加载 Agent 列表
5. WHEN Agent 目录结构变化时 THEN the System SHALL 提供工具脚本自动同步 Agent Registry 配置

### Requirement 3: 复杂 Pipeline 支持

**User Story:** 作为开发者，我希望 Pipeline 支持代码节点、并发执行和复杂的数据流，以满足生产环境的复杂需求。

#### Acceptance Criteria

1. WHEN 定义 Pipeline 步骤时 THEN the System SHALL 支持定义代码节点（Code Node）类型的步骤
2. WHEN 执行代码节点时 THEN the System SHALL 支持执行 JavaScript 或 Python 代码进行数据转换
3. WHEN 分析 Pipeline 步骤依赖时 THEN the System SHALL 识别无依赖关系的步骤
4. WHEN 执行 Pipeline 时 THEN the System SHALL 并发执行所有无依赖关系的步骤
5. WHEN 配置 Pipeline 时 THEN the System SHALL 支持定义步骤的并发组（Concurrent Group）
6. WHEN 执行并发步骤时 THEN the System SHALL 等待所有并发步骤完成后再继续执行后续步骤
7. WHEN 代码节点执行失败时 THEN the System SHALL 记录错误并根据配置决定是否继续执行

### Requirement 4: 批量聚合和后处理支持

**User Story:** 作为开发者，我希望能够批量处理多个测试用例的输出，并将聚合结果传递给下一个 Agent，以支持复杂的评估流程。

#### Acceptance Criteria

1. WHEN 定义 Pipeline 时 THEN the System SHALL 支持定义批量处理步骤（Batch Step）
2. WHEN 执行批量处理步骤时 THEN the System SHALL 收集前序步骤的所有输出结果
3. WHEN 聚合批量结果时 THEN the System SHALL 支持使用代码节点对批量结果进行聚合和转换
4. WHEN 批量结果聚合完成时 THEN the System SHALL 将聚合结果作为单个输入传递给后续 Agent
5. WHEN 配置批量处理时 THEN the System SHALL 支持定义聚合策略（如拼接、统计、过滤等）

### Requirement 5: Pipeline 级别的测试集支持

**User Story:** 作为开发者，我希望测试集能够支持复杂 Pipeline 的评估需求，包括多阶段测试和批量评估。

#### Acceptance Criteria

1. WHEN 定义 Pipeline 测试集时 THEN the System SHALL 支持为不同步骤定义不同的测试数据
2. WHEN 执行 Pipeline 测试时 THEN the System SHALL 支持批量执行多个测试用例并聚合结果
3. WHEN 评估 Pipeline 时 THEN the System SHALL 支持对整个 Pipeline 的最终输出进行评估
4. WHEN 评估 Pipeline 时 THEN the System SHALL 支持对 Pipeline 中间步骤的输出进行评估
5. WHEN 定义测试集时 THEN the System SHALL 支持为批量处理步骤定义预期的聚合结果

### Requirement 6: 过时脚本和文件清理

**User Story:** 作为开发者，我希望项目中只保留有用的脚本和文件，移除所有过时和冗余的内容。

#### Acceptance Criteria

1. WHEN 审查项目脚本时 THEN the System SHALL 识别所有不再使用的测试脚本
2. WHEN 审查项目脚本时 THEN the System SHALL 识别所有功能重复的脚本
3. WHEN 清理项目时 THEN the System SHALL 移除所有过时的单元测试脚本
4. WHEN 清理项目时 THEN the System SHALL 保留所有核心功能的测试脚本
5. WHEN 清理项目时 THEN the System SHALL 更新文档以反映脚本的变更

### Requirement 7: 文档结构优化

**User Story:** 作为用户，我希望项目只有一个入口 README 文件，其他文档都收纳在 docs 目录下，以便快速找到需要的信息。

#### Acceptance Criteria

1. WHEN 查看项目根目录时 THEN the System SHALL 只包含一个主 README.md 文件
2. WHEN 查看 docs 目录时 THEN the System SHALL 包含所有详细文档和子文档
3. WHEN 查看子目录时 THEN the System SHALL 不包含独立的 README.md 文件
4. WHEN 主 README 更新时 THEN the System SHALL 提供清晰的文档导航链接
5. WHEN 文档移动后 THEN the System SHALL 更新所有文档间的相互引用链接

### Requirement 8: 可视化界面准备

**User Story:** 作为开发者，我希望项目结构为即将添加的可视化界面做好准备，确保前后端分离清晰。

#### Acceptance Criteria

1. WHEN 规划项目结构时 THEN the System SHALL 预留 frontend 或 ui 目录用于可视化界面
2. WHEN 设计 API 时 THEN the System SHALL 确保核心功能可通过 API 调用
3. WHEN 设计数据模型时 THEN the System SHALL 确保数据模型支持 JSON 序列化
4. WHEN 设计配置文件时 THEN the System SHALL 确保配置文件可通过 API 读写
5. WHEN 设计执行流程时 THEN the System SHALL 支持异步执行和进度查询

### Requirement 9: 并发执行性能优化

**User Story:** 作为开发者，我希望系统能够并发执行独立的测试用例和 Pipeline 步骤，以提高测试速度。

#### Acceptance Criteria

1. WHEN 执行批量测试时 THEN the System SHALL 支持并发执行多个独立的测试用例
2. WHEN 配置并发执行时 THEN the System SHALL 支持设置最大并发数
3. WHEN 并发执行测试时 THEN the System SHALL 正确处理并发错误和异常
4. WHEN 并发执行完成时 THEN the System SHALL 按原始顺序返回结果
5. WHEN 监控并发执行时 THEN the System SHALL 提供实时进度反馈

### Requirement 10: 代码节点执行引擎

**User Story:** 作为开发者，我希望在 Pipeline 中使用代码节点进行数据转换，支持 JavaScript 和 Python 代码。

#### Acceptance Criteria

1. WHEN 定义代码节点时 THEN the System SHALL 支持内联代码和外部文件引用
2. WHEN 执行 JavaScript 代码节点时 THEN the System SHALL 使用 Node.js 运行时执行代码
3. WHEN 执行 Python 代码节点时 THEN the System SHALL 使用 Python 解释器执行代码
4. WHEN 代码节点执行时 THEN the System SHALL 传递输入数据作为参数
5. WHEN 代码节点执行完成时 THEN the System SHALL 捕获输出数据和错误信息
6. WHEN 代码节点执行超时时 THEN the System SHALL 终止执行并返回超时错误
7. WHEN 代码节点执行失败时 THEN the System SHALL 提供详细的错误堆栈信息
