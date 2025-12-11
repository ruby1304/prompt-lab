# Requirements Document

## Introduction

This feature improves the agent creation workflow by simplifying the input structure and making it more intuitive for developers. Instead of requiring complex file paths and naming conventions, users will create a simple folder structure with standardized file names and use a single command with just the agent name.

## Requirements

### Requirement 1

**User Story:** As a developer, I want to create a new agent by simply creating a folder with standard file names, so that I don't need to remember complex file paths and naming conventions.

#### Acceptance Criteria

1. WHEN I create a new agent folder THEN the system SHALL expect three standard files: `system_prompt`, `user_input`, and `case`
2. WHEN I place template files in the agent folder THEN the system SHALL automatically detect and use them without requiring full file paths
3. WHEN I use non-standard file names THEN the system SHALL provide clear error messages indicating the expected file names

### Requirement 2

**User Story:** As a developer, I want to use a simplified CLI command that only requires the agent name, so that I can quickly create agents without complex parameter specifications.

#### Acceptance Criteria

1. WHEN I run `python -m src.agent_template_parser.cli create-agent <agent_name>` THEN the system SHALL automatically look for template files in the `templates/<agent_name>/` directory
2. WHEN the agent folder or required files don't exist THEN the system SHALL provide helpful error messages with the expected folder structure
3. WHEN the command succeeds THEN the system SHALL create the agent configuration in the standard `agents/<agent_name>/` directory

### Requirement 3

**User Story:** As a developer, I want the template directory structure to be organized by agent name, so that I can easily manage multiple agent templates.

#### Acceptance Criteria

1. WHEN I create templates for a new agent THEN I SHALL create a folder `templates/<agent_name>/` containing the three required files
2. WHEN I list available templates THEN the system SHALL show agent names based on folder structure
3. WHEN I validate templates THEN the system SHALL check for the presence of all three required files in the agent folder

### Requirement 4

**User Story:** As a developer, I want backward compatibility with the existing template structure, so that my current templates continue to work while I migrate to the new structure.

#### Acceptance Criteria

1. WHEN I use the old CLI parameters THEN the system SHALL continue to work as before
2. WHEN I have templates in the old structure THEN the system SHALL still be able to process them
3. WHEN I migrate to the new structure THEN the system SHALL prefer the new structure over the old one if both exist

### Requirement 5

**User Story:** As a developer, I want clear documentation and examples of the new folder structure, so that I can quickly understand how to organize my templates.

#### Acceptance Criteria

1. WHEN I read the templates README THEN I SHALL see examples of both old and new folder structures
2. WHEN I run the help command THEN I SHALL see examples using the simplified syntax
3. WHEN I encounter errors THEN the system SHALL provide examples of the correct folder structure