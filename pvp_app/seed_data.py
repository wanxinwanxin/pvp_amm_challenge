"""Seed database with sample strategies for testing."""

import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from pvp_app.database import Database
from amm_competition.evm.compiler import SolidityCompiler

# Sample strategies
SAMPLE_STRATEGIES = [
    {
        "name": "Vanilla30",
        "author": "System",
        "description": "Fixed 30 basis points fees. Baseline strategy.",
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AMMStrategyBase} from "./AMMStrategyBase.sol";
import {TradeInfo} from "./IAMMStrategy.sol";

contract Strategy is AMMStrategyBase {
    function afterInitialize(uint256, uint256) external override returns (uint256, uint256) {
        return (bpsToWad(30), bpsToWad(30));
    }

    function afterSwap(TradeInfo calldata) external override returns (uint256, uint256) {
        return (bpsToWad(30), bpsToWad(30));
    }

    function getName() external pure override returns (string memory) {
        return "Vanilla30";
    }
}
"""
    },
    {
        "name": "AdaptiveFees",
        "author": "System",
        "description": "Increases fees after large trades, decays back to baseline.",
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AMMStrategyBase} from "./AMMStrategyBase.sol";
import {TradeInfo} from "./IAMMStrategy.sol";

contract Strategy is AMMStrategyBase {
    function afterInitialize(uint256, uint256) external override returns (uint256, uint256) {
        slots[0] = bpsToWad(30);
        return (bpsToWad(30), bpsToWad(30));
    }

    function afterSwap(TradeInfo calldata trade) external override returns (uint256, uint256) {
        uint256 fee = slots[0];

        uint256 tradeRatio = wdiv(trade.amountY, trade.reserveY);
        if (tradeRatio > WAD / 20) {
            fee = clampFee(fee + bpsToWad(10));
        } else {
            uint256 base = bpsToWad(30);
            if (fee > base) {
                fee = fee > bpsToWad(1) ? fee - bpsToWad(1) : base;
            }
        }

        slots[0] = fee;
        return (fee, fee);
    }

    function getName() external pure override returns (string memory) {
        return "AdaptiveFees";
    }
}
"""
    },
    {
        "name": "WideSpreader",
        "author": "System",
        "description": "High fees (60bps) to capture maximum spread from desperate traders.",
        "code": """// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AMMStrategyBase} from "./AMMStrategyBase.sol";
import {TradeInfo} from "./IAMMStrategy.sol";

contract Strategy is AMMStrategyBase {
    function afterInitialize(uint256, uint256) external override returns (uint256, uint256) {
        return (bpsToWad(60), bpsToWad(60));
    }

    function afterSwap(TradeInfo calldata) external override returns (uint256, uint256) {
        return (bpsToWad(60), bpsToWad(60));
    }

    function getName() external pure override returns (string memory) {
        return "WideSpreader";
    }
}
"""
    }
]


def seed_database():
    """Seed database with sample strategies."""
    print("🌱 Seeding database with sample strategies...")

    db = Database()
    compiler = SolidityCompiler()

    for strat in SAMPLE_STRATEGIES:
        print(f"\n📝 Compiling {strat['name']}...")

        # Check if already exists
        existing = db.get_strategy_by_name(strat['name'])
        if existing:
            print(f"   ⏭️  Already exists, skipping")
            continue

        # Compile
        compilation = compiler.compile(strat['code'])

        if not compilation.success:
            print(f"   ❌ Compilation failed:")
            for error in compilation.errors or []:
                print(f"      {error}")
            continue

        # Save to database
        try:
            # Handle bytecode - it might be hex string or already bytes
            if isinstance(compilation.bytecode, bytes):
                bytecode = compilation.bytecode
            elif isinstance(compilation.bytecode, str):
                # Remove 0x prefix if present
                hex_str = compilation.bytecode[2:] if compilation.bytecode.startswith('0x') else compilation.bytecode
                bytecode = bytes.fromhex(hex_str)
            else:
                bytecode = bytes.fromhex(compilation.bytecode)

            strategy_id = db.add_strategy(
                name=strat['name'],
                author=strat['author'],
                source=strat['code'],
                bytecode=bytecode,
                abi=json.dumps(compilation.abi),
                description=strat['description']
            )
            print(f"   ✅ Added to database (ID: {strategy_id})")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    print("\n✨ Seeding complete!")
    print("\n📊 Current strategies:")
    strategies = db.list_strategies()
    for s in strategies:
        print(f"   - {s['name']} by {s['author']}")


if __name__ == "__main__":
    seed_database()
