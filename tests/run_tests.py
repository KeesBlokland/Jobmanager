# tests/run_tests.py
import unittest
import sys
import os

# Add the parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

if __name__ == '__main__':
    # Discover and run all tests in the current directory
    test_suite = unittest.defaultTestLoader.discover('.')
    unittest.TextTestRunner().run(test_suite)