# Convergence Stability Testing - Quick Reference

## 🎯 Purpose
Verify iterative routing algorithm converges reliably without infinite loops or failures.

## 📁 Files
- **Tests**: `tests/test_convergence_stability.py`
- **Docs**: `tests/test_convergence_stability_README.md`
- **Runner**: `run_convergence_tests.py`

## ⚡ Quick Commands

```bash
# Run all convergence tests
pytest tests/test_convergence_stability.py -v

# Run specific scenario
pytest tests/test_convergence_stability.py::TestConvergencePathologicalTiers -v

# Fast check (quiet mode)
pytest tests/test_convergence_stability.py -q

# With timing
pytest tests/test_convergence_stability.py -v --durations=10
```

## ✅ Acceptance Criteria

| Scenario | Iterations | Deviation | Time |
|----------|-----------|-----------|------|
| Well-behaved | 2-3 | <0.1% | <5ms |
| Pathological | ≤5 | <1% | <100ms |
| Identical AMMs | 1-2 | <5% split diff | <5ms |
| 5 AMMs | N/A | <0.1% | <20ms |

## 🧪 Test Classes

1. **TestConvergenceWithinMaxIterations** - No infinite loops
2. **TestConvergenceQualityWellBehavedTiers** - 2-3 iteration convergence
3. **TestConvergencePathologicalTiers** - Steep transitions complete
4. **TestConvergenceExtremeTradeSizes** - 0.001 to 100,000
5. **TestConvergenceExtremeTierThresholds** - Any threshold scale
6. **TestConvergenceSingleTierBoundary** - No oscillation
7. **TestConvergenceIdenticalAMMs** - Equal splits
8. **TestConvergenceSellDirection** - Sell reliability
9. **TestConvergenceMultipleAMMs** - 2, 3, 5 AMMs

## 🔍 Key Metrics

```python
monitor = ConvergenceMonitor()
metrics = monitor.verify_convergence(splits, total_amount)

# Returns:
# - valid: bool (splits sum to total)
# - max_deviation: Decimal (from total)
# - num_splits: int (non-zero)
# - min_split_ratio: Decimal
# - max_split_ratio: Decimal
```

## 🏗️ Fee Profiles

```python
# Available via get_baseline_fee_tiers(profile)
"conservative"  # 30→20→10 bps (gradual)
"moderate"      # 30→15→5 bps  (moderate)
"aggressive"    # 50→10→1 bps  (steep)
"pathological"  # 100%→1→0.1 bps (extreme)
```

## 🚨 Warning Signs

❌ Test failures (exceptions)
❌ Timeout (>100ms)
❌ Invalid splits (don't sum to total)
❌ Negative amounts
❌ High deviation (>1% on well-behaved)

## 🔧 Common Patterns

### Test a new fee structure
```python
def test_my_fee_structure():
    my_tiers = [
        (Decimal("0"), Decimal("0.004")),
        (Decimal("200"), Decimal("0.0015")),
    ]

    amms = [
        create_tiered_fee_amm("A", my_tiers, Decimal("10000"), Decimal("10000")),
        create_tiered_fee_amm("B", my_tiers, Decimal("10000"), Decimal("10000"))
    ]

    router = OrderRouter()
    splits = router.compute_optimal_split_buy(amms, Decimal("500"))

    monitor = ConvergenceMonitor()
    metrics = monitor.verify_convergence(splits, Decimal("500"))

    assert metrics['valid']
    assert metrics['max_deviation'] < Decimal("0.001")
```

### Test extreme scenario
```python
def test_extreme_case():
    try:
        splits = router.compute_optimal_split_buy(amms, amount)
        assert len(splits) > 0, "Should produce splits"

        # Relaxed tolerance for extreme cases
        monitor = ConvergenceMonitor()
        metrics = monitor.verify_convergence(splits, amount,
                                            tolerance=Decimal("0.01"))
        assert metrics['max_deviation'] < Decimal("0.01")
    except Exception as e:
        pytest.fail(f"Should not raise exception: {e}")
```

## 📊 Expected Results

**36+ tests should all pass with:**
- ✅ No exceptions
- ✅ Splits sum to total
- ✅ Fast execution
- ✅ Quality solutions

## 🔗 Integration

### Pre-commit
```bash
pytest tests/test_convergence_stability.py -q
```

### CI/CD
```yaml
- name: Convergence Tests
  run: pytest tests/test_convergence_stability.py -v --tb=short
```

### Development
```bash
# Quick check during development
pytest tests/test_convergence_stability.py::TestConvergenceWithinMaxIterations -v

# Full validation before PR
pytest tests/test_convergence_stability.py -v
```

## 📖 Related Files

- Router: `amm_competition/market/router.py`
- Fee tiers: `amm_competition/core/trade.py`
- Fixtures: `tests/fixtures/economic_fixtures.py`
- Basic tests: `tests/test_router_convergence.py`

## 💡 Tips

1. **Start with well-behaved**: Test conservative/moderate first
2. **Then pathological**: Verify edge cases still work
3. **Check performance**: Use `--durations` to find slow tests
4. **Monitor iterations**: Though not exposed, quality metrics indicate convergence
5. **Relax tolerance**: For extreme cases, 1% deviation is acceptable

## 🎓 Understanding Convergence

**Iterative Refinement Process:**
1. Start with constant fee estimate
2. Estimate output amounts
3. Compute effective fees based on sizes
4. Recompute split with effective fees
5. Check convergence (change < 0.1%)
6. Repeat until converged or max iterations (5)

**Why it works:**
- Well-behaved tiers: Smooth fee curves, quick convergence
- Pathological tiers: May hit max iterations, still produces valid solution
- Identical AMMs: Converges to equal split very quickly

## 🏆 Success Criteria

All tests pass → Convergence algorithm is production-ready!

---

**Quick Start**: `pytest tests/test_convergence_stability.py -v`
