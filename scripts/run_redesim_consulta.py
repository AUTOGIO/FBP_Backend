"""Manual runner for REDESIM consulta (ATF headful).

Steps:
- Requires env vars ATF_USERNAME / ATF_PASSWORD
- Opens browser visible (headless=False)
- Automatically fills form and submits consultation
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.modules.cadastro.consultar_redesim import (
        consultar_redesim,
        process_redesim_stage2,
        ELEMENT_TIMEOUT,
    )
    from app.modules.nfa.atf_login import perform_login, wait_for_post_login
    from app.modules.nfa.browser_launcher import launch_persistent_browser
    from app.modules.nfa.screenshot_utils import save_screenshot
    import logging

    logger = logging.getLogger(__name__)
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(
        f"   Make sure you're running from the project root and dependencies are installed."
    )
    sys.exit(1)

KEEP_OPEN_MS = 3_600_000  # 1h para inspeção manual
FAST_TIMEOUT = 10000  # 10s timeout
FAST_DEFAULT_DELAY = 300  # 300ms delay
FAST_SEARCH_DELAY = 500  # 500ms delay for search/load operations


async def main() -> None:
    """Main execution function with improved error handling."""
    print("=" * 70)
    print("REDESIM Consulta Automation - Starting")
    print("=" * 70)

    # Check environment variables
    user = os.getenv("ATF_USERNAME")
    pwd = os.getenv("ATF_PASSWORD")

    if not user or not pwd:
        print("❌ ERROR: ATF_USERNAME and ATF_PASSWORD environment variables not set")
        print("\nTo set them, run:")
        print("  export ATF_USERNAME='eduardof'")
        print("  export ATF_PASSWORD='atf101010'")
        sys.exit(1)

    print(f"✓ Username: {user}")
    print(f"✓ Password: {'*' * len(pwd)}")
    print()

    browser = None
    context = None
    page = None

    try:
        print("[1/5] Launching browser...")
        browser, context, page = await launch_persistent_browser(
            headless=False, slow_mo=100
        )
        print("✓ Browser launched")

        print("[2/5] Navigating to ATF...")
        await page.goto(
            "https://www4.sefaz.pb.gov.br/atf/",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        print("✓ Navigation complete")

        print("[3/5] Performing login...")
        login_ok = await perform_login(page, username=user, password=pwd)
        if not login_ok:
            raise RuntimeError("Login failed; check credentials or connectivity.")
        print("✓ Login successful")

        print("[4/5] Validating session...")
        post_ok = await wait_for_post_login(page)
        if not post_ok:
            raise RuntimeError("Session not validated after login.")
        print("✓ Session validated")

        print("[5/5] Starting REDESIM consultation...")
        payload: dict = {
            "data_criacao_inicio": "10/12/2025",
            "data_criacao_fim": "17/12/2025",
        }
        await consultar_redesim(page, payload, wait_user_dates=False)
        print("✓ Consultation submitted successfully")
        
        # Wait for results page to load (with iframe)
        print("   ⏳ Waiting for results page to load...")
        results_url_pattern = "CADf_ConsultarProcessosREDESIM"
        max_wait = 30  # seconds
        deadline = time.monotonic() + max_wait
        
        while time.monotonic() < deadline:
            current_url = page.url
            if results_url_pattern in current_url:
                print(f"   ✓ Results page detected: {current_url}")
                break
            await page.wait_for_timeout(500)
        else:
            print(f"   ⚠️  Results URL pattern not found after {max_wait}s. Current URL: {page.url}")
        
        # Wait for page to stabilize and iframe to load
        await page.wait_for_load_state("networkidle", timeout=FAST_TIMEOUT * 3)
        await page.wait_for_timeout(2000)  # Extra wait for iframe to render
        
        # Try to wait for iframe to appear
        print("   ⏳ Waiting for iframe 'principal' to load...")
        try:
            # Wait for iframe element to exist in DOM
            await page.wait_for_selector('iframe[name="principal"]', timeout=FAST_TIMEOUT * 2, state="attached")
            print("   ✓ Iframe element found in DOM")
        except Exception as e:
            print(f"   ⚠️  Iframe selector wait failed: {e}")
            # Continue anyway, will try to resolve in next step

        # Stage 2: Process ALL results and create Gmail drafts for each
        print()
        print("[6/7] Starting Stage 2: Processing ALL results and creating Gmail drafts...")
        
        # Gmail credentials paths (using correct standard location)
        project_root = Path(__file__).parent.parent
        gmail_creds_path = project_root / "credentials" / "gmail_credentials.json"
        gmail_token_path = project_root / "credentials" / "gmail_token.json"
        
        # Check if Gmail credentials exist
        if not gmail_creds_path.exists():
            print(f"⚠️  Gmail credentials not found at: {gmail_creds_path}")
            print("   Stage 2 will be skipped. Gmail draft creation requires credentials.")
            print(f"   Expected location: {gmail_creds_path}")
        elif not gmail_token_path.exists():
            print(f"⚠️  Gmail token not found at: {gmail_token_path}")
            print("   Token will be created during OAuth flow if credentials are valid.")
        else:
            print(f"✓ Gmail credentials found at: {gmail_creds_path}")
            if gmail_token_path.exists():
                print(f"✓ Gmail token found at: {gmail_token_path}")
            else:
                print(f"ℹ️  Gmail token will be created during OAuth flow")
            
            # Load persistent state for deterministic iteration
            from app.modules.cadastro.consultar_redesim import (
                _load_iteration_state,
                _save_iteration_state,
                _resolve_principal_iframe,
                _collect_radio_buttons_from_iframe,
            )
            
            state = _load_iteration_state()
            current_index = state.get("current_index", 0)
            persisted_total = state.get("total")
            
            # Resolve iframe and count processes (MANDATORY: iframe must be resolved explicitly)
            print("\n🔍 Resolving iframe 'principal' and counting processes...")
            print("   This is MANDATORY - radio buttons are inside the iframe")
            
            try:
                # Ensure we're on the results page (navigate if needed)
                results_url = "https://www4.sefaz.pb.gov.br/atf/cad/CADf_ConsultarProcessosREDESIM2.do"
                if results_url_pattern not in page.url:
                    print(f"   ↶ Navigating to results URL...")
                    await page.goto(results_url, wait_until="networkidle", timeout=FAST_TIMEOUT * 3)
                    await page.wait_for_timeout(2000)  # Wait for iframe to load
                
                await page.wait_for_load_state("domcontentloaded", timeout=FAST_TIMEOUT)
                await page.wait_for_timeout(FAST_DEFAULT_DELAY)
                
                # MANDATORY: Resolve iframe 'principal' explicitly
                principal_frame = await _resolve_principal_iframe(page, timeout=FAST_TIMEOUT * 3)
                print(f"   ✓ Iframe 'principal' resolved")
                
                # Collect ALL radio buttons from iframe (index-based, deterministic)
                radio_list = await _collect_radio_buttons_from_iframe(principal_frame)
                total_processes = len(radio_list)
                
                print(f"✓ Found {total_processes} processes in iframe 'principal'")
                
                # Update total in state if not set or if it changed
                if persisted_total is None or persisted_total != total_processes:
                    state["total"] = total_processes
                    _save_iteration_state(state)
                    print(f"✓ Set total processes to {total_processes} in state file")
                
            except Exception as count_err:
                print(f"❌ Error counting processes: {count_err}")
                import traceback
                traceback.print_exc()
                
                if persisted_total:
                    total_processes = persisted_total
                    print(f"⚠️  Using persisted total: {total_processes}")
                else:
                    print("❌ Cannot determine total processes. Aborting.")
                    raise
            
            # Determine starting index from state
            start_index = current_index
            if start_index >= total_processes:
                print(f"\n✓ All processes already processed (index {start_index} >= {total_processes})")
                print("   To restart, delete state file: /Volumes/MICRO/ATF/REDESIM/state.json")
                print("   Or reset current_index to 0 in the state file")
                return
            
            print(f"\n⏳ Processing processes {start_index + 1} to {total_processes}")
            print(f"   Starting from index {start_index} (resumable)")
            print(f"   State file: /Volumes/MICRO/ATF/REDESIM/state.json")
            print(f"   Each process will update state.json after completion\n")
            
            successful_drafts = 0
            failed_drafts = 0
            all_results = []
            
            # Iterate from current_index to total_processes
            for row_index in range(start_index, total_processes):
                print(f"--- Processing {row_index + 1}/{total_processes} ---")
                
                try:
                    stage2_results = await process_redesim_stage2(
                        page=page,
                        gmail_credentials_path=str(gmail_creds_path),
                        gmail_token_path=str(gmail_token_path) if gmail_token_path.exists() else None,
                        output_dir=str(project_root / "output"),
                        row_index=row_index,
                    )
                    
                    all_results.append(stage2_results)
                    
                    # Update state: increment current_index AFTER successful processing
                    if stage2_results.get("success"):
                        # Increment index for next iteration
                        state["current_index"] = row_index + 1
                        _save_iteration_state(state)
                        
                        email_count = stage2_results.get('steps', {}).get('email_extraction', {}).get('count', 0)
                        draft_success = stage2_results.get('steps', {}).get('gmail_draft', {}).get('success', False)
                        processo_num = stage2_results.get('steps', {}).get('process_data', {}).get('processo_numero', 'N/A')
                        
                        if draft_success:
                            successful_drafts += 1
                            draft_id = stage2_results.get('steps', {}).get('gmail_draft', {}).get('draft_id', 'N/A')
                            print(f"✓ Process {processo_num}: Draft created (ID: {draft_id}, {email_count} email(s))")
                            print(f"   ✓ State updated: current_index = {row_index + 1}")
                        else:
                            failed_drafts += 1
                            print(f"⚠️  Process {processo_num}: Draft failed ({email_count} email(s))")
                            # Still increment index to avoid retrying same process
                            print(f"   ✓ State updated: current_index = {row_index + 1}")
                    else:
                        failed_drafts += 1
                        errors = stage2_results.get("errors", [])
                        print(f"⚠️  Process {row_index + 1}: Errors - {', '.join(errors[:2])}")
                        # Increment index even on error to avoid infinite retry
                        state["current_index"] = row_index + 1
                        _save_iteration_state(state)
                        print(f"   ✓ State updated: current_index = {row_index + 1} (error, skipping)")
                    
                    # Navigate back to results list for next iteration (if not last)
                    if row_index < total_processes - 1:
                        print(f"   ↶ Returning to results list for next process...")
                        
                        # Always navigate directly to results URL (more reliable than go_back)
                        # This ensures fresh DOM state for next iteration
                        results_url = "https://www4.sefaz.pb.gov.br/atf/cad/CADf_ConsultarProcessosREDESIM2.do"
                        
                        try:
                            await page.goto(results_url, wait_until="domcontentloaded", timeout=FAST_TIMEOUT * 3)
                            logger.info(f"cadastro_redesim: Navigated to results URL: {results_url}")
                        except Exception as nav_err:
                            logger.warning(f"cadastro_redesim: Navigation error: {nav_err}, trying reload...")
                            await page.reload(wait_until="domcontentloaded", timeout=FAST_TIMEOUT * 3)
                        
                        # Wait for page to fully stabilize
                        await page.wait_for_load_state("networkidle", timeout=FAST_TIMEOUT * 3)
                        await page.wait_for_timeout(FAST_SEARCH_DELAY * 3)
                        
                        # CRITICAL: Re-query iframe and radios after navigation (never reuse stale references)
                        # This is MANDATORY because the iframe fully reloads after each operation
                        try:
                            # Re-resolve iframe 'principal' (MANDATORY after navigation)
                            principal_frame = await _resolve_principal_iframe(page, timeout=FAST_TIMEOUT * 2)
                            print(f"   ✓ Iframe 'principal' re-resolved after navigation")
                            
                            # Re-collect radio buttons (MANDATORY - never reuse stale references)
                            radio_check = principal_frame.locator("input[type='radio'][name='rdbChavePrimaria']")
                            await radio_check.first.wait_for(timeout=ELEMENT_TIMEOUT, state="attached")
                            current_count = await radio_check.count()
                            if current_count > 0:
                                print(f"   ✓ Results list ready ({current_count} processes in iframe)")
                            else:
                                print(f"   ⚠️  Warning: No radio buttons found in iframe after navigation")
                        except Exception as iframe_err:
                            print(f"   ⚠️  Warning: Could not verify iframe: {iframe_err}")
                            # Continue anyway - next iteration will try to resolve again
                        
                except Exception as stage2_err:
                    failed_drafts += 1
                    print(f"❌ Process {row_index + 1} error: {stage2_err}")
                    
                    # IMPORTANT: Increment state even on error to avoid infinite retry
                    state["current_index"] = row_index + 1
                    _save_iteration_state(state)
                    print(f"   ✓ State updated: current_index = {row_index + 1} (error, skipping)")
                    
                    # Try to go back for next iteration
                    try:
                        if row_index < total_processes - 1:
                            print(f"   ↶ Attempting to return to results list after error...")
                            try:
                                await page.go_back(wait_until="domcontentloaded", timeout=FAST_TIMEOUT)
                            except Exception:
                                # Fallback: navigate directly
                                results_url = "https://www4.sefaz.pb.gov.br/atf/cad/CADf_ConsultarProcessosREDESIM2.do"
                                await page.goto(results_url, wait_until="domcontentloaded", timeout=FAST_TIMEOUT)
                            await page.wait_for_timeout(FAST_SEARCH_DELAY * 2)
                    except Exception as nav_err:
                        print(f"   ⚠️  Navigation error: {nav_err}")
            
            print()
            print("=" * 70)
            print(f"📊 Stage 2 Summary:")
            print(f"   Total processes: {total_processes}")
            print(f"   Successful drafts: {successful_drafts}")
            print(f"   Failed drafts: {failed_drafts}")
            print(f"   Success rate: {(successful_drafts/total_processes*100):.1f}%")
            print("=" * 70)

        print()
        print("=" * 70)
        print("✅ SUCCESS: Full automation completed!")
        print("=" * 70)
        print("Browser will remain open for 1 hour for manual inspection.")
        print("Close the browser window when finished.")
        print()

        await page.wait_for_timeout(KEEP_OPEN_MS)

    except KeyboardInterrupt:
        print("\n⚠️  Interrupted by user (Ctrl+C)")
        sys.exit(130)

    except Exception as err:  # noqa: BLE001
        # Check if it's a browser closed error
        error_msg = str(err)
        if (
            "TargetClosedError" in error_msg
            or "Target page, context or browser has been closed" in error_msg
        ):
            print("\n⚠️  Browser was closed during execution")
            print("   This can happen if:")
            print("   - Browser window was manually closed")
            print("   - System closed the browser due to resource constraints")
            print("   - Another process closed the browser")
            print("\n   Try running again - the script will start fresh.")
        print()
        print("=" * 70)
        print(f"❌ ERROR: {err}")
        print("=" * 70)
        print(f"Error type: {type(err).__name__}")

        # Save screenshot if page exists
        if page:
            try:
                screenshots_dir = project_root / "output" / "nfa" / "screenshots"
                screenshots_dir.mkdir(parents=True, exist_ok=True)
                await save_screenshot(
                    page, screenshots_dir, filename="runner_error.png"
                )
                print(f"✓ Screenshot saved: {screenshots_dir}/runner_error.png")
            except Exception as screenshot_err:
                print(f"⚠️  Could not save screenshot: {screenshot_err}")

        # Keep browser open for debugging
        print("\nBrowser will remain open for 5 minutes for debugging...")
        try:
            if page:
                await page.wait_for_timeout(300_000)  # 5 minutes
        except Exception:
            pass

        # Print full traceback for debugging
        import traceback

        print("\nFull traceback:")
        traceback.print_exc()

        sys.exit(1)

    finally:
        # Cleanup (optional - browser stays open for inspection)
        print("\n[Cleanup] Keeping browser open for manual inspection...")
        # Note: We don't close browser/context to allow manual inspection


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️  Script interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
