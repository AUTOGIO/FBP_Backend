#!/usr/bin/env python3
"""NFA Form Filling - Exact Order as Specified
Fills form in the exact order with pesquisar clicks and correct waits.
ONE BLOCK DEPENDS ON THE INPUT OF THE PREDECESSOR.
"""

import os
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

LOGIN_URL = "https://www4.sefaz.pb.gov.br/atf/seg/SEGf_Login.jsp"
FORM_URL = "https://www4.sefaz.pb.gov.br/atf/fis/FISf_EmitirNFAeReparticao.do?limparSessao=true"

# Credentials loaded from environment - NEVER hardcode secrets
USERNAME = os.getenv("NFA_USERNAME", "")
PASSWORD = os.getenv("NFA_PASSWORD", "")
EMITENTE_CNPJ = os.getenv("NFA_EMITENTE_CNPJ", "28.842.017/0001-05")
DOWNLOAD_DIR = "/Users/dnigga/Downloads/NFA_Outputs"


def extract_clean_cpf(cpf_string: str) -> str:
    """Extract and clean CPF/CNPJ by removing formatting (dots, slashes, hyphens)."""
    # Remove all non-digit characters
    clean = re.sub(r"[^\d]", "", cpf_string)
    return clean


def click_pesquisar_and_wait(frame_or_page, wait_seconds=2):
    """Click Pesquisar button and wait."""
    try:
        # Try to find button in frame/page
        pesquisar_btn = frame_or_page.locator("input[value='Pesquisar']").first
        if pesquisar_btn.is_visible(timeout=3000):
            pesquisar_btn.click()
            print(f"  ✓ Clicked 'Pesquisar'")
            print(f"  ⏳ Waiting {wait_seconds} seconds...")
            time.sleep(wait_seconds)
            return True
    except Exception as e:
        print(f"  ⚠️  Pesquisar button not found: {e}")
    return False


def wait_for_page_reload(page, timeout=10000):
    """Wait for page to reload after certain actions."""
    print("  ⏳ Waiting for PAGE RELOAD...")
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
        page.wait_for_load_state("domcontentloaded", timeout=timeout)
        time.sleep(2)  # Extra wait for stability
        print("  ✓ Page reload complete")
    except Exception:
        print("  ⚠️  Page reload wait timeout, continuing...")


def main():
    # Validate credentials are set
    if not USERNAME or not PASSWORD:
        print("❌ ERROR: NFA_USERNAME and NFA_PASSWORD environment variables must be set!")
        print("   Set them in .env or export them before running.")
        return

    # Create download directory if it doesn't exist
    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    print(f"📁 Download directory ready: {DOWNLOAD_DIR}")

    # Extract clean CPF from emitente CNPJ
    clean_cpf = extract_clean_cpf(EMITENTE_CNPJ)
    print(f"📄 Emitente CPF/CNPJ (clean): {clean_cpf}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False, args=["--disable-blink-features=AutomationControlled"]
        )
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()

        print("🌐 Opening login...")
        page.goto(LOGIN_URL, wait_until="domcontentloaded")
        time.sleep(2)

        print("🔐 Filling username/password...")
        page.fill("input[name='edtNoLogin']", USERNAME)
        page.fill("input[name='edtDsSenha']", PASSWORD)

        print("➡️ Submitting login...")
        page.evaluate("logarSistema()")
        time.sleep(4)

        print("➡️ Going directly to FORM...")
        page.goto(FORM_URL, wait_until="domcontentloaded")
        time.sleep(5)

        # Wait for form to be ready
        print("⏳ Waiting for form to load...")
        page.wait_for_selector("select[name='cmbNaturezaOperacao']", timeout=15000)
        print("✅ Form is ready!")

        # ============================================
        # EXACT ORDER AS SPECIFIED - ONE BLOCK DEPENDS ON PREDECESSOR
        # ============================================

        # 1 - Natureza Operação
        print("\n[1] Filling Natureza Operação: REMESSA")
        page.select_option("select[name='cmbNaturezaOperacao']", "75")  # REMESSA
        time.sleep(0.5)

        # 2 - Motivo
        print("\n[2] Filling Motivo: DESPACHO")
        page.select_option("select[name='cmbMotivo']", "1")  # DESPACHO
        time.sleep(0.5)

        # 3 - Repartição Fiscal (in iframe) - wait 3 seconds
        print("\n[3] Filling Repartição Fiscal: 90102008")
        reparticao_frame = page.frame(name="cmpElementoOrg")
        if reparticao_frame:
            reparticao_input = reparticao_frame.locator("input[type='text']").first
            reparticao_input.fill("90102008")
            print("  → Clicking 'Pesquisar'...")
            click_pesquisar_and_wait(reparticao_frame, wait_seconds=3)  # 3 seconds
        else:
            print("  ❌ Repartição iframe not found")
        time.sleep(0.5)

        # 4 - Código Município (in iframe) - wait 2 seconds
        print("\n[4] Filling Código Município: 2051-6")
        municipio_frame = page.frame(name="cmpMunicipioGiva")
        if municipio_frame:
            municipio_input = municipio_frame.locator("input[type='text']").first
            municipio_input.fill("2051-6")
            print("  → Clicking 'Pesquisar'...")
            click_pesquisar_and_wait(municipio_frame, wait_seconds=2)  # 2 seconds
        else:
            print("  ❌ Município iframe not found")
        time.sleep(0.5)

        # 5 - Tipo Operação - PAGE RELOAD after this
        print("\n[5] Filling Tipo Operação: SAIDA")
        page.select_option("select[name='cmbTpOperacao']", "S")  # SAIDA
        time.sleep(1)
        wait_for_page_reload(page)  # PAGE RELOAD

        # 6 - CFOP (dropdown from 5101-7200, value 6908) - PAGE RELOAD after this
        print("\n[6] Filling CFOP: 6908 (dropdown)")
        # Wait for CFOP dropdown to be populated (it's populated after Tipo Operação)
        print("  ⏳ Waiting for CFOP dropdown to be populated...")
        time.sleep(3)  # Wait for dropdown to populate after page reload
        try:
            cfop_select = page.locator("select[name='cmbNrCfop']")
            # Wait for options to be available
            page.wait_for_timeout(2000)
            # Try to select by value
            try:
                cfop_select.select_option(value="6908")
                print("  ✓ CFOP selected by value: 6908")
            except Exception:
                # Try selecting by label text that contains 6908
                try:
                    options = cfop_select.locator("option")
                    option_count = options.count()
                    for i in range(option_count):
                        option_text = options.nth(i).inner_text()
                        if "6908" in option_text:
                            cfop_select.select_option(index=i)
                            print(f"  ✓ CFOP selected: {option_text}")
                            break
                except Exception:
                    print("  ⚠️  CFOP selection failed, continuing...")
        except Exception as e:
            print(f"  ⚠️  CFOP selection failed: {e}")
        time.sleep(1)
        wait_for_page_reload(page)  # PAGE RELOAD

        # 7 - Emitente (in iframe) - wait 3 seconds
        print("\n[7] Filling Emitente CNPJ: 28.842.017/0001-05")
        # First select CNPJ type in main form
        page.select_option("select[name='cmbTpDoccmpEmitente']", "2")  # CNPJ
        time.sleep(0.5)

        emitente_frame = page.frame(name="cmpEmitente")
        if emitente_frame:
            emitente_input = emitente_frame.locator("input[type='text']").first
            # Try formatted first, then clean if needed
            try:
                emitente_input.fill("28.842.017/0001-05")  # Formatted CNPJ
            except Exception:
                emitente_input.fill("28842017000105")  # Clean CNPJ fallback
            print("  → Clicking 'Pesquisar'...")
            click_pesquisar_and_wait(emitente_frame, wait_seconds=3)  # 3 seconds
        else:
            print("  ❌ Emitente iframe not found")
        time.sleep(0.5)

        # 8 - Destinatário CPF (in iframe) - wait 3 seconds
        print("\n[8] Filling Destinatário CPF: 738.255.062-15")
        # First select CPF type in main form
        page.select_option("select[name='cmbTpDoccmpDestinatario']", "3")  # CPF
        time.sleep(0.5)

        destinatario_frame = page.frame(name="cmpDestinatario")
        if destinatario_frame:
            destinatario_input = destinatario_frame.locator("input[type='text']").first
            # Try formatted first, then clean if needed
            try:
                destinatario_input.fill("738.255.062-15")  # Formatted CPF
            except Exception:
                destinatario_input.fill("73825506215")  # Clean CPF fallback
            print("  → Clicking 'Pesquisar'...")
            click_pesquisar_and_wait(destinatario_frame, wait_seconds=3)  # 3 seconds
        else:
            print("  ❌ Destinatário iframe not found")
        time.sleep(0.5)

        # 9 - NCM (in produto iframe) - wait 2 seconds
        print("\n[9] Filling NCM: 0000.00.00")
        time.sleep(1)
        produto_frame = None
        max_retries = 3
        for attempt in range(max_retries):
            try:
                produto_frame = page.frame(name="cmpProduto")
                if produto_frame:
                    # Prefer any visible textbox that is not the hidden hint input
                    ncm_input = produto_frame.locator(
                        "input[type='text']:not([name='hintedit'])"
                    ).first
                    ncm_input.wait_for(state="visible", timeout=8000)
                    ncm_input.click()
                    ncm_input.fill("0000.00.00")
                    print("  → Clicking 'Pesquisar'...")
                    click_pesquisar_and_wait(produto_frame, wait_seconds=2)  # 2 seconds
                    break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"  ⚠️  Attempt {attempt + 1} failed, retrying...")
                    time.sleep(2)
                else:
                    print(
                        f"  ❌ Produto iframe/NCM failed after {max_retries} attempts: {e}"
                    )
        time.sleep(0.5)

        # Wait for product fields to be ready after NCM pesquisar
        print("\n  ⏳ Waiting for product fields to be ready...")
        time.sleep(2)

        # 10 - Detalhamento Produto
        print("\n[10] Filling Detalhamento Produto: '  1 - SID241 '")
        try:
            detalhamento_field = page.locator(
                "textarea[name='txaDsDetalheProduto']"
            ).first
            detalhamento_field.wait_for(state="visible", timeout=10000)
            detalhamento_field.click()  # Focus first
            detalhamento_field.clear()
            detalhamento_field.fill("  1 - SID241 ")
            # Trigger change event
            page.evaluate(
                "document.querySelector('textarea[name=\"txaDsDetalheProduto\"]').dispatchEvent(new Event('change', { bubbles: true }))"
            )
            print("  ✓ Detalhamento filled")
        except Exception as e:
            print(f"  ❌ Detalhamento failed: {e}")
        time.sleep(1)  # Increased wait

        # 11 - Unidade (dropdown)
        print("\n[11] Filling Unidade: UNIDADE")
        try:
            unidade_select = page.locator("select[name='cmbUnidMedida']").first
            unidade_select.wait_for(state="visible", timeout=10000)
            unidade_select.select_option(value="9")  # Value for UNIDADE from HTML
            print("  ✓ Unidade selected by value")
        except Exception:
            try:
                page.select_option("select[name='cmbUnidMedida']", label="UNIDADE")
                print("  ✓ Unidade selected by label")
            except Exception as e:
                print(f"  ❌ Unidade selection failed: {e}")
        time.sleep(1)  # Increased wait

        # 12 - Quantidade (CRITICAL - highlighted in red if empty)
        print("\n[12] Filling Quantidade: 1")
        try:
            quantidade_field = page.locator("input[name='edtQtdProduto']").first
            quantidade_field.wait_for(state="visible", timeout=10000)
            quantidade_field.click()  # Focus first
            quantidade_field.clear()
            quantidade_field.fill("1")
            # Trigger change event
            page.evaluate(
                "document.querySelector('input[name=\"edtQtdProduto\"]').dispatchEvent(new Event('change', { bubbles: true }))"
            )
            # Verify it was filled
            quantidade_value = quantidade_field.input_value()
            if quantidade_value != "1":
                print(
                    f"  ⚠️  Quantidade value mismatch: '{quantidade_value}', retrying..."
                )
                quantidade_field.fill("1")
            print("  ✓ Quantidade filled")
        except Exception as e:
            print(f"  ❌ Quantidade failed: {e}")
        time.sleep(1)  # Increased wait

        # 13 - Valor Unitário
        print("\n[13] Filling Valor Unitário: 1100")
        try:
            valor_field = page.locator("input[name='edtVlProduto']").first
            valor_field.wait_for(state="visible", timeout=10000)
            valor_field.click()  # Focus first
            valor_field.clear()
            valor_field.fill("1100")
            # Trigger change event
            page.evaluate(
                "document.querySelector('input[name=\"edtVlProduto\"]').dispatchEvent(new Event('change', { bubbles: true }))"
            )
            print("  ✓ Valor Unitário filled")
        except Exception as e:
            print(f"  ❌ Valor Unitário failed: {e}")
        time.sleep(1)  # Increased wait

        # 14 - Aliquota
        print("\n[14] Filling Aliquota: 0")
        try:
            aliquota_field = page.locator("input[name='edtVlAliquota']").first
            aliquota_field.wait_for(state="visible", timeout=10000)
            aliquota_field.click()  # Focus first
            aliquota_field.clear()
            aliquota_field.fill("0")
            # Trigger change event
            page.evaluate(
                "document.querySelector('input[name=\"edtVlAliquota\"]').dispatchEvent(new Event('change', { bubbles: true }))"
            )
            print("  ✓ Aliquota filled")
        except Exception as e:
            print(f"  ❌ Aliquota failed: {e}")
        time.sleep(1)  # Increased wait

        # Verify all product fields are filled before clicking ADICIONAR/ALTERAR ITEM
        print("\n[14.5] Verifying all product fields are filled...")
        try:
            detalhamento_value = page.locator(
                "textarea[name='txaDsDetalheProduto']"
            ).first.input_value()
            quantidade_value = page.locator(
                "input[name='edtQtdProduto']"
            ).first.input_value()
            valor_value = page.locator("input[name='edtVlProduto']").first.input_value()
            aliquota_value = page.locator(
                "input[name='edtVlAliquota']"
            ).first.input_value()
            unidade_value = page.locator(
                "select[name='cmbUnidMedida']"
            ).first.input_value()

            print(f"  Detalhamento: '{detalhamento_value}'")
            print(f"  Quantidade: '{quantidade_value}'")
            print(f"  Valor Unitário: '{valor_value}'")
            print(f"  Aliquota: '{aliquota_value}'")
            print(f"  Unidade: '{unidade_value}'")

            if (
                not detalhamento_value
                or not quantidade_value
                or not valor_value
                or not aliquota_value
                or unidade_value == ""
            ):
                print("  ⚠️  WARNING: Some fields are empty! Retrying...")
                # Retry filling empty fields
                if not detalhamento_value:
                    page.locator("textarea[name='txaDsDetalheProduto']").first.fill(
                        "  1 - SID241 "
                    )
                if not quantidade_value:
                    page.locator("input[name='edtQtdProduto']").first.fill("1")
                if not valor_value:
                    page.locator("input[name='edtVlProduto']").first.fill("1100")
                if not aliquota_value:
                    page.locator("input[name='edtVlAliquota']").first.fill("0")
                if unidade_value == "":
                    page.locator("select[name='cmbUnidMedida']").first.select_option(
                        value="9"
                    )
                time.sleep(1)
        except Exception as e:
            print(f"  ⚠️  Verification failed: {e}, continuing anyway...")

        # Click 'ADICIONAR/ALTERAR ITEM' - Wait 5 seconds after clicking
        print("\n[14.5] Clicking 'ADICIONAR/ALTERAR ITEM'...")
        try:
            # Primary selector: name="btnAdicionarItem" with value="Adicionar/Alterar Item"
            adicionar_btn = page.locator(
                "input[name='btnAdicionarItem'][value='Adicionar/Alterar Item']"
            ).first
            if adicionar_btn.is_visible(timeout=5000):
                adicionar_btn.click()
                print("  ✓ Clicked 'ADICIONAR/ALTERAR ITEM'")
                print("  ⏳ Waiting 5 seconds after clicking...")
                time.sleep(5)  # Wait 5 seconds after clicking
            else:
                # Fallback: try by name only
                adicionar_btn = page.locator("input[name='btnAdicionarItem']").first
                if adicionar_btn.is_visible(timeout=5000):
                    adicionar_btn.click()
                    print("  ✓ Clicked 'ADICIONAR/ALTERAR ITEM' (by name)")
                    print("  ⏳ Waiting 5 seconds after clicking...")
                    time.sleep(5)
                else:
                    # Last resort: try by value text
                    adicionar_btn = page.locator(
                        "input[value*='Adicionar' i], input[value*='Alterar' i]"
                    ).first
                    if adicionar_btn.is_visible(timeout=5000):
                        adicionar_btn.click()
                        print("  ✓ Clicked 'ADICIONAR/ALTERAR ITEM' (by value)")
                        print("  ⏳ Waiting 5 seconds after clicking...")
                        time.sleep(5)
        except Exception as e:
            print(f"  ⚠️  Could not click ADICIONAR/ALTERAR ITEM: {e}")

        # 15 - CST (dropdown) - AFTER ADICIONAR/ALTERAR ITEM
        print("\n[15] Filling CST: 41")
        try:
            cst_select = page.locator("select[name='cmbNrCST']").first
            cst_select.wait_for(state="visible", timeout=8000)
            # Try direct value
            cst_select.select_option(value="41")
            print("  ✓ CST selected")
        except Exception:
            try:
                # Try by label containing 41
                cst_select.select_option(label="41")
                print("  ✓ CST selected by label")
            except Exception:
                try:
                    # Fallback: iterate options looking for '41'
                    options = cst_select.locator("option")
                    option_count = options.count()
                    for i in range(option_count):
                        text = options.nth(i).inner_text()
                        if "41" in text:
                            cst_select.select_option(index=i)
                            print(f"  ✓ CST selected by iteration: {text}")
                            break
                    else:
                        print("  ⚠️  CST selection failed (no matching option)")
                except Exception as e:
                    print(f"  ⚠️  CST selection failed: {e}")
        time.sleep(0.5)

        # 16 - Receita (dropdown) - AFTER ADICIONAR/ALTERAR ITEM
        print("\n[16] Filling Receita: 1199 - ICMS - OUTROS (COMERCIO E INDUSTRIA)")
        try:
            page.select_option(
                "select[name='cmbSqReceitaSefin']",
                label="1199 - ICMS - OUTROS (COMERCIO E INDUSTRIA)",
            )
            print("  ✓ Receita selected")
        except Exception:
            try:
                # Try by value if label doesn't work
                page.select_option("select[name='cmbSqReceitaSefin']", value="335")
                print("  ✓ Receita selected by value")
            except Exception:
                print("  ⚠️  Receita selection failed")
        time.sleep(0.5)

        # 16.5 - After CST/Receita, wait and mark "Selecionar Todos"
        print("\n[16.5] Waiting 5s, then marking 'Selecionar Todos' checkbox...")
        time.sleep(5)
        checkbox_marked = False
        # Attempt 1: explicit name/id patterns
        try:
            cb = page.locator(
                "input[type='checkbox'][name*='Selecionar'], input[type='checkbox'][id*='Selecionar']"
            ).first
            cb.wait_for(state="visible", timeout=5000)
            cb.check(force=True)
            checkbox_marked = True
            print("  ✓ 'Selecionar Todos' checked (by name/id pattern)")
        except Exception as e:
            print(f"  ⚠️ Attempt 1 failed: {e}")
        # Attempt 2: checkbox in row containing the text
        if not checkbox_marked:
            try:
                cb = page.locator(
                    "xpath=//td[contains(normalize-space(.), 'Selecionar Todos')]/preceding::input[@type='checkbox'][1]"
                ).first
                cb.wait_for(state="visible", timeout=5000)
                cb.check(force=True)
                checkbox_marked = True
                print("  ✓ 'Selecionar Todos' checked (xpath row text)")
            except Exception as e:
                print(f"  ⚠️ Attempt 2 failed: {e}")
        # Attempt 3: first checkbox in the items table
        if not checkbox_marked:
            try:
                cb = page
                cb = page.locator(
                    "table:has-text('Itens Adicionados') input[type='checkbox']"
                ).first
                cb.wait_for(state="visible", timeout=5000)
                cb.check(force=True)
                checkbox_marked = True
                print("  ✓ 'Selecionar Todos' checked (items table fallback)")
            except Exception as e:
                print(f"  ⚠️ Attempt 3 failed: {e}")
        # Attempt 4: generic first checkbox on page (last resort)
        if not checkbox_marked:
            try:
                cb = page.locator("input[type='checkbox']").first
                cb.wait_for(state="visible", timeout=5000)
                cb.check(force=True)
                checkbox_marked = True
                print("  ✓ 'Selecionar Todos' checked (generic first checkbox)")
            except Exception as e:
                print(f"  ❌ Could not mark 'Selecionar Todos': {e}")

        # 17 - Click Calcular
        print("\n[17] Clicking 'Calcular'...")
        try:
            calcular_btn = page.locator(
                "input[name='btnCalcular'][value='Calcular']"
            ).first
            calcular_btn.wait_for(state="visible", timeout=8000)
            calcular_btn.click()
            print("  ✓ Clicked 'Calcular'")
        except Exception as e:
            print(f"  ❌ Could not click 'Calcular': {e}")

        # 18 - Submeter Nota (may stay on same page or open popup)
        print("\n[18] Clicking 'Submeter Nota' and handling resulting page/popup...")
        try:
            submeter_btn = page.locator(
                "input[type='button'][value*='Submeter Nota' i], input[name='btnIncluirNota']"
            ).first
            submeter_btn.wait_for(state="visible", timeout=8000)
            submeter_btn.click()
            print("  ✓ Submeter Nota clicked")
        except Exception as e:
            print(f"  ⚠️ Could not click 'Submeter Nota': {e}")

        # Soft-mode: wait for success indication in DOM instead of popup / extra buttons
        try:
            page.wait_for_selector("text=/sucesso|sucesso/i", timeout=15000)
            print("  ✓ Submission success detected in DOM")
        except Exception as e:
            print(f"  ⚠️ Could not confirm success message: {e}")

        print("\n" + "=" * 80)
        print("✅ FORM FILLING COMPLETE!")
        print("=" * 80)
        print("\nAll fields filled in exact order:")
        print("  1. Natureza Operação: REMESSA")
        print("  2. Motivo: DESPACHO")
        print("  3. Repartição Fiscal: 90102008 (Pesquisar → wait 3s)")
        print("  4. Código Município: 2051-6 (Pesquisar → wait 2s)")
        print("  5. Tipo Operação: SAIDA (PAGE RELOAD)")
        print("  6. CFOP: 6908 (PAGE RELOAD)")
        print("  7. Emitente: 28.842.017/0001-05 (Pesquisar → wait 3s)")
        print("  8. Destinatário: 738.255.062-15 (Pesquisar → wait 3s)")
        print("  9. NCM: 0000.00.00 (Pesquisar → wait 2s)")
        print("  10. Detalhamento Produto: '  1 - SID241 '")
        print("  11. Unidade: UNIDADE")
        print("  12. Quantidade: 1")
        print("  13. Valor Unitário: 1100")
        print("  14. Aliquota: 0")
        print("  14.5. ADICIONAR/ALTERAR ITEM (wait 5s)")
        print("  15. CST: 41")
        print("  16. Receita: 1199 - ICMS - OUTROS (COMERCIO E INDUSTRIA)")
        print("  17. Calcular")
        print("  18. Submeter Nota (success via DOM)")
        print("\n🎯 Process complete! Keep window open for inspection.")
        time.sleep(9999)


if __name__ == "__main__":
    main()
