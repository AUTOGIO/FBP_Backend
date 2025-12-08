from pathlib import Path

import pytest
from playwright.async_api import async_playwright

HTML_DOC = """
<!doctype html>
<html>
  <body>
    <input id="target" name="NaturezaOperacao" />
    <iframe id="frame" srcdoc="<input id='deep-input' />"></iframe>
  </body>
</html>
"""


@pytest.mark.asyncio
async def test_fallback_extension_injected_and_fills(tmp_path):
    ext_path = Path(__file__).resolve().parents[1] / "fallback_extension"
    assert ext_path.exists(), "fallback_extension directory must exist"

    async with async_playwright() as p:
        user_data_dir = tmp_path / "user-data"

        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            args=[
                f"--disable-extensions-except={ext_path}",
                f"--load-extension={ext_path}",
            ],
        )

        page = await context.new_page()

        async def _serve_html(route):
            await route.fulfill(
                status=200,
                body=HTML_DOC,
                headers={"content-type": "text/html"},
            )

        await context.route("**/*", _serve_html)

        await page.goto(
            "https://www4.sefaz.pb.gov.br/atf/test",
            wait_until="domcontentloaded",
        )
        await page.wait_for_function("() => !!window.nfaFallback", timeout=5000)

        # Basic fill
        fill_result = await page.evaluate(
            "() => window.nfaFallback.fill('#target', 'ABC123')"
        )
        assert fill_result.get("ok"), fill_result
        value = await page.evaluate("() => document.querySelector('#target').value")
        assert value == "ABC123"

        # Deep iframe query
        deep_found = await page.evaluate(
            "() => !!window.nfaFallback.queryDeep('#deep-input')"
        )
        assert deep_found is True

        # Bulk fill
        bulk_result = await page.evaluate(
            "(fields) => window.nfaFallback.tryFillAll(fields)",
            {"#target": "XYZ789"},
        )
        assert bulk_result.get("ok"), bulk_result
        new_value = await page.evaluate("() => document.querySelector('#target').value")
        assert new_value == "XYZ789"

        await context.close()
