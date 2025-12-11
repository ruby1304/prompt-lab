"""Command Line Interface for Agent Template Parser."""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from .template_manager import TemplateManager
from .template_parser import TemplateParser, TemplateParsingError
from .config_generator import AgentConfigGenerator, ConfigGenerationError
from .llm_enhancer import LLMEnhancer, LLMEnhancementError
from .batch_data_processor import BatchDataProcessor
from .error_handler import (
    BatchProcessingError, 
    FileOperationError, 
    ValidationError,
    ErrorRecovery, 
    create_error_context,
    handle_error_with_recovery,
    InvalidFolderStructureError,
    MissingAgentFolderError
)

# Import the template converter from scripts
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
try:
    from convert_templates import TemplateConverter
except ImportError:
    TemplateConverter = None


# Constants for user guidance
FOLDER_STRUCTURE_EXAMPLE = """
Expected folder structure:
templates/{agent_name}/
├── system_prompt    (text file with system prompt)
├── user_input      (text file with user input template)
└── case           (JSON file with test case)

Example:
templates/my_agent/
├── system_prompt
├── user_input  
└── case
"""

LEGACY_STRUCTURE_EXAMPLE = """
Legacy structure:
templates/
├── system_prompts/
│   └── {agent_name}_system.txt
├── user_inputs/
│   └── {agent_name}_user.txt
└── test_cases/
    └── {agent_name}_test.json
"""

COMMON_MISTAKES = {
    'missing_folder': "Agent folder doesn't exist. Create templates/{agent_name}/ directory first.",
    'missing_files': "Required files missing in agent folder. Ensure all three files exist: system_prompt, user_input, case",
    'wrong_file_names': "Files have incorrect names. Use exactly: 'system_prompt', 'user_input', 'case' (no extensions)",
    'empty_files': "Template files are empty. Add content to your template files.",
    'invalid_json': "Test case file contains invalid JSON. Check the 'case' file format.",
    'mixed_structure': "Both folder and legacy structures exist. Consider using folder structure only."
}


class AgentTemplateParserCLI:
    """Command Line Interface for Agent Template Parser."""
    
    def __init__(self):
        self.template_manager = TemplateManager()
        self.template_parser = TemplateParser()
        self.config_generator = AgentConfigGenerator()
        self.llm_enhancer = LLMEnhancer()
        self.batch_processor = BatchDataProcessor()
        self.error_recovery = ErrorRecovery()
    
    def _provide_helpful_error_guidance(self, error: Exception, agent_name: str) -> None:
        """Provide helpful error messages and suggestions based on the error type.
        
        Args:
            error: The exception that occurred
            agent_name: Name of the agent being processed
        """
        print(f"❌ Error creating agent '{agent_name}': {error}")
        
        if isinstance(error, InvalidFolderStructureError):
            print("\n📁 Folder Structure Issue:")
            print(FOLDER_STRUCTURE_EXAMPLE)
            print("💡 Common fixes:")
            print(f"  - Create the directory: mkdir -p templates/{agent_name}")
            print(f"  - Add required files: touch templates/{agent_name}/{{system_prompt,user_input,case}}")
            
        elif isinstance(error, MissingAgentFolderError):
            print("\n📂 Agent Templates Not Found:")
            print(f"Looking for templates in: templates/{agent_name}/")
            print(FOLDER_STRUCTURE_EXAMPLE)
            print("💡 You can also use the legacy structure:")
            print(LEGACY_STRUCTURE_EXAMPLE.format(agent_name=agent_name))
            
        elif isinstance(error, FileOperationError):
            print("\n📄 File Operation Issue:")
            if "not found" in str(error).lower():
                print(COMMON_MISTAKES['missing_files'])
                print(FOLDER_STRUCTURE_EXAMPLE)
            elif "empty" in str(error).lower():
                print(COMMON_MISTAKES['empty_files'])
            else:
                print("💡 Check file permissions and paths")
                
        elif "json" in str(error).lower():
            print("\n🔧 JSON Format Issue:")
            print(COMMON_MISTAKES['invalid_json'])
            print("💡 Example valid test case:")
            print('{\n  "input": "test input",\n  "expected_output": "expected result"\n}')
            
        else:
            print("\n💡 General troubleshooting:")
            print("  - Verify your template folder structure")
            print("  - Check that all files contain valid content")
            print("  - Ensure file permissions allow reading")
            
        print(f"\n📖 For more help, run: python -m src.agent_template_parser.cli validate-templates --agent-name {agent_name}")
    
    def _suggest_common_fixes(self, agent_name: str) -> None:
        """Suggest common fixes for template issues.
        
        Args:
            agent_name: Name of the agent
        """
        template_path = Path(f"templates/{agent_name}")
        
        print("\n🔍 Checking for common issues...")
        
        if not template_path.exists():
            print(f"  ❌ Directory missing: {template_path}")
            print(f"  💡 Fix: mkdir -p {template_path}")
        else:
            print(f"  ✅ Directory exists: {template_path}")
            
            required_files = ['system_prompt', 'user_input', 'case']
            for file_name in required_files:
                file_path = template_path / file_name
                if not file_path.exists():
                    print(f"  ❌ File missing: {file_path}")
                    print(f"  💡 Fix: touch {file_path}")
                elif file_path.stat().st_size == 0:
                    print(f"  ⚠️  File empty: {file_path}")
                    print(f"  💡 Fix: Add content to {file_path}")
                else:
                    print(f"  ✅ File OK: {file_path}")
        
        # Check for legacy structure
        legacy_paths = [
            Path(f"templates/system_prompts/{agent_name}_system.txt"),
            Path(f"templates/user_inputs/{agent_name}_user.txt"),
            Path(f"templates/test_cases/{agent_name}_test.json")
        ]
        
        legacy_exists = any(p.exists() for p in legacy_paths)
        if legacy_exists:
            print("\n📋 Legacy structure detected:")
            for path in legacy_paths:
                status = "✅" if path.exists() else "❌"
                print(f"  {status} {path}")
            print("  💡 Consider migrating to folder structure for easier management")
    
    def create_agent_simple(self, agent_name: str, use_llm_enhancement: bool = True) -> None:
        """Create agent configuration using simplified folder-based template structure.
        
        Args:
            agent_name: Name of the agent to create
            use_llm_enhancement: Whether to use LLM enhancement for configuration fixing
        """
        context = create_error_context(
            operation="create_agent_simple",
            agent_name=agent_name,
            input_data={'agent_name': agent_name}
        )
        
        try:
            print(f"Creating agent '{agent_name}' from template folder...")
            
            # Load template files using enhanced TemplateManager
            try:
                template_files = self.template_manager.load_template_files(agent_name)
                print("✅ Template files loaded successfully")
            except FileNotFoundError as e:
                raise FileOperationError(str(e))
            except Exception as e:
                raise FileOperationError(f"Error loading template files: {e}")
            
            # Parse templates
            print("Parsing templates...")
            try:
                parsed_system = self.template_parser.parse_system_prompt(template_files['system_prompt'])
                parsed_user = self.template_parser.parse_user_input(template_files['user_input'])
                parsed_test = self.template_parser.parse_test_case(template_files['test_case'])
            except TemplateParsingError as e:
                # Try recovery
                recovery_result = self.error_recovery.handle_error(e, context)
                if recovery_result.success and recovery_result.recovered_data:
                    print("⚠️  Template parsing failed, using fallback template")
                    for warning in recovery_result.warnings:
                        print(f"Warning: {warning}")
                    parsed_data = recovery_result.recovered_data
                else:
                    print("❌ Template parsing failed:")
                    for suggestion in recovery_result.suggestions:
                        print(f"  💡 {suggestion}")
                    raise
            else:
                # Create ParsedTemplate object
                parsed_data = self.template_parser.create_parsed_template(
                    parsed_system, parsed_user, parsed_test
                )
            
            # Generate configuration
            print("Generating agent configuration...")
            try:
                agent_config = self.config_generator.generate_agent_yaml(parsed_data, agent_name)
                prompt_config = self.config_generator.generate_prompt_yaml(parsed_data, agent_name)
            except ConfigGenerationError as e:
                # Try recovery
                recovery_result = self.error_recovery.handle_error(e, context)
                if recovery_result.success and recovery_result.recovered_data:
                    print("⚠️  Configuration generation failed, using basic template")
                    for warning in recovery_result.warnings:
                        print(f"Warning: {warning}")
                    config_data = recovery_result.recovered_data
                    agent_config = config_data['agent_config']
                    prompt_config = config_data['prompt_config']
                else:
                    print("❌ Configuration generation failed:")
                    for suggestion in recovery_result.suggestions:
                        print(f"  💡 {suggestion}")
                    raise
            
            # Validate configuration format
            agent_errors = self.config_generator.validate_config_format(agent_config)
            prompt_errors = self.config_generator.validate_config_format(prompt_config)
            
            # If there are errors and LLM enhancement is enabled, use LLM to fix
            if (agent_errors or prompt_errors) and use_llm_enhancement:
                print("Configuration has format issues, applying LLM enhancement...")
                try:
                    if agent_errors:
                        agent_config = self.llm_enhancer.fix_config_format(agent_config, agent_errors)
                    if prompt_errors:
                        prompt_config = self.llm_enhancer.fix_config_format(prompt_config, prompt_errors)
                    print("LLM enhancement completed successfully")
                except LLMEnhancementError as e:
                    # Handle LLM enhancement failure
                    recovery_result = self.error_recovery.handle_error(e, context)
                    for warning in recovery_result.warnings:
                        print(f"⚠️  {warning}")
                    for suggestion in recovery_result.suggestions:
                        print(f"  💡 {suggestion}")
            
            # Save configuration files
            print("Saving configuration files...")
            try:
                # 从 parsed_data 中获取测试用例数据
                test_case_data = getattr(parsed_data, 'test_case_data', None)
                self.config_generator.save_config_files(agent_config, prompt_config, agent_name, test_case_data)
            except Exception as e:
                raise FileOperationError(f"Error saving configuration files: {e}")
            
            print(f"✅ Agent '{agent_name}' created successfully!")
            print(f"Configuration saved to: agents/{agent_name}/")
            
        except Exception as e:
            # Provide helpful error guidance
            self._provide_helpful_error_guidance(e, agent_name)
            self._suggest_common_fixes(agent_name)
            
            # Handle any remaining errors with recovery
            recovery_result = handle_error_with_recovery(e, context, self.error_recovery)
            
            if recovery_result.warnings:
                print("\n⚠️  Additional warnings:")
                for warning in recovery_result.warnings:
                    print(f"  - {warning}")
            
            if recovery_result.suggestions:
                print("\n💡 Additional suggestions:")
                for suggestion in recovery_result.suggestions:
                    print(f"  - {suggestion}")
            
            sys.exit(1)

    def create_agent_from_templates(
        self, 
        system_prompt_file: str, 
        user_input_file: str, 
        test_case_file: str, 
        agent_name: str,
        use_llm_enhancement: bool = True
    ) -> None:
        """从模板文件创建agent配置。
        
        Args:
            system_prompt_file: 系统提示词模板文件路径
            user_input_file: 用户输入模板文件路径
            test_case_file: 测试用例JSON文件路径
            agent_name: 要创建的agent名称
            use_llm_enhancement: 是否使用LLM增强处理
        """
        context = create_error_context(
            operation="create_agent_from_templates",
            agent_name=agent_name,
            input_data={'files': [system_prompt_file, user_input_file, test_case_file]}
        )
        
        try:
            print(f"Creating agent '{agent_name}' from templates...")
            
            # 验证输入文件存在
            files = [system_prompt_file, user_input_file, test_case_file]
            for file_path in files:
                if not Path(file_path).exists():
                    raise FileOperationError(f"Template file not found: {file_path}", file_path)
            
            # 读取模板文件内容
            try:
                with open(system_prompt_file, 'r', encoding='utf-8') as f:
                    system_prompt = f.read()
                
                with open(user_input_file, 'r', encoding='utf-8') as f:
                    user_input = f.read()
                
                with open(test_case_file, 'r', encoding='utf-8') as f:
                    test_case = f.read()
            except (IOError, UnicodeDecodeError) as e:
                raise FileOperationError(f"Error reading template files: {e}")
            
            # 保存模板文件到管理目录
            print("Saving template files...")
            try:
                self.template_manager.create_directory_structure()
                saved_files = self.template_manager.save_template_files(
                    system_prompt, user_input, test_case, agent_name
                )
                print(f"Template files saved: {list(saved_files.keys())}")
            except Exception as e:
                raise FileOperationError(f"Error saving template files: {e}")
            
            # 解析模板
            print("Parsing templates...")
            try:
                parsed_system = self.template_parser.parse_system_prompt(system_prompt)
                parsed_user = self.template_parser.parse_user_input(user_input)
                parsed_test = self.template_parser.parse_test_case(test_case)
            except TemplateParsingError as e:
                # Try recovery
                recovery_result = self.error_recovery.handle_error(e, context)
                if recovery_result.success and recovery_result.recovered_data:
                    print("⚠️  Template parsing failed, using fallback template")
                    for warning in recovery_result.warnings:
                        print(f"Warning: {warning}")
                    parsed_data = recovery_result.recovered_data
                else:
                    print("❌ Template parsing failed:")
                    for suggestion in recovery_result.suggestions:
                        print(f"  💡 {suggestion}")
                    raise
            else:
                # 创建 ParsedTemplate 对象
                parsed_data = self.template_parser.create_parsed_template(
                    parsed_system, parsed_user, parsed_test
                )
            
            # 生成配置
            print("Generating agent configuration...")
            try:
                agent_config = self.config_generator.generate_agent_yaml(parsed_data, agent_name)
                prompt_config = self.config_generator.generate_prompt_yaml(parsed_data, agent_name)
            except ConfigGenerationError as e:
                # Try recovery
                recovery_result = self.error_recovery.handle_error(e, context)
                if recovery_result.success and recovery_result.recovered_data:
                    print("⚠️  Configuration generation failed, using basic template")
                    for warning in recovery_result.warnings:
                        print(f"Warning: {warning}")
                    config_data = recovery_result.recovered_data
                    agent_config = config_data['agent_config']
                    prompt_config = config_data['prompt_config']
                else:
                    print("❌ Configuration generation failed:")
                    for suggestion in recovery_result.suggestions:
                        print(f"  💡 {suggestion}")
                    raise
            
            # 验证配置格式
            agent_errors = self.config_generator.validate_config_format(agent_config)
            prompt_errors = self.config_generator.validate_config_format(prompt_config)
            
            # 如果有错误且启用LLM增强，则使用LLM修正
            if (agent_errors or prompt_errors) and use_llm_enhancement:
                print("Configuration has format issues, applying LLM enhancement...")
                try:
                    if agent_errors:
                        agent_config = self.llm_enhancer.fix_config_format(agent_config, agent_errors)
                    if prompt_errors:
                        prompt_config = self.llm_enhancer.fix_config_format(prompt_config, prompt_errors)
                    print("LLM enhancement completed successfully")
                except LLMEnhancementError as e:
                    # Handle LLM enhancement failure
                    recovery_result = self.error_recovery.handle_error(e, context)
                    for warning in recovery_result.warnings:
                        print(f"⚠️  {warning}")
                    for suggestion in recovery_result.suggestions:
                        print(f"  💡 {suggestion}")
            
            # 保存配置文件
            print("Saving configuration files...")
            try:
                # 从 parsed_data 中获取测试用例数据
                test_case_data = getattr(parsed_data, 'test_case_data', None)
                self.config_generator.save_config_files(agent_config, prompt_config, agent_name, test_case_data)
            except Exception as e:
                raise FileOperationError(f"Error saving configuration files: {e}")
            
            print(f"✅ Agent '{agent_name}' created successfully!")
            print(f"Configuration saved to: agents/{agent_name}/")
            
        except Exception as e:
            # Handle any remaining errors
            recovery_result = handle_error_with_recovery(e, context, self.error_recovery)
            
            print(f"❌ Error creating agent: {e}")
            
            if recovery_result.warnings:
                for warning in recovery_result.warnings:
                    print(f"⚠️  {warning}")
            
            if recovery_result.suggestions:
                print("\n💡 Suggestions to fix the issue:")
                for suggestion in recovery_result.suggestions:
                    print(f"  - {suggestion}")
            
            sys.exit(1)
    
    def batch_create_testsets(
        self, 
        json_files: List[str], 
        target_agent: str, 
        output_filename: str
    ) -> None:
        """批量创建测试集。
        
        Args:
            json_files: JSON输入文件列表
            target_agent: 目标agent名称
            output_filename: 输出测试集文件名
        """
        context = create_error_context(
            operation="batch_create_testsets",
            agent_name=target_agent,
            input_data={'json_files': json_files, 'output_filename': output_filename}
        )
        
        try:
            print(f"Creating testset for agent '{target_agent}'...")
            
            # 验证目标agent存在
            if not self.batch_processor.validate_agent_exists(target_agent):
                raise BatchProcessingError(f"Target agent '{target_agent}' does not exist")
            
            # 验证输入文件存在
            missing_files = []
            for file_path in json_files:
                if not Path(file_path).exists():
                    missing_files.append(file_path)
            
            if missing_files:
                raise FileOperationError(
                    f"JSON files not found: {', '.join(missing_files)}", 
                    missing_files[0]
                )
            
            # 读取JSON文件内容
            json_inputs = []
            failed_files = []
            
            for file_path in json_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Validate JSON format
                        json.loads(content)  # This will raise JSONDecodeError if invalid
                        json_inputs.append(content)
                except (IOError, UnicodeDecodeError, json.JSONDecodeError) as e:
                    failed_files.append(f"{file_path}: {e}")
            
            if failed_files:
                raise BatchProcessingError(
                    f"Failed to read {len(failed_files)} JSON files",
                    failed_files
                )
            
            print(f"Processing {len(json_inputs)} JSON files...")
            
            # 批量处理JSON输入
            try:
                processed_data = self.batch_processor.process_json_inputs(json_inputs, target_agent)
            except Exception as e:
                raise BatchProcessingError(f"Error processing JSON inputs: {e}")
            
            # 转换为测试集格式
            try:
                testset_data = self.batch_processor.convert_to_testset_format(processed_data)
            except Exception as e:
                raise BatchProcessingError(f"Error converting to testset format: {e}")
            
            # 保存测试集
            try:
                output_path = self.batch_processor.save_testset(testset_data, target_agent, output_filename)
            except Exception as e:
                raise FileOperationError(f"Error saving testset: {e}")
            
            print(f"✅ Testset created successfully!")
            print(f"Output saved to: {output_path}")
            print(f"Generated {len(testset_data)} test cases")
            
        except Exception as e:
            # Handle errors with recovery
            recovery_result = handle_error_with_recovery(e, context, self.error_recovery)
            
            print(f"❌ Error creating testset: {e}")
            
            if recovery_result.warnings:
                for warning in recovery_result.warnings:
                    print(f"⚠️  {warning}")
            
            if recovery_result.suggestions:
                print("\n💡 Suggestions to fix the issue:")
                for suggestion in recovery_result.suggestions:
                    print(f"  - {suggestion}")
            
            sys.exit(1)
    
    def list_templates(self) -> None:
        """列出所有可用的模板。"""
        try:
            print("Available templates:")
            
            template_dir = Path("templates")
            if not template_dir.exists():
                print("No templates directory found. Run create command first to initialize.")
                return
            
            # 列出系统提示词模板
            system_dir = template_dir / "system_prompts"
            if system_dir.exists():
                system_files = list(system_dir.glob("*.txt"))
                if system_files:
                    print("\n📝 System Prompt Templates:")
                    for file in system_files:
                        print(f"  - {file.name}")
            
            # 列出用户输入模板
            user_dir = template_dir / "user_inputs"
            if user_dir.exists():
                user_files = list(user_dir.glob("*.txt"))
                if user_files:
                    print("\n👤 User Input Templates:")
                    for file in user_files:
                        print(f"  - {file.name}")
            
            # 列出测试用例模板
            test_dir = template_dir / "test_cases"
            if test_dir.exists():
                test_files = list(test_dir.glob("*.json"))
                if test_files:
                    print("\n🧪 Test Case Templates:")
                    for file in test_files:
                        print(f"  - {file.name}")
            
            if not any([
                (system_dir.exists() and list(system_dir.glob("*.txt"))),
                (user_dir.exists() and list(user_dir.glob("*.txt"))),
                (test_dir.exists() and list(test_dir.glob("*.json")))
            ]):
                print("No template files found.")
                
        except Exception as e:
            print(f"❌ Error listing templates: {e}")
            sys.exit(1)
    
    def validate_templates(self, agent_name: str) -> None:
        """验证模板文件的有效性。
        
        Args:
            agent_name: 要验证的agent名称
        """
        try:
            print(f"Validating templates for agent '{agent_name}'...")
            
            # 尝试加载模板文件
            try:
                template_files = self.template_manager.load_template_files(agent_name)
                print("✅ Template files loaded successfully")
            except FileNotFoundError as e:
                print(f"❌ Template file missing: {e}")
                return
            
            # 验证系统提示词模板
            try:
                parsed_system = self.template_parser.parse_system_prompt(
                    template_files['system_prompt']
                )
                print("✅ System prompt template is valid")
            except TemplateParsingError as e:
                print(f"❌ System prompt template error: {e}")
            
            # 验证用户输入模板
            try:
                parsed_user = self.template_parser.parse_user_input(
                    template_files['user_input']
                )
                print("✅ User input template is valid")
            except TemplateParsingError as e:
                print(f"❌ User input template error: {e}")
            
            # 验证测试用例模板
            try:
                parsed_test = self.template_parser.parse_test_case(
                    template_files['test_case']
                )
                print("✅ Test case template is valid")
            except (TemplateParsingError, json.JSONDecodeError) as e:
                print(f"❌ Test case template error: {e}")
            
            print(f"Template validation completed for '{agent_name}'")
            
        except Exception as e:
            print(f"❌ Error validating templates: {e}")
            sys.exit(1)


def main():
    """主命令行入口函数。"""
    parser = argparse.ArgumentParser(
        description="Agent Template Parser - Generate agent configurations from templates",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
🚀 QUICK START (Recommended):
  1. Create your template folder:
     mkdir -p templates/my_agent
  
  2. Add your template files:
     echo "You are a helpful assistant" > templates/my_agent/system_prompt
     echo "User question: {input}" > templates/my_agent/user_input
     echo '{"input": "test", "expected": "response"}' > templates/my_agent/case
  
  3. Create the agent:
     python -m src.agent_template_parser.cli create-agent my_agent

📁 FOLDER STRUCTURE:
  New simplified structure (recommended):
  templates/
  ├── my_agent/
  │   ├── system_prompt    # System prompt template (no extension)
  │   ├── user_input      # User input template (no extension)
  │   └── case           # Test case JSON (no extension)
  ├── customer_service/
  │   ├── system_prompt
  │   ├── user_input
  │   └── case
  └── ...

📋 EXAMPLES:
  # Create agent using simplified folder structure (RECOMMENDED)
  python -m src.agent_template_parser.cli create-agent my_agent
  python -m src.agent_template_parser.cli create-agent customer_service
  python -m src.agent_template_parser.cli create-agent data_analyzer

  # Create agent from specific template files (legacy support)
  python -m src.agent_template_parser.cli create-agent \\
    --system-prompt templates/system_prompts/my_agent_system.txt \\
    --user-input templates/user_inputs/my_agent_user.txt \\
    --test-case templates/test_cases/my_agent_test.json \\
    --agent-name my_agent

  # Batch create testsets
  python -m src.agent_template_parser.cli create-testset \\
    --json-files data1.json data2.json \\
    --target-agent existing_agent \\
    --output-filename batch_testset.jsonl

  # List available templates
  python -m src.agent_template_parser.cli list-templates

  # Validate templates
  python -m src.agent_template_parser.cli validate-templates --agent-name my_agent

  # Convert legacy templates to folder structure
  python -m src.agent_template_parser.cli convert-templates my_agent
  python -m src.agent_template_parser.cli convert-templates --list
  python -m src.agent_template_parser.cli convert-templates --dry-run

🔧 TROUBLESHOOTING:
  Common Issues:
  ❌ "Agent folder doesn't exist"
     → Create: mkdir -p templates/{agent_name}
  
  ❌ "Required files missing"
     → Add files: touch templates/{agent_name}/{system_prompt,user_input,case}
  
  ❌ "Template files are empty"
     → Add content to your template files
  
  ❌ "Invalid JSON in case file"
     → Ensure case file contains valid JSON: {"input": "test", "expected": "result"}
  
  ❌ "Wrong file names"
     → Use exact names: system_prompt, user_input, case (no extensions)

  Migration from Legacy:
  # Convert existing templates to new structure
  mkdir -p templates/my_agent
  mv templates/system_prompts/my_agent_system.txt templates/my_agent/system_prompt
  mv templates/user_inputs/my_agent_user.txt templates/my_agent/user_input
  mv templates/test_cases/my_agent_test.json templates/my_agent/case

💡 TIPS:
  - Use descriptive agent names (e.g., customer_service, data_analyzer)
  - Keep templates focused on a single, well-defined task
  - Test your templates with validate-templates command
  - Both folder and legacy structures are supported for backward compatibility
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Create agent command with support for both formats
    create_parser = subparsers.add_parser(
        'create-agent', 
        help='Create agent configuration from templates (use simplified folder structure)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="""
Create agent configuration from templates using either:
1. Simplified folder structure (recommended): templates/{agent_name}/
2. Legacy file-based structure (backward compatibility)

The simplified approach only requires the agent name and expects templates in:
templates/{agent_name}/system_prompt, templates/{agent_name}/user_input, templates/{agent_name}/case
        """
    )
    
    # Positional argument for simplified format
    create_parser.add_argument(
        'agent_name',
        nargs='?',
        help='Agent name (RECOMMENDED: uses templates/{agent_name}/ folder structure)'
    )
    
    # Optional arguments for legacy format
    create_parser.add_argument(
        '--system-prompt',
        help='Path to system prompt template file (legacy format only)'
    )
    create_parser.add_argument(
        '--user-input',
        help='Path to user input template file (legacy format only)'
    )
    create_parser.add_argument(
        '--test-case',
        help='Path to test case JSON file (legacy format only)'
    )
    create_parser.add_argument(
        '--agent-name',
        dest='legacy_agent_name',
        help='Name for the new agent (legacy format only)'
    )
    create_parser.add_argument(
        '--no-llm-enhancement', 
        action='store_true',
        help='Disable LLM enhancement for configuration fixing'
    )
    
    # Create testset command
    testset_parser = subparsers.add_parser(
        'create-testset', 
        help='Create testset from JSON files'
    )
    testset_parser.add_argument(
        '--json-files', 
        nargs='+', 
        required=True,
        help='List of JSON input files'
    )
    testset_parser.add_argument(
        '--target-agent', 
        required=True,
        help='Target agent name'
    )
    testset_parser.add_argument(
        '--output-filename', 
        required=True,
        help='Output testset filename'
    )
    
    # List templates command
    subparsers.add_parser(
        'list-templates', 
        help='List all available templates'
    )
    
    # Validate templates command
    validate_parser = subparsers.add_parser(
        'validate-templates', 
        help='Validate template files'
    )
    validate_parser.add_argument(
        '--agent-name', 
        required=True,
        help='Agent name to validate templates for'
    )
    
    # Convert templates command
    convert_parser = subparsers.add_parser(
        'convert-templates',
        help='Convert legacy templates to folder structure'
    )
    convert_parser.add_argument(
        'agent_name',
        nargs='?',
        help='Agent name to convert (optional, converts all if not specified)'
    )
    convert_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    convert_parser.add_argument(
        '--list',
        action='store_true',
        help='List all templates and their structures'
    )
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = AgentTemplateParserCLI()
    
    if args.command == 'create-agent':
        # Detect which format is being used
        # Get agent name from either positional argument or --agent-name flag
        positional_agent_name = getattr(args, 'agent_name', None)
        legacy_agent_name = getattr(args, 'legacy_agent_name', None)
        
        if (args.system_prompt and args.user_input and args.test_case and legacy_agent_name):
            # Legacy format with explicit file paths
            cli.create_agent_from_templates(
                args.system_prompt,
                args.user_input,
                args.test_case,
                legacy_agent_name,
                use_llm_enhancement=not args.no_llm_enhancement
            )
        elif positional_agent_name and not any([args.system_prompt, args.user_input, args.test_case]):
            # Simplified format with just agent name (positional)
            cli.create_agent_simple(
                positional_agent_name,
                use_llm_enhancement=not args.no_llm_enhancement
            )
        else:
            # Invalid combination of arguments
            print("❌ Invalid arguments for create-agent command.")
            print("\n🚀 RECOMMENDED USAGE:")
            print("   python -m src.agent_template_parser.cli create-agent <agent_name>")
            print("\n📁 Required folder structure:")
            print("   templates/<agent_name>/")
            print("   ├── system_prompt    # System prompt template")
            print("   ├── user_input      # User input template")
            print("   └── case           # Test case JSON")
            print("\n💡 Quick setup:")
            print("   mkdir -p templates/my_agent")
            print("   echo 'You are a helpful assistant' > templates/my_agent/system_prompt")
            print("   echo 'User: {input}' > templates/my_agent/user_input")
            print("   echo '{\"input\": \"test\", \"expected\": \"response\"}' > templates/my_agent/case")
            print("   python -m src.agent_template_parser.cli create-agent my_agent")
            print("\n📋 Legacy format (still supported):")
            print("   python -m src.agent_template_parser.cli create-agent \\")
            print("     --system-prompt <file> --user-input <file> --test-case <file> --agent-name <name>")
            print("\n🔧 For troubleshooting, run: python -m src.agent_template_parser.cli --help")
            sys.exit(1)
    elif args.command == 'create-testset':
        cli.batch_create_testsets(
            args.json_files,
            args.target_agent,
            args.output_filename
        )
    elif args.command == 'list-templates':
        cli.list_templates()
    elif args.command == 'validate-templates':
        cli.validate_templates(args.agent_name)
    elif args.command == 'convert-templates':
        if TemplateConverter is None:
            print("❌ Template converter not available. Please ensure scripts/convert_templates.py exists.")
            sys.exit(1)
        
        converter = TemplateConverter()
        
        if args.list:
            converter.list_all_templates()
        elif args.agent_name:
            # Convert specific agent
            success = converter.convert_legacy_to_folder(args.agent_name, dry_run=args.dry_run)
            if not success:
                sys.exit(1)
        else:
            # Convert all legacy templates
            legacy_templates = converter.find_legacy_templates()
            folder_templates = converter.find_folder_templates()
            
            conversion_candidates = [name for name in legacy_templates.keys() 
                                   if name not in folder_templates]
            
            if not conversion_candidates:
                print("✅ No legacy templates need conversion")
                return
            
            print(f"Found {len(conversion_candidates)} templates to convert:")
            for agent_name in conversion_candidates:
                print(f"  - {agent_name}")
            
            if args.dry_run:
                print(f"\nDry run - showing what would be done:")
                for agent_name in conversion_candidates:
                    print(f"\n--- {agent_name} ---")
                    converter.convert_legacy_to_folder(agent_name, dry_run=True)
            else:
                print(f"\nConverting {len(conversion_candidates)} templates...")
                response = input("Continue? (y/N): ")
                if response.lower() != 'y':
                    print("Conversion cancelled")
                    return
                
                success_count = 0
                for agent_name in conversion_candidates:
                    print(f"\n--- Converting {agent_name} ---")
                    if converter.convert_legacy_to_folder(agent_name, dry_run=False):
                        success_count += 1
                
                print(f"\n✅ Successfully converted {success_count}/{len(conversion_candidates)} templates")


if __name__ == '__main__':
    main()