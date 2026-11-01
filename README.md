# claude-animated-pet

A desktop pet for Windows that lives on your screen, reacts to what you are doing, and jumps you into Claude with one click.

> [!TIP]
> Built by [@chaitanybuilds](https://github.com/chaitanybuilds). Shared free of charge.

> [!CAUTION]
> Unofficial fan project. Not affiliated with, endorsed by, or sponsored by Anthropic. The name "Claude" is used only to describe compatibility with Claude / Claude Code. "Claude" and related marks belong to Anthropic.

![status](https://img.shields.io/badge/platform-Windows-blue)
![license](https://img.shields.io/badge/license-MIT-green)

## What it does

- Transparent, draggable, always-on-top pixel pet. No window chrome, no taskbar icon.
- Greets you at login with the welcome mascot. It attempts a bye message on shutdown/restart, but Windows covers the desktop with its shutdown screen, so the bye bubble is not reliably visible on restart. The pet does NOT block shutdown any more, so there is no background-apps warning screen on restart, and restart stays clean. The pet comes back via Startup in about 15 seconds.
- Launches at login via the Startup folder. The installer creates a Startup shortcut (`ClaudeAnimatedPet.vbs` in the Windows Startup folder, action is `run_pet.bat` in this folder), not a Scheduled Task. Task Scheduler was removed because it was unreliable on this PC: it was created with SUCCESS but did not run after reboot, and its priority step failed. Windows staggers Startup apps by about 10-15 seconds after login, so the pet appears in about 10-15 seconds, not instantly. That delay is accepted for reliability. The pet itself still tries realtime process priority first, then high, then above normal, in `set_process_priority_extreme()` in `src/pet.py`, but without an admin task token it will usually fall back to high. If the pet does not appear after a reboot, first double-click `run_pet.bat` manually: if it appears, the pet code is fine and only Startup failed — check the Startup folder for `ClaudeAnimatedPet.vbs`, and that no old `ClaudeAnimatedPet` task is still present in Task Scheduler Library (delete it once if it is, otherwise the pet may launch twice).
- Reacts to the app in front of you, checked every 4 seconds. Each known app gets its own 50-line pool of random one-liners, in English, sarcastic and dark/funny. You are not expected to answer, it is just commentary.
  - Discord, Chrome, VS Code, Claude, Steam, Unity, Unity Hub
  - Any app it does not recognise gets one of 3 confused lines. Music apps (Spotify, Windows Media Player, Groove, Music) switch it to a bouncier "vibing" animation with the fixed line "nice track, vibing with you 🎶".
- Reacts to terminals too, each with its own 50-line pool, also English, sarcastic and dark/funny:
  - PowerShell (`powershell.exe`, `pwsh.exe`)
  - cmd (`cmd.exe`, `conhost.exe`)
  - Git (`git.exe`, `git-bash.exe`, Git's `bash.exe`)
  - Node (`node.exe`)
  - Python (`python.exe`)
  - Windows Terminal (`WindowsTerminal.exe`, `wt.exe`)
  - WSL (`wsl.exe`, `wslhost.exe`, System32 `bash.exe`)
  - `bash.exe` is resolved by its exe path, and `conhost.exe` by its parent shell, so Git Bash and WSL are not mixed up. `pythonw.exe` stays ignored, because that is how the pet itself runs.
- Claude Code: detected automatically, not just when its window is foreground. The pet scans running processes every 4 seconds for `claude.exe` whose exe path is in `.local\bin` (the Claude Code CLI launcher, e.g. `%USERPROFILE%\.local\bin\claude.exe`), plus a node.exe fallback whose command line contains claude and .local. When Claude Code starts, the pet says one extreme dark funny Claude Code joke once, then the 30-second joke pool switches to the 50-line Claude Code pool until Claude Code stops. If the foreground window itself is `claude.exe` from `.local\bin`, it also uses the Claude Code pool instead of the generic Claude app pool.
- Watches your system, on a separate timer, so app jokes and idle fidgets keep working:
  - RAM at 75% or more of total RAM: 20 jokes, mascot `system-monitoring-dashboard.png`
  - CPU at 80% or more: 20 jokes, mascot `processing-logic-symbols.png`
  - Temperature at 50°C or more: 20 jokes, mascot `fine-under-pressure.png`
  - Each trigger has a 5-minute cooldown, and if several fire at once only one is picked, so it does not spam. Temperature is best-effort on Windows: `psutil` does not report it there, so the code falls back to `nvidia-smi` if present, otherwise that trigger stays silent while RAM and CPU keep working.
- Tells a random coding joke every 30 seconds. If the foreground app is a known app or terminal, that app's pool is added to the joke pool for that round.
- Click it and it opens a terminal and runs the `claude` CLI, then closes that terminal once Claude is found or after 25 seconds. The pet says "launching claude for you..." first, then "LETS CODE 💻🔥".
- Drag it anywhere for a random drag line (15 in the pool), drop it for a random drop line (15 in the pool). It remembers where you left it, every reboot.
- Goes quiet for 10 minutes, then starts doing its own thing. If nobody has touched it for 10 minutes, it fires a random idle pose from `assets/idle_extras/` every 45-110 seconds, each with its own caption, until you interact again.
- Pixel-art animation built from static source art with transforms (bob, sway, squash/stretch, rotate). The frame loop ping-pongs instead of snapping back to frame 0, with a subtle sine-wave bob on top.
- Main mascot is not static: after exactly 3 jokes the talk mascot changes to a different mascot from the joke pool. The joke pool is all mascots except the special-state ones, which stay only for their own state: idle/default, drag, drop, welcome, bye, and confuse, plus click/launch. In practice that is `assets/idle_extras/` minus those special files, plus `assets/main_mascots/` if present (the 15 artboard mascots from the zip). So the welcome mascot will never joke, the drag mascot will only appear while dragging, and so on. Idle fidget logic stays separate: it only fires after 10 minutes of no pet touch, on its own timer, even though it picks from the same idle_extras folder. Touching the pet does not reset the joke counter, and the new mascot applies immediately in the talk state, it does not wait for a touch.
- Alt+F4 and window close are ignored on purpose, so the pet stays alive until shutdown. To quit manually, end the task in Task Manager.

## Install

Requirements: Windows 10/11, [Python 3.9+](https://www.python.org/downloads/) installed and on your `PATH` (check "Add python.exe to PATH" during setup).

1. Clone or download this repo, anywhere you like:
   ```
   git clone https://github.com/chaitanybuilds/claude-animated-pet.git
   ```
   The app saves its position file and loads its sprites relative to its own folder, so no fixed path is required.

2. Double-click `install.bat` inside that folder.
   No administrator rights are needed any more, because there is no Scheduled Task to register. If an old `ClaudeAnimatedPet` task is still present, the installer tries to delete it once, so the pet does not launch twice. If that delete fails without admin rights, delete the old task once manually from Task Scheduler Library.
   This will:
   - `pip install` the dependencies (PyQt5, psutil, pywin32)
   - Create the Startup shortcut described above, compulsory, not a fallback.

3. Start it right now, without rebooting, by double-clicking `run_pet.bat`.

From your next login onward, it just shows up on its own.

### Uninstalling

Double-click `uninstall.bat` inside the project folder. It runs as administrator, because deleting the old Scheduled Task (if present) needs admin rights.

It will, in order:
- Delete the Startup shortcut `ClaudeAnimatedPet.vbs` from `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`
- Delete the old Scheduled Task `ClaudeAnimatedPet`, if present, so the pet does not launch twice
- Try to stop the running pet process, best effort only, only processes whose command line contains `pet.py`
- Ask: Do you want to DELETE the project files too? (y/n) [Y = delete, N = keep]
  - Y deletes ONLY the project files in this folder: `src/`, `assets/`, `.git/`, `gen_sprites.py`, `gen_sprites_mascot.py`, `install.bat`, `run_pet.bat`, `requirements.txt`, `LICENSE`, `ASSETS-LICENSE.md`, `README.md`, `.gitignore`, `pet_config.json`, and `uninstall.bat` itself as the last step. Any other file in this folder is left untouched.
  - N keeps all project files, so you can run `uninstall.bat` again later.
- Print `thank you for using my project - Chaitany`, wait for a key press, then close the terminal.

Manual uninstall, if you do not want to run `uninstall.bat`: delete `ClaudeAnimatedPet.vbs` from the Startup folder above, delete the old task once with `schtasks /Delete /TN "ClaudeAnimatedPet" /F` if present, then delete the project folder. That is the entire footprint: no registry entries, no background services.

## Project structure

```
claude-animated-pet/
├── src/pet.py                 # the app itself (PyQt5)
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

- App reactions: edit the app lists near the top of `src/pet.py`, for example `_DISCORD_BASE` / `_EXTRA`, `_CHROME_BASE` / `_EXTRA`. Each app's final 50-line pool is built by `_expand_pool()` from those plus template filler, keyed by Windows process name (for example `"code.exe"`).
- Terminal reactions: edit `_POWERSHELL_POOL`, `_CMD_POOL`, `_GIT_POOL`, `_NODE_POOL`, `_PYTHON_POOL`, `_TERMINAL_POOL`, `_WSL_POOL` in `src/pet.py`. Each is 50 hand-written lines, no template filler.
- Stats reactions: edit `_RAM_STATS`, `_CPU_STATS`, `_TEMP_STATS` in `src/pet.py`, and the thresholds `RAM_THRESHOLD`, `CPU_THRESHOLD`, `TEMP_THRESHOLD_C`, and cooldown `STATS_COOLDOWN_S`.
- Jokes: edit the `CODING_JOKES` list.
- Idle fidgets: drop a `.png` into `assets/idle_extras/`. It will get picked up automatically. Give it a line in `FIDGET_CAPTIONS` (keyed by filename without `.png`) or it will just use a humanized version of the filename.
- Animations: edit `assets/frames/<state>/`, or regenerate with `python gen_sprites_mascot.py <path-to-source-art>`. The ping-pong loop and sine bob live in `_tick_animation` / `_apply_bob` in `src/pet.py`.
- Idle timing: change `IDLE_FIDGET_AFTER_MS` (default 10 min) and `IDLE_FIDGET_INTERVAL_RANGE` (default 45-110 seconds between fidgets once idle) near the top of `src/pet.py`.
- Polling: change `app_timer.start(4_000)` (foreground-app check), `joke_timer.start(30_000)` (jokes), `fidget_timer.start(30_000)` (idle check), and `stats_timer.start(30_000)` (system stats check) in `PetWidget.__init__`.

## Platform notes

App detection, auto-start at login, shutdown hook, and Claude launch all depend on Windows-only APIs (`pywin32`, foreground window polling, `ShutdownBlockReasonCreate`). On macOS/Linux only the pet rendering, dragging, and timers will run.

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
