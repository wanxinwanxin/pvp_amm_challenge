"""Tests for economic test fixtures.

Verifies that the fixture infrastructure works correctly and produces
accurate results for AMM state snapshots and PnL calculations.
"""

import pytest
from decimal import Decimal

from tests.fixtures.economic_fixtures import (
    PoolBalanceProfile,
    create_constant_fee_amm,
    create_tiered_fee_amm,
    create_amm_set,
    get_baseline_fee_tiers,
    get_pool_balance,
    snapshot_amm_state,
    calculate_pnl,
)


class TestConstantFeeAMM:
    """Tests for constant fee AMM creation."""

    def test_create_basic(self):
        """Test creating a basic constant fee AMM."""
        amm = create_constant_fee_amm(
            "TestConstant",
            Decimal("0.003"),
            Decimal("1000"),
            Decimal("1000"),
        )

        assert amm.name == "TestConstant"
        assert amm.reserve_x == Decimal("1000")
        assert amm.reserve_y == Decimal("1000")
        assert amm.current_fees.bid_fee == Decimal("0.003")
        assert amm.current_fees.ask_fee == Decimal("0.003")
        assert amm.current_fees.bid_tiers is None
        assert amm.current_fees.ask_tiers is None

    def test_create_asymmetric(self):
        """Test creating an AMM with different bid/ask fees."""
        amm = create_constant_fee_amm(
            "Asymmetric",
            Decimal("0.003"),
            Decimal("1000"),
            Decimal("1000"),
            asymmetric=True,
            ask_fee_rate=Decimal("0.004"),
        )

        assert amm.current_fees.bid_fee == Decimal("0.003")
        assert amm.current_fees.ask_fee == Decimal("0.004")

    def test_initialized(self):
        """Test that AMM is properly initialized."""
        amm = create_constant_fee_amm(
            "TestInit",
            Decimal("0.003"),
            Decimal("1000"),
            Decimal("1000"),
        )

        # Should be able to get quotes immediately
        quote = amm.get_quote_buy_x(Decimal("10"))
        assert quote is not None
        assert quote.fee_rate == Decimal("0.003")


class TestTieredFeeAMM:
    """Tests for tiered fee AMM creation."""

    def test_create_two_tier(self):
        """Test creating a two-tier fee AMM."""
        tiers = [
            (Decimal("0"), Decimal("0.003")),
            (Decimal("100"), Decimal("0.002")),
        ]
        amm = create_tiered_fee_amm(
            "TwoTier",
            tiers,
            Decimal("1000"),
            Decimal("1000"),
        )

        assert amm.name == "TwoTier"
        assert amm.current_fees.bid_tiers is not None
        assert len(amm.current_fees.bid_tiers) == 2
        assert amm.current_fees.bid_tiers[0].threshold == Decimal("0")
        assert amm.current_fees.bid_tiers[0].fee == Decimal("0.003")
        assert amm.current_fees.bid_tiers[1].threshold == Decimal("100")
        assert amm.current_fees.bid_tiers[1].fee == Decimal("0.002")

    def test_create_three_tier(self):
        """Test creating a three-tier fee AMM."""
        tiers = [
            (Decimal("0"), Decimal("0.003")),
            (Decimal("100"), Decimal("0.002")),
            (Decimal("1000"), Decimal("0.001")),
        ]
        amm = create_tiered_fee_amm(
            "ThreeTier",
            tiers,
            Decimal("1000"),
            Decimal("1000"),
        )

        assert len(amm.current_fees.bid_tiers) == 3

    def test_effective_fees(self):
        """Test that effective fee calculation works with tiers."""
        tiers = [
            (Decimal("0"), Decimal("0.003")),
            (Decimal("100"), Decimal("0.002")),
        ]
        amm = create_tiered_fee_amm(
            "Tiered",
            tiers,
            Decimal("1000"),
            Decimal("1000"),
        )

        # Small trade should use base tier
        small_fee = amm.current_fees.effective_bid_fee(Decimal("50"))
        assert small_fee == Decimal("0.003")

        # Large trade should average across tiers
        large_fee = amm.current_fees.effective_bid_fee(Decimal("150"))
        # 150 = 100@0.003 + 50@0.002
        expected = (Decimal("100") * Decimal("0.003") +
                   Decimal("50") * Decimal("0.002")) / Decimal("150")
        assert large_fee == expected

    def test_invalid_tiers_raises(self):
        """Test that invalid tier configurations raise errors."""
        # Empty tiers
        with pytest.raises(ValueError, match="empty"):
            create_tiered_fee_amm("Bad", [], Decimal("1000"), Decimal("1000"))

        # Too many tiers
        with pytest.raises(ValueError, match="Maximum 3"):
            tiers = [
                (Decimal("0"), Decimal("0.003")),
                (Decimal("100"), Decimal("0.002")),
                (Decimal("200"), Decimal("0.001")),
                (Decimal("300"), Decimal("0.0005")),
            ]
            create_tiered_fee_amm("Bad", tiers, Decimal("1000"), Decimal("1000"))

        # First tier not at zero
        with pytest.raises(ValueError, match="threshold 0"):
            tiers = [(Decimal("10"), Decimal("0.003"))]
            create_tiered_fee_amm("Bad", tiers, Decimal("1000"), Decimal("1000"))


class TestBaselineFeeProfiles:
    """Tests for standard fee tier profiles."""

    def test_conservative_profile(self):
        """Test conservative fee tier profile."""
        tiers = get_baseline_fee_tiers("conservative")
        assert len(tiers) == 3
        assert tiers[0] == (Decimal("0"), Decimal("0.003"))
        assert tiers[1] == (Decimal("100"), Decimal("0.002"))
        assert tiers[2] == (Decimal("1000"), Decimal("0.001"))

    def test_moderate_profile(self):
        """Test moderate fee tier profile."""
        tiers = get_baseline_fee_tiers("moderate")
        assert len(tiers) == 3
        assert tiers[0][1] == Decimal("0.003")
        assert tiers[1][1] == Decimal("0.0015")
        assert tiers[2][1] == Decimal("0.0005")

    def test_aggressive_profile(self):
        """Test aggressive fee tier profile."""
        tiers = get_baseline_fee_tiers("aggressive")
        assert len(tiers) == 3
        assert tiers[0][1] == Decimal("0.005")  # 50 bps
        assert tiers[1][1] == Decimal("0.001")  # 10 bps
        assert tiers[2][1] == Decimal("0.0001")  # 1 bps

    def test_pathological_profile(self):
        """Test pathological fee tier profile."""
        tiers = get_baseline_fee_tiers("pathological")
        assert len(tiers) == 3
        assert tiers[0][1] == Decimal("0.1")  # 100%
        assert tiers[1][0] == Decimal("1")     # Kicks in at 1 token
        assert tiers[2][0] == Decimal("2")     # Kicks in at 2 tokens

    def test_invalid_profile_raises(self):
        """Test that invalid profile name raises error."""
        with pytest.raises(ValueError, match="Unknown profile"):
            get_baseline_fee_tiers("nonexistent")


class TestPoolBalanceProfiles:
    """Tests for pool balance configurations."""

    def test_balanced(self):
        """Test balanced pool configuration."""
        x, y = get_pool_balance(PoolBalanceProfile.BALANCED)
        assert x == y
        assert x == Decimal("10000")

    def test_skewed_x(self):
        """Test X-heavy pool configuration."""
        x, y = get_pool_balance(PoolBalanceProfile.SKEWED_X)
        assert x > y
        assert x == Decimal("20000")
        assert y == Decimal("5000")

    def test_skewed_y(self):
        """Test Y-heavy pool configuration."""
        x, y = get_pool_balance(PoolBalanceProfile.SKEWED_Y)
        assert y > x
        assert x == Decimal("5000")
        assert y == Decimal("20000")

    def test_extreme(self):
        """Test extreme imbalance configuration."""
        x, y = get_pool_balance(PoolBalanceProfile.EXTREME)
        assert x == Decimal("1")
        assert y == Decimal("1000000")


class TestAMMSet:
    """Tests for creating standard AMM sets."""

    def test_create_full_set(self):
        """Test creating full set of AMMs."""
        amms = create_amm_set(PoolBalanceProfile.BALANCED)
        assert len(amms) == 5

        names = [amm.name for amm in amms]
        assert "ConstantFee" in names
        assert "TwoTier" in names
        assert "ThreeTier" in names
        assert "Aggressive" in names
        assert "Pathological" in names

        # All should have same reserves
        for amm in amms:
            assert amm.reserve_x == Decimal("10000")
            assert amm.reserve_y == Decimal("10000")

    def test_create_constant_only(self):
        """Test creating only constant fee AMMs."""
        amms = create_amm_set(
            PoolBalanceProfile.BALANCED,
            include_constant=True,
            include_tiered=False,
        )
        assert len(amms) == 1
        assert amms[0].name == "ConstantFee"

    def test_create_tiered_only(self):
        """Test creating only tiered fee AMMs."""
        amms = create_amm_set(
            PoolBalanceProfile.BALANCED,
            include_constant=False,
            include_tiered=True,
        )
        assert len(amms) == 4
        assert all(amm.name != "ConstantFee" for amm in amms)

    def test_different_balance_profiles(self):
        """Test creating AMM sets with different balance profiles."""
        balanced = create_amm_set(PoolBalanceProfile.BALANCED)
        skewed_x = create_amm_set(PoolBalanceProfile.SKEWED_X)
        extreme = create_amm_set(PoolBalanceProfile.EXTREME)

        assert balanced[0].reserve_x == Decimal("10000")
        assert skewed_x[0].reserve_x == Decimal("20000")
        assert extreme[0].reserve_x == Decimal("1")


class TestStateSnapshot:
    """Tests for AMM state snapshots."""

    def test_snapshot_initial_state(self):
        """Test snapshotting initial AMM state."""
        amm = create_constant_fee_amm(
            "Test",
            Decimal("0.003"),
            Decimal("1000"),
            Decimal("1000"),
        )

        snapshot = snapshot_amm_state(amm)

        assert snapshot.name == "Test"
        assert snapshot.reserve_x == Decimal("1000")
        assert snapshot.reserve_y == Decimal("1000")
        assert snapshot.accumulated_fees_x == Decimal("0")
        assert snapshot.accumulated_fees_y == Decimal("0")
        assert snapshot.k == Decimal("1000000")

    def test_snapshot_after_trade(self):
        """Test snapshotting state after a trade."""
        amm = create_constant_fee_amm(
            "Test",
            Decimal("0.003"),
            Decimal("1000"),
            Decimal("1000"),
        )

        # Execute a trade
        trade = amm.execute_buy_x(Decimal("10"), timestamp=0)
        assert trade is not None

        snapshot = snapshot_amm_state(amm)

        # Reserves should have changed
        assert snapshot.reserve_x != Decimal("1000")
        assert snapshot.reserve_y != Decimal("1000")
        # Fees should have been collected
        assert snapshot.accumulated_fees_x > Decimal("0")

    def test_snapshot_immutable(self):
        """Test that snapshots are immutable."""
        amm = create_constant_fee_amm(
            "Test",
            Decimal("0.003"),
            Decimal("1000"),
            Decimal("1000"),
        )

        snapshot = snapshot_amm_state(amm)
        original_x = snapshot.reserve_x

        # Execute trade changes AMM but not snapshot
        amm.execute_buy_x(Decimal("10"), timestamp=0)

        assert snapshot.reserve_x == original_x

    def test_snapshot_properties(self):
        """Test snapshot computed properties."""
        amm = create_constant_fee_amm(
            "Test",
            Decimal("0.003"),
            Decimal("1000"),
            Decimal("1000"),
        )

        snapshot = snapshot_amm_state(amm)

        assert snapshot.total_x == Decimal("1000")
        assert snapshot.total_y == Decimal("1000")
        assert snapshot.spot_price == Decimal("1")  # Equal reserves


class TestPnLCalculation:
    """Tests for PnL calculation from snapshots."""

    def test_pnl_no_change(self):
        """Test PnL calculation with no trades."""
        amm = create_constant_fee_amm(
            "Test",
            Decimal("0.003"),
            Decimal("1000"),
            Decimal("1000"),
        )

        before = snapshot_amm_state(amm)
        after = snapshot_amm_state(amm)

        pnl = calculate_pnl(before, after)

        assert pnl.delta_x == Decimal("0")
        assert pnl.delta_y == Decimal("0")
        assert pnl.fees_earned_x == Decimal("0")
        assert pnl.fees_earned_y == Decimal("0")
        assert pnl.pnl_at_initial_price == Decimal("0")
        assert pnl.pnl_at_final_price == Decimal("0")

    def test_pnl_after_buy_trade(self):
        """Test PnL calculation after AMM buys X."""
        amm = create_constant_fee_amm(
            "Test",
            Decimal("0.003"),
            Decimal("1000"),
            Decimal("1000"),
        )

        before = snapshot_amm_state(amm)

        # AMM buys X (trader sells X to AMM)
        trade = amm.execute_buy_x(Decimal("10"), timestamp=0)
        assert trade is not None

        after = snapshot_amm_state(amm)
        pnl = calculate_pnl(before, after)

        # AMM gained X (positive delta)
        assert pnl.delta_x > Decimal("0")
        # AMM lost Y (negative delta)
        assert pnl.delta_y < Decimal("0")
        # Fees collected in X
        assert pnl.fees_earned_x > Decimal("0")
        assert pnl.fees_earned_y == Decimal("0")

    def test_pnl_after_sell_trade(self):
        """Test PnL calculation after AMM sells X."""
        amm = create_constant_fee_amm(
            "Test",
            Decimal("0.003"),
            Decimal("1000"),
            Decimal("1000"),
        )

        before = snapshot_amm_state(amm)

        # AMM sells X (trader buys X from AMM)
        trade = amm.execute_sell_x(Decimal("10"), timestamp=0)
        assert trade is not None

        after = snapshot_amm_state(amm)
        pnl = calculate_pnl(before, after)

        # AMM lost X (negative delta)
        assert pnl.delta_x < Decimal("0")
        # AMM gained Y (positive delta)
        assert pnl.delta_y > Decimal("0")
        # Fees collected in Y
        assert pnl.fees_earned_y > Decimal("0")
        assert pnl.fees_earned_x == Decimal("0")

    def test_pnl_multiple_trades(self):
        """Test PnL calculation across multiple trades."""
        amm = create_constant_fee_amm(
            "Test",
            Decimal("0.003"),
            Decimal("1000"),
            Decimal("1000"),
        )

        before = snapshot_amm_state(amm)

        # Execute multiple trades
        amm.execute_buy_x(Decimal("10"), timestamp=0)
        amm.execute_sell_x(Decimal("5"), timestamp=1)
        amm.execute_buy_x(Decimal("10"), timestamp=2)

        after = snapshot_amm_state(amm)
        pnl = calculate_pnl(before, after)

        # Should accumulate all changes
        assert pnl.delta_x != Decimal("0")
        assert pnl.delta_y != Decimal("0")
        # Should have fees from both directions
        assert pnl.fees_earned_x > Decimal("0")
        assert pnl.fees_earned_y > Decimal("0")

    def test_pnl_mismatched_amms_raises(self):
        """Test that PnL calculation requires matching AMM names."""
        amm1 = create_constant_fee_amm(
            "AMM1",
            Decimal("0.003"),
            Decimal("1000"),
            Decimal("1000"),
        )
        amm2 = create_constant_fee_amm(
            "AMM2",
            Decimal("0.003"),
            Decimal("1000"),
            Decimal("1000"),
        )

        snapshot1 = snapshot_amm_state(amm1)
        snapshot2 = snapshot_amm_state(amm2)

        with pytest.raises(ValueError, match="different AMMs"):
            calculate_pnl(snapshot1, snapshot2)

    def test_pnl_custom_valuation_price(self):
        """Test PnL calculation with custom valuation price."""
        amm = create_constant_fee_amm(
            "Test",
            Decimal("0.003"),
            Decimal("1000"),
            Decimal("1000"),
        )

        before = snapshot_amm_state(amm)
        amm.execute_buy_x(Decimal("10"), timestamp=0)
        after = snapshot_amm_state(amm)

        # Calculate PnL at specific price
        custom_price = Decimal("2.0")
        pnl = calculate_pnl(before, after, valuation_price=custom_price)

        # Both initial and final PnL should use custom price
        assert pnl.pnl_at_initial_price == pnl.pnl_at_final_price


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
