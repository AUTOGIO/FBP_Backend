#!/usr/bin/env python3
"""NFA Consultation Batch Runner - Processes first 15 NFAs.

This script runs the NFA consultation automation to download DANFE and DAR PDFs
for the first 15 NFAs found in the results table.

Usage:
    export NFA_USERNAME='eduardof'
    export NFA_PASSWORD='atf101010'
    python run_nfa_consultation_batch.py

Or run with visible browser (for debugging):
    python run_nfa_consultation_batch.py --headless=false
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.modules.nfa_atf_automation import run_nfa_job


async def main():
    """Run NFA consultation batch job."""
    parser = argparse.ArgumentParser(
        description="Run NFA consultation automation for first 15 NFAs"
    )
    parser.add_argument(
        "--headless",
        type=str,
        default="true",
        help="Run browser in headless mode (default: true)",
    )
    parser.add_argument(
        "--max-nfas",
        type=int,
        default=15,
        help="Maximum number of NFAs to process (default: 15)",
    )
    parser.add_argument(
        "--wait-between",
        type=int,
        default=4,
        help="Seconds to wait between NFAs (default: 4)",
    )
    parser.add_argument(
        "--data-inicial",
        type=str,
        default="08/12/2025",
        help="Initial date in DD/MM/YYYY format (default: 08/12/2025)",
    )
    parser.add_argument(
        "--data-final",
        type=str,
        default="08/12/2025",
        help="Final date in DD/MM/YYYY format (default: 08/12/2025)",
    )
    parser.add_argument(
        "--matricula",
        type=str,
        default="1595504",
        help="Employee registration number (default: 1595504)",
    )

    args = parser.parse_args()

    # Get credentials from environment
    username = os.getenv("NFA_USERNAME")
    password = os.getenv("NFA_PASSWORD")

    if not username or not password:
        print("❌ ERROR: NFA credentials not found!")
        print()
        print("Please set environment variables:")
        print("  export NFA_USERNAME='eduardof'")
        print("  export NFA_PASSWORD='atf101010'")
        print()
        sys.exit(1)

    # Parse headless flag
    headless = args.headless.lower() in ("true", "1", "yes", "on")

    print("=" * 80)
    print("🚀 NFA CONSULTATION BATCH AUTOMATION")
    print("=" * 80)
    print(f"   Username: {username}")
    print(f"   Matrícula: {args.matricula}")
    print(f"   Date range: {args.data_inicial} to {args.data_final}")
    print(f"   Max NFAs: {args.max_nfas}")
    print(f"   Wait between NFAs: {args.wait_between} seconds")
    print(f"   Headless mode: {headless}")
    print("   Output directory: /Users/dnigga/Downloads/NFA_Outputs")
    print("=" * 80)
    print()

    # Run the job
    result = await run_nfa_job(
        username=username,
        password=password,
        data_inicial=args.data_inicial,
        data_final=args.data_final,
        matricula=args.matricula,
        headless=headless,
        max_nfas=args.max_nfas,
        wait_between_nfas=args.wait_between,
    )

    # Print summary
    print()
    print("=" * 80)
    print("📊 FINAL RESULTS")
    print("=" * 80)

    if result["status"] == "ok":
        print(f"✅ SUCCESS: {result['total_processed']}/{len(result.get('nfas_processed', []))} NFAs processed")
        print()
        print("Processed NFAs:")
        for idx, nfa_result in enumerate(result.get("nfas_processed", []), 1):
            status_icon = "✅" if nfa_result.get("status") == "ok" else "❌"
            print(f"  {idx}. {status_icon} NFA {nfa_result.get('nfa_numero', 'UNKNOWN')}")
            if nfa_result.get("danfe_path"):
                print(f"     → DANFE: {nfa_result['danfe_path']}")
            if nfa_result.get("dar_path"):
                print(f"     → DAR: {nfa_result['dar_path']}")
            if nfa_result.get("error"):
                print(f"     ⚠️  Error: {nfa_result['error']}")
    else:
        print("❌ FAILED!")
        if result.get("error"):
            print(f"   Error: {result['error']}")
        sys.exit(1)

    print()
    print("=" * 80)
    print("📄 Full JSON Result:")
    print("=" * 80)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("=" * 80)
    print()


if __name__ == "__main__":
    asyncio.run(main())
