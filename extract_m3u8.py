#!/usr/bin/env python3
"""Extract main m3u8 URLs from HAR file with episode metadata."""

import json
import re
import sys
from urllib.parse import unquote

def extract_m3u8_urls(har_file):
    """Extract unique main m3u8 URLs from HAR file with episode titles."""
    with open(har_file, 'r') as f:
        har_data = json.load(f)
    
    # Use dict to track episodes with their metadata
    episodes = {}  # {video_id: {"url": ..., "title": ...}}
    
    # Get all entries from the HAR
    for entry in har_data.get('log', {}).get('entries', []):
        url = entry.get('request', {}).get('url', '')
        
        # Extract episode title from analytics URLs
        if 'title=' in url and 'mediaResource=' in url:
            # Extract video ID from mediaResource parameter
            resource_match = re.search(r'/(\d+)\.m3u8', url)
            if resource_match:
                video_id = resource_match.group(1)
                # Extract title
                title_match = re.search(r'[?&]title=([^&]+)', url)
                if title_match and video_id not in episodes:
                    title = unquote(title_match.group(1))
                    episodes[video_id] = {"title": title, "url": None}
        
        # Extract m3u8 URLs (main manifest only)
        if '.m3u8' in url:
            match = re.search(r'/(\d+)\.m3u8($|\?)', url)
            if match and '-manifest-' not in url:
                video_id = match.group(1)
                # Store or update the URL
                if video_id in episodes:
                    episodes[video_id]["url"] = url
                else:
                    episodes[video_id] = {"url": url, "title": None}
    
    # Sort by video ID numerically
    sorted_ids = sorted(episodes.keys(), key=int)
    return [(video_id, episodes[video_id]) for video_id in sorted_ids]

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 extract_m3u8.py <har_file>")
        sys.exit(1)
    
    har_file = sys.argv[1]
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
