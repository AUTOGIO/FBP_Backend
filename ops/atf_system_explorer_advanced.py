#!/usr/bin/env python3
"""
ATF System Explorer - Advanced Version
Comprehensive system exploration with best practices:
- Recursive deep navigation
- Rate limiting and respectful crawling
- Robust error handling and retry logic
- Structured data extraction
- Progress tracking and reporting
- Configuration management
- Type safety
- Pattern detection
- Flow analysis
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urljoin, urlparse

try:
    import yaml
except ImportError:
    yaml = None

from playwright.async_api import Page, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(funcName)s:%(lineno)d] - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
LOGIN_URL = "https://www4.sefaz.pb.gov.br/atf/seg/SEGf_Login.jsp"
BASE_URL = "https://www4.sefaz.pb.gov.br/atf"
USERNAME = "eduardof"
PASSWORD = "atf101010"

# Exploration settings
MAX_DEPTH = 5  # Maximum navigation depth
MAX_PAGES_PER_DEPTH = 50  # Limit pages per depth level
RATE_LIMIT_DELAY = 1.0  # Seconds between requests
REQUEST_TIMEOUT = 30000  # Milliseconds
MAX_RETRIES = 3
RETRY_DELAY = 2.0  # Seconds

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "atf_exploration"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class PageType(Enum):
    """Types of pages discovered."""

    LOGIN = "login"
    MENU = "menu"
    FORM = "form"
    LIST = "list"
    DETAIL = "detail"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


class ExplorationStatus(Enum):
    """Status of page exploration."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class LinkInfo:
    """Structured link information."""

    text: str
    url: str
    title: str
    target: str
    context: str
    discovered_at: str
    depth: int = 0
    parent_url: str = ""
    link_type: str = "unknown"  # internal, external, javascript, etc.

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class FormField:
    """Structured form field information."""

    type: str
    name: str
    id: str
    label: str
    required: bool
    placeholder: str = ""
    value: str = ""
    options: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class PageInfo:
    """Comprehensive page information."""

    url: str
    title: str
    timestamp: str
    page_type: PageType
    status: ExplorationStatus
    depth: int
    main_text: str = ""
    forms: list[dict[str, Any]] = field(default_factory=list)
    form_fields: list[FormField] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    buttons: list[dict[str, Any]] = field(default_factory=list)
    links: list[LinkInfo] = field(default_factory=list)
    iframes: list[str] = field(default_factory=list)
    error: Optional[str] = None
    load_time: float = 0.0
    screenshot_path: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["page_type"] = self.page_type.value
        data["status"] = self.status.value
        data["form_fields"] = [f.to_dict() for f in self.form_fields]
        data["links"] = [l.to_dict() for l in self.links]
        return data


@dataclass
class ExplorationStats:
    """Exploration statistics."""

    total_pages_discovered: int = 0
    total_pages_explored: int = 0
    total_links_discovered: int = 0
    total_forms_found: int = 0
    total_errors: int = 0
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: float = 0.0
    pages_by_type: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    pages_by_depth: dict[int, int] = field(default_factory=lambda: defaultdict(int))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            **asdict(self),
            "pages_by_type": dict(self.pages_by_type),
            "pages_by_depth": dict(self.pages_by_depth),
        }


class ATFSystemExplorerAdvanced:
    """Advanced ATF system explorer with best practices."""

    def __init__(
        self,
        max_depth: int = MAX_DEPTH,
        rate_limit: float = RATE_LIMIT_DELAY,
        max_pages_per_depth: int = MAX_PAGES_PER_DEPTH,
        config_file: Optional[Path] = None,
    ):
        """Initialize explorer with configuration."""
        # Load config if provided
        self.config = self._load_config(config_file) if config_file else {}

        self.max_depth = self.config.get("max_depth", max_depth)
        self.rate_limit = self.config.get("rate_limit_delay", rate_limit)
        self.max_pages_per_depth = self.config.get(
            "max_pages_per_depth", max_pages_per_depth
        )
        self.skip_patterns = self.config.get("skip_patterns", [])
        self.priority_patterns = self.config.get("priority_patterns", [])

        # State management
        self.visited_urls: set[str] = set()
        self.pending_urls: list[tuple[str, int]] = []  # (url, depth)
        self.page_data: dict[str, PageInfo] = {}
        self.link_registry: list[LinkInfo] = []
        self.stats = ExplorationStats()

        # Rate limiting
        self.last_request_time: float = 0.0

        # Screenshots
        self.screenshots: list[str] = []

        # Pattern detection
        self.url_patterns: dict[str, list[str]] = defaultdict(list)
        self.form_patterns: dict[str, int] = defaultdict(int)

    def _load_config(self, config_file: Optional[Path]) -> dict[str, Any]:
        """Load configuration from YAML file."""
        if not config_file or not config_file.exists():
            return {}

        if yaml is None:
            logger.warning("PyYAML not installed, using defaults")
            return {}

        try:
            with open(config_file, encoding="utf-8") as f:
                config = yaml.safe_load(f)
                # Flatten nested config
                exploration = config.get("exploration", {})
                filters = config.get("filters", {})
                return {
                    **exploration,
                    "skip_patterns": filters.get("skip_patterns", []),
                    "priority_patterns": filters.get("priority_patterns", []),
                }
        except Exception as e:
            logger.warning(f"Failed to load config: {e}")
            return {}

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()

    async def _save_screenshot(self, page: Page, name: str) -> str:
        """Save screenshot with timestamp."""
        screenshot_path = (
            OUTPUT_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        try:
            await page.screenshot(path=str(screenshot_path), full_page=True)
            self.screenshots.append(str(screenshot_path))
            return str(screenshot_path)
        except Exception as e:
            logger.warning(f"Failed to save screenshot {name}: {e}")
            return ""

    async def _login(self, page: Page) -> bool:
        """Login to ATF system with retry logic."""
        for attempt in range(MAX_RETRIES):
            try:
                logger.info(f"Login attempt {attempt + 1}/{MAX_RETRIES}")
                await self._rate_limit()

                await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
                await self._save_screenshot(page, "login_start")

                await page.fill("input[name='edtNoLogin']", USERNAME)
                await page.fill("input[name='edtDsSenha']", PASSWORD)
                await self._save_screenshot(page, "login_filled")

                try:
                    await page.evaluate("logarSistema()")
                except Exception as eval_error:
                    logger.warning(f"logarSistema() failed: {eval_error}")
                    await page.click(
                        "button[name='btnAvancar'], input[name='btnAvancar']"
                    )

                await page.wait_for_timeout(4000)
                await self._save_screenshot(page, "login_after_submit")

                # Validate login
                def _looks_logged_in(url: str) -> bool:
                    return "SEGf_Login.jsp" not in (url or "")

                current_url = page.url
                if _looks_logged_in(current_url):
                    logger.info(f"✅ Login successful: {current_url}")
                    await self._save_screenshot(page, "login_success")
                    return True

                # Probe authenticated endpoint
                menu_url = "https://www4.sefaz.pb.gov.br/atf/seg/SEGf_MontarMenu.jsp"
                try:
                    resp = await page.request.get(menu_url, timeout=8000)
                    final_url = getattr(resp, "url", "") or ""
                    if resp.ok and _looks_logged_in(final_url):
                        logger.info("✅ Login validated via endpoint")
                        await self._save_screenshot(page, "login_success")
                        return True
                except Exception:
                    pass

                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Login failed, retrying in {RETRY_DELAY}s...")
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    logger.error("❌ Login failed after all retries")
                    await self._save_screenshot(page, "login_failed")
                    return False

            except Exception as e:
                logger.error(f"Login error (attempt {attempt + 1}): {e}", exc_info=True)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    await self._save_screenshot(page, "login_error")
                    return False

        return False

    def _classify_page_type(self, url: str, title: str, main_text: str) -> PageType:
        """Classify page type based on URL, title, and content."""
        url_lower = url.lower()
        text_lower = main_text.lower()
        title_lower = title.lower()

        if "login" in url_lower:
            return PageType.LOGIN
        if "menu" in url_lower or "montar" in url_lower:
            return PageType.MENU
        if "form" in url_lower or "incluir" in url_lower or "emitir" in url_lower:
            return PageType.FORM
        if (
            "listar" in url_lower
            or "consultar" in url_lower
            or "pesquisar" in url_lower
        ):
            return PageType.LIST
        if "detalhe" in url_lower or "visualizar" in url_lower:
            return PageType.DETAIL
        if "pdf" in url_lower or "download" in url_lower or "documento" in text_lower:
            return PageType.DOCUMENT
        return PageType.UNKNOWN

    async def _extract_links_advanced(
        self, page: Page, context: str = "", depth: int = 0, parent_url: str = ""
    ) -> list[LinkInfo]:
        """Extract links with advanced classification."""
        links: list[LinkInfo] = []
        base_domain = urlparse(BASE_URL).netloc

        try:
            # Extract from main page
            main_links = await page.evaluate(
                """
                () => {
                    const links = [];
                    document.querySelectorAll('a[href]').forEach(a => {
                        const href = a.href || a.getAttribute('href') || '';
                        links.push({
                            text: a.textContent.trim(),
                            href: href,
                            title: a.title || '',
                            target: a.target || '',
                            onclick: a.getAttribute('onclick') || ''
                        });
                    });
                    return links;
                }
                """
            )

            for link_data in main_links:
                href = link_data.get("href", "")
                if not href:
                    continue

                # Classify link type
                link_type = "unknown"
                if href.startswith("javascript:") or link_data.get("onclick"):
                    link_type = "javascript"
                elif href.startswith("#"):
                    link_type = "anchor"
                elif BASE_URL in href or href.startswith("/"):
                    link_type = "internal"
                else:
                    parsed = urlparse(href)
                    if parsed.netloc and parsed.netloc != base_domain:
                        link_type = "external"

                # Only process internal links
                if link_type in ("internal", "anchor"):
                    full_url = urljoin(BASE_URL, href) if href.startswith("/") else href

                    link_info = LinkInfo(
                        text=link_data.get("text", ""),
                        url=full_url,
                        title=link_data.get("title", ""),
                        target=link_data.get("target", ""),
                        context=context,
                        discovered_at=datetime.now().isoformat(),
                        depth=depth,
                        parent_url=parent_url,
                        link_type=link_type,
                    )
                    links.append(link_info)

            # Extract from all iframes
            frames = page.frames
            for frame in frames:
                try:
                    frame_links = await frame.evaluate(
                        """
                        () => {
                            const links = [];
                            document.querySelectorAll('a[href]').forEach(a => {
                                const href = a.href || a.getAttribute('href') || '';
                                links.push({
                                    text: a.textContent.trim(),
                                    href: href,
                                    title: a.title || '',
                                    target: a.target || '',
                                    onclick: a.getAttribute('onclick') || ''
                                });
                            });
                            return links;
                        }
                        """
                    )

                    for link_data in frame_links:
                        href = link_data.get("href", "")
                        if not href:
                            continue

                        link_type = "unknown"
                        if href.startswith("javascript:") or link_data.get("onclick"):
                            link_type = "javascript"
                        elif href.startswith("#"):
                            link_type = "anchor"
                        elif BASE_URL in href or href.startswith("/"):
                            link_type = "internal"
                        else:
                            parsed = urlparse(href)
                            if parsed.netloc and parsed.netloc != base_domain:
                                link_type = "external"

                        if link_type in ("internal", "anchor"):
                            full_url = (
                                urljoin(BASE_URL, href)
                                if href.startswith("/")
                                else href
                            )

                            link_info = LinkInfo(
                                text=link_data.get("text", ""),
                                url=full_url,
                                title=link_data.get("title", ""),
                                target=link_data.get("target", ""),
                                context=f"{context} (iframe: {frame.name or 'unnamed'})",
                                discovered_at=datetime.now().isoformat(),
                                depth=depth,
                                parent_url=parent_url,
                                link_type=link_type,
                            )
                            links.append(link_info)

                except Exception as e:
                    logger.debug(
                        f"Could not extract links from frame {frame.name}: {e}"
                    )

        except Exception as e:
            logger.warning(f"Error extracting links: {e}")

        return links

    async def _extract_form_fields_advanced(self, page: Page) -> list[FormField]:
        """Extract form fields with detailed information."""
        try:
            fields_data = await page.evaluate(
                """
                () => {
                    const fields = [];
                    document.querySelectorAll('input, select, textarea').forEach(field => {
                        const label = field.labels?.[0]?.textContent || 
                                     field.getAttribute('title') || 
                                     field.getAttribute('placeholder') || 
                                     field.previousElementSibling?.textContent || '';
                        
                        let options = [];
                        if (field.tagName === 'SELECT') {
                            options = Array.from(field.options).map(opt => opt.textContent.trim());
                        }
                        
                        fields.push({
                            type: field.type || field.tagName.toLowerCase(),
                            name: field.name || '',
                            id: field.id || '',
                            label: label.trim(),
                            required: field.required || false,
                            placeholder: field.placeholder || '',
                            value: field.value || '',
                            options: options
                        });
                    });
                    return fields;
                }
                """
            )

            return [FormField(**field_data) for field_data in fields_data]

        except Exception as e:
            logger.warning(f"Error extracting form fields: {e}")
            return []

    async def _extract_page_info_advanced(
        self, page: Page, url: str, depth: int
    ) -> PageInfo:
        """Extract comprehensive page information."""
        start_time = time.time()

        try:
            await self._rate_limit()

            await page.goto(url, wait_until="domcontentloaded", timeout=REQUEST_TIMEOUT)
            await page.wait_for_load_state("networkidle", timeout=10000)

            load_time = time.time() - start_time

            # Extract basic info
            title = await page.title()

            # Extract main text
            try:
                main_text = await page.evaluate(
                    "() => document.body.innerText.substring(0, 2000)"
                )
            except Exception:
                main_text = ""

            # Classify page type
            page_type = self._classify_page_type(url, title, main_text)

            # Extract forms
            forms = []
            try:
                forms = await page.evaluate(
                    """
                    () => {
                        const forms = [];
                        document.querySelectorAll('form').forEach((form, idx) => {
                            forms.push({
                                index: idx,
                                name: form.name || '',
                                action: form.action || '',
                                method: form.method || 'GET',
                                fields_count: form.querySelectorAll('input, select, textarea').length
                            });
                        });
                        return forms;
                    }
                    """
                )
            except Exception:
                pass

            # Extract form fields
            form_fields = await self._extract_form_fields_advanced(page)

            # Extract tables
            tables = []
            try:
                tables = await page.evaluate(
                    """
                    () => {
                        const tables = [];
                        document.querySelectorAll('table').forEach((table, idx) => {
                            const headers = Array.from(table.querySelectorAll('th')).map(th => th.textContent.trim());
                            const rowCount = table.querySelectorAll('tr').length;
                            tables.push({
                                index: idx,
                                headers: headers,
                                row_count: rowCount
                            });
                        });
                        return tables;
                    }
                    """
                )
            except Exception:
                pass

            # Extract buttons
            buttons = []
            try:
                buttons = await page.evaluate(
                    """
                    () => {
                        const buttons = [];
                        document.querySelectorAll('button, input[type="button"], input[type="submit"]').forEach(btn => {
                            buttons.push({
                                text: btn.value || btn.textContent.trim(),
                                type: btn.type || 'button',
                                name: btn.name || '',
                                id: btn.id || ''
                            });
                        });
                        return buttons;
                    }
                    """
                )
            except Exception:
                pass

            # Extract iframes
            iframes = []
            try:
                iframes = await page.evaluate(
                    """
                    () => {
                        const iframes = [];
                        document.querySelectorAll('iframe, frame').forEach(frame => {
                            iframes.push(frame.name || frame.id || 'unnamed');
                        });
                        return iframes;
                    }
                    """
                )
            except Exception:
                pass

            # Extract links
            links = await self._extract_links_advanced(
                page, f"depth_{depth}", depth, url
            )

            page_info = PageInfo(
                url=url,
                title=title,
                timestamp=datetime.now().isoformat(),
                page_type=page_type,
                status=ExplorationStatus.COMPLETED,
                depth=depth,
                main_text=main_text,
                forms=forms,
                form_fields=form_fields,
                tables=tables,
                buttons=buttons,
                links=links,
                iframes=iframes,
                load_time=load_time,
            )

            # Save screenshot
            safe_name = (
                url.replace("https://", "").replace("/", "_").replace("?", "_")[:100]
            )
            screenshot_path = await self._save_screenshot(page, f"page_{safe_name}")
            page_info.screenshot_path = screenshot_path

            return page_info

        except PlaywrightTimeoutError as e:
            logger.warning(f"Timeout exploring {url}: {e}")
            return PageInfo(
                url=url,
                title="",
                timestamp=datetime.now().isoformat(),
                page_type=PageType.UNKNOWN,
                status=ExplorationStatus.FAILED,
                depth=depth,
                error=f"Timeout: {str(e)}",
                load_time=time.time() - start_time,
            )

        except Exception as e:
            logger.error(f"Error exploring {url}: {e}", exc_info=True)
            return PageInfo(
                url=url,
                title="",
                timestamp=datetime.now().isoformat(),
                page_type=PageType.UNKNOWN,
                status=ExplorationStatus.FAILED,
                depth=depth,
                error=str(e),
                load_time=time.time() - start_time,
            )

    def _should_skip_url(self, url: str) -> bool:
        """Check if URL should be skipped based on patterns."""
        url_lower = url.lower()
        for pattern in self.skip_patterns:
            if pattern.lower() in url_lower:
                return True
        return False

    def _get_url_priority(self, url: str) -> int:
        """Calculate URL priority based on patterns."""
        url_lower = url.lower()
        priority = 0
        for pattern in self.priority_patterns:
            if pattern.lower() in url_lower:
                priority += 1
        return priority

    async def _explore_recursive(
        self, page: Page, url: str, depth: int = 0
    ) -> Optional[PageInfo]:
        """Recursively explore pages with depth control."""
        # Skip if already visited or max depth reached
        if url in self.visited_urls or depth > self.max_depth:
            return None

        # Check skip patterns
        if self._should_skip_url(url):
            logger.debug(f"Skipping URL (matches skip pattern): {url}")
            return None

        # Check depth limits
        if depth > 0:
            depth_count = sum(1 for p in self.page_data.values() if p.depth == depth)
            if depth_count >= self.max_pages_per_depth:
                logger.info(f"Reached max pages for depth {depth}, skipping {url}")
                return None

        self.visited_urls.add(url)
        self.stats.total_pages_discovered += 1

        logger.info(f"Exploring: {url} (depth: {depth})")

        try:
            page_info = await self._extract_page_info_advanced(page, url, depth)

            self.page_data[url] = page_info
            self.stats.total_pages_explored += 1
            self.stats.pages_by_type[page_info.page_type.value] += 1
            self.stats.pages_by_depth[depth] += 1

            if page_info.forms:
                self.stats.total_forms_found += len(page_info.forms)

            # Register links
            for link in page_info.links:
                if link.url not in [l.url for l in self.link_registry]:
                    self.link_registry.append(link)
                    self.stats.total_links_discovered += 1

            # Detect URL patterns
            url_path = urlparse(url).path
            if url_path:
                # Extract pattern (e.g., /atf/fis/FISf_*.do)
                pattern = re.sub(r"/[^/]+\.do", "/*.do", url_path)
                self.url_patterns[pattern].append(url)

            # Detect form patterns
            for form in page_info.forms:
                action = form.get("action", "")
                if action:
                    self.form_patterns[action] += 1

            # Add new links to pending queue (if within depth limit)
            if depth < self.max_depth:
                # Sort links by priority
                prioritized_links = sorted(
                    page_info.links,
                    key=lambda l: self._get_url_priority(l.url),
                    reverse=True,
                )

                for link in prioritized_links:
                    if (
                        link.link_type == "internal"
                        and link.url not in self.visited_urls
                        and link.url not in [u for u, _ in self.pending_urls]
                        and not self._should_skip_url(link.url)
                    ):
                        self.pending_urls.append((link.url, depth + 1))

            if page_info.error:
                self.stats.total_errors += 1

            return page_info

        except Exception as e:
            logger.error(f"Error in recursive exploration of {url}: {e}", exc_info=True)
            self.stats.total_errors += 1
            return None

    async def run_exploration(self) -> dict[str, Any]:
        """Run complete ATF system exploration."""
        logger.info("=" * 80)
        logger.info("Starting Advanced ATF System Exploration")
        logger.info("=" * 80)

        self.stats.start_time = datetime.now().isoformat()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            )
            page = await context.new_page()

            try:
                # Step 1: Login
                if not await self._login(page):
                    return {"error": "Login failed", "stats": self.stats.to_dict()}

                # Step 2: Start with menu page
                menu_url = "https://www4.sefaz.pb.gov.br/atf/seg/SEGf_MontarMenu.jsp"
                self.pending_urls.append((menu_url, 0))

                # Step 3: Explore NFA form specifically
                nfa_url = "https://www4.sefaz.pb.gov.br/atf/fis/FISf_EmitirNFAeReparticao.do?limparSessao=true"
                self.pending_urls.append((nfa_url, 0))

                # Step 4: Process pending URLs recursively
                while self.pending_urls:
                    url, depth = self.pending_urls.pop(0)
                    await self._explore_recursive(page, url, depth)

                    # Small delay between pages
                    await asyncio.sleep(0.5)

                self.stats.end_time = datetime.now().isoformat()
                self.stats.duration_seconds = (
                    datetime.fromisoformat(self.stats.end_time)
                    - datetime.fromisoformat(self.stats.start_time)
                ).total_seconds()

                logger.info("=" * 80)
                logger.info("Exploration Complete!")
                logger.info(f"Pages discovered: {self.stats.total_pages_discovered}")
                logger.info(f"Pages explored: {self.stats.total_pages_explored}")
                logger.info(f"Links discovered: {self.stats.total_links_discovered}")
                logger.info(f"Forms found: {self.stats.total_forms_found}")
                logger.info(f"Errors: {self.stats.total_errors}")
                logger.info(f"Duration: {self.stats.duration_seconds:.2f}s")
                logger.info("=" * 80)

                return {
                    "timestamp": datetime.now().isoformat(),
                    "base_url": BASE_URL,
                    "configuration": {
                        "max_depth": self.max_depth,
                        "rate_limit": self.rate_limit,
                        "max_pages_per_depth": self.max_pages_per_depth,
                    },
                    "stats": self.stats.to_dict(),
                    "pages": {
                        url: info.to_dict() for url, info in self.page_data.items()
                    },
                    "links": [link.to_dict() for link in self.link_registry],
                    "patterns": {
                        "url_patterns": dict(self.url_patterns),
                        "form_patterns": dict(self.form_patterns),
                    },
                    "screenshots": self.screenshots,
                }

            finally:
                await browser.close()

    def save_results(self, results: dict[str, Any]) -> Path:
        """Save exploration results to JSON file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = OUTPUT_DIR / f"atf_exploration_advanced_{timestamp}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        logger.info(f"Results saved to: {output_file}")
        return output_file

    def generate_summary_report(self, results: dict[str, Any]) -> str:
        """Generate human-readable summary report."""
        stats = results.get("stats", {})
        patterns = results.get("patterns", {})

        report = f"""# ATF System Exploration - Advanced Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Base URL**: {results.get('base_url', 'N/A')}

## Statistics

- **Pages Discovered**: {stats.get('total_pages_discovered', 0)}
- **Pages Explored**: {stats.get('total_pages_explored', 0)}
- **Links Discovered**: {stats.get('total_links_discovered', 0)}
- **Forms Found**: {stats.get('total_forms_found', 0)}
- **Errors**: {stats.get('total_errors', 0)}
- **Duration**: {stats.get('duration_seconds', 0):.2f} seconds

## Pages by Type

"""
        for page_type, count in stats.get("pages_by_type", {}).items():
            report += f"- **{page_type}**: {count}\n"

        report += "\n## Pages by Depth\n\n"
        for depth, count in sorted(stats.get("pages_by_depth", {}).items()):
            report += f"- **Depth {depth}**: {count}\n"

        # URL Patterns
        url_patterns = patterns.get("url_patterns", {})
        if url_patterns:
            report += "\n## Discovered URL Patterns\n\n"
            for pattern, urls in sorted(
                url_patterns.items(), key=lambda x: len(x[1]), reverse=True
            )[:10]:
                report += f"- **{pattern}**: {len(urls)} occurrences\n"

        # Form Patterns
        form_patterns = patterns.get("form_patterns", {})
        if form_patterns:
            report += "\n## Form Action Patterns\n\n"
            for action, count in sorted(
                form_patterns.items(), key=lambda x: x[1], reverse=True
            )[:10]:
                report += f"- **{action}**: {count} forms\n"

        report += f"\n## Screenshots\n\n{len(results.get('screenshots', []))} screenshots captured.\n"

        # Top pages by links
        pages = results.get("pages", {})
        if pages:
            report += "\n## Top Pages by Link Count\n\n"
            page_links = [
                (url, len(info.get("links", []))) for url, info in pages.items()
            ]
            for url, link_count in sorted(page_links, key=lambda x: x[1], reverse=True)[
                :10
            ]:
                report += f"- **{url}**: {link_count} links\n"

        return report


async def main():
    """Main execution function."""
    # Try to load config file
    config_file = Path(__file__).parent / "atf_explorer_config.yaml"
    config_file = config_file if config_file.exists() else None

    explorer = ATFSystemExplorerAdvanced(
        max_depth=MAX_DEPTH,
        rate_limit=RATE_LIMIT_DELAY,
        max_pages_per_depth=MAX_PAGES_PER_DEPTH,
        config_file=config_file,
    )

    results = await explorer.run_exploration()

    if "error" not in results:
        output_file = explorer.save_results(results)
        summary = explorer.generate_summary_report(results)

        # Save summary
        summary_file = output_file.with_suffix(".md")
        with open(summary_file, "w", encoding="utf-8") as f:
            f.write(summary)

        print("\n✅ Exploration complete!")
        print(f"📊 Pages explored: {results['stats']['total_pages_explored']}")
        print(f"🔗 Links discovered: {results['stats']['total_links_discovered']}")
        print(f"📝 Forms found: {results['stats']['total_forms_found']}")
        print(f"💾 Results: {output_file}")
        print(f"📄 Summary: {summary_file}")
    else:
        print(f"\n❌ Exploration failed: {results['error']}")


if __name__ == "__main__":
    asyncio.run(main())
