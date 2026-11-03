#!/bin/bash
# claude-animated-pet installer - macOS (launchd LaunchAgent autostart).
# Run this from inside the cloned repo folder: ./install.sh
# No sudo / admin rights needed — a LaunchAgent is per-user, same as the
# Windows Startup-folder approach (no Scheduled Task / system daemon).

set -u
cd "$(dirname "$0")"
INSTALL_DIR="$(pwd)"
PLIST_LABEL="com.chaitanybuilds.claudeanimatedpet"
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$PLIST_DIR/$PLIST_LABEL.plist"

if [ "$(uname -s)" != "Darwin" ]; then
    echo "install.sh is for macOS. On Windows, use install.bat instead."
    exit 1
fi

if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "Python was not found on PATH."
    echo "Install Python 3.9+ first, e.g.: brew install python3"
    echo "(or download from https://www.python.org/downloads/), then run this installer again."
    exit 1
fi
PY_PATH="$(command -v "$PY")"

echo "Installing Python dependencies..."
"$PY" -m pip install --break-system-packages -r "$INSTALL_DIR/requirements.txt" \
    || "$PY" -m pip install -r "$INSTALL_DIR/requirements.txt"
if [ $? -ne 0 ]; then
    echo "WARNING: dependency install failed. The pet may not run until"
    echo "you install PyQt5, psutil and pyobjc-framework-Cocoa manually:"
    echo "  $PY -m pip install -r requirements.txt"
fi

mkdir -p "$PLIST_DIR"

cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$PLIST_LABEL</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PY_PATH</string>
        <string>$INSTALL_DIR/src/pet.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$INSTALL_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>ProcessType</key>
    <string>Interactive</string>
    <key>StandardOutPath</key>
    <string>/tmp/claude-animated-pet.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/claude-animated-pet.log</string>
</dict>
</plist>
PLIST

if [ ! -f "$PLIST_PATH" ]; then
    echo "ERROR: LaunchAgent could not be created at $PLIST_PATH"
    exit 1
fi
echo "LaunchAgent created: $PLIST_PATH"

# Reload so it takes effect immediately, not just on next login.
# `load -w` is the broadly-compatible call across macOS versions; a
# failure here is not fatal, the agent still runs on the next login.
launchctl unload "$PLIST_PATH" >/dev/null 2>&1
if launchctl load -w "$PLIST_PATH" >/dev/null 2>&1; then
    echo "Pet launched now, and will auto-start at every login from now on."
else
    echo "Could not launch it immediately (this is not fatal)."
    echo "Run ./run_pet.sh to start it now — it will still auto-start at your next login."
fi

echo
echo "Done! On first run, macOS may ask for Accessibility / Automation"
echo "permission (for app-detection and the click-to-launch terminal)."
echo "Grant it in System Settings > Privacy & Security if prompted."
echo
echo "To start it manually any time: ./run_pet.sh"
