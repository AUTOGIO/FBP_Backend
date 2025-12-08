"""Data Validator for NFA
Validates CPF, CEP, phone numbers, and other Brazilian data formats.
"""

import logging
import re

logger = logging.getLogger(__name__)


def validate_cpf(cpf: str) -> bool:
    """Validate Brazilian CPF format and checksum.

    Args:
        cpf: CPF string (with or without formatting)

    Returns:
        True if valid CPF, False otherwise

    """
    if not cpf:
        return False

    # Remove non-digits
    cpf_clean = re.sub(r"\D", "", cpf)

    # Check length
    if len(cpf_clean) != 11:
        return False

    # Check for invalid patterns (all same digit)
    if cpf_clean == cpf_clean[0] * 11:
        return False

    # Validate checksum
    def calculate_digit(cpf_digits: list[int], weights: list[int]) -> int:
        total = sum(digit * weight for digit, weight in zip(cpf_digits, weights))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder

    cpf_digits = [int(d) for d in cpf_clean]

    # First digit
    first_digit = calculate_digit(cpf_digits[:9], list(range(10, 1, -1)))
    if first_digit != cpf_digits[9]:
        return False

    # Second digit
    second_digit = calculate_digit(cpf_digits[:10], list(range(11, 1, -1)))
    return second_digit == cpf_digits[10]


def validate_cnpj(cnpj: str) -> bool:
    """Validate Brazilian CNPJ format and checksum.

    Args:
        cnpj: CNPJ string (with or without formatting)

    Returns:
        True if valid CNPJ, False otherwise

    """
    if not cnpj:
        return False

    # Remove non-digits
    cnpj_clean = re.sub(r"\D", "", cnpj)

    # Check length
    if len(cnpj_clean) != 14:
        return False

    # Check for invalid patterns
    if cnpj_clean == cnpj_clean[0] * 14:
        return False

    # Validate checksum
    def calculate_digit(cnpj_digits: list[int], weights: list[int]) -> int:
        total = sum(digit * weight for digit, weight in zip(cnpj_digits, weights))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder

    cnpj_digits = [int(d) for d in cnpj_clean]

    # First digit
    weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    first_digit = calculate_digit(cnpj_digits[:12], weights_1)
    if first_digit != cnpj_digits[12]:
        return False

    # Second digit
    weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    second_digit = calculate_digit(cnpj_digits[:13], weights_2)
    return second_digit == cnpj_digits[13]


def validate_phone(phone: str) -> bool:
    """Validate Brazilian phone number format.

    Args:
        phone: Phone string (with or without formatting)

    Returns:
        True if valid phone, False otherwise

    """
    if not phone:
        return False

    # Remove non-digits
    phone_clean = re.sub(r"\D", "", phone)

    # Brazilian phones: 10-11 digits (with area code)
    return len(phone_clean) in [10, 11] and phone_clean[0] in "123456789"


def validate_cep(cep: str) -> bool:
    """Validate Brazilian CEP format.

    Args:
        cep: CEP string (with or without formatting)

    Returns:
        True if valid CEP format, False otherwise

    """
    if not cep:
        return False

    # Remove non-digits
    cep_clean = re.sub(r"\D", "", cep)

    # CEP: exactly 8 digits
    return len(cep_clean) == 8 and cep_clean.isdigit()


def validate_uf(uf: str) -> bool:
    """Validate Brazilian state code (UF).

    Args:
        uf: State code string

    Returns:
        True if valid UF, False otherwise

    """
    valid_states = {
        "AC",
        "AL",
        "AP",
        "AM",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MT",
        "MS",
        "MG",
        "PA",
        "PB",
        "PR",
        "PE",
        "PI",
        "RJ",
        "RN",
        "RS",
        "RO",
        "RR",
        "SC",
        "SP",
        "SE",
        "TO",
    }
    return uf.upper() in valid_states


def validate_destinatario(
    destinatario: dict,
    index: int,
) -> tuple[bool, list[str]]:
    """Validate a single destinatario record (simplified: only CPF validation).

    Args:
        destinatario: Destinatario data dictionary (can be dict with 'cpf' or 'documento' key)
        index: Record index for error reporting

    Returns:
        Tuple of (is_valid, list_of_errors)

    """
    errors: list[str] = []

    # Extract CPF from different possible field names
    cpf = (
        destinatario.get("cpf", "")
        or destinatario.get("CPF", "")
        or destinatario.get("documento", "")
        or destinatario.get("documento", "")
    )

    # CPF is required
    if not cpf:
        errors.append(f"Missing required field: CPF/documento")

    # Validate CPF format and checksum
    if cpf and not validate_cpf(cpf):
        errors.append(f"Invalid CPF format or checksum: {cpf}")

    return len(errors) == 0, errors


def validate_emitente(
    emitente: dict,
    index: int,
) -> tuple[bool, list[str]]:
    """Validate a single emitente record (simplified: only CNPJ validation).

    Args:
        emitente: Emitente data dictionary (can be dict with 'cnpj' key)
        index: Record index for error reporting

    Returns:
        Tuple of (is_valid, list_of_errors)

    """
    errors: list[str] = []

    # Extract CNPJ from different possible field names
    cnpj = (
        emitente.get("cnpj", "")
        or emitente.get("CNPJ", "")
        or emitente.get("documento", "")
    )

    # CNPJ is required
    if not cnpj:
        errors.append(f"Missing required field: CNPJ")

    # Validate CNPJ format and checksum
    if cnpj and not validate_cnpj(cnpj):
        errors.append(f"Invalid CNPJ format or checksum: {cnpj}")

    return len(errors) == 0, errors
