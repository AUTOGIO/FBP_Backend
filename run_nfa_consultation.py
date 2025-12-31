#!/usr/bin/env python3
"""Simple runner script for NFA consultation automation.

This script runs the NFA consultation automation with default parameters.
Credentials are read from environment variables:
- NFA_USERNAME
- NFA_PASSWORD

Usage:
    export NFA_USERNAME='eduardof'
    export NFA_PASSWORD='atf101010'
    python run_nfa_consultation.py
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.modules.nfa_atf_automation import run_nfa_job

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger(__name__)


async def main():
    """Main entry point for NFA consultation automation."""
    logger.info("=" * 80)
    logger.info("NFA Consultation Automation - Starting")
    logger.info("=" * 80)
    
    # Get credentials from environment
    username = os.getenv("NFA_USERNAME")
    password = os.getenv("NFA_PASSWORD")
    
    if not username or not password:
        logger.error("ERROR: NFA_USERNAME and NFA_PASSWORD environment variables must be set")
        logger.error("Example:")
        logger.error("  export NFA_USERNAME='eduardof'")
        logger.error("  export NFA_PASSWORD='atf101010'")
        sys.exit(1)
    
    logger.info(f"Username: {username}")
    logger.info("Password: [REDACTED]")
    logger.info("Date range: 08/12/2025 to 08/12/2025")
    logger.info("Matrícula: 1595504")
    logger.info("Max NFAs: 15")
    logger.info("Wait between NFAs: 3 seconds")
    logger.info("=" * 80)
    
    # Run the automation
    result = await run_nfa_job(
        username=username,
        password=password,
        data_inicial="08/12/2025",
        data_final="08/12/2025",
        matricula="1595504",
        headless=False,  # Show browser for debugging
        max_nfas=15,
        wait_between_nfas=3,
    )
    
    # Check result
    if result["status"] == "ok":
        logger.info(f"✓ Automation completed successfully: {result['total_processed']} NFAs processed")
        sys.exit(0)
    else:
        logger.error(f"✗ Automation failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
