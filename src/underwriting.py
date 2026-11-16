"""
Underwriting, Eligibility, Pricing, and Advance Sizing Engine for PS-027.
Implements BR-01, BR-02, BR-03, BR-04, BR-05, and BR-14.
"""

from datetime import date
import math
import statistics
from typing import Dict, List, Optional, Tuple

from .models import MerchantProfile, SettlementRecord, UnderwritingOffer


def calculate_business_age_months(start_date: date, as_of_date: date) -> int:
    """
    Calculate the number of full months between business_start_date and as_of_date.
    """
    months = (as_of_date.year - start_date.year) * 12 + (as_of_date.month - start_date.month)
    if as_of_date.day < start_date.day:
        months -= 1
    return months


def aggregate_settlement_history(
    history: List[SettlementRecord]
) -> Tuple[List[float], float, int]:
    """
    Aggregates settlement history into:
    1. List of 6 calendar month totals (ordered chronologically)
    2. Total settlement across all days
    3. Total count of settlement days (181 for 6 months)
    """
    by_month: Dict[str, float] = {}
    total_sum = 0.0
    for rec in history:
        month_key = rec.date.strftime("%Y-%m")
        by_month[month_key] = by_month.get(month_key, 0.0) + rec.net_settlement
        total_sum += rec.net_settlement
    
    # Sort months chronologically
    sorted_months = sorted(by_month.keys())
    monthly_totals = [by_month[m] for m in sorted_months]
    return monthly_totals, total_sum, len(history)


def evaluate_eligibility(
    profile: MerchantProfile,
    monthly_totals: List[float],
    total_days: int,
    as_of_date: date,
    cv: float
) -> Tuple[bool, List[str]]:
    """
    Evaluates BR-01 (Eligibility) and BR-03 (CV ceiling).
    BR-01:
    - At least 6 months of settlement history (total_days >= 180 and len(monthly_totals) >= 6)
    - Average monthly settlements >= Rs 1,00,000 (1 lakh)
    - No month with settlements < 40% of the 6-month average
    - Business age >= 12 months
    BR-03:
    - CV <= 0.45 (above 0.45 is not eligible)
    """
    failed_rules: List[str] = []
    
    # History length check
    if len(monthly_totals) < 6 or total_days < 180:
        failed_rules.append("BR-01")
    
    # 6-month average check
    avg_6m = sum(monthly_totals) / 6.0 if len(monthly_totals) >= 6 else 0.0
    if avg_6m < 100000.0:
        if "BR-01" not in failed_rules:
            failed_rules.append("BR-01")
            
    # Monthly 40% floor check
    floor_40 = 0.40 * avg_6m
    for m_tot in monthly_totals:
        if m_tot < floor_40:
            if "BR-01" not in failed_rules:
                failed_rules.append("BR-01")
            break
            
    # Business age check
    age_months = calculate_business_age_months(profile.business_start_date, as_of_date)
    if age_months < 12:
        if "BR-01" not in failed_rules:
            failed_rules.append("BR-01")
            
    # CV Risk Band Eligibility check (BR-03)
    if cv > 0.45:
        failed_rules.append("BR-03")
        
    is_eligible = len(failed_rules) == 0
    return is_eligible, failed_rules


def compute_factor_rate(cv: float) -> Optional[float]:
    """
    BR-03: Factor rate by risk band.
    CV <= 0.15 -> factor 1.12
    0.15 < CV <= 0.30 -> factor 1.18
    0.30 < CV <= 0.45 -> factor 1.25
    CV > 0.45 -> None (ineligible)
    """
    if cv <= 0.15:
        return 1.12
    elif cv <= 0.30:
        return 1.18
    elif cv <= 0.45:
        return 1.25
    else:
        return None


def calculate_holdback_and_term(
    advance: float,
    factor: float,
    avg_daily_settlement: float
) -> Tuple[float, float, float, float]:
    """
    BR-04:
    Default holdback = 12% (12.0).
    Expected term = cap / (holdback * avg_daily_settlement).
    Target term range: [120.0, 270.0] days.
    If outside, adjust holdback in 1-point steps within [8.0, 20.0].
    If still outside after hitting limits, adjust advance so term = 270.0 days.
    Returns: (holdback_pct, expected_term_days, final_advance, final_cap)
    """
    cap = advance * factor
    holdback = 12.0  # percentage
    term = cap / ((holdback / 100.0) * avg_daily_settlement)
    
    # If term > 270 days, step holdback up to 20%
    if term > 270.0:
        while holdback < 20.0 and term > 270.0:
            holdback += 1.0
            term = cap / ((holdback / 100.0) * avg_daily_settlement)
        # If still > 270 at 20% holdback, reduce advance
        if term > 270.0:
            advance = (270.0 * 0.20 * avg_daily_settlement) / factor
            cap = advance * factor
            term = cap / (0.20 * avg_daily_settlement)
            
    # If term < 120 days, step holdback down to 8%
    elif term < 120.0:
        while holdback > 8.0 and term < 120.0:
            holdback -= 1.0
            term = cap / ((holdback / 100.0) * avg_daily_settlement)
            
    return holdback, round(term, 2), round(advance, 2), round(cap, 2)


def underwrite_merchant(
    profile: MerchantProfile,
    history: List[SettlementRecord],
    as_of_date: date,
    requested_advance: float,
    command: str = "UNDERWRITE",
    is_refinance: bool = False
) -> UnderwritingOffer:
    """
    Full Underwriting routine implementing BR-01, BR-02, BR-03, BR-04, BR-05, and BR-14.
    """
    monthly_totals, total_sum, total_days = aggregate_settlement_history(history)
    
    # Metrics
    if len(monthly_totals) >= 6:
        avg_6m = sum(monthly_totals[:6]) / 6.0
        avg_3m = sum(monthly_totals[3:6]) / 3.0
        mean = statistics.mean(monthly_totals[:6])
        pstdev = statistics.pstdev(monthly_totals[:6])
        cv = round(pstdev / mean, 4)
    else:
        avg_6m = 0.0
        avg_3m = 0.0
        cv = 0.0
        
    basis_monthly = min(avg_6m, avg_3m)
    avg_daily_settlement = total_sum / total_days if total_days > 0 else 0.0
    
    # Check eligibility
    is_eligible, failed_rules = evaluate_eligibility(
        profile, monthly_totals, total_days, as_of_date, cv
    )
    
    factor = compute_factor_rate(cv) if is_eligible else None
    
    if not is_eligible or factor is None:
        return UnderwritingOffer(
            merchant_id=profile.merchant_id,
            command=command,
            underwrite_date=as_of_date,
            eligible=False,
            failed_rule_ids=failed_rules,
            avg_monthly_6m=round(avg_6m, 2),
            avg_monthly_3m=round(avg_3m, 2),
            basis_monthly=round(basis_monthly, 2),
            cv=cv,
            factor=factor,
            advance=0.0,
            cap=0.0,
            origination_fee=0.0,
            gst_on_fee=0.0,
            net_disbursal=0.0,
            holdback_pct=0.0,
            avg_daily_settlement=round(avg_daily_settlement, 2),
            expected_term_days=0.0,
            effective_apr=0.0
        )
        
    # BR-02 / BR-14: Advance Sizing
    # Refinance caps advance at 1.0x basis monthly settlements.
    # Regular advance caps at 1.2x basis monthly settlements, absolute cap Rs 25,00,000.
    multiplier = 1.0 if is_refinance else 1.2
    max_advance = min(multiplier * basis_monthly, 2500000.0)
    advance = min(requested_advance, max_advance)
    
    # BR-04: Holdback and Term
    holdback_pct, term, final_advance, cap = calculate_holdback_and_term(
        advance, factor, avg_daily_settlement
    )
    
    # BR-05: Fees, GST & APR
    origination_fee = round(0.02 * final_advance, 2)
    gst_on_fee = round(0.18 * origination_fee, 2)
    net_disbursal = round(final_advance - origination_fee - gst_on_fee, 2)
    
    # Effective APR formula: ((cap - advance) / advance) * (365 / expected_term) * 100
    if term > 0 and final_advance > 0:
        effective_apr = round(
            ((cap - final_advance) / final_advance) * (365.0 / term) * 100.0, 2
        )
    else:
        effective_apr = 0.0
        
    return UnderwritingOffer(
        merchant_id=profile.merchant_id,
        command=command,
        underwrite_date=as_of_date,
        eligible=True,
        failed_rule_ids=[],
        avg_monthly_6m=round(avg_6m, 2),
        avg_monthly_3m=round(avg_3m, 2),
        basis_monthly=round(basis_monthly, 2),
        cv=cv,
        factor=factor,
        advance=final_advance,
        cap=cap,
        origination_fee=origination_fee,
        gst_on_fee=gst_on_fee,
        net_disbursal=net_disbursal,
        holdback_pct=holdback_pct,
        avg_daily_settlement=round(avg_daily_settlement, 2),
        expected_term_days=term,
        effective_apr=effective_apr
    )
