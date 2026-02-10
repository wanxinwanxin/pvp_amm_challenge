# Testing Guide

## Overview

This document provides a high-level overview of the testing infrastructure for the AMM competition system. For detailed information, see the documentation in the `tests/` directory.

## Test Suite Structure

The project includes a comprehensive economic correctness test suite that verifies the system maintains fairness, determinism, and fundamental economic invariants.

### Quick Links

- **[Tests README](tests/README.md)** - Comprehensive guide to all test categories
- **[Quick Start](tests/QUICKSTART.md)** - Common commands and workflows
- **[Test Architecture](tests/TEST_ARCHITECTURE.md)** - Detailed architecture documentation
- **[Fixtures](tests/fixtures/README.md)** - Reusable test fixtures and utilities

## Installation

```bash
# Clone repository
git clone https://github.com/yourusername/pvp_amm_challenge.git
cd pvp_amm_challenge

# Install with development dependencies
pip install -e ".[dev]"

# Verify installation
pytest --version
```

## Running Tests

### Quick Commands

```bash
# Run all fast tests (< 5 minutes)
pytest tests/ -m "not slow"

# Run with coverage
pytest tests/ --cov=amm_competition --cov-report=html

# Run specific category
pytest tests/ -m backward_compat  # Backward compatibility
pytest tests/ -m economic         # Economic properties
pytest tests/ -m edge_case        # Edge cases
```

### Common Workflows

```bash
# Development: Fast feedback on changes
pytest tests/ -x -v  # Stop on first failure

# Pre-commit: Run fast tests before committing
pytest tests/ -m "not slow" --tb=short

# Pre-push: Run all tests including slow ones
pytest tests/ --tb=short

# CI simulation: Same as GitHub Actions
pytest tests/ -m "not slow" --cov=amm_competition
```

See **[Quick Start](tests/QUICKSTART.md)** for more commands.

## Test Categories

### 1. Unit Tests (`test_fee_tiers.py`)

Validates individual components:
- FeeTier creation and validation
- FeeQuote constant fee mode
- FeeQuote tiered fee mode with weighted averages
- Edge cases and boundary conditions

**Run:** `pytest tests/test_fee_tiers.py -v`

### 2. Backward Compatibility (`test_backward_compatibility.py`)

Ensures constant-fee strategies behave identically between old and new systems:
- Single AMM, two AMM, and five AMM scenarios
- Both buy and sell directions
- Multiple trade sizes

**Acceptance:** Splits, prices, and reserves match within tight tolerances

**Run:** `pytest tests/ -m backward_compat`

### 3. Symmetry & Fairness (`test_symmetry_fairness.py`)

Verifies identical strategies compete fairly:
- Identical constant-fee strategies produce symmetric PnL
- Identical tiered strategies produce symmetric PnL
- Similar strategies have proportional PnL differences

**Acceptance:** PnL difference < 0.1% for identical strategies

**Run:** `pytest tests/test_symmetry_fairness.py -v`

### 4. Determinism (`test_determinism.py`)

Ensures reproducibility with fixed random seeds:
- Same seed produces identical results
- Different seeds produce different but valid results

**Acceptance:** Bit-for-bit identical results with same seed

**Run:** `pytest tests/test_determinism.py -v`

### 5. No Arbitrage (`test_no_arbitrage.py`)

Verifies no exploitable arbitrage opportunities:
- Buy-then-sell cycles result in net loss equal to fees
- Cross-AMM arbitrage is not profitable

**Acceptance:** Round-trip loss equals fees paid (±0.1%)

**Run:** `pytest tests/test_no_arbitrage.py -v`

### 6. Optimal Routing (`test_optimal_routing.py`)

Verifies routing achieves near-optimal execution:
- Split routing beats best single AMM
- Tiered fee routing converges in 2-3 iterations
- Results within 0.1% of analytical optimal

**Acceptance:** Split beats single AMM by > 0.01%, converges in ≤ 5 iterations

**Run:** `pytest tests/test_optimal_routing.py -v`

### 7. Accounting Correctness (`test_accounting.py`)

Verifies value conservation and fee accounting:
- Sum of all PnLs equals zero
- Fees collected equal fees paid
- Constant product invariant preserved

**Acceptance:** Sum(PnLs) within 1e-10, fees match within 0.001%

**Run:** `pytest tests/test_accounting.py -v`

### 8. Convergence Stability (`test_convergence.py`)

Verifies iterative routing converges reliably:
- Typical structures converge in 2-3 iterations
- Pathological structures terminate gracefully
- Non-converged results still valid

**Acceptance:** 95% converge in ≤ 3 iterations, 100% in ≤ 5

**Run:** `pytest tests/test_convergence.py -v`

### 9. Edge Cases (`test_edge_cases.py`)

Tests extreme scenarios:
- Very small and very large trades
- Extremely skewed pools
- Pathological fee structures

**Acceptance:** No crashes, mathematically valid results

**Run:** `pytest tests/ -m edge_case`

## Continuous Integration

Tests run automatically via GitHub Actions on:
- Every push to `main` or `develop`
- Every pull request
- Manual workflow dispatch

### CI Workflow

The workflow includes:
- **Matrix testing**: Python 3.10, 3.11, 3.12 on Ubuntu and macOS
- **Fast tests**: Unit tests, backward compatibility, economic properties (< 5 min)
- **Slow tests**: Long-running tests in separate job (< 15 min)
- **Coverage**: Generate and upload coverage reports
- **Performance**: Verify fast tests complete in < 5 minutes
- **Lint**: Ruff and mypy checks

**Configuration:** `.github/workflows/economic-tests.yml`

### Status Badges

Add to your README:

```markdown
![Tests](https://github.com/yourusername/pvp_amm_challenge/workflows/Economic%20Correctness%20Tests/badge.svg)
[![codecov](https://codecov.io/gh/yourusername/pvp_amm_challenge/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/pvp_amm_challenge)
```

## Acceptance Criteria

All tests enforce specific acceptance criteria:

| Category | Criteria |
|----------|----------|
| **Backward Compatibility** | Splits ±0.01%, prices ±1e-10, reserves ±1e-10 |
| **Symmetry** | Identical strategies: PnL diff < 0.1% |
| **Arbitrage** | Round-trip loss = fees ±0.1% |
| **Routing** | Split beats single by >0.01%, converges in ≤5 iterations |
| **Accounting** | Sum(PnLs) ±1e-10, fees ±0.001%, k-invariant ±0.0001% |
| **Convergence** | 95% in ≤3 iterations, 100% in ≤5 iterations |
| **Edge Cases** | No crashes, valid results, properties hold |

See **[Tests README](tests/README.md)** for detailed criteria.

## Test Fixtures

The suite provides reusable fixtures for common scenarios:

```python
# Standard AMM sets
def test_with_standard_amms(standard_amm_set):
    # 5 AMMs with diverse fee structures
    assert len(standard_amm_set) == 5

# Specific configurations
def test_with_balanced_pools(balanced_pools):
    # Equal X and Y reserves
    pass

# Trade sizes
def test_with_sizes(trade_sizes):
    # [10, 100, 1000, 5000]
    for size in trade_sizes:
        # Test each size
        pass

# Custom assertions
def test_symmetry(economic_assert):
    economic_assert.assert_symmetric_pnls(pnl_a, pnl_b)
```

See **[Fixtures README](tests/fixtures/README.md)** for all available fixtures.

## Writing New Tests

### Step 1: Choose Category

Determine which test file your test belongs in based on what property you're testing.

### Step 2: Use Fixtures

```python
import pytest
from decimal import Decimal
from tests.fixtures.economic_fixtures import (
    create_constant_fee_amm,
    snapshot_amm_state,
    calculate_pnl,
)

def test_my_property(standard_amm_set, fair_price):
    """Test description following Google style.

    Acceptance criteria:
    - Criterion 1
    - Criterion 2
    """
    # Use fixtures
    amms = standard_amm_set

    # Take snapshots
    initial_states = {amm.name: snapshot_amm_state(amm) for amm in amms}

    # Execute test logic
    # ...

    # Verify property
    final_states = {amm.name: snapshot_amm_state(amm) for amm in amms}
    # ... assertions ...
```

### Step 3: Add Markers

```python
@pytest.mark.economic
@pytest.mark.integration
def test_my_economic_property():
    """Test an economic invariant."""
    pass
```

### Step 4: Use Decimal Precision

```python
from decimal import Decimal

# ALWAYS use string literals for Decimal
fee = Decimal("0.003")  # GOOD
amount = Decimal("1000")

# NEVER use floats
fee = Decimal(0.003)  # BAD - introduces precision errors!
```

See **[Tests README](tests/README.md)** for detailed guidelines.

## Troubleshooting

### Common Issues

**Import errors:**
```bash
pip install -e .  # Install in development mode
```

**Decimal precision errors:**
```python
# Use string literals, not floats
amount = Decimal("0.003")  # Not: Decimal(0.003)
```

**Random test failures:**
```python
# Always set seed for reproducibility
random.seed(42)
```

**Slow tests:**
```bash
# Run only fast tests
pytest tests/ -m "not slow"

# Run in parallel
pytest tests/ -n auto
```

See **[Quick Start](tests/QUICKSTART.md)** for more troubleshooting tips.

## Performance

### Expected Execution Times

- **Unit tests**: < 1 second
- **Each integration test**: < 1 second
- **All fast tests**: < 5 minutes
- **Slow tests**: 5-15 minutes
- **Total CI time**: < 20 minutes

### Identifying Slow Tests

```bash
# Show slowest tests
pytest tests/ --durations=10

# Check for unmarked slow tests
pytest tests/ --durations=0 | grep -E "^[0-9.]+ s call" | awk '$1 > 5'
```

## Coverage

### Generating Reports

```bash
# Terminal report
pytest tests/ --cov=amm_competition

# HTML report (open htmlcov/index.html)
pytest tests/ --cov=amm_competition --cov-report=html

# With missing lines
pytest tests/ --cov=amm_competition --cov-report=term-missing
```

### Current Coverage

Target: **> 90%** coverage for core modules

```
amm_competition/core/amm.py       94%
amm_competition/core/trade.py     96%
amm_competition/market/router.py  92%
```

## Documentation

### Test Documentation

- **[tests/README.md](tests/README.md)** - Comprehensive test guide
- **[tests/QUICKSTART.md](tests/QUICKSTART.md)** - Quick reference
- **[tests/TEST_ARCHITECTURE.md](tests/TEST_ARCHITECTURE.md)** - Architecture details
- **[tests/fixtures/README.md](tests/fixtures/README.md)** - Fixture documentation

### Implementation Plans

- `20260210-economic-correctness-tests.md` - Test suite implementation plan
- `20250210-complete-tiered-fee-routing.md` - Tiered fee system plan
- `tests/BACKWARD_COMPATIBILITY.md` - Backward compatibility details

## Contributing

When contributing tests:

1. **Follow patterns**: Look at existing tests for structure
2. **Use fixtures**: Leverage shared fixtures from `conftest.py`
3. **Use Decimal**: All monetary values must use `Decimal`
4. **Add docstrings**: Explain what property is being tested
5. **Mark appropriately**: Add relevant pytest markers
6. **Test locally**: Run full suite before submitting PR

## Resources

- **Pytest Documentation**: https://docs.pytest.org/
- **Decimal Module**: https://docs.python.org/3/library/decimal.html
- **GitHub Actions**: https://docs.github.com/en/actions

## Support

For questions or issues:
1. Check the documentation in `tests/`
2. Review existing test files for examples
3. Check implementation plan documents
4. Open an issue on GitHub

## License

MIT License - See LICENSE file for details
