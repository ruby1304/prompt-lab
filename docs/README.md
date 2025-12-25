# Prompt Lab 文档导航

> **当前版本**: v0.8 (完成)
> 
> 所有 v0.8 核心功能已完成。查看 [统一 Spec](./../.kiro/specs/prompt-lab-unified/tasks.md) 了解详细进度。

## 📚 核心文档

### 快速开始
- [README.md](../README.md) - 项目主文档，快速开始指南

### 使用指南
- [使用指南](USAGE_GUIDE.md) - 详细的功能使用说明
- [系统架构](ARCHITECTURE.md) - 完整的系统架构说明和组件详解
- [架构分析](ARCHITECTURE_ANALYSIS.md) - 与 LangChain 生态对比和演进规划
- [故障排除](TROUBLESHOOTING.md) - 常见问题和解决方案
- [已知问题](known-issues.md) - 当前已知的问题和限制

### 管理指南
- [Agent 管理指南](guides/agent-management.md) - Agent 分类、管理和最佳实践
- [Agent Registry 指南](reference/agent-registry-guide.md) - Agent 统一注册和管理系统
- [Agent 模板使用指南](agent-template-guide.md) - 快速创建新 Agent
- [Output Parser 使用指南](guides/output-parser-usage.md) - Output Parser 快速开始
- [Testset 创建指南](guides/testset-creation-guide.md) - Pipeline 测试集创建完整指南
- [测试环境配置指南](guides/test-environment-setup.md) - 测试环境配置和验证完整指南
- [最佳实践指南](guides/best-practices.md) - Agent 开发和 Pipeline 设计最佳实践
- [示例指南](examples-guide.md) - 示例 Agent 和 Pipeline 使用说明
- [Big Thing Agent 指南](big_thing_agent_guide.md) - Big Thing Agent 使用示例

---

## 📖 参考文档

### Pipeline 相关
- [Pipeline 配置指南](reference/pipeline-guide.md) - Pipeline 配置语法和最佳实践
- [Code Node 配置指南](reference/code-node-config-guide.md) - 代码节点完整配置文档
- [Code Node 快速参考](reference/code-node-quick-reference.md) - 代码节点速查表
- [Batch Processing 配置指南](reference/batch-processing-config-guide.md) - 批量处理和聚合完整配置文档
- [Batch Processing 快速参考](reference/batch-processing-quick-reference.md) - 批量处理速查表
- [Batch Aggregator 快速参考](reference/batch-aggregator-quick-reference.md) - 批量聚合器速查表
- [Custom Aggregation 指南](reference/custom-aggregation-guide.md) - 自定义聚合代码使用指南
- [Concurrent Executor 指南](reference/concurrent-executor-guide.md) - 并发执行配置和使用
- [Progress Tracking 指南](reference/progress-tracking-guide.md) - 进度跟踪功能
- [项目结构说明](reference/project-structure.md) - 目录结构详解

### 评估相关
- [评估模式指南](reference/eval-modes-guide.md) - 评估系统详解
- [评估规则参考](reference/evaluation-rules.md) - 规则评估配置
- [手动评估指南](reference/manual-eval-guide.md) - 手动评估流程
- [回归测试指南](reference/regression-testing.md) - 基线管理和回归测试

### 数据相关
- [数据结构指南](reference/data-structure-guide.md) - 数据格式和组织
- [Output Parser 详细指南](reference/output-parser-guide.md) - Output Parser 完整使用文档
- [Batch Testset Format Guide](reference/batch-testset-format-guide.md) - 批量测试集格式指南
- [Pipeline Testset Format Specification](reference/pipeline-testset-format-specification.md) - Pipeline 级别测试集完整格式规范
- [Pipeline Testset Quick Reference](reference/pipeline-testset-quick-reference.md) - Pipeline 测试集速查表
- [Testset Loader Quick Reference](reference/testset-loader-quick-reference.md) - 测试集加载器速查表

### API 相关
- [API Design Specification](reference/api-design-specification.md) - 完整的 RESTful API 接口规范
- [API Routes Implementation Guide](reference/api-routes-implementation-guide.md) - API 路由实现指南
- [API Setup Guide](reference/api-setup-guide.md) - API 层配置和使用指南

### Agent 相关
- [Agent Template Parser 指南](reference/agent-template-parser-guide.md) - 模板解析和配置生成
- [Templates 目录使用指南](reference/templates-guide.md) - 模板文件组织和管理
- [Agent Registry Schema](reference/agent-registry-schema.md) - Agent Registry 配置格式规范
- [Agent Registry 快速参考](reference/agent-registry-quick-reference.md) - Agent Registry 速查表
- [Agent Registry 同步工具](reference/agent-registry-sync-guide.md) - 文件系统与 Registry 同步

### 测试相关
- [测试环境快速参考](reference/test-environment-quick-reference.md) - 测试环境配置速查表
- [Testset Property Tests Quick Reference](reference/testset-property-tests-quick-reference.md) - 测试集属性测试速查表
- [Testset Examples Quick Reference](reference/testset-examples-quick-reference.md) - 测试集示例速查表

### 其他
- [迁移指南](reference/migration-guide.md) - 版本升级指南
- [规则快速参考](reference/rules-quick-reference.md) - 常用规则速查

---

## 📦 归档文档

以下文档记录了项目的历史演进和重组过程，供参考：

### 历史文档
- [Agent 分类报告](archive/agent-classification-report.md) - Agent 分类分析
- [Agent 重组方案](archive/agent-reorganization-plan.md) - 详细的重组方案
- [Agent 分离总结](archive/agent-separation-summary.md) - 分离工作总结
- [重组完成报告](archive/reorganization-complete.md) - 重组完成状态
- [快速开始重组](archive/quick-start-reorganization.md) - 重组快速指南
- [测试套件总结](archive/test-suite-summary.md) - 测试执行总结
- [向后兼容性报告](archive/backward-compatibility-report.json) - 兼容性测试结果
- [项目分析报告（中文）](archive/project-analysis-cn.md) - 项目分析

### 任务执行报告
任务执行过程中产生的报告已归档到 [archive/task-reports/](archive/task-reports/) 目录。

---

## 🗂️ 文档组织

```
docs/
├── README.md                          # 本文件 - 文档导航
├── ARCHITECTURE.md                    # 系统架构
├── ARCHITECTURE_ANALYSIS.md           # 架构分析
├── TROUBLESHOOTING.md                 # 故障排除
├── USAGE_GUIDE.md                     # 使用指南
├── agent-template-guide.md            # Agent 模板使用指南
├── examples-guide.md                  # 示例指南
├── big_thing_agent_guide.md           # Big Thing Agent 指南
├── known-issues.md                    # 已知问题
│
├── guides/                            # 使用指南
│   ├── agent-management.md            # Agent 管理
│   └── output-parser-usage.md         # Output Parser 使用
│
├── reference/                         # 参考文档
│   ├── agent-template-parser-guide.md # Agent Template Parser
│   ├── templates-guide.md             # Templates 目录使用
│   ├── data-structure-guide.md
│   ├── eval-modes-guide.md
│   ├── evaluation-rules.md
│   ├── manual-eval-guide.md
│   ├── migration-guide.md
│   ├── output-parser-guide.md
│   ├── pipeline-guide.md
│   ├── project-structure.md
│   ├── regression-testing.md
│   └── rules-quick-reference.md
│
└── archive/                           # 归档文档
    ├── agent-classification-report.md
    ├── agent-reorganization-plan.md
    ├── agent-separation-summary.md
    ├── reorganization-complete.md
    ├── quick-start-reorganization.md
    ├── test-suite-summary.md
    ├── backward-compatibility-report.json
    └── project-analysis-cn.md
```

---

## 🔍 快速查找

### 我想...
- **快速开始使用** → [README.md](../README.md)
- **了解系统架构** → [ARCHITECTURE.md](ARCHITECTURE.md)
- **学习最佳实践** → [best-practices.md](guides/best-practices.md)
- **创建新 Agent** → [agent-template-guide.md](agent-template-guide.md)
- **注册和管理 Agent** → [agent-registry-guide.md](reference/agent-registry-guide.md)
- **同步 Agent Registry** → [agent-registry-sync-guide.md](reference/agent-registry-sync-guide.md)
- **配置 Pipeline** → [pipeline-guide.md](reference/pipeline-guide.md)
- **使用代码节点** → [code-node-config-guide.md](reference/code-node-config-guide.md)
- **使用批量处理** → [batch-processing-config-guide.md](reference/batch-processing-config-guide.md)
- **创建测试集** → [testset-creation-guide.md](guides/testset-creation-guide.md)
- **使用批量测试集** → [batch-testset-format-guide.md](reference/batch-testset-format-guide.md)
- **配置 Pipeline 测试集** → [pipeline-testset-format-specification.md](reference/pipeline-testset-format-specification.md)
- **使用自定义聚合** → [custom-aggregation-guide.md](reference/custom-aggregation-guide.md)
- **使用并发执行** → [concurrent-executor-guide.md](reference/concurrent-executor-guide.md)
- **使用 Output Parser** → [output-parser-usage.md](guides/output-parser-usage.md)
- **管理 Agent** → [agent-management.md](guides/agent-management.md)
- **评估 Agent/Pipeline** → [eval-modes-guide.md](reference/eval-modes-guide.md)
- **使用模板解析器** → [agent-template-parser-guide.md](reference/agent-template-parser-guide.md)
- **使用 API** → [api-design-specification.md](reference/api-design-specification.md)
- **实现 API 路由** → [api-routes-implementation-guide.md](reference/api-routes-implementation-guide.md)
- **查看示例** → [examples-guide.md](examples-guide.md)
- **解决问题** → [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- **查看已知问题** → [known-issues.md](known-issues.md)

---

**最后更新**: 2025-12-25 (v0.8)
