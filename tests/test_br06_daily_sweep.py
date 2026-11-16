"""
Unit tests for BR-06: Daily Sweep Calculation.
Rules:
- Daily sweep = floor(holdback_pct * net_settlement).
- Rounded down to nearest rupee.
- Day 0 (disbursal date) is not swept.
- Days with zero or negative net settlements sweep Rs 0.
- Sweep is capped at balance remaining.
"""

import math
import pytest


def test_br06_sweep_floor_rounding():
    """Verify floor rounding to integer rupee."""
    holdback = 0.12
    net_settlement = 19500.0
    sweep = math.floor(holdback * net_settlement)
    assert sweep == 2340

    # With cents
    net_with_cents = 8215.75
    sweep_cents = math.floor(holdback * net_with_cents)
    assert sweep_cents == math.floor(985.89) == 985


def test_br06_negative_net_settlement_edge_case():
    """Planted edge case: When refunds exceed gross sales making net negative, sweep is Rs 0."""
    gross = 4200.0
    mdr = 63.0
    refunds = 9800.0
    net_settlement = gross - mdr - refunds  # -5663.00
    assert net_settlement < 0

    sweep = math.floor(0.15 * net_settlement) if net_settlement > 0 else 0.0
    assert sweep == 0.0


def test_br06_sweep_capped_at_balance_remaining():
    """Daily sweep cannot exceed remaining balance."""
    balance_remaining = 500.0
    net_settlement = 50000.0
    raw_sweep = math.floor(0.12 * net_settlement)  # 6000.0
    actual_sweep = min(float(raw_sweep), balance_remaining)
    assert actual_sweep == 500.0
