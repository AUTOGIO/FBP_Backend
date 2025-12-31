#!/usr/bin/env bash
# Script to apply the corrected iTerm2 profile
# Usage: Run this script, then manually import the profile in iTerm2

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE_JSON="${SCRIPT_DIR}/fbp_nfa_iterm2_profile.json"
ITerm2_PROFILES_DIR="$HOME/Library/Application Support/iTerm2/DynamicProfiles"

echo "=== FBP NFA iTerm2 Profile Installer ==="
echo ""

# Check if profile JSON exists
if [ ! -f "$PROFILE_JSON" ]; then
    echo "❌ Profile JSON not found: $PROFILE_JSON"
    exit 1
fi

# Create DynamicProfiles directory if it doesn't exist
mkdir -p "$ITerm2_PROFILES_DIR"

# Copy profile to iTerm2 DynamicProfiles directory
echo "📋 Copying profile to iTerm2 DynamicProfiles..."
cp "$PROFILE_JSON" "$ITerm2_PROFILES_DIR/fbp_nfa_profile.json"

echo "✓ Profile copied to: $ITerm2_PROFILES_DIR/fbp_nfa_profile.json"
echo ""
echo "📝 Next steps:"
echo "1. Open iTerm2"
echo "2. Go to Preferences (⌘,) → Profiles"
echo "3. The 'FBP_NFA' profile should appear automatically (Dynamic Profiles)"
echo "4. Select it and click 'Other Actions...' → 'Set as Default' (optional)"
echo ""
echo "✅ Profile installation complete!"
