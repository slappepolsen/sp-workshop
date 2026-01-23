# SP Workshop

![Developer Banner 13](https://ishan-rest.vercel.app/svg/banner/dev13/slappepolsen)

[![Release](https://img.shields.io/github/v/release/slappepolsen/sp-workshop)](../../releases)
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

## Features

- Batch download episodes from streaming services
- Extract and clean subtitles from video files
- Translate subtitles using Google Gemini
- Burn subtitles into videos with optional watermarks
- Remux MKV files with separate SRT subtitles
- Transcribe audio/video using Whisper

## Installation

**Prerequisites:** Python 3.9 or higher - Download from [python.org](https://www.python.org/downloads/) if needed. Make sure to add it to PATH (the installation wizard will ask you this).

Go to [Releases](https://github.com/slappepolsen/sp-workshop/releases) and click on `Source code (zip)` under Assets to download SP workshop.

Choose your operating system below for complete installation instructions:

### macOS

1. **Open Terminal:**
   - Press `Cmd(⌘)` + `Space`, type "Terminal", press Enter

2. **Navigate to the project folder:**
   - Open Finder and find the `sp-workshop` folder
   - Show the path bar: Press `Cmd(⌘)` + `Option(⌥)` + `P` (or View → Show Path Bar)
   - Click once on the folder in the path bar at the bottom
   - Right-click and select "Copy [folder name] as Pathname"
   - In Terminal, type `cd ` (with a space) and paste the path:
     ```bash
     cd [paste your path here]
     ```

3. **Create and activate virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

4. **Install Python packages:**
   ```bash
   pip3 install -r requirements.txt
   ```
   *If you get an error, try `python3 -m pip install -r requirements.txt`*

5. **Install FFmpeg (Required):**
   - If you don't have Homebrew, install it first from [brew.sh](https://brew.sh) (copy the command from the website and paste it into Terminal)
   - Then run: `brew install ffmpeg`
   - **Verify:** Type `ffmpeg -version` in Terminal. If you see version information, it's installed!

6. **Install N_m3u8DL-RE (Optional - only needed for batch downloads):**
   - Go to [github.com/nilaoda/N_m3u8DL-RE/releases](https://github.com/nilaoda/N_m3u8DL-RE/releases)
   - Download `osx-x64.tar.gz` (Intel) or `osx-arm64.tar.gz` (Apple Silicon M1/M2/M3/M4/...)
   - Extract the file to get the executable `N_m3u8DL-RE`
   - Move it to a folder (e.g., `/Users/YourName/bin` or create a new folder)
   - Edit your shell config: `nano ~/.zshrc`
   - Add this line (replace `/Users/YourName/bin` with your actual folder path): `export PATH="/Users/YourName/bin:$PATH"`
   - Save: Press `Ctrl(⌃)` + `X`, then `Y`, then `Enter`
   - Reload: Type `source ~/.zshrc`, then `Enter`
   - **Verify:** Type `N_m3u8DL-RE --version`. If you see version information, it's installed!

7. **Set up Google Gemini API Key (Required for translation):**
   - Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
   - Sign in with your Google account
   - Click "Create API Key" or "Get API Key"
   - Copy the API key
   - **Set it up:** Open SP Workshop → Settings → Paste in "API Key (Legacy)" field, OR set it as an environment variable (more secure)
   - *You can skip this for now and add it later when you need translation*

8. **Run the app:**
   ```bash
   python3 video_app_v8.py
   ```
   *Note: Make sure your virtual environment is activated (you should see `(.venv)` in your terminal prompt). If not, run `source .venv/bin/activate` first.*

### Windows

1. **Open Command Prompt:**
   - Press `Win` + `R`, type "cmd", press Enter

2. **Navigate to the project folder:**
   - Open File Explorer and find the `sp-workshop` folder
   - Click once on the folder (select it)
   - Press `Ctrl` + `Shift` + `C` to copy the file path
   - In Command Prompt, type `cd ` (with a space) and paste the path:
     ```bash
     cd [paste your path here]
     ```

3. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

4. **Install Python packages:**
   ```bash
   pip install -r requirements.txt
   ```
   *If you get an error, try `python -m pip install -r requirements.txt`*

5. **Install FFmpeg (Required):**
   - Go to [ffmpeg.org/download.html](https://ffmpeg.org/download.html)
   - Download the Windows build (choose the "Windows builds from gyan.dev" link)
   - Extract the ZIP file to a folder (e.g., `C:\ffmpeg`)
   - **Add to PATH:**
     - Press `Win` + `X` and select "System"
     - Click "Advanced system settings" → "Environment Variables"
     - Under "System variables", find "Path" and click "Edit"
     - Click "New" and add the path to the `bin` folder inside your FFmpeg folder (e.g., `C:\ffmpeg\bin`)
     - Click OK on all windows
   - **Verify:** Open a new Command Prompt, type `ffmpeg -version`. If you see version information, it's installed!

6. **Install N_m3u8DL-RE (Optional - only needed for batch downloads):**
   - Go to [github.com/nilaoda/N_m3u8DL-RE/releases](https://github.com/nilaoda/N_m3u8DL-RE/releases)
   - Download `win-x64.zip` (most modern Windows), `win-arm64.zip` (Surface Pro X), or `win-NT6.0-x86.zip` (32-bit)
   - Extract the ZIP file to get `N_m3u8DL-RE.exe`
   - **Add to PATH:** Use the same method as FFmpeg above (add the folder containing the .exe to your PATH)
   - **Verify:** Open a new Command Prompt, type `N_m3u8DL-RE --version`. If you see version information, it's installed!

7. **Set up Google Gemini API Key (Required for translation):**
   - Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
   - Sign in with your Google account
   - Click "Create API Key" or "Get API Key"
   - Copy the API key
   - **Set it up:** Open SP Workshop → Settings → Paste in "API Key (Legacy)" field, OR set it as an environment variable (more secure)
   - *You can skip this for now and add it later when you need translation*

8. **Run the app:**
   ```bash
   python video_app_v8.py
   ```
   *Note: Make sure your virtual environment is activated (you should see `(.venv)` in your command prompt). If not, run `.venv\Scripts\activate` first.*

### Linux

I mean, I assume you're familiar with CLI so here's just a list of what to install. Navigate to the project folder, then:

1. **Create and activate virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install Python packages:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install FFmpeg (Required):**
   ```bash
   sudo apt install ffmpeg  # Debian/Ubuntu
   # or
   sudo dnf install ffmpeg  # Fedora
   ```

4. **Install N_m3u8DL-RE (Optional - only needed for batch downloads):**
   - Download from [github.com/nilaoda/N_m3u8DL-RE/releases](https://github.com/nilaoda/N_m3u8DL-RE/releases)
   - Extract and add to PATH

5. **Set up Google Gemini API Key (Required for translation):**
   - Get from [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
   - Add in Settings or as environment variable

6. **Run the app:**
   ```bash
   python3 video_app_v8.py
   ```

## Getting Started

**First launch:**
When you first run the app, a setup wizard will pop up and check if everything is installed. It's pretty helpful because it'll tell you what's missing and where to get it. You can skip it if you want and configure everything later in Settings.

Trust me, once everything is installed, using the app is smooth and efficient.

**Directory structure:**
The app creates these folders (you can change them in Settings if you want):

- **`~/VideoProcessing/downloads/`** - Put your raw video files (MKV/MP4) here. If you need to remux before translating (because you want to cut scenes first instead of translating full episodes), place separate SRT files here too. Transcribed SRT files go here, too.

- **`~/VideoProcessing/subtitles/`** - This is where your extracted SRT subtitle files live (extracted, cleaned, and translated versions).

- **`~/VideoProcessing/output/`** - Here's where all your final processed videos go (with burned subtitles and watermarks).

**Configuration:**
Click "Settings" to configure:

- **Google Gemini API Key** - Required for translating subtitles. Get yours from [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).

- **Watermark files** (optional) - If you want watermarks on your videos, you'll need PNG images at 720p and 1080p resolutions.
  - **720p watermark:** Create a transparent PNG at 1280x720 pixels, add your text/logo with 20% opacity
  - **1080p watermark:** Same thing but at 1920x1080 pixels
  - You can toggle watermarks on/off in Settings (because sometimes you just don't want them)

- **Directory paths** - Where your downloads, subtitles, and output files go. Change these if you want different locations.

## Workflows

The whole point of this is to make WLW/sapphic/lesbian content accessible for everyone in the world. You know, extracting subtitles, translating them, processing videos with burned-in subtitles and watermarks. All that good stuff, but with way fewer clicks.

There are three main ways to use the app, depending on where your content comes from. Here's a visual overview of all three workflows:

![Workflow Diagrams](flowcharts.png)

*From left to right: Workflow 1 (External Video + Separate SRT), Workflow 2 (Batch Downloader), Workflow 3 (Whisper Transcription)*

### Workflow Comparison

| | **Workflow 1: Remux** | **Workflow 2: Batch Downloader** | **Workflow 3: Transcribe** |
|---|---|---|---|
| **Starting Material** | Video file (MKV/MP4) + separate SRT file | Download commands from streaming source | Video/audio file with no subtitles |
| **What You Need** | FFmpeg | FFmpeg + N_m3u8DL-RE | FFmpeg + `whisper_auto.sh` script |
| **Best For** | Already have video files and separate subtitle tracks | Downloading full episodes/series with embedded subtitles | No subtitles exist yet, need to create them from audio |

**Typical workflow (Workflow 2 - using the Batch Downloader):**
Here's basically how things flow (see [batchdownloader_guide.md](batchdownloader_guide.md) for how to get download commands):

1. Paste your download commands in the text area, click "**Batch Download Episodes**". Hell yeah, automation!
2. Click "**Extract Subtitles**" to pull those embedded subtitle tracks from your MKV files.
3. "**Clean Subtitles**" to remove all those ugly color tags (`<c.yellow>`, etc.) that come from VTT format. Trust me, you want this.
4. Click "**Translate Subtitles**" to translate to your selected target language. The original files get renamed with `_OG` suffix so you don't lose them.
5. Finally, click "**Process Video**" to burn-in the subtitles, add your watermark (if you want), and resize to 720p or 1080p.

**Other features:**

- **Remux:** If you already have an MKV file but the subtitles are separate, this combines them (lossless, no re-encoding, so it's fast!)
- **Transcribe:** Creates subtitles from scratch using Whisper AI if you don't have any. 

## Troubleshooting

Don't worry, we've all been there. Here's how to fix the common stuff:

**"PyQt5 not found"** → Just install it: `pip install PyQt5`. Easy fix!

**"FFmpeg not found"** → Install FFmpeg (see Installation section above) and make sure it's in your PATH. Check with `which ffmpeg` (macOS/Linux) or `where ffmpeg` (Windows). If it doesn't show a path, you need to add it.

**"N_m3u8DL-RE not found"** → Download it, extract it, and add it to your PATH. The app needs to be able to find it when you run download commands.

**"gst command not found"** → Install the translator: `pip install gemini-srt-translator`. The app will find it automatically after that.

**"whisper_auto.sh not found"** → Make sure `whisper_auto.sh` is in the same folder as `video_app_v8.py`. Also make it executable: `chmod +x whisper_auto.sh` if it's not the case yet.

**App won't start** → Check your Python version (`python3 --version` needs to be 3.9 or higher). Verify PyQt5 is installed: `python3 -c "import PyQt5"`. If that fails, check your terminal for error messages—they'll tell you what's wrong.

**Video processing fails** → Make sure FFmpeg is installed and working. Check that your subtitle files match your video filenames (they need to have the same base name). If you're using watermarks, verify the watermark file paths in Settings are correct.

**Translation fails** → Double-check your API key in Settings (or make sure the environment variable is set). Check your internet connection—you need that for API calls. Also make sure your API key has quota/credits left.

**Still stuck?** Check the log output in the app's log window. The logs usually tell you exactly what went wrong.

## System Requirements

- **macOS 10.14+** (primary platform - fully tested)
- **Windows/Linux** - The app should work, but these platforms haven't been as extensively tested. If you're on Windows or Linux and manage to get it working (or run into issues), please let me know! I'd love to hear about your experience and can help troubleshoot.
- Some things might need tweaking on other platforms e.g., path handling (I tried my best to make this cross-platform)

**And of course like I mentioned:**
- Python 3.9 or higher
- FFmpeg (latest version recommended)
- N_m3u8DL-RE (for downloads, if you plan to use the batch downloader)
- Internet connection (only for translation and downloading, the rest is local)

## Documentation
- [batchdownloader_guide.md](batchdownloader_guide.md) - How to extract download commands from streaming sources
- [CHANGELOG.md](CHANGELOG.md) - Version history

## Support

I've received messages asking about donations - thank you, but I don't want any money! The best way to support this project is to try it out and let me know what you think. Your feedback is all I need :)

## License

This project is licensed under the [MIT License](LICENSE).

Made with ❤️ by [@slappepolsen](https://x.com/slappepolsen)

[![Follow](https://img.shields.io/twitter/follow/slappepolsen?style=social)](https://x.com/slappepolsen)

[![Views](https://dynamic-repo-badges.vercel.app/svg/count/9/Repository%20Views/sp-workshop)](https://github.com/slappepolsen/sp-workshop)

