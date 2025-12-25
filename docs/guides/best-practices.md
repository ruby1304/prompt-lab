# Prompt Lab 最佳实践指南

本指南总结了使用 Prompt Lab 进行 Agent 开发和 Pipeline 设计的最佳实践。

## Agent 开发最佳实践

### 1. 配置管理

#### 使用语义化版本号
```yaml
# agent.yaml
version: "1.2.0"  # 主版本.次版本.修订版本
```

- **主版本**：不兼容的 API 变更
- **次版本**：向后兼容的功能新增
- **修订版本**：向后兼容的问题修复

#### 明确定义业务目标
```yaml
business_goal: "将用户对话总结为结构化的记忆条目，便于后续检索"
expectations:
  must_have:
    - "保留关键信息"
    - "输出格式符合规范"
  nice_to_have:
    - "语言流畅自然"
```

### 2. Flow 设计

#### 单一职责原则
每个 Flow 应该只做一件事：
```yaml
flows:
  - name: "extract_entities"      # 只提取实体
  - name: "classify_intent"       # 只分类意图
  - name: "generate_response"     # 只生成回复
```

#### 使用清晰的命名
```yaml
# ✅ 好的命名
flows:
  - name: "summarize_v1"
  - name: "summarize_detailed_v2"
  - name: "summarize_concise_v1"

# ❌ 避免的命名
flows:
  - name: "flow1"
  - name: "test"
  - name: "new_version"
```

#### 提示词模板化
```yaml
# prompts/summarize_v1.yaml
system_prompt: |
  你是一个专业的对话总结助手。
  
  ## 任务
  将用户提供的对话内容总结为简洁的要点。
  
  ## 输出格式
  - 使用 JSON 格式输出
  - 包含 summary 和 key_points 字段

user_template: |
  请总结以下对话：
  
  ${conversation}
```

### 3. 测试集设计

#### 覆盖多种场景
```jsonl
{"id": "happy_path_1", "tags": ["happy_path", "basic"], "input": "正常输入"}
{"id": "edge_case_1", "tags": ["edge_case"], "input": "边界情况"}
{"id": "error_case_1", "tags": ["error_handling"], "input": "异常输入"}
{"id": "regression_1", "tags": ["regression", "critical"], "input": "回归测试用例"}
```

#### 使用有意义的标签
- `happy_path`: 正常流程测试
- `edge_case`: 边界情况测试
- `error_handling`: 错误处理测试
- `regression`: 回归测试
- `performance`: 性能测试
- `critical`: 关键功能测试

---

## Pipeline 设计最佳实践

### 1. 步骤设计

#### 保持步骤独立性
每个步骤应该可以独立测试和替换：
```yaml
steps:
  - id: "clean"
    agent: "text_cleaner"
    flow: "clean_v1"
    # 输入输出明确定义
    input_mapping:
      text: "raw_input"
    output_key: "cleaned_text"
```

#### 合理使用依赖
```yaml
steps:
  - id: "step_a"
    output_key: "result_a"
    
  - id: "step_b"
    depends_on: ["step_a"]  # 显式声明依赖
    input_mapping:
      input: "result_a"
```

### 2. 并发优化

#### 识别可并行步骤
```yaml
steps:
  # 这两个步骤可以并行执行
  - id: "extract_entities"
    concurrent_group: "parallel_1"
    
  - id: "classify_intent"
    concurrent_group: "parallel_1"
    
  # 这个步骤依赖前两个
  - id: "generate_response"
    depends_on: ["extract_entities", "classify_intent"]
```

#### 控制并发数
```yaml
# 根据资源限制设置合理的并发数
config:
  max_workers: 4  # 不要设置过高
```

### 3. 错误处理

#### 区分必需和可选步骤
```yaml
steps:
  - id: "critical_step"
    required: true   # 失败则整个 Pipeline 失败
    
  - id: "optional_step"
    required: false  # 失败不影响后续步骤
```

#### 设置合理的超时
```yaml
steps:
  - id: "llm_step"
    timeout: 60  # LLM 调用可能需要较长时间
    
  - id: "code_step"
    type: "code_node"
    timeout: 10  # 代码执行应该很快
```

### 4. 变体管理

#### 使用有意义的变体名称
```yaml
baseline:
  name: "production_v1"
  description: "当前生产环境版本"

variants:
  improved_prompt:
    description: "优化后的提示词版本"
    overrides:
      step1:
        flow: "improved_v1"
        
  faster_model:
    description: "使用更快的模型"
    overrides:
      step1:
        model: "doubao-lite"
```

---

## Code Node 最佳实践

### 1. 代码组织

#### 使用外部文件存储复杂逻辑
```yaml
# 简单逻辑可以内联
- id: "simple_transform"
  type: "code_node"
  language: "python"
  code: |
    def process(inputs):
        return {"result": inputs["text"].upper()}

# 复杂逻辑使用外部文件
- id: "complex_transform"
  type: "code_node"
  code_file: "scripts/complex_transform.py"
```

#### 保持函数纯净
```python
# ✅ 好的实践
def process(inputs):
    text = inputs.get("text", "")
    return {"processed": text.strip().lower()}

# ❌ 避免的实践
def process(inputs):
    import os
    os.system("rm -rf /")  # 危险操作
    return {"result": "done"}
```

### 2. 错误处理

```python
def process(inputs):
    try:
        text = inputs.get("text")
        if not text:
            return {"error": "Missing required input: text"}
        
        result = do_something(text)
        return {"result": result}
        
    except Exception as e:
        return {"error": str(e)}
```

---

## 批量处理最佳实践

### 1. 选择合适的聚合策略

```yaml
# 文本拼接
- id: "concat_results"
  type: "batch_aggregator"
  aggregation_strategy: "concat"
  separator: "\n---\n"

# 统计分析
- id: "analyze_scores"
  type: "batch_aggregator"
  aggregation_strategy: "stats"
  fields: ["score", "latency"]

# 自定义聚合
- id: "custom_aggregate"
  type: "batch_aggregator"
  aggregation_strategy: "custom"
  code: |
    def aggregate(items):
        return {"total": len(items), "avg": sum(i["score"] for i in items) / len(items)}
```

### 2. 控制批量大小

```yaml
steps:
  - id: "batch_process"
    batch_mode: true
    batch_size: 10      # 每批处理 10 个
    concurrent: true    # 批内并发
    max_workers: 4      # 最大并发数
```

---

## 评估最佳实践

### 1. 建立基线

```bash
# 在稳定版本上建立基线
python -m src baseline save --agent my_agent --flow stable_v1 --name production

# 定期更新基线
python -m src baseline save --agent my_agent --flow stable_v2 --name production --force
```

### 2. 回归测试

```bash
# 在每次发布前运行回归测试
python -m src regression run --agent my_agent --flow new_version --baseline production

# 使用标签过滤关键测试
python -m src eval --agent my_agent --flows new_version --include-tags critical,regression
```

### 3. 使用 Judge 评估

```bash
# 对主观质量使用 LLM Judge
python -m src eval --agent my_agent --flows v1,v2 --judge

# 结合规则评估和 Judge 评估
python -m src eval --agent my_agent --flows v1 --rules --judge
```

---

## API 使用最佳实践

### 1. 异步执行长任务

```python
import requests
import time

# 启动异步执行
response = requests.post(
    "http://localhost:8000/api/v1/executions",
    json={
        "type": "pipeline",
        "target_id": "my_pipeline",
        "inputs": {"text": "..."}
    }
)
execution_id = response.json()["execution_id"]

# 轮询状态
while True:
    status = requests.get(f"http://localhost:8000/api/v1/executions/{execution_id}").json()
    if status["status"] in ["completed", "failed"]:
        break
    time.sleep(1)
```

### 2. 错误处理

```python
response = requests.post(url, json=data)

if response.status_code == 200:
    result = response.json()
elif response.status_code == 422:
    errors = response.json()["details"]["validation_errors"]
    print(f"Validation errors: {errors}")
elif response.status_code == 500:
    error = response.json()["message"]
    print(f"Server error: {error}")
```

---

## 性能优化

### 1. 减少 LLM 调用

- 合并可以一次完成的任务
- 使用缓存避免重复调用
- 选择合适的模型（速度 vs 质量）

### 2. 优化 Pipeline 结构

- 最大化并行执行
- 减少不必要的步骤
- 使用 Code Node 处理简单逻辑

### 3. 批量处理优化

- 选择合适的批量大小
- 控制并发数避免过载
- 使用流式处理大数据集

---

## 总结

1. **Agent 开发**：单一职责、清晰命名、完善测试
2. **Pipeline 设计**：步骤独立、合理并发、优雅错误处理
3. **Code Node**：代码纯净、错误处理、外部文件管理
4. **批量处理**：合适策略、控制规模、监控性能
5. **评估测试**：建立基线、回归测试、多维评估
6. **API 使用**：异步执行、错误处理、性能监控

遵循这些最佳实践，可以帮助您构建更可靠、可维护的 AI Agent 系统。
