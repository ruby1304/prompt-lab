#!/usr/bin/env python3
"""
重组 Agent 目录结构

将示例 Agent 移动到 examples/agents/
将测试 Agent 移动到 tests/agents/
将示例 Pipeline 移动到 examples/pipelines/

使用方法：
    python scripts/reorganize_agents.py --dry-run  # 预览更改
    python scripts/reorganize_agents.py            # 实际执行
"""

import os
import sys
import shutil
from pathlib import Path
from typing import List, Tuple

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# 定义移动规则
AGENT_MOVES = {
    # 示例 Agent -> examples/agents/
    "text_cleaner": "examples/agents",
    "document_summarizer": "examples/agents",
    "intent_classifier": "examples/agents",
    "entity_extractor": "examples/agents",
    "response_generator": "examples/agents",
    
    # 测试 Agent -> tests/agents/
    "big_thing": "tests/agents",
}

PIPELINE_MOVES = {
    # 示例 Pipeline -> examples/pipelines/
    "document_summary.yaml": "examples/pipelines",
    "customer_service_flow.yaml": "examples/pipelines",
}


def move_directory(src: Path, dst: Path, dry_run: bool = False) -> bool:
    """移动目录"""
    if not src.exists():
        print(f"⚠️  源目录不存在: {src}")
        return False
    
    if dst.exists():
        print(f"⚠️  目标目录已存在: {dst}")
        return False
    
    if dry_run:
        print(f"📦 将移动: {src} -> {dst}")
        return True
    else:
        try:
            # 确保目标父目录存在
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            # 移动目录
            shutil.move(str(src), str(dst))
            print(f"✅ 已移动: {src.name} -> {dst.parent.name}/{dst.name}")
            return True
        except Exception as e:
            print(f"❌ 移动失败: {src} -> {dst}: {e}")
            return False


def move_file(src: Path, dst: Path, dry_run: bool = False) -> bool:
    """移动文件"""
    if not src.exists():
        print(f"⚠️  源文件不存在: {src}")
        return False
    
    if dst.exists():
        print(f"⚠️  目标文件已存在: {dst}")
        return False
    
    if dry_run:
        print(f"📄 将移动: {src} -> {dst}")
        return True
    else:
        try:
            # 确保目标目录存在
            dst.parent.mkdir(parents=True, exist_ok=True)
            
            # 移动文件
            shutil.move(str(src), str(dst))
            print(f"✅ 已移动: {src.name} -> {dst.parent.name}/{dst.name}")
            return True
        except Exception as e:
            print(f"❌ 移动失败: {src} -> {dst}: {e}")
            return False


def create_examples_readme(dry_run: bool = False) -> bool:
    """创建 examples/README.md"""
    readme_path = project_root / "examples" / "README.md"
    
    content = """# Prompt Lab 示例

本目录包含 Prompt Lab 的示例 Agent 和 Pipeline，用于演示和学习。

## 📁 目录结构

```
examples/
├── agents/                      # 示例 Agent
│   ├── text_cleaner/           # 文本清洗示例
│   ├── document_summarizer/    # 文档摘要示例
│   ├── intent_classifier/      # 意图识别示例
│   ├── entity_extractor/       # 实体提取示例
│   └── response_generator/     # 回复生成示例
│
├── pipelines/                   # 示例 Pipeline
│   ├── document_summary.yaml   # 文档处理 Pipeline
│   └── customer_service_flow.yaml  # 客服流程 Pipeline
│
└── README.md                    # 本文件
```

## 🎯 示例说明

### 1. 文档处理 Pipeline

**Pipeline**: `pipelines/document_summary.yaml`

**流程**:
```
原始文档 → text_cleaner (清洗) → document_summarizer (摘要) → 最终摘要
```

**运行方法**:
```bash
python -m src eval --pipeline document_summary --variants baseline --limit 3
```

### 2. 客服流程 Pipeline

**Pipeline**: `pipelines/customer_service_flow.yaml`

**流程**:
```
用户消息 → intent_classifier (意图识别) 
         → entity_extractor (实体提取)
         → response_generator (生成回复)
         → 客服回复
```

**运行方法**:
```bash
python -m src eval --pipeline customer_service_flow --variants baseline --limit 3
```

## 📚 学习资源

### Agent 开发
- 查看示例 Agent 的配置文件 (`agent.yaml`)
- 查看提示词配置 (`prompts/*.yaml`)
- 查看测试集格式 (`testsets/*.jsonl`)

### Pipeline 开发
- 查看 Pipeline 配置语法
- 学习步骤编排和数据流
- 了解变体管理

## 🔧 自定义示例

你可以基于这些示例创建自己的 Agent 和 Pipeline：

```bash
# 复制示例 Agent
cp -r examples/agents/text_cleaner agents/my_agent

# 修改配置
vim agents/my_agent/agent.yaml
vim agents/my_agent/prompts/my_flow.yaml

# 运行评估
python -m src eval --agent my_agent --flows my_flow
```

## ⚠️ 注意事项

1. **这些是示例，不是生产 Agent**
   - 示例 Agent 的配置可能不完整
   - 测试集数据是模拟的
   - 不要用于生产环境

2. **修改示例不会影响生产**
   - 示例 Agent 与生产 Agent 完全分离
   - 可以自由修改和实验

3. **保持示例简单**
   - 示例应该易于理解
   - 专注于演示核心功能
   - 避免过度复杂化

## 📖 相关文档

- [Agent 管理指南](../AGENT_MANAGEMENT_GUIDE.md)
- [Pipeline 配置指南](../docs/reference/pipeline-guide.md)
- [使用指南](../docs/USAGE_GUIDE.md)

---

**最后更新**: 2025-12-15
"""
    
    if dry_run:
        print(f"📝 将创建: {readme_path}")
        return True
    else:
        try:
            readme_path.parent.mkdir(parents=True, exist_ok=True)
            readme_path.write_text(content, encoding='utf-8')
            print(f"✅ 已创建: {readme_path}")
            return True
        except Exception as e:
            print(f"❌ 创建失败: {readme_path}: {e}")
            return False


def update_agent_registry(dry_run: bool = False) -> bool:
    """更新 agent_registry.py 以支持多目录加载"""
    registry_path = project_root / "src" / "agent_registry.py"
    
    if not registry_path.exists():
        print(f"⚠️  agent_registry.py 不存在: {registry_path}")
        return False
    
    # 读取现有内容
    content = registry_path.read_text(encoding='utf-8')
    
    # 检查是否已经更新
    if "AGENT_DIRS" in content:
        print(f"ℹ️  agent_registry.py 已经支持多目录加载")
        return True
    
    # 准备新的代码
    new_code = '''
# Agent 目录列表（按优先级排序）
AGENT_DIRS = [
    Path("agents"),           # 生产和系统 Agent（优先级最高）
    Path("examples/agents"),  # 示例 Agent
    Path("tests/agents"),     # 测试 Agent
]

def _find_agent_path(agent_id: str) -> Optional[Path]:
    """在多个目录中查找 Agent"""
    for agent_dir in AGENT_DIRS:
        agent_path = agent_dir / agent_id
        if agent_path.exists() and agent_path.is_dir():
            config_file = agent_path / "agent.yaml"
            if config_file.exists():
                return agent_path
    return None
'''
    
    if dry_run:
        print(f"📝 将更新: {registry_path}")
        print(f"   添加多目录支持")
        return True
    else:
        print(f"⚠️  需要手动更新 {registry_path}")
        print(f"   请在文件开头添加以下代码：")
        print(new_code)
        return False


def generate_git_commands(moves: List[Tuple[Path, Path]]) -> List[str]:
    """生成 Git 命令"""
    commands = []
    
    for src, dst in moves:
        if src.exists():
            # 使用 git mv 保留历史
            commands.append(f"git mv {src} {dst}")
    
    return commands


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="重组 Agent 目录结构")
    parser.add_argument("--dry-run", action="store_true", help="预览更改，不实际修改")
    parser.add_argument("--use-git", action="store_true", help="使用 git mv 而不是普通 mv")
    args = parser.parse_args()
    
    print(f"{'='*80}")
    print(f"Agent 目录重组工具")
    print(f"{'='*80}")
    print(f"模式: {'预览模式（不会修改文件）' if args.dry_run else '执行模式（会修改文件）'}")
    print(f"{'='*80}\n")
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    # 1. 移动 Agent
    print(f"\n{'='*80}")
    print(f"步骤 1: 移动 Agent")
    print(f"{'='*80}\n")
    
    for agent_id, target_dir in AGENT_MOVES.items():
        src = project_root / "agents" / agent_id
        dst = project_root / target_dir / agent_id
        
        result = move_directory(src, dst, dry_run=args.dry_run)
        if result:
            success_count += 1
        else:
            if src.exists():
                failed_count += 1
            else:
                skipped_count += 1
    
    # 2. 移动 Pipeline
    print(f"\n{'='*80}")
    print(f"步骤 2: 移动 Pipeline")
    print(f"{'='*80}\n")
    
    for pipeline_file, target_dir in PIPELINE_MOVES.items():
        src = project_root / "pipelines" / pipeline_file
        dst = project_root / target_dir / pipeline_file
        
        result = move_file(src, dst, dry_run=args.dry_run)
        if result:
            success_count += 1
        else:
            if src.exists():
                failed_count += 1
            else:
                skipped_count += 1
    
    # 3. 创建 examples/README.md
    print(f"\n{'='*80}")
    print(f"步骤 3: 创建示例说明文档")
    print(f"{'='*80}\n")
    
    if create_examples_readme(dry_run=args.dry_run):
        success_count += 1
    else:
        failed_count += 1
    
    # 4. 更新 agent_registry.py
    print(f"\n{'='*80}")
    print(f"步骤 4: 更新 Agent 加载逻辑")
    print(f"{'='*80}\n")
    
    update_agent_registry(dry_run=args.dry_run)
    
    # 打印总结
    print(f"\n{'='*80}")
    print(f"总结:")
    print(f"{'='*80}")
    print(f"✅ 成功: {success_count}")
    print(f"⚠️  跳过: {skipped_count}")
    print(f"❌ 失败: {failed_count}")
    
    if args.dry_run:
        print(f"\n💡 这是预览模式，没有实际修改文件")
        print(f"   要实际执行，请运行: python {__file__}")
        
        # 生成 Git 命令
        if args.use_git:
            print(f"\n📋 Git 命令（如果使用 Git）:")
            moves = []
            for agent_id, target_dir in AGENT_MOVES.items():
                src = project_root / "agents" / agent_id
                dst = project_root / target_dir / agent_id
                if src.exists():
                    moves.append((src, dst))
            
            for pipeline_file, target_dir in PIPELINE_MOVES.items():
                src = project_root / "pipelines" / pipeline_file
                dst = project_root / target_dir / pipeline_file
                if src.exists():
                    moves.append((src, dst))
            
            for cmd in generate_git_commands(moves):
                print(f"   {cmd}")
    else:
        print(f"\n✅ 重组完成！")
        print(f"\n⚠️  重要提示:")
        print(f"   1. 需要手动更新 src/agent_registry.py 以支持多目录加载")
        print(f"   2. 运行测试确保一切正常: pytest tests/")
        print(f"   3. 更新文档中的路径引用")
        print(f"   4. 提交更改: git add . && git commit -m 'Reorganize agents'")
    
    return 0 if failed_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
