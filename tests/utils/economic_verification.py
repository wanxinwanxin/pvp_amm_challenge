"""Economic verification utilities for testing AMM correctness.

This module provides utilities to verify fundamental economic properties:
- Value conservation: Total value is preserved across trades
- No arbitrage: Buy-then-sell cycles should not generate profit
- Optimal routing: Router splits should outperform single-AMM execution
- Fee accounting: Fees paid by traders equals fees collected by AMMs
- Symmetry: Identical strategies should produce similar outcomes

All calculations use Decimal precision to ensure accurate financial accounting.
"""

from decimal import Decimal
from typing import Literal, Optional

from amm_competition.core.amm import AMM
from amm_competition.core.trade import TradeInfo
from amm_competition.market.router import OrderRouter, RoutedTrade
from tests.fixtures.economic_fixtures import AMMStateSnapshot, snapshot_amm_state


def verify_value_conservation(
    trades: list[TradeInfo],
    initial_states: list[AMMStateSnapshot],
    final_states: list[AMMStateSnapshot],
    tolerance: Decimal = Decimal("0.0001"),
) -> tuple[bool, str]:
    """Verify that total value is conserved across all trades.

    In a closed system with constant product AMMs, the total value
    (measured at any consistent price) should remain constant, accounting
    for fees collected by the AMMs.

    Value conservation check:
        initial_value + trader_spent = final_value + trader_received + fees

    Args:
        trades: List of executed trades
        initial_states: AMM state snapshots before trades
        final_states: AMM state snapshots after trades
        tolerance: Maximum acceptable relative error (default: 0.01%)

    Returns:
        Tuple of (is_valid, error_message)
        - is_valid: True if value is conserved within tolerance
        - error_message: Empty string if valid, explanation if invalid

    Example:
        >>> is_valid, error = verify_value_conservation(
        ...     trades, initial_states, final_states
        ... )
        >>> assert is_valid, error

    Notes:
        - Uses initial price for valuation to avoid price impact confusion
        - Accounts for fees collected by AMMs
        - Tolerance is relative to total initial value
    """
    if len(initial_states) != len(final_states):
        return False, (
            f"State count mismatch: {len(initial_states)} initial vs "
            f"{len(final_states)} final"
        )

    if not initial_states:
        return True, ""

    if not trades:
        # No trades means no value change expected
        for initial, final in zip(initial_states, final_states):
            if initial.reserve_x != final.reserve_x or initial.reserve_y != final.reserve_y:
                return False, "No trades executed but reserves changed"
        return True, ""

    # Use average initial price as reference for valuation
    total_initial_x = sum(s.total_x for s in initial_states)
    total_initial_y = sum(s.total_y for s in initial_states)

    if total_initial_x == 0:
        return False, "Cannot verify conservation with zero initial X"

    reference_price = total_initial_y / total_initial_x

    # Calculate total initial value (in Y terms)
    initial_value = Decimal("0")
    for state in initial_states:
        initial_value += state.total_y + state.total_x * reference_price

    # Calculate total final value (in Y terms)
    final_value = Decimal("0")
    for state in final_states:
        final_value += state.total_y + state.total_x * reference_price

    # Calculate net trader flows
    # Positive means trader gave to system, negative means system gave to trader
    trader_net_x = Decimal("0")
    trader_net_y = Decimal("0")

    for trade in trades:
        if trade.side == "buy":
            # AMM bought X (trader sold X, received Y)
            trader_net_x += trade.amount_x  # Trader gave X
            trader_net_y -= trade.amount_y  # Trader received Y
        else:
            # AMM sold X (trader bought X, gave Y)
            trader_net_x -= trade.amount_x  # Trader received X
            trader_net_y += trade.amount_y  # Trader gave Y

    # Calculate trader's net contribution in Y terms
    trader_contribution = trader_net_y + trader_net_x * reference_price

    # Value conservation: initial + trader_in = final
    expected_final_value = initial_value + trader_contribution
    value_difference = abs(final_value - expected_final_value)

    # Check relative error
    if initial_value == 0:
        relative_error = value_difference
    else:
        relative_error = value_difference / initial_value

    if relative_error <= tolerance:
        return True, ""

    return False, (
        f"Value not conserved. Initial: {initial_value:.4f} Y, "
        f"Trader contribution: {trader_contribution:.4f} Y, "
        f"Expected final: {expected_final_value:.4f} Y, "
        f"Actual final: {final_value:.4f} Y, "
        f"Difference: {value_difference:.4f} Y ({relative_error * 100:.4f}%), "
        f"Tolerance: {tolerance * 100:.4f}%"
    )


def verify_no_arbitrage(
    amms: list[AMM],
    trade_sequence: list[tuple[str, Decimal]],
    price: Decimal,
    tolerance: Decimal = Decimal("0.0001"),
) -> tuple[bool, Decimal]:
    """Verify that a buy-then-sell cycle does not generate arbitrage profit.

    Executes a sequence of trades and verifies that attempting to extract
    profit through arbitrage results in a net loss equal to fees paid.

    A proper AMM should satisfy:
        profit = -(fees_paid) ± slippage

    Args:
        amms: List of AMMs to test
        trade_sequence: List of (side, amount) tuples to execute
                       side is "buy" or "sell", amount is in X
        price: Reference price for calculating profit (Y per X)
        tolerance: Maximum acceptable relative error (default: 0.01%)

    Returns:
        Tuple of (is_valid, arbitrage_profit)
        - is_valid: True if no profitable arbitrage exists
        - arbitrage_profit: Net profit/loss from the sequence (should be negative)

    Example:
        >>> # Try to arbitrage: buy 100 X, then sell 100 X
        >>> is_valid, profit = verify_no_arbitrage(
        ...     amms, [("buy", Decimal("100")), ("sell", Decimal("100"))], price
        ... )
        >>> assert is_valid
        >>> assert profit < 0  # Should lose money due to fees

    Notes:
        - Uses current AMM state (non-destructive if you snapshot before)
        - Profit should be negative and approximately equal to fees
        - Small positive values may indicate arbitrage opportunity
    """
    if not amms:
        return True, Decimal("0")

    if not trade_sequence:
        return True, Decimal("0")

    # Snapshot initial state
    initial_states = [snapshot_amm_state(amm) for amm in amms]

    # Track net flows
    net_x_received = Decimal("0")  # Positive = received from AMMs
    net_y_spent = Decimal("0")     # Positive = spent to AMMs

    timestamp = 0

    try:
        for side, amount_x in trade_sequence:
            if amount_x <= 0:
                continue

            for amm in amms:
                if side == "buy":
                    # Trader buying X from AMM
                    quote = amm.get_quote_sell_x(amount_x)
                    if quote:
                        trade_info = amm.execute_sell_x(amount_x, timestamp)
                        if trade_info:
                            net_x_received += trade_info.amount_x
                            net_y_spent += trade_info.amount_y
                elif side == "sell":
                    # Trader selling X to AMM
                    trade_info = amm.execute_buy_x(amount_x, timestamp)
                    if trade_info:
                        net_x_received -= trade_info.amount_x
                        net_y_spent -= trade_info.amount_y

                timestamp += 1

        # Calculate arbitrage profit in Y terms
        # Profit = (Y received - Y spent) + (X received) * price
        arbitrage_profit = -net_y_spent + net_x_received * price

        # Calculate total fees paid
        total_fees = Decimal("0")
        final_states = [snapshot_amm_state(amm) for amm in amms]

        for initial, final in zip(initial_states, final_states):
            fees_x = final.accumulated_fees_x - initial.accumulated_fees_x
            fees_y = final.accumulated_fees_y - initial.accumulated_fees_y
            total_fees += fees_y + fees_x * price

        # Arbitrage profit should be negative and approximately equal to -fees
        expected_loss = -total_fees
        difference = abs(arbitrage_profit - expected_loss)

        if total_fees == 0:
            relative_error = difference
        else:
            relative_error = difference / total_fees

        is_valid = arbitrage_profit <= tolerance and relative_error <= tolerance

        return is_valid, arbitrage_profit

    except Exception as e:
        return False, Decimal("0")


def verify_optimal_routing(
    amms: list[AMM],
    trade_size: Decimal,
    direction: Literal["buy", "sell"],
    tolerance: Decimal = Decimal("0.0001"),
) -> tuple[bool, Decimal]:
    """Verify that router split outperforms single-AMM execution.

    Compares the execution quality of optimal routing across multiple AMMs
    versus executing the entire trade on a single AMM. The router should
    always achieve better or equal execution.

    Args:
        amms: List of AMMs to route across
        trade_size: Size of trade to execute (in Y for buy, X for sell)
        direction: "buy" (trader buying X) or "sell" (trader selling X)
        tolerance: Minimum improvement required (default: 0.01%)

    Returns:
        Tuple of (is_better, improvement_amount)
        - is_better: True if routing improves execution
        - improvement_amount: Amount of improvement in Y terms (positive = better)

    Example:
        >>> is_better, improvement = verify_optimal_routing(
        ...     amms, Decimal("1000"), "buy"
        ... )
        >>> assert is_better
        >>> assert improvement >= 0

    Notes:
        - Takes snapshots to avoid mutating AMM state
        - Compares against best single-AMM execution
        - Improvement should be positive or zero (never worse)
        - Zero improvement is acceptable (routing is optimal but not strictly better)
    """
    if not amms:
        return True, Decimal("0")

    if len(amms) == 1:
        # With only one AMM, routing is identical to single execution
        return True, Decimal("0")

    if trade_size <= 0:
        return True, Decimal("0")

    router = OrderRouter()

    # Snapshot initial states
    initial_snapshots = [snapshot_amm_state(amm) for amm in amms]

    try:
        if direction == "buy":
            # Trader buying X with Y
            # Test routing across all AMMs
            splits = router.compute_optimal_split_buy(amms, trade_size)

            total_x_routed = Decimal("0")
            for amm, y_amount in splits:
                if y_amount > 0:
                    quote = amm.get_amount_x_for_y_input(y_amount)
                    if quote:
                        total_x_routed += quote.amount_out

            # Restore states
            for amm, snapshot in zip(amms, initial_snapshots):
                amm.reserve_x = snapshot.reserve_x
                amm.reserve_y = snapshot.reserve_y
                amm.accumulated_fees_x = snapshot.accumulated_fees_x
                amm.accumulated_fees_y = snapshot.accumulated_fees_y

            # Test each single AMM
            best_single_x = Decimal("0")
            for amm in amms:
                quote = amm.get_amount_x_for_y_input(trade_size)
                if quote and quote.amount_out > best_single_x:
                    best_single_x = quote.amount_out

            # Improvement is extra X received
            improvement = total_x_routed - best_single_x

        else:
            # Trader selling X for Y
            # Test routing across all AMMs
            splits = router.compute_optimal_split_sell(amms, trade_size)

            total_y_routed = Decimal("0")
            for amm, x_amount in splits:
                if x_amount > 0:
                    quote = amm.get_quote_buy_x(x_amount)
                    if quote:
                        total_y_routed += quote.amount_out

            # Restore states
            for amm, snapshot in zip(amms, initial_snapshots):
                amm.reserve_x = snapshot.reserve_x
                amm.reserve_y = snapshot.reserve_y
                amm.accumulated_fees_x = snapshot.accumulated_fees_x
                amm.accumulated_fees_y = snapshot.accumulated_fees_y

            # Test each single AMM
            best_single_y = Decimal("0")
            for amm in amms:
                quote = amm.get_quote_buy_x(trade_size)
                if quote and quote.amount_out > best_single_y:
                    best_single_y = quote.amount_out

            # Improvement is extra Y received
            improvement = total_y_routed - best_single_y

        # Routing should never be worse (within tolerance)
        is_better = improvement >= -tolerance

        return is_better, improvement

    except Exception as e:
        return False, Decimal("0")


def calculate_effective_execution_price(
    trades: list[TradeInfo],
    direction: Literal["buy", "sell"],
) -> Decimal:
    """Calculate volume-weighted average execution price across trades.

    Computes the effective price paid/received when executing a trade
    that was split across multiple AMMs.

    Args:
        trades: List of executed trades
        direction: "buy" (trader bought X) or "sell" (trader sold X)

    Returns:
        Effective price in Y per X (Decimal)
        Returns 0 if no trades or zero volume

    Example:
        >>> trades = [trade1, trade2, trade3]  # From router execution
        >>> avg_price = calculate_effective_execution_price(trades, "buy")
        >>> # avg_price is the average Y paid per X received

    Notes:
        - For "buy": price = total_Y_spent / total_X_received
        - For "sell": price = total_Y_received / total_X_sold
        - Accounts for all fees and slippage
        - Returns 0 for empty trade lists
    """
    if not trades:
        return Decimal("0")

    total_x = Decimal("0")
    total_y = Decimal("0")

    for trade in trades:
        if direction == "buy":
            # Trader bought X (AMM sold X)
            # From AMM perspective: side="sell"
            if trade.side == "sell":
                total_x += trade.amount_x  # X received by trader
                total_y += trade.amount_y  # Y paid by trader
        else:
            # Trader sold X (AMM bought X)
            # From AMM perspective: side="buy"
            if trade.side == "buy":
                total_x += trade.amount_x  # X sold by trader
                total_y += trade.amount_y  # Y received by trader

    if total_x == 0:
        return Decimal("0")

    return total_y / total_x


def verify_symmetry(
    pnl_a: Decimal,
    pnl_b: Decimal,
    tolerance_pct: Decimal = Decimal("5"),
) -> tuple[bool, Decimal]:
    """Verify that two identical strategies have similar PnL.

    Checks that two strategies with the same configuration achieve
    similar profit and loss when exposed to the same market conditions.

    Symmetry check:
        |PnL_A - PnL_B| / avg(|PnL_A|, |PnL_B|) <= tolerance

    Args:
        pnl_a: PnL from first strategy
        pnl_b: PnL from second strategy
        tolerance_pct: Maximum acceptable percentage difference (default: 5%)

    Returns:
        Tuple of (is_symmetric, pnl_difference_pct)
        - is_symmetric: True if PnLs are within tolerance
        - pnl_difference_pct: Percentage difference between PnLs

    Example:
        >>> is_symmetric, diff_pct = verify_symmetry(
        ...     Decimal("100.5"), Decimal("102.3"), Decimal("5")
        ... )
        >>> assert is_symmetric
        >>> assert diff_pct < Decimal("5")

    Notes:
        - Uses average absolute value for relative comparison
        - Handles negative PnL correctly
        - Returns 0% difference if both PnLs are zero
    """
    # Handle zero case
    if pnl_a == 0 and pnl_b == 0:
        return True, Decimal("0")

    # Calculate absolute difference
    difference = abs(pnl_a - pnl_b)

    # Calculate average absolute value for normalization
    avg_abs_pnl = (abs(pnl_a) + abs(pnl_b)) / Decimal("2")

    if avg_abs_pnl == 0:
        # Both very close to zero
        if difference <= Decimal("0.01"):  # 1 cent tolerance for near-zero
            return True, Decimal("0")
        else:
            return False, Decimal("100")  # Arbitrary large percentage

    # Calculate percentage difference
    pnl_difference_pct = (difference / avg_abs_pnl) * Decimal("100")

    is_symmetric = pnl_difference_pct <= tolerance_pct

    return is_symmetric, pnl_difference_pct


def verify_fee_accounting(
    amms: list[AMM],
    trades: list[RoutedTrade],
    tolerance: Decimal = Decimal("0.0001"),
) -> tuple[bool, Decimal]:
    """Verify that fees paid by traders equal fees collected by AMMs.

    Ensures proper fee accounting by checking that the total fees
    deducted from trader transactions match the fees accumulated
    by the AMMs.

    Fee conservation check:
        sum(fees_paid_by_traders) = sum(fees_collected_by_amms)

    Args:
        amms: List of AMMs that executed trades
        trades: List of routed trades with fee information
        tolerance: Maximum acceptable absolute difference (default: 0.0001)

    Returns:
        Tuple of (is_valid, fee_difference)
        - is_valid: True if fees match within tolerance
        - fee_difference: Absolute difference between paid and collected fees

    Example:
        >>> is_valid, difference = verify_fee_accounting(amms, trades)
        >>> assert is_valid
        >>> assert difference < Decimal("0.01")

    Notes:
        - Requires initial and final snapshots to calculate collected fees
        - Fees are calculated in Y terms using trade prices
        - Handles both X and Y denominated fees
    """
    if not trades:
        return True, Decimal("0")

    # Create a mapping of AMM names to their snapshots before trades
    amm_snapshots_before = {amm.name: snapshot_amm_state(amm) for amm in amms}

    # Calculate fees paid by traders from trade info
    trader_fees_paid = Decimal("0")

    for routed_trade in trades:
        trade_info = routed_trade.trade_info
        price = trade_info.implied_price  # Y per X

        # Get the AMM's fee for this trade
        amm = routed_trade.amm
        fees = amm.current_fees

        if trade_info.side == "buy":
            # AMM bought X (trader sold X)
            # Fee is taken from X input
            fee_rate = fees.bid_fee
            if fees.bid_tiers:
                fee_rate = fees.effective_bid_fee(trade_info.amount_x)
            fee_x = trade_info.amount_x * fee_rate
            trader_fees_paid += fee_x * price
        else:
            # AMM sold X (trader bought X)
            # Fee is taken from Y input
            fee_rate = fees.ask_fee
            if fees.ask_tiers:
                fee_rate = fees.effective_ask_fee(trade_info.amount_x)
            fee_y = trade_info.amount_y * fee_rate / (Decimal("1") - fee_rate)
            trader_fees_paid += fee_y

    # Calculate fees collected by AMMs
    amm_fees_collected = Decimal("0")

    for amm in amms:
        snapshot_before = amm_snapshots_before[amm.name]
        snapshot_after = snapshot_amm_state(amm)

        # Fees collected in X and Y
        fees_x = snapshot_after.accumulated_fees_x - snapshot_before.accumulated_fees_x
        fees_y = snapshot_after.accumulated_fees_y - snapshot_before.accumulated_fees_y

        # Convert to Y terms using final price
        price = snapshot_after.spot_price
        amm_fees_collected += fees_y + fees_x * price

    # Calculate difference
    fee_difference = abs(trader_fees_paid - amm_fees_collected)

    is_valid = fee_difference <= tolerance

    if not is_valid:
        # Provide detailed error message
        return False, fee_difference

    return True, fee_difference
