"""
Unit tests for BR-02: Advance Amount Sizing.
Rules:
- Max 1.2x basis monthly settlements.
- Cap Rs 25,00,000 (Rs 25 lakh).
- Basis = min(6-month average, last-3-month average).
- Advance = min(requested, 1.2 * basis, 2500000.0).
"""

from datetime import date
import pytest

from src.models import MerchantProfile, SettlementRecord
from src.underwriting import underwrite_merchant


def create_mock_merchant() -> MerchantProfile:
    return MerchantProfile(
        merchant_id="MCH-SIZE",
        business_name="Sizing Merchant",
        owner_name="Owner",
        city="Mumbai",
        category="RETAIL",
        business_start_date=date(2020, 1, 1),
        aggregator_id="AGG100",
        mandate_id="MNDT100",
        ifsc="HDFC0001000",
        mobile="9000000000"
    )


def create_uniform_history(merchant_id: str, monthly_amounts: list[float]) -> list[SettlementRecord]:
    """Generates 181 records spread across 6 months with given monthly totals."""
    records = []
    # 2026-01-01 to 2026-06-30
    days_in_month = [31, 28, 31, 30, 31, 30]
    m_idx = 1
    for m_days, m_total in zip(days_in_month, monthly_amounts):
        daily = m_total / m_days
        for d in range(1, m_days + 1):
            records.append(SettlementRecord(
                merchant_id=merchant_id,
                date=date(2026, m_idx, d),
                gross_sales=daily * 1.015,
                mdr=daily * 0.015,
                refunds=0.0,
                net_settlement=daily
            ))
        m_idx += 1
    return records


def test_br02_standard_sizing_uses_6m_when_lower():
    """When 6-month average is lower than 3-month average, basis = 6m average."""
    merchant = create_mock_merchant()
    # Months 1-3: 150k, Months 4-6: 200k -> 6m avg = 175k, 3m avg = 200k -> basis = 175k
    history = create_uniform_history("MCH-SIZE", [150000.0, 150000.0, 150000.0, 200000.0, 200000.0, 200000.0])
    
    # 1.2 * 175k = 210,000. Requested = 500k -> sized to 210k.
    offer = underwrite_merchant(merchant, history, date(2026, 7, 1), requested_advance=500000.0)
    assert offer.eligible is True
    assert offer.basis_monthly == 175000.0
    assert offer.advance == 210000.0


def test_br02_uses_3m_when_lower_mch004_trap():
    """MCH-004 trap: When last 3 months average is lower than 6m, use the 3m lower basis."""
    merchant = create_mock_merchant()
    # 6m totals: [500k, 500k, 500k, 420k, 420k, 420k]
    # 6m avg = 460k, 3m avg = 420k -> basis = 420k.
    # 1.2 * 420k = 504,000. Requested = 900,000 -> sized to 504,000.
    history = create_uniform_history("MCH-SIZE", [500000.0, 500000.0, 500000.0, 420000.0, 420000.0, 420000.0])
    
    offer = underwrite_merchant(merchant, history, date(2026, 7, 1), requested_advance=900000.0)
    assert offer.eligible is True
    assert offer.avg_monthly_6m == 460000.0
    assert offer.avg_monthly_3m == 420000.0
    assert offer.basis_monthly == 420000.0
    assert offer.advance == 504000.0


def test_br02_capped_at_25_lakh():
    """Advance cannot exceed the absolute statutory ceiling of Rs 25,00,000."""
    merchant = create_mock_merchant()
    # High volume merchant: 30 lakh per month -> 1.2x would be 36 lakh.
    history = create_uniform_history("MCH-SIZE", [3000000.0] * 6)
    
    offer = underwrite_merchant(merchant, history, date(2026, 7, 1), requested_advance=5000000.0)
    assert offer.eligible is True
    assert offer.basis_monthly == 3000000.0
    assert offer.advance == 2500000.0  # Capped at 25 Lakh


def test_br02_requested_lower_than_eligibility_cap():
    """If merchant requests less than the maximum eligible amount, requested is granted."""
    merchant = create_mock_merchant()
    history = create_uniform_history("MCH-SIZE", [500000.0] * 6)
    # 1.2 * 500k = 600,000 eligible. Requested = 200,000.
    offer = underwrite_merchant(merchant, history, date(2026, 7, 1), requested_advance=200000.0)
    assert offer.eligible is True
    assert offer.advance == 200000.0
