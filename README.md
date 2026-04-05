# SP Workshop

[![Release](https://img.shields.io/github/v/release/slappepolsen/sp-workshop)](https://github.com/slappepolsen/sp-workshop/releases)
[![License](https://img.shields.io/github/license/slappepolsen/sp-workshop)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12-blue)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-macOS%20|%20Windows%20|%20Linux-lightgrey)](INSTALL.md#installation)

<img src="media/icon.png" width="80" height="80" alt="icon"/>

SP Workshop is a desktop GUI for **extracting**, **translating**, **transcribing**, and **burning** subtitles into videos. It was created to make international WLW / sapphic content more accessible, and it works for any audiovisual media.

## What it does

| Function | Description |
|----------|-------------|
| **Subtitles** | Extract subtitles from MKV files, clean formatting, translate subtitles |
| **Process Video** | Burn subtitles into video with optional watermarks, output at 720p or 1080p |
| **Transcription** | Generate subtitles from audio using Whisper when no subtitles exist |
| **Remuxing** | Tree-based file and track view, add external SRT files, remux MKV or MP4, split audio tracks |

## Who it’s for

- Subtitle editors and translators  
- Archivists and fandom preservation projects  
- Anyone who wants subtitles in the language they actually want  

## Get started

- **Latest downloads and release assets:** [Releases](https://github.com/slappepolsen/sp-workshop/releases)  
- **Full setup (source zip, pre-built apps, optional tools, per-OS notes):** [INSTALL.md](INSTALL.md)  
- **Quick start from source**

  Requires **Python 3.12** and **FFmpeg**. Full setup: [INSTALL.md](INSTALL.md).

  ```bash
  cd /path/to/sp-workshop

  python3.12 -m venv .venv
  source .venv/bin/activate

  pip install -r requirements.txt
  python3 app.py
  ```

  On **Windows**, use `py -3.12 -m venv .venv`, then `.venv\Scripts\activate`, then `python app.py`. If `python3.12` is not a command on your system, install Python 3.12 from [python.org](https://www.python.org/downloads/) and ensure it is on `PATH`, or use `python` / `python3` only when that points to 3.12.

## Notes

- **Pre-built apps** are experimental; if they fail on your machine, run from source (see [INSTALL.md](INSTALL.md)).  

## License

This project is licensed under the [MIT License](LICENSE).

Made with ❤️ by [@slappepolsen](https://x.com/slappepolsen)

[![Follow](https://img.shields.io/twitter/follow/slappepolsen?style=social)](https://x.com/slappepolsen)

![Developer Banner 13](https://ishan-rest.vercel.app/svg/banner/dev13/slappepolsen)
