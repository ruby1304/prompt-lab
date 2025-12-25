# Implementation Plan

**Status Summary:**
- ✅ Phase 1: 项目结构重组 (Complete)
- ✅ Phase 2: Agent Registry 系统 (Complete)
- ✅ Phase 3: Code Node Executor (Complete)
- ⏳ Phase 4: Concurrent Executor (Not Started)
- ⏳ Phase 5: Batch Aggregator (Not Started)
- ⏳ Phase 6: API Layer (Not Started)
- ⏳ Phase 7: Pipeline 测试集架构升级 (Not Started)
- ⏳ Phase 8: 测试和文档完善 (Partially Complete)

## Phase 1: 项目结构重组

- [x] 1. 创建项目结构迁移脚本
  - 编写 `scripts/migrate_structure.py` 脚本
  - 实现自动检测当前结构
  - 实现目录移动和文件重组逻辑
  - 添加备份功能
  - _Requirements: 1.2, 1.3, 1.4, 1.5_

- [x] 2. 执行测试内容迁移
  - 将 `tests/agents/` 下的测试 Agent 保留
  - 将 `examples/agents/` 下的示例 Agent 保留
  - 清理 `agents/` 目录，只保留生产 Agent
  - 验证所有 Agent 引用路径正确
  - _Requirements: 1.2, 1.3_

- [x] 3. 整合和清理文档
  - 将所有子目录的 README 移动到 `docs/`
  - 更新主 README.md，移除冗余内容
  - 更新所有文档间的链接引用
  - 创建 `docs/README.md` 作为文档导航
  - _Requirements: 1.4, 7.1, 7.2, 7.3, 7.5_

- [x] 4. 清理根目录脚本
  - 删除 `run_tests.py`
  - 删除 `run_spec_tests.sh`
  - 将有用的脚本移到 `scripts/` 目录
  - 更新文档中的脚本引用
  - _Requirements: 1.5, 6.3, 6.5_

- [x] 5. 创建 pyproject.toml 配置
  - 创建现代化的 Python 项目配置
  - 配置项目元数据
  - 配置依赖管理
  - 配置测试工具
  - _Requirements: 1.1_

- [x] 6. 验证迁移结果
  - 运行现有测试确保兼容性
  - 验证所有导入路径正确
  - 验证文档链接有效
  - 生成迁移报告
  - _Requirements: 1.2, 1.3, 1.4_

## Phase 2: Agent Registry 系统

- [x] 7. 设计 Agent Registry 配置格式
  - 创建 `config/agent_registry.yaml` 模板
  - 定义元数据字段规范
  - 设计分类和标签系统
  - 编写配置文档
  - _Requirements: 2.1, 2.2_

- [x] 8. 实现 AgentRegistry 核心类
  - 创建 `src/agent_registry_v2.py`
  - 实现配置文件加载
  - 实现 Agent 查询接口
  - 实现分类和标签过滤
  - _Requirements: 2.1, 2.3_

- [x] 9. 实现热重载机制
  - 实现文件监听功能
  - 实现自动重新加载
  - 添加重载事件通知
  - 处理重载错误
  - _Requirements: 2.4_

- [x] 10. 实现同步工具脚本
  - 创建 `scripts/sync_agent_registry.py`
  - 实现文件系统扫描
  - 实现自动生成 Registry 配置
  - 实现冲突检测和解决
  - _Requirements: 2.5_

- [x] 11. 编写 Agent Registry 单元测试
  - 测试配置加载功能
  - 测试查询和过滤功能
  - 测试热重载机制
  - _Requirements: 2.1, 2.3, 2.4_

- [x] 12. 编写 Agent Registry Property 测试
  - **Property 1: Registry loading completeness**
  - **Validates: Requirements 2.1**
  - 使用 Hypothesis 生成随机 Agent 配置
  - 测试加载完整性

- [x] 13. 编写 Agent Registry Property 测试
  - **Property 2: Agent registration persistence**
  - **Validates: Requirements 2.2**
  - 测试注册后的持久化

- [x] 14. 编写 Agent Registry Property 测试
  - **Property 3: Agent query completeness**
  - **Validates: Requirements 2.3**
  - 测试查询返回完整元数据

- [x] 15. 编写 Agent Registry Property 测试
  - **Property 4: Registry hot reload consistency**
  - **Validates: Requirements 2.4**
  - 测试热重载一致性

- [x] 16. 更新现有代码使用新 Registry
  - 更新 `src/agent_registry.py` 集成新系统
  - 更新 CLI 命令
  - 保持向后兼容性
  - _Requirements: 2.1, 2.3_

- [x] 17. Checkpoint - 确保所有测试通过
  - 确保所有测试通过，如有问题询问用户


## Phase 3: Code Node Executor

- [x] 18. 设计 Code Node 配置格式
  - 定义代码节点的 YAML 配置结构
  - 设计内联代码和外部文件引用格式
  - 定义输入输出接口
  - 编写配置文档
  - _Requirements: 3.1, 10.1_

- [x] 19. 实现 CodeExecutor 基础类
  - 创建 `src/code_executor.py`
  - 实现基础接口定义
  - 实现输入输出处理
  - 实现超时控制机制
  - _Requirements: 10.4, 10.5, 10.6_

- [x] 20. 实现 JavaScript 执行器
  - 实现 Node.js 进程调用
  - 实现代码注入和执行
  - 实现输出捕获
  - 实现错误处理
  - _Requirements: 3.2, 10.2_

- [x] 21. 实现 Python 执行器
  - 实现 subprocess 调用
  - 实现代码注入和执行
  - 实现输出捕获
  - 实现错误处理
  - _Requirements: 3.2, 10.3_

- [x] 22. 实现超时和错误处理
  - 实现进程超时终止
  - 实现详细错误堆栈捕获
  - 实现资源清理
  - 添加日志记录
  - _Requirements: 10.6, 10.7_

- [x] 23. 更新 Pipeline 配置解析
  - 更新 `src/models.py` 添加 CodeNodeConfig
  - 更新 `src/pipeline_config.py` 解析代码节点
  - 添加配置验证
  - _Requirements: 3.1_

- [x] 24. 更新 PipelineRunner 支持代码节点
  - 在 `src/pipeline_runner.py` 中集成 CodeExecutor
  - 实现代码节点步骤执行
  - 实现数据传递
  - 处理执行错误
  - _Requirements: 3.2, 3.7_

- [x] 25. 编写 Code Executor 单元测试
  - 测试 JavaScript 执行
  - 测试 Python 执行
  - 测试超时控制
  - 测试错误捕获
  - _Requirements: 3.2, 10.2, 10.3, 10.6, 10.7_

- [x] 26. 编写 Code Node Property 测试
  - **Property 5: Code node configuration parsing**
  - **Validates: Requirements 3.1**
  - 测试配置解析正确性

- [x] 27. 编写 Code Node Property 测试
  - **Property 6: JavaScript execution correctness**
  - **Validates: Requirements 3.2**
  - 测试 JS 代码执行正确性

- [x] 28. 编写 Code Node Property 测试
  - **Property 7: Python execution correctness**
  - **Validates: Requirements 3.2**
  - 测试 Python 代码执行正确性

- [x] 29. 编写 Code Node Property 测试
  - **Property 8: Code node input passing**
  - **Validates: Requirements 10.4**
  - 测试输入数据传递

- [x] 30. 编写 Code Node Property 测试
  - **Property 9: Code node output capture**
  - **Validates: Requirements 10.5**
  - 测试输出捕获

- [x] 31. 编写 Code Node Property 测试
  - **Property 10: Code node timeout enforcement**
  - **Validates: Requirements 10.6**
  - 测试超时机制
  - Note: Timeout tests are implemented in test_code_node_properties.py

- [x] 32. 编写 Code Node Property 测试
  - **Property 11: Code node error reporting**
  - **Validates: Requirements 10.7**
  - 测试错误报告
  - Note: Error reporting tests are implemented in test_code_node_properties.py

- [x] 33. Checkpoint - 确保所有测试通过
  - 确保所有测试通过，如有问题询问用户


## Phase 4: Concurrent Executor

- [x] 34. 实现 DependencyAnalyzer 类
  - 创建 `src/dependency_analyzer.py`
  - 实现依赖图构建
  - 实现拓扑排序
  - 实现并发组识别
  - _Requirements: 3.3_

- [x] 35. 实现 ConcurrentExecutor 类
  - 创建 `src/concurrent_executor.py`
  - 实现线程池/进程池管理
  - 实现任务队列
  - 实现结果收集
  - _Requirements: 9.1, 9.2_

- [x] 36. 实现并发执行调度
  - 实现依赖关系分析
  - 实现并发组调度
  - 实现同步点等待
  - 实现最大并发数控制
  - _Requirements: 3.4, 3.5, 3.6, 9.2_

- [x] 37. 实现进度跟踪
  - 实现实时进度更新
  - 实现进度查询接口
  - 集成到 PipelineProgressTracker
  - _Requirements: 9.5_

- [x] 38. 更新 PipelineRunner 支持并发
  - 集成 DependencyAnalyzer
  - 集成 ConcurrentExecutor
  - 实现并发步骤执行
  - 保持向后兼容
  - _Requirements: 3.4, 3.6_

- [x] 39. 实现并发错误处理
  - 实现错误隔离
  - 实现错误收集
  - 实现可选步骤处理
  - 实现结果顺序保持
  - _Requirements: 3.7, 9.3, 9.4_

- [x] 40. 编写 Dependency Analyzer 单元测试
  - 测试依赖图构建
  - 测试拓扑排序
  - 测试循环依赖检测
  - 测试并发组识别
  - _Requirements: 3.3_

- [x] 41. 编写 Concurrent Executor 单元测试
  - 测试任务队列
  - 测试并发执行
  - 测试最大并发数
  - 测试结果收集
  - _Requirements: 9.1, 9.2_

- [x] 42. 编写并发执行 Property 测试
  - **Property 12: Dependency identification**
  - **Validates: Requirements 3.3**
  - 测试依赖识别

- [x] 43. 编写并发执行 Property 测试
  - **Property 13: Concurrent execution of independent steps**
  - **Validates: Requirements 3.4**
  - 测试独立步骤并发执行

- [x] 44. 编写并发执行 Property 测试
  - **Property 14: Concurrent group parsing**
  - **Validates: Requirements 3.5**
  - 测试并发组解析

- [x] 45. 编写并发执行 Property 测试
  - **Property 15: Concurrent synchronization**
  - **Validates: Requirements 3.6**
  - 测试并发同步

- [x] 46. 编写并发执行 Property 测试
  - **Property 16: Concurrent error handling**
  - **Validates: Requirements 3.7**
  - 测试并发错误处理

- [x] 47. 编写并发执行 Property 测试
  - **Property 17: Concurrent test execution**
  - **Validates: Requirements 9.1**
  - 测试并发测试执行

- [x] 48. 编写并发执行 Property 测试
  - **Property 18: Max concurrency enforcement**
  - **Validates: Requirements 9.2**
  - 测试最大并发数限制

- [x] 49. 编写并发执行 Property 测试
  - **Property 19: Concurrent error isolation**
  - **Validates: Requirements 9.3**
  - 测试错误隔离

- [x] 50. 编写并发执行 Property 测试
  - **Property 20: Result order preservation**
  - **Validates: Requirements 9.4**
  - 测试结果顺序保持

- [x] 51. 编写并发执行 Property 测试
  - **Property 21: Progress feedback availability**
  - **Validates: Requirements 9.5**
  - 测试进度反馈

- [x] 52. 编写并发 Pipeline 集成测试
  - ⚠️ 使用真实的豆包 Pro 模型
  - 测试完整的并发 Pipeline 执行
  - 测试性能提升
  - _Requirements: 3.4, 9.1_

- [x] 53. 性能测试和优化
  - 测试并发性能提升
  - 优化线程池配置
  - 优化内存使用
  - 生成性能报告
  - _Requirements: 9.1_

- [x] 54. Checkpoint - 确保所有测试通过
  - 确保所有测试通过，如有问题询问用户


## Phase 5: Batch Aggregator

- [x] 55. 设计批量处理配置格式
  - 定义批量步骤的 YAML 配置
  - 定义聚合策略类型
  - 设计自定义聚合代码格式
  - 编写配置文档
  - _Requirements: 4.1, 4.5_

- [x] 56. 实现 BatchAggregator 类
  - 创建 `src/batch_aggregator.py`
  - 实现基础聚合接口
  - 实现拼接聚合 (concat)
  - 实现统计聚合 (stats)
  - _Requirements: 4.3, 4.5_

- [x] 57. 实现自定义聚合功能
  - 实现过滤聚合 (filter)
  - 实现自定义代码聚合
  - 集成 CodeExecutor
  - 实现错误处理
  - _Requirements: 4.3, 4.5_

- [x] 58. 实现 BatchProcessor 类
  - 实现批量数据收集
  - 实现批量大小控制
  - 实现批量并发处理
  - 实现结果聚合
  - _Requirements: 4.2_

- [x] 59. 更新 Pipeline 配置支持批量处理
  - 更新 StepConfig 添加批量字段
  - 更新配置解析器
  - 添加批量步骤验证
  - _Requirements: 4.1_

- [ ] 60. 更新 PipelineRunner 支持批量步骤
  - 实现批量步骤识别
  - 实现批量数据收集
  - 实现聚合步骤执行
  - 实现结果传递
  - _Requirements: 4.2, 4.4_

- [x] 61. 编写 Batch Aggregator 单元测试
  - 测试各种聚合策略
  - 测试自定义聚合代码
  - 测试批量处理
  - _Requirements: 4.3, 4.5_

- [x] 62. 编写批量处理 Property 测试
  - **Property 22: Batch step configuration parsing**
  - **Validates: Requirements 4.1**
  - 测试批量配置解析

- [x] 63. 编写批量处理 Property 测试
  - **Property 23: Batch output collection**
  - **Validates: Requirements 4.2**
  - 测试批量输出收集

- [x] 64. 编写批量处理 Property 测试
  - **Property 24: Batch aggregation correctness**
  - **Validates: Requirements 4.3**
  - 测试聚合正确性

- [x] 65. 编写批量处理 Property 测试
  - **Property 25: Aggregation result passing**
  - **Validates: Requirements 4.4**
  - 测试聚合结果传递

- [x] 66. 编写批量处理 Property 测试
  - **Property 26: Aggregation strategy parsing**
  - **Validates: Requirements 4.5**
  - 测试聚合策略解析

- [x] 67. 更新测试集格式支持批量处理
  - 设计批量测试集格式
  - 更新测试集加载器
  - 添加批量测试示例
  - _Requirements: 5.1, 5.5_

- [x] 68. 编写批量 Pipeline 集成测试
  - ⚠️ 使用真实的豆包 Pro 模型
  - 测试完整的批量处理流程
  - 测试 Agent1 → 聚合 → Agent2 场景
  - _Requirements: 4.2, 4.3, 4.4_

- [x] 69. Checkpoint - 确保所有测试通过
  - 确保所有测试通过，如有问题询问用户


## Phase 6: API Layer

- [x] 70. 选择和配置 API 框架
  - 选择 FastAPI 作为框架
  - 创建 `src/api/` 目录结构
  - 配置基础 FastAPI 应用
  - 配置 CORS 和中间件
  - _Requirements: 8.2_

- [x] 71. 设计 API 接口规范
  - 设计 RESTful API 路由
  - 定义请求/响应模型
  - 设计错误响应格式
  - 编写 API 设计文档
  - _Requirements: 8.2_

- [x] 72. 实现 Agent 管理 API
  - 实现 GET /agents (列出 Agent)
  - 实现 GET /agents/{id} (获取 Agent 详情)
  - 实现 POST /agents (注册 Agent)
  - 实现 PUT /agents/{id} (更新 Agent)
  - _Requirements: 8.2_

- [x] 73. 实现 Pipeline 管理 API
  - 实现 GET /pipelines (列出 Pipeline)
  - 实现 GET /pipelines/{id} (获取 Pipeline 详情)
  - 实现 POST /pipelines (创建 Pipeline)
  - 实现 PUT /pipelines/{id} (更新 Pipeline)
  - _Requirements: 8.2_

- [x] 74. 实现配置文件读写 API
  - 实现 GET /config/agents/{id} (读取 Agent 配置)
  - 实现 PUT /config/agents/{id} (更新 Agent 配置)
  - 实现 GET /config/pipelines/{id} (读取 Pipeline 配置)
  - 实现 PUT /config/pipelines/{id} (更新 Pipeline 配置)
  - _Requirements: 8.4_

- [x] 75. 实现异步执行 API
  - 实现 POST /execute/agent (异步执行 Agent)
  - 实现 POST /execute/pipeline (异步执行 Pipeline)
  - 实现任务队列管理
  - 实现后台任务执行
  - _Requirements: 8.5_

- [x] 76. 实现进度查询 API
  - 实现 GET /tasks/{task_id} (查询任务状态)
  - 实现 GET /tasks/{task_id}/progress (查询执行进度)
  - 实现 WebSocket 实时进度推送
  - _Requirements: 8.5_

- [x] 77. 实现数据模型序列化
  - 为所有数据模型添加 to_dict/from_dict
  - 为所有数据模型添加 JSON 序列化
  - 实现 Pydantic 模型转换
  - _Requirements: 8.3_

- [x] 78. 生成 OpenAPI 文档
  - 配置 FastAPI 自动文档生成
  - 添加 API 描述和示例
  - 配置 Swagger UI
  - 配置 ReDoc
  - _Requirements: 8.2_

- [x] 79. 编写 API 单元测试
  - 测试所有 API 端点
  - 测试请求验证
  - 测试错误处理
  - 使用 TestClient
  - _Requirements: 8.2, 8.4_

- [x] 80. 编写 API Property 测试
  - **Property 32: Core function API availability**
  - **Validates: Requirements 8.2**
  - 测试 API 可用性

- [x] 81. 编写 API Property 测试
  - **Property 33: Data model JSON serialization**
  - **Validates: Requirements 8.3**
  - 测试 JSON 序列化 round-trip

- [x] 82. 编写 API Property 测试
  - **Property 34: Configuration API read-write**
  - **Validates: Requirements 8.4**
  - 测试配置读写 round-trip

- [x] 83. 编写 API Property 测试
  - **Property 35: Async execution and progress query**
  - **Validates: Requirements 8.5**
  - 测试异步执行和进度查询

- [ ] 84. 编写 API 集成测试
  - ⚠️ 使用真实的豆包 Pro 模型
  - 测试完整的 API 工作流
  - 测试异步执行
  - 测试进度查询
  - _Requirements: 8.2, 8.5_

- [x] 85. Checkpoint - 确保所有测试通过
  - 确保所有测试通过，如有问题询问用户


## Phase 7: Pipeline 测试集架构升级

- [x] 86. 设计 Pipeline 级别测试集格式
  - 设计支持多步骤的测试集格式
  - 设计步骤级输入数据格式
  - 设计批量测试数据格式
  - 设计预期聚合结果格式
  - _Requirements: 5.1, 5.5_

- [x] 87. 更新测试集加载器
  - 更新 `src/testset_loader.py`
  - 实现 Pipeline 测试集解析
  - 实现步骤级数据提取
  - 实现批量数据组织
  - _Requirements: 5.1_

- [x] 88. 实现 Pipeline 评估支持
  - 实现最终输出评估
  - 实现中间步骤评估
  - 实现批量聚合结果评估
  - 集成到 unified_evaluator
  - _Requirements: 5.3, 5.4, 5.5_

- [x] 89. 创建测试集示例
  - 创建简单 Pipeline 测试集示例
  - 创建批量处理测试集示例
  - 创建多阶段评估测试集示例
  - 编写测试集创建指南
  - _Requirements: 5.1, 5.2, 5.5_

- [x] 90. 编写测试集 Property 测试
  - **Property 27: Multi-step testset parsing**
  - **Validates: Requirements 5.1**
  - 测试多步骤测试集解析

- [x] 91. 编写测试集 Property 测试
  - **Property 28: Batch test execution**
  - **Validates: Requirements 5.2**
  - 测试批量测试执行

- [x] 92. 编写测试集 Property 测试
  - **Property 29: Final output evaluation**
  - **Validates: Requirements 5.3**
  - 测试最终输出评估

- [x] 93. 编写测试集 Property 测试
  - **Property 30: Intermediate step evaluation**
  - **Validates: Requirements 5.4**
  - 测试中间步骤评估

- [x] 94. 编写测试集 Property 测试
  - **Property 31: Expected aggregation validation**
  - **Validates: Requirements 5.5**
  - 测试预期聚合验证

- [x] 95. Checkpoint - 确保所有测试通过
  - 确保所有测试通过，如有问题询问用户

## Phase 8: 测试和文档完善

- [x] 96. 配置测试环境
  - 配置 `.env.test` 文件
  - 配置豆包 Pro API 连接
  - 验证 API 连接正常
  - 配置测试数据库/存储
  - _Requirements: 所有涉及 LLM 的测试_

- [ ] 97. 补充缺失的单元测试
  - 审查代码覆盖率
  - 补充未覆盖的单元测试
  - 确保核心功能测试完整
  - _Requirements: 所有功能需求_

- [x] 98. 补充缺失的 Property 测试
  - 审查 Property 覆盖情况
  - 补充缺失的 Property 测试
  - 确保每个 Property 都有测试
  - _Requirements: 所有功能需求_

- [x] 99. 编写端到端集成测试
  - ⚠️ 使用真实的豆包 Pro 模型
  - 测试完整的用户场景
  - 测试复杂 Pipeline (Agent1 → 代码节点 → 批量聚合 → Agent2)
  - 测试并发执行场景
  - _Requirements: 3.4, 4.2, 4.3, 4.4, 9.1_

- [-] 100. 运行完整测试套件
  - 运行所有单元测试
  - 运行所有 Property 测试
  - 运行所有集成测试
  - 生成测试覆盖率报告
  - _Requirements: 所有功能需求_

- [ ] 101. 更新主 README 文档
  - 更新功能列表
  - 更新快速开始指南
  - 更新架构说明
  - 添加新功能示例
  - _Requirements: 7.1, 7.4_

- [ ] 102. 更新 API 文档
  - 完善 OpenAPI 文档
  - 编写 API 使用指南
  - 添加 API 示例代码
  - 创建 Postman Collection
  - _Requirements: 8.2_

- [ ] 103. 编写迁移指南
  - 编写从旧结构迁移的指南
  - 编写 API 迁移指南
  - 编写配置迁移指南
  - 提供迁移脚本
  - _Requirements: 1.2, 1.3, 2.1_

- [ ] 104. 编写最佳实践指南
  - 编写 Agent 开发最佳实践
  - 编写 Pipeline 设计最佳实践
  - 编写代码节点使用指南
  - 编写并发执行优化指南
  - 编写批量处理使用指南
  - _Requirements: 3.2, 3.4, 4.3_

- [ ] 105. 更新所有文档链接
  - 验证所有文档间链接
  - 更新过时的链接
  - 添加缺失的链接
  - 生成文档站点地图
  - _Requirements: 7.5_

- [ ] 106. 创建示例项目
  - 创建简单 Pipeline 示例
  - 创建代码节点示例
  - 创建批量处理示例
  - 创建并发执行示例
  - _Requirements: 3.2, 4.3, 9.1_

- [ ] 107. Final Checkpoint - 完整验证
  - 运行完整测试套件
  - 验证所有文档完整
  - 验证所有示例可运行
  - 生成最终报告
  - _Requirements: 所有需求_

## 备注

**⚠️ 重要提醒**:
- **所有涉及 LLM 调用的测试必须使用真实的豆包 (Doubao) Pro 模型**
- 测试前确保环境变量正确配置:
  - `OPENAI_API_KEY` 或对应的 Doubao API Key
  - `OPENAI_API_BASE` 指向 Doubao API 端点
  - `OPENAI_MODEL_NAME` 设置为 Doubao Pro 模型名称
- 集成测试应标记为 `@pytest.mark.integration`
- **不使用 mock 或模拟的 LLM 响应**

**执行顺序**:
- 按 Phase 顺序执行
- 每个 Phase 内按任务编号顺序执行
- 遇到 Checkpoint 时确保所有测试通过再继续
- 所有测试任务都是必需的，确保全面的测试覆盖

**测试策略**:
- 单元测试: 测试独立组件的功能
- Property 测试: 使用 Hypothesis 进行属性测试，每个测试至少100次迭代
- 集成测试: 测试完整的工作流，使用真实的豆包 Pro 模型
- 所有测试必须通过才能进入下一个 Phase

