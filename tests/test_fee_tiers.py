"""Unit tests for fee tier functionality."""

import pytest
from decimal import Decimal
from amm_competition.core.trade import FeeTier, FeeQuote


class TestFeeTier:
    """Tests for the FeeTier dataclass."""

    def test_create_tier(self):
        """Test basic tier creation."""
        tier = FeeTier(threshold=Decimal("100"), fee=Decimal("0.003"))
        assert tier.threshold == Decimal("100")
        assert tier.fee == Decimal("0.003")

    def test_zero_threshold(self):
        """Test tier with zero threshold (base tier)."""
        tier = FeeTier(threshold=Decimal("0"), fee=Decimal("0.003"))
        assert tier.threshold == Decimal("0")
        assert tier.fee == Decimal("0.003")

    def test_negative_threshold_raises(self):
        """Test that negative threshold raises ValueError."""
        with pytest.raises(ValueError, match="threshold must be >= 0"):
            FeeTier(threshold=Decimal("-1"), fee=Decimal("0.003"))

    def test_negative_fee_raises(self):
        """Test that negative fee raises ValueError."""
        with pytest.raises(ValueError, match="fee must be >= 0"):
            FeeTier(threshold=Decimal("100"), fee=Decimal("-0.001"))

    def test_zero_fee(self):
        """Test tier with zero fee (no fee tier)."""
        tier = FeeTier(threshold=Decimal("0"), fee=Decimal("0"))
        assert tier.fee == Decimal("0")


class TestFeeQuoteConstant:
    """Tests for constant fee mode (no tiers)."""

    def test_constant_fees(self):
        """Test basic constant fee quote."""
        quote = FeeQuote(bid_fee=Decimal("0.003"), ask_fee=Decimal("0.002"))
        assert quote.bid_fee == Decimal("0.003")
        assert quote.ask_fee == Decimal("0.002")
        assert quote.bid_tiers is None
        assert quote.ask_tiers is None

    def test_effective_fees_without_tiers(self):
        """Test that effective fees return constant fees when no tiers."""
        quote = FeeQuote(bid_fee=Decimal("0.003"), ask_fee=Decimal("0.002"))

        # Should return constant fees regardless of trade size
        assert quote.effective_bid_fee(Decimal("10")) == Decimal("0.003")
        assert quote.effective_bid_fee(Decimal("1000")) == Decimal("0.003")
        assert quote.effective_ask_fee(Decimal("10")) == Decimal("0.002")
        assert quote.effective_ask_fee(Decimal("1000")) == Decimal("0.002")

    def test_symmetric_constructor(self):
        """Test symmetric fee quote constructor."""
        quote = FeeQuote.symmetric(Decimal("0.003"))
        assert quote.bid_fee == Decimal("0.003")
        assert quote.ask_fee == Decimal("0.003")


class TestFeeQuoteTiers:
    """Tests for tiered fee mode."""

    def test_single_tier(self):
        """Test fee quote with single tier (equivalent to constant fee)."""
        tiers = [FeeTier(threshold=Decimal("0"), fee=Decimal("0.003"))]
        quote = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003"),
            bid_tiers=tiers,
            ask_tiers=tiers
        )

        # Should return the single tier fee for any size
        assert quote.effective_bid_fee(Decimal("50")) == Decimal("0.003")
        assert quote.effective_bid_fee(Decimal("500")) == Decimal("0.003")

    def test_two_tiers(self):
        """Test fee quote with two tiers."""
        tiers = [
            FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),    # 30bps
            FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),  # 20bps
        ]
        quote = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003"),
            bid_tiers=tiers,
            ask_tiers=tiers
        )

        # Small trade entirely in tier 0
        assert quote.effective_bid_fee(Decimal("50")) == Decimal("0.003")

        # Trade exactly at threshold
        assert quote.effective_bid_fee(Decimal("100")) == Decimal("0.003")

        # Trade spanning both tiers: 150 = 100@30bps + 50@20bps
        # Expected: (100*0.003 + 50*0.002) / 150 = (0.3 + 0.1) / 150 = 0.4 / 150
        expected = (Decimal("100") * Decimal("0.003") + Decimal("50") * Decimal("0.002")) / Decimal("150")
        assert quote.effective_bid_fee(Decimal("150")) == expected

        # Large trade mostly in tier 1
        # 500 = 100@30bps + 400@20bps
        expected = (Decimal("100") * Decimal("0.003") + Decimal("400") * Decimal("0.002")) / Decimal("500")
        assert quote.effective_bid_fee(Decimal("500")) == expected

    def test_three_tiers(self):
        """Test fee quote with three tiers (30bps, 20bps, 10bps)."""
        tiers = [
            FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),     # 30bps
            FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),   # 20bps
            FeeTier(threshold=Decimal("1000"), fee=Decimal("0.001")),  # 10bps
        ]
        quote = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003"),
            bid_tiers=tiers,
            ask_tiers=tiers
        )

        # Small trade in tier 0
        assert quote.effective_bid_fee(Decimal("50")) == Decimal("0.003")

        # Medium trade in tiers 0-1
        # 200 = 100@30bps + 100@20bps
        expected = (Decimal("100") * Decimal("0.003") + Decimal("100") * Decimal("0.002")) / Decimal("200")
        assert quote.effective_bid_fee(Decimal("200")) == expected

        # Large trade spanning all three tiers
        # 1500 = 100@30bps + 900@20bps + 500@10bps
        expected = (
            Decimal("100") * Decimal("0.003") +
            Decimal("900") * Decimal("0.002") +
            Decimal("500") * Decimal("0.001")
        ) / Decimal("1500")
        assert quote.effective_bid_fee(Decimal("1500")) == expected

        # Very large trade mostly in tier 2
        # 10000 = 100@30bps + 900@20bps + 9000@10bps
        expected = (
            Decimal("100") * Decimal("0.003") +
            Decimal("900") * Decimal("0.002") +
            Decimal("9000") * Decimal("0.001")
        ) / Decimal("10000")
        result = quote.effective_bid_fee(Decimal("10000"))
        assert abs(result - expected) < Decimal("0.0000001")  # Allow small rounding

    def test_zero_size_trade(self):
        """Test that zero-size trade returns base tier fee."""
        tiers = [
            FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
            FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
        ]
        quote = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003"),
            bid_tiers=tiers,
            ask_tiers=tiers
        )

        assert quote.effective_bid_fee(Decimal("0")) == Decimal("0.003")

    def test_asymmetric_tiers(self):
        """Test fee quote with different bid and ask tiers."""
        bid_tiers = [
            FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
            FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
        ]
        ask_tiers = [
            FeeTier(threshold=Decimal("0"), fee=Decimal("0.004")),
            FeeTier(threshold=Decimal("200"), fee=Decimal("0.001")),
        ]
        quote = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.004"),
            bid_tiers=bid_tiers,
            ask_tiers=ask_tiers
        )

        # Check bid direction
        bid_150 = (Decimal("100") * Decimal("0.003") + Decimal("50") * Decimal("0.002")) / Decimal("150")
        assert quote.effective_bid_fee(Decimal("150")) == bid_150

        # Check ask direction
        ask_150 = quote.effective_ask_fee(Decimal("150"))
        assert ask_150 == Decimal("0.004")  # Still in first tier


class TestFeeQuoteValidation:
    """Tests for fee quote validation."""

    def test_empty_tiers_raises(self):
        """Test that empty tier list raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            FeeQuote(
                bid_fee=Decimal("0.003"),
                ask_fee=Decimal("0.003"),
                bid_tiers=[],
                ask_tiers=None
            )

    def test_too_many_tiers_raises(self):
        """Test that more than 3 tiers raises ValueError."""
        tiers = [
            FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
            FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
            FeeTier(threshold=Decimal("200"), fee=Decimal("0.001")),
            FeeTier(threshold=Decimal("300"), fee=Decimal("0.0005")),
        ]
        with pytest.raises(ValueError, match="at most 3 tiers"):
            FeeQuote(
                bid_fee=Decimal("0.003"),
                ask_fee=Decimal("0.003"),
                bid_tiers=tiers,
                ask_tiers=None
            )

    def test_first_tier_nonzero_threshold_raises(self):
        """Test that first tier must have threshold 0."""
        tiers = [
            FeeTier(threshold=Decimal("10"), fee=Decimal("0.003")),
            FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
        ]
        with pytest.raises(ValueError, match="must have threshold 0"):
            FeeQuote(
                bid_fee=Decimal("0.003"),
                ask_fee=Decimal("0.003"),
                bid_tiers=tiers,
                ask_tiers=None
            )

    def test_non_increasing_thresholds_raises(self):
        """Test that tier thresholds must be strictly increasing."""
        tiers = [
            FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
            FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
            FeeTier(threshold=Decimal("100"), fee=Decimal("0.001")),  # Duplicate
        ]
        with pytest.raises(ValueError, match="must be >"):
            FeeQuote(
                bid_fee=Decimal("0.003"),
                ask_fee=Decimal("0.003"),
                bid_tiers=tiers,
                ask_tiers=None
            )

    def test_decreasing_thresholds_raises(self):
        """Test that tier thresholds cannot decrease."""
        tiers = [
            FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
            FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
            FeeTier(threshold=Decimal("50"), fee=Decimal("0.001")),  # Goes backward
        ]
        with pytest.raises(ValueError, match="must be >"):
            FeeQuote(
                bid_fee=Decimal("0.003"),
                ask_fee=Decimal("0.003"),
                bid_tiers=tiers,
                ask_tiers=None
            )


class TestWeightedAverageEdgeCases:
    """Tests for edge cases in weighted average calculation."""

    def test_trade_exactly_at_tier_boundary(self):
        """Test trade size exactly equal to tier threshold."""
        tiers = [
            FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
            FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
        ]
        quote = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003"),
            bid_tiers=tiers,
            ask_tiers=tiers
        )

        # Trade of size 100 should be entirely in tier 0
        assert quote.effective_bid_fee(Decimal("100")) == Decimal("0.003")

    def test_very_small_trade(self):
        """Test very small trade (< 1 token)."""
        tiers = [
            FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
            FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
        ]
        quote = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003"),
            bid_tiers=tiers,
            ask_tiers=tiers
        )

        # Should be in tier 0
        assert quote.effective_bid_fee(Decimal("0.001")) == Decimal("0.003")

    def test_very_large_trade(self):
        """Test very large trade (>> tier thresholds)."""
        tiers = [
            FeeTier(threshold=Decimal("0"), fee=Decimal("0.003")),
            FeeTier(threshold=Decimal("100"), fee=Decimal("0.002")),
            FeeTier(threshold=Decimal("1000"), fee=Decimal("0.001")),
        ]
        quote = FeeQuote(
            bid_fee=Decimal("0.003"),
            ask_fee=Decimal("0.003"),
            bid_tiers=tiers,
            ask_tiers=tiers
        )

        # Large trade should be dominated by the lowest tier
        result = quote.effective_bid_fee(Decimal("1000000"))
        # Should be very close to 0.001 (10bps)
        assert result < Decimal("0.00105")
        assert result > Decimal("0.001")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
