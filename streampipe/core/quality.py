class QualityManager:
    # Standard resolution height mappings
    RESOLUTION_HEIGHTS = {
        "144p": 144,
        "240p": 240,
        "360p": 360,
        "480p": 480,
        "720p": 720,
        "1080p": 1080,
        "1440p": 1440,
        "2k": 1440,
        "2160p": 2160,
        "4k": 2160,
        "4320p": 4320,
        "8k": 4320,
    }

    @staticmethod
    def get_supported_resolutions(formats: list) -> list:
        """Returns sorted list of resolutions actually available in the formats list."""
        available_heights = set()
        for fmt in formats:
            height = fmt.get("height")
            if height and fmt.get("vcodec") != "none":
                available_heights.add(height)
        
        # Match against our standard list
        supported = []
        for label, height in sorted(QualityManager.RESOLUTION_HEIGHTS.items(), key=lambda x: x[1]):
            # Avoid duplicate labels like '2k'/'1440p' in the returned list
            if height in available_heights and label not in ["2k", "4k", "8k"]:
                # We'll represent standard labels
                supported.append((label, height))
        
        # Check if there are heights not in standard mapping, add them
        standard_heights = set(QualityManager.RESOLUTION_HEIGHTS.values())
        for height in sorted(available_heights):
            if height not in standard_heights:
                supported.append((f"{height}p", height))
                
        # Sort by height ascending
        supported.sort(key=lambda x: x[1])
        return [item[0] for item in supported]

    @staticmethod
    def parse_available_streams(formats: list) -> dict:
        """Categorizes formats into clean video resolutions and audio streams."""
        video_streams = {}
        audio_streams = []

        for fmt in formats:
            fmt_id = fmt.get("format_id")
            ext = fmt.get("ext")
            vcodec = fmt.get("vcodec")
            acodec = fmt.get("acodec")
            fps = fmt.get("fps")
            filesize = fmt.get("filesize") or fmt.get("filesize_approx")
            tbr = fmt.get("tbr") # total bitrate in kbps

            # Video only or combined
            if vcodec != "none" and vcodec is not None:
                height = fmt.get("height")
                if height:
                    res_label = f"{height}p"
                    if res_label not in video_streams:
                        video_streams[res_label] = []
                    
                    video_streams[res_label].append({
                        "format_id": fmt_id,
                        "ext": ext,
                        "vcodec": vcodec,
                        "acodec": acodec if acodec != "none" else "None (Mux required)",
                        "fps": fps,
                        "filesize": filesize,
                        "bitrate": tbr,
                    })
            
            # Audio only
            elif acodec != "none" and acodec is not None:
                audio_streams.append({
                    "format_id": fmt_id,
                    "ext": ext,
                    "acodec": acodec,
                    "filesize": filesize,
                    "bitrate": tbr or fmt.get("abr"),
                })
        
        # Sort audio by bitrate descending
        audio_streams.sort(key=lambda x: x.get("bitrate") or 0, reverse=True)
        return {
            "video": video_streams,
            "audio": audio_streams
        }

    @staticmethod
    def resolve_format_selector(quality: str, format_pref: str, audio_only: bool = False) -> str:
        """Constructs yt-dlp format selector based on preferences."""
        if audio_only:
            # We want best audio, or a specific audio format if we are extracting without ffmpeg
            if format_pref in ["m4a", "webm", "aac", "mp3"]:
                return f"bestaudio[ext={format_pref}]/bestaudio"
            return "bestaudio"

        # Determine target height
        height_limit = None
        if quality and quality != "best":
            # Strip 'p' if present and convert to standard height
            q_clean = quality.lower()
            height_limit = QualityManager.RESOLUTION_HEIGHTS.get(q_clean)
            if not height_limit and q_clean.endswith("p"):
                try:
                    height_limit = int(q_clean[:-1])
                except ValueError:
                    pass

        # Build video format selector
        video_selector = "bestvideo"
        if height_limit:
            video_selector += f"[height<={height_limit}]"
        
        if format_pref == "mp4":
            video_selector += "[ext=mp4]"

        # Build audio format selector
        audio_selector = "bestaudio"
        if format_pref == "mp4":
            audio_selector += "[ext=m4a]"

        # Combined string
        if format_pref == "mp4":
            # For MP4 we prefer combining mp4 video + m4a audio, falling back to any mp4 format
            return f"{video_selector}+{audio_selector}/{video_selector}+{bestaudio}/best[ext=mp4]"
        else:
            return f"{video_selector}+{audio_selector}/best"
