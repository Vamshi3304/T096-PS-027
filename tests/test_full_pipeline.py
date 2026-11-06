"""
Full Pipeline Integration Test for PS-027.
Validates end-to-end execution on the complete sample dataset.
"""

from datetime import date
import os
import pytest

from src.ingestion import (
    load_commands,
    load_holidays,
    load_merchants,
    load_settlement_events,
    load_settlement_history
)
from src.models import MerchantStatus
from src.simulator import SimulationEngine


DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


@pytest.fixture(scope="module")
def run_full_simulation():
    """Runs simulation on sample dataset and provides the engine instance."""
    merchants_path = os.path.join(DATA_DIR, "merchants.csv")
    history_path = os.path.join(DATA_DIR, "settlement_history.csv")
    events_path = os.path.join(DATA_DIR, "settlement_events.csv")
    holidays_path = os.path.join(DATA_DIR, "holidays.csv")
    commands_path = os.path.join(DATA_DIR, "commands.txt")

    merchants = load_merchants(merchants_path)
    history = load_settlement_history(history_path)
    events_by_date = load_settlement_events(events_path)
    holidays = load_holidays(holidays_path)
    commands = load_commands(commands_path)

    engine = SimulationEngine(
        merchants=merchants,
        history=history,
        events_by_date=events_by_date,
        holidays=holidays,
        commands=commands
    )
    engine.run_simulation()
    return engine


def test_pipeline_underwriting_offers(run_full_simulation):
    """Verify underwriting offers generated for all 10 merchants."""
    engine = run_full_simulation
    offers_by_id = {o.merchant_id: o for o in engine.offer_sheet if o.command == "UNDERWRITE"}
    
    assert len(offers_by_id) == 10
    
    # MCH-001: CV=0.1500, factor=1.12, hb=15%
    o1 = offers_by_id["MCH-001"]
    assert o1.eligible is True
    assert o1.cv == 0.1500
    assert o1.factor == 1.12
    assert o1.holdback_pct == 15.0

    # MCH-002: term=270.00, hb=12%
    o2 = offers_by_id["MCH-002"]
    assert o2.eligible is True
    assert o2.expected_term_days == 270.00
    assert o2.holdback_pct == 12.0

    # MCH-004: lower 3m basis = 420k -> advance = 504k
    o4 = offers_by_id["MCH-004"]
    assert o4.eligible is True
    assert o4.basis_monthly == 420000.0
    assert o4.advance == 504000.0

    # MCH-009: Ineligible (failed 40% floor)
    o9 = offers_by_id["MCH-009"]
    assert o9.eligible is False
    assert "BR-01" in o9.failed_rule_ids

    # MCH-010: Ineligible (failed age requirement)
    o10 = offers_by_id["MCH-010"]
    assert o10.eligible is False
    assert "BR-01" in o10.failed_rule_ids


def test_pipeline_mch004_early_payoff(run_full_simulation):
    """Verify MCH-004 early payoff on Day 90 is recorded in payoffs."""
    engine = run_full_simulation
    payoffs = [p for p in engine.payoffs if p.merchant_id == "MCH-004" and p.event == "EARLY_PAYOFF"]
    assert len(payoffs) == 1
    p = payoffs[0]
    assert p.day_no == 90
    assert p.discount_pct == 25.0
    assert p.amount_due_or_netted == 547538.14


def test_pipeline_mch005_renewal(run_full_simulation):
    """Verify MCH-005 renewal on Day 135 at exactly 60% collected."""
    engine = run_full_simulation
    renewals = [p for p in engine.payoffs if p.merchant_id == "MCH-005" and p.event == "RENEW"]
    assert len(renewals) == 1
    r = renewals[0]
    assert r.collected_to_date == 290304.0
    assert r.collected_to_date / r.cap == 0.60


def test_pipeline_mch007_delinquency_and_default(run_full_simulation):
    """Verify MCH-007 delinquency progression to WATCH and DEFAULT."""
    engine = run_full_simulation
    defaults = [p for p in engine.payoffs if p.merchant_id == "MCH-007" and p.event == "DEFAULT_ACCELERATION"]
    assert len(defaults) == 1
    d = defaults[0]
    assert d.penalty > 0
    assert engine.active_merchants["MCH-007"].status == MerchantStatus.DEFAULT


def test_pipeline_mch008_refinance(run_full_simulation):
    """Verify MCH-008 refinance caps at 1.0x (150,000) and nets off 96,500."""
    engine = run_full_simulation
    refinances = [p for p in engine.payoffs if p.merchant_id == "MCH-008" and p.event == "REFINANCE"]
    assert len(refinances) == 1
    ref = refinances[0]
    assert ref.new_advance == 150000.0
    assert ref.amount_due_or_netted == 96500.0
    assert ref.new_net_disbursal == 49960.0


def test_pipeline_portfolio_ageing_output(run_full_simulation):
    """Verify portfolio ageing report is generated with correct fields."""
    engine = run_full_simulation
    assert len(engine.portfolio_ageing) > 0
    for entry in engine.portfolio_ageing:
        assert entry.merchant_id.startswith("MCH-")
        assert entry.status in ["ACTIVE", "WATCH", "DEFAULT", "CLOSED", "RENEWED"]
        assert entry.days_since_disbursal >= 0
