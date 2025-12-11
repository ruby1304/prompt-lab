# Implementation Plan

- [x] 1. Enhance TemplateManager with folder structure support
  - Add methods to detect and load agent folder templates
  - Implement validation for folder-based template structure
  - Add backward compatibility logic to prefer folder structure over legacy
  - _Requirements: 1.1, 1.2, 3.1, 4.1_

- [x] 1.1 Add folder structure detection methods
  - Implement `get_template_structure_type()` method to detect folder vs legacy structure
  - Create `validate_agent_folder_structure()` method to check for required files
  - Write unit tests for structure detection logic
  - _Requirements: 1.1, 3.1_

- [x] 1.2 Implement folder-based template loading
  - Create `load_agent_folder_templates()` method to load from agent folders
  - Modify existing `load_template_files()` to try folder structure first, then legacy
  - Add error handling for missing files with helpful messages
  - _Requirements: 1.2, 4.1, 5.3_

- [x] 1.3 Add template structure validation
  - Enhance `validate_template_files()` to work with both structures
  - Create specific validation for folder structure completeness
  - Write unit tests for validation methods
  - _Requirements: 3.2, 1.3_

- [x] 2. Update CLI interface with simplified command
  - Add new simplified `create-agent` command that only requires agent name
  - Maintain backward compatibility with existing parameter-based command
  - Enhance error messages to guide users on expected folder structure
  - _Requirements: 2.1, 2.2, 4.2, 5.3_

- [x] 2.1 Implement simplified create-agent command
  - Add `create_agent_simple()` method that takes only agent_name parameter
  - Integrate with enhanced TemplateManager to auto-detect template location
  - Write integration tests for the simplified workflow
  - _Requirements: 2.1, 2.2_

- [x] 2.2 Enhance CLI argument parsing
  - Modify argument parser to support both old and new command formats
  - Add logic to detect which format is being used and route appropriately
  - Update help text to show both options with preference for new syntax
  - _Requirements: 2.1, 4.2, 5.2_

- [x] 2.3 Improve error handling and user guidance
  - Create helpful error messages that show expected folder structure
  - Add examples in error messages for both folder and legacy structures
  - Implement suggestion system for common mistakes
  - _Requirements: 2.2, 5.3_

- [x] 3. Create data models for template structure management
  - Define TemplateStructure enum and TemplateLocation dataclass
  - Add new error classes for folder structure validation
  - Create constants for standard file names and help messages
  - _Requirements: 1.1, 2.2, 5.3_

- [x] 3.1 Define template structure data models
  - Create TemplateStructure enum with FOLDER, LEGACY, MIXED values
  - Implement TemplateLocation dataclass to track template file locations
  - Add type hints and documentation for new data structures
  - _Requirements: 1.1, 3.1_

- [x] 3.2 Add specialized error classes
  - Create InvalidFolderStructureError for incomplete agent folders
  - Implement MissingAgentFolderError for non-existent agent folders
  - Add AmbiguousTemplateStructureError for conflicting structures
  - _Requirements: 2.2, 5.3_

- [x] 4. Update documentation and examples
  - Modify templates README to show new folder structure
  - Update CLI help text and examples
  - Add migration guidance for existing users
  - _Requirements: 5.1, 5.2_

- [x] 4.1 Update templates README documentation
  - Add examples of new folder structure alongside legacy structure
  - Provide clear migration path from legacy to folder structure
  - Include best practices for organizing agent templates
  - _Requirements: 5.1_

- [x] 4.2 Enhance CLI help and examples
  - Update command help text to show simplified syntax first
  - Add examples using the new agent folder structure
  - Include troubleshooting section for common folder structure issues
  - _Requirements: 5.2_

- [x] 5. Write comprehensive tests for new functionality
  - Create test fixtures for both folder and legacy structures
  - Write unit tests for all new TemplateManager methods
  - Add integration tests for the complete simplified workflow
  - _Requirements: 1.1, 1.2, 2.1, 3.1_

- [x] 5.1 Create test fixtures and data
  - Set up test templates in both folder and legacy structures
  - Create mixed structure scenarios for testing compatibility
  - Add invalid structure examples for error handling tests
  - _Requirements: 1.1, 4.1_

- [x] 5.2 Write unit tests for TemplateManager enhancements
  - Test folder structure detection and validation methods
  - Test template loading from both structures with fallback logic
  - Test error handling for various invalid structure scenarios
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 5.3 Add integration tests for CLI workflow
  - Test end-to-end agent creation using simplified command
  - Test backward compatibility with existing parameter-based commands
  - Test error scenarios and user guidance messages
  - _Requirements: 2.1, 2.2, 4.2_

- [x] 6. Create example templates in new folder structure
  - Convert existing template examples to new folder structure
  - Create demonstration agent using simplified workflow
  - Add validation script to verify template structure correctness
  - _Requirements: 5.1, 3.2_

- [x] 6.1 Convert existing templates to folder structure
  - Create example agent folders with system_prompt, user_input, and case files
  - Ensure examples work with both old and new CLI interfaces
  - Document the conversion process for users
  - _Requirements: 5.1, 4.1_

- [x] 6.2 Add template validation utility
  - Create script to validate template folder structures
  - Add option to convert legacy templates to folder structure
  - Include in CLI as a validation subcommand
  - _Requirements: 3.2, 5.1_