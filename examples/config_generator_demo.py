#!/usr/bin/env python3
"""
Demonstration of the AgentConfigGenerator functionality.

This script shows how to use the configuration generator to create
agent and prompt configurations from parsed template data.
"""

import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agent_template_parser import (
    TemplateParser,
    AgentConfigGenerator,
    ParsedTemplate
)


def main():
    """Demonstrate the configuration generation process."""
    print("🚀 Agent Configuration Generator Demo")
    print("=" * 50)
    
    # Sample template content
    system_prompt = """You are a conversation summarizer expert.
Your task is to summarize conversations between {user} and {role}.

Process the following content:
{fullContent}

Requirements:
- Generate 4-10 sentences
- Use objective third-person perspective
- Replace all user references with {user}
- Replace all role references with {role}
- Preserve specific dates and time periods"""
    
    user_input = "Begin summarization."
    
    test_case = """{
    "sys": {
        "user_input": [
            "User: Hello, how are you today?",
            "Assistant: I'm doing well, thank you for asking!"
        ]
    },
    "fullContent": "2024-01-01 Morning: User greeted Assistant warmly and inquired about wellbeing.",
    "user": "{user}",
    "role": "{role}"
}"""
    
    print("📝 Sample Templates:")
    print(f"System Prompt: {len(system_prompt)} characters")
    print(f"User Input: {user_input}")
    print(f"Test Case: {len(test_case)} characters")
    print()
    
    # Initialize components
    parser = TemplateParser()
    
    with tempfile.TemporaryDirectory() as temp_dir:
        generator = AgentConfigGenerator(agents_dir=temp_dir)
        
        print("🔍 Parsing Templates...")
        
        # Parse templates
        system_info = parser.parse_system_prompt(system_prompt)
        user_info = parser.parse_user_input(user_input)
        test_info = parser.parse_test_case(test_case)
        
        print(f"✅ Found {len(system_info['variables'])} variables in system prompt")
        print(f"✅ Found {len(user_info['variables'])} variables in user input")
        print(f"✅ Parsed test case with {len(test_info['data'])} fields")
        
        # Create parsed template
        parsed_template = parser.create_parsed_template(system_info, user_info, test_info)
        
        print(f"📊 Total unique variables: {len(parsed_template.get_all_variables())}")
        print(f"Variables: {parsed_template.get_all_variables()}")
        print()
        
        print("⚙️ Generating Configurations...")
        
        agent_name = "conversation_summarizer"
        
        # Generate complete configuration
        config = generator.generate_complete_config(
            parsed_template,
            agent_name,
            original_system_prompt=system_prompt,
            original_user_template=user_input
        )
        
        print(f"✅ Generated configuration for '{agent_name}'")
        print(f"📋 Agent config fields: {len(config.agent_config)}")
        print(f"📝 Prompt config fields: {len(config.prompt_config)}")
        print(f"⚠️ Validation errors: {len(config.validation_errors)}")
        print(f"🤖 Needs LLM enhancement: {config.needs_llm_enhancement}")
        print()
        
        if config.validation_errors:
            print("⚠️ Validation Errors:")
            for error in config.validation_errors:
                print(f"  - {error}")
            print()
        
        print("💾 Saving Configuration Files...")
        
        # Save configuration files
        generator.save_config_files(
            config.agent_config,
            config.prompt_config,
            agent_name
        )
        
        # Show saved files
        agent_dir = Path(temp_dir) / agent_name
        agent_yaml = agent_dir / "agent.yaml"
        prompt_yaml = agent_dir / "prompts" / f"{agent_name}_v1.yaml"
        
        print(f"✅ Saved agent.yaml ({agent_yaml.stat().st_size} bytes)")
        print(f"✅ Saved prompt.yaml ({prompt_yaml.stat().st_size} bytes)")
        print()
        
        print("📄 Generated Agent Configuration Preview:")
        print("-" * 40)
        print(f"ID: {config.agent_config['id']}")
        print(f"Name: {config.agent_config['name']}")
        print(f"Type: {config.agent_config['type']}")
        print(f"Flows: {len(config.agent_config['flows'])}")
        print(f"Case Fields: {len(config.agent_config['case_fields'])}")
        print()
        
        print("📄 Generated Prompt Configuration Preview:")
        print("-" * 40)
        print(f"Name: {config.prompt_config['name']}")
        print(f"System Prompt: {len(config.prompt_config['system_prompt'])} chars")
        print(f"User Template: {config.prompt_config['user_template']}")
        print(f"Defaults: {list(config.prompt_config['defaults'].keys())}")
        print()
        
        print("🎯 Key Features Demonstrated:")
        print("✅ Template parsing and variable extraction")
        print("✅ Agent configuration generation")
        print("✅ Prompt configuration generation")
        print("✅ Configuration validation")
        print("✅ File saving with proper directory structure")
        print("✅ Original template content preservation")
        print()
        
        print("🏁 Demo completed successfully!")
        print(f"📁 Files were saved to: {agent_dir}")


if __name__ == "__main__":
    main()