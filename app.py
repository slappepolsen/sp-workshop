#!/usr/bin/env python3
"""
Video Processing GUI Application
A PyQt5 desktop app that provides a button-based interface for all video processing scripts.
"""

__version__ = "10.3.3"
VERSION_CODENAME = "Hallucination"

import sys
import os

import json
from urllib.parse import urlparse
from urllib.request import urlopen, urlretrieve
import re
import shlex
import subprocess
import shutil
import threading
import time
import traceback
import platform
import tarfile
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List


def quote_path(path: str) -> str:
    """Quote a path for shell commands in a cross-platform way.
    
    On Windows, shlex.quote() uses single quotes which CMD doesn't understand.
    This function uses double quotes on Windows and shlex.quote on Unix.
    """
    if platform.system() == "Windows":
        # Windows: use double quotes
        escaped = str(path).replace('"', '\\"')
        return f'"{escaped}"'
    else:
        return shlex.quote(str(path))


def get_temp_dir() -> str:
    """Get a cross-platform temporary directory path."""
    return tempfile.gettempdir()


from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QFileDialog, QDialog,
    QLineEdit, QFormLayout, QMessageBox, QProgressBar, QGroupBox, QStyleFactory, QCheckBox, QStackedWidget, QTextBrowser, QComboBox,
    QGraphicsDropShadowEffect, QTabWidget, QSpinBox, QDoubleSpinBox, QScrollArea, QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QProcess, QUrl, QTimer
from PyQt5.QtGui import QFont, QIcon, QPainter, QPen, QDesktopServices


# Download instructions URL
DOWNLOAD_INSTRUCTIONS_URL = "https://rentry.co/sp-workshop"

# Whisper languages: (display name, code)
TRANSCRIBE_LANGUAGES = [
    ("(Select language)", "auto"),
    ("Catalan", "ca"),
    ("Dutch", "nl"),
    ("English", "en"),
    ("French", "fr"),
    ("German", "de"),
    ("Greek", "el"),
    ("Indonesian", "id"),
    ("Italian", "it"),
    ("Japanese", "ja"),
    ("Korean", "ko"),
    ("Mandarin Chinese", "zh"),
    ("Polish", "pl"),
    ("Portuguese (Brazilian)", "pt"),
    ("Spanish", "es"),
    ("Thai", "th"),
    ("Turkish", "tr"),
]

# Model name -> ggml filename
WHISPER_CPP_MODELS = {
    "tiny.en": "ggml-tiny.en.bin",
    "tiny": "ggml-tiny.bin",
    "tiny.en-q5_1": "ggml-tiny.en-q5_1.bin",
    "tiny-q5_1": "ggml-tiny-q5_1.bin",
    "base.en": "ggml-base.en.bin",
    "base": "ggml-base.bin",
    "base.en-q5_1": "ggml-base.en-q5_1.bin",
    "base-q5_1": "ggml-base-q5_1.bin",
    "small.en": "ggml-small.en.bin",
    "small": "ggml-small.bin",
    "small.en-q5_1": "ggml-small.en-q5_1.bin",
    "small-q5_1": "ggml-small-q5_1.bin",
    "medium.en": "ggml-medium.en.bin",
    "medium": "ggml-medium.bin",
    "medium.en-q5_0": "ggml-medium.en-q5_0.bin",
    "medium-q5_0": "ggml-medium-q5_0.bin",
    "large-v1": "ggml-large-v1.bin",
    "large-v2": "ggml-large-v2.bin",
    "large": "ggml-large-v3.bin",
    "large-q5_0": "ggml-large-v3-q5_0.bin",
    "large-v3-turbo": "ggml-large-v3-turbo.bin",
    "large-v3-turbo-q5_0": "ggml-large-v3-turbo-q5_0.bin",
}

# Model sizes for progress (MB)
WHISPER_CPP_MODEL_SIZES = {
    "ggml-tiny.en.bin": "75 MB",
    "ggml-tiny.bin": "75 MB",
    "ggml-tiny.en-q5_1.bin": "32 MB",
    "ggml-tiny-q5_1.bin": "32 MB",
    "ggml-base.en.bin": "141 MB",
    "ggml-base.bin": "141 MB",
    "ggml-base.en-q5_1.bin": "60 MB",
    "ggml-base-q5_1.bin": "60 MB",
    "ggml-small.en.bin": "465 MB",
    "ggml-small.bin": "465 MB",
    "ggml-small.en-q5_1.bin": "190 MB",
    "ggml-small-q5_1.bin": "190 MB",
    "ggml-medium.en.bin": "1.4 GB",
    "ggml-medium.bin": "1.4 GB",
    "ggml-medium.en-q5_0.bin": "539 MB",
    "ggml-medium-q5_0.bin": "539 MB",
    "ggml-large-v1.bin": "2.9 GB",
    "ggml-large-v2.bin": "2.9 GB",
    "ggml-large-v3.bin": "2.9 GB",
    "ggml-large-v3-q5_0.bin": "2.9 GB",
    "ggml-large-v3-turbo.bin": "1.5 GB",
    "ggml-large-v3-turbo-q5_0.bin": "547 MB",
}


def _whisper_cpp_model_size(filename: str) -> str:
    """Return approximate size string for model filename."""
    return WHISPER_CPP_MODEL_SIZES.get(filename, "?")


# ============================================================================
# Custom Widgets
# ============================================================================

class OutlinedLabel(QLabel):
    """QLabel with text outline effect."""
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Text metrics
        font = self.font()
        painter.setFont(font)
        text = self.text()
        
        # Draw outline with offsets
        pen = QPen(Qt.black, 2, Qt.SolidLine)
        painter.setPen(pen)
        
        # Draw outline in all directions
        offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        for dx, dy in offsets:
            painter.drawText(self.rect().adjusted(dx, dy, dx, dy), Qt.AlignCenter, text)
        
        # Draw text on top
        pen.setColor(Qt.white)
        painter.setPen(pen)
        painter.drawText(self.rect(), Qt.AlignCenter, text)


# ============================================================================
# Configuration Management
# ============================================================================

def get_config_path() -> Path:
    """Get the path to the configuration directory."""
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
        "api_keys": [],  # List of API keys; migrated from api_key/api_key2 if empty
        "download_resolution": "1080",
        "ffmpeg_preset": "medium",
        "ffmpeg_path": "",
        "n_m3u8dl_path": "",
        "setup_complete": False,
        "use_watermarks": True,
        "whisper_output_format": "srt",
        "use_iso639_suffixes": False,
        "whisper_options": {
            "extra_args": "",
            "extra_args_parsed": ""
        },
        "whisper_cpp_path": "",
        "whisper_cpp_model_dir": "",
        "whisper_cpp_model": "base",
        "whisper_cpp_extra_args": ""
    }
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                # Merge whisper_options with defaults
                if "whisper_options" in user_config:
                    default_config["whisper_options"].update(user_config["whisper_options"])
                    del user_config["whisper_options"]
                default_config.update(user_config)
        except Exception as e:
            print(f"Error loading config: {e}")
    
    # Migrate api_key/api_key2 to api_keys
    api_keys = default_config.get("api_keys") or []
    if not api_keys and (default_config.get("api_key") or default_config.get("api_key2")):
        api_keys = [k for k in [default_config.get("api_key"), default_config.get("api_key2")] if k]
        default_config["api_keys"] = api_keys
    
    return default_config


def save_config(config: Dict):
    """Save configuration to JSON file."""
    config_path = get_config_path()
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")


def _has_existing_setup() -> bool:
    """Check if VideoProcessing folder and config file exist (returning user)."""
    vp = Path.home() / "VideoProcessing"
    config_path = vp / "config" / "settings.json"
    return vp.exists() and config_path.exists()


# ============================================================================
# Directory Management (Fixed Structure)
# ============================================================================

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


def get_logs_dir() -> Path:
    """Get the logs directory (e.g. for batch download debug logs)."""
    logs_dir = get_base_dir() / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def open_folder_in_explorer(folder_path: Path):
    """Open a folder in the system file explorer (cross-platform)."""
    folder_str = str(folder_path)
    system = platform.system()
    
    if system == "Darwin":  # macOS
        subprocess.run(["open", folder_str])
    elif system == "Windows":
        subprocess.run(["explorer", folder_str])
    else:  # Linux and others
        subprocess.run(["xdg-open", folder_str])


def _resolve_media_path(filename: str) -> Optional[Path]:
    """Return path to media file. Checks root first (older layouts), then media/ (new layout)."""
    script_dir = Path(__file__).parent
    for base in (script_dir, script_dir / "media"):
        p = base / filename
        if p.exists():
            return p
    return None


def get_app_icon() -> QIcon:
    """Load application icon, preferring .icns on macOS, with fallback to PNG and default.
    
    Note: For best results on macOS, use a PNG with transparent background (alpha channel)
    and convert it to .icns using the create_icon.sh script. The icon should be at least
    1024x1024 pixels for best quality.
    """
    # Prefer .icns on macOS
    if sys.platform == "darwin":
        icns_path = _resolve_media_path("icon.icns")
        if icns_path:
            icon = QIcon(str(icns_path.absolute()))
            # Ensure icon is valid
            if not icon.isNull():
                return icon
    
    # Fallback to PNG
    # Try transparent version first
    transparent_png = _resolve_media_path("icon_transparent.png")
    if transparent_png:
        return QIcon(str(transparent_png.absolute()))
    
    png_path = _resolve_media_path("icon.png")
    if png_path:
        return QIcon(str(png_path.absolute()))
    
    # Fallback to default icon
    return QIcon()


def get_remuxed_dir() -> Path:
    """Get the remuxed directory."""
    remuxed_dir = get_base_dir() / "remuxed"
    remuxed_dir.mkdir(parents=True, exist_ok=True)
    return remuxed_dir


def get_matching_subtitle_for_remux(video_path: Path) -> Optional[Path]:
    """Find an SRT or VTT file with the same stem as the video (for remux auto-match).
    Looks in the video's directory first, then in the app subtitles directory.
    Prefers .srt over .vtt, same directory over subtitles dir.
    """
    if not video_path.exists():
        return None
    stem = video_path.stem
    # 1) Same directory as video
    for ext in (".srt", ".vtt"):
        candidate = video_path.parent / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    # 2) App subtitles directory
    sub_dir = get_subtitles_dir()
    for ext in (".srt", ".vtt"):
        candidate = sub_dir / f"{stem}{ext}"
        if candidate.exists():
            return candidate
    return None


def check_whisper_model_exists(model_name: str) -> bool:
    """Check if a Whisper model already exists in the default cache location.
    
    Args:
        model_name: The model name (e.g., "tiny", "base", "small", "medium", "large", "turbo")
    
    Returns:
        True if the model file exists, False otherwise
    """
    system = platform.system()
    
    # Whisper cache: ~/.cache/whisper
    if system == "Windows":
        cache_dir = Path.home() / ".cache" / "whisper"
    else:  # macOS, Linux, etc.
        cache_dir = Path.home() / ".cache" / "whisper"
    
    # Model filename mappings
    model_files = {
        "tiny": "tiny.pt",
        "base": "base.pt",
        "small": "small.pt",
        "medium": "medium.pt",
        "large": "large-v2.pt",  # Note: Whisper uses "large-v2" filename I
        "turbo": "turbo.pt"
    }
    
    model_file = model_files.get(model_name.lower())
    if not model_file:
        return False
    
    model_path = cache_dir / model_file
    return model_path.exists()


# ============================================================================
# ISO 639-2/T Language Codes for Subtitle Suffixes
# ============================================================================

# Target languages for gst
TRANSLATION_TARGET_LANGUAGES = [
    "Catalan", "Dutch", "English", "French", "German", "Greek",
    "Indonesian", "Italian", "Japanese", "Korean", "Mandarin Chinese",
    "Polish", "Portuguese", "Brazilian", "Spanish",
    "Thai", "Turkish",
]

# ISO 639 codes for .eng.srt etc
ISO_639_CODES = {
    "Catalan": "cat", "Dutch": "nld", "English": "eng", "French": "fra",
    "German": "deu", "Greek": "ell", "Indonesian": "ind", "Italian": "ita",
    "Japanese": "jpn", "Korean": "kor", "Mandarin Chinese": "zho", "Polish": "pol",
    "Portuguese": "por", "Portuguese (Brazilian)": "por", "Spanish": "spa",
    "Thai": "tha", "Turkish": "tur",
}


# ============================================================================
# Video Analysis Functions
# ============================================================================

def get_video_duration(video_path: Path) -> Optional[float]:
    """Get video duration in minutes using ffprobe."""
    try:
        ffprobe_exe = get_ffprobe_command()
        cmd = [
            ffprobe_exe, "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            duration_seconds = float(result.stdout.strip())
            return duration_seconds / 60.0  # Convert to minutes
    except Exception:
        pass
    return None


def get_video_duration_seconds(video_path: Path) -> Optional[float]:
    """Get video duration in seconds using ffprobe."""
    try:
        ffprobe_exe = get_ffprobe_command()
        cmd = [
            ffprobe_exe, "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except Exception:
        pass
    return None


def get_audio_channels(video_path: Path) -> Optional[int]:
    """Get audio channel count using ffprobe."""
    try:
        ffprobe_exe = get_ffprobe_command()
        cmd = [
            ffprobe_exe, "-v", "error", "-select_streams", "a:0",
            "-show_entries", "stream=channels",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            channels_str = result.stdout.strip()
            if channels_str:
                return int(channels_str)
    except Exception:
        pass
    return None


def parse_ffmpeg_time(time_str: str) -> Optional[float]:
    """Parse FFmpeg time string (HH:MM:SS.ms or MM:SS.ms) to seconds."""
    try:
        # Strip whitespace
        time_str = time_str.strip()
        
        # Split by colon
        parts = time_str.split(':')
        
        if len(parts) == 3:
            # HH:MM:SS.ms
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:
            # MM:SS.ms
            minutes = float(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        else:
            # Try seconds only
            return float(time_str)
    except (ValueError, IndexError):
        return None


def format_eta(seconds: float) -> str:
    """Format seconds as ETA string (MM:SS or HH:MM:SS)."""
    if seconds < 0:
        return "Calculating..."
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def clean_log_line(line: str) -> Optional[str]:
    """Clean a log line by removing ANSI codes and filtering noise.
    
    Returns None if the line should be skipped, otherwise returns cleaned line.
    IMPORTANT: Error messages are always preserved.
    """
    if not line:
        return None
    
    # Remove ANSI codes
    line = re.sub(r'\033\[[0-9;]*[a-zA-Z]', '', line)
    
    # Remove cursor sequences
    line = line.replace('\033[F', '').replace('\033[K', '')
    
    # Skip empty lines
    if not line.strip():
        return None

    # Skip dependency warnings
    if "RequestsDependencyWarning" in line or ("urllib3" in line and "doesn't match" in line):
        return None

    # Preserve errors/warnings
    is_error = any(keyword in line.lower() for keyword in [
        'error', 'failed', 'exception', 'warning', 'warn', 'fail', 
        '✗', '⚠', '❌', 'critical', 'fatal', 'unable', 'cannot',
        'not found', 'missing', 'invalid', 'denied', 'timeout'
    ])
    
    # Return errors immediately
    if is_error:
        return f"    ⚠ {line.strip()}"
    
    # Skip validating messages
    if "Validating token size..." in line:
        return None
    
    # Skip token validated message
    if "Token size validated. Translating..." in line:
        return None
    
    # Skip API Key messages
    if "Starting with" in line and "API Key" in line:
        return None

    # Handle starting translation line
    if "Starting translation of" in line and "lines..." in line:
        match = re.search(r'Starting translation of (\d+) lines', line)
        if match:
            return f"    Starting translation of {match.group(1)} lines..."
    
    # Extract progress info
    if "Translating:" in line and "|" in line:
        # Extract percent and status
        match = re.search(r'Translating:.*?(\d+)% \((\d+)/(\d+)\)', line)
        if match:
            percent = match.group(1)
            current = match.group(2)
            total = match.group(3)
            
            # Extract status after |
            status_parts = line.split('|')
            status = ""
            if len(status_parts) > 1:
                # Last part after |
                last_part = status_parts[-1].strip()
                # Remove model name
                last_part = re.sub(r'gemini-[^\s]+', '', last_part).strip()
                # Normalize spinner
                spinner_match = re.match(r'^(Thinking|Processing)\s*[—\\|/\s]*$', last_part)
                if spinner_match:
                    status = f"{spinner_match.group(1)}..."
                elif last_part and last_part not in ['Thinking', 'Processing', 'Sending batch']:
                    status = last_part
                elif last_part in ['Thinking', 'Processing', 'Sending batch']:
                    status = f"{last_part}..." if last_part != "Sending batch" else "Sending batch..."
            
            # Build progress line
            if status:
                return f"    Progress: {percent}% ({current}/{total} lines) - {status}"
            else:
                return f"    Progress: {percent}% ({current}/{total} lines)"
    
    # Success message
    if "✅" in line or "Translation completed successfully" in line:
        return "    ✓ Translation completed successfully!"

    # Fallback: Progress format
    prog_match = re.match(r'^\s*Progress:\s*(\d+)%\s*\((\d+)/(\d+)\s*lines?\)\s*-?\s*(.*)$', line.strip())
    if prog_match:
        percent, current, total, status = prog_match.groups()
        status = status.strip()
        # Collapse spinner
        spin = re.match(r'^(Thinking|Processing)\s*[—\\|/\s]*$', status)
        if spin:
            status = f"{spin.group(1)}..."
        return f"    Progress: {percent}% ({current}/{total} lines) - {status}" if status else f"    Progress: {percent}% ({current}/{total} lines)"

    # Return other messages
    return line.strip()


def detect_episode_or_scene(video_path: Path) -> tuple[str, Optional[float]]:
    """Detect if video is an episode or scene based on duration (7 min threshold)."""
    duration = get_video_duration(video_path)
    if duration is None:
        return "unknown", None
    if duration >= 7.0:
        return "episode", duration
    else:
        return "scene", duration


def open_in_lossless_cut(video_paths: List[Path], log_callback=None) -> bool:
    """Open video file(s) in LosslessCut application (cross-platform).
    
    Args:
        video_paths: List of Path objects for video files to open
        log_callback: Optional logging function
        
    Returns:
        True if successful, False otherwise
    """
    lossless_cut = get_app_executable("LosslessCut")
    
    if not lossless_cut:
        if log_callback:
            log_callback("Error: LosslessCut not found. Please install it from https://github.com/mifi/lossless-cut")
        return False
    
    try:
        system = platform.system()
        path_strings = [str(p) for p in video_paths]
        
        if system == "Darwin":
            # macOS: open -a
            subprocess.run(["open", "-a", str(lossless_cut), *path_strings])
        elif system == "Windows":
            # Windows: run executable
            subprocess.Popen([str(lossless_cut), *path_strings])
        else:
            # Linux: run executable
            subprocess.Popen([str(lossless_cut), *path_strings])
        
        if log_callback:
            count = len(video_paths)
            if count == 1:
                log_callback(f"Opened {video_paths[0].name} in LosslessCut")
            else:
                log_callback(f"Opened {count} files in LosslessCut")
        return True
    except Exception as e:
        if log_callback:
            log_callback(f"Error opening LosslessCut: {e}")
        return False


# ============================================================================
# Episode Range Parser
# ============================================================================

def parse_episode_range(range_str: str) -> List[int]:
    """Parse episode range string like '1-5,7,9-11' into list of episode numbers.
    
    Args:
        range_str: String like '1', '1-5', '1,3,5', '1-3,5,7-9'
    
    Returns:
        List of episode numbers in order
    
    Examples:
        '1' -> [1]
        '1-5' -> [1, 2, 3, 4, 5]
        '1,3,5' -> [1, 3, 5]
        '1-3,5,7-9' -> [1, 2, 3, 5, 7, 8, 9]
    """
    episodes = []
    parts = range_str.split(',')
    
    for part in parts:
        part = part.strip()
        if '-' in part:
            # Range like '1-5'
            try:
                start, end = part.split('-')
                start_num = int(start.strip())
                end_num = int(end.strip())
                episodes.extend(range(start_num, end_num + 1))
            except (ValueError, IndexError):
                continue
        else:
            # Single number
            try:
                episodes.append(int(part))
            except ValueError:
                continue
    
    return episodes


def _sanitize_filename(name: str) -> str:
    """Sanitize string for use as filename stem. Disallow / \\ : * ? " < > |"""
    if not name:
        return ""
    invalid = r'/\:*?"<>|'
    result = "".join(c if c not in invalid else "_" for c in name.strip())
    return " ".join(result.split())  # collapse multiple spaces


def build_save_names(
    mode: str,
    name: str,
    use_s01e: bool,
    season: int,
    spec: str,
    count: int,
) -> List[str]:
    """Build list of save-name stems for batch download.

    Args:
        mode: "episodes" or "movie"
        name: Optional prefix (show/movie name), sanitized
        use_s01e: For episodes, use S01E02 format
        season: Season number when use_s01e
        spec: Episode range (1, 1-5, 1,3,5-7) for episodes; ignored for movie
        count: Number of commands (items)

    Returns:
        List of save-name stems, one per command
    """
    safe_name = _sanitize_filename(name)
    prefix = f"{safe_name} " if safe_name else ""

    if mode == "movie":
        if count == 1:
            return [safe_name or "1"]
        return [f"{prefix}{i + 1}" if safe_name else str(i + 1) for i in range(count)]

    # Episode(s) mode
    if use_s01e:
        episodes = parse_episode_range(spec)
        if not episodes:
            episodes = list(range(1, count + 1))
        if len(episodes) < count:
            last = episodes[-1]
            episodes.extend(range(last + 1, last + 1 + (count - len(episodes))))
        return [f"{prefix}S{season:02d}E{e:02d}" for e in episodes[:count]]

    # Episode(s) + numbers
    nums = parse_episode_range(spec)
    if not nums:
        nums = list(range(1, count + 1))
    if len(nums) < count:
        last = nums[-1]
        nums.extend(range(last + 1, last + 1 + (count - len(nums))))
    return [f"{prefix}{n}" if safe_name else str(n) for n in nums[:count]]


def _add_headers_for_bare_url(url_or_cmd: str) -> str:
    """Add Referer/Origin headers for bare URLs. Many CDNs require these to avoid 403."""
    # Referer/Origin from URL
    url = url_or_cmd.strip().strip('"')
    if not url.startswith('http'):
        return url_or_cmd
    url_lower = url.lower()
    if 'globo.com' in url_lower or 'globoplay' in url_lower:
        referer, origin = "https://globoplay.globo.com/", "https://globoplay.globo.com"
    elif 'tf1.fr' in url_lower:
        referer, origin = "https://www.tf1.fr/", "https://www.tf1.fr"
    else:
        # Use URL origin
        try:
            p = urlparse(url)
            base = f"{p.scheme}://{p.netloc}"
            referer, origin = base + "/", base
        except Exception:
            referer, origin = "https://example.com/", "https://example.com"
    headers = [
        f'-H {shlex.quote("User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")}',
        f'-H {shlex.quote(f"Referer: {referer}")}',
        f'-H {shlex.quote("Accept: */*")}',
        f'-H {shlex.quote("Origin: " + origin)}',
    ]
    # Quote URL for params
    return f"{' '.join(headers)} \"{url}\""


def _drop_n_m3u8_output_options(args: List[str]) -> List[str]:
    """Remove output/save options from user args so app's --save-name/--save-dir/-M apply."""
    drop_flags = {
        "--save-name", "--save-dir", "--tmp-dir",
        "-m", "-M", "--mux-after-done", "--del-after-done",
        "--check-segments-count", "--select-video", "--select-audio", "--select-subtitle",
    }
    result = []
    i = 0
    while i < len(args):
        a = args[i]
        a_lower = a.lower()
        if a_lower in drop_flags:
            # Skip flag and value
            if a_lower in ("-m", "-M", "--save-name", "--save-dir", "--tmp-dir", "--check-segments-count",
                          "--select-video", "--select-audio", "--select-subtitle"):
                i += 2  # skip value (avoid bounds: don't skip past end)
                if i > len(args):
                    i = len(args)
            else:
                i += 1
            continue
        result.append(args[i])
        i += 1
    return result


def _url_first_args(args: List[str]) -> List[str]:
    """Put URL(s) first; N_m3u8DL-RE requires <URL> before options or it prints help."""
    urls = [a for a in args if a.startswith("http://") or a.startswith("https://")]
    rest = [a for a in args if a not in urls]
    return urls + rest


def _strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences to reduce log file size."""
    return re.sub(r'\x1b\[[0-9;]*m', '', text)


# ============================================================================
# Script Wrappers
# ============================================================================

def download_episodes(
    commands_text: str,
    output_dir: Path,
    mode: str = "episodes",
    name: str = "",
    use_s01e: bool = False,
    season: int = 1,
    ep_spec: str = "1",
    select_video: str = "best",
    progress_callback=None,
    log_callback=None,
) -> bool:
    """Download episodes or movies using commands from text.

    User pastes full N_m3u8DL-RE commands per instructions. App adds save options only.

    Args:
        commands_text: Raw N_m3u8DL-RE commands, one per line
        output_dir: Directory to save downloaded files
        mode: "episodes" or "movie"
        name: Optional prefix (show/movie name)
        use_s01e: For episodes, use S01E02 format
        season: Season number when use_s01e
        ep_spec: Episode range (1, 1-5, 1,3,5-7) for episodes
        progress_callback: Callback for progress updates
        log_callback: Callback for log messages
    """
    if not commands_text.strip():
        if log_callback:
            log_callback("Error: No commands provided.")
        return False

    if not n_m3u8dl_installed():
        if log_callback:
            log_callback("Error: N_m3u8DL-RE not found. Install it via the Setup Wizard or set n_m3u8dl_path in Settings.")
        return False

    # Filter HAR and empty lines
    lines = []
    for line in commands_text.strip().split('\n'):
        line = line.strip()
        # Skip empty, comments, HAR
        if line and not line.startswith('#') and not line.startswith('@'):
            lines.append(line)

    if not lines:
        if log_callback:
            log_callback("No commands found.")
        return False

    # Build save names
    save_names = build_save_names(mode, name, use_s01e, season, ep_spec, len(lines))

    downloaded_files = []
    total = len(lines)
    if log_callback:
        log_callback(f"Starting batch download for {total} items...")
        if save_names:
            log_callback(f"Output names: {', '.join(save_names[:5])}{' ...' if len(save_names) > 5 else ''}")

    debug_log_path = get_logs_dir() / f"_batch_download_debug_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    debug_file = open(debug_log_path, 'w', encoding='utf-8')
    if log_callback:
        log_callback(f"Full debug log: {debug_log_path}")

    try:
        for i, base_command in enumerate(lines):
            save_name = save_names[i] if i < len(save_names) else str(i + 1)

            # Skip empty or comments
            if not base_command or base_command.startswith('#'):
                continue

            # Strip N_m3u8DL-RE prefix
            if base_command.lower().startswith('n_m3u8dl-re '):
                base_command = base_command[12:].strip()

            # Add CDN headers for bare URLs
            if ' -H ' not in base_command and ' --key ' not in base_command and base_command.lstrip('"').startswith('http'):
                base_command = _add_headers_for_bare_url(base_command)
                if log_callback:
                    log_callback("  (Bare URL detected – added Referer/Origin headers)")

            if progress_callback:
                progress_callback(i + 1, total, save_name)

            # Parse with shlex
            try:
                user_args = shlex.split(base_command)
            except ValueError as e:
                if log_callback:
                    log_callback(f"  ✗ Invalid quoting in command: {e}")
                continue
            # Drop user output options
            user_args = _drop_n_m3u8_output_options(user_args)
            # URL must be first
            user_args = _url_first_args(user_args)

            app_args = [
                "--tmp-dir", get_temp_dir(),
                "--del-after-done",
                "--check-segments-count", "False",
                "--save-name", save_name,
                "--save-dir", str(output_dir),
                "--select-video", select_video,
                "--select-audio", "all",
                "--select-subtitle", "all",
                "-M", "mkv",
            ]
            n_m3u8_cmd = get_n_m3u8dl_command()
            cmd = [n_m3u8_cmd] + user_args + app_args

            if log_callback:
                log_callback(f"\n--- Task {i + 1}/{total}: {save_name} ---")
                log_callback(f"Running: {base_command[:80]}...")
            debug_file.write(f"\n--- Task {i + 1}/{total}: {save_name} ---\n")
            debug_file.write(f"Running: {base_command[:80]}...\n")
            debug_file.flush()

            # Popen with list for correct args
            try:
                process = subprocess.Popen(
                    cmd,
                    shell=False,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,  # Combine stderr into stdout
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )

                # Stream output
                output_lines = []
                last_logged_percent = -5  # Track last logged percentage to avoid spam

                while True:
                    line_output = process.stdout.readline()
                    if not line_output:
                        break
                    # Skip progress bar lines
                    is_progress_bar = '━' in line_output
                    if not is_progress_bar:
                        cleaned = _strip_ansi(line_output)
                        debug_file.write(cleaned)
                        debug_file.flush()
                    line_output = line_output.strip()
                    if line_output:
                        output_lines.append(line_output)

                        # Skip progress bar
                        is_progress_bar = '━' in line_output

                        # Skip file access warnings
                        is_file_access_warning = 'The process cannot access the file' in line_output

                        # Log important only
                        should_log = (
                            not is_progress_bar and
                            not is_file_access_warning and (
                                'INFO' in line_output or
                                'WARN' in line_output or
                                'ERROR' in line_output or
                                'Selected streams' in line_output or
                                'Start downloading' in line_output or
                                'Downloaded' in line_output or
                                'Muxing' in line_output or
                                'Done' in line_output
                            )
                        )

                        if should_log and log_callback:
                            log_callback(f"  {line_output}")

                        # Suppress progress spam

                # Wait for process
                returncode = process.wait()

                if returncode == 0:
                    # Escape glob metachars
                    pattern = save_name.replace("\\", "\\\\").replace("*", "[*]").replace("?", "[?]").replace("[", "[[]")
                    candidates = list(output_dir.glob(f"{pattern}.*"))
                    if candidates:
                        downloaded_files.append(candidates[0])
                        if log_callback:
                            log_callback(f"  ✓ Downloaded: {candidates[0].name}")
                    else:
                        if log_callback:
                            log_callback(f"  ⚠ Warning: No output file found for {save_name}")
                else:
                    if log_callback:
                        log_callback(f"  ✗ Error downloading {save_name} (exit code: {returncode})")
                        # Show last lines for debug
                        if output_lines:
                            log_callback(f"    Last output lines:")
                            for err_line in output_lines[-5:]:
                                clean = re.sub(r'\033\[[0-9;]*[a-zA-Z]', '', err_line).replace('\033[F', '').replace('\033[K', '').strip()
                                if clean:
                                    log_callback(f"      {clean}")

            except Exception as e:
                if log_callback:
                    log_callback(f"  ✗ Exception while downloading {save_name}: {e}")
                    log_callback(f"    Traceback: {traceback.format_exc()}")
    finally:
        debug_file.close()

    if log_callback:
        log_callback(f"\nBatch download completed. Downloaded {len(downloaded_files)}/{total} files.")
    
    return len(downloaded_files) > 0


def extract_subtitles(downloads_dir: Path, subtitles_dir: Path, progress_callback=None, log_callback=None) -> bool:
    """Extract subtitles from MKV files."""
    if not downloads_dir.exists():
        if log_callback:
            log_callback(f"Error: Downloads directory not found: {downloads_dir}")
        return False
    
    subtitles_dir.mkdir(parents=True, exist_ok=True)
    mkv_files = list(downloads_dir.glob("*.mkv"))
    
    if not mkv_files:
        if log_callback:
            log_callback("No MKV files found in downloads directory.")
        return False
    
    total = len(mkv_files)
    success_count = 0
    for idx, mkv_file in enumerate(mkv_files, start=1):
        base = mkv_file.stem
        srt_file = subtitles_dir / f"{base}.srt"
        
        if progress_callback:
            progress_callback(idx, total, mkv_file.name)
        
        if srt_file.exists():
            if log_callback:
                log_callback(f"Skipping {mkv_file.name} - subtitle already exists")
            continue
        
        if log_callback:
            log_callback(f"Extracting subtitles from: {mkv_file.name}")
        
        ffmpeg_exe = get_ffmpeg_command()
        cmd = [
            ffmpeg_exe, "-y", "-i", str(mkv_file),
            "-map", "0:s:0", str(srt_file)
        ]
        
        # Stream FFmpeg output
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Read stderr
            error_lines = []
            while True:
                line = process.stderr.readline()
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                error_lines.append(line)
                
                # Log progress
                if "Stream #" in line or "Subtitle:" in line:
                    if log_callback:
                        log_callback(f"    {line}")
                elif "Error" in line or "error" in line.lower():
                    if log_callback:
                        log_callback(f"    ⚠ {line}")
            
            # Wait for process
            returncode = process.wait()
            
            if returncode == 0 and srt_file.exists():
                success_count += 1
                if log_callback:
                    log_callback(f"  ✓ Extracted: {srt_file.name}")
            else:
                if log_callback:
                    log_callback(f"  ✗ Failed: {mkv_file.name}")
                    if returncode != 0:
                        log_callback(f"    Return code: {returncode}")
                    if error_lines:
                        log_callback(f"    FFmpeg errors:")
                        for err_line in error_lines[-5:]:
                            log_callback(f"      {err_line}")
        
        except Exception as e:
            if log_callback:
                log_callback(f"  ✗ Exception while extracting from {mkv_file.name}: {e}")
                log_callback(f"    Traceback: {traceback.format_exc()}")
    
    if log_callback:
        log_callback(f"\nExtraction complete. Extracted {success_count}/{total} files.")
    
    return success_count > 0


def clean_subtitles(subtitles_dir: Path, progress_callback=None, log_callback=None) -> bool:
    """Remove color tags from subtitle files."""
    if not subtitles_dir.exists():
        if log_callback:
            log_callback(f"Error: Subtitles directory not found: {subtitles_dir}")
        return False
    
    srt_files = list(subtitles_dir.glob("*.srt"))
    
    if not srt_files:
        if log_callback:
            log_callback("No SRT files found.")
        return False
    
    total = len(srt_files)
    cleaned_count = 0
    skipped_count = 0
    
    if log_callback:
        log_callback(f"Starting subtitle cleaning for {total} file(s)...")
    
    for idx, srt_file in enumerate(srt_files, start=1):
        if progress_callback:
            progress_callback(idx, total, srt_file.name)
        
        try:
            # File size for logging
            file_size = srt_file.stat().st_size
            file_size_kb = file_size / 1024
            
            with open(srt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_length = len(content)
            
            # Remove color tags
            cleaned = re.sub(r'<c\.[a-zA-Z0-9_]+>', '', content)
            cleaned = re.sub(r'</c\.[a-zA-Z0-9_]+>', '', cleaned)
            
            if cleaned != content:
                tags_removed = len(re.findall(r'<c\.[a-zA-Z0-9_]+>|</c\.[a-zA-Z0-9_]+>', content))
                with open(srt_file, 'w', encoding='utf-8') as f:
                    f.write(cleaned)
                cleaned_count += 1
                if log_callback:
                    log_callback(f"  ✓ Cleaned: {srt_file.name} ({file_size_kb:.1f} KB, removed {tags_removed} color tag(s))")
            else:
                skipped_count += 1
                if log_callback:
                    log_callback(f"  ○ Skipped: {srt_file.name} ({file_size_kb:.1f} KB, no color tags found)")
        except Exception as e:
            if log_callback:
                log_callback(f"  ✗ Error cleaning {srt_file.name}: {e}")
    
    if log_callback:
        log_callback(f"\nCleaning complete. Cleaned {cleaned_count}/{total} files, skipped {skipped_count}.")
    
    return True


def _is_quota_limit_error(output_lines: List[str]) -> bool:
    """Detect Gemini API quota/rate-limit errors from gst output."""
    combined = " ".join(output_lines).lower()
    patterns = ("429", "resource_exhausted", "quota", "rate limit", "exhausted", "too many requests")
    return any(p in combined for p in patterns)


def _get_key_pairs(env_key: Optional[str], api_keys: Optional[List[str]]) -> List[tuple]:
    """Build (primary, secondary) key pairs for gst. gst uses GEMINI_API_KEY env + -k2."""
    keys = list(api_keys) if api_keys else []
    pairs = []
    if env_key:
        if keys:
            pairs.append((env_key, keys[0]))
            i = 1
        else:
            pairs.append((env_key, None))
            i = 0
    else:
        i = 0
    while i + 1 < len(keys):
        pairs.append((keys[i], keys[i + 1]))
        i += 2
    if i < len(keys):
        pairs.append((keys[i], None))
    return pairs


def translate_subtitles(selected_srt_files: List[Path], target_language: str = "English",
                       use_iso639: bool = False, api_keys: Optional[List[str]] = None,
                       api_key: Optional[str] = None, api_key2: Optional[str] = None,
                       progress_callback=None, log_callback=None) -> bool:
    """Translate selected subtitle files using gemini-srt-translator.

    Supports 6+ API keys: on quota-limit error, retries with the next key pair.

    Args:
        selected_srt_files: List of SRT files to translate
        target_language: Target language for translation (default: English)
        use_iso639: Whether to add ISO 639 language suffix to output filename
        api_keys: List of API keys (preferred). If None/empty, falls back to api_key/api_key2.
        api_key, api_key2: Legacy params for backward compat
        progress_callback: Callback for progress updates
        log_callback: Callback for log messages
    """
    env_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GST_API_KEY")
    resolved_keys = api_keys if api_keys else [k for k in [api_key, api_key2] if k]
    key_pairs = _get_key_pairs(env_api_key, resolved_keys)
    primary = (key_pairs[0][0] if key_pairs else None) or (resolved_keys[0] if resolved_keys else None)

    if not primary:
        if log_callback:
            log_callback("Error: API key not set.")
            log_callback("Please set GEMINI_API_KEY or GST_API_KEY environment variable, or configure in Settings.")
        return False

    if not selected_srt_files:
        if log_callback:
            log_callback("No SRT files selected.")
        return False

    srt_files = [Path(f) for f in selected_srt_files if Path(f).suffix.lower() == ".srt" and not Path(f).name.endswith("_OG.srt")]
    total = len(srt_files)
    success_count = 0

    for idx, srt_file in enumerate(srt_files, start=1):
        if progress_callback:
            progress_callback(idx, total, srt_file.name)

        try:
            iso_match = re.match(r'(.+)\.([a-z]{3})$', srt_file.stem)
            if iso_match:
                base_name = iso_match.group(1)
                og_file = srt_file.parent / f"{base_name}_OG.srt"
            else:
                og_file = srt_file.parent / f"{srt_file.stem}_OG.srt"

            if not og_file.exists():
                srt_file.rename(og_file)

            if log_callback:
                log_callback(f"Translating: {srt_file.name}")

            gst_cmd = find_gst_command()
            if not gst_cmd:
                if log_callback:
                    log_callback(f"  ✗ Failed: {srt_file.name}")
                    log_callback(f"    Error: gst command not found. Make sure gemini-srt-translator is installed.")
                continue

            pair_index = 0
            translation_success = False
            final_srt_file = srt_file
            max_progress_pct = 0  # Never decrease bar when switching API pairs (restart from 0)

            while pair_index < len(key_pairs):
                primary_key, secondary_key = key_pairs[pair_index]
                if not primary_key:
                    pair_index += 1
                    continue

                base_cmd = ["translate", "-i", str(og_file), "-l", target_language, "-o", str(srt_file), "--skip-upgrade", "--batch-size", "30", "--thinking-budget", "0"]
                if secondary_key:
                    base_cmd.extend(["-k2", secondary_key])

                if " -m " in gst_cmd:
                    cmd_parts = gst_cmd.split() + base_cmd
                else:
                    cmd_parts = [gst_cmd] + base_cmd

                env = os.environ.copy()
                env["GEMINI_API_KEY"] = primary_key

                process = subprocess.Popen(
                    cmd_parts,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    env=env,
                )

                output_lines = []
                last_progress_line = None
                last_progress_tuple = None  # (percent, current, total) - only log when this changes
                logged_once = set()  # Dedupe noisy repeated messages
                while True:
                    line_output = process.stdout.readline()
                    if not line_output:
                        break
                    cleaned_line = clean_log_line(line_output)
                    if cleaned_line:
                        output_lines.append(line_output.strip())
                        # Switch keys when exhausted
                        if "All API quotas exceeded" in cleaned_line and "waiting" in cleaned_line:
                            if log_callback and pair_index + 1 < len(key_pairs):
                                log_callback(f"    All API quotas exceeded - switching to next API key pair ({pair_index + 2}/{len(key_pairs)})...")
                            process.terminate()
                            try:
                                process.wait(timeout=5)
                            except subprocess.TimeoutExpired:
                                process.kill()
                                process.wait()
                            break
                        # Progress: update bar, skip log
                        prog_match = re.match(r'\s*Progress:\s*(\d+)%\s*\((\d+)/(\d+)\s*lines?\)', cleaned_line)
                        if prog_match:
                            pct, cur, tot = int(prog_match.group(1)), int(prog_match.group(2)), int(prog_match.group(3))
                            # Update bar when advancing
                            if pct >= max_progress_pct:
                                max_progress_pct = pct
                                if progress_callback:
                                    progress_callback(idx, total, f"{srt_file.name} ({pct}%)")
                            if (pct, cur, tot) == last_progress_tuple:
                                continue
                            last_progress_tuple = (pct, cur, tot)
                            # Skip progress log
                            last_progress_line = cleaned_line
                            continue
                        # Dedupe same line
                        if cleaned_line == last_progress_line:
                            continue
                        # Dedupe repeated errors
                        noise_key = None
                        if "Consecutive error count:" in cleaned_line:
                            noise_key = re.search(r'Consecutive error count: \d+/\d+', cleaned_line)
                            noise_key = noise_key.group(0) if noise_key else cleaned_line
                        elif "malformed object" in cleaned_line and "line" in cleaned_line:
                            noise_key = re.search(r'for line \d+', cleaned_line)
                            noise_key = noise_key.group(0) if noise_key else cleaned_line
                        elif "Retrying batch for lines" in cleaned_line:
                            noise_key = re.search(r'Retrying batch for lines \d+-\d+', cleaned_line)
                            noise_key = noise_key.group(0) if noise_key else cleaned_line
                        elif "quota exceeded" in cleaned_line.lower() and "Switching to" in cleaned_line:
                            noise_key = re.search(r'API \d+ quota.*Switching to API \d+', cleaned_line, re.I)
                            noise_key = noise_key.group(0) if noise_key else cleaned_line
                        elif "All API quotas exceeded" in cleaned_line and "waiting" in cleaned_line:
                            noise_key = "All API quotas exceeded, waiting"
                        if noise_key and noise_key in logged_once:
                            continue
                        if noise_key:
                            logged_once.add(noise_key)
                        if log_callback:
                            log_callback(cleaned_line)
                        last_progress_line = cleaned_line

                returncode = process.wait()

                progress_files = list(srt_file.parent.glob("*.progress"))
                for progress_file in progress_files:
                    try:
                        progress_file.unlink()
                        if log_callback:
                            log_callback(f"    Cleaned up: {progress_file.name}")
                    except Exception as e:
                        if log_callback:
                            log_callback(f"    Warning: Could not remove {progress_file.name}: {e}")

                if returncode == 0 and srt_file.exists():
                    try:
                        file_size = srt_file.stat().st_size
                        if file_size > 0:
                            with open(srt_file, 'r', encoding='utf-8') as f:
                                content_preview = f.read(100)
                                if content_preview.strip():
                                    translation_success = True
                    except Exception:
                        pass

                if translation_success:
                    break

                if _is_quota_limit_error(output_lines) and pair_index + 1 < len(key_pairs):
                    if srt_file.exists():
                        try:
                            srt_file.unlink()
                        except Exception:
                            pass
                    if log_callback:
                        log_callback(f"    Retrying with API key pair {pair_index + 2}/{len(key_pairs)}...")
                    pair_index += 1
                else:
                    break

            if translation_success:
                if use_iso639:
                    target_code = ISO_639_CODES.get(target_language, "eng")
                    source_match = re.match(r'(.+)\.([a-z]{3})$', srt_file.stem)
                    if source_match:
                        base_name = source_match.group(1)
                    else:
                        base_name = srt_file.stem
                    final_srt_file = srt_file.parent / f"{base_name}.{target_code}.srt"
                    if srt_file != final_srt_file:
                        srt_file.rename(final_srt_file)
                        if log_callback:
                            log_callback(f"    Renamed to: {final_srt_file.name}")

                success_count += 1
                if log_callback:
                    output_combined = " ".join(output_lines).lower()
                    was_interrupted = (
                        "translation interrupted" in output_combined
                        or "5 consecutive errors" in output_combined
                        or "stopping script due to reaching" in output_combined
                    )
                    if was_interrupted:
                        log_callback(f"  ✓ Partially translated (interrupted): {final_srt_file.name}")
                    else:
                        log_callback(f"  ✓ Translated: {final_srt_file.name}")
            else:
                if log_callback:
                    log_callback(f"  ✗ Failed: {srt_file.name}")
                    if output_lines:
                        log_callback(f"    Last output lines:")
                        for err_line in output_lines[-5:]:
                            clean = re.sub(r'\033\[[0-9;]*[a-zA-Z]', '', err_line).replace('\033[F', '').replace('\033[K', '').strip()
                            if clean:
                                log_callback(f"      {clean}")
        except Exception as e:
            if log_callback:
                log_callback(f"Error translating {srt_file.name}: {e}")

    if log_callback:
        log_callback(f"\nTranslation complete. Translated {success_count}/{total} files.")

    return success_count > 0


def process_video(selected_video_files: List[Path], subtitles_dir: Path, output_dir: Path,
                 watermark_path: str, resolution: str, use_watermarks: bool = True,
                 ffmpeg_path: str = "", use_iso639: bool = False, target_language: str = "English",
                 downloads_dir: Path = None, progress_callback=None, log_callback=None) -> bool:
    """Process selected video files: burn subtitles, add watermark (if enabled), resize.
    
    Args:
        use_iso639: Whether to look for ISO 639 suffixed subtitle files
        target_language: Target language for ISO 639 suffix matching
    """
    if not selected_video_files:
        if log_callback:
            log_callback("No video files selected.")
        return False
    
    if use_watermarks and not Path(watermark_path).exists():
        if log_callback:
            log_callback(f"Error: Watermark file not found: {watermark_path}")
        return False
    
    output_dir.mkdir(parents=True, exist_ok=True)
    video_files = [Path(f) for f in selected_video_files if Path(f).suffix.lower() in [".mkv", ".mp4", ".mov"]]
    
    if not video_files:
        if log_callback:
            log_callback("No valid video files selected.")
        return False
    
    success_count = 0
    height = "720" if resolution == "720" else "1080"
    preset = "medium" if resolution == "720" else "slow"
    total = len(video_files)
    
    for idx, video_file in enumerate(video_files, start=1):
        base = video_file.stem
        
        # Find subtitle
        srt_file = None
        srt_location = None
        
        # Build filename list
        filenames_to_try = [f"{base}.srt"]  # Always try exact match first
        
        if use_iso639:
            # Try ISO 639 suffix
            target_code = ISO_639_CODES.get(target_language, "eng")
            filenames_to_try.append(f"{base}.{target_code}.srt")
        
        # Check each location
        for filename in filenames_to_try:
            # Video directory first
            candidate = video_file.parent / filename
            if candidate.exists():
                srt_file = candidate
                srt_location = "video directory"
                break
            
            # 2. Subtitles directory
            candidate = subtitles_dir / filename
            if candidate.exists():
                srt_file = candidate
                srt_location = "subtitles directory"
                break

            # Downloads fallback
            if downloads_dir and downloads_dir.exists():
                candidate = downloads_dir / filename
                if candidate.exists():
                    srt_file = candidate
                    srt_location = "downloads directory"
                    break

        out_file = output_dir / f"{base}.mp4"
        
        if progress_callback:
            progress_callback(idx, total, video_file.name)
        
        if out_file.exists():
            if log_callback:
                log_callback(f"Skipping {video_file.name} - output file already exists: {out_file.name}")
            continue
        
        if not srt_file:
            if log_callback:
                log_callback(f"Skipping {video_file.name} - subtitle file not found")
                checked_files = [f"  Checked: {video_file.parent / fn}" for fn in filenames_to_try]
                checked_files.extend([f"  Checked: {subtitles_dir / fn}" for fn in filenames_to_try])
                if downloads_dir and downloads_dir.exists():
                    checked_files.extend([f"  Checked: {downloads_dir / fn}" for fn in filenames_to_try])
                for checked in checked_files:
                    log_callback(checked)
            continue
        
        if log_callback:
            log_callback(f"Processing: {video_file.name} ({resolution}p)")
            log_callback(f"  Subtitle: {srt_file.name} (found in {srt_location})")
            log_callback(f"  Output: {out_file.name}")
            if use_watermarks:
                log_callback(f"  Watermark: {Path(watermark_path).name}")
        
        # Video duration for ETA
        video_duration_seconds = get_video_duration_seconds(video_file)
        
        # Audio filter for multichannel
        audio_channels = get_audio_channels(video_file)
        audio_filter = None
        if audio_channels and audio_channels > 2:
            if log_callback:
                log_callback(f"  Audio: {audio_channels} channels detected, converting to stereo (2.0) for higher compatibility")
            # Downmix to stereo
            if audio_channels == 6:
                # 5.1 to stereo
                audio_filter = "pan=stereo|c0=0.5*c2+0.5*c0+0.3*c4|c1=0.5*c2+0.5*c1+0.3*c5"
            elif audio_channels >= 4:
                # 4+ channels downmix
                audio_filter = "pan=stereo|c0=0.5*c0+0.5*c2|c1=0.5*c1+0.5*c3"
            else:
                # 3 channels downmix
                audio_filter = "pan=stereo|c0=0.5*c0+0.5*c2|c1=0.5*c1+0.5*c2"
        
        # Build FFmpeg filter, escape path for filter
        def escape_subtitle_path_for_filter(p):
            s = str(p).replace("\\", "\\\\")
            # Escape colon for filter
            s = s.replace(":", "\\:")
            return s
        srt_path = escape_subtitle_path_for_filter(srt_file)
        ffmpeg_exe = (ffmpeg_path.strip() or "ffmpeg")
        if use_watermarks:
            if resolution == "720":
                filter_complex = (
                    f"[0:v]subtitles=filename={srt_path},"
                    f"scale=-2:{height}[scaled];"
                    f"[1:v]format=rgba,colorchannelmixer=aa=0.8[wm];"
                    f"[scaled][wm]overlay=W-w-10:H-h-10"
                )
            else:  # 1080p
                filter_complex = (
                    f"[0:v]subtitles=filename={srt_path},"
                    f"scale=-1:{height}[vsub];"
                    f"[1:v]format=rgba,colorchannelmixer=aa=0.8[wm];"
                    f"[vsub][wm]overlay=0:0[outv]"
                )
            cmd = [
                ffmpeg_exe, "-y",
                "-err_detect", "ignore_err",  # Ignore non-critical decoder errors
                "-fflags", "+discardcorrupt+genpts",  # Discard corrupt packets and generate PTS
                "-max_error_rate", "1.0",  # Allow up to 100% error rate (essentially ignore all errors)
                "-i", str(video_file),
                "-i", watermark_path,
                "-filter_complex", filter_complex,
                "-c:v", "libx264", "-preset", preset, "-crf", "20",
            ]
            # Add audio filter if needed
            if audio_filter:
                cmd.extend(["-af", audio_filter])
            cmd.extend(["-c:a", "aac", "-b:a", "128k", str(out_file)])
        else:
            # No watermark - just subtitles and resize
            filter_complex = (
                f"[0:v]subtitles=filename={srt_path},"
                f"scale=-2:{height}" if resolution == "720" else f"scale=-1:{height}"
            )
            cmd = [
                ffmpeg_exe, "-y",
                "-err_detect", "ignore_err",  # Ignore non-critical decoder errors
                "-fflags", "+discardcorrupt+genpts",  # Discard corrupt packets and generate PTS
                "-max_error_rate", "1.0",  # Allow up to 100% error rate (essentially ignore all errors)
                "-i", str(video_file),
                "-vf", filter_complex,
                "-c:v", "libx264", "-preset", preset, "-crf", "20",
            ]
            # Add audio filter if needed
            if audio_filter:
                cmd.extend(["-af", audio_filter])
            cmd.extend(["-c:a", "aac", "-b:a", "128k", str(out_file)])
        
        # Log the exact command being executed for debugging
        if log_callback:
            log_callback(f"  Running: {' '.join(cmd[:3])} ... [filter] ... {cmd[-1]}")
        
        # Stream FFmpeg output
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Read stderr
            error_lines = []
            last_progress_time = None
            current_time_seconds = None
            speed_multiplier = None
            
            while True:
                line = process.stderr.readline()
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                error_lines.append(line)
                
                # Parse FFmpeg progress output (format: frame=  123 fps= 25 q=28.0 size=    1024kB time=00:00:05.00 bitrate=1677.7kbits/s speed=1.0x)
                if "frame=" in line or "time=" in line:
                    # Extract useful progress info
                    progress_info = []
                    
                    # Parse time
                    if "time=" in line:
                        try:
                            time_part = [p for p in line.split() if "time=" in p][0]
                            time_val = time_part.split("=")[1].strip()
                            current_time_seconds = parse_ffmpeg_time(time_val)
                            if current_time_seconds is not None:
                                progress_info.append(f"time {time_val}")
                        except:
                            pass
                    
                    # Parse speed
                    if "speed=" in line:
                        try:
                            speed_part = [p for p in line.split() if "speed=" in p][0]
                            speed_val = speed_part.split("=")[1].strip().rstrip('x')
                            speed_multiplier = float(speed_val)
                            progress_info.append(f"speed {speed_val}x")
                        except:
                            pass
                    
                    # Parse frame (for display)
                    if "frame=" in line:
                        try:
                            frame_part = [p for p in line.split() if "frame=" in p][0]
                            frame_num = frame_part.split("=")[1].strip()
                            progress_info.append(f"frame {frame_num}")
                        except:
                            pass
                    
                    # Calculate percentage and ETA
                    percentage = None
                    eta_str = None
                    
                    if video_duration_seconds and current_time_seconds is not None:
                        percentage = min(100, max(0, (current_time_seconds / video_duration_seconds) * 100))
                        
                        if speed_multiplier and speed_multiplier > 0:
                            remaining_time = (video_duration_seconds - current_time_seconds) / speed_multiplier
                            eta_str = format_eta(remaining_time)
                        else:
                            eta_str = "Calculating..."
                    
                    # Update progress callback more frequently during processing
                    current_time = time.time()
                    should_update = (last_progress_time is None or (current_time - last_progress_time) >= 2.0)
                    
                    # Update time tracking
                    if should_update:
                        last_progress_time = current_time
                    
                    # Update progress callback with enhanced filename including percentage
                    # (No text logging - only visual progress bar updates)
                    if progress_callback and should_update and percentage is not None:
                        # Include percentage in filename for display
                        enhanced_filename = f"{video_file.name} ({percentage:.1f}%)"
                        progress_callback(idx, total, enhanced_filename)
                
                elif "Error" in line or "error" in line.lower() or "failed" in line.lower():
                    # Skip eac3/ac3 decoder packet submission errors (we handle these gracefully)
                    if "Error submitting packet to decoder" in line and ("/eac3 @" in line or "/ac3 @" in line):
                        continue
                    # Log other errors immediately
                    if log_callback:
                        log_callback(f"    ⚠ {line}")
            
            # Wait for process
            returncode = process.wait()
            
            if returncode == 0 and out_file.exists():
                success_count += 1
                if log_callback:
                    log_callback(f"  ✓ Successfully created: {out_file.name}")
            else:
                if log_callback:
                    log_callback(f"  ✗ Failed to process: {video_file.name}")
                    log_callback(f"    Return code: {returncode}")
                    if error_lines:
                        # Show full error output (not just first 300 chars)
                        log_callback(f"    FFmpeg errors:")
                        for err_line in error_lines[-10:]:  # Show last 10 error lines
                            log_callback(f"      {err_line}")
        
        except Exception as e:
            if log_callback:
                log_callback(f"  ✗ Exception while processing {video_file.name}: {e}")
                log_callback(f"    Traceback: {traceback.format_exc()}")
    
    if log_callback:
        log_callback(f"\nProcessing complete. Created {success_count}/{total} files.")
    
    return success_count > 0


def analyze_tracks(video_path: Path, log_callback=None) -> Dict:
    """Analyze video file tracks using mkvmerge or ffprobe.
    
    Args:
        video_path: Path to video file
        log_callback: Optional callback for logging
    
    Returns:
        Dictionary with track info: {
            'video': [{'track_id': int, 'codec': str, 'resolution': str, ...}],
            'audio': [{'track_id': int, 'codec': str, 'channels': int, 'sample_rate': int, 'language': str, ...}],
            'subtitles': [{'track_id': int, 'codec': str, 'language': str, ...}]
        }
    """
    tracks = {'video': [], 'audio': [], 'subtitles': []}
    
    if not video_path.exists():
        if log_callback:
            log_callback(f"Error: File not found: {video_path}")
        return tracks
    
    try:
        # Use ffprobe for all formats - track_id must be FFmpeg stream index for remux -map to work.
        # (mkvmerge track IDs differ from FFmpeg stream indices and would cause remux failures.)
        ffprobe_exe = get_ffprobe_command()
        cmd = [
            ffprobe_exe, '-v', 'quiet', '-print_format', 'json',
            '-show_streams', str(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            
            for stream in data.get('streams', []):
                stream_type = stream.get('codec_type', '')
                track_info = {
                    'track_id': stream.get('index', 0),
                    'codec': stream.get('codec_name', 'unknown'),
                    'language': stream.get('tags', {}).get('language', 'unknown'),
                }
                
                if stream_type == 'video':
                    width = stream.get('width', 0)
                    height = stream.get('height', 0)
                    if width and height:
                        track_info['resolution'] = f"{width}x{height}"
                    tracks['video'].append(track_info)
                    
                elif stream_type == 'audio':
                    channels = stream.get('channels', 0)
                    sample_rate = stream.get('sample_rate', 0)
                    track_info['channels'] = channels
                    track_info['sample_rate'] = sample_rate
                    tracks['audio'].append(track_info)
                    
                elif stream_type == 'subtitle':
                    codec = stream.get('codec_name', 'unknown')
                    # Determine format
                    if codec == 'subrip' or codec == 'srt':
                        track_info['format'] = 'SRT'
                    elif codec == 'webvtt' or codec == 'vtt':
                        track_info['format'] = 'VTT'
                    else:
                        track_info['format'] = codec.upper()
                    tracks['subtitles'].append(track_info)
        
        return tracks
        
    except Exception as e:
        if log_callback:
            log_callback(f"Error analyzing tracks: {e}")
        return tracks


def split_audio_channels(video_path: Path, output_dir: Path, 
                        channel_count: int, log_callback=None) -> bool:
    """Extract individual audio channels from video.
    
    Args:
        video_path: Path to video file
        output_dir: Directory to save extracted channel files
        channel_count: Number of channels detected (1-6 or more)
        log_callback: Optional callback for logging
    
    Returns:
        True if successful, False otherwise
    """
    if not video_path.exists():
        if log_callback:
            log_callback(f"Error: File not found: {video_path}")
        return False
    
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = video_path.stem
    success_count = 0
    
    try:
        # Extract audio first, then split channels
        temp_audio = output_dir / f"{base_name}_temp_audio.wav"
        
        # First extract audio to WAV
        cmd_extract = [
            'ffmpeg', '-i', str(video_path),
            '-vn', '-acodec', 'pcm_s16le', '-ar', '48000',
            '-y', str(temp_audio)
        ]
        
        result = subprocess.run(cmd_extract, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            if log_callback:
                log_callback(f"Error extracting audio: {result.stderr}")
            return False
        
        # Now split into individual channels
        for channel in range(channel_count):
            channel_num = channel + 1  # 1-indexed
            output_file = output_dir / f"{base_name}_channel_{channel_num}.wav"
            
            # Extract individual channel using pan filter
            # pan=mono|c0=c{channel} extracts channel {channel} to mono output
            cmd_split = [
                'ffmpeg', '-i', str(temp_audio),
                '-af', f'pan=mono|c0=c{channel}',
                '-y', str(output_file)
            ]
            
            result = subprocess.run(cmd_split, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and output_file.exists():
                success_count += 1
                if log_callback:
                    log_callback(f"  ✓ Extracted channel {channel_num}: {output_file.name}")
            else:
                if log_callback:
                    log_callback(f"  ✗ Failed to extract channel {channel_num}")
        
        # Clean up temp file
        if temp_audio.exists():
            temp_audio.unlink()
        
        return success_count > 0
        
    except Exception as e:
        if log_callback:
            log_callback(f"Error splitting audio channels: {e}")
        return False


def convert_audio_format(video_path: Path, output_path: Path,
                        target_format: str, log_callback=None) -> bool:
    """Convert audio track to target format (MP3, AAC, etc.).
    
    Args:
        video_path: Path to input video file
        output_path: Path to output file
        target_format: 'mp3', 'aac', or 'keep'
        log_callback: Optional callback for logging
    
    Returns:
        True if successful, False otherwise
    """
    if target_format == 'keep':
        return True  # No conversion needed
    
    if not video_path.exists():
        if log_callback:
            log_callback(f"Error: File not found: {video_path}")
        return False
    
    try:
        if target_format == 'mp3':
            cmd = [
                'ffmpeg', '-i', str(video_path),
                '-vn', '-acodec', 'libmp3lame', '-b:a', '192k',
                '-ar', '44100', '-y', str(output_path)
            ]
        elif target_format == 'aac':
            cmd = [
                'ffmpeg', '-i', str(video_path),
                '-vn', '-acodec', 'aac', '-b:a', '192k',
                '-ar', '48000', '-y', str(output_path)
            ]
        else:
            if log_callback:
                log_callback(f"Error: Unsupported format: {target_format}")
            return False
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0 and output_path.exists():
            if log_callback:
                log_callback(f"  ✓ Converted to {target_format.upper()}: {output_path.name}")
            return True
        else:
            if log_callback:
                log_callback(f"  ✗ Conversion failed: {result.stderr}")
            return False
            
    except Exception as e:
        if log_callback:
            log_callback(f"Error converting audio: {e}")
        return False


def remux_mkv_with_srt_batch(folder_path: Path, output_format: str = "mkv", 
                             progress_callback=None, log_callback=None) -> bool:
    """Batch remux video files (MKV/MP4) with matching subtitle files (SRT/VTT).
    
    Args:
        folder_path: Folder containing video and subtitle files
        output_format: Output format ("mkv" or "mp4")
        progress_callback: Optional callback for progress updates
        log_callback: Optional callback for logging (minimal - errors only)
    """
    if not folder_path.exists():
        if log_callback:
            log_callback(f"Error: Folder not found: {folder_path}")
        return False
    
    # Find video files (MKV and MP4)
    video_files = sorted(list(folder_path.glob("*.mkv")) + list(folder_path.glob("*.mp4")))
    
    if not video_files:
        if log_callback:
            log_callback("Error: No MKV or MP4 files found in folder.")
        return False
    
    success_count = 0
    total = len(video_files)
    errors = []
    
    for idx, video_file in enumerate(video_files, start=1):
        base = video_file.stem
        # Try to find matching subtitle file (SRT or VTT)
        # First try exact match, then try without _01, _02 suffixes (LosslessCut scenes)
        srt_file = folder_path / f"{base}.srt"
        vtt_file = folder_path / f"{base}.vtt"
        subtitle_file = None
        subtitle_format = None
        
        if srt_file.exists():
            subtitle_file = srt_file
            subtitle_format = "srt"
        elif vtt_file.exists():
            subtitle_file = vtt_file
            subtitle_format = "vtt"
        else:
            # Try without _01, _02 suffixes
            base_clean = re.sub(r'_(\d+)$', '', base)
            srt_file = folder_path / f"{base_clean}.srt"
            vtt_file = folder_path / f"{base_clean}.vtt"
            if srt_file.exists():
                subtitle_file = srt_file
                subtitle_format = "srt"
            elif vtt_file.exists():
                subtitle_file = vtt_file
                subtitle_format = "vtt"
        
        if progress_callback:
            progress_callback(idx, total, video_file.name)
        
        if not subtitle_file or not subtitle_file.exists():
            errors.append(f"{video_file.name}: no matching SRT/VTT file")
            continue
        
        # Determine output filename
        output_ext = output_format.lower()
        output_file = folder_path / f"{base}_remuxed.{output_ext}"
        
        if output_file.exists():
            # Skip silently - no log needed
            continue
        
        # Build FFmpeg command
        ffmpeg_exe = get_ffmpeg_command()
        cmd = [
            ffmpeg_exe, "-y",
            "-i", str(video_file),
            "-i", str(subtitle_file),
            "-c", "copy",
            "-c:s", subtitle_format,
        ]
        
        # Add output file
        cmd.append(str(output_file))
        
        # Run remux (minimal logging - only on error)
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=300
            )
            
            if result.returncode == 0 and output_file.exists():
                success_count += 1
            else:
                # Only log errors
                error_msg = result.stderr.split('\n')[-10:] if result.stderr else ["Unknown error"]
                errors.append(f"{video_file.name}: {'; '.join(error_msg)}")
        
        except subprocess.TimeoutExpired:
            errors.append(f"{video_file.name}: timeout")
        except Exception as e:
            errors.append(f"{video_file.name}: {str(e)}")
    
    # Minimal logging - only show errors if any
    if errors and log_callback:
        log_callback("Remux errors:")
        for error in errors:
            log_callback(f"  ✗ {error}")
    
    # Success summary (one line)
    if log_callback and success_count > 0:
        log_callback(f"✓ Remuxed {success_count}/{total} files")
    
    return success_count > 0


def _get_whisper_python(log_callback=None) -> Optional[Path]:
    """Return Path to Python in ~/whisper-env, creating venv and installing whisper/torch if missing."""
    env_dir = Path.home() / "whisper-env"
    if sys.platform == "win32":
        python_exe = env_dir / "Scripts" / "python.exe"
    else:
        python_exe = env_dir / "bin" / "python"

    if not env_dir.exists():
        if log_callback:
            log_callback("Creating virtual environment...")
        try:
            subprocess.run(
                [sys.executable, "-m", "venv", str(env_dir)],
                check=True,
                capture_output=True,
                timeout=120,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            if log_callback:
                log_callback(f"Failed to create whisper-env: {e}")
            return None

    if not python_exe.exists():
        if log_callback:
            log_callback(f"whisper-env Python not found at {python_exe}")
        return None

    # Ensure whisper is installed
    try:
        result = subprocess.run(
            [str(python_exe), "-m", "whisper", "--help"],
            capture_output=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise RuntimeError("whisper not available")
    except Exception:
        if log_callback:
            log_callback("Installing Whisper (first time setup)...")
        try:
            subprocess.run(
                [str(python_exe), "-m", "pip", "install", "-U", "pip"],
                capture_output=True,
                timeout=60,
            )
            subprocess.run(
                [str(python_exe), "-m", "pip", "install", "-U", "openai-whisper"],
                check=True,
                capture_output=True,
                timeout=300,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            if log_callback:
                log_callback(f"Failed to install Whisper: {e}")
            return None

    # Ensure torch is installed
    try:
        result = subprocess.run(
            [str(python_exe), "-c", "import torch"],
            capture_output=True,
            timeout=15,
        )
        if result.returncode != 0:
            raise RuntimeError("torch not available")
    except Exception:
        if log_callback:
            log_callback("Installing PyTorch (first time setup)...")
        try:
            subprocess.run(
                [str(python_exe), "-m", "pip", "install", "torch", "torchvision", "torchaudio"],
                check=True,
                capture_output=True,
                timeout=600,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            if log_callback:
                log_callback(f"Failed to install PyTorch: {e}")
            return None

    return python_exe


def _get_whisper_cpp_binary(config: Dict) -> Optional[Path]:
    """Resolve Whisper CPP executable. Config whisper_cpp_path overrides; else check PATH."""
    user_path = (config.get("whisper_cpp_path") or "").strip()
    if user_path:
        p = Path(user_path).expanduser()
        if p.is_file():
            return p.resolve()
        if p.is_dir():
            exe = p / ("whisper-cli.exe" if os.name == "nt" else "whisper-cli")
            if exe.exists():
                return exe.resolve()
            main_exe = p / ("main.exe" if os.name == "nt" else "main")
            if main_exe.exists():
                return main_exe.resolve()
    def _is_whisper_cpp(bin_path: Path) -> bool:
        """Check if binary is whisper.cpp (not Python openai-whisper)."""
        try:
            r = subprocess.run(
                [str(bin_path), "-h"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            out = (r.stdout or "") + (r.stderr or "")
            # Python whisper has --output_format; reject it
            if "output_format" in out:
                return False
            # Original whisper.cpp has --vad and -f; pip whisper.cpp-cli has -m and -f
            return ("-f" in out or "--file" in out) and (
                "--vad" in out or "-m" in out or "--model" in out
            )
        except Exception:
            return False

    # Check Python venv first
    for exe_dir in [
        Path(sys.executable).resolve().parent,
        Path(__file__).resolve().parent / ".venv" / ("Scripts" if os.name == "nt" else "bin"),
        Path(__file__).resolve().parent / "venv" / ("Scripts" if os.name == "nt" else "bin"),
    ]:
        if not exe_dir.exists():
            continue
        for name in ("whisper-cpp", "whisper-cli", "main", "whisper"):
            candidate = exe_dir / (name + (".exe" if os.name == "nt" else ""))
            if candidate.exists() and _is_whisper_cpp(candidate):
                return candidate

    for name in ("whisper-cpp", "whisper-cli", "main", "whisper"):
        found = shutil.which(name)
        if found:
            p = Path(found)
            if _is_whisper_cpp(p):
                return p
    return None


def transcribe_video_whisper_cpp(
    video_path: Path,
    language_code: str,
    model_name: str,
    progress_callback=None,
    log_callback=None,
) -> bool:
    """Transcribe video using Whisper CPP. Uses built-in VAD. Faster than Python Whisper."""
    if not video_path.exists():
        if log_callback:
            log_callback(f"Error: Video file not found: {video_path}")
        return False

    config = load_config()
    if not ffmpeg_installed(config):
        if log_callback:
            log_callback("Error: FFmpeg not found. Please install it and add to PATH.")
        return False

    binary = _get_whisper_cpp_binary(config)
    if not binary or not Path(binary).exists():
        if log_callback:
            log_callback(
                "Error: Whisper CPP binary not found. Install from https://github.com/ggerganov/whisper.cpp "
                "and set whisper_cpp_path in settings.json to the folder containing the binary."
            )
        return False

    model_filename = WHISPER_CPP_MODELS.get(model_name)
    if not model_filename:
        model_filename = f"ggml-{model_name}.bin" if not model_name.endswith(".bin") else model_name

    model_dir = (config.get("whisper_cpp_model_dir") or "").strip()
    if model_dir:
        model_path = Path(model_dir).expanduser() / model_filename
    else:
        # Try binary's folder first (e.g. whisper.cpp/build)
        base_dir = Path(binary).parent
        # Skip binary dir if it's a venv/bin (pip-installed whisper has no models there)
        if ".venv" in str(base_dir) or "venv" in str(base_dir) or base_dir.name == "bin":
            base_dir = None
        candidates = []
        if base_dir:
            candidates.extend([
                base_dir / "Models" / model_filename,
                base_dir / "models" / model_filename,
                base_dir / model_filename,
            ])
        # Common locations when binary is from pip/venv
        home = Path.home()
        candidates.extend([
            home / ".cache" / "whisper.cpp" / model_filename,
            home / ".cache" / "whisper.cpp" / "models" / model_filename,
            home / "whisper.cpp" / "models" / model_filename,
        ])
        model_path = None
        for c in candidates:
            if c.exists():
                model_path = c
                break
        if model_path is None:
            model_path = candidates[0]  # Use first for error message

    if not model_path.exists():
        download_url = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/{model_filename}"
        model_path.parent.mkdir(parents=True, exist_ok=True)
        if log_callback:
            log_callback(f"Model not found. Downloading {model_filename} (~{_whisper_cpp_model_size(model_filename)})...")
        try:
            last_pct = [-1]  # mutable to allow update in closure
            def _reporthook(block_num, block_size, total_size):
                if log_callback and total_size > 0:
                    pct = min(100, block_num * block_size * 100 // total_size)
                    if pct >= last_pct[0] + 10 or pct == 100:  # throttle to every 10%
                        last_pct[0] = pct
                        mb = (block_num * block_size) / (1024 * 1024)
                        total_mb = total_size / (1024 * 1024)
                        log_callback(f"Downloading model: {mb:.1f}/{total_mb:.1f} MB ({pct}%)")
            urlretrieve(download_url, model_path, reporthook=_reporthook)
        except Exception as e:
            if model_path.exists():
                try:
                    model_path.unlink()
                except OSError:
                    pass
            if log_callback:
                log_callback(f"Error: Failed to download model: {e}")
                log_callback(f"Manual download: {download_url}")
            return False
        if log_callback:
            log_callback("Download complete.")
    if not model_path.exists():
        return False

    try:
        if log_callback:
            log_callback(f"Starting Whisper CPP transcription: {video_path.name}")
            log_callback(f"Language: {language_code}, Model: {model_name}")

        video_dir = video_path.parent
        base_name = video_path.stem
        audio_stem = f"{base_name}_whisper_cpp"
        audio_path = video_dir / f"{audio_stem}.wav"

        existing = list(video_dir.glob(f"{audio_stem}*"))
        if existing:
            n = 1
            while (video_dir / f"{audio_stem}_{n}.wav").exists():
                n += 1
            audio_stem = f"{audio_stem}_{n}"
            audio_path = video_dir / f"{audio_stem}.wav"

        if log_callback:
            log_callback("Extracting audio (16kHz mono, volume=1.75)...")
        ffmpeg_exe = get_ffmpeg_command(config)
        ffmpeg_result = subprocess.run(
            [
                ffmpeg_exe, "-y", "-i", str(video_path),
                "-vn", "-ar", "16000", "-ac", "1", "-ab", "32k",
                "-af", "volume=1.75", "-f", "wav",
                str(audio_path), "-loglevel", "warning", "-hide_banner",
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if ffmpeg_result.returncode != 0:
            if log_callback:
                log_callback(f"FFmpeg error: {ffmpeg_result.stderr or ffmpeg_result.stdout}")
            return False

        if not audio_path.exists():
            if log_callback:
                log_callback("FFmpeg did not produce audio file.")
            return False

        output_stem = str(video_dir / base_name)

        # On macOS, Metal/GPU only works when ggml-metal.metal is next to the binary (built from source).
        # The standalone .metal file requires ggml-common.h etc.; downloading it alone fails at runtime.
        metal_dir = None
        if sys.platform == "darwin":
            binary_dir = Path(binary).parent
            metal_in_cwd = binary_dir / "ggml-metal.metal"
            if metal_in_cwd.exists():
                metal_dir = str(binary_dir)

        vad_args = []
        try:
            r = subprocess.run([str(binary), "-h"], capture_output=True, text=True, timeout=5)
            if "--vad" in ((r.stdout or "") + (r.stderr or "")):
                vad_args = ["--vad"]  # Pip whisper.cpp-cli doesn't support --vad; original does
        except Exception:
            pass
        subtitle_edit_args = ["-sow", "-bo", "3", "-bs", "2", "-nf"]
        cmd = [
            str(binary), "-m", str(model_path), "-f", str(audio_path),
            "-l", language_code if language_code != "auto" else "auto",
        ] + vad_args + subtitle_edit_args + ["--print-progress", "-osrt", "-of", output_stem]
        extra_args = (config.get("whisper_cpp_extra_args") or "").strip()
        if extra_args:
            cmd.extend(extra_args.split())

        cwd = str(Path(binary).parent)

        def _run_whisper_streaming(cmd_args, cwd_path, extra_env=None):
            """Run whisper-cli, streaming stdout/stderr to log_callback in real-time.
            Returns (returncode, stderr_text) for CPU fallback check.
            """
            env = os.environ.copy()
            if extra_env:
                env.update(extra_env)
            proc = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd_path,
                bufsize=1,
                env=env,
            )
            stderr_lines = []

            def read_out(stream):
                for line in iter(stream.readline, ""):
                    if log_callback:
                        log_callback(line.rstrip())

            def read_err(stream):
                for line in iter(stream.readline, ""):
                    stderr_lines.append(line)
                    if log_callback:
                        log_callback(line.rstrip())

            t_out = threading.Thread(target=read_out, args=(proc.stdout,))
            t_err = threading.Thread(target=read_err, args=(proc.stderr,))
            t_out.daemon = True
            t_err.daemon = True
            t_out.start()
            t_err.start()
            try:
                proc.wait(timeout=3600)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                if log_callback:
                    log_callback("Transcription timed out.")
                return -1, "".join(stderr_lines)
            t_out.join(timeout=1)
            t_err.join(timeout=1)
            return proc.returncode, "".join(stderr_lines)

        extra_env = {"GGML_METAL_PATH_RESOURCES": metal_dir} if metal_dir else None
        if log_callback:
            log_callback("Transcribing with Whisper CPP...")
        returncode, stderr_text = _run_whisper_streaming(cmd, cwd, extra_env)

        # CPU fallback: if GPU/Metal init failed, retry with --no-gpu (important for CPU-only laptops)
        if returncode != 0 and "-ng" not in cmd and "--no-gpu" not in cmd:
            stderr_lower = (stderr_text or "").lower()
            gpu_error = (
                "ggml-metal" in stderr_lower or "ggml_metal" in stderr_lower
                or ("metal" in stderr_lower and ("error" in stderr_lower or "not found" in stderr_lower or "could not" in stderr_lower))
                or ("cuda" in stderr_lower and ("error" in stderr_lower or "not found" in stderr_lower))
            )
            if gpu_error and log_callback:
                log_callback("GPU init failed, retrying with CPU (--no-gpu)...")
            if gpu_error:
                cmd_fallback = cmd + ["-ng"]
                returncode, _ = _run_whisper_streaming(cmd_fallback, cwd, extra_env)

        final_srt = video_dir / f"{base_name}.srt"
        if final_srt.exists():
            n = 1
            while (video_dir / f"{base_name}_{n}.srt").exists():
                n += 1
            final_srt = video_dir / f"{base_name}_{n}.srt"

        whisper_srt = Path(output_stem + ".srt")
        if whisper_srt.exists():
            shutil.move(str(whisper_srt), str(final_srt))
        if audio_path.exists():
            try:
                audio_path.unlink()
            except OSError:
                pass

        if returncode == 0 and final_srt.exists():
            if log_callback:
                log_callback(f"✓ Transcription complete: {final_srt.name}")
            return True

        if log_callback:
            log_callback(f"Transcription failed with exit code {returncode}")
        return False

    except subprocess.TimeoutExpired:
        if log_callback:
            log_callback("Transcription timed out.")
        return False
    except Exception as e:
        if log_callback:
            log_callback(f"Error during transcription: {e}")
        return False


def transcribe_video(video_path: Path, language_code: str, model: str, whisper_options: Dict = None, output_format: str = "srt", progress_callback=None, log_callback=None) -> bool:
    """Transcribe video using Python + whisper (cross-platform, no bash required)."""
    if not video_path.exists():
        if log_callback:
            log_callback(f"Error: Video file not found: {video_path}")
        return False

    if not ffmpeg_installed():
        if log_callback:
            log_callback("Error: FFmpeg not found. Please install it and add to PATH.")
        return False

    whisper_python = _get_whisper_python(log_callback)
    if not whisper_python:
        if log_callback:
            log_callback("Error: Could not set up Whisper environment.")
        return False

    try:
        if log_callback:
            log_callback(f"Starting transcription of: {video_path.name}")
            log_callback(f"Language: {language_code}, Model: {model}, Format: {output_format}")

        video_dir = video_path.parent
        base_name = video_path.stem
        audio_stem = f"{base_name}_converted"
        audio_path = video_dir / f"{audio_stem}.wav"

        # Handle existing outputs (numbered suffix like whisper_auto.sh)
        existing = list(video_dir.glob(f"{audio_stem}*"))
        if existing:
            n = 1
            while (video_dir / f"{audio_stem}_{n}.wav").exists():
                n += 1
            audio_stem = f"{audio_stem}_{n}"
            audio_path = video_dir / f"{audio_stem}.wav"
            if log_callback:
                log_callback(f"Existing outputs found, using new stem: {audio_stem}")

        if log_callback:
            log_callback("Extracting and normalizing audio...")
        ffmpeg_exe = get_ffmpeg_command()
        ffmpeg_result = subprocess.run(
            [
                ffmpeg_exe, "-y", "-i", str(video_path),
                "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", "-af", "dynaudnorm",
                str(audio_path), "-loglevel", "warning", "-hide_banner",
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if ffmpeg_result.returncode != 0:
            if log_callback:
                log_callback(f"FFmpeg error: {ffmpeg_result.stderr or ffmpeg_result.stdout}")
            return False

        if not audio_path.exists():
            if log_callback:
                log_callback("FFmpeg did not produce audio file.")
            return False

        if log_callback:
            log_callback("Transcribing with Whisper...")
        whisper_cmd = [
            str(whisper_python), "-m", "whisper", str(audio_path),
            "--model", model,
            "--fp16", "False",
            "--output_format", output_format,
            "--beam_size", "2",
            "--output_dir", str(video_dir),
        ]
        if language_code and language_code != "auto":
            whisper_cmd.extend(["--language", language_code])

        # Append user-provided extra arguments
        if whisper_options and "extra_args_parsed" in whisper_options:
            extra_args = whisper_options.get("extra_args_parsed", "").strip()
            if extra_args:
                whisper_cmd.extend(extra_args.split())

        result = subprocess.run(
            whisper_cmd,
            capture_output=True,
            text=True,
            timeout=3600,
        )

        if log_callback:
            if result.stdout:
                log_callback(result.stdout)
            if result.stderr:
                log_callback(result.stderr)

        whisper_srt = video_dir / f"{audio_stem}.srt"
        final_srt = video_dir / f"{base_name}.srt"
        if final_srt.exists():
            n = 1
            while (video_dir / f"{base_name}_{n}.srt").exists():
                n += 1
            final_srt = video_dir / f"{base_name}_{n}.srt"

        if whisper_srt.exists():
            shutil.move(str(whisper_srt), str(final_srt))
        if audio_path.exists():
            try:
                audio_path.unlink()
            except OSError:
                pass

        if result.returncode == 0 and final_srt.exists():
            if log_callback:
                log_callback(f"✓ Transcription complete: {final_srt.name}")
            return True

        if log_callback:
            log_callback(f"Transcription failed with exit code {result.returncode}")
        return False

    except subprocess.TimeoutExpired:
        if log_callback:
            log_callback("Transcription timed out.")
        return False
    except Exception as e:
        if log_callback:
            log_callback(f"Error during transcription: {e}")
        return False


def transcribe_video_vad(
    video_path: Path,
    language_code: str,
    model: str,
    progress_callback=None,
    log_callback=None,
) -> bool:
    """Transcribe a long video using Silero VAD + Whisper per segment to reduce hallucination.
    Best for files over ~5 minutes. Writes SRT next to the input file.
    Requires: torch, torchaudio, torchcodec, pysrt, openai-whisper (pip install torch torchaudio torchcodec pysrt openai-whisper).
    """
    from decimal import Decimal

    try:
        import torch
        import pysrt
    except ImportError as e:
        if log_callback:
            log_callback(f"Missing dependency: {e}. Install with: pip install torch torchaudio torchcodec pysrt openai-whisper")
        return False

    if not video_path.exists():
        if log_callback:
            log_callback(f"Error: Video file not found: {video_path}")
        return False

    SAMPLE_RATE = 16000
    MIN_SILENCE_GAP = 0.5
    MIN_SEGMENT_LEN = 1.0
    PADDING = 0.2
    MAX_SEGMENT_LEN = 30.0
    MAX_LINE_WIDTH = 42
    MAX_LINE_COUNT = 2

    workdir = video_path.parent / f".vad_work_{video_path.stem}"
    workdir.mkdir(exist_ok=True)
    audio_path = workdir / "audio.wav"

    try:
        if log_callback:
            log_callback("Extracting audio...")
        ffmpeg_exe = get_ffmpeg_command()
        subprocess.run(
            [
                ffmpeg_exe, "-y",
                "-i", str(video_path),
                "-ac", "1",
                "-ar", str(SAMPLE_RATE),
                "-vn",
                str(audio_path),
            ],
            check=True,
            capture_output=True,
        )

        if log_callback:
            log_callback("Loading Silero VAD...")
        vad_model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            trust_repo=True,
        )
        get_speech_timestamps, _, read_audio_fn, _, _ = utils
        wav = read_audio_fn(str(audio_path), sampling_rate=SAMPLE_RATE)
        speech_timestamps = get_speech_timestamps(wav, vad_model, sampling_rate=SAMPLE_RATE)

        if not speech_timestamps:
            if log_callback:
                log_callback("No speech segments detected.")
            return False

        segments_raw = [
            (ts["start"] / SAMPLE_RATE, ts["end"] / SAMPLE_RATE)
            for ts in speech_timestamps
        ]

        merged = []
        for start, end in segments_raw:
            if not merged:
                merged.append([start, end])
                continue
            prev_start, prev_end = merged[-1]
            if start - prev_end <= MIN_SILENCE_GAP and (end - prev_start) <= MAX_SEGMENT_LEN:
                merged[-1][1] = end
            else:
                merged.append([start, end])

        segments = []
        for start, end in merged:
            start = max(0, start - PADDING)
            end += PADDING
            if end - start >= MIN_SEGMENT_LEN:
                segments.append((start, end))

        total = len(segments)
        if log_callback:
            log_callback(f"Detected {total} speech segments. Transcribing...")

        all_subs = pysrt.SubRipFile()

        for i, (start, end) in enumerate(segments):
            if progress_callback:
                progress_callback(i + 1, total, f"seg_{i + 1}")
            if log_callback:
                log_callback(f"Transcribing segment {i + 1}/{total}...")

            seg_wav = workdir / f"seg_{i:04d}.wav"
            seg_srt = workdir / f"seg_{i:04d}.srt"
            duration = end - start

            subprocess.run(
                [
                    ffmpeg_exe, "-y",
                    "-ss", str(start),
                    "-t", str(duration),
                    "-i", str(audio_path),
                    "-ac", "1", "-ar", str(SAMPLE_RATE),
                    str(seg_wav),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )

            whisper_cmd = [
                "whisper",
                str(seg_wav),
                "--model", model,
                "--output_format", "srt",
                "--output_dir", str(workdir),
                "--fp16", "False",
                "--word_timestamps", "True",
                "--max_line_width", str(MAX_LINE_WIDTH),
                "--max_line_count", str(MAX_LINE_COUNT),
            ]
            if language_code != "auto":
                whisper_cmd += ["--language", language_code]

            result = subprocess.run(whisper_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                if log_callback:
                    log_callback(f"Whisper error for segment {i + 1}: {result.stderr or result.stdout}")
                continue

            if not seg_srt.exists():
                continue

            subs = pysrt.open(seg_srt)
            offset = Decimal(str(start))
            for sub in subs:
                sub.start.seconds = float(Decimal(sub.start.seconds) + offset)
                sub.end.seconds = float(Decimal(sub.end.seconds) + offset)
                all_subs.append(sub)

        all_subs.clean_indexes()
        output_srt = video_path.with_suffix(".srt")
        all_subs.save(output_srt, encoding="utf-8")

        if log_callback:
            log_callback(f"Done → {output_srt.name}")
        return True

    except subprocess.CalledProcessError as e:
        if log_callback:
            log_callback(f"FFmpeg/Whisper error: {e}")
        return False
    except Exception as e:
        if log_callback:
            log_callback(f"Error during VAD transcription: {e}")
            log_callback(traceback.format_exc())
        return False
    finally:
        if workdir.exists():
            try:
                shutil.rmtree(workdir)
            except OSError:
                pass


def adjust_srt_timestamps(srt_path: Path, offset_seconds: int) -> bool:
    """Adjust all timestamps in an SRT file by adding an offset.
    
    Args:
        srt_path: Path to the SRT file
        offset_seconds: Number of seconds to add to all timestamps
    
    Returns:
        True if successful, False otherwise
    """
    try:
        with open(srt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Regex to match SRT timestamps (e.g., 00:00:01,234 --> 00:00:05,678)
        timestamp_pattern = r'(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})'
        
        def add_offset(match):
            # Parse start time
            start_h, start_m, start_s, start_ms = map(int, [match.group(1), match.group(2), match.group(3), match.group(4)])
            # Parse end time
            end_h, end_m, end_s, end_ms = map(int, [match.group(5), match.group(6), match.group(7), match.group(8)])
            
            # Convert to total milliseconds
            start_total_ms = (start_h * 3600 + start_m * 60 + start_s) * 1000 + start_ms
            end_total_ms = (end_h * 3600 + end_m * 60 + end_s) * 1000 + end_ms
            
            # Add offset (convert seconds to milliseconds)
            start_total_ms += offset_seconds * 1000
            end_total_ms += offset_seconds * 1000
            
            # Convert back to hours, minutes, seconds, milliseconds
            def ms_to_time(total_ms):
                hours = total_ms // (3600 * 1000)
                total_ms %= (3600 * 1000)
                minutes = total_ms // (60 * 1000)
                total_ms %= (60 * 1000)
                seconds = total_ms // 1000
                milliseconds = total_ms % 1000
                return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
            
            start_str = ms_to_time(start_total_ms)
            end_str = ms_to_time(end_total_ms)
            
            return f"{start_str} --> {end_str}"
        
        # Replace all timestamps
        adjusted_content = re.sub(timestamp_pattern, add_offset, content)
        
        # Write back to file
        with open(srt_path, 'w', encoding='utf-8') as f:
            f.write(adjusted_content)
        
        return True
    except Exception as e:
        print(f"Error adjusting SRT timestamps: {e}")
        return False


# ============================================================================
# Worker Thread for Script Execution
# ============================================================================

class ScriptWorker(QThread):
    """Worker thread for running scripts without blocking UI."""
    finished = pyqtSignal(bool)
    log_message = pyqtSignal(str)
    progress_update = pyqtSignal(int, int, str)  # current, total, filename
    
    def __init__(self, script_func, *args, **kwargs):
        super().__init__()
        self.script_func = script_func
        self.args = args
        self.kwargs = kwargs
        self._stop_requested = False
    
    def stop(self):
        """Request the worker to stop."""
        self._stop_requested = True
        self.log_message.emit("⚠ Stop requested - cancelling operation...")
    
    def is_stop_requested(self):
        """Check if stop was requested."""
        return self._stop_requested
    
    def run(self):
        """Execute the script function."""
        def log_callback(msg):
            if not self._stop_requested:
                self.log_message.emit(msg)
        
        def progress_callback(current, total, filename):
            if not self._stop_requested:
                self.progress_update.emit(current, total, filename)
        
        self.kwargs['log_callback'] = log_callback
        self.kwargs['progress_callback'] = progress_callback
        try:
            result = self.script_func(*self.args, **self.kwargs)
            if self._stop_requested:
                self.log_message.emit("✗ Operation cancelled by user")
                self.finished.emit(False)
            else:
                self.finished.emit(result)
        except Exception as e:
            if not self._stop_requested:
                self.log_message.emit(f"Error: {e}")
            self.finished.emit(False)


class PipInstallWorker(QThread):
    """Worker thread for pip install without blocking UI."""
    finished = pyqtSignal(bool)
    log_message = pyqtSignal(str)
    
    def __init__(self, packages: List[str], parent=None):
        super().__init__(parent)
        self.packages = packages
    
    def run(self):
        try:
            self.log_message.emit(f"Installing: {' '.join(self.packages)}")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install"] + self.packages,
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode != 0:
                err = (result.stderr or result.stdout or "").strip()
                self.log_message.emit(f"pip install failed: {err}")
                self.log_message.emit("Try manually: python -m pip install " + " ".join(self.packages))
                self.finished.emit(False)
            else:
                self.log_message.emit("✓ Installation complete")
                self.finished.emit(True)
        except subprocess.TimeoutExpired:
            self.log_message.emit("Installation timed out")
            self.finished.emit(False)
        except Exception as e:
            self.log_message.emit(f"Error: {e}")
            self.finished.emit(False)


class BinaryInstallWorker(QThread):
    """Worker thread for downloading and installing FFmpeg or N_m3u8DL-RE."""
    finished = pyqtSignal(bool)
    log_message = pyqtSignal(str)

    def __init__(self, tool: str, add_to_path: bool = False, parent=None):
        super().__init__(parent)
        self.tool = tool  # "ffmpeg" or "n_m3u8dl"
        self.add_to_path = add_to_path

    def run(self):
        try:
            if self.tool == "ffmpeg":
                ok = self._install_ffmpeg()
            elif self.tool == "n_m3u8dl":
                ok = self._install_n_m3u8dl()
            else:
                self.log_message.emit(f"Unknown tool: {self.tool}")
                ok = False
            if ok and self.add_to_path:
                self._add_tools_to_path()
            self.finished.emit(ok)
        except Exception as e:
            self.log_message.emit(f"Error: {e}")
            import traceback
            self.log_message.emit(traceback.format_exc())
            self.finished.emit(False)

    def _install_ffmpeg(self) -> bool:
        if sys.platform == "win32":
            return self._install_ffmpeg_windows()
        elif sys.platform == "darwin":
            return self._install_ffmpeg_macos()
        else:
            self.log_message.emit("FFmpeg auto-install is not supported on this platform. Install manually.")
            return False

    def _install_ffmpeg_windows(self) -> bool:
        url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        self.log_message.emit("Downloading FFmpeg (essentials build, ~70 MB)...")
        tools_dir = _get_tools_dir() / "ffmpeg"
        tools_dir.mkdir(parents=True, exist_ok=True)
        archive = tools_dir / "ffmpeg.zip"
        try:
            last_pct = [-1]
            def _reporthook(block_num, block_size, total_size):
                if total_size and total_size > 0:
                    pct = min(100, block_num * block_size * 100 // total_size)
                    if pct >= last_pct[0] + 10 or pct == 100:
                        last_pct[0] = pct
                        self.log_message.emit(f"Downloading: {pct}%")
            urlretrieve(url, archive, reporthook=_reporthook)
            self.log_message.emit("Extracting...")
            with zipfile.ZipFile(archive, "r") as zf:
                for name in zf.namelist():
                    if "/bin/" in name or "\\bin\\" in name:
                        zf.extract(name, tools_dir)
            archive.unlink(missing_ok=True)
            extracted = list(tools_dir.iterdir())
            bin_src = None
            for d in extracted:
                if d.is_dir():
                    inner_bin = d / "bin"
                    if inner_bin.exists():
                        bin_src = inner_bin
                        break
            if bin_src and (bin_src / "ffmpeg.exe").exists():
                dest_bin = tools_dir / "bin"
                dest_bin.mkdir(exist_ok=True)
                for exe in ["ffmpeg.exe", "ffprobe.exe", "ffplay.exe"]:
                    src = bin_src / exe
                    if src.exists():
                        shutil.copy2(src, dest_bin / exe)
                for d in extracted:
                    if d.is_dir() and d != dest_bin:
                        shutil.rmtree(d, ignore_errors=True)
                config = load_config()
                config["ffmpeg_path"] = str((dest_bin / "ffmpeg.exe").resolve())
                save_config(config)
                self.log_message.emit("✓ FFmpeg installed")
                return True
            self.log_message.emit("Extraction did not produce expected bin/ffmpeg.exe")
            return False
        except Exception as e:
            self.log_message.emit(f"Failed: {e}")
            if archive.exists():
                archive.unlink(missing_ok=True)
            return False

    def _install_ffmpeg_macos(self) -> bool:
        brew = shutil.which("brew")
        if not brew:
            self.log_message.emit("Homebrew not found. Install from https://brew.sh then retry.")
            return False
        self.log_message.emit("Running: brew install ffmpeg")
        result = subprocess.run(
            [brew, "install", "ffmpeg"],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            self.log_message.emit(f"brew install failed: {err}")
            return False
        prefix_result = subprocess.run(
            [brew, "--prefix", "ffmpeg"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if prefix_result.returncode == 0 and prefix_result.stdout:
            ffmpeg_dir = Path(prefix_result.stdout.strip()) / "bin"
            ffmpeg_exe = ffmpeg_dir / "ffmpeg"
            if ffmpeg_exe.exists():
                config = load_config()
                config["ffmpeg_path"] = str(ffmpeg_exe.resolve())
                save_config(config)
                self.log_message.emit("✓ FFmpeg installed")
                return True
        self.log_message.emit("✓ FFmpeg installed (brew)")
        return True

    def _install_n_m3u8dl(self) -> bool:
        if sys.platform not in ("win32", "darwin"):
            self.log_message.emit("N_m3u8DL-RE auto-install is not supported on this platform.")
            return False
        machine = platform.machine().lower()
        if sys.platform == "win32":
            if "arm" in machine or "aarch" in machine:
                asset_pattern = "win-arm64"
            else:
                asset_pattern = "win-x64"
            ext = ".zip"
        else:
            if "arm" in machine or "aarch" in machine:
                asset_pattern = "osx-arm64"
            else:
                asset_pattern = "osx-x64"
            ext = ".tar.gz"
        self.log_message.emit(f"Fetching N_m3u8DL-RE releases (platform: {asset_pattern})...")
        try:
            with urlopen("https://api.github.com/repos/nilaoda/N_m3u8DL-RE/releases/latest", timeout=10) as r:
                data = json.loads(r.read().decode())
        except Exception as e:
            self.log_message.emit(f"Failed to fetch releases: {e}")
            return False
        assets = data.get("assets", [])
        download_url = None
        for a in assets:
            name = a.get("name", "")
            if asset_pattern in name and name.endswith(ext):
                download_url = a.get("browser_download_url")
                break
        if not download_url:
            self.log_message.emit(f"No asset found for {asset_pattern}")
            return False
        tools_dir = _get_tools_dir() / "n_m3u8dl-re"
        tools_dir.mkdir(parents=True, exist_ok=True)
        archive = tools_dir / ("n_m3u8dl.zip" if ext == ".zip" else "n_m3u8dl.tar.gz")
        try:
            self.log_message.emit("Downloading N_m3u8DL-RE...")
            last_pct = [-1]
            def _reporthook(block_num, block_size, total_size):
                if total_size and total_size > 0:
                    pct = min(100, block_num * block_size * 100 // total_size)
                    if pct >= last_pct[0] + 10 or pct == 100:
                        last_pct[0] = pct
                        self.log_message.emit(f"Downloading: {pct}%")
            urlretrieve(download_url, archive, reporthook=_reporthook)
            self.log_message.emit("Extracting...")
            if ext == ".zip":
                with zipfile.ZipFile(archive, "r") as zf:
                    zf.extractall(tools_dir)
            else:
                with tarfile.open(archive, "r:gz") as tf:
                    tf.extractall(tools_dir)
            archive.unlink(missing_ok=True)
            exe_name = "N_m3u8DL-RE.exe" if sys.platform == "win32" else "N_m3u8DL-RE"
            found = None
            for p in tools_dir.rglob(exe_name):
                if p.is_file():
                    found = p
                    break
            if found:
                if found.parent != tools_dir:
                    dest = tools_dir / exe_name
                    shutil.move(str(found), str(dest))
                config = load_config()
                config["n_m3u8dl_path"] = str((tools_dir / exe_name).resolve())
                save_config(config)
                self.log_message.emit("✓ N_m3u8DL-RE installed")
                return True
            self.log_message.emit("Extraction did not produce expected executable")
            return False
        except Exception as e:
            self.log_message.emit(f"Failed: {e}")
            if archive.exists():
                archive.unlink(missing_ok=True)
            return False

    def _add_tools_to_path(self):
        tools_dir = _get_tools_dir()
        dirs_to_add = []
        ff_bin = tools_dir / "ffmpeg" / "bin"
        if ff_bin.exists():
            dirs_to_add.append(str(ff_bin))
        nm_dir = tools_dir / "n_m3u8dl-re"
        if nm_dir.exists():
            dirs_to_add.append(str(nm_dir))
        if not dirs_to_add:
            return
        if sys.platform == "win32":
            for d in dirs_to_add:
                try:
                    current = os.environ.get("PATH", "")
                    new_path = d + os.pathsep + current
                    subprocess.run(["setx", "PATH", new_path], capture_output=True, timeout=5)
                    self.log_message.emit(f"Added to PATH (restart terminal to use): {d}")
                except Exception as e:
                    self.log_message.emit(f"Could not add to PATH: {e}")
        else:
            export = '\n'.join(f'export PATH="{d}:$PATH"' for d in dirs_to_add)
            shell_rc = Path.home() / ".zshrc"
            if not shell_rc.exists():
                shell_rc = Path.home() / ".bash_profile"
            try:
                with open(shell_rc, "a") as f:
                    f.write(f"\n# Added by Video Processing Studio\n{export}\n")
                self.log_message.emit(f"Added to {shell_rc}. Restart terminal or run: source {shell_rc}")
            except Exception as e:
                self.log_message.emit(f"Could not add to PATH: {e}")


# ============================================================================
# Setup Checking Functions
# ============================================================================

def check_python_package(package_name: str) -> bool:
    """Check if a Python package is installed."""
    try:
        __import__(package_name)
        return True
    except ImportError:
        return False


def check_command_exists(command: str) -> bool:
    """Check if a command-line program exists."""
    try:
        result = subprocess.run(
            ["which", command] if sys.platform != "win32" else ["where", command],
            capture_output=True,
            timeout=2
        )
        return result.returncode == 0
    except Exception:
        return False


def _get_tools_dir() -> Path:
    """Return the tools installation directory."""
    return Path.home() / "VideoProcessing" / "tools"


def get_ffmpeg_command(config: Optional[Dict] = None) -> str:
    """Return the ffmpeg executable path. Config path overrides; else check PATH."""
    if config is None:
        config = load_config()
    user_path = (config.get("ffmpeg_path") or "").strip()
    if user_path:
        p = Path(user_path).expanduser()
        if p.is_file() and p.exists():
            return str(p.resolve())
        if p.is_dir() and (p / "ffmpeg.exe").exists():
            return str((p / "ffmpeg.exe").resolve())
        if p.is_dir() and (p / "ffmpeg").exists():
            return str((p / "ffmpeg").resolve())
    if sys.platform == "win32":
        tools_bin = _get_tools_dir() / "ffmpeg" / "bin"
        exe = tools_bin / "ffmpeg.exe"
        if exe.exists():
            return str(exe.resolve())
    return shutil.which("ffmpeg") or "ffmpeg"


def get_ffprobe_command(config: Optional[Dict] = None) -> str:
    """Return the ffprobe executable path (same dir as ffmpeg)."""
    ffmpeg = get_ffmpeg_command(config)
    if ffmpeg in ("ffmpeg", "ffmpeg.exe"):
        return "ffprobe" if sys.platform != "win32" else "ffprobe.exe"
    ffmpeg_path = Path(ffmpeg)
    ffprobe_name = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
    ffprobe_path = ffmpeg_path.parent / ffprobe_name
    return str(ffprobe_path) if ffprobe_path.exists() else ("ffprobe" if sys.platform != "win32" else "ffprobe.exe")


def get_n_m3u8dl_command(config: Optional[Dict] = None) -> str:
    """Return the N_m3u8DL-RE executable path. Config path overrides; else check PATH."""
    if config is None:
        config = load_config()
    user_path = (config.get("n_m3u8dl_path") or "").strip()
    if user_path:
        p = Path(user_path).expanduser()
        if p.is_file() and p.exists():
            return str(p.resolve())
        if p.is_dir():
            exe = p / ("N_m3u8DL-RE.exe" if sys.platform == "win32" else "N_m3u8DL-RE")
            if exe.exists():
                return str(exe.resolve())
    tools_dir = _get_tools_dir() / "n_m3u8dl-re"
    if sys.platform == "win32":
        exe = tools_dir / "N_m3u8DL-RE.exe"
    else:
        exe = tools_dir / "N_m3u8DL-RE"
    if exe.exists():
        return str(exe.resolve())
    return shutil.which("N_m3u8DL-RE") or "N_m3u8DL-RE"


def ffmpeg_installed(config: Optional[Dict] = None) -> bool:
    """Check if ffmpeg is available (config path or PATH)."""
    cmd = get_ffmpeg_command(config)
    if cmd == "ffmpeg":
        return check_command_exists("ffmpeg")
    return Path(cmd).exists() if cmd else False


def n_m3u8dl_installed(config: Optional[Dict] = None) -> bool:
    """Check if N_m3u8DL-RE is available (config path or PATH)."""
    cmd = get_n_m3u8dl_command(config)
    if cmd == "N_m3u8DL-RE":
        return check_command_exists("N_m3u8DL-RE")
    return Path(cmd).exists() if cmd else False


def find_gst_command() -> Optional[str]:
    """Find the gst command, checking PATH and common venv locations."""
    # First try to find it in PATH
    try:
        result = subprocess.run(
            ["which", "gst"],
            capture_output=True,
            timeout=2
        )
        if result.returncode == 0:
            gst_path = result.stdout.decode().strip()
            if gst_path and Path(gst_path).exists():
                return gst_path
    except Exception:
        pass
    
    # Check common venv locations
    possible_paths = [
        Path(__file__).parent / "venv" / "bin" / "gst",
        Path.home() / "dna" / "venv" / "bin" / "gst",
        Path(__file__).parent.parent / "venv" / "bin" / "gst",
    ]
    
    for path in possible_paths:
        if path.exists():
            return str(path)
    
    # Try using shutil.which
    try:
        import shutil
        gst_path = shutil.which("gst")
        if gst_path and Path(gst_path).exists():
            return gst_path
    except Exception:
        pass
    
    # Try to run via Python module as fallback
    try:
        # Check gst module
        result = subprocess.run(
            [sys.executable, "-m", "gemini_srt_translator", "--help"],
            capture_output=True,
            timeout=2
        )
        if result.returncode == 0:
            # Run as module
            return f"{sys.executable} -m gemini_srt_translator"
    except Exception:
        pass
    
    return None


def get_app_executable(app_name: str) -> Optional[Path]:
    """Get the path to an application executable (cross-platform).
    
    Returns the path to the executable if found, None otherwise.
    """
    system = platform.system()
    
    # Define executable names and common paths per platform
    app_info = {
        "VLC": {
            "Darwin": {
                "app_paths": ["/Applications/VLC.app", str(Path.home() / "Applications/VLC.app")],
                "exe_name": None  # Use open -a for .app bundles
            },
            "Windows": {
                "exe_paths": [
                    "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe",
                    "C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe",
                ],
                "exe_name": "vlc"
            },
            "Linux": {
                "exe_paths": ["/usr/bin/vlc"],
                "exe_name": "vlc"
            }
        },
        "LosslessCut": {
            "Darwin": {
                "app_paths": ["/Applications/LosslessCut.app", str(Path.home() / "Applications/LosslessCut.app")],
                "exe_name": None
            },
            "Windows": {
                "exe_paths": [
                    str(Path.home() / "AppData/Local/Programs/LosslessCut/LosslessCut.exe"),
                    "C:\\Program Files\\LosslessCut\\LosslessCut.exe",
                    "C:\\Program Files\\LosslessCut-win32-x64\\LosslessCut.exe",
                ],
                "exe_name": "LosslessCut"
            },
            "Linux": {
                "exe_paths": [],
                "exe_name": "losslesscut"  # If installed via package manager
            }
        },
        "SubtitleEdit": {
            "Darwin": {
                "app_paths": [],  # Not commonly available on macOS
                "exe_name": None
            },
            "Windows": {
                "exe_paths": [
                    "C:\\Program Files\\Subtitle Edit\\SubtitleEdit.exe",
                    "C:\\Program Files (x86)\\Subtitle Edit\\SubtitleEdit.exe",
                ],
                "exe_name": "SubtitleEdit"
            },
            "Linux": {
                "exe_paths": [],
                "exe_name": "subtitleedit"
            }
        }
    }
    
    if app_name not in app_info:
        return None
    
    info = app_info[app_name].get(system, {})
    
    # On macOS, check for .app bundles first
    if system == "Darwin":
        for app_path in info.get("app_paths", []):
            if Path(app_path).exists():
                return Path(app_path)
    
    # Check common executable paths
    for exe_path in info.get("exe_paths", []):
        if Path(exe_path).exists():
            return Path(exe_path)
    
    # Check PATH
    exe_name = info.get("exe_name")
    if exe_name:
        found = shutil.which(exe_name)
        if found:
            return Path(found)
    
    return None


def check_app_exists(app_name: str) -> bool:
    """Check if a GUI application is installed (cross-platform)."""
    return get_app_executable(app_name) is not None


# ============================================================================
# Setup Wizard Dialog
# ============================================================================

class SetupWizard(QDialog):
    """First-time setup wizard - step by step."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to Video Processing Studio - Setup")
        self.setMinimumWidth(700)
        self.setMinimumHeight(550)
        self.config = load_config()
        self.current_step = 0
        self._start_fresh_checked = False
        
        # Installation status
        self.pyqt5_installed = check_python_package("PyQt5")
        self.gst_installed = find_gst_command() is not None  # Check for gst command, not Python package (pipx support)
        self.ffmpeg_installed = ffmpeg_installed(self.config)
        self.n_m3u8_installed = n_m3u8dl_installed(self.config)
        self.vlc_installed = check_app_exists("VLC")
        self.lossless_installed = check_app_exists("LosslessCut")
        self.subtitle_edit_installed = check_app_exists("SubtitleEdit")
        self.transcribe_long_installed = all(
            check_python_package(p) for p in ("torch", "torchaudio", "torchcodec", "pysrt")
        )
        self.whisper_cpp_installed = _get_whisper_cpp_binary(self.config) is not None
        
        self.want_batch_download = True
        self.want_translator = True
        self.want_transcribe_long = True
        self.all_required_installed = self._compute_all_required_installed()
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Title bar
        title_bar = QWidget()
        title_layout = QVBoxLayout()
        title = QLabel("Welcome to Video Processing Studio")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        subtitle = QLabel("Let's check your setup")
        subtitle.setFont(QFont("Arial", 11))
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        title_bar.setLayout(title_layout)
        layout.addWidget(title_bar)
        
        # Step indicator
        self.step_label = QLabel("Step 1 of 5")
        self.step_label.setFont(QFont("Arial", 9))
        self.step_label.setStyleSheet("color: #666;")
        layout.addWidget(self.step_label)
        
        # Stacked steps
        self.stacked = QStackedWidget()
        self.stacked.addWidget(self.create_welcome_step())
        self.stacked.addWidget(self.create_features_step())
        self.stacked.addWidget(self.create_required_step())
        self.stacked.addWidget(self.create_optional_step())
        self.stacked.addWidget(self.create_final_step())
        layout.addWidget(self.stacked)
        
        # Navigation buttons
        button_layout = QHBoxLayout()
        self.back_btn = QPushButton("← Back")
        self.back_btn.clicked.connect(self.previous_step)
        self.back_btn.setEnabled(False)
        self.skip_btn = QPushButton("Skip Setup")
        self.skip_btn.clicked.connect(self.skip_setup)
        self.next_btn = QPushButton("Next →")
        self.next_btn.clicked.connect(self.next_step)
        self.finish_btn = QPushButton("Finish")
        self.finish_btn.clicked.connect(self.complete_setup)
        self.finish_btn.setVisible(False)
        
        button_layout.addWidget(self.back_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.skip_btn)
        button_layout.addWidget(self.next_btn)
        button_layout.addWidget(self.finish_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.update_navigation()
    
    def _compute_all_required_installed(self) -> bool:
        """True if all required deps for selected features are installed."""
        if not self.pyqt5_installed or not self.ffmpeg_installed:
            return False
        if self.want_batch_download and not self.n_m3u8_installed:
            return False
        if self.want_translator and not self.gst_installed:
            return False
        if self.want_transcribe_long and not self.transcribe_long_installed:
            return False
        return True
    
    def showEvent(self, event):
        """On first show, check for existing setup and offer start fresh."""
        super().showEvent(event)
        if self._start_fresh_checked:
            return
        self._start_fresh_checked = True
        if not _has_existing_setup():
            return
        msg = QMessageBox(self)
        msg.setWindowTitle("Previous Installation Detected")
        msg.setText(
            "We detected a previous SP Workshop installation.\n\n"
            "Do you want to keep your current setup or start fresh with defaults?"
        )
        keep_btn = msg.addButton("Keep", QMessageBox.YesRole)
        fresh_btn = msg.addButton("Start fresh", QMessageBox.NoRole)
        msg.setDefaultButton(keep_btn)
        msg.exec_()
        if msg.clickedButton() == fresh_btn:
            config_path = get_config_path()
            backup_path = config_path.parent / "settings.json.bak"
            try:
                shutil.copy2(config_path, backup_path)
            except Exception as e:
                QMessageBox.warning(self, "Backup Failed", f"Could not backup config: {e}")
                return
            default_config = {
                "base_dir": str(Path.home() / "VideoProcessing"),
                "watermark_720p": str(Path.home() / "VideoProcessing" / "config" / "watermark_720p.png"),
                "watermark_1080p": str(Path.home() / "VideoProcessing" / "config" / "watermark_1080p.png"),
                "api_key": os.getenv("GST_API_KEY", ""),
                "api_keys": [],
                "download_resolution": "1080",
                "ffmpeg_preset": "medium",
                "ffmpeg_path": "",
                "n_m3u8dl_path": "",
                "setup_complete": False,
                "use_watermarks": True,
                "whisper_output_format": "srt",
                "use_iso639_suffixes": False,
                "whisper_options": {"extra_args": "", "extra_args_parsed": ""}
            }
            save_config(default_config)
            self.config = load_config()
    
    def create_features_step(self) -> QWidget:
        """Create feature selection step."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        title = QLabel("Which features do you plan to use?")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        def on_feature_changed():
            self.want_batch_download = self.batch_cb.isChecked()
            self.want_translator = self.translator_cb.isChecked()
            self.want_transcribe_long = self.transcribe_long_cb.isChecked()
            self.all_required_installed = self._compute_all_required_installed()
            if hasattr(self, "required_content"):
                self.required_content.setHtml(self.get_required_html())
            if hasattr(self, "install_buttons_layout"):
                self._refresh_install_buttons()
        
        self.batch_cb = QCheckBox("Batch download episodes (needs N_m3u8DL-RE)")
        self.batch_cb.setChecked(self.want_batch_download)
        self.batch_cb.stateChanged.connect(lambda: on_feature_changed())
        layout.addWidget(self.batch_cb)
        
        self.translator_cb = QCheckBox("Translate subtitles (needs gemini-srt-translator / gst)")
        self.translator_cb.setChecked(self.want_translator)
        self.translator_cb.stateChanged.connect(lambda: on_feature_changed())
        layout.addWidget(self.translator_cb)
        
        # QCheckBox doesn't support setWordWrap (Qt bug QTBUG-5370). Use checkbox + label combo.
        transcribe_row = QWidget()
        transcribe_row_layout = QHBoxLayout(transcribe_row)
        transcribe_row_layout.setContentsMargins(0, 0, 0, 0)
        transcribe_row_layout.setSpacing(8)

        self.transcribe_long_cb = QCheckBox()
        self.transcribe_long_cb.setChecked(self.want_transcribe_long)
        self.transcribe_long_cb.stateChanged.connect(lambda: on_feature_changed())

        transcribe_label = QLabel(
            "Transcribe long videos (files over ~5 min; needs torch, torchaudio, torchcodec, pysrt, openai-whisper — ~2–3 GB download)"
        )
        transcribe_label.setWordWrap(True)
        transcribe_label.setCursor(Qt.PointingHandCursor)

        def _on_transcribe_label_clicked(event):
            if event.button() == Qt.LeftButton:
                self.transcribe_long_cb.toggle()
        transcribe_label.mousePressEvent = _on_transcribe_label_clicked

        transcribe_row_layout.addWidget(self.transcribe_long_cb)
        transcribe_row_layout.addWidget(transcribe_label, 1)
        layout.addWidget(transcribe_row)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_welcome_step(self) -> QWidget:
        """Create welcome/intro step."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        info = QLabel("This wizard will help you check if everything is set up correctly.")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        if self.all_required_installed:
            status = QLabel("✓ All required components are already installed!")
            status.setStyleSheet("color: #00aa00; font-weight: bold; font-size: 12pt; padding: 10px;")
            layout.addWidget(status)
        else:
            status = QLabel("⚠ Some required components need to be installed.")
            status.setStyleSheet("color: #aa0000; font-weight: bold; font-size: 12pt; padding: 10px;")
            layout.addWidget(status)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_required_step(self) -> QWidget:
        """Create step showing required components."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        title = QLabel("Required Components")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        self.required_content = QTextBrowser()
        self.required_content.setOpenExternalLinks(True)
        self.required_content.setHtml(self.get_required_html())
        layout.addWidget(self.required_content)
        
        # Install buttons for missing pip packages
        self.install_buttons_layout = QHBoxLayout()
        self._refresh_install_buttons()
        layout.addLayout(self.install_buttons_layout)
        
        widget.setLayout(layout)
        return widget
    
    def _refresh_status_after_install(self):
        """Re-check installation status after pip or binary install."""
        self.config = load_config()
        self.gst_installed = find_gst_command() is not None
        self.ffmpeg_installed = ffmpeg_installed(self.config)
        self.n_m3u8_installed = n_m3u8dl_installed(self.config)
        self.transcribe_long_installed = all(
            check_python_package(p) for p in ("torch", "torchaudio", "torchcodec", "pysrt")
        )
        self.whisper_cpp_installed = _get_whisper_cpp_binary(self.config) is not None
        self.all_required_installed = self._compute_all_required_installed()
        self.required_content.setHtml(self.get_required_html())
        self._refresh_install_buttons()
    
    def _refresh_install_buttons(self):
        """Populate install buttons for missing pip packages and binaries."""
        while self.install_buttons_layout.count():
            item = self.install_buttons_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        if not self.ffmpeg_installed and sys.platform in ("win32", "darwin"):
            btn = QPushButton("Install FFmpeg")
            btn.clicked.connect(lambda: self._do_binary_install("ffmpeg"))
            self.install_buttons_layout.addWidget(btn)
        if self.want_batch_download and not self.n_m3u8_installed and sys.platform in ("win32", "darwin"):
            btn = QPushButton("Install N_m3u8DL-RE")
            btn.clicked.connect(lambda: self._do_binary_install("n_m3u8dl"))
            self.install_buttons_layout.addWidget(btn)
        if self.want_translator and not self.gst_installed:
            btn = QPushButton("Install gemini-srt-translator")
            btn.clicked.connect(lambda: self._do_pip_install(["gemini-srt-translator"]))
            self.install_buttons_layout.addWidget(btn)
        if self.want_transcribe_long and not self.transcribe_long_installed:
            btn = QPushButton("Install transcribe-long deps (~2–3 GB)")
            btn.clicked.connect(lambda: self._do_pip_install(
                ["torch", "torchaudio", "torchcodec", "pysrt", "openai-whisper"]
            ))
            self.install_buttons_layout.addWidget(btn)
        if not self.whisper_cpp_installed:
            btn = QPushButton("Install Whisper CPP")
            btn.clicked.connect(lambda: self._do_pip_install(["whisper.cpp-cli"]))
            self.install_buttons_layout.addWidget(btn)
    
    def _do_pip_install(self, packages: List[str]):
        """Run pip install in a worker and show progress."""
        if "torch" in packages:
            reply = QMessageBox.question(
                self,
                "Large Download",
                "This will download approximately 2–3 GB. Continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        dlg = QDialog(self)
        dlg.setWindowTitle("Installing...")
        dlg.setMinimumWidth(400)
        layout = QVBoxLayout()
        log = QTextEdit()
        log.setReadOnly(True)
        layout.addWidget(log)
        close_btn = QPushButton("Close")
        close_btn.setEnabled(False)
        layout.addWidget(close_btn)
        dlg.setLayout(layout)
        worker = PipInstallWorker(packages)
        worker.log_message.connect(lambda m: log.append(m))
        def on_finished(ok):
            if ok:
                dlg.accept()
                self._refresh_status_after_install()
            else:
                log.append("\nInstallation failed. Click Close, then run: python -m pip install " + " ".join(packages))
                close_btn.setEnabled(True)
        close_btn.clicked.connect(dlg.accept)
        worker.finished.connect(on_finished)
        worker.start()
        dlg.exec_()
    
    def _do_binary_install(self, tool: str):
        """Run binary install (FFmpeg or N_m3u8DL-RE) in a worker and show progress."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Install " + ("FFmpeg" if tool == "ffmpeg" else "N_m3u8DL-RE"))
        dlg.setMinimumWidth(450)
        layout = QVBoxLayout()
        add_to_path_cb = QCheckBox("Add to PATH so you can use from terminal")
        add_to_path_cb.setChecked(False)
        layout.addWidget(add_to_path_cb)
        log = QTextEdit()
        log.setReadOnly(True)
        layout.addWidget(log)
        install_btn = QPushButton("Install")
        close_btn = QPushButton("Close")
        close_btn.setEnabled(True)
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(install_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        dlg.setLayout(layout)

        def start_install():
            install_btn.setEnabled(False)
            close_btn.setEnabled(False)
            worker = BinaryInstallWorker(tool, add_to_path=add_to_path_cb.isChecked())
            worker.log_message.connect(lambda m: log.append(m))
            def on_finished(ok):
                if ok:
                    dlg.accept()
                    self._refresh_status_after_install()
                else:
                    log.append("\nInstallation failed. Try manual install (see links above).")
                    close_btn.setEnabled(True)
            worker.finished.connect(on_finished)
            worker.start()

        install_btn.clicked.connect(start_install)
        close_btn.clicked.connect(dlg.accept)
        dlg.exec_()
    
    def create_optional_step(self) -> QWidget:
        """Create step showing optional components."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        title = QLabel("Optional Components")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        info = QLabel("These programs enhance your workflow but aren't required. You can install them later if needed.")
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info)
        
        content = QTextBrowser()
        content.setOpenExternalLinks(True)
        content.setHtml(self.get_optional_html())
        layout.addWidget(content)
        
        widget.setLayout(layout)
        return widget
    
    def create_final_step(self) -> QWidget:
        """Create final step with API key and summary."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        title = QLabel("Almost Done!")
        title.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(title)
        
        # API Key section
        api_label = QLabel("Google Gemini API Key:")
        api_label.setFont(QFont("Arial", 11))
        layout.addWidget(api_label)
        
        api_info = QLabel(
            "Required for translating subtitles.\n\n"
            "Recommended: Set GEMINI_API_KEY or GST_API_KEY environment variable (most secure).\n"
            "See Settings for platform-specific instructions.\n\n"
            "Alternative: You can also set it in Settings (less secure, for backward compatibility)."
        )
        api_info.setWordWrap(True)
        api_info.setStyleSheet("color: #666;")
        layout.addWidget(api_info)
        
        # Check if environment variable is already set
        has_env_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GST_API_KEY"))
        checkbox_text = "I already have an API key set (or I'll set it up later)"
        if has_env_key:
            checkbox_text += " ✓ Environment variable detected"
        
        self.api_key_checkbox = QCheckBox(checkbox_text)
        self.api_key_checkbox.setChecked(has_env_key or bool(self.config.get("api_key", "")) or bool(self.config.get("api_keys")))
        layout.addWidget(self.api_key_checkbox)
        
        layout.addSpacing(10)
        
        # Summary
        summary_label = QLabel("Summary:")
        summary_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(summary_label)
        
        summary_text = QTextBrowser()
        summary_text.setOpenExternalLinks(True)
        summary_text.setHtml(self.get_summary_html())
        summary_text.setMaximumHeight(150)
        layout.addWidget(summary_text)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def get_required_html(self) -> str:
        """Generate HTML for required components (feature-aware)."""
        html = "<div style='line-height: 1.6;'>"
        
        html += "<h4 style='color: #df4300; margin-top: 10px;'>Core (always required):</h4>"
        html += f"<p><b>{'✓ INSTALLED' if self.pyqt5_installed else '✗ NOT FOUND'}</b> - PyQt5</p>"
        if not self.pyqt5_installed:
            html += "<p style='margin-left: 20px; color: #666;'>Install: <code>python -m pip install PyQt5</code></p>"
        
        html += f"<p><b>{'✓ INSTALLED' if self.ffmpeg_installed else '✗ NOT FOUND'}</b> - FFmpeg</p>"
        if not self.ffmpeg_installed:
            system = platform.system()
            if system == "Darwin":
                html += "<p style='margin-left: 20px; color: #666;'>Install: <code>brew install ffmpeg</code><br>"
                html += "If you don't have Homebrew: <a href='https://brew.sh'>Install Homebrew</a></p>"
            elif system == "Windows":
                html += "<p style='margin-left: 20px; color: #666;'>Download: <a href='https://www.gyan.dev/ffmpeg/builds/'>gyan.dev/ffmpeg</a><br>"
                html += "Extract and add the <code>bin</code> folder to your PATH</p>"
            else:
                html += "<p style='margin-left: 20px; color: #666;'>Install: <code>sudo apt install ffmpeg</code> (Debian/Ubuntu)<br>"
                html += "or <code>sudo dnf install ffmpeg</code> (Fedora)</p>"
        
        if self.want_batch_download:
            html += "<h4 style='color: #f48a32; margin-top: 15px;'>Batch Download:</h4>"
            html += f"<p><b>{'✓ INSTALLED' if self.n_m3u8_installed else '✗ NOT FOUND'}</b> - N_m3u8DL-RE</p>"
            if not self.n_m3u8_installed:
                html += "<p style='margin-left: 20px; color: #666;'>Download: <a href='https://github.com/nilaoda/N_m3u8DL-RE/releases'>GitHub Releases</a><br>"
                html += "Extract and add to PATH</p>"
        
        if self.want_translator:
            html += "<h4 style='color: #f48a32; margin-top: 15px;'>Translator:</h4>"
            html += f"<p><b>{'✓ INSTALLED' if self.gst_installed else '✗ NOT FOUND'}</b> - gemini-srt-translator</p>"
            if not self.gst_installed:
                html += "<p style='margin-left: 20px; color: #666;'>Install: <code>python -m pip install gemini-srt-translator</code></p>"
        
        if self.want_transcribe_long:
            html += "<h4 style='color: #f48a32; margin-top: 15px;'>Transcribe long videos (~2–3 GB download):</h4>"
            html += f"<p><b>{'✓ INSTALLED' if self.transcribe_long_installed else '✗ NOT FOUND'}</b> - torch, torchaudio, torchcodec, pysrt, openai-whisper</p>"
            if not self.transcribe_long_installed:
                html += "<p style='margin-left: 20px; color: #666;'>Install: <code>python -m pip install torch torchaudio torchcodec pysrt openai-whisper</code></p>"
        
        html += "<h4 style='color: #f48a32; margin-top: 15px;'>Transcribe (Whisper CPP, faster):</h4>"
        html += f"<p><b>{'✓ INSTALLED' if self.whisper_cpp_installed else '✗ NOT FOUND'}</b> - whisper.cpp-cli</p>"
        if not self.whisper_cpp_installed:
            html += "<p style='margin-left: 20px; color: #666;'>Install: <code>python -m pip install whisper.cpp-cli</code></p>"
        
        html += "</div>"
        return html
    
    def get_optional_html(self) -> str:
        """Generate HTML for optional components."""
        html = "<div style='line-height: 1.6;'>"
        
        html += f"<p><b>{'✓ INSTALLED' if self.vlc_installed else '○ OPTIONAL'}</b> - VLC (Media player)</p>"
        if not self.vlc_installed:
            html += "<p style='margin-left: 20px; color: #666;'>Download: <a href='https://www.videolan.org/vlc/'>videolan.org</a></p>"
        
        html += f"<p><b>{'✓ INSTALLED' if self.lossless_installed else '○ OPTIONAL'}</b> - LosslessCut</p>"
        if not self.lossless_installed:
            html += "<p style='margin-left: 20px; color: #666;'>Download: <a href='https://github.com/mifi/lossless-cut/releases'>GitHub Releases</a></p>"
        
        html += f"<p><b>{'✓ INSTALLED' if self.subtitle_edit_installed else '○ OPTIONAL'}</b> - Subtitle Edit</p>"
        if not self.subtitle_edit_installed:
            html += "<p style='margin-left: 20px; color: #666;'>Download: <a href='https://github.com/SubtitleEdit/subtitleedit/releases'>GitHub Releases</a></p>"
        
        html += "<p><b>○ OPTIONAL</b> - Browser extension for capturing download commands</p>"
        html += "<p style='margin-left: 20px; color: #666;'>See 'How to get commands' in the Download section for details</p>"
        
        html += "</div>"
        return html
    
    def get_summary_html(self) -> str:
        """Generate summary HTML."""
        html = "<div style='line-height: 1.6;'>"
        if self.all_required_installed:
            html += "<p style='color: #00aa00;'><b>✓ All required components are installed!</b></p>"
            html += "<p>You're ready to use the app. Optional components can be installed later if needed.</p>"
        else:
            missing = []
            if not self.pyqt5_installed:
                missing.append("PyQt5")
            if not self.ffmpeg_installed:
                missing.append("FFmpeg")
            if self.want_batch_download and not self.n_m3u8_installed:
                missing.append("N_m3u8DL-RE")
            if self.want_translator and not self.gst_installed:
                missing.append("gemini-srt-translator")
            if self.want_transcribe_long and not self.transcribe_long_installed:
                missing.append("torch, torchaudio, torchcodec, pysrt, openai-whisper")
            html += "<p style='color: #aa0000;'><b>⚠ Some required components are missing.</b></p>"
            html += "<p><b>Missing:</b> " + ", ".join(missing) + "</p>"
            html += "<p>Install from Step 3, or run <code>python -m pip install &lt;package&gt;</code> in your terminal. Then restart the app.</p>"
        html += "</div>"
        return html
    
    def next_step(self):
        """Move to next step."""
        if self.current_step < self.stacked.count() - 1:
            self.current_step += 1
            self.stacked.setCurrentIndex(self.current_step)
            self.update_navigation()
    
    def previous_step(self):
        """Move to previous step."""
        if self.current_step > 0:
            self.current_step -= 1
            self.stacked.setCurrentIndex(self.current_step)
            self.update_navigation()
    
    def update_navigation(self):
        """Update navigation buttons based on current step."""
        total_steps = self.stacked.count()
        self.step_label.setText(f"Step {self.current_step + 1} of {total_steps}")
        
        self.back_btn.setEnabled(self.current_step > 0)
        self.next_btn.setVisible(self.current_step < total_steps - 1)
        self.finish_btn.setVisible(self.current_step == total_steps - 1)
    
    def skip_setup(self):
        """Skip setup and mark as complete."""
        self.config["setup_complete"] = True
        self.config["last_setup_version"] = __version__
        save_config(self.config)
        self.reject()
    
    def complete_setup(self):
        """Complete setup and mark as done."""
        self.config["setup_complete"] = True
        self.config["last_setup_version"] = __version__
        save_config(self.config)
        self.accept()


# ============================================================================
# FAQ Dialog
# ============================================================================

class FAQDialog(QDialog):
    """FAQ dialog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FAQ")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        
        layout = QVBoxLayout()
        
        # FAQ content area
        faq_content = QTextEdit()
        faq_content.setReadOnly(True)
        faq_content.setFont(QFont("Arial", 13))
        faq_content.setHtml(self.get_faq_content())
        layout.addWidget(faq_content)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def get_faq_content(self) -> str:
        """Generate FAQ content as HTML."""
        return """
        <style>
        body { font-family: Arial, sans-serif; font-size: 13pt; line-height: 1.6; }
        h2 { font-size: 20pt; font-weight: bold; margin-bottom: 15px; }
        h3 { font-size: 16pt; font-weight: bold; margin-top: 20px; margin-bottom: 10px; }
        p { font-size: 13pt; margin-bottom: 15px; }
        b { font-weight: bold; }
        </style>
        <h2 style="color: #b42075;">Frequently Asked Questions</h2>
        
        <h3 style="color: #df4300;">Common Error Messages</h3>
        
        <p><b>"Error: No commands provided"</b><br>
        This means you tried to download but didn't paste any commands in the text box.
        Make sure you've copied your download commands and pasted them into the "Commands" area before clicking "Batch download".
        Click <b>How to get commands</b> in the Download section for instructions.</p>
        
        <p><b>"Error: API key not set"</b><br>
        You need to set up your Google Gemini API key to translate subtitles. Go to Settings and enter your API key in the "API Key" field. 
        You can get an API key from Google's Gemini API website.</p>
        
        <p><b>"Error: Watermark file not found"</b><br>
        You need to set up watermark images before processing videos. Go to Settings and browse for your watermark files 
        (one for 720p and one for 1080p). Make sure the file paths are correct.</p>
        
        <p><b>"Error: Downloads directory not found"</b><br>
        The app couldn't find or create the downloads folder. This usually fixes itself automatically, but if it persists, 
        try clicking "Open Downloads Folder" to create it manually.</p>
        
        <p><b>"Error: LosslessCut not found"</b><br>
        LosslessCut isn't installed on your computer. Download it here https://github.com/mifi/lossless-cut and install it 
        in your Applications folder, then try again.</p>
        
        <p><b>"✗ Failed" messages</b><br>
        These mean an operation failed for a specific file. Check the log output above the error message for more details 
        about what went wrong. Common causes: missing files, corrupted files, or permission issues.</p>
        
        <h3 style="color: #f48a32;">Files Being Skipped</h3>
        
        <p><b>"Skipping [file] - subtitle already exists"</b><br>
        This is normal! The app won't overwrite existing subtitle files to protect your work. If you want to re-extract subtitles, 
        delete the existing .srt file first, then try again.</p>
        
        <p><b>"Skipping [file] - output already exists"</b><br>
        The processed video file already exists in the output folder. The app skips it to avoid re-processing. 
        If you want to process it again, delete the existing file from the output folder first.</p>
        
        <p><b>"Skipping [file] - subtitle not found"</b><br>
        The app is trying to process a video but can't find a matching subtitle file. Make sure you've extracted and 
        (if needed) translated the subtitles first. The subtitle filename should match the video filename (e.g., "episode.mkv" 
        needs "episode.srt").</p>
        
        <p><b>"Skipping [file] - no matching SRT file found"</b><br>
        When remuxing, the app looks for an SRT file with the same name as your MKV file. Make sure both files are in the same folder 
        and have matching names (e.g., "video.mkv" and "video.srt").</p>
        
        <p><b>"Skipping invalid line"</b><br>
        Your download command isn't in the right format. Commands should look like: 
        "Episode 1: N_m3u8DL-RE [your command here]". Make sure each line starts with "Episode [number]:" followed by your command.</p>
        
        <h3 style="color: #ffab68;">Operations Not Working</h3>
        
        <p><b>"Operation failed. Check log for details"</b><br>
        Look at the log output above this message. It will tell you which file failed and why. Common issues: missing files, 
        wrong file formats, or permission problems. Scroll up in the log to see the specific error.</p>
        
        <p><b>"Another operation is already running"</b><br>
        You can only run one operation at a time. Wait for the current operation to finish (check the progress bar and status bar), 
        then try again.</p>
        
        <p><b>Translation isn't working</b><br>
        Check these things: 1) Is your API key set in Settings? 2) Do you have internet connection? 3) Are there subtitle files 
        to translate? (Files ending in "_OG.srt" won't be translated - those are backups).</p>
        
        <p><b>Download didn't complete</b><br>
        Check your internet connection and make sure your download commands are correct. Look at the log output for specific error messages. 
        Sometimes the streaming service blocks downloads - this is normal and not something the app can fix.</p>
        
        <p><b>Video processing failed</b><br>
        Make sure: 1) Your watermark files are set up correctly in Settings, 2) The video files have matching subtitle files, 
        3) You have enough disk space. Check the log for the specific error message.</p>
        
        <h3 style="color: #dc7bb3;">Understanding the Log Output</h3>
        
        <p><b>What do the checkmarks (✓) and X marks (✗) mean?</b><br>
        ✓ means the operation succeeded for that file. ✗ means it failed. Always check the log after an operation to see which files 
        worked and which didn't.</p>
        
        <p><b>What does "Processing X/Y" mean in the status bar?</b><br>
        This shows your progress. X is the current file being processed, Y is the total number of files. For example, "Processing 3/10" 
        means you're on file 3 out of 10 total files.</p>
        
        <p><b>How do I read error messages in the log?</b><br>
        Error messages usually start with "Error:" or show "✗ Failed". Read the message after the colon or after "Failed:" - that's 
        what went wrong. Sometimes there's more detail on the next line.</p>
        
        <p><b>What does "Ready" vs "Error occurred" mean?</b><br>
        "Ready" means the app is waiting for you to do something. "Error occurred" means the last operation had problems. 
        Check the log output to see what went wrong.</p>
        
        <h3 style="color: #c46ea1;">Quick Fixes</h3>
        
        <p><b>How do I find my files when something goes wrong?</b><br>
        Use the "Open Folder" buttons! Click "Open Downloads Folder" to see downloaded videos, "Open Subtitles Folder" for subtitle files, 
        and "Open Output Folder" for processed videos. These buttons open Finder so you can see exactly where your files are.</p>
        
        <p><b>How do I configure my API key?</b><br>
        Click the "Settings" button in the top right. Enter your Google Gemini API key in the "API Key" field and click "Save". 
        You can get an API key from Google's Gemini API website.</p>
        
        <p><b>How do I set up watermark files?</b><br>
        Go to Settings and click "Browse..." next to "Watermark 720p" and "Watermark 1080p". Select your watermark image files. 
        Make sure they're PNG images. Click "Save" when done.</p>
        
        <p><b>What if I want to re-process a file that was skipped?</b><br>
        Delete the output file from the output folder first. Then run the processing operation again. The app will create a new file 
        instead of skipping it.</p>
        
        <p style="margin-top: 20px; color: #666; font-style: italic;">
        Still having issues? Check the log output carefully - it usually tells you exactly what went wrong. 
        Most problems are about missing files, wrong settings, or files that already exist.</p>
        """


# ============================================================================
# About Dialog
# ============================================================================

class AboutDialog(QDialog):
    """About dialog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setMinimumWidth(700)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        
        # About content area
        about_content = QTextEdit()
        about_content.setReadOnly(True)
        about_content.setFont(QFont("Arial", 13))
        about_content.setHtml(self.get_about_content())
        layout.addWidget(about_content)
        
        # Icon and Twitter link at bottom
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        # App icon
        icon_label = QLabel()
        icon = get_app_icon()
        if not icon.isNull():
            pixmap = icon.pixmap(64, 64)  # 64x64 icon size
            icon_label.setPixmap(pixmap)
        bottom_layout.addWidget(icon_label)
        
        bottom_layout.addSpacing(10)
        
        # Twitter link
        twitter_label = QLabel('<a href="https://x.com/slappepolsen">@slappepolsen</a>')
        twitter_label.setOpenExternalLinks(True)
        twitter_label.setFont(QFont("Arial", 11))
        bottom_layout.addWidget(twitter_label)
        
        bottom_layout.addStretch()
        layout.addLayout(bottom_layout)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def get_about_content(self) -> str:
        """Generate About content as HTML."""
        version = __version__
        return f"""
        <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; font-size: 13pt; line-height: 1.6; }}
        .app-name {{ font-size: 18pt; font-weight: 600; color: #b42075; margin-bottom: 4px; }}
        .version {{ font-size: 13pt; color: #666; margin-bottom: 16px; }}
        .creator {{ font-size: 13pt; color: #333; margin-bottom: 20px; }}
        .description {{ font-size: 13pt; color: #333; margin-bottom: 24px; line-height: 1.7; }}
        .footer {{ font-size: 12pt; color: #666; font-style: italic; margin-top: 24px; }}
        </style>
        <div style="padding: 24px;">
        <div class="app-name">Video Processing Studio</div>

        <div class="version">Version {version}</div>

        <div class="creator">
        <span style="color: #df4300; font-weight: 600;">Created by:</span> SLAPPEPOLSEN
        </div>
        
        <div class="description">
        This app wraps command-line scripts into a friendly GUI to make video processing 
        accessible and efficient. The whole point is to make WLW / sapphic / lesbian content 
        accessible for everyone in the world! Extracting subtitles, translating them, and 
        processing videos with burned-in subtitles and watermarks. All with way fewer clicks.
        </div>
        
        <div class="footer">
        Built with PyQt5 and a whole lot of automation love. 
        I love automation, and I want you to do as few clicks as possible, basically.
        </div>
        </div>
        """


# ============================================================================
# Language Selection Dialog
# ============================================================================

class LanguageDialog(QDialog):
    """Dialog for selecting language code for transcription."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Language")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Instructions
        info_label = QLabel("Select the language of the audio/video to transcribe:")
        layout.addWidget(info_label)
        
        # Language dropdown
        self.language_combo = QComboBox()
        for name, code in TRANSCRIBE_LANGUAGES:
            self.language_combo.addItem(name, code)
        
        # Set default to English
        default_index = self.language_combo.findData("en")
        if default_index >= 0:
            self.language_combo.setCurrentIndex(default_index)
        
        layout.addWidget(self.language_combo)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def get_language_code(self) -> str:
        """Get the selected language code."""
        return self.language_combo.currentData()


class MediaInfoDialog(QDialog):
    """Dialog showing detailed media information for a video file."""
    
    def __init__(self, parent=None, video_path: Path = None):
        super().__init__(parent)
        self.video_path = video_path
        self.setWindowTitle(f"Media Info - {video_path.name if video_path else 'Unknown'}")
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout()
        
        # File path
        path_label = QLabel(f"File: {video_path}")
        path_label.setStyleSheet("font-weight: bold; color: #d168a3;")
        layout.addWidget(path_label)
        
        # Track information
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setFont(QFont("Courier New", 10))
        info_text.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 3px;
            }
        """)
        
        # Analyze tracks and format info
        if video_path and video_path.exists():
            tracks = analyze_tracks(video_path)
            info_lines = []
            
            # File info
            try:
                stat = video_path.stat()
                size_mb = stat.st_size / (1024 * 1024)
                info_lines.append(f"File Size: {size_mb:.2f} MB")
            except:
                pass
            
            info_lines.append("")
            info_lines.append("=" * 60)
            info_lines.append("VIDEO TRACKS")
            info_lines.append("=" * 60)
            
            if tracks['video']:
                for vid in tracks['video']:
                    info_lines.append(f"\nTrack ID: {vid.get('track_id', 'N/A')}")
                    info_lines.append(f"  Codec: {vid.get('codec', 'unknown')}")
                    info_lines.append(f"  Resolution: {vid.get('resolution', 'unknown')}")
                    info_lines.append(f"  Language: {vid.get('language', 'unknown')}")
            else:
                info_lines.append("\nNo video tracks found")
            
            info_lines.append("")
            info_lines.append("=" * 60)
            info_lines.append("AUDIO TRACKS")
            info_lines.append("=" * 60)
            
            if tracks['audio']:
                for aud in tracks['audio']:
                    info_lines.append(f"\nTrack ID: {aud.get('track_id', 'N/A')}")
                    info_lines.append(f"  Codec: {aud.get('codec', 'unknown')}")
                    info_lines.append(f"  Channels: {aud.get('channels', 0)}")
                    info_lines.append(f"  Sample Rate: {aud.get('sample_rate', 'unknown')} Hz")
                    info_lines.append(f"  Language: {aud.get('language', 'unknown')}")
            else:
                info_lines.append("\nNo audio tracks found")
            
            info_lines.append("")
            info_lines.append("=" * 60)
            info_lines.append("SUBTITLE TRACKS")
            info_lines.append("=" * 60)
            
            if tracks['subtitles']:
                for sub in tracks['subtitles']:
                    info_lines.append(f"\nTrack ID: {sub.get('track_id', 'N/A')}")
                    info_lines.append(f"  Format: {sub.get('format', sub.get('codec', 'unknown'))}")
                    info_lines.append(f"  Language: {sub.get('language', 'unknown')}")
            else:
                info_lines.append("\nNo embedded subtitle tracks found")
            
            # Try to get more detailed info using ffprobe
            try:
                ffprobe_exe = get_ffprobe_command(self.config)
                result = subprocess.run(
                    [ffprobe_exe, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(video_path)],
                    capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    import json
                    probe_data = json.loads(result.stdout)
                    if 'format' in probe_data:
                        fmt = probe_data['format']
                        info_lines.append("")
                        info_lines.append("=" * 60)
                        info_lines.append("CONTAINER INFO")
                        info_lines.append("=" * 60)
                        info_lines.append(f"Format: {fmt.get('format_name', 'unknown')}")
                        info_lines.append(f"Duration: {fmt.get('duration', 'unknown')} seconds")
                        if 'bit_rate' in fmt:
                            bitrate_mbps = int(fmt['bit_rate']) / 1000000
                            info_lines.append(f"Bitrate: {bitrate_mbps:.2f} Mbps")
            except:
                pass
            
            info_text.setText('\n'.join(info_lines))
        else:
            info_text.setText("File not found or cannot be analyzed.")
        
        layout.addWidget(info_text)
        
        # Close button
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)


class WhisperModelDialog(QDialog):
    """Dialog to ask if user already has a Whisper model installed."""
    
    def __init__(self, parent=None, model_name: str = "turbo"):
        super().__init__(parent)
        self.setWindowTitle("Whisper Model Setup")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        # Instructions
        info_label = QLabel(
            f"Do you already have a Whisper model downloaded and stored somewhere?\n\n"
            f"The app will use the '{model_name}' model. If you've previously used Whisper "
            f"(either through this app or another tool), the model may already be downloaded "
            f"to your cache directory (~/.cache/whisper/).\n\n"
            f"Selecting 'Yes' will skip the model download and use your existing model."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Check if model exists in default location
        model_exists = check_whisper_model_exists(model_name)
        if model_exists:
            found_label = QLabel(
                f"✓ Found existing '{model_name}' model in default cache location."
            )
            found_label.setStyleSheet("color: #28a745; font-weight: bold;")
            layout.addWidget(found_label)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        yes_btn = QPushButton("Yes, I have it")
        yes_btn.clicked.connect(lambda: self.set_result(True))
        no_btn = QPushButton("No, download it")
        no_btn.clicked.connect(lambda: self.set_result(False))
        button_layout.addWidget(yes_btn)
        button_layout.addWidget(no_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.result = None
    
    def set_result(self, value: bool):
        """Set the dialog result and close."""
        self.result = value
        self.accept()
    
    def get_result(self) -> bool:
        """Get whether user has existing model."""
        return self.result if self.result is not None else False


# ============================================================================
# Settings Dialog
# ============================================================================

class SettingsDialog(QDialog):
    """Settings configuration dialog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(700)
        
        self.config = load_config()
        
        main_layout = QVBoxLayout()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setSpacing(16)
        
        # --- API Keys ---
        api_group = QGroupBox("API Keys")
        api_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        api_form = QFormLayout()
        api_key_info = QLabel(
            'You can set up your API key safely by setting the GEMINI_API_KEY environment variable. '
            '<a href="https://aistudio.google.com/app/apikey">Get your API key here</a>. '
            'Add multiple keys below; when one hits quota limits, the app retries with the next.'
        )
        api_key_info.setOpenExternalLinks(True)
        api_key_info.setWordWrap(True)
        api_key_info.setStyleSheet("color: #666;")
        api_form.addRow("", api_key_info)
        keys_container = QWidget()
        self.api_keys_layout = QVBoxLayout()
        keys_container.setLayout(self.api_keys_layout)
        self.api_key_inputs = []
        api_keys_list = self.config.get("api_keys") or []
        if not api_keys_list and (self.config.get("api_key") or self.config.get("api_key2")):
            api_keys_list = [k for k in [self.config.get("api_key"), self.config.get("api_key2")] if k]
        if not api_keys_list:
            api_keys_list = [""]
        for key in api_keys_list:
            self._add_api_key_row(key)
        add_btn = QPushButton("+ Add another key")
        add_btn.clicked.connect(self._add_api_key_row_blank)
        self.api_keys_layout.addWidget(add_btn)
        api_form.addRow("", keys_container)
        api_group.setLayout(api_form)
        content_layout.addWidget(api_group)
        
        # --- FFmpeg (optional path for older version) ---
        ffmpeg_group = QGroupBox("FFmpeg")
        ffmpeg_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        ffmpeg_form = QFormLayout()
        ffmpeg_help = QLabel(
            "Leave empty to use FFmpeg from PATH. Set a path (e.g. /opt/homebrew/opt/ffmpeg@6/bin/ffmpeg) "
            "to use a specific version if FFmpeg 7.x gives filter errors with burn-in subtitles."
        )
        ffmpeg_help.setWordWrap(True)
        ffmpeg_help.setStyleSheet("color: #666; font-size: 10px;")
        ffmpeg_form.addRow("", ffmpeg_help)
        self.ffmpeg_path_input = QLineEdit()
        self.ffmpeg_path_input.setText(self.config.get("ffmpeg_path", ""))
        self.ffmpeg_path_input.setPlaceholderText("e.g. /opt/homebrew/opt/ffmpeg@6/bin/ffmpeg")
        ffmpeg_form.addRow("FFmpeg path (optional):", self.ffmpeg_path_input)
        ffmpeg_group.setLayout(ffmpeg_form)
        content_layout.addWidget(ffmpeg_group)

        # --- N_m3u8DL-RE (optional path for batch downloads) ---
        nm3u8_group = QGroupBox("N_m3u8DL-RE")
        nm3u8_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        nm3u8_form = QFormLayout()
        nm3u8_help = QLabel(
            "Leave empty to use N_m3u8DL-RE from PATH. Set path to executable or folder containing it "
            "if installed in a custom location (e.g. for batch downloads)."
        )
        nm3u8_help.setWordWrap(True)
        nm3u8_help.setStyleSheet("color: #666; font-size: 10px;")
        nm3u8_form.addRow("", nm3u8_help)
        self.n_m3u8dl_path_input = QLineEdit()
        self.n_m3u8dl_path_input.setText(self.config.get("n_m3u8dl_path", ""))
        self.n_m3u8dl_path_input.setPlaceholderText("e.g. /usr/local/bin/N_m3u8DL-RE or C:\\Tools\\N_m3u8DL-RE.exe")
        nm3u8_form.addRow("N_m3u8DL-RE path (optional):", self.n_m3u8dl_path_input)
        nm3u8_group.setLayout(nm3u8_form)
        content_layout.addWidget(nm3u8_group)

        # --- Watermarks ---
        watermark_group = QGroupBox("Watermarks")
        watermark_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        wm_form = QFormLayout()
        self.use_watermarks_checkbox = QCheckBox("Use watermarks")
        self.use_watermarks_checkbox.setChecked(self.config.get("use_watermarks", True))
        self.use_watermarks_checkbox.stateChanged.connect(self.toggle_watermark_fields)
        wm_form.addRow("", self.use_watermarks_checkbox)
        self.watermark_720p_input = QLineEdit()
        self.watermark_720p_input.setText(self.config.get("watermark_720p", ""))
        self.wm720_browse = QPushButton("Browse...")
        self.wm720_browse.clicked.connect(lambda: self.browse_file(self.watermark_720p_input, "Select 720p Watermark"))
        wm720_layout = QHBoxLayout()
        wm720_layout.addWidget(self.watermark_720p_input)
        wm720_layout.addWidget(self.wm720_browse)
        wm_form.addRow("Watermark 720p:", wm720_layout)
        self.watermark_1080p_input = QLineEdit()
        self.watermark_1080p_input.setText(self.config.get("watermark_1080p", ""))
        self.wm1080_browse = QPushButton("Browse...")
        self.wm1080_browse.clicked.connect(lambda: self.browse_file(self.watermark_1080p_input, "Select 1080p Watermark"))
        wm1080_layout = QHBoxLayout()
        wm1080_layout.addWidget(self.watermark_1080p_input)
        wm1080_layout.addWidget(self.wm1080_browse)
        wm_form.addRow("Watermark 1080p:", wm1080_layout)
        watermark_group.setLayout(wm_form)
        content_layout.addWidget(watermark_group)
        
        # --- Subtitle Translation ---
        translation_group = QGroupBox("Subtitle Translation")
        translation_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        trans_form = QFormLayout()
        translation_info = QLabel(
            "Select the target language for subtitle translation. "
            "Subtitles will be translated from their original language to your selected target."
        )
        translation_info.setWordWrap(True)
        translation_info.setStyleSheet("color: #666;")
        trans_form.addRow("", translation_info)
        self.translation_target_combo = QComboBox()
        for lang in TRANSLATION_TARGET_LANGUAGES:
            self.translation_target_combo.addItem(lang)
        current_target = self.config.get("translation_target_language", "English")
        target_index = self.translation_target_combo.findText(current_target)
        if target_index >= 0:
            self.translation_target_combo.setCurrentIndex(target_index)
        trans_form.addRow("Translation Target:", self.translation_target_combo)
        self.iso639_checkbox = QCheckBox("Use ISO 639 language suffixes (.eng.srt, .fra.srt)")
        self.iso639_checkbox.setChecked(self.config.get("use_iso639_suffixes", False))
        iso639_help = QLabel(
            "When enabled, translated subtitles will include language codes in filenames. "
            "This allows VLC and Jellyfin to automatically detect and select subtitles."
        )
        iso639_help.setWordWrap(True)
        iso639_help.setStyleSheet("color: #666; font-size: 10px;")
        trans_form.addRow("", self.iso639_checkbox)
        trans_form.addRow("", iso639_help)
        translation_group.setLayout(trans_form)
        content_layout.addWidget(translation_group)
        
        # --- Appearance ---
        appearance_group = QGroupBox("Appearance")
        appearance_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        app_form = QFormLayout()
        self.lesbian_flag_checkbox = QCheckBox("Lesbian flag theme (always on)")
        self.lesbian_flag_checkbox.setChecked(False)
        self.lesbian_flag_checkbox.setToolTip("The app uses lesbian flag colors. Try checking this for a surprise.")
        self.lesbian_flag_checkbox.stateChanged.connect(self.toggle_lesbian_flag_theme)
        app_form.addRow("", self.lesbian_flag_checkbox)
        appearance_group.setLayout(app_form)
        content_layout.addWidget(appearance_group)
        
        content.setLayout(content_layout)
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
        self.toggle_watermark_fields()
        
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)

    def _add_api_key_row(self, value: str = ""):
        """Add an API key row. Called with value when populating, or blank when user clicks +."""
        row = QWidget()
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 4, 0, 4)
        le = QLineEdit()
        le.setText(value)
        le.setEchoMode(QLineEdit.Password)
        le.setPlaceholderText("Paste API key")
        row_layout.addWidget(le)
        remove_btn = QPushButton("−")
        remove_btn.setFixedWidth(28)
        remove_btn.setToolTip("Remove this key")

        def do_remove():
            self.api_key_inputs.remove((le, row, remove_btn))
            row.setParent(None)
            row.deleteLater()
            self._update_remove_buttons()

        remove_btn.clicked.connect(do_remove)
        row_layout.addWidget(remove_btn)
        row.setLayout(row_layout)
        self.api_key_inputs.append((le, row, remove_btn))
        self.api_keys_layout.insertWidget(self.api_keys_layout.count() - 1, row)
        self._update_remove_buttons()

    def _add_api_key_row_blank(self):
        self._add_api_key_row("")

    def _update_remove_buttons(self):
        for le, row, remove_btn in self.api_key_inputs:
            remove_btn.setEnabled(len(self.api_key_inputs) > 1)

    def toggle_watermark_fields(self):
        """Enable/disable watermark input fields based on checkbox."""
        enabled = self.use_watermarks_checkbox.isChecked()
        self.watermark_720p_input.setEnabled(enabled)
        self.watermark_1080p_input.setEnabled(enabled)
        self.wm720_browse.setEnabled(enabled)
        self.wm1080_browse.setEnabled(enabled)
    
    def toggle_lesbian_flag_theme(self, state):
        """Joke feature - shows a message and keeps the theme ON."""
        if state == Qt.Checked:  # User tried to check it (turn theme OFF)
            # Show the message
            QMessageBox.warning(
                self, 
                "Wait a minute...",
                "That kinda homophobic, isn't it?"
            )
            # Immediately uncheck it (keep theme ON)
            self.lesbian_flag_checkbox.blockSignals(True)
            self.lesbian_flag_checkbox.setChecked(False)
            self.lesbian_flag_checkbox.blockSignals(False)
    
    def browse_file(self, line_edit, title):
        """Browse for a file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, title, "", "Image Files (*.png *.jpg);;All Files (*)"
        )
        if file_path:
            line_edit.setText(file_path)
    
    def save_settings(self):
        """Save settings and close dialog."""
        api_keys = [le.text().strip() for le, row, btn in self.api_key_inputs if le.text().strip()]
        self.config["api_keys"] = api_keys
        self.config["ffmpeg_path"] = self.ffmpeg_path_input.text().strip()
        self.config["n_m3u8dl_path"] = self.n_m3u8dl_path_input.text().strip()
        self.config["watermark_720p"] = self.watermark_720p_input.text()
        self.config["watermark_1080p"] = self.watermark_1080p_input.text()
        self.config["use_watermarks"] = self.use_watermarks_checkbox.isChecked()
        self.config["translation_target_language"] = self.translation_target_combo.currentText()
        self.config["use_iso639_suffixes"] = self.iso639_checkbox.isChecked()
        save_config(self.config)
        self.accept()


# ============================================================================
# Whisper Options Dialog (Standalone)
# ============================================================================

class WhisperOptionsDialog(QDialog):
    """Simplified dialog for Whisper advanced options - manual parameter entry."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Whisper Advanced Options")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(700)
        
        self.config = load_config()
        
        main_layout = QVBoxLayout()
        
        # Info label
        info_label = QLabel("Type additional Whisper parameters below. These will be appended to the default command.")
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)
        
        # Split layout: left panel (parameters reference) and right panel (user input)
        split_layout = QHBoxLayout()
        
        # Left panel: Available Parameters (read-only reference)
        left_panel = QGroupBox("Available Parameters (Reference)")
        left_layout = QVBoxLayout()
        
        params_text = QTextEdit()
        params_text.setReadOnly(True)
        params_text.setFont(QFont("Courier New", 10))
        params_text.setPlainText(self.get_parameters_reference())
        left_layout.addWidget(params_text)
        
        left_panel.setLayout(left_layout)
        split_layout.addWidget(left_panel, 1)  # 1:1 ratio
        
        # Right panel: Additional Parameters (user input)
        right_panel = QGroupBox("Additional Parameters")
        right_layout = QVBoxLayout()
        
        help_label = QLabel("Enter one parameter per line. Format: --parameter_name value\nExample:\n--patience 1.0\n--word_timestamps True\n--max_words_per_line 7")
        help_label.setStyleSheet("color: #666; font-size: 10px; margin-bottom: 5px;")
        help_label.setWordWrap(True)
        right_layout.addWidget(help_label)
        
        self.extra_args_input = QTextEdit()
        self.extra_args_input.setFont(QFont("Courier New", 11))
        self.extra_args_input.setPlaceholderText("--patience 1.0\n--word_timestamps True\n--max_words_per_line 7\n--max_line_count 2")
        # Load existing extra_args from config
        extra_args = self.config.get("whisper_options", {}).get("extra_args", "")
        self.extra_args_input.setPlainText(extra_args)
        right_layout.addWidget(self.extra_args_input)
        
        right_panel.setLayout(right_layout)
        split_layout.addWidget(right_panel, 1)  # 1:1 ratio
        
        main_layout.addLayout(split_layout)
        
        # Buttons at bottom
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def get_parameters_reference(self) -> str:
        """Generate reference text listing all available Whisper parameters."""
        params = """--model : name of the Whisper model to use (default: turbo), selects model size; larger = more accurate but slower, smaller = faster but less accurate

--model_dir : path to save model files (default: ~/.cache/whisper), folder where downloaded models are stored

--device : device for PyTorch inference (default: cpu), hardware used for processing; GPU is much faster than CPU if available

--output_dir, -o OUTPUT_DIR : directory to save outputs (default: .), where transcription files are written

--output_format {txt,vtt,srt,tsv,json,all}, -f {txt,vtt,srt,tsv,json,all} : format of output file (default: all)

--verbose : print progress/debug messages (default: True)

--temperature : temperature for sampling (default: 0), randomness of decoding; low = stable/accurate, high = more varied but riskier

--best_of : number of candidates when sampling (default: 5), more candidates can improve accuracy but slow things down

--beam_size : beams in beam search (default: 5), higher explores more alternatives; improves accuracy at the cost of speed

--patience : beam search patience (default: None)

--length_penalty : token length penalty coefficient (default: None)

--suppress_tokens : comma-separated token ids to suppress (default: -1)

--initial_prompt : text prompt for first window (default: None), primes the model with exoected wording or context

--carry_initial_prompt : prepend initial_prompt to every decode() (default: False), keeps the same prompt across all segments

--condition_on_previous_text : use previous output as prompt (default: True), improves continuity but can repeat earlier mistakes

--fp16 : perform inference in fp16 (default: True), faster and lower memory usage on supported hardware

--temperature_increment_on_fallback : temperature increase on fallback (default: 0.2), loosens decoding if the model gets stuck

--compression_ratio_threshold : gzip compression ratio threshold (default: 2.4), detects repetitive or hallucinated output; lower is stricter

--logprob_threshold : average log probability threshold (default: -1.0), filters low-confidence transcriptions; higher is stricter

--no_speech_threshold : probability of <|nospeech|> token (default: 0.6), higher skips more silent segments

--word_timestamps : extract word-level timestamps (default: False), enables per-word timing for subtitles (idk how tho)

--prepend_punctuations : merge with next word (default: "'"¿([{-), keeps opening punctuation attached to the following word

--append_punctuations : merge with previous word (default: "'.。,，!！?？:：")]}), keeps closing punctuation attached to the previous word

--highlight_words : underline words in srt/vtt (requires word_timestamps) (default: False), visually emphasizes spoken words (idk how tho)

--max_line_width : max chars before line break (requires word_timestamps) (default: None), lower values create shorter subtitle lines

--max_line_count : max lines in segment (requires word_timestamps) (default: None), limits subtitle height on screen (max. two lines is standard practice)

--max_words_per_line : max words in segment (REQUIRES word_timestamps, no effect with max_line_width) (default: None), caps words per subtitle LINE

--threads : threads for CPU inference (default: 0), higher can speed up CPU processing at the cost of all other processes running simultaneously

--clip_timestamps : comma-separated start,end,start,end,... timestamps in seconds (default: 0), transcribes only selected audio ranges

--hallucination_silence_threshold : skip silent periods when hallucination detected (requires word_timestamps) (default: None), avoids fake text (the so-called "hallucination") during silences

Note: --language and --task translate are handled by the main tab and should not be included here."""
        return params
    
    def save_settings(self):
        """Save whisper options and close dialog."""
        # Get user-typed parameters (one per line)
        extra_args_text = self.extra_args_input.toPlainText().strip()
        
        # Convert newlines to spaces for WHISPER_EXTRA_ARGS
        # This allows users to type one parameter per line for readability
        extra_args = " ".join(line.strip() for line in extra_args_text.split("\n") if line.strip())
        
        # Save to config
        if "whisper_options" not in self.config:
            self.config["whisper_options"] = {}
        
        self.config["whisper_options"]["extra_args"] = extra_args_text  # Save as multiline for display
        self.config["whisper_options"]["extra_args_parsed"] = extra_args  # Save as space-separated for script
        
        save_config(self.config)
        self.accept()


# ============================================================================
# Main Window
# ============================================================================

class VideoProcessingApp(QMainWindow):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.worker = None
        self.remux_selected_files = []  # Initialize selected files list
        
        # Set window icon
        self.setWindowIcon(get_app_icon())
        
        # Show setup wizard on first launch or first run of this version
        last_ver = self.config.get("last_setup_version", "")
        if not self.config.get("setup_complete", False) or last_ver != __version__:
            wizard = SetupWizard(self)
            wizard.exec_()
        
        self.init_ui()
    
    def darken_color(self, hex_color: str, percent: float = 0.15) -> str:
        """Darken a hex color by a percentage."""
        # Strip #
        hex_color = hex_color.lstrip('#')
        # Convert to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        # Darken by percent
        r = max(0, int(r * (1 - percent)))
        g = max(0, int(g * (1 - percent)))
        b = max(0, int(b * (1 - percent)))
        # To hex
        return f"#{r:02x}{g:02x}{b:02x}"
    
    def apply_button_style(self, button: QPushButton, color: str):
        """Apply solid color style to a button with 15% darker hover."""
        hover_color = self.darken_color(color, 0.15)
        stylesheet = f"""
        QPushButton {{
            background-color: {color};
            color: white;
            border: none;
            border-radius: 5px;
            padding: 4px 12px;
            font-weight: bold;
            min-height: 18px;
            outline: none;
        }}
        QPushButton:hover {{
            background-color: {hover_color};
            border: none;
            outline: none;
        }}
        QPushButton:pressed {{
            background-color: {hover_color};
            border: none;
            outline: none;
        }}
        """
        button.setStyleSheet(stylesheet)
    
    def apply_lesbian_flag_styles(self):
        """Apply lesbian flag color scheme to buttons."""
        # Flag colors
        colors = [
            "#df4300",  # Red
            "#f48a32",  # Orange
            "#ffab68",  # Light Orange
            "#dc7bb3",  # Pink
            "#c46ea1",  # Purple
            "#b42075",  # Dark Pink
        ]
        
        # Find buttons by section
        buttons = self.findChildren(QPushButton)
        
        # Group by QGroupBox
        download_buttons = []
        subtitle_buttons = []
        process_buttons = []
        remux_buttons = []
        transcribe_buttons = []
        settings_button = None
        faq_button = None
        about_button = None
        
        for btn in buttons:
            parent = btn.parent()
            # Find QGroupBox
            while parent:
                if isinstance(parent, QGroupBox):
                    group_title = parent.title()
                    if group_title == "DOWNLOAD":
                        download_buttons.append(btn)
                    elif group_title == "SUBTITLES":
                        subtitle_buttons.append(btn)
                    elif group_title == "PROCESS VIDEO":
                        process_buttons.append(btn)
                    elif group_title == "REMUX":
                        remux_buttons.append(btn)
                    elif group_title == "TRANSCRIBE":
                        transcribe_buttons.append(btn)
                    break
                parent = parent.parent()
            
            # Top bar buttons
            if btn.text() == "Settings":
                settings_button = btn
            elif btn.text() == "FAQ":
                faq_button = btn
            elif btn.text() == "About":
                about_button = btn
        
        # Apply colors
        for btn in download_buttons:
            self.apply_button_style(btn, colors[0])
        
        for btn in subtitle_buttons:
            self.apply_button_style(btn, colors[1])
        
        for btn in process_buttons:
            self.apply_button_style(btn, colors[2])
        
        for btn in remux_buttons:
            self.apply_button_style(btn, colors[3])
        
        for btn in transcribe_buttons:
            self.apply_button_style(btn, colors[4])
        
        if settings_button:
            self.apply_button_style(settings_button, colors[5])
        if faq_button:
            self.apply_button_style(faq_button, colors[5])
        if about_button:
            self.apply_button_style(about_button, colors[5])
    
    def create_transcription_tab(self):
        """Create the dedicated transcription tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Header
        header_label = QLabel("Transcribe Audio/Video to Subtitles")
        header_label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(header_label)
        
        desc_label = QLabel("Use OpenAI Whisper to generate subtitles from audio/video")
        desc_label.setStyleSheet("color: #666;")
        layout.addWidget(desc_label)
        
        # File selection
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout()
        
        file_row = QHBoxLayout()
        file_label = QLabel("Select file:")
        self.transcribe_file_input = QLineEdit()
        self.transcribe_file_input.setReadOnly(True)
        self.transcribe_file_input.setPlaceholderText("No file selected")
        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_transcribe_file)
        file_row.addWidget(file_label, 0)
        file_row.addWidget(self.transcribe_file_input, 1)
        file_row.addWidget(browse_btn, 0)
        file_layout.addLayout(file_row)
        
        # Language selection
        lang_row = QHBoxLayout()
        lang_label = QLabel("Language:")
        self.transcribe_language_combo = QComboBox()
        for name, code in TRANSCRIBE_LANGUAGES:
            self.transcribe_language_combo.addItem(name, code)
        lang_row.addWidget(lang_label, 0)
        lang_row.addWidget(self.transcribe_language_combo, 1)
        lang_row.addStretch()
        file_layout.addLayout(lang_row)
        
        # Output format selector
        format_row = QHBoxLayout()
        format_label = QLabel("Output Format:")
        format_label.setFixedWidth(120)
        self.transcribe_format_combo = QComboBox()
        formats = [
            ("SRT (Subtitles)", "srt"),
            ("VTT (WebVTT)", "vtt"),
            ("TXT (Plain Text)", "txt"),
            ("TSV (Tab-Separated)", "tsv"),
            ("JSON (Detailed)", "json"),
            ("All Formats", "all"),
        ]
        for name, code in formats:
            self.transcribe_format_combo.addItem(name, code)
        # Default to SRT
        default_format = self.config.get("whisper_output_format", "srt")
        format_index = self.transcribe_format_combo.findData(default_format)
        if format_index >= 0:
            self.transcribe_format_combo.setCurrentIndex(format_index)
        format_row.addWidget(format_label, 0)
        format_row.addWidget(self.transcribe_format_combo, 1)
        format_row.addStretch()
        file_layout.addLayout(format_row)
        
        # Whisper Model selector
        model_row = QHBoxLayout()
        model_label = QLabel("Whisper Model:")
        model_label.setFixedWidth(120)
        self.transcribe_model_combo = QComboBox()
        self.transcribe_model_combo.addItems(["tiny", "base", "small", "medium", "large", "turbo"])
        current_model = self.config.get("whisper_model", "turbo")
        model_index = self.transcribe_model_combo.findText(current_model)
        if model_index >= 0:
            self.transcribe_model_combo.setCurrentIndex(model_index)
        else:
            self.transcribe_model_combo.setCurrentText("turbo")
        # Save model when changed
        self.transcribe_model_combo.currentTextChanged.connect(self.save_whisper_model)
        model_info = QLabel("(Turbo recommended for best accuracy/speed, ~1.5 GB)")
        model_info.setStyleSheet("color: #666; font-size: 12px;")
        model_row.addWidget(model_label, 0)
        model_row.addWidget(self.transcribe_model_combo, 1)
        model_row.addWidget(model_info, 1)
        model_row.addStretch()
        file_layout.addLayout(model_row)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        self.transcribe_main_btn = QPushButton("Transcribe")
        # Apply same styling as other buttons in the app
        hover_color = "#b1588a"
        self.transcribe_main_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #d168a3;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 4px 12px;
                font-weight: bold;
                min-height: 18px;
                outline: none;
            }}
            QPushButton:hover {{
                background-color: {hover_color};
                border: none;
                outline: none;
            }}
            QPushButton:pressed {{
                background-color: {hover_color};
                border: none;
                outline: none;
            }}
        """)
        self.transcribe_main_btn.clicked.connect(self.transcribe_from_tab)
        
        transcribe_long_btn = QPushButton("Transcribe longer video")
        transcribe_long_btn.setToolTip(
            "Use this for files over ~5 minutes. Splits audio into short segments via voice detection "
            "(Silero VAD), then transcribes each with Whisper. Prevents hallucination caused by long "
            "silences or extended audio. Takes roughly 1–2× the file duration on CPU."
        )
        transcribe_long_btn.setStyleSheet("""
            QPushButton {
                background-color: #c46ea1;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 4px 12px;
                font-weight: bold;
                min-height: 18px;
            }
            QPushButton:hover {
                background-color: #b85d90;
            }
            QPushButton:pressed {
                background-color: #a04d80;
            }
        """)
        transcribe_long_btn.clicked.connect(self.transcribe_long_from_tab)
        
        transcribe_cpp_btn = QPushButton("Transcribe (Whisper CPP)")
        transcribe_cpp_btn.setToolTip(
            "Uses whisper.cpp. Faster, built-in VAD. Requires whisper.cpp binary (whisper-cli or main); models auto-download on first use."
        )
        transcribe_cpp_btn.setStyleSheet("""
            QPushButton {
                background-color: #a85d8a;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 4px 12px;
                font-weight: bold;
                min-height: 18px;
            }
            QPushButton:hover {
                background-color: #984d7a;
            }
            QPushButton:pressed {
                background-color: #8a4570;
            }
        """)
        transcribe_cpp_btn.clicked.connect(self.transcribe_whisper_cpp_from_tab)
        
        advanced_btn = QPushButton("Advanced Options...")
        advanced_btn.clicked.connect(self.open_whisper_options)
        
        buttons_layout.addWidget(self.transcribe_main_btn, 2)
        buttons_layout.addWidget(transcribe_long_btn, 2)
        buttons_layout.addWidget(transcribe_cpp_btn, 2)
        buttons_layout.addWidget(advanced_btn, 1)
        layout.addLayout(buttons_layout)
        
        transcribe_hint = QLabel(
            "Use \"Transcribe\" for short clips. Use \"Transcribe longer video\" for files over ~5 min (VAD-assisted, prevents hallucination). "
            "Use \"Transcribe (Whisper CPP)\" for a faster alternative with built-in VAD (requires whisper.cpp installed)."
        )
        transcribe_hint.setStyleSheet("color: #666; font-size: 12px;")
        transcribe_hint.setWordWrap(True)
        layout.addWidget(transcribe_hint)
        
        # Processing logs
        logs_label = QLabel("Processing Logs:")
        logs_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(logs_label)
        
        self.transcribe_log_output = QTextEdit()
        self.transcribe_log_output.setReadOnly(True)
        self.transcribe_log_output.setMinimumHeight(200)
        self.transcribe_log_output.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 3px;
                font-family: 'Courier New', 'Menlo',monospace;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.transcribe_log_output)
        
        # Progress bar for transcription
        progress_layout = QHBoxLayout()
        self.transcribe_progress_bar = QProgressBar()
        self.transcribe_progress_bar.setMinimumHeight(25)
        self.transcribe_progress_bar.setVisible(False)
        self.transcribe_progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 5px;
                text-align: center;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #5dade2;
                border-radius: 4px;
            }
        """)
        
        self.transcribe_stop_btn = QPushButton("Stop")
        self.transcribe_stop_btn.setFixedWidth(80)
        self.transcribe_stop_btn.setVisible(False)
        self.transcribe_stop_btn.clicked.connect(self.stop_operation)
        self.transcribe_stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #cc0000;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 4px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #990000;
            }
        """)
        
        progress_layout.addWidget(self.transcribe_progress_bar)
        progress_layout.addWidget(self.transcribe_stop_btn)
        layout.addLayout(progress_layout)
        
        tab.setLayout(layout)
        return tab
    
    def save_whisper_model(self, model: str):
        """Save Whisper model selection to config."""
        config = load_config()
        config["whisper_model"] = model
        save_config(config)
        self.config["whisper_model"] = model
    
    def browse_transcribe_file(self):
        """Browse for file to transcribe."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video or Audio File to Transcribe",
            str(get_downloads_dir()),
            "Media Files (*.mkv *.mp4 *.mov *.mp3 *.wav *.m4a);;All Files (*)"
        )
        if file_path:
            self.transcribe_file_input.setText(file_path)
    
    def transcribe_from_tab(self):
        """Transcribe video from the dedicated tab."""
        file_path = self.transcribe_file_input.text()
        if not file_path or file_path == "No file selected":
            QMessageBox.warning(self, "No File", "Please select a video or audio file to transcribe.")
            return
        
        video_path = Path(file_path)
        if not video_path.exists():
            QMessageBox.warning(self, "File Not Found", f"The selected file does not exist:\n{file_path}")
            return
        
        # Get language from combo
        language_code = self.transcribe_language_combo.currentData()
        if language_code == "auto":
            QMessageBox.warning(
                self,
                "Select Language",
                "Please select a language before transcribing."
            )
            return

        # Get model from combo (saved to config automatically)
        model = self.transcribe_model_combo.currentText()
        
        # Get whisper options from config
        config = load_config()
        whisper_options = config.get("whisper_options", {})
        
        # Process extra_args: convert multiline to space-separated if needed
        if "extra_args" in whisper_options and "extra_args_parsed" not in whisper_options:
            extra_args_text = whisper_options.get("extra_args", "")
            extra_args = " ".join(line.strip() for line in extra_args_text.split("\n") if line.strip())
            whisper_options["extra_args_parsed"] = extra_args
        
        # Check if this is first time using transcription
        whisper_model_asked = config.get("whisper_model_asked", False)
        
        if not whisper_model_asked:
            # Ask user if they already have a model
            model_dialog = WhisperModelDialog(self, model)
            if model_dialog.exec_() != QDialog.Accepted:
                return  # User cancelled
            
            has_existing_model = model_dialog.get_result()
            
            # Save preference to config
            config["whisper_model_asked"] = True
            config["whisper_has_existing_model"] = has_existing_model
            save_config(config)
            
            if has_existing_model:
                self.transcribe_log(f"Using existing Whisper model '{model}' from cache.")
            else:
                self.transcribe_log(f"Will download Whisper model '{model}' on first use.")
        
        # Get output format from combo
        output_format = self.transcribe_format_combo.currentData()
        
        self.transcribe_log(f"Starting transcription of: {video_path.name}")
        self.transcribe_log(f"Language: {language_code}, Model: {model}, Format: {output_format}")
        
        # Show progress bar and stop button
        self.transcribe_progress_bar.setVisible(True)
        self.transcribe_stop_btn.setVisible(True)
        self.transcribe_stop_btn.setEnabled(True)
        self.transcribe_progress_bar.setRange(0, 0)  # Indeterminate
        
        # Run transcription with language, model, whisper options, and output format
        def transcribe_with_params(video_path, language_code, model, whisper_options, output_format, progress_callback=None, log_callback=None):
            return transcribe_video(video_path, language_code, model, whisper_options, output_format, progress_callback, log_callback)
        
        # Use custom callbacks for the tab
        def tab_log_callback(msg):
            self.transcribe_log(msg)
        
        self.worker = ScriptWorker(transcribe_with_params, video_path, language_code, model, whisper_options, output_format)
        self.worker.log_message.connect(tab_log_callback)
        self.worker.finished.connect(self.on_transcribe_finished)
        self.worker.start()
    
    def transcribe_log(self, message):
        """Add message to transcription log."""
        from datetime import datetime
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        self.transcribe_log_output.append(f"{timestamp} {message}")
        # Also log to main log
        self.log(message)
    
    def on_transcribe_finished(self, success: bool):
        """Handle transcription completion."""
        self.transcribe_progress_bar.setVisible(False)
        self.transcribe_stop_btn.setVisible(False)
        if success:
            self.transcribe_log("✓ Transcription completed successfully!")
        else:
            self.transcribe_log("✗ Transcription failed. Check log for details.")
        self.worker = None

    def transcribe_long_from_tab(self):
        """Transcribe long video using VAD + Whisper (for files over ~5 min)."""
        file_path = self.transcribe_file_input.text()
        if not file_path or file_path == "No file selected":
            QMessageBox.warning(self, "No File", "Please select a video or audio file to transcribe.")
            return
        video_path = Path(file_path)
        if not video_path.exists():
            QMessageBox.warning(self, "File Not Found", f"The selected file does not exist:\n{file_path}")
            return
        try:
            import torch  # noqa: F401
            import torchaudio  # noqa: F401
            import torchcodec  # noqa: F401
            import pysrt  # noqa: F401
        except ImportError as e:
            reply = QMessageBox.question(
                self,
                "Missing Dependencies",
                "This feature requires torch, torchaudio, torchcodec, pysrt, openai-whisper (~2–3 GB download).\n\n"
                "Would you like us to install them for you?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                dlg = QDialog(self)
                dlg.setWindowTitle("Installing...")
                dlg.setMinimumWidth(450)
                layout = QVBoxLayout()
                log = QTextEdit()
                log.setReadOnly(True)
                layout.addWidget(log)
                close_btn = QPushButton("Close")
                close_btn.setEnabled(False)
                layout.addWidget(close_btn)
                dlg.setLayout(layout)
                worker = PipInstallWorker(
                    ["torch", "torchaudio", "torchcodec", "pysrt", "openai-whisper"]
                )
                worker.log_message.connect(lambda m: log.append(m))
                def on_finished(ok):
                    if ok:
                        dlg.accept()
                        self.transcribe_long_from_tab()  # Retry
                    else:
                        log.append("\nInstallation failed. Click Close and try: python -m pip install torch torchaudio torchcodec pysrt openai-whisper")
                        close_btn.setEnabled(True)
                close_btn.clicked.connect(dlg.accept)
                worker.finished.connect(on_finished)
                worker.start()
                dlg.exec_()
            return
        language_code = self.transcribe_language_combo.currentData()
        if language_code == "auto":
            QMessageBox.warning(
                self,
                "Select Language",
                "Please select a language before transcribing."
            )
            return
        model = self.transcribe_model_combo.currentText()
        config = load_config()
        whisper_model_asked = config.get("whisper_model_asked", False)
        if not whisper_model_asked:
            model_dialog = WhisperModelDialog(self, model)
            if model_dialog.exec_() != QDialog.Accepted:
                return
            config["whisper_model_asked"] = True
            config["whisper_has_existing_model"] = model_dialog.get_result()
            save_config(config)
        self.transcribe_log(f"Starting VAD-assisted transcription of: {video_path.name}")
        self.transcribe_log(f"Language: {language_code}, Model: {model}")
        self.transcribe_progress_bar.setVisible(True)
        self.transcribe_stop_btn.setVisible(True)
        self.transcribe_stop_btn.setEnabled(True)
        self.transcribe_progress_bar.setRange(0, 0)
        def tab_log_callback(msg):
            self.transcribe_log(msg)
        self.worker = ScriptWorker(transcribe_video_vad, video_path, language_code, model)
        self.worker.log_message.connect(tab_log_callback)
        self.worker.finished.connect(self.on_transcribe_finished)
        self.worker.start()

    def transcribe_whisper_cpp_from_tab(self):
        """Transcribe using Whisper CPP. Faster, built-in VAD."""
        file_path = self.transcribe_file_input.text()
        if not file_path or file_path == "No file selected":
            QMessageBox.warning(self, "No File", "Please select a video or audio file to transcribe.")
            return
        video_path = Path(file_path)
        if not video_path.exists():
            QMessageBox.warning(self, "File Not Found", f"The selected file does not exist:\n{file_path}")
            return
        language_code = self.transcribe_language_combo.currentData()
        if not language_code:
            language_code = "auto"
        config = load_config()
        binary = _get_whisper_cpp_binary(config)
        if not binary or not Path(binary).exists():
            reply = QMessageBox.question(
                self,
                "Whisper CPP Not Installed",
                "Whisper CPP is not installed. Would you like us to install it for you?\n\n"
                "(whisper.cpp-cli, ~50 MB. On Windows, pre-built wheels may not be available—we'll try anyway; "
                "if it fails, you can build from source or use WSL.)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                dlg = QDialog(self)
                dlg.setWindowTitle("Installing Whisper CPP...")
                dlg.setMinimumWidth(400)
                layout = QVBoxLayout()
                log = QTextEdit()
                log.setReadOnly(True)
                layout.addWidget(log)
                close_btn = QPushButton("Close")
                close_btn.setEnabled(False)
                layout.addWidget(close_btn)
                dlg.setLayout(layout)
                worker = PipInstallWorker(["whisper.cpp-cli"])
                worker.log_message.connect(lambda m: log.append(m))
                def on_finished(ok):
                    if ok:
                        dlg.accept()
                        self.transcribe_whisper_cpp_from_tab()  # Retry
                    else:
                        log.append("\nInstallation failed. Click Close, then run in terminal:\n  python -m pip install whisper.cpp-cli")
                        close_btn.setEnabled(True)
                close_btn.clicked.connect(dlg.accept)
                worker.finished.connect(on_finished)
                worker.start()
                dlg.exec_()
                return
            QMessageBox.warning(
                self,
                "Whisper CPP Not Found",
                "Whisper CPP binary not found.\n\n"
                "Install from https://github.com/ggerganov/whisper.cpp and set whisper_cpp_path "
                "in settings.json, or use the install option when prompted."
            )
            return
        # Use same model as UI selector (turbo -> large-v3-turbo for Whisper CPP)
        ui_model = self.transcribe_model_combo.currentText()
        model_name = "large-v3-turbo" if ui_model == "turbo" else ui_model
        self.transcribe_log(f"Starting Whisper CPP transcription of: {video_path.name}")
        self.transcribe_log(f"Language: {language_code}, Model: {model_name}")
        self.transcribe_progress_bar.setVisible(True)
        self.transcribe_stop_btn.setVisible(True)
        self.transcribe_stop_btn.setEnabled(True)
        self.transcribe_progress_bar.setRange(0, 0)

        def tab_log_callback(msg):
            self.transcribe_log(msg)

        self.worker = ScriptWorker(transcribe_video_whisper_cpp, video_path, language_code, model_name)
        self.worker.log_message.connect(tab_log_callback)
        self.worker.finished.connect(self.on_transcribe_finished)
        self.worker.start()

    def create_remuxing_tab(self):
        """Create the dedicated remuxing tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        # Header - compact
        header_row = QHBoxLayout()
        header_label = QLabel("Remux")
        header_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_row.addWidget(header_label)
        header_row.addStretch()
        layout.addLayout(header_row)
        
        desc_label = QLabel("Add subtitles to videos or pick which tracks to keep. Expand a file to see track details.")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(desc_label)
        
        # File management
        file_group = QGroupBox("Files")
        file_layout = QVBoxLayout()
        
        # Initialize selected files list and file configs
        self.remux_selected_files = []
        self.remux_file_configs = {}  # Store per-file configuration
        
        # Buttons row - primary actions first
        buttons_row = QHBoxLayout()
        add_files_btn = QPushButton("Add Files...")
        add_files_btn.clicked.connect(self.add_remux_files)
        auto_match_btn = QPushButton("Auto-match Subtitles")
        auto_match_btn.setToolTip("Find SRT/VTT with same name as each video (same folder or Subtitles folder) and attach.")
        auto_match_btn.clicked.connect(self.auto_match_remux_subtitles)
        buttons_row.addWidget(add_files_btn)
        buttons_row.addWidget(auto_match_btn)
        buttons_row.addSpacing(10)
        remove_files_btn = QPushButton("Remove")
        remove_files_btn.clicked.connect(self.remove_remux_files)
        clear_files_btn = QPushButton("Clear")
        clear_files_btn.clicked.connect(self.clear_remux_files)
        buttons_row.addWidget(remove_files_btn)
        buttons_row.addWidget(clear_files_btn)
        buttons_row.addStretch()
        media_info_btn = QPushButton("Media Info")
        media_info_btn.clicked.connect(self.show_media_info)
        buttons_row.addWidget(media_info_btn)
        file_layout.addLayout(buttons_row)
        
        # Files tree widget - columns: File/Track, Type, Codec/Format, Language/Subtitle, Channels, Action
        self.remux_files_tree = QTreeWidget()
        self.remux_files_tree.setHeaderLabels(["File / Track", "Type", "Codec", "Language", "Channels", "Actions"])
        self.remux_files_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.remux_files_tree.setRootIsDecorated(True)
        self.remux_files_tree.setAlternatingRowColors(True)
        self.remux_files_tree.header().setStretchLastSection(False)
        self.remux_files_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.remux_files_tree.setStyleSheet("""
            QTreeWidget {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 3px;
                font-size: 11px;
            }
            QTreeWidget::item {
                padding: 3px;
            }
            QTreeWidget::item:selected {
                background-color: #d168a3;
                color: white;
            }
        """)
        # Enable context menu
        self.remux_files_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.remux_files_tree.customContextMenuRequested.connect(self.show_track_context_menu)
        file_layout.addWidget(self.remux_files_tree)
        
        # File count label
        self.remux_file_count_label = QLabel("No files selected")
        self.remux_file_count_label.setStyleSheet("color: #666; font-size: 10px;")
        file_layout.addWidget(self.remux_file_count_label)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Default format for new files + batch actions
        actions_row = QHBoxLayout()
        actions_row.addWidget(QLabel("New files:"))
        self.remux_default_output_format = QComboBox()
        self.remux_default_output_format.addItem("MKV", "mkv")
        self.remux_default_output_format.addItem("MP4", "mp4")
        self.remux_default_output_format.setMaximumWidth(70)
        actions_row.addWidget(self.remux_default_output_format)
        actions_row.addSpacing(20)
        remux_selected_btn = QPushButton("Remux Selected")
        remux_selected_btn.clicked.connect(self.remux_selected_files_action)
        actions_row.addWidget(remux_selected_btn)
        split_audio_btn = QPushButton("Split Audio")
        split_audio_btn.clicked.connect(self.split_audio_channels_batch)
        actions_row.addWidget(split_audio_btn)
        actions_row.addStretch()
        layout.addLayout(actions_row)
        
        # Status
        self.remux_log_output = QLineEdit()
        self.remux_log_output.setReadOnly(True)
        self.remux_log_output.setPlaceholderText("Remuxing operations will show status here (success and errors)")
        self.remux_log_output.setStyleSheet("""
            QLineEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 3px;
                padding: 5px;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.remux_log_output)
        
        layout.addStretch()
        tab.setLayout(layout)
        return tab
    
    def add_remux_files(self):
        """Add video files to the remux selection and analyze tracks."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Video Files (MKV/MP4)",
            str(get_downloads_dir()),
            "Video Files (*.mkv *.mp4);;All Files (*)"
        )
        
        if not file_paths:
            return
        
        # Add new files (avoid duplicates)
        for file_path in file_paths:
            video_path = Path(file_path)
            if video_path not in self.remux_selected_files:
                self.remux_selected_files.append(video_path)
                # Initialize file config
                self.remux_file_configs[video_path] = {
                    'output_format': self.remux_default_output_format.currentData(),
                    'subtitle_file': None,
                    'subtitle_language': 'eng',
                    'subtitle_default': True,
                    'selected_video_tracks': [],
                    'selected_audio_tracks': [],
                    'selected_subtitle_tracks': []
                }
                # Add to tree widget
                self.add_file_to_tree(video_path)
                # Auto-match subtitle if same-name SRT/VTT exists (same dir or Subtitles dir)
                self._attach_matching_subtitle_for_file(video_path)
        
        self.update_remux_file_count()
    
    def _attach_matching_subtitle_for_file(self, video_path: Path) -> bool:
        """If a same-name SRT/VTT exists, attach it to this file's config and update tree. Returns True if attached."""
        sub_path = get_matching_subtitle_for_remux(video_path)
        if not sub_path or video_path not in self.remux_file_configs:
            return False
        self.remux_file_configs[video_path]['subtitle_file'] = sub_path
        root = self.remux_files_tree.invisibleRootItem()
        for i in range(root.childCount()):
            file_item = root.child(i)
            if file_item.data(0, 256) == str(video_path):
                sub_btn = self.remux_file_configs.get(video_path, {}).get('subtitle_btn')
                if sub_btn:
                    sub_btn.setText("✓ Set")
                    sub_btn.setToolTip(sub_path.name)
                return True
        return False
    
    def auto_match_remux_subtitles(self):
        """For each video in the list, find a same-name SRT/VTT (same folder or Subtitles folder) and attach it."""
        matched = 0
        for video_path in self.remux_selected_files:
            if self._attach_matching_subtitle_for_file(video_path):
                matched += 1
        if matched > 0:
            self.remux_log_output.setText(f"Auto-matched {matched} subtitle(s) (same name as video).")
        else:
            self.remux_log_output.setText("No matching subtitle files found (look for .srt/.vtt with same name in video folder or Subtitles folder).")
    
    def add_file_to_tree(self, video_path: Path):
        """Add a file to the tree widget with its tracks."""
        if not video_path.exists():
            return
        
        config = self.remux_file_configs.get(video_path, {})
        sub_path = config.get('subtitle_file')
        
        # Create file item - collapsed by default for cleaner view
        file_item = QTreeWidgetItem(self.remux_files_tree)
        file_item.setText(0, video_path.name)
        file_item.setText(1, "File")
        file_item.setExpanded(False)  # Tracks hidden until user expands
        file_item.setData(0, 256, str(video_path))  # Store path in data
        
        # Per-file controls on the file row
        format_combo = QComboBox()
        format_combo.addItem("MKV", "mkv")
        format_combo.addItem("MP4", "mp4")
        default_format = config.get('output_format', 'mkv')
        format_index = format_combo.findData(default_format)
        if format_index >= 0:
            format_combo.setCurrentIndex(format_index)
        format_combo.currentIndexChanged.connect(
            lambda idx, path=video_path: self.update_file_output_format(path, format_combo.currentData()))
        format_combo.setMaximumWidth(70)
        self.remux_files_tree.setItemWidget(file_item, 2, format_combo)
        
        # Col 3 (Language): lang + default - matches column header
        opts_row = QWidget()
        opts_row.setMaximumWidth(130)  # Keep within Language column
        opts_layout = QHBoxLayout(opts_row)
        opts_layout.setContentsMargins(0, 0, 0, 0)
        opts_layout.setSpacing(6)
        lang_combo = QComboBox()
        lang_combo.addItems(["eng", "und", "fra", "spa", "deu", "ita", "jpn", "kor", "por", "rus", "ara", "chi"])
        lang_combo.setCurrentText(config.get('subtitle_language', 'eng'))
        lang_combo.setMaximumWidth(52)
        lang_combo.currentTextChanged.connect(
            lambda lang, path=video_path: self._update_subtitle_lang(path, lang))
        opts_layout.addWidget(lang_combo)
        default_cb = QCheckBox("Default")
        default_cb.setChecked(config.get('subtitle_default', True))
        default_cb.stateChanged.connect(
            lambda s, path=video_path: self._update_subtitle_default(path, s == 2))
        opts_layout.addWidget(default_cb)
        opts_layout.addStretch()
        self.remux_files_tree.setItemWidget(file_item, 3, opts_row)
        
        # Col 4 (Channels): subtitle file button - file row repurposes Channels for this
        sub_btn = QPushButton("+ Add" if not sub_path else "✓ Set")
        sub_btn.setFixedWidth(52)
        sub_btn.setToolTip(sub_path.name if sub_path else "Add subtitle file (SRT/VTT)")
        sub_btn.clicked.connect(lambda checked, path=video_path: self.browse_subtitle_file(path))
        self.remux_files_tree.setItemWidget(file_item, 4, sub_btn)
        self.remux_file_configs[video_path]['subtitle_btn'] = sub_btn
        
        remux_btn = QPushButton("Remux")
        remux_btn.setMaximumWidth(80)
        remux_btn.clicked.connect(lambda checked, path=video_path: self.remux_single_file(path))
        self.remux_files_tree.setItemWidget(file_item, 5, remux_btn)
        
        # Analyze tracks and add as children (visible when expanded)
        tracks = analyze_tracks(video_path)
        
        # Add video tracks
        if tracks['video']:
            for vid_track in tracks['video']:
                track_item = QTreeWidgetItem(file_item)
                track_id = vid_track.get('track_id', 0)
                codec = vid_track.get('codec', 'unknown')
                res = vid_track.get('resolution', 'unknown')
                track_item.setText(0, f"Video {track_id}")
                track_item.setText(1, "Video")
                track_item.setText(2, codec)
                track_item.setText(3, vid_track.get('language', 'unknown'))
                track_item.setText(4, res)
                # Add checkbox
                track_item.setCheckState(0, 1)  # Checked by default
                track_item.setData(0, 256, f"video:{track_id}")  # Store track info
        
        # Add audio tracks
        if tracks['audio']:
            for aud_track in tracks['audio']:
                track_item = QTreeWidgetItem(file_item)
                track_id = aud_track.get('track_id', 0)
                codec = aud_track.get('codec', 'unknown')
                channels = aud_track.get('channels', 0)
                sample_rate = aud_track.get('sample_rate', 'unknown')
                track_item.setText(0, f"Audio {track_id}")
                track_item.setText(1, "Audio")
                track_item.setText(2, codec)
                track_item.setText(3, aud_track.get('language', 'unknown'))
                track_item.setText(4, f"{channels}ch, {sample_rate}Hz")
                # Add checkbox
                track_item.setCheckState(0, 1)  # Checked by default
                track_item.setData(0, 256, f"audio:{track_id}")  # Store track info
        
        # Add embedded subtitle tracks
        if tracks['subtitles']:
            for sub_track in tracks['subtitles']:
                track_item = QTreeWidgetItem(file_item)
                track_id = sub_track.get('track_id', 0)
                format_type = sub_track.get('format', sub_track.get('codec', 'unknown'))
                track_item.setText(0, f"Subtitle {track_id}")
                track_item.setText(1, "Subtitle")
                track_item.setText(2, format_type)
                track_item.setText(3, sub_track.get('language', 'unknown'))
                track_item.setText(4, "")
                # Add checkbox
                track_item.setCheckState(0, 0)  # Unchecked by default (external subs preferred)
                track_item.setData(0, 256, f"subtitle:{track_id}")  # Store track info
    
    def remove_remux_files(self):
        """Remove selected files from the remux selection."""
        selected_items = self.remux_files_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select files to remove.")
            return
        
        # Get top-level items (files) from selection
        files_to_remove = []
        for item in selected_items:
            # If it's a top-level item (file), use it directly
            parent = item.parent()
            if parent is None:
                # It's a file item
                file_path_str = item.data(0, 256)
                if file_path_str:
                    files_to_remove.append(Path(file_path_str))
            else:
                # It's a track item, get the parent file
                file_path_str = parent.data(0, 256)
                if file_path_str and Path(file_path_str) not in files_to_remove:
                    files_to_remove.append(Path(file_path_str))
        
        # Remove files
        for file_path in files_to_remove:
            if file_path in self.remux_selected_files:
                self.remux_selected_files.remove(file_path)
            if file_path in self.remux_file_configs:
                del self.remux_file_configs[file_path]
            
            # Remove from tree
            root = self.remux_files_tree.invisibleRootItem()
            for i in range(root.childCount()):
                child = root.child(i)
                if child.data(0, 256) == str(file_path):
                    root.removeChild(child)
                    break
        
        self.update_remux_file_count()
    
    def clear_remux_files(self):
        """Clear all selected files."""
        self.remux_selected_files.clear()
        self.remux_file_configs.clear()
        self.remux_files_tree.clear()
        self.update_remux_file_count()
    
    def browse_subtitle_file(self, video_path: Path):
        """Browse for external subtitle file for a specific video."""
        subtitle_file, _ = QFileDialog.getOpenFileName(
            self, f"Select Subtitle File for {video_path.name}",
            str(get_subtitles_dir()),
            "Subtitle Files (*.srt *.vtt);;All Files (*)"
        )
        
        if subtitle_file:
            self.remux_file_configs[video_path]['subtitle_file'] = Path(subtitle_file)
            sub_btn = self.remux_file_configs.get(video_path, {}).get('subtitle_btn')
            if sub_btn:
                sub_btn.setText("✓ Set")
                sub_btn.setToolTip(Path(subtitle_file).name)
    
    def update_file_output_format(self, video_path: Path, output_format: str):
        """Update output format for a specific file."""
        if video_path in self.remux_file_configs:
            self.remux_file_configs[video_path]['output_format'] = output_format
    
    def _update_subtitle_lang(self, video_path: Path, lang: str):
        """Update subtitle language for a file."""
        if video_path in self.remux_file_configs:
            self.remux_file_configs[video_path]['subtitle_language'] = lang
    
    def _update_subtitle_default(self, video_path: Path, is_default: bool):
        """Update subtitle default flag for a file."""
        if video_path in self.remux_file_configs:
            self.remux_file_configs[video_path]['subtitle_default'] = is_default
    
    def remux_single_file(self, video_path: Path):
        """Remux a single file with its configured tracks and options."""
        if video_path not in self.remux_file_configs:
            self.remux_log_output.setText(f"Error: Configuration not found for {video_path.name}")
            return
        
        config = self.remux_file_configs[video_path]
        output_format = config['output_format']
        
        # Get selected tracks from tree
        root = self.remux_files_tree.invisibleRootItem()
        file_item = None
        for i in range(root.childCount()):
            child = root.child(i)
            if child.data(0, 256) == str(video_path):
                file_item = child
                break
        
        if not file_item:
            self.remux_log_output.setText(f"Error: File not found in tree")
            return
        
        # Collect selected tracks
        selected_video = []
        selected_audio = []
        selected_subtitles = []
        external_subtitle = config.get('subtitle_file')
        
        for i in range(file_item.childCount()):
            track_item = file_item.child(i)
            if track_item.checkState(0) == 2:  # Checked
                track_data = track_item.data(0, 256)
                if track_data:
                    track_type, track_id = track_data.split(':')
                    track_id = int(track_id)
                    if track_type == 'video':
                        selected_video.append(track_id)
                    elif track_type == 'audio':
                        selected_audio.append(track_id)
                    elif track_type == 'subtitle':
                        selected_subtitles.append(track_id)
        
        # Remux the file
        self.remux_log_output.setText(f"Remuxing {video_path.name}...")
        sub_lang = config.get('subtitle_language', 'eng')
        sub_default = config.get('subtitle_default', True)
        success = self.remux_file_with_tracks(
            video_path, output_format, selected_video, selected_audio,
            selected_subtitles, external_subtitle,
            subtitle_language=sub_lang, subtitle_default=sub_default
        )
        
        if success:
            base = video_path.stem
            out_path = video_path.parent / f"{base}_remuxed.{output_format}"
            self.remux_log_output.setText(f"✓ Saved: {out_path}")
        else:
            # Preserve FFmpeg error if already set
            if not self.remux_log_output.text().startswith("Error:"):
                self.remux_log_output.setText(f"✗ Failed to remux {video_path.name}")
    
    def remux_file_with_tracks(self, video_path: Path, output_format: str,
                               video_tracks: List[int], audio_tracks: List[int],
                               subtitle_tracks: List[int], external_subtitle: Path = None,
                               subtitle_language: str = 'eng', subtitle_default: bool = True) -> bool:
        """Remux a file with specific track selections.
        
        Note: Track IDs from analyze_tracks correspond to FFmpeg stream indices.
        subtitle_language and subtitle_default apply to the external subtitle when present.
        """
        if not video_path.exists():
            return False
        
        base = video_path.stem
        output_file = video_path.parent / f"{base}_remuxed.{output_format}"
        
        if output_file.exists():
            return True  # Already exists
        
        # Build FFmpeg command with track selection
        ffmpeg_exe = get_ffmpeg_command(self.config)
        cmd = [ffmpeg_exe, "-y", "-i", str(video_path)]
        
        # Map selected tracks (track_id from analyze_tracks is the stream index)
        for vid_track in video_tracks:
            cmd.extend(["-map", f"0:{vid_track}"])
        
        for aud_track in audio_tracks:
            cmd.extend(["-map", f"0:{aud_track}"])
        
        for sub_track in subtitle_tracks:
            cmd.extend(["-map", f"0:{sub_track}"])
        
        # Add external subtitle if provided
        if external_subtitle and external_subtitle.exists():
            cmd.extend(["-i", str(external_subtitle)])
            cmd.extend(["-map", "1:0"])  # Map first stream from second input
            subtitle_format = "srt" if external_subtitle.suffix.lower() == ".srt" else "vtt"
            cmd.extend(["-c:s", subtitle_format])
            # External sub is at index len(subtitle_tracks) among subtitle streams
            sub_idx = len(subtitle_tracks)
            cmd.extend(["-metadata:s:s:" + str(sub_idx), f"language={subtitle_language}"])
            if subtitle_default:
                cmd.extend(["-disposition:s:s:" + str(sub_idx), "default"])
        
        # If no tracks explicitly selected, include all tracks (default)
        if not video_tracks and not audio_tracks and not subtitle_tracks:
            # Rebuild command to include all tracks
            cmd = [ffmpeg_exe, "-y", "-i", str(video_path)]
            
            # Add external subtitle if provided
            if external_subtitle and external_subtitle.exists():
                cmd.extend(["-i", str(external_subtitle)])
                cmd.extend(["-map", "0"])  # Map all tracks from video
                cmd.extend(["-map", "1:0"])  # Map subtitle from external file
                subtitle_format = "srt" if external_subtitle.suffix.lower() == ".srt" else "vtt"
                cmd.extend(["-c:v", "copy", "-c:a", "copy", "-c:s", subtitle_format])
                tracks_info = analyze_tracks(video_path)
                sub_idx = len(tracks_info.get('subtitles', []))
                cmd.extend(["-metadata:s:s:" + str(sub_idx), f"language={subtitle_language}"])
                if subtitle_default:
                    cmd.extend(["-disposition:s:s:" + str(sub_idx), "default"])
            else:
                # Check for auto-detected subtitle file
                folder_path = video_path.parent
                base = video_path.stem
                srt_file = folder_path / f"{base}.srt"
                vtt_file = folder_path / f"{base}.vtt"
                
                if srt_file.exists():
                    cmd.extend(["-i", str(srt_file)])
                    cmd.extend(["-map", "0"])  # All video tracks
                    cmd.extend(["-map", "1:0"])  # Subtitle
                    cmd.extend(["-c:v", "copy", "-c:a", "copy", "-c:s", "srt"])
                elif vtt_file.exists():
                    cmd.extend(["-i", str(vtt_file)])
                    cmd.extend(["-map", "0"])  # All video tracks
                    cmd.extend(["-map", "1:0"])  # Subtitle
                    cmd.extend(["-c:v", "copy", "-c:a", "copy", "-c:s", "vtt"])
                else:
                    # Just copy all tracks
                    cmd.extend(["-c", "copy"])
            
            cmd.append(str(output_file))
        else:
            # Copy codecs: avoid -c copy with -c:s (causes "stream type specified multiple times")
            if external_subtitle and external_subtitle.exists():
                cmd.extend(["-c:v", "copy", "-c:a", "copy"])  # -c:s already added above
            else:
                cmd.extend(["-c", "copy"])
            cmd.append(str(output_file))
        
        # Execute
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode != 0:
                # Log error to minimal log
                error_msg = result.stderr.split('\n')[-5:] if result.stderr else ["Unknown error"]
                self.remux_log_output.setText(f"Error: {'; '.join(error_msg)}")
            return result.returncode == 0 and output_file.exists()
        except Exception as e:
            self.remux_log_output.setText(f"Error: {str(e)}")
            return False
    
    def remux_selected_files_action(self):
        """Remux all selected files in the tree."""
        selected_items = self.remux_files_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select files to remux.")
            return
        
        # Get top-level file items
        files_to_remux = []
        for item in selected_items:
            parent = item.parent()
            if parent is None:
                # It's a file item
                file_path_str = item.data(0, 256)
                if file_path_str:
                    files_to_remux.append(Path(file_path_str))
            else:
                # It's a track item, get the parent file
                file_path_str = parent.data(0, 256)
                if file_path_str and Path(file_path_str) not in files_to_remux:
                    files_to_remux.append(Path(file_path_str))
        
        if not files_to_remux:
            self.remux_log_output.setText("Error: No files selected")
            return
        
        # Remux each file
        success_count = 0
        for video_path in files_to_remux:
            self.remux_single_file(video_path)
            if self.remux_log_output.text().startswith("✓"):
                success_count += 1
        
        if success_count > 0:
            self.remux_log_output.setText(f"✓ Remuxed {success_count}/{len(files_to_remux)} files")
    
    def show_track_context_menu(self, position):
        """Show context menu for track items."""
        item = self.remux_files_tree.itemAt(position)
        if not item:
            return
        
        # Check if it's a track item (has parent and track data)
        parent = item.parent()
        if not parent:
            return  # It's a file item, not a track
        
        track_data = item.data(0, 256)
        if not track_data or track_data in ["external_subtitle", "output_format", "remux_action"]:
            return  # Not a track item
        
        # Create context menu
        menu = QMenu(self)
        
        # Get track info
        track_type, track_id = track_data.split(':')
        track_id = int(track_id)
        
        # Get file path
        file_path_str = parent.data(0, 256)
        if not file_path_str:
            return
        
        file_path = Path(file_path_str)
        
        # Add actions
        info_action = menu.addAction("Show Track Info")
        menu.addSeparator()
        modify_action = menu.addAction("Modify Track Properties...")
        
        # Show menu
        action = menu.exec_(self.remux_files_tree.mapToGlobal(position))
        
        if action == info_action:
            self.show_track_info(file_path, track_type, track_id)
        elif action == modify_action:
            self.modify_track_properties(file_path, track_type, track_id, item)
    
    def show_track_info(self, file_path: Path, track_type: str, track_id: int):
        """Show detailed information for a specific track."""
        tracks = analyze_tracks(file_path)
        
        track_info = None
        if track_type == 'video':
            track_info = next((t for t in tracks['video'] if t.get('track_id') == track_id), None)
        elif track_type == 'audio':
            track_info = next((t for t in tracks['audio'] if t.get('track_id') == track_id), None)
        elif track_type == 'subtitle':
            track_info = next((t for t in tracks['subtitles'] if t.get('track_id') == track_id), None)
        
        if not track_info:
            QMessageBox.warning(self, "Error", "Track information not found.")
            return
        
        # Create info dialog
        info_dialog = QDialog(self)
        info_dialog.setWindowTitle(f"Track {track_id} Info - {file_path.name}")
        info_dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        info_text = QTextEdit()
        info_text.setReadOnly(True)
        info_text.setFont(QFont("Courier New", 10))
        
        info_lines = [f"Track Type: {track_type.upper()}", f"Track ID: {track_id}", ""]
        for key, value in track_info.items():
            info_lines.append(f"{key.replace('_', ' ').title()}: {value}")
        
        info_text.setText('\n'.join(info_lines))
        layout.addWidget(info_text)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(info_dialog.accept)
        layout.addWidget(close_btn)
        
        info_dialog.setLayout(layout)
        info_dialog.exec_()
    
    def modify_track_properties(self, file_path: Path, track_type: str, track_id: int, tree_item: QTreeWidgetItem):
        """Open dialog to modify track properties (language, default flags, etc.)."""
        # For now, show a simple dialog - can be enhanced later
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Modify Track {track_id} - {file_path.name}")
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout()
        
        info_label = QLabel(f"Track modification for {track_type} track {track_id}")
        layout.addWidget(info_label)
        
        # Language selection
        lang_label = QLabel("Language:")
        lang_combo = QComboBox()
        lang_combo.addItems(["eng", "fra", "spa", "deu", "ita", "jpn", "kor", "ara", "chi", "unknown"])
        layout.addWidget(lang_label)
        layout.addWidget(lang_combo)
        
        # Note about modification
        note_label = QLabel("Note: Track modifications are applied during remuxing.\nUse mkvpropedit for in-place modifications.")
        note_label.setWordWrap(True)
        note_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(note_label)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(dialog.accept)
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            # Store language preference for this track (can be used during remux)
            if file_path not in self.remux_file_configs:
                self.remux_file_configs[file_path] = {'track_languages': {}}
            elif 'track_languages' not in self.remux_file_configs[file_path]:
                self.remux_file_configs[file_path]['track_languages'] = {}
            
            track_key = f"{track_type}:{track_id}"
            self.remux_file_configs[file_path]['track_languages'][track_key] = lang_combo.currentText()
            
            # Update tree display
            tree_item.setText(3, lang_combo.currentText())
    
    def show_media_info(self):
        """Show detailed media information for selected file(s)."""
        selected_items = self.remux_files_tree.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "No Selection", "Please select a file to view media info.")
            return
        
        # Get the file from selection
        file_path = None
        for item in selected_items:
            parent = item.parent()
            if parent is None:
                # It's a file item
                file_path_str = item.data(0, 256)
                if file_path_str:
                    file_path = Path(file_path_str)
                    break
            else:
                # It's a track item, get the parent file
                file_path_str = parent.data(0, 256)
                if file_path_str:
                    file_path = Path(file_path_str)
                    break
        
        if not file_path or not file_path.exists():
            QMessageBox.warning(self, "Error", "File not found.")
            return
        
        # Create and show media info dialog
        dialog = MediaInfoDialog(self, file_path)
        dialog.exec_()
    
    def update_remux_file_count(self):
        """Update the file count label."""
        count = len(self.remux_selected_files)
        if count == 0:
            self.remux_file_count_label.setText("No files selected")
        elif count == 1:
            self.remux_file_count_label.setText("1 file selected")
        else:
            self.remux_file_count_label.setText(f"{count} files selected")
    
    
    def split_audio_channels_batch(self):
        """Batch split audio channels for selected video files."""
        if not self.remux_selected_files:
            QMessageBox.warning(self, "No Files", "Please add files first.")
            return
        
        # Analyze first file to get channel count
        first_file = self.remux_selected_files[0]
        if not first_file.exists():
            self.remux_log_output.setText(f"Error: File not found: {first_file.name}")
            return
        
        tracks = analyze_tracks(first_file)
        if not tracks['audio']:
            self.remux_log_output.setText("Error: No audio tracks found in video files.")
            return
        
        channel_count = tracks['audio'][0].get('channels', 0)
        if channel_count == 0:
            self.remux_log_output.setText("Error: Could not determine audio channel count.")
            return
        
        # Create minimal log callback
        success_count = 0
        errors = []
        
        def split_log_callback(msg):
            nonlocal success_count
            if "✓ Extracted channel" in msg:
                success_count += 1
            elif "Error:" in msg or "✗" in msg:
                errors.append(msg)
                if len(errors) == 1:
                    self.remux_log_output.setText(msg)
                else:
                    self.remux_log_output.setText(f"{len(errors)} error(s) occurred")
        
        self.remux_log_output.setText(f"Splitting audio channels ({channel_count} channels)...")
        
        # Process files directly (output to same directory as each file)
        for video_file in self.remux_selected_files:
            if video_file.exists():
                output_dir = video_file.parent
                split_audio_channels(video_file, output_dir, channel_count, split_log_callback)
        
        if errors:
            self.remux_log_output.setText(f"Error: {len(errors)} file(s) failed")
        else:
            self.remux_log_output.setText(f"✓ Split {channel_count} channels for {len(self.remux_selected_files)} file(s)")
    
    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle(f"SP Workshop (WLW video processing, translation & subtitling hub) v{__version__}")
        self.setMinimumSize(900, 700)
        
        # Get screen geometry and maximize height
        screen = QApplication.primaryScreen().availableGeometry()
        max_height = screen.height() - 50  # Leave some margin for menu bar/taskbar
        self.resize(900, max_height)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Header with app name
        header_left_layout = QVBoxLayout()
        header_left_layout.setSpacing(4)
        
        # App name with gradient background
        app_name_label = OutlinedLabel("SP WORKSHOP")
        app_name_label.setFont(QFont("Arial", 30, QFont.Bold))
        app_name_label.setStyleSheet("""
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #df4300, stop:0.20 #f48a32, stop:0.33 #ffab68,
                stop:0.5 white, stop:0.66 #dc7bb3, stop:0.80 #c46ea1, stop:1 #b42075);
            padding: 8px 16px;
            border-radius: 5px;
        """)
        
        header_left_layout.addWidget(app_name_label)
        
        # Version number below title
        version_label = QLabel(f'version {__version__} "{VERSION_CODENAME}"')
        version_label.setFont(QFont("Arial", 13))
        version_label.setStyleSheet("color: #999; font-style: italic;")
        header_left_layout.addWidget(version_label)
        
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)
        header_left_widget = QWidget()
        header_left_widget.setLayout(header_left_layout)
        header_layout.addWidget(header_left_widget)
        
        header_layout.addStretch()
        
        # Top bar with About, FAQ, and Settings
        about_btn = QPushButton("About")
        about_btn.clicked.connect(self.open_about)
        faq_btn = QPushButton("FAQ")
        faq_btn.clicked.connect(self.open_faq)
        settings_btn = QPushButton("Settings")
        settings_btn.clicked.connect(self.open_settings)
        header_layout.addWidget(about_btn)
        header_layout.addWidget(faq_btn)
        header_layout.addWidget(settings_btn)
        
        main_layout.addLayout(header_layout)
        
        # Main tabs
        self.main_tabs = QTabWidget()
        
        # Main tab
        main_tab = QWidget()
        layout = QVBoxLayout()
        main_tab.setLayout(layout)
        
        # Download section
        download_group = QGroupBox("DOWNLOAD")
        download_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        download_layout = QVBoxLayout()
        
        # Naming row
        naming_row1 = QHBoxLayout()
        naming_row1.addWidget(QLabel("Mode:"))
        self.download_mode_combo = QComboBox()
        self.download_mode_combo.addItems(["Episode(s)", "Movie"])
        self.download_mode_combo.setMaximumWidth(100)
        naming_row1.addWidget(self.download_mode_combo)

        naming_row1.addWidget(QLabel("Name:"))
        self.download_name_input = QLineEdit()
        self.download_name_input.setPlaceholderText("e.g. Show Name (2025)")
        self.download_name_input.setMinimumWidth(160)
        naming_row1.addWidget(self.download_name_input)

        self.download_s01e_check = QCheckBox("Use S01E02")
        self.download_s01e_check.setChecked(False)
        naming_row1.addWidget(self.download_s01e_check)

        self.download_season_label = QLabel("Season:")
        naming_row1.addWidget(self.download_season_label)
        self.download_season_spin = QSpinBox()
        self.download_season_spin.setMinimum(1)
        self.download_season_spin.setMaximum(99)
        self.download_season_spin.setValue(1)
        self.download_season_spin.setMaximumWidth(50)
        naming_row1.addWidget(self.download_season_spin)

        self.download_items_label = QLabel("Items:")
        naming_row1.addWidget(self.download_items_label)
        self.download_items_input = QLineEdit()
        self.download_items_input.setText("1")
        self.download_items_input.setMaximumWidth(120)
        self.download_items_input.setPlaceholderText("1 or 1-5 or 1,3,5-7")
        self.download_items_input.setToolTip("Episode numbers or range:\n• Single: 1\n• Range: 1-5\n• Mixed: 1,3,5-7,10")
        naming_row1.addWidget(self.download_items_input)

        naming_row1.addStretch()
        instructions_btn = QPushButton("How to get commands")
        instructions_btn.setFlat(True)
        instructions_btn.setStyleSheet("color: #0066cc; text-decoration: underline;")
        instructions_btn.setCursor(Qt.PointingHandCursor)
        instructions_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DOWNLOAD_INSTRUCTIONS_URL)))
        instructions_btn.setToolTip("Opens instructions in your browser")
        naming_row1.addWidget(instructions_btn)

        def _update_naming_visibility():
            is_episodes = self.download_mode_combo.currentText() == "Episode(s)"
            self.download_s01e_check.setVisible(is_episodes)
            show_season = is_episodes and self.download_s01e_check.isChecked()
            self.download_season_label.setVisible(show_season)
            self.download_season_spin.setVisible(show_season)
            self.download_items_label.setVisible(is_episodes)
            self.download_items_input.setVisible(is_episodes)
        _update_naming_visibility()
        self.download_mode_combo.currentTextChanged.connect(_update_naming_visibility)
        self.download_s01e_check.toggled.connect(_update_naming_visibility)

        download_layout.addLayout(naming_row1)
        
        download_label = QLabel("Commands (one per line, paste full command per instructions):")
        download_layout.addWidget(download_label)
        
        self.commands_text = QTextEdit()
        self.commands_text.setPlaceholderText(
            '"https://..." -H "..." --key KID:KEY\n'
            '"https://..." -H "..." --key KID:KEY\n'
            '(see How to get commands for format)'
        )
        self.commands_text.setMaximumHeight(120)
        self.commands_text.setMinimumHeight(80)
        download_layout.addWidget(self.commands_text)
        
        download_buttons = QHBoxLayout()
        self.download_quality_combo = QComboBox()
        # Resolution fallback
        for name, code in [
            ("480p", 'res="480":for=best'),
            ("720p", 'res="720|480":for=best'),
            ("1080p", 'res="1080|720|480":for=best'),
            ("4K", 'res="2160|1080|720|480":for=best'),
            ("Best quality", "best"),
        ]:
            self.download_quality_combo.addItem(name, code)
        self.download_quality_combo.setCurrentIndex(self.download_quality_combo.findData("best"))
        self.download_quality_combo.setMaximumWidth(120)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(lambda: self.commands_text.clear())
        download_btn = QPushButton("(Batch) Download")
        download_btn.clicked.connect(lambda: self.download_episodes(self.download_quality_combo.currentData()))
        open_lossless_btn = QPushButton("Open in LosslessCut...")
        open_lossless_btn.clicked.connect(self.open_lossless_cut)
        open_downloads_btn = QPushButton("Open Downloads folder")
        open_downloads_btn.clicked.connect(lambda: open_folder_in_explorer(get_downloads_dir()))
        download_buttons.addWidget(self.download_quality_combo)
        download_buttons.addWidget(download_btn)
        download_buttons.addWidget(clear_btn)
        download_buttons.addWidget(open_lossless_btn)
        download_buttons.addWidget(open_downloads_btn)
        download_layout.addLayout(download_buttons)
        download_group.setLayout(download_layout)
        layout.addWidget(download_group)
        
        # Subtitles section
        subtitles_group = QGroupBox("SUBTITLES")
        subtitles_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        subtitles_layout = QHBoxLayout()
        extract_btn = QPushButton("Extract subtitles")
        extract_btn.clicked.connect(self.extract_subtitles)
        clean_btn = QPushButton("Clean subtitles")
        clean_btn.clicked.connect(self.clean_subtitles)
        translate_btn = QPushButton("Translate subtitles")
        translate_btn.clicked.connect(self.translate_subtitles)
        open_subtitles_btn = QPushButton("Open subtitles folder")
        open_subtitles_btn.clicked.connect(lambda: open_folder_in_explorer(get_subtitles_dir()))
        subtitles_layout.addWidget(extract_btn)
        subtitles_layout.addWidget(clean_btn)
        subtitles_layout.addWidget(translate_btn)
        subtitles_layout.addWidget(open_subtitles_btn)
        subtitles_group.setLayout(subtitles_layout)
        layout.addWidget(subtitles_group)
        
        # Process video section
        process_group = QGroupBox("PROCESS VIDEO")
        process_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        process_layout = QHBoxLayout()
        process_720_btn = QPushButton("Burn subtitles + watermark (720p)")
        process_720_btn.clicked.connect(lambda: self.process_video("720"))
        process_1080_btn = QPushButton("Burn subtitles + watermark (1080p)")
        process_1080_btn.clicked.connect(lambda: self.process_video("1080"))
        open_output_btn = QPushButton("Open output folder")
        open_output_btn.clicked.connect(lambda: open_folder_in_explorer(get_output_dir()))
        process_layout.addWidget(process_720_btn)
        process_layout.addWidget(process_1080_btn)
        process_layout.addWidget(open_output_btn)
        process_group.setLayout(process_layout)
        layout.addWidget(process_group)
        
        # Progress section (above log output)
        progress_group = QGroupBox("PROGRESS")
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(8)
        
        # Operation type label
        self.progress_operation_label = QLabel("Ready")
        self.progress_operation_label.setFont(QFont("Arial", 10, QFont.Bold))
        progress_layout.addWidget(self.progress_operation_label)
        
        # Current file label
        self.progress_file_label = QLabel("")
        self.progress_file_label.setFont(QFont("Arial", 9))
        self.progress_file_label.setStyleSheet("color: #666;")
        progress_layout.addWidget(self.progress_file_label)
        
        # Progress bar with counter
        progress_bar_layout = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(25)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 5px;
                text-align: center;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #df4300, stop:0.2 #f48a32, stop:0.4 #ffab68,
                    stop:0.6 #dc7bb3, stop:0.8 #c46ea1, stop:1 #b42075);
                border-radius: 4px;
            }
        """)
        self.progress_counter_label = QLabel("")
        self.progress_counter_label.setFont(QFont("Arial", 9))
        self.progress_counter_label.setMinimumWidth(80)
        self.progress_counter_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        progress_bar_layout.addWidget(self.progress_bar)
        progress_bar_layout.addWidget(self.progress_counter_label)
        
        # Stop button
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setFixedWidth(80)
        self.stop_btn.clicked.connect(self.stop_operation)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #cc0000;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 4px 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #990000;
            }
            QPushButton:pressed {
                background-color: #660000;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.stop_btn.setToolTip("Stop the current operation (Ctrl+C)")
        progress_bar_layout.addWidget(self.stop_btn)
        
        progress_layout.addLayout(progress_bar_layout)
        
        progress_group.setLayout(progress_layout)
        progress_group.setVisible(False)  # Hidden by default
        layout.addWidget(progress_group)
        self.progress_group = progress_group  # Store reference
        
        # Log output
        log_group = QGroupBox("LOG OUTPUT")
        log_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        log_layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setFont(QFont("Monaco", 9))
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        # Add main tab to tabs widget
        self.main_tabs.addTab(main_tab, "Subtitles")
        
        # Add transcription tab
        transcription_tab = self.create_transcription_tab()
        self.main_tabs.addTab(transcription_tab, "Transcription")
        
        # Add remuxing tab
        remuxing_tab = self.create_remuxing_tab()
        self.main_tabs.addTab(remuxing_tab, "Remuxing")
        
        # Add tabs to main layout
        main_layout.addWidget(self.main_tabs)
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Apply lesbian flag color scheme to all buttons
        self.apply_lesbian_flag_styles()
        
        # Track current operation type for color coding
        self.current_operation = None
    
    
    def log(self, message: str):
        """Add a message to the log output."""
        self.log_output.append(message)
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )
    
    def open_about(self):
        """Open About dialog."""
        dialog = AboutDialog(self)
        dialog.exec_()
    
    def open_faq(self):
        """Open FAQ dialog."""
        dialog = FAQDialog(self)
        dialog.exec_()
    
    def open_settings(self):
        """Open settings dialog."""
        dialog = SettingsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.config = load_config()
            self.log("Settings saved.")
    
    def open_whisper_options(self):
        """Open Whisper advanced options dialog."""
        dialog = WhisperOptionsDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Reload config after whisper options are saved
            self.config = load_config()
            self.log("Whisper options updated.")
    
    def run_script(self, script_func, *args, **kwargs):
        """Run a script in a worker thread."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Busy", "Another operation is already running.")
            return
        
        # Operation from func name
        func_name = script_func.__name__
        operation_names = {
            "download_episodes": "Downloading episodes",
            "download_with_detection": "Downloading episodes",
            "extract_subtitles": "Extracting subtitles",
            "clean_subtitles": "Cleaning subtitles",
            "translate_subtitles": "Translating subtitles",
            "process_video": "Processing videos",
            "remux_mkv_with_srt_batch": "Remuxing videos",
            "transcribe_video": "Transcribing video",
            "transcribe_video_vad": "Transcribing video (long)",
        }
        self.current_operation = operation_names.get(func_name, "Processing")
        
        # Hide progress for downloads
        is_download = func_name in ["download_episodes", "download_with_detection"]
        self.progress_group.setVisible(not is_download)
        
        if not is_download:
            # Configure progress bar
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("%p%")
            self.progress_operation_label.setText(f"{self.current_operation}...")
            self.progress_file_label.setText("")
            self.progress_counter_label.setText("")
            self.update_progress_bar_color()
            # Enable stop
            self.stop_btn.setEnabled(True)
        
        self.statusBar().showMessage("Running...")
        
        self.worker = ScriptWorker(script_func, *args, **kwargs)
        self.worker.log_message.connect(self.log)
        self.worker.progress_update.connect(self.on_progress_update)
        self.worker.finished.connect(self.on_script_finished)
        self.worker.start()
    
    def update_progress_bar_color(self):
        """Update progress bar color based on operation type."""
        colors = {
            "Downloading episodes": "#df4300",  # Red
            "Extracting subtitles": "#f48a32",  # Orange
            "Cleaning subtitles": "#f48a32",  # Orange
            "Translating subtitles": "#ffab68",  # Light Orange
            "Processing videos": "#dc7bb3",  # Pink
            "Remuxing videos": "#c46ea1",  # Purple
            "Transcribing video": "#b42075",  # Dark Pink
        }
        
        color = colors.get(self.current_operation, "#df4300")
        hover_color = self.darken_color(color, 0.15)
        
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #ccc;
                border-radius: 5px;
                text-align: center;
                background-color: #f0f0f0;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)
    
    def on_progress_update(self, current: int, total: int, filename: str):
        """Handle progress update."""
        # Extract % from filename
        file_percentage = None
        if filename and '(' in filename and '%' in filename:
            try:
                # Get percentage
                match = re.search(r'\((\d+\.?\d*)%\)', filename)
                if match:
                    file_percentage = float(match.group(1))
            except (ValueError, AttributeError):
                pass
        
        if total > 0:
            if file_percentage is not None:
                # Combined progress
                completed_files_progress = ((current - 1) / total) * 100 if current > 1 else 0
                current_file_progress = (file_percentage / 100) * (100 / total)
                combined_percent = completed_files_progress + current_file_progress
                percent = int(min(100, max(0, combined_percent)))
            else:
                # Fallback progress
                percent = int((current / total) * 100)
            
            self.progress_bar.setValue(percent)
            self.progress_counter_label.setText(f"{current}/{total}")
        else:
            # Indeterminate progress
            self.progress_bar.setRange(0, 0)  # Indeterminate mode
            self.progress_counter_label.setText("")
        
        if filename:
            self.progress_file_label.setText(f"Current file: {filename}")
        else:
            self.progress_file_label.setText("")
        
        status_msg = f"{self.current_operation or 'Processing'}"
        if filename:
            status_msg += f" - {filename}"
        if total > 0:
            status_msg += f" ({current}/{total})"
        self.statusBar().showMessage(status_msg)
    
    def on_script_finished(self, success: bool):
        """Handle script completion."""
        self.progress_group.setVisible(False)
        self.progress_bar.setRange(0, 100)  # Reset to determinate mode
        self.progress_bar.setValue(0)
        self.progress_operation_label.setText("Ready")
        self.progress_file_label.setText("")
        self.progress_counter_label.setText("")
        self.current_operation = None
        self.statusBar().showMessage("Ready" if success else "Error occurred")
        # Disable stop button and reset text
        self.stop_btn.setEnabled(False)
        self.stop_btn.setText("Stop")
        if success:
            self.log("✓ Operation completed successfully.")
        else:
            self.log("✗ Operation failed. Check log for details.")
        self.worker = None
    
    def stop_operation(self):
        """Stop the currently running operation."""
        if self.worker and self.worker.isRunning():
            # Request the worker to stop
            self.worker.stop()
            # Disable the button to prevent multiple clicks
            self.stop_btn.setEnabled(False)
            self.stop_btn.setText("Stopping...")
            self.statusBar().showMessage("Stopping operation...")
            
            # Wait a moment for graceful shutdown, then terminate if needed
            QTimer.singleShot(3000, self.force_terminate_worker)
        else:
            self.log("No operation is currently running")
    
    def force_terminate_worker(self):
        """Force terminate the worker if it hasn't stopped gracefully."""
        if self.worker and self.worker.isRunning():
            self.log("⚠ Force terminating operation...")
            self.worker.terminate()
            self.worker.wait()
            self.on_script_finished(False)
        # Reset button text
        self.stop_btn.setText("Stop")
    
    def download_episodes(self, select_video: str = "best"):
        """Download episodes or movies."""
        commands_text = self.commands_text.toPlainText()
        if not commands_text.strip():
            QMessageBox.warning(self, "Error", "Please paste commands in the text area.")
            return

        mode = "episodes" if self.download_mode_combo.currentText() == "Episode(s)" else "movie"
        name = self.download_name_input.text().strip()
        use_s01e = self.download_s01e_check.isChecked()
        season = self.download_season_spin.value()
        ep_spec = self.download_items_input.text().strip() or "1"

        output_dir = get_downloads_dir()
        self.log(f"Starting download to: {output_dir}")
        self.log(f"Mode: {mode}, Name: {name or '(none)'}, S01E02: {use_s01e}, Items: {ep_spec}, Video: {select_video}")

        def download_with_detection(
            commands_text, output_dir, mode, name, use_s01e, season, ep_spec, select_video,
            progress_callback=None, log_callback=None,
        ):
            result = download_episodes(
                commands_text, output_dir,
                mode=mode, name=name, use_s01e=use_s01e, season=season, ep_spec=ep_spec,
                select_video=select_video,
                progress_callback=progress_callback, log_callback=log_callback,
            )
            if result:
                mkv_files = list(output_dir.glob("*.mkv"))
                for mkv_file in mkv_files:
                    video_type, duration = detect_episode_or_scene(mkv_file)
                    if duration is not None:
                        type_label = "Episode" if video_type == "episode" else "Scene"
                        if log_callback:
                            log_callback(f"  {mkv_file.name}: {type_label} ({duration:.1f} min)")
            return result

        self.run_script(
            download_with_detection,
            commands_text, output_dir, mode, name, use_s01e, season, ep_spec, select_video,
        )
    
    def extract_subtitles(self):
        """Extract subtitles."""
        downloads_dir = get_downloads_dir()
        subtitles_dir = get_subtitles_dir()
        
        self.log("Starting subtitle extraction...")
        self.run_script(extract_subtitles, downloads_dir, subtitles_dir)
    
    def clean_subtitles(self):
        """Clean subtitles."""
        subtitles_dir = get_subtitles_dir()
        
        self.log("Starting subtitle cleaning...")
        self.run_script(clean_subtitles, subtitles_dir)
    
    def translate_subtitles(self):
        """Translate subtitles."""
        env_key = os.getenv("GEMINI_API_KEY") or os.getenv("GST_API_KEY")
        api_keys = self.config.get("api_keys") or []
        if not api_keys and (self.config.get("api_key") or self.config.get("api_key2")):
            api_keys = [k for k in [self.config.get("api_key"), self.config.get("api_key2")] if k]
        if not env_key and not api_keys:
            QMessageBox.warning(
                self,
                "API Key Not Set",
                "API key not found.\n\n"
                "Recommended: Set GEMINI_API_KEY or GST_API_KEY environment variable.\n"
                "See Settings for instructions.\n\n"
                "You can also add keys in Settings (API Keys section)."
            )
            return

        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select SRT Files to Translate",
            str(get_subtitles_dir()),
            "Subtitle Files (*.srt);;All Files (*)"
        )

        if not file_paths:
            return

        gst_cmd = find_gst_command()
        if not gst_cmd:
            reply = QMessageBox.question(
                self,
                "Translator Not Found",
                "Translation requires gemini-srt-translator (gst).\n\n"
                "Would you like us to install it via pip?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                dlg = QDialog(self)
                dlg.setWindowTitle("Installing gemini-srt-translator...")
                dlg.setMinimumWidth(400)
                layout = QVBoxLayout()
                log = QTextEdit()
                log.setReadOnly(True)
                layout.addWidget(log)
                close_btn = QPushButton("Close")
                close_btn.setEnabled(False)
                layout.addWidget(close_btn)
                dlg.setLayout(layout)
                worker = PipInstallWorker(["gemini-srt-translator"])
                worker.log_message.connect(lambda m: log.append(m))
                def on_finished(ok):
                    if ok:
                        dlg.accept()
                    else:
                        log.append("\nInstallation failed. Click Close and try: python -m pip install gemini-srt-translator")
                        close_btn.setEnabled(True)
                close_btn.clicked.connect(dlg.accept)
                worker.finished.connect(on_finished)
                worker.start()
                dlg.exec_()
            return

        target_language = self.config.get("translation_target_language", "English")
        use_iso639 = self.config.get("use_iso639_suffixes", False)

        self.log(f"Starting subtitle translation for {len(file_paths)} file(s)...")
        self.log(f"Target language: {target_language}, ISO 639 suffixes: {'enabled' if use_iso639 else 'disabled'}")
        if api_keys:
            self.log(f"Using {len(api_keys)} API key(s) (quota retry enabled)")
        self.run_script(translate_subtitles, file_paths, target_language, use_iso639, api_keys)
    
    def process_video(self, resolution: str):
        """Process video."""
        # Open file picker to select video files
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, f"Select Video Files to Process ({resolution}p)",
            str(get_downloads_dir()),
            "Video Files (*.mkv *.mp4 *.mov);;All Files (*)"
        )
        
        if not file_paths:
            return
        
        subtitles_dir = get_subtitles_dir()
        output_dir = get_output_dir()
        
        use_watermarks = self.config.get("use_watermarks", True)
        watermark_key = f"watermark_{resolution}p"
        watermark_path = self.config.get(watermark_key, "")
        
        if use_watermarks:
            if not watermark_path or not Path(watermark_path).exists():
                QMessageBox.warning(
                    self, "Error",
                    f"Watermark file for {resolution}p not found. Please set it in Settings or disable watermarks."
                )
                return
        
        # Get ISO 639 settings from config
        use_iso639 = self.config.get("use_iso639_suffixes", False)
        target_language = self.config.get("translation_target_language", "English")
        
        self.log(f"Starting video processing ({resolution}p) for {len(file_paths)} file(s)...")
        if use_iso639:
            self.log(f"ISO 639 mode enabled - looking for .{ISO_639_CODES.get(target_language, 'eng')}.srt files")
        ffmpeg_path = self.config.get("ffmpeg_path", "").strip()
        downloads_dir = get_downloads_dir()
        self.run_script(
            process_video, file_paths, subtitles_dir, output_dir,
            watermark_path, resolution, use_watermarks, ffmpeg_path, use_iso639, target_language,
            downloads_dir
        )
    
    def open_lossless_cut(self):
        """Open video file(s) in LosslessCut."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Video Files to Open in LosslessCut",
            str(get_downloads_dir()),
            "Video Files (*.mkv *.mp4 *.mov);;All Files (*)"
        )
        
        if file_paths:
            video_paths = [Path(p) for p in file_paths]
            
            if len(video_paths) == 1:
                # For single file, show detailed info
                video_path = video_paths[0]
                video_type, duration = detect_episode_or_scene(video_path)
                
                if duration:
                    type_label = "Episode" if video_type == "episode" else "Scene"
                    self.log(f"Opening {video_path.name} in LosslessCut ({type_label}, {duration:.1f} min)")
                else:
                    self.log(f"Opening {video_path.name} in LosslessCut")
            else:
                # For multiple files, show count
                self.log(f"Opening {len(video_paths)} files in LosslessCut")
            
            open_in_lossless_cut(video_paths, log_callback=self.log)
    
    
    def transcribe_video(self):
        """Transcribe video file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video or Audio File to Transcribe",
            str(get_downloads_dir()),
            "Media Files (*.mkv *.mp4 *.mov *.mp3 *.wav);;All Files (*)"
        )
        
        if file_path:
            video_path = Path(file_path)
            
            # Show language selection dialog
            lang_dialog = LanguageDialog(self)
            if lang_dialog.exec_() != QDialog.Accepted:
                return  # User cancelled
            
            language_code = lang_dialog.get_language_code()
            
        # Get model from combo (saved to config automatically)
        model = self.transcribe_model_combo.currentText()
        
        # Get whisper options from config
        config = load_config()
        whisper_options = config.get("whisper_options", {})
        
        # Process extra_args: convert multiline to space-separated if needed
        if "extra_args" in whisper_options and "extra_args_parsed" not in whisper_options:
            extra_args_text = whisper_options.get("extra_args", "")
            extra_args = " ".join(line.strip() for line in extra_args_text.split("\n") if line.strip())
            whisper_options["extra_args_parsed"] = extra_args
        
        # Check if this is first time using transcription
        whisper_model_asked = config.get("whisper_model_asked", False)
        
        if not whisper_model_asked:
            # Ask user if they already have a model
            model_dialog = WhisperModelDialog(self, model)
            if model_dialog.exec_() != QDialog.Accepted:
                return  # User cancelled
            
            has_existing_model = model_dialog.get_result()
            
            # Save preference to config
            config["whisper_model_asked"] = True
            config["whisper_has_existing_model"] = has_existing_model
            save_config(config)
            
            if has_existing_model:
                self.log(f"Using existing Whisper model '{model}' from cache.")
            else:
                self.log(f"Will download Whisper model '{model}' on first use.")
            
            self.log(f"Starting transcription of: {video_path.name}")
            lang_display = "(detected from audio)" if language_code == "auto" else language_code
            self.log(f"Language: {lang_display}, Model: {model}")
            
            # Run transcription with language, model, and whisper options
            def transcribe_with_params(video_path, language_code, model, whisper_options, progress_callback=None, log_callback=None):
                return transcribe_video(video_path, language_code, model, whisper_options, progress_callback=progress_callback, log_callback=log_callback)
            
            self.run_script(transcribe_with_params, video_path, language_code, model, whisper_options)
    
# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    # Use Fusion style for better stylesheet support on macOS
    app.setStyle('Fusion')
    
    # Set application-wide icon BEFORE creating window
    # This ensures macOS uses it for dock icon at proper size
    icon = get_app_icon()
    app.setWindowIcon(icon)
    
    window = VideoProcessingApp()
    # Also set window icon (for title bar)
    window.setWindowIcon(icon)
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
