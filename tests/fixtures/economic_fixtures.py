"""Economic test fixtures for AMM testing.

Provides utilities to create AMMs with various fee structures and pool balances,
and to perform accurate economic accounting using Decimal precision.

Standard fee profiles:
- Conservative: [(0, 0.003), (100, 0.002), (1000, 0.001)] (30→20→10 bps)
- Moderate: [(0, 0.003), (100, 0.0015), (1000, 0.0005)] (30→15→5 bps)
- Aggressive: [(0, 0.005), (100, 0.001), (1000, 0.0001)] (50→10→1 bps)
- Pathological: [(0, 0.1), (1, 0.0001), (2, 0.00001)] (steep transitions)

Pool balance profiles:
- Balanced: equal X and Y (10000, 10000)
- Skewed_x: more X (20000, 5000)
- Skewed_y: more Y (5000, 20000)
- Extreme: very imbalanced (1, 1000000)
"""

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Optional

from amm_competition.core.amm import AMM
from amm_competition.core.interfaces import AMMStrategy
from amm_competition.core.trade import FeeQuote, FeeTier


class PoolBalanceProfile(Enum):
    """Standard pool balance configurations for testing."""
    BALANCED = "balanced"      # Equal reserves
    SKEWED_X = "skewed_x"      # More X than Y
    SKEWED_Y = "skewed_y"      # More Y than X
    EXTREME = "extreme"        # Very imbalanced


@dataclass(frozen=True)
class AMMStateSnapshot:
    """Immutable snapshot of AMM state for PnL calculation.

    Captures all relevant state at a point in time to enable
    accurate profit/loss calculations using Decimal precision.
    """
    name: str
    reserve_x: Decimal
    reserve_y: Decimal
    accumulated_fees_x: Decimal
    accumulated_fees_y: Decimal
    k: Decimal  # Constant product invariant

    @property
    def total_x(self) -> Decimal:
        """Total X including reserves and accumulated fees."""
        return self.reserve_x + self.accumulated_fees_x

    @property
    def total_y(self) -> Decimal:
        """Total Y including reserves and accumulated fees."""
        return self.reserve_y + self.accumulated_fees_y

    @property
    def spot_price(self) -> Decimal:
        """Current spot price (Y per X) before fees."""
        if self.reserve_x == 0:
            return Decimal("0")
        return self.reserve_y / self.reserve_x


@dataclass(frozen=True)
class PnLResult:
    """Profit and loss calculation result.

    All values in Decimal for precision. Positive values indicate
    gains, negative values indicate losses.
    """
    amm_name: str
    delta_x: Decimal           # Change in X (reserves + fees)
    delta_y: Decimal           # Change in Y (reserves + fees)
    delta_reserve_x: Decimal   # Change in X reserves only
    delta_reserve_y: Decimal   # Change in Y reserves only
    fees_earned_x: Decimal     # Fees collected in X
    fees_earned_y: Decimal     # Fees collected in Y
    pnl_at_initial_price: Decimal   # PnL valued at initial price
    pnl_at_final_price: Decimal     # PnL valued at final price

    @property
    def total_fees_in_y(self) -> Decimal:
        """Total fees valued in Y at final price."""
        # Convert X fees to Y equivalent
        # This requires knowing the price, which should be in the snapshot
        return self.fees_earned_y  # Simplified for now


class _MockStrategy:
    """Internal mock strategy for testing that returns fixed fees.

    This is a simple implementation that always returns the same
    FeeQuote, useful for controlled testing scenarios.
    """

    def __init__(self, name: str, fee_quote: FeeQuote):
        self._name = name
        self._fee_quote = fee_quote

    def get_name(self) -> str:
        return self._name

    def after_initialize(self, initial_x: Decimal, initial_y: Decimal) -> FeeQuote:
        return self._fee_quote

    def after_swap(self, trade) -> FeeQuote:
        return self._fee_quote

    def reset(self):
        pass


def create_constant_fee_amm(
    name: str,
    fee_rate: Decimal,
    reserve_x: Decimal,
    reserve_y: Decimal,
    asymmetric: bool = False,
    ask_fee_rate: Optional[Decimal] = None,
) -> AMM:
    """Create an AMM with constant fees (no tiers).

    Args:
        name: Display name for the AMM
        fee_rate: Base fee rate for both bid and ask (e.g., 0.003 = 30bps)
        reserve_x: Initial X reserve amount
        reserve_y: Initial Y reserve amount
        asymmetric: If True, use different bid/ask fees
        ask_fee_rate: Ask fee rate if asymmetric (defaults to fee_rate)

    Returns:
        Initialized AMM with constant fee structure

    Example:
        >>> amm = create_constant_fee_amm("ConstantFee", Decimal("0.003"),
        ...                               Decimal("1000"), Decimal("1000"))
        >>> amm.current_fees.bid_fee
        Decimal('0.003')
    """
    if asymmetric and ask_fee_rate is None:
        ask_fee_rate = fee_rate

    fee_quote = FeeQuote(
        bid_fee=fee_rate,
        ask_fee=ask_fee_rate if asymmetric else fee_rate,
    )

    strategy = _MockStrategy(name, fee_quote)
    amm = AMM(strategy=strategy, reserve_x=reserve_x, reserve_y=reserve_y, name=name)
    amm.initialize()
    return amm


def create_tiered_fee_amm(
    name: str,
    fee_tiers: list[tuple[Decimal, Decimal]],
    reserve_x: Decimal,
    reserve_y: Decimal,
    symmetric: bool = True,
    ask_tiers: Optional[list[tuple[Decimal, Decimal]]] = None,
) -> AMM:
    """Create an AMM with tiered fee structure.

    Args:
        name: Display name for the AMM
        fee_tiers: List of (threshold, fee_rate) tuples for bid direction
                   First tier must have threshold 0
                   Maximum 3 tiers allowed
        reserve_x: Initial X reserve amount
        reserve_y: Initial Y reserve amount
        symmetric: If True, use same tiers for bid and ask
        ask_tiers: Ask tier structure if asymmetric (defaults to fee_tiers)

    Returns:
        Initialized AMM with tiered fee structure

    Example:
        >>> tiers = [(Decimal("0"), Decimal("0.003")),
        ...          (Decimal("100"), Decimal("0.002")),
        ...          (Decimal("1000"), Decimal("0.001"))]
        >>> amm = create_tiered_fee_amm("TieredFee", tiers,
        ...                             Decimal("1000"), Decimal("1000"))

    Raises:
        ValueError: If tiers are invalid (empty, too many, wrong thresholds)
    """
    if not fee_tiers:
        raise ValueError("fee_tiers cannot be empty")
    if len(fee_tiers) > 3:
        raise ValueError(f"Maximum 3 tiers allowed, got {len(fee_tiers)}")
    if fee_tiers[0][0] != 0:
        raise ValueError(f"First tier must have threshold 0, got {fee_tiers[0][0]}")

    # Convert tuples to FeeTier objects
    bid_tier_objects = [
        FeeTier(threshold=threshold, fee=fee)
        for threshold, fee in fee_tiers
    ]

    if symmetric:
        ask_tier_objects = bid_tier_objects
    else:
        if ask_tiers is None:
            ask_tiers = fee_tiers
        ask_tier_objects = [
            FeeTier(threshold=threshold, fee=fee)
            for threshold, fee in ask_tiers
        ]

    # Use the base fee from the first tier as the fallback constant fee
    base_bid_fee = fee_tiers[0][1]
    base_ask_fee = ask_tiers[0][1] if ask_tiers else base_bid_fee

    fee_quote = FeeQuote(
        bid_fee=base_bid_fee,
        ask_fee=base_ask_fee,
        bid_tiers=bid_tier_objects,
        ask_tiers=ask_tier_objects,
    )

    strategy = _MockStrategy(name, fee_quote)
    amm = AMM(strategy=strategy, reserve_x=reserve_x, reserve_y=reserve_y, name=name)
    amm.initialize()
    return amm


def get_baseline_fee_tiers(profile: str) -> list[tuple[Decimal, Decimal]]:
    """Get standard fee tier profiles for testing.

    Args:
        profile: One of "conservative", "moderate", "aggressive", "pathological"

    Returns:
        List of (threshold, fee_rate) tuples

    Profiles:
        - conservative: Gradual fee reduction (30→20→10 bps)
        - moderate: Moderate fee reduction (30→15→5 bps)
        - aggressive: Steep fee reduction (50→10→1 bps)
        - pathological: Extreme transitions for edge case testing (100→1→0.1 bps)

    Example:
        >>> tiers = get_baseline_fee_tiers("conservative")
        >>> tiers[0]
        (Decimal('0'), Decimal('0.003'))

    Raises:
        ValueError: If profile is not recognized
    """
    profiles = {
        "conservative": [
            (Decimal("0"), Decimal("0.003")),      # 30 bps
            (Decimal("100"), Decimal("0.002")),    # 20 bps
            (Decimal("1000"), Decimal("0.001")),   # 10 bps
        ],
        "moderate": [
            (Decimal("0"), Decimal("0.003")),      # 30 bps
            (Decimal("100"), Decimal("0.0015")),   # 15 bps
            (Decimal("1000"), Decimal("0.0005")),  # 5 bps
        ],
        "aggressive": [
            (Decimal("0"), Decimal("0.005")),      # 50 bps
            (Decimal("100"), Decimal("0.001")),    # 10 bps
            (Decimal("1000"), Decimal("0.0001")),  # 1 bps
        ],
        "pathological": [
            (Decimal("0"), Decimal("0.1")),        # 10000 bps (100%)
            (Decimal("1"), Decimal("0.0001")),     # 1 bps
            (Decimal("2"), Decimal("0.00001")),    # 0.1 bps
        ],
    }

    if profile not in profiles:
        raise ValueError(
            f"Unknown profile '{profile}'. "
            f"Valid options: {', '.join(profiles.keys())}"
        )

    return profiles[profile]


def get_pool_balance(profile: PoolBalanceProfile) -> tuple[Decimal, Decimal]:
    """Get standard pool balance configurations.

    Args:
        profile: Pool balance profile enum

    Returns:
        Tuple of (reserve_x, reserve_y)

    Example:
        >>> x, y = get_pool_balance(PoolBalanceProfile.BALANCED)
        >>> x == y
        True
    """
    balances = {
        PoolBalanceProfile.BALANCED: (Decimal("10000"), Decimal("10000")),
        PoolBalanceProfile.SKEWED_X: (Decimal("20000"), Decimal("5000")),
        PoolBalanceProfile.SKEWED_Y: (Decimal("5000"), Decimal("20000")),
        PoolBalanceProfile.EXTREME: (Decimal("1"), Decimal("1000000")),
    }
    return balances[profile]


def create_amm_set(
    balance_profile: PoolBalanceProfile = PoolBalanceProfile.BALANCED,
    include_constant: bool = True,
    include_tiered: bool = True,
) -> list[AMM]:
    """Create a standard set of AMMs for testing.

    Creates AMMs with various fee structures using consistent pool balances.
    Useful for comparative testing and routing verification.

    Args:
        balance_profile: Which balance profile to use for all AMMs
        include_constant: Whether to include constant fee AMM
        include_tiered: Whether to include tiered fee AMMs

    Returns:
        List of initialized AMMs with different fee structures

    Standard set includes:
        - ConstantFee: 30bps flat
        - TwoTier: 30bps → 20bps
        - ThreeTier: 30bps → 20bps → 10bps
        - Aggressive: 50bps → 10bps → 1bps
        - Pathological: 100% → 1bps → 0.1bps

    Example:
        >>> amms = create_amm_set(PoolBalanceProfile.BALANCED)
        >>> len(amms)
        5
        >>> amms[0].name
        'ConstantFee'
    """
    reserve_x, reserve_y = get_pool_balance(balance_profile)
    amms = []

    if include_constant:
        # Constant 30bps
        amms.append(create_constant_fee_amm(
            "ConstantFee",
            Decimal("0.003"),
            reserve_x,
            reserve_y,
        ))

    if include_tiered:
        # Two-tier: 30bps → 20bps
        amms.append(create_tiered_fee_amm(
            "TwoTier",
            [
                (Decimal("0"), Decimal("0.003")),
                (Decimal("100"), Decimal("0.002")),
            ],
            reserve_x,
            reserve_y,
        ))

        # Three-tier conservative: 30bps → 20bps → 10bps
        amms.append(create_tiered_fee_amm(
            "ThreeTier",
            get_baseline_fee_tiers("conservative"),
            reserve_x,
            reserve_y,
        ))

        # Aggressive: 50bps → 10bps → 1bps
        amms.append(create_tiered_fee_amm(
            "Aggressive",
            get_baseline_fee_tiers("aggressive"),
            reserve_x,
            reserve_y,
        ))

        # Pathological: extreme transitions for edge case testing
        amms.append(create_tiered_fee_amm(
            "Pathological",
            get_baseline_fee_tiers("pathological"),
            reserve_x,
            reserve_y,
        ))

    return amms


def snapshot_amm_state(amm: AMM) -> AMMStateSnapshot:
    """Capture current AMM state for later PnL calculation.

    Creates an immutable snapshot of all relevant AMM state including
    reserves, accumulated fees, and the constant product invariant.

    Args:
        amm: AMM instance to snapshot

    Returns:
        Immutable state snapshot

    Example:
        >>> amm = create_constant_fee_amm("Test", Decimal("0.003"),
        ...                               Decimal("1000"), Decimal("1000"))
        >>> snapshot = snapshot_amm_state(amm)
        >>> snapshot.reserve_x
        Decimal('1000')
    """
    return AMMStateSnapshot(
        name=amm.name,
        reserve_x=amm.reserve_x,
        reserve_y=amm.reserve_y,
        accumulated_fees_x=amm.accumulated_fees_x,
        accumulated_fees_y=amm.accumulated_fees_y,
        k=amm.k,
    )


def calculate_pnl(
    before: AMMStateSnapshot,
    after: AMMStateSnapshot,
    valuation_price: Optional[Decimal] = None,
) -> PnLResult:
    """Calculate profit and loss between two state snapshots.

    Computes changes in reserves and fees, and values PnL at both
    initial and final prices. All calculations use Decimal precision.

    Args:
        before: State snapshot before the trading period
        after: State snapshot after the trading period
        valuation_price: Optional price (Y per X) to value PnL at
                        If None, uses initial and final spot prices

    Returns:
        PnLResult with detailed breakdown of changes

    Example:
        >>> before = snapshot_amm_state(amm)
        >>> # ... execute some trades ...
        >>> after = snapshot_amm_state(amm)
        >>> pnl = calculate_pnl(before, after)
        >>> pnl.delta_x
        Decimal('-50.5')  # AMM sold X

    Notes:
        - Positive delta_x means AMM gained X (trader sold X to AMM)
        - Positive delta_y means AMM gained Y (trader sold Y to AMM)
        - Fees are always positive (money earned)
        - PnL calculation accounts for both reserves and accumulated fees
    """
    if before.name != after.name:
        raise ValueError(
            f"Snapshots from different AMMs: '{before.name}' vs '{after.name}'"
        )

    # Calculate changes in reserves
    delta_reserve_x = after.reserve_x - before.reserve_x
    delta_reserve_y = after.reserve_y - before.reserve_y

    # Calculate fees earned during period
    fees_earned_x = after.accumulated_fees_x - before.accumulated_fees_x
    fees_earned_y = after.accumulated_fees_y - before.accumulated_fees_y

    # Total change includes both reserves and fees
    delta_x = delta_reserve_x + fees_earned_x
    delta_y = delta_reserve_y + fees_earned_y

    # Calculate PnL at initial price (Y per X)
    initial_price = before.spot_price
    if valuation_price is not None:
        initial_price = valuation_price

    # PnL = value of what we gained - value of what we lost
    # Positive PnL means we profited
    # For AMM: gained Y, lost X → PnL = delta_y - delta_x * price
    # But if delta_x > 0, we gained X, so we value it positively
    pnl_at_initial = delta_y + delta_x * initial_price

    # Calculate PnL at final price
    final_price = after.spot_price
    if valuation_price is not None:
        final_price = valuation_price

    pnl_at_final = delta_y + delta_x * final_price

    return PnLResult(
        amm_name=after.name,
        delta_x=delta_x,
        delta_y=delta_y,
        delta_reserve_x=delta_reserve_x,
        delta_reserve_y=delta_reserve_y,
        fees_earned_x=fees_earned_x,
        fees_earned_y=fees_earned_y,
        pnl_at_initial_price=pnl_at_initial,
        pnl_at_final_price=pnl_at_final,
    )
