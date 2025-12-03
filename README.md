# Prompt Lab

一个用于快速迭代与验证 Prompt 的实验项目，提供单条验证、批量跑数和多模型对比，同时内置自动评估的分析 Agent。所有命令均默认使用中文输出。

## 目录结构

- `prompts/`：Prompt Flow 配置（YAML），可在 `defaults` 中为变量设置兜底值。
- `src/`：核心脚本与工具。
  - `chains.py`：加载 Prompt Flow 并执行模型调用，自动补全缺失变量。
  - `run_single.py`：单样本验证。
  - `run_batch.py`：批量跑测试集（JSONL -> CSV）。
  - `run_compare.py`：多 Flow 对比同一批样本。
  - `run_analysis.py`：自动评估模型输出。
- `data/`：示例测试集与输出文件。

## 环境准备

1. 创建 `.env` 并写入你的 OpenAI Key：

   ```bash
   cp .env.example .env
   # 编辑 .env，填入 OPENAI_API_KEY、OPENAI_MODEL_NAME 等
   ```

2. 安装依赖：

   ```bash
   pip install -r requirements.txt
   ```

## 使用指南

### 1）单条验证

```bash
python -m src.run_single --flow flow_demo --text "你好" --context "可选上下文" --vars '{"user_name": "小明"}'
```

`--vars` 支持任意 JSON 对象，模板未用到的变量会自动忽略，缺失的变量会使用 Prompt 配置里的 `defaults` 或空字符串兜底。

### 2）批量跑测试集

```bash
python -m src.run_batch --flow flow_demo --infile test_cases.demo.jsonl --outfile results.demo.csv
```

`data/test_cases.demo.jsonl` 每行一个 JSON，字段可多可少：脚本会将除 `id/expected` 外的字段全部作为变量传入模型。

### 3）多 Flow 对比

```bash
python -m src.run_compare --flows mem0_l1_v1,mem0_l1_v2 --infile mem0_l1.jsonl --outfile results.compare.csv
```

每条样本的全部字段都会被传入指定的多个 Flow，输出列名形如 `output__{flow}`。

### 4）自动评估（分析 Agent）

```bash
python -m src.run_analysis --infile results.demo.csv --output-column output --flow analysis_agent
```

分析 Agent 会读取指定输出列，与 `input/expected/context` 等字段一起生成评估结果，写回 `{原文件名}.analysis.csv`。

## 自定义 Prompt Flow

在 `prompts/*.yaml` 中新增配置即可：

```yaml
name: "my_flow"
description: "描述" 
system_prompt: "系统提示词..."
user_template: "用户模板，使用 {变量名} 占位"
defaults:
  某变量: "兜底值"
```

- 模板中未使用的变量可以出现在数据集中；
- 若数据集中缺少某个变量，优先使用 `defaults`，否则自动用空字符串兜底。
- 系统提示词与用户模板共享同一套变量解析逻辑，支持占位符自动替换，未提供的变量同样会按上述顺序兜底。

