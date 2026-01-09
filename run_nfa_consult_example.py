#!/usr/bin/env python3
"""Example script to run NFA consultation automation.

This script demonstrates how to use the run_nfa_job function from
app.modules.nfa_atf_automation to consult and download NFA PDFs.

Usage:
    export NFA_USERNAME='your_username'
    export NFA_PASSWORD='your_password'
    python run_nfa_consult_example.py
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
    """Run NFA consultation automation."""
    # Get credentials from environment or use defaults
    username = os.getenv("NFA_USERNAME")
    password = os.getenv("NFA_PASSWORD")

    if not username or not password:
        print("ERROR: NFA_USERNAME and NFA_PASSWORD environment variables must be set")
        print("\nExample:")
        print("  export NFA_USERNAME='eduardof'")
        print("  export NFA_PASSWORD='atf101010'")
        print("  python run_nfa_consult_example.py")
        sys.exit(1)

    print("=" * 80)
    print("NFA Consultation Automation")
    print("=" * 80)
    print(f"Username: {username}")
    print("Date range: 08/12/2025 to 08/12/2025")
    print("Matrícula: 1595504")
    print("=" * 80)
    print()

    # Run the automation job
    # Note: Set headless=False to see the browser in action
    result = await run_nfa_job(
        username=username,
        password=password,
        data_inicial="08/12/2025",
        data_final="08/12/2025",
        matricula="1595504",
        headless=False,  # Set to True for headless mode
    )

    # Check result
    if result["status"] == "ok":
        print("\n✅ Automation completed successfully!")
        if result.get("danfe_path"):
            print(f"   DANFE: {result['danfe_path']}")
        if result.get("dar_path"):
            print(f"   DAR: {result['dar_path']}")
    else:
        print(f"\n❌ Automation failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
