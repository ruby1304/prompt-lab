# Requirements Document

## Introduction

The Pipeline Regression System is a comprehensive upgrade to the existing Prompt Lab architecture that introduces multi-step pipeline evaluation, baseline regression testing, and improved data organization. This system will enable evaluation of complex business workflows that involve multiple Agent/Flow combinations, while maintaining backward compatibility with existing single-agent evaluation capabilities.

The system addresses the current limitations where evaluation is limited to single Agent/Flow combinations, data is mixed together in a single directory, and there's no systematic way to compare pipeline versions or perform regression testing against established baselines.

## Requirements

### Requirement 1: Pipeline Flow Architecture

**User Story:** As a prompt engineer, I want to define multi-step pipelines that chain multiple Agent/Flow combinations together, so that I can evaluate complete business workflows rather than just individual components.

#### Acceptance Criteria

1. WHEN I create a pipeline configuration THEN the system SHALL support defining multiple sequential steps with input/output mapping
2. WHEN I define a pipeline step THEN the system SHALL allow me to specify agent_id, flow_name, input_mapping, and output_key
3. WHEN I execute a pipeline THEN the system SHALL pass outputs from previous steps as inputs to subsequent steps
4. WHEN I configure a pipeline THEN the system SHALL support optional model overrides for individual steps
5. IF a pipeline step fails THEN the system SHALL provide clear error messages indicating which step failed and why

### Requirement 2: Pipeline Configuration Management

**User Story:** As a system administrator, I want to manage pipeline configurations through YAML files, so that I can version control and maintain complex workflow definitions.

#### Acceptance Criteria

1. WHEN I create a pipeline configuration THEN the system SHALL store it in a `pipelines/` directory as a YAML file
2. WHEN I define a pipeline THEN the system SHALL require id, name, description, steps, and outputs fields
3. WHEN I specify pipeline steps THEN the system SHALL validate that referenced agents and flows exist
4. WHEN I define input_mapping THEN the system SHALL support mapping from testset fields and previous step outputs
5. WHEN I configure pipeline outputs THEN the system SHALL specify which step outputs to include in final results

### Requirement 3: Baseline and Variant Management

**User Story:** As a prompt engineer, I want to define baseline configurations and variants for both agents and pipelines, so that I can systematically compare new versions against established standards.

#### Acceptance Criteria

1. WHEN I configure an agent THEN the system SHALL allow me to specify a baseline_flow
2. WHEN I configure a pipeline THEN the system SHALL allow me to define baseline step configurations
3. WHEN I create pipeline variants THEN the system SHALL support overriding specific steps with different flows or models
4. WHEN I run regression tests THEN the system SHALL compare variant performance against baseline performance
5. IF regression performance degrades significantly THEN the system SHALL flag concerning cases for review

### Requirement 4: Enhanced Data Organization

**User Story:** As a data analyst, I want organized data storage by agent and pipeline, so that I can easily locate and manage testsets, runs, and evaluation results.

#### Acceptance Criteria

1. WHEN the system stores data THEN it SHALL organize files under `data/agents/{agent_id}/` and `data/pipelines/{pipeline_id}/` directories
2. WHEN I create testsets THEN the system SHALL store them in `{entity}/testsets/` subdirectories
3. WHEN I execute runs THEN the system SHALL store results in `{entity}/runs/` with timestamped filenames
4. WHEN I perform evaluations THEN the system SHALL store results in `{entity}/evals/` subdirectories
5. WHEN I migrate existing data THEN the system SHALL provide tools to reorganize legacy data into the new structure

### Requirement 5: Testset Tagging and Filtering

**User Story:** As a test engineer, I want to tag testset samples and filter by tags during evaluation, so that I can run targeted tests on specific scenarios or regression cases.

#### Acceptance Criteria

1. WHEN I create testset samples THEN the system SHALL support adding tags as a list of strings
2. WHEN I run evaluations THEN the system SHALL allow filtering by include-tags and exclude-tags
3. WHEN I specify tag filters THEN the system SHALL only process samples matching the criteria
4. WHEN I view results THEN the system SHALL group statistics by tags for analysis
5. WHEN I create regression testsets THEN the system SHALL support dedicated tags like "regression", "happy_path", "edge_case"

### Requirement 6: Pipeline Evaluation and Comparison

**User Story:** As a prompt engineer, I want to evaluate and compare different pipeline configurations, so that I can determine which combination of agents, flows, and models produces the best results.

#### Acceptance Criteria

1. WHEN I evaluate a pipeline THEN the system SHALL execute all steps and collect intermediate and final outputs
2. WHEN I compare pipeline variants THEN the system SHALL run multiple configurations on the same testset
3. WHEN I perform pipeline evaluation THEN the system SHALL apply rules and LLM judge evaluation to pipeline outputs
4. WHEN I view comparison results THEN the system SHALL show score differences, must_have pass rates, and rule violations by variant
5. WHEN I analyze pipeline performance THEN the system SHALL provide statistics at both individual sample and aggregate levels

### Requirement 7: Regression Testing Workflow

**User Story:** As a quality assurance engineer, I want automated regression testing capabilities, so that I can quickly identify when new versions perform worse than established baselines.

#### Acceptance Criteria

1. WHEN I run regression tests THEN the system SHALL compare new flow/pipeline performance against baseline
2. WHEN regression results show degradation THEN the system SHALL highlight cases with significant score drops
3. WHEN I review regression results THEN the system SHALL provide old vs new score comparisons and must_have failure analysis
4. WHEN I configure regression tests THEN the system SHALL support dedicated regression testsets
5. IF critical regression cases fail THEN the system SHALL provide clear failure summaries and recommendations

### Requirement 8: Enhanced CLI Interface

**User Story:** As a developer, I want comprehensive CLI commands for pipeline operations, so that I can integrate pipeline evaluation into automated workflows.

#### Acceptance Criteria

1. WHEN I use the CLI THEN the system SHALL support `--pipeline` parameter for pipeline-specific operations
2. WHEN I run pipeline evaluation THEN the system SHALL support `python -m src eval --pipeline {pipeline_id} --variants {variant_list}`
3. WHEN I perform regression testing THEN the system SHALL support `python -m src eval_regression --pipeline {pipeline_id} --variant {variant_name}`
4. WHEN I filter by tags THEN the system SHALL support `--include-tags` and `--exclude-tags` parameters
5. WHEN I execute commands THEN the system SHALL provide clear progress indicators and error messages

### Requirement 9: Backward Compatibility

**User Story:** As an existing user, I want the new pipeline system to work alongside existing agent/flow evaluation, so that I can migrate gradually without breaking current workflows.

#### Acceptance Criteria

1. WHEN I use existing agent evaluation commands THEN they SHALL continue to work without modification
2. WHEN I access existing data files THEN they SHALL remain accessible in their current locations
3. WHEN I migrate to the new system THEN the system SHALL provide migration tools for existing configurations
4. WHEN I use legacy commands THEN the system SHALL provide deprecation warnings with migration guidance
5. WHEN I run mixed workflows THEN the system SHALL support both old and new evaluation approaches simultaneously

### Requirement 10: Performance and Scalability

**User Story:** As a system operator, I want the pipeline system to handle large testsets and complex pipelines efficiently, so that evaluation doesn't become a bottleneck in the development process.

#### Acceptance Criteria

1. WHEN I execute large pipelines THEN the system SHALL provide progress indicators and estimated completion times
2. WHEN pipeline steps fail THEN the system SHALL support resuming from the last successful step
3. WHEN I run parallel evaluations THEN the system SHALL manage resource usage to prevent API rate limiting
4. WHEN I process large testsets THEN the system SHALL support batching and memory-efficient processing
5. WHEN I store results THEN the system SHALL use efficient file formats and avoid data duplication

### Requirement 11: Chinese Language Support

**User Story:** As a Chinese-speaking developer, I want the system to provide Chinese-friendly output and documentation, so that I can work efficiently in my preferred language.

#### Acceptance Criteria

1. WHEN the system outputs console messages THEN it SHALL display progress, errors, and status information in Chinese
2. WHEN I view CLI help text THEN the system SHALL provide Chinese descriptions for commands and parameters
3. WHEN the system generates code comments THEN they SHALL be written in Chinese for better readability
4. WHEN I receive error messages THEN they SHALL be clear and descriptive in Chinese
5. WHEN the system logs operations THEN log messages SHALL use Chinese for better local analysis

### Requirement 12: Unified Documentation Structure

**User Story:** As a user, I want all essential information in a single comprehensive README with structured reference documents, so that I can quickly understand the system without navigating multiple files.

#### Acceptance Criteria

1. WHEN I read the main README THEN it SHALL contain all essential information about pipeline features, usage, and examples
2. WHEN the README references detailed topics THEN it SHALL provide brief explanations and link to reference documents
3. WHEN I need detailed information THEN reference documents SHALL be organized in a `docs/` directory with clear structure
4. WHEN reference documents are created THEN they SHALL be mentioned and briefly described in the main README
5. WHEN I update features THEN both README and relevant reference documents SHALL be updated consistently