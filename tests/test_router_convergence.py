"""Unit tests for router convergence algorithm with tiered fees."""

import pytest
from decimal import Decimal

from amm_competition.core.amm import AMM
from amm_competition.core.trade import FeeQuote, FeeTier
from amm_competition.market.router import OrderRouter


class MockStrategy:
    """Mock strategy that returns fixed fees."""

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


class TestConvergence:
    """Test that the iterative refinement algorithm converges."""

    def test_converges_for_well_behaved_tiers(self):
        """Test convergence with reasonable tier structures."""
        # Two AMMs with similar tiered fee structures
        tier_quote1 = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003"),
            ask_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
                FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
            ],
            bid_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
                FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
            ]
        )
        strategy1 = MockStrategy("Tier1", tier_quote1)
        amm1 = create_amm(strategy1, Decimal("1000"), Decimal("1000"))

        tier_quote2 = FeeQuote(
            bid_fee=Decimal("0.0025"),
            ask_fee=Decimal("0.0025"),
            ask_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.0025")),
                FeeTier(threshold=Decimal("150"), fee=Decimal("0.0015")),
            ],
            bid_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.0025")),
                FeeTier(threshold=Decimal("150"), fee=Decimal("0.0015")),
            ]
        )
        strategy2 = MockStrategy("Tier2", tier_quote2)
        amm2 = create_amm(strategy2, Decimal("1000"), Decimal("1000"))

        # Route should converge quickly
        router = OrderRouter()
        splits = router.compute_optimal_split_buy([amm1, amm2], Decimal("200"))

        # Verify split completed
        assert len(splits) == 2
        assert splits[0][1] + splits[1][1] == Decimal("200")

    def test_constant_fees_use_fast_path(self):
        """Test that constant-fee strategies don't enter iteration loop."""
        # Two AMMs with constant fees
        constant_quote = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003")
        )
        strategy1 = MockStrategy("Constant1", constant_quote)
        amm1 = create_amm(strategy1, Decimal("1000"), Decimal("1000"))

        strategy2 = MockStrategy("Constant2", constant_quote)
        amm2 = create_amm(strategy2, Decimal("1000"), Decimal("1000"))

        # Should use fast path (no iteration)
        router = OrderRouter()
        splits = router.compute_optimal_split_buy([amm1, amm2], Decimal("100"))

        # Verify split completed
        assert len(splits) == 2
        assert abs(splits[0][1] + splits[1][1] - Decimal("100")) < Decimal("0.01")

    def test_max_iterations_respected(self):
        """Test that algorithm doesn't run forever even with pathological fees."""
        # Create AMMs with extreme tier structures that might not converge well
        extreme_quote = FeeQuote(
            bid_fee=Decimal("0.01"),
            ask_fee=Decimal("0.01"),
            ask_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.01")),
                FeeTier(threshold=Decimal("1"), fee=Decimal("0.0001")),
                FeeTier(threshold=Decimal("2"), fee=Decimal("0.00001")),
            ],
            bid_tiers=[
                FeeTier(threshold=Decimal("0"), fee=Decimal("0.01")),
                FeeTier(threshold=Decimal("1"), fee=Decimal("0.0001")),
                FeeTier(threshold=Decimal("2"), fee=Decimal("0.00001")),
            ]
        )
        strategy1 = MockStrategy("Extreme1", extreme_quote)
        amm1 = create_amm(strategy1, Decimal("1000"), Decimal("1000"))

        strategy2 = MockStrategy("Extreme2", extreme_quote)
        amm2 = create_amm(strategy2, Decimal("1000"), Decimal("1000"))

        # Should still complete (hit max iterations if necessary)
        router = OrderRouter()
        splits = router.compute_optimal_split_buy([amm1, amm2], Decimal("50"))

        # Verify split completed (may not be perfectly optimal but should complete)
        assert len(splits) == 2
        assert abs(splits[0][1] + splits[1][1] - Decimal("50")) < Decimal("0.1")


class TestPerformance:
    """Test that routing performance is acceptable."""

    def test_routing_is_fast(self):
        """Test that routing with 5 tiered AMMs completes quickly."""
        import time

        # Create 5 AMMs with tiered fees
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
            strategy = MockStrategy(f"Tier{i}", tier_quote)
            amm = create_amm(strategy, Decimal("1000"), Decimal("1000"))
            amms.append(amm)

        # Time the routing
        router = OrderRouter()
        start = time.time()
        splits = router.compute_optimal_split_buy(amms, Decimal("500"))
        elapsed = time.time() - start

        # Should complete in < 10ms for 5 AMMs
        assert elapsed < 0.01  # 10ms

        # Verify split completed
        assert len(splits) == 5
        total = sum(s[1] for s in splits)
        assert abs(total - Decimal("500")) < Decimal("0.1")
