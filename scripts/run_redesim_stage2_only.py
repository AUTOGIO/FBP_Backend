#!/usr/bin/env python3
"""
REDESIM Stage 2 Only - Process ALL Results and Create Gmail Drafts
This script connects to an already-open browser and processes all results.
No login or form submission required.
"""

import asyncio
import sys
from pathlib import Path

try:
    from app.modules.cadastro.consultar_redesim import (
        process_redesim_stage2,
        ELEMENT_TIMEOUT,
    )
    from app.modules.nfa.browser_launcher import launch_persistent_browser
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\nMake sure you're running from the project root:")
    print("  cd /Users/dnigga/Documents/FBP_Backend")
    print("  .venv/bin/python scripts/run_redesim_stage2_only.py")
    sys.exit(1)

KEEP_OPEN_MS = 3_600_000  # 1h for manual inspection
FAST_TIMEOUT = 10000  # 10s timeout
FAST_DEFAULT_DELAY = 300  # 300ms delay
FAST_SEARCH_DELAY = 500  # 500ms delay for search/load operations


async def main() -> None:
    """Main execution function - Stage 2 only (no login, no form submission)."""
    print("=" * 70)
    print("REDESIM Stage 2 ONLY - Process ALL Results")
    print("=" * 70)
    print()
    print("ℹ️  This script assumes you are already logged in and viewing results")
    print("   It will connect to your existing browser session and process all results")
    print()

    browser = None
    context = None
    page = None

    try:
        print("[1/3] Connecting to existing browser session...")
        browser, context, page = await launch_persistent_browser(
            headless=False, slow_mo=100
        )
        print("✓ Browser connected")

        # Get current URL to verify we're on the right page
        current_url = page.url
        print(f"   Current URL: {current_url}")
        
        # Check if we're already on results page
        if "CADf_ConsultarProcessosREDESIM" not in current_url:
            print()
            print("⚠️  WARNING: You don't appear to be on the REDESIM results page")
            print(f"   Current URL: {current_url}")
            print("   Expected URL should contain: CADf_ConsultarProcessosREDESIM")
            print()
            print("Please:")
            print("  1. Navigate to the ATF REDESIM consultation page")
            print("  2. Submit your search to see results")
            print("  3. Run this script again")
            return

        print("✓ Confirmed on REDESIM results page")
        print()

        # Stage 2: Process ALL results and create Gmail drafts for each
        print("[2/3] Processing ALL results and creating Gmail drafts...")
        
        # Gmail credentials paths (using correct standard location)
        project_root = Path(__file__).parent.parent
        gmail_creds_path = project_root / "credentials" / "gmail_credentials.json"
        gmail_token_path = project_root / "credentials" / "gmail_token.json"
        
        # Check if Gmail credentials exist
        if not gmail_creds_path.exists():
            print(f"❌ Gmail credentials not found at: {gmail_creds_path}")
            print("   Stage 2 requires Gmail credentials to create drafts.")
            print(f"   Please place your credentials.json at: {gmail_creds_path}")
            return
        
        print(f"✓ Gmail credentials found at: {gmail_creds_path}")
        if gmail_token_path.exists():
            print(f"✓ Gmail token found at: {gmail_token_path}")
        else:
            print(f"ℹ️  Gmail token will be created during OAuth flow")
        
        # Count total processes to iterate
        radio_buttons = page.locator("input[type='radio'][name='rdbChavePrimaria']")
        
        # Wait for radio buttons to load
        try:
            await radio_buttons.first.wait_for(timeout=FAST_TIMEOUT)
        except Exception:
            print("⚠️  Radio buttons not found, waiting longer...")
            await page.wait_for_timeout(FAST_SEARCH_DELAY * 2)
            try:
                await radio_buttons.first.wait_for(timeout=ELEMENT_TIMEOUT)
            except Exception:
                print("❌ No processes found in results list")
                print("   Please ensure the results page is loaded")
                return
        
        total_processes = await radio_buttons.count()
        
        if total_processes == 0:
            print("❌ No processes found in results list")
            return
        
        print(f"\nℹ️  Found {total_processes} processes in results list")
        print(f"⏳ Processing all processes (this may take a few minutes)...\n")
        
        successful_drafts = 0
        failed_drafts = 0
        all_results = []
        
        for row_index in range(total_processes):
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
                
                if stage2_results.get("success"):
                    email_count = stage2_results.get('steps', {}).get('email_extraction', {}).get('count', 0)
                    draft_success = stage2_results.get('steps', {}).get('gmail_draft', {}).get('success', False)
                    processo_num = stage2_results.get('steps', {}).get('process_data', {}).get('processo_numero', 'N/A')
                    
                    if draft_success:
                        successful_drafts += 1
                        draft_id = stage2_results.get('steps', {}).get('gmail_draft', {}).get('draft_id', 'N/A')
                        print(f"✓ Process {processo_num}: Draft created (ID: {draft_id}, {email_count} email(s))")
                    else:
                        failed_drafts += 1
                        print(f"⚠️  Process {processo_num}: Draft failed ({email_count} email(s))")
                else:
                    failed_drafts += 1
                    errors = stage2_results.get("errors", [])
                    print(f"⚠️  Process {row_index + 1}: Errors - {', '.join(errors[:2])}")
                
                # Navigate back to results list for next iteration
                if row_index < total_processes - 1:
                    print(f"   ↶ Returning to results list...")
                    try:
                        # Try go_back first (faster if it works)
                        await page.go_back(wait_until="domcontentloaded", timeout=FAST_TIMEOUT)
                    except Exception:
                        # Fallback: navigate directly to results URL
                        print(f"   ↶ go_back() failed, navigating directly to results URL...")
                        results_url = "https://www4.sefaz.pb.gov.br/atf/cad/CADf_ConsultarProcessosREDESIM2.do"
                        await page.goto(results_url, wait_until="domcontentloaded", timeout=FAST_TIMEOUT)
                    
                    # Wait for page to fully load
                    await page.wait_for_load_state("networkidle", timeout=FAST_TIMEOUT * 2)
                    await page.wait_for_timeout(FAST_SEARCH_DELAY * 2)
                    
                    # Verify we're back on results page by checking for table or results text
                    try:
                        # Wait for results table or "Processos REDESIM Encontrados" text
                        await page.locator("text=Processos REDESIM Encontrados, text=Resultado da consulta").first.wait_for(timeout=ELEMENT_TIMEOUT * 2)
                    except Exception:
                        pass
                    
                    # Now check for radio buttons
                    radio_check = page.locator("input[type='radio'][name='rdbChavePrimaria']")
                    try:
                        await radio_check.first.wait_for(timeout=ELEMENT_TIMEOUT * 2)
                        current_count = await radio_check.count()
                        print(f"   ✓ Results list loaded ({current_count} processes found)")
                    except Exception:
                        print(f"   ⚠️  Warning: Radio buttons not found, waiting longer...")
                        await page.wait_for_timeout(FAST_SEARCH_DELAY * 3)
                        # Try one more time with longer timeout
                        try:
                            await radio_check.first.wait_for(timeout=ELEMENT_TIMEOUT * 3)
                            current_count = await radio_check.count()
                            print(f"   ✓ Results list loaded after extended wait ({current_count} processes)")
                        except Exception:
                            print(f"   ❌ Error: Cannot find results list after navigation")
                            # Try to reload the page
                            print(f"   ↻ Attempting page reload...")
                            await page.reload(wait_until="domcontentloaded", timeout=FAST_TIMEOUT)
                            await page.wait_for_timeout(FAST_SEARCH_DELAY * 2)
                    
            except Exception as stage2_err:
                failed_drafts += 1
                print(f"❌ Process {row_index + 1} error: {stage2_err}")
                
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
        print(f"[3/3] Keeping browser open for {KEEP_OPEN_MS // 60000} minutes for manual inspection...")
        print("   Press Ctrl+C to exit early")
        await page.wait_for_timeout(KEEP_OPEN_MS)

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user (Ctrl+C)")
    except Exception as err:
        print(f"\n❌ AUTOMATION ERROR: {err}")
        if "TargetClosedError" in str(err):
            print("   The browser or page was closed unexpectedly")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        sys.exit(1)
    finally:
        print("\n✓ Script finished")
        print("   Browser will remain open for manual inspection")


if __name__ == "__main__":
    asyncio.run(main())
