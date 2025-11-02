from __future__ import annotations
import subprocess
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class LinterResult:
    """Result from a linter."""
    linter: str
    success: bool
    issues: List[Dict[str, Any]]
    error_count: int
    warning_count: int
    file_count: int


@dataclass
class SecurityResult:
    """Result from security analysis."""
    tool: str
    success: bool
    vulnerabilities: List[Dict[str, Any]]
    critical_count: int
    high_count: int
    medium_count: int


@dataclass
class CodeReview:
    """Complete code review result."""
    file_path: str
    linter_results: List[LinterResult]
    security_results: List[SecurityResult]
    diff_aware_comments: List[Dict[str, Any]]
    summary: Dict[str, Any]
    timestamp: str


class CodeReviewer:
    """Performs static code analysis and security review."""
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.webapp_src = self.project_root / "webapp" / "src"
        self.python_src = self.project_root / "src"
    
    def review_file(self, file_path: str, diff_content: Optional[str] = None) -> CodeReview:
        """
        Review a single file for code quality and security issues.
        
        Args:
            file_path: Path to the file to review
            diff_content: Optional diff content for diff-aware review
            
        Returns:
            CodeReview with analysis results
        """
        full_path = self.project_root / file_path
        
        # Run appropriate linters based on file type
        linter_results = []
        security_results = []
        diff_comments = []
        
        if file_path.endswith(('.py',)):
            # Python files
            linter_results.extend(self._run_python_linters(full_path))
            security_results.extend(self._run_python_security_scan(full_path))
        elif file_path.endswith(('.ts', '.tsx')):
            # TypeScript files
            linter_results.extend(self._run_typescript_linters(full_path))
            security_results.extend(self._run_typescript_security_scan(full_path))
        
        # Generate diff-aware comments if diff content provided
        if diff_content:
            diff_comments = self._generate_diff_comments(file_path, diff_content)
        
        # Generate summary
        summary = self._generate_summary(linter_results, security_results)
        
        return CodeReview(
            file_path=file_path,
            linter_results=linter_results,
            security_results=security_results,
            diff_aware_comments=diff_comments,
            summary=summary,
            timestamp=self._get_current_timestamp()
        )
    
    def _run_python_linters(self, file_path: Path) -> List[LinterResult]:
        """Run Python linters on a file."""
        results = []
        
        # Run ruff
        try:
            result = subprocess.run(
                ["ruff", "check", "--output-format=json", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root
            )
            
            issues = []
            if result.stdout:
                try:
                    issues = json.loads(result.stdout)
                except json.JSONDecodeError:
                    issues = [{"message": result.stdout.strip()}]
            
            # Count errors and warnings
            error_count = sum(1 for issue in issues if issue.get("code", "").startswith(("E", "F")))
            warning_count = len(issues) - error_count
            
            results.append(LinterResult(
                linter="ruff",
                success=result.returncode == 0,
                issues=issues,
                error_count=error_count,
                warning_count=warning_count,
                file_count=1
            ))
        except Exception as e:
            results.append(LinterResult(
                linter="ruff",
                success=False,
                issues=[{"error": str(e)}],
                error_count=1,
                warning_count=0,
                file_count=1
            ))
        
        # Run mypy
        try:
            result = subprocess.run(
                ["mypy", "--show-error-codes", str(file_path)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=self.project_root
            )
            
            issues = []
            if result.stdout:
                # Parse mypy output
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if ":" in line:
                        parts = line.split(":")
                        if len(parts) >= 3:
                            issues.append({
                                "file": parts[0],
                                "line": parts[1],
                                "column": parts[2],
                                "message": ":".join(parts[3:]) if len(parts) > 3 else ""
                            })
            
            # Count errors and warnings
            error_count = len([issue for issue in issues if "error" in issue.get("message", "").lower()])
            warning_count = len(issues) - error_count
            
            results.append(LinterResult(
                linter="mypy",
                success=result.returncode == 0,
                issues=issues,
                error_count=error_count,
                warning_count=warning_count,
                file_count=1
            ))
        except Exception as e:
            results.append(LinterResult(
                linter="mypy",
                success=False,
                issues=[{"error": str(e)}],
                error_count=1,
                warning_count=0,
                file_count=1
            ))
        
        return results
    
    def _run_typescript_linters(self, file_path: Path) -> List[LinterResult]:
        """Run TypeScript linters on a file."""
        results = []
        
        # Run eslint
        try:
            result = subprocess.run(
                ["npx", "eslint", "--format", "json", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root / "webapp"
            )
            
            issues = []
            if result.stdout:
                try:
                    eslint_output = json.loads(result.stdout)
                    if isinstance(eslint_output, list) and len(eslint_output) > 0:
                        issues = eslint_output[0].get("messages", [])
                except json.JSONDecodeError:
                    issues = [{"message": result.stdout.strip()}]
            
            # Count errors and warnings
            error_count = sum(1 for issue in issues if issue.get("severity") == 2)
            warning_count = sum(1 for issue in issues if issue.get("severity") == 1)
            
            results.append(LinterResult(
                linter="eslint",
                success=result.returncode == 0 and error_count == 0,
                issues=issues,
                error_count=error_count,
                warning_count=warning_count,
                file_count=1
            ))
        except Exception as e:
            results.append(LinterResult(
                linter="eslint",
                success=False,
                issues=[{"error": str(e)}],
                error_count=1,
                warning_count=0,
                file_count=1
            ))
        
        return results
    
    def _run_python_security_scan(self, file_path: Path) -> List[SecurityResult]:
        """Run Python security scanning."""
        results = []
        
        # Run bandit
        try:
            result = subprocess.run(
                ["bandit", "-f", "json", "-q", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root
            )
            
            vulnerabilities = []
            critical_count = 0
            high_count = 0
            medium_count = 0
            
            if result.stdout:
                try:
                    bandit_output = json.loads(result.stdout)
                    results_list = bandit_output.get("results", [])
                    for item in results_list:
                        severity = item.get("issue_severity", "LOW")
                        if severity == "CRITICAL":
                            critical_count += 1
                        elif severity == "HIGH":
                            high_count += 1
                        elif severity == "MEDIUM":
                            medium_count += 1
                        
                        vulnerabilities.append({
                            "test_id": item.get("test_id"),
                            "test_name": item.get("test_name"),
                            "severity": severity,
                            "confidence": item.get("issue_confidence"),
                            "line": item.get("line_range"),
                            "code": item.get("code"),
                            "message": item.get("issue_text")
                        })
                except json.JSONDecodeError:
                    vulnerabilities = [{"message": result.stdout.strip()}]
            
            results.append(SecurityResult(
                tool="bandit",
                success=result.returncode == 0 and critical_count == 0 and high_count == 0,
                vulnerabilities=vulnerabilities,
                critical_count=critical_count,
                high_count=high_count,
                medium_count=medium_count
            ))
        except Exception as e:
            results.append(SecurityResult(
                tool="bandit",
                success=False,
                vulnerabilities=[{"error": str(e)}],
                critical_count=1,
                high_count=0,
                medium_count=0
            ))
        
        return results
    
    def _run_typescript_security_scan(self, file_path: Path) -> List[SecurityResult]:
        """Run TypeScript security scanning."""
        results = []
        
        # Run semgrep with common rules
        try:
            # Create temporary semgrep rules for TypeScript
            rules = """
rules:
  - id: insecure-random
    patterns:
      - pattern: Math.random()
    message: "Math.random() is not cryptographically secure"
    languages: [javascript, typescript]
    severity: WARNING
"""
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
                f.write(rules)
                rules_file = f.name
            
            result = subprocess.run(
                ["semgrep", "--config", rules_file, "--json", str(file_path)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.project_root
            )
            
            # Clean up temp file
            Path(rules_file).unlink(missing_ok=True)
            
            vulnerabilities = []
            critical_count = 0
            high_count = 0
            medium_count = 0
            
            if result.stdout:
                try:
                    semgrep_output = json.loads(result.stdout)
                    results_list = semgrep_output.get("results", [])
                    for item in results_list:
                        severity = item.get("extra", {}).get("metadata", {}).get("confidence", "LOW")
                        if severity == "CRITICAL":
                            critical_count += 1
                        elif severity == "HIGH":
                            high_count += 1
                        elif severity == "MEDIUM":
                            medium_count += 1
                        
                        vulnerabilities.append({
                            "check_id": item.get("check_id"),
                            "path": item.get("path"),
                            "line": item.get("start", {}).get("line"),
                            "message": item.get("extra", {}).get("message"),
                            "severity": severity
                        })
                except json.JSONDecodeError:
                    vulnerabilities = [{"message": result.stdout.strip()}]
            
            results.append(SecurityResult(
                tool="semgrep",
                success=result.returncode == 0 and critical_count == 0 and high_count == 0,
                vulnerabilities=vulnerabilities,
                critical_count=critical_count,
                high_count=high_count,
                medium_count=medium_count
            ))
        except Exception as e:
            results.append(SecurityResult(
                tool="semgrep",
                success=False,
                vulnerabilities=[{"error": str(e)}],
                critical_count=1,
                high_count=0,
                medium_count=0
            ))
        
        return results
    
    def _generate_diff_comments(self, file_path: str, diff_content: str) -> List[Dict[str, Any]]:
        """Generate comments based on diff content."""
        comments = []
        
        # Simple line-by-line analysis
        lines = diff_content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('+') and len(line) > 1:
                # Added line - check for common issues
                content = line[1:].strip()
                
                # Check for hardcoded secrets
                if "api_key" in content.lower() or "secret" in content.lower():
                    comments.append({
                        "line": i + 1,
                        "type": "security",
                        "severity": "critical",
                        "message": "Possible hardcoded secret detected",
                        "suggestion": "Use environment variables or secure configuration"
                    })
                
                # Check for console.log calls
                elif "console.log" in content:
                    comments.append({
                        "line": i + 1,
                        "type": "maintainability",
                        "severity": "medium",
                        "message": "Console log detected",
                        "suggestion": "Remove or replace with proper logging"
                    })
                
                # Check for TODO comments
                elif "TODO" in content:
                    comments.append({
                        "line": i + 1,
                        "type": "maintainability",
                        "severity": "low",
                        "message": "TODO comment detected",
                        "suggestion": "Create proper issue or tracking item"
                    })
        
        return comments
    
    def _generate_summary(self, linter_results: List[LinterResult], 
                          security_results: List[SecurityResult]) -> Dict[str, Any]:
        """Generate overall summary of code review."""
        total_errors = sum(result.error_count for result in linter_results)
        total_warnings = sum(result.warning_count for result in linter_results)
        total_critical = sum(result.critical_count for result in security_results)
        total_high = sum(result.high_count for result in security_results)
        total_medium = sum(result.medium_count for result in security_results)
        
        # Determine overall status
        status = "approved"
        if total_critical > 0 or total_high > 0:
            status = "rejected"
        elif total_errors > 0:
            status = "needs_revision"
        elif total_warnings > 0 or total_medium > 0:
            status = "approved_with_comments"
        
        return {
            "status": status,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "total_critical": total_critical,
            "total_high": total_high,
            "total_medium": total_medium,
            "total_low": 0,  # Placeholder
            "linter_results": len(linter_results),
            "security_results": len(security_results)
        }
    
    def _get_current_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()
    
    def generate_review_report(self, review: CodeReview) -> str:
        """Generate a human-readable review report."""
        output = []
        output.append(f"# Code Review Report for {review.file_path}")
        output.append(f"Generated: {review.timestamp}")
        output.append("")
        
        # Summary
        output.append("## Summary")
        output.append(f"Status: {review.summary['status']}")
        output.append(f"Errors: {review.summary['total_errors']}")
        output.append(f"Warnings: {review.summary['total_warnings']}")
        output.append(f"Critical Issues: {review.summary['total_critical']}")
        output.append(f"High Issues: {review.summary['total_high']}")
        output.append(f"Medium Issues: {review.summary['total_medium']}")
        output.append("")
        
        # Linter Results
        if review.linter_results:
            output.append("## Linter Results")
            for result in review.linter_results:
                output.append(f"### {result.linter}")
                output.append(f"Success: {result.success}")
                output.append(f"Issues: {len(result.issues)}")
                output.append(f"Errors: {result.error_count}")
                output.append(f"Warnings: {result.warning_count}")
                if result.issues:
                    output.append("Issues:")
                    for issue in result.issues[:5]:  # Limit to first 5
                        output.append(f"  - {issue}")
                output.append("")
        
        # Security Results
        if review.security_results:
            output.append("## Security Results")
            for result in review.security_results:
                output.append(f"### {result.tool}")
                output.append(f"Success: {result.success}")
                output.append(f"Vulnerabilities: {len(result.vulnerabilities)}")
                output.append(f"Critical: {result.critical_count}")
                output.append(f"High: {result.high_count}")
                output.append(f"Medium: {result.medium_count}")
                if result.vulnerabilities:
                    output.append("Vulnerabilities:")
                    for vuln in result.vulnerabilities[:5]:  # Limit to first 5
                        output.append(f"  - {vuln}")
                output.append("")
        
        # Diff Comments
        if review.diff_aware_comments:
            output.append("## Diff-Aware Comments")
            for comment in review.diff_aware_comments:
                output.append(f"### Line {comment.get('line', '?')}: {comment.get('message', '')}")
                output.append(f"Severity: {comment.get('severity', 'low')}")
                output.append(f"Suggestion: {comment.get('suggestion', 'No suggestion')}")
                output.append("")
        
        return "\n".join(output)


def create_code_reviewer(project_root: str = ".") -> CodeReviewer:
    """Factory function to create a CodeReviewer instance."""
    return CodeReviewer(project_root)


# Example usage:
if __name__ == "__main__":
    # Create reviewer
    reviewer = create_code_reviewer("/Users/venom/Documents/analyse-financiere")
    
    # Review a sample file
    review = reviewer.review_file("webapp/src/App.tsx")
    
    # Generate and print report
    report_text = reviewer.generate_review_report(review)
    print(report_text)
    
    # Save report
    report_file = Path("data/code_review_report.md")
    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text(report_text, encoding="utf-8")
    print(f"\nReport saved to: {report_file}")