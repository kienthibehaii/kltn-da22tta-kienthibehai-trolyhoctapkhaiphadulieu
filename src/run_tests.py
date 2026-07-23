# run_tests.py
"""
Comprehensive test runner for RAG Learning Assistant
"""

import subprocess
import sys
import os
from datetime import datetime


def print_section(title):
    """Print section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def run_command(command, description):
    """Run command and handle errors"""
    print(f"\n🔄 {description}...")
    print(f"Command: {command}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True
        )
        
        print(result.stdout)
        
        if result.returncode != 0:
            print(f"❌ Failed: {description}")
            print(result.stderr)
            return False
        else:
            print(f"✅ Passed: {description}")
            return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "🧪"*35)
    print("  COMPREHENSIVE TEST SUITE")
    print("  RAG Learning Assistant")
    print("🧪"*35)
    print(f"\nStarted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # 1. Unit Tests
    print_section("UNIT TESTS")
    results['unit'] = run_command(
        "pytest tests/unit -v --cov=auth --cov=. --cov-report=term-missing -m unit",
        "Running unit tests"
    )
    
    # 2. Integration Tests
    print_section("INTEGRATION TESTS")
    results['integration'] = run_command(
        "pytest tests/integration -v -m integration",
        "Running integration tests"
    )
    
    # 3. Coverage Report
    print_section("COVERAGE REPORT")
    results['coverage'] = run_command(
        "pytest --cov=. --cov-report=html --cov-report=term",
        "Generating coverage report"
    )
    
    # 4. Test Summary
    print_section("TEST SUMMARY")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    failed_tests = total_tests - passed_tests
    
    print(f"\nTotal test suites: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    
    if failed_tests == 0:
        print("\n🎉 ALL TESTS PASSED!")
        print("\n📊 Coverage report: htmlcov/index.html")
        return 0
    else:
        print("\n⚠️ SOME TESTS FAILED")
        print("\nFailed suites:")
        for name, passed in results.items():
            if not passed:
                print(f"  - {name}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
