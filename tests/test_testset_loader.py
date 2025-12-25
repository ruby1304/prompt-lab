# tests/test_testset_loader.py
"""
Unit tests for testset loader
"""

import pytest
import json
from pathlib import Path
from src.testset_loader import (
    TestCase, TestsetLoader, load_testset, validate_testset, filter_by_tags
)


class TestTestCase:
    """Test TestCase data structure"""
    
    def test_from_dict_simple(self):
        """Test creating TestCase from simple dict"""
        data = {
            "id": "test_1",
            "tags": ["simple"],
            "text": "Hello world",
            "expected_output": "HELLO WORLD"
        }
        
        tc = TestCase.from_dict(data)
        
        assert tc.id == "test_1"
        assert tc.tags == ["simple"]
        assert tc.get_input("text") == "Hello world"
        assert tc.get_input("expected_output") == "HELLO WORLD"
    
    def test_from_dict_explicit_inputs(self):
        """Test creating TestCase with explicit inputs"""
        data = {
            "id": "test_2",
            "tags": ["explicit"],
            "inputs": {
                "text": "Hello",
                "language": "en"
            },
            "expected_outputs": {
                "result": "HELLO"
            }
        }
        
        tc = TestCase.from_dict(data)
        
        assert tc.id == "test_2"
        assert tc.inputs["text"] == "Hello"
        assert tc.inputs["language"] == "en"
        assert tc.expected_outputs["result"] == "HELLO"
    
    def test_from_dict_step_inputs(self):
        """Test creating TestCase with step-specific inputs"""
        data = {
            "id": "test_3",
            "inputs": {"global": "value"},
            "step_inputs": {
                "step1": {"param1": "value1"},
                "step2": {"param2": "value2"}
            }
        }
        
        tc = TestCase.from_dict(data)
        
        assert tc.has_step_inputs()
        assert tc.get_step_input("step1", "param1") == "value1"
        assert tc.get_step_input("step2", "param2") == "value2"
        assert tc.get_step_input("step3", "param3", "default") == "default"
    
    def test_from_dict_batch_items(self):
        """Test creating TestCase with batch items"""
        data = {
            "id": "test_4",
            "batch_items": [
                {"text": "Item 1"},
                {"text": "Item 2"},
                {"text": "Item 3"}
            ],
            "expected_aggregation": {
                "total": 3
            }
        }
        
        tc = TestCase.from_dict(data)
        
        assert tc.has_batch_data()
        assert len(tc.batch_items) == 3
        assert tc.batch_items[0]["text"] == "Item 1"
        assert tc.has_expected_aggregation()
        assert tc.expected_aggregation["total"] == 3
    
    def test_from_dict_tags_string(self):
        """Test handling tags as string"""
        data = {
            "id": "test_5",
            "tags": "single-tag"
        }
        
        tc = TestCase.from_dict(data)
        
        assert tc.tags == ["single-tag"]
    
    def test_from_dict_tags_invalid(self):
        """Test handling invalid tags"""
        data = {
            "id": "test_6",
            "tags": 123  # Invalid type
        }
        
        tc = TestCase.from_dict(data)
        
        assert tc.tags == []
    
    def test_to_dict(self):
        """Test converting TestCase to dict"""
        tc = TestCase(
            id="test_7",
            tags=["test"],
            inputs={"text": "Hello"},
            expected_outputs={"result": "HELLO"}
        )
        
        data = tc.to_dict()
        
        assert data["id"] == "test_7"
        assert data["tags"] == ["test"]
        assert data["inputs"]["text"] == "Hello"
        assert data["expected_outputs"]["result"] == "HELLO"
    
    def test_get_input_with_default(self):
        """Test getting input with default value"""
        tc = TestCase(
            id="test_8",
            inputs={"text": "Hello"}
        )
        
        assert tc.get_input("text") == "Hello"
        assert tc.get_input("missing", "default") == "default"
        assert tc.get_input("missing") is None


class TestTestsetLoader:
    """Test TestsetLoader"""
    
    def test_load_testset_simple(self, tmp_path):
        """Test loading simple testset"""
        testset_file = tmp_path / "test.jsonl"
        testset_file.write_text(
            '{"id": "test_1", "tags": ["simple"], "text": "Hello"}\n'
            '{"id": "test_2", "tags": ["simple"], "text": "World"}\n'
        )
        
        test_cases = TestsetLoader.load_testset(testset_file)
        
        assert len(test_cases) == 2
        assert test_cases[0].id == "test_1"
        assert test_cases[1].id == "test_2"
    
    def test_load_testset_with_batch(self, tmp_path):
        """Test loading testset with batch items"""
        testset_file = tmp_path / "batch.jsonl"
        testset_file.write_text(
            '{"id": "batch_1", "batch_items": [{"x": 1}, {"x": 2}]}\n'
        )
        
        test_cases = TestsetLoader.load_testset(testset_file)
        
        assert len(test_cases) == 1
        assert test_cases[0].has_batch_data()
        assert len(test_cases[0].batch_items) == 2
    
    def test_load_testset_file_not_found(self):
        """Test loading non-existent file"""
        with pytest.raises(FileNotFoundError):
            TestsetLoader.load_testset(Path("nonexistent.jsonl"))
    
    def test_load_testset_invalid_json(self, tmp_path):
        """Test loading file with invalid JSON"""
        testset_file = tmp_path / "invalid.jsonl"
        testset_file.write_text('{"id": "test_1", invalid json}\n')
        
        with pytest.raises(ValueError, match="JSON 解析错误"):
            TestsetLoader.load_testset(testset_file)
    
    def test_load_testset_empty_file(self, tmp_path):
        """Test loading empty file"""
        testset_file = tmp_path / "empty.jsonl"
        testset_file.write_text("")
        
        with pytest.raises(ValueError, match="测试集文件为空"):
            TestsetLoader.load_testset(testset_file)
    
    def test_load_testset_skip_empty_lines(self, tmp_path):
        """Test loading testset with empty lines"""
        testset_file = tmp_path / "with_empty.jsonl"
        testset_file.write_text(
            '{"id": "test_1"}\n'
            '\n'
            '{"id": "test_2"}\n'
            '   \n'
            '{"id": "test_3"}\n'
        )
        
        test_cases = TestsetLoader.load_testset(testset_file)
        
        assert len(test_cases) == 3
    
    def test_load_testset_dict(self, tmp_path):
        """Test loading testset as dict (backward compatibility)"""
        testset_file = tmp_path / "test.jsonl"
        testset_file.write_text('{"id": "test_1", "text": "Hello"}\n')
        
        test_dicts = TestsetLoader.load_testset_dict(testset_file)
        
        assert len(test_dicts) == 1
        assert isinstance(test_dicts[0], dict)
        assert test_dicts[0]["id"] == "test_1"
    
    def test_validate_testset_valid(self):
        """Test validating valid testset"""
        test_cases = [
            TestCase(id="test_1", tags=["a"]),
            TestCase(id="test_2", tags=["b"])
        ]
        
        errors = TestsetLoader.validate_testset(test_cases)
        
        assert len(errors) == 0
    
    def test_validate_testset_duplicate_ids(self):
        """Test validating testset with duplicate IDs"""
        test_cases = [
            TestCase(id="test_1", tags=["a"]),
            TestCase(id="test_1", tags=["b"])
        ]
        
        errors = TestsetLoader.validate_testset(test_cases)
        
        assert len(errors) > 0
        assert any("重复" in error for error in errors)
    
    def test_validate_testset_missing_id(self):
        """Test validating testset with missing ID"""
        test_cases = [
            TestCase(id="", tags=["a"])
        ]
        
        errors = TestsetLoader.validate_testset(test_cases)
        
        assert len(errors) > 0
        assert any("缺少 ID" in error for error in errors)
    
    def test_validate_testset_invalid_batch_items(self):
        """Test validating testset with invalid batch items"""
        test_cases = [
            TestCase(
                id="test_1",
                batch_items="not a list"  # Invalid
            )
        ]
        
        errors = TestsetLoader.validate_testset(test_cases)
        
        assert len(errors) > 0
        assert any("batch_items 必须是列表" in error for error in errors)
    
    def test_validate_testset_invalid_step_inputs(self):
        """Test validating testset with invalid step inputs"""
        test_cases = [
            TestCase(
                id="test_1",
                step_inputs="not a dict"  # Invalid
            )
        ]
        
        errors = TestsetLoader.validate_testset(test_cases)
        
        assert len(errors) > 0
        assert any("step_inputs 必须是字典" in error for error in errors)
    
    def test_filter_by_tags_include(self):
        """Test filtering by include tags"""
        test_cases = [
            TestCase(id="test_1", tags=["a", "b"]),
            TestCase(id="test_2", tags=["b", "c"]),
            TestCase(id="test_3", tags=["c", "d"])
        ]
        
        filtered = TestsetLoader.filter_by_tags(test_cases, include_tags=["a"])
        
        assert len(filtered) == 1
        assert filtered[0].id == "test_1"
    
    def test_filter_by_tags_exclude(self):
        """Test filtering by exclude tags"""
        test_cases = [
            TestCase(id="test_1", tags=["a", "b"]),
            TestCase(id="test_2", tags=["b", "c"]),
            TestCase(id="test_3", tags=["c", "d"])
        ]
        
        filtered = TestsetLoader.filter_by_tags(test_cases, exclude_tags=["a"])
        
        assert len(filtered) == 2
        assert filtered[0].id == "test_2"
        assert filtered[1].id == "test_3"
    
    def test_filter_by_tags_include_and_exclude(self):
        """Test filtering by both include and exclude tags"""
        test_cases = [
            TestCase(id="test_1", tags=["a", "b"]),
            TestCase(id="test_2", tags=["b", "c"]),
            TestCase(id="test_3", tags=["c", "d"])
        ]
        
        filtered = TestsetLoader.filter_by_tags(
            test_cases,
            include_tags=["b", "c"],
            exclude_tags=["a"]
        )
        
        assert len(filtered) == 2
        assert filtered[0].id == "test_2"
        assert filtered[1].id == "test_3"
    
    def test_get_batch_test_cases(self):
        """Test getting batch test cases"""
        test_cases = [
            TestCase(id="test_1", batch_items=[{"x": 1}]),
            TestCase(id="test_2"),
            TestCase(id="test_3", batch_items=[{"x": 2}])
        ]
        
        batch_cases = TestsetLoader.get_batch_test_cases(test_cases)
        
        assert len(batch_cases) == 2
        assert batch_cases[0].id == "test_1"
        assert batch_cases[1].id == "test_3"
    
    def test_get_step_input_test_cases(self):
        """Test getting step input test cases"""
        test_cases = [
            TestCase(id="test_1", step_inputs={"step1": {}}),
            TestCase(id="test_2"),
            TestCase(id="test_3", step_inputs={"step2": {}})
        ]
        
        step_cases = TestsetLoader.get_step_input_test_cases(test_cases)
        
        assert len(step_cases) == 2
        assert step_cases[0].id == "test_1"
        assert step_cases[1].id == "test_3"


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    def test_load_testset(self, tmp_path):
        """Test load_testset convenience function"""
        testset_file = tmp_path / "test.jsonl"
        testset_file.write_text('{"id": "test_1"}\n')
        
        test_cases = load_testset(testset_file)
        
        assert len(test_cases) == 1
        assert test_cases[0].id == "test_1"
    
    def test_validate_testset(self):
        """Test validate_testset convenience function"""
        test_cases = [TestCase(id="test_1")]
        
        errors = validate_testset(test_cases)
        
        assert len(errors) == 0
    
    def test_filter_by_tags(self):
        """Test filter_by_tags convenience function"""
        test_cases = [
            TestCase(id="test_1", tags=["a"]),
            TestCase(id="test_2", tags=["b"])
        ]
        
        filtered = filter_by_tags(test_cases, include_tags=["a"])
        
        assert len(filtered) == 1
        assert filtered[0].id == "test_1"


class TestRealWorldExamples:
    """Test with real-world example files"""
    
    def test_load_batch_processing_demo(self):
        """Test loading the batch processing demo testset"""
        testset_file = Path("examples/testsets/batch_processing_demo.jsonl")
        
        if not testset_file.exists():
            pytest.skip("Example file not found")
        
        test_cases = load_testset(testset_file)
        
        assert len(test_cases) > 0
        
        # Validate all test cases
        errors = validate_testset(test_cases)
        assert len(errors) == 0, f"Validation errors: {errors}"
        
        # Check that test cases have batch-related tags
        batch_tagged = [tc for tc in test_cases if "batch" in tc.tags]
        assert len(batch_tagged) > 0
        
        # Check that test cases have customer_reviews field (batch data in different format)
        reviews_cases = [tc for tc in test_cases if tc.get_input("customer_reviews")]
        assert len(reviews_cases) > 0
    
    def test_load_batch_processing_advanced(self):
        """Test loading the advanced batch processing testset"""
        testset_file = Path("examples/testsets/batch_processing_advanced.jsonl")
        
        if not testset_file.exists():
            pytest.skip("Example file not found")
        
        test_cases = load_testset(testset_file)
        
        assert len(test_cases) > 0
        
        # Validate all test cases
        errors = validate_testset(test_cases)
        assert len(errors) == 0, f"Validation errors: {errors}"
    
    def test_load_pipeline_testset_formats(self):
        """Test loading the pipeline testset formats example"""
        testset_file = Path("examples/testsets/pipeline_testset_formats.jsonl")
        
        if not testset_file.exists():
            pytest.skip("Example file not found")
        
        test_cases = load_testset(testset_file)
        
        assert len(test_cases) > 0
        
        # Validate all test cases
        errors = validate_testset(test_cases)
        assert len(errors) == 0, f"Validation errors: {errors}"
        
        # Check different format types
        simple_cases = [tc for tc in test_cases if "simple" in tc.tags]
        batch_cases = [tc for tc in test_cases if "batch" in tc.tags]
        step_cases = TestsetLoader.get_step_input_test_cases(test_cases)
        
        assert len(simple_cases) > 0
        assert len(batch_cases) > 0
        assert len(step_cases) > 0
