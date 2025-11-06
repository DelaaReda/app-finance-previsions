from __future__ import annotations
import subprocess
import shlex
import json
from typing import Dict, Any, List, Optional
from ..tools.git_tools import _run
from ..tools.ci_tools import run_linters, run_pytests, build_webapp
from ..tools.browser_qa import BrowserQA
from datetime import datetime, timezone


def enhanced_qa_check() -> Dict[str, Any]:
    """
    Enhanced QA check that includes additional validation beyond standard linters/pytests.
    """
    results = {
        "standard_tests": {},
        "architecture_validation": {},
        "vision_alignment": {},
        "security_checks": {},
        "performance_metrics": {},
        "code_coverage": {},
        "branch_health": {},
        "browser_qa": {}
    }
    
    # Run standard tests
    results["standard_tests"] = {
        "linters": run_linters(),
        "pytest": run_pytests(),
        "webapp": build_webapp()
    }
    
    # Run architecture validation
    results["architecture_validation"] = _validate_architecture()
    
    # Check vision alignment
    results["vision_alignment"] = _check_vision_alignment()
    
    # Run security checks
    results["security_checks"] = _run_security_checks()
    
    # Collect performance metrics
    results["performance_metrics"] = _collect_performance_metrics()
    
    # Check code coverage
    results["code_coverage"] = _check_code_coverage()
    
    # Check branch health
    results["branch_health"] = _check_branch_health()
    
    # Run browser QA (web-based validation)
    results["browser_qa"] = _run_browser_qa()
    
    return results


def _run_browser_qa() -> Dict[str, Any]:
    """
    Run browser-based QA to validate web resources and external links.
    """
    try:
        browser_qa = BrowserQA(timeout=30, max_retries=2)
        
        # Check common external resources
        common_urls = [
            "https://finance.yahoo.com/",
            "https://www.investing.com/",
            "https://www.bloomberg.com/",
            "https://www.reuters.com/",
            "https://github.com/"
        ]
        
        validation_results = browser_qa.validate_links(common_urls)
        
        # Check project documentation links
        docs_urls = [
            "https://github.com/venom/analyse-financiere/blob/main/README.md",
            "https://github.com/venom/analyse-financiere/blob/main/docs/VISION.md"
        ]
        
        docs_validation = browser_qa.validate_links(docs_urls)
        
        return {
            "external_resources": validation_results,
            "documentation_links": docs_validation,
            "checked_at": _get_timestamp()
        }
    except Exception as e:
        return {
            "ok": False, 
            "error": str(e), 
            "checked_at": _get_timestamp()
        }


def _validate_architecture() -> Dict[str, Any]:
    """Validate that code changes align with the documented architecture."""
    try:
        # Check for architecture violations
        violations = []
        
        # Look for common anti-patterns in staged files
        rc, out = _run("git diff --cached")
        if rc == 0 and out:
            # Check for hardcoded API keys
            if "api_key" in out.lower() or "secret" in out.lower() or "password" in out.lower():
                violations.append("Potential hardcoded secrets detected")
            
            # Check for large functions/methods (>100 lines)
            lines = out.split('\n')
            current_file = ""
            line_count_in_function = 0
            in_function = False
            
            for i, line in enumerate(lines):
                # Detect file changes
                if line.startswith('--- a/') or line.startswith('+++ b/'):
                    current_file = line.split(' ', 1)[1] if ' ' in line else line
                    continue
                
                # Detect function start/end (simplified)
                if line.startswith('+') and ('def ' in line or 'function ' in line or 'class ' in line):
                    if in_function and line_count_in_function > 100:
                        violations.append(f"Large function detected in {current_file} (>100 lines)")
                    in_function = True
                    line_count_in_function = 1
                elif in_function and line.startswith('+'):
                    line_count_in_function += 1
                elif in_function and not line.startswith('+') and line.strip():
                    # Reset when leaving function context
                    if line_count_in_function > 100:
                        violations.append(f"Large function detected in {current_file} (>100 lines)")
                    in_function = False
                    line_count_in_function = 0
        
        # Check for file structure violations
        rc, staged_files = _run("git diff --cached --name-only")
        if rc == 0:
            files = staged_files.split('\n')
            for file in files:
                if file.endswith('.py'):
                    # Check for test files in wrong location
                    if 'test_' in file and 'tests/' not in file and 'test' not in file.lower():
                        violations.append(f"Test file {file} should be in tests/ directory")
                    # Check for source files in wrong location
                    if file.count('/') > 3 and 'src/' not in file:
                        violations.append(f"Source file {file} should be organized under src/")

        return {
            "ok": len(violations) == 0,
            "violations": violations,
            "checked_at": _get_timestamp()
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "checked_at": _get_timestamp()}


def _check_vision_alignment() -> Dict[str, Any]:
    """Check if recent changes align with the project vision."""
    try:
        # Get recent commits and check if they mention vision-related keywords
        rc, out = _run("git log --oneline -10")
        if rc == 0:
            vision_keywords = [
                "vision", "copilot", "finance", "macro", "stocks", 
                "news", "llm", "rag", "agent", "financial", "analysis"
            ]
            found_keywords = []
            lines = out.lower()
            for keyword in vision_keywords:
                if keyword in lines:
                    found_keywords.append(keyword)
            
            # Check if we're on the right branch
            from ..tools.git_tools import current_branch
            current_br = current_branch()
            branch_aligned = current_br in ["feature/g4f-integration", "local-branch"] or current_br.startswith("feature/")
            
            return {
                "aligned": len(found_keywords) > 0 and branch_aligned,
                "keywords_found": found_keywords,
                "branch_aligned": branch_aligned,
                "current_branch": current_br,
                "checked_at": _get_timestamp()
            }
        return {"aligned": True, "message": "Unable to check", "checked_at": _get_timestamp()}
    except Exception as e:
        return {"ok": False, "error": str(e), "checked_at": _get_timestamp()}


def _run_security_checks() -> Dict[str, Any]:
    """Run basic security checks."""
    try:
        security_issues = []
        
        # Check for common security issues in staged files
        rc, out = _run("git diff --cached --name-only")
        if rc == 0:
            files = out.split('\n')
            for file in files:
                if file.endswith('.py'):
                    # Check for eval/exec usage
                    rc2, content = _run(f"git show :{file}")
                    if rc2 == 0:
                        if "eval(" in content or "exec(" in content:
                            security_issues.append(f"Potentially unsafe eval/exec in {file}")
                        if "os.system(" in content or "subprocess.call(" in content:
                            security_issues.append(f"Potentially unsafe system call in {file}")
        
        # Check for sensitive file exposure
        sensitive_patterns = [".env", ".secret", ".key", ".pem", ".cer"]
        for pattern in sensitive_patterns:
            rc, out = _run(f"git diff --cached --name-only | grep {pattern}")
            if rc == 0 and out.strip():
                security_issues.append(f"Sensitive file pattern detected: {pattern}")
        
        return {
            "issues_found": len(security_issues),
            "issues": security_issues,
            "checked_at": _get_timestamp()
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "checked_at": _get_timestamp()}


def _collect_performance_metrics() -> Dict[str, Any]:
    """Collect basic performance metrics."""
    try:
        # Get basic repo statistics
        rc1, files_changed_output = _run("git diff --cached --name-only | wc -l")
        rc2, lines_added_output = _run("git diff --cached --numstat | awk '{sum += $1} END {print sum}'")
        rc3, lines_removed_output = _run("git diff --cached --numstat | awk '{sum += $2} END {print sum}'")
        
        files_changed = 0
        lines_added = 0
        lines_removed = 0
        
        if rc1 == 0 and files_changed_output.strip().isdigit():
            files_changed = int(files_changed_output.strip())
        
        if rc2 == 0 and lines_added_output.strip().isdigit():
            lines_added = int(lines_added_output.strip())
            
        if rc3 == 0 and lines_removed_output.strip().isdigit():
            lines_removed = int(lines_removed_output.strip())
        
        return {
            "files_changed": files_changed,
            "lines_added": lines_added,
            "lines_removed": lines_removed,
            "net_lines": lines_added - lines_removed,
            "collected_at": _get_timestamp()
        }
    except Exception as e:
        return {"error": str(e), "collected_at": _get_timestamp()}


def _check_code_coverage() -> Dict[str, Any]:
    """Check code coverage if available."""
    try:
        # Try to run coverage check
        rc, out = _run("python -m pytest --cov-report=json --cov=src --cov-fail-under=80 tests/", timeout=60)
        
        if rc == 0:
            return {
                "ok": True,
                "coverage_percentage": "80+",  # Assuming it passed the threshold
                "checked_at": _get_timestamp()
            }
        else:
            # Try without strict threshold
            rc2, out2 = _run("python -m pytest --cov-report=json --cov=src tests/ --tb=no", timeout=60)
            if rc2 == 0:
                # Parse coverage if we can
                try:
                    # Simple heuristic - look for coverage percentage in output
                    import re
                    matches = re.findall(r'(\d+)%', out2)
                    if matches:
                        coverage = max(int(p) for p in matches)
                        return {
                            "ok": coverage >= 80,
                            "coverage_percentage": f"{coverage}%",
                            "checked_at": _get_timestamp()
                        }
                except Exception:
                    pass
            
            return {
                "ok": False,
                "message": "Coverage check failed or not configured",
                "output_preview": out2[:200] if out2 else "",
                "checked_at": _get_timestamp()
            }
    except Exception as e:
        return {"ok": False, "error": f"Coverage check error: {str(e)}", "checked_at": _get_timestamp()}


def _check_branch_health() -> Dict[str, Any]:
    """Check overall branch health."""
    try:
        from ..tools.git_tools import current_branch
        
        current_br = current_branch()
        issues = []
        
        # Check for uncommitted changes
        rc1, uncommitted = _run("git status --porcelain")
        if rc1 == 0 and uncommitted.strip():
            line_count = len(uncommitted.strip().split('\n'))
            issues.append(f"{line_count} uncommitted changes")
        
        # Check for unpushed commits
        rc2, ahead = _run("git rev-list --count HEAD..@{u}")
        if rc2 == 0 and ahead.strip().isdigit() and int(ahead.strip()) > 0:
            issues.append(f"{ahead.strip()} unpushed commits")
        elif rc2 != 0:
            # Likely no upstream, which is fine for feature branches
            pass
        
        # Check branch name validity
        if current_br == "local-branch":
            issues.append("Using reserved branch name 'local-branch'")
        elif not current_br.startswith("feature/") and current_br not in ["main", "master"]:
            issues.append("Branch name should start with 'feature/'")
        
        return {
            "healthy": len(issues) == 0,
            "issues": issues,
            "current_branch": current_br,
            "checked_at": _get_timestamp()
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "checked_at": _get_timestamp()}


def _get_timestamp() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()