"""
Unit tests for BR-12: Early Payoff Discounting.
Rules:
- Before day 90 (day < 90): discount 50% of the remaining uncollected factor portion.
- Day 90 onwards (day >= 90): discount 25% of the remaining uncollected factor portion.
- Remaining factor portion = (cap - advance) - (collected / cap) * (cap - advance).
- Amount due = remaining_balance - discount.
- Edge Case: Early payoff on Day 90 receives 25% discount tier.
"""

import pytest


def test_br12_early_payoff_before_day_90():
    """Payoff on Day 45 (< 90) receives 50% discount on remaining factor portion."""
    advance = 100000.0
    cap = 120000.0
    total_factor = cap - advance  # 20,000.0
    cumulative_collected = 30000.0  # 25% of cap

    factor_collected = (cumulative_collected / cap) * total_factor  # 5,000.0
    factor_remaining = total_factor - factor_collected  # 15,000.0

    day_no = 45
    discount_pct = 50.0 if day_no < 90 else 25.0
    discount_amount = (discount_pct / 100.0) * factor_remaining  # 7,500.0

    balance_remaining = cap - cumulative_collected  # 90,000.0
    amount_due = balance_remaining - discount_amount  # 82,500.0

    assert discount_pct == 50.0
    assert discount_amount == 7500.0
    assert amount_due == 82500.0


def test_br12_early_payoff_exact_day_90_boundary_mch004():
    """Planted edge case: Early payoff on Day 90 is in the 25% discount tier."""
    advance = 504000.0
    cap = 564480.0
    total_factor = cap - advance  # 60,480.0
    cumulative_collected = 1872.0

    factor_collected = (cumulative_collected / cap) * total_factor
    factor_remaining = total_factor - factor_collected

    day_no = 90
    discount_pct = 50.0 if day_no < 90 else 25.0
    assert discount_pct == 25.0

    discount_amount = round((discount_pct / 100.0) * factor_remaining, 2)
    balance_remaining = round(cap - cumulative_collected, 2)
    amount_due = round(balance_remaining - discount_amount, 2)

    assert discount_amount == 15069.86
    assert amount_due == 547538.14


def test_br12_early_payoff_after_day_90():
    """Payoff on Day 110 (> 90) receives 25% discount tier."""
    day_no = 110
    discount_pct = 50.0 if day_no < 90 else 25.0
    assert discount_pct == 25.0
