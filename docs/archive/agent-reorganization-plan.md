# Agent 重组方案 - 物理分离示例 Agent

## 🎯 目标

将示例 Agent 从 `agents/` 目录移动到 `examples/agents/` 目录，使目录结构更清晰。

---

## 📁 新的目录结构

```
项目根目录/
├── agents/                          # 生产和系统 Agent
│   ├── _template/                   # Agent 模板
│   ├── judge_default/               # 系统 Agent
│   ├── mem_l1_summarizer/           # 生产 Agent
│   ├── mem0_l1_summarizer/          # 生产 Agent
│   └── usr_profile/                 # 生产 Agent
│
├── examples/
│   ├── agents/                      # 示例 Agent（新增）
│   │   ├── text_cleaner/
│   │   ├── document_summarizer/
│   │   ├── intent_classifier/
│   │   ├── entity_extractor/
│   │   └── response_generator/
│   │
│   ├── pipelines/                   # 示例 Pipeline（新增）
│   │   ├── document_summary.yaml
│   │   └── customer_service_flow.yaml
│   │
│   └── README.md                    # 示例说明文档
│
├── tests/
│   └── agents/                      # 测试 Agent（新增）
│       └── big_thing/
│
└── pipelines/                       # 生产 Pipeline（保留为空或删除）
```

---

## ✅ 优点

1. **目录结构清晰**
   - `agents/` 只包含生产和系统 Agent
   - `examples/agents/` 明确标识为示例
   - `tests/agents/` 明确标识为测试

2. **避免误操作**
   - 不会误修改或删除示例 Agent
   - 不会误将示例 Agent 用于生产评估

3. **符合项目惯例**
   - 项目已有 `examples/` 目录
   - 与现有结构保持一致

4. **便于维护**
   - 示例 Agent 和示例 Pipeline 放在一起
   - 可以单独管理示例的版本和更新

---

## 🔧 实施步骤

### 步骤 1: 创建新目录结构

```bash
# 创建示例 Agent 目录
mkdir -p examples/agents

# 创建示例 Pipeline 目录
mkdir -p examples/pipelines

# 创建测试 Agent 目录
mkdir -p tests/agents
```

### 步骤 2: 移动示例 Agent

```bash
# 移动示例 Agent
mv agents/text_cleaner examples/agents/
mv agents/document_summarizer examples/agents/
mv agents/intent_classifier examples/agents/
mv agents/entity_extractor examples/agents/
mv agents/response_generator examples/agents/
```

### 步骤 3: 移动示例 Pipeline

```bash
# 移动示例 Pipeline
mv pipelines/document_summary.yaml examples/pipelines/
mv pipelines/customer_service_flow.yaml examples/pipelines/
```

### 步骤 4: 移动测试 Agent

```bash
# 移动测试 Agent
mv agents/big_thing tests/agents/
```

### 步骤 5: 更新 Pipeline 配置

需要更新 Pipeline 配置中的 Agent 引用路径。

---

## 📝 需要修改的代码

### 1. Agent 加载逻辑

需要修改 `src/agent_registry.py` 中的 Agent 加载逻辑，支持从多个目录加载：

```python
# src/agent_registry.py

AGENT_DIRS = [
    Path("agents"),           # 生产和系统 Agent
    Path("examples/agents"),  # 示例 Agent
    Path("tests/agents"),     # 测试 Agent
]

def load_agent(agent_id: str) -> AgentConfig:
    """从多个目录加载 Agent"""
    for agent_dir in AGENT_DIRS:
        agent_path = agent_dir / agent_id / "agent.yaml"
        if agent_path.exists():
            return _load_agent_from_path(agent_path)
    
    raise ValueError(f"Agent not found: {agent_id}")

def list_agents(category: Optional[str] = None) -> List[str]:
    """列出所有 Agent"""
    agents = []
    for agent_dir in AGENT_DIRS:
        if agent_dir.exists():
            for agent_path in agent_dir.iterdir():
                if agent_path.is_dir() and not agent_path.name.startswith("_"):
                    agents.append(agent_path.name)
    return sorted(set(agents))
```

### 2. Pipeline 配置

Pipeline 配置不需要修改，因为 Agent ID 保持不变，只是存储位置改变了。

### 3. 测试代码

需要更新测试代码中的 Agent 路径引用。

---

## 🚀 自动化脚本

我会创建一个自动化脚本来完成所有移动和更新操作。

---

## ⚠️ 注意事项

### 1. 向后兼容性

为了保持向后兼容，Agent 加载逻辑会按以下顺序查找：
1. `agents/` - 优先级最高
2. `examples/agents/` - 其次
3. `tests/agents/` - 最后

这样即使有人还在旧位置创建 Agent，也能正常工作。

### 2. 数据目录

Agent 的运行数据仍然存储在 `data/agents/{agent_id}/` 下，不受影响。

### 3. Git 历史

使用 `git mv` 而不是 `mv` 来移动文件，保留 Git 历史记录。

---

## 📋 验证清单

移动完成后，需要验证：

- [ ] 所有示例 Agent 都在 `examples/agents/` 下
- [ ] 所有示例 Pipeline 都在 `examples/pipelines/` 下
- [ ] 测试 Agent 在 `tests/agents/` 下
- [ ] `agents/` 目录只包含生产和系统 Agent
- [ ] 示例 Pipeline 可以正常运行
- [ ] 所有测试通过
- [ ] 文档已更新

---

## 🎯 最终效果

### agents/ 目录（生产环境）
```
agents/
├── _template/              # 模板
├── judge_default/          # 系统 Agent
├── mem_l1_summarizer/      # 生产 Agent
├── mem0_l1_summarizer/     # 生产 Agent
└── usr_profile/            # 生产 Agent
```

### examples/agents/ 目录（示例）
```
examples/agents/
├── text_cleaner/
├── document_summarizer/
├── intent_classifier/
├── entity_extractor/
└── response_generator/
```

### tests/agents/ 目录（测试）
```
tests/agents/
└── big_thing/
```

---

**下一步**: 运行自动化脚本完成重组
