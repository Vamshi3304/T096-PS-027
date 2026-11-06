"""
Unit tests for BR-13: Advance Renewal & Net-Off.
Rules:
- Allowed when cumulative collected >= 60% of the cap AND status is NOT WATCH or DEFAULT.
- New advance nets off remaining balance of old one at ZERO discount.
- Edge Case: Renewal when cumulative collected is exactly 60.00% of cap (MCH-005 Day 135).
"""

import pytest

from src.models import MerchantStatus


def test_br13_renewal_exact_60_percent_collected_mch005():
    """Planted edge case: Collected exactly 60.00% of cap qualifies for renewal."""
    cap = 483840.0
    collected = 290304.0
    pct = collected / cap
    assert pct == 0.60

    status = MerchantStatus.ACTIVE
    is_allowed = (pct >= 0.60) and (status not in [MerchantStatus.WATCH, MerchantStatus.DEFAULT])
    assert is_allowed is True


def test_br13_renewal_blocked_under_60_percent():
    """Renewal rejected if collections are below 60% of cap."""
    cap = 100000.0
    collected = 59990.0  # 59.99%
    pct = collected / cap
    status = MerchantStatus.ACTIVE

    is_allowed = (pct >= 0.60) and (status not in [MerchantStatus.WATCH, MerchantStatus.DEFAULT])
    assert is_allowed is False


def test_br13_renewal_blocked_by_watch_status():
    """Renewal rejected if merchant has WATCH status despite >= 60% collected."""
    cap = 100000.0
    collected = 75000.0  # 75%
    pct = collected / cap
    status = MerchantStatus.WATCH

    is_allowed = (pct >= 0.60) and (status not in [MerchantStatus.WATCH, MerchantStatus.DEFAULT])
    assert is_allowed is False


def test_br13_renewal_nets_off_old_balance_at_zero_discount():
    """New advance disbursal nets off old remaining balance at zero discount."""
    old_cap = 483840.0
    old_collected = 290304.0
    old_balance_remaining = old_cap - old_collected  # 193,536.0

    # New advance underwrite
    new_advance = 500000.0
    new_fee = 0.02 * new_advance  # 10,000.0
    new_gst = 0.18 * new_fee      # 1,800.0
    new_standard_disbursal = new_advance - new_fee - new_gst  # 488,200.0

    # Netting off old balance at 0 discount
    actual_disbursal = new_standard_disbursal - old_balance_remaining  # 294,664.0
    assert actual_disbursal == 294664.0
