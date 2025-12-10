# 回归测试指南

本文档详细说明了回归测试的工作流程、配置方法和最佳实践。

## 概述

回归测试是一个自动化流程，用于比较新版本的 Agent/Flow 或 Pipeline 与已建立的基线版本的性能。它帮助识别性能下降、功能回退和质量问题。

## 核心概念

### Baseline（基线）

基线是经过验证的、稳定的配置版本，作为性能比较的标准。基线包含：

- 配置快照（Agent/Flow/Pipeline 设置）
- 性能指标（评分、通过率等）
- 评估结果（详细的样本级别结果）
- 元数据（创建时间、创建者、描述等）

### Variant（变体）

变体是要与基线进行比较的新配置版本。变体可以是：

- 新的 Flow 版本
- 不同的模型配置
- 修改的 Pipeline 步骤
- 参数调整

### Regression（回归）

回归是指新版本相比基线版本的性能下降，包括：

- 评分下降
- 必要条件通过率降低
- 规则违反增加
- 执行时间增长

## 工作流程

### 1. 创建基线

首先需要为 Agent 或 Pipeline 创建基线：

```bash
# 为 Agent 创建基线
python -m src baseline save \
  --agent my_agent \
  --flow stable_flow_v1 \
  --name production_baseline \
  --description "生产环境稳定版本"

# 为 Pipeline 创建基线
python -m src baseline save \
  --pipeline my_pipeline \
  --variant baseline \
  --name production_baseline \
  --description "生产环境 Pipeline 基线"
```

### 2. 运行回归测试

使用新的变体与基线进行比较：

```bash
# Agent 回归测试
python -m src eval_regression \
  --agent my_agent \
  --baseline production_baseline \
  --variant new_flow_v2

# Pipeline 回归测试
python -m src eval_regression \
  --pipeline my_pipeline \
  --baseline production_baseline \
  --variant experimental_v1
```

### 3. 分析回归结果

系统会生成详细的回归分析报告，包括：

- 整体性能变化
- 显著回归案例
- 按标签分组的性能分析
- 具体的改进建议

## 基线管理

### 创建基线

基线应该在以下情况下创建：

- 新功能开发完成并验证
- 重大版本发布前
- 性能优化完成后
- 定期的稳定版本检查点

### 基线命名规范

建议使用描述性的基线名称：

```bash
# 版本号命名
production_v1.0
stable_v2.1

# 功能命名
customer_service_baseline
document_processing_v1

# 时间命名
baseline_2025_01
quarterly_baseline_q1
```

### 基线操作

```bash
# 列出所有基线
python -m src baseline list --agent my_agent

# 查看基线详情
python -m src baseline show --agent my_agent --name production_v1

# 复制基线
python -m src baseline copy \
  --agent my_agent \
  --source production_v1 \
  --target backup_v1

# 删除基线
python -m src baseline delete --agent my_agent --name old_baseline
```

## 回归检测

### 检测阈值

系统使用多个指标来检测回归：

- **评分下降阈值**: 默认 0.3 分
- **必要条件通过率下降**: 默认 5%
- **规则违反增加**: 默认 10%

可以通过参数调整阈值：

```bash
python -m src eval_regression \
  --agent my_agent \
  --baseline production_v1 \
  --variant new_version \
  --score-threshold 0.5 \
  --must-have-threshold 0.1
```

### 严重程度分类

回归案例按严重程度分类：

- **Critical（严重）**: 评分下降 > 2.0 或必要条件失败
- **Major（重要）**: 评分下降 1.0-2.0
- **Minor（轻微）**: 评分下降 0.3-1.0

### 回归分析报告

典型的回归报告包含：

```
回归测试报告
=============

基线: production_v1
变体: experimental_v2
测试样本: 150

整体性能变化:
- 平均评分: 8.2 → 7.8 (-0.4)
- 必要条件通过率: 95% → 88% (-7%)
- 规则违反率: 5% → 12% (+7%)

严重回归案例: 3
- Critical: 1
- Major: 2
- Minor: 0

按标签分析:
- customer_service: -0.6 (显著下降)
- document_processing: -0.2 (轻微下降)
- edge_cases: -0.8 (严重下降)

建议:
1. 重点关注 customer_service 相关功能
2. 检查 edge_cases 的处理逻辑
3. 考虑回滚到基线版本
```

## 测试集设计

### 回归测试集

为回归测试创建专门的测试集：

```json
{
  "id": "regression_case_1",
  "tags": ["regression", "critical", "customer_service"],
  "scenario": "complaint_handling",
  "priority": "high",
  "expected_outcome": "准确识别投诉意图并提供合适回复",
  "input_text": "我对你们的服务很不满意..."
}
```

### 标签策略

使用标签组织回归测试：

- **功能标签**: `customer_service`, `document_processing`
- **场景标签**: `happy_path`, `edge_case`, `error_handling`
- **优先级标签**: `critical`, `important`, `nice_to_have`
- **回归标签**: `regression`, `smoke_test`, `full_test`

### 测试覆盖

确保回归测试覆盖：

- 核心功能路径
- 边界情况
- 历史问题案例
- 用户反馈的问题
- 性能敏感场景

## 自动化集成

### CI/CD 集成

将回归测试集成到持续集成流程：

```yaml
# .github/workflows/regression-test.yml
name: Regression Test

on:
  pull_request:
    branches: [main]

jobs:
  regression-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
          
      - name: Install dependencies
        run: pip install -r requirements.txt
        
      - name: Run regression tests
        run: |
          python -m src eval_regression \
            --agent customer_service \
            --baseline production_v1 \
            --variant pr_branch \
            --output-format json > regression_results.json
            
      - name: Check regression results
        run: |
          python scripts/check_regression_results.py regression_results.json
```

### 定期回归检查

设置定期的回归检查：

```bash
# 每日回归检查脚本
#!/bin/bash

# 运行所有关键 Agent 的回归测试
for agent in customer_service document_processor order_handler; do
  echo "Testing $agent..."
  python -m src eval_regression \
    --agent $agent \
    --baseline production_baseline \
    --variant current_version \
    --include-tags critical,regression
done

# 生成汇总报告
python scripts/generate_daily_regression_report.py
```

## 最佳实践

### 1. 基线管理

- 定期更新基线（如每月或每个版本）
- 为重要的里程碑创建基线
- 保留历史基线用于长期趋势分析
- 为基线添加详细的描述和元数据

### 2. 测试设计

- 创建专门的回归测试集
- 包含各种难度和场景的测试案例
- 定期审查和更新测试集
- 使用标签进行精细化管理

### 3. 阈值设置

- 根据业务需求调整回归阈值
- 对不同类型的功能使用不同阈值
- 定期评估和调整阈值设置
- 考虑渐进式阈值（随时间放宽）

### 4. 结果分析

- 不仅关注整体指标，也要分析具体案例
- 按功能模块和场景分析回归
- 建立回归趋势监控
- 及时响应严重回归

### 5. 团队协作

- 建立回归测试的责任制
- 定期回顾回归测试结果
- 分享回归分析的见解
- 持续改进回归测试流程

## 故障排除

### 常见问题

**Q: 基线创建失败**
A: 检查 Agent/Pipeline 配置是否正确，确保测试集文件存在且格式正确。

**Q: 回归测试结果不准确**
A: 验证基线和变体使用相同的测试集，检查评估配置是否一致。

**Q: 回归阈值过于敏感**
A: 根据历史数据调整阈值，考虑使用相对阈值而非绝对阈值。

**Q: 回归测试执行时间过长**
A: 使用标签过滤减少测试样本，或者使用并行执行（如果支持）。

### 调试技巧

1. **使用小规模测试集**: 先用少量样本验证配置
2. **检查日志输出**: 查看详细的执行日志
3. **对比具体案例**: 分析具体的回归案例
4. **验证配置一致性**: 确保基线和变体配置正确

## 相关文档

- [Pipeline 配置指南](pipeline-guide.md)
- [数据结构指南](data-structure-guide.md)
- [评估规则指南](../EVALUATION_RULES.md)