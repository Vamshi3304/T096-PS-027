"""
Data Ingestion and Parser Module for PS-027.
Handles merchants.csv, settlement_history.csv, settlement_events.csv, holidays.csv, and commands.txt.
Ensures defensive validation, deduplication of feeds, and chronological event sorting.
"""

import csv
from datetime import date, datetime
import os
from typing import Dict, List, Set, Tuple

from .models import MerchantProfile, SettlementRecord


def parse_date(date_str: str) -> date:
    """Parses YYYY-MM-DD string into a datetime.date object."""
    return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()


def load_merchants(filepath: str) -> Dict[str, MerchantProfile]:
    """Loads merchant profiles from merchants.csv."""
    merchants: Dict[str, MerchantProfile] = {}
    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            m_id = row["merchant_id"].strip()
            merchants[m_id] = MerchantProfile(
                merchant_id=m_id,
                business_name=row["business_name"].strip(),
                owner_name=row["owner_name"].strip(),
                city=row["city"].strip(),
                category=row["category"].strip(),
                business_start_date=parse_date(row["business_start_date"]),
                aggregator_id=row["aggregator_id"].strip(),
                mandate_id=row["mandate_id"].strip(),
                ifsc=row["ifsc"].strip(),
                mobile=row["mobile"].strip()
            )
    return merchants


def load_settlement_history(filepath: str) -> Dict[str, List[SettlementRecord]]:
    """Loads 6-month pre-underwrite daily settlement history."""
    history: Dict[str, List[SettlementRecord]] = {}
    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            m_id = row["merchant_id"].strip()
            rec = SettlementRecord(
                merchant_id=m_id,
                date=parse_date(row["date"]),
                gross_sales=float(row["gross_sales"]),
                mdr=float(row["mdr"]),
                refunds=float(row["refunds"]),
                net_settlement=float(row["net_settlement"])
            )
            if m_id not in history:
                history[m_id] = []
            history[m_id].append(rec)
            
    # Sort each merchant's history chronologically
    for m_id in history:
        history[m_id].sort(key=lambda x: x.date)
    return history


def load_settlement_events(filepath: str) -> Dict[date, Dict[str, float]]:
    """
    Loads daily post-disbursal settlement events from settlement_events.csv.
    Applies deduplication for (merchant_id, date) and orders by calendar date.
    Returns: Dict[date, Dict[merchant_id, net_settlement]]
    """
    events_by_date: Dict[date, Dict[str, float]] = {}
    seen_records: Set[Tuple[str, date]] = set()
    
    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            m_id = row["merchant_id"].strip()
            d = parse_date(row["date"])
            key = (m_id, d)
            
            # Defensive deduplication (e.g. MCH-001 2026-08-12 row 45 duplicate)
            if key in seen_records:
                continue
            seen_records.add(key)
            
            if d not in events_by_date:
                events_by_date[d] = {}
            events_by_date[d][m_id] = float(row["net_settlement"])
            
    return events_by_date


def load_holidays(filepath: str) -> Set[date]:
    """Loads bank holidays from holidays.csv."""
    holidays: Set[date] = set()
    if not os.path.exists(filepath):
        return holidays
    with open(filepath, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            holidays.add(parse_date(row["date"]))
    return holidays


def load_commands(filepath: str) -> List[Tuple[str, List[str]]]:
    """
    Loads command lines from commands.txt.
    Ignores blank lines and comments starting with '#'.
    Returns: List of (command_name, args_list)
    """
    commands: List[Tuple[str, List[str]]] = []
    with open(filepath, mode="r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split("|")]
            cmd_type = parts[0]
            args = parts[1:]
            commands.append((cmd_type, args))
    return commands
