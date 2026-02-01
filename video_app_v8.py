#!/usr/bin/env python3
"""
Video Processing GUI Application
A PyQt5 desktop app that provides a button-based interface for all video processing scripts.
"""

import sys
import os
import json
from urllib.parse import urlparse
import re
import shlex
import subprocess
import shutil
import time
import traceback
import platform
import tempfile
from pathlib import Path
from typing import Optional, Dict, List


def quote_path(path: str) -> str:
    """Quote a path for shell commands in a cross-platform way.
    
    On Windows, shlex.quote() uses single quotes which CMD doesn't understand.
    This function uses double quotes on Windows and shlex.quote on Unix.
    """
    if platform.system() == "Windows":
        # Windows CMD uses double quotes; escape any existing double quotes
        escaped = str(path).replace('"', '\\"')
        return f'"{escaped}"'
    else:
        return shlex.quote(str(path))


def extract_cookies_from_har(har_file: Path) -> Optional[str]:
    """Extract cookies from a HAR file for use in requests.
    
    Returns a cookie string in the format "name1=value1; name2=value2" or None.
    Extracts from both request and response cookies, prioritizing request cookies.
    """
    if not har_file or not har_file.exists():
        return None
    
    try:
        with open(har_file, 'r', encoding='utf-8') as f:
            har_data = json.load(f)
        
        # Collect cookies from all requests and responses
        cookies = {}
        
        # First, try to get cookies from the browser's cookie store (if present in HAR)
        if 'log' in har_data and 'pages' in har_data['log']:
            for page in har_data['log'].get('pages', []):
                # Some HAR files store cookies at page level
                pass
        
        # Get cookies from all entries (generic - no domain filter)
        for entry in har_data.get('log', {}).get('entries', []):
            # Get cookies from request headers (Cookie header)
            request = entry.get('request', {})
            for header in request.get('headers', []):
                if header.get('name', '').lower() == 'cookie':
                    # Parse Cookie header: "name1=value1; name2=value2"
                    cookie_header = header.get('value', '')
                    for cookie_pair in cookie_header.split(';'):
                        cookie_pair = cookie_pair.strip()
                        if '=' in cookie_pair:
                            name, value = cookie_pair.split('=', 1)
                            name = name.strip()
                            value = value.strip()
                            if name:
                                cookies[name] = value
            
            # Get cookies from request.cookies array
            for cookie in request.get('cookies', []):
                name = cookie.get('name', '')
                value = cookie.get('value', '')
                if name:
                    cookies[name] = value
            
            # Get cookies from response (Set-Cookie headers)
            response = entry.get('response', {})
            for header in response.get('headers', []):
                if header.get('name', '').lower() == 'set-cookie':
                    # Parse Set-Cookie header: "name=value; path=/; domain=..."
                    cookie_value = header.get('value', '')
                    if '=' in cookie_value:
                        cookie_name = cookie_value.split('=')[0].strip()
                        cookie_val = cookie_value.split('=')[1].split(';')[0].strip()
                        if cookie_name:
                            cookies[cookie_name] = cookie_val
        
        if cookies:
            cookie_string = '; '.join(f"{name}={value}" for name, value in sorted(cookies.items()))
            return cookie_string
    except Exception as e:
        # Log error for debugging
        import traceback
        print(f"Error extracting cookies from HAR: {e}")
        traceback.print_exc()
    
    return None


def get_temp_dir() -> str:
    """Get a cross-platform temporary directory path."""
    return tempfile.gettempdir()


from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QFileDialog, QDialog,
    QLineEdit, QFormLayout, QMessageBox, QProgressBar, QGroupBox, QStyleFactory, QCheckBox, QStackedWidget, QTextBrowser, QComboBox,
    QGraphicsDropShadowEffect, QTabWidget, QSpinBox, QDoubleSpinBox, QScrollArea, QTimeEdit, QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QProcess, QUrl, QTime, QTimer
from PyQt5.QtGui import QFont, QIcon, QPainter, QPen, QDesktopServices


# URL for download instructions (rentry.co page - update when creating the page)
DOWNLOAD_INSTRUCTIONS_URL = "https://rentry.co/sp-workshop"

# ============================================================================
# Custom Widgets
# ============================================================================

class OutlinedLabel(QLabel):
    """QLabel with text outline effect."""
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Get text metrics
        font = self.font()
        painter.setFont(font)
        text = self.text()
        
        # Draw black outline by drawing text multiple times with offsets
        pen = QPen(Qt.black, 2, Qt.SolidLine)
        painter.setPen(pen)
        
        # Draw outline in all directions
        offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
        for dx, dy in offsets:
            painter.drawText(self.rect().adjusted(dx, dy, dx, dy), Qt.AlignCenter, text)
        
        # Draw white text on top
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
        "download_resolution": "1080",
        "ffmpeg_preset": "medium",
        "setup_complete": False,
        "use_watermarks": True,
        "whisper_output_format": "srt",
        "whisper_options": {
            "extra_args": "",
            "extra_args_parsed": ""
        }
    }
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
                # Merge whisper_options separately to ensure all defaults exist
                if "whisper_options" in user_config:
                    default_config["whisper_options"].update(user_config["whisper_options"])
                    del user_config["whisper_options"]
                default_config.update(user_config)
        except Exception as e:
            print(f"Error loading config: {e}")
    
    return default_config


def save_config(config: Dict):
    """Save configuration to JSON file."""
    config_path = get_config_path()
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"Error saving config: {e}")


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


def get_app_icon() -> QIcon:
    """Load application icon, preferring .icns on macOS, with fallback to PNG and default.
    
    Note: For best results on macOS, use a PNG with transparent background (alpha channel)
    and convert it to .icns using the create_icon.sh script. The icon should be at least
    1024x1024 pixels for best quality.
    """
    script_dir = Path(__file__).parent
    
    # On macOS, prefer .icns format for better integration
    # Use absolute path to ensure macOS can find it properly
    if sys.platform == "darwin":
        icns_path = script_dir / "icon.icns"
        if icns_path.exists():
            icon = QIcon(str(icns_path.absolute()))
            # Ensure icon is valid and has sizes
            if not icon.isNull():
                return icon
    
    # Fallback to PNG (works on all platforms)
    # Try transparent version first if it exists
    transparent_png = script_dir / "icon_transparent.png"
    if transparent_png.exists():
        return QIcon(str(transparent_png.absolute()))
    
    png_path = script_dir / "icon.png"
    if png_path.exists():
        return QIcon(str(png_path.absolute()))
    
    # Fallback to default PyQt5 icon
    return QIcon()


def get_remuxed_dir() -> Path:
    """Get the remuxed directory."""
    remuxed_dir = get_base_dir() / "remuxed"
    remuxed_dir.mkdir(parents=True, exist_ok=True)
    return remuxed_dir


def check_whisper_model_exists(model_name: str) -> bool:
    """Check if a Whisper model already exists in the default cache location.
    
    Args:
        model_name: The model name (e.g., "tiny", "base", "small", "medium", "large", "turbo")
    
    Returns:
        True if the model file exists, False otherwise
    """
    system = platform.system()
    
    # Whisper stores models in ~/.cache/whisper/ on Unix/macOS
    # and %USERPROFILE%\.cache\whisper\ on Windows
    if system == "Windows":
        cache_dir = Path.home() / ".cache" / "whisper"
    else:  # macOS, Linux, etc.
        cache_dir = Path.home() / ".cache" / "whisper"
    
    # Model file name mappings (Whisper uses these exact names)
    model_files = {
        "tiny": "tiny.pt",
        "base": "base.pt",
        "small": "small.pt",
        "medium": "medium.pt",
        "large": "large-v2.pt",  # Note: Whisper uses "large-v2" filename
        "turbo": "turbo.pt"
    }
    
    model_file = model_files.get(model_name.lower())
    if not model_file:
        return False
    
    model_path = cache_dir / model_file
    return model_path.exists()


# ============================================================================
# Video Analysis Functions
# ============================================================================

def get_video_duration(video_path: Path) -> Optional[float]:
    """Get video duration in minutes using ffprobe."""
    try:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
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
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
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
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "a:0",
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
        # Remove any whitespace
        time_str = time_str.strip()
        
        # Split by colon
        parts = time_str.split(':')
        
        if len(parts) == 3:
            # Format: HH:MM:SS.ms
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:
            # Format: MM:SS.ms
            minutes = float(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        else:
            # Try parsing as just seconds
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
    
    # Remove ANSI escape codes (colors, cursor movement, etc.)
    # Pattern matches: \033[...m, \033[F, \033[K, etc.
    line = re.sub(r'\033\[[0-9;]*[a-zA-Z]', '', line)
    
    # Remove common cursor movement sequences
    line = line.replace('\033[F', '').replace('\033[K', '')
    
    # Skip lines that are just cursor movement codes
    if not line.strip():
        return None
    
    # IMPORTANT: Always preserve error/warning messages - check before filtering
    is_error = any(keyword in line.lower() for keyword in [
        'error', 'failed', 'exception', 'warning', 'warn', 'fail', 
        '✗', '⚠', '❌', 'critical', 'fatal', 'unable', 'cannot',
        'not found', 'missing', 'invalid', 'denied', 'timeout'
    ])
    
    # If it's an error, return it immediately (cleaned but preserved)
    if is_error:
        return f"    ⚠ {line.strip()}"
    
    # Skip repeated "Validating token size..." messages
    if "Validating token size..." in line:
        return None
    
    # Skip "Token size validated. Translating..." (redundant)
    if "Token size validated. Translating..." in line:
        return None
    
    # Skip "Starting with API Key" messages (not useful)
    if "Starting with" in line and "API Key" in line:
        return None
    
    # Handle "Starting translation of X lines..." - keep this but clean it
    if "Starting translation of" in line and "lines..." in line:
        match = re.search(r'Starting translation of (\d+) lines', line)
        if match:
            return f"    Starting translation of {match.group(1)} lines..."
    
    # Clean up progress lines - extract just the useful info
    if "Translating:" in line and "|" in line:
        # Extract progress bar, percentage, and status
        # Format: Translating: |██████░░░░░░| 50% (10/20) model | Status
        match = re.search(r'Translating:.*?(\d+)% \((\d+)/(\d+)\)', line)
        if match:
            percent = match.group(1)
            current = match.group(2)
            total = match.group(3)
            
            # Extract status if present (after the last |)
            status_parts = line.split('|')
            status = ""
            if len(status_parts) > 1:
                # Get the last part after |
                last_part = status_parts[-1].strip()
                # Remove model name if present
                last_part = re.sub(r'gemini-[^\s]+', '', last_part).strip()
                if last_part and last_part not in ['Thinking', 'Processing', 'Sending batch']:
                    status = last_part
                elif last_part in ['Thinking', 'Processing']:
                    # Extract spinner character if present
                    spinner_match = re.search(r'(Thinking|Processing)\s*([—\\|/])', line)
                    if spinner_match:
                        status = f"{spinner_match.group(1)}..."
                    else:
                        status = f"{last_part}..."
            
            # Build clean progress line
            if status:
                return f"    Progress: {percent}% ({current}/{total} lines) - {status}"
            else:
                return f"    Progress: {percent}% ({current}/{total} lines)"
    
    # Clean up success messages
    if "✅" in line or "Translation completed successfully" in line:
        return "    ✓ Translation completed successfully!"
    
    # Return cleaned line for other messages
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
            # macOS: use 'open -a' for .app bundles
            subprocess.run(["open", "-a", str(lossless_cut), *path_strings])
        elif system == "Windows":
            # Windows: run the executable directly with the files as arguments
            subprocess.Popen([str(lossless_cut), *path_strings])
        else:
            # Linux: run the executable directly
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
# ISO 639-2/T Language Codes for Subtitle Suffixes
# ============================================================================

ISO_639_CODES = {
    "English": "eng",
    "French": "fra",
    "Spanish": "spa",
    "Catalan": "cat",
    "German": "deu",
    "Italian": "ita",
    "Portuguese": "por",
    "Dutch": "nld",
    "Chinese": "zho",
    "Japanese": "jpn",
    "Korean": "kor",
    "Arabic": "ara",
    "Thai": "tha",
    "Greek": "ell",
}


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


def _add_headers_for_bare_url(url_or_cmd: str) -> str:
    """Add Referer/Origin headers for bare URLs. Many CDNs require these to avoid 403."""
    # Derive Referer/Origin from URL domain (internal mapping, not user-facing)
    url = url_or_cmd.strip().strip('"')
    if not url.startswith('http'):
        return url_or_cmd
    url_lower = url.lower()
    if 'globo.com' in url_lower or 'globoplay' in url_lower:
        referer, origin = "https://globoplay.globo.com/", "https://globoplay.globo.com"
    elif 'tf1.fr' in url_lower:
        referer, origin = "https://www.tf1.fr/", "https://www.tf1.fr"
    else:
        # Generic: use URL's origin (scheme + host)
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
    # Always quote URL to handle &, =, etc. in query params
    return f"{' '.join(headers)} \"{url}\""


# ============================================================================
# Script Wrappers
# ============================================================================

def download_episodes(commands_text: str, output_dir: Path, episode_spec: str = "1", 
                      progress_callback=None, log_callback=None) -> bool:
    """Download episodes using commands from text.
    
    User pastes full N_m3u8DL-RE commands per instructions. App adds save options only.
    
    Args:
        commands_text: Raw N_m3u8DL-RE commands, one per line
        output_dir: Directory to save downloaded files
        episode_spec: Episode specification (e.g., "1", "1-5", "1,3,5-7")
        progress_callback: Callback for progress updates
        log_callback: Callback for log messages
    """
    if not commands_text.strip():
        if log_callback:
            log_callback("Error: No commands provided.")
        return False
    
    # Filter out HAR file lines (starting with @) and empty lines
    lines = []
    for line in commands_text.strip().split('\n'):
        line = line.strip()
        # Skip empty lines, comments, and HAR file references
        if line and not line.startswith('#') and not line.startswith('@'):
            lines.append(line)
    
    if not lines:
        if log_callback:
            log_callback("No commands found.")
        return False
    
    # Parse episode specification
    episode_numbers = parse_episode_range(episode_spec)
    if not episode_numbers:
        episode_numbers = list(range(1, len(lines) + 1))  # Default to 1, 2, 3, ...
    
    # If fewer episode numbers than commands, extend sequentially
    if len(episode_numbers) < len(lines):
        last_num = episode_numbers[-1]
        episode_numbers.extend(range(last_num + 1, last_num + 1 + (len(lines) - len(episode_numbers))))
    
    downloaded_files = []
    total = len(lines)
    if log_callback:
        log_callback(f"Starting batch download for {total} episodes...")
        if episode_numbers:
            log_callback(f"Episode numbers: {', '.join(map(str, episode_numbers[:10]))}{' ...' if len(episode_numbers) > 10 else ''}")
    
    for i, base_command in enumerate(lines):
        episode_number = episode_numbers[i] if i < len(episode_numbers) else (episode_numbers[-1] + i - len(episode_numbers) + 1)
        
        # Skip empty lines or comments
        if not base_command or base_command.startswith('#'):
            continue
        
        # Strip "N_m3u8DL-RE" prefix if present (user might paste full command)
        if base_command.lower().startswith('n_m3u8dl-re '):
            base_command = base_command[12:].strip()
        
        # If line looks like a bare URL (no -H, no --key), add headers many CDNs require
        if ' -H ' not in base_command and ' --key ' not in base_command and base_command.lstrip('"').startswith('http'):
            base_command = _add_headers_for_bare_url(base_command)
            if log_callback:
                log_callback("  (Bare URL detected – added Referer/Origin headers)")
        
        if progress_callback:
            progress_callback(i + 1, total, f"Episode {episode_number}")
        
        # Use user command as-is; append only save/output options
        command = (
            f"N_m3u8DL-RE "
            f"{base_command} "
            f"--tmp-dir {quote_path(get_temp_dir())} "
            f"--del-after-done "
            f"--check-segments-count False "
            f"--save-name {quote_path(str(episode_number))} "
            f"--save-dir {quote_path(str(output_dir))} "
            f"--select-video best "
            f"--select-audio all "
            f"--select-subtitle all "
            f"-M mkv"
        )
        
        if log_callback:
            log_callback(f"\n--- Task {i + 1}/{total}: Episode {episode_number} ---")
            log_callback(f"Running: {base_command[:80]}...")
        
        # Use Popen to stream output in real-time
        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr into stdout
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Stream output line by line
            output_lines = []
            last_logged_percent = -5  # Track last logged percentage to avoid spam
            
            while True:
                line_output = process.stdout.readline()
                if not line_output:
                    break
                
                line_output = line_output.strip()
                if line_output:
                    output_lines.append(line_output)
                    
                    # Filter out progress bar spam (lines with ━ characters)
                    is_progress_bar = '━' in line_output
                    
                    # Filter out file access warnings (normal concurrent download noise)
                    is_file_access_warning = 'The process cannot access the file' in line_output
                    
                    # Only log important messages
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
                    
                    # Progress logging suppressed to avoid spam from multiple streams
                    # (video, audio, subtitle each report 0-100% separately)
            
            # Wait for process to complete
            returncode = process.wait()
            
            if returncode == 0:
                candidates = list(output_dir.glob(f"{episode_number}.*"))
                if candidates:
                    downloaded_files.append(candidates[0])
                    if log_callback:
                        log_callback(f"  ✓ Downloaded: {candidates[0].name}")
                else:
                    if log_callback:
                        log_callback(f"  ⚠ Warning: No output file found for episode {episode_number}")
            else:
                if log_callback:
                    log_callback(f"  ✗ Error downloading episode {episode_number} (exit code: {returncode})")
                    # Show last few lines of output for debugging
                    if output_lines:
                        log_callback(f"    Last output lines:")
                        for err_line in output_lines[-5:]:
                            log_callback(f"      {err_line}")
        
        except Exception as e:
            if log_callback:
                log_callback(f"  ✗ Exception while downloading episode {episode_number}: {e}")
                log_callback(f"    Traceback: {traceback.format_exc()}")
    
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
        
        cmd = [
            "ffmpeg", "-y", "-i", str(mkv_file),
            "-map", "0:s:0", str(srt_file)
        ]
        
        # Stream FFmpeg output in real-time
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Read stderr line by line (FFmpeg outputs progress to stderr)
            error_lines = []
            while True:
                line = process.stderr.readline()
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                error_lines.append(line)
                
                # Log progress information
                if "Stream #" in line or "Subtitle:" in line:
                    if log_callback:
                        log_callback(f"    {line}")
                elif "Error" in line or "error" in line.lower():
                    if log_callback:
                        log_callback(f"    ⚠ {line}")
            
            # Wait for process to complete
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
            # Get file size for logging
            file_size = srt_file.stat().st_size
            file_size_kb = file_size / 1024
            
            with open(srt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_length = len(content)
            
            # Remove color tags like <c.yellow>, <c.red>, etc.
            cleaned = re.sub(r'<c\.[a-zA-Z]+>', '', content)
            cleaned = re.sub(r'</c\.[a-zA-Z]+>', '', cleaned)
            
            if cleaned != content:
                tags_removed = len(re.findall(r'<c\.[a-zA-Z]+>|</c\.[a-zA-Z]+>', content))
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


def translate_subtitles(selected_srt_files: List[Path], api_key: Optional[str] = None, 
                       target_language: str = "English", use_iso639: bool = False,
                       api_key2: Optional[str] = None,
                       progress_callback=None, log_callback=None) -> bool:
    """Translate selected subtitle files using gemini-srt-translator.
    
    Args:
        selected_srt_files: List of SRT files to translate
        api_key: Optional API key (uses env var if available)
        target_language: Target language for translation (default: English)
        use_iso639: Whether to add ISO 639 language suffix to output filename
        api_key2: Optional second API key for translation
        progress_callback: Callback for progress updates
        log_callback: Callback for log messages
    """
    # Check for API key in environment variables first (most secure)
    env_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GST_API_KEY")
    
    # Use environment variable if available, otherwise fall back to provided api_key
    final_api_key = env_api_key or api_key
    
    if not final_api_key:
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
            # Rename original (in same directory as the SRT file)
            # Check if the file has an ISO 639 language suffix (e.g., .spa in subtitle.spa.srt)
            iso_match = re.match(r'(.+)\.([a-z]{3})$', srt_file.stem)
            if iso_match:
                # File has ISO suffix: subtitle.spa.srt → subtitle_OG.srt
                base_name = iso_match.group(1)
                og_file = srt_file.parent / f"{base_name}_OG.srt"
            else:
                # No ISO suffix: subtitle.srt → subtitle_OG.srt
                og_file = srt_file.parent / f"{srt_file.stem}_OG.srt"
            
            if not og_file.exists():
                srt_file.rename(og_file)
            
            if log_callback:
                log_callback(f"Translating: {srt_file.name}")
            
            # Find gst command
            gst_cmd = find_gst_command()
            if not gst_cmd:
                if log_callback:
                    log_callback(f"  ✗ Failed: {srt_file.name}")
                    log_callback(f"    Error: gst command not found. Make sure gemini-srt-translator is installed.")
                continue
            
            # Build command - NEVER use -k flag, always set environment variable
            # (gst will automatically use GEMINI_API_KEY or GST_API_KEY if set)
            base_cmd = ["translate", "-i", str(og_file), "-l", target_language, "-o", str(srt_file), "--skip-upgrade"]
            
            # Add second API key if provided
            if api_key2:
                base_cmd.extend(["-k2", api_key2])
            
            # Handle Python module format (e.g., "python3 -m gemini_srt_translator")
            if " -m " in gst_cmd:
                cmd_parts = gst_cmd.split() + base_cmd
            else:
                cmd_parts = [gst_cmd] + base_cmd
            
            # Prepare environment with API key set
            # Copy current environment and add/override API key
            env = os.environ.copy()
            if final_api_key:
                # Set GEMINI_API_KEY in the subprocess environment
                env["GEMINI_API_KEY"] = final_api_key
            
            # Use Popen to stream output in real-time
            process = subprocess.Popen(
                cmd_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr into stdout
                stdin=subprocess.DEVNULL,  # Close stdin to prevent hanging on prompts
                text=True,
                bufsize=1,
                universal_newlines=True,
                env=env  # Pass environment with API key
            )
            
            # Stream output line by line with cleaning
            output_lines = []
            last_progress_line = None
            while True:
                line_output = process.stdout.readline()
                if not line_output:
                    break
                
                # Clean the line
                cleaned_line = clean_log_line(line_output)
                
                if cleaned_line:
                    output_lines.append(line_output.strip())  # Keep original for error reporting
                    
                    # Only log if it's different from the last progress line (avoid duplicates)
                    if cleaned_line != last_progress_line:
                        if log_callback:
                            log_callback(cleaned_line)
                        last_progress_line = cleaned_line
            
            # Wait for process to complete
            returncode = process.wait()
            
            # Clean up .progress files in the subtitle directory
            progress_files = list(srt_file.parent.glob("*.progress"))
            for progress_file in progress_files:
                try:
                    progress_file.unlink()
                    if log_callback:
                        log_callback(f"    Cleaned up: {progress_file.name}")
                except Exception as e:
                    if log_callback:
                        log_callback(f"    Warning: Could not remove {progress_file.name}: {e}")
            
            # Verify translation completion
            translation_success = False
            if returncode == 0 and srt_file.exists():
                # Check if file has content (not empty)
                try:
                    file_size = srt_file.stat().st_size
                    if file_size > 0:
                        # Read a bit of the file to verify it's valid SRT content
                        with open(srt_file, 'r', encoding='utf-8') as f:
                            content_preview = f.read(100)
                            if content_preview.strip():
                                translation_success = True
                except Exception:
                    pass
            
            if translation_success:
                # Add ISO 639 language suffix if enabled
                final_srt_file = srt_file
                if use_iso639:
                    target_code = ISO_639_CODES.get(target_language, "eng")
                    
                    # Check if source filename has existing language suffix to replace
                    source_match = re.match(r'(.+)\.([a-z]{3})$', srt_file.stem)
                    if source_match:
                        # Replace existing suffix: video.spa → video.eng
                        base_name = source_match.group(1)
                    else:
                        # No existing suffix: video → video
                        base_name = srt_file.stem
                    
                    final_srt_file = srt_file.parent / f"{base_name}.{target_code}.srt"
                    
                    # Rename the translated file to include language suffix
                    if srt_file != final_srt_file:
                        srt_file.rename(final_srt_file)
                        if log_callback:
                            log_callback(f"    Renamed to: {final_srt_file.name}")
                
                success_count += 1
                if log_callback:
                    log_callback(f"  ✓ Translated: {final_srt_file.name}")
            else:
                if log_callback:
                    log_callback(f"  ✗ Failed: {srt_file.name}")
                    if returncode != 0:
                        log_callback(f"    Exit code: {returncode}")
                    if output_lines:
                        log_callback(f"    Last output lines:")
                        for err_line in output_lines[-5:]:
                            log_callback(f"      {err_line}")
        except Exception as e:
            if log_callback:
                log_callback(f"Error translating {srt_file.name}: {e}")
    
    if log_callback:
        log_callback(f"\nTranslation complete. Translated {success_count}/{total} files.")
    
    return success_count > 0


def process_video(selected_video_files: List[Path], subtitles_dir: Path, output_dir: Path,
                 watermark_path: str, resolution: str, use_watermarks: bool = True,
                 use_iso639: bool = False, target_language: str = "English",
                 progress_callback=None, log_callback=None) -> bool:
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
        
        # Check for subtitle file in multiple locations
        # Try different filename patterns based on ISO 639 settings
        srt_file = None
        srt_location = None
        
        # Build list of filenames to try (in priority order)
        filenames_to_try = [f"{base}.srt"]  # Always try exact match first
        
        if use_iso639:
            # Also try with ISO 639 suffix for target language
            target_code = ISO_639_CODES.get(target_language, "eng")
            filenames_to_try.append(f"{base}.{target_code}.srt")
        
        # Check each location for each filename pattern
        for filename in filenames_to_try:
            # 1. Same directory as video file (preferred)
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
                for checked in checked_files:
                    log_callback(checked)
            continue
        
        if log_callback:
            log_callback(f"Processing: {video_file.name} ({resolution}p)")
            log_callback(f"  Subtitle: {srt_file.name} (found in {srt_location})")
            log_callback(f"  Output: {out_file.name}")
            if use_watermarks:
                log_callback(f"  Watermark: {Path(watermark_path).name}")
        
        # Get video duration for percentage/ETA calculation
        video_duration_seconds = get_video_duration_seconds(video_file)
        
        # Check audio channels and prepare audio filter if needed
        audio_channels = get_audio_channels(video_file)
        audio_filter = None
        if audio_channels and audio_channels > 2:
            if log_callback:
                log_callback(f"  Audio: {audio_channels} channels detected, converting to stereo (2.0) for higher compatibility")
            # For 5.1 (6 channels): downmix to stereo
            # Channel mapping: FL=0, FR=1, FC=2, LFE=3, BL=4, BR=5
            # Stereo output: mix center + front L/R + rear L/R
            if audio_channels == 6:
                # 5.1 to stereo: mix center channel with front and rear channels
                audio_filter = "pan=stereo|c0=0.5*c2+0.5*c0+0.3*c4|c1=0.5*c2+0.5*c1+0.3*c5"
            elif audio_channels >= 4:
                # 4+ channels: simple downmix
                audio_filter = "pan=stereo|c0=0.5*c0+0.5*c2|c1=0.5*c1+0.5*c3"
            else:
                # 3 channels: mix to stereo
                audio_filter = "pan=stereo|c0=0.5*c0+0.5*c2|c1=0.5*c1+0.5*c2"
        
        # Build FFmpeg filter
        if use_watermarks:
            if resolution == "720":
                filter_complex = (
                    f"[0:v]subtitles='{srt_file}':force_style='FontName=Arial,Bold=1',"
                    f"scale=-2:{height}[scaled];"
                    f"[1:v]format=rgba,colorchannelmixer=aa=0.8[wm];"
                    f"[scaled][wm]overlay=W-w-10:H-h-10"
                )
            else:  # 1080p
                filter_complex = (
                    f"[0:v]subtitles='{srt_file}':force_style='FontName=Arial,Bold=1',"
                    f"scale=-1:{height}[vsub];"
                    f"[1:v]format=rgba,colorchannelmixer=aa=0.8[wm];"
                    f"[vsub][wm]overlay=0:0[outv]"
                )
            cmd = [
                "ffmpeg", "-y",
                "-err_detect", "ignore_err",  # Ignore non-critical decoder errors
                "-fflags", "+discardcorrupt+genpts",  # Discard corrupt packets and generate PTS
                "-max_error_rate", "1.0",  # Allow up to 100% error rate (essentially ignore all errors)
                "-i", str(video_file),
                "-i", watermark_path,
                "-filter_complex", filter_complex,
                "-c:v", "libx264", "-preset", preset, "-crf", "20",
            ]
            # Add audio filter if needed for downmixing
            if audio_filter:
                cmd.extend(["-af", audio_filter])
            cmd.extend(["-c:a", "aac", "-b:a", "128k", str(out_file)])
        else:
            # No watermark - just subtitles and resize
            filter_complex = (
                f"[0:v]subtitles='{srt_file}':force_style='FontName=Arial,Bold=1',"
                f"scale=-2:{height}" if resolution == "720" else f"scale=-1:{height}"
            )
            cmd = [
                "ffmpeg", "-y",
                "-err_detect", "ignore_err",  # Ignore non-critical decoder errors
                "-fflags", "+discardcorrupt+genpts",  # Discard corrupt packets and generate PTS
                "-max_error_rate", "1.0",  # Allow up to 100% error rate (essentially ignore all errors)
                "-i", str(video_file),
                "-vf", filter_complex,
                "-c:v", "libx264", "-preset", preset, "-crf", "20",
            ]
            # Add audio filter if needed for downmixing
            if audio_filter:
                cmd.extend(["-af", audio_filter])
            cmd.extend(["-c:a", "aac", "-b:a", "128k", str(out_file)])
        
        # Log the exact command being executed for debugging
        if log_callback:
            log_callback(f"  Running: {' '.join(cmd[:3])} ... [filter] ... {cmd[-1]}")
        
        # Stream FFmpeg output in real-time
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Read stderr line by line (FFmpeg outputs progress to stderr)
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
            
            # Wait for process to complete
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
        # Try mkvmerge first (best for MKV files)
        if video_path.suffix.lower() == '.mkv':
            try:
                cmd = ['mkvmerge', '--identify-verbose', str(video_path)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    current_track = None
                    track_info = {}
                    
                    for line in result.stdout.split('\n'):
                        line = line.strip()
                        if line.startswith('Track ID'):
                            if current_track and track_info:
                                track_type = track_info.get('type', '').lower()
                                if 'video' in track_type:
                                    tracks['video'].append(track_info)
                                elif 'audio' in track_type:
                                    tracks['audio'].append(track_info)
                                elif 'subtitles' in track_type or 'subtitle' in track_type:
                                    tracks['subtitles'].append(track_info)
                            
                            # New track
                            track_id_match = re.search(r'(\d+):', line)
                            if track_id_match:
                                current_track = int(track_id_match.group(1))
                                track_info = {'track_id': current_track}
                        
                        elif current_track is not None:
                            if ':' in line:
                                key, value = line.split(':', 1)
                                key = key.strip().lower().replace(' ', '_')
                                value = value.strip()
                                
                                if key == 'type':
                                    track_info['type'] = value
                                elif key == 'codec':
                                    track_info['codec'] = value
                                elif key == 'channels':
                                    try:
                                        track_info['channels'] = int(value)
                                    except ValueError:
                                        pass
                                elif key == 'sample_rate':
                                    track_info['sample_rate'] = value
                                elif key == 'language':
                                    track_info['language'] = value
                                elif 'video' in key and 'pixel_dimensions' in key:
                                    track_info['resolution'] = value
                    
                    # Add last track
                    if current_track and track_info:
                        track_type = track_info.get('type', '').lower()
                        if 'video' in track_type:
                            tracks['video'].append(track_info)
                        elif 'audio' in track_type:
                            tracks['audio'].append(track_info)
                        elif 'subtitles' in track_type or 'subtitle' in track_type:
                            tracks['subtitles'].append(track_info)
                    
                    return tracks
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # Fall back to ffprobe
                pass
        
        # Use ffprobe (works for all formats)
        cmd = [
            'ffprobe', '-v', 'quiet', '-print_format', 'json',
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
        cmd = [
            "ffmpeg", "-y",
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


def transcribe_video(video_path: Path, language_code: str, model: str, whisper_options: Dict = None, output_format: str = "srt", progress_callback=None, log_callback=None) -> bool:
    """Transcribe video using whisper_auto.sh script."""
    if not video_path.exists():
        if log_callback:
            log_callback(f"Error: Video file not found: {video_path}")
        return False
    
    script_path = Path(__file__).parent / "whisper_auto.sh"
    
    if not script_path.exists():
        if log_callback:
            log_callback(f"Error: whisper_auto.sh not found at {script_path}")
        return False
    
    try:
        if log_callback:
            log_callback(f"Starting transcription of: {video_path.name}")
            log_callback(f"Language: {language_code}, Model: {model}, Format: {output_format}")
        
        # Prepare environment variables - pass user-typed extra arguments if provided
        env = os.environ.copy()
        if whisper_options and "extra_args_parsed" in whisper_options:
            extra_args = whisper_options.get("extra_args_parsed", "")
            if extra_args:
                env["WHISPER_EXTRA_ARGS"] = extra_args
        
        # Run the script with video path, language code, model, and output format as arguments
        result = subprocess.run(
            ["bash", str(script_path), str(video_path), language_code, model, output_format],
            capture_output=True,
            text=True,
            env=env
        )
        
        # Log output
        if log_callback:
            if result.stdout:
                log_callback(result.stdout)
            if result.stderr:
                log_callback(result.stderr)
        
        if result.returncode == 0:
            # Check if SRT file was created (matches input video filename)
            video_dir = video_path.parent
            base_name = video_path.stem
            # Check for exact match first, then numbered variants
            srt_file = video_dir / f"{base_name}.srt"
            if not srt_file.exists():
                # Check for numbered variants (e.g., video_1.srt, video_2.srt)
                n = 1
                while n <= 10:  # Reasonable limit
                    candidate = video_dir / f"{base_name}_{n}.srt"
                    if candidate.exists():
                        srt_file = candidate
                        break
                    n += 1
            
            if srt_file.exists():
                if log_callback:
                    log_callback(f"✓ Transcription complete: {srt_file.name}")
                return True
            else:
                if log_callback:
                    log_callback("Transcription completed but SRT file not found.")
                return False
        else:
            if log_callback:
                log_callback(f"Transcription failed with exit code {result.returncode}")
            return False
    except Exception as e:
        if log_callback:
            log_callback(f"Error during transcription: {e}")
        return False


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


def transcribe_video_time_range(
    video_path: Path, 
    start_seconds: int, 
    end_seconds: int,
    language_code: str,
    model: str,
    whisper_options: Dict = None,
    output_format: str = "srt",
    adjust_timestamps: bool = True,
    progress_callback=None, 
    log_callback=None
) -> bool:
    """Transcribe a specific time range of a video using FFmpeg + Whisper.
    
    Args:
        video_path: Path to the video file
        start_seconds: Start time in seconds
        end_seconds: End time in seconds
        language_code: Language code for transcription
        model: Whisper model to use
        whisper_options: Dictionary of whisper options
        output_format: Whisper output format (srt, vtt, txt, tsv, json, all)
        adjust_timestamps: If True, adjust SRT timestamps to match original video
        progress_callback: Callback for progress updates
        log_callback: Callback for logging
    
    Returns:
        True if successful, False otherwise
    """
    if not video_path.exists():
        if log_callback:
            log_callback(f"Error: Video file not found: {video_path}")
        return False
    
    try:
        duration = end_seconds - start_seconds
        
        if log_callback:
            log_callback(f"Extracting time range: {start_seconds}s to {end_seconds}s ({duration}s duration)")
        
        # Create temporary audio file for the time range
        video_dir = video_path.parent
        temp_audio = video_dir / f"{video_path.stem}_temp_range.wav"
        
        # Convert seconds to HH:MM:SS format for FFmpeg
        def seconds_to_hhmmss(seconds):
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        
        start_str = seconds_to_hhmmss(start_seconds)
        end_str = seconds_to_hhmmss(end_seconds)
        
        # Extract audio segment with FFmpeg
        if log_callback:
            log_callback("Extracting audio segment...")
        
        ffmpeg_cmd = [
            "ffmpeg", "-ss", start_str, "-to", end_str, "-i", str(video_path),
            "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
            "-af", "dynaudnorm", str(temp_audio),
            "-loglevel", "warning", "-hide_banner", "-y"
        ]
        
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            if log_callback:
                log_callback(f"FFmpeg error: {result.stderr}")
            return False
        
        if not temp_audio.exists():
            if log_callback:
                log_callback("Error: Temporary audio file was not created")
            return False
        
        # Transcribe the audio segment using whisper
        if log_callback:
            log_callback("Transcribing audio segment with Whisper...")
        
        # Get the whisper_auto.sh script path
        script_path = Path(__file__).parent / "whisper_auto.sh"
        
        if not script_path.exists():
            if log_callback:
                log_callback(f"Error: whisper_auto.sh not found at {script_path}")
            # Clean up temp file
            if temp_audio.exists():
                temp_audio.unlink()
            return False
        
        # Prepare environment variables - pass user-typed extra arguments if provided
        env = os.environ.copy()
        if whisper_options and "extra_args_parsed" in whisper_options:
            extra_args = whisper_options.get("extra_args_parsed", "")
            if extra_args:
                env["WHISPER_EXTRA_ARGS"] = extra_args
        
        # Use whisper_auto.sh script (same as regular transcription)
        result = subprocess.run(
            ["bash", str(script_path), str(temp_audio), language_code, model, output_format],
            capture_output=True,
            text=True,
            env=env
        )
        
        if log_callback and result.stdout:
            log_callback(result.stdout)
        if log_callback and result.stderr:
            log_callback(result.stderr)
        
        # Find the generated SRT file
        temp_srt = video_dir / f"{temp_audio.stem}.srt"
        final_srt = video_dir / f"{video_path.stem}_range_{start_seconds}_{end_seconds}.srt"
        
        if temp_srt.exists():
            # Adjust timestamps if requested
            if adjust_timestamps:
                if log_callback:
                    log_callback(f"Adjusting timestamps by +{start_seconds}s...")
                adjust_srt_timestamps(temp_srt, start_seconds)
            
            # Rename to final name
            if final_srt.exists():
                # Add number suffix if file exists
                n = 1
                while True:
                    numbered_srt = video_dir / f"{video_path.stem}_range_{start_seconds}_{end_seconds}_{n}.srt"
                    if not numbered_srt.exists():
                        final_srt = numbered_srt
                        break
                    n += 1
            
            temp_srt.rename(final_srt)
            
            # Clean up temporary audio file
            if temp_audio.exists():
                temp_audio.unlink()
            
            if log_callback:
                log_callback(f"✓ Time range transcription complete: {final_srt.name}")
            return True
        else:
            if log_callback:
                log_callback("Error: SRT file was not generated")
            # Clean up temporary audio file
            if temp_audio.exists():
                temp_audio.unlink()
            return False
        
    except Exception as e:
        if log_callback:
            log_callback(f"Error during time range transcription: {e}")
            log_callback(f"Traceback: {traceback.format_exc()}")
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
        # Check if gemini_srt_translator is installed and can be run as module
        result = subprocess.run(
            [sys.executable, "-m", "gemini_srt_translator", "--help"],
            capture_output=True,
            timeout=2
        )
        if result.returncode == 0:
            # Return Python command to run as module
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
    
    # Check if executable is in PATH
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
        
        # Check installation status
        self.pyqt5_installed = check_python_package("PyQt5")
        self.gst_installed = find_gst_command() is not None  # Check for gst command, not Python package (pipx support)
        self.ffmpeg_installed = check_command_exists("ffmpeg")
        self.n_m3u8_installed = check_command_exists("N_m3u8DL-RE")
        self.vlc_installed = check_app_exists("VLC")
        self.lossless_installed = check_app_exists("LosslessCut")
        self.subtitle_edit_installed = check_app_exists("SubtitleEdit")
        
        self.all_required_installed = (self.pyqt5_installed and self.gst_installed and 
                                       self.ffmpeg_installed and self.n_m3u8_installed)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Title bar (consistent across all steps)
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
        self.step_label = QLabel("Step 1 of 4")
        self.step_label.setFont(QFont("Arial", 9))
        self.step_label.setStyleSheet("color: #666;")
        layout.addWidget(self.step_label)
        
        # Stacked widget for different steps
        self.stacked = QStackedWidget()
        self.stacked.addWidget(self.create_welcome_step())
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
        
        content = QTextBrowser()
        content.setOpenExternalLinks(True)
        content.setHtml(self.get_required_html())
        layout.addWidget(content)
        
        widget.setLayout(layout)
        return widget
    
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
        self.api_key_checkbox.setChecked(has_env_key or bool(self.config.get("api_key", "")))
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
        """Generate HTML for required components."""
        html = "<div style='line-height: 1.6;'>"
        
        # Python Packages
        html += "<h4 style='color: #df4300; margin-top: 10px;'>Python Packages:</h4>"
        html += f"<p><b>{'✓ INSTALLED' if self.pyqt5_installed else '✗ NOT FOUND'}</b> - PyQt5</p>"
        if not self.pyqt5_installed:
            html += "<p style='margin-left: 20px; color: #666;'>Install: <code>pip install PyQt5</code></p>"
        
        html += f"<p><b>{'✓ INSTALLED' if self.gst_installed else '✗ NOT FOUND'}</b> - gemini-srt-translator</p>"
        if not self.gst_installed:
            html += "<p style='margin-left: 20px; color: #666;'>Install: <code>pip install gemini-srt-translator</code></p>"
        
        # External Programs
        html += "<h4 style='color: #f48a32; margin-top: 15px;'>External Programs:</h4>"
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
        
        html += f"<p><b>{'✓ INSTALLED' if self.n_m3u8_installed else '✗ NOT FOUND'}</b> - N_m3u8DL-RE</p>"
        if not self.n_m3u8_installed:
            html += "<p style='margin-left: 20px; color: #666;'>Download: <a href='https://github.com/nilaoda/N_m3u8DL-RE/releases'>GitHub Releases</a><br>"
            html += "Extract and add to PATH</p>"
        
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
            html += "<p style='color: #aa0000;'><b>⚠ Some required components are missing.</b></p>"
            html += "<p>The app may not work properly. Install missing items, then restart the app.</p>"
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
        save_config(self.config)
        self.reject()
    
    def complete_setup(self):
        """Complete setup and mark as done."""
        self.config["setup_complete"] = True
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
        This means you tried to download episodes but didn't paste any commands in the text box. 
        Make sure you've copied your download commands and pasted them into the "Commands" area before clicking "Batch Download Episodes".
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
        return """
        <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; font-size: 13pt; line-height: 1.6; }
        .app-name { font-size: 18pt; font-weight: 600; color: #b42075; margin-bottom: 4px; }
        .version { font-size: 13pt; color: #666; margin-bottom: 16px; }
        .creator { font-size: 13pt; color: #333; margin-bottom: 20px; }
        .description { font-size: 13pt; color: #333; margin-bottom: 24px; line-height: 1.7; }
        .footer { font-size: 12pt; color: #666; font-style: italic; margin-top: 24px; }
        </style>
        <div style="padding: 24px;">
        <div class="app-name">Video Processing Studio</div>
        
        <div class="version">Version 9.2.2</div>
        
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
        
        # Selected languages with native names (curated list to avoid scrolling issues)
        languages = [
            ("Auto-detect", "auto"),
            ("English (English)", "en"),
            ("French (Français)", "fr"),
            ("Spanish (Español)", "es"),
            ("Catalan (Català)", "ca"),
            ("German (Deutsch)", "de"),
            ("Italian (Italiano)", "it"),
            ("Portuguese (Português - BR/PT)", "pt"),
            ("Dutch (Nederlands)", "nl"),
            ("Chinese (中文)", "zh"),
            ("Japanese (日本語)", "ja"),
            ("Korean (한국어)", "ko"),
            ("Arabic (العربية)", "ar"),
            ("Thai (ไทย)", "th"),
            ("Greek (Ελληνικά)", "el"),
        ]
        
        for name, code in languages:
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
                result = subprocess.run(
                    ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(video_path)],
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
# Time Range Transcription Dialog
# ============================================================================

class TimeRangeTranscriptionDialog(QDialog):
    """Dialog for transcribing a specific time range of a video."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Transcribe Time Range")
        self.setMinimumWidth(600)
        
        self.video_path = None
        
        layout = QVBoxLayout()
        form_layout = QFormLayout()
        
        # Info label
        info_label = QLabel(
            "Transcribe only a specific portion of a video/audio file. "
            "This is useful for correcting missing sections or processing specific segments."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # File selection
        file_layout = QHBoxLayout()
        self.file_input = QLineEdit()
        self.file_input.setReadOnly(True)
        self.file_input.setPlaceholderText("No file selected")
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(self.file_input)
        file_layout.addWidget(browse_btn)
        form_layout.addRow("Video/Audio File:", file_layout)
        
        # Language selection
        self.language_combo = QComboBox()
        languages = [
            ("Auto-detect", "auto"),
            ("English (English)", "en"),
            ("French (Français)", "fr"),
            ("Spanish (Español)", "es"),
            ("Catalan (Català)", "ca"),
            ("German (Deutsch)", "de"),
            ("Italian (Italiano)", "it"),
            ("Portuguese (Português)", "pt"),
            ("Dutch (Nederlands)", "nl"),
        ]
        for name, code in languages:
            self.language_combo.addItem(name, code)
        default_index = self.language_combo.findData("en")
        if default_index >= 0:
            self.language_combo.setCurrentIndex(default_index)
        form_layout.addRow("Language:", self.language_combo)
        
        # Start time
        self.start_time = QTimeEdit()
        self.start_time.setDisplayFormat("HH:mm:ss")
        self.start_time.setTime(QTime(0, 0, 0))
        self.start_time.timeChanged.connect(self.update_preview)
        form_layout.addRow("Start Time (HH:MM:SS):", self.start_time)
        
        # End time
        self.end_time = QTimeEdit()
        self.end_time.setDisplayFormat("HH:mm:ss")
        self.end_time.setTime(QTime(0, 1, 0))  # Default 1 minute
        self.end_time.timeChanged.connect(self.update_preview)
        form_layout.addRow("End Time (HH:MM:SS):", self.end_time)
        
        # Preview label
        self.preview_label = QLabel("")
        self.preview_label.setStyleSheet("color: #0066cc; font-weight: bold;")
        form_layout.addRow("", self.preview_label)
        
        # Adjust timestamps checkbox
        self.adjust_timestamps_checkbox = QCheckBox(
            "Adjust timestamps to match original video timing"
        )
        self.adjust_timestamps_checkbox.setChecked(True)
        self.adjust_timestamps_checkbox.setToolTip(
            "When enabled, the SRT timestamps will be offset to match the original video. "
            "For example, if you transcribe from 00:01:30 onwards, the first subtitle will "
            "start at 00:01:30 instead of 00:00:00."
        )
        help_label = QLabel(
            "When enabled, subtitle timestamps will align with the original video position. "
            "Disable this if you want timestamps to start at 00:00:00."
        )
        help_label.setWordWrap(True)
        help_label.setStyleSheet("color: #666; font-size: 10px;")
        checkbox_layout = QVBoxLayout()
        checkbox_layout.addWidget(self.adjust_timestamps_checkbox)
        checkbox_layout.addWidget(help_label)
        form_layout.addRow("", checkbox_layout)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.ok_btn = QPushButton("Start Transcription")
        self.ok_btn.clicked.connect(self.validate_and_accept)
        self.ok_btn.setEnabled(False)  # Disabled until file is selected
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        self.update_preview()
    
    def browse_file(self):
        """Browse for video/audio file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video or Audio File",
            str(get_downloads_dir()),
            "Media Files (*.mkv *.mp4 *.mov *.avi *.mp3 *.wav *.m4a);;All Files (*)"
        )
        if file_path:
            self.video_path = Path(file_path)
            self.file_input.setText(str(self.video_path))
            self.ok_btn.setEnabled(True)
            self.update_preview()
    
    def update_preview(self):
        """Update the preview label showing duration."""
        start_seconds = self.time_to_seconds(self.start_time.time())
        end_seconds = self.time_to_seconds(self.end_time.time())
        
        if end_seconds > start_seconds:
            duration_seconds = end_seconds - start_seconds
            duration_str = self.seconds_to_time_str(duration_seconds)
            start_str = self.start_time.time().toString("HH:mm:ss")
            end_str = self.end_time.time().toString("HH:mm:ss")
            self.preview_label.setText(
                f"Will transcribe {duration_str} of audio ({start_str} → {end_str})"
            )
            self.preview_label.setStyleSheet("color: #0066cc; font-weight: bold;")
        else:
            self.preview_label.setText("⚠ End time must be after start time")
            self.preview_label.setStyleSheet("color: #cc0000; font-weight: bold;")
    
    def time_to_seconds(self, qtime: QTime) -> int:
        """Convert QTime to total seconds."""
        return qtime.hour() * 3600 + qtime.minute() * 60 + qtime.second()
    
    def seconds_to_time_str(self, seconds: int) -> str:
        """Convert seconds to readable time string."""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def validate_and_accept(self):
        """Validate inputs before accepting."""
        if not self.video_path:
            QMessageBox.warning(self, "No File", "Please select a video or audio file.")
            return
        
        start_seconds = self.time_to_seconds(self.start_time.time())
        end_seconds = self.time_to_seconds(self.end_time.time())
        
        if end_seconds <= start_seconds:
            QMessageBox.warning(
                self, "Invalid Time Range",
                "End time must be after start time."
            )
            return
        
        self.accept()
    
    def get_parameters(self) -> Dict:
        """Get the transcription parameters."""
        start_seconds = self.time_to_seconds(self.start_time.time())
        end_seconds = self.time_to_seconds(self.end_time.time())
        
        return {
            "video_path": self.video_path,
            "language_code": self.language_combo.currentData(),
            "start_time": start_seconds,
            "end_time": end_seconds,
            "start_time_str": self.start_time.time().toString("HH:mm:ss"),
            "end_time_str": self.end_time.time().toString("HH:mm:ss"),
            "adjust_timestamps": self.adjust_timestamps_checkbox.isChecked()
        }


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
        
        layout = QFormLayout()
        
        # API Key Section
        api_key_info = QLabel(
            'You can set up your API key safely by setting the GEMINI_API_KEY environment variable. '
            '<a href="https://aistudio.google.com/app/apikey">Get your API key here</a> and follow the instructions '
            'for your platform. Using the legacy API key input below is less secure, but it\'s fine if you prefer that.'
        )
        api_key_info.setOpenExternalLinks(True)
        api_key_info.setWordWrap(True)
        api_key_info.setStyleSheet("color: #666;")
        layout.addRow("", api_key_info)
        
        # Legacy API key input (optional, for backward compatibility)
        self.api_key_input = QLineEdit()
        self.api_key_input.setText(self.config.get("api_key", ""))
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("Optional: Legacy API key input")
        legacy_label = QLabel("API Key (Legacy):")
        layout.addRow(legacy_label, self.api_key_input)
        
        # Second API key input (optional, for multi-key translation)
        self.api_key2_input = QLineEdit()
        self.api_key2_input.setText(self.config.get("api_key2", ""))
        self.api_key2_input.setEchoMode(QLineEdit.Password)
        self.api_key2_input.setPlaceholderText("Optional: Second API key for translation")
        api_key2_label = QLabel("API Key 2 (Optional):")
        layout.addRow(api_key2_label, self.api_key2_input)
        
        # Use watermarks checkbox
        self.use_watermarks_checkbox = QCheckBox("Use watermarks")
        self.use_watermarks_checkbox.setChecked(self.config.get("use_watermarks", True))
        self.use_watermarks_checkbox.stateChanged.connect(self.toggle_watermark_fields)
        layout.addRow("", self.use_watermarks_checkbox)
        
        # Watermark 720p
        self.watermark_720p_input = QLineEdit()
        self.watermark_720p_input.setText(self.config.get("watermark_720p", ""))
        self.wm720_browse = QPushButton("Browse...")
        self.wm720_browse.clicked.connect(lambda: self.browse_file(self.watermark_720p_input, "Select 720p Watermark"))
        wm720_layout = QHBoxLayout()
        wm720_layout.addWidget(self.watermark_720p_input)
        wm720_layout.addWidget(self.wm720_browse)
        layout.addRow("Watermark 720p:", wm720_layout)
        
        # Watermark 1080p
        self.watermark_1080p_input = QLineEdit()
        self.watermark_1080p_input.setText(self.config.get("watermark_1080p", ""))
        self.wm1080_browse = QPushButton("Browse...")
        self.wm1080_browse.clicked.connect(lambda: self.browse_file(self.watermark_1080p_input, "Select 1080p Watermark"))
        wm1080_layout = QHBoxLayout()
        wm1080_layout.addWidget(self.watermark_1080p_input)
        wm1080_layout.addWidget(self.wm1080_browse)
        layout.addRow("Watermark 1080p:", wm1080_layout)
        
        # Translation Settings
        translation_section = QLabel("<b>Subtitle Translation Settings</b>")
        layout.addRow("", translation_section)
        
        # Target language for translation
        translation_info = QLabel(
            "Select the target language for subtitle translation. "
            "Subtitles will be translated from their original language to your selected target."
        )
        translation_info.setWordWrap(True)
        translation_info.setStyleSheet("color: #666;")
        layout.addRow("", translation_info)
        
        self.translation_target_combo = QComboBox()
        for lang in ["English", "French", "Spanish", "Catalan", "German", "Italian", "Portuguese", "Dutch"]:
            self.translation_target_combo.addItem(lang)
        current_target = self.config.get("translation_target_language", "English")
        target_index = self.translation_target_combo.findText(current_target)
        if target_index >= 0:
            self.translation_target_combo.setCurrentIndex(target_index)
        layout.addRow("Translation Target:", self.translation_target_combo)
        
        # ISO 639 suffix checkbox
        self.iso639_checkbox = QCheckBox("Use ISO 639 language suffixes (.eng.srt, .fra.srt)")
        self.iso639_checkbox.setChecked(self.config.get("use_iso639_suffixes", False))
        iso639_help = QLabel(
            "When enabled, translated subtitles will include language codes in filenames. "
            "This allows VLC and Jellyfin to automatically detect and select subtitles."
        )
        iso639_help.setWordWrap(True)
        iso639_help.setStyleSheet("color: #666; font-size: 10px;")
        iso639_layout = QVBoxLayout()
        iso639_layout.addWidget(self.iso639_checkbox)
        iso639_layout.addWidget(iso639_help)
        layout.addRow("", iso639_layout)
        
        # Lesbian Flag theme toggle (joke feature - doesn't actually turn off)
        self.lesbian_flag_checkbox = QCheckBox("Toggle Lesbian Flag theme OFF")
        self.lesbian_flag_checkbox.setChecked(False)  # Always unchecked (meaning theme is ON)
        self.lesbian_flag_checkbox.stateChanged.connect(self.toggle_lesbian_flag_theme)
        layout.addRow("", self.lesbian_flag_checkbox)
        
        # Set initial state
        self.toggle_watermark_fields()
        
        # Buttons
        button_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_settings)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addRow(button_layout)
        
        self.setLayout(layout)
    
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
        self.config["api_key"] = self.api_key_input.text()
        self.config["api_key2"] = self.api_key2_input.text()
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
        
        # Show setup wizard on first launch
        if not self.config.get("setup_complete", False):
            wizard = SetupWizard(self)
            wizard.exec_()
        
        self.init_ui()
    
    def darken_color(self, hex_color: str, percent: float = 0.15) -> str:
        """Darken a hex color by a percentage."""
        # Remove # if present
        hex_color = hex_color.lstrip('#')
        # Convert to RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        # Darken by percent
        r = max(0, int(r * (1 - percent)))
        g = max(0, int(g * (1 - percent)))
        b = max(0, int(b * (1 - percent)))
        # Convert back to hex
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
        # Lesbian flag colors: Red → Orange → Light Orange → Pink → Purple → Dark Pink
        colors = [
            "#df4300",  # Red
            "#f48a32",  # Orange
            "#ffab68",  # Light Orange
            "#dc7bb3",  # Pink
            "#c46ea1",  # Purple
            "#b42075",  # Dark Pink
        ]
        
        # Find all buttons and apply colors by section
        # We'll need to store button references or find them by their parent group
        # For now, let's apply styles directly to buttons we can identify
        
        # Get all QPushButton widgets
        buttons = self.findChildren(QPushButton)
        
        # Group buttons by their parent QGroupBox
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
            # Walk up the parent chain to find QGroupBox
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
            
            # Settings, FAQ, and About buttons are in top bar, not in a group
            if btn.text() == "Settings":
                settings_button = btn
            elif btn.text() == "FAQ":
                faq_button = btn
            elif btn.text() == "About":
                about_button = btn
        
        # Apply colors to each group
        # Group 1: Download buttons - Red
        for btn in download_buttons:
            self.apply_button_style(btn, colors[0])
        
        # Group 2: Subtitles buttons - Orange
        for btn in subtitle_buttons:
            self.apply_button_style(btn, colors[1])
        
        # Group 3: Process video buttons - Light Orange
        for btn in process_buttons:
            self.apply_button_style(btn, colors[2])
        
        # Group 4: Remux buttons - Pink
        for btn in remux_buttons:
            self.apply_button_style(btn, colors[3])
        
        # Group 5: Transcribe button - Purple
        for btn in transcribe_buttons:
            self.apply_button_style(btn, colors[4])
        
        # Settings, FAQ, and About buttons - Dark Pink
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
        languages = [
            ("Auto-detect", "auto"),
            ("English (English)", "en"),
            ("French (Français)", "fr"),
            ("Spanish (Español)", "es"),
            ("Catalan (Català)", "ca"),
            ("German (Deutsch)", "de"),
            ("Italian (Italiano)", "it"),
            ("Portuguese (Português)", "pt"),
            ("Dutch (Nederlands)", "nl"),
            ("Chinese (中文)", "zh"),
            ("Japanese (日本語)", "ja"),
            ("Korean (한국어)", "ko"),
        ]
        for name, code in languages:
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
        model_info.setStyleSheet("color: #666; font-size: 10px;")
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
        
        time_range_btn = QPushButton("Transcribe Time Range")
        time_range_btn.clicked.connect(self.transcribe_time_range)
        
        advanced_btn = QPushButton("Advanced Options...")
        advanced_btn.clicked.connect(self.open_whisper_options)
        
        buttons_layout.addWidget(self.transcribe_main_btn, 2)
        buttons_layout.addWidget(time_range_btn, 1)
        buttons_layout.addWidget(advanced_btn, 1)
        layout.addLayout(buttons_layout)
        
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
        lang_display = "Auto-detect" if language_code == "auto" else language_code
        self.transcribe_log(f"Language: {lang_display}, Model: {model}, Format: {output_format}")
        
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
    
    def create_remuxing_tab(self):
        """Create the dedicated remuxing tab."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Header
        header_label = QLabel("Remuxing Hub")
        header_label.setFont(QFont("Arial", 14, QFont.Bold))
        layout.addWidget(header_label)
        
        desc_label = QLabel(
            "Combine video files (MKV/MP4) with subtitle files (SRT/VTT), split audio channels, "
            "and convert audio formats. Use track analysis to see available tracks before remuxing."
        )
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #666;")
        layout.addWidget(desc_label)
        
        # File management
        file_group = QGroupBox("Files")
        file_layout = QVBoxLayout()
        
        # Initialize selected files list and file configs
        self.remux_selected_files = []
        self.remux_file_configs = {}  # Store per-file configuration
        
        # Buttons row
        buttons_row = QHBoxLayout()
        add_files_btn = QPushButton("Add Files...")
        add_files_btn.clicked.connect(self.add_remux_files)
        remove_files_btn = QPushButton("Remove Selected")
        remove_files_btn.clicked.connect(self.remove_remux_files)
        clear_files_btn = QPushButton("Clear All")
        clear_files_btn.clicked.connect(self.clear_remux_files)
        media_info_btn = QPushButton("Media Info")
        media_info_btn.clicked.connect(self.show_media_info)
        buttons_row.addWidget(add_files_btn)
        buttons_row.addWidget(remove_files_btn)
        buttons_row.addWidget(clear_files_btn)
        buttons_row.addWidget(media_info_btn)
        file_layout.addLayout(buttons_row)
        
        # Files tree widget (like MKVToolNix GUI)
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
        self.remux_files_tree.setContextMenuPolicy(3)  # Qt.CustomContextMenu
        self.remux_files_tree.customContextMenuRequested.connect(self.show_track_context_menu)
        file_layout.addWidget(self.remux_files_tree)
        
        # File count label
        self.remux_file_count_label = QLabel("No files selected")
        self.remux_file_count_label.setStyleSheet("color: #666; font-size: 10px;")
        file_layout.addWidget(self.remux_file_count_label)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Global options (defaults for new files)
        options_group = QGroupBox("Default Options (for new files)")
        options_layout = QVBoxLayout()
        
        # Output format
        format_row = QHBoxLayout()
        format_label = QLabel("Output Format:")
        format_label.setFixedWidth(150)
        self.remux_default_output_format = QComboBox()
        self.remux_default_output_format.addItem("MKV", "mkv")
        self.remux_default_output_format.addItem("MP4", "mp4")
        format_row.addWidget(format_label)
        format_row.addWidget(self.remux_default_output_format)
        format_row.addStretch()
        options_layout.addLayout(format_row)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Action buttons
        buttons_layout = QHBoxLayout()
        
        remux_selected_btn = QPushButton("Remux Selected Files")
        remux_selected_btn.clicked.connect(self.remux_selected_files_action)
        buttons_layout.addWidget(remux_selected_btn, 2)
        
        split_audio_btn = QPushButton("Split Audio Channels")
        split_audio_btn.clicked.connect(self.split_audio_channels_batch)
        buttons_layout.addWidget(split_audio_btn, 1)
        
        layout.addLayout(buttons_layout)
        
        # Minimal log (single line)
        log_label = QLabel("Status:")
        log_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(log_label)
        
        self.remux_log_output = QLineEdit()
        self.remux_log_output.setReadOnly(True)
        self.remux_log_output.setPlaceholderText("Remuxing operations will show status here (errors only)")
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
                    'subtitle_file': None,  # Will be auto-detected or manually set
                    'selected_video_tracks': [],
                    'selected_audio_tracks': [],
                    'selected_subtitle_tracks': []
                }
                # Add to tree widget
                self.add_file_to_tree(video_path)
        
        self.update_remux_file_count()
    
    def add_file_to_tree(self, video_path: Path):
        """Add a file to the tree widget with its tracks."""
        if not video_path.exists():
            return
        
        # Create file item
        file_item = QTreeWidgetItem(self.remux_files_tree)
        file_item.setText(0, video_path.name)
        file_item.setText(1, "File")
        file_item.setExpanded(True)
        file_item.setData(0, 256, str(video_path))  # Store path in data
        
        # Analyze tracks
        tracks = analyze_tracks(video_path)
        
        # Add video tracks
        if tracks['video']:
            for vid_track in tracks['video']:
                track_item = QTreeWidgetItem(file_item)
                track_id = vid_track.get('track_id', 0)
                codec = vid_track.get('codec', 'unknown')
                res = vid_track.get('resolution', 'unknown')
                track_item.setText(0, f"Video Track {track_id}")
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
                track_item.setText(0, f"Audio Track {track_id}")
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
                track_item.setText(0, f"Subtitle Track {track_id}")
                track_item.setText(1, "Subtitle")
                track_item.setText(2, format_type)
                track_item.setText(3, sub_track.get('language', 'unknown'))
                track_item.setText(4, "")
                # Add checkbox
                track_item.setCheckState(0, 0)  # Unchecked by default (external subs preferred)
                track_item.setData(0, 256, f"subtitle:{track_id}")  # Store track info
        
        # Add external subtitle file option
        subtitle_item = QTreeWidgetItem(file_item)
        subtitle_item.setText(0, "External Subtitle File")
        subtitle_item.setText(1, "External")
        subtitle_item.setText(2, "SRT/VTT")
        subtitle_item.setText(3, "")
        subtitle_item.setText(4, "")
        # Add browse button in Actions column
        browse_sub_btn = QPushButton("Browse...")
        browse_sub_btn.setMaximumWidth(80)
        browse_sub_btn.clicked.connect(lambda checked, path=video_path: self.browse_subtitle_file(path))
        self.remux_files_tree.setItemWidget(subtitle_item, 5, browse_sub_btn)
        subtitle_item.setData(0, 256, "external_subtitle")
        
        # Add per-file output format
        format_item = QTreeWidgetItem(file_item)
        format_item.setText(0, "Output Format")
        format_item.setText(1, "Option")
        format_combo = QComboBox()
        format_combo.addItem("MKV", "mkv")
        format_combo.addItem("MP4", "mp4")
        # Set current format
        default_format = self.remux_file_configs[video_path]['output_format']
        format_index = format_combo.findData(default_format)
        if format_index >= 0:
            format_combo.setCurrentIndex(format_index)
        format_combo.currentIndexChanged.connect(lambda idx, path=video_path: self.update_file_output_format(path, format_combo.currentData()))
        self.remux_files_tree.setItemWidget(format_item, 2, format_combo)
        format_item.setData(0, 256, "output_format")
        
        # Add remux button for this file
        remux_file_item = QTreeWidgetItem(file_item)
        remux_file_item.setText(0, "Actions")
        remux_file_btn = QPushButton("Remux This File")
        remux_file_btn.setMaximumWidth(120)
        remux_file_btn.clicked.connect(lambda checked, path=video_path: self.remux_single_file(path))
        self.remux_files_tree.setItemWidget(remux_file_item, 5, remux_file_btn)
        remux_file_item.setData(0, 256, "remux_action")
    
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
            # Update the tree item text to show selected file
            root = self.remux_files_tree.invisibleRootItem()
            for i in range(root.childCount()):
                file_item = root.child(i)
                if file_item.data(0, 256) == str(video_path):
                    # Find the external subtitle item
                    for j in range(file_item.childCount()):
                        child = file_item.child(j)
                        if child.data(0, 256) == "external_subtitle":
                            child.setText(2, Path(subtitle_file).name)
                            break
                    break
    
    def update_file_output_format(self, video_path: Path, output_format: str):
        """Update output format for a specific file."""
        if video_path in self.remux_file_configs:
            self.remux_file_configs[video_path]['output_format'] = output_format
    
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
        success = self.remux_file_with_tracks(
            video_path, output_format, selected_video, selected_audio, 
            selected_subtitles, external_subtitle
        )
        
        if success:
            self.remux_log_output.setText(f"✓ Remuxed {video_path.name}")
        else:
            self.remux_log_output.setText(f"✗ Failed to remux {video_path.name}")
    
    def remux_file_with_tracks(self, video_path: Path, output_format: str,
                               video_tracks: List[int], audio_tracks: List[int],
                               subtitle_tracks: List[int], external_subtitle: Path = None) -> bool:
        """Remux a file with specific track selections.
        
        Note: Track IDs from analyze_tracks correspond to FFmpeg stream indices.
        """
        if not video_path.exists():
            return False
        
        base = video_path.stem
        output_file = video_path.parent / f"{base}_remuxed.{output_format}"
        
        if output_file.exists():
            return True  # Already exists
        
        # Build FFmpeg command with track selection
        cmd = ["ffmpeg", "-y", "-i", str(video_path)]
        
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
        
        # If no tracks explicitly selected, include all tracks (default)
        if not video_tracks and not audio_tracks and not subtitle_tracks:
            # Rebuild command to include all tracks
            cmd = ["ffmpeg", "-y", "-i", str(video_path)]
            
            # Add external subtitle if provided
            if external_subtitle and external_subtitle.exists():
                cmd.extend(["-i", str(external_subtitle)])
                cmd.extend(["-map", "0"])  # Map all tracks from video
                cmd.extend(["-map", "1:0"])  # Map subtitle from external file
                subtitle_format = "srt" if external_subtitle.suffix.lower() == ".srt" else "vtt"
                cmd.extend(["-c", "copy", "-c:s", subtitle_format])
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
                    cmd.extend(["-c", "copy", "-c:s", "srt"])
                elif vtt_file.exists():
                    cmd.extend(["-i", str(vtt_file)])
                    cmd.extend(["-map", "0"])  # All video tracks
                    cmd.extend(["-map", "1:0"])  # Subtitle
                    cmd.extend(["-c", "copy", "-c:s", "vtt"])
                else:
                    # Just copy all tracks
                    cmd.extend(["-c", "copy"])
            
            cmd.append(str(output_file))
        else:
            # Copy codecs for selected tracks
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
        self.setWindowTitle("SP workshop (WLW video processing, translation & subtitling hub)")
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
                stop:0 #df4300, stop:0.16 #f48a32, stop:0.33 #ffab68,
                stop:0.5 white, stop:0.66 #dc7bb3, stop:0.83 #c46ea1, stop:1 #b42075);
            padding: 8px 16px;
            border-radius: 5px;
        """)
        
        header_left_layout.addWidget(app_name_label)
        
        # Version number below title
        version_label = QLabel('version 9.2.2 "Polyglot"')
        version_label.setFont(QFont("Arial", 18))
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
        
        # Create tab widget for main content
        self.main_tabs = QTabWidget()
        
        # Create "Main" tab with all existing sections
        main_tab = QWidget()
        layout = QVBoxLayout()
        main_tab.setLayout(layout)
        
        # Download section
        download_group = QGroupBox("DOWNLOAD")
        download_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        download_layout = QVBoxLayout()
        
        # Episodes row and Instructions link
        episodes_row = QHBoxLayout()
        starting_ep_label = QLabel("Episodes:")
        self.starting_episode_input = QLineEdit()
        self.starting_episode_input.setText("1")
        self.starting_episode_input.setMaximumWidth(120)
        self.starting_episode_input.setPlaceholderText("1 or 1-5 or 1,3,5-7")
        self.starting_episode_input.setToolTip("Episode numbers:\n• Single: 1\n• Range: 1-5\n• Mixed: 1,3,5-7,10")
        
        instructions_btn = QPushButton("How to get commands")
        instructions_btn.setFlat(True)
        instructions_btn.setStyleSheet("color: #0066cc; text-decoration: underline;")
        instructions_btn.setCursor(Qt.PointingHandCursor)
        instructions_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(DOWNLOAD_INSTRUCTIONS_URL)))
        instructions_btn.setToolTip("Opens instructions in your browser")
        
        episodes_row.addWidget(starting_ep_label)
        episodes_row.addWidget(self.starting_episode_input)
        episodes_row.addStretch()
        episodes_row.addWidget(instructions_btn)
        download_layout.addLayout(episodes_row)
        
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
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(lambda: self.commands_text.clear())
        download_btn = QPushButton("Batch download episodes")
        download_btn.clicked.connect(self.download_episodes)
        add_videos_btn = QPushButton("Add videos...")
        add_videos_btn.clicked.connect(self.add_videos)
        open_lossless_btn = QPushButton("Open in LosslessCut...")
        open_lossless_btn.clicked.connect(self.open_lossless_cut)
        open_downloads_btn = QPushButton("Open Downloads folder")
        open_downloads_btn.clicked.connect(lambda: open_folder_in_explorer(get_downloads_dir()))
        download_buttons.addWidget(clear_btn)
        download_buttons.addWidget(download_btn)
        download_buttons.addWidget(add_videos_btn)
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
        
        # Determine operation type from function name
        func_name = script_func.__name__
        operation_names = {
            "download_episodes": "Downloading episodes",
            "download_with_detection": "Downloading episodes",
            "extract_subtitles": "Extracting subtitles",
            "clean_subtitles": "Cleaning subtitles",
            "translate_subtitles": "Translating subtitles",
            "process_video": "Processing videos",
            "remux_mkv_with_srt_batch": "Remuxing videos",
            "transcribe_video": "Transcribing video"
        }
        self.current_operation = operation_names.get(func_name, "Processing")
        
        # Hide progress section for downloads (user preference), show for other operations
        is_download = func_name in ["download_episodes", "download_with_detection"]
        self.progress_group.setVisible(not is_download)
        
        if not is_download:
            # Only configure progress bar if visible
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("%p%")
            self.progress_operation_label.setText(f"{self.current_operation}...")
            self.progress_file_label.setText("")
            self.progress_counter_label.setText("")
            self.update_progress_bar_color()
            # Enable stop button
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
        # Try to extract percentage from filename (format: "filename.mp4 (45.2%)")
        file_percentage = None
        if filename and '(' in filename and '%' in filename:
            try:
                # Extract percentage from filename like "video.mp4 (45.2%)"
                match = re.search(r'\((\d+\.?\d*)%\)', filename)
                if match:
                    file_percentage = float(match.group(1))
            except (ValueError, AttributeError):
                pass
        
        if total > 0:
            if file_percentage is not None:
                # Calculate combined progress: file-level progress + per-file percentage
                # File-level progress accounts for completed files (0 to total-1)
                # Per-file progress accounts for current file (0 to 1)
                completed_files_progress = ((current - 1) / total) * 100 if current > 1 else 0
                current_file_progress = (file_percentage / 100) * (100 / total)
                combined_percent = completed_files_progress + current_file_progress
                percent = int(min(100, max(0, combined_percent)))
            else:
                # Fallback to file-level progress only
                percent = int((current / total) * 100)
            
            self.progress_bar.setValue(percent)
            self.progress_counter_label.setText(f"{current}/{total}")
        else:
            # Indeterminate progress for single-file operations
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
    
    def download_episodes(self):
        """Download episodes."""
        commands_text = self.commands_text.toPlainText()
        if not commands_text.strip():
            QMessageBox.warning(self, "Error", "Please paste commands in the text area.")
            return
        
        # Get episode specification from UI
        episode_spec = self.starting_episode_input.text().strip() or "1"
        
        output_dir = get_downloads_dir()
        self.log(f"Starting download to: {output_dir}")
        self.log(f"Episodes: {episode_spec}")
        
        # Create a wrapper that adds detection after download
        def download_with_detection(commands_text, output_dir, episode_spec, progress_callback=None, log_callback=None):
            result = download_episodes(commands_text, output_dir, episode_spec, progress_callback, log_callback)
            if result:
                # Detect episode/scene for downloaded files
                mkv_files = list(output_dir.glob("*.mkv"))
                for mkv_file in mkv_files:
                    video_type, duration = detect_episode_or_scene(mkv_file)
                    if duration is not None:
                        type_label = "Episode" if video_type == "episode" else "Scene"
                        if log_callback:
                            log_callback(f"  {mkv_file.name}: {type_label} ({duration:.1f} min)")
            return result
        
        self.run_script(download_with_detection, commands_text, output_dir, episode_spec)
    
    def add_videos(self):
        """Add videos manually."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Video Files", "", "Video Files (*.mkv *.mp4);;All Files (*)"
        )
        
        if not file_paths:
            return
        
        downloads_dir = get_downloads_dir()
        copied_count = 0
        
        for file_path in file_paths:
            try:
                source_path = Path(file_path)
                dest_path = downloads_dir / source_path.name
                if dest_path.exists():
                    self.log(f"Skipping {source_path.name} - already exists")
                    continue
                shutil.copy2(file_path, dest_path)
                copied_count += 1
                
                # Detect episode or scene
                video_type, duration = detect_episode_or_scene(dest_path)
                if duration is not None:
                    type_label = "Episode" if video_type == "episode" else "Scene"
                    self.log(f"Copied: {source_path.name} ({type_label}, {duration:.1f} min)")
                else:
                    self.log(f"Copied: {source_path.name}")
            except Exception as e:
                self.log(f"Error copying {Path(file_path).name}: {e}")
        
        QMessageBox.information(self, "Complete", f"Added {copied_count} file(s) to downloads folder.")
    
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
        # Check environment variables first (recommended), then config (legacy)
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GST_API_KEY") or self.config.get("api_key", "")
        if not api_key:
            QMessageBox.warning(
                self, 
                "API Key Not Set", 
                "API key not found.\n\n"
                "Recommended: Set GEMINI_API_KEY or GST_API_KEY environment variable.\n"
                "See Settings for instructions.\n\n"
                "Legacy: You can also set it in Settings (less secure)."
            )
            return
        
        # Open file picker to select SRT files
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "Select SRT Files to Translate",
            str(get_subtitles_dir()),
            "Subtitle Files (*.srt);;All Files (*)"
        )
        
        if not file_paths:
            return
        
        # Get translation settings from config
        target_language = self.config.get("translation_target_language", "English")
        use_iso639 = self.config.get("use_iso639_suffixes", False)
        api_key2 = self.config.get("api_key2", "")
        
        self.log(f"Starting subtitle translation for {len(file_paths)} file(s)...")
        self.log(f"Target language: {target_language}, ISO 639 suffixes: {'enabled' if use_iso639 else 'disabled'}")
        if api_key2:
            self.log("Using second API key for translation")
        self.run_script(translate_subtitles, file_paths, api_key, target_language, use_iso639, api_key2)
    
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
        self.run_script(
            process_video, file_paths, subtitles_dir, output_dir,
            watermark_path, resolution, use_watermarks, use_iso639, target_language
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
            lang_display = "Auto-detect" if language_code == "auto" else language_code
            self.log(f"Language: {lang_display}, Model: {model}")
            
            # Run transcription with language, model, and whisper options
            def transcribe_with_params(video_path, language_code, model, whisper_options, progress_callback=None, log_callback=None):
                return transcribe_video(video_path, language_code, model, whisper_options, progress_callback=progress_callback, log_callback=log_callback)
            
            self.run_script(transcribe_with_params, video_path, language_code, model, whisper_options)
    
    def transcribe_time_range(self):
        """Transcribe a specific time range of a video."""
        # Show time range transcription dialog
        dialog = TimeRangeTranscriptionDialog(self)
        if dialog.exec_() != QDialog.Accepted:
            return  # User cancelled
        
        # Get parameters from dialog
        params = dialog.get_parameters()
        video_path = params["video_path"]
        language_code = params["language_code"]
        start_seconds = params["start_time"]
        end_seconds = params["end_time"]
        start_str = params["start_time_str"]
        end_str = params["end_time_str"]
        adjust_timestamps = params["adjust_timestamps"]
        
        # Get model from combo (saved to config automatically)
        model = self.transcribe_model_combo.currentText()
        
        # Get whisper options and output format
        config = load_config()
        whisper_options = config.get("whisper_options", {})
        
        # Process extra_args: convert multiline to space-separated if needed
        if "extra_args" in whisper_options and "extra_args_parsed" not in whisper_options:
            extra_args_text = whisper_options.get("extra_args", "")
            extra_args = " ".join(line.strip() for line in extra_args_text.split("\n") if line.strip())
            whisper_options["extra_args_parsed"] = extra_args
        
        output_format = self.transcribe_format_combo.currentData()
        
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
        
        self.transcribe_log(f"Starting time range transcription of: {video_path.name}")
        self.transcribe_log(f"Time range: {start_str} → {end_str}")
        lang_display = "Auto-detect" if language_code == "auto" else language_code
        self.transcribe_log(f"Language: {lang_display}, Model: {model}, Format: {output_format}")
        if adjust_timestamps:
            self.transcribe_log("Timestamps will be adjusted to match original video timing")
        else:
            self.transcribe_log("Timestamps will start at 00:00:00")
        
        # Show progress bar and stop button
        self.transcribe_progress_bar.setVisible(True)
        self.transcribe_stop_btn.setVisible(True)
        self.transcribe_stop_btn.setEnabled(True)
        self.transcribe_progress_bar.setRange(0, 0)  # Indeterminate
        
        # Run time range transcription
        def transcribe_range_with_params(
            video_path, start_seconds, end_seconds, language_code, model, 
            whisper_options, output_format, adjust_timestamps, progress_callback=None, log_callback=None
        ):
            return transcribe_video_time_range(
                video_path, start_seconds, end_seconds, language_code, model,
                whisper_options, output_format, adjust_timestamps, progress_callback, log_callback
            )
        
        # Use custom callbacks for the tab
        def tab_log_callback(msg):
            self.transcribe_log(msg)
        
        self.worker = ScriptWorker(
            transcribe_range_with_params, video_path, start_seconds, end_seconds, 
            language_code, model, whisper_options, output_format, adjust_timestamps
        )
        self.worker.log_message.connect(tab_log_callback)
        self.worker.finished.connect(self.on_transcribe_finished)
        self.worker.start()


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
