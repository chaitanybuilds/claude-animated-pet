"""
claude-animated-pet - an animated desktop companion for Claude Code.
Windows-focused PyQt5 app:
 - transparent, always-on-top, frameless, draggable sprite
 - greets you on login
 - watches the foreground process, reacts per-app (random questions you're
   not expected to answer, "what is this place?" for unknown apps, vibes
   to music)
 - click => opens a terminal, types `claude`, waits for the Claude desktop
   app, then closes the terminal and hypes you up to start coding
 - every 30s: random coding joke/question in a speech bubble
 - drag => "wowww!!!!" ; drop => "new place!! same craze!!!"
 - on shutdown/logoff => says bye (briefly delays shutdown)
"""

import os
import sys
import json
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
CONFIG_PATH = os.path.join(BASE_DIR, "pet_config.json")

SPRITE_SIZE = 150  # on-screen pet size (px)

# --------------------------------------------------------------------------
# Content: jokes, per-app questions, unknown-app lines
# --------------------------------------------------------------------------

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
]

# process-name -> list of app-specific question strings (random pick each time)
APP_QUESTIONS = {
    "discord.exe": [
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
    ],
    "chrome.exe": [
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
    ],
    "code.exe": [
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
    ],
    "claude.exe": [
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
    ],
    "steam.exe": [
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
    ],
    "unity.exe": [
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
    ],
    "unityhub.exe": [
        "Which project are we opening today?",
        "Is this Unity version actually compatible or are we gambling?",
        "New project or back into the chaos of an old one?",
    ],
}

UNKNOWN_LINES = [
    "What is this place?",
    "Umm... Never seen this one before?",
    "Ok new app unlocked, what does this do?",
]

# known apps that get a dedicated question pool (process name -> pool key above)
KNOWN_APPS = set(APP_QUESTIONS.keys())

MUSIC_PROCS = {"spotify.exe", "music.exe", "wmplayer.exe", "groove.exe"}


# --------------------------------------------------------------------------
# Foreground app watcher
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# Speech bubble
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# Sprite loader / animator
# --------------------------------------------------------------------------

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


# --------------------------------------------------------------------------
# Main pet widget
# --------------------------------------------------------------------------

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
        self.label = QLabel(self)
        self.label.setGeometry(0, 0, SPRITE_SIZE, SPRITE_SIZE)
        self.label.setAlignment(Qt.AlignCenter)

        self.bubble = SpeechBubble()

        self._drag_pos = None
        self._dragging = False
        self._launch_stage = None  # None, 'terminal_open', 'waiting_claude'
        self._terminal_proc = None

        self._load_position()
        self._apply_frame()
        self.show()

        # animation timer
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._tick_animation)
        self.anim_timer.start(120)

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

    def _apply_frame(self):
        frames = self.sprites.frames(self.state)
        if not frames:
            return
        self.frame_idx %= len(frames)
        self.label.setPixmap(frames[self.frame_idx])

    def _tick_animation(self):
        self.frame_idx += 1
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

    # ---- click-to-launch-claude ----
    def _start_claude_launch(self):
        if self._launch_stage is not None:
            return
        self._launch_stage = "terminal_open"
        self.set_state("click")
        self.say("launching claude for you...", duration_ms=3000)
        try:
            if IS_WINDOWS:
                # open a terminal and type claude
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
            if self._terminal_proc is not None:
                try:
                    self._terminal_proc.terminate()
                except Exception:
                    pass
            self.set_state("click")
            self.say("LETS CODE \U0001F4BB\U0001F525", duration_ms=3500)
            QTimer.singleShot(3500, lambda: self.set_state("idle"))
            self._launch_stage = None

    # ---- mouse / drag ----
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            self._dragging = False
            self._press_time = time.time()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            if not self._dragging:
                self._dragging = True
                self.set_state("drag")
                self.say("wowww!!!!", duration_ms=1500)
            self.move(event.globalPos() - self._drag_pos)
            self.bubble.move(
                self.x() + SPRITE_SIZE // 2 - self.bubble.width() // 2,
                self.y() - self.bubble.height() - 10,
            )
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            was_dragging = self._dragging
            self._dragging = False
            self._drag_pos = None
            self._save_position()
            if was_dragging:
                self.set_state("vibe")
                self.say("new place!! same craze!!!", duration_ms=2000)
                QTimer.singleShot(2000, lambda: self.set_state("idle"))
            else:
                # it was a click, not a drag
                self._start_claude_launch()
            event.accept()

    def closeEvent(self, event):
        self._save_position()
        event.accept()


# --------------------------------------------------------------------------
# Windows shutdown/logoff hook
# --------------------------------------------------------------------------

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
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(True)
    pet = PetWidget()
    install_shutdown_hook(app, pet)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
