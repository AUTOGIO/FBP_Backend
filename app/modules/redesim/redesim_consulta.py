"""Automates the REDESIM consulta form after NFA login."""

from __future__ import annotations

import logging

from playwright.async_api import Page

logger = logging.getLogger(__name__)


async def consultar_processos_redesim(page: Page) -> None:
    """Fill and submit the REDESIM 'Consultar Processos' form with fixed criteria."""
    logger.info("Filling REDESIM consulta form with fixed criteria...")

    # Natureza da Solicitação
    await page.select_option(
        'select[name="cmbOperacao"]',
        label="CADASTRAMENTO",
    )

    # Criação do processo
    await page.fill('input[name="edtDtCriacaoProcIni"]', "10/12/2025")
    await page.fill('input[name="edtDtCriacaoProcFim"]', "17/12/2025")

    # Situação do Processo
    await page.select_option(
        'select[name="lstSituacaoProc"]',
        label="DEFERIDO",
    )

    # Situação do conjunto de Inconsistências (select all options)
    options = await page.locator('select[name="lstSitIncons"] option').all()
    values = [await opt.get_attribute("value") for opt in options]
    await page.select_option(
        'select[name="lstSitIncons"]',
        values=values,
    )

    # Elemento organizacional responsável
    await page.fill('input[name="txtCodOrgao"]', "90102008")

    # Consultar
    await page.click('input[type="submit"][value="Consultar"]')
    await page.wait_for_load_state("networkidle")

    logger.info("REDESIM consulta submitted.")
