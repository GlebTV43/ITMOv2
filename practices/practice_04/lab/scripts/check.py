"""
Trusted runner: discovers and runs all tests under tests/, syntax-checks
all owned Python files via compile(), prints real unittest output, and exits
non-zero on any failure.

False-green guards:
  - Fails if zero tests are discovered.
  - Fails if any required production file is missing.
  - Compiles every owned Python source (excluding __pycache__).
"""
import sys
import os
import glob
import unittest


LAB_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS_DIR = os.path.join(LAB_DIR, "tests")

# Required production files — fail immediately if any is absent
REQUIRED_FILES = [
    os.path.join(LAB_DIR, "registry.py"),
    os.path.join(LAB_DIR, "mcp", "server.py"),
    os.path.join(LAB_DIR, "mcp", "contract.py"),
]


def collect_python_sources():
    """Return every .py file under LAB_DIR, excluding __pycache__ dirs."""
    sources = []
    for root, dirs, files in os.walk(LAB_DIR):
        # Skip __pycache__ and hidden dirs
        dirs[:] = [
            d for d in dirs
            if d != "__pycache__" and not d.startswith(".")
        ]
        for name in files:
            if name.endswith(".py"):
                sources.append(os.path.join(root, name))
    return sources


def syntax_check():
    errors = []

    # Check required files exist
    for path in REQUIRED_FILES:
        if not os.path.exists(path):
            errors.append(f"Missing required file: {path}")

    # Compile all owned .py sources
    for path in collect_python_sources():
        try:
            with open(path, "rb") as f:
                source = f.read()
            compile(source, path, "exec")
        except SyntaxError as e:
            errors.append(f"SyntaxError in {path}: {e}")

    return errors


def main():
    print("=" * 60)
    print("Syntax check")
    print("=" * 60)
    errs = syntax_check()
    if errs:
        for e in errs:
            print("FAIL:", e)
        print()
    else:
        print("OK — no syntax errors")
    print()

    print("=" * 60)
    print("Unit tests")
    print("=" * 60)

    loader = unittest.TestLoader()
    suite = loader.discover(TESTS_DIR, pattern="test_*.py")

    # Guard against zero-test false green
    test_count = suite.countTestCases()
    if test_count == 0:
        print("FAIL: no tests discovered under", TESTS_DIR)
        sys.exit(1)

    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    if errs or not result.wasSuccessful():
        sys.exit(1)


if __name__ == "__main__":
    main()
