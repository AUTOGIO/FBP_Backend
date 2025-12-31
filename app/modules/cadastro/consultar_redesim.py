"""Post-login REDESIM consultation workflow.

Requires an already authenticated ATF Playwright page.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence, Union

import httpx
from playwright.async_api import Frame, Locator, Page

from app.modules.nfa.delays import (
    AFTER_SEARCH_DELAY,
    CLICK_DELAY,
    DEFAULT_DELAY,
    FIELD_DELAY,
    NETWORK_IDLE_TIMEOUT,
)
from app.modules.redesim.draft_creator import GmailService

logger = logging.getLogger(__name__)

FormContext = Union[Page, Frame]

REDESIM_CONSULT_URL = (
    "https://www4.sefaz.pb.gov.br/atf/cad/CADf_ConsultarProcessosREDESIM.do"
    "?limparSessao=true"
)

DEFAULT_CRIACAO_INICIO = "10/12/2025"
DEFAULT_CRIACAO_FIM = "17/12/2025"

_FORM_SELECTORS: Sequence[str] = (
    "form[action*='ConsultarProcessosREDESIM']",
    "form[name*='ConsultarProcessosREDESIM' i]",
    "form:has(button:has-text('Consultar'))",
)

_RESULT_HINTS: Sequence[str] = (
    "text=Situação do Processo",
    "table:has-text('Situação do Processo')",
    "text=Situação do conjunto de inconsistências",
    "text=Nenhum registro encontrado",
)

# Fallback selectors for double-list widgets
SITUACAO_PROCESSO_CONTAINER = "table:has-text('Situação do Processo')"
SITUACAO_INCONSISTENCIAS_CONTAINER = (
    "table:has-text('Situação do conjunto de Inconsistências')"
)

# Defaults requested by user
DEFAULT_NATUREZA_VALUE = "1"  # CADASTRAMENTO
DEFAULT_CRIACAO_INICIO = "10/12/2025"
DEFAULT_CRIACAO_FIM = "17/12/2025"

# Optimized delays (reduced for faster execution)
FAST_TIMEOUT = 10000  # 10 seconds (reduced from 30s)
ELEMENT_TIMEOUT = 5000  # 5 seconds for known elements
MINIMAL_DELAY = 100  # 100ms minimal delay
FAST_FIELD_DELAY = 200  # 200ms (reduced from 800ms)
FAST_CLICK_DELAY = 200  # 200ms (reduced from 600ms)
FAST_DEFAULT_DELAY = 300  # 300ms (reduced from 1500ms)
FAST_SEARCH_DELAY = 500  # 500ms (reduced from 2000ms)


def _is_page_closed(page: Page) -> bool:
    """Check if page is closed."""
    try:
        # Try to access page properties - will raise if closed
        _ = page.url
        return False
    except Exception:
        return True


async def _wait_network_idle(page: Page) -> None:
    """Optimized: Use domcontentloaded instead of networkidle for faster execution."""
    try:
        # domcontentloaded is much faster than networkidle
        await page.wait_for_load_state(
            "domcontentloaded",
            timeout=FAST_TIMEOUT,
        )
    except Exception as load_err:
        logger.debug("domcontentloaded wait skipped: %s", load_err)


async def _resolve_form_context(page: Page) -> FormContext:
    """Locate the REDESIM form either on the page or inside a frame."""
    search_targets: Sequence[FormContext] = (page, *page.frames)

    for target in search_targets:
        for selector in _FORM_SELECTORS:
            try:
                await target.locator(selector).first.wait_for(
                    timeout=FAST_TIMEOUT  # Reduced from 30s to 10s
                )
                logger.info(
                    "cadastro_redesim: consultation form detected via %s",
                    selector,
                )
                return target
            except Exception:
                continue

    # Fallback: try any context containing the REDESIM label text
    for target in search_targets:
        try:
            await target.get_by_text("REDESIM", exact=False).wait_for(
                timeout=FAST_TIMEOUT  # Reduced from 30s to 10s
            )
            logger.warning(
                "cadastro_redesim: form fallback detection via text " "match in a frame"
            )
            return target
        except Exception:
            continue

    raise RuntimeError("Consulta REDESIM form not available after navigation.")


def _is_valid_date(value: str | None) -> bool:
    if not value:
        return False
    return bool(re.fullmatch(r"\d{2}/\d{2}/\d{4}", value.strip()))


async def _fill_field(
    context: FormContext,
    page: Page,
    value: Any,
    labels: Sequence[str],
    selectors: Sequence[str],
    field_name: str,
) -> bool:
    """Fill a form field using label-first, selector-second strategy."""
    if value in (None, ""):
        return False

    for label in labels:
        try:
            locator = context.get_by_label(label, exact=False)
            await locator.wait_for(timeout=ELEMENT_TIMEOUT)  # Reduced timeout
            await locator.fill(str(value))
            # Removed delay - element is already ready after wait_for
            logger.debug(
                "cadastro_redesim: filled %s via label '%s'",
                field_name,
                label,
            )
            return True
        except Exception:
            continue

    for selector in selectors:
        try:
            locator = context.locator(selector).first
            await locator.wait_for(timeout=ELEMENT_TIMEOUT)  # Reduced timeout
            await locator.fill(str(value))
            # Removed delay - element is already ready after wait_for
            logger.debug(
                "cadastro_redesim: filled %s via selector '%s'",
                field_name,
                selector,
            )
            return True
        except Exception:
            continue

    raise RuntimeError(f"Could not locate field for '{field_name}'.")


async def _ensure_natureza_cadastramento(context: FormContext, page: Page) -> None:
    """Force Natureza da Solicitação = CADASTRAMENTO."""
    selectors = (
        "select[name='cmbOperacao']",
        "select[name*='cmbOperacao' i]",
        "select[name*='Operacao' i]",
    )
    for sel in selectors:
        try:
            select_box = context.locator(sel).first
            await select_box.wait_for(timeout=ELEMENT_TIMEOUT)  # Reduced timeout
            try:
                await select_box.select_option(label="CADASTRAMENTO")
            except Exception:
                await select_box.select_option(value="1")
            logger.info("cadastro_redesim: natureza set to CADASTRAMENTO")
            return
        except Exception:
            continue
    raise RuntimeError("Natureza da Solicitação (CADASTRAMENTO) não localizada.")


async def _ensure_situacao_processo_deferido(context: FormContext, page: Page) -> bool:
    """Seleciona apenas DEFERIDO e move para selecionados (conforme imagem correta)."""
    # Usar seletor específico do guia: lstSitFacDisp (Disponíveis)
    try:
        # Localizar o select de Disponíveis na seção "Situação do Processo"
        # Guia: document.querySelector("body > table > tbody > tr:nth-child(2) > td > form > table > tbody > tr:nth-child(15) > td > table > tbody > tr.tdPadrao > td:nth-child(3) > select")
        container = context.locator("table:has-text('Situação do Processo')").first
        await container.wait_for(timeout=FAST_TIMEOUT)  # Optimized timeout

        # Tentar selector específico do guia primeiro
        disponiveis_selectors = [
            "body > table > tbody > tr:nth-child(2) > td > form > table > tbody > tr:nth-child(15) > td > table > tbody > tr.tdPadrao > td:nth-child(3) > select",
            "select[name='lstSitFacDisp']",
            "table:has-text('Situação do Processo') select[name='lstSitFacDisp']",
        ]

        disponiveis = None
        for sel in disponiveis_selectors:
            try:
                disponiveis = context.locator(sel).first
                await disponiveis.wait_for(timeout=5000)
                break
            except Exception:
                continue

        if not disponiveis:
            raise RuntimeError(
                "Select de Disponíveis (Situação do Processo) não encontrado"
            )

        # Primeiro, verificar se DEFERIDO já está em Selecionadas
        # Se estiver, não precisa fazer nada
        selecionadas_selectors = [
            "select[name='lstSitFacSel']",
            "table:has-text('Situação do Processo') select[name='lstSitFacSel']",
        ]

        deferido_ja_selecionado = False
        for sel in selecionadas_selectors:
            try:
                selecionadas = context.locator(sel).first
                await selecionadas.wait_for(timeout=5000)
                options = await selecionadas.locator("option").all_text_contents()
                if any("DEFERIDO" in opt.upper() for opt in options):
                    logger.info("cadastro_redesim: DEFERIDO já está em Selecionadas")
                    deferido_ja_selecionado = True
                    break
            except Exception:
                continue

        if not deferido_ja_selecionado:
            # Selecionar apenas DEFERIDO (value=2 baseado em padrões comuns)
            # Tentar por value primeiro, depois por texto
            try:
                await disponiveis.select_option(value="2")
                logger.info("cadastro_redesim: DEFERIDO selecionado por value=2")
            except Exception:
                # Fallback: selecionar por texto (buscar opção que contenha DEFERIDO)
                try:
                    options = await disponiveis.locator("option").all()
                    for opt in options:
                        text = await opt.text_content()
                        if text and "DEFERIDO" in text.upper():
                            value = await opt.get_attribute("value")
                            if value:
                                await disponiveis.select_option(value=value)
                                logger.info(
                                    "cadastro_redesim: DEFERIDO selecionado por texto"
                                )
                                break
                    else:
                        raise ValueError("DEFERIDO não encontrado nas opções")
                except Exception:
                    # Último fallback: selecionar por índice (geralmente DEFERIDO é o segundo)
                    try:
                        await disponiveis.select_option(index=1)
                        logger.info("cadastro_redesim: DEFERIDO selecionado por índice")
                    except Exception as e:
                        logger.warning(
                            f"cadastro_redesim: não foi possível selecionar DEFERIDO: {e}"
                        )
                        return False

            await page.wait_for_timeout(MINIMAL_DELAY)  # Minimal delay after select

            # Clicar no botão >> para mover para Selecionadas
            # Guia: document.querySelector("body > table > tbody > tr:nth-child(2) > td > form > table > tbody > tr:nth-child(15) > td > table > tbody > tr.tdPadrao > td.tdPadrao > input:nth-child(4)")
            mover_btn_selectors = [
                "body > table > tbody > tr:nth-child(2) > td > form > table > tbody > tr:nth-child(15) > td > table > tbody > tr.tdPadrao > td.tdPadrao > input:nth-child(4)",
                "table:has-text('Situação do Processo') input[type='button'][value='>>']",
                "input[type='button'][value='>>']",
            ]

            mover_btn = None
            for sel in mover_btn_selectors:
                try:
                    mover_btn = context.locator(sel).first
                    await mover_btn.wait_for(timeout=5000)
                    break
                except Exception:
                    continue

            if not mover_btn:
                raise RuntimeError(
                    "Botão >> (mover Situação do Processo) não encontrado"
                )

            await mover_btn.click()
            logger.info("cadastro_redesim: DEFERIDO movido para Selecionadas")
            await page.wait_for_timeout(FAST_CLICK_DELAY)  # Optimized click delay

            # Atualizar hidden field com DEFERIDO
            try:
                await page.evaluate(
                    """
                    () => {
                        const frm = document.forms['frmConsultarPendeciaProc'];
                        if (frm && frm.hidSitFacSel) {
                            frm.hidSitFacSel.value = 'DEFERIDO#2¨';
                        }
                    }
                    """
                )
            except Exception:
                pass

        return True
    except Exception as e:
        logger.warning(
            f"cadastro_redesim: erro ao selecionar situação do processo: {e}"
        )
        return False


async def _check_listar_outros_processos(context: FormContext, page: Page) -> None:
    """Marca o checkbox 'listar outros processos' (conforme imagem correta)."""
    try:
        # Procurar checkbox "listar outros processos"
        checkbox_selectors = [
            "input[type='checkbox'][name*='listar' i]",
            "input[type='checkbox']:has-text('listar outros processos')",
            "input[type='checkbox']",
        ]

        checkbox = None
        for sel in checkbox_selectors:
            try:
                checkboxes_locator = context.locator(sel)
                count = await checkboxes_locator.count()
                for i in range(count):
                    cb = checkboxes_locator.nth(i)
                    text = await cb.evaluate(
                        "el => el.parentElement?.textContent || ''"
                    )
                    if (
                        "listar outros processos" in text.lower()
                        or "listar outros" in text.lower()
                    ):
                        checkbox = cb
                        break
                if checkbox:
                    break
            except Exception:
                continue

        if checkbox:
            is_checked = await checkbox.is_checked()
            if not is_checked:
                await checkbox.check()
                logger.info(
                    "cadastro_redesim: checkbox 'listar outros processos' marcado"
                )
            else:
                logger.info(
                    "cadastro_redesim: checkbox 'listar outros processos' já estava marcado"
                )
        else:
            logger.warning(
                "cadastro_redesim: checkbox 'listar outros processos' não encontrado"
            )
    except Exception as e:
        logger.warning(
            f"cadastro_redesim: erro ao marcar checkbox 'listar outros processos': {e}"
        )


async def _select_all_inconsistencias(context: FormContext, page: Page) -> None:
    """Seleciona todas as opções de inconsistências e move para Selecionadas."""
    try:
        # Localizar container "Situação do conjunto de Inconsistências"
        container = context.locator(
            "table:has-text('Situação do conjunto de Inconsistências')"
        ).first
        await container.wait_for(timeout=FAST_TIMEOUT)  # Optimized timeout

        # Selecionar no select de Disponíveis (lstSitIncoDisp)
        # Guia: document.querySelector("body > table > tbody > tr:nth-child(2) > td > form > table > tbody > tr:nth-child(15) > td > table > tbody > tr.tdPadrao > td:nth-child(1) > select > option:nth-child(1)")
        disponiveis_selectors = [
            "select[name='lstSitIncoDisp']",
            "table:has-text('Situação do conjunto de Inconsistências') select[name='lstSitIncoDisp']",
        ]

        disponiveis = None
        for sel in disponiveis_selectors:
            try:
                disponiveis = container.locator(sel).first
                await disponiveis.wait_for(timeout=5000)
                break
            except Exception:
                continue

        if not disponiveis:
            raise RuntimeError("Select de Disponíveis (Inconsistências) não encontrado")

        # Selecionar todas as opções: -1, 1, 2, 3, 4
        # SEM INCONSISTÊNCIAS (-1), NÃO TRATADAS (1), EM TRATAMENTO (2), LIBERADAS (3), NÃO LIBERADAS (4)
        target_values = ["-1", "1", "2", "3", "4"]
        await disponiveis.select_option(value=target_values)
        logger.info(
            "cadastro_redesim: todas inconsistências selecionadas (SEM INCONSISTÊNCIAS, NÃO TRATADAS, EM TRATAMENTO, LIBERADAS, NÃO LIBERADAS)"
        )
        await page.wait_for_timeout(MINIMAL_DELAY)  # Minimal delay after select

        # Clicar no botão >> para mover para Selecionadas
        # Guia: document.querySelector("body > table > tbody > tr:nth-child(2) > td > form > table > tbody > tr:nth-child(19) > td > table > tbody > tr.tdPadrao > td.tdPadrao > input:nth-child(1)")
        mover_btn_selectors = [
            "body > table > tbody > tr:nth-child(2) > td > form > table > tbody > tr:nth-child(19) > td > table > tbody > tr.tdPadrao > td.tdPadrao > input:nth-child(1)",
            "table:has-text('Situação do conjunto de Inconsistências') input[type='button'][value='>>']",
            "input[type='button'][value='>>']",
        ]

        mover_btn = None
        for sel in mover_btn_selectors:
            try:
                mover_btn = context.locator(sel).first
                await mover_btn.wait_for(timeout=5000)
                break
            except Exception:
                continue

        if not mover_btn:
            raise RuntimeError("Botão >> (mover Inconsistências) não encontrado")

        await mover_btn.click()
        logger.info("cadastro_redesim: inconsistências movidas para Selecionadas")
        await page.wait_for_timeout(FAST_CLICK_DELAY)  # Optimized click delay

        # Atualizar hidden field
        try:
            await page.evaluate(
                """
                () => {
                    const frm = document.forms['frmConsultarPendeciaProc'];
                    if (frm && frm.hidSitIncoSel) {
                        frm.hidSitIncoSel.value = 'SEM INCONSISTÊNCIAS#-1¨NÃO TRATADAS#1¨EM TRATAMENTO#2¨LIBERADAS#3¨NÃO LIBERADAS#4¨';
                    }
                }
                """
            )
        except Exception:
            pass
    except Exception as e:
        logger.warning(f"cadastro_redesim: erro ao selecionar inconsistências: {e}")


async def _fill_elemento_organizacional(context: FormContext, page: Page) -> None:
    """Preenche código do elemento organizacional e aciona Pesquisar."""
    code_value = "90102008"

    # Guia: document.querySelector("body > table > tbody > tr:nth-child(2) > td > form > table > tbody > tr:nth-child(21) > td > table > tbody > tr:nth-child(2) > td > input[type=hidden]:nth-child(2)")
    # Hidden field: <input type="hidden" name="hidcdSefincmpEleOrg" value="90102008">

    # Primeiro, setar o hidden field via JavaScript
    try:
        await page.evaluate(
            """(codeVal) => {
                const frm = document.forms['frmConsultarPendeciaProc'];
                if (!frm) return;
                if (frm.hidcdSefincmpEleOrg) frm.hidcdSefincmpEleOrg.value = codeVal;
                if (frm.hidsgElementoOrgcmpEleOrg) frm.hidsgElementoOrgcmpEleOrg.value = codeVal;
            }""",
            code_value,
        )
        logger.info("cadastro_redesim: elemento org setado via hidden fields")
    except Exception as e:
        logger.warning(f"cadastro_redesim: erro ao setar hidden field: {e}")

    # Tentar preencher campo visível também (se existir)
    code_selectors = (
        "input[name*='CodOrgao' i]",
        "input[id*='CodOrgao' i]",
        "input[name*='CodigoElemento' i]",
        "input[name*='Código' i]",
    )

    filled = False
    for selector in code_selectors:
        try:
            field = context.locator(selector).first
            await field.wait_for(timeout=5000)
            await field.fill(code_value)
            filled = True
            logger.info(
                "cadastro_redesim: elemento org preenchido no campo visível: %s",
                code_value,
            )
            # Removed delay - element is ready after wait_for
            break
        except Exception:
            continue

    # Tentar no iframe cmpEleOrg se existir
    if not filled:
        try:
            # Buscar frame por nome (case-insensitive)
            cmp_frame = None
            for frame in page.frames:
                if frame.name and "cmpEleOrg" in frame.name.lower():
                    cmp_frame = frame
                    break

            if cmp_frame:
                for selector in ("input[type='text']", *code_selectors):
                    try:
                        field = cmp_frame.locator(selector).first
                        await field.wait_for(timeout=5000)
                        await field.fill(code_value)
                        filled = True
                        logger.info(
                            "cadastro_redesim: elemento org preenchido no iframe: %s",
                            code_value,
                        )
                        # Removed delay - element is ready after wait_for
                        break
                    except Exception:
                        continue
        except Exception:
            pass

    # Clicar no botão Pesquisar
    # Guia: document.querySelector("#Layer1 > table > tbody > tr > td > form > table > tbody > tr:nth-child(1) > td:nth-child(3) > input")
    search_btn_selectors = [
        "#Layer1 > table > tbody > tr > td > form > table > tbody > tr:nth-child(1) > td:nth-child(3) > input",
        "input[type='button'][value*='Pesquisar' i]",
        "input[type='submit'][value*='Pesquisar' i]",
        "button:has-text('Pesquisar')",
        "input[name='btnPesquisar']",
    ]

    pesquisar_clicked = False
    for btn_sel in search_btn_selectors:
        try:
            # Tentar no contexto principal
            btn = context.locator(btn_sel).first
            await btn.wait_for(timeout=5000)
            await btn.click()
            pesquisar_clicked = True
            logger.info(
                "cadastro_redesim: botão Pesquisar acionado via selector: %s", btn_sel
            )
            await page.wait_for_timeout(FAST_CLICK_DELAY)  # Optimized click delay
            break
        except Exception:
            continue

    # Tentar no iframe se não encontrou
    if not pesquisar_clicked:
        try:
            # Buscar frame por nome (case-insensitive)
            cmp_frame = None
            for frame in page.frames:
                if frame.name and "cmpEleOrg" in frame.name.lower():
                    cmp_frame = frame
                    break

            if cmp_frame:
                for btn_sel in search_btn_selectors:
                    try:
                        btn = cmp_frame.locator(btn_sel).first
                        await btn.wait_for(timeout=5000)
                        await btn.click()
                        pesquisar_clicked = True
                        logger.info(
                            "cadastro_redesim: botão Pesquisar acionado no iframe"
                        )
                        await page.wait_for_timeout(
                            FAST_CLICK_DELAY
                        )  # Optimized click delay
                        break
                    except Exception:
                        continue
        except Exception:
            pass

    if not pesquisar_clicked:
        logger.warning(
            "cadastro_redesim: botão Pesquisar não encontrado, mas hidden field foi setado"
        )

    # Aguardar um pouco após pesquisar (reduced delay)
    await page.wait_for_timeout(FAST_SEARCH_DELAY)  # Optimized search delay


async def _wait_user_creation_dates(
    context: FormContext, page: Page
) -> tuple[str, str]:
    """Espera o usuário digitar datas de criação (início/fim)."""
    start_selectors = (
        "input[name*='DtCriacaoProcInicio' i]",
        "input[name*='DtCriacaoProInicio' i]",
        "input[name*='CriacaoProcInicio' i]",
        "input[name*='CriacaoProInicio' i]",
        "input[name*='DtInicio' i]",
    )
    end_selectors = (
        "input[name*='DtCriacaoProcFim' i]",
        "input[name*='DtCriacaoProFim' i]",
        "input[name*='CriacaoProcFim' i]",
        "input[name*='CriacaoProFim' i]",
        "input[name*='DtFim' i]",
    )

    def _first_existing(selectors: Sequence[str]) -> Locator | None:
        for sel in selectors:
            loc = context.locator(sel).first
            try:
                if loc:
                    return loc
            except Exception:
                continue
        return None

    start_field = _first_existing(start_selectors)
    end_field = _first_existing(end_selectors)

    if start_field is None or end_field is None:
        raise RuntimeError("Campos de data de criação não encontrados.")

    await start_field.wait_for(timeout=ELEMENT_TIMEOUT)  # Optimized timeout
    await end_field.wait_for(timeout=ELEMENT_TIMEOUT)  # Optimized timeout

    # Dar foco para abrir o calendário e sinalizar ao usuário
    try:
        await start_field.click()
        await page.wait_for_timeout(300)
        await end_field.click()
    except Exception:
        pass

    logger.info(
        "cadastro_redesim: aguardando o usuário digitar datas de criação (início e fim)"
    )

    deadline = time.monotonic() + 600.0  # até 10 minutos
    last_logged = time.monotonic()

    while time.monotonic() < deadline:
        try:
            start_val = (await start_field.input_value()).strip()
            end_val = (await end_field.input_value()).strip()
        except Exception:
            start_val = ""
            end_val = ""

        if _is_valid_date(start_val) and _is_valid_date(end_val):
            logger.info(
                "cadastro_redesim: datas fornecidas pelo usuário: %s -> %s",
                start_val,
                end_val,
            )
            return start_val, end_val

        now = time.monotonic()
        if now - last_logged > 30:
            logger.info(
                "cadastro_redesim: aguardando datas... valores atuais start='%s' end='%s'",
                start_val,
                end_val,
            )
            last_logged = now

        await page.wait_for_timeout(500)

    raise RuntimeError("Tempo excedido aguardando datas de criação.")


async def _click_consultar(context: FormContext, page: Page) -> None:
    """Click the Consultar trigger using stable selectors."""
    # Guia: document.querySelector("body > table > tbody > tr:nth-child(2) > td > form > table > tbody > tr:nth-child(24) > td > input:nth-child(3)")
    consult_btn_selectors = [
        "body > table > tbody > tr:nth-child(2) > td > form > table > tbody > tr:nth-child(24) > td > input:nth-child(3)",
        "input[type='submit'][value*='Consultar' i]",
        "button[name*='Consultar' i]",
        "input[value='Consultar']",
        "a:has-text('Consultar')",
    ]

    consult_locator: Locator | None = None

    # Tentar selector específico do guia primeiro
    for selector in consult_btn_selectors:
        try:
            consult_locator = context.locator(selector).first
            await consult_locator.wait_for(timeout=ELEMENT_TIMEOUT)  # Optimized timeout
            logger.info(
                "cadastro_redesim: botão Consultar encontrado via selector '%s'",
                selector,
            )
            break
        except Exception:
            continue

    # Fallback: tentar por role/text
    if consult_locator is None:
        try:
            consult_locator = context.get_by_role(
                "button",
                name=re.compile("Consultar", re.IGNORECASE),
            ).first
            await consult_locator.wait_for(timeout=ELEMENT_TIMEOUT)  # Optimized timeout
            logger.info("cadastro_redesim: botão Consultar encontrado via role")
        except Exception:
            pass

    if consult_locator is None:
        raise RuntimeError("Consultar button not available on REDESIM form.")

    # Click without waiting for navigation timeout (page may take time to load results)
    try:
        # Use click with no_wait_after to avoid navigation timeout
        await consult_locator.click(no_wait_after=True, timeout=ELEMENT_TIMEOUT)
        logger.info("cadastro_redesim: botão Consultar clicado")
    except TypeError:
        # no_wait_after might not be available in this Playwright version, use regular click
        try:
            await consult_locator.click(timeout=ELEMENT_TIMEOUT)
            logger.info("cadastro_redesim: botão Consultar clicado (fallback)")
        except Exception as click_err:
            # If timeout waiting for navigation, that's OK - the click happened
            if "Timeout" in str(click_err) and "navigations" in str(click_err):
                logger.info(
                    "cadastro_redesim: botão Consultar clicado (navegação em andamento)"
                )
            else:
                raise
    except Exception as click_err:
        # If timeout waiting for navigation, that's OK - the click happened
        if "Timeout" in str(click_err) and "navigations" in str(click_err):
            logger.info(
                "cadastro_redesim: botão Consultar clicado (navegação em andamento)"
            )
        else:
            raise

    await page.wait_for_timeout(FAST_CLICK_DELAY)  # Small delay after click


async def _wait_for_results(page: Page, context: FormContext) -> None:
    """Wait for the results view to stabilize."""
    await _wait_network_idle(page)
    await page.wait_for_timeout(FAST_SEARCH_DELAY)  # Optimized search delay

    for target in (context, page):
        for selector in _RESULT_HINTS:
            try:
                await target.locator(selector).first.wait_for(
                    timeout=NETWORK_IDLE_TIMEOUT
                )
                logger.info(
                    "cadastro_redesim: results detected via %s",
                    selector,
                )
                return
            except Exception:
                continue

    logger.debug("cadastro_redesim: results hints not detected, proceeding anyway")


async def consultar_redesim(
    page: Page,
    payload: Mapping[str, Any],
    wait_user_dates: bool = False,
) -> Page:
    """Consult REDESIM processes using an already authenticated ATF page.

    Args:
        page: Playwright Page instance **already logged in** via perform_login.
        payload: Mapping containing only dynamic values to populate, e.g.:
            - processo_serpb: Process number (string)
            - protocolo: Protocol number (string)
            - cnpj: Company CNPJ (string)
            - inscricao_estadual: State registration (string)
            - natureza_solicitacao: Select value for nature of request
            - data_criacao_inicio / data_criacao_fim: Date range (dd/mm/yyyy)
            - data_evento_inicio / data_evento_fim: Date range (dd/mm/yyyy)
        wait_user_dates: When True, pausa até o usuário preencher datas de criação.
            Quando False (default), usa intervalo padrão 10/12/2025-17/12/2025
            caso não venha no payload.

    Returns:
        The same Page instance, positioned on the results view.

    Raises:
        ValueError: If the page is missing or payload is invalid.
        RuntimeError: If mandatory elements (form/button) cannot be located.
    """

    if page is None:
        raise ValueError("consultar_redesim requires a valid Playwright page.")

    data = dict(payload or {})
    logger.info("cadastro_redesim: starting consultation with authenticated session")

    # 1) Force navigation to the canonical consultation URL using the same session
    if _is_page_closed(page):
        raise RuntimeError("Page was closed before navigation")

    await page.goto(
        REDESIM_CONSULT_URL,
        wait_until="domcontentloaded",
        timeout=FAST_TIMEOUT,  # Optimized timeout
    )

    if _is_page_closed(page):
        raise RuntimeError("Page was closed after navigation")

    await _wait_network_idle(page)

    if _is_page_closed(page):
        raise RuntimeError("Page was closed during network idle wait")

    await page.wait_for_timeout(FAST_DEFAULT_DELAY)  # Optimized default delay

    # 2) Detect consultation form (legacy table-based HTML)
    context = await _resolve_form_context(page)
    await page.wait_for_timeout(FAST_DEFAULT_DELAY)  # Optimized default delay

    # 3) Populate fields only when provided in payload
    await _fill_field(
        context,
        page,
        data.get("processo_serpb") or data.get("processo"),
        labels=["Processo SER-PB", "Processo REDESIM", "Processo"],
        selectors=[
            "input[name*='ProcessoSER' i]",
            "input[name*='ProcessoRedesim' i]",
            "input[name*='Processo' i]",
        ],
        field_name="processo_serpb",
    )

    await _fill_field(
        context,
        page,
        data.get("protocolo"),
        labels=["Protocolo REDESIM", "Protocolo"],
        selectors=[
            "input[name*='ProtocoloRedesim' i]",
            "input[name*='Protocolo' i]",
        ],
        field_name="protocolo",
    )

    await _fill_field(
        context,
        page,
        data.get("cpf_cnpj") or data.get("cnpj"),
        labels=["CPF/CNPJ", "CNPJ"],
        selectors=[
            "input[name*='CPF' i]",
            "input[name*='CNPJ' i]",
            "input[name*='CpfCnpj' i]",
        ],
        field_name="cpf_cnpj",
    )

    await _fill_field(
        context,
        page,
        data.get("inscricao_estadual"),
        labels=["Inscrição Estadual", "Inscricao Estadual"],
        selectors=[
            "input[name*='InscricaoEstadual' i]",
            "input[id*='InscricaoEstadual' i]",
        ],
        field_name="inscricao_estadual",
    )

    # Natureza: força CADASTRAMENTO quando não vier
    natureza_val = data.get("natureza_solicitacao") or "CADASTRAMENTO"
    try:
        await _fill_field(
            context,
            page,
            natureza_val,
            labels=["Natureza da Solicitação", "Operação"],
            selectors=[
                "select[name*='cmbOperacao' i]",
                "select[name*='Operacao' i]",
            ],
            field_name="natureza_solicitacao",
        )
    except Exception:
        logger.info(
            "cadastro_redesim: natureza via _fill_field não encontrada, "
            "seguindo para _ensure_natureza_cadastramento()"
        )

    await _fill_field(
        context,
        page,
        data.get("data_evento_inicio"),
        labels=["Data de Evento", "Data do Evento (início)"],
        selectors=[
            "input[name*='DtEventoInicio' i]",
            "input[name*='EventoInicio' i]",
        ],
        field_name="data_evento_inicio",
    )

    await _fill_field(
        context,
        page,
        data.get("data_evento_fim"),
        labels=["Data de Evento", "Data do Evento (fim)"],
        selectors=[
            "input[name*='DtEventoFim' i]",
            "input[name*='EventoFim' i]",
        ],
        field_name="data_evento_fim",
    )

    # Datas de criação: usar selectors específicos do guia
    # Guia: document.querySelector("body > table > tbody > tr:nth-child(2) > td > form > table > tbody > tr:nth-child(12) > td:nth-child(2) > input:nth-child(1)")
    # <input type="text" name="edtDtCriacaoProInicio" ...>
    # <input type="text" name="edtDtCriacaoProFim" ...>
    data_inicio = (
        data.get("data_criacao_inicio")
        or data.get("data_inicio")
        or DEFAULT_CRIACAO_INICIO
    )
    data_fim = (
        data.get("data_criacao_fim") or data.get("data_fim") or DEFAULT_CRIACAO_FIM
    )

    inicio_selectors = [
        "input[name='edtDtCriacaoProInicio']",
        "body > table > tbody > tr:nth-child(2) > td > form > table > tbody > tr:nth-child(12) > td:nth-child(2) > input:nth-child(1)",
        "input[name*='DtCriacaoProcInicio' i]",
        "input[name*='DtCriacaoProInicio' i]",
        "input[name*='CriacaoProcInicio' i]",
        "input[name*='CriacaoProInicio' i]",
    ]

    fim_selectors = [
        "input[name='edtDtCriacaoProFim']",
        "input[name*='DtCriacaoProcFim' i]",
        "input[name*='DtCriacaoProFim' i]",
        "input[name*='CriacaoProcFim' i]",
        "input[name*='CriacaoProFim' i]",
    ]

    # Preencher data início
    inicio_filled = False
    for sel in inicio_selectors:
        try:
            field = context.locator(sel).first
            await field.wait_for(timeout=5000)
            await field.fill(data_inicio)
            inicio_filled = True
            logger.info(
                "cadastro_redesim: data_criacao_inicio preenchida: %s", data_inicio
            )
            # Removed delay - element is ready after wait_for
            break
        except Exception:
            continue

    if not inicio_filled:
        logger.warning("cadastro_redesim: campo data_criacao_inicio não encontrado")

    # Preencher data fim
    fim_filled = False
    for sel in fim_selectors:
        try:
            field = context.locator(sel).first
            await field.wait_for(timeout=5000)
            await field.fill(data_fim)
            fim_filled = True
            logger.info("cadastro_redesim: data_criacao_fim preenchida: %s", data_fim)
            # Removed delay - element is ready after wait_for
            break
        except Exception:
            continue

    if not fim_filled:
        logger.warning("cadastro_redesim: campo data_criacao_fim não encontrado")

    # Passos fixos: natureza, situação DEFERIDO, inconsistências, elemento org, checkbox
    await _ensure_natureza_cadastramento(context, page)
    await _ensure_situacao_processo_deferido(context, page)
    await _select_all_inconsistencias(context, page)
    await _fill_elemento_organizacional(context, page)
    await _check_listar_outros_processos(context, page)

    # Se pedido, aguardar usuário escolher datas de criação (senão usamos defaults)
    if wait_user_dates:
        await _wait_user_creation_dates(context, page)

    # 4) Submit the consultation and wait for results
    await _click_consultar(context, page)
    await _wait_for_results(page, context)

    logger.info(
        "cadastro_redesim: consultation submitted; current URL: %s",
        page.url,
    )
    return page


# ============================================================================
# Stage 2: Post-consulta automation (List selection, CEP/CFC validation, Gmail drafts)
# ============================================================================

# State persistence for deterministic iteration
STATE_FILE_PATH = Path("/Volumes/MICRO/ATF/REDESIM/state.json")


def _load_iteration_state() -> dict[str, Any]:
    """Load iteration state from persistent file.
    
    Returns:
        Dictionary with current_index, total, and last_processed_value
        Defaults to {"current_index": 0, "total": None, "last_processed_value": None}
    """
    try:
        if STATE_FILE_PATH.exists():
            with open(STATE_FILE_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
                logger.info(
                    "cadastro_redesim: Loaded state: current_index=%s, total=%s, last_value=%s",
                    state.get("current_index", 0),
                    state.get("total"),
                    state.get("last_processed_value"),
                )
                return state
    except Exception as e:
        logger.warning(f"cadastro_redesim: Error loading state file: {e}")
    
    # Return default state
    default_state = {
        "current_index": 0,
        "total": None,
        "last_processed_value": None,
    }
    logger.info("cadastro_redesim: Using default state (no file found)")
    return default_state


def _save_iteration_state(state: dict[str, Any]) -> None:
    """Save iteration state to persistent file.
    
    Args:
        state: Dictionary with current_index, total, and last_processed_value
    """
    try:
        # Ensure directory exists
        STATE_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Save state
        with open(STATE_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        
        logger.info(
            "cadastro_redesim: Saved state: current_index=%s, total=%s, last_value=%s",
            state.get("current_index"),
            state.get("total"),
            state.get("last_processed_value"),
        )
    except Exception as e:
        logger.error(f"cadastro_redesim: Error saving state file: {e}", exc_info=True)


async def _resolve_principal_iframe(page: Page, timeout: int = FAST_TIMEOUT) -> Frame:
    """Resolve the 'principal' iframe explicitly.
    
    This is MANDATORY because the radio buttons are inside this iframe.
    The iframe MUST be resolved before accessing any elements within it.
    
    Args:
        page: Playwright Page instance
        timeout: Timeout in milliseconds
        
    Returns:
        Frame instance for the 'principal' iframe
        
    Raises:
        RuntimeError: If iframe 'principal' is not found
    """
    logger.info("cadastro_redesim: Resolving iframe 'principal' explicitly...")
    
    # Method 1: Wait for iframe element to exist in DOM first
    try:
        logger.info("cadastro_redesim: Waiting for iframe element in DOM...")
        await page.wait_for_selector('iframe[name="principal"]', timeout=timeout, state="attached")
        logger.info("cadastro_redesim: Iframe element found in DOM")
    except Exception as e:
        logger.warning(f"cadastro_redesim: Iframe element wait failed: {e}")
        # Try alternative selectors
        try:
            await page.wait_for_selector('iframe[id*="principal" i], iframe[src*="principal" i]', timeout=timeout // 2, state="attached")
            logger.info("cadastro_redesim: Found iframe by id/src containing 'principal'")
        except Exception:
            pass
    
    # Method 2: Try to get frame by name directly
    try:
        frame = page.frame(name="principal")
        if frame:
            logger.info("cadastro_redesim: Found iframe 'principal' by name")
            return frame
    except Exception as e:
        logger.debug(f"cadastro_redesim: Direct frame lookup failed: {e}")
    
    # Method 3: Search through all frames with extended timeout
    deadline = time.monotonic() + (timeout / 1000.0)
    iteration = 0
    while time.monotonic() < deadline:
        iteration += 1
        all_frames = list(page.frames)
        frame_names = [f.name for f in all_frames if f.name]
        frame_urls = [f.url for f in all_frames]
        
        if iteration == 1 or iteration % 10 == 0:
            logger.info(
                f"cadastro_redesim: Checking frames (iteration {iteration}): "
                f"names={frame_names}, count={len(all_frames)}"
            )
        
        for frame in all_frames:
            # Check frame name exactly
            if frame.name == "principal":
                logger.info("cadastro_redesim: Found iframe 'principal' by iteration")
                return frame
            
            # Also check if name contains 'principal' (case-insensitive fallback)
            if frame.name and "principal" in frame.name.lower():
                logger.info(
                    "cadastro_redesim: Found iframe with 'principal' in name: %s",
                    frame.name,
                )
                return frame
            
            # Check if frame URL contains 'principal' or 'REDESIM'
            if frame.url and ("principal" in frame.url.lower() or "redesim" in frame.url.lower()):
                logger.info(
                    "cadastro_redesim: Found iframe with relevant URL: %s (name: %s)",
                    frame.url,
                    frame.name or "unnamed",
                )
                # Verify it has radio buttons before returning
                try:
                    radio_test = frame.locator("input[type='radio'][name='rdbChavePrimaria']").first
                    await radio_test.wait_for(timeout=2000, state="attached")
                    logger.info("cadastro_redesim: Verified iframe contains radio buttons")
                    return frame
                except Exception:
                    logger.debug("cadastro_redesim: Frame URL matches but no radio buttons found")
                    continue
        
        await page.wait_for_timeout(300)  # Wait 300ms before retry
    
    # Final attempt 1: Try to find ANY iframe and check if it has radio buttons
    logger.warning("cadastro_redesim: Standard methods failed, trying fallback: check all iframes for radio buttons")
    for frame in page.frames:
        if frame == page.main_frame:
            continue  # Skip main frame
        try:
            radio_test = frame.locator("input[type='radio'][name='rdbChavePrimaria']").first
            await radio_test.wait_for(timeout=1000, state="attached")
            logger.info(f"cadastro_redesim: Found iframe with radio buttons (name: {frame.name or 'unnamed'}, URL: {frame.url})")
            return frame
        except Exception:
            continue
    
    # Final attempt 2: Use JavaScript to find iframe in DOM and wait for it to load
    logger.warning("cadastro_redesim: Trying JavaScript-based iframe detection...")
    try:
        # Check if iframe exists in DOM
        iframe_info = await page.evaluate("""
            () => {
                const iframes = Array.from(document.querySelectorAll('iframe'));
                return iframes.map(iframe => ({
                    name: iframe.name || null,
                    id: iframe.id || null,
                    src: iframe.src || null,
                    hasName: iframe.name === 'principal' || iframe.name?.toLowerCase().includes('principal')
                }));
            }
        """)
        logger.info(f"cadastro_redesim: Found {len(iframe_info)} iframe(s) in DOM: {iframe_info}")
        
        # Wait a bit more for frames to register with Playwright
        await page.wait_for_timeout(2000)
        
        # Try again after JS detection
        for frame in page.frames:
            if frame == page.main_frame:
                continue
            try:
                radio_test = frame.locator("input[type='radio'][name='rdbChavePrimaria']").first
                await radio_test.wait_for(timeout=2000, state="attached")
                logger.info(f"cadastro_redesim: Found iframe with radio buttons after JS detection (name: {frame.name or 'unnamed'}, URL: {frame.url})")
                return frame
            except Exception:
                continue
    except Exception as js_err:
        logger.warning(f"cadastro_redesim: JavaScript detection failed: {js_err}")
    
    # If not found, raise explicit error with detailed info
    all_frame_info = []
    for f in page.frames:
        info = f"name='{f.name or 'unnamed'}'"
        if f.url:
            info += f", url='{f.url[:100]}...'"
        all_frame_info.append(info)
    
    error_msg = (
        f"Iframe 'principal' not found within {timeout}ms timeout. "
        f"Available frames ({len(page.frames)}): {all_frame_info}"
    )
    logger.error(f"cadastro_redesim: {error_msg}")
    raise RuntimeError(error_msg)


async def _wait_for_hidden_field_sync(
    frame: Frame, expected_value: str, timeout: int = ELEMENT_TIMEOUT
) -> bool:
    """Wait for hidden field hidNrProcesso to be updated after radio click.
    
    CRITICAL: The system does NOT use .checked state when submitting.
    It uses hidden fields (hidNrProcesso) which are ONLY updated by defineCamposHid()
    when a real click event occurs.
    
    This function polls the hidden field until it matches the expected radio value,
    ensuring state synchronization before form submission.
    
    Args:
        frame: Playwright Frame instance (the 'principal' iframe)
        expected_value: Expected value for hidNrProcesso (should match radio.value)
        timeout: Maximum time to wait in milliseconds
        
    Returns:
        True if hidden field was synchronized, False if timeout
    """
    logger.info(
        "cadastro_redesim: Waiting for hidNrProcesso to equal '%s' (timeout=%dms)",
        expected_value,
        timeout,
    )
    
    deadline = time.monotonic() + (timeout / 1000.0)
    poll_interval = 100  # Check every 100ms
    iteration = 0
    
    while time.monotonic() < deadline:
        iteration += 1
        try:
            # Re-query the form and hidden field (never reuse stale references)
            form = frame.locator('form[name="frmListagemPendeciaProc"]').first
            hidden_field = form.locator('input[name="hidNrProcesso"]').first
            
            # Check if hidden field exists and get its value
            if await hidden_field.count() > 0:
                current_value = await hidden_field.get_attribute("value") or ""
                current_value = current_value.strip()
                
                if current_value == expected_value:
                    logger.info(
                        "cadastro_redesim: Hidden field synchronized after %d iterations (%dms)",
                        iteration,
                        int((time.monotonic() - (deadline - timeout / 1000.0)) * 1000),
                    )
                    return True
                
                # Log progress every 10 iterations
                if iteration % 10 == 0:
                    logger.debug(
                        "cadastro_redesim: Waiting for sync... current='%s', expected='%s'",
                        current_value,
                        expected_value,
                    )
            else:
                # Form or hidden field not found yet
                if iteration % 10 == 0:
                    logger.debug(
                        "cadastro_redesim: Form or hidden field not found yet (iteration %d)",
                        iteration,
                    )
        except Exception as e:
            # Log error but continue polling
            if iteration % 10 == 0:
                logger.debug(f"cadastro_redesim: Error checking hidden field: {e}")
        
        await asyncio.sleep(poll_interval / 1000.0)
    
    # Timeout - check final state for debugging
    try:
        form = frame.locator('form[name="frmListagemPendeciaProc"]').first
        hidden_field = form.locator('input[name="hidNrProcesso"]').first
        if await hidden_field.count() > 0:
            final_value = await hidden_field.get_attribute("value") or ""
            logger.error(
                "cadastro_redesim: Hidden field sync timeout. Final value='%s', expected='%s'",
                final_value,
                expected_value,
            )
        else:
            logger.error(
                "cadastro_redesim: Hidden field sync timeout. Form or hidden field not found."
            )
    except Exception as e:
        logger.error(f"cadastro_redesim: Error checking final state: {e}")
    
    return False


async def _collect_radio_buttons_from_iframe(frame: Frame) -> list[Locator]:
    """Collect all radio buttons from the iframe using index-based approach.
    
    CRITICAL: This function MUST be called AFTER every iframe reload.
    Never reuse radio button references after navigation - they become stale.
    
    This function collects ALL radio buttons ONCE per page load.
    It does NOT rely on scroll position, visibility, or timing.
    The order is assumed to be STABLE.
    
    Args:
        frame: Playwright Frame instance (the 'principal' iframe)
        MUST be freshly resolved - never reuse stale frame references
        
    Returns:
        List of Locator objects for each radio button, in order
        
    Raises:
        RuntimeError: If no radio buttons are found
    """
    logger.info("cadastro_redesim: Collecting radio buttons from iframe (FRESH QUERY)...")
    
    # CRITICAL: Always query fresh - never reuse stale locators
    # Use explicit selector for radio buttons
    radio_locator = frame.locator("input[type='radio'][name='rdbChavePrimaria']")
    
    # Wait for at least one radio button to appear
    try:
        await radio_locator.first.wait_for(timeout=ELEMENT_TIMEOUT, state="attached")
    except Exception as e:
        error_msg = f"No radio buttons found in iframe 'principal': {e}"
        logger.error(f"cadastro_redesim: {error_msg}")
        raise RuntimeError(error_msg)
    
    # Count total radio buttons (fresh count, never cached)
    total_count = await radio_locator.count()
    
    if total_count == 0:
        error_msg = "Radio buttons count is 0 after wait"
        logger.error(f"cadastro_redesim: {error_msg}")
        raise RuntimeError(error_msg)
    
    logger.info(
        "cadastro_redesim: Collected %d radio button(s) from iframe 'principal' (fresh query)",
        total_count,
    )
    
    # Return list of locators (index-based, deterministic)
    # Each locator is fresh and scoped to the current iframe state
    radios = []
    for i in range(total_count):
        radios.append(radio_locator.nth(i))
    
    return radios


async def _find_frame_by_name_or_src(
    page: Page, frame_name: str, timeout: int = FAST_TIMEOUT
) -> Frame | None:
    """Locate a frame by name or src attribute containing the target string.

    Args:
        page: Playwright Page instance
        frame_name: Frame name or partial src to search for (case-insensitive)
        timeout: Timeout in milliseconds

    Returns:
        Frame if found, None otherwise
    """
    deadline = time.monotonic() + (timeout / 1000.0)
    frame_name_lower = frame_name.lower()

    while time.monotonic() < deadline:
        for frame in page.frames:
            # Check frame name
            if frame.name and frame_name_lower in frame.name.lower():
                logger.info(
                    "cadastro_redesim: found frame '%s' by name: %s",
                    frame_name,
                    frame.name,
                )
                return frame

            # Check frame URL/src
            try:
                frame_url = frame.url
                if frame_url and frame_name_lower in frame_url.lower():
                    logger.info(
                        "cadastro_redesim: found frame '%s' by URL: %s",
                        frame_name,
                        frame_url,
                    )
                    return frame
            except Exception:
                continue

        await page.wait_for_timeout(200)  # Wait 200ms before retry

    logger.warning("cadastro_redesim: frame '%s' not found within timeout", frame_name)
    return None


async def _select_list_checkbox_and_submit(
    page: Page, frame_lista: Frame | None = None, row_index: int = 0
) -> bool:
    """Select checkbox in LISTA frame and submit via Enter.

    Args:
        page: Playwright Page instance
        frame_lista: Optional LISTA frame (will be located if None)
        row_index: Index of row to select (default: 0 = first row)

    Returns:
        True if successful, False otherwise
    """
    try:
        # Locate LISTA frame if not provided
        if frame_lista is None:
            frame_lista = await _find_frame_by_name_or_src(page, "LISTA")
            if frame_lista is None:
                logger.error("cadastro_redesim: LISTA frame not found")
                return False

        # Wait for frame to be ready
        await frame_lista.wait_for_load_state("domcontentloaded", timeout=FAST_TIMEOUT)

        # Find checkboxes (radio buttons with name='rdbChavePrimaria')
        checkbox_selectors = [
            "input[name='rdbChavePrimaria']",
            "input[type='radio'][name='rdbChavePrimaria']",
            "input[type='radio']",
        ]

        checkbox = None
        for selector in checkbox_selectors:
            try:
                checkbox_locator = frame_lista.locator(selector)
                count = await checkbox_locator.count()
                if count > 0:
                    # Select the checkbox at row_index
                    index = min(row_index, count - 1)
                    checkbox = checkbox_locator.nth(index)
                    await checkbox.wait_for(timeout=ELEMENT_TIMEOUT)
                    break
            except Exception:
                continue

        if checkbox is None:
            logger.error("cadastro_redesim: checkbox not found in LISTA frame")
            return False

        # Click the checkbox
        await checkbox.click()
        logger.info("cadastro_redesim: checkbox selected in LISTA frame")
        await page.wait_for_timeout(FAST_CLICK_DELAY)

        # Submit via Enter key (simulate Enter press on the form)
        try:
            # Try to find the form and submit it
            form = frame_lista.locator("form").first
            await form.press("Enter")
            logger.info("cadastro_redesim: form submitted via Enter key")
        except Exception:
            # Fallback: try clicking a submit button
            submit_selectors = [
                "input[type='submit'][value*='Detalhar' i]",
                "input[type='submit']",
                "button[type='submit']",
            ]
            for sel in submit_selectors:
                try:
                    submit_btn = frame_lista.locator(sel).first
                    await submit_btn.wait_for(timeout=ELEMENT_TIMEOUT)
                    await submit_btn.click()
                    logger.info("cadastro_redesim: form submitted via button")
                    break
                except Exception:
                    continue

        await page.wait_for_timeout(FAST_SEARCH_DELAY)
        return True

    except Exception as e:
        logger.exception(
            f"cadastro_redesim: error selecting checkbox and submitting: {e}"
        )
        return False


async def _validate_cep_viacep(cep: str) -> dict[str, Any]:
    """Validate CEP using ViaCEP API.

    Args:
        cep: CEP string (with or without formatting)

    Returns:
        Dictionary with validation result and address data
    """
    # Clean CEP (remove formatting)
    cep_clean = re.sub(r"[^\d]", "", cep)

    if len(cep_clean) != 8:
        return {
            "valid": False,
            "error": f"CEP inválido: formato incorreto (esperado 8 dígitos, recebido {len(cep_clean)})",
            "cep": cep,
        }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"https://viacep.com.br/ws/{cep_clean}/json/"
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            # ViaCEP returns {"erro": true} for invalid CEPs
            if data.get("erro"):
                return {
                    "valid": False,
                    "error": "CEP não encontrado na base ViaCEP",
                    "cep": cep,
                }

            return {
                "valid": True,
                "cep": data.get("cep", cep_clean),
                "logradouro": data.get("logradouro", ""),
                "complemento": data.get("complemento", ""),
                "bairro": data.get("bairro", ""),
                "localidade": data.get("localidade", ""),
                "uf": data.get("uf", ""),
                "ibge": data.get("ibge", ""),
                "gia": data.get("gia", ""),
                "ddd": data.get("ddd", ""),
                "siafi": data.get("siafi", ""),
            }

    except httpx.HTTPError as e:
        logger.exception(f"cadastro_redesim: HTTP error validating CEP: {e}")
        return {
            "valid": False,
            "error": f"Erro de conexão com ViaCEP: {str(e)}",
            "cep": cep,
        }
    except Exception as e:
        logger.exception(f"cadastro_redesim: error validating CEP: {e}")
        return {
            "valid": False,
            "error": f"Erro inesperado: {str(e)}",
            "cep": cep,
        }


async def _check_contabilista_cfc(cpf: str) -> dict[str, Any]:
    """Check contabilista regularity at CFC site using CPF.

    Queries https://www3.cfc.org.br/SPW/ConsultaNacionalCFC/cfc with the CPF.

    Args:
        cpf: CPF string (with or without formatting)

    Returns:
        Dictionary with CFC check result including regularity status
    """
    # Clean CPF (remove formatting)
    cpf_clean = re.sub(r"[^\d]", "", cpf)

    if len(cpf_clean) != 11:
        return {
            "valid": False,
            "error": f"CPF inválido: formato incorreto (esperado 11 dígitos, recebido {len(cpf_clean)})",
            "cpf": cpf,
        }

    try:
        # CFC consultation URL
        cfc_url = "https://www3.cfc.org.br/SPW/ConsultaNacionalCFC/cfc"

        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            # Try GET with CPF as query parameter first
            try:
                response = await client.get(
                    cfc_url,
                    params={"cpf": cpf_clean},
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                    },
                )
                response.raise_for_status()
                content = response.text

                # Check if response contains CPF or regularity indicators
                content_lower = content.lower()
                cpf_found = cpf_clean in content or cpf_clean in content_lower

                # Look for regularity indicators in the response
                regularity_indicators = {
                    "regular": ["regular", "ativo", "habilitado"],
                    "irregular": ["irregular", "suspenso", "cancelado", "inativo"],
                }

                regularity_status = "unknown"
                for status, keywords in regularity_indicators.items():
                    if any(keyword in content_lower for keyword in keywords):
                        regularity_status = status
                        break

                return {
                    "valid": True,
                    "cpf": cpf_clean,
                    "cfc_accessible": True,
                    "cpf_found": cpf_found,
                    "regularity_status": regularity_status,
                    "url": cfc_url,
                    "note": "CFC consultation performed. Regularity status may require manual verification.",
                }

            except httpx.HTTPError as get_err:
                logger.debug(
                    f"cadastro_redesim: GET request failed, trying POST: {get_err}"
                )
                # Fallback: try POST with form data
                try:
                    response = await client.post(
                        cfc_url,
                        data={"cpf": cpf_clean},
                        headers={
                            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                            "Content-Type": "application/x-www-form-urlencoded",
                        },
                    )
                    response.raise_for_status()
                    content = response.text
                    content_lower = content.lower()

                    return {
                        "valid": True,
                        "cpf": cpf_clean,
                        "cfc_accessible": True,
                        "cpf_found": cpf_clean in content_lower,
                        "regularity_status": "unknown",
                        "url": cfc_url,
                        "note": "CFC consultation performed via POST. Regularity status requires manual verification.",
                    }
                except Exception as post_err:
                    logger.warning(
                        f"cadastro_redesim: POST request also failed: {post_err}"
                    )
                    raise get_err  # Raise original error

    except httpx.HTTPError as e:
        logger.exception(f"cadastro_redesim: HTTP error checking CFC: {e}")
        return {
            "valid": False,
            "error": f"Erro de conexão com CFC: {str(e)}",
            "cpf": cpf,
        }
    except Exception as e:
        logger.exception(f"cadastro_redesim: error checking CFC: {e}")
        return {
            "valid": False,
            "error": f"Erro inesperado: {str(e)}",
            "cpf": cpf,
        }


async def _extract_emails_from_page(page: Page) -> list[str]:
    """Extract emails from the main detail page (no frames).
    
    Based on the HTML structure, emails are in td elements like:
    <td width="390">ssantos25m@gmail.com</td>
    <td width="390">diretor@phdsolucoescontabeis.com.br</td>
    
    Args:
        page: Playwright Page instance
        
    Returns:
        List of unique, filtered email addresses
    """
    emails: set[str] = set()
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

    # System email patterns to exclude
    system_email_patterns = [
        r"@sefaz\.pb\.gov\.br",
        r"cacgr1@sefaz\.pb\.gov\.br",
        r".*@.*sefaz.*",
    ]

    try:
        # Get all text content from the page
        text_content = await page.content()

        # Find emails in text
        found_emails = re.findall(email_pattern, text_content, re.IGNORECASE)
        emails.update(email.lower() for email in found_emails)

        # Check td elements that contain the "@" symbol (common email containers)
        email_tds = page.locator("td:has-text('@')")
        count = await email_tds.count()
        for i in range(count):
            try:
                text = await email_tds.nth(i).text_content()
                if text:
                    found = re.findall(email_pattern, text, re.IGNORECASE)
                    emails.update(email.lower() for email in found)
            except Exception:
                continue

        # Filter out common non-email patterns and system emails
        filtered_emails = []
        for email in emails:
            # Basic validation
            if (
                email.startswith("http")
                or "@" not in email
                or "." not in email.split("@")[1]
            ):
                continue

            # Filter out system emails
            is_system_email = any(
                re.search(pattern, email, re.IGNORECASE)
                for pattern in system_email_patterns
            )
            if is_system_email:
                logger.debug(f"cadastro_redesim: filtered out system email: {email}")
                continue

            filtered_emails.append(email)

        if filtered_emails:
            logger.info(
                "cadastro_redesim: extracted %d unique email(s) from page: %s",
                len(filtered_emails),
                ", ".join(filtered_emails[:3])
                + ("..." if len(filtered_emails) > 3 else ""),
            )
        else:
            logger.warning(
                "cadastro_redesim: no valid emails extracted from page. "
                "Total raw email candidates found: %d",
                len(emails),
            )
        return sorted(filtered_emails)

    except Exception as e:
        logger.exception(f"cadastro_redesim: error extracting emails from page: {e}")
        return []


async def _extract_process_data_from_page(page: Page) -> dict[str, str]:
    """Extract process number and razão social from the main detail page.
    
    Based on the HTML structure:
    <td width="210">&nbsp;- Número do processo:</td>
    <td width="390"><b>2753442025-3</b></td>
    
    <td width="210">&nbsp;- Razão Social:</td>
    <td width="390">SILVA COMERCIO DE GAS LTDA</td>
    
    Args:
        page: Playwright Page instance
        
    Returns:
        Dictionary with processo_numero and razao_social
    """
    data: dict[str, str] = {}

    try:
        # Extract process number
        processo_selectors = [
            "td:has-text('Número do processo:') + td",
            "td:has-text('Número do processo') + td",
        ]

        for selector in processo_selectors:
            try:
                processo_td = page.locator(selector).first
                await processo_td.wait_for(timeout=ELEMENT_TIMEOUT)
                text = await processo_td.text_content()
                if text:
                    # Extract the process number (format: digits-dash-digit)
                    match = re.search(r"(\d{4,}[-]?\d{1,})", text.strip())
                    if match:
                        data["processo_numero"] = match.group(1).strip()
                        break
            except Exception:
                continue

        # Extract razão social
        razao_selectors = [
            "td:has-text('Razão Social:') + td",
            "td:has-text('Razão Social') + td",
        ]

        for selector in razao_selectors:
            try:
                razao_td = page.locator(selector).first
                await razao_td.wait_for(timeout=ELEMENT_TIMEOUT)
                text = await razao_td.text_content()
                if text:
                    # Clean up the text (remove any label remnants and extra whitespace)
                    cleaned = re.sub(
                        r".*Razão Social[:\s]*", "", text, flags=re.IGNORECASE
                    ).strip()
                    # Remove any HTML tags or formatting
                    cleaned = re.sub(r"<[^>]+>", "", cleaned).strip()
                    if cleaned and len(cleaned) > 3:
                        data["razao_social"] = cleaned
                        break
            except Exception:
                continue

        logger.info(
            "cadastro_redesim: extracted process data from page: processo=%s, razao_social=%s",
            data.get("processo_numero", "N/A"),
            data.get("razao_social", "N/A")[:50] if data.get("razao_social") else "N/A",
        )
        return data

    except Exception as e:
        logger.exception(f"cadastro_redesim: error extracting process data from page: {e}")
        return data


async def _extract_emails_from_frame(frame: Frame) -> list[str]:
    """Extract all email addresses from a frame.

    Filters out SEFAZ system emails (e.g., @sefaz.pb.gov.br).

    Args:
        frame: Playwright Frame instance

    Returns:
        List of unique email addresses found (excluding system emails)
    """
    emails: set[str] = set()
    email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

    # System email patterns to exclude
    system_email_patterns = [
        r"@sefaz\.pb\.gov\.br",
        r"cacgr1@sefaz\.pb\.gov\.br",
        r".*@.*sefaz.*",
    ]

    try:
        # Get all text content from the frame
        text_content = await frame.content()

        # Find emails in text
        found_emails = re.findall(email_pattern, text_content, re.IGNORECASE)
        emails.update(email.lower() for email in found_emails)

        # Also check input fields with type="email" or name containing "email"
        email_inputs = frame.locator(
            "input[type='email'], input[name*='email' i], input[id*='email' i]"
        )
        count = await email_inputs.count()
        for i in range(count):
            try:
                value = await email_inputs.nth(i).input_value()
                if value and "@" in value:
                    emails.add(value.lower().strip())
            except Exception:
                continue

        # Check td elements that might contain emails (like in the FC frame)
        email_tds = frame.locator("td:has-text('@')")
        count = await email_tds.count()
        for i in range(count):
            try:
                text = await email_tds.nth(i).text_content()
                if text:
                    found = re.findall(email_pattern, text, re.IGNORECASE)
                    emails.update(email.lower() for email in found)
            except Exception:
                continue

        # Filter out common non-email patterns and system emails
        filtered_emails = []
        for email in emails:
            # Basic validation
            if (
                email.startswith("http")
                or "@" not in email
                or "." not in email.split("@")[1]
            ):
                continue

            # Filter out system emails
            is_system_email = any(
                re.search(pattern, email, re.IGNORECASE)
                for pattern in system_email_patterns
            )
            if is_system_email:
                logger.debug(f"cadastro_redesim: filtered out system email: {email}")
                continue

            filtered_emails.append(email)

        if filtered_emails:
            logger.info(
                "cadastro_redesim: extracted %d unique email(s): %s",
                len(filtered_emails),
                ", ".join(filtered_emails[:3])
                + ("..." if len(filtered_emails) > 3 else ""),
            )
        else:
            logger.warning(
                "cadastro_redesim: no valid emails extracted from frame. "
                "Total raw email candidates found: %d",
                len(emails),
            )
        return sorted(filtered_emails)

    except Exception as e:
        logger.exception(f"cadastro_redesim: error extracting emails: {e}")
        return []


async def _extract_process_data_from_frame(frame: Frame) -> dict[str, str]:
    """Extract process number and razão social from FC frame.

    Uses exact selectors matching the HTML structure:
    - Process number: td with "Número do processo:" followed by value in next td
    - Razão Social: td with "Razão Social:" followed by value in next td

    Args:
        frame: Playwright Frame instance (FC frame)

    Returns:
        Dictionary with processo_numero and razao_social
    """
    data: dict[str, str] = {}

    try:
        # Extract process number using exact selector pattern
        # HTML: <td width="210">&nbsp;- Número do processo:</td><td width="390"><b>2766432025-9</b></td>
        processo_selectors = [
            "td:has-text('Número do processo:') + td",
            "td:has-text('Número do processo') + td",
            "td[width='210']:has-text('Número do processo') + td[width='390']",
        ]

        for selector in processo_selectors:
            try:
                processo_td = frame.locator(selector).first
                await processo_td.wait_for(timeout=ELEMENT_TIMEOUT)
                text = await processo_td.text_content()
                if text:
                    # Extract the process number (format: digits-dash-digit)
                    match = re.search(r"(\d{4,}[-]?\d{1,})", text.strip())
                    if match:
                        data["processo_numero"] = match.group(1).strip()
                        break
            except Exception:
                continue

        # Extract razão social using exact selector pattern
        # HTML: <td width="210">&nbsp;- Razão Social:</td><td width="390">D S DA SILVA...</td>
        razao_selectors = [
            "td:has-text('Razão Social:') + td",
            "td:has-text('Razão Social') + td",
            "td[width='210']:has-text('Razão Social') + td[width='390']",
        ]

        for selector in razao_selectors:
            try:
                razao_td = frame.locator(selector).first
                await razao_td.wait_for(timeout=ELEMENT_TIMEOUT)
                text = await razao_td.text_content()
                if text:
                    # Clean up the text (remove any label remnants and extra whitespace)
                    cleaned = re.sub(
                        r".*Razão Social[:\s]*", "", text, flags=re.IGNORECASE
                    ).strip()
                    # Remove any HTML tags or formatting
                    cleaned = re.sub(r"<[^>]+>", "", cleaned).strip()
                    if cleaned and len(cleaned) > 3:
                        data["razao_social"] = cleaned
                        break
            except Exception:
                continue

        logger.info(
            "cadastro_redesim: extracted process data: processo=%s, razao_social=%s",
            data.get("processo_numero", "N/A"),
            data.get("razao_social", "N/A")[:50] if data.get("razao_social") else "N/A",
        )
        return data

    except Exception as e:
        logger.exception(f"cadastro_redesim: error extracting process data: {e}")
        return data


async def process_redesim_stage2(
    page: Page,
    gmail_credentials_path: str | None = None,
    gmail_token_path: str | None = None,
    output_dir: str | None = None,
    row_index: int = 0,
) -> dict[str, Any]:
    """Process REDESIM Stage 2: Extract data from detail page and create Gmail drafts.

    Args:
        page: Playwright Page instance (on results list page after consultar_redesim)
        gmail_credentials_path: Optional path to Gmail credentials.json
        gmail_token_path: Optional path to Gmail token.json
        output_dir: Optional output directory for JSON results (default: project_root/output)
        row_index: Index of row to select in results list (default: 0)

    Returns:
        Dictionary with stage 2 processing results
    """
    results: dict[str, Any] = {
        "timestamp": datetime.now().isoformat(),
        "success": False,
        "steps": {},
        "errors": [],
    }

    try:
        # Step 1: Load persistent state and resolve iframe
        logger.info("cadastro_redesim: Stage 2 - Step 1: Loading iteration state")
        state = _load_iteration_state()
        
        # CRITICAL BUG FIX: Do NOT override row_index with persisted state
        # The loop in run_redesim_consulta.py already manages the iteration correctly
        # We should use the row_index passed as parameter, not the persisted one
        # The persisted state is only used for resuming after a crash, not during normal iteration
        last_processed_value = state.get("last_processed_value")
        
        logger.info(
            "cadastro_redesim: Stage 2 - Processing row_index=%d (from loop), persisted_index=%s",
            row_index,
            state.get("current_index", "N/A"),
        )
        
        # CRITICAL: Validate we're not reprocessing the same process
        if last_processed_value:
            logger.info(
                "cadastro_redesim: Stage 2 - Last processed value: %s (will skip if same)",
                last_processed_value,
            )
        
        # Step 2: Wait for results page and resolve iframe 'principal' EXPLICITLY
        logger.info("cadastro_redesim: Stage 2 - Step 2: Waiting for results page and resolving iframe")
        await page.wait_for_load_state("domcontentloaded", timeout=FAST_TIMEOUT)
        await page.wait_for_timeout(FAST_DEFAULT_DELAY)
        
        # MANDATORY: Resolve iframe 'principal' explicitly
        try:
            principal_frame = await _resolve_principal_iframe(page, timeout=FAST_TIMEOUT)
        except RuntimeError as iframe_err:
            error_msg = f"Failed to resolve iframe 'principal': {iframe_err}"
            logger.error(f"cadastro_redesim: Stage 2 - {error_msg}")
            results["errors"].append(error_msg)
            return results
        
        # Step 3: Collect ALL radio buttons from iframe (index-based, deterministic)
        logger.info("cadastro_redesim: Stage 2 - Step 3: Collecting radio buttons from iframe")
        try:
            radio_list = await _collect_radio_buttons_from_iframe(principal_frame)
            radio_count = len(radio_list)
        except RuntimeError as radio_err:
            error_msg = f"Failed to collect radio buttons: {radio_err}"
            logger.error(f"cadastro_redesim: Stage 2 - {error_msg}")
            results["errors"].append(error_msg)
            return results
        
        logger.info(
            "cadastro_redesim: Stage 2 - Collected %d radio button(s) from iframe",
            radio_count,
        )
        
        # Update total in state if not set
        if state.get("total") is None:
            state["total"] = radio_count
            _save_iteration_state(state)
            logger.info(
                "cadastro_redesim: Stage 2 - Set total processes to %d in state",
                radio_count,
            )
        
        # Validate index bounds
        if row_index >= radio_count:
            error_msg = (
                f"Index {row_index} >= total {radio_count}. "
                f"All processes have been processed."
            )
            logger.warning(f"cadastro_redesim: Stage 2 - {error_msg}")
            results["errors"].append(error_msg)
            return results
        
        # Step 4: Select radio button by INDEX (deterministic)
        logger.info(
            "cadastro_redesim: Stage 2 - Step 4: Selecting radio button at index %d",
            row_index,
        )
        
        try:
            # CRITICAL: Get the radio button by index from our collected list
            # This list was collected fresh at the start of this function
            # Never reuse radio references from previous iterations
            radio = radio_list[row_index]
            
            # Get the value before clicking (for logging and state)
            # CRITICAL: Always query fresh - never cache values
            radio_value = await radio.get_attribute("value")
            logger.info(
                "cadastro_redesim: Stage 2 - Radio button[%d] value: %s",
                row_index,
                radio_value,
            )
            
            # CRITICAL: Skip if this is the same process we just processed
            if last_processed_value and radio_value == last_processed_value:
                error_msg = (
                    f"Skipping process {radio_value} at index {row_index} - "
                    f"already processed (last_processed_value={last_processed_value}). "
                    f"This indicates the same process is being selected again."
                )
                logger.warning(f"cadastro_redesim: Stage 2 - {error_msg}")
                results["errors"].append(error_msg)
                results["steps"]["process_selection"] = {
                    "success": False,
                    "error": "Same process detected - skipping to avoid duplicate",
                    "row_index": row_index,
                    "radio_value": radio_value,
                }
                return results
            
            # CRITICAL: Click the radio button (MUST use real click, never .checked = true)
            # Scroll into view first for reliability
            await radio.wait_for(timeout=ELEMENT_TIMEOUT, state="visible")
            await radio.scroll_into_view_if_needed()
            await radio.click()
            logger.info(
                "cadastro_redesim: Stage 2 - Radio button[%d] (value=%s) clicked",
                row_index,
                radio_value,
            )
            
            # CRITICAL: Wait for hidden fields to be updated by defineCamposHid()
            # The system does NOT use .checked state - it uses hidden fields updated by onClick
            logger.info(
                "cadastro_redesim: Stage 2 - Waiting for hidden fields to be updated..."
            )
            hidden_field_updated = await _wait_for_hidden_field_sync(
                principal_frame, radio_value, timeout=ELEMENT_TIMEOUT * 2
            )
            
            if not hidden_field_updated:
                error_msg = (
                    f"Hidden field hidNrProcesso not updated after radio click. "
                    f"Expected: {radio_value}, but field was not synchronized."
                )
                logger.error(f"cadastro_redesim: Stage 2 - {error_msg}")
                results["errors"].append(error_msg)
                results["steps"]["process_selection"] = {
                    "success": False,
                    "error": "Hidden field synchronization failed",
                }
                return results
            
            logger.info(
                "cadastro_redesim: Stage 2 - Hidden fields synchronized: hidNrProcesso=%s",
                radio_value,
            )
            await page.wait_for_timeout(FAST_CLICK_DELAY)
            
            # Step 5: Submit form (press Enter as per requirement)
            # ONLY after hidden fields are confirmed updated
            # CRITICAL: Form submission must occur only after:
            #   - Radio click completed
            #   - Hidden fields updated (validated above)
            #   - State synchronized
            logger.info("cadastro_redesim: Stage 2 - Step 5: Submitting form (pressing Enter)")
            
            # CRITICAL: Re-query form elements (never reuse stale references after click)
            # The iframe may have updated, so we must query fresh
            form = principal_frame.locator('form[name="frmListagemPendeciaProc"]').first
            
            # Try to find "Detalhar" button first (more reliable)
            # HTML real: <input type="submit" name="btnConsultar" value="Detalhar" onClick="defineAcao(this)">
            detalhar_buttons = form.locator(
                "input[name='btnConsultar'], "
                "input[type='submit'][value*='Detalhar' i], "
                "input[type='button'][value*='Detalhar' i]"
            )
            detalhar_count = await detalhar_buttons.count()
            
            if detalhar_count > 0:
                # CRITICAL: Re-query the button before clicking (never reuse stale reference)
                detalhar_button = detalhar_buttons.first
                await detalhar_button.wait_for(timeout=ELEMENT_TIMEOUT, state="visible")
                await detalhar_button.click()
                logger.info("cadastro_redesim: Stage 2 - Clicked 'Detalhar' button in iframe")
            else:
                # Fallback: press Enter on the radio button (as per requirement)
                # CRITICAL: Re-query radio before pressing (never reuse stale reference)
                radio_fresh = principal_frame.locator(
                    f"input[type='radio'][name='rdbChavePrimaria'][value='{radio_value}']"
                ).first
                await radio_fresh.wait_for(timeout=ELEMENT_TIMEOUT, state="visible")
                await radio_fresh.press("Enter")
                logger.info("cadastro_redesim: Stage 2 - Pressed Enter on radio button")
            
            results["steps"]["process_selection"] = {
                "success": True,
                "row_index": row_index,
                "radio_value": radio_value,
            }
            
            # Update state with last processed value
            state["last_processed_value"] = radio_value
            _save_iteration_state(state)
            
            # Wait for detail page to load
            await page.wait_for_load_state("domcontentloaded", timeout=FAST_TIMEOUT)
            await page.wait_for_timeout(FAST_SEARCH_DELAY)
            
        except Exception as e:
            error_msg = f"Failed to select and submit process: {e}"
            logger.exception(f"cadastro_redesim: Stage 2 - {error_msg}")
            results["errors"].append(error_msg)
            results["steps"]["process_selection"] = {"success": False, "error": str(e)}
            return results

        
        # Step 3: Extract emails and process data directly from detail page
        logger.info("cadastro_redesim: Stage 2 - Step 3: Extracting emails and process data from detail page")
        
        # Extract emails from the main page (no frames)
        emails = await _extract_emails_from_page(page)
        
        # Extract process data from the main page
        process_data = await _extract_process_data_from_page(page)
        
        results["steps"]["email_extraction"] = {"emails": emails, "count": len(emails)}
        results["steps"]["process_data"] = process_data

        logger.info(
            "cadastro_redesim: Stage 2 - Step 3: Extracted %d email(s), process_num=%s, razao_social=%s",
            len(emails),
            process_data.get("processo_numero", "N/A"),
            (
                process_data.get("razao_social", "N/A")[:50]
                if process_data.get("razao_social")
                else "N/A"
            ),
        )

        # Step 4: Create Gmail draft
        logger.info("cadastro_redesim: Stage 2 - Step 4: Creating Gmail draft")
        draft_result = None

        if not emails:
            logger.warning(
                "cadastro_redesim: Stage 2 - No emails extracted, skipping draft creation"
            )
            results["steps"]["gmail_draft"] = {
                "success": False,
                "error": "No emails found",
            }
            results["errors"].append("No emails found for Gmail draft")
        elif emails:
            # Build subject from process number and razão social
            # Format matches: "Número do processo: {num} - Razão Social: {name}"
            processo_num = process_data.get("processo_numero", "N/A")
            razao_social = process_data.get("razao_social", "N/A")
            subject = (
                f"Número do processo: {processo_num} - Razão Social: {razao_social}"
            )

            # Truncate razão social if too long (Gmail subject limit is ~200 chars)
            if len(subject) > 200:
                max_razao_len = 200 - len(
                    f"Número do processo: {processo_num} - Razão Social: "
                )
                if max_razao_len > 0:
                    razao_truncated = razao_social[:max_razao_len] + "..."
                    subject = f"Número do processo: {processo_num} - Razão Social: {razao_truncated}"

            # Email body template
            body = """Prezado contribuinte,

	O processo de cadastramento estadual segue em análise. 

Para finalizarmos o parecer fiscal, solicitamos o envio digital (sem compactação) dos documentos abaixo dentro de 3 (três) dias corridos:

• Fotos internas e externas atualizadas do empreendimento (fachada com numeração)
• Contrato de locação ou instrumento que comprove a posse do parque
• Lista do ativo imobilizado, equipamentos recreativos e quadro de colaboradores previstos"""

            try:
                logger.info(
                    "cadastro_redesim: Stage 2 - Initializing GmailService with credentials_path=%s, token_path=%s",
                    gmail_credentials_path,
                    gmail_token_path,
                )

                gmail_service = GmailService(
                    credentials_path=gmail_credentials_path,
                    token_path=gmail_token_path,
                )

                logger.info(
                    "cadastro_redesim: Stage 2 - Creating draft for %d recipient(s): %s",
                    len(emails),
                    ", ".join(emails[:3]) + ("..." if len(emails) > 3 else ""),
                )
                logger.info(
                    "cadastro_redesim: Stage 2 - Draft subject: %s",
                    subject[:100] + ("..." if len(subject) > 100 else ""),
                )

                draft_result = gmail_service.create_draft(
                    to=", ".join(emails),
                    subject=subject,
                    body=body,
                )

                if draft_result:
                    draft_id = draft_result.get("id", "unknown")
                    message_id = draft_result.get("message", {}).get("id", "unknown")
                    logger.info(
                        "cadastro_redesim: Stage 2 - Draft created successfully! draft_id=%s, message_id=%s",
                        draft_id,
                        message_id,
                    )
                    results["steps"]["gmail_draft"] = {
                        "success": True,
                        "draft_id": draft_id,
                        "message_id": message_id,
                    }
                else:
                    error_msg = "Draft creation returned None (check Gmail API logs for details)"
                    logger.error(
                        "cadastro_redesim: Stage 2 - %s",
                        error_msg,
                    )
                    results["steps"]["gmail_draft"] = {
                        "success": False,
                        "error": error_msg,
                    }
                    results["errors"].append("Gmail draft creation failed")

            except FileNotFoundError as e:
                error_msg = f"Gmail credentials file not found: {e}"
                logger.exception(f"cadastro_redesim: Stage 2 - {error_msg}")
                results["steps"]["gmail_draft"] = {"success": False, "error": error_msg}
                results["errors"].append(f"Gmail credentials error: {error_msg}")
            except Exception as e:
                error_msg = str(e)
                logger.exception(
                    "cadastro_redesim: Stage 2 - Error creating Gmail draft: %s",
                    error_msg,
                )
                results["steps"]["gmail_draft"] = {"success": False, "error": error_msg}
                results["errors"].append(f"Gmail draft creation error: {error_msg}")

        # Step 7: Save results to JSON
        logger.info("cadastro_redesim: Stage 2 - Step 7: Saving results to JSON")
        if output_dir is None:
            project_root = Path(__file__).parent.parent.parent.parent
            output_dir = str(project_root / "output")

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_path / f"redesim_stage2_results_{timestamp_str}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        results["output_file"] = str(output_file)
        logger.info(f"cadastro_redesim: Stage 2 results saved to {output_file}")

        results["success"] = len(results["errors"]) == 0
        return results

    except Exception as e:
        logger.exception(f"cadastro_redesim: Stage 2 processing error: {e}")
        results["errors"].append(f"Unexpected error: {str(e)}")
        results["success"] = False
        return results
