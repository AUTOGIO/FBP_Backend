#!/usr/bin/env python3
"""NFA Form Filling Diagnostic Script
Tests all form filling components and reports issues.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright

from app.core.config import settings
from app.modules.nfa.atf_frames import wait_for_nfa_fields, wait_for_nfa_form_ready
from app.modules.nfa.atf_login import navigate_to_nfa_form, perform_login
from app.modules.nfa.campos_fixos_filler import preencher_campos_fixos
from app.modules.nfa.destinatario_filler import preencher_destinatario
from app.modules.nfa.emitente_filler import preencher_emitente
from app.modules.nfa.endereco_filler import preencher_endereco
from app.modules.nfa.form_filler import fill_nfa_form_complete
from app.modules.nfa.nfa_context import resolve_nfa_context, wait_for_nfa_ready
from app.modules.nfa.produto_filler import adicionar_item
from app.modules.nfa.screenshot_utils import save_screenshot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DiagnosticResult:
    """Track diagnostic test results."""

    def __init__(self):
        self.passed = []
        self.failed = []
        self.warnings = []

    def add_pass(self, test_name: str, details: str = ""):
        self.passed.append((test_name, details))
        logger.info(f"✓ PASS: {test_name} {details}")

    def add_fail(self, test_name: str, error: str):
        self.failed.append((test_name, error))
        logger.error(f"✗ FAIL: {test_name} - {error}")

    def add_warning(self, test_name: str, warning: str):
        self.warnings.append((test_name, warning))
        logger.warning(f"⚠ WARN: {test_name} - {warning}")

    def print_summary(self):
        print("\n" + "=" * 80)
        print("NFA FORM FILLING DIAGNOSTIC SUMMARY")
        print("=" * 80)
        print(f"\n✓ Passed: {len(self.passed)}")
        for test, details in self.passed:
            print(f"  - {test}" + (f" ({details})" if details else ""))
        print(f"\n✗ Failed: {len(self.failed)}")
        for test, error in self.failed:
            print(f"  - {test}: {error}")
        print(f"\n⚠ Warnings: {len(self.warnings)}")
        for test, warning in self.warnings:
            print(f"  - {test}: {warning}")
        print("\n" + "=" * 80)


async def test_login(result: DiagnosticResult, page):
    """Test login flow."""
    try:
        logger.info("Testing login...")
        success = await perform_login(page)
        if success:
            result.add_pass("Login", "Successfully logged in")
        else:
            result.add_fail("Login", "Login returned False")
    except Exception as e:
        result.add_fail("Login", str(e))


async def test_navigation(result: DiagnosticResult, page):
    """Test navigation to NFA form."""
    try:
        logger.info("Testing navigation to NFA form...")
        success = await navigate_to_nfa_form(page)
        if success:
            result.add_pass("Navigation", "Successfully navigated to NFA form")
        else:
            result.add_fail("Navigation", "Navigation returned False")
    except Exception as e:
        result.add_fail("Navigation", str(e))


async def test_form_ready(result: DiagnosticResult, page):
    """Test form readiness detection."""
    try:
        logger.info("Testing form ready detection...")
        ready = await wait_for_nfa_form_ready(page, timeout=30000)
        if ready:
            result.add_pass("Form Ready", "Form detected as ready")
        else:
            result.add_warning("Form Ready", "Form ready check returned False")
    except Exception as e:
        result.add_fail("Form Ready", str(e))


async def test_context_resolution(result: DiagnosticResult, page):
    """Test NFA context resolution."""
    try:
        logger.info("Testing context resolution...")
        ctx = await resolve_nfa_context(page)
        if ctx:
            ctx_type = type(ctx).__name__
            result.add_pass("Context Resolution", f"Resolved as {ctx_type}")
            try:
                await wait_for_nfa_ready(ctx, timeout=30000)
                result.add_pass("Context Ready", "Context is ready for interaction")
            except Exception as e:
                result.add_fail("Context Ready", str(e))
        else:
            result.add_fail("Context Resolution", "Failed to resolve context")
    except Exception as e:
        result.add_fail("Context Resolution", str(e))


async def test_field_detection(result: DiagnosticResult, page):
    """Test field detection."""
    try:
        logger.info("Testing field detection...")
        frame = await wait_for_nfa_fields(page, timeout=30000)
        if frame:
            result.add_pass("Field Detection", "Fields detected successfully")
        else:
            result.add_fail("Field Detection", "No fields detected")
    except Exception as e:
        result.add_fail("Field Detection", str(e))


async def test_campos_fixos(result: DiagnosticResult, page):
    """Test fixed fields filling."""
    try:
        logger.info("Testing campos fixos filling...")
        ctx = await resolve_nfa_context(page)
        await wait_for_nfa_ready(ctx, timeout=30000)
        ctx_result = await preencher_campos_fixos(ctx)
        if ctx_result:
            result.add_pass("Campos Fixos", "Fixed fields filled successfully")
        else:
            result.add_warning("Campos Fixos", "Fixed fields returned None")
    except Exception as e:
        result.add_fail("Campos Fixos", str(e))


async def test_emitente(result: DiagnosticResult, page):
    """Test emitente filling."""
    try:
        logger.info("Testing emitente filling...")
        ctx = await resolve_nfa_context(page)
        await wait_for_nfa_ready(ctx, timeout=30000)
        # Use a test CNPJ
        test_cnpj = "28842017000105"
        ctx_result = await preencher_emitente(ctx, test_cnpj)
        if ctx_result:
            result.add_pass("Emitente", f"Emitente filled with CNPJ {test_cnpj}")
        else:
            result.add_fail("Emitente", "Emitente filling returned None")
    except Exception as e:
        result.add_fail("Emitente", str(e))


async def test_destinatario(result: DiagnosticResult, page):
    """Test destinatario filling."""
    try:
        logger.info("Testing destinatario filling...")
        ctx = await resolve_nfa_context(page)
        await wait_for_nfa_ready(ctx, timeout=30000)
        # Use a test CPF
        test_cpf = "73825506215"
        ctx_result = await preencher_destinatario(ctx, test_cpf)
        if ctx_result:
            result.add_pass("Destinatario", f"Destinatario filled with CPF {test_cpf}")
        else:
            result.add_fail("Destinatario", "Destinatario filling returned None")
    except Exception as e:
        result.add_fail("Destinatario", str(e))


async def test_endereco(result: DiagnosticResult, page):
    """Test endereco filling."""
    try:
        logger.info("Testing endereco filling...")
        ctx = await resolve_nfa_context(page)
        await wait_for_nfa_ready(ctx, timeout=30000)
        test_endereco = {
            "cep": "58000000",
            "logradouro": "Rua Test",
            "numero": "123",
            "bairro": "Centro",
            "uf": "PB",
        }
        ctx_result = await preencher_endereco(ctx, test_endereco)
        if ctx_result:
            result.add_pass("Endereco", "Endereco filled successfully")
        else:
            result.add_fail("Endereco", "Endereco filling returned None")
    except Exception as e:
        result.add_fail("Endereco", str(e))


async def test_produto(result: DiagnosticResult, page):
    """Test produto filling."""
    try:
        logger.info("Testing produto filling...")
        ctx = await resolve_nfa_context(page)
        await wait_for_nfa_ready(ctx, timeout=30000)
        test_item = {
            "descricao": "Test Product",
            "ncm": "0000.00.00",
            "unidade": "UN",
            "valor_unitario": "100",
            "quantidade": "1",
            "aliquota": "0",
            "cst": "41",
        }
        ctx_result = await adicionar_item(ctx, test_item)
        if ctx_result:
            result.add_pass("Produto", "Produto filled successfully")
        else:
            result.add_fail("Produto", "Produto filling returned None")
    except Exception as e:
        result.add_fail("Produto", str(e))


async def test_full_form_filling(result: DiagnosticResult, page):
    """Test complete form filling."""
    try:
        logger.info("Testing full form filling...")
        form_data = {
            "emitente": {"cnpj": "28842017000105"},
            "destinatario": {"documento": "73825506215"},
            "endereco": {
                "cep": "58000000",
                "logradouro": "Rua Test",
                "numero": "123",
                "bairro": "Centro",
                "uf": "PB",
            },
            "item": {
                "descricao": "Test Product",
                "ncm": "0000.00.00",
                "unidade": "UN",
                "valor_unitario": "100",
                "quantidade": "1",
                "aliquota": "0",
            },
        }
        success = await fill_nfa_form_complete(page, form_data)
        if success:
            result.add_pass("Full Form Filling", "Complete form filled successfully")
        else:
            result.add_fail("Full Form Filling", "Form filling returned False")
    except Exception as e:
        result.add_fail("Full Form Filling", str(e))


async def run_diagnostics():
    """Run all diagnostic tests."""
    result = DiagnosticResult()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            # Test login
            await test_login(result, page)
            await page.wait_for_timeout(2000)

            # Test navigation
            await test_navigation(result, page)
            await page.wait_for_timeout(3000)

            # Test form readiness
            await test_form_ready(result, page)
            await page.wait_for_timeout(1000)

            # Test context resolution
            await test_context_resolution(result, page)
            await page.wait_for_timeout(1000)

            # Test field detection
            await test_field_detection(result, page)
            await page.wait_for_timeout(1000)

            # Test individual fillers
            await test_campos_fixos(result, page)
            await page.wait_for_timeout(2000)

            await test_emitente(result, page)
            await page.wait_for_timeout(2000)

            await test_destinatario(result, page)
            await page.wait_for_timeout(2000)

            await test_endereco(result, page)
            await page.wait_for_timeout(2000)

            await test_produto(result, page)
            await page.wait_for_timeout(2000)

            # Save final screenshot
            await save_screenshot(page, None, filename="diagnostic_final.png")

            # Test full form filling (requires fresh page)
            logger.info("Re-navigating for full form test...")
            await navigate_to_nfa_form(page)
            await page.wait_for_timeout(3000)
            await test_full_form_filling(result, page)

        except Exception as e:
            result.add_fail("Diagnostic Execution", f"Unexpected error: {e}")
            await save_screenshot(page, None, filename="diagnostic_error.png")
        finally:
            result.print_summary()
            input("\nPress ENTER to close browser...")
            await browser.close()

    return result


if __name__ == "__main__":
    asyncio.run(run_diagnostics())
