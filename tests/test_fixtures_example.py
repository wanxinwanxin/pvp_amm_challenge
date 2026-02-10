"""Example tests demonstrating economic fixtures usage.

These examples show how to use the fixtures for common testing scenarios.
"""

import pytest
from decimal import Decimal

from tests.fixtures import (
    PoolBalanceProfile,
    create_constant_fee_amm,
    create_tiered_fee_amm,
    create_amm_set,
    get_baseline_fee_tiers,
    snapshot_amm_state,
    calculate_pnl,
)


class TestBasicUsage:
    """Basic fixture usage examples."""

    def test_create_and_trade_constant_fee(self):
        """Example: Create constant fee AMM and execute a trade."""
        # Create AMM with 30 bps fee
        amm = create_constant_fee_amm(
            "Example",
            Decimal("0.003"),
            Decimal("1000"),
            Decimal("1000"),
        )

        # Take snapshot before trade
        before = snapshot_amm_state(amm)

        # Execute trade (AMM buys X)
        trade = amm.execute_buy_x(Decimal("10"), timestamp=0)
        assert trade is not None

        # Take snapshot after trade
        after = snapshot_amm_state(amm)

        # Calculate PnL
        pnl = calculate_pnl(before, after)

        # Verify trade executed correctly
        assert pnl.delta_x > Decimal("0")  # AMM gained X
        assert pnl.delta_y < Decimal("0")  # AMM lost Y
        assert pnl.fees_earned_x > Decimal("0")  # Collected fees

    def test_create_and_trade_tiered_fee(self):
        """Example: Create tiered fee AMM and execute a large trade."""
        # Create tiered AMM
        tiers = [
            (Decimal("0"), Decimal("0.003")),    # 30 bps small
            (Decimal("100"), Decimal("0.002")),  # 20 bps medium
            (Decimal("1000"), Decimal("0.001")), # 10 bps large
        ]
        amm = create_tiered_fee_amm("TieredExample", tiers,
                                    Decimal("10000"), Decimal("10000"))

        before = snapshot_amm_state(amm)

        # Large trade spanning multiple tiers
        trade = amm.execute_buy_x(Decimal("150"), timestamp=0)
        assert trade is not None

        after = snapshot_amm_state(amm)
        pnl = calculate_pnl(before, after)

        # Verify weighted average fee applied
        # 150 = 100@0.003 + 50@0.002
        expected_avg_fee = (Decimal("100") * Decimal("0.003") +
                           Decimal("50") * Decimal("0.002")) / Decimal("150")
        expected_total_fee = Decimal("150") * expected_avg_fee

        # Fees should be close to expected (accounting for rounding)
        assert abs(pnl.fees_earned_x - expected_total_fee) < Decimal("0.01")


class TestStandardProfiles:
    """Examples using standard profiles."""

    def test_compare_fee_profiles(self):
        """Example: Compare different fee profiles on same trade."""
        trade_size = Decimal("200")

        results = {}
        for profile in ["conservative", "moderate", "aggressive"]:
            tiers = get_baseline_fee_tiers(profile)
            amm = create_tiered_fee_amm(profile, tiers,
                                        Decimal("10000"), Decimal("10000"))

            before = snapshot_amm_state(amm)
            amm.execute_buy_x(trade_size, timestamp=0)
            after = snapshot_amm_state(amm)

            pnl = calculate_pnl(before, after)
            results[profile] = pnl.fees_earned_x

        # Aggressive should have highest base fee but drops faster
        # Conservative should have lower base fee but drops slower
        # For 200-token trade, all profiles should have collected fees
        assert all(fee > Decimal("0") for fee in results.values())

    def test_pool_balance_affects_price(self):
        """Example: Different pool balances have different prices."""
        profiles = [
            PoolBalanceProfile.BALANCED,
            PoolBalanceProfile.SKEWED_X,
            PoolBalanceProfile.SKEWED_Y,
        ]

        prices = {}
        for profile in profiles:
            amm = create_amm_set(profile, include_constant=True,
                                include_tiered=False)[0]
            snapshot = snapshot_amm_state(amm)
            prices[profile.value] = snapshot.spot_price

        # Balanced should have price = 1
        assert prices["balanced"] == Decimal("1")

        # Skewed_x (more X) should have lower price (Y per X)
        assert prices["skewed_x"] < Decimal("1")

        # Skewed_y (more Y) should have higher price (Y per X)
        assert prices["skewed_y"] > Decimal("1")


class TestMultiAMMScenarios:
    """Examples with multiple AMMs."""

    def test_compare_constant_vs_tiered(self):
        """Example: Compare constant vs tiered fee AMM on same trades."""
        # Create two AMMs with same initial reserves
        constant = create_constant_fee_amm("Constant", Decimal("0.003"),
                                          Decimal("1000"), Decimal("1000"))

        tiers = [
            (Decimal("0"), Decimal("0.003")),
            (Decimal("100"), Decimal("0.002")),
        ]
        tiered = create_tiered_fee_amm("Tiered", tiers,
                                       Decimal("1000"), Decimal("1000"))

        # Snapshots
        const_before = snapshot_amm_state(constant)
        tier_before = snapshot_amm_state(tiered)

        # Execute same trade on both
        trade_size = Decimal("150")
        constant.execute_buy_x(trade_size, timestamp=0)
        tiered.execute_buy_x(trade_size, timestamp=0)

        # Calculate PnL
        const_pnl = calculate_pnl(const_before, snapshot_amm_state(constant))
        tier_pnl = calculate_pnl(tier_before, snapshot_amm_state(tiered))

        # Constant should collect more fees (always 30 bps)
        # Tiered averages down (100@30bps + 50@20bps)
        assert const_pnl.fees_earned_x > tier_pnl.fees_earned_x

    def test_amm_set_economic_consistency(self):
        """Example: Verify economic consistency across AMM set."""
        amms = create_amm_set(PoolBalanceProfile.BALANCED)

        # All should start with same reserves
        for amm in amms:
            snapshot = snapshot_amm_state(amm)
            assert snapshot.reserve_x == Decimal("10000")
            assert snapshot.reserve_y == Decimal("10000")
            assert snapshot.k == Decimal("100000000")

        # Execute same trade on all
        trade_size = Decimal("10")
        for amm in amms:
            trade = amm.execute_buy_x(trade_size, timestamp=0)
            assert trade is not None

        # All should have changed reserves
        for amm in amms:
            snapshot = snapshot_amm_state(amm)
            # k should be preserved (fee-on-input model)
            assert abs(snapshot.k - Decimal("100000000")) < Decimal("1")

    def test_track_pnl_across_multiple_amms(self):
        """Example: Track and compare PnL across multiple AMMs."""
        # Create diverse AMM set
        amms = create_amm_set(PoolBalanceProfile.BALANCED)

        # Initial snapshots
        snapshots_before = {amm.name: snapshot_amm_state(amm) for amm in amms}

        # Simulate different trading patterns
        amms[0].execute_buy_x(Decimal("50"), timestamp=0)   # Small on constant
        amms[1].execute_buy_x(Decimal("150"), timestamp=1)  # Medium on two-tier
        amms[2].execute_buy_x(Decimal("1500"), timestamp=2) # Large on three-tier

        # Calculate PnL for each
        pnl_results = {}
        for amm in amms:
            if amm.name in snapshots_before:
                before = snapshots_before[amm.name]
                after = snapshot_amm_state(amm)
                pnl = calculate_pnl(before, after)
                pnl_results[amm.name] = pnl

        # Verify all traded AMMs earned fees
        assert pnl_results["ConstantFee"].fees_earned_x > Decimal("0")
        assert pnl_results["TwoTier"].fees_earned_x > Decimal("0")
        assert pnl_results["ThreeTier"].fees_earned_x > Decimal("0")

        # AMMs that didn't trade should have no change
        assert pnl_results["Aggressive"].fees_earned_x == Decimal("0")
        assert pnl_results["Pathological"].fees_earned_x == Decimal("0")


class TestEconomicInvariants:
    """Examples verifying economic invariants."""

    def test_constant_product_preserved(self):
        """Example: Verify k invariant with fee-on-input model."""
        amm = create_constant_fee_amm("Test", Decimal("0.003"),
                                     Decimal("1000"), Decimal("1000"))

        before = snapshot_amm_state(amm)
        k_initial = before.k

        # Execute multiple trades
        for i in range(10):
            if i % 2 == 0:
                amm.execute_buy_x(Decimal("10"), timestamp=i)
            else:
                amm.execute_sell_x(Decimal("5"), timestamp=i)

        after = snapshot_amm_state(amm)
        k_final = after.k

        # In fee-on-input model, k should stay constant
        # (fees don't go into reserves)
        assert abs(k_final - k_initial) < Decimal("0.01")

    def test_fees_accumulate_correctly(self):
        """Example: Verify fees accumulate in separate bucket."""
        amm = create_constant_fee_amm("Test", Decimal("0.003"),
                                     Decimal("1000"), Decimal("1000"))

        before = snapshot_amm_state(amm)

        # Execute trades in both directions
        amm.execute_buy_x(Decimal("100"), timestamp=0)
        amm.execute_sell_x(Decimal("50"), timestamp=1)

        after = snapshot_amm_state(amm)
        pnl = calculate_pnl(before, after)

        # Fees should be in accumulated bucket, not reserves
        assert after.accumulated_fees_x > before.accumulated_fees_x
        assert after.accumulated_fees_y > before.accumulated_fees_y

        # PnL should account for both reserves and fees
        assert pnl.delta_x == pnl.delta_reserve_x + pnl.fees_earned_x
        assert pnl.delta_y == pnl.delta_reserve_y + pnl.fees_earned_y

    def test_pnl_valuation_consistency(self):
        """Example: PnL valuation at different prices."""
        amm = create_constant_fee_amm("Test", Decimal("0.003"),
                                     Decimal("1000"), Decimal("1000"))

        before = snapshot_amm_state(amm)
        amm.execute_buy_x(Decimal("10"), timestamp=0)
        after = snapshot_amm_state(amm)

        # Calculate PnL at different prices
        pnl_default = calculate_pnl(before, after)
        pnl_at_2 = calculate_pnl(before, after, Decimal("2.0"))
        pnl_at_half = calculate_pnl(before, after, Decimal("0.5"))

        # Higher price should value X gains more
        # AMM gained X (delta_x > 0), so higher price = higher PnL
        if pnl_default.delta_x > 0:
            assert pnl_at_2.pnl_at_initial_price > pnl_at_half.pnl_at_initial_price


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
