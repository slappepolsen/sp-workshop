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
> Open this folder. You should see files like `app.py`, `requirements.txt`, and `README.md`. The steps below assume you open a terminal inside this folder.

## macOS

1. Open the **Terminal** app
2. Navigate to the project folder
   ```bash
   cd path/to/sp-workshop
   ```

> **Tip**
> In that same Terminal, do **either**: 
> **Option A:** type `cd`, add a space, drag the unzipped project folder into Terminal, then press Enter. 
> **Option B:** type `cd`, add a space, then type or paste your real folder path where the example says `path/to/sp-workshop` (for example something under Downloads), then press Enter.

3. Create and activate a virtual environment  
   Use Python 3.12 to avoid Qt issues on macOS (`brew install python@3.12`).
   ```bash
   python3.12 -m venv .venv   # or python3 if 3.12 is default
   source .venv/bin/activate
   ```

> **Note**
> A virtual environment keeps this app’s Python packages separate from the rest of your system.

4. Install dependencies
   ```bash
   pip install -r requirements.txt
   ```

5. Install FFmpeg (required)

   ```bash
   brew install ffmpeg-full
   ```

> **Note**  
> Homebrew must be installed first. Install it from https://brew.sh if needed.

> **If FFmpeg is not detected later in the app**  
> After you start SP Workshop, open **Settings → Tools** and set the FFmpeg path manually:
>
> - Apple Silicon: `/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg`
> - Intel: `/usr/local/opt/ffmpeg-full/bin/ffmpeg`

6. Install N_m3u8DL-RE (optional)
- Download from https://github.com/nilaoda/N_m3u8DL-RE/releases
- Add the executable to your PATH

> **Note**  
> PATH is a list of folders your system searches for commands. Search “add directory to PATH macOS” if needed.

7. Run the app
   ```bash
   python3 app.py
   ```
   
   > **Note**  
   > For versions before 10.0.0, use `python3 video_app_v8.py` or rename the file to `app.py`.

## Windows

1. Open **Command Prompt**
2. Navigate to the project folder
   ```bash
   cd path\to\sp-workshop
   ```

> **Tip**  
> Copy the folder path from File Explorer, then type `cd`, paste it, and press Enter..

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

> Download from: https://www.gyan.dev/ffmpeg/builds/

> **Note**  
> **PATH** tells Windows where to find programs when you type them in Command Prompt. 
> If `ffmpeg` is not found, add the folder that contains **your** `ffmpeg.exe` to PATH.

6. Install N_m3u8DL-RE (optional)
- Download from https://github.com/nilaoda/N_m3u8DL-RE/releases
- Add the executable to your PATH

> **Note**  
> Same idea as for FFmpeg: add the folder that contains the N_m3u8DL-RE executable to your PATH, or
> configure the path inside the app’s settings if there is an option.

7. Run the app
   ```bash
   python app.py
   ```
   
> **Note**  
> For versions before 10.0.0, use `python video_app_v8.py` or rename the file to `app.py`.


## Linux

> The `apt` commands below assume **Debian** or **Ubuntu**. Other distributions use their own package manager to install FFmpeg.

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
4. Install N_m3u8DL-RE (optional, for downloads)
   - Download from https://github.com/nilaoda/N_m3u8DL-RE/releases
   - Add the executable to your PATH

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
