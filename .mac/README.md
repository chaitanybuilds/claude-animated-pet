# claude-animated-pet — macOS port

This folder is the macOS port. It is the same pet as the Windows version in the repo root, with macOS-specific launch, app detection, and click-to-launch. The Windows version in the repo root is unchanged.

**Important layout:** this port lives in `.mac/` and shares the repo root `assets/` folder. Do not move `.mac/` out of the repo on its own, or the pet will not find its sprites. The Mac code in `.mac/src/pet.py` first looks for `.mac/assets/`, and if that folder is missing it falls back to `../assets/` (the repo root assets).

## Requirements

- macOS 11+
- Python 3.9+ on your `PATH` as `python3` (`brew install python3` is the easiest route if you use Homebrew)
- Claude Code CLI, if you want click-to-launch to open Claude (`~/.local/bin/claude` is the usual install path)

## Install

From the repo root:

```
chmod +x .mac/*.sh
.mac/install.sh
```

Or, without changing permissions:

```
bash .mac/install.sh
```

`install.sh` will:

- `pip install` the dependencies from `.mac/requirements.txt` (PyQt5, psutil, and `pyobjc-framework-Cocoa` on macOS only)
- Register a per-user LaunchAgent at `~/Library/LaunchAgents/com.chaitanybuilds.claudeanimatedpet.plist`, with `RunAtLoad`, so the pet starts at every login
- No `sudo` is needed. A LaunchAgent is per-user, the macOS equivalent of the Windows Startup folder, not a system-wide daemon.

Start it right now, without logging out, with:

```
bash .mac/run_pet.sh
```

## First run permissions

macOS will likely prompt for Accessibility and/or Automation permission the first time the pet tries to read the frontmost app or open Terminal. Grant it once in **System Settings → Privacy & Security**.

If you skip it, the pet still runs and drags around fine, it just will not react to the app in front of you. A permission error is swallowed silently by design, so the pet never crashes on a fresh Mac.

## What works on macOS, and what is different from Windows

- **App reactions:** every 4 seconds, via AppKit `NSWorkspace` when `pyobjc-framework-Cocoa` is installed, with an automatic fallback to `osascript` / System Events if it is not. Mac app names are translated in `MAC_APP_NAME_MAP` in `.mac/src/pet.py` to the same keys the Windows version uses, for example "Google Chrome" → `chrome.exe`, "Visual Studio Code" → `code.exe`, "Discord" → `discord.exe`, "Finder" → `explorer.exe` (ignored, like Windows Explorer). No duplicate joke pools.
- **Terminals:** Terminal, iTerm2, Warp, Hyper, Alacritty, and kitty all get the one generic "terminal" pool. macOS can only see which terminal app is in front, not which shell or CLI tool is running inside it, so the per-shell pools (PowerShell, cmd, Git, Node, Python, WSL) stay Windows-only by design.
- **Claude Code:** detected automatically in the background, same as Windows. It scans for a `claude` process whose exe path is in `.local/bin` (for example `~/.local/bin/claude`), plus a `node` fallback whose command line contains claude and `.local`. When Claude Code starts, the pet says one Claude Code joke once, then the 30-second joke pool switches to the Claude Code pool until it stops.
- **Click-to-launch:** click the pet and it opens Terminal.app (via `osascript`, `tell application "Terminal" to do script "claude"`) and runs `claude` there. The pet never closes that terminal, because for Claude Code the terminal is the app. If Claude Code CLI is not installed, the pet does not open a terminal, it directly says: "Claude Code CLI is not installed. Download Claude Code, restart your Mac, and try again." The same message is shown if Claude is not found in 25 seconds.
- **Process priority:** Windows priority classes do not exist on macOS, so the pet best-effort renices itself with `os.nice(-10)`. If macOS refuses that for a non-root user, which is normal, it is silently ignored and the pet runs at normal priority.
- **Bye bubble:** Windows-only. macOS has no equivalent of Windows' `WM_QUERYENDSESSION` hook, so logging out simply quits the pet, with no bye bubble.
- **Closing the pet:** window close is ignored on purpose, same as Windows. To quit manually, quit the `pet.py` process from Activity Monitor. The pet's position is saved to `.mac/pet_config.json`, not to the repo root config.
- **System stats, jokes, idle fidgets:** same as Windows, on the same timers. Temperature is best-effort: `psutil` does not report CPU temperature on macOS, so that trigger falls back to `nvidia-smi` if present, otherwise it stays silent while RAM and CPU keep working.
- **Linux:** not a target of this repo. No installer is provided for Linux, but the pet still runs there with reduced functionality, while Windows/macOS-only detection stays silent rather than erroring.

## Uninstalling (macOS)

```
bash .mac/uninstall.sh
```

It will, in order:

- Unload and delete the LaunchAgent at `~/Library/LaunchAgents/com.chaitanybuilds.claudeanimatedpet.plist`
- Try to stop the running pet process, best effort only, only processes whose command line contains `src/pet.py`
- Ask: Do you want to DELETE the project files too? (y/n) [Y = delete, N = keep]
  - Y deletes ONLY the files inside `.mac/`: `src/`, `install.sh`, `run_pet.sh`, `requirements.txt`, `README.md`, `pet_config.json`, and `uninstall.sh` itself as the last step. The repo root `assets/`, root `README.md`, and Windows files are NOT deleted.
  - N keeps all `.mac/` files, so you can run `uninstall.sh` again later.
- Print `thank you for using my project - Chaitany`

After a Y delete, the empty `.mac/` folder itself remains. Delete that folder manually if you want it gone.

Manual uninstall, if you do not want to run `uninstall.sh`: `launchctl unload ~/Library/LaunchAgents/com.chaitanybuilds.claudeanimatedpet.plist && rm ~/Library/LaunchAgents/com.chaitanybuilds.claudeanimatedpet.plist`, then delete the `.mac/` folder. That is the entire footprint: no system daemons, no files outside your home folder.

## Troubleshooting

- **Pet does not appear after login:** run `bash .mac/run_pet.sh` manually first. If it appears, the pet code is fine and only autostart registration failed, re-run `bash .mac/install.sh`.
- **Pet runs but does not react to apps:** check System Settings → Privacy & Security → Accessibility / Automation, and grant permission to the terminal / Python app running the pet.
- **Pet does not appear at all:** check that PyQt5 installed, with `python3 -m pip install -r .mac/requirements.txt`, then run `python3 .mac/src/pet.py` from a terminal to see the error.
- **Click does nothing:** check that `claude` is on your `PATH`, or at `~/.local/bin/claude`. If it is not installed, the pet will say so instead of opening a terminal, by design.

## Credits and license

Same as the repo root: code is MIT, artwork in `assets/` is NOT MIT. See `../LICENSE` and `../ASSETS-LICENSE.md`. Mascot illustrations by GetIllustrations.com, do not sell, resell, or redistribute the `assets/` images as standalone files, and do not claim them as your own.
