# PS-027: Merchant Cash Advance and Revenue-Based Financing Engine
### Team ID: T096 · Capstone Project Submission (Week 1 to Week 3 Complete)

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Test Suite](https://img.shields.io/badge/pytest-passing-brightgreen.svg)](tests/)
[![Business Rules](https://img.shields.io/badge/Business%20Rules-BR--01%20to%20BR--14-success.svg)](docs/DESIGN_DOCUMENT.md)
[![Evaluation Score Goal](https://img.shields.io/badge/Rubric%20Target-100%2F100-gold.svg)]()

---

## 1. Project Overview

This repository contains the production-grade back-end rules engine for **PS-027 (Merchant Cash Advance and Revenue-Based Financing Engine)** built for fintech alternative lending.

The engine models the complete lifecycle of revenue-based financing:
1. **Ingestion & Underwriting:** Ingests merchant profiles and 6 months of daily settlement feeds from payment aggregators to size advances, determine risk bands via coefficient of variation (CV), establish factor rates, calculate holdback percentages, and enforce business age and consistency rules.
2. **Disbursal & Daily Sweeping:** Automatically sweeps a share of daily net card/UPI settlement payouts until the repayment cap is fulfilled.
3. **Daily Precedence Simulation:** Runs strict 5-stage daily jobs:
   $$\text{Settlement Sweep} \longrightarrow \text{True-Up Check} \longrightarrow \text{Weekly Shortfall Mandate} \longrightarrow \text{Delinquency Tracking} \longrightarrow \text{Term Review}$$
4. **Lifecycle Commands:** Executes early payoff discounting, advance renewals with zero-discount balance net-offs, external lender refinancing buyouts, and portfolio ageing analytics.

---

## 2. Quickstart & Execution

### Prerequisites
* Python 3.10+ (tested on Python 3.13)
* `pytest` (for running the automated test suite)

### Setup & Run Engine
To run the full command-file simulation on the benchmark sample dataset:

```bash
# Clone the repository
git clone https://github.com/T096/T096-PS-027.git
cd T096-PS-027

# Run the engine
python main.py
```

By default, the engine reads input files from `data/` and outputs the 4 mandatory CSV reports to `output/`:
* `output/offer_sheet.csv`: Underwriting decisions and loan pricing parameters.
* `output/daily_ledger.csv`: Daily sweep transactions, holdback in force, balances, and operational flags.
* `output/payoffs.csv`: Early payoffs, contract renewals, refinance buyouts, and default accelerations.
* `output/portfolio_ageing.csv`: Portfolio-wide ageing, collection percentages, and delinquency statuses.

Custom input/output paths can be passed via flags:
```bash
python main.py --data-dir path/to/data --output-dir path/to/output
```

---

## 3. Automated Test Suite (Single-Command Execution)

Run all unit tests and edge-case validations using `pytest`:

```bash
pytest
```

For verbose output with exact test descriptions:
```bash
pytest -v
```

### Test Coverage Highlights
* **100% Business Rule Mapping:** Separate unit test modules for `BR-01` through `BR-14` (`test_br01_eligibility.py` to `test_br14_refinance.py`).
* **Explicit Edge Case Suite (`tests/test_edge_cases.py`):** Dedicated tests for all 8 mandatory edge cases and 5 planted traps from the brief.
* **End-to-End Pipeline Test (`tests/test_full_pipeline.py`):** Runs the full simulation and asserts exact figures against benchmark data.

---

## 4. Repository Structure

```
T096-PS-027/
├── data/                                 # Sample data pack
│   ├── merchants.csv                     # 10 merchant profiles
│   ├── settlement_history.csv            # 181 days of pre-underwrite settlements
│   ├── settlement_events.csv            # 151 days of post-disbursal event feed
│   ├── holidays.csv                      # Bank holidays calendar
│   └── commands.txt                      # 28 lifecycle and event commands
├── docs/                                 # Documentation & Evaluation Deliverables
│   ├── DESIGN_DOCUMENT.md                # Week 1 Design Doc (Glossary, Diagrams, BR-01..BR-14)
│   └── DECISION_LOG.md                   # 15 Architecture & Numerical Decisions
├── src/                                  # Clean Modular Architecture
│   ├── __init__.py
│   ├── models.py                         # Enums, Dataclasses, Custom Exceptions
│   ├── underwriting.py                   # BR-01 to BR-05, BR-14 Underwriting Logic
│   ├── ingestion.py                      # CSV parsers, deduplication, date ordering
│   ├── simulator.py                      # 5-stage daily job precedence & commands
│   └── reports.py                        # Exporters for the 4 mandatory CSVs
├── tests/                                # Comprehensive Pytest Test Suite
│   ├── __init__.py
│   ├── test_br01_eligibility.py          # Eligibility (months, age, floor, 1L avg)
│   ├── test_br02_advance_sizing.py       # 1.2x sizing, 3m vs 6m lower basis, 25L cap
│   ├── test_br03_factor_rate_cv.py       # CV risk bands, boundaries at 0.15 & 0.45
│   ├── test_br04_holdback_term.py        # 120-270 day term target, 270 day boundary
│   ├── test_br05_fees_apr.py             # 2% fee, 18% GST, effective APR formula
│   ├── test_br06_daily_sweep.py          # Floor rounding, zero/negative sweep clamping
│   ├── test_br07_daily_precedence.py     # 5-stage daily execution precedence
│   ├── test_br08_true_up.py              # Day 60/90 true-ups, >130% strict inequality
│   ├── test_br09_weekly_minimum.py       # Monday shortfall debit, failed charge, zero week
│   ├── test_br10_delinquency.py          # Watch at 2, Default at 4 (+5% penalty)
│   ├── test_br11_term_tracking.py        # Term + 60 days review trigger
│   ├── test_br12_early_payoff.py         # Day 90 25% discount tier vs Day <90 50% tier
│   ├── test_br13_renewal.py              # Exact 60% threshold, net-off at 0% discount
│   ├── test_br14_refinance.py            # 1.0x basis cap, external lender payoff deduction
│   ├── test_edge_cases.py                # All 8 mandatory edge cases & traps
│   └── test_full_pipeline.py             # End-to-end integration test
├── main.py                               # CLI entry point
├── pytest.ini                            # Test configuration
└── README.md                             # Project documentation & viva guide
```

---

## 5. Business Rule Register Summary

| Rule ID | Name | Core Logic |
| :---: | :--- | :--- |
| **BR-01** | Merchant Eligibility | 6+ months history (180+ days), avg monthly $\ge$ Rs 1L, no month $<$ 40% of 6m avg, business age $\ge$ 12 months. |
| **BR-02** | Advance Sizing | Max $1.2\times$ basis monthly settlements ($\min(6\text{m avg}, 3\text{m avg})$), capped at Rs 25 Lakh. |
| **BR-03** | Risk Banding & Factor | $\text{CV} \le 0.15 \to 1.12$; $0.15 < \text{CV} \le 0.30 \to 1.18$; $0.30 < \text{CV} \le 0.45 \to 1.25$; $\text{CV} > 0.45 \to \text{Ineligible}$. $\text{Cap} = \text{Advance} \times \text{Factor}$. |
| **BR-04** | Holdback & Term | Default 12%; target term 120–270 days. Adjust holdback in 1% steps within 8%–20%. If still outside, reduce advance to fit 270 days. |
| **BR-05** | Fees & APR | Origination fee 2% + 18% GST deducted at disbursal. $\text{Effective APR} = \frac{\text{Cap}-\text{Adv}}{\text{Adv}} \times \frac{365}{\text{Term}} \times 100$. |
| **BR-06** | Daily Sweep | $\lfloor \text{Holdback} \times \text{Net Settlement} \rfloor$. Days with zero or negative net settlements sweep Rs 0. Day 0 not swept. |
| **BR-07** | Job Precedence | Strict priority: Sweep $\to$ True-Up (Days 60, 90...) $\to$ Weekly Minimum (Mondays) $\to$ Delinquency $\to$ Term Review. |
| **BR-08** | Mid-Term True-Up | Day 60 & every 30 days: $>130\%$ of plan reduces holdback by 2 points (floor 8%); $<70\%$ raises holdback by 2 points (ceiling 20%) from next day. |
| **BR-09** | Weekly Minimum | Preceding Mon-Sun sweeps $< 50\%$ expected weekly amount $\implies$ debit shortfall on Monday. Failed debit adds Rs 500 charge + 1 missed week. |
| **BR-10** | Delinquency | 2 missed weeks $\implies$ WATCH (blocks renewals); 4 missed weeks $\implies$ DEFAULT (accelerates balance + 5% penalty, sweeps cease). |
| **BR-11** | Term Tracking | Elapsed days $\ge \text{Term} + 60 \implies \text{TERM\_REVIEW}$ flag. |
| **BR-12** | Early Payoff | Before Day 90: 50% discount on uncollected factor portion; Day 90 onwards: 25% discount. |
| **BR-13** | Renewal | Allowed when $\ge 60\%$ of cap collected and not WATCH/DEFAULT. Nets off old balance at 0% discount. |
| **BR-14** | External Refinance | Caps advance at $1.0\times$ basis monthly settlements. Pays off other lender out of disbursal proceeds. |

---

## 6. Viva Presentation & Live Coding Guide

### A. Factor-Rate Pricing vs. Compound Interest
* **Why Factor Rates?** In Merchant Cash Advances, the lender is purchasing future receivables at a discount, not issuing a traditional loan with an amortization schedule.
* **No Compounding:** A factor rate creates a fixed, upfront monetary markup ($\text{Cap} = \text{Advance} \times \text{Factor}$). The total amount owed never increases with time, regardless of whether repayment takes 120 days or 270 days.
* **Why APR is Still Disclosed:** Regulation requires providing an annualized effective APR so merchants can compare alternative financing options against conventional bank term loans.

### B. How True-Ups Change Holdback Mid-Term
* RBF contracts aim for an expected tenure (e.g. 180–224 days).
* If a merchant has unexpectedly booming sales, sweeping 12% would deplete their working capital too aggressively. A True-Up down to 10% or 8% leaves more daily cash in the merchant's hands.
* Conversely, if sales drop significantly, a True-Up up to 14%–20% ensures the advance is repaid before the merchant's risk profile deteriorates.

### C. Live Code Modification Cheatsheet (for Viva Panel)
If the viva panel asks you to modify a rule live:
* **To change the fee or GST rate:** Look in [`src/underwriting.py`](src/underwriting.py) under `underwrite_merchant` (lines 148–150).
* **To change the True-Up threshold (e.g., from 130% to 125%):** Look in [`src/simulator.py`](src/simulator.py) under `_run_daily_job` (lines 115–124).
* **To change the missed weeks threshold for WATCH or DEFAULT:** Look in [`src/simulator.py`](src/simulator.py) under Precedence 4 (lines 160–180).
* **To change the Early Payoff discount tiers:** Look in [`src/simulator.py`](src/simulator.py) under `EARLY_PAYOFF` command handler (lines 225–240).
