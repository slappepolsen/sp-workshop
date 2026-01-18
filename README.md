# SP Workshop

Video Processing Studio - A GUI application for video/subtitle processing, translation, and more.

**Version 8.0.0 "Torre de Babel"**

## Features

- Batch download episodes from streaming services
- Extract and clean subtitles from video files
- Translate subtitles using Google Gemini AI
- Burn subtitles into videos with optional watermarks
- Remux MKV files with separate SRT subtitles
- Transcribe audio/video using Whisper AI

## Installation

### Option 1: Download Executable (Recommended)

Go to the [Releases](../../releases) page and download the executable for your platform:
- **macOS**: `SP_Workshop-macOS.zip`
- **Windows**: `SP_Workshop-Windows.zip`
- **Linux**: `SP_Workshop-Linux.tar.gz`

### Option 2: Run from Source

Requires Python 3.9+

```bash
pip install -r requirements.txt
python3 video_app_v8.py
```

## External Dependencies

The app requires these external tools (not included):

- **FFmpeg** - For video/subtitle processing
  - macOS: `brew install ffmpeg`
  - Windows: [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
  - Linux: `sudo apt install ffmpeg`

- **N_m3u8DL-RE** (optional) - For batch downloading
  - [github.com/nilaoda/N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE/releases)

- **Google Gemini API Key** (for translation)
  - Get yours at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

## Documentation

- [SETUP.md](SETUP.md) - Detailed setup guide
- [CHANGELOG.md](CHANGELOG.md) - Version history

## Building

Executables are automatically built via GitHub Actions for all platforms.

To build manually:
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "SP_Workshop" video_app_v8.py
```

## License

Made with ❤️ by [@slappepolsen](https://x.com/slappepolsen)
