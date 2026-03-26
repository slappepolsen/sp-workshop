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

> **Note**
> During Python setup, keep the option to add Python to PATH enabled (wording varies by version and OS). This allows Terminal or Command Prompt to find `python` / `python3` when you run a command.

Download SP Workshop from:
👉 [GitHub Releases](https://github.com/slappepolsen/sp-workshop/releases)

> **Tip**
> On the page you are on, look at the right-hand side. Under **Releases**, you will see a version number (e.g., `10.3.0-alpha.2`) + a label **Latest**. Click on that.

Select **Source code (zip)** under **Assets**.

> **Note**
> After downloading, you will have a `.zip` file (for example `sp-workshop-10.3.0-alpha.2.zip`).
> Double-click it to unzip. This creates a folder with the same name (for example `sp-workshop-10.3.0-alpha.2`).
> Open this folder. You should see files like `app.py`, `requirements.txt`, and `README.md`.

## Easiest way to run (all OS)

You no longer need to run this every time:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Use the launcher instead. It will:
- create `.venv` automatically if missing
- install/update `requirements.txt` automatically when needed
- start `app.py` automatically

### One-click start

- **macOS:** double-click `Start_SP_Workshop.command`
- **Windows:** double-click `Start_SP_Workshop.bat`
- **Linux:** run `./Start_SP_Workshop.sh` (or double-click it in file manager if executable)

### Terminal command start (`spw`)

Pick your OS once below. After that, just type `spw` in terminal from anywhere.

## macOS

1. Open Terminal and go to the project once:
   ```bash
   cd /path/to/sp-workshop
   ```
2. Install FFmpeg (required):
   ```bash
   brew install ffmpeg-full
   ```
3. Add `sp-workshop` and `spw` commands:
   ```bash
   echo 'alias sp-workshop="bash \"/path/to/sp-workshop/scripts/run_sp_workshop.sh\""' >> ~/.zshrc
   echo 'alias spw="sp-workshop"' >> ~/.zshrc
   source ~/.zshrc
   ```
4. Run from anywhere:
   ```bash
   spw
   ```

## Windows

1. Install FFmpeg and add it to PATH (required): https://www.gyan.dev/ffmpeg/builds/
2. Open **PowerShell** and run:
   ```powershell
   Add-Content $PROFILE 'function sp-workshop { & "C:\path\to\sp-workshop\scripts\run_sp_workshop.ps1" }'
   Add-Content $PROFILE 'Set-Alias spw sp-workshop'
   . $PROFILE
   ```
3. Run from anywhere:
   ```powershell
   spw
   ```

If PowerShell blocks scripts, run this once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

## Linux

1. Install FFmpeg (Debian/Ubuntu example):
   ```bash
   sudo apt install ffmpeg
   ```
2. Add `sp-workshop` and `spw` commands:
   ```bash
   echo 'alias sp-workshop="bash \"/path/to/sp-workshop/scripts/run_sp_workshop.sh\""' >> ~/.bashrc
   echo 'alias spw="sp-workshop"' >> ~/.bashrc
   source ~/.bashrc
   ```
3. Run from anywhere:
   ```bash
   spw
   ```

## Optional tools

- N_m3u8DL-RE (optional, for downloads): https://github.com/nilaoda/N_m3u8DL-RE/releases
- Add it to PATH or configure path in app settings.

---


## License

This project is licensed under the [MIT License](LICENSE).

Made with ❤️ by [@slappepolsen](https://x.com/slappepolsen)

[![Follow](https://img.shields.io/twitter/follow/slappepolsen?style=social)](https://x.com/slappepolsen)

![Developer Banner 13](https://ishan-rest.vercel.app/svg/banner/dev13/slappepolsen)
