import os
import sys
import click

from streampipe import __version__
from streampipe.config import ConfigManager
from streampipe.core.downloader import Downloader
from streampipe.core.extractor import Extractor
from streampipe.core.quality import QualityManager
from streampipe.ui.dashboard import Dashboard
from streampipe.utils import is_ffmpeg_available, get_ffmpeg_version

# Reconfigure stdout/stderr to use UTF-8 on Windows to prevent UnicodeEncodeError with emojis/non-ascii
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.argument('url', required=False)
@click.option('--list-qualities', is_flag=True, help="List all available resolutions & audio streams.")
@click.option('-q', '--quality', help="Target quality (e.g. 1080p, 720p, 4k, best).")
@click.option('-f', '--format', 'format_pref', help="Preferred container format (mp4, mkv, webm).")
@click.option('-x', '--audio-only', is_flag=True, help="Download/extract audio only.")
@click.option('--audio-format', default="mp3", help="Audio output format (mp3, m4a, opus, flac).")
@click.option('--bitrate', default="192k", help="Audio bitrate (e.g. 128k, 256k, 320k).")
@click.option('--playlist', is_flag=True, help="Force downloading as a playlist.")
@click.option('--batch', type=click.Path(exists=True, file_okay=True, dir_okay=False, readable=True), help="Path to a text file containing URLs to download.")
@click.option('-p', '--parallel', type=int, help="Number of concurrent batch downloads.")
@click.option('--preset', help="Use a saved config preset.")
@click.option('--subs', help="Subtitle language code (e.g., en, es).")
@click.option('--embed-subs', is_flag=True, help="Embed subtitles in the downloaded video file (requires FFmpeg).")
@click.option('--embed-thumbnail', is_flag=True, help="Embed thumbnail in the downloaded file (requires FFmpeg).")
@click.option('--embed-metadata', is_flag=True, help="Embed uploader and description metadata (requires FFmpeg).")
@click.option('-o', '--outdir', help="Directory to save downloaded files.")
@click.option('--version', is_flag=True, help="Show the version and system diagnostic info.")
@click.pass_context
def main(
    ctx,
    url,
    list_qualities,
    quality,
    format_pref,
    audio_only,
    audio_format,
    bitrate,
    playlist,
    batch,
    parallel,
    preset,
    subs,
    embed_subs,
    embed_thumbnail,
    embed_metadata,
    outdir,
    version
):
    """StreamPipe: The Advanced Terminal-Based YouTube Downloader"""
    Dashboard.show_header()

    # If version requested, print diagnostics and exit
    if version:
        ffmpeg_status = "Available" if is_ffmpeg_available() else "NOT Available"
        ffmpeg_ver = get_ffmpeg_version()
        click.echo(f"StreamPipe version: {__version__}")
        click.echo(f"FFmpeg Status: {ffmpeg_status} ({ffmpeg_ver})")
        click.echo(f"Python version: {sys.version.split()[0]}")
        return

    # Ensure we have a URL or a batch file to process
    if not url and not batch:
        click.echo(ctx.get_help())
        return

    config_manager = ConfigManager()
    
    # Initialize values
    opts = {
        "quality": quality,
        "format_pref": format_pref,
        "audio_only": audio_only,
        "audio_format": audio_format,
        "bitrate": bitrate,
        "embed_subs": embed_subs,
        "embed_thumbnail": embed_thumbnail,
        "embed_metadata": embed_metadata,
        "subs_lang": subs,
        "parallel": parallel,
        "outdir": outdir
    }

    # Resolve presets if supplied
    if preset:
        preset_config = config_manager.get_preset(preset)
        if not preset_config:
            Dashboard.print_error(f"Preset '{preset}' not found in configuration or built-in presets.")
            sys.exit(1)
        
        Dashboard.print_info(f"Applying preset '{preset}': {preset_config}")
        
        # Preset key mappings to options keys
        key_mappings = {
            "quality": "quality",
            "format": "format_pref",
            "audio_only": "audio_only",
            "audio_format": "audio_format",
            "bitrate": "bitrate",
            "embed_subs": "embed_subs",
            "embed_thumbnail": "embed_thumbnail",
            "embed_metadata": "embed_metadata",
            "subs": "subs_lang",
            "parallel": "parallel",
            "outdir": "outdir"
        }
        
        # Apply preset, letting explicitly passed CLI flags override preset values
        for p_key, opt_key in key_mappings.items():
            if p_key in preset_config and ctx.get_parameter_source(opt_key) == click.core.ParameterSource.DEFAULT:
                opts[opt_key] = preset_config[p_key]

    # Warm warnings if ffmpeg is missing and requested features require it
    if not is_ffmpeg_available():
        requires_ffmpeg = (
            opts["embed_subs"] or 
            opts["embed_thumbnail"] or 
            opts["embed_metadata"] or 
            (opts["audio_only"] and opts["audio_format"] not in ["m4a", "webm"]) or
            (opts["quality"] not in [None, "360p", "720p"] and not opts["audio_only"])
        )
        if requires_ffmpeg:
            Dashboard.print_warning(
                "FFmpeg is not installed on this system.\n"
                "Merging streams, transcoding audio formats, and embedding thumbnails/metadata/subtitles "
                "require FFmpeg to function correctly.\n"
                "Downloads will run in fallback mode (capped at 720p pre-merged video/original audio format).\n"
                "To install FFmpeg on Windows, run:\n"
                "  winget install Gyan.FFmpeg\n"
            )

    # Action 1: List qualities
    if list_qualities:
        if not url:
            Dashboard.print_error("A URL is required to list available qualities.")
            sys.exit(1)
        
        Dashboard.print_info(f"Extracting streams for: {url}")
        try:
            extractor = Extractor()
            info = extractor.extract_video_info(url)
            streams = QualityManager.parse_available_streams(info.get("formats", []))
            Dashboard.list_qualities(
                video_title=info.get("title", "Unknown Video"),
                duration=info.get("duration", 0),
                streams=streams
            )
        except Exception as e:
            Dashboard.print_error(f"Failed to list qualities: {e}")
            sys.exit(1)
        return

    # Action 2: Process batch
    downloader = Downloader(config_manager)
    if batch:
        urls = []
        try:
            with open(batch, 'r', encoding='utf-8') as f:
                urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        except Exception as e:
            Dashboard.print_error(f"Failed to read batch file: {e}")
            sys.exit(1)

        if not urls:
            Dashboard.print_warning("Batch file is empty.")
            return

        downloader.download_batch(
            urls=urls,
            parallel=opts["parallel"],
            quality=opts["quality"],
            format_pref=opts["format_pref"],
            audio_only=opts["audio_only"],
            audio_format=opts["audio_format"],
            bitrate=opts["bitrate"],
            embed_metadata=opts["embed_metadata"],
            embed_subs=opts["embed_subs"],
            embed_thumbnail=opts["embed_thumbnail"],
            subs_lang=opts["subs_lang"],
            outdir=opts["outdir"]
        )
        return

    # Action 3: Process single URL (Playlist or Single Video)
    if playlist:
        downloader.download_playlist(
            playlist_url=url,
            parallel=opts["parallel"] or 1,
            quality=opts["quality"],
            format_pref=opts["format_pref"],
            audio_only=opts["audio_only"],
            audio_format=opts["audio_format"],
            bitrate=opts["bitrate"],
            embed_metadata=opts["embed_metadata"],
            embed_subs=opts["embed_subs"],
            embed_thumbnail=opts["embed_thumbnail"],
            subs_lang=opts["subs_lang"],
            outdir=opts["outdir"]
        )
    else:
        # Detect if it's a playlist URL but `--playlist` wasn't set, warn or prompt?
        # yt-dlp usually handles it. If playlist, we download it as a playlist.
        # We can perform a quick extraction check or let downloader handle it
        downloader.download_single(
            url=url,
            quality=opts["quality"],
            format_pref=opts["format_pref"],
            audio_only=opts["audio_only"],
            audio_format=opts["audio_format"],
            bitrate=opts["bitrate"],
            embed_metadata=opts["embed_metadata"],
            embed_subs=opts["embed_subs"],
            embed_thumbnail=opts["embed_thumbnail"],
            subs_lang=opts["subs_lang"],
            outdir=opts["outdir"]
        )

if __name__ == '__main__':
    main()
