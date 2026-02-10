"""No-arbitrage testing module.

Verifies that the AMM system doesn't create exploitable arbitrage opportunities.
All arbitrage cycles (buy-then-sell or sell-then-buy) should result in a net
loss equal to the fees paid, preventing profitable arbitrage.

Economic correctness properties tested:
1. Round-trip trades always lose money (fees + slippage)
2. Loss equals fees paid (within tolerance)
3. No profitable arbitrage across multiple AMMs
4. Fee tier boundaries don't create exploitable opportunities
5. Extreme trade sizes behave correctly

All calculations use Decimal precision for accurate financial accounting.
"""

import pytest
from decimal import Decimal
from typing import List, Tuple

from amm_competition.core.amm import AMM
from tests.fixtures.economic_fixtures import (
    PoolBalanceProfile,
    create_constant_fee_amm,
    create_tiered_fee_amm,
    create_amm_set,
    get_baseline_fee_tiers,
    snapshot_amm_state,
)
from tests.utils.economic_verification import verify_no_arbitrage


class TestNoArbitrageConstantFees:
    """Test that constant fee AMMs prevent arbitrage."""

    def test_buy_sell_cycle_loses_money(self):
        """Test that buying then selling results in net loss.

        Buy-sell cycle (trader perspective):
        1. Buy 100 X with Y (spend Y, receive X)
        2. Sell 100 X for Y (spend X, receive Y)

        Expected: Net Y received < Net Y spent (loss = fees + slippage)
        """
        amm = create_constant_fee_amm(
            "ConstantFee",
            Decimal("0.003"),  # 30 bps
            Decimal("10000"),
            Decimal("10000"),
        )

        initial_snapshot = snapshot_amm_state(amm)
        trade_size = Decimal("100")
        price = initial_snapshot.spot_price  # 1.0

        # Execute buy-sell cycle
        # Step 1: Trader buys X (AMM sells X)
        quote_buy = amm.get_quote_sell_x(trade_size)
        assert quote_buy is not None
        trade1 = amm.execute_sell_x(trade_size, timestamp=0)
        assert trade1 is not None

        y_spent = trade1.amount_y  # Y paid by trader
        x_received = trade1.amount_x  # X received by trader

        # Step 2: Trader sells X back (AMM buys X)
        trade2 = amm.execute_buy_x(x_received, timestamp=1)
        assert trade2 is not None

        y_received = trade2.amount_y  # Y received by trader

        # Calculate net result
        net_y = y_received - y_spent

        # Should lose money
        assert net_y < Decimal("0"), f"Expected loss but got profit: {net_y}"

        # Calculate total fees paid
        final_snapshot = snapshot_amm_state(amm)
        total_fees_x = final_snapshot.accumulated_fees_x - initial_snapshot.accumulated_fees_x
        total_fees_y = final_snapshot.accumulated_fees_y - initial_snapshot.accumulated_fees_y

        # Convert fees to Y terms
        total_fees_in_y = total_fees_y + total_fees_x * price

        # Loss should approximately equal fees (within 0.1% due to slippage)
        expected_loss = -total_fees_in_y
        loss_difference = abs(net_y - expected_loss)
        relative_error = loss_difference / total_fees_in_y if total_fees_in_y > 0 else Decimal("0")

        assert relative_error < Decimal("0.001"), (
            f"Loss {abs(net_y)} doesn't match fees {total_fees_in_y}. "
            f"Relative error: {relative_error * 100}%"
        )

    def test_sell_buy_cycle_loses_money(self):
        """Test that selling then buying results in net loss.

        Sell-buy cycle (trader perspective):
        1. Sell 100 X for Y (spend X, receive Y)
        2. Buy 100 X with Y (spend Y, receive X)

        Expected: Net X received < Net X spent (loss = fees + slippage)
        """
        amm = create_constant_fee_amm(
            "ConstantFee",
            Decimal("0.003"),  # 30 bps
            Decimal("10000"),
            Decimal("10000"),
        )

        initial_snapshot = snapshot_amm_state(amm)
        trade_size = Decimal("100")
        price = initial_snapshot.spot_price

        # Execute sell-buy cycle
        # Step 1: Trader sells X (AMM buys X)
        trade1 = amm.execute_buy_x(trade_size, timestamp=0)
        assert trade1 is not None

        x_spent = trade1.amount_x  # X sold by trader
        y_received = trade1.amount_y  # Y received by trader

        # Step 2: Trader buys X back (AMM sells X)
        # Use the Y received to buy X back
        quote_buy = amm.get_amount_x_for_y_input(y_received)
        assert quote_buy is not None
        trade2 = amm.execute_buy_x_with_y(y_received, timestamp=1)
        assert trade2 is not None

        x_received = trade2.amount_x  # X received by trader

        # Calculate net result in X terms
        net_x = x_received - x_spent

        # Should lose money (in X terms)
        assert net_x < Decimal("0"), f"Expected loss but got profit: {net_x}"

        # Calculate total fees
        final_snapshot = snapshot_amm_state(amm)
        total_fees_x = final_snapshot.accumulated_fees_x - initial_snapshot.accumulated_fees_x
        total_fees_y = final_snapshot.accumulated_fees_y - initial_snapshot.accumulated_fees_y

        # Convert to X terms
        total_fees_in_x = total_fees_x + total_fees_y / price

        # Loss should approximately equal fees
        expected_loss = -total_fees_in_x
        loss_difference = abs(net_x - expected_loss)
        relative_error = loss_difference / total_fees_in_x if total_fees_in_x > 0 else Decimal("0")

        assert relative_error < Decimal("0.01"), (
            f"Loss {abs(net_x)} doesn't match fees {total_fees_in_x}. "
            f"Relative error: {relative_error * 100}%"
        )

    def test_various_trade_sizes(self):
        """Test that arbitrage is prevented across various trade sizes."""
        amm = create_constant_fee_amm(
            "ConstantFee",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        trade_sizes = [
            Decimal("1"),       # Very small
            Decimal("10"),      # Small
            Decimal("100"),     # Medium
            Decimal("500"),     # Large
            Decimal("1000"),    # Very large
        ]

        for trade_size in trade_sizes:
            # Reset AMM state
            amm.reserve_x = Decimal("10000")
            amm.reserve_y = Decimal("10000")
            amm.accumulated_fees_x = Decimal("0")
            amm.accumulated_fees_y = Decimal("0")

            initial_snapshot = snapshot_amm_state(amm)
            price = initial_snapshot.spot_price

            # Execute buy-sell cycle
            trade1 = amm.execute_sell_x(trade_size, timestamp=0)
            assert trade1 is not None, f"Failed to execute buy for size {trade_size}"

            y_spent = trade1.amount_y
            x_received = trade1.amount_x

            trade2 = amm.execute_buy_x(x_received, timestamp=1)
            assert trade2 is not None, f"Failed to execute sell for size {trade_size}"

            y_received = trade2.amount_y
            net_y = y_received - y_spent

            # Should always lose money
            assert net_y < Decimal("0"), (
                f"Trade size {trade_size}: Expected loss but got {net_y}"
            )

            # Calculate fees
            final_snapshot = snapshot_amm_state(amm)
            fees_x = final_snapshot.accumulated_fees_x
            fees_y = final_snapshot.accumulated_fees_y
            total_fees = fees_y + fees_x * price

            # Verify loss approximately equals fees
            relative_error = abs(abs(net_y) - total_fees) / total_fees if total_fees > 0 else Decimal("0")
            assert relative_error < Decimal("0.01"), (
                f"Trade size {trade_size}: Loss {abs(net_y)} doesn't match fees {total_fees}"
            )


class TestNoArbitrageTieredFees:
    """Test that tiered fee AMMs prevent arbitrage."""

    def test_buy_sell_cycle_two_tiers(self):
        """Test buy-sell cycle with two-tier fee structure."""
        tiers = [
            (Decimal("0"), Decimal("0.003")),    # 30 bps
            (Decimal("100"), Decimal("0.002")),  # 20 bps
        ]
        amm = create_tiered_fee_amm(
            "TwoTier",
            tiers,
            Decimal("10000"),
            Decimal("10000"),
        )

        initial_snapshot = snapshot_amm_state(amm)
        trade_size = Decimal("150")  # Crosses tier boundary
        price = initial_snapshot.spot_price

        # Execute buy-sell cycle
        trade1 = amm.execute_sell_x(trade_size, timestamp=0)
        assert trade1 is not None

        y_spent = trade1.amount_y
        x_received = trade1.amount_x

        trade2 = amm.execute_buy_x(x_received, timestamp=1)
        assert trade2 is not None

        y_received = trade2.amount_y
        net_y = y_received - y_spent

        # Should lose money
        assert net_y < Decimal("0"), f"Expected loss but got profit: {net_y}"

        # Calculate fees
        final_snapshot = snapshot_amm_state(amm)
        fees_x = final_snapshot.accumulated_fees_x
        fees_y = final_snapshot.accumulated_fees_y
        total_fees = fees_y + fees_x * price

        # Verify loss equals fees (within tolerance)
        relative_error = abs(abs(net_y) - total_fees) / total_fees
        assert relative_error < Decimal("0.01"), (
            f"Loss {abs(net_y)} doesn't match fees {total_fees}. "
            f"Relative error: {relative_error * 100}%"
        )

    def test_buy_sell_cycle_three_tiers(self):
        """Test buy-sell cycle with three-tier fee structure."""
        tiers = get_baseline_fee_tiers("conservative")
        amm = create_tiered_fee_amm(
            "ThreeTier",
            tiers,
            Decimal("10000"),
            Decimal("10000"),
        )

        initial_snapshot = snapshot_amm_state(amm)
        trade_size = Decimal("1500")  # Crosses all tier boundaries
        price = initial_snapshot.spot_price

        # Execute buy-sell cycle
        trade1 = amm.execute_sell_x(trade_size, timestamp=0)
        assert trade1 is not None

        y_spent = trade1.amount_y
        x_received = trade1.amount_x

        trade2 = amm.execute_buy_x(x_received, timestamp=1)
        assert trade2 is not None

        y_received = trade2.amount_y
        net_y = y_received - y_spent

        # Should lose money
        assert net_y < Decimal("0"), f"Expected loss but got profit: {net_y}"

        # Calculate fees
        final_snapshot = snapshot_amm_state(amm)
        fees_x = final_snapshot.accumulated_fees_x
        fees_y = final_snapshot.accumulated_fees_y
        total_fees = fees_y + fees_x * price

        # Verify loss equals fees (within tolerance)
        relative_error = abs(abs(net_y) - total_fees) / total_fees
        assert relative_error < Decimal("0.01"), (
            f"Loss {abs(net_y)} doesn't match fees {total_fees}. "
            f"Relative error: {relative_error * 100}%"
        )

    def test_various_sizes_across_tiers(self):
        """Test arbitrage prevention at various sizes across tier boundaries."""
        tiers = [
            (Decimal("0"), Decimal("0.003")),     # 30 bps
            (Decimal("100"), Decimal("0.002")),   # 20 bps
            (Decimal("1000"), Decimal("0.001")),  # 10 bps
        ]
        amm = create_tiered_fee_amm(
            "ThreeTier",
            tiers,
            Decimal("10000"),
            Decimal("10000"),
        )

        # Test sizes: within tiers and crossing boundaries
        trade_sizes = [
            Decimal("50"),    # Tier 0 only
            Decimal("100"),   # Exactly at boundary
            Decimal("150"),   # Crosses tier 0-1
            Decimal("500"),   # Tier 1 mostly
            Decimal("1000"),  # Exactly at boundary
            Decimal("1500"),  # Crosses tier 1-2
            Decimal("2000"),  # All three tiers
        ]

        for trade_size in trade_sizes:
            # Reset AMM
            amm.reserve_x = Decimal("10000")
            amm.reserve_y = Decimal("10000")
            amm.accumulated_fees_x = Decimal("0")
            amm.accumulated_fees_y = Decimal("0")

            initial_snapshot = snapshot_amm_state(amm)
            price = initial_snapshot.spot_price

            # Execute cycle
            trade1 = amm.execute_sell_x(trade_size, timestamp=0)
            if trade1 is None:
                continue

            y_spent = trade1.amount_y
            x_received = trade1.amount_x

            trade2 = amm.execute_buy_x(x_received, timestamp=1)
            if trade2 is None:
                continue

            y_received = trade2.amount_y
            net_y = y_received - y_spent

            # Should lose money
            assert net_y < Decimal("0"), (
                f"Size {trade_size}: Expected loss but got {net_y}"
            )

            # Verify loss equals fees
            final_snapshot = snapshot_amm_state(amm)
            fees_x = final_snapshot.accumulated_fees_x
            fees_y = final_snapshot.accumulated_fees_y
            total_fees = fees_y + fees_x * price

            relative_error = abs(abs(net_y) - total_fees) / total_fees if total_fees > 0 else Decimal("0")
            assert relative_error < Decimal("0.01"), (
                f"Size {trade_size}: Loss {abs(net_y)} doesn't match fees {total_fees}. "
                f"Error: {relative_error * 100}%"
            )


class TestNoArbitrageCrossTierBoundaries:
    """Test that tier boundaries don't create exploitable opportunities."""

    def test_just_below_tier_threshold(self):
        """Test trades just below tier threshold."""
        tiers = [
            (Decimal("0"), Decimal("0.003")),
            (Decimal("100"), Decimal("0.002")),
        ]
        amm = create_tiered_fee_amm(
            "TwoTier",
            tiers,
            Decimal("10000"),
            Decimal("10000"),
        )

        # Trade just below threshold
        trade_size = Decimal("99.99")
        initial_snapshot = snapshot_amm_state(amm)
        price = initial_snapshot.spot_price

        # Execute cycle
        trade1 = amm.execute_sell_x(trade_size, timestamp=0)
        assert trade1 is not None

        y_spent = trade1.amount_y
        x_received = trade1.amount_x

        trade2 = amm.execute_buy_x(x_received, timestamp=1)
        assert trade2 is not None

        y_received = trade2.amount_y
        net_y = y_received - y_spent

        # Should lose money
        assert net_y < Decimal("0")

        # Verify loss equals fees
        final_snapshot = snapshot_amm_state(amm)
        fees_x = final_snapshot.accumulated_fees_x
        fees_y = final_snapshot.accumulated_fees_y
        total_fees = fees_y + fees_x * price

        relative_error = abs(abs(net_y) - total_fees) / total_fees
        assert relative_error < Decimal("0.01")

    def test_just_above_tier_threshold(self):
        """Test trades just above tier threshold."""
        tiers = [
            (Decimal("0"), Decimal("0.003")),
            (Decimal("100"), Decimal("0.002")),
        ]
        amm = create_tiered_fee_amm(
            "TwoTier",
            tiers,
            Decimal("10000"),
            Decimal("10000"),
        )

        # Trade just above threshold
        trade_size = Decimal("100.01")
        initial_snapshot = snapshot_amm_state(amm)
        price = initial_snapshot.spot_price

        # Execute cycle
        trade1 = amm.execute_sell_x(trade_size, timestamp=0)
        assert trade1 is not None

        y_spent = trade1.amount_y
        x_received = trade1.amount_x

        trade2 = amm.execute_buy_x(x_received, timestamp=1)
        assert trade2 is not None

        y_received = trade2.amount_y
        net_y = y_received - y_spent

        # Should lose money
        assert net_y < Decimal("0")

        # Verify loss equals fees
        final_snapshot = snapshot_amm_state(amm)
        fees_x = final_snapshot.accumulated_fees_x
        fees_y = final_snapshot.accumulated_fees_y
        total_fees = fees_y + fees_x * price

        relative_error = abs(abs(net_y) - total_fees) / total_fees
        assert relative_error < Decimal("0.01")

    def test_exactly_at_tier_threshold(self):
        """Test trades exactly at tier threshold."""
        tiers = [
            (Decimal("0"), Decimal("0.003")),
            (Decimal("100"), Decimal("0.002")),
        ]
        amm = create_tiered_fee_amm(
            "TwoTier",
            tiers,
            Decimal("10000"),
            Decimal("10000"),
        )

        # Trade exactly at threshold
        trade_size = Decimal("100")
        initial_snapshot = snapshot_amm_state(amm)
        price = initial_snapshot.spot_price

        # Execute cycle
        trade1 = amm.execute_sell_x(trade_size, timestamp=0)
        assert trade1 is not None

        y_spent = trade1.amount_y
        x_received = trade1.amount_x

        trade2 = amm.execute_buy_x(x_received, timestamp=1)
        assert trade2 is not None

        y_received = trade2.amount_y
        net_y = y_received - y_spent

        # Should lose money
        assert net_y < Decimal("0")

        # Verify loss equals fees
        final_snapshot = snapshot_amm_state(amm)
        fees_x = final_snapshot.accumulated_fees_x
        fees_y = final_snapshot.accumulated_fees_y
        total_fees = fees_y + fees_x * price

        relative_error = abs(abs(net_y) - total_fees) / total_fees
        assert relative_error < Decimal("0.01")

    def test_multiple_boundary_crosses(self):
        """Test that crossing multiple boundaries doesn't create arbitrage."""
        tiers = get_baseline_fee_tiers("conservative")
        amm = create_tiered_fee_amm(
            "ThreeTier",
            tiers,
            Decimal("10000"),
            Decimal("10000"),
        )

        # Trade that crosses both boundaries
        boundary_crossing_sizes = [
            Decimal("99"),    # Just below first boundary
            Decimal("101"),   # Just above first boundary
            Decimal("999"),   # Just below second boundary
            Decimal("1001"),  # Just above second boundary
            Decimal("1500"),  # Well into third tier
        ]

        for trade_size in boundary_crossing_sizes:
            # Reset AMM
            amm.reserve_x = Decimal("10000")
            amm.reserve_y = Decimal("10000")
            amm.accumulated_fees_x = Decimal("0")
            amm.accumulated_fees_y = Decimal("0")

            initial_snapshot = snapshot_amm_state(amm)
            price = initial_snapshot.spot_price

            # Execute cycle
            trade1 = amm.execute_sell_x(trade_size, timestamp=0)
            assert trade1 is not None, f"Failed for size {trade_size}"

            y_spent = trade1.amount_y
            x_received = trade1.amount_x

            trade2 = amm.execute_buy_x(x_received, timestamp=1)
            assert trade2 is not None, f"Failed for size {trade_size}"

            y_received = trade2.amount_y
            net_y = y_received - y_spent

            # Should lose money
            assert net_y < Decimal("0"), (
                f"Size {trade_size}: Expected loss but got {net_y}"
            )


class TestNoArbitrageTwoAMMs:
    """Test that no profitable arbitrage exists across multiple AMMs."""

    def test_constant_vs_constant_same_fees(self):
        """Test arbitrage between two AMMs with identical constant fees."""
        amm1 = create_constant_fee_amm(
            "AMM1",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )
        amm2 = create_constant_fee_amm(
            "AMM2",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        # Attempt cross-AMM arbitrage
        # Buy from AMM1, sell to AMM2
        trade_size = Decimal("100")

        # Buy from AMM1
        trade1 = amm1.execute_sell_x(trade_size, timestamp=0)
        assert trade1 is not None

        y_spent_amm1 = trade1.amount_y
        x_received_amm1 = trade1.amount_x

        # Sell to AMM2
        trade2 = amm2.execute_buy_x(x_received_amm1, timestamp=1)
        assert trade2 is not None

        y_received_amm2 = trade2.amount_y

        # Net result
        net_y = y_received_amm2 - y_spent_amm1

        # Should lose money (fees from both AMMs)
        assert net_y < Decimal("0"), (
            f"Cross-AMM arbitrage should lose money, got {net_y}"
        )

    def test_constant_vs_constant_different_fees(self):
        """Test arbitrage between AMMs with different constant fees."""
        # Lower fee AMM
        amm1 = create_constant_fee_amm(
            "LowFee",
            Decimal("0.002"),  # 20 bps
            Decimal("10000"),
            Decimal("10000"),
        )

        # Higher fee AMM
        amm2 = create_constant_fee_amm(
            "HighFee",
            Decimal("0.005"),  # 50 bps
            Decimal("10000"),
            Decimal("10000"),
        )

        # Try to exploit: buy from low-fee, sell to high-fee
        trade_size = Decimal("100")

        trade1 = amm1.execute_sell_x(trade_size, timestamp=0)
        assert trade1 is not None

        y_spent = trade1.amount_y
        x_received = trade1.amount_x

        trade2 = amm2.execute_buy_x(x_received, timestamp=1)
        assert trade2 is not None

        y_received = trade2.amount_y
        net_y = y_received - y_spent

        # Even buying from low-fee and selling to high-fee should lose money
        # because we pay fees on both sides
        assert net_y < Decimal("0"), (
            f"Should lose money across AMMs with different fees, got {net_y}"
        )

    def test_constant_vs_tiered(self):
        """Test arbitrage between constant fee and tiered fee AMMs."""
        amm1 = create_constant_fee_amm(
            "Constant",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        tiers = [
            (Decimal("0"), Decimal("0.003")),
            (Decimal("100"), Decimal("0.002")),
            (Decimal("1000"), Decimal("0.001")),
        ]
        amm2 = create_tiered_fee_amm(
            "Tiered",
            tiers,
            Decimal("10000"),
            Decimal("10000"),
        )

        # Try large trade that benefits from tiered structure
        trade_size = Decimal("1500")

        # Buy from tiered (lower average fee for large trade)
        trade1 = amm2.execute_sell_x(trade_size, timestamp=0)
        assert trade1 is not None

        y_spent = trade1.amount_y
        x_received = trade1.amount_x

        # Sell to constant
        trade2 = amm1.execute_buy_x(x_received, timestamp=1)
        assert trade2 is not None

        y_received = trade2.amount_y
        net_y = y_received - y_spent

        # Should still lose money
        assert net_y < Decimal("0"), (
            f"Constant vs tiered arbitrage should lose money, got {net_y}"
        )

    def test_tiered_vs_tiered_different_structures(self):
        """Test arbitrage between AMMs with different tiered structures."""
        # Conservative tiers
        amm1 = create_tiered_fee_amm(
            "Conservative",
            get_baseline_fee_tiers("conservative"),
            Decimal("10000"),
            Decimal("10000"),
        )

        # Aggressive tiers
        amm2 = create_tiered_fee_amm(
            "Aggressive",
            get_baseline_fee_tiers("aggressive"),
            Decimal("10000"),
            Decimal("10000"),
        )

        # Try to exploit different tier structures
        trade_size = Decimal("1500")

        # Buy from aggressive (potentially lower fees for large trades)
        trade1 = amm2.execute_sell_x(trade_size, timestamp=0)
        assert trade1 is not None

        y_spent = trade1.amount_y
        x_received = trade1.amount_x

        # Sell to conservative
        trade2 = amm1.execute_buy_x(x_received, timestamp=1)
        assert trade2 is not None

        y_received = trade2.amount_y
        net_y = y_received - y_spent

        # Should lose money
        assert net_y < Decimal("0"), (
            f"Different tier structures shouldn't create arbitrage, got {net_y}"
        )


class TestNoArbitrageExtremeSizes:
    """Test that extreme trade sizes don't create arbitrage opportunities."""

    def test_very_small_trades(self):
        """Test very small trades (< 1 token)."""
        amm = create_constant_fee_amm(
            "SmallTrades",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        very_small_sizes = [
            Decimal("0.01"),
            Decimal("0.1"),
            Decimal("0.5"),
        ]

        for trade_size in very_small_sizes:
            # Reset AMM
            amm.reserve_x = Decimal("10000")
            amm.reserve_y = Decimal("10000")
            amm.accumulated_fees_x = Decimal("0")
            amm.accumulated_fees_y = Decimal("0")

            initial_snapshot = snapshot_amm_state(amm)
            price = initial_snapshot.spot_price

            # Execute cycle
            trade1 = amm.execute_sell_x(trade_size, timestamp=0)
            if trade1 is None:
                continue

            y_spent = trade1.amount_y
            x_received = trade1.amount_x

            trade2 = amm.execute_buy_x(x_received, timestamp=1)
            if trade2 is None:
                continue

            y_received = trade2.amount_y
            net_y = y_received - y_spent

            # Should lose money
            assert net_y < Decimal("0") or abs(net_y) < Decimal("0.000001"), (
                f"Very small trade {trade_size} should lose money, got {net_y}"
            )

    def test_very_large_trades(self):
        """Test very large trades (>> pool size)."""
        amm = create_constant_fee_amm(
            "LargeTrades",
            Decimal("0.003"),
            Decimal("100000"),  # Large pool
            Decimal("100000"),
        )

        large_sizes = [
            Decimal("1000"),
            Decimal("5000"),
            Decimal("10000"),
        ]

        for trade_size in large_sizes:
            # Reset AMM
            amm.reserve_x = Decimal("100000")
            amm.reserve_y = Decimal("100000")
            amm.accumulated_fees_x = Decimal("0")
            amm.accumulated_fees_y = Decimal("0")

            initial_snapshot = snapshot_amm_state(amm)
            price = initial_snapshot.spot_price

            # Execute cycle
            trade1 = amm.execute_sell_x(trade_size, timestamp=0)
            if trade1 is None:
                continue

            y_spent = trade1.amount_y
            x_received = trade1.amount_x

            trade2 = amm.execute_buy_x(x_received, timestamp=1)
            if trade2 is None:
                continue

            y_received = trade2.amount_y
            net_y = y_received - y_spent

            # Should lose money
            assert net_y < Decimal("0"), (
                f"Large trade {trade_size} should lose money, got {net_y}"
            )

    def test_extreme_sizes_with_tiered_fees(self):
        """Test extreme sizes with tiered fee structure."""
        tiers = get_baseline_fee_tiers("conservative")
        amm = create_tiered_fee_amm(
            "TieredExtreme",
            tiers,
            Decimal("100000"),
            Decimal("100000"),
        )

        extreme_sizes = [
            Decimal("0.01"),    # Very small
            Decimal("10000"),   # Very large
        ]

        for trade_size in extreme_sizes:
            # Reset AMM
            amm.reserve_x = Decimal("100000")
            amm.reserve_y = Decimal("100000")
            amm.accumulated_fees_x = Decimal("0")
            amm.accumulated_fees_y = Decimal("0")

            # Execute cycle
            trade1 = amm.execute_sell_x(trade_size, timestamp=0)
            if trade1 is None:
                continue

            y_spent = trade1.amount_y
            x_received = trade1.amount_x

            trade2 = amm.execute_buy_x(x_received, timestamp=1)
            if trade2 is None:
                continue

            y_received = trade2.amount_y
            net_y = y_received - y_spent

            # Should lose money or be approximately zero for dust
            assert net_y < Decimal("0.001"), (
                f"Extreme trade {trade_size} should lose money, got {net_y}"
            )


class TestNoArbitrageAsymmetricPools:
    """Test arbitrage with imbalanced liquidity pools."""

    def test_skewed_x_pool(self):
        """Test arbitrage on pool with more X than Y."""
        amm = create_constant_fee_amm(
            "SkewedX",
            Decimal("0.003"),
            Decimal("20000"),  # More X
            Decimal("5000"),   # Less Y
        )

        initial_snapshot = snapshot_amm_state(amm)
        trade_size = Decimal("100")
        price = initial_snapshot.spot_price

        # Execute cycle
        trade1 = amm.execute_sell_x(trade_size, timestamp=0)
        assert trade1 is not None

        y_spent = trade1.amount_y
        x_received = trade1.amount_x

        trade2 = amm.execute_buy_x(x_received, timestamp=1)
        assert trade2 is not None

        y_received = trade2.amount_y
        net_y = y_received - y_spent

        # Should lose money even with imbalanced pool
        assert net_y < Decimal("0"), (
            f"Skewed pool should prevent arbitrage, got {net_y}"
        )

    def test_skewed_y_pool(self):
        """Test arbitrage on pool with more Y than X."""
        amm = create_constant_fee_amm(
            "SkewedY",
            Decimal("0.003"),
            Decimal("5000"),   # Less X
            Decimal("20000"),  # More Y
        )

        initial_snapshot = snapshot_amm_state(amm)
        trade_size = Decimal("100")
        price = initial_snapshot.spot_price

        # Execute cycle
        trade1 = amm.execute_sell_x(trade_size, timestamp=0)
        assert trade1 is not None

        y_spent = trade1.amount_y
        x_received = trade1.amount_x

        trade2 = amm.execute_buy_x(x_received, timestamp=1)
        assert trade2 is not None

        y_received = trade2.amount_y
        net_y = y_received - y_spent

        # Should lose money
        assert net_y < Decimal("0"), (
            f"Skewed pool should prevent arbitrage, got {net_y}"
        )

    def test_arbitrage_across_imbalanced_pools(self):
        """Test arbitrage between two imbalanced pools."""
        # Pool skewed towards X (low X price)
        amm1 = create_constant_fee_amm(
            "SkewedX",
            Decimal("0.003"),
            Decimal("20000"),
            Decimal("5000"),
        )

        # Pool skewed towards Y (high X price)
        amm2 = create_constant_fee_amm(
            "SkewedY",
            Decimal("0.003"),
            Decimal("5000"),
            Decimal("20000"),
        )

        # Try to exploit price difference
        trade_size = Decimal("100")

        # Buy X from pool with more X (cheaper)
        trade1 = amm1.execute_sell_x(trade_size, timestamp=0)
        assert trade1 is not None

        y_spent = trade1.amount_y
        x_received = trade1.amount_x

        # Sell X to pool with less X (more expensive)
        trade2 = amm2.execute_buy_x(x_received, timestamp=1)
        assert trade2 is not None

        y_received = trade2.amount_y
        net_y = y_received - y_spent

        # Even with price difference, fees should prevent profit
        assert net_y < Decimal("0"), (
            f"Cross-pool arbitrage should lose money despite price difference, got {net_y}"
        )


class TestNoArbitrageVerifyUtility:
    """Test the verify_no_arbitrage utility function."""

    def test_verify_no_arbitrage_simple_cycle(self):
        """Test verify_no_arbitrage with simple buy-sell cycle."""
        amm = create_constant_fee_amm(
            "Test",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        trade_sequence = [
            ("buy", Decimal("100")),   # Trader buys X
            ("sell", Decimal("100")),  # Trader sells X
        ]

        price = Decimal("1.0")

        is_valid, profit = verify_no_arbitrage([amm], trade_sequence, price)

        # Should be valid (no profitable arbitrage)
        assert is_valid, f"Arbitrage detected: profit = {profit}"
        # Profit should be negative (loss)
        assert profit < Decimal("0"), f"Expected loss but got profit: {profit}"

    def test_verify_no_arbitrage_with_tiered_fees(self):
        """Test verify_no_arbitrage with tiered fee AMM."""
        tiers = get_baseline_fee_tiers("conservative")
        amm = create_tiered_fee_amm(
            "Tiered",
            tiers,
            Decimal("10000"),
            Decimal("10000"),
        )

        trade_sequence = [
            ("buy", Decimal("1500")),
            ("sell", Decimal("1500")),
        ]

        price = Decimal("1.0")

        is_valid, profit = verify_no_arbitrage([amm], trade_sequence, price)

        assert is_valid, f"Arbitrage detected with tiered fees: profit = {profit}"
        assert profit < Decimal("0"), f"Expected loss but got profit: {profit}"

    def test_verify_no_arbitrage_multiple_amms(self):
        """Test verify_no_arbitrage with multiple AMMs."""
        amm1 = create_constant_fee_amm(
            "AMM1",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )
        amm2 = create_constant_fee_amm(
            "AMM2",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        trade_sequence = [
            ("buy", Decimal("100")),
            ("sell", Decimal("100")),
        ]

        price = Decimal("1.0")

        # Each AMM processes both trades
        is_valid, profit = verify_no_arbitrage([amm1, amm2], trade_sequence, price)

        assert is_valid, f"Arbitrage detected across AMMs: profit = {profit}"
        assert profit < Decimal("0"), f"Expected loss but got profit: {profit}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
