#!/usr/bin/env python3
"""Quick test runner for nfa_atf_automation module."""

import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from app.modules.nfa_atf_automation import run_nfa_job


async def main():
    """Run NFA automation job."""
    print("=" * 60)
    print("NFA ATF Automation - Test Run")
    print("=" * 60)
    print()

    # Run the automation with visible browser
    result = await run_nfa_job(
        data_inicial="08/12/2025",
        data_final="10/12/2025",
        matricula="1595504",
        headless=False,  # Run with visible browser
    )

    # Print results
    print("\n" + "=" * 60)
    print("Results:")
    print("=" * 60)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("=" * 60)

    # Return exit code
    return 0 if result.get("status") == "ok" else 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
