#!/usr/bin/env python3
"""NFA Batch Processor - Modernized & Hardened (2024-2025)
Process multiple NFA forms with LOJA and CPF.
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

# --- Configuration ---
LOGIN_URL = "https://www4.sefaz.pb.gov.br/atf/seg/SEGf_Login.jsp"
FORM_URL = "https://www4.sefaz.pb.gov.br/atf/fis/FISf_EmitirNFAeReparticao.do?limparSessao=true"

# Credentials loaded from environment - NEVER hardcode secrets
USERNAME = os.getenv("NFA_USERNAME", "")
PASSWORD = os.getenv("NFA_PASSWORD", "")
EMITENTE_CNPJ = os.getenv("NFA_EMITENTE_CNPJ", "28.842.017/0001-05")
DOWNLOAD_DIR = "/Users/dnigga/Downloads/NFA_Outputs"
LOGS_DIR = "logs"

# Global speed factor (1.0 = normal, >1.0 = mais rápido, <1.0 = mais lento)
SPEED_MULTIPLIER: float = 1.0


# --- Logging Setup ---
class ContextLogger:
    """Logger adapter that supports context binding."""

    def __init__(self, logger, context=None):
        self.logger = logger
        self.context = context or {}

    def bind(self, **kwargs):
        new_context = self.context.copy()
        new_context.update(kwargs)
        return ContextLogger(self.logger, new_context)

    def _log(self, level, msg, *args, **kwargs):
        if self.context:
            context_str = " ".join(f"{k}={v}" for k, v in self.context.items())
            msg = f"[{context_str}] {msg}"
        getattr(self.logger, level)(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        self._log("info", msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        self._log("warning", msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        self._log("error", msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        self._log("debug", msg, *args, **kwargs)


def setup_logging():
    os.makedirs(LOGS_DIR, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(
                os.path.join(LOGS_DIR, "nfa_history.log"), encoding="utf-8"
            ),
        ],
    )
    return ContextLogger(logging.getLogger("nfa_batch"))


logger = setup_logging()
# Global notice about deprecated UI steps
logger.info("Serviço and Imprimir permanently removed from workflow.")

# Validate credentials at import time
if not USERNAME or not PASSWORD:
    logger.warning(
        "NFA_USERNAME and/or NFA_PASSWORD not set. "
        "Set them in .env or export before running batch processing."
    )

# --- Helper Functions ---


def sleep(seconds: float):
    """Soft wait escalonada pelo SPEED_MULTIPLIER.

    SPEED_MULTIPLIER > 1.0  → reduz o tempo de espera (mais rápido)
    SPEED_MULTIPLIER < 1.0  → aumenta o tempo de espera (mais lento)
    """
    # Protege contra valores extremos/zero
    factor = max(0.1, SPEED_MULTIPLIER)
    effective = max(0.05, seconds / factor)
    time.sleep(effective)


def extract_clean_cpf(cpf_string: str) -> str:
    """Extract and clean CPF/CNPJ."""
    return re.sub(r"[^\d]", "", cpf_string)


def wait_for_page_load_soft(page: Page, timeout: int = 5000):
    """Soft-mode navigation wait."""
    try:
        page.wait_for_load_state("domcontentloaded", timeout=timeout)
        page.wait_for_load_state("networkidle", timeout=timeout)
    except PlaywrightTimeoutError:
        logger.info("Soft-mode: Page load timeout (continuing).")


def safe_click(page: Page, selector: str, description: str, timeout: int = 4000):
    """Hardened click with retry."""
    try:
        element = page.locator(selector).first
        element.wait_for(state="visible", timeout=timeout)
        element.click()
        logger.info(f"Clicked {description}")
        return True
    except Exception as e:
        logger.warning(
            f"Standard click failed for {description}: {e}. Retrying with force..."
        )
        try:
            # Retry with force
            page.locator(selector).first.click(force=True)
            logger.info(f"Force clicked {description}")
            return True
        except Exception as e2:
            logger.error(f"Force click failed for {description}: {e2}")
            return False


def hardened_interaction(
    page: Page,
    selector: str,
    description: str,
    action: str = "click",
    value: str = None,
):
    """Apply hardened reliability pattern."""
    try:
        loc = page.locator(selector).first
        loc.wait_for(state="visible", timeout=4000)
        if action == "click":
            loc.click()
        elif action == "fill":
            loc.fill(value)
        elif action == "select":
            loc.select_option(value=value)
    except Exception as e:
        logger.warning(
            f"Element {description} not visible/interactable, retrying interaction... Error: {e}"
        )
        # NOTE: Skipping page.reload() here to prevent data loss during form filling.
        # Using force click/fill as fallback.
        try:
            loc = page.locator(selector).first
            if action == "click":
                loc.click(force=True)
            elif action == "fill":
                loc.fill(value, force=True)
        except Exception as e2:
            logger.error(f"Hardened interaction failed for {description}: {e2}")
            raise e2


def click_pesquisar_and_wait(frame_or_page, wait_seconds=1.5):
    """Click Pesquisar button and wait."""
    try:
        # Try multiple selectors for Pesquisar button
        pesquisar_selectors = [
            "input[value='Pesquisar']",
            "button:has-text('Pesquisar')",
            "input[type='button'][value*='Pesquisar' i]",
            "button[type='button']:has-text('Pesquisar')",
        ]

        for selector in pesquisar_selectors:
            try:
                pesquisar_btn = frame_or_page.locator(selector).first
                if pesquisar_btn.is_visible(timeout=2000):
                    pesquisar_btn.click()
                    sleep(wait_seconds)
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def _fill_emitente_via_frame(page: Page, cnpj_clean: str, log) -> bool:
    """Strategy 1: Fill Emitente via frame (legacy approach)."""
    try:
        emitente_frame = page.frame(name="cmpEmitente")
        if not emitente_frame:
            return False

        inp = emitente_frame.locator("input[type='text']").first
        inp.wait_for(state="visible", timeout=4000)
        inp.fill(cnpj_clean)

        if click_pesquisar_and_wait(emitente_frame, 2):
            return True
    except Exception:
        pass
    return False


def _fill_emitente_direct_page_name(page: Page, cnpj_clean: str, log) -> bool:
    """Strategy 2: Fill Emitente directly on page using name selector."""
    try:
        # Multiple selectors for Emitente CNPJ input
        emitente_selectors = [
            "input[name*='Emitente' i][type='text']",
            "input[name*='CNPJ' i][type='text']",
            "input[id*='Emitente' i][type='text']",
            "input[id*='CNPJ' i][type='text']",
            "table:has-text('Emitente') input[type='text']",
        ]

        for selector in emitente_selectors:
            try:
                cnpj_input = page.locator(selector).first
                if cnpj_input.is_visible(timeout=3000):
                    cnpj_input.click()
                    cnpj_input.clear()
                    cnpj_input.fill(cnpj_clean)
                    sleep(0.5)

                    # Try to click Pesquisar on main page
                    if click_pesquisar_and_wait(page, 2):
                        return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def _fill_emitente_direct_page_generic(page: Page, cnpj_clean: str, log) -> bool:
    """Strategy 3: Fill Emitente using generic selectors."""
    try:
        # After selecting CNPJ type, find the input near the select
        tipo_select = page.locator("select[name='cmbTpDoccmpEmitente']").first
        if tipo_select.is_visible(timeout=3000):
            # Try to find input field after the select
            all_inputs = page.locator("input[type='text']").all()
            for inp in all_inputs[:10]:  # Check first 10 inputs
                try:
                    if inp.is_visible(timeout=1000):
                        # Fill and try Pesquisar
                        inp.click()
                        inp.clear()
                        inp.fill(cnpj_clean)
                        sleep(0.5)
                        if click_pesquisar_and_wait(page, 2):
                            return True
                        break
                except Exception:
                    continue
    except Exception:
        pass
    return False


def fill_informacoes_adicionais(page: Page, loja: str) -> bool:
    """Fill Informações Adicionais."""
    try:
        info_text = loja
        logger.info(f"Filling Informações Adicionais: '{info_text}'")

        info_field = page.locator("textarea[name='txaInformacoesAdicionais']").first
        info_field.wait_for(state="visible", timeout=5000)
        info_field.click()
        info_field.clear()
        info_field.fill(info_text)
        sleep(0.5)
        return True
    except Exception as e:
        logger.error(f"Failed to fill Informações Adicionais: {e}")
        return False


# --- Main Processing Logic ---


def process_single_nfa(
    page: Page,
    context: Any,  # Playwright context
    item_ctx: Dict[str, Any],  # Data context
    speed_multiplier: float = 1.0,
) -> Dict[str, Any]:
    """Process a single NFA form."""

    # Bind context to logger
    log = logger.bind(**item_ctx)

    loja = item_ctx["loja"]
    cpf = item_ctx["cpf"]

    result = {
        "loja": loja,
        "cpf": cpf,
        "success": False,
        "error": None,
        "timestamp": datetime.now().isoformat(),
    }

    clean_cpf = extract_clean_cpf(cpf)

    try:
        log.info(f"Processing NFA {item_ctx['item']}/{item_ctx['total']}")

        # Navigate
        log.info("Navigating to form...")
        page.goto(FORM_URL, wait_until="domcontentloaded")
        sleep(3)

        # CRITICAL: Protect DATE field from any modification IMMEDIATELY after page load
        log.info("🔒 PROTECTING DATE FIELD (edtDtEmissao) - DO NOT MODIFY")
        date_protected = False
        original_date = None
        try:
            date_field = page.locator("input[name='edtDtEmissao']").first
            if date_field.is_visible(timeout=5000):
                # Store original date value IMMEDIATELY
                original_date = date_field.input_value()
                log.info(
                    f"🔒 DATE field protected - original value: '{original_date}' (will NOT be changed)"
                )
                date_protected = True

                # Add JavaScript protection to prevent accidental changes
                page.evaluate(
                    f"""
                    (function() {{
                        const dateField = document.querySelector('input[name=\"edtDtEmissao\"]');
                        if (dateField) {{
                            const originalValue = '{original_date}';
                            
                            // Prevent any modifications
                            const protectDate = function() {{
                                if (dateField.value !== originalValue && originalValue !== '') {{
                                    console.warn('DATE field change detected - restoring original:', originalValue);
                                    dateField.value = originalValue;
                                    dateField.dispatchEvent(new Event('change', {{ bubbles: false }}));
                                }}
                            }};
                            
                            // Protect on focus (prevent user/system changes)
                            dateField.addEventListener('focus', function(e) {{
                                console.log('DATE field focused - protecting value:', originalValue);
                            }}, true);
                            
                            // Protect on change
                            dateField.addEventListener('change', protectDate, true);
                            
                            // Protect on input
                            dateField.addEventListener('input', protectDate, true);
                            
                            // Protect on blur
                            dateField.addEventListener('blur', protectDate, true);
                            
                            // Make field read-only via attribute
                            dateField.setAttribute('readonly', 'readonly');
                            dateField.style.backgroundColor = '#f0f0f0';
                            
                            console.log('DATE field protection activated:', originalValue);
                        }}
                    }})();
                """
                )
                log.info("✓ JavaScript protection added to DATE field")
        except Exception as e:
            log.warning(f"Could not protect DATE field (may not exist): {e}")

        page.wait_for_selector("select[name='cmbNaturezaOperacao']", timeout=8000)

        # Fill Info Adicionais - LOJA + test field (e.g., "RN13 - Remessa por conta de contrato de locação")
        test_text = item_ctx.get("test", "Remessa por conta de contrato de locação")
        info_adicionais_text = f"{loja} - {test_text}"
        if not fill_informacoes_adicionais(page, info_adicionais_text):
            raise Exception("Failed to fill Informações Adicionais")

        # 1 - Natureza Operação
        page.select_option("select[name='cmbNaturezaOperacao']", "75")
        sleep(0.5)

        # 2 - Motivo
        page.select_option("select[name='cmbMotivo']", "1")
        sleep(0.5)

        # 3 - Repartição Fiscal
        reparticao_frame = page.frame(name="cmpElementoOrg")
        if reparticao_frame:
            reparticao_frame.locator("input[type='text']").first.fill("90102008")
            click_pesquisar_and_wait(reparticao_frame, 2)
        sleep(0.5)

        # 4 - Código Município
        municipio_frame = page.frame(name="cmpMunicipioGiva")
        if municipio_frame:
            municipio_frame.locator("input[type='text']").first.fill("2051-6")
            click_pesquisar_and_wait(municipio_frame, 1.5)
        sleep(0.5)

        # 5 - Tipo Operação
        page.select_option("select[name='cmbTpOperacao']", "S")
        sleep(1)
        wait_for_page_load_soft(page)

        # 6 - CFOP
        sleep(1.5)
        try:
            cfop_select = page.locator("select[name='cmbNrCfop']")
            try:
                cfop_select.select_option(value="6908")
            except Exception:
                # Fallback strategy
                options = cfop_select.locator("option")
                for i in range(options.count()):
                    if "6908" in options.nth(i).inner_text():
                        cfop_select.select_option(index=i)
                        break
        except Exception as e:
            log.warning(f"CFOP selection issue: {e}")
        sleep(1)
        wait_for_page_load_soft(page)

        # 7 - Emitente (CNPJ fixo, com retries e múltiplas estratégias)
        log.info("=== FILLING EMITENTE CNPJ ===")

        # Validate CNPJ is not placeholder
        emitente_cnpj_clean = extract_clean_cpf(EMITENTE_CNPJ)
        if (
            not EMITENTE_CNPJ
            or emitente_cnpj_clean == "00000000000000"
            or len(emitente_cnpj_clean) != 14
        ):
            error_msg = f"❌ INVALID EMITENTE CNPJ: '{EMITENTE_CNPJ}' (clean: '{emitente_cnpj_clean}'). Please set NFA_EMITENTE_CNPJ in .env file with a valid 14-digit CNPJ."
            log.error(error_msg)
            raise ValueError(error_msg)

        # Step 1: Select CNPJ document type
        try:
            page.select_option("select[name='cmbTpDoccmpEmitente']", "2")
            log.info("✓ Selected CNPJ document type")
            sleep(1)  # Wait for form to update
            wait_for_page_load_soft(page, timeout=5000)
        except Exception as e:
            log.warning(f"Failed to select document type: {e}")

        emitente_filled = False
        log.info(f"CNPJ to fill: {EMITENTE_CNPJ} (clean: {emitente_cnpj_clean})")

        # Multiple strategies for filling Emitente CNPJ
        strategies = [
            # Strategy 1: Try frame-based approach (legacy)
            {
                "name": "Frame-based (cmpEmitente)",
                "action": lambda: _fill_emitente_via_frame(
                    page, emitente_cnpj_clean, log
                ),
            },
            # Strategy 2: Direct page input with name selector
            {
                "name": "Direct page input (name selector)",
                "action": lambda: _fill_emitente_direct_page_name(
                    page, emitente_cnpj_clean, log
                ),
            },
            # Strategy 3: Direct page input with generic selector
            {
                "name": "Direct page input (generic selector)",
                "action": lambda: _fill_emitente_direct_page_generic(
                    page, emitente_cnpj_clean, log
                ),
            },
        ]

        for attempt in range(3):  # Reduced attempts for speed
            if emitente_filled:
                break

            for strategy_idx, strategy in enumerate(strategies):
                try:
                    log.info(f"Attempt {attempt + 1}, Strategy: {strategy['name']}")
                    strategy_result = strategy["action"]()  # Returns bool
                    if strategy_result:
                        emitente_filled = True
                        log.info(
                            f"✓ Emitente CNPJ filled successfully using: {strategy['name']}"
                        )
                        break
                except Exception as e:
                    log.warning(f"Strategy {strategy['name']} failed: {e}")
                    continue

            if not emitente_filled:
                sleep(1.5)
                wait_for_page_load_soft(page, timeout=3000)

        if not emitente_filled:
            log.error(
                "❌ CRITICAL: Emitente CNPJ could not be filled after all strategies and retries"
            )
            raise Exception("Emitente CNPJ filling failed - cannot continue")
        else:
            log.info("✓✓✓ EMITENTE CNPJ FILLED SUCCESSFULLY ✓✓✓")

        sleep(1)

        # 8 - Destinatário (CPF, com múltiplas estratégias)
        log.info(f"=== FILLING DESTINATARIO CPF: {cpf} ===")

        try:
            page.select_option("select[name='cmbTpDoccmpDestinatario']", "3")
            log.info("✓ Selected CPF document type")
            sleep(1)
            wait_for_page_load_soft(page, timeout=5000)
        except Exception as e:
            log.warning(f"Failed to select destinatario document type: {e}")

        cpf_clean = extract_clean_cpf(cpf)
        destinatario_filled = False

        # Try frame first, then direct page
        try:
            destinatario_frame = page.frame(name="cmpDestinatario")
            if destinatario_frame:
                inp = destinatario_frame.locator("input[type='text']").first
                if inp.is_visible(timeout=5000):
                    inp.fill(cpf_clean)
                    if click_pesquisar_and_wait(destinatario_frame, 2):
                        destinatario_filled = True
                        log.info(f"✓ Destinatario CPF filled via frame: {cpf_clean}")
        except Exception:
            pass

        # Fallback to direct page input
        if not destinatario_filled:
            try:
                destinatario_selectors = [
                    "input[name*='Destinatario' i][type='text']",
                    "input[name*='CPF' i][type='text']",
                    "table:has-text('Destinatário') input[type='text']",
                    "table:has-text('Destinatario') input[type='text']",
                ]
                for selector in destinatario_selectors:
                    try:
                        doc_input = page.locator(selector).first
                        if doc_input.is_visible(timeout=3000):
                            doc_input.click()
                            doc_input.clear()
                            doc_input.fill(cpf_clean)
                            sleep(0.5)
                            if click_pesquisar_and_wait(page, 2):
                                destinatario_filled = True
                                log.info(
                                    f"✓ Destinatario CPF filled via page: {cpf_clean}"
                                )
                                break
                    except Exception:
                        continue
            except Exception as e:
                log.warning(f"Destinatario fill fallback failed: {e}")

        if not destinatario_filled:
            log.warning("⚠️ Destinatario CPF could not be filled, continuing...")
        sleep(0.5)

        # 9 - NCM
        sleep(1)
        ncm_filled = False
        for attempt in range(3):
            try:
                produto_frame = page.frame(name="cmpProduto")
                if produto_frame:
                    # Harden NCM search
                    ncm_input = produto_frame.locator(
                        "input[type='text']:not([name='hintedit'])"
                    ).first
                    if ncm_input.is_visible(timeout=2000):
                        ncm_input.click()
                        ncm_input.clear()
                        ncm_input.fill("0000.00.00")
                        sleep(0.5)
                        click_pesquisar_and_wait(produto_frame, 1.5)
                        ncm_filled = True
                        break
            except Exception:
                sleep(1)

        if not ncm_filled:
            log.warning("NCM filling failed, continuing...")
        sleep(1.5)

        # 10-14 - Product Fields (Item da Nota Fiscal)
        log.info("=== FILLING PRODUCT FIELDS (Item da Nota Fiscal) ===")

        # CRITICAL: Select Product checkbox FIRST (before filling fields and clicking ADICIONAR ITEM)
        log.info("=== SELECTING PRODUCT CHECKBOX ===")
        produto_checkbox_checked = False
        checkbox_selectors = [
            "input[name='chbProduto']",
            "input[type='checkbox'][name*='Produto' i]",
            "input[type='checkbox'][id*='Produto' i]",
            "table:has-text('Produto') input[type='checkbox']",
            "td:has-text('Produto *') input[type='checkbox']",
        ]

        for selector in checkbox_selectors:
            try:
                checkbox = page.locator(selector).first
                if checkbox.is_visible(timeout=5000):
                    # Check if already checked
                    is_checked = checkbox.is_checked()
                    if not is_checked:
                        checkbox.check()
                        log.info(f"✓ Product checkbox checked using: {selector}")
                    else:
                        log.info(f"✓ Product checkbox already checked: {selector}")
                    produto_checkbox_checked = True
                    sleep(0.5)
                    break
            except Exception as e:
                log.warning(f"Checkbox selector '{selector}' failed: {e}")
                continue

        if not produto_checkbox_checked:
            log.warning("⚠️ Product checkbox not found/checked - continuing anyway")
        else:
            log.info("✓✓✓ PRODUCT CHECKBOX SELECTED ✓✓✓")

        sleep(1)

        # Wait for product fields to be available
        sleep(2)
        wait_for_page_load_soft(page, timeout=5000)

        # Field 1: Detalhamento do Produto (Product Description)
        produto_descricao_filled = False
        produto_descricao_selectors = [
            "textarea[name='txaDsDetalheProduto']",
            "textarea[id*='DetalheProduto' i]",
            "textarea[name*='Detalhe' i]",
            "table:has-text('Detalhamento do Produto') textarea",
        ]
        for selector in produto_descricao_selectors:
            try:
                desc_field = page.locator(selector).first
                if desc_field.is_visible(timeout=5000):
                    desc_field.click()
                    desc_field.clear()
                    desc_field.fill("  1 - SID241 ")
                    # Trigger change event (safe eval with try-catch in JS)
                    try:
                        page.evaluate(
                            """
                            const el = document.querySelector('textarea[name=\"txaDsDetalheProduto\"]');
                            if (el) {
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                            """
                        )
                    except Exception:
                        pass  # Event trigger is optional
                    produto_descricao_filled = True
                    log.info("✓ Detalhamento do Produto filled: '  1 - SID241 '")
                    break
            except Exception as e:
                log.warning(f"Descrição selector '{selector}' failed: {e}")
                continue

        if not produto_descricao_filled:
            log.warning("⚠️ Detalhamento do Produto not filled")
        sleep(0.8)

        # Field 2: Unidade de Medida (Unit of Measure)
        unidade_filled = False
        unidade_selectors = [
            "select[name='cmbUnidMedida']",
            "select[name='cmbUnidadeMedidaItem']",
            "select[id*='UnidMedida' i]",
            "table:has-text('Unidade de Medida') select",
        ]
        for selector in unidade_selectors:
            try:
                unidade_select = page.locator(selector).first
                if unidade_select.is_visible(timeout=5000):
                    # Try value first, then label
                    try:
                        unidade_select.select_option(value="9")
                    except Exception:
                        try:
                            unidade_select.select_option(label="UN - Unidade")
                        except Exception:
                            unidade_select.select_option(index=9)

                    # Verify
                    selected = unidade_select.input_value()
                    if selected:
                        unidade_filled = True
                        log.info(f"✓ Unidade de Medida selected: {selected}")
                        break
            except Exception as e:
                log.warning(f"Unidade selector '{selector}' failed: {e}")
                continue

        if not unidade_filled:
            log.warning("⚠️ Unidade de Medida not selected")
        sleep(0.8)

        # Field 3: Quantidade (Quantity)
        quantidade_filled = False
        quantidade_selectors = [
            "input[name='edtQtdProduto']",
            "input[name='txtQuantidadeItem']",
            "input[id*='QtdProduto' i]",
            "table:has-text('Quantidade') input[type='text']",
        ]
        for selector in quantidade_selectors:
            try:
                qtd_field = page.locator(selector).first
                if qtd_field.is_visible(timeout=5000):
                    qtd_field.click()
                    qtd_field.clear()
                    qtd_field.fill("1")
                    # Trigger change event
                    try:
                        page.evaluate(
                            """
                            const el = document.querySelector('input[name=\"edtQtdProduto\"], input[name=\"txtQuantidadeItem\"]');
                            if (el) {
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                            """
                        )
                    except Exception:
                        pass
                    quantidade_filled = True
                    log.info("✓ Quantidade filled: 1")
                    break
            except Exception as e:
                log.warning(f"Quantidade selector '{selector}' failed: {e}")
                continue

        if not quantidade_filled:
            log.warning("⚠️ Quantidade not filled")
        sleep(0.8)

        # Field 4: Valor Unitário (Unit Value)
        valor_filled = False
        valor_selectors = [
            "input[name='edtVlProduto']",
            "input[name='txtVlrtUnitarioItem']",
            "input[id*='VlProduto' i]",
            "table:has-text('Valor Unitário') input[type='text']",
        ]
        for selector in valor_selectors:
            try:
                valor_field = page.locator(selector).first
                if valor_field.is_visible(timeout=5000):
                    valor_field.click()
                    valor_field.clear()
                    valor_field.fill("1100")
                    # Trigger change event
                    try:
                        page.evaluate(
                            """
                            const el = document.querySelector('input[name=\"edtVlProduto\"], input[name=\"txtVlrtUnitarioItem\"]');
                            if (el) {
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                            """
                        )
                    except Exception:
                        pass
                    valor_filled = True
                    log.info("✓ Valor Unitário filled: 1100")
                    break
            except Exception as e:
                log.warning(f"Valor selector '{selector}' failed: {e}")
                continue

        if not valor_filled:
            log.warning("⚠️ Valor Unitário not filled")
        sleep(0.8)

        # Field 5: Alíquota (%) (Tax Rate)
        aliquota_filled = False
        aliquota_selectors = [
            "input[name='edtVlAliquota']",
            "input[name='txtAliquotaItem']",
            "input[id*='Aliquota' i][id!*='IPI' i]",
            "table:has-text('Alíquota') input[type='text']:not([name*='IPI' i])",
        ]
        for selector in aliquota_selectors:
            try:
                aliquota_field = page.locator(selector).first
                if aliquota_field.is_visible(timeout=5000):
                    aliquota_field.click()
                    aliquota_field.clear()
                    aliquota_field.fill("0")
                    # Trigger change event
                    try:
                        page.evaluate(
                            """
                            const el = document.querySelector('input[name=\"edtVlAliquota\"], input[name=\"txtAliquotaItem\"]');
                            if (el) {
                                el.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                            """
                        )
                    except Exception:
                        pass
                    aliquota_filled = True
                    log.info("✓ Alíquota (%) filled: 0")
                    break
            except Exception as e:
                log.warning(f"Alíquota selector '{selector}' failed: {e}")
                continue

        if not aliquota_filled:
            log.warning("⚠️ Alíquota (%) not filled")
        sleep(0.8)

        # Field 6: Alíquota IPI (%) (IPI Tax Rate) - if exists
        aliquota_ipi_filled = False
        aliquota_ipi_selectors = [
            "input[name*='IPI' i][name*='Aliquota' i]",
            "input[id*='IPI' i][id*='Aliquota' i]",
            "input[name*='AliquotaIPI' i]",
            "table:has-text('Alíquota IPI') input[type='text']",
        ]
        for selector in aliquota_ipi_selectors:
            try:
                ipi_field = page.locator(selector).first
                if ipi_field.is_visible(timeout=3000):
                    ipi_field.click()
                    ipi_field.clear()
                    ipi_field.fill("0")
                    # Trigger change event
                    page.evaluate(
                        f"document.querySelector('{selector}')?.dispatchEvent(new Event('change', {{ bubbles: true }}))"
                    )
                    aliquota_ipi_filled = True
                    log.info("✓ Alíquota IPI (%) filled: 0")
                    break
            except Exception:
                continue  # IPI field is optional

        if aliquota_ipi_filled:
            log.info("✓ Alíquota IPI filled (optional field)")

        # Summary
        filled_count = sum(
            [
                produto_descricao_filled,
                unidade_filled,
                quantidade_filled,
                valor_filled,
                aliquota_filled,
            ]
        )
        log.info(
            f"✓✓✓ Product fields filled: {filled_count}/5 required fields completed"
        )

        sleep(1.5)

        # Click ADICIONAR/ALTERAR ITEM (CRITICAL: Must click to add item to table)
        log.info("=== STEP 14: CLICKING 'ADICIONAR/ALTERAR ITEM' BUTTON ===")
        adicionar_clicked = False
        adicionar_selectors = [
            "input[name='btnAdicionarItem']",
            "input[value='Adicionar/Alterar Item' i]",
            "input[value*='Adicionar' i]",
            "input[value*='Alterar' i]",
            "button:has-text('Adicionar' i)",
            "button:has-text('Alterar' i)",
        ]

        for attempt in range(3):
            if adicionar_clicked:
                break
            log.info(
                f"Attempting to click ADICIONAR/ALTERAR ITEM (attempt {attempt + 1}/3)"
            )
            for selector in adicionar_selectors:
                try:
                    adicionar_btn = page.locator(selector).first
                    if adicionar_btn.is_visible(timeout=5000):
                        log.info(
                            f"Found ADICIONAR/ALTERAR ITEM button using: {selector}"
                        )
                        adicionar_btn.click()
                        log.info(
                            f"✓✓✓ ADICIONAR/ALTERAR ITEM button clicked using: {selector} ✓✓✓"
                        )
                        adicionar_clicked = True
                        sleep(4)  # Wait for item to be added to table
                        wait_for_page_load_soft(page, timeout=5000)
                        log.info("✓ Item added to table - waiting for table to update")
                        break
                except Exception as e:
                    log.warning(
                        f"ADICIONAR selector '{selector}' attempt {attempt + 1} failed: {e}"
                    )
                    continue

            if not adicionar_clicked and attempt < 4:
                sleep(2)
                log.info("Retrying ADICIONAR/ALTERAR ITEM button search...")

        if not adicionar_clicked:
            log.error("❌ CRITICAL: ADICIONAR/ALTERAR ITEM button could not be clicked")
            raise Exception("ADICIONAR/ALTERAR ITEM button not found - cannot continue")
        else:
            log.info(
                "✓✓✓ ADICIONAR/ALTERAR ITEM completed - Item should be in table now ✓✓✓"
            )
        sleep(2)

        # 15 - CST (Hardened with multiple strategies)
        # Value 6 = 41 - NÃO TRIBUTADA
        cst_filled = False
        cst_strategies = [
            {"type": "value", "value": "6"},
            {"type": "label", "label": "41 - NÃO TRIBUTADA"},
            {"type": "index", "index": 6},  # Index-based fallback
        ]

        for attempt in range(3):
            if cst_filled:
                break
            try:
                cst_select = page.locator("select[name='cmbNrCST']").first
                cst_select.wait_for(state="visible", timeout=5000)

                for strategy in cst_strategies:
                    try:
                        if strategy["type"] == "value":
                            cst_select.select_option(value=strategy["value"])
                        elif strategy["type"] == "label":
                            cst_select.select_option(label=strategy["label"])
                        elif strategy["type"] == "index":
                            cst_select.select_option(index=strategy["index"])

                        # Verify selection
                        sleep(0.5)
                        selected_value = cst_select.input_value()
                        if selected_value:
                            cst_filled = True
                            log.info(f"✓ CST selected successfully: {selected_value}")
                            break
                    except Exception as e:
                        log.warning(f"CST strategy {strategy['type']} failed: {e}")
                        continue

                if not cst_filled and attempt < 2:
                    sleep(1)
                    wait_for_page_load_soft(page, timeout=3000)
            except Exception as e:
                log.warning(f"CST selection attempt {attempt + 1} failed: {e}")
                sleep(1)

        if not cst_filled:
            log.warning("⚠️ CST selection failed, continuing anyway...")
        sleep(0.5)

        # 16 - Receita
        try:
            page.select_option(
                "select[name='cmbSqReceitaSefin']",
                label="1199 - ICMS - OUTROS (COMERCIO E INDUSTRIA)",
            )
        except:
            try:
                page.select_option("select[name='cmbSqReceitaSefin']", value="335")
            except:
                pass
        sleep(0.5)

        # 16.5 - Checkbox (Selecionar item na tabela)
        log.info("=== SELECTING ITEM CHECKBOX (after adding item) ===")
        sleep(1.5)
        checkbox_selected = False
        checkbox_selectors = [
            "input[type='checkbox'][name*='Selecionar']",
            "input[type='checkbox'][name='chbProduto']",
            "table:has-text('Itens Adicionados') input[type='checkbox']",
        ]

        for selector in checkbox_selectors:
            try:
                checkbox = page.locator(selector).first
                if checkbox.is_visible(timeout=5000):
                    checkbox.check(force=True)
                    log.info(f"✓ Item checkbox selected using: {selector}")
                    checkbox_selected = True
                    break
            except Exception as e:
                log.warning(f"Checkbox selector '{selector}' failed: {e}")
                continue

        if not checkbox_selected:
            log.warning("⚠️ Item checkbox not selected - continuing anyway")
        sleep(1)

        # 17 - Calcular (CRITICAL: Must click before SUBMETER NOTA)
        log.info("=== STEP 17: CLICKING 'CALCULAR' BUTTON ===")
        log.info("⚠️ CRITICAL: CALCULAR must be clicked BEFORE SUBMETER NOTA")
        calcular_clicked = False
        calcular_selectors = [
            "input[name='btnCalcular'][value='Calcular']",
            "input[name='btnCalcular']",
            "input[value='Calcular' i]",
            "button:has-text('Calcular' i)",
            "input[type='submit'][value*='Calcular' i]",
            "input[type='button'][value*='Calcular' i]",
        ]

        for attempt in range(3):  # Reduced attempts for speed
            if calcular_clicked:
                break
            log.info(f"Attempting to click CALCULAR (attempt {attempt + 1}/3)")
            for selector in calcular_selectors:
                try:
                    calcular_btn = page.locator(selector).first
                    if calcular_btn.is_visible(timeout=5000):
                        log.info(f"Found CALCULAR button using: {selector}")
                        calcular_btn.click()
                        log.info(f"✓✓✓ CALCULAR button clicked using: {selector} ✓✓✓")
                        calcular_clicked = True
                        sleep(3)  # Wait for calculation to complete
                        wait_for_page_load_soft(page, timeout=5000)
                        log.info("✓ Calculation processing completed")
                        break
                except Exception as e:
                    log.warning(
                        f"Calcular selector '{selector}' attempt {attempt + 1} failed: {e}"
                    )
                    continue

            if not calcular_clicked and attempt < 4:
                sleep(2)
                log.info("Retrying CALCULAR button search...")

        if not calcular_clicked:
            log.error(
                "❌ CRITICAL: CALCULAR button could not be clicked - continuing anyway to try SUBMETER"
            )
        else:
            log.info(
                "✓✓✓ CALCULAR completed successfully - Ready for SUBMETER NOTA ✓✓✓"
            )
        sleep(2)

        # 18 - SUBMETER NOTA (CRITICAL: Must click AFTER CALCULAR and wait for confirmation page)
        log.info("=== STEP 18: SUBMITTING NOTA (SUBMETER NOTA) ===")
        log.info(
            "⚠️ IMPORTANT: SUBMETER NOTA must be clicked AFTER CALCULAR, then wait for confirmation page"
        )

        # CRITICAL: Re-verify DATE field protection before SUBMETER
        log.info("🔒 RE-VERIFYING DATE FIELD PROTECTION before SUBMETER NOTA")
        try:
            date_field_check = page.locator("input[name='edtDtEmissao']").first
            if date_field_check.is_visible(timeout=2000):
                current_date_value = date_field_check.input_value()
                if date_protected and original_date:
                    if current_date_value != original_date:
                        log.error(
                            f"❌ CRITICAL: DATE field changed from '{original_date}' to '{current_date_value}'!"
                        )
                        log.error("❌ Restoring original DATE value before SUBMETER...")
                        # Restore using JavaScript
                        page.evaluate(
                            f"""
                            const dateField = document.querySelector('input[name=\"edtDtEmissao\"]');
                            if (dateField) {{
                                dateField.value = '{original_date}';
                                dateField.setAttribute('readonly', 'readonly');
                            }}
                        """
                        )
                        sleep(0.5)
                        log.info(f"✓ DATE field restored to: '{original_date}'")
                    else:
                        log.info(
                            f"✓ DATE field protected - value unchanged: '{current_date_value}'"
                        )
                else:
                    log.info(
                        f"⚠️ DATE field value: '{current_date_value}' (protection not initialized)"
                    )
        except Exception as e:
            log.warning(f"Could not verify DATE field: {e}")

        submeter_clicked = False
        submeter_selectors = [
            "input[name='btnIncluirNota']",
            "input[value='Submeter Nota' i]",
            "input[value*='Submeter' i]",
            "button:has-text('Submeter Nota' i)",
            "input[type='button'][value*='Submeter' i]",
        ]

        # Step 1: Click SUBMETER NOTA button (PRECISE CLICK - no accidental field interaction)
        for attempt in range(3):  # Reduced attempts for speed
            if submeter_clicked:
                break
            for selector in submeter_selectors:
                try:
                    submeter_btn = page.locator(selector).first
                    if submeter_btn.is_visible(timeout=5000):
                        log.info(f"Found SUBMETER button using: {selector}")

                        # CRITICAL: Use precise click to avoid touching DATE field
                        # Scroll button into view first to ensure clean click
                        submeter_btn.scroll_into_view_if_needed()
                        sleep(0.5)

                        # Precise click on button only
                        submeter_btn.click(force=False, timeout=5000)
                        log.info("✓✓✓ SUBMETER NOTA button clicked ✓✓✓")
                        submeter_clicked = True

                        # CRITICAL: Verify DATE field was NOT changed after clicking SUBMETER
                        # Use the original_date from the beginning of the function
                        try:
                            date_field_check = page.locator(
                                "input[name='edtDtEmissao']"
                            ).first
                            if date_field_check.is_visible(timeout=2000):
                                new_date_value = date_field_check.input_value()
                                # Get original date from the protected variable at function start
                                if date_protected and "original_date" in locals():
                                    if new_date_value != original_date:
                                        log.error(
                                            f"❌ CRITICAL: DATE field was changed from '{original_date}' to '{new_date_value}'!"
                                        )
                                        log.error(
                                            "❌ Restoring original DATE value immediately..."
                                        )
                                        # Restore original date using JavaScript to avoid triggering events
                                        page.evaluate(
                                            f"""
                                            const dateField = document.querySelector('input[name=\"edtDtEmissao\"]');
                                            if (dateField) {{
                                                dateField.value = '{original_date}';
                                                dateField.dispatchEvent(new Event('change', {{ bubbles: false }}));
                                            }}
                                        """
                                        )
                                        sleep(0.5)
                                        # Verify restoration
                                        restored_value = date_field_check.input_value()
                                        if restored_value == original_date:
                                            log.info(
                                                f"✓ DATE field restored to original: '{original_date}'"
                                            )
                                        else:
                                            log.error(
                                                f"❌ Failed to restore DATE field. Current: '{restored_value}', Expected: '{original_date}'"
                                            )
                                    else:
                                        log.info(
                                            f"✓ DATE field protected - value unchanged: '{new_date_value}'"
                                        )
                                else:
                                    log.info(
                                        f"✓ DATE field value: '{new_date_value}' (no original stored for comparison)"
                                    )
                        except Exception as e:
                            log.warning(f"Could not verify DATE field: {e}")

                        # Wait for confirmation page to open (navigation or popup)
                        log.info(
                            "⏳ Waiting for confirmation page to open after SUBMETER NOTA..."
                        )
                        confirmation_page_opened = False

                        # Check for popup first
                        try:
                            popup = page.wait_for_event("popup", timeout=3000)
                            log.info(
                                "✓ Popup/New window detected - confirmation page opened"
                            )
                            confirmation_page_opened = True
                            # Switch to popup if needed
                            if popup:
                                log.info("Switching to confirmation popup window")
                        except PlaywrightTimeoutError:
                            # No popup, check for page navigation
                            try:
                                sleep(2)  # Wait for navigation
                                new_url = page.url
                                if new_url != initial_url:
                                    log.info(
                                        f"✓ Page navigated to: {new_url} - confirmation page opened"
                                    )
                                    confirmation_page_opened = True
                                else:
                                    log.info(
                                        "No immediate navigation - waiting for confirmation content..."
                                    )
                            except Exception:
                                pass

                        sleep(2)  # Wait for form processing/confirmation page load
                        break
                except Exception as e:
                    log.warning(
                        f"SUBMETER selector '{selector}' attempt {attempt + 1} failed: {e}"
                    )
                    continue

            if not submeter_clicked and attempt < 4:
                sleep(2)
                wait_for_page_load_soft(page, timeout=3000)

        if not submeter_clicked:
            error_msg = "❌ CRITICAL: SUBMETER NOTA button could not be clicked - CANNOT proceed to next CPF"
            log.error(error_msg)
            result["error"] = error_msg
            result["success"] = False
            return result

        # Step 2: WAIT for confirmation page to open (REQUIRED before next CPF)
        log.info("⏳ Waiting for SUBMETER NOTA confirmation page to open...")
        log.info(
            "⚠️ CRITICAL: Must wait for confirmation page to OPEN before proceeding to next CPF"
        )
        submission_confirmed = False

        # Store initial URL to detect page navigation
        try:
            if "initial_url" not in locals():
                initial_url = page.url
                log.info(f"Initial URL before SUBMETER: {initial_url}")
        except Exception:
            initial_url = None

        # Multiple strategies to detect success
        success_indicators = [
            ("text=/sucesso|sucesso/i", "Success message text"),
            ("text=/Nota.*emitida|emitida.*sucesso/i", "Nota emitida message"),
            ("text=/NFA.*gerada|gerada.*com.*sucesso/i", "NFA gerada message"),
            ("text=/Nota.*incluída|incluída.*com.*sucesso/i", "Nota incluída message"),
            (
                "text=/Operação.*realizada|realizada.*com.*sucesso/i",
                "Operação realizada message",
            ),
            (".alert-success, .mensagem-sucesso, .sucesso", "Success CSS class"),
            ("text=/número.*da.*nota|chave.*de.*acesso/i", "Número/chave da nota"),
        ]

        for timeout_attempt in range(4):  # Up to 60 seconds total
            for selector, description in success_indicators:
                try:
                    element = page.locator(selector).first
                    if element.is_visible(timeout=5000):
                        log.info(f"✓✓✓ SUBMETER NOTA CONFIRMED: {description} ✓✓✓")
                        submission_confirmed = True
                        result["success"] = True
                        sleep(2)  # Extra wait for processing
                        break
                except Exception:
                    continue

            if submission_confirmed:
                break

            # Also check for page navigation/changes (confirmation page opened)
            try:
                # Check if URL changed (indicates confirmation page opened)
                current_url = page.url
                if initial_url and current_url != initial_url:
                    log.info(
                        f"✓✓✓ SUBMETER NOTA CONFIRMED: Page navigated from '{initial_url}' to '{current_url}' ✓✓✓"
                    )
                    log.info(
                        "✓✓✓ Confirmation page opened - SUBMETER NOTA successful ✓✓✓"
                    )
                    submission_confirmed = True
                    result["success"] = True
                    sleep(3)  # Wait for confirmation page to fully load
                    break
                elif (
                    "sucesso" in current_url.lower()
                    or "confirmacao" in current_url.lower()
                ):
                    log.info("✓✓✓ SUBMETER NOTA CONFIRMED: URL indicates success ✓✓✓")
                    submission_confirmed = True
                    result["success"] = True
                    sleep(3)  # Wait for confirmation page to fully load
                    break
            except Exception:
                pass

            if not submission_confirmed:
                log.info(
                    f"Waiting for confirmation... (attempt {timeout_attempt + 1}/4)"
                )
                sleep(10)  # Wait 10 seconds between attempts
                wait_for_page_load_soft(page, timeout=5000)

        if not submission_confirmed:
            # Final check with longer timeout and page content check
            log.info("Performing final confirmation check...")
            try:
                # Check page content for any success indicators
                page_content = page.content()
                success_keywords = [
                    "sucesso",
                    "emitida",
                    "gerada",
                    "incluída",
                    "número da nota",
                    "chave de acesso",
                ]
                found_keyword = None
                for keyword in success_keywords:
                    if keyword.lower() in page_content.lower():
                        found_keyword = keyword
                        break

                if found_keyword:
                    log.info(
                        f"✓✓✓ SUBMETER NOTA CONFIRMED: Found '{found_keyword}' in page content ✓✓✓"
                    )
                    submission_confirmed = True
                    result["success"] = True
                else:
                    # Try one more time with selector
                    page.wait_for_selector(
                        "text=/sucesso|sucesso|emitida|gerada|incluída/i", timeout=5000
                    )
                    log.info(
                        "✓✓✓ SUBMETER NOTA CONFIRMED (late detection via selector) ✓✓✓"
                    )
                    submission_confirmed = True
                    result["success"] = True
            except PlaywrightTimeoutError:
                # Last resort: check if form was reset or page changed (indicates submission)
                try:
                    current_url = page.url
                    # If we're still on the form page but form fields are reset, might indicate success
                    form_reset = not page.locator(
                        "input[name='edtDtEmissao']"
                    ).is_visible(timeout=2000)
                    if form_reset or "sucesso" in current_url.lower():
                        log.info(
                            "✓✓✓ SUBMETER NOTA CONFIRMED: Form reset or URL change indicates success ✓✓✓"
                        )
                        submission_confirmed = True
                        result["success"] = True
                    else:
                        error_msg = "❌ CRITICAL: SUBMETER NOTA confirmation not received - CANNOT proceed to next CPF"
                        log.error(error_msg)
                        result["error"] = (
                            "SUBMETER NOTA confirmation timeout - success message not found"
                        )
                        result["success"] = False
                    return result
                except Exception:
                    error_msg = "❌ CRITICAL: SUBMETER NOTA confirmation not received - CANNOT proceed to next CPF"
                    log.error(error_msg)
                    result["error"] = (
                        "SUBMETER NOTA confirmation timeout - success message not found"
                    )
                    result["success"] = False
                    return result

        log.info(
            "✅✅✅ SUBMETER NOTA COMPLETED SUCCESSFULLY - Ready for next CPF ✅✅✅"
        )
        return result

    except Exception as e:
        result["error"] = str(e)
        log.error(f"Processing failed: {e}")
        return result


def process_batch(
    batch_data: List[Dict[str, str]],
    max_forms: int = None,
    speed_multiplier: float = 1.0,
):
    """Process batch with restart logic."""
    global SPEED_MULTIPLIER
    SPEED_MULTIPLIER = speed_multiplier

    if max_forms:
        batch_data = batch_data[:max_forms]

    total_items = len(batch_data)
    logger.info(f"Starting batch processing for {total_items} items")

    # New browser session per 10 items (chunk)
    CHUNK_SIZE = 10
    results = []

    for chunk_idx in range(0, total_items, CHUNK_SIZE):
        chunk = batch_data[chunk_idx : chunk_idx + CHUNK_SIZE]
        logger.info(
            f"Starting chunk {chunk_idx // CHUNK_SIZE + 1} (Items {chunk_idx+1} to {chunk_idx+len(chunk)})"
        )

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context = browser.new_context(accept_downloads=True)
                page = context.new_page()

                # Login (optimized waits instead of long fixed sleeps)
                page.goto(LOGIN_URL, wait_until="domcontentloaded")
                try:
                    page.wait_for_selector("input[name='edtNoLogin']", timeout=5000)
                    page.wait_for_selector("input[name='edtDsSenha']", timeout=5000)
                except PlaywrightTimeoutError:
                    logger.warning(
                        "Login fields did not appear within 5s (continuing)."
                    )
                sleep(0.5)
                page.fill("input[name='edtNoLogin']", USERNAME)
                page.fill("input[name='edtDsSenha']", PASSWORD)
                page.evaluate("logarSistema()")
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except PlaywrightTimeoutError:
                    logger.info("Login navigation wait timed out (continuing).")
                sleep(0.5)

                chunk_results = []
                for i, item in enumerate(chunk):
                    global_idx = chunk_idx + i
                    ctx = {
                        "batch": chunk_idx // CHUNK_SIZE + 1,
                        "item": global_idx + 1,
                        "total": total_items,
                        "loja": item.get("loja"),
                        "cpf": item.get("cpf"),
                        "test": item.get("test"),  # Info Adicionais text
                    }

                    res = process_single_nfa(page, context, ctx, speed_multiplier)
                    chunk_results.append(res)
                    results.append(res)

                    # CRITICAL: Only proceed to next CPF if SUBMETER NOTA was successful
                    if not res.get("success", False):
                        logger.error(
                            f"⚠️ NFA {ctx['item']}/{ctx['total']} failed. Error: {res.get('error', 'Unknown')}"
                        )
                        logger.warning(
                            "⚠️ Continuing to next CPF despite failure (check logs for details)"
                        )
                    else:
                        logger.info(
                            f"✓✓✓ NFA {ctx['item']}/{ctx['total']} completed successfully - proceeding to next CPF"
                        )

                    if i < len(chunk) - 1:
                        sleep(
                            1.5
                        )  # Shorter wait between CPFs; still gives server time to settle

                browser.close()

                # Per-batch log
                batch_log_path = (
                    Path(LOGS_DIR) / f"nfa_batch_{chunk_idx // CHUNK_SIZE + 1}.log"
                )
                with open(batch_log_path, "w", encoding="utf-8") as f:
                    for r in chunk_results:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")

        except Exception as e:
            logger.error(f"Chunk processing failed: {e}")

    return results


def load_batch_from_file(file_path: str) -> List[Dict[str, str]]:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load batch: {e}")
        return []


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("batch_file", nargs="?", default="input/batch_example.json")
    parser.add_argument("--speed", type=float, default=1.0)
    parser.add_argument("--max-forms", type=int, default=None)
    args = parser.parse_args()

    data = load_batch_from_file(args.batch_file)
    if data:
        process_batch(data, args.max_forms, args.speed)
