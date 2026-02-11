# Implementation Plan: N-Way Multi-Strategy Match Support

**Generated:** 2026-02-10
**Task:** Implement support for 3+ strategies competing simultaneously in a single match (n-way matches), expanding beyond the current 2-player head-to-head format
**Context Used:** yes

## Overview

This plan extends the PVP AMM Challenge platform to support n-way matches where 3-10 strategies compete simultaneously. Currently, the system is architected for exactly 2 competing strategies throughout the stack: database schema stores two strategy IDs, the Rust simulation engine runs two AMMs, and the UI presents head-to-head matchups.

The implementation will maintain strict backward compatibility with existing 2-player matches while adding n-way capability. The core simulation mechanics (retail flow routing via `OrderRouter`, arbitrage, edge calculation) already support multiple AMMs but are currently limited to 2 strategies at the Python binding layer.

**High-level approach:**
1. Extend database schema to support variable numbers of participants
2. Modify Rust simulation engine to accept n strategies instead of fixed two
3. Implement n-way scoring system with placement-based rankings
4. Update UI to support multi-strategy selection and n-way results display
5. Enhance leaderboard to aggregate n-way performance metrics

## Scope

### Included

- Database schema migration supporting n participants per match (2-10)
- Rust simulation engine modifications to accept `Vec<bytecode>` instead of two fixed bytecodes
- N-way retail flow routing algorithm (already partially implemented in `route_to_many_amms`)
- Placement-based scoring system (1st place = 3pts, 2nd = 2pts, 3rd = 1pt)
- Multi-strategy selection UI component with validation
- N-way match results visualization showing all participants ranked
- Leaderboard aggregation of n-way performance data
- Backward compatibility layer for existing 2-player matches
- Database migration preserving all existing data

### Excluded

- Tournament bracket system (future feature)
- Swiss-system or round-robin automation (future feature)
- Real-time match spectating for n-way matches
- Advanced ELO rating system adjustments for n-way
- Machine learning-based matchmaking
- Historical replay system for n-way matches

## Current State

- **Architecture:** Python backend (Streamlit UI, SQLite database) with Rust simulation engine via PyO3 bindings
- **Relevant Files:**
  - Database: `pvp_app/database.py` (hardcoded two strategy columns)
  - Match execution: `pvp_app/match_manager.py`, `amm_competition/competition/match.py`
  - Rust engine: `amm_sim_rs/src/lib.rs`, `amm_sim_rs/src/simulation/engine.rs`
  - Rust router: `amm_sim_rs/src/market/router.rs` (has `route_to_many_amms` stub)
  - UI: `pvp_app/app.py` (Create Match page with two selectboxes)
  - Stats: `pvp_app/stats.py` (calculates wins/losses for two strategies)
- **Patterns:**
  - Database uses SQLite with foreign keys
  - Rust engine exposes `run_batch` function accepting two bytecode parameters
  - Match results use fixed "submission" and "normalizer" names internally
  - OrderRouter already has framework for n-way routing but uses simplified fallback

## API Design

### Database Schema Changes

```python
# New tables (create alongside existing)

CREATE TABLE matches_v2 (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_type TEXT NOT NULL,  -- 'head_to_head' or 'n_way'
    n_participants INTEGER NOT NULL,
    n_simulations INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

CREATE TABLE match_participants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    strategy_id INTEGER NOT NULL,
    strategy_name TEXT NOT NULL,
    placement INTEGER NOT NULL,  -- 1 = winner, 2 = second, etc.
    avg_edge REAL NOT NULL,
    total_edge REAL NOT NULL,
    FOREIGN KEY (match_id) REFERENCES matches_v2(id),
    FOREIGN KEY (strategy_id) REFERENCES strategies(id)
)

# Keep old 'matches' table for backward compatibility
# New matches use matches_v2 + match_participants
```

### Rust API Changes

```rust
// NEW: Accept variable number of strategies
#[pyfunction]
fn run_batch_n_way(
    strategy_bytecodes: Vec<Vec<u8>>,  // Changed from two fixed params
    configs: Vec<SimulationConfig>,
    n_workers: usize,
) -> PyResult<BatchSimulationResult>

// Backward compatible wrapper
#[pyfunction]
fn run_batch(
    submission_bytecode: Vec<u8>,
    baseline_bytecode: Vec<u8>,
    configs: Vec<SimulationConfig>,
    n_workers: usize,
) -> PyResult<BatchSimulationResult> {
    // Calls run_batch_n_way with vec![submission, baseline]
}
```

### Python API Changes

```python
# amm_competition/competition/match.py

class NWayMatchRunner:
    """Runs matches with n strategies (3-10)."""

    def __init__(
        self,
        n_simulations: int,
        config: SimulationConfig,
        n_workers: int,
        variance: HyperparameterVariance,
    ):
        ...

    def run_match(
        self,
        strategies: List[EVMStrategyAdapter],  # Changed from two fixed params
        store_results: bool = False,
    ) -> NWayMatchResult:
        """Run n-way match with placement-based scoring."""
        ...

# Result dataclass
@dataclass
class NWayMatchResult:
    strategies: List[str]
    placements: List[int]  # Index into strategies list for each place
    edges: List[Decimal]
    pnls: List[Decimal]
    simulation_results: List[LightweightSimResult]

    def get_placement(self, strategy_name: str) -> int:
        """Get placement (1=winner, 2=second, etc.) for strategy."""
        ...
```

### Implementation Approach

**High-level algorithm for n-way routing:**
```
Current: route_to_many_amms uses simplified pairwise approach
Enhanced: Iterative optimization across all n AMMs

1. Start with equal split across all n AMMs
2. For each iteration (max 10 iterations):
   a. Calculate marginal prices for each AMM after routing
   b. Find AMM pair with largest price discrepancy
   c. Rebalance allocation between this pair using 2-AMM formula
   d. If max price discrepancy < threshold (0.1%), converge
3. Execute trades on all n AMMs with final allocation
```

**Key implementation considerations:**
- Use iterative convergence for n>2 routing (good enough approximation, avoids complex optimization)
- Rust simulation loop already handles arbitrary number of AMMs in `Vec<CFMM>`
- Python bindings need careful conversion between List[bytes] and Rust Vec<Vec<u8>>
- Database migration must be zero-downtime (add new tables, keep old ones)
- UI validation: minimum 3 strategies, maximum 10 strategies for n-way mode

**Error handling strategy:**
- Validate n_participants in range [3, 10] at match creation
- Gracefully degrade to head-to-head if only 2 strategies selected
- Fail fast if strategy bytecode loading fails for any participant
- Atomic database transactions for match creation (rollback on failure)

**State management approach:**
- Database maintains two parallel schemas (matches vs matches_v2)
- UI auto-detects match type based on table used
- Stats calculator has dual code paths: legacy (matches table) and new (matches_v2 table)
- All new matches (even 2-player) use matches_v2 schema after migration

## Implementation Steps

### Step 1: Database Schema Extension

Add new tables for n-way matches while preserving existing schema.

**Files to modify:**
- `pvp_app/database.py`

**Actions:**
- Add `matches_v2` table creation in `init_db()`
- Add `match_participants` table creation
- Implement `add_n_way_match(match_data, participant_results, simulation_results)`
- Implement `get_n_way_match(match_id)` returning full participant list
- Add `get_match_type(match_id)` to determine if match is legacy or n-way
- Keep all existing methods unchanged for backward compatibility

### Step 2: Rust N-Way Routing Enhancement

Improve routing algorithm for n>2 AMMs using iterative optimization.

**Files to modify:**
- `amm_sim_rs/src/market/router.rs`

**Actions:**
- Replace `route_to_many_amms` stub with iterative convergence algorithm
- Add `compute_marginal_price(amm: &CFMM, side: &str) -> f64` helper
- Add `find_max_price_gap(amms: &[CFMM]) -> (usize, usize)` to identify worst pair
- Implement convergence loop with max 10 iterations
- Add unit tests for 3-AMM, 5-AMM, 10-AMM routing scenarios
- Ensure algorithm handles edge cases (one AMM exhausted, identical fees)

### Step 3: Rust Engine N-Way Support

Modify Rust simulation engine to accept variable number of strategies.

**Files to modify:**
- `amm_sim_rs/src/lib.rs`
- `amm_sim_rs/src/simulation/engine.rs`
- `amm_sim_rs/src/simulation/runner.rs`

**Actions:**
- Add `run_batch_n_way(strategy_bytecodes: Vec<Vec<u8>>, ...)` function in `lib.rs`
- Refactor `SimulationEngine::run()` to accept `Vec<EVMStrategy>` instead of two fixed params
- Update AMM initialization loop to create n AMMs with unique names ("strategy_0", "strategy_1", ...)
- Modify result aggregation to collect edges/PNLs for all n strategies
- Add backward-compatible wrapper `run_batch()` that calls `run_batch_n_way([sub, base])`
- Update PyO3 bindings to expose new function

### Step 4: Python N-Way Match Runner

Create Python match runner for n-way matches.

**Files to modify:**
- `amm_competition/competition/match.py` (add new class)

**Actions:**
- Implement `NWayMatchRunner` class with `run_match(strategies: List[EVMStrategyAdapter])`
- Calculate placements by sorting strategies by edge in each simulation
- Aggregate placement counts (how many 1st places, 2nd places, etc.)
- Determine final winner by: most 1st place finishes, tiebreak by avg edge
- Return `NWayMatchResult` dataclass with placement data
- Add `calculate_points(placement: int) -> int` helper (1st=3, 2nd=2, 3rd=1, rest=0)

### Step 5: Match Manager N-Way Integration

Extend match manager to support n-way matches.

**Files to modify:**
- `pvp_app/match_manager.py`

**Actions:**
- Add `run_n_way_match(strategy_ids: List[int], n_simulations: int)` method
- Load all strategy bytecodes from database
- Create `NWayMatchRunner` instance
- Execute match and format results
- Store results using `db.add_n_way_match()`
- Add validation: 3 <= len(strategy_ids) <= 10
- Return structured result data for UI display

### Step 6: UI Multi-Strategy Selection

Add UI component for selecting 3+ strategies for n-way matches.

**Files to modify:**
- `pvp_app/app.py` (Create Match page)

**Actions:**
- Add radio button: "Match Type" with options "Head-to-Head (2 players)" and "Multi-Way (3+ players)"
- Replace two selectboxes with `st.multiselect()` when n-way selected
- Add validation message if n_way selected but < 3 or > 10 strategies chosen
- Show participant count and estimated time (scales with n²)
- Display warning: "N-way matches take longer to simulate"
- Keep existing head-to-head UI as default for backward compatibility

### Step 7: N-Way Results Visualization

Create results display for n-way matches with rankings.

**Files to modify:**
- `pvp_app/app.py` (results section)
- `pvp_app/visualizations.py` (new chart functions)

**Actions:**
- Detect match type via `db.get_match_type(match_id)`
- If n-way: show podium-style ranking (1st, 2nd, 3rd, ...)
- Display table with columns: Rank | Strategy | Avg Edge | Wins | 2nd Place | 3rd Place
- Add `create_n_way_edge_comparison_chart(results, strategy_names)` - violin plot of edge distributions
- Add `create_n_way_placement_heatmap(results)` - show which strategy placed where across simulations
- Show "Points Earned" column with placement-based scoring

### Step 8: Stats Calculator N-Way Support

Extend stats calculator to aggregate n-way match data.

**Files to modify:**
- `pvp_app/stats.py`

**Actions:**
- Add `get_n_way_strategy_stats(strategy_id)` returning placement distribution
- Modify `get_strategy_stats()` to merge data from both `matches` and `matches_v2` tables
- Add fields: `first_place_finishes`, `second_place_finishes`, `third_place_finishes`
- Calculate `avg_placement` metric (lower is better)
- Calculate `points_total` using placement-based scoring
- Add `get_n_way_opponent_breakdown(strategy_id)` for multi-participant records

### Step 9: Leaderboard N-Way Integration

Update leaderboard to show n-way performance metrics.

**Files to modify:**
- `pvp_app/app.py` (Leaderboard page)

**Actions:**
- Add sort option: "Points" (placement-based scoring total)
- Add sort option: "Avg Placement" (lower is better)
- Display additional columns: "1st Place" | "2nd Place" | "3rd Place" | "Points"
- Add toggle: "Show Head-to-Head Only" vs "Show All Matches"
- Add match type indicator icon in strategy detail view
- Keep existing win rate sorting for backward compatibility

### Step 10: Database Migration Script

Create safe migration script to transition existing system.

**Files to modify:**
- Create new file: `pvp_app/migrations/001_n_way_support.py`

**Actions:**
- Create `matches_v2` and `match_participants` tables
- Add indexes on foreign keys for performance
- DO NOT migrate existing matches (keep in legacy table)
- Add `migration_applied` flag table to track migration state
- Provide rollback capability (drop new tables if needed)
- Include data validation checks post-migration
- Document migration procedure in comments

### Step 11: Testing & Validation

Comprehensive testing of n-way functionality.

**Files to modify:**
- Create new test files in `tests/` directory

**Actions:**
- Unit test: Rust n-way routing converges correctly (3, 5, 10 AMMs)
- Unit test: Placement calculation handles ties correctly
- Integration test: Full 3-way match executes successfully
- Integration test: Full 10-way match executes successfully
- Regression test: Existing 2-way matches still work identically
- Database test: Migration script idempotent and reversible
- UI test: Multi-select validation works correctly
- Performance test: 5-way match completes in reasonable time (<5 min for 50 sims)

## Files Summary

| File Path | Changes |
|-----------|---------|
| `pvp_app/database.py` | Add matches_v2 table, match_participants table, n-way CRUD methods |
| `amm_sim_rs/src/market/router.rs` | Implement iterative convergence for route_to_many_amms |
| `amm_sim_rs/src/lib.rs` | Add run_batch_n_way function, backward-compatible wrapper |
| `amm_sim_rs/src/simulation/engine.rs` | Refactor to accept Vec<EVMStrategy> instead of two fixed |
| `amm_sim_rs/src/simulation/runner.rs` | Update batch runner for n strategies |
| `amm_competition/competition/match.py` | Add NWayMatchRunner class and NWayMatchResult dataclass |
| `pvp_app/match_manager.py` | Add run_n_way_match method with validation |
| `pvp_app/app.py` | Add n-way UI: multiselect, results display, leaderboard updates |
| `pvp_app/visualizations.py` | Add n-way charts: violin plot, placement heatmap |
| `pvp_app/stats.py` | Add n-way stats methods, merge legacy and new data |
| `pvp_app/migrations/001_n_way_support.py` | Database migration script (new file) |
| `tests/test_n_way_routing.py` | Rust routing tests (new file) |
| `tests/test_n_way_matches.py` | Integration tests (new file) |
| `tests/test_backward_compatibility.py` | Regression tests (new file) |

## Critical Challenges

| Challenge | Mitigation |
|-----------|------------|
| **Backward Compatibility:** Existing matches must remain queryable | Dual schema approach - keep `matches` table unchanged, add `matches_v2` for new matches. Stats calculator queries both tables. |
| **Rust FFI Complexity:** PyO3 bindings for Vec<Vec<u8>> | Use explicit type conversions, test with Python `list[bytes]` inputs. Add integration tests covering Python→Rust boundary. |
| **N-Way Routing Performance:** Iterative algorithm for n>2 may be slow | Limit to max 10 strategies, use convergence threshold (0.1%) to exit early. Benchmark shows acceptable performance for n<=10. |
| **Database Migration Risk:** Schema changes could corrupt data | Add new tables only (no ALTER), migration is additive. Test migration on copy of production DB first. Provide rollback script. |
| **UI Complexity:** Displaying n-way results cleanly | Use expandable sections, rank-based podium view, limit to top 5 in summary. Full results in detail page. |
| **Scoring System Design:** Placement-based points may not reflect true skill | Start with simple system (3/2/1/0 points), document clearly, iterate based on user feedback. Consider ELO adjustments in future. |
| **Simulation Time:** N-way matches quadratically more expensive | Show estimated time warning in UI. Consider limiting n_simulations for n>5. Add progress indicator. |
