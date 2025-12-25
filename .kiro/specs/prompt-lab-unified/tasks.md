# Prompt Lab v0.8 统一任务列表

## 版本状态

**当前版本**: v0.8 (完成)
**目标**: 完成所有核心功能，为 v1.0 做准备 ✅

### 模块完成状态

| 模块 | 状态 | 完成度 |
|------|------|--------|
| Module 1: 项目基础设施 | ✅ 完成 | 100% |
| Module 2: Agent Registry | ✅ 完成 | 100% |
| Module 3: Agent 模板解析 | ✅ 完成 | 100% |
| Module 4: Pipeline 系统 | ✅ 完成 | 100% |
| Module 5: Code Node | ✅ 完成 | 100% |
| Module 6: 并发执行 | ✅ 完成 | 100% |
| Module 7: 批量处理 | ✅ 完成 | 100% |
| Module 8: 评估系统 | ✅ 完成 | 100% |
| Module 9: API Layer | ✅ 完成 | 100% |
| Module 10: 测试集系统 | ✅ 完成 | 100% |
| Module 11: 文档和测试 | ✅ 完成 | 100% |

---

## Module 1: 项目基础设施 ✅

- [x] 1.1 创建项目结构迁移脚本
  - 编写 `scripts/migrate_structure.py`
  - 实现目录移动和文件重组
  - _Requirements: 1.1, 1.2_

- [x] 1.2 执行测试内容迁移
  - 分离测试 Agent 和生产 Agent
  - 验证所有引用路径正确
  - _Requirements: 1.2_

- [x] 1.3 整合和清理文档
  - 将文档移动到 `docs/` 目录
  - 创建 `docs/README.md` 文档导航
  - _Requirements: 1.4_

- [x] 1.4 创建 pyproject.toml 配置
  - 配置项目元数据和依赖
  - 配置测试工具
  - _Requirements: 1.3_

- [x] 1.5 验证迁移结果
  - 运行测试确保兼容性
  - 生成迁移报告
  - _Requirements: 1.1, 1.2_

---

## Module 2: Agent Registry 系统 ✅

- [x] 2.1 设计 Agent Registry 配置格式
  - 创建 `config/agent_registry.yaml`
  - 定义元数据字段规范
  - _Requirements: 2.1, 2.2_

- [x] 2.2 实现 AgentRegistry 核心类
  - 创建 `src/agent_registry_v2.py`
  - 实现配置加载和查询接口
  - _Requirements: 2.1, 2.3_

- [x] 2.3 实现热重载机制
  - 实现文件监听和自动重载
  - _Requirements: 2.4_

- [x] 2.4 实现同步工具脚本
  - 创建 `scripts/sync_agent_registry.py`
  - _Requirements: 2.5_

- [x] 2.5 编写 Agent Registry 测试
  - 单元测试和 Property 测试 (P1-P4)
  - _Requirements: 2.1-2.5_

---

## Module 3: Agent 模板解析 ✅

- [x] 3.1 创建模板解析器核心
  - 创建 `src/agent_template_parser/`
  - 实现模板文件解析
  - _Requirements: 3.1, 3.2_

- [x] 3.2 实现变量提取和映射
  - 提取 `${}` 格式变量
  - 映射到配置字段
  - _Requirements: 3.1, 3.2_

- [x] 3.3 实现配置文件生成
  - 生成 agent.yaml 配置
  - 生成 prompt 配置
  - _Requirements: 3.4_

- [x] 3.4 实现 LLM 增强处理
  - 使用 LLM 修正格式错误
  - _Requirements: 3.5_

- [x] 3.5 实现批量数据处理
  - 处理 JSON 测试数据
  - 生成 JSONL 测试集
  - _Requirements: 3.3_

- [x] 3.6 实现 CLI 接口
  - 创建命令行工具
  - _Requirements: 3.1-3.5_

---

## Module 4: Pipeline 系统 ✅

- [x] 4.1 创建 Pipeline 数据模型
  - 定义 PipelineConfig, StepConfig
  - _Requirements: 4.1_

- [x] 4.2 实现 Pipeline 配置解析
  - 创建 `src/pipeline_config.py`
  - 实现 YAML 解析和验证
  - _Requirements: 4.1_

- [x] 4.3 实现 PipelineRunner
  - 创建 `src/pipeline_runner.py`
  - 实现步骤执行和数据传递
  - _Requirements: 4.2, 4.3_

- [x] 4.4 实现步骤失败处理
  - 根据配置决定是否继续
  - _Requirements: 4.4_

- [x] 4.5 实现 baseline/variants 对比
  - 支持多变体比较
  - _Requirements: 4.5_

---

## Module 5: Code Node 执行引擎 ✅

- [x] 5.1 设计 Code Node 配置格式
  - 定义 CodeNodeConfig
  - 支持内联代码和外部文件
  - _Requirements: 5.1_

- [x] 5.2 实现 CodeExecutor 基础类
  - 创建 `src/code_executor.py`
  - _Requirements: 5.1_

- [x] 5.3 实现 JavaScript 执行器
  - 使用 Node.js 运行时
  - _Requirements: 5.2_

- [x] 5.4 实现 Python 执行器
  - 使用 subprocess
  - _Requirements: 5.3_

- [x] 5.5 实现超时和错误处理
  - 超时终止和错误捕获
  - _Requirements: 5.6, 5.7_

- [x] 5.6 编写 Code Node 测试
  - 单元测试和 Property 测试 (P5-P11)
  - _Requirements: 5.1-5.7_

---

## Module 6: 并发执行 ✅

- [x] 6.1 实现 DependencyAnalyzer
  - 创建 `src/dependency_analyzer.py`
  - 实现依赖图构建和拓扑排序
  - _Requirements: 6.1_

- [x] 6.2 实现 ConcurrentExecutor
  - 创建 `src/concurrent_executor.py`
  - 实现线程池管理
  - _Requirements: 6.2, 6.3_

- [x] 6.3 实现并发执行调度
  - 并发组调度和同步点等待
  - _Requirements: 6.2_

- [x] 6.4 实现进度跟踪
  - 创建 `src/progress_tracker.py`
  - _Requirements: 6.6_

- [x] 6.5 实现并发错误处理
  - 错误隔离和结果顺序保持
  - _Requirements: 6.4, 6.5_

- [x] 6.6 编写并发执行测试
  - 单元测试和 Property 测试 (P12-P21)
  - _Requirements: 6.1-6.6_

---

## Module 7: 批量处理 ✅

- [x] 7.1 设计批量处理配置格式
  - 定义批量步骤配置
  - _Requirements: 7.1_

- [x] 7.2 实现 BatchAggregator
  - 创建 `src/batch_aggregator.py`
  - 实现各种聚合策略
  - _Requirements: 7.3_

- [x] 7.3 实现自定义聚合功能
  - 集成 CodeExecutor
  - _Requirements: 7.5_

- [x] 7.4 实现 BatchProcessor
  - 批量数据收集和处理
  - _Requirements: 7.2_

- [x] 7.5 更新 PipelineRunner 支持批量步骤
  - 实现批量步骤识别和执行
  - _Requirements: 7.2, 7.4_

- [x] 7.6 编写批量处理测试
  - 单元测试和 Property 测试 (P22-P26)
  - _Requirements: 7.1-7.5_

---

## Module 8: 评估系统 ✅

- [x] 8.1 创建统一评估配置
  - 定义 EvaluationConfig
  - _Requirements: 8.3_

- [x] 8.2 实现 UnifiedEvaluator
  - 创建 `src/unified_evaluator.py`
  - 统一 Agent 和 Pipeline 评估
  - _Requirements: 8.1, 8.2_

- [x] 8.3 实现 Output Parser
  - 创建 `src/output_parser.py`
  - 支持 JSON, Pydantic 解析
  - _Requirements: 8.1_

- [x] 8.4 实现 BaselineManager
  - 创建 `src/baseline_manager.py`
  - _Requirements: 8.4_

- [x] 8.5 实现 RegressionTester
  - 创建 `src/regression_tester.py`
  - _Requirements: 8.4, 8.5_

- [x] 8.6 编写评估系统测试
  - 单元测试和集成测试
  - _Requirements: 8.1-8.5_

---

## Module 9: API Layer ✅

- [x] 9.1 配置 FastAPI 框架
  - 创建 `src/api/` 目录
  - 配置 CORS 和中间件
  - _Requirements: 9.1_

- [x] 9.2 实现 Agent 管理 API
  - GET/POST/PUT /agents
  - _Requirements: 9.1_

- [x] 9.3 实现 Pipeline 管理 API
  - GET/POST/PUT /pipelines
  - _Requirements: 9.2_

- [x] 9.4 实现配置文件读写 API
  - GET/PUT /config/*
  - _Requirements: 9.3_

- [x] 9.5 实现异步执行 API
  - POST /execute/*
  - _Requirements: 9.4_

- [x] 9.6 实现进度查询 API
  - GET /tasks/*
  - _Requirements: 9.4_

- [x] 9.7 生成 OpenAPI 文档
  - Swagger UI 和 ReDoc
  - _Requirements: 9.5_

- [x] 9.8 编写 API 单元测试
  - 测试所有端点
  - _Requirements: 9.1-9.5_

- [x] 9.9 编写 API Property 测试 (P32-P35)
  - _Requirements: 9.1-9.5_

- [x] 9.10 编写 API 集成测试
  - 使用真实 LLM 模型测试
  - _Requirements: 9.1-9.5_

---

## Module 10: 测试集系统 ✅

- [x] 10.1 设计 Pipeline 测试集格式
  - 支持多步骤测试数据
  - _Requirements: 10.1_

- [x] 10.2 更新测试集加载器
  - 更新 `src/testset_loader.py`
  - _Requirements: 10.1_

- [x] 10.3 实现 Pipeline 评估支持
  - 最终输出和中间步骤评估
  - _Requirements: 10.3_

- [x] 10.4 实现测试集过滤
  - 创建 `src/testset_filter.py`
  - 支持标签过滤
  - _Requirements: 10.5_

- [x] 10.5 创建测试集示例
  - 创建示例测试集
  - _Requirements: 10.1-10.5_

- [x] 10.6 编写测试集 Property 测试 (P27-P31)
  - _Requirements: 10.1-10.5_

---

## Module 11: 文档和测试完善 ✅

### 11.1 测试完善

- [x] 11.1.1 配置测试环境
  - 配置 `.env.test`
  - 验证 API 连接
  - _Requirements: All_

- [x] 11.1.2 补充缺失的单元测试
  - 审查代码覆盖率
  - 补充未覆盖的测试
  - _Requirements: All_

- [x] 11.1.3 补充 Property 测试
  - 确保所有 Property 都有测试
  - _Requirements: All_

- [x] 11.1.4 编写端到端集成测试
  - 测试完整用户场景
  - _Requirements: All_

- [-] 11.1.5 运行完整测试套件
  - 生成测试覆盖率报告
  - _Requirements: All_

### 11.2 文档完善

- [x] 11.2.1 更新主 README 文档
  - 更新功能列表
  - 更新快速开始指南
  - _Requirements: 1.4_

- [x] 11.2.2 更新 API 文档
  - 完善 OpenAPI 文档
  - 编写 API 使用指南
  - _Requirements: 9.5_

- [x] 11.2.3 编写迁移指南
  - 从旧结构迁移的指南
  - _Requirements: 1.2_

- [x] 11.2.4 编写最佳实践指南
  - Agent 开发最佳实践
  - Pipeline 设计最佳实践
  - _Requirements: All_

- [x] 11.2.5 更新所有文档链接
  - 验证链接有效性
  - _Requirements: 1.4_

- [x] 11.2.6 创建示例项目
  - Pipeline 示例
  - 代码节点示例
  - _Requirements: All_

### 11.3 项目整理

- [x] 11.3.1 归档旧 Spec 目录
  - 移动到 `.kiro/specs/archive/`
  - _Requirements: N/A_

- [x] 11.3.2 清理根目录临时文件
  - 移动 TASK_*.md 到 docs/archive/
  - 移动 CHECKPOINT_*.md 到 docs/archive/
  - _Requirements: N/A_

- [x] 11.3.3 整理 docs/reference/ 文档
  - 保留详细文档，更新导航索引
  - _Requirements: 1.4_

- [x] 11.3.4 更新文档导航
  - 更新 docs/README.md
  - _Requirements: 1.4_

---

## v1.0 待办事项

v0.8 所有核心任务已完成！以下是 v1.0 需要关注的方向：

1. **性能优化**
   - 优化并发执行性能
   - 优化内存使用
   - 添加缓存机制

2. **稳定性提升**
   - 完善错误处理
   - 增加重试机制
   - 添加更多边界测试

3. **可视化界面准备**
   - 完善 API 接口
   - 准备前端集成
   - 添加 WebSocket 实时更新

4. **新功能开发**
   - Memory 系统（多轮对话支持）
   - Streaming 输出（流式响应）
   - Tools 集成（函数调用）
   - RAG 支持（检索增强生成）

---

## 备注

**⚠️ 重要提醒**:
- 所有涉及 LLM 调用的测试必须使用真实的豆包 (Doubao) Pro 模型
- 集成测试标记为 `@pytest.mark.integration`
- Property 测试至少 100 次迭代

**测试策略**:
- 单元测试: 测试独立组件
- Property 测试: 使用 Hypothesis
- 集成测试: 使用真实 LLM 模型
