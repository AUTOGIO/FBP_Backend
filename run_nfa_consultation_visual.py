#!/usr/bin/env python3
"""Visual runner for NFA consultation automation.

This script runs the NFA consultation automation with the browser visible
(headless=False) so you can watch the automation in action.

Usage:
    python run_nfa_consultation_visual.py

Environment variables:
    NFA_USERNAME: ATF username (default: from .env)
    NFA_PASSWORD: ATF password (default: from .env)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.modules.nfa_atf_automation import run_nfa_job


async def main():
    """Run NFA consultation automation in visual mode."""
    print("=" * 80)
    print("NFA Consultation Automation - Visual Mode")
    print("=" * 80)
    print()

    # Get credentials from environment or use defaults
    username = os.getenv("NFA_USERNAME")
    password = os.getenv("NFA_PASSWORD")

    if not username or not password:
        print("⚠️  Warning: NFA_USERNAME and/or NFA_PASSWORD not set in environment")
        print("   Using credentials from .env file if available")
        print()

    print("Configuration:")
    print(f"  - Username: {username or '(from .env)'}")
    print(f"  - Password: {'*' * len(password) if password else '(from .env)'}")
    print("  - Date range: 08/12/2025 to 08/12/2025")
    print("  - Matrícula: 1595504")
    print("  - Max NFAs: 3")
    print("  - Wait between NFAs: 4 seconds")
    print("  - Headless: False (browser will be visible)")
    print()
    print("Starting automation in 3 seconds...")
    print("(You'll see the browser window open)")
    print()

    await asyncio.sleep(3)

    # Run the automation
    result = await run_nfa_job(
        username=username,
        password=password,
        data_inicial="08/12/2025",
        data_final="08/12/2025",
        matricula="1595504",
        headless=False,  # Visual mode
        max_nfas=3,
        wait_between_nfas=4,
    )

    # Print summary
    print()
    print("=" * 80)
    print("Final Summary")
    print("=" * 80)
    print(f"Status: {result['status']}")
    print(f"Total NFAs processed: {result.get('total_processed', 0)}")
    print()

    if result.get("nfas_processed"):
        print("NFAs processed:")
        for idx, nfa in enumerate(result["nfas_processed"], 1):
            print(f"\n  {idx}. NFA {nfa.get('nfa_numero', 'UNKNOWN')}")
            print(f"     Status: {nfa.get('status', 'unknown')}")
            if nfa.get("danfe_path"):
                print(f"     DANFE: {nfa['danfe_path']}")
            if nfa.get("dar_path"):
                print(f"     DAR:   {nfa['dar_path']}")
            if nfa.get("error"):
                print(f"     Error: {nfa['error']}")

    if result.get("error"):
        print(f"\nOverall error: {result['error']}")

    print()
    print("=" * 80)
    print("Automation completed!")
    print("=" * 80)

    return result


if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result["status"] == "ok" else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Automation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
