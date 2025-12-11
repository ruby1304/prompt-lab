"""Configuration file generator for creating agent and prompt YAML files."""

import yaml
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import re

from .models import ParsedTemplate, GeneratedConfig


logger = logging.getLogger(__name__)


class ConfigGenerationError(Exception):
    """Exception raised when configuration generation fails."""
    pass


class AgentConfigGenerator:
    """Generator for creating agent and prompt configuration files."""
    
    def __init__(self, agents_dir: str = "agents"):
        """Initialize the configuration generator.
        
        Args:
            agents_dir: Directory where agent configurations are stored
        """
        self.agents_dir = Path(agents_dir)
        self.default_judge_agent = "judge_default"
        self.default_judge_flow = "judge_v2"
        self.default_model = "doubao-1-5-pro-32k-250115"
    
    def generate_agent_yaml(self, parsed_data: ParsedTemplate, agent_name: str) -> Dict[str, Any]:
        """Generate agent.yaml configuration.
        
        Args:
            parsed_data: Parsed template data
            agent_name: Name of the agent
            
        Returns:
            Dictionary containing agent configuration
            
        Raises:
            ConfigGenerationError: If generation fails
        """
        if not agent_name or not agent_name.strip():
            raise ConfigGenerationError("Agent name cannot be empty")
        
        if not parsed_data:
            raise ConfigGenerationError("Parsed data cannot be None")
        
        try:
            # Generate basic agent configuration
            agent_config = {
                "id": agent_name,
                "name": self._generate_display_name(agent_name),
                "type": "task",
                "description": self._generate_description(parsed_data, agent_name),
                "business_goal": self._generate_business_goal(parsed_data, agent_name),
                "expectations": self._generate_expectations(parsed_data),
                "default_testset": f"{agent_name}.jsonl",
                "flows": self._generate_flows(agent_name),
                "evaluation": self._generate_evaluation_config(),
                "case_fields": self._generate_case_fields(parsed_data)
            }
            
            logger.info(f"Generated agent configuration for {agent_name}")
            return agent_config
            
        except Exception as e:
            logger.error(f"Failed to generate agent configuration: {e}")
            raise ConfigGenerationError(f"Agent configuration generation failed: {e}")
    
    def generate_prompt_yaml(self, parsed_data: ParsedTemplate, agent_name: str, original_system_prompt: str = None, original_user_template: str = None) -> Dict[str, Any]:
        """Generate prompt.yaml configuration file.
        
        Args:
            parsed_data: Parsed template data
            agent_name: Name of the agent
            
        Returns:
            Dictionary containing prompt configuration
            
        Raises:
            ConfigGenerationError: If generation fails
        """
        if not agent_name or not agent_name.strip():
            raise ConfigGenerationError("Agent name cannot be empty")
        
        if not parsed_data:
            raise ConfigGenerationError("Parsed data cannot be None")
        
        try:
            # Use original content if provided, otherwise extract from parsed data
            system_prompt = original_system_prompt or self._extract_system_prompt_content(parsed_data)
            user_template = original_user_template or self._extract_user_template_content(parsed_data)
            
            prompt_config = {
                "name": f"flow_{agent_name}_v1",
                "description": f"Generated prompt configuration for {agent_name}",
                "system_prompt": system_prompt,
                "user_template": user_template,
                "defaults": self._generate_defaults(parsed_data)
            }
            
            logger.info(f"Generated prompt configuration for {agent_name}")
            return prompt_config
            
        except Exception as e:
            logger.error(f"Failed to generate prompt configuration: {e}")
            raise ConfigGenerationError(f"Prompt configuration generation failed: {e}")
    
    def validate_config_format(self, config: Dict[str, Any]) -> List[str]:
        """Validate generated configuration format.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        if not isinstance(config, dict):
            errors.append("Configuration must be a dictionary")
            return errors
        
        # Check for required fields based on config type
        if "flows" in config or "id" in config:  # This is an agent config
            errors.extend(self._validate_agent_config(config))
        elif "system_prompt" in config or "name" in config:  # This is a prompt config
            errors.extend(self._validate_prompt_config(config))
        else:
            errors.append("Unknown configuration type")
        
        return errors
    
    def save_config_files(
        self, 
        agent_config: Dict[str, Any], 
        prompt_config: Dict[str, Any], 
        agent_name: str,
        test_case_data: Dict[str, Any] = None
    ) -> None:
        """Save configuration files to agents directory.
        
        Args:
            agent_config: Agent configuration dictionary
            prompt_config: Prompt configuration dictionary
            agent_name: Name of the agent
            test_case_data: Test case data to save as testset (optional)
            
        Raises:
            ConfigGenerationError: If saving fails
        """
        if not agent_name or not agent_name.strip():
            raise ConfigGenerationError("Agent name cannot be empty")
        
        try:
            # Create agent directory structure
            agent_dir = self.agents_dir / agent_name
            prompts_dir = agent_dir / "prompts"
            testsets_dir = agent_dir / "testsets"
            
            # Create directories
            agent_dir.mkdir(parents=True, exist_ok=True)
            prompts_dir.mkdir(exist_ok=True)
            testsets_dir.mkdir(exist_ok=True)
            
            # Save agent.yaml
            agent_yaml_path = agent_dir / "agent.yaml"
            with open(agent_yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(agent_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            # Save prompt.yaml
            prompt_yaml_path = prompts_dir / f"{agent_name}_v1.yaml"
            with open(prompt_yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(prompt_config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            # Save testset if provided
            if test_case_data:
                testset_path = testsets_dir / f"{agent_name}.jsonl"
                # Convert test case to JSONL format
                testset_entry = [test_case_data]  # Wrap in array for JSONL format
                
                with open(testset_path, 'w', encoding='utf-8') as f:
                    import json
                    for entry in testset_entry:
                        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
                
                logger.debug(f"Testset saved to: {testset_path}")
            
            logger.info(f"Saved configuration files for {agent_name}")
            logger.debug(f"Agent config saved to: {agent_yaml_path}")
            logger.debug(f"Prompt config saved to: {prompt_yaml_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration files: {e}")
            raise ConfigGenerationError(f"Configuration file saving failed: {e}")
    
    def generate_complete_config(
        self, 
        parsed_data: ParsedTemplate, 
        agent_name: str,
        original_system_prompt: str = None,
        original_user_template: str = None
    ) -> GeneratedConfig:
        """Generate complete configuration with validation.
        
        Args:
            parsed_data: Parsed template data
            agent_name: Name of the agent
            
        Returns:
            GeneratedConfig object with all configuration and validation results
        """
        try:
            # Generate configurations
            agent_config = self.generate_agent_yaml(parsed_data, agent_name)
            prompt_config = self.generate_prompt_yaml(parsed_data, agent_name, original_system_prompt, original_user_template)
            
            # Validate configurations
            agent_errors = self.validate_config_format(agent_config)
            prompt_errors = self.validate_config_format(prompt_config)
            all_errors = agent_errors + prompt_errors
            
            # Determine if LLM enhancement is needed
            needs_enhancement = len(all_errors) > 0 or self._needs_enhancement(parsed_data)
            
            return GeneratedConfig(
                agent_config=agent_config,
                prompt_config=prompt_config,
                validation_errors=all_errors,
                needs_llm_enhancement=needs_enhancement,
                agent_name=agent_name
            )
            
        except Exception as e:
            logger.error(f"Failed to generate complete configuration: {e}")
            return GeneratedConfig(
                agent_config={},
                prompt_config={},
                validation_errors=[f"Configuration generation failed: {e}"],
                needs_llm_enhancement=True,
                agent_name=agent_name
            )
    
    def _generate_display_name(self, agent_name: str) -> str:
        """Generate a human-readable display name from agent name.
        
        Args:
            agent_name: Agent identifier
            
        Returns:
            Human-readable display name
        """
        # Convert snake_case or kebab-case to title case
        display_name = agent_name.replace('_', ' ').replace('-', ' ')
        display_name = ' '.join(word.capitalize() for word in display_name.split())
        return display_name
    
    def _generate_description(self, parsed_data: ParsedTemplate, agent_name: str) -> str:
        """Generate description based on parsed template data.
        
        Args:
            parsed_data: Parsed template data
            agent_name: Agent name
            
        Returns:
            Generated description
        """
        # Analyze variables to understand the agent's purpose
        variables = parsed_data.get_all_variables()
        
        description_parts = [f"Auto-generated agent: {self._generate_display_name(agent_name)}"]
        
        if variables:
            description_parts.append(f"Processes the following inputs: {', '.join(variables)}")
        
        if parsed_data.test_structure:
            if isinstance(parsed_data.test_structure, dict) and 'sys' in parsed_data.test_structure:
                description_parts.append("Handles structured input with system context")
        
        return " | ".join(description_parts)
    
    def _generate_business_goal(self, parsed_data: ParsedTemplate, agent_name: str) -> str:
        """Generate business goal based on parsed data.
        
        Args:
            parsed_data: Parsed template data
            agent_name: Agent name
            
        Returns:
            Generated business goal
        """
        goal_parts = [
            f"Provide automated processing for {self._generate_display_name(agent_name)} tasks:",
            "- Process input data according to defined templates",
            "- Generate consistent and reliable outputs",
            "- Support evaluation and testing workflows"
        ]
        
        if parsed_data.has_variables():
            goal_parts.append("- Handle dynamic variable substitution")
        
        return "\n".join(goal_parts)
    
    def _generate_expectations(self, parsed_data: ParsedTemplate) -> Dict[str, Any]:
        """Generate expectations based on parsed data.
        
        Args:
            parsed_data: Parsed template data
            
        Returns:
            Dictionary with must_have and nice_to_have expectations
        """
        must_have = [
            "Generate valid output for all inputs",
            "Handle variable substitution correctly"
        ]
        
        nice_to_have = [
            "Provide informative error messages for invalid inputs",
            "Maintain consistent output format"
        ]
        
        if parsed_data.has_variables():
            must_have.append("Process all template variables correctly")
        
        return {
            "must_have": must_have,
            "nice_to_have": nice_to_have
        }
    
    def _generate_flows(self, agent_name: str) -> List[Dict[str, str]]:
        """Generate flows configuration.
        
        Args:
            agent_name: Agent name
            
        Returns:
            List of flow configurations
        """
        return [
            {
                "name": f"{agent_name}_v1",
                "file": f"{agent_name}_v1.yaml",
                "notes": f"Generated flow for {agent_name}"
            }
        ]
    
    def _generate_evaluation_config(self) -> Dict[str, Any]:
        """Generate evaluation configuration.
        
        Returns:
            Dictionary with evaluation settings
        """
        return {
            "judge_agent_id": self.default_judge_agent,
            "judge_flow": self.default_judge_flow,
            "scale": {
                "min": 0,
                "max": 10
            },
            "preferred_judge_model": self.default_model,
            "temperature": 0.0,
            "rules": [
                {
                    "id": "reasonable_length",
                    "kind": "max_chars",
                    "target": "output",
                    "max_chars": 2000,
                    "action": "mark_bad"
                }
            ]
        }
    
    def _generate_case_fields(self, parsed_data: ParsedTemplate) -> List[Dict[str, Any]]:
        """Generate case fields based on parsed variables.
        
        Args:
            parsed_data: Parsed template data
            
        Returns:
            List of case field configurations
        """
        case_fields = []
        
        # Add fields based on variables found in templates
        for variable in parsed_data.get_all_variables():
            field_name = self._variable_to_field_name(variable)
            field_config = {
                "key": field_name,
                "label": self._generate_field_label(variable),
                "section": self._determine_field_section(variable),
                "required": self._is_required_field(variable)
            }
            case_fields.append(field_config)
        
        # Add standard fields
        case_fields.extend([
            {
                "key": "expected",
                "label": "Expected output description",
                "section": "meta",
                "required": False
            },
            {
                "key": "*",
                "label": "Raw sample JSON",
                "section": "raw",
                "as_json": True,
                "required": False
            }
        ])
        
        return case_fields
    
    def _extract_system_prompt_content(self, parsed_data: ParsedTemplate) -> str:
        """Extract system prompt content from parsed data.
        
        Args:
            parsed_data: Parsed template data
            
        Returns:
            System prompt content
        """
        # 优先使用原始系统提示词内容
        if parsed_data.system_content and parsed_data.system_content.strip():
            return parsed_data.system_content.strip()
        
        # 如果没有原始内容，生成基础模板
        base_prompt = "You are an AI assistant that processes the provided input data."
        
        if parsed_data.system_variables:
            # Add variable placeholders in the format expected by the system
            variable_section = "\n\nInput data:\n"
            for var in parsed_data.system_variables:
                clean_var = var.strip('{}$')
                # Use the proper variable reference format
                if var.startswith('${') and var.endswith('}'):
                    variable_section += f"{{{clean_var}}}\n"
                else:
                    variable_section += f"{var}\n"
            base_prompt += variable_section
        
        return base_prompt
    
    def _extract_user_template_content(self, parsed_data: ParsedTemplate) -> str:
        """Extract user template content from parsed data.
        
        Args:
            parsed_data: Parsed template data
            
        Returns:
            User template content
        """
        # 优先使用原始用户模板内容
        if parsed_data.user_content and parsed_data.user_content.strip():
            return parsed_data.user_content.strip()
        
        # 如果没有原始内容，生成基础模板
        if parsed_data.user_variables:
            template_parts = []
            for var in parsed_data.user_variables:
                clean_var = var.strip('{}$')
                # Use the proper variable reference format
                if var.startswith('${') and var.endswith('}'):
                    template_parts.append(f"{{{clean_var}}}")
                else:
                    template_parts.append(var)
            return "Process the following: " + " ".join(template_parts)
        else:
            return "Begin processing."
    
    def _generate_defaults(self, parsed_data: ParsedTemplate) -> Dict[str, str]:
        """Generate default values for variables.
        
        Args:
            parsed_data: Parsed template data
            
        Returns:
            Dictionary of default values
        """
        defaults = {}
        
        for variable in parsed_data.get_all_variables():
            clean_var = variable.strip('{}$')
            if clean_var in ['user', 'role']:
                defaults[clean_var] = f"{{{clean_var}}}"
            else:
                defaults[clean_var] = "Default value"
        
        return defaults
    
    def _validate_agent_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate agent configuration.
        
        Args:
            config: Agent configuration to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        required_fields = ['id', 'name', 'type', 'flows', 'evaluation']
        
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Validate flows
        if 'flows' in config:
            if not isinstance(config['flows'], list) or not config['flows']:
                errors.append("Flows must be a non-empty list")
            else:
                for i, flow in enumerate(config['flows']):
                    if not isinstance(flow, dict):
                        errors.append(f"Flow {i} must be a dictionary")
                    elif 'name' not in flow or 'file' not in flow:
                        errors.append(f"Flow {i} missing required fields (name, file)")
        
        # Validate evaluation
        if 'evaluation' in config:
            eval_config = config['evaluation']
            if not isinstance(eval_config, dict):
                errors.append("Evaluation must be a dictionary")
            else:
                required_eval_fields = ['judge_agent_id', 'scale']
                for field in required_eval_fields:
                    if field not in eval_config:
                        errors.append(f"Missing required evaluation field: {field}")
        
        return errors
    
    def _validate_prompt_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate prompt configuration.
        
        Args:
            config: Prompt configuration to validate
            
        Returns:
            List of validation errors
        """
        errors = []
        required_fields = ['name', 'system_prompt']
        
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Validate system_prompt is not empty
        if 'system_prompt' in config:
            if not config['system_prompt'] or not config['system_prompt'].strip():
                errors.append("System prompt cannot be empty")
        
        return errors
    
    def _needs_enhancement(self, parsed_data: ParsedTemplate) -> bool:
        """Determine if configuration needs LLM enhancement.
        
        Args:
            parsed_data: Parsed template data
            
        Returns:
            True if enhancement is recommended
        """
        # Enhancement is recommended if:
        # - There are many variables (complex template)
        # - The test structure is complex
        # - There are unmapped variables
        
        variable_count = len(parsed_data.get_all_variables())
        has_complex_structure = isinstance(parsed_data.test_structure, dict) and len(parsed_data.test_structure) > 3
        
        return variable_count > 5 or has_complex_structure
    
    def _variable_to_field_name(self, variable: str) -> str:
        """Convert variable name to field name.
        
        Args:
            variable: Variable name
            
        Returns:
            Field name
        """
        # Remove ${} or {} wrapper and clean up
        clean_var = variable.strip('{}$')
        return re.sub(r'[^a-zA-Z0-9_]', '_', clean_var).lower()
    
    def _generate_field_label(self, variable: str) -> str:
        """Generate human-readable label for field.
        
        Args:
            variable: Variable name
            
        Returns:
            Human-readable label
        """
        clean_var = variable.strip('{}$')
        return clean_var.replace('_', ' ').replace('.', ' ').title()
    
    def _determine_field_section(self, variable: str) -> str:
        """Determine which section a field belongs to.
        
        Args:
            variable: Variable name
            
        Returns:
            Section name
        """
        clean_var = variable.strip('{}$').lower()
        
        if clean_var in ['user', 'role']:
            return "context"
        elif 'input' in clean_var or 'query' in clean_var:
            return "primary_input"
        else:
            return "context"
    
    def _is_required_field(self, variable: str) -> bool:
        """Determine if a field is required.
        
        Args:
            variable: Variable name
            
        Returns:
            True if field is required
        """
        clean_var = variable.strip('{}$').lower()
        
        # Input fields are typically required
        return 'input' in clean_var or 'query' in clean_var or 'data' in clean_var