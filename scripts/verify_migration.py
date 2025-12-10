#!/usr/bin/env python3
"""
迁移验证工具

验证迁移完整性，确保：
1. 配置文件格式正确
2. 数据文件完整性
3. 新旧系统兼容性
4. 功能正常运行
"""

import os
import sys
import json
from pathlib import Path
import argparse

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

class MigrationVerifier:
    """迁移验证器"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self.verification_results = []
        
    def verify_agent_config(self, agent_id: str) -> bool:
        """验证 Agent 配置"""
        console.print(f"\n[bold blue]验证 Agent 配置: {agent_id}[/]")
        
        try:
            from agent_registry import load_agent
            agent_cfg = load_agent(agent_id)
            
            # 验证基本字段
            required_fields = ["id", "name", "flows"]
            missing_fields = []
            
            for field in required_fields:
                if not hasattr(agent_cfg, field) or not getattr(agent_cfg, field):
                    missing_fields.append(field)
            
            if missing_fields:
                self.verification_results.append({
                    "test": f"agent_config_{agent_id}",
                    "success": False,
                    "error": f"缺少必需字段: {missing_fields}"
                })
                console.print(f"  [red]✗ 缺少字段: {missing_fields}[/]")
                return False
            
            console.print(f"  ✓ 基本配置正常: {len(agent_cfg.flows)} 个 flows")
            
            self.verification_results.append({
                "test": f"agent_config_{agent_id}",
                "success": True,
                "details": f"{len(agent_cfg.flows)} flows"
            })
            
            return True
            
        except Exception as e:
            self.verification_results.append({
                "test": f"agent_config_{agent_id}",
                "success": False,
                "error": str(e)
            })
            console.print(f"  [red]✗ 配置加载失败: {e}[/]")
            return False
    
    def verify_backward_compatibility(self) -> bool:
        """验证向后兼容性"""
        console.print(f"\n[bold blue]验证向后兼容性[/]")
        
        try:
            # 测试基本的 agent 加载
            from agent_registry import list_available_agents, load_agent
            
            available_agents = list_available_agents()
            if not available_agents:
                console.print(f"  [red]✗ 没有可用的 agents[/]")
                return False
            
            console.print(f"  ✓ 找到 {len(available_agents)} 个可用 agents")
            
            # 测试加载第一个 agent
            test_agent = available_agents[0]
            agent_cfg = load_agent(test_agent)
            console.print(f"  ✓ Agent 加载正常: {agent_cfg.name}")
            
            # 测试标签过滤功能
            from testset_filter import filter_samples_by_tags
            
            test_samples = [
                {"id": "1", "tags": ["test"]},
                {"id": "2", "tags": ["other"]},
            ]
            
            filtered = filter_samples_by_tags(test_samples, include_tags=["test"])
            if len(filtered) == 1 and filtered[0]["id"] == "1":
                console.print(f"  ✓ 标签过滤功能正常")
            else:
                console.print(f"  [red]✗ 标签过滤功能异常[/]")
                return False
            
            self.verification_results.append({
                "test": "backward_compatibility",
                "success": True,
                "details": f"{len(available_agents)} agents, 标签过滤正常"
            })
            
            return True
            
        except Exception as e:
            self.verification_results.append({
                "test": "backward_compatibility",
                "success": False,
                "error": str(e)
            })
            console.print(f"  [red]✗ 兼容性验证失败: {e}[/]")
            return False
    
    def generate_verification_report(self) -> bool:
        """生成验证报告"""
        console.print("\n[bold blue]生成验证报告...[/]")
        
        total_tests = len(self.verification_results)
        passed_tests = sum(1 for r in self.verification_results if r["success"])
        failed_tests = total_tests - passed_tests
        
        # 总体统计
        console.print(Panel.fit(
            f"总验证项: {total_tests}\n"
            f"通过: [green]{passed_tests}[/]\n"
            f"失败: [red]{failed_tests}[/]\n"
            f"通过率: {passed_tests/total_tests*100:.1f}%",
            title="验证结果统计",
            border_style="blue"
        ))
        
        # 详细结果表格
        if self.verification_results:
            table = Table(title="详细验证结果")
            table.add_column("验证项", style="bold")
            table.add_column("状态", justify="center")
            table.add_column("详情/错误", overflow="fold")
            
            for result in self.verification_results:
                status = "[green]✓[/]" if result["success"] else "[red]✗[/]"
                details = result.get("details", result.get("error", ""))
                
                table.add_row(
                    result["test"],
                    status,
                    details
                )
            
            console.print(table)
        
        return failed_tests == 0
    
    def verify_all(self, agent_id: str = None) -> bool:
        """执行完整验证"""
        console.rule("[bold blue]迁移验证开始[/]")
        
        success = True
        
        # 验证向后兼容性
        if not self.verify_backward_compatibility():
            success = False
        
        # 验证指定的 agent
        if agent_id:
            if not self.verify_agent_config(agent_id):
                success = False
        else:
            # 验证所有 agents
            try:
                from agent_registry import list_available_agents
                available_agents = list_available_agents()
                
                for agent in available_agents:
                    if not self.verify_agent_config(agent):
                        success = False
                        
            except Exception as e:
                console.print(f"[red]获取 agents 列表失败: {e}[/]")
                success = False
        
        # 生成报告
        report_success = self.generate_verification_report()
        
        console.rule("[bold green]验证完成[/]" if success and report_success else "[bold red]验证完成（有失败项）[/]")
        
        return success and report_success


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="迁移验证工具")
    parser.add_argument("--agent", help="指定要验证的 agent ID")
    parser.add_argument("--all", action="store_true", help="验证所有配置")
    
    args = parser.parse_args()
    
    verifier = MigrationVerifier()
    
    if args.all:
        success = verifier.verify_all()
    else:
        success = verifier.verify_all(args.agent)
    
    if not success:
        console.print("\n[bold red]警告：发现验证失败项，请检查详细报告[/]")
        sys.exit(1)
    else:
        console.print("\n[bold green]✓ 所有验证项通过[/]")


if __name__ == "__main__":
    main()