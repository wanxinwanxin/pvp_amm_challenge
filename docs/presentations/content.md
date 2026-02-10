# PVP AMM Competition Presentation: Complete Slide Content

**Target Audience:** Technical AMM developers
**Duration:** 25-30 minutes + Q&A
**Format:** 20 slides across 6 sections

---

## SECTION 1: OPENING

### Slide 1: Title Slide

**Title:** Understanding the Modified PVP AMM Competition: From Baseline to Battle Royale

**Subtitle:** Why the New Game Mechanics Make Sense

**Footer:** Internal Technical Briefing | 2026

**Visual Note:** Clean title design with AMM iconography (liquidity pools, routing arrows)

---

### Slide 2: The Evolution Story

**Title:** From Solo Challenge to Head-to-Head Competition

**Content - Two Column Comparison:**

**Original (2024):**
- 🎯 Beat a baseline normalizer (30bps)
- 📊 Score: Total edge over baseline
- ⚙️ Single strategy submission
- 🔢 99 simulation gauntlet
- 💻 CLI tool only

**Modified (2025-2026):**
- ⚔️ Beat another strategy directly
- 🏆 Score: Win/loss/draw record
- 👥 Head-to-head matches
- 🎮 50+ simulation matches
- 🌐 Full web platform + leaderboard

**Key Message:** "We've moved from an academic exercise to a competitive arena"

**Visual Note:** Timeline arrow from left (2024) to right (2026) with icons

---

### Slide 3: Agenda

**Title:** What We'll Cover

**Content:**

1. **The Original System** - What you need to remember (3 min)
2. **What Changed** - The five major modifications (8 min)
3. **Why It's Better** - The business and technical case (6 min)
4. **Strategic Implications** - How to win now (5 min)
5. **Q&A** - Your questions (flexible)

**Estimated Total Time:** 25-30 minutes

**Visual Note:** Clean numbered list with time estimates per section

---

## SECTION 2: THE ORIGINAL SYSTEM

### Slide 4: Original Competition Mechanics

**Title:** The Original Challenge: Beat the Baseline

**Content:**

**Competition Structure:**
```
Single Strategy vs Baseline Normalizer (30bps constant fee)
├─ 99 independent simulations
├─ Score: sum(your_edge - baseline_edge) across all sims
└─ Winner: Highest cumulative edge over baseline
```

**Key Characteristics:**
- **Objective:** Maximize total edge above baseline across 99 runs
- **Fee Model:** Constant fees only (e.g., 30bps buy, 30bps sell)
- **Routing:** 2-AMM analytical optimal split (closed-form solution)
- **Scoring:** Cumulative profit differential
- **Interface:** CLI tool (`python run_competition.py`)

**The Baseline:** Fixed 30bps fee, deterministic behavior, easy to beat with adaptive strategies

**Visual Note:** Flowchart showing single strategy vs baseline, formula for score calculation

---

### Slide 5: Original System Limitations

**Title:** What Was Missing: The Realism Gap

**Content:**

**Gaps Between Simulation and Reality:**

| Real Markets | Original Challenge | Impact |
|--------------|-------------------|---------|
| Multiple competing venues | Single opponent (baseline) | Unrealistic strategic landscape |
| Volume-based pricing tiers | Constant fees only | Can't model real fee schedules |
| N-way routing (aggregators) | 2-AMM max | Oversimplified execution |
| Head-to-head competition | Beat fixed benchmark | No adversarial dynamics |
| Public performance tracking | Local CLI results | No accountability/visibility |

**The Core Problem:**
> "You were optimizing against a fixed target, not adapting to real competition. It's like training to beat a chess computer at one difficulty level instead of playing against other humans."

**Visual Note:** Table with red X marks highlighting gaps, quote box for core problem

---

## SECTION 3: WHAT CHANGED

### Slide 6: The Five Major Changes

**Title:** What Changed: Five Key Modifications

**Content:**

**1. Head-to-Head Matches** ⚔️
Old: You vs Baseline | New: Strategy A vs Strategy B

**2. Win/Loss Scoring** 🏆
Old: Total edge differential | New: Win count across simulations

**3. Tiered Fee Structures** 📊
Old: Constant fees | New: Up to 3 tiers per direction with volume discounts

**4. N-Way Routing (N≤5)** 🔀
Old: 2-AMM analytical | New: 5-AMM iterative (2-3 iterations)

**5. Full Web Platform** 🌐
Old: CLI tool | New: Streamlit app with leaderboard, match history, analytics

**Visual Note:** 5 boxes in grid layout with icons and before/after comparisons

---

### Slide 7: Change #1 - Head-to-Head Competition

**Title:** Change #1: True Adversarial Dynamics

**Content:**

**Before:**
```python
# Your strategy vs fixed baseline
def score():
    your_edge = run_simulation(your_strategy)
    baseline_edge = run_simulation(baseline_normalizer)
    return your_edge - baseline_edge  # Beat by X amount
```

**After:**
```python
# Your strategy vs opponent's strategy
def match_winner():
    wins_a = wins_b = draws = 0
    for sim in range(50):
        edge_a = run_sim(strategy_a)
        edge_b = run_sim(strategy_b)
        if edge_a > edge_b: wins_a += 1
        elif edge_b > edge_a: wins_b += 1
        else: draws += 1
    return "A wins" if wins_a > wins_b else "B wins"
```

**Why This Matters:**
- ✅ **Adaptive Strategy Needed:** Your opponent isn't static - they optimize too
- ✅ **Zero-Sum Dynamics:** Retail flow splits between you - if you win, they lose
- ✅ **Meta Game:** Strategies evolve based on what others are doing
- ✅ **Win Consistency:** You need to win more often, not just by more total

**Real-World Analog:** "Like Uniswap vs Sushiswap competing for the same retail order flow"

**Visual Note:** Side-by-side code with syntax highlighting, diagram showing double arrows (A ↔ B)

---

### Slide 8: Changes #2-3 - Scoring & Tiered Fees

**Title:** Changes #2-3: Wins Matter + Volume Discounts

**Content:**

**Change #2: Win/Loss Scoring**

| Metric | Original | Modified |
|--------|----------|----------|
| **Primary Score** | Cumulative edge over baseline | Win count |
| **Tiebreaker** | N/A | Average edge |
| **Objective** | Maximize total profit | Win more simulations |
| **Strategy Implication** | Optimize expected value | Optimize consistency |

**Example:** Strategy A wins 30/50 sims by +10 edge each, loses 20/50 by -5 edge each. Total edge = 200. Strategy B wins 26/50 sims by +5 edge each, loses 24/50 by -3 edge each. Total edge = 58. **Winner: A** (more wins).

**Change #3: Tiered Fee Structures**

```solidity
// Old: Constant fees
function afterSwap(TradeInfo calldata) external returns (uint256, uint256) {
    return (bpsToWad(30), bpsToWad(30));  // Always 30bps
}

// New: Tiered fees with volume discounts
function getFeeStructure(TradeInfo calldata) external view returns (FeeStructure memory) {
    FeeTier memory tier1 = createTier(0, 30);      // 0-100 X: 30bps
    FeeTier memory tier2 = createTier(100, 20);    // 100-1000 X: 20bps
    FeeTier memory tier3 = createTier(1000, 10);   // 1000+ X: 10bps
    return createSymmetricFeeStructure(tier1, tier2, tier3);
}
```

**Why This Matters:**
- **More realistic:** Real venues (Uniswap v3, dYdX) have volume-based pricing
- **Strategic depth:** You can optimize fee schedules, not just levels
- **Compete on structure:** Attract whales with discounts, protect against small toxic flow

**Visual Note:** Table for scoring comparison, code snippets side-by-side, fee tier diagram (30→20→10 bps curve)

---

### Slide 9: Change #4 - N-Way Routing

**Title:** Change #4: Multi-Venue Routing (N≤5)

**Content:**

**Before: 2-AMM Analytical Solution**
```python
# Fast analytical formula (closed form)
def split_two_amms(amm1, amm2, total_y):
    A1 = sqrt(x1 * gamma1 * y1)
    A2 = sqrt(x2 * gamma2 * y2)
    r = A1 / A2
    y1 = (r * (y2 + gamma2 * Y) - y1) / (gamma1 + r * gamma2)
    y2 = total_y - y1
    return [(amm1, y1), (amm2, y2)]
```
✅ Instant computation
❌ Only works for 2 AMMs with constant fees

**After: N-Way Iterative Routing**
```python
# Iterative refinement (2-3 iterations typical)
def split_n_amms(amms, total_y, max_iter=5):
    splits = initial_split(amms, total_y)  # Use constant fees
    for iteration in range(max_iter):
        # Compute effective fees at current split sizes
        effective_fees = [amm.effective_fee(split_amount)
                         for amm, split_amount in splits]
        # Recompute split with effective fees
        new_splits = pairwise_split(amms, total_y, effective_fees)
        # Check convergence
        if max_change(splits, new_splits) < 0.001:
            return new_splits  # Converged!
        splits = new_splits
    return splits  # Max iterations reached
```
✅ Handles tiered fees correctly
✅ Supports up to 5 strategies
✅ Converges in 2-3 iterations (< 10ms)
✅ Near-optimal (within 0.1% of true optimal)

**Why This Matters:**
- **Realistic aggregation:** 1inch, Matcha route across 5+ venues
- **Tiered fees work:** Iterative method handles size-dependent pricing
- **Still fast:** Sub-10ms for 5-way split with tiered fees
- **Backward compatible:** Constant fees hit fast path (no iterations)

**Visual Note:** Side-by-side code with annotations, convergence diagram showing 2-3 iterations → stable split

---

### Slide 10: Change #5 - Web Platform

**Title:** Change #5: From CLI Tool to Full Platform

**Content:**

**Before: Local CLI**
```bash
$ python run_competition.py --strategy my_strategy.sol
Running 99 simulations...
[========================================] 100%
Your edge: 245.7 bps
Baseline edge: 187.3 bps
Advantage: +58.4 bps
```
- No persistence
- No comparison across runs
- No visibility to others
- Hard to analyze patterns

**After: Web Platform**

**Features:**
1. **Strategy Submission** - Upload Solidity, compile, validate, store
2. **Leaderboard** - Sort by wins, win rate, avg edge, total matches
3. **Match Creation** - Select 2 strategies, run 50 simulations, view results
4. **Match History** - Full audit trail with charts and statistics
5. **Head-to-Head Stats** - A vs B record, average outcomes
6. **Analytics** - Performance over time, fee tier analysis

**Tech Stack:**
- Frontend: Streamlit (Python web framework)
- Backend: SQLite database with full match persistence
- Charts: Plotly (interactive visualizations)
- Deployment: Railway + Docker

**Why This Matters:**
- 🔍 **Transparency:** Everyone sees everyone's performance
- 📊 **Analytics:** Understand what works and why
- 🏆 **Accountability:** Your record is public
- 🔄 **Iteration:** Easy to test and refine strategies
- 🎮 **Engagement:** Feels like a real competition, not a homework assignment

**Visual Note:** CLI screenshot (minimal), web platform mockup showing leaderboard, feature list with icons

---

## SECTION 4: WHY IT'S BETTER

### Slide 11: Business Case - Realism

**Title:** Why It's Better #1: Real-World Realism

**Content:**

**The Realism Test:** How well does this simulate actual market making?

| Dimension | Original | Modified | Real Markets |
|-----------|----------|----------|-------------|
| **Competition Type** | You vs benchmark | You vs competitors | Multi-venue competition |
| **Fee Structures** | Constant only | Tiered (3 levels) | Tiered & dynamic |
| **Routing** | 2-venue max | 5-venue routing | 5-10+ venues |
| **Scoring** | Total profit | Win consistency | Market share + profitability |
| **Visibility** | Private CLI | Public leaderboard | On-chain transparency |

**Realism Score:**
Original: ⭐⭐☆☆☆ (40%)
Modified: ⭐⭐⭐⭐☆ (85%)

**What We Model Better Now:**
1. **Competitive dynamics:** Other venues optimize against you
2. **Pricing sophistication:** Volume discounts to attract large orders
3. **Aggregator routing:** 1inch/Matcha split across multiple venues
4. **Market transparency:** Everyone sees everyone's performance
5. **Win consistency:** Market share matters, not just total profit

**What's Still Simplified:**
- Fixed simulation parameters (not dynamic market conditions)
- No MEV or sandwich attacks
- Simplified price process (GBM instead of real orderbook dynamics)

**Visual Note:** Table with color coding (red = poor, yellow = medium, green = good), star ratings

---

### Slide 12: Business Case - Strategic Depth

**Title:** Why It's Better #2: Richer Strategy Space

**Content:**

**Strategy Dimensions:** What can you optimize?

**Original System:**
1. ✅ Fee level (single constant)
2. ✅ Fee timing (when to adjust)
3. ⚠️ Predict retail flow (limited impact)

**3 dimensions → Limited differentiation**

**Modified System:**
1. ✅ Fee level (still important)
2. ✅ Fee timing (when to adjust)
3. ✅ **Fee structure** (tier thresholds, tier spreads)
4. ✅ **Volume targeting** (optimize for small/large trades)
5. ✅ **Opponent modeling** (adapt to their fee structure)
6. ✅ **Win probability** (optimize for consistency, not just EV)
7. ✅ **Meta game** (respond to leaderboard strategies)

**7 dimensions → Rich strategic landscape**

**Example Strategy Types:**

**"Whale Hunter"**
```
Tier 1: 40bps (0-100 X)      ← High fee for small trades
Tier 2: 15bps (100-1000 X)   ← Discount for medium
Tier 3: 5bps (1000+ X)       ← Deep discount for whales
Strategy: Sacrifice small retail, capture large institutional flow
```

**"Retail Specialist"**
```
Tier 1: 20bps (0-500 X)      ← Competitive for small trades
Tier 2: 25bps (500-2000 X)   ← Increase for medium
Tier 3: 35bps (2000+ X)      ← Price out large trades
Strategy: Win many small trades, avoid toxic large flow
```

**"Adaptive Defender"**
```python
def afterSwap(trade):
    if recent_arb_loss > threshold:
        return increase_all_fees(10bps)  # Protect against arb
    elif opponent_lowered_fees:
        return match_their_structure()    # Stay competitive
    else:
        return baseline_tiers()
```

**Visual Note:** Dimension comparison (3 vs 7), fee structure charts for each strategy type

---

### Slide 13: Business Case - Developer Value

**Title:** Why It's Better #3: More Valuable Experience

**Content:**

**What You Learn From Each System:**

**Original System:**
- ✅ CFMM math (constant product formula)
- ✅ Fee impact on execution quality
- ✅ Basic strategy logic (if/then rules)
- ❌ Competitive adaptation
- ❌ Sophisticated pricing models
- ❌ Multi-venue routing algorithms

**Skills gained:** AMM basics, Solidity fundamentals

**Modified System:**
- ✅ CFMM math (constant product formula)
- ✅ Fee impact on execution quality
- ✅ Basic strategy logic (if/then rules)
- ✅ **Adversarial strategy design** (game theory)
- ✅ **Tiered pricing optimization** (price discrimination)
- ✅ **Multi-venue routing** (aggregator algorithms)
- ✅ **Iterative optimization** (convergence algorithms)
- ✅ **Data-driven strategy tuning** (leaderboard analytics)

**Skills gained:** Production-ready market making + competitive strategy

**Resume Line:**
- Old: "Implemented AMM fee strategy that beat baseline by 58bps"
- New: "Designed tiered fee AMM strategy with 68% win rate in head-to-head competition, optimized for 5-way routing with iterative convergence"

**Career Relevance:**

| Role | Original Prep | Modified Prep |
|------|--------------|--------------|
| **Market Maker @ TradFi** | ⭐☆☆ Basic | ⭐⭐⭐ Strong |
| **AMM Designer @ DeFi Protocol** | ⭐⭐☆ Good | ⭐⭐⭐ Excellent |
| **Aggregator Engineer @ 1inch/Matcha** | ⭐☆☆ Minimal | ⭐⭐⭐ Highly relevant |
| **Quant Researcher** | ⭐⭐☆ Good | ⭐⭐⭐ Excellent |

**Visual Note:** Two skill trees (before/after), resume comparison, career relevance table

---

### Slide 14: Technical Case - Correctness

**Title:** Why It's Better #4: Rigorously Tested

**Content:**

**Testing Investment:** We didn't just modify the system - we proved it works

**150+ Economic Correctness Tests** across 8 categories:

1. **Backward Compatibility (25 tests)**
   - Constant-fee strategies behave identically to old system
   - Acceptance: < 0.01% difference in splits, prices, reserves

2. **Symmetry & Fairness (15 tests)**
   - Identical strategies produce symmetric PnL
   - Acceptance: < 5% PnL difference

3. **Determinism (17 tests)**
   - Fixed seeds → identical results
   - Acceptance: Bit-exact reproduction

4. **No Arbitrage (23 tests)**
   - Buy-then-sell loses exactly fees paid
   - Acceptance: Loss = fees ± 0.1%

5. **Optimal Routing (24 tests)**
   - Split beats any single AMM
   - Acceptance: Split > single + 0.01%, converges ≤ 5 iterations

6. **Accounting Correctness (22 tests)**
   - Value conservation (sum PnLs = 0)
   - Acceptance: ± 0.01%

7. **Convergence Stability (36 tests)**
   - Iterative routing always converges
   - Acceptance: 95% converge in ≤ 3 iterations, 100% in ≤ 5

8. **Edge Cases (14 tests)**
   - Extreme trade sizes, pool imbalances, pathological fees
   - Acceptance: No crashes, valid results

**CI/CD:**
- ✅ All tests run on every commit
- ✅ Python 3.10, 3.11, 3.12
- ✅ Coverage > 90% for core modules
- ✅ Full test suite < 5 minutes

**What This Means:**
> "The modified system is not experimental - it's production-grade with better test coverage than most DeFi protocols."

**Visual Note:** Test pyramid showing 150+ tests, 8 categories with counts, CI/CD badge icons

---

## SECTION 5: STRATEGIC IMPLICATIONS

### Slide 15: How to Win Now - Core Principles

**Title:** Strategic Implications: How to Win the New Game

**Content:**

**The Old Playbook (Doesn't Work Anymore):**
- ❌ Static optimal fee (e.g., "27bps is best")
- ❌ Just beat baseline by any amount
- ❌ Optimize for total edge only
- ❌ Ignore opponent's behavior

**The New Playbook:**

**1. Optimize for Win Probability, Not Just EV**
```
Old thinking: "I need +500 total edge across 99 sims"
New thinking: "I need to win 26+ out of 50 simulations"

Strategy implication: Consistency > variance
- Prefer strategies that win often by a little
- Avoid high-variance strategies (win big or lose big)
```

**2. Design Fee Structures, Not Just Levels**
```
Old: Set bid_fee=30bps, ask_fee=30bps, done
New: Design a tier structure that targets your niche

Questions to answer:
- Who are your target traders? (retail vs institutional)
- What trade sizes do you want? (small frequent vs large rare)
- How do you price out toxic flow? (arb protection)
```

**3. Adapt to Your Opponent**
```
Old: Optimize against fixed baseline
New: Study opponent's fee structure and adapt

If opponent has:
- Aggressive low fees → Find a niche they're weak in
- Flat structure → Exploit with targeted tiers
- Specific tier thresholds → Arbitrage the gaps
```

**4. Use the Data**
```
Old: No feedback except final score
New: Leaderboard shows:
- Win rates against specific opponents
- Average edge per match
- Head-to-head records

Action: Test strategies, analyze match history, iterate
```

**Visual Note:** Old playbook crossed out, 4 principles in boxes with examples

---

### Slide 16: Tactical Approaches

**Title:** Tactical Approaches: Three Winning Strategies

**Content:**

**Strategy Archetype 1: "Volume Discounter"**
```solidity
// Attract large trades with steep discounts
FeeTier tier1 = createTier(0, 35);      // 0-50: 35bps (high base)
FeeTier tier2 = createTier(50, 20);     // 50-500: 20bps (standard)
FeeTier tier3 = createTier(500, 8);     // 500+: 8bps (aggressive)

// Win condition: Capture 60%+ of large orders (> 500X)
// Risk: Vulnerable to toxic large flow
```
**When to use:** Opponent has flat fee structure, many large trades in simulations

**Strategy Archetype 2: "Retail Specialist"**
```solidity
// Dominate small/medium trades, price out large
FeeTier tier1 = createTier(0, 25);      // 0-100: 25bps (competitive)
FeeTier tier2 = createTier(100, 28);    // 100-500: 28bps (slight increase)
FeeTier tier3 = createTier(500, 40);    // 500+: 40bps (expensive)

// Win condition: Win 70%+ of small/medium orders
// Risk: Lose market share if large trades dominate
```
**When to use:** Opponent is whale-focused, retail flow is frequent

**Strategy Archetype 3: "Adaptive Defender"**
```python
def afterSwap(trade):
    # Track recent performance
    recent_pnl = calculate_recent_pnl(window=10)
    price_volatility = calculate_volatility(window=20)

    # Adjust fees based on conditions
    if recent_pnl < -50:  # Losing to arb
        return widen_spreads(5bps)
    elif price_volatility > 0.02:  # High volatility
        return increase_base_fee(3bps)
    elif recent_win_rate > 0.7:  # Dominating
        return slightly_lower_fees(2bps)  # Capture more volume
    else:
        return baseline_fees()
```
**When to use:** Against dynamic opponents, volatile markets

**Choosing Your Approach:**
1. Analyze opponent's historical fee structures (leaderboard)
2. Identify their weakness (over-optimized for specific flow type?)
3. Design counter-strategy targeting their blind spots
4. Test in matches, iterate based on results

**Visual Note:** 3 strategy boxes with code snippets, fee tier graphs showing structures

---

### Slide 17: Common Pitfalls to Avoid

**Title:** Common Pitfalls: What Not to Do

**Content:**

**❌ Pitfall #1: Optimizing for Expected Value Only**
```
Bad: "My strategy wins by +200 edge on average!"
Reality: Wins 15/50 sims (big wins), loses 35/50 (small losses)
Result: 30% win rate → You lose the match

Fix: Target consistency. Win 26+ simulations, even by small margins.
```

**❌ Pitfall #2: Ignoring Tiered Fee Complexity**
```
Bad: "Tier 1: 30bps, Tier 2: 29bps, Tier 3: 28bps"
Problem: Tiers barely different → no strategic advantage
Result: Acts like constant fee, but slower routing

Fix: Make tiers meaningful (5-10bps gaps). Target specific niches.
```

**❌ Pitfall #3: Static Fee Structures**
```
Bad: Set fees once in afterInitialize(), never adjust
Problem: Market conditions change (volatility spikes, arb attacks)
Result: Get exploited in adverse conditions

Fix: Use afterSwap() callback to adapt. Monitor your PnL.
```

**❌ Pitfall #4: Racing to the Bottom on Fees**
```
Bad: "I'll just set 5bps everywhere and win on price!"
Problem: Attract toxic flow (arb bots), lose money to adverse selection
Result: Win volume, lose profitability → lower edge → lose match

Fix: Use tiers to attract good flow, price out bad flow.
```

**❌ Pitfall #5: Not Using Match History**
```
Bad: Submit strategy, run one match, assume it's optimal
Problem: Sample size too small, didn't test against diverse opponents
Result: Overfitted to one opponent

Fix: Test against 5-10 different strategies, analyze patterns.
```

**Key Principle:**
> "In the modified system, *how* you compete matters as much as *how well* you compete. Strategy design is now a core skill."

**Visual Note:** 5 pitfall boxes with X marks, example metrics, quote box for key principle

---

## SECTION 6: CONCLUSION

### Slide 18: Summary - Key Takeaways

**Title:** Key Takeaways: The Essential Points

**Content:**

**1. The Competition Changed Fundamentally**
- From solo benchmark-beating → head-to-head competition
- From constant fees → tiered fee structures
- From 2-AMM routing → 5-AMM routing
- From CLI tool → full web platform

**2. The Changes Make It More Realistic**
- Models actual multi-venue competition (85% realism vs 40%)
- Enables sophisticated pricing strategies (7 dimensions vs 3)
- Tests skills you'll actually use in production

**3. Winning Requires New Strategies**
- Optimize for win consistency, not just total edge
- Design fee structures, not just levels
- Adapt to opponents using match history
- Balance volume attraction with profitability

**4. The System is Rigorously Tested**
- 150+ economic correctness tests
- Backward compatible with original system
- Production-grade quality (> 90% coverage)

**5. This is an Investment in Your Skills**
- More valuable experience for career growth
- Deeper understanding of market microstructure
- Hands-on with production-relevant algorithms

**Bottom Line:**
> "The modified competition is harder, more realistic, and more valuable. It's designed to make you a better market maker, not just complete an assignment."

**Visual Note:** 5 numbered boxes with icons, prominent bottom-line quote

---

### Slide 19: Your Call to Action

**Title:** What You Should Do Next

**Content:**

**Immediate Actions (This Week):**

1. **📚 Review the docs**
   - `README.md` - System overview
   - `tests/README.md` - Economic properties tested
   - `20250210-complete-tiered-fee-routing.md` - Technical implementation

2. **🔍 Explore the platform**
   - Browse existing strategies on leaderboard
   - Study head-to-head match results
   - Analyze winning fee structures

3. **🧪 Test a simple strategy**
   - Start with constant fees (familiar territory)
   - Run 3-5 matches against different opponents
   - Review match history and identify patterns

**Short-Term Goals (Next 2 Weeks):**

4. **📊 Design a tiered fee structure**
   - Choose an archetype (Discounter, Specialist, Adaptive)
   - Implement in Solidity using `getFeeStructure()`
   - Test against leaderboard top 5

5. **🎯 Iterate based on data**
   - Analyze why you win/lose specific matches
   - Adjust tier thresholds and fee levels
   - Test counter-strategies against your weaknesses

**Long-Term Vision (Ongoing):**

6. **🏆 Climb the leaderboard**
   - Aim for 60%+ overall win rate
   - Study opponent patterns, adapt strategies
   - Share learnings with the team

7. **💡 Innovate**
   - Try unconventional fee structures
   - Combine static tiers + dynamic adjustment
   - Find unexploited niches

**Resources:**
- Platform: [Streamlit app URL]
- Docs: `pvp_amm_challenge/` repo
- Support: #amm-challenge Slack channel

**Visual Note:** Timeline showing immediate → short-term → long-term, checklist format

---

### Slide 20: Q&A + Discussion

**Title:** Questions & Discussion

**Content:**

**Common Questions Anticipated:**

**Q: "Will this replace the original competition completely?"**
A: No - the original system remains available for backward compatibility testing. Think of this as "Challenge 2.0" - a parallel track.

**Q: "Do I have to use tiered fees?"**
A: No - constant fees still work and use the fast analytical routing path. But tiered fees unlock strategic advantages.

**Q: "How do I know my strategy is good?"**
A: Run 10+ matches against diverse opponents. Target 60%+ win rate. Use match history analytics.

**Q: "What if iterative routing doesn't converge?"**
A: Handled gracefully - max 5 iterations, then uses last result. 95% of realistic structures converge in 2-3 iterations.

**Q: "Can I see my opponent's strategy code?"**
A: Platform shows fee structures and match results, not source code. Learn by observing behavior.

**Q: "What about gas costs?"**
A: Not modeled in simulation - focus on economic strategy. Real deployments would need gas optimization.

**Open Discussion:**
- What strategies are you thinking about?
- What additional features would help you?
- Any concerns about the new system?

**Contact:**
- Technical questions: [Lead engineer email]
- Strategy discussion: #amm-challenge Slack
- Bug reports: GitHub issues

**Visual Note:** Q&A format with clean typography, contact information box

---

## PRESENTATION NOTES

### Timing Guide
- Section 1 (Opening): 3 minutes
- Section 2 (Original): 3 minutes
- Section 3 (Changes): 8 minutes
- Section 4 (Why Better): 6 minutes
- Section 5 (Strategy): 5 minutes
- Section 6 (Conclusion): 2 minutes
- Q&A: 5-10 minutes flexible

### Delivery Tips
1. Use progressive disclosure for busy slides
2. Consider live demo of web platform (Slide 10, 19)
3. Walk through code examples slowly (Slides 7-9)
4. Emphasize enthusiasm - this is genuinely more interesting
5. Have backup slides ready for technical deep-dives

### Key Messages by Section
- Opening: Generate excitement about the evolution
- Original: Set context without criticism
- Changes: Educate on technical details
- Why Better: Build conviction with evidence
- Strategy: Empower with practical guidance
- Conclusion: Motivate action

---

**End of Slide Content Document**
