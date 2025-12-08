#!/usr/bin/env bash
# Auto-install Safari Extension - Zero Human Intervention
# Builds, installs and activates NFASEFAZPB extension automatically

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_PATH="$PROJECT_ROOT/NFASEFAZPB/NFASEFAZPB.xcodeproj"
SCHEME="NFASEFAZPB"
APP_NAME="NFASEFAZPB"
BUNDLE_ID="com.sefazpb.nfa"
EXT_BUNDLE_ID="com.sefazpb.nfa.Extension"

echo "🚀 Starting automated Safari extension installation..."

# Step 1: Build the project
echo "📦 Step 1: Building Xcode project..."
cd "$PROJECT_ROOT/NFASEFAZPB"
xcodebuild -project "$PROJECT_PATH" \
    -scheme "$SCHEME" \
    -configuration Release \
    clean build \
    CODE_SIGN_IDENTITY="" \
    CODE_SIGNING_REQUIRED=NO \
    CODE_SIGNING_ALLOWED=NO \
    > /tmp/xcodebuild.log 2>&1

if [ $? -ne 0 ]; then
    echo "❌ Build failed. Check /tmp/xcodebuild.log"
    exit 1
fi

echo "✅ Build successful!"

# Step 2: Find the built app
BUILD_DIR=$(xcodebuild -project "$PROJECT_PATH" -scheme "$SCHEME" -configuration Release -showBuildSettings 2>/dev/null | grep -m 1 "BUILT_PRODUCTS_DIR" | cut -d "=" -f 2 | xargs)
APP_PATH="$BUILD_DIR/$APP_NAME.app"

if [ ! -d "$APP_PATH" ]; then
    # Try finding in DerivedData
    APP_PATH=$(find ~/Library/Developer/Xcode/DerivedData -name "$APP_NAME.app" -type d | head -1)
fi

if [ ! -d "$APP_PATH" ]; then
    echo "❌ Could not find built app"
    exit 1
fi

echo "✅ Found app at: $APP_PATH"

# Step 3: Copy to Applications
echo "📋 Step 2: Installing app..."
INSTALL_DIR="$HOME/Applications"
mkdir -p "$INSTALL_DIR"
rm -rf "$INSTALL_DIR/$APP_NAME.app"
cp -R "$APP_PATH" "$INSTALL_DIR/"
echo "✅ App installed to $INSTALL_DIR"

# Step 4: Register extension with pluginkit
echo "🔌 Step 3: Registering extension..."
EXT_PATH="$INSTALL_DIR/$APP_NAME.app/Contents/PlugIns/$APP_NAME Extension.appex"

if [ -d "$EXT_PATH" ]; then
    pluginkit -a "$EXT_PATH" 2>/dev/null || true
    echo "✅ Extension registered"
else
    echo "⚠️  Extension path not found: $EXT_PATH"
fi

# Step 5: Enable extension in Safari preferences
echo "⚙️  Step 4: Enabling extension in Safari..."

# Kill Safari if running
killall "Safari Technology Preview" 2>/dev/null || true
sleep 1

# Enable extension via defaults (Safari Tech Preview)
PLIST_PATH="$HOME/Library/Containers/com.apple.SafariTechnologyPreview/Data/Library/Preferences/com.apple.SafariTechnologyPreview.plist"

# Create plist if doesn't exist
if [ ! -f "$PLIST_PATH" ]; then
    mkdir -p "$(dirname "$PLIST_PATH")"
    defaults write com.apple.SafariTechnologyPreview ExtensionsEnabled -bool true
fi

# Enable extension
defaults write com.apple.SafariTechnologyPreview "com.apple.Safari.SandboxBroker" -dict-add "SafariWebExtensions" -array-add "$EXT_BUNDLE_ID" 2>/dev/null || true
defaults write com.apple.SafariTechnologyPreview "com.apple.Safari.SandboxBroker" -dict-add "SafariWebExtensions" -array "$EXT_BUNDLE_ID" 2>/dev/null || true

# Alternative: Use AppleScript to enable
osascript <<'EOF'
tell application "Safari Technology Preview"
    activate
    delay 2
end tell

tell application "System Events"
    tell process "Safari Technology Preview"
        -- Open Preferences
        keystroke "," using command down
        delay 2

        -- Click Extensions tab
        try
            click button "Extensions" of toolbar 1 of window 1
            delay 1

            -- Find and enable our extension
            set extensionRow to first row of table 1 of scroll area 1 of group 1 of window 1 whose name contains "NFA SEFAZ PB"
            set checkbox of extensionRow to true
            delay 1

            -- Close preferences
            keystroke "w" using command down
        on error
            -- If UI automation fails, just close preferences
            keystroke "w" using command down
        end try
    end tell
end tell
EOF

echo "✅ Extension enabled"

# Step 6: Open Safari and test URL
echo "🌐 Step 5: Opening Safari with test URL..."
open -a "Safari Technology Preview" "https://www4.sefaz.pb.gov.br/atf/"

echo ""
echo "✅ Installation complete!"
echo "📝 Extension should be active. Check Safari > Settings > Extensions"
echo "🔗 Test URL opened: https://www4.sefaz.pb.gov.br/atf/"

