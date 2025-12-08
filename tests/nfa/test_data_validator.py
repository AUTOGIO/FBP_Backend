"""Tests for NFA data validator."""

from app.modules.nfa.data_validator import (
    validate_cep,
    validate_cnpj,
    validate_cpf,
    validate_destinatario,
    validate_phone,
    validate_uf,
)


def test_validate_cpf_valid() -> None:
    """Test valid CPF validation."""
    assert validate_cpf("12345678909") is True
    assert validate_cpf("123.456.789-09") is True


def test_validate_cpf_invalid() -> None:
    """Test invalid CPF validation."""
    assert validate_cpf("12345678900") is False
    assert validate_cpf("11111111111") is False
    assert validate_cpf("") is False


def test_validate_cnpj_valid() -> None:
    """Test valid CNPJ validation."""
    assert validate_cnpj("11222333000181") is True
    assert validate_cnpj("11.222.333/0001-81") is True


def test_validate_cnpj_invalid() -> None:
    """Test invalid CNPJ validation."""
    assert validate_cnpj("11222333000180") is False
    assert validate_cnpj("11111111111111") is False


def test_validate_cep_valid() -> None:
    """Test valid CEP validation."""
    assert validate_cep("58000000") is True
    assert validate_cep("58000-000") is True


def test_validate_cep_invalid() -> None:
    """Test invalid CEP validation."""
    assert validate_cep("1234567") is False
    assert validate_cep("123456789") is False


def test_validate_phone_valid() -> None:
    """Test valid phone validation."""
    assert validate_phone("83987654321") is True
    assert validate_phone("(83) 98765-4321") is True


def test_validate_phone_invalid() -> None:
    """Test invalid phone validation."""
    assert validate_phone("123456789") is False
    assert validate_phone("") is False


def test_validate_uf_valid() -> None:
    """Test valid UF validation."""
    assert validate_uf("PB") is True
    assert validate_uf("pb") is True
    assert validate_uf("SP") is True


def test_validate_uf_invalid() -> None:
    """Test invalid UF validation."""
    assert validate_uf("XX") is False
    assert validate_uf("") is False


def test_validate_destinatario_valid() -> None:
    """Test valid destinatario validation."""
    destinatario = {
        "NOME DO FRANQUEADO": "Teste",
        "CPF": "12345678909",
        "ENDEREÇO": "Rua Teste",
        "NÚMERO": "123",
        "BAIRRO": "Centro",
        "MUNICÍPIO": "João Pessoa",
        "UF": "PB",
        "CEP": "58000000",
        "TELEFONE": "83987654321",
    }
    is_valid, errors = validate_destinatario(destinatario, 0)
    assert is_valid is True
    assert len(errors) == 0


def test_validate_destinatario_invalid() -> None:
    """Test invalid destinatario validation."""
    destinatario = {
        "NOME DO FRANQUEADO": "",
        "CPF": "123",
        "UF": "XX",
    }
    is_valid, errors = validate_destinatario(destinatario, 0)
    assert is_valid is False
    assert len(errors) > 0
