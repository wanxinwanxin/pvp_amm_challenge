"""Framework for comparing old and new router implementations.

Provides utilities to run parallel simulations and compare routing decisions
between the old router (constant fees only) and the new router (with tiered
fee support and constant fee fallback).

Key capabilities:
- Wrapper classes for clean API access to both routers
- Comparison functions for splits, prices, and execution results
- Parallel simulation runner for matched trades
- Decimal-precision comparison utilities
"""

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from amm_competition.core.amm import AMM
from amm_competition.market.retail import RetailOrder
from amm_competition.market.router import OrderRouter as NewOrderRouter
from tests.utils.old_router import OrderRouter as OldOrderRouter


@dataclass
class SplitComparison:
    """Comparison of split decisions between routers.

    Captures differences in how each router allocated order flow
    across AMMs. All differences use Decimal precision.
    """
    amm_name: str
    old_amount: Decimal
    new_amount: Decimal
    absolute_diff: Decimal
    relative_diff_pct: Decimal  # Percentage difference

    @property
    def matches(self) -> bool:
        """Check if splits match within tolerance (0.01%)."""
        return abs(self.relative_diff_pct) < Decimal("0.01")


@dataclass
class ExecutionComparison:
    """Comparison of execution results between routers.

    Compares final execution outcomes including prices, amounts,
    and final AMM states.
    """
    order_side: str
    order_size: Decimal

    # Execution prices (weighted average across all AMMs)
    old_execution_price: Decimal
    new_execution_price: Decimal
    price_diff: Decimal
    price_diff_pct: Decimal

    # Total amounts executed
    old_total_x: Decimal
    new_total_x: Decimal
    old_total_y: Decimal
    new_total_y: Decimal

    # Split comparisons for each AMM
    split_comparisons: list[SplitComparison]

    # Final AMM state comparisons
    reserve_diffs: dict[str, tuple[Decimal, Decimal]]  # name -> (x_diff, y_diff)

    @property
    def prices_match(self) -> bool:
        """Check if execution prices match within tolerance (1e-10)."""
        return abs(self.price_diff) < Decimal("1e-10")

    @property
    def splits_match(self) -> bool:
        """Check if all splits match within tolerance."""
        return all(sc.matches for sc in self.split_comparisons)

    @property
    def reserves_match(self) -> bool:
        """Check if final reserves match within tolerance (1e-10)."""
        for x_diff, y_diff in self.reserve_diffs.values():
            if abs(x_diff) >= Decimal("1e-10") or abs(y_diff) >= Decimal("1e-10"):
                return False
        return True


class OldRouter:
    """Wrapper around old router implementation.

    Provides a clean interface for testing that matches the new router API.
    The old router only supports constant fees - it uses the ask_fee/bid_fee
    from FeeQuote and ignores any tier information.
    """

    def __init__(self):
        self._router = OldOrderRouter()

    def compute_optimal_split_buy(
        self,
        amms: list[AMM],
        total_y: Decimal
    ) -> list[tuple[AMM, Decimal]]:
        """Compute optimal Y split for buying X.

        Args:
            amms: List of AMMs to split across
            total_y: Total Y amount to spend

        Returns:
            List of (AMM, Y_amount) tuples
        """
        return self._router.compute_optimal_split_buy(amms, total_y)

    def compute_optimal_split_sell(
        self,
        amms: list[AMM],
        total_x: Decimal
    ) -> list[tuple[AMM, Decimal]]:
        """Compute optimal X split for selling X.

        Args:
            amms: List of AMMs to split across
            total_x: Total X amount to sell

        Returns:
            List of (AMM, X_amount) tuples
        """
        return self._router.compute_optimal_split_sell(amms, total_x)

    def route_order(
        self,
        order: RetailOrder,
        amms: list[AMM],
        fair_price: Decimal,
        timestamp: int,
    ) -> list:
        """Route a retail order across AMMs.

        Args:
            order: Retail order to route
            amms: List of AMMs to route to
            fair_price: Current fair price
            timestamp: Current simulation step

        Returns:
            List of RoutedTrade objects
        """
        return self._router.route_order(order, amms, fair_price, timestamp)


class NewRouter:
    """Wrapper around new router implementation.

    Provides a clean interface for testing. The new router supports both
    constant fees (fast path) and tiered fees (iterative refinement).
    """

    def __init__(self):
        self._router = NewOrderRouter()

    def compute_optimal_split_buy(
        self,
        amms: list[AMM],
        total_y: Decimal
    ) -> list[tuple[AMM, Decimal]]:
        """Compute optimal Y split for buying X.

        Args:
            amms: List of AMMs to split across
            total_y: Total Y amount to spend

        Returns:
            List of (AMM, Y_amount) tuples
        """
        return self._router.compute_optimal_split_buy(amms, total_y)

    def compute_optimal_split_sell(
        self,
        amms: list[AMM],
        total_x: Decimal
    ) -> list[tuple[AMM, Decimal]]:
        """Compute optimal X split for selling X.

        Args:
            amms: List of AMMs to split across
            total_x: Total X amount to sell

        Returns:
            List of (AMM, X_amount) tuples
        """
        return self._router.compute_optimal_split_sell(amms, total_x)

    def route_order(
        self,
        order: RetailOrder,
        amms: list[AMM],
        fair_price: Decimal,
        timestamp: int,
    ) -> list:
        """Route a retail order across AMMs.

        Args:
            order: Retail order to route
            amms: List of AMMs to route to
            fair_price: Current fair price
            timestamp: Current simulation step

        Returns:
            List of RoutedTrade objects
        """
        return self._router.route_order(order, amms, fair_price, timestamp)


def compare_splits(
    old_splits: list[tuple[AMM, Decimal]],
    new_splits: list[tuple[AMM, Decimal]],
) -> list[SplitComparison]:
    """Compare split decisions from both routers.

    Args:
        old_splits: Splits from old router
        new_splits: Splits from new router

    Returns:
        List of SplitComparison objects, one per AMM

    Raises:
        ValueError: If splits don't cover the same set of AMMs
    """
    # Build dictionaries for easy lookup
    old_dict = {amm.name: amount for amm, amount in old_splits}
    new_dict = {amm.name: amount for amm, amount in new_splits}

    # Verify same set of AMMs
    old_names = set(old_dict.keys())
    new_names = set(new_dict.keys())
    if old_names != new_names:
        raise ValueError(
            f"Split AMM mismatch: old={old_names}, new={new_names}"
        )

    comparisons = []
    for name in sorted(old_names):
        old_amount = old_dict[name]
        new_amount = new_dict[name]

        absolute_diff = new_amount - old_amount

        # Calculate relative difference (as percentage of larger amount)
        max_amount = max(abs(old_amount), abs(new_amount))
        if max_amount > 0:
            relative_diff_pct = (absolute_diff / max_amount) * Decimal("100")
        else:
            relative_diff_pct = Decimal("0")

        comparisons.append(SplitComparison(
            amm_name=name,
            old_amount=old_amount,
            new_amount=new_amount,
            absolute_diff=absolute_diff,
            relative_diff_pct=relative_diff_pct,
        ))

    return comparisons


def _deep_copy_amm(amm: AMM) -> AMM:
    """Create a deep copy of an AMM for independent simulation.

    Args:
        amm: AMM to copy

    Returns:
        Independent copy with same state
    """
    # Create new AMM with same strategy and reserves
    new_amm = AMM(
        strategy=amm.strategy,
        reserve_x=amm.reserve_x,
        reserve_y=amm.reserve_y,
        name=amm.name,
    )

    # Copy state
    new_amm.current_fees = amm.current_fees
    new_amm._initialized = amm._initialized
    new_amm.accumulated_fees_x = amm.accumulated_fees_x
    new_amm.accumulated_fees_y = amm.accumulated_fees_y

    return new_amm


def run_parallel_simulations(
    order: RetailOrder,
    amms: list[AMM],
    fair_price: Decimal,
    timestamp: int = 0,
) -> ExecutionComparison:
    """Run matched trades through both old and new routers.

    Executes the same order through independent copies of the AMMs using
    both routers, then compares the results.

    Args:
        order: Order to execute
        amms: List of AMMs (will be copied for independent execution)
        fair_price: Current fair price
        timestamp: Simulation timestamp

    Returns:
        ExecutionComparison with detailed results

    Notes:
        - Creates independent AMM copies for each router
        - Executes order through both routers in parallel
        - Compares splits, execution prices, and final states
        - Uses Decimal precision throughout
    """
    # Create independent AMM copies for each router
    old_amms = [_deep_copy_amm(amm) for amm in amms]
    new_amms = [_deep_copy_amm(amm) for amm in amms]

    # Create routers
    old_router = OldRouter()
    new_router = NewRouter()

    # Capture initial states
    old_initial_reserves = {
        amm.name: (amm.reserve_x, amm.reserve_y) for amm in old_amms
    }
    new_initial_reserves = {
        amm.name: (amm.reserve_x, amm.reserve_y) for amm in new_amms
    }

    # Execute order through both routers
    old_trades = old_router.route_order(order, old_amms, fair_price, timestamp)
    new_trades = new_router.route_order(order, new_amms, fair_price, timestamp)

    # Calculate total amounts executed
    old_total_x = sum(trade.trade_info.amount_x for trade in old_trades)
    old_total_y = sum(trade.amount_y for trade in old_trades)
    new_total_x = sum(trade.trade_info.amount_x for trade in new_trades)
    new_total_y = sum(trade.amount_y for trade in new_trades)

    # Calculate execution prices (weighted average)
    if old_total_x > 0:
        old_execution_price = old_total_y / old_total_x
    else:
        old_execution_price = Decimal("0")

    if new_total_x > 0:
        new_execution_price = new_total_y / new_total_x
    else:
        new_execution_price = Decimal("0")

    price_diff = new_execution_price - old_execution_price
    if old_execution_price > 0:
        price_diff_pct = (price_diff / old_execution_price) * Decimal("100")
    else:
        price_diff_pct = Decimal("0")

    # Compare splits (amounts allocated to each AMM)
    old_splits = [(trade.amm, trade.amount_y if order.side == "buy" else trade.trade_info.amount_x)
                  for trade in old_trades]
    new_splits = [(trade.amm, trade.amount_y if order.side == "buy" else trade.trade_info.amount_x)
                  for trade in new_trades]

    split_comparisons = compare_splits(old_splits, new_splits)

    # Compare final reserves
    reserve_diffs = {}
    for name in old_initial_reserves.keys():
        old_amm = next(amm for amm in old_amms if amm.name == name)
        new_amm = next(amm for amm in new_amms if amm.name == name)

        x_diff = new_amm.reserve_x - old_amm.reserve_x
        y_diff = new_amm.reserve_y - old_amm.reserve_y

        reserve_diffs[name] = (x_diff, y_diff)

    return ExecutionComparison(
        order_side=order.side,
        order_size=order.size,
        old_execution_price=old_execution_price,
        new_execution_price=new_execution_price,
        price_diff=price_diff,
        price_diff_pct=price_diff_pct,
        old_total_x=old_total_x,
        new_total_x=new_total_x,
        old_total_y=old_total_y,
        new_total_y=new_total_y,
        split_comparisons=split_comparisons,
        reserve_diffs=reserve_diffs,
    )


def compare_routing_decisions(
    order: RetailOrder,
    amms: list[AMM],
    fair_price: Decimal,
) -> tuple[list[SplitComparison], bool]:
    """Compare routing split decisions without executing trades.

    Computes splits from both routers and compares them, without
    actually executing any trades. Useful for pure split testing.

    Args:
        order: Order to route
        amms: List of AMMs
        fair_price: Current fair price

    Returns:
        Tuple of (split_comparisons, all_match)
        - split_comparisons: List of SplitComparison objects
        - all_match: True if all splits match within tolerance
    """
    old_router = OldRouter()
    new_router = NewRouter()

    if order.side == "buy":
        total_y = order.size
        old_splits = old_router.compute_optimal_split_buy(amms, total_y)
        new_splits = new_router.compute_optimal_split_buy(amms, total_y)
    else:
        total_x = order.size / fair_price
        old_splits = old_router.compute_optimal_split_sell(amms, total_x)
        new_splits = new_router.compute_optimal_split_sell(amms, total_x)

    comparisons = compare_splits(old_splits, new_splits)
    all_match = all(c.matches for c in comparisons)

    return comparisons, all_match
