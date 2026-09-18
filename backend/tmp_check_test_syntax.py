"""Test file syntax check."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

test_files = [
    "tests/test_provider_base.py",
    "tests/test_providers.py",
    "tests/test_adapters.py",
    "tests/test_normalization.py",
    "tests/test_persistence.py",
    "tests/test_routes.py",
    "tests/test_api_football.py",
    "tests/test_integration.py",
    "tests/conftest.py",
    "tests/__init__.py",
]

errors = []
for f in test_files:
    try:
        with open(f, "r") as fh:
            compile(fh.read(), f, "exec")
        print(f"OK: {f}")
    except SyntaxError as e:
        print(f"FAIL: {f}: {e}")
        errors.append(f)

if errors:
    print(f"\n{len(errors)} test files have syntax errors")
    sys.exit(1)
else:
    print("\nAll test files OK")
