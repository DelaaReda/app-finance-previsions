# 🧪 Codacy Integration Guide - Finance Copilot

## Purpose

This document explains how to use the Codacy analysis system for code quality in the Finance Copilot project. The integration helps detect potential issues in code, maintain consistent style, and ensure security best practices.

## Setup Instructions

### 1. Install Codacy CLI
Ensure you have the codacy-cli installed on your system:

```bash
# Install globally using npm
npm install -g @codacy/cli

# Or using the official installation script
curl -L https://github.com/codacy/codacy-cli/releases/latest/download/codacy-cli-Linux-x86_64.tar.gz | tar xz
sudo mv codacy-cli /usr/local/bin/
```

### 2. Verify Installation
```bash
codacy-cli --version
```

## Usage Instructions

### Run Complete Analysis
```bash
# Analyze the entire project
./scripts/quality/codacy-analyze.sh

# Analyze specific directory
./scripts/quality/codacy-analyze.sh backend/
./scripts/quality/codacy-analyze.sh frontend/webapp/
```

### Generate SARIF Output
```bash
# Generate SARIF format results (good for integrations)
./scripts/quality/codacy-analyze.sh -f sarif -o results.sarif

# For specific tools
./scripts/quality/codacy-analyze.sh --tool eslint -f sarif -o eslint-results.sarif
```

### Analyze with Specific Tools
```bash
# Run specific analysis tools
./scripts/quality/codacy-analyze.sh --tool eslint
./scripts/quality/codacy-analyze.sh --tool pylint
```

## Integration with Development Workflow

### 1. Pre-commit Hook
The system includes a pre-commit hook that runs basic smoke tests. To add Codacy analysis:

```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run codacy analysis on modified files only (fast check)
MODIFIED_PY=$(git diff --cached --name-only --diff-filter=ACM | grep "\.py$" || true)
MODIFIED_TS=$(git diff --cached --name-only --diff-filter=ACM | grep -E "\.(ts|tsx|js|jsx)$" || true)

if [ -n "$MODIFIED_PY" ]; then
    echo "🧪 Running Python analysis on modified files..."
    echo "$MODIFIED_PY" | xargs codacy-cli analyze --tool pylint --project-root .
fi

if [ -n "$MODIFIED_TS" ]; then
    echo "🧪 Running TypeScript analysis on modified files..."  
    echo "$MODIFIED_TS" | xargs codacy-cli analyze --tool eslint --project-root .
fi

echo "✅ Code quality check passed"
```

### 2. Continuous Quality Checks
Regular team members should run:
```bash
# Before major commits
./scripts/quality/codacy-analyze.sh -f sarif -o quality-report-$(date +%Y%m%d).sarif

# To check specific issues
./scripts/quality/codacy-analyze.sh backend/models/ -f text
```

## Quality Standards for Finance Copilot

The following standards should be maintained based on Codacy analysis:

### Python Backend
- Cyclomatic complexity < 10 (preferably < 5)
- Function length < 100 lines
- No unused imports or variables
- No hardcoded credentials or secrets
- Proper exception handling
- Type hints on function signatures

### TypeScript Frontend  
- No `any` type (except in specific cases with comments)
- Proper error boundaries and empty state handling
- Safe access patterns: `data?.field ?? []`
- Proper async/await error handling
- No console.log statements in production code

### API Endpoints
- Always return structured responses (never return raw errors or undefined)
- Follow the `{ok, data}` pattern consistently
- Include freshness metadata
- Handle empty results gracefully

## Common Issues & Solutions

### 1. Import Problems
If Codacy reports import issues:
- Check Python package structure (proper `__init__.py` files)
- Use absolute imports: `from backend.services import ...`
- Avoid circular dependencies

### 2. Duplicate Code
- Extract repeated code into reusable functions
- Create utility modules for common operations
- Use composition over inheritance where possible

### 3. Security Issues
- Never hardcode API keys or credentials
- Sanitize user inputs
- Validate all external parameters

## Quality Gates

Before any commit:
1. Run `./scripts/quality/codacy-analyze.sh --tool eslint` on frontend changes
2. Run `./scripts/quality/codacy-analyze.sh --tool pylint` on backend changes
3. Address any HIGH or CRITICAL severity issues
4. Ensure no new issues are introduced in modified files
5. Run the smoke tests: `./scripts/smoke.sh`

## Sample Commands

```bash
# Quick check on backend
./scripts/quality/codacy-analyze.sh backend/ -f text

# Full analysis with SARIF output
./scripts/quality/codacy-analyze.sh -f sarif -o full-analysis.sarif

# Check specific file types
find backend/ -name "*.py" -exec codacy-cli analyze --tool pylint {} \;

# Check for vulnerabilities only
codacy-cli analyze --categories vulnerability --project-root .
```

## Troubleshooting

### Command not found
If `codacy-cli` is not found:
```bash
# Make sure it's in your PATH
export PATH=$PATH:~/.npm-global/bin
# Or install using the official method
```

### Analysis taking too long
- For quick checks, use specific tool: `--tool eslint`
- Analyze only specific directories: `./scripts/quality/codacy-analyze.sh backend/api/`
- Limit to modified files only

This ensures high code quality across the Finance Copilot system while maintaining the rapid development pace needed for the project.