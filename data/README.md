# PS-027 – Merchant Cash Advance and Revenue-Based Financing Engine — Sample Data Pack

Prepared by 10 SECONDS for Team T096.

## Files

| File | What it holds | Row count |
|---|---|---|
| `merchants.csv` | Merchant profiles (10) with business start date, aggregator id and bank mandate | 10 |
| `settlement_history.csv` | Daily net settlements from the aggregator, 2026-01-01 to 2026-06-30 (181 days = 6 full months) for every merchant | 1810 |
| `settlement_events.csv` | Daily post-disbursal settlement feed for all merchants, day 0 (2026-07-01) to day 150 (2026-11-28) | 1511 |
| `holidays.csv` | Bank holidays 2026 (Sundays are implicit non-working days) | 10 |
| `commands.txt` | Underwriting, acceptance, mandate failures, payoff / renewal / refinance commands (25) | 28 |

Row count for `commands.txt` = command lines (comment lines starting with `#` and blank lines are not counted).

## Column reference

### merchants.csv
| column | type | format / allowed values | notes |
|---|---|---|---|
| merchant_id | string | `MCH-001` … | primary key |
| business_name, owner_name | string | | |
| city | string | | |
| category | string | e.g. `RESTAURANT`, `PHARMACY` | context only |
| business_start_date | date | `YYYY-MM-DD` | business age = full months between this date and the UNDERWRITE date |
| aggregator_id | string | `AGG######` | payment aggregator merchant id |
| mandate_id | string | `MNDT##########` | bank mandate used for Monday shortfall debits |
| ifsc | string | 11-char IFSC-shaped code | fake |
| mobile | string | 10 digits starting 6–9 | |

### settlement_history.csv (6 months before underwriting)
| column | type | format | notes |
|---|---|---|---|
| merchant_id | string | FK → merchants | |
| date | date | `YYYY-MM-DD` | every calendar day 2026-01-01 … 2026-06-30, exactly one row per merchant per day |
| gross_sales | money | Rs, 2 decimals | card + UPI sales |
| mdr | money | Rs | aggregator fee (≈1.5% of gross) |
| refunds | money | Rs | customer refunds processed that day |
| net_settlement | money | Rs | = gross_sales − mdr − refunds; this is the "settlement" every rule refers to. Monthly settlements = sum of net_settlement per calendar month; average daily settlement = 6-month total / 181 |

### settlement_events.csv (post-disbursal feed)
Same columns as settlement_history.csv. One row per merchant per day from 2026-07-01 (day 0 = disbursal day, not swept) to 2026-11-28 (day 150). Day n = disbursal date + n days. Contains one duplicate row and one out-of-order row (see traps). `net_settlement` can be negative.

### holidays.csv
| column | type | notes |
|---|---|---|
| date | date | bank holiday; Sundays are also non-working days |
| name | string | |

## Command file format

One command per line, `COMMAND|arg1|arg2|...`, processed strictly in file order. Lines starting with `#` are comments. A command dated D is applied after the daily job (sweep → true-up → weekly minimum → delinquency → term tracking) for date D has run.

| command | arguments | meaning |
|---|---|---|
| `UNDERWRITE` | `merchant_id`, `date`, `requested_advance` | run eligibility and pricing as of `date`; advance = min(requested, 1.2 × basis monthly settlements, 2500000.00) where basis = min(6-month average, last-3-month average); print the offer with rule IDs |
| `ACCEPT` | `merchant_id`, `date` | accept the open offer; disburse on `date` net of origination 2% + 18% GST on the fee |
| `MANDATE_FAIL` | `merchant_id`, `monday_date` | the shortfall debit presented for that Monday's weekly-minimum check fails (Rs 500 charge, counts as a missed week). Debits not listed here succeed |
| `EARLY_PAYOFF` | `merchant_id`, `date` | compute and settle the early-payoff amount on `date` (day number = date − disbursal date) |
| `RENEW` | `merchant_id`, `date`, `requested_advance` | renewal request; re-underwrite on the same 6-month history, net off the remaining balance of the old advance at zero discount |
| `REFINANCE` | `merchant_id`, `date`, `other_lender`, `payoff_letter_ref`, `payoff_amount` | take over a balance from another lender; advance capped at 1.0 × basis monthly settlements; payoff_amount is paid to the other lender out of the disbursal |
| `PRINT_PORTFOLIO` | `date` | emit the portfolio ageing as of `date` |

Pricing conventions you must state in your output if you deviate: CV uses the population standard deviation of the 6 calendar-month totals; expected term is printed with 2 decimals; effective APR = ((cap − advance) / advance) × (365 / expected_term) × 100, 2 decimals; plan at day n = cap × n / expected_term.

## Planted scenarios

Locators below are physical line numbers of the named file (a CSV header is line 1; comment lines in commands.txt count).

Edge cases from the brief (one bullet per edge case, in brief order):

- **CV exactly 0.15 and 0.45** — settlement_history.csv: MCH-001 monthly totals alternate 230000.00 / 170000.00 (mean 200000, population std 30000 → CV = 0.1500 exactly → factor 1.12 band); MCH-008 monthly totals alternate 217500.00 / 82500.00 (mean 150000, population std 67500 → CV = 0.4500 exactly → still eligible, factor 1.25). Each month's daily rows sum exactly to the monthly total (check Jan: rows dated 2026-01-01..31). CV convention: population standard deviation of the 6 calendar-month totals divided by their mean, 4 decimals.
- **Expected term exactly 270 days before holdback adjustment** — MCH-002: 6-month total 2172000.00 over 181 days → average daily settlement 12000.00; UNDERWRITE requests 311040.00 (below the 1.2x cap 434400.00), CV 0.40 → factor 1.25 → cap 388800.00; term = 388800 / (0.12 × 12000) = 270.00 days exactly → inside 120–270, no holdback step needed.
- **A week with Rs 0 settlements on all days** — MCH-003 settlement_events.csv rows 2026-10-05 (Mon) to 2026-10-11 (Sun) (rows 401–407) are all 0.00 → sweeps 0 for the whole calendar week → Monday 2026-10-12 mandate debit for the full shortfall (50% of expected weekly 12600.00 = 6300.00 threshold; expected weekly = cap 403200 / term 224 × 7).
- **True-up on day 60 with collections exactly 130% of plan** — MCH-003: advance 360000.00, CV 0.10 → factor 1.12 → cap 403200.00; avg daily 15000.00 → term 224 days at 12%. Post-disbursal net is 19500.00 on every day 0–61 (rows 305–367) → sweep floor(0.12 × 19500) = 2340 per day → cumulative after 60 sweeps = 140400.00 = exactly 130% of plan (plan at day 60 = 403200 × 60 / 224 = 108000.00). Not '> 130%', so holdback must NOT be reduced on day 60 (2026-08-30).
- **Early payoff on day 90** — EARLY_PAYOFF for MCH-004 on 2026-09-29 = disbursal 2026-07-01 + 90 days (commands.txt line 29). Day numbering: disbursal date is day 0, so 2026-09-29 is day 90 — the boundary between the 50% ('before day 90') and 25% discount tiers.
- **Renewal when collected is exactly 60% of cap** — MCH-005: advance 432000.00, factor 1.12 → cap 483840.00; net 18000.00 on days 1–134 (sweep 2160 each = 289440.00) and 7200.00 on day 135 (sweep 864) → cumulative exactly 290304.00 = 60.00% of cap after the day-135 sweep; RENEW on 2026-11-13 (day 135, commands.txt line 30) is processed after that sweep. No WATCH on this merchant.
- **Mandate debit failing on a Monday holiday** — MCH-006: week Mon 2026-09-07 to Sun 2026-09-13 has nets at ~15% of average (below 50% of the expected weekly amount) → shortfall debit falls due Monday 2026-09-14, which is Ganesh Chaturthi in holidays.csv; MANDATE_FAIL|MCH-006|2026-09-14 (commands.txt line 28) says that debit failed → Rs 500 charge + 1 missed week. State in your output whether you present on the holiday or roll to Tue 2026-09-15; the failure applies to that week's debit either way.
- **Settlement with refunds making net negative** — MCH-006 row dated 2026-08-20 (row 808): gross 4200.00, mdr 63.00, refunds 9800.00 → net −5663.00 → sweep 0 for that day.

Extra traps:

- MCH-004 (settlement_history.csv): last-3-months average (420000.00) is lower than the 6-month average (460000.00) → the advance basis must be the lower figure (1.2 × 420000 = 504000.00 cap on the 900000.00 requested).
- MCH-009: March 2026 total 60000.00 is below 40% of its 6-month average (160000.00 × 0.40 = 64000.00) → ineligible; the later ACCEPT for MCH-009 must be rejected (no offer exists). MCH-010: business_start_date 2025-08-01 → 11 months old on the underwrite date → ineligible.
- Duplicate feed row: settlement_events.csv row 45 repeats MCH-001 / 2026-08-12 verbatim → sweep that day only once.
- Out-of-order feed row: MCH-002 / 2026-09-10 appears at row 227 after 2026-09-11 and 2026-09-12 → the daily job must key on the date column, not on file position.
- MCH-007 delinquency path: settlements collapse to ~12% of average from Mon 2026-08-03; mandate debits fail on 2026-08-10, 08-17, 08-31, 09-07 (lines 24–27) → WATCH after 2 missed weeks, DEFAULT after 4 → accelerate remaining cap + 5% penalty and stop sweeping (later feed rows for MCH-007 must not be swept).
- Duplicate UNDERWRITE for MCH-004 at line 14 (same date, same request) → ignore / log, do not create a second offer. REFINANCE for MCH-008 (line 23) caps the advance at 1.0x monthly settlements (150000.00) even though 180000.00 was requested, and nets off the 96500.00 payoff to the other lender.

## What is NOT in this pack

Expected outputs are not provided for this set. Validate your engine with your own test suite against the rules in your brief (BR-01 … BR-nn). A separate hidden input set with the same schema will be used at final evaluation; outputs are compared field-for-field, so follow the column formats above exactly in your own output.


## Output format expected at evaluation

1. `offer_sheet.csv` — one row per UNDERWRITE / RENEW / REFINANCE: `merchant_id, command, date, eligible (true/false), failed_rule_ids (semicolon list, blank if eligible), avg_monthly_6m, avg_monthly_3m, basis_monthly, cv, factor, advance, cap, origination_fee, gst_on_fee, net_disbursal, holdback_pct, avg_daily_settlement, expected_term_days, effective_apr`.
2. `daily_ledger.csv` — one row per disbursed merchant per day 1..150 (or until closed): `merchant_id, day_no, date, net_settlement, holdback_pct_in_force, sweep, mandate_debit, mandate_charge, cumulative_collected, balance_remaining, missed_weeks, status (ACTIVE/WATCH/DEFAULT/CLOSED/RENEWED), flags (semicolon list e.g. TRUEUP_DOWN, TRUEUP_UP, TERM_REVIEW, ZERO_WEEK)`.
3. `payoffs.csv` — one row per EARLY_PAYOFF / RENEW / REFINANCE / DEFAULT acceleration: `merchant_id, event, date, day_no, cap, collected_to_date, remaining_cap, factor_portion_remaining, discount_pct, discount_amount, penalty, amount_due_or_netted, new_advance, new_net_disbursal`.
4. `portfolio_ageing.csv` — as of the PRINT_PORTFOLIO date: `merchant_id, status, days_since_disbursal, expected_term_days, pct_collected, missed_weeks, balance_remaining, review_flag`.
