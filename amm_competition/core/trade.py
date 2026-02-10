"""Trade data classes."""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Literal, Optional


class TradeSide(Enum):
    """Side of a trade from the AMM's perspective."""
    BUY = "buy"    # AMM buys X (trader sells X)
    SELL = "sell"  # AMM sells X (trader buys X)


@dataclass(frozen=True)
class FeeTier:
    """A single fee tier with a trade size threshold and fee rate.

    Example: FeeTier(threshold=100, fee=0.003) means trades above 100 X
    have a fee of 0.003 (30 basis points).
    """
    threshold: Decimal  # Trade size threshold (in X tokens)
    fee: Decimal        # Fee rate for amounts above threshold

    def __post_init__(self) -> None:
        if self.threshold < 0:
            raise ValueError(f"threshold must be >= 0, got {self.threshold}")
        if self.fee < 0:
            raise ValueError(f"fee must be >= 0, got {self.fee}")


@dataclass(frozen=True)
class FeeQuote:
    """Fee quote returned by an AMM strategy.

    Fees are expressed as decimals (e.g., 0.003 = 30bps).

    Supports two modes:
    1. Constant fees (bid_fee, ask_fee): Single fee rate for all trade sizes
    2. Piecewise tiers (bid_tiers, ask_tiers): Size-dependent fee rates

    When tiers are provided, the router computes weighted average fees
    for optimal trade splitting.
    """
    bid_fee: Decimal  # Fee when AMM buys X (constant rate)
    ask_fee: Decimal  # Fee when AMM sells X (constant rate)

    # Optional piecewise fee tiers (up to 3 per direction)
    bid_tiers: Optional[list[FeeTier]] = None
    ask_tiers: Optional[list[FeeTier]] = None

    def __post_init__(self) -> None:
        if self.bid_fee < 0:
            raise ValueError(f"bid_fee must be >= 0, got {self.bid_fee}")
        if self.ask_fee < 0:
            raise ValueError(f"ask_fee must be >= 0, got {self.ask_fee}")

        # Validate tier structures if provided
        if self.bid_tiers is not None:
            self._validate_tiers(self.bid_tiers, "bid_tiers")
        if self.ask_tiers is not None:
            self._validate_tiers(self.ask_tiers, "ask_tiers")

    @staticmethod
    def _validate_tiers(tiers: list[FeeTier], name: str) -> None:
        """Validate that tiers are properly structured."""
        if not tiers:
            raise ValueError(f"{name} cannot be empty")
        if len(tiers) > 3:
            raise ValueError(f"{name} can have at most 3 tiers, got {len(tiers)}")

        # First tier must have threshold 0
        if tiers[0].threshold != 0:
            raise ValueError(f"{name}[0] must have threshold 0, got {tiers[0].threshold}")

        # Subsequent tiers must have strictly increasing thresholds
        for i in range(1, len(tiers)):
            if tiers[i].threshold <= tiers[i-1].threshold:
                raise ValueError(
                    f"{name}[{i}] threshold ({tiers[i].threshold}) must be > "
                    f"{name}[{i-1}] threshold ({tiers[i-1].threshold})"
                )

    def effective_bid_fee(self, trade_size: Decimal) -> Decimal:
        """Compute size-weighted average fee for bid direction.

        If bid_tiers is None, returns the constant bid_fee.
        Otherwise, computes the weighted average across all tiers
        that the trade spans.

        Args:
            trade_size: Total amount of X being traded

        Returns:
            Effective fee rate as a weighted average

        Example:
            Trade size 150 X with tiers [0:30bps, 100:20bps]
            -> (100*0.003 + 50*0.002) / 150 = 0.00267 (26.7bps average)
        """
        if self.bid_tiers is None:
            return self.bid_fee
        return self._weighted_average(self.bid_tiers, trade_size)

    def effective_ask_fee(self, trade_size: Decimal) -> Decimal:
        """Compute size-weighted average fee for ask direction.

        If ask_tiers is None, returns the constant ask_fee.
        Otherwise, computes the weighted average across all tiers
        that the trade spans.

        Args:
            trade_size: Total amount of X being traded

        Returns:
            Effective fee rate as a weighted average
        """
        if self.ask_tiers is None:
            return self.ask_fee
        return self._weighted_average(self.ask_tiers, trade_size)

    @staticmethod
    def _weighted_average(tiers: list[FeeTier], size: Decimal) -> Decimal:
        """Compute size-weighted average fee across tiers.

        The trade is split across tiers based on their thresholds,
        and each tier's fee is weighted by the amount traded in that tier.

        Args:
            tiers: List of fee tiers (must be sorted by threshold)
            size: Total trade size

        Returns:
            Weighted average fee rate

        Algorithm:
            For each tier [t_i, t_{i+1}), compute the amount in that tier:
                amount_i = min(size, t_{i+1}) - t_i
            Then: weighted_fee = sum(amount_i * fee_i) / size
        """
        if size == 0:
            return tiers[0].fee  # Return base tier fee for zero-size trades

        total_weighted_fee = Decimal("0")
        remaining_size = size

        for i, tier in enumerate(tiers):
            # Determine the upper bound of this tier
            if i + 1 < len(tiers):
                next_threshold = tiers[i + 1].threshold
            else:
                next_threshold = size  # Last tier extends to trade size

            # Amount of trade in this tier
            tier_size = min(remaining_size, next_threshold - tier.threshold)

            if tier_size > 0:
                total_weighted_fee += tier_size * tier.fee
                remaining_size -= tier_size

            if remaining_size <= 0:
                break

        return total_weighted_fee / size

    @classmethod
    def symmetric(cls, fee: Decimal) -> "FeeQuote":
        """Create a symmetric fee quote (same bid and ask)."""
        return cls(bid_fee=fee, ask_fee=fee)


@dataclass(frozen=True)
class TradeInfo:
    """Information about an executed trade, provided to AMM strategies.

    This is the only information strategies receive about market activity.
    Strategies cannot see external prices, other AMM states, or any other data.
    """
    side: Literal["buy", "sell"]  # From AMM's perspective
    amount_x: Decimal             # Amount of X traded
    amount_y: Decimal             # Amount of Y traded
    timestamp: int                # Simulation step number
    reserve_x: Decimal            # Post-trade X reserves
    reserve_y: Decimal            # Post-trade Y reserves

    @property
    def implied_price(self) -> Decimal:
        """The effective price of this trade (Y per X)."""
        if self.amount_x == 0:
            return Decimal("0")
        return self.amount_y / self.amount_x
