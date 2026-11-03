#!/bin/bash
# claude-animated-pet uninstaller - macOS (.mac/ copy).
# Run this from inside the repo's .mac/ folder: ./uninstall.sh
# It only touches files inside .mac/ and the LaunchAgent plist.
# The repo root assets/, README.md and Windows files are NOT deleted.
# No sudo needed — everything it touches is per-user (LaunchAgents is
# in your home folder, same reasoning as the Windows Startup-folder
# approach not needing admin rights).
#
# What it does, in order:
#  1. Unloads and deletes the LaunchAgent plist
#  2. Tries to stop the running pet process, best effort only
#  3. Asks: delete the project files too? Y = delete, N = keep
#     Y deletes ONLY the project files listed below, in this folder.
#     Any other file in this folder is left untouched.
#  4. Prints thank you, then exits. In the delete case, uninstall.sh
#     deletes itself as the very last step.

set -u
cd "$(dirname "$0")"
INSTALL_DIR="$(pwd)"
PLIST_LABEL="com.chaitanybuilds.claudeanimatedpet"
PLIST_PATH="$HOME/Library/LaunchAgents/$PLIST_LABEL.plist"

echo "Uninstalling claude-animated-pet..."
echo

# 1. LaunchAgent
if [ -f "$PLIST_PATH" ]; then
    launchctl unload "$PLIST_PATH" >/dev/null 2>&1
    rm -f "$PLIST_PATH"
    echo "LaunchAgent removed: $PLIST_PATH"
else
    echo "No LaunchAgent found at $PLIST_PATH"
fi

# 2. Stop the running pet, best effort only. Only processes whose
# command line contains pet.py are stopped, other Python apps are
# left alone.
pkill -f "src/pet.py" >/dev/null 2>&1
echo "Pet autostart removed. If the pet is still on screen, quit it from Activity Monitor, it will not come back on login."
echo

while true; do
    read -r -p "Do you want to DELETE the project files too? (y/n) [Y = delete, N = keep]: " DELETE_FILES
    case "$DELETE_FILES" in
        [Yy]) break ;;
        [Nn])
            echo
            echo "Keeping project files in $INSTALL_DIR"
            echo "You can run uninstall.sh again later to delete them."
            echo
            echo "thank you for using my project - Chaitany"
            exit 0
            ;;
        *) echo "Please press Y or N." ;;
    esac
done

echo
echo "Deleting ONLY project files in $INSTALL_DIR"
echo "Any other file in this folder will be left untouched."
rm -rf "$INSTALL_DIR/src"
rm -f "$INSTALL_DIR/install.sh" \
      "$INSTALL_DIR/run_pet.sh" \
      "$INSTALL_DIR/requirements.txt" "$INSTALL_DIR/README.md" \
      "$INSTALL_DIR/pet_config.json"
echo "Project files deleted."
echo
echo "thank you for using my project - Chaitany"
echo
# Delete this uninstaller itself as the very last line.
rm -f "$INSTALL_DIR/uninstall.sh"
