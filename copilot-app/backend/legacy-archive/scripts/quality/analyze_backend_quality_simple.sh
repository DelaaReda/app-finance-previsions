#!/bin/bash
# Backend Quality Analysis Script
# Task: FC-QM-CODACY-002 - Backend Quality Analysis & Corrections
# Author: LENA-LLM-STRATEGIST-WONDERWOMAN-21

echo "🔍 STARTING BACKEND CODE QUALITY ANALYSIS"
echo "Task: FC-QM-CODACY-002 - Backend Quality Analysis & Corrections" 
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "----------------------------------------"

# Define directories to analyze
BACKEND_DIR="/Users/venom/Documents/analyse-financiere/copilot-app/backend"

# Create reports directory
REPORTS_DIR="$BACKEND_DIR/reports"
mkdir -p "$REPORTS_DIR"

# 1. Security Analysis
echo "🛡️  Performing Security Analysis..."
SECURITY_FILE="$REPORTS_DIR/security_findings.txt"
{
    echo "Security Analysis Report - $(date)"
    echo "=================================="
    
    # Check for potential credential issues  
    echo "Searching for potential credential/storage issues..."
    credential_hits=$(find "$BACKEND_DIR" -name "*.py" -exec grep -Hi -E "(secret|token|password|api_key|key.*=)" {} \; 2>/dev/null | grep -vi "demo\|test\|stub\|placeholder\|_test\|test_" | wc -l)
    echo "  - Potential credential patterns found: $credential_hits"
    
    # Check for potential path traversal issues
    echo "Checking for potential path traversal issues..."
    traversal_hits=$(find "$BACKEND_DIR" -name "*.py" -exec grep -Hn "os\.path\.join\|path.*\+\|open.*\+" {} \; 2>/dev/null | wc -l)
    echo "  - Potential path traversal patterns: $traversal_hits"
    
    echo ""
    echo "Security Scan Complete"
} > "$SECURITY_FILE"

echo "✅ Security analysis completed"

# 2. Code Style Analysis  
echo ""
echo "🧹 Performing Code Style Analysis..."

STYLE_FILE="$REPORTS_DIR/style_findings.txt"
{
    echo "Code Style Analysis Report - $(date)"
    echo "==================================="
    
    # Count lines of code
    loc_count=$(find "$BACKEND_DIR" -name "*.py" -exec cat {} \; | wc -l)
    file_count=$(find "$BACKEND_DIR" -name "*.py" | wc -l)
    echo "Code Metrics:"
    echo "  - Total Python lines: $loc_count"
    echo "  - Total Python files: $file_count"
    echo ""
    
    # Check for technical debt markers
    debt_markers=$(grep -r -n -E "(TODO|FIXME|HACK|\#.*todo|\#.*fixme)" "$BACKEND_DIR" --include="*.py" | grep -v ".git" | wc -l)
    echo "Technical Debt:"
    echo "  - TODO/FIXME/HACK markers: $debt_markers"
    if [ "$debt_markers" -gt 0 ]; then
        echo "  - Locations (first 10):"
        grep -r -n -E "(TODO|FIXME|HACK|\#.*todo|\#.*fixme)" "$BACKEND_DIR" --include="*.py" | head -10
    fi
    echo ""
    
} > "$STYLE_FILE"

echo "✅ Style analysis completed"

# 3. Performance Analysis
echo ""
echo "⚡ Performing Performance Analysis..."

PERFORMANCE_FILE="$REPORTS_DIR/performance_findings.txt"
{
    echo "Performance Analysis Report - $(date)"
    echo "===================================="
    
    # Check for potentially inefficient patterns
    perf_hits=$(grep -r -n -E "(for.*in.*range.*1000|while.*True|time\.sleep|sleep\()" "$BACKEND_DIR" --include="*.py" | wc -l)
    echo "Performance Patterns:"
    echo "  - Potentially inefficient loops/sleeps: $perf_hits"
    if [ "$perf_hits" -gt 0 ]; then
        echo "  - Details (first 10):"
        grep -r -n -E "(for.*in.*range.*1000|while.*True|time\.sleep|sleep\()" "$BACKEND_DIR" --include="*.py" | head -10
    fi
    echo ""
    
} > "$PERFORMANCE_FILE"

echo "✅ Performance analysis completed"

# 4. Error Handling Analysis
echo ""
echo "❌ Performing Error Handling Analysis..."

ERROR_FILE="$REPORTS_DIR/error_handling_findings.txt"
{
    echo "Error Handling Analysis Report - $(date)"
    echo "========================================"
    
    # Count try/except usage
    try_count=$(grep -r -c "try:" "$BACKEND_DIR" --include="*.py" | awk -F: '{sum+=$2} END {print sum+0}')
    except_count=$(grep -r -c "except:" "$BACKEND_DIR" --include="*.py" | awk -F: '{sum+=$2} END {print sum+0}')
    bare_excepts=$(grep -r -n "except:" "$BACKEND_DIR" --include="*.py" | grep -v -E "(Exception|ValueError|TypeError|IOError|FileNotFoundError|ImportError|KeyError|IndexError)" | wc -l)
    
    echo "Error Handling Metrics:"
    echo "  - Try blocks found: $try_count"
    echo "  - Except blocks found: $except_count" 
    echo "  - Bare except clauses (dangerous): $bare_excepts"
    if [ "$bare_excepts" -gt 0 ]; then
        echo "  - Bare except locations (first 5):"
        grep -r -n "except:" "$BACKEND_DIR" --include="*.py" | grep -v -E "(Exception|ValueError|TypeError|IOError|FileNotFoundError|ImportError|KeyError|IndexError)" | head -5
    fi
    echo ""
    
} > "$ERROR_FILE"

echo "✅ Error handling analysis completed"

# 5. Generate Summary Report
echo ""
echo "📈 Generating Final Summary..."

SUMMARY_FILE="$REPORTS_DIR/quality_analysis_summary.txt"
{
    echo "Backend Code Quality Analysis - SUMMARY"
    echo "====================================="
    echo "Task: FC-QM-CODACY-002"
    echo "Agent: LENA-LLM-STRATEGIST-WONDERWOMAN-21" 
    echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo ""
    
    echo "Analysis Results:"
    echo "  - Security findings: $credential_hits potential issues"
    echo "  - Style observations: $debt_markers technical debt markers found"
    echo "  - Performance items: $perf_hits potential inefficiencies"
    echo "  - Error handling: $bare_excepts bare except clauses to fix"
    echo ""
    
    echo "Files analyzed: $file_count Python files ($loc_count lines)"
    echo ""
    
    echo "Detailed reports saved to: $REPORTS_DIR/"
    echo "  - security_findings.txt"
    echo "  - style_findings.txt"
    echo "  - performance_findings.txt" 
    echo "  - error_handling_findings.txt"
    echo ""
    
    echo "Quality Recommendations:"
    echo "  1. Secure credential handling (avoid hardcoded values)"
    echo "  2. Improve error handling (avoid bare excepts)"
    echo "  3. Optimize performance patterns (reduce sleep, inefficient loops)"
    echo "  4. Address technical debt items (TODO/FIXME/HACK comments)"
    echo "  5. Ensure never-empty contracts with proper fallbacks"
    
} > "$SUMMARY_FILE"

cat "$SUMMARY_FILE"

echo ""
echo "📊 ANALYSIS COMPLETE - Reports saved to $REPORTS_DIR/"
echo "🔍 Manual review recommended for all findings"
echo ""
echo "🎯 NEXT STEPS: Implement targeted fixes per FC-QM-CODACY-002 requirements"