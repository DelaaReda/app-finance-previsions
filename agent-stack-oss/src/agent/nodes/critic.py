from __future__ import annotations
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class CriticGate:
    """Final quality gate check."""
    passed: bool
    issues: List[Dict[str, Any]]
    critical_issues: int
    high_priority_issues: int
    summary: str
    timestamp: str


class Critic:
    """Final quality gate for code changes before commit."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = project_root
    
    def evaluate_changes(self, changes: Dict[str, Any]) -> CriticGate:
        """
        Evaluate proposed changes against quality criteria.
        
        Args:
            changes: Dictionary containing changes to evaluate
            
        Returns:
            CriticGate with evaluation results
        """
        issues = []
        critical_issues = 0
        high_priority_issues = 0
        
        # Check for critical security issues
        security_issues = self._check_security(changes)
        issues.extend(security_issues)
        critical_issues += sum(1 for issue in security_issues if issue["severity"] == "critical")
        high_priority_issues += sum(1 for issue in security_issues if issue["severity"] == "high")
        
        # Check for critical type issues
        type_issues = self._check_types(changes)
        issues.extend(type_issues)
        critical_issues += sum(1 for issue in type_issues if issue["severity"] == "critical")
        high_priority_issues += sum(1 for issue in type_issues if issue["severity"] == "high")
        
        # Check for critical architecture issues
        arch_issues = self._check_architecture(changes)
        issues.extend(arch_issues)
        critical_issues += sum(1 for issue in arch_issues if issue["severity"] == "critical")
        high_priority_issues += sum(1 for issue in arch_issues if issue["severity"] == "high")
        
        # Check for visual regression issues
        visual_issues = self._check_visual_regression(changes)
        issues.extend(visual_issues)
        critical_issues += sum(1 for issue in visual_issues if issue["severity"] == "critical")
        high_priority_issues += sum(1 for issue in visual_issues if issue["severity"] == "high")
        
        # Check for accessibility issues
        a11y_issues = self._check_accessibility(changes)
        issues.extend(a11y_issues)
        critical_issues += sum(1 for issue in a11y_issues if issue["severity"] == "critical")
        high_priority_issues += sum(1 for issue in a11y_issues if issue["severity"] == "high")
        
        # Determine if changes pass the gate
        passed = critical_issues == 0 and high_priority_issues == 0
        
        # Generate summary
        summary = self._generate_summary(passed, critical_issues, high_priority_issues, len(issues))
        
        return CriticGate(
            passed=passed,
            issues=issues,
            critical_issues=critical_issues,
            high_priority_issues=high_priority_issues,
            summary=summary,
            timestamp=self._get_current_timestamp()
        )
    
    def _check_security(self, changes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for security issues in changes."""
        issues = []
        
        # Check for hardcoded secrets
        for file_path, content in changes.get("files", {}).items():
            if isinstance(content, str):
                # Check for common secret patterns
                secret_patterns = [
                    "api_key", "secret", "password", "token", "access_key"
                ]
                
                for pattern in secret_patterns:
                    if pattern in content.lower():
                        issues.append({
                            "type": "security",
                            "severity": "critical",
                            "file": file_path,
                            "message": f"Possible hardcoded {pattern} found",
                            "line": self._find_line_number(content, pattern),
                            "suggestion": "Use environment variables or secure configuration"
                        })
                
                # Check for insecure imports or functions
                insecure_patterns = [
                    "eval(", "exec(", "os.system("
                ]
                
                for pattern in insecure_patterns:
                    if pattern in content:
                        issues.append({
                            "type": "security",
                            "severity": "high",
                            "file": file_path,
                            "message": f"Insecure function {pattern} found",
                            "line": self._find_line_number(content, pattern),
                            "suggestion": "Avoid using insecure functions"
                        })
        
        return issues
    
    def _check_types(self, changes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for type-related issues."""
        issues = []
        
        # Check for TypeScript/JavaScript files
        for file_path, content in changes.get("files", {}).items():
            if isinstance(content, str) and file_path.endswith(('.ts', '.tsx', '.js', '.jsx')):
                # Check for type annotations in TypeScript
                if file_path.endswith(('.ts', '.tsx')):
                    # Check if functions lack type annotations
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if 'function ' in line and '(' in line and ')' in line:
                            # Simple check for function without type annotations
                            if ':' not in line.split(')')[-1] and '=>' not in line:
                                issues.append({
                                    "type": "type",
                                    "severity": "medium",
                                    "file": file_path,
                                    "message": f"Function at line {i+1} lacks type annotations",
                                    "line": i + 1,
                                    "suggestion": "Add type annotations for parameters and return type"
                                })
        
        return issues
    
    def _check_architecture(self, changes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for architecture violations."""
        issues = []
        
        # Check for file structure violations
        for file_path in changes.get("files", {}).keys():
            if isinstance(file_path, str):
                # Check if files are being placed in wrong directories
                if "test_" in file_path and "tests/" not in file_path:
                    issues.append({
                        "type": "architecture",
                        "severity": "medium",
                        "file": file_path,
                        "message": "Test file should be in tests/ directory",
                        "line": 1,
                        "suggestion": "Move test files to appropriate test directory"
                    })
                
                # Check for component/service boundaries
                if "component" in file_path.lower() and ".service." in file_path.lower():
                    issues.append({
                        "type": "architecture",
                        "severity": "medium",
                        "file": file_path,
                        "message": "Component and service logic mixed",
                        "line": 1,
                        "suggestion": "Separate component and service logic"
                    })
        
        return issues
    
    def _check_visual_regression(self, changes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for potential visual regression issues."""
        issues = []
        
        # Check if UI files were modified without visual tests
        ui_files_modified = False
        test_files_added = False
        
        for file_path in changes.get("files", {}).keys():
            if isinstance(file_path, str):
                if file_path.endswith(('.tsx', '.jsx', '.vue', '.svelte')):
                    ui_files_modified = True
                elif "test" in file_path.lower() and file_path.endswith(('.test.tsx', '.spec.tsx')):
                    test_files_added = True
        
        if ui_files_modified and not test_files_added:
            issues.append({
                "type": "visual_regression",
                "severity": "medium",
                "file": "multiple",
                "message": "UI files modified without corresponding visual tests",
                "line": 0,
                "suggestion": "Add visual regression tests for UI changes"
            })
        
        return issues
    
    def _check_accessibility(self, changes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check for accessibility issues."""
        issues = []
        
        # Check if JSX/TSX files have accessibility anti-patterns
        for file_path, content in changes.get("files", {}).items():
            if isinstance(content, str) and file_path.endswith(('.tsx', '.jsx')):
                # Check for missing alt attributes on images
                if '<img' in content and 'alt=' not in content:
                    issues.append({
                        "type": "accessibility",
                        "severity": "high",
                        "file": file_path,
                        "message": "Image without alt attribute found",
                        "line": self._find_line_number(content, '<img'),
                        "suggestion": "Add descriptive alt attribute to image"
                    })
                
                # Check for buttons without aria-label
                if '<button' in content and 'aria-label=' not in content:
                    issues.append({
                        "type": "accessibility",
                        "severity": "medium",
                        "file": file_path,
                        "message": "Button without aria-label found",
                        "line": self._find_line_number(content, '<button'),
                        "suggestion": "Add aria-label to button for screen readers"
                    })
        
        return issues
    
    def _find_line_number(self, content: str, pattern: str) -> int:
        """Find line number of a pattern in content."""
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if pattern in line.lower():
                return i + 1
        return 1
    
    def _generate_summary(self, passed: bool, critical_issues: int, 
                          high_priority_issues: int, total_issues: int) -> str:
        """Generate summary of evaluation."""
        if passed:
            return f"✅ Changes approved ({total_issues} issues found, 0 critical/high)"
        else:
            return f"❌ Changes rejected ({critical_issues} critical, {high_priority_issues} high priority issues)"
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()


def create_critic(project_root: str = ".") -> Critic:
    """Factory function to create a Critic instance."""
    return Critic(project_root)


# Example usage:
if __name__ == "__main__":
    # Create critic
    critic = create_critic("/Users/venom/Documents/analyse-financiere")
    
    # Example changes to evaluate
    sample_changes = {
        "files": {
            "webapp/src/App.tsx": "import React from 'react';\n\nfunction App() {\n  return (\n    <div className=\"App\">\n      <img src=\"logo.png\" />\n      <button>Click me</button>\n    </div>\n  );\n}\n\nexport default App;",
            "src/api/main.py": "import os\napi_key = 'secret123'\ndef get_data():\n  eval(user_input)\n  return {'data': 'sensitive'}"
        }
    }
    
    # Evaluate changes
    result = critic.evaluate_changes(sample_changes)
    
    # Print results
    print(f"Evaluation Result: {result.summary}")
    print(f"Passed: {result.passed}")
    print(f"Critical Issues: {result.critical_issues}")
    print(f"High Priority Issues: {result.high_priority_issues}")
    print("\nIssues Found:")
    for issue in result.issues:
        print(f"  - [{issue['severity'].upper()}] {issue['type']}: {issue['message']}")
        print(f"    File: {issue['file']}, Line: {issue['line']}")
        print(f"    Suggestion: {issue['suggestion']}")
        print()