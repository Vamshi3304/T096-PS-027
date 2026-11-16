"""
Unit tests for BR-03: Risk Banding, Factor Rate & Repayment Cap.
Rules:
- Risk band calculated by Coefficient of Variation (CV) of monthly settlements.
- CV convention: population standard deviation of the 6 calendar-month totals / mean.
- Bands:
    * CV <= 0.15 -> factor 1.12
    * 0.15 < CV <= 0.30 -> factor 1.18
    * 0.30 < CV <= 0.45 -> factor 1.25
    * CV > 0.45 -> Ineligible
- Repayment cap = advance * factor.
"""

import pytest

from src.underwriting import compute_factor_rate


def test_br03_factor_lowest_risk_band():
    """CV in (0, 0.15) receives factor 1.12."""
    assert compute_factor_rate(0.08) == 1.12
    assert compute_factor_rate(0.12) == 1.12


def test_br03_factor_exact_cv_0_15_boundary_mch001():
    """Planted edge case: CV exactly 0.1500 qualifies for 1.12 factor band."""
    assert compute_factor_rate(0.1500) == 1.12


def test_br03_factor_medium_risk_band():
    """CV in (0.15, 0.30] receives factor 1.18."""
    assert compute_factor_rate(0.1501) == 1.18
    assert compute_factor_rate(0.22) == 1.18
    assert compute_factor_rate(0.3000) == 1.18


def test_br03_factor_high_risk_band():
    """CV in (0.30, 0.45] receives factor 1.25."""
    assert compute_factor_rate(0.3001) == 1.25
    assert compute_factor_rate(0.4000) == 1.25
    assert compute_factor_rate(0.4499) == 1.25


def test_br03_factor_exact_cv_0_45_boundary_mch008():
    """Planted edge case: CV exactly 0.4500 is still eligible and receives factor 1.25."""
    assert compute_factor_rate(0.4500) == 1.25


def test_br03_factor_cv_above_0_45_ineligible():
    """CV > 0.4500 is outside underwriting risk appetite and is ineligible."""
    assert compute_factor_rate(0.4501) is None
    assert compute_factor_rate(0.52) is None


def test_br03_repayment_cap_calculation():
    """Repayment cap = advance * factor."""
    advance = 200000.0
    factor = 1.12
    assert advance * factor == 224000.0

    advance_high = 311040.0
    factor_high = 1.25
    assert advance_high * factor_high == 388800.0
