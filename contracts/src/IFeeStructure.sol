// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title Fee tier configuration for size-dependent fees
/// @notice Represents a single fee tier with a trade size threshold and fee rate
/// @dev Fees are applied when the trade size exceeds the threshold
struct FeeTier {
    /// @notice Trade size threshold in WAD precision (1e18)
    /// @dev For the base tier, this should be 0
    /// @dev Subsequent tiers should have strictly increasing thresholds
    uint256 threshold;

    /// @notice Fee rate in WAD precision (1e18 = 100%, 1e15 = 0.1% = 10bps)
    /// @dev Must be in range [0, MAX_FEE] where MAX_FEE = 1e17 (10%)
    uint256 fee;
}

/// @title Complete fee structure for an AMM strategy
/// @notice Contains up to 3 fee tiers each for bid and ask directions
/// @dev Supports piecewise linear fee curves based on trade size
/// @dev Example: Small trades (0-100 X) at 30bps, medium (100-1000 X) at 20bps, large (1000+ X) at 10bps
struct FeeStructure {
    /// @notice Fee tiers for bid direction (when AMM buys X / trader sells X)
    /// @dev Array of up to 3 tiers, sorted by increasing threshold
    /// @dev Only the first bidTierCount elements are active
    FeeTier[3] bidTiers;

    /// @notice Fee tiers for ask direction (when AMM sells X / trader buys X)
    /// @dev Array of up to 3 tiers, sorted by increasing threshold
    /// @dev Only the first askTierCount elements are active
    FeeTier[3] askTiers;

    /// @notice Number of active bid tiers (1-3)
    /// @dev Must be at least 1. If > 1, tiers must be sorted by threshold
    uint8 bidTierCount;

    /// @notice Number of active ask tiers (1-3)
    /// @dev Must be at least 1. If > 1, tiers must be sorted by threshold
    uint8 askTierCount;
}
