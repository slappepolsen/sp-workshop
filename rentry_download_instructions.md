# SP Workshop – Download Input Guide

Paste commands into the Download section, one per line. Each line = one episode. The app auto-numbers episodes from the number you set in **Episodes**.

---

## Format

- **One command per line**
- **Episodes field** = starting episode number (e.g. `89` for episode 89)
- You can paste the `N_m3u8DL-RE` prefix or omit it – the app adds what it needs

---

## Type A – URL-only (no DRM)

For streams that don’t use DRM:

**Option 1 (simple):** Paste just the URL. The app may add headers automatically for some CDNs.

```
"https://.../manifest.m3u8"
"https://.../episode2.m3u8"
```

**Option 2 (manual headers):** If you get 403 errors, add headers yourself. From your browser’s **Network** tab (F12 → Network), copy the request headers (Referer, Cookie, etc.) and include them:

```
"https://.../manifest.m3u8" -H "Referer: https://..." -H "Cookie: ..."
```

---

## Type B – DRM (Widevine)

For streams protected by Widevine:

1. Install a browser extension that captures Widevine keys
2. Play the video and capture the command it generates
3. Paste the **full command** (URL + `-H` headers + `--key KID:KEY`)

Example:

```
"https://vod.example.com/..." -H "Cookie: ..." -H "User-Agent: ..." --key KID:KEY --use-shaka-packager
```

---

## Type C – MPD/DASH

Same as Type B. Use the full command from your capture tool. Add `--use-shaka-packager` if your tool doesn’t include it.

---

## Episode numbering

- **Single:** `1` → episodes 1, 2, 3, …
- **Range:** `1-5` → episodes 1, 2, 3, 4, 5
- **List:** `1,3,5` → episodes 1, 3, 5
- **Mixed:** `89-92` → episodes 89, 90, 91, 92

---

Return to SP Workshop
