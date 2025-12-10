"""
向后兼容性支持模块

提供新旧系统的兼容性支持，包括：
1. 数据共享机制
2. 弃用警告
3. 混合模式运行支持
4. 平滑迁移功能
"""

import warnings
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from rich.console import Console

console = Console()

class DeprecationManager:
    """弃用功能管理器"""
    
    def __init__(self):
        self.warnings_shown = set()
    
    def warn_once(self, message: str, category: str = "general"):
        """显示一次性弃用警告"""
        warning_key = f"{category}:{message}"
        if warning_key not in self.warnings_shown:
            console.print(f"[yellow]弃用警告：{message}[/]")
            self.warnings_shown.add(warning_key)
    
    def warn_legacy_command(self, old_command: str, new_command: str):
        """警告旧命令的使用"""
        self.warn_once(
            f"命令 '{old_command}' 将在未来版本中弃用，请使用 '{new_command}' 替代",
            "command"
        )
    
    def warn_legacy_parameter(self, old_param: str, new_param: str):
        """警告旧参数的使用"""
        self.warn_once(
            f"参数 '{old_param}' 将在未来版本中弃用，请使用 '{new_param}' 替代",
            "parameter"
        )
    
    def warn_legacy_data_structure(self, old_path: str, new_path: str):
        """警告旧数据结构的使用"""
        self.warn_once(
            f"数据路径 '{old_path}' 将在未来版本中弃用，建议迁移到 '{new_path}'",
            "data_structure"
        )


class DataPathResolver:
    """数据路径解析器 - 支持新旧数据结构"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.deprecation_manager = DeprecationManager()
    
    def resolve_testset_path(self, agent_id: str, testset_name: str) -> Path:
        """解析测试集路径，优先使用新结构"""
        # 新结构路径
        new_path = self.project_root / "data" / "agents" / agent_id / "testsets" / testset_name
        if new_path.exists():
            return new_path
        
        # 旧结构路径
        old_path = self.project_root / "agents" / agent_id / "testsets" / testset_name
        if old_path.exists():
            self.deprecation_manager.warn_legacy_data_structure(
                str(old_path.relative_to(self.project_root)),
                str(new_path.relative_to(self.project_root))
            )
            return old_path
        
        # 如果都不存在，返回新路径（用于创建）
        return new_path
    
    def resolve_runs_dir(self, agent_id: str) -> Path:
        """解析运行结果目录，优先使用新结构"""
        # 新结构路径
        new_dir = self.project_root / "data" / "agents" / agent_id / "runs"
        if new_dir.exists():
            return new_dir
        
        # 创建新目录
        new_dir.mkdir(parents=True, exist_ok=True)
        return new_dir
    
    def resolve_evals_dir(self, agent_id: str) -> Path:
        """解析评估结果目录，优先使用新结构"""
        # 新结构路径
        new_dir = self.project_root / "data" / "agents" / agent_id / "evals"
        if new_dir.exists():
            return new_dir
        
        # 创建新目录
        new_dir.mkdir(parents=True, exist_ok=True)
        return new_dir
    
    def find_legacy_results(self, agent_id: str, pattern: str = "*.csv") -> List[Path]:
        """查找旧数据结构中的结果文件"""
        legacy_files = []
        
        # 在 data/ 根目录查找相关文件
        data_dir = self.project_root / "data"
        if data_dir.exists():
            # 查找包含 agent_id 的文件
            for file_path in data_dir.glob(pattern):
                if agent_id in file_path.name:
                    legacy_files.append(file_path)
        
        return legacy_files
    
    def suggest_migration(self, agent_id: str):
        """建议数据迁移"""
        legacy_files = self.find_legacy_results(agent_id)
        if legacy_files:
            console.print(f"\n[yellow]发现 {len(legacy_files)} 个旧格式的结果文件[/]")
            console.print("[dim]建议运行以下命令进行数据迁移：[/]")
            console.print(f"[dim]python scripts/migrate_data.py --agent {agent_id} --dry-run[/]")
            console.print(f"[dim]python scripts/migrate_data.py --agent {agent_id} --execute[/]")


class MixedModeRunner:
    """混合模式运行器 - 支持新旧系统并存"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.path_resolver = DataPathResolver(project_root)
        self.deprecation_manager = DeprecationManager()
    
    def run_with_compatibility(self, command_type: str, **kwargs) -> Dict[str, Any]:
        """以兼容模式运行命令"""
        result = {"success": True, "warnings": [], "data": {}}
        
        # 检查是否使用了旧的参数名
        self._check_legacy_parameters(kwargs)
        
        # 解析数据路径
        if "agent_id" in kwargs:
            agent_id = kwargs["agent_id"]
            
            # 检查数据结构并建议迁移
            self.path_resolver.suggest_migration(agent_id)
            
            # 更新路径到新结构
            kwargs["runs_dir"] = self.path_resolver.resolve_runs_dir(agent_id)
            kwargs["evals_dir"] = self.path_resolver.resolve_evals_dir(agent_id)
        
        return result
    
    def _check_legacy_parameters(self, kwargs: Dict[str, Any]):
        """检查并警告旧参数的使用"""
        legacy_mappings = {
            "infile": "testset",
            "outfile": "output",
            "flow": "flows",
        }
        
        for old_param, new_param in legacy_mappings.items():
            if old_param in kwargs and new_param not in kwargs:
                self.deprecation_manager.warn_legacy_parameter(old_param, new_param)
    
    def ensure_data_accessibility(self, agent_id: str):
        """确保新旧数据都可以访问"""
        # 创建新目录结构（如果不存在）
        new_agent_dir = self.project_root / "data" / "agents" / agent_id
        for subdir in ["testsets", "runs", "evals"]:
            (new_agent_dir / subdir).mkdir(parents=True, exist_ok=True)
        
        # 创建符号链接或复制文件以确保兼容性
        self._ensure_testset_accessibility(agent_id)
    
    def _ensure_testset_accessibility(self, agent_id: str):
        """确保测试集在新旧位置都可访问"""
        old_testsets_dir = self.project_root / "agents" / agent_id / "testsets"
        new_testsets_dir = self.project_root / "data" / "agents" / agent_id / "testsets"
        
        if old_testsets_dir.exists() and new_testsets_dir.exists():
            # 检查是否有文件只在旧位置存在
            for old_file in old_testsets_dir.glob("*.jsonl"):
                new_file = new_testsets_dir / old_file.name
                if not new_file.exists():
                    # 复制文件到新位置
                    import shutil
                    shutil.copy2(old_file, new_file)
                    console.print(f"[dim]已复制测试集到新位置: {old_file.name}[/]")


class CompatibilityChecker:
    """兼容性检查器"""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
    
    def check_system_compatibility(self) -> Dict[str, Any]:
        """检查系统兼容性"""
        result = {
            "compatible": True,
            "issues": [],
            "recommendations": []
        }
        
        # 检查必需的目录结构
        required_dirs = ["src", "agents", "data"]
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                result["compatible"] = False
                result["issues"].append(f"缺少必需目录: {dir_name}")
        
        # 检查新旧数据结构共存
        self._check_data_structure_coexistence(result)
        
        # 检查配置文件兼容性
        self._check_config_compatibility(result)
        
        return result
    
    def _check_data_structure_coexistence(self, result: Dict[str, Any]):
        """检查新旧数据结构共存情况"""
        agents_dir = self.project_root / "agents"
        data_agents_dir = self.project_root / "data" / "agents"
        
        if agents_dir.exists() and data_agents_dir.exists():
            # 检查是否有数据不一致
            old_agents = set(d.name for d in agents_dir.iterdir() if d.is_dir() and not d.name.startswith('.'))
            new_agents = set(d.name for d in data_agents_dir.iterdir() if d.is_dir())
            
            missing_in_new = old_agents - new_agents
            if missing_in_new:
                result["recommendations"].append(
                    f"建议迁移以下 agents 的数据结构: {', '.join(missing_in_new)}"
                )
        
        elif agents_dir.exists() and not data_agents_dir.exists():
            result["recommendations"].append(
                "建议运行数据迁移工具创建新的数据结构"
            )
    
    def _check_config_compatibility(self, result: Dict[str, Any]):
        """检查配置文件兼容性"""
        try:
            # 检查是否可以加载 agents
            import sys
            sys.path.insert(0, str(self.project_root / "src"))
            from agent_registry import list_available_agents
            
            agents = list_available_agents()
            if not agents:
                result["issues"].append("没有找到可用的 agent 配置")
            
        except Exception as e:
            result["compatible"] = False
            result["issues"].append(f"配置加载失败: {e}")


# 全局实例
_project_root = Path(__file__).parent.parent
deprecation_manager = DeprecationManager()
path_resolver = DataPathResolver(_project_root)
mixed_mode_runner = MixedModeRunner(_project_root)
compatibility_checker = CompatibilityChecker(_project_root)


def ensure_compatibility(agent_id: str = None):
    """确保系统兼容性"""
    if agent_id:
        mixed_mode_runner.ensure_data_accessibility(agent_id)
    
    # 检查整体兼容性
    compat_result = compatibility_checker.check_system_compatibility()
    
    if not compat_result["compatible"]:
        console.print("[red]发现兼容性问题：[/]")
        for issue in compat_result["issues"]:
            console.print(f"  - {issue}")
    
    if compat_result["recommendations"]:
        console.print("[yellow]兼容性建议：[/]")
        for rec in compat_result["recommendations"]:
            console.print(f"  - {rec}")
    
    return compat_result


def get_compatible_path(path_type: str, agent_id: str, filename: str = None) -> Path:
    """获取兼容的文件路径"""
    if path_type == "testset":
        return path_resolver.resolve_testset_path(agent_id, filename)
    elif path_type == "runs":
        return path_resolver.resolve_runs_dir(agent_id)
    elif path_type == "evals":
        return path_resolver.resolve_evals_dir(agent_id)
    else:
        raise ValueError(f"不支持的路径类型: {path_type}")


def warn_if_legacy(feature_name: str, old_usage: str, new_usage: str):
    """如果使用旧功能则发出警告"""
    deprecation_manager.warn_once(
        f"{feature_name}: '{old_usage}' 已弃用，请使用 '{new_usage}'",
        feature_name
    )