#!/usr/bin/env python3
"""Live NFA Form Filling Demo
Fills form automatically after entering only CPF/CNPJ.
Shows the process in real-time with browser visible.
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
from app.modules.nfa.atf_login import navigate_to_nfa_form, perform_login
from app.modules.nfa.campos_fixos_filler import preencher_campos_fixos
from app.modules.nfa.destinatario_filler import preencher_destinatario
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

# Data from the DANFE you provided
DANFE_DATA = {
    "emitente": {
        "cnpj": "28842017000105",  # IKLI TECNOLOGIA LTDA
    },
    "destinatario": {
        "documento": "51603144234",  # ALEXANDRA PEREIRA SANTOS
        "endereco": {
            "cep": "69083010",
            "logradouro": "R CONSTELACAO DE GEMEOS",
            "numero": "150",
            "complemento": "CASA 14",
            "bairro": "ALEIXO",
            "municipio": "MANAUS",
            "uf": "AM",
        },
    },
    "item": {
        "descricao": "1 - SID241",
        "ncm": "0000.00.00",
        "unidade": "UN",
        "valor_unitario": "1100",
        "quantidade": "1",
        "aliquota": "0",
        "cst": "41",
        "cfop": "6908",
    },
    "valores_fixos": {
        "natureza_operacao": "REMESSA",
        "motivo": "DESPACHO",
        "reparticao_fiscal": "90102008",
        "codigo_municipio": "2051-6",
        "tipo_operacao": "SAIDA",
        "cfop": "6908",
    },
    "informacoes_adicionais": "Remessa por conta de contrato de locacao",
}


async def live_fill_demo():
    """Live demonstration of automatic form filling."""
    print("=" * 80)
    print("NFA LIVE FORM FILLING DEMO")
    print("=" * 80)
    print("\nThis demo will:")
    print("1. Login to SEFAZ ATF")
    print("2. Navigate to NFA form")
    print("3. Fill ONLY the CPF/CNPJ field")
    print("4. Automatically fill all other fields")
    print("\nStarting in 2 seconds...")
    await asyncio.sleep(2)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            slow_mo=500,  # Slow down for visibility
        )
        page = await browser.new_page()

        try:
            # Step 1: Login
            print("\n[STEP 1] Logging in...")
            logger.info("Starting login...")
            success = await perform_login(page)
            if not success:
                print("❌ Login failed!")
                return
            print("✅ Login successful!")
            await page.wait_for_timeout(2000)

            # Step 2: Navigate to NFA form
            print("\n[STEP 2] Navigating to NFA form...")
            logger.info("Navigating to NFA form...")
            success = await navigate_to_nfa_form(page, timeout=90000)  # Longer timeout
            if not success:
                print("❌ Navigation failed!")
                print("   Checking if form is already loaded...")
                # Try to continue anyway - maybe form is there but detection failed
                try:
                    from app.modules.nfa.nfa_context import resolve_nfa_context, wait_for_nfa_ready
                    ctx = await resolve_nfa_context(page)
                    await wait_for_nfa_ready(ctx, timeout=30000)
                    print("✅ Form found via alternative detection!")
                    success = True
                except Exception as e:
                    print(f"❌ Form not found: {e}")
                    await save_screenshot(page, None, filename="navigation_failed.png")
                    return
            if success:
                print("✅ Navigated to NFA form!")
                await page.wait_for_timeout(3000)

            # Step 3: Resolve context and wait for form ready
            print("\n[STEP 3] Waiting for form to be ready...")
            ctx = await resolve_nfa_context(page)
            await wait_for_nfa_ready(ctx, timeout=45000)
            print("✅ Form is ready!")
            await page.wait_for_timeout(2000)

            # Step 4: Fill fixed fields (natureza, motivo, etc.)
            print("\n[STEP 4] Filling fixed fields (Natureza, Motivo, CFOP, etc.)...")
            valores_fixos = DANFE_DATA["valores_fixos"]
            ctx_result = await preencher_campos_fixos(ctx, valores_fixos)
            if ctx_result:
                ctx = ctx_result
                print("✅ Fixed fields filled!")
            else:
                print("⚠️  Fixed fields had issues, continuing...")
            await page.wait_for_timeout(2000)

            # Step 5: Fill Emitente (CNPJ)
            print("\n[STEP 5] Filling Emitente (CNPJ: 28.842.017/0001-05)...")
            emitente_cnpj = DANFE_DATA["emitente"]["cnpj"]
            ctx_result = await preencher_emitente(ctx, emitente_cnpj)
            if ctx_result:
                ctx = ctx_result
                print("✅ Emitente filled!")
            else:
                print("❌ Emitente filling failed!")
                return
            await page.wait_for_timeout(3000)

            # Step 6: Fill ONLY Destinatario CPF (this triggers auto-fill)
            print("\n[STEP 6] Filling Destinatario CPF (516.031.442-34)...")
            print("   → System will auto-fill address and other data...")
            destinatario_doc = DANFE_DATA["destinatario"]["documento"]
            ctx_result = await preencher_destinatario(ctx, destinatario_doc)
            if ctx_result:
                ctx = ctx_result
                print("✅ Destinatario CPF filled! Waiting for auto-fill...")
            else:
                print("❌ Destinatario filling failed!")
                return
            await page.wait_for_timeout(5000)  # Wait for system to auto-fill

            # Step 7: Fill Endereco (if not auto-filled)
            print("\n[STEP 7] Filling Endereco details...")
            endereco_data = DANFE_DATA["destinatario"]["endereco"]
            ctx_result = await preencher_endereco(ctx, endereco_data)
            if ctx_result:
                ctx = ctx_result
                print("✅ Endereco filled!")
            else:
                print("⚠️  Endereco had issues, continuing...")
            await page.wait_for_timeout(2000)

            # Step 8: Fill Produto
            print("\n[STEP 8] Filling Produto (1 - SID241, Valor: R$ 1.100,00)...")
            item_data = DANFE_DATA["item"]
            ctx_result = await adicionar_item(ctx, item_data)
            if ctx_result:
                ctx = ctx_result
                print("✅ Produto filled!")
            else:
                print("❌ Produto filling failed!")
                return
            await page.wait_for_timeout(2000)

            # Step 9: Fill Informações Adicionais
            print("\n[STEP 9] Filling Informações Adicionais...")
            info_texto = DANFE_DATA["informacoes_adicionais"]
            from app.modules.nfa.informacoes_adicionais_filler import (
                preencher_informacoes_adicionais,
            )

            ctx_result = await preencher_informacoes_adicionais(ctx, info_texto)
            if ctx_result:
                ctx = ctx_result
                print("✅ Informações Adicionais filled!")
            else:
                print("⚠️  Informações Adicionais had issues, continuing...")
            await page.wait_for_timeout(2000)

            # Save final screenshot
            print("\n[FINAL] Saving screenshot...")
            await save_screenshot(page, None, filename="live_demo_final.png")
            print("✅ Screenshot saved: output/nfa/screenshots/live_demo_final.png")

            print("\n" + "=" * 80)
            print("✅ FORM FILLING COMPLETE!")
            print("=" * 80)
            print("\nForm filled with data matching your DANFE:")
            print(f"  Emitente: IKLI TECNOLOGIA LTDA (CNPJ: {emitente_cnpj})")
            print(f"  Destinatário: ALEXANDRA PEREIRA SANTOS (CPF: {destinatario_doc})")
            print(
                f"  Endereço: {endereco_data['logradouro']}, {endereco_data['numero']}"
            )
            print(
                f"  Produto: {item_data['descricao']} - R$ {item_data['valor_unitario']},00"
            )
            print(f"  Natureza: {valores_fixos['natureza_operacao']}")
            print(f"  Motivo: {valores_fixos['motivo']}")
            print("\nBrowser will stay open for 30 seconds for inspection...")
            await asyncio.sleep(30)

        except Exception as e:
            logger.error(f"Error in live demo: {e}", exc_info=True)
            await save_screenshot(page, None, filename="live_demo_error.png")
            print(f"\n❌ Error occurred: {e}")
            print("Screenshot saved: output/nfa/screenshots/live_demo_error.png")
            await asyncio.sleep(10)
        finally:
            await browser.close()


if __name__ == "__main__":
    asyncio.run(live_fill_demo())
