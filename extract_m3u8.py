#!/usr/bin/env python3
"""Extract main m3u8 URLs from HAR file with episode metadata. Uses har_utils."""

import sys
from pathlib import Path

# Use shared HAR logic
from har_utils import extract_m3u8_urls


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_m3u8.py <har_file>")
        sys.exit(1)
    har_file = Path(sys.argv[1])
    episodes = extract_m3u8_urls(har_file)
    print(f"Found {len(episodes)} unique episodes:\n")
    print("=" * 80)
    for video_id, data in episodes:
        title = data.get("title") or "Unknown"
        url = data.get("url") or "No URL found"
        print(f"\nVideo ID: {video_id}")
        print(f"Title: {title}")
        print(f'URL: "{url}"')
    print("\n" + "=" * 80)
    print("\nURLs only (ready to paste):\n")
    for video_id, data in episodes:
        if data.get("url"):
            print(f'"{data["url"]}"')


if __name__ == "__main__":
    main()
