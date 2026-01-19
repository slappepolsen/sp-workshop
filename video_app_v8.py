#!/usr/bin/env python3
"""
Video Processing GUI Application
A PyQt5 desktop app that provides a button-based interface for all video processing scripts.
"""

import sys
import os
import json
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


def get_temp_dir() -> str:
    """Get a cross-platform temporary directory path."""
    return tempfile.gettempdir()


from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QFileDialog, QDialog,
    QLineEdit, QFormLayout, QMessageBox, QProgressBar, QGroupBox, QStyleFactory, QCheckBox, QStackedWidget, QTextBrowser, QComboBox,
    QGraphicsDropShadowEffect
)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QProcess, QUrl
from PyQt5.QtGui import QFont, QIcon, QPainter, QPen


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
        "use_watermarks": True
    }
    
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                user_config = json.load(f)
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


def detect_episode_or_scene(video_path: Path) -> tuple[str, Optional[float]]:
    """Detect if video is an episode or scene based on duration (7 min threshold)."""
    duration = get_video_duration(video_path)
    if duration is None:
        return "unknown", None
    if duration >= 7.0:
        return "episode", duration
    else:
        return "scene", duration


def open_in_lossless_cut(video_path: Path, log_callback=None) -> bool:
    """Open video file in LosslessCut application (cross-platform)."""
    lossless_cut = get_app_executable("LosslessCut")
    
    if not lossless_cut:
        if log_callback:
            log_callback("Error: LosslessCut not found. Please install it from https://github.com/mifi/lossless-cut")
        return False
    
    try:
        system = platform.system()
        
        if system == "Darwin":
            # macOS: use 'open -a' for .app bundles
            subprocess.run(["open", "-a", str(lossless_cut), str(video_path)])
        elif system == "Windows":
            # Windows: run the executable directly with the file as argument
            subprocess.Popen([str(lossless_cut), str(video_path)])
        else:
            # Linux: run the executable directly
            subprocess.Popen([str(lossless_cut), str(video_path)])
        
        if log_callback:
            log_callback(f"Opened {video_path.name} in LosslessCut")
        return True
    except Exception as e:
        if log_callback:
            log_callback(f"Error opening LosslessCut: {e}")
        return False


# ============================================================================
# Script Wrappers
# ============================================================================

def download_episodes(commands_text: str, output_dir: Path, progress_callback=None, log_callback=None) -> bool:
    """Download episodes using commands from text."""
    if not commands_text.strip():
        if log_callback:
            log_callback("Error: No commands provided.")
        return False
    
    lines = [line.strip() for line in commands_text.strip().split('\n') if line.strip()]
    
    if not lines:
        if log_callback:
            log_callback("No commands found.")
        return False
    
    downloaded_files = []
    total = len(lines)
    if log_callback:
        log_callback(f"Starting batch download for {total} episodes...")
    
    for i, line in enumerate(lines, start=1):
        match = re.search(r"Episode\s+(\d+):\s*(.*)", line)
        if not match:
            if log_callback:
                log_callback(f"Skipping invalid line {i}: {line}")
            continue
        
        episode_number, base_command = match.groups()
        episode_number = episode_number.strip()
        
        if progress_callback:
            progress_callback(i, total, f"Episode {episode_number}")
        
        command = (
            f"{base_command} "
            f"-sv best "
            f"--tmp-dir {quote_path(get_temp_dir())} "
            f"--del-after-done "
            f"--check-segments-count False "
            f"--save-name {quote_path(episode_number)} "
            f"--save-dir {quote_path(str(output_dir))} "
            f"--select-video best"
            f"--select-audio lang=fr "
            f"--select-subtitle lang=fr"
        )
        
        if log_callback:
            log_callback(f"\n--- Task {i}/{total}: Episode {episode_number} ---")
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
            while True:
                line_output = process.stdout.readline()
                if not line_output:
                    break
                
                line_output = line_output.strip()
                if line_output:
                    output_lines.append(line_output)
                    # Log all output from N_m3u8DL-RE for verbose feedback
                    if log_callback:
                        log_callback(f"  {line_output}")
                    
                    # Try to parse progress information from N_m3u8DL-RE output
                    # Common patterns: "Downloading...", "Progress: X%", "Speed: X MB/s", etc.
                    if "Progress:" in line_output or "%" in line_output:
                        # Extract percentage if available
                        percent_match = re.search(r'(\d+(?:\.\d+)?)%', line_output)
                        if percent_match and progress_callback:
                            try:
                                percent = float(percent_match.group(1))
                                # Update progress with percentage for current episode
                                enhanced_filename = f"Episode {episode_number} ({percent:.1f}%)"
                                progress_callback(i, total, enhanced_filename)
                            except ValueError:
                                pass
            
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


def translate_subtitles(selected_srt_files: List[Path], api_key: Optional[str] = None, progress_callback=None, log_callback=None) -> bool:
    """Translate selected subtitle files using gemini-srt-translator."""
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
            
            # Build command - only use -k flag if API key is NOT in environment variable
            # (gst will automatically use GEMINI_API_KEY or GST_API_KEY if set)
            base_cmd = ["translate", "-i", str(og_file), "-l", "English", "-o", str(srt_file)]
            
            # Only pass -k if we have a non-env API key (from config)
            if not env_api_key and final_api_key:
                base_cmd.extend(["-k", final_api_key])
            
            # Handle Python module format (e.g., "python3 -m gemini_srt_translator")
            if " -m " in gst_cmd:
                cmd_parts = gst_cmd.split() + base_cmd
            else:
                cmd_parts = [gst_cmd] + base_cmd
            
            # Use Popen to stream output in real-time
            process = subprocess.Popen(
                cmd_parts,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr into stdout
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Stream output line by line
            output_lines = []
            while True:
                line_output = process.stdout.readline()
                if not line_output:
                    break
                
                line_output = line_output.strip()
                if line_output:
                    output_lines.append(line_output)
                    # Log translation progress
                    if log_callback:
                        log_callback(f"    {line_output}")
            
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
                success_count += 1
                if log_callback:
                    log_callback(f"  ✓ Translated: {srt_file.name}")
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
                 watermark_path: str, resolution: str, use_watermarks: bool = True, progress_callback=None, log_callback=None) -> bool:
    """Process selected video files: burn subtitles, add watermark (if enabled), resize."""
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
        
        # Check for subtitle file in multiple locations (matching bash script behavior)
        # 1. Same directory as video file (preferred, matches bash scripts)
        srt_file = video_file.parent / f"{base}.srt"
        srt_location = "video directory"
        
        # 2. Fall back to subtitles_dir if not found
        if not srt_file.exists():
            srt_file = subtitles_dir / f"{base}.srt"
            srt_location = "subtitles directory"
        
        out_file = output_dir / f"{base}.mp4"
        
        if progress_callback:
            progress_callback(idx, total, video_file.name)
        
        if out_file.exists():
            if log_callback:
                log_callback(f"Skipping {video_file.name} - output file already exists: {out_file.name}")
            continue
        
        if not srt_file.exists():
            if log_callback:
                log_callback(f"Skipping {video_file.name} - subtitle file not found")
                log_callback(f"  Checked: {video_file.parent / f'{base}.srt'}")
                log_callback(f"  Checked: {subtitles_dir / f'{base}.srt'}")
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
                log_callback(f"  Audio: {audio_channels} channels detected, converting to stereo (2.0)")
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
                    
                    if log_callback and should_update:
                        # Only log progress every few seconds to avoid spam
                        if percentage is not None:
                            progress_msg = f"    Progress: {percentage:.1f}%"
                            if eta_str:
                                progress_msg += f" (ETA: {eta_str})"
                            log_callback(progress_msg)
                        else:
                            log_callback(f"    Progress: {', '.join(progress_info)}")
                        last_progress_time = current_time
                    
                    # Update progress callback with enhanced filename including percentage
                    if progress_callback and should_update and percentage is not None:
                        # Include percentage in filename for display
                        enhanced_filename = f"{video_file.name} ({percentage:.1f}%)"
                        progress_callback(idx, total, enhanced_filename)
                
                elif "Error" in line or "error" in line.lower() or "failed" in line.lower():
                    # Log errors immediately
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


def remux_mkv_with_srt_batch(folder_path: Path, progress_callback=None, log_callback=None) -> bool:
    """Batch remux MKV files with matching SRT files."""
    if not folder_path.exists():
        if log_callback:
            log_callback(f"Error: Folder not found: {folder_path}")
        return False
    
    mkv_files = sorted(folder_path.glob("*.mkv"))
    
    if not mkv_files:
        if log_callback:
            log_callback("No MKV files found in folder.")
        return False
    
    success_count = 0
    total = len(mkv_files)
    
    for idx, mkv_file in enumerate(mkv_files, start=1):
        base = mkv_file.stem
        # Try to find matching SRT file
        # First try exact match, then try without _01, _02 suffixes (LosslessCut scenes)
        srt_file = folder_path / f"{base}.srt"
        if not srt_file.exists():
            # Remove _01, _02 suffixes that LosslessCut adds to scenes
            base_clean = re.sub(r'_(\d+)$', '', base)
            srt_file = folder_path / f"{base_clean}.srt"
        
        if progress_callback:
            progress_callback(idx, total, mkv_file.name)
        
        if not srt_file.exists():
            if log_callback:
                log_callback(f"Skipping {mkv_file.name} - no matching SRT file found")
            continue
        
        output_file = folder_path / f"{base}_remuxed.mkv"
        
        if output_file.exists():
            if log_callback:
                log_callback(f"Skipping {mkv_file.name} - remuxed file already exists")
            continue
        
        if log_callback:
            log_callback(f"Remuxing: {mkv_file.name} + {srt_file.name}")
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(mkv_file),
            "-i", str(srt_file),
            "-c", "copy",
            "-c:s", "srt",
            str(output_file)
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
                if "Stream #" in line or "Subtitle:" in line or "Output #" in line:
                    if log_callback:
                        log_callback(f"    {line}")
                elif "Error" in line or "error" in line.lower():
                    if log_callback:
                        log_callback(f"    ⚠ {line}")
            
            # Wait for process to complete
            returncode = process.wait()
            
            if returncode == 0 and output_file.exists():
                success_count += 1
                if log_callback:
                    log_callback(f"  ✓ Remuxed: {output_file.name}")
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
                log_callback(f"  ✗ Exception while remuxing {mkv_file.name}: {e}")
                log_callback(f"    Traceback: {traceback.format_exc()}")
    
    if log_callback:
        log_callback(f"\nRemux complete. Remuxed {success_count}/{total} files.")
    
    return success_count > 0


def transcribe_video(video_path: Path, language_code: str, model: str, progress_callback=None, log_callback=None) -> bool:
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
            log_callback(f"Language: {language_code}, Model: {model}")
        
        # Run the script with video path, language code, and model as arguments
        result = subprocess.run(
            ["bash", str(script_path), str(video_path), language_code, model],
            capture_output=True,
            text=True
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
    
    def run(self):
        """Execute the script function."""
        def log_callback(msg):
            self.log_message.emit(msg)
        
        def progress_callback(current, total, filename):
            self.progress_update.emit(current, total, filename)
        
        self.kwargs['log_callback'] = log_callback
        self.kwargs['progress_callback'] = progress_callback
        try:
            result = self.script_func(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
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
        Path("/Users/kszxvd/dna/venv/bin/gst"),
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
        self.gst_installed = check_python_package("gemini_srt_translator")
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
        
        html += "<p><b>○ OPTIONAL</b> - Widevine Proxy 2 (Browser extension)</p>"
        html += "<p style='margin-left: 20px; color: #666;'>Install as browser extension - Needed for capturing download commands</p>"
        
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
        See <b>batchdownloader_guide.md</b> for how to extract commands from Widevine Proxy 2.</p>
        
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
        LosslessCut isn't installed on your computer. Download it from https://github.com/mifi/lossless-cut and install it 
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
        
        <div class="version">Version 8</div>
        
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
        
        # Whisper Model Selection
        whisper_info = QLabel(
            "Turbo is the best model for accuracy and speed, but it's also the largest (~1.5 GB). "
            "The model will be downloaded automatically on first use."
        )
        whisper_info.setWordWrap(True)
        whisper_info.setStyleSheet("color: #666;")
        layout.addRow("", whisper_info)
        
        self.whisper_model_combo = QComboBox()
        self.whisper_model_combo.addItems(["tiny", "base", "small", "medium", "large", "turbo"])
        current_model = self.config.get("whisper_model", "turbo")
        index = self.whisper_model_combo.findText(current_model)
        if index >= 0:
            self.whisper_model_combo.setCurrentIndex(index)
        else:
            self.whisper_model_combo.setCurrentText("turbo")
        layout.addRow("Whisper Model:", self.whisper_model_combo)
        
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
        self.config["watermark_720p"] = self.watermark_720p_input.text()
        self.config["watermark_1080p"] = self.watermark_1080p_input.text()
        self.config["use_watermarks"] = self.use_watermarks_checkbox.isChecked()
        self.config["whisper_model"] = self.whisper_model_combo.currentText()
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
        self.remux_folder_path = None
        
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
        layout = QVBoxLayout()
        central_widget.setLayout(layout)
        
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
        version_label = QLabel('version 8.1.1 "Torre de Babel"')
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
        
        layout.addLayout(header_layout)
        
        # Download section
        download_group = QGroupBox("DOWNLOAD")
        download_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        download_layout = QVBoxLayout()
        download_label = QLabel("Commands (paste here, one per line):")
        download_layout.addWidget(download_label)
        
        self.commands_text = QTextEdit()
        self.commands_text.setPlaceholderText("Episode 1: N_m3u8DL-RE \"https://...\" --key ...\nEpisode 2: N_m3u8DL-RE \"https://...\" --key ...")
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
        
        # Remux section
        remux_group = QGroupBox("REMUX")
        remux_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        remux_layout = QHBoxLayout()
        remux_folder_btn = QPushButton("Select folder...")
        remux_folder_btn.clicked.connect(self.select_remux_folder)
        self.remux_folder_label = QLabel("No folder selected")
        remux_btn = QPushButton("Batch remux MKV + SRT")
        remux_btn.clicked.connect(self.remux_batch)
        remux_layout.addWidget(remux_folder_btn)
        remux_layout.addWidget(self.remux_folder_label)
        remux_layout.addWidget(remux_btn)
        remux_group.setLayout(remux_layout)
        layout.addWidget(remux_group)
        
        # Transcribe section
        transcribe_group = QGroupBox("TRANSCRIBE")
        transcribe_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        transcribe_layout = QHBoxLayout()
        transcribe_btn = QPushButton("Transcribe video...")
        transcribe_btn.clicked.connect(self.transcribe_video)
        transcribe_layout.addWidget(transcribe_btn)
        transcribe_group.setLayout(transcribe_layout)
        layout.addWidget(transcribe_group)
        
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
    
    def run_script(self, script_func, *args, **kwargs):
        """Run a script in a worker thread."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Busy", "Another operation is already running.")
            return
        
        # Determine operation type from function name
        func_name = script_func.__name__
        operation_names = {
            "download_episodes": "Downloading episodes",
            "extract_subtitles": "Extracting subtitles",
            "clean_subtitles": "Cleaning subtitles",
            "translate_subtitles": "Translating subtitles",
            "process_video": "Processing videos",
            "remux_mkv_with_srt_batch": "Remuxing videos",
            "transcribe_video": "Transcribing video"
        }
        self.current_operation = operation_names.get(func_name, "Processing")
        
        # Show progress section
        self.progress_group.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        self.progress_operation_label.setText(f"{self.current_operation}...")
        self.progress_file_label.setText("")
        self.progress_counter_label.setText("")
        self.update_progress_bar_color()
        
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
        if success:
            self.log("✓ Operation completed successfully.")
        else:
            self.log("✗ Operation failed. Check log for details.")
    
    def download_episodes(self):
        """Download episodes."""
        commands_text = self.commands_text.toPlainText()
        if not commands_text.strip():
            QMessageBox.warning(self, "Error", "Please paste commands in the text area.")
            return
        
        output_dir = get_downloads_dir()
        self.log(f"Starting download to: {output_dir}")
        
        # Create a wrapper that adds detection after download
        def download_with_detection(commands_text, output_dir, progress_callback=None, log_callback=None):
            result = download_episodes(commands_text, output_dir, progress_callback, log_callback)
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
        
        self.run_script(download_with_detection, commands_text, output_dir)
    
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
        
        self.log(f"Starting subtitle translation for {len(file_paths)} file(s)...")
        self.run_script(translate_subtitles, file_paths, api_key)
    
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
        
        self.log(f"Starting video processing ({resolution}p) for {len(file_paths)} file(s)...")
        self.run_script(
            process_video, file_paths, subtitles_dir, output_dir,
            watermark_path, resolution, use_watermarks
        )
    
    def open_lossless_cut(self):
        """Open video file in LosslessCut."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File to Open in LosslessCut",
            str(get_downloads_dir()),
            "Video Files (*.mkv *.mp4 *.mov);;All Files (*)"
        )
        
        if file_path:
            video_path = Path(file_path)
            video_type, duration = detect_episode_or_scene(video_path)
            
            if duration:
                type_label = "Episode" if video_type == "episode" else "Scene"
                self.log(f"Opening {video_path.name} in LosslessCut ({type_label}, {duration:.1f} min)")
            else:
                self.log(f"Opening {video_path.name} in LosslessCut")
            
            open_in_lossless_cut(video_path, log_callback=self.log)
    
    def select_remux_folder(self):
        """Select folder for remuxing."""
        folder_path = QFileDialog.getExistingDirectory(
            self, "Select Folder with MKV and SRT Files",
            str(get_downloads_dir())
        )
        
        if folder_path:
            self.remux_folder_path = Path(folder_path)
            self.remux_folder_label.setText(f"Folder: {self.remux_folder_path.name}")
            self.log(f"Selected remux folder: {self.remux_folder_path}")
    
    def remux_batch(self):
        """Batch remux MKV files with SRT files."""
        if not hasattr(self, 'remux_folder_path') or not self.remux_folder_path:
            QMessageBox.warning(self, "Error", "Please select a folder first.")
            return
        
        if not self.remux_folder_path.exists():
            QMessageBox.warning(self, "Error", "Selected folder does not exist.")
            return
        
        self.log(f"Starting batch remux in: {self.remux_folder_path}")
        self.run_script(remux_mkv_with_srt_batch, self.remux_folder_path)
    
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
            
            # Get model from config
            config = load_config()
            model = config.get("whisper_model", "turbo")
            
            self.log(f"Starting transcription of: {video_path.name}")
            lang_display = "Auto-detect" if language_code == "auto" else language_code
            self.log(f"Language: {lang_display}, Model: {model}")
            
            # Run transcription with language and model
            def transcribe_with_params(video_path, language_code, model, progress_callback=None, log_callback=None):
                return transcribe_video(video_path, language_code, model, progress_callback, log_callback)
            
            self.run_script(transcribe_with_params, video_path, language_code, model)


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
