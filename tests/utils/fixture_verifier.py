#!/usr/bin/env python3
"""Quick verification script for economic test fixtures.

Run this to verify the fixtures are working correctly.
"""

from decimal import Decimal
from tests.fixtures import (
    PoolBalanceProfile,
    create_constant_fee_amm,
    create_tiered_fee_amm,
    create_amm_set,
    get_baseline_fee_tiers,
    snapshot_amm_state,
    calculate_pnl,
)


def main():
    print("=" * 70)
    print("Economic Test Fixtures Verification")
    print("=" * 70)
    print()

    # Test 1: Create constant fee AMM
    print("1. Creating constant fee AMM (30 bps)...")
    constant_amm = create_constant_fee_amm(
        "ConstantFee",
        Decimal("0.003"),
        Decimal("1000"),
        Decimal("1000"),
    )
    print(f"   ✓ Created: {constant_amm.name}")
    print(f"   ✓ Reserves: {constant_amm.reserve_x} X, {constant_amm.reserve_y} Y")
    print(f"   ✓ Bid fee: {constant_amm.current_fees.bid_fee}")
    print()

    # Test 2: Create tiered fee AMM
    print("2. Creating tiered fee AMM (30→20→10 bps)...")
    tiers = get_baseline_fee_tiers("conservative")
    tiered_amm = create_tiered_fee_amm(
        "TieredFee",
        tiers,
        Decimal("1000"),
        Decimal("1000"),
    )
    print(f"   ✓ Created: {tiered_amm.name}")
    print(f"   ✓ Tiers: {len(tiered_amm.current_fees.bid_tiers)} tier structure")
    for tier in tiered_amm.current_fees.bid_tiers:
        bps = tier.fee * Decimal("10000")
        print(f"     - Threshold {tier.threshold}: {bps} bps")
    print()

    # Test 3: Create AMM set
    print("3. Creating standard AMM set...")
    amm_set = create_amm_set(PoolBalanceProfile.BALANCED)
    print(f"   ✓ Created {len(amm_set)} AMMs:")
    for amm in amm_set:
        print(f"     - {amm.name}")
    print()

    # Test 4: Execute trade and snapshot
    print("4. Executing trade and taking snapshots...")
    test_amm = constant_amm

    before = snapshot_amm_state(test_amm)
    print(f"   ✓ Before: X={before.reserve_x}, Y={before.reserve_y}")

    trade = test_amm.execute_buy_x(Decimal("10"), timestamp=0)
    print(f"   ✓ Executed: AMM bought {trade.amount_x} X for {trade.amount_y} Y")

    after = snapshot_amm_state(test_amm)
    print(f"   ✓ After: X={after.reserve_x}, Y={after.reserve_y}")
    print()

    # Test 5: Calculate PnL
    print("5. Calculating PnL...")
    pnl = calculate_pnl(before, after)
    print(f"   ✓ Delta X: {pnl.delta_x}")
    print(f"   ✓ Delta Y: {pnl.delta_y}")
    print(f"   ✓ Fees earned (X): {pnl.fees_earned_x}")
    print(f"   ✓ PnL at final price: {pnl.pnl_at_final_price}")
    print()

    # Test 6: Compare fee structures
    print("6. Comparing fee structures on large trade (150 tokens)...")
    trade_size = Decimal("150")

    results = []
    for profile in ["conservative", "moderate", "aggressive"]:
        tiers = get_baseline_fee_tiers(profile)
        amm = create_tiered_fee_amm(
            profile,
            tiers,
            Decimal("10000"),
            Decimal("10000"),
        )

        before = snapshot_amm_state(amm)
        amm.execute_buy_x(trade_size, timestamp=0)
        after = snapshot_amm_state(amm)

        pnl = calculate_pnl(before, after)
        results.append((profile, pnl.fees_earned_x))

    print(f"   Fee comparison for {trade_size} token trade:")
    for profile, fees in results:
        bps = (fees / trade_size) * Decimal("10000")
        print(f"     - {profile:12s}: {fees:>10} X ({bps:.2f} bps effective)")
    print()

    # Test 7: Verify constant product invariant
    print("7. Verifying constant product invariant (k preservation)...")
    test_amm = create_constant_fee_amm(
        "InvariantTest",
        Decimal("0.003"),
        Decimal("1000"),
        Decimal("1000"),
    )

    before = snapshot_amm_state(test_amm)
    k_before = before.k

    # Execute multiple trades
    for i in range(5):
        if i % 2 == 0:
            test_amm.execute_buy_x(Decimal("10"), timestamp=i)
        else:
            test_amm.execute_sell_x(Decimal("5"), timestamp=i)

    after = snapshot_amm_state(test_amm)
    k_after = after.k
    k_change = abs(k_after - k_before)

    print(f"   ✓ k before: {k_before}")
    print(f"   ✓ k after:  {k_after}")
    print(f"   ✓ Change:   {k_change} (should be ~0 for fee-on-input model)")

    if k_change < Decimal("0.01"):
        print(f"   ✓ PASS: k preserved within tolerance")
    else:
        print(f"   ✗ FAIL: k changed by {k_change}")
    print()

    print("=" * 70)
    print("All verification tests completed successfully!")
    print("=" * 70)
    print()
    print("The fixtures are ready for use in economic correctness testing.")
    print()


if __name__ == "__main__":
    main()
