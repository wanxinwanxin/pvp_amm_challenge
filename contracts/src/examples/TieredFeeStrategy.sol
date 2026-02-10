// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {AMMStrategyBase} from "../AMMStrategyBase.sol";
import {TradeInfo} from "../IAMMStrategy.sol";
import {FeeStructure, FeeTier} from "../IFeeStructure.sol";

/// @title Tiered Fee Strategy Example
/// @notice Demonstrates a 3-tier piecewise fee structure based on trade size
/// @dev Fee tiers:
///      - Small trades (0-100 X): 30 basis points (0.30%)
///      - Medium trades (100-1000 X): 20 basis points (0.20%)
///      - Large trades (1000+ X): 10 basis points (0.10%)
/// @dev This creates an incentive for traders to execute larger trades to get better rates
contract TieredFeeStrategy is AMMStrategyBase {
    /*//////////////////////////////////////////////////////////////
                              CONSTANTS
    //////////////////////////////////////////////////////////////*/

    /// @notice Base tier threshold (always 0)
    uint256 constant SMALL_THRESHOLD = 0;

    /// @notice Medium tier starts at 100 X tokens
    uint256 constant MEDIUM_THRESHOLD = 100 * WAD;

    /// @notice Large tier starts at 1000 X tokens
    uint256 constant LARGE_THRESHOLD = 1000 * WAD;

    /// @notice Small trade fee: 30 basis points
    uint256 constant SMALL_FEE_BPS = 30;

    /// @notice Medium trade fee: 20 basis points
    uint256 constant MEDIUM_FEE_BPS = 20;

    /// @notice Large trade fee: 10 basis points
    uint256 constant LARGE_FEE_BPS = 10;

    /*//////////////////////////////////////////////////////////////
                        INITIALIZATION
    //////////////////////////////////////////////////////////////*/

    /// @notice Initialize the strategy with starting reserves
    /// @dev Returns base tier fees (30bps) as fallback
    /// @param initialX Starting X reserve amount (unused)
    /// @param initialY Starting Y reserve amount (unused)
    /// @return bidFee Base tier bid fee (30bps)
    /// @return askFee Base tier ask fee (30bps)
    function afterInitialize(uint256 initialX, uint256 initialY)
        external
        pure
        override
        returns (uint256 bidFee, uint256 askFee)
    {
        return (bpsToWad(SMALL_FEE_BPS), bpsToWad(SMALL_FEE_BPS));
    }

    /*//////////////////////////////////////////////////////////////
                        TIER-BASED FEE SUPPORT
    //////////////////////////////////////////////////////////////*/

    /// @notice Indicate that this strategy supports piecewise fee structures
    /// @return Always returns true
    function supportsFeeStructure() external pure override returns (bool) {
        return true;
    }

    /// @notice Get the complete 3-tier fee structure
    /// @dev Returns symmetric tiers for both bid and ask directions
    /// @param trade Trade information (unused in this simple implementation)
    /// @return fs Complete fee structure with 3 tiers
    function getFeeStructure(TradeInfo calldata trade)
        external
        pure
        override
        returns (FeeStructure memory fs)
    {
        // Build bid tiers
        fs.bidTiers[0] = createTier(SMALL_THRESHOLD, SMALL_FEE_BPS);
        fs.bidTiers[1] = createTier(MEDIUM_THRESHOLD, MEDIUM_FEE_BPS);
        fs.bidTiers[2] = createTier(LARGE_THRESHOLD, LARGE_FEE_BPS);
        fs.bidTierCount = 3;

        // Symmetric ask tiers (same as bid)
        fs.askTiers[0] = createTier(SMALL_THRESHOLD, SMALL_FEE_BPS);
        fs.askTiers[1] = createTier(MEDIUM_THRESHOLD, MEDIUM_FEE_BPS);
        fs.askTiers[2] = createTier(LARGE_THRESHOLD, LARGE_FEE_BPS);
        fs.askTierCount = 3;

        return fs;
    }

    /*//////////////////////////////////////////////////////////////
                    LEGACY COMPATIBILITY (FALLBACK)
    //////////////////////////////////////////////////////////////*/

    /// @notice Fallback implementation for compatibility with constant-fee routers
    /// @dev Returns the base tier fee (30bps) for both directions
    /// @dev This is only called if the router doesn't support fee structures
    /// @param trade Trade information (unused)
    /// @return bidFee Base tier bid fee (30bps)
    /// @return askFee Base tier ask fee (30bps)
    function afterSwap(TradeInfo calldata trade)
        external
        pure
        override
        returns (uint256 bidFee, uint256 askFee)
    {
        return (bpsToWad(SMALL_FEE_BPS), bpsToWad(SMALL_FEE_BPS));
    }

    /*//////////////////////////////////////////////////////////////
                            METADATA
    //////////////////////////////////////////////////////////////*/

    /// @notice Get the strategy name for display
    /// @return Strategy name with tier information
    function getName() external pure override returns (string memory) {
        return "TieredFees_30_20_10";
    }
}
