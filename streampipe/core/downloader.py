import os
import concurrent.futures
from pathlib import Path
import yt_dlp

from streampipe.core.extractor import Extractor
from streampipe.core.quality import QualityManager
from streampipe.core.postprocess import build_postprocessors_and_options
from streampipe.ui.dashboard import Dashboard
from streampipe.utils import is_ffmpeg_available, translate_template

class Downloader:
    def __init__(self, config_manager):
        self.config = config_manager
        self.extractor = Extractor()

    def download_single(
        self,
        url: str,
        quality: str = None,
        format_pref: str = None,
        audio_only: bool = False,
        audio_format: str = "mp3",
        bitrate: str = "192k",
        embed_metadata: bool = False,
        embed_subs: bool = False,
        embed_thumbnail: bool = False,
        subs_lang: str = None,
        progress = None,
        outdir: str = None
    ) -> bool:
        """Downloads a single video or audio stream with full control options."""
        # Load defaults from config if not specified
        quality = quality or self.config.get("quality", "best")
        format_pref = format_pref or self.config.get("preferred_format", "mp4")
        outdir = outdir or self.config.get("download_dir", str(Path.cwd()))
        
        # Ensure download directory exists
        os.makedirs(outdir, exist_ok=True)

        # Build output path template
        user_template = self.config.get("output_template", "{title} - {resolution}.{ext}")
        translated_template = translate_template(user_template)
        outtmpl = os.path.join(outdir, translated_template)

        # Extract video info
        try:
            info = self.extractor.extract_video_info(url)
        except Exception as e:
            if progress:
                # If running in batch, we don't want to crash the whole queue
                Dashboard.print_error(f"Extraction failed for {url}: {e}")
                return False
            else:
                raise e

        title = info.get("title", "Unknown Title")
        
        # Decide resolution / format
        ffmpeg_ok = is_ffmpeg_available()
        
        # Handle quality fallback if ffmpeg is missing
        if not ffmpeg_ok and not audio_only:
            # Tell the user we are falling back to pre-merged stream if quality request is separate formats
            if quality in ["1080p", "1440p", "2160p", "4k", "8k", "best"]:
                format_selector = "best[vcodec!=none][acodec!=none]/best"
                res_label = "fallback-720p"
            else:
                # E.g. 480p or 360p might have pre-merged streams
                height = QualityManager.RESOLUTION_HEIGHTS.get(quality.lower(), 720)
                format_selector = f"best[height<={height}][vcodec!=none][acodec!=none]/best"
                res_label = f"fallback-{quality}"
        else:
            format_selector = QualityManager.resolve_format_selector(quality, format_pref, audio_only)
            res_label = quality if not audio_only else "audio"

        ydl_opts = {
            'format': format_selector,
            'outtmpl': outtmpl,
            'quiet': True,
            'no_warnings': True,
            'noprogress': True,
            'merge_output_format': format_pref if ffmpeg_ok and not audio_only else None,
        }

        # Build postprocessors (subtitles, metadata, thumbnails, audio transcodes)
        build_postprocessors_and_options(
            ydl_opts=ydl_opts,
            embed_metadata=embed_metadata,
            embed_subs=embed_subs,
            embed_thumbnail=embed_thumbnail,
            subs_lang=subs_lang,
            audio_only=audio_only,
            audio_format=audio_format,
            audio_bitrate=bitrate
        )

        # Manage progress bar context
        local_progress = False
        if progress is None:
            progress = Dashboard.create_progress_bar()
            progress.start()
            local_progress = True

        task_id = progress.add_task(
            description=title,
            title=title[:30] + "..." if len(title) > 30 else title,
            res=res_label,
            status="Starting",
            total=None
        )

        def make_progress_hook(p_bar, t_id):
            def hook(d):
                if d['status'] == 'downloading':
                    completed = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                    speed = d.get('speed')
                    p_bar.update(
                        t_id,
                        completed=completed,
                        total=total,
                        speed=speed,
                        status="Downloading"
                    )
                elif d['status'] == 'finished':
                    p_bar.update(
                        t_id,
                        completed=d.get('total_bytes', 0) or d.get('downloaded_bytes', 0),
                        status="Muxing..." if ffmpeg_ok else "Finished"
                    )
            return hook

        ydl_opts['progress_hooks'] = [make_progress_hook(progress, task_id)]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            progress.update(task_id, status="Done")
            success = True
        except Exception as e:
            progress.update(task_id, status="Failed")
            if not local_progress:
                Dashboard.print_error(f"Download failed for '{title}': {e}")
            success = False
        finally:
            if local_progress:
                progress.stop()

        return success

    def download_batch(
        self,
        urls: list,
        parallel: int = 1,
        quality: str = None,
        format_pref: str = None,
        audio_only: bool = False,
        audio_format: str = "mp3",
        bitrate: str = "192k",
        embed_metadata: bool = False,
        embed_subs: bool = False,
        embed_thumbnail: bool = False,
        subs_lang: str = None,
        outdir: str = None
    ) -> bool:
        """Downloads multiple URLs in parallel using a thread pool."""
        parallel = parallel or self.config.get("parallel", 1)
        progress = Dashboard.create_progress_bar()
        
        Dashboard.print_info(f"Starting batch download of {len(urls)} URLs (Parallel count: {parallel})")
        
        progress.start()
        success_count = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as executor:
            # Submit all download tasks
            futures = {
                executor.submit(
                    self.download_single,
                    url=url,
                    quality=quality,
                    format_pref=format_pref,
                    audio_only=audio_only,
                    audio_format=audio_format,
                    bitrate=bitrate,
                    embed_metadata=embed_metadata,
                    embed_subs=embed_subs,
                    embed_thumbnail=embed_thumbnail,
                    subs_lang=subs_lang,
                    progress=progress,
                    outdir=outdir
                ): url for url in urls
            }

            for future in concurrent.futures.as_completed(futures):
                try:
                    if future.result():
                        success_count += 1
                except Exception as e:
                    url = futures[future]
                    Dashboard.print_error(f"Thread execution error for {url}: {e}")

        progress.stop()
        Dashboard.print_success(f"Batch completed: {success_count}/{len(urls)} downloaded successfully.")
        return success_count == len(urls)

    def download_playlist(
        self,
        playlist_url: str,
        parallel: int = 1,
        quality: str = None,
        format_pref: str = None,
        audio_only: bool = False,
        audio_format: str = "mp3",
        bitrate: str = "192k",
        embed_metadata: bool = False,
        embed_subs: bool = False,
        embed_thumbnail: bool = False,
        subs_lang: str = None,
        outdir: str = None
    ) -> bool:
        """Extracts entries from a playlist and schedules them for batch downloading."""
        Dashboard.print_info(f"Extracting playlist information...")
        try:
            playlist_info = self.extractor.extract_playlist_info(playlist_url)
        except Exception as e:
            Dashboard.print_error(f"Failed to load playlist: {e}")
            return False

        entries = playlist_info.get("entries", [])
        if not entries:
            Dashboard.print_error("No videos found in this playlist.")
            return False

        # Gather urls from entries (filter out None or empty)
        urls = []
        for entry in entries:
            if entry:
                # Some extractors return 'url' directly, others might require video id assembly
                url = entry.get("url") or entry.get("webpage_url")
                if not url and entry.get("id"):
                    url = f"https://www.youtube.com/watch?v={entry['id']}"
                if url:
                    urls.append(url)

        if not urls:
            Dashboard.print_error("Failed to parse individual video URLs from playlist.")
            return False

        Dashboard.print_success(f"Found {len(urls)} videos in playlist: '{playlist_info.get('title', 'Untitled')}'")
        return self.download_batch(
            urls=urls,
            parallel=parallel,
            quality=quality,
            format_pref=format_pref,
            audio_only=audio_only,
            audio_format=audio_format,
            bitrate=bitrate,
            embed_metadata=embed_metadata,
            embed_subs=embed_subs,
            embed_thumbnail=embed_thumbnail,
            subs_lang=subs_lang,
            outdir=outdir
        )
