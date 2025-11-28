"""NFA (Nota Fiscal Avulsa) Automation Module.

Core logic for NFA form automation and ATF integration with universal DOM context
support (root or iframe).
"""

from app.modules.nfa.atf_frames import (
    get_main_frame,  # Deprecated, kept for compatibility
    wait_for_nfa_fields,
)
from app.modules.nfa.atf_login import (
    ATF_BASE_URL,
    NFA_FORM_URL,
    atf_manual_login,
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
from app.modules.nfa.data_validator import (
    validate_cep,
    validate_cnpj,
    validate_cpf,
    validate_destinatario,
    validate_phone,
    validate_uf,
)
from app.modules.nfa.destinatario_filler import preencher_destinatario
from app.modules.nfa.emitente_filler import preencher_emitente
from app.modules.nfa.endereco_filler import preencher_endereco
from app.modules.nfa.form_filler import fill_nfa_form_complete, preencher_nfa
from app.modules.nfa.form_utils import (
    click_calcular,
    click_form_button,
    fill_form_fields,
    get_form_value,
    select_form_option,
    set_form_value,
    submit_form,
)
from app.modules.nfa.nfa_context import (
    NFAContext,
    get_page_from_context,
    resolve_nfa_context,
    wait_for_nfa_ready,
)
from app.modules.nfa.produto_filler import adicionar_item

__all__ = [
    # URLs
    "ATF_BASE_URL",
    "NFA_FORM_URL",
    # Frame functions
    "get_main_frame",  # Deprecated
    "wait_for_nfa_fields",
    "NFAContext",
    "get_page_from_context",
    "resolve_nfa_context",
    "wait_for_nfa_ready",
    # Login functions
    "atf_manual_login",
    "perform_login",
    "select_function_fis_1698",
    "wait_for_post_login",
    # Form utils
    "click_calcular",
    "click_form_button",
    "fill_form_fields",
    "get_form_value",
    "select_form_option",
    "set_form_value",
    "submit_form",
    # Fillers
    "adicionar_item",
    "fill_nfa_form_complete",
    "preencher_destinatario",
    "preencher_emitente",
    "preencher_endereco",
    "preencher_nfa",
    # Selectors
    "DEST_TABLE",
    "EMITENTE_TABLE",
    "ENDERECO_TABLE",
    "ITEM_TABLE",
    "PRODUTO_TABLE",
    # Processor
    "BatchNFAProcessor",
    # Validators
    "validate_cep",
    "validate_cnpj",
    "validate_cpf",
    "validate_destinatario",
    "validate_phone",
    "validate_uf",
]
