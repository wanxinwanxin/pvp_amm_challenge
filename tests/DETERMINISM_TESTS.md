# Determinism and Stability Testing

## Overview

The `test_determinism.py` module provides comprehensive testing to verify that AMM simulations are reproducible with fixed random seeds and maintain bit-exact precision across multiple runs.

## Test File

**Location:** `/Users/xinwan/Github/pvp_amm_challenge/tests/test_determinism.py`

## Test Coverage

### 1. TestDeterministicRoutingDecisions

Verifies that routing decisions (how trades are split across AMMs) are bit-exact reproducible.

**Tests:**
- `test_constant_fee_routing_deterministic()` - Constant fee structures
- `test_tiered_fee_routing_deterministic()` - Two-tier fee structures
- `test_three_tier_routing_deterministic()` - Three-tier fee structures

**Key Assertions:**
```python
# Splits must be bit-exact identical
assert amt1 == amt2  # Decimal comparison
```

### 2. TestDeterministicExecutionPrices

Verifies that execution prices are reproducible with Decimal precision.

**Tests:**
- `test_execution_prices_bit_exact()` - Constant fees
- `test_tiered_fee_execution_prices_stable()` - Tiered fees

**Key Assertions:**
```python
# Prices must match exactly (Decimal, not float)
assert p1 == p2
```

### 3. TestDeterministicPnLCalculation

Verifies that profit/loss calculations are stable and reproducible.

**Tests:**
- `test_pnl_bit_exact_reproduction()` - Constant fees
- `test_tiered_pnl_stability()` - Tiered fees

**Key Assertions:**
```python
# PnLs must be bit-exact identical
assert pnl1 == pnl2
```

### 4. TestMultipleRunsIdenticalResults

Verifies that running the same scenario multiple times produces identical results.

**Tests:**
- `test_five_runs_constant_fees()` - 5 runs with constant fees
- `test_five_runs_tiered_fees()` - 5 runs with tiered fees

**Coverage:**
- All Decimal values match
- Routing decisions identical
- Reserves, accumulated fees, and k invariant match
- PnL calculations match

### 5. TestRouterConvergenceStableSplits

Verifies that iterative router convergence produces stable, reproducible splits.

**Tests:**
- `test_convergence_identical_across_runs()` - Multiple runs produce same splits
- `test_convergence_with_various_trade_sizes()` - Stability across trade size range

**Trade Sizes Tested:**
- Tiny: 1
- Small: 10, 50
- Medium: 150 (crosses first tier)
- Large: 500
- Very large: 1500 (crosses second tier)
- Huge: 5000

**Key Features:**
- Tests both buy and sell directions
- Tests tier boundary crossing
- Verifies convergence is deterministic

### 6. TestDifferentSeedsDifferentResults

Verifies that different seeds produce different outcomes (ensures randomness works).

**Tests:**
- `test_different_seeds_produce_different_splits()` - Different seeds → different outcomes
- `test_same_seed_different_n_trades_diverges()` - Different trade counts → different end states
- `test_each_seed_is_reproducible()` - Each seed is individually reproducible

**Purpose:**
Ensures the randomness system is working correctly while each seed remains reproducible.

### 7. TestAMMStateReproducibility

Verifies that AMM state variables are exactly reproducible.

**Tests:**
- `test_reserves_bit_exact_identical()` - Reserve values match exactly
- `test_accumulated_fees_bit_exact_identical()` - Fee accumulation matches
- `test_spot_price_reproducible()` - Spot prices match

**State Variables Tested:**
- `reserve_x`
- `reserve_y`
- `accumulated_fees_x`
- `accumulated_fees_y`
- `k` (constant product invariant)
- `spot_price` (derived from reserves)

## Implementation Details

### SimulationResult Dataclass

Captures complete simulation state for comparison:

```python
@dataclass
class SimulationResult:
    amm_snapshots: List[AMMStateSnapshot]  # Final AMM states
    splits: List[Tuple[str, Decimal]]      # All routing decisions
    execution_prices: List[Decimal]        # All trade prices
    final_pnls: List[Tuple[str, Decimal]]  # Final PnLs per AMM
    total_trades: int                       # Trade count
```

Implements `__eq__` for bit-exact comparison of all Decimal fields.

### Helper Functions

#### `create_amm_set_for_test()`
Creates standard AMM sets with configurable fee structures:
- `"constant"` - Flat 30bps fee
- `"two_tier"` - 30bps → 20bps
- `"three_tier"` - 30bps → 20bps → 10bps

#### `generate_trade_sequence()`
Generates deterministic trade sequences using a seeded RNG:
- Side: Buy/sell randomly selected
- Size: Between 25 and 125 (log-normal-ish)
- Same seed always produces same sequence

#### `run_simulation()`
Executes a complete simulation:
1. Takes initial AMM snapshots
2. Generates deterministic trades
3. Routes trades optimally
4. Records splits, prices, and state
5. Calculates final PnLs

## Design Principles

### 1. Decimal Precision
All comparisons use `Decimal` type for bit-exact precision:
```python
assert amt1 == amt2  # NOT: abs(amt1 - amt2) < epsilon
```

### 2. Fixed Seeds
Every test uses explicit seeds for reproducibility:
```python
seed = 42
results = run_simulation(amms, seed=seed)
```

### 3. Detailed Error Messages
Failures show exactly what differs:
```python
assert amt1 == amt2, \
    f"Split {i} ({name}): Different amounts: {amt1} vs {amt2} (diff: {abs(amt1 - amt2)})"
```

### 4. Comprehensive Coverage
Tests cover:
- Constant and tiered fee structures
- Two-tier and three-tier configurations
- Multiple AMM counts (1, 2, 3)
- Buy and sell directions
- Various trade sizes

## Running the Tests

### Run all determinism tests:
```bash
pytest tests/test_determinism.py -v
```

### Run specific test class:
```bash
pytest tests/test_determinism.py::TestDeterministicRoutingDecisions -v
```

### Run with detailed output:
```bash
pytest tests/test_determinism.py -v -s
```

## Expected Behavior

### Success Criteria
- All tests pass with bit-exact comparisons
- No epsilon tolerances needed
- Same seed always produces identical results
- Different seeds produce different results
- Convergence is stable and deterministic

### What Tests Verify

1. **Reproducibility:** Same seed → identical results
2. **Stability:** Multiple runs → same outcome
3. **Precision:** Decimal comparisons (not floats)
4. **Convergence:** Iterative router converges identically
5. **Randomness:** Different seeds → different outcomes
6. **State Integrity:** All AMM state variables match exactly

## Integration with Existing Tests

This module complements:
- `test_backward_compatibility.py` - Version compatibility
- `test_economic_fixtures.py` - Economic correctness
- `test_tiered_routing.py` - Routing algorithm correctness
- `test_fee_tiers.py` - Fee calculation accuracy

## Failure Diagnosis

### If splits differ:
```
Split 5 (AMM2): Different amounts: 123.456 vs 123.457 (diff: 0.001)
```
- Check for float contamination
- Verify Decimal → float → Decimal conversions
- Inspect router iteration logic

### If prices differ:
```
Price 10: 1.234567890123 vs 1.234567890124 (diff: 1E-12)
```
- Check execution path uses Decimal
- Verify fee calculations maintain precision
- Inspect constant product formula

### If PnLs differ:
```
PnL for AMM1: 45.123 vs 45.124 (diff: 0.001)
```
- Check accumulated fees calculation
- Verify reserve updates are exact
- Inspect snapshot/PnL calculation logic

### If convergence differs:
```
Run 2, split 3 (buy, 150): AMM1 amounts differ: 75.12 vs 75.13
```
- Check iterative convergence tolerance
- Verify effective fee calculations
- Inspect termination conditions

## Performance Considerations

- Tests use `create_amm_set_for_test()` which creates fresh AMMs per run
- Simulations with 50 trades typically complete in <100ms
- 5-run comparison tests complete in <500ms
- Tiered fee convergence adds ~2-3 iterations overhead

## Maintenance

### Adding New Test Cases
1. Use `create_amm_set_for_test()` for AMM setup
2. Use `generate_trade_sequence()` for deterministic trades
3. Use `run_simulation()` for execution
4. Compare `SimulationResult` instances for bit-exact equality

### Testing New Fee Structures
```python
# Add to create_amm_set_for_test()
elif fee_structure == "custom_tier":
    amm = create_tiered_fee_amm(
        name,
        [(Decimal("0"), Decimal("0.005")),
         (Decimal("50"), Decimal("0.001"))],
        reserve_x,
        reserve_y,
    )
```

### Testing Edge Cases
```python
def test_extreme_imbalance():
    """Test with extremely imbalanced pools."""
    reserve_x, reserve_y = get_pool_balance(PoolBalanceProfile.EXTREME)
    # Test with reserve_x = 1, reserve_y = 1000000
```

## Known Limitations

1. **Float Conversion:** Router uses float internally for math.sqrt performance
   - Converts Decimal → float → Decimal
   - Small precision loss possible (tested to be negligible)

2. **Iterative Convergence:** Tiered fee router uses tolerance = 0.001 (0.1%)
   - Typically converges in 2-3 iterations
   - Max 5 iterations enforced

3. **Pairwise Approximation:** For N > 2 AMMs, uses pairwise splitting
   - Near-optimal for N ≤ 5
   - May not be globally optimal for N > 5

## Future Enhancements

1. **Extended Precision Tests:**
   - Test with higher Decimal precision (128-bit)
   - Verify no precision loss in float conversions

2. **Convergence Analysis:**
   - Track iteration counts
   - Measure convergence rates
   - Verify monotonic improvement

3. **Performance Benchmarks:**
   - Compare constant vs tiered fee performance
   - Measure router overhead
   - Profile hot paths

4. **Edge Case Coverage:**
   - Zero reserves
   - Extremely large trades
   - Pathological fee structures

## References

- AMM implementation: `/Users/xinwan/Github/pvp_amm_challenge/amm_competition/core/amm.py`
- Router implementation: `/Users/xinwan/Github/pvp_amm_challenge/amm_competition/market/router.py`
- Economic fixtures: `/Users/xinwan/Github/pvp_amm_challenge/tests/fixtures/economic_fixtures.py`
- Fee tiers: `/Users/xinwan/Github/pvp_amm_challenge/amm_competition/core/trade.py`
