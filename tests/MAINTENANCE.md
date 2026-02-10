# Test Suite Maintenance Guide

## Overview

This guide helps maintainers keep the economic correctness test suite healthy, performant, and up-to-date.

## Regular Maintenance Tasks

### Weekly Tasks

- [ ] Review CI failures and investigate root causes
- [ ] Check for slow unmarked tests (`pytest --durations=0`)
- [ ] Monitor test execution time trends
- [ ] Review coverage reports for gaps

### Monthly Tasks

- [ ] Update dependencies in `pyproject.toml`
- [ ] Review and update tolerance thresholds if needed
- [ ] Audit test markers for consistency
- [ ] Check for deprecated pytest features
- [ ] Update documentation for new patterns

### Quarterly Tasks

- [ ] Full test suite audit
- [ ] Performance optimization review
- [ ] Coverage target review (currently 90%)
- [ ] Update acceptance criteria if system changes
- [ ] Review and consolidate duplicate tests

## Health Checks

### Test Execution Time

Target: Fast tests < 5 minutes, total < 20 minutes

```bash
# Check current timing
pytest tests/ -m "not slow" --durations=0

# Acceptable if:
# - No individual test > 5 seconds (without @pytest.mark.slow)
# - Total fast tests < 5 minutes
# - Total slow tests < 15 minutes
```

**Action if violated:**
- Mark slow tests with `@pytest.mark.slow`
- Reduce trade counts in random tests
- Use smaller AMM sets where possible
- Consider splitting into multiple tests

### Coverage Thresholds

Target: > 90% for core modules

```bash
# Check coverage
pytest tests/ --cov=amm_competition --cov-report=term-missing

# Acceptable if:
# - amm_competition/core/*.py > 90%
# - amm_competition/market/*.py > 90%
# - Overall > 85%
```

**Action if below threshold:**
- Add tests for uncovered branches
- Remove dead code
- Add `# pragma: no cover` for debug/error paths
- Review acceptance criteria coverage

### CI Stability

Target: < 1% flaky test rate

```bash
# Run tests multiple times to check stability
for i in {1..10}; do pytest tests/ -m "not slow" || echo "Run $i failed"; done

# Acceptable if:
# - All 10 runs pass
# - No intermittent failures
```

**Action if unstable:**
- Check for missing `random.seed()` calls
- Verify AMM state reset between tests
- Look for shared mutable state
- Add explicit cleanup in fixtures

### Documentation Sync

Ensure documentation matches code:

```bash
# Check that all test files are documented
ls tests/test_*.py | while read f; do
    grep "$(basename $f)" tests/README.md || echo "Missing: $f"
done
```

**Action if out of sync:**
- Update `tests/README.md` with new test categories
- Update `TEST_ARCHITECTURE.md` with new patterns
- Update `QUICKSTART.md` with new commands

## Monitoring Metrics

### Test Count by Category

```bash
# Count tests by marker
pytest --collect-only -q tests/ | grep "test_" | wc -l  # Total
pytest --collect-only -m backward_compat | wc -l         # Backward compat
pytest --collect-only -m economic | wc -l                 # Economic
pytest --collect-only -m edge_case | wc -l                # Edge cases
pytest --collect-only -m slow | wc -l                     # Slow tests
```

Expected distribution:
- Backward compatibility: 15-25 tests
- Economic properties: 30-50 tests
- Edge cases: 10-20 tests
- Unit tests: 20-30 tests

### Coverage Trends

Track over time:
- Overall coverage percentage
- Lines of code vs lines tested
- Branch coverage percentage

```bash
# Generate coverage and save
pytest tests/ --cov=amm_competition --cov-report=json
# Compare coverage.json with previous runs
```

### Performance Trends

Track over time:
- Total test execution time
- Slowest 10 tests
- Average test duration

```bash
# Generate timing report
pytest tests/ --durations=0 > test_timings_$(date +%Y%m%d).txt
# Compare with previous reports
```

## Common Maintenance Issues

### Issue: Test Fails Only in CI

**Symptoms:**
- Test passes locally but fails in GitHub Actions
- Intermittent failures
- Platform-specific failures

**Diagnosis:**
```bash
# Check for platform differences
grep -r "sys.platform\|platform.system" tests/

# Check for timing dependencies
grep -r "time.sleep\|asyncio" tests/

# Check for environment dependencies
grep -r "os.environ\|getenv" tests/
```

**Solutions:**
- Use `Decimal` instead of `float` for all monetary values
- Set explicit random seeds in all tests using randomness
- Avoid timing-dependent assertions
- Use fixtures to ensure clean state

### Issue: Coverage Decreasing

**Symptoms:**
- Coverage percentage dropping over time
- New features not covered by tests

**Diagnosis:**
```bash
# Find uncovered lines
pytest tests/ --cov=amm_competition --cov-report=term-missing

# Check diff coverage for recent changes
git diff main | grep "^+" | grep -v "^+++"
```

**Solutions:**
- Add tests for new features before merging
- Review PRs for test coverage
- Add coverage checks to CI (fail if < threshold)
- Use coverage comments in PRs

### Issue: Tests Getting Slower

**Symptoms:**
- CI taking longer over time
- Individual tests timing out
- Fast tests exceeding 5-minute target

**Diagnosis:**
```bash
# Identify slowest tests
pytest tests/ --durations=20

# Compare with baseline
diff test_timings_baseline.txt test_timings_current.txt
```

**Solutions:**
- Mark slow tests with `@pytest.mark.slow`
- Reduce trade counts in random tests
- Use smaller AMM sets (2-3 instead of 5)
- Cache expensive computations in fixtures
- Run tests in parallel with `pytest -n auto`

### Issue: Flaky Tests

**Symptoms:**
- Tests pass/fail randomly
- Different results on reruns
- "Works on my machine" syndrome

**Diagnosis:**
```bash
# Run test multiple times
pytest tests/test_symmetry_fairness.py -x --count=100

# Check for randomness without seeds
grep -r "random\." tests/ | grep -v "random.seed"
```

**Solutions:**
- Always use `random.seed()` in tests with randomness
- Use fixtures to provide deterministic seeds
- Reset AMM state between tests
- Avoid shared mutable state
- Use `pytest-randomly` plugin to detect order dependencies

## Updating Fixtures

### When to Update

Update fixtures when:
- New AMM types are added
- Fee structures change
- Pool configurations need new profiles
- Acceptance criteria change

### How to Update

1. **Add new fixture to `conftest.py`:**

```python
@pytest.fixture
def new_amm_type() -> list[AMM]:
    """Description of new AMM type."""
    # Implementation
    return [...]
```

2. **Document in fixture README:**

```markdown
### New AMM Type

Description...

**Usage:**
\```python
def test_with_new_type(new_amm_type):
    amms = new_amm_type
    # ...
\```
```

3. **Add tests using new fixture:**

```python
def test_new_property(new_amm_type):
    """Test property with new AMM type."""
    # ...
```

4. **Update fixture documentation:**
- `tests/fixtures/README.md`
- `tests/README.md` (if new category)

## Updating Acceptance Criteria

### Process

1. **Identify need for change:**
   - Economic property violation
   - System design change
   - Performance improvement
   - Bug fix

2. **Document rationale:**
   - Why is the current criterion insufficient?
   - What is the new requirement?
   - What is the impact on existing tests?

3. **Update criteria in code:**

```python
# Before
assert abs(difference) < Decimal("0.0001")  # 0.01%

# After
assert abs(difference) < Decimal("0.001")   # 0.1%
```

4. **Update documentation:**
   - `tests/README.md` (acceptance criteria section)
   - `TESTING.md` (acceptance criteria table)
   - Test docstrings

5. **Verify all tests:**

```bash
# Ensure all tests still pass with new criteria
pytest tests/ -v
```

## Adding New Test Categories

### Steps

1. **Create test file:**

```bash
touch tests/test_new_category.py
```

2. **Implement tests:**

```python
"""Test module for new category.

Description of what this category tests...
"""

import pytest
from decimal import Decimal
# ... imports ...

class TestNewCategory:
    """Tests for new economic property."""

    @pytest.mark.economic
    @pytest.mark.integration
    def test_property(self, standard_amm_set):
        """Test that property holds."""
        # ...
```

3. **Add marker if needed:**

In `conftest.py`:
```python
def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "new_marker: Description of new marker"
    )
```

4. **Update documentation:**
   - Add section in `tests/README.md`
   - Update `TEST_ARCHITECTURE.md` diagram
   - Add to `QUICKSTART.md` examples
   - Update `TESTING.md` overview

5. **Add to CI:**

In `.github/workflows/economic-tests.yml`:
```yaml
- name: Run new category tests
  run: |
    pytest tests/test_new_category.py -v --tb=short
  timeout-minutes: 3
```

## Deprecating Old Tests

### When to Deprecate

Deprecate tests when:
- Feature is removed
- Test is redundant
- Property is no longer relevant
- Better test exists

### Process

1. **Mark as deprecated:**

```python
@pytest.mark.skip(reason="Deprecated: replaced by test_new_approach")
def test_old_approach():
    """Old test approach (deprecated)."""
    pass
```

2. **Document deprecation:**

```python
"""
DEPRECATED: This test is deprecated as of 2026-02-15.

Reason: Feature removed in PR #123
Replacement: Use test_new_approach instead
Removal: Planned for 2026-03-01
"""
```

3. **Update documentation:**
- Mark as deprecated in `tests/README.md`
- Add note to changelog
- Update related documentation

4. **Schedule removal:**
- Create issue to remove after grace period (2-4 weeks)
- Notify team in PR
- Remove in follow-up PR

## Best Practices

### Do's

✅ Use fixtures for common setups
✅ Use `Decimal` for all monetary values
✅ Set random seeds for reproducibility
✅ Write clear docstrings with acceptance criteria
✅ Use markers to categorize tests
✅ Keep tests isolated (no shared state)
✅ Test one property per test method
✅ Use descriptive test names
✅ Add comments for complex logic
✅ Update documentation with code changes

### Don'ts

❌ Don't use floats for monetary values
❌ Don't share mutable state between tests
❌ Don't use hardcoded magic numbers
❌ Don't write tests that depend on execution order
❌ Don't skip tests without explanation
❌ Don't ignore failing tests
❌ Don't write overly complex test logic
❌ Don't test implementation details
❌ Don't duplicate test fixtures
❌ Don't forget to mark slow tests

## Checklist for New Tests

Use this checklist when reviewing new tests:

### Code Quality
- [ ] Test has clear docstring with acceptance criteria
- [ ] Uses appropriate fixtures from `conftest.py`
- [ ] Uses `Decimal` for all monetary values
- [ ] Sets random seed if using randomness
- [ ] Has appropriate markers (`@pytest.mark.*`)
- [ ] Follows existing naming conventions
- [ ] No code duplication
- [ ] No hardcoded magic numbers

### Functionality
- [ ] Tests one clear property
- [ ] Assertions have clear error messages
- [ ] Uses appropriate tolerance thresholds
- [ ] Handles edge cases
- [ ] Cleans up state (if needed)

### Performance
- [ ] Completes in reasonable time (< 5s for non-slow)
- [ ] Marked as `@pytest.mark.slow` if > 5 seconds
- [ ] Uses minimal AMM sets (2-3 when possible)
- [ ] Uses small trade counts for random tests

### Documentation
- [ ] Documented in `tests/README.md`
- [ ] Acceptance criteria documented
- [ ] Example usage provided (if new pattern)
- [ ] Related to implementation plan (if applicable)

### CI Integration
- [ ] Passes in CI
- [ ] Added to appropriate CI job (if needed)
- [ ] Covered by existing coverage configuration

## Emergency Procedures

### All Tests Failing in CI

1. **Check CI logs:**
   - Look for dependency installation errors
   - Check for environment issues
   - Verify Python version compatibility

2. **Reproduce locally:**
   ```bash
   # Use same Python version as CI
   pytest tests/ -v
   ```

3. **Bisect if needed:**
   ```bash
   git bisect start
   git bisect bad HEAD
   git bisect good <last-known-good>
   git bisect run pytest tests/
   ```

4. **Emergency fixes:**
   - Pin dependency versions if incompatibility
   - Skip failing tests temporarily (with issue link)
   - Revert breaking change if critical

### Coverage Suddenly Drops

1. **Check what changed:**
   ```bash
   git diff main -- amm_competition/
   ```

2. **Identify uncovered code:**
   ```bash
   pytest tests/ --cov=amm_competition --cov-report=html
   # Open htmlcov/index.html
   ```

3. **Add missing tests or mark as no cover:**
   ```python
   # For unreachable code
   if False:  # pragma: no cover
       # Debug code
   ```

### Tests Timeout in CI

1. **Identify slow tests:**
   ```bash
   pytest tests/ --durations=0
   ```

2. **Temporary workaround:**
   - Increase timeout in `.github/workflows/economic-tests.yml`
   - Skip slow tests temporarily

3. **Permanent fix:**
   - Mark as slow: `@pytest.mark.slow`
   - Optimize test logic
   - Reduce iteration counts
   - Use smaller test data

## Resources

- **Pytest Documentation**: https://docs.pytest.org/
- **Coverage.py**: https://coverage.readthedocs.io/
- **GitHub Actions**: https://docs.github.com/en/actions
- **Decimal Module**: https://docs.python.org/3/library/decimal.html

## Contact

For maintenance questions:
- Review this guide first
- Check `tests/README.md` for test-specific info
- Consult implementation plans in project root
- Open issue for clarification
