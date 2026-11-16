"""
Reports and CSV Export Module for PS-027.
Exports the 4 mandatory files specified in the benchmark evaluation:
1. offer_sheet.csv
2. daily_ledger.csv
3. payoffs.csv
4. portfolio_ageing.csv
"""

import csv
import os
from typing import List

from .models import (
    LedgerEntry,
    PayoffRecord,
    PortfolioAgeingRecord,
    UnderwritingOffer
)


def export_offer_sheet(offers: List[UnderwritingOffer], output_path: str):
    """Exports offer_sheet.csv."""
    fieldnames = [
        "merchant_id", "command", "date", "eligible", "failed_rule_ids",
        "avg_monthly_6m", "avg_monthly_3m", "basis_monthly", "cv", "factor",
        "advance", "cap", "origination_fee", "gst_on_fee", "net_disbursal",
        "holdback_pct", "avg_daily_settlement", "expected_term_days", "effective_apr"
    ]
    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for o in offers:
            writer.writerow({
                "merchant_id": o.merchant_id,
                "command": o.command,
                "date": o.underwrite_date.strftime("%Y-%m-%d"),
                "eligible": str(o.eligible).lower(),
                "failed_rule_ids": ";".join(o.failed_rule_ids),
                "avg_monthly_6m": f"{o.avg_monthly_6m:.2f}",
                "avg_monthly_3m": f"{o.avg_monthly_3m:.2f}",
                "basis_monthly": f"{o.basis_monthly:.2f}",
                "cv": f"{o.cv:.4f}",
                "factor": f"{o.factor:.2f}" if o.factor is not None else "",
                "advance": f"{o.advance:.2f}",
                "cap": f"{o.cap:.2f}",
                "origination_fee": f"{o.origination_fee:.2f}",
                "gst_on_fee": f"{o.gst_on_fee:.2f}",
                "net_disbursal": f"{o.net_disbursal:.2f}",
                "holdback_pct": f"{o.holdback_pct:.2f}",
                "avg_daily_settlement": f"{o.avg_daily_settlement:.2f}",
                "expected_term_days": f"{o.expected_term_days:.2f}",
                "effective_apr": f"{o.effective_apr:.2f}"
            })


def export_daily_ledger(ledger_entries: List[LedgerEntry], output_path: str):
    """Exports daily_ledger.csv."""
    fieldnames = [
        "merchant_id", "day_no", "date", "net_settlement", "holdback_pct_in_force",
        "sweep", "mandate_debit", "mandate_charge", "cumulative_collected",
        "balance_remaining", "missed_weeks", "status", "flags"
    ]
    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for e in ledger_entries:
            writer.writerow({
                "merchant_id": e.merchant_id,
                "day_no": e.day_no,
                "date": e.date.strftime("%Y-%m-%d"),
                "net_settlement": f"{e.net_settlement:.2f}",
                "holdback_pct_in_force": f"{e.holdback_pct_in_force:.2f}",
                "sweep": f"{e.sweep:.2f}",
                "mandate_debit": f"{e.mandate_debit:.2f}",
                "mandate_charge": f"{e.mandate_charge:.2f}",
                "cumulative_collected": f"{e.cumulative_collected:.2f}",
                "balance_remaining": f"{e.balance_remaining:.2f}",
                "missed_weeks": e.missed_weeks,
                "status": e.status.value,
                "flags": ";".join(e.flags)
            })


def export_payoffs(payoff_records: List[PayoffRecord], output_path: str):
    """Exports payoffs.csv."""
    fieldnames = [
        "merchant_id", "event", "date", "day_no", "cap", "collected_to_date",
        "remaining_cap", "factor_portion_remaining", "discount_pct",
        "discount_amount", "penalty", "amount_due_or_netted", "new_advance",
        "new_net_disbursal"
    ]
    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in payoff_records:
            writer.writerow({
                "merchant_id": p.merchant_id,
                "event": p.event,
                "date": p.date.strftime("%Y-%m-%d"),
                "day_no": p.day_no,
                "cap": f"{p.cap:.2f}",
                "collected_to_date": f"{p.collected_to_date:.2f}",
                "remaining_cap": f"{p.remaining_cap:.2f}",
                "factor_portion_remaining": f"{p.factor_portion_remaining:.2f}",
                "discount_pct": f"{p.discount_pct:.2f}",
                "discount_amount": f"{p.discount_amount:.2f}",
                "penalty": f"{p.penalty:.2f}",
                "amount_due_or_netted": f"{p.amount_due_or_netted:.2f}",
                "new_advance": f"{p.new_advance:.2f}" if p.new_advance is not None else "",
                "new_net_disbursal": f"{p.new_net_disbursal:.2f}" if p.new_net_disbursal is not None else ""
            })


def export_portfolio_ageing(ageing_records: List[PortfolioAgeingRecord], output_path: str):
    """Exports portfolio_ageing.csv."""
    fieldnames = [
        "merchant_id", "status", "days_since_disbursal", "expected_term_days",
        "pct_collected", "missed_weeks", "balance_remaining", "review_flag"
    ]
    with open(output_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for a in ageing_records:
            writer.writerow({
                "merchant_id": a.merchant_id,
                "status": a.status,
                "days_since_disbursal": a.days_since_disbursal,
                "expected_term_days": f"{a.expected_term_days:.2f}",
                "pct_collected": f"{a.pct_collected:.2f}",
                "missed_weeks": a.missed_weeks,
                "balance_remaining": f"{a.balance_remaining:.2f}",
                "review_flag": str(a.review_flag).upper()
            })
