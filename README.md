# ⚔️ PVP AMM Challenge

**Player vs Player** automated market maker competition. Submit strategies, create head-to-head matches, and climb the leaderboard!

![PVP AMM Banner](https://img.shields.io/badge/AMM-PvP%20Competition-blue)
![Rust](https://img.shields.io/badge/Rust-Simulation%20Engine-orange)
![Python](https://img.shields.io/badge/Python-Backend-green)
![Streamlit](https://img.shields.io/badge/Streamlit-UI-red)

## 🎮 Features

- 📤 **Submit Strategies** - Write Solidity contracts with dynamic fee logic
- ⚔️ **Head-to-Head Matches** - Compete any two strategies in realistic simulations
- 📊 **Live Leaderboard** - Track wins, losses, and average edge
- 📈 **Rich Analytics** - Interactive charts showing edge, fees, and performance
- 🏆 **Match History** - Full history with head-to-head breakdowns
- 🎯 **Public Strategies** - Learn from others' approaches

## 🚀 Quick Start

### Local Development

```bash
# Clone the repo
git clone https://github.com/wanxinwanxin/pvp_amm_challenge.git
cd pvp_amm_challenge

# Run the setup script (installs everything + launches app)
./setup_and_run.sh
```

The app will launch at **http://localhost:8501**

### Manual Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Rust (if needed)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Build Rust simulation engine
cd amm_sim_rs
pip install maturin
maturin develop --release
cd ..

# Install dependencies
pip install -e .
pip install -r requirements-pvp.txt

# Seed database (optional)
python pvp_app/seed_data.py

# Run app
streamlit run pvp_app/app.py
```

## 📖 How It Works

### Strategy Submission
1. Write a Solidity contract implementing `AMMStrategyBase`
2. Implement `afterInitialize()` and `afterSwap()` callbacks
3. Submit through web interface
4. Strategy is validated, compiled, and stored

### Match Mechanics
- Each strategy controls its own AMM pool
- Both start with identical reserves (100 X, 10,000 Y at price 100)
- Retail flow splits optimally based on fees
- Arbitrageurs exploit mispricings
- Winner = higher edge across simulations

### Scoring
- **Edge**: Profit from retail trades - losses to arbitrage
- **Win**: Strategy with higher edge in a simulation
- **Match Winner**: Strategy with most simulation wins

## 🏗️ Architecture

```
Streamlit UI
    ↓
Python Backend
├── SQLite Database
├── Match Manager
├── Stats Calculator
└── Visualizations
    ↓
AMM Competition Framework
├── EVM Strategy Executor
├── Solidity Compiler
└── Match Runner
    ↓
Rust Simulation Engine (Fast!)
```

## 📊 Tech Stack

- **Frontend**: Streamlit
- **Backend**: Python
- **Database**: SQLite
- **Simulation**: Rust (via Python bindings)
- **Smart Contracts**: Solidity
- **Charts**: Plotly
- **Deployment**: Railway / Docker

## 🚢 Deploy to Railway

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template)

```bash
# Install Railway CLI
npm i -g @railway/cli

# Login and deploy
railway login
railway init
railway up
```

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for full instructions.

## 📝 Example Strategy

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AMMStrategyBase} from "./AMMStrategyBase.sol";
import {TradeInfo} from "./IAMMStrategy.sol";

contract Strategy is AMMStrategyBase {
    function afterInitialize(uint256, uint256) external override returns (uint256, uint256) {
        // Return initial bid and ask fees (30 basis points)
        return (bpsToWad(30), bpsToWad(30));
    }

    function afterSwap(TradeInfo calldata trade) external override returns (uint256, uint256) {
        // Increase fees after large trades
        uint256 tradeRatio = wdiv(trade.amountY, trade.reserveY);

        if (tradeRatio > WAD / 20) { // > 5% of reserves
            return (bpsToWad(40), bpsToWad(40));
        }

        return (bpsToWad(30), bpsToWad(30));
    }

    function getName() external pure override returns (string memory) {
        return "Adaptive Strategy";
    }
}
```

## 💎 Tiered Fee Structures (Advanced)

Strategies can now implement **piecewise tiered fees** that vary with trade size, enabling volume discounts and more sophisticated pricing.

### How It Works

- **Small trades**: Higher fees (e.g., 30 basis points)
- **Medium trades**: Mid-tier fees (e.g., 20 basis points)
- **Large trades**: Lower fees (e.g., 10 basis points)

The router automatically uses **iterative refinement** to find near-optimal splits across strategies with different tier structures.

### Example Tiered Strategy

```solidity
import {AMMStrategyBase, TradeInfo, FeeStructure, FeeTier} from "./AMMStrategyBase.sol";

contract TieredFeeStrategy is AMMStrategyBase {
    function afterInitialize(uint256, uint256) external override returns (uint256, uint256) {
        // Return constant fallback fees
        return (bpsToWad(30), bpsToWad(30));
    }

    function supportsFeeStructure() external pure override returns (bool) {
        return true;  // Enable tiered fees
    }

    function getFeeStructure(TradeInfo calldata) external view override returns (FeeStructure memory) {
        // Create 3-tier structure for both bid and ask
        FeeTier memory tier1 = createTier(0, 30);      // 0-100 X: 30bps
        FeeTier memory tier2 = createTier(100, 20);    // 100-1000 X: 20bps
        FeeTier memory tier3 = createTier(1000, 10);   // 1000+ X: 10bps

        return createSymmetricFeeStructure(tier1, tier2, tier3);
    }

    function afterSwap(TradeInfo calldata) external override returns (uint256, uint256) {
        // Still need this for backward compatibility
        return (bpsToWad(30), bpsToWad(30));
    }

    function getName() external pure override returns (string memory) {
        return "Tiered Volume Discount";
    }
}
```

### Routing Behavior

- **Constant fees**: Uses fast analytical solution (original algorithm)
- **Tiered fees**: Uses iterative refinement (2-3 iterations typical)
- **N-way routing**: Supports up to 5 strategies with mixed tier/constant fees
- **Performance**: < 10ms for 5-way routing with tiered fees

### Key Features

- ✅ **Backward compatible** - Existing strategies work unchanged
- ✅ **Near-optimal** - Within 0.1% of true optimal split
- ✅ **Fast convergence** - Typically 2-3 iterations
- ✅ **Flexible** - Up to 3 tiers per direction (bid/ask)

See [contracts/src/examples/TieredFeeStrategy.sol](contracts/src/examples/TieredFeeStrategy.sol) for a complete working example.

## 🎓 Strategy Tips

1. **Balance fees vs volume** - Lower fees attract more trades
2. **React to market conditions** - Widen spreads during volatility
3. **Minimize arbitrage losses** - Quick fee adjustments help
4. **Study opponents** - Use head-to-head stats to find weaknesses
5. **Test extensively** - Run 100+ simulations to verify robustness

## 📚 Documentation

- [README_PVP.md](README_PVP.md) - Detailed user guide
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Railway deployment
- [MVP_PLAN.md](MVP_PLAN.md) - Implementation details
- [SETUP_COMPLETE.md](SETUP_COMPLETE.md) - Setup walkthrough

## 🤝 Contributing

Built on top of the original [AMM Challenge](https://github.com/benedictbrady/amm-challenge) by Benedict Brady and Dan Robinson.

Contributions welcome! Open an issue or submit a PR.

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Credits

- Original AMM Challenge: [benedictbrady/amm-challenge](https://github.com/benedictbrady/amm-challenge)
- Streamlit: [streamlit.io](https://streamlit.io)
- Rust Simulation Engine: Built with [revm](https://github.com/bluealloy/revm)

## 🔗 Links

- **Live Demo**: [Coming Soon]
- **Original Challenge**: https://ammchallenge.com
- **Discord**: [Coming Soon]

---

**Start competing!** 🏆

```bash
./setup_and_run.sh
```
