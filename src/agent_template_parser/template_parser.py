"""Template parsing engine for extracting variables and processing template content."""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
import logging

from .models import ParsedTemplate


logger = logging.getLogger(__name__)


# Variable mapping rules for converting template variables to agent config fields
VARIABLE_MAPPINGS = {
    "${sys.user_input}": "chat_round_30",  # 映射到对话历史字段
    "{user}": "{user}",  # 保留用户占位符
    "{role}": "{role}",  # 保留角色占位符
    "${input}": "input",  # 通用输入字段
    "${query}": "query",  # 查询字段
    "${context}": "context",  # 上下文字段
    "${data}": "data",  # 数据字段
}


class TemplateParsingError(Exception):
    """Exception raised when template parsing fails."""
    pass


class TemplateParser:
    """Parser for processing template files and extracting variables."""
    
    def __init__(self):
        """Initialize the template parser."""
        self.variable_pattern = re.compile(r'\$\{([^}]+)\}')  # Matches ${variable}
        self.simple_variable_pattern = re.compile(r'\{([^}]+)\}')  # Matches {variable}
    
    def parse_system_prompt(self, content: str) -> Dict[str, Any]:
        """Parse system prompt template and extract variable placeholders.
        
        Args:
            content: System prompt template content
            
        Returns:
            Dictionary containing parsed information
            
        Raises:
            TemplateParsingError: If parsing fails
        """
        if not content or not content.strip():
            raise TemplateParsingError("System prompt content cannot be empty")
        
        try:
            # Extract variables
            variables = self.extract_variables(content)
            
            # Analyze content structure
            lines = content.strip().split('\n')
            non_empty_lines = [line.strip() for line in lines if line.strip()]
            
            parsed_info = {
                'content': content,
                'variables': variables,
                'line_count': len(lines),
                'non_empty_line_count': len(non_empty_lines),
                'has_variables': len(variables) > 0,
                'variable_positions': self._find_variable_positions(content, variables)
            }
            
            logger.debug(f"Parsed system prompt: {len(variables)} variables found")
            return parsed_info
            
        except Exception as e:
            logger.error(f"Failed to parse system prompt: {e}")
            raise TemplateParsingError(f"System prompt parsing failed: {e}")
    
    def parse_user_input(self, content: str) -> Dict[str, Any]:
        """Parse user input template and identify variable structure.
        
        Args:
            content: User input template content
            
        Returns:
            Dictionary containing parsed information
            
        Raises:
            TemplateParsingError: If parsing fails
        """
        if not content or not content.strip():
            raise TemplateParsingError("User input content cannot be empty")
        
        try:
            # Extract variables
            variables = self.extract_variables(content)
            
            # Analyze template structure
            template_structure = self._analyze_template_structure(content)
            
            parsed_info = {
                'content': content,
                'variables': variables,
                'structure': template_structure,
                'has_variables': len(variables) > 0,
                'is_simple_template': self._is_simple_template(content),
                'variable_positions': self._find_variable_positions(content, variables)
            }
            
            logger.debug(f"Parsed user input: {len(variables)} variables found")
            return parsed_info
            
        except Exception as e:
            logger.error(f"Failed to parse user input: {e}")
            raise TemplateParsingError(f"User input parsing failed: {e}")
    
    def parse_test_case(self, content: str) -> Dict[str, Any]:
        """Parse test case JSON and understand data structure.
        
        Args:
            content: Test case JSON content
            
        Returns:
            Dictionary containing parsed information
            
        Raises:
            TemplateParsingError: If parsing fails
        """
        if not content or not content.strip():
            raise TemplateParsingError("Test case content cannot be empty")
        
        try:
            # Parse JSON
            test_data = json.loads(content)
            
            # Analyze structure
            structure_info = self._analyze_json_structure(test_data)
            
            # Extract potential variable names from the JSON structure
            json_variables = self._extract_json_variables(test_data)
            
            parsed_info = {
                'content': content,
                'data': test_data,
                'structure': structure_info,
                'json_variables': json_variables,
                'has_sys_structure': 'sys' in test_data if isinstance(test_data, dict) else False,
                'has_user_input': self._has_user_input_structure(test_data),
                'data_types': self._get_data_types(test_data)
            }
            
            logger.debug(f"Parsed test case: {len(json_variables)} potential variables found")
            return parsed_info
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in test case: {e}")
            raise TemplateParsingError(f"Invalid JSON in test case: {e}")
        except Exception as e:
            logger.error(f"Failed to parse test case: {e}")
            raise TemplateParsingError(f"Test case parsing failed: {e}")
    
    def extract_variables(self, text: str) -> List[str]:
        """Extract ${} format variable placeholders from text.
        
        Args:
            text: Text to extract variables from
            
        Returns:
            List of unique variable names found
        """
        if not text:
            return []
        
        variables = set()
        
        # Extract ${variable} format
        dollar_variables = self.variable_pattern.findall(text)
        for var in dollar_variables:
            variables.add(f"${{{var}}}")
        
        # Extract {variable} format (simple variables)
        simple_variables = self.simple_variable_pattern.findall(text)
        for var in simple_variables:
            # Skip if it's already captured as ${variable}
            if f"${{{var}}}" not in variables:
                variables.add(f"{{{var}}}")
        
        return sorted(list(variables))
    
    def map_variables_to_config(self, variables: List[str]) -> Dict[str, str]:
        """Map variables to agent configuration fields.
        
        Args:
            variables: List of variables to map
            
        Returns:
            Dictionary mapping variables to config fields
        """
        mappings = {}
        
        for variable in variables:
            # Check if we have a predefined mapping
            if variable in VARIABLE_MAPPINGS:
                mappings[variable] = VARIABLE_MAPPINGS[variable]
            else:
                # Generate a mapping based on variable name
                mapped_field = self._generate_field_mapping(variable)
                mappings[variable] = mapped_field
        
        return mappings
    
    def create_parsed_template(
        self, 
        system_info: Dict[str, Any], 
        user_info: Dict[str, Any], 
        test_info: Dict[str, Any]
    ) -> ParsedTemplate:
        """Create a ParsedTemplate object from parsed information.
        
        Args:
            system_info: Parsed system prompt information
            user_info: Parsed user input information
            test_info: Parsed test case information
            
        Returns:
            ParsedTemplate object with all extracted information
        """
        # Combine variables from all sources
        system_variables = system_info.get('variables', [])
        user_variables = user_info.get('variables', [])
        
        # Create variable mappings
        all_variables = list(set(system_variables + user_variables))
        variable_mappings = self.map_variables_to_config(all_variables)
        
        return ParsedTemplate(
            system_variables=system_variables,
            user_variables=user_variables,
            test_structure=test_info.get('data', {}),
            variable_mappings=variable_mappings,
            system_content=system_info.get('content', ''),
            user_content=user_info.get('content', ''),
            test_case_data=test_info.get('data', {})
        )
    
    def _find_variable_positions(self, text: str, variables: List[str]) -> Dict[str, List[int]]:
        """Find positions of variables in text.
        
        Args:
            text: Text to search in
            variables: Variables to find positions for
            
        Returns:
            Dictionary mapping variables to their positions
        """
        positions = {}
        
        for variable in variables:
            # Remove the ${} or {} wrapper to get the actual variable name
            if variable.startswith('${') and variable.endswith('}'):
                search_pattern = re.escape(variable)
            elif variable.startswith('{') and variable.endswith('}'):
                search_pattern = re.escape(variable)
            else:
                search_pattern = re.escape(variable)
            
            matches = list(re.finditer(search_pattern, text))
            positions[variable] = [match.start() for match in matches]
        
        return positions
    
    def _analyze_template_structure(self, content: str) -> Dict[str, Any]:
        """Analyze the structure of a template.
        
        Args:
            content: Template content to analyze
            
        Returns:
            Dictionary with structure information
        """
        lines = content.split('\n')
        
        return {
            'total_lines': len(lines),
            'non_empty_lines': len([line for line in lines if line.strip()]),
            'has_multiline': len(lines) > 1,
            'average_line_length': sum(len(line) for line in lines) / len(lines) if lines else 0,
            'max_line_length': max(len(line) for line in lines) if lines else 0
        }
    
    def _analyze_json_structure(self, data: Any) -> Dict[str, Any]:
        """Analyze the structure of JSON data.
        
        Args:
            data: JSON data to analyze
            
        Returns:
            Dictionary with structure information
        """
        def count_nested_levels(obj, level=0):
            if isinstance(obj, dict):
                if not obj:
                    return level
                return max(count_nested_levels(v, level + 1) for v in obj.values())
            elif isinstance(obj, list):
                if not obj:
                    return level
                return max(count_nested_levels(item, level + 1) for item in obj)
            else:
                return level
        
        return {
            'type': type(data).__name__,
            'is_dict': isinstance(data, dict),
            'is_list': isinstance(data, list),
            'nested_levels': count_nested_levels(data),
            'total_keys': len(data) if isinstance(data, dict) else 0,
            'has_nested_objects': self._has_nested_objects(data)
        }
    
    def _extract_json_variables(self, data: Any, prefix: str = "") -> List[str]:
        """Extract potential variable names from JSON structure.
        
        Args:
            data: JSON data to extract from
            prefix: Prefix for nested keys
            
        Returns:
            List of potential variable names
        """
        variables = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                variables.append(full_key)
                
                # Recursively extract from nested objects
                if isinstance(value, (dict, list)):
                    variables.extend(self._extract_json_variables(value, full_key))
        
        elif isinstance(data, list) and data:
            # For lists, analyze the first item to understand structure
            if isinstance(data[0], dict):
                variables.extend(self._extract_json_variables(data[0], prefix))
        
        return variables
    
    def _has_user_input_structure(self, data: Any) -> bool:
        """Check if JSON has user input structure.
        
        Args:
            data: JSON data to check
            
        Returns:
            True if it has user input structure
        """
        if not isinstance(data, dict):
            return False
        
        # Check for common user input patterns
        user_input_keys = ['sys', 'user_input', 'input', 'query', 'message']
        
        for key in user_input_keys:
            if key in data:
                return True
        
        # Check for nested user input
        if 'sys' in data and isinstance(data['sys'], dict):
            return 'user_input' in data['sys']
        
        return False
    
    def _get_data_types(self, data: Any) -> Dict[str, str]:
        """Get data types of JSON values.
        
        Args:
            data: JSON data to analyze
            
        Returns:
            Dictionary mapping keys to their data types
        """
        types = {}
        
        if isinstance(data, dict):
            for key, value in data.items():
                types[key] = type(value).__name__
                
                # For nested objects, add nested types
                if isinstance(value, dict):
                    nested_types = self._get_data_types(value)
                    for nested_key, nested_type in nested_types.items():
                        types[f"{key}.{nested_key}"] = nested_type
        
        return types
    
    def _has_nested_objects(self, data: Any) -> bool:
        """Check if data has nested objects.
        
        Args:
            data: Data to check
            
        Returns:
            True if it has nested objects
        """
        if isinstance(data, dict):
            return any(isinstance(value, (dict, list)) for value in data.values())
        elif isinstance(data, list):
            return any(isinstance(item, (dict, list)) for item in data)
        
        return False
    
    def _is_simple_template(self, content: str) -> bool:
        """Check if template is simple (single line, few variables).
        
        Args:
            content: Template content
            
        Returns:
            True if template is simple
        """
        lines = content.strip().split('\n')
        variables = self.extract_variables(content)
        
        return len(lines) <= 2 and len(variables) <= 3
    
    def _generate_field_mapping(self, variable: str) -> str:
        """Generate a field mapping for an unmapped variable.
        
        Args:
            variable: Variable to generate mapping for
            
        Returns:
            Generated field name
        """
        # Remove ${} or {} wrapper
        if variable.startswith('${') and variable.endswith('}'):
            clean_var = variable[2:-1]
        elif variable.startswith('{') and variable.endswith('}'):
            clean_var = variable[1:-1]
        else:
            clean_var = variable
        
        # Convert to snake_case and clean up
        clean_var = re.sub(r'[^a-zA-Z0-9_]', '_', clean_var)
        clean_var = re.sub(r'_+', '_', clean_var)
        clean_var = clean_var.strip('_').lower()
        
        return clean_var if clean_var else 'unknown_field'