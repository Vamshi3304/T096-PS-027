"""
Unit tests for BR-04: Holdback Rate & Expected Term Sizing.
Rules:
- Default holdback = 12% (0.12).
- Expected term = cap / (holdback * avg_daily_settlement).
- Target range: [120, 270] days.
- If outside, adjust holdback in 1-point steps within 8%–20%.
- If still outside at 20%, reduce advance to fit 270 days.
"""

import pytest

from src.underwriting import calculate_holdback_and_term


def test_br04_default_holdback_within_range():
    """When term at 12% holdback falls cleanly within [120, 270], holdback remains 12%."""
    advance = 360000.0
    factor = 1.12
    cap = advance * factor  # 403,200.0
    avg_daily = 15000.0
    # term = 403200 / (0.12 * 15000) = 403200 / 1800 = 224.0 days
    hb, term, adv, cap_res = calculate_holdback_and_term(advance, factor, avg_daily)
    assert hb == 12.0
    assert term == 224.0
    assert adv == 360000.0
    assert cap_res == 403200.0


def test_br04_exact_270_days_boundary_mch002():
    """Planted edge case: Expected term exactly 270.00 days before holdback adjustment."""
    advance = 311040.0
    factor = 1.25
    cap = advance * factor  # 388,800.0
    avg_daily = 12000.0
    # term = 388800 / (0.12 * 12000) = 388800 / 1440 = 270.00 days exactly!
    hb, term, adv, cap_res = calculate_holdback_and_term(advance, factor, avg_daily)
    assert hb == 12.0
    assert term == 270.00
    assert adv == 311040.0
    assert cap_res == 388800.0


def test_br04_term_too_long_adjusts_holdback_upwards():
    """When term at 12% exceeds 270 days, step holdback upwards."""
    advance = 228000.0
    factor = 1.12
    avg_daily = 6629.834
    # At 12%, term = 255360 / (0.12 * 6629.834) = 321.0 days (>270)
    # Steps to 15% -> term = 256.78 days (<= 270)
    hb, term, adv, cap_res = calculate_holdback_and_term(advance, factor, avg_daily)
    assert hb == 15.0
    assert 120.0 <= term <= 270.0


def test_br04_term_too_short_adjusts_holdback_downwards():
    """When term at 12% is under 120 days, step holdback downwards towards 8%."""
    advance = 100000.0
    factor = 1.12
    cap = 112000.0
    avg_daily = 10000.0
    # At 12%: term = 112000 / (0.12 * 10000) = 93.3 days (< 120)
    # At 9%: term = 112000 / 900 = 124.4 days (>= 120)
    hb, term, adv, cap_res = calculate_holdback_and_term(advance, factor, avg_daily)
    assert hb == 9.0
    assert term >= 120.0


def test_br04_extreme_long_term_reduces_advance():
    """When term exceeds 270 days even at 20% holdback, reduce advance so term = 270 days."""
    advance = 1000000.0
    factor = 1.25
    avg_daily = 1000.0
    # At 20% holdback: daily sweep = 200. Max cap for 270 days = 270 * 200 = 54,000.
    # Advance reduced to 54000 / 1.25 = 43,200.
    hb, term, adv, cap_res = calculate_holdback_and_term(advance, factor, avg_daily)
    assert hb == 20.0
    assert term == 270.0
    assert adv < 1000000.0
    assert cap_res == adv * factor
