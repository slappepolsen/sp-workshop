# SP Workshop

[![Build](https://img.shields.io/github/actions/workflow/status/slappepolsen/sp-workshop/build.yml?branch=main)](../../actions)
[![Release](https://img.shields.io/github/v/release/slappepolsen/sp-workshop)](../../releases)
[![Downloads](https://img.shields.io/github/downloads/slappepolsen/sp-workshop/total)](../../releases)
[![License](https://img.shields.io/github/license/slappepolsen/sp-workshop)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue)](https://www.python.org)
[![Platform](https://img.shields.io/badge/platform-macOS%20|%20Windows%20|%20Linux-lightgrey)](#installation)

## Video processing studio GUI 🎬 

🌐 Extract, translate, transcribe, and burn subtitles into videos  

🏳️‍🌈 Built from the need for representation and accessible international WLW/sapphic content (but works for any audiovisual media)

#### Intended users
SP Workshop is built for subtitle editors, translators, archivists, and  **anyone** determined to watch their favorite (WLW / Sapphic) shows or ships with subtitles in the language they actually want.

#### Skill level
Designed for non-technical users (too!). If you can download software on your laptop, you can use SP Workshop. No command-line experience required.

*Version 8.1.1 "Torre de Babel" [reference](https://en.wikipedia.org/wiki/Tower_of_Babel)*

## Features

- Batch download episodes from streaming services
- Extract and clean subtitles from video files
- Translate subtitles using Google Gemini
- Burn subtitles into videos with optional watermarks
- Remux MKV files with separate SRT subtitles
- Transcribe audio/video using Whisper

## Installation

### Option 1: Download Executable (Recommended)

An "executable" is a ready-to-run version of the app that doesn't require any setup—just download and run! This is the easiest option for most users.

1. Go to the [Releases](../../releases) page
2. Download the file for your operating system:
   - **macOS** (Apple computers): Download `SP_Workshop-macOS.zip`
   - **Windows**: Download `SP_Workshop-Windows.zip`
   - **Linux**: Download `SP_Workshop-Linux.tar.gz`
3. **Extract the file**: 
   - On **macOS/Windows**: Double-click the `.zip` file to extract it (creates a folder)
   - On **Linux**: Right-click the `.tar.gz` file and select "Extract" or use your file manager
4. **Run the app**:
   - On **macOS**: Open the extracted folder and double-click `SP_Workshop.app`
   - On **Windows**: Open the extracted folder and double-click `SP_Workshop.exe`
   - On **Linux**: Open the extracted folder, right-click `SP_Workshop`, select "Properties" → "Permissions" → check "Execute", then double-click to run

The executable includes all documentation files (README, SETUP guide, etc.) in the same folder.

### Option 2: Run from Source

"Running from source" means running the app directly from the Python code. This option requires Python to be installed on your computer.

**What you need:**
- **Python 3.9 or higher** - Python is a programming language that runs the app. If you don't have it, download from [python.org](https://www.python.org/downloads/)

**Installation steps:**

1. **Open Terminal** (macOS/Linux) or **Command Prompt** (Windows):
   - **macOS**: Press `Cmd(⌘)` + `Space`, type "Terminal", press Enter
   - **Windows**: Press `Win` + `R`, type "cmd", press Enter
   - **Linux**: Press `Ctrl` + `Alt` + `T` or find Terminal in your applications

2. **Navigate to the folder** where you downloaded this project:
   
   First, get the actual path to your folder:
   - **Windows**: 
     - Open File Explorer and find the `sp-workshop` folder
     - Click once on the folder (select it)
     - Press `Ctrl` + `Shift` + `C` to copy the file path
   - **macOS**: 
     - Open Finder and find the `sp-workshop` folder
     - Show the path bar: Press `Cmd(⌘)` + `Option(⌥)` + `P` (or View → Show Path Bar)
     - Click once on the folder in the path bar at the bottom
     - Right-click and select "Copy [folder name] as Pathname"
   - **Linux**: 
     - Right-click the `sp-workshop` folder
     - Look for "Copy path" or "Copy location" option (varies by file manager)
     - Or simply drag the folder into the Terminal window
   
   Then, in Terminal/Command Prompt, type `cd ` (with a space) and paste the path:
   ```bash
   cd [paste your path here]
   ```

3. **Install required Python packages** (this downloads the libraries the app needs):
   ```bash
   pip install -r requirements.txt
   ```
   *Note: If you get an error, try `pip3` instead of `pip`, or `python -m pip install -r requirements.txt`*

4. **Run the app**:
   ```bash
   python3 video_app_v8.py
   ```
   *Note: On Windows, you might need to use `python` instead of `python3`*

## External Dependencies

The app needs some additional tools to work properly. These aren't included with the app itself, so you'll need to install them separately. Don't worry, I'll guide you through each one!

### FFmpeg (Required)

**How to install:**

- **macOS:**
  1. If you don't have Homebrew, install it first from [brew.sh](https://brew.sh) (copy the command from the website and paste it into Terminal)
  2. Then run: `brew install ffmpeg`
  3. **Verify it worked:** Type `ffmpeg -version` in Terminal. If you see version information, it's installed!

- **Windows:**
  1. Go to [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
  2. Download the Windows build (choose the "Windows builds from gyan.dev" link)
  3. Extract the ZIP file to a folder (e.g., `C:\ffmpeg`)
  4. **Add to PATH:** 
     - Press `Win` + `X` and select "System"
     - Click "Advanced system settings" → "Environment Variables"
     - Under "System variables", find "Path" and click "Edit"
     - Click "New" and add the path to the `bin` folder inside your FFmpeg folder (e.g., `C:\ffmpeg\bin`)
     - Click OK on all windows
  5. **Verify it worked:** Open Command Prompt (Win + R, type "cmd"), type `ffmpeg -version`. If you see version information, it's installed!

- **Linux:**
  1. Open Terminal
  2. Run: `sudo apt install ffmpeg` (for Debian/Ubuntu) or `sudo dnf install ffmpeg` (for Fedora)
  3. **Verify it worked:** Type `ffmpeg -version`. If you see version information, it's installed!

### N_m3u8DL-RE (Optional)

Only needed if you want to use the "Batch download episodes" feature. If you're just processing videos you already have, you can skip this. Instead of downloading episodes one by one, you can paste multiple download commands and let the app download them all automatically.

**How to install:**

1. Go to [github.com/nilaoda/N_m3u8DL-RE/releases](https://github.com/nilaoda/N_m3u8DL-RE/releases)
2. Download the latest release for your platform
3. Extract the ZIP file to a folder
4. **Add to PATH** (so the app can find it):
   - **macOS/Linux:** Add the folder path to your PATH in `~/.zshrc` or `~/.bashrc`
   - **Windows:** Add the folder to your PATH using the same method as FFmpeg (see above)
5. **Verify it worked:** Open Terminal/Command Prompt, type `N_m3u8DL-RE --version`. If you see version information, it's installed!

*Note: You don't need this if you're only using the app to process videos you already have or transcribe videos.*

### Google Gemini API Key (Required for Translation)

**What it is:** An API key is like a password that lets the app use Google's AI translation service. It's free to get and use.

**Why you need it:** The app uses Google Gemini AI to translate subtitles. Without an API key, the translation feature won't work. You can still use other features like extracting subtitles or processing videos without it.

**How to get one:**

1. Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with your Google account (if you're not already signed in)
3. Click "Create API Key" or "Get API Key"
4. Copy the API key that appears (it looks like a long string of letters and numbers)
5. **Set it up in the app:**
   - Open SP Workshop
   - Go to **Settings** (button in top right)
   - Paste your API key in the "API Key (Legacy)" field, OR
   - **Recommended (more secure):** Set it as an environment variable on your computer instead of saving it in the app

**Don't worry if you don't have one yet!** You can always get it later when you need to translate subtitles. The app will remind you if you try to use translation without an API key.

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
