# Batch Downloader Guide

The batch downloader runs N_m3u8DL-RE commands to download video streams.

## Quick Start

1. Click **"How to get commands"** in the Download section to open the instructions
2. Follow the instructions to obtain commands for your content
3. Set **Mode** (Episode(s) or Movie), optionally **Name**, and for episodes: **Items** (e.g. `1` or `1-5`)
4. Paste one command per line
5. Click **Batch download**

## Naming Options

- **Mode**: Choose Episode(s) for TV series or Movie for films
- **Name** (optional): Prefix for all files, e.g. `Show Name (2025)` or `Movie Name (2025)`
- **Use S01E02** (Episode(s) only): When checked, outputs S01E01, S01E02, etc. Set **Season** for the season number
- **Items** (Episode(s) only): Episode numbers or range: `1`, `1-5`, `1,3,5-7`

Examples:
- Episode(s), Name: "Tres Gracias 2025", S01E02 checked, Season: 1, Items: 1-12 → `Tres Gracias 2025 S01E01.mkv` … `Tres Gracias 2025 S01E12.mkv`
- Movie, Name: "My Movie (2025)", 1 command → `My Movie (2025).mkv`
- Episode(s), no name, Items: 1-5 → `1.mkv`, `2.mkv`, … `5.mkv` (same as before)

## Command Format

- Paste one full N_m3u8DL-RE-style command per line
- Each line = one item (episode or movie)
- The app adds save/output options (e.g. `--save-name`, `--save-dir`, `-M mkv`)

See the instructions linked in the app for the exact format needed for your use case.
