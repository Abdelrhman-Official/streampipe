# StreamPipe User Guide 🎬⚡
### The Advanced Terminal-Based YouTube Downloader

StreamPipe is a command-line tool designed to give you precise control over your media downloads. This guide covers how to set up, use, and customize StreamPipe.

---

## 🚀 1. Getting Started

Before using StreamPipe, activate the virtual environment in your terminal:

```powershell
# Activate in PowerShell
.venv\Scripts\Activate.ps1
```

Once active, you can call `streampipe` directly:
```powershell
streampipe --help
```

---

## 📖 2. Basic Download Commands

### Download a Video (Default Best Quality)
Saves the video at the highest quality available:
```powershell
streampipe "https://www.youtube.com/watch?v=aqz-KE-bpKQ"
```

### Specifying Output Directory
Use `-o` to save the download to a specific folder (defaults to your Windows `Downloads` folder):
```powershell
streampipe "https://www.youtube.com/watch?v=aqz-KE-bpKQ" -o "D:\MyVideos"
```

---

## 🎛️ 3. Advanced Features

### List Available Qualities & Codecs
Inspect all available stream combinations before downloading:
```powershell
streampipe "https://www.youtube.com/watch?v=aqz-KE-bpKQ" --list-qualities
```

### Select Video Quality & Format
Choose target resolution (`4k`, `1080p`, `720p`, etc.) and container (`mp4`, `mkv`, `webm`):
```powershell
streampipe "https://www.youtube.com/watch?v=aqz-KE-bpKQ" --quality 1080p --format mp4
```

### Extract Audio-Only
Download sound tracks in formats like `mp3`, `m4a`, `opus`, or `flac`, with custom bitrates:
```powershell
streampipe "https://www.youtube.com/watch?v=aqz-KE-bpKQ" --audio-only --audio-format mp3 --bitrate 320k
```

---

## 🗂️ 4. Batch & Playlists

### Playlist Download
To download all videos in a playlist (downloads in parallel where supported):
```powershell
streampipe "https://www.youtube.com/playlist?list=PL..." --playlist --parallel 3
```

### Batch Download from a File
1. Create a text file (e.g. `urls.txt`) containing one URL per line:
   ```text
   https://www.youtube.com/watch?v=ID1
   https://www.youtube.com/watch?v=ID2
   ```
2. Run the batch command specifying the parallel threads:
   ```powershell
   streampipe --batch urls.txt --parallel 4
   ```

---

## ⚙️ 5. Presets & Configuration

StreamPipe stores its configuration in `~/.streampipe/config.yaml` (usually in `C:\Users\<YourUsername>\.streampipe\config.yaml`). You can set your default download directories, parallel limits, and custom presets there.

### Built-in Presets
You can apply pre-defined profiles using the `--preset` flag:

* **`archive-4k`**: Targets 4K, downloads in MKV container, embeds subtitles, thumbnail, and metadata.
  ```powershell
  streampipe "URL" --preset archive-4k
  ```
* **`quick-audio`**: Downloads audio-only, encodes to 320k MP3.
  ```powershell
  streampipe "URL" --preset quick-audio
  ```
* **`mobile-720p`**: Capped at 720p MP4 format.
  ```powershell
  streampipe "URL" --preset mobile-720p
  ```

---

## ⚙️ 6. FFmpeg Integration

To merge high-quality video and audio streams (1080p+ resolutions), encode MP3s, or embed subtitles/metadata, **FFmpeg** must be installed on your system.

### Installing FFmpeg on Windows:
Open PowerShell as Administrator and run:
```powershell
winget install Gyan.FFmpeg
```
*Note: Restart your terminal after installation for the changes to take effect.*

If FFmpeg is not installed, StreamPipe automatically switches to **Fallback Mode** (capping downloads at 720p/360p pre-merged formats) so that your downloads still complete successfully.
