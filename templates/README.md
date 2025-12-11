# Templates Directory

This directory contains input template files for the Agent Template Parser system.

## Recommended Structure (New)

The preferred way to organize templates is using agent-specific folders with standardized file names:

```
templates/
├── my_agent/
│   ├── system_prompt    # System prompt template (no extension)
│   ├── user_input      # User input template (no extension)
│   └── case           # Test case JSON (no extension)
├── another_agent/
│   ├── system_prompt
│   ├── user_input
│   └── case
└── ...
```

### Benefits of New Structure
- **Simplified CLI**: Create agents with just `python -m src.agent_template_parser.cli create-agent <agent_name>`
- **Better Organization**: All files for an agent are grouped together
- **Clearer Naming**: Standard file names eliminate confusion
- **Easier Management**: Add, remove, or modify agent templates as complete units

## Legacy Structure (Still Supported)

The original file-based structure continues to work for backward compatibility:

```
templates/
├── system_prompts/
│   ├── my_agent_system.txt
│   └── another_agent_system.txt
├── user_inputs/
│   ├── my_agent_user.txt
│   └── another_agent_user.txt
└── test_cases/
    ├── my_agent_test.json
    └── another_agent_test.json
```

## Usage

### Using New Folder Structure (Recommended)

1. Create a folder named after your agent: `templates/{agent_name}/`
2. Add three files with standard names:
   - `system_prompt` - Contains the system prompt template
   - `user_input` - Contains the user input template
   - `case` - Contains the test case JSON
3. Run: `python -m src.agent_template_parser.cli create-agent {agent_name}`

### Using Legacy Structure

Place your template files in the appropriate subdirectories:
- System prompt templates: `system_prompts/{agent_name}_system.txt`
- User input templates: `user_inputs/{agent_name}_user.txt`
- Test case files: `test_cases/{agent_name}_test.json`

Then use the full command with file paths.

## Migration Guide

### Converting from Legacy to New Structure

1. **Create agent folder**: `mkdir templates/{agent_name}`
2. **Move and rename files**:
   ```bash
   # Move system prompt
   mv system_prompts/{agent_name}_system.txt templates/{agent_name}/system_prompt
   
   # Move user input
   mv user_inputs/{agent_name}_user.txt templates/{agent_name}/user_input
   
   # Move test case
   mv test_cases/{agent_name}_test.json templates/{agent_name}/case
   ```
3. **Test the migration**: `python -m src.agent_template_parser.cli create-agent {agent_name}`

### Automated Conversion

Use the built-in conversion utilities for easier migration:

```bash
# List all templates and their structures
python -m src.agent_template_parser.cli convert-templates --list

# Convert a specific agent
python -m src.agent_template_parser.cli convert-templates my_agent

# Preview what would be converted (dry run)
python -m src.agent_template_parser.cli convert-templates my_agent --dry-run

# Convert all legacy templates at once
python -m src.agent_template_parser.cli convert-templates --dry-run
python -m src.agent_template_parser.cli convert-templates
```

### Gradual Migration

You can migrate agents one at a time. The system will:
1. First look for the new folder structure
2. Fall back to legacy structure if folder not found
3. Prefer new structure if both exist

### Validation Tools

Verify your templates are correctly structured:

```bash
# Validate a specific agent's templates
python -m src.agent_template_parser.cli validate-templates --agent-name my_agent

# Use the standalone validation script
python scripts/convert_templates.py validate my_agent
python scripts/convert_templates.py list
```

## Best Practices

### File Content Guidelines
- **system_prompt**: Write clear, specific instructions for the AI agent
- **user_input**: Provide template with placeholders like `{variable_name}`
- **case**: Include realistic test scenarios with expected inputs/outputs

### Organization Tips
- Use descriptive agent names that reflect their purpose
- Group related agents with consistent naming (e.g., `customer_service_v1`, `customer_service_v2`)
- Keep templates focused on a single, well-defined task
- Document any special requirements or dependencies in comments

### Template Validation
- Ensure all three files are present and non-empty
- Test your templates before deploying
- Use consistent formatting and style across templates

## Troubleshooting

### Common Issues
- **Missing files**: Ensure all three files (`system_prompt`, `user_input`, `case`) exist
- **Empty files**: All template files must contain content
- **Wrong location**: Agent folders must be directly under `templates/`
- **File extensions**: New structure uses no file extensions

### Getting Help
If you encounter issues, the CLI will provide helpful error messages showing:
- Expected folder structure
- Missing files
- Suggested fixes