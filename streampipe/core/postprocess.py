from streampipe.utils import is_ffmpeg_available

def build_postprocessors_and_options(
    ydl_opts: dict,
    embed_metadata: bool = False,
    embed_subs: bool = False,
    embed_thumbnail: bool = False,
    subs_lang: str = None,
    audio_only: bool = False,
    audio_format: str = "mp3",
    audio_bitrate: str = "192",
) -> None:
    """Configures yt-dlp options and appends appropriate postprocessors based on preferences."""
    
    postprocessors = []

    # Check for FFmpeg availability
    ffmpeg_ok = is_ffmpeg_available()

    # Audio extraction configuration
    if audio_only:
        ydl_opts['format'] = 'bestaudio/best'
        if ffmpeg_ok:
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
                'preferredquality': audio_bitrate.replace('k', ''),
            })
        else:
            # Without ffmpeg, we download best audio as-is
            # yt-dlp format selection will get the best audio file
            pass

    # Subtitles configuration
    if embed_subs or subs_lang:
        langs = [subs_lang] if subs_lang else ['all']
        ydl_opts['writesubtitles'] = True
        ydl_opts['subtitleslangs'] = langs
        ydl_opts['writeautomaticsub'] = True
        
        if embed_subs and ffmpeg_ok:
            ydl_opts['embedsubtitles'] = True
            postprocessors.append({
                'key': 'FFmpegEmbedSubtitle',
                'already_have_subtitle': False,
            })

    # Thumbnail configuration
    if embed_thumbnail:
        ydl_opts['writethumbnail'] = True
        if ffmpeg_ok:
            postprocessors.append({
                'key': 'EmbedThumbnail',
                'already_have_thumbnail': False,
            })

    # Metadata tagging and chapters
    if embed_metadata:
        if ffmpeg_ok:
            postprocessors.append({
                'key': 'FFmpegMetadata',
                'add_chapters': True,
                'add_metadata': True,
            })
        else:
            # Without ffmpeg, we can't embed metadata, but we can write info json if needed
            pass

    # Assign postprocessors to options dictionary if any exist
    if postprocessors:
        if 'postprocessors' not in ydl_opts:
            ydl_opts['postprocessors'] = []
        ydl_opts['postprocessors'].extend(postprocessors)
