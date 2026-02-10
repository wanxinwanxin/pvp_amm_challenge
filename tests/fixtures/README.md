# Economic Test Fixtures

This module provides test fixtures for AMM economic correctness testing with Decimal precision.

## Overview

The fixtures enable:
- Creating AMMs with various fee structures (constant and tiered)
- Configuring different pool balance profiles
- Taking immutable state snapshots
- Calculating accurate PnL between snapshots

All monetary calculations use Python's `Decimal` type for precision.

## Quick Start

```python
from decimal import Decimal
from tests.fixtures import (
    create_constant_fee_amm,
    create_tiered_fee_amm,
    create_amm_set,
    snapshot_amm_state,
    calculate_pnl,
)

# Create a constant fee AMM
amm = create_constant_fee_amm(
    "ConstantFee",
    Decimal("0.003"),  # 30 bps
    Decimal("1000"),   # X reserve
    Decimal("1000"),   # Y reserve
)

# Create a tiered fee AMM
tiers = [
    (Decimal("0"), Decimal("0.003")),      # 30 bps for small trades
    (Decimal("100"), Decimal("0.002")),    # 20 bps for medium trades
    (Decimal("1000"), Decimal("0.001")),   # 10 bps for large trades
]
tiered_amm = create_tiered_fee_amm("TieredFee", tiers, Decimal("1000"), Decimal("1000"))

# Create a standard test set
amms = create_amm_set()  # Returns 5 AMMs with different fee structures

# Snapshot and calculate PnL
before = snapshot_amm_state(amm)
# ... execute trades ...
after = snapshot_amm_state(amm)
pnl = calculate_pnl(before, after)
```

## Standard Fee Profiles

### Conservative
Gradual fee reduction (30→20→10 bps):
```python
from tests.fixtures import get_baseline_fee_tiers

tiers = get_baseline_fee_tiers("conservative")
# [(0, 0.003), (100, 0.002), (1000, 0.001)]
```

### Moderate
Moderate fee reduction (30→15→5 bps):
```python
tiers = get_baseline_fee_tiers("moderate")
# [(0, 0.003), (100, 0.0015), (1000, 0.0005)]
```

### Aggressive
Steep fee reduction (50→10→1 bps):
```python
tiers = get_baseline_fee_tiers("aggressive")
# [(0, 0.005), (100, 0.001), (1000, 0.0001)]
```

### Pathological
Extreme transitions for edge case testing:
```python
tiers = get_baseline_fee_tiers("pathological")
# [(0, 0.1), (1, 0.0001), (2, 0.00001)]
```

## Pool Balance Profiles

### Balanced
Equal X and Y reserves:
```python
from tests.fixtures import PoolBalanceProfile, create_amm_set

amms = create_amm_set(PoolBalanceProfile.BALANCED)
# All AMMs have (10000, 10000) reserves
```

### Skewed X
More X than Y:
```python
amms = create_amm_set(PoolBalanceProfile.SKEWED_X)
# All AMMs have (20000, 5000) reserves
```

### Skewed Y
More Y than X:
```python
amms = create_amm_set(PoolBalanceProfile.SKEWED_Y)
# All AMMs have (5000, 20000) reserves
```

### Extreme
Very imbalanced for edge case testing:
```python
amms = create_amm_set(PoolBalanceProfile.EXTREME)
# All AMMs have (1, 1000000) reserves
```

## State Snapshots

Snapshots are immutable records of AMM state:

```python
snapshot = snapshot_amm_state(amm)

# Access snapshot data
snapshot.name                  # AMM name
snapshot.reserve_x             # X reserves
snapshot.reserve_y             # Y reserves
snapshot.accumulated_fees_x    # Fees collected in X
snapshot.accumulated_fees_y    # Fees collected in Y
snapshot.k                     # Constant product invariant

# Computed properties
snapshot.total_x               # Reserves + fees
snapshot.total_y               # Reserves + fees
snapshot.spot_price            # Current price (Y per X)
```

## PnL Calculation

Calculate profit and loss between two snapshots:

```python
before = snapshot_amm_state(amm)
# ... execute trades ...
after = snapshot_amm_state(amm)

pnl = calculate_pnl(before, after)

# Access PnL data
pnl.delta_x                    # Change in total X (positive = gained)
pnl.delta_y                    # Change in total Y (positive = gained)
pnl.delta_reserve_x            # Change in X reserves only
pnl.delta_reserve_y            # Change in Y reserves only
pnl.fees_earned_x              # Fees collected in X
pnl.fees_earned_y              # Fees collected in Y
pnl.pnl_at_initial_price       # PnL valued at initial price
pnl.pnl_at_final_price         # PnL valued at final price
```

### Custom Valuation Price

You can value PnL at a specific price:

```python
pnl = calculate_pnl(before, after, valuation_price=Decimal("2.0"))
# Both initial and final PnL will use the custom price
```

## Creating Custom AMM Sets

You can create custom combinations:

```python
# Only constant fee AMMs
amms = create_amm_set(
    PoolBalanceProfile.BALANCED,
    include_constant=True,
    include_tiered=False,
)

# Only tiered fee AMMs
amms = create_amm_set(
    PoolBalanceProfile.BALANCED,
    include_constant=False,
    include_tiered=True,
)

# All AMMs with skewed reserves
amms = create_amm_set(PoolBalanceProfile.SKEWED_X)
```

## Standard AMM Set

The default `create_amm_set()` creates 5 AMMs:

1. **ConstantFee**: 30bps flat fee
2. **TwoTier**: 30bps → 20bps (threshold at 100)
3. **ThreeTier**: 30bps → 20bps → 10bps (thresholds at 100, 1000)
4. **Aggressive**: 50bps → 10bps → 1bps (thresholds at 100, 1000)
5. **Pathological**: 100% → 1bps → 0.1bps (thresholds at 1, 2)

All AMMs use the same balance profile (default: BALANCED).

## Examples

### Example 1: Compare Routing Across Fee Structures

```python
from decimal import Decimal
from tests.fixtures import create_amm_set, snapshot_amm_state, calculate_pnl

# Create test AMMs
amms = create_amm_set()

# Take initial snapshots
snapshots_before = {amm.name: snapshot_amm_state(amm) for amm in amms}

# Execute routing logic
# ... your routing code here ...

# Calculate PnL for each AMM
for amm in amms:
    before = snapshots_before[amm.name]
    after = snapshot_amm_state(amm)
    pnl = calculate_pnl(before, after)

    print(f"{amm.name}:")
    print(f"  Fees earned: X={pnl.fees_earned_x}, Y={pnl.fees_earned_y}")
    print(f"  PnL: {pnl.pnl_at_final_price}")
```

### Example 2: Test Economic Invariants

```python
from decimal import Decimal
from tests.fixtures import create_constant_fee_amm, snapshot_amm_state

# Create AMM
amm = create_constant_fee_amm("Test", Decimal("0.003"),
                              Decimal("1000"), Decimal("1000"))

# Check constant product invariant
before = snapshot_amm_state(amm)
k_before = before.k

# Execute trade
amm.execute_buy_x(Decimal("10"), timestamp=0)

# Check invariant preserved (fees go to separate bucket, not reserves)
after = snapshot_amm_state(amm)
k_after = after.k

# In fee-on-input model, k should stay constant
assert abs(k_after - k_before) < Decimal("0.0001")
```

### Example 3: Verify Fee Collection

```python
from decimal import Decimal
from tests.fixtures import create_tiered_fee_amm, snapshot_amm_state, calculate_pnl

# Create tiered AMM
tiers = [
    (Decimal("0"), Decimal("0.003")),
    (Decimal("100"), Decimal("0.002")),
]
amm = create_tiered_fee_amm("Test", tiers, Decimal("1000"), Decimal("1000"))

before = snapshot_amm_state(amm)

# Execute large trade that spans tiers
trade_size = Decimal("150")
trade = amm.execute_buy_x(trade_size, timestamp=0)

after = snapshot_amm_state(amm)
pnl = calculate_pnl(before, after)

# Verify fees match expected calculation
# 150 = 100@0.003 + 50@0.002
expected_fee_rate = (Decimal("100") * Decimal("0.003") +
                     Decimal("50") * Decimal("0.002")) / trade_size
expected_fee = trade_size * expected_fee_rate

# Fees should match (within rounding)
assert abs(pnl.fees_earned_x - expected_fee) < Decimal("0.001")
```

## API Reference

### Functions

- `create_constant_fee_amm(name, fee_rate, reserve_x, reserve_y, ...)` - Create constant fee AMM
- `create_tiered_fee_amm(name, fee_tiers, reserve_x, reserve_y, ...)` - Create tiered fee AMM
- `create_amm_set(balance_profile, include_constant, include_tiered)` - Create standard AMM set
- `get_baseline_fee_tiers(profile)` - Get standard fee tier configurations
- `get_pool_balance(profile)` - Get standard pool balance configurations
- `snapshot_amm_state(amm)` - Create immutable state snapshot
- `calculate_pnl(before, after, valuation_price)` - Calculate PnL between snapshots

### Classes

- `PoolBalanceProfile` - Enum of standard pool balance configurations
- `AMMStateSnapshot` - Immutable AMM state snapshot
- `PnLResult` - Detailed PnL breakdown

## Testing

Run the fixture tests:

```bash
pytest tests/test_economic_fixtures.py -v
```

## Design Principles

1. **Decimal Precision**: All monetary values use `Decimal` to avoid floating-point errors
2. **Immutability**: State snapshots are frozen dataclasses that cannot be modified
3. **Clarity**: Functions have clear names and comprehensive docstrings
4. **Reusability**: Standard profiles enable consistent testing across different scenarios
5. **Accuracy**: PnL calculations account for both reserves and accumulated fees
