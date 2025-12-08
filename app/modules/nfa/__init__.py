"""NFA (Nota Fiscal Avulsa) Automation Module.

Core logic for NFA form automation and ATF integration.
"""

from app.modules.nfa.atf_frames import log_page_frames
from app.modules.nfa.atf_login import (
    navigate_to_nfa_form,
    perform_login,
    select_function_fis_1698,
    wait_for_post_login,
)
from app.modules.nfa.atf_selectors import (
    DEST_TABLE,
    EMITENTE_TABLE,
    ENDERECO_TABLE,
    ITEM_TABLE,
    PRODUTO_TABLE,
)
from app.modules.nfa.batch_processor import BatchNFAProcessor
from app.modules.nfa.browser_launcher import (
    launch_persistent_browser,
    navigate_to_sefaz_with_fallback,
)
from app.modules.nfa.campos_fixos_filler import preencher_campos_fixos
from app.modules.nfa.data_validator import (
    validate_cep,
    validate_cnpj,
    validate_cpf,
    validate_destinatario,
    validate_emitente,
    validate_phone,
    validate_uf,
)
from app.modules.nfa.destinatario_filler import preencher_destinatario
from app.modules.nfa.emitente_filler import preencher_emitente
from app.modules.nfa.endereco_filler import preencher_endereco
from app.modules.nfa.form_filler import fill_nfa_form_complete, preencher_nfa
from app.modules.nfa.form_submitter import submeter_nfa
from app.modules.nfa.informacoes_adicionais_filler import (
    preencher_informacoes_adicionais,
)
from app.modules.nfa.pdf_downloader import (
    download_all_pdfs,
    download_dar_pdf,
    download_nota_fiscal_pdf,
)
from app.modules.nfa.produto_filler import adicionar_item

__all__ = [
    "DEST_TABLE",
    "EMITENTE_TABLE",
    "ENDERECO_TABLE",
    "ITEM_TABLE",
    "PRODUTO_TABLE",
    "BatchNFAProcessor",
    "adicionar_item",
    "download_all_pdfs",
    "download_dar_pdf",
    "download_nota_fiscal_pdf",
    "fill_nfa_form_complete",
    "launch_persistent_browser",
    "log_page_frames",
    "navigate_to_nfa_form",
    "navigate_to_sefaz_with_fallback",
    "perform_login",
    "preencher_campos_fixos",
    "preencher_destinatario",
    "preencher_emitente",
    "preencher_endereco",
    "preencher_informacoes_adicionais",
    "preencher_nfa",
    "select_function_fis_1698",
    "submeter_nfa",
    "validate_cep",
    "validate_cnpj",
    "validate_cpf",
    "validate_destinatario",
    "validate_emitente",
    "validate_phone",
    "validate_uf",
    "wait_for_post_login",
]
