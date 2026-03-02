# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]
- ...

## [10.4.0-alpha.2] - 2026-03-02

### Fixed
- Whisper CPP: stop downloading broken ggml-metal.metal (caused ggml-common.h errors); use Metal only when ggml-metal.metal exists next to the binary

## [10.4.0-alpha.1] - 2025-03-01

### Added
- Transcribe (Whisper CPP) button: alternative transcription using whisper.cpp. Faster, built-in VAD. Metal/GPU support on macOS (auto-downloads ggml-metal.metal). Auto-downloads models on first use. Config: whisper_cpp_path, whisper_cpp_model_dir, whisper_cpp_model, whisper_cpp_extra_args.
- On-demand pip install: When a feature needs a missing dependency (Whisper CPP, Transcribe longer video, Translate subtitles), the app now offers to install it via pip. User can accept or install manually.

### Changed
- Subtitle translation: cleaner gst log output (dedupe progress/errors, strip ANSI, suppress RequestsDependencyWarning), progress bar driven by line progress, API key pair switching when "All API quotas exceeded" (no 60s wait), --thinking-budget 0 to reduce malformed responses, partial/interrupted translation reported as "Partially translated (interrupted)", ANSI stripping for "Last output lines" in translation failures.
- Batch download: ANSI stripping for "Last output lines" when download fails.
- README: troubleshooting updates (python -m pip, Python 3.14).
- BENCHMARKS.md and run.sh added to .gitignore.
- Simplify comments in app.py.

### Fixed
- Remux tab: ffprobe for track indices, avoid -c copy + -c:s conflic

## [10.3.2] - 2026-02-28

### Added
- Downloads directory as third subtitle search location when burning subtitles

### Fixed
- Setup Wizard crash on startup (QCheckBox setWordWrap AttributeError)
- FFmpeg subtitles filter failing with absolute paths (e.g. videos outside VideoProcessing)

## [10.3.1] - 2026-02-28

### Added
- Feature selection step in Setup Wizard
- Automatic pip installer (non-blocking UI) for optional dependencies
- Quality selector (480p/720p/1080p/4K/best) for batch downloads
- Version-aware setup wizard re-run on app update
- Detection of previous installation with optional reset
- Support for torch, torchaudio, torchcodec for long transcription
- Media directory support with backward-compatible icon resolution

### Changed
- Batch download debug log now written to `VideoProcessing/logs` instead of the downloads folder.
- `get_logs_dir()` helper for the logs directory.
- Reorganized media assets into `media/`
- Improved debug logging (ANSI stripping and progress filtering)
- Translator now uses `--batch-size 30`
- Setup wizard now feature-aware for required dependencies
- Updated README with extended transcription dependency instructions

### Removed
- Manual “Add videos…” button in Batch Download tab
- - `batchdownloader_guide.md`; content merged into the external rentry page. README Documentation section and build workflow updated accordingly.

### Fixed
- Prevent transcription when language is set to "auto"
- Improved missing dependency messages for long transcription

## [10.3.0] - 2026-02-25

### Added

- Transcription on Windows without bash. Standard transcription now runs in Python with `_get_whisper_python()` instead of `whisper_auto.sh`, so Git for Windows is no longer required.
- `_get_whisper_python()` helper to create and use `~/whisper-env`, install Whisper and PyTorch if missing, and return the Python path for both Windows and Unix.
- Batch download debug log: full N_m3u8DL-RE output written to `VideoProcessing/logs/_batch_download_debug_YYYYMMDD_HHMMSS.log` for troubleshooting hangs or failures.

### Changed

- `transcribe_video()` no longer calls `whisper_auto.sh` or bash; it uses subprocess with ffmpeg and Whisper directly.
- Platform-specific venv paths: `Scripts/python.exe` on Windows, `bin/python` on Unix for the whisper environment.
- Update README: note under "Run the app" for older versions (before 10.0.0) that the main file may be `video_app_v8.py`.

## [10.2.0] - 2026-02-25

### Added

- Support for many Gemini API keys for subtitle translation.
- `api_keys` config (list) replacing `api_key` and `api_key2`; migration from existing keys in `load_config()`.
- Quota-limit retry: on 429, RESOURCE_EXHAUSTED, quota, rate limit, or exhausted errors from gst, retry the same file with the next key pair.
- `_is_quota_limit_error()` helper detecting quota/rate-limit patterns in gst output.
- `_get_key_pairs()` helper building (primary, secondary) key pairs for gst from env and config.
- Settings UI: dynamic API key list with "Add another key" button and per-key remove button (minimum one key).
- Partial output file removed before retry so gst can re-run from scratch.
- Log message "Retrying with next API key(s)..." when switching to a new key pair.

### Changed

- `translate_subtitles()` now accepts `api_keys: List[str]` and legacy `api_key`/`api_key2` for backward compatibility.
- Translation logic pairs keys for gst (primary via `GEMINI_API_KEY` env, secondary via `-k2`).
- Setup wizard API key checkbox now considers `api_keys` when deciding whether keys are configured.

## [10.1.0] - 2026-02-25

### Added

- Flexible download naming: Mode (Episode(s) | Movie), optional Name field, Use S01E02 checkbox with Season spinbox, Items field for episode numbers or ranges.
- `build_save_names()` and `_sanitize_filename()` helpers for output filenames.

### Changed

- Batch downloader UI replaces Episodes spec with Mode, Name, S01E02, Season, and Items controls.
- Button text "Batch download episodes" renamed to "Batch download".
- `batchdownloader_guide.md` updated with naming options and examples.

## [10.0.1] - 2026-02-25

### Restored

- ISO 639 subtitle suffixes for translation and video processing (.eng.srt, .fra.srt format).

## [10.0.0] - 2026-02-23

### Added

- Transcribe (anti-hallucination): VAD-assisted transcription for files over ~5 minutes. Uses Silero VAD to split audio into short speech segments, then transcribes each with Whisper.

### Changed

- Renamed `video_app_v8.py` to `app.py`.

### Removed

- Transcribe time range (replaced by anti-hallucination transcription).
- ISO 639 subtitle suffixes from translation and video processing.

## [9.2.2] - 2026-01-23

### Added

- "How to get commands" link in Download section opening external instructions.
- Bare URL support: when pasting just a URL (no headers or keys), app auto-adds Referer/Origin headers for CDN compatibility.

### Changed

- Simplified Download section: unified command processing (one full command per line).
- Batch downloader now uses `--select-audio all` and `--select-subtitle all` for generic track selection.
- `batchdownloader_guide.md` streamlined to point to external instructions.
- Setup wizard and FAQ updated to reference "How to get commands" for download instructions.

### Fixed

- Subtitle translation no longer freezes on "new version available" prompt (`--skip-upgrade` and `stdin=subprocess.DEVNULL`).

## [9.2.1] - 2026-01-21

### Changed

- Installation instructions reorganized into OS-specific sections (macOS, Windows, Linux) for better clarity.
- Linux installation section simplified for CLI-familiar users.
- Virtual environment setup (`.venv`) added to all installation instructions as best practice.
- Installation prerequisites updated with Python PATH requirement and download link to releases.

### Fixed

- Step numbering corrected in macOS installation section.

## [9.2.0] - 2026-01-21

### Added

- Remuxing tab with tree-based file management interface.
- Per-file track selection with checkboxes for video, audio, and subtitle tracks.
- Track analysis using `mkvmerge` and `ffprobe` to display codec, language, channels, and resolution.
- `MediaInfoDialog` for detailed media file information display.
- Right-click context menu on tracks for "Show Track Info" and "Modify Track Properties".
- Track modification dialog with language selection per track.
- Per-file output format selection (MKV/MP4) in remuxing interface.
- External subtitle file browser with per-file selection (defaults to subtitles directory).
- Individual "Remux This File" button for per-file remuxing operations.
- Batch remuxing of selected files with individual configurations.
- Audio channel splitting functionality (`split_audio_channels()`).
- `analyze_tracks()` function for comprehensive track detection.
- `remux_file_with_tracks()` function for per-file remuxing with track selection.
- Output format dropdown in Transcription tab (SRT, VTT, TXT, TSV, JSON, All Formats).
- Whisper Model selector in Transcription tab with auto-save functionality.
- Batch file opening in LosslessCut (multiple files to single instance).
- File selection manager for remuxing (replaces folder-based selection).

### Changed

- Remuxing functionality moved from section to dedicated "Remuxing" tab.
- Whisper Model setting moved from Settings dialog to Transcription tab.
- `whisper_auto.sh` accepts 4th argument for `output_format` (replaces hardcoded SRT).
- `transcribe_video()` and `transcribe_video_time_range()` now accept `output_format` parameter.
- External subtitle file browser defaults to `VideoProcessing/subtitles` directory.
- `open_in_lossless_cut()` now accepts list of files for batch opening.
- Main window tab structure: "Subtitles" (renamed from "Main"), "Transcription", "Remuxing".

### Fixed

- CHANGELOG documentation updated to reflect Whisper Model location change.

## [9.1.3] - 2026-01-21

### Added

- Whisper Advanced Options dialog with 15 configurable transcription parameters.
- Subtitle formatting presets (Standard, Narrow, Wide, Custom) with manual line width/count controls.
- Advanced Whisper settings: beam_size, patience, best_of, temperature, no_speech_threshold, compression_ratio_threshold, logprob_threshold.
- Context and prompting controls: condition_on_previous_text, initial_prompt.
- Word-level timestamps and highlight_words options.
- Time-range transcription feature for transcribing specific video segments.
- `TimeRangeTranscriptionDialog` with HH:MM:SS time pickers and timestamp adjustment option.
- SRT timestamp offset adjustment function for time-range transcriptions.
- Stop operation button with graceful shutdown (3-second timeout before force termination).
- Browser-style tab navigation with "Main" and "Transcription" tabs.
- Dedicated Transcription tab with file picker, language selection, and integrated logs.

### Changed

- Whisper options stored in `settings.json` under `whisper_options` dictionary.
- `whisper_auto.sh` accepts Whisper parameters via environment variables.
- `transcribe_video()` passes whisper options from config to bash script.
- Transcription functionality moved from section to dedicated tab.
- Main window uses `QTabWidget` for tab-based navigation.
- Worker thread enhanced with stop flag for operation cancellation.
- Transcribe button color changed to pink (#d168a3).

## [9.1.2] - 2026-01-21

### Fixed

- Gemini API key repeated prompts during subtitle translation batch processing.
- FFmpeg eac3/ac3 audio decoder errors when processing Dolby Atmos streams.
- Decoder packet submission errors now filtered from log output.

### Changed

- Video processing progress display now shows only visual progress bar (removed text-based progress spam).
- Audio conversion log message now mentions compatibility benefit.
- Gemini API key now passed as subprocess environment variable instead of command-line argument.
- FFmpeg error handling improved with `-err_detect ignore_err`, `-fflags +discardcorrupt+genpts`, and `-max_error_rate 1.0` flags.

## [9.1.0] - 2026-01-20

### Added

- Translation target language selection (8 languages: English, French, Spanish, Catalan, German, Italian, Portuguese, Dutch).
- ISO 639 language suffix support (.eng.srt, .fra.srt, etc.) for VLC and Jellyfin auto-detection.
- Settings UI for configuring translation preferences with "Translation Target Language" dropdown and "Use ISO 639 language suffixes" checkbox.
- Smart subtitle filename handling that auto-replaces existing language suffixes (e.g., video.spa.srt → video.eng.srt).
- Video processor now matches ISO 639 suffixed subtitle files with priority for exact match first.
- `ISO_639_CODES` constant with 14 language mappings.

### Changed

- `translate_subtitles()` now accepts `target_language` and `use_iso639` parameters.
- `process_video()` now accepts `use_iso639` and `target_language` parameters for subtitle matching.
- Translation no longer hardcoded to English - uses user-selected target language.
- Subtitle matching logic enhanced to support multiple filename patterns (works with both video directory and subtitles directory).
- All changes are backward compatible (ISO 639 mode disabled by default).

## [9.0.0] - 2026-01-19

### Added

- Source selector dropdown in Download section.
- Episode range input with support for single episodes (`1`), ranges (`1-5`), multiple selections (`1,3,5`), and mixed (`1-3,5,7-10`).
- `SOURCE_SETTINGS` configuration for per-source language mappings.
- Dynamic placeholder text that changes based on selected source.
- `parse_episode_range()` helper function for parsing episode specifications.

### Changed

- Command format simplified: no longer requires "Episode X:" prefix.
- Commands are now auto-numbered based on episode specification.
- Language selection (audio/subtitles) is now dynamic based on source.
- Episode input field now accepts ranges instead of just starting number.

### Removed

- Hardcoded language tags from download function.

## [8.1.2] - 2026-01-19

### Added

- Whisper model detection to check if models already exist in cache directory.
- First-time user dialog asking if user already has a Whisper model installed.
- Auto-detection of existing Whisper models in default cache location (~/.cache/whisper/).
- User preference storage to avoid redundant model downloads.
- All documentation files now included in release packages (README.md, SETUP.md, CHANGELOG.md, batchdownloader_guide.md, LICENSE, requirements.txt, app.py, flowcharts.png).

## [8.1.1] - 2026-01-19

### Fixed

- Video stream not downloading when source has no 1080p option (changed `-sv res=1080` to `-sv best`).

## [8.1.0] - 2026-01-18

### Added

- Cross-platform path quoting with `quote_path()` function (fixes Windows CMD single-quote issue).
- Cross-platform temp directory with `get_temp_dir()` function (replaces hardcoded `/tmp`).
- Cross-platform app detection with `get_app_executable()` function.
- Platform-specific executable paths for VLC, LosslessCut, and SubtitleEdit.
- Platform-specific FFmpeg installation instructions in setup wizard.
- `open_folder_in_explorer()` function with Windows/Linux support (renamed from `open_folder_in_finder()`).
- `open_in_lossless_cut()` now works on Windows and Linux (runs executable directly).
- N_m3u8DL-RE download command now uses proper quoting for Windows compatibility.
- GitHub release.

### Fixed

- Windows path concatenation error when downloading episodes (single quotes in `--save-dir` argument).
- Windows temp directory error (`/tmp` doesn't exist on Windows).
- "Open Downloads/Subtitles/Output folder" buttons now work on Windows (Explorer) and Linux (xdg-open).

### Changed

- `check_app_exists()` now uses `get_app_executable()` for cross-platform detection.

## [8.0.0] - 2026-01-18

### Added

- Language selection dialog (`LanguageDialog`) for transcription with 14 curated languages + auto-detect.
- Native language names in dropdown (e.g., "French (Français)", "Japanese (日本語)").
- Whisper model selection dropdown in Transcription tab (tiny, base, small, medium, large, turbo).
- Whisper model description explaining turbo is best but largest (~1.5 GB).
- API key link to Google AI Studio in Settings (clickable).
- Environment variable support for API keys (`GEMINI_API_KEY`, `GST_API_KEY`).
- Legacy API key input with security note.
- App name header with lesbian flag gradient background.
- Custom `OutlinedLabel` class for text with black outline effect.
- Version label below header ("version 8.0.0 Torre de Babel").
- Bold section headers (DOWNLOAD, SUBTITLES, PROCESS VIDEO, REMUX, TRANSCRIBE, LOG OUTPUT).
- App icon and Twitter link in About dialog footer.
- Maximized window height to screen's available height.
- Distribution package with source code and macOS executable.
- `sync_to_dist.sh` script for syncing changes to distribution folder.
- `build_executables.sh` script for building platform executables.
- `QUICK_START.md` simplified getting started guide.
- Build instructions for Windows and Linux executables.

### Changed

- `transcribe_video()` now accepts `language_code` and `model` parameters.
- `whisper_auto.sh` accepts language and model as command-line arguments.
- Output SRT filename now matches input video filename.
- Temporary `.wav` file removed after transcription.
- Settings, About, and FAQ dialogs widened to 700px.
- Dialog fonts standardized to Arial 13pt.
- FAQ dialog improved formatting and readability.
- About dialog streamlined (removed "What it does" section).
- Reduced Whisper log output verbosity.

### Fixed

- Duplicate log output during transcription.
- Language dialog scrolling (limited to 12 visible items).
- Portuguese entry updated to "Portuguese (Português - BR/PT)".
- FFmpeg verbose output suppressed in transcription.

## [7.0.0] - 2026-01-17

### Added

- About dialog displaying app name, version, credits, purpose, and features.
- "About" button in top bar alongside FAQ and Settings.

### Changed

- About button styled with dark pink color (#b42075) matching other top bar buttons.

## [6.0.0] - 2026-01-16

### Added

- Application icon support with `get_app_icon()` function.
- macOS native `.icns` icon format support (preferred).
- Fallback to `.png` icon format if `.icns` not available.
- Window icon display for both application-wide and window-specific icons.
- Absolute path support for reliable icon loading.

## [5.0.0] - 2026-01-15

### Added

- Detailed progress display section with dedicated "PROGRESS" QGroupBox.
- Operation label showing current operation type.
- File label showing current file being processed.
- Counter label displaying "X of Y" file counter.
- Real-time percentage calculation and display.
- Estimated time remaining (ETA) calculation and display.
- Color-coded progress bar that changes based on operation type.
- Real-time FFmpeg output streaming using `subprocess.Popen`.
- FFmpeg progress parsing from stderr (frame, time, speed).
- Throttled progress updates (every 2 seconds) to avoid log spam.
- `get_video_duration_seconds()` function for percentage calculation.
- `parse_ffmpeg_time()` function to parse FFmpeg time format.
- `format_eta()` function for human-readable ETA strings.
- `update_progress_bar_color()` function for dynamic progress bar coloring.

### Changed

- `process_video()` now uses `subprocess.Popen` instead of `subprocess.run` for real-time streaming.
- `on_progress_update()` enhanced to parse percentage from filename string.
- Progress bar styled with lesbian flag color gradient.

### Fixed

- Hidden FFmpeg output that made video processing appear slow.
- Improved subtitle file detection (now checks video directory first).
- Enhanced error reporting with full FFmpeg errors and exact commands.

## [4.0.0] - 2026-01-14

### Added

- Setup wizard (`SetupWizard`) shown on first app launch.
- Automatic installation check for required components (PyQt5, FFmpeg, N_m3u8DL-RE, etc.).
- Visual status indicators (✓ INSTALLED, ✗ NOT FOUND, ○ OPTIONAL).
- Detailed installation instructions for missing components.
- Clickable links that open in browser.
- Skip setup option for users who want to configure later.
- Setup completion tracking in config.
- FAQ dialog (`FAQDialog`) with comprehensive help content.
- "FAQ" button in top bar.
- File picker for selecting SRT files to translate (replaces directory-based selection).
- File picker for selecting video files to process (replaces directory-based selection).
- Multiple file selection support.
- Watermark toggle checkbox in Settings.
- Dynamic UI that disables watermark fields when watermarks are off.
- `check_python_package()` function to check if Python package is installed.
- `check_command_exists()` function to check if command-line tool exists.
- `check_app_exists()` function to check if macOS app exists.
- Enhanced `find_gst_command()` to search multiple locations.

### Changed

- `translate_subtitles()` now accepts list of selected files instead of directory.
- `process_video()` now accepts list of selected files and `use_watermarks` parameter.
- Translation and processing operations now use file pickers instead of directory-based selection.

### Removed

- Directory-based file selection for translation and processing operations.

## [3.0.0] - 2026-01-13

### Added

- Lesbian flag color scheme for all buttons.
- Color-coded button groups (DOWNLOAD: Red, SUBTITLES: Orange, PROCESS VIDEO: Light Orange, REMUX: Pink, TRANSCRIBE: Purple, Settings/FAQ: Dark Pink).
- Hover effects with 15% darker color.
- `darken_color()` function to darken hex colors by percentage.
- `apply_button_style()` function for styled buttons with hover effects.
- `apply_lesbian_flag_styles()` function to apply color scheme to all buttons.
- Initial FAQ dialog implementation (placeholder).

### Changed

- Complete visual redesign with unified color-coded sections.
- Uses QStyleFactory.Fusion style for better stylesheet support on macOS.

## [2.0.0] - 2026-01-12

### Added

- Lossless Cut integration with "Open in Lossless Cut..." button in DOWNLOAD section.
- Auto-detection of Lossless Cut installation location.
- Episode/scene auto-detection based on video duration using `ffprobe`.
- 7-minute threshold for episode vs scene classification.
- Episode/scene detection displayed when adding videos, after downloads, and when opening in Lossless Cut.
- Remux feature with new "REMUX" section.
- Batch remuxing of MKV files with matching SRT files.
- Smart matching that handles Lossless Cut scene prefixes (`_01`, `_02`, etc.).
- Transcription feature with new "TRANSCRIBE" section.
- File picker for selecting video/audio files to transcribe.
- Integration with `whisper_auto.sh` script.
- `get_video_duration()` function to get video duration in minutes.
- `detect_episode_or_scene()` function returning ('episode'/'scene', duration).
- `open_in_lossless_cut()` function to open video in Lossless Cut app.
- `remux_mkv_with_srt_batch()` function for batch remuxing.
- `transcribe_video()` function wrapping whisper_auto.sh.
- `get_remuxed_dir()` function for remuxed files directory.

### Changed

- `add_videos()` now shows episode/scene detection after copying files.
- `download_episodes()` now shows episode/scene detection after downloads complete.

## [1.1.0] - 2026-01-11

### Changed

- Simplified to flat directory structure (`downloads/`, `subtitles/`, `output/`).
- Streamlined UI with cleaner, more focused interface.
- Improved file handling and management.

### Removed

- Project-based folder structure.
- Project selector dropdown (QComboBox).
- Project management functionality.

## [1.0.0] - 2026-01-10

### Added

- Batch download episodes from commands text.
- Extract subtitles from MKV files.
- Clean subtitle color tags (VTT → SRT conversion).
- Translate subtitles using Gemini SRT Translator.
- Process videos: burn subtitles + watermark at 720p or 1080p.
- Manual video file addition.
- Open folder buttons for easy access.
- Real-time progress tracking and log output.
- Centralized configuration management.
- PyQt5 GUI application.
- Single-file implementation.
- Worker threads for non-blocking operations.
- Progress bars and status updates.
