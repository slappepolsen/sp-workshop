# SP Workshop

[![Release](https://img.shields.io/github/v/release/slappepolsen/sp-workshop)](../../releases)
[![Downloads](https://img.shields.io/github/downloads/slappepolsen/sp-workshop/total)](../../releases)
[![License](https://img.shields.io/github/license/slappepolsen/sp-workshop)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-blue)](https://www.python.org)
[![Platform](https://img.shields.io/badge/platform-macOS%20|%20Windows%20|%20Linux-lightgrey)](#installation)

## Video processing studio GUI 🎬 

🌐 Extract, translate, transcribe, and burn subtitles into videos  

🏳️‍🌈 Built from the need for representation and accessible international WLW/sapphic content (but works for any audiovisual media)

![Views](https://yourdomain.com/svg/count/9/Repository%20Views/your-repo)

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

**What you need:**
- **Python 3.9 or higher** - Download from [python.org](https://www.python.org/downloads/) if you don't have it

**Installation steps:**

1. **Open Terminal** (macOS/Linux) or **Command Prompt** (Windows):
   - **macOS**: Press `Cmd(⌘)` + `Space`, type "Terminal", press Enter
   - **Windows**: Press `Win` + `R`, type "cmd", press Enter
   - **Linux**: Press `Ctrl` + `Alt` + `T` or find Terminal in your applications

2. **Navigate to the folder** where you downloaded this project:
   
   #### First, get the actual path to your folder:
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
2. Download the file for your platform:
   - **Windows x64** (most modern Windows): `win-x64.zip`
   - **Windows ARM64** (Surface Pro X): `win-arm64.zip`
   - **Windows 32-bit**: `win-NT6.0-x86.zip`
   - **Linux x64** (Ubuntu, etc.): `linux-x64.tar.gz`
   - **Linux ARM64** (Raspberry Pi): `linux-arm64.tar.gz`
   - **macOS Intel**: `osx-x64.tar.gz`
   - **macOS Apple Silicon** (M1/M2/M3/M4/...): `osx-arm64.tar.gz`
   - *Click "Show all 13 assets" if you don't see these files*
3. Extract the downloaded file, you'll get a single executable file (e.g., `N_m3u8DL-RE` or `N_m3u8DL-RE.exe`)
4. **Add to PATH** (so the app can find it):
   - **macOS/Linux:**
     1. Move the executable to a folder (e.g., `/Users/YourName/bin` or create a new folder for it)
     2. Open Terminal
     3. Edit your shell config: `nano ~/.zshrc` (macOS) or `nano ~/.bashrc` (Linux)
     4. Add this line (replace `/Users/YourName/bin` with [your actual folder path](#first-get-the-actual-path-to-your-folder)): `export PATH="/Users/YourName/bin:$PATH"`
     5. Save: Press `Ctrl(⌃)` + `X`, then `Y`, then `Enter`
     6. Reload: Type `source ~/.zshrc` (macOS) or `source ~/.bashrc` (Linux), then `Enter`
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
   - **Recommended (more secure):** Set it as an environment variable on your computer instead of saving it in the app.

**Don't worry if you don't have one yet!** You can always get it later when you need to translate subtitles. The app will remind you if you try to use translation without an API key.

## Getting Started

**First launch:**
When you first run the app, a setup wizard will pop up and check if everything is installed. It's pretty helpful because it'll tell you what's missing and where to get it. You can skip it if you want and configure everything later in Settings.

Trust me, once everything is installed, using the app is smooth and efficient.

**Directory structure:**
The app creates these folders (you can change them in Settings if you want):

- **`~/VideoProcessing/downloads/`** - Put your raw video files (MKV/MP4) here. If you need to remux before translating (because you want to cut scenes first instead of translating full episodes), place separate SRT files here too.

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
- **Transcribe:** Creates subtitles from scratch using Whisper AI if you don't have any. Requires `whisper_auto.sh` to be in the same folder.

**Quick note on resolution:**

- **720p:** Great for archiving large collections (like, if you're me and archiving 2,300 scenes, that's about 38GB in 720p vs 76GB in 1080p...)
- **1080p:** Perfect for sharing when quality is the priority. File sizes are about double, but the quality is worth it if you have the space.

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
- Python 3.9 or higher
- FFmpeg (latest version recommended)
- N_m3u8DL-RE (for downloads, if you plan to use the batch downloader)
- Internet connection (for API translation)

**Note for Windows/Linux users:**

The app was primarily built and tested on macOS, so some things might need tweaking on other platforms:

- The `whisper_auto.sh` script is a bash script; Windows users might need to adapt it
- Path handling should work cross-platform, but let me know if you run into issues
- The app icon might look different on non-macOS systems (that's fine, it'll still work)

## Documentation

- [batchdownloader_guide.md](batchdownloader_guide.md) - How to extract download commands from streaming sources
- [CHANGELOG.md](CHANGELOG.md) - Version history

## Support

I've received messages asking about donations - thank you, but I don't want any money! The best way to support this project is to try it out and let me know what you think. Your feedback is all I need :)

## License

This project is licensed under the [MIT License](LICENSE).

Made with ❤️ by [@slappepolsen](https://x.com/slappepolsen)

[![Follow](https://img.shields.io/twitter/follow/slappepolsen?style=social)](https://x.com/slappepolsen)
