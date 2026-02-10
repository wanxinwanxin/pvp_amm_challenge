# User Requirements for Economic Correctness Testing

**Date:** 2026-02-10
**Source:** User-provided test ideas for validating the modified AMM system

---

## Original User-Specified Tests

The user identified these key properties to test:

### 1. Backward Compatibility
> "If I submit a single strategy, and run it in the old version, it should give same results as what I get if I run the new game with the same strategy and the baseline strategy as the second strategy"

**Implementation:** `tests/test_backward_compatibility.py` (25 tests)
- Compares constant-fee strategies in old vs new system
- Validates splits, execution prices, and final states match
- Acceptance: < 0.01% difference

### 2. Symmetry / Fairness
> "If I submit the same strategy twice to the new version, the competition should show that they are mostly tied (except for noise caused by randomness, if any)"

**Implementation:** `tests/test_symmetry_fairness.py` (15 tests)
- Identical strategies should have symmetric PnL
- Tests with multiple random seeds for consistency
- Acceptance: < 5% PnL difference (accounting for randomness)

### 3. Determinism / Stability
> "If I submit the same set of strategies and run the competition a few times, it should give similar results"

**Implementation:** `tests/test_determinism.py` (17 tests)
- Fixed seeds produce bit-exact reproduction
- Multiple runs with same seed are identical
- Acceptance: Bit-exact Decimal equality

---

## Extended Properties (Added Based on Discussion)

After discussing "what else?", we expanded to cover:

### 4. No Arbitrage Creation
**Rationale:** The modified routing should not create "free money" opportunities

**Implementation:** `tests/test_no_arbitrage.py` (23 tests)
- Buy-then-sell cycles always lose money (equal to fees)
- No profitable arbitrage across AMMs
- Acceptance: Loss equals fees paid (< 0.1% error)

### 5. Optimal Routing Property
**Rationale:** Router's split should achieve better execution than single-AMM routing

**Implementation:** `tests/test_optimal_routing.py` (24 tests)
- Split routing beats or equals single-AMM execution
- Marginal prices equalized after routing
- Acceptance: Split ≥ single, converges in ≤5 iterations

### 6. Accounting Correctness
**Rationale:** Total fees collected should match fees deducted; value should be conserved

**Implementation:** `tests/test_accounting_correctness.py` (22 tests)
- Fees paid by traders = fees collected by AMMs
- Sum of all PnLs ≈ zero (conservation of value)
- K invariant preserved (accounting for fees)
- Acceptance: Value conserved within 0.01%

### 7. Convergence Stability
**Rationale:** Iterative routing algorithm should always converge without infinite loops

**Implementation:** `tests/test_convergence_stability.py` (36+ tests)
- Algorithm converges within max iterations (5)
- Well-behaved cases converge in 2-3 iterations
- Pathological cases handled gracefully
- Acceptance: 100% convergence rate, no exceptions

### 8. Edge Case Robustness (Implicit)
**Rationale:** Extreme cases shouldn't break the system

**Implementation:** `tests/test_edge_cases.py` (14 tests)
- Tiny trades (0.0001) and huge trades (1,000,000)
- Extreme pool imbalances (1:1,000,000)
- Zero fees and maximum fees (10%)
- 1000-trade stress test
- Acceptance: No crashes, graceful degradation

---

## Summary

**User-Specified Core Properties:** 3
- Backward compatibility
- Symmetry/fairness
- Determinism

**Extended Properties (Discussed):** 5
- No arbitrage
- Optimal routing
- Accounting correctness
- Convergence stability
- Edge case handling

**Total Properties Tested:** 8
**Total Test Cases Implemented:** 150+

---

## Acceptance Criteria Summary

| Property | User-Specified Criteria | Implementation Status |
|----------|------------------------|----------------------|
| Backward Compatibility | Same results old vs new | ✅ < 0.01% difference |
| Symmetry | Mostly tied | ✅ < 5% PnL difference |
| Determinism | Similar results | ✅ Bit-exact reproduction |
| No Arbitrage | N/A (extended) | ✅ Loss = fees ±0.1% |
| Optimal Routing | N/A (extended) | ✅ Split ≥ single |
| Accounting | N/A (extended) | ✅ Value conserved ±0.01% |
| Convergence | N/A (extended) | ✅ ≤5 iterations |
| Edge Cases | N/A (extended) | ✅ No crashes |

---

## Running the Tests

To validate all properties:

```bash
# Run all tests
pytest tests/test_*.py -v

# Run user-specified core tests only
pytest tests/test_backward_compatibility.py -v
pytest tests/test_symmetry_fairness.py -v
pytest tests/test_determinism.py -v

# Run extended property tests
pytest tests/test_no_arbitrage.py -v
pytest tests/test_optimal_routing.py -v
pytest tests/test_accounting_correctness.py -v
pytest tests/test_convergence_stability.py -v
pytest tests/test_edge_cases.py -v
```

---

## Notes

- The user's original intuition about needed tests was excellent and formed the foundation
- Extended properties were added through discussion to ensure comprehensive economic correctness
- All tests use Decimal precision to avoid floating-point errors
- Tests are deterministic (fixed seeds) for reproducibility
- Comprehensive documentation provided for each test category
