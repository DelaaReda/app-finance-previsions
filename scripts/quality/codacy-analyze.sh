#!/bin/bash
# Codacy Analysis Script - FC-QM-CODACY-001
# Task: Intégration Codacy CLI dans le workflow de développement

set -euo pipefail

# Default values
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FORMAT="json"
OUTPUT_FILE=""
TARGET_PATH=""
TOOL=""

print_usage() {
    echo "Usage: $0 [OPTIONS] [PATH]"
    echo ""
    echo "Options:"
    echo "  -f, --format FORMAT    Output format: json, sarif, text (default: json)"
    echo "  -o, --output FILE      Output file (default: stdout)"
    echo "  -t, --tool TOOL        Specific tool: eslint, pylint, etc. (default: all)"
    echo "  --help                 Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                            # Analyze whole project, output JSON"
    echo "  $0 backend/                  # Analyze backend only"
    echo "  $0 -f sarif -o results.sarif # Generate SARIF output file"
    echo "  $0 --tool pylint             # Analyze with specific tool"
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--format)
            FORMAT="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -t|--tool)
            TOOL="$2"
            shift 2
            ;;
        --help)
            print_usage
            exit 0
            ;;
        -*)
            echo "Unknown option $1"
            print_usage
            exit 1
            ;;
        *)
            TARGET_PATH="$1"
            shift
            ;;
    esac
done

# Set default target path if not provided
if [ -z "$TARGET_PATH" ]; then
    TARGET_PATH="$PROJECT_ROOT"
fi

echo "🔍 Running Codacy analysis on: $TARGET_PATH"
echo "📝 Format: $FORMAT"

# Change to project root
cd "$PROJECT_ROOT"

# Analyze based on parameters
if [ -n "$TOOL" ]; then
    echo "🔧 Using specific tool: $TOOL"
    if [ -n "$OUTPUT_FILE" ]; then
        codacy-cli analyze -t "$TOOL" --format "$FORMAT" --project-root "$PROJECT_ROOT" -o "$OUTPUT_FILE" "$TARGET_PATH"
    else
        codacy-cli analyze -t "$TOOL" --format "$FORMAT" --project-root "$PROJECT_ROOT" "$TARGET_PATH"
    fi
else
    echo "🔧 Using all configured tools"
    if [ -n "$OUTPUT_FILE" ]; then
        codacy-cli analyze --format "$FORMAT" --project-root "$PROJECT_ROOT" -o "$OUTPUT_FILE" "$TARGET_PATH"
    else
        codacy-cli analyze --format "$FORMAT" --project-root "$PROJECT_ROOT" "$TARGET_PATH"
    fi
fi

echo "✅ Codacy analysis completed"
if [ -n "$OUTPUT_FILE" ]; then
    echo "📄 Results saved to: $OUTPUT_FILE"
else
    echo "📋 Results printed to stdout"
fi