#!/usr/bin/env python3
"""Demo script showing how to use the BatchDataProcessor."""

import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_template_parser import BatchDataProcessor


def main():
    """Demonstrate BatchDataProcessor usage."""
    print("=== BatchDataProcessor Demo ===\n")
    
    # Initialize the processor
    processor = BatchDataProcessor()
    
    # Show available agents
    print("Available agents:")
    agents = processor.get_available_agents()
    for agent in agents:
        print(f"  - {agent}")
    
    if not agents:
        print("  No agents found. Please ensure you have agents configured in the 'agents' directory.")
        return
    
    # Use the first available agent for demo
    target_agent = agents[0]
    print(f"\nUsing agent: {target_agent}")
    
    # Sample JSON inputs (similar to real testset format)
    sample_json_inputs = [
        json.dumps({
            "id": 1,
            "character_profile": "Demo character profile for testing",
            "current_schedule_time": "14:30",
            "current_schedule_full_desc": "Demo schedule description",
            "cloth_prompt": "默认服装",
            "chat_round_30": "Demo chat history content",
            "user_name": "{user_name}",
            "expected": "能正确处理测试数据"
        }),
        json.dumps({
            "id": 2,
            "sys": {
                "user_input": "Complex nested chat history with multiple rounds of conversation"
            },
            "character_profile": "Another demo character profile",
            "user_name": "DemoUser",
            "expected": "能正确处理嵌套数据结构"
        }),
        json.dumps({
            "id": 3,
            "field1": "value1",
            "field2": "value2",
            "user_name": "TestUser",
            "message": "Hello {user_name}, this is a test!",
            "expected": "能正确替换用户名占位符"
        })
    ]
    
    try:
        print(f"\n1. Processing {len(sample_json_inputs)} JSON inputs...")
        
        # Process JSON inputs
        processed_data = processor.process_json_inputs(sample_json_inputs, target_agent)
        print(f"   ✓ Successfully processed {len(processed_data)} entries")
        
        # Show some details about processed data
        for i, data in enumerate(processed_data):
            print(f"   Entry {i+1}: {len(data.extracted_fields)} fields extracted")
            if data.sys_user_input:
                print(f"     - Has sys.user_input: {len(str(data.sys_user_input))} chars")
            if data.user_name:
                print(f"     - User name: {data.user_name}")
        
        print("\n2. Converting to testset format...")
        
        # Convert to testset format
        testset_data = processor.convert_to_testset_format(processed_data)
        print(f"   ✓ Converted to {len(testset_data)} testset entries")
        
        # Show sample testset entry
        print(f"   Sample entry keys: {list(testset_data[0].keys())}")
        
        print("\n3. Saving testset...")
        
        # Save testset
        output_filename = "batch_processor_demo"
        output_path = processor.save_testset(testset_data, target_agent, output_filename)
        print(f"   ✓ Saved testset to: {output_path}")
        
        # Verify saved file
        if output_path.exists():
            with open(output_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            print(f"   ✓ File contains {len(lines)} lines")
            
            # Show first line as example
            first_entry = json.loads(lines[0])
            print(f"   First entry ID: {first_entry.get('id')}")
            print(f"   First entry fields: {len(first_entry)} total")
        
        print("\n=== Demo completed successfully! ===")
        
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())