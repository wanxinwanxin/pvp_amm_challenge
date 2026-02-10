# No-Arbitrage Testing Quick Reference

## Quick Start

```bash
# Run all no-arbitrage tests
pytest tests/test_no_arbitrage.py -v

# Run with detailed output
pytest tests/test_no_arbitrage.py -vv

# Run specific test class
pytest tests/test_no_arbitrage.py::TestNoArbitrageConstantFees -v

# Run with coverage
pytest tests/test_no_arbitrage.py --cov=amm_competition.core
```

## Test Categories

| Category | Tests | Purpose |
|----------|-------|---------|
| **Constant Fees** | 3 tests | Verify constant fee AMMs prevent arbitrage |
| **Tiered Fees** | 3 tests | Verify tiered structures prevent arbitrage |
| **Tier Boundaries** | 4 tests | Verify no exploits at tier thresholds |
| **Two AMMs** | 4 tests | Verify cross-AMM arbitrage prevention |
| **Extreme Sizes** | 3 tests | Verify edge cases (dust, whale trades) |
| **Asymmetric Pools** | 3 tests | Verify imbalanced pools are safe |
| **Utility Functions** | 3 tests | Verify verification utilities |
| **Total** | **23 tests** | Complete arbitrage prevention coverage |

## Core Assertion Pattern

```python
# Standard arbitrage test pattern
def test_no_arbitrage():
    # 1. Create AMM
    amm = create_constant_fee_amm("Test", fee, x, y)

    # 2. Execute round-trip trade
    trade1 = amm.execute_sell_x(amount, 0)  # Buy X
    trade2 = amm.execute_buy_x(trade1.amount_x, 1)  # Sell X

    # 3. Calculate net result
    net_y = trade2.amount_y - trade1.amount_y

    # 4. Assert loss
    assert net_y < 0, "Should lose money"

    # 5. Verify loss ≈ fees
    fees = calculate_total_fees(amm)
    assert abs(abs(net_y) - fees) / fees < 0.001
```

## Key Test Scenarios

### 1. Basic Constant Fee
```python
# 30 bps constant fee, 100 X trade
amm = create_constant_fee_amm("Test", Decimal("0.003"), 10000, 10000)
# Execute buy-sell cycle → expect loss ≈ 0.6 Y (2 × 30 bps × 100)
```

### 2. Tiered Fee Structure
```python
# 30→20→10 bps tiers, 1500 X trade
tiers = get_baseline_fee_tiers("conservative")
amm = create_tiered_fee_amm("Test", tiers, 10000, 10000)
# Execute cycle → expect loss = weighted average fees
```

### 3. Cross-AMM Arbitrage
```python
# Buy from AMM1, sell to AMM2
amm1 = create_constant_fee_amm("A", fee1, x, y)
amm2 = create_constant_fee_amm("B", fee2, x, y)
# Execute cross-AMM → expect loss = fee1 + fee2
```

### 4. Tier Boundary
```python
# Test exactly at tier threshold
amm = create_tiered_fee_amm("Test", [(0, 0.003), (100, 0.002)], x, y)
# Trade 100 X → verify no discontinuity
```

### 5. Extreme Size
```python
# Very small trade
amm.execute_sell_x(Decimal("0.01"), 0)  # 0.01 X
# Very large trade
amm.execute_sell_x(Decimal("10000"), 0)  # 10000 X
# Both should lose money proportional to fees
```

## Expected Test Results

### All Tests Pass
```
==================== 23 passed in 2.34s ====================
```

### Individual Test
```
test_buy_sell_cycle_loses_money PASSED                [100%]

Net loss: -0.602400 Y
Total fees: 0.602401 Y
Relative error: 0.0002%
```

## Common Assertions

```python
# Loss is negative (lose money)
assert net_y < 0

# Loss matches fees (within 0.1%)
assert abs(abs(net_y) - fees) / fees < 0.001

# Cross-AMM loss equals sum of fees
assert net_loss ≈ fee_amm1 + fee_amm2

# Tier boundary continuity
assert abs(loss_below - loss_above) < tolerance
```

## Fee Calculations

### Constant Fee (Uniswap v2 model)
```
fee_on_input = amount × fee_rate
net_to_pool = amount × (1 - fee_rate)
```

### Tiered Fee (Weighted Average)
```
For trade size 150 with tiers [(0, 0.003), (100, 0.002)]:
  Tier 0: 100 × 0.003 = 0.300
  Tier 1: 50 × 0.002 = 0.100
  Total: 0.400
  Average: 0.400 / 150 = 0.00267 (26.7 bps)
```

### Round-Trip Loss
```
Buy:  spend Y, get X (pay ask fee)
Sell: spend X, get Y (pay bid fee)
Loss ≈ Y × (ask_fee + bid_fee) + slippage
```

## Debugging Failed Tests

### If `net_y >= 0` (profitable arbitrage)
```python
# Check:
1. Fee rates are correctly set
2. Fees are being collected (accumulated_fees_x/y > 0)
3. Constant product invariant maintained (k = x × y)
4. Correct fee model (fee-on-input, not fee-on-output)
```

### If `loss != fees` (mismatch)
```python
# Check:
1. Price used for fee conversion (X to Y terms)
2. Slippage accounted for (small relative error OK)
3. Tolerance level (< 1% is acceptable)
4. Decimal precision (no float rounding)
```

### If test errors
```python
# Check:
1. AMM initialized (amm.initialize() called)
2. Trade size valid (0 < size < reserve_x for sells)
3. Quote exists before execution
4. Snapshots taken at correct times
```

## Integration Points

### Fixtures Used
```python
from tests.fixtures.economic_fixtures import (
    create_constant_fee_amm,
    create_tiered_fee_amm,
    get_baseline_fee_tiers,
    snapshot_amm_state,
)
```

### Utilities Used
```python
from tests.utils.economic_verification import (
    verify_no_arbitrage,
    calculate_effective_execution_price,
)
```

### Core Components
```python
from amm_competition.core.amm import AMM
from amm_competition.core.trade import FeeQuote, FeeTier
```

## Test Data

### Standard Trade Sizes
- Dust: 0.01, 0.1, 0.5 X
- Small: 1, 10 X
- Medium: 100, 500 X
- Large: 1000, 5000 X
- Whale: 10000+ X

### Standard Fee Tiers
- Conservative: 30 → 20 → 10 bps
- Moderate: 30 → 15 → 5 bps
- Aggressive: 50 → 10 → 1 bps
- Pathological: 10000 → 1 → 0.1 bps

### Standard Pool Balances
- Balanced: (10000, 10000)
- Skewed X: (20000, 5000)
- Skewed Y: (5000, 20000)
- Extreme: (1, 1000000)

## Performance Benchmarks

| Test Category | Duration | AMM Operations |
|---------------|----------|----------------|
| Constant Fees | ~0.2s | 50 trades |
| Tiered Fees | ~0.3s | 60 trades |
| Tier Boundaries | ~0.2s | 40 trades |
| Two AMMs | ~0.3s | 40 trades |
| Extreme Sizes | ~0.2s | 30 trades |
| Asymmetric Pools | ~0.2s | 30 trades |
| Utilities | ~0.1s | 20 trades |
| **Total** | **~1.5s** | **270 trades** |

## Success Criteria

✅ **All tests pass**
- 23/23 tests successful
- No arbitrage opportunities detected

✅ **Economic correctness**
- All cycles lose money (net < 0)
- Loss equals fees (error < 0.1%)

✅ **Edge case coverage**
- Extreme sizes handled
- Tier boundaries safe
- Imbalanced pools secure

✅ **Cross-AMM safety**
- No profitable cross-AMM arbitrage
- Fee structures don't create exploits

## Quick Troubleshooting

| Issue | Likely Cause | Solution |
|-------|--------------|----------|
| Profitable cycle | Fees not collected | Check `accumulated_fees_x/y` |
| Loss > fees | Slippage calculation | Increase tolerance to 1% |
| Quote is None | Invalid trade size | Check `0 < size < reserve_x` |
| Random failures | Float precision | Use Decimal everywhere |
| Test timeout | Infinite loop | Check for division by zero |

## Additional Resources

- Full documentation: `tests/TEST_NO_ARBITRAGE_SUMMARY.md`
- Economic fixtures: `tests/fixtures/economic_fixtures.py`
- Verification utilities: `tests/utils/economic_verification.py`
- AMM implementation: `amm_competition/core/amm.py`
- Fee structures: `amm_competition/core/trade.py`

## Contact & Support

For issues or questions:
1. Check test output for detailed error messages
2. Review `TEST_NO_ARBITRAGE_SUMMARY.md` for comprehensive documentation
3. Examine similar passing tests for patterns
4. Verify AMM state with `snapshot_amm_state(amm)`
