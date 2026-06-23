"""
StreamPipe Windows Desktop App — CustomTkinter GUI
Run: python -m gui.windows_app
"""
import sys
import threading
import queue
from pathlib import Path
from tkinter import filedialog, messagebox

sys.path.insert(0, str(Path(__file__).parent.parent))

import customtkinter as ctk
from streampipe.config import ConfigManager
from streampipe.utils import is_ffmpeg_available
from gui.core_bridge import GUIDownloader, DownloadJob

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

CYAN   = "#00c8ff"
BLUE   = "#1565c0"
GREEN  = "#00e676"
RED    = "#ff5252"
YELLOW = "#ffca28"
BG     = "#1a1a2e"
CARD   = "#16213e"
SIDEBAR= "#0f3460"


# ─────────────────────────────── ProgressRow ────────────────────────────────
class ProgressRow(ctk.CTkFrame):
    def __init__(self, master, title, **kw):
        super().__init__(master, fg_color=CARD, corner_radius=8, **kw)
        self.columnconfigure(0, weight=1)

        self._title = ctk.CTkLabel(self, text=title[:60], anchor="w",
                                   font=ctk.CTkFont(size=12))
        self._title.grid(row=0, column=0, columnspan=2, padx=12, pady=(8,2), sticky="w")

        self._bar = ctk.CTkProgressBar(self, height=6, progress_color=CYAN)
        self._bar.set(0)
        self._bar.grid(row=1, column=0, padx=12, pady=2, sticky="ew")

        self._status = ctk.CTkLabel(self, text="Starting…", width=90,
                                    font=ctk.CTkFont(size=10), text_color="gray",
                                    anchor="e")
        self._status.grid(row=1, column=1, padx=(4,12), pady=2)

        self._info = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=10),
                                  text_color="gray", anchor="w")
        self._info.grid(row=2, column=0, columnspan=2, padx=12, pady=(0,8), sticky="w")

    def update_job(self, job: DownloadJob):
        self._title.configure(text=job.title[:60])
        self._bar.set(min(job.progress, 1.0))
        status_colors = {"done": GREEN, "error": RED, "cancelled": YELLOW,
                         "muxing": CYAN, "downloading": "white"}
        color = status_colors.get(job.status, "gray")
        self._status.configure(text=job.status.capitalize(), text_color=color)
        if job.total:
            mb_done = job.downloaded / 1_048_576
            mb_total = job.total / 1_048_576
            spd = (job.speed or 0) / 1_048_576
            self._info.configure(text=f"{mb_done:.1f} / {mb_total:.1f} MB  •  {spd:.2f} MB/s")


# ─────────────────────────────── Main App ───────────────────────────────────
class StreamPipeApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("StreamPipe  🎬⚡")
        self.geometry("960x680")
        self.minsize(820, 580)
        self.configure(fg_color=BG)

        self.cfg = ConfigManager()
        self._dl_rows: dict[str, ProgressRow] = {}
        self._ui_queue: queue.Queue = queue.Queue()

        self._build_ui()
        self._poll_queue()

    # ── Layout ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self._build_sidebar()
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self._content.columnconfigure(0, weight=1)
        self._content.rowconfigure(0, weight=1)
        self._panes = {
            "download": self._build_download_pane(),
            "batch":    self._build_batch_pane(),
            "settings": self._build_settings_pane(),
        }
        self._show("download")

    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=190, corner_radius=0, fg_color=SIDEBAR)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.rowconfigure(10, weight=1)

        ctk.CTkLabel(sb, text="🎬⚡", font=ctk.CTkFont(size=34)).grid(
            row=0, column=0, pady=(28, 2))
        ctk.CTkLabel(sb, text="StreamPipe",
                     font=ctk.CTkFont(size=18, weight="bold"),
                     text_color=CYAN).grid(row=1, column=0, pady=(0, 4))
        ctk.CTkLabel(sb, text="YouTube Downloader",
                     font=ctk.CTkFont(size=11), text_color="gray").grid(
            row=2, column=0, pady=(0, 24))

        nav_style = dict(anchor="w", fg_color="transparent",
                         text_color="white", hover_color="#1a4a7a",
                         height=42, font=ctk.CTkFont(size=13))
        ctk.CTkButton(sb, text="  ⬇   Download",
                      command=lambda: self._show("download"),
                      **nav_style).grid(row=3, column=0, padx=10, pady=3, sticky="ew")
        ctk.CTkButton(sb, text="  📋  Batch / Playlist",
                      command=lambda: self._show("batch"),
                      **nav_style).grid(row=4, column=0, padx=10, pady=3, sticky="ew")
        ctk.CTkButton(sb, text="  ⚙   Settings",
                      command=lambda: self._show("settings"),
                      **nav_style).grid(row=5, column=0, padx=10, pady=3, sticky="ew")

        ffok = is_ffmpeg_available()
        ctk.CTkLabel(sb,
                     text="● FFmpeg: OK" if ffok else "● FFmpeg: Missing",
                     text_color=GREEN if ffok else RED,
                     font=ctk.CTkFont(size=11)).grid(row=11, column=0, pady=20)

    # ── Download Pane ────────────────────────────────────────────────────────
    def _build_download_pane(self):
        f = ctk.CTkFrame(self._content, fg_color="transparent")
        f.columnconfigure(0, weight=1)
        f.rowconfigure(5, weight=1)

        ctk.CTkLabel(f, text="Download Video",
                     font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 12))

        # URL row
        url_card = ctk.CTkFrame(f, fg_color=CARD, corner_radius=10)
        url_card.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        url_card.columnconfigure(0, weight=1)
        self._url = ctk.CTkEntry(url_card, placeholder_text="Paste YouTube URL…",
                                 height=44, font=ctk.CTkFont(size=13),
                                 fg_color="#0d0d1a", border_color=CYAN)
        self._url.grid(row=0, column=0, padx=(12,6), pady=10, sticky="ew")
        ctk.CTkButton(url_card, text="Paste", width=72, height=44,
                      fg_color=BLUE, hover_color="#0d47a1",
                      command=self._paste_url).grid(row=0, column=1, padx=(0,12), pady=10)

        # Options row
        opt = ctk.CTkFrame(f, fg_color=CARD, corner_radius=10)
        opt.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        for i, w in enumerate([1,0,1,0,0,1,0]): opt.columnconfigure(i, weight=w)

        ctk.CTkLabel(opt, text="Quality").grid(row=0, column=0, padx=(14,4), pady=12, sticky="e")
        self._qual = ctk.StringVar(value="best")
        ctk.CTkOptionMenu(opt, variable=self._qual, width=110,
                          values=["best","4k","2160p","1440p","1080p","720p","480p","360p"],
                          button_color=BLUE, fg_color="#0d0d1a").grid(
            row=0, column=1, padx=(0,14), pady=12)

        ctk.CTkLabel(opt, text="Format").grid(row=0, column=2, padx=(0,4), pady=12, sticky="e")
        self._fmt = ctk.StringVar(value="mp4")
        ctk.CTkOptionMenu(opt, variable=self._fmt, width=90,
                          values=["mp4","mkv","webm"],
                          button_color=BLUE, fg_color="#0d0d1a").grid(
            row=0, column=3, padx=(0,14), pady=12)

        self._audio_only = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(opt, text="Audio Only", variable=self._audio_only,
                        checkmark_color=CYAN, border_color=CYAN,
                        command=self._toggle_audio).grid(
            row=0, column=4, padx=(0,14), pady=12)

        ctk.CTkLabel(opt, text="Audio Format").grid(row=0, column=5, padx=(0,4), pady=12, sticky="e")
        self._afmt = ctk.StringVar(value="mp3")
        self._afmt_menu = ctk.CTkOptionMenu(opt, variable=self._afmt, width=90,
                                            values=["mp3","m4a","opus","flac"],
                                            button_color=BLUE, fg_color="#0d0d1a",
                                            state="disabled")
        self._afmt_menu.grid(row=0, column=6, padx=(0,14), pady=12)

        # Output dir row
        dir_card = ctk.CTkFrame(f, fg_color=CARD, corner_radius=10)
        dir_card.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        dir_card.columnconfigure(1, weight=1)
        ctk.CTkLabel(dir_card, text="Save to:").grid(row=0, column=0, padx=(14,8), pady=12)
        self._outdir = ctk.StringVar(
            value=self.cfg.get("download_dir", str(Path.home() / "Downloads")))
        ctk.CTkEntry(dir_card, textvariable=self._outdir, state="readonly",
                     fg_color="#0d0d1a").grid(row=0, column=1, padx=0, pady=12, sticky="ew")
        ctk.CTkButton(dir_card, text="Browse…", width=90,
                      fg_color=BLUE, hover_color="#0d47a1",
                      command=lambda: self._browse(self._outdir)).grid(
            row=0, column=2, padx=(8,14), pady=12)

        # Download button
        self._dl_btn = ctk.CTkButton(
            f, text="⬇   Download", height=50,
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color=BLUE, hover_color="#0d47a1",
            command=self._start_single)
        self._dl_btn.grid(row=4, column=0, sticky="ew", pady=(0, 12))

        # Progress scroll
        ctk.CTkLabel(f, text="Active Downloads",
                     font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=5, column=0, sticky="w", pady=(0, 4))
        self._prog_scroll = ctk.CTkScrollableFrame(f, fg_color="transparent")
        self._prog_scroll.grid(row=6, column=0, sticky="nsew")
        self._prog_scroll.columnconfigure(0, weight=1)
        f.rowconfigure(6, weight=1)
        return f

    # ── Batch Pane ───────────────────────────────────────────────────────────
    def _build_batch_pane(self):
        f = ctk.CTkFrame(self._content, fg_color="transparent")
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)

        ctk.CTkLabel(f, text="Batch / Playlist",
                     font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 12))

        tabs = ctk.CTkTabview(f, fg_color=CARD, segmented_button_fg_color=SIDEBAR,
                              segmented_button_selected_color=BLUE)
        tabs.grid(row=1, column=0, sticky="nsew")
        tabs.columnconfigure(0, weight=1)

        # — Playlist tab
        pl = tabs.add("Playlist URL")
        pl.columnconfigure(0, weight=1)
        self._pl_url = ctk.CTkEntry(pl, placeholder_text="Paste playlist URL…",
                                    height=44, fg_color="#0d0d1a", border_color=CYAN)
        self._pl_url.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(10,8))
        ctk.CTkLabel(pl, text="Parallel:").grid(row=1, column=0, sticky="w", pady=4)
        self._pl_par = ctk.StringVar(value="2")
        ctk.CTkOptionMenu(pl, variable=self._pl_par, width=80,
                          values=["1","2","3","4","5"],
                          button_color=BLUE, fg_color="#0d0d1a").grid(
            row=2, column=0, sticky="w", pady=(0,10))
        ctk.CTkButton(pl, text="⬇  Download Playlist", height=46,
                      font=ctk.CTkFont(size=13, weight="bold"),
                      fg_color=BLUE, hover_color="#0d47a1",
                      command=self._start_playlist).grid(
            row=3, column=0, sticky="ew", pady=8)

        # — Multi-URL tab
        mu = tabs.add("Multiple URLs")
        mu.columnconfigure(0, weight=1)
        mu.rowconfigure(0, weight=1)
        self._batch_text = ctk.CTkTextbox(mu, font=ctk.CTkFont(family="Consolas", size=12),
                                          fg_color="#0d0d1a")
        self._batch_text.grid(row=0, column=0, sticky="nsew", pady=(10,6))
        self._batch_text.insert("0.0", "# One URL per line\n")
        btn_row = ctk.CTkFrame(mu, fg_color="transparent")
        btn_row.grid(row=1, column=0, sticky="ew", pady=6)
        ctk.CTkButton(btn_row, text="📁 Load .txt", width=130,
                      fg_color=SIDEBAR, hover_color="#1a4a7a",
                      command=self._load_txt).pack(side="left", padx=(0,8))
        ctk.CTkButton(btn_row, text="⬇  Download All",
                      fg_color=BLUE, hover_color="#0d47a1",
                      command=self._start_batch).pack(side="right")

        # Batch progress
        ctk.CTkLabel(f, text="Batch Progress",
                     font=ctk.CTkFont(size=13, weight="bold")).grid(
            row=2, column=0, sticky="w", pady=(10, 4))
        self._batch_scroll = ctk.CTkScrollableFrame(f, height=160, fg_color="transparent")
        self._batch_scroll.grid(row=3, column=0, sticky="ew")
        self._batch_scroll.columnconfigure(0, weight=1)
        return f

    # ── Settings Pane ────────────────────────────────────────────────────────
    def _build_settings_pane(self):
        f = ctk.CTkFrame(self._content, fg_color="transparent")
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)

        ctk.CTkLabel(f, text="Settings",
                     font=ctk.CTkFont(size=22, weight="bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 12))

        form = ctk.CTkScrollableFrame(f, fg_color=CARD, corner_radius=10)
        form.grid(row=1, column=0, sticky="nsew")
        form.columnconfigure(1, weight=1)

        def row(r, label, widget):
            ctk.CTkLabel(form, text=label, anchor="w").grid(
                row=r, column=0, padx=(16,20), pady=10, sticky="w")
            widget.grid(row=r, column=1, padx=(0,16), pady=10, sticky="ew")

        # Download folder
        dir_frame = ctk.CTkFrame(form, fg_color="transparent")
        dir_frame.columnconfigure(0, weight=1)
        self._s_dir = ctk.StringVar(
            value=self.cfg.get("download_dir", str(Path.home() / "Downloads")))
        ctk.CTkEntry(dir_frame, textvariable=self._s_dir, state="readonly",
                     fg_color="#0d0d1a").grid(row=0, column=0, sticky="ew", padx=(0,6))
        ctk.CTkButton(dir_frame, text="Browse", width=70,
                      fg_color=BLUE, hover_color="#0d47a1",
                      command=lambda: self._browse(self._s_dir)).grid(row=0, column=1)
        row(0, "Download Folder:", dir_frame)

        self._s_qual = ctk.StringVar(value=self.cfg.get("quality", "best"))
        row(1, "Default Quality:", ctk.CTkOptionMenu(
            form, variable=self._s_qual,
            values=["best","4k","1080p","720p","480p","360p"],
            width=120, button_color=BLUE, fg_color="#0d0d1a"))

        self._s_fmt = ctk.StringVar(value=self.cfg.get("preferred_format", "mp4"))
        row(2, "Default Format:", ctk.CTkOptionMenu(
            form, variable=self._s_fmt,
            values=["mp4","mkv","webm"],
            width=100, button_color=BLUE, fg_color="#0d0d1a"))

        self._s_par = ctk.StringVar(value=str(self.cfg.get("parallel", 2)))
        row(3, "Parallel Downloads:", ctk.CTkOptionMenu(
            form, variable=self._s_par,
            values=["1","2","3","4","5","6","8"],
            width=80, button_color=BLUE, fg_color="#0d0d1a"))

        self._s_meta = ctk.BooleanVar(value=self.cfg.get("embed_metadata", False))
        row(4, "Embed Metadata:", ctk.CTkSwitch(form, text="", variable=self._s_meta,
                                                progress_color=CYAN))

        self._s_thumb = ctk.BooleanVar(value=self.cfg.get("embed_thumbnail", False))
        row(5, "Embed Thumbnail:", ctk.CTkSwitch(form, text="", variable=self._s_thumb,
                                                 progress_color=CYAN))

        ctk.CTkButton(f, text="💾  Save Settings", height=46,
                      font=ctk.CTkFont(size=13, weight="bold"),
                      fg_color=BLUE, hover_color="#0d47a1",
                      command=self._save_settings).grid(
            row=2, column=0, sticky="ew", pady=(10, 0))
        return f

    # ── Navigation ───────────────────────────────────────────────────────────
    def _show(self, name):
        for p in self._panes.values():
            p.grid_forget()
        self._panes[name].grid(row=0, column=0, sticky="nsew")

    # ── Helpers ──────────────────────────────────────────────────────────────
    def _paste_url(self):
        try:
            self._url.delete(0, "end")
            self._url.insert(0, self.clipboard_get())
        except Exception:
            pass

    def _browse(self, var: ctk.StringVar):
        folder = filedialog.askdirectory(initialdir=var.get())
        if folder:
            var.set(folder)

    def _toggle_audio(self):
        self._afmt_menu.configure(
            state="normal" if self._audio_only.get() else "disabled")

    def _load_txt(self):
        p = filedialog.askopenfilename(filetypes=[("Text", "*.txt"), ("All", "*.*")])
        if p:
            with open(p, encoding="utf-8") as fh:
                self._batch_text.delete("0.0", "end")
                self._batch_text.insert("0.0", fh.read())

    def _save_settings(self):
        self.cfg.set("download_dir", self._s_dir.get())
        self.cfg.set("quality",      self._s_qual.get())
        self.cfg.set("preferred_format", self._s_fmt.get())
        self.cfg.set("parallel",     int(self._s_par.get()))
        self.cfg.set("embed_metadata",  self._s_meta.get())
        self.cfg.set("embed_thumbnail", self._s_thumb.get())
        self._outdir.set(self._s_dir.get())
        messagebox.showinfo("Saved", "Settings saved successfully!")

    # ── Progress queue ────────────────────────────────────────────────────────
    def _poll_queue(self):
        try:
            while True:
                job, container = self._ui_queue.get_nowait()
                key = f"{id(container)}:{job.job_id}"
                if key not in self._dl_rows:
                    row = ProgressRow(container, job.title)
                    row.grid(column=0, sticky="ew", pady=3)
                    container.columnconfigure(0, weight=1)
                    self._dl_rows[key] = row
                self._dl_rows[key].update_job(job)
        except queue.Empty:
            pass
        self.after(120, self._poll_queue)

    def _make_callback(self, container):
        def cb(job: DownloadJob):
            self._ui_queue.put((job, container))
        return cb

    # ── Download actions ──────────────────────────────────────────────────────
    def _opts(self):
        return dict(
            quality=self._qual.get(),
            format_pref=self._fmt.get(),
            audio_only=self._audio_only.get(),
            audio_format=self._afmt.get(),
            outdir=self._outdir.get(),
            embed_metadata=self.cfg.get("embed_metadata", False),
            embed_thumbnail=self.cfg.get("embed_thumbnail", False),
        )

    def _start_single(self):
        url = self._url.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please enter a YouTube URL.")
            return
        job = DownloadJob(url)
        cb  = self._make_callback(self._prog_scroll)
        opts = self._opts()
        threading.Thread(
            target=GUIDownloader(on_progress=cb, config_manager=self.cfg).download,
            args=(job,), kwargs=opts, daemon=True
        ).start()

    def _start_playlist(self):
        url = self._pl_url.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please enter a playlist URL.")
            return
        par = int(self._pl_par.get())
        cb  = self._make_callback(self._batch_scroll)
        opts = self._opts()

        def run():
            from streampipe.core.extractor import Extractor
            try:
                info = Extractor().extract_playlist_info(url)
            except Exception as e:
                messagebox.showerror("Error", str(e)); return
            entries = info.get("entries", [])
            jobs = []
            for entry in entries:
                u = entry.get("url") or entry.get("webpage_url")
                if not u and entry.get("id"):
                    u = f"https://www.youtube.com/watch?v={entry['id']}"
                if u:
                    jobs.append(DownloadJob(u))
            GUIDownloader(on_progress=cb, config_manager=self.cfg).download_batch(
                jobs, parallel=par, **opts)

        threading.Thread(target=run, daemon=True).start()

    def _start_batch(self):
        raw = self._batch_text.get("0.0", "end")
        urls = [l.strip() for l in raw.splitlines()
                if l.strip() and not l.strip().startswith("#")]
        if not urls:
            messagebox.showwarning("No URLs", "Add at least one URL.")
            return
        cb   = self._make_callback(self._batch_scroll)
        opts = self._opts()
        jobs = [DownloadJob(u) for u in urls]
        threading.Thread(
            target=GUIDownloader(on_progress=cb, config_manager=self.cfg).download_batch,
            args=(jobs,), kwargs={"parallel": int(self.cfg.get("parallel", 2)), **opts},
            daemon=True
        ).start()


def main():
    app = StreamPipeApp()
    app.mainloop()


if __name__ == "__main__":
    main()
