#!/usr/bin/env python3
"""
ATF System Explorer
Maps all links, features, and functionality of the SEFAZ ATF system.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.async_api import Page, async_playwright

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ATF Configuration
LOGIN_URL = "https://www4.sefaz.pb.gov.br/atf/seg/SEGf_Login.jsp"
BASE_URL = "https://www4.sefaz.pb.gov.br/atf"
USERNAME = "eduardof"
PASSWORD = "atf101010"

# Output directory
OUTPUT_DIR = Path(__file__).parent.parent / "output" / "atf_exploration"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


class ATFSystemExplorer:
    """Explores and maps the ATF system structure."""

    def __init__(self):
        self.visited_urls: set[str] = set()
        self.discovered_links: list[dict[str, Any]] = []
        self.features: list[dict[str, Any]] = []
        self.menu_structure: dict[str, Any] = {}
        self.screenshots: list[str] = []

    async def login(self, page: Page) -> bool:
        """Login to ATF system."""
        try:
            logger.info(f"Navigating to login page: {LOGIN_URL}")
            await page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=60000)
            await self.save_screenshot(page, "login_start")

            logger.info("Filling credentials...")
            await page.fill("input[name='edtNoLogin']", USERNAME)
            await page.fill("input[name='edtDsSenha']", PASSWORD)
            await self.save_screenshot(page, "login_filled")

            logger.info("Submitting login...")
            try:
                await page.evaluate("logarSistema()")
            except Exception as eval_error:
                logger.warning(f"logarSistema() evaluation failed: {eval_error}")
                await page.click("button[name='btnAvancar'], input[name='btnAvancar']")

            logger.info("Waiting for post-login navigation...")
            await page.wait_for_timeout(4000)
            await self.save_screenshot(page, "login_after_submit")

            # Wait for navigation away from login page (similar to atf_login.py)
            def _looks_logged_in(url: str) -> bool:
                return "SEGf_Login.jsp" not in (url or "")

            # Check current URL
            current_url = page.url
            logger.info(f"Current URL: {current_url}")

            # Try waiting for network idle
            try:
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass  # networkidle isn't guaranteed

            # Check URL again
            current_url = page.url
            if _looks_logged_in(current_url):
                logger.info(f"✅ Login successful. Current URL: {current_url}")
                await self.save_screenshot(page, "login_success")
                return True

            # Try probing authenticated endpoint
            menu_url = "https://www4.sefaz.pb.gov.br/atf/seg/SEGf_MontarMenu.jsp"
            try:
                resp = await page.request.get(menu_url, timeout=8000)
                final_url = getattr(resp, "url", "") or ""
                if resp.ok and _looks_logged_in(final_url):
                    logger.info("✅ Login validated via authenticated endpoint")
                    await self.save_screenshot(page, "login_success")
                    return True
            except Exception as probe_error:
                logger.debug(f"Probe failed: {probe_error}")

            # Final check
            current_url = page.url
            if "SEGf_Login.jsp" in current_url:
                logger.error("❌ Login failed - still on login page")
                await self.save_screenshot(page, "login_failed")
                return False

            logger.info(f"✅ Login successful. Current URL: {current_url}")
            await self.save_screenshot(page, "login_success")
            return True

        except Exception as e:
            logger.error(f"Login error: {e}", exc_info=True)
            await self.save_screenshot(page, "login_error")
            return False

    async def save_screenshot(self, page: Page, name: str) -> str:
        """Save screenshot and return path."""
        screenshot_path = (
            OUTPUT_DIR / f"{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        await page.screenshot(path=str(screenshot_path), full_page=True)
        self.screenshots.append(str(screenshot_path))
        return str(screenshot_path)

    async def extract_links(
        self, page: Page, context: str = ""
    ) -> list[dict[str, Any]]:
        """Extract all links from current page."""
        links = []

        try:
            # Extract links from main page
            main_links = await page.evaluate(
                """
                () => {
                    const links = [];
                    document.querySelectorAll('a[href]').forEach(a => {
                        links.push({
                            text: a.textContent.trim(),
                            href: a.href,
                            title: a.title || '',
                            target: a.target || ''
                        });
                    });
                    return links;
                }
                """
            )

            for link in main_links:
                if link["href"] and BASE_URL in link["href"]:
                    links.append(
                        {
                            "text": link["text"],
                            "url": link["href"],
                            "title": link["title"],
                            "target": link["target"],
                            "context": context,
                            "discovered_at": datetime.now().isoformat(),
                        }
                    )

            # Extract links from iframes
            frames = page.frames
            for frame in frames:
                try:
                    frame_links = await frame.evaluate(
                        """
                        () => {
                            const links = [];
                            document.querySelectorAll('a[href]').forEach(a => {
                                links.push({
                                    text: a.textContent.trim(),
                                    href: a.href,
                                    title: a.title || '',
                                    target: a.target || ''
                                });
                            });
                            return links;
                        }
                        """
                    )

                    for link in frame_links:
                        if link["href"] and BASE_URL in link["href"]:
                            links.append(
                                {
                                    "text": link["text"],
                                    "url": link["href"],
                                    "title": link["title"],
                                    "target": link["target"],
                                    "context": f"{context} (iframe: {frame.name or 'unnamed'})",
                                    "discovered_at": datetime.now().isoformat(),
                                }
                            )
                except Exception as e:
                    logger.debug(
                        f"Could not extract links from frame {frame.name}: {e}"
                    )

        except Exception as e:
            logger.warning(f"Error extracting links: {e}")

        return links

    async def extract_page_info(self, page: Page, url: str) -> dict[str, Any]:
        """Extract comprehensive information about current page."""
        try:
            info = {
                "url": url,
                "title": await page.title(),
                "timestamp": datetime.now().isoformat(),
            }

            # Extract page text content
            try:
                info["main_text"] = await page.evaluate(
                    "() => document.body.innerText.substring(0, 1000)"
                )
            except Exception:
                info["main_text"] = ""

            # Extract forms
            try:
                info["forms"] = await page.evaluate(
                    """
                    () => {
                        const forms = [];
                        document.querySelectorAll('form').forEach(form => {
                            forms.push({
                                name: form.name || '',
                                action: form.action || '',
                                method: form.method || '',
                                fields: Array.from(form.querySelectorAll('input, select, textarea')).map(f => ({
                                    type: f.type || f.tagName.toLowerCase(),
                                    name: f.name || '',
                                    id: f.id || ''
                                }))
                            });
                        });
                        return forms;
                    }
                    """
                )
            except Exception:
                info["forms"] = []

            # Extract tables
            try:
                info["tables"] = await page.evaluate(
                    """
                    () => {
                        const tables = [];
                        document.querySelectorAll('table').forEach((table, idx) => {
                            const headers = Array.from(table.querySelectorAll('th')).map(th => th.textContent.trim());
                            const rows = Array.from(table.querySelectorAll('tr')).slice(0, 5).map(tr => 
                                Array.from(tr.querySelectorAll('td')).map(td => td.textContent.trim())
                            );
                            tables.push({
                                index: idx,
                                headers: headers,
                                sample_rows: rows
                            });
                        });
                        return tables;
                    }
                    """
                )
            except Exception:
                info["tables"] = []

            # Extract buttons
            try:
                info["buttons"] = await page.evaluate(
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
                info["buttons"] = []

            return info

        except Exception as e:
            logger.warning(f"Error extracting page info for {url}: {e}")
            return {
                "url": url,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def explore_menu(self, page: Page) -> dict[str, Any]:
        """Explore the main menu structure."""
        logger.info("Exploring main menu...")
        menu_data = {}

        try:
            # Wait for menu to load
            await page.wait_for_timeout(3000)

            # Try to find menu frame
            frames = page.frames
            menu_frame = None
            for frame in frames:
                if "menu" in frame.name.lower() or "mainFrame" in frame.name:
                    menu_frame = frame
                    break

            if menu_frame:
                logger.info(f"Found menu frame: {menu_frame.name}")
                menu_links = await self.extract_links(menu_frame, "main_menu")
                menu_data["menu_links"] = menu_links
                menu_data["frame_name"] = menu_frame.name

                # Extract menu structure
                try:
                    menu_structure = await menu_frame.evaluate(
                        """
                        () => {
                            const structure = [];
                            document.querySelectorAll('a, li, tr').forEach(el => {
                                const text = el.textContent.trim();
                                if (text && text.length > 0) {
                                    structure.push({
                                        text: text,
                                        tag: el.tagName,
                                        href: el.href || el.querySelector('a')?.href || ''
                                    });
                                }
                            });
                            return structure;
                        }
                        """
                    )
                    menu_data["structure"] = menu_structure
                except Exception as e:
                    logger.warning(f"Could not extract menu structure: {e}")

            else:
                # Try to extract from main page
                logger.info("No menu frame found, extracting from main page")
                menu_links = await self.extract_links(page, "main_page")
                menu_data["menu_links"] = menu_links

        except Exception as e:
            logger.error(f"Error exploring menu: {e}", exc_info=True)

        return menu_data

    async def navigate_and_explore(
        self, page: Page, url: str, depth: int = 0, max_depth: int = 3
    ) -> dict[str, Any]:
        """Navigate to URL and explore its content."""
        if depth > max_depth or url in self.visited_urls:
            return {}

        self.visited_urls.add(url)
        logger.info(f"Exploring: {url} (depth: {depth})")

        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)

            page_info = await self.extract_page_info(page, url)
            links = await self.extract_links(page, f"depth_{depth}")

            # Add new links to discovered list
            for link in links:
                if link["url"] not in [l["url"] for l in self.discovered_links]:
                    self.discovered_links.append(link)

            # Save screenshot
            safe_name = (
                url.replace("https://", "").replace("/", "_").replace("?", "_")[:100]
            )
            await self.save_screenshot(page, f"page_{safe_name}")

            return {
                "url": url,
                "depth": depth,
                "page_info": page_info,
                "links": links,
            }

        except Exception as e:
            logger.warning(f"Error navigating to {url}: {e}")
            return {"url": url, "error": str(e), "depth": depth}

    async def explore_nfa_features(self, page: Page) -> dict[str, Any]:
        """Specifically explore NFA-related features."""
        logger.info("Exploring NFA features...")
        nfa_url = "https://www4.sefaz.pb.gov.br/atf/fis/FISf_EmitirNFAeReparticao.do?limparSessao=true"

        try:
            await page.goto(nfa_url, wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

            nfa_info = await self.extract_page_info(page, nfa_url)
            nfa_links = await self.extract_links(page, "nfa_form")

            # Extract form fields specific to NFA
            try:
                form_fields = await page.evaluate(
                    """
                    () => {
                        const fields = [];
                        document.querySelectorAll('input, select, textarea').forEach(field => {
                            fields.push({
                                type: field.type || field.tagName.toLowerCase(),
                                name: field.name || '',
                                id: field.id || '',
                                label: field.labels?.[0]?.textContent || field.getAttribute('title') || '',
                                required: field.required || false
                            });
                        });
                        return fields;
                    }
                    """
                )
                nfa_info["form_fields"] = form_fields
            except Exception as e:
                logger.warning(f"Could not extract NFA form fields: {e}")

            await self.save_screenshot(page, "nfa_form_detailed")

            return {
                "nfa_url": nfa_url,
                "page_info": nfa_info,
                "links": nfa_links,
            }

        except Exception as e:
            logger.error(f"Error exploring NFA features: {e}", exc_info=True)
            return {"error": str(e)}

    async def run_exploration(self) -> dict[str, Any]:
        """Run complete ATF system exploration."""
        logger.info("Starting ATF System Exploration...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Step 1: Login
                if not await self.login(page):
                    return {"error": "Login failed"}

                # Step 2: Explore main menu
                menu_data = await self.explore_menu(page)
                self.menu_structure = menu_data

                # Step 3: Explore NFA features specifically
                nfa_features = await self.explore_nfa_features(page)

                # Step 4: Explore key links from menu
                key_urls = [
                    "https://www4.sefaz.pb.gov.br/atf/seg/SEGf_MontarMenu.jsp",
                ]

                # Add URLs from discovered links (limit to avoid too many)
                for link in self.discovered_links[:20]:  # Limit exploration
                    if link["url"] not in key_urls:
                        key_urls.append(link["url"])

                explored_pages = []
                for url in key_urls[:10]:  # Limit to 10 pages
                    result = await self.navigate_and_explore(page, url, depth=1)
                    if result:
                        explored_pages.append(result)

                # Compile results
                exploration_results = {
                    "timestamp": datetime.now().isoformat(),
                    "base_url": BASE_URL,
                    "menu_structure": menu_data,
                    "nfa_features": nfa_features,
                    "discovered_links": self.discovered_links,
                    "explored_pages": explored_pages,
                    "total_links_discovered": len(self.discovered_links),
                    "total_pages_explored": len(explored_pages),
                    "screenshots": self.screenshots,
                }

                return exploration_results

            finally:
                await browser.close()

    def save_results(self, results: dict[str, Any]) -> Path:
        """Save exploration results to JSON file."""
        output_file = (
            OUTPUT_DIR
            / f"atf_exploration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        logger.info(f"Results saved to: {output_file}")
        return output_file


async def main():
    """Main execution function."""
    explorer = ATFSystemExplorer()
    results = await explorer.run_exploration()

    if "error" not in results:
        output_file = explorer.save_results(results)
        print("\n✅ Exploration complete!")
        print(f"📊 Total links discovered: {results['total_links_discovered']}")
        print(f"📄 Total pages explored: {results['total_pages_explored']}")
        print(f"💾 Results saved to: {output_file}")
    else:
        print(f"\n❌ Exploration failed: {results['error']}")


if __name__ == "__main__":
    asyncio.run(main())
