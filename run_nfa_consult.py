#!/usr/bin/env python3
"""Quick runner for NFA consultation automation."""

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
    """Run NFA consultation job."""
    # Get credentials from environment or use provided defaults
    username = os.getenv("NFA_USERNAME", "eduardof")
    password = os.getenv("NFA_PASSWORD", "atf101010")
    matricula = "1595504"
    
    print("🚀 Starting NFA consultation automation...")
    print(f"   Username: {username}")
    print(f"   Matrícula: {matricula}")
    print(f"   Date range: 08/12/2025 to 10/12/2025")
    print()
    
    # Run the job
    result = await run_nfa_job(
        username=username,
        password=password,
        data_inicial="08/12/2025",
        data_final="10/12/2025",
        matricula=matricula,
    )
    
    # Print results
    print()
    print("=" * 60)
    print("📊 RESULTS")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print()
    
    if result["status"] == "ok":
        print("✅ SUCCESS!")
        if result.get("danfe_path"):
            print(f"   DANFE: {result['danfe_path']}")
        if result.get("dar_path"):
            print(f"   DAR: {result['dar_path']}")
        if result.get("nfa_numero"):
            print(f"   NFA Number: {result['nfa_numero']}")
    else:
        print("❌ FAILED!")
        if result.get("error"):
            print(f"   Error: {result['error']}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
