#!/usr/bin/env bash

# SEFAZ PB ATF Access Validation Script
# Tests browser launch, navigation, and iframe detection

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== SEFAZ PB ATF Access Validation ===${NC}"
echo "Project Root: $PROJECT_ROOT"
echo ""

# Find virtual environment
VENV_DIR=""
if [ -d "$PROJECT_ROOT/venv" ]; then
    VENV_DIR="$PROJECT_ROOT/venv"
elif [ -d "$PROJECT_ROOT/.venv" ]; then
    VENV_DIR="$PROJECT_ROOT/.venv"
else
    echo -e "${RED}✗ Virtual environment not found${NC}"
    echo -e "${YELLOW}Run: ./ops/scripts/foks_env_autofix.sh${NC}"
    exit 1
fi

# Activate virtual environment
source "$VENV_DIR/bin/activate"

# Run validation script
echo -e "${YELLOW}Running SEFAZ access validation...${NC}"
echo ""

python3 << 'PYEOF'
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path("/Users/dnigga/Documents/FBP_Backend")
sys.path.insert(0, str(project_root))

from app.modules.nfa.browser_launcher import (
    launch_persistent_browser,
    navigate_to_sefaz_with_fallback,
)
from app.modules.nfa.atf_frames import detect_sefaz_iframe
from app.core.config import settings

async def validate_sefaz_access():
    """Validate SEFAZ PB ATF access."""
    print("🔹 Step 1: Launching browser with persistent context...")
    try:
        browser, context, page = await launch_persistent_browser(
            headless=False,  # Show browser for debugging
            slow_mo=100,
        )
        print("✅ Browser launched successfully")
    except Exception as e:
        print(f"❌ Browser launch failed: {e}")
        return False

    try:
        print("\n🔹 Step 2: Navigating to SEFAZ PB ATF...")
        navigation_success = await navigate_to_sefaz_with_fallback(
            page,
            url="https://www4.sefaz.pb.gov.br/atf/",
            timeout=120000,
        )
        
        if not navigation_success:
            print("❌ Navigation failed - page may be blank")
            return False
        
        final_url = page.url
        print(f"✅ Navigation successful")
        print(f"   Final URL: {final_url}")
        
        if final_url == "about:blank":
            print("⚠️  WARNING: Page is still 'about:blank'")
            return False
        
        # Save screenshot
        screenshot_path = settings.paths.project_root / "logs" / "nfa" / "validation_screenshot.png"
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"✅ Screenshot saved: {screenshot_path}")
        
        print("\n🔹 Step 3: Detecting iframes...")
        frame = await detect_sefaz_iframe(page, timeout=60000)
        
        if frame:
            print("✅ NFA form frame detected")
            print(f"   Frame URL: {frame.url}")
            print(f"   Frame name: {frame.name or 'unnamed'}")
        else:
            print("❌ NFA form frame NOT detected")
            # List all frames
            print("\n   All frames:")
            for idx, f in enumerate(page.frames):
                print(f"   Frame {idx}: name='{f.name or 'unnamed'}', url='{f.url}'")
            return False
        
        print("\n🔹 Step 4: Checking frame count...")
        frame_count = len(page.frames)
        print(f"✅ Total frames detected: {frame_count}")
        
        if frame_count == 0:
            print("⚠️  WARNING: No frames detected")
            return False
        
        print("\n" + "="*50)
        print("✅ VALIDATION SUCCESSFUL")
        print("="*50)
        print(f"   Final URL: {final_url}")
        print(f"   Frame count: {frame_count}")
        print(f"   NFA form frame: {'✅ Detected' if frame else '❌ Not detected'}")
        if frame:
            print(f"   Frame URL: {frame.url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Validation error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        print("\n🔹 Cleaning up...")
        try:
            await context.close()
            if browser:
                await browser.close()
        except Exception:
            pass
        print("✅ Cleanup complete")

# Run validation
result = asyncio.run(validate_sefaz_access())
sys.exit(0 if result else 1)
PYEOF

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✅ Validation PASSED${NC}"
else
    echo -e "${RED}❌ Validation FAILED${NC}"
    echo -e "${YELLOW}Check logs in: $PROJECT_ROOT/logs/nfa/${NC}"
fi

exit $EXIT_CODE
