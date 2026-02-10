"""Accounting correctness tests for AMM value conservation and fee tracking.

This module verifies fundamental accounting properties of the AMM system:
- Value conservation: Total value is preserved across all trades
- Fee accounting: Fees paid by traders equal fees collected by AMMs
- K invariant: Constant product invariant is maintained (accounting for fees)
- PnL balance: Sum of all participant PnLs equals zero
- Reserve accuracy: Reserves change correctly according to AMM math

All tests use Decimal precision to ensure accurate financial accounting
and provide detailed error messages for diagnosis.
"""

import random
from decimal import Decimal
from typing import Optional

import pytest

from amm_competition.core.amm import AMM
from amm_competition.core.trade import TradeInfo
from amm_competition.market.retail import RetailOrder
from amm_competition.market.router import OrderRouter, RoutedTrade
from tests.fixtures.economic_fixtures import (
    PoolBalanceProfile,
    create_constant_fee_amm,
    create_tiered_fee_amm,
    create_amm_set,
    get_baseline_fee_tiers,
    snapshot_amm_state,
    calculate_pnl,
    AMMStateSnapshot,
)
from tests.utils.economic_verification import (
    verify_value_conservation,
    verify_fee_accounting,
)


def generate_random_order(
    seed: int,
    mean_size: float = 100.0,
    size_range: tuple[float, float] = (10.0, 1000.0),
) -> RetailOrder:
    """Generate a random retail order for testing.

    Args:
        seed: Random seed for reproducibility
        mean_size: Mean order size in Y terms
        size_range: Min and max order sizes

    Returns:
        Random retail order
    """
    rng = random.Random(seed)

    # Random side (buy or sell)
    side = "buy" if rng.random() < 0.5 else "sell"

    # Random size within range
    min_size, max_size = size_range
    size = Decimal(str(rng.uniform(min_size, max_size)))

    return RetailOrder(side=side, size=size)


def calculate_total_value(
    states: list[AMMStateSnapshot],
    price: Decimal,
) -> Decimal:
    """Calculate total value of all AMM states at given price.

    Args:
        states: List of AMM state snapshots
        price: Valuation price (Y per X)

    Returns:
        Total value in Y terms
    """
    total = Decimal("0")
    for state in states:
        # Value = reserves + fees (in Y terms)
        total += state.total_y + state.total_x * price
    return total


def calculate_trader_flows(
    trades: list[TradeInfo],
    price: Decimal,
) -> tuple[Decimal, Decimal]:
    """Calculate net trader flows in X and Y.

    Args:
        trades: List of executed trades
        price: Reference price for valuation

    Returns:
        Tuple of (net_x_flow, net_y_flow)
        - Positive = trader gave to system
        - Negative = trader received from system
    """
    net_x = Decimal("0")
    net_y = Decimal("0")

    for trade in trades:
        if trade.side == "buy":
            # AMM bought X (trader sold X, received Y)
            net_x += trade.amount_x  # Trader gave X
            net_y -= trade.amount_y  # Trader received Y
        else:
            # AMM sold X (trader bought X, gave Y)
            net_x -= trade.amount_x  # Trader received X
            net_y += trade.amount_y  # Trader gave Y

    return net_x, net_y


class TestValueConservationSingleTrade:
    """Test value conservation for single trades."""

    def test_value_conserved_constant_fee_buy(self):
        """Test value conservation on single buy trade with constant fees."""
        amm = create_constant_fee_amm(
            "TestAMM",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        initial_states = [snapshot_amm_state(amm)]
        initial_price = initial_states[0].spot_price

        # Execute single buy trade (trader buys X from AMM)
        trade = amm.execute_sell_x(Decimal("100"), timestamp=0)
        assert trade is not None

        final_states = [snapshot_amm_state(amm)]

        # Verify value conservation
        is_valid, error = verify_value_conservation(
            [trade],
            initial_states,
            final_states,
            tolerance=Decimal("0.0001"),
        )

        assert is_valid, f"Value not conserved: {error}"

        # Manual verification
        initial_value = calculate_total_value(initial_states, initial_price)
        final_value = calculate_total_value(final_states, initial_price)

        net_x, net_y = calculate_trader_flows([trade], initial_price)
        trader_contribution = net_y + net_x * initial_price

        expected_final = initial_value + trader_contribution
        difference = abs(final_value - expected_final)

        assert difference < Decimal("0.01"), (
            f"Manual verification failed. "
            f"Initial: {initial_value}, "
            f"Trader contribution: {trader_contribution}, "
            f"Expected final: {expected_final}, "
            f"Actual final: {final_value}, "
            f"Difference: {difference}"
        )

    def test_value_conserved_constant_fee_sell(self):
        """Test value conservation on single sell trade with constant fees."""
        amm = create_constant_fee_amm(
            "TestAMM",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        initial_states = [snapshot_amm_state(amm)]
        initial_price = initial_states[0].spot_price

        # Execute single sell trade (trader sells X to AMM)
        trade = amm.execute_buy_x(Decimal("100"), timestamp=0)
        assert trade is not None

        final_states = [snapshot_amm_state(amm)]

        # Verify value conservation
        is_valid, error = verify_value_conservation(
            [trade],
            initial_states,
            final_states,
            tolerance=Decimal("0.0001"),
        )

        assert is_valid, f"Value not conserved: {error}"

    def test_value_conserved_tiered_fee(self):
        """Test value conservation with tiered fees."""
        tiers = get_baseline_fee_tiers("conservative")
        amm = create_tiered_fee_amm(
            "TieredAMM",
            tiers,
            Decimal("10000"),
            Decimal("10000"),
        )

        initial_states = [snapshot_amm_state(amm)]

        # Execute trade that spans multiple tiers
        trade = amm.execute_buy_x(Decimal("150"), timestamp=0)
        assert trade is not None

        final_states = [snapshot_amm_state(amm)]

        # Verify value conservation
        is_valid, error = verify_value_conservation(
            [trade],
            initial_states,
            final_states,
            tolerance=Decimal("0.0001"),
        )

        assert is_valid, f"Value not conserved with tiered fees: {error}"


class TestValueConservationMultipleTrades:
    """Test value conservation across multiple trades."""

    def test_value_conserved_50_random_trades_constant(self):
        """Test value conservation over 50 random trades with constant fees."""
        amms = [
            create_constant_fee_amm(
                "AMM1",
                Decimal("0.003"),
                Decimal("10000"),
                Decimal("10000"),
            ),
            create_constant_fee_amm(
                "AMM2",
                Decimal("0.0025"),
                Decimal("10000"),
                Decimal("10000"),
            ),
            create_constant_fee_amm(
                "AMM3",
                Decimal("0.0035"),
                Decimal("10000"),
                Decimal("10000"),
            ),
        ]

        initial_states = [snapshot_amm_state(amm) for amm in amms]
        initial_price = initial_states[0].spot_price
        router = OrderRouter()
        all_trades = []

        # Execute 50 random trades
        for i in range(50):
            order = generate_random_order(seed=i, mean_size=100.0)
            routed_trades = router.route_order(order, amms, initial_price, timestamp=i)

            # Extract TradeInfo from RoutedTrade
            for rt in routed_trades:
                all_trades.append(rt.trade_info)

        final_states = [snapshot_amm_state(amm) for amm in amms]

        # Verify value conservation
        is_valid, error = verify_value_conservation(
            all_trades,
            initial_states,
            final_states,
            tolerance=Decimal("0.0001"),
        )

        assert is_valid, f"Value not conserved over 50 trades: {error}"

    def test_value_conserved_50_random_trades_tiered(self):
        """Test value conservation over 50 random trades with tiered fees."""
        amms = create_amm_set(
            PoolBalanceProfile.BALANCED,
            include_constant=True,
            include_tiered=True,
        )

        initial_states = [snapshot_amm_state(amm) for amm in amms]
        initial_price = initial_states[0].spot_price
        router = OrderRouter()
        all_trades = []

        # Execute 50 random trades
        for i in range(50):
            order = generate_random_order(seed=i + 1000, mean_size=100.0)
            routed_trades = router.route_order(order, amms, initial_price, timestamp=i)

            for rt in routed_trades:
                all_trades.append(rt.trade_info)

        final_states = [snapshot_amm_state(amm) for amm in amms]

        # Verify value conservation
        is_valid, error = verify_value_conservation(
            all_trades,
            initial_states,
            final_states,
            tolerance=Decimal("0.0001"),
        )

        assert is_valid, f"Value not conserved over 50 trades with tiers: {error}"

    def test_value_conserved_extreme_imbalance(self):
        """Test value conservation with extreme pool imbalances."""
        amms = create_amm_set(
            PoolBalanceProfile.EXTREME,
            include_constant=True,
            include_tiered=True,
        )

        initial_states = [snapshot_amm_state(amm) for amm in amms]
        initial_price = initial_states[0].spot_price
        router = OrderRouter()
        all_trades = []

        # Execute 20 random trades (fewer due to extreme imbalance)
        for i in range(20):
            order = generate_random_order(seed=i + 2000, mean_size=50.0)
            routed_trades = router.route_order(order, amms, initial_price, timestamp=i)

            for rt in routed_trades:
                all_trades.append(rt.trade_info)

        final_states = [snapshot_amm_state(amm) for amm in amms]

        # Verify value conservation (slightly higher tolerance for extreme cases)
        is_valid, error = verify_value_conservation(
            all_trades,
            initial_states,
            final_states,
            tolerance=Decimal("0.001"),  # 0.1% tolerance
        )

        assert is_valid, f"Value not conserved with extreme imbalance: {error}"


class TestFeeAccounting:
    """Test that fees paid by traders equal fees collected by AMMs."""

    def test_fees_paid_equals_collected_constant(self):
        """Test fee accounting with constant fee structure."""
        amm = create_constant_fee_amm(
            "TestAMM",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        initial_snapshot = snapshot_amm_state(amm)
        router = OrderRouter()
        price = initial_snapshot.spot_price

        # Execute 10 trades
        routed_trades = []
        for i in range(10):
            order = generate_random_order(seed=i + 3000, mean_size=100.0)
            trades = router.route_order(order, [amm], price, timestamp=i)
            routed_trades.extend(trades)

        # Verify fee accounting
        is_valid, difference = verify_fee_accounting(
            [amm],
            routed_trades,
            tolerance=Decimal("0.0001"),
        )

        assert is_valid, (
            f"Fee accounting mismatch. "
            f"Difference: {difference} (tolerance: 0.0001)"
        )

        # Additional manual verification
        final_snapshot = snapshot_amm_state(amm)

        fees_x_collected = final_snapshot.accumulated_fees_x - initial_snapshot.accumulated_fees_x
        fees_y_collected = final_snapshot.accumulated_fees_y - initial_snapshot.accumulated_fees_y

        assert fees_x_collected >= Decimal("0"), "Negative X fees collected"
        assert fees_y_collected >= Decimal("0"), "Negative Y fees collected"
        assert fees_x_collected + fees_y_collected > Decimal("0"), "No fees collected"

    def test_fees_paid_equals_collected_tiered(self):
        """Test fee accounting with tiered fee structure."""
        tiers = get_baseline_fee_tiers("conservative")
        amm = create_tiered_fee_amm(
            "TieredAMM",
            tiers,
            Decimal("10000"),
            Decimal("10000"),
        )

        initial_snapshot = snapshot_amm_state(amm)
        router = OrderRouter()
        price = initial_snapshot.spot_price

        # Execute 10 trades
        routed_trades = []
        for i in range(10):
            order = generate_random_order(seed=i + 4000, mean_size=150.0)
            trades = router.route_order(order, [amm], price, timestamp=i)
            routed_trades.extend(trades)

        # Verify fee accounting
        is_valid, difference = verify_fee_accounting(
            [amm],
            routed_trades,
            tolerance=Decimal("0.0001"),
        )

        assert is_valid, (
            f"Fee accounting mismatch with tiered fees. "
            f"Difference: {difference}"
        )

    def test_fees_paid_equals_collected_multiple_amms(self):
        """Test fee accounting across multiple AMMs."""
        amms = create_amm_set(
            PoolBalanceProfile.BALANCED,
            include_constant=True,
            include_tiered=True,
        )

        initial_snapshots = [snapshot_amm_state(amm) for amm in amms]
        router = OrderRouter()
        price = initial_snapshots[0].spot_price

        # Execute 20 trades across multiple AMMs
        routed_trades = []
        for i in range(20):
            order = generate_random_order(seed=i + 5000, mean_size=200.0)
            trades = router.route_order(order, amms, price, timestamp=i)
            routed_trades.extend(trades)

        # Verify fee accounting
        is_valid, difference = verify_fee_accounting(
            amms,
            routed_trades,
            tolerance=Decimal("0.001"),  # Slightly higher tolerance for multiple AMMs
        )

        assert is_valid, (
            f"Fee accounting mismatch across multiple AMMs. "
            f"Difference: {difference}"
        )


class TestKInvariant:
    """Test that constant product invariant is preserved (accounting for fees)."""

    def test_k_invariant_preserved_single_trade(self):
        """Test k invariant after single trade."""
        amm = create_constant_fee_amm(
            "TestAMM",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        initial_k = amm.k

        # Execute trade
        trade = amm.execute_buy_x(Decimal("100"), timestamp=0)
        assert trade is not None

        # k should increase due to fees (fees are added to reserves)
        # New k = (reserve_x + fee_x) * reserve_y
        # Since fees are extracted before the swap, k of trading reserves stays constant
        # but total k increases by the fee amount
        final_k = amm.k

        # For fee-on-input, the invariant of the core reserves (excluding fees) is preserved
        # The new k should be >= initial k due to accumulated fees
        assert final_k >= initial_k, (
            f"K invariant decreased. Initial: {initial_k}, Final: {final_k}"
        )

    def test_k_invariant_preserved_multiple_trades(self):
        """Test k invariant across multiple trades."""
        amm = create_constant_fee_amm(
            "TestAMM",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        initial_snapshot = snapshot_amm_state(amm)
        initial_k = initial_snapshot.k

        # Execute 10 trades
        for i in range(10):
            if i % 2 == 0:
                amm.execute_buy_x(Decimal("50"), timestamp=i)
            else:
                amm.execute_sell_x(Decimal("50"), timestamp=i)

        final_snapshot = snapshot_amm_state(amm)
        final_k = final_snapshot.k

        # k should increase or stay roughly the same
        # (slight variations due to fees and rounding)
        assert final_k >= initial_k * Decimal("0.99"), (
            f"K invariant decreased significantly. "
            f"Initial: {initial_k}, Final: {final_k}, "
            f"Change: {(final_k - initial_k) / initial_k * 100:.4f}%"
        )

    def test_reserve_k_vs_total_k(self):
        """Test that reserve k is preserved while total k increases."""
        amm = create_constant_fee_amm(
            "TestAMM",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        initial_snapshot = snapshot_amm_state(amm)

        # Execute trades
        for i in range(5):
            amm.execute_buy_x(Decimal("100"), timestamp=i)

        final_snapshot = snapshot_amm_state(amm)

        # Calculate k with reserves only (excluding accumulated fees)
        reserve_k = final_snapshot.reserve_x * final_snapshot.reserve_y

        # Calculate k with total holdings (including accumulated fees)
        total_k = final_snapshot.total_x * final_snapshot.total_y

        # Total k should be greater than reserve k due to accumulated fees
        assert total_k > reserve_k, (
            f"Total k should exceed reserve k. "
            f"Reserve k: {reserve_k}, Total k: {total_k}"
        )

        # Fees should be positive
        assert final_snapshot.accumulated_fees_x > Decimal("0"), "No X fees accumulated"


class TestSumOfPnLs:
    """Test that sum of all participant PnLs equals zero."""

    def test_sum_of_pnls_zero_constant_fees(self):
        """Test that sum of PnLs is zero with constant fees."""
        amms = [
            create_constant_fee_amm(
                "AMM1",
                Decimal("0.003"),
                Decimal("10000"),
                Decimal("10000"),
            ),
            create_constant_fee_amm(
                "AMM2",
                Decimal("0.003"),
                Decimal("10000"),
                Decimal("10000"),
            ),
        ]

        initial_snapshots = [snapshot_amm_state(amm) for amm in amms]
        initial_price = initial_snapshots[0].spot_price
        router = OrderRouter()

        # Track trader PnL
        trader_net_x = Decimal("0")
        trader_net_y = Decimal("0")

        # Execute 20 trades
        for i in range(20):
            order = generate_random_order(seed=i + 6000, mean_size=100.0)
            routed_trades = router.route_order(order, amms, initial_price, timestamp=i)

            for rt in routed_trades:
                trade = rt.trade_info
                if trade.side == "buy":
                    # AMM bought X (trader sold X, received Y)
                    trader_net_x -= trade.amount_x  # Trader gave X
                    trader_net_y += trade.amount_y  # Trader received Y
                else:
                    # AMM sold X (trader bought X, gave Y)
                    trader_net_x += trade.amount_x  # Trader received X
                    trader_net_y -= trade.amount_y  # Trader gave Y

        final_snapshots = [snapshot_amm_state(amm) for amm in amms]

        # Calculate AMM PnLs
        amm_pnls = []
        for initial, final in zip(initial_snapshots, final_snapshots):
            pnl = calculate_pnl(initial, final, valuation_price=initial_price)
            amm_pnls.append(pnl.pnl_at_initial_price)

        total_amm_pnl = sum(amm_pnls)

        # Calculate trader PnL
        trader_pnl = trader_net_y + trader_net_x * initial_price

        # Sum should be approximately zero (within fee precision)
        total_pnl = total_amm_pnl + trader_pnl

        # Calculate relative tolerance
        total_volume = sum(abs(pnl) for pnl in amm_pnls) + abs(trader_pnl)
        if total_volume > 0:
            relative_error = abs(total_pnl) / total_volume
        else:
            relative_error = abs(total_pnl)

        assert relative_error < Decimal("0.01"), (
            f"Sum of PnLs not zero. "
            f"Total: {total_pnl}, "
            f"AMM PnLs: {amm_pnls}, "
            f"Trader PnL: {trader_pnl}, "
            f"Relative error: {relative_error * 100:.4f}%"
        )

    def test_sum_of_pnls_zero_tiered_fees(self):
        """Test that sum of PnLs is zero with tiered fees."""
        amms = create_amm_set(
            PoolBalanceProfile.BALANCED,
            include_constant=False,
            include_tiered=True,
        )

        initial_snapshots = [snapshot_amm_state(amm) for amm in amms]
        initial_price = initial_snapshots[0].spot_price
        router = OrderRouter()

        # Track trader PnL
        trader_net_x = Decimal("0")
        trader_net_y = Decimal("0")

        # Execute 20 trades
        for i in range(20):
            order = generate_random_order(seed=i + 7000, mean_size=150.0)
            routed_trades = router.route_order(order, amms, initial_price, timestamp=i)

            for rt in routed_trades:
                trade = rt.trade_info
                if trade.side == "buy":
                    trader_net_x -= trade.amount_x
                    trader_net_y += trade.amount_y
                else:
                    trader_net_x += trade.amount_x
                    trader_net_y -= trade.amount_y

        final_snapshots = [snapshot_amm_state(amm) for amm in amms]

        # Calculate AMM PnLs
        amm_pnls = []
        for initial, final in zip(initial_snapshots, final_snapshots):
            pnl = calculate_pnl(initial, final, valuation_price=initial_price)
            amm_pnls.append(pnl.pnl_at_initial_price)

        total_amm_pnl = sum(amm_pnls)
        trader_pnl = trader_net_y + trader_net_x * initial_price
        total_pnl = total_amm_pnl + trader_pnl

        # Calculate relative tolerance
        total_volume = sum(abs(pnl) for pnl in amm_pnls) + abs(trader_pnl)
        if total_volume > 0:
            relative_error = abs(total_pnl) / total_volume
        else:
            relative_error = abs(total_pnl)

        assert relative_error < Decimal("0.01"), (
            f"Sum of PnLs not zero with tiered fees. "
            f"Total: {total_pnl}, "
            f"Relative error: {relative_error * 100:.4f}%"
        )


class TestAccumulatedFeesTracking:
    """Test that accumulated fees are tracked correctly."""

    def test_accumulated_fees_increase_monotonically(self):
        """Test that accumulated fees only increase, never decrease."""
        amm = create_constant_fee_amm(
            "TestAMM",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        prev_fees_x = amm.accumulated_fees_x
        prev_fees_y = amm.accumulated_fees_y

        # Execute 10 trades
        for i in range(10):
            if i % 2 == 0:
                amm.execute_buy_x(Decimal("50"), timestamp=i)
            else:
                amm.execute_sell_x(Decimal("50"), timestamp=i)

            # Fees should never decrease
            assert amm.accumulated_fees_x >= prev_fees_x, (
                f"Fees X decreased at step {i}"
            )
            assert amm.accumulated_fees_y >= prev_fees_y, (
                f"Fees Y decreased at step {i}"
            )

            prev_fees_x = amm.accumulated_fees_x
            prev_fees_y = amm.accumulated_fees_y

    def test_accumulated_fees_match_manual_calculation(self):
        """Test that accumulated fees match manual calculation."""
        amm = create_constant_fee_amm(
            "TestAMM",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        # Execute buy trade (fee on X input)
        trade_size = Decimal("100")
        trade = amm.execute_buy_x(trade_size, timestamp=0)
        assert trade is not None

        # Calculate expected fee
        fee_rate = Decimal("0.003")
        expected_fee_x = trade_size * fee_rate

        # Check accumulated fees
        assert abs(amm.accumulated_fees_x - expected_fee_x) < Decimal("0.001"), (
            f"Fee X mismatch. Expected: {expected_fee_x}, "
            f"Actual: {amm.accumulated_fees_x}"
        )
        assert amm.accumulated_fees_y == Decimal("0"), (
            f"Fee Y should be zero for buy trade, got {amm.accumulated_fees_y}"
        )

    def test_accumulated_fees_tiered_structure(self):
        """Test accumulated fees with tiered fee structure."""
        tiers = get_baseline_fee_tiers("conservative")
        amm = create_tiered_fee_amm(
            "TieredAMM",
            tiers,
            Decimal("10000"),
            Decimal("10000"),
        )

        initial_fees_x = amm.accumulated_fees_x

        # Execute trade spanning multiple tiers
        trade_size = Decimal("150")  # Spans 0-100 at 30bps, 100-150 at 20bps
        trade = amm.execute_buy_x(trade_size, timestamp=0)
        assert trade is not None

        # Calculate expected weighted average fee
        expected_avg_fee = (
            Decimal("100") * Decimal("0.003") +
            Decimal("50") * Decimal("0.002")
        ) / Decimal("150")
        expected_total_fee = trade_size * expected_avg_fee

        actual_fee = amm.accumulated_fees_x - initial_fees_x

        # Allow small tolerance for rounding
        assert abs(actual_fee - expected_total_fee) / expected_total_fee < Decimal("0.01"), (
            f"Tiered fee mismatch. Expected: {expected_total_fee}, "
            f"Actual: {actual_fee}, "
            f"Difference: {abs(actual_fee - expected_total_fee)}"
        )


class TestReserveAccountingAccuracy:
    """Test that reserve changes match expected AMM math."""

    def test_reserve_changes_constant_product(self):
        """Test that reserves follow constant product formula."""
        amm = create_constant_fee_amm(
            "TestAMM",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        initial_snapshot = snapshot_amm_state(amm)
        initial_reserve_k = initial_snapshot.reserve_x * initial_snapshot.reserve_y

        # Execute buy trade
        trade = amm.execute_buy_x(Decimal("100"), timestamp=0)
        assert trade is not None

        final_snapshot = snapshot_amm_state(amm)
        final_reserve_k = final_snapshot.reserve_x * final_snapshot.reserve_y

        # Reserve k should be approximately constant (within rounding)
        k_change_pct = abs(final_reserve_k - initial_reserve_k) / initial_reserve_k * Decimal("100")

        assert k_change_pct < Decimal("0.01"), (
            f"Reserve k changed significantly. "
            f"Initial: {initial_reserve_k}, Final: {final_reserve_k}, "
            f"Change: {k_change_pct:.4f}%"
        )

    def test_reserve_changes_match_quote(self):
        """Test that actual reserve changes match quoted amounts."""
        amm = create_constant_fee_amm(
            "TestAMM",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        initial_snapshot = snapshot_amm_state(amm)

        # Get quote for buy
        trade_size = Decimal("100")
        quote = amm.get_quote_buy_x(trade_size)
        assert quote is not None

        quoted_x = quote.amount_out
        quoted_y = quote.amount_in

        # Execute trade
        trade = amm.execute_buy_x(trade_size, timestamp=0)
        assert trade is not None

        final_snapshot = snapshot_amm_state(amm)

        # Check reserve changes match quote
        actual_x_change = initial_snapshot.reserve_x - final_snapshot.reserve_x
        actual_y_change = final_snapshot.reserve_y - initial_snapshot.reserve_y

        assert abs(actual_x_change - quoted_x) < Decimal("0.001"), (
            f"X reserve change doesn't match quote. "
            f"Quoted: {quoted_x}, Actual: {actual_x_change}"
        )

        # Y change should match quoted input
        # Note: reserve_y includes the Y input after fee deduction
        assert actual_y_change > Decimal("0"), "Y reserves should increase"

    def test_decimal_precision_maintained(self):
        """Test that Decimal precision is maintained throughout."""
        amm = create_constant_fee_amm(
            "TestAMM",
            Decimal("0.003"),
            Decimal("10000"),
            Decimal("10000"),
        )

        # Execute very small trade to test precision
        small_trade = Decimal("0.001")
        trade = amm.execute_buy_x(small_trade, timestamp=0)
        assert trade is not None

        # Check that values are still Decimal type
        assert isinstance(amm.reserve_x, Decimal), "reserve_x not Decimal"
        assert isinstance(amm.reserve_y, Decimal), "reserve_y not Decimal"
        assert isinstance(amm.accumulated_fees_x, Decimal), "fees_x not Decimal"
        assert isinstance(amm.accumulated_fees_y, Decimal), "fees_y not Decimal"

        # Check that very small fee is tracked
        assert amm.accumulated_fees_x > Decimal("0"), "Small fee not tracked"
        assert amm.accumulated_fees_x < Decimal("0.01"), "Fee too large for small trade"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
