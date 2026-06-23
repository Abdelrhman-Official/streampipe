"""
StreamPipe Mobile App — Kivy
Run locally (desktop preview): python mobile/main.py
Build for Android:  buildozer android debug
"""
import sys
import os
import threading
from pathlib import Path

# Allow imports from project root when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("KIVY_NO_CONSOLELOG", "1")

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, SlideTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.progressbar import ProgressBar
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle

from streampipe.config import ConfigManager
from streampipe.utils import is_ffmpeg_available
from gui.core_bridge import GUIDownloader, DownloadJob

# ── Theme ─────────────────────────────────────────────────────────────────
BG      = (0.08, 0.08, 0.14, 1)
CARD    = (0.09, 0.13, 0.24, 1)
BLUE    = (0.08, 0.39, 0.75, 1)
CYAN    = (0.0,  0.78, 1.0,  1)
GREEN   = (0.0,  0.90, 0.46, 1)
RED     = (1.0,  0.32, 0.32, 1)
GRAY    = (0.55, 0.55, 0.65, 1)
WHITE   = (1.0,  1.0,  1.0,  1)
SIDEBAR = (0.06, 0.20, 0.38, 1)

Window.clearcolor = BG


# ── Helpers ───────────────────────────────────────────────────────────────
def card_button(text, on_press, bg=BLUE, **kw):
    btn = Button(text=text, size_hint_y=None, height=dp(48),
                 background_normal="", background_color=bg,
                 color=WHITE, font_size=dp(14), bold=True,
                 on_press=on_press, **kw)
    return btn


def label(text, size=14, color=WHITE, bold=False, **kw):
    return Label(text=text, font_size=dp(size), color=color, bold=bold,
                 size_hint_y=None, height=dp(30), **kw)


def entry(hint="", **kw):
    return TextInput(hint_text=hint, multiline=False,
                     background_color=(0.05, 0.05, 0.1, 1),
                     foreground_color=WHITE,
                     hint_text_color=GRAY,
                     cursor_color=CYAN,
                     size_hint_y=None, height=dp(46),
                     padding=[dp(12), dp(10)],
                     font_size=dp(14), **kw)


def spinner_widget(values, default, **kw):
    return Spinner(text=default, values=values,
                   size_hint_y=None, height=dp(42),
                   background_normal="", background_color=CARD,
                   color=WHITE, font_size=dp(13), **kw)


# ── Bottom nav bar ────────────────────────────────────────────────────────
class NavBar(BoxLayout):
    def __init__(self, sm: ScreenManager, **kw):
        super().__init__(orientation="horizontal",
                         size_hint_y=None, height=dp(56),
                         spacing=0, **kw)
        self._sm = sm
        nav_items = [
            ("⬇ Download", "home"),
            ("📋 Batch",   "batch"),
            ("⚙ Settings", "settings"),
        ]
        for (txt, screen) in nav_items:
            btn = Button(text=txt, background_normal="",
                         background_color=SIDEBAR, color=WHITE,
                         font_size=dp(12), bold=True,
                         on_press=lambda _, s=screen: self._go(s))
            self.add_widget(btn)

    def _go(self, screen):
        self._sm.current = screen


# ── ProgressCard ─────────────────────────────────────────────────────────
class ProgressCard(BoxLayout):
    def __init__(self, job: DownloadJob, **kw):
        super().__init__(orientation="vertical",
                         size_hint_y=None, height=dp(90),
                         padding=dp(10), spacing=dp(4), **kw)
        self.job = job
        self._title = Label(text=job.title[:50], font_size=dp(13),
                            color=WHITE, halign="left",
                            size_hint_y=None, height=dp(24))
        self._title.bind(size=self._title.setter("text_size"))
        self._bar = ProgressBar(max=100, value=0,
                                size_hint_y=None, height=dp(10))
        self._status = Label(text="Starting…", font_size=dp(11),
                             color=list(GRAY), halign="left",
                             size_hint_y=None, height=dp(20))
        self._status.bind(size=self._status.setter("text_size"))
        self.add_widget(self._title)
        self.add_widget(self._bar)
        self.add_widget(self._status)
        with self.canvas.before:
            Color(*CARD)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *_):
        self._rect.pos  = self.pos
        self._rect.size = self.size

    def refresh(self, job: DownloadJob):
        self._title.text = job.title[:50]
        self._bar.value  = round(job.progress * 100)
        speed = (job.speed or 0) / 1_048_576
        info  = f"{job.status.capitalize()}"
        if job.total:
            mb = job.downloaded / 1_048_576
            info += f"  •  {mb:.1f} MB  •  {speed:.2f} MB/s"
        self._status.text = info
        colors = {"done": GREEN, "error": RED, "cancelled": (1,.7,0,1)}
        self._status.color = list(colors.get(job.status, GRAY))


# ── Home Screen ───────────────────────────────────────────────────────────
class HomeScreen(Screen):
    def __init__(self, cfg: ConfigManager, **kw):
        super().__init__(name="home", **kw)
        self.cfg = cfg
        self._cards: dict[str, ProgressCard] = {}
        self._pending: list = []
        self._build()
        Clock.schedule_interval(self._flush, 0.15)

    def _build(self):
        root = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(8))

        # Header
        root.add_widget(Label(text="🎬⚡ StreamPipe", font_size=dp(22), bold=True,
                              color=list(CYAN), size_hint_y=None, height=dp(44)))
        root.add_widget(Label(text="YouTube Downloader", font_size=dp(12),
                              color=list(GRAY), size_hint_y=None, height=dp(24)))

        # URL input
        self._url = entry(hint="Paste YouTube URL…")
        root.add_widget(label("URL", size=12, color=GRAY))
        root.add_widget(self._url)

        # Options row
        opts = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        self._qual = spinner_widget(
            ["best","1080p","720p","480p","360p"], "best", size_hint_x=0.4)
        self._fmt  = spinner_widget(["mp4","mkv","webm"], "mp4", size_hint_x=0.3)
        self._audio_btn = ToggleButton(text="Audio Only",
                                       background_normal="",
                                       background_color=CARD,
                                       background_down="",
                                       color=WHITE,
                                       font_size=dp(12),
                                       size_hint_x=0.3)
        opts.add_widget(self._qual)
        opts.add_widget(self._fmt)
        opts.add_widget(self._audio_btn)
        root.add_widget(label("Quality / Format / Mode", size=12, color=GRAY))
        root.add_widget(opts)

        # Download button
        root.add_widget(card_button("⬇  Download", self._download))

        # Progress list
        root.add_widget(label("Downloads", size=13, bold=True))
        scroll = ScrollView()
        self._prog_list = GridLayout(cols=1, spacing=dp(6),
                                     size_hint_y=None, padding=dp(4))
        self._prog_list.bind(minimum_height=self._prog_list.setter("height"))
        scroll.add_widget(self._prog_list)
        root.add_widget(scroll)
        self.add_widget(root)

    def _download(self, *_):
        url = self._url.text.strip()
        if not url:
            self._popup("Error", "Please enter a URL."); return
        job = DownloadJob(url)
        card = ProgressCard(job)
        self._prog_list.add_widget(card)
        self._cards[job.job_id] = card

        def cb(j):
            self._pending.append((j, card))

        opts = dict(quality=self._qual.text,
                    format_pref=self._fmt.text,
                    audio_only=self._audio_btn.state == "down",
                    outdir=self.cfg.get("download_dir",
                                        str(Path.home() / "Downloads")))
        threading.Thread(
            target=GUIDownloader(on_progress=cb, config_manager=self.cfg).download,
            args=(job,), kwargs=opts, daemon=True
        ).start()

    def _flush(self, dt):
        for job, card in self._pending:
            card.refresh(job)
        self._pending.clear()

    def _popup(self, title, msg):
        Popup(title=title, content=Label(text=msg),
              size_hint=(0.8, 0.3)).open()


# ── Batch Screen ──────────────────────────────────────────────────────────
class BatchScreen(Screen):
    def __init__(self, cfg: ConfigManager, **kw):
        super().__init__(name="batch", **kw)
        self.cfg = cfg
        self._pending: list = []
        self._cards: dict = {}
        self._build()
        Clock.schedule_interval(self._flush, 0.15)

    def _build(self):
        root = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(8))
        root.add_widget(Label(text="Batch / Playlist", font_size=dp(20), bold=True,
                              color=list(CYAN), size_hint_y=None, height=dp(40)))

        root.add_widget(label("Playlist URL", size=12, color=GRAY))
        self._pl_url = entry(hint="YouTube playlist URL…")
        root.add_widget(self._pl_url)

        par_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        par_row.add_widget(Label(text="Parallel:", color=WHITE,
                                 size_hint_x=0.35, font_size=dp(13)))
        self._par = spinner_widget(["1","2","3","4","5"], "2", size_hint_x=0.65)
        par_row.add_widget(self._par)
        root.add_widget(par_row)
        root.add_widget(card_button("⬇  Download Playlist", self._start_playlist))

        root.add_widget(Label(text="─" * 50, color=list(GRAY),
                              size_hint_y=None, height=dp(20), font_size=dp(10)))

        root.add_widget(label("Multiple URLs (one per line)", size=12, color=GRAY))
        self._urls_input = TextInput(
            hint_text="https://youtube.com/watch?v=...\nhttps://youtube.com/watch?v=...",
            background_color=(0.05, 0.05, 0.1, 1),
            foreground_color=WHITE, hint_text_color=list(GRAY),
            size_hint_y=None, height=dp(120), font_size=dp(13))
        root.add_widget(self._urls_input)
        root.add_widget(card_button("⬇  Download All URLs", self._start_batch))

        root.add_widget(label("Batch Progress", size=13, bold=True))
        scroll = ScrollView()
        self._prog_list = GridLayout(cols=1, spacing=dp(6),
                                     size_hint_y=None, padding=dp(4))
        self._prog_list.bind(minimum_height=self._prog_list.setter("height"))
        scroll.add_widget(self._prog_list)
        root.add_widget(scroll)
        self.add_widget(root)

    def _start_playlist(self, *_):
        url = self._pl_url.text.strip()
        if not url: return
        par = int(self._par.text)

        def run():
            from streampipe.core.extractor import Extractor
            try:
                info = Extractor().extract_playlist_info(url)
            except Exception as e:
                return
            entries = info.get("entries", [])
            jobs = []
            for e in entries:
                u = e.get("url") or e.get("webpage_url")
                if not u and e.get("id"):
                    u = f"https://www.youtube.com/watch?v={e['id']}"
                if u:
                    j = DownloadJob(u)
                    card = ProgressCard(j)
                    Clock.schedule_once(lambda dt, c=card: self._prog_list.add_widget(c))
                    self._cards[j.job_id] = card
                    jobs.append(j)

            def cb(job):
                self._pending.append((job, self._cards.get(job.job_id)))

            GUIDownloader(on_progress=cb, config_manager=self.cfg).download_batch(
                jobs, parallel=par,
                outdir=self.cfg.get("download_dir", str(Path.home() / "Downloads")))

        threading.Thread(target=run, daemon=True).start()

    def _start_batch(self, *_):
        raw = self._urls_input.text.strip()
        urls = [l.strip() for l in raw.splitlines()
                if l.strip() and not l.strip().startswith("#")]
        if not urls: return
        jobs = []
        for u in urls:
            j = DownloadJob(u)
            card = ProgressCard(j)
            self._prog_list.add_widget(card)
            self._cards[j.job_id] = card
            jobs.append(j)

        def cb(job):
            self._pending.append((job, self._cards.get(job.job_id)))

        threading.Thread(
            target=GUIDownloader(on_progress=cb, config_manager=self.cfg).download_batch,
            args=(jobs,),
            kwargs={"parallel": int(self._par.text),
                    "outdir": self.cfg.get("download_dir", str(Path.home() / "Downloads"))},
            daemon=True
        ).start()

    def _flush(self, dt):
        for job, card in self._pending:
            if card:
                card.refresh(job)
        self._pending.clear()


# ── Settings Screen ───────────────────────────────────────────────────────
class SettingsScreen(Screen):
    def __init__(self, cfg: ConfigManager, **kw):
        super().__init__(name="settings", **kw)
        self.cfg = cfg
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        root.add_widget(Label(text="Settings", font_size=dp(20), bold=True,
                              color=list(CYAN), size_hint_y=None, height=dp(40)))

        root.add_widget(label("Default Quality", size=12, color=GRAY))
        self._qual = spinner_widget(
            ["best","4k","1080p","720p","480p","360p"],
            self.cfg.get("quality", "best"))
        root.add_widget(self._qual)

        root.add_widget(label("Default Format", size=12, color=GRAY))
        self._fmt = spinner_widget(
            ["mp4","mkv","webm"],
            self.cfg.get("preferred_format", "mp4"))
        root.add_widget(self._fmt)

        root.add_widget(label("Parallel Downloads", size=12, color=GRAY))
        self._par = spinner_widget(
            ["1","2","3","4","5"],
            str(self.cfg.get("parallel", 2)))
        root.add_widget(self._par)

        root.add_widget(label("Download Folder (Android: leave blank for default)",
                              size=11, color=GRAY))
        self._dir = entry(hint="/sdcard/Download or leave blank")
        self._dir.text = self.cfg.get("download_dir", "")
        root.add_widget(self._dir)

        ffok = is_ffmpeg_available()
        root.add_widget(Label(
            text=f"FFmpeg: {'✅ Available' if ffok else '❌ Not Found'}",
            font_size=dp(13), color=list(GREEN if ffok else RED),
            size_hint_y=None, height=dp(32)))

        root.add_widget(card_button("💾  Save Settings", self._save))
        root.add_widget(Label())  # spacer
        self.add_widget(root)

    def _save(self, *_):
        self.cfg.set("quality",          self._qual.text)
        self.cfg.set("preferred_format", self._fmt.text)
        self.cfg.set("parallel",         int(self._par.text))
        if self._dir.text.strip():
            self.cfg.set("download_dir", self._dir.text.strip())
        Popup(title="Saved",
              content=Label(text="Settings saved!"),
              size_hint=(0.6, 0.25)).open()


# ── App Entry ─────────────────────────────────────────────────────────────
class StreamPipeMobileApp(App):
    def build(self):
        self.title = "StreamPipe"
        cfg = ConfigManager()

        sm = ScreenManager(transition=SlideTransition())
        sm.add_widget(HomeScreen(cfg))
        sm.add_widget(BatchScreen(cfg))
        sm.add_widget(SettingsScreen(cfg))

        root = BoxLayout(orientation="vertical")
        root.add_widget(sm)
        root.add_widget(NavBar(sm))
        return root


if __name__ == "__main__":
    StreamPipeMobileApp().run()
