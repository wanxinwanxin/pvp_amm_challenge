# PVP AMM Challenge - MVP Implementation Plan

## 🎯 MVP Scope

A simple web interface where users can:
1. Submit strategies (Solidity code)
2. Browse all submitted strategies
3. View strategy stats and match history
4. Manually create matches between any two strategies
5. View match results with visualizations

## 🏗️ Architecture Decision

### Option A: Streamlit (Recommended for MVP)
**Fastest path to launch - 2-3 days**

**Pros:**
- Single Python codebase (integrates seamlessly with existing AMM code)
- Built-in UI components (file upload, charts, tables)
- No frontend/backend split needed
- Deploy to Streamlit Cloud for free
- Perfect for data science/simulation apps

**Cons:**
- Less customizable UI
- Harder to scale to thousands of users
- Page reloads on interaction

**Tech Stack:**
- Streamlit (UI + Backend)
- SQLite (Database)
- Plotly (Charts)
- Existing amm_sim_rs (Match engine)

### Option B: FastAPI + React
**More professional - 1-2 weeks**

**Pros:**
- Modern, scalable architecture
- Better UX (no page reloads)
- Easier to add features later
- Professional appearance

**Cons:**
- More setup time
- Need to manage frontend/backend separately
- More deployment complexity

**Tech Stack:**
- FastAPI (Backend API)
- Next.js + React (Frontend)
- SQLite → PostgreSQL (Database)
- Existing amm_sim_rs (Match engine)

## ✅ Recommendation: Start with Streamlit

Build Streamlit MVP first (2-3 days), then migrate to FastAPI+React if needed.

---

## 📁 Project Structure

```
pvp_amm_challenge/
├── amm_competition/          # Existing code
├── amm_sim_rs/              # Existing Rust engine
├── contracts/               # Existing Solidity contracts
├── pvp_app/                 # NEW: MVP application
│   ├── app.py              # Main Streamlit app
│   ├── database.py         # SQLite operations
│   ├── match_manager.py    # Match execution
│   ├── stats.py            # Calculate statistics
│   └── visualizations.py   # Charts and graphs
├── data/                    # NEW: Data storage
│   ├── strategies.db       # SQLite database
│   └── strategies/         # Compiled bytecode cache
├── requirements-pvp.txt     # NEW: Additional dependencies
└── README_PVP.md           # NEW: PVP setup instructions
```

---

## 🗄️ Database Schema (SQLite)

### Table: strategies
```sql
CREATE TABLE strategies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    author TEXT NOT NULL,
    solidity_source TEXT NOT NULL,
    bytecode BLOB NOT NULL,
    abi TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    gas_estimate INTEGER,
    description TEXT
);
```

### Table: matches
```sql
CREATE TABLE matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    strategy_a_id INTEGER NOT NULL,
    strategy_b_id INTEGER NOT NULL,
    strategy_a_name TEXT NOT NULL,
    strategy_b_name TEXT NOT NULL,
    wins_a INTEGER NOT NULL,
    wins_b INTEGER NOT NULL,
    draws INTEGER NOT NULL,
    avg_edge_a REAL NOT NULL,
    avg_edge_b REAL NOT NULL,
    total_edge_a REAL NOT NULL,
    total_edge_b REAL NOT NULL,
    n_simulations INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (strategy_a_id) REFERENCES strategies(id),
    FOREIGN KEY (strategy_b_id) REFERENCES strategies(id)
);
```

### Table: simulation_results
```sql
CREATE TABLE simulation_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id INTEGER NOT NULL,
    simulation_index INTEGER NOT NULL,
    seed INTEGER NOT NULL,
    edge_a REAL NOT NULL,
    edge_b REAL NOT NULL,
    pnl_a REAL NOT NULL,
    pnl_b REAL NOT NULL,
    winner TEXT, -- 'a', 'b', or 'draw'
    steps_json TEXT, -- Compressed JSON of all steps for replay
    FOREIGN KEY (match_id) REFERENCES matches(id)
);
```

---

## 🎨 Streamlit App Pages

### 1. Home Page (`app.py`)
```
═══════════════════════════════════════
        🏆 PVP AMM Challenge
═══════════════════════════════════════

Welcome to the Player vs Player AMM competition!

[Submit Strategy] [Browse Strategies] [Create Match]

Recent Matches:
┌─────────────────────────────────────┐
│ SmartSpread vs AdaptiveFees        │
│ Winner: SmartSpread (8-2-0)        │
│ Avg Edge: 530 vs 420              │
│ 2 hours ago                        │
└─────────────────────────────────────┘

Top Strategies by Win Rate:
1. SmartSpread (12-3-1, 80%)
2. VolatilityTracker (10-5-0, 67%)
3. MomentumFees (8-7-0, 53%)
```

### 2. Submit Strategy Page
```
═══════════════════════════════════════
        📤 Submit New Strategy
═══════════════════════════════════════

Strategy Name: [___________________]
Author:        [___________________]

Solidity Code:
┌────────────────────────────────────┐
│ // SPDX-License-Identifier: MIT    │
│ pragma solidity ^0.8.24;           │
│                                    │
│ import {AMMStrategyBase} ...       │
│ [Monaco Editor / Text Area]        │
│                                    │
└────────────────────────────────────┘

Description: [Optional notes about strategy]

[Validate] [Compile & Submit]

✓ Validation Status: Passed
✓ Compilation: Success
✓ Gas Estimate: 245,000 per swap
```

### 3. Browse Strategies Page
```
═══════════════════════════════════════
        📚 All Strategies
═══════════════════════════════════════

Search: [___________] Sort by: [Win Rate ▼]

┌────────────────────────────────────────────────────┐
│ SmartSpread by @danrobinson                        │
│ Win Rate: 80% (12W-3L-1D)  Avg Edge: 530         │
│ [View Details] [Challenge This Strategy]          │
├────────────────────────────────────────────────────┤
│ VolatilityTracker by @benedictbrady               │
│ Win Rate: 67% (10W-5L-0D)  Avg Edge: 485         │
│ [View Details] [Challenge This Strategy]          │
└────────────────────────────────────────────────────┘
```

### 4. Strategy Detail Page
```
═══════════════════════════════════════
    Strategy: SmartSpread
═══════════════════════════════════════

Author: @danrobinson
Created: 2024-01-15
Gas Usage: ~245k per swap

📊 Statistics
────────────────────────────────────
Total Matches:    16
Wins:            12 (75%)
Losses:           3 (19%)
Draws:            1 (6%)
Avg Edge:       530
Best Edge:      682
Worst Edge:     401

📈 Performance Over Time
[Line Chart: Edge per match]

🎯 Head-to-Head Record
────────────────────────────────────
vs AdaptiveFees:      3-1-0 (75%)
vs MomentumFees:      2-0-0 (100%)
vs VolatilityTracker: 1-2-0 (33%)

📜 Match History
────────────────────────────────────
Match #42: vs AdaptiveFees
Winner: SmartSpread (8-2-0)
Edge: 530 vs 420
[View Details]

Match #38: vs VolatilityTracker
Winner: VolatilityTracker (5-5-0)
Edge: 485 vs 492
[View Details]

💻 Source Code
────────────────────────────────────
[Show/Hide Code Toggle]
```

### 5. Create Match Page
```
═══════════════════════════════════════
        ⚔️ Create New Match
═══════════════════════════════════════

Select Strategy A: [SmartSpread ▼]
Select Strategy B: [AdaptiveFees ▼]

Match Configuration:
Number of Simulations: [50] (default)
Variance: [Standard ▼]

[Start Match]

⏳ Running match... (Simulation 25/50)
Progress: [████████░░░░░░] 50%

Current Score:
Strategy A: 12 wins
Strategy B: 13 wins
Draws: 0
```

### 6. Match Results Page
```
═══════════════════════════════════════
    Match Results - SmartSpread vs AdaptiveFees
═══════════════════════════════════════

🏆 Winner: SmartSpread

Final Score:
SmartSpread:   27 wins  (54%)
AdaptiveFees:  23 wins  (46%)
Draws:          0       (0%)

Performance Metrics:
                SmartSpread   AdaptiveFees
────────────────────────────────────────
Avg Edge:       530          485
Total Edge:     26,500       24,250
Avg Fees:       42 bps       38 bps
Retail Volume:  1,250,000    1,180,000
Arb Volume:     450,000      520,000

📈 Simulation Results
[Chart: Edge for each simulation, scatter plot]

📊 Edge Over Time (Sample Simulation)
[Chart: Line chart of cumulative edge across 10k steps]

💹 Fee Changes (Sample Simulation)
[Chart: Bid/Ask fees over time for both strategies]

🔍 Individual Simulation Results
────────────────────────────────────────
Sim #1:  SmartSpread (532) vs AdaptiveFees (491) ✓
Sim #2:  SmartSpread (528) vs AdaptiveFees (540) ✗
Sim #3:  SmartSpread (545) vs AdaptiveFees (502) ✓
...
[Show All 50]

[Replay Simulation #1] [Download Results JSON]
```

---

## 🚀 Implementation Steps

### Day 1: Setup & Database

**1. Project Setup**
```bash
cd /Users/xinwan/Github/pvp_amm_challenge
mkdir -p pvp_app data/strategies
touch pvp_app/{app.py,database.py,match_manager.py,stats.py,visualizations.py}
```

**2. Install Dependencies**
```bash
# requirements-pvp.txt
streamlit>=1.31.0
plotly>=5.18.0
pandas>=2.1.0
```

**3. Create Database Module** (`pvp_app/database.py`)
- Initialize SQLite database
- CRUD operations for strategies
- CRUD operations for matches
- Query functions for stats

**4. Test Database**
```python
# Insert dummy strategies
# Query strategies
# Create dummy match
```

### Day 2: Core Features

**5. Build Match Manager** (`pvp_app/match_manager.py`)
- Integrate with existing `MatchRunner`
- Load strategies from database
- Execute match
- Save results back to database

**6. Build Stats Calculator** (`pvp_app/stats.py`)
- Calculate win/loss/draw records
- Compute average edge
- Generate head-to-head matrices
- Performance over time

**7. Test Match Execution**
```python
# Load two strategies from DB
# Run a match
# Verify results saved correctly
```

### Day 3: UI

**8. Build Strategy Submission** (`app.py`)
- File upload or code editor
- Validate using existing `SolidityValidator`
- Compile using existing `SolidityCompiler`
- Save to database

**9. Build Strategy Browser**
- List all strategies (with search/filter)
- Strategy detail page with stats
- Match history table

**10. Build Match Creation**
- Dropdown to select two strategies
- Run match button
- Display results with charts

**11. Build Match Results Page**
- Summary stats
- Plotly charts (edge over time, simulation scatter)
- Individual simulation breakdown

### Day 4: Polish & Deploy

**12. Add Visualizations** (`pvp_app/visualizations.py`)
- Edge comparison charts
- Fee changes over time
- Performance distribution

**13. Add Match Replay**
- Store full step data in database
- Slider to scrub through steps
- Animate price/edge changes

**14. Deploy to Streamlit Cloud**
- Push to GitHub
- Connect to Streamlit Cloud
- Configure secrets for DB persistence

---

## 📦 Key Files to Create

### `pvp_app/database.py`
```python
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

class Database:
    def __init__(self, db_path: str = "data/strategies.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create strategies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS strategies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                author TEXT NOT NULL,
                solidity_source TEXT NOT NULL,
                bytecode BLOB NOT NULL,
                abi TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                gas_estimate INTEGER,
                description TEXT
            )
        """)

        # Create matches table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_a_id INTEGER NOT NULL,
                strategy_b_id INTEGER NOT NULL,
                strategy_a_name TEXT NOT NULL,
                strategy_b_name TEXT NOT NULL,
                wins_a INTEGER NOT NULL,
                wins_b INTEGER NOT NULL,
                draws INTEGER NOT NULL,
                avg_edge_a REAL NOT NULL,
                avg_edge_b REAL NOT NULL,
                total_edge_a REAL NOT NULL,
                total_edge_b REAL NOT NULL,
                n_simulations INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (strategy_a_id) REFERENCES strategies(id),
                FOREIGN KEY (strategy_b_id) REFERENCES strategies(id)
            )
        """)

        # Create simulation_results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS simulation_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER NOT NULL,
                simulation_index INTEGER NOT NULL,
                seed INTEGER NOT NULL,
                edge_a REAL NOT NULL,
                edge_b REAL NOT NULL,
                pnl_a REAL NOT NULL,
                pnl_b REAL NOT NULL,
                winner TEXT,
                steps_json TEXT,
                FOREIGN KEY (match_id) REFERENCES matches(id)
            )
        """)

        conn.commit()
        conn.close()

    def add_strategy(self, name: str, author: str, source: str,
                    bytecode: bytes, abi: str, description: str = "") -> int:
        """Add a new strategy to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO strategies (name, author, solidity_source, bytecode, abi, description)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, author, source, bytecode, abi, description))

        strategy_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return strategy_id

    def get_strategy(self, strategy_id: int) -> Optional[Dict]:
        """Get a strategy by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM strategies WHERE id = ?", (strategy_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def list_strategies(self) -> List[Dict]:
        """List all strategies"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM strategies ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def add_match(self, match_data: Dict, simulation_results: List[Dict]) -> int:
        """Add a match and its simulation results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Insert match
        cursor.execute("""
            INSERT INTO matches (
                strategy_a_id, strategy_b_id, strategy_a_name, strategy_b_name,
                wins_a, wins_b, draws, avg_edge_a, avg_edge_b,
                total_edge_a, total_edge_b, n_simulations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match_data['strategy_a_id'], match_data['strategy_b_id'],
            match_data['strategy_a_name'], match_data['strategy_b_name'],
            match_data['wins_a'], match_data['wins_b'], match_data['draws'],
            match_data['avg_edge_a'], match_data['avg_edge_b'],
            match_data['total_edge_a'], match_data['total_edge_b'],
            match_data['n_simulations']
        ))

        match_id = cursor.lastrowid

        # Insert simulation results
        for sim in simulation_results:
            cursor.execute("""
                INSERT INTO simulation_results (
                    match_id, simulation_index, seed, edge_a, edge_b,
                    pnl_a, pnl_b, winner, steps_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match_id, sim['index'], sim['seed'],
                sim['edge_a'], sim['edge_b'],
                sim['pnl_a'], sim['pnl_b'],
                sim['winner'], json.dumps(sim.get('steps', []))
            ))

        conn.commit()
        conn.close()
        return match_id

    def get_strategy_matches(self, strategy_id: int) -> List[Dict]:
        """Get all matches for a strategy"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM matches
            WHERE strategy_a_id = ? OR strategy_b_id = ?
            ORDER BY created_at DESC
        """, (strategy_id, strategy_id))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]

    def get_match(self, match_id: int) -> Optional[Dict]:
        """Get a match by ID"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM matches WHERE id = ?", (match_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return dict(row)
        return None

    def get_match_simulations(self, match_id: int) -> List[Dict]:
        """Get all simulation results for a match"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM simulation_results
            WHERE match_id = ?
            ORDER BY simulation_index
        """, (match_id,))

        rows = cursor.fetchall()
        conn.close()

        return [dict(row) for row in rows]
```

### `pvp_app/match_manager.py`
```python
from typing import Tuple, Dict, List
from decimal import Decimal
import sys
sys.path.append('/tmp/amm-challenge')

from amm_competition.competition.match import MatchRunner, HyperparameterVariance
from amm_competition.competition.config import (
    BASELINE_SETTINGS, BASELINE_VARIANCE,
    build_base_config, resolve_n_workers
)
from amm_competition.evm.adapter import EVMStrategyAdapter
import json

class MatchManager:
    def __init__(self, db):
        self.db = db

    def run_match(
        self,
        strategy_a_id: int,
        strategy_b_id: int,
        n_simulations: int = 50
    ) -> Tuple[Dict, List[Dict]]:
        """
        Run a match between two strategies.
        Returns (match_data, simulation_results)
        """
        # Load strategies from database
        strat_a = self.db.get_strategy(strategy_a_id)
        strat_b = self.db.get_strategy(strategy_b_id)

        if not strat_a or not strat_b:
            raise ValueError("Strategy not found")

        # Create EVM adapters
        adapter_a = EVMStrategyAdapter(
            bytecode=strat_a['bytecode'],
            abi=json.loads(strat_a['abi'])
        )

        adapter_b = EVMStrategyAdapter(
            bytecode=strat_b['bytecode'],
            abi=json.loads(strat_b['abi'])
        )

        # Setup match runner
        config = build_base_config(seed=None)
        runner = MatchRunner(
            n_simulations=n_simulations,
            config=config,
            n_workers=resolve_n_workers(),
            variance=BASELINE_VARIANCE
        )

        # Run match (store_results=True to get detailed data)
        result = runner.run_match(adapter_a, adapter_b, store_results=True)

        # Prepare match data
        match_data = {
            'strategy_a_id': strategy_a_id,
            'strategy_b_id': strategy_b_id,
            'strategy_a_name': strat_a['name'],
            'strategy_b_name': strat_b['name'],
            'wins_a': result.wins_a,
            'wins_b': result.wins_b,
            'draws': result.draws,
            'avg_edge_a': float(result.total_edge_a / n_simulations),
            'avg_edge_b': float(result.total_edge_b / n_simulations),
            'total_edge_a': float(result.total_edge_a),
            'total_edge_b': float(result.total_edge_b),
            'n_simulations': n_simulations
        }

        # Prepare simulation results
        simulation_results = []
        for i, sim_result in enumerate(result.simulation_results):
            edge_a = float(sim_result.edges.get('submission', 0))
            edge_b = float(sim_result.edges.get('normalizer', 0))
            pnl_a = float(sim_result.pnl.get('submission', 0))
            pnl_b = float(sim_result.pnl.get('normalizer', 0))

            winner = 'a' if edge_a > edge_b else ('b' if edge_b > edge_a else 'draw')

            # Store only summary steps (every 100th) to save space
            steps_summary = [
                {
                    'timestamp': step.timestamp,
                    'fair_price': step.fair_price,
                    'spot_prices': step.spot_prices,
                    'pnls': step.pnls,
                    'fees': step.fees
                }
                for j, step in enumerate(sim_result.steps) if j % 100 == 0
            ]

            simulation_results.append({
                'index': i,
                'seed': sim_result.seed,
                'edge_a': edge_a,
                'edge_b': edge_b,
                'pnl_a': pnl_a,
                'pnl_b': pnl_b,
                'winner': winner,
                'steps': steps_summary
            })

        return match_data, simulation_results
```

### `pvp_app/app.py` (Main Streamlit App)
```python
import streamlit as st
import sys
sys.path.append('/tmp/amm-challenge')

from database import Database
from match_manager import MatchManager
from stats import StatsCalculator
from amm_competition.evm.validator import SolidityValidator
from amm_competition.evm.compiler import SolidityCompiler
import json

# Initialize
st.set_page_config(page_title="PVP AMM Challenge", layout="wide")
db = Database()
match_manager = MatchManager(db)
stats_calc = StatsCalculator(db)

# Navigation
page = st.sidebar.selectbox(
    "Navigation",
    ["Home", "Submit Strategy", "Browse Strategies", "Create Match"]
)

if page == "Home":
    st.title("🏆 PVP AMM Challenge")
    st.write("Welcome to the Player vs Player AMM competition!")

    # Recent matches
    st.header("Recent Matches")
    # TODO: Query and display recent matches

    # Top strategies
    st.header("Top Strategies")
    strategies = db.list_strategies()
    for strat in strategies[:5]:
        matches = db.get_strategy_matches(strat['id'])
        wins = sum(1 for m in matches if (m['strategy_a_id'] == strat['id'] and m['wins_a'] > m['wins_b']) or (m['strategy_b_id'] == strat['id'] and m['wins_b'] > m['wins_a']))
        st.write(f"**{strat['name']}** by {strat['author']} - {wins} wins")

elif page == "Submit Strategy":
    st.title("📤 Submit New Strategy")

    name = st.text_input("Strategy Name")
    author = st.text_input("Author")
    description = st.text_area("Description (optional)")

    code = st.text_area("Solidity Code", height=400, value="""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AMMStrategyBase} from "./AMMStrategyBase.sol";
import {TradeInfo} from "./IAMMStrategy.sol";

contract Strategy is AMMStrategyBase {
    function afterInitialize(uint256, uint256) external override returns (uint256, uint256) {
        return (bpsToWad(30), bpsToWad(30));
    }

    function afterSwap(TradeInfo calldata trade) external override returns (uint256, uint256) {
        return (bpsToWad(30), bpsToWad(30));
    }

    function getName() external pure override returns (string memory) {
        return "My Strategy";
    }
}
""")

    col1, col2 = st.columns(2)

    if col1.button("Validate"):
        validator = SolidityValidator()
        validation = validator.validate(code)
        if validation.valid:
            st.success("✓ Validation passed!")
        else:
            st.error("✗ Validation failed:")
            for error in validation.errors:
                st.error(f"  - {error}")

    if col2.button("Compile & Submit"):
        if not name or not author:
            st.error("Please provide name and author")
        else:
            # Validate
            validator = SolidityValidator()
            validation = validator.validate(code)
            if not validation.valid:
                st.error("Validation failed. Please fix errors first.")
                return

            # Compile
            compiler = SolidityCompiler()
            compilation = compiler.compile(code)
            if not compilation.success:
                st.error("Compilation failed:")
                for error in compilation.errors or []:
                    st.error(f"  - {error}")
                return

            # Save to database
            strategy_id = db.add_strategy(
                name=name,
                author=author,
                source=code,
                bytecode=bytes.fromhex(compilation.bytecode),
                abi=json.dumps(compilation.abi),
                description=description
            )

            st.success(f"✓ Strategy submitted successfully! ID: {strategy_id}")

elif page == "Browse Strategies":
    st.title("📚 All Strategies")

    strategies = db.list_strategies()

    for strat in strategies:
        with st.expander(f"{strat['name']} by {strat['author']}"):
            matches = db.get_strategy_matches(strat['id'])
            wins = sum(1 for m in matches if (m['strategy_a_id'] == strat['id'] and m['wins_a'] > m['wins_b']) or (m['strategy_b_id'] == strat['id'] and m['wins_b'] > m['wins_a']))
            losses = sum(1 for m in matches if (m['strategy_a_id'] == strat['id'] and m['wins_a'] < m['wins_b']) or (m['strategy_b_id'] == strat['id'] and m['wins_b'] < m['wins_a']))
            draws = sum(1 for m in matches if m['wins_a'] == m['wins_b'])

            col1, col2, col3 = st.columns(3)
            col1.metric("Matches", len(matches))
            col2.metric("Wins", wins)
            col3.metric("Win Rate", f"{wins/(wins+losses)*100:.1f}%" if (wins+losses) > 0 else "N/A")

            if st.button(f"View Details", key=f"view_{strat['id']}"):
                st.write("TODO: Navigate to detail page")

elif page == "Create Match":
    st.title("⚔️ Create New Match")

    strategies = db.list_strategies()
    strategy_options = {f"{s['name']} (ID: {s['id']})": s['id'] for s in strategies}

    col1, col2 = st.columns(2)

    with col1:
        strategy_a = st.selectbox("Select Strategy A", options=strategy_options.keys())

    with col2:
        strategy_b = st.selectbox("Select Strategy B", options=strategy_options.keys())

    n_sims = st.slider("Number of Simulations", min_value=10, max_value=100, value=50)

    if st.button("Start Match"):
        if strategy_a == strategy_b:
            st.error("Please select two different strategies")
        else:
            with st.spinner("Running match..."):
                strat_a_id = strategy_options[strategy_a]
                strat_b_id = strategy_options[strategy_b]

                match_data, sim_results = match_manager.run_match(
                    strat_a_id, strat_b_id, n_simulations=n_sims
                )

                match_id = db.add_match(match_data, sim_results)

                st.success("Match complete!")

                # Display results
                st.subheader("Results")
                col1, col2, col3 = st.columns(3)
                col1.metric(f"{match_data['strategy_a_name']} Wins", match_data['wins_a'])
                col2.metric(f"{match_data['strategy_b_name']} Wins", match_data['wins_b'])
                col3.metric("Draws", match_data['draws'])

                col1, col2 = st.columns(2)
                col1.metric(f"{match_data['strategy_a_name']} Avg Edge", f"{match_data['avg_edge_a']:.2f}")
                col2.metric(f"{match_data['strategy_b_name']} Avg Edge", f"{match_data['avg_edge_b']:.2f}")

                st.write(f"Match ID: {match_id}")
```

---

## 🚢 Deployment Options

### Option 1: Streamlit Cloud (Easiest)
1. Push code to GitHub
2. Go to share.streamlit.io
3. Connect repo → Deploy
4. **Issue**: Need to handle Rust compilation
   - Solution: Pre-compile `amm_sim_rs` and include wheel
   - Or: Use GitHub Actions to build before deploy

### Option 2: Railway (Recommended)
```bash
# Railway supports Dockerfile
# Can install Rust toolchain
```

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

# Install Rust
RUN apt-get update && apt-get install -y curl build-essential
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy code
WORKDIR /app
COPY . .

# Build Rust engine
RUN cd amm_sim_rs && pip install maturin && maturin build --release
RUN pip install target/wheels/*.whl

# Install Python deps
RUN pip install -e .
RUN pip install -r requirements-pvp.txt

# Run app
CMD streamlit run pvp_app/app.py --server.port=$PORT
```

### Option 3: Render
Similar to Railway, supports Docker

---

## 📋 Checklist for MVP

- [ ] Database setup with 3 tables
- [ ] Strategy submission (validate + compile + save)
- [ ] List all strategies
- [ ] Strategy detail page with stats
- [ ] Create match interface
- [ ] Match execution using existing code
- [ ] Match results display
- [ ] Basic charts (edge comparison)
- [ ] Deploy to hosting

---

## ⏱️ Timeline

**Total: 3-4 days for Streamlit MVP**

- Day 1: Database + Backend (8 hours)
- Day 2: Match execution + Stats (8 hours)
- Day 3: UI pages (8 hours)
- Day 4: Charts + Deploy (4 hours)

---

## 🔧 Setup Instructions for You

When you're ready to start:

1. **Clone the existing repo**
   ```bash
   cd /Users/xinwan/Github/pvp_amm_challenge
   ```

2. **Install Rust dependencies** (if not already)
   ```bash
   cd amm_sim_rs
   pip install maturin
   maturin develop --release
   cd ..
   ```

3. **Install PVP dependencies**
   ```bash
   pip install streamlit plotly pandas
   ```

4. **I'll create the files** above and you can run:
   ```bash
   streamlit run pvp_app/app.py
   ```

5. **For deployment**, let me know your preference:
   - Streamlit Cloud (free, easiest)
   - Railway ($5-10/mo, more control)
   - Your own server (I'll help with Docker setup)

---

## 💬 Next Steps

Would you like me to:

1. **Start implementing** the Streamlit app now?
2. **Create the database schema** and backend first?
3. **Set up the project structure** with all files?
4. **Build a different architecture** (FastAPI + React)?

I'm ready to code! Just let me know which approach you prefer and any hosting constraints.
