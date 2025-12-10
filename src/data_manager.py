# src/data_manager.py
"""数据目录管理模块，支持新的 agents/ 和 pipelines/ 组织结构"""

from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Optional, Union
import json
import os
import shutil
from typing import Dict, Any, List

try:
    from .paths import ROOT_DIR, DATA_DIR
except ImportError:
    # 当作为独立模块导入时的回退
    from paths import ROOT_DIR, DATA_DIR


class DataManager:
    """数据目录和文件管理器"""
    
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or ROOT_DIR
        self.data_dir = self.root_dir / "data"
    
    # 目录结构管理
    def get_agent_base_dir(self, agent_id: str) -> Path:
        """获取 agent 的基础目录"""
        return self.data_dir / "agents" / agent_id
    
    def get_pipeline_base_dir(self, pipeline_id: str) -> Path:
        """获取 pipeline 的基础目录"""
        return self.data_dir / "pipelines" / pipeline_id
    
    def get_entity_testsets_dir(self, entity_type: str, entity_id: str) -> Path:
        """获取实体的测试集目录"""
        if entity_type == "agent":
            return self.get_agent_base_dir(entity_id) / "testsets"
        elif entity_type == "pipeline":
            return self.get_pipeline_base_dir(entity_id) / "testsets"
        else:
            raise ValueError(f"不支持的实体类型: {entity_type}")
    
    def get_entity_runs_dir(self, entity_type: str, entity_id: str) -> Path:
        """获取实体的运行结果目录"""
        if entity_type == "agent":
            return self.get_agent_base_dir(entity_id) / "runs"
        elif entity_type == "pipeline":
            return self.get_pipeline_base_dir(entity_id) / "runs"
        else:
            raise ValueError(f"不支持的实体类型: {entity_type}")
    
    def get_entity_evals_dir(self, entity_type: str, entity_id: str) -> Path:
        """获取实体的评估结果目录"""
        if entity_type == "agent":
            return self.get_agent_base_dir(entity_id) / "evals"
        elif entity_type == "pipeline":
            return self.get_pipeline_base_dir(entity_id) / "evals"
        else:
            raise ValueError(f"不支持的实体类型: {entity_type}")
    
    def get_baselines_dir(self, entity_type: str) -> Path:
        """获取基线存储目录"""
        return self.data_dir / "baselines" / f"{entity_type}s"
    
    def ensure_entity_dirs(self, entity_type: str, entity_id: str) -> None:
        """确保实体的所有目录都存在"""
        base_dir = (self.get_agent_base_dir(entity_id) 
                   if entity_type == "agent" 
                   else self.get_pipeline_base_dir(entity_id))
        
        # 创建基础目录结构
        (base_dir / "testsets").mkdir(parents=True, exist_ok=True)
        (base_dir / "runs").mkdir(parents=True, exist_ok=True)
        
        # 创建评估子目录
        evals_dir = base_dir / "evals"
        (evals_dir / "rules").mkdir(parents=True, exist_ok=True)
        (evals_dir / "manual").mkdir(parents=True, exist_ok=True)
        (evals_dir / "llm").mkdir(parents=True, exist_ok=True)
        
        # 创建基线目录
        baselines_dir = self.get_baselines_dir(entity_type)
        (baselines_dir / entity_id).mkdir(parents=True, exist_ok=True)
    
    def initialize_data_structure(self) -> None:
        """初始化完整的数据目录结构"""
        # 创建顶级目录
        self.data_dir.mkdir(exist_ok=True)
        (self.data_dir / "agents").mkdir(exist_ok=True)
        (self.data_dir / "pipelines").mkdir(exist_ok=True)
        (self.data_dir / "baselines").mkdir(exist_ok=True)
        (self.data_dir / "baselines" / "agents").mkdir(exist_ok=True)
        (self.data_dir / "baselines" / "pipelines").mkdir(exist_ok=True)
    
    # 文件路径解析器
    def resolve_testset_path(self, entity_type: str, entity_id: str, 
                           testset_name: str) -> Path:
        """解析测试集文件路径"""
        testsets_dir = self.get_entity_testsets_dir(entity_type, entity_id)
        
        # 如果 testset_name 是相对路径，相对于 testsets_dir
        if not testset_name.startswith('/'):
            return testsets_dir / testset_name
        else:
            return Path(testset_name)
    
    def resolve_run_output_path(self, entity_type: str, entity_id: str,
                              variant: str, timestamp: Optional[str] = None,
                              extension: str = "csv") -> Path:
        """解析运行结果输出路径"""
        if timestamp is None:
            timestamp = self.generate_timestamp()
        
        runs_dir = self.get_entity_runs_dir(entity_type, entity_id)
        filename = f"{entity_id}.{variant}.{timestamp}.{extension}"
        return runs_dir / filename
    
    def resolve_eval_output_path(self, entity_type: str, entity_id: str,
                               variant: str, eval_type: str,
                               timestamp: Optional[str] = None,
                               extension: str = "csv") -> Path:
        """解析评估结果输出路径"""
        if timestamp is None:
            timestamp = self.generate_timestamp()
        
        evals_dir = self.get_entity_evals_dir(entity_type, entity_id)
        filename = f"{entity_id}.{variant}.{timestamp}.{eval_type}.{extension}"
        return evals_dir / eval_type / filename
    
    def resolve_baseline_path(self, entity_type: str, entity_id: str,
                            baseline_name: str) -> Path:
        """解析基线快照路径"""
        baselines_dir = self.get_baselines_dir(entity_type)
        filename = f"{entity_id}.{baseline_name}.snapshot.json"
        return baselines_dir / entity_id / filename
    
    # 兼容性方法 - 支持旧路径结构
    def get_legacy_agent_runs_dir(self, agent_id: str) -> Path:
        """获取旧结构的 agent 运行目录"""
        return self.data_dir / "runs" / agent_id
    
    def get_legacy_agent_evals_dir(self, agent_id: str) -> Path:
        """获取旧结构的 agent 评估目录"""
        return self.data_dir / "evals" / agent_id
    
    def get_legacy_agent_testsets_dir(self, agent_id: str) -> Path:
        """获取旧结构的 agent 测试集目录"""
        return self.data_dir / "testsets" / agent_id
    
    def find_testset_file(self, entity_type: str, entity_id: str, 
                         testset_name: str) -> Optional[Path]:
        """查找测试集文件，支持新旧结构"""
        # 首先尝试新结构
        new_path = self.resolve_testset_path(entity_type, entity_id, testset_name)
        if new_path.exists():
            return new_path
        
        # 如果是 agent，尝试旧结构
        if entity_type == "agent":
            legacy_path = self.get_legacy_agent_testsets_dir(entity_id) / testset_name
            if legacy_path.exists():
                return legacy_path
        
        # 尝试相对于项目根目录的路径
        root_relative_path = self.root_dir / testset_name
        if root_relative_path.exists():
            return root_relative_path
        
        return None
    
    @staticmethod
    def generate_timestamp() -> str:
        """生成 ISO 格式时间戳"""
        return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    
    @staticmethod
    def parse_timestamp(timestamp_str: str) -> datetime:
        """解析时间戳字符串"""
        return datetime.strptime(timestamp_str, "%Y-%m-%dT%H-%M-%S")
    
    # 文件命名和版本管理
    def generate_run_filename(self, entity_id: str, variant: str, 
                            timestamp: Optional[str] = None,
                            extension: str = "csv") -> str:
        """生成标准化的运行结果文件名"""
        if timestamp is None:
            timestamp = self.generate_timestamp()
        return f"{entity_id}.{variant}.{timestamp}.{extension}"
    
    def generate_eval_filename(self, entity_id: str, variant: str, 
                             eval_type: str, timestamp: Optional[str] = None,
                             extension: str = "csv") -> str:
        """生成标准化的评估结果文件名"""
        if timestamp is None:
            timestamp = self.generate_timestamp()
        return f"{entity_id}.{variant}.{timestamp}.{eval_type}.{extension}"
    
    def generate_baseline_filename(self, entity_id: str, baseline_name: str) -> str:
        """生成标准化的基线快照文件名"""
        return f"{entity_id}.{baseline_name}.snapshot.json"
    
    def check_file_exists(self, file_path: Path) -> bool:
        """检查文件是否存在"""
        return file_path.exists()
    
    def create_backup_if_exists(self, file_path: Path) -> Optional[Path]:
        """如果文件存在，创建备份"""
        if not file_path.exists():
            return None
        
        timestamp = self.generate_timestamp()
        backup_path = file_path.with_suffix(f".backup.{timestamp}{file_path.suffix}")
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def list_files_by_pattern(self, directory: Path, entity_id: str, 
                            variant: Optional[str] = None,
                            eval_type: Optional[str] = None) -> List[Path]:
        """根据模式列出文件"""
        if not directory.exists():
            return []
        
        pattern_parts = [entity_id]
        if variant:
            pattern_parts.append(variant)
        if eval_type:
            pattern_parts.append("*")  # timestamp
            pattern_parts.append(eval_type)
        
        pattern = ".".join(pattern_parts) + ".*"
        return list(directory.glob(pattern))
    
    # 文件元数据管理
    def create_file_metadata(self, file_path: Path, creator: str = None,
                           description: str = None, 
                           additional_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """创建文件元数据"""
        metadata = {
            "file_path": str(file_path),
            "created_at": datetime.now().isoformat(),
            "creator": creator or os.getenv("USER", "unknown"),
            "description": description or "",
            "file_size": file_path.stat().st_size if file_path.exists() else 0,
            "version": "1.0"
        }
        
        if additional_info:
            metadata.update(additional_info)
        
        return metadata
    
    def save_file_metadata(self, file_path: Path, metadata: Dict[str, Any]) -> Path:
        """保存文件元数据到 .meta.json 文件"""
        meta_path = file_path.with_suffix(file_path.suffix + ".meta.json")
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        return meta_path
    
    def load_file_metadata(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """加载文件元数据"""
        meta_path = file_path.with_suffix(file_path.suffix + ".meta.json")
        if not meta_path.exists():
            return None
        
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None
    
    def create_and_save_file_with_metadata(self, file_path: Path, 
                                         creator: str = None,
                                         description: str = None,
                                         additional_info: Dict[str, Any] = None) -> Path:
        """创建文件并保存元数据"""
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 如果文件已存在，创建备份
        backup_path = self.create_backup_if_exists(file_path)
        if backup_path:
            print(f"文件已存在，已创建备份: {backup_path}")
        
        # 创建元数据
        metadata = self.create_file_metadata(
            file_path, creator, description, additional_info
        )
        
        # 保存元数据
        self.save_file_metadata(file_path, metadata)
        
        return file_path
    
    # 文件版本管理
    def get_file_versions(self, file_path: Path) -> List[Path]:
        """获取文件的所有版本（包括备份）"""
        versions = []
        
        # 原文件
        if file_path.exists():
            versions.append(file_path)
        
        # 备份文件
        backup_pattern = f"{file_path.stem}.backup.*{file_path.suffix}"
        backup_files = list(file_path.parent.glob(backup_pattern))
        versions.extend(sorted(backup_files, reverse=True))
        
        return versions
    
    def cleanup_old_versions(self, file_path: Path, keep_versions: int = 5) -> List[Path]:
        """清理旧版本文件，保留指定数量的版本"""
        versions = self.get_file_versions(file_path)
        
        if len(versions) <= keep_versions:
            return []
        
        # 删除多余的版本
        to_delete = versions[keep_versions:]
        deleted_files = []
        
        for old_file in to_delete:
            try:
                old_file.unlink()
                # 同时删除元数据文件
                meta_file = old_file.with_suffix(old_file.suffix + ".meta.json")
                if meta_file.exists():
                    meta_file.unlink()
                deleted_files.append(old_file)
            except OSError as e:
                print(f"删除文件失败 {old_file}: {e}")
        
        return deleted_files


# 全局实例
data_manager = DataManager()


# 便捷函数
def ensure_agent_dirs(agent_id: str) -> None:
    """确保 agent 目录存在"""
    data_manager.ensure_entity_dirs("agent", agent_id)


def ensure_pipeline_dirs(pipeline_id: str) -> None:
    """确保 pipeline 目录存在"""
    data_manager.ensure_entity_dirs("pipeline", pipeline_id)


def get_agent_testsets_dir(agent_id: str) -> Path:
    """获取 agent 测试集目录"""
    return data_manager.get_entity_testsets_dir("agent", agent_id)


def get_agent_runs_dir(agent_id: str) -> Path:
    """获取 agent 运行结果目录"""
    return data_manager.get_entity_runs_dir("agent", agent_id)


def get_agent_evals_dir(agent_id: str) -> Path:
    """获取 agent 评估结果目录"""
    return data_manager.get_entity_evals_dir("agent", agent_id)


def get_pipeline_testsets_dir(pipeline_id: str) -> Path:
    """获取 pipeline 测试集目录"""
    return data_manager.get_entity_testsets_dir("pipeline", pipeline_id)


def get_pipeline_runs_dir(pipeline_id: str) -> Path:
    """获取 pipeline 运行结果目录"""
    return data_manager.get_entity_runs_dir("pipeline", pipeline_id)


def get_pipeline_evals_dir(pipeline_id: str) -> Path:
    """获取 pipeline 评估结果目录"""
    return data_manager.get_entity_evals_dir("pipeline", pipeline_id)


# 文件命名便捷函数
def generate_run_filename(entity_id: str, variant: str, 
                        timestamp: Optional[str] = None) -> str:
    """生成运行结果文件名"""
    return data_manager.generate_run_filename(entity_id, variant, timestamp)


def generate_eval_filename(entity_id: str, variant: str, eval_type: str,
                         timestamp: Optional[str] = None) -> str:
    """生成评估结果文件名"""
    return data_manager.generate_eval_filename(entity_id, variant, eval_type, timestamp)


def generate_baseline_filename(entity_id: str, baseline_name: str) -> str:
    """生成基线快照文件名"""
    return data_manager.generate_baseline_filename(entity_id, baseline_name)


def create_timestamped_file(base_path: Path, entity_id: str, variant: str,
                          creator: str = None, description: str = None) -> Path:
    """创建带时间戳的文件并保存元数据"""
    timestamp = data_manager.generate_timestamp()
    filename = data_manager.generate_run_filename(entity_id, variant, timestamp)
    file_path = base_path / filename
    
    return data_manager.create_and_save_file_with_metadata(
        file_path, creator, description
    )


def backup_important_file(file_path: Path) -> Optional[Path]:
    """备份重要文件"""
    return data_manager.create_backup_if_exists(file_path)


def cleanup_old_files(directory: Path, entity_id: str, keep_versions: int = 5) -> None:
    """清理目录中的旧文件版本"""
    if not directory.exists():
        return
    
    # 查找该实体的所有文件
    pattern = f"{entity_id}.*"
    files = list(directory.glob(pattern))
    
    # 按文件名分组（去除时间戳部分）
    file_groups = {}
    for file_path in files:
        if ".backup." in file_path.name:
            continue  # 跳过备份文件，它们会被单独处理
        
        # 提取基础名称（去除时间戳）
        parts = file_path.stem.split('.')
        if len(parts) >= 3:  # entity_id.variant.timestamp
            base_name = '.'.join(parts[:2])  # entity_id.variant
            if base_name not in file_groups:
                file_groups[base_name] = []
            file_groups[base_name].append(file_path)
    
    # 对每组文件进行清理
    for base_name, group_files in file_groups.items():
        # 按修改时间排序，保留最新的
        group_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        if len(group_files) > keep_versions:
            for old_file in group_files[keep_versions:]:
                data_manager.cleanup_old_versions(old_file, 1)  # 只保留1个版本，即删除