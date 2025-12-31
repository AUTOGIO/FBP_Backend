#!/usr/bin/env python3
"""Visual test script for NFA automation - runs with headless=False."""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.modules.nfa_atf_automation import run_nfa_job


async def main():
    """Run NFA automation in visual mode."""
    print("=" * 80)
    print("NFA Automation - Visual Mode")
    print("=" * 80)
    print("\nRunning with headless=False (browser will be visible)")
    print("Make sure Funcionário Emitente block is filled and Pesquisar is clicked\n")
    
    # Get credentials from environment or use defaults
    username = os.getenv("NFA_USERNAME", "eduardof")
    password = os.getenv("NFA_PASSWORD", "atf101010")
    
    result = await run_nfa_job(
        username=username,
        password=password,
        data_inicial="08/12/2025",
        data_final="10/12/2025",
        matricula="1595504",
        headless=False,  # Visual mode
    )
    
    print("\n" + "=" * 80)
    if result["status"] == "ok":
        print("✅ Automation completed successfully!")
        print(f"   NFA Number: {result.get('nfa_numero', 'N/A')}")
        print(f"   DANFE: {result.get('danfe_path', 'N/A')}")
        print(f"   DAR: {result.get('dar_path', 'N/A')}")
    else:
        print("❌ Automation failed!")
        print(f"   Error: {result.get('error', 'Unknown error')}")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
