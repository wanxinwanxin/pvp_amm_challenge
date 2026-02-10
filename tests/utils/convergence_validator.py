#!/usr/bin/env python3
"""Validation script to demonstrate convergence behavior.

This script runs example scenarios to show how the convergence
algorithm behaves in different situations. Useful for understanding
convergence characteristics without running full test suite.
"""

from decimal import Decimal
from amm_competition.market.router import OrderRouter
from tests.fixtures.economic_fixtures import (
    create_tiered_fee_amm,
    create_constant_fee_amm,
    get_baseline_fee_tiers,
)


class ConvergenceValidator:
    """Helper to validate and display convergence behavior."""

    def __init__(self):
        self.router = OrderRouter()
        self.results = []

    def test_scenario(self, name: str, amms: list, amount: Decimal, direction: str = "buy"):
        """Test a convergence scenario and record results."""
        print(f"\n{'='*70}")
        print(f"Scenario: {name}")
        print(f"{'='*70}")
        print(f"Amount: {amount} Y" if direction == "buy" else f"Amount: {amount} X")
        print(f"AMMs: {len(amms)}")

        import time
        start = time.time()

        try:
            if direction == "buy":
                splits = self.router.compute_optimal_split_buy(amms, amount)
            else:
                splits = self.router.compute_optimal_split_sell(amms, amount)

            elapsed = (time.time() - start) * 1000  # Convert to ms

            # Calculate metrics
            total = sum(split_amount for _, split_amount in splits)
            deviation = abs(total - amount) / amount if amount > 0 else Decimal("0")

            print(f"\n✅ Converged successfully")
            print(f"Time: {elapsed:.2f}ms")
            print(f"Total: {total}")
            print(f"Expected: {amount}")
            print(f"Deviation: {float(deviation)*100:.4f}%")

            print(f"\nSplits:")
            for i, (amm, split_amount) in enumerate(splits):
                ratio = float(split_amount / amount) * 100 if amount > 0 else 0
                print(f"  {amm.name}: {split_amount} ({ratio:.2f}%)")

            self.results.append({
                'name': name,
                'success': True,
                'time_ms': elapsed,
                'deviation_pct': float(deviation) * 100,
                'num_splits': len(splits)
            })

            return True

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            print(f"\n❌ Failed: {e}")
            print(f"Time: {elapsed:.2f}ms")

            self.results.append({
                'name': name,
                'success': False,
                'time_ms': elapsed,
                'error': str(e)
            })

            return False

    def print_summary(self):
        """Print summary of all tests."""
        print(f"\n{'='*70}")
        print("CONVERGENCE VALIDATION SUMMARY")
        print(f"{'='*70}")

        successful = sum(1 for r in self.results if r['success'])
        total = len(self.results)

        print(f"\nTests Run: {total}")
        print(f"Successful: {successful}")
        print(f"Failed: {total - successful}")

        if successful > 0:
            avg_time = sum(r['time_ms'] for r in self.results if r['success']) / successful
            max_time = max(r['time_ms'] for r in self.results if r['success'])
            avg_dev = sum(r['deviation_pct'] for r in self.results if r['success']) / successful

            print(f"\nPerformance:")
            print(f"  Average time: {avg_time:.2f}ms")
            print(f"  Max time: {max_time:.2f}ms")
            print(f"  Average deviation: {avg_dev:.4f}%")

        print(f"\nDetailed Results:")
        for r in self.results:
            status = "✅" if r['success'] else "❌"
            if r['success']:
                print(f"  {status} {r['name']}: {r['time_ms']:.2f}ms, "
                      f"dev={r['deviation_pct']:.4f}%")
            else:
                print(f"  {status} {r['name']}: {r.get('error', 'Unknown error')}")

        print(f"\n{'='*70}")
        if successful == total:
            print("🎉 All scenarios converged successfully!")
        else:
            print(f"⚠️  {total - successful} scenarios failed")
        print(f"{'='*70}\n")


def main():
    """Run convergence validation scenarios."""
    validator = ConvergenceValidator()

    # Scenario 1: Well-behaved conservative tiers
    print("\n🔵 WELL-BEHAVED SCENARIOS")
    conservative_tiers = get_baseline_fee_tiers("conservative")
    amms = [
        create_tiered_fee_amm("Conservative1", conservative_tiers,
                             Decimal("10000"), Decimal("10000")),
        create_tiered_fee_amm("Conservative2", conservative_tiers,
                             Decimal("10000"), Decimal("10000"))
    ]
    validator.test_scenario("Conservative Tiers (2-3 iterations expected)",
                           amms, Decimal("200"))

    # Scenario 2: Moderate tiers
    moderate_tiers = get_baseline_fee_tiers("moderate")
    amms = [
        create_tiered_fee_amm("Moderate1", moderate_tiers,
                             Decimal("10000"), Decimal("10000")),
        create_tiered_fee_amm("Moderate2", moderate_tiers,
                             Decimal("10000"), Decimal("10000"))
    ]
    validator.test_scenario("Moderate Tiers (2-3 iterations expected)",
                           amms, Decimal("500"))

    # Scenario 3: Pathological tiers
    print("\n🔴 PATHOLOGICAL SCENARIOS")
    pathological_tiers = get_baseline_fee_tiers("pathological")
    amms = [
        create_tiered_fee_amm("Pathological1", pathological_tiers,
                             Decimal("10000"), Decimal("10000")),
        create_tiered_fee_amm("Pathological2", pathological_tiers,
                             Decimal("10000"), Decimal("10000"))
    ]
    validator.test_scenario("Pathological Tiers (steep: 100%→1bp→0.1bp)",
                           amms, Decimal("100"))

    # Scenario 4: Extreme trade size - tiny
    print("\n🔸 EXTREME TRADE SIZES")
    amms = [
        create_tiered_fee_amm("A", conservative_tiers,
                             Decimal("10000"), Decimal("10000")),
        create_tiered_fee_amm("B", conservative_tiers,
                             Decimal("10000"), Decimal("10000"))
    ]
    validator.test_scenario("Tiny Trade (0.001)",
                           amms, Decimal("0.001"))

    # Scenario 5: Extreme trade size - huge
    amms = [
        create_tiered_fee_amm("A", conservative_tiers,
                             Decimal("100000"), Decimal("100000")),
        create_tiered_fee_amm("B", conservative_tiers,
                             Decimal("100000"), Decimal("100000"))
    ]
    validator.test_scenario("Huge Trade (100,000)",
                           amms, Decimal("100000"))

    # Scenario 6: Identical AMMs
    print("\n🟢 IDENTICAL AMM SCENARIOS")
    amms = [
        create_tiered_fee_amm("Identical1", conservative_tiers,
                             Decimal("10000"), Decimal("10000")),
        create_tiered_fee_amm("Identical2", conservative_tiers,
                             Decimal("10000"), Decimal("10000"))
    ]
    validator.test_scenario("Identical AMMs (should split equally)",
                           amms, Decimal("400"))

    # Scenario 7: Asymmetric pools
    print("\n🟡 ASYMMETRIC SCENARIOS")
    amms = [
        create_tiered_fee_amm("Large", conservative_tiers,
                             Decimal("20000"), Decimal("20000")),
        create_tiered_fee_amm("Small", conservative_tiers,
                             Decimal("5000"), Decimal("5000"))
    ]
    validator.test_scenario("Asymmetric Pools (large vs small)",
                           amms, Decimal("400"))

    # Scenario 8: Multiple AMMs (5)
    print("\n🟣 MULTIPLE AMM SCENARIOS")
    amms = [
        create_tiered_fee_amm(f"AMM{i}", conservative_tiers,
                             Decimal("10000"), Decimal("10000"))
        for i in range(5)
    ]
    validator.test_scenario("Five AMMs (pairwise approximation)",
                           amms, Decimal("1000"))

    # Scenario 9: Sell direction
    print("\n🟤 SELL DIRECTION SCENARIOS")
    amms = [
        create_tiered_fee_amm("Sell1", conservative_tiers,
                             Decimal("10000"), Decimal("10000")),
        create_tiered_fee_amm("Sell2", conservative_tiers,
                             Decimal("10000"), Decimal("10000"))
    ]
    validator.test_scenario("Sell Direction (conservative tiers)",
                           amms, Decimal("100"), direction="sell")

    # Scenario 10: Mixed fee structures
    print("\n🟠 MIXED FEE STRUCTURE SCENARIOS")
    amms = [
        create_constant_fee_amm("Constant", Decimal("0.003"),
                               Decimal("10000"), Decimal("10000")),
        create_tiered_fee_amm("Tiered", conservative_tiers,
                             Decimal("10000"), Decimal("10000"))
    ]
    validator.test_scenario("Mixed (constant + tiered)",
                           amms, Decimal("300"))

    # Scenario 11: Tier boundary
    print("\n⚫ BOUNDARY SCENARIOS")
    two_tier = [
        (Decimal("0"), Decimal("0.003")),
        (Decimal("100"), Decimal("0.002"))
    ]
    amms = [
        create_tiered_fee_amm("A", two_tier,
                             Decimal("10000"), Decimal("10000")),
        create_tiered_fee_amm("B", two_tier,
                             Decimal("10000"), Decimal("10000"))
    ]
    validator.test_scenario("Trade at Tier Boundary (100)",
                           amms, Decimal("100"))

    # Print summary
    validator.print_summary()

    # Return exit code
    failed = sum(1 for r in validator.results if not r['success'])
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
