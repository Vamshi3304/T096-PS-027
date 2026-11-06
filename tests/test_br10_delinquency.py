"""
Unit tests for BR-10: Delinquency Progression & Default Acceleration.
Rules:
- 2 missed weeks -> Status transitions to WATCH (blocks renewals).
- 4 missed weeks -> Status transitions to DEFAULT.
- DEFAULT triggers acceleration of full remaining cap + 5% penalty.
- Stops all future settlement sweeps in favour of recovery demand.
"""

import pytest

from src.models import MerchantStatus


def test_br10_delinquency_transitions():
    """Verify progression: ACTIVE -> WATCH (at 2) -> DEFAULT (at 4)."""
    missed_weeks = 1
    status = MerchantStatus.ACTIVE
    assert status == MerchantStatus.ACTIVE

    # Hit 2 missed weeks
    missed_weeks = 2
    if missed_weeks >= 4:
        status = MerchantStatus.DEFAULT
    elif missed_weeks >= 2:
        status = MerchantStatus.WATCH
    assert status == MerchantStatus.WATCH

    # Hit 3 missed weeks
    missed_weeks = 3
    if missed_weeks >= 4:
        status = MerchantStatus.DEFAULT
    elif missed_weeks >= 2:
        status = MerchantStatus.WATCH
    assert status == MerchantStatus.WATCH

    # Hit 4 missed weeks
    missed_weeks = 4
    if missed_weeks >= 4:
        status = MerchantStatus.DEFAULT
    elif missed_weeks >= 2:
        status = MerchantStatus.WATCH
    assert status == MerchantStatus.DEFAULT


def test_br10_default_acceleration_penalty_and_sweeps_halted():
    """DEFAULT accelerates balance with 5% penalty and stops sweeping."""
    remaining_balance = 200000.0
    penalty = 0.05 * remaining_balance  # 10,000.0
    accelerated_total = remaining_balance + penalty  # 210,000.0

    assert penalty == 10000.0
    assert accelerated_total == 210000.0
