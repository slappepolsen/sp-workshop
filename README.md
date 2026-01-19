# SP Workshop

[![Build](https://img.shields.io/github/actions/workflow/status/slappepolsen/sp-workshop/build.yml?branch=main)](../../actions)
[![Release](https://img.shields.io/github/v/release/slappepolsen/sp-workshop)](../../releases)
[![Downloads](https://img.shields.io/github/downloads/slappepolsen/sp-workshop/total)](../../releases)
[![License](https://img.shields.io/github/license/slappepolsen/sp-workshop)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue)](https://www.python.org)
[![Platform](https://img.shields.io/badge/platform-macOS%20|%20Windows%20|%20Linux-lightgrey)](#installation)

Video Processing Studio - A GUI application for video/subtitle processing, translation, and more.

#### Intended users
SP Workshop is built for subtitle editors, translators, archivists, and  **anyone** determined to watch their favorite (WLW / Sapphic) shows or ships with subtitles in the language they actually want.

#### Skill level
Designed for non-technical users (too!). If you can download software on your laptop, you can use SP Workshop. No command-line experience required.

**Version 8.1.1 "Torre de Babel"**

## Features

- Batch download episodes from streaming services
- Extract and clean subtitles from video files
- Translate subtitles using Google Gemini
- Burn subtitles into videos with optional watermarks
- Remux MKV files with separate SRT subtitles
- Transcribe audio/video using Whisper

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
- [batchdownloader_guide.md](batchdownloader_guide.md) - How to extract download commands from Widevine Proxy 2
- [CHANGELOG.md](CHANGELOG.md) - Version history

## Building

Executables are automatically built via GitHub Actions for all platforms.

To build manually:
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "SP_Workshop" video_app_v8.py
```

## Support

I've received messages asking about donations - thank you, but I don't want any money! The best way to support this project is to try it out and let me know what you think. Your feedback is all I need :)

## License

This project is licensed under the [MIT License](LICENSE).

Made with ❤️ by [@slappepolsen](https://x.com/slappepolsen)

[![Follow](https://img.shields.io/twitter/follow/slappepolsen?style=social)](https://x.com/slappepolsen)
