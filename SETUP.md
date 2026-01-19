# Video processing studio - SETUP GUIDE

Hey there! Welcome to Video Processing Studio. This app basically wraps all ,y command-line scripts into a nice, friendly GUI so you don't have to deal with the technical `terminal` (which, let's be honest, isn't always the most appealing thing to look at). 

The whole point of this is to make WLW /sapphic / lesbian content accessible for everyone in the world. You know, extracting subtitles, translating them, processing videos with burned-in subtitles and watermarks. All that good stuff, but with way fewer clicks. I love automation, and I want you to do as few clicks as possible, basically.

So let's get you set up! Trust me, once everything is installed, using the app is smooth and efficient.

## Installation

**Quick start:**

1. Install Python dependencies: `pip install -r requirements.txt`
2. Install FFmpeg: `brew install ffmpeg` (macOS) or download from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html)
3. Install N_m3u8DL-RE: Download from [https://github.com/nilaoda/N_m3u8DL-RE/releases](https://github.com/nilaoda/N_m3u8DL-RE/releases) and add to PATH
4. Run the app in terminal / command prompt: `python3 video_app_v6.py`

**Python dependencies:**
The app requires Python 3.9+. Install with: `pip install -r requirements.txt`

Or manually: `pip install PyQt5>=5.15.0 gemini-srt-translator>=3.0.0`

**FFmpeg (required):**
This is the thing that does all the heavy lifting aka extracting subtitles, burning them into videos, resizing, watermarking, all that. Without it, nothing works. Install on macOS with `brew install ffmpeg`, or download from https://ffmpeg.org/download.html for other platforms. Verify it worked with `ffmpeg -version`.

**N_m3u8DL-RE (required if you want to use the batch downloader):**
If you want to batch download episodes from streaming services, you'll need this. It's what makes the whole "paste commands and download multiple episodes at once" thing possible. Download from [https://github.com/nilaoda/N_m3u8DL-RE/releases](https://github.com/nilaoda/N_m3u8DL-RE/releases), extract it, and add to PATH. Verify with `N_m3u8DL-RE --version`.

**Google Gemini API key (required if you want to use the SRT translator):**
So here's the thing,if you want to translate subtitles (which is probably why you're here, right?), you'll need a Google Gemini API key. Get yours from [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey). You can set it in the app via Settings → "Google Gemini API Key", or as an environment variable: `export GST_API_KEY="your-key-here"`. Don't worry if you don't have one yet, you can always set it up later when you need it.

**Optional (nice to have):**
These aren't required, but they make your life easier:

- **Lossless Cut:** For fast, lossless video cutting. Super useful if you're working with scenes. [https://github.com/mifi/lossless-cut/releases](https://github.com/mifi/lossless-cut/releases)
- **VLC:** Good for previewing videos before processing. Way better and higher compatibility than your standard video player. [https://www.videolan.org/vlc/](https://www.videolan.org/vlc/)
- **Subtitle Edit:** If you need to manually edit subtitles (though hopefully the app handles most of that for you). [https://github.com/SubtitleEdit/subtitleedit/releases](https://github.com/SubtitleEdit/subtitleedit/releases)

---

## Getting to work

**First launch:**
When you first run the app, a setup wizard will pop up and check if everything is installed. It's pretty helpful because it'll tell you what's missing and where to get it. You can skip it if you want and configure everything later in Settings.

**Configuration:**
Click "Settings" to configure:

- **Google Gemini API Key**, required for translating subtitles. Get yours from the link in the *Installation* section above.

- **Watermark files** (optional) - If you want watermarks on your videos, you'll need PNG images at 720p and 1080p resolutions. 
  - **720p watermark:** Create a transparent PNG at 1280x720 pixels, add your text/logo with 20% opacity
  - **1080p watermark:** Same thing but at 1920x1080 pixels
  - You can toggle watermarks on/off in *Settings* (because sometimes you just don't want them)

- **Directory paths** - Where your downloads, subtitles, and output files go. Change these if you want different locations.

**Directory structure:**
The app creates these folders (you can change them in Settings if you want):

- **`~/VideoProcessing/downloads/`**. Put your raw video files (MKV/MP4) here. If you need to remux before translating (because you want to cut scenes first instead of translating full episodes), place separate SRT files here too.

- **`~/VideoProcessing/subtitles/`**. This is where your extracted SRT subtitle files live (extracted, cleaned, and translated versions).

- **`~/VideoProcessing/output/`**. Here's where all your final processed videos go (with burned subtitles and watermarks).


**Workflows:**

There are three main ways to use the app, depending on where your content comes from. Here's a visual overview of all three workflows:

![Workflow Diagrams](flowcharts.png)

*From left to right: Workflow 1 (External Video + Separate SRT), Workflow 2 (Batch Downloader), Workflow 3 (Whisper Transcription)*

**Typical workflow (Workflow 2 - Batch Downloader):**
Here's basically how things flow (see [batchdownloader_guide.md](batchdownloader_guide.md) for how to get download commands from Widevine Proxy 2):

1. Paste your download commands in the text area, click "**Batch Download Episodes**". Hell yeah, automation!
2. Click "**Extract Subtitles**" to pull those embedded subtitle tracks from your MKV files. 
3. "**Clean Subtitles**" to remove all those ugly color tags (`<c.yellow>`, etc.) that come from VTT format. Trust me, you want this.
4. Click "**Translate Subtitles**" to translate to English (or whatever language you need). The original files get renamed with `_OG` suffix so you don't lose them.
5. Finally, click "**Process Video**" to burn-in the subtitles, add your watermark (if you want), and resize to 720p or 1080p. 


**Other features:**

- **Remux:** If you already have an MKV file but the subtitles are separate, this combines them (lossless, no re-encoding, so it's fast!)
- **Transcribe:** Creates subtitles from scratch using Whisper AI if you don't have any. Requires `whisper_auto.sh` to be in the same folder.

**Quick note on resolution:**

- **720p:** Great for archiving large collections (like, if you're me and archiving 2,300 scenes, that's about 38GB in 720p vs 76GB in 1080p...)
- **1080p:** Perfect for sharing when quality is the priority. File sizes are about double, but the quality is worth it if you have the space.

---

## Troubleshooting

Don't worry, we've all been there. Here's how to fix the common stuff:

**"PyQt5 not found"** → Just install it: `pip install PyQt5`. Easy fix!

**"FFmpeg not found"** → Install FFmpeg (see Installation section above) and make sure it's in your PATH. Check with `which ffmpeg`, if it doesn't show a path, you need to add it.

**"N_m3u8DL-RE not found"** → Download it, extract it, and add it to your PATH. The app needs to be able to find it when you run download commands.

**"gst command not found"** → Install the translator: `pip install gemini-srt-translator`. The app will find it automatically after that.

**"whisper_auto.sh not found"** → Make sure `whisper_auto.sh` is in the same folder as `video_app_v6.py`. Also make it executable: `chmod +x whisper_auto.sh` if it's not the case yet.

**App won't start** → Check your Python version (`python3 --version` needs to be 3.9 or higher). Verify PyQt5 is installed: `python3 -c "import PyQt5"`. If that fails, check your terminal for error messages—they'll tell you what's wrong.

**Video processing fails** → Make sure FFmpeg is installed and working. Check that your subtitle files match your video filenames (they need to have the same base name). If you're using watermarks, verify the watermark file paths in Settings are correct.

**Translation fails** → Double-check your API key in Settings (or make sure the environment variable is set). Check your internet connection—you need that for API calls. Also make sure your API key has quota/credits left.

**Still stuck?** Check the FAQ in the app (click the "FAQ" button) or look at the log output in the app's log window. The logs usually tell you exactly what went wrong.

---

## System requirements

- **macOS 10.14+** (primary platform - fully tested)
- **Linux/Windows** - The app should work, but I haven't tested it on these platforms. If you're on Linux or Windows and manage to get it working (or run into issues), please let me know! I'd love to hear about your experience and can help troubleshoot.
- Python 3.9 or higher
- FFmpeg (latest version recommended)
- N_m3u8DL-RE (for downloads, if you plan to use the batch downloader)
- Internet connection (for API translation)

**Files included:**

- `video_app_v6.py` the main application
- `icon.icns` / `icon.png` are app icons (`.icns` is macOS-specific, `.png` works everywhere)
- `requirements.txt` python dependencies
- `whisper_auto.sh` transcription script (bash script, may need adjustments for Windows)
- `SETUP.md` is this file

**Note for Windows/Linux users:**

The app was built and tested on macOS, so some things might need tweaking on other platforms:

- The `whisper_auto.sh` script is a bash script, Windows users might need to adapt it
- Path handling should work cross-platform, but let me know if you run into issues
- The app icon might look different on non-macOS systems (that's fine, it'll still work)