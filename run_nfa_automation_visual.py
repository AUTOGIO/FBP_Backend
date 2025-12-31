#!/usr/bin/env python3
"""Run NFA automation in visual (headed) mode for debugging and monitoring."""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from app.modules.nfa_atf_automation import run_nfa_job


async def main():
    """Run NFA automation in visual mode."""
    print("=" * 80)
    print("NFA Automation - Visual Mode")
    print("=" * 80)
    print()
    
    # Get credentials from environment or use defaults
    username = os.getenv("NFA_USERNAME", "eduardof")
    password = os.getenv("NFA_PASSWORD", "atf101010")
    
    if not username or not password:
        print("ERROR: NFA_USERNAME and NFA_PASSWORD must be set")
        print("Export them or set in .env file")
        sys.exit(1)
    
    print(f"Username: {username}")
    print(f"Date range: 08/12/2025 to 10/12/2025")
    print(f"Matrícula: 1595504")
    print()
    print("Starting automation in VISUAL mode (browser will be visible)...")
    print()
    
    # Run automation in visual mode
    result = await run_nfa_job(
        username=username,
        password=password,
        data_inicial="08/12/2025",
        data_final="10/12/2025",
        matricula="1595504",
        headless=False,  # Visual mode
    )
    
    # Print final summary
    print()
    print("=" * 80)
    if result["status"] == "ok":
        print("✅ AUTOMATION COMPLETED SUCCESSFULLY")
        print(f"   NFA Number: {result['nfa_numero']}")
        if result.get("danfe_path"):
            print(f"   DANFE: {result['danfe_path']}")
        if result.get("dar_path"):
            print(f"   DAR: {result['dar_path']}")
    else:
        print("❌ AUTOMATION FAILED")
        print(f"   Error: {result.get('error', 'Unknown error')}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
