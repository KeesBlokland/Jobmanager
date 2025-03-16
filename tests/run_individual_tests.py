#!/usr/bin/env python3
# tests/run_individual_tests.py

import unittest
import os
import sys

def run_tests():
    """Run individual test files directly to avoid import issues"""
    
    print("=== Running individual tests to avoid circular imports ===\n")
    
    # Get the path to all test files
    current_dir = os.path.dirname(os.path.abspath(__file__))
    test_files = [
        f for f in os.listdir(current_dir) 
        if f.startswith('test_') and f.endswith('.py') and f != 'test_runner.py'
    ]
    
    success_count = 0
    failure_count = 0
    
    for test_file in test_files:
        test_module = test_file[:-3]  # Remove .py extension
        print(f"\n=== Running {test_module} ===")
        
        try:
            # Run the test file as a script
            result = os.system(f"python3 {current_dir}/{test_file}")
            
            if result == 0:
                print(f"✅ {test_module} PASSED")
                success_count += 1
            else:
                print(f"❌ {test_module} FAILED")
                failure_count += 1
        except Exception as e:
            print(f"❌ {test_module} ERROR: {str(e)}")
            failure_count += 1
    
    print(f"\n=== Test Summary ===")
    print(f"Total test files: {len(test_files)}")
    print(f"Passed: {success_count}")
    print(f"Failed: {failure_count}")
    
    return failure_count == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)