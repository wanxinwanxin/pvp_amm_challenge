# Economic Correctness Test Suite

## Overview

This comprehensive test suite verifies the economic properties of the AMM competition system, particularly focusing on the transition from constant fees to tiered fee structures with iterative routing. The tests ensure that the system maintains fairness, determinism, and fundamental economic invariants while supporting more sophisticated fee strategies.

The suite uses **Decimal precision** for all monetary calculations to ensure accurate financial accounting and avoid floating-point errors that could accumulate over multiple trades.

## Test Philosophy

Rather than running full competition simulations (which are slow and hard to debug), we use **focused integration tests** that:
- Target specific economic properties
- Use controlled scenarios with 2-5 AMMs
- Execute in milliseconds for fast CI feedback
- Provide clear failure messages when properties are violated

## Test Categories

### 1. Backward Compatibility (`test_backward_compatibility.py`)

**Purpose:** Verify that constant-fee strategies behave identically between the old system (constant fees only) and new system (tiered fees with constant fee fallback).

**What it tests:**
- Single AMM routing (trivial split, tests execution)
- Two AMM routing (optimal split computation)
- Five AMM routing (N-way split with N <= 5 constraint)
- Both buy and sell directions
- Multiple trade sizes (small, medium, large)
- Final state matching (reserves, fees, k-invariant)

**Acceptance criteria:**
- Splits match within 0.01% relative error
- Execution prices match within 1e-10 (Decimal precision)
- Final reserves match within 1e-10
- PnLs match within 0.001%

**Example:**
```python
def test_two_amms_buy_medium():
    """Test that two constant-fee AMMs produce identical routing."""
    amms = [
        create_constant_fee_amm("LowFee", Decimal("0.002"), ...),
        create_constant_fee_amm("HighFee", Decimal("0.004"), ...),
    ]
    order = RetailOrder(side="buy", size=Decimal("1000"))
    comparison = run_parallel_simulations(order, amms, fair_price)

    assert comparison.splits_match  # Within 0.01%
    assert comparison.prices_match  # Within 1e-10
    assert comparison.reserves_match  # Within 1e-10
```

### 2. Symmetry & Fairness (`test_symmetry_fairness.py`)

**Purpose:** Verify that identical or similar strategies compete fairly and produce symmetric outcomes.

**What it tests:**
- Identical constant-fee strategies produce identical PnL
- Identical tiered strategies produce identical PnL
- Near-identical strategies have proportional PnL differences
- Routing gives competitive AMMs fair access to flow
- Results are consistent across multiple random seeds

**Acceptance criteria:**
- Identical strategies: PnL difference < 0.1% of total volume
- Similar strategies: PnL proportional to fee advantage (within 5%)
- Flow distribution matches expected optimal split (within 1%)

**Example:**
```python
def test_identical_constant_strategies_symmetric_pnl():
    """Two identical constant-fee AMMs should earn identical PnL."""
    amms = [
        create_constant_fee_amm("AMM_A", Decimal("0.003"), ...),
        create_constant_fee_amm("AMM_B", Decimal("0.003"), ...),
    ]

    # Execute random trades
    execute_random_trades(amms, num_trades=100, seed=42)

    # Check PnL symmetry
    pnl_a = calculate_pnl(snapshots_before["AMM_A"], snapshots_after["AMM_A"])
    pnl_b = calculate_pnl(snapshots_before["AMM_B"], snapshots_after["AMM_B"])

    is_symmetric, diff_pct = verify_symmetry(pnl_a, pnl_b, tolerance_pct=Decimal("0.1"))
    assert is_symmetric
```

### 3. Determinism (`test_determinism.py`)

**Purpose:** Ensure that simulations are reproducible with fixed random seeds.

**What it tests:**
- Same seed produces identical routing decisions
- Same seed produces identical execution prices
- Same seed produces identical final states
- Different seeds produce different but valid results

**Acceptance criteria:**
- Two runs with same seed match exactly (bit-for-bit)
- Two runs with different seeds produce different outcomes
- All runs satisfy other economic properties regardless of seed

**Example:**
```python
def test_deterministic_routing_with_fixed_seed():
    """Same seed should produce identical routing."""
    amms1 = create_amm_set()
    amms2 = create_amm_set()  # Fresh copies

    trades1 = execute_random_trades(amms1, num_trades=50, seed=42)
    trades2 = execute_random_trades(amms2, num_trades=50, seed=42)

    # Should be identical
    assert trades1 == trades2
    for amm1, amm2 in zip(amms1, amms2):
        assert snapshot_amm_state(amm1) == snapshot_amm_state(amm2)
```

### 4. No Arbitrage (`test_no_arbitrage.py`)

**Purpose:** Verify that the system doesn't create exploitable arbitrage opportunities.

**What it tests:**
- Buy-then-sell cycles should not generate profit (accounting for fees)
- Sell-then-buy cycles should not generate profit
- Cross-AMM arbitrage is not profitable after fees
- Large trades don't create exploitable price impact arbitrage

**Acceptance criteria:**
- Round-trip trades result in net loss equal to fees paid (within 0.1%)
- No positive arbitrage profit found in systematic testing
- Price impact is monotonic (larger trades = worse execution)

**Example:**
```python
def test_no_arbitrage_buy_sell_cycle():
    """Buy-then-sell should result in net loss equal to fees."""
    amms = create_amm_set()

    initial_states = {amm.name: snapshot_amm_state(amm) for amm in amms}

    # Execute buy then sell
    buy_amount = Decimal("1000")
    x_received = execute_buy(amms, buy_amount)
    y_received = execute_sell(amms, x_received)

    final_states = {amm.name: snapshot_amm_state(amm) for amm in amms}

    # Net position should be negative (lost to fees)
    net_position = y_received - buy_amount
    total_fees = calculate_total_fees(initial_states, final_states)

    # Net loss should approximately equal fees paid
    assert net_position < 0
    assert abs(abs(net_position) - total_fees) / total_fees < Decimal("0.001")
```

### 5. Optimal Routing (`test_optimal_routing.py`)

**Purpose:** Verify that split routing achieves better execution than single-AMM routing.

**What it tests:**
- Router splits outperform best single AMM
- Router splits achieve near-optimal execution (within 0.1% of analytical optimal)
- Tiered fee routing converges in 2-3 iterations
- Mixed constant/tiered routing is handled correctly

**Acceptance criteria:**
- Split execution better than any single AMM by > 0.01%
- Within 0.1% of analytical optimal (where computable)
- Convergence achieved in <= 5 iterations for 95% of cases
- Final split is stable (further iterations don't improve)

**Example:**
```python
def test_split_routing_outperforms_single_amm():
    """Router split should beat best single AMM."""
    amms = create_amm_set()
    trade_size = Decimal("1000")

    # Get optimal split execution
    split_trades = router.execute_optimal_split_buy(amms, trade_size)
    split_price = calculate_effective_execution_price(split_trades)

    # Try each AMM individually
    single_prices = []
    for amm in amms:
        test_amm = clone_amm(amm)
        trade = test_amm.execute_buy_x_with_y(trade_size, timestamp=0)
        single_prices.append(trade.execution_price)

    best_single_price = min(single_prices)  # Lower is better for buy

    # Split should beat best single
    assert split_price < best_single_price
    improvement = (best_single_price - split_price) / best_single_price
    assert improvement > Decimal("0.0001")  # At least 0.01% better
```

### 6. Accounting Correctness (`test_accounting.py`)

**Purpose:** Verify value conservation and proper fee accounting.

**What it tests:**
- Sum of all PnLs equals zero (closed system)
- Fees collected by AMMs equal fees paid by traders
- Constant product invariant (k = x * y) preserved for reserves
- No token creation or destruction
- Accurate tracking of accumulated fees

**Acceptance criteria:**
- Sum(PnLs) within 1e-10 of zero
- Fees match within 0.001% relative error
- k-invariant preserved within 0.0001% (accounting for fees)
- Token totals match across all states

**Example:**
```python
def test_value_conservation_across_trades():
    """Total value should be conserved across all trades."""
    amms = create_amm_set()

    initial_states = [snapshot_amm_state(amm) for amm in amms]

    # Execute multiple trades
    trades = execute_random_trades(amms, num_trades=100, seed=42)

    final_states = [snapshot_amm_state(amm) for amm in amms]

    # Verify conservation
    is_valid, error = verify_value_conservation(
        trades, initial_states, final_states, tolerance=Decimal("0.0001")
    )
    assert is_valid, error
```

### 7. Convergence Stability (`test_convergence.py`)

**Purpose:** Verify that the iterative routing algorithm converges reliably.

**What it tests:**
- Typical fee structures converge in 2-3 iterations
- Pathological fee structures converge or hit max iterations gracefully
- Convergence tolerance is appropriate (0.1%)
- Non-convergence cases still produce valid (suboptimal) splits

**Acceptance criteria:**
- 95% of realistic cases converge in <= 3 iterations
- 100% of cases either converge or terminate at max iterations (5)
- Non-converged results are still economically valid
- Convergence is monotonic (splits improve or stabilize each iteration)

**Example:**
```python
def test_convergence_typical_tiers():
    """Typical tiered structures should converge quickly."""
    amms = [
        create_constant_fee_amm("Constant", Decimal("0.003"), ...),
        create_tiered_fee_amm("Tiered", get_baseline_fee_tiers("moderate"), ...),
    ]

    convergence_data = router.compute_optimal_split_buy_with_metrics(
        amms, Decimal("1000")
    )

    assert convergence_data.converged
    assert convergence_data.iterations <= 3
    assert convergence_data.final_change < Decimal("0.001")
```

### 8. Edge Cases (`test_edge_cases.py`)

**Purpose:** Test extreme scenarios and boundary conditions.

**What it tests:**
- Very small trades (< 1 token)
- Very large trades (>> pool reserves)
- Extremely skewed pools (1:1000000 ratio)
- Pathological fee structures (100% -> 0.1% -> 0.01%)
- Zero-fee strategies
- Single-tier "tiered" strategies (equivalent to constant)

**Acceptance criteria:**
- No crashes or exceptions
- Results are mathematically valid (no negative amounts, NaN, infinity)
- Economic properties still hold (accounting, no arbitrage)
- Degrades gracefully at limits

**Example:**
```python
def test_extreme_trade_size():
    """Very large trade should not break system."""
    amms = create_amm_set(PoolBalanceProfile.BALANCED)

    # Trade 10x larger than any pool
    huge_trade = Decimal("100000")

    # Should not crash
    splits = router.compute_optimal_split_buy(amms, huge_trade)

    # Should produce valid split
    assert all(amount >= 0 for _, amount in splits)
    assert sum(amount for _, amount in splits) == huge_trade

    # Should still conserve value
    # ... accounting checks ...
```

## Test Organization

### Directory Structure

```
tests/
├── README.md                          # This file
├── conftest.py                        # Shared fixtures and configuration
├── pytest.ini                         # Pytest settings (at project root)
├── __init__.py                        # Package marker
│
├── fixtures/                          # Reusable test data
│   ├── __init__.py
│   ├── README.md                      # Fixture documentation
│   └── economic_fixtures.py           # AMM creation, snapshots, PnL
│
├── utils/                             # Test utilities
│   ├── __init__.py
│   ├── economic_verification.py       # Property verification functions
│   └── version_comparison.py          # Old vs new system comparison
│
├── test_fee_tiers.py                  # Unit tests for FeeTier/FeeQuote
├── test_backward_compatibility.py     # Backward compatibility suite
├── test_symmetry_fairness.py          # Symmetry and fairness tests
├── test_determinism.py                # Determinism tests
├── test_no_arbitrage.py               # No-arbitrage tests
├── test_optimal_routing.py            # Routing optimality tests
├── test_accounting.py                 # Value conservation tests
├── test_convergence.py                # Convergence stability tests
└── test_edge_cases.py                 # Edge case and stress tests
```

### Fixtures and Utilities

**Shared fixtures** (defined in `conftest.py`):
- `standard_amm_set`: 5 AMMs with diverse fee structures
- `balanced_pools`: Equal X and Y reserves
- `skewed_pools`: Imbalanced reserves for edge testing
- `fair_price`: Standard price of 1.0 for testing

**Utility functions** (in `tests/utils/`):
- `create_constant_fee_amm()`: Create constant-fee AMM
- `create_tiered_fee_amm()`: Create tiered-fee AMM
- `snapshot_amm_state()`: Capture immutable state
- `calculate_pnl()`: Compute profit/loss between snapshots
- `verify_value_conservation()`: Check accounting correctness
- `verify_no_arbitrage()`: Detect arbitrage opportunities
- `verify_symmetry()`: Compare PnLs for fairness

## Quick Start

### Running All Tests

```bash
# Run entire economic test suite
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=amm_competition --cov-report=html

# Run specific test category
pytest tests/test_backward_compatibility.py -v

# Run tests matching a pattern
pytest tests/ -k "constant_fee" -v
```

### Running by Marker

```bash
# Run only backward compatibility tests
pytest tests/ -m backward_compat -v

# Run only slow tests (> 5 seconds)
pytest tests/ -m slow -v

# Run everything except slow tests
pytest tests/ -m "not slow" -v

# Run economic property tests
pytest tests/ -m economic -v

# Run edge case tests
pytest tests/ -m edge_case -v
```

### Running with Output Options

```bash
# Show print statements and detailed output
pytest tests/ -v -s

# Show only failures
pytest tests/ --tb=short

# Stop on first failure
pytest tests/ -x

# Run in parallel (requires pytest-xdist)
pytest tests/ -n auto
```

### Running Specific Tests

```bash
# Run single test file
pytest tests/test_symmetry_fairness.py -v

# Run single test class
pytest tests/test_backward_compatibility.py::TestConstantFeeSingleAMM -v

# Run single test method
pytest tests/test_backward_compatibility.py::TestConstantFeeSingleAMM::test_single_amm_buy_small -v
```

### Debugging Failed Tests

```bash
# Enter debugger on failure
pytest tests/ --pdb

# Show local variables in tracebacks
pytest tests/ -l

# Verbose output with full diff
pytest tests/ -vv
```

## Test Markers

Tests are organized using pytest markers for selective execution:

- `@pytest.mark.backward_compat` - Backward compatibility tests
- `@pytest.mark.economic` - Core economic property tests
- `@pytest.mark.edge_case` - Edge cases and stress tests
- `@pytest.mark.integration` - Integration tests (multi-component)
- `@pytest.mark.slow` - Tests taking > 5 seconds

## Adding New Tests

### Step 1: Choose Test Category

Determine which test file your test belongs in:
- **Unit tests for new features**: Create new file following naming convention
- **Economic property tests**: Add to appropriate category file
- **Edge cases**: Add to `test_edge_cases.py`

### Step 2: Use Fixtures

Leverage existing fixtures for consistency:

```python
import pytest
from decimal import Decimal
from tests.fixtures.economic_fixtures import (
    create_constant_fee_amm,
    create_amm_set,
    snapshot_amm_state,
    calculate_pnl,
)

def test_my_property():
    """Test description following Google style."""
    # Use fixtures to create test scenario
    amms = create_amm_set(PoolBalanceProfile.BALANCED)

    # Take initial snapshots
    initial_states = {amm.name: snapshot_amm_state(amm) for amm in amms}

    # Execute test logic
    # ...

    # Verify property
    final_states = {amm.name: snapshot_amm_state(amm) for amm in amms}
    # ... assertions ...
```

### Step 3: Add Appropriate Markers

```python
@pytest.mark.economic
@pytest.mark.integration
def test_my_economic_property():
    """Test an economic invariant."""
    pass

@pytest.mark.edge_case
@pytest.mark.slow
def test_extreme_scenario():
    """Test behavior at extreme values."""
    pass
```

### Step 4: Document Expected Behavior

```python
def test_new_property():
    """Test that new property holds under conditions.

    This test verifies that [property] holds when [conditions].

    Acceptance criteria:
    - Criterion 1: [specific threshold]
    - Criterion 2: [specific behavior]

    Example:
        >>> # Minimal example demonstrating the property
    """
    pass
```

### Step 5: Use Decimal Precision

Always use `Decimal` for monetary calculations:

```python
from decimal import Decimal

# GOOD
fee = Decimal("0.003")
amount = Decimal("1000")
result = amount * (Decimal("1") - fee)

# BAD
fee = 0.003  # Float precision errors!
amount = 1000
result = amount * (1 - fee)
```

### Step 6: Add to CI

Tests are automatically discovered by pytest. Ensure:
- File name starts with `test_`
- Class name starts with `Test`
- Method name starts with `test_`
- File is in `tests/` directory

## Acceptance Criteria Summary

### Backward Compatibility
- ✓ Splits match within 0.01%
- ✓ Prices match within 1e-10
- ✓ Reserves match within 1e-10
- ✓ PnLs match within 0.001%

### Symmetry & Fairness
- ✓ Identical strategies: PnL difference < 0.1%
- ✓ Similar strategies: PnL proportional to fee advantage (±5%)
- ✓ Flow distribution matches optimal split (±1%)

### Determinism
- ✓ Same seed produces bit-for-bit identical results
- ✓ Different seeds produce different but valid results

### No Arbitrage
- ✓ Round-trip loss equals fees paid (±0.1%)
- ✓ No positive arbitrage in systematic testing

### Optimal Routing
- ✓ Split beats best single AMM by > 0.01%
- ✓ Within 0.1% of analytical optimal
- ✓ Converges in <= 5 iterations (95% in <= 3)

### Accounting Correctness
- ✓ Sum(PnLs) within 1e-10 of zero
- ✓ Fees match within 0.001%
- ✓ k-invariant preserved within 0.0001%

### Convergence Stability
- ✓ 95% of cases converge in <= 3 iterations
- ✓ 100% either converge or terminate gracefully
- ✓ Non-converged results still valid

### Edge Cases
- ✓ No crashes on extreme inputs
- ✓ Results mathematically valid
- ✓ Economic properties still hold

## Continuous Integration

Tests run automatically on:
- Every push to `main` or `develop`
- Every pull request
- Python versions: 3.10, 3.11, 3.12

CI workflow includes:
- Dependency installation
- All economic test modules
- Coverage report generation
- Coverage artifact upload

See `.github/workflows/economic-tests.yml` for configuration.

## Troubleshooting

### Test Failures

**Symptom:** Tests pass locally but fail in CI

**Common causes:**
- Random seed not set (non-deterministic behavior)
- Platform-specific behavior (use `Decimal`, not `float`)
- Uninitialized state (AMMs not reset between tests)

**Solutions:**
```python
# Always set seed for randomness
random.seed(42)

# Use Decimal for monetary values
amount = Decimal("1000")  # Not: 1000 or 1000.0

# Reset AMM state between tests (use fixtures)
@pytest.fixture
def fresh_amms():
    return create_amm_set()  # New instances each time
```

**Symptom:** Accounting tests fail with small differences

**Common causes:**
- Floating-point accumulation errors
- Incorrect PnL calculation
- Fee rounding differences

**Solutions:**
```python
# Use appropriate tolerance for Decimal comparisons
assert abs(actual - expected) < Decimal("1e-10")

# Check relative error, not absolute
relative_error = abs(actual - expected) / expected
assert relative_error < Decimal("0.0001")  # 0.01%
```

**Symptom:** Convergence tests fail intermittently

**Common causes:**
- Pathological fee structures
- Tolerance too tight
- Iteration limit too low

**Solutions:**
```python
# Use realistic fee structures for most tests
tiers = get_baseline_fee_tiers("moderate")  # Not "pathological"

# Have separate tests for edge cases
@pytest.mark.edge_case
def test_pathological_convergence():
    # May not converge, that's okay
    result = router.compute_split_with_metrics(...)
    assert result.iterations <= MAX_ITERATIONS  # Just check it terminates
```

### Performance Issues

**Symptom:** Tests take too long

**Common causes:**
- Too many random trades in test
- Large trade sizes causing slow convergence
- Inefficient test setup

**Solutions:**
```python
# Use smaller trade counts for fast tests
execute_random_trades(amms, num_trades=10, seed=42)  # Not 1000

# Mark slow tests appropriately
@pytest.mark.slow
def test_large_simulation():
    execute_random_trades(amms, num_trades=1000, seed=42)

# Use parameterization instead of loops
@pytest.mark.parametrize("size", [10, 100, 1000])
def test_various_sizes(size):
    # Faster than loop with 1000 sizes
```

### Import Errors

**Symptom:** `ModuleNotFoundError` or `ImportError`

**Solutions:**
```bash
# Install package in development mode
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Ensure PYTHONPATH includes project root
export PYTHONPATH=/path/to/pvp_amm_challenge:$PYTHONPATH
```

### Decimal Precision Issues

**Symptom:** Unexpected precision errors or rounding

**Solutions:**
```python
from decimal import Decimal, getcontext

# Set appropriate precision (default 28 is usually fine)
getcontext().prec = 28

# Use string literals, not floats
correct = Decimal("0.003")
wrong = Decimal(0.003)  # Introduces float error!

# Round explicitly when needed
result = (amount * rate).quantize(Decimal("0.000001"))
```

## Contributing

When contributing tests:

1. **Follow existing patterns**: Look at similar tests for structure
2. **Use fixtures**: Leverage `conftest.py` and `economic_fixtures.py`
3. **Use Decimal**: All monetary values must use `Decimal`
4. **Add docstrings**: Explain what property is being tested
5. **Mark appropriately**: Add relevant pytest markers
6. **Test locally first**: Run full suite before submitting PR
7. **Update documentation**: If adding new category, update this README

## Additional Resources

- **Fixture Documentation**: `tests/fixtures/README.md`
- **Implementation Plan**: `20260210-economic-correctness-tests.md`
- **Tiered Fee Documentation**: `20250210-complete-tiered-fee-routing.md`
- **Backward Compatibility Status**: `tests/BACKWARD_COMPATIBILITY_STATUS.md`
- **Pytest Documentation**: https://docs.pytest.org/

## Contact

For questions about the test suite:
- Check existing test files for examples
- Review fixture documentation in `tests/fixtures/README.md`
- Consult implementation plan documents in project root
