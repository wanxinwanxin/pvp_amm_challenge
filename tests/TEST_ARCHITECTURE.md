# Test Architecture

## Overview

This document describes the architecture and organization of the economic correctness test suite for the AMM competition system.

## Test Pyramid

```
                        ┌─────────────────────┐
                        │   Full Simulations  │  (Slow, covered separately)
                        │   (match runner)    │
                        └─────────────────────┘
                               ▲
                        ┌──────┴──────┐
                        │             │
              ┌─────────┴─────────────┴─────────┐
              │    Integration Tests             │  (2-3 seconds each)
              │  - Multi-AMM routing             │
              │  - Economic properties           │
              │  - Value conservation            │
              └──────────────────────────────────┘
                               ▲
                        ┌──────┴──────┐
                        │             │
              ┌─────────┴─────────────┴─────────┐
              │        Unit Tests                │  (< 1 second)
              │  - FeeTier validation            │
              │  - FeeQuote computation          │
              │  - Individual AMM execution      │
              └──────────────────────────────────┘
```

**Focus:** This test suite primarily focuses on the **Integration Tests** layer, providing fast feedback on economic properties without requiring full competition simulations.

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Test Suite                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────┐    ┌─────────────────┐                  │
│  │  Test Categories │    │    Fixtures     │                  │
│  │                  │    │                 │                  │
│  │  - Backward      │───▶│  - Standard AMM │                  │
│  │    Compat        │    │    Sets         │                  │
│  │  - Symmetry      │    │  - Pool Configs │                  │
│  │  - Arbitrage     │    │  - Price Data   │                  │
│  │  - Routing       │    │  - Seeds        │                  │
│  │  - Accounting    │    └─────────────────┘                  │
│  │  - Convergence   │             │                            │
│  │  - Edge Cases    │             │                            │
│  └──────────────────┘             │                            │
│           │                       │                            │
│           │                       ▼                            │
│           │           ┌─────────────────────┐                 │
│           └──────────▶│  Utility Functions  │                 │
│                       │                     │                 │
│                       │  - Value            │                 │
│                       │    Conservation     │                 │
│                       │  - No Arbitrage     │                 │
│                       │  - Symmetry Check   │                 │
│                       │  - PnL Calculation  │                 │
│                       └─────────────────────┘                 │
│                                │                               │
│                                ▼                               │
│                    ┌────────────────────────┐                 │
│                    │   Core System Under    │                 │
│                    │        Test            │                 │
│                    │                        │                 │
│                    │  - AMM Engine          │                 │
│                    │  - Router              │                 │
│                    │  - Trade Execution     │                 │
│                    └────────────────────────┘                 │
│                                                                │
└─────────────────────────────────────────────────────────────────┘
```

## Test Flow

### 1. Backward Compatibility Tests

```
┌─────────────────┐
│ Create AMMs     │  (Constant fee only)
│ (Old + New)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Execute Trade   │  (Same order)
│ in Both Systems │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Compare Results │
│ - Splits        │  ✓ Within 0.01%
│ - Prices        │  ✓ Within 1e-10
│ - Reserves      │  ✓ Within 1e-10
└─────────────────┘
```

### 2. Economic Property Tests

```
┌─────────────────┐
│ Setup AMMs      │  (Mixed constant/tiered)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Take Initial    │
│ Snapshots       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Execute Trades  │  (Random or specific)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Take Final      │
│ Snapshots       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Verify Property │
│ - Sum(PnL) = 0  │
│ - No Arbitrage  │
│ - Symmetry      │
└─────────────────┘
```

### 3. Convergence Tests

```
┌─────────────────┐
│ Create Tiered   │
│ AMMs            │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Route with      │
│ Metrics         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Check           │
│ - Converged?    │  ✓ 95% in ≤3 iters
│ - Iterations    │  ✓ 100% in ≤5 iters
│ - Improvement   │  ✓ Monotonic
└─────────────────┘
```

## Data Flow

```
┌──────────────┐
│  Test Input  │
│              │
│  - AMM count │
│  - Fee type  │
│  - Pool size │
│  - Trade dir │
│  - Trade size│
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Fixtures   │──────┐
│              │      │
│ Create AMMs  │      │
│ Set prices   │      │
│ Set seeds    │      │
└──────┬───────┘      │
       │              │
       ▼              │
┌──────────────┐      │
│   Execute    │      │
│    Trade     │      │
│              │      │
│  Router ────▶│      │
│  AMM Engine  │      │
└──────┬───────┘      │
       │              │
       ▼              │
┌──────────────┐      │
│   Collect    │      │
│    Data      │      │
│              │      │
│  - Trades    │      │
│  - States    │      │
│  - PnLs      │      │
└──────┬───────┘      │
       │              │
       ▼              │
┌──────────────┐      │
│   Verify     │◀─────┘
│  Properties  │
│              │  Utility Functions
│  Use Utils   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ Test Result  │
│              │
│  PASS/FAIL   │
└──────────────┘
```

## Test Categories Detail

### Unit Tests (test_fee_tiers.py)

**Purpose:** Validate individual components in isolation

```
FeeTier
  ├─ Creation and validation
  ├─ Threshold constraints
  └─ Fee constraints

FeeQuote (Constant)
  ├─ Basic creation
  ├─ Symmetric constructor
  └─ Effective fee (returns constant)

FeeQuote (Tiered)
  ├─ Single tier (equivalent to constant)
  ├─ Two tiers (weighted average)
  ├─ Three tiers (complex weighted average)
  ├─ Zero-size trade
  ├─ Asymmetric bid/ask tiers
  └─ Edge cases (boundary conditions)

FeeQuote Validation
  ├─ Empty tiers rejected
  ├─ Too many tiers rejected
  ├─ First tier must have threshold 0
  ├─ Non-increasing thresholds rejected
  └─ Decreasing thresholds rejected
```

### Integration Tests

#### Backward Compatibility (test_backward_compatibility.py)

```
Single AMM
  ├─ Buy (small, medium, large)
  └─ Sell (small, medium, large)

Two AMMs
  ├─ Buy (small, medium, large)
  ├─ Sell (small, medium, large)
  ├─ Same fees
  └─ Different fees

Five AMMs
  ├─ Buy (various sizes)
  └─ Sell (various sizes)
```

#### Symmetry & Fairness (test_symmetry_fairness.py)

```
Identical Strategies
  ├─ Constant fees
  ├─ Tiered fees
  └─ Multiple random seeds

Similar Strategies
  ├─ Near-identical fees (2.9% vs 3.1%)
  └─ Proportional PnL verification

Flow Distribution
  ├─ Competitive AMMs get equal flow
  └─ Better fees get more flow
```

#### No Arbitrage (test_no_arbitrage.py)

```
Round-Trip Trades
  ├─ Buy then sell
  ├─ Sell then buy
  └─ Net loss = fees paid

Cross-AMM Arbitrage
  ├─ Different fee structures
  └─ No profitable cycles

Price Impact
  └─ Monotonic (larger = worse)
```

#### Optimal Routing (test_optimal_routing.py)

```
Split vs Single
  ├─ Split beats best single AMM
  └─ Improvement > 0.01%

Convergence
  ├─ Typical structures: ≤3 iterations
  ├─ All structures: ≤5 iterations
  └─ Monotonic improvement

Near-Optimal
  └─ Within 0.1% of analytical optimal
```

#### Accounting (test_accounting.py)

```
Value Conservation
  ├─ Sum(PnLs) ≈ 0
  └─ Tolerance: 1e-10

Fee Accounting
  ├─ Fees collected = fees paid
  └─ Tolerance: 0.001%

Invariant Preservation
  ├─ k = x * y preserved
  └─ Tolerance: 0.0001%

Token Conservation
  └─ Total X and Y constant
```

#### Convergence (test_convergence.py)

```
Typical Structures
  ├─ Conservative tiers
  ├─ Moderate tiers
  └─ Aggressive tiers

Pathological Structures
  ├─ May not converge
  └─ Terminates gracefully

Convergence Properties
  ├─ Monotonic improvement
  ├─ Stable final split
  └─ Valid even if non-converged
```

#### Edge Cases (test_edge_cases.py)

```
Extreme Sizes
  ├─ Very small (< 1 token)
  ├─ Very large (>> reserves)
  └─ Zero size

Extreme Pools
  ├─ Balanced (1:1)
  ├─ Skewed (4:1)
  └─ Extreme (1:1000000)

Extreme Fees
  ├─ Zero fees
  ├─ Very high fees (10%)
  └─ Pathological transitions
```

## Fixture Hierarchy

```
conftest.py (Root)
  │
  ├─ Standard Sets
  │  ├─ standard_amm_set (5 AMMs, mixed types)
  │  ├─ constant_fee_amms (5 AMMs, constant only)
  │  ├─ two_identical_amms (symmetry testing)
  │  └─ two_different_fee_amms (routing testing)
  │
  ├─ Pool Configurations
  │  ├─ balanced_pools (equal X and Y)
  │  ├─ skewed_x_pools (more X than Y)
  │  ├─ skewed_y_pools (more Y than X)
  │  └─ extreme_pools (very imbalanced)
  │
  ├─ Parameters
  │  ├─ fair_price (Decimal("1.0"))
  │  ├─ fixed_seed (42)
  │  ├─ random_seeds ([42, 123, 456, 789, 1337])
  │  └─ trade_sizes ([10, 100, 1000, 5000])
  │
  ├─ Utilities
  │  ├─ timer (measure execution time)
  │  ├─ benchmark (time callable execution)
  │  └─ economic_assert (custom assertions)
  │
  └─ Tolerances
     ├─ decimal_tolerance (1e-10)
     ├─ percentage_tolerance (0.0001 = 0.01%)
     └─ symmetry_tolerance (0.001 = 0.1%)
```

## Utility Functions

### Economic Verification (tests/utils/economic_verification.py)

```python
verify_value_conservation(trades, initial, final) -> (bool, str)
  ├─ Check sum(PnLs) ≈ 0
  ├─ Account for fees
  └─ Return (is_valid, error_message)

verify_no_arbitrage(amms, trades, price) -> (bool, Decimal)
  ├─ Execute round-trip
  ├─ Calculate net position
  └─ Return (is_valid, arbitrage_profit)

verify_optimal_routing(amms, size, direction) -> (bool, Decimal)
  ├─ Compare split vs single
  ├─ Calculate improvement
  └─ Return (is_better, improvement)

verify_symmetry(pnl_a, pnl_b) -> (bool, Decimal)
  ├─ Check relative difference
  └─ Return (is_symmetric, diff_pct)
```

### Version Comparison (tests/utils/version_comparison.py)

```python
OldRouter
  └─ Wrapper around constant-fee routing

NewRouter
  └─ Wrapper around tiered-fee routing

run_parallel_simulations(order, amms, price) -> Comparison
  ├─ Clone AMMs for old and new
  ├─ Execute in both systems
  └─ Return detailed comparison

compare_routing_decisions(order, amms, price) -> List[SplitComparison]
  ├─ Compute splits only (no execution)
  └─ Compare split amounts
```

## CI Integration

### Workflow Structure

```
GitHub Actions Workflow
  │
  ├─ Fast Tests (< 5 minutes)
  │  ├─ Unit tests (test_fee_tiers.py)
  │  ├─ Backward compatibility
  │  ├─ Economic properties
  │  └─ Edge cases (not slow)
  │
  ├─ Slow Tests (5-15 minutes)
  │  └─ Tests marked with @pytest.mark.slow
  │
  ├─ Coverage
  │  ├─ Generate XML report
  │  ├─ Upload to Codecov
  │  └─ Generate HTML artifact
  │
  ├─ Performance Check
  │  ├─ Verify < 5 minute total
  │  └─ Identify slow unmarked tests
  │
  └─ Lint & Type Check
     ├─ Ruff (linter)
     ├─ Ruff (formatter)
     └─ Mypy (type checker)
```

### Test Matrix

```
             Python 3.10   Python 3.11   Python 3.12
Ubuntu         ✓              ✓             ✓
macOS          -              ✓             -

Markers:
  - backward_compat
  - economic
  - edge_case
  - integration
  - slow
```

## Performance Targets

```
Test Category              Target Time    Actual (Typical)
─────────────────────────────────────────────────────────
Unit Tests                 < 1 second     ~0.5 seconds
Backward Compat (each)     < 0.1 second   ~0.05 seconds
Economic Tests (each)      < 1 second     ~0.5 seconds
Edge Cases (each)          < 2 seconds    ~1 second
All Fast Tests             < 5 minutes    ~3 minutes
Slow Tests                 < 15 minutes   ~10 minutes
─────────────────────────────────────────────────────────
Total CI Time              < 20 minutes   ~13 minutes
```

## Success Criteria

Each test category has specific acceptance criteria:

```
✓ Backward Compatibility
  ├─ Splits match within 0.01%
  ├─ Prices match within 1e-10
  └─ Reserves match within 1e-10

✓ Symmetry & Fairness
  ├─ Identical strategies: PnL diff < 0.1%
  └─ Flow distribution within 1%

✓ No Arbitrage
  └─ Round-trip loss = fees ± 0.1%

✓ Optimal Routing
  ├─ Split beats single by > 0.01%
  └─ Within 0.1% of optimal

✓ Accounting
  ├─ Sum(PnLs) within 1e-10
  ├─ Fees match within 0.001%
  └─ k-invariant within 0.0001%

✓ Convergence
  ├─ 95% converge in ≤3 iterations
  └─ 100% terminate in ≤5 iterations

✓ Edge Cases
  ├─ No crashes
  ├─ Results mathematically valid
  └─ Properties still hold
```

## Future Enhancements

Potential areas for expansion:

1. **Property-based Testing**: Use Hypothesis for generative testing
2. **Performance Regression Testing**: Track routing time over commits
3. **Fuzz Testing**: Random input generation for robustness
4. **Multi-currency Tests**: Extend beyond X/Y pair
5. **Gas Cost Analysis**: Estimate EVM execution costs
6. **Visualization**: Generate charts of PnL distribution
7. **Statistical Analysis**: Chi-square tests for fairness
8. **Adversarial Testing**: Intentionally break properties

## Documentation Links

- **Main README**: `tests/README.md`
- **Quick Start**: `tests/QUICKSTART.md`
- **Fixtures**: `tests/fixtures/README.md`
- **Implementation Plans**: Project root (`.md` files)
