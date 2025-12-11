# Design Document

## Overview

This design improves the agent creation workflow by implementing a simplified folder-based template structure and streamlined CLI interface. The new system allows developers to organize templates by agent name in dedicated folders with standardized file names, while maintaining backward compatibility with the existing structure.

## Architecture

### Current Structure
```
templates/
├── system_prompts/
│   └── {agent_name}_system.txt
├── user_inputs/
│   └── {agent_name}_user.txt
└── test_cases/
    └── {agent_name}_test.json
```

### New Structure
```
templates/
├── {agent_name}/
│   ├── system_prompt
│   ├── user_input
│   └── case
└── (legacy structure still supported)
```

### CLI Command Evolution
- **Current:** `python -m src.agent_template_parser.cli create-agent --system-prompt path1 --user-input path2 --test-case path3 --agent-name name`
- **New:** `python -m src.agent_template_parser.cli create-agent name`

## Components and Interfaces

### 1. Enhanced TemplateManager

**New Methods:**
- `load_agent_folder_templates(agent_name: str) -> Dict[str, str]`
- `validate_agent_folder_structure(agent_name: str) -> Tuple[bool, List[str]]`
- `get_template_structure_type(agent_name: str) -> str`  # Returns "folder" or "legacy"

**Modified Methods:**
- `load_template_files(agent_name: str)` - Enhanced to try folder structure first, then fall back to legacy

### 2. Updated CLI Interface

**New Command Signature:**
```python
# Primary new interface
create_agent_simple(agent_name: str) -> None

# Enhanced existing interface (backward compatibility)
create_agent_from_templates(
    system_prompt_file: Optional[str] = None,
    user_input_file: Optional[str] = None, 
    test_case_file: Optional[str] = None,
    agent_name: str,
    use_llm_enhancement: bool = True
) -> None
```

### 3. Template Structure Detection

**Detection Logic:**
1. Check for `templates/{agent_name}/` folder with required files
2. If not found, check legacy structure `templates/*/agent_name_*.txt`
3. If neither found, provide helpful error with expected structure

**File Mapping:**
- `system_prompt` → system prompt template
- `user_input` → user input template  
- `case` → test case JSON

## Data Models

### Enhanced TemplateStructure Enum
```python
class TemplateStructure(Enum):
    FOLDER = "folder"      # New agent-folder structure
    LEGACY = "legacy"      # Existing file-based structure
    MIXED = "mixed"        # Both structures present
```

### Template Location Info
```python
@dataclass
class TemplateLocation:
    structure_type: TemplateStructure
    agent_name: str
    system_prompt_path: Path
    user_input_path: Path
    test_case_path: Path
    base_path: Path
```

## Error Handling

### New Error Types
- `InvalidFolderStructureError` - When agent folder exists but missing required files
- `AmbiguousTemplateStructureError` - When both folder and legacy structures exist
- `MissingAgentFolderError` - When specified agent folder doesn't exist

### Error Messages with Helpful Guidance
```python
FOLDER_STRUCTURE_HELP = """
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
```

## Testing Strategy

### Unit Tests
1. **TemplateManager Tests**
   - Test folder structure detection
   - Test file loading from both structures
   - Test validation of folder contents
   - Test backward compatibility

2. **CLI Tests**
   - Test simplified command interface
   - Test backward compatibility with existing parameters
   - Test error handling and help messages

### Integration Tests
1. **End-to-End Workflow Tests**
   - Create agent using folder structure
   - Create agent using legacy structure
   - Test mixed environment scenarios

2. **Migration Tests**
   - Test conversion from legacy to folder structure
   - Test coexistence of both structures

### Test Data Structure
```
tests/fixtures/templates/
├── folder_structure_agent/
│   ├── system_prompt
│   ├── user_input
│   └── case
├── legacy_structure/
│   ├── system_prompts/legacy_agent_system.txt
│   ├── user_inputs/legacy_agent_user.txt
│   └── test_cases/legacy_agent_test.json
└── mixed_structure/
    ├── mixed_agent/          # Folder structure
    │   ├── system_prompt
    │   ├── user_input
    │   └── case
    └── system_prompts/       # Legacy structure
        └── mixed_agent_system.txt
```

## Implementation Phases

### Phase 1: Core Infrastructure
- Enhance TemplateManager with folder structure support
- Add template structure detection logic
- Implement new file loading methods

### Phase 2: CLI Enhancement
- Add simplified create-agent command
- Maintain backward compatibility
- Enhance error messages and help text

### Phase 3: Documentation and Migration
- Update README and documentation
- Provide migration examples
- Add validation tools for template structure

## Backward Compatibility Strategy

### Graceful Fallback
1. **Primary:** Try folder structure (`templates/{agent_name}/`)
2. **Fallback:** Try legacy structure (`templates/*/agent_name_*`)
3. **Error:** Provide guidance for both structures

### Migration Path
- Existing templates continue to work unchanged
- New templates can use simplified folder structure
- Optional migration utility to convert legacy to folder structure

### CLI Compatibility
- Old command syntax remains fully functional
- New simplified syntax is additive, not replacing
- Help text shows both options with preference for new syntax