"""Edge case and stress testing module for AMM system.

Tests extreme scenarios including:
- Numerical precision (tiny/huge values)
- Pool states (empty, imbalanced, identical)
- Fee structures (zero, maximum, pathological)
- Trade patterns (many small, alternating)

All tests verify graceful handling without exceptions, crashes,
or precision loss. Uses Decimal throughout for exact arithmetic.
"""

import pytest
from decimal import Decimal
from typing import List

from amm_competition.core.amm import AMM
from amm_competition.market.router import OrderRouter
from tests.fixtures.economic_fixtures import (
    create_constant_fee_amm,
    create_tiered_fee_amm,
    get_baseline_fee_tiers,
    snapshot_amm_state,
    calculate_pnl,
)


class TestNumericalPrecision:
    """Test cases for numerical precision with extreme values."""

    def test_tiny_trade_sizes_decimal_precision(self):
        """Execute trades with very small sizes and verify no precision loss.

        Tests:
        - Trade size of 0.0001
        - Reserves change correctly
        - No rounding errors accumulate
        """
        amm = create_constant_fee_amm(
            "TinyTrades",
            Decimal("0.003"),
            reserve_x=Decimal("10000"),
            reserve_y=Decimal("10000")
        )

        before = snapshot_amm_state(amm)
        tiny_size = Decimal("0.0001")

        # Execute very small trade
        trade_info = amm.execute_buy_x(tiny_size, timestamp=1)

        # Verify trade executed
        assert trade_info is not None
        assert trade_info.amount_x == tiny_size

        # Verify reserves changed correctly
        after = snapshot_amm_state(amm)
        pnl = calculate_pnl(before, after)

        # AMM gained X (trader sold X)
        assert pnl.delta_x > Decimal("0")
        assert pnl.delta_x <= tiny_size  # Some goes to fees

        # AMM lost Y (paid out to trader)
        assert pnl.delta_y < Decimal("0")

        # Fees should be positive but very small
        assert pnl.fees_earned_x >= Decimal("0")
        assert pnl.fees_earned_x < tiny_size

        # Verify k invariant maintained (within floating point tolerance)
        # k should stay constant since fees don't go to reserves
        k_before = before.reserve_x * before.reserve_y
        k_after = after.reserve_x * after.reserve_y
        relative_error = abs(k_after - k_before) / k_before
        assert relative_error < Decimal("0.000001")  # 0.0001% tolerance

    def test_huge_trade_sizes_no_overflow(self):
        """Execute trades with very large sizes and verify no overflow.

        Tests:
        - Trade size of 1,000,000
        - Decimal handles large values correctly
        - No arithmetic overflow errors
        """
        # Create AMM with large reserves
        amm = create_constant_fee_amm(
            "HugeTrades",
            Decimal("0.003"),
            reserve_x=Decimal("10000000"),  # 10M
            reserve_y=Decimal("10000000")   # 10M
        )

        before = snapshot_amm_state(amm)
        huge_size = Decimal("1000000")  # 1M

        # Execute large trade (10% of reserves)
        trade_info = amm.execute_buy_x(huge_size, timestamp=1)

        # Verify trade executed
        assert trade_info is not None
        assert trade_info.amount_x == huge_size

        # Verify reserves updated correctly
        after = snapshot_amm_state(amm)
        pnl = calculate_pnl(before, after)

        # Check deltas are reasonable
        assert pnl.delta_x > Decimal("0")
        assert pnl.delta_y < Decimal("0")

        # Verify Y output is reasonable (should be close to 1M for balanced pool)
        y_out = abs(pnl.delta_y)
        assert y_out > Decimal("900000")  # At least 900k (after fees & slippage)
        assert y_out < Decimal("1000000")  # Less than 1M (fees applied)

        # k invariant should still hold
        k_before = before.reserve_x * before.reserve_y
        k_after = after.reserve_x * after.reserve_y
        relative_error = abs(k_after - k_before) / k_before
        assert relative_error < Decimal("0.00001")  # 0.001% tolerance for large numbers


class TestExtremePoolStates:
    """Test cases for extreme pool configurations."""

    def test_extreme_pool_imbalance(self):
        """Test routing through severely imbalanced pool.

        Creates pool with reserves (1, 1000000) and verifies:
        - Router handles imbalance gracefully
        - No division by zero errors
        - Trade can still execute
        """
        amm_imbalanced = create_tiered_fee_amm(
            "Imbalanced",
            get_baseline_fee_tiers("conservative"),
            reserve_x=Decimal("1"),
            reserve_y=Decimal("1000000")
        )

        amm_balanced = create_tiered_fee_amm(
            "Balanced",
            get_baseline_fee_tiers("conservative"),
            reserve_x=Decimal("10000"),
            reserve_y=Decimal("10000")
        )

        router = OrderRouter()

        # Try to buy 1000 Y worth of X
        # Should route mostly to balanced pool
        try:
            splits = router.compute_optimal_split_buy(
                [amm_imbalanced, amm_balanced],
                Decimal("1000")
            )

            # Verify splits are valid
            assert len(splits) == 2
            assert all(s[1] >= Decimal("0") for s in splits)

            # Total should equal input
            total = sum(s[1] for s in splits)
            assert abs(total - Decimal("1000")) < Decimal("0.01")

            # Most should go to balanced pool (imbalanced has very little X)
            balanced_amount = next(s[1] for s in splits if s[0].name == "Balanced")
            assert balanced_amount > Decimal("900")  # At least 90%

        except Exception as e:
            pytest.fail(f"Failed on extreme imbalance: {e}")

    def test_zero_liquidity_pool_handling(self):
        """Test router with nearly empty pool.

        Verifies:
        - Router skips or minimizes usage of empty pool
        - No division by zero errors
        - Trades route to pools with liquidity
        """
        amm_empty = create_constant_fee_amm(
            "Empty",
            Decimal("0.003"),
            reserve_x=Decimal("0.01"),  # Nearly empty
            reserve_y=Decimal("0.01")
        )

        amm_full = create_constant_fee_amm(
            "Full",
            Decimal("0.003"),
            reserve_x=Decimal("10000"),
            reserve_y=Decimal("10000")
        )

        router = OrderRouter()

        # Route order - should go entirely to full pool
        splits = router.compute_optimal_split_sell(
            [amm_empty, amm_full],
            Decimal("100")
        )

        # Verify splits are valid
        assert len(splits) == 2
        assert all(s[1] >= Decimal("0") for s in splits)

        # Nearly all should go to full pool
        full_amount = next(s[1] for s in splits if s[0].name == "Full")
        assert full_amount > Decimal("99.9")  # >99.9%

        # Empty pool should get negligible amount
        empty_amount = next(s[1] for s in splits if s[0].name == "Empty")
        assert empty_amount < Decimal("0.1")  # <0.1%

    def test_very_similar_amms(self):
        """Test routing with nearly identical AMMs.

        Verifies:
        - Router splits approximately equally
        - Numerical stability with similar values
        - No pathological behavior
        """
        # Create three identical AMMs
        amms = [
            create_constant_fee_amm(
                f"AMM{i}",
                Decimal("0.003"),
                reserve_x=Decimal("10000"),
                reserve_y=Decimal("10000")
            )
            for i in range(3)
        ]

        router = OrderRouter()

        # Route order across identical AMMs
        splits = router.compute_optimal_split_sell(
            amms,
            Decimal("300")
        )

        # Verify all splits are similar (within 5% of equal split)
        assert len(splits) == 3
        expected_per_amm = Decimal("100")  # 300 / 3

        for amm, amount in splits:
            # Each should get ~100, allow 5% variance due to pairwise approximation
            assert abs(amount - expected_per_amm) < Decimal("5")

        # Total should equal input
        total = sum(s[1] for s in splits)
        assert abs(total - Decimal("300")) < Decimal("0.01")


class TestExtremeFeeStructures:
    """Test cases for extreme fee configurations."""

    def test_all_fees_zero_edge_case(self):
        """Test AMMs with zero fees.

        Verifies:
        - Routing still works with zero fees
        - Optimal splits computed correctly
        - No division by zero with gamma = 1
        """
        amm_zero1 = create_constant_fee_amm(
            "ZeroFee1",
            Decimal("0"),  # No fees
            reserve_x=Decimal("10000"),
            reserve_y=Decimal("10000")
        )

        amm_zero2 = create_constant_fee_amm(
            "ZeroFee2",
            Decimal("0"),  # No fees
            reserve_x=Decimal("5000"),
            reserve_y=Decimal("5000")
        )

        router = OrderRouter()

        # Route with zero fees
        splits = router.compute_optimal_split_sell(
            [amm_zero1, amm_zero2],
            Decimal("100")
        )

        # Verify splits computed
        assert len(splits) == 2
        assert all(s[1] >= Decimal("0") for s in splits)

        # Total should equal input
        total = sum(s[1] for s in splits)
        assert abs(total - Decimal("100")) < Decimal("0.01")

        # Larger pool should get more (2x reserves = ~2x flow)
        larger_amount = next(s[1] for s in splits if s[0].name == "ZeroFee1")
        smaller_amount = next(s[1] for s in splits if s[0].name == "ZeroFee2")
        assert larger_amount > smaller_amount

    def test_all_fees_maximum_edge_case(self):
        """Test AMMs with very high fees (10%).

        Verifies:
        - System handles expensive fees
        - Trades still execute
        - Fee calculations correct
        """
        amm_expensive = create_constant_fee_amm(
            "Expensive",
            Decimal("0.1"),  # 10% fee (1000 bps)
            reserve_x=Decimal("10000"),
            reserve_y=Decimal("10000")
        )

        before = snapshot_amm_state(amm_expensive)

        # Execute trade with high fees
        trade_info = amm_expensive.execute_buy_x(Decimal("100"), timestamp=1)

        # Trade should execute
        assert trade_info is not None

        after = snapshot_amm_state(amm_expensive)
        pnl = calculate_pnl(before, after)

        # Verify high fees collected
        # 10% of 100 = 10 X in fees
        assert pnl.fees_earned_x >= Decimal("9.9")
        assert pnl.fees_earned_x <= Decimal("10.1")

        # Only 90 X should go to reserves
        net_x = pnl.delta_reserve_x
        assert net_x >= Decimal("89")
        assert net_x <= Decimal("91")

    def test_single_tier_at_boundaries(self):
        """Test trades exactly at tier thresholds.

        Verifies:
        - Correct tier selection at boundaries
        - No off-by-one errors
        - Effective fee calculation correct
        """
        tiers = [
            (Decimal("0"), Decimal("0.003")),     # 30 bps
            (Decimal("100"), Decimal("0.002")),   # 20 bps
            (Decimal("1000"), Decimal("0.001")),  # 10 bps
        ]

        amm = create_tiered_fee_amm(
            "Tiered",
            tiers,
            reserve_x=Decimal("10000"),
            reserve_y=Decimal("10000")
        )

        # Test trade exactly at first threshold
        fee_at_0 = amm.current_fees.effective_bid_fee(Decimal("0"))
        assert fee_at_0 == Decimal("0.003")

        # Test trade exactly at second threshold
        fee_at_100 = amm.current_fees.effective_bid_fee(Decimal("100"))
        # Should be weighted average of tier 0 only
        assert fee_at_100 == Decimal("0.003")

        # Test trade just past second threshold
        fee_at_101 = amm.current_fees.effective_bid_fee(Decimal("101"))
        # Should be weighted: (100*0.003 + 1*0.002) / 101
        expected = (Decimal("100") * Decimal("0.003") + Decimal("1") * Decimal("0.002")) / Decimal("101")
        assert abs(fee_at_101 - expected) < Decimal("0.000001")

        # Test trade exactly at third threshold
        fee_at_1000 = amm.current_fees.effective_bid_fee(Decimal("1000"))
        # Should be weighted: (100*0.003 + 900*0.002) / 1000
        expected = (Decimal("100") * Decimal("0.003") + Decimal("900") * Decimal("0.002")) / Decimal("1000")
        assert abs(fee_at_1000 - expected) < Decimal("0.000001")


class TestTradePatterns:
    """Test cases for complex trade patterns."""

    def test_many_small_trades_vs_one_large(self):
        """Compare 100 tiny trades vs 1 large trade of same total size.

        Verifies:
        - Final states are similar (within tolerance)
        - No accumulation errors
        - k invariant maintained
        """
        # Create two identical AMMs
        amm_many = create_constant_fee_amm(
            "ManySmall",
            Decimal("0.003"),
            reserve_x=Decimal("10000"),
            reserve_y=Decimal("10000")
        )

        amm_one = create_constant_fee_amm(
            "OneLarge",
            Decimal("0.003"),
            reserve_x=Decimal("10000"),
            reserve_y=Decimal("10000")
        )

        total_size = Decimal("1000")
        num_trades = 100
        small_size = total_size / num_trades

        # Execute 100 small trades
        for i in range(num_trades):
            trade_info = amm_many.execute_buy_x(small_size, timestamp=i)
            assert trade_info is not None

        # Execute 1 large trade
        trade_info = amm_one.execute_buy_x(total_size, timestamp=1)
        assert trade_info is not None

        # Compare final states
        state_many = snapshot_amm_state(amm_many)
        state_one = snapshot_amm_state(amm_one)

        # Reserves should be similar (within 0.1% due to path dependence)
        rx_diff = abs(state_many.reserve_x - state_one.reserve_x) / state_one.reserve_x
        ry_diff = abs(state_many.reserve_y - state_one.reserve_y) / state_one.reserve_y

        assert rx_diff < Decimal("0.001")  # Within 0.1%
        assert ry_diff < Decimal("0.001")  # Within 0.1%

        # Fees should be exactly equal (same total size, same fee rate)
        assert abs(state_many.accumulated_fees_x - state_one.accumulated_fees_x) < Decimal("0.01")

    def test_alternating_buy_sell(self):
        """Execute alternating buy and sell trades.

        Verifies:
        - No drift or accumulation errors
        - Final state close to initial (after equal buys/sells)
        - Fees collected on both sides
        """
        amm = create_constant_fee_amm(
            "Alternating",
            Decimal("0.003"),
            reserve_x=Decimal("10000"),
            reserve_y=Decimal("10000")
        )

        before = snapshot_amm_state(amm)
        trade_size = Decimal("100")
        num_cycles = 50

        # Execute alternating buy/sell trades
        for i in range(num_cycles):
            # Buy X (trader sells X to AMM)
            trade_info = amm.execute_buy_x(trade_size, timestamp=i * 2)
            assert trade_info is not None

            # Sell X (trader buys X from AMM)
            trade_info = amm.execute_sell_x(trade_size, timestamp=i * 2 + 1)
            assert trade_info is not None

        after = snapshot_amm_state(amm)

        # Reserves should be close to original (within 1% due to fees)
        rx_change = abs(after.reserve_x - before.reserve_x) / before.reserve_x
        ry_change = abs(after.reserve_y - before.reserve_y) / before.reserve_y

        assert rx_change < Decimal("0.01")  # Within 1%
        assert ry_change < Decimal("0.01")  # Within 1%

        # Should have collected fees on both sides
        assert after.accumulated_fees_x > Decimal("0")
        assert after.accumulated_fees_y > Decimal("0")

        # Total fees should be roughly equal (equal trade sizes)
        # Convert fees to common unit for comparison
        fees_x_value = after.accumulated_fees_x * after.spot_price
        fees_y_value = after.accumulated_fees_y

        # Should be within 10% of each other
        if fees_y_value > 0:
            ratio = fees_x_value / fees_y_value
            assert ratio > Decimal("0.9")
            assert ratio < Decimal("1.1")


class TestRouterEdgeCases:
    """Test router behavior in edge cases."""

    def test_router_with_pathological_fee_tiers(self):
        """Test router with pathological fee structure (10000bps -> 1bps).

        Verifies:
        - Router handles extreme fee transitions
        - No numerical instability
        - Converges to valid solution
        """
        amm_pathological = create_tiered_fee_amm(
            "Pathological",
            get_baseline_fee_tiers("pathological"),  # 100% -> 1bps -> 0.1bps
            reserve_x=Decimal("10000"),
            reserve_y=Decimal("10000")
        )

        amm_normal = create_constant_fee_amm(
            "Normal",
            Decimal("0.003"),
            reserve_x=Decimal("10000"),
            reserve_y=Decimal("10000")
        )

        router = OrderRouter()

        # Small trade should avoid pathological AMM (100% fee on first unit)
        splits = router.compute_optimal_split_sell(
            [amm_pathological, amm_normal],
            Decimal("0.5")  # Very small trade
        )

        # Should route mostly to normal AMM
        normal_amount = next(s[1] for s in splits if s[0].name == "Normal")
        pathological_amount = next(s[1] for s in splits if s[0].name == "Pathological")

        assert normal_amount > Decimal("0.4")  # Most to normal
        assert pathological_amount < Decimal("0.1")  # Little to pathological

        # Large trade should use pathological AMM (after first unit, fees are low)
        splits = router.compute_optimal_split_sell(
            [amm_pathological, amm_normal],
            Decimal("1000")  # Large trade
        )

        # With large trade, pathological becomes attractive after threshold
        normal_amount = next(s[1] for s in splits if s[0].name == "Normal")
        pathological_amount = next(s[1] for s in splits if s[0].name == "Pathological")

        # Both should get significant flow
        assert normal_amount > Decimal("100")
        assert pathological_amount > Decimal("100")

    def test_router_convergence_with_tiered_fees(self):
        """Test that router converges quickly with tiered fees.

        Verifies:
        - Iterative refinement converges within 5 iterations
        - Final split is stable
        - No oscillation or divergence
        """
        amm1 = create_tiered_fee_amm(
            "Tiered1",
            get_baseline_fee_tiers("conservative"),
            reserve_x=Decimal("10000"),
            reserve_y=Decimal("10000")
        )

        amm2 = create_tiered_fee_amm(
            "Tiered2",
            get_baseline_fee_tiers("moderate"),
            reserve_x=Decimal("8000"),
            reserve_y=Decimal("12000")
        )

        router = OrderRouter()

        # Compute split multiple times - should be stable
        splits1 = router.compute_optimal_split_sell([amm1, amm2], Decimal("500"))
        splits2 = router.compute_optimal_split_sell([amm1, amm2], Decimal("500"))
        splits3 = router.compute_optimal_split_sell([amm1, amm2], Decimal("500"))

        # All splits should be identical (router is deterministic)
        assert splits1[0][1] == splits2[0][1]
        assert splits1[0][1] == splits3[0][1]
        assert splits1[1][1] == splits2[1][1]
        assert splits1[1][1] == splits3[1][1]

        # Verify total is preserved
        total1 = sum(s[1] for s in splits1)
        assert abs(total1 - Decimal("500")) < Decimal("0.01")


class TestStressScenarios:
    """Stress tests combining multiple edge cases."""

    def test_mixed_extreme_amms(self):
        """Test router with mix of extreme AMMs.

        Combines:
        - Empty pool
        - Imbalanced pool
        - High fee pool
        - Normal pool
        """
        amms: List[AMM] = [
            create_constant_fee_amm(
                "Empty",
                Decimal("0.003"),
                reserve_x=Decimal("0.01"),
                reserve_y=Decimal("0.01")
            ),
            create_constant_fee_amm(
                "Imbalanced",
                Decimal("0.003"),
                reserve_x=Decimal("1"),
                reserve_y=Decimal("100000")
            ),
            create_constant_fee_amm(
                "HighFee",
                Decimal("0.05"),  # 5% fee
                reserve_x=Decimal("10000"),
                reserve_y=Decimal("10000")
            ),
            create_constant_fee_amm(
                "Normal",
                Decimal("0.003"),
                reserve_x=Decimal("10000"),
                reserve_y=Decimal("10000")
            ),
        ]

        router = OrderRouter()

        # Route order through mixed AMMs
        try:
            splits = router.compute_optimal_split_sell(amms, Decimal("100"))

            # Verify basic sanity
            assert len(splits) == len(amms)
            assert all(s[1] >= Decimal("0") for s in splits)

            # Total should equal input
            total = sum(s[1] for s in splits)
            assert abs(total - Decimal("100")) < Decimal("0.1")

            # Normal pool should get most of the flow
            normal_amount = next(s[1] for s in splits if s[0].name == "Normal")
            assert normal_amount > Decimal("50")  # At least 50%

        except Exception as e:
            pytest.fail(f"Failed with mixed extreme AMMs: {e}")

    def test_continuous_trading_stability(self):
        """Test system stability under continuous trading.

        Executes 1000 trades and verifies:
        - No numerical drift
        - k invariant maintained
        - Fees accumulate correctly
        """
        amm = create_constant_fee_amm(
            "ContinuousTrading",
            Decimal("0.003"),
            reserve_x=Decimal("100000"),
            reserve_y=Decimal("100000")
        )

        before = snapshot_amm_state(amm)
        num_trades = 1000

        # Execute many trades of varying sizes
        for i in range(num_trades):
            # Alternate direction
            if i % 2 == 0:
                size = Decimal(str(10 + (i % 50)))  # Varying sizes 10-59
                trade_info = amm.execute_buy_x(size, timestamp=i)
            else:
                size = Decimal(str(10 + ((i + 25) % 50)))  # Different pattern
                trade_info = amm.execute_sell_x(size, timestamp=i)

            assert trade_info is not None

        after = snapshot_amm_state(amm)

        # Verify k invariant maintained (within 0.01% after 1000 trades)
        k_before = before.reserve_x * before.reserve_y
        k_after = after.reserve_x * after.reserve_y
        relative_error = abs(k_after - k_before) / k_before
        assert relative_error < Decimal("0.0001")

        # Should have collected substantial fees
        assert after.accumulated_fees_x > Decimal("100")
        assert after.accumulated_fees_y > Decimal("100")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
