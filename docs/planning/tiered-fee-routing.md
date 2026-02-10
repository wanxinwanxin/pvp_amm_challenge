# Implementation Plan: Complete Tiered Fee System Integration

**Generated:** 2025-02-10
**Task:** Complete the tiered fee system integration for PVP AMM Challenge
**Context Used:** yes

## Overview

This plan completes the tiered fee system by integrating it into the router, AMM engine, and EVM adapter. The Python tier structures (FeeTier, FeeQuote) and Solidity infrastructure (IFeeStructure.sol, supportsFeeStructure(), getFeeStructure()) are already complete. The missing piece is the routing algorithm that handles size-dependent fees correctly.

The approach uses **iterative refinement** rather than analytical solution: start with an initial split using constant fees, compute effective fees at those sizes, recompute the split with effective fees, and repeat until convergence (typically 2-3 iterations). This handles N-way routing (N ≤ 5) with mixed constant/tiered strategies correctly while remaining simple to implement and test.

## Scope

### Included

- Router iterative refinement algorithm for tiered fees
- AMM engine integration to use effective_bid_fee() and effective_ask_fee()
- EVM adapter/executor methods to load FeeStructure from Solidity
- N-way routing support (N ≤ 5 strategies)
- Integration tests for mixed constant/tiered routing
- Backward compatibility with constant-fee strategies
- Documentation updates

### Excluded

- Changes to existing tier structures (already complete)
- Changes to Solidity contracts (infrastructure exists)
- Analytical optimization (iterative is sufficient)
- Support for N > 5 (out of scope)
- Dynamic tier adjustment during routing (static tiers only)

## Current State

- **Architecture:** Constant product AMM (xy=k) with fee-on-input model
- **Relevant Files:**
  - `amm_competition/market/router.py` (280 lines, needs iterative refinement)
  - `amm_competition/core/amm.py` (356 lines, needs effective fee usage)
  - `amm_competition/core/trade.py` (192 lines, tier structures complete)
  - `amm_competition/evm/adapter.py` (207 lines, needs fee structure loading)
  - `amm_competition/evm/executor.py` (285 lines, needs EVM function calls)
  - `contracts/src/IFeeStructure.sol` (41 lines, complete)
  - `contracts/src/examples/TieredFeeStrategy.sol` (120 lines, complete)
- **Patterns:**
  - Float math for performance in routing
  - Decimal for precision in AMM engine
  - WAD (1e18) precision in Solidity
  - Fee-on-input model (γ = 1 - f)

## API Design

### Router Extensions

```python
class OrderRouter:
    def _compute_effective_fee(
        self,
        amm: AMM,
        trade_size: Decimal,
        is_buy: bool
    ) -> float:
        """Compute effective fee for given trade size and direction.

        Args:
            amm: AMM to query
            trade_size: Size of trade in appropriate units (X or Y)
            is_buy: True for buy direction (ask_fee), False for sell (bid_fee)

        Returns:
            Effective fee rate as float for fast math
        """
        pass

    def _split_with_convergence(
        self,
        amms: list[AMM],
        total_amount: Decimal,
        is_buy_x: bool,
        max_iterations: int = 5,
        tolerance: float = 0.001
    ) -> list[tuple[AMM, Decimal]]:
        """Compute optimal split with iterative refinement.

        Algorithm:
        1. Initial split using constant fees (existing algorithm)
        2. Compute effective fees at current split amounts
        3. Recompute split using effective fees
        4. Check convergence: max relative change < tolerance
        5. Repeat steps 2-4 until convergence or max_iterations

        Args:
            amms: List of AMMs to split across
            total_amount: Total amount to split (X or Y depending on direction)
            is_buy_x: True if buying X, False if selling X
            max_iterations: Maximum iterations (default 5)
            tolerance: Convergence threshold (default 0.1%)

        Returns:
            List of (AMM, amount) tuples
        """
        pass
```

### EVM Executor Extensions

```python
class EVMStrategyExecutor:
    # Function selectors for new methods
    SELECTOR_SUPPORTS_FEE_STRUCTURE = bytes.fromhex("...")  # supportsFeeStructure()
    SELECTOR_GET_FEE_STRUCTURE = bytes.fromhex("...")       # getFeeStructure(TradeInfo)

    def supports_fee_structure(self) -> bool:
        """Check if strategy supports piecewise fee structures.

        Returns:
            True if strategy implements getFeeStructure(), False otherwise
        """
        pass

    def get_fee_structure(self, trade: TradeInfo) -> Optional[tuple]:
        """Get fee structure from strategy.

        Args:
            trade: Current trade info (may be dummy for initial query)

        Returns:
            Tuple of (bid_tiers, ask_tiers) where each is list of FeeTier,
            or None if strategy doesn't support tiers
        """
        pass
```

### EVM Adapter Extensions

```python
class EVMStrategyAdapter(AMMStrategy):
    def _load_fee_structure(self) -> Optional[FeeQuote]:
        """Load fee structure from EVM strategy if supported.

        Workflow:
        1. Check supportsFeeStructure() on strategy
        2. If false, return None (use constant fees)
        3. If true, call getFeeStructure(dummy_trade)
        4. Parse FeeStructure from return data
        5. Build FeeQuote with bid_tiers and ask_tiers

        Returns:
            FeeQuote with tiers, or None if constant fees
        """
        pass

    def after_initialize(self, initial_x: Decimal, initial_y: Decimal) -> FeeQuote:
        """Modified to load fee structure if available."""
        # Get constant fees from strategy
        # Try to load tier structure
        # Return FeeQuote with both constant fees and tiers
        pass
```

### Implementation Approach

**Iterative Refinement Algorithm:**

```
Input: amms[], total_amount, is_buy_x
Output: splits[]

1. splits = compute_initial_split(amms, total_amount, constant_fees)
2. For iteration in range(max_iterations):
   a. For each (amm, amount) in splits:
      - effective_fee = amm.current_fees.effective_{ask|bid}_fee(amount)
      - Update amm's temporary fee for this iteration
   b. new_splits = compute_split(amms, total_amount, effective_fees)
   c. max_change = max(|new_splits[i] - splits[i]| / total_amount for all i)
   d. If max_change < tolerance:
      - Return new_splits (converged)
   e. splits = new_splits
3. Return splits (max iterations reached)
```

**Key implementation considerations:**

- Use float math throughout routing for performance (existing pattern)
- Convert to Decimal only at boundaries (existing pattern)
- Effective fee computation must handle both constant and tiered FeeQuote
- Convergence check: max relative change across all splits < 0.1%
- Fallback: if doesn't converge after 5 iterations, use last result
- Backward compatible: constant-fee strategies never enter iteration loop

**Error handling strategy:**

- Invalid tier structures: caught during FeeQuote construction (validation exists)
- Non-convergence: log warning, use last iteration result
- EVM call failures: fall back to constant fees
- Division by zero: handle in split computation (existing guards)

## Implementation Steps

### Step 1: Add EVM Function Selectors

Add function selectors for supportsFeeStructure() and getFeeStructure() to EVMStrategyExecutor.

**Files to modify:** `/Users/xinwan/Github/pvp_amm_challenge/amm_competition/evm/executor.py`

- Compute keccak256 hashes for function signatures
- Add SELECTOR_SUPPORTS_FEE_STRUCTURE constant
- Add SELECTOR_GET_FEE_STRUCTURE constant

### Step 2: Implement EVM Fee Structure Methods

Implement supports_fee_structure() and get_fee_structure() in EVMStrategyExecutor.

**Files to modify:** `/Users/xinwan/Github/pvp_amm_challenge/amm_competition/evm/executor.py`

- Implement supports_fee_structure(): call EVM, decode bool return
- Implement get_fee_structure(): encode TradeInfo calldata, call EVM, decode FeeStructure
- Handle EVM errors gracefully (return False/None)
- Convert WAD values to Decimal for FeeTier creation

### Step 3: Update EVM Adapter to Load Tiers

Modify EVMStrategyAdapter.after_initialize() to load fee structures from EVM.

**Files to modify:** `/Users/xinwan/Github/pvp_amm_challenge/amm_competition/evm/adapter.py`

- Add _load_fee_structure() private method
- Call in after_initialize() after getting constant fees
- Build FeeQuote with both constant fees and optional tiers
- Cache the tier structure (doesn't change during simulation)

### Step 4: Add Effective Fee Helper to Router

Add _compute_effective_fee() method to OrderRouter.

**Files to modify:** `/Users/xinwan/Github/pvp_amm_challenge/amm_competition/market/router.py`

- Accept AMM, trade_size, and direction
- Call appropriate effective_*_fee() method on AMM's current_fees
- Return as float for routing math
- Handle both constant and tiered fee quotes

### Step 5: Implement Iterative Split for Buy Direction

Modify _split_buy_two_amms() to support iterative refinement with tiered fees.

**Files to modify:** `/Users/xinwan/Github/pvp_amm_challenge/amm_competition/market/router.py`

- Check if any AMM has tiered fees (bid_tiers or ask_tiers not None)
- If all constant, use existing algorithm (no change)
- If any tiered:
  - Initial split with constant fees
  - Loop: compute effective fees, recompute split, check convergence
  - Return converged split
- Add convergence logging (debug level)

### Step 6: Implement Iterative Split for Sell Direction

Modify _split_sell_two_amms() to support iterative refinement with tiered fees.

**Files to modify:** `/Users/xinwan/Github/pvp_amm_challenge/amm_competition/market/router.py`

- Mirror buy direction logic
- Use bid_fee direction for effective fees (trader selling X)
- Same convergence criteria and max iterations

### Step 7: Extend to N-way Routing

Modify compute_optimal_split_buy() and compute_optimal_split_sell() for N-way routing.

**Files to modify:** `/Users/xinwan/Github/pvp_amm_challenge/amm_competition/market/router.py`

- Replace pairwise approximation with proper N-way iterative refinement
- For N strategies, compute N-way split in each iteration
- Use existing 2-way algorithm as subroutine within iteration
- Handle N ≤ 5 constraint (document in comments)

### Step 8: Update AMM Quote Methods (Optional Enhancement)

Consider whether AMM engine quote methods should use effective fees.

**Files to modify:** `/Users/xinwan/Github/pvp_amm_challenge/amm_competition/core/amm.py` (optional)

**Note:** Current design uses effective fees only in router for splitting. AMM engine continues using constant fees from current_fees.bid_fee/ask_fee. This is backward compatible and sufficient. Only modify if quotes need to reflect actual trade size.

### Step 9: Create Integration Test Suite

Create comprehensive tests for tiered fee routing.

**Files to modify:** Create `/Users/xinwan/Github/pvp_amm_challenge/tests/test_tiered_routing.py`

Test cases:
- Two AMMs: one constant, one tiered
- Two AMMs: both tiered with different structures
- Three AMMs: mixed constant/tiered
- Convergence behavior: verify 2-3 iterations typical
- Edge cases: all tiers, no tiers, single-tier
- Accounting accuracy: sum of PnLs = 0
- Near-optimality: compare to analytical solution where available

### Step 10: Add Router Convergence Tests

Add unit tests for convergence algorithm.

**Files to modify:** Create `/Users/xinwan/Github/pvp_amm_challenge/tests/test_router_convergence.py`

Test cases:
- Convergence with well-behaved fee structures
- Max iterations reached (pathological fees)
- Tolerance sensitivity
- Performance: verify < 10ms for 5 AMMs × 5 iterations

### Step 11: Add EVM Integration Tests

Test EVM adapter fee structure loading.

**Files to modify:** Extend existing EVM test suite or create new file

Test cases:
- Load tiers from TieredFeeStrategy.sol
- supportsFeeStructure() returns correct value
- Tier values match Solidity constants
- Backward compatibility with constant-fee strategies
- Error handling: strategy without getFeeStructure()

### Step 12: Update Documentation

Document the tiered fee feature for strategy authors.

**Files to modify:**
- `/Users/xinwan/Github/pvp_amm_challenge/README.md`
- Create `/Users/xinwan/Github/pvp_amm_challenge/docs/TIERED_FEES.md` (if doesn't exist)

Content:
- Overview of tiered fee system
- How to create tiered fee strategies in Solidity
- Router behavior with tiered fees (iterative refinement)
- Performance characteristics (2-3 iterations typical)
- Limitations (near-optimal, not perfect; N ≤ 5)
- Example: TieredFeeStrategy walkthrough

## Files Summary

| File Path | Changes |
|-----------|---------|
| `amm_competition/evm/executor.py` | Add function selectors, implement supports_fee_structure() and get_fee_structure() |
| `amm_competition/evm/adapter.py` | Add _load_fee_structure(), modify after_initialize() to load tiers |
| `amm_competition/market/router.py` | Add iterative refinement to _split_buy_two_amms(), _split_sell_two_amms(), extend N-way routing |
| `tests/test_tiered_routing.py` | New file: integration tests for mixed constant/tiered routing |
| `tests/test_router_convergence.py` | New file: unit tests for convergence algorithm |
| `tests/test_evm_tiers.py` | New file: EVM adapter tier loading tests |
| `README.md` | Add tiered fee overview, link to detailed docs |
| `docs/TIERED_FEES.md` | New file: comprehensive tiered fee guide (optional) |

## Critical Challenges

| Challenge | Mitigation |
|-----------|-----------|
| Non-convergence with pathological fee structures | Max 5 iterations cap, use last result, log warning. Create test with extreme tiers to verify fallback. |
| EVM call overhead with supportsFeeStructure() check | Cache result after first check, only call once per strategy per simulation. |
| Accounting errors in N-way splits with convergence | Comprehensive integration tests with PnL verification. Ensure sum of splits equals total_amount in each iteration. |

## Quality Checks

Before considering this feature complete:

1. Can constant-fee strategies run unchanged? (backward compatibility)
2. Does routing converge in ≤ 5 iterations for typical tier structures?
3. Is the result within 0.1% of analytical optimal (where computable)?
4. Do integration tests verify sum(PnLs) = 0 across all strategies?
5. Are all edge cases covered (all tiers, no tiers, mixed)?
6. Is documentation clear enough for strategy authors?
7. Does performance remain acceptable (< 10ms for 5 AMMs)?

## Implementation Timeline

**Phase 1: EVM Integration** (1-2 hours)
- Steps 1-3: EVM function selectors, methods, adapter

**Phase 2: Router Iterative Refinement** (3-4 hours)
- Steps 4-7: Router helpers, 2-way iterative, N-way extension

**Phase 3: Testing** (2-3 hours)
- Steps 9-11: Integration tests, convergence tests, EVM tests

**Phase 4: Documentation** (1 hour)
- Step 12: README updates, tiered fee guide

**Total Estimated Time:** 7-10 hours

## Success Metrics

1. All existing tests pass (backward compatibility)
2. All new tests pass (tiered fee correctness)
3. Convergence achieved in ≤ 3 iterations for 95% of test cases
4. Performance: N-way routing with tiered fees < 10ms for N ≤ 5
5. Accounting accurate: sum(PnLs) within 1e-10 of zero
6. Documentation complete and reviewed

## Notes for Implementer

- **Start with EVM integration** - this is the foundation and easiest to test in isolation
- **Test 2-way routing thoroughly** before extending to N-way - easier to debug
- **Use existing tests as templates** - fee tier tests already exist, extend pattern
- **Log convergence metrics** during development - helps tune tolerance and max_iterations
- **Performance matters** - router is called frequently, keep iterations low
- **Backward compatibility is non-negotiable** - must not break existing strategies
