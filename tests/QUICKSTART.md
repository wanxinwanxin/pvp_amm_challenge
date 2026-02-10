# Economic Tests Quick Start Guide

## Installation

```bash
# Install package with development dependencies
pip install -e ".[dev]"

# Verify installation
pytest --version
pytest --co tests/  # Collect tests without running
```

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run specific test file
pytest tests/test_backward_compatibility.py

# Run specific test class
pytest tests/test_backward_compatibility.py::TestConstantFeeSingleAMM

# Run specific test method
pytest tests/test_backward_compatibility.py::TestConstantFeeSingleAMM::test_single_amm_buy_small
```

### By Category (Markers)

```bash
# Backward compatibility tests only
pytest tests/ -m backward_compat

# Economic property tests
pytest tests/ -m economic

# Edge case tests
pytest tests/ -m edge_case

# Exclude slow tests
pytest tests/ -m "not slow"

# Multiple markers (AND)
pytest tests/ -m "economic and not slow"

# Multiple markers (OR)
pytest tests/ -m "backward_compat or economic"
```

### Coverage

```bash
# Run with coverage report
pytest tests/ --cov=amm_competition

# Generate HTML coverage report
pytest tests/ --cov=amm_competition --cov-report=html
# Open htmlcov/index.html in browser

# Generate terminal report with missing lines
pytest tests/ --cov=amm_competition --cov-report=term-missing

# Fail if coverage below threshold
pytest tests/ --cov=amm_competition --cov-fail-under=80
```

### Output Control

```bash
# Show print statements
pytest tests/ -s

# Short traceback format
pytest tests/ --tb=short

# Only show failures
pytest tests/ --tb=line

# Stop on first failure
pytest tests/ -x

# Stop after N failures
pytest tests/ --maxfail=3
```

### Performance

```bash
# Show slowest 10 tests
pytest tests/ --durations=10

# Run tests in parallel (requires pytest-xdist)
pytest tests/ -n auto

# Run with timeout (requires pytest-timeout)
pytest tests/ --timeout=60
```

## Common Test Patterns

### Test Specific Size

```bash
# Run tests with "small" in name
pytest tests/ -k "small"

# Run tests with "buy" in name
pytest tests/ -k "buy"

# Exclude tests with "large" in name
pytest tests/ -k "not large"
```

### Test Specific AMM Configuration

```bash
# Tests with constant fees
pytest tests/ -k "constant_fee"

# Tests with tiered fees
pytest tests/ -k "tiered"

# Tests with identical strategies
pytest tests/ -k "identical"
```

### Test Specific Properties

```bash
# Symmetry tests
pytest tests/test_symmetry_fairness.py

# Arbitrage tests
pytest tests/test_no_arbitrage.py

# Accounting tests
pytest tests/test_accounting.py
```

## Debugging

```bash
# Enter debugger on failure
pytest tests/ --pdb

# Enter debugger on error (not assertion failures)
pytest tests/ --pdb --pdbcls=IPython.terminal.debugger:Pdb

# Show local variables in tracebacks
pytest tests/ -l

# Very verbose output
pytest tests/ -vv

# Show full diff for failed assertions
pytest tests/ -vv
```

## CI Simulation

```bash
# Run the same tests as CI (fast tests only)
pytest tests/ -m "not slow" --cov=amm_competition --cov-report=xml

# Run slow tests separately (like CI)
pytest tests/ -m slow

# Check test execution time
timeout 300 pytest tests/ -m "not slow" || echo "Tests took > 5 minutes!"
```

## Expected Results

### Passing Tests

```
tests/test_backward_compatibility.py::TestConstantFeeSingleAMM::test_single_amm_buy_small PASSED [ 10%]
tests/test_backward_compatibility.py::TestConstantFeeSingleAMM::test_single_amm_sell_small PASSED [ 20%]
...
======================== 50 passed in 3.42s ========================
```

### Coverage Report

```
Name                                    Stmts   Miss Branch BrPart  Cover
-------------------------------------------------------------------------
amm_competition/core/amm.py              120      5     30      2    94%
amm_competition/core/trade.py             85      2     15      1    96%
amm_competition/market/router.py         180     10     45      3    92%
-------------------------------------------------------------------------
TOTAL                                    385     17     90      6    94%
```

### Performance

Expected execution times:
- **Unit tests** (test_fee_tiers.py): < 1 second
- **Backward compatibility**: 1-2 seconds
- **Symmetry tests**: 1-2 seconds
- **All fast tests**: < 5 minutes
- **Slow tests**: 5-15 minutes

## Troubleshooting

### Import Errors

```bash
# Ensure package is installed
pip install -e .

# Check Python path
python -c "import amm_competition; print(amm_competition.__file__)"
```

### Test Discovery Issues

```bash
# List all discovered tests
pytest --collect-only tests/

# Check for syntax errors
pytest --collect-only tests/ -v
```

### Decimal Precision Errors

```python
# Always use string literals for Decimal
from decimal import Decimal

# GOOD
amount = Decimal("0.003")

# BAD - introduces float precision errors
amount = Decimal(0.003)
```

### Random Test Failures

```python
# Always set seed for reproducibility
import random
random.seed(42)

# Or use fixtures
def test_with_seed(fixed_seed):
    random.seed(fixed_seed)
    # ... test code ...
```

### Slow Test Execution

```bash
# Identify slow tests
pytest tests/ --durations=0

# Run in parallel
pytest tests/ -n auto

# Run subset for quick feedback
pytest tests/ -m "not slow" -k "small"
```

## Useful Aliases

Add to your shell configuration (.bashrc, .zshrc):

```bash
# Quick test aliases
alias pt='pytest tests/'
alias ptv='pytest tests/ -v'
alias ptc='pytest tests/ --cov=amm_competition --cov-report=html'
alias ptf='pytest tests/ -x -v'  # Stop on first failure
alias pts='pytest tests/ -m "not slow"'  # Fast tests only
alias ptb='pytest tests/ -m backward_compat'  # Backward compat
alias pte='pytest tests/ -m economic'  # Economic tests
```

## Next Steps

- Read the full test documentation: `tests/README.md`
- Review fixture documentation: `tests/fixtures/README.md`
- Check implementation plans in project root
- Explore example tests for patterns
