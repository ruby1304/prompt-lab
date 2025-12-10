#!/usr/bin/env python3
"""
配置迁移工具

自动转换现有配置到新格式，支持：
1. Agent 配置增强（添加 baseline_flow 等）
2. 测试集标签添加
3. Pipeline 配置生成
4. 数据目录结构迁移
"""

import os
import sys
import json
import yaml
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional
import argparse
from datetime import datetime

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

console = Console()

class ConfigMigrator:
    """配置迁移器"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.backup_dir = self.project_root / "migration_backup"
        self.migration_log = []
        
    def create_backup(self, file_path: Path) -> Path:
        """创建文件备份"""
        if not self.backup_dir.exists():
            self.backup_dir.mkdir(parents=True)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.{timestamp}.backup"
        backup_path = self.backup_dir / backup_name
        
        shutil.copy2(file_path, backup_path)
        console.print(f"[dim]已备份: {file_path} -> {backup_path}[/]")
        
        return backup_path
    
    def log_migration(self, action: str, file_path: Path, details: str = ""):
        """记录迁移操作"""
        self.migration_log.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "file": str(file_path),
            "details": details
        })
    
    def enhance_agent_config(self, agent_id: str, dry_run: bool = True) -> bool:
        """增强 Agent 配置"""
        console.print(f"\n[bold blue]增强 Agent 配置: {agent_id}[/]")
        
        agent_config_path = self.project_root / "agents" / agent_id / "agent.yaml"
        if not agent_config_path.exists():
            console.print(f"[red]错误：Agent 配置文件不存在: {agent_config_path}[/]")
            return False
        
        try:
            # 读取现有配置
            with open(agent_config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            original_config = config.copy()
            changes_made = False
            
            # 检查是否需要添加 baseline_flow
            if 'baseline_flow' not in config and 'flows' in config and config['flows']:
                # 选择第一个 flow 作为 baseline
                baseline_flow = config['flows'][0]['name']
                config['baseline_flow'] = baseline_flow
                changes_made = True
                console.print(f"  + 添加 baseline_flow: {baseline_flow}")
            
            # 检查是否需要添加 extra_testsets 字段
            if 'extra_testsets' not in config:
                # 查找额外的测试集文件
                testsets_dir = self.project_root / "agents" / agent_id / "testsets"
                if testsets_dir.exists():
                    testset_files = [f.name for f in testsets_dir.glob("*.jsonl")]
                    default_testset = config.get('default_testset', '')
                    
                    extra_testsets = [f for f in testset_files if f != default_testset]
                    if extra_testsets:
                        config['extra_testsets'] = extra_testsets
                        changes_made = True
                        console.print(f"  + 添加 extra_testsets: {extra_testsets}")
            
            # 检查评估配置
            if 'evaluation' in config:
                eval_config = config['evaluation']
                
                # 添加默认的规则配置示例（如果没有）
                if 'rules' not in eval_config:
                    eval_config['rules'] = [
                        {
                            "id": "reasonable_length",
                            "kind": "max_chars",
                            "target": "output",
                            "max_chars": 2000,
                            "action": "mark_bad"
                        }
                    ]
                    changes_made = True
                    console.print("  + 添加默认规则配置")
                
                # 确保有 case_fields 配置
                if 'case_fields' not in eval_config:
                    eval_config['case_fields'] = [
                        {
                            "key": "input",
                            "label": "输入内容",
                            "section": "primary_input",
                            "required": True
                        },
                        {
                            "key": "expected",
                            "label": "期望输出说明",
                            "section": "meta",
                            "required": False
                        }
                    ]
                    changes_made = True
                    console.print("  + 添加默认 case_fields 配置")
            
            if not changes_made:
                console.print("  [dim]无需修改[/]")
                return True
            
            if dry_run:
                console.print("  [yellow]预览模式：不会实际修改文件[/]")
                return True
            
            # 创建备份
            self.create_backup(agent_config_path)
            
            # 写入增强后的配置
            with open(agent_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            self.log_migration("enhance_agent_config", agent_config_path, f"添加了 {len([k for k in config.keys() if k not in original_config])} 个新字段")
            console.print(f"  [green]✓ 配置已更新[/]")
            
            return True
            
        except Exception as e:
            console.print(f"  [red]✗ 增强失败: {e}[/]")
            return False
    
    def add_testset_tags(self, agent_id: str, testset_name: str, dry_run: bool = True) -> bool:
        """为测试集添加标签"""
        console.print(f"\n[bold blue]为测试集添加标签: {agent_id}/{testset_name}[/]")
        
        testset_path = self.project_root / "agents" / agent_id / "testsets" / testset_name
        if not testset_path.exists():
            console.print(f"[red]错误：测试集文件不存在: {testset_path}[/]")
            return False
        
        try:
            # 读取测试集
            samples = []
            with open(testset_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        sample = json.loads(line)
                        samples.append(sample)
                    except json.JSONDecodeError as e:
                        console.print(f"[yellow]警告：第 {line_num} 行 JSON 格式错误，跳过[/]")
                        continue
            
            if not samples:
                console.print("  [yellow]测试集为空[/]")
                return True
            
            # 检查是否已有标签
            samples_with_tags = sum(1 for s in samples if 'tags' in s)
            if samples_with_tags == len(samples):
                console.print("  [dim]所有样本都已有标签[/]")
                return True
            
            # 为没有标签的样本添加默认标签
            changes_made = False
            for sample in samples:
                if 'tags' not in sample:
                    # 根据样本内容推断标签
                    tags = ["regression"]  # 默认标签
                    
                    # 根据 id 或内容特征添加更多标签
                    sample_id = sample.get('id', '')
                    if 'edge' in str(sample_id).lower() or 'error' in str(sample_id).lower():
                        tags.append("edge_case")
                    else:
                        tags.append("happy_path")
                    
                    # 根据输入长度添加标签
                    input_text = sample.get('input', '')
                    if len(input_text) < 50:
                        tags.append("short_input")
                    elif len(input_text) > 500:
                        tags.append("long_input")
                    
                    sample['tags'] = tags
                    changes_made = True
            
            if not changes_made:
                console.print("  [dim]无需修改[/]")
                return True
            
            console.print(f"  + 为 {len(samples) - samples_with_tags} 个样本添加标签")
            
            if dry_run:
                console.print("  [yellow]预览模式：不会实际修改文件[/]")
                # 显示标签统计
                all_tags = set()
                for sample in samples:
                    all_tags.update(sample.get('tags', []))
                console.print(f"  标签统计: {', '.join(sorted(all_tags))}")
                return True
            
            # 创建备份
            self.create_backup(testset_path)
            
            # 写入更新后的测试集
            with open(testset_path, 'w', encoding='utf-8') as f:
                for sample in samples:
                    f.write(json.dumps(sample, ensure_ascii=False) + '\n')
            
            self.log_migration("add_testset_tags", testset_path, f"为 {len(samples) - samples_with_tags} 个样本添加标签")
            console.print(f"  [green]✓ 标签已添加[/]")
            
            return True
            
        except Exception as e:
            console.print(f"  [red]✗ 添加标签失败: {e}[/]")
            return False
    
    def generate_pipeline_config(self, pipeline_id: str, agent_flows: List[Dict[str, str]], dry_run: bool = True) -> bool:
        """生成 Pipeline 配置"""
        console.print(f"\n[bold blue]生成 Pipeline 配置: {pipeline_id}[/]")
        
        pipeline_dir = self.project_root / "pipelines"
        pipeline_dir.mkdir(exist_ok=True)
        
        pipeline_config_path = pipeline_dir / f"{pipeline_id}.yaml"
        
        if pipeline_config_path.exists():
            console.print(f"[yellow]警告：Pipeline 配置已存在: {pipeline_config_path}[/]")
            if not dry_run and not Confirm.ask("是否覆盖现有配置？"):
                return False
        
        try:
            # 生成 Pipeline 配置
            config = {
                "id": pipeline_id,
                "name": f"自动生成的管道: {pipeline_id}",
                "description": f"基于 {len(agent_flows)} 个 Agent/Flow 组合的多步骤管道",
                "default_testset": "default.jsonl",
                "inputs": [
                    {
                        "name": "input",
                        "desc": "管道输入数据"
                    }
                ],
                "steps": [],
                "outputs": [],
                "baseline": {
                    "name": "baseline_v1",
                    "description": "自动生成的基线配置"
                },
                "variants": {
                    "variant_a": {
                        "description": "变体 A 配置",
                        "overrides": {}
                    }
                }
            }
            
            # 生成步骤配置
            for i, agent_flow in enumerate(agent_flows):
                step_id = f"step_{i+1}"
                agent_id = agent_flow["agent"]
                flow_name = agent_flow["flow"]
                
                step_config = {
                    "id": step_id,
                    "type": "agent_flow",
                    "agent": agent_id,
                    "flow": flow_name,
                    "input_mapping": {},
                    "output_key": f"output_{i+1}"
                }
                
                # 第一步从输入获取数据
                if i == 0:
                    step_config["input_mapping"]["input"] = "input"
                else:
                    # 后续步骤从前一步获取输出
                    prev_output_key = f"output_{i}"
                    step_config["input_mapping"]["input"] = prev_output_key
                
                config["steps"].append(step_config)
            
            # 生成输出配置
            if config["steps"]:
                last_output_key = config["steps"][-1]["output_key"]
                config["outputs"].append({
                    "key": last_output_key,
                    "label": "管道最终输出"
                })
            
            console.print(f"  + 生成 {len(config['steps'])} 个步骤")
            console.print(f"  + 输入: {[inp['name'] for inp in config['inputs']]}")
            console.print(f"  + 输出: {[out['key'] for out in config['outputs']]}")
            
            if dry_run:
                console.print("  [yellow]预览模式：不会实际创建文件[/]")
                console.print(f"  配置将保存至: {pipeline_config_path}")
                return True
            
            # 写入配置文件
            with open(pipeline_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, indent=2)
            
            self.log_migration("generate_pipeline_config", pipeline_config_path, f"生成了 {len(agent_flows)} 步骤的管道配置")
            console.print(f"  [green]✓ Pipeline 配置已生成: {pipeline_config_path}[/]")
            
            return True
            
        except Exception as e:
            console.print(f"  [red]✗ 生成 Pipeline 配置失败: {e}[/]")
            return False
    
    def migrate_data_structure(self, agent_id: str, dry_run: bool = True) -> bool:
        """迁移数据目录结构"""
        console.print(f"\n[bold blue]迁移数据结构: {agent_id}[/]")
        
        # 创建新的目录结构
        new_agent_dir = self.project_root / "data" / "agents" / agent_id
        
        if dry_run:
            console.print(f"  [yellow]预览模式：将创建目录结构[/]")
            console.print(f"    {new_agent_dir}/testsets/")
            console.print(f"    {new_agent_dir}/runs/")
            console.print(f"    {new_agent_dir}/evals/")
            return True
        
        try:
            # 创建目录结构
            (new_agent_dir / "testsets").mkdir(parents=True, exist_ok=True)
            (new_agent_dir / "runs").mkdir(parents=True, exist_ok=True)
            (new_agent_dir / "evals").mkdir(parents=True, exist_ok=True)
            
            # 复制测试集文件
            source_testsets = self.project_root / "agents" / agent_id / "testsets"
            if source_testsets.exists():
                for testset_file in source_testsets.glob("*.jsonl"):
                    target_file = new_agent_dir / "testsets" / testset_file.name
                    if not target_file.exists():
                        shutil.copy2(testset_file, target_file)
                        console.print(f"  + 复制测试集: {testset_file.name}")
            
            # 移动相关的运行结果文件
            data_dir = self.project_root / "data"
            moved_files = 0
            
            for pattern in [f"*{agent_id}*.csv", f"{agent_id}_*.csv"]:
                for result_file in data_dir.glob(pattern):
                    if result_file.is_file():
                        target_file = new_agent_dir / "runs" / result_file.name
                        if not target_file.exists():
                            shutil.move(result_file, target_file)
                            moved_files += 1
                            console.print(f"  + 移动结果文件: {result_file.name}")
            
            self.log_migration("migrate_data_structure", new_agent_dir, f"创建目录结构，移动了 {moved_files} 个文件")
            console.print(f"  [green]✓ 数据结构迁移完成[/]")
            
            return True
            
        except Exception as e:
            console.print(f"  [red]✗ 数据结构迁移失败: {e}[/]")
            return False
    
    def validate_migration(self, agent_id: str = None) -> bool:
        """验证迁移结果"""
        console.print(f"\n[bold blue]验证迁移结果[/]")
        
        try:
            # 验证 Agent 配置
            if agent_id:
                from agent_registry import load_agent
                agent_cfg = load_agent(agent_id)
                console.print(f"  ✓ Agent 配置加载正常: {agent_cfg.name}")
                
                # 验证新目录结构
                agent_data_dir = self.project_root / "data" / "agents" / agent_id
                if agent_data_dir.exists():
                    console.print(f"  ✓ 新数据目录存在: {agent_data_dir}")
                    
                    for subdir in ["testsets", "runs", "evals"]:
                        subdir_path = agent_data_dir / subdir
                        if subdir_path.exists():
                            file_count = len(list(subdir_path.glob("*")))
                            console.print(f"    {subdir}/: {file_count} 个文件")
            
            # 验证 Pipeline 配置（如果存在）
            pipelines_dir = self.project_root / "pipelines"
            if pipelines_dir.exists():
                pipeline_files = list(pipelines_dir.glob("*.yaml"))
                console.print(f"  ✓ 找到 {len(pipeline_files)} 个 Pipeline 配置")
                
                for pipeline_file in pipeline_files:
                    try:
                        from pipeline_config import load_pipeline_config
                        pipeline_id = pipeline_file.stem
                        pipeline_cfg = load_pipeline_config(pipeline_id)
                        console.print(f"    {pipeline_id}: {len(pipeline_cfg.steps)} 个步骤")
                    except Exception as e:
                        console.print(f"    [red]{pipeline_id}: 配置错误 - {e}[/]")
            
            console.print(f"  [green]✓ 迁移验证完成[/]")
            return True
            
        except Exception as e:
            console.print(f"  [red]✗ 迁移验证失败: {e}[/]")
            return False
    
    def save_migration_log(self):
        """保存迁移日志"""
        if not self.migration_log:
            return
        
        log_file = self.project_root / "migration_log.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(self.migration_log, f, indent=2, ensure_ascii=False)
        
        console.print(f"\n[dim]迁移日志已保存至: {log_file}[/]")
    
    def interactive_migration(self):
        """交互式迁移"""
        console.rule("[bold blue]配置迁移工具[/]")
        
        # 列出可用的 agents
        try:
            from agent_registry import list_available_agents
            available_agents = list_available_agents()
            
            if not available_agents:
                console.print("[red]没有找到可用的 agents[/]")
                return
            
            console.print(f"找到 {len(available_agents)} 个可用 agents:")
            for i, agent_id in enumerate(available_agents, 1):
                console.print(f"  {i}. {agent_id}")
            
        except Exception as e:
            console.print(f"[red]加载 agents 失败: {e}[/]")
            return
        
        # 选择要迁移的 agent
        while True:
            choice = Prompt.ask(
                "选择要迁移的 agent (输入编号或 agent_id，'all' 表示全部，'q' 退出)",
                default="1"
            )
            
            if choice.lower() == 'q':
                return
            
            if choice.lower() == 'all':
                selected_agents = available_agents
                break
            
            try:
                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(available_agents):
                        selected_agents = [available_agents[idx]]
                        break
                elif choice in available_agents:
                    selected_agents = [choice]
                    break
                else:
                    console.print("[red]无效选择，请重试[/]")
            except ValueError:
                console.print("[red]无效输入，请重试[/]")
        
        # 选择迁移操作
        console.print("\n选择迁移操作:")
        console.print("1. 增强 Agent 配置")
        console.print("2. 添加测试集标签")
        console.print("3. 迁移数据结构")
        console.print("4. 生成 Pipeline 配置")
        console.print("5. 全部操作")
        
        operation = Prompt.ask("选择操作", choices=["1", "2", "3", "4", "5"], default="5")
        
        # 确认是否为预览模式
        dry_run = Confirm.ask("是否为预览模式（不实际修改文件）？", default=True)
        
        # 执行迁移
        for agent_id in selected_agents:
            console.rule(f"[bold green]迁移 Agent: {agent_id}[/]")
            
            if operation in ["1", "5"]:
                self.enhance_agent_config(agent_id, dry_run)
            
            if operation in ["2", "5"]:
                # 查找测试集文件
                testsets_dir = self.project_root / "agents" / agent_id / "testsets"
                if testsets_dir.exists():
                    for testset_file in testsets_dir.glob("*.jsonl"):
                        self.add_testset_tags(agent_id, testset_file.name, dry_run)
            
            if operation in ["3", "5"]:
                self.migrate_data_structure(agent_id, dry_run)
            
            if operation in ["4", "5"]:
                # 为单个 agent 生成简单的 pipeline
                try:
                    from agent_registry import load_agent
                    agent_cfg = load_agent(agent_id)
                    if len(agent_cfg.flows) >= 2:
                        # 创建一个比较两个 flow 的 pipeline
                        agent_flows = [
                            {"agent": agent_id, "flow": agent_cfg.flows[0].name},
                            {"agent": agent_id, "flow": agent_cfg.flows[1].name}
                        ]
                        pipeline_id = f"{agent_id}_comparison"
                        self.generate_pipeline_config(pipeline_id, agent_flows, dry_run)
                except Exception as e:
                    console.print(f"[yellow]跳过 Pipeline 生成: {e}[/]")
        
        # 验证迁移结果
        if not dry_run:
            for agent_id in selected_agents:
                self.validate_migration(agent_id)
        
        # 保存迁移日志
        self.save_migration_log()
        
        console.rule("[bold green]迁移完成[/]")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="配置迁移工具")
    parser.add_argument("--agent", help="指定要迁移的 agent ID")
    parser.add_argument("--operation", choices=["enhance", "tags", "data", "pipeline", "all"], 
                       default="all", help="迁移操作类型")
    parser.add_argument("--dry-run", action="store_true", default=False, help="预览模式，不实际修改文件")
    parser.add_argument("--interactive", action="store_true", help="交互式模式")
    
    args = parser.parse_args()
    
    migrator = ConfigMigrator()
    
    if args.interactive:
        migrator.interactive_migration()
        return
    
    if not args.agent:
        console.print("[red]错误：必须指定 --agent 或使用 --interactive 模式[/]")
        return
    
    # 非交互式迁移
    console.rule(f"[bold blue]迁移 Agent: {args.agent}[/]")
    
    if args.operation in ["enhance", "all"]:
        migrator.enhance_agent_config(args.agent, args.dry_run)
    
    if args.operation in ["tags", "all"]:
        testsets_dir = migrator.project_root / "agents" / args.agent / "testsets"
        if testsets_dir.exists():
            for testset_file in testsets_dir.glob("*.jsonl"):
                migrator.add_testset_tags(args.agent, testset_file.name, args.dry_run)
    
    if args.operation in ["data", "all"]:
        migrator.migrate_data_structure(args.agent, args.dry_run)
    
    if args.operation in ["pipeline", "all"]:
        try:
            sys.path.insert(0, str(migrator.project_root / "src"))
            from agent_registry import load_agent
            agent_cfg = load_agent(args.agent)
            if len(agent_cfg.flows) >= 2:
                agent_flows = [
                    {"agent": args.agent, "flow": agent_cfg.flows[0].name},
                    {"agent": args.agent, "flow": agent_cfg.flows[1].name}
                ]
                pipeline_id = f"{args.agent}_comparison"
                migrator.generate_pipeline_config(pipeline_id, agent_flows, args.dry_run)
        except Exception as e:
            console.print(f"[yellow]跳过 Pipeline 生成: {e}[/]")
    
    if not args.dry_run:
        migrator.validate_migration(args.agent)
    
    migrator.save_migration_log()


if __name__ == "__main__":
    main()