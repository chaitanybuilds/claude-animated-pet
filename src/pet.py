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
 - watches terminals too: PowerShell, cmd, Git, Node, Python, Windows
   Terminal and WSL each get their own 50-line pool of English, sarcastic,
   dark/funny terminal jokes
 - click => opens a terminal and runs `claude` (the old CLI launch),
   then closes that terminal once Claude is found or after 25s
 - Alt+F4 / window close is ignored on purpose, so the pet stays alive
   until shutdown, when it can show its bye bubble for 1.8s
 - every 30s: random coding joke/question (incl. dev-level dark humor) in
   a speech bubble
 - drag => one of 15 random lines ; drop => another 15
 - system stats (separate timer, other logics keep running): RAM >= 75%,
   CPU >= 80%, or temperature >= 50C => one random joke from that trigger's
   20-line pool, with its own mascot, 5-min cooldown per trigger
 - 10 min with zero interaction => starts doing its own idle fidgets,
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
IDLE_FIDGET_AFTER_MS = 10 * 60 * 1000
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

# Filler templates top up the four main pools to 50; hand-written lines come first.
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



# Terminal pools: 50 hand-written lines each, no template filler.
_POWERSHELL_POOL = [
    'Is this a script or a ransom note written in Verb-Noun?',
    'Be honest, did you Google that cmdlet or just guess Get-Something until it worked?',
    '$Error is not a variable, it is a lifestyle at this point.',
    'ExecutionPolicy says Restricted, you say run anyway. Security team says hi.',
    'Another pipeline with twelve stages? That is not scripting, that is plumbing with extra steps.',
    'Did you just pipe everything to Out-Null and call it error handling?',
    'PowerShell ISE is still open? That is not nostalgia, that is a cry for help.',
    'Your .ps1 is eight hundred lines and the comment at the top says quick script.',
    'Is this admin PowerShell or are we just living dangerously with UAC off?',
    'How many times have you typed Get-Help and still not read it?',
    'That blue background is not productivity, it is a confession.',
    'You renamed a variable $x, $y, $z and now even you do not know what $z holds.',
    'Is this automation or are you just automating your own mistakes faster?',
    'Did the script work, or did it just fail silently and you moved on?',
    'Another one-liner that is four hundred characters long. Sure, one line.',
    'Are we in pwsh 7 or PowerShell 5? The answer determines how much will break.',
    'You used -Force on everything. That is not confidence, that is despair.',
    'Is this a remote session or are you just SSHing into your own problems?',
    'That function returns nothing, throws nothing, and yet somehow broke production.',
    'Be honest, how much of this script is copied from a blog post from 2014?',
    'Your profile.ps1 loads slower than your motivation on a Monday.',
    'Did you just run a script you found in a forum with trust me bro in the comments?',
    'This is not DevOps, this is a guy with a blue window and a deadline.',
    'The pipeline broke at stage nine. Of course it did. Stage nine is where hope goes to die.',
    'You set ExecutionPolicy to Unrestricted and called it fixing the issue.',
    'Is that a real error or just PowerShell being passive-aggressive in red text?',
    'Another day, another object that is not actually an object, it is a string pretending.',
    'Your script has more Write-Host than actual logic. That is not logging, that is diary writing.',
    'Did you test this in prod? No, you tested this on prod.',
    'That cmdlet name is so long you need a second monitor just to read it.',
    'Are you automating this task or just procrastinating with extra steps and a blue theme?',
    'The job ran, the output is empty, and you are calling that success.',
    'You piped Get-Process to Stop-Process. Bold. Reckless, but bold.',
    'Is this a scheduled task or a time bomb with a calendar invite?',
    'Your error handling is try, do stuff, catch, ignore. Classic.',
    'How many modules did you import for a script that prints one line?',
    'That $null comparison just failed because you compared the wrong side. Again.',
    'PowerShell remoting: because breaking one machine was not enough.',
    'You wrote a script to automate a task you do once a year. Efficiency, sort of.',
    'Is this a function or a novel with parameters?',
    'The terminal says completed successfully and you still do not believe it.',
    'You used Invoke-Expression on user input. Security team just felt a disturbance.',
    'Another alias that only you understand. Future you is already angry.',
    'Did you just close the window without saving? The script was never saved, was it?',
    'This is not a blue screen of death, it is a blue screen of I told you so.',
    'Your script works on your machine. It works nowhere else. That is the whole personality now.',
    'Are we scripting or are we just typing commands until the red text stops?',
    'That one-liner just became a two hundred line function. Growth, I guess.',
    'You forgot to dot-source the file and now nothing works. Again.',
    'Is this PowerShell or a therapy session with a dollar prompt?',
]

_CMD_POOL = [
    'Is this cmd or a museum exhibit that still runs?',
    'You typed dir and got two hundred files. The one you needed was not in the list, classic.',
    'Be honest, is this a batch file or a list of regrets with .bat at the end?',
    'Another echo off at the top, as if hiding the output hides the shame.',
    'Did you just cd into the wrong folder for the third time today?',
    'That %PATH% variable has been edited so many times it needs therapy.',
    'Is this a script or are you just typing commands you half-remember from 2009?',
    'You ran del *.* and then froze. We all saw it. We all felt it.',
    'Another pause at the end so you can pretend you meant to read the output.',
    'Is this admin cmd or are we just hoping UAC is asleep?',
    'Your batch file has more goto labels than actual logic. Spaghetti, but make it Windows.',
    'Did that command work or did it just print nothing and you took that as a yes?',
    'You are still using cmd in 2026. That is not loyalty, that is Stockholm syndrome.',
    'Another cls to hide the evidence before anyone looks over your shoulder.',
    'Is this a real task or are you just pinging localhost to feel productive?',
    'That for loop in batch just ate your afternoon. Congratulations.',
    'You typed the command, it failed, you typed it again louder. It still failed.',
    'Be honest, how many of these commands did you copy from a forum post with no explanation?',
    'This window has been open since the last reboot. It has seen things.',
    'Did you just set a variable with set and forget to use setlocal? Future you is crying.',
    'Another ipconfig /flushdns as if that fixes anything except your confidence.',
    'Is this a build script or a prayer written in percent signs?',
    'Your .bat file works, but nobody, including you, knows why. Do not touch it.',
    'You ran a command as admin that you would never run as a normal user. Bold.',
    'That error level is 1. It has always been 1. It will always be 1.',
    'Did you just type exit and then realise you needed that window?',
    'Another taskkill /F because closing things politely was too slow for you.',
    'Is this cmd or a time machine to when computers were simpler and errors were vaguer?',
    'You have three cmd windows open and no idea which one is doing what.',
    'That command prompt title still says Administrator. Power, and also danger.',
    'Be honest, did you just run format on the wrong drive in your head and panic for a second?',
    'Your batch script has a comment that says do not delete this line. Nobody knows why.',
    'Another xcopy with no switches, as if copying files was ever that simple.',
    'Is this a quick fix or are we about to edit the registry because cmd was not enough?',
    'You typed help and got a list longer than your patience. Classic cmd.',
    'That ping just timed out four times and you are still staring at it like it owes you an answer.',
    'Did you just chain commands with && and hope the first one succeeds? Optimism, sort of.',
    'Another system32 folder, another reason to be careful and also not careful at all.',
    'Your script deletes temp files and also, somehow, your will to live.',
    'Is this a terminal or a black box where good intentions go to get error level 9009?',
    'You ran sfc /scannow because someone on the internet said to. It found nothing. It always finds nothing.',
    'That caret ^ in batch just escaped your sanity, not just the character.',
    'Another day, another command that works only if you run it from exactly the right folder.',
    'Did you just open cmd to run one command and end up in a two-hour rabbit hole?',
    'Your prompt is C:\\Users\\you\\Desktop\\project\\final\\final2\\actually_final. We know what that means.',
    'Is this cmd or a confession booth with a blinking cursor?',
    'You closed the window and the process is still running. Of course it is.',
    'That batch file is older than your current job and still runs the whole deployment.',
    'Another echo hello world, as if the world needed another hello from this window.',
    'Did you just type a command, get access denied, and pretend you did not see it?',
]

_GIT_POOL = [
    'Is this a repo or a crime scene with a .git folder?',
    'You just force pushed to main. The team will find out. They always find out.',
    'Another merge conflict? That is not a bug, that is two people refusing to agree.',
    'Did you commit with message fix or are we just documenting our denial?',
    'Your branch name is literally fix-stuff-final-v2. Nobody believes v2 is final.',
    'Be honest, how many stashes do you have that you will never pop again?',
    'You rebased, it went wrong, and now history is a choose-your-own-adventure book.',
    'Another git blame that points straight at you. Awkward.',
    'Is this a pull request or a group therapy session with code review comments?',
    'You committed node_modules once. Once was enough to scar everyone.',
    'That detached HEAD state is not a bug, it is a metaphor for your career right now.',
    'Did you just push to the wrong remote? Production says hi.',
    'Your commit history reads like a diary: wip, wip, wip, actually fix, revert wip.',
    'Another cherry-pick that brought three new bugs as a bonus.',
    'Is this a feature branch or a branch you started in 2023 and forgot to delete?',
    'You resolved a conflict by deleting both versions. Bold. Terrifying, but bold.',
    'That .gitignore file ignores everything except your mistakes. Those are committed.',
    'Did you just amend a commit that was already pushed? The timeline is now broken.',
    'Your git log is longer than your patience and shorter than your excuses.',
    'Another rebase interactive where you squashed your dignity along with the commits.',
    'Is this a submodule or a nested doll of pain?',
    'You cloned a repo just to read the README and now you have 400 MB of regret.',
    'That merge just created a conflict in a file you have never even opened.',
    'Be honest, did you just git add . without checking what . actually contains?',
    'Your remote is called origin, your confidence is called gone.',
    'Another branch with no upstream set, floating in the void like your weekend plans.',
    'Did you just reset --hard and lose three hours of work? Yes. Yes you did.',
    'That tag is v1.0.0-final-real-this-time. Sure it is.',
    'Is this a hotfix or are we just hot-gluing production back together?',
    'You wrote a commit message that says minor changes and changed 47 files.',
    'Another pull that fast-forwarded your code and your anxiety at the same time.',
    'Your stash message is just asdf. Future you will love that.',
    'Did you just open a PR with no description? Reviewers can smell fear.',
    'That conflict marker <<<<<<< is still in the file. It has been there since Tuesday.',
    'Is this a monorepo or a black hole where good code goes to get lost?',
    'You forked a repo, changed one line, and called it a contribution. Respect, sort of.',
    'Another git bisect to find the commit that broke everything. Spoiler: it was yours.',
    'Your branch just diverged by 128 commits. That is not divergence, that is a breakup.',
    'Did you just delete a branch that had the only working version? Of course you did.',
    'That pre-commit hook just blocked your commit for linting. The linter is not wrong, you are.',
    'Is this a release or are we just tagging our trauma?',
    'You committed a .env file once and now security is in your DMs.',
    'Another git status that shows 200 modified files and you modified exactly one on purpose.',
    'Your commit just broke CI and CI is the only honest friend you have left.',
    'Did you just say let me just quickly rebase? Nothing quick has ever followed those words.',
    'That repository has more branches than your project has users.',
    'Is this git or a horror story told in commit messages?',
    'You pushed, the build failed, and you pretended you did not see the red X.',
    'Another day, another merge conflict in a file that is just a list of names.',
    'Your git history will be studied by future developers as a warning, not a guide.',
]

_NODE_POOL = [
    'Is this Node or a support group for people who installed one package too many?',
    'Your node_modules folder is bigger than your entire operating system. Congratulations.',
    'Be honest, did you npm install something just to print hello world?',
    'Another package.json with 47 dependencies and zero idea what half of them do.',
    'Did you just run npm install and watch your disk space disappear in real time?',
    'That callback hell is not code, it is a descent into madness with extra indentation.',
    'You updated one package and now everything is broken. Dependency roulette, again.',
    'Is this a server or a process that crashes when you look at it wrong?',
    'Another unhandled promise rejection. The promise was that this would work.',
    'Your code uses async/await and still somehow blocks everything. Impressive, in a bad way.',
    'Did you just console.log your way through a bug instead of actually debugging it? Respect.',
    'That version mismatch between Node 18 and Node 20 just ended your afternoon.',
    'Is this an API or a list of endpoints that return 500 with confidence?',
    'You installed a package to left-pad a string. The internet has not forgiven you yet.',
    'Another node_modules that you deleted and reinstalled, as if that was ever the fix.',
    'Your server just crashed because of an uncaught exception in a file you forgot existed.',
    'Be honest, how many of these dependencies are just dependencies of dependencies?',
    'That event loop is blocked and so is your weekend.',
    'Did you just run node app.js and hope? Hope is not a runtime strategy.',
    'Another .env file that is not actually loaded, so production is using defaults. Fun.',
    'Is this JavaScript or a language where == and === are two different kinds of betrayal?',
    'You used var in 2026. That is not retro, that is a cry for help.',
    'That npm audit just reported 900 vulnerabilities and you are ignoring all of them.',
    'Did you just copy a Stack Overflow snippet that uses eval? Security just left the chat.',
    'Your package-lock.json just changed by itself and now nobody trusts the build.',
    'Another port already in use error. Something else is running on 3000, probably your past self.',
    'Is this a microservice or a monolith with extra steps and a README that lies?',
    'You restarted the server and it worked. Nobody knows why. Do not touch it.',
    'That memory leak is not a bug, it is a feature that slowly consumes your RAM and your soul.',
    'Be honest, did you just use setTimeout to fix a race condition? Yes, you did.',
    'Your code has a comment that says TODO: fix this later. Later was three years ago.',
    'Another JSON.parse that just threw because the API returned HTML instead of JSON. Classic.',
    'Did you just require a file with a relative path that only works on your machine?',
    'That Express route just returned Cannot GET / and you are acting surprised.',
    'Is this Node or a therapy session where the therapist is also a JavaScript runtime?',
    'You installed TypeScript to avoid bugs and now you have TypeScript bugs instead.',
    'Another day, another node process that will not die even after you killed it twice.',
    'Your code uses Promise.all and one rejection just ruined all of them. Teamwork.',
    'Did you just run npm run dev and watch it fail because of a missing script? Classic.',
    'That error stack trace is longer than the actual code. It has its own lore now.',
    'Is this a REPL or are you just typing JavaScript into a terminal to feel something?',
    'You used a global variable to share state. The state is now shared with your regret.',
    'Another dependency just got deprecated and its maintainer just gave up. Same.',
    'Your server logs are just console.log spam with no timestamps. Archaeology, not debugging.',
    'Did you just deploy to production on a Friday? The on-call phone just started ringing.',
    'That callback just called back twice and now your database has duplicate everything.',
    'Is this Node or a machine that turns coffee into unhandled exceptions?',
    'You wrote a one-line script and it needs 200 MB of dependencies to run. Efficiency.',
    'Another npm install -g that just polluted your global environment forever.',
    'Your code works, but only if you run it with --experimental-something. Stable, sure.',
]

_PYTHON_POOL = [
    'Is this Python or a therapy session with indentation as the therapist?',
    'You got an IndentationError again. The code looked fine. It was not fine.',
    'Be honest, did you just pip install something without a virtualenv? Global Python is crying.',
    'Another venv that you forgot to activate, so you installed everything globally. Classic.',
    'Did you just use a mutable default argument and wonder why the list keeps growing?',
    'Your code has a variable named data, data2, and final_data. None of them are final.',
    'Is this a script or a Jupyter notebook that you converted to .py and hoped for the best?',
    'That traceback is longer than your code and it ends with a typo you made at 2am.',
    'You used == to compare two lists and got False. They looked identical. They were not.',
    'Another print debugging session, because breakpoints are for people with patience.',
    'Did you just import * and now you have no idea where that function came from?',
    'Your requirements.txt has no versions pinned. The build will break next week, guaranteed.',
    'Is this Python 2 or Python 3? The print statement just answered that for you, badly.',
    'You wrote a one-liner list comprehension that nobody, including you, can read.',
    'That RecursionError just happened because your base case was more of a suggestion.',
    'Be honest, how many of these imports are actually used? Half of them are just decoration.',
    'Your code just threw a TypeError because you added a string to an int. Again.',
    'Another virtualenv named venv, venv2, venv_final, venv_final2. We know what that means.',
    'Did you just run python instead of python3 and wonder why nothing works?',
    'That dictionary just lost a key and you are acting like it was never there.',
    'Is this a class or a collection of functions pretending to be object-oriented?',
    'You used global inside a function. The function works. Your architecture does not.',
    'Another f-string that just printed {variable} literally because you forgot the f.',
    'Your code has a comment that says hack, do not touch. Everyone will touch it.',
    'Did you just catch all exceptions with except: pass? The bug is now invisible, not fixed.',
    'That pip install just took ten minutes and installed a package you will use once.',
    'Is this a script or a list of TODOs that you will never actually do?',
    'You used os.system instead of subprocess. Security just felt a disturbance.',
    'Another NameError because you defined the variable after you used it. Time travel, sort of.',
    'Your code works on your machine because your machine has that one package nobody else has.',
    'Be honest, did you just copy a snippet that uses eval on user input? Bold. Reckless.',
    'That loop just ran forever because you forgot to increment the counter. Classic.',
    'Did you just use time.sleep to fix a race condition? Sleep is not a fix, it is a nap.',
    'Your function returns None and you are surprised the result is None. It always was.',
    'Is this Python or a language where whitespace is both the syntax and the enemy?',
    'You just used a lambda for something that deserved a real function and a real name.',
    'Another ModuleNotFoundError because the module is in a folder Python refuses to see.',
    'Your code has more try/except blocks than actual logic. Confidence, sort of.',
    'Did you just run a script that deletes files and hope the path was correct? It was not.',
    'That list just mutated while you were iterating over it. Python warned you. You ignored it.',
    'Is this a REPL or are you just typing Python into a terminal to avoid writing a real file?',
    'You used pickle to load data from the internet. That is not loading, that is trusting strangers.',
    'Another day, another dependency conflict where pip just gives up and you give up too.',
    'Your code just passed all tests because the tests are empty. Victory, sort of.',
    'Did you just use == True instead of just checking the value? We all saw it.',
    'That generator just got exhausted and you are wondering where your data went.',
    'Is this Python or a confession booth with a >>> prompt?',
    'You wrote a script to automate a task and now maintaining the script is the task.',
    'Another import that just shadowed a standard library module. Chaos, but make it Pythonic.',
    'Your code is PEP8 compliant and still completely unreadable. Impressive.',
]

_TERMINAL_POOL = [
    'Is this Windows Terminal or a tab hoarder support group?',
    'You have seven tabs open and no idea which one is actually doing something.',
    'Be honest, did you just split a pane to feel productive while doing nothing?',
    'Another JSON settings file that you edited by hand and immediately broke.',
    'Did you just change the colour scheme instead of fixing the actual problem? Classic.',
    'Your terminal has more profiles than you have actual projects.',
    'Is this a terminal or a collection of shells pretending to be one app?',
    'You set the default profile to something you do not even use. Bold.',
    'Another tab that says PowerShell, cmd, and WSL all at once. Identity crisis, sort of.',
    'Did you just close the wrong tab and lose the one command that was working?',
    'Your settings.json is 400 lines long and the comment at the top says keep it simple.',
    'Is this a new tab or are you just opening the same shell for the fifth time today?',
    'You changed the font to something fancy and now nothing is readable. Aesthetic, though.',
    'Another pane split that just made everything smaller and your patience thinner.',
    'Be honest, how many of these tabs are just sitting there, doing nothing, judging you?',
    'Your terminal just crashed and took all seven tabs with it. No warning, no mercy.',
    'Did you just paste a command into the wrong pane? The other shell just ran it. Fun.',
    'That acrylic blur looks nice and also makes your eyes hurt after an hour.',
    'Is this Windows Terminal or a window manager that you use to avoid actual work?',
    'You spent an hour customising the prompt and zero minutes using it productively.',
    'Another profile that you created, used once, and forgot exists.',
    'Your terminal history is just the same five commands, in different orders, forever.',
    'Did you just set the background image to something distracting and call it motivation?',
    'That tab title still says Windows PowerShell even though you are in WSL. Confusing, sort of.',
    'Is this a terminal or a tab bar that is slowly becoming your to-do list?',
    'You just used Ctrl+Shift+T to reopen a tab you closed on purpose. Regret, instantly.',
    'Another shortcut that you forgot, so you clicked through three menus instead.',
    'Your terminal just updated and reset your settings. Customisation is temporary, pain is permanent.',
    'Be honest, did you just open a new terminal because the old one had too much red text?',
    'That pane is so small you cannot read the output, but you refuse to close it.',
    'Is this a shell or a collection of shells that you switch between to avoid committing to one?',
    'You just dragged a tab out into a new window and now you have two problems instead of one.',
    'Another colour scheme named after a city you have never visited.',
    'Your terminal font ligatures just made == look like a single character. Cute, and also confusing.',
    'Did you just set the default shell to WSL and forget how to get back to PowerShell?',
    'That settings file has a trailing comma and now the whole terminal refuses to start.',
    'Is this Windows Terminal or a pretty box where your productivity goes to hide?',
    'You have a tab for every project and you are working on none of them right now.',
    'Another day, another terminal window that you opened, forgot, and left running overnight.',
    'Your prompt just shows the full path and it is so long it wraps to the next line.',
    'Did you just use the search feature in the terminal to find a command you typed five minutes ago?',
    'That tab just froze and you are staring at it like staring will unfreeze it.',
    'Is this a terminal or a museum of every shell you have ever tried and abandoned?',
    'You just changed the theme to dark mode, again, as if that was the problem.',
    'Another profile with a starting directory that no longer exists. It opens, it fails, it judges.',
    'Your terminal just beeped and you have no idea why. It will beep again. It always does.',
    'Did you just open Terminal to run one command and end up customising it for an hour?',
    'That window is maximised, minimised, and also somehow still in your way.',
    'Is this a new feature or are we just renaming the same tab bar and calling it innovation?',
    'You just closed Terminal and all your tabs are gone. They were not saved. They never are.',
]

_WSL_POOL = [
    'Is this WSL or a Linux machine pretending to be a Windows app?',
    'You just typed sudo and then realised you have no idea what the password is.',
    'Be honest, did you just apt update and then apt upgrade and then regret everything?',
    'Another distro that you installed, used once, and forgot exists.',
    'Did you just run a Linux command in Windows and wonder why it failed? Wrong OS, friend.',
    'Your WSL just ate all your RAM and Windows is now asking for it back, politely.',
    'Is this Ubuntu or a fresh install that you have already broken in three commands?',
    'You just edited a file in Windows and WSL sees a different version. Line endings, classic.',
    'Another permission denied because the file is owned by root and also by your past self.',
    'Did you just chmod 777 everything to fix permissions? Security just left the chat.',
    'Your WSL kernel just updated and now nothing that worked yesterday works today.',
    'Is this a terminal or a bridge between two operating systems that both blame each other?',
    'You just ran rm -rf in WSL and then remembered it can see your Windows files too.',
    'Another day, another package that is not found because apt needs an update first.',
    'Be honest, how many distros do you have installed just to say you use Linux?',
    'Your WSL just froze and Windows is pretending it does not know what happened.',
    'Did you just use wsl --shutdown to fix a problem and create three new ones?',
    'That path /mnt/c/Users/you is so long it deserves its own postcode.',
    'Is this Linux or a Windows feature that lets you feel superior while still using Windows?',
    'You just installed Docker in WSL and now your disk is full. Again.',
    'Another sudo apt install that just installed 200 dependencies for one tiny tool.',
    'Your .bashrc just broke and now every new shell starts with an error. Welcome back.',
    'Did you just try to run a GUI app in WSL and wonder why it looks wrong? It always looks wrong.',
    'That kernel panic just happened in a VM that is also not really a VM. Confusing.',
    'Is this WSL2 or WSL1? The answer determines how much of your life you will lose today.',
    'You just mounted a Windows drive and the permissions are now a work of fiction.',
    'Another day, another time sync issue where WSL thinks it is yesterday.',
    'Your WSL just ran out of disk space because Docker left 50 GB of images behind.',
    'Be honest, did you just use Linux commands in PowerShell by accident? We all saw it.',
    'That apt package just conflicted with another apt package. Apt is now in therapy.',
    'Did you just edit /etc/hosts and break networking for both OSes at once? Efficient.',
    'Your WSL distro just updated and your custom config is gone. It was never saved, was it?',
    'Is this a shell or a place where Windows and Linux argue about line endings forever?',
    'You just ran a script that works in Linux and fails in WSL because of one path. Classic.',
    'Another wsl --list --verbose that just shows distros you do not remember installing.',
    'Your Linux file system is case-sensitive and your Windows brain is not. Chaos.',
    'Did you just use grep to search a Windows folder from WSL and wait ten minutes?',
    'That service just failed to start in WSL because systemd is not really systemd here.',
    'Is this WSL or a science experiment where two OSes share one kernel and one grudge?',
    'You just copied a file from Windows to WSL and the permissions changed. Of course they did.',
    'Another day, another sudo command that you typed without thinking and then regretted.',
    'Your WSL just needs a restart and Windows just needs a restart and you just need a break.',
    'Did you just install a package with pip in WSL and also in Windows? Now you have two problems.',
    'That network just stopped working in WSL because Windows updated overnight. Thanks, Windows.',
    'Is this Linux or a Windows app that lets you run Linux commands and still blame Microsoft?',
    'You just used vim in WSL and now you cannot exit vim. Nobody can exit vim. That is the rule.',
    'Another distro upgrade that just broke Python, Node, and your will to continue.',
    'Your WSL just took 30 seconds to start and you are acting like that is fast. It is not.',
    'Did you just run a command that worked in Ubuntu and failed in Debian? Same Linux, different pain.',
    'That WSL terminal just closed and your long-running job is gone. It was almost done. Almost.',
]

TERMINAL_QUESTIONS = {
    "powershell": _POWERSHELL_POOL,
    "cmd": _CMD_POOL,
    "git": _GIT_POOL,
    "node": _NODE_POOL,
    "python": _PYTHON_POOL,
    "terminal": _TERMINAL_POOL,
    "wsl": _WSL_POOL,
}

# bash.exe and conhost.exe are resolved by exe path / parent process, not name alone.
TERMINAL_MAP = {
    "powershell.exe": "powershell",
    "pwsh.exe": "powershell",
    "cmd.exe": "cmd",
    "git.exe": "git",
    "git-bash.exe": "git",
    "node.exe": "node",
    "python.exe": "python",
    "windowsterminal.exe": "terminal",
    "wt.exe": "terminal",
    "wsl.exe": "wsl",
    "wslhost.exe": "wsl",
}

def _resolve_terminal_category(proc_name, exe_path=None, parent_name=None):
    if proc_name == "bash.exe":
        if exe_path and "git" in exe_path.lower():
            return "git"
        return "wsl"
    if proc_name == "conhost.exe":
        if parent_name in TERMINAL_MAP:
            return TERMINAL_MAP[parent_name]
        if parent_name == "bash.exe":
            return "wsl"
        return "cmd"
    return TERMINAL_MAP.get(proc_name)



# Stats jokes: 20 each. RAM >= 75%, CPU >= 80%, temp >= 50C.
# Separate timer, 5-minute cooldown per trigger, one trigger per check.
_RAM_STATS = [
    'RAM is at 75% and you are still opening tabs like RAM is free. It is not free, it is dying.',
    'Congratulations, you have turned your PC into a Chrome tab museum with no exit plan.',
    'RAM is full, your patience is empty, and somehow you are still opening one more app.',
    'Is this multitasking or are you just collecting open windows like they are Pokemon?',
    'Your RAM just filed for bankruptcy and you are the reason.',
    'Close a tab. No, not that one. Any tab. Literally any tab will do.',
    'RAM at 75% is not a warning, it is a cry for help written in swap file.',
    'You have more tabs open than you have brain cells left today, and both are struggling.',
    'This PC is not slow, it is just carrying your entire digital life on its back.',
    'RAM is begging for mercy and you just opened Discord, Spotify, and a game at the same time.',
    'Your memory usage is higher than your memory of what you were actually doing.',
    'Is this a computer or a hoarder house with a processor?',
    'RAM just hit 75% and your PC is now running on hope and page file.',
    'You keep saying just one more tab, and RAM keeps saying just one more funeral.',
    'Close Chrome and suddenly your PC feels like it just got a second life. Coincidence? No.',
    'Your RAM is full because you treat closing apps like a personal betrayal.',
    'This is not multitasking, this is digital self-harm with extra steps.',
    'RAM usage is at 75%, your productivity is at 5%, and somehow both are your fault.',
    'Your PC is swapping so hard it is basically writing a diary on your SSD now.',
    'RAM is at 75% and you are still surprised the fan sounds like a jet engine. Really?',
]

_CPU_STATS = [
    'CPU is at 80% and you are acting like this is normal. It is not normal, it is a meltdown in progress.',
    'Your processor is working harder than you have worked all week, and it is not even getting paid.',
    'Is this a PC or a space heater that also runs Chrome?',
    'CPU just hit 80% and your fan just started auditioning for a horror movie.',
    'You have one app eating all the CPU and you are still blaming Windows. Classic.',
    'Your CPU is not busy, it is drowning, and you just threw another tab in the water.',
    'At 80% CPU, your PC is basically running a marathon while you sit and watch it suffer.',
    'Close that one process. You know which one. The one using 60% for no reason.',
    'CPU usage is high, your code is slow, and somehow both are somehow your fault.',
    'This processor did not sign up to render, compile, stream, and update all at once.',
    'Your CPU is throttling and your patience is throttling faster.',
    'Is this multitasking or are you just torturing silicon for fun?',
    'CPU at 80% is not performance, it is a cry for help in binary.',
    'You just opened another heavy app and the CPU just quietly updated its will.',
    'Your fan is loud because your CPU is screaming, and you are ignoring both.',
    'This PC is not lagging, it is just contemplating its life choices at 80% load.',
    'CPU is at 80%, temperature is rising, and you are still saying just one more thing.',
    'Your processor has more threads than you have thoughts today, and all of them are busy.',
    'At this rate, your CPU will retire before you do.',
    'CPU usage is high, RAM is full, and you are still opening a game. Bold. Reckless, but bold.',
]

_TEMP_STATS = [
    'Temperature just crossed 50 degrees and your PC is now legally a cooking appliance.',
    'Is this a laptop or a frying pan with a keyboard attached?',
    'Your CPU is so hot it could fry an egg, and you are still using it as a lap warmer. Bold choice.',
    'At 50 degrees, your PC is not warm, it is just one bad decision away from thermal shutdown.',
    'Your fan is working overtime and your PC is still hot. That is not cooling, that is denial.',
    'Temperature is rising, performance is falling, and you are acting like this is fine. It is not fine.',
    'This PC is not overheating, it is just passionately expressing its feelings in Celsius.',
    'You could cook noodles on this keyboard right now, and honestly, that might be its best use today.',
    'At 50 degrees, your laptop is basically a portable heater that also crashes sometimes.',
    'Your CPU is hot because you treat it like it has no feelings. It does, and they are burning.',
    'Temperature just hit 50 and your PC just started throttling like it is trying to survive, not perform.',
    'Is this a computer or a sauna for silicon?',
    'Your laptop is so hot, even the table underneath it is asking for a break.',
    'At this temperature, your PC is not running, it is slowly melting with dignity.',
    'You just ignored the temperature warning and opened another game. Thermal paste just cried.',
    'This is fine. Everything is fine. The pet is on fire, the CPU is on fire, and you are still typing.',
    'Temperature is up, fan is loud, and you are still wondering why everything is lagging. Really?',
    'Your PC is hot enough to be a hand warmer in winter, and a fire hazard in summer.',
    'At 50 degrees, your CPU is not working, it is just surviving your decisions.',
    'If this laptop gets any hotter, it will start its own weather system. Congratulations.',
]

STATS_TRIGGERS = {
    "ram": {"pool": _RAM_STATS, "mascot": "system-monitoring-dashboard.png"},
    "cpu": {"pool": _CPU_STATS, "mascot": "processing-logic-symbols.png"},
    "temp": {"pool": _TEMP_STATS, "mascot": "fine-under-pressure.png"},
}
RAM_THRESHOLD = 75
CPU_THRESHOLD = 80
TEMP_THRESHOLD_C = 50
STATS_COOLDOWN_S = 300

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

# Idle fidgets: after 10 min with no interaction, show a random pose from assets/idle_extras/.

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

def get_foreground_process_info():
    """Return (process name, exe path, parent process name) for the
    foreground window, or (None, None, None) if it cannot be determined.
    The exe path / parent name matter for bash.exe and conhost.exe, where
    the process name alone does not say which shell is actually running."""
    if not IS_WINDOWS or win32gui is None or psutil is None:
        return None, None, None
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        name = proc.name().lower()
        try:
            exe = proc.exe()
        except Exception:
            exe = None
        try:
            parent = proc.parent()
            parent_name = parent.name().lower() if parent else None
        except Exception:
            parent_name = None
        return name, exe, parent_name
    except Exception:
        return None, None, None

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


def _get_cpu_temperature_c():
    """Best-effort CPU temperature in Celsius, or None if unavailable.
    psutil.sensors_temperatures() does not work on Windows, so on Windows
    this falls back to nvidia-smi (GPU temperature, only if an NVIDIA GPU
    and nvidia-smi are present). It never raises, and never blocks for
    long: a missing sensor simply means the temp trigger stays silent,
    while RAM and CPU triggers keep working."""
    if psutil is not None:
        try:
            temps = psutil.sensors_temperatures()
        except Exception:
            temps = {}
        if temps:
            for entries in temps.values():
                for entry in entries:
                    try:
                        if entry.current is not None:
                            return float(entry.current)
                    except Exception:
                        continue
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=2,
        ).stdout.strip()
        if out:
            return float(out.splitlines()[0].strip())
    except Exception:
        pass
    return None

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
        self._terminal_proc = None
        self._allow_close = False  # only the shutdown hook sets this True

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

        self.joke_timer = QTimer(self)
        self.joke_timer.timeout.connect(self._random_joke_or_question)
        self.joke_timer.start(30_000)

        self.app_timer = QTimer(self)
        self.app_timer.timeout.connect(self._check_foreground_app)
        self.app_timer.start(4_000)
        self._last_category = None
        self._last_proc = None
        self._last_terminal = None

        # idle-fidget watcher — checked every 30s, only actually fires once
        # IDLE_FIDGET_AFTER_MS of zero interaction has passed
        self.fidget_timer = QTimer(self)
        self.fidget_timer.timeout.connect(self._maybe_fidget)
        self.fidget_timer.start(30_000)

        # Stats watcher: separate timer. Prime cpu_percent() once, first call returns 0.0.
        self._last_stats_time = {}
        if psutil is not None:
            try:
                psutil.cpu_percent(interval=None)
            except Exception:
                pass
        self.stats_timer = QTimer(self)
        self.stats_timer.timeout.connect(self._maybe_stats_joke)
        self.stats_timer.start(30_000)

        QTimer.singleShot(600, self._welcome)
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
    def _welcome(self):
        self.set_state("welcome")
        self.say("welcome back! let's build something today ✨")
        QTimer.singleShot(4000, lambda: self.set_state("idle"))

    def say_bye_and_allow_close(self):
        self.set_state("talk")
        self.say(random.choice(["see you soon!", "bye bro!", "see ya later!"]), duration_ms=2500)
    def _check_foreground_app(self):
        if self._dragging or self._launch_stage is not None:
            return
        proc, exe_path, parent_name = get_foreground_process_info()
        if proc is None:
            return
        if proc == self._last_proc:
            return
        self._last_proc = proc
        terminal = _resolve_terminal_category(proc, exe_path, parent_name)

        if proc in MUSIC_PROCS:
            self._last_terminal = None
            self.set_state("vibe")
            self.say("nice track, vibing with you \U0001F3B6")
            return

        if proc in KNOWN_APPS:
            self._last_terminal = None
            self.set_state("talk")
            self.say(random.choice(APP_QUESTIONS[proc]))
            return

        if terminal in TERMINAL_QUESTIONS:
            self._last_terminal = terminal
            self.set_state("talk")
            self.say(random.choice(TERMINAL_QUESTIONS[terminal]))
            return

        # unknown app -> confused line, but not spammy for Explorer/system procs
        # Note: python.exe is NOT ignored here any more — it is a terminal
        # category above. pythonw.exe stays ignored because that is how the
        # pet itself runs, so the pet must not react to its own process.
        self._last_terminal = None
        if proc in ("explorer.exe", "dwm.exe", "searchhost.exe", "shellexperiencehost.exe",
                    "claudeanimatedpet.exe", "pythonw.exe"):
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
        elif self._last_terminal in TERMINAL_QUESTIONS:
            pool += TERMINAL_QUESTIONS[self._last_terminal]
        self.say(random.choice(pool), duration_ms=5000)
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
    def _maybe_stats_joke(self):
        # Do not override a drag, launch, or fidget in progress.
        if self._dragging or self._launch_stage is not None or self._fidgeting:
            return
        if psutil is None:
            return
        now = time.time()
        fired = []
        try:
            ram_pct = psutil.virtual_memory().percent
        except Exception:
            ram_pct = 0
        try:
            cpu_pct = psutil.cpu_percent(interval=None)
        except Exception:
            cpu_pct = 0
        temp_c = _get_cpu_temperature_c()
        candidates = []
        if ram_pct >= RAM_THRESHOLD:
            candidates.append("ram")
        if cpu_pct >= CPU_THRESHOLD:
            candidates.append("cpu")
        if temp_c is not None and temp_c >= TEMP_THRESHOLD_C:
            candidates.append("temp")
        # Per-trigger cooldown, so a hot/full PC does not spam.
        candidates = [
            c for c in candidates
            if now - self._last_stats_time.get(c, 0) >= STATS_COOLDOWN_S
        ]
        if not candidates:
            return
        trigger = random.choice(candidates)
        self._last_stats_time[trigger] = now
        info = STATS_TRIGGERS[trigger]
        self._do_stats_joke(info["mascot"], random.choice(info["pool"]))

    def _do_stats_joke(self, mascot_file, joke):
        # Show the trigger's mascot from assets/idle_extras/ for 5 seconds.
        path = os.path.join(IDLE_EXTRAS_DIR, mascot_file)
        pix = QPixmap(path)
        if pix.isNull():
            self.say(joke, duration_ms=5000)
            return
        pix = pix.scaled(SPRITE_SIZE, SPRITE_SIZE, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._fidgeting = True
        self.label.setPixmap(pix)
        self.say(joke, duration_ms=5000)
        QTimer.singleShot(5000, self._end_fidget)
    def _start_claude_launch(self):
        if self._launch_stage is not None:
            return
        self._launch_stage = "terminal_open"
        self.set_state("click")
        self.say("launching claude for you...", duration_ms=3000)
        try:
            if IS_WINDOWS:
                # open a terminal and type claude (old CLI launch)
                self._terminal_proc = subprocess.Popen(
                    ["cmd.exe", "/K", "claude"],
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
            else:
                self._terminal_proc = subprocess.Popen(
                    ["x-terminal-emulator", "-e", "bash -c 'claude; exec bash'"]
                )
        except Exception:
            self._terminal_proc = None
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
            # close the terminal we opened
            if getattr(self, "_terminal_proc", None) is not None:
                try:
                    self._terminal_proc.terminate()
                except Exception:
                    pass
                self._terminal_proc = None
            self.set_state("click")
            self.say("LETS CODE \U0001F4BB\U0001F525", duration_ms=3500)
            QTimer.singleShot(3500, lambda: self.set_state("idle"))
            self._launch_stage = None
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
        # Alt+F4 / window X must not kill the pet, otherwise it would not
        # be alive at shutdown to show the bye bubble for 1.8s.
        # Only the shutdown hook sets _allow_close = True, when it releases
        # its shutdown block. To quit manually, end the task in Task Manager.
        if getattr(self, "_allow_close", False):
            self._save_position()
            event.accept()
        else:
            event.ignore()
            self.say("nope, I'm staying here!", duration_ms=2000)

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
        if msg == WM_ENDSESSION:
            pet._allow_close = True
            return ctypes.windll.user32.CallWindowProcW(old_wndproc, hWnd, msg, wParam, lParam)
        if msg == WM_QUERYENDSESSION:
            if not getattr(pet, "_bye_shown", False):
                pet._bye_shown = True
                pet.say_bye_and_allow_close()
                QTimer.singleShot(1800, lambda: _release_block(hwnd))
                return 0  # block briefly so the bubble is visible
            # Bye already shown and block released: let Windows close us.
            return ctypes.windll.user32.CallWindowProcW(old_wndproc, hWnd, msg, wParam, lParam)
        return ctypes.windll.user32.CallWindowProcW(old_wndproc, hWnd, msg, wParam, lParam)

    def _release_block(hwnd_):
        try:
            pet._allow_close = True
        except Exception:
            pass
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
