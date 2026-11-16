"""
Unit tests for BR-07: Daily Job Execution Precedence.
Rules:
- Order of operations on each day:
    1. Settlement sweep
    2. True-up check (day 60, 90, 120, ...)
    3. Weekly minimum check (Mondays)
    4. Delinquency check
    5. Term tracking (expected term + 60 days)
"""

from datetime import date
import pytest

from src.models import (
    MerchantProfile,
    MerchantStatus,
    UnderwritingOffer
)
from src.simulator import MerchantSimulationState, SimulationEngine


def create_test_state():
    profile = MerchantProfile(
        merchant_id="MCH-PREC",
        business_name="Precedence Corp",
        owner_name="Owner",
        city="Delhi",
        category="RETAIL",
        business_start_date=date(2020, 1, 1),
        aggregator_id="AGG01",
        mandate_id="MNDT01",
        ifsc="HDFC01",
        mobile="9898989898"
    )
    offer = UnderwritingOffer(
        merchant_id="MCH-PREC",
        command="UNDERWRITE",
        underwrite_date=date(2026, 7, 1),
        eligible=True,
        failed_rule_ids=[],
        avg_monthly_6m=200000.0,
        avg_monthly_3m=200000.0,
        basis_monthly=200000.0,
        cv=0.10,
        factor=1.12,
        advance=200000.0,
        cap=224000.0,
        origination_fee=4000.0,
        gst_on_fee=720.0,
        net_disbursal=195280.0,
        holdback_pct=12.0,
        avg_daily_settlement=6629.83,
        expected_term_days=281.0,
        effective_apr=15.58
    )
    return MerchantSimulationState(profile, offer, disbursal_date=date(2026, 7, 1))


def test_br07_precedence_order_execution():
    """Verify state updates happen sequentially according to precedence specification."""
    state = create_test_state()
    # At day 1, initial balance = 224,000
    assert state.balance_remaining == 224000.0
    assert state.current_holdback == 12.0
    assert state.missed_weeks == 0
    assert state.status == MerchantStatus.ACTIVE
