"""
core_bridge.py — GUI-friendly wrapper around the StreamPipe download engine.

Replaces rich.Progress callbacks with plain Python callables so both the
Windows (CustomTkinter) and mobile (Kivy) apps can drive downloads without
any terminal dependencies.
"""
import os
import threading
import concurrent.futures
from pathlib import Path

import yt_dlp

from streampipe.config import ConfigManager
from streampipe.core.extractor import Extractor
from streampipe.core.quality import QualityManager
from streampipe.core.postprocess import build_postprocessors_and_options
from streampipe.utils import is_ffmpeg_available, translate_template


class DownloadJob:
    """Represents a single download task with observable state."""

    def __init__(self, url: str, job_id: str = None):
        self.url = url
        self.job_id = job_id or url
        self.title = "Fetching info..."
        self.progress = 0.0        # 0.0 – 1.0
        self.speed = 0.0           # bytes/s
        self.downloaded = 0        # bytes
        self.total = 0             # bytes
        self.status = "pending"    # pending | downloading | muxing | done | error
        self.error: str = None
        self._cancel_event = threading.Event()

    def cancel(self):
        self._cancel_event.set()

    @property
    def cancelled(self):
        return self._cancel_event.is_set()


class GUIDownloader:
    """
    Callback-driven downloader for GUI frontends.

    Parameters
    ----------
    on_progress : callable(job: DownloadJob)
        Called on every yt-dlp progress tick and status change.
        May be called from a background thread — callers must marshal
        to their own UI thread if required.
    config_manager : ConfigManager | None
        Pass an existing ConfigManager or one will be created.
    """

    def __init__(self, on_progress=None, config_manager: ConfigManager = None):
        self.on_progress = on_progress or (lambda job: None)
        self.config = config_manager or ConfigManager()
        self.extractor = Extractor()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def download(self, job: DownloadJob, **opts) -> bool:
        """
        Download a single URL described by *job*.

        Extra keyword arguments override config defaults:
            quality, format_pref, audio_only, audio_format, bitrate,
            embed_metadata, embed_subs, embed_thumbnail, subs_lang, outdir
        """
        quality      = opts.get("quality") or self.config.get("quality", "best")
        format_pref  = opts.get("format_pref") or self.config.get("preferred_format", "mp4")
        audio_only   = opts.get("audio_only", False)
        audio_format = opts.get("audio_format", "mp3")
        bitrate      = opts.get("bitrate", "192k")
        embed_meta   = opts.get("embed_metadata", False)
        embed_subs   = opts.get("embed_subs", False)
        embed_thumb  = opts.get("embed_thumbnail", False)
        subs_lang    = opts.get("subs_lang")
        outdir       = opts.get("outdir") or self.config.get("download_dir", str(Path.home() / "Downloads"))

        os.makedirs(outdir, exist_ok=True)

        # --- resolve output template ---
        user_tmpl   = self.config.get("output_template", "{title} - {resolution}.{ext}")
        outtmpl     = os.path.join(outdir, translate_template(user_tmpl))

        # --- fetch video metadata ---
        job.status = "fetching"
        self.on_progress(job)
        try:
            info = self.extractor.extract_video_info(job.url)
        except Exception as exc:
            job.status = "error"
            job.error = str(exc)
            self.on_progress(job)
            return False

        job.title = info.get("title", job.url)
        self.on_progress(job)

        # --- build format selector ---
        ffmpeg_ok = is_ffmpeg_available()
        if not ffmpeg_ok and not audio_only:
            if quality in ["1080p", "1440p", "2160p", "4k", "8k", "best"]:
                fmt_sel = "best[vcodec!=none][acodec!=none]/best"
            else:
                h = QualityManager.RESOLUTION_HEIGHTS.get(quality.lower(), 720)
                fmt_sel = f"best[height<={h}][vcodec!=none][acodec!=none]/best"
        else:
            fmt_sel = QualityManager.resolve_format_selector(quality, format_pref, audio_only)

        ydl_opts = {
            "format": fmt_sel,
            "outtmpl": outtmpl,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "merge_output_format": format_pref if ffmpeg_ok and not audio_only else None,
        }

        build_postprocessors_and_options(
            ydl_opts=ydl_opts,
            embed_metadata=embed_meta,
            embed_subs=embed_subs,
            embed_thumbnail=embed_thumb,
            subs_lang=subs_lang,
            audio_only=audio_only,
            audio_format=audio_format,
            audio_bitrate=bitrate,
        )

        def _hook(d):
            if job.cancelled:
                raise yt_dlp.utils.DownloadError("Cancelled by user")
            if d["status"] == "downloading":
                job.downloaded = d.get("downloaded_bytes", 0)
                job.total      = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                job.speed      = d.get("speed") or 0.0
                job.progress   = (job.downloaded / job.total) if job.total else 0.0
                job.status     = "downloading"
                self.on_progress(job)
            elif d["status"] == "finished":
                job.progress = 1.0
                job.status   = "muxing" if ffmpeg_ok else "done"
                self.on_progress(job)

        ydl_opts["progress_hooks"] = [_hook]

        job.status = "downloading"
        self.on_progress(job)
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([job.url])
            job.status   = "done"
            job.progress = 1.0
        except Exception as exc:
            if job.cancelled:
                job.status = "cancelled"
            else:
                job.status = "error"
                job.error  = str(exc)
        finally:
            self.on_progress(job)

        return job.status == "done"

    def download_batch(self, jobs: list, parallel: int = 2, **opts) -> int:
        """
        Download a list of DownloadJob objects in parallel.
        Returns the number of successful downloads.
        """
        success = 0
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, parallel)) as ex:
            futures = {ex.submit(self.download, job, **opts): job for job in jobs}
            for fut in concurrent.futures.as_completed(futures):
                try:
                    if fut.result():
                        success += 1
                except Exception:
                    pass
        return success

    def fetch_qualities(self, url: str) -> dict:
        """Returns parsed stream info dict or raises on failure."""
        info = self.extractor.extract_video_info(url)
        return {
            "title":    info.get("title", "Unknown"),
            "duration": info.get("duration", 0),
            "streams":  QualityManager.parse_available_streams(info.get("formats", [])),
        }
