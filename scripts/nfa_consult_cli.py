#!/usr/bin/env python3
"""CLI script for NFA consultation automation.

This script allows direct execution of NFA consultation automation
without going through the FastAPI server.

Usage:
    python scripts/nfa_consult_cli.py --data-inicial 08/12/2025 --data-final 10/12/2025
    python scripts/nfa_consult_cli.py --data-inicial 08/12/2025 --data-final 10/12/2025 --matricula 1595504
    python scripts/nfa_consult_cli.py --data-inicial 08/12/2025 --data-final 10/12/2025 --username USER --password PASS
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from app.modules.nfa_consult.tasks import run_nfa_consult_automation


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="NFA Consultation Automation CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "--data-inicial",
        required=True,
        help="Initial date in DD/MM/YYYY format (e.g., 08/12/2025)",
    )
    parser.add_argument(
        "--data-final",
        required=True,
        help="Final date in DD/MM/YYYY format (e.g., 10/12/2025)",
    )
    parser.add_argument(
        "--matricula",
        default="1595504",
        help="Employee registration number (default: 1595504)",
    )
    parser.add_argument(
        "--username",
        default=None,
        help="ATF username (uses NFA_USERNAME env var if not provided)",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="ATF password (uses NFA_PASSWORD env var if not provided)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode (default: False)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output result as JSON (default: human-readable)",
    )

    return parser.parse_args()


def validate_date(date_str: str) -> bool:
    """Validate date format DD/MM/YYYY."""
    try:
        parts = date_str.split("/")
        if len(parts) != 3:
            return False
        day, month, year = parts
        if len(day) != 2 or len(month) != 2 or len(year) != 4:
            return False
        int(day)
        int(month)
        int(year)
        return True
    except (ValueError, AttributeError):
        return False


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Validate dates
    if not validate_date(args.data_inicial):
        print(f"Error: Invalid date format for data-inicial: {args.data_inicial}")
        print("Expected format: DD/MM/YYYY (e.g., 08/12/2025)")
        return 1

    if not validate_date(args.data_final):
        print(f"Error: Invalid date format for data-final: {args.data_final}")
        print("Expected format: DD/MM/YYYY (e.g., 10/12/2025)")
        return 1

    # Run automation
    try:
        result = asyncio.run(
            run_nfa_consult_automation(
                username=args.username,
                password=args.password,
                data_inicial=args.data_inicial,
                data_final=args.data_final,
                matricula=args.matricula,
                headless=args.headless,
            ),
        )

        # Output result
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("\n" + "=" * 60)
            print("NFA Consultation Automation Result")
            print("=" * 60)
            print(f"Status: {result.get('status', 'unknown')}")
            print(f"NFA Number: {result.get('nfa_numero', 'N/A')}")
            print(f"DANFE Path: {result.get('danfe_path', 'N/A')}")
            print(f"DAR Path: {result.get('dar_path', 'N/A')}")
            print(f"Started: {result.get('started_at', 'N/A')}")
            print(f"Finished: {result.get('finished_at', 'N/A')}")
            if result.get("error"):
                print(f"Error: {result['error']}")
            print("=" * 60 + "\n")

        # Return exit code
        return 0 if result.get("status") == "ok" else 1

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
