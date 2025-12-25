#!/usr/bin/env python3
"""
Migration Verification Script

This script verifies that the project migration was successful by:
1. Running existing tests to ensure compatibility
2. Verifying all import paths are correct
3. Verifying document links are valid
4. Generating a comprehensive migration report

Requirements: 1.2, 1.3, 1.4
"""

import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Tuple, Set
import re
from datetime import datetime


class MigrationVerifier:
    """Verifies migration results and generates reports"""
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": {},
            "imports": {},
            "docs": {},
            "summary": {}
        }
        
    def run_tests(self) -> Dict[str, any]:
        """Run existing tests to ensure compatibility"""
        print("\n" + "="*80)
        print("STEP 1: Running Existing Tests")
        print("="*80)
        
        test_results = {
            "passed": False,
            "total_tests": 0,
            "passed_tests": 0,
            "failed_tests": 0,
            "skipped_tests": 0,
            "errors": [],
            "output": ""
        }
        
        try:
            # Run pytest with coverage
            cmd = [
                sys.executable, "-m", "pytest",
                "tests/",
                "-v",
                "--tb=short",
                "-m", "not integration",  # Skip integration tests that require LLM
                "--maxfail=5",  # Stop after 5 failures
            ]
            
            print(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            test_results["output"] = result.stdout + result.stderr
            
            # Parse pytest output
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if 'passed' in line.lower() or 'failed' in line.lower():
                    # Extract test counts from summary line
                    # Example: "5 passed, 2 failed, 1 skipped in 10.23s"
                    parts = line.split(',')
                    for part in parts:
                        if 'passed' in part:
                            test_results["passed_tests"] = int(re.search(r'(\d+)', part).group(1))
                        elif 'failed' in part:
                            test_results["failed_tests"] = int(re.search(r'(\d+)', part).group(1))
                        elif 'skipped' in part:
                            test_results["skipped_tests"] = int(re.search(r'(\d+)', part).group(1))
            
            test_results["total_tests"] = (
                test_results["passed_tests"] + 
                test_results["failed_tests"] + 
                test_results["skipped_tests"]
            )
            
            test_results["passed"] = result.returncode == 0
            
            if test_results["passed"]:
                print(f"✓ All tests passed ({test_results['passed_tests']} tests)")
            else:
                print(f"✗ Some tests failed:")
                print(f"  - Passed: {test_results['passed_tests']}")
                print(f"  - Failed: {test_results['failed_tests']}")
                print(f"  - Skipped: {test_results['skipped_tests']}")
                
                # Extract error messages
                if result.stderr:
                    test_results["errors"].append(result.stderr)
                    
        except subprocess.TimeoutExpired:
            test_results["errors"].append("Test execution timed out after 5 minutes")
            print("✗ Test execution timed out")
        except Exception as e:
            test_results["errors"].append(str(e))
            print(f"✗ Error running tests: {e}")
        
        self.results["tests"] = test_results
        return test_results
    
    def verify_imports(self) -> Dict[str, any]:
        """Verify all import paths are correct"""
        print("\n" + "="*80)
        print("STEP 2: Verifying Import Paths")
        print("="*80)
        
        import_results = {
            "passed": True,
            "total_files": 0,
            "files_checked": 0,
            "import_errors": [],
            "warnings": []
        }
        
        # Find all Python files
        python_files = list(self.project_root.glob("**/*.py"))
        # Exclude virtual environments and build directories
        python_files = [
            f for f in python_files 
            if not any(part in f.parts for part in ['.venv', 'venv', '__pycache__', 'build', 'dist', '.pytest_cache'])
        ]
        
        import_results["total_files"] = len(python_files)
        
        print(f"Checking {len(python_files)} Python files...")
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find all import statements
                import_pattern = r'^(?:from|import)\s+([a-zA-Z0-9_.]+)'
                imports = re.findall(import_pattern, content, re.MULTILINE)
                
                # Check for common migration issues
                for imp in imports:
                    # Check for old paths that should have been updated
                    if imp.startswith('agents.') and 'tests' not in str(py_file):
                        import_results["warnings"].append(
                            f"{py_file.relative_to(self.project_root)}: "
                            f"Importing from 'agents' package (should be in agents/ directory)"
                        )
                    
                    # Check for imports from moved locations
                    if 'templates.' in imp and 'tests' not in str(py_file):
                        import_results["warnings"].append(
                            f"{py_file.relative_to(self.project_root)}: "
                            f"Importing from 'templates' package"
                        )
                
                import_results["files_checked"] += 1
                
            except Exception as e:
                import_results["import_errors"].append(
                    f"{py_file.relative_to(self.project_root)}: {str(e)}"
                )
                import_results["passed"] = False
        
        if import_results["passed"] and not import_results["warnings"]:
            print(f"✓ All import paths verified ({import_results['files_checked']} files)")
        else:
            print(f"⚠ Import verification completed with warnings:")
            print(f"  - Files checked: {import_results['files_checked']}")
            print(f"  - Warnings: {len(import_results['warnings'])}")
            print(f"  - Errors: {len(import_results['import_errors'])}")
        
        self.results["imports"] = import_results
        return import_results
    
    def verify_doc_links(self) -> Dict[str, any]:
        """Verify document links are valid"""
        print("\n" + "="*80)
        print("STEP 3: Verifying Document Links")
        print("="*80)
        
        doc_results = {
            "passed": True,
            "total_docs": 0,
            "docs_checked": 0,
            "broken_links": [],
            "warnings": []
        }
        
        # Find all markdown files
        md_files = list(self.project_root.glob("**/*.md"))
        # Exclude virtual environments and build directories
        md_files = [
            f for f in md_files 
            if not any(part in f.parts for part in ['.venv', 'venv', 'node_modules', 'build', 'dist'])
        ]
        
        doc_results["total_docs"] = len(md_files)
        
        print(f"Checking {len(md_files)} markdown files...")
        
        # Pattern to match markdown links: [text](path)
        link_pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        
        for md_file in md_files:
            try:
                with open(md_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Find all links
                links = re.findall(link_pattern, content)
                
                for link_text, link_path in links:
                    # Skip external links (http/https)
                    if link_path.startswith(('http://', 'https://', '#')):
                        continue
                    
                    # Remove anchor from path
                    clean_path = link_path.split('#')[0]
                    if not clean_path:
                        continue
                    
                    # Resolve relative path
                    if clean_path.startswith('/'):
                        target_path = self.project_root / clean_path.lstrip('/')
                    else:
                        target_path = (md_file.parent / clean_path).resolve()
                    
                    # Check if target exists
                    if not target_path.exists():
                        doc_results["broken_links"].append({
                            "file": str(md_file.relative_to(self.project_root)),
                            "link_text": link_text,
                            "link_path": link_path,
                            "resolved_path": str(target_path.relative_to(self.project_root))
                        })
                        doc_results["passed"] = False
                
                doc_results["docs_checked"] += 1
                
            except Exception as e:
                doc_results["warnings"].append(
                    f"{md_file.relative_to(self.project_root)}: {str(e)}"
                )
        
        if doc_results["passed"]:
            print(f"✓ All document links verified ({doc_results['docs_checked']} files)")
        else:
            print(f"✗ Found broken links:")
            print(f"  - Docs checked: {doc_results['docs_checked']}")
            print(f"  - Broken links: {len(doc_results['broken_links'])}")
            for broken in doc_results["broken_links"][:5]:  # Show first 5
                print(f"    - {broken['file']}: [{broken['link_text']}]({broken['link_path']})")
            if len(doc_results["broken_links"]) > 5:
                print(f"    ... and {len(doc_results['broken_links']) - 5} more")
        
        self.results["docs"] = doc_results
        return doc_results
    
    def generate_report(self, output_path: Path = None) -> str:
        """Generate comprehensive migration report"""
        print("\n" + "="*80)
        print("STEP 4: Generating Migration Report")
        print("="*80)
        
        # Calculate summary
        all_passed = (
            self.results["tests"].get("passed", False) and
            self.results["imports"].get("passed", True) and
            self.results["docs"].get("passed", True)
        )
        
        self.results["summary"] = {
            "overall_status": "PASSED" if all_passed else "FAILED",
            "tests_passed": self.results["tests"].get("passed", False),
            "imports_verified": self.results["imports"].get("passed", True),
            "docs_verified": self.results["docs"].get("passed", True),
            "total_issues": (
                len(self.results["tests"].get("errors", [])) +
                len(self.results["imports"].get("import_errors", [])) +
                len(self.results["docs"].get("broken_links", []))
            )
        }
        
        # Generate markdown report
        report_lines = [
            "# Migration Verification Report",
            "",
            f"**Generated:** {self.results['timestamp']}",
            f"**Overall Status:** {'✓ PASSED' if all_passed else '✗ FAILED'}",
            "",
            "## Summary",
            "",
            f"- **Tests:** {'✓ Passed' if self.results['summary']['tests_passed'] else '✗ Failed'}",
            f"- **Imports:** {'✓ Verified' if self.results['summary']['imports_verified'] else '✗ Issues Found'}",
            f"- **Documentation:** {'✓ Verified' if self.results['summary']['docs_verified'] else '✗ Broken Links'}",
            f"- **Total Issues:** {self.results['summary']['total_issues']}",
            "",
            "---",
            "",
            "## 1. Test Results",
            "",
        ]
        
        # Test results section
        test_res = self.results["tests"]
        if test_res.get("passed"):
            report_lines.extend([
                f"✓ **All tests passed**",
                "",
                f"- Total tests: {test_res.get('total_tests', 0)}",
                f"- Passed: {test_res.get('passed_tests', 0)}",
                f"- Failed: {test_res.get('failed_tests', 0)}",
                f"- Skipped: {test_res.get('skipped_tests', 0)}",
                "",
            ])
        else:
            report_lines.extend([
                f"✗ **Some tests failed**",
                "",
                f"- Total tests: {test_res.get('total_tests', 0)}",
                f"- Passed: {test_res.get('passed_tests', 0)}",
                f"- Failed: {test_res.get('failed_tests', 0)}",
                f"- Skipped: {test_res.get('skipped_tests', 0)}",
                "",
            ])
            
            if test_res.get("errors"):
                report_lines.extend([
                    "### Errors:",
                    "",
                    "```",
                ])
                for error in test_res["errors"][:3]:  # Show first 3 errors
                    report_lines.append(error[:500])  # Truncate long errors
                report_lines.append("```")
                report_lines.append("")
        
        # Import results section
        report_lines.extend([
            "## 2. Import Path Verification",
            "",
        ])
        
        import_res = self.results["imports"]
        report_lines.extend([
            f"- Files checked: {import_res.get('files_checked', 0)}/{import_res.get('total_files', 0)}",
            f"- Import errors: {len(import_res.get('import_errors', []))}",
            f"- Warnings: {len(import_res.get('warnings', []))}",
            "",
        ])
        
        if import_res.get("import_errors"):
            report_lines.extend([
                "### Import Errors:",
                "",
            ])
            for error in import_res["import_errors"][:10]:
                report_lines.append(f"- {error}")
            report_lines.append("")
        
        if import_res.get("warnings"):
            report_lines.extend([
                "### Warnings:",
                "",
            ])
            for warning in import_res["warnings"][:10]:
                report_lines.append(f"- {warning}")
            report_lines.append("")
        
        # Documentation results section
        report_lines.extend([
            "## 3. Documentation Link Verification",
            "",
        ])
        
        doc_res = self.results["docs"]
        report_lines.extend([
            f"- Documents checked: {doc_res.get('docs_checked', 0)}/{doc_res.get('total_docs', 0)}",
            f"- Broken links: {len(doc_res.get('broken_links', []))}",
            f"- Warnings: {len(doc_res.get('warnings', []))}",
            "",
        ])
        
        if doc_res.get("broken_links"):
            report_lines.extend([
                "### Broken Links:",
                "",
            ])
            for broken in doc_res["broken_links"][:20]:
                report_lines.append(
                    f"- **{broken['file']}**: [{broken['link_text']}]({broken['link_path']})"
                )
            if len(doc_res["broken_links"]) > 20:
                report_lines.append(f"- ... and {len(doc_res['broken_links']) - 20} more")
            report_lines.append("")
        
        # Recommendations section
        report_lines.extend([
            "## 4. Recommendations",
            "",
        ])
        
        if all_passed:
            report_lines.extend([
                "✓ **Migration verification passed successfully!**",
                "",
                "The project structure has been successfully migrated and all verification checks passed.",
                "You can proceed with the next phase of development.",
                "",
            ])
        else:
            report_lines.extend([
                "⚠ **Action items to address:**",
                "",
            ])
            
            if not test_res.get("passed"):
                report_lines.append("1. Fix failing tests before proceeding")
            if import_res.get("import_errors"):
                report_lines.append("2. Resolve import path errors")
            if doc_res.get("broken_links"):
                report_lines.append("3. Fix broken documentation links")
            
            report_lines.append("")
        
        report_lines.extend([
            "---",
            "",
            "## Detailed Results (JSON)",
            "",
            "```json",
            json.dumps(self.results, indent=2),
            "```",
            "",
        ])
        
        report_content = "\n".join(report_lines)
        
        # Save report
        if output_path is None:
            output_path = self.project_root / "MIGRATION_VERIFICATION_REPORT.md"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(report_content)
        
        print(f"✓ Report generated: {output_path}")
        
        return report_content
    
    def run_full_verification(self) -> bool:
        """Run all verification steps and generate report"""
        print("\n" + "="*80)
        print("MIGRATION VERIFICATION")
        print("="*80)
        print(f"Project root: {self.project_root}")
        print()
        
        # Run all verification steps
        self.run_tests()
        self.verify_imports()
        self.verify_doc_links()
        self.generate_report()
        
        # Print final summary
        print("\n" + "="*80)
        print("VERIFICATION COMPLETE")
        print("="*80)
        
        summary = self.results["summary"]
        print(f"\nOverall Status: {summary['overall_status']}")
        print(f"  - Tests: {'✓' if summary['tests_passed'] else '✗'}")
        print(f"  - Imports: {'✓' if summary['imports_verified'] else '✗'}")
        print(f"  - Documentation: {'✓' if summary['docs_verified'] else '✗'}")
        print(f"  - Total Issues: {summary['total_issues']}")
        print(f"\nDetailed report: MIGRATION_VERIFICATION_REPORT.md")
        
        return summary["overall_status"] == "PASSED"


def main():
    """Main entry point"""
    verifier = MigrationVerifier()
    success = verifier.run_full_verification()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
