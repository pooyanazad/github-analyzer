#!/usr/bin/env python3
"""
Simple test runner script for GitHubAnalyzer project.
Runs unit, quality, and smoke tests in sequence.
"""

import subprocess
import sys
import time

def run_command(cmd, description):
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"Running {description}...")
    print(f"{'='*60}")
    
    start_time = time.time()
    result = subprocess.run(cmd, shell=True)
    end_time = time.time()
    
    duration = end_time - start_time
    if result.returncode == 0:
        print(f"✅ {description} PASSED ({duration:.2f}s)")
        return True
    else:
        print(f"❌ {description} FAILED ({duration:.2f}s)")
        return False

def main():
    """Run all test suites."""
    print("GitHubAnalyzer Test Runner")
    print("=" * 60)
    
    test_suites = [
        ("python -m pytest tests/unit/ -v", "Unit Tests"),
        ("python -m pytest tests/quality/ -v", "Quality Tests"),
        ("python -m pytest tests/smoke/ -v", "Smoke Tests")
    ]
    
    results = []
    total_start = time.time()
    
    for cmd, description in test_suites:
        success = run_command(cmd, description)
        results.append((description, success))
        
        if not success:
            print(f"\n❌ Stopping due to failure in {description}")
            break
    
    total_end = time.time()
    total_duration = total_end - total_start
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    all_passed = True
    for description, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{description:<20} {status}")
        if not success:
            all_passed = False
    
    print(f"\nTotal time: {total_duration:.2f}s")
    
    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n💥 Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())