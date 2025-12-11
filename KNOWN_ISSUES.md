# 已知问题

1. **Pipeline 示例配置缺失**：仓库没有 `pipelines/` 目录，`data/pipelines/demo_pipeline` 仅包含以往运行产生的检查点文件，无法直接复现实例 Pipeline。需要补充可执行的 Pipeline 配置或在文档中提供创建步骤。【445216†L1-L2】【c06654†L1-L2】
2. **数据目录含历史产物未注明用途**：`data/` 下保留了 `high_score_cases.csv`、`results.demo.csv` 等运行输出，缺少用途说明，容易与用户评估结果混淆，建议迁移到示例目录或在文档中标注。【133f45†L1-L2】
