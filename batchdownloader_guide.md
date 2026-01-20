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

Globoplay does **not** use DRM encryption for browser streams, so no keys are needed.

### How to Get the m3u8 URLs

1. Open DevTools (`F12`) while playing an episode
2. Go to the **Network** tab
3. Filter by `.m3u8`
4. Copy the main manifest URL (contains the video ID and token)

### Example Commands (Globoplay)

```
"https://egcdn-vod.video.globo.com/r360_1080/v1/.../episode1.m3u8"
"https://egcdn-vod.video.globo.com/r360_1080/v1/.../episode2.m3u8"
"https://egcdn-vod.video.globo.com/r360_1080/v1/.../episode3.m3u8"
```

### Token Expiration

Globoplay URLs contain a token that expires after ~2.5 hours. If you get 403 errors, grab fresh URLs from DevTools.

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
