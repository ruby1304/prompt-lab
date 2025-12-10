# src/baseline_manager.py
"""
Baseline 管理系统

提供 baseline 配置和快照的保存、加载、管理功能，
支持 agent 和 pipeline 级别的 baseline 管理。
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from .data_manager import DataManager
from .models import EvaluationResult, ComparisonReport


@dataclass
class BaselineSnapshot:
    """Baseline 快照数据结构"""
    entity_type: str  # "agent" or "pipeline"
    entity_id: str
    baseline_name: str
    description: str
    created_at: datetime
    creator: str
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    configuration: Dict[str, Any] = field(default_factory=dict)
    evaluation_results: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "baseline_name": self.baseline_name,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
            "creator": self.creator,
            "performance_metrics": self.performance_metrics,
            "configuration": self.configuration,
            "evaluation_results": self.evaluation_results,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> BaselineSnapshot:
        """从字典创建 BaselineSnapshot 实例"""
        created_at = datetime.now()
        if "created_at" in data:
            try:
                created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass
        
        return cls(
            entity_type=data.get("entity_type", ""),
            entity_id=data.get("entity_id", ""),
            baseline_name=data.get("baseline_name", ""),
            description=data.get("description", ""),
            created_at=created_at,
            creator=data.get("creator", ""),
            performance_metrics=data.get("performance_metrics", {}),
            configuration=data.get("configuration", {}),
            evaluation_results=data.get("evaluation_results", []),
            metadata=data.get("metadata", {})
        )


class BaselineManager:
    """Baseline 管理器"""
    
    def __init__(self, data_manager: Optional[DataManager] = None):
        self.data_manager = data_manager or DataManager()
        self.data_manager.initialize_data_structure()
    
    def save_baseline(self, entity_type: str, entity_id: str, baseline_name: str,
                     description: str = "", creator: str = "",
                     performance_metrics: Optional[Dict[str, float]] = None,
                     configuration: Optional[Dict[str, Any]] = None,
                     evaluation_results: Optional[List[EvaluationResult]] = None,
                     metadata: Optional[Dict[str, Any]] = None) -> Path:
        """
        保存 baseline 快照
        
        Args:
            entity_type: 实体类型 ("agent" 或 "pipeline")
            entity_id: 实体 ID
            baseline_name: baseline 名称
            description: 描述信息
            creator: 创建者
            performance_metrics: 性能指标
            configuration: 配置信息
            evaluation_results: 评估结果列表
            metadata: 额外元数据
            
        Returns:
            保存的文件路径
        """
        if entity_type not in ["agent", "pipeline"]:
            raise ValueError(f"不支持的实体类型: {entity_type}")
        
        # 创建快照对象
        snapshot = BaselineSnapshot(
            entity_type=entity_type,
            entity_id=entity_id,
            baseline_name=baseline_name,
            description=description,
            created_at=datetime.now(),
            creator=creator or "unknown",
            performance_metrics=performance_metrics or {},
            configuration=configuration or {},
            evaluation_results=[],
            metadata=metadata or {}
        )
        
        # 处理评估结果
        if evaluation_results:
            snapshot.evaluation_results = [
                result.to_dict() if isinstance(result, EvaluationResult) else result
                for result in evaluation_results
            ]
        
        # 获取保存路径
        baseline_path = self.data_manager.resolve_baseline_path(
            entity_type, entity_id, baseline_name
        )
        
        # 确保目录存在
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 如果文件已存在，创建备份
        if baseline_path.exists():
            backup_path = self.data_manager.create_backup_if_exists(baseline_path)
            if backup_path:
                print(f"已存在的 baseline 已备份至: {backup_path}")
        
        # 保存快照
        with open(baseline_path, 'w', encoding='utf-8') as f:
            json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)
        
        # 创建元数据文件
        metadata_info = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "baseline_name": baseline_name,
            "description": description,
            "creator": creator,
            "performance_summary": self._summarize_performance(performance_metrics or {})
        }
        self.data_manager.save_file_metadata(baseline_path, metadata_info)
        
        print(f"Baseline '{baseline_name}' 已保存至: {baseline_path}")
        return baseline_path
    
    def load_baseline(self, entity_type: str, entity_id: str, 
                     baseline_name: str) -> Optional[BaselineSnapshot]:
        """
        加载 baseline 快照
        
        Args:
            entity_type: 实体类型
            entity_id: 实体 ID
            baseline_name: baseline 名称
            
        Returns:
            BaselineSnapshot 对象，如果不存在则返回 None
        """
        baseline_path = self.data_manager.resolve_baseline_path(
            entity_type, entity_id, baseline_name
        )
        
        if not baseline_path.exists():
            return None
        
        try:
            with open(baseline_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return BaselineSnapshot.from_dict(data)
        except (json.JSONDecodeError, IOError) as e:
            print(f"加载 baseline 失败 {baseline_path}: {e}")
            return None
    
    def list_baselines(self, entity_type: str, entity_id: str) -> List[Dict[str, Any]]:
        """
        列出指定实体的所有 baseline
        
        Args:
            entity_type: 实体类型
            entity_id: 实体 ID
            
        Returns:
            baseline 信息列表
        """
        baselines_dir = self.data_manager.get_baselines_dir(entity_type) / entity_id
        
        if not baselines_dir.exists():
            return []
        
        baselines = []
        pattern = f"{entity_id}.*.snapshot.json"
        
        for baseline_file in baselines_dir.glob(pattern):
            try:
                # 从文件名提取 baseline 名称
                name_part = baseline_file.stem.replace(f"{entity_id}.", "").replace(".snapshot", "")
                
                # 加载基本信息
                with open(baseline_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                baseline_info = {
                    "baseline_name": name_part,
                    "description": data.get("description", ""),
                    "created_at": data.get("created_at", ""),
                    "creator": data.get("creator", ""),
                    "performance_metrics": data.get("performance_metrics", {}),
                    "file_path": str(baseline_file),
                    "file_size": baseline_file.stat().st_size
                }
                
                baselines.append(baseline_info)
                
            except (json.JSONDecodeError, IOError) as e:
                print(f"读取 baseline 文件失败 {baseline_file}: {e}")
                continue
        
        # 按创建时间排序
        baselines.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return baselines
    
    def delete_baseline(self, entity_type: str, entity_id: str, 
                       baseline_name: str) -> bool:
        """
        删除 baseline 快照
        
        Args:
            entity_type: 实体类型
            entity_id: 实体 ID
            baseline_name: baseline 名称
            
        Returns:
            是否删除成功
        """
        baseline_path = self.data_manager.resolve_baseline_path(
            entity_type, entity_id, baseline_name
        )
        
        if not baseline_path.exists():
            print(f"Baseline '{baseline_name}' 不存在")
            return False
        
        try:
            # 创建备份
            backup_path = self.data_manager.create_backup_if_exists(baseline_path)
            if backup_path:
                print(f"已创建备份: {backup_path}")
            
            # 删除主文件
            baseline_path.unlink()
            
            # 删除元数据文件
            meta_path = baseline_path.with_suffix(baseline_path.suffix + ".meta.json")
            if meta_path.exists():
                meta_path.unlink()
            
            print(f"Baseline '{baseline_name}' 已删除")
            return True
            
        except OSError as e:
            print(f"删除 baseline 失败: {e}")
            return False
    
    def copy_baseline(self, entity_type: str, entity_id: str,
                     source_baseline: str, target_baseline: str,
                     new_description: str = "") -> bool:
        """
        复制 baseline 快照
        
        Args:
            entity_type: 实体类型
            entity_id: 实体 ID
            source_baseline: 源 baseline 名称
            target_baseline: 目标 baseline 名称
            new_description: 新的描述信息
            
        Returns:
            是否复制成功
        """
        # 加载源 baseline
        source_snapshot = self.load_baseline(entity_type, entity_id, source_baseline)
        if not source_snapshot:
            print(f"源 baseline '{source_baseline}' 不存在")
            return False
        
        # 检查目标是否已存在
        target_path = self.data_manager.resolve_baseline_path(
            entity_type, entity_id, target_baseline
        )
        if target_path.exists():
            print(f"目标 baseline '{target_baseline}' 已存在")
            return False
        
        # 创建新的快照
        new_snapshot = BaselineSnapshot(
            entity_type=source_snapshot.entity_type,
            entity_id=source_snapshot.entity_id,
            baseline_name=target_baseline,
            description=new_description or f"复制自 {source_baseline}",
            created_at=datetime.now(),
            creator=source_snapshot.creator,
            performance_metrics=source_snapshot.performance_metrics.copy(),
            configuration=source_snapshot.configuration.copy(),
            evaluation_results=source_snapshot.evaluation_results.copy(),
            metadata=source_snapshot.metadata.copy()
        )
        
        # 保存新快照
        try:
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(new_snapshot.to_dict(), f, ensure_ascii=False, indent=2)
            
            print(f"Baseline 已复制: '{source_baseline}' -> '{target_baseline}'")
            return True
            
        except IOError as e:
            print(f"复制 baseline 失败: {e}")
            return False
    
    def get_baseline_performance(self, entity_type: str, entity_id: str,
                               baseline_name: str) -> Optional[Dict[str, float]]:
        """
        获取 baseline 的性能指标
        
        Args:
            entity_type: 实体类型
            entity_id: 实体 ID
            baseline_name: baseline 名称
            
        Returns:
            性能指标字典，如果不存在则返回 None
        """
        snapshot = self.load_baseline(entity_type, entity_id, baseline_name)
        return snapshot.performance_metrics if snapshot else None
    
    def update_baseline_metadata(self, entity_type: str, entity_id: str,
                               baseline_name: str, 
                               new_description: Optional[str] = None,
                               additional_metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        更新 baseline 元数据
        
        Args:
            entity_type: 实体类型
            entity_id: 实体 ID
            baseline_name: baseline 名称
            new_description: 新的描述信息
            additional_metadata: 额外的元数据
            
        Returns:
            是否更新成功
        """
        snapshot = self.load_baseline(entity_type, entity_id, baseline_name)
        if not snapshot:
            print(f"Baseline '{baseline_name}' 不存在")
            return False
        
        # 更新信息
        if new_description is not None:
            snapshot.description = new_description
        
        if additional_metadata:
            snapshot.metadata.update(additional_metadata)
        
        # 保存更新后的快照
        baseline_path = self.data_manager.resolve_baseline_path(
            entity_type, entity_id, baseline_name
        )
        
        try:
            with open(baseline_path, 'w', encoding='utf-8') as f:
                json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)
            
            print(f"Baseline '{baseline_name}' 元数据已更新")
            return True
            
        except IOError as e:
            print(f"更新 baseline 元数据失败: {e}")
            return False
    
    def validate_baseline(self, entity_type: str, entity_id: str,
                         baseline_name: str) -> List[str]:
        """
        验证 baseline 快照的完整性
        
        Args:
            entity_type: 实体类型
            entity_id: 实体 ID
            baseline_name: baseline 名称
            
        Returns:
            验证错误列表，空列表表示验证通过
        """
        errors = []
        
        snapshot = self.load_baseline(entity_type, entity_id, baseline_name)
        if not snapshot:
            errors.append(f"无法加载 baseline '{baseline_name}'")
            return errors
        
        # 验证基本字段
        if not snapshot.entity_type:
            errors.append("缺少实体类型")
        elif snapshot.entity_type not in ["agent", "pipeline"]:
            errors.append(f"无效的实体类型: {snapshot.entity_type}")
        
        if not snapshot.entity_id:
            errors.append("缺少实体 ID")
        
        if not snapshot.baseline_name:
            errors.append("缺少 baseline 名称")
        
        if not snapshot.creator:
            errors.append("缺少创建者信息")
        
        # 验证性能指标
        if not snapshot.performance_metrics:
            errors.append("缺少性能指标")
        else:
            for metric, value in snapshot.performance_metrics.items():
                if not isinstance(value, (int, float)):
                    errors.append(f"性能指标 '{metric}' 的值不是数字: {value}")
        
        # 验证评估结果
        if snapshot.evaluation_results:
            for i, result in enumerate(snapshot.evaluation_results):
                if not isinstance(result, dict):
                    errors.append(f"评估结果 {i} 不是字典格式")
                elif "sample_id" not in result:
                    errors.append(f"评估结果 {i} 缺少 sample_id")
        
        return errors
    
    def _summarize_performance(self, metrics: Dict[str, float]) -> str:
        """生成性能指标摘要"""
        if not metrics:
            return "无性能数据"
        
        summary_parts = []
        
        # 常见指标的中文名称映射
        metric_names = {
            "overall_score": "总体评分",
            "must_have_pass_rate": "必要条件通过率",
            "rule_violation_rate": "规则违反率",
            "avg_execution_time": "平均执行时间",
            "sample_count": "样本数量"
        }
        
        for metric, value in metrics.items():
            display_name = metric_names.get(metric, metric)
            if isinstance(value, float):
                if metric.endswith("_rate"):
                    summary_parts.append(f"{display_name}: {value:.1%}")
                elif metric.endswith("_time"):
                    summary_parts.append(f"{display_name}: {value:.2f}s")
                else:
                    summary_parts.append(f"{display_name}: {value:.2f}")
            else:
                summary_parts.append(f"{display_name}: {value}")
        
        return ", ".join(summary_parts)
    
    def export_baseline(self, entity_type: str, entity_id: str,
                       baseline_name: str, export_path: Path) -> bool:
        """
        导出 baseline 快照到指定路径
        
        Args:
            entity_type: 实体类型
            entity_id: 实体 ID
            baseline_name: baseline 名称
            export_path: 导出路径
            
        Returns:
            是否导出成功
        """
        snapshot = self.load_baseline(entity_type, entity_id, baseline_name)
        if not snapshot:
            print(f"Baseline '{baseline_name}' 不存在")
            return False
        
        try:
            export_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)
            
            print(f"Baseline 已导出至: {export_path}")
            return True
            
        except IOError as e:
            print(f"导出 baseline 失败: {e}")
            return False
    
    def import_baseline(self, import_path: Path, 
                       target_entity_type: Optional[str] = None,
                       target_entity_id: Optional[str] = None,
                       target_baseline_name: Optional[str] = None) -> bool:
        """
        从指定路径导入 baseline 快照
        
        Args:
            import_path: 导入路径
            target_entity_type: 目标实体类型（可选，使用文件中的值）
            target_entity_id: 目标实体 ID（可选，使用文件中的值）
            target_baseline_name: 目标 baseline 名称（可选，使用文件中的值）
            
        Returns:
            是否导入成功
        """
        if not import_path.exists():
            print(f"导入文件不存在: {import_path}")
            return False
        
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            snapshot = BaselineSnapshot.from_dict(data)
            
            # 使用目标参数覆盖（如果提供）
            if target_entity_type:
                snapshot.entity_type = target_entity_type
            if target_entity_id:
                snapshot.entity_id = target_entity_id
            if target_baseline_name:
                snapshot.baseline_name = target_baseline_name
            
            # 更新创建时间
            snapshot.created_at = datetime.now()
            
            # 保存导入的快照
            return self.save_baseline(
                snapshot.entity_type,
                snapshot.entity_id,
                snapshot.baseline_name,
                snapshot.description,
                snapshot.creator,
                snapshot.performance_metrics,
                snapshot.configuration,
                [EvaluationResult.from_dict(result) for result in snapshot.evaluation_results],
                snapshot.metadata
            ) is not None
            
        except (json.JSONDecodeError, IOError) as e:
            print(f"导入 baseline 失败: {e}")
            return False


# 全局实例
baseline_manager = BaselineManager()


# 便捷函数
def save_agent_baseline(agent_id: str, baseline_name: str, description: str = "",
                       performance_metrics: Optional[Dict[str, float]] = None,
                       evaluation_results: Optional[List[EvaluationResult]] = None) -> Path:
    """保存 agent baseline"""
    return baseline_manager.save_baseline(
        "agent", agent_id, baseline_name, description,
        performance_metrics=performance_metrics,
        evaluation_results=evaluation_results
    )


def save_pipeline_baseline(pipeline_id: str, baseline_name: str, description: str = "",
                          performance_metrics: Optional[Dict[str, float]] = None,
                          evaluation_results: Optional[List[EvaluationResult]] = None) -> Path:
    """保存 pipeline baseline"""
    return baseline_manager.save_baseline(
        "pipeline", pipeline_id, baseline_name, description,
        performance_metrics=performance_metrics,
        evaluation_results=evaluation_results
    )


def load_agent_baseline(agent_id: str, baseline_name: str) -> Optional[BaselineSnapshot]:
    """加载 agent baseline"""
    return baseline_manager.load_baseline("agent", agent_id, baseline_name)


def load_pipeline_baseline(pipeline_id: str, baseline_name: str) -> Optional[BaselineSnapshot]:
    """加载 pipeline baseline"""
    return baseline_manager.load_baseline("pipeline", pipeline_id, baseline_name)


def list_agent_baselines(agent_id: str) -> List[Dict[str, Any]]:
    """列出 agent 的所有 baseline"""
    return baseline_manager.list_baselines("agent", agent_id)


def list_pipeline_baselines(pipeline_id: str) -> List[Dict[str, Any]]:
    """列出 pipeline 的所有 baseline"""
    return baseline_manager.list_baselines("pipeline", pipeline_id)