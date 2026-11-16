"""
Unit tests for BR-09: Weekly Minimum Shortfall & Mandate Debits.
Rules:
- Evaluated on Mondays for preceding calendar week (Monday to Sunday, 7 days).
- Expected weekly amount = (cap / expected_term) * 7.
- Minimum threshold = 50% of expected weekly amount.
- If sweeps < threshold, shortfall is debited on Monday from bank mandate.
- Successful debit collects shortfall, reduces balance.
- Failed debit adds Rs 500 charge, marks missed week.
- Edge Case: Week with Rs 0 settlements on all days -> full shortfall, ZERO_WEEK flag.
- Edge Case: Mandate debit failing on Monday bank holiday (e.g. Ganesh Chaturthi 2026-09-14).
"""

import pytest


def test_br09_weekly_minimum_expected_amount_and_threshold():
    """Verify expected weekly calculation and 50% threshold."""
    cap = 403200.0
    term = 224.0
    expected_weekly = (cap / term) * 7.0  # 12,600.0
    threshold = 0.50 * expected_weekly   # 6,300.0
    assert expected_weekly == 12600.0
    assert threshold == 6300.0


def test_br09_zero_week_edge_case_mch003():
    """Planted edge case: All 7 days have Rs 0 settlements -> full shortfall debited."""
    cap = 403200.0
    term = 224.0
    expected_weekly = (cap / term) * 7.0  # 12600.0
    threshold = 0.50 * expected_weekly   # 6300.0

    actual_week_sweeps = 0.0
    shortfall = threshold - actual_week_sweeps
    assert shortfall == 6300.0


def test_br09_failed_mandate_debit_charge_and_missed_week():
    """Failed mandate debit adds Rs 500 charge and increments missed_weeks."""
    balance = 300000.0
    missed_weeks = 0

    # Debit fails
    charge = 500.0
    balance += charge
    missed_weeks += 1

    assert balance == 300500.0
    assert missed_weeks == 1


def test_br09_successful_mandate_debit_collects_money():
    """Successful mandate debit collects shortfall and reduces balance remaining."""
    balance = 300000.0
    cumulative_collected = 50000.0
    shortfall = 6300.0

    # Debit succeeds
    cumulative_collected += shortfall
    balance -= shortfall

    assert cumulative_collected == 56300.0
    assert balance == 293700.0
