# 统一评估命令 (run_eval.py)

## 概述

新的 `run_eval` 命令整合了之前分散的批量执行和judge评估功能，提供了一个统一、清晰的评估工具。

## 主要优势

✅ **一站式解决方案**：一个命令完成执行+评估，无需分两步操作  
✅ **智能文件命名**：自动生成带时间戳的文件名，避免覆盖  
✅ **统一token统计**：完整的token使用统计和成本分析  
✅ **灵活执行模式**：支持单flow和多flow对比执行  
✅ **可选judge评估**：可选择是否立即进行LLM judge评估  
✅ **清晰的进度显示**：分阶段显示执行和评估进度  

## 使用方法

### 基本语法
```bash
python -m src eval --agent <agent_id> [OPTIONS]
```

### 常用选项
- `--agent`: 必需，指定agent ID
- `--flows`: 可选，指定要执行的flow（逗号分隔），默认使用agent的所有flows
- `--judge`: 可选，是否在执行后立即进行judge评估
- `--limit`: 可选，限制执行的测试用例数量
- `--infile`: 可选，指定测试集文件，默认使用agent的default_testset
- `--outfile`: 可选，指定输出文件名，默认自动生成

## 使用示例

### 1. 单个flow执行（不带judge）
```bash
python -m src eval --agent mem0_l1_summarizer --flows mem0_l1_v3 --limit 5
```

### 2. 单个flow执行（带judge评估）
```bash
python -m src eval --agent mem0_l1_summarizer --flows mem0_l1_v3 --judge --limit 5
```

### 3. 多个flow对比执行
```bash
python -m src eval --agent mem0_l1_summarizer --flows mem0_l1_v1,mem0_l1_v2,mem0_l1_v3 --limit 5
```

### 4. 多个flow对比执行（带judge评估）
```bash
python -m src eval --agent mem0_l1_summarizer --flows mem0_l1_v1,mem0_l1_v2,mem0_l1_v3 --judge --limit 5
```

### 5. 使用agent的所有flows（带judge评估）
```bash
python -m src eval --agent mem0_l1_summarizer --judge --limit 5
```

## 输出文件

### 执行结果文件
- **单flow模式**: `{agent_id}_{flow_name}.results.{timestamp}.csv`
- **多flow模式**: `{agent_id}_compare.results.{timestamp}.csv`
- **带judge模式**: `{agent_id}_{flow_name}.eval.{timestamp}.csv`

### Judge评估文件（如果启用）
- 额外生成: `{原文件名}.judge.csv`
- 包含详细的评估结果和token统计

## 输出内容

### 执行结果文件包含：
- 测试用例的所有原始变量
- 每个flow的输出结果
- 详细的token统计信息

### Judge评估文件包含：
- 整体评分和评论
- must_have检查结果
- nice_to_have检查结果
- 详细的token统计

## 与旧命令的对比

| 功能 | 旧方式 | 新方式 |
|------|--------|--------|
| 单flow执行 | `python -m src batch` | `python -m src eval --flows flow_name` |
| 多flow对比 | `python -m src compare` | `python -m src eval --flows flow1,flow2` |
| Judge评估 | 先执行，再 `python -m src.eval_llm_judge` | 添加 `--judge` 参数 |
| 文件管理 | 手动指定文件名，容易覆盖 | 自动生成时间戳文件名 |
| Token统计 | 分散在不同命令中 | 统一显示，包含judge token |

## 兼容性

- 旧的 `batch`、`compare` 命令仍然可用
- 新命令完全兼容现有的agent配置和测试集格式
- 输出格式与旧命令保持一致，便于后续分析

## 快速开始

运行演示脚本查看所有使用示例：
```bash
./scripts/run_eval_demo.sh
```

这个统一的评估命令让整个评估流程更加简洁高效，特别适合需要频繁进行模型对比和评估的场景。