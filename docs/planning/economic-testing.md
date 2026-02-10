# Implementation Plan: Economic Correctness Testing

**Generated:** 2026-02-10
**Task:** Create comprehensive integration tests for testing the modified AMM competition system to ensure economic correctness
**Context Used:** yes

## Overview

This plan details a comprehensive testing strategy to verify that the transition from constant fees to tiered fee structures with iterative routing preserves economic correctness properties. The modified system introduces size-dependent pricing through up to 3 fee tiers per direction and iterative refinement routing (converges in 2-3 iterations), replacing the previous constant fee + analytical routing approach.

The testing strategy focuses on seven critical economic properties: backward compatibility, symmetry/fairness, determinism/stability, no arbitrage creation, optimal routing, accounting correctness, and convergence stability. Tests will be structured as focused integration tests rather than full competition runs to enable fast CI execution while maintaining comprehensive coverage.

This approach validates not just unit-level correctness (already covered by existing tests) but system-level economic invariants that must hold for the competition to be fair and economically sound.

## Scope

### Included

- Integration tests verifying economic properties across multi-AMM scenarios
- Backward compatibility tests comparing old constant-fee system to new tiered system baseline
- Symmetry and fairness tests with identical and near-identical strategies
- Determinism tests ensuring reproducibility across runs
- No-arbitrage tests for sequential buy-sell cycles
- Optimal routing verification comparing tiered vs constant fee execution
- Accounting correctness tests verifying conservation of value
- Convergence stability tests for edge cases and pathological fee structures
- Edge case tests: extreme trade sizes, asymmetric pools, pathological fee tiers
- Numerical precision validation for Decimal arithmetic
- Test fixtures and utilities for common scenarios (2/3/5 AMM setups)
- CI integration with GitHub Actions

### Excluded

- Full competition simulation tests (too slow for CI; covered by existing match runner)
- UI/visualization testing (not relevant to economic correctness)
- Solidity contract tests (already covered by `contracts/test/TieredFeeStrategy.t.sol`)
- Performance benchmarking beyond convergence timing (optimization is separate concern)
- Multi-threaded/concurrent testing (simulation is sequential)

## Current State

### Architecture

- **Core Engine:** Python-based AMM simulation with Decimal precision
- **Fee Model:** Original: constant `bid_fee`/`ask_fee` per AMM; Modified: optional `bid_tiers`/`ask_tiers` (up to 3 tiers) with weighted average computation
- **Router:** Original: analytical split formula; Modified: iterative refinement (2-3 iterations typical) with fast path for constant fees
- **Integration:** pyrevm for Solidity strategy execution, Python wrapper in `evm/adapter.py`

### Relevant Files

| File Path | Purpose |
|-----------|---------|
| `amm_competition/core/trade.py` | `FeeTier`, `FeeQuote` with tiered fee support |
| `amm_competition/core/amm.py` | `AMM` engine with fee-on-input model |
| `amm_competition/market/router.py` | `OrderRouter` with iterative refinement for tiers |
| `tests/test_fee_tiers.py` | Unit tests for fee tier logic |
| `tests/test_tiered_routing.py` | Integration tests for tiered routing |
| `tests/test_router_convergence.py` | Convergence algorithm tests |

### Patterns

- **Decimal Arithmetic:** All monetary values use Python `Decimal` for precision
- **Mock Strategies:** Test helpers use `MockStrategy` class returning fixed `FeeQuote`
- **Fast Path:** Router detects constant fees and bypasses iteration
- **Uniswap v2 Model:** Fee-on-input with γ = 1 - f, fees accumulate separately from reserves
- **Git History:** Commit `217d5ad` represents pre-tiered system (backward compatibility baseline)

## API Design

### Test Fixtures Module

**File:** `tests/fixtures/economic_fixtures.py`

```python
from decimal import Decimal
from typing import Callable, Literal
from amm_competition.core.amm import AMM
from amm_competition.core.trade import FeeQuote, FeeTier

# Type aliases
FeeStructure = Literal["constant", "two_tier", "three_tier", "aggressive", "pathological"]
PoolBalance = Literal["balanced", "skewed_x", "skewed_y", "extreme"]

def create_constant_fee_amm(
    name: str,
    fee: Decimal,
    reserve_x: Decimal,
    reserve_y: Decimal
) -> AMM:
    """Create AMM with constant fees (old system equivalent)."""
    pass

def create_tiered_fee_amm(
    name: str,
    bid_tiers: list[FeeTier],
    ask_tiers: list[FeeTier],
    reserve_x: Decimal,
    reserve_y: Decimal
) -> AMM:
    """Create AMM with tiered fee structure."""
    pass

def create_amm_set(
    n_amms: int,
    fee_structure: FeeStructure,
    pool_balance: PoolBalance = "balanced",
    base_liquidity: Decimal = Decimal("10000")
) -> list[AMM]:
    """Create standard AMM test sets for common scenarios."""
    pass

def get_baseline_fee_tiers(
    profile: Literal["conservative", "moderate", "aggressive"]
) -> tuple[list[FeeTier], list[FeeTier]]:
    """Return standard fee tier configurations."""
    pass

def snapshot_amm_state(amm: AMM) -> dict:
    """Capture complete AMM state for comparison."""
    pass

def calculate_pnl(
    initial_state: dict,
    final_state: dict
) -> tuple[Decimal, Decimal]:
    """Calculate PnL in both X and Y tokens."""
    pass
```

### Economic Verification Utilities

**File:** `tests/utils/economic_verification.py`

```python
from decimal import Decimal
from typing import Sequence
from amm_competition.core.amm import AMM
from amm_competition.market.router import RoutedTrade

def verify_value_conservation(
    trades: Sequence[RoutedTrade],
    initial_states: dict[str, dict],
    final_states: dict[str, dict],
    tolerance: Decimal = Decimal("0.0001")
) -> tuple[bool, str]:
    """
    Verify that total value is conserved across all trades.
    Returns (is_valid, error_message).
    """
    pass

def verify_no_arbitrage(
    amms: list[AMM],
    trade_sequence: Sequence[tuple[str, Decimal]],
    price: Decimal,
    tolerance: Decimal = Decimal("0.001")
) -> tuple[bool, Decimal]:
    """
    Execute buy-then-sell cycle and verify no profit extraction.
    Returns (is_valid, arbitrage_profit).
    """
    pass

def verify_optimal_routing(
    amms: list[AMM],
    trade_size: Decimal,
    direction: Literal["buy", "sell"],
    tolerance: Decimal = Decimal("0.0001")
) -> tuple[bool, Decimal]:
    """
    Compare router split vs single-AMM execution.
    Returns (is_better, improvement_amount).
    """
    pass

def calculate_effective_execution_price(
    trades: Sequence[RoutedTrade],
    direction: Literal["buy", "sell"]
) -> Decimal:
    """Calculate volume-weighted execution price."""
    pass

def verify_symmetry(
    pnl_a: Decimal,
    pnl_b: Decimal,
    tolerance_pct: Decimal = Decimal("5")
) -> tuple[bool, Decimal]:
    """
    Verify two identical strategies have similar PnL.
    Returns (is_symmetric, pnl_difference_pct).
    """
    pass
```

### Comparison Framework (Old vs New)

**File:** `tests/utils/version_comparison.py`

```python
from decimal import Decimal
from typing import Protocol
from amm_competition.core.amm import AMM

class RouterProtocol(Protocol):
    """Interface for router implementations."""
    def compute_optimal_split_buy(
        self, amms: list[AMM], total_y: Decimal
    ) -> list[tuple[AMM, Decimal]]:
        ...

    def compute_optimal_split_sell(
        self, amms: list[AMM], total_x: Decimal
    ) -> list[tuple[AMM, Decimal]]:
        ...

class OldRouter:
    """Analytical router from commit 217d5ad (constant fees only)."""
    # Implementation copied from git history
    pass

class NewRouter:
    """Current iterative router with tiered fee support."""
    # Wrapper around current OrderRouter
    pass

def compare_routing_decisions(
    amms_old: list[AMM],
    amms_new: list[AMM],
    trade_size: Decimal,
    direction: Literal["buy", "sell"]
) -> dict:
    """
    Compare old and new router decisions.
    Returns metrics: execution_price_diff, split_similarity, etc.
    """
    pass

def run_parallel_simulations(
    old_config: dict,
    new_config: dict,
    n_trades: int,
    seed: int
) -> dict:
    """
    Run matched trades through old and new systems.
    Returns comparison metrics.
    """
    pass
```

## Implementation Steps

### Step 1: Create Test Infrastructure

Create foundational test utilities and fixtures to support all economic tests.

**Tasks:**
1. Create `tests/fixtures/` directory structure
2. Implement `economic_fixtures.py` with AMM creation helpers
3. Implement standard fee tier profiles (conservative, moderate, aggressive)
4. Create pool balance configurations (balanced, skewed, extreme)
5. Implement state snapshot and PnL calculation utilities
6. Write unit tests for fixture utilities themselves

**Files to create:**
- `tests/fixtures/__init__.py`
- `tests/fixtures/economic_fixtures.py`
- `tests/utils/__init__.py`
- `tests/utils/economic_verification.py`

**Estimated complexity:** Medium (foundational infrastructure)

### Step 2: Implement Backward Compatibility Tests

Verify that constant-fee strategies behave identically between old and new systems.

**Tasks:**
1. Extract old router logic from git commit `217d5ad`
2. Create `tests/utils/version_comparison.py` with `OldRouter` class
3. Implement side-by-side execution framework
4. Write tests comparing constant-fee routing decisions
5. Verify identical execution prices for single strategy
6. Test multi-strategy scenarios (2, 3, 5 AMMs)

**Test cases:**
- `test_constant_fee_backward_compatible_single_amm()`
- `test_constant_fee_backward_compatible_two_amms()`
- `test_constant_fee_backward_compatible_five_amms()`
- `test_constant_fee_identical_execution_prices()`
- `test_constant_fee_identical_splits()`

**Files to create:**
- `tests/test_backward_compatibility.py`
- `tests/utils/version_comparison.py`

**Acceptance criteria:**
- Constant-fee strategies produce identical splits (< 0.01% difference)
- Execution prices match within Decimal precision (< 1e-10)
- All tests pass on both old and new code paths

### Step 3: Implement Symmetry and Fairness Tests

Verify that identical or similar strategies compete fairly.

**Tasks:**
1. Create test scenarios with identical strategies
2. Run multiple simulations with random seed variation
3. Verify PnL distribution is centered near zero (tied competition)
4. Test near-identical strategies (1% fee difference)
5. Verify proportional PnL differences

**Test cases:**
- `test_identical_constant_strategies_symmetric_pnl()`
- `test_identical_tiered_strategies_symmetric_pnl()`
- `test_near_identical_strategies_proportional_pnl()`
- `test_asymmetric_reserves_fair_competition()`
- `test_multiple_runs_consistent_symmetry()`

**Files to create:**
- `tests/test_symmetry_fairness.py`

**Implementation approach:**
```python
# High-level algorithm for symmetry test
def test_identical_strategies_symmetric():
    # 1. Create two identical AMMs
    amm_a = create_tiered_fee_amm("A", tiers, tiers, 10000, 10000)
    amm_b = create_tiered_fee_amm("B", tiers, tiers, 10000, 10000)

    # 2. Run N random trades through router
    for i in range(100):
        trade = random_trade(seed=i)
        route_order(trade, [amm_a, amm_b], price, timestamp=i)

    # 3. Calculate PnLs
    pnl_a = calculate_pnl(initial_a, final_a)
    pnl_b = calculate_pnl(initial_b, final_b)

    # 4. Verify symmetric (within 5% tolerance)
    is_symmetric, diff = verify_symmetry(pnl_a, pnl_b, tolerance=5%)
    assert is_symmetric
```

**Acceptance criteria:**
- Identical strategies: PnL difference < 5% (accounting for randomness)
- Near-identical strategies: PnL proportional to fee advantage
- Tests pass with multiple random seeds

### Step 4: Implement Determinism and Stability Tests

Verify that simulations are reproducible with fixed seeds.

**Tasks:**
1. Create deterministic test scenarios with fixed seeds
2. Run same scenario multiple times
3. Verify bit-exact reproduction of results
4. Test with different AMM configurations
5. Verify router convergence produces stable splits

**Test cases:**
- `test_deterministic_routing_decisions()`
- `test_deterministic_execution_prices()`
- `test_deterministic_pnl_calculation()`
- `test_multiple_runs_identical_results()`
- `test_router_convergence_stable_splits()`

**Files to create:**
- `tests/test_determinism.py`

**Implementation approach:**
```python
# High-level algorithm for determinism test
def test_deterministic_execution():
    # 1. Create test scenario
    amms = create_amm_set(n=3, fee_structure="two_tier")
    trades = generate_test_trades(seed=42, n=50)

    # 2. Run scenario twice with same seed
    results_1 = execute_trades(amms, trades, seed=42)
    results_2 = execute_trades(amms, trades, seed=42)

    # 3. Verify bit-exact equality
    assert results_1 == results_2  # All Decimals, splits, PnLs identical
```

**Acceptance criteria:**
- Bit-exact reproduction of all Decimal values
- Routing splits identical across runs
- No floating-point non-determinism

### Step 5: Implement No-Arbitrage Tests

Verify that the router and fee structure don't create exploitable arbitrage opportunities.

**Tasks:**
1. Design buy-then-sell cycle tests
2. Test sequential trades at different sizes
3. Verify no value extraction from cycles
4. Test cross-AMM arbitrage scenarios
5. Test tiered fee boundary cases

**Test cases:**
- `test_no_arbitrage_constant_fees()`
- `test_no_arbitrage_tiered_fees()`
- `test_no_arbitrage_cross_tier_boundaries()`
- `test_no_arbitrage_extreme_trade_sizes()`
- `test_no_arbitrage_asymmetric_pools()`

**Files to create:**
- `tests/test_no_arbitrage.py`

**Implementation approach:**
```python
# High-level algorithm for no-arbitrage test
def test_no_arbitrage_cycle():
    # 1. Create AMM(s) and record initial state
    amms = create_amm_set(n=2, fee_structure="three_tier")
    initial_trader_x = Decimal("1000")
    initial_trader_y = Decimal("0")

    # 2. Execute buy cycle: Y -> X
    x_received = execute_buy_x(amms, spend_y=Decimal("500"))

    # 3. Execute sell cycle: X -> Y
    y_received = execute_sell_x(amms, sell_x=x_received)

    # 4. Verify net loss (fees consumed)
    net_y = y_received - Decimal("500")
    assert net_y < Decimal("0")  # Lost money to fees

    # 5. Verify loss equals fees paid
    total_fees = calculate_total_fees_paid(amms)
    assert abs(abs(net_y) - total_fees) < Decimal("0.01")
```

**Acceptance criteria:**
- All buy-sell cycles result in net loss equal to fees
- No profitable arbitrage paths exist
- Tests cover constant and tiered fee scenarios

### Step 6: Implement Optimal Routing Tests

Verify that router splits achieve better execution than single-AMM routing.

**Tasks:**
1. Compare split routing vs single-AMM execution
2. Measure execution price improvement
3. Test across different fee structures
4. Verify marginal price equalization
5. Test with varying liquidity distributions

**Test cases:**
- `test_split_routing_better_than_single_amm()`
- `test_marginal_prices_equalized_after_split()`
- `test_optimal_split_with_tiered_fees()`
- `test_optimal_split_with_asymmetric_liquidity()`
- `test_optimal_split_convergence_quality()`

**Files to create:**
- `tests/test_optimal_routing.py`

**Implementation approach:**
```python
# High-level algorithm for optimal routing verification
def test_split_better_than_single():
    # 1. Create multiple AMMs with different fees
    amms = [
        create_tiered_fee_amm("A", conservative_tiers, conservative_tiers, 10000, 10000),
        create_tiered_fee_amm("B", aggressive_tiers, aggressive_tiers, 10000, 10000)
    ]

    # 2. Execute via optimal router
    split_trades = router.route_order(order, amms, price, timestamp=0)
    split_price = calculate_effective_execution_price(split_trades, "buy")

    # 3. Execute on best single AMM
    best_amm = amms[0]  # Choose best by spot fee
    single_trade = execute_single(order, best_amm)
    single_price = single_trade.implied_price

    # 4. Verify split is better or equal
    assert split_price <= single_price * Decimal("1.0001")  # Allow 0.01% tolerance
```

**Acceptance criteria:**
- Split routing always achieves better or equal execution vs single AMM
- Improvement measurable for heterogeneous fee structures
- Marginal prices equalized within convergence tolerance (0.1%)

### Step 7: Implement Accounting Correctness Tests

Verify that value is conserved and fees are correctly tracked.

**Tasks:**
1. Implement value conservation tests across trades
2. Verify fees paid equals fees collected
3. Test reserve accounting (k invariant)
4. Verify accumulated_fees tracking
5. Test sum of all PnLs equals zero

**Test cases:**
- `test_value_conservation_single_trade()`
- `test_value_conservation_multiple_trades()`
- `test_fees_paid_equals_fees_collected()`
- `test_k_invariant_preserved()`
- `test_sum_of_pnls_zero()`
- `test_accumulated_fees_tracking()`

**Files to create:**
- `tests/test_accounting_correctness.py`

**Implementation approach:**
```python
# High-level algorithm for accounting correctness
def test_value_conservation():
    # 1. Create AMMs and snapshot initial total value
    amms = create_amm_set(n=3, fee_structure="two_tier")
    initial_value = sum(
        amm.reserve_x * price + amm.reserve_y + amm.accumulated_fees_y
        for amm in amms
    )

    # 2. Execute trades
    for i in range(50):
        order = generate_random_order(seed=i)
        router.route_order(order, amms, price, timestamp=i)

    # 3. Calculate final total value
    final_value = sum(
        amm.reserve_x * price + amm.reserve_y + amm.accumulated_fees_y
        for amm in amms
    )

    # 4. Verify conservation (value change only from external trades)
    # Internal routing should preserve value (fees accounted for)
    assert abs(final_value - initial_value - external_value_change) < Decimal("0.01")
```

**Acceptance criteria:**
- Value conserved across all trades (within 0.01% tolerance)
- Fees paid by traders equals fees collected by AMMs
- k invariant preserved for each AMM
- Sum of PnLs approximately zero (within fee collection)

### Step 8: Implement Convergence Stability Tests

Verify that iterative routing algorithm converges reliably, even for edge cases.

**Tasks:**
1. Test convergence for well-behaved fee structures
2. Test convergence for pathological fee structures
3. Verify max iterations respected (no infinite loops)
4. Test convergence quality metrics
5. Test edge cases: tiny trades, huge trades, extreme tiers

**Test cases:**
- `test_convergence_within_max_iterations()`
- `test_convergence_quality_well_behaved_tiers()`
- `test_convergence_pathological_tiers()`
- `test_convergence_extreme_trade_sizes()`
- `test_convergence_extreme_tier_thresholds()`
- `test_convergence_zero_liquidity_edge_case()`

**Files to create:**
- `tests/test_convergence_stability.py`

**Implementation approach:**
```python
# High-level algorithm for convergence stability
def test_convergence_pathological():
    # 1. Create AMMs with pathological fee tiers
    # (very steep transitions between tiers)
    pathological_tiers = [
        FeeTier(threshold=Decimal("0"), fee=Decimal("0.1")),     # 10%
        FeeTier(threshold=Decimal("1"), fee=Decimal("0.0001")),  # 1bp
        FeeTier(threshold=Decimal("2"), fee=Decimal("0.00001")), # 0.1bp
    ]
    amms = [
        create_tiered_fee_amm("A", pathological_tiers, pathological_tiers, 10000, 10000),
        create_tiered_fee_amm("B", pathological_tiers, pathological_tiers, 10000, 10000)
    ]

    # 2. Execute routing (should converge within max iterations)
    router = OrderRouter()
    splits = router.compute_optimal_split_buy(amms, Decimal("100"))

    # 3. Verify convergence completed (no exception)
    assert len(splits) == 2
    assert sum(s[1] for s in splits) <= Decimal("100") * Decimal("1.01")

    # 4. Verify reasonable split (not wildly suboptimal)
    # Even with pathological tiers, should avoid worst case
    execution_price = calculate_execution_price(splits, amms)
    assert execution_price < single_amm_price * Decimal("1.05")  # < 5% worse
```

**Acceptance criteria:**
- Convergence completes within max iterations (5) for all cases
- No infinite loops or exceptions
- Pathological cases converge to reasonable (not necessarily optimal) solution
- Well-behaved cases converge within 2-3 iterations

### Step 9: Implement Edge Case and Stress Tests

Test extreme scenarios that might break economic properties.

**Tasks:**
1. Test with extreme trade sizes (tiny and huge)
2. Test with extreme pool imbalances
3. Test with extreme fee tier configurations
4. Test with zero-liquidity scenarios
5. Test numerical precision edge cases

**Test cases:**
- `test_tiny_trade_sizes_decimal_precision()`
- `test_huge_trade_sizes_no_overflow()`
- `test_extreme_pool_imbalance()`
- `test_zero_liquidity_pool_handling()`
- `test_all_fees_zero_edge_case()`
- `test_all_fees_maximum_edge_case()`
- `test_single_tier_boundary_conditions()`

**Files to create:**
- `tests/test_edge_cases.py`

**Implementation approach:**
```python
# High-level algorithm for edge case testing
def test_extreme_pool_imbalance():
    # 1. Create extremely imbalanced pool
    amm_imbalanced = create_tiered_fee_amm(
        "Imbalanced",
        tiers, tiers,
        reserve_x=Decimal("1"),        # Very small
        reserve_y=Decimal("1000000")    # Very large
    )
    amm_balanced = create_tiered_fee_amm(
        "Balanced",
        tiers, tiers,
        reserve_x=Decimal("10000"),
        reserve_y=Decimal("10000")
    )

    # 2. Route through both
    router = OrderRouter()
    splits = router.compute_optimal_split_buy(
        [amm_imbalanced, amm_balanced],
        Decimal("1000")
    )

    # 3. Verify routing handles gracefully
    assert len(splits) == 2
    # Most/all should go to balanced pool
    assert splits[1][1] > Decimal("900")  # >90% to balanced

    # 4. Verify no numerical instability
    for amm, amount in splits:
        assert amount >= Decimal("0")
        assert not math.isnan(float(amount))
```

**Acceptance criteria:**
- Extreme values handled without exceptions
- Decimal precision maintained (no float conversion errors)
- Router degrades gracefully for pathological inputs
- Tests cover 99th percentile edge cases

### Step 10: Create Test Documentation and CI Integration

Document testing strategy and integrate into CI pipeline.

**Tasks:**
1. Write testing documentation (README for tests/)
2. Document test fixtures usage
3. Create pytest configuration
4. Set up GitHub Actions workflow
5. Create test coverage reporting
6. Document acceptance criteria for each test category

**Files to create:**
- `tests/README.md`
- `.github/workflows/economic-tests.yml`
- `pytest.ini` (update)
- `tests/conftest.py` (pytest configuration)

**Documentation structure:**
```markdown
# tests/README.md

## Economic Correctness Test Suite

### Overview
Comprehensive integration tests verifying economic properties...

### Test Categories
1. Backward Compatibility (`test_backward_compatibility.py`)
2. Symmetry & Fairness (`test_symmetry_fairness.py`)
...

### Running Tests
```bash
# Run all economic tests
pytest tests/test_*economic* -v

# Run specific category
pytest tests/test_backward_compatibility.py -v

# Run with coverage
pytest --cov=amm_competition tests/
```

### Adding New Tests
...
```

**CI workflow approach:**
```yaml
# .github/workflows/economic-tests.yml
name: Economic Correctness Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install -e .[dev]
          pip install pytest-cov
      - name: Run economic tests
        run: |
          pytest tests/test_backward_compatibility.py -v
          pytest tests/test_symmetry_fairness.py -v
          pytest tests/test_determinism.py -v
          pytest tests/test_no_arbitrage.py -v
          pytest tests/test_optimal_routing.py -v
          pytest tests/test_accounting_correctness.py -v
          pytest tests/test_convergence_stability.py -v
          pytest tests/test_edge_cases.py -v
      - name: Generate coverage report
        run: pytest --cov=amm_competition --cov-report=html tests/
```

**Acceptance criteria:**
- All tests run in CI on every push
- Tests complete in < 5 minutes total
- Coverage report generated and archived
- Clear failure messages for debugging

## Files to Modify

| File Path | Changes |
|-----------|---------|
| `pyproject.toml` | Add pytest-cov to dev dependencies |
| `tests/__init__.py` | Add imports for new test utilities |

## New Files

| File Path | Purpose |
|-----------|---------|
| `tests/fixtures/__init__.py` | Fixture package initialization |
| `tests/fixtures/economic_fixtures.py` | AMM creation and state management fixtures |
| `tests/utils/__init__.py` | Utility package initialization |
| `tests/utils/economic_verification.py` | Economic property verification functions |
| `tests/utils/version_comparison.py` | Old vs new system comparison framework |
| `tests/test_backward_compatibility.py` | Backward compatibility test suite |
| `tests/test_symmetry_fairness.py` | Symmetry and fairness test suite |
| `tests/test_determinism.py` | Determinism and reproducibility tests |
| `tests/test_no_arbitrage.py` | No-arbitrage property tests |
| `tests/test_optimal_routing.py` | Optimal routing verification tests |
| `tests/test_accounting_correctness.py` | Value conservation and accounting tests |
| `tests/test_convergence_stability.py` | Convergence algorithm stability tests |
| `tests/test_edge_cases.py` | Edge case and stress tests |
| `tests/README.md` | Testing documentation |
| `tests/conftest.py` | Pytest configuration and shared fixtures |
| `.github/workflows/economic-tests.yml` | CI workflow configuration |

## Challenges

| Issue | Mitigation |
|-------|-----------|
| **Extracting old router logic from git history** | Use `git show 217d5ad:amm_competition/market/router.py` to extract and vendor old implementation. Create isolated `OldRouter` class to avoid conflicts. |
| **Floating-point vs Decimal precision** | Strictly enforce Decimal usage in all test assertions. Use custom comparison functions with explicit tolerance. Document precision requirements. |
| **Nondeterministic randomness** | Use fixed seeds for all RNG operations. Create deterministic trade generators. Verify bit-exact reproduction in determinism tests. |
| **CI test performance** | Limit test scope to focused scenarios (not full competitions). Use smaller trade counts (50-100 trades). Parallelize test execution. Target < 5min total runtime. |
| **Convergence non-determinism** | Iterative algorithm is deterministic given fixed inputs, but ensure float-to-Decimal conversions don't introduce variance. Use strict Decimal arithmetic in router. |
| **Backward compatibility false positives** | Old system has known numerical precision differences due to float usage. Accept < 0.01% tolerance for backward compatibility tests. |
| **Pathological fee structures** | Some extreme tier configurations may not converge optimally. Accept sub-optimal but reasonable solutions (< 5% worse than optimal). Document known limitations. |

## Testing Strategy

### Test Organization

```
tests/
├── fixtures/
│   ├── __init__.py
│   └── economic_fixtures.py          # AMM/strategy creation helpers
├── utils/
│   ├── __init__.py
│   ├── economic_verification.py      # Property verification functions
│   └── version_comparison.py         # Old vs new comparison
├── test_backward_compatibility.py    # Old system equivalence
├── test_symmetry_fairness.py         # Identical strategy competition
├── test_determinism.py               # Reproducibility tests
├── test_no_arbitrage.py              # Cycle arbitrage tests
├── test_optimal_routing.py           # Split optimality tests
├── test_accounting_correctness.py    # Value conservation tests
├── test_convergence_stability.py     # Iteration convergence tests
├── test_edge_cases.py                # Extreme scenario tests
├── conftest.py                       # Pytest configuration
└── README.md                         # Test documentation
```

### Test Execution Tiers

**Tier 1 - Fast Unit Tests (existing):**
- `test_fee_tiers.py` - Fee tier math
- `test_tiered_routing.py` - Basic routing
- `test_router_convergence.py` - Convergence basics
- Target: < 10 seconds total

**Tier 2 - Economic Integration Tests (new):**
- All new test files in this plan
- Target: < 5 minutes total
- Run on every push in CI

**Tier 3 - Full Competition Tests (existing):**
- Match runner simulations
- Target: minutes to hours
- Run manually or nightly

### Test Data Strategy

**Standard Fixtures:**
- **2 AMM Scenarios:** Most common, fast execution
- **3 AMM Scenarios:** Pairwise approximation testing
- **5 AMM Scenarios:** Maximum N testing
- **Fee Profiles:**
  - Conservative: 30bps → 20bps → 10bps
  - Moderate: 30bps → 15bps → 5bps
  - Aggressive: 50bps → 10bps → 1bp
  - Pathological: 1000bps → 1bp → 0.1bp
- **Liquidity Profiles:**
  - Balanced: 10000 X, 10000 Y
  - Skewed X: 20000 X, 5000 Y
  - Skewed Y: 5000 X, 20000 Y
  - Extreme: 1 X, 1000000 Y

### Randomness Management

**Deterministic Tests:**
- Use fixed seeds for RNG
- Document seed in test docstring
- Verify bit-exact reproduction

**Stochastic Tests (symmetry):**
- Run with multiple seeds (5-10)
- Check statistical properties (mean, variance)
- Accept tolerance based on sample size

### Performance Targets

- Unit tests: < 10 seconds
- Economic integration tests: < 5 minutes
- Individual test: < 5 seconds
- CI total runtime: < 6 minutes (including setup)

## Success Criteria

### Backward Compatibility
- ✅ Constant-fee strategies produce identical routing splits (< 0.01% diff)
- ✅ Execution prices match within Decimal precision (< 1e-10)
- ✅ PnLs match within rounding tolerance (< 0.001%)

### Symmetry/Fairness
- ✅ Identical strategies have symmetric PnL (< 5% difference over 100 trades)
- ✅ Near-identical strategies have proportional PnL
- ✅ Tests pass with 5+ different random seeds

### Determinism/Stability
- ✅ Bit-exact reproduction of results with fixed seed
- ✅ All Decimal values identical across runs
- ✅ Routing decisions reproducible

### No Arbitrage Creation
- ✅ Buy-sell cycles always lose money (equal to fees paid)
- ✅ No profitable arbitrage paths exist
- ✅ Loss equals fees collected by AMMs (< 0.1% diff)

### Optimal Routing
- ✅ Split routing achieves better or equal execution vs single AMM
- ✅ Marginal prices equalized within 0.1% after split
- ✅ Measurable improvement for heterogeneous fee structures

### Accounting Correctness
- ✅ Value conserved across all trades (< 0.01% error)
- ✅ Fees paid equals fees collected (< 0.01% diff)
- ✅ K invariant preserved for each AMM
- ✅ Sum of PnLs ≈ zero (within fee tracking precision)

### Convergence Stability
- ✅ Algorithm converges within max iterations (5) for all cases
- ✅ Well-behaved tiers converge in 2-3 iterations
- ✅ Pathological cases complete without exceptions
- ✅ Extreme edge cases handled gracefully

### CI Integration
- ✅ All tests run automatically on push
- ✅ Tests complete in < 5 minutes
- ✅ Clear failure reporting
- ✅ Coverage report generated

## Performance Benchmarks

While not the primary focus, track convergence performance:

**Convergence Iterations:**
- Well-behaved tiers: 2-3 iterations (target)
- Moderate tiers: 3-4 iterations (acceptable)
- Pathological tiers: 4-5 iterations (max)

**Execution Time:**
- 2-AMM split: < 1ms
- 5-AMM split: < 5ms
- 100-trade scenario: < 1 second

## Old vs New Comparison Strategy

### Extraction Process

1. **Extract old router:**
   ```bash
   git show 217d5ad:amm_competition/market/router.py > tests/utils/old_router.py
   ```

2. **Create wrapper class:**
   ```python
   # tests/utils/version_comparison.py
   from tests.utils.old_router import OrderRouter as OldRouterImpl

   class OldRouter:
       def __init__(self):
           self._impl = OldRouterImpl()

       def compute_optimal_split_buy(self, amms, total_y):
           # Wrapper ensuring compatible interface
           return self._impl.compute_optimal_split_buy(amms, total_y)
   ```

3. **Create comparison framework:**
   - Run same trades through old and new systems
   - Compare routing decisions
   - Compare execution prices
   - Compare final PnLs

### Comparison Metrics

**Routing Decision Similarity:**
- Split allocation difference (L1 norm)
- Rank correlation of AMM order
- Percentage agreement on dominant AMM

**Execution Quality:**
- Effective price difference
- Slippage difference
- Fee burden difference

**PnL Comparison:**
- Absolute PnL difference
- Relative PnL difference (%)
- Rank preservation (winner stays winner)

### Acceptance Thresholds

- Routing splits: < 1% difference
- Execution prices: < 0.1% difference
- PnLs: < 1% difference (allowing for accumulated differences)
- No rank reversals (winner/loser should not flip)

## CI Integration Approach

### GitHub Actions Workflow

```yaml
name: Economic Correctness Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  economic-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']

    steps:
      - name: Checkout code
        uses: actions/checkout@v3
        with:
          fetch-depth: 0  # Full history for git comparison

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e .[dev]
          pip install pytest pytest-cov pytest-xdist

      - name: Run economic tests
        run: |
          pytest tests/test_backward_compatibility.py -v --tb=short
          pytest tests/test_symmetry_fairness.py -v --tb=short
          pytest tests/test_determinism.py -v --tb=short
          pytest tests/test_no_arbitrage.py -v --tb=short
          pytest tests/test_optimal_routing.py -v --tb=short
          pytest tests/test_accounting_correctness.py -v --tb=short
          pytest tests/test_convergence_stability.py -v --tb=short
          pytest tests/test_edge_cases.py -v --tb=short

      - name: Generate coverage report
        run: |
          pytest --cov=amm_competition --cov-report=xml --cov-report=html tests/

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
          flags: economic-tests
          name: economic-correctness

      - name: Archive coverage report
        uses: actions/upload-artifact@v3
        with:
          name: coverage-report-${{ matrix.python-version }}
          path: htmlcov/

  test-summary:
    runs-on: ubuntu-latest
    needs: economic-tests
    if: always()
    steps:
      - name: Test Summary
        run: |
          echo "Economic correctness tests completed"
          echo "Check individual job results for details"
```

### Local Testing

```bash
# Run all economic tests
pytest tests/test_*_*.py -v

# Run specific category
pytest tests/test_backward_compatibility.py -v

# Run with coverage
pytest --cov=amm_competition --cov-report=html tests/

# Run fast tests only (exclude slow)
pytest tests/ -m "not slow" -v

# Run in parallel (if available)
pytest tests/ -n auto
```

### Test Markers

```python
# pytest.ini
[tool.pytest.ini_options]
markers =
    slow: marks tests as slow (> 5 seconds)
    backward_compat: backward compatibility tests
    economic: economic property tests
    edge_case: edge case and stress tests
```

## Acceptance Criteria Summary

### Per Test Category

1. **Backward Compatibility:** All constant-fee tests pass with < 0.01% difference
2. **Symmetry/Fairness:** Identical strategies within 5% PnL over 100 trades
3. **Determinism:** Bit-exact reproduction with fixed seeds
4. **No Arbitrage:** All cycles lose exactly fees paid (< 0.1% diff)
5. **Optimal Routing:** Split always better/equal than single AMM
6. **Accounting:** Value conserved within 0.01%, fees balance
7. **Convergence:** All cases converge within 5 iterations
8. **Edge Cases:** No exceptions, graceful degradation

### Overall Success

- ✅ 100% of tests pass on main branch
- ✅ CI completes in < 5 minutes
- ✅ No regressions from existing tests
- ✅ Coverage > 90% for new code
- ✅ Documentation complete and clear
- ✅ All seven economic properties verified
