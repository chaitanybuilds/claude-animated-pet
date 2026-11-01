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
- Greets you at login, and says bye before shutdown. It briefly holds shutdown just long enough to show the bye message.
- Launches fast at login. The installer registers a Scheduled Task (`ClaudeAnimatedPet`, runs at logon, highest run level, action is `run_pet.bat` in this folder) instead of a Startup-folder shortcut, so it does not hit Windows' 10-15 second startup delay. The task priority is set to 0 (realtime, the highest Task Scheduler priority), with StartWhenAvailable on, so it runs first at logon, ahead of normal Startup apps. The pet itself also tries realtime process priority first, then high, then above normal, in `set_process_priority_extreme()` in `src/pet.py`. It also bumps its own process priority on launch. If the pet does not appear after a reboot, first double-click `run_pet.bat` manually: if it appears, the pet code is fine and only the task failed — check Task Scheduler Library for `ClaudeAnimatedPet` and its Last Run Result, then run `install.bat` again as administrator.
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
- Main mascot is not static, and is kept separate from idle: every 2-3 jokes the talk mascot changes to a different main mascot from `assets/frames/` (7 main states), plus `assets/main_mascots/` if present (the 15 artboard mascots from the zip, not idle). `assets/idle_extras/` is NOT used in this cycle; idle fidgets alone use idle_extras, only after 10 minutes of no pet touch.
- Alt+F4 and window close are ignored on purpose, so the pet stays alive until shutdown. To quit manually, end the task in Task Manager.

## Install

Requirements: Windows 10/11, [Python 3.9+](https://www.python.org/downloads/) installed and on your `PATH` (check "Add python.exe to PATH" during setup).

1. Clone or download this repo, anywhere you like:
   ```
   git clone https://github.com/chaitanybuilds/claude-animated-pet.git
   ```
   The app saves its position file and loads its sprites relative to its own folder, so no fixed path is required.

2. Double-click `install.bat` inside that folder.
   The installer will ask for administrator rights once (a Windows permission prompt, click Yes). That is required because the fast logon task is registered at the highest run level, and Windows refuses that registration from a normal process with "Access is denied". If you click No, the installer exits without registering anything.
   This will:
   - `pip install` the dependencies (PyQt5, psutil, pywin32)
   - Register the Scheduled Task described above. Only if Task Scheduler registration still fails for another reason does it fall back to a silent Startup-folder shortcut instead (which launches about 10-15 seconds late).

3. Start it right now, without rebooting, by double-clicking `run_pet.bat`.

From your next login onward, it just shows up on its own.

### Uninstalling

Remove the Scheduled Task:
```
schtasks /Delete /TN "ClaudeAnimatedPet" /F
```
If it fell back to the Startup-folder method instead, delete `ClaudeAnimatedPet.vbs` from `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`. Then delete the project folder. That is the entire footprint: no registry entries, no background services.

## Project structure

```
claude-animated-pet/
├── src/pet.py                 # the app itself (PyQt5)
├── assets/frames/<state>/     # animation frames per pet state
├── assets/idle_extras/        # static poses used for 10-min idle fidgets and stats mascots
├── gen_sprites_mascot.py      # builds animated frames from mascot pack art
├── gen_sprites.py             # original procedural (hand-coded) blocky art
├── install.bat                # one-time setup + autostart registration
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
