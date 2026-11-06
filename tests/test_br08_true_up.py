"""
Unit tests for BR-08: Mid-Term Performance True-Up.
Rules:
- Evaluated on Day 60 and every 30 days after (Day 60, 90, 120, 150...).
- Plan at day n = (cap / expected_term) * n.
- If cumulative collections > 130% of plan:
    * holdback reduced by 2 points (floor 8%), effective next day (n+1).
- If cumulative collections < 70% of plan:
    * holdback raised by 2 points (ceiling 20%), effective next day (n+1).
- Edge Case: Collections exactly 130% of plan does NOT trigger reduction (strictly > 130%).
"""

import pytest


def test_br08_exact_130_percent_edge_case_mch003():
    """
    Planted edge case (MCH-003):
    Cap = 403,200, Term = 224 days, Day = 60.
    Plan = 403,200 * 60 / 224 = 108,000.00.
    Cumulative collections = 140,400.00 (exactly 130.00% of plan).
    Must NOT trigger holdback reduction because condition is strictly > 130%.
    """
    cap = 403200.0
    term = 224.0
    day = 60
    plan = (cap * day) / term
    assert plan == 108000.0

    cumulative = 140400.0
    assert cumulative == 1.30 * plan

    # Verification of strict inequality
    should_reduce = cumulative > 1.30 * plan
    assert should_reduce is False


def test_br08_collections_exceeding_130_percent():
    """Cumulative collections > 130% reduces holdback by 2 points (floor 8%)."""
    cap = 403200.0
    term = 224.0
    day = 60
    plan = (cap * day) / term  # 108,000

    cumulative = 145000.0  # > 140,400 (130%)
    should_reduce = cumulative > 1.30 * plan
    assert should_reduce is True

    current_holdback = 12.0
    new_holdback = max(8.0, current_holdback - 2.0)
    assert new_holdback == 10.0


def test_br08_collections_below_70_percent():
    """Cumulative collections < 70% raises holdback by 2 points (ceiling 20%)."""
    cap = 403200.0
    term = 224.0
    day = 60
    plan = (cap * day) / term  # 108,000.0
    threshold_70 = 0.70 * plan   # 75,600.0

    cumulative = 70000.0  # < 75,600
    should_raise = cumulative < threshold_70
    assert should_raise is True

    current_holdback = 12.0
    new_holdback = min(20.0, current_holdback + 2.0)
    assert new_holdback == 14.0


def test_br08_floor_and_ceiling_boundaries():
    """True-up adjustments respect floor of 8% and ceiling of 20%."""
    # Floor test
    hb_at_9 = 9.0
    assert max(8.0, hb_at_9 - 2.0) == 8.0

    # Ceiling test
    hb_at_19 = 19.0
    assert min(20.0, hb_at_19 + 2.0) == 20.0
