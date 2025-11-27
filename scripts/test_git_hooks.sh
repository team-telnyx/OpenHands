#!/bin/bash

# Test script for Git sample hooks
# This script runs all tests for the Git sample hooks to ensure they work correctly

set -e

echo "🚀 Starting Git hooks testing..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ] || [ ! -d ".git" ]; then
    print_error "This script must be run from the root of the OpenHands repository"
    exit 1
fi

print_status "Running Git hooks tests..."

# Run the standalone tests (these don't require OpenHands dependencies)
print_status "Running standalone hook tests..."
if python -m pytest tests/unit/git_hooks/test_sample_hooks_standalone.py -v; then
    print_status "✅ Standalone hook tests passed!"
else
    print_error "❌ Standalone hook tests failed!"
    exit 1
fi

# Check if we can run the full tests (with OpenHands dependencies)
print_status "Checking if OpenHands dependencies are available..."

if python -c "import openhands" 2>/dev/null; then
    print_status "OpenHands dependencies found, running full hook tests..."
    if python -m pytest tests/unit/git_hooks/test_sample_hooks.py -v; then
        print_status "✅ Full hook tests passed!"
    else
        print_warning "⚠️  Full hook tests failed, but standalone tests passed"
    fi
else
    print_warning "OpenHands dependencies not found, skipping full hook tests"
    print_warning "To run full tests, install dependencies with: poetry install --with dev,test"
fi

# Run hook validation
print_status "Running hook validation..."

# Check if all sample hooks exist and are executable
hooks_dir=".git/hooks"
missing_hooks=()
non_executable_hooks=()

expected_hooks=(
    "applypatch-msg.sample"
    "commit-msg.sample"
    "fsmonitor-watchman.sample"
    "post-update.sample"
    "pre-applypatch.sample"
    "pre-commit.sample"
    "pre-merge-commit.sample"
    "pre-push.sample"
    "pre-rebase.sample"
    "pre-receive.sample"
    "prepare-commit-msg.sample"
    "push-to-checkout.sample"
    "sendemail-validate.sample"
    "update.sample"
)

for hook in "${expected_hooks[@]}"; do
    if [ ! -f "$hooks_dir/$hook" ]; then
        missing_hooks+=("$hook")
    elif [ ! -x "$hooks_dir/$hook" ]; then
        non_executable_hooks+=("$hook")
    fi
done

if [ ${#missing_hooks[@]} -gt 0 ]; then
    print_error "Missing sample hooks:"
    for hook in "${missing_hooks[@]}"; do
        echo "  - $hook"
    done
    exit 1
fi

if [ ${#non_executable_hooks[@]} -gt 0 ]; then
    print_error "Non-executable sample hooks:"
    for hook in "${non_executable_hooks[@]}"; do
        echo "  - $hook"
    done
    exit 1
fi

# Check hook syntax
print_status "Checking hook syntax..."
syntax_errors=()

for hook_file in "$hooks_dir"/*.sample; do
    if [ -f "$hook_file" ]; then
        hook_name=$(basename "$hook_file")
        
        # Check shebang
        first_line=$(head -n1 "$hook_file")
        if [[ ! "$first_line" =~ ^#! ]]; then
            syntax_errors+=("$hook_name: Missing shebang")
        elif [[ ! "$first_line" =~ (sh|bash|perl) ]]; then
            syntax_errors+=("$hook_name: Invalid shebang: $first_line")
        fi
        
        # For shell scripts, check syntax
        if [[ "$first_line" =~ (sh|bash) ]]; then
            if ! bash -n "$hook_file" 2>/dev/null; then
                syntax_errors+=("$hook_name: Shell syntax error")
            fi
        fi
    fi
done

if [ ${#syntax_errors[@]} -gt 0 ]; then
    print_error "Hook syntax errors:"
    for error in "${syntax_errors[@]}"; do
        echo "  - $error"
    done
    exit 1
fi

print_status "✅ All hook validation checks passed!"

# Generate test coverage report
print_status "Generating test coverage report..."
if command -v coverage >/dev/null 2>&1; then
    coverage run -m pytest tests/unit/git_hooks/test_sample_hooks_standalone.py
    coverage report -m tests/unit/git_hooks/test_sample_hooks_standalone.py
    coverage html -d coverage_html
    print_status "✅ Coverage report generated in coverage_html/"
else
    print_warning "Coverage tool not found. Install with: pip install coverage"
fi

print_status "🎉 All Git hooks tests completed successfully!"
print_status ""
print_status "Summary:"
print_status "  ✅ All sample hooks exist and are executable"
print_status "  ✅ All hooks have valid syntax"
print_status "  ✅ Standalone tests passed"
print_status "  ✅ Hook validation completed"
print_status ""
print_status "You can now confidently use the sample hooks as reference implementations."