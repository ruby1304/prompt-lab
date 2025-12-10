# src/checkpoint_manager.py
"""
断点续传和错误恢复机制

提供执行状态保存和恢复功能，支持从失败步骤继续执行，
确保不丢失已完成的工作。
"""

from __future__ import annotations

import json
import pickle
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

from .models import PipelineConfig
# Import types at runtime to avoid circular imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .pipeline_runner import PipelineResult, StepResult
from .data_manager import get_pipeline_runs_dir


class CheckpointStatus(Enum):
    """检查点状态"""
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionCheckpoint:
    """执行检查点数据"""
    # 基本信息
    checkpoint_id: str
    pipeline_id: str
    variant: str
    status: CheckpointStatus
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    # 执行配置
    total_samples: int = 0
    completed_samples: int = 0
    failed_samples: int = 0
    
    # 样本和结果
    sample_hashes: List[str] = field(default_factory=list)  # 样本内容的哈希值
    completed_results: List[Dict[str, Any]] = field(default_factory=list)  # 已完成的结果
    failed_sample_indices: List[int] = field(default_factory=list)  # 失败的样本索引
    
    # 错误信息
    last_error: Optional[str] = None
    error_count: int = 0
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        data = asdict(self)
        data["status"] = self.status.value
        data["created_at"] = self.created_at.isoformat()
        data["updated_at"] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutionCheckpoint:
        """从字典创建检查点"""
        data = data.copy()
        data["status"] = CheckpointStatus(data["status"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)


class CheckpointManager:
    """检查点管理器"""
    
    def __init__(self, pipeline_id: str, variant: str = "baseline"):
        """
        初始化检查点管理器
        
        Args:
            pipeline_id: Pipeline ID
            variant: 变体名称
        """
        self.pipeline_id = pipeline_id
        self.variant = variant
        self.checkpoint_dir = get_pipeline_runs_dir(pipeline_id) / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成检查点ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.checkpoint_id = f"{pipeline_id}_{variant}_{timestamp}"
        self.checkpoint_file = self.checkpoint_dir / f"{self.checkpoint_id}.json"
        
        self.checkpoint: Optional[ExecutionCheckpoint] = None
    
    def create_checkpoint(self, 
                         samples: List[Dict[str, Any]], 
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        创建新的检查点
        
        Args:
            samples: 测试样本列表
            metadata: 额外的元数据
            
        Returns:
            检查点ID
        """
        # 计算样本哈希值
        sample_hashes = []
        for sample in samples:
            sample_str = json.dumps(sample, sort_keys=True, ensure_ascii=False)
            sample_hash = hashlib.md5(sample_str.encode('utf-8')).hexdigest()
            sample_hashes.append(sample_hash)
        
        # 创建检查点
        self.checkpoint = ExecutionCheckpoint(
            checkpoint_id=self.checkpoint_id,
            pipeline_id=self.pipeline_id,
            variant=self.variant,
            status=CheckpointStatus.RUNNING,
            total_samples=len(samples),
            sample_hashes=sample_hashes,
            metadata=metadata or {}
        )
        
        # 保存检查点
        self._save_checkpoint()
        
        return self.checkpoint_id
    
    def update_checkpoint(self, 
                         completed_sample_index: int,
                         result: Any,  # PipelineResult
                         failed: bool = False,
                         error_message: Optional[str] = None):
        """
        更新检查点状态
        
        Args:
            completed_sample_index: 完成的样本索引
            result: Pipeline 执行结果
            failed: 是否失败
            error_message: 错误消息
        """
        if not self.checkpoint:
            raise ValueError("检查点未初始化")
        
        self.checkpoint.updated_at = datetime.now()
        
        if failed:
            self.checkpoint.failed_samples += 1
            self.checkpoint.failed_sample_indices.append(completed_sample_index)
            if error_message:
                self.checkpoint.last_error = error_message
                self.checkpoint.error_count += 1
        else:
            self.checkpoint.completed_samples += 1
            # 保存结果（转换为字典格式）
            self.checkpoint.completed_results.append(result.to_dict())
        
        # 保存检查点
        self._save_checkpoint()
    
    def complete_checkpoint(self, success: bool = True):
        """
        完成检查点
        
        Args:
            success: 是否成功完成
        """
        if not self.checkpoint:
            return
        
        self.checkpoint.status = CheckpointStatus.COMPLETED if success else CheckpointStatus.FAILED
        self.checkpoint.updated_at = datetime.now()
        
        # 保存最终检查点
        self._save_checkpoint()
    
    def load_checkpoint(self, checkpoint_id: str) -> Optional[ExecutionCheckpoint]:
        """
        加载检查点
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            检查点数据，如果不存在则返回None
        """
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        
        if not checkpoint_file.exists():
            return None
        
        try:
            with open(checkpoint_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.checkpoint = ExecutionCheckpoint.from_dict(data)
            self.checkpoint_id = checkpoint_id
            self.checkpoint_file = checkpoint_file
            
            return self.checkpoint
            
        except Exception as e:
            print(f"加载检查点失败: {e}")
            return None
    
    def find_resumable_checkpoint(self) -> Optional[str]:
        """
        查找可恢复的检查点
        
        Returns:
            可恢复的检查点ID，如果没有则返回None
        """
        if not self.checkpoint_dir.exists():
            return None
        
        # 查找相同pipeline和variant的运行中检查点
        pattern = f"{self.pipeline_id}_{self.variant}_*.json"
        checkpoint_files = list(self.checkpoint_dir.glob(pattern))
        
        # 按创建时间排序，最新的在前
        checkpoint_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        for checkpoint_file in checkpoint_files:
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                checkpoint = ExecutionCheckpoint.from_dict(data)
                
                # 只考虑运行中的检查点
                if checkpoint.status == CheckpointStatus.RUNNING:
                    return checkpoint.checkpoint_id
                    
            except Exception:
                continue
        
        return None
    
    def get_resume_info(self) -> Optional[Dict[str, Any]]:
        """
        获取恢复信息
        
        Returns:
            恢复信息字典，包含已完成的样本索引等
        """
        if not self.checkpoint:
            return None
        
        completed_indices = set(range(self.checkpoint.completed_samples))
        failed_indices = set(self.checkpoint.failed_sample_indices)
        
        # 需要重新执行的样本索引
        remaining_indices = []
        for i in range(self.checkpoint.total_samples):
            if i not in completed_indices:
                remaining_indices.append(i)
        
        return {
            "total_samples": self.checkpoint.total_samples,
            "completed_samples": self.checkpoint.completed_samples,
            "failed_samples": self.checkpoint.failed_samples,
            "completed_indices": list(completed_indices),
            "failed_indices": list(failed_indices),
            "remaining_indices": remaining_indices,
            "completed_results": self.checkpoint.completed_results,
            "last_error": self.checkpoint.last_error,
            "error_count": self.checkpoint.error_count
        }
    
    def validate_samples(self, samples: List[Dict[str, Any]]) -> bool:
        """
        验证样本是否与检查点匹配
        
        Args:
            samples: 当前样本列表
            
        Returns:
            是否匹配
        """
        if not self.checkpoint:
            return False
        
        if len(samples) != len(self.checkpoint.sample_hashes):
            return False
        
        # 计算当前样本的哈希值并比较
        for i, sample in enumerate(samples):
            sample_str = json.dumps(sample, sort_keys=True, ensure_ascii=False)
            sample_hash = hashlib.md5(sample_str.encode('utf-8')).hexdigest()
            
            if sample_hash != self.checkpoint.sample_hashes[i]:
                return False
        
        return True
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        列出所有检查点
        
        Returns:
            检查点信息列表
        """
        if not self.checkpoint_dir.exists():
            return []
        
        checkpoints = []
        pattern = f"{self.pipeline_id}_*.json"
        
        for checkpoint_file in self.checkpoint_dir.glob(pattern):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                checkpoint = ExecutionCheckpoint.from_dict(data)
                
                checkpoints.append({
                    "checkpoint_id": checkpoint.checkpoint_id,
                    "variant": checkpoint.variant,
                    "status": checkpoint.status.value,
                    "created_at": checkpoint.created_at.isoformat(),
                    "updated_at": checkpoint.updated_at.isoformat(),
                    "total_samples": checkpoint.total_samples,
                    "completed_samples": checkpoint.completed_samples,
                    "failed_samples": checkpoint.failed_samples,
                    "progress": f"{checkpoint.completed_samples}/{checkpoint.total_samples}",
                    "success_rate": f"{(checkpoint.completed_samples - checkpoint.failed_samples)/checkpoint.total_samples*100:.1f}%" if checkpoint.total_samples > 0 else "0%"
                })
                
            except Exception:
                continue
        
        # 按创建时间排序
        checkpoints.sort(key=lambda x: x["created_at"], reverse=True)
        
        return checkpoints
    
    def cleanup_old_checkpoints(self, keep_count: int = 10):
        """
        清理旧的检查点文件
        
        Args:
            keep_count: 保留的检查点数量
        """
        if not self.checkpoint_dir.exists():
            return
        
        pattern = f"{self.pipeline_id}_*.json"
        checkpoint_files = list(self.checkpoint_dir.glob(pattern))
        
        # 按修改时间排序，最新的在前
        checkpoint_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # 删除多余的检查点文件
        for checkpoint_file in checkpoint_files[keep_count:]:
            try:
                checkpoint_file.unlink()
            except Exception:
                pass
    
    def _save_checkpoint(self):
        """保存检查点到文件"""
        if not self.checkpoint:
            return
        
        try:
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(self.checkpoint.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存检查点失败: {e}")


class ResumableExecutor:
    """可恢复的执行器"""
    
    def __init__(self, pipeline_runner, checkpoint_manager: CheckpointManager):
        """
        初始化可恢复执行器
        
        Args:
            pipeline_runner: Pipeline 执行器
            checkpoint_manager: 检查点管理器
        """
        self.pipeline_runner = pipeline_runner
        self.checkpoint_manager = checkpoint_manager
    
    def execute_with_resume(self, 
                           samples: List[Dict[str, Any]], 
                           variant: str = "baseline",
                           auto_resume: bool = True,
                           max_retries: int = 3) -> List[Any]:
        """
        执行 Pipeline 并支持断点续传
        
        Args:
            samples: 测试样本列表
            variant: 变体名称
            auto_resume: 是否自动恢复
            max_retries: 最大重试次数
            
        Returns:
            Pipeline 执行结果列表
        """
        # 尝试查找可恢复的检查点
        resumable_checkpoint_id = None
        if auto_resume:
            resumable_checkpoint_id = self.checkpoint_manager.find_resumable_checkpoint()
        
        if resumable_checkpoint_id:
            print(f"发现可恢复的检查点: {resumable_checkpoint_id}")
            return self._resume_execution(samples, resumable_checkpoint_id, max_retries)
        else:
            print("开始新的执行")
            return self._start_new_execution(samples, variant, max_retries)
    
    def _start_new_execution(self, 
                           samples: List[Dict[str, Any]], 
                           variant: str,
                           max_retries: int) -> List[Any]:
        """开始新的执行"""
        # 创建检查点
        checkpoint_id = self.checkpoint_manager.create_checkpoint(samples)
        print(f"创建检查点: {checkpoint_id}")
        
        results = []
        retry_count = 0
        
        try:
            for i, sample in enumerate(samples):
                sample_id = sample.get("id", f"sample_{i}")
                
                # 执行样本，支持重试
                while retry_count < max_retries:
                    try:
                        result = self.pipeline_runner.execute_sample(sample, variant)
                        
                        # 更新检查点
                        failed = bool(result.error)
                        self.checkpoint_manager.update_checkpoint(
                            completed_sample_index=i,
                            result=result,
                            failed=failed,
                            error_message=result.error
                        )
                        
                        results.append(result)
                        retry_count = 0  # 重置重试计数
                        break
                        
                    except Exception as e:
                        retry_count += 1
                        error_msg = f"样本 {sample_id} 执行失败 (重试 {retry_count}/{max_retries}): {str(e)}"
                        print(error_msg)
                        
                        if retry_count >= max_retries:
                            # 创建错误结果
                            from .pipeline_runner import PipelineResult
                            error_result = PipelineResult(
                                sample_id=sample_id,
                                variant=variant,
                                error=error_msg
                            )
                            
                            # 更新检查点
                            self.checkpoint_manager.update_checkpoint(
                                completed_sample_index=i,
                                result=error_result,
                                failed=True,
                                error_message=error_msg
                            )
                            
                            results.append(error_result)
                            retry_count = 0  # 重置重试计数
            
            # 完成检查点
            self.checkpoint_manager.complete_checkpoint(success=True)
            
        except Exception as e:
            print(f"执行过程中出现严重错误: {e}")
            self.checkpoint_manager.complete_checkpoint(success=False)
            raise
        
        return results
    
    def _resume_execution(self, 
                         samples: List[Dict[str, Any]], 
                         checkpoint_id: str,
                         max_retries: int) -> List[Any]:
        """恢复执行"""
        # 加载检查点
        checkpoint = self.checkpoint_manager.load_checkpoint(checkpoint_id)
        if not checkpoint:
            raise ValueError(f"无法加载检查点: {checkpoint_id}")
        
        # 验证样本是否匹配
        if not self.checkpoint_manager.validate_samples(samples):
            print("警告: 当前样本与检查点中的样本不匹配，将开始新的执行")
            return self._start_new_execution(samples, checkpoint.variant, max_retries)
        
        # 获取恢复信息
        resume_info = self.checkpoint_manager.get_resume_info()
        if not resume_info:
            raise ValueError("无法获取恢复信息")
        
        print(f"恢复执行: 已完成 {resume_info['completed_samples']}/{resume_info['total_samples']} 个样本")
        
        # 重建已完成的结果
        results = []
        for result_data in resume_info["completed_results"]:
            # 动态导入以避免循环依赖
            from .pipeline_runner import PipelineResult, StepResult
            
            # 从字典重建 PipelineResult
            result = PipelineResult(
                sample_id=result_data["sample_id"],
                variant=result_data["variant"],
                total_execution_time=result_data["total_execution_time"],
                total_token_usage=result_data["total_token_usage"],
                final_outputs=result_data["final_outputs"],
                error=result_data.get("error"),
                created_at=datetime.fromisoformat(result_data["created_at"])
            )
            
            # 重建步骤结果
            for step_data in result_data["step_results"]:
                step_result = StepResult(
                    step_id=step_data["step_id"],
                    output_key=step_data["output_key"],
                    output_value=step_data["output_value"],
                    execution_time=step_data["execution_time"],
                    token_usage=step_data["token_usage"],
                    error=step_data.get("error")
                )
                result.step_results.append(step_result)
            
            results.append(result)
        
        # 继续执行剩余的样本
        retry_count = 0
        
        try:
            for i in resume_info["remaining_indices"]:
                sample = samples[i]
                sample_id = sample.get("id", f"sample_{i}")
                
                # 执行样本，支持重试
                while retry_count < max_retries:
                    try:
                        result = self.pipeline_runner.execute_sample(sample, checkpoint.variant)
                        
                        # 更新检查点
                        failed = bool(result.error)
                        self.checkpoint_manager.update_checkpoint(
                            completed_sample_index=i,
                            result=result,
                            failed=failed,
                            error_message=result.error
                        )
                        
                        results.append(result)
                        retry_count = 0  # 重置重试计数
                        break
                        
                    except Exception as e:
                        retry_count += 1
                        error_msg = f"样本 {sample_id} 执行失败 (重试 {retry_count}/{max_retries}): {str(e)}"
                        print(error_msg)
                        
                        if retry_count >= max_retries:
                            # 创建错误结果
                            from .pipeline_runner import PipelineResult
                            error_result = PipelineResult(
                                sample_id=sample_id,
                                variant=checkpoint.variant,
                                error=error_msg
                            )
                            
                            # 更新检查点
                            self.checkpoint_manager.update_checkpoint(
                                completed_sample_index=i,
                                result=error_result,
                                failed=True,
                                error_message=error_msg
                            )
                            
                            results.append(error_result)
                            retry_count = 0  # 重置重试计数
            
            # 完成检查点
            self.checkpoint_manager.complete_checkpoint(success=True)
            
        except Exception as e:
            print(f"恢复执行过程中出现严重错误: {e}")
            self.checkpoint_manager.complete_checkpoint(success=False)
            raise
        
        # 按原始顺序排序结果
        results.sort(key=lambda r: samples.index(next(s for s in samples if s.get("id", f"sample_{samples.index(s)}") == r.sample_id)))
        
        return results