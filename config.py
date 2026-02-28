"""Configuration and directory paths for SP Workshop."""

import json
import os
from pathlib import Path
from typing import Dict, Optional


def get_config_path() -> Path:
    """Get the path to the configuration file."""
    base_dir = Path.home() / "VideoProcessing"
    config_dir = base_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "settings.json"


def load_config() -> Dict:
    """Load configuration from JSON file."""
    config_path = get_config_path()
    default_config = {
        "base_dir": str(Path.home() / "VideoProcessing"),
        "watermark_720p": str(Path.home() / "VideoProcessing" / "config" / "watermark_720p.png"),
        "watermark_1080p": str(Path.home() / "VideoProcessing" / "config" / "watermark_1080p.png"),
        "api_key": os.getenv("GST_API_KEY", ""),
        "download_resolution": "1080",
        "ffmpeg_preset": "medium",
        "ffmpeg_path": "",
        "setup_complete": False,
        "use_watermarks": True,
        "whisper_output_format": "srt",
        "use_iso639_suffixes": False,
        "whisper_options": {
            "extra_args": "",
            "extra_args_parsed": ""
        }
    }

    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                if "whisper_options" in user_config:
                    default_config["whisper_options"].update(user_config["whisper_options"])
                    del user_config["whisper_options"]
                default_config.update(user_config)
        except Exception as e:
            print(f"Error loading config: {e}")

    return default_config


def save_config(config: Dict) -> None:
    """Save configuration to JSON file."""
    config_path = get_config_path()
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")


def get_base_dir() -> Path:
    """Get the base VideoProcessing directory."""
    base_dir = Path.home() / "VideoProcessing"
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


def get_downloads_dir() -> Path:
    """Get the downloads directory."""
    downloads_dir = get_base_dir() / "downloads"
    downloads_dir.mkdir(parents=True, exist_ok=True)
    return downloads_dir


def get_subtitles_dir() -> Path:
    """Get the subtitles directory."""
    subtitles_dir = get_base_dir() / "subtitles"
    subtitles_dir.mkdir(parents=True, exist_ok=True)
    return subtitles_dir


def get_output_dir() -> Path:
    """Get the output directory."""
    output_dir = get_base_dir() / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_remuxed_dir() -> Path:
    """Get the remuxed directory."""
    remuxed_dir = get_base_dir() / "remuxed"
    remuxed_dir.mkdir(parents=True, exist_ok=True)
    return remuxed_dir


def get_matching_subtitle_for_remux(video_path: Path) -> Optional[Path]:
    """Find an SRT or VTT file with the same stem as the video (for remux auto-match)."""
    if not video_path.exists():
        return None
    stem = video_path.stem
    for ext in (".srt", ".vtt"):
        candidate = video_path.parent / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    sub_dir = get_subtitles_dir()
    for ext in (".srt", ".vtt"):
        candidate = sub_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def check_whisper_model_exists(model_name: str) -> bool:
    """Check if a Whisper model already exists in the default cache location."""
    import platform
    system = platform.system()
    cache_dir = Path.home() / ".cache" / "whisper"
    model_files = {
        "tiny": "tiny.pt", "base": "base.pt", "small": "small.pt",
        "medium": "medium.pt", "large": "large-v2.pt", "turbo": "turbo.pt"
    }
    model_file = model_files.get(model_name.lower())
    if not model_file:
        return False
    return (cache_dir / model_file).exists()


# ISO 639-2/T language codes for subtitle suffixes
ISO_639_CODES = {
    "English": "eng", "French": "fra", "Spanish": "spa", "Catalan": "cat",
    "German": "deu", "Italian": "ita", "Portuguese": "por", "Dutch": "nld",
    "Chinese": "zho", "Japanese": "jpn", "Korean": "kor", "Arabic": "ara",
    "Thai": "tha", "Greek": "ell",
}
