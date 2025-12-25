#!/usr/bin/env python3
"""
按分类列出 Agent

使用方法：
    python scripts/list_agents_by_category.py                    # 列出所有 Agent
    python scripts/list_agents_by_category.py --category production  # 只列出生产 Agent
    python scripts/list_agents_by_category.py --category example     # 只列出示例 Agent
    python scripts/list_agents_by_category.py --show-details         # 显示详细信息
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml
from collections import defaultdict

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_agent_config(agent_dir: Path) -> Optional[Dict[str, Any]]:
    """加载 Agent 配置"""
    config_file = agent_dir / "agent.yaml"
    
    if not config_file.exists():
        return None
    
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"⚠️  加载 {agent_dir.name} 配置失败: {e}", file=sys.stderr)
        return None


def get_agent_category(config: Dict[str, Any]) -> str:
    """获取 Agent 分类"""
    return config.get('category', 'uncategorized')


def get_agent_environment(config: Dict[str, Any]) -> str:
    """获取 Agent 环境"""
    return config.get('environment', 'unknown')


def format_agent_info(agent_id: str, config: Dict[str, Any], show_details: bool = False) -> str:
    """格式化 Agent 信息"""
    category = get_agent_category(config)
    environment = get_agent_environment(config)
    agent_type = config.get('type', 'unknown')
    name = config.get('name', agent_id)
    
    # 分类图标
    category_icon = {
        'production': '🚀',
        'example': '📋',
        'test': '🧪',
        'system': '⚙️',
        'uncategorized': '❓',
    }.get(category, '❓')
    
    # 环境标签
    env_label = {
        'production': '[PROD]',
        'staging': '[STAG]',
        'demo': '[DEMO]',
        'test': '[TEST]',
        'unknown': '[????]',
    }.get(environment, '[????]')
    
    # 基本信息
    info = f"{category_icon} {agent_id:30s} {env_label:8s} {name}"
    
    if show_details:
        # 详细信息
        details = []
        
        if 'version' in config:
            details.append(f"v{config['version']}")
        
        if 'owner' in config:
            details.append(f"Owner: {config['owner']}")
        
        if 'tags' in config:
            tags = ', '.join(config['tags'])
            details.append(f"Tags: {tags}")
        
        if 'deprecated' in config and config['deprecated']:
            details.append("⚠️  DEPRECATED")
        
        if 'flows' in config:
            flow_count = len(config['flows'])
            details.append(f"Flows: {flow_count}")
        
        if details:
            info += f"\n    {' | '.join(details)}"
        
        # 描述
        if 'description' in config:
            desc = config['description'].strip()
            # 只显示第一行
            first_line = desc.split('\n')[0]
            if len(first_line) > 80:
                first_line = first_line[:77] + "..."
            info += f"\n    📝 {first_line}"
        
        # 特殊说明
        if 'notes' in config:
            info += f"\n    💡 {config['notes']}"
        
        if 'example_usage' in config:
            info += f"\n    📖 {config['example_usage']}"
        
        if 'test_purpose' in config:
            info += f"\n    🎯 {config['test_purpose']}"
    
    return info


def list_agents(
    agents_dir: Path,
    category_filter: Optional[str] = None,
    environment_filter: Optional[str] = None,
    show_details: bool = False,
    group_by_category: bool = True,
) -> None:
    """列出 Agent"""
    
    # 收集所有 Agent
    agents_by_category = defaultdict(list)
    
    for agent_dir in sorted(agents_dir.iterdir()):
        if not agent_dir.is_dir():
            continue
        
        agent_id = agent_dir.name
        
        # 跳过模板目录
        if agent_id.startswith("_"):
            continue
        
        # 加载配置
        config = load_agent_config(agent_dir)
        if not config:
            continue
        
        # 应用过滤器
        category = get_agent_category(config)
        environment = get_agent_environment(config)
        
        if category_filter and category != category_filter:
            continue
        
        if environment_filter and environment != environment_filter:
            continue
        
        # 添加到分类列表
        agents_by_category[category].append((agent_id, config))
    
    # 打印结果
    if not agents_by_category:
        print("没有找到匹配的 Agent")
        return
    
    # 分类顺序
    category_order = ['production', 'system', 'example', 'test', 'uncategorized']
    
    # 分类标题
    category_titles = {
        'production': '生产环境 Agent',
        'system': '系统 Agent',
        'example': '示例 Agent',
        'test': '测试 Agent',
        'uncategorized': '未分类 Agent',
    }
    
    total_count = 0
    
    if group_by_category:
        # 按分类分组显示
        for category in category_order:
            if category not in agents_by_category:
                continue
            
            agents = agents_by_category[category]
            count = len(agents)
            total_count += count
            
            print(f"\n{'='*80}")
            print(f"{category_titles.get(category, category)} ({count})")
            print(f"{'='*80}")
            
            for agent_id, config in agents:
                print(format_agent_info(agent_id, config, show_details))
                if show_details:
                    print()  # 详细模式下添加空行
    else:
        # 不分组，直接列出
        print(f"\n{'='*80}")
        print(f"所有 Agent")
        print(f"{'='*80}")
        
        for category in category_order:
            if category not in agents_by_category:
                continue
            
            for agent_id, config in agents_by_category[category]:
                print(format_agent_info(agent_id, config, show_details))
                if show_details:
                    print()
                total_count += 1
    
    # 打印总结
    print(f"\n{'='*80}")
    print(f"总计: {total_count} 个 Agent")
    
    # 按分类统计
    if len(agents_by_category) > 1:
        print(f"\n分类统计:")
        for category in category_order:
            if category in agents_by_category:
                count = len(agents_by_category[category])
                icon = {
                    'production': '🚀',
                    'example': '📋',
                    'test': '🧪',
                    'system': '⚙️',
                    'uncategorized': '❓',
                }.get(category, '❓')
                print(f"  {icon} {category_titles.get(category, category):20s}: {count}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="按分类列出 Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有 Agent
  python scripts/list_agents_by_category.py
  
  # 只列出生产 Agent
  python scripts/list_agents_by_category.py --category production
  
  # 只列出示例 Agent
  python scripts/list_agents_by_category.py --category example
  
  # 显示详细信息
  python scripts/list_agents_by_category.py --show-details
  
  # 列出生产环境的 Agent（详细信息）
  python scripts/list_agents_by_category.py --environment production --show-details
        """
    )
    
    parser.add_argument(
        "--category",
        type=str,
        choices=['production', 'example', 'test', 'system', 'uncategorized'],
        help="按分类过滤"
    )
    
    parser.add_argument(
        "--environment",
        type=str,
        choices=['production', 'staging', 'demo', 'test'],
        help="按环境过滤"
    )
    
    parser.add_argument(
        "--show-details",
        action="store_true",
        help="显示详细信息"
    )
    
    parser.add_argument(
        "--no-group",
        action="store_true",
        help="不按分类分组"
    )
    
    args = parser.parse_args()
    
    agents_dir = project_root / "agents"
    
    if not agents_dir.exists():
        print(f"❌ agents 目录不存在: {agents_dir}")
        return 1
    
    list_agents(
        agents_dir=agents_dir,
        category_filter=args.category,
        environment_filter=args.environment,
        show_details=args.show_details,
        group_by_category=not args.no_group,
    )
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
