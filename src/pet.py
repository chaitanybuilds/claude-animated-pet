"""
claude-animated-pet - an animated desktop companion for Claude Code.
Windows-focused PyQt5 app:
 - transparent, always-on-top, frameless, draggable sprite
 - greets you on login
 - launches via a Scheduled Task (not the Startup folder) and boosts its
   own process priority, so it shows up right away instead of 10-15s late
 - watches the foreground process, reacts per-app with a 50-line pool of
   random questions you're not expected to answer ("what is this place?"
   for unknown apps, vibes to music)
 - click => resolves the Claude Desktop app's Start Menu shortcut (never a
   hardcoded exe path) and launches it directly, no terminal involved
 - every 30s: random coding joke/question (incl. dev-level dark humor) in
   a speech bubble
 - drag => one of 15 random lines ; drop => another 15
 - 30 min with zero interaction => starts doing its own idle fidgets,
   random poses from assets/idle_extras/, every 45-110s until touched again
 - on shutdown/logoff => says bye (briefly delays shutdown)
"""

import os
import sys
import json
import math
import random
import subprocess
import time

from PyQt5.QtCore import Qt, QTimer, QPoint, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QPainter, QFont, QColor, QFontMetrics, QRegion
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout

try:
    import psutil
except ImportError:
    psutil = None

IS_WINDOWS = sys.platform.startswith("win")

if IS_WINDOWS:
    try:
        import win32gui
        import win32process
        import win32con
        import win32api
    except ImportError:
        win32gui = None
else:
    win32gui = None

# Everything is resolved relative to this script's own folder, so the repo
# works no matter where someone clones/installs it.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(BASE_DIR, "assets")
FRAMES_DIR = os.path.join(ASSETS, "frames")
IDLE_EXTRAS_DIR = os.path.join(ASSETS, "idle_extras")
CONFIG_PATH = os.path.join(BASE_DIR, "pet_config.json")

SPRITE_SIZE = 150  # on-screen pet size (px)

# how long (ms) the pet has to go completely untouched (no drag, no click)
# before it starts doing its own little idle quirks
IDLE_FIDGET_AFTER_MS = 30 * 60 * 1000
# once that threshold is crossed, roughly how often (seconds, min/max) it
# fires off another one — randomized so it doesn't feel like a cron job
IDLE_FIDGET_INTERVAL_RANGE = (45, 110)

# Content: jokes, per-app questions, unknown-app lines

CODING_JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "There are 10 types of people: those who understand binary and those who don't.",
    "Why did your code break in production? It worked on his machine!",
    "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'",
    "!false — it's funny because it's true.",
    "99 little bugs in the code, 99 little bugs... Take one down, patch it around, 127 little bugs in the code.",
    "Quick one: what's the time complexity of your patience right now?",
    "Why do Java devs wear glasses? Because they can't C#.",
    "I'd tell you a UDP joke but you might not get it.",
    "Real talk: have you committed in the last hour or are we living dangerously?",
    "Why was the function sad after calling another function? It didn't get a callback.",
    "Pop quiz: what does 'git commit -m fix' actually fix?",
    "There's no place like 127.0.0.1.",
    "Why did the developer go broke? Because he used up all his cache.",
    "Be honest — is that variable named 'temp2' still there from 3 months ago?",
    "Knock knock. Who's there? Race condition. Race condition who? *crash before you can answer*",
    "Why do programmers hate nature? Too many bugs, not enough documentation.",
    "What's a programmer's favorite place? The foo bar.",
    # --- dev-level dark jokes ---
    "The code works. Nobody, including you, knows why. Don't touch it.",
    "Documentation is a love letter you write to someone who will never read it: future you.",
    "Your code doesn't have technical debt, it has technical trauma.",
    "Every senior dev was once a junior who deleted the wrong branch and survived.",
    "Legacy code is just a crime scene with really good test coverage missing.",
    "On-call is just insomnia with a corporate sponsor.",
    "'It's just a quick fix' — the last words of every production incident.",
    "The bus factor on this project is one, and he's on vacation.",
    "Your git blame is basically a confession wall.",
    "We don't have bugs, we have undocumented features with trust issues.",
    "The real 404 is the work-life balance you never found.",
    "Impostor syndrome never leaves, it just gets a senior title.",
    "Nothing bonds a team like a 3am incident channel and shared regret.",
    "Your code review comments age like milk, not wine.",
    "Clean code is a myth we tell junior devs to keep them hopeful.",
    "The only thing worse than no comments is a comment that's been lying since 2019.",
    "Burnout doesn't knock, it just quietly rm -rf's your motivation.",
    "Every 'temporary' hack becomes permanent the moment it ships.",
    "Debugging is just arguing with a machine that's technically always right.",
    "CI is green. Nobody trusts it. Everyone deploys anyway.",
    "The postmortem says 'human error.' The human was exhausted and alone at 2am.",
    "Your code is a time capsule of every deadline that crushed you.",
    "We called it a sprint. It was a crawl with extra anxiety.",
    "Someone's going to inherit this codebase and they will not forgive you.",
    "The real monster under the bed is a silent merge conflict.",
]

def _expand_pool(base, extra=None, templates=None, subjects=None, target=50):
    """Build a de-duplicated pool of `target` lines: hand-written base lines
    first (best quality, always kept), then hand-written extras, then —
    only if still short — template x subject combinations as filler so
    every app reliably has a big, non-repetitive pool instead of cycling
    through the same handful of lines every few minutes."""
    pool = list(dict.fromkeys(base + (extra or [])))
    if templates and subjects:
        combos = [t.format(s=s) for t in templates for s in subjects]
        random.shuffle(combos)
        for line in combos:
            if len(pool) >= target:
                break
            if line not in pool:
                pool.append(line)
    return pool[:target]

_DISCORD_BASE = [
    "Is this actually a work server or are we just chatting?",
    "Who's typing, and should I be worried?",
    "Is this voice call productive or is it just vibes?",
    "Another ping? Are you ever going to mute this server?",
    "Screen-sharing code or screen-sharing memes right now?",
    "How many unread messages are we ignoring today?",
    "Is this the coding server or the 'definitely not coding' server?",
    "Quick poll: productive Discord or procrastination Discord?",
    "You opened Discord mid-build. Bold move.",
    "Is someone @ing you, or did you open this out of habit?",
    "Be honest, how long has this call been running in the background?",
    "New emoji reaction just dropped. Worth the context switch?",
    "Is this a quick check or a 45-minute rabbit hole?",
    "Did you mute notifications or are we living on the edge?",
    "Server's popping off. Coding can wait 5 more minutes, right?",
]
_DISCORD_EXTRA = [
    "That red badge count is a cry for help at this point.",
    "Is the bot in this server more useful than the humans?",
    "Someone sent a 2am 'u up' and you actually answered. Bold.",
    "Voice chat background noise says keyboard, foreground says denial.",
    "Which server is this — the real one or the one you forgot to leave?",
    "A wall of text just dropped. Are you reading it or skimming for your name?",
    "This emoji reaction war has been going for how long now?",
    "Is this DM about the project or about the drama?",
    "You joined a call with no mic and no camera. Ghost mode activated.",
    "That pinned message has been ignored since March.",
    "Is this server muted everywhere except the one channel that matters?",
    "Who's status says 'do not disturb' and is doing the opposite right now?",
    "Thread got long enough to need its own thread.",
    "This voice channel has three people and absolute silence. Awkward.",
    "Nitro boost or not, this server still lags the same.",
    "Is that a genuine question in chat or bait for an argument?",
    "You left this server on read for how many hours exactly?",
    "Someone's sharing their screen and it's just their desktop wallpaper.",
    "Is this the group project chat where nobody's agreed on anything yet?",
    "That bot command just spammed 40 messages. Worth it?",
]

_CHROME_BASE = [
    "Tab count check — how many is too many?",
    "Is this research or are we doom-scrolling again?",
    "Found the answer yet or still 6 tabs deep?",
    "Be honest, how many of these tabs are Stack Overflow?",
    "Incognito mode? Suspicious.",
    "Is this the 15th tutorial for the same bug?",
    "Did you forget what you opened this tab for already?",
    "YouTube 'for research' again?",
    "How deep into this rabbit hole are we?",
    "Your RAM is crying with this many tabs open.",
    "Reading docs or reading memes? No judgment.",
    "Is this ChatGPT tab doing my job again?",
    "Another GitHub issue thread? Classic.",
    "Are we shopping or debugging right now?",
    "Is this tab from 3 days ago still relevant?",
]
_CHROME_EXTRA = [
    "That tab's been loading for ten minutes. Pretty sure it's dead.",
    "Fifty tabs and you still can't find the one with the answer.",
    "Is this the official docs or the third-party blog guessing at the docs?",
    "You searched the exact error message and found your own old forum post.",
    "Dark mode on every site except the one that matters, obviously.",
    "That extension you installed is now running half your CPU. Worth it?",
    "Is this a changelog you're reading or a eulogy for your free time?",
    "Bookmark bar says 'to read later.' It has been later for months.",
    "Ctrl+T out of pure habit again, no actual destination in mind?",
    "This is the fourth AI chat tab open. Are they even agreeing with each other?",
    "You've got the same site open in three tabs. Trust issues with your own scrolling?",
    "Is that a pricing page you're closing out of guilt?",
    "Reverse image search on a meme — peak productivity.",
    "That autoplay video snuck up on you again, didn't it?",
    "Thirty seconds on this page and you've already opened two more from it.",
    "Password manager popup again — are you ever going to update that one?",
    "This tab's title still says 'Untitled' and so does your code.",
    "Did the search results actually help or just open five more questions?",
    "You've refreshed this page four times hoping it'll load faster somehow.",
    "That cookie banner's been sitting unclosed for the whole session.",
]

_CODE_BASE = [
    "Is this spaghetti code or are we doing fusion cuisine today?",
    "Are you Googling the error or staring at it hoping it fixes itself?",
    "Did you write a test for that, or are we vibing on faith?",
    "Is this a bug or a feature you forgot you shipped?",
    "How many TODO comments are haunting this file?",
    "Is that indentation consistent, or are we feeling adventurous?",
    "Did you actually read the error message or just hit run again?",
    "console.log debugging again? Respect.",
    "Is this refactor going to take 10 minutes or 3 hours?",
    "That variable name... 'data2'? Really?",
    "How many unsaved files are open right now?",
    "Is this a side project or are we actually finishing something?",
    "Did you just copy-paste from Stack Overflow without reading it?",
    "One more feature before you test it, right?",
    "Is this function doing one thing or seventeen things?",
    "Quick question: why is this file 2000 lines long?",
    "Are those print statements going to make it to production?",
    "Dark theme looking clean today. Productive vibes?",
]
_CODE_EXTRA = [
    "That red squiggle's been ignored for six commits now.",
    "Is this a merge conflict or a philosophical disagreement with your past self?",
    "You renamed the variable three times and it's still not right.",
    "That stack trace is longer than the function that caused it.",
    "Is 'final_v2_ACTUALLY_final' the real file or is there a third one?",
    "Did you just comment out the failing test instead of fixing it?",
    "This file has more imports than actual logic at this point.",
    "Is the linter mad at you or are you mad at the linter?",
    "You wrote a one-liner that took forty minutes. Efficiency, sort of.",
    "That exception is being swallowed silently. Hope that's intentional.",
    "Is this the fifth time rewriting the same function differently?",
    "Breakpoint's been sitting there since yesterday's bug, hasn't it?",
    "That magic number has no comment and no mercy for future-you.",
    "Is this recursive function going to terminate or haunt your terminal?",
    "You just typed 'git push --force' with your eyes closed, admit it.",
    "This branch name is just today's date and a swear word.",
    "Did that unit test pass because it's correct or because it's empty?",
    "Is this tab width argument about to end a friendship?",
    "That function has four nested try/excepts. Confidence or despair?",
    "You're about to ship on a Friday afternoon. Living dangerously.",
]

_CLAUDE_BASE = [
    "Are you asking me to write code or asking me to think for you?",
    "Is this prompt going to actually work, or are we iterating 5 more times?",
    "Did you read what I wrote or just copy-pasted it in?",
    "Another 'fix this error' message? Classic duo.",
    "Are we vibe-coding or actually architecting this?",
    "Is this the real task or are we exploring a tangent again?",
    "How many times have you rephrased this prompt now?",
    "We're basically pair programming right now. I see you.",
    "Did that code even run before you asked for the next thing?",
    "Big feature or tiny tweak this time?",
    "Are you going to actually test what I just gave you?",
    "Is this a real bug or did you just not read the stack trace?",
]
_CLAUDE_EXTRA = [
    "Is this chat still about the original bug or did scope creep win again?",
    "You pasted the whole file instead of the one function. Bold strategy.",
    "That's the third 'one more thing' in this conversation. Respect the hustle.",
    "Did you actually run that before asking why it's still broken?",
    "Is this a real architecture decision or just typing until it feels right?",
    "This context window's seen some things today.",
    "You asked for a quick fix and now we're redesigning the whole module.",
    "Is this the main project or the side quest you swore you wouldn't start?",
    "That error message got pasted without the actual question. Classic.",
    "Are we debugging your code or debugging the prompt now?",
    "Six messages in and we're still arguing about naming. Iconic.",
    "Is this going in the real codebase or staying a scratch file forever?",
    "You said 'just a small change' and that was forty minutes ago.",
    "Did you skim the explanation or go straight for the code block?",
]

_STEAM_BASE = [
    "Hey... Weren't you supposed to be coding right now?",
    "One more round, right? Riiight?",
    "Is this a break or are we calling it quits for the day?",
    "That backlog of unplayed games says otherwise.",
    "Sale's tempting, but do you need another game you won't finish?",
    "Just 'checking the store' at this hour?",
    "Is this stress relief or straight-up procrastination?",
    "Your project missed you while you were here.",
    "One match and back to coding, promise?",
    "Achievements can wait, can't they?",
]
_STEAM_TEMPLATES = [
    "Is {s} really worth the distraction right now?",
    "{s} again? Focus, come on.",
    "Be honest, {s} is procrastination wearing a disguise.",
    "Your code's still open behind {s}, you know.",
    "One more look at {s} and then straight back to work, deal?",
    "{s} isn't going anywhere — your deadline is.",
    "Didn't we agree to ignore {s} today?",
    "{s} just winked at you. Resist.",
    "That build error is still waiting while you check {s}.",
    "{s} at this hour is a choice.",
]
_STEAM_SUBJECTS = [
    "that sale", "your wishlist", "this DLC", "the achievement list",
    "your friends list", "that early access title", "the workshop mods",
    "this beta build", "your playtime stats", "that review-bombed thread",
    "the trading cards", "this co-op lobby",
]

_UNITY_BASE = [
    "Did that scene actually build or is the console red again?",
    "Is this a quick playtest or are we redesigning the whole level?",
    "How many empty GameObjects are floating in this hierarchy?",
    "Null reference exception again? Classic Unity moment.",
    "Did you forget to save the scene before hitting play?",
    "Is this prefab doing what you think it's doing?",
    "Frame rate looking good or are we debugging performance again?",
    "Another script attached to the same GameObject? Bold.",
    "Is this a game jam deadline or a passion project today?",
    "Physics acting weird again? Rigidbody says hi.",
]
_UNITY_TEMPLATES = [
    "Is {s} finally fixed or are we pretending it is?",
    "{s} strikes again — classic Unity.",
    "Did you Google {s} or just restart the editor and hope?",
    "{s} — new bug or an old friend?",
    "One more coffee before tackling {s}?",
    "{s} says it's not a bug, it's a feature.",
    "Console's red because of {s}, isn't it?",
    "{s} at 2am hits different.",
    "Did {s} survive the last Unity update, or barely?",
    "Is {s} why the build's been running for twenty minutes?",
]
_UNITY_SUBJECTS = [
    "that null ref", "the broken prefab", "this lighting bake",
    "the physics glitch", "that missing script warning", "the editor freeze",
    "this shader error", "the animation rig", "that memory leak",
    "the build pipeline", "this camera clipping bug", "the input system",
]

_UNITYHUB_BASE = [
    "Which project are we opening today?",
    "Is this Unity version actually compatible or are we gambling?",
    "New project or back into the chaos of an old one?",
]
_UNITYHUB_TEMPLATES = [
    "Opening {s} again? Bold.",
    "{s}, or are we finally starting fresh?",
    "Is {s} even compatible with this Unity version?",
    "{s} — nostalgia or necessity?",
    "Hub says update, you say later. {s} agrees, probably.",
    "Is {s} getting finished this time or just reopened for old time's sake?",
]
_UNITYHUB_SUBJECTS = [
    "this old project", "the version mismatch", "that abandoned prototype",
    "the asset store cart", "this new template", "the package manager",
    "that broken import", "the license popup",
]

# shared filler templates used to top up the four main pools (Discord,
# Chrome, VS Code, Claude) past their hand-written lines up to 50 — the
# hand-written ones always come first and are never pushed out
_GENERIC_TEMPLATES = [
    "Is {s} actually worth the detour right now?",
    "{s} again? Focus, come on.",
    "Be honest, {s} is a distraction wearing a disguise.",
    "Everything else is still waiting behind {s}.",
    "One quick look at {s} and then straight back to it, deal?",
    "{s} isn't going anywhere, you know.",
    "Didn't we agree to leave {s} alone for a bit?",
    "{s} says hi. Your deadline says otherwise.",
]
_DISCORD_SUBJECTS = [
    "that unread badge", "this voice call", "the pinned message", "that reaction",
    "the mute button", "this thread", "that DM", "the announcement channel",
    "this bot", "that server emoji",
]
_CHROME_SUBJECTS = [
    "that search tab", "the extension store", "this changelog", "that forum thread",
    "the dev console", "this cached page", "that pinned tab", "the bookmarks bar",
    "this incognito window", "that download",
]
_CODE_SUBJECTS = [
    "that TODO", "this stack trace", "the failing test", "that commit message",
    "this deprecated function", "the config file", "that env variable",
    "this regex", "the build script", "that dependency",
]
_CLAUDE_SUBJECTS = [
    "this prompt", "that context window", "the last response", "this edge case",
    "that refactor", "the test plan", "this edit", "that design decision",
    "the next step", "this conversation",
]

# process-name -> list of app-specific question strings (random pick each time)
APP_QUESTIONS = {
    "discord.exe": _expand_pool(
        _DISCORD_BASE, _DISCORD_EXTRA, templates=_GENERIC_TEMPLATES,
        subjects=_DISCORD_SUBJECTS, target=50,
    ),
    "chrome.exe": _expand_pool(
        _CHROME_BASE, _CHROME_EXTRA, templates=_GENERIC_TEMPLATES,
        subjects=_CHROME_SUBJECTS, target=50,
    ),
    "code.exe": _expand_pool(
        _CODE_BASE, _CODE_EXTRA, templates=_GENERIC_TEMPLATES,
        subjects=_CODE_SUBJECTS, target=50,
    ),
    "claude.exe": _expand_pool(
        _CLAUDE_BASE, _CLAUDE_EXTRA, templates=_GENERIC_TEMPLATES,
        subjects=_CLAUDE_SUBJECTS, target=50,
    ),
    "steam.exe": _expand_pool(
        _STEAM_BASE, templates=_STEAM_TEMPLATES, subjects=_STEAM_SUBJECTS, target=50
    ),
    "unity.exe": _expand_pool(
        _UNITY_BASE, templates=_UNITY_TEMPLATES, subjects=_UNITY_SUBJECTS, target=50
    ),
    "unityhub.exe": _expand_pool(
        _UNITYHUB_BASE, templates=_UNITYHUB_TEMPLATES, subjects=_UNITYHUB_SUBJECTS, target=50
    ),
}

UNKNOWN_LINES = [
    "What is this place?",
    "Umm... Never seen this one before?",
    "Ok new app unlocked, what does this do?",
]

DRAG_LINES = [
    "wowww!!!!",
    "wheee, where to?",
    "okay okay I'm coming!",
    "yoinked successfully.",
    "mid-air crisis incoming.",
    "this is my Superman pose.",
    "flying claude, no cape needed.",
    "don't drop me on a tab with 47 errors.",
    "redecorating my own life rn.",
    "turbulence detected, hold on.",
    "is this a promotion or a kidnapping?",
    "new desktop real estate, scouting now.",
    "catch me if you — oh wait, you already did.",
    "pixel physics said sure, why not.",
    "didn't consent to this trajectory but okay.",
]

DROP_LINES = [
    "new place!! same craze!!!",
    "landed it, 10/10 dismount.",
    "home sweet pixel.",
    "and we're parked.",
    "this spot's got good vibes.",
    "relocation complete, boss.",
    "okay this corner slaps.",
    "settling in like it's rent-controlled.",
    "new coordinates, same chaos.",
    "touchdown. no notes.",
    "could get used to this view.",
    "moved in, not paying rent though.",
    "found my spawn point.",
    "this'll do until the next kidnapping.",
    "anchored. for now.",
]

# known apps that get a dedicated question pool (process name -> pool key above)
KNOWN_APPS = set(APP_QUESTIONS.keys())

MUSIC_PROCS = {"spotify.exe", "music.exe", "wmplayer.exe", "groove.exe"}

# Idle fidgets — after 30 min with zero interaction the pet starts doing
# its own little things, pulled from the static mascot-pack art dropped
# into assets/idle_extras/. Hand-written captions for the ones worth a
# proper line; anything else just gets its filename humanized so dropping
# new art in there works out of the box with no code changes.

FIDGET_CAPTIONS = {
    "debugging-system-bugs": "found a bug. several bugs. it's bugs all the way down.",
    "angry-at-laptop": "the laptop did nothing wrong and yet.",
    "sleeping-soundly": "five more minutes... or five hundred.",
    "thinking-in-code": "brain.exe is compiling.",
    "malware-detection-window": "scanning... scanning... probably fine.",
    "stealth-ninja-security": "moving in complete silence. mostly.",
    "it-depends-sign": "the only honest answer in tech.",
    "broken-heart-sad": "my last deploy didn't survive.",
    "happy-pixel-celebrating": "tests passed first try, miracles exist.",
    "crying-sad-reaction": "merge conflicts. so many merge conflicts.",
    "rocket-launch-success": "shipped it. no turning back now.",
    "dizzy-failed-state": "stack traces do this to me.",
    "holding-ancient-scroll": "reading docs from 2014. bold choice.",
    "lifting-heavy-barbell": "optimizing this loop, one rep at a time.",
    "secure-access-padlock": "yes I changed the password. no I don't remember it.",
    "repairing-with-tools": "duct tape and hope, the full stack.",
    "system-error-alert": "something broke. probably me.",
    "processing-logic-symbols": "if true then true else also true.",
    "examining-green-globe": "scanning the whole internet for one answer.",
    "confusion-spiral-pixel": "re-reading my own code from last week like a stranger.",
    "angry-pixel-coffee": "coffee's cold. so is my motivation.",
    "angry-powerful-lightning": "rage-quitting the bug, not the job. probably.",
    "api-success-pixel": "200 OK. a rare and beautiful sight.",
    "baking-steaming-pie": "letting something bake while the build runs.",
    "building-colorful-blocks": "stacking abstractions on top of abstractions.",
    "data-blocks-pixel": "organizing data that will be messy again by Tuesday.",
    "developer-pair-programming-scene": "pairing with myself, technically.",
    "disconnected-plug-pixel": "connection lost. story of my life.",
    "failed-process-error": "process exited with code 1. mood.",
    "fast-performance-trail": "finally fast. savor this moment.",
    "fine-under-pressure": "everything's fine. this is fine.",
    "growing-pixel-nature": "letting the codebase grow organically. for better or worse.",
    "idea-lightbulb-pixel": "idea acquired. will forget it in nine minutes.",
    "in-constant-loop": "stuck in a loop and the exit condition is a lie.",
    "in-glowing-aura": "radiating main-character energy today.",
    "infrastructure-server-stacks": "counting servers. losing count.",
    "lab-science-testing": "running an experiment nobody approved.",
    "love-cloud-pixel": "sending love to whoever writes good commit messages.",
    "managing-server-rack": "keeping the lights on, barely.",
    "marking-critical-error": "flagging this as critical and ignoring it anyway.",
    "multi-window-workflow": "fourteen windows open, focused on none of them.",
    "nature-growth-mushrooms": "something's growing in this codebase and it's not features.",
    "planting-small-trees": "planting seeds for future-me's problems.",
    "professional-documentation-audit": "auditing docs that don't exist.",
    "reading-data-document": "reading the changelog nobody else reads.",
    "refresh-sync-pixel": "syncing. still syncing. always syncing.",
    "reviewing-long-data-log": "scrolling logs looking for the one line that matters.",
    "server-stack-pixel": "the servers are fine. probably.",
    "success-achievement-milestone": "small win. taking it anyway.",
    "system-monitoring-dashboard": "watching the graphs do nothing interesting.",
    "thinking-pixel-bubble": "thoughts loading, please wait.",
    "tracking-multiple-locations": "tracking everything, understanding nothing.",
    "trending-up-pixel": "line go up. nobody knows why.",
    "user-profile-settings": "poking around settings I shouldn't touch.",
    "visualizing-tree-data": "staring at a tree structure, feeling rooted.",
    "welcome-pixel-banner": "still here. still vibing.",
    "with-success-checkmark": "checkbox checked. dopamine acquired.",
    "writing-software-code": "writing code nobody asked for, out of habit.",
    "holding-green-leaf": "taking a small, quiet win.",
    "error-state-pixel": "error state achieved. working as intended, unfortunately.",
}

def _humanize_fidget_name(stem):
    return stem.replace("-", " ").replace("_", " ").strip()

def _load_fidget_files():
    if not os.path.isdir(IDLE_EXTRAS_DIR):
        return []
    return sorted(f for f in os.listdir(IDLE_EXTRAS_DIR) if f.lower().endswith(".png"))

FIDGET_FILES = _load_fidget_files()

# Foreground app watcher

def get_foreground_process_name():
    if not IS_WINDOWS or win32gui is None or psutil is None:
        return None
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        return proc.name().lower()
    except Exception:
        return None

def set_process_priority_extreme():
    """Push this process to the top of Windows' scheduler so the pet isn't
    starved for CPU by everything else competing for it at login. Tries
    REALTIME first (needs admin, usually silently refused without it),
    falls back to HIGH, then ABOVE_NORMAL — whichever the OS actually grants."""
    if not IS_WINDOWS or win32process is None:
        return
    try:
        handle = win32api.GetCurrentProcess()
    except Exception:
        return
    candidates = [
        getattr(win32process, "REALTIME_PRIORITY_CLASS", 0x00000100),
        getattr(win32process, "HIGH_PRIORITY_CLASS", 0x00000080),
        getattr(win32process, "ABOVE_NORMAL_PRIORITY_CLASS", 0x00008000),
    ]
    for priority_class in candidates:
        try:
            win32process.SetPriorityClass(handle, priority_class)
            return
        except Exception:
            continue

def find_claude_desktop_shortcut():
    """Locate the Claude desktop app's Start Menu shortcut instead of
    guessing an install path. Electron-style apps like Claude Desktop live
    under a version-numbered folder that changes on every auto-update
    (there's no stable claude.exe to hardcode), but the Start Menu/Desktop
    shortcut Windows creates on install always points at whatever the
    current one is — so resolving that shortcut is the only path that
    survives updates."""
    if not IS_WINDOWS:
        return None

    search_roots = []
    appdata = os.environ.get("APPDATA")
    programdata = os.environ.get("PROGRAMDATA")
    userprofile = os.environ.get("USERPROFILE")
    if appdata:
        search_roots.append(os.path.join(appdata, "Microsoft", "Windows", "Start Menu", "Programs"))
    if programdata:
        search_roots.append(os.path.join(programdata, "Microsoft", "Windows", "Start Menu", "Programs"))
    if userprofile:
        search_roots.append(os.path.join(userprofile, "Desktop"))

    best = None
    for root in search_roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            for fname in filenames:
                if not fname.lower().endswith(".lnk"):
                    continue
                stem = fname[:-4].lower()
                if "claude" not in stem or "code" in stem:
                    continue
                full = os.path.join(dirpath, fname)
                if stem == "claude":
                    return full  # exact match, stop looking
                if best is None:
                    best = full
    return best

# Speech bubble

class SpeechBubble(QWidget):
    def __init__(self):
        super().__init__(
            None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.label = QLabel(self)
        self.label.setWordWrap(True)
        self.label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        self.label.setStyleSheet("color: #2b2b2b; background: transparent; padding: 10px;")
        self.label.setAlignment(Qt.AlignCenter)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        self.hide()
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor(255, 255, 255, 235))
        painter.setPen(QColor(224, 108, 74, 255))
        rect = self.rect().adjusted(1, 1, -1, -8)
        painter.drawRoundedRect(rect, 14, 14)
        # little tail pointing down
        w = self.width()
        h = self.height()
        points = [QPoint(w // 2 - 8, h - 8), QPoint(w // 2 + 8, h - 8), QPoint(w // 2, h)]
        painter.setBrush(QColor(255, 255, 255, 235))
        painter.drawPolygon(*points)

    def show_text(self, text, anchor_global_pos, duration_ms=4500):
        fm = QFontMetrics(self.label.font())
        max_width = 230
        text_rect = fm.boundingRect(0, 0, max_width - 20, 1000, Qt.TextWordWrap, text)
        w = min(max_width, text_rect.width() + 30)
        h = text_rect.height() + 30
        self.label.setText(text)
        self.resize(w, h)
        x = anchor_global_pos.x() - w // 2
        y = anchor_global_pos.y() - h - 10
        self.move(x, y)
        self.show()
        self.raise_()
        self._timer.stop()
        self._timer.start(duration_ms)

# Sprite loader / animator

class SpriteBank:
    def __init__(self):
        self.cache = {}

    def frames(self, state):
        if state in self.cache:
            return self.cache[state]
        folder = os.path.join(FRAMES_DIR, state)
        files = sorted(f for f in os.listdir(folder) if f.endswith(".png"))
        pixmaps = [
            QPixmap(os.path.join(folder, f)).scaled(
                SPRITE_SIZE, SPRITE_SIZE, Qt.KeepAspectRatio, Qt.FastTransformation
            )
            for f in files
        ]
        self.cache[state] = pixmaps
        return pixmaps

# Main pet widget

class PetWidget(QWidget):
    def __init__(self):
        super().__init__(
            None,
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(SPRITE_SIZE, SPRITE_SIZE)

        self.sprites = SpriteBank()
        self.state = "idle"
        self.frame_idx = 0
        self._anim_dir = 1  # ping-pong direction for smoother looping
        self._bob_phase = 0.0
        self.label = QLabel(self)
        self.label.setGeometry(0, 0, SPRITE_SIZE, SPRITE_SIZE)
        self.label.setAlignment(Qt.AlignCenter)

        self.bubble = SpeechBubble()

        self._drag_pos = None
        self._dragging = False
        self._launch_stage = None  # None, 'launching', 'waiting_claude'

        # idle-fidget bookkeeping
        self._last_interaction = time.time()
        self._fidgeting = False
        self._last_fidget_time = 0.0
        self._fidget_due_gap = random.randint(*IDLE_FIDGET_INTERVAL_RANGE)

        self._load_position()
        self._apply_frame()
        self.show()

        # animation timer (90ms + ping-pong + a little sine bob = noticeably
        # smoother motion than a flat frame-cycle without touching the art)
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._tick_animation)
        self.anim_timer.start(90)

        # joke/question timer (every 30s)
        self.joke_timer = QTimer(self)
        self.joke_timer.timeout.connect(self._random_joke_or_question)
        self.joke_timer.start(30_000)

        # app watcher
        self.app_timer = QTimer(self)
        self.app_timer.timeout.connect(self._check_foreground_app)
        self.app_timer.start(4_000)
        self._last_category = None
        self._last_proc = None

        # idle-fidget watcher — checked every 30s, only actually fires once
        # IDLE_FIDGET_AFTER_MS of zero interaction has passed
        self.fidget_timer = QTimer(self)
        self.fidget_timer.timeout.connect(self._maybe_fidget)
        self.fidget_timer.start(30_000)

        # welcome
        QTimer.singleShot(600, self._welcome)

    # ---- persistence ----
    def _load_position(self):
        try:
            with open(CONFIG_PATH, "r") as f:
                cfg = json.load(f)
            x, y = cfg.get("x"), cfg.get("y")
            if x is not None and y is not None:
                self.move(x, y)
                return
        except Exception:
            pass
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.width() - SPRITE_SIZE - 60, screen.height() - SPRITE_SIZE - 60)

    def _save_position(self):
        try:
            with open(CONFIG_PATH, "w") as f:
                json.dump({"x": self.x(), "y": self.y()}, f)
        except Exception:
            pass

    # ---- animation ----
    def set_state(self, state):
        if state != self.state:
            self.state = state
            self.frame_idx = 0
            self._anim_dir = 1

    def _apply_frame(self):
        frames = self.sprites.frames(self.state)
        if not frames:
            return
        self.frame_idx = max(0, min(self.frame_idx, len(frames) - 1))
        self.label.setPixmap(frames[self.frame_idx])

    def _apply_bob(self):
        # subtle sine-wave bob on resting/talking states only — a cheap way
        # to make the loop feel alive between frame changes instead of a
        # flat frame-swap, without needing any new art
        if self.state in ("idle", "vibe", "welcome", "talk") and not self._fidgeting:
            self._bob_phase += 0.35
            offset = int(round(math.sin(self._bob_phase) * 3))
        else:
            offset = 0
        self.label.setGeometry(0, offset, SPRITE_SIZE, SPRITE_SIZE)

    def _tick_animation(self):
        if self._fidgeting:
            self._apply_bob()
            return
        frames = self.sprites.frames(self.state)
        n = len(frames)
        if n <= 1:
            self._apply_bob()
            return
        self.frame_idx += self._anim_dir
        if self.frame_idx >= n - 1:
            self.frame_idx = n - 1
            self._anim_dir = -1
        elif self.frame_idx <= 0:
            self.frame_idx = 0
            self._anim_dir = 1
        self._apply_bob()
        self._apply_frame()

    def _anchor_point(self):
        return self.mapToGlobal(QPoint(SPRITE_SIZE // 2, 10))

    def say(self, text, duration_ms=4500):
        self.bubble.show_text(text, self._anchor_point(), duration_ms)

    # ---- welcome / bye ----
    def _welcome(self):
        self.set_state("welcome")
        self.say("welcome back! let's build something today ✨")
        QTimer.singleShot(4000, lambda: self.set_state("idle"))

    def say_bye_and_allow_close(self):
        self.set_state("talk")
        self.say("bye, see you later \U0001F44B", duration_ms=2500)

    # ---- foreground app watch ----
    def _check_foreground_app(self):
        if self._dragging or self._launch_stage is not None:
            return
        proc = get_foreground_process_name()
        if proc is None:
            return
        if proc == self._last_proc:
            return
        self._last_proc = proc

        if proc in MUSIC_PROCS:
            self.set_state("vibe")
            self.say("nice track, vibing with you \U0001F3B6")
            return

        if proc in KNOWN_APPS:
            self.set_state("talk")
            self.say(random.choice(APP_QUESTIONS[proc]))
            return

        # unknown app -> confused line, but not spammy for Explorer/system procs
        if proc in ("explorer.exe", "dwm.exe", "searchhost.exe", "shellexperiencehost.exe",
                    "claudeanimatedpet.exe", "python.exe", "pythonw.exe"):
            return
        self.set_state("confused")
        self.say(random.choice(UNKNOWN_LINES))

    def _random_joke_or_question(self):
        if self._dragging or self._launch_stage is not None:
            return
        proc = self._last_proc
        if proc in MUSIC_PROCS:
            self.set_state("vibe")
        pool = CODING_JOKES[:]
        if proc in KNOWN_APPS:
            pool += APP_QUESTIONS[proc]
        self.say(random.choice(pool), duration_ms=5000)

    # ---- idle fidgets (no touch for 30+ minutes) ----
    def _mark_interaction(self):
        self._last_interaction = time.time()

    def _maybe_fidget(self):
        if self._dragging or self._launch_stage is not None or self._fidgeting:
            return
        if not FIDGET_FILES:
            return
        idle_for = time.time() - self._last_interaction
        if idle_for < IDLE_FIDGET_AFTER_MS / 1000:
            return
        since_last_fidget = time.time() - self._last_fidget_time
        if since_last_fidget < self._fidget_due_gap:
            return
        self._do_fidget()

    def _do_fidget(self):
        fname = random.choice(FIDGET_FILES)
        stem = fname[:-4].lower()
        caption = FIDGET_CAPTIONS.get(stem) or _humanize_fidget_name(stem)
        path = os.path.join(IDLE_EXTRAS_DIR, fname)
        pix = QPixmap(path)
        if pix.isNull():
            return
        pix = pix.scaled(SPRITE_SIZE, SPRITE_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._fidgeting = True
        self.label.setPixmap(pix)
        self.say(caption, duration_ms=3500)
        self._last_fidget_time = time.time()
        self._fidget_due_gap = random.randint(*IDLE_FIDGET_INTERVAL_RANGE)
        QTimer.singleShot(3500, self._end_fidget)

    def _end_fidget(self):
        self._fidgeting = False
        self._apply_frame()

    # ---- click-to-launch-claude ----
    def _start_claude_launch(self):
        if self._launch_stage is not None:
            return
        self._launch_stage = "launching"
        self.set_state("click")
        self.say("opening claude desktop...", duration_ms=2500)

        launched = False
        if IS_WINDOWS:
            shortcut = find_claude_desktop_shortcut()
            if shortcut:
                try:
                    os.startfile(shortcut)
                    launched = True
                except Exception:
                    launched = False
        else:
            try:
                subprocess.Popen(["claude"])
                launched = True
            except Exception:
                launched = False

        if not launched:
            self.say(
                "couldn't find Claude Desktop on the Start Menu — pin it there "
                "and I'll find it next time \U0001F614",
                duration_ms=4000,
            )
            self._launch_stage = None
            return

        self._launch_stage = "waiting_claude"
        self._claude_wait_elapsed = 0
        self._claude_wait_timer = QTimer(self)
        self._claude_wait_timer.timeout.connect(self._poll_for_claude_desktop)
        self._claude_wait_timer.start(1500)

    def _poll_for_claude_desktop(self):
        self._claude_wait_elapsed += 1500
        found = False
        if psutil is not None:
            for p in psutil.process_iter(["name"]):
                try:
                    name = (p.info["name"] or "").lower()
                except Exception:
                    continue
                if "claude" in name and "pet" not in name:
                    found = True
                    break
        timed_out = self._claude_wait_elapsed > 25_000
        if found or timed_out:
            self._claude_wait_timer.stop()
            self.set_state("click")
            self.say("LETS CODE \U0001F4BB\U0001F525", duration_ms=3500)
            QTimer.singleShot(3500, lambda: self.set_state("idle"))
            self._launch_stage = None

    # ---- mouse / drag ----
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._mark_interaction()
            if self._fidgeting:
                self._end_fidget()
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self._dragging = False
            self._press_time = time.time()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self._mark_interaction()
            if not self._dragging:
                self._dragging = True
                self.set_state("drag")
                self.say(random.choice(DRAG_LINES), duration_ms=1500)
            self.move(event.globalPos() - self._drag_pos)
            self.bubble.move(
                self.x() + SPRITE_SIZE // 2 - self.bubble.width() // 2,
                self.y() - self.bubble.height() - 10,
            )
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._mark_interaction()
            was_dragging = self._dragging
            self._dragging = False
            self._drag_pos = None
            self._save_position()
            if was_dragging:
                self.set_state("vibe")
                self.say(random.choice(DROP_LINES), duration_ms=2000)
                QTimer.singleShot(2000, lambda: self.set_state("idle"))
            else:
                # it was a click, not a drag
                self._start_claude_launch()
            event.accept()

    def closeEvent(self, event):
        self._save_position()
        event.accept()

# Windows shutdown/logoff hook

def install_shutdown_hook(app, pet):
    """Intercept WM_QUERYENDSESSION so we can show the bye bubble before
    the OS actually shuts the process down. Falls back to atexit elsewhere."""
    if not IS_WINDOWS or win32gui is None:
        import atexit
        atexit.register(lambda: None)
        return

    import ctypes
    from ctypes import wintypes

    WM_QUERYENDSESSION = 0x0011
    WM_ENDSESSION = 0x0016

    hwnd = int(pet.winId())

    user32 = ctypes.windll.user32
    try:
        user32.ShutdownBlockReasonCreate(
            hwnd, ctypes.c_wchar_p("claude-animated-pet is saying bye...")
        )
    except Exception:
        pass

    old_wndproc = None

    WNDPROCTYPE = ctypes.WINFUNCTYPE(
        ctypes.c_long, ctypes.c_int, ctypes.c_uint, ctypes.c_int, ctypes.c_int
    )

    def wnd_proc(hWnd, msg, wParam, lParam):
        if msg == WM_QUERYENDSESSION:
            if not getattr(pet, "_bye_shown", False):
                pet._bye_shown = True
                pet.say_bye_and_allow_close()
                QTimer.singleShot(1800, lambda: _release_block(hwnd))
            return 0  # block briefly so the bubble is visible
        return ctypes.windll.user32.CallWindowProcW(old_wndproc, hWnd, msg, wParam, lParam)

    def _release_block(hwnd_):
        try:
            user32.ShutdownBlockReasonDestroy(hwnd_)
        except Exception:
            pass

    GWL_WNDPROC = -4
    new_proc = WNDPROCTYPE(wnd_proc)
    try:
        old_wndproc = ctypes.windll.user32.SetWindowLongW(hwnd, GWL_WNDPROC, new_proc)
        pet._wndproc_ref = new_proc  # keep alive
    except Exception:
        pass

def main():
    set_process_priority_extreme()
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    pet = PetWidget()
    install_shutdown_hook(app, pet)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
