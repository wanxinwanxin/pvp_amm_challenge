"""Backward compatibility tests for router implementations.

Verifies that constant-fee strategies behave identically between:
- Old system: constant fees only, no tier support
- New system: tiered fees with constant fee fallback

Test strategy:
- Use constant-fee AMMs only (no tiers)
- Compare splits, execution prices, and final states
- Test multiple AMM counts (1, 2, 5)
- Test both buy and sell directions
- Test multiple trade sizes

Acceptance criteria:
- Splits match within 0.01%
- Execution prices match within 1e-10 (Decimal precision)
- Final reserves match within 1e-10
- PnLs match within 0.001%
"""

import pytest
from decimal import Decimal

from amm_competition.market.retail import RetailOrder
from tests.fixtures.economic_fixtures import (
    create_constant_fee_amm,
    PoolBalanceProfile,
    get_pool_balance,
    snapshot_amm_state,
    calculate_pnl,
)
from tests.utils.version_comparison import (
    OldRouter,
    NewRouter,
    run_parallel_simulations,
    compare_routing_decisions,
)


class TestConstantFeeSingleAMM:
    """Test backward compatibility with a single AMM.

    With only one AMM, routing is trivial - all flow goes to that AMM.
    This tests basic execution mechanics.
    """

    def test_single_amm_buy_small(self):
        """Test small buy order routed to single AMM."""
        amm = create_constant_fee_amm(
            "SingleAMM",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        order = RetailOrder(side="buy", size=Decimal("100"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, [amm], fair_price)

        # With single AMM, splits should be identical (100%)
        assert len(comparison.split_comparisons) == 1
        assert comparison.splits_match

        # Execution prices should match exactly
        assert comparison.prices_match
        assert abs(comparison.price_diff) < Decimal("1e-10")

        # Final reserves should match
        assert comparison.reserves_match

    def test_single_amm_sell_small(self):
        """Test small sell order routed to single AMM."""
        amm = create_constant_fee_amm(
            "SingleAMM",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        order = RetailOrder(side="sell", size=Decimal("100"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, [amm], fair_price)

        assert comparison.splits_match
        assert comparison.prices_match
        assert comparison.reserves_match

    def test_single_amm_buy_large(self):
        """Test large buy order routed to single AMM."""
        amm = create_constant_fee_amm(
            "SingleAMM",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        order = RetailOrder(side="buy", size=Decimal("5000"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, [amm], fair_price)

        assert comparison.splits_match
        assert comparison.prices_match
        assert comparison.reserves_match

    def test_single_amm_sell_large(self):
        """Test large sell order routed to single AMM."""
        amm = create_constant_fee_amm(
            "SingleAMM",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        order = RetailOrder(side="sell", size=Decimal("5000"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, [amm], fair_price)

        assert comparison.splits_match
        assert comparison.prices_match
        assert comparison.reserves_match


class TestConstantFeeTwoAMMs:
    """Test backward compatibility with two AMMs.

    Two-AMM case is the most important since it's the base case
    for the optimal splitting algorithm.
    """

    def test_two_identical_amms_buy(self):
        """Test buy order split across two identical AMMs.

        With identical AMMs, split should be 50/50.
        """
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amms = [
            create_constant_fee_amm("AMM1", Decimal("0.003"), reserve_x, reserve_y),
            create_constant_fee_amm("AMM2", Decimal("0.003"), reserve_x, reserve_y),
        ]

        order = RetailOrder(side="buy", size=Decimal("1000"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        # Verify splits match
        assert comparison.splits_match
        for sc in comparison.split_comparisons:
            # Should be approximately 500 each
            assert abs(sc.old_amount - Decimal("500")) < Decimal("10")
            assert abs(sc.new_amount - Decimal("500")) < Decimal("10")
            assert abs(sc.relative_diff_pct) < Decimal("0.01")

        # Verify execution
        assert comparison.prices_match
        assert comparison.reserves_match

    def test_two_identical_amms_sell(self):
        """Test sell order split across two identical AMMs."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amms = [
            create_constant_fee_amm("AMM1", Decimal("0.003"), reserve_x, reserve_y),
            create_constant_fee_amm("AMM2", Decimal("0.003"), reserve_x, reserve_y),
        ]

        order = RetailOrder(side="sell", size=Decimal("1000"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        assert comparison.splits_match
        assert comparison.prices_match
        assert comparison.reserves_match

    def test_two_different_fees_buy(self):
        """Test buy order with different fee rates.

        Lower fee AMM should get more flow.
        """
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amms = [
            create_constant_fee_amm("LowFee", Decimal("0.002"), reserve_x, reserve_y),
            create_constant_fee_amm("HighFee", Decimal("0.004"), reserve_x, reserve_y),
        ]

        order = RetailOrder(side="buy", size=Decimal("1000"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        # Splits should match
        assert comparison.splits_match

        # LowFee should get more flow
        low_fee_split = next(sc for sc in comparison.split_comparisons if sc.amm_name == "LowFee")
        high_fee_split = next(sc for sc in comparison.split_comparisons if sc.amm_name == "HighFee")

        assert low_fee_split.old_amount > high_fee_split.old_amount
        assert low_fee_split.new_amount > high_fee_split.new_amount

        # Execution should match
        assert comparison.prices_match
        assert comparison.reserves_match

    def test_two_different_fees_sell(self):
        """Test sell order with different fee rates."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amms = [
            create_constant_fee_amm("LowFee", Decimal("0.002"), reserve_x, reserve_y),
            create_constant_fee_amm("HighFee", Decimal("0.004"), reserve_x, reserve_y),
        ]

        order = RetailOrder(side="sell", size=Decimal("1000"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        assert comparison.splits_match
        assert comparison.prices_match
        assert comparison.reserves_match

    def test_two_different_reserves_buy(self):
        """Test buy order with different reserve sizes.

        Larger AMM should get more flow.
        """
        amms = [
            create_constant_fee_amm("SmallPool", Decimal("0.003"), Decimal("5000"), Decimal("5000")),
            create_constant_fee_amm("LargePool", Decimal("0.003"), Decimal("20000"), Decimal("20000")),
        ]

        order = RetailOrder(side="buy", size=Decimal("1000"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        assert comparison.splits_match

        # LargePool should get more flow
        small_split = next(sc for sc in comparison.split_comparisons if sc.amm_name == "SmallPool")
        large_split = next(sc for sc in comparison.split_comparisons if sc.amm_name == "LargePool")

        assert large_split.old_amount > small_split.old_amount
        assert large_split.new_amount > small_split.new_amount

        assert comparison.prices_match
        assert comparison.reserves_match

    def test_two_different_reserves_sell(self):
        """Test sell order with different reserve sizes."""
        amms = [
            create_constant_fee_amm("SmallPool", Decimal("0.003"), Decimal("5000"), Decimal("5000")),
            create_constant_fee_amm("LargePool", Decimal("0.003"), Decimal("20000"), Decimal("20000")),
        ]

        order = RetailOrder(side="sell", size=Decimal("1000"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        assert comparison.splits_match
        assert comparison.prices_match
        assert comparison.reserves_match

    def test_two_skewed_reserves_buy(self):
        """Test with skewed reserve ratios (different prices)."""
        amms = [
            create_constant_fee_amm("SkewedX", Decimal("0.003"), Decimal("20000"), Decimal("5000")),
            create_constant_fee_amm("SkewedY", Decimal("0.003"), Decimal("5000"), Decimal("20000")),
        ]

        order = RetailOrder(side="buy", size=Decimal("1000"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        assert comparison.splits_match
        assert comparison.prices_match
        assert comparison.reserves_match


class TestConstantFeeFiveAMMs:
    """Test backward compatibility with five AMMs.

    Multi-AMM routing uses pairwise approximation. Should still
    match exactly for constant fees.
    """

    def test_five_identical_amms_buy(self):
        """Test buy order across five identical AMMs."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amms = [
            create_constant_fee_amm(f"AMM{i}", Decimal("0.003"), reserve_x, reserve_y)
            for i in range(5)
        ]

        order = RetailOrder(side="buy", size=Decimal("1000"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        assert comparison.splits_match
        assert comparison.prices_match
        assert comparison.reserves_match

    def test_five_identical_amms_sell(self):
        """Test sell order across five identical AMMs."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amms = [
            create_constant_fee_amm(f"AMM{i}", Decimal("0.003"), reserve_x, reserve_y)
            for i in range(5)
        ]

        order = RetailOrder(side="sell", size=Decimal("1000"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        assert comparison.splits_match
        assert comparison.prices_match
        assert comparison.reserves_match

    def test_five_varied_fees_buy(self):
        """Test buy order with varied fee rates."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amms = [
            create_constant_fee_amm("Fee1", Decimal("0.001"), reserve_x, reserve_y),
            create_constant_fee_amm("Fee2", Decimal("0.002"), reserve_x, reserve_y),
            create_constant_fee_amm("Fee3", Decimal("0.003"), reserve_x, reserve_y),
            create_constant_fee_amm("Fee4", Decimal("0.004"), reserve_x, reserve_y),
            create_constant_fee_amm("Fee5", Decimal("0.005"), reserve_x, reserve_y),
        ]

        order = RetailOrder(side="buy", size=Decimal("2000"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        assert comparison.splits_match
        assert comparison.prices_match
        assert comparison.reserves_match

        # Lower fees should get more flow
        fee1_split = next(sc for sc in comparison.split_comparisons if sc.amm_name == "Fee1")
        fee5_split = next(sc for sc in comparison.split_comparisons if sc.amm_name == "Fee5")

        assert fee1_split.old_amount > fee5_split.old_amount
        assert fee1_split.new_amount > fee5_split.new_amount

    def test_five_varied_fees_sell(self):
        """Test sell order with varied fee rates."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amms = [
            create_constant_fee_amm("Fee1", Decimal("0.001"), reserve_x, reserve_y),
            create_constant_fee_amm("Fee2", Decimal("0.002"), reserve_x, reserve_y),
            create_constant_fee_amm("Fee3", Decimal("0.003"), reserve_x, reserve_y),
            create_constant_fee_amm("Fee4", Decimal("0.004"), reserve_x, reserve_y),
            create_constant_fee_amm("Fee5", Decimal("0.005"), reserve_x, reserve_y),
        ]

        order = RetailOrder(side="sell", size=Decimal("2000"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        assert comparison.splits_match
        assert comparison.prices_match
        assert comparison.reserves_match

    def test_five_varied_reserves_buy(self):
        """Test buy order with varied reserve sizes."""
        amms = [
            create_constant_fee_amm("Pool1", Decimal("0.003"), Decimal("5000"), Decimal("5000")),
            create_constant_fee_amm("Pool2", Decimal("0.003"), Decimal("10000"), Decimal("10000")),
            create_constant_fee_amm("Pool3", Decimal("0.003"), Decimal("15000"), Decimal("15000")),
            create_constant_fee_amm("Pool4", Decimal("0.003"), Decimal("20000"), Decimal("20000")),
            create_constant_fee_amm("Pool5", Decimal("0.003"), Decimal("25000"), Decimal("25000")),
        ]

        order = RetailOrder(side="buy", size=Decimal("2000"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        assert comparison.splits_match
        assert comparison.prices_match
        assert comparison.reserves_match


class TestIdenticalExecutionPrices:
    """Test that execution prices match exactly.

    Execution price is the key metric for traders - it must match
    exactly between old and new systems.
    """

    def test_execution_price_small_buy(self):
        """Test execution price for small buy order."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amms = [
            create_constant_fee_amm("AMM1", Decimal("0.003"), reserve_x, reserve_y),
            create_constant_fee_amm("AMM2", Decimal("0.003"), reserve_x, reserve_y),
        ]

        order = RetailOrder(side="buy", size=Decimal("100"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        # Prices should match within 1e-10
        assert abs(comparison.price_diff) < Decimal("1e-10")
        assert comparison.prices_match

    def test_execution_price_large_buy(self):
        """Test execution price for large buy order."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amms = [
            create_constant_fee_amm("AMM1", Decimal("0.003"), reserve_x, reserve_y),
            create_constant_fee_amm("AMM2", Decimal("0.003"), reserve_x, reserve_y),
        ]

        order = RetailOrder(side="buy", size=Decimal("5000"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        assert abs(comparison.price_diff) < Decimal("1e-10")
        assert comparison.prices_match

    def test_execution_price_small_sell(self):
        """Test execution price for small sell order."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amms = [
            create_constant_fee_amm("AMM1", Decimal("0.003"), reserve_x, reserve_y),
            create_constant_fee_amm("AMM2", Decimal("0.003"), reserve_x, reserve_y),
        ]

        order = RetailOrder(side="sell", size=Decimal("100"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        assert abs(comparison.price_diff) < Decimal("1e-10")
        assert comparison.prices_match

    def test_execution_price_large_sell(self):
        """Test execution price for large sell order."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amms = [
            create_constant_fee_amm("AMM1", Decimal("0.003"), reserve_x, reserve_y),
            create_constant_fee_amm("AMM2", Decimal("0.003"), reserve_x, reserve_y),
        ]

        order = RetailOrder(side="sell", size=Decimal("5000"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        assert abs(comparison.price_diff) < Decimal("1e-10")
        assert comparison.prices_match


class TestIdenticalSplits:
    """Test that split allocations match exactly.

    Split decisions should be identical for constant-fee AMMs
    since both routers use the same algorithm in that case.
    """

    def test_split_decision_only_buy(self):
        """Test split decision without execution (buy)."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amms = [
            create_constant_fee_amm("AMM1", Decimal("0.002"), reserve_x, reserve_y),
            create_constant_fee_amm("AMM2", Decimal("0.004"), reserve_x, reserve_y),
        ]

        order = RetailOrder(side="buy", size=Decimal("1000"))
        fair_price = Decimal("1.0")

        comparisons, all_match = compare_routing_decisions(order, amms, fair_price)

        assert all_match
        for comp in comparisons:
            assert abs(comp.relative_diff_pct) < Decimal("0.01")

    def test_split_decision_only_sell(self):
        """Test split decision without execution (sell)."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amms = [
            create_constant_fee_amm("AMM1", Decimal("0.002"), reserve_x, reserve_y),
            create_constant_fee_amm("AMM2", Decimal("0.004"), reserve_x, reserve_y),
        ]

        order = RetailOrder(side="sell", size=Decimal("1000"))
        fair_price = Decimal("1.0")

        comparisons, all_match = compare_routing_decisions(order, amms, fair_price)

        assert all_match
        for comp in comparisons:
            assert abs(comp.relative_diff_pct) < Decimal("0.01")

    def test_splits_multiple_sizes(self):
        """Test splits across multiple trade sizes."""
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
            Decimal("10000"),   # Very large
        ]

        for size in sizes:
            order = RetailOrder(side="buy", size=size)
            comparisons, all_match = compare_routing_decisions(order, amms, fair_price)
            assert all_match, f"Splits don't match for size {size}"


class TestBuyAndSellDirections:
    """Test both buy and sell directions comprehensively.

    Both directions should produce identical results between
    old and new routers.
    """

    def test_symmetric_buy_sell_pair(self):
        """Test matching buy and sell orders."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amms = [
            create_constant_fee_amm("AMM1", Decimal("0.003"), reserve_x, reserve_y),
            create_constant_fee_amm("AMM2", Decimal("0.003"), reserve_x, reserve_y),
        ]

        fair_price = Decimal("1.0")

        # Test buy
        buy_order = RetailOrder(side="buy", size=Decimal("1000"))
        buy_comparison = run_parallel_simulations(buy_order, amms, fair_price)

        assert buy_comparison.splits_match
        assert buy_comparison.prices_match
        assert buy_comparison.reserves_match

        # Test sell (create fresh AMMs)
        amms = [
            create_constant_fee_amm("AMM1", Decimal("0.003"), reserve_x, reserve_y),
            create_constant_fee_amm("AMM2", Decimal("0.003"), reserve_x, reserve_y),
        ]

        sell_order = RetailOrder(side="sell", size=Decimal("1000"))
        sell_comparison = run_parallel_simulations(sell_order, amms, fair_price)

        assert sell_comparison.splits_match
        assert sell_comparison.prices_match
        assert sell_comparison.reserves_match

    def test_asymmetric_fees_both_directions(self):
        """Test asymmetric fees in both directions."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        # Test buy direction
        buy_amms = [
            create_constant_fee_amm("AMM1", Decimal("0.002"), reserve_x, reserve_y),
            create_constant_fee_amm("AMM2", Decimal("0.004"), reserve_x, reserve_y),
        ]

        buy_order = RetailOrder(side="buy", size=Decimal("1000"))
        buy_comparison = run_parallel_simulations(buy_order, buy_amms, Decimal("1.0"))

        assert buy_comparison.splits_match
        assert buy_comparison.prices_match

        # Test sell direction
        sell_amms = [
            create_constant_fee_amm("AMM1", Decimal("0.002"), reserve_x, reserve_y),
            create_constant_fee_amm("AMM2", Decimal("0.004"), reserve_x, reserve_y),
        ]

        sell_order = RetailOrder(side="sell", size=Decimal("1000"))
        sell_comparison = run_parallel_simulations(sell_order, sell_amms, Decimal("1.0"))

        assert sell_comparison.splits_match
        assert sell_comparison.prices_match


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_fee_amm(self):
        """Test with zero-fee AMM."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amms = [
            create_constant_fee_amm("ZeroFee", Decimal("0"), reserve_x, reserve_y),
            create_constant_fee_amm("NormalFee", Decimal("0.003"), reserve_x, reserve_y),
        ]

        order = RetailOrder(side="buy", size=Decimal("1000"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        assert comparison.splits_match
        assert comparison.prices_match

        # Zero-fee AMM should get most of the flow
        zero_fee_split = next(sc for sc in comparison.split_comparisons if sc.amm_name == "ZeroFee")
        normal_fee_split = next(sc for sc in comparison.split_comparisons if sc.amm_name == "NormalFee")

        assert zero_fee_split.old_amount > normal_fee_split.old_amount

    def test_very_small_order(self):
        """Test with very small order size."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        amms = [
            create_constant_fee_amm("AMM1", Decimal("0.003"), reserve_x, reserve_y),
            create_constant_fee_amm("AMM2", Decimal("0.003"), reserve_x, reserve_y),
        ]

        order = RetailOrder(side="buy", size=Decimal("0.01"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        assert comparison.splits_match
        assert comparison.prices_match

    def test_extreme_reserve_imbalance(self):
        """Test with extremely imbalanced reserves."""
        amms = [
            create_constant_fee_amm("Extreme", Decimal("0.003"), Decimal("1"), Decimal("1000000")),
            create_constant_fee_amm("Normal", Decimal("0.003"), Decimal("10000"), Decimal("10000")),
        ]

        order = RetailOrder(side="buy", size=Decimal("1000"))
        fair_price = Decimal("1.0")

        comparison = run_parallel_simulations(order, amms, fair_price)

        assert comparison.splits_match
        assert comparison.prices_match


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
