# claude-animated-pet

A desktop pet that lives on your Windows screen, reacts to whatever app
you're using, and helps you jump into Claude Code with one click.

Built by [@chaitanybuilds](https://github.com/chaitanybuilds).

![status](https://img.shields.io/badge/platform-Windows-blue)
![license](https://img.shields.io/badge/license-MIT-green)

## Features

- Transparent, draggable, always-on-top sprite sitting on your desktop —
  no window chrome, no taskbar icon, just the pet.
- Greets you at login with a welcome bubble, and says bye before shutdown
  (briefly holds shutdown just long enough to show the message).
- Launches right away instead of 10-15s late. The old Startup-folder
  shortcut hit Windows' built-in startup stagger delay; the installer now
  registers a Scheduled Task (`ONLOGON`, highest run level) instead, which
  fires immediately. The process also bumps its own scheduling priority
  (realtime, then high, then above-normal, whichever Windows grants) on
  launch.
- Reacts to the app you're using, checked every few seconds:
  - Discord, Chrome, VS Code, Claude desktop, Steam, Unity and Unity Hub
    each have their own pool of 50 app-specific one-liners/questions it
    randomly throws at you (you're not expected to answer, it's just
    commentary).
  - Any app it doesn't recognize gets "what is this place?" (a few
    variants).
  - Music apps playing switches it into a bouncier "vibing" animation.
- Random coding jokes, now including dev-level dark humor (burnout,
  on-call, legacy code, the usual) in a speech bubble every 30 seconds.
- Click it and it finds the Claude Desktop app via its Start Menu shortcut
  (no hardcoded `claude.exe` path, since the installed exe lives in a
  version-numbered folder that changes on every auto-update) and launches
  it directly — no terminal window, no `claude` CLI call.
- Drag it anywhere on your desktop for one of 15 random lines while
  dragging, another 15 when you drop it. Remembers where you left it,
  every time you reboot.
- Goes quiet for 30 minutes, then does its own thing. If nobody's touched
  it for half an hour, it starts firing off little idle quirks every
  45-110s — random poses pulled from `assets/idle_extras/` (debugging,
  rage-coffee, shipping a rocket, crying at merge conflicts, etc.) each
  with its own caption, until you interact with it again.
- Pixel-art mascot animation — bob, sway, squash/stretch, rotate — all
  built from static source art via pure transform animation (no
  frame-by-frame hand-drawing needed), so new poses are easy to add. The
  frame loop now ping-pongs instead of snapping back to frame 0, plus a
  subtle sine-wave bob layered on top, for smoother idle/talk/vibe motion.

## Install (first time)

Requirements: Windows 10/11, [Python 3.9+](https://www.python.org/downloads/)
installed and on your `PATH` (check "Add python.exe to PATH" during setup).

1. Clone or download this repo, anywhere you like:
   ```
   git clone https://github.com/chaitanybuilds/claude-animated-pet.git
   ```
   The app saves its position file and loads its sprites relative to its own
   folder, so no fixed path is required — put it in `Documents`, `Desktop`,
   wherever.

2. Run the installer. Double-click `install.bat` inside that folder.
   The installer will ask for administrator rights once (a Windows
   permission prompt - click Yes). That is required because the fast
   logon task is registered at the highest run level, and Windows
   refuses that registration from a normal process with
   "Access is denied". If you click No, the installer exits without
   registering anything.
   This will:
   - `pip install` the dependencies (PyQt5, psutil, pywin32)
   - register a Scheduled Task (`ClaudeAnimatedPet`, runs at logon, highest
     run level) so the pet launches automatically, with no console window
     and without the ~10s delay Windows adds to classic Startup-folder
     apps, every time you log in. Only if Task Scheduler registration
     still fails for another reason does it fall back to a silent
     Startup-folder shortcut instead (which launches about 10-15s late).

3. Start it right now, without rebooting, by double-clicking `run_pet.bat`.

That's it — from your next login onward, it just shows up on its own.

### Uninstalling

Remove the Scheduled Task:
```
schtasks /Delete /TN "ClaudeAnimatedPet" /F
```
If it fell back to the Startup-folder method instead, delete
`ClaudeAnimatedPet.vbs` from
`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`. Then delete the
project folder. That's the entire footprint — no registry entries, no
background services.

## Project structure

```
claude-animated-pet/
├── src/pet.py        # the app itself (PyQt5)
├── assets/frames/<state>/    # animation frames per pet state
├── assets/idle_extras/       # static poses used for 30-min-idle fidgets
├── gen_sprites_mascot.py     # builds animated frames from mascot pack art
├── gen_sprites.py            # original procedural (hand-coded) blocky art
├── install.bat                # one-time setup + autostart registration
├── run_pet.bat                 # manual launch
├── requirements.txt
└── pet_config.json            # auto-created; remembers screen position
```

## Customizing

- Add or change app reactions by editing the `_DISCORD_BASE`/`_EXTRA`,
  `_CHROME_BASE`/`_EXTRA`, etc. lists near the top of `src/pet.py`. Each
  app's final 50-line pool is built by `_expand_pool()` from those plus
  template filler, keyed by Windows process name (e.g. `"code.exe"`).
- Add or change jokes by editing the `CODING_JOKES` list.
- Add idle fidgets by dropping a `.png` into `assets/idle_extras/`. It'll
  get picked up automatically. Give it a line in `FIDGET_CAPTIONS` (keyed
  by filename without `.png`) or it'll just use a humanized version of
  the filename.
- Change animations by editing `assets/frames/<state>/`, or regenerate
  with `python gen_sprites_mascot.py <path-to-source-art>` — see the
  comments at the top of that file for how each state's motion is built.
  The ping-pong loop and sine bob live in `_tick_animation`/`_apply_bob`
  in `src/pet.py`.
- Change idle-fidget timing via `IDLE_FIDGET_AFTER_MS` (default 30 min)
  and `IDLE_FIDGET_INTERVAL_RANGE` (default 45-110s between fidgets once
  idle) near the top of `src/pet.py`.
- Change polling frequency via `app_timer.start(4_000)` (foreground-app
  check) and `joke_timer.start(30_000)` (jokes) in `PetWidget.__init__`.

## Platform notes

The app-detection, auto-start-at-login, shutdown hook, and Claude-launch
features all depend on Windows-only APIs (`pywin32`, foreground window
polling, `ShutdownBlockReasonCreate`). On macOS/Linux only the pet
rendering, dragging and timers will run.

## Credits

Mascot artwork adapted from a third-party Claude Mascot Pack illustration
pack: [Claude Mascot Pack](https://getillustrations.com/illustration-pack/claude-mascot-pack).
That art has its own license terms from its creator, separate from
this repo's code — check the pack's source page before redistributing the
`assets/` images themselves beyond personal use. Everything in `src/`,
`gen_sprites*.py`, and the installer scripts is original and covered by the
MIT license below.

## License

MIT — see [LICENSE](LICENSE). Free to use, modify, and share.
