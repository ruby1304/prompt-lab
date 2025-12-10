# tests/test_baseline_manager.py
"""
BaselineManager 单元测试
"""

import pytest
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, mock_open

from src.baseline_manager import (
    BaselineManager, BaselineSnapshot, 
    save_agent_baseline, save_pipeline_baseline,
    load_agent_baseline, load_pipeline_baseline,
    list_agent_baselines, list_pipeline_baselines
)
from src.models import EvaluationResult


class TestBaselineSnapshot:
    """测试 BaselineSnapshot 类"""
    
    def test_baseline_snapshot_creation(self):
        """测试 BaselineSnapshot 创建"""
        snapshot = BaselineSnapshot(
            entity_type="agent",
            entity_id="test_agent",
            baseline_name="baseline_v1",
            description="测试基线",
            created_at=datetime.now(),
            creator="test_user"
        )
        
        assert snapshot.entity_type == "agent"
        assert snapshot.entity_id == "test_agent"
        assert snapshot.baseline_name == "baseline_v1"
        assert snapshot.description == "测试基线"
        assert snapshot.creator == "test_user"
        assert isinstance(snapshot.created_at, datetime)
        assert snapshot.performance_metrics == {}
        assert snapshot.configuration == {}
        assert snapshot.evaluation_results == []
        assert snapshot.metadata == {}
    
    def test_baseline_snapshot_to_dict(self):
        """测试 BaselineSnapshot 转换为字典"""
        created_at = datetime.now()
        snapshot = BaselineSnapshot(
            entity_type="pipeline",
            entity_id="test_pipeline",
            baseline_name="baseline_v1",
            description="测试基线",
            created_at=created_at,
            creator="test_user",
            performance_metrics={"score": 8.5},
            configuration={"model": "gpt-4"},
            evaluation_results=[{"sample_id": "1", "score": 8.5}],
            metadata={"version": "1.0"}
        )
        
        result_dict = snapshot.to_dict()
        
        assert result_dict["entity_type"] == "pipeline"
        assert result_dict["entity_id"] == "test_pipeline"
        assert result_dict["baseline_name"] == "baseline_v1"
        assert result_dict["description"] == "测试基线"
        assert result_dict["created_at"] == created_at.isoformat()
        assert result_dict["creator"] == "test_user"
        assert result_dict["performance_metrics"]["score"] == 8.5
        assert result_dict["configuration"]["model"] == "gpt-4"
        assert len(result_dict["evaluation_results"]) == 1
        assert result_dict["metadata"]["version"] == "1.0"
    
    def test_baseline_snapshot_from_dict(self):
        """测试从字典创建 BaselineSnapshot"""
        created_at = datetime.now()
        data = {
            "entity_type": "agent",
            "entity_id": "test_agent",
            "baseline_name": "baseline_v1",
            "description": "测试基线",
            "created_at": created_at.isoformat(),
            "creator": "test_user",
            "performance_metrics": {"score": 8.5},
            "configuration": {"model": "gpt-4"},
            "evaluation_results": [{"sample_id": "1", "score": 8.5}],
            "metadata": {"version": "1.0"}
        }
        
        snapshot = BaselineSnapshot.from_dict(data)
        
        assert snapshot.entity_type == "agent"
        assert snapshot.entity_id == "test_agent"
        assert snapshot.baseline_name == "baseline_v1"
        assert snapshot.description == "测试基线"
        assert snapshot.creator == "test_user"
        assert snapshot.performance_metrics["score"] == 8.5
        assert snapshot.configuration["model"] == "gpt-4"
        assert len(snapshot.evaluation_results) == 1
        assert snapshot.metadata["version"] == "1.0"
    
    def test_baseline_snapshot_from_dict_missing_fields(self):
        """测试从不完整字典创建 BaselineSnapshot"""
        data = {
            "entity_type": "agent",
            "entity_id": "test_agent",
            "baseline_name": "baseline_v1"
        }
        
        snapshot = BaselineSnapshot.from_dict(data)
        
        assert snapshot.entity_type == "agent"
        assert snapshot.entity_id == "test_agent"
        assert snapshot.baseline_name == "baseline_v1"
        assert snapshot.description == ""
        assert snapshot.creator == ""
        assert snapshot.performance_metrics == {}
        assert isinstance(snapshot.created_at, datetime)
    
    def test_baseline_snapshot_from_dict_invalid_date(self):
        """测试处理无效日期格式"""
        data = {
            "entity_type": "agent",
            "entity_id": "test_agent",
            "baseline_name": "baseline_v1",
            "created_at": "invalid_date"
        }
        
        snapshot = BaselineSnapshot.from_dict(data)
        
        # 应该使用当前时间作为默认值
        assert isinstance(snapshot.created_at, datetime)


class TestBaselineManager:
    """测试 BaselineManager 类"""
    
    def test_baseline_manager_initialization(self, mock_data_manager):
        """测试 BaselineManager 初始化"""
        manager = BaselineManager(mock_data_manager)
        
        assert manager.data_manager == mock_data_manager
    
    def test_baseline_manager_default_initialization(self):
        """测试 BaselineManager 默认初始化"""
        with patch('src.baseline_manager.DataManager') as mock_dm_class:
            mock_dm = Mock()
            mock_dm_class.return_value = mock_dm
            
            manager = BaselineManager()
            
            mock_dm_class.assert_called_once()
            mock_dm.initialize_data_structure.assert_called_once()
    
    def test_save_baseline_success(self, mock_data_manager, temp_dir):
        """测试成功保存 baseline"""
        manager = BaselineManager(mock_data_manager)
        
        # 模拟路径解析
        baseline_path = temp_dir / "test_agent.baseline_v1.snapshot.json"
        mock_data_manager.resolve_baseline_path.return_value = baseline_path
        mock_data_manager.create_backup_if_exists.return_value = None
        
        # 执行保存
        result_path = manager.save_baseline(
            entity_type="agent",
            entity_id="test_agent",
            baseline_name="baseline_v1",
            description="测试基线",
            creator="test_user",
            performance_metrics={"score": 8.5}
        )
        
        assert result_path == baseline_path
        assert baseline_path.exists()
        
        # 验证文件内容
        with open(baseline_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data["entity_type"] == "agent"
        assert data["entity_id"] == "test_agent"
        assert data["baseline_name"] == "baseline_v1"
        assert data["description"] == "测试基线"
        assert data["creator"] == "test_user"
        assert data["performance_metrics"]["score"] == 8.5
    
    def test_save_baseline_invalid_entity_type(self, mock_data_manager):
        """测试保存无效实体类型的 baseline"""
        manager = BaselineManager(mock_data_manager)
        
        with pytest.raises(ValueError, match="不支持的实体类型"):
            manager.save_baseline(
                entity_type="invalid",
                entity_id="test_id",
                baseline_name="baseline_v1"
            )
    
    def test_save_baseline_with_evaluation_results(self, mock_data_manager, temp_dir):
        """测试保存包含评估结果的 baseline"""
        manager = BaselineManager(mock_data_manager)
        
        baseline_path = temp_dir / "test_pipeline.baseline_v1.snapshot.json"
        mock_data_manager.resolve_baseline_path.return_value = baseline_path
        mock_data_manager.create_backup_if_exists.return_value = None
        
        # 创建评估结果
        eval_results = [
            EvaluationResult(
                sample_id="sample1",
                variant="baseline",
                overall_score=8.5,
                must_have_pass=True,
                rule_violations=[],
                judge_feedback="良好",
                execution_time=1.5
            )
        ]
        
        manager.save_baseline(
            entity_type="pipeline",
            entity_id="test_pipeline",
            baseline_name="baseline_v1",
            evaluation_results=eval_results
        )
        
        # 验证评估结果被正确保存
        with open(baseline_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert len(data["evaluation_results"]) == 1
        assert data["evaluation_results"][0]["sample_id"] == "sample1"
        assert data["evaluation_results"][0]["overall_score"] == 8.5
    
    def test_save_baseline_existing_file_backup(self, mock_data_manager, temp_dir):
        """测试保存时已存在文件的备份处理"""
        manager = BaselineManager(mock_data_manager)
        
        baseline_path = temp_dir / "test_agent.baseline_v1.snapshot.json"
        backup_path = temp_dir / "test_agent.baseline_v1.snapshot.json.backup"
        
        # 创建已存在的文件
        baseline_path.write_text('{"old": "data"}')
        
        mock_data_manager.resolve_baseline_path.return_value = baseline_path
        mock_data_manager.create_backup_if_exists.return_value = backup_path
        
        manager.save_baseline(
            entity_type="agent",
            entity_id="test_agent",
            baseline_name="baseline_v1"
        )
        
        # 验证备份被创建
        mock_data_manager.create_backup_if_exists.assert_called_once_with(baseline_path)
    
    def test_load_baseline_success(self, mock_data_manager, temp_dir):
        """测试成功加载 baseline"""
        manager = BaselineManager(mock_data_manager)
        
        # 创建测试文件
        baseline_path = temp_dir / "test_agent.baseline_v1.snapshot.json"
        test_data = {
            "entity_type": "agent",
            "entity_id": "test_agent",
            "baseline_name": "baseline_v1",
            "description": "测试基线",
            "created_at": datetime.now().isoformat(),
            "creator": "test_user",
            "performance_metrics": {"score": 8.5}
        }
        
        with open(baseline_path, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)
        
        mock_data_manager.resolve_baseline_path.return_value = baseline_path
        
        # 加载 baseline
        snapshot = manager.load_baseline("agent", "test_agent", "baseline_v1")
        
        assert snapshot is not None
        assert snapshot.entity_type == "agent"
        assert snapshot.entity_id == "test_agent"
        assert snapshot.baseline_name == "baseline_v1"
        assert snapshot.description == "测试基线"
        assert snapshot.creator == "test_user"
        assert snapshot.performance_metrics["score"] == 8.5
    
    def test_load_baseline_not_exists(self, mock_data_manager, temp_dir):
        """测试加载不存在的 baseline"""
        manager = BaselineManager(mock_data_manager)
        
        baseline_path = temp_dir / "nonexistent.snapshot.json"
        mock_data_manager.resolve_baseline_path.return_value = baseline_path
        
        snapshot = manager.load_baseline("agent", "test_agent", "nonexistent")
        
        assert snapshot is None
    
    def test_load_baseline_invalid_json(self, mock_data_manager, temp_dir):
        """测试加载无效 JSON 文件"""
        manager = BaselineManager(mock_data_manager)
        
        baseline_path = temp_dir / "invalid.snapshot.json"
        baseline_path.write_text("invalid json content")
        
        mock_data_manager.resolve_baseline_path.return_value = baseline_path
        
        snapshot = manager.load_baseline("agent", "test_agent", "invalid")
        
        assert snapshot is None
    
    def test_list_baselines_success(self, mock_data_manager, temp_dir):
        """测试成功列出 baselines"""
        manager = BaselineManager(mock_data_manager)
        
        # 创建测试目录和文件
        baselines_dir = temp_dir / "test_agent"
        baselines_dir.mkdir()
        
        # 创建多个 baseline 文件
        baseline1_path = baselines_dir / "test_agent.baseline_v1.snapshot.json"
        baseline2_path = baselines_dir / "test_agent.baseline_v2.snapshot.json"
        
        test_data1 = {
            "baseline_name": "baseline_v1",
            "description": "第一个基线",
            "created_at": "2025-01-01T10:00:00",
            "creator": "user1",
            "performance_metrics": {"score": 8.0}
        }
        
        test_data2 = {
            "baseline_name": "baseline_v2",
            "description": "第二个基线",
            "created_at": "2025-01-02T10:00:00",
            "creator": "user2",
            "performance_metrics": {"score": 8.5}
        }
        
        with open(baseline1_path, 'w', encoding='utf-8') as f:
            json.dump(test_data1, f)
        
        with open(baseline2_path, 'w', encoding='utf-8') as f:
            json.dump(test_data2, f)
        
        mock_data_manager.get_baselines_dir.return_value = temp_dir
        
        # 列出 baselines
        baselines = manager.list_baselines("agent", "test_agent")
        
        assert len(baselines) == 2
        
        # 验证按创建时间倒序排列
        assert baselines[0]["baseline_name"] == "baseline_v2"
        assert baselines[1]["baseline_name"] == "baseline_v1"
        
        # 验证字段完整性
        for baseline in baselines:
            assert "baseline_name" in baseline
            assert "description" in baseline
            assert "created_at" in baseline
            assert "creator" in baseline
            assert "performance_metrics" in baseline
            assert "file_path" in baseline
            assert "file_size" in baseline
    
    def test_list_baselines_empty_directory(self, mock_data_manager, temp_dir):
        """测试列出空目录的 baselines"""
        manager = BaselineManager(mock_data_manager)
        
        mock_data_manager.get_baselines_dir.return_value = temp_dir / "nonexistent"
        
        baselines = manager.list_baselines("agent", "test_agent")
        
        assert baselines == []
    
    def test_list_baselines_invalid_files(self, mock_data_manager, temp_dir):
        """测试处理无效文件"""
        manager = BaselineManager(mock_data_manager)
        
        baselines_dir = temp_dir / "test_agent"
        baselines_dir.mkdir()
        
        # 创建无效的 JSON 文件
        invalid_file = baselines_dir / "test_agent.invalid.snapshot.json"
        invalid_file.write_text("invalid json")
        
        mock_data_manager.get_baselines_dir.return_value = temp_dir
        
        baselines = manager.list_baselines("agent", "test_agent")
        
        # 应该跳过无效文件
        assert baselines == []
    
    def test_delete_baseline_success(self, mock_data_manager, temp_dir):
        """测试成功删除 baseline"""
        manager = BaselineManager(mock_data_manager)
        
        # 创建测试文件
        baseline_path = temp_dir / "test_agent.baseline_v1.snapshot.json"
        baseline_path.write_text('{"test": "data"}')
        
        meta_path = baseline_path.with_suffix(baseline_path.suffix + ".meta.json")
        meta_path.write_text('{"meta": "data"}')
        
        mock_data_manager.resolve_baseline_path.return_value = baseline_path
        mock_data_manager.create_backup_if_exists.return_value = temp_dir / "backup.json"
        
        result = manager.delete_baseline("agent", "test_agent", "baseline_v1")
        
        assert result is True
        assert not baseline_path.exists()
        assert not meta_path.exists()
    
    def test_delete_baseline_not_exists(self, mock_data_manager, temp_dir):
        """测试删除不存在的 baseline"""
        manager = BaselineManager(mock_data_manager)
        
        baseline_path = temp_dir / "nonexistent.snapshot.json"
        mock_data_manager.resolve_baseline_path.return_value = baseline_path
        
        result = manager.delete_baseline("agent", "test_agent", "nonexistent")
        
        assert result is False
    
    def test_copy_baseline_success(self, mock_data_manager, temp_dir):
        """测试成功复制 baseline"""
        manager = BaselineManager(mock_data_manager)
        
        # 创建源文件
        source_path = temp_dir / "source.snapshot.json"
        target_path = temp_dir / "target.snapshot.json"
        
        source_data = {
            "entity_type": "agent",
            "entity_id": "test_agent",
            "baseline_name": "source",
            "description": "源基线",
            "created_at": datetime.now().isoformat(),
            "creator": "test_user",
            "performance_metrics": {"score": 8.0}
        }
        
        with open(source_path, 'w', encoding='utf-8') as f:
            json.dump(source_data, f)
        
        def mock_resolve_path(entity_type, entity_id, baseline_name):
            if baseline_name == "source":
                return source_path
            elif baseline_name == "target":
                return target_path
        
        mock_data_manager.resolve_baseline_path.side_effect = mock_resolve_path
        
        result = manager.copy_baseline(
            "agent", "test_agent", "source", "target", "复制的基线"
        )
        
        assert result is True
        assert target_path.exists()
        
        # 验证复制的内容
        with open(target_path, 'r', encoding='utf-8') as f:
            copied_data = json.load(f)
        
        assert copied_data["baseline_name"] == "target"
        assert copied_data["description"] == "复制的基线"
        assert copied_data["performance_metrics"]["score"] == 8.0
    
    def test_copy_baseline_source_not_exists(self, mock_data_manager):
        """测试复制不存在的源 baseline"""
        manager = BaselineManager(mock_data_manager)
        
        mock_data_manager.resolve_baseline_path.return_value = Path("nonexistent.json")
        
        result = manager.copy_baseline(
            "agent", "test_agent", "nonexistent", "target"
        )
        
        assert result is False
    
    def test_copy_baseline_target_exists(self, mock_data_manager, temp_dir):
        """测试复制到已存在的目标 baseline"""
        manager = BaselineManager(mock_data_manager)
        
        source_path = temp_dir / "source.snapshot.json"
        target_path = temp_dir / "target.snapshot.json"
        
        # 创建源文件和目标文件
        source_path.write_text('{"test": "source"}')
        target_path.write_text('{"test": "target"}')
        
        def mock_resolve_path(entity_type, entity_id, baseline_name):
            if baseline_name == "source":
                return source_path
            elif baseline_name == "target":
                return target_path
        
        mock_data_manager.resolve_baseline_path.side_effect = mock_resolve_path
        
        result = manager.copy_baseline(
            "agent", "test_agent", "source", "target"
        )
        
        assert result is False
    
    def test_get_baseline_performance(self, mock_data_manager, temp_dir):
        """测试获取 baseline 性能指标"""
        manager = BaselineManager(mock_data_manager)
        
        baseline_path = temp_dir / "test.snapshot.json"
        test_data = {
            "performance_metrics": {"score": 8.5, "pass_rate": 0.9}
        }
        
        with open(baseline_path, 'w', encoding='utf-8') as f:
            json.dump(test_data, f)
        
        mock_data_manager.resolve_baseline_path.return_value = baseline_path
        
        metrics = manager.get_baseline_performance("agent", "test_agent", "baseline_v1")
        
        assert metrics is not None
        assert metrics["score"] == 8.5
        assert metrics["pass_rate"] == 0.9
    
    def test_get_baseline_performance_not_exists(self, mock_data_manager):
        """测试获取不存在 baseline 的性能指标"""
        manager = BaselineManager(mock_data_manager)
        
        mock_data_manager.resolve_baseline_path.return_value = Path("nonexistent.json")
        
        metrics = manager.get_baseline_performance("agent", "test_agent", "nonexistent")
        
        assert metrics is None
    
    def test_update_baseline_metadata(self, mock_data_manager, temp_dir):
        """测试更新 baseline 元数据"""
        manager = BaselineManager(mock_data_manager)
        
        baseline_path = temp_dir / "test.snapshot.json"
        original_data = {
            "entity_type": "agent",
            "entity_id": "test_agent",
            "baseline_name": "baseline_v1",
            "description": "原始描述",
            "metadata": {"version": "1.0"}
        }
        
        with open(baseline_path, 'w', encoding='utf-8') as f:
            json.dump(original_data, f)
        
        mock_data_manager.resolve_baseline_path.return_value = baseline_path
        
        result = manager.update_baseline_metadata(
            "agent", "test_agent", "baseline_v1",
            new_description="更新的描述",
            additional_metadata={"version": "1.1", "updated": True}
        )
        
        assert result is True
        
        # 验证更新后的内容
        with open(baseline_path, 'r', encoding='utf-8') as f:
            updated_data = json.load(f)
        
        assert updated_data["description"] == "更新的描述"
        assert updated_data["metadata"]["version"] == "1.1"
        assert updated_data["metadata"]["updated"] is True
    
    def test_validate_baseline_success(self, mock_data_manager, temp_dir):
        """测试成功验证 baseline"""
        manager = BaselineManager(mock_data_manager)
        
        baseline_path = temp_dir / "test.snapshot.json"
        valid_data = {
            "entity_type": "agent",
            "entity_id": "test_agent",
            "baseline_name": "baseline_v1",
            "creator": "test_user",
            "performance_metrics": {"score": 8.5},
            "evaluation_results": [{"sample_id": "sample1"}]
        }
        
        with open(baseline_path, 'w', encoding='utf-8') as f:
            json.dump(valid_data, f)
        
        mock_data_manager.resolve_baseline_path.return_value = baseline_path
        
        errors = manager.validate_baseline("agent", "test_agent", "baseline_v1")
        
        assert errors == []
    
    def test_validate_baseline_missing_fields(self, mock_data_manager, temp_dir):
        """测试验证缺少字段的 baseline"""
        manager = BaselineManager(mock_data_manager)
        
        baseline_path = temp_dir / "test.snapshot.json"
        invalid_data = {
            "entity_type": "",  # 空实体类型
            "entity_id": "",    # 空实体 ID
            # 缺少 baseline_name 和 creator
        }
        
        with open(baseline_path, 'w', encoding='utf-8') as f:
            json.dump(invalid_data, f)
        
        mock_data_manager.resolve_baseline_path.return_value = baseline_path
        
        errors = manager.validate_baseline("agent", "test_agent", "baseline_v1")
        
        assert len(errors) >= 4  # 至少4个错误
        assert any("实体类型" in error for error in errors)
        assert any("实体 ID" in error for error in errors)
        assert any("baseline 名称" in error for error in errors)
        assert any("创建者" in error for error in errors)
    
    def test_validate_baseline_invalid_entity_type(self, mock_data_manager, temp_dir):
        """测试验证无效实体类型的 baseline"""
        manager = BaselineManager(mock_data_manager)
        
        baseline_path = temp_dir / "test.snapshot.json"
        invalid_data = {
            "entity_type": "invalid_type",
            "entity_id": "test_agent",
            "baseline_name": "baseline_v1",
            "creator": "test_user"
        }
        
        with open(baseline_path, 'w', encoding='utf-8') as f:
            json.dump(invalid_data, f)
        
        mock_data_manager.resolve_baseline_path.return_value = baseline_path
        
        errors = manager.validate_baseline("agent", "test_agent", "baseline_v1")
        
        assert any("无效的实体类型" in error for error in errors)
    
    def test_validate_baseline_invalid_metrics(self, mock_data_manager, temp_dir):
        """测试验证无效性能指标的 baseline"""
        manager = BaselineManager(mock_data_manager)
        
        baseline_path = temp_dir / "test.snapshot.json"
        invalid_data = {
            "entity_type": "agent",
            "entity_id": "test_agent",
            "baseline_name": "baseline_v1",
            "creator": "test_user",
            "performance_metrics": {"score": "invalid_number"}  # 非数字值
        }
        
        with open(baseline_path, 'w', encoding='utf-8') as f:
            json.dump(invalid_data, f)
        
        mock_data_manager.resolve_baseline_path.return_value = baseline_path
        
        errors = manager.validate_baseline("agent", "test_agent", "baseline_v1")
        
        assert any("不是数字" in error for error in errors)


class TestConvenienceFunctions:
    """测试便捷函数"""
    
    @patch('src.baseline_manager.baseline_manager')
    def test_save_agent_baseline(self, mock_manager):
        """测试保存 agent baseline 便捷函数"""
        mock_manager.save_baseline.return_value = Path("test.json")
        
        result = save_agent_baseline(
            "test_agent", "baseline_v1", "测试基线",
            performance_metrics={"score": 8.5}
        )
        
        mock_manager.save_baseline.assert_called_once_with(
            "agent", "test_agent", "baseline_v1", "测试基线",
            performance_metrics={"score": 8.5},
            evaluation_results=None
        )
        assert result == Path("test.json")
    
    @patch('src.baseline_manager.baseline_manager')
    def test_save_pipeline_baseline(self, mock_manager):
        """测试保存 pipeline baseline 便捷函数"""
        mock_manager.save_baseline.return_value = Path("test.json")
        
        result = save_pipeline_baseline(
            "test_pipeline", "baseline_v1", "测试基线"
        )
        
        mock_manager.save_baseline.assert_called_once_with(
            "pipeline", "test_pipeline", "baseline_v1", "测试基线",
            performance_metrics=None,
            evaluation_results=None
        )
        assert result == Path("test.json")
    
    @patch('src.baseline_manager.baseline_manager')
    def test_load_agent_baseline(self, mock_manager):
        """测试加载 agent baseline 便捷函数"""
        mock_snapshot = Mock()
        mock_manager.load_baseline.return_value = mock_snapshot
        
        result = load_agent_baseline("test_agent", "baseline_v1")
        
        mock_manager.load_baseline.assert_called_once_with(
            "agent", "test_agent", "baseline_v1"
        )
        assert result == mock_snapshot
    
    @patch('src.baseline_manager.baseline_manager')
    def test_load_pipeline_baseline(self, mock_manager):
        """测试加载 pipeline baseline 便捷函数"""
        mock_snapshot = Mock()
        mock_manager.load_baseline.return_value = mock_snapshot
        
        result = load_pipeline_baseline("test_pipeline", "baseline_v1")
        
        mock_manager.load_baseline.assert_called_once_with(
            "pipeline", "test_pipeline", "baseline_v1"
        )
        assert result == mock_snapshot
    
    @patch('src.baseline_manager.baseline_manager')
    def test_list_agent_baselines(self, mock_manager):
        """测试列出 agent baselines 便捷函数"""
        mock_list = [{"baseline_name": "v1"}, {"baseline_name": "v2"}]
        mock_manager.list_baselines.return_value = mock_list
        
        result = list_agent_baselines("test_agent")
        
        mock_manager.list_baselines.assert_called_once_with("agent", "test_agent")
        assert result == mock_list
    
    @patch('src.baseline_manager.baseline_manager')
    def test_list_pipeline_baselines(self, mock_manager):
        """测试列出 pipeline baselines 便捷函数"""
        mock_list = [{"baseline_name": "v1"}, {"baseline_name": "v2"}]
        mock_manager.list_baselines.return_value = mock_list
        
        result = list_pipeline_baselines("test_pipeline")
        
        mock_manager.list_baselines.assert_called_once_with("pipeline", "test_pipeline")
        assert result == mock_list