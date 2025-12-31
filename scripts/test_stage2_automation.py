"""Quick test script for REDESIM Stage 2 automation components.

Tests individual functions without requiring full browser session.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.modules.cadastro.consultar_redesim import (
    _check_contabilista_cfc,
    _validate_cep_viacep,
)


async def test_cep_validation() -> None:
    """Test CEP validation."""
    print("\n[TEST] Testing CEP validation via ViaCEP...")

    # Test valid CEP
    result = await _validate_cep_viacep("58084-150")
    print(f"  Valid CEP test: {result.get('valid', False)}")
    if result.get("valid"):
        print(f"    CEP: {result.get('cep')}")
        print(f"    Logradouro: {result.get('logradouro')}")
        print(f"    Cidade: {result.get('localidade')}")

    # Test invalid format
    result = await _validate_cep_viacep("12345")
    print(f"  Invalid format test: {not result.get('valid', True)}")
    if not result.get("valid"):
        print(f"    Error: {result.get('error')}")


async def test_cfc_check() -> None:
    """Test CFC contabilista check."""
    print("\n[TEST] Testing CFC contabilista check...")

    # Test with a sample CPF (this will attempt real API call)
    result = await _check_contabilista_cfc("048.667.604-86")
    print(f"  CFC check result: {result.get('valid', False)}")
    print(f"    CPF: {result.get('cpf')}")
    print(f"    Accessible: {result.get('cfc_accessible', False)}")
    if result.get("regularity_status"):
        print(f"    Status: {result.get('regularity_status')}")
    if result.get("error"):
        print(f"    Error: {result.get('error')}")

    # Test invalid format
    result = await _check_contabilista_cfc("12345")
    print(f"  Invalid CPF format test: {not result.get('valid', True)}")
    if not result.get("valid"):
        print(f"    Error: {result.get('error')}")


async def main() -> None:
    """Run all component tests."""
    print("=" * 60)
    print("REDESIM Stage 2 Automation - Component Tests")
    print("=" * 60)

    try:
        await test_cep_validation()
        await test_cfc_check()

        print("\n" + "=" * 60)
        print("Component tests completed!")
        print("=" * 60)
        print("\nNote: Full integration test requires:")
        print("  - ATF_USERNAME and ATF_PASSWORD environment variables")
        print("  - Authenticated browser session")
        print("  - Run: python3 scripts/run_redesim_stage2.py")

    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
