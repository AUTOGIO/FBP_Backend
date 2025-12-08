"""REDESIM Email Extraction Module.

Core logic for REDESIM email extraction and automation.
"""

from app.modules.redesim.auto_extractor import ATFAutoExtractor
from app.modules.redesim.browser_extractor import BrowserExtractor
from app.modules.redesim.data_extractor import REDESIMDataExtractor
from app.modules.redesim.devtools_extractor import DeveloperToolsExtractor
from app.modules.redesim.draft_creator import GmailService
from app.modules.redesim.email_client import GmailClient
from app.modules.redesim.email_collector import (
    extract_emails_from_html,
    extract_specific_emails,
)
from app.modules.redesim.email_extractor import EmailExtractor
from app.modules.redesim.extractor import REDESIMExtractor
from app.modules.redesim.playwright_extractor import PlaywrightExtractor

__all__ = [
    "ATFAutoExtractor",
    "BrowserExtractor",
    "DeveloperToolsExtractor",
    "EmailExtractor",
    "GmailClient",
    "GmailService",
    "PlaywrightExtractor",
    "REDESIMDataExtractor",
    "REDESIMExtractor",
    "extract_emails_from_html",
    "extract_specific_emails",
]
