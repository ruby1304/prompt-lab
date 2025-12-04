# 数据目录结构指南

## 新的目录结构

经过重构，现在的数据目录按照 **agent + 类型** 分层管理，结构清晰：

```
data/
├── testsets/           # 测试集（进Git）
│   ├── mem0_l1_summarizer/
│   │   ├── mem0_l1.jsonl
│   │   └── test_cases.demo.jsonl
│   └── asr_cleaner/
│       └── core.jsonl
├── runs/              # 运行输出（不进Git）
│   ├── mem0_l1_summarizer/
│   │   ├── 2025-12-04T11-05-01_batch_mem0_l1_v1.csv
│   │   └── 2025-12-04T11-05-29_compare_mem0_l1_v1_mem0_l1_v2.csv
│   └── asr_cleaner/
│       └── 2025-12-04T09-15_compare_v1_v2_v3.csv
└── evals/             # 评估结果（不进Git）
    ├── mem0_l1_summarizer/
    │   ├── rules/     # 规则评估结果
    │   ├── manual/    # 人工评审结果
    │   └── llm/       # LLM评估结果
    └── asr_cleaner/
        ├── rules/
        ├── manual/
        └── llm/
```

## 文件命名规范

### 运行输出文件
- 单flow批量运行：`{timestamp}_batch_{flow_name}.csv`
- 多flow对比运行：`{timestamp}_compare_{flow1}_{flow2}_{...}.csv`

### 评估结果文件
- 规则评估：`{base_name}.rules.csv`
- 人工评审：`{base_name}.manual.csv`
- LLM评估：`{base_name}.judge.csv`

## 使用方式

### 1. 基本执行（自动路径）

```bash
# 单flow执行，自动使用默认测试集和输出路径
python -m src.run_eval --agent mem0_l1_summarizer --flows mem0_l1_v1

# 多flow对比，自动路径
python -m src.run_eval --agent mem0_l1_summarizer --flows mem0_l1_v1,mem0_l1_v2
```

### 2. 规则评估

```bash
# 对运行结果应用规则评估，自动输出到 evals/{agent}/rules/
python -m src.eval_rules run --agent mem0_l1_summarizer --infile 2025-12-04T11-05-29_compare_mem0_l1_v1_mem0_l1_v2.csv
```

### 3. 统计规则结果

```bash
# 统计规则评估结果
python -m src.eval_rules stats --agent mem0_l1_summarizer --infile 2025-12-04T11-05-29_compare_mem0_l1_v1_mem0_l1_v2.rules.csv
```

## 路径解析规则

1. **测试集路径**：
   - 未指定 `--infile` → 使用 `data/testsets/{agent_id}/{agent.default_testset}`
   - 指定相对路径 → `data/testsets/{agent_id}/{infile}`
   - 指定绝对路径 → 直接使用

2. **输出路径**：
   - 未指定 `--outfile` → 自动生成到 `data/runs/{agent_id}/`
   - 指定相对路径 → `data/runs/{agent_id}/{outfile}`
   - 指定绝对路径 → 直接使用

3. **评估结果路径**：
   - 规则评估 → `data/evals/{agent_id}/rules/`
   - 人工评审 → `data/evals/{agent_id}/manual/`
   - LLM评估 → `data/evals/{agent_id}/llm/`

## 优势

1. **清晰分类**：测试集、运行输出、评估结果分离
2. **按agent组织**：每个agent的所有相关文件都在一起
3. **自动路径**：大部分情况下不需要手动指定路径
4. **版本控制友好**：只有测试集进Git，运行结果不污染仓库
5. **时间戳命名**：运行结果按时间排序，容易找到最新的

## 迁移说明

旧的 `data/` 根目录文件已经按类型迁移到新结构：
- `*.jsonl` → `data/testsets/{agent}/`
- 运行结果 → `data/runs/{agent}/`
- 评估结果 → `data/evals/{agent}/{type}/`

现有脚本已经更新支持新的路径系统，向后兼容绝对路径的使用方式。