"""Pytest configuration and shared fixtures for economic correctness tests.

This module provides:
- Shared fixtures for common test scenarios
- Pytest markers for test categorization
- Custom assertions for economic properties
- Test timing utilities
"""

import time
from decimal import Decimal
from typing import Callable, Generator

import pytest

from amm_competition.core.amm import AMM
from tests.fixtures.economic_fixtures import (
    PoolBalanceProfile,
    create_amm_set,
    create_constant_fee_amm,
    get_pool_balance,
)


# ============================================================================
# Pytest Hooks
# ============================================================================


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "backward_compat: Backward compatibility tests comparing old vs new system",
    )
    config.addinivalue_line(
        "markers", "economic: Core economic property tests (symmetry, arbitrage, etc.)"
    )
    config.addinivalue_line(
        "markers", "edge_case: Edge case and stress tests with extreme inputs"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests spanning multiple components"
    )
    config.addinivalue_line(
        "markers", "slow: Tests taking more than 5 seconds to run"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically mark tests based on location and name."""
    for item in items:
        # Auto-mark backward compatibility tests
        if "backward_compat" in item.nodeid:
            item.add_marker(pytest.mark.backward_compat)

        # Auto-mark edge case tests
        if "edge_case" in item.nodeid or "edge_case" in item.name:
            item.add_marker(pytest.mark.edge_case)

        # Auto-mark integration tests
        if any(
            keyword in item.nodeid
            for keyword in ["symmetry", "arbitrage", "routing", "accounting"]
        ):
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.economic)


# ============================================================================
# Standard AMM Fixtures
# ============================================================================


@pytest.fixture
def standard_amm_set() -> list[AMM]:
    """Standard set of 5 AMMs with diverse fee structures.

    Returns:
        List of 5 AMMs:
        1. ConstantFee: 30bps flat fee
        2. TwoTier: 30bps -> 20bps (threshold at 100)
        3. ThreeTier: 30bps -> 20bps -> 10bps (thresholds at 100, 1000)
        4. Aggressive: 50bps -> 10bps -> 1bps (thresholds at 100, 1000)
        5. Pathological: 100% -> 1bps -> 0.1bps (thresholds at 1, 2)

    All AMMs have balanced reserves (10000, 10000).
    """
    return create_amm_set()


@pytest.fixture
def balanced_pools() -> list[AMM]:
    """AMMs with equal X and Y reserves (10000, 10000).

    Returns:
        Standard AMM set with balanced reserves.
    """
    return create_amm_set(PoolBalanceProfile.BALANCED)


@pytest.fixture
def skewed_x_pools() -> list[AMM]:
    """AMMs with more X than Y reserves (20000, 5000).

    Returns:
        Standard AMM set with X-skewed reserves.
    """
    return create_amm_set(PoolBalanceProfile.SKEWED_X)


@pytest.fixture
def skewed_y_pools() -> list[AMM]:
    """AMMs with more Y than X reserves (5000, 20000).

    Returns:
        Standard AMM set with Y-skewed reserves.
    """
    return create_amm_set(PoolBalanceProfile.SKEWED_Y)


@pytest.fixture
def extreme_pools() -> list[AMM]:
    """AMMs with extremely imbalanced reserves (1, 1000000).

    Returns:
        Standard AMM set with extreme reserve imbalance.
    """
    return create_amm_set(PoolBalanceProfile.EXTREME)


@pytest.fixture
def constant_fee_amms() -> list[AMM]:
    """Set of AMMs with only constant fees (no tiers).

    Returns:
        5 AMMs with different constant fees:
        - 20bps, 25bps, 30bps, 35bps, 40bps
    """
    reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)
    return [
        create_constant_fee_amm("ConstantFee_20bps", Decimal("0.002"), reserve_x, reserve_y),
        create_constant_fee_amm("ConstantFee_25bps", Decimal("0.0025"), reserve_x, reserve_y),
        create_constant_fee_amm("ConstantFee_30bps", Decimal("0.003"), reserve_x, reserve_y),
        create_constant_fee_amm("ConstantFee_35bps", Decimal("0.0035"), reserve_x, reserve_y),
        create_constant_fee_amm("ConstantFee_40bps", Decimal("0.004"), reserve_x, reserve_y),
    ]


@pytest.fixture
def two_identical_amms() -> list[AMM]:
    """Two AMMs with identical fee structures for symmetry testing.

    Returns:
        2 AMMs with identical 30bps constant fees and balanced reserves.
    """
    reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)
    return [
        create_constant_fee_amm("AMM_A", Decimal("0.003"), reserve_x, reserve_y),
        create_constant_fee_amm("AMM_B", Decimal("0.003"), reserve_x, reserve_y),
    ]


@pytest.fixture
def two_different_fee_amms() -> list[AMM]:
    """Two AMMs with different fee structures for routing tests.

    Returns:
        2 AMMs with 20bps and 40bps fees and balanced reserves.
    """
    reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.BALANCED)
    return [
        create_constant_fee_amm("LowFee", Decimal("0.002"), reserve_x, reserve_y),
        create_constant_fee_amm("HighFee", Decimal("0.004"), reserve_x, reserve_y),
    ]


# ============================================================================
# Price and Seed Fixtures
# ============================================================================


@pytest.fixture
def fair_price() -> Decimal:
    """Standard fair price for testing (1.0 Y per X).

    Returns:
        Decimal("1.0")
    """
    return Decimal("1.0")


@pytest.fixture
def fixed_seed() -> int:
    """Fixed random seed for deterministic tests.

    Returns:
        42
    """
    return 42


@pytest.fixture
def random_seeds() -> list[int]:
    """Multiple random seeds for testing consistency across seeds.

    Returns:
        List of 5 seeds: [42, 123, 456, 789, 1337]
    """
    return [42, 123, 456, 789, 1337]


# ============================================================================
# Trade Size Fixtures
# ============================================================================


@pytest.fixture
def small_trade_size() -> Decimal:
    """Small trade size relative to pool reserves.

    Returns:
        Decimal("100") - 1% of standard pool (10000)
    """
    return Decimal("100")


@pytest.fixture
def medium_trade_size() -> Decimal:
    """Medium trade size relative to pool reserves.

    Returns:
        Decimal("1000") - 10% of standard pool (10000)
    """
    return Decimal("1000")


@pytest.fixture
def large_trade_size() -> Decimal:
    """Large trade size relative to pool reserves.

    Returns:
        Decimal("5000") - 50% of standard pool (10000)
    """
    return Decimal("5000")


@pytest.fixture
def trade_sizes() -> list[Decimal]:
    """Multiple trade sizes for parameterized testing.

    Returns:
        List of sizes: [10, 100, 1000, 5000] covering small to large.
    """
    return [Decimal("10"), Decimal("100"), Decimal("1000"), Decimal("5000")]


# ============================================================================
# Timing Utilities
# ============================================================================


@pytest.fixture
def timer() -> Callable[[], float]:
    """Timer fixture for measuring test execution time.

    Returns:
        Function that returns elapsed time in seconds since fixture creation.

    Example:
        >>> def test_performance(timer):
        ...     # ... test code ...
        ...     elapsed = timer()
        ...     assert elapsed < 0.1  # Should complete in < 100ms
    """
    start_time = time.perf_counter()

    def get_elapsed() -> float:
        return time.perf_counter() - start_time

    return get_elapsed


@pytest.fixture
def benchmark() -> Callable[[Callable], float]:
    """Benchmark fixture for timing callable execution.

    Returns:
        Function that executes and times a callable, returning elapsed seconds.

    Example:
        >>> def test_routing_performance(benchmark):
        ...     elapsed = benchmark(lambda: router.compute_optimal_split(...))
        ...     assert elapsed < 0.01  # Should complete in < 10ms
    """

    def run_benchmark(func: Callable) -> float:
        start = time.perf_counter()
        func()
        return time.perf_counter() - start

    return run_benchmark


# ============================================================================
# Tolerance Fixtures
# ============================================================================


@pytest.fixture
def decimal_tolerance() -> Decimal:
    """Standard tolerance for Decimal precision comparisons.

    Returns:
        Decimal("1e-10") - appropriate for financial calculations
    """
    return Decimal("1e-10")


@pytest.fixture
def percentage_tolerance() -> Decimal:
    """Standard tolerance for percentage-based comparisons.

    Returns:
        Decimal("0.0001") - 0.01% relative error
    """
    return Decimal("0.0001")


@pytest.fixture
def symmetry_tolerance() -> Decimal:
    """Tolerance for symmetry testing (identical strategies).

    Returns:
        Decimal("0.001") - 0.1% relative difference
    """
    return Decimal("0.001")


# ============================================================================
# Custom Assertions
# ============================================================================


class EconomicAssertions:
    """Custom assertion helpers for economic properties.

    Provides domain-specific assertions with clear error messages.
    """

    @staticmethod
    def assert_values_match(
        actual: Decimal,
        expected: Decimal,
        tolerance: Decimal = Decimal("1e-10"),
        name: str = "value",
    ) -> None:
        """Assert two Decimal values match within tolerance.

        Args:
            actual: Actual value
            expected: Expected value
            tolerance: Maximum absolute difference
            name: Name for error message

        Raises:
            AssertionError: If values don't match within tolerance
        """
        diff = abs(actual - expected)
        assert diff <= tolerance, (
            f"{name} mismatch: expected {expected}, got {actual}, "
            f"diff {diff} exceeds tolerance {tolerance}"
        )

    @staticmethod
    def assert_percentage_match(
        actual: Decimal,
        expected: Decimal,
        tolerance_pct: Decimal = Decimal("0.01"),
        name: str = "value",
    ) -> None:
        """Assert two values match within percentage tolerance.

        Args:
            actual: Actual value
            expected: Expected value
            tolerance_pct: Maximum relative difference as percentage (e.g., 0.01 = 1%)
            name: Name for error message

        Raises:
            AssertionError: If values don't match within tolerance
        """
        if expected == 0:
            assert actual == 0, f"{name}: expected 0, got {actual}"
            return

        relative_diff = abs(actual - expected) / abs(expected)
        tolerance_decimal = tolerance_pct / Decimal("100")

        assert relative_diff <= tolerance_decimal, (
            f"{name} relative diff {relative_diff * 100:.6f}% exceeds "
            f"tolerance {tolerance_pct}%. Expected {expected}, got {actual}"
        )

    @staticmethod
    def assert_symmetric_pnls(
        pnl_a: Decimal,
        pnl_b: Decimal,
        tolerance_pct: Decimal = Decimal("0.1"),
    ) -> None:
        """Assert two PnLs are symmetric (for identical strategies).

        Args:
            pnl_a: First PnL
            pnl_b: Second PnL
            tolerance_pct: Maximum relative difference as percentage

        Raises:
            AssertionError: If PnLs are not symmetric
        """
        if pnl_a == 0 and pnl_b == 0:
            return

        avg_pnl = (abs(pnl_a) + abs(pnl_b)) / 2
        if avg_pnl == 0:
            return

        diff = abs(pnl_a - pnl_b)
        relative_diff_pct = (diff / avg_pnl) * Decimal("100")

        assert relative_diff_pct <= tolerance_pct, (
            f"PnLs not symmetric: {pnl_a} vs {pnl_b}, "
            f"relative diff {relative_diff_pct:.4f}% exceeds tolerance {tolerance_pct}%"
        )

    @staticmethod
    def assert_no_arbitrage(
        net_position: Decimal,
        total_fees: Decimal,
        tolerance_pct: Decimal = Decimal("0.1"),
    ) -> None:
        """Assert that net position equals fees paid (no arbitrage).

        Args:
            net_position: Net position after round-trip (should be negative)
            total_fees: Total fees paid
            tolerance_pct: Maximum relative difference

        Raises:
            AssertionError: If arbitrage opportunity exists
        """
        assert net_position <= 0, f"Positive net position indicates arbitrage: {net_position}"

        loss = abs(net_position)
        if total_fees == 0:
            assert loss == 0, f"Loss {loss} with zero fees indicates arbitrage"
            return

        relative_diff = abs(loss - total_fees) / total_fees
        tolerance_decimal = tolerance_pct / Decimal("100")

        assert relative_diff <= tolerance_decimal, (
            f"Loss {loss} doesn't match fees {total_fees}, "
            f"relative diff {relative_diff * 100:.4f}% exceeds tolerance {tolerance_pct}%"
        )

    @staticmethod
    def assert_sum_near_zero(
        values: list[Decimal],
        tolerance: Decimal = Decimal("1e-10"),
        name: str = "sum",
    ) -> None:
        """Assert sum of values is near zero (value conservation).

        Args:
            values: List of values to sum
            tolerance: Maximum absolute sum
            name: Name for error message

        Raises:
            AssertionError: If sum exceeds tolerance
        """
        total = sum(values)
        assert abs(total) <= tolerance, (
            f"{name} = {total} exceeds tolerance {tolerance}. "
            f"Individual values: {values}"
        )


@pytest.fixture
def economic_assert() -> EconomicAssertions:
    """Fixture providing custom economic assertions.

    Returns:
        EconomicAssertions instance with helper methods.

    Example:
        >>> def test_symmetry(economic_assert):
        ...     pnl_a = calculate_pnl(...)
        ...     pnl_b = calculate_pnl(...)
        ...     economic_assert.assert_symmetric_pnls(pnl_a, pnl_b)
    """
    return EconomicAssertions()


# ============================================================================
# Session-scoped Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def test_config() -> dict:
    """Global test configuration.

    Returns:
        Dictionary with test configuration:
        - default_tolerance: Decimal("1e-10")
        - convergence_max_iterations: 5
        - convergence_tolerance: Decimal("0.001")
    """
    return {
        "default_tolerance": Decimal("1e-10"),
        "convergence_max_iterations": 5,
        "convergence_tolerance": Decimal("0.001"),
        "symmetry_tolerance_pct": Decimal("0.1"),
        "arbitrage_tolerance_pct": Decimal("0.1"),
    }
