# Installation

SP Workshop runs on **macOS**, **Windows**, and **Linux**. The most reliable way to use it is **from source**; **pre-built apps** are also available but are experimental.

---

## Prerequisites

- **Python 3.12** (required). Download from [python.org](https://www.python.org/downloads/) and add Python to **PATH** during installation. Older or newer Python versions are not supported for running from source.
- **FFmpeg** (required): install with your OS package manager or from [ffmpeg.org](https://ffmpeg.org/download.html) so `ffmpeg` is on your **PATH**.

> **Note:** During Python setup, keep the option to add Python to PATH enabled (wording varies by version and OS). That lets Terminal or Command Prompt find `python` / `python3` / `python3.12`.

---

## Run from source (recommended)

This is the most reliable way to run the app.

### Step 1: Get the source code

1. Open [GitHub Releases](https://github.com/slappepolsen/sp-workshop/releases).
2. Open the latest release.
3. Under **Assets**, download **Source code (zip)**.
4. Extract the zip (e.g. right-click → **Extract All** / **Unzip**).
5. Open the folder (often named like `sp-workshop-<version>`).

You can also clone this repository instead of using the zip. You already know how to do that in that case.

### Step 2: Start the app

Inside the project folder:

- **macOS:** double-click `Start_SP_Workshop.command`
- **Windows:** double-click `Start_SP_Workshop.bat`
- **Linux:** run `./Start_SP_Workshop.sh`

Alternatively, from a terminal:

```bash
cd /path/to/sp-workshop

python3.12 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
python3 app.py
```

On **Windows**, use `py -3.12 -m venv .venv`, then `.venv\Scripts\activate`, then `python app.py` (or `python3` if available). If `python3.12` is not found, use the `py` launcher or the full path to your 3.12 interpreter after installing from [python.org](https://www.python.org/downloads/).

Ensure **FFmpeg** and **Python 3.12** are available before running; the app may still prompt for other optional tools (for example download helpers).

---

## Pre-built app (experimental)

Ready-made builds are easier to try but **may not run on every machine**. If you have trouble, use **Run from source** above.

### Get the build

1. Open [GitHub Releases](https://github.com/slappepolsen/sp-workshop/releases).
2. Choose the newest release.
3. Under **Assets**, download the file for your system:

| Your computer | File name under **Assets** |
|---------------|----------------------------|
| **macOS Apple Silicon (M1/M2/M3/M4)** | **`SP_Workshop-macOS-ARM64.dmg`** |
| **macOS Intel (x64)** | **`SP_Workshop-macOS-x64.dmg`** |
| **Windows x64** | **`SP_Workshop-Windows-x64.zip`** |
| **Windows ARM64** | **`SP_Workshop-Windows-ARM64.zip`** |
| **Linux x64** | **`SP_Workshop-Linux-x64.tar.gz`** |

### macOS

Open the **`.dmg`** for your CPU, drag **`SP_Workshop.app`** to **Applications** (or run it from the disk image). ARM64 and Intel builds are not interchangeable.

**Gatekeeper** may warn the first time: Control-click (or right-click) the app → **Open**, or **System Settings → Privacy & Security → Open Anyway**.

### Windows

Unzip **`SP_Workshop-Windows-x64.zip`** or **`SP_Workshop-Windows-ARM64.zip`** (match your PC architecture), then run **`SP_Workshop.exe`**.

**SmartScreen** may block unsigned downloads: **More info** → **Run anyway** if you trust the release.

### Linux (x64)

Example:

```bash
tar -xzf SP_Workshop-Linux-x64.tar.gz
./SP_Workshop
```

If needed: `chmod +x SP_Workshop`.

> **Note:** The **Windows ARM64** build uses GitHub’s **`windows-11-arm`** runner, which is aimed at **public** repositories. **Private forks** may need to drop that matrix job or use a self-hosted ARM64 runner to produce ARM64 Windows assets.

---

## Optional download tools

The app runs **without** these unless you use a workflow that needs them (for example certain stream downloads). When you do, install and add to **PATH**, or set the path in the app’s settings.

- **[N_m3u8DL-RE](https://github.com/nilaoda/N_m3u8DL-RE/releases)** (optional, for some download flows)

---

## Common issues (PATH and errors)

| Symptom | What to try |
|--------|----------------|
| `python` / `pip` not found | Reinstall **Python 3.12** with **Add to PATH** enabled, or use `py -3.12` on Windows / `python3.12` on macOS and Linux. |
| Install packages safely | With the venv activated: `pip install -r requirements.txt`, or `python -m pip install -r requirements.txt` using the same 3.12 interpreter. |
| Wrong Python version | This project expects **3.12**; recreate the venv with `python3.12 -m venv .venv` (or `py -3.12 -m venv .venv` on Windows). |
| `ffmpeg` not found | Install FFmpeg and ensure it is on **PATH** (required). |
| Other optional tools | Run the app; it may indicate optional download helpers. Configure paths in settings when needed. |

Back to the project overview: [README.md](README.md).
