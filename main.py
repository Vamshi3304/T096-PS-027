"""
PS-027 Merchant Cash Advance & Revenue-Based Financing Engine
CLI Entrypoint and Execution Runner.
Team: T096
"""

import argparse
import os
import sys

from src.ingestion import (
    load_commands,
    load_holidays,
    load_merchants,
    load_settlement_events,
    load_settlement_history
)
from src.reports import (
    export_daily_ledger,
    export_offer_sheet,
    export_payoffs,
    export_portfolio_ageing
)
from src.simulator import SimulationEngine


def main():
    parser = argparse.ArgumentParser(
        description="PS-027 MCA & Revenue-Based Financing Engine"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "data"),
        help="Path to directory containing input CSVs and commands.txt"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "output"),
        help="Path to directory where output CSVs will be generated"
    )
    args = parser.parse_args()

    data_dir = os.path.abspath(args.data_dir)
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    print("======================================================================")
    print("  PS-027: MCA & REVENUE-BASED FINANCING ENGINE (TEAM T096)")
    print("======================================================================")
    print(f"Loading input data from: {data_dir}")

    merchants_path = os.path.join(data_dir, "merchants.csv")
    history_path = os.path.join(data_dir, "settlement_history.csv")
    events_path = os.path.join(data_dir, "settlement_events.csv")
    holidays_path = os.path.join(data_dir, "holidays.csv")
    commands_path = os.path.join(data_dir, "commands.txt")

    for p in [merchants_path, history_path, events_path, commands_path]:
        if not os.path.exists(p):
            print(f"Error: Missing required input file: {p}", file=sys.stderr)
            sys.exit(1)

    merchants = load_merchants(merchants_path)
    history = load_settlement_history(history_path)
    events_by_date = load_settlement_events(events_path)
    holidays = load_holidays(holidays_path)
    commands = load_commands(commands_path)

    print(f"Ingested {len(merchants)} merchants, {len(history)} settlement histories.")
    print(f"Ingested events across {len(events_by_date)} dates, {len(commands)} commands.")

    print("\nRunning daily job simulation and processing command feed...")
    engine = SimulationEngine(
        merchants=merchants,
        history=history,
        events_by_date=events_by_date,
        holidays=holidays,
        commands=commands
    )
    engine.run_simulation()

    print("\nExporting output CSVs...")
    offer_sheet_file = os.path.join(output_dir, "offer_sheet.csv")
    daily_ledger_file = os.path.join(output_dir, "daily_ledger.csv")
    payoffs_file = os.path.join(output_dir, "payoffs.csv")
    portfolio_file = os.path.join(output_dir, "portfolio_ageing.csv")

    export_offer_sheet(engine.offer_sheet, offer_sheet_file)
    export_daily_ledger(engine.daily_ledger, daily_ledger_file)
    export_payoffs(engine.payoffs, payoffs_file)
    export_portfolio_ageing(engine.portfolio_ageing, portfolio_file)

    print(f"  ✓ {offer_sheet_file} ({len(engine.offer_sheet)} rows)")
    print(f"  ✓ {daily_ledger_file} ({len(engine.daily_ledger)} rows)")
    print(f"  ✓ {payoffs_file} ({len(engine.payoffs)} rows)")
    print(f"  ✓ {portfolio_file} ({len(engine.portfolio_ageing)} rows)")

    print("\nExecution completed successfully!")


if __name__ == "__main__":
    main()
