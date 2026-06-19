# StreamPipe 🎬⚡
### The Advanced Terminal-Based YouTube Downloader

> "Not just another downloader — full control, every time."

---

## 1. Vision

Most YouTube downloaders give you one button: "Download." **StreamPipe** is different — it puts you in the driver's seat. You choose the **exact format**, the **exact quality** (from 144p all the way to 4K, scaled automatically to whatever the source video actually supports), audio codec, subtitles, and post-processing — all from a clean, fast terminal interface.

StreamPipe is built to be the **most controllable, most transparent, and most powerful** CLI downloader available — for personal archiving, offline viewing, and fair-use research purposes.

---

## 2. What Makes StreamPipe Different

| Other tools | StreamPipe |
|---|---|
| Pick "best" and hope | Interactive quality/format picker showing every available stream |
| One-size-fits-all output | Per-video adaptive quality list (only shows what's *actually* available — no fake 4K on a 480p source) |
| Plain text logs | Live terminal dashboard (progress bars, speed, ETA, per-file status) |
| Single download at a time | Parallel/batch queue with resume support |
| No format intelligence | Smart merging of separate video+audio streams via ffmpeg, auto codec matching |
| Static config | Profiles & presets (e.g. "Archive-4K", "Quick-Audio", "Mobile-720p") |

---

## 3. Core Features

### 🎚️ Format & Quality Control
- Full resolution ladder: `144p, 240p, 360p, 480p, 720p, 1080p, 1440p (2K), 2160p (4K)` — and beyond if the source provides it (8K-ready architecture).
- Auto-detects which qualities actually exist for the given video/playlist (no guessing).
- `--list-qualities` flag to preview all available streams before downloading.
- Choose container/format: `mp4`, `mkv`, `webm`.
- Choose video codec: `h264`, `vp9`, `av1` (when available).

### 🔊 Audio Control
- Audio-only extraction: `mp3`, `m4a`, `opus`, `flac`.
- Select audio bitrate (e.g. 128k / 192k / 320k).
- Keep original audio track or re-encode.

### 📦 Batch & Playlist Support
- Download full playlists or channels.
- Queue multiple URLs from a `.txt` file.
- Parallel downloads with configurable thread/connection count.
- Resume interrupted downloads automatically.

### 📝 Extras
- Subtitle download & embedding (auto + manual languages).
- Thumbnail download & embedding into file metadata.
- Metadata tagging (title, uploader, upload date, chapters).
- Chapter markers preserved in output file.
- Rate limiting & proxy support for controlled bandwidth usage.

### 🖥️ Terminal Experience
- Live progress bars (speed, ETA, % complete) per file.
- Color-coded status (queued / downloading / merging / done / failed).
- Quiet mode for scripting, verbose mode for debugging.
- JSON output mode for piping into other tools/scripts.

### ⚙️ Configuration
- Global config file (`~/.streampipe/config.yaml`) for defaults (preferred format, output folder, naming pattern).
- Custom output filename templates, e.g. `{title}-{resolution}.{ext}`.
- Saved presets/profiles for repeated use cases.

---

## 4. Example CLI Usage

```bash
# Basic download with explicit quality + format
streampipe "<url>" --quality 1080p --format mp4

# See exactly what qualities/formats are available first
streampipe "<url>" --list-qualities

# Audio-only extraction
streampipe "<url>" --audio-only --format mp3 --bitrate 320k

# 4K with subtitles embedded
streampipe "<url>" --quality 4k --subs en --embed-subs

# Download an entire playlist at the best quality each video supports
streampipe --playlist "<url>" --quality best

# Batch download from a list file, 4 parallel downloads
streampipe --batch urls.txt --parallel 4

# Use a saved preset
streampipe "<url>" --preset archive-4k
```

---

## 5. Proposed Architecture

```
streampipe/
├── streampipe/
│   ├── cli.py              # Argument parsing & command routing
│   ├── core/
│   │   ├── extractor.py    # Resolves video info & available streams
│   │   ├── quality.py      # Builds the resolution/format ladder per video
│   │   ├── downloader.py   # Multi-threaded download engine + resume logic
│   │   └── postprocess.py  # ffmpeg muxing, metadata, subtitles, thumbnails
│   ├── ui/
│   │   └── dashboard.py    # Live terminal progress UI
│   ├── config.py           # Profiles, presets, defaults
│   └── utils.py
├── tests/
├── README.md
└── pyproject.toml
```

**Suggested stack:**
- **Language:** Python (fast to build, great ecosystem) — or Rust/Go later for a single-binary, zero-dependency distribution.
- **Extraction backend:** built on top of a mature open-source extraction library (e.g. `yt-dlp`) so StreamPipe doesn't need to reverse-engineer YouTube's API itself — instead it focuses on UX, control, and the smart layer on top.
- **Post-processing:** `ffmpeg` for merging video/audio streams, transcoding, and embedding metadata/subtitles/thumbnails.
- **CLI framework:** `typer` or `click`.
- **Terminal UI:** `rich` or `textual` for live progress dashboards.

---

## 6. Roadmap

- **Phase 1 — MVP:** single-video download, quality + format selection, basic progress bar.
- **Phase 2 — Batch Engine:** playlists, batch files, parallel downloads, resume support.
- **Phase 3 — Polish:** subtitles, thumbnails, metadata embedding, filename templates.
- **Phase 4 — Power Features:** presets/profiles, proxy & rate limiting, JSON/scripting mode.
- **Phase 5 — Pro UI:** full live terminal dashboard (multi-file view), plugin system for other platforms.

---

## 7. Notes on Responsible Use

StreamPipe is intended for **personal use, offline viewing, and content you have the right to download** (your own uploads, Creative Commons content, or platform-permitted downloads). Always respect copyright and the terms of service of the platform you're downloading from.

---

*This file is a living spec — update it as features are added or design decisions change.*
