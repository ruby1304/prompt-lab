"""Tests for the BatchDataProcessor class."""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from src.agent_template_parser.batch_data_processor import BatchDataProcessor, ProcessedJsonData


class TestProcessedJsonData:
    """Test cases for ProcessedJsonData class."""
    
    def test_get_testset_entry_with_id(self):
        """Test getting testset entry with provided ID."""
        data = ProcessedJsonData(
            original_data={"test": "data"},
            extracted_fields={"field1": "value1", "field2": "value2"},
            expected="test_expected"
        )
        
        entry = data.get_testset_entry(entry_id=123)
        
        assert entry["id"] == 123
        assert entry["field1"] == "value1"
        assert entry["field2"] == "value2"
    
    def test_get_testset_entry_without_id(self):
        """Test getting testset entry without provided ID (auto-generated)."""
        data = ProcessedJsonData(
            original_data={"test": "data"},
            extracted_fields={"field1": "value1"},
        )
        
        entry = data.get_testset_entry()
        
        assert "id" in entry
        assert isinstance(entry["id"], int)
        assert entry["field1"] == "value1"


class TestBatchDataProcessor:
    """Test cases for BatchDataProcessor class."""
    
    @pytest.fixture
    def temp_agents_dir(self):
        """Create a temporary agents directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            agents_dir = Path(temp_dir) / "agents"
            agents_dir.mkdir()
            
            # Create a test agent
            test_agent_dir = agents_dir / "test_agent"
            test_agent_dir.mkdir()
            (test_agent_dir / "agent.yaml").write_text("test: config")
            
            # Create testsets directory
            testsets_dir = test_agent_dir / "testsets"
            testsets_dir.mkdir()
            
            yield str(agents_dir)
    
    @pytest.fixture
    def processor(self, temp_agents_dir):
        """Create a BatchDataProcessor instance with temp directory."""
        return BatchDataProcessor(agents_dir=temp_agents_dir)
    
    def test_init(self, temp_agents_dir):
        """Test BatchDataProcessor initialization."""
        processor = BatchDataProcessor(agents_dir=temp_agents_dir)
        assert processor.agents_dir == Path(temp_agents_dir)
    
    def test_validate_agent_exists_true(self, processor):
        """Test agent validation for existing agent."""
        assert processor.validate_agent_exists("test_agent") is True
    
    def test_validate_agent_exists_false(self, processor):
        """Test agent validation for non-existing agent."""
        assert processor.validate_agent_exists("nonexistent_agent") is False
    
    def test_get_available_agents(self, processor):
        """Test getting list of available agents."""
        agents = processor.get_available_agents()
        assert "test_agent" in agents
    
    def test_get_available_agents_empty_dir(self):
        """Test getting agents from empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            processor = BatchDataProcessor(agents_dir=temp_dir)
            agents = processor.get_available_agents()
            assert agents == []
    
    def test_process_json_inputs_valid(self, processor):
        """Test processing valid JSON inputs."""
        json_inputs = [
            '{"id": 1, "field1": "value1", "expected": "test1"}',
            '{"id": 2, "sys": {"user_input": "test input"}, "expected": "test2"}'
        ]
        
        result = processor.process_json_inputs(json_inputs, "test_agent")
        
        assert len(result) == 2
        assert isinstance(result[0], ProcessedJsonData)
        assert result[0].extracted_fields["id"] == 1
        assert result[0].extracted_fields["field1"] == "value1"
        assert result[0].expected == "test1"
        
        assert result[1].extracted_fields["id"] == 2
        assert result[1].extracted_fields["chat_round_30"] == "test input"
        assert result[1].sys_user_input == "test input"
        assert result[1].expected == "test2"
    
    def test_process_json_inputs_invalid_agent(self, processor):
        """Test processing JSON inputs with invalid agent."""
        json_inputs = ['{"test": "data"}']
        
        with pytest.raises(ValueError, match="Target agent 'invalid_agent' does not exist"):
            processor.process_json_inputs(json_inputs, "invalid_agent")
    
    def test_process_json_inputs_invalid_json(self, processor):
        """Test processing invalid JSON inputs."""
        json_inputs = ['{"invalid": json}']
        
        with pytest.raises(ValueError, match="Invalid JSON at index 0"):
            processor.process_json_inputs(json_inputs, "test_agent")
    
    def test_extract_structured_data_simple(self, processor):
        """Test extracting structured data from simple JSON."""
        data = {"id": 1, "field1": "value1", "expected": "test"}
        
        result = processor._extract_structured_data(data, 0)
        
        assert result.extracted_fields["id"] == 1
        assert result.extracted_fields["field1"] == "value1"
        assert result.expected == "test"
    
    def test_extract_structured_data_with_sys(self, processor):
        """Test extracting structured data with sys object."""
        data = {
            "id": 1,
            "sys": {
                "user_input": "test input",
                "other_field": "other value"
            },
            "expected": "test"
        }
        
        result = processor._extract_structured_data(data, 0)
        
        assert result.extracted_fields["id"] == 1
        assert result.extracted_fields["chat_round_30"] == "test input"
        assert result.extracted_fields["sys_other_field"] == "other value"
        assert result.sys_user_input == "test input"
        assert result.expected == "test"
    
    def test_extract_structured_data_with_user_name_replacement(self, processor):
        """Test extracting data with user_name placeholder replacement."""
        data = {
            "id": 1,
            "user_name": "TestUser",
            "message": "Hello {user_name}!",
            "expected": "test"
        }
        
        result = processor._extract_structured_data(data, 0)
        
        assert result.extracted_fields["user_name"] == "TestUser"
        assert result.extracted_fields["message"] == "Hello TestUser!"
        assert result.user_name == "TestUser"
    
    def test_convert_to_testset_format(self, processor):
        """Test converting processed data to testset format."""
        processed_data = [
            ProcessedJsonData(
                original_data={"id": 1},
                extracted_fields={"id": 1, "field1": "value1", "expected": "test1"}
            ),
            ProcessedJsonData(
                original_data={"id": 2},
                extracted_fields={"field2": "value2", "expected": "test2"}
            )
        ]
        
        result = processor.convert_to_testset_format(processed_data)
        
        assert len(result) == 2
        assert result[0]["id"] == 1
        assert result[0]["field1"] == "value1"
        assert result[0]["expected"] == "test1"
        assert "tags" in result[0]
        
        assert result[1]["id"] == 2  # Auto-generated from index + 1
        assert result[1]["field2"] == "value2"
        assert result[1]["expected"] == "test2"
        assert "tags" in result[1]
    
    def test_save_testset_success(self, processor):
        """Test successfully saving testset data."""
        testset_data = [
            {"id": 1, "field1": "value1", "expected": "test1"},
            {"id": 2, "field2": "value2", "expected": "test2"}
        ]
        
        output_path = processor.save_testset(testset_data, "test_agent", "test_output")
        
        assert output_path.exists()
        assert output_path.name == "test_output.jsonl"
        
        # Verify file content
        with open(output_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        assert len(lines) == 2
        assert json.loads(lines[0]) == testset_data[0]
        assert json.loads(lines[1]) == testset_data[1]
    
    def test_save_testset_invalid_agent(self, processor):
        """Test saving testset with invalid agent."""
        testset_data = [{"id": 1, "test": "data"}]
        
        with pytest.raises(ValueError, match="Agent 'invalid_agent' does not exist"):
            processor.save_testset(testset_data, "invalid_agent", "test_output")
    
    def test_save_testset_auto_add_jsonl_extension(self, processor):
        """Test that .jsonl extension is automatically added."""
        testset_data = [{"id": 1, "test": "data"}]
        
        output_path = processor.save_testset(testset_data, "test_agent", "test_output")
        
        assert output_path.name == "test_output.jsonl"
    
    def test_save_testset_creates_testsets_dir(self, temp_agents_dir):
        """Test that testsets directory is created if it doesn't exist."""
        # Create agent without testsets directory
        agent_dir = Path(temp_agents_dir) / "new_agent"
        agent_dir.mkdir()
        (agent_dir / "agent.yaml").write_text("test: config")
        
        processor = BatchDataProcessor(agents_dir=temp_agents_dir)
        testset_data = [{"id": 1, "test": "data"}]
        
        output_path = processor.save_testset(testset_data, "new_agent", "test_output")
        
        assert output_path.parent.exists()
        assert output_path.parent.name == "testsets"


class TestBatchDataProcessorIntegration:
    """Integration tests for BatchDataProcessor."""
    
    @pytest.fixture
    def temp_agents_dir(self):
        """Create a temporary agents directory for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            agents_dir = Path(temp_dir) / "agents"
            agents_dir.mkdir()
            
            # Create mem0_l1_summarizer agent (like in the example)
            agent_dir = agents_dir / "mem0_l1_summarizer"
            agent_dir.mkdir()
            (agent_dir / "agent.yaml").write_text("test: config")
            
            testsets_dir = agent_dir / "testsets"
            testsets_dir.mkdir()
            
            yield str(agents_dir)
    
    def test_end_to_end_processing(self, temp_agents_dir):
        """Test complete end-to-end processing workflow."""
        processor = BatchDataProcessor(agents_dir=temp_agents_dir)
        
        # Sample JSON inputs similar to the real testset format
        json_inputs = [
            json.dumps({
                "id": 1,
                "character_profile": "Test character profile",
                "current_schedule_time": "13:03",
                "current_schedule_full_desc": "Test schedule description",
                "cloth_prompt": "默认服装",
                "chat_round_30": "Test chat history",
                "user_name": "{user_name}",
                "expected": "能正确总结记忆"
            }),
            json.dumps({
                "id": 2,
                "sys": {
                    "user_input": "Complex chat history with multiple rounds"
                },
                "character_profile": "Another character profile",
                "user_name": "TestUser",
                "expected": "能正确总结记忆"
            })
        ]
        
        # Process JSON inputs
        processed_data = processor.process_json_inputs(json_inputs, "mem0_l1_summarizer")
        assert len(processed_data) == 2
        
        # Convert to testset format
        testset_data = processor.convert_to_testset_format(processed_data)
        assert len(testset_data) == 2
        
        # Save testset
        output_path = processor.save_testset(testset_data, "mem0_l1_summarizer", "integration_test")
        assert output_path.exists()
        
        # Verify saved content
        with open(output_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        assert len(lines) == 2
        
        # Verify first entry
        entry1 = json.loads(lines[0])
        assert entry1["id"] == 1
        assert entry1["character_profile"] == "Test character profile"
        assert entry1["chat_round_30"] == "Test chat history"
        
        # Verify second entry with sys.user_input processing
        entry2 = json.loads(lines[1])
        assert entry2["id"] == 2
        assert entry2["chat_round_30"] == "Complex chat history with multiple rounds"
        assert entry2["character_profile"] == "Another character profile"