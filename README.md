# claude-animated-pet

A desktop pet that lives on your Windows screen, reacts to whatever app
you're using, and helps you jump into Claude Code with one click.

Built by [@chaitanybuilds](https://github.com/chaitanybuilds).

![status](https://img.shields.io/badge/platform-Windows-blue)
![license](https://img.shields.io/badge/license-MIT-green)

## Features

- **Transparent, draggable, always-on-top sprite** sitting on your desktop —
  no window chrome, no taskbar icon, just the pet.
- **Greets you at login** with a welcome bubble, and **says bye before
  shutdown** (briefly holds shutdown just long enough to show the message).
- **Reacts to the app you're using**, checked every few seconds:
  - **Discord, Chrome, VS Code, Claude desktop, Steam, Unity** each have
    their own pool of app-specific one-liners/questions it randomly throws
    at you (you're not expected to answer — it's just commentary).
  - Any app it doesn't recognize → *"what is this place?"* (a few variants).
  - Music apps playing → switches into a bouncier "vibing" animation.
- **Random coding jokes/questions** in a speech bubble every 30 seconds.
- **Click it** → opens a terminal, runs `claude`, waits for the Claude
  desktop app to actually open, closes the terminal, then hypes you up to
  start coding.
- **Drag it anywhere** on your desktop → reacts while dragging and when you
  drop it. Remembers where you left it, every time you reboot.
- **Pixel-art mascot animation** — bob, sway, squash/stretch, rotate — all
  built from static source art via pure transform animation (no frame-by-frame
  hand-drawing needed), so new poses are easy to add.

## Install (first time)

**Requirements:** Windows 10/11, [Python 3.9+](https://www.python.org/downloads/)
installed and on your `PATH` (check "Add python.exe to PATH" during setup).

1. **Clone or download this repo**, anywhere you like:
   ```
   git clone https://github.com/chaitanybuilds/claude-animated-pet.git
   ```
   The app saves its position file and loads its sprites relative to its own
   folder, so no fixed path is required — put it in `Documents`, `Desktop`,
   wherever.

2. **Run the installer.** Double-click `install.bat` inside that folder.
   This will:
   - `pip install` the dependencies (PyQt5, psutil, pywin32)
   - create a silent startup shortcut (`ClaudeAnimatedPet.vbs`) in your Windows
     Startup folder, so the pet launches automatically — with no console
     window — every time you log in.

3. **Start it right now** (without rebooting) by double-clicking
   `run_pet.bat`, or the `.vbs` file the installer just created.

That's it — from your next login onward, it just shows up on its own.

### Uninstalling

Delete the `.vbs` file from:
`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`
and delete the project folder. That's the entire footprint — no registry
entries, no background services.

## Project structure

```
claude-animated-pet/
├── src/pet.py        # the app itself (PyQt5)
├── assets/frames/<state>/    # animation frames per pet state
├── gen_sprites_mascot.py     # builds animated frames from mascot pack art
├── gen_sprites.py            # original procedural (hand-coded) blocky art
├── install.bat                # one-time setup + autostart registration
├── run_pet.bat                 # manual launch
├── requirements.txt
└── pet_config.json            # auto-created; remembers screen position
```

## Customizing

- **Add/change app reactions:** edit `APP_QUESTIONS` and `KNOWN_APPS` in
  `src/pet.py` — keyed by Windows process name (e.g. `"code.exe"`).
- **Add/change jokes:** edit the `CODING_JOKES` list.
- **Change animations:** edit `assets/frames/<state>/` or regenerate with
  `python gen_sprites_mascot.py <path-to-source-art>` — see the comments at
  the top of that file for how each state's motion is built.
- **Change polling frequency:** `app_timer.start(4_000)` (foreground-app
  check) and `joke_timer.start(30_000)` (jokes) in `PetWidget.__init__`.

## Platform notes

The app-detection, auto-start-at-login, shutdown hook, and terminal-launch
features all depend on Windows-only APIs (`pywin32`, foreground window
polling, `ShutdownBlockReasonCreate`). On macOS/Linux only the pet
rendering, dragging and timers will run.

## Credits

Mascot artwork adapted from a third-party **Claude Mascot Pack** illustration
pack. That art has its own license terms from its creator, separate from
this repo's code — check the pack's source page before redistributing the
`assets/` images themselves beyond personal use. Everything in `src/`,
`gen_sprites*.py`, and the installer scripts is original and covered by the
MIT license below.

## License

MIT — see [LICENSE](LICENSE). Free to use, modify, and share.
