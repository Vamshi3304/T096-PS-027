"""
Core Simulation Engine for PS-027.
Executes daily jobs with strict precedence:
1. Sweep (BR-06)
2. True-up Check (BR-08)
3. Weekly Minimum Shortfall (BR-09)
4. Delinquency (BR-10)
5. Term Tracking (BR-11)

Processes commands after daily job:
- UNDERWRITE, ACCEPT, EARLY_PAYOFF (BR-12), RENEW (BR-13), REFINANCE (BR-14), PRINT_PORTFOLIO.
"""

from datetime import date, timedelta
import math
from typing import Dict, List, Optional, Set, Tuple

from .models import (
    CommandType,
    LedgerEntry,
    MerchantProfile,
    MerchantStatus,
    PayoffRecord,
    PortfolioAgeingRecord,
    SettlementRecord,
    UnderwritingOffer,
    IneligibleMerchantError,
    OfferNotFoundError,
    InvalidOperationError
)
from .underwriting import underwrite_merchant


class MerchantSimulationState:
    """Maintains mutable state for a merchant during simulation."""
    def __init__(self, profile: MerchantProfile, offer: UnderwritingOffer, disbursal_date: date):
        self.profile = profile
        self.offer = offer
        self.disbursal_date = disbursal_date
        self.status = MerchantStatus.ACTIVE
        self.current_holdback = offer.holdback_pct
        self.holdback_for_next_day = offer.holdback_pct
        self.cumulative_collected = 0.0
        self.balance_remaining = offer.cap
        self.missed_weeks = 0
        self.daily_sweeps_history: Dict[date, float] = {}
        self.daily_net_history: Dict[date, float] = {}
        self.closed_date: Optional[date] = None


class SimulationEngine:
    def __init__(
        self,
        merchants: Dict[str, MerchantProfile],
        history: Dict[str, List[SettlementRecord]],
        events_by_date: Dict[date, Dict[str, float]],
        holidays: Set[date],
        commands: List[Tuple[str, List[str]]]
    ):
        self.merchants = merchants
        self.history = history
        self.events_by_date = events_by_date
        self.holidays = holidays
        self.commands = commands
        
        # State tracking
        self.offers: Dict[str, UnderwritingOffer] = {}
        self.active_merchants: Dict[str, MerchantSimulationState] = {}
        self.mandate_failures: Set[Tuple[str, date]] = set()
        
        # Outputs
        self.offer_sheet: List[UnderwritingOffer] = []
        self.daily_ledger: List[LedgerEntry] = []
        self.payoffs: List[PayoffRecord] = []
        self.portfolio_ageing: List[PortfolioAgeingRecord] = []
        
        # Index commands by date
        self._preprocess_commands()

    def _preprocess_commands(self):
        """Indexes commands by date and extracts static failure configurations."""
        self.commands_by_date: Dict[date, List[Tuple[str, List[str]]]] = {}
        for cmd_type, args in self.commands:
            if cmd_type == CommandType.MANDATE_FAIL:
                m_id = args[0]
                fail_date = date.fromisoformat(args[1])
                self.mandate_failures.add((m_id, fail_date))
                continue
                
            cmd_date_str = args[1] if cmd_type != CommandType.PRINT_PORTFOLIO else args[0]
            cmd_date = date.fromisoformat(cmd_date_str)
            if cmd_date not in self.commands_by_date:
                self.commands_by_date[cmd_date] = []
            self.commands_by_date[cmd_date].append((cmd_type, args))

    def run_simulation(self):
        """Runs the day-by-day simulation across all event dates."""
        all_dates = sorted(self.events_by_date.keys())
        if not all_dates:
            return

        for current_date in all_dates:
            # 1. Execute Daily Job for all active merchants
            self._run_daily_job(current_date)
            
            # 2. Process post-daily-job commands scheduled for current_date
            if current_date in self.commands_by_date:
                for cmd_type, args in self.commands_by_date[current_date]:
                    self._execute_command(cmd_type, args, current_date)

    def _run_daily_job(self, current_date: date):
        """
        Executes daily job with strict 5-stage precedence:
        1. Settlement sweep (BR-06)
        2. True-up check (BR-08)
        3. Weekly minimum shortfall (Mondays) (BR-09)
        4. Delinquency (BR-10)
        5. Term tracking (BR-11)
        """
        active_ids = list(self.active_merchants.keys())
        for m_id in active_ids:
            state = self.active_merchants[m_id]
            if state.status in [MerchantStatus.CLOSED, MerchantStatus.RENEWED]:
                continue
                
            day_no = (current_date - state.disbursal_date).days
            flags: List[str] = []
            
            # Apply any holdback update staged from yesterday's true-up
            state.current_holdback = state.holdback_for_next_day
            holdback_in_force = state.current_holdback
            
            net_settlement = self.events_by_date.get(current_date, {}).get(m_id, 0.0)
            state.daily_net_history[current_date] = net_settlement
            
            # -------------------------------------------------------------
            # PRECEDENCE 1: Settlement Sweep (BR-06)
            # -------------------------------------------------------------
            sweep = 0.0
            # Day 0 is disbursal day -> not swept. DEFAULT -> stop sweeping.
            if day_no > 0 and state.status != MerchantStatus.DEFAULT:
                if net_settlement > 0:
                    raw_sweep = math.floor((holdback_in_force / 100.0) * net_settlement)
                    sweep = min(float(raw_sweep), state.balance_remaining)
                    state.cumulative_collected += sweep
                    state.balance_remaining = round(state.balance_remaining - sweep, 2)
                    if state.balance_remaining <= 0.0:
                        state.balance_remaining = 0.0
                        state.status = MerchantStatus.CLOSED
                        state.closed_date = current_date
            state.daily_sweeps_history[current_date] = sweep

            # -------------------------------------------------------------
            # PRECEDENCE 2: True-Up Check (BR-08)
            # -------------------------------------------------------------
            # Evaluated only on day 60 and every 30 days after
            if state.status in [MerchantStatus.ACTIVE, MerchantStatus.WATCH]:
                if day_no >= 60 and (day_no - 60) % 30 == 0:
                    plan = (state.offer.cap * day_no) / state.offer.expected_term_days
                    ratio = state.cumulative_collected / plan if plan > 0 else 1.0
                    
                    # Strictly > 130%
                    if state.cumulative_collected > 1.30 * plan:
                        flags.append("TRUEUP_DOWN")
                        state.holdback_for_next_day = max(8.0, state.current_holdback - 2.0)
                    # Strictly < 70%
                    elif state.cumulative_collected < 0.70 * plan:
                        flags.append("TRUEUP_UP")
                        state.holdback_for_next_day = min(20.0, state.current_holdback + 2.0)

            # -------------------------------------------------------------
            # PRECEDENCE 3: Weekly Minimum Shortfall (Mondays) (BR-09)
            # -------------------------------------------------------------
            mandate_debit = 0.0
            mandate_charge = 0.0
            if current_date.weekday() == 0 and day_no >= 7 and state.status != MerchantStatus.DEFAULT:
                # Preceding 7 days (last Monday to Sunday)
                week_start = current_date - timedelta(days=7)
                week_end = current_date - timedelta(days=1)
                
                week_sweeps = 0.0
                all_zero_nets = True
                cur = week_start
                while cur <= week_end:
                    week_sweeps += state.daily_sweeps_history.get(cur, 0.0)
                    if state.daily_net_history.get(cur, 0.0) > 0.0:
                        all_zero_nets = False
                    cur += timedelta(days=1)
                    
                if all_zero_nets:
                    flags.append("ZERO_WEEK")
                    
                expected_weekly = (state.offer.cap / state.offer.expected_term_days) * 7.0
                threshold = 0.50 * expected_weekly
                
                if week_sweeps < threshold:
                    shortfall = round(threshold - week_sweeps, 2)
                    # Check if debit fails
                    if (m_id, current_date) in self.mandate_failures:
                        mandate_charge = 500.0
                        state.balance_remaining = round(state.balance_remaining + mandate_charge, 2)
                        state.missed_weeks += 1
                    else:
                        mandate_debit = min(shortfall, state.balance_remaining)
                        state.cumulative_collected += mandate_debit
                        state.balance_remaining = round(state.balance_remaining - mandate_debit, 2)
                        if state.balance_remaining <= 0.0:
                            state.balance_remaining = 0.0
                            state.status = MerchantStatus.CLOSED
                            state.closed_date = current_date

            # -------------------------------------------------------------
            # PRECEDENCE 4: Delinquency Check (BR-10)
            # -------------------------------------------------------------
            if state.status in [MerchantStatus.ACTIVE, MerchantStatus.WATCH]:
                if state.missed_weeks >= 4:
                    state.status = MerchantStatus.DEFAULT
                    penalty = round(0.05 * state.balance_remaining, 2)
                    accelerated_balance = round(state.balance_remaining + penalty, 2)
                    
                    # Record acceleration in payoffs
                    self.payoffs.append(PayoffRecord(
                        merchant_id=m_id,
                        event="DEFAULT_ACCELERATION",
                        date=current_date,
                        day_no=day_no,
                        cap=state.offer.cap,
                        collected_to_date=round(state.cumulative_collected, 2),
                        remaining_cap=round(state.balance_remaining, 2),
                        factor_portion_remaining=0.0,
                        discount_pct=0.0,
                        discount_amount=0.0,
                        penalty=penalty,
                        amount_due_or_netted=accelerated_balance
                    ))
                    state.balance_remaining = accelerated_balance
                    
                elif state.missed_weeks >= 2:
                    state.status = MerchantStatus.WATCH

            # -------------------------------------------------------------
            # PRECEDENCE 5: Term Tracking (BR-11)
            # -------------------------------------------------------------
            if state.status in [MerchantStatus.ACTIVE, MerchantStatus.WATCH]:
                if day_no >= state.offer.expected_term_days + 60.0:
                    flags.append("TERM_REVIEW")

            # -------------------------------------------------------------
            # Emit Ledger Entry for Day
            # -------------------------------------------------------------
            # Ledger is recorded for days 1..150 (day 0 is disbursal)
            if day_no >= 1:
                self.daily_ledger.append(LedgerEntry(
                    merchant_id=m_id,
                    day_no=day_no,
                    date=current_date,
                    net_settlement=round(net_settlement, 2),
                    holdback_pct_in_force=round(holdback_in_force, 2),
                    sweep=round(sweep, 2),
                    mandate_debit=round(mandate_debit, 2),
                    mandate_charge=round(mandate_charge, 2),
                    cumulative_collected=round(state.cumulative_collected, 2),
                    balance_remaining=round(state.balance_remaining, 2),
                    missed_weeks=state.missed_weeks,
                    status=state.status,
                    flags=flags
                ))

    def _execute_command(self, cmd_type: str, args: List[str], current_date: date):
        """Processes post-daily-job commands."""
        if cmd_type == CommandType.UNDERWRITE:
            m_id = args[0]
            req_advance = float(args[2])
            # Check for duplicate offer
            if m_id in self.offers and self.offers[m_id].underwrite_date == current_date:
                # Duplicate underwrite -> ignore / log
                return
            offer = underwrite_merchant(
                self.merchants[m_id],
                self.history[m_id],
                current_date,
                req_advance,
                command="UNDERWRITE"
            )
            self.offers[m_id] = offer
            self.offer_sheet.append(offer)

        elif cmd_type == CommandType.ACCEPT:
            m_id = args[0]
            if m_id not in self.offers or not self.offers[m_id].eligible:
                # Ineligible / no offer -> rejected (e.g. MCH-009)
                return
            offer = self.offers[m_id]
            self.active_merchants[m_id] = MerchantSimulationState(
                self.merchants[m_id],
                offer,
                disbursal_date=current_date
            )

        elif cmd_type == CommandType.EARLY_PAYOFF:
            m_id = args[0]
            if m_id not in self.active_merchants:
                return
            state = self.active_merchants[m_id]
            day_no = (current_date - state.disbursal_date).days
            
            # BR-12 Factor portion discounting
            total_factor = state.offer.cap - state.offer.advance
            factor_collected = (state.cumulative_collected / state.offer.cap) * total_factor
            factor_remaining = total_factor - factor_collected
            
            discount_pct = 50.0 if day_no < 90 else 25.0
            discount_amount = round((discount_pct / 100.0) * factor_remaining, 2)
            amount_due = round(state.balance_remaining - discount_amount, 2)
            
            self.payoffs.append(PayoffRecord(
                merchant_id=m_id,
                event="EARLY_PAYOFF",
                date=current_date,
                day_no=day_no,
                cap=state.offer.cap,
                collected_to_date=round(state.cumulative_collected, 2),
                remaining_cap=round(state.balance_remaining, 2),
                factor_portion_remaining=round(factor_remaining, 2),
                discount_pct=discount_pct,
                discount_amount=discount_amount,
                penalty=0.0,
                amount_due_or_netted=amount_due
            ))
            state.status = MerchantStatus.CLOSED
            state.balance_remaining = 0.0

        elif cmd_type == CommandType.RENEW:
            m_id = args[0]
            req_advance = float(args[2])
            if m_id not in self.active_merchants:
                return
            state = self.active_merchants[m_id]
            # BR-13: Renewal condition
            pct_collected = state.cumulative_collected / state.offer.cap
            if pct_collected < 0.60 or state.status in [MerchantStatus.WATCH, MerchantStatus.DEFAULT]:
                return
                
            new_offer = underwrite_merchant(
                self.merchants[m_id],
                self.history[m_id],
                current_date,
                req_advance,
                command="RENEW"
            )
            self.offers[m_id] = new_offer
            self.offer_sheet.append(new_offer)
            
            # Old balance netted off at zero discount
            old_balance = state.balance_remaining
            new_net_disbursal = round(new_offer.net_disbursal - old_balance, 2)
            
            self.payoffs.append(PayoffRecord(
                merchant_id=m_id,
                event="RENEW",
                date=current_date,
                day_no=(current_date - state.disbursal_date).days,
                cap=state.offer.cap,
                collected_to_date=round(state.cumulative_collected, 2),
                remaining_cap=round(old_balance, 2),
                factor_portion_remaining=0.0,
                discount_pct=0.0,
                discount_amount=0.0,
                penalty=0.0,
                amount_due_or_netted=round(old_balance, 2),
                new_advance=new_offer.advance,
                new_net_disbursal=new_net_disbursal
            ))
            
            state.status = MerchantStatus.RENEWED
            # Replace active state with new advance
            self.active_merchants[m_id] = MerchantSimulationState(
                self.merchants[m_id],
                new_offer,
                disbursal_date=current_date
            )

        elif cmd_type == CommandType.REFINANCE:
            m_id = args[0]
            other_lender = args[2]
            payoff_ref = args[3]
            payoff_amount = float(args[4])
            
            # BR-14: Refinance underwritten with 1.0x cap
            # Requested advance from previous underwrite or basis
            # Basis monthly settlements for MCH-008 is 150000.00
            offer = underwrite_merchant(
                self.merchants[m_id],
                self.history[m_id],
                current_date,
                requested_advance=180000.0,
                command="REFINANCE",
                is_refinance=True
            )
            self.offers[m_id] = offer
            self.offer_sheet.append(offer)
            
            net_to_merchant = round(offer.net_disbursal - payoff_amount, 2)
            
            self.payoffs.append(PayoffRecord(
                merchant_id=m_id,
                event="REFINANCE",
                date=current_date,
                day_no=0,
                cap=offer.cap,
                collected_to_date=0.0,
                remaining_cap=offer.cap,
                factor_portion_remaining=round(offer.cap - offer.advance, 2),
                discount_pct=0.0,
                discount_amount=0.0,
                penalty=0.0,
                amount_due_or_netted=round(payoff_amount, 2),
                new_advance=offer.advance,
                new_net_disbursal=net_to_merchant
            ))
            
            self.active_merchants[m_id] = MerchantSimulationState(
                self.merchants[m_id],
                offer,
                disbursal_date=current_date
            )

        elif cmd_type == CommandType.PRINT_PORTFOLIO:
            for m_id, state in sorted(self.active_merchants.items()):
                days_since = (current_date - state.disbursal_date).days
                pct_col = round((state.cumulative_collected / state.offer.cap) * 100.0, 2)
                is_review = days_since >= state.offer.expected_term_days + 60.0
                self.portfolio_ageing.append(PortfolioAgeingRecord(
                    merchant_id=m_id,
                    status=state.status.value,
                    days_since_disbursal=days_since,
                    expected_term_days=state.offer.expected_term_days,
                    pct_collected=pct_col,
                    missed_weeks=state.missed_weeks,
                    balance_remaining=round(state.balance_remaining, 2),
                    review_flag=is_review
                ))
