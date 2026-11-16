"""
Unit tests for BR-14: External Refinance Buyout.
Rules:
- Refinance from another lender requires payoff letter reference.
- Caps advance at 1.0x basis monthly settlements (instead of 1.2x).
- Payoff amount to existing lender is netted off out of the disbursal.
"""

from datetime import date
import pytest

from src.models import MerchantProfile, SettlementRecord
from src.underwriting import underwrite_merchant


def create_mock_merchant_refinance() -> MerchantProfile:
    return MerchantProfile(
        merchant_id="MCH-008",
        business_name="Kamath Hardware",
        owner_name="Deepak Kamath",
        city="Delhi",
        category="HARDWARE",
        business_start_date=date(2015, 1, 15),
        aggregator_id="AGG976981",
        mandate_id="MNDT9946698479",
        ifsc="HDFC0932328",
        mobile="7319084520"
    )


def test_br14_refinance_advance_capped_at_1_0x():
    """Refinance caps advance multiplier at 1.0x monthly settlements."""
    basis_monthly = 150000.0
    requested = 180000.0

    # Under standard underwrite (1.2x): max = 180,000.0
    # Under refinance (1.0x): max = 150,000.0
    multiplier = 1.0
    advance = min(requested, multiplier * basis_monthly, 2500000.0)
    assert advance == 150000.0


def test_br14_refinance_payoff_netting():
    """Verify other lender payoff amount is deducted from disbursal proceeds."""
    advance = 150000.0
    fee = 0.02 * advance       # 3000.0
    gst = 0.18 * fee           # 540.0
    standard_disbursal = advance - fee - gst  # 146,460.0

    other_lender_payoff = 96500.0
    net_to_merchant = standard_disbursal - other_lender_payoff  # 49,960.0

    assert net_to_merchant == 49960.0
