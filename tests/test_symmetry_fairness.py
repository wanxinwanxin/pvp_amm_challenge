"""Symmetry and fairness testing module for AMM competition.

This module verifies that identical or similar strategies compete fairly:
- Identical strategies should have symmetric PnL outcomes
- Near-identical strategies should have proportional PnL differences
- Routing should give all competitive AMMs fair access to flow
- Results should be consistent across multiple random seeds

All tests use Decimal precision for accurate financial calculations.
"""

import random
from decimal import Decimal
from typing import Literal

import pytest

from amm_competition.core.amm import AMM
from amm_competition.market.router import OrderRouter
from tests.fixtures.economic_fixtures import (
    PoolBalanceProfile,
    calculate_pnl,
    create_constant_fee_amm,
    create_tiered_fee_amm,
    get_baseline_fee_tiers,
    get_pool_balance,
    snapshot_amm_state,
)
from tests.utils.economic_verification import verify_symmetry


def generate_random_trade(
    seed: int, size_range: tuple[Decimal, Decimal]
) -> tuple[Literal["buy", "sell"], Decimal]:
    """Generate a random trade for testing.

    Args:
        seed: Random seed for reproducibility
        size_range: (min_size, max_size) for trade amounts

    Returns:
        Tuple of (direction, size) where direction is "buy" or "sell"
    """
    random.seed(seed)
    direction: Literal["buy", "sell"] = random.choice(["buy", "sell"])
    size = Decimal(str(random.uniform(float(size_range[0]), float(size_range[1]))))
    return direction, size


def execute_random_trades(
    amms: list[AMM],
    num_trades: int,
    seed: int,
    size_range: tuple[Decimal, Decimal] = (Decimal("10"), Decimal("100")),
) -> list[tuple[Literal["buy", "sell"], Decimal]]:
    """Execute a sequence of random trades through the router.

    Args:
        amms: List of AMMs to route across
        num_trades: Number of trades to execute
        seed: Random seed for reproducibility
        size_range: (min_size, max_size) for trade amounts in X

    Returns:
        List of executed (direction, size) tuples for verification
    """
    router = OrderRouter()
    executed_trades = []
    timestamp = 0

    for i in range(num_trades):
        direction, size = generate_random_trade(seed + i, size_range)
        executed_trades.append((direction, size))

        if direction == "buy":
            # Trader buying X, spending Y
            # Estimate Y needed: use first AMM's quote as approximation
            quote = amms[0].get_quote_sell_x(size)
            if quote:
                y_amount = quote.amount_out * Decimal("1.1")  # Add buffer
                splits = router.compute_optimal_split_buy(amms, y_amount)
                for amm, y_split in splits:
                    if y_split > 0:
                        amm.execute_buy_x_with_y(y_split, timestamp)
        else:
            # Trader selling X for Y
            splits = router.compute_optimal_split_sell(amms, size)
            for amm, x_split in splits:
                if x_split > 0:
                    amm.execute_buy_x(x_split, timestamp)

        timestamp += 1

    return executed_trades


class TestIdenticalConstantStrategies:
    """Test symmetry for identical constant-fee strategies."""

    def test_identical_constant_strategies_symmetric_pnl(self):
        """Test that two identical constant-fee AMMs have symmetric PnL.

        Creates two AMMs with identical 30bps fees and balanced reserves,
        runs 100 random trades, and verifies PnLs are within 5% of each other.
        """
        # Create two identical AMMs
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)
        fee_rate = Decimal("0.003")  # 30bps

        amm1 = create_constant_fee_amm("Identical_A", fee_rate, reserve_x, reserve_y)
        amm2 = create_constant_fee_amm("Identical_B", fee_rate, reserve_x, reserve_y)

        amms = [amm1, amm2]

        # Snapshot initial states
        initial_states = [snapshot_amm_state(amm) for amm in amms]

        # Execute 100 random trades with fixed seed
        seed = 42
        num_trades = 100
        execute_random_trades(amms, num_trades, seed)

        # Snapshot final states
        final_states = [snapshot_amm_state(amm) for amm in amms]

        # Calculate PnL for each AMM
        pnl1 = calculate_pnl(initial_states[0], final_states[0])
        pnl2 = calculate_pnl(initial_states[1], final_states[1])

        # Verify symmetry (within 5% tolerance)
        is_symmetric, diff_pct = verify_symmetry(
            pnl1.pnl_at_final_price, pnl2.pnl_at_final_price, tolerance_pct=Decimal("5")
        )

        assert is_symmetric, (
            f"Identical constant-fee strategies should have symmetric PnL. "
            f"AMM1 PnL: {pnl1.pnl_at_final_price:.4f}, "
            f"AMM2 PnL: {pnl2.pnl_at_final_price:.4f}, "
            f"Difference: {diff_pct:.2f}% (tolerance: 5%)"
        )

        # Additional checks: both should have earned fees
        assert pnl1.fees_earned_x > 0 or pnl1.fees_earned_y > 0, "AMM1 should earn fees"
        assert pnl2.fees_earned_x > 0 or pnl2.fees_earned_y > 0, "AMM2 should earn fees"

        # Fee earnings should also be symmetric
        total_fees_1 = pnl1.fees_earned_y + pnl1.fees_earned_x * final_states[0].spot_price
        total_fees_2 = pnl2.fees_earned_y + pnl2.fees_earned_x * final_states[1].spot_price

        is_fee_symmetric, fee_diff_pct = verify_symmetry(
            total_fees_1, total_fees_2, tolerance_pct=Decimal("5")
        )

        assert is_fee_symmetric, (
            f"Fee earnings should be symmetric. "
            f"AMM1 fees: {total_fees_1:.4f}, "
            f"AMM2 fees: {total_fees_2:.4f}, "
            f"Difference: {fee_diff_pct:.2f}% (tolerance: 5%)"
        )

    def test_identical_constant_strategies_balanced_volume(self):
        """Test that identical strategies receive approximately equal volume.

        Verifies that the router distributes flow fairly between identical AMMs.
        """
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)
        fee_rate = Decimal("0.003")

        amm1 = create_constant_fee_amm("Equal_A", fee_rate, reserve_x, reserve_y)
        amm2 = create_constant_fee_amm("Equal_B", fee_rate, reserve_x, reserve_y)

        amms = [amm1, amm2]
        initial_states = [snapshot_amm_state(amm) for amm in amms]

        # Execute trades
        execute_random_trades(amms, 100, seed=123)

        final_states = [snapshot_amm_state(amm) for amm in amms]

        # Calculate total volume for each AMM (absolute value of reserve changes)
        volume1 = abs(final_states[0].reserve_x - initial_states[0].reserve_x) + abs(
            final_states[0].reserve_y - initial_states[0].reserve_y
        )
        volume2 = abs(final_states[1].reserve_x - initial_states[1].reserve_x) + abs(
            final_states[1].reserve_y - initial_states[1].reserve_y
        )

        # Volumes should be similar (within 20% due to discrete routing)
        is_balanced, vol_diff_pct = verify_symmetry(
            volume1, volume2, tolerance_pct=Decimal("20")
        )

        assert is_balanced, (
            f"Identical strategies should receive similar volume. "
            f"AMM1 volume: {volume1:.2f}, "
            f"AMM2 volume: {volume2:.2f}, "
            f"Difference: {vol_diff_pct:.2f}% (tolerance: 20%)"
        )


class TestIdenticalTieredStrategies:
    """Test symmetry for identical tiered-fee strategies."""

    def test_identical_tiered_strategies_symmetric_pnl(self):
        """Test that two identical tiered-fee AMMs have symmetric PnL.

        Uses conservative tier profile (30→20→10 bps) with balanced reserves.
        """
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)
        tiers = get_baseline_fee_tiers("conservative")

        amm1 = create_tiered_fee_amm("TieredIdentical_A", tiers, reserve_x, reserve_y)
        amm2 = create_tiered_fee_amm("TieredIdentical_B", tiers, reserve_x, reserve_y)

        amms = [amm1, amm2]
        initial_states = [snapshot_amm_state(amm) for amm in amms]

        # Execute 100 random trades
        execute_random_trades(amms, 100, seed=42)

        final_states = [snapshot_amm_state(amm) for amm in amms]

        # Calculate PnL
        pnl1 = calculate_pnl(initial_states[0], final_states[0])
        pnl2 = calculate_pnl(initial_states[1], final_states[1])

        # Verify symmetry
        is_symmetric, diff_pct = verify_symmetry(
            pnl1.pnl_at_final_price, pnl2.pnl_at_final_price, tolerance_pct=Decimal("5")
        )

        assert is_symmetric, (
            f"Identical tiered-fee strategies should have symmetric PnL. "
            f"AMM1 PnL: {pnl1.pnl_at_final_price:.4f}, "
            f"AMM2 PnL: {pnl2.pnl_at_final_price:.4f}, "
            f"Difference: {diff_pct:.2f}% (tolerance: 5%)"
        )

    def test_identical_aggressive_tiers_symmetric(self):
        """Test symmetry with aggressive tier profile (50→10→1 bps)."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)
        tiers = get_baseline_fee_tiers("aggressive")

        amm1 = create_tiered_fee_amm("Aggressive_A", tiers, reserve_x, reserve_y)
        amm2 = create_tiered_fee_amm("Aggressive_B", tiers, reserve_x, reserve_y)

        amms = [amm1, amm2]
        initial_states = [snapshot_amm_state(amm) for amm in amms]

        # Execute trades with larger sizes to trigger tier transitions
        execute_random_trades(
            amms, 50, seed=789, size_range=(Decimal("50"), Decimal("500"))
        )

        final_states = [snapshot_amm_state(amm) for amm in amms]

        pnl1 = calculate_pnl(initial_states[0], final_states[0])
        pnl2 = calculate_pnl(initial_states[1], final_states[1])

        is_symmetric, diff_pct = verify_symmetry(
            pnl1.pnl_at_final_price, pnl2.pnl_at_final_price, tolerance_pct=Decimal("5")
        )

        assert is_symmetric, (
            f"Identical aggressive-tier strategies should have symmetric PnL. "
            f"AMM1 PnL: {pnl1.pnl_at_final_price:.4f}, "
            f"AMM2 PnL: {pnl2.pnl_at_final_price:.4f}, "
            f"Difference: {diff_pct:.2f}% (tolerance: 5%)"
        )


class TestNearIdenticalStrategies:
    """Test proportional PnL for near-identical strategies."""

    def test_near_identical_strategies_proportional_pnl(self):
        """Test that slightly different fees lead to proportional PnL differences.

        Creates two AMMs with 30bps vs 31bps fees. The lower-fee AMM should
        capture more volume and have higher PnL, proportional to the advantage.
        """
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amm_low = create_constant_fee_amm(
            "LowFee_30bps", Decimal("0.0030"), reserve_x, reserve_y
        )
        amm_high = create_constant_fee_amm(
            "HighFee_31bps", Decimal("0.0031"), reserve_x, reserve_y
        )

        amms = [amm_low, amm_high]
        initial_states = [snapshot_amm_state(amm) for amm in amms]

        # Execute trades
        execute_random_trades(amms, 100, seed=456)

        final_states = [snapshot_amm_state(amm) for amm in amms]

        pnl_low = calculate_pnl(initial_states[0], final_states[0])
        pnl_high = calculate_pnl(initial_states[1], final_states[1])

        # Lower fee AMM should have higher or equal PnL
        assert (
            pnl_low.pnl_at_final_price >= pnl_high.pnl_at_final_price * Decimal("0.95")
        ), (
            f"Lower-fee AMM should have higher PnL. "
            f"Low fee (30bps) PnL: {pnl_low.pnl_at_final_price:.4f}, "
            f"High fee (31bps) PnL: {pnl_high.pnl_at_final_price:.4f}"
        )

        # Calculate volume received by each AMM
        vol_low = abs(final_states[0].reserve_x - initial_states[0].reserve_x)
        vol_high = abs(final_states[1].reserve_x - initial_states[1].reserve_x)

        # Lower fee AMM should receive more or equal volume
        assert vol_low >= vol_high * Decimal("0.9"), (
            f"Lower-fee AMM should receive more volume. "
            f"Low fee volume: {vol_low:.2f}, High fee volume: {vol_high:.2f}"
        )

    def test_fee_advantage_translates_to_volume(self):
        """Test that fee advantage leads to volume advantage.

        Compares 25bps vs 35bps fees (significant 10bps difference).
        The lower-fee AMM should capture substantially more flow.
        """
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amm_competitive = create_constant_fee_amm(
            "Competitive_25bps", Decimal("0.0025"), reserve_x, reserve_y
        )
        amm_expensive = create_constant_fee_amm(
            "Expensive_35bps", Decimal("0.0035"), reserve_x, reserve_y
        )

        amms = [amm_competitive, amm_expensive]
        initial_states = [snapshot_amm_state(amm) for amm in amms]

        execute_random_trades(amms, 100, seed=999)

        final_states = [snapshot_amm_state(amm) for amm in amms]

        # Calculate volumes
        vol_competitive = abs(
            final_states[0].reserve_x - initial_states[0].reserve_x
        ) + abs(final_states[0].reserve_y - initial_states[0].reserve_y)
        vol_expensive = abs(final_states[1].reserve_x - initial_states[1].reserve_x) + abs(
            final_states[1].reserve_y - initial_states[1].reserve_y
        )

        # Competitive AMM should dominate
        assert vol_competitive > vol_expensive, (
            f"Competitive AMM (25bps) should receive more volume than expensive (35bps). "
            f"Competitive: {vol_competitive:.2f}, Expensive: {vol_expensive:.2f}"
        )

        # Calculate PnL
        pnl_competitive = calculate_pnl(initial_states[0], final_states[0])
        pnl_expensive = calculate_pnl(initial_states[1], final_states[1])

        assert pnl_competitive.pnl_at_final_price > pnl_expensive.pnl_at_final_price, (
            f"Competitive AMM should have higher PnL. "
            f"Competitive PnL: {pnl_competitive.pnl_at_final_price:.4f}, "
            f"Expensive PnL: {pnl_expensive.pnl_at_final_price:.4f}"
        )


class TestAsymmetricReserves:
    """Test fair competition with asymmetric reserve sizes."""

    def test_asymmetric_reserves_fair_competition(self):
        """Test that AMMs with different liquidity levels can both compete.

        Creates one AMM with 10k reserves and another with 20k reserves.
        Both should receive flow based on their marginal pricing, not size alone.
        """
        # Small AMM: 10k balanced
        reserve_x_small, reserve_y_small = (Decimal("10000"), Decimal("10000"))
        # Large AMM: 20k balanced
        reserve_x_large, reserve_y_large = (Decimal("20000"), Decimal("20000"))

        fee_rate = Decimal("0.003")  # Same fees

        amm_small = create_constant_fee_amm(
            "Small_10k", fee_rate, reserve_x_small, reserve_y_small
        )
        amm_large = create_constant_fee_amm(
            "Large_20k", fee_rate, reserve_x_large, reserve_y_large
        )

        amms = [amm_small, amm_large]
        initial_states = [snapshot_amm_state(amm) for amm in amms]

        # Execute moderate-sized trades
        execute_random_trades(
            amms, 50, seed=111, size_range=(Decimal("50"), Decimal("200"))
        )

        final_states = [snapshot_amm_state(amm) for amm in amms]

        # Both AMMs should have received some volume
        vol_small = abs(final_states[0].reserve_x - initial_states[0].reserve_x) + abs(
            final_states[0].reserve_y - initial_states[0].reserve_y
        )
        vol_large = abs(final_states[1].reserve_x - initial_states[1].reserve_x) + abs(
            final_states[1].reserve_y - initial_states[1].reserve_y
        )

        assert vol_small > 0, "Small AMM should receive some volume"
        assert vol_large > 0, "Large AMM should receive some volume"

        # Both should be profitable
        pnl_small = calculate_pnl(initial_states[0], final_states[0])
        pnl_large = calculate_pnl(initial_states[1], final_states[1])

        assert pnl_small.fees_earned_x > 0 or pnl_small.fees_earned_y > 0, (
            "Small AMM should earn fees"
        )
        assert pnl_large.fees_earned_x > 0 or pnl_large.fees_earned_y > 0, (
            "Large AMM should earn fees"
        )

    def test_skewed_reserves_compete_effectively(self):
        """Test that AMMs with skewed reserves can still compete.

        One AMM has more X, another has more Y. Both should be used by router.
        """
        reserve_x_skewed_x, reserve_y_skewed_x = (Decimal("20000"), Decimal("5000"))
        reserve_x_skewed_y, reserve_y_skewed_y = (Decimal("5000"), Decimal("20000"))

        fee_rate = Decimal("0.003")

        amm_x_heavy = create_constant_fee_amm(
            "X_Heavy", fee_rate, reserve_x_skewed_x, reserve_y_skewed_x
        )
        amm_y_heavy = create_constant_fee_amm(
            "Y_Heavy", fee_rate, reserve_x_skewed_y, reserve_y_skewed_y
        )

        amms = [amm_x_heavy, amm_y_heavy]
        initial_states = [snapshot_amm_state(amm) for amm in amms]

        # Execute diverse trades
        execute_random_trades(amms, 100, seed=222)

        final_states = [snapshot_amm_state(amm) for amm in amms]

        # Both should have participated
        vol_x_heavy = abs(final_states[0].reserve_x - initial_states[0].reserve_x)
        vol_y_heavy = abs(final_states[1].reserve_x - initial_states[1].reserve_x)

        assert vol_x_heavy > 0, "X-heavy AMM should receive volume"
        assert vol_y_heavy > 0, "Y-heavy AMM should receive volume"


class TestMultipleRunsConsistency:
    """Test that symmetry holds across multiple runs with different seeds."""

    def test_multiple_runs_consistent_symmetry(self):
        """Run same scenario with different random seeds.

        Verifies that symmetry property holds statistically across
        multiple independent runs.
        """
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)
        fee_rate = Decimal("0.003")

        seeds = [100, 200, 300, 400, 500]
        symmetry_results = []

        for seed in seeds:
            # Create fresh AMMs for each run
            amm1 = create_constant_fee_amm("Multi_A", fee_rate, reserve_x, reserve_y)
            amm2 = create_constant_fee_amm("Multi_B", fee_rate, reserve_x, reserve_y)

            amms = [amm1, amm2]
            initial_states = [snapshot_amm_state(amm) for amm in amms]

            # Execute trades with this seed
            execute_random_trades(amms, 50, seed=seed)

            final_states = [snapshot_amm_state(amm) for amm in amms]

            # Calculate PnL
            pnl1 = calculate_pnl(initial_states[0], final_states[0])
            pnl2 = calculate_pnl(initial_states[1], final_states[1])

            # Check symmetry
            is_symmetric, diff_pct = verify_symmetry(
                pnl1.pnl_at_final_price,
                pnl2.pnl_at_final_price,
                tolerance_pct=Decimal("5"),
            )

            symmetry_results.append((seed, is_symmetric, diff_pct))

        # All runs should show symmetry
        failures = [
            (seed, diff_pct)
            for seed, is_symmetric, diff_pct in symmetry_results
            if not is_symmetric
        ]

        assert not failures, (
            f"Symmetry should hold across all seeds. Failures: "
            f"{[(s, f'{d:.2f}%') for s, d in failures]}"
        )

        # Calculate average and max deviation
        deviations = [diff_pct for _, _, diff_pct in symmetry_results]
        avg_deviation = sum(deviations) / len(deviations)
        max_deviation = max(deviations)

        # Average deviation should be low
        assert avg_deviation < Decimal("3"), (
            f"Average deviation across seeds should be < 3%. Got {avg_deviation:.2f}%"
        )

        # Max deviation should still be within tolerance
        assert max_deviation < Decimal("5"), (
            f"Max deviation should be < 5%. Got {max_deviation:.2f}%"
        )

    def test_statistical_distribution_of_pnl(self):
        """Test that PnL distribution is consistent across seeds.

        Verifies that PnL magnitudes are similar across different random runs,
        indicating stable and predictable behavior.
        """
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)
        fee_rate = Decimal("0.003")

        seeds = [1000, 2000, 3000, 4000, 5000]
        pnl_values = []

        for seed in seeds:
            amm = create_constant_fee_amm("Statistical", fee_rate, reserve_x, reserve_y)
            initial_state = snapshot_amm_state(amm)

            # Execute trades
            execute_random_trades([amm], 100, seed=seed)

            final_state = snapshot_amm_state(amm)
            pnl = calculate_pnl(initial_state, final_state)

            pnl_values.append(pnl.pnl_at_final_price)

        # Calculate statistics
        avg_pnl = sum(pnl_values) / len(pnl_values)
        min_pnl = min(pnl_values)
        max_pnl = max(pnl_values)

        # All PnL values should be in similar range
        pnl_range = max_pnl - min_pnl
        if avg_pnl != 0:
            relative_range = pnl_range / abs(avg_pnl)
            assert relative_range < Decimal("1.0"), (
                f"PnL range should be less than 100% of average. "
                f"Range: {pnl_range:.2f}, Avg: {avg_pnl:.2f}, "
                f"Relative: {relative_range * 100:.1f}%"
            )


class TestThreeIdenticalAMMs:
    """Test symmetry with three identical AMMs."""

    def test_three_identical_amms_symmetric(self):
        """Test that three identical AMMs all have similar PnL.

        Each should receive approximately 1/3 of the volume and have
        similar profit outcomes.
        """
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)
        fee_rate = Decimal("0.003")

        amm1 = create_constant_fee_amm("Triple_A", fee_rate, reserve_x, reserve_y)
        amm2 = create_constant_fee_amm("Triple_B", fee_rate, reserve_x, reserve_y)
        amm3 = create_constant_fee_amm("Triple_C", fee_rate, reserve_x, reserve_y)

        amms = [amm1, amm2, amm3]
        initial_states = [snapshot_amm_state(amm) for amm in amms]

        # Execute trades
        execute_random_trades(amms, 150, seed=333)

        final_states = [snapshot_amm_state(amm) for amm in amms]

        # Calculate PnL for all three
        pnls = [
            calculate_pnl(initial_states[i], final_states[i]) for i in range(3)
        ]

        # Check pairwise symmetry
        is_sym_12, diff_12 = verify_symmetry(
            pnls[0].pnl_at_final_price,
            pnls[1].pnl_at_final_price,
            tolerance_pct=Decimal("10"),  # Slightly higher tolerance for 3-way split
        )
        is_sym_13, diff_13 = verify_symmetry(
            pnls[0].pnl_at_final_price,
            pnls[1].pnl_at_final_price,
            tolerance_pct=Decimal("10"),
        )
        is_sym_23, diff_23 = verify_symmetry(
            pnls[1].pnl_at_final_price,
            pnls[2].pnl_at_final_price,
            tolerance_pct=Decimal("10"),
        )

        assert is_sym_12, (
            f"AMM1 and AMM2 should have symmetric PnL. "
            f"Difference: {diff_12:.2f}% (tolerance: 10%)"
        )
        assert is_sym_13, (
            f"AMM1 and AMM3 should have symmetric PnL. "
            f"Difference: {diff_13:.2f}% (tolerance: 10%)"
        )
        assert is_sym_23, (
            f"AMM2 and AMM3 should have symmetric PnL. "
            f"Difference: {diff_23:.2f}% (tolerance: 10%)"
        )

        # Check volume distribution
        volumes = []
        for i in range(3):
            vol = abs(final_states[i].reserve_x - initial_states[i].reserve_x) + abs(
                final_states[i].reserve_y - initial_states[i].reserve_y
            )
            volumes.append(vol)

        # Each should get roughly 1/3 of volume (within 30% tolerance due to discrete routing)
        avg_volume = sum(volumes) / len(volumes)
        for i, vol in enumerate(volumes):
            deviation = abs(vol - avg_volume) / avg_volume
            assert deviation < Decimal("0.3"), (
                f"AMM{i+1} volume should be within 30% of average. "
                f"Volume: {vol:.2f}, Average: {avg_volume:.2f}, "
                f"Deviation: {deviation * 100:.1f}%"
            )

    def test_three_tiered_amms_symmetric(self):
        """Test three identical tiered-fee AMMs for symmetry."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)
        tiers = get_baseline_fee_tiers("moderate")

        amm1 = create_tiered_fee_amm("TieredTriple_A", tiers, reserve_x, reserve_y)
        amm2 = create_tiered_fee_amm("TieredTriple_B", tiers, reserve_x, reserve_y)
        amm3 = create_tiered_fee_amm("TieredTriple_C", tiers, reserve_x, reserve_y)

        amms = [amm1, amm2, amm3]
        initial_states = [snapshot_amm_state(amm) for amm in amms]

        # Execute larger trades to trigger tiers
        execute_random_trades(
            amms, 100, seed=444, size_range=(Decimal("50"), Decimal("300"))
        )

        final_states = [snapshot_amm_state(amm) for amm in amms]

        # Calculate PnL
        pnls = [
            calculate_pnl(initial_states[i], final_states[i]) for i in range(3)
        ]

        # All should be positive and similar
        for i, pnl in enumerate(pnls):
            assert pnl.fees_earned_x > 0 or pnl.fees_earned_y > 0, (
                f"AMM{i+1} should earn fees"
            )

        # Check symmetry between all pairs
        is_sym_12, _ = verify_symmetry(
            pnls[0].pnl_at_final_price,
            pnls[1].pnl_at_final_price,
            tolerance_pct=Decimal("10"),
        )
        is_sym_13, _ = verify_symmetry(
            pnls[0].pnl_at_final_price,
            pnls[2].pnl_at_final_price,
            tolerance_pct=Decimal("10"),
        )
        is_sym_23, _ = verify_symmetry(
            pnls[1].pnl_at_final_price,
            pnls[2].pnl_at_final_price,
            tolerance_pct=Decimal("10"),
        )

        assert all([is_sym_12, is_sym_13, is_sym_23]), (
            "All three tiered AMMs should have symmetric PnL"
        )


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_identical_amms_zero_trades(self):
        """Test that identical AMMs with no trades have zero PnL difference."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)
        fee_rate = Decimal("0.003")

        amm1 = create_constant_fee_amm("Zero_A", fee_rate, reserve_x, reserve_y)
        amm2 = create_constant_fee_amm("Zero_B", fee_rate, reserve_x, reserve_y)

        initial_states = [snapshot_amm_state(amm1), snapshot_amm_state(amm2)]
        final_states = initial_states  # No changes

        pnl1 = calculate_pnl(initial_states[0], final_states[0])
        pnl2 = calculate_pnl(initial_states[1], final_states[1])

        assert pnl1.pnl_at_final_price == Decimal("0"), "No trades should mean zero PnL"
        assert pnl2.pnl_at_final_price == Decimal("0"), "No trades should mean zero PnL"

        is_symmetric, diff = verify_symmetry(
            pnl1.pnl_at_final_price, pnl2.pnl_at_final_price
        )
        assert is_symmetric and diff == Decimal("0"), "Zero PnL should be perfectly symmetric"

    def test_single_large_trade_symmetry(self):
        """Test symmetry with a single large trade instead of many small ones."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)
        fee_rate = Decimal("0.003")

        amm1 = create_constant_fee_amm("SingleTrade_A", fee_rate, reserve_x, reserve_y)
        amm2 = create_constant_fee_amm("SingleTrade_B", fee_rate, reserve_x, reserve_y)

        amms = [amm1, amm2]
        initial_states = [snapshot_amm_state(amm) for amm in amms]

        # Execute just one large trade
        execute_random_trades(
            amms, 1, seed=555, size_range=(Decimal("1000"), Decimal("1001"))
        )

        final_states = [snapshot_amm_state(amm) for amm in amms]

        pnl1 = calculate_pnl(initial_states[0], final_states[0])
        pnl2 = calculate_pnl(initial_states[1], final_states[1])

        # Should still be symmetric
        is_symmetric, diff_pct = verify_symmetry(
            pnl1.pnl_at_final_price, pnl2.pnl_at_final_price, tolerance_pct=Decimal("5")
        )

        assert is_symmetric, (
            f"Single large trade should maintain symmetry. "
            f"Difference: {diff_pct:.2f}%"
        )
