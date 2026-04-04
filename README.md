# SP Workshop

[![Release](https://img.shields.io/github/v/release/slappepolsen/sp-workshop)](../../releases)
[![License](https://img.shields.io/github/license/slappepolsen/sp-workshop)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9--3.12-blue)](https://www.python.org)
[![Platform](https://img.shields.io/badge/platform-macOS%20|%20Windows%20|%20Linux-lightgrey)](#installation)

<img src="media/icon.png" width="80" height="80" alt="icon"/>

## Quick Start (if you know your way around a Terminal)

If not, go to [Installation](#installation).

1. Install Python 3.12

2. Open a Terminal in the project folder and run:

   `pip install -r requirements.txt`

   `python app.py`

   (On macOS/Linux you may need: python3 app.py)

3. If something is missing:
   The app will tell you what to install (FFmpeg, N_m3u8DL-RE, etc.)

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

---

### Installation option 1 (Recommended): Download the source code and run

This is the most reliable way to run the app.

#### Step 1: Download the source code

1. Go to:
   https://github.com/slappepolsen/sp-workshop/releases

2. Open the first release on the page.

3. Under **Assets**, click **Source code (zip)**.

4. Open the downloaded file.

5. Extract it (right-click → **Extract All** / **Unzip**).

6. Open the extracted folder (it will be named something like `sp-workshop-main`).

#### Step 2: Run the app

Inside the extracted folder:

- **macOS:** double-click `Start_SP_Workshop.command`
- **Windows:** double-click `Start_SP_Workshop.bat`
- **Linux:** run `./Start_SP_Workshop.sh`

---

### Installation option 2: Pre-built app (experimental)

These are ready-made app files. They are easier to try but may not run on every computer. 
**If you have trouble, use Installation option 1 (download the source code zip) instead.**

#### How to get the app file

1. Open [GitHub Releases](https://github.com/slappepolsen/sp-workshop/releases).
2. Click the release at the top of the list (the newest one).
3. Scroll to **Assets**.
4. Download the file that matches your computer (use the table below).

| Your computer | File name under **Assets** |
|----------|----------|
| **macOS Apple Silicon (M1/M2/M3/M4)** | **`SP_Workshop-macOS-ARM64.dmg`** |
| **macOS Intel (x64)** | **`SP_Workshop-macOS-x64.dmg`** |
| **Windows x64** | **`SP_Workshop-Windows-x64.zip`** |
| **Windows ARM64** | **`SP_Workshop-Windows-ARM64.zip`** |
| **Linux x64** | **`SP_Workshop-Linux-x64.tar.gz`** |

#### macOS

Open the **`.dmg`** for your CPU, drag **`SP_Workshop.app`** to **Applications** (or run it from the disk image), then open the app. The ARM64 build does not run on Intel Macs (and vice versa).

Gatekeeper may warn the first time: Control-click (or right-click) the app > **Open**, or **System Settings > Privacy & Security > Open Anyway**.

#### Windows

Unzip **`SP_Workshop-Windows-x64.zip`** or **`SP_Workshop-Windows-ARM64.zip`** (match your PC architecture), then run **`SP_Workshop.exe`**.
Windows SmartScreen may block unsigned downloads: click **More info** > **Run anyway** if you trust the release.

#### Linux (x64)

Extract the tarball and run the binary, for example:

`tar -xzf SP_Workshop-Linux-x64.tar.gz` then `./SP_Workshop`. If needed: `chmod +x SP_Workshop`.

> **Note:** The **Windows ARM64** job uses GitHub’s **`windows-11-arm`** runner, which is intended for **public** repositories. Private forks may need to drop that matrix leg or use a self-hosted ARM64 runner.

---

## Optional tools

- N_m3u8DL-RE (optional, for downloads): https://github.com/nilaoda/N_m3u8DL-RE/releases
- Add it to PATH or configure path in app settings.

---


## License

This project is licensed under the [MIT License](LICENSE).

Made with ❤️ by [@slappepolsen](https://x.com/slappepolsen)

[![Follow](https://img.shields.io/twitter/follow/slappepolsen?style=social)](https://x.com/slappepolsen)

![Developer Banner 13](https://ishan-rest.vercel.app/svg/banner/dev13/slappepolsen)
