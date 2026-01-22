# Batch Downloader Guide

This guide explains how to use SP Workshop's batch downloader with different streaming sources.

## Supported Sources

| Source | DRM | Keys Required | Language |
|--------|-----|---------------|----------|
| TF1 (French) | Widevine | Yes | French |
| Globoplay (Portuguese) | None | No | Portuguese |

## Quick Start

1. Select your **Source** from the dropdown
2. Set the **Episodes** (default: 1)
   - Single: `1`
   - Range: `1-5` (episodes 1, 2, 3, 4, 5)
   - Multiple: `1,3,5` (episodes 1, 3, 5)
   - Mixed: `1-3,5,7-10` (episodes 1, 2, 3, 5, 7, 8, 9, 10)
3. Paste your commands (one per line)
4. Click **Batch download episodes**

---

## Quick Reference: Globoplay

**TL;DR for Globoplay:**
1. Play episode in browser → Open DevTools (F12) → Network tab → Filter `.m3u8`
2. Copy the m3u8 URL (right-click → Copy URL)
3. Repeat for each episode
4. In SP Workshop: Select "Globoplay (Portuguese)" → Paste URLs (one per line) → Set episode numbers → Click download

**That's it!** Headers are added automatically. No keys needed.

---

## TF1 (French)

TF1 uses Widevine DRM, so you need to extract decryption keys using WidevineProxy2.

### Setup WidevineProxy2

1. Go to `chrome://extensions/`
2. Enable **Developer mode** (top-right toggle)
3. Find "Widevine Proxy 2" and copy its **ID**
4. Open this URL in a new tab:
   ```
   chrome-extension://YOUR_EXTENSION_ID/panel/panel.html
   ```

### Extract Commands

After capturing streams with Widevine Proxy 2:

1. Open Chrome DevTools: `Cmd+Option+I` (Mac) or `F12` (Windows)
2. Go to the **Console** tab
3. Paste and run:

```javascript
(() => {
  const text = Array.from(document.querySelectorAll('.log-container'))
    .map(container => {
      const cmdInput = container.querySelector('#command');
      if (!cmdInput) return null;
      return cmdInput.value.trim();
    })
    .filter(Boolean)
    .join('\n');
  copy(text);
  console.log(`Copied ${text.split('\n').length} commands to clipboard.`);
})();
```

4. Paste the commands into SP Workshop's **DOWNLOAD** section

### Example Commands (TF1)

```
"https://vod.tf1.fr/..." -H "..." --key KID:KEY --use-shaka-packager
"https://vod.tf1.fr/..." -H "..." --key KID:KEY --use-shaka-packager
"https://vod.tf1.fr/..." -H "..." --key KID:KEY --use-shaka-packager
```

---

## Globoplay (Portuguese)

Globoplay does **not** use DRM encryption for browser streams, so no keys are needed. The downloader automatically adds browser headers to bypass 403 errors.

### How to Get the m3u8 URLs

1. **Open Globoplay** in your browser and start playing an episode
2. **Open DevTools**: Press `F12` (Windows/Linux) or `Cmd+Option+I` (Mac)
3. **Go to Network tab** in DevTools
4. **Filter by `.m3u8`** in the search box
5. **Find the main manifest URL** - it will look like:
   ```
   https://egcdn-vod.video.globo.com/r360_1080/v1/.../14242569.m3u8
   ```
6. **Right-click the URL** → Copy → Copy URL
7. **Repeat for each episode** you want to download
8. **Paste all URLs** into SP Workshop (one per line, with or without quotes)

### Using SP Workshop

1. **Select Source**: Choose "Globoplay (Portuguese)" from the dropdown
2. **Set Episode Numbers**: Enter the starting episode number or range
   - Single: `71`
   - Range: `71-80` (episodes 71 through 80)
   - Multiple: `71,73,75` (specific episodes)
3. **Paste URLs**: Paste your m3u8 URLs (one per line):
   ```
   "https://egcdn-vod.video.globo.com/.../episode1.m3u8"
   "https://egcdn-vod.video.globo.com/.../episode2.m3u8"
   "https://egcdn-vod.video.globo.com/.../episode3.m3u8"
   ```
4. **Click "Batch download episodes"**

**Note**: You can paste URLs with or without quotes, the downloader handles both.

### Troubleshooting

#### 403 Forbidden Errors

If you get 403 errors:

1. **Get fresh URLs**: Globoplay URLs expire after ~2.5 hours. Get new URLs from DevTools.
2. **Make sure you're logged in** when capturing URLs from DevTools.
3. **Check the URL format**: Make sure you're copying the `.m3u8` URL, not the `.ism` manifest URL.

---

## Command Format

The batch downloader accepts raw commands, one per line. You can paste:

- Just the URL in quotes: `"https://..."`
- Full N_m3u8DL-RE command: `N_m3u8DL-RE "https://..." --key ...`
- Mix of both

The downloader will:
1. Auto-number episodes starting from your specified number
2. Automatically add quality/language/output settings
3. Select audio/subtitles based on the source language
