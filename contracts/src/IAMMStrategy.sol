// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import {FeeStructure} from "./IFeeStructure.sol";

/// @title Trade information passed to AMM strategies
/// @notice Contains all data about an executed trade that strategies can use to adjust fees
struct TradeInfo {
    bool isBuy;          // true if AMM bought X (trader sold X)
    uint256 amountX;     // Amount of X traded (WAD precision, 1e18)
    uint256 amountY;     // Amount of Y traded (WAD precision, 1e18)
    uint256 timestamp;   // Simulation step number
    uint256 reserveX;    // Post-trade X reserves (WAD precision)
    uint256 reserveY;    // Post-trade Y reserves (WAD precision)
}

/// @title AMM Strategy Interface
/// @notice Interface that all AMM fee strategies must implement
/// @dev Fees are returned as WAD values (1e18 = 100%, 1e15 = 0.1% = 10bps)
interface IAMMStrategy {
    /// @notice Initialize the strategy with starting reserves
    /// @param initialX Starting X reserve amount (WAD precision)
    /// @param initialY Starting Y reserve amount (WAD precision)
    /// @return bidFee Fee when AMM buys X (WAD precision, e.g., 30e14 = 30bps)
    /// @return askFee Fee when AMM sells X (WAD precision, e.g., 30e14 = 30bps)
    function afterInitialize(uint256 initialX, uint256 initialY) external returns (uint256 bidFee, uint256 askFee);

    /// @notice Called after each trade to update fees
    /// @param trade Information about the just-executed trade
    /// @return bidFee Updated fee when AMM buys X (WAD precision)
    /// @return askFee Updated fee when AMM sells X (WAD precision)
    function afterSwap(TradeInfo calldata trade) external returns (uint256 bidFee, uint256 askFee);

    /// @notice Get the strategy name for display
    /// @return Strategy name string
    function getName() external view returns (string memory);

    /*//////////////////////////////////////////////////////////////
                        OPTIONAL TIER-BASED FEES
    //////////////////////////////////////////////////////////////*/

    /// @notice Check if this strategy supports piecewise fee structures
    /// @dev Strategies implementing tier-based fees should return true
    /// @dev Default implementation in AMMStrategyBase returns false for backward compatibility
    /// @return True if the strategy implements getFeeStructure(), false otherwise
    function supportsFeeStructure() external view returns (bool);

    /// @notice Get the complete fee structure with up to 3 tiers per direction
    /// @dev Only called if supportsFeeStructure() returns true
    /// @dev Allows strategies to specify size-dependent fees (e.g., 30bps for small trades, 10bps for large)
    /// @dev Router will compute weighted average fees for near-optimal splitting
    /// @param trade Current trade information (may be used to adjust tiers dynamically)
    /// @return fee structure containing bid and ask tier arrays
    function getFeeStructure(TradeInfo calldata trade) external returns (FeeStructure memory);
}
