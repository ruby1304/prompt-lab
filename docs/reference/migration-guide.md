# Pipeline 系统迁移指南

本指南帮助用户从现有的单 Agent/Flow 评估系统逐步迁移到新的 Pipeline 系统，同时保持现有工作流程的正常运行。

## 迁移概述

Pipeline 系统是对现有系统的扩展，而不是替换。您可以：

- **继续使用现有命令**：所有现有的 Agent/Flow 评估命令保持不变
- **逐步采用新功能**：根据需要逐步引入 Pipeline 功能
- **混合使用**：在同一项目中同时使用 Agent 和 Pipeline 评估

## 迁移路径

### 阶段 1：了解新功能（无需修改现有工作流程）

在这个阶段，您可以继续使用现有的命令，同时了解新的 Pipeline 功能：

```bash
# 现有命令继续正常工作
python -m src eval --agent mem0_l1_summarizer --flows mem0_l1_v3 --judge
python -m src batch --agent asr_cleaner --flow asr_clean_v1
python -m src compare --agent mem0_l1_summarizer --flows mem0_l1_v1,mem0_l1_v2
```

### 阶段 2：创建第一个 Pipeline（可选）

当您需要评估多步骤工作流程时，可以创建您的第一个 Pipeline：

1. **识别多步骤场景**：
   - 需要将多个 Agent/Flow 串联执行
   - 前一步的输出作为后一步的输入
   - 需要对整个工作流程进行评估

2. **创建 Pipeline 配置**：
   ```yaml
   # pipelines/my_first_pipeline.yaml
   id: "my_first_pipeline"
   name: "我的第一个管道"
   description: "ASR 清理 + 对话总结的完整流程"
   
   inputs:
     - name: "raw_asr_text"
       desc: "原始 ASR 识别文本"
   
   steps:
     - id: "clean_step"
       type: "agent_flow"
       agent: "asr_cleaner"
       flow: "asr_clean_v1"
       input_mapping:
         input: "raw_asr_text"
       output_key: "cleaned_text"
   
     - id: "summary_step"
       type: "agent_flow"
       agent: "mem0_l1_summarizer"
       flow: "mem0_l1_v3"
       input_mapping:
         chat_round_30: "cleaned_text"
       output_key: "summary"
   
   outputs:
     - key: "summary"
       label: "最终总结"
   
   baseline:
     name: "baseline_v1"
     description: "基线配置"
   ```

3. **测试 Pipeline**：
   ```bash
   python -m src eval --pipeline my_first_pipeline --limit 3
   ```

### 阶段 3：数据组织迁移（推荐但非必需）

新系统提供了更好的数据组织结构，但现有数据仍然可以正常访问：

#### 新的目录结构
```
data/
├── agents/                    # 新：按 agent 组织
│   └── {agent_id}/
│       ├── testsets/
│       ├── runs/
│       └── evals/
├── pipelines/                 # 新：按 pipeline 组织
│   └── {pipeline_id}/
│       ├── testsets/
│       ├── runs/
│       └── evals/
└── [现有文件保持不变]        # 旧：现有文件继续可用
```

#### 使用迁移工具（可选）
```bash
# 迁移现有数据到新结构
python scripts/migrate_data.py --agent mem0_l1_summarizer --dry-run
python scripts/migrate_data.py --agent mem0_l1_summarizer --execute
```

### 阶段 4：采用高级功能（按需）

根据需要采用更高级的功能：

- **Baseline 管理**：保存和比较基线性能
- **回归测试**：自动检测性能下降
- **标签过滤**：基于标签的精确测试
- **变体比较**：系统化的 A/B 测试

## 详细迁移步骤

### 1. Agent 配置迁移

现有的 Agent 配置无需修改，但您可以选择添加新功能：

#### 添加 baseline_flow（可选）
```yaml
# agents/your_agent/agent.yaml
flows:
  - name: "your_flow_v1"
    file: "your_flow_v1.yaml"
    notes: "基线版本"
  - name: "your_flow_v2"
    file: "your_flow_v2.yaml"
    notes: "改进版本"

# 新增：指定基线 flow
baseline_flow: "your_flow_v1"
```

#### 增强测试集标签（可选）
```jsonl
{"id": "1", "input": "测试输入", "tags": ["regression", "happy_path"]}
{"id": "2", "input": "边缘情况", "tags": ["edge_case", "regression"]}
```

### 2. 命令行使用迁移

#### 现有命令保持不变
```bash
# 这些命令继续正常工作
python -m src batch --agent your_agent --flow your_flow_v1
python -m src eval --agent your_agent --flows your_flow_v1,your_flow_v2 --judge
python -m src compare --agent your_agent --flows your_flow_v1,your_flow_v2
```

#### 新增标签过滤功能
```bash
# 使用标签过滤（适用于现有命令）
python -m src eval --agent your_agent --flows your_flow_v1 --include-tags regression
python -m src batch --agent your_agent --exclude-tags edge_case
```

#### 新增 Pipeline 命令
```bash
# Pipeline 评估
python -m src eval --pipeline your_pipeline --variants baseline,variant_a
python -m src baseline save --pipeline your_pipeline --variant baseline --name stable_v1
python -m src regression --pipeline your_pipeline --variant new_version --baseline stable_v1
```

### 3. 数据文件迁移

#### 自动迁移工具
```bash
# 查看迁移计划（不执行）
python scripts/migrate_data.py --agent your_agent --dry-run

# 执行迁移
python scripts/migrate_data.py --agent your_agent --execute

# 验证迁移结果
python scripts/migrate_data.py --agent your_agent --verify
```

#### 手动迁移步骤
如果您偏好手动迁移：

1. **创建新目录结构**：
   ```bash
   mkdir -p data/agents/your_agent/{testsets,runs,evals}
   ```

2. **移动测试集文件**：
   ```bash
   # 从 agents/your_agent/testsets/ 复制到 data/agents/your_agent/testsets/
   cp agents/your_agent/testsets/*.jsonl data/agents/your_agent/testsets/
   ```

3. **移动运行结果**：
   ```bash
   # 移动相关的 CSV 文件
   mv data/runs/your_agent_*.csv data/agents/your_agent/runs/
   ```

## 常见迁移场景

### 场景 1：单 Agent 多 Flow 比较

**现有方式**：
```bash
python -m src compare --agent mem0_l1_summarizer --flows mem0_l1_v1,mem0_l1_v2,mem0_l1_v3
```

**新方式（可选）**：
```bash
# 使用统一的 eval 命令
python -m src eval --agent mem0_l1_summarizer --flows mem0_l1_v1,mem0_l1_v2,mem0_l1_v3

# 或者使用 baseline 比较
python -m src baseline save --agent mem0_l1_summarizer --flow mem0_l1_v1 --name baseline
python -m src regression --agent mem0_l1_summarizer --flow mem0_l1_v2 --baseline baseline
```

### 场景 2：多步骤工作流程

**现有方式**（需要手动串联）：
```bash
# 步骤 1：ASR 清理
python -m src batch --agent asr_cleaner --flow asr_clean_v1 --infile raw_asr.jsonl --outfile cleaned.csv

# 步骤 2：手动处理中间结果
# ... 需要手动脚本处理 ...

# 步骤 3：对话总结
python -m src batch --agent mem0_l1_summarizer --flow mem0_l1_v3 --infile processed.jsonl
```

**新方式**（自动化 Pipeline）：
```bash
# 创建 Pipeline 配置后，一条命令完成
python -m src eval --pipeline asr_to_summary --variants baseline
```

### 场景 3：回归测试

**现有方式**（手动比较）：
```bash
# 运行基线版本
python -m src eval --agent your_agent --flows baseline_flow --outfile baseline_results.csv

# 运行新版本
python -m src eval --agent your_agent --flows new_flow --outfile new_results.csv

# 手动比较结果
```

**新方式**（自动化回归测试）：
```bash
# 保存基线
python -m src baseline save --agent your_agent --flow baseline_flow --name stable_v1

# 自动回归测试
python -m src regression --agent your_agent --flow new_flow --baseline stable_v1
```

## 迁移验证清单

### ✅ 基本功能验证
- [ ] 现有 Agent 配置正常加载
- [ ] 现有 CLI 命令正常执行
- [ ] 现有数据文件正常访问
- [ ] 输出格式保持一致

### ✅ 新功能验证
- [ ] 标签过滤功能正常
- [ ] Pipeline 配置加载正常
- [ ] Pipeline 执行正常
- [ ] Baseline 管理功能正常

### ✅ 数据迁移验证
- [ ] 迁移工具运行正常
- [ ] 数据完整性检查通过
- [ ] 新旧数据访问都正常
- [ ] 文件路径解析正确

## 故障排除

### 常见问题

#### 1. 命令找不到
**问题**：`python -m src eval --pipeline` 报错
**解决**：确保您使用的是最新版本的代码，Pipeline 功能已正确安装

#### 2. 配置文件格式错误
**问题**：Pipeline YAML 配置解析失败
**解决**：使用配置验证工具检查格式：
```bash
python -c "from src.pipeline_config import load_pipeline_config; load_pipeline_config('your_pipeline')"
```

#### 3. 数据文件路径问题
**问题**：找不到测试集文件
**解决**：检查文件路径，使用新的文件查找逻辑：
```bash
# 检查可用的测试集
python -c "from src.agent_registry import load_agent; print(load_agent('your_agent').all_testsets)"
```

#### 4. 迁移工具失败
**问题**：数据迁移过程中出错
**解决**：
1. 先运行 `--dry-run` 查看迁移计划
2. 检查文件权限
3. 确保目标目录有足够空间
4. 查看详细错误日志

### 获取帮助

如果遇到迁移问题：

1. **查看帮助文档**：
   ```bash
   python -m src --help
   python -m src eval --help
   python -m src baseline --help
   ```

2. **运行兼容性测试**：
   ```bash
   python scripts/test_backward_compatibility.py
   ```

3. **检查配置文件**：
   ```bash
   python scripts/validate_config.py --agent your_agent
   python scripts/validate_config.py --pipeline your_pipeline
   ```

## 最佳实践

### 1. 渐进式迁移
- 不要一次性迁移所有内容
- 先在小范围内测试新功能
- 保持现有工作流程的稳定性

### 2. 备份重要数据
- 在迁移前备份重要的结果文件
- 使用版本控制管理配置文件
- 定期验证数据完整性

### 3. 团队协作
- 与团队成员沟通迁移计划
- 提供培训和文档
- 建立新旧系统的使用规范

### 4. 监控和验证
- 定期运行兼容性测试
- 监控系统性能变化
- 收集用户反馈并及时调整

## 总结

Pipeline 系统的设计原则是**向后兼容**和**渐进式增强**。您可以：

- **立即受益**：现有命令获得新功能（如标签过滤）
- **按需采用**：根据实际需求逐步使用 Pipeline 功能
- **平滑过渡**：新旧系统可以并存，无需强制迁移

记住，迁移是一个过程，不是一个事件。根据您的具体需求和时间安排，选择合适的迁移路径和节奏。