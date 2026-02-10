#!/usr/bin/env python3
"""Demonstration of backward compatibility testing infrastructure.

This script demonstrates how to use the version comparison framework
to verify backward compatibility between old and new routers.

Run with:
    python tests/demo_backward_compatibility.py
"""

from decimal import Decimal

from amm_competition.market.retail import RetailOrder
from tests.fixtures.economic_fixtures import create_constant_fee_amm, get_pool_balance, PoolBalanceProfile
from tests.utils.version_comparison import (
    OldRouter,
    NewRouter,
    run_parallel_simulations,
    compare_routing_decisions,
)


def demo_split_comparison():
    """Demonstrate split comparison without execution."""
    print("=" * 70)
    print("DEMO: Split Comparison (No Execution)")
    print("=" * 70)

    # Create two AMMs with different fees
    reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)
    amms = [
        create_constant_fee_amm("LowFee", Decimal("0.002"), reserve_x, reserve_y),
        create_constant_fee_amm("HighFee", Decimal("0.004"), reserve_x, reserve_y),
    ]

    # Create buy order
    order = RetailOrder(side="buy", size=Decimal("1000"))
    fair_price = Decimal("1.0")

    # Compare routing decisions
    comparisons, all_match = compare_routing_decisions(order, amms, fair_price)

    print(f"\nOrder: {order.side} {order.size} Y")
    print(f"All splits match: {all_match}\n")

    for comp in comparisons:
        print(f"{comp.amm_name}:")
        print(f"  Old router: {comp.old_amount:>15} Y")
        print(f"  New router: {comp.new_amount:>15} Y")
        print(f"  Absolute diff: {comp.absolute_diff:>12}")
        print(f"  Relative diff: {comp.relative_diff_pct:>12.6f}%")
        print(f"  Matches: {comp.matches}")
        print()


def demo_execution_comparison():
    """Demonstrate full execution comparison."""
    print("=" * 70)
    print("DEMO: Full Execution Comparison")
    print("=" * 70)

    # Create two AMMs with different reserves
    amms = [
        create_constant_fee_amm("SmallPool", Decimal("0.003"), Decimal("5000"), Decimal("5000")),
        create_constant_fee_amm("LargePool", Decimal("0.003"), Decimal("20000"), Decimal("20000")),
    ]

    # Create sell order
    order = RetailOrder(side="sell", size=Decimal("1000"))
    fair_price = Decimal("1.0")

    # Run parallel simulations
    comparison = run_parallel_simulations(order, amms, fair_price)

    print(f"\nOrder: {order.side} {order.size} Y")
    print(f"Fair price: {fair_price}\n")

    print("Execution Prices:")
    print(f"  Old router: {comparison.old_execution_price}")
    print(f"  New router: {comparison.new_execution_price}")
    print(f"  Difference: {comparison.price_diff}")
    print(f"  Diff %: {comparison.price_diff_pct}%")
    print(f"  Prices match: {comparison.prices_match}\n")

    print("Total Amounts:")
    print(f"  Old X: {comparison.old_total_x:>15}")
    print(f"  New X: {comparison.new_total_x:>15}")
    print(f"  Old Y: {comparison.old_total_y:>15}")
    print(f"  New Y: {comparison.new_total_y:>15}\n")

    print("Split Comparisons:")
    for sc in comparison.split_comparisons:
        print(f"  {sc.amm_name}:")
        print(f"    Old: {sc.old_amount:>15} ({float(sc.old_amount/comparison.order_size*100):>6.2f}%)")
        print(f"    New: {sc.new_amount:>15} ({float(sc.new_amount/comparison.order_size*100):>6.2f}%)")
        print(f"    Diff: {sc.relative_diff_pct:>6.4f}%")
    print(f"\n  All splits match: {comparison.splits_match}\n")

    print("Final Reserve Differences:")
    for name, (x_diff, y_diff) in comparison.reserve_diffs.items():
        print(f"  {name}:")
        print(f"    X diff: {x_diff}")
        print(f"    Y diff: {y_diff}")
    print(f"\n  All reserves match: {comparison.reserves_match}\n")


def demo_router_wrappers():
    """Demonstrate direct router wrapper usage."""
    print("=" * 70)
    print("DEMO: Direct Router Wrapper Usage")
    print("=" * 70)

    # Create AMMs
    reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)
    amms = [
        create_constant_fee_amm("AMM1", Decimal("0.003"), reserve_x, reserve_y),
        create_constant_fee_amm("AMM2", Decimal("0.003"), reserve_x, reserve_y),
    ]

    # Create routers
    old_router = OldRouter()
    new_router = NewRouter()

    # Compute splits
    total_y = Decimal("1000")

    old_splits = old_router.compute_optimal_split_buy(amms, total_y)
    new_splits = new_router.compute_optimal_split_buy(amms, total_y)

    print(f"\nBuy order: {total_y} Y\n")

    print("Old Router Splits:")
    for amm, amount in old_splits:
        print(f"  {amm.name}: {amount} Y")

    print("\nNew Router Splits:")
    for amm, amount in new_splits:
        print(f"  {amm.name}: {amount} Y")

    print("\nDifferences:")
    for i, ((amm_old, amt_old), (amm_new, amt_new)) in enumerate(zip(old_splits, new_splits)):
        diff = amt_new - amt_old
        print(f"  {amm_old.name}: {diff} Y ({float(diff/amt_old*100):.6f}%)")


def demo_multiple_sizes():
    """Demonstrate testing across multiple trade sizes."""
    print("=" * 70)
    print("DEMO: Multiple Trade Sizes")
    print("=" * 70)

    # Create AMMs
    reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)
    amms = [
        create_constant_fee_amm("AMM1", Decimal("0.003"), reserve_x, reserve_y),
        create_constant_fee_amm("AMM2", Decimal("0.003"), reserve_x, reserve_y),
    ]

    fair_price = Decimal("1.0")

    # Test various sizes
    sizes = [
        Decimal("10"),      # Very small
        Decimal("100"),     # Small
        Decimal("1000"),    # Medium
        Decimal("5000"),    # Large
    ]

    print("\nTesting buy orders of various sizes:\n")
    print(f"{'Size':<12} {'Splits Match':<15} {'Prices Match':<15} {'Reserves Match'}")
    print("-" * 60)

    for size in sizes:
        order = RetailOrder(side="buy", size=size)

        # Use fresh AMM copies for each test
        test_amms = [
            create_constant_fee_amm("AMM1", Decimal("0.003"), reserve_x, reserve_y),
            create_constant_fee_amm("AMM2", Decimal("0.003"), reserve_x, reserve_y),
        ]

        comparison = run_parallel_simulations(order, test_amms, fair_price)

        print(f"{size:<12} {str(comparison.splits_match):<15} "
              f"{str(comparison.prices_match):<15} {str(comparison.reserves_match)}")


def main():
    """Run all demonstrations."""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "BACKWARD COMPATIBILITY DEMO" + " " * 26 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    try:
        demo_split_comparison()
        print("\n")

        demo_execution_comparison()
        print("\n")

        demo_router_wrappers()
        print("\n")

        demo_multiple_sizes()
        print("\n")

        print("=" * 70)
        print("All demonstrations completed successfully!")
        print("=" * 70)
        print()

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
