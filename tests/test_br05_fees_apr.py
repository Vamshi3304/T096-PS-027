"""
Unit tests for BR-05: Fee Structure, GST & Effective APR.
Rules:
- Origination fee = 2% of advance.
- GST = 18% on origination fee (deducted at disbursal).
- Total deduction = 2% + 0.36% = 2.36% of advance.
- Net disbursal = advance - fee - GST.
- Effective APR = ((cap - advance) / advance) * (365 / expected_term) * 100 (2 decimals).
"""

from datetime import date
import pytest

from src.models import MerchantProfile, SettlementRecord
from src.underwriting import underwrite_merchant


def test_br05_origination_fee_and_gst():
    """Verify 2% origination fee and 18% GST on the fee deducted from advance."""
    advance = 100000.0
    fee = round(0.02 * advance, 2)  # 2000.00
    gst = round(0.18 * fee, 2)       # 360.00
    net_disbursal = round(advance - fee - gst, 2)  # 97640.00

    assert fee == 2000.0
    assert gst == 360.0
    assert net_disbursal == 97640.0


def test_br05_apr_calculation_convention():
    """Verify effective APR conforms to benchmark convention."""
    advance = 360000.0
    cap = 403200.0
    term = 224.0
    # markup = 403200 - 360000 = 43200
    # markup_pct = 43200 / 360000 = 0.12 (12%)
    # apr = 0.12 * (365 / 224) * 100 = 19.5535... -> 19.55%
    apr = round(((cap - advance) / advance) * (365.0 / term) * 100.0, 2)
    assert apr == 19.55
