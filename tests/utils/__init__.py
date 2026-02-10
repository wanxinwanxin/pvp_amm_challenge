"""Economic verification utilities for AMM testing.

This package provides functions to verify economic correctness properties
such as value conservation, no arbitrage, optimal routing, and fee accounting.

Also includes backward compatibility testing utilities for comparing old and
new router implementations.
"""

from tests.utils.economic_verification import (
    calculate_effective_execution_price,
    verify_fee_accounting,
    verify_no_arbitrage,
    verify_optimal_routing,
    verify_symmetry,
    verify_value_conservation,
)
from tests.utils.version_comparison import (
    OldRouter,
    NewRouter,
    SplitComparison,
    ExecutionComparison,
    compare_splits,
    compare_routing_decisions,
    run_parallel_simulations,
)

__all__ = [
    # Economic verification
    "calculate_effective_execution_price",
    "verify_fee_accounting",
    "verify_no_arbitrage",
    "verify_optimal_routing",
    "verify_symmetry",
    "verify_value_conservation",
    # Version comparison
    "OldRouter",
    "NewRouter",
    "SplitComparison",
    "ExecutionComparison",
    "compare_splits",
    "compare_routing_decisions",
    "run_parallel_simulations",
]
