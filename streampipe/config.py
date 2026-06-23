import os
import yaml
from pathlib import Path

# Constants for Paths
CONFIG_DIR = Path.home() / ".streampipe"
CONFIG_FILE = CONFIG_DIR / "config.yaml"

# Built-in Presets
BUILTIN_PRESETS = {
    "archive-4k": {
        "quality": "2160p",
        "format": "mkv",
        "embed_metadata": True,
        "embed_subs": True,
        "embed_thumbnail": True,
        "subs": "en",
    },
    "quick-audio": {
        "audio_only": True,
        "audio_format": "mp3",
        "bitrate": "320k",
    },
    "mobile-720p": {
        "quality": "720p",
        "format": "mp4",
    }
}

DEFAULT_CONFIG = {
    "download_dir": str(Path.home() / "Downloads"),
    "output_template": "{title} - {resolution}.{ext}",
    "preferred_format": "mp4",
    "quality": "best",
    "parallel": 2,
    "embed_metadata": False,
    "embed_subs": False,
    "embed_thumbnail": False,
    "presets": {}
}

class ConfigManager:
    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self.load_config()

    def load_config(self):
        """Loads configuration from ~/.streampipe/config.yaml or creates it with defaults if not exists."""
        try:
            if not CONFIG_DIR.exists():
                CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            
            if not CONFIG_FILE.exists():
                self.save_config()
                return

            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                if user_config and isinstance(user_config, dict):
                    # Merge user config with defaults
                    for key, val in user_config.items():
                        if key == "presets" and isinstance(val, dict):
                            self.config["presets"].update(val)
                        else:
                            self.config[key] = val
        except Exception:
            # Fallback to default config on errors
            pass

    def save_config(self):
        """Saves current config to disk."""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                yaml.safe_dump(self.config, f, default_flow_style=False)
        except Exception:
            pass

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        """Set a config value and persist to disk."""
        self.config[key] = value
        self.save_config()

    def get_preset(self, name):
        """Resolves a preset by name. Builtin presets take precedence unless overridden in config."""
        preset = BUILTIN_PRESETS.get(name)
        if not preset:
            preset = self.config.get("presets", {}).get(name)
        return preset
