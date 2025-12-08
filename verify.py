import asyncio
import sys

from playwright.async_api import Error, async_playwright


async def main() -> None:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://www.google.com", wait_until="networkidle")
        print("Chromium reinstall successful")
        await browser.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Error as exc:
        sys.stderr.write(f"Playwright error: {exc}\n")
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(f"Unexpected error: {exc}\n")
        sys.exit(1)
