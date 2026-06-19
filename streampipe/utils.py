import shutil
import subprocess

def is_ffmpeg_available() -> bool:
    """Checks if ffmpeg executable is available in system path."""
    return shutil.which("ffmpeg") is not None

def get_ffmpeg_version() -> str:
    """Runs ffmpeg -version to get version info."""
    if not is_ffmpeg_available():
        return "Not Installed"
    try:
        res = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True)
        # First line contains version
        first_line = res.stdout.splitlines()[0]
        return first_line.split("version")[1].strip().split()[0]
    except Exception:
        return "Unknown Version"

def format_size(bytes_size) -> str:
    """Formats bytes size to a readable string."""
    if bytes_size is None:
        return "Unknown Size"
    try:
        bytes_size = float(bytes_size)
    except (ValueError, TypeError):
        return "Unknown Size"
    
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def format_speed(bytes_per_sec) -> str:
    """Formats speed in bytes per second to readable string."""
    if bytes_per_sec is None:
        return "0.00 B/s"
    try:
        bytes_per_sec = float(bytes_per_sec)
    except (ValueError, TypeError):
        return "0.00 B/s"
    
    for unit in ['B/s', 'KB/s', 'MB/s', 'GB/s']:
        if bytes_per_sec < 1024.0:
            return f"{bytes_per_sec:.2f} {unit}"
        bytes_per_sec /= 1024.0
    return f"{bytes_per_sec:.2f} PB/s"

def translate_template(template: str) -> str:
    """Translates user-friendly {token} format to yt-dlp's %(token)s format."""
    mappings = {
        "{title}": "%(title)s",
        "{resolution}": "%(resolution)s",
        "{ext}": "%(ext)s",
        "{uploader}": "%(uploader)s",
        "{id}": "%(id)s",
        "{playlist}": "%(playlist)s",
        "{playlist_index}": "%(playlist_index)s",
        "{upload_date}": "%(upload_date)s",
    }
    res = template
    for key, val in mappings.items():
        res = res.replace(key, val)
    return res
