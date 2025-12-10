#!/usr/bin/env python3
# scripts/migrate_data.py
"""数据迁移工具：将现有数据从旧结构迁移到新的 agents/ 和 pipelines/ 结构"""

import sys
import argparse
import shutil
from pathlib import Path
from typing import List, Dict, Set, Optional
import json
from datetime import datetime

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from data_manager import DataManager, data_manager
from paths import ROOT_DIR, DATA_DIR


class DataMigrator:
    """数据迁移器"""
    
    def __init__(self, dry_run: bool = False, verbose: bool = False):
        self.dry_run = dry_run
        self.verbose = verbose
        self.data_manager = DataManager()
        self.migration_log = []
        self.errors = []
        
    def log(self, message: str, level: str = "INFO"):
        """记录迁移日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}"
        self.migration_log.append(log_entry)
        
        if self.verbose or level in ["ERROR", "WARNING"]:
            print(log_entry)
    
    def discover_agents(self) -> Set[str]:
        """发现现有的 agent ID"""
        agents = set()
        
        # 从 runs 目录发现
        runs_dir = DATA_DIR / "runs"
        if runs_dir.exists():
            for agent_dir in runs_dir.iterdir():
                if agent_dir.is_dir():
                    agents.add(agent_dir.name)
        
        # 从 evals 目录发现
        evals_dir = DATA_DIR / "evals"
        if evals_dir.exists():
            for agent_dir in evals_dir.iterdir():
                if agent_dir.is_dir():
                    agents.add(agent_dir.name)
        
        # 从 testsets 目录发现
        testsets_dir = DATA_DIR / "testsets"
        if testsets_dir.exists():
            for agent_dir in testsets_dir.iterdir():
                if agent_dir.is_dir():
                    agents.add(agent_dir.name)
        
        # 从 agents 配置目录发现
        agents_config_dir = ROOT_DIR / "agents"
        if agents_config_dir.exists():
            for agent_dir in agents_config_dir.iterdir():
                if agent_dir.is_dir() and not agent_dir.name.startswith('_'):
                    agents.add(agent_dir.name)
        
        self.log(f"发现 {len(agents)} 个 agent: {', '.join(sorted(agents))}")
        return agents
    
    def migrate_agent_data(self, agent_id: str) -> Dict[str, int]:
        """迁移单个 agent 的数据"""
        stats = {"testsets": 0, "runs": 0, "evals": 0, "errors": 0}
        
        self.log(f"开始迁移 agent: {agent_id}")
        
        # 确保新目录结构存在
        if not self.dry_run:
            self.data_manager.ensure_entity_dirs("agent", agent_id)
        
        # 迁移测试集
        old_testsets_dir = DATA_DIR / "testsets" / agent_id
        if old_testsets_dir.exists():
            new_testsets_dir = self.data_manager.get_entity_testsets_dir("agent", agent_id)
            stats["testsets"] = self._migrate_directory(
                old_testsets_dir, new_testsets_dir, f"{agent_id} testsets"
            )
        
        # 迁移运行结果
        old_runs_dir = DATA_DIR / "runs" / agent_id
        if old_runs_dir.exists():
            new_runs_dir = self.data_manager.get_entity_runs_dir("agent", agent_id)
            stats["runs"] = self._migrate_directory(
                old_runs_dir, new_runs_dir, f"{agent_id} runs"
            )
        
        # 迁移评估结果
        old_evals_dir = DATA_DIR / "evals" / agent_id
        if old_evals_dir.exists():
            new_evals_dir = self.data_manager.get_entity_evals_dir("agent", agent_id)
            stats["evals"] = self._migrate_directory(
                old_evals_dir, new_evals_dir, f"{agent_id} evals"
            )
        
        self.log(f"完成 agent {agent_id} 迁移: "
                f"testsets={stats['testsets']}, runs={stats['runs']}, evals={stats['evals']}")
        
        return stats
    
    def _migrate_directory(self, source_dir: Path, target_dir: Path, 
                          description: str) -> int:
        """迁移目录内容"""
        if not source_dir.exists():
            return 0
        
        file_count = 0
        
        try:
            for item in source_dir.rglob("*"):
                if item.is_file():
                    # 计算相对路径
                    rel_path = item.relative_to(source_dir)
                    target_path = target_dir / rel_path
                    
                    # 确保目标目录存在
                    if not self.dry_run:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # 检查文件是否已存在
                    if target_path.exists():
                        self.log(f"目标文件已存在，跳过: {target_path}", "WARNING")
                        continue
                    
                    # 复制文件
                    if not self.dry_run:
                        shutil.copy2(item, target_path)
                        self.log(f"复制文件: {item} -> {target_path}")
                    else:
                        self.log(f"[DRY RUN] 将复制: {item} -> {target_path}")
                    
                    file_count += 1
        
        except Exception as e:
            error_msg = f"迁移 {description} 时出错: {e}"
            self.log(error_msg, "ERROR")
            self.errors.append(error_msg)
        
        return file_count
    
    def verify_migration(self, agent_id: str) -> Dict[str, bool]:
        """验证迁移结果"""
        verification = {"testsets": True, "runs": True, "evals": True}
        
        # 检查测试集
        old_testsets = DATA_DIR / "testsets" / agent_id
        new_testsets = self.data_manager.get_entity_testsets_dir("agent", agent_id)
        if old_testsets.exists():
            verification["testsets"] = self._verify_directory_migration(
                old_testsets, new_testsets
            )
        
        # 检查运行结果
        old_runs = DATA_DIR / "runs" / agent_id
        new_runs = self.data_manager.get_entity_runs_dir("agent", agent_id)
        if old_runs.exists():
            verification["runs"] = self._verify_directory_migration(
                old_runs, new_runs
            )
        
        # 检查评估结果
        old_evals = DATA_DIR / "evals" / agent_id
        new_evals = self.data_manager.get_entity_evals_dir("agent", agent_id)
        if old_evals.exists():
            verification["evals"] = self._verify_directory_migration(
                old_evals, new_evals
            )
        
        return verification
    
    def _verify_directory_migration(self, source_dir: Path, target_dir: Path) -> bool:
        """验证目录迁移的完整性"""
        if not source_dir.exists():
            return True
        
        if not target_dir.exists():
            self.log(f"目标目录不存在: {target_dir}", "ERROR")
            return False
        
        # 比较文件数量和大小
        source_files = list(source_dir.rglob("*"))
        source_files = [f for f in source_files if f.is_file()]
        
        for source_file in source_files:
            rel_path = source_file.relative_to(source_dir)
            target_file = target_dir / rel_path
            
            if not target_file.exists():
                self.log(f"目标文件缺失: {target_file}", "ERROR")
                return False
            
            if source_file.stat().st_size != target_file.stat().st_size:
                self.log(f"文件大小不匹配: {source_file} vs {target_file}", "ERROR")
                return False
        
        return True
    
    def create_migration_report(self, agents: Set[str], 
                              migration_stats: Dict[str, Dict[str, int]]) -> str:
        """创建迁移报告"""
        report_lines = [
            "# 数据迁移报告",
            f"迁移时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"迁移模式: {'试运行' if self.dry_run else '实际迁移'}",
            "",
            "## 迁移统计",
        ]
        
        total_stats = {"testsets": 0, "runs": 0, "evals": 0, "errors": 0}
        
        for agent_id in sorted(agents):
            if agent_id in migration_stats:
                stats = migration_stats[agent_id]
                report_lines.append(
                    f"- {agent_id}: testsets={stats['testsets']}, "
                    f"runs={stats['runs']}, evals={stats['evals']}"
                )
                for key in total_stats:
                    total_stats[key] += stats[key]
        
        report_lines.extend([
            "",
            "## 总计",
            f"- 测试集文件: {total_stats['testsets']}",
            f"- 运行结果文件: {total_stats['runs']}",
            f"- 评估结果文件: {total_stats['evals']}",
            f"- 错误数量: {total_stats['errors']}",
        ])
        
        if self.errors:
            report_lines.extend([
                "",
                "## 错误详情",
            ])
            for error in self.errors:
                report_lines.append(f"- {error}")
        
        if self.migration_log:
            report_lines.extend([
                "",
                "## 详细日志",
            ])
            for log_entry in self.migration_log:
                report_lines.append(log_entry)
        
        return "\n".join(report_lines)
    
    def run_migration(self, specific_agents: Optional[List[str]] = None) -> bool:
        """运行完整的迁移过程"""
        self.log("开始数据迁移过程")
        
        # 初始化新的数据结构
        if not self.dry_run:
            self.data_manager.initialize_data_structure()
            self.log("已初始化新的数据目录结构")
        
        # 发现需要迁移的 agents
        all_agents = self.discover_agents()
        
        if specific_agents:
            agents_to_migrate = set(specific_agents) & all_agents
            missing_agents = set(specific_agents) - all_agents
            if missing_agents:
                self.log(f"指定的 agent 不存在: {', '.join(missing_agents)}", "WARNING")
        else:
            agents_to_migrate = all_agents
        
        if not agents_to_migrate:
            self.log("没有找到需要迁移的 agent", "WARNING")
            return False
        
        # 执行迁移
        migration_stats = {}
        success_count = 0
        
        for agent_id in sorted(agents_to_migrate):
            try:
                stats = self.migrate_agent_data(agent_id)
                migration_stats[agent_id] = stats
                
                # 验证迁移结果
                if not self.dry_run:
                    verification = self.verify_migration(agent_id)
                    if all(verification.values()):
                        success_count += 1
                        self.log(f"Agent {agent_id} 迁移验证通过")
                    else:
                        self.log(f"Agent {agent_id} 迁移验证失败: {verification}", "ERROR")
                else:
                    success_count += 1
                
            except Exception as e:
                error_msg = f"迁移 agent {agent_id} 时发生异常: {e}"
                self.log(error_msg, "ERROR")
                self.errors.append(error_msg)
        
        # 生成报告
        report = self.create_migration_report(agents_to_migrate, migration_stats)
        
        # 保存报告
        report_filename = f"migration_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        report_path = ROOT_DIR / report_filename
        
        if not self.dry_run:
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(report)
            self.log(f"迁移报告已保存: {report_path}")
        else:
            print("\n" + "="*50)
            print("迁移报告预览:")
            print("="*50)
            print(report)
        
        # 总结
        total_agents = len(agents_to_migrate)
        self.log(f"迁移完成: {success_count}/{total_agents} 个 agent 成功迁移")
        
        if self.errors:
            self.log(f"迁移过程中发生 {len(self.errors)} 个错误", "WARNING")
            return False
        
        return success_count == total_agents


def main():
    parser = argparse.ArgumentParser(
        description="将现有数据从旧结构迁移到新的 agents/ 和 pipelines/ 结构"
    )
    parser.add_argument(
        "--agents", 
        nargs="*", 
        help="指定要迁移的 agent ID，不指定则迁移所有发现的 agent"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true", 
        help="试运行模式，不实际移动文件"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true", 
        help="显示详细的迁移过程"
    )
    
    args = parser.parse_args()
    
    print("数据迁移工具")
    print("="*50)
    
    if args.dry_run:
        print("运行模式: 试运行 (不会实际移动文件)")
    else:
        print("运行模式: 实际迁移")
        response = input("确认要执行实际迁移吗？这将移动现有文件。(y/N): ")
        if response.lower() != 'y':
            print("迁移已取消")
            return
    
    print()
    
    # 创建迁移器并运行
    migrator = DataMigrator(dry_run=args.dry_run, verbose=args.verbose)
    success = migrator.run_migration(args.agents)
    
    if success:
        print("\n✅ 迁移成功完成!")
        if not args.dry_run:
            print("建议在确认迁移结果正确后，手动删除旧的数据目录")
    else:
        print("\n❌ 迁移过程中出现错误，请检查日志")
        sys.exit(1)


if __name__ == "__main__":
    main()