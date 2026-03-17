# SP Workshop

[![Release](https://img.shields.io/github/v/release/slappepolsen/sp-workshop)](../../releases)
[![License](https://img.shields.io/github/license/slappepolsen/sp-workshop)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9--3.12-blue)](https://www.python.org)
[![Platform](https://img.shields.io/badge/platform-macOS%20|%20Windows%20|%20Linux-lightgrey)](#installation)

<img src="media/icon.png" width="80" height="80" alt="icon"/>

## Video processing studio GUI 🎬 

🌐 SP Workshop is a desktop GUI for extracting, translating, transcribing, and burning subtitles into videos.

🏳️‍🌈 It was created to make international WLW / sapphic content more accessible, but it works for any audiovisual media.

#### Intended users
SP Workshop is built for:

- Subtitle editors and translators
- Archivists and fandom preservation projects
- Anyone who wants subtitles in the language they actually want

## Features

| Function | Description |
|--------|-------------|
| **Download** | Batch download episodes using N_m3u8DL-RE, add local videos, open files in LosslessCut for trimming |
| **Subtitles** | Extract subtitles from MKV files, clean formatting, translate subtitles |
| **Process Video** | Burn subtitles into video with optional watermarks, output at 720p or 1080p |
| **Transcription** | Generate subtitles from audio using Whisper when no subtitles exist |
| **Remuxing** | Tree-based file and track view, add external SRT files, remux MKV or MP4, split audio tracks |


## Installation

### Prerequisites

- **Python 3.9–3.12** (3.12 recommended; 3.13+ causes Qt errors on macOS)
  Download from [python.org](https://www.python.org/downloads/) and make sure it is added to PATH during installation.

Download SP Workshop from:
👉 [GitHub Releases](https://github.com/slappepolsen/sp-workshop/releases)

Select **Source code (zip)** under Assets.

## macOS

1. Open **Terminal**
2. Navigate to the project folder
   ```bash
   cd path/to/sp-workshop
   ```
3. Create and activate a virtual environment  
   Use Python 3.12 to avoid Qt issues on macOS (`brew install python@3.12`).
   ```bash
   python3.12 -m venv .venv   # or python3 if 3.12 is default
   source .venv/bin/activate
   ```
4. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

5. Install FFmpeg (required; use ffmpeg-full for burn-in subtitles)
   ```bash
   brew install ffmpeg-full
   ```
   If using ffmpeg-full, set path in Settings > Tools to `/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg` (keg-only).
6. Install N_m3u8DL-RE (optional, for downloads)
   - Download from https://github.com/nilaoda/N_m3u8DL-RE/releases
   - Add the executable to your PATH
7. Run the app
   ```bash
   python3 app.py
   ```
   For older versions (before 10.0.0), the main file is called  `video_app_v8.py`. Use `python3 video_app_v8.py` or rename it to `app.py`.

## Windows

1. Open **Command Prompt**
2. Navigate to the project folder
   ```bash
   cd path\to\sp-workshop
   ```
3. Create and activate a virtual environment  
   Python 3.12 recommended.
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
4. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

5. Install FFmpeg and add it to PATH
6. Install N_m3u8DL-RE (optional, for downloads)
7. Run the app
   ```bash
   python app.py
   ```
   For older versions (before 10.0.0), the main file is called  `video_app_v8.py`. Use `python3 video_app_v8.py` or rename it to `app.py`.

## Linux

1. Create and activate a virtual environment  
   Python 3.12 recommended.
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
2. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

3. Install FFmpeg
   ```bash
   sudo apt install ffmpeg
   ```
4. Install N_m3u8DL-RE (optional)
5. Run the app
   ```bash
   python3 app.py
   ```
   For older versions (before 10.0.0), the main file is called  `video_app_v8.py`. Use `python3 video_app_v8.py` or rename it to `app.py`.

---


## License

This project is licensed under the [MIT License](LICENSE).

Made with ❤️ by [@slappepolsen](https://x.com/slappepolsen)

[![Follow](https://img.shields.io/twitter/follow/slappepolsen?style=social)](https://x.com/slappepolsen)

![Developer Banner 13](https://ishan-rest.vercel.app/svg/banner/dev13/slappepolsen)
