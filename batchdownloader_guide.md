# Batch Downloader Guide

> **Experimental** - Currently only works with TF1.

This guide explains how to extract download commands from Widevine Proxy 2 for use with SP Workshop's batch downloader.

## Setup

### Open Widevine Proxy 2 as a Tab

The extension works better as a full tab instead of a popup.

1. Go to `chrome://extensions/`
2. Enable **Developer mode** (top-right toggle)
3. Find "Widevine Proxy 2" and copy its **ID**
4. Open this URL in a new tab:
   ```
   chrome-extension://YOUR_EXTENSION_ID/panel/panel.html
   ```

## Extract Commands

After capturing streams with Widevine Proxy 2:

1. Open Chrome DevTools: `Cmd+Option+I` (Mac) or `F12` (Windows)
2. Go to the **Console** tab
3. Paste and run:

```javascript
(() => {
  const text = Array.from(document.querySelectorAll('.log-container'))
    .map(container => {
      const urlInput = container.querySelector('label input[type="text"]');
      const cmdInput = container.querySelector('#command');
      if (!urlInput || !cmdInput) return null;

      const url = urlInput.value;
      const match = url.match(/episode-(\d+)-/);
      const episode = match ? match[1] : 'unknown';
      const command = cmdInput.value.trim();
      return `Episode ${episode}: N_m3u8DL-RE ${command}`;
    })
    .filter(Boolean)
    .join('\n');
  copy(text);
  console.log(`Copied ${text.split('\n').length} clean commands to clipboard.`);
})();
```

4. Paste the commands into SP Workshop's **DOWNLOAD** section
