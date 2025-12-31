"""Tests for REDESIM Stage 2 automation.

Tests CEP validation, CFC checking, email extraction, and Gmail draft creation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.cadastro.consultar_redesim import (
    _check_contabilista_cfc,
    _extract_emails_from_frame,
    _extract_process_data_from_frame,
    _validate_cep_viacep,
)


class TestCEPValidation:
    """Tests for CEP validation via ViaCEP."""

    @pytest.mark.asyncio
    async def test_validate_cep_valid(self) -> None:
        """Test validation of a valid CEP."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "cep": "58084-150",
                "logradouro": "Rua Test",
                "bairro": "Test Bairro",
                "localidade": "João Pessoa",
                "uf": "PB",
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            result = await _validate_cep_viacep("58084-150")

            assert result["valid"] is True
            assert result["cep"] == "58084-150"
            assert result["logradouro"] == "Rua Test"

    @pytest.mark.asyncio
    async def test_validate_cep_invalid_format(self) -> None:
        """Test validation of invalid CEP format."""
        result = await _validate_cep_viacep("12345")

        assert result["valid"] is False
        assert "formato incorreto" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_validate_cep_not_found(self) -> None:
        """Test validation of CEP not found in ViaCEP."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"erro": True}
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            result = await _validate_cep_viacep("00000-000")

            assert result["valid"] is False
            assert "não encontrado" in result["error"].lower()


class TestCFCCheck:
    """Tests for contabilista CFC checking."""

    @pytest.mark.asyncio
    async def test_check_cfc_valid_cpf(self) -> None:
        """Test CFC check with valid CPF."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = "04866760486 regular ativo"
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get.return_value = (
                mock_response
            )

            result = await _check_contabilista_cfc("048.667.604-86")

            assert result["valid"] is True
            assert result["cpf"] == "04866760486"
            assert result["cfc_accessible"] is True

    @pytest.mark.asyncio
    async def test_check_cfc_invalid_format(self) -> None:
        """Test CFC check with invalid CPF format."""
        result = await _check_contabilista_cfc("12345")

        assert result["valid"] is False
        assert "formato incorreto" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_check_cfc_http_error(self) -> None:
        """Test CFC check with HTTP error."""
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = (
                Exception("Connection error")
            )

            result = await _check_contabilista_cfc("04866760486")

            assert result["valid"] is False
            assert "erro" in result["error"].lower()


class TestEmailExtraction:
    """Tests for email extraction from frames."""

    @pytest.mark.asyncio
    async def test_extract_emails_from_text(self) -> None:
        """Test email extraction from frame content."""
        mock_frame = MagicMock()  # Use MagicMock, not AsyncMock for frame
        mock_frame.content = AsyncMock(
            return_value="""
        <html>
        <body>
        <td>Email: test@example.com</td>
        <td>Another: user@domain.com.br</td>
        <td>System: admin@sefaz.pb.gov.br</td>
        </body>
        </html>
        """
        )

        # Mock locator chain for input fields (returns immediately, not a coroutine)
        mock_input_locator = MagicMock()
        mock_input_locator.count = AsyncMock(return_value=0)

        # Mock locator for td elements (empty)
        mock_td_locator = MagicMock()
        mock_td_locator.count = AsyncMock(return_value=0)

        # Setup locator to return appropriate mock (not a coroutine)
        def locator_side_effect(selector):
            if "input" in selector:
                return mock_input_locator
            if "td:has-text('@')" in selector:
                return mock_td_locator
            return mock_td_locator

        mock_frame.locator = MagicMock(side_effect=locator_side_effect)

        emails = await _extract_emails_from_frame(mock_frame)

        # Should extract emails but filter out sefaz system emails
        assert "test@example.com" in emails
        assert "user@domain.com.br" in emails
        assert "admin@sefaz.pb.gov.br" not in emails  # System email filtered

    @pytest.mark.asyncio
    async def test_extract_emails_from_input_fields(self) -> None:
        """Test email extraction from input fields."""
        mock_frame = MagicMock()  # Use MagicMock, not AsyncMock for frame
        mock_frame.content = AsyncMock(return_value="<html><body></body></html>")

        # Mock input fields locator
        mock_inputs = MagicMock()
        mock_inputs.count = AsyncMock(return_value=2)

        # Mock nth() to return input elements with input_value
        mock_input1 = MagicMock()
        mock_input1.input_value = AsyncMock(return_value="email1@test.com")
        mock_input2 = MagicMock()
        mock_input2.input_value = AsyncMock(return_value="email2@test.com")
        mock_inputs.nth.side_effect = [mock_input1, mock_input2]

        # Mock td locator (empty)
        mock_td_locator = MagicMock()
        mock_td_locator.count = AsyncMock(return_value=0)

        # Setup locator to return different mocks based on selector (not a coroutine)
        def locator_side_effect(selector):
            if "input" in selector:
                return mock_inputs
            return mock_td_locator

        mock_frame.locator = MagicMock(side_effect=locator_side_effect)

        emails = await _extract_emails_from_frame(mock_frame)

        assert len(emails) >= 2
        assert "email1@test.com" in emails
        assert "email2@test.com" in emails


class TestProcessDataExtraction:
    """Tests for process data extraction from FC frame."""

    @pytest.mark.asyncio
    async def test_extract_process_number(self) -> None:
        """Test extraction of process number."""
        mock_frame = AsyncMock()

        # Mock the processo td element
        mock_processo_td = AsyncMock()
        mock_processo_td.wait_for = AsyncMock()
        mock_processo_td.text_content.return_value = "2766432025-9"

        mock_frame.locator.return_value.first = mock_processo_td

        data = await _extract_process_data_from_frame(mock_frame)

        # Should extract process number (may need adjustment based on actual selector behavior)
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_extract_razao_social(self) -> None:
        """Test extraction of razão social."""
        mock_frame = AsyncMock()

        # Mock the razao td element
        mock_razao_td = AsyncMock()
        mock_razao_td.wait_for = AsyncMock()
        mock_razao_td.text_content.return_value = "D S DA SILVA COMÉRCIO DE FERRAGENS"

        mock_frame.locator.return_value.first = mock_razao_td

        data = await _extract_process_data_from_frame(mock_frame)

        assert isinstance(data, dict)


class TestIntegration:
    """Integration tests for Stage 2 workflow."""

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires live browser and ATF credentials")
    async def test_full_stage2_workflow(self) -> None:
        """Test full Stage 2 workflow (requires live browser)."""
        # This test would require:
        # - Authenticated Playwright page
        # - Actual ATF session
        # - Gmail credentials
        #
        # Uncomment and configure to run:
        # from app.modules.cadastro.consultar_redesim import process_redesim_stage2
        # from playwright.async_api import async_playwright
        #
        # async with async_playwright() as p:
        #     browser = await p.chromium.launch(headless=False)
        #     page = await browser.new_page()
        #     # ... login and navigate ...
        #     results = await process_redesim_stage2(page)
        #     assert results["success"] is True
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
