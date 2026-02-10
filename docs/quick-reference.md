# PVP AMM Competition: Quick Reference Guide

**Version:** 2.0 (Modified System)
**Date:** 2025-02-10
**Format:** 2-page printable handout

---

## What Changed: The Big Five

| Feature | Original | Modified | Impact |
|---------|----------|----------|---------|
| **Competition Format** | You vs Baseline | Strategy A vs Strategy B | Zero-sum, adversarial dynamics |
| **Scoring Method** | Cumulative edge | Win count (primary) | Optimize for consistency |
| **Fee Model** | Constant only | Tiered (up to 3 levels) | Volume-based pricing strategies |
| **Routing Algorithm** | 2-AMM analytical | N-way iterative (N≤5) | Handles tiered fees, realistic aggregation |
| **Interface** | CLI tool | Web platform + leaderboard | Transparency, analytics, iteration |

---

## Core Concepts

### Head-to-Head Competition

**How It Works:**
- Two strategies compete across 50 simulations
- Each simulation: Both start with identical reserves (100 X, 10,000 Y @ price 100)
- Retail flow splits optimally based on fees (router minimizes trader slippage)
- Winner: Strategy with higher edge (retail profit - arb loss) in that sim

**Match Winner:**
- **Primary criterion:** Win count (need 26+ wins out of 50)
- **Tiebreaker:** Average edge across all simulations

**Example:**
```
Strategy A: 28 wins, 20 losses, 2 draws → Avg edge +12.5 bps
Strategy B: 22 wins, 28 losses, 0 draws → Avg edge +15.0 bps
Winner: A (more wins, despite lower average edge)
```

### Tiered Fee Structures

**What They Are:**
Size-dependent fee rates with up to 3 tiers per direction (bid/ask)

**Example Structure:**
```
Tier 1 (0-100 X):      30 basis points
Tier 2 (100-1000 X):   20 basis points
Tier 3 (1000+ X):      10 basis points
```

**Effective Fee Calculation:**
For a 150 X trade:
- 100 X @ 30bps = 0.300
- 50 X @ 20bps = 0.100
- Total: 0.400 / 150 = **26.7 bps average**

**Why They Matter:**
- Model real venues (Uniswap v3, dYdX have volume discounts)
- Enable strategic differentiation (target specific flow types)
- Create competitive advantage beyond just price

### N-Way Iterative Routing

**How It Works:**
1. Start with initial split (using constant fees)
2. Compute effective fees at current split sizes
3. Recompute optimal split with effective fees
4. Check convergence (< 0.1% change)
5. Repeat steps 2-4 until converged (max 5 iterations)

**Performance:**
- Typical convergence: 2-3 iterations
- Speed: < 10ms for 5-AMM split with tiered fees
- Optimality: Within 0.1% of true optimal

**Backward Compatible:**
Constant-fee strategies use fast analytical path (no iterations)

---

## Strategy Design Checklist

### Step 1: Choose Your Archetype

**Option A: Volume Discounter** (Attract large trades)
```
Tier 1: 35-40bps (0-100 X)     ← High base, filter small
Tier 2: 15-20bps (100-1000 X)  ← Competitive medium
Tier 3: 5-10bps (1000+ X)      ← Aggressive whales
```
✅ Best when: Opponent has flat fees, large trades common
❌ Risk: Toxic large flow, arb vulnerability

**Option B: Retail Specialist** (Dominate small trades)
```
Tier 1: 20-25bps (0-500 X)     ← Competitive small
Tier 2: 25-30bps (500-2000 X)  ← Slight increase
Tier 3: 35-40bps (2000+ X)     ← Price out large
```
✅ Best when: Opponent whale-focused, retail flow frequent
❌ Risk: Lose share if large trades dominate

**Option C: Adaptive Defender** (Dynamic adjustment)
```python
def afterSwap(trade):
    if recent_pnl < -50:
        return widen_all_fees(+5bps)  # Arb protection
    elif price_volatility > 0.02:
        return increase_base(+3bps)   # Volatility hedge
    elif win_rate > 0.7:
        return lower_fees(-2bps)      # Capture more volume
    else:
        return baseline_tiers()
```
✅ Best when: Volatile markets, dynamic opponents
❌ Risk: Over-adjustment, lag in response

### Step 2: Implement in Solidity

**Minimal Tiered Strategy Template:**
```solidity
contract MyStrategy is AMMStrategyBase {
    function supportsFeeStructure() external pure returns (bool) {
        return true;  // Enable tiered fees
    }

    function getFeeStructure(TradeInfo calldata)
        external pure returns (FeeStructure memory fs)
    {
        // Define bid tiers
        fs.bidTiers[0] = createTier(0, 30);        // 0-100: 30bps
        fs.bidTiers[1] = createTier(100 * WAD, 20); // 100-1000: 20bps
        fs.bidTiers[2] = createTier(1000 * WAD, 10); // 1000+: 10bps
        fs.bidTierCount = 3;

        // Mirror for ask tiers (or asymmetric if desired)
        fs.askTiers[0] = createTier(0, 30);
        fs.askTiers[1] = createTier(100 * WAD, 20);
        fs.askTiers[2] = createTier(1000 * WAD, 10);
        fs.askTierCount = 3;

        return fs;
    }

    function afterSwap(TradeInfo calldata)
        external pure returns (uint256, uint256)
    {
        return (bpsToWad(30), bpsToWad(30));  // Fallback
    }
}
```

### Step 3: Test & Iterate

**Testing Workflow:**
1. Submit strategy to platform
2. Run 5-10 matches against diverse opponents
3. Analyze match history:
   - Win rate overall
   - Win rate by trade size category
   - Average edge per match
   - Head-to-head records
4. Identify weaknesses (losing to specific archetypes?)
5. Adjust tier thresholds or fee levels
6. Repeat from step 2

**Target Metrics:**
- **Win rate:** 60%+ across diverse opponents
- **Consistency:** Win by similar margins (not high variance)
- **Coverage:** Test against at least 5 different strategies

---

## Common Pitfalls to Avoid

### ❌ Pitfall #1: Optimizing for Expected Value Only
**Problem:** High-variance strategy (big wins, frequent small losses)
**Example:** Win 15/50 sims by +100 each, lose 35/50 by -20 each
**Result:** 30% win rate → You lose the match
**Fix:** Target consistency - win 26+ sims, even by small margins

### ❌ Pitfall #2: Meaningless Tier Differences
**Problem:** Tiers barely different (30bps → 29bps → 28bps)
**Result:** No strategic advantage, just slower routing
**Fix:** Make tiers meaningful (5-10bps gaps minimum)

### ❌ Pitfall #3: Static Fee Structures
**Problem:** Set fees once in `afterInitialize()`, never adjust
**Result:** Exploited when conditions change (volatility spikes, arb attacks)
**Fix:** Use `afterSwap()` callback to adapt based on recent performance

### ❌ Pitfall #4: Racing to the Bottom
**Problem:** "I'll set 5bps everywhere to win on price!"
**Result:** Attract toxic flow, lose to adverse selection, lower edge
**Fix:** Use tiers to attract good flow, price out bad flow

### ❌ Pitfall #5: Insufficient Testing
**Problem:** Run 1 match, assume strategy is optimal
**Result:** Overfitted to one opponent
**Fix:** Test against 5-10 diverse strategies, analyze patterns

---

## Winning Principles

### 1. Optimize for Win Probability, Not Just EV
- **Old thinking:** "Maximize total edge across all sims"
- **New thinking:** "Win 26+ out of 50 simulations"
- **Implication:** Consistency matters more than variance

### 2. Design Fee Structures, Not Just Levels
- **Old thinking:** "Set bid=30bps, ask=30bps, done"
- **New thinking:** "Design tier structure targeting my niche"
- **Questions to answer:**
  - Who are my target traders? (retail vs institutional)
  - What trade sizes do I want? (small frequent vs large rare)
  - How do I price out toxic flow?

### 3. Adapt to Your Opponent
- **Old thinking:** "Optimize against fixed baseline"
- **New thinking:** "Study opponent's structure, exploit weaknesses"
- **If opponent has:**
  - Aggressive low fees → Find niche they're weak in
  - Flat structure → Exploit with targeted tiers
  - Specific thresholds → Arbitrage the gaps

### 4. Use the Data
- **Old thinking:** "No feedback except final score"
- **New thinking:** "Leaderboard + match history = intelligence"
- **Actions:**
  - Study opponent win rates by category
  - Analyze head-to-head records
  - Identify successful patterns
  - Test counter-strategies

---

## Key Resources

### Documentation
- **System Overview:** `README.md` in repo
- **Economic Testing:** `tests/README.md`
- **Technical Details:** `20250210-complete-tiered-fee-routing.md`
- **User Requirements:** `USER_REQUIREMENTS.md`

### Platform
- **Web App:** [Streamlit app URL]
- **Leaderboard:** View all strategies, win rates, match history
- **Match Creation:** Select any 2 strategies, run 50 simulations
- **Analytics:** Performance over time, fee tier analysis

### Support
- **Slack Channel:** `#amm-challenge` for strategy discussion
- **GitHub Issues:** Bug reports and feature requests
- **1-on-1 Help:** Contact [lead engineer] for technical questions

---

## Quick Start: Your First Week

### Day 1-2: Learn
- [ ] Read `README.md` and this quick reference
- [ ] Browse leaderboard, study top 5 strategies
- [ ] Review match history, identify winning patterns

### Day 3-4: Simple Test
- [ ] Implement constant-fee strategy (familiar territory)
- [ ] Submit to platform
- [ ] Run 3-5 matches against different opponents
- [ ] Analyze results: What worked? What didn't?

### Day 5-7: Tiered Strategy
- [ ] Choose archetype (Discounter, Specialist, or Adaptive)
- [ ] Implement 3-tier structure in Solidity
- [ ] Test against leaderboard top 5
- [ ] Iterate based on match history data

### Week 2+: Optimize
- [ ] Adjust tier thresholds based on performance
- [ ] Test counter-strategies against your weaknesses
- [ ] Aim for 60%+ overall win rate
- [ ] Share learnings with team

---

## Terminology

**Edge:** Profit from retail trades - losses to arbitrageurs (in basis points)

**Win:** In a single simulation, the strategy with higher edge wins

**Match:** 50 simulations between two strategies; winner has most simulation wins

**Tier:** A fee rate applied to trades within a size range (e.g., 0-100 X: 30bps)

**Effective Fee:** Weighted average fee across tiers for a given trade size

**Router:** Algorithm that splits retail orders optimally across AMMs

**Convergence:** Iterative routing stabilizes when splits change < 0.1% between iterations

**Basis Point (bps):** 1/100 of 1%, so 30bps = 0.30% = 0.003

---

## Performance Benchmarks

### Routing Speed
- **2-AMM constant fees:** < 1ms (analytical)
- **2-AMM tiered fees:** ~3ms (2-3 iterations)
- **5-AMM tiered fees:** ~9ms (2-3 iterations)

### Convergence Stats (1000 random scenarios)
- **1 iteration:** 12.3% of cases
- **2 iterations:** 48.7% of cases
- **3 iterations:** 34.2% of cases
- **4+ iterations:** 4.8% of cases
- **Average:** 2.31 iterations

### Test Coverage
- **Total tests:** 150+
- **Categories:** 8 (Backward Compat, Symmetry, Determinism, No-Arb, Optimal Routing, Accounting, Convergence, Edge Cases)
- **Code coverage:** 93% (core modules)
- **CI runtime:** < 5 minutes

---

## Strategy Comparison Example

| Metric | Constant 25bps | Whale Hunter (40-15-5) | Retail Specialist (20-28-35) |
|--------|---------------|------------------------|------------------------------|
| **Small trade fee** | 25bps | 40bps | 20bps |
| **Medium trade fee** | 25bps | 15bps | 28bps |
| **Large trade fee** | 25bps | 5bps | 35bps |
| **Targets** | Balanced | Large institutional | Small retail |
| **Risk** | Mediocre everywhere | Toxic large flow | Miss whale volume |
| **Best against** | Niche specialists | Flat or retail-focused | Flat or whale-focused |

---

## Troubleshooting

### "My strategy always loses"
- **Check:** Are your tiers too extreme? (e.g., 50bps base fee)
- **Check:** Are you testing against very different flow patterns?
- **Action:** Start with baseline tiers (30-20-10), adjust incrementally

### "Routing seems slow"
- **Check:** Are your tiers reasonable? (Not 100+ tiers, not 0.0001bps gaps)
- **Note:** 5-10ms for 5-AMM tiered routing is normal and acceptable

### "I can't tell why I'm losing"
- **Use:** Match history analytics - filter by trade size category
- **Look for:** Are you losing on small trades? Large trades? Both?
- **Adjust:** Tiers to target the flow you're competitive in

### "Platform won't accept my strategy"
- **Check:** Does it compile? (Solidity 0.8.24)
- **Check:** Does it inherit `AMMStrategyBase`?
- **Check:** Does it implement all required functions?
- **Action:** Review example strategies in `contracts/src/examples/`

---

## Realism Score: What We Model

### ✅ What We Model (85% realistic)
- Head-to-head competition between strategies
- Volume-based tiered pricing (up to 3 tiers)
- Multi-venue routing (up to 5 AMMs)
- Constant product market making (xy=k)
- Retail flow and arbitrageur dynamics
- Public performance transparency

### ⚠️ What We Simplify
- Fixed simulation parameters (not dynamic conditions)
- No MEV or sandwich attacks
- Simplified price process (GBM not real orderbook)
- No gas costs (focus on economic strategy)
- Limited to 5 AMMs (real aggregators use 10+)

---

## Next Steps

1. **Review the slide deck** for detailed rationale
2. **Explore the platform** and leaderboard
3. **Implement your first tiered strategy** using the template
4. **Test against 5-10 opponents** and analyze results
5. **Iterate and climb the leaderboard** - target 60%+ win rate
6. **Share learnings** in Slack `#amm-challenge`

---

## Remember

> "The modified competition is harder, more realistic, and more valuable. It's designed to make you a better market maker, not just complete an assignment."

**Key Insight:** This is game theory now, not just optimization. How you compete matters as much as how well you compete.

---

**End of Quick Reference - Print this as a 2-page handout for easy reference during development**

**Version 2.0 | Modified PVP AMM Competition | 2025-02-10**
