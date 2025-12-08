"""CEP Validator Module - REDESIM Email Extractor
Optimized for Apple M3 + SEFAZ-PB Workflow.

Implements Pareto Principle (80/20):
- 80% value: Automatic CEP validation + data enrichment
- 20% effort: Simple fallback system + minimal configuration
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
import yaml

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class CEPData:
    """Structured CEP data container."""

    cep: str
    logradouro: str | None = None
    bairro: str | None = None
    cidade: str | None = None
    uf: str | None = None
    ibge: str | None = None
    gia: str | None = None
    siafi: str | None = None
    lat: float | None = None
    lng: float | None = None
    valid: bool = False
    source: str | None = None
    error: str | None = None


class CEPValidator:
    """CEP Validator with fallback system
    Implements Pareto Principle: Simple, effective, reliable.
    """

    def __init__(self, config_path: str | None = None) -> None:
        """Initialize CEP validator with configuration."""
        self.config = self._load_config(config_path)
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "REDESIM-Email-Extractor/1.0 (SEFAZ-PB)"},
        )

        # Simple in-memory cache (Pareto: 80% of caching benefits with 20% complexity)
        self._cache: dict[str, CEPData] = {}
        self._cache_timestamps: dict[str, float] = {}

        logger.info("CEP Validator initialized with fallback system")

    def _load_config(self, config_path: str | None = None) -> dict:
        """Load configuration from YAML file."""
        if config_path is None:
            # Use FBP project root for config lookup
            project_root = Path(__file__).parent.parent.parent.parent
            config_path = project_root / "config" / "redesim.yaml"

        try:
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                return config.get("cep_apis", {})
            logger.warning(
                f"Config file not found at {config_path}. Using defaults.",
            )
            return self._get_default_config()
        except Exception as e:
            logger.warning(f"Could not load config: {e}. Using defaults.")
            return self._get_default_config()

    def _get_default_config(self) -> dict:
        """Default configuration following Pareto Principle."""
        return {
            "primary": {
                "name": "viacep",
                "url": "https://viacep.com.br/ws/{cep}/json/",
                "timeout": 5,
            },
            "backup": {
                "name": "awesomeapi",
                "url": "https://cep.awesomeapi.com.br/json/{cep}",
                "timeout": 5,
            },
        }

    def _normalize_cep(self, cep: str) -> str:
        """Normalize CEP format (remove spaces, dashes, etc.)."""
        if not cep:
            return ""

        # Remove all non-numeric characters
        normalized = re.sub(r"[^\d]", "", str(cep))

        # Ensure 8 digits
        if len(normalized) == 8:
            return normalized
        if len(normalized) == 9 and normalized[0] == "0":
            return normalized[1:]  # Remove leading zero
        return normalized

    def _is_valid_cep_format(self, cep: str) -> bool:
        """Validate CEP format (8 digits)."""
        normalized = self._normalize_cep(cep)
        return len(normalized) == 8 and normalized.isdigit()

    def _check_cache(self, cep: str) -> CEPData | None:
        """Check if CEP is in cache and still valid."""
        if not self.config.get("cep_validation", {}).get(
            "cache_results", True,
        ):
            return None

        cache_ttl = (
            self.config.get("cep_validation", {}).get("cache_ttl_hours", 24)
            * 3600
        )

        if cep in self._cache:
            timestamp = self._cache_timestamps.get(cep, 0)
            if time.time() - timestamp < cache_ttl:
                logger.debug(f"CEP {cep} found in cache")
                return self._cache[cep]
            # Remove expired cache entry
            del self._cache[cep]
            del self._cache_timestamps[cep]

        return None

    def _cache_result(self, cep: str, data: CEPData) -> None:
        """Cache CEP validation result."""
        if self.config.get("cep_validation", {}).get("cache_results", True):
            self._cache[cep] = data
            self._cache_timestamps[cep] = time.time()

    def _fetch_from_api(self, cep: str, api_config: dict) -> CEPData | None:
        """Fetch CEP data from specific API."""
        try:
            url = api_config["url"].format(cep=cep)
            timeout = api_config.get("timeout", 5)

            logger.debug(f"Fetching CEP {cep} from {api_config['name']}")

            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()

            data = response.json()

            # Handle different API response formats
            if api_config["name"] == "viacep":
                return self._parse_viacep_response(
                    cep, data, api_config["name"],
                )
            if api_config["name"] == "awesomeapi":
                return self._parse_awesomeapi_response(
                    cep, data, api_config["name"],
                )
            return self._parse_generic_response(
                cep, data, api_config["name"],
            )

        except Exception as e:
            logger.warning(
                f"API {api_config['name']} failed for CEP {cep}: {e}",
            )
            return None

    def _parse_viacep_response(
        self, cep: str, data: dict, source: str,
    ) -> CEPData:
        """Parse ViaCEP API response."""
        if data.get("erro"):
            return CEPData(
                cep=cep, valid=False, source=source, error="CEP not found",
            )

        return CEPData(
            cep=cep,
            logradouro=data.get("logradouro"),
            bairro=data.get("bairro"),
            cidade=data.get("localidade"),
            uf=data.get("uf"),
            ibge=data.get("ibge"),
            gia=data.get("gia"),
            siafi=data.get("siafi"),
            valid=True,
            source=source,
        )

    def _parse_awesomeapi_response(
        self, cep: str, data: dict, source: str,
    ) -> CEPData:
        """Parse AwesomeAPI response (includes coordinates)."""
        return CEPData(
            cep=cep,
            logradouro=data.get("address"),
            bairro=data.get("neighborhood"),
            cidade=data.get("city"),
            uf=data.get("state"),
            ibge=data.get("city_ibge"),
            lat=float(data.get("lat")) if data.get("lat") else None,
            lng=float(data.get("lng")) if data.get("lng") else None,
            valid=True,
            source=source,
        )

    def _parse_generic_response(
        self, cep: str, data: dict, source: str,
    ) -> CEPData:
        """Parse generic API response."""
        return CEPData(
            cep=cep,
            logradouro=data.get("logradouro") or data.get("address"),
            bairro=data.get("bairro") or data.get("neighborhood"),
            cidade=data.get("cidade")
            or data.get("city")
            or data.get("localidade"),
            uf=data.get("uf") or data.get("state"),
            ibge=data.get("ibge") or data.get("city_ibge"),
            valid=True,
            source=source,
        )

    def validate_cep(self, cep: str) -> CEPData:
        """Validate CEP with fallback system
        Implements Pareto Principle: 80% reliability with 20% complexity.
        """
        # Normalize CEP
        normalized_cep = self._normalize_cep(cep)

        # Check format
        if not self._is_valid_cep_format(normalized_cep):
            return CEPData(
                cep=cep, valid=False, error=f"Invalid CEP format: {cep}",
            )

        # Check cache first
        cached_result = self._check_cache(normalized_cep)
        if cached_result:
            return cached_result

        # Try APIs in order (Pareto: 80% success with primary API)
        apis_to_try = ["primary", "backup", "fallback"]

        for api_key in apis_to_try:
            if api_key not in self.config:
                continue

            api_config = self.config[api_key]
            result = self._fetch_from_api(normalized_cep, api_config)

            if result and result.valid:
                # Cache successful result
                self._cache_result(normalized_cep, result)
                logger.info(
                    f"CEP {cep} validated successfully via {api_config['name']}",
                )
                return result

            # Small delay between retries
            if api_key != apis_to_try[-1]:  # Don't delay on last attempt
                time.sleep(0.5)

        # All APIs failed
        error_result = CEPData(
            cep=cep, valid=False, error="All CEP APIs failed",
        )

        logger.error(f"All CEP APIs failed for {cep}")
        return error_result

    def get_coordinates(
        self, cep: str,
    ) -> tuple[float | None, float | None]:
        """Get coordinates for CEP (lat, lng)."""
        cep_data = self.validate_cep(cep)
        return cep_data.lat, cep_data.lng

    def enrich_company_data(self, company_data: dict) -> dict:
        """Enrich company data with CEP validation
        Pareto Principle: 80% value with minimal integration.
        """
        if "cep" not in company_data:
            return company_data

        cep_data = self.validate_cep(company_data["cep"])

        # Add CEP validation results
        company_data["cep_valid"] = cep_data.valid
        company_data["cep_source"] = cep_data.source

        if cep_data.valid:
            company_data["endereco_completo"] = (
                f"{cep_data.logradouro}, {cep_data.bairro}, {cep_data.cidade}-{cep_data.uf}"
            )
            company_data["codigo_ibge"] = cep_data.ibge
            company_data["codigo_gia"] = cep_data.gia
            company_data["codigo_siafi"] = cep_data.siafi

            if cep_data.lat and cep_data.lng:
                company_data["coordenadas"] = {
                    "latitude": cep_data.lat,
                    "longitude": cep_data.lng,
                }
        else:
            company_data["cep_error"] = cep_data.error

        return company_data

    def batch_validate(self, cep_list: list) -> dict[str, CEPData]:
        """Validate multiple CEPs efficiently."""
        results = {}

        for cep in cep_list:
            results[cep] = self.validate_cep(cep)
            # Small delay to be respectful to APIs
            time.sleep(0.1)

        return results

    def get_stats(self) -> dict[str, Any]:
        """Get validation statistics."""
        total_cached = len(self._cache)
        valid_results = sum(1 for data in self._cache.values() if data.valid)

        return {
            "total_cached": total_cached,
            "valid_results": valid_results,
            "invalid_results": total_cached - valid_results,
            "cache_hit_rate": f"{(total_cached / max(total_cached, 1)) * 100:.1f}%",
        }


# Convenience function for quick validation
def validate_cep(cep: str, config_path: str | None = None) -> CEPData:
    """Quick CEP validation function."""
    validator = CEPValidator(config_path)
    return validator.validate_cep(cep)
