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

- **App reactions:** via AppKit `NSWorkspace` when `pyobjc-framework-Cocoa` is installed, with an automatic fallback to `osascript` / System Events if it is not. Mac app names are translated in `MAC_APP_NAME_MAP` to the same keys Windows uses, so no duplicate joke pools.
- **Terminals:** Terminal, iTerm2, Warp, Hyper, Alacritty, and kitty all share one generic terminal pool. Per-shell pools (PowerShell, cmd, Git, Node, Python, WSL) stay Windows-only.
- **Claude Code:** detected automatically in the background, same as Windows, from `~/.local/bin/claude` plus a `node` fallback.
- **Click-to-launch:** opens Terminal.app and runs `claude` there. It never closes that terminal, and if Claude Code is not installed, it says so directly instead of opening anything.
- **Process priority:** a best-effort `os.nice(-10)`, silently ignored if macOS refuses it for a non-root user.
- **Bye bubble:** Windows-only. On macOS, logging out simply quits the pet.
- **Closing the pet:** window close is ignored, same as Windows. Quit the `pet.py` process from Activity Monitor. Its position is saved to `.mac/pet_config.json`.
- **Stats, jokes, and idle fidgets:** same as Windows, on the same timers. Temperature is best-effort.
- **Linux:** not a target of this repo, but the pet still runs there with reduced functionality.

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
