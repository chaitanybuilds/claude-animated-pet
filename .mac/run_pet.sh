#!/bin/bash
# claude-animated-pet - manual launch (macOS/Linux).
# Equivalent of run_pet.bat on Windows.
cd "$(dirname "$0")"
# Prefer python3 (python on macOS is usually missing or points at
# the system's ancient Python 2), fall back to `python` if that is
# all that is on PATH. No errors either way: whichever is missing
# is simply skipped.
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "Python was not found on PATH. Install Python 3.9+ from https://www.python.org/downloads/ (or 'brew install python3' on macOS) and try again."
    exit 1
fi

# Run detached (like Windows' pythonw) so closing this terminal window
# does not kill the pet, and this script returns control immediately.
nohup "$PY" src/pet.py "$@" >/dev/null 2>&1 &
disown
echo "claude-animated-pet started."
