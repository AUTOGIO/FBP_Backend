#!/usr/bin/env python3
"""CLI wrapper for NFA ATF Automation (FIS_308 Consultation).

This script provides a direct command-line interface to run the NFA consultation
automation that processes all available NFAs and triggers PDF downloads.

Usage:
    # Process all NFAs with both DANFE and DAR (default)
    python run_nfa_automation.py

    # Process only DANFE for all NFAs
    python run_nfa_automation.py --mode danfe

    # Process only DAR for all NFAs
    python run_nfa_automation.py --mode dar

    # Custom date range
    python run_nfa_automation.py --data-inicial 08/12/2025 --data-final 08/12/2025

    # Custom matrícula
    python run_nfa_automation.py --matricula 1595504

    # Close browser at end
    python run_nfa_automation.py --close-browser

    # Headless mode
    python run_nfa_automation.py --headless

Environment Variables:
    NFA_USERNAME: ATF username (required if not provided via --username)
    NFA_PASSWORD: ATF password (required if not provided via --password)
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from app.modules.nfa_atf_automation import run_nfa_job


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="NFA ATF Automation - FIS_308 Consultation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
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
        "--data-inicial",
        default="08/12/2025",
        help="Initial date in DD/MM/YYYY format (default: 08/12/2025)",
    )
    parser.add_argument(
        "--data-final",
        default="08/12/2025",
        help="Final date in DD/MM/YYYY format (default: 08/12/2025)",
    )
    parser.add_argument(
        "--matricula",
        default="1595504",
        help="Employee registration number (default: 1595504)",
    )
    parser.add_argument(
        "--mode",
        choices=["danfe", "dar", "both"],
        default="both",
        help="Action mode: 'danfe' (only DANFE), 'dar' (only DAR), or 'both' (both, two passes) (default: both)",
    )
    parser.add_argument(
        "--close-browser",
        action="store_true",
        default=False,
        help="Close browser at end (default: False - leave browser open)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode (default: False)",
    )
    parser.add_argument(
        "--wait-between",
        type=int,
        default=3,
        help="Seconds to wait between NFAs (default: 3)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output result as JSON only (default: human-readable summary + JSON)",
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
        print(
            f"Error: Invalid date format for data-inicial: {args.data_inicial}",
            file=sys.stderr,
        )
        print("Expected format: DD/MM/YYYY (e.g., 08/12/2025)", file=sys.stderr)
        return 1

    if not validate_date(args.data_final):
        print(
            f"Error: Invalid date format for data-final: {args.data_final}",
            file=sys.stderr,
        )
        print("Expected format: DD/MM/YYYY (e.g., 08/12/2025)", file=sys.stderr)
        return 1

    # Check credentials - try env vars first, then let function use settings from .env
    username = args.username or os.getenv("NFA_USERNAME")
    password = args.password or os.getenv("NFA_PASSWORD")

    # If not provided, pass None and let run_nfa_job use settings (which loads from .env)
    # This allows the function to use pydantic_settings to load from .env file

    # Run automation
    try:
        print("\n" + "=" * 80)
        print("NFA ATF Automation - FIS_308 Consultation")
        print("=" * 80)
        print(f"Mode: {args.mode}")
        print(f"Date range: {args.data_inicial} to {args.data_final}")
        print(f"Matrícula: {args.matricula}")
        print(f"Close browser: {args.close_browser}")
        print(f"Headless: {args.headless}")
        print(f"Wait between NFAs: {args.wait_between} seconds")
        print("=" * 80 + "\n")

        result = asyncio.run(
            run_nfa_job(
                username=username,
                password=password,
                data_inicial=args.data_inicial,
                data_final=args.data_final,
                matricula=args.matricula,
                mode=args.mode,
                close_browser=args.close_browser,
                headless=args.headless,
                wait_between_nfas=args.wait_between,
            ),
        )

        # Output result
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            # The function already prints a summary, but we can add a final status
            status_emoji = {
                "success": "✅",
                "partial": "⚠️",
                "failed": "❌",
            }.get(result.get("status", "unknown"), "❓")

            print("\n" + "=" * 80)
            print(
                f"Final Status: {status_emoji} {result.get('status', 'unknown').upper()}"
            )
            print("=" * 80)
            print(f"NFAs Processed: {result.get('n_nfas_processed', 0)}")
            print(f"Total NFAs Found: {len(result.get('nfas', []))}")
            print(f"Mode: {result.get('mode', 'unknown')}")
            print(f"Started: {result.get('started_at', 'N/A')}")
            print(f"Finished: {result.get('finished_at', 'N/A')}")
            print("=" * 80 + "\n")

        # Return exit code
        status = result.get("status", "failed")
        if status == "success":
            return 0
        elif status == "partial":
            return 2  # Partial success
        else:
            return 1  # Failed

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
