#!/usr/bin/env python3
# ============================================================================
# Version, imports, widgets
# ============================================================================
"""
Video Processing GUI Application
A PyQt5 desktop app that provides a button-based interface for all video processing scripts.
"""


__version__ = "10.4.0-alpha.12"
VERSION_CODENAME = "Rocket Launcher"

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
import inspect
import traceback
import platform
import tarfile
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List
try:
    from typing import Protocol, runtime_checkable
except ImportError:
    from typing_extensions import Protocol, runtime_checkable  # type: ignore


# Enforce Python 3.9–3.12 (PyQt5 + 3.13+ causes Qt plugin errors on macOS)
if sys.version_info >= (3, 13):
    print("SP Workshop requires Python 3.9–3.12.")
    print("Python 3.13+ causes Qt failures on macOS. Use Python 3.12:")
    print("  brew install python@3.12")
    print("  python3.12 -m venv .venv && source .venv/bin/activate")
    sys.exit(1)

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


# ============================================================================
# Qt widgets
# ============================================================================
# Fix Qt "cocoa" plugin not found on macOS (often works first run, fails on second).
# An empty QT_QPA_PLATFORM_PLUGIN_PATH makes Qt look nowhere; unset it so Qt uses defaults.
# Must run before any PyQt5 QtWidgets/QtGui imports.
if platform.system() == "Darwin":
    if os.environ.get("QT_QPA_PLATFORM_PLUGIN_PATH", "x") == "":
        os.environ.pop("QT_QPA_PLATFORM_PLUGIN_PATH", None)

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QTextEdit, QFileDialog, QDialog,
        QLineEdit, QFormLayout, QMessageBox, QProgressBar, QGroupBox, QStyleFactory, QCheckBox, QStackedWidget, QTextBrowser, QComboBox,
        QGraphicsDropShadowEffect, QTabWidget, QSpinBox, QDoubleSpinBox, QScrollArea, QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu, QFrame, QSizePolicy,
    )
    from PyQt5.QtCore import QThread, pyqtSignal, Qt, QProcess, QUrl, QTimer
    from PyQt5.QtGui import QFont, QIcon, QPainter, QPen, QDesktopServices
except ImportError as e:
    print("SP Workshop needs PyQt5.")
    print("Activate your virtual environment, then run: pip install PyQt5")
    print("Or: python -m pip install -r requirements.txt")
    print(f"(Error: {e})")
    sys.exit(1)


# ============================================================================
# Constants
# ============================================================================  

# Download instructions URL
DOWNLOAD_INSTRUCTIONS_URL = "https://rentry.co/sp-workshop"
DEFAULT_WHISPER_VOLUME_BOOST = 1.75

# Layout spacing (used across tabs for consistency)
LAYOUT_SPACING = 12
SECTION_SPACING = 8
LOG_MIN_HEIGHT = 100

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
# Custom widgets
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
# Configuration management
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
        "whisper_cpp_extra_args": "",
        "whisper_cpp_vad_model": "",
        "clean_subtitles_fixes": {
            "remove_empty_lines": True,
            "fix_invalid_italic_tags": True,
            "fix_overlapping_display_times": True,
            "fix_short_display_times": True,
            "fix_long_display_times": True,
            "fix_short_gaps": True,
            "remove_unneeded_spaces": True,
            "fix_missing_spaces": True,
            "break_long_lines": True,
            "split_dialogs_on_one_line": True,
            "remove_dialog_dashes_single_line": True,
            "remove_start_dash_non_dialogs": True,
            "strip_leading_spaces": True,
        },
        "whisper_post_processing_enabled":         False,
        "whisper_post_proc_adjust_timings":        True,
        "whisper_post_proc_merge_lines":           True,
        "whisper_post_proc_split_lines":           True,
        "whisper_post_proc_fix_short_duration":    True,
        "whisper_post_proc_add_periods":           True,
        "whisper_post_proc_fix_casing":            True,
    }
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                # Merge whisper_options with defaults
                if "whisper_options" in user_config:
                    default_config["whisper_options"].update(user_config["whisper_options"])
                    del user_config["whisper_options"]
                # Merge clean_subtitles_fixes with defaults
                if "clean_subtitles_fixes" in user_config:
                    default_config["clean_subtitles_fixes"].update(user_config["clean_subtitles_fixes"])
                    del user_config["clean_subtitles_fixes"]
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
# Directory & file system management
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
    
    Note: Master asset is media/icon-source.png; regenerate icon.icns / icon.ico / icon.png with
    media/build_app_icon.sh (ImageMagick + macOS iconutil). Use at least 1024×1024; transparent
    logos work well; full-bleed iOS-style masters often use ICON_PLATE=none ICON_INSET_PERCENT=100.
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
# Video & media analysis
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
# Downloader helper functions
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


def _parse_n_m3u8dl_progress(line: str) -> Optional[str]:
    """Parse an N_m3u8DL-RE progress bar line into a compact status string.

    Returns a formatted string like
      "Vid 1920x1080 | 5002 Kbps | Main · 23/212 segs · 11.15 MBps · ETA 00:01:35"
    or None if the line cannot be parsed.
    """
    clean = _strip_ansi(line).replace("\r", "").strip()
    if not clean:
        return None

    # Format 1: Unicode progress bar lines (contains "━")
    bar_idx = clean.find('━')
    if bar_idx >= 0:
        label = clean[:bar_idx].strip()
        if not label:
            return None
        after_bar = clean[bar_idx:]
        seg_match = re.search(r'(\d+)/(\d+)', after_bar)
        segments = seg_match.group(0) if seg_match else '?/?'
        speed_match = re.search(r'[\d.]+\s*[KMG]?B(?:ps|/s)', after_bar, re.IGNORECASE)
        speed = speed_match.group(0).strip() if speed_match else '-'
        eta_match = re.search(r'\d{2}:\d{2}:\d{2}|--:--:--', after_bar)
        eta = eta_match.group(0) if eta_match else '--:--:--'
        return f"{label} · {segments} segs · {speed} · ETA {eta}"

    # Format 2: INFO lines in the style:
    # "INFO : Vid ... | 3023 Kbps | ... | 214 Segments | Main | ~28m26s"
    if "|" not in clean or "segment" not in clean.lower():
        return None
    payload = clean.split("INFO :", 1)[-1].strip()
    parts = [p.strip() for p in payload.split("|") if p.strip()]
    if not parts:
        return None

    label = parts[0]
    bitrate = next((p for p in parts if re.search(r'\b\d+(?:\.\d+)?\s*[KMG]bps\b', p, re.IGNORECASE)), None)
    segments = next((p for p in parts if re.search(r'\b\d+\s+Segments?\b', p, re.IGNORECASE)), None)
    eta = next(
        (p for p in parts if p.startswith("~") or re.search(r'\d{1,2}m\d{1,2}s|--:--:--|\d{2}:\d{2}:\d{2}', p)),
        None,
    )

    out = [label]
    if bitrate:
        out.append(bitrate)
    if segments:
        out.append(segments)
    if eta:
        out.append(f"ETA {eta}" if eta.startswith("~") else eta)
    return " · ".join(out)


# ============================================================================
# Download & subtitle pipeline
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
    stream_progress_callback=None,
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
                last_progress_emit: dict = {}  # stream_label -> last emit time (seconds)

                while True:
                    line_output = process.stdout.readline()
                    if not line_output:
                        break
                    is_progress_bar = '━' in line_output
                    if not is_progress_bar:
                        cleaned = _strip_ansi(line_output)
                        debug_file.write(cleaned)
                        debug_file.flush()
                    line_output = line_output.strip()
                    if line_output:
                        output_lines.append(line_output)

                        is_progress_bar = '━' in line_output

                        if stream_progress_callback:
                            parsed = _parse_n_m3u8dl_progress(line_output)
                            if parsed:
                                # Use the part before ' · ' as stream key to throttle.
                                stream_key = parsed.split(' · ')[0]
                                now = time.time()
                                if now - last_progress_emit.get(stream_key, 0) >= 1.0:
                                    last_progress_emit[stream_key] = now
                                    stream_progress_callback(parsed)

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

                        # Drive the stream-status label with key milestone lines
                        if should_log and stream_progress_callback:
                            clean_line = _strip_ansi(line_output)
                            if 'Start downloading' in clean_line:
                                desc = clean_line.split('Start downloading...', 1)[-1].strip()
                                if desc:
                                    stream_progress_callback(f"Downloading: {desc[:100]}")
                            elif 'Binary merging' in clean_line:
                                stream_progress_callback("Merging segments…")
                            elif 'Decrypting using' in clean_line:
                                stream_progress_callback("Decrypting…")
                            elif 'Muxing to' in clean_line:
                                dest = clean_line.split('Muxing to', 1)[-1].strip()
                                stream_progress_callback(f"Muxing: {dest}")

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


# ============================================================================
# Fix common errors (SRT parsing + 12 fixes)
# ============================================================================

# Fix key -> (display label, example) for CleanSubtitlesDialog
CLEAN_SUBTITLES_FIX_ITEMS = [
    ("remove_empty_lines",              "Remove empty lines",                   'Line with only spaces --> [removed]'),
    ("fix_invalid_italic_tags",         "Fix invalid italic tags",              '<i>text<i> --> <i>text</i>'),
    ("fix_overlapping_display_times",   "Fix overlapping display times",        '00:00:05,000 --> 00:00:07,000 (overlaps next)'),
    ("fix_short_display_times",         "Fix short display times",              'Duration < minimum --> end time extended'),
    ("fix_long_display_times",          "Fix long display times",               'Duration > maximum --> clamp end time'),
    ("fix_short_gaps",                  "Fix short gaps",                       'Gap < 24 ms --> trim previous end'),
    ("remove_unneeded_spaces",          "Remove unneeded spaces",               'Hey  you --> Hey you'),
    ("fix_missing_spaces",              "Fix missing spaces",                   'Hey.You  Hey. You'),
    ("break_long_lines",                "Break long lines",                     'Very long line --> split at space'),
    ("split_dialogs_on_one_line",       "Split dialogs on one line",            'A. - B --> A.\n- B'),
    ("remove_dialog_dashes_single_line","Remove dialog dashes in single lines", '- Text --> Text'),
    ("remove_start_dash_non_dialogs",   "Remove start dash in non-dialogs",     '- Text --> Text'),
    ("strip_leading_spaces",            "Strip leading spaces",                 ' Hello --> Hello'),
]
CLEAN_SUBTITLES_FIX_LABELS = {item[0]: item[1] for item in CLEAN_SUBTITLES_FIX_ITEMS}

# Default config for fix logic
FIX_CONFIG_DEFAULTS = {
    "subtitle_minimum_display_ms": 1000,
    "subtitle_maximum_display_ms": 8000,
    "minimum_ms_between_lines": 24,
    "subtitle_line_max_length": 43,
    "subtitle_max_chars_per_second": 25,
}



def _parse_srt(content: str) -> List[Dict]:
    """Parse SRT content into list of {start_ms, end_ms, text} dicts."""
    entries = []
    blocks = re.split(r'\n\s*\n', content.strip())
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) < 2:
            continue
        # First line: index (optional)
        # Second line: 00:00:00,000 --> 00:00:01,000
        time_line = lines[1] if lines[0].isdigit() else lines[0]
        text_lines = lines[2:] if lines[0].isdigit() else lines[1:]
        m = re.match(r'(\d{2}):(\d{2}):(\d{2})[,.](\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2})[,.](\d{3})', time_line)
        if not m:
            continue
        start_ms = int(m.group(1)) * 3600000 + int(m.group(2)) * 60000 + int(m.group(3)) * 1000 + int(m.group(4))
        end_ms = int(m.group(5)) * 3600000 + int(m.group(6)) * 60000 + int(m.group(7)) * 1000 + int(m.group(8))
        text = '\n'.join(text_lines).strip()
        entries.append({"start_ms": start_ms, "end_ms": end_ms, "text": text})
    return entries


def _format_srt(entries: List[Dict]) -> str:
    """Serialize entries back to SRT format."""
    out = []
    for i, e in enumerate(entries, 1):
        h1, m1, s1, ms1 = e["start_ms"] // 3600000, (e["start_ms"] % 3600000) // 60000, (e["start_ms"] % 60000) // 1000, e["start_ms"] % 1000
        h2, m2, s2, ms2 = e["end_ms"] // 3600000, (e["end_ms"] % 3600000) // 60000, (e["end_ms"] % 60000) // 1000, e["end_ms"] % 1000
        out.append(f"{i}\n{h1:02d}:{m1:02d}:{s1:02d},{ms1:03d} --> {h2:02d}:{m2:02d}:{s2:02d},{ms2:03d}\n{e['text']}\n")
    return '\n'.join(out)


# ============================================================================
# Whisper CPP post-processing helpers
# ============================================================================

def _pp_adjust_timings(entries: List[Dict], audio_path) -> List[Dict]:
    """Snap subtitle start times to actual speech/silence boundaries.

    Uses the already-extracted 16 kHz mono WAV (Python built-in wave + array,
    no external deps).  Mirrors WhisperTimingFixer.ShortenViaWavePeaks logic:
    for each entry, if the audio around the start time is above a silence
    threshold, scan ±250 ms to find a quieter boundary and snap to it.
    """
    import wave as _wave
    import array as _array

    try:
        with _wave.open(str(audio_path), 'rb') as wf:
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2:
                return entries
            sample_rate = wf.getframerate()
            raw = wf.readframes(wf.getnframes())
        samples = _array.array('h', raw)
    except Exception:
        return entries

    # Pre-compute RMS in 25 ms windows for the whole file
    win_samples = max(1, int(sample_rate * 0.025))
    n_windows = len(samples) // win_samples
    if n_windows == 0:
        return entries

    rms_windows: List[float] = []
    for w in range(n_windows):
        chunk = samples[w * win_samples:(w + 1) * win_samples]
        rms_windows.append((sum(x * x for x in chunk) / len(chunk)) ** 0.5)

    peak_rms = max(rms_windows) if rms_windows else 1.0
    if peak_rms == 0:
        return entries
    SILENCE_THRESH = 0.07  # 7 % of peak — matches SE source

    def rms_at_ms(ms: int) -> float:
        w = int(ms / 25)
        if 0 <= w < len(rms_windows):
            return rms_windows[w] / peak_rms
        return 1.0  # treat out-of-range as non-silence

    result = []
    for idx, entry in enumerate(entries):
        prev_end_ms = result[-1]["end_ms"] if result else 0
        start = entry["start_ms"]

        # If already in silence, scan forward to find speech onset
        if rms_at_ms(start) < SILENCE_THRESH:
            pos = start
            while pos < entry["end_ms"] - 600 and rms_at_ms(pos) < SILENCE_THRESH:
                pos += 25
            if pos > start and pos < entry["end_ms"] - 100:
                start = max(prev_end_ms + 1, pos - 25)
        else:
            # In speech — scan back up to 250 ms to find silence boundary
            best = start
            best_rms = rms_at_ms(start)
            for delta in range(25, 276, 25):
                candidate = start - delta
                if candidate <= prev_end_ms:
                    break
                r = rms_at_ms(candidate)
                if r < best_rms:
                    best_rms = r
                    best = candidate
                if r < SILENCE_THRESH:
                    break
            start = max(prev_end_ms + 1, best)

        new_entry = dict(entry)
        if start < entry["end_ms"] - 100:
            new_entry["start_ms"] = start
        result.append(new_entry)

    return result


def _pp_fix_short_duration(entries: List[Dict], min_ms: int = 1000) -> List[Dict]:
    """Extend entries whose display time is below min_ms.

    The end time is pushed forward to reach min_ms, capped so it does not
    exceed the midpoint to the next entry's start.
    """
    result = [dict(e) for e in entries]
    for i, e in enumerate(result):
        dur = e["end_ms"] - e["start_ms"]
        if dur < min_ms:
            desired_end = e["start_ms"] + min_ms
            if i + 1 < len(result):
                cap = e["start_ms"] + (result[i + 1]["start_ms"] - e["start_ms"]) // 2
                desired_end = min(desired_end, cap)
            e["end_ms"] = max(e["end_ms"], desired_end)
    return result


def _pp_merge_short_lines(entries: List[Dict], max_gap_ms: int = 100, max_chars: int = 86) -> List[Dict]:
    """Merge consecutive entries that are close together and short.

    Two entries are merged when gap ≤ max_gap_ms AND their combined text
    (separated by a space) does not exceed max_chars.  Mirrors
    AudioToTextPostProcessor.MergeShortLines logic.
    """
    if not entries:
        return entries
    result = []
    skip_next = False
    for i in range(len(entries)):
        if skip_next:
            skip_next = False
            continue
        e = dict(entries[i])
        if i + 1 < len(entries):
            nxt = entries[i + 1]
            gap = nxt["start_ms"] - e["end_ms"]
            combined = e["text"].strip() + " " + nxt["text"].strip()
            if 0 <= gap <= max_gap_ms and len(combined) <= max_chars:
                e["text"] = combined.strip()
                e["end_ms"] = nxt["end_ms"]
                skip_next = True
        result.append(e)
    return result


def _pp_split_long_lines(entries: List[Dict], max_chars: int = 43) -> List[Dict]:
    """Break long text into two lines inside the same subtitle cue.

    Important: this is a line-break step, not a cue-splitting step.
    Timings stay unchanged; only text formatting is adjusted.
    """
    result = []
    for e in entries:
        text = e["text"].strip()
        if len(text) <= max_chars or "\n" in text:
            result.append(e)
            continue

        # Normalize internal spacing so line-length checks are meaningful.
        text = re.sub(r"\s+", " ", text).strip()
        words = text.split(" ")
        if len(words) < 2:
            result.append({**e, "text": text})
            continue

        # Choose split point that best balances line lengths.
        best_idx = 1
        best_score = float("inf")
        for i in range(1, len(words)):
            left = " ".join(words[:i])
            right = " ".join(words[i:])
            score = max(len(left), len(right))
            if score < best_score:
                best_score = score
                best_idx = i

        part1 = " ".join(words[:best_idx]).strip()
        part2 = " ".join(words[best_idx:]).strip()
        if not part1 or not part2:
            result.append({**e, "text": text})
            continue

        result.append({**e, "text": f"{part1}\n{part2}"})
    return result


def _pp_add_periods(entries: List[Dict], gap_ms: int = 600) -> List[Dict]:
    """Add a period at the end of an entry when the gap to the next is > gap_ms.

    Matches AudioToTextPostProcessor.AddPeriods: only adds if the text does not
    already end with terminal punctuation.
    """
    _terminal = set('.!?,:])}')
    result = [dict(e) for e in entries]
    for i, e in enumerate(result):
        text = e["text"].rstrip()
        if not text or text[-1] in _terminal:
            continue
        if i + 1 < len(result):
            gap = result[i + 1]["start_ms"] - e["end_ms"]
            if gap > gap_ms:
                e["text"] = text + "."
        else:
            # Last entry always gets a period
            e["text"] = text + "."
    return result


def _pp_fix_casing(entries: List[Dict]) -> List[Dict]:
    """Capitalise the first letter of each entry's text."""
    result = []
    for e in entries:
        text = e["text"]
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        result.append({**e, "text": text})
    return result


def _whisper_cpp_post_process(
    final_srt,
    audio_path,
    config: Dict,
    log_callback=None,
) -> None:
    """Apply post-processing pipeline to a freshly written whisper.cpp SRT.

    Steps are controlled by individual config keys and the master
    whisper_post_processing_enabled toggle.  audio_path is needed only for
    the adjust-timings step and may be None.
    """
    if not config.get("whisper_post_processing_enabled", False):
        if log_callback:
            log_callback("  Post-processing skipped (disabled).")
        return
    try:
        raw = final_srt.read_text(encoding="utf-8")
        entries = _parse_srt(raw)
        if not entries:
            return

        if config.get("whisper_post_proc_adjust_timings", True) and audio_path and Path(audio_path).exists():
            entries = _pp_adjust_timings(entries, audio_path)

        if config.get("whisper_post_proc_fix_short_duration", True):
            entries = _pp_fix_short_duration(entries)

        if config.get("whisper_post_proc_merge_lines", True):
            entries = _pp_merge_short_lines(entries)

        if config.get("whisper_post_proc_split_lines", True):
            entries = _pp_split_long_lines(entries)

        if config.get("whisper_post_proc_add_periods", True):
            entries = _pp_add_periods(entries)

        if config.get("whisper_post_proc_fix_casing", True):
            entries = _pp_fix_casing(entries)

        final_srt.write_text(_format_srt(entries), encoding="utf-8")
        if log_callback:
            log_callback("  Post-processing applied.")
    except Exception as e:
        if log_callback:
            log_callback(f"  Post-processing error (skipped): {e}")


def _fix_empty_lines(entries: List[Dict], config: Dict, ctx=None) -> int:
    """Remove empty lines and fully empty paragraphs."""
    count = 0
    ACT_TEXT = "Fix empty lines"
    ACT_REM  = "Remove empty entry"
    i = len(entries) - 1
    while i >= 0:
        e = entries[i]
        text = e["text"]
        stripped = re.sub(r'<[^>]+>', '', text).strip()
        if not stripped:
            before = dict(e)
            if not ctx or ctx.allow(e.get("_id", i), ACT_REM):
                entries.pop(i)
                count += 1
                if ctx:
                    ctx.record(ACT_REM, before,
                               {"start_ms": before["start_ms"], "end_ms": before["end_ms"], "text": "[removed]"})
            i -= 1
            continue
        # Trim + collapse double newlines; remove lone dash lines
        new_text = re.sub(r'\n\n+', '\n', text.strip())
        arr = new_text.split('\n')
        if len(arr) == 2:
            if arr[0].strip() == '-' and len(arr[1]) > 2:
                new_text = arr[1].lstrip('-').lstrip()
            elif arr[1].strip() == '-' and len(arr[0]) > 2:
                new_text = arr[0].lstrip('-').lstrip()
        if new_text != text:
            before = dict(e)
            if not ctx or ctx.allow(e.get("_id", i), ACT_TEXT):
                e["text"] = new_text
                count += 1
                if ctx:
                    ctx.record(ACT_TEXT, before, e)
        i -= 1
    return count


def _fix_invalid_italic_tags(entries: List[Dict], config: Dict, ctx=None) -> int:
    """Fix unclosed/swapped italic tags."""
    count = 0
    ACTION = "Fix invalid italic tags"
    for i, e in enumerate(entries):
        text = e["text"]
        new_text = re.sub(r'<i\s*/>', '</i>', text, flags=re.I)
        opens  = len(re.findall(r'<i\s*>',  new_text, re.I))
        closes = len(re.findall(r'</i\s*>', new_text, re.I))
        if opens == 2 and closes == 0:
            last_open = new_text.rfind('<i>')
            if last_open >= 0:
                new_text = new_text[:last_open] + '</i>' + new_text[last_open + 3:]
        elif opens > closes:
            for _ in range(opens - closes):
                last_i = new_text.rfind('<i>')
                if last_i >= 0:
                    end = new_text.find('>', last_i) + 1
                    new_text = new_text[:end] + '</i>' + new_text[end:]
        if new_text != text:
            before = dict(e)
            if not ctx or ctx.allow(e.get("_id", i), ACTION):
                e["text"] = new_text
                count += 1
                if ctx:
                    ctx.record(ACTION, before, e)
    return count


def _fix_overlapping_display_times(entries: List[Dict], config: Dict, ctx=None) -> int:
    """Fix overlapping and negative duration."""
    count = 0
    min_dur = config.get("subtitle_minimum_display_ms", 1000)
    ACTION = "Fix overlapping display times"
    for i, e in enumerate(entries):
        dur = e["end_ms"] - e["start_ms"]
        if dur < 0:
            before = dict(e)
            if not ctx or ctx.allow(e.get("_id", i), ACTION):
                e["end_ms"] = e["start_ms"] + min_dur
                count += 1
                if ctx:
                    ctx.record(ACTION, before, e)
        if i > 0 and e["start_ms"] < entries[i - 1]["end_ms"]:
            prev = entries[i - 1]
            before_prev = dict(prev)
            if not ctx or ctx.allow(prev.get("_id", i - 1), ACTION):
                prev["end_ms"] = e["start_ms"] - 1
                if prev["end_ms"] < prev["start_ms"]:
                    prev["end_ms"] = prev["start_ms"] + min_dur
                count += 1
                if ctx:
                    ctx.record(ACTION, before_prev, prev)
    return count


def _fix_short_display_times(entries: List[Dict], config: Dict, ctx=None) -> int:
    """Extend short display times if next allows."""
    count = 0
    min_dur = config.get("subtitle_minimum_display_ms", 1000)
    ACTION = "Fix short display time"
    for i, e in enumerate(entries):
        dur = e["end_ms"] - e["start_ms"]
        if dur < min_dur and i + 1 < len(entries):
            gap = entries[i + 1]["start_ms"] - e["end_ms"]
            need = min_dur - dur
            if gap > need:
                before = dict(e)
                if not ctx or ctx.allow(e.get("_id", i), ACTION):
                    e["end_ms"] += need
                    count += 1
                    if ctx:
                        ctx.record(ACTION, before, e)
    return count


def _fix_long_display_times(entries: List[Dict], config: Dict, ctx=None) -> int:
    """Cap long display times."""
    count = 0
    max_dur = config.get("subtitle_maximum_display_ms", 8000)
    ACTION = "Fix long display time"
    for i, e in enumerate(entries):
        dur = e["end_ms"] - e["start_ms"]
        if dur > max_dur:
            before = dict(e)
            if not ctx or ctx.allow(e.get("_id", i), ACTION):
                e["end_ms"] = e["start_ms"] + max_dur
                count += 1
                if ctx:
                    ctx.record(ACTION, before, e)
    return count


def _fix_short_gaps(entries: List[Dict], config: Dict) -> int:
    """Ensure minimum gap between subtitles."""
    count = 0
    min_gap = config.get("minimum_ms_between_lines", 24)
    for i in range(len(entries) - 1):
        gap = entries[i + 1]["start_ms"] - entries[i]["end_ms"]
        if 0 <= gap < min_gap:
            entries[i]["end_ms"] = entries[i + 1]["start_ms"] - min_gap
            count += 1
    return count


def _remove_unneeded_spaces(entries: List[Dict], config: Dict, ctx=None) -> int:
    """Remove zero-width chars, collapse spaces, normalize ellipses."""
    count = 0
    zw = '\u200B\uFEFF\u009D'
    ACTION = "Remove unneeded spaces"
    for i, e in enumerate(entries):
        text = e["text"]
        new_text = text
        for c in zw:
            new_text = new_text.replace(c, '')
        new_text = new_text.replace('\t', ' ').replace('\u00A0', ' ')
        new_text = re.sub(r' +', ' ', new_text)
        new_text = re.sub(r'\. \. \.', '...', new_text)
        new_text = re.sub(r'\.{4,}', '...', new_text)
        if new_text != text:
            before = dict(e)
            if not ctx or ctx.allow(e.get("_id", i), ACTION):
                e["text"] = new_text
                count += 1
                if ctx:
                    ctx.record(ACTION, before, e)
    return count


def _fix_missing_spaces(entries: List[Dict], config: Dict, ctx=None) -> int:
    """Insert missing spaces after punctuation."""
    count = 0
    ACTION = "Fix missing spaces"
    for i, e in enumerate(entries):
        text = e["text"]
        new_text = re.sub(r'([^\s\d]),([^\s])', r'\1, \2', text)
        new_text = re.sub(r'([a-z]{2})\.([A-Za-z])', r'\1. \2', new_text)
        new_text = re.sub(r'([^\s\d])([?!])([A-Za-z])', r'\1\2 \3', new_text)
        new_text = re.sub(r'([a-zA-Z])(<i>)', r'\1 \2', new_text, flags=re.I)
        new_text = re.sub(r'(</i>)([a-zA-Z])', r'\1 \2', new_text, flags=re.I)
        if new_text != text:
            before = dict(e)
            if not ctx or ctx.allow(e.get("_id", i), ACTION):
                e["text"] = new_text
                count += 1
                if ctx:
                    ctx.record(ACTION, before, e)
    return count


def _break_long_lines(entries: List[Dict], config: Dict, ctx=None) -> int:
    """Break lines longer than max length at spaces."""
    count = 0
    max_len = config.get("subtitle_line_max_length", 43)
    ACTION = "Break long lines"
    for i, e in enumerate(entries):
        lines = e["text"].split('\n')
        new_lines = []
        changed = False
        for line in lines:
            if len(line) <= max_len:
                new_lines.append(line)
                continue
            parts = line.split(' ')
            curr: List[str] = []
            curr_len = 0
            for p in parts:
                if curr_len + len(p) + (1 if curr else 0) > max_len and curr:
                    new_lines.append(' '.join(curr))
                    curr = [p]
                    curr_len = len(p)
                    changed = True
                else:
                    curr.append(p)
                    curr_len += len(p) + (1 if len(curr) > 1 else 0)
            if curr:
                new_lines.append(' '.join(curr))
        if changed:
            new_text = '\n'.join(new_lines)
            before = dict(e)
            if not ctx or ctx.allow(e.get("_id", i), ACTION):
                e["text"] = new_text
                count += 1
                if ctx:
                    ctx.record(ACTION, before, e)
    return count


def _split_dialogs_on_one_line(entries: List[Dict], config: Dict, ctx=None) -> int:
    """Split 'A - B' style dialogs onto two lines."""
    count = 0
    ACTION = "Split dialog on one line"
    for i, e in enumerate(entries):
        text = e["text"]
        if '\n' in text or ' - ' not in text:
            continue
        m = re.search(r'([.!?…")\]])\s*-\s+([A-Z"\'\u2669\u266a])', text)
        if m:
            pos = m.start(2) - 2
            new_text = text[:pos] + '\n- ' + text[pos + 3:]
            before = dict(e)
            if not ctx or ctx.allow(e.get("_id", i), ACTION):
                e["text"] = new_text
                count += 1
                if ctx:
                    ctx.record(ACTION, before, e)
    return count


def _remove_dialog_dashes_single_line(entries: List[Dict], config: Dict, ctx=None) -> int:
    """Remove leading dash when single sentence (no dialog)."""
    count = 0
    ACTION = "Remove dialog dash (single line)"
    for i, e in enumerate(entries):
        text = e["text"]
        stripped = text.strip()
        if not stripped.startswith('-') and not stripped.startswith('\u2010'):
            continue
        if ' - ' in text or '\n' in text:
            continue
        new_text = re.sub(r'^[\s\-‐\-]+', '', stripped)
        if new_text != stripped:
            before = dict(e)
            if not ctx or ctx.allow(e.get("_id", i), ACTION):
                e["text"] = new_text
                count += 1
                if ctx:
                    ctx.record(ACTION, before, e)
    return count


def _remove_start_dash_non_dialogs(entries: List[Dict], config: Dict, ctx=None) -> int:
    """Remove leading dash when not dialog structure."""
    count = 0
    ACTION = "Remove start dash (non-dialog)"
    for i, e in enumerate(entries):
        text = e["text"]
        if not (text.strip().startswith('-') or text.strip().startswith('\u2010')):
            continue
        if re.search(r'[.!?]\s*-\s', text):
            continue
        new_text = re.sub(r'^[\s\-‐\-]+', '', text.strip()).strip()
        if new_text != text.strip():
            before = dict(e)
            if not ctx or ctx.allow(e.get("_id", i), ACTION):
                e["text"] = new_text
                count += 1
                if ctx:
                    ctx.record(ACTION, before, e)
    return count


def _fix_strip_leading_spaces(entries: List[Dict], config: Dict, ctx=None) -> int:
    """Remove leading spaces from each text line (Whisper CPP tokenizer artifact)."""
    count = 0
    ACTION = "Strip leading spaces"
    for i, e in enumerate(entries):
        text = e["text"]
        new_text = '\n'.join(line.lstrip(' ') for line in text.split('\n'))
        if new_text != text:
            before = dict(e)
            if not ctx or ctx.allow(e.get("_id", i), ACTION):
                e["text"] = new_text
                count += 1
                if ctx:
                    ctx.record(ACTION, before, e)
    return count


_FIX_MAP = {
    "remove_empty_lines":               _fix_empty_lines,
    "fix_invalid_italic_tags":          _fix_invalid_italic_tags,
    "fix_overlapping_display_times":    _fix_overlapping_display_times,
    "fix_short_display_times":          _fix_short_display_times,
    "fix_long_display_times":           _fix_long_display_times,
    "fix_short_gaps":                   _fix_short_gaps,
    "remove_unneeded_spaces":           _remove_unneeded_spaces,
    "fix_missing_spaces":               _fix_missing_spaces,
    "break_long_lines":                 _break_long_lines,
    "split_dialogs_on_one_line":        _split_dialogs_on_one_line,
    "remove_dialog_dashes_single_line": _remove_dialog_dashes_single_line,
    "remove_start_dash_non_dialogs":    _remove_start_dash_non_dialogs,
    "strip_leading_spaces":             _fix_strip_leading_spaces,
}


def _apply_fixes_to_content(content: str, enabled_fixes: List[str], config: Dict) -> tuple:
    """Apply enabled fixes to SRT content. Returns (new_content, change_summary)."""
    entries = _parse_srt(content)
    if not entries:
        return content, {}
    cfg = {**FIX_CONFIG_DEFAULTS, **config}
    summary = {}
    for key in enabled_fixes:
        if key in _FIX_MAP:
            n = _FIX_MAP[key](entries, cfg)
            if n > 0:
                summary[key] = n
    return _format_srt(entries), summary



def clean_subtitles(subtitles_dir: Path, enabled_fixes: Optional[List[str]] = None,
                    progress_callback=None, log_callback=None) -> bool:
    """Remove color tags (always) and optionally apply fix common errors to subtitle files."""
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
    fixes_list = enabled_fixes or []
    
    if log_callback:
        log_callback(f"Starting subtitle cleaning for {total} file(s)...")
        if fixes_list:
            log_callback(f"Applying: Remove color tags (always) + {len(fixes_list)} fix(es)")
            labels = [CLEAN_SUBTITLES_FIX_LABELS.get(k, k) for k in fixes_list]
            log_callback(f"Selected fixes: {', '.join(labels)}")
    
    for idx, srt_file in enumerate(srt_files, start=1):
        if progress_callback:
            progress_callback(idx, total, srt_file.name)
        
        try:
            file_size = srt_file.stat().st_size
            file_size_kb = file_size / 1024
            
            with open(srt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 1. Always remove color tags
            cleaned = re.sub(r'<c\.[a-zA-Z0-9_]+>', '', content)
            cleaned = re.sub(r'</c\.[a-zA-Z0-9_]+>', '', cleaned)
            
            # 2. Apply selected fixes (strip_leading_spaces handled in entries pipeline)
            summary = {}
            if fixes_list:
                cleaned, fix_summary = _apply_fixes_to_content(cleaned, fixes_list, {})
                summary.update(fix_summary)
            
            if cleaned != content:
                with open(srt_file, 'w', encoding='utf-8') as f:
                    f.write(cleaned)
                cleaned_count += 1
                if log_callback:
                    tags_removed = len(re.findall(r'<c\.[a-zA-Z0-9_]+>|</c\.[a-zA-Z0-9_]+>', content))
                    if fixes_list and summary:
                        parts = [
                            f"{CLEAN_SUBTITLES_FIX_LABELS.get(k, k)}: {v}"
                            for k, v in summary.items()
                        ]
                        if tags_removed:
                            parts.append(f"Removed color tags: {tags_removed}")
                        summary_str = ", ".join(parts)
                        log_callback(f"  ✓ Cleaned: {srt_file.name} ({file_size_kb:.1f} KB) — {summary_str}")
                    elif not fixes_list:
                        log_callback(f"  ✓ Cleaned: {srt_file.name} ({file_size_kb:.1f} KB, removed {tags_removed} color tag(s))")
                    else:
                        change_hint = f", removed {tags_removed} color tag(s)" if tags_removed else ", formatting updates applied"
                        log_callback(f"  ✓ Cleaned: {srt_file.name} ({file_size_kb:.1f} KB{change_hint})")
            else:
                skipped_count += 1
                if log_callback:
                    log_callback(f"  ○ Skipped: {srt_file.name} ({file_size_kb:.1f} KB, no changes)")
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

    gst_cmd = find_gst_command()
    if not gst_cmd:
        if log_callback:
            log_callback("Error: gst command not found. Install gemini-srt-translator (gst) or add it to PATH.")
        return False

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

# ============================================================================
# Video processing pipeline
# ============================================================================

def process_video(selected_video_files: List[Path], subtitles_dir: Path, output_dir: Path,
                 watermark_path: str, resolution: str, use_watermarks: bool = True,
                 config: Optional[Dict] = None, use_iso639: bool = False, target_language: str = "English",
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
        ffmpeg_exe = get_ffmpeg_command(config, require_libass=True)
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
                        # Detect missing subtitles filter (FFmpeg without libass)
                        err_text = " ".join(error_lines).lower()
                        if "no such filter" in err_text and "subtitles" in err_text:
                            log_callback("")
                            log_callback("    FFmpeg lacks the subtitles filter (needs libass).")
                            log_callback("    Run: brew install ffmpeg-full")
                            log_callback("    The app will use it automatically. Or set path in Settings > Tools.")
        
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
        ffmpeg_exe = get_ffmpeg_command()
        # Extract audio first, then split channels
        temp_audio = output_dir / f"{base_name}_temp_audio.wav"
        
        # First extract audio to WAV
        cmd_extract = [
            ffmpeg_exe, '-i', str(video_path),
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
                ffmpeg_exe, '-i', str(temp_audio),
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
        ffmpeg_exe = get_ffmpeg_command()
        if target_format == 'mp3':
            cmd = [
                ffmpeg_exe, '-i', str(video_path),
                '-vn', '-acodec', 'libmp3lame', '-b:a', '192k',
                '-ar', '44100', '-y', str(output_path)
            ]
        elif target_format == 'aac':
            cmd = [
                ffmpeg_exe, '-i', str(video_path),
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
            py = _host_python_for_module_cli()
            if not py:
                if log_callback:
                    log_callback("No system Python found to create whisper-env (bundled app cannot use its own binary as python).")
                return None
            subprocess.run(
                [py, "-m", "venv", str(env_dir)],
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


# ============================================================================
# Transcription engines
# ============================================================================

def _get_whisper_cpp_binary(config: Dict) -> Optional[Path]:
    """Resolve Whisper CPP executable. Config whisper_cpp_path overrides; else check PATH."""
    user_path = (config.get("whisper_cpp_path") or "").strip()
    if user_path:
        p = Path(user_path).expanduser()
        if p.is_file():
            return p.resolve()
        if p.is_dir():
            for name in ("whisper-cli", "whisper-cpp", "main"):
                exe = p / (name + (".exe" if os.name == "nt" else ""))
                if exe.exists():
                    return exe.resolve()
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


def _extract_audio_for_transcription(
    video_path: Path,
    output_path: Path,
    config: Dict,
    log_callback=None,
) -> bool:
    """Extract 16 kHz mono WAV from *video_path* into *output_path* using FFmpeg.

    Uses a fixed internal volume boost for all backends. This is the single
    shared preprocessing step used by all transcription backends.
    """
    volume = DEFAULT_WHISPER_VOLUME_BOOST
    ffmpeg_exe = get_ffmpeg_command(config)
    if log_callback:
        log_callback(f"Extracting audio (16 kHz mono, volume={volume})...")
    result = subprocess.run(
        [
            ffmpeg_exe, "-y", "-i", str(video_path),
            "-vn", "-ar", "16000", "-ac", "1",
            "-af", f"volume={volume}",
            "-f", "wav", str(output_path),
            "-loglevel", "warning", "-hide_banner",
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if result.returncode != 0:
        if log_callback:
            log_callback(f"FFmpeg error: {result.stderr or result.stdout}")
        return False
    if not output_path.exists():
        if log_callback:
            log_callback("FFmpeg did not produce audio file.")
        return False
    return True


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
        srt_out_dir = get_subtitles_dir()
        audio_stem = f"{base_name}_whisper_cpp"
        audio_path = video_dir / f"{audio_stem}.wav"

        existing = list(video_dir.glob(f"{audio_stem}*"))
        if existing:
            n = 1
            while (video_dir / f"{audio_stem}_{n}.wav").exists():
                n += 1
            audio_stem = f"{audio_stem}_{n}"
            audio_path = video_dir / f"{audio_stem}.wav"

        if not _extract_audio_for_transcription(video_path, audio_path, config, log_callback):
            return False

        # whisper-cli writes <stem>.srt; we point it at a temp location in video_dir
        # then move the result to the subtitles folder.
        output_stem = str(video_dir / base_name)

        # On macOS: Homebrew/build-from-source often embeds Metal (GGML_METAL_EMBED_LIBRARY=ON),
        # so ggml-metal.metal may not exist on disk. Try Metal first; fallback to -ng if init fails.
        metal_dir = None
        no_gpu_args = []
        if sys.platform == "darwin":
            binary_dir = Path(binary).parent
            metal_path = binary_dir / "ggml-metal.metal"
            if metal_path.exists():
                metal_dir = str(binary_dir)  # External file: point GGML_METAL_PATH_RESOURCES at it
            # Do NOT add -ng when file is missing: embedded Metal builds (Homebrew) work without it.

        # VAD: whisper.cpp uses ggml-silero-v6.2.0.bin (ggml format) from ggml-org/whisper-vad.
        # See https://huggingface.co/ggml-org/whisper-vad/discussions/1
        VAD_MODEL_FILENAME = "ggml-silero-v6.2.0.bin"
        vad_args = []
        vad_model_path = (config.get("whisper_cpp_vad_model") or "").strip()
        if vad_model_path:
            vad_model_path = str(Path(vad_model_path).expanduser())
        if not vad_model_path or not Path(vad_model_path).exists():
            home = Path.home()
            vad_cache = home / ".cache" / "whisper.cpp"
            for candidate in (
                vad_cache / VAD_MODEL_FILENAME,
                vad_cache / "models" / VAD_MODEL_FILENAME,
                Path(binary).parent / VAD_MODEL_FILENAME,
                vad_cache / "silero_vad.onnx",  # legacy
            ):
                if candidate.exists():
                    vad_model_path = str(candidate)
                    break
            else:
                # Auto-download VAD model from ggml-org/whisper-vad
                vad_model_path = vad_cache / VAD_MODEL_FILENAME
                vad_model_path.parent.mkdir(parents=True, exist_ok=True)
                if not vad_model_path.exists():
                    if log_callback:
                        log_callback(f"Downloading VAD model {VAD_MODEL_FILENAME} (~1 MB)...")
                    try:
                        urlretrieve(
                            "https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v6.2.0.bin",
                            vad_model_path,
                        )
                        vad_model_path = str(vad_model_path)
                        if log_callback:
                            log_callback("VAD model downloaded.")
                    except Exception as e:
                        if log_callback:
                            log_callback(f"VAD model download failed: {e}. Running without VAD.")
                        vad_model_path = None
                else:
                    vad_model_path = str(vad_model_path)
        else:
            vad_model_path = str(vad_model_path) if Path(vad_model_path).exists() else None
        try:
            r = subprocess.run([str(binary), "-h"], capture_output=True, text=True, timeout=5)
            help_out = (r.stdout or "") + (r.stderr or "")
            if vad_model_path and "--vad" in help_out and "--vad-model" in help_out:
                vad_args = ["--vad", "-vm", vad_model_path]
        except Exception:
            pass
        # Default stack tuned for more stable punctuation/sentence boundaries.
        subtitle_edit_args = ["-sow", "-bs", "5", "-bo", "5"]
        cmd = [
            str(binary), "-m", str(model_path), "-f", str(audio_path),
            "-l", language_code if language_code != "auto" else "auto",
        ] + vad_args + no_gpu_args + subtitle_edit_args + ["--print-progress", "-osrt", "-of", output_stem]
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

        tmp_srt   = Path(output_stem + ".srt")
        final_srt = srt_out_dir / f"{base_name}.srt"

        if tmp_srt.exists():
            shutil.move(str(tmp_srt), str(final_srt))

        # Post-processing uses the audio WAV for timing adjustment — delete it only after.
        if final_srt.exists():
            _whisper_cpp_post_process(final_srt, audio_path, config, log_callback)

        if audio_path.exists():
            try:
                audio_path.unlink()
            except OSError:
                pass

        if returncode == 0 and final_srt.exists():
            if log_callback:
                log_callback(f"✓ Transcription complete: {final_srt}")
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

        video_dir   = video_path.parent
        base_name   = video_path.stem
        srt_out_dir = get_subtitles_dir()
        audio_stem  = f"{base_name}_converted"
        audio_path  = video_dir / f"{audio_stem}.wav"

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

        _cfg = load_config()
        if not _extract_audio_for_transcription(video_path, audio_path, _cfg, log_callback):
            return False

        if log_callback:
            log_callback("Transcribing with Whisper...")
        # whisper writes <audio_stem>.<format> into --output_dir; we use video_dir
        # for the temp output then move the SRT to the subtitles folder.
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
        final_srt   = srt_out_dir / f"{base_name}.srt"

        if whisper_srt.exists():
            shutil.move(str(whisper_srt), str(final_srt))
        if audio_path.exists():
            try:
                audio_path.unlink()
            except OSError:
                pass

        if result.returncode == 0 and final_srt.exists():
            if log_callback:
                log_callback(f"✓ Transcription complete: {final_srt}")
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
        _cfg = load_config()
        ffmpeg_exe = get_ffmpeg_command(_cfg)
        if not _extract_audio_for_transcription(video_path, audio_path, _cfg, log_callback):
            return False

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
        output_srt = get_subtitles_dir() / f"{video_path.stem}.srt"
        all_subs.save(output_srt, encoding="utf-8")

        if log_callback:
            log_callback(f"Done → {output_srt}")
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
# Worker threads
# ============================================================================

def run_batch_transcribe(transcribe_func, video_paths, *args, **kwargs) -> bool:
    """Run transcribe_func on each path. Logs [i/N] filename, respects check_stop. Returns True only if all succeed."""
    paths = [Path(p) for p in video_paths]
    total = len(paths)
    # Filter kwargs to only what transcribe_func accepts (avoids leaking ScriptWorker-injected
    # extras like check_stop, stream_progress_callback, etc. into funcs that don't declare them)
    sig = inspect.signature(transcribe_func)
    params = sig.parameters
    accepts_var_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
    if accepts_var_kwargs:
        call_kwargs = {k: v for k, v in kwargs.items() if k != "check_stop"}
    else:
        allowed = set(params.keys())
        call_kwargs = {k: v for k, v in kwargs.items() if k in allowed}
    for i, path in enumerate(paths):
        check_stop = kwargs.get("check_stop")
        if check_stop and check_stop():
            return False
        log_cb = kwargs.get("log_callback")
        if log_cb:
            log_cb(f"[{i + 1}/{total}] {path.name}")
        prog_cb = kwargs.get("progress_callback")
        if prog_cb:
            prog_cb(i + 1, total, path.name)
        ok = transcribe_func(path, *args, **call_kwargs)
        if not ok:
            return False
    return True


# ============================================================================
# Transcription backend protocol + registry
# ============================================================================

@runtime_checkable
class TranscribeBackend(Protocol):
    """Common interface for every transcription engine.

    Each backend exposes a human-readable *name* (shown in the UI combo) and a
    stable *backend_id* key used for dispatch.  ``is_available`` is called at
    startup so the combo can grey out unavailable engines.
    """

    name:       str   # display label, e.g. "Whisper CPP (recommended)"
    backend_id: str   # machine key, e.g. "cpp"

    def is_available(self, config: Dict) -> bool: ...

    def transcribe(
        self,
        video_path: Path,
        language_code: str,
        model: str,
        config: Dict,
        progress_callback=None,
        log_callback=None,
    ) -> bool: ...


class WhisperCppBackend:
    name       = "Whisper CPP (recommended)"
    backend_id = "cpp"

    def is_available(self, config: Dict) -> bool:
        binary = _get_whisper_cpp_binary(config)
        return binary is not None and Path(binary).exists()

    def transcribe(self, video_path: Path, language_code: str, model: str,
                   config: Dict, progress_callback=None, log_callback=None) -> bool:
        return transcribe_video_whisper_cpp(
            video_path, language_code, model,
            progress_callback=progress_callback, log_callback=log_callback,
        )


class OpenAIWhisperBackend:
    name       = "OpenAI Whisper (short clip, legacy)"
    backend_id = "standard"

    def is_available(self, config: Dict) -> bool:  # noqa: ARG002
        return _get_whisper_python(None) is not None

    def transcribe(self, video_path: Path, language_code: str, model: str,
                   config: Dict, progress_callback=None, log_callback=None) -> bool:
        output_format   = config.get("whisper_output_format", "srt")
        whisper_options = config.get("whisper_options", {})
        return transcribe_video(
            video_path, language_code, model, whisper_options,
            output_format=output_format,
            progress_callback=progress_callback, log_callback=log_callback,
        )


class VadWhisperBackend:
    name       = "OpenAI Whisper (>5 min. clip, legacy)"
    backend_id = "long"

    def is_available(self, config: Dict) -> bool:  # noqa: ARG002
        try:
            import torch   # noqa: F401
            import pysrt   # noqa: F401
            return True
        except ImportError:
            return False

    def transcribe(self, video_path: Path, language_code: str, model: str,
                   config: Dict, progress_callback=None, log_callback=None) -> bool:
        return transcribe_video_vad(
            video_path, language_code, model,
            progress_callback=progress_callback, log_callback=log_callback,
        )


# Ordered list of all available backends
TRANSCRIBE_BACKENDS: List[TranscribeBackend] = [
    WhisperCppBackend(),
    OpenAIWhisperBackend(),
    VadWhisperBackend(),
]


class ScriptWorker(QThread):
    """Worker thread for running scripts without blocking UI."""
    finished = pyqtSignal(bool)
    log_message = pyqtSignal(str)
    progress_update = pyqtSignal(int, int, str)  # current, total, filename
    stream_progress = pyqtSignal(str)  # live per-stream download progress
    
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

        def stream_progress_callback(msg):
            if not self._stop_requested:
                self.stream_progress.emit(msg)

        self.kwargs["log_callback"] = log_callback
        self.kwargs["progress_callback"] = progress_callback
        self.kwargs["stream_progress_callback"] = stream_progress_callback
        self.kwargs["check_stop"] = lambda: self._stop_requested
        # Filter kwargs to only what script_func accepts (avoids passing check_stop to functions that don't support it)
        sig = inspect.signature(self.script_func)
        params = sig.parameters
        accepts_var_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
        if accepts_var_kwargs:
            call_kwargs = dict(self.kwargs)
        else:
            param_names = set(params.keys())
            call_kwargs = {k: v for k, v in self.kwargs.items() if k in param_names}
        try:
            result = self.script_func(*self.args, **call_kwargs)
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
            py = _host_python_for_module_cli()
            if not py:
                self.log_message.emit(
                    "Cannot run pip from this bundled app. Use a system Python in Terminal: "
                    "python3 -m pip install " + " ".join(self.packages)
                )
                self.finished.emit(False)
                return
            result = subprocess.run(
                [py, "-m", "pip", "install"] + self.packages,
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


class WhisperCppInstallWorker(QThread):  # pyright: ignore [reportUnreachable]
    """Worker thread for installing Whisper CPP. On macOS with Homebrew, installs Metal-enabled build; otherwise pip."""
    finished = pyqtSignal(bool)
    log_message = pyqtSignal(str)

    def run(self):
        try:
            if sys.platform == "darwin" and shutil.which("brew"):
                ok = self._install_whisper_cpp_macos_metal()
                if not ok:
                    self.log_message.emit("Metal install failed. Falling back to pip (CPU-only)...")
                    ok = self._install_whisper_cpp_pip()
            elif sys.platform == "darwin":
                self.log_message.emit("Homebrew not found. Installing CPU-only version. For Metal, install from brew.sh and retry.")
                ok = self._install_whisper_cpp_pip()
            else:
                ok = self._install_whisper_cpp_pip()
            self.finished.emit(ok)
        except Exception as e:
            self.log_message.emit(f"Error: {e}")
            self.log_message.emit(traceback.format_exc())
            self.finished.emit(False)

    def _install_whisper_cpp_macos_metal(self) -> bool:
        brew = shutil.which("brew")
        if not brew:
            return False
        self.log_message.emit("Running: brew install whisper-cpp")
        result = subprocess.run(
            [brew, "install", "whisper-cpp"],
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            err = (result.stderr or result.stdout or "").strip()
            self.log_message.emit(f"brew install failed: {err}")
            return False
        prefix_result = subprocess.run(
            [brew, "--prefix", "whisper-cpp"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if prefix_result.returncode != 0 or not prefix_result.stdout:
            self.log_message.emit("Could not get whisper-cpp install path")
            return False
        prefix = prefix_result.stdout.strip()
        bin_dir = Path(prefix) / "bin"
        # Homebrew installs whisper-cli (not whisper-cpp); build-from-source may use main
        exe = None
        for name in ("whisper-cli", "whisper-cpp", "main"):
            candidate = bin_dir / name
            if candidate.exists():
                exe = candidate
                break
        if not exe:
            self.log_message.emit(f"whisper binary not found in {bin_dir} (expected whisper-cli, whisper-cpp, or main)")
            return False
        # Homebrew builds with GGML_METAL_EMBED_LIBRARY=ON: Metal is embedded, no ggml-metal.metal file needed.
        # Do NOT download ggml-metal.metal: version mismatch with binary can cause ggml-common.h errors.
        config = load_config()
        config["whisper_cpp_path"] = str(bin_dir.resolve())
        save_config(config)
        self.log_message.emit("✓ Whisper CPP (Metal) installed")
        return True

    def _install_whisper_cpp_pip(self) -> bool:
        self.log_message.emit("Installing: whisper.cpp-cli")
        try:
            py = _host_python_for_module_cli()
            if not py:
                self.log_message.emit(
                    "Cannot run pip from this bundled app. In Terminal: python3 -m pip install whisper.cpp-cli"
                )
                return False
            result = subprocess.run(
                [py, "-m", "pip", "install", "whisper.cpp-cli"],
                capture_output=True,
                text=True,
                timeout=600,
            )
            if result.returncode != 0:
                err = (result.stderr or result.stdout or "").strip()
                self.log_message.emit(f"pip install failed: {err}")
                self.log_message.emit("Try manually: python -m pip install whisper.cpp-cli")
                return False
            self.log_message.emit("✓ Whisper CPP (CPU) installed")
            return True
        except subprocess.TimeoutExpired:
            self.log_message.emit("Installation timed out")
            return False
        except Exception as e:
            self.log_message.emit(f"Error: {e}")
            return False


# ============================================================================
# Tool detection and installation
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


def get_ffmpeg_command(config: Optional[Dict] = None, require_libass: bool = False) -> str:
    """Return the ffmpeg executable path. When require_libass=True (subtitle burning), forces ffmpeg-full on macOS."""
    if config is None:
        config = load_config()
    # For subtitle burning, always prefer ffmpeg-full on macOS (overrides user config)
    if require_libass and sys.platform == "darwin":
        for prefix in (Path("/opt/homebrew/opt/ffmpeg-full"), Path("/usr/local/opt/ffmpeg-full")):
            exe = prefix / "bin" / "ffmpeg"
            if exe.exists():
                return str(exe.resolve())
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
    # Prefer ffmpeg-full on macOS when not require_libass (has libass for subtitles filter)
    if sys.platform == "darwin":
        for prefix in (Path("/opt/homebrew/opt/ffmpeg-full"), Path("/usr/local/opt/ffmpeg-full")):
            exe = prefix / "bin" / "ffmpeg"
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


def _is_frozen_pyinstaller() -> bool:
    """True inside a PyInstaller bundle: sys.executable is the app binary, not CPython."""
    return bool(getattr(sys, "frozen", False)) or hasattr(sys, "_MEIPASS")


def _host_python_for_module_cli() -> Optional[str]:
    """Interpreter for `python -m ...` subprocesses. Never the frozen GUI executable."""
    if not _is_frozen_pyinstaller():
        return sys.executable
    frozen_exe = Path(sys.executable).resolve()
    for name in ("python3.12", "python3", "python"):
        candidate = shutil.which(name)
        if not candidate:
            continue
        try:
            if Path(candidate).resolve() == frozen_exe:
                continue
        except OSError:
            continue
        return candidate
    return None


def _gst_command_via_python_module() -> Optional[str]:
    """Detect gemini-srt-translator via `python -m ... --help`; kills child on timeout."""
    py = _host_python_for_module_cli()
    if not py:
        return None
    proc = subprocess.Popen(
        [py, "-m", "gemini_srt_translator", "--help"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        proc.communicate(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        return None
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
        return None
    if proc.returncode == 0:
        return f"{py} -m gemini_srt_translator"
    return None


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
    
    return _gst_command_via_python_module()


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
# Setup wizard & dialogs
# ============================================================================

class CleanSubtitlesDialog(QDialog):
    """Dialog to select which fixes to apply when cleaning subtitles."""
    
    def __init__(self, parent=None, config: Optional[Dict] = None):
        super().__init__(parent)
        self.setWindowTitle("Clean subtitles – select fixes")
        self.setMinimumWidth(420)
        self.config = config or load_config()
        self.fix_checkboxes = {}
        
        layout = QVBoxLayout()
        
        # Always-on: Remove color tags (greyed out)
        color_cb = QCheckBox("Remove color tags")
        color_cb.setChecked(True)
        color_cb.setEnabled(False)
        color_cb.setStyleSheet("color: #888;")
        layout.addWidget(color_cb)
        
        always_label = QLabel("(always on)")
        always_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(always_label)
        
        sep = QLabel("────────────────────────────────────")
        sep.setStyleSheet("color: #ccc;")
        layout.addWidget(sep)
        
        # Optional fixes (CLEAN_SUBTITLES_FIX_ITEMS may be 2- or 3-tuples)
        saved = self.config.get("clean_subtitles_fixes", {})
        for item in CLEAN_SUBTITLES_FIX_ITEMS:
            key, label = item[0], item[1]
            cb = QCheckBox(label)
            cb.setChecked(saved.get(key, True))
            self.fix_checkboxes[key] = cb
            layout.addWidget(cb)
        
        layout.addWidget(QLabel("────────────────────────────────────"))
        
        # Buttons
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select all")
        select_all_btn.clicked.connect(self._select_all)
        select_none_btn = QPushButton("Select none")
        select_none_btn.clicked.connect(self._select_none)
        apply_btn = QPushButton("Apply selected")
        apply_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(select_none_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
    
    def _select_all(self):
        for cb in self.fix_checkboxes.values():
            cb.setChecked(True)
    
    def _select_none(self):
        for cb in self.fix_checkboxes.values():
            cb.setChecked(False)
    
    def get_enabled_fixes(self) -> List[str]:
        """Return list of fix keys that are checked."""
        return [k for k, cb in self.fix_checkboxes.items() if cb.isChecked()]
    
    def save_selection_to_config(self):
        """Persist current selection to config."""
        fixes = {k: cb.isChecked() for k, cb in self.fix_checkboxes.items()}
        self.config["clean_subtitles_fixes"] = fixes
        save_config(self.config)


class WhisperPostProcessingDialog(QDialog):
    """Dialog to configure per-step Whisper post-processing options."""

    _OPTIONS = [
        ("whisper_post_proc_adjust_timings",     "Adjust timings",      "Snap subtitle boundaries to speech/silence using the audio waveform"),
        ("whisper_post_proc_merge_lines",         "Merge short lines",   "Merge adjacent short subtitles when the gap is ≤ 100 ms"),
        ("whisper_post_proc_split_lines",         "Break long lines",   "Insert a line break in long subtitles (keeps one subtitle cue)"),
        ("whisper_post_proc_fix_short_duration",  "Fix short duration",  "Extend subtitles displayed for less than 1 second"),
        ("whisper_post_proc_add_periods",         "Add periods",         "Add a period when the gap to the next subtitle is > 600 ms"),
        ("whisper_post_proc_fix_casing",          "Fix casing",          "Capitalise the first letter of each subtitle"),
    ]

    def __init__(self, parent=None, config: Optional[Dict] = None):
        super().__init__(parent)
        self.setWindowTitle("Whisper post-processing options")
        self.setMinimumWidth(380)
        self.config = config or load_config()
        self._checkboxes: Dict[str, QCheckBox] = {}

        layout = QVBoxLayout()
        layout.setSpacing(6)

        for key, label, tooltip in self._OPTIONS:
            cb = QCheckBox(label)
            cb.setChecked(self.config.get(key, True))
            cb.setToolTip(tooltip)
            self._checkboxes[key] = cb
            layout.addWidget(cb)

        layout.addWidget(QLabel("────────────────────────────────────"))

        btn_layout = QHBoxLayout()
        select_all = QPushButton("Select all")
        select_all.clicked.connect(lambda: [cb.setChecked(True) for cb in self._checkboxes.values()])
        select_none = QPushButton("Select none")
        select_none.clicked.connect(lambda: [cb.setChecked(False) for cb in self._checkboxes.values()])
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(select_all)
        btn_layout.addWidget(select_none)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def save_to_config(self):
        for key, cb in self._checkboxes.items():
            self.config[key] = cb.isChecked()
        save_config(self.config)


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
        
        self.batch_cb = QCheckBox("Batch download episodes")
        self.batch_cb.setChecked(self.want_batch_download)
        self.batch_cb.stateChanged.connect(lambda: on_feature_changed())
        layout.addWidget(self.batch_cb)
        
        translator_row = QWidget()
        translator_layout = QVBoxLayout(translator_row)
        translator_layout.setContentsMargins(0, 0, 0, 0)
        translator_layout.setSpacing(2)
        self.translator_cb = QCheckBox("Translate subtitles")
        self.translator_cb.setChecked(self.want_translator)
        self.translator_cb.stateChanged.connect(lambda: on_feature_changed())
        translator_layout.addWidget(self.translator_cb)
        trans_helper = QLabel("Uses Google Gemini API")
        trans_helper.setStyleSheet("color: #666; font-size: 10px;")
        trans_helper.setWordWrap(True)
        translator_layout.addWidget(trans_helper)
        layout.addWidget(translator_row)
        
        # QCheckBox doesn't support setWordWrap (Qt bug QTBUG-5370). Use checkbox + label combo.
        transcribe_row = QWidget()
        transcribe_row_layout = QVBoxLayout(transcribe_row)
        transcribe_row_layout.setContentsMargins(0, 0, 0, 0)
        transcribe_row_layout.setSpacing(2)
        transcribe_inner = QHBoxLayout()
        transcribe_inner.setSpacing(8)

        self.transcribe_long_cb = QCheckBox("Transcribe audio/video")
        self.transcribe_long_cb.setChecked(self.want_transcribe_long)
        self.transcribe_long_cb.stateChanged.connect(lambda: on_feature_changed())

        transcribe_inner.addWidget(self.transcribe_long_cb)
        transcribe_inner.addStretch()
        transcribe_row_layout.addLayout(transcribe_inner)
        transcribe_helper = QLabel("Requires additional download (~2–3 GB). Uses local AI model.")
        transcribe_helper.setStyleSheet("color: #666; font-size: 10px;")
        transcribe_helper.setWordWrap(True)
        transcribe_row_layout.addWidget(transcribe_helper)
        layout.addWidget(transcribe_row)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def create_welcome_step(self) -> QWidget:
        """Create welcome/intro step."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        summary = QLabel("We'll check your system and install what's missing.")
        summary.setWordWrap(True)
        layout.addWidget(summary)
        
        info = QLabel("This wizard will help you check if everything is set up correctly.")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        if self.all_required_installed:
            status = QLabel("✓ All required components are already installed!")
            status.setStyleSheet("color: #00aa00; font-weight: bold; font-size: 12pt; padding: 10px;")
            layout.addWidget(status)
        else:
            status = QLabel("Some features need additional components. You can install them now or skip.")
            status.setStyleSheet("color: #666; font-size: 11pt; padding: 10px;")
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
        
        # Expandable technical details
        self.technical_details_visible = False
        self.technical_details_btn = QPushButton("Show technical details")
        self.technical_details_btn.setStyleSheet("color: #666; text-decoration: underline;")
        self.technical_details_btn.setFlat(True)
        self.technical_details_btn.setCursor(Qt.PointingHandCursor)
        self.technical_details_widget = QTextBrowser()
        self.technical_details_widget.setOpenExternalLinks(True)
        self.technical_details_widget.setHtml(self.get_technical_details_html())
        self.technical_details_widget.setMaximumHeight(0)
        self.technical_details_widget.setVisible(False)

        def toggle_technical():
            self.technical_details_visible = not self.technical_details_visible
            if self.technical_details_visible:
                self.technical_details_btn.setText("Hide technical details")
                self.technical_details_widget.setMaximumHeight(400)
                self.technical_details_widget.setVisible(True)
            else:
                self.technical_details_btn.setText("Show technical details")
                self.technical_details_widget.setMaximumHeight(0)
                self.technical_details_widget.setVisible(False)

        self.technical_details_btn.clicked.connect(toggle_technical)
        layout.addWidget(self.technical_details_btn)
        layout.addWidget(self.technical_details_widget)
        
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
        if hasattr(self, "technical_details_widget") and self.technical_details_widget:
            self.technical_details_widget.setHtml(self.get_technical_details_html())
        if hasattr(self, "summary_text") and self.summary_text:
            self.summary_text.setHtml(self.get_summary_html())
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
            btn.clicked.connect(self._do_whisper_cpp_install)
            self.install_buttons_layout.addWidget(btn)
    
    def _do_whisper_cpp_install(self, on_success_after_install=None):
        """Install Whisper CPP. On macOS with Homebrew: Metal-enabled; otherwise pip (CPU)."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Installing Whisper CPP...")
        dlg.setMinimumWidth(400)
        dlg.setWindowModality(Qt.ApplicationModal)
        layout = QVBoxLayout()
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 0)
        layout.addWidget(progress_bar)
        log = QTextEdit()
        log.setReadOnly(True)
        layout.addWidget(log)
        close_btn = QPushButton("Close")
        close_btn.setEnabled(False)
        layout.addWidget(close_btn)
        dlg.setLayout(layout)
        worker = WhisperCppInstallWorker(parent=dlg)
        worker.log_message.connect(lambda m: log.append(m))
        def on_finished(ok):
            worker.wait()
            if ok:
                log.append("\nInstalled successfully")
                progress_bar.setVisible(False)
                close_btn.setEnabled(True)
                close_btn.setText("Installed successfully")
                def auto_close():
                    self._refresh_status_after_install()
                    if on_success_after_install:
                        on_success_after_install()
                    dlg.accept()
                QTimer.singleShot(1500, auto_close)
            else:
                log.append("\nInstallation failed. Click Close, then run: python -m pip install whisper.cpp-cli")
                close_btn.setEnabled(True)
        close_btn.clicked.connect(dlg.accept)
        worker.finished.connect(on_finished)
        worker.start()
        dlg.exec_()

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
        dlg.setWindowModality(Qt.ApplicationModal)
        layout = QVBoxLayout()
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 0)
        layout.addWidget(progress_bar)
        log = QTextEdit()
        log.setReadOnly(True)
        layout.addWidget(log)
        close_btn = QPushButton("Close")
        close_btn.setEnabled(False)
        layout.addWidget(close_btn)
        dlg.setLayout(layout)
        worker = PipInstallWorker(packages, parent=dlg)
        worker.log_message.connect(lambda m: log.append(m))
        def on_finished(ok):
            worker.wait()
            if ok:
                log.append("\nInstalled successfully")
                progress_bar.setVisible(False)
                close_btn.setEnabled(True)
                close_btn.setText("Installed successfully")

                def auto_close():
                    self._refresh_status_after_install()
                    dlg.accept()
                QTimer.singleShot(1500, auto_close)
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
        dlg.setWindowModality(Qt.ApplicationModal)
        layout = QVBoxLayout()
        add_to_path_cb = QCheckBox("Add to PATH so you can use from terminal")
        add_to_path_cb.setChecked(False)
        layout.addWidget(add_to_path_cb)
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 0)
        progress_bar.setVisible(False)
        layout.addWidget(progress_bar)
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
            progress_bar.setVisible(True)
            worker = BinaryInstallWorker(tool, add_to_path=add_to_path_cb.isChecked(), parent=dlg)
            worker.log_message.connect(lambda m: log.append(m))
            def on_finished(ok):
                worker.wait()  # Ensure thread has fully exited before any cleanup (prevents QThread crash)
                if ok:
                    log.append("\nInstalled successfully")
                    progress_bar.setVisible(False)
                    close_btn.setEnabled(True)
                    close_btn.setText("Installed successfully")

                    def auto_close():
                        self._refresh_status_after_install()
                        dlg.accept()
                    QTimer.singleShot(1500, auto_close)
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
        
        # API key configured: checked = configured, unchecked = configure later
        has_env_key = bool(os.getenv("GEMINI_API_KEY") or os.getenv("GST_API_KEY"))
        has_config_key = bool(self.config.get("api_key", "")) or bool(self.config.get("api_keys"))
        api_configured = has_env_key or has_config_key
        
        api_row = QWidget()
        api_row_layout = QHBoxLayout(api_row)
        api_row_layout.setContentsMargins(0, 0, 0, 0)
        api_row_layout.setSpacing(8)
        self.api_key_checkbox = QCheckBox("API key configured")
        self.api_key_checkbox.setChecked(api_configured)
        api_row_layout.addWidget(self.api_key_checkbox)
        if has_env_key:
            env_label = QLabel("✓ Environment variable detected")
            env_label.setStyleSheet("color: #666; font-size: 10px;")
            api_row_layout.addWidget(env_label)
        api_row_layout.addStretch()
        layout.addWidget(api_row)
        
        configure_help = QLabel("Uncheck to configure later in Settings")
        configure_help.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(configure_help)
        
        layout.addSpacing(10)
        
        # Summary
        summary_label = QLabel("Summary:")
        summary_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(summary_label)
        
        self.summary_text = QTextBrowser()
        self.summary_text.setOpenExternalLinks(True)
        self.summary_text.setHtml(self.get_summary_html())
        self.summary_text.setMaximumHeight(150)
        layout.addWidget(self.summary_text)
        
        layout.addStretch()
        widget.setLayout(layout)
        return widget
    
    def get_required_html(self) -> str:
        """Generate HTML for required components (feature-aware). No pip commands here — those go in technical details."""
        html = "<div style='line-height: 1.6;'>"
        
        html += "<h4 style='margin-top: 10px; color: #333;'>Core</h4>"
        html += f"<p><b>{'✓ Installed' if self.pyqt5_installed else '✗ Not installed'}</b> — PyQt5</p>"
        html += f"<p><b>{'✓ Installed' if self.ffmpeg_installed else '✗ Not installed'}</b> — FFmpeg</p>"
        
        if self.want_batch_download:
            html += "<h4 style='margin-top: 15px; color: #333;'>Batch Download</h4>"
            html += f"<p><b>{'✓ Installed' if self.n_m3u8_installed else '✗ Not installed'}</b> — N_m3u8DL-RE</p>"
        
        if self.want_translator:
            html += "<h4 style='margin-top: 15px; color: #333;'>Translator</h4>"
            html += f"<p><b>{'✓ Installed' if self.gst_installed else '✗ Not installed'}</b> — gemini-srt-translator</p>"
        
        if self.want_transcribe_long:
            html += "<h4 style='margin-top: 15px; color: #333;'>Transcription (Local AI)</h4>"
            status = "✓ Installed" if self.transcribe_long_installed else "✗ Not installed — Requires ~2–3 GB download"
            html += f"<p><b>{status}</b></p>"
        
        html += "<h4 style='margin-top: 15px; color: #333;'>Whisper CPP (Faster alternative)</h4>"
        html += f"<p><b>{'✓ Installed' if self.whisper_cpp_installed else '✗ Not installed'}</b> — whisper.cpp-cli</p>"
        
        html += "</div>"
        return html

    def get_technical_details_html(self) -> str:
        """Generate HTML for expandable technical details (pip commands, etc.)."""
        html = "<div style='line-height: 1.6; font-size: 11px; color: #555;'>"
        parts = []
        if not self.pyqt5_installed:
            parts.append(("<b>PyQt5</b>", "<code>python -m pip install PyQt5</code>"))
        if not self.ffmpeg_installed:
            system = platform.system()
            if system == "Darwin":
                parts.append(("<b>FFmpeg</b>", "<code>brew install ffmpeg</code> — <a href='https://brew.sh'>Install Homebrew</a> if needed"))
            elif system == "Windows":
                parts.append(("<b>FFmpeg</b>", "<a href='https://www.gyan.dev/ffmpeg/builds/'>Download from gyan.dev</a>, extract and add bin to PATH"))
            else:
                parts.append(("<b>FFmpeg</b>", "<code>sudo apt install ffmpeg</code> (Debian/Ubuntu) or <code>sudo dnf install ffmpeg</code> (Fedora)"))
        if self.want_batch_download and not self.n_m3u8_installed:
            parts.append(("<b>N_m3u8DL-RE</b>", "<a href='https://github.com/nilaoda/N_m3u8DL-RE/releases'>GitHub Releases</a>, extract and add to PATH"))
        if self.want_translator and not self.gst_installed:
            parts.append(("<b>gemini-srt-translator</b>", "<code>python -m pip install gemini-srt-translator</code>"))
        if self.want_transcribe_long and not self.transcribe_long_installed:
            parts.append(("<b>Transcription (Local AI)</b>", "<code>python -m pip install torch torchaudio torchcodec pysrt openai-whisper</code>"))
        if not self.whisper_cpp_installed:
            parts.append(("<b>Whisper CPP</b>", "<code>python -m pip install whisper.cpp-cli</code>"))
        if not parts:
            html += "<p>All components installed.</p>"
        else:
            for name, detail in parts:
                html += f"<p>{name}: {detail}</p>"
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


# FAQ dialog
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


# About dialog
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


# Language selection dialog
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


# Settings dialog
class SettingsDialog(QDialog):
    """Settings configuration dialog."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(700)
        
        self.config = load_config()
        
        main_layout = QVBoxLayout()
        tabs = QTabWidget()
        
        # --- API tab ---
        api_tab = QWidget()
        api_layout = QVBoxLayout(api_tab)
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
        api_layout.addWidget(api_group)
        tabs.addTab(api_tab, "API")
        
        # --- Tools tab ---
        tools_tab = QWidget()
        tools_layout = QVBoxLayout(tools_tab)
        ffmpeg_group = QGroupBox("FFmpeg")
        ffmpeg_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        ffmpeg_form = QFormLayout()
        ffmpeg_help = QLabel(
            "Leave empty to auto-detect (on macOS, prefers ffmpeg-full for libass/subtitles). "
            "For burn-in subtitles, FFmpeg must include libass (brew install ffmpeg-full)."
        )
        ffmpeg_help.setWordWrap(True)
        ffmpeg_help.setStyleSheet("color: #666; font-size: 10px;")
        ffmpeg_form.addRow("", ffmpeg_help)
        self.ffmpeg_path_input = QLineEdit()
        self.ffmpeg_path_input.setText(self.config.get("ffmpeg_path", ""))
        self.ffmpeg_path_input.setPlaceholderText("Leave empty to auto-detect ffmpeg-full on macOS")
        ffmpeg_form.addRow("FFmpeg path (optional):", self.ffmpeg_path_input)
        ffmpeg_group.setLayout(ffmpeg_form)
        tools_layout.addWidget(ffmpeg_group)

        nm3u8_group = QGroupBox("N_m3u8DL-RE")
        nm3u8_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        nm3u8_form = QFormLayout()
        nm3u8_help = QLabel(
            "Leave empty to use system default. Set path if installed in a custom location."
        )
        nm3u8_help.setWordWrap(True)
        nm3u8_help.setStyleSheet("color: #666; font-size: 10px;")
        nm3u8_form.addRow("", nm3u8_help)
        self.n_m3u8dl_path_input = QLineEdit()
        self.n_m3u8dl_path_input.setText(self.config.get("n_m3u8dl_path", ""))
        self.n_m3u8dl_path_input.setPlaceholderText("e.g. /usr/local/bin/N_m3u8DL-RE")
        nm3u8_form.addRow("N_m3u8DL-RE path (optional):", self.n_m3u8dl_path_input)
        nm3u8_group.setLayout(nm3u8_form)
        tools_layout.addWidget(nm3u8_group)

        whisper_cpp_group = QGroupBox("Whisper CPP")
        whisper_cpp_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        whisper_cpp_form = QFormLayout()
        whisper_cpp_help = QLabel(
            "For Metal GPU on macOS: use Homebrew (brew install whisper-cpp) – Metal is embedded. "
            "Or set path to a build from source with Metal. Leave empty to use pip whisper.cpp-cli (CPU)."
        )
        whisper_cpp_help.setWordWrap(True)
        whisper_cpp_help.setStyleSheet("color: #666; font-size: 10px;")
        whisper_cpp_form.addRow("", whisper_cpp_help)
        self.whisper_cpp_path_input = QLineEdit()
        self.whisper_cpp_path_input.setText(self.config.get("whisper_cpp_path", ""))
        self.whisper_cpp_path_input.setPlaceholderText("e.g. /opt/homebrew/opt/whisper-cpp/bin")
        whisper_cpp_form.addRow("Whisper CPP path (optional):", self.whisper_cpp_path_input)
        whisper_cpp_group.setLayout(whisper_cpp_form)
        tools_layout.addWidget(whisper_cpp_group)
        tabs.addTab(tools_tab, "Tools")
        
        # --- Processing tab ---
        processing_tab = QWidget()
        processing_layout = QVBoxLayout(processing_tab)
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
        processing_layout.addWidget(watermark_group)

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
        translation_helper = QLabel("Used when clicking \"Translate subtitles\".")
        translation_helper.setStyleSheet("color: #666; font-size: 10px;")
        trans_form.addRow("", translation_helper)
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
        processing_layout.addWidget(translation_group)
        tabs.addTab(processing_tab, "Processing")
        
        # --- Appearance tab ---
        appearance_tab = QWidget()
        appearance_layout = QVBoxLayout(appearance_tab)
        appearance_group = QGroupBox("Appearance")
        appearance_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        app_form = QFormLayout()
        self.lesbian_flag_checkbox = QCheckBox("Lesbian flag theme")
        self.lesbian_flag_checkbox.setChecked(True)
        self.lesbian_flag_checkbox.stateChanged.connect(self.toggle_lesbian_flag_theme)
        app_form.addRow("", self.lesbian_flag_checkbox)
        appearance_group.setLayout(app_form)
        appearance_layout.addWidget(appearance_group)
        tabs.addTab(appearance_tab, "Appearance")
        
        main_layout.addWidget(tabs)
        
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
        """Joke feature - shows a message when user tries to turn theme OFF; keeps theme ON."""
        if state == Qt.Unchecked:  # User tried to uncheck it (turn theme off)
            QMessageBox.warning(
                self,
                "Wait a minute...",
                "That kinda homophobic, isn't it?"
            )
            self.lesbian_flag_checkbox.blockSignals(True)
            self.lesbian_flag_checkbox.setChecked(True)
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
        self.config["whisper_cpp_path"] = self.whisper_cpp_path_input.text().strip()
        self.config["watermark_720p"] = self.watermark_720p_input.text()
        self.config["watermark_1080p"] = self.watermark_1080p_input.text()
        self.config["use_watermarks"] = self.use_watermarks_checkbox.isChecked()
        self.config["translation_target_language"] = self.translation_target_combo.currentText()
        self.config["use_iso639_suffixes"] = self.iso639_checkbox.isChecked()
        save_config(self.config)
        self.accept()


# Whisper options dialog
class WhisperOptionsDialog(QDialog):
    """Advanced options dialog for Whisper — shows per-engine parameter reference and extra args."""

    _BTN_ACTIVE = (
        "QPushButton { background: #e8e8e8; border: 2px solid #aaa; border-radius: 4px;"
        " font-weight: bold; padding: 4px 10px; }"
    )
    _BTN_INACTIVE = (
        "QPushButton { background: none; border: 1px solid #ccc; border-radius: 4px;"
        " font-weight: normal; padding: 4px 10px; }"
        "QPushButton:hover { background: #f0f0f0; }"
    )

    def __init__(self, parent=None, initial_method="cpp"):
        super().__init__(parent)
        self.setWindowTitle("Whisper Advanced Options")
        self.setMinimumWidth(1000)
        self.setMinimumHeight(700)

        self.config = load_config()
        self._current_method = None  # set by _switch_method

        # Load both extra_args up front
        self._extra_args = {
            "cpp":    (self.config.get("whisper_cpp_extra_args") or ""),
            "openai": (self.config.get("whisper_options", {}).get("extra_args") or ""),
        }

        main_layout = QVBoxLayout()

        info_label = QLabel("Type additional parameters below. These will be appended to the default command for the selected engine.")
        info_label.setStyleSheet("color: #666; margin-bottom: 6px;")
        info_label.setWordWrap(True)
        main_layout.addWidget(info_label)

        split_layout = QHBoxLayout()

        # ── Left panel: engine selector + reference ──────────────────────────
        left_panel = QGroupBox("Available Parameters (Reference)")
        left_layout = QVBoxLayout()
        left_layout.setSpacing(6)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.btn_cpp = QPushButton("Whisper CPP")
        self.btn_openai = QPushButton("OpenAI Whisper")
        self.btn_cpp.clicked.connect(lambda: self._switch_method("cpp"))
        self.btn_openai.clicked.connect(lambda: self._switch_method("openai"))
        btn_row.addWidget(self.btn_cpp)
        btn_row.addWidget(self.btn_openai)
        btn_row.addStretch()
        left_layout.addLayout(btn_row)

        self.params_text = QTextEdit()
        self.params_text.setReadOnly(True)
        self.params_text.setFont(QFont("Courier New", 10))
        left_layout.addWidget(self.params_text)

        left_panel.setLayout(left_layout)
        split_layout.addWidget(left_panel, 1)

        # ── Right panel: extra args input ────────────────────────────────────
        right_panel = QGroupBox("Additional Parameters")
        right_layout = QVBoxLayout()
        right_layout.setSpacing(6)

        self.help_label = QLabel()
        self.help_label.setStyleSheet("color: #666; font-size: 10px;")
        self.help_label.setWordWrap(True)
        right_layout.addWidget(self.help_label)

        self.extra_args_input = QTextEdit()
        self.extra_args_input.setFont(QFont("Courier New", 11))
        self.extra_args_input.setMaximumHeight(160)
        right_layout.addWidget(self.extra_args_input)

        right_panel.setLayout(right_layout)
        split_layout.addWidget(right_panel, 1)

        main_layout.addLayout(split_layout)

        # ── Buttons ──────────────────────────────────────────────────────────
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

        # Open on the requested method
        self._switch_method(initial_method)

    # ── Method switching ─────────────────────────────────────────────────────

    def _switch_method(self, method: str):
        """Flush current input, then load the new method's reference + args."""
        # Flush currently displayed text back to the dict before switching
        if self._current_method is not None:
            self._extra_args[self._current_method] = self.extra_args_input.toPlainText()

        self._current_method = method

        if method == "cpp":
            self.params_text.setPlainText(self.get_cpp_parameters_reference())
            self.extra_args_input.setPlaceholderText(
                "--word-thold 0.02\n--entropy-thold 2.4\n--no-speech-thold 0.6"
            )
            self.help_label.setText(
                "Applied by default: -sow (split-on-word), beam-size=5, best-of=5, temperature fallback on.\n"
                "One flag per line. Short form (-bo 3) or long form (--best-of 3). "
                "Language, model, output format and VAD are handled by the main tab."
            )
            self.btn_cpp.setStyleSheet(self._BTN_ACTIVE)
            self.btn_openai.setStyleSheet(self._BTN_INACTIVE)
        else:
            self.params_text.setPlainText(self.get_parameters_reference())
            self.extra_args_input.setPlaceholderText(
                "--patience 1.0\n--word_timestamps True\n--max_words_per_line 7\n--max_line_count 2"
            )
            self.help_label.setText(
                "One parameter per line.  Format: --parameter_name value\n"
                "Language, model, output format and task are handled by the main tab."
            )
            self.btn_openai.setStyleSheet(self._BTN_ACTIVE)
            self.btn_cpp.setStyleSheet(self._BTN_INACTIVE)

        self.extra_args_input.setPlainText(self._extra_args.get(method, ""))

    # ── Parameter references ─────────────────────────────────────────────────

    def get_cpp_parameters_reference(self) -> str:
        """Parameter reference for whisper-cli (whisper.cpp)."""
        return """\
Whisper CPP (whisper-cli) extra flags
======================================
Note: -l / --language, -m / --model, -f / --file, output format flags
and VAD flags are already set by the main tab. Only add flags not listed there.

Core decoding
-------------
-t N,   --threads N          [4]      number of threads for computation
-p N,   --processors N       [1]      number of processors
-bo N,  --best-of N          [5]      best-of candidates to keep
-bs N,  --beam-size N        [5]      beam size for beam search
-tp,    --temperature N      [0.00]   sampling temperature (0-1)
-tpi,   --temperature-inc N  [0.20]   temperature increment on fallback
-nf,    --no-fallback        [false]  disable temperature fallback
-mc N,  --max-context N      [-1]     max text context tokens to store
-ml N,  --max-len N          [0]      max segment length in characters
-sow,   --split-on-word      [false]  split on word rather than token
-ac N,  --audio-ctx N        [0]      audio context size (0 = all)

Quality / filtering thresholds
-------------------------------
-wt N,  --word-thold N       [0.01]   word timestamp probability threshold
-et N,  --entropy-thold N    [2.40]   entropy threshold for decoder fail
-lpt N, --logprob-thold N    [-1.00]  log probability threshold for fail
-nth N, --no-speech-thold N  [0.60]   no-speech probability threshold

Output options
--------------
-otxt,  --output-txt         [false]  also write a .txt file
-ovtt,  --output-vtt         [false]  also write a .vtt file
-olrc,  --output-lrc         [false]  also write a .lrc file
-oj,    --output-json        [false]  also write a .json file
-ojf,   --output-json-full   [false]  include token-level detail in JSON
-nt,    --no-timestamps      [false]  omit timestamps from output
-ps,    --print-special      [false]  print special tokens
        --print-confidence   [false]  print confidence scores
-pp,    --print-progress     [false]  print progress to stderr

Translation / diarization
-------------------------
-tr,    --translate          [false]  translate to English
-di,    --diarize            [false]  stereo audio diarization
-tdrz,  --tinydiarize        [false]  tinydiarize (requires tdrz model)

Advanced / experimental
-----------------------
        --prompt PROMPT      []       initial prompt (max n_text_ctx/2 tokens)
        --carry-initial-prompt [false] always prepend initial prompt
-dtw MODEL --dtw MODEL       []       compute token-level timestamps
-ng,    --no-gpu             [false]  disable GPU
-fa,    --flash-attn         [true]   enable flash attention
-nfa,   --no-flash-attn      [false]  disable flash attention
-sns,   --suppress-nst       [false]  suppress non-speech tokens
        --suppress-regex REGEX []     regex matching tokens to suppress
        --grammar GRAMMAR    []       GBNF grammar to guide decoding
        --grammar-rule RULE  []       top-level GBNF grammar rule name
        --grammar-penalty N  [100.0]  scale down logits of non-grammar tokens
-debug, --debug-mode         [false]  dump log_mel and other debug info
-ls,    --log-score          [false]  log best decoder scores of tokens

Voice Activity Detection (VAD) — set by main tab if model configured
---------------------------------------------------------------------
        --vad                [false]  enable VAD
-vm FNAME, --vad-model FNAME []       VAD model path (.onnx)
-vt N,  --vad-threshold N    [0.50]   speech probability threshold
-vspd N, --vad-min-speech-duration-ms N [250]  min speech duration (ms)
-vsd N,  --vad-min-silence-duration-ms N [100]  min silence to split (ms)
-vmsd N, --vad-max-speech-duration-s  N [FLT_MAX] auto-split threshold (s)
-vp N,  --vad-speech-pad-ms N [30]   extend segments by this padding (ms)
-vo N,  --vad-samples-overlap N [0.10] overlap between segments (s)

Time / clipping
---------------
-ot N,  --offset-t N         [0]      time offset in milliseconds
-on N,  --offset-n N         [0]      segment index offset
-d  N,  --duration N         [0]      duration of audio to process (ms)"""

    def get_parameters_reference(self) -> str:
        """Parameter reference for openai-whisper (Python package)."""
        return """\
OpenAI Whisper (python -m whisper) extra flags
===============================================
Note: --language, --model, --output_dir, --output_format and --task
are already set by the main tab. Only add flags not listed there.

Core decoding
-------------
--temperature TEMPERATURE         [0]      sampling temperature; 0 = greedy
--best_of BEST_OF                 [5]      candidates when temperature > 0
--beam_size BEAM_SIZE             [5]      beams in beam search (temperature=0)
--patience PATIENCE               [None]   beam search patience multiplier
--length_penalty LENGTH_PENALTY   [None]   token length penalty (alpha)

Context / prompting
-------------------
--initial_prompt INITIAL_PROMPT            optional prompt for first window
--carry_initial_prompt BOOL       [False]  prepend prompt to every decode()
--condition_on_previous_text BOOL [True]   use prior output as context prompt
--suppress_tokens SUPPRESS_TOKENS [-1]     comma-separated token ids to suppress

Quality / filtering thresholds
-------------------------------
--compression_ratio_threshold N   [2.4]    gzip ratio above = failed decode
--logprob_threshold N             [-1.0]   avg log-prob below = failed decode
--no_speech_threshold N           [0.6]    nospeech prob above = silence
--temperature_increment_on_fallback N [0.2] temp increase when decode fails

Hardware
--------
--device DEVICE                   [cpu]    pytorch device (cpu / cuda / mps)
--fp16 BOOL                       [True]   fp16 inference (faster on GPU)
--threads THREADS                 [0]      torch CPU threads (0 = auto)

Word-level timestamps (experimental)
-------------------------------------
--word_timestamps BOOL            [False]  extract per-word timestamps
--highlight_words BOOL            [False]  underline words in srt/vtt output
--max_line_width N                [None]   max chars per line (needs word_ts)
--max_line_count N                [None]   max lines per segment (needs word_ts)
--max_words_per_line N            [None]   max words per line (needs word_ts)
--prepend_punctuations CHARS               punctuation to attach to next word
--append_punctuations CHARS                punctuation to attach to prev word
--hallucination_silence_threshold N [None] skip silence if hallucination likely

Clipping
--------
--clip_timestamps CLIP_TIMESTAMPS [0]      start,end,... timestamps (seconds)"""

    # ── Save ─────────────────────────────────────────────────────────────────

    def save_settings(self):
        """Save extra args for both engines and close dialog."""
        # Flush the currently visible input back to the dict
        self._extra_args[self._current_method] = self.extra_args_input.toPlainText().strip()

        # Save Whisper CPP args
        self.config["whisper_cpp_extra_args"] = self._extra_args["cpp"]

        # Save OpenAI Whisper args
        if "whisper_options" not in self.config:
            self.config["whisper_options"] = {}
        raw = self._extra_args["openai"]
        parsed = " ".join(line.strip() for line in raw.split("\n") if line.strip())
        self.config["whisper_options"]["extra_args"] = raw
        self.config["whisper_options"]["extra_args_parsed"] = parsed

        save_config(self.config)
        self.accept()


# ============================================================================
# Burn-in subtitles dialog
# ============================================================================

class BurnInDialog(QDialog):
    """Dialog for configuring and launching the burn-in subtitles operation."""

    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self.config = config
        self.selected_files: list[str] = []
        self.setWindowTitle("Burn-in subtitles")
        self.setMinimumSize(640, 420)
        self.resize(720, 460)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(16, 16, 16, 16)

        top = QHBoxLayout()
        top.setSpacing(16)

        # ── Left: options ────────────────────────────────────────────────────
        opts_group = QGroupBox("Options")
        opts_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 11px; }")
        opts_layout = QVBoxLayout()
        opts_layout.setSpacing(10)

        # Quality
        q_row = QHBoxLayout()
        q_row.addWidget(QLabel("Output quality:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItem("720p", "720")
        self.quality_combo.addItem("1080p", "1080")
        self.quality_combo.currentIndexChanged.connect(self._on_quality_changed)
        q_row.addWidget(self.quality_combo)
        q_row.addStretch()
        opts_layout.addLayout(q_row)

        # Watermark
        wm_header = QHBoxLayout()
        self.watermark_check = QCheckBox("Add watermark")
        self.watermark_check.setChecked(self.config.get("use_watermarks", True))
        self.watermark_check.toggled.connect(self._on_watermark_toggled)
        wm_header.addWidget(self.watermark_check)
        wm_header.addStretch()
        opts_layout.addLayout(wm_header)

        self.wm_path_label = QLabel()
        self.wm_path_label.setStyleSheet("color: #555; font-size: 10px;")
        self.wm_path_label.setWordWrap(True)
        opts_layout.addWidget(self.wm_path_label)

        wm_browse_row = QHBoxLayout()
        self.wm_browse_btn = QPushButton("Browse…")
        self.wm_browse_btn.setFixedWidth(90)
        self.wm_browse_btn.clicked.connect(self._browse_watermark)
        wm_browse_row.addWidget(self.wm_browse_btn)
        wm_browse_row.addStretch()
        opts_layout.addLayout(wm_browse_row)

        opts_layout.addStretch()
        opts_group.setLayout(opts_layout)
        top.addWidget(opts_group, 1)

        # ── Right: file list ─────────────────────────────────────────────────
        files_group = QGroupBox("Video files")
        files_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 11px; }")
        files_layout = QVBoxLayout()
        files_layout.setSpacing(6)

        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.file_list.setAlternatingRowColors(True)
        files_layout.addWidget(self.file_list)

        file_btn_row = QHBoxLayout()
        add_btn = QPushButton("Add files…")
        add_btn.clicked.connect(self._add_files)
        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self._remove_selected)
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._clear_files)
        file_btn_row.addWidget(add_btn)
        file_btn_row.addWidget(remove_btn)
        file_btn_row.addWidget(clear_btn)
        file_btn_row.addStretch()
        files_layout.addLayout(file_btn_row)

        files_group.setLayout(files_layout)
        top.addWidget(files_group, 2)

        root.addLayout(top)

        # ── Bottom: action buttons ───────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self.burn_btn = QPushButton("Burn-in subtitles")
        self.burn_btn.setMinimumWidth(160)
        self.burn_btn.setDefault(True)
        self.burn_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self.burn_btn)
        root.addLayout(btn_row)

        # Initialise watermark display
        self._refresh_watermark_ui()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _current_wm_key(self) -> str:
        return f"watermark_{self.quality_combo.currentData()}p"

    def _refresh_watermark_ui(self):
        enabled = self.watermark_check.isChecked()
        self.wm_path_label.setVisible(enabled)
        self.wm_browse_btn.setVisible(enabled)
        if enabled:
            path = self.config.get(self._current_wm_key(), "")
            res = "1280×720" if self.quality_combo.currentData() == "720" else "1920×1080"
            if path:
                self.wm_path_label.setText(f"{path}\n(expected dimensions: {res})")
            else:
                self.wm_path_label.setText(f"No watermark configured — use Browse or set in Settings.\n(expected dimensions: {res})")

    def _on_quality_changed(self):
        self._refresh_watermark_ui()

    def _on_watermark_toggled(self):
        self._refresh_watermark_ui()

    def _browse_watermark(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select watermark image",
            str(Path(self.config.get(self._current_wm_key(), str(Path.home()))).parent),
            "Images (*.png *.jpg *.jpeg);;All Files (*)"
        )
        if path:
            self.config[self._current_wm_key()] = path
            self._refresh_watermark_ui()

    def _add_files(self):
        from_dir = str(get_downloads_dir())
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select video files",
            from_dir,
            "Video Files (*.mkv *.mp4 *.mov);;All Files (*)"
        )
        for p in paths:
            if p not in self.selected_files:
                self.selected_files.append(p)
                self.file_list.addItem(Path(p).name)

    def _remove_selected(self):
        for item in self.file_list.selectedItems():
            row = self.file_list.row(item)
            self.file_list.takeItem(row)
            del self.selected_files[row]

    def _clear_files(self):
        self.file_list.clear()
        self.selected_files.clear()

    # ── Result accessors ─────────────────────────────────────────────────────

    def get_resolution(self) -> str:
        return self.quality_combo.currentData()

    def get_use_watermarks(self) -> bool:
        return self.watermark_check.isChecked()

    def get_watermark_path(self) -> str:
        return self.config.get(self._current_wm_key(), "")


# ============================================================================
# Main application window
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
    # color functions
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
    # button style functions
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
    # lesbian flag style functions (slay)
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
        
        role_to_color = {
            "download": colors[0],
            "subtitle": colors[1],
            "process": colors[2],
            "remux": colors[3],
            "transcribe": colors[4],
            "header": colors[5],
        }
        for btn in self.findChildren(QPushButton):
            role = btn.property("ui_role")
            if role and role in role_to_color:
                self.apply_button_style(btn, role_to_color[role])
    
    def build_transcription_tab(self):
        """Create the dedicated transcription tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(8)

        _folder_strip_style = "QPushButton { background: none; color: #777; border: none; padding: 2px 6px; font-size: 10px; } QPushButton:hover { color: #555; text-decoration: underline; } QPushButton:pressed { color: #333; }"
        tr_folder_bar = QFrame()
        tr_folder_bar.setStyleSheet("QFrame { background: #f5f5f5; border-bottom: 1px solid #e0e0e0; }")
        tr_folder_layout = QHBoxLayout(tr_folder_bar)
        tr_folder_layout.setContentsMargins(4, 4, 4, 4)
        tr_open_downloads_top = QPushButton("Open downloads folder")
        tr_open_downloads_top.setStyleSheet(_folder_strip_style)
        tr_open_downloads_top.clicked.connect(lambda: open_folder_in_explorer(get_downloads_dir()))
        tr_open_subtitles_top = QPushButton("Open subtitles folder")
        tr_open_subtitles_top.setStyleSheet(_folder_strip_style)
        tr_open_subtitles_top.clicked.connect(lambda: open_folder_in_explorer(get_subtitles_dir()))
        tr_open_output_top = QPushButton("Open output folder")
        tr_open_output_top.setStyleSheet(_folder_strip_style)
        tr_open_output_top.clicked.connect(lambda: open_folder_in_explorer(get_output_dir()))
        tr_folder_layout.addWidget(tr_open_downloads_top)
        tr_folder_layout.addWidget(tr_open_subtitles_top)
        tr_folder_layout.addWidget(tr_open_output_top)
        tr_folder_layout.addStretch()
        layout.addWidget(tr_folder_bar)

        # Transcription setup
        file_group = QGroupBox("Setup")
        file_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        file_layout = QVBoxLayout()
        self.transcribe_file_paths = []

        # Method selector — primary choice, shown first
        _LABEL_W = 120   # all row labels share this width so controls align
        _COMBO_W = 280   # all dropdowns share this width

        method_row = QHBoxLayout()
        method_label = QLabel("Method:")
        method_label.setFixedWidth(_LABEL_W)
        method_label.setStyleSheet("font-weight: bold;")
        self.transcribe_method_combo = QComboBox()
        self.transcribe_method_combo.setFixedWidth(_COMBO_W)
        _cfg_now = load_config()
        for _backend in TRANSCRIBE_BACKENDS:
            self.transcribe_method_combo.addItem(_backend.name, _backend.backend_id)
            if not _backend.is_available(_cfg_now):
                # Grey out unavailable backends (still selectable)
                idx = self.transcribe_method_combo.count() - 1
                item_model = self.transcribe_method_combo.model()
                if item_model:
                    from PyQt5.QtGui import QColor
                    item_model.item(idx).setForeground(QColor("#aaaaaa"))
        method_row.addWidget(method_label, 0)
        method_row.addWidget(self.transcribe_method_combo, 0)
        method_row.addStretch()
        file_layout.addLayout(method_row)

        file_row = QHBoxLayout()
        file_label = QLabel("Select file(s):")
        file_label.setFixedWidth(_LABEL_W)
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
        lang_label.setFixedWidth(_LABEL_W)
        self.transcribe_language_combo = QComboBox()
        self.transcribe_language_combo.setFixedWidth(_COMBO_W)
        for name, code in TRANSCRIBE_LANGUAGES:
            self.transcribe_language_combo.addItem(name, code)
        lang_row.addWidget(lang_label, 0)
        lang_row.addWidget(self.transcribe_language_combo, 0)
        lang_row.addStretch()
        file_layout.addLayout(lang_row)

        # Output format selector
        format_row = QHBoxLayout()
        format_label = QLabel("Output Format:")
        format_label.setFixedWidth(_LABEL_W)
        self.transcribe_format_combo = QComboBox()
        self.transcribe_format_combo.setFixedWidth(_COMBO_W)
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
        format_row.addWidget(self.transcribe_format_combo, 0)
        format_row.addStretch()
        file_layout.addLayout(format_row)

        # Whisper model selector
        model_row = QHBoxLayout()
        model_label = QLabel("Whisper Model:")
        model_label.setFixedWidth(_LABEL_W)
        self.transcribe_model_combo = QComboBox()
        self.transcribe_model_combo.setFixedWidth(_COMBO_W)
        for _m_name, _m_size in [
            ("tiny",   "~75 MB"),
            ("base",   "~145 MB"),
            ("small",  "~465 MB"),
            ("medium", "~1.5 GB"),
            ("large",  "~2.9 GB"),
            ("turbo",  "~1.6 GB"),
        ]:
            self.transcribe_model_combo.addItem(f"{_m_name} ({_m_size})", _m_name)
        current_model = self.config.get("whisper_model", "turbo")
        model_index = self.transcribe_model_combo.findData(current_model)
        if model_index >= 0:
            self.transcribe_model_combo.setCurrentIndex(model_index)
        else:
            self.transcribe_model_combo.setCurrentIndex(self.transcribe_model_combo.findData("turbo"))
        # Save model key (not display text) when changed
        self.transcribe_model_combo.currentIndexChanged.connect(
            lambda: self.save_whisper_model(self.transcribe_model_combo.currentData())
        )
        model_row.addWidget(model_label, 0)
        model_row.addWidget(self.transcribe_model_combo, 0)
        model_row.addStretch()
        file_layout.addLayout(model_row)

        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Action bar: separated from the form by a top border
        action_bar = QFrame()
        action_bar.setStyleSheet("QFrame { border-top: 1px solid #e0e0e0; }")
        action_bar_layout = QHBoxLayout(action_bar)
        action_bar_layout.setContentsMargins(0, 6, 0, 2)
        action_bar_layout.setSpacing(8)

        _btn_style = (
            "QPushButton { background: #f5f5f5; border: 1px solid #ccc; border-radius: 4px;"
            "  font-size: 11px; color: #555; padding: 4px 10px; }"
            "QPushButton:hover { background: #eaeaea; border-color: #aaa; color: #333; }"
            "QPushButton:pressed { background: #d8d8d8; }"
        )

        gear_btn = QPushButton("⚙  Advanced options")
        gear_btn.setToolTip("Open advanced transcription settings")
        gear_btn.setStyleSheet(_btn_style)
        gear_btn.clicked.connect(self.open_whisper_options)

        # Post-processing toggle + options gear
        self.transcribe_post_proc_cb = QCheckBox("Post-processing")
        self.transcribe_post_proc_cb.setToolTip("Apply post-processing steps after transcription (adjust timings, merge lines, etc.)")
        self.transcribe_post_proc_cb.setChecked(self.config.get("whisper_post_processing_enabled", False))
        self.transcribe_post_proc_cb.toggled.connect(self._on_post_proc_toggled)
        post_proc_gear = QPushButton("⚙")
        post_proc_gear.setFixedWidth(28)
        post_proc_gear.setToolTip("Configure post-processing options")
        post_proc_gear.setStyleSheet(_btn_style)
        post_proc_gear.clicked.connect(self.open_post_processing_options)

        self.transcribe_main_btn = QPushButton("Transcribe")
        self.transcribe_main_btn.setProperty("ui_role", "transcribe")
        self.transcribe_main_btn.clicked.connect(self._transcribe_from_tab_by_method)

        action_bar_layout.addWidget(gear_btn)
        action_bar_layout.addWidget(self.transcribe_post_proc_cb)
        action_bar_layout.addWidget(post_proc_gear)
        action_bar_layout.addWidget(self.transcribe_main_btn)
        action_bar_layout.addStretch()
        layout.addWidget(action_bar)
        
        transcribe_log_group, self.transcribe_log_output = self._make_log_panel(
            placeholder="Logs will appear here after processing starts"
        )
        layout.addWidget(transcribe_log_group)
        
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
    
    def _transcribe_from_tab_by_method(self):
        """Dispatch to the appropriate transcription handler based on method selection.

        Looks up the selected backend_id in TRANSCRIBE_BACKENDS so that adding a
        new backend only requires registering it there.
        """
        method = self.transcribe_method_combo.currentData()
        # Legacy direct-method dispatch (kept for the install-flow handlers which
        # call transcribe_whisper_cpp_from_tab / transcribe_from_tab / transcribe_long_from_tab
        # directly after install succeeds)
        if method == "standard":
            self.transcribe_from_tab()
        elif method == "long":
            self.transcribe_long_from_tab()
        elif method == "cpp":
            self.transcribe_whisper_cpp_from_tab()
        else:
            # Generic backend dispatch for any backend registered in TRANSCRIBE_BACKENDS
            backend = next((b for b in TRANSCRIBE_BACKENDS if b.backend_id == method), None)
            if backend:
                video_paths = self._get_transcribe_paths()
                if not video_paths:
                    QMessageBox.warning(self, "No File",
                                        "Please select a video or audio file to transcribe.")
                    return
                language_code = self.transcribe_language_combo.currentData() or "auto"
                model         = self.transcribe_model_combo.currentData()
                config        = load_config()
                self.transcribe_log(f"Starting transcription ({backend.name})...")
                self.transcribe_progress_bar.setVisible(True)
                self.transcribe_stop_btn.setVisible(True)
                self.transcribe_stop_btn.setEnabled(True)
                self.transcribe_progress_bar.setRange(0, 0)

                def _log(msg): self.transcribe_log(msg)
                self.worker = ScriptWorker(
                    run_batch_transcribe,
                    lambda p, lc=language_code, m=model, c=config: backend.transcribe(
                        p, lc, m, c, log_callback=_log),
                    video_paths,
                )
                self.worker.log_message.connect(_log)
                self.worker.finished.connect(self.on_transcribe_finished)
                self.worker.start()
            else:
                self.transcribe_from_tab()

    def save_whisper_model(self, model: str):
        """Save Whisper model selection to config."""
        config = load_config()
        config["whisper_model"] = model
        save_config(config)
        self.config["whisper_model"] = model
    
    def browse_transcribe_file(self):
        """Browse for file(s) to transcribe."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Video or Audio File(s) to Transcribe",
            str(get_downloads_dir()),
            "Media Files (*.mkv *.mp4 *.mov *.mp3 *.wav *.m4a);;All Files (*)"
        )
        if file_paths:
            self.transcribe_file_paths = file_paths
            if len(file_paths) == 1:
                self.transcribe_file_input.setText(file_paths[0])
            else:
                self.transcribe_file_input.setText(f"{len(file_paths)} files selected")
    
    def _get_transcribe_paths(self) -> List[Path]:
        """Resolve selected file path(s) from transcribe tab. Returns list of Paths (may be empty)."""
        if self.transcribe_file_paths:
            return [Path(p) for p in self.transcribe_file_paths]
        text = self.transcribe_file_input.text().strip()
        if not text or text == "No file selected" or re.match(r"^\d+ files selected$", text):
            return []
        p = Path(text)
        return [p] if p.exists() else []
    
    def transcribe_from_tab(self):
        """Transcribe video from the dedicated tab."""
        video_paths = self._get_transcribe_paths()
        if not video_paths:
            QMessageBox.warning(self, "No File", "Please select a video or audio file to transcribe.")
            return
        missing = [p for p in video_paths if not p.exists()]
        if missing:
            QMessageBox.warning(self, "File Not Found", f"File(s) do not exist:\n{missing[0]}")
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
        model = self.transcribe_model_combo.currentData()
        
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
        
        n = len(video_paths)
        self.transcribe_log(f"Starting transcription of {n} file(s)")
        self.transcribe_log(f"Language: {language_code}, Model: {model}, Format: {output_format}")
        
        # Show progress bar and stop button
        self.transcribe_progress_bar.setVisible(True)
        self.transcribe_stop_btn.setVisible(True)
        self.transcribe_stop_btn.setEnabled(True)
        self.transcribe_progress_bar.setRange(0, n) if n > 1 else self.transcribe_progress_bar.setRange(0, 0)
        
        def transcribe_with_params(video_path, language_code, model, whisper_options, output_format, progress_callback=None, log_callback=None):
            return transcribe_video(video_path, language_code, model, whisper_options, output_format, progress_callback, log_callback)
        
        def tab_log_callback(msg):
            self.transcribe_log(msg)
        
        self.worker = ScriptWorker(
            run_batch_transcribe,
            transcribe_with_params,
            video_paths,
            language_code,
            model,
            whisper_options,
            output_format,
        )
        self.worker.log_message.connect(tab_log_callback)
        self.worker.finished.connect(self.on_transcribe_finished)
        self.worker.start()
    
    def transcribe_log(self, message):
        """Add message to transcription log."""
        from datetime import datetime
        timestamp = datetime.now().strftime("[%H:%M:%S]")
        self.transcribe_log_output.append(f"{timestamp} {message}")
        self.transcribe_log_output.verticalScrollBar().setValue(
            self.transcribe_log_output.verticalScrollBar().maximum()
        )
        # Also log to main log
        self.log(message)
    
    def on_transcribe_finished(self, success: bool):
        """Handle transcription completion."""
        self.transcribe_progress_bar.setVisible(False)
        self.transcribe_stop_btn.setVisible(False)
        # Reset both stop buttons
        self.stop_btn.setEnabled(False)
        self.stop_btn.setText("Stop")
        self.transcribe_stop_btn.setEnabled(False)
        self.transcribe_stop_btn.setText("Stop")
        if success:
            self.transcribe_log("✓ Transcription completed successfully!")
        else:
            self.transcribe_log("✗ Transcription failed. Check log for details.")
        self.worker = None

    def transcribe_long_from_tab(self):
        """Transcribe long video using VAD + Whisper (for files over ~5 min)."""
        video_paths = self._get_transcribe_paths()
        if not video_paths:
            QMessageBox.warning(self, "No File", "Please select a video or audio file to transcribe.")
            return
        missing = [p for p in video_paths if not p.exists()]
        if missing:
            QMessageBox.warning(self, "File Not Found", f"File(s) do not exist:\n{missing[0]}")
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
                    ["torch", "torchaudio", "torchcodec", "pysrt", "openai-whisper"],
                    parent=dlg,
                )
                worker.log_message.connect(lambda m: log.append(m))
                def on_finished(ok):
                    worker.wait()
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
        model = self.transcribe_model_combo.currentData()
        config = load_config()
        whisper_model_asked = config.get("whisper_model_asked", False)
        if not whisper_model_asked:
            model_dialog = WhisperModelDialog(self, model)
            if model_dialog.exec_() != QDialog.Accepted:
                return
            config["whisper_model_asked"] = True
            config["whisper_has_existing_model"] = model_dialog.get_result()
            save_config(config)
        n = len(video_paths)
        self.transcribe_log(f"Starting VAD-assisted transcription of {n} file(s)")
        self.transcribe_log(f"Language: {language_code}, Model: {model}")
        self.transcribe_progress_bar.setVisible(True) 
        self.transcribe_stop_btn.setVisible(True) 
        self.transcribe_stop_btn.setEnabled(True) 
        self.transcribe_progress_bar.setRange(0, 0)
        def tab_log_callback(msg): 
            self.transcribe_log(msg)
        self.worker = ScriptWorker( 
            run_batch_transcribe,
            transcribe_video_vad, 
            video_paths,
            language_code, 
            model, 
        )
        self.worker.log_message.connect(tab_log_callback) 
        self.worker.finished.connect(self.on_transcribe_finished) 
        self.worker.start() 
    
    def _do_whisper_cpp_install(self, on_success_after_install=None): 
        """Install Whisper CPP. On macOS with Homebrew: Metal-enabled; otherwise pip (CPU)."""
        dlg = QDialog(self) 
        dlg.setWindowTitle("Installing Whisper CPP...")
        dlg.setMinimumWidth(400) 
        dlg.setWindowModality(Qt.ApplicationModal) 
        layout = QVBoxLayout()
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 0)
        layout.addWidget(progress_bar)
        log = QTextEdit()
        log.setReadOnly(True)
        layout.addWidget(log)
        close_btn = QPushButton("Close")
        close_btn.setEnabled(False)
        layout.addWidget(close_btn)
        dlg.setLayout(layout)
        worker = WhisperCppInstallWorker(parent=dlg)        
        worker.log_message.connect(lambda m: log.append(m)) 
        def on_finished(ok):
            worker.wait() 
            if ok:
                log.append("\nInstalled successfully") 
                progress_bar.setVisible(False)
                close_btn.setEnabled(True) 
                close_btn.setText("Installed successfully")
                def auto_close():
                    if on_success_after_install: 
                        on_success_after_install()
                    dlg.accept() 
                QTimer.singleShot(1500, auto_close)
            else:
                log.append("\nInstallation failed. Click Close, then run: python -m pip install whisper.cpp-cli") 
                close_btn.setEnabled(True) 
        close_btn.clicked.connect(dlg.accept) 
        worker.finished.connect(on_finished) 
        worker.start() 
        dlg.exec_()         

    def transcribe_whisper_cpp_from_tab(self):
        """Transcribe using Whisper CPP. Faster, built-in VAD.""" 
        video_paths = self._get_transcribe_paths() 
        if not video_paths:
            QMessageBox.warning(self, "No File", "Please select a video or audio file to transcribe.") 
            return
        missing = [p for p in video_paths if not p.exists()] 
        if missing:
            QMessageBox.warning(self, "File Not Found", f"File(s) do not exist:\n{missing[0]}") 
            return
        language_code = self.transcribe_language_combo.currentData()
        if not language_code:
            language_code = "auto" # set language code to auto
        config = load_config() # load config
        binary = _get_whisper_cpp_binary(config) # get whisper cpp binary
        if not binary or not Path(binary).exists():
            reply = QMessageBox.question( # show question dialog    
                self,
                "Whisper CPP Not Installed",
                "Whisper CPP is not installed. Would you like us to install it for you?\n\n"
                "(whisper.cpp-cli, ~50 MB. On Windows, pre-built wheels may not be available—we'll try anyway; "
                "if it fails, you can build from source or use WSL.)",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            # if yes, install whisper cpp
            if reply == QMessageBox.Yes:
                self._do_whisper_cpp_install(on_success_after_install=self.transcribe_whisper_cpp_from_tab)
                return
            QMessageBox.warning(
                self,
                "Whisper CPP Not Found",
                "Whisper CPP binary not found.\n\n"
                "Install from https://github.com/ggerganov/whisper.cpp and set whisper_cpp_path "
                "in settings.json, or use the install option when prompted."
            )
            return
        # Use same model as UI selector
        ui_model = self.transcribe_model_combo.currentData()
        model_name = "large-v3-turbo" if ui_model == "turbo" else ui_model
        n = len(video_paths)
        self.transcribe_log(f"Starting Whisper CPP transcription of {n} file(s)")
        self.transcribe_log(f"Language: {language_code}, Model: {model_name}")
        self.transcribe_progress_bar.setVisible(True)
        self.transcribe_stop_btn.setVisible(True)
        self.transcribe_stop_btn.setEnabled(True)
        self.transcribe_progress_bar.setRange(0, 0)

        def tab_log_callback(msg):
            self.transcribe_log(msg)

        self.worker = ScriptWorker(
            run_batch_transcribe,
            transcribe_video_whisper_cpp,
            video_paths,
            language_code,
            model_name,
        )
        self.worker.log_message.connect(tab_log_callback)
        self.worker.finished.connect(self.on_transcribe_finished)
        self.worker.start()

    def build_remux_tab(self):
        """Create the dedicated remuxing tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(LAYOUT_SPACING)
        
        # Header
        header_row = QHBoxLayout()
        header_label = QLabel("Remux")
        header_label.setFont(QFont("Arial", 14, QFont.Bold))
        header_row.addWidget(header_label)
        header_row.addStretch()
        layout.addLayout(header_row)
        
        # Description
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
        add_files_btn.setProperty("ui_role", "remux")
        add_files_btn.clicked.connect(self.add_remux_files)
        auto_match_btn = QPushButton("Auto-match Subtitles")
        auto_match_btn.setProperty("ui_role", "remux")
        auto_match_btn.clicked.connect(self.auto_match_remux_subtitles)
        buttons_row.addWidget(add_files_btn)
        buttons_row.addWidget(auto_match_btn)
        buttons_row.addSpacing(10)
        remove_files_btn = QPushButton("Remove")
        remove_files_btn.setProperty("ui_role", "remux")
        remove_files_btn.clicked.connect(self.remove_remux_files)
        clear_files_btn = QPushButton("Clear")
        clear_files_btn.setProperty("ui_role", "remux")
        clear_files_btn.clicked.connect(self.clear_remux_files)
        buttons_row.addWidget(remove_files_btn)
        buttons_row.addWidget(clear_files_btn)
        buttons_row.addStretch()
        media_info_btn = QPushButton("Media Info")
        media_info_btn.setProperty("ui_role", "remux")
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
        self.remux_files_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.remux_files_tree.customContextMenuRequested.connect(self.show_track_context_menu)

        # Empty state placeholder (shown in tree area when no files)
        self.remux_empty_placeholder = QLabel("No files added yet. Click Add Files to get started.")
        self.remux_empty_placeholder.setAlignment(Qt.AlignCenter)
        self.remux_empty_placeholder.setStyleSheet("color: #888; font-size: 12px; padding: 24px; background-color: #f5f5f5; border: 1px solid #ddd; border-radius: 3px;")
        self.remux_empty_placeholder.setMinimumHeight(120)

        self.remux_tree_stack = QStackedWidget()
        self.remux_tree_stack.addWidget(self.remux_empty_placeholder)
        self.remux_tree_stack.addWidget(self.remux_files_tree)
        self.remux_tree_stack.setCurrentWidget(self.remux_empty_placeholder)
        file_layout.addWidget(self.remux_tree_stack)

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
        remux_selected_btn.setProperty("ui_role", "remux")
        remux_selected_btn.clicked.connect(self.remux_selected_files_action)
        actions_row.addWidget(remux_selected_btn)
        split_audio_btn = QPushButton("Split Audio")
        split_audio_btn.setProperty("ui_role", "remux")
        split_audio_btn.clicked.connect(self.split_audio_channels_batch)
        actions_row.addWidget(split_audio_btn)
        actions_row.addStretch()
        layout.addLayout(actions_row)
        
        remux_log_group, self.remux_log_output = self._make_log_panel(
            placeholder="Logs will appear here after processing starts"
        )
        layout.addWidget(remux_log_group)
        tab.setLayout(layout)
        return tab
    
    def _remux_log(self, message: str):
        """Append message to remux log and scroll to bottom."""
        self.remux_log_output.append(message)
        self.remux_log_output.verticalScrollBar().setValue(
            self.remux_log_output.verticalScrollBar().maximum()
        )
    
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
                return True
        return False
    
    def auto_match_remux_subtitles(self):
        """For each video in the list, find a same-name SRT/VTT (same folder or Subtitles folder) and attach it."""
        matched = 0
        for video_path in self.remux_selected_files:
            if self._attach_matching_subtitle_for_file(video_path):
                matched += 1
        if matched > 0:
            self._remux_log(f"Auto-matched {matched} subtitle(s) (same name as video).")
        else:
            self._remux_log("No matching subtitle files found (look for .srt/.vtt with same name in video folder or Subtitles folder).")
    
    def add_file_to_tree(self, video_path: Path):
        """Add a file to the tree widget with its tracks."""
        if not video_path.exists():
            return
        
        config = self.remux_file_configs.get(video_path, {})
        sub_path = config.get('subtitle_file')
        
        # Create file item collapsed by default
        file_item = QTreeWidgetItem(self.remux_files_tree)
        file_item.setText(0, video_path.name)
        file_item.setText(1, "File")
        file_item.setExpanded(False)  
        file_item.setData(0, 256, str(video_path))  
        
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
        
        # Col 3 (Language): lang + default
        opts_row = QWidget()
        opts_row.setMaximumWidth(130) 
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
            self._remux_log(f"Error: Configuration not found for {video_path.name}")
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
            self._remux_log(f"Error: File not found in tree")
            return
        
        # Collect selected tracks
        selected_video = []
        selected_audio = []
        selected_subtitles = []
        external_subtitle = config.get('subtitle_file')
        
        for i in range(file_item.childCount()):
            track_item = file_item.child(i)
            if track_item.checkState(0) == 2:
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
        self._remux_log(f"Remuxing {video_path.name}...")
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
            self._remux_log(f"✓ Saved: {out_path}")
        else:
            # Preserve FFmpeg error if already set
            lines = self.remux_log_output.toPlainText().strip().split("\n")
            last_line = lines[-1] if lines else ""
            if not last_line.startswith("Error:"):
                self._remux_log(f"✗ Failed to remux {video_path.name}")
    
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
                self._remux_log(f"Error: {'; '.join(error_msg)}")
            return result.returncode == 0 and output_file.exists()
        except Exception as e:
            self._remux_log(f"Error: {str(e)}")
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
            self._remux_log("Error: No files selected")
            return
        
        # Remux each file
        success_count = 0
        for video_path in files_to_remux:
            self.remux_single_file(video_path)
            lines = self.remux_log_output.toPlainText().strip().split("\n")
            last_line = lines[-1] if lines else ""
            if last_line.startswith("✓"):
                success_count += 1
        
        if success_count > 0:
            self._remux_log(f"✓ Remuxed {success_count}/{len(files_to_remux)} files")
    
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
        # for now we'll show a simple dialog because the remux window makes me mad
        # it's just really not looking good but i also don't know how to fix it for the better
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
        """Update the file count label and empty state visibility."""
        count = len(self.remux_selected_files)
        if count == 0:
            self.remux_file_count_label.setText("No files selected")
            self.remux_tree_stack.setCurrentWidget(self.remux_empty_placeholder)
        else:
            self.remux_tree_stack.setCurrentWidget(self.remux_files_tree)
            if count == 1:
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
            self._remux_log(f"Error: File not found: {first_file.name}")
            return
        
        tracks = analyze_tracks(first_file)
        if not tracks['audio']:
            self._remux_log("Error: No audio tracks found in video files.")
            return
        
        channel_count = tracks['audio'][0].get('channels', 0)
        if channel_count == 0:
            self._remux_log("Error: Could not determine audio channel count.")
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
                    self._remux_log(msg)
                else:
                    self._remux_log(f"{len(errors)} error(s) occurred")
        
        self._remux_log(f"Splitting audio channels ({channel_count} channels)...")
        
        # Process files directly (output to same directory as each file)
        for video_file in self.remux_selected_files:
            if video_file.exists():
                output_dir = video_file.parent
                split_audio_channels(video_file, output_dir, channel_count, split_log_callback)
        
        if errors:
            self._remux_log(f"Error: {len(errors)} file(s) failed")
        else:
            self._remux_log(f"✓ Split {channel_count} channels for {len(self.remux_selected_files)} file(s)")
    
    def _make_log_panel(self, title: str = "LOG OUTPUT", placeholder: str = None):
        """Returns (group, text_edit). Caller adds to layout."""
        group = QGroupBox(title)
        group.setStyleSheet("QGroupBox { font-weight: bold; }")
        layout = QVBoxLayout()
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setFont(QFont("Monaco", 9))
        text_edit.setMinimumHeight(LOG_MIN_HEIGHT)
        text_edit.setStyleSheet("QTextEdit { background-color: #f5f5f5; border: 1px solid #ddd; border-radius: 3px; }")
        if placeholder:
            text_edit.setPlaceholderText(placeholder)
        layout.addWidget(text_edit)
        group.setLayout(layout)
        return group, text_edit

    def build_header(self, main_layout: QVBoxLayout):
        """Build header with app name, version, About/FAQ/Settings."""
        header_left_layout = QVBoxLayout()
        header_left_layout.setSpacing(4)

        app_name_label = OutlinedLabel("SP WORKSHOP")
        app_name_label.setFont(QFont("Arial", 25, QFont.Bold))
        app_name_label.setStyleSheet("""
            background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #df4300, stop:0.20 #f48a32, stop:0.33 #ffab68,
                stop:0.5 white, stop:0.66 #dc7bb3, stop:0.80 #c46ea1, stop:1 #b42075);
            padding: 4px 10px;
            border-radius: 5px;
        """)
        header_left_layout.addWidget(app_name_label)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        header_left_widget = QWidget()
        header_left_widget.setLayout(header_left_layout)
        header_layout.addWidget(header_left_widget)
        header_layout.addStretch()

        about_btn = QPushButton("About")
        about_btn.setProperty("ui_role", "header")
        about_btn.setFont(QFont("Arial", 10))
        about_btn.clicked.connect(self.open_about)
        faq_btn = QPushButton("FAQ")
        faq_btn.setProperty("ui_role", "header")
        faq_btn.setFont(QFont("Arial", 10))
        faq_btn.clicked.connect(self.open_faq)
        settings_btn = QPushButton("Settings")
        settings_btn.setProperty("ui_role", "header")
        settings_btn.setFont(QFont("Arial", 10))
        settings_btn.clicked.connect(self.open_settings)
        header_layout.addWidget(about_btn)
        header_layout.addWidget(faq_btn)
        header_layout.addWidget(settings_btn)

        main_layout.addLayout(header_layout)

    def build_download_tab(self) -> QWidget:
        """Build the Download tab."""
        download_tab = QWidget()
        download_tab_layout = QVBoxLayout()
        download_tab_layout.setSpacing(LAYOUT_SPACING)
        download_tab.setLayout(download_tab_layout)

        _folder_strip_style = "QPushButton { background: none; color: #777; border: none; padding: 2px 6px; font-size: 10px; } QPushButton:hover { color: #555; text-decoration: underline; } QPushButton:pressed { color: #333; }"
        dl_folder_bar = QFrame()
        dl_folder_bar.setStyleSheet("QFrame { background: #f5f5f5; border-bottom: 1px solid #e0e0e0; }")
        dl_folder_layout = QHBoxLayout(dl_folder_bar)
        dl_folder_layout.setContentsMargins(4, 4, 4, 4)
        dl_open_downloads_top = QPushButton("Open downloads folder")
        dl_open_downloads_top.setStyleSheet(_folder_strip_style)
        dl_open_downloads_top.clicked.connect(lambda: open_folder_in_explorer(get_downloads_dir()))
        dl_open_subtitles_top = QPushButton("Open subtitles folder")
        dl_open_subtitles_top.setStyleSheet(_folder_strip_style)
        dl_open_subtitles_top.clicked.connect(lambda: open_folder_in_explorer(get_subtitles_dir()))
        dl_open_output_top = QPushButton("Open output folder")
        dl_open_output_top.setStyleSheet(_folder_strip_style)
        dl_open_output_top.clicked.connect(lambda: open_folder_in_explorer(get_output_dir()))
        dl_folder_layout.addWidget(dl_open_downloads_top)
        dl_folder_layout.addWidget(dl_open_subtitles_top)
        dl_folder_layout.addWidget(dl_open_output_top)
        dl_folder_layout.addStretch()
        download_tab_layout.addWidget(dl_folder_bar)

        # Naming/options group
        naming_group = QGroupBox("Naming options")
        naming_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        naming_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        naming_layout = QVBoxLayout()
        naming_layout.setContentsMargins(8, 4, 8, 6)
        naming_row1 = QHBoxLayout()
        naming_row1.addWidget(QLabel("Mode:"))
        self.download_mode_combo = QComboBox()
        self.download_mode_combo.addItems(["Episode(s)", "Movie"])
        self.download_mode_combo.setMaximumWidth(100)
        naming_row1.addWidget(self.download_mode_combo)

        naming_row1.addWidget(QLabel("Name:"))
        self.download_name_input = QLineEdit()
        self.download_name_input.setPlaceholderText("e.g. Show Name (2025)")
        self.download_name_input.setMinimumWidth(140)
        self.download_name_input.setMaximumWidth(220)
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
        naming_row1.addWidget(self.download_items_input)

        naming_row1.addStretch()

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

        naming_layout.addLayout(naming_row1)
        naming_group.setLayout(naming_layout)
        download_tab_layout.addWidget(naming_group)

        # Commands group
        commands_group = QGroupBox()
        commands_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 11px; }")
        commands_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)
        commands_layout = QVBoxLayout()
        commands_layout.setContentsMargins(8, 4, 8, 6)
        commands_layout.setSpacing(4)

        commands_header_row = QHBoxLayout()
        commands_heading = QLabel("Commands")
        commands_heading.setStyleSheet("font-weight: bold;")
        commands_header_row.addWidget(commands_heading)
        commands_header_row.addSpacing(8)
        commands_how_btn = QPushButton("How to get commands")
        commands_how_btn.setFlat(True)
        commands_how_btn.setStyleSheet("color: #0066cc; text-decoration: underline; font-weight: normal; font-size: 11px;")
        commands_how_btn.setCursor(Qt.PointingHandCursor)
        commands_how_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DOWNLOAD_INSTRUCTIONS_URL)))
        commands_header_row.addWidget(commands_how_btn)
        commands_header_row.addStretch()
        commands_layout.addLayout(commands_header_row)

        self.commands_text = QTextEdit()
        self.commands_text.setPlaceholderText(
            'Paste commands, one per line. See "How to get commands" for format.'
        )
        self.commands_text.setMinimumHeight(90)
        self.commands_text.setMaximumHeight(120)
        commands_layout.addWidget(self.commands_text)
        commands_group.setLayout(commands_layout)
        download_tab_layout.addWidget(commands_group)
        download_tab_layout.addSpacing(-4)

        # Action row: Quality → Download (primary) → stretch → Clear → Open in LosslessCut
        download_buttons = QHBoxLayout()
        self.download_quality_combo = QComboBox()
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
        download_btn = QPushButton("(Batch) Download")
        download_btn.setProperty("ui_role", "download")
        download_btn.setMinimumWidth(160)
        download_btn.clicked.connect(lambda: self.download_episodes(self.download_quality_combo.currentData()))
        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet(
            "QPushButton { color: #c0392b; border: 1px solid #e8c0bb; background: #fff5f4; "
            "border-radius: 3px; padding: 4px 10px; } "
            "QPushButton:hover { background: #fde8e6; } "
            "QPushButton:pressed { background: #f9d0cc; }"
        )
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(lambda: self.commands_text.clear())
        open_lossless_btn = QPushButton("Open in LosslessCut...")
        open_lossless_btn.setStyleSheet(
            "QPushButton { color: #555; border: 1px solid #ccc; background: #f9f9f9; "
            "border-radius: 3px; padding: 4px 10px; } "
            "QPushButton:hover { background: #efefef; } "
            "QPushButton:pressed { background: #e5e5e5; }"
        )
        open_lossless_btn.setCursor(Qt.PointingHandCursor)
        open_lossless_btn.clicked.connect(self.open_lossless_cut)
        download_buttons.addWidget(self.download_quality_combo)
        download_buttons.addWidget(download_btn)
        download_buttons.addStretch()
        download_buttons.addWidget(clear_btn)
        download_buttons.addWidget(open_lossless_btn)
        download_tab_layout.addLayout(download_buttons)

        download_log_group, self.download_log_output = self._make_log_panel(
            placeholder="Logs will appear here after processing starts"
        )
        download_tab_layout.addWidget(download_log_group, 1)

        return download_tab

    def build_subtitles_tab(self) -> QWidget:
        """Build the Subtitles tab."""
        main_tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(LAYOUT_SPACING)
        main_tab.setLayout(layout)

        # All buttons share this fixed width (sized to fit "Open subtitles folder")
        BUTTON_WIDTH = 200

        _folder_strip_style = "QPushButton { background: none; color: #777; border: none; padding: 2px 6px; font-size: 10px; } QPushButton:hover { color: #555; text-decoration: underline; } QPushButton:pressed { color: #333; }"

        # Folder shortcuts
        folder_bar = QFrame()
        folder_bar.setStyleSheet("QFrame { background: #f5f5f5; border-bottom: 1px solid #e0e0e0; }")
        folder_bar_layout = QHBoxLayout(folder_bar)
        folder_bar_layout.setContentsMargins(4, 4, 4, 4)
        open_downloads_btn = QPushButton("Open downloads folder")
        open_downloads_btn.setStyleSheet(_folder_strip_style)
        open_downloads_btn.clicked.connect(lambda: open_folder_in_explorer(get_downloads_dir()))
        open_subtitles_btn = QPushButton("Open subtitles folder")
        open_subtitles_btn.setStyleSheet(_folder_strip_style)
        open_subtitles_btn.clicked.connect(lambda: open_folder_in_explorer(get_subtitles_dir()))
        open_output_btn = QPushButton("Open output folder")
        open_output_btn.setStyleSheet(_folder_strip_style)
        open_output_btn.clicked.connect(lambda: open_folder_in_explorer(get_output_dir()))
        folder_bar_layout.addWidget(open_downloads_btn)
        folder_bar_layout.addWidget(open_subtitles_btn)
        folder_bar_layout.addWidget(open_output_btn)
        folder_bar_layout.addStretch()
        layout.addWidget(folder_bar)

        # Process flow: buttons stacked, description on right of each
        process_frame = QFrame()
        process_frame.setStyleSheet("QFrame { border: 1px solid #ebebeb; border-radius: 4px; background: #fafafa; }")
        process_layout = QVBoxLayout(process_frame)
        process_layout.setSpacing(6)
        process_layout.setContentsMargins(4, 6, 4, 6)

        extract_row = QHBoxLayout()
        extract_btn = QPushButton("Extract subtitles")
        extract_btn.setProperty("ui_role", "subtitle")
        extract_btn.setFixedWidth(BUTTON_WIDTH)
        extract_btn.clicked.connect(self.extract_subtitles)
        extract_desc = QLabel("Expects MKV files in downloads folder. Extracts subtitles to subtitles folder.")
        extract_desc.setFont(QFont("Arial", 12))
        extract_desc.setStyleSheet("color: #555;")
        extract_desc.setWordWrap(True)
        extract_row.addWidget(extract_btn)
        extract_row.addWidget(extract_desc, 1)
        process_layout.addLayout(extract_row)

        clean_row = QHBoxLayout()
        clean_btn = QPushButton("Clean subtitles")
        clean_btn.setProperty("ui_role", "subtitle")
        clean_btn.setFixedWidth(BUTTON_WIDTH)
        clean_btn.clicked.connect(self.clean_subtitles)
        clean_desc = QLabel("Works on SRT files in subtitles folder (e.g. from Extract). Cleans color tags, auto-breaks and common errors.")
        clean_desc.setFont(QFont("Arial", 12))
        clean_desc.setStyleSheet("color: #555;")
        clean_desc.setWordWrap(True)
        clean_row.addWidget(clean_btn)
        clean_row.addWidget(clean_desc, 1)
        process_layout.addLayout(clean_row)

        translate_row = QHBoxLayout()
        translate_btn = QPushButton("Translate subtitles")
        translate_btn.setProperty("ui_role", "subtitle")
        translate_btn.setFixedWidth(BUTTON_WIDTH)
        translate_btn.clicked.connect(self.translate_subtitles)
        translate_desc = QLabel("Select SRT files to translate.")
        translate_desc.setFont(QFont("Arial", 12))
        translate_desc.setStyleSheet("color: #555;")
        translate_desc.setWordWrap(True)
        translate_row.addWidget(translate_btn)
        translate_row.addWidget(translate_desc, 1)
        process_layout.addLayout(translate_row)

        burn_row = QHBoxLayout()
        burn_btn = QPushButton("Burn-in subtitles")
        burn_btn.setFixedWidth(BUTTON_WIDTH)
        burn_btn.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #f48a32;
                border: 2px solid #f48a32;
                border-radius: 5px;
                padding: 4px 12px;
                font-weight: bold;
                min-height: 18px;
            }
            QPushButton:hover { background-color: #fff4ec; }
            QPushButton:pressed { background-color: #ffe8d4; }
        """)
        burn_btn.clicked.connect(self.open_burn_in_dialog)
        burn_desc = QLabel("Select video file(s), quality and watermark options, then burn.")
        burn_desc.setFont(QFont("Arial", 12))
        burn_desc.setStyleSheet("color: #555;")
        burn_desc.setWordWrap(True)
        burn_row.addWidget(burn_btn)
        burn_row.addWidget(burn_desc, 1)
        process_layout.addLayout(burn_row)

        process_frame.setLayout(process_layout)
        layout.addWidget(process_frame)

        progress_group = QGroupBox("PROGRESS")
        progress_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 11px; }")
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(4)
        progress_layout.setContentsMargins(8, 12, 8, 8)

        progress_strip = QHBoxLayout()
        self.progress_operation_label = QLabel("Ready")
        self.progress_operation_label.setFont(QFont("Arial", 10, QFont.Bold))
        self.progress_operation_label.setMinimumWidth(100)
        progress_strip.addWidget(self.progress_operation_label)

        self.progress_file_label = QLabel("")
        self.progress_file_label.setFont(QFont("Arial", 9))
        self.progress_file_label.setStyleSheet("color: #666;")
        self.progress_file_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        progress_strip.addWidget(self.progress_file_label, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimumHeight(20)
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
        progress_strip.addWidget(self.progress_bar, 2)
        progress_strip.addWidget(self.progress_counter_label)

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
        progress_strip.addWidget(self.stop_btn)

        progress_layout.addLayout(progress_strip)
        progress_group.setLayout(progress_layout)
        progress_group.setVisible(False)
        layout.addWidget(progress_group)
        self.progress_group = progress_group

        log_group, self.log_output = self._make_log_panel(
            placeholder="Logs will appear here after processing starts"
        )
        layout.addWidget(log_group)

        return main_tab

    def build_main_tabs(self) -> QTabWidget:
        """Build main tab widget with all tabs."""
        self.main_tabs = QTabWidget()
        self.main_tabs.addTab(self.build_download_tab(), "Download")
        self.main_tabs.addTab(self.build_subtitles_tab(), "Subtitles")
        self.main_tabs.addTab(self.build_transcription_tab(), "Transcription")
        self.main_tabs.addTab(self.build_remux_tab(), "Remux")
        return self.main_tabs

    def init_ui(self):
        """Initialize the UI."""
        self.setWindowTitle(f"SP Workshop (WLW video processing, translation & subtitling hub) v{__version__}")
        self.setMinimumSize(900, 700)

        screen = QApplication.primaryScreen().availableGeometry()
        max_height = screen.height() - 50
        self.resize(900, max_height)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        self.build_header(main_layout)
        main_layout.addWidget(self.build_main_tabs())

        self.statusBar().showMessage("Ready")
        self.apply_lesbian_flag_styles()
        self.current_operation = None
    
    
    def log(self, message: str):
        """Add a message to both log outputs (global / settings messages)."""
        for widget in (self.log_output, self.download_log_output):
            widget.append(message)
            widget.verticalScrollBar().setValue(
                widget.verticalScrollBar().maximum()
            )

    def log_download(self, message: str):
        """Add a message to the Download tab log only."""
        self.download_log_output.append(message)
        self.download_log_output.verticalScrollBar().setValue(
            self.download_log_output.verticalScrollBar().maximum()
        )

    def log_subtitles(self, message: str):
        """Add a message to the Subtitles tab log only."""
        self.log_output.append(message)
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )

    def _log_route(self, message: str):
        """Route a log message to the appropriate tab based on current_operation."""
        download_ops = {"Downloading episodes"}
        subtitle_ops = {
            "Extracting subtitles", "Cleaning subtitles",
            "Translating subtitles", "Processing videos",
            "Remuxing videos", "Transcribing video", "Transcribing video (long)",
        }
        op = self.current_operation
        if op in download_ops:
            self.log_download(message)
        elif op in subtitle_ops:
            self.log_subtitles(message)
        else:
            self.log(message)
    
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
        """Open Whisper advanced options dialog, pre-selected to the current engine."""
        method = self.transcribe_method_combo.currentData()
        initial = "openai" if method in ("standard", "long") else "cpp"
        dialog = WhisperOptionsDialog(self, initial_method=initial)
        if dialog.exec_() == QDialog.Accepted:
            # Reload config after whisper options are saved
            self.config = load_config()
            self.log("Whisper options updated.")

    def _on_post_proc_toggled(self, checked: bool):
        self.config["whisper_post_processing_enabled"] = checked
        save_config(self.config)

    def open_post_processing_options(self):
        """Open the Whisper post-processing options dialog."""
        dlg = WhisperPostProcessingDialog(self, self.config)
        if dlg.exec_() == QDialog.Accepted:
            dlg.save_to_config()
            self.config = load_config()
    
    def run_script(self, script_func, *args, **kwargs):
        """Run a script in a worker thread."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Busy", "Another operation is already running.")
            return
        
        # Operation from func name
        # These are all the operations that can be run
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
            # enable stop button even tho it doesn't work half of the time
            self.stop_btn.setEnabled(True)
        
        self.statusBar().showMessage("Running...")
        
        self.worker = ScriptWorker(script_func, *args, **kwargs)
        self.worker.log_message.connect(self._log_route)
        self.worker.progress_update.connect(self.on_progress_update)
        self.worker.stream_progress.connect(self.on_download_stream_progress)
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
        } # = lesbian world domination
        
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
                # fallback progress
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
    
    def on_download_stream_progress(self, message: str):
        """Route download stream progress into the Download log only."""
        if message:
            self.log_download(f"  ↓  {message}")

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
        # Reset both stop buttons
        self.stop_btn.setEnabled(False)
        self.stop_btn.setText("Stop")
        self.transcribe_stop_btn.setEnabled(False)
        self.transcribe_stop_btn.setText("Stop")
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
            # Disable both stop buttons to prevent multiple clicks
            self.stop_btn.setEnabled(False)
            self.stop_btn.setText("Stopping...")
            self.transcribe_stop_btn.setEnabled(False)
            self.transcribe_stop_btn.setText("Stopping...")
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
            if self.transcribe_stop_btn.isVisible():
                self.on_transcribe_finished(False)
            else:
                self.on_script_finished(False)
        # Reset both stop buttons
        self.stop_btn.setEnabled(False)
        self.stop_btn.setText("Stop")
        self.transcribe_stop_btn.setEnabled(False)
        self.transcribe_stop_btn.setText("Stop")
    
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
            progress_callback=None, log_callback=None, stream_progress_callback=None,
        ):
            result = download_episodes(
                commands_text, output_dir,
                mode=mode, name=name, use_s01e=use_s01e, season=season, ep_spec=ep_spec,
                select_video=select_video,
                progress_callback=progress_callback,
                log_callback=log_callback,
                stream_progress_callback=stream_progress_callback,
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
        """Clean subtitles. Opens dialog to select fixes, then runs."""
        dlg = CleanSubtitlesDialog(self, self.config)
        if dlg.exec_() != QDialog.Accepted:
            return
        enabled_fixes = dlg.get_enabled_fixes()
        dlg.save_selection_to_config()
        self.config = load_config()
        
        subtitles_dir = get_subtitles_dir()
        self.log("Starting subtitle cleaning...")
        self.run_script(clean_subtitles, subtitles_dir, enabled_fixes)

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
                worker = PipInstallWorker(["gemini-srt-translator"], parent=dlg)
                worker.log_message.connect(lambda m: log.append(m))
                def on_finished(ok):
                    worker.wait()
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
    
    def open_burn_in_dialog(self):
        """Open the Burn-in subtitles configuration dialog."""
        dlg = BurnInDialog(self.config, parent=self)
        if dlg.exec_() != QDialog.Accepted:
            return
        if not dlg.selected_files:
            QMessageBox.warning(self, "No files", "Please add at least one video file.")
            return
        self.process_video(
            file_paths=dlg.selected_files,
            resolution=dlg.get_resolution(),
            use_watermarks=dlg.get_use_watermarks(),
            watermark_path_override=dlg.get_watermark_path(),
        )

    def process_video(self, file_paths: list, resolution: str,
                      use_watermarks: bool = None, watermark_path_override: str = None):
        """Process video files: burn subtitles, resize, optionally add watermark."""
        subtitles_dir = get_subtitles_dir()
        output_dir = get_output_dir()

        if use_watermarks is None:
            use_watermarks = self.config.get("use_watermarks", True)

        watermark_path = watermark_path_override if watermark_path_override is not None \
            else self.config.get(f"watermark_{resolution}p", "")

        if use_watermarks:
            if not watermark_path or not Path(watermark_path).exists():
                QMessageBox.warning(
                    self, "Error",
                    f"Watermark file for {resolution}p not found. Please set it in Settings or disable watermarks."
                )
                return

        use_iso639 = self.config.get("use_iso639_suffixes", False)
        target_language = self.config.get("translation_target_language", "English")

        self.log(f"Starting video processing ({resolution}p) for {len(file_paths)} file(s)...")
        if use_iso639:
            self.log(f"ISO 639 mode enabled - looking for .{ISO_639_CODES.get(target_language, 'eng')}.srt files")
        config = load_config()
        downloads_dir = get_downloads_dir()
        self.run_script(
            process_video, file_paths, subtitles_dir, output_dir,
            watermark_path, resolution, use_watermarks, config, use_iso639, target_language,
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
        model = self.transcribe_model_combo.currentData()
        
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
# Application entry point
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
