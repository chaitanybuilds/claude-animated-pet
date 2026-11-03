# claude-animated-pet

A desktop pet for Windows and macOS that lives on your screen, reacts to what you are doing, and jumps you into Claude with one click.

The Windows version is in the repo root. The macOS version lives in `.mac/` — see [macOS](#macos) below and `.mac/README.md` for Mac install, uninstall, and differences. The Mac code shares the repo root `assets/` folder, so do not move `.mac/` out of the repo on its own.

> [!TIP]
> Built by [@chaitanybuilds](https://github.com/chaitanybuilds). Shared free of charge.

> [!CAUTION]
> Unofficial fan project. Not affiliated with, endorsed by, or sponsored by Anthropic. The name "Claude" is used only to describe compatibility with Claude / Claude Code. "Claude" and related marks belong to Anthropic.

![status](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-blue)
![license](https://img.shields.io/badge/license-MIT-green)

## What it does

- Transparent, draggable, always-on-top pixel pet. No window chrome, no taskbar icon.
- Greets you at login, and remembers where you left it.
- Reacts to the app in front of you, checked every 4 seconds. Discord, Chrome, VS Code, Claude, Steam, Unity, and Unity Hub each get their own 50-line pool of English, sarcastic, dark/funny one-liners. Unknown apps get a confused line, music apps switch it to a vibing animation.
- Reacts to terminals too, each with its own 50-line pool: PowerShell, cmd, Git, Node, Python, Windows Terminal, and WSL. On macOS, all terminal apps share one generic terminal pool.
- Detects Claude Code automatically in the background. When it starts, the pet says one Claude Code joke, then switches the 30-second joke pool to the Claude Code pool until it stops.
- Watches system stats on a separate timer: RAM at 75% or more, CPU at 80% or more, or temperature at 50°C or more. Each trigger has 20 jokes, a 5-minute cooldown, and its own mascot. Temperature is best-effort.
- Tells a random coding joke every 30 seconds.
- Click it to open a terminal and run `claude`: `cmd.exe` on Windows, Terminal.app on macOS. It never closes that terminal, and if Claude Code is not installed, it says so directly instead of opening anything.
- Drag it anywhere for a random drag line, drop it for a random drop line.
- After 10 minutes untouched, it does idle fidgets from `assets/idle_extras/` every 45-110 seconds, until you interact again.
- After exactly 3 jokes, its talk mascot changes to another mascot from the joke pool, excluding special-state mascots.
- Window close is ignored on purpose. To quit manually, end the task in Task Manager on Windows, or quit `pet.py` from Activity Monitor on macOS.

## Install

### Windows

Requirements: Windows 10/11, [Python 3.9+](https://www.python.org/downloads/) installed and on your `PATH` (check "Add python.exe to PATH" during setup).

1. Clone or download this repo, anywhere you like:
   ```
   git clone https://github.com/chaitanybuilds/claude-animated-pet.git
   ```
   The app saves its position file and loads its sprites relative to its own folder, so no fixed path is required.
2. Double-click `install.bat` inside that folder. No administrator rights are needed. It will `pip install` the dependencies (PyQt5, psutil, pywin32), create the Startup shortcut, and delete an old `ClaudeAnimatedPet` Scheduled Task once if one is still present.
3. Start it right now, without rebooting, by double-clicking `run_pet.bat`.

From your next login onward, it just shows up on its own. Windows staggers Startup apps by about 10-15 seconds after login, so the pet appears in about 10-15 seconds, not instantly. That delay is accepted for reliability.

#### Uninstalling (Windows)

Double-click `uninstall.bat` inside the project folder. It runs as administrator, because deleting the old Scheduled Task (if present) needs admin rights.

It will, in order, delete the Startup shortcut `ClaudeAnimatedPet.vbs`, delete the old Scheduled Task if present, try to stop the running pet process (best effort, only processes whose command line contains `pet.py`), and ask: Do you want to DELETE the project files too? (y/n) [Y = delete, N = keep]. Y deletes ONLY the project files in this folder, any other file is left untouched, then it prints `thank you for using my project - Chaitany` and closes.

Manual uninstall: delete `ClaudeAnimatedPet.vbs` from the Startup folder, delete the old task once with `schtasks /Delete /TN "ClaudeAnimatedPet" /F` if present, then delete the project folder.

### macOS

Requirements: macOS 11+, Python 3.9+ on your `PATH` as `python3` (`brew install python3` is the easiest route if you use Homebrew).

1. Clone or download this repo, anywhere you like:
   ```
   git clone https://github.com/chaitanybuilds/claude-animated-pet.git
   ```
   The macOS port lives in `.mac/` and shares the repo root `assets/` folder, so do not move `.mac/` out of the repo on its own.
2. From the repo root, run the Mac installer:
   ```
   chmod +x .mac/*.sh
   .mac/install.sh
   ```
   Or, without changing permissions: `bash .mac/install.sh`
   No `sudo` is needed. It will `pip install` the dependencies from `.mac/requirements.txt` (PyQt5, psutil, and `pyobjc-framework-Cocoa` on macOS only), and register a per-user LaunchAgent at `~/Library/LaunchAgents/com.chaitanybuilds.claudeanimatedpet.plist`, so it starts at every login.
3. Start it right now, without logging out, with `bash .mac/run_pet.sh`.

First run only: macOS will likely prompt for Accessibility and/or Automation permission the first time the pet tries to read the frontmost app or open Terminal. Grant it once in **System Settings → Privacy & Security**. If you skip it, the pet still runs and drags around fine, it just will not react to the app in front of you.

Full Mac instructions, differences, and troubleshooting are in `.mac/README.md`.

#### Uninstalling (macOS)

```
bash .mac/uninstall.sh
```

It unloads and deletes the LaunchAgent, tries to stop the running pet, and asks: Do you want to DELETE the project files too? (y/n) [Y = delete, N = keep]. Y deletes ONLY the files inside `.mac/` (`src/`, `install.sh`, `run_pet.sh`, `requirements.txt`, `README.md`, `pet_config.json`, and `uninstall.sh` itself last). The repo root `assets/`, root `README.md`, and Windows files are NOT deleted. After a Y delete, the empty `.mac/` folder itself remains, delete it manually if you want it gone.

Manual uninstall: `launchctl unload ~/Library/LaunchAgents/com.chaitanybuilds.claudeanimatedpet.plist && rm ~/Library/LaunchAgents/com.chaitanybuilds.claudeanimatedpet.plist`, then delete the `.mac/` folder.

## Project structure

```
claude-animated-pet/
├── src/pet.py                 # the app itself (PyQt5), Windows version
├── .mac/                      # macOS port: .mac/src/pet.py, .mac/install.sh, .mac/run_pet.sh, .mac/uninstall.sh, .mac/requirements.txt, .mac/README.md — shares the repo root assets/ folder
├── assets/frames/<state>/     # animation frames per pet state
├── assets/idle_extras/        # static poses used for 10-min idle fidgets and stats mascots
├── gen_sprites_mascot.py      # builds animated frames from mascot pack art
├── gen_sprites.py             # original procedural (hand-coded) blocky art
├── install.bat                # one-time setup + Startup autostart registration, no Task Scheduler
├── uninstall.bat              # admin uninstaller, Startup + old task delete, Y/N project-files-only delete
├── run_pet.bat                # manual launch
├── requirements.txt
├── LICENSE                    # MIT, code/docs only, NOT assets/
├── ASSETS-LICENSE.md          # artwork license (assets/ is NOT MIT)
├── .gitignore                 # __pycache__/, *.pyc, pet_config.json, .vscode/, .idea/
└── pet_config.json            # auto-created; remembers screen position
```

## Customizing

- App reactions: edit the app lists near the top of `src/pet.py`, for example `_DISCORD_BASE` / `_EXTRA`, `_CHROME_BASE` / `_EXTRA`. Each app's final 50-line pool is built by `_expand_pool()` from those plus template filler, keyed by Windows process name (for example `"code.exe"`). On macOS, edit `.mac/src/pet.py` instead, and add the Mac app name to `MAC_APP_NAME_MAP` there, which translates it to the same Windows-style key, so a new app only needs adding once.
- Terminal reactions: edit `_POWERSHELL_POOL`, `_CMD_POOL`, `_GIT_POOL`, `_NODE_POOL`, `_PYTHON_POOL`, `_TERMINAL_POOL`, `_WSL_POOL` in `src/pet.py`. Each is 50 hand-written lines, no template filler.
- Stats reactions: edit `_RAM_STATS`, `_CPU_STATS`, `_TEMP_STATS` in `src/pet.py`, and the thresholds `RAM_THRESHOLD`, `CPU_THRESHOLD`, `TEMP_THRESHOLD_C`, and cooldown `STATS_COOLDOWN_S`.
- Jokes: edit the `CODING_JOKES` list.
- Idle fidgets: drop a `.png` into `assets/idle_extras/`. It will get picked up automatically. Give it a line in `FIDGET_CAPTIONS` (keyed by filename without `.png`) or it will just use a humanized version of the filename.
- Animations: edit `assets/frames/<state>/`, or regenerate with `python gen_sprites_mascot.py <path-to-source-art>`. The ping-pong loop and sine bob live in `_tick_animation` / `_apply_bob` in `src/pet.py`.
- Idle timing: change `IDLE_FIDGET_AFTER_MS` (default 10 min) and `IDLE_FIDGET_INTERVAL_RANGE` (default 45-110 seconds between fidgets once idle) near the top of `src/pet.py`.
- Polling: change `app_timer.start(4_000)` (foreground-app check), `joke_timer.start(30_000)` (jokes), `fidget_timer.start(30_000)` (idle check), and `stats_timer.start(30_000)` (system stats check) in `PetWidget.__init__`.

## Platform notes

**Windows and macOS are both supported.** The Windows version is in the repo root, the macOS version is in `.mac/`, and both share the same jokes, pools, timers, and repo root `assets/`. The differences are:

- **Foreground-app detection.** Windows uses `pywin32` (`GetForegroundWindow` → PID → `psutil`). macOS uses AppKit `NSWorkspace` (via the optional `pyobjc-framework-Cocoa` dependency) when installed, and falls back automatically to `osascript` / System Events if it is not, so this never hard-fails on a minimal Mac install, it just gets a little slower per check.
- **Per-shell terminal pools** (PowerShell, cmd, Git, Node, Python, WSL) are Windows-only. macOS can only see which terminal app is in front (Terminal, iTerm2, Warp, Hyper, Alacritty, kitty), not which shell is running inside it, so all of those map to one shared "terminal" pool there.
- **Process priority boost** uses Windows priority classes (realtime → high → above-normal) on Windows, and a best-effort `os.nice(-10)` on macOS, silently ignored if macOS refuses it for a non-root user, which is normal, not a bug.
- **Shutdown "bye" bubble** only fires on Windows (`WM_QUERYENDSESSION`). macOS has no equivalent hook, so logging out simply quits the pet.
- **Click-to-launch Claude** opens `cmd.exe` on Windows and Terminal.app on macOS (via `osascript`). On both, the pet never closes that terminal itself, and shows a plain-English not-installed message instead of opening anything if the `claude` CLI is not installed.
- **Auto-start at login** is the Windows Startup folder on Windows, and a per-user LaunchAgent (`~/Library/LaunchAgents`) on macOS. Neither installer needs admin/sudo.
- **Linux** is not a target of this repo (no installer/autostart script is provided), but the pet still runs there with reduced functionality: rendering, dragging, and timers work, while Windows/macOS-only detection stays silent rather than erroring.

## Disclaimer

> [!CAUTION]
> This is an unofficial, non-commercial fan project. It is not an Anthropic product, and it is not affiliated with, endorsed by, or sponsored by Anthropic. The mascot art is not official Anthropic artwork. Nothing in this repo claims ownership of the "Claude" name or marks, or of the third-party illustration pack used for the mascot art.

## Credits

> [!TIP]
> Illustrations by [GetIllustrations.com](https://getillustrations.com) — mascot artwork from the [Claude Mascot Pack](https://getillustrations.com/illustration-pack/claude-mascot-pack).

> [!CAUTION]
> The images in `assets/frames/` and `assets/idle_extras/` are derived from that pack, so the same artwork rules apply to them. This artwork is NOT covered by this repo's MIT license, and it is NOT owned by the author of this repo. It is used under GetIllustrations' Free License, which requires this visible credit. See [ASSETS-LICENSE.md](ASSETS-LICENSE.md) and GetIllustrations' own license page: https://getillustrations.com/license — if that page and this summary ever differ, the original license governs.

Everything in `src/`, `gen_sprites*.py`, and the installer scripts is original code and is covered by the MIT license below, except where a file itself says otherwise.

## License

> [!TIP]
> Code and documentation: MIT — see [LICENSE](LICENSE). The MIT license applies only to the original code/documentation, not to the artwork.
> [!CAUTION]
> Artwork in `assets/`: NOT MIT. See [ASSETS-LICENSE.md](ASSETS-LICENSE.md). Do not sell, resell, or redistribute the `assets/` images as standalone files, and do not claim them as your own. If you fork this repo, keep the credit above and the `ASSETS-LICENSE.md` file intact.

> [!CAUTION]
> This project is shared free of charge. Selling a bundle that includes the `assets/` artwork would break the artwork license, even though the code itself is MIT.
