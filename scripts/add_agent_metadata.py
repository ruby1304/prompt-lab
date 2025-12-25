#!/usr/bin/env python3
"""
为所有 Agent 添加分类元数据

使用方法：
    python scripts/add_agent_metadata.py --dry-run  # 预览更改
    python scripts/add_agent_metadata.py            # 实际执行
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any
import yaml

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Agent 分类配置
AGENT_METADATA = {
    # 生产 Agent
    "mem_l1_summarizer": {
        "category": "production",
        "environment": "production",
        "owner": "memory_team",
        "version": "1.0.0",
        "tags": ["memory", "conversation", "summarization"],
        "deprecated": False,
    },
    "mem0_l1_summarizer": {
        "category": "production",
        "environment": "production",
        "owner": "memory_team",
        "version": "1.0.0",
        "tags": ["memory", "conversation", "summarization"],
        "deprecated": False,  # 如果是旧版本，改为 True
        "notes": "需要确认：是否与 mem_l1_summarizer 重复？",
    },
    "usr_profile": {
        "category": "production",
        "environment": "production",
        "owner": "profile_team",
        "version": "1.0.0",
        "tags": ["profile", "user_analysis"],
        "deprecated": False,
    },
    
    # 示例 Agent
    "text_cleaner": {
        "category": "example",
        "environment": "demo",
        "owner": "platform_team",
        "version": "1.0.0",
        "tags": ["demo", "text_processing", "pipeline"],
        "deprecated": False,
        "example_usage": "用于 document_summary Pipeline 演示",
    },
    "document_summarizer": {
        "category": "example",
        "environment": "demo",
        "owner": "platform_team",
        "version": "1.0.0",
        "tags": ["demo", "summarization", "pipeline"],
        "deprecated": False,
        "example_usage": "用于 document_summary Pipeline 演示",
    },
    "intent_classifier": {
        "category": "example",
        "environment": "demo",
        "owner": "platform_team",
        "version": "1.0.0",
        "tags": ["demo", "classification", "customer_service"],
        "deprecated": False,
        "example_usage": "用于 customer_service_flow Pipeline 演示",
    },
    "entity_extractor": {
        "category": "example",
        "environment": "demo",
        "owner": "platform_team",
        "version": "1.0.0",
        "tags": ["demo", "extraction", "customer_service"],
        "deprecated": False,
        "example_usage": "用于 customer_service_flow Pipeline 演示",
    },
    "response_generator": {
        "category": "example",
        "environment": "demo",
        "owner": "platform_team",
        "version": "1.0.0",
        "tags": ["demo", "generation", "customer_service"],
        "deprecated": False,
        "example_usage": "用于 customer_service_flow Pipeline 演示",
    },
    
    # 测试 Agent
    "big_thing": {
        "category": "test",
        "environment": "test",
        "owner": "platform_team",
        "version": "1.0.0",
        "tags": ["test", "template_parser"],
        "deprecated": False,
        "test_purpose": "测试 Agent Template Parser 功能",
    },
    
    # 系统 Agent
    "judge_default": {
        "category": "system",
        "environment": "production",
        "owner": "platform_team",
        "version": "2.0.0",
        "tags": ["system", "evaluation", "judge"],
        "deprecated": False,
    },
}


def load_yaml_preserving_order(file_path: Path) -> Dict[str, Any]:
    """加载 YAML 文件，保持顺序和注释"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


def save_yaml_preserving_format(file_path: Path, data: Dict[str, Any]):
    """保存 YAML 文件，保持格式"""
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, 
                  default_flow_style=False, 
                  allow_unicode=True,
                  sort_keys=False,
                  indent=2)


def add_metadata_to_agent(agent_id: str, agent_config: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
    """为 Agent 配置添加元数据"""
    # 创建新的配置，保持原有字段顺序
    new_config = {}
    
    # 1. 基本字段（保持原有顺序）
    for key in ['id', 'name', 'type']:
        if key in agent_config:
            new_config[key] = agent_config[key]
    
    # 2. 添加新的元数据字段
    new_config['category'] = metadata['category']
    new_config['environment'] = metadata['environment']
    
    # 3. 可选元数据
    if 'owner' in metadata:
        new_config['owner'] = metadata['owner']
    if 'version' in metadata:
        new_config['version'] = metadata['version']
    if 'tags' in metadata:
        new_config['tags'] = metadata['tags']
    if 'deprecated' in metadata:
        new_config['deprecated'] = metadata['deprecated']
    
    # 4. 添加特殊说明
    if 'notes' in metadata:
        new_config['notes'] = metadata['notes']
    if 'example_usage' in metadata:
        new_config['example_usage'] = metadata['example_usage']
    if 'test_purpose' in metadata:
        new_config['test_purpose'] = metadata['test_purpose']
    
    # 5. 更新 description（添加分类标签）
    if 'description' in agent_config:
        category_label = {
            'production': '【生产环境】',
            'example': '【示例 Agent】',
            'test': '【测试 Agent】',
            'system': '【系统 Agent】',
        }.get(metadata['category'], '')
        
        original_desc = agent_config['description']
        if not original_desc.startswith(category_label):
            new_config['description'] = f"{category_label}{original_desc}"
        else:
            new_config['description'] = original_desc
    
    # 6. 保留其他所有字段
    for key, value in agent_config.items():
        if key not in new_config:
            new_config[key] = value
    
    return new_config


def update_agent_config(agent_dir: Path, metadata: Dict[str, Any], dry_run: bool = False) -> bool:
    """更新单个 Agent 的配置"""
    agent_id = agent_dir.name
    config_file = agent_dir / "agent.yaml"
    
    if not config_file.exists():
        print(f"⚠️  跳过 {agent_id}: 配置文件不存在")
        return False
    
    try:
        # 加载现有配置
        config = load_yaml_preserving_order(config_file)
        
        # 检查是否已有元数据
        if 'category' in config and 'environment' in config:
            print(f"ℹ️  跳过 {agent_id}: 已有元数据")
            return False
        
        # 添加元数据
        new_config = add_metadata_to_agent(agent_id, config, metadata)
        
        if dry_run:
            print(f"\n{'='*60}")
            print(f"📝 预览 {agent_id} 的更改:")
            print(f"{'='*60}")
            print(f"Category: {metadata['category']}")
            print(f"Environment: {metadata['environment']}")
            print(f"Tags: {metadata.get('tags', [])}")
            if 'notes' in metadata:
                print(f"Notes: {metadata['notes']}")
            print()
        else:
            # 保存更新后的配置
            save_yaml_preserving_format(config_file, new_config)
            print(f"✅ 更新 {agent_id}")
        
        return True
    
    except Exception as e:
        print(f"❌ 更新 {agent_id} 失败: {e}")
        return False


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="为所有 Agent 添加分类元数据")
    parser.add_argument("--dry-run", action="store_true", help="预览更改，不实际修改文件")
    parser.add_argument("--agent", type=str, help="只更新指定的 Agent")
    args = parser.parse_args()
    
    agents_dir = project_root / "agents"
    
    if not agents_dir.exists():
        print(f"❌ agents 目录不存在: {agents_dir}")
        return 1
    
    print(f"{'='*60}")
    print(f"Agent 元数据更新工具")
    print(f"{'='*60}")
    print(f"模式: {'预览模式（不会修改文件）' if args.dry_run else '执行模式（会修改文件）'}")
    print(f"{'='*60}\n")
    
    updated_count = 0
    skipped_count = 0
    failed_count = 0
    
    # 遍历所有 Agent 目录
    for agent_dir in sorted(agents_dir.iterdir()):
        if not agent_dir.is_dir():
            continue
        
        agent_id = agent_dir.name
        
        # 跳过模板目录
        if agent_id.startswith("_"):
            continue
        
        # 如果指定了特定 Agent，只处理该 Agent
        if args.agent and agent_id != args.agent:
            continue
        
        # 获取元数据配置
        if agent_id not in AGENT_METADATA:
            print(f"⚠️  跳过 {agent_id}: 未配置元数据")
            skipped_count += 1
            continue
        
        metadata = AGENT_METADATA[agent_id]
        
        # 更新配置
        result = update_agent_config(agent_dir, metadata, dry_run=args.dry_run)
        
        if result:
            updated_count += 1
        else:
            skipped_count += 1
    
    # 打印总结
    print(f"\n{'='*60}")
    print(f"总结:")
    print(f"{'='*60}")
    print(f"✅ 更新: {updated_count}")
    print(f"ℹ️  跳过: {skipped_count}")
    print(f"❌ 失败: {failed_count}")
    
    if args.dry_run:
        print(f"\n💡 这是预览模式，没有实际修改文件")
        print(f"   要实际执行，请运行: python {__file__}")
    else:
        print(f"\n✅ 所有更改已保存")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
