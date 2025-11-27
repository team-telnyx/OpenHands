#!/usr/bin/env python3
"""
Automated testing script for sample hooks in the OpenHands repository.

This script provides comprehensive testing for all hook implementations including:
- Web hooks (web_hook.py and batched_web_hook.py)
- Git hooks
- Any future hook implementations

Usage:
    python scripts/test_hooks.py [--verbose] [--coverage] [--hook-type TYPE]
"""

import argparse
import sys
import subprocess
import os
from pathlib import Path
from typing import List, Optional


def run_command(cmd: List[str], cwd: Optional[str] = None) -> tuple[int, str, str]:
    """Run a command and return exit code, stdout, and stderr."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def run_pytest_tests(test_path: str, verbose: bool = False, coverage: bool = False) -> bool:
    """Run pytest tests for a specific test path."""
    cmd = ["python", "-m", "pytest", test_path, "-v"]
    
    if verbose:
        cmd.append("-vv")
    
    if coverage:
        cmd.extend([
            "--cov=openhands.storage",
            "--cov=openhands.runtime",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov"
        ])
    
    exit_code, stdout, stderr = run_command(cmd)
    
    print(f"Running tests for {test_path}:")
    print("=" * 60)
    print(stdout)
    
    if stderr:
        print("STDERR:")
        print(stderr)
    
    return exit_code == 0


def test_web_hooks(verbose: bool = False, coverage: bool = False) -> bool:
    """Test web hook implementations."""
    print("🔗 Testing Web Hooks...")
    
    # Test basic web hook
    basic_success = run_pytest_tests(
        "tests/unit/storage/test_web_hook.py",
        verbose=verbose,
        coverage=coverage
    )
    
    # Test batched web hook
    batched_success = run_pytest_tests(
        "tests/unit/storage/test_batched_web_hook.py",
        verbose=verbose,
        coverage=coverage
    )
    
    return basic_success and batched_success


def test_git_hooks(verbose: bool = False, coverage: bool = False) -> bool:
    """Test git hook implementations."""
    print("🔧 Testing Git Hooks...")
    
    return run_pytest_tests(
        "tests/unit/runtime/test_git_hooks.py",
        verbose=verbose,
        coverage=coverage
    )


def test_all_hooks(verbose: bool = False, coverage: bool = False) -> bool:
    """Test all hook implementations."""
    print("🚀 Testing All Hooks...")
    
    results = []
    
    # Test web hooks
    results.append(test_web_hooks(verbose, coverage))
    
    # Test git hooks
    results.append(test_git_hooks(verbose, coverage))
    
    return all(results)


def check_test_environment() -> bool:
    """Check if the testing environment is properly set up."""
    print("🔍 Checking test environment...")
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Error: pyproject.toml not found. Please run from repository root.")
        return False
    
    # Check if pytest is available
    exit_code, _, _ = run_command(["python", "-m", "pytest", "--version"])
    if exit_code != 0:
        print("❌ Error: pytest not available. Please install test dependencies.")
        return False
    
    # Check if test directories exist
    test_dirs = [
        "tests/unit/storage",
        "tests/unit/runtime"
    ]
    
    for test_dir in test_dirs:
        if not Path(test_dir).exists():
            print(f"❌ Error: Test directory {test_dir} not found.")
            return False
    
    print("✅ Test environment is properly set up.")
    return True


def generate_test_report(results: dict) -> None:
    """Generate a test report summary."""
    print("\n" + "=" * 60)
    print("📊 TEST REPORT SUMMARY")
    print("=" * 60)
    
    total_tests = sum(results.values())
    passed_tests = sum(1 for result in results.values() if result)
    
    for hook_type, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{hook_type:20} {status}")
    
    print("-" * 60)
    print(f"Total test suites: {len(results)}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(results) - passed_tests}")
    
    if passed_tests == len(results):
        print("\n🎉 All hook tests passed!")
        sys.exit(0)
    else:
        print(f"\n💥 {len(results) - passed_tests} test suite(s) failed!")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated testing for OpenHooks hooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/test_hooks.py                    # Test all hooks
    python scripts/test_hooks.py --webhook          # Test only web hooks
    python scripts/test_hooks.py --git-hook         # Test only git hooks
    python scripts/test_hooks.py --verbose          # Verbose output
    python scripts/test_hooks.py --coverage         # Generate coverage report
        """
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--webhook",
        action="store_true",
        help="Test only web hooks"
    )
    
    parser.add_argument(
        "--git-hook",
        action="store_true",
        help="Test only git hooks"
    )
    
    args = parser.parse_args()
    
    # Check test environment
    if not check_test_environment():
        sys.exit(1)
    
    # Run tests based on arguments
    results = {}
    
    if args.webhook:
        results["Web Hooks"] = test_web_hooks(args.verbose, args.coverage)
    elif args.git_hook:
        results["Git Hooks"] = test_git_hooks(args.verbose, args.coverage)
    else:
        # Test all hooks
        results["Web Hooks"] = test_web_hooks(args.verbose, args.coverage)
        results["Git Hooks"] = test_git_hooks(args.verbose, args.coverage)
    
    # Generate report
    generate_test_report(results)


if __name__ == "__main__":
    main()