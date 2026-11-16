"""
Unit tests for BR-01: Merchant Eligibility.
Rules:
- At least 6 months of settlement history (>= 180 days).
- Average monthly settlements >= Rs 1,00,000.
- No month with settlements < 40% of the 6-month average.
- Business age >= 12 full months on underwrite date.
"""

from datetime import date
import pytest

from src.models import MerchantProfile
from src.underwriting import (
    calculate_business_age_months,
    evaluate_eligibility
)


def create_sample_profile(business_start_date: str) -> MerchantProfile:
    return MerchantProfile(
        merchant_id="MCH-TEST",
        business_name="Test Enterprise",
        owner_name="Test Owner",
        city="Bengaluru",
        category="RETAIL",
        business_start_date=date.fromisoformat(business_start_date),
        aggregator_id="AGG001",
        mandate_id="MNDT001",
        ifsc="HDFC0001234",
        mobile="9876543210"
    )


def test_br01_happy_path_eligible():
    """All 4 eligibility criteria satisfied."""
    profile = create_sample_profile("2024-01-01")
    monthly_totals = [150000.0, 160000.0, 140000.0, 155000.0, 165000.0, 170000.0]
    total_days = 181
    as_of = date(2026, 7, 1)
    cv = 0.10

    eligible, fails = evaluate_eligibility(profile, monthly_totals, total_days, as_of, cv)
    assert eligible is True
    assert fails == []


def test_br01_fail_insufficient_history_days():
    """Less than 180 days of history fails BR-01."""
    profile = create_sample_profile("2024-01-01")
    monthly_totals = [150000.0, 160000.0, 140000.0, 155000.0, 165000.0, 170000.0]
    total_days = 150  # Less than 180
    as_of = date(2026, 7, 1)
    cv = 0.10

    eligible, fails = evaluate_eligibility(profile, monthly_totals, total_days, as_of, cv)
    assert eligible is False
    assert "BR-01" in fails


def test_br01_fail_insufficient_months():
    """Fewer than 6 calendar months fails BR-01."""
    profile = create_sample_profile("2024-01-01")
    monthly_totals = [150000.0, 160000.0, 140000.0, 155000.0, 165000.0]  # Only 5 months
    total_days = 181
    as_of = date(2026, 7, 1)
    cv = 0.10

    eligible, fails = evaluate_eligibility(profile, monthly_totals, total_days, as_of, cv)
    assert eligible is False
    assert "BR-01" in fails


def test_br01_fail_average_settlement_below_1_lakh():
    """Average monthly settlements < Rs 1,00,000 fails BR-01."""
    profile = create_sample_profile("2024-01-01")
    monthly_totals = [90000.0, 95000.0, 92000.0, 94000.0, 96000.0, 93000.0]
    total_days = 181
    as_of = date(2026, 7, 1)
    cv = 0.10

    eligible, fails = evaluate_eligibility(profile, monthly_totals, total_days, as_of, cv)
    assert eligible is False
    assert "BR-01" in fails


def test_br01_fail_month_below_40_percent_of_average():
    """MCH-009 scenario: A month with settlements < 40% of 6m average fails BR-01."""
    profile = create_sample_profile("2024-01-01")
    # Average = 160,000. 40% of average = 64,000. Month 3 has 60,000 < 64,000.
    monthly_totals = [180000.0, 190000.0, 60000.0, 175000.0, 185000.0, 170000.0]
    total_days = 181
    as_of = date(2026, 7, 1)
    cv = 0.28

    eligible, fails = evaluate_eligibility(profile, monthly_totals, total_days, as_of, cv)
    assert eligible is False
    assert "BR-01" in fails


def test_br01_fail_business_age_below_12_months():
    """MCH-010 scenario: Business age 11 months (< 12 months) fails BR-01."""
    profile = create_sample_profile("2025-08-01")
    as_of = date(2026, 7, 1)
    age = calculate_business_age_months(profile.business_start_date, as_of)
    assert age == 11

    monthly_totals = [200000.0, 210000.0, 220000.0, 205000.0, 215000.0, 225000.0]
    total_days = 181
    cv = 0.05

    eligible, fails = evaluate_eligibility(profile, monthly_totals, total_days, as_of, cv)
    assert eligible is False
    assert "BR-01" in fails


def test_br01_business_age_exact_12_months():
    """Exact 12 months business age passes BR-01."""
    profile = create_sample_profile("2025-07-01")
    as_of = date(2026, 7, 1)
    age = calculate_business_age_months(profile.business_start_date, as_of)
    assert age == 12

    monthly_totals = [200000.0, 210000.0, 220000.0, 205000.0, 215000.0, 225000.0]
    total_days = 181
    cv = 0.05

    eligible, fails = evaluate_eligibility(profile, monthly_totals, total_days, as_of, cv)
    assert eligible is True
    assert fails == []
