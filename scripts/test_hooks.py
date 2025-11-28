#!/usr/bin/env python3
"""
Automated testing script for sample hooks in the OpenHands repository.

This script provides comprehensive testing for all hook implementations including:
- Web hooks (web_hook.py and batched_web_hook.py)
- Git hooks
- Any future hook implementations

Usage:
    python scripts/test_hooks.py [--verbose] [--coverage] [--hook-type TYPE] [--performance] [--integration]
"""

import argparse
import sys
import subprocess
import os
import time
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime


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


def run_pytest_tests(test_path: str, verbose: bool = False, coverage: bool = False, 
                     extra_args: Optional[List[str]] = None) -> tuple[bool, Dict[str, Any]]:
    """Run pytest tests for a specific test path and return results."""
    cmd = ["python", "-m", "pytest", test_path, "-v", "--json-report", "--json-report-file=test_results.json"]
    
    if verbose:
        cmd.append("-vv")
    
    if coverage:
        cmd.extend([
            "--cov=openhands.storage",
            "--cov=openhands.runtime",
            "--cov-report=term-missing",
            "--cov-report=html:htmlcov",
            "--cov-report=json:coverage.json"
        ])
    
    if extra_args:
        cmd.extend(extra_args)
    
    start_time = time.time()
    exit_code, stdout, stderr = run_command(cmd)
    end_time = time.time()
    
    # Parse test results
    results = {
        "success": exit_code == 0,
        "duration": end_time - start_time,
        "stdout": stdout,
        "stderr": stderr,
        "test_count": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "coverage": {}
    }
    
    # Try to parse JSON report
    try:
        if Path("test_results.json").exists():
            with open("test_results.json", "r") as f:
                json_report = json.load(f)
                summary = json_report.get("summary", {})
                results["test_count"] = summary.get("total", 0)
                results["passed"] = summary.get("passed", 0)
                results["failed"] = summary.get("failed", 0)
                results["skipped"] = summary.get("skipped", 0)
    except Exception:
        pass
    
    # Try to parse coverage report
    try:
        if Path("coverage.json").exists():
            with open("coverage.json", "r") as f:
                coverage_data = json.load(f)
                totals = coverage_data.get("totals", {})
                results["coverage"] = {
                    "percent_covered": totals.get("percent_covered", 0),
                    "covered_lines": totals.get("covered_lines", 0),
                    "missing_lines": totals.get("missing_lines", 0),
                    "num_statements": totals.get("num_statements", 0)
                }
    except Exception:
        pass
    
    print(f"Running tests for {test_path}:")
    print("=" * 60)
    print(stdout)
    
    if stderr:
        print("STDERR:")
        print(stderr)
    
    return results["success"], results


def test_web_hooks(verbose: bool = False, coverage: bool = False, 
                   performance: bool = False) -> Dict[str, Any]:
    """Test web hook implementations."""
    print("🔗 Testing Web Hooks...")
    
    results = {
        "basic_webhook": {},
        "batched_webhook": {},
        "overall_success": False
    }
    
    # Test basic web hook
    basic_success, basic_results = run_pytest_tests(
        "tests/unit/storage/test_web_hook.py",
        verbose=verbose,
        coverage=coverage
    )
    results["basic_webhook"] = basic_results
    
    # Test batched web hook
    batched_success, batched_results = run_pytest_tests(
        "tests/unit/storage/test_batched_web_hook.py",
        verbose=verbose,
        coverage=coverage
    )
    results["batched_webhook"] = batched_results
    
    # Performance tests if requested
    if performance:
        print("🏃 Running performance tests...")
        perf_success, perf_results = run_pytest_tests(
            "tests/unit/storage/test_batched_web_hook.py",
            verbose=verbose,
            coverage=False,
            extra_args=["-k", "performance"]
        )
        results["performance"] = perf_results
    
    results["overall_success"] = basic_success and batched_success
    return results


def test_git_hooks(verbose: bool = False, coverage: bool = False) -> Dict[str, Any]:
    """Test git hook implementations."""
    print("🔧 Testing Git Hooks...")
    
    success, results = run_pytest_tests(
        "tests/unit/runtime/test_git_hooks.py",
        verbose=verbose,
        coverage=coverage
    )
    
    return {
        "git_hooks": results,
        "overall_success": success
    }


def test_integration_hooks(verbose: bool = False) -> Dict[str, Any]:
    """Test integration scenarios for hooks."""
    print("🔗 Testing Hook Integration...")
    
    # For now, run all hook tests as integration
    integration_results = {}
    
    # Test web hooks integration
    web_results = test_web_hooks(verbose=verbose, coverage=False)
    integration_results["web_integration"] = web_results
    
    # Test git hooks integration  
    git_results = test_git_hooks(verbose=verbose, coverage=False)
    integration_results["git_integration"] = git_results
    
    integration_results["overall_success"] = (
        web_results["overall_success"] and git_results["overall_success"]
    )
    
    return integration_results


def test_all_hooks(verbose: bool = False, coverage: bool = False, 
                  performance: bool = False, integration: bool = False) -> Dict[str, Any]:
    """Test all hook implementations."""
    print("🚀 Testing All Hooks...")
    
    results = {
        "timestamp": datetime.now().isoformat(),
        "web_hooks": {},
        "git_hooks": {},
        "overall_success": False
    }
    
    # Test web hooks
    web_results = test_web_hooks(verbose=verbose, coverage=coverage, performance=performance)
    results["web_hooks"] = web_results
    
    # Test git hooks
    git_results = test_git_hooks(verbose=verbose, coverage=coverage)
    results["git_hooks"] = git_results
    
    # Integration tests if requested
    if integration:
        integration_results = test_integration_hooks(verbose=verbose)
        results["integration"] = integration_results
    
    results["overall_success"] = (
        web_results["overall_success"] and git_results["overall_success"] and
        (not integration or results.get("integration", {}).get("overall_success", True))
    )
    
    return results


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


def generate_test_report(results: Dict[str, Any]) -> None:
    """Generate a comprehensive test report summary."""
    print("\n" + "=" * 80)
    print("📊 COMPREHENSIVE TEST REPORT SUMMARY")
    print("=" * 80)
    
    # Overall status
    overall_success = results.get("overall_success", False)
    status_emoji = "✅" if overall_success else "❌"
    print(f"Overall Status: {status_emoji} {'PASSED' if overall_success else 'FAILED'}")
    print(f"Test Timestamp: {results.get('timestamp', 'Unknown')}")
    print()
    
    # Web hooks results
    if "web_hooks" in results:
        web_results = results["web_hooks"]
        print("🔗 Web Hooks Results:")
        print("-" * 40)
        
        if "basic_webhook" in web_results:
            basic = web_results["basic_webhook"]
            basic_status = "✅ PASSED" if basic.get("success", False) else "❌ FAILED"
            print(f"  Basic Web Hook:    {basic_status}")
            if basic.get("test_count"):
                print(f"    Tests: {basic['test_count']} ({basic['passed']} passed, {basic['failed']} failed)")
                print(f"    Duration: {basic.get('duration', 0):.2f}s")
                if basic.get("coverage", {}).get("percent_covered"):
                    print(f"    Coverage: {basic['coverage']['percent_covered']:.1f}%")
        
        if "batched_webhook" in web_results:
            batched = web_results["batched_webhook"]
            batched_status = "✅ PASSED" if batched.get("success", False) else "❌ FAILED"
            print(f"  Batched Web Hook:  {batched_status}")
            if batched.get("test_count"):
                print(f"    Tests: {batched['test_count']} ({batched['passed']} passed, {batched['failed']} failed)")
                print(f"    Duration: {batched.get('duration', 0):.2f}s")
                if batched.get("coverage", {}).get("percent_covered"):
                    print(f"    Coverage: {batched['coverage']['percent_covered']:.1f}%")
        
        if "performance" in web_results:
            perf = web_results["performance"]
            perf_status = "✅ PASSED" if perf.get("success", False) else "❌ FAILED"
            print(f"  Performance Tests: {perf_status}")
            if perf.get("test_count"):
                print(f"    Tests: {perf['test_count']} ({perf['passed']} passed, {perf['failed']} failed)")
        print()
    
    # Git hooks results
    if "git_hooks" in results:
        git_results = results["git_hooks"]
        print("🔧 Git Hooks Results:")
        print("-" * 40)
        
        if "git_hooks" in git_results:
            git = git_results["git_hooks"]
            git_status = "✅ PASSED" if git.get("success", False) else "❌ FAILED"
            print(f"  Git Hooks:         {git_status}")
            if git.get("test_count"):
                print(f"    Tests: {git['test_count']} ({git['passed']} passed, {git['failed']} failed)")
                print(f"    Duration: {git.get('duration', 0):.2f}s")
                if git.get("coverage", {}).get("percent_covered"):
                    print(f"    Coverage: {git['coverage']['percent_covered']:.1f}%")
        print()
    
    # Integration results
    if "integration" in results:
        integration_results = results["integration"]
        print("🔗 Integration Tests:")
        print("-" * 40)
        integration_status = "✅ PASSED" if integration_results.get("overall_success", False) else "❌ FAILED"
        print(f"  Integration:       {integration_status}")
        print()
    
    # Summary statistics
    print("📈 Summary Statistics:")
    print("-" * 40)
    
    total_tests = 0
    total_passed = 0
    total_failed = 0
    total_duration = 0
    
    def extract_stats(result_dict):
        nonlocal total_tests, total_passed, total_failed, total_duration
        if isinstance(result_dict, dict):
            if "test_count" in result_dict:
                total_tests += result_dict.get("test_count", 0)
                total_passed += result_dict.get("passed", 0)
                total_failed += result_dict.get("failed", 0)
                total_duration += result_dict.get("duration", 0)
            
            # Recursively process nested dictionaries
            for value in result_dict.values():
                if isinstance(value, dict):
                    extract_stats(value)
    
    extract_stats(results)
    
    print(f"  Total Tests Run:    {total_tests}")
    print(f"  Total Passed:       {total_passed}")
    print(f"  Total Failed:       {total_failed}")
    print(f"  Total Duration:     {total_duration:.2f}s")
    if total_tests > 0:
        print(f"  Success Rate:       {(total_passed / total_tests * 100):.1f}%")
    
    print()
    
    # Save detailed report to file
    report_file = f"hook_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(report_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"📄 Detailed report saved to: {report_file}")
    except Exception as e:
        print(f"⚠️  Could not save detailed report: {e}")
    
    print("=" * 80)
    
    if overall_success:
        print("🎉 All hook tests passed successfully!")
        sys.exit(0)
    else:
        print("💥 Some hook tests failed. Check the details above.")
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Automated testing for OpenHands hooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/test_hooks.py                           # Test all hooks
    python scripts/test_hooks.py --webhook                 # Test only web hooks
    python scripts/test_hooks.py --git-hook                # Test only git hooks
    python scripts/test_hooks.py --verbose                 # Verbose output
    python scripts/test_hooks.py --coverage                # Generate coverage report
    python scripts/test_hooks.py --performance             # Run performance tests
    python scripts/test_hooks.py --integration             # Run integration tests
    python scripts/test_hooks.py --webhook --performance   # Performance tests for webhooks
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
    
    parser.add_argument(
        "--performance", "-p",
        action="store_true",
        help="Run performance tests"
    )
    
    parser.add_argument(
        "--integration", "-i",
        action="store_true",
        help="Run integration tests"
    )
    
    args = parser.parse_args()
    
    # Check test environment
    if not check_test_environment():
        sys.exit(1)
    
    # Run tests based on arguments
    results = {}
    
    if args.webhook:
        results = test_web_hooks(
            verbose=args.verbose, 
            coverage=args.coverage, 
            performance=args.performance
        )
        results["overall_success"] = results["overall_success"]
    elif args.git_hook:
        results = test_git_hooks(verbose=args.verbose, coverage=args.coverage)
        results["overall_success"] = results["overall_success"]
    else:
        # Test all hooks
        results = test_all_hooks(
            verbose=args.verbose,
            coverage=args.coverage,
            performance=args.performance,
            integration=args.integration
        )
    
    # Generate report
    generate_test_report(results)


if __name__ == "__main__":
    main()