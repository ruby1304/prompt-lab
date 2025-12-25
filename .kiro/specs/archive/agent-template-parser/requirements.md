# Requirements Document

## Introduction

本功能旨在为Prompt Lab项目添加两个核心能力：1）从文本模板文件自动生成符合项目规范的agent配置；2）批量处理JSON输入生成测试集。这将大大简化agent创建和测试数据准备的工作流程，提高开发效率。

## Requirements

### Requirement 1

**User Story:** 作为开发者，我希望能够通过提供三个txt文件（系统提示词模板、用户输入模板、测试case）来自动生成符合项目规范的agent配置，这样我就可以快速创建新的agent而不需要手动编写复杂的YAML配置。

#### Acceptance Criteria

1. WHEN 用户提供系统提示词模板文件 THEN 系统 SHALL 解析其中的${}格式变量占位符
2. WHEN 用户提供用户输入模板文件 THEN 系统 SHALL 识别并保留其中的变量结构
3. WHEN 用户提供测试case的JSON文件 THEN 系统 SHALL 解析其变量结构以理解数据格式
4. WHEN 所有三个文件都提供 THEN 系统 SHALL 生成符合项目规范的agent.yaml和prompt.yaml文件
5. WHEN 生成的配置文件存在格式差异 THEN 系统 SHALL 提供第二阶段的模型解析来修正格式
6. WHEN 配置生成完成 THEN 系统 SHALL 将文件保存到正确的agents目录结构中

### Requirement 2

**User Story:** 作为开发者，我希望能够批量处理多个JSON输入并生成指定agent的测试集，这样我就可以高效地为agent准备大量测试数据而不需要逐个手动转换。

#### Acceptance Criteria

1. WHEN 用户提供多个JSON格式的输入数据 THEN 系统 SHALL 解析每个JSON的结构和内容
2. WHEN 用户指定目标agent THEN 系统 SHALL 验证该agent是否存在于项目中
3. WHEN JSON数据包含sys.user_input等嵌套结构 THEN 系统 SHALL 正确提取和转换数据格式
4. WHEN 数据转换完成 THEN 系统 SHALL 生成符合项目testset格式的JSONL文件
5. WHEN 测试集生成完成 THEN 系统 SHALL 将文件保存到指定agent的testsets目录中
6. WHEN 处理过程中出现错误 THEN 系统 SHALL 提供详细的错误信息和建议

### Requirement 3

**User Story:** 作为开发者，我希望有一个专门的目录来管理输入的模板文件，这样我就可以有组织地存储和管理不同的模板资源。

#### Acceptance Criteria

1. WHEN 系统初始化 THEN 系统 SHALL 创建专门的模板输入目录结构
2. WHEN 用户上传模板文件 THEN 系统 SHALL 将文件保存到对应的子目录中
3. WHEN 目录结构包含系统提示词、用户输入、测试case三类文件 THEN 系统 SHALL 分别管理这些文件类型
4. WHEN 用户查看模板目录 THEN 系统 SHALL 提供清晰的文件组织结构
5. WHEN 模板文件被使用 THEN 系统 SHALL 能够正确定位和读取文件

### Requirement 4

**User Story:** 作为开发者，我希望系统能够智能处理模板中的变量替换逻辑，这样生成的agent配置就能正确处理动态内容。

#### Acceptance Criteria

1. WHEN 系统解析模板文件 THEN 系统 SHALL 识别${}格式的变量占位符
2. WHEN 遇到{user}和{role}占位符 THEN 系统 SHALL 保留这些特殊变量用于运行时替换
3. WHEN 遇到${sys.user_input}等系统变量 THEN 系统 SHALL 正确映射到agent配置的输入字段
4. WHEN 生成prompt配置 THEN 系统 SHALL 确保变量引用格式符合项目规范
5. WHEN 变量映射存在冲突 THEN 系统 SHALL 提供清晰的错误提示和解决建议

### Requirement 5

**User Story:** 作为开发者，我希望系统提供两阶段的处理机制（模板填充+模型解析），这样就能处理复杂的格式转换需求。

#### Acceptance Criteria

1. WHEN 第一阶段处理完成 THEN 系统 SHALL 生成基础的配置文件结构
2. WHEN 检测到格式差异 THEN 系统 SHALL 自动触发第二阶段的模型解析
3. WHEN 调用模型解析 THEN 系统 SHALL 使用适当的LLM来修正和优化配置格式
4. WHEN 模型解析完成 THEN 系统 SHALL 验证生成的配置文件的正确性
5. WHEN 两阶段处理都完成 THEN 系统 SHALL 提供处理结果的详细报告