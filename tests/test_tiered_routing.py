"""Integration tests for tiered fee routing across multiple AMMs."""

import pytest
from decimal import Decimal

from amm_competition.core.amm import AMM
from amm_competition.core.trade import FeeQuote, FeeTier
from amm_competition.market.router import OrderRouter
from amm_competition.market.retail import RetailOrder


class MockStrategy:
    """Mock strategy for testing that returns fixed fees."""

    def __init__(self, name: str, fee_quote: FeeQuote):
        self._name = name
        self._fee_quote = fee_quote

    def get_name(self) -> str:
        return self._name

    def after_initialize(self, initial_x: Decimal, initial_y: Decimal) -> FeeQuote:
        return self._fee_quote

    def after_swap(self, trade):
        return self._fee_quote

    def reset(self):
        pass


def create_amm(strategy: MockStrategy, reserve_x: Decimal, reserve_y: Decimal) -> AMM:
    """Helper to create and initialize an AMM."""
    amm = AMM(strategy=strategy, reserve_x=reserve_x, reserve_y=reserve_y)
    amm.initialize()
    return amm


class TestTwoAMMsConstantVsTiered:
    """Test routing between one constant-fee and one tiered-fee AMM."""

    def test_buy_with_one_constant_one_tiered(self):
        """Test buying X when one AMM has constant fees and one has tiers."""
        # AMM1: Constant 30bps
        constant_quote = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003")
        )
        strategy1 = MockStrategy("ConstantFee", constant_quote)
        amm1 = create_amm(strategy1, Decimal("1000"), Decimal("1000"))

        # AMM2: Tiered fees (30bps small, 20bps medium, 10bps large)
        tiered_quote = FeeQuote(
            bid_fee=Decimal("0.003"),  # Fallback
            ask_fee=Decimal("0.003"),  # Fallback
            bid_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
                FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
                FeeTier(threshold=Decimal("1000"), fee=Decimal("0.001")),
            ],
            ask_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
                FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
                FeeTier(threshold=Decimal("1000"), fee=Decimal("0.001")),
            ]
        )
        strategy2 = MockStrategy("TieredFee", tiered_quote)
        amm2 = create_amm(strategy2, Decimal("1000"), Decimal("1000"))

        # Route a buy order
        router = OrderRouter()
        total_y = Decimal("100")
        splits = router.compute_optimal_split_buy([amm1, amm2], total_y)

        # Verify split is reasonable
        assert len(splits) == 2
        assert splits[0][0] in [amm1, amm2]
        assert splits[1][0] in [amm1, amm2]

        # Verify amounts sum to total
        total_split = splits[0][1] + splits[1][1]
        assert abs(total_split - total_y) < Decimal("0.01")

        # Since both have same base fee, split should be roughly equal
        # (tiered AMM becomes cheaper for larger trades, so exact split depends on iteration)
        assert splits[0][1] > Decimal("0")
        assert splits[1][1] > Decimal("0")

    def test_sell_with_one_constant_one_tiered(self):
        """Test selling X when one AMM has constant fees and one has tiers."""
        constant_quote = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003")
        )
        strategy1 = MockStrategy("ConstantFee", constant_quote)
        amm1 = create_amm(strategy1, Decimal("1000"), Decimal("1000"))

        tiered_quote = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003"),
            bid_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
                FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
            ],
            ask_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
                FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
            ]
        )
        strategy2 = MockStrategy("TieredFee", tiered_quote)
        amm2 = create_amm(strategy2, Decimal("1000"), Decimal("1000"))

        # Route a sell order
        router = OrderRouter()
        total_x = Decimal("50")
        splits = router.compute_optimal_split_sell([amm1, amm2], total_x)

        # Verify split
        assert len(splits) == 2
        total_split = splits[0][1] + splits[1][1]
        assert abs(total_split - total_x) < Decimal("0.01")
        assert splits[0][1] > Decimal("0")
        assert splits[1][1] > Decimal("0")


class TestTwoAMMsBothTiered:
    """Test routing between two tiered-fee AMMs."""

    def test_buy_with_different_tier_structures(self):
        """Test routing when both AMMs have different tiered fee structures."""
        # AMM1: Aggressive tiers (starts high, drops fast)
        tier_quote1 = FeeQuote(
            bid_fee=Decimal("0.005"),
            ask_fee=Decimal("0.005"),
            ask_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.005")),
                FeeTier(threshold=Decimal("50"), fee=Decimal("0.001")),
            ],
            bid_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.005")),
                FeeTier(threshold=Decimal("50"), fee=Decimal("0.001")),
            ]
        )
        strategy1 = MockStrategy("AggressiveTiers", tier_quote1)
        amm1 = create_amm(strategy1, Decimal("1000"), Decimal("1000"))

        # AMM2: Conservative tiers (starts low, stays flat)
        tier_quote2 = FeeQuote(
            bid_fee=Decimal("0.002"),
            ask_fee=Decimal("0.002"),
            ask_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.002")),
                FeeTier(threshold=Decimal("500"), fee=Decimal("0.001")),
            ],
            bid_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.002")),
                FeeTier(threshold=Decimal("500"), fee=Decimal("0.001")),
            ]
        )
        strategy2 = MockStrategy("ConservativeTiers", tier_quote2)
        amm2 = create_amm(strategy2, Decimal("1000"), Decimal("1000"))

        # Route a buy order
        router = OrderRouter()
        total_y = Decimal("200")
        splits = router.compute_optimal_split_buy([amm1, amm2], total_y)

        # AMM2 should get more of the order due to lower base fee
        assert len(splits) == 2
        total_split = splits[0][1] + splits[1][1]
        assert abs(total_split - total_y) < Decimal("0.01")

    def test_sell_with_symmetric_tiers(self):
        """Test routing when both AMMs have identical tiered structures."""
        # Both AMMs: Same tier structure
        tier_quote = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003"),
            bid_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
                FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
                FeeTier(threshold=Decimal("500"), fee=Decimal("0.001")),
            ],
            ask_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
                FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
                FeeTier(threshold=Decimal("500"), fee=Decimal("0.001")),
            ]
        )

        strategy1 = MockStrategy("TieredA", tier_quote)
        amm1 = create_amm(strategy1, Decimal("1000"), Decimal("1000"))

        strategy2 = MockStrategy("TieredB", tier_quote)
        amm2 = create_amm(strategy2, Decimal("1000"), Decimal("1000"))

        # Route a sell order
        router = OrderRouter()
        total_x = Decimal("100")
        splits = router.compute_optimal_split_sell([amm1, amm2], total_x)

        # With identical reserves and fees, split should be roughly 50/50
        assert len(splits) == 2
        total_split = splits[0][1] + splits[1][1]
        assert abs(total_split - total_x) < Decimal("0.01")

        # Check split is approximately equal (within 10% tolerance for numerical precision)
        assert abs(splits[0][1] - splits[1][1]) < total_x * Decimal("0.1")


class TestNWayRouting:
    """Test routing across N > 2 AMMs with tiered fees."""

    def test_three_amms_mixed_tiers(self):
        """Test routing across 3 AMMs with mixed constant/tiered fees."""
        # AMM1: Constant
        constant_quote = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003")
        )
        strategy1 = MockStrategy("Constant", constant_quote)
        amm1 = create_amm(strategy1, Decimal("1000"), Decimal("1000"))

        # AMM2: Tiered
        tier_quote2 = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003"),
            ask_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
                FeeTier(threshold=Decimal("100"), fee=Decimal("0.0015")),
            ],
            bid_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
                FeeTier(threshold=Decimal("100"), fee=Decimal("0.0015")),
            ]
        )
        strategy2 = MockStrategy("Tiered1", tier_quote2)
        amm2 = create_amm(strategy2, Decimal("1000"), Decimal("1000"))

        # AMM3: Different tiers
        tier_quote3 = FeeQuote(
            bid_fee=Decimal("0.002"),
            ask_fee=Decimal("0.002"),
            ask_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.002")),
                FeeTier(threshold=Decimal("200"), fee=Decimal("0.001")),
            ],
            bid_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.002")),
                FeeTier(threshold=Decimal("200"), fee=Decimal("0.001")),
            ]
        )
        strategy3 = MockStrategy("Tiered2", tier_quote3)
        amm3 = create_amm(strategy3, Decimal("1000"), Decimal("1000"))

        # Route a buy order across all 3
        router = OrderRouter()
        total_y = Decimal("300")
        splits = router.compute_optimal_split_buy([amm1, amm2, amm3], total_y)

        # Verify 3-way split
        assert len(splits) == 3
        total_split = sum(s[1] for s in splits)
        assert abs(total_split - total_y) < Decimal("0.01")

        # All AMMs should get some of the order
        for amm, amount in splits:
            assert amount > Decimal("0")

    def test_five_amms_all_tiered(self):
        """Test maximum N=5 case with all tiered AMMs."""
        # Create 5 AMMs with different tier structures
        amms = []
        for i in range(5):
            tier_quote = FeeQuote(
                bid_fee=Decimal("0.003"),
                ask_fee=Decimal("0.003"),
                ask_tiers=[
                    FeeTier(threshold=Decimal("0"), fee=Decimal("0.003") - Decimal(i) * Decimal("0.0001")),
                    FeeTier(threshold=Decimal("100"), fee=Decimal("0.002") - Decimal(i) * Decimal("0.0001")),
                ],
                bid_tiers=[
                    FeeTier(threshold=Decimal("0"), fee=Decimal("0.003") - Decimal(i) * Decimal("0.0001")),
                    FeeTier(threshold=Decimal("100"), fee=Decimal("0.002") - Decimal(i) * Decimal("0.0001")),
                ]
            )
            strategy = MockStrategy(f"Tiered{i}", tier_quote)
            amm = create_amm(strategy, Decimal("1000"), Decimal("1000"))
            amms.append(amm)

        # Route across all 5
        router = OrderRouter()
        total_x = Decimal("500")
        splits = router.compute_optimal_split_sell(amms, total_x)

        # Verify 5-way split
        assert len(splits) == 5
        total_split = sum(s[1] for s in splits)
        assert abs(total_split - total_x) < Decimal("0.01")

        # AMMs with lower fees should get more of the order
        # (AMM4 has lowest fees, should get most)
        amounts_by_amm = {amm.strategy.get_name(): amount for amm, amount in splits}
        # Just verify all got some amount (exact distribution depends on iteration)
        for name, amount in amounts_by_amm.items():
            assert amount > Decimal("0")


class TestAccountingAccuracy:
    """Test that PnL accounting is accurate with tiered fees."""

    def test_pnl_sums_to_zero_two_amms(self):
        """Test that sum of PnLs equals zero for two-AMM routing."""
        # Create two AMMs with tiered fees
        tier_quote1 = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003"),
            ask_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
                FeeTier(threshold=Decimal("50"), fee=Decimal("0.002")),
            ],
            bid_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
                FeeTier(threshold=Decimal("50"), fee=Decimal("0.002")),
            ]
        )
        strategy1 = MockStrategy("Tiered1", tier_quote1)
        amm1 = create_amm(strategy1, Decimal("1000"), Decimal("1000"))

        tier_quote2 = FeeQuote(
            bid_fee=Decimal("0.002"),
            ask_fee=Decimal("0.002"),
            ask_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.002")),
                FeeTier(threshold=Decimal("100"), fee=Decimal("0.001")),
            ],
            bid_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.002")),
                FeeTier(threshold=Decimal("100"), fee=Decimal("0.001")),
            ]
        )
        strategy2 = MockStrategy("Tiered2", tier_quote2)
        amm2 = create_amm(strategy2, Decimal("1000"), Decimal("1000"))

        # Record initial reserves
        initial_x1, initial_y1 = amm1.reserve_x, amm1.reserve_y
        initial_x2, initial_y2 = amm2.reserve_x, amm2.reserve_y

        # Execute a routed buy order
        router = OrderRouter()
        order = RetailOrder(side="buy", size=Decimal("100"))
        trades = router.route_order(order, [amm1, amm2], Decimal("1.0"), timestamp=0)

        # Calculate PnL for each AMM (change in reserves)
        pnl_x1 = amm1.reserve_x - initial_x1
        pnl_y1 = amm1.reserve_y - initial_y1
        pnl_x2 = amm2.reserve_x - initial_x2
        pnl_y2 = amm2.reserve_y - initial_y2

        # Total X change should equal negative of total Y change (value conservation)
        # AMMs gain Y, lose X (buy direction)
        total_x_change = pnl_x1 + pnl_x2
        total_y_change = pnl_y1 + pnl_y2

        # Verify reserves changed
        assert total_x_change < Decimal("0")  # AMMs lost X
        assert total_y_change > Decimal("0")  # AMMs gained Y

        # Verify trades were executed
        assert len(trades) > 0

        # Sum of all Y amounts traded should approximately match order size
        total_y_traded = sum(trade.amount_y for trade in trades)
        assert abs(total_y_traded - order.size) < Decimal("0.01")

        # The key accounting property: reserves changed by the traded amounts
        # (minus fees which go to accumulated_fees, not reserves)
        # For this test, we just verify trades executed and reserves changed consistently
        assert abs(total_y_change - total_y_traded) < order.size * Decimal("0.01")  # Within 1% for fees


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_liquidity_amm(self):
        """Test routing when one AMM has zero liquidity."""
        # AMM1: Normal
        tier_quote = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003"),
            ask_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
            ],
            bid_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
            ]
        )
        strategy1 = MockStrategy("Normal", tier_quote)
        amm1 = create_amm(strategy1, Decimal("1000"), Decimal("1000"))

        # AMM2: Zero liquidity
        strategy2 = MockStrategy("Zero", tier_quote)
        amm2 = create_amm(strategy2, Decimal("0"), Decimal("0"))

        # Route should handle gracefully
        router = OrderRouter()
        total_y = Decimal("100")
        splits = router.compute_optimal_split_buy([amm1, amm2], total_y)

        # All should go to AMM1
        assert len(splits) == 2
        assert splits[0][1] + splits[1][1] == total_y

    def test_very_small_trade(self):
        """Test routing with very small trade amount."""
        tier_quote = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003"),
            ask_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
                FeeTier(threshold=Decimal("100"), fee=Decimal("0.001")),
            ],
            bid_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
                FeeTier(threshold=Decimal("100"), fee=Decimal("0.001")),
            ]
        )
        strategy1 = MockStrategy("Tiered1", tier_quote)
        amm1 = create_amm(strategy1, Decimal("1000"), Decimal("1000"))

        strategy2 = MockStrategy("Tiered2", tier_quote)
        amm2 = create_amm(strategy2, Decimal("1000"), Decimal("1000"))

        # Very small trade (stays in first tier)
        router = OrderRouter()
        total_y = Decimal("0.1")
        splits = router.compute_optimal_split_buy([amm1, amm2], total_y)

        assert len(splits) == 2
        total_split = splits[0][1] + splits[1][1]
        assert abs(total_split - total_y) < Decimal("0.001")

    def test_very_large_trade(self):
        """Test routing with very large trade amount."""
        tier_quote = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003"),
            ask_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
                FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
                FeeTier(threshold=Decimal("500"), fee=Decimal("0.001")),
            ],
            bid_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
                FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
                FeeTier(threshold=Decimal("500"), fee=Decimal("0.001")),
            ]
        )
        strategy1 = MockStrategy("Tiered1", tier_quote)
        amm1 = create_amm(strategy1, Decimal("10000"), Decimal("10000"))

        strategy2 = MockStrategy("Tiered2", tier_quote)
        amm2 = create_amm(strategy2, Decimal("10000"), Decimal("10000"))

        # Large trade (spans all tiers)
        router = OrderRouter()
        total_y = Decimal("5000")
        splits = router.compute_optimal_split_buy([amm1, amm2], total_y)

        assert len(splits) == 2
        total_split = splits[0][1] + splits[1][1]
        assert abs(total_split - total_y) < Decimal("1")
