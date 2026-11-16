"""
Domain models, enums, dataclasses, and custom exceptions for PS-027.
Merchant Cash Advance (MCA) & Revenue-Based Financing (RBF) Engine.
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Dict, List, Optional, Set


class MerchantStatus(str, Enum):
    PROSPECT = "PROSPECT"
    ACTIVE = "ACTIVE"
    WATCH = "WATCH"
    DEFAULT = "DEFAULT"
    CLOSED = "CLOSED"
    RENEWED = "RENEWED"


class CommandType(str, Enum):
    UNDERWRITE = "UNDERWRITE"
    ACCEPT = "ACCEPT"
    MANDATE_FAIL = "MANDATE_FAIL"
    EARLY_PAYOFF = "EARLY_PAYOFF"
    RENEW = "RENEW"
    REFINANCE = "REFINANCE"
    PRINT_PORTFOLIO = "PRINT_PORTFOLIO"


@dataclass
class MerchantProfile:
    merchant_id: str
    business_name: str
    owner_name: str
    city: str
    category: str
    business_start_date: date
    aggregator_id: str
    mandate_id: str
    ifsc: str
    mobile: str


@dataclass
class SettlementRecord:
    merchant_id: str
    date: date
    gross_sales: float
    mdr: float
    refunds: float
    net_settlement: float


@dataclass
class UnderwritingOffer:
    merchant_id: str
    command: str
    underwrite_date: date
    eligible: bool
    failed_rule_ids: List[str]
    avg_monthly_6m: float
    avg_monthly_3m: float
    basis_monthly: float
    cv: float
    factor: Optional[float]
    advance: float
    cap: float
    origination_fee: float
    gst_on_fee: float
    net_disbursal: float
    holdback_pct: float
    avg_daily_settlement: float
    expected_term_days: float
    effective_apr: float


@dataclass
class LedgerEntry:
    merchant_id: str
    day_no: int
    date: date
    net_settlement: float
    holdback_pct_in_force: float
    sweep: float
    mandate_debit: float
    mandate_charge: float
    cumulative_collected: float
    balance_remaining: float
    missed_weeks: int
    status: MerchantStatus
    flags: List[str] = field(default_factory=list)


@dataclass
class PayoffRecord:
    merchant_id: str
    event: str
    date: date
    day_no: int
    cap: float
    collected_to_date: float
    remaining_cap: float
    factor_portion_remaining: float
    discount_pct: float
    discount_amount: float
    penalty: float
    amount_due_or_netted: float
    new_advance: Optional[float] = None
    new_net_disbursal: Optional[float] = None


@dataclass
class PortfolioAgeingRecord:
    merchant_id: str
    status: str
    days_since_disbursal: int
    expected_term_days: float
    pct_collected: float
    missed_weeks: int
    balance_remaining: float
    review_flag: bool


class MCAEngineError(Exception):
    """Base exception for MCA Engine."""
    pass


class IneligibleMerchantError(MCAEngineError):
    """Raised when an ineligible merchant attempts restricted operations."""
    pass


class OfferNotFoundError(MCAEngineError):
    """Raised when accepting or referencing an offer that does not exist."""
    pass


class DuplicateOfferError(MCAEngineError):
    """Raised or logged when an underwriting request is duplicated."""
    pass


class InvalidOperationError(MCAEngineError):
    """Raised when an operation violates state machine constraints."""
    pass
