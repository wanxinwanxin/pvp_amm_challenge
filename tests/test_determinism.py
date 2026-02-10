"""Determinism and stability testing for AMM simulations.

Verifies that simulations are reproducible with fixed random seeds and that
all calculations maintain bit-exact precision across multiple runs.

Test coverage:
- Routing decisions are deterministic
- Execution prices are bit-exact reproducible
- PnL calculations are stable
- Convergence behavior is consistent
- Different seeds produce different results (randomness works)

Key requirements:
- All comparisons use Decimal precision (not floats)
- Fixed seeds guarantee bit-exact reproduction
- Detailed error messages show which values differ
- Tests cover both constant and tiered fee structures
"""

import random
from decimal import Decimal
from typing import List, Tuple
from dataclasses import dataclass

import pytest

from amm_competition.core.amm import AMM
from amm_competition.market.router import OrderRouter
from amm_competition.market.retail import RetailOrder
from tests.fixtures.economic_fixtures import (
    create_constant_fee_amm,
    create_tiered_fee_amm,
    get_baseline_fee_tiers,
    PoolBalanceProfile,
    get_pool_balance,
    snapshot_amm_state,
    calculate_pnl,
    AMMStateSnapshot,
)


@dataclass
class SimulationResult:
    """Complete state capture from a simulation run."""
    amm_snapshots: List[AMMStateSnapshot]
    splits: List[Tuple[str, Decimal]]  # (amm_name, amount)
    execution_prices: List[Decimal]
    final_pnls: List[Tuple[str, Decimal]]  # (amm_name, pnl)
    total_trades: int

    def __eq__(self, other) -> bool:
        """Bit-exact equality check for all Decimal fields."""
        if not isinstance(other, SimulationResult):
            return False

        # Check array lengths
        if len(self.amm_snapshots) != len(other.amm_snapshots):
            return False
        if len(self.splits) != len(other.splits):
            return False
        if len(self.execution_prices) != len(other.execution_prices):
            return False
        if len(self.final_pnls) != len(other.final_pnls):
            return False
        if self.total_trades != other.total_trades:
            return False

        # Check AMM snapshots bit-exact
        for s1, s2 in zip(self.amm_snapshots, other.amm_snapshots):
            if s1.name != s2.name:
                return False
            if s1.reserve_x != s2.reserve_x:
                return False
            if s1.reserve_y != s2.reserve_y:
                return False
            if s1.accumulated_fees_x != s2.accumulated_fees_x:
                return False
            if s1.accumulated_fees_y != s2.accumulated_fees_y:
                return False
            if s1.k != s2.k:
                return False

        # Check splits bit-exact
        for (name1, amt1), (name2, amt2) in zip(self.splits, other.splits):
            if name1 != name2:
                return False
            if amt1 != amt2:
                return False

        # Check execution prices bit-exact
        for p1, p2 in zip(self.execution_prices, other.execution_prices):
            if p1 != p2:
                return False

        # Check PnLs bit-exact
        for (name1, pnl1), (name2, pnl2) in zip(self.final_pnls, other.final_pnls):
            if name1 != name2:
                return False
            if pnl1 != pnl2:
                return False

        return True


def create_amm_set_for_test(
    fee_structure: str = "constant",
    n_amms: int = 3,
) -> List[AMM]:
    """Create a standard set of AMMs for testing.

    Args:
        fee_structure: "constant", "two_tier", or "three_tier"
        n_amms: Number of AMMs to create

    Returns:
        List of initialized AMMs with identical balances but different names
    """
    reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)
    amms = []

    for i in range(n_amms):
        name = f"AMM{i+1}"

        if fee_structure == "constant":
            amm = create_constant_fee_amm(
                name,
                Decimal("0.003"),
                reserve_x,
                reserve_y,
            )
        elif fee_structure == "two_tier":
            amm = create_tiered_fee_amm(
                name,
                [
                    (Decimal("0"), Decimal("0.003")),
                    (Decimal("100"), Decimal("0.002")),
                ],
                reserve_x,
                reserve_y,
            )
        elif fee_structure == "three_tier":
            amm = create_tiered_fee_amm(
                name,
                get_baseline_fee_tiers("conservative"),
                reserve_x,
                reserve_y,
            )
        else:
            raise ValueError(f"Unknown fee structure: {fee_structure}")

        amms.append(amm)

    return amms


def generate_trade_sequence(
    seed: int,
    n_trades: int,
    fair_price: Decimal = Decimal("1.0"),
) -> List[RetailOrder]:
    """Generate a deterministic sequence of retail orders.

    Args:
        seed: Random seed for reproducibility
        n_trades: Number of trades to generate
        fair_price: Base price for sizing

    Returns:
        List of retail orders with deterministic properties
    """
    rng = random.Random(seed)
    orders = []

    for i in range(n_trades):
        # Deterministic side selection
        side = "buy" if rng.random() < 0.5 else "sell"

        # Deterministic size selection (log-normal-ish distribution)
        # Size between 10 and 1000 Y
        size_factor = rng.uniform(0.5, 2.5)
        base_size = Decimal("50") * Decimal(str(size_factor))

        orders.append(RetailOrder(side=side, size=base_size))

    return orders


def run_simulation(
    amms: List[AMM],
    seed: int,
    n_trades: int = 50,
    fair_price: Decimal = Decimal("1.0"),
) -> SimulationResult:
    """Run a complete simulation with deterministic trade sequence.

    Args:
        amms: List of AMMs to route trades to
        seed: Random seed for trade generation
        n_trades: Number of trades to execute
        fair_price: Fair price for routing decisions

    Returns:
        Complete simulation result with all state snapshots
    """
    # Take initial snapshots
    initial_snapshots = [snapshot_amm_state(amm) for amm in amms]

    # Generate deterministic trade sequence
    orders = generate_trade_sequence(seed, n_trades, fair_price)

    # Execute trades
    router = OrderRouter()
    all_splits = []
    all_prices = []
    timestamp = 0

    for order in orders:
        # Compute optimal split
        if order.side == "buy":
            splits = router.compute_optimal_split_buy(amms, order.size)
        else:
            total_x = order.size / fair_price
            splits = router.compute_optimal_split_sell(amms, total_x)

        # Record splits (amm_name, amount)
        for amm, amount in splits:
            all_splits.append((amm.name, amount))

        # Execute the order
        trades = router.route_order(order, amms, fair_price, timestamp)

        # Record execution prices
        for trade in trades:
            price = trade.trade_info.implied_price
            all_prices.append(price)

        timestamp += 1

    # Take final snapshots
    final_snapshots = [snapshot_amm_state(amm) for amm in amms]

    # Calculate PnLs
    pnls = []
    for initial, final in zip(initial_snapshots, final_snapshots):
        pnl_result = calculate_pnl(initial, final)
        pnls.append((final.name, pnl_result.pnl_at_final_price))

    return SimulationResult(
        amm_snapshots=final_snapshots,
        splits=all_splits,
        execution_prices=all_prices,
        final_pnls=pnls,
        total_trades=len(orders),
    )


class TestDeterministicRoutingDecisions:
    """Test that routing decisions are reproducible with fixed seeds."""

    def test_constant_fee_routing_deterministic(self):
        """Verify routing splits are bit-exact identical across runs (constant fees)."""
        seed = 42
        n_trades = 50

        # Run 1
        amms1 = create_amm_set_for_test("constant", n_amms=3)
        results1 = run_simulation(amms1, seed=seed, n_trades=n_trades)

        # Run 2
        amms2 = create_amm_set_for_test("constant", n_amms=3)
        results2 = run_simulation(amms2, seed=seed, n_trades=n_trades)

        # Verify splits are bit-exact identical
        assert len(results1.splits) == len(results2.splits), \
            f"Different number of splits: {len(results1.splits)} vs {len(results2.splits)}"

        for i, ((name1, amt1), (name2, amt2)) in enumerate(zip(results1.splits, results2.splits)):
            assert name1 == name2, \
                f"Split {i}: Different AMM names: {name1} vs {name2}"
            assert amt1 == amt2, \
                f"Split {i} ({name1}): Different amounts: {amt1} vs {amt2}"

    def test_tiered_fee_routing_deterministic(self):
        """Verify routing splits are bit-exact identical with tiered fees."""
        seed = 42
        n_trades = 50

        # Run 1
        amms1 = create_amm_set_for_test("two_tier", n_amms=3)
        results1 = run_simulation(amms1, seed=seed, n_trades=n_trades)

        # Run 2
        amms2 = create_amm_set_for_test("two_tier", n_amms=3)
        results2 = run_simulation(amms2, seed=seed, n_trades=n_trades)

        # Verify splits are bit-exact identical
        assert len(results1.splits) == len(results2.splits), \
            f"Different number of splits: {len(results1.splits)} vs {len(results2.splits)}"

        for i, ((name1, amt1), (name2, amt2)) in enumerate(zip(results1.splits, results2.splits)):
            assert name1 == name2, \
                f"Split {i}: Different AMM names: {name1} vs {name2}"
            assert amt1 == amt2, \
                f"Split {i} ({name1}): Different amounts: {amt1} vs {amt2} (diff: {abs(amt1 - amt2)})"

    def test_three_tier_routing_deterministic(self):
        """Verify routing splits work with three-tier fee structures."""
        seed = 123
        n_trades = 30

        # Run 1
        amms1 = create_amm_set_for_test("three_tier", n_amms=2)
        results1 = run_simulation(amms1, seed=seed, n_trades=n_trades)

        # Run 2
        amms2 = create_amm_set_for_test("three_tier", n_amms=2)
        results2 = run_simulation(amms2, seed=seed, n_trades=n_trades)

        # Verify splits are identical
        assert len(results1.splits) == len(results2.splits)
        for (name1, amt1), (name2, amt2) in zip(results1.splits, results2.splits):
            assert name1 == name2
            assert amt1 == amt2, \
                f"Split amounts differ: {amt1} vs {amt2}"


class TestDeterministicExecutionPrices:
    """Test that execution prices are reproducible with Decimal precision."""

    def test_execution_prices_bit_exact(self):
        """Verify execution prices are identical across multiple runs."""
        seed = 42
        n_trades = 50

        # Run 1
        amms1 = create_amm_set_for_test("constant", n_amms=3)
        results1 = run_simulation(amms1, seed=seed, n_trades=n_trades)

        # Run 2
        amms2 = create_amm_set_for_test("constant", n_amms=3)
        results2 = run_simulation(amms2, seed=seed, n_trades=n_trades)

        # Verify all prices match bit-exact
        assert len(results1.execution_prices) == len(results2.execution_prices), \
            f"Different number of prices: {len(results1.execution_prices)} vs {len(results2.execution_prices)}"

        for i, (p1, p2) in enumerate(zip(results1.execution_prices, results2.execution_prices)):
            assert p1 == p2, \
                f"Price {i}: {p1} vs {p2} (diff: {abs(p1 - p2)})"

    def test_tiered_fee_execution_prices_stable(self):
        """Verify execution prices are stable with tiered fees."""
        seed = 99
        n_trades = 30

        # Run 1
        amms1 = create_amm_set_for_test("two_tier", n_amms=2)
        results1 = run_simulation(amms1, seed=seed, n_trades=n_trades)

        # Run 2
        amms2 = create_amm_set_for_test("two_tier", n_amms=2)
        results2 = run_simulation(amms2, seed=seed, n_trades=n_trades)

        # Verify all prices match
        assert len(results1.execution_prices) == len(results2.execution_prices)

        for i, (p1, p2) in enumerate(zip(results1.execution_prices, results2.execution_prices)):
            assert p1 == p2, \
                f"Price {i}: {p1} vs {p2} (diff: {abs(p1 - p2)})"


class TestDeterministicPnLCalculation:
    """Test that PnL calculations are reproducible and stable."""

    def test_pnl_bit_exact_reproduction(self):
        """Verify PnL calculations are bit-exact identical."""
        seed = 42
        n_trades = 50

        # Run 1
        amms1 = create_amm_set_for_test("constant", n_amms=3)
        results1 = run_simulation(amms1, seed=seed, n_trades=n_trades)

        # Run 2
        amms2 = create_amm_set_for_test("constant", n_amms=3)
        results2 = run_simulation(amms2, seed=seed, n_trades=n_trades)

        # Verify PnLs match bit-exact
        assert len(results1.final_pnls) == len(results2.final_pnls)

        for (name1, pnl1), (name2, pnl2) in zip(results1.final_pnls, results2.final_pnls):
            assert name1 == name2, f"AMM names differ: {name1} vs {name2}"
            assert pnl1 == pnl2, \
                f"PnL for {name1}: {pnl1} vs {pnl2} (diff: {abs(pnl1 - pnl2)})"

    def test_tiered_pnl_stability(self):
        """Verify PnL calculations are stable with tiered fees."""
        seed = 123
        n_trades = 30

        # Run 1
        amms1 = create_amm_set_for_test("two_tier", n_amms=2)
        results1 = run_simulation(amms1, seed=seed, n_trades=n_trades)

        # Run 2
        amms2 = create_amm_set_for_test("two_tier", n_amms=2)
        results2 = run_simulation(amms2, seed=seed, n_trades=n_trades)

        # Verify PnLs match
        assert len(results1.final_pnls) == len(results2.final_pnls)

        for (name1, pnl1), (name2, pnl2) in zip(results1.final_pnls, results2.final_pnls):
            assert name1 == name2
            assert pnl1 == pnl2, \
                f"PnL for {name1}: {pnl1} vs {pnl2}"


class TestMultipleRunsIdenticalResults:
    """Test that multiple runs with same seed produce identical results."""

    def test_five_runs_constant_fees(self):
        """Run same scenario 5 times and verify all results match."""
        seed = 42
        n_trades = 50
        n_runs = 5

        results = []
        for run in range(n_runs):
            amms = create_amm_set_for_test("constant", n_amms=3)
            result = run_simulation(amms, seed=seed, n_trades=n_trades)
            results.append(result)

        # Verify all results are identical to first result
        first = results[0]
        for i, result in enumerate(results[1:], start=2):
            assert result == first, \
                f"Run {i} differs from run 1"

            # Also verify reserves explicitly
            for j, (snap1, snap2) in enumerate(zip(first.amm_snapshots, result.amm_snapshots)):
                assert snap1.reserve_x == snap2.reserve_x, \
                    f"Run {i}, AMM {j}: reserve_x differs: {snap1.reserve_x} vs {snap2.reserve_x}"
                assert snap1.reserve_y == snap2.reserve_y, \
                    f"Run {i}, AMM {j}: reserve_y differs: {snap1.reserve_y} vs {snap2.reserve_y}"
                assert snap1.accumulated_fees_x == snap2.accumulated_fees_x, \
                    f"Run {i}, AMM {j}: fees_x differs: {snap1.accumulated_fees_x} vs {snap2.accumulated_fees_x}"
                assert snap1.accumulated_fees_y == snap2.accumulated_fees_y, \
                    f"Run {i}, AMM {j}: fees_y differs: {snap1.accumulated_fees_y} vs {snap2.accumulated_fees_y}"

    def test_five_runs_tiered_fees(self):
        """Run same scenario 5 times with tiered fees and verify all results match."""
        seed = 99
        n_trades = 30
        n_runs = 5

        results = []
        for run in range(n_runs):
            amms = create_amm_set_for_test("two_tier", n_amms=2)
            result = run_simulation(amms, seed=seed, n_trades=n_trades)
            results.append(result)

        # Verify all results are identical
        first = results[0]
        for i, result in enumerate(results[1:], start=2):
            assert result == first, \
                f"Run {i} differs from run 1"


class TestRouterConvergenceStableSplits:
    """Test that iterative router convergence produces stable splits."""

    def test_convergence_identical_across_runs(self):
        """Verify iterative convergence produces same split each time."""
        seed = 42

        # Create AMMs with tiered fees (triggers iterative convergence)
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        # Use different tier structures to force convergence behavior
        amm1_tiers = [
            (Decimal("0"), Decimal("0.003")),
            (Decimal("100"), Decimal("0.002")),
        ]
        amm2_tiers = [
            (Decimal("0"), Decimal("0.004")),
            (Decimal("200"), Decimal("0.001")),
        ]

        router = OrderRouter()
        splits_runs = []

        for run in range(5):
            # Create fresh AMMs for each run
            amm1 = create_tiered_fee_amm("AMM1", amm1_tiers, reserve_x, reserve_y)
            amm2 = create_tiered_fee_amm("AMM2", amm2_tiers, reserve_x, reserve_y)

            # Test various trade sizes
            test_sizes = [
                Decimal("50"),    # Small
                Decimal("150"),   # Medium (crosses tier)
                Decimal("500"),   # Large
                Decimal("1500"),  # Very large (crosses multiple tiers)
            ]

            run_splits = []
            for size in test_sizes:
                # Buy direction (splits Y amount)
                splits_buy = router.compute_optimal_split_buy([amm1, amm2], size)
                run_splits.append(("buy", size, splits_buy))

                # Sell direction (splits X amount)
                x_amount = size / Decimal("1.0")  # Using fair price = 1.0
                splits_sell = router.compute_optimal_split_sell([amm1, amm2], x_amount)
                run_splits.append(("sell", x_amount, splits_sell))

            splits_runs.append(run_splits)

        # Verify all runs produced identical splits
        first_run = splits_runs[0]
        for run_idx, run_splits in enumerate(splits_runs[1:], start=2):
            for split_idx, (split1, split2) in enumerate(zip(first_run, run_splits)):
                direction1, size1, result1 = split1
                direction2, size2, result2 = split2

                assert direction1 == direction2
                assert size1 == size2

                # Check splits are identical
                for (amm1_obj, amt1), (amm2_obj, amt2) in zip(result1, result2):
                    assert amm1_obj.name == amm2_obj.name
                    assert amt1 == amt2, \
                        f"Run {run_idx}, split {split_idx} ({direction1}, {size1}): " \
                        f"{amm1_obj.name} amounts differ: {amt1} vs {amt2} (diff: {abs(amt1 - amt2)})"

    def test_convergence_with_various_trade_sizes(self):
        """Test convergence stability across a range of trade sizes."""
        reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)

        tiers = get_baseline_fee_tiers("conservative")

        router = OrderRouter()

        # Test trade sizes from very small to very large
        trade_sizes = [
            Decimal("1"),      # Tiny
            Decimal("10"),     # Small
            Decimal("50"),     # Medium-small
            Decimal("150"),    # Medium (crosses first tier)
            Decimal("500"),    # Large
            Decimal("1500"),   # Very large (crosses second tier)
            Decimal("5000"),   # Huge
        ]

        for size in trade_sizes:
            # Run split computation twice
            amm1_run1 = create_tiered_fee_amm("AMM1", tiers, reserve_x, reserve_y)
            amm2_run1 = create_tiered_fee_amm("AMM2", tiers, reserve_x, reserve_y)
            splits1 = router.compute_optimal_split_sell([amm1_run1, amm2_run1], size)

            amm1_run2 = create_tiered_fee_amm("AMM1", tiers, reserve_x, reserve_y)
            amm2_run2 = create_tiered_fee_amm("AMM2", tiers, reserve_x, reserve_y)
            splits2 = router.compute_optimal_split_sell([amm1_run2, amm2_run2], size)

            # Verify splits are identical
            for (amm_obj1, amt1), (amm_obj2, amt2) in zip(splits1, splits2):
                assert amm_obj1.name == amm_obj2.name
                assert amt1 == amt2, \
                    f"Trade size {size}: {amm_obj1.name} splits differ: {amt1} vs {amt2}"


class TestDifferentSeedsDifferentResults:
    """Test that different seeds produce different outcomes."""

    def test_different_seeds_produce_different_splits(self):
        """Verify different seeds lead to different trade sequences and outcomes."""
        seed1 = 42
        seed2 = 99
        n_trades = 50

        # Run with seed 1
        amms1 = create_amm_set_for_test("constant", n_amms=3)
        results1 = run_simulation(amms1, seed=seed1, n_trades=n_trades)

        # Run with seed 2
        amms2 = create_amm_set_for_test("constant", n_amms=3)
        results2 = run_simulation(amms2, seed=seed2, n_trades=n_trades)

        # Results should be different (different trade sequences)
        # At least one split should differ
        splits_differ = False
        for (name1, amt1), (name2, amt2) in zip(results1.splits, results2.splits):
            if name1 != name2 or amt1 != amt2:
                splits_differ = True
                break

        assert splits_differ, \
            "Different seeds produced identical splits - randomness not working"

        # Final PnLs should also differ
        pnls_differ = False
        for (name1, pnl1), (name2, pnl2) in zip(results1.final_pnls, results2.final_pnls):
            if pnl1 != pnl2:
                pnls_differ = True
                break

        assert pnls_differ, \
            "Different seeds produced identical PnLs - randomness not working"

    def test_same_seed_different_n_trades_diverges(self):
        """Verify that same seed with different n_trades produces different end states."""
        seed = 42

        # Run with 30 trades
        amms1 = create_amm_set_for_test("constant", n_amms=2)
        results1 = run_simulation(amms1, seed=seed, n_trades=30)

        # Run with 50 trades (superset)
        amms2 = create_amm_set_for_test("constant", n_amms=2)
        results2 = run_simulation(amms2, seed=seed, n_trades=50)

        # First 30 trades should be identical
        for i in range(min(len(results1.splits), 60)):  # 30 trades * ~2 AMMs
            if i < len(results1.splits) and i < len(results2.splits):
                (name1, amt1), (name2, amt2) = results1.splits[i], results2.splits[i]
                assert name1 == name2
                assert amt1 == amt2

        # But final states should differ (more trades = different end state)
        for (name1, pnl1), (name2, pnl2) in zip(results1.final_pnls, results2.final_pnls):
            assert name1 == name2
            # PnLs should be different after different number of trades
            assert pnl1 != pnl2, \
                f"PnL for {name1} same after 30 and 50 trades: {pnl1}"

    def test_each_seed_is_reproducible(self):
        """Verify that each different seed is itself reproducible."""
        seeds = [42, 99, 123, 456, 789]
        n_trades = 30

        for seed in seeds:
            # Run 1
            amms1 = create_amm_set_for_test("constant", n_amms=2)
            results1 = run_simulation(amms1, seed=seed, n_trades=n_trades)

            # Run 2
            amms2 = create_amm_set_for_test("constant", n_amms=2)
            results2 = run_simulation(amms2, seed=seed, n_trades=n_trades)

            # Should be identical
            assert results1 == results2, \
                f"Seed {seed} not reproducible"


class TestAMMStateReproducibility:
    """Test that AMM state (reserves, fees) is exactly reproducible."""

    def test_reserves_bit_exact_identical(self):
        """Verify reserve values are bit-exact identical across runs."""
        seed = 42
        n_trades = 50

        # Run 1
        amms1 = create_amm_set_for_test("constant", n_amms=3)
        results1 = run_simulation(amms1, seed=seed, n_trades=n_trades)

        # Run 2
        amms2 = create_amm_set_for_test("constant", n_amms=3)
        results2 = run_simulation(amms2, seed=seed, n_trades=n_trades)

        # Check all snapshots
        for snap1, snap2 in zip(results1.amm_snapshots, results2.amm_snapshots):
            assert snap1.name == snap2.name
            assert snap1.reserve_x == snap2.reserve_x, \
                f"{snap1.name}: reserve_x differs: {snap1.reserve_x} vs {snap2.reserve_x}"
            assert snap1.reserve_y == snap2.reserve_y, \
                f"{snap1.name}: reserve_y differs: {snap1.reserve_y} vs {snap2.reserve_y}"
            assert snap1.k == snap2.k, \
                f"{snap1.name}: k differs: {snap1.k} vs {snap2.k}"

    def test_accumulated_fees_bit_exact_identical(self):
        """Verify accumulated fees are bit-exact identical across runs."""
        seed = 42
        n_trades = 50

        # Run 1
        amms1 = create_amm_set_for_test("two_tier", n_amms=2)
        results1 = run_simulation(amms1, seed=seed, n_trades=n_trades)

        # Run 2
        amms2 = create_amm_set_for_test("two_tier", n_amms=2)
        results2 = run_simulation(amms2, seed=seed, n_trades=n_trades)

        # Check accumulated fees
        for snap1, snap2 in zip(results1.amm_snapshots, results2.amm_snapshots):
            assert snap1.name == snap2.name
            assert snap1.accumulated_fees_x == snap2.accumulated_fees_x, \
                f"{snap1.name}: accumulated_fees_x differs: " \
                f"{snap1.accumulated_fees_x} vs {snap2.accumulated_fees_x}"
            assert snap1.accumulated_fees_y == snap2.accumulated_fees_y, \
                f"{snap1.name}: accumulated_fees_y differs: " \
                f"{snap1.accumulated_fees_y} vs {snap2.accumulated_fees_y}"

    def test_spot_price_reproducible(self):
        """Verify spot prices are reproducible after identical trade sequences."""
        seed = 42
        n_trades = 50

        # Run 1
        amms1 = create_amm_set_for_test("three_tier", n_amms=2)
        results1 = run_simulation(amms1, seed=seed, n_trades=n_trades)

        # Run 2
        amms2 = create_amm_set_for_test("three_tier", n_amms=2)
        results2 = run_simulation(amms2, seed=seed, n_trades=n_trades)

        # Check spot prices
        for snap1, snap2 in zip(results1.amm_snapshots, results2.amm_snapshots):
            assert snap1.name == snap2.name
            assert snap1.spot_price == snap2.spot_price, \
                f"{snap1.name}: spot_price differs: {snap1.spot_price} vs {snap2.spot_price}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
