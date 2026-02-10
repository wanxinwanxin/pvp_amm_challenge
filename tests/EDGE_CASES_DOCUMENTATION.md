# Edge Case and Stress Testing Documentation

## Overview

The `test_edge_cases.py` module provides comprehensive coverage of extreme scenarios and boundary conditions for the AMM system. All tests verify graceful degradation, numerical stability, and correctness under stress.

## Test Categories

### 1. Numerical Precision (`TestNumericalPrecision`)

Tests the system's ability to handle extreme numerical values without precision loss or overflow.

#### `test_tiny_trade_sizes_decimal_precision()`
- **Purpose**: Verify Decimal precision maintained for very small trades
- **Test Size**: `0.0001` X tokens
- **Verifies**:
  - Trade executes without rounding errors
  - Reserves update correctly
  - Fees calculated accurately
  - k invariant maintained within 0.0001% tolerance
- **Edge Case**: Minimum trade size close to Decimal precision limits

#### `test_huge_trade_sizes_no_overflow()`
- **Purpose**: Verify no arithmetic overflow with large values
- **Test Size**: `1,000,000` X tokens (10% of 10M reserves)
- **Verifies**:
  - Decimal handles large arithmetic operations
  - No overflow errors
  - Slippage and fees correct at scale
  - k invariant maintained within 0.001% tolerance
- **Edge Case**: Maximum practical trade size

### 2. Extreme Pool States (`TestExtremePoolStates`)

Tests router and AMM behavior with pathological pool configurations.

#### `test_extreme_pool_imbalance()`
- **Purpose**: Handle severely imbalanced liquidity pools
- **Configuration**:
  - Imbalanced pool: (1, 1,000,000) - ratio 1:1,000,000
  - Balanced pool: (10,000, 10,000)
- **Verifies**:
  - Router routes mostly to balanced pool (>90%)
  - No division by zero errors
  - Optimal split computed correctly
- **Edge Case**: 6 orders of magnitude pool imbalance

#### `test_zero_liquidity_pool_handling()`
- **Purpose**: Handle nearly empty pools gracefully
- **Configuration**:
  - Empty pool: (0.01, 0.01)
  - Full pool: (10,000, 10,000)
- **Verifies**:
  - Router minimizes empty pool usage (<0.1%)
  - No division by zero errors
  - Trades route to liquid pools
- **Edge Case**: Near-zero liquidity

#### `test_very_similar_amms()`
- **Purpose**: Test numerical stability with identical AMMs
- **Configuration**: 3 identical AMMs with same reserves and fees
- **Verifies**:
  - Router splits approximately equally (within 5%)
  - No pathological behavior
  - Pairwise approximation works correctly
- **Edge Case**: Zero differentiation between pools

### 3. Extreme Fee Structures (`TestExtremeFeeStructures`)

Tests handling of unusual fee configurations.

#### `test_all_fees_zero_edge_case()`
- **Purpose**: Verify routing with zero-fee AMMs
- **Configuration**: Two AMMs with 0% fees
- **Verifies**:
  - No division by zero (gamma = 1)
  - Optimal splits based on reserves only
  - Larger pool gets more flow
- **Edge Case**: Zero fee rate

#### `test_all_fees_maximum_edge_case()`
- **Purpose**: Handle very high fee rates
- **Configuration**: AMM with 10% (1000 bps) fee
- **Verifies**:
  - Trades execute with expensive fees
  - Fee collection accurate (10 X from 100 X trade)
  - Net reserves correct (90 X to reserves)
- **Edge Case**: Maximum practical fee rate

#### `test_single_tier_at_boundaries()`
- **Purpose**: Verify correct tier selection at thresholds
- **Configuration**: 3-tier structure (30→20→10 bps)
- **Test Points**:
  - Exactly at tier 0 (size = 0)
  - Exactly at tier 1 threshold (size = 100)
  - Just past tier 1 (size = 101)
  - Exactly at tier 2 threshold (size = 1000)
- **Verifies**:
  - Correct weighted average calculations
  - No off-by-one errors
  - Boundary handling exact
- **Edge Case**: Tier boundary conditions

### 4. Trade Patterns (`TestTradePatterns`)

Tests complex trading sequences and their impact on system state.

#### `test_many_small_trades_vs_one_large()`
- **Purpose**: Verify path independence and precision
- **Comparison**:
  - 100 trades of 10 X each
  - 1 trade of 1000 X
- **Verifies**:
  - Final states within 0.1% of each other
  - No accumulation errors
  - Fees identical (same total size)
- **Edge Case**: Trade fragmentation

#### `test_alternating_buy_sell()`
- **Purpose**: Test stability under oscillating trades
- **Pattern**: 50 cycles of buy/sell 100 X each
- **Verifies**:
  - No drift (<1% from initial reserves)
  - Fees collected on both sides
  - Fee balance approximately equal
- **Edge Case**: Cyclical trading pattern

### 5. Router Edge Cases (`TestRouterEdgeCases`)

Tests router-specific boundary conditions and convergence.

#### `test_router_with_pathological_fee_tiers()`
- **Purpose**: Handle extreme tier transitions
- **Configuration**: Pathological tiers (10000→1→0.1 bps)
- **Test Cases**:
  - Small trade (0.5 X) - should avoid pathological
  - Large trade (1000 X) - both pools used
- **Verifies**:
  - Router adapts to trade size
  - No numerical instability
  - Convergence to valid solution
- **Edge Case**: Discontinuous fee structure

#### `test_router_convergence_with_tiered_fees()`
- **Purpose**: Verify iterative refinement converges
- **Configuration**: Two tiered-fee AMMs with different profiles
- **Verifies**:
  - Deterministic results (same split every time)
  - Convergence within 5 iterations
  - Total preserved exactly
- **Edge Case**: Iterative optimization convergence

### 6. Stress Scenarios (`TestStressScenarios`)

Combined stress tests mixing multiple edge cases.

#### `test_mixed_extreme_amms()`
- **Purpose**: Test router with multiple pathological AMMs
- **Configuration**:
  - Empty pool (0.01, 0.01)
  - Imbalanced pool (1, 100,000)
  - High fee pool (5%)
  - Normal pool
- **Verifies**:
  - Router handles heterogeneous set
  - No exceptions or crashes
  - Normal pool gets most flow (>50%)
- **Edge Case**: Multiple simultaneous pathologies

#### `test_continuous_trading_stability()`
- **Purpose**: Long-term stability under load
- **Pattern**: 1000 trades with alternating direction and varying sizes
- **Verifies**:
  - k invariant maintained (<0.01% drift)
  - Substantial fees collected
  - No numerical drift
- **Edge Case**: Sustained high-volume trading

## Key Verification Principles

### 1. No Exceptions or Crashes
All tests must complete without raising exceptions, even with pathological inputs.

### 2. Graceful Degradation
System should handle extreme cases by routing around problems (e.g., avoiding empty pools) rather than failing.

### 3. Numerical Stability
- Decimal precision maintained throughout
- k invariant preserved (within tolerance)
- No accumulation of rounding errors

### 4. Correct Fee Handling
- Fees always positive
- Correct tier selection
- Weighted averages accurate

### 5. Router Optimality
- Valid splits (non-negative, sum to total)
- Reasonable distribution based on pool states
- Convergence for iterative methods

## Tolerance Levels

Different tolerance levels are used based on test characteristics:

- **Exact**: `< 0.000001` (0.0001%) - For single trades
- **Tight**: `< 0.0001` (0.01%) - For k invariant after simple operations
- **Standard**: `< 0.001` (0.1%) - For comparing equivalent operations
- **Relaxed**: `< 0.01` (1%) - For long trading sequences
- **Loose**: `< 0.05` (5%) - For approximate equality (e.g., equal splits)

## Running the Tests

```bash
# Run all edge case tests
pytest tests/test_edge_cases.py -v

# Run specific test class
pytest tests/test_edge_cases.py::TestNumericalPrecision -v

# Run specific test
pytest tests/test_edge_cases.py::TestNumericalPrecision::test_tiny_trade_sizes_decimal_precision -v

# Run with coverage
pytest tests/test_edge_cases.py --cov=amm_competition --cov-report=html
```

## Expected Results

All tests should pass with status `PASSED`. Any failures indicate:

1. **Numerical instability**: Check Decimal usage and k invariant maintenance
2. **Router issues**: Verify split algorithms and convergence logic
3. **Fee calculation errors**: Check tier boundaries and weighted averages
4. **Precision loss**: Verify all arithmetic uses Decimal, not float (except in fast paths)

## Integration with Other Tests

This module complements:

- **`test_fee_tiers.py`**: Basic fee tier functionality
- **`test_tiered_routing.py`**: Router behavior with tiered fees
- **`test_router_convergence.py`**: Convergence properties
- **`test_backward_compatibility.py`**: Regression testing

Edge case tests focus on **extreme scenarios** that normal tests don't cover, ensuring robustness under stress.

## Maintenance

When adding new features:

1. **Add edge cases** for new boundaries
2. **Test extreme values** for new parameters
3. **Verify numerical stability** for new calculations
4. **Update tolerance levels** if precision changes

## Summary Statistics

- **Total Test Methods**: 15
- **Test Classes**: 6
- **Edge Cases Covered**:
  - Numerical: 2 (tiny, huge)
  - Pool States: 3 (imbalanced, empty, identical)
  - Fees: 3 (zero, maximum, boundaries)
  - Patterns: 2 (fragmented, cyclical)
  - Router: 2 (pathological, convergence)
  - Stress: 2 (mixed, continuous)
- **Coverage Areas**:
  - AMM execution engine
  - Fee calculation (constant and tiered)
  - Router optimal splitting
  - Numerical precision
  - Long-term stability
