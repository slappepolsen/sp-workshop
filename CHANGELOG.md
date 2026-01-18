# Changelog


The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

...

## [8.1.0] "Torre de Babel" - 2026-01-18

### Added
- Cross-platform path quoting with `quote_path()` function (fixes Windows CMD single-quote issue)
- Cross-platform temp directory with `get_temp_dir()` function (replaces hardcoded `/tmp`)
- Cross-platform app detection with `get_app_executable()` function
- Platform-specific executable paths for VLC, LosslessCut, and SubtitleEdit
- Platform-specific FFmpeg installation instructions in setup wizard

### Changed
- `open_folder_in_finder()` renamed to `open_folder_in_explorer()` with Windows/Linux support
- `open_in_lossless_cut()` now works on Windows and Linux (runs executable directly)
- `check_app_exists()` now uses `get_app_executable()` for cross-platform detection
- N_m3u8DL-RE download command now uses proper quoting for Windows compatibility

### Fixed
- Windows path concatenation error when downloading episodes (single quotes in `--save-dir` argument)
- Windows temp directory error (`/tmp` doesn't exist on Windows)
- "Open Downloads/Subtitles/Output folder" buttons now work on Windows (Explorer) and Linux (xdg-open)

## [8.0.0] "Torre de Babel" - 2026-01-18

### Added
- Language selection dialog (`LanguageDialog`) for transcription with 14 curated languages + auto-detect
- Native language names in dropdown (e.g., "French (Français)", "Japanese (日本語)")
- Whisper model selection dropdown in Settings (tiny, base, small, medium, large, turbo)
- Whisper model description explaining turbo is best but largest (~1.5 GB)
- API key link to Google AI Studio in Settings (clickable)
- Environment variable support for API keys (`GEMINI_API_KEY`, `GST_API_KEY`)
- Legacy API key input with security note
- App name header with lesbian flag gradient background
- Custom `OutlinedLabel` class for text with black outline effect
- Version label below header ("version 8.0.0 Torre de Babel")
- Bold section headers (DOWNLOAD, SUBTITLES, PROCESS VIDEO, REMUX, TRANSCRIBE, LOG OUTPUT)
- App icon and Twitter link in About dialog footer
- Maximized window height to screen's available height
- Distribution package with source code and macOS executable
- `sync_to_dist.sh` script for syncing changes to distribution folder
- `build_executables.sh` script for building platform executables
- `QUICK_START.md` simplified getting started guide
- Build instructions for Windows and Linux executables

### Changed
- `transcribe_video()` now accepts `language_code` and `model` parameters
- `whisper_auto.sh` accepts language and model as command-line arguments
- Output SRT filename now matches input video filename
- Temporary `.wav` file removed after transcription
- Settings, About, and FAQ dialogs widened to 700px
- Dialog fonts standardized to Arial 13pt
- FAQ dialog improved formatting and readability
- About dialog streamlined (removed "What it does" section)
- Reduced Whisper log output verbosity

### Fixed
- Duplicate log output during transcription
- Language dialog scrolling (limited to 12 visible items)
- Portuguese entry updated to "Portuguese (Português - BR/PT)"
- FFmpeg verbose output suppressed in transcription

## [7.0.0] - 2026-01-17

### Added
- About dialog displaying app name, version, credits, purpose, and features
- "About" button in top bar alongside FAQ and Settings

### Changed
- About button styled with dark pink color (#b42075) matching other top bar buttons

## [6.0.0] - 2026-01-16

### Added
- Application icon support with `get_app_icon()` function
- macOS native `.icns` icon format support (preferred)
- Fallback to `.png` icon format if `.icns` not available
- Window icon display for both application-wide and window-specific icons
- Absolute path support for reliable icon loading

## [5.0.0] - 2026-01-15

### Added
- Detailed progress display section with dedicated "PROGRESS" QGroupBox
- Operation label showing current operation type
- File label showing current file being processed
- Counter label displaying "X of Y" file counter
- Real-time percentage calculation and display
- Estimated time remaining (ETA) calculation and display
- Color-coded progress bar that changes based on operation type
- Real-time FFmpeg output streaming using `subprocess.Popen`
- FFmpeg progress parsing from stderr (frame, time, speed)
- Throttled progress updates (every 2 seconds) to avoid log spam
- `get_video_duration_seconds()` function for percentage calculation
- `parse_ffmpeg_time()` function to parse FFmpeg time format
- `format_eta()` function for human-readable ETA strings
- `update_progress_bar_color()` function for dynamic progress bar coloring

### Changed
- `process_video()` now uses `subprocess.Popen` instead of `subprocess.run` for real-time streaming
- `on_progress_update()` enhanced to parse percentage from filename string
- Progress bar styled with lesbian flag color gradient

### Fixed
- Hidden FFmpeg output that made video processing appear slow
- Improved subtitle file detection (now checks video directory first)
- Enhanced error reporting with full FFmpeg errors and exact commands

## [4.0.0] - 2026-01-14

### Added
- Setup wizard (`SetupWizard`) shown on first app launch
- Automatic installation check for required components (PyQt5, FFmpeg, N_m3u8DL-RE, etc.)
- Visual status indicators (✓ INSTALLED, ✗ NOT FOUND, ○ OPTIONAL)
- Detailed installation instructions for missing components
- Clickable links that open in browser
- Skip setup option for users who want to configure later
- Setup completion tracking in config
- FAQ dialog (`FAQDialog`) with comprehensive help content
- "FAQ" button in top bar
- File picker for selecting SRT files to translate (replaces directory-based selection)
- File picker for selecting video files to process (replaces directory-based selection)
- Multiple file selection support
- Watermark toggle checkbox in Settings
- Dynamic UI that disables watermark fields when watermarks are off
- `check_python_package()` function to check if Python package is installed
- `check_command_exists()` function to check if command-line tool exists
- `check_app_exists()` function to check if macOS app exists
- Enhanced `find_gst_command()` to search multiple locations

### Changed
- `translate_subtitles()` now accepts list of selected files instead of directory
- `process_video()` now accepts list of selected files and `use_watermarks` parameter
- Translation and processing operations now use file pickers instead of directory-based selection

### Removed
- Directory-based file selection for translation and processing operations

## [3.0.0] - 2026-01-13

### Added
- Lesbian flag color scheme for all buttons
- Color-coded button groups:
  - DOWNLOAD section: Red (#df4300)
  - SUBTITLES section: Orange (#f48a32)
  - PROCESS VIDEO section: Light Orange (#ffab68)
  - REMUX section: Pink (#dc7bb3)
  - TRANSCRIBE section: Purple (#c46ea1)
  - Settings/FAQ buttons: Dark Pink (#b42075)
- Hover effects with 15% darker color
- `darken_color()` function to darken hex colors by percentage
- `apply_button_style()` function for styled buttons with hover effects
- `apply_lesbian_flag_styles()` function to apply color scheme to all buttons
- Initial FAQ dialog implementation (placeholder)

### Changed
- Complete visual redesign with unified color-coded sections
- Uses QStyleFactory.Fusion style for better stylesheet support on macOS

## [2.0.0] - 2026-01-12

### Added
- Lossless Cut integration with "Open in Lossless Cut..." button in DOWNLOAD section
- Auto-detection of Lossless Cut installation location
- Episode/scene auto-detection based on video duration using `ffprobe`
- 7-minute threshold for episode vs scene classification
- Episode/scene detection displayed when adding videos, after downloads, and when opening in Lossless Cut
- Remux feature with new "REMUX" section
- Batch remuxing of MKV files with matching SRT files
- Smart matching that handles Lossless Cut scene prefixes (`_01`, `_02`, etc.)
- Transcription feature with new "TRANSCRIBE" section
- File picker for selecting video/audio files to transcribe
- Integration with `whisper_auto.sh` script
- `get_video_duration()` function to get video duration in minutes
- `detect_episode_or_scene()` function returning ('episode'/'scene', duration)
- `open_in_lossless_cut()` function to open video in Lossless Cut app
- `remux_mkv_with_srt_batch()` function for batch remuxing
- `transcribe_video()` function wrapping whisper_auto.sh
- `get_remuxed_dir()` function for remuxed files directory

### Changed
- `add_videos()` now shows episode/scene detection after copying files
- `download_episodes()` now shows episode/scene detection after downloads complete

## [1.1.0] - 2026-01-11

### Removed
- Project-based folder structure
- Project selector dropdown (QComboBox)
- Project management functionality

### Changed
- Simplified to flat directory structure (`downloads/`, `subtitles/`, `output/`)
- Streamlined UI with cleaner, more focused interface
- Improved file handling and management

## [1.0.0] - 2026-01-10

### Added
- Batch download episodes from commands text
- Extract subtitles from MKV files
- Clean subtitle color tags (VTT → SRT conversion)
- Translate subtitles using Gemini SRT Translator
- Process videos: burn subtitles + watermark at 720p or 1080p
- Manual video file addition
- Open folder buttons for easy access
- Real-time progress tracking and log output
- Centralized configuration management
- PyQt5 GUI application
- Single-file implementation
- Worker threads for non-blocking operations
- Progress bars and status updates
