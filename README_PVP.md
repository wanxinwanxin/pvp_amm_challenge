# ⚔️ PVP AMM Challenge

Player vs Player version of the AMM Challenge. Submit strategies, create head-to-head matches, and climb the leaderboard!

## 🚀 Quick Start

### Local Development

1. **Clone and setup**
   ```bash
   cd pvp_amm_challenge
   ```

2. **Build the Rust simulation engine** (if not already done)
   ```bash
   cd amm_sim_rs
   pip install maturin
   maturin develop --release
   cd ..
   ```

3. **Install dependencies**
   ```bash
   pip install -e .
   pip install -r requirements-pvp.txt
   ```

4. **Run the app**
   ```bash
   streamlit run pvp_app/app.py
   ```

5. **Open in browser**
   - The app will automatically open at `http://localhost:8501`

## 📁 Project Structure

```
pvp_amm_challenge/
├── pvp_app/                  # PVP web application
│   ├── app.py               # Main Streamlit app
│   ├── database.py          # SQLite database operations
│   ├── match_manager.py     # Match execution
│   ├── stats.py             # Statistics calculator
│   └── visualizations.py    # Charts and graphs
├── data/                     # Data storage (auto-created)
│   ├── strategies.db        # SQLite database
│   └── strategies/          # Bytecode cache
├── amm_competition/          # Original AMM competition code
├── amm_sim_rs/              # Rust simulation engine
├── contracts/               # Solidity contracts
├── Dockerfile               # Docker configuration
├── railway.toml             # Railway deployment config
└── requirements-pvp.txt     # Python dependencies
```

## 🎮 Features

### ✅ Implemented (MVP)
- ✅ Submit Solidity strategies
- ✅ Browse all strategies with search
- ✅ View strategy stats (wins, losses, win rate, avg edge)
- ✅ Create head-to-head matches
- ✅ View match results with charts
- ✅ Leaderboard with multiple sort options
- ✅ Match history per strategy
- ✅ Head-to-head breakdown
- ✅ Performance visualization

### 🔜 Coming Soon
- Twitter OAuth login
- Real-time match streaming (WebSocket)
- Match replay with step-by-step playback
- ELO rating system
- Automatic matchmaking queue
- Tournament mode
- Strategy privacy settings
- Public API for programmatic access

## 🎯 How It Works

### Strategy Submission
1. Write a Solidity contract implementing `AMMStrategyBase`
2. Submit through the web interface
3. Code is validated and compiled
4. Strategy is stored in database

### Match Creation
1. Select two strategies
2. Choose number of simulations (10-100)
3. Match runs both strategies as competing AMMs
4. Retail flow splits optimally between them
5. Winner determined by total wins across simulations

### Scoring
- **Edge**: Profit from retail trades minus losses to arbitrageurs
- **Win**: Strategy with higher edge in a simulation
- **Match Winner**: Strategy with most simulation wins

## 🏗️ Technical Details

### Architecture
- **Frontend**: Streamlit (Python web framework)
- **Backend**: Python + existing AMM competition code
- **Database**: SQLite (local file)
- **Simulation Engine**: Rust (via Python bindings)

### Match Execution Flow
```
User selects two strategies
    ↓
Load bytecode from database
    ↓
Create EVM adapters
    ↓
Run MatchRunner (50 simulations)
    ↓
Each simulation:
  - Both AMMs start with identical reserves
  - GBM price process
  - Arbitrageurs exploit mispricings
  - Retail orders route optimally
  - Winner = higher edge
    ↓
Save results to database
    ↓
Display charts and summary
```

## 🚢 Deployment

### Railway (Recommended)

1. **Create Railway account**
   - Go to [railway.app](https://railway.app)
   - Sign up with GitHub

2. **Connect repository**
   - New Project → Deploy from GitHub
   - Select `pvp_amm_challenge` repo
   - Railway auto-detects Dockerfile

3. **Configure**
   - Railway will automatically use `railway.toml`
   - Set environment variables if needed:
     ```
     PORT=8501 (auto-set by Railway)
     ```

4. **Deploy**
   - Push to main branch → auto-deploy
   - Railway provides public URL

5. **Persistent storage** (optional)
   - Add Railway Volume for `/app/data`
   - Otherwise database resets on each deploy

### Docker (Local)

```bash
# Build image
docker build -t pvp-amm-challenge .

# Run container
docker run -p 8501:8501 -v $(pwd)/data:/app/data pvp-amm-challenge
```

### Streamlit Cloud (Alternative)

⚠️ Note: Streamlit Cloud may have issues with Rust compilation.

1. Push to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect repo
4. Deploy

**Workaround for Rust**: Pre-build `amm_sim_rs` wheel and commit to repo.

## 🔧 Configuration

### Database Location
Default: `data/strategies.db`

Change in `pvp_app/app.py`:
```python
st.session_state.db = Database("custom/path/db.sqlite")
```

### Match Settings
Default: 50 simulations per match

Adjust in UI or modify `match_manager.py`:
```python
n_simulations: int = 50  # Change default
```

### Simulation Parameters
Uses baseline config from original challenge:
- 10,000 steps per simulation
- GBM volatility: 0.088% - 0.101%
- Retail arrival rate: 0.6 - 1.0 per step
- Initial reserves: 100 X, 10,000 Y at price 100

## 🐛 Troubleshooting

### Rust compilation fails
```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Rebuild
cd amm_sim_rs
maturin develop --release
```

### Database locked
```bash
# Close all connections
rm data/strategies.db
# Restart app to recreate
```

### Solidity validation fails
- Ensure contract is named `Strategy`
- Must inherit from `AMMStrategyBase`
- Must implement `afterInitialize` and `afterSwap`
- Check for syntax errors

### Match execution error
- Check both strategies exist in database
- Ensure strategies have valid bytecode
- Try with fewer simulations first

## 📊 Database Schema

### strategies
```sql
id, name, author, solidity_source, bytecode, abi, created_at, gas_estimate, description
```

### matches
```sql
id, strategy_a_id, strategy_b_id, wins_a, wins_b, draws,
avg_edge_a, avg_edge_b, n_simulations, created_at
```

### simulation_results
```sql
id, match_id, simulation_index, seed, edge_a, edge_b,
pnl_a, pnl_b, winner, steps_json
```

## 🤝 Contributing

This is a personal project but contributions are welcome!

1. Fork the repo
2. Create feature branch
3. Make changes
4. Submit PR

## 📝 License

Based on [amm-challenge](https://github.com/benedictbrady/amm-challenge) by Benedict Brady and Dan Robinson.

## 🆘 Support

Issues? Questions?

1. Check troubleshooting section above
2. Review [original AMM challenge docs](https://ammchallenge.com)
3. Open GitHub issue

---

Built with ❤️ using Streamlit + Rust + Solidity
