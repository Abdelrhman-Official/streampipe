import yt_dlp

class Extractor:
    def __init__(self):
        pass

    def extract_video_info(self, url: str) -> dict:
        """Extracts metadata from a single YouTube video URL without downloading."""
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': False,
            'extract_flat': False,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise RuntimeError("No info returned from yt-dlp")
                
                # If it's a playlist representation, it might contain entries
                if 'entries' in info:
                    # It's actually a playlist URL or channel, return the first video or raise
                    entries = list(info['entries'])
                    if not entries:
                        raise RuntimeError("Playlist is empty")
                    # If we wanted video info but got playlist, we'll return the playlist wrapper info
                    # indicating it is a playlist
                return info
            except Exception as e:
                raise RuntimeError(f"Failed to extract video info: {str(e)}")

    def extract_playlist_info(self, url: str) -> dict:
        """Extracts list of entries from a playlist or channel URL without downloading individual video formats."""
        ydl_opts = {
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'extract_flat': 'in_playlist',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise RuntimeError("No playlist info returned from yt-dlp")
                
                if 'entries' not in info:
                    # URL might be a single video, wrap it in playlist structure
                    return {
                        'title': info.get('title', 'Single Video'),
                        'entries': [info],
                        '_type': 'playlist'
                    }
                return info
            except Exception as e:
                raise RuntimeError(f"Failed to extract playlist info: {str(e)}")
