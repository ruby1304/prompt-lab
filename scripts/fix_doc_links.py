#!/usr/bin/env python3
"""
Fix Documentation Links Script

This script fixes broken documentation links identified during migration verification.
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple


class DocLinkFixer:
    """Fixes broken documentation links"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.fixes_applied = []
        
    def fix_all_links(self) -> List[str]:
        """Fix all known broken links"""
        
        # Define link fixes: (file_path, old_link, new_link)
        link_fixes = [
            # OUTPUT_PARSER_USAGE.md moved to docs/guides/
            ("docs/ARCHITECTURE.md", "../OUTPUT_PARSER_USAGE.md", "guides/output-parser-usage.md"),
            ("docs/TROUBLESHOOTING.md", "../OUTPUT_PARSER_USAGE.md", "guides/output-parser-usage.md"),
            ("docs/ARCHITECTURE_ANALYSIS.md", "../OUTPUT_PARSER_USAGE.md", "guides/output-parser-usage.md"),
            ("docs/reference/output-parser-guide.md", "../../OUTPUT_PARSER_USAGE.md", "../guides/output-parser-usage.md"),
            ("docs/reference/pipeline-guide.md", "../OUTPUT_PARSER_USAGE.md", "output-parser-guide.md"),
            
            # Spec documents in scripts/README_MIGRATION.md
            ("scripts/README_MIGRATION.md", ".kiro/specs/project-production-readiness/design.md", "../.kiro/specs/project-production-readiness/design.md"),
            ("scripts/README_MIGRATION.md", ".kiro/specs/project-production-readiness/requirements.md", "../.kiro/specs/project-production-readiness/requirements.md"),
            ("scripts/README_MIGRATION.md", ".kiro/specs/project-production-readiness/tasks.md", "../.kiro/specs/project-production-readiness/tasks.md"),
            
            # Archive documents - these are in archive, so links to other archive docs should be relative
            ("docs/archive/reorganization-complete.md", "QUICK_START_REORGANIZATION.md", "quick-start-reorganization.md"),
            ("docs/archive/reorganization-complete.md", "AGENT_REORGANIZATION_PLAN.md", "agent-reorganization-plan.md"),
            ("docs/archive/reorganization-complete.md", "AGENT_CLASSIFICATION_REPORT.md", "agent-classification-report.md"),
            ("docs/archive/reorganization-complete.md", "AGENT_MANAGEMENT_GUIDE.md", "../guides/agent-management.md"),
            ("docs/archive/reorganization-complete.md", "examples/README.md", "../../examples/README.md"),
            
            ("docs/archive/quick-start-reorganization.md", "AGENT_REORGANIZATION_PLAN.md", "agent-reorganization-plan.md"),
            ("docs/archive/quick-start-reorganization.md", "AGENT_CLASSIFICATION_REPORT.md", "agent-classification-report.md"),
            ("docs/archive/quick-start-reorganization.md", "AGENT_MANAGEMENT_GUIDE.md", "../guides/agent-management.md"),
            
            # project-analysis-cn.md links to docs
            ("docs/archive/project-analysis-cn.md", "docs/ARCHITECTURE.md", "../ARCHITECTURE.md"),
            ("docs/archive/project-analysis-cn.md", "docs/ARCHITECTURE_ANALYSIS.md", "../ARCHITECTURE_ANALYSIS.md"),
            ("docs/archive/project-analysis-cn.md", "docs/USAGE_GUIDE.md", "../USAGE_GUIDE.md"),
            ("docs/archive/project-analysis-cn.md", "docs/TROUBLESHOOTING.md", "../TROUBLESHOOTING.md"),
            
            # agent-management.md links
            ("docs/guides/agent-management.md", "AGENT_CLASSIFICATION_REPORT.md", "../archive/agent-classification-report.md"),
            ("docs/guides/agent-management.md", "docs/ARCHITECTURE.md", "../ARCHITECTURE.md"),
            ("docs/guides/agent-management.md", "docs/USAGE_GUIDE.md", "../USAGE_GUIDE.md"),
            
            # Evaluation rules references
            ("docs/reference/regression-testing.md", "../EVALUATION_RULES.md", "evaluation-rules.md"),
            ("docs/reference/rules-quick-reference.md", "EVALUATION_RULES.md", "evaluation-rules.md"),
            ("docs/reference/rules-quick-reference.md", "MANUAL_EVAL_GUIDE.md", "manual-eval-guide.md"),
            ("docs/reference/manual-eval-guide.md", "EVALUATION_RULES.md", "evaluation-rules.md"),
        ]
        
        for file_path, old_link, new_link in link_fixes:
            self.fix_link_in_file(file_path, old_link, new_link)
        
        return self.fixes_applied
    
    def fix_link_in_file(self, file_path: str, old_link: str, new_link: str):
        """Fix a specific link in a file"""
        full_path = self.project_root / file_path
        
        if not full_path.exists():
            print(f"⚠ File not found: {file_path}")
            return
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Escape special regex characters in the old link
            escaped_old = re.escape(old_link)
            
            # Replace the link (match markdown link format)
            pattern = f'\\[([^\\]]+)\\]\\({escaped_old}\\)'
            replacement = f'[\\1]({new_link})'
            
            new_content, count = re.subn(pattern, replacement, content)
            
            if count > 0:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                fix_msg = f"✓ Fixed {count} link(s) in {file_path}: {old_link} -> {new_link}"
                print(fix_msg)
                self.fixes_applied.append(fix_msg)
            else:
                print(f"  No matches found in {file_path} for: {old_link}")
                
        except Exception as e:
            print(f"✗ Error fixing {file_path}: {e}")
    
    def run(self):
        """Run the link fixer"""
        print("="*80)
        print("FIXING DOCUMENTATION LINKS")
        print("="*80)
        print()
        
        fixes = self.fix_all_links()
        
        print()
        print("="*80)
        print(f"COMPLETE: Applied {len(fixes)} fixes")
        print("="*80)
        
        return len(fixes)


def main():
    fixer = DocLinkFixer()
    fixer.run()


if __name__ == "__main__":
    main()
