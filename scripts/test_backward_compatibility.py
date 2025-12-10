#!/usr/bin/env python3
"""
向后兼容性测试脚本

验证现有 Agent/Flow 评估命令继续正常工作，确保新的 Pipeline 系统
不会破坏现有功能。

测试覆盖：
1. 现有 CLI 命令和参数组合
2. 现有数据文件的访问和处理
3. Agent 配置加载和验证
4. Flow 执行和输出格式
5. 评估系统（规则和 LLM judge）
"""

import os
import sys
import subprocess
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Optional
import tempfile
import shutil

# 添加 src 目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

class BackwardCompatibilityTester:
    """向后兼容性测试器"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.test_results = []
        self.temp_dir = None
        
    def setup_test_environment(self):
        """设置测试环境"""
        console.print("[bold blue]设置测试环境...[/]")
        
        # 创建临时目录用于测试输出
        self.temp_dir = Path(tempfile.mkdtemp(prefix="compat_test_"))
        console.print(f"临时目录: {self.temp_dir}")
        
        # 验证项目结构
        required_dirs = ["src", "agents", "data"]
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                raise FileNotFoundError(f"必需目录不存在: {dir_path}")
        
        console.print("[green]✓ 测试环境设置完成[/]")
    
    def cleanup_test_environment(self):
        """清理测试环境"""
        if self.temp_dir and self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            console.print(f"[dim]已清理临时目录: {self.temp_dir}[/]")
    
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None) -> Dict[str, Any]:
        """运行命令并返回结果"""
        if cwd is None:
            cwd = self.project_root
            
        try:
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=60  # 60秒超时
            )
            
            return {
                "success": result.returncode == 0,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "cmd": " ".join(cmd)
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": "Command timed out",
                "cmd": " ".join(cmd)
            }
        except Exception as e:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": str(e),
                "cmd": " ".join(cmd)
            }
    
    def test_agent_loading(self):
        """测试 Agent 配置加载"""
        console.print("\n[bold yellow]测试 Agent 配置加载...[/]")
        
        try:
            from agent_registry import load_agent, list_available_agents
            
            # 测试列出可用 agents
            available_agents = list_available_agents()
            if not available_agents:
                self.test_results.append({
                    "test": "list_available_agents",
                    "success": False,
                    "error": "没有找到可用的 agents"
                })
                return
            
            console.print(f"找到 {len(available_agents)} 个可用 agents: {', '.join(available_agents)}")
            
            # 测试加载每个 agent
            for agent_id in available_agents:
                try:
                    agent_cfg = load_agent(agent_id)
                    
                    # 验证基本字段
                    required_fields = ["id", "name", "flows"]
                    missing_fields = [f for f in required_fields if not hasattr(agent_cfg, f) or not getattr(agent_cfg, f)]
                    
                    if missing_fields:
                        self.test_results.append({
                            "test": f"load_agent_{agent_id}",
                            "success": False,
                            "error": f"缺少必需字段: {missing_fields}"
                        })
                    else:
                        self.test_results.append({
                            "test": f"load_agent_{agent_id}",
                            "success": True,
                            "details": f"flows: {[f.name for f in agent_cfg.flows]}"
                        })
                        console.print(f"  ✓ {agent_id}: {len(agent_cfg.flows)} flows")
                        
                except Exception as e:
                    self.test_results.append({
                        "test": f"load_agent_{agent_id}",
                        "success": False,
                        "error": str(e)
                    })
                    console.print(f"  ✗ {agent_id}: {e}")
                    
        except ImportError as e:
            self.test_results.append({
                "test": "agent_loading_import",
                "success": False,
                "error": f"导入错误: {e}"
            })
    
    def test_cli_commands(self):
        """测试现有 CLI 命令"""
        console.print("\n[bold yellow]测试 CLI 命令...[/]")
        
        # 测试主入口点
        help_result = self.run_command(["python", "-m", "src", "--help"])
        self.test_results.append({
            "test": "main_help",
            "success": help_result["success"],
            "details": "主命令帮助" if help_result["success"] else help_result["stderr"]
        })
        
        if help_result["success"]:
            console.print("  ✓ 主命令帮助正常")
        else:
            console.print(f"  ✗ 主命令帮助失败: {help_result['stderr']}")
        
        # 测试各个子命令的帮助
        subcommands = ["batch", "compare", "eval", "baseline", "regression"]
        for subcmd in subcommands:
            help_result = self.run_command(["python", "-m", "src", subcmd, "--help"])
            self.test_results.append({
                "test": f"{subcmd}_help",
                "success": help_result["success"],
                "details": f"{subcmd} 命令帮助" if help_result["success"] else help_result["stderr"]
            })
            
            if help_result["success"]:
                console.print(f"  ✓ {subcmd} 命令帮助正常")
            else:
                console.print(f"  ✗ {subcmd} 命令帮助失败: {help_result['stderr']}")
    
    def test_agent_execution(self):
        """测试 Agent 执行功能"""
        console.print("\n[bold yellow]测试 Agent 执行功能...[/]")
        
        # 查找一个可用的 agent 进行测试
        try:
            from agent_registry import list_available_agents, load_agent
            
            available_agents = list_available_agents()
            if not available_agents:
                console.print("  ✗ 没有可用的 agents 进行测试")
                return
            
            # 选择第一个 agent 进行测试
            test_agent_id = available_agents[0]
            agent_cfg = load_agent(test_agent_id)
            
            console.print(f"使用 agent '{test_agent_id}' 进行测试")
            
            # 检查是否有测试集
            agent_testset_dir = self.project_root / "agents" / test_agent_id / "testsets"
            if not agent_testset_dir.exists():
                console.print(f"  ✗ Agent {test_agent_id} 没有 testsets 目录")
                return
            
            testset_files = list(agent_testset_dir.glob("*.jsonl"))
            if not testset_files:
                console.print(f"  ✗ Agent {test_agent_id} 没有 JSONL 测试集文件")
                return
            
            test_testset = testset_files[0]
            console.print(f"使用测试集: {test_testset.name}")
            
            # 测试 batch 命令（限制1条样本）
            output_file = self.temp_dir / f"test_{test_agent_id}_batch.csv"
            batch_cmd = [
                "python", "-m", "src", "batch",
                "--agent", test_agent_id,
                "--limit", "1",
                "--outfile", str(output_file)
            ]
            
            batch_result = self.run_command(batch_cmd)
            self.test_results.append({
                "test": f"batch_execution_{test_agent_id}",
                "success": batch_result["success"] and output_file.exists(),
                "details": f"输出文件: {output_file}" if batch_result["success"] else batch_result["stderr"]
            })
            
            if batch_result["success"] and output_file.exists():
                console.print(f"  ✓ batch 命令执行成功")
                
                # 验证输出文件格式
                try:
                    with open(output_file, 'r', encoding='utf-8') as f:
                        reader = csv.DictReader(f)
                        rows = list(reader)
                        
                    if rows and 'output' in rows[0]:
                        console.print(f"    输出文件包含 {len(rows)} 行数据")
                        self.test_results.append({
                            "test": f"batch_output_format_{test_agent_id}",
                            "success": True,
                            "details": f"{len(rows)} 行数据，包含 output 字段"
                        })
                    else:
                        self.test_results.append({
                            "test": f"batch_output_format_{test_agent_id}",
                            "success": False,
                            "error": "输出文件格式不正确"
                        })
                        
                except Exception as e:
                    self.test_results.append({
                        "test": f"batch_output_format_{test_agent_id}",
                        "success": False,
                        "error": f"读取输出文件失败: {e}"
                    })
            else:
                console.print(f"  ✗ batch 命令执行失败: {batch_result['stderr']}")
            
            # 测试 eval 命令（Agent 模式）
            if agent_cfg.flows:
                flow_name = agent_cfg.flows[0].name
                eval_output_file = self.temp_dir / f"test_{test_agent_id}_eval.csv"
                
                eval_cmd = [
                    "python", "-m", "src", "eval",
                    "--agent", test_agent_id,
                    "--flows", flow_name,
                    "--limit", "1",
                    "--outfile", str(eval_output_file)
                ]
                
                eval_result = self.run_command(eval_cmd)
                self.test_results.append({
                    "test": f"eval_agent_{test_agent_id}",
                    "success": eval_result["success"] and eval_output_file.exists(),
                    "details": f"flow: {flow_name}" if eval_result["success"] else eval_result["stderr"]
                })
                
                if eval_result["success"]:
                    console.print(f"  ✓ eval 命令 (Agent 模式) 执行成功")
                else:
                    console.print(f"  ✗ eval 命令 (Agent 模式) 执行失败: {eval_result['stderr']}")
                    
        except Exception as e:
            console.print(f"  ✗ Agent 执行测试失败: {e}")
            self.test_results.append({
                "test": "agent_execution_general",
                "success": False,
                "error": str(e)
            })
    
    def test_data_access(self):
        """测试现有数据文件访问"""
        console.print("\n[bold yellow]测试数据文件访问...[/]")
        
        # 检查数据目录结构
        data_dir = self.project_root / "data"
        if not data_dir.exists():
            self.test_results.append({
                "test": "data_directory",
                "success": False,
                "error": "data 目录不存在"
            })
            return
        
        # 检查现有数据文件
        existing_files = []
        for pattern in ["*.csv", "*.jsonl", "*.json"]:
            existing_files.extend(data_dir.rglob(pattern))
        
        console.print(f"找到 {len(existing_files)} 个现有数据文件")
        
        # 测试读取一些数据文件
        test_files = existing_files[:5]  # 只测试前5个文件
        
        for file_path in test_files:
            try:
                if file_path.suffix == '.csv':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        reader = csv.reader(f)
                        rows = list(reader)
                    success = len(rows) > 0
                    details = f"CSV 文件，{len(rows)} 行"
                    
                elif file_path.suffix == '.jsonl':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = [line.strip() for line in f if line.strip()]
                        for line in lines[:3]:  # 只验证前3行
                            json.loads(line)
                    success = len(lines) > 0
                    details = f"JSONL 文件，{len(lines)} 行"
                    
                elif file_path.suffix == '.json':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    success = True
                    details = f"JSON 文件，类型: {type(data).__name__}"
                    
                else:
                    success = True
                    details = f"其他文件类型: {file_path.suffix}"
                
                self.test_results.append({
                    "test": f"data_file_access_{file_path.name}",
                    "success": success,
                    "details": details
                })
                
                if success:
                    console.print(f"  ✓ {file_path.relative_to(data_dir)}: {details}")
                    
            except Exception as e:
                self.test_results.append({
                    "test": f"data_file_access_{file_path.name}",
                    "success": False,
                    "error": str(e)
                })
                console.print(f"  ✗ {file_path.relative_to(data_dir)}: {e}")
    
    def test_tag_filtering(self):
        """测试标签过滤功能"""
        console.print("\n[bold yellow]测试标签过滤功能...[/]")
        
        try:
            from testset_filter import filter_samples_by_tags
            
            # 创建测试样本
            test_samples = [
                {"id": "1", "input": "test1", "tags": ["regression", "happy_path"]},
                {"id": "2", "input": "test2", "tags": ["edge_case"]},
                {"id": "3", "input": "test3", "tags": ["regression"]},
                {"id": "4", "input": "test4"},  # 没有 tags
            ]
            
            # 测试包含标签过滤
            filtered = filter_samples_by_tags(test_samples, include_tags=["regression"])
            expected_ids = {"1", "3"}
            actual_ids = {s["id"] for s in filtered}
            
            include_success = actual_ids == expected_ids
            self.test_results.append({
                "test": "tag_filtering_include",
                "success": include_success,
                "details": f"期望: {expected_ids}, 实际: {actual_ids}" if include_success else f"过滤失败"
            })
            
            # 测试排除标签过滤
            filtered = filter_samples_by_tags(test_samples, exclude_tags=["edge_case"])
            expected_ids = {"1", "3", "4"}
            actual_ids = {s["id"] for s in filtered}
            
            exclude_success = actual_ids == expected_ids
            self.test_results.append({
                "test": "tag_filtering_exclude",
                "success": exclude_success,
                "details": f"期望: {expected_ids}, 实际: {actual_ids}" if exclude_success else f"过滤失败"
            })
            
            if include_success and exclude_success:
                console.print("  ✓ 标签过滤功能正常")
            else:
                console.print("  ✗ 标签过滤功能异常")
                
        except Exception as e:
            self.test_results.append({
                "test": "tag_filtering_general",
                "success": False,
                "error": str(e)
            })
            console.print(f"  ✗ 标签过滤测试失败: {e}")
    
    def generate_report(self):
        """生成测试报告"""
        console.print("\n[bold blue]生成测试报告...[/]")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests
        
        # 总体统计
        console.print(Panel.fit(
            f"总测试数: {total_tests}\n"
            f"通过: [green]{passed_tests}[/]\n"
            f"失败: [red]{failed_tests}[/]\n"
            f"通过率: {passed_tests/total_tests*100:.1f}%",
            title="测试结果统计",
            border_style="blue"
        ))
        
        # 详细结果表格
        if self.test_results:
            table = Table(title="详细测试结果")
            table.add_column("测试项", style="bold")
            table.add_column("状态", justify="center")
            table.add_column("详情/错误", overflow="fold")
            
            for result in self.test_results:
                status = "[green]✓[/]" if result["success"] else "[red]✗[/]"
                details = result.get("details", result.get("error", ""))
                
                table.add_row(
                    result["test"],
                    status,
                    details
                )
            
            console.print(table)
        
        # 保存报告到文件
        report_file = self.project_root / "backward_compatibility_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": str(Path(__file__).stat().st_mtime),
                "summary": {
                    "total": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "pass_rate": passed_tests/total_tests if total_tests > 0 else 0
                },
                "results": self.test_results
            }, f, indent=2, ensure_ascii=False)
        
        console.print(f"\n[dim]详细报告已保存至: {report_file}[/]")
        
        return failed_tests == 0
    
    def run_all_tests(self):
        """运行所有测试"""
        console.rule("[bold blue]向后兼容性测试开始[/]")
        
        try:
            self.setup_test_environment()
            
            # 运行各项测试
            self.test_agent_loading()
            self.test_cli_commands()
            self.test_agent_execution()
            self.test_data_access()
            self.test_tag_filtering()
            
            # 生成报告
            success = self.generate_report()
            
            console.rule("[bold green]测试完成[/]" if success else "[bold red]测试完成（有失败项）[/]")
            
            return success
            
        finally:
            self.cleanup_test_environment()


def main():
    """主函数"""
    tester = BackwardCompatibilityTester()
    success = tester.run_all_tests()
    
    if not success:
        console.print("\n[bold red]警告：发现向后兼容性问题，请检查失败的测试项[/]")
        sys.exit(1)
    else:
        console.print("\n[bold green]✓ 所有向后兼容性测试通过[/]")


if __name__ == "__main__":
    main()