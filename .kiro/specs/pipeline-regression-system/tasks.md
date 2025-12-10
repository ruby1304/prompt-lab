# Implementation Plan

- [x] 1. 建立核心数据结构和配置系统
  - 创建 Pipeline、Step、Baseline 等核心数据类
  - 实现 YAML 配置文件的解析和验证逻辑
  - 建立配置文件的 schema 验证机制
  - _Requirements: 1.1, 1.2, 2.1, 2.2, 2.3_

- [x] 1.1 创建核心数据模型类
  - 在 `src/models.py` 中定义 PipelineConfig、StepConfig、BaselineConfig、VariantConfig 数据类
  - 实现数据类的验证方法和序列化/反序列化功能
  - 添加中文错误消息和字段描述
  - _Requirements: 1.1, 1.2, 11.3_

- [x] 1.2 实现 Pipeline YAML 配置解析器
  - 创建 `src/pipeline_config.py` 模块处理 pipeline YAML 文件加载
  - 实现配置文件的 schema 验证，包括必需字段和引用完整性检查
  - 添加循环依赖检测和中文错误提示
  - _Requirements: 2.1, 2.2, 2.3, 11.4_

- [x] 1.3 扩展现有 Agent 配置支持 baseline_flow
  - 修改 `src/agent_registry.py` 支持 baseline_flow 配置字段
  - 更新 Agent YAML schema 包含 baseline 相关配置
  - 实现向后兼容性确保现有配置继续工作
  - _Requirements: 3.1, 9.1, 9.2_

- [x] 2. 实现 Pipeline 执行引擎
  - 创建 PipelineRunner 类处理多步骤执行流程
  - 实现步骤间的数据传递和上下文管理
  - 集成现有的 chains.py 逻辑处理单步执行
  - _Requirements: 1.3, 1.4, 1.5_

- [x] 2.1 创建 PipelineRunner 核心执行器
  - 在 `src/pipeline_runner.py` 中实现 PipelineRunner 类
  - 实现 execute() 方法处理完整 pipeline 执行流程
  - 添加步骤执行进度跟踪和中文进度提示
  - _Requirements: 1.3, 10.1, 11.1_

- [x] 2.2 实现步骤执行和数据流管理
  - 实现 execute_step() 方法处理单个步骤执行
  - 创建输入映射解析器处理 testset 字段和前序步骤输出
  - 实现 pipeline 上下文管理和中间结果存储
  - _Requirements: 1.3, 1.4_

- [x] 2.3 集成现有 Agent/Flow 执行逻辑
  - 修改 `src/chains.py` 支持从 pipeline 上下文接收输入
  - 实现模型覆盖功能允许步骤级别的模型替换
  - 确保错误处理和异常传播机制正常工作
  - _Requirements: 1.4, 1.5, 11.4_

- [x] 3. 建立新的数据组织结构
  - 创建 data/agents/ 和 data/pipelines/ 目录结构
  - 实现数据文件的命名规范和时间戳管理
  - 提供数据迁移工具从现有结构迁移到新结构
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

- [x] 3.1 创建标准化目录结构
  - 实现 `src/data_manager.py` 模块管理数据目录创建和维护
  - 创建目录结构初始化函数支持 agents/ 和 pipelines/ 组织方式
  - 实现文件路径解析器支持新的目录结构
  - _Requirements: 4.1, 4.2_

- [x] 3.2 实现文件命名和时间戳管理
  - 创建标准化文件命名函数使用 ISO 时间戳格式
  - 实现文件版本管理避免覆盖重要结果
  - 添加文件元数据管理包括创建者和描述信息
  - _Requirements: 4.3_

- [x] 3.3 开发数据迁移工具
  - 创建 `scripts/migrate_data.py` 脚本迁移现有数据到新结构
  - 实现数据完整性检查确保迁移过程不丢失数据
  - 提供迁移进度报告和中文状态提示
  - _Requirements: 4.5, 9.3, 11.1_

- [x] 4. 实现 Testset 标签和过滤系统
  - 扩展 testset JSONL 格式支持 tags 字段
  - 创建 TestsetFilter 类处理基于标签的样本过滤
  - 更新现有的 batch 处理逻辑支持标签过滤
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 4.1 扩展 Testset 数据格式
  - 在 README.md 中添加 testset tags 字段的简要说明和示例
  - 更新 `docs/reference/data-structure-guide.md` 详细描述新的 tags 字段格式
  - 修改现有的 testset 加载逻辑支持可选的 tags 字段
  - 实现 testset 验证确保 tags 字段格式正确
  - _Requirements: 5.1, 12.1, 12.2_

- [x] 4.2 创建 TestsetFilter 过滤器类
  - 在 `src/testset_filter.py` 中实现 TestsetFilter 类
  - 实现 filter_by_tags() 方法支持 include/exclude 标签过滤
  - 添加 filter_by_scenario() 和其他过滤维度支持
  - _Requirements: 5.2, 5.3_

- [x] 4.3 集成标签过滤到现有执行流程
  - 修改 `src/run_batch.py` 支持 --include-tags 和 --exclude-tags 参数
  - 更新 `src/run_eval.py` 集成标签过滤功能
  - 实现过滤统计报告显示处理的样本数量和标签分布
  - _Requirements: 5.3, 5.4, 11.1_

- [x] 5. 开发 Pipeline 评估和比较系统
  - 创建 pipeline_eval.py 模块处理 pipeline 级别的评估
  - 实现多变体比较功能支持同时评估多个 pipeline 配置
  - 集成现有的规则评估和 LLM judge 逻辑到 pipeline 评估中
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 5.1 创建 Pipeline 评估执行器
  - 在 `src/pipeline_eval.py` 中实现 PipelineEvaluator 类
  - 实现 evaluate_pipeline() 方法处理单个 pipeline 评估
  - 集成现有的 eval_rules.py 和 eval_llm_judge.py 逻辑
  - _Requirements: 6.1, 6.3_

- [x] 5.2 实现多变体比较功能
  - 实现 compare_variants() 方法同时运行多个 pipeline 变体
  - 创建比较结果数据结构存储变体间的性能差异
  - 实现并行执行优化提高多变体比较效率
  - _Requirements: 6.2, 10.3_

- [x] 5.3 开发比较结果分析和报告
  - 创建 ComparisonEngine 类分析变体间的性能差异
  - 实现统计分析功能包括分数分布、must_have 通过率等
  - 生成中文格式的比较报告包含关键指标和建议
  - _Requirements: 6.4, 6.5, 11.1_

- [x] 6. 实现 Baseline 管理和回归测试
  - 创建 BaselineManager 类管理 baseline 配置和快照
  - 实现回归测试工作流比较新版本与 baseline 性能
  - 开发回归检测算法识别性能显著下降的案例
  - _Requirements: 3.2, 3.3, 3.4, 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 6.1 创建 Baseline 管理系统
  - 在 `src/baseline_manager.py` 中实现 BaselineManager 类
  - 实现 save_baseline() 和 load_baseline() 方法管理 baseline 快照
  - 创建 baseline 元数据管理包括创建时间、描述、性能指标
  - _Requirements: 3.2, 3.3_

- [x] 6.2 实现回归测试执行器
  - 创建 `src/regression_tester.py` 模块处理回归测试工作流
  - 实现 run_regression_test() 方法比较新版本与 baseline
  - 集成 pipeline 和 agent 级别的回归测试支持
  - _Requirements: 7.1, 7.2_

- [x] 6.3 开发回归检测和分析算法
  - 实现 detect_regressions() 方法识别性能显著下降的案例
  - 创建回归严重程度分类和优先级排序
  - 生成详细的回归分析报告包含具体案例和建议修复措施
  - _Requirements: 7.3, 7.4, 7.5, 11.1_

- [x] 7. 扩展 CLI 接口支持 Pipeline 操作
  - 更新 run_eval.py 支持 --pipeline 参数和相关选项
  - 创建新的 CLI 命令处理 baseline 管理和回归测试
  - 实现中文帮助文档和错误消息
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 11.1, 11.2, 11.4_

- [x] 7.1 扩展现有 eval 命令支持 Pipeline
  - 修改 `src/run_eval.py` 添加 --pipeline 参数支持
  - 实现 pipeline 和 agent 模式的统一接口
  - 添加 --variants 参数支持多变体比较
  - _Requirements: 8.1, 8.2_

- [x] 7.2 创建 Baseline 管理 CLI 命令
  - 创建 `src/baseline_cli.py` 模块处理 baseline 相关命令
  - 实现 baseline save/load/list/compare 子命令
  - 在 README.md 中添加 baseline 管理的使用示例和常用命令
  - 添加中文帮助文档和使用示例
  - _Requirements: 8.3, 11.2, 12.1_

- [x] 7.3 实现回归测试 CLI 接口
  - 创建 `src/regression_cli.py` 模块处理回归测试命令
  - 实现 eval_regression 命令支持 agent 和 pipeline 模式
  - 添加详细的中文进度提示和结果摘要
  - _Requirements: 8.3, 11.1, 11.4_

- [x] 8. 实现性能优化和错误处理
  - 添加进度指示器和预估完成时间显示
  - 实现断点续传功能支持大型 pipeline 执行
  - 创建全面的错误处理和中文错误消息系统
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 11.4_

- [x] 8.1 实现执行进度跟踪和显示
  - 创建 `src/progress_tracker.py` 模块管理执行进度
  - 实现进度条显示和预估完成时间计算
  - 添加中文进度消息和状态更新
  - _Requirements: 10.1, 11.1_

- [x] 8.2 开发断点续传和错误恢复机制
  - 实现执行状态保存和恢复功能
  - 创建错误恢复策略允许从失败步骤继续执行
  - 添加部分结果保存确保不丢失已完成的工作
  - _Requirements: 10.2_

- [x] 8.3 建立全面的错误处理系统
  - 创建 `src/error_handler.py` 模块统一管理错误处理
  - 实现分类错误处理包括配置、执行、数据错误
  - 提供清晰的中文错误消息和修复建议
  - _Requirements: 11.4_

- [x] 9. 确保向后兼容性和迁移支持
  - 验证现有 Agent/Flow 评估命令继续正常工作
  - 创建迁移指南和工具帮助用户逐步迁移到新系统
  - 实现混合模式支持新旧系统并存
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 9.1 验证现有功能的向后兼容性
  - 运行现有的测试套件确保所有功能正常工作
  - 测试现有的 CLI 命令和参数组合
  - 验证现有数据文件的访问和处理
  - _Requirements: 9.1, 9.2_

- [x] 9.2 创建迁移指南和工具
  - 编写详细的迁移文档包括步骤和最佳实践
  - 创建配置迁移工具自动转换现有配置到新格式
  - 提供迁移验证工具确保迁移完整性
  - _Requirements: 9.3, 9.4_

- [x] 9.3 实现混合模式运行支持
  - 确保新旧系统可以同时运行不冲突
  - 实现数据共享机制允许新旧系统访问相同数据
  - 添加弃用警告引导用户迁移到新功能
  - _Requirements: 9.4, 9.5_

- [x] 10. 编写测试和文档
  - 创建全面的单元测试覆盖所有新功能
  - 编写集成测试验证端到端工作流
  - 更新项目文档包括新功能使用指南
  - _Requirements: All requirements validation_

- [x] 10.1 编写核心功能单元测试
  - 为 PipelineRunner、TestsetFilter、BaselineManager 等核心类编写单元测试
  - 测试配置解析、数据验证、错误处理等关键功能
  - 确保测试覆盖率达到 90% 以上
  - _Requirements: All core functionality_

- [x] 10.2 创建集成测试套件
  - 编写端到端测试验证完整的 pipeline 执行流程
  - 测试多变体比较和回归测试工作流
  - 验证 CLI 接口和数据文件生成
  - _Requirements: All workflow requirements_

- [x] 10.3 更新统一文档结构
  - 重写 README.md 作为单一综合文档包含所有 pipeline 功能、使用方法和示例
  - 创建 `docs/` 目录存放结构化参考文档
  - 将现有的 DATA_STRUCTURE_GUIDE.md、EVAL_MODES_GUIDE.md 等移入 `docs/reference/` 
  - 在 README 中简要介绍每个参考文档的用途并提供链接
  - 创建 `docs/reference/pipeline-guide.md` 详细说明 pipeline 配置语法
  - 创建 `docs/reference/regression-testing.md` 详细说明回归测试工作流
  - 确保 README 包含完整的快速开始指南和常用命令示例
  - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5_