#!/usr/bin/env python3
"""
Template Conversion Utility

This script converts legacy template structure to the new folder-based structure.
It can also validate existing template structures.
"""

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class TemplateConverter:
    """Utility for converting and validating template structures."""
    
    def __init__(self):
        self.templates_dir = Path("templates")
        self.legacy_dirs = {
            'system_prompts': self.templates_dir / "system_prompts",
            'user_inputs': self.templates_dir / "user_inputs", 
            'test_cases': self.templates_dir / "test_cases"
        }
    
    def find_legacy_templates(self) -> Dict[str, Dict[str, Path]]:
        """Find all legacy template files and group them by agent name.
        
        Returns:
            Dictionary mapping agent names to their template file paths
        """
        legacy_templates = {}
        
        # Check system prompts
        if self.legacy_dirs['system_prompts'].exists():
            for file_path in self.legacy_dirs['system_prompts'].glob("*.txt"):
                # Extract agent name from filename (remove _system.txt suffix)
                name = file_path.stem
                if name.endswith('_system'):
                    agent_name = name[:-7]  # Remove '_system'
                    if agent_name not in legacy_templates:
                        legacy_templates[agent_name] = {}
                    legacy_templates[agent_name]['system_prompt'] = file_path
        
        # Check user inputs
        if self.legacy_dirs['user_inputs'].exists():
            for file_path in self.legacy_dirs['user_inputs'].glob("*.txt"):
                name = file_path.stem
                if name.endswith('_user'):
                    agent_name = name[:-5]  # Remove '_user'
                    if agent_name not in legacy_templates:
                        legacy_templates[agent_name] = {}
                    legacy_templates[agent_name]['user_input'] = file_path
        
        # Check test cases
        if self.legacy_dirs['test_cases'].exists():
            for file_path in self.legacy_dirs['test_cases'].glob("*.json"):
                name = file_path.stem
                if name.endswith('_test'):
                    agent_name = name[:-5]  # Remove '_test'
                    if agent_name not in legacy_templates:
                        legacy_templates[agent_name] = {}
                    legacy_templates[agent_name]['test_case'] = file_path
        
        # Filter out incomplete template sets
        complete_templates = {}
        for agent_name, files in legacy_templates.items():
            if all(key in files for key in ['system_prompt', 'user_input', 'test_case']):
                complete_templates[agent_name] = files
        
        return complete_templates
    
    def find_folder_templates(self) -> List[str]:
        """Find all folder-based templates.
        
        Returns:
            List of agent names with folder-based templates
        """
        folder_templates = []
        
        if not self.templates_dir.exists():
            return folder_templates
        
        for item in self.templates_dir.iterdir():
            if item.is_dir() and item.name not in ['system_prompts', 'user_inputs', 'test_cases']:
                # Check if it has the required files
                required_files = ['system_prompt', 'user_input', 'case']
                if all((item / file_name).exists() for file_name in required_files):
                    folder_templates.append(item.name)
        
        return folder_templates
    
    def validate_template_structure(self, agent_name: str) -> Tuple[bool, List[str]]:
        """Validate a template structure for completeness.
        
        Args:
            agent_name: Name of the agent to validate
            
        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []
        
        # Check folder structure
        folder_path = self.templates_dir / agent_name
        folder_valid = False
        
        if folder_path.exists() and folder_path.is_dir():
            required_files = ['system_prompt', 'user_input', 'case']
            missing_files = []
            empty_files = []
            
            for file_name in required_files:
                file_path = folder_path / file_name
                if not file_path.exists():
                    missing_files.append(file_name)
                elif file_path.stat().st_size == 0:
                    empty_files.append(file_name)
            
            if missing_files:
                issues.append(f"Missing files in folder structure: {', '.join(missing_files)}")
            if empty_files:
                issues.append(f"Empty files in folder structure: {', '.join(empty_files)}")
            
            # Validate JSON in case file
            if not missing_files and 'case' not in empty_files:
                try:
                    case_content = (folder_path / 'case').read_text(encoding='utf-8')
                    json.loads(case_content)
                except json.JSONDecodeError as e:
                    issues.append(f"Invalid JSON in case file: {e}")
                except Exception as e:
                    issues.append(f"Error reading case file: {e}")
            
            folder_valid = not missing_files and not empty_files
        
        # Check legacy structure
        legacy_templates = self.find_legacy_templates()
        legacy_valid = agent_name in legacy_templates
        
        if not folder_valid and not legacy_valid:
            issues.append(f"No valid template structure found for '{agent_name}'")
        elif folder_valid and legacy_valid:
            issues.append(f"Both folder and legacy structures exist for '{agent_name}' - consider using folder structure only")
        
        return (folder_valid or legacy_valid), issues
    
    def convert_legacy_to_folder(self, agent_name: str, dry_run: bool = False) -> bool:
        """Convert a legacy template to folder structure.
        
        Args:
            agent_name: Name of the agent to convert
            dry_run: If True, only show what would be done without making changes
            
        Returns:
            True if conversion was successful or would be successful
        """
        legacy_templates = self.find_legacy_templates()
        
        if agent_name not in legacy_templates:
            print(f"❌ No legacy template found for '{agent_name}'")
            return False
        
        files = legacy_templates[agent_name]
        target_dir = self.templates_dir / agent_name
        
        if target_dir.exists():
            print(f"⚠️  Target directory already exists: {target_dir}")
            if not dry_run:
                response = input("Overwrite existing folder structure? (y/N): ")
                if response.lower() != 'y':
                    print("Conversion cancelled")
                    return False
        
        print(f"Converting '{agent_name}' from legacy to folder structure...")
        
        if dry_run:
            print(f"Would create directory: {target_dir}")
            print(f"Would copy {files['system_prompt']} → {target_dir}/system_prompt")
            print(f"Would copy {files['user_input']} → {target_dir}/user_input")
            print(f"Would copy {files['test_case']} → {target_dir}/case")
            return True
        
        try:
            # Create target directory
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy files with new names
            shutil.copy2(files['system_prompt'], target_dir / 'system_prompt')
            shutil.copy2(files['user_input'], target_dir / 'user_input')
            shutil.copy2(files['test_case'], target_dir / 'case')
            
            print(f"✅ Successfully converted '{agent_name}' to folder structure")
            print(f"   Created: {target_dir}")
            print(f"   Files: system_prompt, user_input, case")
            
            return True
            
        except Exception as e:
            print(f"❌ Error converting '{agent_name}': {e}")
            return False
    
    def list_all_templates(self) -> None:
        """List all available templates in both structures."""
        print("📋 Template Structure Analysis")
        print("=" * 50)
        
        # Find templates
        legacy_templates = self.find_legacy_templates()
        folder_templates = self.find_folder_templates()
        
        # Show folder templates
        if folder_templates:
            print(f"\n📁 Folder-based templates ({len(folder_templates)}):")
            for agent_name in sorted(folder_templates):
                print(f"  ✅ {agent_name}")
                # Check if legacy also exists
                if agent_name in legacy_templates:
                    print(f"     ⚠️  Also has legacy structure")
        else:
            print("\n📁 Folder-based templates: None found")
        
        # Show legacy templates
        if legacy_templates:
            print(f"\n📋 Legacy templates ({len(legacy_templates)}):")
            for agent_name in sorted(legacy_templates.keys()):
                if agent_name not in folder_templates:
                    print(f"  📄 {agent_name} (can be converted)")
        else:
            print("\n📋 Legacy templates: None found")
        
        # Show conversion candidates
        conversion_candidates = [name for name in legacy_templates.keys() 
                               if name not in folder_templates]
        
        if conversion_candidates:
            print(f"\n🔄 Conversion candidates ({len(conversion_candidates)}):")
            for agent_name in sorted(conversion_candidates):
                print(f"  → {agent_name}")
            print(f"\n💡 Convert with: python scripts/convert_templates.py convert <agent_name>")
        
        # Summary
        total_agents = len(set(folder_templates) | set(legacy_templates.keys()))
        print(f"\n📊 Summary: {total_agents} total agents")
        print(f"   - {len(folder_templates)} using folder structure")
        print(f"   - {len(conversion_candidates)} using legacy structure only")
        print(f"   - {len(folder_templates) - len(set(folder_templates) - set(legacy_templates.keys()))} with both structures")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Template Conversion and Validation Utility",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
EXAMPLES:
  # List all templates and their structures
  python scripts/convert_templates.py list

  # Validate a specific template
  python scripts/convert_templates.py validate my_agent

  # Convert legacy template to folder structure
  python scripts/convert_templates.py convert my_agent

  # Convert all legacy templates
  python scripts/convert_templates.py convert-all

  # Dry run (show what would be done)
  python scripts/convert_templates.py convert my_agent --dry-run

TEMPLATE STRUCTURES:
  Folder structure (recommended):
    templates/my_agent/
    ├── system_prompt    # System prompt template
    ├── user_input      # User input template
    └── case           # Test case JSON

  Legacy structure:
    templates/
    ├── system_prompts/my_agent_system.txt
    ├── user_inputs/my_agent_user.txt
    └── test_cases/my_agent_test.json
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List all templates and their structures')
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate template structure')
    validate_parser.add_argument('agent_name', help='Agent name to validate')
    
    # Convert command
    convert_parser = subparsers.add_parser('convert', help='Convert legacy template to folder structure')
    convert_parser.add_argument('agent_name', help='Agent name to convert')
    convert_parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    
    # Convert all command
    convert_all_parser = subparsers.add_parser('convert-all', help='Convert all legacy templates to folder structure')
    convert_all_parser.add_argument('--dry-run', action='store_true', help='Show what would be done without making changes')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    converter = TemplateConverter()
    
    if args.command == 'list':
        converter.list_all_templates()
    
    elif args.command == 'validate':
        is_valid, issues = converter.validate_template_structure(args.agent_name)
        
        print(f"Validating template structure for '{args.agent_name}'...")
        
        if is_valid:
            print(f"✅ Template structure is valid")
        else:
            print(f"❌ Template structure has issues:")
            for issue in issues:
                print(f"   - {issue}")
        
        if issues:
            print(f"\n💡 Issues found:")
            for issue in issues:
                print(f"   - {issue}")
    
    elif args.command == 'convert':
        success = converter.convert_legacy_to_folder(args.agent_name, dry_run=args.dry_run)
        if not success:
            sys.exit(1)
    
    elif args.command == 'convert-all':
        legacy_templates = converter.find_legacy_templates()
        folder_templates = converter.find_folder_templates()
        
        # Find templates that need conversion
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