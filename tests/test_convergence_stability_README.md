# Convergence Stability Testing Module

## Overview

The `test_convergence_stability.py` module provides comprehensive testing of the iterative routing algorithm's convergence behavior across a wide range of scenarios. This ensures that the router can reliably handle real-world fee structures and edge cases without infinite loops or failures.

## Test Coverage

### 1. TestConvergenceWithinMaxIterations

Verifies that all scenarios converge within the maximum iteration limit (5 iterations).

**Test Cases:**
- `test_convergence_conservative_tiers`: Conservative fee structures (30→20→10 bps)
- `test_convergence_moderate_tiers`: Moderate fee structures (30→15→5 bps)
- `test_convergence_aggressive_tiers`: Aggressive fee structures (50→10→1 bps)
- `test_convergence_mixed_fee_structures`: Mix of constant and tiered fees
- `test_convergence_no_infinite_loops`: Pathological cases with guaranteed termination

**Acceptance Criteria:**
- All tests complete without exceptions
- Solutions sum to total amount (within 0.1% tolerance)
- Execution time < 100ms even for pathological cases

### 2. TestConvergenceQualityWellBehavedTiers

Tests solution quality for well-behaved fee tier profiles, expecting convergence in 2-3 iterations.

**Test Cases:**
- `test_quality_conservative_equal_pools`: Equal pools should split near-equally
- `test_quality_moderate_converges_quickly`: Multiple trade sizes converge with high accuracy
- `test_quality_asymmetric_pools_reasonable_split`: Asymmetric pools produce sensible splits

**Acceptance Criteria:**
- Convergence in 2-3 iterations (fast)
- High accuracy: deviation < 0.1%
- Reasonable split ratios based on pool characteristics

### 3. TestConvergencePathologicalTiers

Tests convergence with pathological fee profiles (steep transitions: 100%→1bp→0.1bp).

**Test Cases:**
- `test_pathological_completes_without_exception`: Must complete successfully
- `test_pathological_accepts_suboptimal_solution`: Accept reasonable but not optimal solutions
- `test_pathological_steep_transitions_stable`: No oscillation with extreme transitions

**Acceptance Criteria:**
- No exceptions raised
- Algorithm completes within 5 iterations
- Deviation < 1% (relaxed tolerance)
- Non-negative splits

### 4. TestConvergenceExtremeTradeSizes

Tests convergence across extreme trade size ranges.

**Test Cases:**
- `test_tiny_trade_size`: Decimal("0.001") - very small trades
- `test_small_trade_size`: Decimal("1.0") - small but not tiny
- `test_huge_trade_size`: Decimal("100000") - very large trades
- `test_extreme_range_of_sizes`: Full range from 0.001 to 50000

**Acceptance Criteria:**
- All sizes converge successfully
- Tiny trades: < 5% deviation acceptable
- Normal/large trades: < 0.1% deviation
- No numerical instabilities

### 5. TestConvergenceExtremeTierThresholds

Tests convergence with extreme tier threshold configurations.

**Test Cases:**
- `test_very_high_thresholds`: Thresholds at 100k and 1M
- `test_very_low_thresholds`: Thresholds at 0.1 and 1
- `test_mixed_threshold_scales`: Different threshold scales across AMMs

**Acceptance Criteria:**
- Converges regardless of threshold scale
- Normal trades work even if they don't reach high tiers
- Mixed scales don't cause issues

### 6. TestConvergenceSingleTierBoundary

Tests stability when trades occur exactly at tier boundaries.

**Test Cases:**
- `test_trade_exactly_at_boundary`: Trade size exactly equals tier threshold
- `test_multiple_boundaries`: Multiple boundaries don't cause instability
- `test_straddling_boundary`: Trades spanning boundaries converge smoothly

**Acceptance Criteria:**
- No oscillation at boundaries
- Smooth convergence
- Non-negative splits

### 7. TestConvergenceIdenticalAMMs

Tests convergence when routing through identical AMMs (should converge in 1-2 iterations).

**Test Cases:**
- `test_identical_constant_fee_equal_split`: Constant fee AMMs split equally
- `test_identical_tiered_equal_split`: Tiered fee AMMs split near-equally
- `test_identical_converges_fast`: Fast convergence (< 5ms)

**Acceptance Criteria:**
- Near-equal splits (within 5%)
- Very fast convergence (1-2 iterations)
- Execution time < 5ms

### 8. TestConvergenceSellDirection

Tests that sell direction converges as reliably as buy direction.

**Test Cases:**
- `test_sell_conservative_tiers`: Conservative tiers in sell direction
- `test_sell_pathological_completes`: Pathological tiers complete
- `test_sell_identical_equal_split`: Identical AMMs split equally

**Acceptance Criteria:**
- Same reliability as buy direction
- Similar convergence characteristics
- Near-equal splits for identical AMMs

### 9. TestConvergenceMultipleAMMs

Tests convergence with more than 2 AMMs (uses pairwise approximation).

**Test Cases:**
- `test_three_amms_converge`: Three AMMs converge reliably
- `test_five_amms_converge`: Five AMMs converge (recommended max)

**Acceptance Criteria:**
- All splits sum to total
- Reasonable execution time (< 20ms for 5 AMMs)
- Valid splits produced

## Helper Classes

### ConvergenceMonitor

Utility class for tracking convergence metrics:

```python
monitor = ConvergenceMonitor()
metrics = monitor.verify_convergence(splits, total_amount)
```

**Metrics Returned:**
- `valid`: Whether splits sum to total (within tolerance)
- `max_deviation`: Maximum deviation from expected total
- `num_splits`: Number of non-zero splits
- `min_split_ratio`: Smallest split as fraction of total
- `max_split_ratio`: Largest split as fraction of total

## Running the Tests

### Run all convergence tests:
```bash
pytest tests/test_convergence_stability.py -v
```

### Run specific test class:
```bash
pytest tests/test_convergence_stability.py::TestConvergencePathologicalTiers -v
```

### Run with detailed output:
```bash
pytest tests/test_convergence_stability.py -v --tb=short
```

### Using the test runner script:
```bash
python run_convergence_tests.py
```

## Interpretation of Results

### Expected Behavior

**Well-Behaved Cases (Conservative/Moderate):**
- Convergence in 2-3 iterations
- Deviation < 0.1%
- Fast execution (< 5ms for 2 AMMs)

**Pathological Cases:**
- Convergence within 5 iterations (may hit max)
- Deviation < 1% acceptable
- Solution may be sub-optimal but reasonable

**Edge Cases:**
- Tiny trades: 5% deviation acceptable
- Boundary trades: No oscillation
- Identical AMMs: Near-equal splits (< 5% deviation)

### Warning Signs

The following would indicate issues with the convergence algorithm:

1. **Test Failures**: Any test raising exceptions
2. **Timeout**: Tests taking > 100ms
3. **Invalid Splits**: Splits not summing to total
4. **Negative Amounts**: Any negative split amounts
5. **Excessive Deviation**: > 1% deviation on well-behaved cases

## Integration with Development Workflow

### Pre-Commit Checks
```bash
# Run convergence tests before committing routing changes
pytest tests/test_convergence_stability.py -v
```

### Continuous Integration
These tests should be included in CI pipelines to catch regressions in convergence behavior.

### Performance Benchmarking
The tests include timing assertions that serve as performance benchmarks:
- 2 AMMs, well-behaved: < 5ms
- 2 AMMs, pathological: < 100ms
- 5 AMMs, well-behaved: < 20ms

## Future Extensions

Potential additions to the test suite:

1. **Convergence Rate Analysis**: Track actual iteration counts
2. **Solution Quality Metrics**: Compare to analytical optimal solutions
3. **Stress Testing**: Test with 10+ AMMs (beyond recommended limit)
4. **Numerical Stability**: Test with very large or very small token amounts
5. **Fee Tier Combinations**: Test all combinations of 1/2/3 tier structures

## References

- Router Implementation: `/amm_competition/market/router.py`
- Fee Tier Definition: `/amm_competition/core/trade.py`
- Economic Fixtures: `/tests/fixtures/economic_fixtures.py`
- Router Convergence Tests: `/tests/test_router_convergence.py` (basic tests)

## Test Maintenance

When modifying the router algorithm:

1. **Run all convergence tests** to ensure no regressions
2. **Check performance benchmarks** haven't degraded
3. **Add new test cases** for any new convergence scenarios
4. **Update max_iterations** if algorithm changes require it
5. **Verify pathological cases** still complete successfully

## Contact

For questions about convergence testing or algorithm behavior, refer to:
- Main routing documentation: `20250210-complete-tiered-fee-routing.md`
- Economic correctness tests: `tests/test_economic_correctness.py`
- Original convergence tests: `tests/test_router_convergence.py`
