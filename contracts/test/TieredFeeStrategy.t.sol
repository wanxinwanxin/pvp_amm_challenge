// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "forge-std/Test.sol";
import {TieredFeeStrategy} from "../src/examples/TieredFeeStrategy.sol";
import {TradeInfo} from "../src/IAMMStrategy.sol";
import {FeeStructure, FeeTier} from "../src/IFeeStructure.sol";

contract TieredFeeStrategyTest is Test {
    TieredFeeStrategy public strategy;

    function setUp() public {
        strategy = new TieredFeeStrategy();
    }

    function test_SupportsFeeStructure() public view {
        assertTrue(strategy.supportsFeeStructure(), "Should support fee structures");
    }

    function test_GetFeeStructure() public {
        TradeInfo memory trade = TradeInfo({
            isBuy: true,
            amountX: 50e18,
            amountY: 5000e18,
            timestamp: 1,
            reserveX: 150e18,
            reserveY: 15000e18
        });

        FeeStructure memory fs = strategy.getFeeStructure(trade);

        // Verify bid tier count
        assertEq(fs.bidTierCount, 3, "Should have 3 bid tiers");

        // Verify bid tiers
        assertEq(fs.bidTiers[0].threshold, 0, "Tier 0 threshold should be 0");
        assertEq(fs.bidTiers[0].fee, 30e14, "Tier 0 fee should be 30bps");

        assertEq(fs.bidTiers[1].threshold, 100e18, "Tier 1 threshold should be 100 X");
        assertEq(fs.bidTiers[1].fee, 20e14, "Tier 1 fee should be 20bps");

        assertEq(fs.bidTiers[2].threshold, 1000e18, "Tier 2 threshold should be 1000 X");
        assertEq(fs.bidTiers[2].fee, 10e14, "Tier 2 fee should be 10bps");

        // Verify ask tier count
        assertEq(fs.askTierCount, 3, "Should have 3 ask tiers");

        // Verify ask tiers (symmetric)
        assertEq(fs.askTiers[0].threshold, 0, "Ask tier 0 threshold should be 0");
        assertEq(fs.askTiers[0].fee, 30e14, "Ask tier 0 fee should be 30bps");

        assertEq(fs.askTiers[1].threshold, 100e18, "Ask tier 1 threshold should be 100 X");
        assertEq(fs.askTiers[1].fee, 20e14, "Ask tier 1 fee should be 20bps");

        assertEq(fs.askTiers[2].threshold, 1000e18, "Ask tier 2 threshold should be 1000 X");
        assertEq(fs.askTiers[2].fee, 10e14, "Ask tier 2 fee should be 10bps");
    }

    function test_GetFeeStructureGas() public {
        TradeInfo memory trade = TradeInfo({
            isBuy: true,
            amountX: 50e18,
            amountY: 5000e18,
            timestamp: 1,
            reserveX: 150e18,
            reserveY: 15000e18
        });

        uint256 gasBefore = gasleft();
        strategy.getFeeStructure(trade);
        uint256 gasUsed = gasBefore - gasleft();

        console.log("Gas used for getFeeStructure:", gasUsed);

        // Should be well under 300k gas (targeting ~10-20k)
        assertLt(gasUsed, 50000, "Gas usage should be < 50k");
    }

    function test_BackwardCompatibility_AfterSwap() public view {
        TradeInfo memory trade = TradeInfo({
            isBuy: true,
            amountX: 50e18,
            amountY: 5000e18,
            timestamp: 1,
            reserveX: 150e18,
            reserveY: 15000e18
        });

        (uint256 bidFee, uint256 askFee) = strategy.afterSwap(trade);

        // Should return base tier (30bps) for compatibility
        assertEq(bidFee, 30e14, "Bid fee should be 30bps (base tier)");
        assertEq(askFee, 30e14, "Ask fee should be 30bps (base tier)");
    }

    function test_BackwardCompatibility_AfterInitialize() public view {
        (uint256 bidFee, uint256 askFee) = strategy.afterInitialize(100e18, 10000e18);

        assertEq(bidFee, 30e14, "Initial bid fee should be 30bps");
        assertEq(askFee, 30e14, "Initial ask fee should be 30bps");
    }

    function test_GetName() public view {
        string memory name = strategy.getName();
        assertEq(name, "TieredFees_30_20_10", "Name should indicate tier structure");
    }

    function test_TierThresholdsAreIncreasing() public {
        TradeInfo memory trade = TradeInfo({
            isBuy: true,
            amountX: 1e18,
            amountY: 100e18,
            timestamp: 1,
            reserveX: 100e18,
            reserveY: 10000e18
        });

        FeeStructure memory fs = strategy.getFeeStructure(trade);

        // Verify thresholds are strictly increasing
        assertLt(fs.bidTiers[0].threshold, fs.bidTiers[1].threshold, "Tier thresholds should be increasing");
        assertLt(fs.bidTiers[1].threshold, fs.bidTiers[2].threshold, "Tier thresholds should be increasing");

        assertLt(fs.askTiers[0].threshold, fs.askTiers[1].threshold, "Ask tier thresholds should be increasing");
        assertLt(fs.askTiers[1].threshold, fs.askTiers[2].threshold, "Ask tier thresholds should be increasing");
    }

    function test_TierFeesAreDecreasing() public {
        TradeInfo memory trade = TradeInfo({
            isBuy: true,
            amountX: 1e18,
            amountY: 100e18,
            timestamp: 1,
            reserveX: 100e18,
            reserveY: 10000e18
        });

        FeeStructure memory fs = strategy.getFeeStructure(trade);

        // Verify fees decrease with larger trades (volume discount)
        assertGt(fs.bidTiers[0].fee, fs.bidTiers[1].fee, "Fees should decrease for larger trades");
        assertGt(fs.bidTiers[1].fee, fs.bidTiers[2].fee, "Fees should decrease for larger trades");

        assertGt(fs.askTiers[0].fee, fs.askTiers[1].fee, "Ask fees should decrease for larger trades");
        assertGt(fs.askTiers[1].fee, fs.askTiers[2].fee, "Ask fees should decrease for larger trades");
    }
}
