"""REDESIM Stage 2 Automation - Full Workflow Execution.

Steps:
- Requires env vars ATF_USERNAME / ATF_PASSWORD
- Opens browser visible (headless=False) via Playwright
- Runs consultar_redesim to get results
- Then runs process_redesim_stage2 to:
  - Select checkbox in LISTA frame
  - Validate CEP via ViaCEP
  - Check contabilista CPF via CFC
  - Extract emails and create Gmail draft
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from app.modules.cadastro.consultar_redesim import (
    consultar_redesim,
    process_redesim_stage2,
)
from app.modules.nfa.atf_login import perform_login, wait_for_post_login
from app.modules.nfa.browser_launcher import launch_persistent_browser
from app.modules.nfa.screenshot_utils import save_screenshot

KEEP_OPEN_MS = 3_600_000  # 1h for inspection


async def main() -> None:
    user = os.getenv("ATF_USERNAME")
    pwd = os.getenv("ATF_PASSWORD")
    if not user or not pwd:
        raise RuntimeError("Set ATF_USERNAME and ATF_PASSWORD before running.")

    # Gmail credentials
    project_root = Path(__file__).parent.parent
    creds_path = (
        project_root / "app" / "modules" / "cad_redesim_consulta" / "credential_gmail"
    )
    token_path = project_root / "credentials" / "gmail_token.json"

    # Launch Playwright browser (headful for visual inspection)
    _, context, page = await launch_persistent_browser(headless=False, slow_mo=100)

    try:
        print("[🔹] Navigating to ATF...")
        await page.goto("https://www4.sefaz.pb.gov.br/atf/")

        print("[🔹] Logging in...")
        login_ok = await perform_login(page, username=user, password=pwd)
        if not login_ok:
            raise RuntimeError("Login failed; check credentials or connectivity.")

        print("[🔹] Validating session...")
        post_ok = await wait_for_post_login(page)
        if not post_ok:
            raise RuntimeError("Session not validated after login.")

        print("[🔹] Starting REDESIM consultation...")
        payload: dict = {
            # Mandatory date range (per user request)
            "data_criacao_inicio": "05/11/2025",
            "data_criacao_fim": "07/11/2025",
        }
        await consultar_redesim(page, payload, wait_user_dates=False)

        print("[🔹] Starting Stage 2 automation...")
        print("  → Selecting checkbox in LISTA frame...")
        print("  → Validating CEP via ViaCEP...")
        print("  → Checking contabilista via CFC...")
        print("  → Extracting emails...")
        print("  → Creating Gmail draft...")

        stage2_results = await process_redesim_stage2(
            page,
            gmail_credentials_path=str(creds_path) if creds_path.exists() else None,
            gmail_token_path=str(token_path) if token_path.exists() else None,
            row_index=0,
        )

        print("\n[✅] Stage 2 completed!")
        print(f"  Success: {stage2_results.get('success', False)}")
        print(f"  Errors: {len(stage2_results.get('errors', []))}")

        if stage2_results.get("output_file"):
            print(f"  Output file: {stage2_results['output_file']}")

        email_count = (
            stage2_results.get("steps", {}).get("email_extraction", {}).get("count", 0)
        )
        print(f"  Emails extracted: {email_count}")

        if stage2_results.get("steps", {}).get("gmail_draft", {}).get("success"):
            draft_info = stage2_results["steps"]["gmail_draft"]
            print(f"  Gmail draft ID: {draft_info.get('draft_id', 'N/A')}")
            print("  ✅ Draft created successfully!")
        else:
            print("  ⚠️  Gmail draft creation failed or no emails found")

        print("\n[⏸️] Keeping browser open for inspection (1 hour)...")
        await page.wait_for_timeout(KEEP_OPEN_MS)

    except Exception as err:
        print(f"\n[❌] Error: {err}")
        try:
            screenshots_dir = project_root / "output" / "nfa" / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            await save_screenshot(page, screenshots_dir, filename="runner_error.png")
            print(f"[📸] Screenshot saved: {screenshots_dir}/runner_error.png")
        except Exception:
            pass
        print("[⏸️] Keeping browser open for debugging (5 minutes)...")
        try:
            await page.wait_for_timeout(300_000)
        except Exception:
            pass
        raise


if __name__ == "__main__":
    asyncio.run(main())
