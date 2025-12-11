"""Batch data processor for handling JSON inputs and generating testsets."""

import json
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .models import TemplateData


@dataclass
class ProcessedJsonData:
    """Represents processed JSON data with extracted fields."""
    
    original_data: Dict[str, Any]
    extracted_fields: Dict[str, Any]
    sys_user_input: Optional[Any] = None
    user_name: Optional[str] = None
    expected: Optional[str] = None
    
    def get_testset_entry(self, entry_id: Optional[int] = None) -> Dict[str, Any]:
        """Convert to testset format entry."""
        if entry_id is None:
            entry_id = int(str(uuid.uuid4().int)[:8])
            
        return {
            "id": entry_id,
            **self.extracted_fields
        }


class BatchDataProcessor:
    """Processor for handling batch JSON inputs and generating testsets."""
    
    def __init__(self, agents_dir: str = "agents"):
        """Initialize the batch data processor.
        
        Args:
            agents_dir: Directory containing agent configurations
        """
        self.agents_dir = Path(agents_dir)
    
    def process_json_inputs(self, json_inputs: List[str], target_agent: str) -> List[ProcessedJsonData]:
        """Process multiple JSON input strings and extract structured data.
        
        Args:
            json_inputs: List of JSON strings to process
            target_agent: Name of the target agent for validation
            
        Returns:
            List of ProcessedJsonData objects
            
        Raises:
            ValueError: If target agent doesn't exist or JSON is invalid
        """
        if not self.validate_agent_exists(target_agent):
            raise ValueError(f"Target agent '{target_agent}' does not exist")
        
        processed_data = []
        
        for i, json_input in enumerate(json_inputs):
            try:
                # Parse JSON data
                data = json.loads(json_input)
                
                # Extract structured data
                processed_entry = self._extract_structured_data(data, i)
                processed_data.append(processed_entry)
                
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON at index {i}: {e}")
            except Exception as e:
                raise ValueError(f"Error processing JSON at index {i}: {e}")
        
        return processed_data
    
    def _extract_structured_data(self, data: Dict[str, Any], index: int) -> ProcessedJsonData:
        """Extract and structure data from a single JSON object.
        
        Args:
            data: Raw JSON data dictionary
            index: Index of the data entry for error reporting
            
        Returns:
            ProcessedJsonData object with extracted fields
        """
        extracted_fields = {}
        sys_user_input = None
        user_name = None
        expected = None
        
        # Handle nested sys.user_input structure
        if "sys" in data and isinstance(data["sys"], dict):
            if "user_input" in data["sys"]:
                sys_user_input = data["sys"]["user_input"]
                extracted_fields["chat_round_30"] = sys_user_input
        
        # Extract direct fields
        for key, value in data.items():
            if key == "sys":
                # Handle sys object specially
                if isinstance(value, dict):
                    for sys_key, sys_value in value.items():
                        if sys_key == "user_input":
                            continue  # Already handled above
                        extracted_fields[f"sys_{sys_key}"] = sys_value
            elif key in ["user_name", "expected", "id"]:
                # Handle special fields
                if key == "user_name":
                    user_name = value
                    extracted_fields[key] = value
                elif key == "expected":
                    expected = value
                    extracted_fields[key] = value
                elif key == "id":
                    extracted_fields[key] = value
            else:
                # Handle regular fields
                extracted_fields[key] = value
        
        # Handle user_name placeholder if present
        if user_name and "{user_name}" in str(extracted_fields):
            # Replace {user_name} placeholders in all string fields
            for field_key, field_value in extracted_fields.items():
                if isinstance(field_value, str):
                    extracted_fields[field_key] = field_value.replace("{user_name}", user_name)
        
        return ProcessedJsonData(
            original_data=data,
            extracted_fields=extracted_fields,
            sys_user_input=sys_user_input,
            user_name=user_name,
            expected=expected
        )
    
    def convert_to_testset_format(self, processed_data: List[ProcessedJsonData]) -> List[Dict[str, Any]]:
        """Convert processed data to project testset format.
        
        Args:
            processed_data: List of ProcessedJsonData objects
            
        Returns:
            List of dictionaries in JSONL testset format
        """
        testset_entries = []
        
        for i, data_entry in enumerate(processed_data):
            # Generate entry ID if not present
            entry_id = data_entry.extracted_fields.get("id", i + 1)
            
            # Create testset entry
            testset_entry = data_entry.get_testset_entry(entry_id)
            
            # Ensure required fields are present
            if "id" not in testset_entry:
                testset_entry["id"] = entry_id
            
            # Add tags if not present (optional field)
            if "tags" not in testset_entry:
                testset_entry["tags"] = []
            
            testset_entries.append(testset_entry)
        
        return testset_entries
    
    def save_testset(self, testset_data: List[Dict[str, Any]], agent_name: str, filename: str) -> Path:
        """Save testset data to the specified agent's testsets directory.
        
        Args:
            testset_data: List of testset entries
            agent_name: Name of the target agent
            filename: Name of the output file (should end with .jsonl)
            
        Returns:
            Path to the saved file
            
        Raises:
            ValueError: If agent doesn't exist or filename is invalid
        """
        if not self.validate_agent_exists(agent_name):
            raise ValueError(f"Agent '{agent_name}' does not exist")
        
        if not filename.endswith('.jsonl'):
            filename += '.jsonl'
        
        # Create testsets directory if it doesn't exist
        testsets_dir = self.agents_dir / agent_name / "testsets"
        testsets_dir.mkdir(parents=True, exist_ok=True)
        
        # Save testset data as JSONL
        output_path = testsets_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in testset_data:
                json.dump(entry, f, ensure_ascii=False, separators=(',', ':'))
                f.write('\n')
        
        return output_path
    
    def validate_agent_exists(self, agent_name: str) -> bool:
        """Validate that the target agent exists in the agents directory.
        
        Args:
            agent_name: Name of the agent to validate
            
        Returns:
            True if agent exists, False otherwise
        """
        agent_dir = self.agents_dir / agent_name
        agent_config = agent_dir / "agent.yaml"
        
        return agent_dir.exists() and agent_config.exists()
    
    def get_available_agents(self) -> List[str]:
        """Get list of available agents in the agents directory.
        
        Returns:
            List of agent names
        """
        if not self.agents_dir.exists():
            return []
        
        agents = []
        for item in self.agents_dir.iterdir():
            if item.is_dir() and (item / "agent.yaml").exists():
                agents.append(item.name)
        
        return sorted(agents)