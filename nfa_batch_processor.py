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
# Get EMITENTE_CNPJ from env, with fallback default
EMITENTE_CNPJ_ENV = os.getenv("NFA_EMITENTE_CNPJ", "")
# If env value is placeholder or empty, use default
if not EMITENTE_CNPJ_ENV or EMITENTE_CNPJ_ENV == "00000000000000":
    EMITENTE_CNPJ = "28.842.017/0001-05"  # Default CNPJ
else:
    # Clean and format the CNPJ from env
    EMITENTE_CNPJ = EMITENTE_CNPJ_ENV.strip().strip('"').strip("'")
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


def wait_for_page_load_soft(page: Page, timeout: int = 8000):
    """Soft-mode navigation wait."""
    try:
        page.wait_for_load_state("domcontentloaded", timeout=timeout)
        page.wait_for_load_state("networkidle", timeout=timeout)
    except PlaywrightTimeoutError:
        logger.info("Soft-mode: Page load timeout (continuing).")


def safe_click(page: Page, selector: str, description: str, timeout: int = 6000):
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
        loc.wait_for(state="visible", timeout=6000)
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
        pesquisar_btn = frame_or_page.locator("input[value='Pesquisar']").first
        if pesquisar_btn.is_visible(timeout=3000):
            pesquisar_btn.click()
            sleep(wait_seconds)
            return True
    except Exception:
        pass
    return False


def fill_informacoes_adicionais(page: Page, loja: str) -> bool:
    """Fill Informações Adicionais."""
    try:
        info_text = loja
        logger.info(f"Filling Informações Adicionais: '{info_text}'")

        info_field = page.locator("textarea[name='txaInformacoesAdicionais']").first
        info_field.wait_for(state="visible", timeout=10000)
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

        page.wait_for_selector("select[name='cmbNaturezaOperacao']", timeout=15000)

        # Fill Info Adicionais
        if not fill_informacoes_adicionais(page, loja):
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

        # 7 - Emitente (CNPJ fixo, com retries) - MODERNIZED: Direct selectors, no frames
        page.select_option("select[name='cmbTpDoccmpEmitente']", "2")
        sleep(0.5)
        emitente_filled = False
        emitente_cnpj_clean = extract_clean_cpf(EMITENTE_CNPJ)

        for attempt in range(5):
            try:
                # Try direct input selector (modern approach - no frames)
                cnpj_input = page.locator("input[name*='Emitente' i][type='text']").first
                if not cnpj_input.is_visible(timeout=3000):
                    # Fallback: try any text input near emitente area
                    cnpj_input = page.locator("input[type='text']").nth(0)
                
                if cnpj_input.is_visible(timeout=5000):
                    cnpj_input.click()
                    cnpj_input.clear()
                    cnpj_input.fill(emitente_cnpj_clean)
                    log.info(f"✓ Emitente CNPJ input filled: {emitente_cnpj_clean}")
                    sleep(0.5)
                    
                    # Click Pesquisar button (try multiple selectors)
                    pesquisar_clicked = False
                    for btn_selector in [
                        "button:has-text('Pesquisar')",
                        "input[value='Pesquisar']",
                        "input[type='button'][value*='Pesquisar' i]"
                    ]:
                        try:
                            btn = page.locator(btn_selector).first
                            if btn.is_visible(timeout=2000):
                                btn.click()
                                pesquisar_clicked = True
                                log.info("✓ Clicked Pesquisar for Emitente")
                                sleep(2)  # Wait for search results
                                break
                        except Exception:
                            continue
                    
                    if pesquisar_clicked:
                        emitente_filled = True
                        break
                    else:
                        log.warning("Pesquisar button not found, but CNPJ filled")
                        emitente_filled = True  # Consider filled if input is OK
                        break
                else:
                    log.warning(f"Emitente input not visible, attempt {attempt + 1}/5")
                    sleep(1)
                    
            except Exception as e:
                log.warning(f"Emitente fill attempt {attempt + 1}/5 failed: {e}")
                sleep(1)

        if not emitente_filled:
            log.error("Emitente CNPJ could not be filled after retries")
            raise Exception("Failed to fill Emitente CNPJ")
        sleep(0.5)

        # 8 - Destinatário - MODERNIZED: Direct selectors, no frames
        page.select_option("select[name='cmbTpDoccmpDestinatario']", "3")
        sleep(0.5)
        
        try:
            # Try direct input selector (modern approach - no frames)
            cpf_input = page.locator("input[name*='Destinatario' i][type='text']").first
            if not cpf_input.is_visible(timeout=3000):
                # Fallback: try any text input after destinatario select
                cpf_input = page.locator("input[type='text']").nth(1)
            
            if cpf_input.is_visible(timeout=5000):
                cpf_input.click()
                cpf_input.clear()
                cpf_input.fill(cpf)
                log.info(f"✓ Destinatario CPF filled: {cpf}")
                sleep(0.5)
                
                # Click Pesquisar button
                for btn_selector in [
                    "button:has-text('Pesquisar')",
                    "input[value='Pesquisar']",
                    "input[type='button'][value*='Pesquisar' i]"
                ]:
                    try:
                        btn = page.locator(btn_selector).nth(1)  # Second pesquisar button
                        if btn.is_visible(timeout=2000):
                            btn.click()
                            log.info("✓ Clicked Pesquisar for Destinatario")
                            sleep(2)  # Wait for search results
                            break
                    except Exception:
                        continue
            else:
                log.warning("Destinatario input not found, trying frame fallback...")
                # Fallback to old frame approach if direct selector fails
                destinatario_frame = page.frame(name="cmpDestinatario")
                if destinatario_frame:
                    hardened_interaction(
                        destinatario_frame,
                        "input[type='text']",
                        "Destinatario CPF",
                        "fill",
                        cpf,
                    )
                    click_pesquisar_and_wait(destinatario_frame, 2)
        except Exception as e:
            log.warning(f"Destinatario fill error: {e}, trying frame fallback...")
            try:
                destinatario_frame = page.frame(name="cmpDestinatario")
                if destinatario_frame:
                    hardened_interaction(
                        destinatario_frame,
                        "input[type='text']",
                        "Destinatario CPF",
                        "fill",
                        cpf,
                    )
                    click_pesquisar_and_wait(destinatario_frame, 2)
            except Exception as frame_error:
                log.error(f"Both direct and frame approaches failed: {frame_error}")
        
        sleep(0.5)

        # 9 - NCM - MODERNIZED: Direct selectors with frame fallback
        sleep(1)
        ncm_filled = False
        
        for attempt in range(5):
            try:
                # Try direct selector first (modern approach)
                ncm_input = page.locator("input[name*='Produto' i][type='text']").first
                if not ncm_input.is_visible(timeout=2000):
                    # Try alternative selectors
                    ncm_input = page.locator("input[type='text'][placeholder*='NCM' i]").first
                if not ncm_input.is_visible(timeout=2000):
                    ncm_input = page.locator("input[type='text']").nth(2)  # Fallback to nth input
                
                if ncm_input.is_visible(timeout=3000):
                    ncm_input.click()
                    ncm_input.clear()
                    ncm_input.fill("0000.00.00")
                    log.info("✓ NCM filled: 0000.00.00")
                    sleep(0.5)
                    
                    # Click Pesquisar for NCM
                    for btn_selector in [
                        "button:has-text('Pesquisar')",
                        "input[value='Pesquisar']",
                        "input[type='button'][value*='Pesquisar' i]"
                    ]:
                        try:
                            btn = page.locator(btn_selector).nth(2)  # Third pesquisar button
                            if btn.is_visible(timeout=2000):
                                btn.click()
                                log.info("✓ Clicked Pesquisar for NCM")
                                sleep(1.5)
                                ncm_filled = True
                                break
                        except Exception:
                            continue
                    
                    if ncm_filled:
                        break
                        
                # Fallback to frame approach
                produto_frame = page.frame(name="cmpProduto")
                if produto_frame:
                    ncm_input_frame = produto_frame.locator(
                        "input[type='text']:not([name='hintedit'])"
                    ).first
                    if ncm_input_frame.is_visible(timeout=2000):
                        ncm_input_frame.click()
                        ncm_input_frame.clear()
                        ncm_input_frame.fill("0000.00.00")
                        sleep(0.5)
                        click_pesquisar_and_wait(produto_frame, 1.5)
                        ncm_filled = True
                        break
                        
            except Exception as e:
                log.debug(f"NCM fill attempt {attempt + 1}/5 failed: {e}")
                sleep(1)

        if not ncm_filled:
            log.warning("NCM filling failed, continuing...")
        sleep(1.5)

        # 10-14 - Product Fields
        try:
            page.locator("textarea[name='txaDsDetalheProduto']").first.fill(
                "  1 - SID241 "
            )
            page.evaluate(
                "document.querySelector('textarea[name=\"txaDsDetalheProduto\"]').dispatchEvent(new Event('change', { bubbles: true }))"
            )
        except:
            pass
        sleep(0.5)

        try:
            page.locator("select[name='cmbUnidMedida']").first.select_option(value="9")
        except:
            pass
        sleep(0.5)

        try:
            page.locator("input[name='edtQtdProduto']").first.fill("1")
            page.evaluate(
                "document.querySelector('input[name=\"edtQtdProduto\"]').dispatchEvent(new Event('change', { bubbles: true }))"
            )
        except:
            pass
        sleep(0.5)

        try:
            page.locator("input[name='edtVlProduto']").first.fill("1100")
            page.evaluate(
                "document.querySelector('input[name=\"edtVlProduto\"]').dispatchEvent(new Event('change', { bubbles: true }))"
            )
        except:
            pass
        sleep(0.5)

        try:
            page.locator("input[name='edtVlAliquota']").first.fill("0")
            page.evaluate(
                "document.querySelector('input[name=\"edtVlAliquota\"]').dispatchEvent(new Event('change', { bubbles: true }))"
            )
        except:
            pass
        sleep(1)

        # Click ADICIONAR/ALTERAR ITEM (Hardened)
        hardened_interaction(page, "input[name='btnAdicionarItem']", "ADICIONAR ITEM")
        sleep(3)

        # 15 - CST (Hardened) - IMPROVED: Multiple fallback strategies
        # Value 6 = 41 - NÃO TRIBUTADA
        cst_selected = False
        wait_for_page_load_soft(page)  # Ensure page is stable
        sleep(2)  # Extra wait for CST select to be ready after ADICIONAR ITEM
        
        for attempt in range(3):
            try:
                cst_select = page.locator("select[name='cmbNrCST']").first
                # Wait for select to be visible and enabled
                cst_select.wait_for(state="visible", timeout=10000)
                
                # Wait a bit more for options to load
                sleep(0.5)
                
                # Try multiple selection strategies
                strategies = [
                    lambda: cst_select.select_option(value="6"),  # By value
                    lambda: cst_select.select_option(label="41 - NÃO TRIBUTADA"),  # By label
                    lambda: cst_select.select_option(index=6),  # By index
                ]
                
                for strategy_idx, strategy in enumerate(strategies):
                    try:
                        strategy()
                        log.info(f"✓ CST selected using strategy {strategy_idx + 1}")
                        cst_selected = True
                        break
                    except Exception as strategy_error:
                        log.debug(f"CST strategy {strategy_idx + 1} failed: {strategy_error}")
                        continue
                
                if cst_selected:
                    break
                    
                # Last resort: iterate through options
                if not cst_selected:
                    try:
                        options = cst_select.locator("option")
                        option_count = options.count()
                        log.info(f"Found {option_count} CST options, searching for '41'...")
                        for i in range(min(option_count, 50)):  # Limit search
                            option_text = options.nth(i).inner_text()
                            if "41" in option_text or "NÃO TRIBUTADA" in option_text.upper():
                                cst_select.select_option(index=i)
                                log.info(f"✓ CST selected by iteration (index {i}): {option_text}")
                                cst_selected = True
                                break
                    except Exception as iter_error:
                        log.warning(f"Option iteration failed: {iter_error}")
                        
            except Exception as e:
                log.warning(f"CST selection attempt {attempt + 1}/3 failed: {e}")
                if attempt < 2:
                    sleep(1)
                    wait_for_page_load_soft(page)
                else:
                    log.error("CST selection failed after all attempts")
        
        if not cst_selected:
            log.error("⚠️  CST could not be selected - continuing anyway")
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

        # 16.5 - Checkbox
        sleep(1.5)
        try:
            page.locator("input[type='checkbox'][name*='Selecionar']").first.check(
                force=True
            )
        except Exception as e:
            log.warning(f"Checkbox selection failed: {e}")

        # 17 - Calcular (Hardened)
        hardened_interaction(
            page, "input[name='btnCalcular'][value='Calcular']", "Calcular"
        )

        # 18 - Submeter Nota (Soft-mode)
        log.info("Submitting note...")
        try:
            submeter_btn = page.locator("input[name='btnIncluirNota']").first
            submeter_btn.click()

            # Soft-mode: Wait for popup OR stay on page
            try:
                page.wait_for_event("popup", timeout=5000)
            except PlaywrightTimeoutError:
                log.info("Soft-mode: No popup detected.")

        except Exception as e:
            log.warning(f"Submit button click issue: {e}")

        # Wait for success message (ALWAYS)
        try:
            page.wait_for_selector("text=/sucesso|sucesso/i", timeout=15000)
            log.info("SUCCESS: Submission confirmed via DOM.")
            result["success"] = True
        except PlaywrightTimeoutError:
            log.error("FAILURE: Success message not found.")
            result["error"] = "Success message missing"
            return result

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

                # Login
                page.goto(LOGIN_URL)
                sleep(2)
                page.fill("input[name='edtNoLogin']", USERNAME)
                page.fill("input[name='edtDsSenha']", PASSWORD)
                page.evaluate("logarSistema()")
                sleep(4)

                chunk_results = []
                for i, item in enumerate(chunk):
                    global_idx = chunk_idx + i
                    ctx = {
                        "batch": chunk_idx // CHUNK_SIZE + 1,
                        "item": global_idx + 1,
                        "total": total_items,
                        "loja": item.get("loja"),
                        "cpf": item.get("cpf"),
                    }

                    res = process_single_nfa(page, context, ctx, speed_multiplier)
                    chunk_results.append(res)
                    results.append(res)

                    if i < len(chunk) - 1:
                        sleep(2)

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
