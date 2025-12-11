#!/usr/bin/env python3
"""Demo script showing how to use the Agent Template Parser CLI."""

import tempfile
import json
from pathlib import Path
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from src.agent_template_parser.cli import AgentTemplateParserCLI


def create_sample_templates():
    """Create sample template files for demonstration."""
    # Create temporary directory for demo files
    temp_dir = Path(tempfile.mkdtemp())
    
    # Sample system prompt template
    system_prompt = """你是一个专业的对话总结专家。你的任务是分析用户提供的对话内容，并生成简洁、准确的总结。

请遵循以下原则：
1. 保持客观中立的语调
2. 突出对话的关键信息和要点
3. 使用清晰、简洁的语言
4. 如果对话涉及多个话题，请分别总结

用户输入的对话内容：${sys.user_input}

请为这段对话生成一个专业的总结。"""
    
    # Sample user input template
    user_input = """请总结以下对话内容：

{user_input}

请提供一个简洁的总结。"""
    
    # Sample test case
    test_case = {
        "sys": {
            "user_input": [
                {
                    "role": "user",
                    "content": "你好，我想了解一下你们公司的产品。"
                },
                {
                    "role": "assistant", 
                    "content": "您好！很高兴为您介绍我们的产品。我们主要提供AI驱动的客户服务解决方案。"
                },
                {
                    "role": "user",
                    "content": "听起来很有趣，能详细说说吗？"
                },
                {
                    "role": "assistant",
                    "content": "当然可以。我们的产品包括智能聊天机器人、语音识别系统和情感分析工具，可以帮助企业提升客户服务效率。"
                }
            ]
        },
        "user_input": "这是一段关于AI产品咨询的对话",
        "expected_output": "用户咨询AI客户服务解决方案，了解了智能聊天机器人、语音识别和情感分析等产品功能。"
    }
    
    # Write sample files
    system_file = temp_dir / "system_prompt.txt"
    user_file = temp_dir / "user_input.txt"
    test_file = temp_dir / "test_case.json"
    
    with open(system_file, 'w', encoding='utf-8') as f:
        f.write(system_prompt)
    
    with open(user_file, 'w', encoding='utf-8') as f:
        f.write(user_input)
    
    with open(test_file, 'w', encoding='utf-8') as f:
        json.dump(test_case, f, ensure_ascii=False, indent=2)
    
    return system_file, user_file, test_file


def demo_create_agent():
    """Demonstrate creating an agent from templates."""
    print("🚀 Agent Template Parser CLI Demo")
    print("=" * 50)
    
    # Create sample template files
    print("📝 Creating sample template files...")
    system_file, user_file, test_file = create_sample_templates()
    
    print(f"✅ Created sample files:")
    print(f"   - System prompt: {system_file}")
    print(f"   - User input: {user_file}")
    print(f"   - Test case: {test_file}")
    
    # Initialize CLI
    cli = AgentTemplateParserCLI()
    
    # Create agent from templates
    print("\n🔧 Creating agent from templates...")
    try:
        cli.create_agent_from_templates(
            system_prompt_file=str(system_file),
            user_input_file=str(user_file),
            test_case_file=str(test_file),
            agent_name="conversation_summarizer_demo",
            use_llm_enhancement=False  # Disable LLM for demo
        )
        print("✅ Agent created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating agent: {e}")
    
    # List available templates
    print("\n📋 Listing available templates...")
    cli.list_templates()
    
    # Validate templates
    print("\n🔍 Validating templates...")
    try:
        cli.validate_templates("conversation_summarizer_demo")
    except Exception as e:
        print(f"⚠️  Validation completed with issues: {e}")
    
    print("\n🎉 Demo completed!")
    print("\nTo use the CLI directly, run:")
    print("python -m src.agent_template_parser.cli --help")


def demo_batch_testset():
    """Demonstrate creating testsets from JSON files."""
    print("\n📊 Batch Testset Creation Demo")
    print("=" * 40)
    
    # Create sample JSON files
    temp_dir = Path(tempfile.mkdtemp())
    
    sample_data = [
        {
            "sys": {
                "user_input": [
                    {"role": "user", "content": "Hello, how are you?"},
                    {"role": "assistant", "content": "I'm doing well, thank you!"}
                ]
            },
            "user_input": "Greeting conversation",
            "expected_output": "A friendly greeting exchange"
        },
        {
            "sys": {
                "user_input": [
                    {"role": "user", "content": "What's the weather like?"},
                    {"role": "assistant", "content": "I don't have access to current weather data."}
                ]
            },
            "user_input": "Weather inquiry",
            "expected_output": "User asked about weather, assistant explained limitations"
        }
    ]
    
    json_files = []
    for i, data in enumerate(sample_data):
        json_file = temp_dir / f"sample_data_{i+1}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        json_files.append(str(json_file))
    
    print(f"📝 Created {len(json_files)} sample JSON files")
    
    # Initialize CLI
    cli = AgentTemplateParserCLI()
    
    # Note: This would fail because the target agent might not exist
    # This is just to demonstrate the CLI interface
    print("\n🔧 Attempting to create testset...")
    print("(This may fail if target agent doesn't exist - that's expected for demo)")
    
    try:
        cli.batch_create_testsets(
            json_files=json_files,
            target_agent="conversation_summarizer_demo",  # From previous demo
            output_filename="demo_testset.jsonl"
        )
        print("✅ Testset created successfully!")
    except Exception as e:
        print(f"⚠️  Expected error (agent may not exist): {e}")
    
    print("\n💡 To create testsets, first ensure the target agent exists")


if __name__ == "__main__":
    demo_create_agent()
    demo_batch_testset()