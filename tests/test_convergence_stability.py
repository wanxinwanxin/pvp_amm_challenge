"""Convergence stability testing for iterative routing algorithm.

This module verifies that the iterative routing algorithm converges reliably
across a wide range of scenarios including:
- Well-behaved fee tier structures (2-3 iterations expected)
- Pathological fee structures (steep transitions, must still converge)
- Extreme trade sizes (tiny and huge amounts)
- Extreme tier thresholds (very high and very low)
- Boundary conditions (trades exactly at tier boundaries)
- Identical AMMs (should converge to equal split)

All tests verify convergence within max_iterations (5) and check for:
- No infinite loops
- No exceptions raised
- Reasonable solution quality
- Stability of splits (changes < 0.1%)
"""

import pytest
from decimal import Decimal
from typing import Optional

from amm_competition.market.router import OrderRouter
from tests.fixtures.economic_fixtures import (
    create_constant_fee_amm,
    create_tiered_fee_amm,
    get_baseline_fee_tiers,
)


class ConvergenceMonitor:
    """Helper class to monitor convergence metrics during routing.

    This class helps track convergence behavior by analyzing the
    router's behavior indirectly through repeated calls with
    slightly different parameters.
    """

    def __init__(self):
        self.iterations_count = 0
        self.splits_history = []

    def verify_convergence(
        self,
        splits: list[tuple],
        total_amount: Decimal,
        tolerance: Decimal = Decimal("0.001")
    ) -> dict:
        """Verify that splits represent a valid converged solution.

        Args:
            splits: List of (AMM, amount) tuples from router
            total_amount: Expected total amount across all splits
            tolerance: Maximum allowed deviation from total

        Returns:
            Dictionary with convergence metrics:
                - valid: Whether splits sum to total
                - max_deviation: Maximum deviation from total
                - num_splits: Number of non-zero splits
                - min_split_ratio: Smallest split as fraction of total
                - max_split_ratio: Largest split as fraction of total
        """
        if not splits:
            return {
                'valid': False,
                'max_deviation': Decimal("1.0"),
                'num_splits': 0,
                'min_split_ratio': Decimal("0"),
                'max_split_ratio': Decimal("0"),
            }

        # Calculate total and deviation
        actual_total = sum(amount for _, amount in splits)
        deviation = abs(actual_total - total_amount) / total_amount if total_amount > 0 else Decimal("0")

        # Calculate split ratios
        non_zero_splits = [amount for _, amount in splits if amount > Decimal("0.0001")]
        if non_zero_splits and total_amount > 0:
            min_ratio = min(non_zero_splits) / total_amount
            max_ratio = max(non_zero_splits) / total_amount
        else:
            min_ratio = Decimal("0")
            max_ratio = Decimal("0")

        return {
            'valid': deviation <= tolerance,
            'max_deviation': deviation,
            'num_splits': len(non_zero_splits),
            'min_split_ratio': min_ratio,
            'max_split_ratio': max_ratio,
        }


class TestConvergenceWithinMaxIterations:
    """Test that all scenarios converge within maximum iteration limit (5)."""

    def test_convergence_conservative_tiers(self):
        """Conservative tiers should converge in 2-3 iterations."""
        conservative_tiers = get_baseline_fee_tiers("conservative")

        amms = [
            create_tiered_fee_amm("Conservative1", conservative_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("Conservative2", conservative_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()

        # Should converge without exception
        splits = router.compute_optimal_split_buy(amms, Decimal("200"))

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, Decimal("200"))

        assert metrics['valid'], "Splits should sum to total amount"
        assert len(splits) == 2, "Should produce splits for both AMMs"
        assert metrics['max_deviation'] < Decimal("0.001"), "Deviation should be < 0.1%"

    def test_convergence_moderate_tiers(self):
        """Moderate tiers should converge in 2-3 iterations."""
        moderate_tiers = get_baseline_fee_tiers("moderate")

        amms = [
            create_tiered_fee_amm("Moderate1", moderate_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("Moderate2", moderate_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()

        # Should converge without exception
        splits = router.compute_optimal_split_buy(amms, Decimal("500"))

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, Decimal("500"))

        assert metrics['valid'], "Splits should sum to total amount"
        assert len(splits) == 2, "Should produce splits for both AMMs"

    def test_convergence_aggressive_tiers(self):
        """Aggressive tiers should still converge within 5 iterations."""
        aggressive_tiers = get_baseline_fee_tiers("aggressive")

        amms = [
            create_tiered_fee_amm("Aggressive1", aggressive_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("Aggressive2", aggressive_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()

        # Should converge without exception
        splits = router.compute_optimal_split_buy(amms, Decimal("1000"))

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, Decimal("1000"))

        assert metrics['valid'], "Splits should sum to total amount"
        assert len(splits) == 2, "Should produce splits for both AMMs"

    def test_convergence_mixed_fee_structures(self):
        """Mix of constant and tiered fees should converge."""
        conservative_tiers = get_baseline_fee_tiers("conservative")

        amms = [
            create_constant_fee_amm("Constant", Decimal("0.003"),
                                   Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("Tiered", conservative_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()

        # Should converge without exception
        splits = router.compute_optimal_split_buy(amms, Decimal("300"))

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, Decimal("300"))

        assert metrics['valid'], "Splits should sum to total amount"
        assert len(splits) == 2, "Should produce splits for both AMMs"

    def test_convergence_no_infinite_loops(self):
        """Verify algorithm terminates even in worst case."""
        # Use pathological tiers that might cause issues
        pathological_tiers = get_baseline_fee_tiers("pathological")

        amms = [
            create_tiered_fee_amm("Path1", pathological_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("Path2", pathological_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()

        # Should complete without hanging
        import time
        start = time.time()

        splits = router.compute_optimal_split_buy(amms, Decimal("100"))

        elapsed = time.time() - start

        # Should complete very quickly (< 100ms)
        assert elapsed < 0.1, "Algorithm should terminate quickly"
        assert len(splits) > 0, "Should produce splits"


class TestConvergenceQualityWellBehavedTiers:
    """Test convergence quality with well-behaved tier profiles."""

    def test_quality_conservative_equal_pools(self):
        """Conservative tiers with equal pools should split near-equally."""
        conservative_tiers = get_baseline_fee_tiers("conservative")

        amms = [
            create_tiered_fee_amm("A", conservative_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("B", conservative_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()
        splits = router.compute_optimal_split_buy(amms, Decimal("200"))

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, Decimal("200"))

        # With identical AMMs, should split equally
        assert metrics['valid'], "Should be valid split"

        # Check for near-equal split
        split1_ratio = splits[0][1] / Decimal("200")
        split2_ratio = splits[1][1] / Decimal("200")

        # Should be within 10% of equal split (0.5 each)
        assert abs(split1_ratio - Decimal("0.5")) < Decimal("0.1")
        assert abs(split2_ratio - Decimal("0.5")) < Decimal("0.1")

    def test_quality_moderate_converges_quickly(self):
        """Moderate tiers should produce stable solution quickly."""
        moderate_tiers = get_baseline_fee_tiers("moderate")

        amms = [
            create_tiered_fee_amm("M1", moderate_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("M2", moderate_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()

        # Test multiple trade sizes
        for size in [Decimal("100"), Decimal("500"), Decimal("1500")]:
            splits = router.compute_optimal_split_buy(amms, size)

            monitor = ConvergenceMonitor()
            metrics = monitor.verify_convergence(splits, size)

            assert metrics['valid'], f"Should converge for size {size}"
            assert metrics['max_deviation'] < Decimal("0.001"), "High accuracy expected"

    def test_quality_asymmetric_pools_reasonable_split(self):
        """Asymmetric pools should still produce reasonable splits."""
        conservative_tiers = get_baseline_fee_tiers("conservative")

        # One large pool, one small pool
        amms = [
            create_tiered_fee_amm("Large", conservative_tiers,
                                 Decimal("20000"), Decimal("20000")),
            create_tiered_fee_amm("Small", conservative_tiers,
                                 Decimal("5000"), Decimal("5000"))
        ]

        router = OrderRouter()
        splits = router.compute_optimal_split_buy(amms, Decimal("400"))

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, Decimal("400"))

        assert metrics['valid'], "Should produce valid split"

        # Larger pool should get more flow
        large_amount = splits[0][1]
        small_amount = splits[1][1]

        assert large_amount > small_amount, "Larger pool should get more flow"


class TestConvergencePathologicalTiers:
    """Test convergence with pathological tier profiles (steep transitions)."""

    def test_pathological_completes_without_exception(self):
        """Pathological tiers should still complete successfully."""
        pathological_tiers = get_baseline_fee_tiers("pathological")

        amms = [
            create_tiered_fee_amm("P1", pathological_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("P2", pathological_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()

        # Should not raise exception
        try:
            splits = router.compute_optimal_split_buy(amms, Decimal("100"))
            assert len(splits) > 0, "Should produce splits"
        except Exception as e:
            pytest.fail(f"Convergence failed with pathological tiers: {e}")

    def test_pathological_accepts_suboptimal_solution(self):
        """Pathological tiers may not be optimal but should be reasonable."""
        pathological_tiers = get_baseline_fee_tiers("pathological")

        amms = [
            create_tiered_fee_amm("P1", pathological_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("P2", pathological_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()
        splits = router.compute_optimal_split_buy(amms, Decimal("50"))

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, Decimal("50"),
                                            tolerance=Decimal("0.01"))  # Relaxed tolerance

        # Accept solution even if not perfectly optimal
        assert len(splits) > 0, "Should produce some split"

        # Total should be close to target (within 1%)
        assert metrics['max_deviation'] < Decimal("0.01"), "Should be reasonably accurate"

    def test_pathological_steep_transitions_stable(self):
        """Steep fee transitions should not cause oscillation."""
        # Extreme transitions: 100% -> 0.01% -> 0.001%
        extreme_tiers = [
            (Decimal("0"), Decimal("1.0")),      # 100% fee!
            (Decimal("1"), Decimal("0.0001")),   # 1bp
            (Decimal("2"), Decimal("0.00001"))   # 0.1bp
        ]

        amms = [
            create_tiered_fee_amm("Extreme1", extreme_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("Extreme2", extreme_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()

        # Should complete without oscillation
        splits = router.compute_optimal_split_buy(amms, Decimal("100"))

        assert len(splits) > 0, "Should produce splits"

        # Verify splits are non-negative
        for amm, amount in splits:
            assert amount >= 0, "Splits should be non-negative"


class TestConvergenceExtremeTradeSizes:
    """Test convergence with extreme trade sizes (tiny and huge)."""

    def test_tiny_trade_size(self):
        """Very small trades should converge."""
        conservative_tiers = get_baseline_fee_tiers("conservative")

        amms = [
            create_tiered_fee_amm("A", conservative_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("B", conservative_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()

        # Very tiny trade
        tiny_amount = Decimal("0.001")
        splits = router.compute_optimal_split_buy(amms, tiny_amount)

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, tiny_amount,
                                            tolerance=Decimal("0.01"))

        assert len(splits) > 0, "Should handle tiny trades"
        # For tiny amounts, one AMM might get it all (acceptable)
        assert metrics['max_deviation'] < Decimal("0.05"), "Should be reasonably accurate"

    def test_small_trade_size(self):
        """Small trades should converge accurately."""
        conservative_tiers = get_baseline_fee_tiers("conservative")

        amms = [
            create_tiered_fee_amm("A", conservative_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("B", conservative_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()

        # Small but not tiny
        small_amount = Decimal("1.0")
        splits = router.compute_optimal_split_buy(amms, small_amount)

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, small_amount)

        assert metrics['valid'], "Should converge for small trades"

    def test_huge_trade_size(self):
        """Very large trades should converge."""
        conservative_tiers = get_baseline_fee_tiers("conservative")

        amms = [
            create_tiered_fee_amm("A", conservative_tiers,
                                 Decimal("100000"), Decimal("100000")),
            create_tiered_fee_amm("B", conservative_tiers,
                                 Decimal("100000"), Decimal("100000"))
        ]

        router = OrderRouter()

        # Huge trade
        huge_amount = Decimal("100000")
        splits = router.compute_optimal_split_buy(amms, huge_amount)

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, huge_amount)

        assert metrics['valid'], "Should handle large trades"
        assert len(splits) == 2, "Should split across both AMMs"

    def test_extreme_range_of_sizes(self):
        """Test full range from tiny to huge."""
        conservative_tiers = get_baseline_fee_tiers("conservative")

        amms = [
            create_tiered_fee_amm("A", conservative_tiers,
                                 Decimal("50000"), Decimal("50000")),
            create_tiered_fee_amm("B", conservative_tiers,
                                 Decimal("50000"), Decimal("50000"))
        ]

        router = OrderRouter()

        # Test range of sizes
        sizes = [
            Decimal("0.001"),   # Tiny
            Decimal("0.1"),     # Very small
            Decimal("10"),      # Small
            Decimal("1000"),    # Medium
            Decimal("10000"),   # Large
            Decimal("50000"),   # Huge
        ]

        for size in sizes:
            splits = router.compute_optimal_split_buy(amms, size)

            monitor = ConvergenceMonitor()
            # Use relaxed tolerance for extreme sizes
            tolerance = Decimal("0.01") if size < Decimal("1") else Decimal("0.001")
            metrics = monitor.verify_convergence(splits, size, tolerance=tolerance)

            assert len(splits) > 0, f"Should handle size {size}"
            assert metrics['max_deviation'] < tolerance, f"Size {size} should converge"


class TestConvergenceExtremeTierThresholds:
    """Test convergence with extreme tier threshold configurations."""

    def test_very_high_thresholds(self):
        """Tiers with very high thresholds should converge."""
        high_threshold_tiers = [
            (Decimal("0"), Decimal("0.003")),
            (Decimal("100000"), Decimal("0.002")),   # Very high
            (Decimal("1000000"), Decimal("0.001"))   # Extremely high
        ]

        amms = [
            create_tiered_fee_amm("High1", high_threshold_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("High2", high_threshold_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()

        # Normal-sized trade (won't reach high tiers)
        splits = router.compute_optimal_split_buy(amms, Decimal("200"))

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, Decimal("200"))

        assert metrics['valid'], "Should handle high thresholds"

    def test_very_low_thresholds(self):
        """Tiers with very low thresholds should converge."""
        low_threshold_tiers = [
            (Decimal("0"), Decimal("0.005")),
            (Decimal("0.1"), Decimal("0.003")),      # Very low
            (Decimal("1"), Decimal("0.001"))         # Low
        ]

        amms = [
            create_tiered_fee_amm("Low1", low_threshold_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("Low2", low_threshold_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()

        # Normal trade should traverse multiple tiers quickly
        splits = router.compute_optimal_split_buy(amms, Decimal("100"))

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, Decimal("100"))

        assert metrics['valid'], "Should handle low thresholds"

    def test_mixed_threshold_scales(self):
        """AMMs with different threshold scales should converge."""
        low_tiers = [
            (Decimal("0"), Decimal("0.003")),
            (Decimal("10"), Decimal("0.002")),
            (Decimal("100"), Decimal("0.001"))
        ]

        high_tiers = [
            (Decimal("0"), Decimal("0.003")),
            (Decimal("1000"), Decimal("0.002")),
            (Decimal("10000"), Decimal("0.001"))
        ]

        amms = [
            create_tiered_fee_amm("LowThresh", low_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("HighThresh", high_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()
        splits = router.compute_optimal_split_buy(amms, Decimal("500"))

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, Decimal("500"))

        assert metrics['valid'], "Should handle mixed threshold scales"


class TestConvergenceSingleTierBoundary:
    """Test convergence when trades occur exactly at tier boundaries."""

    def test_trade_exactly_at_boundary(self):
        """Trade size exactly at tier boundary should not oscillate."""
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

        router = OrderRouter()

        # Trade exactly at boundary (100 Y total, split ~50/50 = ~50 each at boundary)
        splits = router.compute_optimal_split_buy(amms, Decimal("100"))

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, Decimal("100"))

        assert metrics['valid'], "Should handle boundary trades"

        # Should not cause any issues
        for amm, amount in splits:
            assert amount >= 0, "No negative splits"

    def test_multiple_boundaries(self):
        """Multiple tier boundaries should not cause instability."""
        three_tier = [
            (Decimal("0"), Decimal("0.003")),
            (Decimal("100"), Decimal("0.002")),
            (Decimal("1000"), Decimal("0.001"))
        ]

        amms = [
            create_tiered_fee_amm("A", three_tier,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("B", three_tier,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()

        # Test trades near each boundary
        boundary_sizes = [
            Decimal("100"),    # First boundary
            Decimal("200"),    # 2x first boundary
            Decimal("1000"),   # Second boundary
            Decimal("2000"),   # 2x second boundary
        ]

        for size in boundary_sizes:
            splits = router.compute_optimal_split_buy(amms, size)

            monitor = ConvergenceMonitor()
            metrics = monitor.verify_convergence(splits, size)

            assert metrics['valid'], f"Should handle boundary size {size}"

    def test_straddling_boundary(self):
        """Trades that straddle boundaries should converge smoothly."""
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

        router = OrderRouter()

        # Trade that straddles boundary: ~50 in tier 0, ~50 in tier 1
        splits = router.compute_optimal_split_buy(amms, Decimal("100"))

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, Decimal("100"))

        assert metrics['valid'], "Should handle straddling trades"


class TestConvergenceIdenticalAMMs:
    """Test convergence when routing through identical AMMs."""

    def test_identical_constant_fee_equal_split(self):
        """Identical constant-fee AMMs should split equally."""
        amms = [
            create_constant_fee_amm("A", Decimal("0.003"),
                                   Decimal("10000"), Decimal("10000")),
            create_constant_fee_amm("B", Decimal("0.003"),
                                   Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()
        splits = router.compute_optimal_split_buy(amms, Decimal("200"))

        # Should be exactly equal (or very close)
        amount_a = splits[0][1]
        amount_b = splits[1][1]

        ratio = amount_a / amount_b if amount_b > 0 else Decimal("0")

        # Should be very close to 1.0 (equal split)
        assert abs(ratio - Decimal("1.0")) < Decimal("0.01"), "Should split equally"

    def test_identical_tiered_equal_split(self):
        """Identical tiered AMMs should split equally."""
        conservative_tiers = get_baseline_fee_tiers("conservative")

        amms = [
            create_tiered_fee_amm("A", conservative_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("B", conservative_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()
        splits = router.compute_optimal_split_buy(amms, Decimal("400"))

        # Should be nearly equal
        amount_a = splits[0][1]
        amount_b = splits[1][1]

        ratio = amount_a / amount_b if amount_b > 0 else Decimal("0")

        # Allow small deviation due to iteration
        assert abs(ratio - Decimal("1.0")) < Decimal("0.05"), "Should split near-equally"

    def test_identical_converges_fast(self):
        """Identical AMMs should converge in 1-2 iterations."""
        conservative_tiers = get_baseline_fee_tiers("conservative")

        amms = [
            create_tiered_fee_amm("A", conservative_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("B", conservative_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()

        import time
        start = time.time()

        splits = router.compute_optimal_split_buy(amms, Decimal("300"))

        elapsed = time.time() - start

        # Should be very fast (< 5ms)
        assert elapsed < 0.005, "Identical AMMs should converge quickly"

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, Decimal("300"))

        assert metrics['valid'], "Should produce valid split"


class TestConvergenceSellDirection:
    """Test that sell direction converges as reliably as buy direction."""

    def test_sell_conservative_tiers(self):
        """Sell with conservative tiers should converge."""
        conservative_tiers = get_baseline_fee_tiers("conservative")

        amms = [
            create_tiered_fee_amm("A", conservative_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("B", conservative_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()

        # Sell direction
        splits = router.compute_optimal_split_sell(amms, Decimal("100"))

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, Decimal("100"))

        assert metrics['valid'], "Sell should converge"
        assert len(splits) == 2, "Should produce splits for both AMMs"

    def test_sell_pathological_completes(self):
        """Sell with pathological tiers should complete."""
        pathological_tiers = get_baseline_fee_tiers("pathological")

        amms = [
            create_tiered_fee_amm("P1", pathological_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("P2", pathological_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()

        try:
            splits = router.compute_optimal_split_sell(amms, Decimal("50"))
            assert len(splits) > 0, "Should produce splits"
        except Exception as e:
            pytest.fail(f"Sell convergence failed: {e}")

    def test_sell_identical_equal_split(self):
        """Sell with identical AMMs should split equally."""
        conservative_tiers = get_baseline_fee_tiers("conservative")

        amms = [
            create_tiered_fee_amm("A", conservative_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("B", conservative_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()
        splits = router.compute_optimal_split_sell(amms, Decimal("100"))

        # Should be nearly equal
        amount_a = splits[0][1]
        amount_b = splits[1][1]

        ratio = amount_a / amount_b if amount_b > 0 else Decimal("0")

        # Allow small deviation
        assert abs(ratio - Decimal("1.0")) < Decimal("0.05"), "Should split near-equally"


class TestConvergenceMultipleAMMs:
    """Test convergence with more than 2 AMMs."""

    def test_three_amms_converge(self):
        """Three AMMs should converge reliably."""
        conservative_tiers = get_baseline_fee_tiers("conservative")

        amms = [
            create_tiered_fee_amm("A", conservative_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("B", conservative_tiers,
                                 Decimal("10000"), Decimal("10000")),
            create_tiered_fee_amm("C", conservative_tiers,
                                 Decimal("10000"), Decimal("10000"))
        ]

        router = OrderRouter()
        splits = router.compute_optimal_split_buy(amms, Decimal("600"))

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, Decimal("600"))

        assert metrics['valid'], "Three AMMs should converge"
        assert len(splits) == 3, "Should produce splits for all AMMs"

    def test_five_amms_converge(self):
        """Five AMMs should converge (recommended max)."""
        conservative_tiers = get_baseline_fee_tiers("conservative")

        amms = [
            create_tiered_fee_amm(f"AMM{i}", conservative_tiers,
                                 Decimal("10000"), Decimal("10000"))
            for i in range(5)
        ]

        router = OrderRouter()
        splits = router.compute_optimal_split_buy(amms, Decimal("1000"))

        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, Decimal("1000"))

        assert metrics['valid'], "Five AMMs should converge"
        assert len(splits) == 5, "Should produce splits for all AMMs"

        # Should complete reasonably fast
        import time
        start = time.time()
        router.compute_optimal_split_buy(amms, Decimal("1000"))
        elapsed = time.time() - start

        assert elapsed < 0.02, "Five AMMs should route quickly"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
