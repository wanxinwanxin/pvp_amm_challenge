# Backward Compatibility Testing Infrastructure

This document describes the backward compatibility testing infrastructure for verifying that constant-fee strategies behave identically between the old router (constant fees only) and the new router (tiered fees with constant fee fallback).

## Overview

The backward compatibility testing system ensures that the new router implementation with tiered fee support maintains 100% compatibility with the old router when used with constant-fee AMMs. This is critical because:

1. Existing strategies using constant fees must produce identical results
2. Any differences could indicate bugs in the new implementation
3. Traders should see no difference in execution quality for constant-fee AMMs

## Architecture

### Core Components

#### 1. Version Comparison Framework (`tests/utils/version_comparison.py`)

The comparison framework provides utilities for running parallel simulations and comparing results.

**Classes:**

- `OldRouter`: Wrapper around old router implementation from commit 217d5ad
  - Uses constant fees only (ignores tier information)
  - Provides clean API matching new router interface

- `NewRouter`: Wrapper around current router implementation
  - Supports both constant fees (fast path) and tiered fees (iterative refinement)
  - Should produce identical results to old router for constant-fee AMMs

- `SplitComparison`: Comparison of how each router split order flow across AMMs
  - Tracks absolute and relative differences
  - Provides `matches` property for tolerance checking (0.01%)

- `ExecutionComparison`: Comprehensive comparison of execution results
  - Execution prices (weighted average across AMMs)
  - Split allocations per AMM
  - Final AMM state differences (reserves, fees)
  - Convenience methods: `prices_match`, `splits_match`, `reserves_match`

**Key Functions:**

- `compare_splits(old_splits, new_splits)`: Compare split decisions
  - Returns list of `SplitComparison` objects
  - Validates that same AMMs are covered
  - Calculates absolute and percentage differences

- `run_parallel_simulations(order, amms, fair_price)`: Execute matched trades
  - Creates independent AMM copies for each router
  - Executes same order through both routers
  - Returns comprehensive `ExecutionComparison`
  - Uses Decimal precision throughout

- `compare_routing_decisions(order, amms, fair_price)`: Compare splits without execution
  - Useful for pure split algorithm testing
  - No state changes to AMMs
  - Returns (comparisons, all_match) tuple

#### 2. Test Suite (`tests/test_backward_compatibility.py`)

Comprehensive test suite organized by scenario complexity.

### Test Organization

#### Single AMM Tests (`TestConstantFeeSingleAMM`)

Simplest case - all flow goes to one AMM. Tests basic execution mechanics.

- `test_single_amm_buy_small`: Small buy order
- `test_single_amm_buy_large`: Large buy order
- `test_single_amm_sell_small`: Small sell order
- `test_single_amm_sell_large`: Large sell order

**Expected:** 100% identical results (trivial routing).

#### Two AMM Tests (`TestConstantFeeTwoAMMs`)

Most critical test class - two-AMM case is the base case for optimal splitting.

- `test_two_identical_amms_buy/sell`: Identical AMMs should split 50/50
- `test_two_different_fees_buy/sell`: Lower fee AMM gets more flow
- `test_two_different_reserves_buy/sell`: Larger AMM gets more flow
- `test_two_skewed_reserves_buy`: Different price levels

**Expected:** Exact match on splits, prices, and final states.

#### Five AMM Tests (`TestConstantFeeFiveAMMs`)

Multi-AMM routing uses pairwise approximation. Tests scalability.

- `test_five_identical_amms_buy/sell`: Equal splits across identical AMMs
- `test_five_varied_fees_buy/sell`: Flow distributed by fee level
- `test_five_varied_reserves_buy`: Flow distributed by liquidity

**Expected:** Exact match despite pairwise approximation.

#### Execution Price Tests (`TestIdenticalExecutionPrices`)

Focuses specifically on execution price matching.

- Tests small and large orders in both directions
- Verifies price difference < 1e-10
- Most important metric for traders

#### Split Allocation Tests (`TestIdenticalSplits`)

Tests split decisions in isolation (without execution).

- `test_split_decision_only_buy/sell`: Pure algorithm comparison
- `test_splits_multiple_sizes`: Various trade sizes

#### Direction Tests (`TestBuyAndSellDirections`)

Comprehensive testing of both trade directions.

- `test_symmetric_buy_sell_pair`: Matching buy/sell orders
- `test_asymmetric_fees_both_directions`: Different fees both ways

#### Edge Case Tests (`TestEdgeCases`)

Boundary conditions and extreme scenarios.

- `test_zero_fee_amm`: Zero-fee AMM handling
- `test_very_small_order`: Minimal order size
- `test_extreme_reserve_imbalance`: Pathological pool states

## Acceptance Criteria

Tests pass when the following criteria are met:

### 1. Split Tolerance: 0.01%

Split allocations must match within 0.01% relative difference:

```python
relative_diff_pct = (new_amount - old_amount) / max(old_amount, new_amount) * 100
assert abs(relative_diff_pct) < 0.01
```

### 2. Execution Price Tolerance: 1e-10

Execution prices must match within Decimal precision (1e-10):

```python
price_diff = abs(new_price - old_price)
assert price_diff < Decimal("1e-10")
```

### 3. Reserve Tolerance: 1e-10

Final reserve states must match within Decimal precision:

```python
x_diff = abs(new_reserve_x - old_reserve_x)
y_diff = abs(new_reserve_y - old_reserve_y)
assert x_diff < Decimal("1e-10")
assert y_diff < Decimal("1e-10")
```

### 4. PnL Tolerance: 0.001%

Profit and loss calculations must match within 0.001%:

```python
pnl_diff_pct = abs((new_pnl - old_pnl) / old_pnl * 100)
assert pnl_diff_pct < 0.001
```

## Usage

### Running Tests

Run all backward compatibility tests:

```bash
pytest tests/test_backward_compatibility.py -v
```

Run specific test class:

```bash
pytest tests/test_backward_compatibility.py::TestConstantFeeTwoAMMs -v
```

Run single test:

```bash
pytest tests/test_backward_compatibility.py::TestConstantFeeTwoAMMs::test_two_identical_amms_buy -v
```

### Using the Comparison Framework

Example of comparing routing decisions:

```python
from decimal import Decimal
from amm_competition.market.retail import RetailOrder
from tests.fixtures.economic_fixtures import create_constant_fee_amm
from tests.utils.version_comparison import run_parallel_simulations

# Create constant-fee AMMs
amms = [
    create_constant_fee_amm("AMM1", Decimal("0.003"), Decimal("10000"), Decimal("10000")),
    create_constant_fee_amm("AMM2", Decimal("0.003"), Decimal("10000"), Decimal("10000")),
]

# Create order
order = RetailOrder(side="buy", size=Decimal("1000"))
fair_price = Decimal("1.0")

# Run parallel simulations
comparison = run_parallel_simulations(order, amms, fair_price)

# Check results
print(f"Splits match: {comparison.splits_match}")
print(f"Prices match: {comparison.prices_match}")
print(f"Reserves match: {comparison.reserves_match}")

# Detailed split comparison
for sc in comparison.split_comparisons:
    print(f"{sc.amm_name}:")
    print(f"  Old: {sc.old_amount}")
    print(f"  New: {sc.new_amount}")
    print(f"  Diff: {sc.relative_diff_pct}%")
```

Example of comparing just split decisions:

```python
from tests.utils.version_comparison import compare_routing_decisions

# Compare splits without execution
comparisons, all_match = compare_routing_decisions(order, amms, fair_price)

print(f"All splits match: {all_match}")
for comp in comparisons:
    print(f"{comp.amm_name}: {comp.relative_diff_pct}%")
```

## Implementation Details

### Router Fast Path Detection

The new router detects constant-fee AMMs and uses a fast path:

```python
# In _split_buy_two_amms:
has_tiers = (amm1.current_fees.ask_tiers is not None or
             amm2.current_fees.ask_tiers is not None)

if not has_tiers:
    return self._split_buy_two_amms_constant(amm1, amm2, total_y)
```

This ensures constant-fee AMMs get the original algorithm, guaranteeing identical behavior.

### AMM Copying for Independent Execution

Each router gets independent AMM copies to avoid cross-contamination:

```python
def _deep_copy_amm(amm: AMM) -> AMM:
    new_amm = AMM(
        strategy=amm.strategy,
        reserve_x=amm.reserve_x,
        reserve_y=amm.reserve_y,
        name=amm.name,
    )
    new_amm.current_fees = amm.current_fees
    new_amm._initialized = amm._initialized
    new_amm.accumulated_fees_x = amm.accumulated_fees_x
    new_amm.accumulated_fees_y = amm.accumulated_fees_y
    return new_amm
```

### Decimal Precision

All monetary values use Python's `Decimal` type for precision:

- No floating-point rounding errors
- Exact comparisons possible at 1e-10 tolerance
- Critical for financial calculations

## Testing Philosophy

### Deterministic Testing

All tests use:
- Fixed reserve amounts (no randomness)
- Fixed fee rates
- Fixed order sizes
- No random seeds required

This ensures:
- Tests are reproducible
- Failures are debuggable
- CI/CD is reliable

### Comprehensive Coverage

Tests cover:
- All AMM counts: 1, 2, 5
- Both directions: buy, sell
- Multiple sizes: small, medium, large
- Various fee structures: identical, different, zero
- Various pool sizes: balanced, skewed, extreme

### Layered Testing

Tests are organized in layers:
1. Split decisions (pure algorithm)
2. Execution prices (trader perspective)
3. Final states (accounting correctness)
4. Edge cases (robustness)

## Debugging Failed Tests

If a test fails, examine the comparison object:

```python
def test_example():
    comparison = run_parallel_simulations(order, amms, fair_price)

    if not comparison.splits_match:
        for sc in comparison.split_comparisons:
            if not sc.matches:
                print(f"SPLIT MISMATCH: {sc.amm_name}")
                print(f"  Old: {sc.old_amount}")
                print(f"  New: {sc.new_amount}")
                print(f"  Diff: {sc.absolute_diff} ({sc.relative_diff_pct}%)")

    if not comparison.prices_match:
        print(f"PRICE MISMATCH:")
        print(f"  Old: {comparison.old_execution_price}")
        print(f"  New: {comparison.new_execution_price}")
        print(f"  Diff: {comparison.price_diff} ({comparison.price_diff_pct}%)")

    if not comparison.reserves_match:
        for name, (x_diff, y_diff) in comparison.reserve_diffs.items():
            print(f"RESERVE MISMATCH: {name}")
            print(f"  X diff: {x_diff}")
            print(f"  Y diff: {y_diff}")
```

## Maintenance

### When to Update Tests

Update tests when:
1. Adding new router features (ensure backward compatibility)
2. Changing split algorithms (verify constant-fee path unchanged)
3. Modifying AMM execution logic (verify consistency)

### What Not to Test

These tests focus on constant-fee AMMs only:
- Do NOT test tiered fee behavior here
- Do NOT test iterative refinement convergence here
- Do NOT test new features that don't affect constant fees

For tiered fee testing, see:
- `tests/test_tiered_routing.py`
- `tests/test_router_convergence.py`

## References

- Old router implementation: `tests/utils/old_router.py` (from commit 217d5ad)
- New router implementation: `amm_competition/market/router.py`
- Economic fixtures: `tests/fixtures/economic_fixtures.py`
- AMM core: `amm_competition/core/amm.py`
