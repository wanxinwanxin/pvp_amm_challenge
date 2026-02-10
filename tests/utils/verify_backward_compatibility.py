#!/usr/bin/env python3
"""Verification script for backward compatibility testing infrastructure.

This script checks that all components are properly installed and working.
Run this to verify the infrastructure is ready for use.

Usage:
    python tests/verify_backward_compatibility.py
"""

import sys
from pathlib import Path


def check_file_exists(filepath: str, description: str) -> bool:
    """Check if a file exists and report status."""
    path = Path(filepath)
    exists = path.exists()
    status = "✅" if exists else "❌"
    print(f"{status} {description}: {filepath}")
    return exists


def check_import(module_name: str, description: str) -> bool:
    """Check if a module can be imported."""
    try:
        __import__(module_name)
        print(f"✅ {description}: {module_name}")
        return True
    except ImportError as e:
        print(f"❌ {description}: {module_name}")
        print(f"   Error: {e}")
        return False


def check_function_callable(module_name: str, function_name: str, description: str) -> bool:
    """Check if a function exists and is callable."""
    try:
        module = __import__(module_name, fromlist=[function_name])
        func = getattr(module, function_name)
        if callable(func):
            print(f"✅ {description}: {module_name}.{function_name}")
            return True
        else:
            print(f"❌ {description}: {module_name}.{function_name} (not callable)")
            return False
    except (ImportError, AttributeError) as e:
        print(f"❌ {description}: {module_name}.{function_name}")
        print(f"   Error: {e}")
        return False


def verify_infrastructure():
    """Verify all components of backward compatibility infrastructure."""
    print("=" * 70)
    print("BACKWARD COMPATIBILITY INFRASTRUCTURE VERIFICATION")
    print("=" * 70)
    print()

    all_checks_passed = True

    # Check files
    print("1. Checking Files...")
    print("-" * 70)
    files_to_check = [
        ("tests/utils/version_comparison.py", "Version comparison framework"),
        ("tests/utils/old_router.py", "Old router implementation"),
        ("tests/test_backward_compatibility.py", "Test suite"),
        ("tests/fixtures/economic_fixtures.py", "Economic fixtures"),
        ("tests/demo_backward_compatibility.py", "Demo script"),
        ("tests/BACKWARD_COMPATIBILITY.md", "Full documentation"),
        ("tests/BACKWARD_COMPATIBILITY_SUMMARY.md", "Quick reference"),
        ("tests/BACKWARD_COMPATIBILITY_STATUS.md", "Status report"),
    ]

    for filepath, description in files_to_check:
        if not check_file_exists(filepath, description):
            all_checks_passed = False

    print()

    # Check imports
    print("2. Checking Imports...")
    print("-" * 70)
    imports_to_check = [
        ("tests.utils.version_comparison", "Version comparison module"),
        ("tests.utils.old_router", "Old router module"),
        ("tests.fixtures.economic_fixtures", "Economic fixtures module"),
        ("amm_competition.market.router", "New router module"),
        ("amm_competition.market.retail", "Retail order module"),
        ("amm_competition.core.amm", "AMM core module"),
    ]

    for module_name, description in imports_to_check:
        if not check_import(module_name, description):
            all_checks_passed = False

    print()

    # Check key classes
    print("3. Checking Key Classes...")
    print("-" * 70)
    classes_to_check = [
        ("tests.utils.version_comparison", "OldRouter", "OldRouter class"),
        ("tests.utils.version_comparison", "NewRouter", "NewRouter class"),
        ("tests.utils.version_comparison", "SplitComparison", "SplitComparison class"),
        ("tests.utils.version_comparison", "ExecutionComparison", "ExecutionComparison class"),
    ]

    for module_name, class_name, description in classes_to_check:
        if not check_function_callable(module_name, class_name, description):
            all_checks_passed = False

    print()

    # Check key functions
    print("4. Checking Key Functions...")
    print("-" * 70)
    functions_to_check = [
        ("tests.utils.version_comparison", "compare_splits", "compare_splits function"),
        ("tests.utils.version_comparison", "run_parallel_simulations", "run_parallel_simulations function"),
        ("tests.utils.version_comparison", "compare_routing_decisions", "compare_routing_decisions function"),
        ("tests.fixtures.economic_fixtures", "create_constant_fee_amm", "create_constant_fee_amm function"),
        ("tests.fixtures.economic_fixtures", "create_tiered_fee_amm", "create_tiered_fee_amm function"),
        ("tests.fixtures.economic_fixtures", "snapshot_amm_state", "snapshot_amm_state function"),
        ("tests.fixtures.economic_fixtures", "calculate_pnl", "calculate_pnl function"),
    ]

    for module_name, function_name, description in functions_to_check:
        if not check_function_callable(module_name, function_name, description):
            all_checks_passed = False

    print()

    # Quick functional test
    print("5. Running Quick Functional Test...")
    print("-" * 70)
    try:
        from decimal import Decimal
        from tests.fixtures.economic_fixtures import create_constant_fee_amm
        from tests.utils.version_comparison import OldRouter, NewRouter

        # Create a simple AMM
        amm = create_constant_fee_amm(
            "TestAMM",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        # Create routers
        old_router = OldRouter()
        new_router = NewRouter()

        # Test split computation
        total_y = Decimal("1000")
        old_splits = old_router.compute_optimal_split_buy([amm], total_y)
        new_splits = new_router.compute_optimal_split_buy([amm], total_y)

        # Verify splits
        if len(old_splits) == 1 and len(new_splits) == 1:
            if old_splits[0][1] == new_splits[0][1] == total_y:
                print("✅ Functional test passed: Single AMM routing works correctly")
            else:
                print("❌ Functional test failed: Split amounts don't match")
                all_checks_passed = False
        else:
            print("❌ Functional test failed: Unexpected split count")
            all_checks_passed = False

    except Exception as e:
        print(f"❌ Functional test failed with error: {e}")
        import traceback
        traceback.print_exc()
        all_checks_passed = False

    print()

    # Summary
    print("=" * 70)
    if all_checks_passed:
        print("✅ ALL CHECKS PASSED")
        print()
        print("The backward compatibility testing infrastructure is ready for use.")
        print()
        print("Next steps:")
        print("  1. Run tests: pytest tests/test_backward_compatibility.py -v")
        print("  2. Run demo: python tests/demo_backward_compatibility.py")
        print("  3. Read docs: tests/BACKWARD_COMPATIBILITY.md")
        print()
        return 0
    else:
        print("❌ SOME CHECKS FAILED")
        print()
        print("Please fix the issues above before using the infrastructure.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(verify_infrastructure())
