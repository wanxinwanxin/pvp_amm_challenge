# Presenter Notes: PVP AMM Competition Explainer

**Generated:** 2025-02-10
**Duration:** 25-30 minutes + Q&A
**Audience:** Technical AMM developers on the team
**Tone:** Professional but enthusiastic, educational not defensive

---

## Pre-Presentation Checklist

- [ ] Test all demo links/platform access
- [ ] Load slide deck on presentation computer
- [ ] Test code syntax highlighting visibility
- [ ] Have backup slides ready (algorithm details, test breakdowns)
- [ ] Confirm room setup (projector, remote, water)
- [ ] Print quick reference handout (1 per person)

---

## SECTION 1: OPENING (3 minutes total)

### Slide 1: Title Slide (30 seconds)

**What to Say:**
"Good [morning/afternoon], everyone. Today I want to walk you through the modified PVP AMM competition - what changed, why it changed, and most importantly, what it means for how you approach strategy design going forward."

**Tone:** Professional, set expectations
**Body Language:** Make eye contact, smile
**Transition:** "This isn't just a technical update - it's a fundamental shift in how the competition works."

---

### Slide 2: Evolution Story (1 minute)

**What to Say:**
"Let's start with the big picture. The original competition from 2024 had you competing against a fixed baseline - think of it as beating a benchmark. The modified version is fundamentally different: you're now competing head-to-head against other strategies in a true competitive arena."

**Key Points to Emphasize:**
- "Notice the shift from solo challenge to multiplayer competition"
- "From CLI tool to full web platform with visibility"
- "From 99 sims to 50, but each one matters more"

**What to Show:**
- Point to timeline arrow showing progression
- Highlight icons as you mention each change

**Common Question:** "Why fewer simulations (50 vs 99)?"
**Answer:** "Win consistency matters more than sample size. 50 is statistically sufficient to determine a winner while being faster to run."

**Transition:** "Let me show you what we'll cover today..."

---

### Slide 3: Agenda (1.5 minutes)

**What to Say:**
"We'll cover five sections in about 25 minutes, leaving time for your questions. First, a quick refresher on the original system - what you need to remember. Second, the five major changes we made. Third, why these changes make sense both technically and from a business perspective. Fourth, strategic implications - how to actually win now. And finally, concrete next steps for you."

**Key Points to Emphasize:**
- "We'll spend most time on sections 3 and 4 - the 'what changed' and 'why better'"
- "I'll keep section 2 brief since most of you know the original"
- "Save technical deep-dives for Q&A"

**Body Language:** Use hand gestures to count off sections
**Transition:** "Let's start with a quick reminder of what we had..."

---

## SECTION 2: ORIGINAL SYSTEM (3 minutes total)

### Slide 4: Original Mechanics (1.5 minutes)

**What to Say:**
"The original competition was straightforward: your strategy competed against a baseline normalizer with a constant 30 basis point fee. You ran 99 independent simulations, and your score was the sum of how much better you did than the baseline across all runs."

**Key Points to Emphasize:**
- "Constant fees only - single number like 30bps"
- "2-AMM routing with a closed-form analytical solution"
- "Cumulative scoring - total edge mattered"

**What NOT to Say:**
- Don't criticize the original design ("it was bad")
- Don't imply it was a mistake
- Frame as "good foundation, but limited"

**Tone:** Neutral, factual, respectful
**Transition:** "This served us well for learning AMM basics, but there were gaps..."

---

### Slide 5: Original Limitations (1.5 minutes)

**What to Say:**
"The challenge with the original system wasn't that it was wrong - it was that it didn't reflect real-world market making dynamics. Real markets have multiple competing venues, volume-based pricing, N-way routing, and head-to-head competition. The original system simplified all of these away."

**Key Points to Emphasize:**
- Point to each row in the table
- "This isn't criticism - it's evolution"
- Read the quote slowly for emphasis

**Quote to Emphasize:**
"You were optimizing against a fixed target, not adapting to real competition. It's like training to beat a chess computer at one difficulty level instead of playing against other humans."

**Pause after quote** - let it sink in

**Common Question:** "Wasn't the original still useful?"
**Answer:** "Absolutely! It taught AMM fundamentals. But to take you to production-ready market making, we needed more realism."

**Transition:** "So what did we change? Five major things..."

---

## SECTION 3: WHAT CHANGED (8 minutes total)

### Slide 6: The Five Changes Overview (1 minute)

**What to Say:**
"We made five key modifications. Let me preview them all, then we'll dive into each one. Head-to-head matches replace the baseline. Win/loss scoring replaces cumulative edge. Tiered fee structures replace constant fees. N-way routing replaces 2-AMM limits. And a full web platform replaces the CLI tool."

**What to Show:**
- Use progressive reveal if live presenting (1 box per 2 seconds)
- Point to each icon as you mention it

**Tone:** Energetic, building anticipation
**Transition:** "Let's start with the biggest change - head-to-head competition..."

---

### Slide 7: Head-to-Head Competition (1.5 minutes)

**What to Say:**
"Instead of competing against a fixed baseline, you now compete directly against another strategy. Look at these code examples - before, you just had to beat a constant 30bps fee. Now, you're in a zero-sum game where retail flow splits between you and your opponent."

**Key Points to Emphasize:**
- Point to the code difference
- "This is zero-sum - if you win, they lose"
- "Creates a meta game - strategies evolve"
- Use the Uniswap vs Sushiswap analogy

**What to Show:**
- Highlight the for loop in the "After" code
- Point to the win counting logic

**Common Question:** "Is it always 50 simulations?"
**Answer:** "Yes, 50 is our standard. Statistically sufficient to differentiate strategies while being fast."

**Transition:** "This changes how we score winners..."

---

### Slide 8: Scoring & Tiered Fees (2 minutes)

**What to Say:**
"Two changes here. First, we score by win count, not cumulative edge. You need to win more simulations, not just have higher total profit. Second, we support tiered fee structures - up to 3 tiers per direction with volume discounts."

**Key Points to Emphasize:**
- Walk through the example: Strategy A has higher total edge but loses
- "Consistency matters more than variance"
- Show the Solidity code transition - simple to tiered

**What to Show:**
- Point to the table showing Strategy A vs B
- Trace through the fee tier code
- Show the fee diagram (30→20→10)

**Technical Note:**
If audience is very technical, mention: "The weighted average is computed for router optimization - we'll see how that works in the next slide."

**Transition:** "But how do we route orders across multiple AMMs with tiered fees? That requires a new algorithm..."

---

### Slide 9: N-Way Routing (2 minutes)

**What to Say:**
"This is the most technical change. The original 2-AMM routing used a closed-form analytical solution - instant but limited to constant fees. The new system uses iterative refinement to handle tiered fees and up to 5 AMMs."

**Key Points to Emphasize:**
- "Still fast - converges in 2-3 iterations, under 10ms"
- "Backward compatible - constant fees hit the fast path"
- "Near-optimal - within 0.1% of true optimal"

**What to Show:**
- Point to the iteration loop in the code
- Show the convergence flowchart
- Emphasize the max_iterations = 5 limit

**Common Question:** "What if it doesn't converge?"
**Answer:** "Gracefully handled - max 5 iterations, then returns best result. In practice, 95% converge in 3 or fewer."

**Technical Deep-Dive (if asked):**
"Happy to walk through the math in Q&A. The key insight is we estimate effective fees at current split sizes, recompute the split, and repeat until the split stabilizes."

**Transition:** "Finally, we built a full platform around this..."

---

### Slide 10: Web Platform (1.5 minutes)

**What to Say:**
"The CLI tool worked, but it gave you no visibility, no persistence, and no way to learn from others. The new web platform gives you a leaderboard, match history, analytics, and full transparency into everyone's performance."

**Key Points to Emphasize:**
- "This makes it feel like a real competition"
- "You can study opponents, iterate, and improve"
- "Full audit trail of every match"

**What to Show:**
- Point to the feature list
- If possible, do a 30-second live demo (have it pre-loaded)
- Show tech stack badges

**Optional Demo:**
"Let me quickly show you... [switch to browser, show leaderboard for 30 seconds, switch back]"

**Transition:** "So those are the five changes. Now let's talk about why they matter..."

---

## SECTION 4: WHY IT'S BETTER (6 minutes total)

### Slide 11: Realism (1.5 minutes)

**What to Say:**
"The first reason this is better: realism. Look at this comparison table. The original system modeled about 40% of real market making dynamics. The modified system gets us to 85%. That's not perfect - we still simplify some things - but it's a huge jump."

**Key Points to Emphasize:**
- Point to each row: competition, fee structures, routing, scoring, visibility
- "We're modeling what actually matters in production"
- "85% is the sweet spot - realistic without being overwhelming"

**What to Show:**
- Trace down the table row by row
- Emphasize the star ratings (visual impact)

**What We Still Simplify:**
"To be clear, we still simplify some things - no MEV, no dynamic market conditions. But we focus on what matters for strategy design."

**Transition:** "Realism is one thing, but there's also strategic depth..."

---

### Slide 12: Strategic Depth (2 minutes)

**What to Say:**
"The original system gave you 3 dimensions to optimize: fee level, timing, and retail flow prediction. The modified system gives you 7 dimensions, including fee structure design, volume targeting, opponent modeling, and meta-game strategy."

**Key Points to Emphasize:**
- "3 dimensions vs 7 dimensions - over 2x the strategy space"
- Walk through the three strategy archetypes
- "Each archetype targets a different niche"

**What to Show:**
- Point to the dimension lists (3 vs 7)
- Trace through each archetype's fee structure
- Highlight the differences in tier placement

**Archetypes:**
1. **Whale Hunter:** "Sacrifice small retail, capture institutional"
2. **Retail Specialist:** "Win many small trades, price out large"
3. **Adaptive Defender:** "Dynamically adjust to conditions"

**Engagement Question:**
"Which archetype sounds most interesting to you?" [Wait for responses, acknowledge]

**Transition:** "Beyond just being interesting, this is more valuable for your career..."

---

### Slide 13: Developer Value (1.5 minutes)

**What to Say:**
"Let's be practical: what do you learn from each system? The original taught AMM basics and Solidity fundamentals. The modified system teaches adversarial strategy design, tiered pricing optimization, multi-venue routing, iterative optimization, and data-driven tuning. These are production-ready skills."

**Key Points to Emphasize:**
- Read the resume line comparison - emphasize the difference
- Point to the career relevance table
- "This prepares you for real roles in DeFi and TradFi"

**What to Show:**
- Skill tree comparison (simple vs complex)
- Resume line side-by-side
- Career relevance star ratings

**Personal Touch:**
"When you interview for market maker or aggregator roles, this experience will directly translate."

**Transition:** "And finally, we didn't just modify it - we proved it works..."

---

### Slide 14: Rigorous Testing (1 minute)

**What to Say:**
"We invested heavily in testing. 150+ economic correctness tests across 8 categories. Backward compatibility with the old system. Over 90% code coverage. CI/CD on every commit. This isn't experimental - it's production-grade."

**Key Points to Emphasize:**
- "150+ tests is more than most DeFi protocols"
- "Backward compatible - constant fees work exactly as before"
- Read the quote slowly: "This is production-grade"

**What to Show:**
- Point to the test pyramid
- Highlight the CI/CD badges
- Emphasize the acceptance criteria for each category

**Tone:** Confident, reassuring
**Transition:** "So now that you understand what changed and why, let's talk strategy..."

---

## SECTION 5: STRATEGIC IMPLICATIONS (5 minutes total)

### Slide 15: Core Principles (2 minutes)

**What to Say:**
"The old playbook doesn't work anymore. You can't just find a static optimal fee. You can't ignore your opponent. You can't optimize for total edge only. Here's the new playbook."

**Key Points to Emphasize:**
- Cross out the old playbook visibly
- Walk through each of the 4 new principles
- "Consistency over variance - win often, not big"

**What to Show:**
- Point to each principle's code example
- Emphasize the shift in thinking

**Principles:**
1. **Win probability:** "26+ wins out of 50, not max total edge"
2. **Fee structures:** "Design tiers, don't just set levels"
3. **Adapt to opponent:** "Study their structure, exploit weaknesses"
4. **Use data:** "Leaderboard + match history = intelligence"

**Engagement:**
"This is game theory now, not just optimization."

**Transition:** "Let me give you three tactical approaches..."

---

### Slide 16: Tactical Approaches (2 minutes)

**What to Say:**
"Three winning archetypes. First, the Volume Discounter - attract large trades with steep discounts. Second, the Retail Specialist - dominate small trades, price out large. Third, the Adaptive Defender - dynamically adjust to conditions."

**Key Points to Emphasize:**
- Walk through each archetype's code
- "Choose based on your opponent's weakness"
- "No one-size-fits-all strategy"

**What to Show:**
- Point to fee structures in each code block
- Highlight the win conditions and risks
- Show the fee tier charts side-by-side

**Tactical Advice:**
"Start with one archetype, test it, analyze results, iterate. Don't try to be clever on day one."

**Transition:** "And avoid these common mistakes..."

---

### Slide 17: Common Pitfalls (1 minute)

**What to Say:**
"Five pitfalls to avoid. Don't optimize for expected value only - you'll lose on win count. Don't make meaningless tiers - make 5-10bps gaps. Don't use static fees - market conditions change. Don't race to the bottom - you'll attract toxic flow. And don't test once - test against 5-10 opponents."

**Key Points to Emphasize:**
- Read each pitfall title clearly
- Emphasize the fixes (green sections)
- Read the quote: "How you compete matters as much as how well"

**Tone:** Warning but helpful, not condescending
**What to Show:**
- Point to each pitfall box
- Highlight the fix sections

**Transition:** "Let's wrap up with key takeaways..."

---

## SECTION 6: CONCLUSION (2 minutes total)

### Slide 18: Key Takeaways (1 minute)

**What to Say:**
"Five key takeaways. One, the competition changed fundamentally - head-to-head, tiered fees, N-way routing, web platform. Two, the changes make it 85% realistic versus 40% before. Three, winning requires new strategies - consistency, structure design, opponent adaptation. Four, the system is rigorously tested with 150+ tests. Five, this is an investment in your skills - more valuable for your career."

**Key Points to Emphasize:**
- Point to each numbered box
- Pause between each takeaway
- Read the bottom line quote with emphasis

**Bottom Line Quote:**
"The modified competition is harder, more realistic, and more valuable. It's designed to make you a better market maker, not just complete an assignment."

**Let that sink in** - pause for 2 seconds

**Transition:** "So what should you do next?"

---

### Slide 19: Call to Action (1 minute)

**What to Say:**
"Here's what I'd like you to do. This week, review the docs, explore the platform, test a simple strategy. Over the next two weeks, design a tiered fee structure and iterate based on data. Ongoing, climb the leaderboard, aim for 60%+ win rate, and innovate with new approaches."

**Key Points to Emphasize:**
- "Start simple - constant fees are fine initially"
- "Use the data - match history is your friend"
- "Target 60%+ win rate as your benchmark"

**What to Show:**
- Point to the timeline (immediate → short → long-term)
- Highlight the resource links

**Resources:**
"All the docs are in the repo, the platform link is [URL], and we have a Slack channel for strategy discussion."

**Transition:** "That's what I have for you. Let's open it up for questions..."

---

### Slide 20: Q&A (5-10 minutes)

**What to Say:**
"I've got some common questions anticipated here, but I'd love to hear your questions first. Who has the first question?"

**Facilitation Tips:**
- Point to someone who raises hand
- Repeat the question for everyone: "Great question about [X]..."
- Answer concisely (< 1 minute per question)
- If you don't know: "Good question, let me get back to you on that"

**Anticipated Questions (Pre-prepared):**

**Q: "Will this replace the original completely?"**
A: "No - the original is still available for backward compatibility testing. Think of this as Challenge 2.0, a parallel track."

**Q: "Do I have to use tiered fees?"**
A: "No - constant fees still work and use the fast path. But tiered fees unlock strategic advantages. Start with constant if you prefer."

**Q: "How do I know my strategy is good?"**
A: "Run 10+ matches against diverse opponents. Target 60%+ win rate. Use match history to identify patterns and weaknesses."

**Q: "What if iterative routing doesn't converge?"**
A: "Handled gracefully - max 5 iterations. 95% converge in 3 or fewer. Worst case, you get a near-optimal result."

**Q: "Can I see opponent code?"**
A: "No - platform shows fee structures and match results, not source code. Learn by observing behavior, just like in real markets."

**Q: "What about gas costs?"**
A: "Not modeled in simulation - we focus on economic strategy. Real deployments would need gas optimization, but that's orthogonal."

**Technical Deep-Dives (if requested):**
"Happy to walk through the iterative routing math offline - it's based on fixed-point iteration with the constant product invariant."

**Closing:**
"Any final questions? [Wait 5 seconds] Okay, thank you all for your time. Looking forward to seeing your strategies on the leaderboard!"

---

## Post-Presentation Follow-Up

### Within 24 Hours:
- [ ] Share slide deck via Slack/email
- [ ] Post recording if available
- [ ] Answer any unanswered questions
- [ ] Share platform access links

### Within 1 Week:
- [ ] Check who has submitted strategies
- [ ] Offer 1-on-1 help for anyone stuck
- [ ] Post interesting match results to generate excitement
- [ ] Share top strategy patterns (anonymized)

---

## Timing Breakdown

| Section | Slides | Time | Pace |
|---------|--------|------|------|
| Opening | 1-3 | 3 min | Moderate |
| Original System | 4-5 | 3 min | Fast |
| What Changed | 6-10 | 8 min | Detailed |
| Why Better | 11-14 | 6 min | Moderate |
| Strategy | 15-17 | 5 min | Moderate |
| Conclusion | 18-20 | 2 min | Fast |
| **Total** | **20** | **27 min** | |
| Q&A | - | 5-10 min | Flexible |

**Buffer:** 3 minutes built-in for questions during presentation

---

## Tone and Energy Guidelines

### Section-by-Section Tone:

**Opening:** Professional, set expectations, generate interest
**Original:** Neutral, respectful, factual (don't criticize)
**What Changed:** Educational, detailed, technical depth
**Why Better:** Persuasive, confident, evidence-based
**Strategy:** Practical, empowering, actionable
**Conclusion:** Inspiring, motivating, clear next steps

### Energy Level:

**Start:** Medium-high (engage audience)
**Middle:** High (detail-heavy sections, keep engaged)
**End:** Medium-high (inspire action)
**Q&A:** Medium (conversational, responsive)

### Body Language:

- **Open stance:** Don't cross arms
- **Eye contact:** Scan the room, don't focus on one person
- **Hand gestures:** Use to emphasize points, don't overdo
- **Movement:** Move to different parts of room, don't pace
- **Smile:** Especially when mentioning exciting features

---

## Backup Content (if needed)

### Technical Deep-Dive: Iterative Routing Math

If someone asks for the mathematical derivation:

"The key insight is that we're solving for a fixed point. With constant fees, the optimal split satisfies:

marginal_price_1 = marginal_price_2

For tiered fees, the effective fee depends on trade size, so we can't solve analytically. Instead, we use fixed-point iteration:

1. Start with a split (using constant fees as initial guess)
2. Compute effective fees at those sizes
3. Recompute optimal split with those effective fees
4. Repeat until split stabilizes (< 0.1% change)

This converges because the effective fee function is monotonic (higher volume → lower average fee). Typical convergence is 2-3 iterations."

### Test Breakdown Detail

If someone wants more detail on testing:

"The 8 test categories each verify a specific economic property:

1. **Backward Compatibility:** Constant fees match old system exactly
2. **Symmetry:** Identical strategies earn identical PnL
3. **Determinism:** Fixed seed → identical results
4. **No Arbitrage:** Buy-then-sell loses exactly fees paid
5. **Optimal Routing:** Split beats any single AMM
6. **Accounting:** Value conservation (sum PnLs = 0)
7. **Convergence:** Routing always converges in ≤5 iterations
8. **Edge Cases:** Extreme inputs don't crash

Each category has 15-36 tests with strict acceptance criteria. For example, backward compatibility requires < 0.01% difference in final reserves."

### Example Match Replay

If someone wants to see a concrete example:

"Let me walk through a sample match. Strategy A is a Whale Hunter (40-15-5 bps tiers). Strategy B is flat 25 bps. In simulation 1, a large 1500 X trade comes in. Strategy A charges effective ~12 bps, Strategy B charges 25 bps. Router sends 80% of flow to A. A wins that sim. In simulation 2, many small 50 X trades. Strategy A charges 40 bps, Strategy B charges 25 bps. Router sends 70% to B. B wins that sim. After 50 sims, A wins 28, B wins 22. A wins the match."

---

## Adaptations for Different Scenarios

### If Running Short on Time (15 minutes):

- **Skip:** Slide 4-5 (assume they know original)
- **Combine:** Slides 11-14 into 2 slides (realism + testing only)
- **Shorten:** Strategic implications to principles only (skip tactics)
- **Result:** 15 minutes + Q&A

### If Management in Audience:

- **Emphasize:** Business case (Slides 11-13)
- **De-emphasize:** Technical details (Slide 9)
- **Add:** ROI of testing investment, career development value
- **Tone:** Focus on "why this investment was worth it"

### If Highly Technical Audience:

- **Add:** Algorithm pseudocode backup slides
- **Show:** Actual test code examples
- **Dive:** Deeper into convergence proofs
- **Encourage:** Interrupt with questions

---

## Red Flags to Watch For

**During Presentation:**

- ❌ Glazed eyes → Slow down, ask engagement question
- ❌ Lots of side conversations → Pause, check if too detailed
- ❌ Checking phones → Pick up energy, move to next section
- ❌ Confused looks → Stop, ask "Does that make sense?"
- ❌ No questions at end → Ask specific person for their thoughts

**After Presentation:**

- ❌ No one submits strategies → Follow up 1-on-1
- ❌ Negative feedback about complexity → Offer simplified onboarding
- ❌ Questions show fundamental misunderstanding → Schedule follow-up session

---

## Success Criteria

**This presentation succeeds if:**

✅ Developers understand all 5 major changes
✅ Developers agree changes improve realism and strategic depth
✅ Developers feel equipped to design winning strategies
✅ Developers are motivated to participate actively
✅ Questions reflect engagement ("How do I..." not "Why did you...")

**Red flags:**

❌ Confusion about why changes were made
❌ Skepticism that it's "just more complicated"
❌ Feeling overwhelmed by complexity
❌ Disengagement or lack of questions

---

## End of Presenter Notes

**Total Duration:** 25-30 minutes + Q&A
**Difficulty:** Medium-high (technical content, requires engagement)
**Preparation Time:** 1-2 hours (familiarize with slides, practice transitions)

**Final Tip:** The most important thing is enthusiasm. If you're excited about these changes, that energy will carry through to the audience. Good luck!
