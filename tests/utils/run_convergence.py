#!/usr/bin/env python3
"""Simple test runner for convergence stability tests."""

import sys
import subprocess

def main():
    """Run convergence stability tests and report results."""
    print("=" * 80)
    print("Running Convergence Stability Tests")
    print("=" * 80)
    print()

    # Run pytest with verbose output
    result = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            "tests/test_convergence_stability.py",
            "-v",
            "--tb=short",
            "--color=yes"
        ],
        cwd="/Users/xinwan/Github/pvp_amm_challenge"
    )

    print()
    print("=" * 80)
    if result.returncode == 0:
        print("✓ All convergence stability tests passed!")
    else:
        print("✗ Some tests failed. Review output above.")
    print("=" * 80)

    return result.returncode

if __name__ == "__main__":
    sys.exit(main())
